"""Run the CAD gate on every design in the SFT data and count what happens.

    .venv/bin/python scripts/cad_gate_report.py

These are real rockets that fly in OpenRocket, so ideally every buildable one passes.
Any that fail are worth a look: either the design really has a problem, or the gate
is wrong. Never change the gate just to make this number look better.
"""
import collections
import json
import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))

from rocketai import cad  # noqa: E402

FILES = ["new_results/sft_v2.jsonl", "new_results/sft_test_v2.jsonl"]


def short(reason):
    """Group similar messages: drop the part name before the first colon."""
    return reason.split(": ", 1)[-1] if ": " in reason else reason


def main():
    status = collections.Counter()
    why = collections.defaultdict(collections.Counter)
    examples = collections.defaultdict(list)
    seen = set()
    failed = []
    t0 = time.time()
    for path in FILES:
        for line in open(os.path.join(REPO, path), encoding="utf-8"):
            row = json.loads(line)
            design = cad.design_from_row(row)
            key = json.dumps(design, sort_keys=True)
            if key in seen:  # several prompts share one design; count each design once
                continue
            seen.add(key)
            r = cad.cad_gate(design)
            status[r["status"]] += 1
            if r["status"] in ("fail", "error"):
                failed.append((row["id"], row["file"], r["failures"]))
            reasons = r["unsupported"] if r["status"] == "unsupported" else r["failures"]
            for reason in sorted({short(x) for x in reasons}):
                why[r["status"]][reason] += 1
                if len(examples[(r["status"], reason)]) < 3:
                    examples[(r["status"], reason)].append(row["id"])
    total = sum(status.values())
    print(f"{total} distinct designs, {time.time() - t0:.0f} s\n")
    for s in ("pass", "fail", "unsupported", "error"):
        print(f"{s:12s} {status[s]}")
        if s == "unsupported":
            for reason, n in why[s].most_common():
                print(f"    {n:3d}  {reason}   e.g. {', '.join(examples[(s, reason)])}")
    print("\nevery failed design, with its full reasons:")
    for rid, f, reasons in failed:
        print(f"\n  {rid}  ({f})")
        for x in reasons:
            print(f"      - {x}")


if __name__ == "__main__":
    main()
