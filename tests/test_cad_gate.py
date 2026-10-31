"""Tests for the CAD gate (src/rocketai/cad.py).

    .venv/bin/python -m pytest tests/test_cad_gate.py -q

A gate is only worth something if it FAILS broken rockets, so most tests here break a
good rocket on purpose and check that the gate catches it.
"""
import copy
import json
import math
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from rocketai.layout import layout, nose_radius  # noqa: E402

cq = pytest.importorskip("cadquery")
from rocketai import cad  # noqa: E402


def design(row_id, path="new_results/sft_v2.jsonl"):
    for line in open(REPO / path, encoding="utf-8"):
        row = json.loads(line)
        if row["id"] == row_id:
            return cad.design_from_row(row)
    raise KeyError(row_id)


U020 = design("U-020")  # Estes BT-55 style: ogive nose, one tube, 3 trapezoid fins


# ---------------------------------------------------------------- layout (no CAD)

@pytest.mark.parametrize("shape,param", [("conical", 0), ("ogive", 1.0), ("ogive", 0.5),
                                         ("ellipsoid", 0), ("power", 0.5), ("parabolic", 1.0),
                                         ("haack", 0.0), ("haack", 1 / 3)])
def test_nose_profile_goes_from_tip_to_base(shape, param):
    assert nose_radius(shape, param, 100.0, 20.0, 0.0) == pytest.approx(0.0, abs=1e-9)
    assert nose_radius(shape, param, 100.0, 20.0, 100.0) == pytest.approx(20.0, rel=1e-6)


def test_tangent_ogive_matches_the_textbook_formula():
    L, R = 101.6, 16.83
    rho = (R * R + L * L) / (2 * R)
    for x in (10.0, 50.0, 90.0):
        textbook = math.sqrt(rho ** 2 - (L - x) ** 2) + R - rho
        assert nose_radius("ogive", 1.0, L, R, x) == pytest.approx(textbook, rel=1e-9)


def test_u020_layout_stacks_parts_nose_to_tail():
    lay = layout(U020)
    nose, tube, fins = lay.parts
    assert (nose.x0, nose.x1) == pytest.approx((0.0, 0.1016))
    assert (tube.x0, tube.x1) == pytest.approx((0.1016, 0.5588))
    assert fins.x1 == pytest.approx(tube.x1)  # fins flush with the back of the tube
    assert fins.fin["count"] == 3


# ---------------------------------------------------------------- the real gate

def test_good_rocket_passes():
    r = cad.cad_gate(U020)
    assert r["status"] == "pass", r["failures"]
    assert r["reward"] is None
    assert 0 < r["cg_m"] < 0.5588  # CG somewhere inside the rocket


def test_fin_is_as_thick_as_the_design_says():
    built = cad.build(layout(U020))
    fin = next(x for x in built.solids if x.kind == "fin")
    f = fin.part.fin
    expected = (f["root_chord_m"] + f["tip_chord_m"]) / 2 * f["span_m"] * f["thickness_m"] * 1e9
    assert fin.shape.Volume() == pytest.approx(expected, rel=1e-3)


def test_tube_is_the_right_size():
    built = cad.build(layout(U020))
    tube = next(x for x in built.solids if x.kind == "bodytube")
    bb = tube.shape.BoundingBox()
    assert bb.xlen == pytest.approx(457.2, abs=0.01)
    assert bb.ylen == pytest.approx(33.66, abs=0.01)


def test_floating_fins_fail():
    built = cad.build(layout(U020))
    for x in built.solids:
        if x.kind == "fin":  # push each fin 5 mm straight out from the axis
            a = math.radians(x.angle)
            x.shape = x.shape.translate(cq.Vector(0, 5 * math.cos(a), 5 * math.sin(a)))
    failures = cad.check(built)
    assert any("not attached" in f for f in failures), failures


def test_parts_pushed_into_each_other_fail():
    built = cad.build(layout(U020))
    tube = next(x for x in built.solids if x.kind == "bodytube")
    tube.shape = tube.shape.translate(cq.Vector(-10, 0, 0))  # tube slides 10 mm into the nose
    failures = cad.check(built)
    assert any("overlap" in f for f in failures), failures


def test_motor_tube_too_big_for_body_tube_fails():
    d = copy.deepcopy(U020)
    inner = d["components"][0]["contains"][1]["contains"][0]
    assert inner["type"] == "innertube"
    inner["outer_d_m"] = 0.05  # 50 mm motor tube in a 33 mm body tube
    r = cad.cad_gate(d)
    assert r["status"] == "fail" and r["reward"] == cad.FAIL_REWARD
    assert any("does not fit" in f for f in r["failures"])


def test_negative_fin_size_fails():
    d = copy.deepcopy(U020)
    fins = next(c for c in d["components"][0]["contains"][1]["contains"] if c["type"] == "trapezoidfin")
    fins["span_m"] = -0.05
    r = cad.cad_gate(d)
    assert r["status"] == "fail" and r["reward"] == cad.FAIL_REWARD


@pytest.mark.parametrize("bad", ["not json at all", "[]", '{"components": []}',
                                 '{"components": [{"type": "bodytube"}]}'])
def test_malformed_design_fails(bad):
    r = cad.cad_gate(bad)
    assert r["status"] == "fail" and r["reward"] == cad.FAIL_REWARD


def test_zero_wall_tube_fails_with_a_clear_reason():
    d = copy.deepcopy(U020)
    d["components"][0]["contains"][1]["wall_thickness_m"] = 0.0
    r = cad.cad_gate(d)
    assert r["status"] == "fail"
    assert any("needs a wall" in f for f in r["failures"])


def test_conical_nose_is_a_valid_solid():
    d = copy.deepcopy(U020)
    d["components"][0]["contains"][0]["shape"] = "conical"
    built = cad.build(layout(d))
    nose = next(x for x in built.solids if x.kind == "nosecone")
    assert nose.shape.isValid()
    r, length = 16.83, 101.6
    assert nose.shape.Volume() == pytest.approx(math.pi * r * r * length / 3, rel=1e-3)


def test_free_form_fins_are_unsupported_not_passed():
    r = cad.cad_gate(design("V1-032"))  # Parth_L1, free-form fins with no outline points
    assert r["status"] == "unsupported"
    assert r["reward"] is None
    assert any("free-form" in u for u in r["unsupported"])


def test_export_writes_files(tmp_path):
    step, glb = cad.export(U020, tmp_path)
    assert Path(step).stat().st_size > 1000
    assert Path(glb).stat().st_size > 1000
