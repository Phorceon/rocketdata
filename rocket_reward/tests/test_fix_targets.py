"""Stage 7 scores every target from the prompt the same way.

t is the product of one credit per stated target (no weights), the prompt's
landing limit is a stage 7 target only (stage 6 judges no prompt number), a
"max" landing target without a tol gets limits.LANDING_SLACK_DEFAULT, and the
two motor targets never zero the product. Runs without Java on recorded
simulator replies, through the real targets stage and the real score formula.
"""
from __future__ import annotations

import itertools
import math
import random

import pytest

from rocket_reward import flight, ladder
from rocket_reward import limits as L
from rocket_reward.motors import MotorTable
from rocket_reward.records import Requirements, Target
from rocket_reward.targets import check_targets, landing_credit

from replies import each_branch, load_reply

NUMERIC = ("apogee_m", "landing_ms", "flight_time_s", "time_to_apogee_s", "max_velocity_ms", "max_accel_ms2",
           "body_diameter_m", "mass_kg")


@pytest.fixture(scope="module")
def table() -> MotorTable:
    return MotorTable.load()


def nominal_of(reply: dict) -> dict:
    return reply["flights"][L.NOMINAL_FLIGHT]


def measured_of(reply: dict) -> dict:
    """What stage 7 measures on the recorded single-stage reply."""
    f = nominal_of(reply)
    chk = check_targets(reply, Requirements(id="m", apogee_m=Target(1.0, "about"),
                                            body_diameter_m=Target(1.0, "about")), {}, MotorTable({}))
    body = next(r for r in chk.info["targets"] if r["target"] == "body_diameter_m")["measured"]
    return {"apogee_m": f["apogee_m"], "landing_ms": f["branches"][0]["landing_vertical_ms"],
            "flight_time_s": f["flight_time_s"], "time_to_apogee_s": f["time_to_apogee_s"],
            "max_velocity_ms": f["max_velocity_ms"], "max_accel_ms2": f["max_accel_ms2"],
            "body_diameter_m": body, "mass_kg": reply["rocket"]["mass_kg"]}


MEASURED = measured_of(load_reply())
FLOWN_MOTORS = ("K550W", "I211W")      # what the recorded single-stage reply flies; largest K550W, class K


def met(field: str) -> Target:
    """A target the recorded reply meets exactly (a landing limit with room, above the comfort floor)."""
    if field == "landing_ms":
        return Target(MEASURED[field], "max", 0.0)
    return Target(MEASURED[field], "about")


def score_of(reply: dict, req: Requirements, table: MotorTable) -> float:
    """The score of a design that reached stage 7 with this reply and these requirements."""
    chk = check_targets(reply, req, {}, table)
    assert chk.passed and chk.stage == "targets"
    return ladder.stage_score("targets", chk.credit)


def requirements(**targets) -> Requirements:
    targets.setdefault("apogee_m", met("apogee_m"))
    return Requirements(id="fix", **targets)


def missed_target(field: str, factor: float, kind: str) -> Target:
    """A target that the recorded value misses by `factor` (>= 1) on the side `kind` judges."""
    m = MEASURED[field]
    if kind == "max":
        return Target(m / factor, "max", 0.0)
    if kind == "min":
        return Target(m * factor, "min", 0.0)
    return Target(m * factor, "about", 0.0)


# ------------------------------------------------------------------ b1: further away never scores more

@pytest.mark.parametrize("field", NUMERIC)
@pytest.mark.parametrize("kind", ["about", "max", "min"])
def test_further_from_the_target_never_scores_more(table, field, kind):
    """Moving the target away from the measured value, step by step, never raises the score."""
    reply = load_reply()
    last = None
    for i in range(80):
        factor = 1.04 ** i
        others = {} if field == "apogee_m" else {"apogee_m": met("apogee_m")}
        s = score_of(reply, requirements(**others, **{field: missed_target(field, factor, kind)}), table)
        if last is not None:
            assert s <= last + 1e-12, (field, kind, factor)
        last = s
    assert last < 0.80, (field, kind, last)       # 23 times off loses most of the band


@pytest.mark.parametrize("limit", [3.0, 5.0, 8.0])
@pytest.mark.parametrize("tol", [None, 0.0, 0.1])
def test_landing_further_from_the_band_never_scores_more(table, limit, tol):
    """The measured landing speed stepped away from the full-credit band on both sides."""
    target = Target(limit, "max", tol)
    best = limit * 0.9
    for direction in (1.02, 1 / 1.02):
        speed, last = best, None
        for _ in range(150):
            reply = each_branch(load_reply(), 0, landing_vertical_ms=speed)
            s = score_of(reply, requirements(landing_ms=target, apogee_m=met("apogee_m")), table)
            if last is not None:
                assert s <= last + 1e-12, (limit, tol, speed)
            last = s
            speed *= direction


def test_fewer_named_motors_flown_never_scores_more(table):
    reply = load_reply()
    named = [("K550W", "I211W"), ("K550W", "I211W", "M2000R"), ("K550W", "M2000R"),
             ("K550W", "M2000R", "H128W"), ("M2000R",)]
    scores = [score_of(reply, requirements(motors=n), table) for n in named]
    assert scores == sorted(scores, reverse=True), scores
    assert scores[0] == 1.0 and scores[-1] == ladder.stage_score("targets", ladder.MOTORS_CREDIT_MIN)


def test_further_motor_class_never_scores_more(table):
    reply = load_reply()                             # largest motor K550W: class K
    by_steps = [score_of(reply, requirements(motor_class=c), table) for c in "KLMNO"]
    assert by_steps == sorted(by_steps, reverse=True)
    assert by_steps[:3] == [1.0, ladder.stage_score("targets", ladder.MOTOR_CLASS_NEAR_CREDIT),
                            ladder.stage_score("targets", ladder.MOTOR_CLASS_FAR_CREDIT)]
    assert by_steps[3] == by_steps[4] == by_steps[2]


# ------------------------------------------------------------------ b2: two misses never beat one

MISSES = [(f, k) for f in NUMERIC for k in ("about", "max", "min")]


def test_missing_two_never_beats_missing_one(table):
    """For every pair of numeric targets and several sizes of miss: the design missing
    both never scores above the same design missing only one of them by the same amount."""
    reply = load_reply()
    rng = random.Random(7)
    checked = 0
    for (fa, ka), (fb, kb) in itertools.combinations(MISSES, 2):
        if fa == fb:
            continue
        for _ in range(3):
            xa, xb = 1 + rng.random() * 3, 1 + rng.random() * 3
            base = {f: met(f) for f in ("apogee_m",)}
            one_a = requirements(**{**base, fa: missed_target(fa, xa, ka)})
            one_b = requirements(**{**base, fb: missed_target(fb, xb, kb)})
            both = requirements(**{**base, fa: missed_target(fa, xa, ka), fb: missed_target(fb, xb, kb)})
            s_both = score_of(reply, both, table)
            assert s_both <= score_of(reply, one_a, table) + 1e-12, (fa, ka, fb, kb)
            assert s_both <= score_of(reply, one_b, table) + 1e-12, (fa, ka, fb, kb)
            checked += 1
    assert checked > 500


def test_a_motor_miss_on_top_of_a_numeric_miss_never_scores_more(table):
    reply = load_reply()
    for field in NUMERIC:
        others = {} if field == "apogee_m" else {"apogee_m": met("apogee_m")}
        one = requirements(**others, **{field: missed_target(field, 2.0, "about")})
        both = requirements(**others, **{field: missed_target(field, 2.0, "about")}, motors=("M2000R",),
                            motor_class="M")
        assert score_of(reply, both, table) < score_of(reply, one, table)


# ------------------------------------------------------------------ b3: all credits 1 gives exactly 1.0

def test_every_target_met_scores_exactly_one(table):
    reply = load_reply()
    req = requirements(**{f: met(f) for f in NUMERIC}, motors=FLOWN_MOTORS, motor_class="K")
    chk = check_targets(reply, req, {}, table)
    assert [r["credit"] for r in chk.info["targets"]] == [1.0] * 10
    assert chk.credit == 1.0 and chk.reasons == []
    assert ladder.stage_score("targets", chk.credit) == 1.0


# ------------------------------------------------------------------ b4: stage 7 stays in 0.70 - 1.00

def test_every_score_in_stage_7_stays_in_its_band(table):
    """Random targets of every kind (and missing measured values): the score stays in 0.70 - 1.00."""
    rng = random.Random(11)
    seen = []
    for _ in range(400):
        reply = load_reply()
        if rng.random() < 0.15:
            nominal_of(reply)[rng.choice(["apogee_m", "flight_time_s", "max_velocity_ms"])] = None
        fields = {}
        for f in NUMERIC:
            if f == "apogee_m" or rng.random() < 0.5:
                kind = rng.choice(["about", "max", "min"])
                tol = rng.choice([None, 0.0, 0.05, 0.3])
                fields[f] = Target(MEASURED[f] * math.exp(rng.uniform(-3, 3)), kind, tol)
        if rng.random() < 0.5:
            fields["motors"] = tuple(rng.sample(["K550W", "I211W", "M2000R", "H128W"], rng.randint(1, 3)))
        if rng.random() < 0.5:
            fields["motor_class"] = rng.choice("AHIJKLMO")
        s = score_of(reply, Requirements(id="r", **fields), table)
        assert 0.70 <= s <= 1.0
        seen.append(s)
    assert min(seen) == 0.70 and max(seen) > 0.95     # the whole band is used


# ------------------------------------------------------------------ the landing target

def test_a_max_landing_target_without_tol_gets_the_default_slack():
    t = Target(5.0, "max")
    edge = 5.0 * (1 + L.LANDING_SLACK_DEFAULT)
    assert landing_credit(edge, t) == 1.0
    assert landing_credit(edge * 1.01, t) == pytest.approx(ladder.closeness(edge * 1.01, 5.0, "max",
                                                                            L.LANDING_SLACK_DEFAULT))
    assert landing_credit(edge * 1.01, t) < 1.0


def test_a_given_tol_is_used_as_given():
    assert landing_credit(5.01, Target(5.0, "max", 0.0)) < 1.0
    assert landing_credit(5.0, Target(5.0, "max", 0.0)) == 1.0
    assert landing_credit(5.4, Target(5.0, "max", 0.1)) == 1.0
    assert landing_credit(5.6, Target(5.0, "max", 0.1)) < 1.0
    # the slack is only for a "max" landing target: "about" keeps the usual default
    assert landing_credit(5.6, Target(5.0, "about")) == pytest.approx(ladder.closeness(5.6, 5.0, "about"))


def test_landing_reason_shows_the_slack(table):
    reply = each_branch(load_reply(), 0, landing_vertical_ms=7.0)
    chk = check_targets(reply, requirements(landing_ms=Target(5.0, "max")), {}, table)
    credit = ladder.closeness(7.0, 5.0, "max", L.LANDING_SLACK_DEFAULT)
    assert chk.reasons == [f"landing speed 7.00 m/s, asked for at most 5.00 m/s (15% allowed): credit {credit:.2f}"]


def test_a_landing_over_the_prompt_limit_passes_stage_6_and_costs_in_stage_7(table):
    """Landing 1% over the prompt's limit (tol 0.0) passes the flight stage and loses about 0.01."""
    reply = load_reply()
    land = MEASURED["landing_ms"]
    req = requirements(landing_ms=Target(land / 1.01, "max", 0.0))
    assert flight.check_flight(reply, Requirements(id="f", apogee_m=met("apogee_m"), landing_ms=req.landing_ms,
                                                   wind_ms=2.0)).passed
    loss = 1.0 - score_of(reply, req, table)
    assert 0.008 < loss < 0.015
    # 100% over: still in stage 7
    req = requirements(landing_ms=Target(land / 2, "max", 0.0))
    assert 0.70 < score_of(reply, req, table) < 0.85


@pytest.mark.parametrize("factor,low,high", [(1.1, 0.04, 0.055), (2.0, 0.20, 0.23), (10.0, 0.26, 0.28)])
def test_apogee_misses_cost_the_same_whatever_else_is_stated(table, factor, low, high):
    """The apogee miss costs the same with one target stated or with every one: no weights."""
    reply = load_reply()
    off = Target(MEASURED["apogee_m"] * factor, "about")
    alone = score_of(reply, requirements(apogee_m=off), table)
    every = score_of(reply, requirements(apogee_m=off, **{f: met(f) for f in NUMERIC if f != "apogee_m"},
                                         motors=FLOWN_MOTORS, motor_class="K"), table)
    assert alone == every
    assert low <= 1.0 - alone <= high


# ------------------------------------------------------------------ motors never zero the product

def test_a_different_real_motor_halves_the_credit(table):
    reply = load_reply()
    req = requirements(**{f: met(f) for f in NUMERIC if f != "apogee_m"}, motors=("M2000R",), motor_class="B")
    chk = check_targets(reply, req, {}, table)
    credits = {r["target"]: r["credit"] for r in chk.info["targets"]}
    assert credits["motors"] == ladder.MOTORS_CREDIT_MIN and credits["motor_class"] == ladder.MOTOR_CLASS_FAR_CREDIT
    assert chk.credit == pytest.approx(ladder.MOTORS_CREDIT_MIN * ladder.MOTOR_CLASS_FAR_CREDIT)
    assert any(x.startswith("motors: flies 0 of the 1 motors") and x.endswith("credit 0.50") for x in chk.reasons)
    assert any("asked for class B" in x and x.endswith("credit 0.50") for x in chk.reasons)


def test_a_missing_measured_value_still_earns_nothing(table):
    reply = load_reply()
    nominal_of(reply)["flight_time_s"] = None
    chk = check_targets(reply, requirements(flight_time_s=Target(60.0, "about"), motors=FLOWN_MOTORS), {}, table)
    assert chk.credit == 0.0
    assert ladder.stage_score("targets", chk.credit) == 0.70


def test_no_weight_names_left():
    assert not hasattr(ladder, "APOGEE_WEIGHT") and not hasattr(ladder, "OTHER_TARGET_WEIGHT")
    assert 0 < ladder.MOTOR_CLASS_FAR_CREDIT <= ladder.MOTORS_CREDIT_MIN < 1
    assert ladder.MOTOR_CLASS_FAR_CREDIT < ladder.MOTOR_CLASS_NEAR_CREDIT < 1
