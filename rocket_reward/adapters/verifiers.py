"""A reward for Prime Intellect verifiers 0.4.x (the verifiers.v1 task API).

NOT YET RUN AGAINST THE REAL LIBRARY. verifiers is not installed where this
package was built. The adapter follows the 0.4.1 source (verifiers/v1/task.py,
trace.py, errors.py and utils/decorators.py at tag v0.4.1) and is tested only
with a fake task and trace shaped like it. Try it on a few rollouts first.

How verifiers calls it (v0.4.1): a task's rewards are async functions that ask
for what they need by parameter name, `task` (the task's data) and `trace`
(the rollout); `Task.score` awaits them all with asyncio.gather and records a
returned float with the reward's weight. A reward can be plugged in by import
path in the task configuration:

    --env.taskset.task.rewards '{"rocket": {"fn": "rocket_reward.adapters.verifiers:rocket_reward"}}'

What it does: it finds the requirements in the task's data (field
"requirements", a dict or JSON string), takes the final assistant message,
treats the answer as cut off when the last model call finished with
finish_reason "length" (or the trace says it was truncated), scores it on a
worker thread and returns the score. A quarantined answer (Result.score is
None) calls `trace.drop(...)`, which verifiers documents as "leave the trace
out of reward means and training batches", and returns None (no reward is
recorded). RewardSetupError is raised, never turned into a number; note that
verifiers records any error raised in a reward on the trace as a TaskError
instead of stopping the run (README.md says how to stop on it).
"""
from __future__ import annotations

import asyncio
from typing import Any, Callable, Optional

from .. import scoring
from ..errors import RewardSetupError
from ..records import Requirements
from .trl import message_text, read_requirements

REQUIREMENTS_FIELD = "requirements"
STAGE_METRIC = "rocket_stages_passed"   # 0..7, recorded on the trace for logging


def task_requirements(task: Any, field: str = REQUIREMENTS_FIELD) -> Requirements:
    """The requirements in a task's data: an attribute (a TaskData subclass
    field, or an extra field of verifiers' WireTaskData), a dict key, or a key
    of the task's `info` dict. Missing requirements are a broken taskset, so
    this raises RewardSetupError."""
    value: Any = None
    if isinstance(task, dict):
        value = task.get(field)
        info = task.get("info")
    else:
        value = getattr(task, field, None)
        info = getattr(task, "info", None)
        if value is None:
            extra = getattr(task, "model_extra", None)
            if isinstance(extra, dict):
                value = extra.get(field)
    if value is None and isinstance(info, dict):
        value = info.get(field)
    if value is None:
        name = getattr(task, "id", None) or (task.get("id") if isinstance(task, dict) else None)
        raise RewardSetupError(f"task {name!r} has no {field!r} in its data, so the reward cannot know what "
                               f"the prompt asked for; add the record (DESIGN.md section 4) to every task")
    return read_requirements(value, where=f"task {getattr(task, 'id', None)!r}")


def final_answer(trace: Any) -> str:
    """The text of the final assistant message the model wrote ("" when there is none)."""
    messages = getattr(trace, "assistant_messages", None)
    if messages:
        return message_text(getattr(messages[-1], "content", None))
    reply = getattr(trace, "last_reply", None)
    return reply if isinstance(reply, str) else ""


def was_cut_off(trace: Any) -> bool:
    """True when the last successful model call stopped on the length limit
    (finish_reason "length") or the trace reports itself truncated."""
    calls = getattr(trace, "calls", None) or []
    last = next((c for c in reversed(list(calls)) if getattr(c, "error", None) is None), None)
    if last is not None and getattr(last, "finish_reason", None) == "length":
        return True
    return getattr(trace, "is_truncated", False) is True


def make_rollout_reward(simulator: Any = None, requirements_field: str = REQUIREMENTS_FIELD) -> Callable[..., Any]:
    """An async verifiers reward `(task, trace) -> float | None`.

    simulator: a sim.SimPool shared by every rollout in this process; None uses
    scoring.default_simulator() (ROCKET_REWARD_WORKERS helpers, started on first use).
    """

    async def rocket_reward(task: Any, trace: Any) -> Optional[float]:
        req = task_requirements(task, requirements_field)
        text = final_answer(trace)
        cut = was_cut_off(trace)
        result = await asyncio.to_thread(scoring.score, text, req, cut, simulator)
        record_metric = getattr(trace, "record_metric", None)
        if callable(record_metric):
            record_metric(STAGE_METRIC, float(result.stages_passed))
        info = getattr(trace, "info", None)
        if isinstance(info, dict):
            info["rocket_reward"] = {"stage": result.stage, "reasons": list(result.reasons[:5])}
        if result.score is None:
            drop = getattr(trace, "drop", None)
            if not callable(drop):
                raise RewardSetupError("an answer was quarantined but this trace has no drop() method, so it "
                                       "cannot be left out of training; check the verifiers version (0.4.x)")
            drop(f"rocket_reward quarantined the answer: {result.flags.get('error', 'unexpected error')}")
            return None
        return float(result.score)

    return rocket_reward


# The ready-made reward to plug by import path: rocket_reward.adapters.verifiers:rocket_reward
rocket_reward = make_rollout_reward()


def is_setup_error(trace: Any) -> bool:
    """True when a finished trace's last error is a RewardSetupError (verifiers
    records it as a TaskError whose message names it). Check it in the training
    loop and stop: the machine is broken, not the answer."""
    errors = getattr(trace, "errors", None) or []
    last = errors[-1] if errors else None
    message = getattr(last, "message", None) if last is not None else None
    return isinstance(message, str) and RewardSetupError.__name__ in message
