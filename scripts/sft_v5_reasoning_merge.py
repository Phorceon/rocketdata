"""Replace sft_v5 <thought> text: request, rocket reasoning, then a computed request check."""
import json
import re
import shutil
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "sftgen/out/scratch/sft_v5_reasoning"
MAIN = ROOT / "new_results/sft_v5.jsonl"
NUMBER = re.compile(
    r"(\d[\d,]*\.?\d*)\s*(meters|metres|meter|feet|foot|ft|km|m/s|mm|cm|inches|inch|in|"
    r"kg|grams|g|seconds|secs|sec|minutes|min|mph|s|m)\b", re.I)
TO_M = {"m": 1.0, "meter": 1.0, "meters": 1.0, "metres": 1.0, "ft": 0.3048, "feet": 0.3048,
        "foot": 0.3048, "km": 1000.0}
STALE_FLAGS = {"thought_coverage_fallback", "reasoning_summarized_for_context"}


def sig(value):
    return f"{value:.4g}"


def request_check(prompt, facts):
    """Lines that compare each number in the prompt with this rocket's real values."""
    flight = facts["reference_flight"]
    wind = flight.get("wind_ms")
    lines, seen = [], set()

    def add(key, text):
        if key not in seen:
            seen.add(key)
            lines.append(f"- {text}")

    for match in NUMBER.finditer(prompt):
        raw, unit = match.group(1), match.group(2).lower()
        value = float(raw.replace(",", "").rstrip("."))
        nearby = prompt[max(0, match.start() - 22):match.end() + 16].lower()
        stated = f"{raw.rstrip('.')} {match.group(2)}"
        if unit in TO_M:
            add("apogee", f"Apogee request {stated}: the reference flight reaches {sig(flight['apogee_m'])} m.")
        elif unit == "mph" or (unit == "m/s" and wind is not None and abs(value - wind) <= 0.5
                               and re.search(r"wind|breeze|gust", nearby)):
            add("wind", f"Wind {stated}: the reference flight used {sig(wind)} m/s.")
        elif unit == "m/s":
            add("touchdown", f"Touchdown limit {stated}: the reference flight lands at "
                             f"{sig(flight['ground_hit_ms'])} m/s, within the limit.")
        elif unit in {"mm", "cm", "in", "inch", "inches"}:
            add("diameter", f"Diameter limit {stated}: the body is {sig(facts['diameter_m'] * 1000)} mm.")
        elif unit in {"g", "grams", "kg"}:
            add("mass", f"Mass limit {stated}: liftoff mass is {sig(facts['liftoff_mass_kg'])} kg.")
        else:
            add("time", f"Flight time {stated}: the reference flight lasts {sig(flight['flight_time_s'])} s.")
    for motor in re.findall(r"designation ([^,]+)", " ".join(facts["motors"])):
        if re.search(rf"(?<![\w-]){re.escape(motor)}(?![\w-])", prompt):
            add("motor", f"Motor {motor}: this design uses it.")
    return lines


def main():
    facts, written = {}, {}
    for path in (BASE / "shards").glob("shard_*.jsonl"):
        for line in path.open():
            item = json.loads(line)
            facts[item["catalog_id"]] = item
    for path in (BASE / "written").glob("shard_*.jsonl"):
        for line in path.open():
            item = json.loads(line)
            written[item["catalog_id"]] = item["reasoning"].strip()
    rows = [json.loads(line) for line in MAIN.open()]
    assert set(written) == {r["catalog_id"] for r in rows}
    for row in rows:
        cid, prompt = row["catalog_id"], row["messages"][1]["content"]
        design = re.search(r"<design>.*</design>", row["messages"][-1]["content"], re.S).group(0)
        check = "\n".join(request_check(prompt, facts[cid]))
        row["messages"][-1]["content"] = (
            f'<thought>\nREQUEST:\n"{prompt}"\n\n{written[cid]}\n\nREQUEST CHECK:\n{check}\n</thought>\n{design}')
        row["flags"] = [f for f in row["flags"] if isinstance(f, dict) or f not in STALE_FLAGS]
        row["reasoning_version"] = "v5_engineering"
    backup = ROOT / f"sftgen/out/scratch/sft_v5_backup_{time.strftime('%Y%m%d-%H%M%S')}"
    backup.mkdir()
    shutil.copy(MAIN, backup / MAIN.name)
    with MAIN.open("w") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print("rows", len(rows), "backup", backup)


if __name__ == "__main__":
    main()
