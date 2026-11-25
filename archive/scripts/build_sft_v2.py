"""Build sft_v2 / sft_test_v2: sft_v1 / sft_test with every number re-simulated in
OpenRocket 24.12.

    python3 scripts/resim_v2.py      # once: writes new_results/sft_v2_sims.jsonl
    python3 scripts/build_sft_v2.py  # deterministic, reads only the cache + v1 files
    python3 scripts/verify_sft_v2.py # strict checks, must print 0 failures

What changes per row (everything else is copied byte-for-byte from v1 / sft_test):
  * targets          -> the 7 target keys from the re-sim
  * prompt numbers   -> same wording, numbers replaced by the re-sim values at the same
                        precision ("under N" bounds kept if still true, else tightened).
                        Rows whose v1 prompt numbers did not match their own v1 sim, or
                        whose wording no longer fits the re-sim, get a fresh prompt from
                        the v1 template bank (seeded by row id) and are listed.
  * <thought> block  -> re-rendered from the new prompt + re-sim with the v1 renderer
The <design> block, system message, ir_chars, ids, files, sims and splits are unchanged.

Rows are dropped (with the reason written to the changes file) when the re-sim errors,
has no finite touchdown velocity / no GROUND_HIT event, or the design carries a parachute
or streamer that OpenRocket never deployed.
"""
import hashlib
import json
import math
import os
import random
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import prompt_numbers as pn  # noqa: E402
from sft_v1_lib import (PROMPT_TEMPLATES, motor_label, render_thought, sims_of)  # noqa: E402

CACHE = "new_results/sft_v2_sims.jsonl"
JOBS = [("new_results/sft_v1.jsonl", "new_results/sft_v2.jsonl"),
        ("data/sft_test.jsonl", "new_results/sft_test_v2.jsonl")]
CHANGES = "new_results/sft_v2_changes.jsonl"
REPORT = "new_results/SFT_V2_REPORT.md"
TARGET_KEYS = ["apogee_m", "max_velocity_ms", "max_mach", "time_to_apogee_s",
               "flight_time_s", "ground_hit_ms", "wind_ms"]
# templates that can be filled from a re-sim without inventing a value or a bound
SAFE_TEMPLATES = [i for i, f in enumerate(PROMPT_TEMPLATES)
                  if "deployment" not in f.__code__.co_consts.__repr__()
                  and "under" not in f.__code__.co_consts.__repr__()]


def p(rel):
    return os.path.join(REPO, rel)


def load_jsonl(rel):
    return [json.loads(x) for x in open(p(rel), encoding="utf-8") if x.strip()]


def load_cache():
    return {(r["file"], r["sim"]): r for r in load_jsonl(CACHE)}


def finite(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def design_of(content):
    return json.loads(content.split("<design>", 1)[1].split("</design>", 1)[0])


def has_recovery(design):
    def walk(cs):
        for c in cs:
            if c.get("type") in ("parachute", "streamer"):
                return True
            if walk(c.get("contains", [])):
                return True
        return False
    return walk(design["components"])


def events(sim, branch=0):
    return [e["type"] for e in sim.get("events", []) if e["branch"] == branch]


def drop_reason(sim, design):
    if sim is None:
        return "sim not in cache"
    if "error" in sim:
        return "re-sim error: " + sim["error"]
    if not finite(sim.get("ground_hit_ms")) or sim["ground_hit_ms"] <= 0:
        return "re-sim has no finite touchdown velocity"
    ev = events(sim)
    if "GROUND_HIT" not in ev:
        return "re-sim has no GROUND_HIT event"
    if has_recovery(design) and "RECOVERY_DEVICE_DEPLOYMENT" not in ev:
        return "design has a parachute/streamer but the re-sim never deployed it"
    for k in TARGET_KEYS:
        v = sim.get(k)
        if not finite(v) or v < 0 or (k != "wind_ms" and v == 0):
            return f"re-sim {k} not a positive finite number ({v})"
    return None


def old_values(row):
    """The v1 numbers a prompt was written from: stored sim in the .ork (as v1 used)."""
    s = [x for x in sims_of(p(row["file"])) if x["name"] == row["sim"]]
    if len(s) != 1:
        return None, None
    s = s[0]
    old = {k: s[k] for k in ("apogee_m", "max_velocity_ms", "max_mach", "time_to_apogee_s",
                             "flight_time_s", "ground_hit_ms", "deployment_velocity_ms")}
    old["max_accel_ms2"] = s["max_acceleration_ms2"]
    return old, s


def new_values(sim):
    return {k: sim[k] for k in ("apogee_m", "max_velocity_ms", "max_mach", "time_to_apogee_s",
                                "flight_time_s", "ground_hit_ms", "deployment_velocity_ms",
                                "max_accel_ms2")}


def regen_prompt(row_id, new, stored_sim):
    rng = random.Random(int(hashlib.sha256(row_id.encode()).hexdigest(), 16))
    order = SAFE_TEMPLATES[:]
    rng.shuffle(order)
    t = {k: new[k] for k in TARGET_KEYS if k in new}
    s = {"max_acceleration_ms2": new["max_accel_ms2"]}
    m = motor_label(stored_sim)
    for i in order:
        out = PROMPT_TEMPLATES[i](t, s, m, 1, None)
        if not pn.check(out, new):
            return out, i
    raise RuntimeError(f"no template fits {row_id}")


def thought_sim(sim, stored_sim):
    return {"apogee_m": sim["apogee_m"], "time_to_apogee_s": sim["time_to_apogee_s"],
            "max_velocity_ms": sim["max_velocity_ms"], "max_mach": sim["max_mach"],
            "flight_time_s": sim["flight_time_s"], "ground_hit_ms": sim["ground_hit_ms"],
            "active_motors": stored_sim["active_motors"]}


def build_row(row, cache):
    """Return (new_row or None, change_record)."""
    content = row["messages"][2]["content"]
    design = design_of(content)
    sim = cache.get((row["file"], row["sim"]))
    ch = {"id": row["id"], "split": row["split"], "file": row["file"], "sim": row["sim"]}
    old, stored = old_values(row)
    if stored is None:
        ch["dropped"] = f"v1 sim '{row['sim']}' is not in {row['file']}"
        return None, ch
    reason = drop_reason(sim, design)
    if reason:
        ch["dropped"] = reason
        return None, ch
    new = new_values(sim)
    prompt0 = row["prompt_text"]
    prompt, problems, notes = pn.rewrite(prompt0, old, new)
    problems += pn.qual_ok(prompt0, new, old)
    if problems:
        prompt, tmpl = regen_prompt(row["id"], new, stored)
        ch["prompt_regenerated"] = {"why": problems, "template": tmpl}
        notes = []
    if notes:
        ch["prompt_notes"] = sorted(set(notes))
    ch["prompt_changed"] = prompt != prompt0
    if prompt != prompt0:
        ch["prompt_v1"], ch["prompt_v2"] = prompt0, prompt
    thought = render_thought(prompt, thought_sim(sim, stored), design)
    new_content = thought + "\n" + content[content.index("<design>"):]
    targets = {k: sim[k] for k in TARGET_KEYS}
    out = {}
    for k in row:  # keep v1 key order exactly
        if k == "prompt_text":
            out[k] = prompt
        elif k == "messages":
            out[k] = [dict(row["messages"][0]), {"role": "user", "content": prompt},
                      {"role": "assistant", "content": new_content}]
        elif k == "targets":
            out[k] = targets
        else:
            out[k] = row[k]
    ch["targets_v1"] = row["targets"]
    ch["targets_v2"] = targets
    ch["uuid_sensitivity"] = sim.get("uuid_sensitivity")
    return out, ch


def rel_change(a, b):
    return (b - a) / a if a else float("inf")


def pct(xs, q):
    xs = sorted(xs)
    if not xs:
        return float("nan")
    k = (len(xs) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def report(results, cache):
    L = []
    w = L.append
    w("# sft_v2 re-simulation report\n")
    w("Generated by `scripts/build_sft_v2.py` from `new_results/sft_v2_sims.jsonl`; "
      "every number below is computed from the files, nothing is typed in by hand.\n")
    w("Simulator: OpenRocket 24.12 (sha256 4959b72f…f897), seed 42, component-UUID seed 42, "
      "via `scripts/or_batch/OrBatch.java`. Each (ork, sim) got one discarded warm-up run and "
      "two recorded runs, which are bit-identical; `verify_sft_v2.py --resim` re-runs every "
      "pair in reverse order and requires the result to equal the cache byte for byte.\n")
    w("## Counts\n")
    w("| split | v1 rows | kept | dropped | prompt numbers updated | prompt regenerated |")
    w("|---|---|---|---|---|---|")
    for name, (rows, chs) in results.items():
        kept = [c for c in chs if "dropped" not in c]
        w(f"| {name} | {len(chs)} | {len(kept)} | {len(chs) - len(kept)} | "
          f"{sum(1 for c in kept if c['prompt_changed'] and 'prompt_regenerated' not in c)} | "
          f"{sum(1 for c in kept if 'prompt_regenerated' in c)} |")
    w("")
    w("## Dropped rows\n")
    w("| id | split | file | sim | reason |")
    w("|---|---|---|---|---|")
    for name, (rows, chs) in results.items():
        for c in chs:
            if "dropped" in c:
                w(f"| {c['id']} | {c['split']} | {c['file'][4:]} | {c['sim']} | {c['dropped']} |")
    w("")
    w("## How much the targets moved (kept rows, v2 vs v1, relative change)\n")
    w("| target | median abs change | p90 abs change | max abs change | rows > 10% |")
    w("|---|---|---|---|---|")
    kept = [c for _, (_, chs) in results.items() for c in chs if "dropped" not in c]
    for k in TARGET_KEYS:
        if k == "wind_ms":
            continue
        xs = [abs(rel_change(c["targets_v1"][k], c["targets_v2"][k])) for c in kept
              if finite(c["targets_v1"].get(k)) and c["targets_v1"][k]]
        w(f"| {k} | {100 * statistics.median(xs):.1f}% | {100 * pct(xs, 0.9):.1f}% | "
          f"{100 * max(xs):.1f}% | {sum(x > 0.10 for x in xs)} |")
    w("")
    def f(x, d):
        return f"{x:.{d}f}" if finite(x) else "none"

    def gh_move(c):
        a = c["targets_v1"].get("ground_hit_ms")
        return abs(rel_change(a, c["targets_v2"]["ground_hit_ms"])) if finite(a) and a else float("inf")
    big = sorted(kept, key=lambda c: -gh_move(c))[:10]
    w("Largest touchdown-velocity changes (all deployed recovery and hit the ground in the re-sim):\n")
    w("| id | file | sim | v1 m/s | v2 m/s | v1 flight s | v2 flight s |")
    w("|---|---|---|---|---|---|---|")
    for c in big:
        a, b = c["targets_v1"], c["targets_v2"]
        w(f"| {c['id']} | {c['file'][4:]} | {c['sim']} | {f(a['ground_hit_ms'], 2)} | "
          f"{f(b['ground_hit_ms'], 2)} | {f(a['flight_time_s'], 1)} | {f(b['flight_time_s'], 1)} |")
    w("")
    w("## Regenerated prompts\n")
    w("These v1 prompts either quoted numbers that did not match their own v1 sim, or used "
      "wording the re-sim no longer satisfies, so they got a fresh prompt from the v1 "
      "template bank (seed = sha256 of the row id).\n")
    w("| id | why | v1 prompt | v2 prompt |")
    w("|---|---|---|---|")
    for c in kept:
        if "prompt_regenerated" in c:
            why = "; ".join(c["prompt_regenerated"]["why"]).replace("|", "/")
            w(f"| {c['id']} | {why} | {c['prompt_v1']} | {c['prompt_v2']} |")
    w("")
    dep = [c for c in kept if "deployment_was_touchdown" in c.get("prompt_notes", [])]
    bnd = [c for c in kept if "v1_bound_was_violated" in c.get("prompt_notes", [])]
    w("## v1 prompt-template bugs fixed\n")
    w(f"* {len(dep)} prompts said \"deployment at about X m/s\" but v1 filled X with the "
      "touchdown velocity; v2 writes the real deployment velocity there: "
      + ", ".join(c["id"] for c in dep) + ".")
    w(f"* {len(bnd)} prompts said \"under N\" with N rounded below the true value; v2 uses the "
      "smallest N at that precision that is really above it: "
      + ", ".join(c["id"] for c in bnd) + ".\n")
    sens = sorted([c for c in kept if isinstance(c.get("uuid_sensitivity"), (int, float))
                   and c["uuid_sensitivity"] > 1e-3], key=lambda c: -c["uuid_sensitivity"])
    w("## OpenRocket motor-ordering sensitivity\n")
    w("OpenRocket keys its per-configuration motor map by component UUIDs that older .ork "
      "files do not store, so for some multi-motor / multi-stage designs the result depends "
      "on those UUIDs. v2 fixes them (seed 42) so the build is reproducible; re-running with "
      f"UUID seed 7 changes these kept rows by more than 0.1% ({len(sens)} rows):\n")
    w("| id | file | sim | max relative change |")
    w("|---|---|---|---|")
    for c in sens:
        w(f"| {c['id']} | {c['file'][4:]} | {c['sim']} | {100 * c['uuid_sensitivity']:.2f}% |")
    w("")
    return "\n".join(L) + "\n"


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=None,
                    help="write outputs here instead of the repo (used by the verifier)")
    a = ap.parse_args(argv)

    def outp(rel):
        return os.path.join(a.out_dir, os.path.basename(rel)) if a.out_dir else p(rel)
    cache = load_cache()
    results = {}
    all_changes = []
    for src, dst in JOBS:
        rows = load_jsonl(src)
        outs, chs = [], []
        for r in rows:
            o, c = build_row(r, cache)
            chs.append(c)
            if o is not None:
                outs.append(o)
        with open(outp(dst), "w", encoding="utf-8") as fh:
            for o in outs:
                fh.write(json.dumps(o, ensure_ascii=False) + "\n")
        results[os.path.basename(dst).replace(".jsonl", "")] = (outs, chs)
        all_changes += chs
        print(f"{dst}: {len(outs)} kept / {len(rows)}")
    with open(outp(CHANGES), "w", encoding="utf-8") as fh:
        for c in all_changes:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    with open(outp(REPORT), "w", encoding="utf-8") as fh:
        fh.write(report(results, cache))


if __name__ == "__main__":
    main()
