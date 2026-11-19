"""Stage 2 (parts.py): the eight needed parts."""
from __future__ import annotations

import copy
import json
import time

import pytest

from answers import design_of
from rocket_reward.parts import ITEMS, check_parts, fin_count
from rocket_reward.tree import find_all as nodes


# The model answers (tests/data/model_val.jsonl.gz) that hold a readable tree
# but miss parts, as found when this stage was calibrated: parts placed
# outside "subcomponents", a stage directly under "rocket", or no motor mount.
MODEL_PART_FAILURES = {
    "row-003-fca5ed76", "row-011-54ff7228", "row-018-fe08cd1c", "row-031-e75ff0bf",
    "row-039-b6bbcf30", "row-041-bbcf4448", "row-045-1f6c5f5e",
    # its only parachute (and a fin set, a lug and a mass) sit directly in the
    # stage, where OpenRocket does not accept them and drops them
    "row-006-ff300a35",
}




@pytest.fixture(scope="module")
def gold_designs(gold_rows):
    return [(r["id"], design_of(r["answer"])) for r in gold_rows]


@pytest.fixture()
def gold(gold_designs):
    """A fresh copy of a plain one-stage reference rocket with one motor."""
    return copy.deepcopy(gold_designs[9][1])


def drop(tree, tags):
    """Remove every node whose tag is in `tags`, wherever it sits."""
    stack = [tree]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            for body in cur.values():
                if isinstance(body, dict) and isinstance(body.get("children"), list):
                    body["children"] = [c for c in body["children"]
                                        if not (isinstance(c, dict) and next(iter(c), None) in tags)]
                    stack.extend(body["children"])
    return tree


def set_child_value(node, tag, value):
    body = next(iter(node.values()))
    kids = [c for c in body["children"] if next(iter(c)) != tag]
    kids.append({tag: {"value": value}})
    body["children"] = kids


# ---------------------------------------------------------------------------
# real data

def test_every_gold_answer_passes(gold_designs):
    for rid, d in gold_designs:
        res = check_parts(d)
        assert res.passed, (rid, res.reasons)
        assert res.credit == 1.0
        assert set(res.info["found"]) == set(ITEMS) and all(res.info["found"].values())


def test_model_answers_fail_exactly_where_parts_are_misplaced(model_rows):
    failed = set()
    for r in model_rows:
        d = design_of(r["content"]) if not r.get("truncated") else None
        if not isinstance(d, dict) or "openrocket" not in d:
            continue
        res = check_parts(d)
        if not res.passed:
            failed.add(r["id"])
            assert 0 <= res.credit < 1
            assert res.reasons and all("missing" in x or "does not accept" in x for x in res.reasons[1:])
    assert failed == MODEL_PART_FAILURES


def test_misplaced_parts_reason_says_where_they_belong(model_rows):
    """row-006 puts its parachute, fins, lug and mass directly in the stage: the
    reason says a stage holds only shells and where the others go."""
    row = next(r for r in model_rows if r["id"] == "row-006-ff300a35")
    res = check_parts(design_of(row["content"]))
    line = next(x for x in res.reasons if "does not accept" in x)
    assert "a stage holds only nose cones, body tubes and transitions" in line
    assert "subcomponents of a body tube" in line


# ---------------------------------------------------------------------------
# each item, one at a time

@pytest.mark.parametrize("tags, item, words, left", [
    (("nosecone",), "nose_cone", "nose cone", 7),
    (("parachute", "streamer"), "recovery", "recovery device", 7),
    (("trapezoidfinset", "freeformfinset", "ellipticalfinset", "tubefinset"), "fin_set", "fin set", 7),
    (("motorconfiguration",), "motor_configuration", "motor configuration", 7),
    # with no motor, no motor can use the configuration either
    (("motor",), "motor", "motor inside a motor mount", 6),
])
def test_removing_one_item_costs_its_share(gold, tags, item, words, left):
    res = check_parts(drop(gold, set(tags)))
    assert not res.passed
    assert res.info["found"][item] is False
    assert sum(res.info["found"].values()) == left
    assert res.credit == pytest.approx(left / 8)
    assert any(words in r for r in res.reasons)


def test_removing_the_motor_mount_also_loses_the_motor(gold):
    res = check_parts(drop(gold, {"motormount"}))
    found = res.info["found"]
    assert not found["motor_mount"] and not found["motor"] and not found["motor_configuration"]
    assert res.credit == pytest.approx(5 / 8)


def test_no_body_tube(gold):
    res = check_parts(drop(gold, {"bodytube"}))
    assert res.info["found"]["body_tube"] is False


def test_empty_rocket_finds_nothing_but_names_everything():
    res = check_parts({"openrocket": {"children": [{"rocket": {"children": []}}]}})
    assert res.credit == 0 and not res.passed
    assert len(res.reasons) == 1 + len(ITEMS)


def test_stage_directly_under_rocket_does_not_count(gold):
    rocket = gold["openrocket"]["children"][0]
    body = rocket["rocket"]
    holder = next(c for c in body["children"] if "subcomponents" in c)
    stage = holder["subcomponents"]["children"].pop(0)
    body["children"].append(stage)
    res = check_parts(gold)
    assert res.info["found"]["stage"] is False
    assert res.info["found"]["nose_cone"] is False   # parts inside a misplaced stage do not count
    assert any("belongs inside" in r for r in res.reasons)


def test_part_outside_subcomponents_does_not_count(gold):
    stage = nodes(gold, "stage")[-1]                     # the stage under rocket > subcomponents
    stage_body = stage["stage"]
    holder = next(c for c in stage_body["children"] if "subcomponents" in c)
    cone = next(c for c in holder["subcomponents"]["children"] if "nosecone" in c)
    holder["subcomponents"]["children"].remove(cone)
    stage_body["children"].append(cone)
    assert check_parts(gold).info["found"]["nose_cone"] is False


# ---------------------------------------------------------------------------
# ways real rockets express each item

def test_streamer_alone_is_recovery(gold):
    chute = nodes(gold, "parachute")[0]
    chute["streamer"] = chute.pop("parachute")
    drop(gold, {"parachute"})
    assert check_parts(gold).passed


def test_tube_fins_alone_are_a_fin_set(gold_designs):
    # Reference row 16 flies on tube fins only.
    d = copy.deepcopy(gold_designs[15][1])
    assert nodes(d, "tubefinset") and not nodes(d, "trapezoidfinset")
    assert check_parts(d).passed


def test_motor_mount_on_the_body_tube_counts(gold):
    mm = nodes(gold, "motormount")[0]
    holder_tube = None
    for tube in nodes(gold, "innertube"):
        if mm in tube["innertube"]["children"]:
            holder_tube = tube
    tube_body = holder_tube["innertube"]
    tube_body["children"].remove(mm)
    outer = nodes(gold, "bodytube")[-1]
    outer["bodytube"]["children"].append(mm)
    assert check_parts(gold).passed


def test_motor_mount_on_a_coupler_does_not_count(gold):
    mm = nodes(gold, "motormount")[0]
    for tube in nodes(gold, "innertube"):
        if mm in tube["innertube"]["children"]:
            tube["tubecoupler"] = tube.pop("innertube")
    res = check_parts(gold)
    assert not res.info["found"]["motor_mount"] and not res.info["found"]["motor"]


@pytest.mark.parametrize("count, ok", [(3, True), ("4", True), (1, True), (10**9, True),
                                       (0, False), (-2, False), (0.5, False), ("three", False),
                                       (None, False), (float("nan"), False), ([3], False)])
def test_fin_count(gold, count, ok):
    for fs in nodes(gold, "trapezoidfinset") + nodes(gold, "freeformfinset"):
        set_child_value(fs, "fincount", count)
    assert check_parts(gold).info["found"]["fin_set"] is ok


def test_instancecount_stands_in_for_fincount_and_no_count_means_three(gold):
    fs = (nodes(gold, "trapezoidfinset") + nodes(gold, "freeformfinset"))[0]
    body = next(iter(fs.values()))
    body["children"] = [c for c in body["children"] if next(iter(c)) not in ("fincount", "instancecount")]
    assert fin_count(fs) is None and check_parts(gold).info["found"]["fin_set"]
    body["children"].append({"instancecount": {"value": 4}})
    assert fin_count(fs) == 4.0
    body["children"][-1] = {"instancecount": {"value": 0}}
    assert check_parts(gold).info["found"]["fin_set"] is False


@pytest.mark.parametrize("tag", ["fincount", "instancecount"])
def test_a_fin_count_written_twice_counts_by_its_last_copy(gold, tag):
    """OpenRocket's loader and the cleaned copy keep the last copy of a
    setting, so stage 2 reads the last one too."""
    fins = nodes(gold, "trapezoidfinset") + nodes(gold, "freeformfinset")
    for fs in fins:
        body = next(iter(fs.values()))
        body["children"] = [c for c in body["children"] if next(iter(c)) not in ("fincount", "instancecount")]
        body["children"] += [{tag: {"value": 0}}, {"material": {"value": "Balsa"}}, {tag: {"value": 4}}]
    assert fin_count(fins[0]) == 4.0 and check_parts(gold).info["found"]["fin_set"]
    for fs in fins:
        body = next(iter(fs.values()))
        body["children"][-1] = {tag: {"value": 0}}
        body["children"][-3] = {tag: {"value": 4}}
    assert fin_count(fins[0]) == 0.0 and check_parts(gold).info["found"]["fin_set"] is False


def test_motor_must_use_the_flown_configuration(gold):
    motor = nodes(gold, "motor")[0]
    motor["motor"]["attrs"]["configid"] = "other"
    res = check_parts(gold)
    assert res.info["found"]["motor"] and not res.info["found"]["motor_configuration"]
    assert any("'cfg0'" in r and "other" in r for r in res.reasons)


def test_motor_without_configid_fails_item_7(gold):
    motor = nodes(gold, "motor")[0]
    del motor["motor"]["attrs"]
    assert check_parts(gold).info["found"]["motor_configuration"] is False


def test_second_top_level_key_is_ignored(gold):
    gold["simulations"] = {"children": []}
    assert check_parts(gold).passed


# ---------------------------------------------------------------------------
# hostile input

@pytest.mark.parametrize("tree", [
    None, 5, "openrocket", [], {}, {"openrocket": None}, {"openrocket": []},
    {"openrocket": {"children": "rocket"}},
    {"openrocket": {"children": [1, "x", None, {"rocket": 7}]}},
    {"openrocket": {"children": [{"rocket": {"children": [{"subcomponents": {"children": [
        {"stage": {"children": [{"subcomponents": {"children": [None, 3, {"a": 1, "b": 2},
                                                                {"nosecone": "x"}]}}]}}]}}]}}]}},
])
def test_hostile_trees_give_a_normal_result(tree):
    res = check_parts(tree)
    assert res.stage == "parts" and not res.passed and 0 <= res.credit < 1
    assert set(res.info["found"]) == set(ITEMS)


def test_very_deep_nesting_is_fast():
    inner = {"bodytube": {"children": []}}
    top = inner
    for _ in range(20000):
        top = {"bodytube": {"children": [{"subcomponents": {"children": [top]}}]}}
    tree = {"openrocket": {"children": [{"rocket": {"children": [
        {"subcomponents": {"children": [{"stage": {"children": [
            {"subcomponents": {"children": [top]}}]}}]}}]}}]}}
    t0 = time.perf_counter()
    res = check_parts(tree)
    assert time.perf_counter() - t0 < 5
    assert res.info["found"]["body_tube"] and not res.passed


def test_many_parts_are_fast(gold):
    stage = nodes(gold, "stage")[-1]
    holder = next(c for c in stage["stage"]["children"] if "subcomponents" in c)
    holder["subcomponents"]["children"].extend({"bodytube": {"children": []}} for _ in range(200000))
    t0 = time.perf_counter()
    assert check_parts(gold).passed
    assert time.perf_counter() - t0 < 5
