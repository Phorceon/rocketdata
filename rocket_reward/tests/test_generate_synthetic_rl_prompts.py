"""Unit tests (no Java needed) for rocket_reward.tools.generate_synthetic_rl_prompts."""
from __future__ import annotations

import random
import re

import pytest

from rocket_reward.records import Requirements
from rocket_reward.tools import generate_synthetic_rl_prompts as G


SAMPLE_MOTOR = {
    "motor_id": "AeroTech-G74W-v1",
    "designation": "G74W",
    "manufacturer": "AeroTech",
    "motor_type": "reload",
    "impulse_ns": 117.0,
    "diameter_m": 0.029,
    "length_m": 0.124,
    "launch_mass_kg": 0.125,
    "burnout_mass_kg": 0.062,
    "average_thrust_n": 74.0,
    "max_thrust_n": 110.0,
}

SAMPLE_METRICS = {
    "apogee_m": 512.4,
    "landing_ms": 5.2,
    "flight_time_s": 108.6,
    "time_to_apogee_s": 11.4,
    "ignition_time_s": 0.6,
    "max_velocity_ms": 148.0,
    "max_accel_ms2": 135.0,
    "mass_kg": 0.42,
}


@pytest.mark.parametrize("total", [0, 1, 5, 10, 15, 50, 100, 2000])
def test_class_quotas_always_sums_to_total(total):
    avail = list(G.ALL_CLASSES)
    q = G.class_quotas(total, avail)
    assert sum(q.values()) == total
    assert all(v >= 0 for v in q.values())
    if total >= len(avail):
        assert all(v >= 1 for v in q.values())


def test_split_motors_ood_has_zero_overlap_for_large_classes():
    by_class = {
        "G": [{"designation": f"G{i}"} for i in range(20)],
        "O": [{"designation": f"O{i}"} for i in range(10)],
    }
    tr, ev = G.split_motors_ood(by_class, holdout_frac=0.10, seed=42)
    for c in ("G", "O"):
        tr_d = {m["designation"] for m in tr[c]}
        ev_d = {m["designation"] for m in ev[c]}
        assert tr_d and ev_d
        assert tr_d.isdisjoint(ev_d)
        assert len(tr_d) + len(ev_d) == len(by_class[c])


def test_article_matches_english_pronunciation():
    assert G._article("A6") == "an"
    assert G._article("E20W") == "an"
    assert G._article("F25W") == "an"
    assert G._article("H128W") == "an"
    assert G._article("M2000R") == "an"
    assert G._article("848J520-16A") == "an"
    assert G._article("18A") == "an"
    assert G._article("1109J440-P") == "an"
    assert G._article("11077N2600-P") == "an"
    assert G._article("180F40") == "a"
    assert G._article("G74W") == "a"
    assert G._article("B6") == "a"
    assert G._article("C6") == "a"


def test_casual_build_grammar_never_uses_targeting_and_lands():
    for seed in range(100):
        text, _ = G.build_prompt_from_metrics(
            random.Random(seed), f"G-{seed}:casual", "casual", "G", SAMPLE_MOTOR, 2.0, SAMPLE_METRICS, 0.054
        )
        assert "targeting roughly" not in text or " and lands " not in text
        assert "targeting roughly" not in text or " and drifts " not in text


@pytest.mark.parametrize("style", ["original", "casual", "engineering"])
def test_build_prompt_from_metrics_text_matches_requirements(style):
    saw_feet = False
    saw_grams = False
    for seed in range(60):
        rng = random.Random(seed)
        text, req = G.build_prompt_from_metrics(
            rng, f"T-{seed}:{style}", style, "G", SAMPLE_MOTOR, 2.5, SAMPLE_METRICS, 0.054
        )
        parsed = Requirements.from_dict(req)

        # Unstated tolerance styles must always use 0.05 (no hidden tolerance)
        if style in ("original", "casual"):
            assert parsed.apogee_m.tol == 0.05
        else:
            pct = int(round(parsed.apogee_m.tol * 100))
            assert f"(+/- {pct}%)" in text

        # Feet conversion in casual must match req.apogee_m.value exactly
        ft_match = re.search(r"([\d,]+)\s+ft\b", text)
        if ft_match:
            saw_feet = True
            ft_val = int(ft_match.group(1).replace(",", ""))
            assert parsed.apogee_m.value == pytest.approx(ft_val / G.M_TO_FT, abs=1e-3)

        # Gram conversion must match req.mass_kg.value exactly
        g_match = re.search(r"([\d,]+)\s+(?:grams|g)\b", text)
        if g_match:
            saw_grams = True
            g_val = int(g_match.group(1).replace(",", ""))
            assert parsed.mass_kg is not None
            assert parsed.mass_kg.value == pytest.approx(g_val / 1000.0, abs=1e-4)

        # Named motor / class must appear in text
        if parsed.motors:
            assert parsed.motors[0] in text
        if parsed.motor_class:
            assert f"class {parsed.motor_class} motor" in text

        # Timed caps must respect ignition_time_s offset (and exceed measured)
        if parsed.flight_time_s:
            assert parsed.flight_time_s.value >= SAMPLE_METRICS["flight_time_s"] - SAMPLE_METRICS["ignition_time_s"]
        if parsed.time_to_apogee_s:
            assert parsed.time_to_apogee_s.value >= SAMPLE_METRICS["time_to_apogee_s"] - SAMPLE_METRICS["ignition_time_s"]

    assert saw_grams
    if style == "casual":
        assert saw_feet
