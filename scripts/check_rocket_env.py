"""Check the rocket-design verifiers environment without a GPU or a model.

    python scripts/check_rocket_env.py
    python scripts/check_rocket_env.py rocket_reward/tests/data/gold_val.jsonl.gz --limit 8
    python scripts/check_rocket_env.py model_out/results_val.json --requirements rocket_reward/prompts/rl_prompts_v1.jsonl

1. verifiers loads the installed 'rocket-design' taskset across train/val/test and resolves RocketHarness
2. checks edge cases on real Task.score: single-flight caching, rescore invalidation, truncation via
   calls[-1].finish_reason == "length", and quarantine trace.drop(...)
3. scores saved answers through verifiers' Task.score and checks exact match against rocket_reward.scoring.score_many
"""
from __future__ import annotations

import argparse
import asyncio
import collections
import gzip
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import verifiers.v1 as vf  # noqa: E402

import rocket_design as rd  # noqa: E402  (installed with: uv pip install -e environments/rocket_design)
from rocket_reward import scoring  # noqa: E402
from rocket_reward.cli import answer_of, read_rows  # noqa: E402
from rocket_reward.records import Requirements, Result  # noqa: E402

DEFAULT_ANSWERS = "rocket_reward/tests/data/model_val.jsonl.gz"
DEFAULT_REQUIREMENTS = "rocket_reward/tests/data/model_val_requirements.json"


class FakeCall:
    def __init__(self, finish_reason: str = "stop", error: str | None = None):
        self.finish_reason = finish_reason
        self.error = error


class AnswerTrace:
    """The parts of a verifiers Trace that Task.score reads and writes, filled from one saved answer."""

    def __init__(self, reply: str | None, truncated: bool):
        self.last_reply = reply or ""
        self.is_truncated = truncated
        self.is_format_violation = False
        self.has_error = False
        self.calls: list = [FakeCall("length" if truncated else "stop")]
        self.assistant_messages: list = []
        self.info: dict = {}
        self.metrics: dict = {}
        self.rewards: dict = {}
        self.dropped: str | None = None

    def record_metric(self, name: str, value: float) -> None:
        self.metrics[name] = float(value)

    def record_metrics(self, values: dict[str, float]) -> None:
        for k, v in values.items():
            self.record_metric(k, v)

    def record_reward(self, name: str, value: float, weight: float = 1.0) -> None:
        self.rewards[name] = float(value) * float(weight)

    def drop(self, reason: str) -> None:
        if self.dropped is None:
            self.dropped = reason


def load_answers(path: Path) -> list[dict]:
    if path.suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        return data["results"] if isinstance(data, dict) and "results" in data else data
    rows = []
    for rid, row in read_rows(path):
        if isinstance(row, dict):
            row = dict(row)
            row.setdefault("id", rid)
            rows.append(row)
    return rows


def load_requirements_map(path: Path) -> dict[str, dict]:
    if path.suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "apogee_m" not in data:
            return data
        if isinstance(data, list):
            return {r["id"]: r for r in data}
        return {"*": data}
    opener = gzip.open if path.name.endswith(".gz") else open
    out: dict[str, dict] = {}
    with opener(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            row = json.loads(line)
            if "requirements" in row:
                out[row["id"]] = row["requirements"]
            elif "id" in row:
                out[row["id"]] = row
    return out


def is_truncated(row: dict) -> bool:
    val = row.get("truncated")
    if isinstance(val, bool):
        return val
    return str(val).lower() == "true"


def check_edge_cases() -> None:
    """Verify single-call caching, rescore invalidation, truncation via calls, and quarantine drop."""
    req = {"id": "edge-1", "apogee_m": {"value": 500.0, "kind": "about"}}
    data = rd.RocketData(id="edge-1", prompt="test", system_prompt=rd.SYSTEM_PROMPT, requirements=req)
    task = rd.RocketTask(data, rd.RocketTaskConfig(workers=0))

    calls = 0
    orig_score = scoring.score

    def counted_score(text, req_obj, cut=False, sim=None):
        nonlocal calls
        calls += 1
        if text == "QUARANTINE":
            return Result(score=None, stage="dropped", stages_passed=1, credit=0.0, flags={"error": "boom"})
        if cut:
            return Result(score=0.0, stage="format", stages_passed=0, credit=0.0)
        return Result(score=0.42, stage="build", stages_passed=4, credit=0.25)

    scoring.score = counted_score
    try:
        # Single scoring call across both @vf.metric and @vf.reward
        tr = AnswerTrace("some design", truncated=False)
        asyncio.run(task.score(tr))
        assert calls == 1, f"expected 1 score call per rollout, got {calls}"
        assert tr.rewards["rocket_reward"] == 0.42
        assert tr.metrics["rocket_stages_passed"] == 4.0

        # Truncation detected via calls[-1].finish_reason == "length" even if is_truncated is False
        tr_cut = AnswerTrace("some design", truncated=False)
        tr_cut.calls = [FakeCall("length")]
        asyncio.run(task.score(tr_cut))
        assert tr_cut.rewards["rocket_reward"] == 0.0
        assert tr_cut.info[rd.RESULT_INFO_KEY]["truncated"] is True

        # Rescore with changed requirements recomputes instead of reusing stale trace.info
        req2 = {"id": "edge-1", "apogee_m": {"value": 900.0, "kind": "about"}}
        task2 = rd.RocketTask(
            rd.RocketData(id="edge-1", prompt="test", system_prompt=rd.SYSTEM_PROMPT, requirements=req2),
            rd.RocketTaskConfig(workers=0),
        )
        before = calls
        asyncio.run(task2.score(tr))
        assert calls == before + 1, "rescore with changed requirements should recompute"

        # Quarantine drops trace, leaves reward None and metrics empty, and is NOT cached across rescore
        tr_q = AnswerTrace("QUARANTINE", truncated=False)
        before_q = calls
        asyncio.run(task.score(tr_q))
        assert calls == before_q + 1, "quarantined rollout should still score only once per Task.score"
        assert tr_q.rewards["rocket_reward"] is None
        assert tr_q.metrics == {}
        assert tr_q.dropped and "boom" in tr_q.dropped
        assert rd.RESULT_INFO_KEY not in tr_q.info
        # Rescoring via real verifiers Task.rescore() retries quarantined traces
        asyncio.run(task.rescore(tr_q))
        assert calls == before_q + 2, "rescoring a quarantined trace must retry scoring"
    finally:
        scoring.score = orig_score


async def score_all(answers: list[dict], reqs_by_id: dict[str, dict], task_cfg: rd.RocketTaskConfig):
    async def one(r: dict):
        rid = r["id"]
        req = r.get("requirements") or reqs_by_id.get(rid) or reqs_by_id.get("*")
        if req is None:
            raise KeyError(f"no requirements found for answer id {rid!r}")
        data = rd.RocketData(id=rid, prompt="", system_prompt=rd.SYSTEM_PROMPT, requirements=req)
        task = rd.RocketTask(data, task_cfg)
        trace = AnswerTrace(answer_of(r), is_truncated(r))
        await task.score(trace)
        return trace

    return await asyncio.gather(*(one(r) for r in answers))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("answers", nargs="?", default=DEFAULT_ANSWERS,
                    help=f"saved answers (.json, .jsonl, or .jsonl.gz; default {DEFAULT_ANSWERS})")
    ap.add_argument("--requirements", default=DEFAULT_REQUIREMENTS,
                    help=f"requirements file (.json or .jsonl; default {DEFAULT_REQUIREMENTS})")
    ap.add_argument("--prompts-file", default=None,
                    help="override RocketTasksetConfig.prompts_file for step 1 check")
    ap.add_argument("--splits", default="train,val,test",
                    help="comma-separated splits to check in step 1 (default train,val,test)")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()

    task_cfg = rd.RocketTaskConfig(workers=a.workers)
    ts_kwargs = {"id": "rocket-design", "task": task_cfg}
    if a.prompts_file:
        ts_kwargs["prompts_file"] = a.prompts_file

    print(f"1. verifiers {getattr(__import__('verifiers'), '__version__', '?')}: loading taskset 'rocket-design'")
    for split in [s.strip() for s in a.splits.split(",") if s.strip()]:
        taskset = vf.load_taskset(rd.RocketTasksetConfig(split=split, **ts_kwargs))
        tasks = list(taskset)
        print(f"   split={split:5s}: {len(tasks):4d} prompts | first: {tasks[0].data.prompt_text[:90]}")
        assert tasks[0].data.system_prompt == rd.SYSTEM_PROMPT, "system prompt is not the v5 one"
        assert isinstance(tasks[0].data.requirements, dict) and "apogee_m" in tasks[0].data.requirements

    hid = vf.default_harness_id("rocket-design")
    harness = vf.load_harness(vf.HarnessConfig(id=hid))
    print(f"   harness: {hid} -> {type(harness).__name__} (plain chat, no tools)")
    assert hid == "rocket-design", f"default harness resolved to {hid!r}, not this package's plain-chat harness"

    print("\n2. checking edge cases (single-flight cache, truncation, rescore invalidation, quarantine drop)")
    check_edge_cases()
    print("   ok")

    answers = load_answers(Path(rd.repo_path(a.answers)))
    if a.limit:
        answers = answers[:a.limit]
    reqs_by_id = load_requirements_map(Path(rd.repo_path(a.requirements))) if a.requirements else {}

    print(f"\n3. scoring {len(answers)} answers through verifiers' Task.score ({a.workers} OpenRocket helpers)")
    t = time.time()
    traces = asyncio.run(score_all(answers, reqs_by_id, task_cfg))
    print(f"   done in {time.time() - t:.1f} s")
    print(f"   logged per answer: rewards {sorted(traces[0].rewards)}, metrics {sorted(traces[0].metrics)}")

    print("\n4. same answers through rocket_reward.scoring.score_many directly")
    texts = [answer_of(r) or "" for r in answers]
    req_objs = [Requirements.from_dict(r.get("requirements") or reqs_by_id.get(r["id"]) or reqs_by_id["*"])
                for r in answers]
    cuts = [is_truncated(r) for r in answers]
    direct_results = scoring.score_many(texts, req_objs, truncated=cuts, simulator=rd.pool_for(a.workers))

    mismatch: list[str] = []
    stage_counts: collections.Counter[str] = collections.Counter()
    for r, tr, direct in zip(answers, traces, direct_results):
        res = tr.info[rd.RESULT_INFO_KEY]
        env_score = tr.rewards.get("rocket_reward")
        same_score = (
            (direct.score is None and env_score is None and tr.dropped is not None)
            or (direct.score is not None and env_score is not None and abs(direct.score - env_score) <= 1e-9)
        )
        if not same_score or direct.stage != res["stage"] or direct.stages_passed != res["stages_passed"]:
            mismatch.append(
                f"{r['id']}: env {env_score} ({res['stage']}) vs direct {direct.score} ({direct.stage})"
            )
        stage_counts[res["stage"]] += 1

    scored = [tr.rewards["rocket_reward"] for tr in traces if tr.rewards.get("rocket_reward") is not None]
    mean = sum(scored) / len(scored) if scored else 0.0
    print(f"\nmean reward {mean:.4f} over {len(scored)}/{len(traces)} scored answers")
    print("where answers stopped:")
    for stage in rd.STAGES + ["dropped"]:
        if stage_counts[stage]:
            print(f"   {stage:12s} {stage_counts[stage]:3d}")
    if mismatch:
        print(f"\nFAIL: {len(mismatch)} answers scored differently through the environment")
        for m in mismatch[:20]:
            print("  ", m)
        sys.exit(1)
    print("\nPASS: the environment gives exactly the same score and stage as rocket_reward for every answer")


if __name__ == "__main__":
    try:
        main()
    finally:
        rd.close_pools()
