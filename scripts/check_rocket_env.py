"""Check the rocket-design verifiers environment without a GPU or a model.

    .venv/bin/python scripts/check_rocket_env.py model_out/results_val.json
    .venv/bin/python scripts/check_rocket_env.py model_out/results_val.json --limit 5 --no-flight

1. verifiers finds the installed environment by its id ("rocket-design"): the taskset loads the prompts with
   the v5 system prompt, and the harness resolves to plain chat (no tools)
2. saved model answers (a results_<label>.json from sft/eval_test.py) are scored through verifiers' own
   scoring code (Task.score: the @vf.metric and @vf.reward methods), the path the RL trainer uses
3. the same answers are scored by scripts/reward.py directly, and every score must match

Saved answers have no prompt attached, so the motor-the-prompt-asked-for and target-apogee checks only run when
--test gives the prompts file the answers came from (rows are matched by id, as eval_test.py does).
"""
import argparse
import asyncio
import collections
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO))

import verifiers.v1 as vf  # noqa: E402

import rocket_design as rd  # noqa: E402  (installed with: uv pip install -e environments/rocket_design)


class AnswerTrace:
    """The parts of a verifiers Trace that Task.score reads and writes, filled from one saved answer."""

    def __init__(self, reply, truncated):
        self.last_reply, self.is_truncated = (reply or "").strip(), truncated
        self.is_format_violation = False
        self.info, self.metrics, self.rewards = {}, {}, {}

    def record_metric(self, name, value):
        self.metrics[name] = float(value)

    def record_metrics(self, values):
        for k, v in values.items():
            self.record_metric(k, v)

    def record_reward(self, name, value, weight=1.0):
        self.rewards[name] = float(value) * float(weight)


def prompts_by_id(test_path):
    if not test_path:
        return {}
    ev = rd._reward_module().ev  # sft/eval_test.py, for its row ids
    return {r["id"]: rd.user_text(r) for r in ev.load_rows(test_path)}


async def score_all(answers, prompts, task_cfg):
    async def one(r):
        data = rd.RocketData(id=r["id"], prompt=prompts.get(r["id"], ""), system_prompt=rd.SYSTEM_PROMPT)
        task = rd.RocketTask(data, task_cfg)
        trace = AnswerTrace(r.get("content"), str(r.get("truncated")) == "True")
        await task.score(trace)
        return trace
    return await asyncio.gather(*(one(r) for r in answers))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results", help="results_<label>.json written by sft/eval_test.py")
    ap.add_argument("--test", help="the prompts file those answers came from (optional)")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--no-flight", action="store_true")
    ap.add_argument("--no-cad", action="store_true")
    a = ap.parse_args()
    task_cfg = rd.RocketTaskConfig(workers=a.workers, flight=not a.no_flight, cad=not a.no_cad)

    print(f"1. verifiers {getattr(__import__('verifiers'), '__version__', '?')}: loading taskset 'rocket-design'")
    taskset = vf.load_taskset(rd.RocketTasksetConfig(id="rocket-design", task=task_cfg))
    tasks = list(taskset)
    print(f"   ok: {type(taskset).__name__}, {len(tasks)} prompts")
    print(f"   first prompt: {tasks[0].data.prompt_text[:110]}")
    assert tasks[0].data.system_prompt == rd.SYSTEM_PROMPT, "system prompt is not the v5 one"
    hid = vf.default_harness_id("rocket-design")
    harness = vf.harness_class(hid) if hasattr(vf, "harness_class") else None
    print(f"   harness: {hid} -> {getattr(harness, '__name__', '?')} (plain chat, no tools)")
    assert hid == "rocket-design", f"default harness resolved to {hid!r}, not this package's plain-chat harness"

    data = json.load(open(a.results, encoding="utf-8"))
    answers = data["results"] if isinstance(data, dict) else data
    if a.limit:
        answers = answers[:a.limit]
    prompts = prompts_by_id(a.test)

    print(f"\n2. scoring {len(answers)} answers through verifiers' Task.score ({a.workers} worker processes)")
    t = time.time()
    traces = asyncio.run(score_all(answers, prompts, task_cfg))
    print(f"   done in {time.time() - t:.0f} s")
    print(f"   logged per answer: rewards {sorted(traces[0].rewards)}, metrics {sorted(traces[0].metrics)}")

    print("\n3. same answers through scripts/reward.py directly")
    rw = rd._reward_module()
    lookup_path = rd.repo_path(task_cfg.motor_lookup)
    lookup = rd._lookup(lookup_path) if Path(lookup_path).exists() else None
    mismatch, gate_fail, unverified = [], collections.Counter(), collections.Counter()
    for r, tr in zip(answers, traces):
        res, score = tr.info["rocket"], tr.rewards.get("rocket_reward")
        finish = "length" if str(r.get("truncated")) == "True" else "stop"
        direct = rw.score_answer((r.get("content") or "").strip(), prompts.get(r["id"], ""), lookup=lookup,
                                 finish=finish, flight=task_cfg.flight, cad=task_cfg.cad, seed=0)
        if score is None or abs(direct["score"] - score) > 1e-9 or direct["gate_failed"] != res["gate_failed"]:
            mismatch.append(f"{r['id']}: env {score} ({res['gate_failed']}) vs direct {direct['score']} "
                            f"({direct['gate_failed']})")
        gate_fail[res["gate_failed"] or "cleared all gates"] += 1
        for u in res.get("unverified", []):
            unverified[u.split(":")[0]] += 1

    scores = [tr.rewards.get("rocket_reward") or 0.0 for tr in traces]
    print(f"\nmean reward {sum(scores) / len(scores):.3f} over {len(scores)} answers")
    print("where answers stopped:")
    for g in rd.GATES + ["reward_error", "timeout", "cleared all gates"]:
        if gate_fail[g]:
            print(f"   {g:18s} {gate_fail[g]:3d}")
    if unverified:
        print("gates that could not run (count as not passed):", dict(unverified))
    if lookup is None:
        print("NOTE: new_results/sft_v4_motor_lookup.json is missing, so motors were checked against the catalog only")
    if mismatch:
        print(f"\nFAIL: {len(mismatch)} answers scored differently through the environment")
        for m in mismatch[:20]:
            print("  ", m)
        sys.exit(1)
    print("\nPASS: the environment gives exactly the same score as scripts/reward.py for every answer")


if __name__ == "__main__":
    main()
