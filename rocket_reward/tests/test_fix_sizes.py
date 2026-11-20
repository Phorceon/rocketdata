"""Absurd sizes and positions (added 2026-11-19 after the numeric review).

Stage 5 (fit.py): an inside part is judged by how far it lies outside its
airframe, as a distance along the axis, never by how much of its own length
is uncovered. Before, a 6 mm engine block 63 m ahead of the nose measured
6 mm and passed. Every inside part type is judged, also in pods.

Stage 4 (limit_checks.py): a written radius of 0 is not "auto"; packed
lengths, fin roots, rail button sizes, counts, delays, positions, angles and
the density of a mass component all have bounds set from the references.

No Java is needed: stage 5 tests edit a recorded reply, stage 4 tests edit
the first reference design.
"""
from __future__ import annotations

import copy

import pytest

from replies import load_reply
from rocket_reward import fit
from rocket_reward import limit_checks as LC
from rocket_reward import limits as L
from rocket_reward import tree as T
from rocket_reward.tree import find_all as nodes
from rocket_reward.tree import make_node

from test_fit import fit_check, fit_outcome, fit_part, fit_rules
from test_limits import _local_flown_motors, check, fails_with, gold, set_field  # noqa: F401 (fixtures)

# single_stage reply: nose cone 0 to 0.533 m (mass component 2 inside), body
# tubes to 2.565 m (the tail); tube coupler 6 with bulkheads 7 and 8; parachute
# 11; centering rings 13 and 14 and motor tubes 15 and 16 in body tube 10.
TAIL_M = 2.5654


# ------------------------------------------------------------------ stage 5: distance outside the airframe

@pytest.mark.parametrize("index, rule", [(14, "ring_outside_airframe"), (7, "ring_outside_airframe"),
                                         (6, "ring_outside_airframe"), (2, "part_outside_airframe"),
                                         (11, "part_outside_airframe"), (15, "motor_tube_outside_airframe")])
@pytest.mark.parametrize("x0", [-63.5, -470.0, 110.0])
def test_a_thin_part_far_away_measures_its_distance_not_its_length(index, rule, x0):
    reply = load_reply("single_stage")
    part = fit_part(reply, index)
    part["x0_m"] = x0
    check = fit_check(reply)
    assert fit_outcome(check) == "fail"
    far = -x0 if x0 < 0 else x0 + (part["length_m"] or 0.0) - TAIL_M
    assert check.info["measures"][rule] == pytest.approx(far, rel=1e-6)
    assert any(f"{abs(far):.4g} m" in r for r in check.reasons), check.reasons


@pytest.mark.parametrize("outside, outcome", [(0.04, "pass"), (0.06, "defect"), (0.3, "fail")])
def test_packed_parts_behind_the_tail(outside, outcome):
    # the largest sound reference is a tail weight 28.6 mm behind the tail (V4-0179)
    reply = load_reply("single_stage")
    mass = fit_part(reply, 9)
    mass["parent"] = 10
    mass["x0_m"] = TAIL_M + outside - mass["length_m"]
    check = fit_check(reply)
    assert fit_outcome(check) == outcome
    assert check.info["measures"]["part_outside_airframe"] == pytest.approx(outside, abs=1e-6)


def test_a_point_mass_ahead_of_the_nose_fails():
    # a 12.7 kg mass component with no length, 1.48 m ahead of the nose tip, used to pass
    reply = load_reply("single_stage")
    mass = fit_part(reply, 2)
    mass["x0_m"], mass["length_m"] = -1.478, 0.0
    check = fit_check(reply)
    assert fit_outcome(check) == "fail"
    assert "1.478 m ahead of the front of the airframe" in " ".join(check.reasons)


def test_moving_a_part_further_out_never_scores_better():
    credits = []
    for x0 in (-0.01, -0.03, -0.1, -1.0, -10.0, -100.0):
        reply = load_reply("single_stage")
        fit_part(reply, 13)["x0_m"] = x0
        credits.append(fit_check(reply).credit)
    assert credits == sorted(credits, reverse=True)


def test_a_ring_on_a_motor_tube_that_sticks_out_counts_as_inside():
    # V4-0183: motor retainer rings sit on a motor tube 22 mm behind the tail
    reply = load_reply("single_stage")
    tube = fit_part(reply, 15)
    tube["x0_m"] = TAIL_M + 0.03 - tube["length_m"]
    ring = fit_part(reply, 14)
    ring["parent"] = 15
    ring["x0_m"] = TAIL_M + 0.03 - ring["length_m"]
    check = fit_check(reply)
    assert check.info["measures"]["ring_outside_airframe"] == pytest.approx(0.0, abs=1e-6)
    assert "motor_tube_outside_airframe" in check.info["measures"]
    assert check.passed and check.defects == []
    # the same ring on the body tube (not on the motor tube) is 30 mm outside
    ring["parent"] = 10
    assert fit_check(reply).info["measures"]["ring_outside_airframe"] == pytest.approx(0.03, abs=1e-6)


def test_parts_in_a_pod_are_judged_against_the_pod():
    reply = load_reply("two_stage")
    assert fit_check(reply).passed
    ring = fit_part(reply, 9)          # a ring in the booster pod's body tube
    ring["x0_m"] = -50.0
    check = fit_check(reply)
    assert fit_outcome(check) == "fail" and "its pod's shell" in " ".join(check.reasons)


def test_a_pod_without_a_shell_falls_back_to_the_main_airframe():
    reply = load_reply("two_stage")
    for c in reply["components"]:
        if c["index"] in (5, 6):   # the pod's nose cone and body tube are no shell any more
            c["type"] = "LaunchLug"
    assert "ring_outside_airframe (defect)" not in fit_rules(fit_check(reply))
    fit_part(reply, 9)["x0_m"] = 50.0
    check = fit_check(reply)
    assert "the airframe" in " ".join(check.reasons) and not check.passed


def test_outside_distance_in_a_gap_and_at_the_ends():
    union = [(0.0, 1.0), (2.0, 3.0)]
    assert fit._outside_distance(0.2, 0.3, union)[0] == 0.0
    d, where = fit._outside_distance(1.3, 1.4, union)       # in the gap: 0.4 m to the nearer stretch
    assert d == pytest.approx(0.4) and where == "outside"
    d, where = fit._outside_distance(-5.0, -4.99, union)
    assert d == pytest.approx(5.0) and where == "ahead of the front of"
    d, where = fit._outside_distance(3.5, 3.502, union)
    assert d == pytest.approx(0.502) and where == "behind the back of"


# ------------------------------------------------------------------ stage 4: helpers

def add_part(root, part):
    holder = T.child(nodes(root, "bodytube")[0], "subcomponents")
    holder["subcomponents"]["children"].append(part)
    return root


def button(**fields):
    kids = [{"outerdiameter": {"value": 0.0097}}, {"innerdiameter": {"value": 0.008}},
            {"height": {"value": 0.0097}}, {"baseheight": {"value": 0.002}}, {"flangeheight": {"value": 0.002}}]
    kids += [{k: {"value": v}} for k, v in fields.items()]
    return {"railbutton": {"children": kids}}


def test_the_reference_design_passes(gold):
    assert check(gold).passed


# ------------------------------------------------------------------ stage 4: zero is not "auto"

def test_nose_cone_base_radius_zero_is_a_rocket_with_no_width(gold):
    fails_with(set_field(copy.deepcopy(gold), "nosecone", "aftradius", 0.0), "aftradius is 0", "auto")
    fails_with(set_field(copy.deepcopy(gold), "nosecone", "aftradius", 0.0005), "aftradius", "1 mm")
    for auto in ("auto", "auto 0.05"):
        assert check(set_field(copy.deepcopy(gold), "nosecone", "aftradius", auto)).passed


def test_a_pointed_transition_end_is_allowed(gold):
    tr = {"transition": {"children": [{"length": {"value": 0.1}}, {"foreradius": {"value": 0.0}},
                                      {"aftradius": {"value": 0.05}}, {"thickness": {"value": 0.002}}]}}
    stage = next(s for s in nodes(gold, "stage") if T.child(s, "subcomponents") is not None)
    T.child(stage, "subcomponents")["subcomponents"]["children"].append(tr)
    assert not any("transition" in r for r in check(gold).reasons)


# ------------------------------------------------------------------ stage 4: recovery

@pytest.mark.parametrize("tag", ["parachute", "masscomponent"])
def test_packed_length(gold, tag):
    fails_with(set_field(copy.deepcopy(gold), tag, "packedlength", 25.0), "packedlength", "25 m", "1.5 m")
    assert check(set_field(copy.deepcopy(gold), tag, "packedlength", 1.0)).passed
    worse = [check(set_field(copy.deepcopy(gold), tag, "packedlength", x)).credit for x in (2.0, 4.0, 25.0, 1e308)]
    assert worse == sorted(worse, reverse=True)


@pytest.mark.parametrize("value, ok", [(8, True), (24, True), (-6, False), (0, False), (2.5, False), (100, False)])
def test_line_count(gold, value, ok):
    r = check(set_field(copy.deepcopy(gold), "parachute", "linecount", value))
    assert r.passed == ok, r.reasons
    if not ok:
        assert "linecount" in " ".join(r.reasons)


@pytest.mark.parametrize("field, value, ok", [
    ("deploydelay", 1.0, True), ("deploydelay", 1e308, False), ("deploydelay", -1.0, False),
    ("deployaltitude", 300.0, True), ("deployaltitude", 1e6, False), ("deployaltitude", -5.0, False),
    ("linelength", 1.0, True), ("linelength", 50.0, False)])
def test_recovery_settings(gold, field, value, ok):
    r = check(set_field(copy.deepcopy(gold), "parachute", field, value))
    assert r.passed == ok, r.reasons


# ------------------------------------------------------------------ stage 4: fins

def test_fin_root_chord(gold):
    fails_with(set_field(copy.deepcopy(gold), "trapezoidfinset", "rootchord", 0.0), "rootchord is 0")
    fails_with(set_field(copy.deepcopy(gold), "trapezoidfinset", "rootchord", 5.08e-05), "rootchord", "2 mm")
    fails_with(set_field(copy.deepcopy(gold), "trapezoidfinset", "height", 0.0), "height is 0")


def test_a_wide_fin_on_a_short_root(gold):
    d = set_field(set_field(copy.deepcopy(gold), "trapezoidfinset", "rootchord", 0.02),
                  "trapezoidfinset", "tipchord", 0.2)
    fails_with(d, "tip chord", "10 times its root chord")
    d = set_field(set_field(copy.deepcopy(gold), "trapezoidfinset", "rootchord", 0.1),
                  "trapezoidfinset", "tipchord", 0.11)
    assert check(d).passed


# ------------------------------------------------------------------ stage 4: rail buttons and counts

@pytest.mark.parametrize("field", ["baseheight", "flangeheight", "innerdiameter", "outerdiameter", "screwheight"])
@pytest.mark.parametrize("value", [1e308, 2.0, -0.002])
def test_rail_button_sizes(gold, field, value):
    fails_with(add_part(copy.deepcopy(gold), button(**{field: value})), "railbutton #1", field)


def test_a_sound_rail_button_passes(gold):
    assert check(add_part(copy.deepcopy(gold), button(screwheight=0.0))).passed


@pytest.mark.parametrize("value", [-2, 0, 1.5])
def test_instance_count_is_a_whole_number_of_at_least_one(gold, value):
    fails_with(add_part(copy.deepcopy(gold), button(instancecount=value)), "instancecount")


# ------------------------------------------------------------------ stage 4: positions and angles

@pytest.mark.parametrize("field, value, ok", [
    ("position", -4.0, True), ("position", -63.5, False), ("axialoffset", 470.0, False),
    ("radialposition", 0.05, True), ("radialposition", 2.0, False),
    ("radialdirection", -150.0, True), ("radialdirection", 1e308, False)])
def test_positions_and_angles(gold, field, value, ok):
    r = check(set_field(copy.deepcopy(gold), "centeringring", field, value))
    assert r.passed == ok, r.reasons
    if not ok:
        assert "either way" in " ".join(r.reasons)


# ------------------------------------------------------------------ stage 4: mass components

def test_a_heavy_weight_the_size_of_a_coin(gold):
    coin = {"masscomponent": {"children": [{"mass": {"value": 20.0}}, {"packedlength": {"value": 0.002}},
                                           {"packedradius": {"value": 0.0125}}]}}
    fails_with(add_part(copy.deepcopy(gold), coin), "masscomponent #3", "kg/m3")
    real = {"masscomponent": {"children": [{"mass": {"value": 1.0}}, {"packedlength": {"value": 0.1}},
                                           {"packedradius": {"value": 0.02}}]}}
    assert check(add_part(copy.deepcopy(gold), real)).passed
    # a point mass (no size) is not judged by density
    point = {"masscomponent": {"children": [{"mass": {"value": 5.0}}, {"packedlength": {"value": 0.0}},
                                            {"packedradius": {"value": 0.0}}]}}
    assert check(add_part(copy.deepcopy(gold), point)).passed


# ------------------------------------------------------------------ stage 4: motor mounts

@pytest.mark.parametrize("tag, value, ok", [("ignitiondelay", 3.0, True), ("ignitiondelay", 1e308, False),
                                            ("ignitiondelay", -1.0, False), ("overhang", 0.02, True),
                                            ("overhang", -100.0, False)])
def test_motor_mount_settings(gold, tag, value, ok):
    mount = nodes(gold, "motormount")[0]
    kids = mount["motormount"].setdefault("children", [])
    kids[:] = [c for c in kids if T.tag_of(c) != tag] + [make_node(tag, value)]
    assert check(gold).passed == ok


@pytest.mark.parametrize("value, ok", [(14.0, True), (1e308, False), (-2.0, False)])
def test_motor_ejection_delay(gold, value, ok):
    motor = nodes(gold, "motor")[0]
    kids = motor["motor"].setdefault("children", [])
    kids[:] = [c for c in kids if T.tag_of(c) != "delay"] + [make_node("delay", value)]
    assert check(gold).passed == ok


def test_new_limits_clear_the_reference_extremes():
    # largest sound reference values (overrides stripped), each well inside its limit
    assert L.PACKED_LENGTH_MAX_M >= 2 * 0.70
    assert L.POSITION_MAX_M >= 1.9 * 2.5876
    assert L.MASS_COMPONENT_DENSITY_MAX_KG_M3 >= 2 * 462025
    assert L.PACKED_OUTSIDE_AIRFRAME_MAX_M >= 1.7 * 0.028575
    assert L.RING_OUTSIDE_AIRFRAME_MAX_M >= 1.9 * 0.01016
    assert L.FIN_ROOT_CHORD_MIN_M < 0.003 and L.SHELL_RADIUS_MIN_M < 0.0023749


# ------------------------------------------------------------------ later additions from the mutation runs

def test_a_tail_closed_to_a_point_fails():
    reply = load_reply("single_stage")
    assert "tail_radius_per_motor" in fit_check(reply).info["measures"]
    fit_part(reply, 10)["outer_radius_aft_m"] = 0.0
    check = fit_check(reply)
    assert fit_outcome(check) == "fail" and "open the tail" in " ".join(check.reasons)


@pytest.mark.parametrize("value, ok", [("auto 0.0125", True), ("auto -0.0125", False), ("auto 0.0", False),
                                       ("auto 5.0", False)])
def test_the_number_after_auto_is_judged(gold, value, ok):
    assert check(set_field(copy.deepcopy(gold), "bodytube", "radius", value)).passed == ok


def test_separation_settings_in_their_configuration(gold):
    stage = next(s for s in nodes(gold, "stage") if T.child(s, "subcomponents") is not None)
    conf = make_node("separationconfiguration", children=[make_node("separationdelay", -0.5)])
    stage["stage"]["children"].append(conf)
    fails_with(gold, "separationdelay", "negative")


def test_a_rail_button_beyond_the_tail_fails():
    reply = load_reply("two_stage")
    button = fit_part(reply, 16)
    assert fit_check(reply).passed
    button["x0_m"] = 2.2      # about 1 m behind the 1.143 m long rocket
    check = fit_check(reply)
    assert fit_outcome(check) == "fail" and "onto a body tube" in " ".join(check.reasons)
