"""Score reference (or model) answers through the whole ladder and report.

Usage (from the repo root; Java and the OpenRocket jar must be set up):

    python -m rocket_reward.tools.calibrate --meta META.jsonl --prompts PARSED.jsonl \\
        --out report.md --json report.json [--expected EXPECTED.json] [--workers 4] [--limit N]
    python -m rocket_reward.tools.calibrate --answers ANSWERS.jsonl[.gz] --requirements REQS.json \\
        --out report.md --json report.json

Inputs:
  --meta        reference rows: {"id", "group_id", "prompt_text", "messages": [..., assistant]}
  --prompts     parsed prompts: {"id": "<meta id>:<style>", "prompt_text", "requirements"}; a meta
                row takes the parsed row whose id starts with its own id, else the one with
                the same prompt text
  --answers     answer rows: {"id", "content" or "answer" or "messages", "truncated"?}
  --requirements  {answer id: requirements record} for --answers
  --expected    {design id: {"stage": ..., "why": ...}}: designs an earlier measurement
                already called broken or unsafe, with the stage they should stop at.
                Every answer that does not reach the targets stage is matched against it,
                and a failure nobody predicted is listed first.

The report gives answers per stage (rows and distinct designs), the rule and
value of every stage 5 and 6 failure, defects, the score distribution, time
per answer, and every answer that does not reach the targets stage with its
reasons.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Optional, Sequence

from rocket_reward import ladder
from rocket_reward.cli import read_numbered_rows
from rocket_reward.records import Requirements, Result

FAIL_STAGES = ("format", "parts", "motor", "limits", "build", "flight", "dropped")


# --------------------------------------------------------------------------- reading

def _answer_text(row: Any) -> str:
    if not isinstance(row, dict):
        return ""
    msgs = row.get("messages")
    if isinstance(msgs, list) and msgs and isinstance(msgs[-1], dict):
        return str(msgs[-1].get("content") or "")
    return str(row.get("content") or row.get("answer") or "")


def _block_hash(text: str) -> str:
    """Rows asking for the same rocket share one design block; group by it."""
    start, end = text.find("<design>"), text.rfind("</design>")
    body = text[start:end] if 0 <= start < end else text
    return hashlib.sha256(body.encode("utf-8", errors="replace")).hexdigest()[:10]


def reference_rows(meta_path: Path, prompts_path: Path, limit: Optional[int] = None) -> list[dict[str, Any]]:
    """Reference rows joined with their parsed requirements (see the module notes)."""
    parsed = [row for _, row in read_numbered_rows(prompts_path) if isinstance(row, dict)]
    by_id: dict[str, dict] = {}
    by_text: dict[str, dict] = {}
    for p in parsed:
        by_id.setdefault(str(p.get("id", "")).split(":")[0], p)
        by_text.setdefault(str(p.get("prompt_text", "")), p)
    out = []
    for _, m in read_numbered_rows(meta_path):
        if not isinstance(m, dict):
            continue
        p = by_id.get(str(m.get("id"))) or by_text.get(str(m.get("prompt_text")))
        text = _answer_text(m)
        out.append({"id": m.get("id"), "design": m.get("group_id") or m.get("id"), "block": _block_hash(text),
                    "split": m.get("split"), "answer": text, "truncated": False,
                    "requirements": p.get("requirements") if p else None,
                    "joined_by": None if p is None else ("id" if by_id.get(str(m.get("id"))) is p else "prompt")})
    return out[:limit] if limit else out


def answer_rows(answers_path: Path, requirements_path: Path) -> list[dict[str, Any]]:
    """Answer rows with requirements from a {id: record} file."""
    with open(requirements_path, encoding="utf-8") as fh:
        reqs = json.load(fh)
    out = []
    for _, r in read_numbered_rows(answers_path):
        if not isinstance(r, dict):
            continue
        text = _answer_text(r)
        out.append({"id": r.get("id"), "design": r.get("id"), "block": _block_hash(text), "split": None,
                    "answer": text, "truncated": bool(r.get("truncated")),
                    "requirements": reqs.get(r.get("id")), "joined_by": "id"})
    return out


# --------------------------------------------------------------------------- scoring

def _findings(result: Result) -> list[dict[str, Any]]:
    """Rule, value and limit of every problem the stopping stage found (stages 5 and 6)."""
    info = result.flags.get("stage_info") if isinstance(result.flags, dict) else None
    if not isinstance(info, dict):
        return []
    if result.stage == "build":
        return [{"rule": f.get("rule"), "value": f.get("value"), "limit": f.get("limit"),
                 "size": f.get("size"), "defect": f.get("defect")}
                for f in info.get("findings") or [] if isinstance(f, dict)]
    if result.stage == "flight":
        worst = info.get("worst_flight")
        per = info.get("flight_violations") or []
        rows = per[worst] if isinstance(worst, int) and 0 <= worst < len(per) else []
        out = [{"rule": v.get("rule"), "size": v.get("size"), "flight": worst} for v in rows if isinstance(v, dict)]
        if info.get("static_violation"):
            out.append({"rule": "pad_stability", "size": info.get("static_violation"),
                        "value": info.get("static_stability_cal")})
        out += [{"rule": "opens_low", "size": s} for s in info.get("low_opening_violations") or []]
        return out
    return []


def score_rows(rows: list[dict[str, Any]], workers: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Score every row with a fresh pool of `workers` helpers; returns per-row results and timing."""
    from rocket_reward.scoring import ErrorTracker, score_many
    from rocket_reward.sim import SimPool

    fallback = {"id": "missing-requirements", "apogee_m": {"value": 1.0, "kind": "about"}}
    reqs = []
    for r in rows:
        try:
            reqs.append(Requirements.from_dict(r["requirements"]))
            r["requirements_ok"] = True
        except (ValueError, TypeError):
            reqs.append(Requirements.from_dict(fallback))
            r["requirements_ok"] = False
    t0 = time.perf_counter()
    with SimPool(workers) as pool:
        t1 = time.perf_counter()
        results = score_many([r["answer"] for r in rows], reqs, [r["truncated"] for r in rows],
                             simulator=pool, tracker=ErrorTracker(window=10**6, run=10**6))
        t2 = time.perf_counter()
    out = []
    for r, res in zip(rows, results):
        shadow = res.flags.get("shadow") or {}
        out.append({"id": r["id"], "design": r["design"], "block": r["block"], "split": r["split"],
                    "requirements_ok": r["requirements_ok"], "joined_by": r["joined_by"],
                    "stage": res.stage, "score": res.score, "credit": round(res.credit, 6),
                    "reasons": res.reasons, "defects": res.defects, "findings": _findings(res),
                    "metrics": res.metrics,
                    "shadow": {k: shadow.get(k) for k in ("substitutes", "score", "stage", "progress")}
                    if shadow else None,
                    "motor_facts_credit": res.flags.get("motor_facts_credit")})
    timing = {"answers": len(rows), "workers": workers, "pool_start_s": round(t1 - t0, 2),
              "score_s": round(t2 - t1, 2), "s_per_answer": round((t2 - t1) / max(1, len(rows)), 4)}
    return out, timing


# --------------------------------------------------------------------------- summary

def _spread(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"n": 0}
    v = sorted(values)

    def q(p: float) -> float:
        return round(v[min(len(v) - 1, int(p * (len(v) - 1) + 0.5))], 4)

    return {"n": len(v), "min": round(v[0], 4), "p5": q(0.05), "p25": q(0.25), "median": q(0.5),
            "p75": q(0.75), "p95": q(0.95), "max": round(v[-1], 4), "mean": round(statistics.fmean(v), 4)}


def summarize_ladder(results: list[dict[str, Any]], expected: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Counts per stage, failures by design matched with `expected`, score spread, ties."""
    expected = expected or {}
    stage_rows = collections.Counter(r["stage"] for r in results)
    stage_designs = {s: len({r["block"] for r in results if r["stage"] == s}) for s in stage_rows}
    scores = [r["score"] for r in results if r["score"] is not None]
    ties = collections.Counter(round(s, 6) for s in scores)
    top_tie = ties.most_common(1)[0] if ties else (None, 0)
    failing: dict[str, dict[str, Any]] = {}
    for r in results:
        if r["stage"] == "targets":
            continue
        d = failing.setdefault(r["design"], {"design": r["design"], "rows": [], "stages": set(), "scores": set(),
                                             "reasons": r["reasons"], "findings": r["findings"],
                                             "defects": r["defects"]})
        d["rows"].append(r["id"])
        d["stages"].add(r["stage"])
        d["scores"].add(r["score"])
    for d in failing.values():
        e = expected.get(d["design"])
        d["stages"] = sorted(d["stages"])
        d["scores"] = sorted(s for s in d["scores"] if s is not None)
        called_broken = bool(e) and e.get("stage") not in (None, "targets")
        d["predicted"] = called_broken and e.get("stage") in d["stages"]
        # Called broken, but it stops at another stage, for a reason the measurement did not name.
        d["other_stage"] = called_broken and not d["predicted"]
        d["expected"] = e
    reached = {r["design"] for r in results if r["stage"] == "targets"}
    missed = {k: v for k, v in expected.items()
              if v.get("stage") not in (None, "targets") and k in reached and k not in failing}
    defect_designs: dict[str, list[str]] = {}
    for r in results:
        if r["defects"] and r["design"] not in defect_designs:
            defect_designs[r["design"]] = r["defects"]
    t_values = [(r["score"] - ladder.stage("targets").floor) / ladder.stage("targets").width
                for r in results if r["stage"] == "targets" and r["score"] is not None]
    return {
        "rows": len(results), "designs": len({r["block"] for r in results}),
        "stage_rows": dict(stage_rows), "stage_designs": stage_designs,
        "score_spread": _spread(scores), "targets_t_spread": _spread(t_values),
        "distinct_scores": len(ties), "largest_tie": {"score": top_tie[0], "rows": top_tie[1]},
        "band_counts": {s.key: sum(1 for x in scores if s.floor - 1e-9 <= x <= s.top + 1e-9) for s in ladder.STAGES},
        "failing_designs": sorted(failing.values(), key=lambda d: (d["predicted"], d["design"])),
        "unexpected": sorted(d["design"] for d in failing.values() if not d["predicted"] and not d["other_stage"]),
        "other_stage": sorted(d["design"] for d in failing.values() if d["other_stage"]),
        "predicted_but_reached_targets": missed,
        "defects_by_design": defect_designs,
        "requirements_missing": [r["id"] for r in results if not r["requirements_ok"]],
        "quarantined": [r["id"] for r in results if r["stage"] == "dropped"],
    }


def _fmt_finding(f: dict[str, Any]) -> str:
    bits = [str(f.get("rule"))]
    if f.get("value") is not None:
        v = f["value"]
        bits.append(f"value {v:.4g}" if isinstance(v, (int, float)) else f"value {v}")
    if f.get("limit") is not None:
        lim = f["limit"]
        bits.append(f"limit {lim:.4g}" if isinstance(lim, (int, float)) else f"limit {lim}")
    if f.get("size") is not None:
        bits.append(f"size {f['size']:.3g}")
    if f.get("defect"):
        bits.append("(defect)")
    return " ".join(bits)


def ladder_report_md(summary: dict[str, Any], timing: dict[str, Any], title: str) -> str:
    """The Markdown report."""
    s = summary
    out = [f"# {title}", "",
           f"{s['rows']} answers, {s['designs']} distinct design blocks. Scored with {timing['workers']} "
           f"simulator helpers: {timing['score_s']} s, {timing['s_per_answer']} s per answer "
           f"(pool start {timing['pool_start_s']} s).", "",
           "## Where answers stop", "", "| stage | rows | distinct designs |", "|---|---|---|"]
    for st in list(ladder.STAGE_KEYS) + ["dropped"]:
        if st in s["stage_rows"]:
            out.append(f"| {st} | {s['stage_rows'][st]} | {s['stage_designs'][st]} |")
    sp = s["score_spread"]
    out += ["", "## Scores", "",
            "Spread of all scores: " + ", ".join(f"{k} {v}" for k, v in sp.items()), "",
            "Spread of t for answers that reach the targets stage: "
            + ", ".join(f"{k} {v}" for k, v in s["targets_t_spread"].items()), "",
            f"{s['distinct_scores']} distinct scores; the largest group of exact ties is "
            f"{s['largest_tie']['rows']} answers at {s['largest_tie']['score']}.", "",
            "Answers per band: " + ", ".join(f"{k} {v}" for k, v in s["band_counts"].items() if v), ""]
    if s["unexpected"]:
        out += ["## Failures nobody predicted", "",
                "These answers stop before the targets stage for a reason the earlier measurement did not "
                "name. They matter most.", ""]
        for d in s["failing_designs"]:
            if not d["predicted"] and not d["other_stage"]:
                out += _design_lines(d)
    else:
        out += ["## Failures nobody predicted", "", "None: every answer that stops before the targets stage "
                "stops where the earlier measurement said it would.", ""]
    if s["other_stage"]:
        out += ["## Called broken, but stopped at another stage", "",
                "The measurement called these designs broken; they stop at a different stage, for a "
                "reason it did not name.", ""]
        for d in s["failing_designs"]:
            if d["other_stage"]:
                out += _design_lines(d)
    out += ["## Predicted failures", ""]
    for d in s["failing_designs"]:
        if d["predicted"]:
            out += _design_lines(d)
    if s["predicted_but_reached_targets"]:
        out += ["## Called broken or unsafe, but reached the targets stage", ""]
        for k, v in sorted(s["predicted_but_reached_targets"].items()):
            out.append(f"- {k}: expected {v.get('stage')} ({v.get('why')})")
        out.append("")
    if s["defects_by_design"]:
        out += ["## Defects (small problems that do not stop the ladder)", ""]
        for k, v in sorted(s["defects_by_design"].items()):
            out.append(f"- {k}: " + "; ".join(v))
        out.append("")
    if s["requirements_missing"]:
        out += ["## Rows without usable requirements", "", ", ".join(map(str, s["requirements_missing"])), ""]
    if s["quarantined"]:
        out += ["## Quarantined (the reward crashed)", "", ", ".join(map(str, s["quarantined"])), ""]
    return "\n".join(out) + "\n"


def _design_lines(d: dict[str, Any]) -> list[str]:
    e = d.get("expected") or {}
    lines = [f"### {d['design']}: {', '.join(d['stages'])} (scores {', '.join(f'{x:.4f}' for x in d['scores'])})", "",
             f"Rows: {', '.join(map(str, d['rows']))}.",
             f"Predicted: {'yes' if d['predicted'] else ('another stage' if d['other_stage'] else 'no')}"
             + (f" (expected {e.get('stage')}: {e.get('why')})" if e else "") + "."]
    if d["findings"]:
        lines.append("Rules: " + "; ".join(_fmt_finding(f) for f in d["findings"] if not f.get("defect")) + ".")
    lines.append("")
    lines += [f"- {x}" for x in d["reasons"]]
    lines.append("")
    return lines


# --------------------------------------------------------------------------- main

def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--meta", type=Path, help="reference rows (.jsonl)")
    ap.add_argument("--prompts", type=Path, help="parsed prompts with requirements (.jsonl)")
    ap.add_argument("--answers", type=Path, help="answer rows (.jsonl or .jsonl.gz) instead of --meta")
    ap.add_argument("--requirements", type=Path, help="{answer id: requirements} for --answers")
    ap.add_argument("--expected", type=Path, help="{design id: {stage, why}} predicted failures")
    ap.add_argument("--out", type=Path, required=True, help="Markdown report to write")
    ap.add_argument("--json", type=Path, required=True, help="JSON report to write")
    ap.add_argument("--workers", type=int, default=4, help="simulator helpers (default 4)")
    ap.add_argument("--limit", type=int, default=None, help="score only the first N rows")
    ap.add_argument("--title", default="The whole ladder on the reference answers", help="report heading")
    a = ap.parse_args(argv)
    if a.answers:
        if not a.requirements:
            ap.error("--answers needs --requirements")
        rows = answer_rows(a.answers, a.requirements)
        rows = rows[:a.limit] if a.limit else rows
    else:
        if not (a.meta and a.prompts):
            ap.error("give --meta and --prompts, or --answers and --requirements")
        rows = reference_rows(a.meta, a.prompts, a.limit)
    expected = {}
    if a.expected:
        with open(a.expected, encoding="utf-8") as fh:
            expected = json.load(fh)
    results, timing = score_rows(rows, a.workers)
    summary = summarize_ladder(results, expected)
    with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(ladder_report_md(summary, timing, a.title))
    with open(a.json, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"timing": timing, "summary": summary, "results": results}, fh, ensure_ascii=False, indent=1,
                  default=str)
        fh.write("\n")
    print(json.dumps({"timing": timing, "stage_rows": summary["stage_rows"], "unexpected": summary["unexpected"],
                      "other_stage": summary["other_stage"],
                      "predicted_but_reached_targets": sorted(summary["predicted_but_reached_targets"])},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
