"""Tests for ladder.py: the bands and the credit formulas (DESIGN.md section 2)."""
from __future__ import annotations

import math

import pytest

from rocket_reward import ladder

ODD_VALUES = [None, "3", [], {}, True, False, float("nan"), float("inf"), -float("inf"),
              -1.0, 0, 0.0, 1e-300, 1e300]
# Integers too large for a float. ladder.is_number crashes on them (reported as a
# foundation bug); parse.py rejects such numbers so they never reach the ladder.
HUGE_INTS = [10**400, -10**400]
CREDITS = [-1e300, -5, -1, -0.0, 0, 1e-12, 0.25, 0.5, 0.999999, 1, 1.5, 7, 1e300,
           float("nan"), float("inf"), -float("inf"), None, "0.5", True]
DEFECTS = [-10**12, -3, -1, 0, 1, 2, 5, 9, 10, 11, 100, 10**12, 1.5, True]


def test_stage_order_matches_design():
    assert ladder.STAGE_KEYS == ("format", "parts", "motor", "limits", "build", "flight", "targets")
    assert ladder.stage("targets").top == pytest.approx(1.0)
    assert ladder.stage("format").floor == 0.0


def test_bands_never_overlap():
    for lower, upper in zip(ladder.STAGES, ladder.STAGES[1:]):
        assert lower.width > 0
        assert lower.top < upper.floor, f"{lower.key} reaches {lower.top}, {upper.key} starts at {upper.floor}"


def test_best_of_a_stage_is_below_worst_of_the_next():
    for lower, upper in zip(ladder.STAGE_KEYS, ladder.STAGE_KEYS[1:]):
        assert ladder.stage_score(lower, 1.0, 0) < ladder.stage_score(upper, 0.0, 100)


@pytest.mark.parametrize("key", ladder.STAGE_KEYS)
def test_stage_score_stays_in_band(key):
    s = ladder.stage(key)
    for credit in CREDITS:
        for defects in DEFECTS:
            got = ladder.stage_score(key, credit, defects)
            assert isinstance(got, float) and math.isfinite(got)
            assert s.floor - 1e-9 <= got <= s.top + 1e-9, (key, credit, defects, got)


def test_stage_score_rises_with_credit_and_falls_with_defects():
    for key in ladder.STAGE_KEYS:
        prev = -1.0
        for c in [i / 20 for i in range(21)]:
            got = ladder.stage_score(key, c)
            assert got >= prev
            prev = got
        prev = 2.0
        for d in range(15):
            got = ladder.stage_score(key, 1.0, d)
            assert got <= prev
            prev = got


def test_defects_cost_at_most_half():
    s = ladder.stage("flight")
    assert ladder.stage_score("flight", 1.0, 1000) == pytest.approx(s.floor + s.width * 0.5)
    assert ladder.stage_score("flight", 1.0, 1) == pytest.approx(s.floor + s.width * 0.95)


def test_unknown_stage_is_an_error():
    with pytest.raises(KeyError):
        ladder.stage_score("nope", 0.5)


def test_clamp01_and_is_number():
    assert ladder.clamp01(2) == 1.0 and ladder.clamp01(-2) == 0.0 and ladder.clamp01(0.3) == 0.3
    for odd in [None, "1", float("nan"), float("inf"), True, [], {}]:
        assert ladder.clamp01(odd) == 0.0
        assert not ladder.is_number(odd)
    assert ladder.is_number(3) and ladder.is_number(-2.5)


def test_violation_sizes_follow_the_formula():
    assert ladder.over_limit(10, 10) == 0.0
    assert ladder.over_limit(20, 10) == pytest.approx(1.0)
    assert ladder.over_limit(80, 10) == pytest.approx(3.0)
    assert ladder.over_limit(10**6, 10) == 3.0
    assert ladder.under_limit(5, 10) == pytest.approx(1.0)
    assert ladder.under_limit(0, 10) == 3.0
    assert ladder.under_limit(-5, 10) == 3.0


@pytest.mark.parametrize("fn", [ladder.over_limit, ladder.under_limit])
def test_violations_never_raise_and_stay_in_range(fn):
    for value in ODD_VALUES:
        for limit in [-1.0, 0.0, 1e-9, 1.0, 1e9]:
            v = fn(value, limit)
            assert 0.0 <= v <= ladder.MAX_VIOLATION, (value, limit, v)


def test_over_limit_is_monotone():
    values = [0.0, 0.5, 1, 1.5, 2, 3, 5, 8, 16, 1e6, 1e300]
    sizes = [ladder.over_limit(v, 2.0) for v in values]
    assert sizes == sorted(sizes)


def test_under_limit_is_monotone():
    values = [1e300, 1e6, 8, 2, 1.5, 1, 0.5, 0.25, 0.1, 1e-9, 0.0, -1.0]
    sizes = [ladder.under_limit(v, 2.0) for v in values]
    assert sizes == sorted(sizes)


def test_credit_from_violations():
    assert ladder.credit_from_violations([]) == 1.0
    assert ladder.credit_from_violations([1.0]) == pytest.approx(0.5)
    assert ladder.credit_from_violations([1.0, 2.0]) == pytest.approx(0.25)
    # each term is clamped to 0..3; odd terms count as 3
    assert ladder.credit_from_violations([100.0]) == pytest.approx(0.25)
    assert ladder.credit_from_violations([-5.0]) == 1.0
    for odd in [None, "x", float("nan"), float("inf"), True]:
        assert ladder.credit_from_violations([odd]) == pytest.approx(0.25)


def test_credit_from_violations_is_monotone():
    prev = 2.0
    for v in [0, 0.1, 0.5, 1, 2, 3, 4, 100]:
        c = ladder.credit_from_violations([v, 0.5])
        assert 0 < c <= 1 and c <= prev
        prev = c


def test_closeness_full_credit_inside_tolerance():
    assert ladder.closeness(100, 100) == 1.0
    assert ladder.closeness(104, 100) == 1.0               # within the default 5%
    assert ladder.closeness(50, 100, "max") == 1.0
    assert ladder.closeness(200, 100, "min") == 1.0
    assert ladder.closeness(101, 100, "max") < 1.0         # no slack for max by default


def test_closeness_closer_is_never_worse():
    for kind in ("about", "max", "min"):
        for side in (1, -1):
            prev = 2.0
            for k in range(0, 40):
                value = 100 * math.exp(side * k * 0.1)
                c = ladder.closeness(value, 100, kind)
                assert 0 < c <= 1 and c <= prev + 1e-12, (kind, side, k, c)
                prev = c


def test_closeness_never_reaches_zero_for_a_positive_value():
    assert ladder.closeness(1e300, 1.0) > 0
    assert ladder.closeness(1e-300, 1.0) > 0
    assert ladder.closeness(200, 100) > ladder.closeness(400, 100)


def test_closeness_odd_input():
    for odd in ODD_VALUES:
        c = ladder.closeness(odd, 100)
        assert 0.0 <= c <= 1.0
        c = ladder.closeness(100, odd)
        assert 0.0 <= c <= 1.0
    assert ladder.closeness(100, 100, "about", tol=-3) <= 1.0
    with pytest.raises(ValueError):
        ladder.closeness(100, 100, "sideways")


@pytest.mark.parametrize("fn", [ladder.is_number, ladder.clamp01,
                                lambda x: ladder.over_limit(x, 1.0),
                                lambda x: ladder.under_limit(x, 1.0),
                                lambda x: ladder.closeness(x, 1.0),
                                lambda x: ladder.credit_from_violations([x]),
                                lambda x: ladder.stage_score("parts", x)])
def test_huge_integers_do_not_raise(fn):
    fn(HUGE_INTS[0])


@pytest.mark.parametrize("defects", [float("nan"), float("inf")])
def test_stage_score_with_non_finite_defect_count(defects):
    got = ladder.stage_score("parts", 0.5, defects)
    assert 0.10 <= got <= 0.18
