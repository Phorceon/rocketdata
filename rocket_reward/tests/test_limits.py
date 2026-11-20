"""Tests for stage 4 (limit_checks.py) and the numbers in limits.py.

A tiny fake motor table is used instead of the real one, and the "which
motors fly" helper from motors.py is replaced by a small local version, so
these tests depend only on limits.py and limit_checks.py.
"""
from __future__ import annotations

import ast
import copy
import json
import math
import time
from pathlib import Path

import pytest

from answers import design_of
from rocket_reward import ladder
from rocket_reward import limit_checks as LC
from rocket_reward import limits as L
from rocket_reward import tree as T
from rocket_reward.tree import find_all as nodes
from rocket_reward.ladder import stage_score

PKG = Path(LC.__file__).resolve().parent


# ------------------------------------------------------------------ helpers

class FakeTable:
    """The two motor-table calls stage 4 uses: resolve() and get()."""

    def __init__(self, entries: dict) -> None:
        self.entries = entries

    def resolve(self, motor_id, manufacturer=None, designation=None):
        if isinstance(motor_id, str) and motor_id.strip():
            low = motor_id.strip().lower()
            for k in self.entries:
                if k.lower() in (low, low + "-v1"):
                    return k
            return None
        if motor_id is not None:
            return None
        hits = [k for k, e in self.entries.items()
                if e["manufacturer"] == manufacturer and e["designation"] == designation]
        return hits[0] if len(hits) == 1 else None

    def get(self, key):
        return self.entries[key]


TABLE = FakeTable({
    "Big-O30000-v1": {"manufacturer": "Big", "designation": "O30000", "diameter_m": 0.15,
                      "length_m": 1.0, "total_impulse_ns": 30000.0},
    "Small-C6-v1": {"manufacturer": "Small", "designation": "C6", "diameter_m": 0.018,
                    "length_m": 0.07, "total_impulse_ns": 9.0},
})


def _simple_flown_motors(root):
    """Motors in any motor mount whose configid is the rocket's default one."""
    rocket = T.child(root, "rocket") if T.is_node(root) else None
    if rocket is None:
        return []
    cid = None
    for c in T.children_of(rocket):
        if T.tag_of(c) == "motorconfiguration":
            a = T.attrs_of(c)
            if cid is None or a.get("default") in (True, "true"):
                cid = a.get("configid")
    return [n for n in T.walk_nodes(rocket)
            if T.tag_of(n) == "motor" and T.attrs_of(n).get("configid") == cid]


@pytest.fixture(autouse=True)
def _local_flown_motors(monkeypatch):
    monkeypatch.setattr(LC, "flown_motors", _simple_flown_motors)




@pytest.fixture()
def gold(gold_rows):
    """A fresh copy of the first reference design (a fiberglass M-motor rocket)."""
    return copy.deepcopy(design_of(gold_rows[0]["answer"], root_only=True))


def set_field(root, comp_tag, field, value, nth=0):
    """Set `field` of the nth `comp_tag` component, adding the field if missing."""
    comp = nodes(root, comp_tag)[nth]
    for c in T.children_of(comp):
        if T.tag_of(c) == field:
            c[field] = {"value": value}
            return root
    comp[comp_tag].setdefault("children", []).insert(0, {field: {"value": value}})
    return root


def first_tube_subcomponents(root):
    return T.child(nodes(root, "bodytube")[0], "subcomponents")["subcomponents"]["children"]


def check(root):
    return LC.check_limits(root, TABLE)


def fails_with(root, *words):
    r = check(root)
    assert not r.passed, "expected a limit failure"
    text = " ".join(r.reasons)
    for w in words:
        assert w in text, f"{w!r} not in {r.reasons}"
    assert 0.0 <= r.credit < 1.0
    return r


# ------------------------------------------------------------------ the reference designs

def test_every_reference_design_passes(gold_rows):
    for row in gold_rows:
        r = check(design_of(row["answer"], root_only=True))
        assert r.passed, (row["id"], r.reasons)
        assert r.credit == 1.0 and r.stage == "limits"


def test_model_answers_give_normal_results(model_rows):
    seen = {}
    for row in model_rows:
        d = design_of(row["content"], root_only=True)
        if d is None:
            continue
        r = check(d)
        assert 0.0 <= r.credit <= 1.0
        seen[row["id"]] = r
    # 33 (35 before 2026-11-19: a mass override no longer excuses the unknown
    # materials of row-013 and row-023)
    assert sum(r.passed for r in seen.values()) >= 33
    # fins five times the body width, used as air brakes
    assert "times its width" in " ".join(seen["row-017-df7ff989"].reasons)
    # a component type OpenRocket does not have
    assert "apogeerocketcomputer" in " ".join(seen["row-007-5e9884b6"].reasons)


# ------------------------------------------------------------------ fins

def test_fin_count_limits(gold):
    for bad in (0, 9, 1e9, 2.5, -3):
        d = set_field(copy.deepcopy(gold), "trapezoidfinset", "fincount", bad)
        fails_with(d, "fin")
    for ok in (1, 4, 8):
        d = set_field(set_field(copy.deepcopy(gold), "trapezoidfinset", "fincount", ok),
                      "trapezoidfinset", "instancecount", ok)
        assert check(d).passed


def test_a_billion_fins_is_quick(gold):
    d = set_field(set_field(gold, "trapezoidfinset", "fincount", 10 ** 9),
                  "trapezoidfinset", "instancecount", "1000000000")
    t0 = time.perf_counter()
    r = fails_with(d, "1e+09")
    assert time.perf_counter() - t0 < 1.0
    assert r.credit > 0


def test_cant_angle(gold):
    for bad in (20, -20):
        fails_with(set_field(copy.deepcopy(gold), "trapezoidfinset", "cant", bad), "cant", "15 deg")
    assert check(set_field(copy.deepcopy(gold), "trapezoidfinset", "cant", -15)).passed


def test_fin_thickness(gold):
    r = fails_with(set_field(copy.deepcopy(gold), "trapezoidfinset", "thickness", 0.0001), "0.1 mm", "0.5 mm")
    # the thinnest real reference fins (1.0 mm) pass
    assert check(set_field(copy.deepcopy(gold), "trapezoidfinset", "thickness", 0.001)).passed
    # closer to the limit is never worse
    closer = check(set_field(copy.deepcopy(gold), "trapezoidfinset", "thickness", 0.0004))
    assert closer.credit > r.credit


def test_fin_span_against_body_width(gold):
    # the reference body is 157 mm wide; fins reaching 1 m out are air brakes
    r = fails_with(set_field(gold, "trapezoidfinset", "height", 1.0), "times its width")
    assert r.credit > 0


def test_fin_chord(gold):
    fails_with(set_field(gold, "trapezoidfinset", "rootchord", 3.0), "rootchord", "3 m")


def _add_freeform(root, points):
    fin = {"freeformfinset": {"children": [
        {"fincount": {"value": 3}}, {"thickness": {"value": 0.003}},
        {"finpoints": {"children": [{"point": {"attrs": {"x": x, "y": y}}} for x, y in points]}}]}}
    first_tube_subcomponents(root).append(fin)
    return root


def test_freeform_fin_points(gold):
    good = [(0.0, 0.0), (0.05, 0.05), (0.1, 0.0)]
    assert check(_add_freeform(copy.deepcopy(gold), good)).passed
    fails_with(_add_freeform(copy.deepcopy(gold), [(0.0, 0.0), (5.0, 0.05), (0.1, 0.0)]), "outline point")
    fails_with(_add_freeform(copy.deepcopy(gold), [(i * 1e-4, 0.01) for i in range(1000)]), "points")
    fails_with(_add_freeform(copy.deepcopy(gold), [(0.0, 0.0), ("x", None), (0.1, 0.0)]), "usable")


# ------------------------------------------------------------------ shell, recovery, mass

def _drop_tag(root, tag):
    for n in T.walk_nodes(root):
        kids = n[T.tag_of(n)].get("children") if isinstance(n[T.tag_of(n)], dict) else None
        if isinstance(kids, list):
            kids[:] = [c for c in kids if not (T.is_node(c) and T.tag_of(c) == tag)]
    return root


def test_wall_thickness(gold):
    bare = _drop_tag(copy.deepcopy(gold), "overridemass")
    thin = fails_with(set_field(copy.deepcopy(bare), "bodytube", "thickness", 0.00001), "wall", "0.13 mm")
    # the word "filled" is OpenRocket's solid part
    assert check(set_field(copy.deepcopy(bare), "bodytube", "thickness", "filled")).passed
    assert check(set_field(copy.deepcopy(bare), "nosecone", "thickness", "filled")).passed
    # a 0 mm wall is a shell with no mass: never better than a too-thin wall
    for zero in (0, 0.0, "0", "0.0f"):
        r = fails_with(set_field(copy.deepcopy(bare), "bodytube", "thickness", zero), "0 mm")
        assert r.credit <= thin.credit
    # a mass override excuses no wall (the cleaning removes every override before stage 4)
    for wall in (0.0, 0.00001):
        d = set_field(set_field(copy.deepcopy(bare), "bodytube", "thickness", wall), "bodytube", "overridemass", 1.2)
        fails_with(d, "wall")
    stage = next(s for s in nodes(bare, "stage") if T.child(s, "subcomponents") is not None)
    stage["stage"]["children"][:0] = [{"overridemass": {"value": 9.0}}, {"overridesubcomponents": {"value": 1}}]
    fails_with(set_field(copy.deepcopy(bare), "bodytube", "thickness", 0.0), "0 mm")


def test_tube_radius_and_length(gold):
    fails_with(set_field(copy.deepcopy(gold), "bodytube", "radius", 0.5), "radius", "150 mm")
    fails_with(set_field(copy.deepcopy(gold), "bodytube", "radius", 0.001), "radius", "2.5 mm")
    fails_with(set_field(copy.deepcopy(gold), "bodytube", "length", 10.0), "length", "3.66 m")
    # "auto" radii are taken from the neighbouring part
    for auto in ("auto", "auto 0.025"):
        assert check(set_field(copy.deepcopy(gold), "bodytube", "radius", auto)).passed
    # Changed on purpose (2026-11-19): a written 0 is not "auto" in OpenRocket but a
    # tube of no width, so it fails; it passes only on an empty tube of length 0
    fails_with(set_field(copy.deepcopy(gold), "bodytube", "radius", 0), "radius", "no size")
    empty = set_field(set_field(copy.deepcopy(gold), "bodytube", "radius", 0), "bodytube", "length", 0.0)
    assert not any("radius" in r for r in check(empty).reasons)


def test_nose_cone_and_transition_sizes(gold):
    fails_with(set_field(copy.deepcopy(gold), "nosecone", "length", 5.0), "nosecone", "length")
    fails_with(set_field(copy.deepcopy(gold), "nosecone", "aftradius", 0.4), "aftradius")
    tr = {"transition": {"children": [{"length": {"value": 3.0}}, {"aftradius": {"value": 0.5}}]}}
    # (the motor configuration also has "stage" children; take the real stage)
    stage = next(s for s in nodes(gold, "stage") if T.child(s, "subcomponents") is not None)
    T.child(stage, "subcomponents")["subcomponents"]["children"].append(tr)
    fails_with(gold, "transition", "length", "aftradius")


def test_parachute_limits(gold):
    fails_with(set_field(copy.deepcopy(gold), "parachute", "cd", 50), "cd", "2.9")
    fails_with(set_field(copy.deepcopy(gold), "parachute", "cd", 0.2), "cd", "0.6")
    fails_with(set_field(copy.deepcopy(gold), "parachute", "diameter", 30.0), "diameter", "6.1 m")
    fails_with(set_field(copy.deepcopy(gold), "parachute", "diameter", 0.05), "diameter")
    assert check(set_field(copy.deepcopy(gold), "parachute", "cd", "auto")).passed
    near = check(set_field(copy.deepcopy(gold), "parachute", "cd", 3.2))
    far = check(set_field(copy.deepcopy(gold), "parachute", "cd", 50))
    assert near.credit > far.credit


def test_streamer_limits(gold):
    s = {"streamer": {"children": [{"striplength": {"value": 20.0}}, {"stripwidth": {"value": 2.0}},
                                   {"cd": {"value": 5.0}}]}}
    first_tube_subcomponents(gold).append(s)
    fails_with(gold, "striplength", "stripwidth", "cd")


def test_mass_component(gold):
    fails_with(set_field(copy.deepcopy(gold), "masscomponent", "mass", 100.0), "mass", "20 kg")
    fails_with(set_field(copy.deepcopy(gold), "masscomponent", "mass", -1.0), "negative")


def test_negative_size(gold):
    fails_with(set_field(gold, "bodytube", "length", -0.3), "negative")


# ------------------------------------------------------------------ types, numbers, impulse

def test_invented_component_type_fails(gold):
    first_tube_subcomponents(gold).append({"antigravityunit": {"children": [{"mass": {"value": 1}}]}})
    fails_with(gold, "antigravityunit", "not a known")


def test_unknown_small_setting_is_fine(gold):
    set_field(gold, "bodytube", "colourname", "bright red")
    set_field(gold, "bodytube", "somesetting", 3)
    assert check(gold).passed


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), "NaN", "-Infinity", "1e999", 10 ** 400])
def test_numbers_must_be_finite(gold, bad):
    fails_with(set_field(gold, "bodytube", "length", bad), "not a finite number")


def test_non_finite_attribute_fails(gold):
    nodes(gold, "axialoffset")[0]["axialoffset"]["attrs"] = {"method": "top", "scale": float("nan")}
    fails_with(gold, "attribute", "not a finite number")


def _put_motor(root, motor_id, cluster=None):
    mount = nodes(root, "motor")[0]
    for c in T.children_of(mount):
        if T.tag_of(c) == "motor_id":
            c["motor_id"] = {"value": motor_id}
    if cluster:
        tube = next(t for t in nodes(root, "innertube") + nodes(root, "bodytube")
                    if T.child(t, "motormount") is not None)
        kids = tube[T.tag_of(tube)]["children"]
        kids[:] = [c for c in kids if T.tag_of(c) != "clusterconfiguration"]
        kids.insert(0, {"clusterconfiguration": {"value": cluster}})
    return root


def test_total_impulse(gold):
    r = check(_put_motor(copy.deepcopy(gold), "Big-O30000-v1"))
    assert r.passed and r.info["total_impulse_ns"] == 30000.0
    r = fails_with(_put_motor(copy.deepcopy(gold), "big-o30000", cluster="double"),
                   "total impulse", "6e+04 Ns", "4.096e+04 Ns")
    # an unknown motor is stage 3's business, not this stage's
    assert check(_put_motor(copy.deepcopy(gold), "Nobody-Z1")).passed


def _materials_named(root, comp_tag, name, density=None, drop_override=True):
    """Rename the material of every `comp_tag` part (and drop its own mass
    override, so the name matters)."""
    for comp in nodes(root, comp_tag):
        kids = comp[comp_tag]["children"]
        if drop_override:
            kids[:] = [c for c in kids if T.tag_of(c) != "overridemass"]
        for c in kids:
            if T.tag_of(c) == "material":
                c["material"]["value"] = name
                if density is not None:
                    c["material"]["attrs"]["density"] = density
    return root


def test_unknown_material_name_fails_and_suggests_a_known_one(gold):
    r = fails_with(_materials_named(gold, "bodytube", "Paper, spiral kraft glassine, RK Tubes"),
                   "'Paper, spiral kraft glassine, RK Tubes'", "not in the material table of bulk materials",
                   "for example 'Paper", "kg/m3")
    assert r.credit == pytest.approx(1 / 2)   # one yes/no violation


@pytest.mark.parametrize("name", ["Bronze", "Inconel", "Woods", "Custom", "RS: Hexsonic"])
def test_unknown_material_name_with_no_close_spelling_points_to_the_list(gold, name):
    """No absurd 'did you mean' ('Bronze' once suggested 'Oak (Brown)'): a name
    spelled like no table name gets a pointer to the list instead."""
    r = fails_with(_materials_named(gold, "bodytube", name), f"material {name!r}",
                   "no bulk material in OpenRocket's list is spelled like it", "material_table.json")
    assert not any("for example" in x for x in r.reasons)
    assert r.credit == pytest.approx(1 / 2)   # the same violation as with a suggestion


def test_known_material_name_passes_in_any_case_or_with_rs_prefix(gold):
    for name in ("cardboard", "RS: Cardboard", "  Cardboard "):
        assert check(_materials_named(copy.deepcopy(gold), "bodytube", name)).passed


def test_each_distinct_unknown_name_counts_once_and_at_most_three(gold):
    one = check(_materials_named(copy.deepcopy(gold), "bodytube", "Unobtainium"))
    assert one.credit == pytest.approx(1 / 2)
    same = _materials_named(copy.deepcopy(gold), "bodytube", "Unobtainium")
    _materials_named(same, "nosecone", "unobtainium ")           # the same name up to case and spacing
    assert check(same).credit == pytest.approx(1 / 2)
    many = copy.deepcopy(gold)
    for i, tag in enumerate(("bodytube", "nosecone", "centeringring", "innertube", "bulkhead")):
        _materials_named(many, tag, f"Madeup{i}")
    r = check(many)
    assert r.credit == pytest.approx(1 / 4)                      # three counted
    assert any("more unknown material name(s) are not counted" in x for x in r.reasons)


def test_unknown_name_counts_also_on_a_part_with_a_mass_override(gold):
    """A mass override no longer excuses a material: the cleaning removes it."""
    d = copy.deepcopy(gold)
    tube = nodes(d, "bodytube")[0]
    tube["bodytube"]["children"].append({"overridemass": {"value": 0.5}})
    for c in tube["bodytube"]["children"]:
        if T.tag_of(c) == "material":
            c["material"]["value"] = "Unobtainium"
    r = fails_with(d, "Unobtainium", "not in the material table")
    assert "notes" not in r.info


def test_density_bounds_apply_only_to_unknown_names(gold):
    # a known name: the cleaning gives it the table density, so its written one is not judged
    assert check(_materials_named(copy.deepcopy(gold), "bodytube", "Cardboard", density=1e-9)).passed
    r = fails_with(_materials_named(copy.deepcopy(gold), "bodytube", "Unobtainium", density=1e-9),
                   "density", "kg/m3", "Unobtainium")
    assert len(r.reasons) >= 2


def test_no_material_names_are_not_unknown(gold):
    for name in ("", "RS:", "  "):
        assert check(_materials_named(copy.deepcopy(gold), "bodytube", name)).passed


# ------------------------------------------------------------------ hostile trees

def test_hostile_shapes_do_not_crash(gold):
    junk = copy.deepcopy(gold)
    first_tube_subcomponents(junk).extend([1, "x", None, [], {}, {"a": 1, "b": 2}, {"bodytube": 5},
                                          {"bodytube": {"children": "no"}}])
    nodes(junk, "trapezoidfinset")[0]["trapezoidfinset"]["children"].append({"fincount": {"value": [1, 2]}})
    for root in (None, 5, "text", [], {}, {"openrocket": None}, {"openrocket": {"children": 7}},
                 {"rocket": {}}, junk):
        r = check(root)
        assert 0.0 <= r.credit <= 1.0


def test_deep_nesting_is_quick():
    inner = {"bodytube": {"children": [{"length": {"value": 0.3}}]}}
    for _ in range(5000):
        inner = {"bodytube": {"children": [{"subcomponents": {"children": [inner]}}]}}
    root = {"openrocket": {"children": [{"rocket": {"children": [
        {"subcomponents": {"children": [{"stage": {"children": [
            {"subcomponents": {"children": [inner]}}]}}]}}]}}]}}
    t0 = time.perf_counter()
    r = check(root)
    assert time.perf_counter() - t0 < 2.0
    # 5002 parts: only the part-count limit is broken (log2(5002 / 150) is past the cap)
    assert r.reasons == [f"the number of parts in the design (every component inside the rocket) is 5002 parts, "
                         f"more than the limit of {L.COMPONENTS_MAX} parts"]
    assert r.credit == pytest.approx(ladder.credit_from_violations([ladder.MAX_VIOLATION]))


def test_failing_stays_inside_the_band(gold):
    d = set_field(gold, "parachute", "cd", 1e300)
    r = fails_with(d, "cd")
    s = stage_score("limits", r.credit)
    assert 0.30 <= s <= 0.38


# ------------------------------------------------------------------ limits.py itself

def test_every_limit_names_its_source():
    """Each upper-case constant in limits.py is followed by a comment on its line
    (or, for a multi-line value, a comment block just above it). The second of
    a min/max pair may share the note of the line just above it (a NAME_MIN
    line followed by NAME_MAX)."""
    src = (PKG / "limits.py").read_text(encoding="utf-8")
    lines = src.splitlines()
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) \
                and node.targets[0].id.isupper():
            line = lines[node.lineno - 1]
            above = lines[node.lineno - 2] if node.lineno >= 2 else ""
            pair = (node.targets[0].id.endswith("_MAX") and "#" in above
                    and above.startswith(node.targets[0].id[:-4] + "_MIN"))
            assert "#" in line or above.lstrip().startswith("#") or pair, node.targets[0].id


def test_limits_are_sane_numbers():
    for name in dir(L):
        v = getattr(L, name)
        if name.isupper() and isinstance(v, (int, float)):
            # A lowest stability margin of 0 calibres is a real limit ("never
            # unstable"); every other limit is a positive number.
            low_ok = 0 if name.endswith("_STABILITY_MIN_CAL") else None
            assert math.isfinite(v) and (v > 0 or v == low_ok), name
    assert L.FIN_COUNT_MIN <= L.FIN_COUNT_MAX
    assert L.CHUTE_CD_MIN < L.CHUTE_CD_MAX
    assert L.CHUTE_DIAMETER_MIN_M < L.CHUTE_DIAMETER_MAX_M
    assert L.TOTAL_IMPULSE_MAX_NS == 40960.0


# ------------------------------------------------------------------ part counts and small outside parts

def _lug(radius=0.0005, length=0.002, instances=None):
    kids = [{"radius": {"value": radius}}, {"length": {"value": length}}, {"thickness": {"value": 0.0002}}]
    if instances is not None:
        kids.append({"instancecount": {"value": instances}})
    return {"launchlug": {"children": kids}}


def _button(diameter=0.01, height=0.01, instances=None):
    kids = [{"outerdiameter": {"value": diameter}}, {"height": {"value": height}}]
    if instances is not None:
        kids.append({"instancecount": {"value": instances}})
    return {"railbutton": {"children": kids}}


def _mass(n):
    return [{"masscomponent": {"children": [{"mass": {"value": 0.001}}, {"radius": {"value": 0.005}}]}}
            for _ in range(n)]


def test_part_count_limit(gold):
    have = check(gold).info["components"]
    at = copy.deepcopy(gold)
    first_tube_subcomponents(at).extend(_mass(L.COMPONENTS_MAX - have))
    assert check(at).passed and check(at).info["counts"]["parts"] == L.COMPONENTS_MAX
    over = copy.deepcopy(gold)
    first_tube_subcomponents(over).extend(_mass(2 * L.COMPONENTS_MAX - have))
    r = fails_with(over, "number of parts", f"{2 * L.COMPONENTS_MAX} parts", f"limit of {L.COMPONENTS_MAX} parts")
    assert r.credit == pytest.approx(1 / 2)      # twice the limit costs 1


def test_launch_lug_and_rail_button_counts(gold):
    ok = copy.deepcopy(gold)
    first_tube_subcomponents(ok).extend([_lug() for _ in range(L.LAUNCH_LUG_COUNT_MAX)]
                                        + [_button() for _ in range(L.RAIL_BUTTON_COUNT_MAX)])
    assert check(ok).passed, check(ok).reasons
    many = copy.deepcopy(gold)
    first_tube_subcomponents(many).extend([_lug() for _ in range(4 * L.LAUNCH_LUG_COUNT_MAX)])
    r = fails_with(many, "number of launch lugs", "32 lugs", "limit of 8 lugs")
    assert r.credit == pytest.approx(1 / 3)      # four times the limit costs 2
    copies = copy.deepcopy(gold)
    first_tube_subcomponents(copies).append(_button(instances=2 * L.RAIL_BUTTON_COUNT_MAX))
    fails_with(copies, "number of rail buttons", "16 buttons", "instance count")


def test_more_lugs_never_score_better(gold):
    last = 1.0
    for n in (8, 9, 12, 20, 40, 80, 400):
        d = copy.deepcopy(gold)
        first_tube_subcomponents(d).extend([_lug() for _ in range(n)])
        credit = check(d).credit
        assert credit <= last + 1e-12, n
        last = credit


def test_part_instances_limit(gold):
    assert check(set_field(copy.deepcopy(gold), "centeringring", "instancecount", L.PART_INSTANCES_MAX)).passed
    fails_with(set_field(copy.deepcopy(gold), "centeringring", "instancecount", 1000), "centeringring #1's instance count",
               "1000 copies", "limit of 8 copies")


@pytest.mark.parametrize("part, words", [
    (_lug(radius=2 * L.LAUNCH_LUG_RADIUS_MAX_M), ("launchlug #1's radius", "40 mm", "20 mm")),
    (_lug(length=2 * L.LAUNCH_LUG_LENGTH_MAX_M), ("launchlug #1's length", "0.6 m", "0.3 m")),
    (_button(diameter=2 * L.RAIL_BUTTON_DIAMETER_MAX_M), ("railbutton #1's outerdiameter", "80 mm", "40 mm")),
    (_button(height=2 * L.RAIL_BUTTON_HEIGHT_MAX_M), ("railbutton #1's height", "60 mm", "30 mm"))])
def test_launch_lug_and_rail_button_sizes(gold, part, words):
    d = copy.deepcopy(gold)
    first_tube_subcomponents(d).append(part)
    assert fails_with(d, *words).credit == pytest.approx(1 / 2)


def test_tube_fins_no_wider_than_the_body(gold):
    body = 0.05
    set_field(gold, "bodytube", "radius", body)

    def with_tube_fins(radius):
        d = copy.deepcopy(gold)
        first_tube_subcomponents(d).append({"tubefinset": {"children": [
            {"fincount": {"value": 4}}, {"radius": {"value": radius}}, {"length": {"value": 0.2}},
            {"thickness": {"value": 0.001}}]}})
        return d

    assert check(with_tube_fins("auto")).passed
    assert check(with_tube_fins(body)).passed
    r = fails_with(with_tube_fins(3 * body), "tubefinset #1's tubes", "3 times", "limit 1 times")
    assert r.credit == pytest.approx(1 / (1 + math.log2(3)))


FOAM = "Styrofoam (generic EPS)"


def test_foam_film_walls_fail(gold):
    d = _materials_named(copy.deepcopy(gold), "bodytube", FOAM)
    for i in range(len(nodes(d, "bodytube"))):
        set_field(d, "bodytube", "thickness", L.WALL_MIN_M, nth=i)
    r = fails_with(d, "bodytube #1's wall weighs", "kg/m2", FOAM, "limit of 0.045 kg/m2")
    assert r.credit < 0.3
    # the same wall in paper passes
    paper = _materials_named(copy.deepcopy(d), "bodytube", "Paper (office)")
    assert check(paper).passed, check(paper).reasons


def test_foam_film_fins_fail(gold):
    d = _materials_named(copy.deepcopy(gold), "trapezoidfinset", FOAM)
    set_field(d, "trapezoidfinset", "thickness", L.FIN_THICKNESS_MIN_M)
    fails_with(d, "trapezoidfinset #1's fins weigh", FOAM, "limit of 0.12 kg/m2")
    balsa = _materials_named(copy.deepcopy(gold), "trapezoidfinset", "Balsa")
    set_field(balsa, "trapezoidfinset", "thickness", 0.0016)     # 1/16 inch balsa, the lightest reference fin
    assert check(balsa).passed, check(balsa).reasons


def test_lighter_wall_is_never_better(gold):
    """Thinner foam never scores better than thicker foam, across the thickness limit too."""
    last = 0.0
    for wall in (0.0, 0.00001, 0.0001, 0.00013, 0.0005, 0.001, 0.0025, 0.005):
        d = _materials_named(copy.deepcopy(gold), "bodytube", FOAM)
        for i in range(len(nodes(d, "bodytube"))):
            set_field(d, "bodytube", "thickness", wall, nth=i)
        credit = check(d).credit
        assert credit >= last - 1e-12, wall
        last = credit
    assert last == 1.0


def test_areal_density_is_judged_also_on_parts_with_a_mass_override(gold):
    """A mass override no longer excuses a foam wall: the cleaning removes it."""
    d = _materials_named(copy.deepcopy(gold), "bodytube", FOAM, drop_override=False)
    for tube in nodes(d, "bodytube"):
        tube["bodytube"]["children"].append({"overridemass": {"value": 0.2}})
    assert any("weighs" in x for x in check(d).reasons)
