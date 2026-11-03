"""Validate written sft_v5 prompt variations against each rocket's real facts."""
import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "sftgen/out/scratch/sft_v5_prompts"
STYLES = {"casual", "engineering"}
BANNED = re.compile(r"\$|\bcost|\bbudget|\bprice|\bcheap|\btool\b|\bsimulat|<|>", re.I)
TO_M = {"m": 1.0, "meter": 1.0, "meters": 1.0, "metres": 1.0, "ft": 0.3048, "feet": 0.3048,
        "foot": 0.3048, "km": 1000.0}
NUMBER = re.compile(
    r"(\d[\d,]*\.?\d*)\s*(meters|metres|meter|feet|foot|ft|km|m/s|mm|cm|inches|inch|in|"
    r"kg|grams|g|seconds|secs|sec|minutes|min|mph|s|m)\b", re.I)


def number_problems(prompt, facts):
    """Every number with a unit must match a real fact, within its allowed direction."""
    issues = []
    apogee, touchdown = facts["apogee_m"], facts["touchdown_ms"]
    flight, wind = facts["flight_time_s"], facts.get("wind_ms")
    diameter, mass = facts.get("body_diameter_mm"), facts.get("liftoff_mass_g")
    for raw, unit in NUMBER.findall(prompt):
        value, unit = float(raw.replace(",", "").rstrip(".")), unit.lower()
        ok = False
        if unit in TO_M:
            ok = abs(value * TO_M[unit] - apogee) <= 0.05 * apogee
        elif unit == "m/s":
            ok = touchdown <= value <= touchdown * 1.15 + 0.1
            ok = ok or (wind is not None and abs(value - wind) <= 0.5)
        elif unit == "mph":
            ok = wind is not None and abs(value * 0.44704 - wind) <= 0.5
        elif unit in {"mm", "cm", "in", "inch", "inches"}:
            mm = value * {"mm": 1, "cm": 10}.get(unit, 25.4)
            ok = diameter is not None and diameter <= mm <= diameter * 1.25 + 1
        elif unit in {"g", "grams", "kg"}:
            grams = value * (1000 if unit == "kg" else 1)
            ok = mass is not None and mass <= grams <= mass * 1.25 + 1
        elif unit in {"s", "sec", "secs", "seconds", "min", "minutes"}:
            seconds = value * (60 if unit in {"min", "minutes"} else 1)
            ok = flight <= seconds <= flight * 1.15 + 1
        if not ok:
            issues.append(f"{raw} {unit} does not match the facts")
    return issues


def check():
    facts = {}
    for path in sorted((OUT / "shards").glob("shard_*.jsonl")):
        for line in path.open():
            item = json.loads(line)
            facts[item["catalog_id"]] = item
    problems, seen, counts = [], set(), collections.Counter()
    for path in sorted((OUT / "written").glob("shard_*.jsonl")):
        for number, line in enumerate(path.open(), 1):
            where = f"{path.name}:{number}"
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                problems.append(f"{where}: bad JSON")
                continue
            if set(item) != {"catalog_id", "style", "prompt"}:
                problems.append(f"{where}: keys must be catalog_id, style, prompt")
                continue
            cid, style, prompt = item["catalog_id"], item["style"], item["prompt"].strip()
            if cid not in facts:
                problems.append(f"{where}: unknown rocket {cid}")
                continue
            if style not in STYLES:
                problems.append(f"{where}: bad style {style}")
            if (cid, style) in seen:
                problems.append(f"{where}: duplicate {cid} {style}")
            seen.add((cid, style))
            counts[cid] += 1
            if BANNED.search(prompt):
                problems.append(f"{where}: banned word or character: {prompt}")
            if prompt == facts[cid]["original_prompt"]:
                problems.append(f"{where}: same as original prompt")
            if not 30 <= len(prompt) <= 400:
                problems.append(f"{where}: length {len(prompt)}")
            if not NUMBER.search(prompt):
                problems.append(f"{where}: no measurable requirement")
            problems += [f"{where}: {cid}: {x}: {prompt}" for x in number_problems(prompt, facts[cid])]
    missing = [cid for cid in facts if counts[cid] != len(STYLES)]
    return facts, problems, missing


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    facts, problems, missing = check()
    if only:
        shard = {json.loads(l)["catalog_id"] for l in (OUT / "shards" / f"shard_{only}.jsonl").open()}
        problems = [p for p in problems if p.startswith(f"shard_{only}.jsonl")]
        missing = [cid for cid in missing if cid in shard]
    print(f"rockets {len(facts)}  problems {len(problems)}  rockets missing prompts {len(missing)}")
    for line in problems[:60]:
        print(line[:260])
    sys.exit(1 if problems or missing else 0)


if __name__ == "__main__":
    main()
