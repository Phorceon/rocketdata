"""Prime Intellect `verifiers` environment (v1 API, verifiers >= 0.4) for rocket design RL. Self-hosted: no
Prime sandbox or API key.

The model gets a mission prompt and must answer with <thought>...</thought> and the OpenRocket tree as JSON
inside <design>...</design> (the sft_v5 format). Each answer is scored by `rocket_reward`, the repo's
seven-stage reward ladder (format, parts, motor, limits, build, flight, targets) backed by OpenRocket 24.12.

In verifiers v1 an environment is a *taskset* package: this module exports a Taskset (the prompts), its Task
(scoring: one @vf.reward plus per-stage @vf.metric numbers) and a harness. The harness is verifiers' "null"
harness, a plain chat call with no tools, which is what a single-answer design task needs.

    uv pip install --python .venv/bin/python verifiers
    uv pip install --python .venv/bin/python -e environments/rocket_design
    .venv/bin/python -m rocket_reward check
    .venv/bin/python scripts/check_rocket_env.py
    vf-run rocket-design ...    /  prime-rl:  --env.taskset.id rocket-design

Options (all have defaults):  --env.taskset.prompts-file, --env.taskset.split, --env.taskset.task.workers
"""
from __future__ import annotations

import asyncio
import atexit
import gzip
import json
import os
import sys
import threading
from pathlib import Path
from typing import Any

import verifiers.v1 as vf
from verifiers.v1.harnesses.null import NullHarness

# environments/rocket_design/rocket_design.py -> repo root, unless ROCKETDATA_REPO says otherwise
REPO = Path(os.environ.get("ROCKETDATA_REPO") or Path(__file__).resolve().parents[2])
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from rocket_reward import ladder, scoring  # noqa: E402
from rocket_reward.adapters.verifiers import (  # noqa: E402
    STAGE_METRIC,
    final_answer,
    task_requirements,
    was_cut_off,
)
from rocket_reward.errors import RewardSetupError  # noqa: E402
from rocket_reward.sim import SimPool  # noqa: E402

# The system prompt the v5 model was fine-tuned with (also stored per row in rl_prompts_v1.jsonl).
SYSTEM_PROMPT = (
    "You are an aerospace design assistant. Explain the airframe, propulsion, stability, and recovery choices "
    "inside <thought> tags, then output the complete OpenRocket design JSON inside <design> tags. Distinguish "
    "stored reference-flight results from static calculations. Do not claim to have run tools or guarantee "
    "flight safety. State missing data and safety limits."
)
STAGES = list(ladder.STAGE_KEYS)


def repo_path(p: str) -> str:
    return p if not p or os.path.isabs(p) else str(REPO / p)


# ----------------------------------------------------------------------------------------- simulator pool
_POOL_LOCK = threading.Lock()
_POOLS: dict[int, SimPool] = {}
_ATEXIT_REGISTERED = False


def close_pools() -> None:
    with _POOL_LOCK:
        pools = list(_POOLS.values())
        _POOLS.clear()
    for pool in pools:
        pool.close()


def pool_for(workers: int) -> SimPool | None:
    """Shared SimPool of `workers` OpenRocket helpers (0 = use rocket_reward's default pool)."""
    global _ATEXIT_REGISTERED
    n = int(workers)
    if n <= 0:
        return None
    with _POOL_LOCK:
        pool = _POOLS.get(n)
        if pool is None:
            pool = SimPool(n)
            _POOLS[n] = pool
            if not _ATEXIT_REGISTERED:
                atexit.register(close_pools)
                _ATEXIT_REGISTERED = True
        return pool


# ----------------------------------------------------------------------------------------- task
class RocketTaskConfig(vf.TaskConfig):
    workers: int = 4
    """OpenRocket helper processes in SimPool (0 = use rocket_reward default / ROCKET_REWARD_WORKERS)."""


class RocketData(vf.TaskData):
    requirements: dict[str, Any]
    split: str | None = None
    family: str | None = None
    prompt_style: str | None = None
    leaks_family: bool | None = None


class RocketTask(vf.Task[RocketData, vf.State, RocketTaskConfig]):
    async def evaluate(self, task: RocketData, trace) -> dict[str, Any]:
        """Score once with rocket_reward and cache the JSON-safe Result dict on trace.info["rocket_reward"]."""
        res = trace.info.get("rocket_reward")
        if res is None:
            req = task_requirements(task)
            text = final_answer(trace)
            cut = was_cut_off(trace)
            pool = pool_for(self.config.workers)
            result = await asyncio.to_thread(scoring.score, text, req, cut, pool)
            res = result.to_dict()
            trace.info["rocket_reward"] = res
        return res

    @vf.metric
    async def stages(self, task: RocketData, trace) -> dict[str, float]:
        """Weight 0, logged only: stages passed (0..7) and per-stage pass indicators."""
        res = await self.evaluate(task, trace)
        if res["score"] is None:
            return {}
        passed = int(res["stages_passed"])
        out: dict[str, float] = {STAGE_METRIC: float(passed)}
        for idx, stage in enumerate(STAGES):
            out[f"passed_{stage}"] = 1.0 if passed > idx else 0.0
        return out

    @vf.reward(weight=1.0)
    async def rocket_reward(self, task: RocketData, trace) -> float | None:
        """The seven-stage rocket_reward score in 0..1 (or None + trace.drop when quarantined)."""
        res = await self.evaluate(task, trace)
        if res["score"] is None:
            drop = getattr(trace, "drop", None)
            if not callable(drop):
                raise RewardSetupError(
                    "an answer was quarantined but this trace has no drop() method, so it cannot be "
                    "left out of training; check the verifiers version (0.4.x)"
                )
            drop(f"rocket_reward quarantined the answer: {res.get('flags', {}).get('error', 'unexpected error')}")
            return None
        return float(res["score"])


# ----------------------------------------------------------------------------------------- taskset
class RocketTasksetConfig(vf.TasksetConfig):
    task: RocketTaskConfig = RocketTaskConfig()
    prompts_file: str = "rocket_reward/prompts/rl_prompts_v1.jsonl"
    """JSONL (or .jsonl.gz) of RL prompts with 'prompt' and 'requirements'. Relative to the repo."""
    split: str | None = "train"
    """Which split to load ('train', 'val', 'test'), or None / '' to load every row."""


def user_text(row: dict[str, Any]) -> str:
    """The mission text from a prompts row: 'prompt' as a string, or the user turn of 'prompt'/'messages'."""
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
        want_split = self.config.split or None
        opener = gzip.open if path.endswith(".gz") else open
        n = 0
        with opener(path, "rt", encoding="utf-8") as fh:
            for i, line in enumerate(fh):
                if not line.strip():
                    continue
                row = json.loads(line)
                if want_split is not None and row.get("split") != want_split:
                    continue
                if "requirements" not in row:
                    raise RewardSetupError(f"{path}:{i + 1} has no 'requirements' field")
                data = RocketData(
                    id=str(row.get("id", f"line-{i + 1}")),
                    prompt=user_text(row),
                    system_prompt=row.get("system") or SYSTEM_PROMPT,
                    requirements=row["requirements"],
                    split=row.get("split"),
                    family=row.get("family"),
                    prompt_style=row.get("prompt_style"),
                    leaks_family=row.get("leaks_family"),
                )
                n += 1
                yield RocketTask(data, self.config.task)
        if not n:
            raise ValueError(f"no prompts in {path} (split={want_split!r})")


class RocketHarness(NullHarness):
    """Plain chat, no tools: the model answers once and the answer is scored."""


__all__ = [
    "RocketTaskset",
    "RocketTasksetConfig",
    "RocketTask",
    "RocketTaskConfig",
    "RocketData",
    "RocketHarness",
]
