"""Merge written prompt variations into sft_v5.jsonl: three rows per rocket."""
import copy
import json
import re
import shutil
import statistics
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "sftgen/out/scratch/sft_v5_prompts"
MAIN = ROOT / "new_results/sft_v5.jsonl"
TOUCHDOWN_LIMIT_MS = 8.0


def read_jsonl(path):
    return [json.loads(line) for line in path.open()]


def clamp_touchdown(prompt, facts):
    """A stated touchdown limit never exceeds the project limit of 8 m/s."""
    wind = facts.get("wind_ms")

    def fix(match):
        value = float(match.group(1))
        if value <= TOUCHDOWN_LIMIT_MS or (wind is not None and abs(value - wind) <= 0.5):
            return match.group(0)
        return "8 m/s"
    return re.sub(r"(\d+\.?\d*)\s*m/s", fix, prompt)


def main():
    facts = {}
    for path in (BASE / "shards").glob("shard_*.jsonl"):
        facts.update({item["catalog_id"]: item for item in read_jsonl(path)})
    written = {}
    clamped = 0
    for path in sorted((BASE / "written").glob("shard_*.jsonl")):
        for item in read_jsonl(path):
            prompt = clamp_touchdown(item["prompt"].strip(), facts[item["catalog_id"]])
            clamped += prompt != item["prompt"].strip()
            written.setdefault(item["catalog_id"], {})[item["style"]] = prompt

    rows = read_jsonl(MAIN)
    assert len(rows) == 218 and len({r["catalog_id"] for r in rows}) == 218
    merged = []
    for row in rows:
        original = row["messages"][1]["content"]
        assistant = row["messages"][-1]["content"]
        assert assistant.count(f'"{original}"') == 1, row["catalog_id"]
        base = dict(row, prompt_style="original")
        merged.append(base)
        for style in ("casual", "engineering"):
            new = copy.deepcopy(row)
            prompt = written[row["catalog_id"]][style]
            new["id"] = f'{row["id"]}-{style}'
            new["prompt_style"] = style
            new["prompt_text"] = prompt
            new["messages"][1]["content"] = prompt
            new["messages"][-1]["content"] = assistant.replace(f'"{original}"', f'"{prompt}"')
            merged.append(new)

    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = ROOT / f"sftgen/out/scratch/sft_v5_backup_{stamp}"
    backup.mkdir()
    shutil.copy(MAIN, backup / MAIN.name)
    with MAIN.open("w") as f:
        for row in merged:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"rows {len(merged)}  clamped prompts {clamped}  backup {backup}")


if __name__ == "__main__":
    main()
