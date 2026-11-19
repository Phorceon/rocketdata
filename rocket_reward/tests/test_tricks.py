"""Tricks that once let a broken design pass stages 1-4, run end to end.

Each test starts from the first reference design (it passes stages 1-4), adds
one trick, and runs the real preflight (parse, parts, motor, clean, limits)
with the packaged motor table. The trick must fail the stage that owns it.
"""
from __future__ import annotations

import copy
import json
import re

import pytest

from rocket_reward.materials import default_material_table, slot_type
from rocket_reward.parts import check_parts
from rocket_reward.scoring import preflight, preflight_result
from rocket_reward.tree import MATERIAL_TAGS, child, find_all as find, read_number, tag_of, walk

FIN_TAGS = ("trapezoidfinset", "freeformfinset", "ellipticalfinset")
RAZOR_FIN = {"trapezoidfinset": {"children": [
    {"fincount": {"value": 4}}, {"rootchord": {"value": 0.1}}, {"tipchord": {"value": 0.05}},
    {"height": {"value": 0.08}}, {"thickness": {"value": 0.00001}}]}}
DRAG_CHUTE = {"parachute": {"children": [{"diameter": {"value": 1.0}}, {"cd": {"value": 50.0}}]}}


# ------------------------------------------------------------------ helpers

@pytest.fixture()
def gold(gold_rows):
    text = gold_rows[0]["answer"]
    d = json.loads(re.search(r"<design>(.*?)</design>", text, re.S).group(1))
    assert stops_at(d) is None, "the reference design must pass stages 1-4"
    return d


def stops_at(design):
    """None when the design passes stages 1-4, else (stage, score, reasons)."""
    pre = preflight("<thought>t</thought><design>" + json.dumps(design) + "</design>")
    res = preflight_result(pre)
    return None if res is None else (res.stage, res.score, res.reasons)


def kids(node):
    return next(iter(node.values())).setdefault("children", [])


def set_everywhere(design, tags, field, value):
    for t in tags:
        for n in find(design, t):
            for c in kids(n):
                if field in c:
                    c[field] = {"value": value}
    return design


def fin_tube(design):
    """The body tube holding the fins, and its subcomponents holder."""
    for bt in find(design, "bodytube"):
        sub = child(bt, "subcomponents")
        if sub and any(any(t in c for t in FIN_TAGS) for c in kids(sub)):
            return bt, sub
    raise AssertionError("no fins")


def fails(design, stage, *words):
    got = stops_at(design)
    assert got is not None, "expected the trick to fail"
    assert got[0] == stage, got
    text = " ".join(got[2])
    for w in words:
        assert w in text, (w, got[2])
    return got


# ------------------------------------------------------------------ numbers written oddly

@pytest.mark.parametrize("text, value", [
    ("0.00001f", 0.00001), ("0.00001d", 0.00001), ("1F", 1.0), ("+2.5D", 2.5), ("0x1p-3", 0.125),
    ("0X1.8P1", 3.0), ("-0x.8p0f", -0.5), ("  0.5  ", 0.5), ("0.5" + " " * 70, 0.5),
    ("0" * 68 + "50", 50.0), ("0.00001" + "0" * 66, 0.00001), (".5e1", 5.0), ("5.", 5.0),
])
def test_number_text_is_read_as_openrocket_reads_it(text, value):
    got, broken = read_number(text)
    assert not broken and got == pytest.approx(value)


@pytest.mark.parametrize("text", ["auto", "filled", "auto 0.025", "1_0", "0x10", "1e", "--1", "", "  ",
                                  "٥", "1.2.3", "M2000R", "cfg0"])
def test_words_are_not_numbers(text):
    assert read_number(text) == (None, False)


@pytest.mark.parametrize("text", ["NaN", "-Infinity", "1e999", "1e999f", "0x1p99999", "inf", "nan",
                                  "auto 1e999", "  Infinity  "])
def test_non_finite_text_is_broken(text):
    assert read_number(text) == (None, True)


@pytest.mark.parametrize("value", ["0.00001f", "0x1p-17", " " * 70 + "0.00001", "0.00001" + "0" * 66])
def test_razor_fins_written_as_odd_text_fail(gold, value):
    fails(set_everywhere(gold, FIN_TAGS, "thickness", value), "limits", "fin thickness")


@pytest.mark.parametrize("value", ["50f", "0" * 68 + "50", "50" + " " * 70])
def test_drag_chute_written_as_odd_text_fails(gold, value):
    fails(set_everywhere(gold, ("parachute",), "cd", value), "limits", "cd", "2.9")


# ------------------------------------------------------------------ hiding parts and settings

def test_parts_in_a_second_subcomponents_holder_are_checked(gold):
    bt, _ = fin_tube(gold)
    kids(bt).append({"subcomponents": {"children": [copy.deepcopy(RAZOR_FIN), copy.deepcopy(DRAG_CHUTE)]}})
    fails(gold, "limits", "fin thickness", "cd")


def test_fins_moved_to_a_second_holder_keep_their_limits(gold):
    bt, sub = fin_tube(gold)
    fins = [c for c in kids(sub) if any(t in c for t in FIN_TAGS)]
    for f in fins:
        kids(sub).remove(f)
    set_everywhere({"x": {"children": fins}}, FIN_TAGS, "thickness", 0.00001)
    kids(bt).append({"subcomponents": {"children": fins}})
    fails(gold, "limits", "fin thickness")


def test_pods_in_a_second_holder_count_toward_total_impulse(gold):
    bt, _ = fin_tube(gold)
    tube = next(n for t in ("innertube", "bodytube") for n in find(gold, t) if child(n, "motormount"))
    pod = {"podset": {"children": [{"instancecount": {"value": 40}},
                                   {"subcomponents": {"children": [copy.deepcopy(tube)]}}]}}
    kids(bt).append({"subcomponents": {"children": [pod]}})
    fails(gold, "limits", "total impulse")


def test_a_setting_written_twice_is_checked_by_its_last_copy(gold):
    for p in find(gold, "parachute"):
        kids(p).append({"cd": {"value": 50.0}})
    fails(gold, "limits", "cd", "2.9")


def test_a_second_default_configuration_cannot_fly_an_unchecked_motor(gold):
    rocket = find(gold, "rocket")[0]
    kids(rocket).append({"motorconfiguration": {"attrs": {"configid": "cfgX", "default": "true"}}})
    for mm in find(gold, "motormount"):
        kids(mm).append({"motor": {"attrs": {"configid": "cfgX"}, "children": [
            {"motor_id": {"value": "Totally-Fake-Q99999"}}, {"diameter": {"value": 0.5}}]}})
    fails(gold, "motor", "Totally-Fake-Q99999")


def test_a_written_motor_id_twice_is_checked_by_its_last_copy(gold):
    for m in find(gold, "motor"):
        kids(m).append({"motor_id": {"value": "Totally-Fake-Q99999"}})
    fails(gold, "motor", "Totally-Fake-Q99999")


def test_a_model_written_digest_is_replaced_from_the_table(gold):
    for m in find(gold, "motor"):
        kids(m).extend([{"digest": {"value": "976282261671421bd3548938af89454c"}},
                        {"type": {"value": "single"}}, {"thrustcurve": {"value": "1000000"}}])
    pre = preflight("<design>" + json.dumps(gold) + "</design>")
    assert pre.passed
    for m in find(pre.clean_root, "motor"):
        tags = [next(iter(c)) for c in kids(m)]
        assert tags.count("digest") == 1 and tags.count("type") == 1 and "thrustcurve" not in tags
        assert child(m, "digest")["digest"]["value"] != "976282261671421bd3548938af89454c"


# ------------------------------------------------------------------ overrides and materials

@pytest.mark.parametrize("tag, value, words", [
    ("overridemass", -50.0, "negative"), ("overridemass", 1e300, "20 kg"),
    ("overridecg", -100.0, "negative"), ("overridecg", 50.0, "3.66 m"),
])
def test_override_values_are_bounded(gold, tag, value, words):
    nose = find(gold, "nosecone")[0]
    kids(nose).append({tag: {"value": value}})
    fails(gold, "limits", tag, words)


@pytest.mark.parametrize("value", [0.0, -5.0, 40.0, "3.799240749538965E-7"])
def test_drag_overrides_are_removed_before_anything_is_checked(gold, value):
    """A drag override was a free way to lower drag (references wrote Cd 0 and
    3.8e-7); the cleaning removes it, so it can neither help nor fail."""
    for t in ("nosecone", "bodytube"):
        for n in find(gold, t):
            kids(n).extend([{"overridecd": {"value": value}}, {"overridesubcomponentscd": {"value": True}}])
    pre = preflight("<design>" + json.dumps(gold) + "</design>")
    assert pre.passed
    assert not find(pre.clean_root, "overridecd") and not find(pre.clean_root, "overridesubcomponentscd")


def _cleaned_densities(clean_root):
    """(slot type, name, density) of every material in the cleaned copy."""
    out = []
    for node, parents in walk(clean_root):
        t = tag_of(node)
        if t in MATERIAL_TAGS and parents:
            out.append((slot_type(tag_of(parents[-1]), t), node[t].get("value"), node[t]["attrs"]["density"]))
    return out


@pytest.mark.parametrize("density", [-500.0, 1e-9, 0.0, "1e-12f"])
def test_written_densities_are_replaced_by_the_table(gold, density):
    """Every material the table knows flies with its table density, whatever
    the design wrote, so a weightless (or negative) density gains nothing."""
    _set_materials(_without_mass_overrides(gold), density, "keep")
    pre = preflight("<design>" + json.dumps(gold) + "</design>")
    assert pre.passed, preflight_result(pre)
    table = default_material_table()
    got = _cleaned_densities(pre.clean_root)
    assert got and all(d == table.lookup(kind, name) for kind, name, d in got)


def test_zero_walls_are_never_better_than_thin_walls(gold):
    for n in find(gold, "children"):
        if isinstance(n.get("children"), list):
            n["children"][:] = [c for c in n["children"] if not (isinstance(c, dict) and "overridemass" in c)]
    shells = ("bodytube", "transition", "nosecone")
    thin = fails(set_everywhere(copy.deepcopy(gold), shells, "thickness", 0.00001), "limits", "wall")
    zero = fails(set_everywhere(copy.deepcopy(gold), shells, "thickness", 0.0), "limits", "0 mm")
    assert zero[1] <= thin[1]
    assert stops_at(set_everywhere(copy.deepcopy(gold), shells, "thickness", "filled")) is None


# ------------------------------------------------------------------ counts and placement

def test_fin_counts_close_to_whole_are_whole(gold):
    assert stops_at(set_everywhere(gold, FIN_TAGS, "fincount", 3.0000001)) is None


def test_fractional_fin_counts_past_the_limit_cost_more(gold):
    s = {}
    for n in (8.5, 20.5, 100.5):
        got = fails(set_everywhere(copy.deepcopy(gold), FIN_TAGS, "fincount", n), "limits", "whole number")
        s[n] = got[1]
    assert s[8.5] >= s[20.5] >= s[100.5]


def test_parts_inside_a_parachute_do_not_count(gold):
    bt, sub = fin_tube(gold)
    fins = [c for c in kids(sub) if any(t in c for t in FIN_TAGS)]
    for f in fins:
        kids(sub).remove(f)
    chute = find(gold, "parachute")[0]
    kids(chute).append({"subcomponents": {"children": fins}})
    fails(gold, "parts", "fin set", "does not accept")
    res = check_parts(gold)
    line = next(x for x in res.reasons if "does not accept" in x)
    assert "go on a nose cone, body tube or transition" in line and "a stage holds only" not in line


def test_negative_size_reason_has_a_unit(gold):
    got = fails(set_everywhere(gold, ("nosecone",), "length", -0.9144), "limits", "negative")
    assert any("-0.9144 m" in r for r in got[2])


# ------------------------------------------------------------------ material types (added on review)

def _without_mass_overrides(design):
    """Remove every overridemass, so every part's material density counts."""
    for n in find(design, "openrocket") + [m for t in ("bodytube", "nosecone", "transition", "innertube",
                                                             "trapezoidfinset", "freeformfinset",
                                                             "ellipticalfinset", "tubecoupler",
                                                             "centeringring", "bulkhead", "engineblock",
                                                             "parachute", "streamer", "shockcord",
                                                             "launchlug", "railbutton", "stage")
                                           for m in find(design, t)]:
        k = kids(n)
        k[:] = [c for c in k if not (isinstance(c, dict) and "overridemass" in c)]
    return design


def _set_materials(design, density, type_value, name=None):
    """Set every material's density (and name, when given); type_value None
    removes the type attribute, "keep" keeps it."""
    count = 0
    for tag in ("material", "filletmaterial", "linematerial"):
        for n in find(design, tag):
            a = n[tag].setdefault("attrs", {})
            a["density"] = density
            if type_value is None:
                a.pop("type", None)
            elif type_value != "keep":
                a["type"] = type_value
            if name is not None:
                n[tag]["value"] = name
            count += 1
    assert count > 5
    return design


def test_untyped_weightless_material_gets_the_table_density(gold):
    """OpenRocket loads a material with no "type" as the type its slot holds
    (bulk for a tube): the cleaning writes that type and the table density,
    so an untyped 0.0001 kg/m3 rocket flies at its real weight."""
    pre = preflight("<design>" + json.dumps(_set_materials(_without_mass_overrides(gold), 0.0001, None))
                    + "</design>")
    assert pre.passed
    table = default_material_table()
    got = _cleaned_densities(pre.clean_root)
    assert got and all(d == table.lookup(kind, name) for kind, name, d in got)
    assert all(node[tag_of(node)]["attrs"]["type"] in ("bulk", "surface", "line")
               for node, _ in walk(pre.clean_root) if tag_of(node) in MATERIAL_TAGS)


def test_wrongly_typed_material_is_dropped_like_openrocket_ignores_it(gold):
    """A material whose type is not exactly the slot's ("Bulk", "surface" on a
    tube) is ignored by OpenRocket, which keeps the part's default material:
    the cleaning removes it, so its written density cannot make the rocket lighter."""
    pre = preflight("<design>" + json.dumps(_set_materials(_without_mass_overrides(copy.deepcopy(gold)),
                                                           0.0001, "Bulk")) + "</design>")
    assert pre.passed and not any(tag_of(n) in MATERIAL_TAGS for n, _ in walk(pre.clean_root))


def test_weightless_unknown_material_fails_on_its_name_and_its_density(gold):
    fails(_set_materials(_without_mass_overrides(gold), 0.0001, "bulk", name="Featherlite"),
          "limits", "Featherlite", "not in the material table", "density")
