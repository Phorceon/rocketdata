"""Stage 3 (motors.py): every flown motor is a real one."""
from __future__ import annotations

import copy
import json
import time

import pytest

from answers import design_of
from rocket_reward.errors import RewardSetupError
from rocket_reward.tree import find_all as nodes
from rocket_reward.motors import (MotorTable, check_motors, class_from_designation, flown_config_id,
                                  flown_motors, impulse_class)





@pytest.fixture(scope="module")
def table():
    return MotorTable.load()


@pytest.fixture(scope="module")
def gold_designs(gold_rows):
    return [(r["id"], design_of(r["answer"])) for r in gold_rows]


@pytest.fixture()
def gold(gold_designs):
    """A fresh copy of a one-stage reference rocket flying AeroTech-H148R-v1."""
    return copy.deepcopy(gold_designs[9][1])


def set_fields(motor, **fields):
    """Replace (or with value ... remove) children of a motor node."""
    body = motor["motor"]
    kids = [c for c in body["children"] if next(iter(c)) not in fields]
    for tag, value in fields.items():
        if value is not ...:
            kids.append({tag: {"value": value}})
    body["children"] = kids


def make_motor(motor_id=..., maker=..., designation=..., diameter=..., configid="cfg0"):
    m = {"motor": {"attrs": {"configid": configid}, "children": []}}
    set_fields(m, motor_id=motor_id, manufacturer=maker, designation=designation, diameter=diameter)
    return m


def with_motors(gold, motors):
    """Put exactly these motor nodes in the gold rocket's first motor mount."""
    mounts = nodes(gold, "motormount")
    for mm in mounts:
        mm["motormount"]["children"] = [c for c in mm["motormount"]["children"] if "motor" not in c]
    mounts[0]["motormount"]["children"].extend(motors)
    return gold


# ---------------------------------------------------------------------------
# the table

def test_table_loads(table):
    assert len(table) == 1409  # every motor OpenRocket 24.12 has a thrust curve for
    assert "AeroTech-M2000R-v2" in table
    e = table.get("AeroTech-M2000R-v2")
    assert e["manufacturer"] == "AeroTech" and e["diameter_m"] == pytest.approx(0.098)


def test_missing_table_is_a_setup_error(tmp_path):
    with pytest.raises(RewardSetupError, match="not found"):
        MotorTable.load(tmp_path / "nope.json")


@pytest.mark.parametrize("content", ["{not json", "[]", "{}", '{"X-A1": 3}', '{"X-A1": {"designation": "A1"}}'])
def test_broken_table_is_a_setup_error(tmp_path, content):
    p = tmp_path / "t.json"
    p.write_text(content, encoding="utf-8")
    with pytest.raises(RewardSetupError, match="motor_table.json"):
        MotorTable.load(p)


def test_unreadable_bytes_are_a_setup_error(tmp_path):
    p = tmp_path / "t.json"
    p.write_bytes(b"\xff\xfe\x00garbage")
    with pytest.raises(RewardSetupError):
        MotorTable.load(p)


@pytest.mark.parametrize("written, key", [
    ("AeroTech-M2000R-v2", "AeroTech-M2000R-v2"),
    ("aerotech-m2000r-V2", "AeroTech-M2000R-v2"),
    ("AeroTech-HP-L1000W", "AeroTech-HP-L1000W-v1"),     # versions 1 and 2 exist: lowest wins
    ("  AeroTech-G74W ", "AeroTech-G74W"),
    ("AEROTECH-G74W", "AeroTech-G74W"),
])
def test_accepted_aliases(table, written, key):
    assert table.resolve(written) == key


@pytest.mark.parametrize("written", [
    "AeroTech-H195NT",            # the real one is AeroTech-HP-H195NT: never auto-corrected
    "AeroTech-M2000R-v9",         # a version that does not exist
    "AeroTech-G74W-v1",           # the table has G74W with no version
    "Cesaroni Technology-K550W",  # K550W is real, but only from AeroTech
    "M2000R", "", "   ", 42, 4.2, True, ["AeroTech-G74W"], {"id": "x"},
    "AeroTech-G74W" * 100000,
], ids=lambda x: repr(x)[:40])
def test_rejected_ids(table, written):
    assert table.resolve(written) is None


def test_no_motor_id_uses_maker_and_designation(table):
    assert table.resolve(None, "AeroTech", "G74W") == "AeroTech-G74W"
    assert table.resolve("", "aerotech", "g74w") == "AeroTech-G74W"
    assert table.resolve(None, "AeroTech", "HP-L1000W") == "AeroTech-HP-L1000W-v1"
    assert table.resolve(None, "Estes", "G74W") is None
    assert table.resolve(None, None, "G74W") is None
    assert table.resolve(None, "AeroTech", None) is None
    # a written but unknown id never falls back to maker and designation
    assert table.resolve("AeroTech-G74W-typo", "AeroTech", "G74W") is None


def test_maker_and_designation_matching_two_motors_is_ambiguous():
    # In the real table every key is maker-designation[-vN], so this cannot
    # happen there; a hand-made table shows the rule.
    t = MotorTable({
        "A-X1": {"manufacturer": "A", "designation": "X1"},
        "A-X1b": {"manufacturer": "A", "designation": "X1"},
    })
    assert t.resolve(None, "A", "X1") is None
    t1 = MotorTable({
        "A-X1-v1": {"manufacturer": "A", "designation": "X1"},
        "A-X1": {"manufacturer": "A", "designation": "X1"},
    })
    assert t1.resolve(None, "A", "X1") == "A-X1"        # no suffix counts as the lowest version
    t2 = MotorTable({k: v for k, v in {
        "A-X1-v2": {"manufacturer": "A", "designation": "X1"},
        "A-X1-v10": {"manufacturer": "A", "designation": "X1"},
    }.items()})
    assert t2.resolve(None, "A", "X1") == "A-X1-v2"     # versions compare as numbers, not text
    assert t2.resolve("a-x1") == "A-X1-v2"


@pytest.mark.parametrize("impulse, letter", [
    (0.3, "A"), (2.5, "A"), (2.51, "B"), (5.0, "B"), (5.01, "C"), (160, "G"), (161, "H"),
    (40960, "O"), (40961, "P"), (0, None), (-5, None), (None, None), (float("nan"), None),
    (float("inf"), None), ("100", None), (True, None), (1e300, None),
])
def test_impulse_class(impulse, letter):
    assert impulse_class(impulse) == letter


@pytest.mark.parametrize("des, letter", [
    ("H195NT", "H"), ("HP-H195NT", "H"), ("1109J440-P", "J"), ("1/2A3", "A"), ("m2000r", "M"),
    ("Kismet_v4", "K"), ("", None), ("123", None), (None, None), (5, None),
    # HyperTEK: tank size first, class letter after "CC" and the injector size
    ("440CC098J", "J"), ("1685CC098L-L200", "L"), ("440CC172J-I260", "I"), ("1685CCRGL", "L"),
    ("2730L1276-P", "L"),
    # Animal Motor Works: propellant, diameter, impulse in Ns
    ("BB-38-390", "I"), ("BB-98-11000", "N"), ("WT-54-1400", "K"), ("bb-54-1750", "K"),
    # Cesaroni impulse-first names, Quest Micro Maxx
    ("21062-O3400-IM", "O"), ("4263-L1350-CS", "L"), ("644-J94-MY", "J"),
    ("MICRO_MAXX", "A"), ("MICRO_MAXX_II", "A"),
])
def test_class_from_designation(des, letter):
    assert class_from_designation(des) == letter


def test_designation_letters_are_at_most_one_class_off(table):
    """With the Animal Motor Works, Cesaroni impulse-first and Micro Maxx names
    read right, every table motor's written letter is its measured class or
    one next to it (motors sold under a letter one off from their impulse)."""
    far = []
    for key in table._entries:
        e = table.get(key)
        a, b = impulse_class(e.get("total_impulse_ns")), class_from_designation(e["designation"])
        if a is None or b is None or abs(ord(a) - ord(b)) > 1:
            far.append((key, a, b))
    assert far == []


def test_no_real_class_b_motor_is_98_mm_wide(table):
    """The AMW 'BB-98-...' motors were once read as class B, so an invented
    98 mm class-B motor earned the diameter fact."""
    assert not table.class_has_diameter("B", 0.098)
    assert table.class_has_diameter("N", 0.098)


def test_entries_without_impulse_have_no_class(table):
    assert "ICLR-N1903" not in table and table.class_of("ICLR-N1903") is None
    assert table.class_of("AeroTech-M2000R-v2") == "M"
    assert all(d > 0 for d in table.diameters_for_class("H"))
    assert table.class_has_diameter("H", 0.029) and table.class_has_diameter("H", 0.0294)
    assert not table.class_has_diameter("H", 0.0296) and not table.class_has_diameter("H", 0.098)
    assert not table.class_has_diameter("H", float("nan")) and not table.class_has_diameter("H", "0.029")


# ---------------------------------------------------------------------------
# which motors fly

def test_flown_config_is_the_default_one(gold):
    rocket = gold["openrocket"]["children"][0]["rocket"]
    rocket["children"].insert(0, {"motorconfiguration": {"attrs": {"configid": "early"}}})
    assert flown_config_id(gold) == "early"           # the gold config here is not marked default
    rocket["children"].append({"motorconfiguration": {"attrs": {"configid": "late", "default": "true"}}})
    assert flown_config_id(gold) == "late"
    rocket["children"][-1]["motorconfiguration"]["attrs"]["default"] = True
    assert flown_config_id(gold) == "late"
    assert flown_motors(gold) == []                   # no motor uses 'late'


@pytest.mark.parametrize("tree", [None, 3, {}, {"openrocket": {}}, {"openrocket": {"children": [
    {"rocket": {"children": [{"motorconfiguration": {"attrs": {"configid": 7}}},
                             {"motorconfiguration": {"attrs": {"configid": "  "}}},
                             {"motorconfiguration": "x"}]}}]}}])
def test_no_usable_configuration(tree):
    assert flown_config_id(tree) is None
    assert flown_motors(tree) == []


def test_motors_of_other_configurations_do_not_fly(gold, table):
    other = make_motor("Invented-Z1", configid="spare")
    with_motors(gold, [nodes(gold, "motor")[0], other])
    assert len(flown_motors(gold)) == 1
    assert check_motors(gold, table).passed


# ---------------------------------------------------------------------------
# real data

def test_every_gold_answer_passes(gold_designs, table):
    for rid, d in gold_designs:
        res = check_motors(d, table)
        assert res.passed, (rid, res.reasons)
        assert res.credit == 1.0
        assert all(m["key"] for m in res.info["motors"])


def test_model_answers(model_rows, table):
    """Calibration on the model's 48 saved answers: 11 fly real motors; the
    unknown motors spread over several credits instead of all tying."""
    passed, credits = 0, []
    for r in model_rows:
        d = design_of(r["content"]) if not r.get("truncated") else None
        if not isinstance(d, dict) or "openrocket" not in d:
            continue
        res = check_motors(d, table)
        if res.passed:
            passed += 1
        elif res.info["motors"]:
            credits.append(round(res.credit, 3))
            assert all("is not a real motor" in x or "more unknown" in x for x in res.reasons)
    assert passed == 11
    assert len(credits) == 30
    assert len(set(credits)) >= 3


def test_near_miss_is_named_but_not_accepted(gold, table):
    set_fields(nodes(gold, "motor")[0], motor_id="AeroTech-H195NT", manufacturer="AeroTech",
               designation="H195NT", diameter=0.029)
    res = check_motors(gold, table)
    assert not res.passed
    assert "'AeroTech-H195NT' is not a real motor" in res.reasons[0]
    assert "did you mean 'AeroTech-HP-H195NT'?" in res.reasons[0]
    m = res.info["motors"][0]
    assert m["written_id"] == "AeroTech-H195NT" and m["key"] is None
    assert m["maker_real"] and m["designation_real"] and m["class_diameter_real"]
    assert res.credit == 1.0


@pytest.mark.parametrize("fields, credit", [
    (dict(motor_id="Nobody-Q9", manufacturer="Nobody", designation="Q9", diameter=0.5), 0.0),
    (dict(motor_id="AeroTech-Q9", manufacturer="AeroTech", designation="Q9", diameter=0.5), 1 / 3),
    (dict(motor_id="AeroTech-H999Z", manufacturer="AeroTech", designation="H999Z", diameter=0.029), 2 / 3),
    (dict(motor_id="AeroTech-G80-v1", manufacturer="AeroTech", designation="G80", diameter=0.029), 1.0),
    # maker and designation read from the id when they are not written
    (dict(motor_id="AeroTech-H999Z", manufacturer=..., designation=..., diameter=0.029), 2 / 3),
    (dict(motor_id="AeroTech-H999Z", manufacturer=..., designation=..., diameter=...), 1 / 3),
    (dict(motor_id="AeroTech-H999Z", manufacturer=..., designation=..., diameter=float("nan")), 1 / 3),
    (dict(motor_id="AeroTech-H999Z", manufacturer=..., designation=..., diameter="0.029"), 2 / 3),
])
def test_credit_is_the_share_of_true_facts(gold, table, fields, credit):
    set_fields(nodes(gold, "motor")[0], **fields)
    res = check_motors(gold, table)
    assert not res.passed and res.stage == "motor"
    assert res.credit == pytest.approx(credit)


def test_no_motor_id_but_unique_maker_and_designation_passes(gold, table):
    set_fields(nodes(gold, "motor")[0], motor_id=..., manufacturer="AeroTech", designation="G74W")
    res = check_motors(gold, table)
    assert res.passed and res.info["motors"][0]["key"] == "AeroTech-G74W"


def test_no_motor_id_and_unknown_designation_fails(gold, table):
    set_fields(nodes(gold, "motor")[0], motor_id=None, manufacturer="AeroTech", designation="G7400W")
    res = check_motors(gold, table)
    assert not res.passed and "no motor_id" in res.reasons[0]


def test_worst_motor_counts(gold, table):
    good = make_motor("AeroTech-G74W", "AeroTech", "G74W", 0.029)
    close = make_motor("AeroTech-H999Z", "AeroTech", "H999Z", 0.029)
    bad = make_motor("Nobody-Q9", "Nobody", "Q9", 0.5)
    with_motors(gold, [good, close])
    assert check_motors(gold, table).credit == pytest.approx(2 / 3)
    with_motors(gold, [good, close, bad])
    res = check_motors(gold, table)
    assert res.credit == 0.0 and len(res.reasons) == 2
    assert [m["key"] for m in res.info["motors"]] == ["AeroTech-G74W", None, None]


def test_no_flown_motor_fails_with_zero(gold, table):
    for mm in nodes(gold, "motormount"):
        mm["motormount"]["children"] = [c for c in mm["motormount"]["children"] if "motor" not in c]
    res = check_motors(gold, table)
    assert not res.passed and res.credit == 0 and "no motor" in res.reasons[0]


# ---------------------------------------------------------------------------
# hostile input

STRANGE = [None, 7, -1.5, True, [1, 2], {"a": "b"}, float("inf"),
           "x" * 1_000_000, "\u0000퟿", "HP-" * 1000]


@pytest.mark.parametrize("value", STRANGE, ids=[f"strange{i}" for i in range(len(STRANGE))])
def test_strange_field_values_do_not_crash(gold, table, value):
    set_fields(nodes(gold, "motor")[0], motor_id=value, manufacturer=value, designation=value, diameter=value)
    res = check_motors(gold, table)
    assert not res.passed and 0 <= res.credit <= 1
    assert all(len(r) < 1000 for r in res.reasons)


def test_a_million_motors_are_fast(gold, table):
    motors = [make_motor(f"Fake-H{i}W", "AeroTech", f"H{i}W", 0.029) for i in range(1_000_000)]
    with_motors(gold, motors)
    t0 = time.perf_counter()
    res = check_motors(gold, table)
    assert time.perf_counter() - t0 < 20   # about 6 s here; parse.py caps real trees far below this
    assert not res.passed and res.info["motor_count"] == 1_000_000
    assert len(res.info["motors"]) <= 50 and len(res.reasons) <= 11


def test_a_million_copies_of_one_motor_are_fast(gold, table):
    with_motors(gold, [make_motor("AeroTech-G74W", "AeroTech", "G74W", 0.029) for _ in range(1_000_000)])
    t0 = time.perf_counter()
    assert check_motors(gold, table).passed
    assert time.perf_counter() - t0 < 10


def test_broken_motor_nodes_are_skipped(gold, table):
    mm = nodes(gold, "motormount")[0]
    mm["motormount"]["children"].extend([None, 3, "motor", {"motor": None}, {"motor": {"children": "x"}}])
    res = check_motors(gold, table)
    assert res.stage == "motor" and 0 <= res.credit <= 1


def test_every_real_motor_satisfies_the_class_fact_for_itself(table):
    """A real motor's own designation and diameter must always satisfy fact 3,
    so an invented motor of a real size never loses that third of the credit."""
    bad = []
    for key in table._entries:
        e = table.get(key)
        letter = class_from_designation(e["designation"])
        if letter is None or not isinstance(e.get("diameter_m"), (int, float)):
            continue
        if not table.class_has_diameter(letter, e["diameter_m"]):
            bad.append((key, letter, e["diameter_m"]))
    assert bad == []


def test_last_default_configuration_flies(gold, table):
    rocket = gold["openrocket"]["children"][0]["rocket"]
    rocket["children"].insert(0, {"motorconfiguration": {"attrs": {"configid": "first", "default": "true"}}})
    rocket["children"].append({"motorconfiguration": {"attrs": {"configid": "second", "default": "true"}}})
    assert flown_config_id(gold) == "second"


def test_motor_field_written_twice_uses_the_last_copy(gold, table):
    m = nodes(gold, "motor")[0]
    m["motor"]["children"].append({"motor_id": {"value": "Invented-Z1"}})
    res = check_motors(gold, table)
    assert not res.passed and "Invented-Z1" in " ".join(res.reasons)
