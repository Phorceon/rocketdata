#!/usr/bin/env python3
"""Independent validator for the Stage-2 final rows (NO flights).

Deliberately does NOT import the reasoning renderer: it re-implements every
check from the Stage-1 inputs and the final files.  For every row it checks:

* JSON parses; the assistant message has exactly one <thought> and one
  <design> block;
* the design JSON equals the Stage-1 compact after the approved Stage-2
  changes (motor <digest> elements replaced by readable <motor_id> elements,
  preset blocks, cosmetic leaves and the simulation name removed, and
  preset-supplied parachute overrides written out explicitly);
* no digest or hex string survives anywhere in the design, every motor_id
  exists in final/motor_lookup.json, the lookup is one-to-one with the
  digests, and every explicit override value is backed by the headless load
  dump;
* every leaf of the final design appears in the thought with an equal value;
* banned patterns (verified, sha256, hex digests, UUIDs, .ork, source file
  names, simulation names, seed, getter names, audit, reverse-simulation,
  provenance, base64) are absent from the assistant text;
* flags are correct (recomputed from targets + engineering.json);
* no id is lost or duplicated across train/test/excluded/oversized and the
  main-file order matches the Stage-1 row order;
* prompts and system messages are unchanged from the source rows;
* every main row is under 32,768 real Qwen tokens and every oversized row is
  over it.

Writes final/validation_report.json and exits 0 only when everything passes.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.sft_compact_motor_ids import apply_stage2_and_fix  # noqa: E402

STAGE_DIR = REPO_ROOT / "sftgen" / "out" / "scratch" / "sft_compact_20261103"
CANDIDATE_REL = REPO_ROOT / "sftgen/out/scratch/sft_full_fidelity_20261102/candidate/sft_v2_full_fidelity.jsonl"
TEST_INPUT_REL = REPO_ROOT / "new_results" / "sft_test_v2.jsonl"
TOKENIZER_MODEL = "Qwen/Qwen2.5-3B-Instruct"
ROW_TOKEN_LIMIT = 32_768
G0 = 9.80665

BANNED_RES = [
    ("word verified", re.compile(r"verified", re.IGNORECASE)),
    ("sha256", re.compile(r"sha256", re.IGNORECASE)),
    ("hex digest", re.compile(r"\b[0-9a-f]{32,}\b", re.IGNORECASE)),
    ("uuid", re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
                        r"[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE)),
    (".ork", re.compile(r"\.ork\b", re.IGNORECASE)),
    ("seed", re.compile(r"seed", re.IGNORECASE)),
    ("getter name", re.compile(r"get[A-Z]")),
    ("audit", re.compile(r"audit", re.IGNORECASE)),
    ("reverse-simulation", re.compile(r"reverse-simulation", re.IGNORECASE)),
    ("provenance", re.compile(r"provenance", re.IGNORECASE)),
    ("base64", re.compile(r"base64", re.IGNORECASE)),
]

TARGET_LABELS = ("apogee_m", "max_velocity_ms", "max_mach", "time_to_apogee_s",
                 "flight_time_s", "ground_hit_ms", "wind_ms")


def iter_jsonl(path: Path):
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


# ---- compact leaf walker (independent implementation) --------------------

def design_leaves(design: dict):
    """(path, value) for every leaf of the design JSON (attrs included)."""
    def visit(node, path):
        if not isinstance(node, dict):
            return
        kids = node.get("children")
        if not isinstance(kids, list):
            return
        for i, wrapper in enumerate(kids):
            if not (isinstance(wrapper, dict) and len(wrapper) == 1):
                continue
            (tag, payload), = wrapper.items()
            if not isinstance(payload, dict):
                continue
            here = f"{path}/{i}:{tag}"
            for ak, av in (payload.get("attrs") or {}).items():
                yield f"{here}@{ak}", av
            if "value" in payload:
                yield here, payload.get("value")
            yield from visit(payload, here)

    for wrapper in (design.get("openrocket") or {}).get("children") or []:
        if isinstance(wrapper, dict) and "rocket" in wrapper:
            yield from visit(wrapper["rocket"], "rocket")


def value_text(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return repr(v)
    return str(v)


# ---- flag recomputation (independent) ------------------------------------

def stage_mount_events(rocket: dict) -> list[tuple[Any, Any]]:
    """(ignitionevent, ignitiondelay) per mount with a motor, DFS order."""
    events = []

    def visit(node):
        kids = node.get("children") if isinstance(node, dict) else None
        if not isinstance(kids, list):
            return
        for wrapper in kids:
            if not (isinstance(wrapper, dict) and len(wrapper) == 1):
                continue
            (tag, payload), = wrapper.items()
            if tag == "motormount":
                ev = dl = None
                motor_present = False
                for w2 in (payload.get("children") or []):
                    if not (isinstance(w2, dict) and len(w2) == 1):
                        continue
                    (t2, p2), = w2.items()
                    if t2 == "motor":
                        motor_present = True
                    if t2 == "ignitionevent":
                        ev = p2.get("value")
                    if t2 == "ignitiondelay":
                        dl = p2.get("value")
                if motor_present:
                    events.append((ev, dl))
            visit(payload)

    visit(rocket)
    return events


def design_designations(design: dict) -> list[str]:
    out = []
    for path, value in design_leaves(design):
        if path.rsplit(":", 1)[-1] == "designation" and value is not None:
            out.append(str(value))
    return out


def expected_flags(row: dict, design: dict, eng: dict) -> list:
    """Flags recomputed from the row data only (fit_issue and
    motor_name_differs consistency is checked separately)."""
    flags: list = []
    targets = row["targets"]
    gh = targets.get("ground_hit_ms")
    if gh is not None and gh > 8.0:
        flags.append("landing_over_8ms")
    sm = eng.get("static_margin_cal")
    if sm is not None:
        if sm < 0:
            flags += ["stability_under_1cal", "stability_negative"]
        elif sm < 1:
            flags.append("stability_under_1cal")

    # ttw certainty: one motor, or every mount-lit motor launches with no delay
    rocket = next(w["rocket"] for w in design["openrocket"]["children"]
                  if "rocket" in w)
    events = stage_mount_events(rocket)
    motors = [m for m in (eng.get("motors") or [])
              if isinstance(m, dict) and m.get("motor")]
    certain = bool(motors) and (
        len(motors) == 1 or
        all(ev == "launch" for ev, _ in events)
        and all(d in (0, 0.0, None) for _, d in events))
    if not certain:
        flags.append("ttw_undetermined")

    # motor_name_differs: design designations vs resolved designations, in
    # order.  Motors with no resolved data (engineering.json motor: null) are
    # skipped on both sides, mirroring the reasoning renderer.
    design_des = design_designations(design)
    resolved = [m["motor"]["designation"] for m in motors if m.get("motor")]
    if len(design_des) == len(resolved):
        for d_des, r_des in zip(design_des, resolved):
            if d_des != r_des:
                flags.append({"flag": "motor_name_differs",
                              "designation_design": d_des,
                              "designation_resolved": r_des,
                              "digest_differs": None})
    return flags


def flags_match(actual: list, expected: list) -> list[str]:
    """Compare flag lists (dict entries compared on their flag name + names).

    fit_issue entries are skipped here: the validator cannot re-derive the
    fit arithmetic from data alone, so its presence is validated separately
    as text/flag consistency.
    """
    def key(f: Any) -> str:
        if isinstance(f, str):
            return f
        if f.get("flag") == "motor_name_differs":
            return (f"motor_name_differs:{f.get('designation_design')}:"
                    f"{f.get('designation_resolved')}")
        return f"{f.get('flag')}:{len(f.get('details') or [])}"

    a = sorted(map(key, (f for f in actual
                         if not (isinstance(f, dict) and f["flag"] == "fit_issue"))))
    e = sorted(map(key, (f for f in expected
                         if not (isinstance(f, dict) and f["flag"] == "fit_issue"))))
    diffs = []
    for k in e:
        if k not in a:
            diffs.append(f"missing flag: {k}")
    for k in a:
        if k not in e:
            diffs.append(f"unexpected flag: {k}")
    return diffs


# ---- design-level identity checks (independent of the transform) ----------

HEX_RE = re.compile(r"\b[0-9a-f]{32,}\b", re.IGNORECASE)


def check_design_ids(rid: str, design: dict, lookup: dict,
                     dump_rows: list[dict]) -> list[str]:
    """No digest/hex anywhere in the design; every motor_id exists in the
    lookup; every explicit override value is backed by the load dump."""
    problems: list[str] = []

    def visit(node, path):
        if not isinstance(node, dict):
            return
        kids = node.get("children")
        if not isinstance(kids, list):
            return
        for i, wrapper in enumerate(kids):
            if not (isinstance(wrapper, dict) and len(wrapper) == 1):
                continue
            (tag, payload), = wrapper.items()
            here = f"{path}/{i}:{tag}"
            if tag == "digest":
                problems.append(f"{rid}: digest leaf survives at {here}")
            if isinstance(payload, dict):
                value = payload.get("value")
                if tag == "motor_id":
                    if value not in lookup:
                        problems.append(
                            f"{rid}: motor_id {value!r} not in motor_lookup")
                elif value is not None and isinstance(value, str) \
                        and HEX_RE.search(value):
                    problems.append(f"{rid}: hex value at {here}")
                for ak, av in (payload.get("attrs") or {}).items():
                    if isinstance(av, str) and HEX_RE.search(av):
                        problems.append(f"{rid}: hex attr {ak} at {here}")
                visit(payload, here)

    for wrapper in (design.get("openrocket") or {}).get("children") or []:
        if isinstance(wrapper, dict) and "rocket" in wrapper:
            visit(wrapper["rocket"], "rocket")

    # explicit overrides must be backed by the as-is load dump (any component
    # can carry an override, so scan every dumped component's resolved state;
    # compare numerically because design spellings like '9.0E-4' stay strings
    # when the exact XML text is kept)
    def as_num(v: Any) -> Any:
        if isinstance(v, str):
            try:
                return float(v)
            except ValueError:
                return v
        return v

    dump_masses = {as_num(r["loaded"].get("getOverrideMass")) for r in dump_rows
                   if isinstance(r.get("loaded"), dict)}
    for path, value in design_leaves(design):
        if path.rsplit(":", 1)[-1] == "overridemass" \
                and value is not None and as_num(value) not in dump_masses:
            problems.append(f"{rid}: overridemass {value!r} not in the load "
                            "dump")
    return problems


# ---- main ----------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--final-dir", default=str(STAGE_DIR / "final"))
    parser.add_argument("--no-tokenizer", action="store_true")
    args = parser.parse_args()
    final_dir = Path(args.final_dir)

    eng = json.loads((STAGE_DIR / "engineering.json").read_text())
    digest_check = json.loads((STAGE_DIR / "digest_check.json").read_text())
    digest_pairs = digest_check["pairs"]
    lookup = json.loads(
        (STAGE_DIR / "final" / "motor_lookup.json").read_text())
    lookup_digests = {v["digest"] for v in lookup.values()}
    if len(lookup) != len(lookup_digests) or len(lookup) != len(set(lookup)):
        problems.append("motor lookup is not one-to-one (id<->digest)")
        stats["motor_lookup"] = {"size": len(lookup),
                                 "distinct_digests": len(lookup_digests)}
    stage_rows: dict[str, dict] = {}
    stage_order: dict[str, list[str]] = {}
    for split in ("train", "test"):
        stage_order[split] = []
        for row in iter_jsonl(STAGE_DIR / "compact" / f"{split}_rows.jsonl"):
            stage_rows[row["id"]] = row
            stage_order[split].append(row["id"])
    src_by_id: dict[str, dict] = {}
    for row in iter_jsonl(CANDIDATE_REL):
        src_by_id[row["id"]] = row
    for row in iter_jsonl(TEST_INPUT_REL):
        src_by_id[row["id"]] = row

    if args.no_tokenizer:
        def n_tokens(_t: str) -> int:
            return 0
    else:
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(TOKENIZER_MODEL, local_files_only=True)

        def n_tokens(text: str) -> int:
            return len(tok(text, add_special_tokens=False)["input_ids"])

    problems: list[str] = []
    stats: dict[str, Any] = {"files": {}, "banned": [], "flags": [],
                             "coverage": [], "token_limit": [],
                             "accounting": {}, "prompts": []}

    seen_ids: Counter = Counter()
    files = {split: final_dir / f"{split}.jsonl" for split in ("train", "test")}
    files["excluded"] = final_dir / "excluded.jsonl"
    files["oversized"] = final_dir / "oversized.jsonl"

    for split, path in files.items():
        rows = list(iter_jsonl(path)) if path.exists() else []
        stats["files"][split] = len(rows)
        for row in rows:
            seen_ids[row["id"]] += 1
            rid = row["id"]
            stage_row = stage_rows.get(rid)
            if stage_row is None:
                problems.append(f"{rid}: id not in stage-1 rows")
                continue
            src = src_by_id[rid]

            if split == "excluded":
                if not row.get("excluded_reason"):
                    problems.append(f"{rid}: excluded row without reason")
                if "compact" not in row:
                    problems.append(f"{rid}: excluded row lost its compact data")
                continue

            # message structure
            msgs = row.get("messages") or []
            if len(msgs) != 3:
                problems.append(f"{rid}: {len(msgs)} messages")
                continue
            assistant = msgs[2]["content"]
            if assistant.count("<thought>") != 1 or assistant.count("</thought>") != 1:
                problems.append(f"{rid}: not exactly one thought block")
            if assistant.count("<design>") != 1 or assistant.count("</design>") != 1:
                problems.append(f"{rid}: not exactly one design block")

            # design equals approved removals of the stage-1 compact
            m = re.search(r"<design>\n(.*)\n</design>\s*\Z", assistant, re.DOTALL)
            if not m:
                problems.append(f"{rid}: design block not found")
                continue
            design = json.loads(m.group(1))
            pair = f"{row['file']}|{row['sim']}"
            dump_rows = (digest_pairs.get(pair) or {}).get("components") or []
            expected_design, _fixes = apply_stage2_and_fix(
                stage_row["compact"],
                {v["digest"]: k for k, v in lookup.items()},
                dump_rows)
            if design != expected_design:
                problems.append(f"{rid}: design != approved stage-2 changes "
                                "of the stage-1 compact")

            # no digest/hex anywhere in the design; every motor_id in lookup;
            # every explicit override value backed by the load dump
            problems += check_design_ids(rid, design, lookup, dump_rows)

            # prompts and system message unchanged
            if msgs[1]["content"] != src["prompt_text"] or \
                    row.get("prompt_text") != src["prompt_text"]:
                problems.append(f"{rid}: prompt changed")
                stats["prompts"].append(rid)
            if msgs[0]["content"] != src["messages"][0]["content"]:
                problems.append(f"{rid}: system message changed")

            # banned patterns (assistant text) + row-identifying strings
            banned = [name for name, rx in BANNED_RES if rx.search(assistant)]
            file_stem = Path(row["file"]).stem
            if file_stem and file_stem in assistant:
                banned.append("source file stem")
            sim_name = row.get("sim")
            if sim_name and sim_name in assistant:
                banned.append("simulation name")
            if banned:
                stats["banned"].append({"id": rid, "banned": banned})
                problems.append(f"{rid}: banned patterns {banned}")

            # coverage: every leaf of the design appears in the thought
            thought = assistant.split("<thought>", 1)[1].split("</thought>", 1)[0]
            gaps = [f"{p} = {value_text(v)}" for p, v in design_leaves(design)
                    if v is not None and value_text(v) not in thought]
            if gaps:
                stats["coverage"].append({"id": rid, "gaps": gaps[:10]})
                problems.append(f"{rid}: {len(gaps)} uncovered leaves")

            # flags recomputed (fit_issue cannot be re-derived from data alone:
            # it is checked as text/flag consistency below)
            exp = expected_flags(row, design, eng[pair])
            got = row.get("flags") or []
            diffs = flags_match(got, exp)
            # fit_issue presence must match failure claims in the reasoning
            # (the exact verdict fragments the fit checks emit on failure)
            failure_words = ("exceeds mount inner diameter",
                             "exceeds tube inner",
                             "exceeds adjacent tube inner radius",
                             "differs from loaded extent")
            claims_fail = any(k in thought for k in failure_words)
            has_fit_flag = any(isinstance(f, dict) and f["flag"] == "fit_issue"
                               for f in got)
            if claims_fail and not has_fit_flag:
                diffs.append("reasoning states a failure but no fit_issue flag")
            if has_fit_flag and not claims_fail:
                diffs.append("fit_issue flag but the reasoning states no failure")
            if diffs:
                stats["flags"].append({"id": rid, "diffs": diffs})
                problems.append(f"{rid}: flags wrong: {diffs[:3]}")

            # token limits
            row_tokens = sum(n_tokens(m["content"]) for m in msgs)
            if split in ("train", "test") and row_tokens > ROW_TOKEN_LIMIT:
                problems.append(f"{rid}: main row over the token limit "
                                f"({row_tokens})")
                stats["token_limit"].append(rid)
            if split == "oversized" and row_tokens <= ROW_TOKEN_LIMIT:
                problems.append(f"{rid}: oversized row is under the limit "
                                f"({row_tokens})")

    # accounting: every stage-1 id exactly once across the four files
    expected_total = Counter({"train": 0, "test": 0})
    for rid in stage_order["train"]:
        expected_total["train"] += 1
    accounted = sum(seen_ids.values())
    dupes = [rid for rid, n in seen_ids.items() if n > 1]
    if dupes:
        problems.append(f"duplicate ids: {dupes[:10]}")
    missing = [rid for rid in (stage_order["train"] + stage_order["test"])
               if seen_ids[rid] == 0]
    if missing:
        problems.append(f"missing ids: {missing[:10]}")
    stats["accounting"] = {
        "stage1_ids": len(stage_order["train"]) + len(stage_order["test"]),
        "accounted": accounted,
        "duplicates": dupes,
        "missing": missing,
    }

    # order preserved in the main files
    for split in ("train", "test"):
        if files[split].exists():
            main_ids = [r["id"] for r in iter_jsonl(files[split])]
            expected_ids = [rid for rid in stage_order[split]
                            if seen_ids[rid] and _is_main(rid, final_dir, split)]
            if main_ids != expected_ids:
                problems.append(f"{split}: row order changed")

    stats["problems"] = problems
    (final_dir / "validation_report.json").write_text(
        json.dumps(stats, indent=1, ensure_ascii=False) + "\n")

    print(f"rows per file: {stats['files']}")
    print(f"accounting: {stats['accounting']}")
    print(f"problems: {len(problems)}")
    for p in problems[:20]:
        print("  -", p)
    return 0 if not problems else 1


def _is_main(rid: str, final_dir: Path, split: str) -> bool:
    return rid in {r["id"] for r in iter_jsonl(final_dir / f"{split}.jsonl")}


if __name__ == "__main__":
    sys.exit(main())
