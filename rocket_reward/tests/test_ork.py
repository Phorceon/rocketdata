"""Tests for ork.py (design tree -> OpenRocket file). None of these need Java;
the flown parity check lives in ork_checks/parity.py."""
from __future__ import annotations

import json
import math
import xml.etree.ElementTree as ET

import pytest

from rocket_reward.ork import OrkWriteError, design_to_ork
from rocket_reward.tree import java_number, make_node

TABLE = {
    "AeroTech-G74W": {"manufacturer": "AeroTech", "designation": "G74W",
                      "digest": "d1g3st000000000000000000000000aa"},
}


def doc(*rocket_children, attrs=None, extra=()):
    rocket = make_node("rocket", children=list(rocket_children))
    return make_node("openrocket", attrs=attrs or {"version": "1.10"},
                     children=[rocket, *extra])


def motor(*kids):
    return make_node("motor", attrs={"configid": "cfg0"}, children=list(kids))


def parse(text: str) -> ET.Element:
    assert text.startswith("<?xml version='1.0' encoding='utf-8'?>\n")
    assert "\r" not in text
    text.encode("utf-8")  # must be encodable
    return ET.fromstring(text.encode("utf-8"))


def write(root, motors=TABLE) -> ET.Element:
    return parse(design_to_ork(root, motors))


# ----------------------------------------------------------------- structure

def test_nesting_order_attrs_and_values():
    root = doc(make_node("name", "R"),
               make_node("axialoffset", 0.25, attrs={"method": "top"}),
               make_node("subcomponents", children=[
                   make_node("stage", children=[make_node("name", "S")]),
                   make_node("stage", children=[make_node("name", "T")])]))
    x = write(root)
    assert x.tag == "openrocket" and x.get("version") == "1.10"
    rocket = x.find("rocket")
    assert [c.tag for c in rocket] == ["name", "axialoffset", "subcomponents"]
    assert rocket.find("axialoffset").get("method") == "top"
    assert rocket.find("axialoffset").text == "0.25"
    assert [s.find("name").text for s in rocket.find("subcomponents")] == ["S", "T"]


def test_file_version_is_always_the_one_openrocket_writes():
    """The version changes how OpenRocket reads the file (below 1.4 the motor
    digest is ignored, 1.11 gives a warning), so the design never chooses it."""
    for attrs in ({}, {"version": 1.8}, {"version": "1.11"}, {"version": "1.2"}, {"version": None}):
        assert write(doc(attrs=attrs)).get("version") == "1.10"


@pytest.mark.parametrize("value, text", [
    (0.1, "0.1"), (0.6095999999999999, "0.6095999999999999"), (6.870602662363831e-4, "0.0006870602662363831"),
    (1e-20, "1e-20"), (1e300, "1e+300"), (-0.0, "-0.0"), (3, "3"), (True, "true"), (False, "false"),
    ("auto 0.033528", "auto 0.033528"),
])
def test_numbers_and_flags_read_back_exactly(value, text):
    x = write(doc(make_node("v", value, attrs={"a": value})))
    el = x.find("rocket/v")
    assert el.text == text and el.get("a") == text
    if isinstance(value, float) and math.isfinite(value):
        assert float(el.text) == value  # Java's Double.parseDouble reads the same spelling


@pytest.mark.parametrize("value, text", [
    ("6.870602662363831E-4", "0.0006870602662363831"), ("0.5f", "0.5"), ("0x1p-3", "0.125"),
    ("  0.25  ", "0.25"), ("+2.5D", "2.5"), ("007", "7"), ("0.0", "0.0"), (".5e1", "5.0"),
    ("auto 0.03", "auto 0.03"), ("filled", "filled"), ("1_0", "1_0"),
])
def test_numbers_written_as_text_are_written_as_the_number_the_reward_read(value, text):
    """Stage 4 reads "0.5f" as 0.5 (tree.java_number); the file must say 0.5,
    so the value checked is exactly the value that flies."""
    x = write(doc(make_node("thickness", value),
                  make_node("material", "Cardboard", attrs={"density": value, "configid": value})))
    assert x.find("rocket/thickness").text == text
    m = x.find("rocket/material")
    assert m.get("density") == text and m.get("configid") == value  # only numeric attributes change
    if java_number(value) is not None:
        assert float(text) == java_number(value)


def test_names_keep_number_like_text():
    x = write(doc(make_node("name", "0.5f"), make_node("material", "1e-3", attrs={"type": "0x1p0"})))
    assert x.find("rocket/name").text == "0.5f" and x.find("rocket/material").text == "1e-3"
    assert x.find("rocket/material").get("type") == "0x1p0"


@pytest.mark.parametrize("value, text", [(3.0, "3"), ("4.0", "4"), (3.0000001, "3"), (" 5 ", "5"),
                                         (2.5, "2.5"), (6, "6")])
def test_whole_counts_are_written_as_digits(value, text):
    """OpenRocket reads fin, instance and line counts with Java's integer
    reader, which refuses "3.0" and keeps its default count."""
    for tag in ("fincount", "instancecount", "linecount"):
        assert write(doc(make_node(tag, value))).find(f"rocket/{tag}").text == text


def test_empty_value_and_empty_children():
    x = write(doc(make_node("a"), make_node("b", children=[]), make_node("c", "")))
    assert [x.find(f"rocket/{t}").text for t in "abc"] == [None, None, None]


# ----------------------------------------------------------------- escaping

def test_markup_in_strings_is_escaped():
    nasty = 'a & b < c > d "q" \'s\' ]]> <!-- x --> <![CDATA[y]]> &amp;'
    x = write(doc(make_node("material", nasty, attrs={"type": nasty})))
    el = x.find("rocket/material")
    assert el.text == nasty and el.get("type") == nasty
    assert len(list(x.find("rocket"))) == 1  # no element was injected


def test_whitespace_in_attributes_survives():
    s = "line1\nline2\tTab\rCR"
    x = write(doc(make_node("n", s, attrs={"a": s})))
    assert x.find("rocket/n").get("a") == s
    assert x.find("rocket/n").text == s


def test_control_characters_and_lone_surrogates_are_replaced():
    lone = chr(0xDFFF) + chr(0xD800)  # two lone surrogates, as json.loads can produce
    s = "ok" + "".join(map(chr, (0, 1, 8, 0x0B, 0x0C, 0x1F))) + lone + chr(0xFFFE) + chr(0xFFFF) + "-end"
    x = write(doc(make_node("n", s, attrs={"a": s})))
    expect = "ok" + chr(0xFFFD) * 10 + "-end"
    assert x.find("rocket/n").text == expect
    assert x.find("rocket/n").get("a") == expect


def test_unicode_is_kept():
    s = "PolystyrÃ¨ne âœ“ ç«ç®­ \U0001f680"
    assert write(doc(make_node("n", s))).find("rocket/n").text == s


# ----------------------------------------------------------------- dropped tags and the motor

def test_motor_id_becomes_table_digest_in_place():
    m = motor(make_node("type", "single"), make_node("manufacturer", "AeroTech"),
              make_node("motor_id", "AeroTech-G74W"), make_node("designation", "G74W"),
              make_node("delay", 9.0))
    x = write(doc(m))
    el = x.find(".//motor")
    assert [c.tag for c in el] == ["type", "manufacturer", "digest", "designation", "delay"]
    assert el.find("digest").text == TABLE["AeroTech-G74W"]["digest"]
    assert x.find(".//motor_id") is None


def test_design_digest_never_used():
    m = motor(make_node("digest", "evil"), make_node("motor_id", "AeroTech-G74W"),
              make_node("designation", "G74W"))
    x = write(doc(m))
    assert [d.text for d in x.iter("digest")] == [TABLE["AeroTech-G74W"]["digest"]]
    m2 = motor(make_node("digest", "evil"), make_node("designation", "G74W"))
    assert list(write(doc(m2)).iter("digest")) == []


def test_unknown_motor_id_writes_no_digest():
    m = motor(make_node("motor_id", "Nobody-X1"), make_node("designation", "X1"))
    x = write(doc(m))
    assert x.find(".//digest") is None and x.find(".//motor_id") is None
    assert x.find(".//designation").text == "X1"


def test_motor_lookup_ignores_case_and_accepts_a_function():
    m = motor(make_node("motor_id", "aerotech-g74w"))
    el = write(doc(m)).find(".//motor")
    assert el.find("digest").text == TABLE["AeroTech-G74W"]["digest"]
    # maker and designation filled in from the table when the design leaves them out
    assert el.find("manufacturer").text == "AeroTech" and el.find("designation").text == "G74W"
    seen = []
    el = write(doc(motor(make_node("motor_id", "Q"))),
               motors=lambda mid: seen.append(mid) or {"digest": "abc"}).find(".//motor")
    assert seen == ["Q"] and el.find("digest").text == "abc"


def test_default_motor_table_is_used():
    x = parse(design_to_ork(doc(motor(make_node("motor_id", "AeroTech-G74W"),
                                      make_node("designation", "G74W")))))
    d = x.find(".//digest")
    assert d is not None and len(d.text) == 32


def test_simulations_dropped_wherever_they_sit():
    sims = make_node("simulations", children=[make_node("simulation", children=[
        make_node("conditions", children=[make_node("windaverage", 50.0)])])])
    root = doc(make_node("subcomponents", children=[make_node("stage", children=[sims])]),
               extra=[sims])
    x = write(root)
    assert x.find(".//simulations") is None and x.find(".//windaverage") is None
    assert x.find("rocket/subcomponents/stage") is not None


# ----------------------------------------------------------------- hostile input

@pytest.mark.parametrize("tag", ["", "a b", "1abc", "x:y", "<x>", "a\x00", "Ã©", "a/b", "-a", 5, None])
def test_bad_tag_names_raise(tag):
    with pytest.raises(OrkWriteError):
        design_to_ork(doc({tag: {"value": 1}}), TABLE)


@pytest.mark.parametrize("name", ["", "a b", "x:y", 'a="1" b', "1a"])
def test_bad_attribute_names_raise(name):
    with pytest.raises(OrkWriteError):
        design_to_ork(doc(make_node("n", 1, attrs={name: "v"})), TABLE)


@pytest.mark.parametrize("node", [
    {"n": {"value": [1, 2]}}, {"n": {"value": {"a": 1}}}, {"n": {"attrs": {"a": [1]}}},
    {"n": {"attrs": [1]}}, {"n": {"children": {"a": {}}}}, {"n": {"children": [1]}},
    {"n": {"children": [{"a": {}, "b": {}}]}}, {"n": 5}, {"a": {}, "b": {}}, [],
])
def test_malformed_nodes_raise(node):
    with pytest.raises(OrkWriteError):
        design_to_ork(doc(node), TABLE)


def test_bad_roots_raise():
    with pytest.raises(OrkWriteError):
        design_to_ork(make_node("rocket"), TABLE)
    with pytest.raises(OrkWriteError):
        design_to_ork(make_node("openrocket", children=[make_node("name", "x")]), TABLE)
    with pytest.raises(OrkWriteError):
        design_to_ork(make_node("openrocket", attrs=None, children=None), TABLE)


def test_huge_integer_raises_cleanly():
    with pytest.raises(OrkWriteError):
        design_to_ork(doc(make_node("n", 10 ** 5000)), TABLE)
    with pytest.raises(OrkWriteError):
        design_to_ork(doc(make_node("n", 10 ** 400)), TABLE)  # prints fine, but no double holds it


@pytest.mark.parametrize("value", [
    math.nan, math.inf, -math.inf,
    "NaN", "nan", "NAN", "Infinity", "-Infinity", "infinity", "inf", "-inf", "+Inf", "1e999", "-1E400",
    "auto NaN", " NaN ", "auto 1e999",
])
def test_non_finite_numbers_raise_in_values_and_attributes(value):
    """OpenRocket skips a value it cannot read (or flies an infinite one) and keeps
    a default, so a different rocket would fly: such values are refused."""
    with pytest.raises(OrkWriteError) as err:
        design_to_ork(doc(make_node("mass", value)), TABLE)
    assert "finite" in str(err.value)
    with pytest.raises(OrkWriteError):
        design_to_ork(doc(make_node("material", "Kraft phenolic", attrs={"type": "bulk", "density": value})), TABLE)


def test_words_that_only_look_like_numbers_in_names_are_kept():
    """Free text (names, materials, designations) is never read as a number."""
    x = write(doc(make_node("name", "Infinity"), make_node("material", "NaN", attrs={"type": "bulk"}),
                  make_node("comment", "inf")))
    assert x.find("rocket/name").text == "Infinity" and x.find("rocket/material").text == "NaN"
    assert write(doc(make_node("n", "auto 0.033"))).find("rocket/n").text == "auto 0.033"
    assert write(doc(make_node("n", "information"))).find("rocket/n").text == "information"


def test_huge_strings_and_deep_trees_do_not_break():
    big = "<&>" * 300_000
    x = write(doc(make_node("n", big, attrs={"a": big})))
    assert x.find("rocket/n").text == big
    node = make_node("leaf", 1)
    for _ in range(5000):  # far deeper than Python's recursion limit
        node = make_node("d", children=[node])
    text = design_to_ork(doc(node), TABLE)
    assert text.count("<d>") == 5000 and "<leaf>1</leaf>" in text


def test_output_is_deterministic():
    root = doc(make_node("a", 0.1, attrs={"z": 1, "b": 2}), motor(make_node("motor_id", "AeroTech-G74W")))
    assert design_to_ork(root, TABLE) == design_to_ork(json.loads(json.dumps(root)), TABLE)


def test_input_is_not_changed():
    root = doc(motor(make_node("motor_id", "AeroTech-G74W")),
               extra=[make_node("simulations")])
    before = json.dumps(root, sort_keys=True)
    design_to_ork(root, TABLE)
    assert json.dumps(root, sort_keys=True) == before


# ----------------------------------------------------------------- the 48 gold designs

def _design(answer: str) -> dict:
    i = answer.find("<design>")
    j = answer.find("</design>", i)
    obj = json.loads(answer[i + len("<design>"):j])
    return {"openrocket": obj["openrocket"]}


def _json_preorder(node, out, path=()):
    (tag, body), = node.items()
    if tag in ("simulations", "motor_id"):
        return
    out.append(("/".join(path + (tag,)), body.get("attrs") or {}, body.get("value")))
    for c in body.get("children") or []:
        _json_preorder(c, out, path + (tag,))


def _xml_preorder(el, out, path=()):
    if el.tag == "digest":
        return
    text = el.text
    if len(el) and text is not None:  # layout whitespace around child elements
        text = text.strip() or None
    out.append(("/".join(path + (el.tag,)), dict(el.attrib), text))
    for c in el:
        _xml_preorder(c, out, path + (el.tag,))


def _same(json_val, xml_text):
    if json_val is None:
        return xml_text is None
    if isinstance(json_val, bool):
        return xml_text == ("true" if json_val else "false")
    if isinstance(json_val, (int, float)):
        return float(xml_text) == float(json_val)
    if xml_text != json_val and java_number(json_val) is not None:
        return float(xml_text) == java_number(json_val)   # number text written canonically
    return xml_text == json_val


def test_all_gold_designs_convert_and_parse_back(gold_rows):
    assert len(gold_rows) == 48
    for row in gold_rows:
        root = _design(row["answer"])
        x = parse(design_to_ork(root))
        want, got = [], []
        _json_preorder(root, want)
        _xml_preorder(x, got)
        assert [w[0] for w in want] == [g[0] for g in got], row["id"]
        for (path, wa, wv), (_, ga, gv) in zip(want, got):
            assert set(wa) == set(ga) or path == "openrocket", (row["id"], path)
            for k, v in wa.items():
                if (path, k) == ("openrocket", "version"):
                    assert ga[k] == "1.10"
                    continue
                assert _same(v, ga[k]), (row["id"], path, k)
            assert _same(wv, gv), (row["id"], path, wv, gv)
        # every motor that names a known motor id carries exactly one digest
        motors = x.findall(".//motor")
        assert motors, row["id"]
        for m in motors:
            assert len(m.findall("digest")) == 1, row["id"]
        assert x.find(".//simulations") is None


# ---------------------------------------------------------------- flight configuration id

def test_flight_config_id_prefers_the_default_then_the_first():
    from rocket_reward.ork import flight_config_id
    a = make_node("motorconfiguration", attrs={"configid": "a"})
    b = make_node("motorconfiguration", attrs={"configid": "b", "default": True})
    assert flight_config_id(doc(a, b)) == "b"
    assert flight_config_id(doc(a)) == "a"
    assert flight_config_id(doc(make_node("motorconfiguration", attrs={"configid": "c", "default": "true"}), a)) == "c"
    assert flight_config_id(doc()) is None
    assert flight_config_id({"openrocket": "junk"}) is None
    assert flight_config_id([]) is None
