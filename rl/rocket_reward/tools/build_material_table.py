"""Build data/material_table.json: the density of every material name the reward knows.

Usage (from the folder that holds rocket_reward):

    python -m rocket_reward.tools.build_material_table \\
        --java-home /path/to/jdk17 --jar /path/to/OpenRocket-24.12.jar \\
        --gold train.jsonl val.jsonl test.jsonl \\
        --model-answers rocket_reward/tests/data/model_val.jsonl.gz \\
        --out rocket_reward/data/material_table.json --report material_report.md

What it does:

1. OpenRocket's own list. java/DumpMaterials.java is compiled and run against
   the jar. It prints OpenRocket's built-in materials (source "openrocket")
   and the materials of every component preset file (.orc) inside the jar
   (source "preset"). Densities come from each file's Materials section. A
   name can appear in several files with different densities; the value
   used is the one most of the newer files declare (see typical()), or most
   of the old "-legacy" files when no newer file lists the name, and a
   spread of more than 10% is flagged in the report. A built-in name always
   keeps OpenRocket's built-in density.
2. Reference names. Every material node in the reference ("gold") answers is
   read. A name the OpenRocket list does not know by any of the matching
   rules in materials.py (exact, up to case and spacing, or with "RS:" taken
   off) gets the median of the densities the reference designs write for
   it (source "reference"); names whose written densities disagree by more
   than 10% are flagged. Every reference node whose written density differs
   from the table value by more than 10% is counted in the report.
3. Physical values only. A density is used only when it is physically
   possible: bulk between limits.BULK_DENSITY_MIN_KG_M3 and
   BULK_DENSITY_MAX_KG_M3; surface between limits.SURFACE_MIN_KG_M2 and
   SURFACE_DENSITY_MAX_KG_M2; line between limits.LINE_MIN_KG_M and
   LINE_DENSITY_MAX_KG_M. Zero is never a physical density: parachute
   cloth and lines always weigh something, and a table entry of 0 would let a
   design fly a massless parachute. So zero (and unit slips such as paper
   written as 0.0011 kg/m3) are left out before the median is taken, and a
   name with no physical value left is dropped, unless STAND_INS names the
   real OpenRocket material it stands for.
4. Measuring. The report says how many reference material nodes the finished
   table knows, and, for the model's saved answers, every unknown name with
   its count and how many answers hold at least one unknown name.

The Java home and the jar are always passed in; nothing here knows where
they live on a given machine. --dump reuses a saved DumpMaterials output
instead of running Java.
"""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import os
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

from .. import limits as L
from ..materials import (MATERIAL_TYPES, MaterialTable, UNITS, loose_name, rocksim_name)
from ..parse import parse_answer
from ..tree import material_nodes, number

PACKAGE = Path(__file__).resolve().parents[1]
JAVA_SOURCE = PACKAGE / "java" / "DumpMaterials.java"

# Two densities "agree" when the larger is at most this much above the smaller.
AGREE_RATIO = 1.10

# The physical bounds for every density (bulk, surface and line, lowest and
# highest) live in limits.py with their sources; physical() reads them there.

# Reference names written only with a zero density, mapped to the real
# OpenRocket material each one stands for, with the reason. Without these a
# reference design would either fly a massless line or cloth, or lose its
# material name.
STAND_INS: dict[tuple[str, str], tuple[str, str]] = {
    ("bulk", "RS: G10 (PML 0.093)"): (
        "G10 Phenolic",
        "PML's 0.093 in. G10 sheet; the designs write 0.0071 kg/m3 (a unit slip) and OpenRocket's "
        "G10 (PML 0.093) is listed only as a surface material; Rocksim's G10 is 1905 kg/m3, as here"),
    ("line", "Nylon IIIa Paraline [flat 6.4 mm, 1/4 in]"): (
        "Nylon #400 IIIa Paraline [flat 6.4 mm, 1/4 in]",
        "the same product as listed in the Front Range and Fruity Chutes preset files"),
    ("bulk", "Paper, bulk"): (
        "Paper (office)",
        "two preset files declare this name at 0 kg/m3 and the reference designs write 0.0011 kg/m3 "
        "(a unit slip for about 1,100 kg/m3); OpenRocket's own paper is used"),
    ("line", "RS: Thin poly"): (
        "Braided nylon (2 mm, 1/16 in)",
        "Rocksim's thin shroud line; no density is known, so the lightest common OpenRocket shroud line"),
    ("line", "RS: Medium poly"): (
        "Braided nylon (3 mm, 1/8 in)",
        "Rocksim's medium shroud line; no density is known, so the next OpenRocket braided line"),
    ("line", "RS: Heavy poly"): (
        "Nylon flat webbing md. (10 mm, 3/8 in)",
        "Rocksim's heavy line; no density is known, so a medium OpenRocket webbing"),
}


# --------------------------------------------------------------------------- Java

def run_dump(java_home: Path, jar: Path, work: Optional[Path] = None) -> dict:
    """Compile and run DumpMaterials against the jar; return its JSON."""
    exe = ".exe" if os.name == "nt" else ""
    javac = java_home / "bin" / f"javac{exe}"
    java = java_home / "bin" / f"java{exe}"
    for p, what in ((javac, "javac"), (java, "java"), (jar, "the OpenRocket jar"), (JAVA_SOURCE, "DumpMaterials.java")):
        if not p.is_file():
            raise SystemExit(f"{what} not found at {p}")
    tmp = None
    if work is None:
        tmp = tempfile.TemporaryDirectory()
        work = Path(tmp.name)
    classes = work / "classes"
    classes.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(javac), "-nowarn", "-encoding", "UTF-8", "-cp", str(jar), "-d", str(classes),
                    str(JAVA_SOURCE)], check=True)
    proc = subprocess.run([str(java), "-cp", f"{jar}{os.pathsep}{classes}", "DumpMaterials", str(jar)],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=600)
    if proc.returncode != 0:
        raise SystemExit("DumpMaterials failed:\n" + proc.stderr.decode("utf-8", "replace")[-4000:])
    if tmp is not None:
        tmp.cleanup()
    return json.loads(proc.stdout.decode("utf-8"))


# --------------------------------------------------------------------------- answers

def read_answers(paths: Iterable[Path]) -> list[tuple[str, str, bool]]:
    """(row id, answer text, truncated) from JSONL files, plain or gzip.

    A row is either a chat record {"messages": [...]} (the assistant message
    is the answer) or a saved answer {"content": ...} / {"answer": ...}."""
    out: list[tuple[str, str, bool]] = []
    for path in paths:
        opener = gzip.open if str(path).endswith(".gz") else open
        with opener(path, "rt", encoding="utf-8") as fh:
            for i, line in enumerate(fh):
                if not line.strip():
                    continue
                row = json.loads(line)
                rid = str(row.get("id", f"{Path(path).name}:{i + 1}"))
                if "messages" in row:
                    text = next((m.get("content", "") for m in row["messages"] if m.get("role") == "assistant"), "")
                else:
                    text = row.get("content", row.get("answer", ""))
                out.append((rid, text if isinstance(text, str) else "", bool(row.get("truncated", False))))
    return out


def answer_material_nodes(text: str, truncated: bool = False) -> Optional[list[tuple[str, Any, Any, Any]]]:
    """(tag, type, name, written density) for every material node in the
    answer's design, or None when the design cannot be read."""
    _, root = parse_answer(text, truncated=truncated)
    if root is None:
        return None
    return material_nodes(root)


# --------------------------------------------------------------------------- building

def physical(mtype: str, d: Any) -> bool:
    """True when d is a physically possible density for this material type."""
    if not isinstance(d, (int, float)) or isinstance(d, bool):
        return False
    lo, hi = {"bulk": (L.BULK_DENSITY_MIN_KG_M3, L.BULK_DENSITY_MAX_KG_M3),
              "surface": (L.SURFACE_MIN_KG_M2, L.SURFACE_DENSITY_MAX_KG_M2),
              "line": (L.LINE_MIN_KG_M, L.LINE_DENSITY_MAX_KG_M)}[mtype]
    return lo <= d <= hi


def junk_name(name: Any) -> bool:
    """Names that are not a material: not text, empty, or only the Rocksim
    prefix "RS:". (Names in OpenRocket's old "[material:...]" wrapper are kept:
    the legacy preset files and some reference designs use them as names.)"""
    return not isinstance(name, str) or not name.strip() or not rocksim_name(name)


def disagree(values: Sequence[float]) -> bool:
    """True when the values differ by more than AGREE_RATIO."""
    return len(values) > 1 and max(values) > AGREE_RATIO * min(values)


def typical(values: Sequence[float]) -> float:
    """The value most preset files declare for a name (to 4 significant
    digits); when no value is the most common one, the median of all of them.
    Preset files copy their materials from each other, so the common value is
    the catalogue value; a plain median would average two catalogues into a
    number neither uses (Paper: three files say 1121 kg/m3 and two say 609,
    the median is 896)."""
    groups: dict[float, list[float]] = collections.defaultdict(list)
    for v in values:
        groups[float(f"{v:.4g}")].append(v)
    counts = sorted((len(g) for g in groups.values()), reverse=True)
    if len(counts) > 1 and counts[0] == counts[1]:
        return statistics.median(values)
    best = max(groups, key=lambda k: len(groups[k]))
    return statistics.median(groups[best])


def build(dump: dict, gold: list[tuple[str, str, bool]]) -> tuple[dict, dict]:
    """Return (materials, notes): the table's materials and what the report needs."""
    materials: dict[str, dict[str, dict]] = {t: {} for t in MATERIAL_TYPES}
    notes: dict[str, Any] = collections.defaultdict(list)

    # 1a. OpenRocket's built-in database
    for m in dump["builtin"]:
        t, name, d = m["type"], m["name"], m["density"]
        if t not in materials:
            continue
        if not physical(t, d):
            notes["dropped"].append((t, name, "openrocket", [d], "not physical"))
            continue
        materials[t][name] = {"density": d, "source": "openrocket"}

    # 1b. preset files: declared materials plus the materials parts use
    values: dict[tuple[str, str], dict[bool, list[float]]] = collections.defaultdict(lambda: {True: [], False: []})
    raw: dict[tuple[str, str], list] = collections.defaultdict(list)
    used = {(m["type"], m["name"], m["density"]) for m in dump["presets"]}
    declared = {(m["type"], m["name"], m["density"]) for m in dump["declared"]}
    # Densities come from the files' Materials sections. OpenRocket's reader
    # gives some legacy parts a material of the declared name but a density
    # worked out from that part's own weight (Polystyrene PS is declared at
    # 1049 kg/m3 but read at 424 to 2192 kg/m3); such a part counts only for
    # a name that no file declares.
    declared_names = {(m["type"], m["name"]) for m in dump["declared"]}
    # A declared density is the number as the file writes it, read as SI. Six
    # surface materials in two files are labelled "g/m2", but their numbers
    # are kg/m2 (1.1 oz/yd2 ripstop written 0.0341 is 34 g/m2, the real
    # weight); read as g/m2 they would be a thousand times too light, which is
    # what OpenRocket's own reader does with them. Every such label is listed
    # in the report, and physical() still judges the number as SI.
    for m in dump["declared"]:
        if m["type"] in UNITS and m.get("units") not in (None, UNITS[m["type"]]):
            notes["unit_labels"].append((m["type"], m["name"], m["file"].rsplit("/", 1)[-1], m["density"],
                                         m["units"]))
    extra = [m for m in dump["presets"] if (m["type"], m["name"]) not in declared_names]
    for m in list(dump["declared"]) + extra:
        t, name, d, f = m["type"], m["name"], m["density"], m["file"]
        if t not in materials:
            continue
        raw[(t, name)].append(d)
        if junk_name(name):
            continue
        if physical(t, d):
            values[(t, name)]["-legacy" in f.lower()].append(float(d))
    notes["used_not_declared"] = sorted(used - declared, key=str)
    for (t, name), d_raw in sorted(raw.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        if junk_name(name):
            notes["dropped"].append((t, name, "preset", sorted(set(map(str, d_raw))), "not a material name"))
            continue
        tiers = values.get((t, name))
        chosen = (tiers[False] or tiers[True]) if tiers else []
        if name in materials[t]:
            ord_d = materials[t][name]["density"]
            if chosen and disagree([typical(chosen), ord_d]):
                notes["preset_vs_builtin"].append((t, name, ord_d, typical(chosen)))
            continue
        if not chosen:
            notes["dropped"].append((t, name, "preset", sorted(set(map(str, d_raw))), "no physical density"))
            continue
        med = typical(chosen)
        if disagree(chosen):
            notes["preset_spread"].append((t, name, min(chosen), med, max(chosen), len(chosen)))
        materials[t][name] = {"density": med, "source": "preset"}
        excluded = [d for d in d_raw if not physical(t, d)]
        if excluded:
            notes["preset_values_left_out"].append((t, name, sorted(set(map(str, excluded))), med))

    known = MaterialTable(materials)

    # 2. reference names
    gold_nodes: list[tuple[str, str, Any, Any, Any]] = []
    for rid, text, trunc in gold:
        nodes = answer_material_nodes(text, trunc)
        if nodes is None:
            notes["gold_unreadable"].append(rid)
            continue
        gold_nodes.extend((rid, tag, t, n, d) for tag, t, n, d in nodes)
    written: dict[tuple[str, str], list] = collections.defaultdict(list)
    for _, _, t, name, d in gold_nodes:
        if isinstance(t, str) and t in materials and isinstance(name, str):
            written[(t, name)].append(d)
    for (t, name), ds in sorted(written.items()):
        if junk_name(name):
            notes["gold_junk"].append((t, name, len(ds)))
            continue
        hit = known.match(t, name)
        nums = [number(d) for d in ds]
        good = [x for x in nums if x is not None and physical(t, x)]
        if hit is not None:
            # OpenRocket knows this name (for "RS: X" through its X), and its
            # value is kept: the reference designs' own "RS:" densities are
            # listed next to it in the report.
            if hit.rule == "rocksim":
                notes["rocksim_pairs"].append((t, name, hit.name, statistics.median(good) if good else None,
                                               hit.density, len(ds)))
            continue
        if not good:
            stand = STAND_INS.get((t, name))
            target = materials[t].get(stand[0]) if stand else None
            if target is None:
                notes["dropped"].append((t, name, "reference", sorted(set(map(str, ds))), "no physical density"))
                continue
            materials[t][name] = {"density": target["density"], "source": "reference",
                                  "stand_in_for": stand[0]}
            notes["stand_ins"].append((t, name, stand[0], target["density"], stand[1], len(ds)))
            continue
        med = statistics.median(good)
        if disagree(good):
            notes["reference_spread"].append((t, name, min(good), med, max(good), len(good)))
        materials[t][name] = {"density": med, "source": "reference"}
        if len(good) < len(ds):
            notes["reference_values_left_out"].append(
                (t, name, collections.Counter(str(d) for d, x in zip(ds, nums)
                                              if x is None or not physical(t, x)), med))
    for key in STAND_INS:
        if key not in materials[key[0]] or materials[key[0]][key[1]].get("stand_in_for") is None:
            notes["stand_ins_unused"].append(key)

    # 3. reference densities compared with the finished table
    table = MaterialTable(materials)
    slips = collections.Counter()
    slip_values: dict[tuple, collections.Counter] = collections.defaultdict(collections.Counter)
    rules = collections.Counter()
    unknown = collections.Counter()
    for rid, tag, t, name, d in gold_nodes:
        hit = table.match(t, name)
        if hit is None:
            unknown[(str(t), str(name))] += 1
            continue
        rules[hit.rule] += 1
        x = number(d)
        if x is None or x <= 0 or max(x, hit.density) > AGREE_RATIO * min(x, hit.density):
            slips[(t, name, hit.source, hit.density)] += 1
            slip_values[(t, name, hit.source, hit.density)][str(d)] += 1
    notes["gold_rows"] = len(gold)
    notes["gold_nodes"] = len(gold_nodes)
    notes["gold_rules"] = rules
    notes["gold_unknown"] = unknown
    notes["gold_slips"] = slips
    notes["gold_slip_values"] = slip_values
    return materials, notes


def measure_model(table: MaterialTable, answers: list[tuple[str, str, bool]]) -> dict:
    """Unknown material names in the model's answers."""
    names = collections.Counter()
    per_answer: dict[str, list[str]] = {}
    unreadable = []
    nodes_total = 0
    rules = collections.Counter()
    for rid, text, trunc in answers:
        nodes = answer_material_nodes(text, trunc)
        if nodes is None:
            unreadable.append(rid)
            continue
        bad = []
        for tag, t, name, d in nodes:
            nodes_total += 1
            hit = table.match(t, name)
            if hit is None:
                names[(str(t), str(name))] += 1
                bad.append(f"{t}:{name}")
            else:
                rules[hit.rule] += 1
        if bad:
            per_answer[rid] = sorted(set(bad))
    return {"answers": len(answers), "unreadable": unreadable, "nodes": nodes_total, "rules": rules,
            "unknown_names": names, "answers_with_unknown": per_answer}


# --------------------------------------------------------------------------- output

def write_table(materials: dict, dump_meta: dict, path: Path) -> None:
    doc = {
        "about": ("Density of every material name the reward knows, in SI units. Built by "
                  "rocket_reward/tools/build_material_table.py; see rocket_reward/materials.py for "
                  "how a name is matched. Sources: openrocket = OpenRocket's built-in materials, "
                  "preset = OpenRocket's component preset files, reference = names only the "
                  "reference designs use, with the density they write."),
        "built_from": dump_meta,
        "units": UNITS,
        "materials": {t: {n: materials[t][n] for n in sorted(materials[t])} for t in MATERIAL_TYPES},
    }
    text = json.dumps(doc, indent=1, ensure_ascii=False, sort_keys=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def _g(x: float) -> str:
    return f"{x:.6g}"


def write_report(materials: dict, notes: dict, model: Optional[dict], path: Path) -> None:
    lines: list[str] = ["# Material table build report", ""]
    src = collections.Counter((t, e["source"]) for t in MATERIAL_TYPES for e in materials[t].values())
    lines += ["## Table", "", "| type | openrocket | preset | reference | total |", "|---|---|---|---|---|"]
    for t in MATERIAL_TYPES:
        lines.append(f"| {t} | {src[(t, 'openrocket')]} | {src[(t, 'preset')]} | {src[(t, 'reference')]} | "
                     f"{len(materials[t])} |")
    lines.append("")

    gn = notes["gold_nodes"]
    unk = notes["gold_unknown"]
    lines += ["## Reference coverage", "",
              f"{notes['gold_rows']} reference answers, {gn} material nodes; "
              f"{gn - sum(unk.values())} known ({dict(notes['gold_rules'])}), "
              f"{sum(unk.values())} unknown.", ""]
    for (t, n), c in unk.most_common():
        lines.append(f"* unknown: {t} {n!r} x{c}")
    if notes["gold_unreadable"]:
        lines.append(f"* unreadable reference answers: {notes['gold_unreadable']}")
    lines.append("")

    slips = notes["gold_slips"]
    by_src = collections.Counter()
    for (t, n, s, d), c in slips.items():
        by_src[s] += c
    lines += ["## Reference densities more than 10% off the table value", "",
              f"{sum(slips.values())} nodes ({dict(by_src)}), over {len(slips)} names. "
              "Counted per node; the written values follow each name.", "",
              "| type | name | source | table | nodes | written values (count) |", "|---|---|---|---|---|---|"]
    for (t, n, s, d), c in sorted(slips.items(), key=lambda kv: (kv[0][2] == "reference", -kv[1], kv[0][1])):
        vals = ", ".join(f"{v} ({k})" for v, k in notes["gold_slip_values"][(t, n, s, d)].most_common(6))
        lines.append(f"| {t} | {n} | {s} | {_g(d)} | {c} | {vals} |")
    lines.append("")

    def section(title: str, rows: list, fmt) -> None:
        lines.extend([f"## {title}", ""])
        lines.extend(fmt(r) for r in rows)
        if not rows:
            lines.append("none")
        lines.append("")

    section("Reference names whose written densities disagree by more than 10% (median used)",
            notes["reference_spread"],
            lambda r: f"* {r[0]} {r[1]!r}: {_g(r[2])} .. {_g(r[4])}, median {_g(r[3])} ({r[5]} values)")
    section("Reference values left out as not physical", notes["reference_values_left_out"],
            lambda r: f"* {r[0]} {r[1]!r}: {dict(r[2])} -> table {_g(r[3])}")
    section("Stand-ins for reference names written only with a zero density", notes["stand_ins"],
            lambda r: f"* {r[0]} {r[1]!r} ({r[5]} nodes) -> {r[2]!r} = {_g(r[3])}: {r[4]}")
    section("Rocksim names (\"RS: X\") next to OpenRocket's X", notes["rocksim_pairs"],
            lambda r: (f"* {r[0]} {r[1]!r}: designs write {_g(r[3])}, table uses {r[2]!r} = {_g(r[4])} "
                       f"({(r[3] / r[4] - 1) * 100:+.1f}%, {r[5]} nodes)") if r[3] is not None else
                      (f"* {r[0]} {r[1]!r}: designs write no physical value, table uses {r[2]!r} = "
                       f"{_g(r[4])} ({r[5]} nodes)"))
    section("Preset names whose densities disagree by more than 10%", notes["preset_spread"],
            lambda r: f"* {r[0]} {r[1]!r}: {_g(r[2])} .. {_g(r[4])}, table uses {_g(r[3])} ({r[5]} values)")
    section("Preset values left out as not physical", notes["preset_values_left_out"],
            lambda r: f"* {r[0]} {r[1]!r}: {r[2]} -> table {_g(r[3])}")
    section("Preset names that differ from OpenRocket's built-in value (built-in kept)", notes["preset_vs_builtin"],
            lambda r: f"* {r[0]} {r[1]!r}: built-in {_g(r[2])}, presets {_g(r[3])}")
    section("Declared densities with a non-SI unit label (the number is read as SI)", notes["unit_labels"],
            lambda r: f"* {r[0]} {r[1]!r} in {r[2]}: {r[3]} labelled {r[4]}")
    section("Dropped", notes["dropped"], lambda r: f"* {r[0]} {r[1]!r} ({r[2]}): {r[4]}; values {r[3][:8]}")
    section("Junk names in the reference designs", notes["gold_junk"],
            lambda r: f"* {r[0]} {r[1]!r} x{r[2]}")

    if model is not None:
        un = model["unknown_names"]
        lines += ["## Model answers", "",
                  f"{model['answers']} answers, {len(model['unreadable'])} without a readable design "
                  f"({model['unreadable']}); {model['nodes']} material nodes, "
                  f"{sum(un.values())} with an unknown name; known by rule {dict(model['rules'])}.", "",
                  f"Answers with at least one unknown name: {len(model['answers_with_unknown'])}", ""]
        for (t, n), c in un.most_common():
            lines.append(f"* {t} {n!r} x{c}")
        lines.append("")
        for rid, names in sorted(model["answers_with_unknown"].items()):
            lines.append(f"* {rid}: {names}")
        lines.append("")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines))


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--java-home", type=Path, help="JDK 17 folder (holds bin/javac and bin/java)")
    ap.add_argument("--jar", type=Path, required=True, help="the OpenRocket 24.12 jar")
    ap.add_argument("--dump", type=Path, help="reuse a saved DumpMaterials output instead of running Java")
    ap.add_argument("--save-dump", type=Path, help="also save the DumpMaterials output here")
    ap.add_argument("--work", type=Path, help="folder for the compiled Java class (default: a temporary one)")
    ap.add_argument("--gold", type=Path, nargs="+", required=True, help="reference answer files (JSONL)")
    ap.add_argument("--model-answers", type=Path, nargs="*", default=[], help="model answers to measure")
    ap.add_argument("--out", type=Path, required=True, help="where to write material_table.json")
    ap.add_argument("--report", type=Path, required=True, help="where to write the Markdown report")
    args = ap.parse_args(argv)

    if args.dump is not None:
        with open(args.dump, encoding="utf-8") as fh:
            dump = json.load(fh)
    else:
        if args.java_home is None:
            ap.error("--java-home is needed unless --dump is given")
        dump = run_dump(args.java_home, args.jar, args.work)
    if args.save_dump is not None:
        with open(args.save_dump, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(dump, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
    sha = hashlib.sha256(args.jar.read_bytes()).hexdigest() if args.jar.is_file() else None
    gold = read_answers(args.gold)
    materials, notes = build(dump, gold)
    meta = {"openrocket_jar": args.jar.name, "openrocket_jar_sha256": sha,
            "preset_files": len(dump.get("preset_files", [])), "reference_answers": len(gold)}
    write_table(materials, meta, args.out)
    table = MaterialTable.load(args.out)
    model = measure_model(table, read_answers(args.model_answers)) if args.model_answers else None
    write_report(materials, notes, model, args.report)
    print(f"wrote {args.out} ({len(table)} materials) and {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
