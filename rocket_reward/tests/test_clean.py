"""Tests for clean.py: the cleaned copy the reward flies (DESIGN.md section 5).

A tiny fake motor table is used instead of the real one.
"""
from __future__ import annotations

import copy
import json

import pytest

from answers import design_of
from rocket_reward.clean import DRAG_OVERRIDE_TAGS, clean_design
from rocket_reward.materials import default_material_table, means_no_material
from rocket_reward.ork import FILE_VERSION
from rocket_reward.tree import (MATERIAL_TAGS, attrs_of, child as kid, child_value, rocket_of as rocket, tag_of,
                                value_of, walk_nodes as walk)


class FakeTable:
    """The two motor-table calls clean.py uses: resolve() and get()."""

    def __init__(self, entries: dict) -> None:
        self.entries = entries

    def resolve(self, motor_id, manufacturer=None, designation=None):
        if isinstance(motor_id, str) and motor_id.strip():
            low = motor_id.strip().lower()
            for k in self.entries:
                if k.lower() in (low, low + "-v1", low + "-v2"):
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
    "AeroTech-M2000R-v2": {"manufacturer": "AeroTech", "designation": "M2000R", "diameter_m": 0.098,
                           "length_m": 0.732, "total_impulse_ns": 9671.0},
    "Estes-C6-v1": {"manufacturer": "Estes", "designation": "C6", "diameter_m": 0.018,
                    "length_m": 0.07, "total_impulse_ns": 9.0},
})




def tags(root):
    return [tag_of(n) for n in walk(root)]


def value(node, tag):
    return child_value(node, tag)


def small_design(motor_children):
    """A minimal rocket with one motor, a model-written wind and a custom reference."""
    return {"openrocket": {"attrs": {"version": 1.8}, "children": [
        {"rocket": {"children": [
            {"motorconfiguration": {"attrs": {"configid": "cfg0", "default": "true"}}},
            {"referencetype": {"value": "custom"}},
            {"customreference": {"value": 0.001}},
            {"subcomponents": {"children": [{"stage": {"children": [{"subcomponents": {"children": [
                {"nosecone": {"children": [{"length": {"value": 0.2}}, {"overridemass": {"value": 0.05}}]}},
                {"bodytube": {"children": [
                    {"length": {"value": 0.5}}, {"radius": {"value": 0.05}},
                    {"overridecg": {"value": 0.2}},
                    {"motormount": {"children": [
                        {"motor": {"attrs": {"configid": "cfg0"}, "children": motor_children}}]}},
                    {"subcomponents": {"children": [
                        {"simulations": {"children": []}}]}}]}}]}}]}}]}}]}},
        {"simulations": {"children": [{"simulation": {"children": [{"conditions": {"children": [
            {"windaverage": {"value": 30.0}}, {"launchrodlength": {"value": 50.0}},
            {"timestep": {"value": 0.5}}]}}]}}]}}]},
        "simulations": {"children": []}}


def motor_of(root):
    return next(n for n in walk(root) if "motor" in n)


# ------------------------------------------------------------------ the contract

def test_input_is_never_changed_and_cleaning_twice_changes_nothing(gold_rows, model_rows):
    designs = [design_of(r["answer"]) for r in gold_rows] + [design_of(r["content"]) for r in model_rows]
    designs = [d for d in designs if d is not None]
    assert len(designs) >= 90
    for d in designs:
        before = copy.deepcopy(d)
        once, notes = clean_design(d, TABLE)
        assert d == before
        assert all(isinstance(n, str) and n for n in notes)
        twice, notes2 = clean_design(once, TABLE)
        assert twice == once
        assert notes2 == []


def tags_outside_simulations(root):
    out, stack = [], [root]
    while stack:
        cur = stack.pop()
        if not (isinstance(cur, dict) and len(cur) == 1) or "simulations" in cur:
            continue
        out.append(next(iter(cur)))
        body = next(iter(cur.values()))
        kids = body.get("children") if isinstance(body, dict) else None
        if isinstance(kids, list):
            stack.extend(kids)
    return sorted(out)


def without_exact_repeats(root):
    """A copy in which a setting written twice with the SAME content keeps one
    copy (three reference rockets write a tube fin's count and rotation twice)."""
    root = copy.deepcopy(root)
    for node in walk(root):
        body = next(iter(node.values()))
        kids = body.get("children") if isinstance(body, dict) else None
        if not isinstance(kids, list) or next(iter(node)) in ("subcomponents", "finpoints",
                                                               "motormount", "motorconfiguration"):
            continue
        kids[:] = [c for i, c in enumerate(kids) if c not in kids[i + 1:] or "tabposition" in c]
    return root


def test_reference_designs_lose_only_what_the_reward_sets(gold_rows):
    for row in gold_rows:
        d = design_of(row["answer"])
        out, _ = clean_design(d, TABLE)
        assert "simulations" not in tags(out)
        assert value(rocket(out), "referencetype") == "maximum"
        # every part, mass and balance override tag and setting outside the
        # simulations is kept; only a setting repeated with identical content
        # loses its extra copy, drag overrides go, and so does a material
        # with no name ("RS:" shroud lines)
        gone = ("motor_id",) + DRAG_OVERRIDE_TAGS + MATERIAL_TAGS
        before = [t for t in tags_outside_simulations(without_exact_repeats(d)) if t not in gone]
        after = [t for t in tags_outside_simulations(out) if t not in gone]
        assert before == after, row["id"]
        named = [n for n in walk(without_exact_repeats(d)) if tag_of(n) in MATERIAL_TAGS
                 and not means_no_material(value_of(n, ""))]
        assert len(named) == sum(1 for n in walk(out) if tag_of(n) in MATERIAL_TAGS), row["id"]
        assert out["openrocket"]["attrs"]["version"] == FILE_VERSION


def test_model_written_wind_and_launch_conditions_are_removed():
    d = small_design([{"motor_id": {"value": "AeroTech-M2000R-v2"}}])
    out, notes = clean_design(d, TABLE)
    t = tags(out)
    for gone in ("simulations", "windaverage", "launchrodlength", "timestep"):
        assert gone not in t
    assert list(out) == ["openrocket"]
    assert any("simulations" in n for n in notes)


def test_stability_reference_is_forced():
    out, notes = clean_design(small_design([]), TABLE)
    r = rocket(out)
    assert value(r, "referencetype") == "maximum"
    assert "customreference" not in tags(out)
    assert any("reference" in n for n in notes)
    # a missing reference type is added
    d = small_design([])
    rk = rocket(d)
    rk["rocket"]["children"] = [c for c in rk["rocket"]["children"] if "referencetype" not in c]
    out, _ = clean_design(d, TABLE)
    assert value(rocket(out), "referencetype") == "maximum"


def test_fake_motor_size_is_replaced_from_the_table():
    d = small_design([
        {"manufacturer": {"value": "Acme"}}, {"motor_id": {"value": "aerotech-m2000r"}},
        {"designation": {"value": "M9999"}}, {"diameter": {"value": 0.5}},
        {"length": {"value": 0.01}}, {"delay": {"value": 0.0}}])
    out, notes = clean_design(d, TABLE)
    m = motor_of(out)
    assert value(m, "motor_id") == "AeroTech-M2000R-v2"
    assert value(m, "manufacturer") == "AeroTech"
    assert value(m, "designation") == "M2000R"
    assert value(m, "diameter") == 0.098
    assert value(m, "length") == 0.732
    assert value(m, "delay") == 0.0          # the model chooses the delay
    assert any("AeroTech-M2000R-v2" in n and "diameter" in n for n in notes)


def test_motor_without_id_gets_the_canonical_id():
    d = small_design([{"manufacturer": {"value": "Estes"}}, {"designation": {"value": "C6"}}])
    out, _ = clean_design(d, TABLE)
    m = motor_of(out)
    assert value(m, "motor_id") == "Estes-C6-v1"
    assert value(m, "diameter") == 0.018


def test_unknown_motor_is_left_for_stage_3():
    children = [{"motor_id": {"value": "Nobody-Z1"}}, {"diameter": {"value": 0.5}}]
    d = small_design(copy.deepcopy(children))
    out, _ = clean_design(d, TABLE)
    assert motor_of(out)["motor"]["children"] == children


def test_second_subcomponents_holder_is_merged_in_order():
    d = small_design([{"motor_id": {"value": "AeroTech-M2000R-v2"}}])
    stage = next(n for n in walk({"openrocket": d["openrocket"]}) if "stage" in n and kid(n, "subcomponents"))
    stage["stage"]["children"].append({"subcomponents": {"children": [{"transition": {}}]}})
    out, notes = clean_design(d, TABLE)
    st = next(n for n in walk(out) if "stage" in n and kid(n, "subcomponents"))
    holders = [c for c in st["stage"]["children"] if "subcomponents" in c]
    assert len(holders) == 1
    assert [next(iter(c)) for c in holders[0]["subcomponents"]["children"]] == ["nosecone", "bodytube", "transition"]
    assert any("merged" in n for n in notes)


def test_repeated_setting_keeps_the_last_copy():
    d = small_design([{"motor_id": {"value": "AeroTech-M2000R-v2"}}, {"delay": {"value": 3}},
                      {"delay": {"value": 9}}])
    nose = next(n for n in walk({"openrocket": d["openrocket"]}) if "nosecone" in n)
    nose["nosecone"]["children"].append({"length": {"value": 0.5}})
    out, notes = clean_design(d, TABLE)
    nose = next(n for n in walk(out) if "nosecone" in n)
    assert [c for c in nose["nosecone"]["children"] if "length" in c] == [{"length": {"value": 0.5}}]
    assert value(motor_of(out), "delay") == 9
    assert any("repeated" in n for n in notes)


def test_only_the_flown_configuration_is_kept():
    d = small_design([{"motor_id": {"value": "AeroTech-M2000R-v2"}}])
    r = rocket(d)
    r["rocket"]["children"].append({"motorconfiguration": {"attrs": {"configid": "cfgX", "default": "true"}}})
    mount = next(n for n in walk({"openrocket": d["openrocket"]}) if "motormount" in n)
    mount["motormount"]["children"].append({"motor": {"attrs": {"configid": "cfg0"},
                                                      "children": [{"motor_id": {"value": "Estes-C6"}}]}})
    out, notes = clean_design(d, TABLE)
    configs = [c for c in rocket(out)["rocket"]["children"] if "motorconfiguration" in c]
    assert [c["motorconfiguration"]["attrs"]["configid"] for c in configs] == ["cfgX"]
    assert [n for n in walk(out) if "motor" in n] == []      # no motor uses cfgX
    assert any("flown configuration" in n for n in notes)


def test_motor_keeps_only_known_settings_and_the_table_digest():
    table = FakeTable({"AeroTech-M2000R-v2": dict(TABLE.entries["AeroTech-M2000R-v2"], digest="abc")})
    d = small_design([{"motor_id": {"value": "AeroTech-M2000R-v2"}}, {"digest": {"value": "evil"}},
                      {"thrust": {"value": 1e6}}, {"type": {"value": "reload"}}])
    out, _ = clean_design(d, table)
    m = motor_of(out)
    assert value(m, "digest") == "abc"
    assert kid(m, "thrust") is None and value(m, "type") == "reload"


def test_override_tags_are_kept_for_now():
    out, _ = clean_design(small_design([]), TABLE)
    t = tags(out)
    assert "overridemass" in t and "overridecg" in t


def test_no_step_is_left_for_later():
    from rocket_reward import clean
    assert "LATER STEP" not in open(clean.__file__, encoding="utf-8").read()


def test_natural_copy_removes_every_override_and_nothing_else():
    from rocket_reward import clean
    tree = {"openrocket": {"children": [{"rocket": {"children": [{"subcomponents": {"children": [
        {"stage": {"children": [{"subcomponents": {"children": [{"bodytube": {"children": [
            {"overridemass": {"value": 0.2}}, {"overridesubcomponentsmass": {"value": "true"}},
            {"overridecg": {"value": 0.1}}, {"length": {"value": 0.5}}]}}]}}]}}]}}]}}]}}
    before = json.dumps(tree)
    natural, removed = clean.natural_copy(tree)
    assert removed == 3 and clean.override_count(tree) == 3 and clean.override_count(natural) == 0
    assert json.dumps(tree) == before
    assert "length" in json.dumps(natural)


# ------------------------------------------------------------------ file version, drag, materials

@pytest.mark.parametrize("version", [1.8, "1.2", "1.11", None, "x"])
def test_file_version_is_forced(version):
    d = small_design([])
    if version is None:
        del d["openrocket"]["attrs"]
    else:
        d["openrocket"]["attrs"]["version"] = version
    out, notes = clean_design(d, TABLE)
    assert out["openrocket"]["attrs"]["version"] == FILE_VERSION == "1.10"
    assert any("file format version" in n for n in notes)
    assert clean_design(out, TABLE)[1] == []


def test_drag_overrides_are_removed_mass_and_balance_overrides_stay():
    d = small_design([])
    for n in walk({"openrocket": d["openrocket"]}):
        if tag_of(n) in ("nosecone", "bodytube"):
            n[tag_of(n)]["children"] += [{"overridecd": {"value": 0.0}},
                                          {"overridesubcomponentscd": {"value": True}}]
    out, notes = clean_design(d, TABLE)
    t = tags(out)
    assert "overridecd" not in t and "overridesubcomponentscd" not in t
    assert "overridemass" in t and "overridecg" in t
    assert any("drag override" in n for n in notes)


MATERIALS = default_material_table()


def tube_with(*materials):
    """A small design whose body tube holds these material nodes, and its
    parachute the given cloth and lines (when passed as ("parachute", node))."""
    d = small_design([])
    tube = next(n for n in walk({"openrocket": d["openrocket"]}) if tag_of(n) == "bodytube")
    chute = {"parachute": {"children": []}}
    for m in materials:
        if isinstance(m, tuple):
            chute["parachute"]["children"].append(m[1])
        else:
            tube["bodytube"]["children"].append(m)
    kid(tube, "subcomponents")["subcomponents"]["children"].append(chute)
    return d


def mats(root, where):
    node = next(n for n in walk(root) if tag_of(n) == where)
    return [c for c in node[where]["children"] if tag_of(c) in MATERIAL_TAGS]


def test_known_material_gets_the_table_density_and_the_slots_type():
    d = tube_with({"material": {"attrs": {"type": "bulk", "density": 0.0011}, "value": "Cardboard"}},
                  ("p", {"material": {"attrs": {"density": "1e-7", "group": "x"}, "value": "Ripstop nylon"}}),
                  ("p", {"linematerial": {"attrs": {"type": "line", "density": 0},
                                          "value": "RS: Braided nylon (2 mm, 1/16 in)"}}))
    out, notes = clean_design(d, TABLE)
    tube, = mats(out, "bodytube")
    assert attrs_of(tube) == {"type": "bulk", "density": MATERIALS.lookup("bulk", "Cardboard")}
    cloth, line = mats(out, "parachute")
    assert attrs_of(cloth) == {"type": "surface", "density": MATERIALS.lookup("surface", "Ripstop nylon"),
                               "group": "x"}
    assert attrs_of(line)["density"] == MATERIALS.lookup("line", "Braided nylon (2 mm, 1/16 in)") > 0
    assert any("material density" in n for n in notes)
    again, notes2 = clean_design(out, TABLE)
    assert again == out and notes2 == []


def test_unknown_material_keeps_its_density_and_gets_the_slots_type():
    d = tube_with({"material": {"attrs": {"density": 0.0011}, "value": "Unobtainium"}})
    out, _ = clean_design(d, TABLE)
    m, = mats(out, "bodytube")
    assert attrs_of(m) == {"type": "bulk", "density": 0.0011} and value_of(m) == "Unobtainium"


@pytest.mark.parametrize("node", [
    {"material": {"attrs": {"type": "Bulk", "density": 0.0001}, "value": "Cardboard"}},     # wrong spelling of the type
    {"material": {"attrs": {"type": "surface", "density": 0.0001}, "value": "Cardboard"}},  # another slot's type
    {"material": {"attrs": {"type": "bulk", "density": "light"}, "value": "Cardboard"}},    # density not a number
    {"material": {"attrs": {"type": "bulk"}, "value": "Cardboard"}},                        # no density
    {"material": {"value": "Cardboard"}},                                                   # no attributes
    {"material": {"attrs": {"type": "bulk", "density": 0.0001}, "value": "  "}},            # empty name
    {"material": {"attrs": {"type": "bulk", "density": 0.0001}}},                           # no name
    {"material": {"attrs": {"type": "bulk", "density": 0.0001}, "value": "RS:"}},           # no material given
    {"material": {"attrs": {"type": "bulk", "density": 0.0001}, "value": "rs: "}},
])
def test_material_openrocket_would_not_use_is_removed(node):
    """OpenRocket then uses the part's default material, as it would anyway."""
    out, notes = clean_design(tube_with(node), TABLE)
    assert mats(out, "bodytube") == []
    assert any("default material" in n for n in notes)


def test_material_where_no_material_slot_is_left_alone():
    d = small_design([])
    nose = next(n for n in walk({"openrocket": d["openrocket"]}) if tag_of(n) == "nosecone")
    nose["nosecone"]["children"].append({"subcomponents": {"children": [{"masscomponent": {"children": [
        {"material": {"attrs": {"type": "bulk", "density": 1.0}, "value": "Lead"}}]}}]}})
    out, _ = clean_design(d, TABLE)
    m = next(n for n in walk(out) if tag_of(n) == "material")
    assert attrs_of(m) == {"type": "bulk", "density": 1.0}


@pytest.mark.parametrize("bad", [{"material": "Cardboard"}, {"material": {"attrs": 5, "value": "Cardboard"}},
                                 {"material": {"attrs": {"density": 1.0}, "value": ["x"]}},
                                 {"material": {"attrs": {"density": True, "type": "bulk"}, "value": 5}},
                                 {"material": {"attrs": {"density": "NaN"}, "value": "x" * 5000}}])
def test_hostile_material_nodes_do_not_crash(bad):
    out, _ = clean_design(tube_with(bad), TABLE)
    assert clean_design(out, TABLE)[0] == out


# ------------------------------------------------------------------ hostile trees

@pytest.mark.parametrize("root", [None, 5, "x", [], {}, {"openrocket": None},
                                  {"openrocket": {"children": "no"}},
                                  {"openrocket": {"children": [1, None, {"rocket": 7}]}},
                                  {"openrocket": {"children": [{"rocket": {"children": [
                                      {"subcomponents": {"children": [{"motor": {"children": [5, {"a": 1, "b": 2}]}}]}},
                                      {"referencetype": "bad body"}]}}]}}])
def test_hostile_shapes_do_not_crash(root):
    before = copy.deepcopy(root)
    out, notes = clean_design(root, TABLE)
    assert root == before
    again, _ = clean_design(out, TABLE)
    assert again == out


def test_deep_tree_does_not_crash():
    inner = {"bodytube": {"children": []}}
    for _ in range(3000):
        inner = {"bodytube": {"children": [{"subcomponents": {"children": [inner]}}]}}
    root = {"openrocket": {"children": [{"rocket": {"children": [{"subcomponents": {"children": [inner]}}]}}]}}
    out, _ = clean_design(root, TABLE)
    assert out is not root
    assert value(rocket(out), "referencetype") == "maximum"
    assert len(list(walk(out))) == len(list(walk(root))) + 1   # only the reference type is added


# ------------------------------------------------------------------ no waiting on the pad

def _stage_with_mount(delay, event="launch", config_delay=None):
    """A stage holding one body tube with a motor mount (ignition event and delay)
    and a per-configuration ignition setting."""
    cfg = [{"ignitionevent": {"value": event}}, {"ignitiondelay": {"value": delay if config_delay is None
                                                                        else config_delay}}]
    mount = {"motormount": {"children": [
        {"ignitionevent": {"value": event}}, {"ignitiondelay": {"value": delay}},
        {"motor": {"attrs": {"configid": "c1"}, "children": [{"motor_id": {"value": "Estes-C6-v1"}}]}},
        {"ignitionconfiguration": {"attrs": {"configid": "c1"}, "children": cfg}}]}}
    return {"stage": {"children": [{"subcomponents": {"children": [
        {"bodytube": {"children": [{"subcomponents": {"children": [
            {"innertube": {"children": [mount]}}]}}]}}]}}]}}


def _two_stage(upper_delay, bottom_delay, bottom_event="launch"):
    return {"openrocket": {"children": [{"rocket": {"children": [
        {"motorconfiguration": {"attrs": {"configid": "c1", "default": "true"}}},
        {"subcomponents": {"children": [_stage_with_mount(upper_delay, "burnout"),
                                        _stage_with_mount(bottom_delay, bottom_event)]}}]}}]}}


def _delays(stage_node):
    return [value(n, "ignitiondelay") for n in walk(stage_node)
            if tag_of(n) in ("motormount", "ignitionconfiguration")]


def test_bottom_stage_motors_light_without_delay():
    out, notes = clean_design(_two_stage(upper_delay=5.0, bottom_delay=16.0), TABLE)
    upper, bottom = [c for c in walk(out) if tag_of(c) == "stage"]
    assert _delays(bottom) == [0.0, 0.0]
    assert _delays(upper) == [5.0, 5.0]                    # an air start of the upper stage stays
    assert value(next(n for n in walk(bottom) if tag_of(n) == "motormount"), "ignitionevent") == "launch"
    assert any("wait on the pad" in n for n in notes)
    again, notes2 = clean_design(out, TABLE)
    assert again == out and not any("wait on the pad" in n for n in notes2)


@pytest.mark.parametrize("bad", ["16", "x", None, 1e9, -3.0])
def test_odd_bottom_stage_delays_become_zero(bad):
    out, _ = clean_design(_two_stage(upper_delay=0.0, bottom_delay=bad), TABLE)
    bottom = [c for c in walk(out) if tag_of(c) == "stage"][-1]
    assert _delays(bottom) == [0.0, 0.0]


def test_a_side_booster_keeps_its_own_ignition():
    root = _two_stage(upper_delay=0.0, bottom_delay=0.0)
    bottom = [c for c in walk(root) if tag_of(c) == "stage"][-1]
    tube = next(c for c in walk(bottom) if tag_of(c) == "bodytube")
    booster = _stage_with_mount(2.0)["stage"]
    tube["bodytube"]["children"][0]["subcomponents"]["children"].append({"parallelstage": booster})
    out, _ = clean_design(root, TABLE)
    side = next(c for c in walk(out) if tag_of(c) == "parallelstage")
    assert _delays(side) == [2.0, 2.0]
