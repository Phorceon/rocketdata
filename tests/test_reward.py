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
@pytest.mark.parametrize("bad", ["NaN", "Infinity", -0.2, 50.0])
def test_bad_numbers_fail_geometry(bad):
    d = design()
    field(nodes(d, "bodytube")[0], "length")["value"] = bad
    r = run(d)
    assert r["gate"] == "geometry" and -0.8 <= r["score"] < -0.5


def _fake_fly(sim):
    return lambda path, seed=42, name="reward0": copy.deepcopy(sim)


def test_openrocket_warnings_decide_structure(monkeypatch):
    """Unknown parts, misplaced parts and bad words are OpenRocket's call: a skipped part fails,
    an unknown field (which OpenRocket ignores) is only noted."""
    ok = _fake_flight(None)
    monkeypatch.setattr(R._OR, "fly", _fake_fly({**ok, "load_warnings": ["Unknown element antigravity, ignoring."]}))
    r = R.score(answer(design()), {}, lookup=LOOKUP)
    assert r["gate"] == "geometry" and "antigravity" in r["reasons"][0]
    monkeypatch.setattr(R._OR, "fly", _fake_fly(
        {**ok, "load_warnings": ["Unknown parameter type 'warpdrive' for Body Tube, ignoring."]}))
    r = R.score(answer(design()), {}, lookup=LOOKUP)
    assert r["gate"] is None and "warpdrive" in r["notes"]["ignored_fields"][0]


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
    R.gate_geometry(root, stages, R._load(R.MATERIALS_PATH, "materials"))
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
    m = {"apogee_m": 300.0, "flight_time_s": 40.0, "landing_ms": [4.0], "landing_limit_ms": 6.0}
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
        R._load(REPO / "no" / "such.json", "materials")


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
    mats = R._load(R.MATERIALS_PATH, "materials")
    d = design()
    field(nodes(d, "bodytube")[0], "material")["value"] = "Paper, spiral kraft glassine, made-up grade, bulk"
    root, _ = R.gate_format(answer(d), "stop")
    assert R.material_problems(root, mats) == []
    tube = next(n for n in root.walk() if n.tag == "bodytube")
    assert 500 < tube.get("material").attrs["density"] < 1500


def test_no_bulk_material_is_lighter_than_foam():
    mats = R._load(R.MATERIALS_PATH, "materials")
    assert min(v for k, v in mats["materials"].items() if k.startswith("bulk|")) >= 10


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
    monkeypatch.setattr(R._OR, "fly", _fake_fly(_fake_flight(warn)))
    r = R.score(answer(design()), {"max_touchdown_ms": 6.0}, lookup=LOOKUP)
    assert (r["gate"] is None) == ok, r["reasons"]
    assert r["metrics"]["apogee_m"] == 300.0          # metrics are kept even when the flight fails


# ------------------------------------------------------------------ physical limits, not old designs
def test_new_kinds_of_values_pass():
    """Values no reference design used, but real rockets can have."""
    d = design()
    field(nodes(d, "trapezoidfinset")[0], "cant")["value"] = 2.0
    for c in nodes(d, "parachute")[0]["children"]:
        if "diameter" in c:
            c["diameter"]["value"] = 5.5
    assert run(d)["gate"] == "not flown"


@pytest.mark.parametrize("tag,fld,value,why", [
    ("parachute", "cd", 50.0, "outside"),            # the soft-landing cheat
    ("parachute", "diameter", 30.0, "outside"),      # no chute that big exists
    ("bodytube", "thickness", 0.00001, "wall"),      # the light-rocket cheat
    ("bodytube", "radius", 2.0, "outside"),          # a 4 m tube
    ("trapezoidfinset", "fincount", 40, "outside"),
])
def test_physical_limits_block_cheats(tag, fld, value, why):
    d = design()
    body = nodes(d, tag)[0]
    f = next((c for c in body["children"] if fld in c), None)
    if f is None:
        f = {fld: {}}
        body["children"].append(f)
    f[fld]["value"] = value
    r = run(d)
    assert r["gate"] == "geometry" and any(why in x for x in r["reasons"]), r["reasons"]


def test_openrocket_build_error_is_a_geometry_fail(monkeypatch):
    monkeypatch.setattr(R._OR, "fly", _fake_fly({"error": "IllegalStateException: not compatible"}))
    r = R.score(answer(design()), {}, lookup=LOOKUP)
    assert (r["gate"], r["score"]) == ("geometry", -0.8)


# ------------------------------------------------------------------ partial credit and three flights
def test_tiers_never_overlap():
    d = design()
    field(nodes(d, "trapezoidfinset")[0], "thickness")["value"] = 0.0005
    one = run(d)["score"]
    assert -0.8 < one < -0.5                           # one problem: some credit, still below any flight fail
    for t in ("length",):
        field(nodes(d, "bodytube")[0], t)["value"] = 50.0
    assert run(d)["score"] < one                       # more problems, less credit


def test_unsafe_flight_gets_partial_credit_below_zero(monkeypatch):
    sim = _fake_flight(None)
    sim["branches"][0]["landing_ms"] = 6.5             # just over the 6 m/s limit
    monkeypatch.setattr(R._OR, "fly", _fake_fly(sim))
    near = R.score(answer(design()), {"max_touchdown_ms": 6.0}, lookup=LOOKUP)
    sim["branches"][0]["landing_ms"] = 30.0            # a lawn dart
    far = R.score(answer(design()), {"max_touchdown_ms": 6.0}, lookup=LOOKUP)
    assert near["gate"] == far["gate"] == "flight" and -0.5 <= far["score"] < near["score"] < 0


def test_worst_of_three_flights_counts(monkeypatch):
    good, bad = _fake_flight(None), _fake_flight(None)
    bad["branches"][0]["landing_ms"] = 9.0
    calls = iter([good, good, bad])
    monkeypatch.setattr(R._OR, "fly", lambda path, seed=42, name="reward0": copy.deepcopy(next(calls)))
    assert R.score(answer(design()), {"max_touchdown_ms": 6.0}, lookup=LOOKUP)["gate"] == "flight"


def test_a_bigger_chute_than_needed_earns_nothing(monkeypatch):
    req = {"max_touchdown_ms": 6.0}
    scores = []
    for v in (5.0, 2.0):                               # 2 m/s = a needlessly big chute
        sim = _fake_flight(None)
        sim["branches"][0]["landing_ms"] = v
        monkeypatch.setattr(R._OR, "fly", _fake_fly(sim))
        scores.append(R.score(answer(design()), req, lookup=LOOKUP)["parts"]["landing"])
    assert scores[0] == 1.0 and scores[1] < 1.0


def test_three_simulations_in_three_winds():
    root, _ = R.gate_format(answer(design()), "stop")
    R.gate_motors(root, LOOKUP)
    x = R.to_ork(root, {"wind_ms": 4.0})
    assert [f"reward{i}" for i in range(3)] == [n for n in __import__("re").findall(r"<name>(reward\d)</name>", x)]
    assert "<windaverage>2.0</windaverage>" in x and "<windaverage>6.0</windaverage>" in x
