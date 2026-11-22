"""The trainer adapters (adapters/trl.py, adapters/verifiers.py).

Neither trainer library is needed: TRL's call is imitated with plain lists,
and verifiers' task and trace with small stand-ins shaped like the v0.4.1
source (Task.score passes `task` and `trace` by name and awaits the result).
Most tests swap scoring.score_many / scoring.score for fakes, to check the
adapter alone; one test uses recorded simulator replies, and one (needs_java)
the real simulator.
"""
from __future__ import annotations

import asyncio
import functools
import inspect
import json
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from rocket_reward import Requirements, Result, RewardSetupError, ladder
from rocket_reward import scoring as S
from rocket_reward.adapters import trl as T
from rocket_reward.adapters import verifiers as V
from replies import load_reply
from test_scoring_sim import quiet  # noqa: F401  (fixture: a fresh tracker and quarantine folder)

DATA = Path(__file__).resolve().parent / "data"
REPO = Path(__file__).resolve().parents[2]
REQUIREMENTS = json.loads((DATA / "model_val_requirements.json").read_text(encoding="utf-8"))
REQ = {"id": "t-1", "apogee_m": {"value": 500, "kind": "about"}}


class FakeScoring:
    """Stands in for scoring.score_many: records each batch and answers with a
    Result chosen by the answer text ("stage:<key>:<score>", "quarantine", "setup")."""

    def __init__(self, monkeypatch):
        self.batches: list[dict] = []
        monkeypatch.setattr(S, "score_many", self.score_many)

    @staticmethod
    def result_for(text: str) -> Result:
        if text == "setup":
            raise RewardSetupError("Java is missing")
        if text == "quarantine":
            return Result(score=None, stage="dropped", stages_passed=0, credit=0.0,
                          flags={"quarantined": True, "error": "TypeError: boom"})
        if text.startswith("stage:"):
            _, key, value = text.split(":")
            return Result(score=float(value), stage=key, stages_passed=ladder.stage_index(key), credit=0.5)
        return Result(score=0.0, stage="format", stages_passed=0, credit=0.0)

    def score_many(self, answers, requirements_list, truncated=None, simulator=None, **kw):
        self.batches.append({"answers": list(answers), "reqs": list(requirements_list),
                             "truncated": list(truncated) if truncated is not None else None,
                             "simulator": simulator})
        return [self.result_for(a) for a in answers]


def call(fn, completions, requirements=None, prompts=None, **extra):
    """Call a reward function the way TRL 0.23.1 does (keyword arguments)."""
    n = len(completions)
    requirements = requirements if requirements is not None else [REQ] * n
    prompts = prompts if prompts is not None else ["p"] * n
    return fn(prompts=prompts, completions=completions, completion_ids=extra.pop("completion_ids", None),
              requirements=requirements, trainer_state=object(), **extra)


# ------------------------------------------------------------------ imports

def test_importing_the_adapters_imports_no_trainer_library():
    code = ("import sys, rocket_reward.adapters, rocket_reward.adapters.trl, rocket_reward.adapters.verifiers\n"
            "bad = [m for m in ('trl', 'verifiers', 'torch', 'transformers', 'datasets', 'unsloth') "
            "if m in sys.modules]\n"
            "assert not bad, bad\n"
            "assert not any(m.startswith('rocket_reward.sim') for m in sys.modules)\n")
    done = subprocess.run([sys.executable, "-c", code], cwd=str(REPO), capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stderr


def test_making_the_rewards_does_no_work(monkeypatch):
    monkeypatch.setattr(S, "default_simulator", lambda: (_ for _ in ()).throw(AssertionError("started")))
    reward = T.make_reward()
    T.make_diagnostics(reward)
    V.make_rollout_reward()
    assert reward.__name__ == T.REWARD_NAME


# ------------------------------------------------------------------ TRL: inputs

def test_plain_and_chat_completions_give_the_same_text(monkeypatch):
    fake = FakeScoring(monkeypatch)
    reward = T.make_reward()
    plain = call(reward, ["stage:limits:0.33", "stage:build:0.44"])
    chat = call(reward, [[{"role": "assistant", "content": "stage:limits:0.33"}],
                         [{"role": "assistant", "content": [{"type": "text", "text": "stage:build:0.44"}]}]])
    assert plain == chat == [0.33, 0.44]
    assert all(isinstance(x, float) for x in plain)
    assert fake.batches[0]["answers"] == ["stage:limits:0.33", "stage:build:0.44"]


def test_chat_completion_keeps_only_assistant_text():
    assert T.completion_text([{"role": "user", "content": "no"}, {"role": "assistant", "content": "yes"}]) == "yes"
    assert T.completion_text([]) == ""


@pytest.mark.parametrize("bad", [42, None, [1, 2]])
def test_an_unknown_completion_shape_is_a_setup_error(bad):
    with pytest.raises(RewardSetupError):
        T.completion_text(bad)


def test_requirements_as_dict_json_or_filled_with_none(monkeypatch):
    fake = FakeScoring(monkeypatch)
    reward = T.make_reward()
    filled = dict(REQ, landing_ms=None, motors=None, motor_class=None)  # what a datasets table gives
    call(reward, ["a", "b", "c"], requirements=[REQ, json.dumps(REQ), filled])
    reqs = fake.batches[0]["reqs"]
    assert all(isinstance(r, Requirements) for r in reqs)
    assert reqs[0] == reqs[1] == reqs[2] == Requirements.from_dict(REQ)


def test_requirements_from_another_column(monkeypatch):
    fake = FakeScoring(monkeypatch)
    reward = T.make_reward(requirements_column="req")
    reward(prompts=["p"], completions=["a"], req=[REQ])
    assert fake.batches[0]["reqs"][0].id == "t-1"


@pytest.mark.parametrize("requirements, words", [
    (None, "no 'requirements' column"),
    (["{not json"], "not valid JSON"),
    ([{"id": "x"}], "apogee_m"),
    ([{"id": "x", "apogee_m": {"value": 1, "kind": "about"}, "apogee": 3}], "unknown keys"),
    ([7], "must be a dict"),
    ([REQ, REQ], "one value per completion"),
])
def test_broken_requirements_stop_training(monkeypatch, requirements, words):
    FakeScoring(monkeypatch)
    reward = T.make_reward()
    kwargs = {} if requirements is None else {"requirements": requirements}
    with pytest.raises(RewardSetupError, match=words):
        reward(prompts=["p"], completions=["a"], **kwargs)


# ------------------------------------------------------------------ TRL: truncation

def test_an_answer_that_used_every_token_is_cut_off(monkeypatch):
    fake = FakeScoring(monkeypatch)
    reward = T.make_reward(max_completion_tokens=4)
    call(reward, ["a", "b", "c"], completion_ids=[[1, 2, 3], [1, 2, 3, 4], [1, 2, 3, 4, 5]])
    assert fake.batches[0]["truncated"] == [False, True, True]


def test_an_answer_ending_on_the_end_token_at_the_limit_is_not_cut_off(monkeypatch):
    fake = FakeScoring(monkeypatch)
    reward = T.make_reward(max_completion_tokens=3, eos_token_id=99)
    call(reward, ["a", "b"], completion_ids=[[1, 2, 99], [1, 2, 3]])
    assert fake.batches[0]["truncated"] == [False, True]


def test_without_a_limit_nothing_is_cut_off(monkeypatch):
    fake = FakeScoring(monkeypatch)
    call(T.make_reward(), ["a"], completion_ids=[[1] * 10_000])
    assert fake.batches[0]["truncated"] == [False]


def test_a_limit_without_token_ids_is_a_setup_error(monkeypatch):
    FakeScoring(monkeypatch)
    with pytest.raises(RewardSetupError, match="completion_ids"):
        call(T.make_reward(max_completion_tokens=8), ["a"])


@pytest.mark.parametrize("bad", [0, -1, 2.5, True, "8"])
def test_a_bad_limit_is_refused(bad):
    with pytest.raises(ValueError):
        T.make_reward(max_completion_tokens=bad)


# ------------------------------------------------------------------ TRL: outputs

def test_a_quarantined_answer_gets_its_groups_mean(monkeypatch):
    FakeScoring(monkeypatch)
    reward = T.make_reward()
    got = call(reward, ["stage:limits:0.3", "quarantine", "stage:build:0.5", "quarantine", "stage:flight:0.6"],
               prompts=["A", "A", "A", "B", "C"])
    assert got[:3] == [0.3, pytest.approx(0.4), 0.5]
    assert got[3] is None          # nothing else in group B was scored
    assert got[4] == 0.6


def test_groups_are_told_apart_by_requirements_too(monkeypatch):
    FakeScoring(monkeypatch)
    other = dict(REQ, id="t-2")
    got = call(T.make_reward(), ["stage:limits:0.3", "quarantine", "stage:build:0.5"],
               prompts=["A", "A", "A"], requirements=[REQ, REQ, other])
    assert got == [0.3, 0.3, 0.5]


def test_a_setup_error_is_raised_not_scored(monkeypatch):
    FakeScoring(monkeypatch)
    with pytest.raises(RewardSetupError, match="Java"):
        call(T.make_reward(), ["stage:limits:0.3", "setup"])


def test_the_shared_simulator_is_passed_to_every_batch(monkeypatch):
    fake = FakeScoring(monkeypatch)
    pool = object()
    reward = T.make_reward(simulator=pool)
    call(reward, ["a"])
    call(reward, ["b"])
    assert [b["simulator"] for b in fake.batches] == [pool, pool]


# ------------------------------------------------------------------ TRL: diagnostics

def test_diagnostics_reuse_the_batch_and_say_where_answers_stopped(monkeypatch):
    fake = FakeScoring(monkeypatch)
    reward = T.make_reward()
    diags = T.make_diagnostics(reward)
    assert list(diags) == list(ladder.STAGE_KEYS)
    assert len({f.__name__ for f in diags.values()}) == 7
    answers = ["stage:parts:0.15", "stage:build:0.44", "stage:targets:0.9", "quarantine"]
    call(reward, answers, prompts=["A"] * 4)
    got = {k: call(f, answers, prompts=["A"] * 4) for k, f in diags.items()}
    assert len(fake.batches) == 1, "the diagnostics must not score the batch again"
    assert got["format"] == [1.0, 1.0, 1.0, None]
    assert got["parts"] == [1.0, 1.0, 1.0, None]
    assert got["motor"] == [0.0, 1.0, 1.0, None]
    assert got["build"] == [0.0, 1.0, 1.0, None]
    assert got["flight"] == [0.0, 0.0, 1.0, None]
    assert got["targets"] == [0.0, 0.0, 1.0, None]


def test_diagnostics_first_still_score_only_once(monkeypatch):
    fake = FakeScoring(monkeypatch)
    reward = T.make_reward(max_completion_tokens=5)
    diags = T.make_diagnostics()        # the reward made last
    ids = [[1, 2], [1, 2, 3, 4, 5]]
    call(diags["limits"], ["stage:build:0.44", "b"], completion_ids=ids)
    call(reward, ["stage:build:0.44", "b"], completion_ids=ids)
    assert len(fake.batches) == 1
    call(reward, ["stage:build:0.44", "c"], completion_ids=ids)   # a new batch is scored
    assert len(fake.batches) == 2


def test_cache_keeps_a_few_batches_only(monkeypatch):
    FakeScoring(monkeypatch)
    reward = T.make_reward()
    for i in range(T.CACHE_BATCHES + 3):
        call(reward, [f"answer {i}"])
    assert len(reward._cache) == T.CACHE_BATCHES


def test_trl_style_reward_end_to_end_with_recorded_replies(quiet, gold_rows):
    """The adapter gives exactly what scoring.score gives, with a stand-in simulator."""

    class Sim:
        size = 2
        _lock = threading.Lock()

        def run(self, ork_text, rail_m, flights, config_id=None, **extra):
            return load_reply("single_stage")

    sim = Sim()
    rows = gold_rows[:3]
    reqs = [REQUIREMENTS[r["id"]] for r in rows]
    completions = [[{"role": "assistant", "content": r["answer"]}] for r in rows] + [[{"role": "assistant",
                                                                                      "content": "no design"}]]
    reward = T.make_reward(simulator=sim, max_completion_tokens=100_000)
    ids = [[0] * 10 for _ in completions[:-1]] + [[0] * 100_000]
    got = call(reward, completions, requirements=reqs + [reqs[0]], completion_ids=ids)
    want = [S.score(r["answer"], Requirements.from_dict(q), False, sim).score for r, q in zip(rows, reqs)]
    assert got[:3] == want
    assert got[3] == 0.0
    assert all(0.0 <= g <= 1.0 for g in got)


# ------------------------------------------------------------------ verifiers stand-ins

class FakeMessage:
    def __init__(self, content):
        self.content = content


class FakeCall:
    def __init__(self, finish_reason="stop", error=None):
        self.finish_reason = finish_reason
        self.error = error


class FakeTrace:
    """The parts of verifiers.v1 Trace the adapter reads or writes."""

    def __init__(self, reply="stage:limits:0.33", finish_reason="stop", calls=None):
        self.assistant_messages = [FakeMessage("first try"), FakeMessage(reply)]
        self.calls = calls if calls is not None else [FakeCall(finish_reason)]
        self.metrics: dict = {}
        self.info: dict = {}
        self.dropped = None
        self.errors: list = []

    @property
    def is_truncated(self):
        last = next((c for c in reversed(self.calls) if c.error is None), None)
        return bool(last and last.finish_reason == "length")

    def record_metric(self, name, value):
        self.metrics[name] = float(value)

    def drop(self, reason):
        if self.dropped is None:
            self.dropped = reason


class FakeTaskData:
    """Like verifiers' WireTaskData: known fields as attributes, extra ones in model_extra."""

    def __init__(self, requirements=None, extra=None, info=None, id="task-1"):
        self.id = id
        if requirements is not None:
            self.requirements = requirements
        self.model_extra = extra or {}
        if info is not None:
            self.info = info


class FakeScore:
    """Stands in for scoring.score in the verifiers tests."""

    def __init__(self, monkeypatch):
        self.calls: list[tuple] = []
        monkeypatch.setattr(S, "score", self.score)

    def score(self, answer_text, requirements, truncated=False, simulator=None, **kw):
        self.calls.append((answer_text, requirements, truncated, simulator))
        if truncated:
            return Result(score=0.0, stage="format", stages_passed=0, credit=0.0)
        return FakeScoring.result_for(answer_text)


def run_like_verifiers(fn, task, trace):
    """What verifiers 0.4.1's invoke_all does: pass the named arguments it asks for, await them."""
    available = {"task": task, "trace": trace}
    params = inspect.signature(fn).parameters

    async def invoke_all():
        return await asyncio.gather(fn(**{n: available[n] for n in params if n in available}))

    return asyncio.run(invoke_all())[0]


def test_verifiers_reward_has_the_shape_verifiers_calls():
    fn = V.rocket_reward
    assert inspect.iscoroutinefunction(fn)
    assert set(inspect.signature(fn).parameters) == {"task", "trace"}

    @functools.wraps(fn)            # how verifiers wraps a reward plugged by import path
    def plugged(*args, **kwargs):
        return fn(*args, **kwargs)

    assert set(inspect.signature(plugged).parameters) == {"task", "trace"}


@pytest.mark.parametrize("task", [
    FakeTaskData(requirements=REQ),
    FakeTaskData(requirements=json.dumps(REQ)),
    FakeTaskData(extra={"requirements": REQ}),
    FakeTaskData(info={"requirements": REQ}),
    {"id": "task-1", "requirements": REQ},
])
def test_verifiers_reward_scores_the_final_assistant_message(monkeypatch, task):
    fake = FakeScore(monkeypatch)
    trace = FakeTrace("stage:limits:0.33")
    got = run_like_verifiers(V.rocket_reward, task, trace)
    assert got == 0.33
    text, req, cut, _ = fake.calls[0]
    assert (text, req.id, cut) == ("stage:limits:0.33", "t-1", False)
    assert trace.metrics[V.STAGE_METRIC] == ladder.stage_index("limits")
    assert trace.info["rocket_reward"]["stage"] == "limits"


def test_verifiers_reward_sees_a_length_finish_as_cut_off(monkeypatch):
    fake = FakeScore(monkeypatch)
    trace = FakeTrace("stage:targets:0.9", calls=[FakeCall("length"), FakeCall("stop", error="boom")])
    assert run_like_verifiers(V.rocket_reward, FakeTaskData(REQ), trace) == 0.0
    assert fake.calls[0][2] is True


def test_verifiers_reward_with_no_answer_scores_zero(monkeypatch):
    FakeScore(monkeypatch)
    trace = FakeTrace()
    trace.assistant_messages = []
    trace.last_reply = ""
    assert run_like_verifiers(V.rocket_reward, FakeTaskData(REQ), trace) == 0.0


def test_verifiers_quarantined_answer_drops_the_rollout(monkeypatch):
    FakeScore(monkeypatch)
    trace = FakeTrace("quarantine")
    assert run_like_verifiers(V.rocket_reward, FakeTaskData(REQ), trace) is None
    assert trace.dropped and "TypeError" in trace.dropped


@pytest.mark.parametrize("task, trace_reply", [(FakeTaskData(), "a"), (FakeTaskData(REQ), "setup")])
def test_verifiers_setup_errors_are_raised(monkeypatch, task, trace_reply):
    FakeScore(monkeypatch)
    with pytest.raises(RewardSetupError):
        run_like_verifiers(V.rocket_reward, task, FakeTrace(trace_reply))


def test_is_setup_error_reads_the_recorded_error():
    class Err:
        message = "task RocketTask scoring: RewardSetupError: Java is missing"

    trace = FakeTrace()
    assert not V.is_setup_error(trace)
    trace.errors = [Err()]
    assert V.is_setup_error(trace)


# ------------------------------------------------------------------ real simulator

@pytest.mark.needs_java
def test_trl_reward_and_diagnostics_with_the_real_simulator(gold_rows):
    from rocket_reward.sim import SimPool
    rows = gold_rows[:4]
    reqs = [REQUIREMENTS[r["id"]] for r in rows]
    completions = [r["answer"] for r in rows] + [rows[0]["answer"]]
    ids = [[0] * 10] * 4 + [[0] * 64]
    tracker = S.ErrorTracker()
    with SimPool(2) as pool:
        reward = T.make_reward(simulator=pool, max_completion_tokens=64)
        diags = T.make_diagnostics(reward)
        got = call(reward, completions, requirements=reqs + [reqs[0]], completion_ids=ids)
        reached = {k: call(f, completions, requirements=reqs + [reqs[0]], completion_ids=ids)
                   for k, f in diags.items()}
        want = [S.score(r["answer"], Requirements.from_dict(q), False, pool, tracker=tracker)
                for r, q in zip(rows, reqs)]
    assert got[:4] == [w.score for w in want]
    assert got[4] == 0.0                      # used every token: cut off
    for i, w in enumerate(want):
        assert reached["targets"][i] == (1.0 if w.stage == "targets" else 0.0)
    assert reached["parts"][4] == 0.0
