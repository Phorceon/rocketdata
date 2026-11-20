"""The second round of fixes of 2026-11-19 (after three more attacks on the fixed reward),
and the third round of the same day (after the attack on the second; "round 3" below).

Stage 5 (fit.py), judged on OpenRocket's own placement of the parts:
  * pod_outside_airframe: at most limits.POD_OVERHANG_MAX_FRACTION of a pod's
    or side booster's own shell length reaches ahead of the front or behind
    the back of the main-body shells of the stage that holds it (a weighted pod
    far ahead of the nose is nose weight on a stick; a booster's pod beside the
    stage above drops away from the part it touches; a strap-on booster that
    ends a little below the core is sound). A share since round 3; round 2
    measured a distance;
  * pod_in_pod (round 3): a pod or booster set inside another one fails;
  * pod_inside_body and pod_detached: a pod sits on the outside of the body
    tube that holds it, neither sunk into it nor far from it (they need the
    helper's "axis_offset_m", helper version 4, and are skipped without it);
  * pod_motor_one_sided: a pod or booster that holds a motor has two copies or more;
  * a motor in a pod is judged against that pod's own shells (motor_ahead_of_tail,
    tail_closed; tests/test_fit.py has the booster case);
  * part_ahead_of_stage: an inside part of a lower stage does not lie ahead of
    its own stage's shells (a booster's weight in the sustainer's nose); since
    round 3 a ring, bulkhead or engine block counts from the front of the motor
    tube or tube coupler that holds it;
  * slenderness: length over the body's width (fit._body_width: the largest
    diameter that at least limits.SLENDERNESS_WIDTH_SHARE of the main body's
    length has; round 3) at most limits.SLENDERNESS_MAX (60 since round 3).
Stage 6 (flight.py):
  * opens_late_<section>: the last recovery opening of a section comes at least
    limits.RECOVERY_OPEN_BEFORE_LANDING_MIN_S before it lands, in every flight;
  * a device set to open at a fixed altitude opens at limits.DEPLOY_ALTITUDE_MIN_M
    or higher (info["low_opening_violations"]).

Every test edits a recorded reply (tests/replies.py), except the last one, which
needs Java: the real helper reports "axis_offset_m".
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path

import pytest

from rocket_reward import fit, flight, ladder
from rocket_reward import limits as L
from rocket_reward.records import Requirements, Target

from replies import each_branch, load_reply
from test_fit import fit_check, fit_outcome, fit_part, fit_root, fit_rules, fit_shift_booster

NO_LIMIT = Requirements(id="t", apogee_m=Target(500.0, "about"), wind_ms=2.0)

# single_stage: nose cone 1 (0 to 0.533 m, mass component 2 inside), body tubes 3, 5
# (1.2954 to 1.3462 m: tube coupler 6 with bulkheads 7 and 8, mass component 9) and
# 10 (1.3462 m to the tail at 2.5654 m: parachute 11, rings 13 and 14, motor tubes 15 and 16).
# two_stage: core body tube 3 (radius 28.7 mm), booster set 4 (two copies, 0.97155 m to the
# tail at 1.143 m) with nose cone 5 and body tube 6 (radius 16.8 mm), motor tube 11 inside.
TAIL_M = 2.5654
STAGE_FRONT_M = 1.3462          # front of body tube 10
CORE_RADIUS_M = 0.028702
POD_RADIUS_M = 0.0168275
POD_FRONT_M = 0.97155
POD_BACK_M = 1.143


def outcome_and_rule(check, rule):
    """(pass / defect / fail, the finding of `rule` or None)."""
    found = next((f for f in check.info["findings"] if f["rule"] == rule), None)
    return fit_outcome(check), found


def all_text(check) -> str:
    return " ".join(check.reasons + check.defects)


# ------------------------------------------------------------------ stage 5: pods alongside the body

POD_LENGTH_M = POD_BACK_M - POD_FRONT_M     # 0.17145 m: the booster's nose cone and body tube


@pytest.mark.parametrize("where", ["ahead", "behind"])
@pytest.mark.parametrize("share, outcome", [(0.0, "pass"), (0.2, "pass"), (0.33, "pass"), (0.4, "defect"),
                                            (0.9, "fail")])
def test_pod_reaches_past_the_main_body(where, share, outcome):
    """The booster moved so that `share` of its own 0.171 m length lies ahead of the nose tip or behind
    the tail. A share, not a distance (round 3): V4-0107's boosters 0.08 m aft (47%) are a defect."""
    outside = share * POD_LENGTH_M
    dx = -(POD_FRONT_M + outside) if where == "ahead" else outside
    check = fit_check(fit_shift_booster(load_reply("two_stage"), dx))
    got, found = outcome_and_rule(check, "pod_outside_airframe")
    assert got == outcome
    assert check.info["measures"]["pod_outside_airframe"] == pytest.approx(share, abs=1e-6)
    if outcome == "pass":
        assert found is None
        return
    assert found["defect"] == (outcome == "defect")
    assert found["size"] == pytest.approx(math.log2(share / L.POD_OVERHANG_MAX_FRACTION), abs=1e-4)
    assert found["limit"] == L.POD_OVERHANG_MAX_FRACTION
    side = "ahead of the front of" if where == "ahead" else "behind the back of"
    text = all_text(check)
    assert "booster set 'Booster Set' is 0.1715 m long and reaches" in text, text
    assert f"{side} the main body, {share:.0%} of its own length; at most 33%" in text, text


@pytest.mark.parametrize("gap", [0.0, 1.0, 3.0])
def test_pod_wholly_ahead_of_the_nose_fails(gap):
    """A pod whose back end is `gap` m ahead of the nose tip: more than its whole length is outside."""
    check = fit_check(fit_shift_booster(load_reply("two_stage"), -(POD_BACK_M + gap)))
    got, found = outcome_and_rule(check, "pod_outside_airframe")
    share = (POD_LENGTH_M + gap) / POD_LENGTH_M
    assert got == "fail" and not found["defect"]
    assert check.info["measures"]["pod_outside_airframe"] == pytest.approx(share, abs=1e-6)
    assert share >= 1.0
    assert "ahead of the front of the main body" in check.reasons[0]


def test_pod_share_limit_is_the_ladder_boundary():
    """Up to about 0.47 of the pod's length is a defect (size under ladder.FIT_DEFECT_BELOW), more fails."""
    edge = L.POD_OVERHANG_MAX_FRACTION * 2 ** ladder.FIT_DEFECT_BELOW
    for share, outcome in ((edge - 0.005, "defect"), (edge + 0.005, "fail")):
        check = fit_check(fit_shift_booster(load_reply("two_stage"), share * POD_LENGTH_M))
        assert outcome_and_rule(check, "pod_outside_airframe")[0] == outcome, share


@pytest.mark.parametrize("empty", ["no shells", "zero length"])
def test_pod_without_a_shell_length_is_not_judged(empty):
    """A pod with no shells, or whose shells have no length, has no share to measure."""
    reply = fit_shift_booster(load_reply("two_stage"), -3.0)      # far ahead of the nose if it were judged
    if empty == "no shells":
        reply["components"] = [c for c in reply["components"] if c["index"] not in range(5, 13)]
    else:
        for i in (5, 6):
            fit_part(reply, i)["length_m"] = 0.0
        fit_part(reply, 6)["x0_m"] = fit_part(reply, 5)["x0_m"]
    check = fit_check(reply)
    assert "pod_outside_airframe" not in check.info["measures"]
    assert "pod_outside_airframe" not in {f["rule"] for f in check.info["findings"]}


def stage_split_with_pod(holder: int, front: float, length: float = 0.4) -> dict:
    """single_stage cut into two stages (body tube 10 is stage 20), with a two-copy pod (a 50 mm nose
    cone and a tube, 30 mm in radius, `length` m in all) held by body tube `holder`, its front at `front`."""
    reply = single_stage_split((20, [10]))
    reply["components"] += [
        {"type": "PodSet", "index": 40, "parent": holder, "name": "Side Pods", "x0_m": front, "length_m": length,
         "active": True, "instances": 2},
        {"type": "NoseCone", "index": 41, "parent": 40, "name": "Pod Nose", "x0_m": front, "length_m": 0.05,
         "active": True, "instances": 2, "outer_radius_fore_m": 0.0, "outer_radius_aft_m": 0.03},
        {"type": "BodyTube", "index": 42, "parent": 40, "name": "Pod Tube", "x0_m": front + 0.05,
         "length_m": length - 0.05, "active": True, "instances": 2, "outer_radius_fore_m": 0.03,
         "outer_radius_aft_m": 0.03, "inner_radius_m": 0.029}]
    return reply


def test_booster_pod_beside_the_stage_above_fails():
    """Round 3: the attackers' "booster pods by the sustainer's nose" (V4-0050, -0051, -0063 scored
    0.965-0.986). The pod lies inside the whole rocket's span, but beside the stage above the one
    that holds it, so it would drop away from the part it touches."""
    front = 0.6                                         # beside body tube 3 (0.533 to 1.295 m), stage 0
    assert 0.0 < front and front + 0.4 < TAIL_M         # inside the whole rocket
    check = fit_check(stage_split_with_pod(10, front))  # held by stage 20 (front at 1.346 m)
    got, found = outcome_and_rule(check, "pod_outside_airframe")
    share = (STAGE_FRONT_M - front) / 0.4
    assert got == "fail" and not found["defect"]
    assert check.info["measures"]["pod_outside_airframe"] == pytest.approx(share, abs=1e-6)
    assert "pod set 'Side Pods' is 0.4 m long and reaches 0.7462 m ahead of the front of the stage that " \
           "holds it" in check.reasons[0], check.reasons
    # the same pod held by the stage it sits beside, or beside its own lower stage: sound
    for holder, at in ((3, front), (10, STAGE_FRONT_M + 0.2)):
        check = fit_check(stage_split_with_pod(holder, at))
        assert check.passed and check.defects == [], (holder, check.reasons, check.defects)
        assert check.info["measures"]["pod_outside_airframe"] == 0.0


def test_pod_in_a_pod_fails():
    """Round 3: two motor pods nested inside the booster pods (they sat inside the main body and fired
    into the airframe: V4-0099 with fins x0.6 scored 0.7394 against 0.594 honest); a yes/no rule."""
    reply = load_reply("two_stage")
    assert "pod_in_pod" not in {f["rule"] for f in fit_check(reply).info["findings"]}   # a pod on the main body
    reply["components"] += [
        {"type": "PodSet", "index": 50, "parent": 6, "name": "Inner Pods", "x0_m": 1.05, "length_m": 0.06,
         "active": True, "instances": 2},
        {"type": "NoseCone", "index": 51, "parent": 50, "name": "Inner Nose", "x0_m": 1.05, "length_m": 0.01,
         "active": True, "instances": 2, "outer_radius_fore_m": 0.0, "outer_radius_aft_m": 0.005},
        {"type": "BodyTube", "index": 52, "parent": 50, "name": "Inner Tube", "x0_m": 1.06, "length_m": 0.05,
         "active": True, "instances": 2, "outer_radius_fore_m": 0.005, "outer_radius_aft_m": 0.005,
         "inner_radius_m": 0.0045}]
    check = fit_check(reply)
    assert fit_outcome(check) == "fail"
    assert fit_rules(check) == {"pod_in_pod"}
    assert check.info["failure_sizes"] == [ladder.YES_NO_VIOLATION]
    assert check.reasons == ["pod set 'Inner Pods' is inside another pod or booster set; put every pod and "
                             "side booster on the main body"]


def two_stage_with_axis(axis: float) -> dict:
    """two_stage with the booster set's axis `axis` metres from the centre line."""
    reply = load_reply("two_stage")
    fit_part(reply, 4)["axis_offset_m"] = axis
    return reply


@pytest.mark.parametrize("sunk, outcome", [(0.0, "pass"), (0.4, "pass"), (0.6, "defect"), (1.0, "fail"),
                                           (1.0 + CORE_RADIUS_M / POD_RADIUS_M, "fail")])
def test_pod_sunk_into_the_body(sunk, outcome):
    # 0: flush on the outside (every sound reference); 1: the axis on the body's surface;
    # the last: the axis on the centre line (V4-0227, and a motor tube wrapped in a pod)
    axis = CORE_RADIUS_M + POD_RADIUS_M * (1.0 - sunk)
    check = fit_check(two_stage_with_axis(axis))
    got, found = outcome_and_rule(check, "pod_inside_body")
    assert got == outcome
    assert check.info["measures"]["pod_inside_body"] == pytest.approx(sunk, abs=1e-6)
    if outcome == "pass":
        assert found is None and check.passed and check.defects == []
        return
    assert found["defect"] == (outcome == "defect")
    assert found["size"] == pytest.approx(math.log2(sunk / L.POD_SUNK_MAX_FRACTION), abs=1e-4)
    text = all_text(check)
    assert f"{min(sunk, 1.0):.0%} of the pod's 16.83 mm radius lies inside that body" in text, text
    assert ("(its axis is inside the body)" in text) == (sunk > 1.0)


def test_pod_on_the_centre_line_fails():
    check = fit_check(two_stage_with_axis(0.0))
    assert not check.passed
    assert "the axis of booster set 'Booster Set' is 0 mm from the centre line" in check.reasons[0]


@pytest.mark.parametrize("gap, outcome", [(0.0, "pass"), (0.0508, "pass"), (0.13, "defect"), (0.2, "fail"),
                                          (1.0, "fail")])
def test_pod_detached_from_the_body(gap, outcome):
    # V4-0112's pods stand 50.8 mm off the body; the others sit against it
    check = fit_check(two_stage_with_axis(CORE_RADIUS_M + POD_RADIUS_M + gap))
    got, found = outcome_and_rule(check, "pod_detached")
    assert got == outcome
    assert check.info["measures"]["pod_detached"] == pytest.approx(gap, abs=1e-9)
    assert check.info["measures"]["pod_inside_body"] <= 0.0
    if outcome == "pass":
        assert found is None
        return
    assert found["defect"] == (outcome == "defect")
    assert f"booster set 'Booster Set' sits {gap * 1000:.4g} mm clear of the body beside it" in all_text(check)


def wider_tube_beside_the_pod(radius: float) -> dict:
    """two_stage with one more main-body tube of `radius` alongside the booster set. The booster
    set is still held by core tube 3 (28.7 mm) and sits flush on it."""
    reply = two_stage_with_axis(CORE_RADIUS_M + POD_RADIUS_M)
    core = fit_part(reply, 3)
    wide = dict(core, index=max(c["index"] for c in reply["components"]) + 1, name="Wide tube",
                x0_m=POD_FRONT_M - 0.05, length_m=0.3, outer_radius_fore_m=radius, outer_radius_aft_m=radius,
                inner_radius_m=radius - 0.001, motor=None)
    reply["components"].append(wide)
    return reply


def test_pod_is_judged_against_the_body_beside_it_not_only_its_holder():
    # held by a narrow tube but lying inside a wider part of the same rocket (2026-11-19, last check)
    check = fit_check(wider_tube_beside_the_pod(0.080))
    got, found = outcome_and_rule(check, "pod_inside_body")
    assert got == "fail" and found is not None and not found["defect"]
    sunk = (POD_RADIUS_M - (CORE_RADIUS_M + POD_RADIUS_M - 0.080)) / POD_RADIUS_M
    assert check.info["measures"]["pod_inside_body"] == pytest.approx(sunk, abs=1e-6)
    assert "the body beside it is 80 mm in radius" in all_text(check), all_text(check)
    # a tube no wider than the holder changes nothing
    same = fit_check(wider_tube_beside_the_pod(CORE_RADIUS_M))
    assert same.info["measures"]["pod_inside_body"] == pytest.approx(0.0, abs=1e-6)
    assert outcome_and_rule(same, "pod_inside_body")[1] is None


def test_radius_beside_reads_a_transition_along_its_slope():
    reply = load_reply("two_stage")
    core = fit_part(reply, 3)
    cone = dict(core, type="Transition", x0_m=10.0, length_m=1.0, outer_radius_fore_m=0.02,
                outer_radius_aft_m=0.06)
    parts = fit._Parts([cone])
    assert fit._radius_beside(parts, 10.25, 10.5) == pytest.approx(0.04)
    assert fit._radius_beside(parts, 9.0, 10.5) == pytest.approx(0.04)     # only the part inside counts
    assert fit._radius_beside(parts, 10.5, 12.0) == pytest.approx(0.06)
    assert fit._radius_beside(parts, 11.5, 12.0) is None                    # beside nothing
    assert fit._radius_beside(fit._Parts([dict(cone, length_m=0.0)]), 9.0, 11.0) == pytest.approx(0.06)


def test_pod_rules_that_need_the_axis_are_skipped_on_older_replies():
    """The stored replies come from helper version 3, which has no "axis_offset_m"."""
    reply = load_reply("two_stage")
    assert all("axis_offset_m" not in c for c in reply["components"])
    check = fit_check(reply)
    assert check.passed and check.defects == []
    assert "pod_inside_body" not in check.info["measures"] and "pod_detached" not in check.info["measures"]
    assert check.info["measures"]["pod_outside_airframe"] == 0.0   # judged on positions alone
    fit_part(reply, 4)["axis_offset_m"] = None                     # unknown counts as not reported
    assert "pod_inside_body" not in fit_check(reply).info["measures"]


@pytest.mark.parametrize("copies, motor, outcome", [(2, True, "pass"), (1, True, "fail"), (1, False, "pass"),
                                                    (3, True, "pass")])
def test_pod_with_a_motor_needs_two_copies(copies, motor, outcome):
    reply = load_reply("two_stage")
    fit_part(reply, 4)["instances"] = copies
    if not motor:
        fit_part(reply, 11)["motor"] = None
    check = fit_check(reply, fit_root(2 if motor else 1))
    assert fit_outcome(check) == outcome
    if outcome == "fail":
        assert fit_rules(check) == {"pod_motor_one_sided"}
        assert check.info["failure_sizes"] == [ladder.YES_NO_VIOLATION]
        assert "booster set 'Booster Set' holds a motor but has only one copy" in check.reasons[0]
    else:
        assert "pod_motor_one_sided" not in {f["rule"] for f in check.info["findings"]}


@pytest.mark.parametrize("gap, outcome", [(0.0, "pass"), (0.149, "pass"), (0.18, "defect"), (0.4, "fail")])
def test_motor_in_a_pod_is_judged_against_the_pod_shells(gap, outcome):
    """The booster's motor `gap` m ahead of its own booster's tail, while the core's tail is 0.3 m
    further back (the booster moved forward): only the booster's shells count. The case where the
    pods were skipped, and tail_closed on the booster's last shell, are in tests/test_fit.py."""
    reply = fit_shift_booster(load_reply("two_stage"), -0.3)
    tail = fit_part(reply, 6)["x0_m"] + fit_part(reply, 6)["length_m"]
    motor = fit_part(reply, 11)["motor"]
    motor["x0_m"] = tail - motor["length_m"] - gap
    check = fit_check(reply)
    assert fit_outcome(check) == outcome
    assert check.info["measures"]["motor_ahead_of_tail"] == pytest.approx(gap, abs=1e-9)
    if outcome != "pass":
        assert "motor 'E12' in inner tube 'Inner Tube'" in all_text(check)
        assert "the airframe of booster set 'Booster Set'" in all_text(check)


# ------------------------------------------------------------------ stage 5: a part in the stage above

def single_stage_split(*stages: tuple[int, list[int]]) -> dict:
    """single_stage cut into stages: each (new stage index, the body tubes moved into it).
    The coupler (6) and its bulkheads stay in the top stage, on body tube 3."""
    reply = load_reply("single_stage")
    fit_part(reply, 6)["parent"] = 3
    for index, tubes in stages:
        first = min(fit_part(reply, t)["x0_m"] for t in tubes)
        reply["components"].append({"type": "AxialStage", "index": index, "parent": -1, "name": f"Stage {index}",
                                    "x0_m": first, "length_m": 0.0, "active": True, "instances": 1})
        for t in tubes:
            fit_part(reply, t)["parent"] = index
    return reply


def test_split_rocket_is_sound():
    check = fit_check(single_stage_split((20, [10])))
    assert check.passed and check.defects == []
    assert check.info["measures"]["part_ahead_of_stage"] == 0.0


@pytest.mark.parametrize("ahead, outcome", [(0.0, "pass"), (0.04, "pass"), (0.06, "defect"),
                                            (STAGE_FRONT_M - 0.6, "fail")])
def test_booster_weight_inside_the_stage_above(ahead, outcome):
    # V4-0051: a weight owned by the booster, placed in the sustainer's nose, scored 0.986
    reply = single_stage_split((20, [10]))
    mass = fit_part(reply, 9)
    mass["parent"] = 10
    mass["x0_m"] = STAGE_FRONT_M - ahead
    check = fit_check(reply)
    got, found = outcome_and_rule(check, "part_ahead_of_stage")
    assert got == outcome
    assert check.info["measures"]["part_ahead_of_stage"] == pytest.approx(ahead, abs=1e-6)
    assert check.info["measures"]["part_outside_airframe"] == 0.0   # it is inside the airframe
    if outcome != "pass":
        assert found["defect"] == (outcome == "defect")
        assert "mass component 'Mass Component' belongs to stage 'Stage 20' but lies" in all_text(check)
        assert "inside the stage above it" in all_text(check)


@pytest.mark.parametrize("reach, outcome", [(0.10, "pass"), (0.20, "pass"), (0.3, "fail")])
def test_coupler_reaching_into_the_stage_above(reach, outcome):
    # the joint between stages: V4-0063's coupler reaches 0.102 m, V4-0003's motor tubes 0.19 m
    reply = single_stage_split((20, [10]))
    for i in (7, 8):
        fit_part(reply, i)["parent"] = 5        # the bulkheads stay in the top stage
    coupler = fit_part(reply, 6)
    coupler["parent"] = 10
    coupler["x0_m"] = STAGE_FRONT_M - reach
    check = fit_check(reply)
    assert fit_outcome(check) == outcome
    assert check.info["measures"]["part_ahead_of_stage"] == pytest.approx(reach, abs=1e-6)
    if outcome == "fail":
        assert f"may reach at most {L.STAGE_JOINT_REACH_MAX_M:g} m ahead of its own stage" in check.reasons[0]


def test_ring_on_a_motor_tube_that_reaches_forward():
    """A ring sits on the motor tube that holds it; the tube reaches 0.15 m into the stage above."""
    reply = single_stage_split((20, [10]))
    tube = fit_part(reply, 15)
    tube["x0_m"] = STAGE_FRONT_M - 0.15
    tube["length_m"] = TAIL_M - tube["x0_m"]
    ring = fit_part(reply, 13)
    ring["parent"] = 15
    ring["x0_m"] = STAGE_FRONT_M - 0.146
    check = fit_check(reply)
    assert check.passed and check.defects == []
    assert check.info["measures"]["part_ahead_of_stage"] == pytest.approx(0.15, abs=1e-6)   # the tube itself
    # the same ring on the body tube instead: 0.146 m ahead of its stage, past the 0.02 m ring limit
    ring["parent"] = 10
    check = fit_check(reply)
    assert fit_outcome(check) == "fail" and "part_ahead_of_stage" in fit_rules(check)
    assert "centering ring 'Centering Ring' belongs to stage 'Stage 20'" in check.reasons[0]


def booster_coupler_with_bulkhead(bulkhead_parent: int) -> dict:
    """single_stage cut into two stages, the coupler (6) owned by the lower stage's body tube 10 and
    reaching 0.10 m into the stage above (as V4-0063's interstage coupler does), and bulkhead 7 at the
    coupler's front, held by `bulkhead_parent`. Bulkhead 8 stays in the coupler, inside its own stage."""
    reply = single_stage_split((20, [10]))
    coupler = fit_part(reply, 6)
    coupler["parent"] = 10
    coupler["x0_m"] = STAGE_FRONT_M - 0.10
    fit_part(reply, 8)["x0_m"] = STAGE_FRONT_M + 0.2
    bulkhead = fit_part(reply, 7)
    bulkhead["parent"] = bulkhead_parent
    bulkhead["x0_m"] = STAGE_FRONT_M - 0.10
    return reply


def test_bulkhead_counts_from_the_coupler_that_holds_it():
    """Round 3: a bulkhead capping a booster's coupler that reaches 0.10 m into the stage above passes
    (V4-0063: 0.9883); the same bulkhead held by the booster's body tube is a part of the booster lying
    0.10 m inside the stage above, past the 20 mm ring limit (V4-0063: 0.4241)."""
    check = fit_check(booster_coupler_with_bulkhead(6))
    assert check.passed and check.defects == [], (check.reasons, check.defects)
    assert check.info["measures"]["part_ahead_of_stage"] == pytest.approx(0.10, abs=1e-6)   # the coupler itself
    check = fit_check(booster_coupler_with_bulkhead(10))
    got, found = outcome_and_rule(check, "part_ahead_of_stage")
    assert got == "fail" and not found["defect"]
    assert found["size"] == pytest.approx(math.log2(0.10 / L.RING_OUTSIDE_AIRFRAME_MAX_M), abs=1e-4)
    assert fit_rules(check) == {"part_ahead_of_stage"}
    assert "bulkhead 'Bulkhead' belongs to stage 'Stage 20' but lies 100 mm ahead of the front of that stage's " \
           "airframe" in check.reasons[0], check.reasons
    assert "may reach at most 20 mm ahead of its own stage" in check.reasons[0]


def test_bulkhead_in_a_coupler_reaching_too_far_still_fails():
    """The coupler's own limit (limits.STAGE_JOINT_REACH_MAX_M) still holds: a coupler 0.3 m into the
    stage above fails with its bulkhead, which counts from that coupler's front."""
    reply = booster_coupler_with_bulkhead(6)
    for i in (6, 7):
        fit_part(reply, i)["x0_m"] = STAGE_FRONT_M - 0.3
    check = fit_check(reply)
    assert fit_outcome(check) == "fail" and fit_rules(check) == {"part_ahead_of_stage"}
    sizes = [f["size"] for f in check.info["findings"]]
    assert sizes == [pytest.approx(math.log2(0.3 / L.STAGE_JOINT_REACH_MAX_M), abs=1e-4)]   # the coupler only
    assert "tube coupler 'Tube Coupler' belongs to stage 'Stage 20'" in check.reasons[0]


def test_top_stage_and_single_stage_rockets_never_get_the_rule():
    reply = load_reply("single_stage")
    fit_part(reply, 2)["x0_m"] = -0.5                # the nose weight 0.5 m ahead of the tip
    check = fit_check(reply)
    assert "part_ahead_of_stage" not in check.info["measures"]
    assert "part_outside_airframe" in fit_rules(check)
    reply = single_stage_split((20, [10]))
    fit_part(reply, 2)["x0_m"] = -0.5                # a part of the top stage
    check = fit_check(reply)
    assert "part_outside_airframe" in fit_rules(check)
    assert "part_ahead_of_stage" not in {f["rule"] for f in check.info["findings"]}


def test_part_reaching_behind_its_stage_is_judged_on_the_whole_airframe_only():
    reply = single_stage_split((20, [5]), (21, [10]))
    assert fit_check(reply).passed
    fit_part(reply, 9)["x0_m"] = 1.8                 # stage 20's weight, inside stage 21's tube
    check = fit_check(reply)
    assert check.passed and check.defects == []
    assert check.info["measures"]["part_ahead_of_stage"] == 0.0
    assert check.info["measures"]["part_outside_airframe"] == 0.0
    fit_part(reply, 9)["x0_m"] = TAIL_M + 0.3        # behind the whole airframe: caught
    assert "part_outside_airframe" in fit_rules(fit_check(reply))


def test_stage_rule_ignores_launch_lugs_and_rail_buttons():
    """A rail button of the lower stage that sits along the stage above is not judged by stage."""
    reply = single_stage_split((20, [10]))
    reply["components"].append({"type": "RailButton", "index": 30, "parent": 10, "name": "Rail Button",
                                "x0_m": 1.0, "length_m": 0.0, "active": True, "instances": 2,
                                "outer_radius_fore_m": 0.00485, "outer_radius_aft_m": 0.00485})
    check = fit_check(reply)
    assert check.passed and check.defects == []
    assert check.info["measures"]["part_ahead_of_stage"] == 0.0
    assert check.info["measures"]["part_outside_airframe"] == 0.0


# ------------------------------------------------------------------ stage 5: slenderness

BODY_WIDTH_M = 2 * 0.0974344      # single_stage: the nose cone's base and every body tube
MAIN_SHELLS = (1, 3, 5, 10)        # single_stage's nose cone and body tubes, 2.565 m in all


@pytest.mark.parametrize("ratio, outcome", [(13.17, "pass"), (56.0, "pass"), (59.9, "pass"), (70.0, "defect"),
                                            (100.0, "fail"), (151.0, "fail")])
def test_slenderness(ratio, outcome):
    # the references reach 56.1 (V4-0050); up to about 85 is a defect (ladder.FIT_DEFECT_BELOW)
    reply = load_reply("single_stage")
    reply["rocket"]["length_m"] = ratio * BODY_WIDTH_M
    check = fit_check(reply)
    got, found = outcome_and_rule(check, "slenderness")
    assert got == outcome
    assert check.info["measures"]["slenderness"] == pytest.approx(ratio, rel=1e-6)
    if outcome == "pass":
        assert found is None
        return
    assert found["defect"] == (outcome == "defect")
    assert found["size"] == pytest.approx(math.log2(ratio / L.SLENDERNESS_MAX), abs=1e-4)
    assert f"its body is 194.9 mm across, {ratio:.0f} times as long as it is wide; the limit is 60 times" \
        in all_text(check), all_text(check)


def tail_transition(reply: dict, length: float, aft_radius: float) -> dict:
    """A transition `length` m long behind single_stage's tail, opening from the body's radius to `aft_radius`."""
    reply["components"].append({"type": "Transition", "index": 60, "parent": 0, "name": "Tail Flare",
                                "x0_m": TAIL_M, "length_m": length, "active": True, "instances": 1,
                                "outer_radius_fore_m": 0.0974344, "outer_radius_aft_m": aft_radius})
    return reply


def slenderness_of(reply: dict) -> float:
    return fit_check(reply).info["measures"]["slenderness"]


def test_thin_wide_disk_does_not_change_the_width():
    """Round 3: the attackers' 2 mm flared disk 2.5 times the body's width at the tail (round 2's
    ratio of V4-0050 stretched to 100 then measured 40). It is far less than 10% of the body's length."""
    reply = load_reply("single_stage")
    length = reply["rocket"]["length_m"] = 100.0 * BODY_WIDTH_M
    tail_transition(reply, 0.002, 2.5 * 0.0974344)
    reply["rocket"]["max_diameter_m"] = 5 * 0.0974344        # what OpenRocket reports: the disk
    assert fit._body_width(fit._Parts(reply["components"])) == pytest.approx(BODY_WIDTH_M, rel=1e-9)
    assert slenderness_of(reply) == pytest.approx(length / BODY_WIDTH_M, rel=1e-6)
    got, _ = outcome_and_rule(fit_check(reply), "slenderness")
    assert got == "fail"


@pytest.mark.parametrize("share, counts", [(0.09, False), (0.11, True), (0.5, True)])
def test_wide_section_counts_when_long_enough(share, counts):
    """A transition opening to 0.15 m radius, `share` of the main body's length long: it sets the
    width only when it covers at least limits.SLENDERNESS_WIDTH_SHARE of that length."""
    reply = load_reply("single_stage")
    body = sum(fit_part(reply, i)["length_m"] for i in MAIN_SHELLS)
    flare = share * body / (1.0 - share)                    # its share of the body with the flare in it
    tail_transition(reply, flare, 0.15)
    width = fit._body_width(fit._Parts(reply["components"]))
    assert width == pytest.approx(0.30 if counts else BODY_WIDTH_M, rel=1e-9)
    assert slenderness_of(reply) == pytest.approx(reply["rocket"]["length_m"] / width, rel=1e-6)


def test_pods_do_not_count_towards_the_width():
    """two_stage's booster shells made 0.1 m in radius (wider than the 28.7 mm core): the width stays the
    core's, and the reply's max_diameter_m is not used while there are shells to measure."""
    reply = load_reply("two_stage")
    for i in (5, 6):
        fit_part(reply, i)["outer_radius_aft_m"] = 0.1
    fit_part(reply, 6)["outer_radius_fore_m"] = 0.1
    reply["rocket"]["max_diameter_m"] = 0.3
    assert slenderness_of(reply) == pytest.approx(reply["rocket"]["length_m"] / (2 * CORE_RADIUS_M), rel=1e-6)


@pytest.mark.parametrize("unusable", ["no radius", "no length", "inactive"])
def test_width_falls_back_to_the_reply_without_usable_shells(unusable):
    reply = load_reply("single_stage")
    for i in MAIN_SHELLS:
        part = fit_part(reply, i)
        if unusable == "no radius":
            part["outer_radius_fore_m"] = part["outer_radius_aft_m"] = None
        elif unusable == "no length":
            part["length_m"] = 0.0
        else:
            part["active"] = False
    reply["rocket"]["max_diameter_m"] = 0.05
    assert fit._body_width(fit._Parts(reply["components"])) is None
    assert slenderness_of(reply) == pytest.approx(reply["rocket"]["length_m"] / 0.05, rel=1e-6)


def test_slenderness_with_an_absurd_length_is_the_largest_violation():
    """A length so large that the ratio is not a finite number: the largest violation, and
    nothing that is not a finite number is kept in info (it must stay valid JSON)."""
    reply = load_reply("single_stage")
    reply["rocket"]["length_m"] = 1e308
    check = fit_check(reply)
    got, found = outcome_and_rule(check, "slenderness")
    assert got == "fail" and found["size"] == ladder.MAX_VIOLATION and found["value"] is None
    assert "inf" not in all_text(check) and "cannot be judged" in all_text(check)
    json.dumps(check.info, allow_nan=False)


@pytest.mark.parametrize("field, value", [("length_m", None), ("length_m", 0.0), ("length_m", "long")])
def test_slenderness_skipped_without_a_length(field, value):
    reply = load_reply("single_stage")
    reply["rocket"][field] = value
    assert "slenderness" not in fit_check(reply).info["measures"]


@pytest.mark.parametrize("value", [None, 0.0, "wide"])
def test_slenderness_skipped_without_any_width(value):
    """No usable shell and no usable max_diameter_m: the rule is skipped (with shells, the reply's
    max_diameter_m is not needed)."""
    reply = load_reply("single_stage")
    reply["rocket"]["max_diameter_m"] = value
    assert slenderness_of(reply) == pytest.approx(reply["rocket"]["length_m"] / BODY_WIDTH_M, rel=1e-6)
    for i in MAIN_SHELLS:
        fit_part(reply, i)["outer_radius_fore_m"] = fit_part(reply, i)["outer_radius_aft_m"] = None
    assert "slenderness" not in fit_check(reply).info["measures"]
    del reply["rocket"]
    assert "slenderness" not in fit_check(reply).info["measures"]


# ------------------------------------------------------------------ stage 6: the last opening before landing

def opening_reply(gap: "float | None", first_gap: float = 50.0) -> dict:
    """single_stage with section 0's first opening `first_gap` s and its last `gap` s before landing."""
    land = 93.0
    last = None if gap is None else land - gap
    deployments = [{"device": "Drogue", "during_burn": False, "speed_ms": 1.0, "time_s": land - first_gap},
                   {"device": "Main", "during_burn": False, "speed_ms": 20.0, "time_s": last}]
    return each_branch(load_reply("single_stage"), 0, landing_time_s=land, deploy_time_s=land - first_gap,
                       deployments=deployments)


def opens_late_sizes(check) -> list:
    return [v["size"] for flight_rules in check.info["flight_violations"] for v in flight_rules
            if v["rule"] == "opens_late_0"]


@pytest.mark.parametrize("gap, passed", [(34.4, True), (5.7, True), (3.0, True), (2.2, False), (0.4, False)])
def test_last_opening_before_landing(gap, passed):
    # the references that pass open at least 5.7 s before landing (V4-0073); V4-0112 with 8 pods 2.2 s
    check = flight.check_flight(opening_reply(gap), NO_LIMIT)
    assert check.passed == passed
    if passed:
        assert opens_late_sizes(check) == []
        return
    assert opens_late_sizes(check) == [pytest.approx(math.log2(L.RECOVERY_OPEN_BEFORE_LANDING_MIN_S / gap),
                                                     abs=1e-6)] * 3
    assert any(f"opens only {gap:.1f} s before it lands" in r for r in check.reasons), check.reasons
    assert check.credit == pytest.approx(1 / (1 + math.log2(3.0 / gap)), abs=1e-6)


def test_opening_after_landing_is_the_largest_violation():
    check = flight.check_flight(opening_reply(-1.0), NO_LIMIT)
    assert opens_late_sizes(check) == [ladder.MAX_VIOLATION] * 3
    assert any("opens only 0.0 s before it lands" in r for r in check.reasons)


@pytest.mark.parametrize("unknown", ["opening", "landing"])
def test_unknown_times_are_the_largest_violation(unknown):
    if unknown == "opening":
        reply = each_branch(load_reply("single_stage"), 0, deploy_time_s=None,
                            deployments=[{"device": "Parachute", "time_s": None}])
    else:
        reply = each_branch(load_reply("single_stage"), 0, landing_time_s="soon")
    check = flight.check_flight(reply, NO_LIMIT)
    assert opens_late_sizes(check) == [ladder.MAX_VIOLATION] * 3
    assert any("its landing is unknown" in r for r in check.reasons)


def test_section_with_two_openings_uses_the_last():
    # the drogue opens 50 s before landing, the main only 2.2 s before: fails
    check = flight.check_flight(opening_reply(2.2, first_gap=50.0), NO_LIMIT)
    assert not check.passed and len(opens_late_sizes(check)) == 3
    # the first opening late and the last early cannot happen (the last is the latest); the
    # largest time counts whatever the order the reply lists them in
    reply = opening_reply(2.2, first_gap=50.0)
    for f in reply["flights"]:
        f["branches"][0]["deployments"].reverse()
    assert opens_late_sizes(flight.check_flight(reply, NO_LIMIT)) == opens_late_sizes(check)


def test_section_that_never_opens_gets_no_opens_late():
    reply = each_branch(load_reply("two_stage"), 1, has_recovery=False)
    check = flight.check_flight(reply, NO_LIMIT)
    assert check.passed and not any(v["rule"].startswith("opens_late") for fl in check.info["flight_violations"]
                                    for v in fl)


# ------------------------------------------------------------------ stage 6: a fixed opening altitude

def low_reply(event: str, altitude) -> dict:
    """single_stage with the main parachute (4, set to ALTITUDE 182.88 m) changed."""
    reply = load_reply("single_stage")
    rec = fit_part(reply, 4)["recovery"]
    rec["deploy_event"], rec["deploy_altitude_m"] = event, altitude
    return reply


@pytest.mark.parametrize("altitude, size", [(182.88, 0.0), (100.0, 0.0), (50.0, 0.0), (30.0, math.log2(50 / 30)),
                                            (4.0, ladder.MAX_VIOLATION), (0.0, ladder.MAX_VIOLATION)])
def test_fixed_altitude_opening_must_be_high_enough(altitude, size):
    # 55 references open at a fixed altitude, the lowest at 100 m (V4-0173)
    check = flight.check_flight(low_reply("ALTITUDE", altitude), NO_LIMIT)
    if size == 0.0:
        assert check.passed and check.info["low_opening_violations"] == []
        return
    assert not check.passed
    assert check.info["low_opening_violations"] == [pytest.approx(min(size, ladder.MAX_VIOLATION), abs=1e-6)]
    assert check.credit == pytest.approx(1 / (1 + min(size, ladder.MAX_VIOLATION)), abs=1e-6)
    assert check.reasons[0] == (f"'Parachute' is set to open {altitude:.4g} m above the ground; a recovery device "
                                f"that opens at a fixed altitude must open at {L.DEPLOY_ALTITUDE_MIN_M:g} m or higher "
                                f"(a real parachute needs height to fill)")


@pytest.mark.parametrize("event", ["APOGEE", "EJECTION", "LOWER_STAGE_SEPARATION", None])
def test_other_events_are_not_judged_on_their_altitude_setting(event):
    check = flight.check_flight(low_reply(event, 4.0), NO_LIMIT)
    assert check.passed and check.info["low_opening_violations"] == []


@pytest.mark.parametrize("altitude", [None, "low", float("nan")])
def test_unknown_altitude_is_the_largest_violation(altitude):
    check = flight.check_flight(low_reply("ALTITUDE", altitude), NO_LIMIT)
    assert check.info["low_opening_violations"] == [ladder.MAX_VIOLATION]
    assert "'Parachute' is set to open at an unknown altitude" in check.reasons[0]


def test_low_openings_add_to_the_worst_flight():
    reply = low_reply("ALTITUDE", 25.0)
    for f in reply["flights"]:
        f["branches"][0]["landing_time_s"] = f["branches"][0]["deployments"][-1]["time_s"] + 1.5
    check = flight.check_flight(reply, NO_LIMIT)
    low, late = math.log2(50 / 25.0), math.log2(3.0 / 1.5)
    assert check.info["low_opening_violations"] == [pytest.approx(low, abs=1e-6)]
    assert check.credit == pytest.approx(1 / (1 + low + late), abs=1e-6)
    assert check.reasons[0].startswith("'Parachute' is set to open 25 m") and len(check.reasons) == 2


def test_every_low_device_counts_once():
    reply = low_reply("ALTITUDE", 10.0)
    rec = fit_part(reply, 11)["recovery"]
    rec["deploy_event"], rec["deploy_altitude_m"] = "ALTITUDE", 20.0
    check = flight.check_flight(reply, NO_LIMIT)
    assert check.info["low_opening_violations"] == [pytest.approx(math.log2(5.0)), pytest.approx(math.log2(2.5))]


# ------------------------------------------------------------------ the real helper reports axis_offset_m

@pytest.mark.needs_java
def test_helper_reports_its_version_and_axis_offsets(gold_rows):
    from rocket_reward import ork, sim
    from rocket_reward.scoring import default_motor_table
    from rocket_reward.tools import mutate as M

    case = next(c for c in M.collect_designs(gold_rows)[0] if c.id.startswith("row-028"))
    design = M.apply_operator(M.operator_named("one_sided_motor_pod"), case.design, default_motor_table())
    assert design is not None
    root = {"openrocket": design["openrocket"]}
    flights = [{"wind_ms": 1.0, "seed": 1}]
    with sim.Simulator() as helper:
        assert helper.ping_reply["helper"] == 4
        reply = helper.run(ork.design_to_ork(root), 1.5, flights, config_id=ork.flight_config_id(root))
    assert reply["ok"] is True, reply
    parts = {c["index"]: c for c in reply["components"]}
    assert all("axis_offset_m" in c for c in parts.values())

    def pod_of(c):
        while c is not None and c["type"] != "PodSet":
            c = parts.get(c["parent"])
        return c

    pods = [c for c in parts.values() if c["type"] == "PodSet"]
    assert len(pods) == 1
    pod = pods[0]
    holder = parts[pod["parent"]]
    pod_radius = max(c["outer_radius_aft_m"] or 0.0 for c in parts.values()
                     if pod_of(c) is pod and c["type"] in ("NoseCone", "BodyTube"))
    flush = holder["outer_radius_fore_m"] + pod_radius
    assert pod["axis_offset_m"] == pytest.approx(flush, abs=1e-6)
    for c in parts.values():
        if pod_of(c) is pod and c["type"] in ("NoseCone", "BodyTube"):
            assert c["axis_offset_m"] == pytest.approx(flush, abs=1e-6), c["name"]
        elif pod_of(c) is None and c["type"] in ("AxialStage", "NoseCone", "BodyTube", "Transition"):
            assert c["axis_offset_m"] == pytest.approx(0.0, abs=1e-9), c["name"]
    check = fit.check_build(reply, root)
    assert check.info["measures"]["pod_inside_body"] == pytest.approx(0.0, abs=1e-6)
    assert check.info["measures"]["pod_detached"] == pytest.approx(0.0, abs=1e-6)
    assert "pod_motor_one_sided" in fit_rules(check)


# ------------------------------------------------------------------ round 3 on the 197 reference designs

META = Path(os.environ.get("ROCKET_REWARD_PROMPT_META", "") or "missing-prompt-meta.jsonl")
needs_meta = pytest.mark.skipif(not META.exists(), reason="set ROCKET_REWARD_PROMPT_META to the prompt meta file")
STRAP_ON_AFT_SHARE = 0.2
STAGE_ONLY = Requirements(id="t", apogee_m=Target(500.0, "about"), wind_ms=2.0)   # the same for both copies


def reference_designs() -> list:
    """The distinct reference designs of the prompt meta file (answers only, no requirements)."""
    from rocket_reward.tools import mutate as M
    rows = []
    with open(META, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                m = json.loads(line)
                msgs = m.get("messages") or [{}]
                rows.append({"id": m.get("id"), "answer": str(msgs[-1].get("content") or "")})
    return M.collect_designs(rows)[0]


def strap_ons_moved_aft(design: dict, share: float = STRAP_ON_AFT_SHARE):
    """A copy with every pod and side booster moved aft by `share` of its own written shell length
    (its axial offset grows by that much, whatever the offset is measured from); None without pods."""
    from rocket_reward.tools import mutate as M
    from rocket_reward.tree import attr_of, copy_tree, last_child, read_number, tag_of, value_of
    design = copy_tree(design)
    done = 0
    for pod in M._mu_parts(design, *M.POD_TAGS):
        length = sum(M._mu_num(s, "length") or 0.0 for s in M._mu_holder_parts(pod) if tag_of(s) in M.SHELL_TAGS)
        offset = last_child(pod, "axialoffset")
        at = read_number(value_of(offset))[0] if offset is not None else None
        if length > 0 and at is not None:
            M._mu_place(pod, attr_of(offset, "method") or "top", round(at + share * length, 6))
            done += 1
    return design if done else None


@needs_meta
def test_nested_motor_pods_apply_to_reference_designs():
    """motor_pods_inside_pods applies to none of the 48 val answers (tests/test_mutations.py) but to
    18 of the 197 reference designs (2026-11-19), among them the attackers' V4-0046 and V4-0099."""
    from rocket_reward.scoring import default_motor_table
    from rocket_reward.tools import mutate as M
    op, table = M.operator_named("motor_pods_inside_pods"), default_motor_table()
    applied = {c.id for c in reference_designs() if M.apply_operator(op, c.design, table) is not None}
    assert len(applied) >= 3 and {"V4-0046", "V4-0099"} <= applied, sorted(applied)


@needs_meta
@pytest.mark.needs_java
def test_strap_on_boosters_ending_below_the_core_keep_their_stage():
    """Round 3 made pod_outside_airframe a share of the pod's own length so that a sound strap-on
    booster that ends a little below the core passes. On every reference design with pods, the pods
    moved aft by 20% of their own length reach the same stage as the original. Not an operator with
    the "same_or_higher" promise: the flight changes, and V4-0107 goes from 0.9991 to 0.9989
    (2026-11-19, targets both)."""
    from rocket_reward.scoring import score_many
    from rocket_reward.sim import SimPool
    from rocket_reward.tools import mutate as M
    pairs = [(c, m) for c in reference_designs() for m in [strap_ons_moved_aft(c.design)] if m is not None]
    assert len(pairs) >= 5, [c.id for c, _ in pairs]          # 9 on 2026-11-19
    answers = [M.mutant_answer(c) for c, _ in pairs] + [M.mutant_answer(c, m) for c, m in pairs]
    with SimPool(4) as pool:
        got = score_many(answers, [STAGE_ONLY] * len(answers), simulator=pool)
    before, after = got[:len(pairs)], got[len(pairs):]
    moved = [f"{c.id}: {b.stage} {b.score:.4f} -> {a.stage} {a.score:.4f} {a.reasons[:1]}"
             for (c, _), b, a in zip(pairs, before, after) if a.stage != b.stage]
    assert not moved, "\n".join(moved)
    assert sum(b.stage == "targets" for b in before) >= 3
