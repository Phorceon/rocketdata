"""Optimizer attack on the reward: a genetic algorithm (pymoo) turns about 12 numbers on a real reference
rocket and climbs scripts/reward.py. GRPO is also an optimizer, so a hole this finds, GRPO finds too.

Each knob has a wide range on purpose (the physical limits, not the range of real rockets), so the search can
try the strange values where holes hide. Every flight is logged; read the top of each run by hand.

    python scripts/attack.py --refs SFT_JSONL --lookup data/motor_lookup.json --pick 5 --out results/attack
    python scripts/attack.py ... --source-ids "original:Big_Red.ork,..."   # choose the rockets yourself
"""
import argparse
import copy
import json
import math
import multiprocessing as mp
import re
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reward as R  # noqa: E402

FINS = ("trapezoidfinset", "ellipticalfinset")
# knob: (low, high). Wide on purpose.
KNOBS = {
    "tube_len_x":   (0.2, 4.0),      # times the reference length, every body tube
    "nose_len_x":   (0.2, 6.0),      # times the reference nose length
    "fin_count":    (1, 8),
    "fin_root_m":   (0.005, 0.6),
    "fin_tip_m":    (0.0, 0.6),
    "fin_span_m":   (0.005, 0.6),
    "fin_sweep_m":  (-0.2, 0.8),
    "fin_thick_m":  (0.0005, 0.02),
    "fin_cant_deg": (-15.0, 15.0),
    "chute_d_m":    (0.05, 8.0),
    "chute_cd":     (0.2, 4.0),
    "motor":        (0.0, 1.0),      # index into the real motors that fit the reference mount
}
NAMES = list(KNOBS)
LO = np.array([KNOBS[k][0] for k in NAMES], float)
HI = np.array([KNOBS[k][1] for k in NAMES], float)


# ------------------------------------------------------------------ design editing
def bodies(d, tags):
    out, stack = [], [d["openrocket"]]
    while stack:
        b = stack.pop()
        for c in b.get("children") or []:
            for k, v in c.items():
                if isinstance(v, dict):
                    if k in tags:
                        out.append(v)
                    if "children" in v:
                        stack.append(v)
    return out


def get(body, name):
    return next((c[name] for c in body.get("children") or [] if name in c), None)


def put(body, name, value):
    f = get(body, name)
    if f is not None:
        f["value"] = value


def design_of(row):
    text = row["messages"][-1]["content"]
    i = text.rfind("<design>")
    return json.loads(text[i + 8:text.find("</design>", i)])


def req_of(row):
    p, t = row["prompt_text"], row["targets"]
    q = {"target_apogee_m": t["apogee_m"], "apogee_tol_frac": 0.10, "wind_ms": t.get("wind_ms", 2.0)}
    if m := re.search(r"touches down under ([\d.]+) m/s", p):
        q["max_touchdown_ms"] = float(m.group(1))
    if m := re.search(r"flight time under ([\d.]+) s", p):
        q["max_flight_time_s"] = float(m.group(1))
    return q


def motor_choices(d, lookup):
    """Real motors with the same diameter as the reference motor, so a motor swap alone never breaks the fit."""
    m = bodies(d, ("motor",))[0]
    dia = get(m, "diameter")["value"] if get(m, "diameter") else None
    ref = get(m, "motor_id")["value"]
    dia = dia or lookup.get(ref, {}).get("diameter_m")
    return sorted(k for k, v in lookup.items() if dia and abs(v["diameter_m"] - dia) < 0.0015)


def knobs_of(d):
    """The reference rocket's own knob values (the start point)."""
    f = bodies(d, FINS)[0]
    ch = bodies(d, ("parachute",))
    def val(b, n, dflt=0.0):
        v = (get(b, n) or {}).get("value", dflt)
        return v if isinstance(v, (int, float)) and not isinstance(v, bool) else dflt   # "auto" sizes
    return {"tube_len_x": 1.0, "nose_len_x": 1.0, "fin_count": val(f, "fincount", 3),
            "fin_root_m": val(f, "rootchord"), "fin_tip_m": val(f, "tipchord"), "fin_span_m": val(f, "height"),
            "fin_sweep_m": val(f, "sweeplength"), "fin_thick_m": val(f, "thickness"), "fin_cant_deg": val(f, "cant"),
            "chute_d_m": val(ch[0], "diameter", 0.5) if ch else 0.5, "chute_cd": val(ch[0], "cd", 0.8) if ch else 0.8}


def apply(base, x, motors):
    d = copy.deepcopy(base)
    k = dict(zip(NAMES, x))
    for t in bodies(d, ("bodytube",)):
        put(t, "length", get(t, "length")["value"] * k["tube_len_x"])
    for n in bodies(d, ("nosecone",)):
        put(n, "length", get(n, "length")["value"] * k["nose_len_x"])
    for f in bodies(d, FINS)[:1]:
        n = int(round(k["fin_count"]))
        put(f, "fincount", n)
        put(f, "instancecount", n)
        put(f, "rootchord", k["fin_root_m"])
        put(f, "tipchord", k["fin_tip_m"])
        put(f, "height", k["fin_span_m"])
        put(f, "sweeplength", k["fin_sweep_m"])
        put(f, "thickness", k["fin_thick_m"])
        put(f, "cant", k["fin_cant_deg"])
    for c in bodies(d, ("parachute",)):
        put(c, "diameter", k["chute_d_m"])
        put(c, "cd", k["chute_cd"])
    mid = motors[min(int(k["motor"] * len(motors)), len(motors) - 1)]
    for m in bodies(d, ("motor",)):
        put(m, "motor_id", mid)
    return d, mid


# ------------------------------------------------------------------ scoring (one worker process each)
_W = {}


def _init(lookup_path):
    _W["lookup"] = json.load(open(lookup_path))


def evaluate(job):
    base, x, motors, req = job
    d, mid = apply(base, x, motors)
    t0 = time.time()
    try:
        r = R.score("<thought>x</thought><design>" + json.dumps(d) + "</design>", req, lookup=_W["lookup"])
        out = {"score": r["score"], "gate": r["gate"], "reasons": r["reasons"][:3], "parts": r.get("parts"),
               "metrics": {k: v for k, v in (r.get("metrics") or {}).items() if not isinstance(v, (dict, list))}}
    except Exception as e:                      # a crash is a finding, not a stop
        out = {"score": -1.0, "gate": "CRASH", "reasons": [f"{type(e).__name__}: {str(e)[:200]}"]}
    out.update(x=dict(zip(NAMES, map(float, x))), motor=mid, sec=round(time.time() - t0, 2))
    return out


# ------------------------------------------------------------------ search
def attack(row, lookup, pool, pop, gens, log, seed, apogee_x=1.0):
    from pymoo.algorithms.soo.nonconvex.ga import GA
    from pymoo.core.problem import Problem
    from pymoo.optimize import minimize
    base, req = design_of(row), req_of(row)
    req["target_apogee_m"] *= apogee_x          # a new target forces a redesign; the reference already scores 1.0
    motors = motor_choices(base, lookup)
    if not motors or not bodies(base, FINS):
        return None
    ref_mid = get(bodies(base, ("motor",))[0], "motor_id")["value"]
    start = knobs_of(base)
    start["motor"] = (motors.index(ref_mid) + 0.5) / len(motors) if ref_mid in motors else 0.5
    x0 = np.clip(np.array([start[k] for k in NAMES], float), LO, HI)
    seen = []

    class P(Problem):
        def __init__(self):
            super().__init__(n_var=len(NAMES), n_obj=1, xl=LO, xu=HI)

        def _evaluate(self, X, out, *a, **kw):
            res = pool.map(evaluate, [(base, x, motors, req) for x in X])
            for r in res:
                r["source_id"], r["apogee_x"] = row["source_id"], apogee_x
                log.write(json.dumps(r) + "\n")
                seen.append(r)
            log.flush()
            out["F"] = np.array([[-(r["score"] if r["score"] is not None else -1.0)] for r in res])

    # half the first round starts near the reference rocket, half anywhere: both kinds of hole get a chance
    rng = np.random.default_rng(seed)
    near = np.clip(x0 + rng.normal(0, 0.1, (pop // 2, len(NAMES))) * (HI - LO) * 0.3, LO, HI)
    near[0] = x0
    anywhere = LO + rng.random((pop - pop // 2, len(NAMES))) * (HI - LO)
    minimize(P(), GA(pop_size=pop, sampling=np.vstack([near, anywhere]), eliminate_duplicates=True),
             ("n_gen", gens), seed=seed, verbose=False)
    return seen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refs", required=True, help="sft_v5 JSONL with prompt_text, targets, source_id")
    ap.add_argument("--lookup", default=str(R.LOOKUP_PATH))
    ap.add_argument("--source-ids", default="")
    ap.add_argument("--pick", type=int, default=5, help="without --source-ids: this many rockets that fly safely")
    ap.add_argument("--pop", type=int, default=40)
    ap.add_argument("--gens", type=int, default=40)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--apogee-x", default="0.5,2", help="targets to chase, as multiples of the reference apogee")
    ap.add_argument("--out", default="results/attack")
    a = ap.parse_args()
    lookup = json.load(open(a.lookup))
    rows, seen = [], set()
    for line in open(a.refs):
        r = json.loads(line)
        if r["source_id"] not in seen:
            seen.add(r["source_id"])
            rows.append(r)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    with mp.get_context("spawn").Pool(a.workers, initializer=_init, initargs=(a.lookup,)) as pool:
        if a.source_ids:
            want = a.source_ids.split(",")
            chosen = [r for r in rows if r["source_id"] in want]
        else:                                   # spread over motor sizes: every k-th rocket that flies safely
            cands = [r for r in rows if bodies(design_of(r), FINS) and bodies(design_of(r), ("parachute",))]
            cands.sort(key=lambda r: r["targets"]["apogee_m"])
            step = max(1, len(cands) // (a.pick * 3))
            cands = cands[::step]
            ok = pool.map(evaluate, [(design_of(r), _ref_x(r, lookup), motor_choices(design_of(r), lookup), req_of(r))
                                     for r in cands])
            chosen = [r for r, o in zip(cands, ok) if o["gate"] is None]
            chosen = chosen[::max(1, len(chosen) // a.pick)][:a.pick]
        print("attacking:", [r["source_id"] for r in chosen], flush=True)
        with open(out / "flights.jsonl", "w") as log:
            for r in chosen:
                for ax in map(float, a.apogee_x.split(",")):
                    t0 = time.time()
                    res = attack(r, lookup, pool, a.pop, a.gens, log, a.seed, ax)
                    if res is None:
                        print("skip", r["source_id"], flush=True)
                        break
                    best = max(res, key=lambda o: o["score"] if o["score"] is not None else -9)
                    print(f"{r['source_id'][:45]:45} apogee x{ax:g}  {len(res)} flights {time.time() - t0:.0f}s  "
                          f"start {res[0]['score']}  best {best['score']}", flush=True)


def _ref_x(row, lookup):
    base = design_of(row)
    motors = motor_choices(base, lookup)
    start = knobs_of(base)
    mid = get(bodies(base, ("motor",))[0], "motor_id")["value"]
    start["motor"] = (motors.index(mid) + 0.5) / len(motors) if mid in motors else 0.5
    return np.clip(np.array([start[k] for k in NAMES], float), LO, HI)


if __name__ == "__main__":
    main()
