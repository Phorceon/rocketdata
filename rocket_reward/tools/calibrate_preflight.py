"""Check that the reference ("gold") answers pass stages 1-4.

Usage (from the repo root):

    python -m rocket_reward.tools.calibrate_preflight train.jsonl val.jsonl test.jsonl
    python -m rocket_reward.tools.calibrate_preflight FILES... --report report.md --json out.json

Each file holds rows like {"messages": [system, user, assistant]} (or rows
with a "content" or "answer" field). The assistant message is the answer.
For every answer it prints the stage it stops at; every gold answer that does
not pass stages 1-4 is listed with its reasons, grouped by design, so a person
can decide whether the limit is too strict or the design is truly broken.

A row is named "<file stem>-<line>", counting every line of the file from 0
(blank lines included). When two input files share a stem, the later rows get
"#2", "#3" ... added, so no row is lost.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Optional, Sequence

from rocket_reward.cli import answer_of, read_numbered_rows, run_row, unique_key, use_utf8_output


def _design_key(text: Optional[str]) -> str:
    """Rows asking for the same rocket share one design block; group by it."""
    if text is None:
        return "-"
    start, end = text.find("<design>"), text.rfind("</design>")
    body = text[start:end] if 0 <= start < end else text
    return hashlib.sha256(body.encode("utf-8", errors="replace")).hexdigest()[:10]


def calibrate(files: Sequence[str]) -> dict[str, Any]:
    """Run stages 1-4 on every row of `files`; return counts and failures."""
    rows: dict[str, dict[str, Any]] = {}
    for name in files:
        path = Path(name)
        stem = path.name.split(".")[0]
        for n, row in read_numbered_rows(path):
            res = run_row(row)
            res["design"] = _design_key(answer_of(row))
            rows[unique_key(f"{stem}-{n}", rows)] = res
    stages = collections.Counter(r["stage"] for r in rows.values())
    failures = {k: r for k, r in rows.items() if r["stage"] != "passed"}
    by_design: dict[str, list[str]] = collections.defaultdict(list)
    for k, r in failures.items():
        by_design[r["design"]].append(k)
    return {"rows": len(rows), "passed": stages.get("passed", 0), "stages": dict(stages),
            "failures": failures, "by_design": dict(by_design),
            "designs": len({r["design"] for r in rows.values()})}


def report_markdown(cal: dict[str, Any]) -> str:
    n, ok = cal["rows"], cal["passed"]
    out = [f"# Stages 1-4 on the gold answers", "",
           f"{ok} of {n} gold answers pass stages 1-4 ({ok / max(1, n):.1%}); "
           f"{cal['designs']} distinct designs.", "",
           "Stops at: " + ", ".join(f"{k} {v}" for k, v in sorted(cal["stages"].items())), ""]
    if cal["failures"]:
        out += ["## Failing designs", "",
                "Rows that share a design block are one rocket asked several ways.", ""]
        for design, keys in cal["by_design"].items():
            first = cal["failures"][keys[0]]
            out.append(f"### {', '.join(keys)} (stage {first['stage']}, score {first['score']})")
            out.append("")
            out += [f"- {r}" for r in first["reasons"]]
            out.append("")
    return "\n".join(out)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("files", nargs="+", help="gold .jsonl or .jsonl.gz files")
    ap.add_argument("--report", help="also write the failing designs to this Markdown file")
    ap.add_argument("--json", help="also write every row's result to this JSON file")
    args = ap.parse_args(argv)
    use_utf8_output()
    cal = calibrate(args.files)
    print(f"{cal['passed']}/{cal['rows']} gold answers pass stages 1-4 "
          f"({cal['passed'] / max(1, cal['rows']):.1%}); stops: {dict(sorted(cal['stages'].items()))}")
    for design, keys in cal["by_design"].items():
        first = cal["failures"][keys[0]]
        print(f"  {', '.join(keys)}: {first['stage']} {first['score']}: "
              f"{'; '.join(first['reasons'])[:300]}")
    if args.report:
        with open(args.report, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(report_markdown(cal) + "\n")
    if args.json:
        with open(args.json, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(cal, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
