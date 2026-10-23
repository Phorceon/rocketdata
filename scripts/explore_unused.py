"""Explore unused .ork files: apply exclusions, dedupe by design fingerprint,
categorize for variety. Prints counts only (no files written)."""
import json
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from ork_design import build_design, fingerprint, load_bytes, _num  # noqa: E402
from xml.etree import ElementTree as ET  # noqa: E402

ORK = os.path.join(REPO, "ork")


def sims_with_metrics(path):
    """Return list of (name, configid, metrics) for stored sims that have an apogee."""
    root = ET.fromstring(load_bytes(path))
    out = []
    for sim in root.iter("simulation"):
        name = sim.findtext("name")
        cfg = sim.findtext("conditions/configid") or sim.findtext("configid")
        fd = sim.find("flightdata")
        if fd is None:
            continue
        apogee = _f(fd.get("maxaltitude"))
        if apogee is None:
            continue
        metrics = {
            "apogee_m": apogee,
            "max_velocity_mps": _f(fd.get("maxvelocity")),
            "max_acceleration_mps2": _f(fd.get("maxacceleration")),
            "max_mach": _f(fd.get("maxmach")),
            "time_to_apogee_s": _f(fd.get("timetoapogee")),
            "flight_time_s": _f(fd.get("flighttime")),
            "ground_hit_velocity_mps": _f(fd.get("groundhitvelocity")),
            "deployment_velocity_mps": _f(fd.get("deploymentvelocity")),
            "launchrod_velocity_mps": _f(fd.get("launchrodvelocity")),
        }
        out.append((name, cfg, metrics))
    return out


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def motor_classes(comps):
    """Impulse classes of every motor designation found in the IR."""
    out = set()

    def rec(c):
        for m in c.get("motors", []):
            d = m["designation"]
            # impulse class = leading alpha (skip digits/"HP-")
            for ch in d:
                if ch.isalpha():
                    out.add(ch.upper())
                    break
        for ch in c.get("contains", []):
            rec(ch)

    for c in comps:
        rec(c)
    return out


def fin_kinds(comps):
    kinds = set()

    def rec(c):
        if c["type"] in ("trapezoidfin", "freeformfinset", "ellipticalfin", "tubefin"):
            kinds.add(c["type"])
        for ch in c.get("contains", []):
            rec(ch)

    for c in comps:
        rec(c)
    return kinds


def deploy_kinds(comps):
    d = set()

    def rec(c):
        if c["type"] in ("parachute", "streamer"):
            d.add(c["type"])
        for ch in c.get("contains", []):
            rec(ch)

    for c in comps:
        rec(c)
    return d


def main():
    def used_files(path):
        out = {}
        for line in open(os.path.join(REPO, path), encoding="utf-8"):
            if line.strip():
                row = json.loads(line)
                out[row["file"]] = row
        return out

    v0 = used_files("data/sft_v0.jsonl")
    test = used_files("data/sft_test.jsonl")
    held = {(row["file"]): row for row in
            (json.loads(l) for l in open(os.path.join(REPO, "data/splits/rl_heldout.jsonl"), encoding="utf-8") if l.strip())}

    used_paths = set(v0) | set(test) | set(held)

    allork = sorted(f for f in os.listdir(ORK) if f.lower().endswith(".ork"))
    files = ["ork/" + f for f in allork]

    # fingerprints of the leakage rockets (v0/test/heldout) by their stored row files
    leak_fps = {}
    for p in used_paths:
        try:
            comps, _ = build_design(p)
            leak_fps[p] = fingerprint(comps)
        except Exception:
            pass

    # v0 fingerprints (for dedupe decisions)
    v0_fps = set()
    for p in v0:
        try:
            comps, _ = build_design(p)
            v0_fps.add(fingerprint(comps))
        except Exception:
            pass

    stats = Counter()
    removed = Counter()
    kept = []
    seen_fp = {}
    for p in files:
        if p in used_paths:
            stats["used"] += 1
            continue
        try:
            comps, root = build_design(p)
        except Exception as e:
            stats["parse_error"] += 1
            continue
        rocket_name = root.findtext("rocket/name")
        stats["unused"] += 1
        # NOTE: `Rocket` is OpenRocket's default name and is NOT used as an
        # exclusion criterion (real designs use it too).
        fps = fingerprint(comps)
        # exclusion 1: fingerprint matches a leakage rocket
        if fps in set(leak_fps.values()):
            removed["fp_matches_v0_test_held"] += 1
            continue
        # exclusion 3: dedupe — one file per fingerprint
        if fps in seen_fp:
            removed["dup_fingerprint"] += 1
            continue
        sims = sims_with_metrics(p)
        if not sims:
            removed["no_sim_metrics"] += 1
            continue
        # need nosecone + bodytube for schema
        types = set()

        def walk(c):
            types.add(c["type"])
            for ch in c.get("contains", []):
                walk(ch)
        for c in comps:
            walk(c)
        if "nosecone" not in types or "bodytube" not in types:
            removed["missing_nose_or_tube"] += 1
            continue
        seen_fp[fps] = p
        kept.append({
            "file": p,
            "name": rocket_name,
            "n_sims": len(sims),
            "classes": sorted(motor_classes(comps)),
            "fins": sorted(fin_kinds(comps)),
            "deploy": sorted(deploy_kinds(comps)),
            "max_diameter": _max_dia(comps),
        })

    print("=== raw counts ===")
    print(dict(stats))
    print("\n=== removed (after being an unused non-generic file) ===")
    print(dict(removed))
    print("\n=== kept candidates:", len(kept))
    # class mix
    cmix = Counter()
    for k in kept:
        cls = k["classes"]
        cmix[tuple(cls) if cls else ("?",)] += 1
    print("\n=== candidate motor-class combos ===")
    for c, n in cmix.most_common():
        print(f"  {n:3d} {c}")
    json.dump(kept, open("/tmp/candidates.json", "w"))


def _max_dia(comps):
    m = 0.0

    def rec(c):
        nonlocal m
        for k in ("outer_d_m", "base_radius_m", "aft_d_m"):
            if c.get(k):
                m = max(m, c[k] * (2 if k == "base_radius_m" else 1))
        for ch in c.get("contains", []):
            rec(ch)

    for c in comps:
        rec(c)
    return round(m, 3)


if __name__ == "__main__":
    main()
