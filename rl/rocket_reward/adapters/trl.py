"""Reward functions for Hugging Face TRL's GRPOTrainer (and Unsloth, which wraps it).

TRL calls every reward function as

    f(prompts=..., completions=..., completion_ids=..., trainer_state=..., **other_columns)

and wants one number (or None) per completion. This module turns that call
into one `scoring.score_many` batch:

    reward = make_reward(simulator=pool, max_completion_tokens=4096)
    diagnostics = make_diagnostics(reward)       # seven 0/1 functions, pass with weight 0
    GRPOTrainer(..., reward_funcs=[reward, *diagnostics.values()],
                args=GRPOConfig(..., reward_weights=[1.0] + [0.0] * 7, scale_rewards="batch"))

What it returns:

* a float from 0 to 1 per answer (DESIGN.md section 2);
* for an answer the reward quarantined (Result.score is None: a check crashed
  on it), the mean score of the other answers to the same prompt in the same
  call, so its advantage is about zero and it pushes the model neither way.
  TRL 0.23.1 would turn a plain None into 0.0, the worst possible score
  (README.md quotes the lines). When every answer to a prompt was quarantined
  they all get None (equal rewards, so zero advantage);
* never a number for a broken machine: RewardSetupError (no Java, wrong jar,
  too many crashes, a dataset without requirements) is raised and stops training.

No trainer library is imported here; the functions only use the arguments TRL
passes in.
"""
from __future__ import annotations

import collections
import hashlib
import json
import threading
from typing import Any, Callable, Optional, Sequence

from .. import ladder, scoring
from ..errors import RewardSetupError
from ..records import Requirements, Result

REWARD_NAME = "rocket_reward"          # TRL logs each reward function under its __name__
DIAGNOSTIC_PREFIX = "rocket_reached_"  # + stage key, e.g. rocket_reached_flight
CACHE_BATCHES = 4                      # scored batches kept for the diagnostics to reuse


# --------------------------------------------------------------------------- shared readers

def read_requirements(value: Any, where: str = "this row") -> Requirements:
    """One row's requirements as a Requirements record.

    `value` may be a Requirements, a dict, or the same dict written as a JSON
    string. Anything else, or a record Requirements.from_dict rejects, is a
    broken dataset, so it raises RewardSetupError: training on it would score
    every answer against the wrong targets.
    """
    if isinstance(value, Requirements):
        return value
    data = value
    if isinstance(value, (str, bytes)):
        try:
            data = json.loads(value)
        except ValueError as exc:
            raise RewardSetupError(f"the requirements of {where} are not valid JSON ({exc}); "
                                   f"write them as the record DESIGN.md section 4 shows") from exc
    if not isinstance(data, dict):
        raise RewardSetupError(f"the requirements of {where} must be a dict or a JSON string, "
                               f"got {type(value).__name__}")
    # A datasets table fills keys a row does not have with None; from_dict skips them.
    data = {k: v for k, v in data.items() if v is not None}
    try:
        return Requirements.from_dict(data)
    except ValueError as exc:
        raise RewardSetupError(f"the requirements of {where} are not valid: {exc}") from exc


def message_text(content: Any) -> str:
    """The text of one chat message's content: a string, or a list of parts
    such as {"type": "text", "text": "..."} (other parts are skipped)."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, (list, tuple)):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and isinstance(part.get("text"), str):
                parts.append(part["text"])
        return "".join(parts)
    text = getattr(content, "text", None)
    return text if isinstance(text, str) else str(content)


def completion_text(completion: Any, where: str = "this completion") -> str:
    """The answer text of one TRL completion: a plain string, or a list of chat
    messages (the assistant messages' text, joined). Any other shape means the
    trainer is set up differently from what this adapter expects, so it raises
    RewardSetupError."""
    if isinstance(completion, str):
        return completion
    if isinstance(completion, (list, tuple)):
        texts = []
        for message in completion:
            if not isinstance(message, dict):
                raise RewardSetupError(f"{where} is a list but not of chat messages "
                                       f"(found {type(message).__name__})")
            if message.get("role", "assistant") == "assistant":
                texts.append(message_text(message.get("content")))
        return "".join(texts)
    raise RewardSetupError(f"{where} must be a string or a list of chat messages, "
                           f"got {type(completion).__name__}")


def _stable_json(value: Any) -> str:
    """One text for a value, the same every time (used for cache and group keys)."""
    if isinstance(value, Requirements):
        value = value.to_dict()
    if isinstance(value, (str, bytes)):
        return value if isinstance(value, str) else value.decode("utf-8", errors="replace")
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)


# --------------------------------------------------------------------------- the reward

class RocketReward:
    """A TRL reward function that scores one batch with scoring.score_many.

    Make it with make_reward(). Calling it returns one float (or None) per
    completion; `results(...)` returns the full Result objects of the same
    call, and is what the diagnostics use, so a batch is flown only once.
    """

    def __init__(self, simulator: Any = None, requirements_column: str = "requirements",
                 max_completion_tokens: Optional[int] = None, eos_token_id: Optional[int] = None) -> None:
        if max_completion_tokens is not None and (isinstance(max_completion_tokens, bool)
                                                  or not isinstance(max_completion_tokens, int)
                                                  or max_completion_tokens < 1):
            raise ValueError(f"max_completion_tokens must be a whole number of 1 or more, "
                             f"got {max_completion_tokens!r}")
        self.__name__ = REWARD_NAME
        self.simulator = simulator
        self.requirements_column = requirements_column
        self.max_completion_tokens = max_completion_tokens
        self.eos_token_id = eos_token_id
        self.last_results: list[Optional[Result]] = []
        self._cache: collections.OrderedDict[str, list[Result]] = collections.OrderedDict()
        self._parsed: dict[str, Requirements] = {}
        self._lock = threading.Lock()

    # ---- reading one TRL call

    def _requirements(self, n: int, kwargs: dict[str, Any]) -> tuple[list[Requirements], list[str]]:
        column = self.requirements_column
        if column not in kwargs:
            seen = sorted(k for k in kwargs if k not in ("trainer_state", "completion_ids"))
            raise RewardSetupError(f"the dataset has no {column!r} column, so the reward cannot know what "
                                   f"each prompt asked for; columns passed: {seen}. Add it, or pass "
                                   f"requirements_column= to make_reward")
        values = kwargs[column]
        if isinstance(values, (str, bytes, dict)) or not isinstance(values, Sequence) or len(values) != n:
            got = len(values) if isinstance(values, Sequence) and not isinstance(values, (str, bytes)) else "?"
            raise RewardSetupError(f"the {column!r} column must hold one value per completion: "
                                   f"{n} completions, {got} values")
        reqs, keys = [], []
        for i, value in enumerate(values):
            key = _stable_json(value)
            req = self._parsed.get(key)
            if req is None:
                req = read_requirements(value, where=f"completion {i} ({column!r} column)")
                if len(self._parsed) > 10_000:
                    self._parsed.clear()
                self._parsed[key] = req
            reqs.append(req)
            keys.append(key)
        return reqs, keys

    def _truncated(self, n: int, kwargs: dict[str, Any]) -> list[bool]:
        """An answer that used every allowed token was cut off (TRL passes the
        ids up to and including the end token, so one that ended exactly at
        the limit with `eos_token_id` as its last token is not)."""
        if self.max_completion_tokens is None:
            return [False] * n
        ids = kwargs.get("completion_ids")
        if ids is None or len(ids) != n:
            raise RewardSetupError("max_completion_tokens is set but the trainer passed no completion_ids "
                                   "(one list of token ids per completion), so cut-off answers cannot be found")
        out = []
        for row in ids:
            length = len(row)
            ended = self.eos_token_id is not None and length > 0 and row[-1] == self.eos_token_id
            out.append(length >= self.max_completion_tokens and not ended)
        return out

    def results(self, prompts: Sequence[Any], completions: Sequence[Any], **kwargs: Any) -> list[Result]:
        """Score one TRL batch (or return the cached results of the same batch)."""
        n = len(completions)
        texts = [completion_text(c, where=f"completion {i}") for i, c in enumerate(completions)]
        reqs, req_keys = self._requirements(n, kwargs)
        truncated = self._truncated(n, kwargs)
        digest = hashlib.sha256()
        for text, key, cut in zip(texts, req_keys, truncated):
            for piece in (text, key, "1" if cut else "0"):
                digest.update(piece.encode("utf-8", errors="replace"))
                digest.update(b"\x00")
        batch_key = digest.hexdigest()
        with self._lock:
            cached = self._cache.get(batch_key)
            if cached is None:
                cached = scoring.score_many(texts, reqs, truncated, self.simulator)
                self._cache[batch_key] = cached
                while len(self._cache) > CACHE_BATCHES:
                    self._cache.popitem(last=False)
            else:
                self._cache.move_to_end(batch_key)
            self.last_results = list(cached)
            return list(cached)

    def __call__(self, prompts: Sequence[Any], completions: Sequence[Any], **kwargs: Any) -> list[Optional[float]]:
        results = self.results(prompts, completions, **kwargs)
        scores: list[Optional[float]] = [r.score for r in results]
        if all(s is not None for s in scores):
            return [float(s) for s in scores]  # type: ignore[arg-type]
        # A quarantined answer gets the mean of the other answers to its prompt,
        # so its advantage is about zero (see the module docstring).
        _, req_keys = self._requirements(len(completions), kwargs)
        prompt_list = list(prompts) if prompts is not None else [None] * len(scores)
        if len(prompt_list) != len(scores):
            prompt_list = [None] * len(scores)
        groups: dict[tuple[str, str], list[float]] = collections.defaultdict(list)
        keys = [(_stable_json(p), k) for p, k in zip(prompt_list, req_keys)]
        for key, s in zip(keys, scores):
            if s is not None:
                groups[key].append(s)
        out: list[Optional[float]] = []
        for key, s in zip(keys, scores):
            if s is not None:
                out.append(float(s))
            elif groups.get(key):
                out.append(sum(groups[key]) / len(groups[key]))
            else:
                out.append(None)
        return out


_made: list[RocketReward] = []   # the reward make_reward made last, for make_diagnostics()


def make_reward(simulator: Any = None, requirements_column: str = "requirements",
                max_completion_tokens: Optional[int] = None, *,
                eos_token_id: Optional[int] = None) -> RocketReward:
    """A TRL reward function for the rocket ladder.

    simulator:             a sim.SimPool (or sim.Simulator) shared by every call;
                           None uses scoring.default_simulator() (ROCKET_REWARD_WORKERS
                           helpers, started on first use).
    requirements_column:   the dataset column holding each prompt's requirements
                           (a dict, or a JSON string of one).
    max_completion_tokens: set it to GRPOConfig.max_completion_length; an answer
                           that used every token is scored as cut off (0.0).
    eos_token_id:          optional; an answer whose last token is this id ended
                           on its own even at the limit.
    Making it does no work: nothing is read or started until the first call.
    """
    reward = RocketReward(simulator, requirements_column, max_completion_tokens, eos_token_id)
    _made[:] = [reward]
    return reward


def make_diagnostics(reward: Optional[RocketReward] = None) -> dict[str, Callable[..., list[Optional[float]]]]:
    """Seven TRL reward functions, one per stage, that return 1.0 when an answer
    reached that stage or a later one and 0.0 when it stopped earlier (None for
    a quarantined answer). Pass them with weight 0: they change nothing, but TRL
    logs each one's batch mean (rewards/rocket_reached_<stage>/mean), which shows
    where the model is stuck. `format` is 1.0 for every scored answer; it is
    there so the seven lines read as one ladder.

    They reuse the results `reward` already computed for the same batch (TRL
    calls the reward functions one after another with the same arguments), so
    nothing is flown twice. `reward` defaults to the one make_reward made last.
    """

    def owner() -> RocketReward:
        if reward is not None:
            return reward
        if not _made:
            make_reward()
        return _made[0]

    def make_one(key: str) -> Callable[..., list[Optional[float]]]:
        index = ladder.stage_index(key)

        def reached(prompts: Sequence[Any], completions: Sequence[Any], **kwargs: Any) -> list[Optional[float]]:
            out: list[Optional[float]] = []
            for r in owner().results(prompts, completions, **kwargs):
                if r.score is None or r.stage not in ladder.STAGE_KEYS:
                    out.append(None)
                else:
                    out.append(1.0 if ladder.stage_index(r.stage) >= index else 0.0)
            return out

        reached.__name__ = DIAGNOSTIC_PREFIX + key
        reached.__qualname__ = reached.__name__
        reached.__doc__ = f"1.0 when the answer reached the {key} stage or beyond, else 0.0 (None if quarantined)."
        return reached

    return {key: make_one(key) for key in ladder.STAGE_KEYS}
