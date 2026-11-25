"""Tests for parse.py: stage 1 (format)."""
from __future__ import annotations

import json
import time

import pytest

from rocket_reward import parse
from rocket_reward.ladder import FORMAT_CREDIT_BAD_TREE, FORMAT_MAX_DEPTH as MAX_DEPTH
from rocket_reward.ladder import FORMAT_MAX_JSON_BYTES as MAX_JSON_BYTES, FORMAT_READ_CEILING_BYTES
from rocket_reward.parse import parse_answer
from rocket_reward.tree import tag_of

TINY = {"openrocket": {"attrs": {"version": "1.9"}, "children": [
    {"rocket": {"children": [{"name": {"value": "R"}}, {"length": {"value": 0.5}},
                             {"flag": {"value": True}}, {"none": {"value": None}}]}}]}}


def wrap(json_text: str, before: str = "<thought>\nplan\n</thought>\n", after: str = "\n") -> str:
    return f"{before}<design>\n{json_text}\n</design>{after}"


def ok(text: str):
    check, root = parse_answer(text)
    assert check.passed, check.reasons
    assert check.stage == "format" and check.credit == 1.0
    assert root is not None and tag_of(root) == "openrocket"
    return check, root


def fails(text: str, credit: float, *, truncated: bool = False, words: str = ""):
    check, root = parse_answer(text, truncated)
    assert not check.passed and root is None
    assert check.stage == "format"
    assert check.credit == credit, check.reasons
    assert len(check.reasons) == 1
    assert words in check.reasons[0], check.reasons
    return check


# ------------------------------------------------------------------ real answers

def test_every_gold_answer_passes(gold_rows):
    for row in gold_rows:
        ok(row["answer"])


def test_model_answers_match_hand_reading(model_rows):
    """What a person sees in the 48 saved answers: two were cut off, one puts
    a nested object in attrs, one puts a second key next to a node's tag, one
    writes tags with spaces ("cord diameter"), and ten add a second top-level
    key next to "openrocket"."""
    by_id = {r["id"][:7]: r for r in model_rows}
    results = {k: parse_answer(r["content"], r["truncated"]) for k, r in by_id.items()}
    cut = {k for k, r in by_id.items() if r["truncated"]}
    assert cut == {"row-029", "row-034"}
    for k in cut:
        assert results[k][0].credit == 0.0
    assert results["row-007"][0].credit == 0.75 and "attribute" in results["row-007"][0].reasons[0]
    assert results["row-018"][0].credit == 0.75 and "exactly one tag" in results["row-018"][0].reasons[0]
    assert results["row-031"][0].credit == 0.75 and "cord diameter" in results["row-031"][0].reasons[0]
    passed = [k for k, (c, _) in results.items() if c.passed]
    assert len(passed) == 43
    extra = [k for k in passed if results[k][0].info.get("ignored_top_keys")]
    assert len(extra) == 10
    assert results["row-002"][0].info["ignored_top_keys"] == ["simulations"]


def test_truncated_model_answer_without_flag_still_fails(model_rows):
    row = next(r for r in model_rows if r["truncated"])
    fails(row["content"], 0.0, words="never closed")


# ------------------------------------------------------------------ finding the block

def test_cut_off_flag_scores_zero_even_with_a_good_block():
    fails(wrap(json.dumps(TINY)), 0.0, truncated=True, words="cut off")


@pytest.mark.parametrize("text", ["", "no design here", "<thought>x</thought>",
                                  "<design>{\"openrocket\": {}}", "</design>{} <design>",
                                  "<DESIGN>{}</DESIGN>"])
def test_no_complete_block_scores_zero(text):
    fails(text, 0.0)


@pytest.mark.parametrize("odd", [None, 5, b"<design>{}</design>", ["<design>"], {"a": 1}])
def test_answer_that_is_not_text(odd):
    fails(odd, 0.0, words="must be text")  # type: ignore[arg-type]


def test_text_around_the_block_is_ignored():
    _, root = ok(wrap(json.dumps(TINY), after="\nThat is my design. Fly safe!\n"))
    assert root == TINY
    check, _ = ok(wrap(json.dumps(TINY), before="", after="  \n\n "))
    assert check.info["chars_after_block"] == 0


def test_first_complete_block_is_used():
    second = {"openrocket": {"children": [{"rocket": {"children": []}}]}}
    text = wrap(json.dumps(TINY)) + wrap(json.dumps(second))
    _, root = ok(text)
    assert root == TINY
    check, _ = parse_answer(text)
    assert check.info["open_tags"] == 2


def test_stray_open_tag_in_thought_does_not_swallow_the_block():
    text = "<thought>I will write the <design> block next.</thought>\n" + wrap(json.dumps(TINY), before="")
    _, root = ok(text)
    assert root == TINY


def test_broken_first_block_is_not_skipped():
    """The first complete block decides; a later good block does not rescue it."""
    text = wrap("{not json") + wrap(json.dumps(TINY))
    fails(text, 0.5)


def test_close_tag_before_any_open_tag_is_skipped():
    _, root = ok("stray </design> text " + wrap(json.dumps(TINY)))
    assert root == TINY


# ------------------------------------------------------------------ JSON problems

@pytest.mark.parametrize("bad", ["", "{", "{'openrocket': {}}", "{\"openrocket\": {},}",
                                 "{\"openrocket\": {}} trailing", "[1, 2", "\"unterminated"])
def test_json_that_does_not_parse_scores_half(bad):
    fails(wrap(bad), 0.5, words="does not parse")


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity"])
def test_nan_and_infinity_tokens_are_rejected(token):
    text = wrap('{"openrocket": {"children": [{"length": {"value": %s}}]}}' % token)
    fails(text, 0.5, words=token)


@pytest.mark.parametrize("number", ["1e999", "-1e999", "1" * 400])
def test_numbers_too_large_for_a_float_are_rejected(number):
    text = wrap('{"openrocket": {"children": [{"length": {"value": %s}}]}}' % number)
    fails(text, 0.75, words="too large")
    text = wrap('{"openrocket": {"attrs": {"v": %s}}}' % number)
    fails(text, 0.75, words="too large")


def test_integer_too_long_for_python_does_not_crash():
    text = wrap('{"openrocket": {"children": [{"fincount": {"value": %s}}]}}' % ("9" * 5000))
    check, root = parse_answer(text)
    assert not check.passed and check.credit in (0.5, 0.75)


def test_repeated_keys_are_rejected():
    text = wrap('{"openrocket": {"children": [{"fincount": {"value": 3, "value": 4}}]}}')
    fails(text, 0.75, words="repeats the key 'value'")


# ------------------------------------------------------------------ tree shape

def shape(doc) -> str:
    return wrap(json.dumps(doc))


BAD_SHAPES = [
    ("top level is a list", [TINY], "\"openrocket\" root"),
    ("top level is a number", 5, "\"openrocket\" root"),
    ("wrong root", {"rocket": {}}, "\"openrocket\" root"),
    ("root body is a list", {"openrocket": []}, "must hold an object"),
    ("root body is text", {"openrocket": "x"}, "must hold an object"),
    ("unknown body key", {"openrocket": {"kids": []}}, "only attrs, value and children"),
    ("attrs is a list", {"openrocket": {"attrs": ["a"]}}, "attrs of"),
    ("attr value is an object", {"openrocket": {"attrs": {"a": {"b": 1}}}}, "plain value"),
    ("attr value is a list", {"openrocket": {"attrs": {"a": [1]}}}, "plain value"),
    ("value is an object", {"openrocket": {"value": {"a": 1}}}, "plain value"),
    ("value is a list", {"openrocket": {"value": [1]}}, "plain value"),
    ("children is an object", {"openrocket": {"children": {"rocket": {}}}}, "must be a list"),
    ("child is text", {"openrocket": {"children": ["rocket"]}}, "exactly one tag"),
    ("child has two tags", {"openrocket": {"children": [{"a": {}, "b": {}}]}}, "exactly one tag"),
    ("child has no tag", {"openrocket": {"children": [{}]}}, "exactly one tag"),
    ("empty tag", {"openrocket": {"children": [{"": {}}]}}, "empty"),
    ("child body null", {"openrocket": {"children": [{"a": None}]}}, "must hold an object"),
    ("deep bad node", {"openrocket": {"children": [{"rocket": {"children": [
        {"subcomponents": {"children": [{"stage": {"children": [{"x": {"value": {}}}]}}]}}]}}]}},
     "plain value"),
]


@pytest.mark.parametrize("label,doc,words", BAD_SHAPES, ids=[b[0] for b in BAD_SHAPES])
def test_bad_tree_shapes_score_three_quarters(label, doc, words):
    fails(shape(doc), 0.75, words=words)


def test_shape_reasons_say_what_to_write():
    """A node with two tags names them and says how to write a child; a value
    that is not plain says what a plain value is."""
    two = fails(shape({"openrocket": {"children": [{"nosecone": {}, "material": {}}]}}), 0.75)
    assert "2 keys ('nosecone', 'material')" in two.reasons[0] and "its own" in two.reasons[0]
    attr = fails(shape({"openrocket": {"attrs": {"attrs": {"configid": "c"}}}}), 0.75)
    assert "a text, a number, true, false or null" in attr.reasons[0]


BAD_TAGS = ["cord diameter", "1stage", "-fin", ".fin", "<nosecone>", "or:rocket", "fin\n", "größe",
            "a/b", "x y", "٣"]
GOOD_TAGS = ["a", "_x", "nosecone", "tube-fin.set_2", "A9", "_"]


@pytest.mark.parametrize("tag", BAD_TAGS)
def test_a_tag_that_is_not_an_xml_name_makes_the_tree_invalid(tag):
    deep = {"openrocket": {"children": [{"rocket": {"children": [
        {"subcomponents": {"children": [{"shockcord": {"children": [{tag: {"value": 0.003}}]}}]}}]}}]}}
    check = fails(shape(deep), 0.75, words="not a valid XML element name")
    assert "shockcord" in check.reasons[0]


@pytest.mark.parametrize("tag", GOOD_TAGS)
def test_xml_name_tags_are_fine(tag):
    ok(shape({"openrocket": {"children": [{tag: {"value": 1}}]}}))


def test_attribute_names_and_ignored_top_keys_are_not_tags():
    """The rule is about node tags only: the second top-level key is dropped
    unread, and attribute names are left to later stages."""
    ok(shape({"openrocket": {"attrs": {"odd name": 1}}, "my simulations": {}}))


def test_no_gold_or_model_answer_breaks_the_tag_rule_except_row_031(gold_rows, model_rows):
    for row in gold_rows:
        ok(row["answer"])
    hit = [r["id"][:7] for r in model_rows
           if "XML element name" in " ".join(parse_answer(r["content"], r["truncated"])[0].reasons)]
    assert hit == ["row-031"]


def test_extra_top_level_keys_are_ignored_and_noted():
    doc = {"openrocket": TINY["openrocket"], "simulations": {"anything": [1, {"x": None}]}}
    check, root = ok(shape(doc))
    assert root == TINY
    assert check.info["ignored_top_keys"] == ["simulations"]


def test_empty_bodies_and_null_values_are_fine():
    ok(shape({"openrocket": {}}))
    ok(shape({"openrocket": {"children": [{"a": {}}, {"b": {"value": None}}, {"c": {"children": []}}]}}))


def test_nothing_is_repaired():
    """The returned tree is exactly what the model wrote."""
    _, root = ok(shape(TINY))
    assert root == TINY


# ------------------------------------------------------------------ caps

def chain(levels: int) -> dict:
    node: dict = {"leaf": {"value": 1}}
    for _ in range(levels - 2):
        node = {"x": {"children": [node]}}
    return {"openrocket": {"children": [node]}}


def test_depth_cap_is_exact():
    ok(shape(chain(MAX_DEPTH)))
    fails(shape(chain(MAX_DEPTH + 1)), 0.75, words=f"more than {MAX_DEPTH} levels")


def test_absurdly_deep_json_does_not_crash():
    text = wrap('{"openrocket": {"children": [' + '{"x": {"children": [' * 50_000 + ']}}' * 50_000 + "]}}")
    t0 = time.perf_counter()
    check, _ = parse_answer(text)
    assert not check.passed and check.credit in (0.5, 0.75)
    assert time.perf_counter() - t0 < 5
    fails(wrap("[" * 100_000 + "]" * 100_000), 0.75)


@pytest.mark.parametrize("text", ["[" * 200_000, '{"a": ' * 100_000, "[" * 100_000 + "]" * 99_999,
                                  "[" * 100_000 + "1,]" + "]" * 99_999],
                         ids=["open-lists", "open-objects", "one-short", "trailing-comma"])
def test_deep_json_that_never_closes_scores_like_bad_json(text):
    t0 = time.perf_counter()
    fails(wrap(text), 0.5, words="does not parse")
    assert time.perf_counter() - t0 < 5


def test_json_syntax_check_agrees_with_the_json_reader():
    import random
    rnd = random.Random(7)
    pieces = ["[", "]", "{", "}", ",", ":", '"a"', "1", " ", "null", "-0.5e3", '"\\u00"']
    for _ in range(5000):
        text = "".join(rnd.choice(pieces) for _ in range(rnd.randint(0, 10)))
        try:
            json.loads(text, parse_constant=parse._no_constants)
            want = True
        except ValueError:
            want = False
        assert parse.json_syntax_ok(text) == want, text


def test_size_cap():
    filler = "a" * (MAX_JSON_BYTES - 200)
    ok(shape({"openrocket": {"children": [{"note": {"value": filler}}]}}))
    big = "a" * (MAX_JSON_BYTES + 10)
    fails(shape({"openrocket": {"children": [{"note": {"value": big}}]}}), 0.75, words="kB")


def test_size_is_counted_in_utf8_bytes():
    wide = "é" * (MAX_JSON_BYTES // 2 + 10)   # 2 bytes each in UTF-8
    fails(shape({"openrocket": {"children": [{"note": {"value": wide}}]}}), 0.75, words="kB")


def test_huge_text_is_not_read_and_never_beats_a_large_tree():
    junk = wrap("x" * (FORMAT_READ_CEILING_BYTES + 1))
    t0 = time.perf_counter()
    check = fails(junk, 0.5, words="too large to read")
    assert time.perf_counter() - t0 < 2
    assert check.credit < FORMAT_CREDIT_BAD_TREE


def test_padding_bad_json_does_not_raise_credit():
    """Making broken JSON bigger than the cap must not move it from 0.5 to 0.75."""
    fails(wrap("{" + " " * (MAX_JSON_BYTES + 5)), 0.5)


def test_many_fins_and_wide_trees_are_quick():
    kids = [{"f": {"value": 1}} for i in range(13_000)]   # about 275 kB, just under the cap
    text = shape({"openrocket": {"children": kids}})
    t0 = time.perf_counter()
    ok(text)
    assert time.perf_counter() - t0 < 2
    ok(shape({"openrocket": {"children": [{"fincount": {"value": 10**9}}]}}))


def test_parse_never_raises_on_random_garbage():
    import random
    rng = random.Random(1234)
    pieces = ["{", "}", "[", "]", ",", ":", "\"a\"", "\"openrocket\"", "\"children\"", "\"attrs\"",
              "\"value\"", "1", "-0.5e3", "null", "true", "NaN", " ", "<design>", "</design>"]
    for _ in range(2000):
        body = "".join(rng.choice(pieces) for _ in range(rng.randint(0, 40)))
        check, root = parse_answer(wrap(body))
        assert check.stage == "format"
        assert (root is not None) == check.passed
        assert 0.0 <= check.credit <= 1.0
