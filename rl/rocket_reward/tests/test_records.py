"""Tests for records.py: Target, Requirements, StageCheck, Result."""
from __future__ import annotations

import json

import pytest

from rocket_reward.records import TARGET_FIELDS, Requirements, Result, StageCheck, Target

GOOD = {
    "id": "v5-0012",
    "apogee_m": {"value": 3320, "kind": "about", "tol": 0.05},
    "landing_ms": {"value": 5.7, "kind": "max"},
    "flight_time_s": {"value": 190.2, "kind": "max"},
    "wind_ms": 0.1,
    "motors": ["M2000R"],
}


def test_design_example_round_trips():
    req = Requirements.from_dict(GOOD)
    assert req.apogee_m == Target(3320, "about", 0.05)
    assert req.landing_ms.kind == "max" and req.wind_ms == 0.1 and req.motors == ("M2000R",)
    assert Requirements.from_dict(req.to_dict()) == req
    json.dumps(req.to_dict())  # plain JSON


def test_minimal_record_uses_defaults():
    req = Requirements.from_dict({"id": "a", "apogee_m": {"value": 100, "kind": "about"}})
    assert req.wind_ms == 2.0 and req.motors == () and req.motor_class is None
    assert set(req.targets()) == {"apogee_m"}


def test_every_target_field_is_accepted():
    d = {"id": "all", **{name: {"value": 1.5, "kind": "max"} for name in TARGET_FIELDS},
         "motor_class": "H", "motors": ["H128W", "H100"], "wind_ms": 0}
    req = Requirements.from_dict(d)
    assert set(req.targets()) == set(TARGET_FIELDS)
    assert req.motor_class == "H" and req.wind_ms == 0


def test_null_optional_fields_mean_not_graded():
    req = Requirements.from_dict({**GOOD, "landing_ms": None, "motors": None, "wind_ms": None})
    assert req.landing_ms is None and req.motors == () and req.wind_ms == 2.0


BAD = [
    ("not a dict", ["id", "apogee_m"], "must be a dict"),
    ("unknown key", {**GOOD, "apogee": {"value": 1, "kind": "about"}}, "unknown keys"),
    ("typo in target", {**GOOD, "landing_m": {"value": 5, "kind": "max"}}, "unknown keys"),
    ("no apogee", {k: v for k, v in GOOD.items() if k != "apogee_m"}, "'apogee_m' is required"),
    ("null apogee", {**GOOD, "apogee_m": None}, "'apogee_m' is required"),
    ("no id", {k: v for k, v in GOOD.items() if k != "id"}, "non-empty text 'id'"),
    ("empty id", {**GOOD, "id": ""}, "non-empty text 'id'"),
    ("number id", {**GOOD, "id": 12}, "non-empty text 'id'"),
    ("target not a dict", {**GOOD, "apogee_m": 3320}, "must look like"),
    ("target extra key", {**GOOD, "apogee_m": {"value": 1, "kind": "about", "unit": "ft"}}, "unknown keys"),
    ("target no kind", {**GOOD, "apogee_m": {"value": 1}}, "needs both"),
    ("target no value", {**GOOD, "apogee_m": {"kind": "about"}}, "needs both"),
    ("bad kind", {**GOOD, "apogee_m": {"value": 1, "kind": "around"}}, "kind must be one of"),
    ("zero value", {**GOOD, "apogee_m": {"value": 0, "kind": "about"}}, "positive number"),
    ("negative value", {**GOOD, "apogee_m": {"value": -5, "kind": "about"}}, "positive number"),
    ("nan value", {**GOOD, "apogee_m": {"value": float("nan"), "kind": "about"}}, "positive number"),
    ("inf value", {**GOOD, "apogee_m": {"value": float("inf"), "kind": "about"}}, "positive number"),
    ("text value", {**GOOD, "apogee_m": {"value": "3320", "kind": "about"}}, "positive number"),
    ("bool value", {**GOOD, "apogee_m": {"value": True, "kind": "about"}}, "positive number"),
    ("tol too big", {**GOOD, "apogee_m": {"value": 1, "kind": "about", "tol": 1.0}}, "tolerance"),
    ("tol negative", {**GOOD, "apogee_m": {"value": 1, "kind": "about", "tol": -0.1}}, "tolerance"),
    ("tol text", {**GOOD, "apogee_m": {"value": 1, "kind": "about", "tol": "5%"}}, "tolerance"),
    ("negative wind", {**GOOD, "wind_ms": -1}, "'wind_ms'"),
    ("nan wind", {**GOOD, "wind_ms": float("nan")}, "'wind_ms'"),
    ("text wind", {**GOOD, "wind_ms": "2"}, "'wind_ms'"),
    ("motors as text", {**GOOD, "motors": "M2000R"}, "'motors' must be a list"),
    ("motors as dict", {**GOOD, "motors": {"a": 1}}, "'motors' must be a list"),
    ("motors with blank", {**GOOD, "motors": ["M2000R", ""]}, "list of designations"),
    ("motors with number", {**GOOD, "motors": [5]}, "list of designations"),
    ("class lower case", {**GOOD, "motor_class": "h"}, "one capital letter"),
    ("class two letters", {**GOOD, "motor_class": "HI"}, "one capital letter"),
    ("class number", {**GOOD, "motor_class": 7}, "one capital letter"),
]


@pytest.mark.parametrize("label,record,message", BAD, ids=[b[0] for b in BAD])
def test_bad_records_are_rejected_clearly(label, record, message):
    with pytest.raises(ValueError) as info:
        Requirements.from_dict(record)
    assert message in str(info.value)


def test_target_names_the_field_in_errors():
    with pytest.raises(ValueError, match="landing_ms"):
        Requirements.from_dict({**GOOD, "landing_ms": {"value": -1, "kind": "max"}})


def test_records_are_frozen():
    req = Requirements.from_dict(GOOD)
    with pytest.raises(Exception):
        req.id = "other"  # type: ignore[misc]


def test_stagecheck_and_result_defaults_are_independent():
    a, b = StageCheck("parts", False), StageCheck("parts", False)
    a.reasons.append("x")
    assert b.reasons == [] and a.credit == 0.0
    r = Result(score=0.5, stage="parts", stages_passed=1, credit=0.3)
    d = r.to_dict()
    assert d["score"] == 0.5 and d["flags"] == {} and d["reasons"] == []
    json.dumps(d)
