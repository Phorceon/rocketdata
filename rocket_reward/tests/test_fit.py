"""Stage 5 (fit.py): OpenRocket built the design and its parts fit together.

Every test starts from a real recorded reply (tests/replies.py) of a sound
rocket and edits it to break exactly one rule: just under the limit (passes),
a little over it (a defect, which does not stop the ladder) and far over it
(a failure). No Java is needed.

single_stage: nose cone (1), body tubes (3, 5, 10) with a coupler and
bulkheads, a fin set (12) and two centering rings (13, 14) on body tube 10,
and two motor tubes (15, 16) each holding a motor.
two_stage: a main body tube (3) holding a motor and a fin set (13), with a
booster set (pod, 4) whose body tube (6) carries two one-fin sets (7, 8) at
+45 and -45 degrees and a motor tube (11).
"""
from __future__ import annotations

import math

import pytest

from rocket_reward import fit, ladder
from rocket_reward import limits as L
from rocket_reward.tree import make_node

from replies import load_reply

CONFIG = "cfg-1"


def fit_root(mounts: int = 2) -> dict:
    """A small design tree with `mounts` motor tubes, each holding a motor of the flown configuration."""
    tubes = [make_node("innertube", children=[
        make_node("motormount", children=[make_node("motor", attrs={"configid": CONFIG})])]) for _ in range(mounts)]
    stage = make_node("stage", children=[make_node("subcomponents", children=[
        make_node("bodytube", children=[make_node("subcomponents", children=tubes)])])])
    rocket = make_node("rocket", children=[
        make_node("motorconfiguration", attrs={"configid": CONFIG, "default": "true"}),
        make_node("subcomponents", children=[stage])])
    return make_node("openrocket", children=[rocket])


def fit_part(reply: dict, index: int) -> dict:
    """The part with this index in a reply."""
    return next(c for c in reply["components"] if c["index"] == index)


def fit_check(reply, root=None):
    """Run stage 5 with the matching two-mount design tree unless another is given."""
    return fit.check_build(reply, fit_root() if root is None else root)


def fit_rules(check) -> set:
    """The rules that found something, with "(defect)" on the small ones."""
    return {f["rule"] + (" (defect)" if f["defect"] else "") for f in check.info["findings"]}


def fit_outcome(check) -> str:
    """"pass", "defect" or "fail"."""
    if not check.passed:
        return "fail"
    return "defect" if check.defects else "pass"


# ------------------------------------------------------------------ sound replies

@pytest.mark.parametrize("name", ["single_stage", "two_stage"])
def test_sound_reply_passes_with_no_defect(name):
    check = fit_check(load_reply(name))
    assert check.stage == "build"
    assert check.passed and check.credit == 1.0
    assert check.defects == [] and check.reasons == []
    assert check.info["motor_mounts_loaded"] == 2
    rules = ["shell_step", "fin_past_back", "fin_past_front", "rigid_inside_radius", "soft_inside_radius",
             "motor_diameter", "motor_overhang"]
    # two_stage's motor tube and rings sit in the booster pod and are judged against the pod's own shell
    rules += ["motor_tube_outside_airframe", "ring_outside_airframe", "part_outside_airframe"]
    if name == "two_stage":
        rules += ["fin_sets_angle_gap"]
    for rule in rules:
        assert rule in check.info["measures"], rule


# ------------------------------------------------------------------ OpenRocket could not build or fly it

@pytest.mark.parametrize("kind, words", [("load", "could not read"), ("build", "could not build"),
                                         ("hang", "did not finish"), ("crash", "crashed")])
def test_reply_not_ok_gets_credit_zero(kind, words):
    check = fit_check({"ok": False, "error_kind": kind, "message": "Invalid parameter encountered, ignoring."})
    assert not check.passed and check.credit == 0.0
    assert words in check.reasons[0] and "Invalid parameter" in check.reasons[0]


def test_unreadable_value_reason_says_where_to_look():
    """OpenRocket's warning never names the value, so the reason says what it
    usually is and lists the other things OpenRocket skipped, at most three."""
    msg = "OpenRocket could not read some values in the file and would fly a different rocket: " \
          "Invalid parameter encountered, ignoring."
    others = [f"Unknown element separation{i}, ignoring." for i in range(5)]
    check = fit_check({"ok": False, "error_kind": "build", "message": msg,
                       "load_warnings": ["Invalid parameter encountered, ignoring."] + others})
    reason = check.reasons[0]
    assert check.credit == 0.0 and "a word or NaN" in reason and "write a number there" in reason
    assert "it also skipped" in reason and "separation2" in reason and "separation3" not in reason
    assert "and 2 more" in reason
    plain = fit_check({"ok": False, "error_kind": "build", "message": "the file holds no rocket"})
    assert "write a number there" not in plain.reasons[0]


@pytest.mark.parametrize("reply", [None, [], "text", {}, {"ok": None}, {"ok": "true"},
                                   {"ok": False}, {"ok": False, "error_kind": 3, "message": {"a": [1]}}])
def test_odd_reply_is_a_failure_not_a_crash(reply):
    check = fit_check(reply)
    assert not check.passed and check.credit == 0.0 and check.reasons


@pytest.mark.parametrize("flight", [{"ok": False, "error_kind": "crash", "error": "NullPointerException"},
                                    {"ok": False, "error_kind": "build", "error": "motor never ignites"},
                                    {"ok": None}, None, "x"])
def test_a_flight_that_could_not_fly_gets_credit_zero(flight):
    reply = load_reply("single_stage")
    reply["flights"][1] = flight
    check = fit_check(reply)
    assert not check.passed and check.credit == 0.0
    assert "flight 2" in check.reasons[0]


# ------------------------------------------------------------------ load warnings

def test_load_warning_is_a_yes_no_failure():
    reply = load_reply("single_stage")
    reply["load_warnings"] = ["Unknown parameter type 'mass' for Centering Ring, ignoring."] * 3
    check = fit_check(reply)
    assert not check.passed
    assert check.info["load_warnings"] == 1     # the same text twice counts once
    assert check.credit == pytest.approx(ladder.credit_from_violations([ladder.YES_NO_VIOLATION]))
    assert "Unknown parameter type 'mass'" in check.reasons[0]


def test_no_warning_is_known_to_be_harmless():
    assert fit.HARMLESS_LOAD_WARNINGS == ()


@pytest.mark.parametrize("warnings", [None, [], "Unknown element foo, ignoring.", [None, 3, {"a": 1}]])
def test_odd_load_warnings_do_not_crash(warnings):
    reply = load_reply("single_stage")
    reply["load_warnings"] = warnings
    check = fit_check(reply)
    assert check.passed == (not warnings)


# ------------------------------------------------------------------ shell steps

def fit_shell_step(step: float) -> dict:
    """single_stage with body tube 10 starting `step` (a share) narrower than body tube 5 ahead of it."""
    reply = load_reply("single_stage")
    big = fit_part(reply, 5)["outer_radius_aft_m"]
    fit_part(reply, 10)["outer_radius_fore_m"] = big * (1 - step)
    return reply


@pytest.mark.parametrize("step, outcome", [(0.099, "pass"), (0.12, "defect"), (0.5, "fail"), (1.0, "fail")])
def test_shell_step_within_a_stage(step, outcome):
    check = fit_check(fit_shell_step(step))
    assert fit_outcome(check) == outcome
    assert check.info["measures"]["shell_step"] == pytest.approx(step, abs=1e-6)
    if outcome != "pass":
        text = (check.reasons + check.defects)[0]
        assert "mm" in text and f"{step:.0%}" in text and "10%" in text


def fit_two_axial_stages(step: float) -> dict:
    """single_stage with a second stage behind it whose body tube is `step` narrower."""
    reply = load_reply("single_stage")
    back = fit_part(reply, 10)
    end = back["x0_m"] + back["length_m"]
    r = back["outer_radius_aft_m"] * (1 - step)
    reply["components"] += [
        {"index": 100, "parent": -1, "type": "AxialStage", "name": "Booster", "x0_m": end, "length_m": 0.3},
        {"index": 101, "parent": 100, "type": "BodyTube", "name": "Booster tube", "x0_m": end, "length_m": 0.3,
         "outer_radius_fore_m": r, "outer_radius_aft_m": r, "inner_radius_m": r - 0.002, "thickness_m": 0.002}]
    return reply


@pytest.mark.parametrize("step, outcome", [(0.14, "pass"), (0.2, "defect"), (0.6, "fail")])
def test_shell_step_between_stages_uses_its_own_limit(step, outcome):
    check = fit_check(fit_two_axial_stages(step))
    assert fit_outcome(check) == outcome
    assert "shell_step_between_stages" in check.info["measures"]
    assert check.info["measures"]["shell_step"] < L.SHELL_STEP_MAX_FRACTION


@pytest.mark.parametrize("step, outcome", [(0.09, "pass"), (0.12, "defect"), (0.5, "fail")])
def test_shell_step_inside_a_pod(step, outcome):
    reply = load_reply("two_stage")
    nose = fit_part(reply, 5)
    fit_part(reply, 6)["outer_radius_fore_m"] = nose["outer_radius_aft_m"] * (1 - step)
    assert fit_outcome(fit_check(reply)) == outcome


# ------------------------------------------------------------------ fins on their part

def fit_fin_at(start_x: float) -> dict:
    """single_stage with the root of fin set 12 starting at `start_x` metres from the nose tip."""
    reply = load_reply("single_stage")
    fins = fit_part(reply, 12)
    fins["x0_m"] = start_x
    fins["fins"]["root_x0_m"] = start_x
    return reply


@pytest.mark.parametrize("chords, outcome", [(0.0, "pass"), (0.49, "pass"), (0.6, "defect"), (2.0, "fail")])
def test_fin_root_past_the_back_of_its_part(chords, outcome):
    reply = load_reply("single_stage")
    tube, chord = fit_part(reply, 10), fit_part(reply, 12)["fins"]["root_chord_m"]
    check = fit_check(fit_fin_at(tube["x0_m"] + tube["length_m"] - chord + chords * chord))
    assert fit_outcome(check) == outcome
    assert check.info["measures"]["fin_past_back"] == pytest.approx(chords, abs=1e-6)
    if outcome == "fail":
        assert "root chord" in check.reasons[0] and "m" in check.reasons[0]


@pytest.mark.parametrize("chords, outcome", [(0.9, "pass"), (1.0, "pass"), (1.2, "defect"), (3.0, "fail")])
def test_fin_root_past_the_front_of_its_part(chords, outcome):
    reply = load_reply("single_stage")
    tube, chord = fit_part(reply, 10), fit_part(reply, 12)["fins"]["root_chord_m"]
    check = fit_check(fit_fin_at(tube["x0_m"] - chords * chord))
    assert fit_outcome(check) == outcome


def test_fin_root_reads_its_own_start_when_given():
    reply = load_reply("single_stage")
    fit_part(reply, 12)["fins"]["root_x0_m"] = None   # falls back to the part's own x0_m
    assert fit_check(reply).passed


def fit_tube_fins_at(lengths_past_back: float) -> dict:
    """single_stage with fin set 12 turned into tube fins as the helper reports
    them (no "fins" outline, the tubes' own x0_m and length_m), placed so their
    back end runs `lengths_past_back` tube lengths past the back of body tube 10."""
    reply = load_reply("single_stage")
    tube, fins = fit_part(reply, 10), fit_part(reply, 12)
    length = 0.076
    fins.update(type="TubeFinSet", fins=None, length_m=length,
                x0_m=tube["x0_m"] + tube["length_m"] - length + lengths_past_back * length)
    return reply


@pytest.mark.parametrize("lengths, outcome", [(0.0, "pass"), (0.49, "pass"), (0.6, "defect"),
                                              (1.5, "fail"), (3.0, "fail")])
def test_tube_fins_past_the_back_of_their_part(lengths, outcome):
    """Tube fins have no fin outline in the reply; their tubes are their root.
    They used to be skipped, so tubes floating behind the rocket reached targets
    (mutation floating_fins on row-016)."""
    check = fit_check(fit_tube_fins_at(lengths))
    assert fit_outcome(check) == outcome
    assert check.info["measures"]["fin_past_back"] == pytest.approx(lengths, abs=1e-6)
    if outcome == "fail":
        assert "the tubes of tube fin set" in check.reasons[0] and "tube length" in check.reasons[0]


def test_tube_fins_further_back_never_score_better():
    credits = [fit_check(fit_tube_fins_at(x)).credit for x in (0.0, 0.6, 1.0, 1.5, 2.5, 6.0)]
    assert credits == sorted(credits, reverse=True)


# ------------------------------------------------------------------ inside parts against the airframe

@pytest.mark.parametrize("index, ratio, outcome", [
    (13, 1.07, "pass"), (13, 1.2, "defect"), (13, 2.0, "fail"),     # centering ring, rigid: 1.08
    (11, 1.29, "pass"), (11, 1.5, "defect"), (11, 3.0, "fail"),     # parachute, packed: 1.30
])
def test_inside_part_wider_than_the_airframe(index, ratio, outcome):
    reply = load_reply("single_stage")
    inner = fit_part(reply, 10)["inner_radius_m"]
    part = fit_part(reply, index)
    part["outer_radius_fore_m"] = part["outer_radius_aft_m"] = inner * ratio
    check = fit_check(reply)
    assert fit_outcome(check) == outcome
    if outcome != "pass":
        text = (check.reasons + check.defects)[0]
        assert "wider than the" in text and "mm" in text


def test_inside_part_is_judged_against_the_airframe_not_its_parent():
    reply = load_reply("single_stage")
    # a centering ring parented to the motor tube is 3.5 times the motor tube's bore, but fits the body tube
    fit_part(reply, 13)["parent"] = 15
    check = fit_check(reply)
    assert check.passed and check.defects == []


def test_radial_offset_counts_towards_the_width():
    reply = load_reply("single_stage")
    inner = fit_part(reply, 10)["inner_radius_m"]
    chute = fit_part(reply, 11)
    chute["radial_offset_m"] = inner * 2.0
    assert not fit_check(reply).passed


# ------------------------------------------------------------------ outside the airframe

@pytest.mark.parametrize("outside, outcome", [(0.04, "pass"), (0.06, "defect"), (0.3, "fail")])
def test_motor_tube_out_of_the_airframe(outside, outcome):
    reply = load_reply("single_stage")
    fit_part(reply, 15)["x0_m"] += outside
    check = fit_check(reply)
    assert fit_outcome(check) == outcome
    assert check.info["measures"]["motor_tube_outside_airframe"] == pytest.approx(outside, abs=1e-6)


@pytest.mark.parametrize("outside, outcome", [(0.015, "pass"), (0.025, "defect"), (0.2, "fail")])
def test_ring_out_of_the_airframe(outside, outcome):
    reply = load_reply("single_stage")
    tube = fit_part(reply, 10)
    ring = fit_part(reply, 14)
    ring["length_m"] = 0.2
    ring["x0_m"] = tube["x0_m"] + tube["length_m"] + outside - ring["length_m"]
    check = fit_check(reply)
    assert fit_outcome(check) == outcome


def test_parts_in_a_pod_are_judged_against_the_pods_own_shell():
    # Changed on purpose (2026-11-19): parts in a pod used to be skipped, so a
    # booster part could sit anywhere. Now they are judged against the pod's shell.
    reply = load_reply("two_stage")
    assert "motor_tube_outside_airframe" not in fit_rules(fit_check(reply))
    fit_part(reply, 11)["x0_m"] += 1.0   # the booster's motor tube, 1 m behind its pod
    check = fit_check(reply)
    assert "motor_tube_outside_airframe" in fit_rules(check) and not check.passed
    assert check.info["measures"]["motor_tube_outside_airframe"] == pytest.approx(1.0, abs=1e-6)


# ------------------------------------------------------------------ motors

@pytest.mark.parametrize("ratio, outcome", [(1.04, "pass"), (1.2, "defect"), (2.0, "fail")])
def test_motor_wider_than_its_mount(ratio, outcome):
    reply = load_reply("single_stage")
    tube = fit_part(reply, 15)
    tube["motor"]["diameter_m"] = 2 * tube["inner_radius_m"] * ratio
    check = fit_check(reply)
    assert fit_outcome(check) == outcome
    assert check.info["measures"]["motor_diameter"] == pytest.approx(ratio, abs=1e-6)


def test_motor_in_a_mount_with_no_bore_fails():
    reply = load_reply("single_stage")
    fit_part(reply, 15)["inner_radius_m"] = 0.0
    check = fit_check(reply)
    assert not check.passed and "no room inside" in check.reasons[0]


@pytest.mark.parametrize("share, outcome", [(0.0, "pass"), (0.49, "pass"), (0.6, "defect"), (1.0, "fail")])
def test_motor_hanging_out_behind_its_mount(share, outcome):
    reply = load_reply("single_stage")
    motor = fit_part(reply, 15)["motor"]
    motor["overhang_m"] = share * motor["length_m"]
    check = fit_check(reply)
    assert fit_outcome(check) == outcome
    if outcome == "fail":
        assert "100%" in check.reasons[0] and "50%" in check.reasons[0]


def test_motor_missing_after_loading():
    reply = load_reply("single_stage")
    fit_part(reply, 16)["motor"] = None
    check = fit_check(reply)
    assert not check.passed and "motor_missing" in fit_rules(check)
    assert check.info["motor_mounts_expected"] == 2 and check.info["motor_mounts_loaded"] == 1
    assert check.credit == pytest.approx(ladder.credit_from_violations([ladder.YES_NO_VIOLATION]))


def test_no_motor_at_all():
    reply = load_reply("single_stage")
    for c in reply["components"]:
        c["motor"] = None
    check = fit_check(reply, root=fit_root(0))
    assert not check.passed and "no motor" in check.reasons[0]


def test_each_missing_motor_counts():
    one = load_reply("single_stage")
    fit_part(one, 16)["motor"] = None
    two = load_reply("single_stage")
    fit_part(two, 15)["motor"] = fit_part(two, 16)["motor"] = None
    assert fit_check(two).credit < fit_check(one).credit


# ------------------------------------------------------------------ two parts in one place

@pytest.mark.parametrize("rotation, outcome", [(-42.5, "pass"), (43.5, "defect"), (45.0, "fail"), (44.0, "fail")])
def test_two_fin_sets_at_the_same_angle(rotation, outcome):
    reply = load_reply("two_stage")
    # sets 7 (+45 degrees) and 8 overlap along the pod's tube; turn 8 to `rotation`
    fit_part(reply, 8)["fins"]["base_rotation_deg"] = rotation
    check = fit_check(reply)
    assert fit_outcome(check) == outcome


def test_fin_sets_sharing_one_angle_are_not_the_same_fins():
    reply = load_reply("two_stage")
    a, b = fit_part(reply, 7), fit_part(reply, 8)
    a["fins"].update(count=3, base_rotation_deg=0.0)
    b["fins"].update(count=4, base_rotation_deg=0.0)   # fins at 0 degrees coincide, the others do not
    check = fit_check(reply)
    assert check.passed and check.defects == []
    assert check.info["measures"]["fin_sets_angle_gap"] == pytest.approx(30.0)


def test_fin_sets_at_the_same_angle_that_do_not_overlap_pass():
    reply = load_reply("two_stage")
    b = fit_part(reply, 8)
    b["fins"]["base_rotation_deg"] = 45.0
    b["x0_m"] += b["length_m"] + 0.001
    assert "fin_sets_same_angle" not in fit_rules(fit_check(reply))


@pytest.mark.parametrize("overlap, outcome", [(0.003, "pass"), (0.004, "defect"), (0.009, "fail")])
def test_rings_pushed_into_each_other(overlap, outcome):
    reply = load_reply("single_stage")
    first, second = fit_part(reply, 13), fit_part(reply, 14)
    second["x0_m"] = first["x0_m"] + first["length_m"] - overlap
    check = fit_check(reply)
    assert fit_outcome(check) == outcome
    assert check.info["measures"]["rings_overlap"] == pytest.approx(overlap, abs=1e-9)


# ------------------------------------------------------------------ frames with no room inside

@pytest.mark.parametrize("make_solid", [
    lambda t: t.update(filled=True, inner_radius_m=0.0),     # "filled"
    lambda t: t.update(inner_radius_m=0.0),                  # a wall as thick as the radius
    lambda t: t.update(inner_radius_m=-0.01)])               # odd: thicker than the radius
def test_inside_part_in_a_frame_with_no_room_is_judged_against_its_outer_radius(make_solid):
    """Writing "filled" never hides an oversized part: it is judged against the
    frame's outer radius instead of being skipped (DESIGN.md rules 2 and 4)."""
    reply = load_reply("single_stage")
    tube = fit_part(reply, 10)
    make_solid(tube)
    assert fit_check(reply).passed       # the rings and motor tubes fit within the outer radius
    fit_part(reply, 15).update(outer_radius_fore_m=2 * tube["outer_radius_fore_m"],
                               outer_radius_aft_m=2 * tube["outer_radius_fore_m"])
    check = fit_check(reply)
    assert not check.passed and "rigid_inside_radius" in fit_rules(check)
    assert any("no room inside" in r and "100% wider" in r for r in check.reasons), check.reasons


def test_filled_frame_never_beats_a_frame_with_a_little_room():
    """The oversized part fails in both; the solid frame is not a way out."""
    credits = []
    for inner in (0.0003, 0.0):
        reply = load_reply("single_stage")
        tube = fit_part(reply, 10)
        tube.update(inner_radius_m=inner, filled=inner == 0.0)
        fit_part(reply, 15).update(outer_radius_fore_m=2 * tube["outer_radius_fore_m"],
                                   outer_radius_aft_m=2 * tube["outer_radius_fore_m"])
        credits.append(fit_check(reply))
    assert not credits[0].passed and not credits[1].passed


# ------------------------------------------------------------------ where the motor fires

def fit_motor_ahead(gap):
    """single_stage with motor 15's back end `gap` metres ahead of the back of the airframe."""
    reply = load_reply("single_stage")
    tail = fit_part(reply, 10)["x0_m"] + fit_part(reply, 10)["length_m"]
    motor = fit_part(reply, 15)["motor"]
    motor["x0_m"] = tail - motor["length_m"] - gap
    return (reply,)


@pytest.mark.parametrize("gap, outcome", [(0.0, "pass"), (0.12, "pass"), (0.15, "pass"), (0.18, "defect"),
                                          (0.3, "fail"), (0.53, "fail")])
def test_motor_ahead_of_the_tail(gap, outcome):
    check = fit_check(*fit_motor_ahead(gap))
    assert fit_outcome(check) == outcome
    assert check.info["measures"]["motor_ahead_of_tail"] == pytest.approx(gap, abs=1e-9)
    if outcome != "pass":
        text = (check.reasons + check.defects)[0]
        assert "fires into the rocket" in text and (f"{gap * 1000:.4g} mm" in text or f"{gap:.4g} m" in text)


def test_motor_in_a_side_booster_is_not_judged_against_the_core_tail():
    reply = load_reply("two_stage")
    motor = fit_part(reply, 11)["motor"]
    motor["x0_m"] -= 0.5
    assert "motor_ahead_of_tail" not in fit_rules(fit_check(reply))


# ------------------------------------------------------------------ pods and side boosters

def fit_pod_width(ratio):
    """two_stage with the booster's shells `ratio` times the core's radius."""
    reply = load_reply("two_stage")
    core = fit_part(reply, 3)["outer_radius_fore_m"]
    for i in (5, 6):
        part = fit_part(reply, i)
        part["outer_radius_aft_m"] = core * ratio
        if part["type"] == "BodyTube":
            part["outer_radius_fore_m"] = core * ratio
    return (reply,)


@pytest.mark.parametrize("ratio, outcome", [(0.6, "pass"), (1.0, "pass"), (1.3, "defect"), (2.0, "fail"),
                                            (5.0, "fail")])
def test_pod_no_wider_than_the_body(ratio, outcome):
    check = fit_check(*fit_pod_width(ratio))
    assert fit_outcome(check) == outcome
    if outcome != "pass":
        assert "pod_width" in {r.split(" ")[0] for r in fit_rules(check)}
        assert "times the main body's" in (check.reasons + check.defects)[0]


def test_pod_with_an_open_front_fails():
    reply = load_reply("two_stage")
    reply["components"] = [c for c in reply["components"] if c["index"] != 5]   # drop the booster's nose cone
    check = fit_check(reply)
    assert not check.passed and "pod_open_front" in fit_rules(check)
    assert "starts with an open body tube" in check.reasons[0]
    assert fit_check(load_reply("two_stage")).passed


# ------------------------------------------------------------------ missing, null and hostile fields

def test_components_missing_is_a_failure():
    for components in (None, [], "parts", 3):
        reply = load_reply("single_stage")
        reply["components"] = components
        check = fit_check(reply)
        assert not check.passed and check.credit < 1


@pytest.mark.parametrize("field", ["x0_m", "length_m", "outer_radius_fore_m", "outer_radius_aft_m",
                                   "inner_radius_m", "thickness_m", "radial_offset_m", "parent", "index",
                                   "type", "name", "fins", "motor", "active", "instances", "filled"])
@pytest.mark.parametrize("value", [None, "1.0", True, [], {}, float("nan"), float("inf"), -1e308, 10 ** 400])
@pytest.mark.parametrize("name", ["single_stage", "two_stage"])
def test_odd_field_values_never_crash(name, field, value):
    reply = load_reply(name)
    for c in reply["components"]:
        c[field] = value
    check = fit_check(reply)
    assert check.stage == "build" and 0.0 <= check.credit <= 1.0
    assert all(isinstance(r, str) for r in check.reasons + check.defects)


@pytest.mark.parametrize("field", ["count", "root_chord_m", "root_x0_m", "base_rotation_deg"])
@pytest.mark.parametrize("value", [None, "3", 0, -5, 1e9, float("nan")])
def test_odd_fin_values_never_crash(field, value):
    reply = load_reply("two_stage")
    for c in reply["components"]:
        if isinstance(c.get("fins"), dict):
            c["fins"][field] = value
    check = fit_check(reply)
    assert 0.0 <= check.credit <= 1.0


@pytest.mark.parametrize("field", ["diameter_m", "length_m", "overhang_m", "designation"])
@pytest.mark.parametrize("value", [None, "54", 0.0, -1.0, float("inf")])
def test_odd_motor_values_never_crash(field, value):
    reply = load_reply("single_stage")
    for c in reply["components"]:
        if isinstance(c.get("motor"), dict):
            c["motor"][field] = value
    check = fit_check(reply)
    assert 0.0 <= check.credit <= 1.0


def test_parent_links_in_a_loop_do_not_hang():
    reply = load_reply("single_stage")
    fit_part(reply, 10)["parent"] = 13
    fit_part(reply, 13)["parent"] = 10
    fit_part(reply, 11)["parent"] = 11
    check = fit_check(reply)
    assert 0.0 <= check.credit <= 1.0


def test_odd_design_tree_does_not_crash():
    for root in (None, {}, [], {"openrocket": 3}, make_node("openrocket")):
        check = fit.check_build(load_reply("single_stage"), root)
        assert check.stage == "build" and 0.0 <= check.credit <= 1.0


def test_reasons_are_short_for_huge_texts():
    reply = load_reply("single_stage")
    reply["load_warnings"] = ["x" * 100000]
    check = fit_check(reply)
    assert len(check.reasons[0]) < 2 * fit.MAX_TEXT_CHARS + 200


# ------------------------------------------------------------------ closer is never worse

def fit_series(make, values):
    """Credit and outcome of the reply that make(v) builds, for each v."""
    return [fit_check(*make(v)) for v in values]


SERIES = {
    "shell_step": (lambda v: (fit_shell_step(v),), [0.0, 0.05, 0.1, 0.11, 0.13, 0.2, 0.5, 0.9, 1.0]),
    "between_stages": (lambda v: (fit_two_axial_stages(v),), [0.1, 0.15, 0.18, 0.22, 0.4, 0.8]),
}


def fit_overhang(share):
    reply = load_reply("single_stage")
    motor = fit_part(reply, 15)["motor"]
    motor["overhang_m"] = share * motor["length_m"]
    return (reply,)


def fit_ring_overlap(overlap):
    reply = load_reply("single_stage")
    first, second = fit_part(reply, 13), fit_part(reply, 14)
    second["x0_m"] = first["x0_m"] + first["length_m"] - overlap
    return (reply,)


def fit_motor_width(ratio):
    reply = load_reply("single_stage")
    tube = fit_part(reply, 15)
    tube["motor"]["diameter_m"] = 2 * tube["inner_radius_m"] * ratio
    return (reply,)


SERIES.update({
    "motor_ahead": (fit_motor_ahead, [0.0, 0.1, 0.15, 0.16, 0.2, 0.3, 0.6, 1.2, 1.9]),
    "pod_width": (fit_pod_width, [0.5, 1.0, 1.1, 1.4, 2.0, 4.0, 10.0]),
    "overhang": (fit_overhang, [0.0, 0.3, 0.5, 0.55, 0.7, 1.0]),
    "ring_overlap": (fit_ring_overlap, [0.0, 0.002, 0.0035, 0.004, 0.006, 0.0095]),
    "motor_width": (fit_motor_width, [1.0, 1.05, 1.1, 1.3, 1.6, 3.0, 100.0]),
})


@pytest.mark.parametrize("rule", sorted(SERIES))
def test_bigger_violation_never_raises_the_credit(rule):
    make, values = SERIES[rule]
    checks = fit_series(make, values)
    credits = [c.credit for c in checks]
    assert all(a >= b for a, b in zip(credits, credits[1:])), credits
    # once a design fails it never passes again further out, and the defect count never falls before that
    order = {"pass": 0, "defect": 1, "fail": 2}
    outcomes = [order[fit_outcome(c)] for c in checks]
    assert outcomes == sorted(outcomes), outcomes
    # the score this stage gives (with defects counted) never rises either
    scores = [ladder.stage_score("build", c.credit, len(c.defects)) if not c.passed
              else ladder.stage_score("flight", 1.0, len(c.defects)) for c in checks]
    assert all(a >= b for a, b in zip(scores, scores[1:])), scores
    assert outcomes[0] == 0 and outcomes[-1] == 2


def test_failure_credit_follows_the_violation_formula():
    check = fit_check(fit_shell_step(0.5))
    size = ladder.over_limit(0.5, L.SHELL_STEP_MAX_FRACTION)
    assert check.credit == pytest.approx(1 / (1 + size))
    assert check.info["failure_sizes"] == [round(size, 4)]


def test_defect_boundary_is_the_ladder_number():
    limit = L.SHELL_STEP_MAX_FRACTION
    just_below = limit * 2 ** (ladder.FIT_DEFECT_BELOW - 1e-6)
    just_above = limit * 2 ** (ladder.FIT_DEFECT_BELOW + 1e-6)
    assert fit_outcome(fit_check(fit_shell_step(just_below))) == "defect"
    assert fit_outcome(fit_check(fit_shell_step(just_above))) == "fail"


def test_info_is_plain_numbers():
    check = fit_check(load_reply("single_stage"))
    for k, v in check.info["measures"].items():
        assert isinstance(v, float) and math.isfinite(v), k
