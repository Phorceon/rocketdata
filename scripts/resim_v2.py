"""Re-simulate every (ork, sim) used by sft_v1 / sft_test with OpenRocket 24.12 and write
the sim cache new_results/sft_v2_sims.jsonl that build_sft_v2.py reads.

    bash scripts/fetch_openrocket.sh           # lib/OpenRocket.jar (24.12, sha-pinned)
    python3 scripts/resim_v2.py                # needs a JDK 17+ (javac + java) on PATH
    python3 scripts/resim_v2.py --from-runs a.jsonl b.jsonl   # rebuild cache from raw runs

Determinism. Plain OpenRocket is not reproducible run to run, for two reasons:
  1. SimulationOptions builds its pink-noise wind models from a random seed at
     construction; setRandomSeed() does not reseed them.
  2. Components in older .ork files have no stored id, so each load assigns
     UUID.randomUUID(); those UUIDs key FlightConfiguration's motor HashMap, so the
     motor iteration order (and the result of multi-motor / multi-stage sims) changes.
scripts/or_batch/OrBatch.java fixes both: it rebuilds the wind models from the sim seed
and installs a seeded SecureRandom provider so component UUIDs are the same every load.

The first simulation of a design in a JVM differs from every later one at the ~1e-14
level (OpenRocket fills lazy caches on first use), so each pair gets one discarded warm-up
run, then two recorded runs with seed 42 / uuid seed 42 that must be bit-identical or the
script fails. `--order reverse` runs the pairs in the opposite order; the verifier uses it
to show the cache does not depend on what ran before. A third run with uuid seed 7 measures how much a pair depends on
OpenRocket's motor ordering; that is recorded (uuid_sensitivity) and reported, not hidden.
"""
import argparse
import json
import math
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SEED = 42
UUID_SEED = 42
ALT_UUID_SEED = 7
METRICS = ["apogee_m", "max_velocity_ms", "max_accel_ms2", "max_mach", "time_to_apogee_s",
           "flight_time_s", "ground_hit_ms", "deployment_velocity_ms", "wind_ms"]
SOURCES = ["new_results/sft_v1.jsonl", "data/sft_test.jsonl"]
CACHE = "new_results/sft_v2_sims.jsonl"


def pairs():
    seen = []
    for src in SOURCES:
        for line in open(os.path.join(REPO, src), encoding="utf-8"):
            if line.strip():
                r = json.loads(line)
                k = (r["file"], r["sim"])
                if k not in seen:
                    seen.append(k)
    return sorted(seen)


def run_java(jar, lines, workdir):
    src = os.path.join(HERE, "or_batch", "OrBatch.java")
    subprocess.run(["javac", "--release", "17", "-nowarn", "-cp", jar, "-d", workdir, src], check=True)
    env = dict(os.environ, LC_ALL="C.UTF-8", LANG="C.UTF-8")
    p = subprocess.run(["java", "-Dsun.jnu.encoding=UTF-8", "-Dfile.encoding=UTF-8",
                        "-Djava.awt.headless=true", "-cp", jar + os.pathsep + workdir, "OrBatch"],
                       input="".join(lines), capture_output=True, text=True, cwd=REPO, env=env,
                       encoding="utf-8", check=True)
    return [json.loads(x) for x in p.stdout.splitlines() if x.strip()]


def finite(x):
    return isinstance(x, (int, float)) and math.isfinite(x)


def build_cache(runs):
    by = {}
    for d in runs:
        by.setdefault((d["file"], d["sim"]), []).append(d)
    out = []
    for (f, s) in pairs():
        rs = by.get((f, s), [])
        main = [d for d in rs if d["uuid_seed"] == UUID_SEED and d["rep"] >= 1]  # rep 0 = warm-up
        alt = [d for d in rs if d["uuid_seed"] == ALT_UUID_SEED and d["rep"] >= 1]
        if len(main) < 2 or len(alt) < 1:
            sys.exit(f"missing runs for {f} / {s}")
        a, b = main[0], main[1]
        strip = lambda d: {k: v for k, v in d.items() if k != "rep"}  # noqa: E731
        if json.dumps(strip(a), sort_keys=True) != json.dumps(strip(b), sort_keys=True):
            sys.exit(f"NOT DETERMINISTIC: {f} / {s}")
        rec = {"file": f, "sim": s, "seed": SEED, "uuid_seed": UUID_SEED}
        if "error" in a:
            rec["error"] = a["error"]
        else:
            rec.update({k: a.get(k) for k in METRICS})
            rec["events"] = a["events"]
            c = alt[0]
            if "error" in c:
                rec["uuid_sensitivity"] = None
            else:
                rel = 0.0
                for k in METRICS:
                    x, y = a.get(k), c.get(k)
                    if finite(x) and finite(y):
                        rel = max(rel, abs(x - y) / max(abs(x), 1e-9))
                    elif finite(x) != finite(y):
                        rel = float("inf")
                rec["uuid_sensitivity"] = rel if math.isfinite(rel) else "inf"
                rec["alt_uuid_seed"] = ALT_UUID_SEED
                rec["alt"] = {k: c.get(k) for k in METRICS}
        out.append(rec)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", default=os.path.join(REPO, "lib", "OpenRocket.jar"))
    ap.add_argument("--from-runs", nargs="*")
    ap.add_argument("--out", default=os.path.join(REPO, CACHE))
    ap.add_argument("--order", choices=["sorted", "reverse"], default="sorted")
    a = ap.parse_args()
    if a.from_runs:
        runs = [json.loads(x) for p in a.from_runs for x in open(p, encoding="utf-8") if x.strip()]
    else:
        lines = []
        order = pairs() if a.order == "sorted" else pairs()[::-1]
        for f, s in order:
            lines.append(f"{f}\t{s}\t{SEED}\t3\t{UUID_SEED}\n")
            lines.append(f"{f}\t{s}\t{SEED}\t2\t{ALT_UUID_SEED}\n")
        with tempfile.TemporaryDirectory() as td:
            runs = run_java(os.path.abspath(a.jar), lines, td)
    cache = build_cache(runs)
    with open(a.out, "w", encoding="utf-8") as fh:
        for r in cache:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(cache)} sims to {a.out} "
          f"({sum('error' in r for r in cache)} errors)")


if __name__ == "__main__":
    main()
