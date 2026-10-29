"""Write a training copy of an SFT JSONL without the very large designs; the source file is not changed.

A few rows of new_results/sft_v2.jsonl model every small part of a kit (68 centering rings, 92 inner tubes),
so their <design> lists run past 100 components. Training on them taught the model to keep listing parts
until it ran out of tokens. This drops every row whose design has --max-parts components or more.

    python sft\\filter_data.py                     (new_results/sft_v2.jsonl -> C:\\ft\\data_qwen\\sft_v2_cap60.jsonl)
    python sft\\filter_data.py --max-parts 40 --out C:\\ft\\data_qwen\\sft_v2_cap40.jsonl
"""
import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def walk(components):
    """Yield every component dict, including those nested under "contains"."""
    for c in components if isinstance(components, list) else []:
        if isinstance(c, dict):
            yield c
            yield from walk(c.get("contains"))


def part_count(row):
    answer = row["messages"][-1]["content"]
    design = json.loads(answer.split("<design>")[1].split("</design>")[0])
    return sum(1 for _ in walk(design.get("components")))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default=str(REPO / "new_results" / "sft_v2.jsonl"))
    ap.add_argument("--out", default=r"C:\ft\data_qwen\sft_v2_cap60.jsonl")
    ap.add_argument("--max-parts", type=int, default=60, help="drop designs with this many components or more")
    args = ap.parse_args()

    kept, dropped = [], []
    for line in open(args.src, encoding="utf-8"):
        if line.strip():
            row = json.loads(line)
            (dropped if part_count(row) >= args.max_parts else kept).append((row, line))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(line for _, line in kept), encoding="utf-8")
    print(f"kept {len(kept)}, dropped {len(dropped)} -> {out}")
    for row, _ in dropped:
        print(f"  dropped {row['id']} ({part_count(row)} parts, {row['file']})")


if __name__ == "__main__":
    main()
