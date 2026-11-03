"""Tests for the Stage-2 reasoning renderer, removals, flags and validator.

Every test here is purely static: no JVM, no simulation, no flights.  The
fixture is a small synthetic compact design written by hand and mirrors the
real Stage-1 compact shape: leaves are direct children of their component,
sub-components live under a "subcomponents" wrapper.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.sft_compact_removals import (  # noqa: E402
    apply_approved_removals,
)
from scripts.sft_compact_reasoning import (  # noqa: E402
    child,
    children_of,
    coverage_gaps,
    fit_checks,
    find_rocket,
    fmt_sig3,
    fmt_value,
    render_propulsion,
    render_thought,
    stage_wrappers,
    walk_components,
)
from scripts.sft_compact_finalize import banned_hits, compute_flags  # noqa: E402
from scripts.sft_compact_validate import (  # noqa: E402
    design_designations,
    design_leaves,
    expected_flags,
    flags_match,
    stage_mount_events,
)


# --------------------------------------------------------------------------
# fixtures
# --------------------------------------------------------------------------

def _leaf(tag, value, attrs=None):
    payload: dict = {}
    if attrs:
        payload["attrs"] = attrs
    payload["value"] = value
    return {tag: payload}


def _comp(tag, attrs=None, children=None):
    payload: dict = {}
    if attrs:
        payload["attrs"] = attrs
    payload["children"] = children or []
    return {tag: payload}


def _subs(*comps):
    return _comp("subcomponents", children=list(comps))


def make_compact_design() -> dict:
    """One stage: nose, tube with a motor mount, ring, chute, two fin sets."""
    mount = _comp("motormount", children=[
        _leaf("ignitionevent", "launch"),
        _leaf("ignitiondelay", 0.0),
        _comp("motor", attrs={"configid": "cfg0"}, children=[
            _leaf("type", "single"),
            _leaf("manufacturer", "Estes"),
            _leaf("designation", "C6"),
            _leaf("diameter", 0.018),
            _leaf("length", 0.07),
            _leaf("delay", 0.0),
        ]),
    ])
    inner = _comp("innertube", children=[
        _leaf("position", 0.02),
        _leaf("length", 0.2),
        _leaf("radius", 0.014),
        _leaf("thickness", 0.001),
        mount,
    ])
    ring = _comp("centeringring", children=[
        _leaf("position", 0.03),
        _leaf("length", 0.006),
        _leaf("radius", 0.015),
        _leaf("inneradius", 0.0115),
    ])
    chute = _comp("parachute", children=[
        _leaf("cd", 0.8),
        _leaf("diameter", 0.3),
        _leaf("deployevent", "apogee"),
        _leaf("position", 0.1),
        _leaf("length", 0.1),
    ])
    fins_trap = _comp("trapezoidfinset", children=[
        _leaf("fincount", 3),
        _leaf("rootchord", 0.055),
        _leaf("tipchord", 0.022),
        _leaf("height", 0.038),
        _leaf("sweeplength", 0.02),
        _leaf("thickness", 0.003),
        _leaf("crosssection", "airfoil"),
        _leaf("position", 0.3),
        _leaf("length", 0.055),
    ])
    fins_free = _comp("freeformfinset", children=[
        _leaf("fincount", 3),
        _leaf("thickness", 0.003),
        _leaf("position", 0.32),
        _leaf("length", 0.05),
        _comp("finpoints", children=[
            _leaf("point", None, attrs={"x": 0.0, "y": 0.0}),
            _leaf("point", None, attrs={"x": 0.05, "y": 0.0}),
            _leaf("point", None, attrs={"x": 0.03, "y": 0.038}),
        ]),
    ])
    stage = _comp("stage", children=[
        _subs(
            _comp("nosecone", children=[
                _leaf("shapeclipped", False),
                _leaf("thickness", 0.002),
                _leaf("length", 0.12),
                _leaf("position", 0.0),
            ]),
            _comp("bodytube", children=[
                _leaf("length", 0.457),
                _leaf("radius", 0.0124),
                _leaf("thickness", 0.0005),
                _leaf("position", 0.12),
                _subs(inner, ring, chute, fins_trap, fins_free),
            ]),
        ),
    ])
    rocket = _comp("rocket", attrs={"referencetype": "maximum"}, children=[
        _comp("motorconfiguration", attrs={"configid": "cfg0", "default": "true"},
              children=[_comp("stage", attrs={"number": 0, "active": "true"})]),
        _subs(stage),
    ])
    simulation = _comp("simulation", attrs={"name": "Simulation 1"}, children=[
        _comp("conditions", children=[
            _leaf("launchrodangle", 0.0),
            _leaf("launchrodlength", 1.0),
            _leaf("winddirection", 2.0),
            _leaf("windaverage", 0.0),
        ]),
        _leaf("calculator", "Barrowman"),
    ])
    return {"openrocket": {"attrs": {"version": "1.9"}, "children": [
        rocket,
        {"simulations": {"attrs": {}, "children": [{"simulation": simulation}]}},
    ]}}


def design_parts(design: dict):
    """(rocket, stage, bodytube, innertube, motormount, motor) of the fixture."""
    rocket = find_rocket(design)
    stage = children_of(child(rocket, "subcomponents"))[0]["stage"]
    stage_kids = child(stage, "subcomponents")["children"]
    bodytube = stage_kids[1]["bodytube"]
    tube_kids = child(bodytube, "subcomponents")["children"]
    inner = tube_kids[0]["innertube"]
    mount = child(inner, "motormount")
    motor = child(mount, "motor")
    return rocket, stage, bodytube, inner, mount, motor


def make_eng() -> dict:
    return {
        "motors": [{
            "motor": {
                "designation": "C6",
                "total_impulse_ns": 10.0,
                "burn_time_s": 1.6,
                "average_thrust_n": 6.0,
                "diameter_m": 0.018,
                "length_m": 0.07,
                "digest": "c8743ef3fa99e14a89885cbe0ead47b2",
            },
            "instance_count": 1,
        }],
        "motor_aggregates": {"total_impulse_ns": 10.0},
        "liftoff_mass_kg": 0.065,
        "cg_m": 0.31,
        "cp_m": 0.352,
        "reference_diameter_m": 0.0248,
        "static_margin_cal": 1.7,
    }


TARGETS = {"apogee_m": 245.0, "max_velocity_ms": 88.0, "max_mach": 0.26,
           "time_to_apogee_s": 4.2, "flight_time_s": 22.8, "ground_hit_ms": 5.2,
           "wind_ms": 0.0}
PROMPT = ("Design a hobby rocket to reach 245 meters apogee, total flight "
          "duration under 25 seconds, and land under 6 m/s.")


def make_fit_dump() -> list[dict]:
    """Load-dump rows aligned with the fixture's component DFS order."""
    return [
        {"cls": "NoseCone", "index": 1, "parent_index": 0,
         "loaded": {"getLength": 0.12, "getPosition": 0.0}},
        {"cls": "BodyTube", "index": 2, "parent_index": 0,
         "loaded": {"getLength": 0.457, "getPosition": 0.12,
                    "getInnerRadius": 0.0119, "getOuterRadius": 0.0124}},
        {"cls": "InnerTube", "index": 3, "parent_index": 2,
         "loaded": {"getLength": 0.2, "getPosition": 0.02,
                    "getInnerRadius": 0.014, "getOuterRadius": 0.015}},
        {"cls": "CenteringRing", "index": 4, "parent_index": 2,
         "loaded": {"getLength": 0.006, "getPosition": 0.03,
                    "getInnerRadius": 0.0115, "getOuterRadius": 0.015}},
        {"cls": "Parachute", "index": 5, "parent_index": 2,
         "loaded": {"getLength": 0.1, "getPosition": 0.1}},
        {"cls": "TrapezoidFinSet", "index": 6, "parent_index": 2,
         "loaded": {"getLength": 0.055, "getPosition": 0.3}},
        {"cls": "FreeformFinSet", "index": 7, "parent_index": 2,
         "loaded": {"getLength": 0.05, "getPosition": 0.32}},
        {"cls": "AxialStage", "index": 0, "parent_index": -1,
         "loaded": {"getLength": 0.577}},
    ]


# --------------------------------------------------------------------------
# rendering tests
# --------------------------------------------------------------------------

def test_thought_has_all_eight_sections_in_order():
    out = render_thought(make_compact_design(), make_eng(), TARGETS, PROMPT,
                         fit_dump=make_fit_dump())
    thought = out["thought"]
    sections = ["REQUIREMENTS", "AIRFRAME", "HOW THE PARTS FIT", "FINS",
                "PROPULSION", "BALANCE", "RECOVERY", "EXPECTED FLIGHT"]
    pos = [re.search(rf"(?m)^{re.escape(s)}", thought).start() for s in sections]
    assert pos == sorted(pos), f"section order wrong: {pos}"


def test_thought_covers_every_design_leaf():
    design = make_compact_design()
    out = render_thought(design, make_eng(), TARGETS, PROMPT,
                         fit_dump=make_fit_dump())
    assert out["not_computed"] == [], out["not_computed"]
    assert coverage_gaps(out["thought"], design) == []


def test_thought_contains_freeform_fin_points():
    out = render_thought(make_compact_design(), make_eng(), TARGETS, PROMPT,
                         fit_dump=None)
    assert "(0.05, 0.0)" in out["thought"]
    assert "(0.03, 0.038)" in out["thought"]


def test_thought_no_banned_words_or_sim_name():
    out = render_thought(make_compact_design(), make_eng(), TARGETS, PROMPT,
                         fit_dump=None)
    assert banned_hits(out["thought"]) == []
    assert "Simulation 1" not in out["thought"]


def test_fit_checks_report_real_numbers():
    design = make_compact_design()
    rocket = find_rocket(design)
    comps = [(tag, payload) for _, st in stage_wrappers(rocket)
             for tag, payload, _ in walk_components(st)]
    lines, failures, not_computed = fit_checks(comps, make_fit_dump(), make_eng())
    text = "\n".join(lines)
    assert "motor C6: diameter 0.018 m vs mount inner diameter 0.028 m" in text
    assert "motor length 0.07 m vs mount length 0.2 m - fits" in text
    assert failures == []
    assert not any("did not align" in n for n in not_computed)


def test_fit_checks_flag_motor_longer_than_mount():
    eng = make_eng()
    eng["motors"][0]["motor"]["length_m"] = 0.25  # longer than the 0.2 m tube
    design = make_compact_design()
    rocket = find_rocket(design)
    comps = [(tag, payload) for _, st in stage_wrappers(rocket)
             for tag, payload, _ in walk_components(st)]
    lines, failures, _ = fit_checks(comps, make_fit_dump(), eng)
    # overhang is normal, so it is stated but not a failure
    assert not any("mount length" in f for f in failures)
    assert any("overhangs the mount" in line for line in lines)


def test_propulsion_prints_ttw_only_when_certain():
    design = make_compact_design()
    rocket = find_rocket(design)
    lines, _, certain = render_propulsion(design, rocket, make_eng())
    # single motor with an explicit launch event: certain, printed
    assert certain
    assert any("thrust-to-weight at liftoff" in l for l in lines)
    ttw = 6.0 / (0.065 * 9.80665)
    assert any(fmt_sig3(ttw) in l for l in lines)


def _add_second_mount(design: dict) -> None:
    """Give the tube a second mount+motor with an automatic ignition event,
    so which motor lights first is not certain from the file."""
    _, _, bodytube, _, _, _ = design_parts(design)
    subs = child(bodytube, "subcomponents")
    mount2 = _comp("motormount", children=[
        _leaf("ignitionevent", "automatic"),
        _leaf("ignitiondelay", 0.0),
        _comp("motor", attrs={"configid": "cfg0"}, children=[
            _leaf("type", "single"),
            _leaf("manufacturer", "Estes"),
            _leaf("designation", "D12"),
            _leaf("diameter", 0.018),
            _leaf("length", 0.07),
            _leaf("delay", 0.0),
        ]),
    ])
    subs["children"].append({"innertube": {
        "attrs": {}, "children": [_leaf("position", 0.1), mount2]}})


def test_ttw_undetermined_for_multi_motor_ambiguity():
    design = make_compact_design()
    rocket = find_rocket(design)
    _add_second_mount(design)
    eng = make_eng()
    eng["motors"].append({"motor": dict(eng["motors"][0]["motor"],
                                        designation="D12"), "instance_count": 1})
    lines, _, certain = render_propulsion(design, rocket, eng)
    assert not certain
    assert any("could not be determined" in l for l in lines)
    assert not any("thrust-to-weight at liftoff" in l for l in lines)


def test_motor_name_differs_reported_with_both_names():
    design = make_compact_design()
    rocket = find_rocket(design)
    eng = make_eng()
    eng["motors"][0]["motor"]["designation"] = "Estes C6-5"  # alias
    lines, diffs, _ = render_propulsion(design, rocket, eng)
    assert any("the motor database resolves this as Estes C6-5" in l
               for l in lines)
    assert diffs and diffs[0]["designation_design"] == "C6"
    assert diffs[0]["designation_resolved"] == "Estes C6-5"


def test_values_never_rounded():
    odd = 0.028956000000000001
    assert fmt_value(odd) == repr(odd)
    assert "0.028956" in fmt_value(odd)
    assert fmt_sig3(245.0) == "245"
    assert fmt_sig3(1.7) == "1.7"


# --------------------------------------------------------------------------
# flag tests
# --------------------------------------------------------------------------

def test_compute_flags_landing_and_stability():
    flags = compute_flags(dict(TARGETS, ground_hit_ms=9.0), make_eng(), [],
                          [], ttw_certain=True)
    assert "landing_over_8ms" in flags
    assert "ttw_undetermined" not in flags

    flags = compute_flags(dict(TARGETS), {"static_margin_cal": -0.442}, [],
                          [], ttw_certain=True)
    assert "stability_negative" in flags and "stability_under_1cal" in flags

    flags = compute_flags(dict(TARGETS), {"static_margin_cal": 0.8}, [],
                          [], ttw_certain=True)
    assert "stability_under_1cal" in flags and "stability_negative" not in flags

    flags = compute_flags(dict(TARGETS), {"static_margin_cal": 1.2}, [],
                          [], ttw_certain=True)
    assert "stability_under_1cal" not in flags


def test_compute_flags_fit_and_motor_diffs():
    flags = compute_flags(dict(TARGETS), {}, [{"designation_design": "C6",
                                               "designation_resolved": "C6-5",
                                               "digest_differs": False}],
                          ["motor C6 length 0.25 exceeds mount length 0.2"],
                          ttw_certain=True)
    kinds = [f if isinstance(f, str) else f["flag"] for f in flags]
    assert "fit_issue" in kinds and "motor_name_differs" in kinds
    fit_flag = next(f for f in flags if isinstance(f, dict)
                    and f["flag"] == "fit_issue")
    assert fit_flag["details"] == ["motor C6 length 0.25 exceeds mount length 0.2"]


def test_expected_flags_matches_compute_flags_on_fixture():
    design = make_compact_design()
    out = render_thought(design, make_eng(), TARGETS, PROMPT, fit_dump=None)
    flags = compute_flags(TARGETS, make_eng(), out["motor_diffs"],
                          out["fit_failures"], out["ttw_certain"])
    row = {"file": "test.ork", "sim": "Simulation 1", "targets": TARGETS}
    exp = expected_flags(row, design, make_eng())
    assert flags_match(flags, exp) == []


# --------------------------------------------------------------------------
# removal tests
# --------------------------------------------------------------------------

def _add_junk(design: dict) -> dict:
    rocket, stage, bodytube, inner, mount, motor = design_parts(design)
    bodytube["children"].insert(0, {"color": {"value": "255,0,0"}})
    bodytube["children"].insert(0, {"linestyle": {"value": "solid"}})
    stage["children"].insert(
        0, _comp("digest", children=[_leaf("digestvalue", "deadbeef" * 4)]))
    rocket["children"].insert(0, _comp("preset", attrs={
        "digest": "aaaabbbbccccddddeeeeffff00001111",
        "manufacturer": "Estes", "partno": "BT-50", "type": "BODY_TUBE"}))
    return design


def test_apply_removals_strips_junk_and_keeps_clean_designs():
    clean = make_compact_design()
    # a clean design passes through unchanged
    assert json.dumps(apply_approved_removals(clean), sort_keys=True) == \
        json.dumps(clean, sort_keys=True)

    junk = _add_junk(make_compact_design())
    stripped = apply_approved_removals(junk)
    s = json.dumps(stripped)
    assert '"digest"' not in s and '"color"' not in s and '"linestyle"' not in s
    assert '"preset"' not in s

    # every physics value of the clean design is still in the stripped one
    _, _, _, _, _, motor = design_parts(stripped)
    assert child(motor, "designation")["value"] == "C6"


def test_preset_blocks_removed_entirely():
    design = make_compact_design()
    _, _, bodytube, _, _, _ = design_parts(design)
    bodytube["children"].insert(0, _comp("preset", attrs={
        "digest": "aaaabbbbccccddddeeeeffff00001111",
        "manufacturer": "Estes", "partno": "BT-50", "type": "BODY_TUBE"}))
    stripped = apply_approved_removals(design)
    _, _, tube_s, _, _, _ = design_parts(stripped)
    assert not [w for w in tube_s["children"] if "preset" in w]
    # every other bodytube leaf survives
    assert any("length" in w for w in tube_s["children"])


# --------------------------------------------------------------------------
# validator helper tests
# --------------------------------------------------------------------------

def test_design_leaves_and_designations():
    design = make_compact_design()
    paths = [p for p, _ in design_leaves(design)]
    assert any(p.rsplit(":", 1)[-1] == "designation" for p in paths)
    assert design_designations(design) == ["C6"]


def test_stage_mount_events_finds_motor_and_ignition():
    rocket = find_rocket(make_compact_design())
    assert stage_mount_events(rocket) == [("launch", 0.0)]


def test_expected_flags_ttw_undetermined_for_multi_motor():
    design = make_compact_design()
    _add_second_mount(design)
    row = {"file": "test.ork", "sim": "Simulation 1", "targets": TARGETS}
    eng = make_eng()
    eng["motors"].append({"motor": dict(eng["motors"][0]["motor"],
                                        designation="D12"), "instance_count": 1})
    flags = expected_flags(row, design, eng)
    assert "ttw_undetermined" in flags


def test_flags_match_reports_missing_and_unexpected():
    got = ["landing_over_8ms"]
    exp = ["landing_over_8ms", "ttw_undetermined"]
    diffs = flags_match(got, exp)
    assert any("missing flag: ttw_undetermined" in d for d in diffs)
    diffs = flags_match(got + ["stability_negative"], exp)
    assert any("unexpected flag: stability_negative" in d for d in diffs)


def test_banned_hits_patterns():
    hits = banned_hits("the verified design 0beec7b5ea3f0fdbc95d0dd47f3c5bc2 "
                       "file alpha.ork id 0b9e6a83-3a0c-4a70-9d47-6f3d6a1a2f31")
    assert "word verified" in hits
    assert ".ork" in hits
    assert "uuid" in hits
    assert banned_hits("a clean thought about fins and parachutes") == []
    assert "getter name" in banned_hits("see getRadius of the tube")
    assert banned_hits("we get the radius from the file") == []


# --------------------------------------------------------------------------
# integration (skipped when the final outputs are absent)
# --------------------------------------------------------------------------

FINAL_DIR = REPO_ROOT / "sftgen" / "out" / "scratch" / "sft_compact_20261103" / "final"


@pytest.mark.skipif(not (FINAL_DIR / "validation_report.json").exists(),
                    reason="final rows not generated")
def test_final_validator_report_is_clean():
    report = json.loads((FINAL_DIR / "validation_report.json").read_text())
    assert report["problems"] == [], report["problems"][:5]
