"""Fast checks for scripts/reward.py (no OpenRocket, no cadquery needed)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import reward as R  # noqa: E402


# ---------------------------------------------------------------- prompt parsing
def test_landing_limit_cannot_go_above_hard_max():
    assert R.landing_limit("about 300 m, landing under 15 m/s") == R.HARD_MAX_LANDING_MS


def test_landing_limit_ignores_wind():
    p = "Reach 300 m in wind under 3 m/s"
    assert R.landing_limit(p) == R.LIMITS["default_max_landing_ms"]
    assert R.asked_wind(p) == 3.0


def test_landing_limit_and_wind_in_one_prompt():
    p = ("Requirements: apogee 441 m; wind 4.5 m/s; touchdown at most 6 m/s; flight time 105 s")
    assert R.landing_limit(p) == 6.0
    assert R.asked_wind(p) == 4.5
    p = "2,560 ft is my target, with a 2 m/s breeze and a landing no faster than 8.0 m/s."
    assert R.landing_limit(p) == 8.0
    assert R.asked_wind(p) == 2.0


def test_stricter_prompt_limit_is_kept():
    assert R.landing_limit("touches down under 3.2 m/s, launched in about 2 m/s wind") == 3.2


def test_every_apogee_goal_is_kept():
    goals = R.asked_apogees("Stay below 500 ft apogee, about 120 m")
    assert [(round(v), k) for v, k in goals] == [(152, "max"), (120, "about")]


@pytest.mark.parametrize("prompt,want", [
    ("land safely within 25 seconds under $35", (25.0, "max")),
    ("with total flight time under 117.3 s, launched in about 2 m/s wind", (117.3, "max")),
    ("keep the flight near four minutes", (240.0, "about")),
    ("Flight should stay under 2.2 min, body 110 mm", (132.0, "max")),
    ("motor C6-5 with a 5 s delay", None),
])
def test_flight_time(prompt, want):
    got = R.asked_flight_time(prompt)
    assert (got if got is None else (round(got[0], 3), got[1])) == want


# ---------------------------------------------------------------- scoring
def test_closeness_is_graded():
    assert R.closeness(300, 300, "about", 0.05) == 1.0
    assert R.closeness(314, 300, "about", 0.05) == 1.0          # inside 5 %
    assert 0.0 < R.closeness(400, 300, "about", 0.05) < R.closeness(330, 300, "about", 0.05) < 1.0
    assert R.closeness(1000, 300, "about", 0.05) == 0.0
    assert R.closeness(500, 300, "min", 0.05) == 1.0             # one-sided
    assert R.closeness(280, 300, "min", 0.05) < 1.0


def test_tier4_weights_rescale_when_a_target_is_missing():
    assert R.tier4_score({"apogee": 1.0, "landing": 1.0}) == 1.0
    assert R.tier4_score({"apogee": 1.0, "landing": 0.0}) == round(0.40 / 0.55, 4)


def test_strip_overrides():
    body = {"children": [{"rocket": {"children": [
        {"overridecg": {"value": 0.05}},
        {"stage": {"children": [{"overridemass": {"value": 1}}, {"overridecd": {"value": 0.1}},
                                {"name": {"value": "s"}}]}}]}}]}
    assert R.strip_overrides(body) == 3
    assert "override" not in str(body)
    assert "name" in str(body)


# ---------------------------------------------------------------- ladder
def test_bad_json_is_tier1():
    assert R.reward("<design>{oops</design>", "about 300 m") == -1.0
    assert R.reward("no design at all", "about 300 m") == -1.0
    assert R.score_answer("<design>{}</design>", "x", finish="length")["score"] == -1.0


def test_skipped_gates_give_no_score(monkeypatch):
    # a stub design that clears gates 1-3, so the skip logic is what is tested
    monkeypatch.setattr(R, "gate_format", lambda c, f: ({"openrocket": {"children": []}}, None))
    monkeypatch.setattr(R, "gate_structure", lambda d: ([("m", "C6")], None))
    monkeypatch.setattr(R, "gate_motors", lambda m, p, l: (True, None, "stub"))
    monkeypatch.setattr(R, "fit_problems", lambda root: [])
    r = R.score_answer("x", "about 300 m", cad=False, flight=False)
    assert r["score"] is None
    assert {u.split(":")[0] for u in r["unverified"]} == {"cad", "flight", "targets"}
    with pytest.raises(RuntimeError):
        R.reward("x", "about 300 m", cad=False, flight=False)


def test_failure_before_a_skipped_gate_still_scores(monkeypatch):
    monkeypatch.setattr(R, "gate_format", lambda c, f: ({"openrocket": {"children": []}}, None))
    monkeypatch.setattr(R, "gate_structure", lambda d: ([("m", "C6")], None))
    monkeypatch.setattr(R, "gate_motors", lambda m, p, l: (True, None, "stub"))
    monkeypatch.setattr(R, "fit_problems", lambda root: ["29.0 mm motor does not fit a 26.6 mm mount"])
    r = R.score_answer("x", "about 300 m", cad=False, flight=False)
    assert r["gate_failed"] == "cad" and r["score"] == -0.8
