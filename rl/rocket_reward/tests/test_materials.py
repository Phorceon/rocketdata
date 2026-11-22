"""Tests for the material table (materials.py, data/material_table.json)."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from rocket_reward import limits as L
from rocket_reward.errors import RewardSetupError
from rocket_reward.materials import (DEFAULT_TABLE_PATH, MATERIAL_TYPES, MAX_NAME_CHARS, MaterialTable,
                                     SOURCES, loose_name, rocksim_name)
from rocket_reward.tools import build_material_table as BMT


@pytest.fixture(scope="module")
def table() -> MaterialTable:
    return MaterialTable.load()


def small(entries: dict) -> MaterialTable:
    """A table from {type: {name: density}}, every type present."""
    mats = {t: {} for t in MATERIAL_TYPES}
    for t, names in entries.items():
        mats[t] = {n: {"density": d, "source": "preset"} for n, d in names.items()}
    return MaterialTable(mats)


def type_names(answer: str, truncated: bool = False) -> list:
    """(type, name) of every material node in an answer's design, read as the
    material-table tool reads them (one shared helper, tree.material_nodes)."""
    return [(t, n) for _, t, n, _ in (BMT.answer_material_nodes(answer, truncated) or [])]


# ------------------------------------------------------------------ the data file

def test_file_is_utf8_with_lf_endings():
    raw = DEFAULT_TABLE_PATH.read_bytes()
    assert b"\r" not in raw
    raw.decode("utf-8")


def test_table_has_every_type_and_source(table):
    doc = json.loads(DEFAULT_TABLE_PATH.read_text(encoding="utf-8"))
    for t in MATERIAL_TYPES:
        assert len(table.names(t)) >= 40
        sources = {e["source"] for e in doc["materials"][t].values()}
        assert sources == set(SOURCES)
    assert len(table) == sum(len(table.names(t)) for t in MATERIAL_TYPES)


def test_every_density_is_physical():
    """No zero, negative or unit-slip density survives into the table, so no
    massless parachute, line or body part is possible."""
    doc = json.loads(DEFAULT_TABLE_PATH.read_text(encoding="utf-8"))
    for name, e in doc["materials"]["bulk"].items():
        assert L.BULK_DENSITY_MIN_KG_M3 <= e["density"] <= L.BULK_DENSITY_MAX_KG_M3, name
    for name, e in doc["materials"]["surface"].items():
        assert L.SURFACE_MIN_KG_M2 <= e["density"] <= L.SURFACE_DENSITY_MAX_KG_M2, name
    for name, e in doc["materials"]["line"].items():
        assert L.LINE_MIN_KG_M <= e["density"] <= L.LINE_DENSITY_MAX_KG_M, name


def test_stand_ins_copy_a_real_entry():
    doc = json.loads(DEFAULT_TABLE_PATH.read_text(encoding="utf-8"))
    seen = 0
    for t in MATERIAL_TYPES:
        for name, e in doc["materials"][t].items():
            if "stand_in_for" in e:
                seen += 1
                target = doc["materials"][t][e["stand_in_for"]]
                assert target["source"] in ("openrocket", "preset")
                assert e["density"] == target["density"], name
    assert seen >= 1


# ------------------------------------------------------------------ OpenRocket values

@pytest.mark.parametrize("mtype,name,density", [
    ("bulk", "Aluminum", 2700.0),
    ("bulk", "Cardboard", 680.0),
    ("bulk", "Balsa", 170.0),
    ("bulk", "Kraft phenolic", 950.0),
    ("surface", "Ripstop nylon", 0.067),
    ("surface", "Mylar", 0.021),
    ("line", "Braided nylon (2 mm, 1/16 in)", 0.001),
])
def test_openrocket_builtin_values(table, mtype, name, density):
    hit = table.match(mtype, name)
    assert hit is not None and hit.source == "openrocket" and hit.rule == "exact"
    assert hit.density == pytest.approx(density)


def test_preset_and_reference_names(table):
    assert table.source("bulk", "Paper, spiral kraft glassine, Estes avg, bulk") == "preset"
    assert table.lookup("bulk", "Polystyrene PS") == pytest.approx(1049, rel=0.01)
    assert table.source("bulk", "kompozit") == "reference"
    assert table.lookup("bulk", "kompozit") == pytest.approx(1500.0)


def test_zero_density_reference_names_get_a_real_weight(table):
    """The reference designs write these at 0; the table never does."""
    for mtype, name in [("line", "RS: Thin poly"), ("line", "RS: Medium poly"), ("line", "RS: Heavy poly"),
                        ("surface", "RS: Rip stop nylon"), ("surface", "1.9 oz. Ripstop Nylon (SkyAngle)"),
                        ("line", "Nylon IIIa Paraline [flat 6.4 mm, 1/4 in]")]:
        d = table.lookup(mtype, name)
        assert d is not None and d > 0, name


# ------------------------------------------------------------------ matching rules

def test_exact_name_wins_over_loose(table):
    # "Carbon fiber" (OpenRocket, 1780) and "Carbon Fiber" (a preset file, 1400)
    # differ only in case; each finds itself first, any other spelling the heavier
    assert table.match("bulk", "Carbon fiber").density == 1780.0
    hit = table.match("bulk", "Carbon Fiber")
    assert hit.rule == "exact" and hit.density == 1400.0
    hit = table.match("bulk", "CARBON FIBER")
    assert hit.rule == "loose" and hit.density == 1780.0


def test_case_and_spacing_are_ignored(table):
    for written in ("aluminum", "ALUMINUM", "  Aluminum ", "Alu minum".replace(" ", ""), "Aluminum\t"):
        hit = table.match("bulk", written)
        assert hit is not None and hit.name == "Aluminum" and hit.density == 2700.0
    hit = table.match("line", "braided  nylon (2 mm,\t1/16 in)")
    assert hit is not None and hit.rule == "loose" and hit.density == pytest.approx(0.001)


def test_type_is_read_loosely_but_must_match(table):
    assert table.lookup(" Bulk ", "Aluminum") == 2700.0
    assert table.lookup("surface", "Aluminum") is None
    assert table.lookup("metal", "Aluminum") is None
    for bad in (None, 3, ["bulk"], {"bulk": 1}, "x" * 10_000):
        assert table.lookup(bad, "Aluminum") is None


def test_rocksim_prefix_is_ignored_both_ways(table):
    hit = table.match("bulk", "RS: Aluminum")
    assert hit is not None and hit.rule == "rocksim" and hit.name == "Aluminum"
    assert table.lookup("bulk", "rs:aluminum") == 2700.0
    assert table.lookup("bulk", "RS:  Kraft phenolic") is not None
    # a plain name finds the table's "RS: ..." entry
    hit = table.match("line", "Thin poly")
    assert hit is not None and hit.name == "RS: Thin poly" and hit.density > 0


def test_ambiguous_spelling_uses_the_heaviest():
    t = small({"line": {"30 Lb. kevlar": 0.002, "30 Lb. Kevlar": 0.003},
               "bulk": {"Kraft phenolic": 950.0, "RS: Kraft phenolic": 958.7}})
    assert t.lookup("line", "30 Lb. kevlar") == 0.002      # exact
    assert t.lookup("line", "30 lb. KEVLAR") == 0.003      # loose: two candidates, heaviest
    assert t.lookup("bulk", "rs: kraft phenolic") == 958.7  # loose finds the RS entry itself
    assert t.lookup("bulk", "RS:Kraft phenolic") == 958.7   # rocksim: both candidates, heaviest


@pytest.mark.parametrize("name", [None, 7, 2.5, True, [], {}, ["Aluminum"], "", "   ", "RS:", "rs:  ",
                                  "Unobtainium", "Aluminium alloy 7075", "RS: Unobtainium"])
def test_unknown_or_junk_names(table, name):
    assert table.lookup("bulk", name) is None
    assert table.match("bulk", name) is None


def test_long_names_are_never_matched(table):
    assert table.lookup("bulk", "Aluminum" + " " * MAX_NAME_CHARS) is None
    longest = max((n for t in MATERIAL_TYPES for n in table.names(t)), key=len)
    assert len(longest) <= MAX_NAME_CHARS


def test_hostile_input_is_fast(table):
    huge = "RS: " + "a b " * 500_000          # 2 MB of text
    start = time.perf_counter()
    assert table.lookup("bulk", huge) is None
    for i in range(20_000):
        table.lookup("bulk", f"RS:  {'x' * 150} {i}")
        table.lookup("line", " " * 190)
    assert time.perf_counter() - start < 2.0


def test_names_are_sorted_and_typed(table):
    names = table.names("surface")
    assert names == sorted(names) and "Ripstop nylon" in names
    assert table.names("BULK") == table.names("bulk")
    assert table.names("nonsense") == [] and table.names(None) == []


def test_name_helpers():
    assert loose_name("  Kraft \t Phenolic ") == "kraft phenolic"
    assert rocksim_name("RS:  Kraft Phenolic") == "kraft phenolic"
    assert rocksim_name("Kraft RS: phenolic") == "kraft rs: phenolic"
    assert rocksim_name("RS:") == ""


# ------------------------------------------------------------------ broken files

def test_missing_file_says_what_to_fix(tmp_path):
    with pytest.raises(RewardSetupError, match="material_table.json"):
        MaterialTable.load(tmp_path / "nope.json")


@pytest.mark.parametrize("content", [
    "{not json",
    "[]",
    json.dumps({"materials": {}}),
    json.dumps({"materials": {"bulk": {"A": {"density": 1.0, "source": "preset"}}}}),
    json.dumps({"materials": {t: {"A": {"density": 0, "source": "preset"}} for t in MATERIAL_TYPES}}),
    json.dumps({"materials": {t: {"A": {"density": -5.0, "source": "preset"}} for t in MATERIAL_TYPES}}),
    json.dumps({"materials": {t: {"A": {"density": 1.0, "source": "guess"}} for t in MATERIAL_TYPES}}),
    json.dumps({"materials": {t: {"A": {"density": "1", "source": "preset"}} for t in MATERIAL_TYPES}}),
    json.dumps({"materials": {t: {" ": {"density": 1.0, "source": "preset"}} for t in MATERIAL_TYPES}}),
])
def test_broken_file_raises(tmp_path, content):
    p = tmp_path / "material_table.json"
    p.write_text(content, encoding="utf-8")
    with pytest.raises(RewardSetupError, match="rebuild"):
        MaterialTable.load(p)


def test_small_valid_file_loads(tmp_path):
    p = tmp_path / "t.json"
    p.write_text(json.dumps({"materials": {t: {"A": {"density": 2.0, "source": "openrocket"}}
                                           for t in MATERIAL_TYPES}}), encoding="utf-8")
    t = MaterialTable.load(p)
    assert t.lookup("line", "a") == 2.0 and len(t) == 3


# ------------------------------------------------------------------ reference and model answers

def test_every_reference_material_is_known(table, gold_rows):
    """All material nodes in the 48 saved reference answers are known, except
    the documented junk name "RS:" (a Rocksim import with no name)."""
    nodes = [n for row in gold_rows for n in type_names(row["answer"])]
    assert len(nodes) > 900
    unknown = [n for n in nodes if table.match(*n) is None]
    assert all(name == "RS:" for _, name in unknown), unknown


def test_model_answers_unknown_names(table, model_rows):
    """Pins the measurement that sets how strict stage 4 is: 12 of the 48
    saved model answers that pass stage 1 name at least one material the
    table does not know (13 before the stage 1 tag rule; row-031 now fails
    stage 1 for a "cord diameter" tag, so its materials are never reached)."""
    bad = {}
    for row in model_rows:
        names = sorted({f"{t}:{n}" for t, n in type_names(row["content"], row.get("truncated", False))
                        if table.match(t, n) is None})
        if names:
            bad[row["id"]] = names
    assert len(bad) == 12, bad
    assert not any(rid.startswith("row-031") for rid in bad)
    assert bad["row-038-c24331d9"] == ["bulk:Inconel"]


# ------------------------------------------------------------------ checks added on review

def test_tool_takes_density_bounds_from_limits(monkeypatch):
    """The build tool has no bounds of its own: every floor and ceiling is
    read from limits.py when it runs."""
    for name in ("SURFACE_MIN_KG_M2", "LINE_MIN_KG_M", "BULK_DENSITY_MIN_KG_M3"):
        assert not hasattr(BMT, name)
    assert BMT.physical("surface", 0.05)
    monkeypatch.setattr(L, "SURFACE_MIN_KG_M2", 0.1)
    assert not BMT.physical("surface", 0.05)
    monkeypatch.setattr(L, "LINE_MIN_KG_M", 0.01)
    assert not BMT.physical("line", 0.001)


def test_density_floors_sit_below_the_lightest_real_entries(table):
    """The floors only catch unit slips: the lightest real cloth and line in
    OpenRocket's lists are above them (limits.py names both)."""
    assert table.lookup("surface", "Polyethylene film, HDPE, 0.30 mil, bare") == pytest.approx(0.00705)
    assert table.lookup("line", "Kevlar thread, size 23, 0.15 mm dia, 6 lb. test") == pytest.approx(1.98e-05)
    assert min(table.lookup("surface", n) for n in table.names("surface")) == pytest.approx(0.00705)
    assert min(table.lookup("line", n) for n in table.names("line")) == pytest.approx(1.98e-05)


def test_unit_labels_are_reported_and_the_number_read_as_si():
    """Two preset files label six ripstop cloths "g/m2" although the numbers
    are kg/m2 (1.1 oz/yd2 is 0.037 kg/m2). The tool reads the number as SI and
    lists the label in the report."""
    dump = {"builtin": [], "presets": [],
            "declared": [{"file": "datafiles/x/generic.orc", "type": "surface", "name": "Cloth",
                          "density": 0.0341, "units": "g/m2"},
                         {"file": "datafiles/x/generic.orc", "type": "bulk", "name": "Wood",
                          "density": 500.0, "units": "kg/m3"}]}
    materials, notes = BMT.build(dump, [])
    assert materials["surface"]["Cloth"] == {"density": 0.0341, "source": "preset"}
    assert notes["unit_labels"] == [("surface", "Cloth", "generic.orc", 0.0341, "g/m2")]


def test_g_per_m2_labelled_ripstop_has_its_real_weight(table):
    assert 0.030 < table.lookup("surface", "Nylon fabric, ripstop, 1.1 oz actual") < 0.040
    assert table.lookup("surface", "Rip stop nylon") == pytest.approx(0.06685)


@pytest.mark.parametrize("mtype,name,expected", [
    ("bulk", "Balsa\u00a0", "Balsa"),          # a no-break space at the end is spacing
    ("bulk", "Bal\u00a0sa", None),             # but not inside a word
    ("bulk", "Fiberglass\u200b", None),        # an invisible character is not spacing
    ("bulk", "RS : Balsa", None),              # the prefix is exactly "RS:"
    ("bulk", "RS: RS: Balsa", None),           # taken off once only
    ("bulk", "Balsa, bulk", None),             # no guessing at suffixes
    ("bulk", "[material:Balsa]", "[material:Balsa]"),  # a legacy preset name, kept as written
    ("line", "Balsa", None),                   # the type must match
])
def test_tricky_names(table, mtype, name, expected):
    hit = table.match(mtype, name)
    assert (hit.name if hit else None) == expected


@pytest.mark.parametrize("component,tag,expected", [
    ("bodytube", "material", "bulk"), ("nosecone", "material", "bulk"), ("innertube", "material", "bulk"),
    ("centeringring", "material", "bulk"), ("trapezoidfinset", "filletmaterial", "bulk"),
    ("parachute", "material", "surface"), ("streamer", "material", "surface"),
    ("parachute", "linematerial", "line"), ("shockcord", "material", "line"),
    ("bodytube", "linematerial", None), ("bodytube", "filletmaterial", None), ("masscomponent", "material", None),
])
def test_slot_types_follow_openrocket(component, tag, expected):
    """OpenRocket's loader (DocumentConfig) gives each material slot one type."""
    from rocket_reward.materials import slot_type
    assert slot_type(component, tag) == expected


def test_loaded_type_follows_openrocket():
    """No type means the slot's type; any other spelling is ignored (None)."""
    from rocket_reward.materials import loaded_type
    assert loaded_type("bodytube", "material", None) == "bulk"
    assert loaded_type("bodytube", "material", "bulk") == "bulk"
    assert loaded_type("bodytube", "material", "Bulk") is None
    assert loaded_type("bodytube", "material", " bulk") is None
    assert loaded_type("bodytube", "material", "surface") is None
    assert loaded_type("parachute", "material", None) == "surface"
    # a slot OpenRocket does not have: the written type, as before
    assert loaded_type("masscomponent", "material", "line") == "line"
    assert loaded_type("masscomponent", "material", 5) is None


# The unknown names of the model's 48 validation answers (tests/data/model_val.jsonl.gz)
# and of reference V4-0172, with the start of the suggestion each should get.
CLOSE_SPELLINGS = [
    ("bulk", "Paper, spiral kraft glassine, Estes avg", "Paper, spiral kraft glassine, Estes avg, bulk"),
    ("bulk", "Paper, spiral kraft glassine, OK tubular", "Paper, spiral kraft glassine, bulk"),
    ("bulk", "Paper, spiral kraft glassine, PK IIIa, bulk", "Paper, spiral kraft glassine"),
    ("bulk", "Paper, spiral kraft glassine, RK Tubes, loc:03a", "Paper, spiral kraft glassine"),
    ("bulk", "Paper, spiral kraft glassine, OK tubular, bulk, 3/16 in. o.a.", "Paper, spiral kraft glassine"),
    ("bulk", "Paper, spiral kraft, LOC average, bulk", "Paper, spiral kraft"),
    ("bulk", "Paper, spiral kraft, LOC tube avg, bulk", "Paper, spiral kraft"),
    ("line", "Braided nylon (1 mm, 1/16 in)", "Braided nylon (2 mm, 1/16 in)"),
    ("line", "RS: 2 mm braided nylon", "Braided nylon"),
    ("line", "RS: Elastic cord (flat 10 mm, 3/8 in)", "Elastic cord (flat"),
]
NO_CLOSE_SPELLING = [("bulk", "Bronze"), ("bulk", "Inconel"), ("bulk", "Woods"), ("bulk", "Custom"),
                     ("bulk", "RS: Flexible phenolic"), ("bulk", "RS: Hexsonic"), ("surface", "Thin plastic")]


@pytest.mark.parametrize("mtype, name, starts", CLOSE_SPELLINGS)
def test_closest_suggests_a_close_spelling(table, mtype, name, starts):
    near = table.closest(mtype, name)
    assert near is not None and near.startswith(starts), near
    assert table.match(mtype, near) is not None


@pytest.mark.parametrize("mtype, name", NO_CLOSE_SPELLING)
def test_closest_suggests_nothing_for_a_different_material(table, mtype, name):
    """'Bronze' used to get 'Oak (Brown)': a plain spelling match with no bar."""
    assert table.closest(mtype, name) is None


def test_closest_bar_sits_between_the_two_groups(table):
    import difflib
    from rocket_reward.materials import CLOSE_NAME_RATIO_MIN, rocksim_name

    def best(mtype, name):
        key = rocksim_name(name)
        return max(difflib.SequenceMatcher(None, key, rocksim_name(n)).ratio() for n in table.names(mtype))

    close = min(best(t, n) for t, n, _ in CLOSE_SPELLINGS)
    far = max(best(t, n) for t, n in NO_CLOSE_SPELLING)
    assert far < CLOSE_NAME_RATIO_MIN <= close
    assert table.closest("bulk", "cardboard") == "Cardboard"       # a known name finds itself
