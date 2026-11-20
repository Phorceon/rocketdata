"""Stage 6 (flight.py): the flight plan, the rail length, the landing limit and
every safety rule, on editable copies of real recorded simulator replies."""
from __future__ import annotations

import math
import random

import pytest

from rocket_reward import flight, ladder
from rocket_reward import limits as L
from rocket_reward.motors import MotorTable
from rocket_reward.records import Requirements, Target

from replies import each_branch, each_flight, load_reply

NO_LIMIT = Requirements(id="t", apogee_m=Target(500.0, "about"), wind_ms=2.0)


def requirement_with_landing(value: float, tol: "float | None" = None, kind: str = "max") -> Requirements:
    """Requirements with a 2 m/s wind and a landing target."""
    return Requirements(id="t", apogee_m=Target(500.0, "about"), landing_ms=Target(value, kind, tol), wind_ms=2.0)


def rule_sizes(check, index: int = 0) -> dict:
    """{rule: size} of one flight's violations."""
    return {v["rule"]: v["size"] for v in check.info["flight_violations"][index]}


# --------------------------------------------------------------------------- plan

def test_flight_plan_scales_and_caps_the_wind():
    assert flight.flight_plan(NO_LIMIT) == [{"wind_ms": 1.0, "seed": 1}, {"wind_ms": 2.0, "seed": 2},
                                            {"wind_ms": 3.0, "seed": 3}]
    windy = Requirements(id="t", apogee_m=Target(500.0, "about"), wind_ms=8.0)
    assert [p["wind_ms"] for p in flight.flight_plan(windy)] == [4.0, 8.0, L.WIND_MAX_MS]
    calm = Requirements(id="t", apogee_m=Target(500.0, "about"), wind_ms=0.0)
    assert [p["wind_ms"] for p in flight.flight_plan(calm)] == [0.0, 0.0, 0.0]
    default = Requirements(id="t", apogee_m=Target(500.0, "about"))
    assert [p["wind_ms"] for p in flight.flight_plan(default)] == [f * L.DEFAULT_WIND_MS for f in L.WIND_FACTORS]
    assert [p["seed"] for p in flight.flight_plan(default)] == list(L.FLIGHT_SEEDS)


def test_landing_limit_uses_slack_and_cap():
    assert flight.landing_limit_ms(NO_LIMIT) is None
    assert flight.landing_limit_ms(requirement_with_landing(5.0)) == pytest.approx(5.0 * (1 + L.LANDING_SLACK_DEFAULT))
    assert flight.landing_limit_ms(requirement_with_landing(5.0, tol=0.05)) == pytest.approx(5.25)
    assert flight.landing_limit_ms(requirement_with_landing(5.0, tol=0.0)) == pytest.approx(5.0)
    assert flight.landing_limit_ms(requirement_with_landing(8.5)) == L.LANDING_HARD_MAX_MS
    assert flight.landing_limit_ms(requirement_with_landing(5.0, kind="min")) is None


def motor_tree(*motors: str) -> dict:
    """A minimal design tree with one motor mount per motor id, all in the flown configuration."""
    tubes = [{"bodytube": {"children": [{"motormount": {"children": [
        {"motor": {"attrs": {"configid": "c1"}, "children": [{"motor_id": {"value": m}},
                                                               {"designation": {"value": m.split("-")[-1]}}]}}]}}]}}
        for m in motors]
    return {"openrocket": {"children": [{"rocket": {"children": [
        {"motorconfiguration": {"attrs": {"configid": "c1", "default": "true"}}},
        {"subcomponents": {"children": [{"stage": {"children": [{"subcomponents": {"children": tubes}}]}}]}}]}}]}}


@pytest.fixture(scope="module")
def rail_table() -> MotorTable:
    """A small motor table: one motor at each edge of the classes that change the rail."""
    impulses = {"F80": 80.0, "G81": 80.01, "G160": 160.0, "H161": 160.01, "I640": 640.0, "J641": 640.01,
                "K2560": 2560.0, "L2561": 2560.01, "O40000": 40000.0, "A1": 1.0}
    return MotorTable({f"Test-{d}": {"manufacturer": "Test", "designation": d, "total_impulse_ns": ns,
                                     "diameter_m": 0.029} for d, ns in impulses.items()})


@pytest.mark.parametrize("motor, rail", [
    ("Test-A1", 1.5), ("Test-F80", 1.5), ("Test-G81", 1.8), ("Test-G160", 1.8), ("Test-H161", 2.4),
    ("Test-I640", 2.4), ("Test-J641", 3.0), ("Test-K2560", 3.0), ("Test-L2561", 3.7), ("Test-O40000", 3.7)])
def test_rail_length_follows_the_motor_class(rail_table, motor, rail):
    assert flight.rail_length_m(motor_tree(motor), rail_table) == rail


def test_rail_length_uses_the_largest_single_motor(rail_table):
    assert flight.rail_length_m(motor_tree("Test-F80", "Test-F80", "Test-F80", "Test-F80"), rail_table) == 1.5
    assert flight.rail_length_m(motor_tree("Test-F80", "Test-J641", "Test-G81"), rail_table) == 3.0


def test_rail_length_without_a_known_motor(rail_table):
    assert flight.rail_length_m(motor_tree(), rail_table) == L.RAIL_LENGTH_BY_CLASS_M[0][1]
    assert flight.rail_length_m(motor_tree("Nobody-K550"), rail_table) == 3.0   # by its written class
    assert flight.rail_length_m({"openrocket": "junk"}, rail_table) == 1.5
    assert flight.rail_length_m({}, rail_table) == 1.5


# --------------------------------------------------------------------------- sound replies pass

@pytest.mark.parametrize("name", ["single_stage", "two_stage"])
def test_recorded_sound_rockets_pass(name):
    check = flight.check_flight(load_reply(name), requirement_with_landing(5.0))
    assert check.stage == "flight" and check.passed and check.credit == 1.0 and check.reasons == []
    assert check.info["flight_violations"] == [[], [], []]
    assert check.info["landing_limit_ms"] == pytest.approx(5.75)


def test_info_carries_nominal_metrics_and_per_flight_lists():
    reply = load_reply("single_stage")
    check = flight.check_flight(reply, NO_LIMIT)
    nominal = reply["flights"][L.NOMINAL_FLIGHT]
    m = check.info["metrics"]
    assert m["apogee_m"] == nominal["apogee_m"] and m["wind_ms"] == 2.0 and m["seed"] == 2
    assert m["landing_ms"] == nominal["branches"][0]["landing_vertical_ms"]
    assert m["flight_time_s"] == nominal["flight_time_s"] and m["mass_kg"] == reply["rocket"]["mass_kg"]
    assert len(check.info["flight_violations"]) == 3 and check.info["worst_flight"] == 0
    assert check.info["winds_ms"] == [1.0, 2.0, 3.0]


# --------------------------------------------------------------------------- each rule alone

# (reply, field, value that just passes, value that just fails, where the field lives, rule, words in the reason)
EDGES = [
    ("single_stage", "rail_exit_ms", L.RAIL_EXIT_MIN_MS, L.RAIL_EXIT_MIN_MS - 0.01, "flight", "rail_exit",
     "leaves the rail at 10.99 m/s; it needs at least 11 m/s"),
    ("single_stage", "liftoff_twr", L.THRUST_TO_WEIGHT_MIN, L.THRUST_TO_WEIGHT_MIN - 0.01, "flight",
     "thrust_to_weight", "thrust-to-weight ratio is 2.99"),
    ("single_stage", "stability_rail_cal", 0.001, 0.0, "flight", "rail_stability",
     "leaving the rail is 0.00 cal"),
    ("single_stage", "stability_min_burn_cal", 0.001, 0.0, "flight", "burn_stability",
     "falls to 0.00 cal"),
    ("single_stage", "deploy_speed_ms", L.DEPLOY_SPEED_MAX_MS, L.DEPLOY_SPEED_MAX_MS + 0.01, "branch0",
     "deploy_speed", "opens at 60.01 m/s; it must open at 60 m/s or slower"),
    ("single_stage", "landing_vertical_ms", L.LANDING_HARD_MAX_MS, L.LANDING_HARD_MAX_MS + 0.01, "branch0",
     "landing_hard_0", "lands at 9.01 m/s vertical speed"),
    ("two_stage", "landing_vertical_ms", L.UNRECOVERED_LANDING_MAX_MS, L.UNRECOVERED_LANDING_MAX_MS + 0.01,
     "branch1", "landing_unrecovered_1", "no recovery device and hits the ground at 25.01 m/s"),
]


def set_value(reply: dict, where: str, field: str, value) -> dict:
    """Set one field on every flight, or on branch N of every flight."""
    if where == "flight":
        return each_flight(reply, **{field: value})
    return each_branch(reply, int(where[len("branch"):]), **{field: value})


@pytest.mark.parametrize("name, field, ok, bad, where, rule, words", EDGES)
def test_each_rule_just_inside_and_just_outside(name, field, ok, bad, where, rule, words):
    good = flight.check_flight(set_value(load_reply(name), where, field, ok), NO_LIMIT)
    assert good.passed, good.reasons
    broken = flight.check_flight(set_value(load_reply(name), where, field, bad), NO_LIMIT)
    assert not broken.passed
    sizes = rule_sizes(broken)
    assert list(sizes) == [rule], sizes
    assert 0 < sizes[rule] < 0.2   # just outside costs little
    assert 0 < broken.credit < 1 and broken.credit == pytest.approx(1 / (1 + sizes[rule]))
    assert len(broken.reasons) == 1 and words in broken.reasons[0], broken.reasons
    assert broken.reasons[0].startswith("in 1.0 m/s wind")


def test_zero_stability_fails_by_the_step():
    check = flight.check_flight(each_flight(load_reply(), stability_rail_cal=0.0), NO_LIMIT)
    assert rule_sizes(check)["rail_stability"] == pytest.approx(ladder.STABILITY_ZERO_STEP)
    deep = flight.check_flight(each_flight(load_reply(), stability_min_burn_cal=-20.0), NO_LIMIT)
    assert rule_sizes(deep)["burn_stability"] == ladder.MAX_VIOLATION


def test_static_stability_is_judged_once():
    reply = load_reply()
    reply["rocket"]["stability_cal"] = L.STATIC_STABILITY_MIN_CAL
    assert flight.check_flight(reply, NO_LIMIT).passed
    reply["rocket"]["stability_cal"] = 0.5
    check = flight.check_flight(reply, NO_LIMIT)
    assert not check.passed and check.info["flight_violations"] == [[], [], []]
    assert check.info["static_violation"] == pytest.approx(1.0)
    assert check.credit == pytest.approx(0.5)
    assert check.reasons == ["on the pad the rocket's stability margin is 0.5 cal; it needs at least 1 cal "
                             "(move mass forward or enlarge the fins)"]


def test_recovery_that_never_opens():
    reply = each_branch(load_reply(), 0, deployed=False, deployments=[], deploy_speed_ms=None,
                        deploy_during_burn=None, deploy_time_s=None)
    check = flight.check_flight(reply, NO_LIMIT)
    assert rule_sizes(check) == {"deploys_0": ladder.YES_NO_VIOLATION}
    assert "never opens" in check.reasons[0]


def test_opening_during_a_burn():
    check = flight.check_flight(each_branch(load_reply(), 0, deploy_during_burn=True), NO_LIMIT)
    assert rule_sizes(check) == {"deploy_during_burn": ladder.YES_NO_VIOLATION}
    assert "while a motor is still burning" in check.reasons[0]


def test_section_that_never_lands_is_charged_once():
    reply = each_branch(load_reply(), 0, landed=False, landing_vertical_ms=None, landing_total_ms=None)
    check = flight.check_flight(reply, requirement_with_landing(5.0))
    assert rule_sizes(check) == {"lands_0": ladder.NO_FLIGHT_VIOLATION}
    assert "never reaches the ground" in check.reasons[0]


def test_prompt_landing_limit_on_the_main_section():
    req = requirement_with_landing(5.0)          # 5.75 m/s with the default slack
    assert flight.check_flight(each_branch(load_reply(), 0, landing_vertical_ms=5.75), req).passed
    check = flight.check_flight(each_branch(load_reply(), 0, landing_vertical_ms=5.76), req)
    assert rule_sizes(check) == {"landing_prompt": pytest.approx(math.log2(5.76 / 5.75), abs=1e-6)}
    assert "the prompt's landing limit with its slack is 5.75 m/s" in check.reasons[0]
    # Without a stated limit only the hard limit applies.
    assert flight.check_flight(each_branch(load_reply(), 0, landing_vertical_ms=8.0), NO_LIMIT).passed


def test_prompt_limit_does_not_apply_to_a_booster():
    req = requirement_with_landing(5.0)
    check = flight.check_flight(load_reply("two_stage"), req)   # the booster lands at 11.8 m/s
    assert check.passed


def test_booster_given_a_recovery_device_must_land_softly():
    reply = each_branch(load_reply("two_stage"), 1, has_recovery=True, deployed=True, deploy_speed_ms=5.0,
                        deploy_during_burn=False)
    check = flight.check_flight(reply, NO_LIMIT)
    assert rule_sizes(check) == {"landing_hard_1": pytest.approx(math.log2(11.81331146119454 / 9.0), abs=1e-6)}


def test_main_section_without_recovery_uses_the_hard_limit():
    reply = each_branch(load_reply(), 0, has_recovery=False, landing_vertical_ms=20.0)
    assert "landing_hard_0" in rule_sizes(flight.check_flight(reply, NO_LIMIT))


# --------------------------------------------------------------------------- aborts and caps

@pytest.mark.parametrize("fields", [{"abort": "Stage began to tumble under thrust"}, {"hit_step_cap": True},
                                    {"hit_time_cap": True}, {"abort": ""}])
def test_stopped_flight_costs_no_flight_plus_the_rest(fields):
    reply = load_reply()
    reply["flights"][1].update(fields)
    check = flight.check_flight(reply, NO_LIMIT)
    assert not check.passed and check.info["worst_flight"] == 1
    assert rule_sizes(check, 1) == {"no_flight": ladder.NO_FLIGHT_VIOLATION}
    assert check.credit == pytest.approx(1 / (1 + ladder.NO_FLIGHT_VIOLATION))
    assert check.reasons[0].startswith("in 2.0 m/s wind")
    # whatever else is wrong still counts on top
    reply["flights"][1]["rail_exit_ms"] = 5.5
    worse = flight.check_flight(reply, NO_LIMIT)
    assert rule_sizes(worse, 1) == {"no_flight": 3.0, "rail_exit": pytest.approx(1.0)}
    assert worse.credit < check.credit


def test_abort_with_nothing_landed():
    reply = load_reply()
    f = reply["flights"][2]
    f.update(abort="Simulation stopped", rail_exit_ms=None)
    f["branches"][0].update(landed=False, landing_vertical_ms=None)
    sizes = rule_sizes(flight.check_flight(reply, NO_LIMIT), 2)
    assert sizes == {"no_flight": 3.0, "rail_exit": 3.0, "lands_0": 3.0}


def test_flight_without_numbers():
    reply = load_reply()
    reply["flights"][0] = {"wind_ms": 1.0, "seed": 1, "ok": False, "error": "boom", "error_kind": "crash"}
    check = flight.check_flight(reply, NO_LIMIT)
    sizes = rule_sizes(check, 0)
    assert sizes["no_flight"] == ladder.NO_FLIGHT_VIOLATION and sizes["rail_exit"] == ladder.MAX_VIOLATION
    assert check.info["worst_flight"] == 0 and 0 < check.credit < 0.1


# --------------------------------------------------------------------------- worst of three

def test_the_worst_flight_counts_not_the_sum():
    reply = load_reply()
    reply["flights"][0]["rail_exit_ms"] = 9.0     # log2(11 / 9) = 0.29
    reply["flights"][2]["rail_exit_ms"] = 5.5     # log2(11 / 5.5) = 1
    check = flight.check_flight(reply, NO_LIMIT)
    assert check.info["worst_flight"] == 2
    assert check.credit == pytest.approx(0.5)
    assert check.info["flight_totals"][0] == pytest.approx(math.log2(11 / 9), abs=1e-6)
    assert check.reasons == ["in 3.0 m/s wind the rocket leaves the rail at 5.5 m/s; it needs at least 11 m/s "
                             "(use a motor with more initial thrust or a lighter rocket)"]


def test_different_problems_in_different_winds():
    reply = load_reply()
    reply["flights"][0]["stability_rail_cal"] = -0.4          # 0.5
    reply["flights"][2]["branches"][0]["deploy_speed_ms"] = 120.0   # 1.0
    check = flight.check_flight(reply, NO_LIMIT)
    assert check.info["worst_flight"] == 2 and check.credit == pytest.approx(0.5)
    assert len(check.reasons) == 2 and check.reasons[0].startswith("in 3.0 m/s wind")
    assert check.reasons[1].startswith("in 1.0 m/s wind")


def test_static_adds_to_the_worst_flight():
    reply = load_reply()
    reply["rocket"]["stability_cal"] = 0.5                    # 1.0
    reply["flights"][1]["rail_exit_ms"] = 5.5                 # 1.0
    assert flight.check_flight(reply, NO_LIMIT).credit == pytest.approx(1 / 3)


# --------------------------------------------------------------------------- nulls and odd replies

NULLABLE = [("flight", "rail_exit_ms", "rail_exit"), ("flight", "liftoff_twr", "thrust_to_weight"),
            ("flight", "stability_rail_cal", "rail_stability"),
            ("flight", "stability_min_burn_cal", "burn_stability"),
            ("branch0", "deploy_speed_ms", "deploy_speed"), ("branch0", "landing_vertical_ms", "landing_hard_0"),
            ("branch0", "deploy_during_burn", "deploy_during_burn")]


@pytest.mark.parametrize("bad", [None, "12", True, float("nan"), float("inf"), [], {}])
@pytest.mark.parametrize("where, field, rule", NULLABLE)
def test_missing_number_counts_as_the_largest_violation(where, field, rule, bad):
    check = flight.check_flight(set_value(load_reply(), where, field, bad), NO_LIMIT)
    if field == "deploy_during_burn" and bad is True:
        assert rule_sizes(check)[rule] == ladder.YES_NO_VIOLATION
        return
    assert not check.passed
    assert rule_sizes(check)[rule] == ladder.MAX_VIOLATION, rule_sizes(check)
    assert "unknown" in check.reasons[0] or "did not say" in check.reasons[0]


@pytest.mark.parametrize("field", ["rail_exit_ms", "liftoff_twr", "stability_rail_cal"])
def test_removed_number_counts_as_the_largest_violation(field):
    reply = load_reply()
    for f in reply["flights"]:
        del f[field]
    assert not flight.check_flight(reply, NO_LIMIT).passed


def test_missing_landing_speed_with_a_prompt_limit_counts_twice():
    check = flight.check_flight(each_branch(load_reply(), 0, landing_vertical_ms=None), requirement_with_landing(5.0))
    assert rule_sizes(check) == {"landing_hard_0": 3.0, "landing_prompt": 3.0}


def test_missing_static_stability():
    reply = load_reply()
    del reply["rocket"]["stability_cal"]
    check = flight.check_flight(reply, NO_LIMIT)
    assert check.info["static_violation"] == ladder.MAX_VIOLATION and "unknown" in check.reasons[0]


@pytest.mark.parametrize("reply", [None, 7, "text", [], {}, {"ok": True}, {"flights": None, "rocket": None},
                                   {"flights": [None, 3, "x"], "rocket": {"stability_cal": 2.0}},
                                   {"flights": [{"ok": True, "branches": None}] * 3, "rocket": []}])
def test_odd_replies_become_normal_results(reply):
    check = flight.check_flight(reply, NO_LIMIT)  # type: ignore[arg-type]
    assert check.stage == "flight" and not check.passed and 0 <= check.credit < 0.25
    assert check.reasons and len(check.info["flight_violations"]) == 3


def test_fewer_flights_than_planned():
    reply = load_reply()
    reply["flights"] = reply["flights"][:2]
    check = flight.check_flight(reply, NO_LIMIT)
    assert not check.passed and check.info["worst_flight"] == 2
    assert check.reasons[0].startswith("in 3.0 m/s wind the simulator could not fly")


def test_odd_branches():
    reply = load_reply("two_stage")
    reply["flights"][0]["branches"][1] = "booster"
    reply["flights"][1]["branches"][1]["has_recovery"] = None
    reply["flights"][2]["branches"] = []
    check = flight.check_flight(reply, NO_LIMIT)
    assert rule_sizes(check, 0) == {"section_1": 3.0}
    assert rule_sizes(check, 1)["recovery_known_1"] == 3.0
    assert rule_sizes(check, 2) == {"sections": 3.0}


def test_random_junk_never_crashes():
    rng = random.Random(6)
    junk = [None, True, False, -1.0, 0.0, 1e308, -1e308, float("nan"), "", "x" * 500, [], {}, 10**400, 3]
    for _ in range(400):
        reply = load_reply(rng.choice(["single_stage", "two_stage"]))
        for _ in range(rng.randint(1, 6)):
            flights = reply.get("flights") if isinstance(reply.get("flights"), list) and reply.get("flights") else [{}]
            f = rng.choice(flights)
            f = f if isinstance(f, dict) else {}
            branches = f.get("branches") if isinstance(f.get("branches"), list) and f.get("branches") else [{}]
            target = rng.choice([f, rng.choice(branches), reply.get("rocket"), reply])
            if isinstance(target, dict) and target:
                target[rng.choice(sorted(target))] = rng.choice(junk)
        check = flight.check_flight(reply, requirement_with_landing(4.0))
        assert 0 <= check.credit <= 1 and isinstance(check.reasons, list)
        assert all(isinstance(r, str) for r in check.reasons)


# --------------------------------------------------------------------------- closer is never worse

@pytest.mark.parametrize("where, field, values", [
    ("flight", "rail_exit_ms", [0.0, 0.5, 1.0, 2.0, 5.0, 9.0, 10.99, 11.0, 30.0]),
    ("flight", "liftoff_twr", [0.0, 0.3, 1.0, 2.0, 2.99, 3.0]),
    ("flight", "stability_rail_cal", [-30.0, -3.0, -2.9, -1.0, -0.1, 0.0, 0.0001, 2.0]),
    ("flight", "stability_min_burn_cal", [-30.0, -1.0, -0.5, 0.0, 0.5]),
    ("branch0", "deploy_speed_ms", [1000.0, 480.0, 200.0, 100.0, 60.01, 60.0, 5.0]),
    ("branch0", "landing_vertical_ms", [1000.0, 72.0, 30.0, 12.0, 9.01, 9.0, 3.0]),
])
def test_closer_is_never_worse(where, field, values):
    credits = [flight.check_flight(set_value(load_reply(), where, field, v), NO_LIMIT).credit for v in values]
    assert credits == sorted(credits), list(zip(values, credits))
    assert credits[0] < credits[-1] == 1.0


def test_booster_landing_is_monotone():
    values = [500.0, 200.0, 64.0, 40.0, 25.01, 25.0]
    credits = [flight.check_flight(each_branch(load_reply("two_stage"), 1, landing_vertical_ms=v), NO_LIMIT).credit
               for v in values]
    assert credits == sorted(credits) and credits[-1] == 1.0


def test_flight_score_stays_in_its_band():
    reply = each_flight(load_reply(), abort="x", rail_exit_ms=None, liftoff_twr=None,
                        stability_rail_cal=None, stability_min_burn_cal=None)
    check = flight.check_flight(reply, NO_LIMIT)
    s = ladder.stage("flight")
    assert s.floor <= ladder.stage_score("flight", check.credit) < s.top


# --------------------------------------------------------------------------- with the simulator

@pytest.fixture(scope="module")
def flight_sim():
    from rocket_reward import sim
    with sim.Simulator() as s:
        yield s


@pytest.mark.needs_java
def test_reference_designs_fly_through_stage_6(gold_rows, flight_sim):
    from rocket_reward import ork
    from rocket_reward.motors import MotorTable as Table
    from rocket_reward.scoring import preflight
    table = Table.load()
    flown = passed = 0
    for row in gold_rows[:24:3]:   # one row of each of the first eight rockets
        pre = preflight(row["answer"], motor_table=table)
        if not pre.passed:
            continue
        root = pre.clean_root
        reply = flight_sim.run(ork.design_to_ork(root), flight.rail_length_m(root, table),
                               flight.flight_plan(NO_LIMIT), config_id=ork.flight_config_id(root))
        if not reply.get("ok"):
            continue
        check = flight.check_flight(reply, NO_LIMIT)
        flown += 1
        passed += check.passed
        assert len(check.info["flight_violations"]) == 3 and "apogee_m" in check.info["metrics"]
        assert check.passed or (check.reasons and 0 < check.credit < 1)
    assert flown >= 6 and passed >= flown - 1


@pytest.mark.parametrize("bad", [-15.06, -9.88, -0.001, 0.0, -0.0])
def test_landing_speed_that_is_not_downward_counts_as_unknown(bad):
    """landing_vertical_ms is downward and positive; zero or upward on a landed
    section is an odd reply (an older helper read OpenRocket's last sample, after the touchdown) and
    counts as the largest violation, never as a soft landing."""
    check = flight.check_flight(each_branch(load_reply(), 0, landing_vertical_ms=bad), requirement_with_landing(6.0))
    assert rule_sizes(check) == {"landing_hard_0": ladder.MAX_VIOLATION, "landing_prompt": ladder.MAX_VIOLATION}
    assert "unknown" in check.reasons[0] and "not a downward speed" in check.reasons[0]


def test_booster_landing_speed_that_is_not_downward_counts_as_unknown():
    check = flight.check_flight(each_branch(load_reply("two_stage"), 1, landing_vertical_ms=-30.0), NO_LIMIT)
    assert rule_sizes(check) == {"landing_unrecovered_1": ladder.MAX_VIOLATION}
