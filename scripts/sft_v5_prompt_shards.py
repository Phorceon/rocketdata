"""Build per-rocket fact shards for writing extra sft_v5 prompt variations."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "sftgen/out/scratch/sft_v5_prompts"
SHARDS = 4


def facts_for(row):
    text = row["messages"][-1]["content"].split("<design>")[0]
    t = row["targets"]
    facts = {
        "catalog_id": row["catalog_id"],
        "original_prompt": row["messages"][1]["content"],
        "apogee_m": round(t["apogee_m"], 1),
        "touchdown_ms": round(t["ground_hit_ms"], 2),
        "flight_time_s": round(t["flight_time_s"], 1),
    }
    if isinstance(t.get("wind_ms"), (int, float)):
        facts["wind_ms"] = round(t["wind_ms"], 1)
    m = re.search(r"reference diameter ([\d.Ee-]+) m", text)
    if m:
        facts["body_diameter_mm"] = round(float(m.group(1)) * 1000, 1)
    m = re.search(r"liftoff mass ([\d.Ee-]+) kg", text)
    if m:
        facts["liftoff_mass_g"] = round(float(m.group(1)) * 1000)
    designations = re.findall(r"designation ([^,\n]+),", text)
    if designations:
        facts["motor_designations"] = sorted(set(designations))
    return facts


def main():
    rows = [json.loads(line) for line in (ROOT / "new_results/sft_v5.jsonl").open()]
    facts = [facts_for(row) for row in rows]
    for i in range(SHARDS):
        with (OUT / "shards" / f"shard_{i}.jsonl").open("w") as f:
            for item in facts[i::SHARDS]:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(len(facts), [len(facts[i::SHARDS]) for i in range(SHARDS)])
    for key in ("body_diameter_mm", "liftoff_mass_g", "motor_designations", "wind_ms"):
        print(key, sum(key in item for item in facts))
    print(json.dumps(facts[0])[:500])
    print(facts[0]["original_prompt"])


if __name__ == "__main__":
    main()
