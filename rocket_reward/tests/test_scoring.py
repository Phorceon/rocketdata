"""Tests for scoring.py: the stages run in order, and crashes are handled.

The stage modules (parts, motors, clean, limit_checks) are replaced by small
fakes here, so these tests check the running order and the error handling
alone and do not need those files.
"""
from __future__ import annotations

import json
import subprocess
import sys

import pytest

from rocket_reward import Requirements, RewardSetupError, StageCheck, ladder
from rocket_reward import scoring as S

REQ = Requirements.from_dict({"id": "t-1", "apogee_m": {"value": 500, "kind": "about"}})
GOOD = ('<thought>ok</thought>\n<design>{"openrocket": {"children": [{"rocket": {"children": []}}]}}'
        '</design>')


class Fakes:
    """Passing stand-ins for stages 2-4 and the cleaner that record their calls."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.loads = 0
        self.parts = StageCheck("parts", True, 1.0)
        self.motor = StageCheck("motor", True, 1.0)
        self.limits = StageCheck("limits", True, 1.0)
        self.table = object()
        self.cleaned = {"openrocket": {"children": [{"cleaned": {}}]}}

    def check_parts(self, root):
        self.calls.append(("parts", root))
        return self.parts

    def check_motors(self, root, table):
        self.calls.append(("motor", root, table))
        return self.motor

    def clean_design(self, root, table):
        self.calls.append(("clean", root, table))
        return self.cleaned, ["motor diameter set from the table"]

    def check_limits(self, root, table):
        self.calls.append(("limits", root, table))
        return self.limits

    def load_table(self):
        self.loads += 1
        return self.table

    def stages(self) -> list[str]:
        return [c[0] for c in self.calls]


@pytest.fixture
def fakes(monkeypatch, tmp_path):
    f = Fakes()
    monkeypatch.setattr(S, "_check_parts", f.check_parts)
    monkeypatch.setattr(S, "_check_motors", f.check_motors)
    monkeypatch.setattr(S, "_clean_design", f.clean_design)
    monkeypatch.setattr(S, "_check_limits", f.check_limits)
    monkeypatch.setattr(S, "_load_motor_table", f.load_table)
    monkeypatch.setattr(S, "_substitute_motors", lambda root, table: (None, []))  # no shadow flight
    monkeypatch.setattr(S, "_table_cache", [])
    monkeypatch.setattr(S, "_default_tracker", S.ErrorTracker())
    monkeypatch.setenv(S.QUARANTINE_ENV, str(tmp_path / "quarantine"))
    return f


def quarantined_files(tmp_path):
    folder = tmp_path / "quarantine"
    return sorted(folder.glob("*.json")) if folder.exists() else []


# ------------------------------------------------------------------ order and scores

def test_truncated_answer_scores_zero(fakes):
    r = S.score(GOOD, REQ, truncated=True)
    assert r.score == 0.0 and r.stage == "format" and r.stages_passed == 0
    assert r.flags["truncated"] is True
    assert fakes.calls == []


def test_unreadable_json_scores_inside_format_band(fakes):
    r = S.score("<design>{oops</design>", REQ)
    assert r.score == ladder.stage_score("format", 0.5) and r.credit == 0.5
    assert "does not parse" in r.reasons[0]


def test_parts_failure_stops_the_ladder(fakes):
    fakes.parts = StageCheck("parts", False, 0.5, reasons=["no fin set"])
    r = S.score(GOOD, REQ)
    assert r.stage == "parts" and r.stages_passed == 1
    assert r.score == pytest.approx(0.10 + 0.08 * 0.5)
    assert r.reasons == ["no fin set"]
    assert fakes.stages() == ["parts"] and fakes.loads == 0


def test_motor_failure(fakes):
    """With no substitute motor the shadow share earns nothing (DESIGN.md stage 3)."""
    fakes.motor = StageCheck("motor", False, 2 / 3, reasons=["motor 'X' is not a real motor"])
    r = S.score(GOOD, REQ)
    assert r.stage == "motor" and r.stages_passed == 2
    assert r.score == ladder.stage_score("motor", ladder.MOTOR_FACTS_SHARE * 2 / 3)
    assert r.flags["motor_facts_credit"] == 2 / 3 and r.flags["shadow"]["progress"] == 0.0
    assert fakes.stages() == ["parts", "motor"]
    assert S.preflight_result(S.preflight(GOOD)).score == ladder.stage_score("motor", 2 / 3)


def test_limits_run_on_the_cleaned_copy(fakes):
    fakes.limits = StageCheck("limits", False, 0.25, reasons=["9 fins; at most 8"])
    r = S.score(GOOD, REQ)
    assert r.stage == "limits" and r.stages_passed == 3
    assert r.score == ladder.stage_score("limits", 0.25)
    assert fakes.stages() == ["parts", "motor", "clean", "limits"]
    original = fakes.calls[0][1]
    assert fakes.calls[2][1] is original and fakes.calls[2][2] is fakes.table
    assert fakes.calls[3][1] is fakes.cleaned
    assert r.flags["clean_notes"] == ["motor diameter set from the table"]


def test_defects_from_earlier_stages_count(fakes):
    fakes.parts = StageCheck("parts", True, 1.0, defects=["a", "b"])
    fakes.motor = StageCheck("motor", False, 1.0, reasons=["x"], defects=["c"])
    r = S.score(GOOD, REQ)
    assert r.defects == ["a", "b", "c"]
    assert r.score == ladder.stage_score("motor", ladder.MOTOR_FACTS_SHARE, 3)


def test_scores_respect_the_bands(fakes):
    """However the stages report, a stage-k failure lands in band k."""
    for credit in [-1, 0, 0.3, 1, 5, float("nan")]:
        fakes.parts = StageCheck("parts", False, credit)
        r = S.score(GOOD, REQ)
        s = ladder.stage("parts")
        assert s.floor <= r.score <= s.top
        assert 0.0 <= r.credit <= 1.0


def test_same_answer_same_score(fakes):
    fakes.limits = StageCheck("limits", False, 0.4)
    assert S.score(GOOD, REQ).to_dict() == S.score(GOOD, REQ).to_dict()


def test_default_simulator_that_cannot_start_is_a_setup_error(fakes, monkeypatch, tmp_path):
    def no_java(size):
        raise RewardSetupError("Java 17 was not found")

    monkeypatch.setattr(S, "_sim_cache", [])
    monkeypatch.setattr(S, "_start_simulator", no_java)
    with pytest.raises(RewardSetupError, match="Java"):
        S.score(GOOD, REQ)
    assert quarantined_files(tmp_path) == [] and S._default_tracker.errors == 0


def test_a_simulator_without_run_is_a_setup_error(fakes):
    with pytest.raises(RewardSetupError, match="run"):
        S.score(GOOD, REQ, simulator=object())


class _Sim:
    def run(self, *args, **kwargs):
        raise AssertionError("not flown in this test")


def test_simulator_hook_receives_the_preflight(fakes, monkeypatch):
    seen = {}

    def fake_sim(pre, requirements, simulator, table):
        seen["pre"], seen["table"] = pre, table
        return S.Result(score=0.85, stage="targets", stages_passed=7, credit=0.5)

    monkeypatch.setattr(S, "_run_simulator_stages", fake_sim)
    r = S.score(GOOD, REQ, simulator=_Sim())
    assert r.score == 0.85
    assert seen["pre"].passed and seen["pre"].clean_root is fakes.cleaned and seen["table"] is fakes.table


# ------------------------------------------------------------------ preflight

def test_preflight_lists_checks_in_order(fakes):
    pre = S.preflight(GOOD)
    assert [c.stage for c in pre.checks] == ["format", "parts", "motor", "limits"]
    assert pre.passed and pre.failed is None
    assert pre.root == json.loads(GOOD.split("<design>")[1].split("</design>")[0])
    assert pre.clean_root is fakes.cleaned and pre.notes == ["motor diameter set from the table"]


def test_preflight_stops_at_first_failure(fakes):
    fakes.parts = StageCheck("parts", False, 0.0)
    pre = S.preflight(GOOD)
    assert [c.stage for c in pre.checks] == ["format", "parts"]
    assert pre.failed is fakes.parts and not pre.passed and pre.clean_root is None


def test_preflight_on_a_bad_answer(fakes):
    pre = S.preflight("nothing here")
    assert [c.stage for c in pre.checks] == ["format"] and pre.root is None
    assert fakes.calls == []


def test_preflight_runs_on_every_gold_answer(fakes, gold_rows):
    for row in gold_rows:
        assert S.preflight(row["answer"]).passed


def test_motor_table_is_loaded_once_and_only_when_needed(fakes):
    fakes.parts = StageCheck("parts", False, 0.0)
    S.preflight(GOOD)
    assert fakes.loads == 0
    fakes.parts = StageCheck("parts", True, 1.0)
    fakes.motor = StageCheck("motor", False, 0.0)
    for _ in range(3):
        S.preflight(GOOD)
        S.score(GOOD, REQ)
    assert fakes.loads == 1


def test_given_motor_table_is_used(fakes):
    mine = object()
    fakes.motor = StageCheck("motor", False, 0.0)
    S.preflight(GOOD, motor_table=mine)
    assert fakes.calls[1][2] is mine and fakes.loads == 0


def test_missing_motor_table_is_a_setup_error(fakes, monkeypatch, tmp_path):
    def broken():
        raise FileNotFoundError("motor_table.json")

    monkeypatch.setattr(S, "_load_motor_table", broken)
    with pytest.raises(RewardSetupError, match="motor table"):
        S.score(GOOD, REQ)
    assert quarantined_files(tmp_path) == []


def test_importing_does_no_work():
    code = ("import sys, rocket_reward; from rocket_reward import scoring as S; "
            "print(len(S._table_cache), any(m in sys.modules for m in "
            "('rocket_reward.parts', 'rocket_reward.motors', 'rocket_reward.clean')))")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         cwd=str(S.Path(S.__file__).parents[1]), check=True)
    assert out.stdout.split() == ["0", "False"]


# ------------------------------------------------------------------ unexpected errors

def test_crash_is_quarantined(fakes, monkeypatch, tmp_path):
    def boom(root):
        raise ZeroDivisionError("fin count divided by zero")

    monkeypatch.setattr(S, "_check_parts", boom)
    r = S.score(GOOD + " tail", REQ)
    assert r.score is None and r.stage == "dropped" and r.stages_passed == 1
    assert r.flags["quarantined"] is True
    assert "ZeroDivisionError" in r.flags["error"]
    files = quarantined_files(tmp_path)
    assert len(files) == 1 and r.flags["quarantine_file"] == str(files[0])
    saved = json.loads(files[0].read_text(encoding="utf-8"))
    assert saved["answer_text"] == GOOD + " tail"
    assert saved["requirements_id"] == "t-1"
    assert "fin count divided by zero" in saved["traceback"]
    assert b"\r\n" not in files[0].read_bytes()
    assert S._default_tracker.errors == 1


@pytest.mark.parametrize("where", ["_check_motors", "_clean_design", "_check_limits"])
def test_crash_in_any_stage_is_quarantined(fakes, monkeypatch, where):
    def boom(*args):
        raise KeyError("x")

    monkeypatch.setattr(S, where, boom)
    r = S.score(GOOD, REQ)
    assert r.score is None and r.flags["quarantined"]


@pytest.mark.parametrize("bad", [None, 0.5, StageCheck("motor", True, 1.0), "ok"])
def test_stage_returning_the_wrong_thing_is_quarantined(fakes, monkeypatch, bad):
    monkeypatch.setattr(S, "_check_parts", lambda root: bad)
    r = S.score(GOOD, REQ)
    assert r.score is None and r.flags["quarantined"]


def test_cleaner_returning_the_wrong_thing_is_quarantined(fakes, monkeypatch):
    monkeypatch.setattr(S, "_clean_design", lambda root, table: None)
    assert S.score(GOOD, REQ).flags["quarantined"]


def test_setup_error_inside_a_stage_is_never_caught(fakes, monkeypatch, tmp_path):
    def broken(root):
        raise RewardSetupError("Java is missing")

    monkeypatch.setattr(S, "_check_parts", broken)
    with pytest.raises(RewardSetupError, match="Java"):
        S.score(GOOD, REQ)
    assert quarantined_files(tmp_path) == [] and S._default_tracker.errors == 0


def test_unwritable_quarantine_is_a_setup_error(fakes, monkeypatch, tmp_path):
    blocker = tmp_path / "a_file"
    blocker.write_text("x", encoding="utf-8")
    monkeypatch.setenv(S.QUARANTINE_ENV, str(blocker / "sub"))
    monkeypatch.setattr(S, "_check_parts", lambda root: 1 / 0)
    with pytest.raises(RewardSetupError, match=S.QUARANTINE_ENV):
        S.score(GOOD, REQ)


def test_default_quarantine_folder(monkeypatch):
    monkeypatch.delenv(S.QUARANTINE_ENV, raising=False)
    assert S.quarantine_dir().name == "rocket_reward_quarantine"
    monkeypatch.setenv(S.QUARANTINE_ENV, "somewhere")
    assert str(S.quarantine_dir()) == "somewhere"


def test_five_crashes_in_a_row_raise(fakes, monkeypatch):
    monkeypatch.setattr(S, "_check_parts", lambda root: 1 / 0)
    tracker = S.ErrorTracker()
    for _ in range(4):
        assert S.score(GOOD, REQ, tracker=tracker).score is None
    with pytest.raises(RewardSetupError, match="5 answers in a row"):
        S.score(GOOD, REQ, tracker=tracker)


def test_crashes_spread_out_raise_past_one_percent():
    tracker = S.ErrorTracker()
    for _ in range(495):
        tracker.record(False)
    for _ in range(5):          # 5 of 500 is exactly 1%: not more than 1%
        tracker.record(True)
        tracker.record(False)
    assert tracker.errors == 5 and len(tracker) == 500
    with pytest.raises(RewardSetupError, match="6 of the last 500"):
        tracker.record(True)


def test_a_few_crashes_early_on_need_at_least_five():
    tracker = S.ErrorTracker()
    for _ in range(4):
        tracker.record(True)
        tracker.record(False)
    with pytest.raises(RewardSetupError, match="5 of the last 9"):
        tracker.record(True)


def test_old_crashes_leave_the_window():
    tracker = S.ErrorTracker(window=500)
    for _ in range(4):
        tracker.record(True)
        tracker.record(False)
    for _ in range(500):
        tracker.record(False)
    assert tracker.errors == 0
    for _ in range(4):
        tracker.record(True)
        tracker.record(False)
    tracker.reset()
    assert len(tracker) == 0 and tracker.in_a_row == 0


def test_successes_are_counted(fakes):
    fakes.parts = StageCheck("parts", False, 0.0)
    tracker = S.ErrorTracker()
    for _ in range(3):
        S.score(GOOD, REQ, tracker=tracker)
    assert len(tracker) == 3 and tracker.errors == 0


def test_hostile_answers_never_crash(fakes):
    """Odd input gives a normal format result, never an exception."""
    odd = [None, 12, b"<design></design>", "<design>" * 10_000, "</design>" * 10_000,
           "<design>" + "[" * 200_000 + "</design>", "<design>{\"openrocket\": 1e999}</design>"]
    for text in odd:
        r = S.score(text, REQ)  # type: ignore[arg-type]
        assert r.stage == "format" and 0.0 <= r.score <= 0.08


def test_default_tracker_is_the_one_score_uses(fakes):
    assert S.default_tracker() is S._default_tracker
    S.score(GOOD.replace("openrocket", "nope"), REQ)
    assert len(S.default_tracker()) == 1
