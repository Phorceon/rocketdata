"""Strict checks for sft_v2 / sft_test_v2. Prints every failure; exit code 1 if any.

    python3 scripts/verify_sft_v2.py            # all checks against the committed sim cache
    python3 scripts/verify_sft_v2.py --resim    # also re-run OpenRocket (pairs in reverse
                                                # order) and require the fresh sims to equal
                                                # the cache bit-for-bit (needs a JDK, ~10 min)
    python3 scripts/verify_sft_v2.py --fresh-cache path.jsonl   # same, using an existing run

Nothing here is tolerance-tuned to make the data pass: numbers must equal the cache
exactly, prompts must display those numbers at their own precision, and the design
block must be byte-identical to v1. Do not loosen a check to make it pass; fix the
builder instead.

Two v1 problems live inside the byte-identical design block and so cannot change in v2:
eval_test motor_known (design motor not in data/catalog.sqlite) and motor_match (prompt
motor differs from the design motor). They are printed as INHERITED with their ids, and
a v2 row may only fail them if its v1 row failed them too.
"""
import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "sft"))

import build_sft_v2 as B  # noqa: E402
import prompt_numbers as pn  # noqa: E402
from sft_v1_lib import SYSTEM_MSG, render_thought  # noqa: E402

ROW_KEYS = ["id", "file", "source_prompt", "sim", "prompt_text", "messages", "targets",
            "ir_chars", "split"]
COPIED = ["id", "file", "source_prompt", "sim", "ir_chars", "split"]
EVAL_MUST = ["design_found", "json_ok", "schema_ok", "recovery"]
EVAL_INHERIT = ["motor_known", "motor_match"]

FAILS = []


def fail(msg):
    FAILS.append(msg)


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--resim", action="store_true")
    ap.add_argument("--fresh-cache")
    a = ap.parse_args()

    cache = B.load_cache()
    cache_rows = B.load_jsonl(B.CACHE)
    changes = {c["id"]: c for c in B.load_jsonl(B.CHANGES)}
    import eval_test
    types, motors = eval_test.reference_vocab()
    inherited = {k: [] for k in EVAL_INHERIT}
    counts = {}

    # ---- 0. sim cache itself ----
    if len(cache) != len(cache_rows):
        fail("sim cache has duplicate (file, sim) pairs")
    for r in cache_rows:
        if r.get("seed") != B_SEED or r.get("uuid_seed") != B_UUID:
            fail(f"cache {r['file']} / {r['sim']}: seed/uuid_seed not {B_SEED}/{B_UUID}")

    outputs = {}
    for src, dst in B.JOBS:
        srows = B.load_jsonl(src)
        vrows = B.load_jsonl(dst)
        outputs[dst] = vrows
        sby = {r["id"]: r for r in srows}
        name = os.path.basename(dst)
        if len(sby) != len(srows):
            fail(f"{src}: duplicate ids")
        ids = [r["id"] for r in vrows]
        if len(set(ids)) != len(ids):
            fail(f"{name}: duplicate ids")
        if ids != [r["id"] for r in srows if r["id"] in set(ids)]:
            fail(f"{name}: row order differs from {src}")

        # ---- 1. every source row is kept or dropped for a real, re-derivable reason ----
        for r in srows:
            c = changes.get(r["id"])
            if c is None:
                fail(f"{r['id']}: missing from {B.CHANGES}")
                continue
            design = B.design_of(r["messages"][2]["content"])
            _, stored = B.old_values(r)
            want = (f"v1 sim '{r['sim']}' is not in {r['file']}" if stored is None
                    else B.drop_reason(cache.get((r["file"], r["sim"])), design))
            if (r["id"] in ids) == bool(want):
                fail(f"{r['id']}: kept={r['id'] in ids} but drop rule says {want!r}")
            if c.get("dropped") != want:
                fail(f"{r['id']}: changes file says dropped={c.get('dropped')!r}, rule says {want!r}")

        for v in vrows:
            rid = v["id"]
            r = sby.get(rid)
            if r is None:
                fail(f"{name} {rid}: id not in {src}")
                continue
            # ---- 2. schema / copied fields ----
            if list(v.keys()) != ROW_KEYS:
                fail(f"{rid}: keys {list(v.keys())}")
                continue
            for k in COPIED:
                if v[k] != r[k]:
                    fail(f"{rid}: {k} changed from v1")
            msgs = v["messages"]
            if [m.get("role") for m in msgs] != ["system", "user", "assistant"] or \
                    any(list(m.keys()) != ["role", "content"] for m in msgs):
                fail(f"{rid}: message structure")
                continue
            if msgs[0] != r["messages"][0] or msgs[0]["content"] != SYSTEM_MSG:
                fail(f"{rid}: system message changed")
            if msgs[1]["content"] != v["prompt_text"]:
                fail(f"{rid}: user message != prompt_text")
            content, vcontent = r["messages"][2]["content"], msgs[2]["content"]
            if "<design>" not in vcontent or \
                    vcontent[vcontent.index("<design>"):] != content[content.index("<design>"):]:
                fail(f"{rid}: design block not byte-identical to v1")
                continue
            design = B.design_of(vcontent)

            # ---- 3. targets == cache, exactly ----
            sim = cache.get((v["file"], v["sim"]))
            if sim is None or "error" in sim:
                fail(f"{rid}: no usable sim in cache")
                continue
            if list(v["targets"].keys()) != B.TARGET_KEYS:
                fail(f"{rid}: target keys {list(v['targets'].keys())}")
            for k in B.TARGET_KEYS:
                x = v["targets"].get(k)
                if not B.finite(x) or x < 0 or (k != "wind_ms" and x == 0):
                    fail(f"{rid}: target {k}={x} not positive finite")
                if x != sim.get(k):
                    fail(f"{rid}: target {k}={x} != cache {sim.get(k)}")

            # ---- 4. flight events ----
            ev = B.events(sim)
            if "GROUND_HIT" not in ev:
                fail(f"{rid}: no GROUND_HIT event")
            if B.has_recovery(design) and "RECOVERY_DEVICE_DEPLOYMENT" not in ev:
                fail(f"{rid}: recovery in design but never deployed")
            if "LIFTOFF" not in ev or "APOGEE" not in ev:
                fail(f"{rid}: missing LIFTOFF/APOGEE event")

            # ---- 5. prompt: every number displays the v2 value ----
            old, stored = B.old_values(r)
            new = B.new_values(sim)
            errs = pn.check(v["prompt_text"], new, old)
            for e in errs:
                fail(f"{rid}: prompt: {e} | {v['prompt_text']}")
            c = changes[rid]
            if "prompt_regenerated" not in c:
                # wording kept: the prompt must be v1's prompt with only number tokens changed
                t1, _ = pn.tokens(r["prompt_text"])
                t2, _ = pn.tokens(v["prompt_text"])
                skel = lambda s, ts: "".join(  # noqa: E731
                    s[(ts[i - 1][1] if i else 0):ts[i][0]] + "\0" for i in range(len(ts))) + \
                    s[(ts[-1][1] if ts else 0):]
                if len(t1) != len(t2) or skel(r["prompt_text"], t1) != skel(v["prompt_text"], t2):
                    fail(f"{rid}: wording changed beyond numbers: {r['prompt_text']!r} -> {v['prompt_text']!r}")
                if [t[4] for t in t1] != [t[4] for t in t2]:
                    fail(f"{rid}: number roles changed")
            else:
                if c["prompt_v2"] != v["prompt_text"]:
                    fail(f"{rid}: regenerated prompt does not match changes file")

            # ---- 6. thought is exactly the v1 renderer on (prompt, re-sim, design) ----
            th = render_thought(v["prompt_text"], B.thought_sim(sim, stored), design)
            if vcontent != th + "\n" + content[content.index("<design>"):]:
                fail(f"{rid}: assistant content != rendered thought + v1 design")

            # ---- 7. project eval (gold answer scored as model output) ----
            s2 = eval_test.score(v, "", vcontent, "stop", types, motors)
            s1 = eval_test.score(r, "", content, "stop", types, motors)
            for k in EVAL_MUST:
                if not s2[k]:
                    fail(f"{rid}: eval_test {k} False")
            if s2["claim_vs_ask"] is False:
                fail(f"{rid}: eval_test claim_vs_ask False (asked {s2['asked_apogee_m']}, "
                     f"claimed {s2['claimed_apogee_m']})")
            for k in EVAL_INHERIT:
                if s2[k] is False:
                    if s1[k] is False:
                        inherited[k].append(rid)
                    else:
                        fail(f"{rid}: eval_test {k} False in v2 but True in v1")
            # ---- 8. builder reproduces this row exactly ----
            o, _ = B.build_row(r, cache)
            if json.dumps(o, ensure_ascii=False) != json.dumps(v, ensure_ascii=False):
                fail(f"{rid}: row differs from builder output")
        counts[name] = len(vrows)

    # ---- 9. files: serialization, overlap ----
    for dst, rows in outputs.items():
        text = open(B.p(dst), encoding="utf-8").read()
        if text != "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows):
            fail(f"{dst}: not canonical one-row-per-line JSON")
    tr = {r["file"] for r in outputs[B.JOBS[0][1]]}
    te = {r["file"] for r in outputs[B.JOBS[1][1]]}
    rl = {r["file"] for r in B.load_jsonl("data/splits/rl_heldout.jsonl")}
    if tr & te or tr & rl or te & rl:
        fail(f"file overlap train/test/rl: {sorted(tr & te)} {sorted(tr & rl)} {sorted(te & rl)}")
    from ork_family import build_all
    allork = sorted("ork/" + f for f in os.listdir(B.p("ork")) if f.lower().endswith(".ork"))
    fam, _ = build_all(allork)
    ftr = {fam[x] for x in tr}
    fho = {fam[x] for x in te | rl if x in fam}
    if ftr & fho:
        fail(f"family overlap train vs test/rl: {sorted(ftr & fho)}")

    # ---- 10. deterministic build: two fresh processes, same bytes as committed ----
    with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
        for d, hs in ((d1, "1"), (d2, "12345")):
            subprocess.run([sys.executable, os.path.join(HERE, "build_sft_v2.py"), "--out-dir", d],
                           check=True, capture_output=True, env=dict(os.environ, PYTHONHASHSEED=hs))
        for rel in [dst for _, dst in B.JOBS] + [B.CHANGES, B.REPORT]:
            b = os.path.basename(rel)
            h0, h1, h2 = sha(B.p(rel)), sha(os.path.join(d1, b)), sha(os.path.join(d2, b))
            if not h0 == h1 == h2:
                fail(f"{rel}: committed file is not what the builder produces "
                     f"({h0[:12]} / {h1[:12]} / {h2[:12]})")

    # ---- 11. report counts match the files ----
    rep = open(B.p(B.REPORT), encoding="utf-8").read()
    for name, n in counts.items():
        line = [x for x in rep.splitlines() if x.startswith(f"| {name.replace('.jsonl', '')} |")]
        if len(line) != 1 or line[0].split("|")[3].strip() != str(n):
            fail(f"report kept-count for {name} does not match file ({n})")

    # ---- 12. optional: fresh OpenRocket run equals the cache ----
    fresh = a.fresh_cache
    if a.resim:
        fresh = os.path.join(tempfile.mkdtemp(), "fresh.jsonl")
        # reverse order: proves results do not depend on what the JVM simulated before
        subprocess.run([sys.executable, os.path.join(HERE, "resim_v2.py"), "--order", "reverse",
                        "--out", fresh], check=True)
    if fresh:
        got = open(fresh, encoding="utf-8").read()
        if got != open(B.p(B.CACHE), encoding="utf-8").read():
            n = sum(1 for x, y in zip(got.splitlines(), open(B.p(B.CACHE), encoding="utf-8").read().splitlines()) if x != y)
            fail(f"fresh OpenRocket re-sim differs from the committed cache on {n} pairs")
        else:
            print("fresh OpenRocket re-sim == committed cache (bit-identical)")

    for name, n in counts.items():
        print(f"{name}: {n} rows")
    for k, v in inherited.items():
        print(f"INHERITED from v1 (inside the unchanged design block) eval_test {k} False: "
              f"{len(v)} {v}")
    for f in FAILS:
        print("FAIL", f)
    print(f"{len(FAILS)} failures")
    sys.exit(1 if FAILS else 0)


B_SEED = 42
B_UUID = 42

if __name__ == "__main__":
    main()
