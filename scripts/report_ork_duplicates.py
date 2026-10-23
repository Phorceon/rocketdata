"""Report repetition among all .ork files (report only; nothing is modified).

Three kinds:
  1. EXACT  - identical file bytes (same sha256), different names.
  2. SAME   - identical component/dimension fingerprint (design IR equal) but the
              files differ in name, sims, or metadata.
  3. NEAR   - same airframe (geometry of structure: tubes/nose/transitions/fins/mounts)
              with only small changes (motor, mass components, or recovery devices).

Writes data/ORK_DUPLICATES_REPORT.md and data/ork_duplicates.csv.
"""
import csv
import hashlib
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from ork_design import build_design, fingerprint, load_bytes  # noqa: E402
from ork_family import build_all as build_families, stem_family  # noqa: E402
from xml.etree import ElementTree as ET  # noqa: E402

ORK = os.path.join(REPO, "ork")
STRUCT_TYPES = {"nosecone", "bodytube", "transition", "trapezoidfin",
                "freeformfinset", "ellipticalfin", "tubefin", "innertube",
                "centeringring", "bulkhead", "engineblock", "launchlug", "pod_set"}


def airframe_signature(comps):
    """Geometry-only signature: structural components' type+name+dims, in order.
    Ignores motors, mass components and recovery devices (those are the 'small'
    changes allowed under NEAR-duplicate)."""
    parts = []

    def rec(c):
        if c["type"] in STRUCT_TYPES:
            sig = [c["type"], c.get("name")]
            for k in ("length_m", "outer_d_m", "base_radius_m", "wall_thickness_m",
                      "fore_d_m", "aft_d_m", "root_chord_m", "tip_chord_m", "span_m",
                      "sweep_m", "fin_count", "count"):
                if k in c:
                    sig.append((k, c[k]))
            parts.append(tuple(sig))
            for ch in c.get("contains", []):
                rec(ch)
        else:
            for ch in c.get("contains", []):
                rec(ch)

    for c in comps:
        rec(c)
    return hashlib.sha1(repr(parts).encode("utf-8")).hexdigest()


def motors_sig(comps):
    out = []

    def rec(c):
        for m in c.get("motors", []):
            out.append((m["manufacturer"], m["designation"]))
        for ch in c.get("contains", []):
            rec(ch)
    for c in comps:
        rec(c)
    seen, uniq = set(), []
    for m in out:
        if m not in seen:
            seen.add(m)
            uniq.append(m)
    return uniq


def mass_sig(comps):
    out = []

    def rec(c):
        if c["type"] == "masscomponent":
            out.append((c.get("name"), c.get("mass_kg"), c.get("kind")))
        for ch in c.get("contains", []):
            rec(ch)
    for c in comps:
        rec(c)
    return out


def recovery_sig(comps):
    out = []

    def rec(c):
        if c["type"] in ("parachute", "streamer"):
            out.append((c["type"], c.get("name"), c.get("diameter_m") or c.get("strip_length_m")))
        for ch in c.get("contains", []):
            rec(ch)
    for c in comps:
        rec(c)
    return out


def n_sims(path):
    root = ET.fromstring(load_bytes(path))
    n = 0
    for sim in root.iter("simulation"):
        fd = sim.find("flightdata")
        if fd is not None and fd.get("maxaltitude") is not None:
            n += 1
    return n


def rocket_name(path):
    root = ET.fromstring(load_bytes(path))
    return root.findtext("rocket/name") or ""


def used_in():
    """file path -> split label."""
    out = {}
    for label, path in (("sft_v0", "data/sft_v0.jsonl"),
                        ("sft_test", "data/sft_test.jsonl"),
                        ("rl_heldout", "data/splits/rl_heldout.jsonl")):
        for line in open(os.path.join(REPO, path), encoding="utf-8"):
            if line.strip():
                out.setdefault(json.loads(line)["file"], set()).add(label)
    return {k: "+".join(sorted(v)) for k, v in out.items()}


def main():
    files = sorted("ork/" + f for f in os.listdir(ORK) if f.lower().endswith(".ork"))
    used = used_in()
    info = {}
    for p in files:
        try:
            b = load_bytes(p)
            comps, _ = build_design(p)
            info[p] = {
                "hash": hashlib.sha256(b).hexdigest(),
                "fp": fingerprint(comps),
                "air": airframe_signature(comps),
                "name": rocket_name(p),
                "motors": motors_sig(comps),
                "mass": mass_sig(comps),
                "rec": recovery_sig(comps),
                "sims": n_sims(p),
                "used": used.get(p, ""),
            }
        except Exception as e:
            info[p] = {"error": str(e)[:120], "used": used.get(p, "")}

    ok = {p: d for p, d in info.items() if "error" not in d}

    # ---- EXACT: same sha256 ----
    by_hash = defaultdict(list)
    for p, d in ok.items():
        by_hash[d["hash"]].append(p)
    exact = {h: fs for h, fs in by_hash.items() if len(fs) > 1}

    # ---- SAME design: same fingerprint ----
    by_fp = defaultdict(list)
    for p, d in ok.items():
        by_fp[d["fp"]].append(p)
    same = {f: fs for f, fs in by_fp.items() if len(fs) > 1}

    # ---- NEAR: same airframe, but not already SAME ----
    by_air = defaultdict(list)
    for p, d in ok.items():
        by_air[d["air"]].append(p)
    near = {}
    for a, fs in by_air.items():
        if len(fs) <= 1:
            continue
        # skip groups whose members are all in one SAME group
        fps = set(info[p]["fp"] for p in fs)
        if len(fps) == 1:
            continue  # that's a SAME group
        near[a] = fs

    # ---- write CSV + report ----
    rows = []
    groups = []

    def diff_summary(fs):
        bits = []
        for p in fs:
            d = info[p]
            bits.append((p, d["name"], d["sims"], d["motors"], d["mass"], d["rec"], d["used"]))
        return bits

    gid = 0
    # EXACT groups
    for h, fs in sorted(exact.items(), key=lambda x: -len(x[1])):
        gid += 1
        keep = pick_keep(fs, info, prefer="split")
        kind = "EXACT"
        groups.append((gid, kind, fs, h, keep))
        for p in fs:
            rows.append([gid, p, kind, info[p]["used"], "keep" if p == keep else "remove"])
    # SAME groups (exclude exact-only)
    for f, fs in sorted(same.items(), key=lambda x: -len(x[1])):
        if len(set(info[p]["hash"] for p in fs)) == 1:
            continue  # pure exact copy, already reported
        gid += 1
        keep = pick_keep(fs, info, prefer="split")
        groups.append((gid, "SAME", fs, f, keep))
        for p in fs:
            rows.append([gid, p, "SAME", info[p]["used"], "keep" if p == keep else "remove"])
    # NEAR groups
    for a, fs in sorted(near.items(), key=lambda x: -len(x[1])):
        gid += 1
        keep = pick_keep(fs, info, prefer="split")
        groups.append((gid, "NEAR", fs, a, keep))
        for p in fs:
            rows.append([gid, p, "NEAR", info[p]["used"], "keep" if p == keep else "remove"])

    # ---- families (stem-prefix OR airframe within ~5%) ----
    fam, fam_members = build_families(files)

    os.makedirs(os.path.join(REPO, "data"), exist_ok=True)
    with open(os.path.join(REPO, "data", "ork_duplicates.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["group_id", "file", "kind", "used_in", "keep_or_remove",
                    "family", "family_size"])
        for r in rows:
            p = r[1]
            w.writerow(r + [os.path.basename(fam.get(p, "")) if fam.get(p) else "",
                            len(fam_members.get(fam.get(p), []))])

    write_report(info, ok, exact, same, near, groups, files, rows,
                 fam, fam_members)
    print("files:", len(files), "distinct designs (fingerprints):", len(set(d["fp"] for d in ok.values())))
    print("EXACT groups:", len(exact), "SAME groups:", sum(1 for f, fs in same.items() if len(set(info[p]['hash'] for p in fs)) > 1), "NEAR groups:", len(near))
    print("families:", len(fam_members), "multi-file families:",
          sum(1 for ms in fam_members.values() if len(ms) > 1))
    print("wrote data/ork_duplicates.csv and data/ORK_DUPLICATES_REPORT.md")


def pick_keep(fs, info, prefer="split"):
    def score(p):
        d = info[p]
        return (1 if d["used"] else 0, d["sims"], -len(p))
    return sorted(fs, key=score, reverse=True)[0]


def write_report(info, ok, exact, same, near, groups, files, rows,
                 fam=None, fam_members=None):
    used_groups = defaultdict(list)
    for gid, kind, fs, key, keep in groups:
        used_groups[kind].append((gid, fs, keep))
    out = []
    out.append("# .ork Duplicate Report\n")
    out.append("Report only: no files were modified, moved, or deleted.\n")
    n_ok = len(ok)
    distinct = len(set(d["fp"] for d in ok.values()))
    out.append(f"- Total files scanned: **{len(files)}**")
    out.append(f"- Parsed: {n_ok}  (unparseable: {len(files) - n_ok})")
    out.append(f"- Distinct designs (fingerprint): **{distinct}**")
    out.append(f"- EXACT groups: {len(exact)}  |  SAME groups: "
               f"{sum(1 for f, fs in same.items() if len(set(info[p]['hash'] for p in fs)) > 1)}  |  "
               f"NEAR groups: {len(near)}\n")
    out.append("## Definitions\n")
    out.append("- **EXACT**: identical file bytes (sha256), different filenames.")
    out.append("- **SAME**: identical design fingerprint (every component, dimension, "
               "name, in order); files differ only in name, stored sims, or metadata.")
    out.append("- **NEAR**: identical *airframe signature* — a geometry-only signature over "
               "structural components (nosecone, bodytube, transition, fin sets, innertube, "
               "centering rings, bulkheads, engine blocks, launch lugs, pods) with the same "
               "names and rounded dimensions — but one or more of the following changed: "
               "**motor configuration, mass components, or recovery devices** (parachutes/streamers). "
               "Nothing else may differ, so 'small' = motor-only, mass-only, and/or recovery-only edits.\n")
    out.append("`used_in` = the splits a file's design appears in: `sft_v0`, `sft_test`, "
               "`rl_heldout`.\n")

    # summary table
    n_remove = sum(1 for r in rows if r[4] == "remove")
    out.append("## Summary\n")
    out.append("| kind | groups | files | keep | remove |")
    out.append("|---|---|---|---|---|")
    for kind in ("EXACT", "SAME", "NEAR"):
        gs = [g for g in groups if g[1] == kind]
        files_in = sum(len(g[2]) for g in gs)
        out.append(f"| {kind} | {len(gs)} | {files_in} | {len(gs)} | {files_in - len(gs)} |")
    out.append(f"| **total** | **{len(groups)}** | "
               f"**{sum(len(g[2]) for g in groups)}** | **{len(groups)}** | **{n_remove}** |")
    out.append("")
    out.append("Keep rule (in priority order): a file already used in a split, then the "
               "one with the most stored sims, then the shortest filename.\n")

    # split-crossing (leakage) groups
    leak = []
    warn = []
    for gid, kind, fs, key, keep in groups:
        in_held = [p for p in fs if "sft_test" in info[p]["used"] or "rl_heldout" in info[p]["used"]]
        in_train = [p for p in fs if "sft_v0" in info[p]["used"]]
        if in_held and in_train:
            leak.append((gid, kind, fs, keep))
        elif in_held:
            warn.append((gid, kind, fs, keep))
    out.append(f"## Test leakage: groups with one copy in a held-out split AND another in sft_v0: {len(leak)}\n")
    for gid, kind, fs, keep in leak:
        out.append(f"- **group {gid}** ({kind}) crosses splits: "
                   + ", ".join(f"`{p}` [{info[p]['used']}]" for p in fs))
    if not leak:
        out.append("- **None.** No group has a member in sft_v0 and a member in "
                   "sft_test/rl_heldout.\n")
    out.append(f"## Warning: held-out files that have an unused near-twin: {len(warn)}\n")
    out.append("These are not leakage today, but the twin must NOT be added to training.\n")
    for gid, kind, fs, keep in warn:
        out.append(f"- **group {gid}** ({kind}): "
                   + ", ".join(f"`{p}` [{info[p]['used'] or 'unused'}]" for p in fs))
    if not warn:
        out.append("- None.")
    out.append("")

    # ---- family leakage ----
    if fam:
        split_of = {}
        for p, d in info.items():
            if d.get("used"):
                split_of.setdefault(fam[p], set()).update(d["used"].split("+"))
        multi = {f: ms for f, ms in fam_members.items() if len(ms) > 1}
        fam_leak = {}
        for f, s in split_of.items():
            held = s & {"sft_test", "rl_heldout"}
            if held and "sft_v0" in s:
                fam_leak[f] = s
        out.append("## Family grouping\n")
        out.append("A **family** = files that are versions/variants of the same rocket, "
                   "combined from two signals (union):")
        out.append("1. same **filename stem** after stripping version/date/sim suffixes "
                   "(e.g. `APEX*`, `ASTRA*`, `Siruis*`, `Argonia_*`, `NASA_Rocket_*`, "
                   "`2024_IREC*`, `RocketV1*`, `IREK*`, `DarkMatter*`, `falconHeavey*`, "
                   "`ASCENSION*`, `Scale_model_Nasa*`); or")
        out.append("2. same **airframe** within ~5% relative tolerance on body diameter, "
                   "total length and fin dimensions (structure counts must match exactly).\n")
        out.append(f"- Families (distinct): **{len(fam_members)}**")
        out.append(f"- Multi-file families: **{len(multi)}** "
                   f"({sum(len(v) for v in multi.values())} files)\n")

        out.append(f"## Family leakage: families with members in BOTH sft_v0 and "
                   f"(sft_test or rl_heldout): {len(fam_leak)}\n")
        if fam_leak:
            out.append("**These inflate the current test/RL score: a training row and its "
                       "test/RL twin are the same rocket.** sft_v1 will exclude the whole "
                       "family from training (see `data/SFT_V1_REPORT.md`).\n")
            for f in sorted(fam_leak, key=lambda x: -len(fam_members[x])):
                s = fam_leak[f]
                out.append(f"- family `{os.path.basename(f)}` — splits: "
                           f"{', '.join(sorted(s))} — {len(fam_members[f])} file(s)")
                for p in sorted(fam_members[f]):
                    d = info[p]
                    out.append(f"  - `{p}` used={d['used'] or '-'} sims={d['sims']}")
        else:
            out.append("- None.")
        out.append("")

        out.append("## Multi-file families\n")
        for f in sorted(multi, key=lambda x: -len(multi[x])):
            labs = []
            for p in sorted(multi[f]):
                d = info[p]
                if d["used"]:
                    labs.append(f"{p} [{d['used']}]")
            head = f"### {os.path.basename(f)} ({len(multi[f])} files)"
            if labs:
                head += "  — used: " + ", ".join(labs)
            out.append(head)
            for p in sorted(multi[f]):
                d = info[p]
                out.append(f"- `{p}`  name={d['name']!r} sims={d['sims']} used={d['used'] or '-'}")
            out.append("")

    for label, kind in (("EXACT copies", "EXACT"), ("Same design (fingerprint)", "SAME"),
                        ("Near-duplicates", "NEAR")):
        gs = [g for g in groups if g[1] == kind]
        out.append(f"## {label}: {len(gs)} group(s)\n")
        for gid, _, fs, key, keep in sorted(gs, key=lambda g: -len(g[2]))[:200]:
            out.append(f"### group {gid} ({len(fs)} files) — keep `{keep}`")
            for p in sorted(fs):
                d = info[p]
                out.append(f"- `{p}`  name={d['name']!r} sims={d['sims']} used={d['used'] or '-'}"
                           f"  motors={[m[1] for m in d['motors']]}")
            if len(fs) > 1:
                def norm_mass(p):
                    return tuple(sorted((n, m, k) for n, m, k in info[p]["mass"]))
                diffs = []
                if len(set(tuple(map(tuple, info[p]["motors"])) for p in fs)) > 1:
                    diffs.append("motors")
                if len(set(norm_mass(p) for p in fs)) > 1:
                    diffs.append("mass components")
                if len(set(repr(info[p]["rec"]) for p in fs)) > 1:
                    diffs.append("recovery")
                if len(set(info[p]["sims"] for p in fs)) > 1:
                    diffs.append("sims")
                if len(set(info[p]["name"] for p in fs)) > 1:
                    diffs.append("rocket name")
                out.append(f"  - differs in: {', '.join(diffs) if diffs else 'metadata only'}")
            out.append("")

    # generic Rocket fixtures (informational only; NOT an exclusion list)
    gen = [p for p, d in ok.items() if d["name"] in ("Rocket", "rocket")]
    out.append(f"## Files whose internal rocket name is `Rocket` (informational): {len(gen)}\n")
    out.append("`Rocket` is OpenRocket's default name, so this list mixes repository "
               "test fixtures with real designs (Argonia, NASA_Rocket, *_L1, Big_Red, "
               "etc.). **These files are NOT excluded on the basis of this name** — "
               "exclusion is by family/leakage only.\n")
    for p in sorted(gen):
        d = info[p]
        out.append(f"- `{p}`  fp={d['fp'][:10]} sims={d['sims']} used={d['used'] or '-'}")
    out.append("")

    with open(os.path.join(REPO, "data", "ORK_DUPLICATES_REPORT.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(out))


if __name__ == "__main__":
    main()
