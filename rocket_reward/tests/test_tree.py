"""Tests for tree.py: reading the design tree."""
from __future__ import annotations

import time

import pytest

from rocket_reward import tree
from rocket_reward.tree import make_node as n


def sample() -> dict:
    """A small rocket: openrocket > rocket > subcomponents > stage > nose + tube."""
    nose = n("nosecone", children=[n("length", 0.2), n("material", "Polystyrene", {"type": "bulk"})])
    fins = n("trapezoidfinset", children=[n("fincount", 3)])
    tube = n("bodytube", children=[n("length", "0.5"), n("subcomponents", children=[fins])])
    stage = n("stage", children=[n("subcomponents", children=[nose, tube])])
    rocket = n("rocket", children=[n("name", "Test"), n("subcomponents", children=[stage])])
    return n("openrocket", attrs={"version": "1.9"}, children=[rocket])


def test_make_node_writes_only_given_pieces():
    assert n("a") == {"a": {}}
    assert n("a", 0.0) == {"a": {"value": 0.0}}
    assert n("a", attrs={"x": 1}, children=[]) == {"a": {"attrs": {"x": 1}, "children": []}}


def test_basic_accessors():
    root = sample()
    assert tree.tag_of(root) == "openrocket"
    assert tree.attr_of(root, "version") == "1.9"
    assert tree.attr_of(root, "missing", "d") == "d"
    rocket = tree.rocket_of(root)
    assert rocket is not None and tree.child_value(rocket, "name") == "Test"
    assert tree.child(rocket, "nothing") is None
    assert tree.child_value(rocket, "nothing", 7) == 7


def test_find_all_and_walk_order():
    root = sample()
    tags = [tree.tag_of(x) for x, _ in tree.walk(root)]
    assert tags[0] == "openrocket"
    assert tags.index("nosecone") < tags.index("bodytube") < tags.index("trapezoidfinset")
    assert len(tree.find_all(root, "length")) == 2
    for node, parents in tree.walk(root):
        if tree.tag_of(node) == "fincount":
            assert [tree.tag_of(p) for p in parents][:2] == ["openrocket", "rocket"]


def test_walk_components_follows_only_subcomponents():
    stage = tree.subcomponents(tree.rocket_of(sample()))[0]
    names = [tree.tag_of(c) for c, _ in tree.walk_components(stage)]
    assert names == ["nosecone", "bodytube", "trapezoidfinset"]   # the stage itself is not listed
    fin_parents = [p for c, p in tree.walk_components(stage) if tree.tag_of(c) == "trapezoidfinset"][0]
    assert [tree.tag_of(p) for p in fin_parents] == ["stage", "bodytube"]


def test_numbers():
    assert tree.number(3) == 3.0 and tree.number("0.05") == 0.05 and tree.number(" 2 ") == 2.0
    for bad in [True, False, None, "auto", "", "nan", "inf", "-Infinity", float("nan"),
                float("inf"), [], {}, "1,5"]:
        assert tree.number(bad) is None, bad
    tube = n("bodytube", children=[n("length", "0.5"), n("radius", "auto")])
    assert tree.child_number(tube, "length") == 0.5
    assert tree.child_number(tube, "radius") is None
    assert tree.child_number(tube, "missing") is None


def test_number_is_read_number_without_the_flag():
    """There is one number reader: `number` gives read_number's value, so odd
    text OpenRocket reads ("3f", "0x1p1") is a number and text it does not
    read ("1_0", "٣", "infinity" written by Python) is not."""
    for x in [3, 0.5, "0.5f", "3D", "0x1p1", " 2 ", "1_0", "٣", "inf", "1e999", 10**400, "auto 0.025",
              True, None, [1]]:
        assert tree.number(x) == tree.read_number(x)[0], x
    assert tree.number("3f") == 3.0 and tree.number("0x1p1") == 2.0
    assert tree.number("1_0") is None and tree.number("٣") is None


def test_number_of_a_huge_integer():
    assert tree.number(10**400) is None


def test_copy_tree_is_independent():
    root = sample()
    other = tree.copy_tree(root)
    tree.rocket_of(other)["rocket"]["children"].clear()
    assert tree.children_of(tree.rocket_of(root))


def test_malformed_nodes_do_not_crash_helpers():
    odd = [
        {"a": None}, {"a": 5}, {"a": "text"}, {"a": []},
        {"a": {"children": "nope"}}, {"a": {"children": None}}, {"a": {"attrs": [1, 2]}},
        {"a": {"attrs": "x"}}, {"a": {"value": {"deep": 1}}},
    ]
    for node in odd:
        assert tree.tag_of(node) == "a"
        assert isinstance(tree.body_of(node), dict)
        assert tree.children_of(node) == []
        assert tree.attr_of(node, "x", "d") == "d"
        assert tree.child(node, "b") is None
        assert tree.subcomponents(node) == []
        assert [x for x, _ in tree.walk(node)] == [node]
        assert tree.find_all(node, "a") == [node]
    assert tree.rocket_of({"notopenrocket": {}}) is None
    assert tree.rocket_of({"openrocket": {}}) is None
    assert tree.value_of({"a": {"value": None}}, "d") is None


def test_walk_on_a_very_deep_tree_does_not_overflow():
    node = n("leaf", 1)
    for _ in range(100_000):
        node = n("x", children=[node])
    count = 0
    for _ in tree.walk(node):
        count += 1
    assert count == 100_001


def test_helpers_are_safe_on_things_that_are_not_nodes():
    for odd in [{}, {"a": {}, "b": {}}, [], None, 5, "text", {1: {}}]:
        assert tree.tag_of(odd) == ""
        assert tree.body_of(odd) == {} and tree.attrs_of(odd) == {}
        assert tree.children_of(odd) == [] and tree.child_list(odd) is None
        assert tree.child(odd, "a") is None and tree.last_child(odd, "a") is None
        assert tree.subcomponents(odd) == [] and list(tree.walk_components(odd)) == []
        assert tree.stages_of(odd) == []


def test_children_skip_things_that_are_not_nodes():
    node = {"a": {"children": [1, "x", None, {}, {"b": {}, "c": {}}, n("d", 1), [n("e")]]}}
    assert [tree.tag_of(c) for c in tree.children_of(node)] == ["d"]
    assert len(tree.child_list(node)) == 7


def test_first_and_last_child():
    node = n("motor", children=[n("motor_id", "A"), n("motor_id", "B"), n("delay", 5)])
    assert tree.child_value(node, "motor_id") == "A"
    assert tree.last_text(node, "motor_id") == "B"
    assert tree.last_text(node, "delay") is None   # not text
    assert tree.children_named(node, "motor_id") == [n("motor_id", "A"), n("motor_id", "B")]


def test_subcomponents_merges_every_holder():
    a, b = n("bodytube"), n("innertube")
    tube = n("bodytube", children=[n("subcomponents", children=[a]), n("x"), n("subcomponents", children=[b])])
    assert tree.subcomponents(tube) == [a, b]


def test_rocket_and_stages():
    root = sample()
    assert [tree.tag_of(s) for s in tree.stages_of(root)] == ["stage"]
    with_extra = {"openrocket": root["openrocket"], "simulations": {}}
    assert tree.rocket_of(with_extra) is tree.rocket_of(root)


def test_legal_only_drops_misplaced_parts():
    chute = n("parachute", children=[n("subcomponents", children=[n("trapezoidfinset")])])
    stage = n("stage", children=[n("subcomponents", children=[n("bodytube", children=[
        n("subcomponents", children=[chute])])])])
    skipped: list = []
    tags = [tree.tag_of(c) for c in tree.iter_components(stage, legal_only=True, skipped=skipped)]
    assert tags == ["bodytube", "parachute"] and skipped == [("parachute", "trapezoidfinset")]
    assert tree.is_legal_child("bodytube", "trapezoidfinset") and not tree.is_legal_child("stage", "parachute")


def test_ancestors_read_like_a_tuple():
    root = sample()
    for node, parents in tree.walk(root):
        if tree.tag_of(node) == "fincount":
            tags = tuple(tree.tag_of(p) for p in parents)
            assert len(parents) == len(tags) and bool(parents)
            assert tree.tag_of(parents[-1]) == "trapezoidfinset" and tree.tag_of(parents[0]) == "openrocket"
            assert parents == tuple(parents) and (parents + (node,))[-1] is node
            assert [tree.tag_of(p) for p in reversed(parents)] == list(reversed(tags))
        if node is root:
            assert not parents and len(parents) == 0


def test_walks_stay_fast_on_a_very_deep_tree():
    """Each step adds one link to the ancestors instead of copying them, so a
    walk costs the same per node however deep the tree is."""
    node = n("leaf", 1)
    for _ in range(200_000):
        node = n("x", children=[node])
    t0 = time.perf_counter()
    *_, (leaf, parents) = tree.walk(node)
    assert tree.tag_of(leaf) == "leaf" and len(parents) == 200_000
    comp = n("stage")
    for _ in range(50_000):
        comp = n("bodytube", children=[n("subcomponents", children=[comp])])
    assert sum(1 for _ in tree.walk_components(comp)) == 50_000
    assert time.perf_counter() - t0 < 5.0


def test_copy_tree_handles_a_very_deep_tree():
    node = n("leaf", [1, {"k": "v"}])
    for _ in range(100_000):
        node = n("x", children=[node])
    other = tree.copy_tree(node)
    a, b, depth = node, other, 0
    while tree.tag_of(a) == "x":          # compare level by level (== itself would recurse)
        assert b is not a and tree.tag_of(b) == "x"
        a, b, depth = tree.children_of(a)[0], tree.children_of(b)[0], depth + 1
    assert depth == 100_000 and b == a and b is not a and b["leaf"]["value"][1] is not a["leaf"]["value"][1]


def test_read_number_follows_openrocket():
    assert tree.read_number("0.5f") == (0.5, False)
    assert tree.read_number("0x1p-1") == (0.5, False)
    assert tree.read_number("auto") == (None, False)
    assert tree.read_number("1e999") == (None, True)
    assert tree.read_number("NaN") == (None, True)
    assert tree.read_number(10**400) == (None, True)
    assert tree.java_number(" 2 ") == 2.0 and tree.java_number("1_0") is None


# ------------------------------------------------------------------ malformed input

MALFORMED = [None, 0, 1.5, True, "x", "", [], {}, {"a": 1, "b": 2}, {1: {}}, {"t": None}, {"t": []},
             {"t": "text"}, {"t": {"children": "abc"}}, {"t": {"attrs": [1], "value": {"a": 1}}},
             {"t": {"children": [1, None, {"x": 1, "y": 2}, {"k": {"children": None}}]}}, [{"a": {}}], b"x"]


@pytest.mark.parametrize("x", MALFORMED)
def test_every_helper_is_safe_on_malformed_input(x):
    """Every reading helper takes any JSON-like value without raising: the
    tree comes from a language model."""
    for f in (tree.is_node, tree.tag_of, tree.body_of, tree.children_of, tree.child_list, tree.value_of,
              tree.attrs_of, tree.number, tree.read_number, tree.java_number, tree.copy_tree,
              lambda v: tree.find_all(v, "t"), tree.rocket_of, tree.stages_of,
              tree.subcomponents, tree.material_nodes, lambda v: list(tree.walk(v)),
              lambda v: list(tree.walk_nodes(v)), lambda v: list(tree.iter_components(v)),
              lambda v: tree.child(v, "t"), lambda v: tree.last_child(v, "t"), lambda v: tree.last_text(v, "t"),
              lambda v: tree.child_number(v, "t"), lambda v: tree.children_named(v, "t"),
              lambda v: tree.attr_of(v, "a")):
        f(x)


def test_java_number_on_non_text_is_none():
    for x in (None, 3, 2.5, True, [], {}, b"1"):
        assert tree.java_number(x) is None


def test_material_nodes_lists_every_material_as_written():
    root = sample()
    chute = n("parachute", children=[n("material", "Ripstop nylon", {"type": "surface", "density": 0.067}),
                                     n("linematerial", "Braided nylon (2 mm, 1/16 in)", {"type": "line"})])
    holder = tree.child_list(tree.child(tree.find_all(root, "bodytube")[0], "subcomponents"))
    holder.append(chute)
    holder.append({"filletmaterial": {"attrs": ["not", "a", "dict"]}})
    assert tree.material_nodes(root) == [
        ("material", "bulk", "Polystyrene", None),
        ("material", "surface", "Ripstop nylon", 0.067),
        ("linematerial", "line", "Braided nylon (2 mm, 1/16 in)", None),
        ("filletmaterial", None, None, None),
    ]
    assert tree.material_nodes(None) == [] and tree.material_nodes({"material": "x"}) == [("material", None, None, None)]
