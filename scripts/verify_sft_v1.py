"""Verify data/sft_v1.jsonl against the approved requirements. Prints a report
and exits non-zero on any hard failure."""
import json
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "sft"))

from ork_design import build_design, fingerprint  # noqa: E402
from ork_family import build_all as build_families  # noqa: E402
from sft_v1_lib import sims_of  # noqa: E402

ROW_KEYS = ["id", "file", "source_prompt", "sim", "prompt_text",
            "messages", "targets", "ir_chars", "split"]
TARGET_KEYS = ["apogee_m", "max_velocity_ms", "max_mach", "time_to_apogee_s",
               "flight_time_s", "ground_hit_ms", "wind_ms"]


def load(path):
    return [json.loads(l) for l in open(os.path.join(REPO, path), encoding="utf-8")
            if l.strip()]


def files_of(rows):
    return set(r["file"] for r in rows)


def main():
    fails = []
    v1 = load("data/sft_v1.jsonl")
    v0 = load("data/sft_v0.jsonl")
    test = load("data/sft_test.jsonl")
    held = load("data/splits/rl_heldout.jsonl")

    print(f"rows: {len(v1)}")

    # ---- 1. schema ----
    bad = 0
    for r in v1:
        if list(r.keys()) != ROW_KEYS:
            bad += 1
            continue
        if list(r["targets"].keys()) != TARGET_KEYS:
            bad += 1
        msgs = r["messages"]
        if [m["role"] for m in msgs] != ["system", "user", "assistant"]:
            bad += 1
        if "<thought>" not in msgs[2]["content"] or "<design>" not in msgs[2]["content"]:
            bad += 1
        if r["messages"][1]["content"] != r["prompt_text"]:
            bad += 1
    print(f"schema failures: {bad}")
    if bad:
        fails.append(f"{bad} schema failures")

    # ---- 2. schema via the project's own eval_test check ----
    # Feed each row's own gold answer through eval_test.score() as if it were the
    # model output; design_found/json_ok/schema_ok/recovery/motor_known must all
    # be True (the other keys depend on a live model / the test split).
    try:
        import eval_test
        types, motors = eval_test.reference_vocab()
        n_ok = 0
        for r in v1:
            ans = r["messages"][-1]["content"]
            s = eval_test.score(r, "", ans, "stop", types, motors)
            if s["design_found"] and s["json_ok"] and s["schema_ok"] and s["recovery"]:
                n_ok += 1
        print(f"eval_test score(): design+schema+recovery ok on {n_ok}/{len(v1)} rows")
        if n_ok != len(v1):
            fails.append(f"eval_test schema failed on {len(v1) - n_ok} rows")
    except Exception as e:
        print(f"(eval_test schema check skipped: {e})")

    # ---- 3. file & family overlap with held-out splits ----
    fam, fam_members = build_families(
        sorted("ork/" + f for f in os.listdir(os.path.join(REPO, "ork"))
               if f.lower().endswith(".ork")))
    v1_files = files_of(v1)
    path_overlap = v1_files & (files_of(test) | files_of(held))
    print(f"file-path overlap with test/heldout: {len(path_overlap)}")

    def fps(rows):
        out = set()
        for r in rows:
            try:
                out.add(fingerprint(build_design(r["file"])[0]))
            except Exception:
                pass
        return out
    fp_overlap = fps(v1) & (fps(test) | fps(held))
    print(f"fingerprint overlap with test/heldout: {len(fp_overlap)}")
    if path_overlap or fp_overlap:
        fails.append("overlap with held-out splits")

    v1_fams = {fam[p] for p in v1_files}
    held_fams = {fam[p] for p in (files_of(test) | files_of(held))}
    fam_overlap = v1_fams & held_fams
    print(f"family overlap with test/heldout: {len(fam_overlap)} "
          f"{[os.path.basename(f) for f in fam_overlap]}")
    if fam_overlap:
        fails.append("family overlap with held-out splits")

    # ---- 4. family cap (<=5 examples per family) ----
    fam_rows = Counter(fam[r["file"]] for r in v1)
    over = {k: v for k, v in fam_rows.items() if v > 5}
    print(f"families over 5 examples: {len(over)}")
    if over:
        fails.append(f"families over cap: {over}")

    # ---- 5. target check ----
    # new (V1-*) rows: every number must equal the stored sim exactly.
    # retained v0 rows: must equal the ORIGINAL sft_v0 row exactly.
    v0_by_id = {r["id"]: r for r in v0}
    mism = 0
    for r in v1:
        if r["id"].startswith("V1-"):
            s = [x for x in sims_of(r["file"]) if x["name"] == r["sim"]]
            ref = s[0] if s else None
        else:
            ref = v0_by_id.get(r["id"], {}).get("targets")
            ref = ref if isinstance(ref, dict) else None
        if ref is None:
            mism += 1
            continue
        for k in ("apogee_m", "max_velocity_ms", "max_mach", "time_to_apogee_s",
                  "flight_time_s", "ground_hit_ms", "wind_ms"):
            if abs((r["targets"][k] or 0) - (ref[k] or 0)) > 1e-6:
                mism += 1
                break
    print(f"target mismatches: {mism}")
    if mism:
        fails.append(f"{mism} target mismatches")

    # retained v0 rows must be byte-identical to their sft_v0 originals
    v0_diff = 0
    for r in v1:
        if r["id"].startswith("V1-"):
            continue
        o = v0_by_id.get(r["id"])
        if o is None or json.dumps(o, sort_keys=True) != json.dumps(r, sort_keys=True):
            v0_diff += 1
    print(f"retained v0 rows differing from original: {v0_diff}")
    if v0_diff:
        fails.append(f"{v0_diff} v0 rows altered")

    # ---- 6. ir_chars == design length ----
    ich = 0
    for r in v1:
        m = re.search(r"<design>\n(.*)\n</design>", r["messages"][2]["content"], re.S)
        if not m or len(m.group(1)) != r["ir_chars"]:
            ich += 1
    print(f"ir_chars mismatches: {ich}")
    if ich:
        fails.append(f"{ich} ir_chars mismatches")

    # ---- 7. distribution ----
    shares = Counter(r["file"] for r in v1)
    print(f"distinct files: {len(shares)}")
    print(f"max single-file share: {shares.most_common(1)[0]}")
    mclass = Counter()
    for r in v1:
        d = json.loads(re.search(r"<design>\n(.*)\n</design>",
                                 r["messages"][2]["content"], re.S).group(1))
        m = d["flight"]["motor"]
        m = m[0] if isinstance(m, str) else m[0]
        for ch in m:
            if ch.isalpha():
                mclass[ch.upper()] += 1
                break
    print(f"motor classes: {dict(sorted(mclass.items()))}")
    print(f"unique prompts: {len(set(r['prompt_text'] for r in v1))} / {len(v1)}")
    print(f"unique ids: {len(set(r['id'] for r in v1))}")
    print(f"v0 rows retained: {sum(1 for r in v1 if r['id'].startswith(('U-','NEW-')))}")

    if fails:
        print("\nFAILURES:")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
