"""Checks for scripts/reward.py. The flight test needs Java + lib/OpenRocket.jar and is skipped without them;
everything else runs in milliseconds."""
import copy
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import reward as R  # noqa: E402

FIX = json.loads((REPO / "tests" / "fixtures" / "reward_design.json").read_text())
LOOKUP = FIX["lookup"]


def answer(design):
    return "<thought>sizing...</thought><design>" + json.dumps(design) + "</design>"


def run(design, req=None, **kw):
    return R.score(answer(design), req or {}, lookup=LOOKUP, flight=False, **kw)


def nodes(d, tag):
    """Every {tag: body} body in a v5 design dict."""
    out, stack = [], [d["openrocket"]]
    while stack:
        b = stack.pop()
        for c in b.get("children") or []:
            for k, v in c.items():
                if isinstance(v, dict):
                    if k == tag:
                        out.append(v)
                    if "children" in v:
                        stack.append(v)
    return out


def field(body, name):
    return next(c[name] for c in body["children"] if name in c)


def design():
    return copy.deepcopy(FIX["design"])


# ------------------------------------------------------------------ the reference design passes
def test_reference_design_clears_every_gate_before_flight():
    r = run(design())
    assert r["gate"] == "not flown", r["reasons"]


# ------------------------------------------------------------------ format and parts (-1.0)
@pytest.mark.parametrize("text,why", [
    ("no design here", "no complete"),
    ("<design>{oops</design>", "does not parse"),
    ('<design>{"rocket": {}}</design>', "openrocket"),
    ('<design>{"openrocket": {"children": []}, "notes": {}}</design>', "extra keys"),
    ('<design>{"openrocket": {"children": [{"rocket": []}]}}</design>', "is not {attrs"),
    ('<design>{"openrocket": {"children": [{"bad tag!": {}}]}}</design>', "bad tag name"),
])
def test_format_gate(text, why):
    r = R.score(text, {}, lookup=LOOKUP, flight=False)
    assert (r["score"], r["gate"]) == (-1.0, "format") and why in r["reasons"][0]


def test_unfinished_answer_is_format_fail():
    assert R.score(answer(design()), {}, lookup=LOOKUP, finish="length")["gate"] == "format"


def test_very_deep_tree_does_not_crash():
    deep = '{"openrocket": {"children": [' + '{"x": {"children": [' * 3000 + "]}}" * 3000 + "]}}"
    assert R.score("<design>" + deep + "</design>", {}, lookup=LOOKUP, flight=False)["gate"] == "format"


def test_missing_parachute_is_parts_fail():
    d = design()
    for b in nodes(d, "subcomponents"):
        b["children"] = [c for c in b["children"] if "parachute" not in c and "streamer" not in c]
    r = run(d)
    assert r["gate"] == "parts" and "parachute" in r["reasons"][0]


def test_made_up_motor_is_motors_fail():
    d = design()
    field(nodes(d, "motor")[0], "motor_id")["value"] = "Estes-Z9999"
    assert run(d)["gate"] == "motors"


# ------------------------------------------------------------------ geometry (-0.8)
@pytest.mark.parametrize("bad", ["NaN", "Infinity", "abc", -0.2, 50.0])
def test_bad_numbers_fail_geometry(bad):
    d = design()
    field(nodes(d, "bodytube")[0], "length")["value"] = bad
    r = run(d)
    assert r["gate"] == "geometry" and r["score"] == -0.8


def test_unknown_field_is_dropped_but_unknown_part_fails():
    d = design()
    nodes(d, "bodytube")[0]["children"].append({"warpdrive": {"value": 1}})
    r = run(d)
    assert r["gate"] == "not flown" and "bodytube.warpdrive" in r["notes"]["ignored_fields"]
    d = design()
    nodes(d, "subcomponents")[0]["children"].append({"antigravity": {"children": []}})
    assert "unknown part" in run(d)["reasons"][0]


def test_thin_fins_fail():
    d = design()
    field(nodes(d, "trapezoidfinset")[0], "thickness")["value"] = 0.0005
    assert any("thick" in x for x in run(d)["reasons"])


def test_duplicated_fin_set_clashes():
    d = design()
    for b in nodes(d, "subcomponents"):
        fins = [c for c in b["children"] if "trapezoidfinset" in c]
        if fins:
            b["children"].append(copy.deepcopy(fins[0]))
            break
    assert any("clash" in x for x in run(d)["reasons"])


def test_floating_fins_fail():
    d = design()
    f = nodes(d, "trapezoidfinset")[0]
    for key in ("position", "axialoffset"):
        if any(key in c for c in f["children"]):
            field(f, key)["attrs"] = {"type" if key == "position" else "method": "bottom"}
            field(f, key)["value"] = 0.5                     # 0.5 m behind the tail
    assert any("off the airframe" in x for x in run(d)["reasons"])


def test_unknown_material_fails():
    d = design()
    field(nodes(d, "bodytube")[0], "material")["value"] = "Unobtainium"
    assert any("unknown material" in x for x in run(d)["reasons"])


# ------------------------------------------------------------------ the model can not set physics
def test_overrides_are_removed():
    d = design()
    nodes(d, "stage")[0]["children"] += [{"overridecg": {"value": 0.01}}, {"overridesubcomponentscg": {"value": True}}]
    r = run(d)
    assert r["gate"] == "not flown" and r["notes"]["overrides_removed"] >= 2


def test_density_and_motor_come_from_tables():
    d = design()
    field(nodes(d, "bodytube")[0], "material")["attrs"]["density"] = 0.001
    motor = nodes(d, "motor")[0]
    field(motor, "diameter")["value"] = 0.5
    root, _ = R.gate_format(answer(d), "stop")
    stages = R.gate_parts(root)
    R.gate_motors(root, LOOKUP)
    R.gate_geometry(root, stages, R._load(R.SCHEMA_PATH, "schema"))
    tube = next(n for n in root.walk() if n.tag == "bodytube")
    assert tube.get("material").attrs["density"] > 100
    m = next(n for n in root.walk() if n.tag == "motor" and not n.leaf)
    assert m.num("diameter") == LOOKUP[m.text("motor_id")]["diameter_m"]


# ------------------------------------------------------------------ scoring
def test_closeness_is_graded():
    assert R.closeness(300, 300, "about", 0.05) == 1.0
    assert R.closeness(314, 300, "about", 0.05) == 1.0
    assert 0 < R.closeness(400, 300, "about", 0.05) < R.closeness(330, 300, "about", 0.05) < 1
    assert R.closeness(1000, 300, "about", 0.05) == 0.0
    assert R.closeness(90, 100, "max", 0.0) == 1.0 and R.closeness(120, 100, "max", 0.0) < 1


def test_targets_use_requirements_and_rescale_weights():
    m = {"apogee_m": 300.0, "flight_time_s": 40.0, "landing_ms": [2.0], "landing_limit_ms": 6.0}
    total, parts = R.targets({"target_apogee_m": 300, "apogee_tol_frac": 0.1}, m)
    assert parts == {"apogee": 1.0, "landing": 1.0} and total == 1.0
    total, parts = R.targets({"target_apogee_m": 600, "max_flight_time_s": 30}, m)
    assert total < 0.5 and set(parts) == {"apogee", "flight_time", "landing"}


def test_spec_gate():
    m = {"max_velocity_ms": 150.0}
    with pytest.raises(R.Reject):
        R.gate_spec({"max_body_diameter_mm": 24}, 0.02, [], m)          # 40 mm body
    with pytest.raises(R.Reject):
        R.gate_spec({"max_motor_class": "G"}, 0.01, [{"total_impulse_ns": 200}], m)   # an H
    R.gate_spec({"max_motor_class": "H"}, 0.01, [{"total_impulse_ns": 200}], m)
    assert R.motor_class({"total_impulse_ns": 10}) == "C"


def test_setup_problems_raise():
    with pytest.raises(R.SetupError):
        R._load(REPO / "no" / "such.json", "schema")


# ------------------------------------------------------------------ OpenRocket (skipped without Java)
def _have_openrocket():
    import shutil
    return R.JAR.exists() and (shutil.which("java") is not None or Path(R.OpenRocket._java("java")).exists())


@pytest.mark.skipif(not _have_openrocket(), reason="needs Java and lib/OpenRocket.jar")
def test_flight_end_to_end():
    r = R.score(answer(design()), {"target_apogee_m": 1000, "apogee_tol_frac": 0.1, "max_touchdown_ms": 6.9},
                lookup=LOOKUP)
    assert r["score"] is not None and r["metrics"].get("apogee_m") or r["gate"] == "flight"
    assert -0.5 <= r["score"] <= 1.0


def test_simulations_next_to_the_root_is_tolerated_and_dropped():
    d = design()
    text = "<design>" + json.dumps({"openrocket": d["openrocket"], "simulations": {"children": []}}) + "</design>"
    assert R.score(text, {}, lookup=LOOKUP, flight=False)["gate"] == "not flown"


def test_material_names_fall_back_to_their_family():
    schema = R._load(R.SCHEMA_PATH, "schema")
    d = design()
    field(nodes(d, "bodytube")[0], "material")["value"] = "Paper, spiral kraft glassine, made-up grade, bulk"
    root, _ = R.gate_format(answer(d), "stop")
    assert R.material_problems(root, schema) == []
    tube = next(n for n in root.walk() if n.tag == "bodytube")
    assert 500 < tube.get("material").attrs["density"] < 1500


def test_no_bulk_material_is_lighter_than_foam():
    schema = R._load(R.SCHEMA_PATH, "schema")
    assert min(v for k, v in schema["materials"].items() if k.startswith("bulk|")) >= 10


def test_motor_id_without_version_suffix_is_accepted():
    lk = {"AeroTech-F50T-v1": {**next(iter(LOOKUP.values())), "designation": "F50T"}}
    d = design()
    field(nodes(d, "motor")[0], "motor_id")["value"] = "AeroTech-F50T"
    assert R.score(answer(d), {}, lookup=lk, flight=False)["gate"] != "motors"


def _fake_flight(warn):
    return {"apogee_m": 300.0, "flight_time_s": 40.0, "max_velocity_ms": 90.0, "rail_exit_ms": 20.0,
            "stability_rail_cal": 2.0, "stability_min_burn_cal": 2.0, "deployment_velocity_ms": 5.0,
            "branches": [{"name": "Stage", "deployed": True, "ground": True, "landing_ms": 4.0}],
            "events": [{"branch": 0, "type": "SIM_WARN", "t": 1.2, "data": warn}] if warn else []}


@pytest.mark.parametrize("warn,ok", [
    (None, True),
    ('Recovery device deployment at high speed (38.2 m/s):  "Parachute"', True),     # normal for hobby rockets
    ('Recovery device deployment at high speed (262 m/s):  "Parachute"', False),     # shreds the chute
])
def test_fast_deployment_fails_flight(monkeypatch, warn, ok):
    monkeypatch.setattr(R._OR, "fly", lambda path, seed=42: _fake_flight(warn))
    r = R.score(answer(design()), {"max_touchdown_ms": 6.0}, lookup=LOOKUP)
    assert (r["gate"] is None) == ok, r["reasons"]
    assert r["metrics"]["apogee_m"] == 300.0          # metrics are kept even when the flight fails


# ------------------------------------------------------------------ ranges are wide, but cheats stay closed
def _schema_problem(tag, fld, value, attrs=None):
    d = design()
    body = nodes(d, tag)[0]
    f = next((c for c in body["children"] if fld in c), None)
    if f is None:
        f = {fld: {}}
        body["children"].append(f)
    f[fld]["value"] = value
    if attrs is not None:
        f[fld]["attrs"] = attrs
    return [x for x in run(d)["reasons"] if fld in x]


def test_zero_only_fields_get_a_physical_range():
    schema = R._load(R.SCHEMA_PATH, "schema")
    rule = schema["nodes"]["tubefinset"]["fields"]["axialoffset"]
    assert R.value_problem(rule, -0.002) is None and R.value_problem(rule, 50.0)


def test_parachute_cd_upper_bound_still_blocks_the_drag_cheat():
    assert _schema_problem("parachute", "cd", 50.0)


def test_paper_thin_walls_still_fail():
    schema = R._load(R.SCHEMA_PATH, "schema")
    rule = schema["nodes"]["transition"]["fields"]["thickness"]
    assert R.value_problem(rule, 1e-8) and R.value_problem(rule, 0.002) is None


def test_fin_tab_bottom_is_accepted():
    schema = R._load(R.SCHEMA_PATH, "schema")
    rule = schema["nodes"]["freeformfinset"]["fields"]["tabposition"]["attrs"]["relativeto"]
    assert R.value_problem(rule, "bottom") is None and R.value_problem(rule, "sideways")


def test_openrocket_build_error_is_a_geometry_fail(monkeypatch):
    monkeypatch.setattr(R._OR, "fly", lambda path, seed=42: {"error": "IllegalStateException: not compatible"})
    r = R.score(answer(design()), {}, lookup=LOOKUP)
    assert (r["gate"], r["score"]) == ("geometry", -0.8)
