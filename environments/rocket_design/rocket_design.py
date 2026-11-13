"""Prime Intellect `verifiers` environment (v1 API, verifiers >= 0.4) for rocket design RL. Self-hosted: no
Prime sandbox or API key.

The model gets a mission prompt and must answer with <thought>...</thought> and the OpenRocket tree as JSON
inside <design>...</design> (the sft_v5 format). Each answer is scored by scripts/reward.py, the repo's reward
ladder: format, structure, motors, cad, flight (OpenRocket), targets. reward = gates passed / 6, in 0..1.

In verifiers v1 an environment is a *taskset* package: this module exports a Taskset (the prompts), its Task
(scoring: one @vf.reward plus per-gate @vf.metric numbers) and a harness. The harness is verifiers' "null"
harness, a plain chat call with no tools, which is what a single-answer design task needs.

    uv pip install --python .venv/bin/python verifiers
    uv pip install --python .venv/bin/python -e environments/rocket_design
    .venv/bin/python scripts/check_rocket_env.py model_out/results_val.json      # no GPU, no model
    vf-run rocket-design ...    /  prime-rl:  --env.taskset.id rocket-design

Options (all have defaults):  --env.taskset.prompts-file, --env.taskset.task.workers, ...task.flight,
...task.cad, ...task.motor-lookup, ...task.timeout-s

Scoring runs in worker processes, each with its own OpenRocket JVM, because OpenRocket keeps global state and
is not safe to share between threads. Set task.workers to about the number of free CPU cores.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import threading
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from pathlib import Path

import verifiers.v1 as vf
from verifiers.v1.harnesses.null import NullHarness

# environments/rocket_design/rocket_design.py -> repo root, unless ROCKETDATA_REPO says otherwise
REPO = Path(os.environ.get("ROCKETDATA_REPO") or Path(__file__).resolve().parents[2])

# The system prompt the v5 model was fine-tuned with (new_results/sft_v5.jsonl). RL has to use the same one.
SYSTEM_PROMPT = (
    "You are an aerospace design assistant. Explain the airframe, propulsion, stability, and recovery choices "
    "inside <thought> tags, then output the complete OpenRocket design JSON inside <design> tags. Distinguish "
    "stored reference-flight results from static calculations. Do not claim to have run tools or guarantee "
    "flight safety. State missing data and safety limits."
)
GATES = ["format", "structure", "motors", "cad", "flight", "targets"]


def repo_path(p):
    return p if not p or os.path.isabs(p) else str(REPO / p)


# ----------------------------------------------------------------------------------------- scoring
_REWARD = None
_LOOKUPS = {}


def _reward_module():
    global _REWARD
    if _REWARD is None:
        for p in (REPO, REPO / "scripts"):
            if str(p) not in sys.path:
                sys.path.insert(0, str(p))
        import reward  # scripts/reward.py
        _REWARD = reward
    return _REWARD


def _lookup(path):
    if path and path not in _LOOKUPS:
        _LOOKUPS[path] = json.load(open(path, encoding="utf-8"))
    return _LOOKUPS.get(path)


def _failed(gate, reason):
    return {"score": 0.0, "gate_failed": gate, "reasons": [reason], "gates": {g: "not reached" for g in GATES},
            "unverified": [], "slop": False, "metrics": {}}


def score_one(content, prompt, finish, opts):
    """Score one answer with scripts/reward.py. Runs in a worker process (or a thread when workers=0).
    Never raises: a crash in the reward code scores 0 and says why."""
    try:
        rw = _reward_module()
        res = rw.score_answer(content, prompt, lookup=_lookup(opts["motor_lookup"]), finish=finish,
                              flight=opts["flight"], cad=opts["cad"], seed=opts["seed"])
    except Exception as e:  # noqa: BLE001
        res = _failed("reward_error", f"{type(e).__name__}: {e}"[:300])
    return json.loads(json.dumps(res, default=str))  # plain JSON types, safe to pass between processes


def _compile_or_batch_once():
    try:
        _reward_module()
        import or_headless as orh  # scripts/or_headless.py
        jar = orh._jar()
        if jar.exists():
            orh._compile_or_batch(str(jar))
    except Exception as e:  # noqa: BLE001  the flight gate reports the real problem later
        print(f"[rocket_design] could not precompile OrBatch: {type(e).__name__}: {e}", file=sys.stderr)


class RocketScorer:
    def __init__(self, opts, workers, timeout_s):
        self.opts, self.timeout_s = opts, timeout_s
        if opts["flight"] and workers > 0:
            _compile_or_batch_once()  # so the worker processes don't all compile OrBatch.java at the same time
        self.pool = (ProcessPoolExecutor(max_workers=workers, mp_context=get_context("spawn"))
                     if workers > 0 else None)
        self.lock = threading.Lock()  # workers=0: one OpenRocket JVM in this process, one sim at a time

    def _in_thread(self, content, prompt, finish):
        with self.lock:
            return score_one(content, prompt, finish, self.opts)

    async def score(self, content, prompt, finish):
        loop = asyncio.get_running_loop()
        if self.pool is not None:
            fut = loop.run_in_executor(self.pool, score_one, content, prompt, finish, self.opts)
        else:
            fut = loop.run_in_executor(None, self._in_thread, content, prompt, finish)
        try:
            return await asyncio.wait_for(fut, self.timeout_s)
        except asyncio.TimeoutError:
            return _failed("timeout", f"scoring took over {self.timeout_s:g} s")


_SCORERS = {}


def scorer_for(cfg) -> RocketScorer:
    """One scorer (and process pool) per distinct set of options, shared by every task."""
    lookup = repo_path(cfg.motor_lookup)
    if lookup and not os.path.exists(lookup):
        print(f"[rocket_design] {lookup} not found: motors are checked against data/catalog.sqlite only "
              f"(weaker). Get it from branch sft-v5-data.", file=sys.stderr)
        lookup = None
    opts = {"motor_lookup": lookup, "flight": bool(cfg.flight), "cad": bool(cfg.cad), "seed": int(cfg.seed)}
    key = (json.dumps(opts, sort_keys=True), int(cfg.workers), float(cfg.timeout_s))
    if key not in _SCORERS:
        _SCORERS[key] = RocketScorer(opts, int(cfg.workers), float(cfg.timeout_s))
    return _SCORERS[key]


# ----------------------------------------------------------------------------------------- task
class RocketTaskConfig(vf.TaskConfig):
    motor_lookup: str | None = "new_results/sft_v4_motor_lookup.json"
    """motor_id -> motor file map (branch sft-v5-data). Missing file: the weaker catalog-name check."""
    flight: bool = True
    """Run the OpenRocket gate. Off: flight and targets count as not passed (see scripts/reward.py)."""
    cad: bool = True
    """Run the CadQuery solid checks (the fit checks of the cad gate always run)."""
    workers: int = 4
    """Scoring processes, each with its own OpenRocket JVM (0 = one, inside the env process)."""
    seed: int = 0
    timeout_s: float = 300.0
    """An answer whose scoring takes longer than this scores 0."""


class RocketData(vf.TaskData):
    difficulty: str | None = None


class RocketTask(vf.Task[RocketData, vf.State, RocketTaskConfig]):
    async def ladder(self, task: RocketData, trace) -> dict:
        """The full reward.py result for this answer, computed once and kept on trace.info["rocket"]."""
        res = trace.info.get("rocket")
        if res is None:
            finish = "length" if trace.is_truncated else "stop"
            res = await scorer_for(self.config).score(trace.last_reply, task.prompt_text, finish)
            trace.info["rocket"] = res
        return res

    @vf.metric
    async def gates(self, task: RocketData, trace) -> dict:
        """Weight 0, logged only: which gates each answer passed, so you can see where the model is stuck."""
        res = await self.ladder(task, trace)
        out = {f"passed_{g}": 1.0 if str(res["gates"].get(g, "")).startswith("pass") else 0.0 for g in GATES}
        out["slop"] = 1.0 if res.get("slop") else 0.0
        return out

    @vf.reward(weight=1.0)
    async def rocket_reward(self, task: RocketData, trace) -> float:
        """The reward ladder score, 0..1 (gates passed / 6)."""
        return float((await self.ladder(task, trace))["score"])


# ----------------------------------------------------------------------------------------- taskset
class RocketTasksetConfig(vf.TasksetConfig):
    task: RocketTaskConfig = RocketTaskConfig()
    prompts_file: str = "data/splits/rl_heldout.jsonl"
    """JSONL of mission prompts: "prompt" (a string or chat messages) or "messages". Relative to the repo.
    Only the user text is used; the system prompt is always the v5 training one."""


def user_text(row):
    """The mission text from a prompts row: "prompt" as a string, or the user turn of "prompt"/"messages"."""
    p = row.get("prompt", row.get("messages"))
    if isinstance(p, str):
        return p.strip()
    if isinstance(p, list):
        users = [m.get("content", "") for m in p if isinstance(m, dict) and m.get("role") == "user"]
        if users:
            return users[0].strip()
    raise ValueError(f"row has no prompt text: {str(row)[:120]}")


class RocketTaskset(vf.Taskset[RocketTask, RocketTasksetConfig]):
    def load(self):
        path = repo_path(self.config.prompts_file)
        n = 0
        for i, line in enumerate(open(path, encoding="utf-8")):
            if not line.strip():
                continue
            row = json.loads(line)
            data = RocketData(id=str(row.get("id", f"line-{i + 1}")), prompt=user_text(row),
                              system_prompt=SYSTEM_PROMPT, difficulty=row.get("difficulty"))
            n += 1
            yield RocketTask(data, self.config.task)
        if not n:
            raise ValueError(f"no prompts in {path}")


class RocketHarness(NullHarness):
    """Plain chat, no tools: the model answers once and the answer is scored."""


__all__ = ["RocketTaskset", "RocketTasksetConfig", "RocketTask", "RocketTaskConfig", "RocketData",
           "RocketHarness"]
