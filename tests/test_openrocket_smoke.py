"""Smoke test: simulate one .ork headless and check the numbers are sane.

Skipped when the OpenRocket JAR or JDK 17 is not available.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.or_headless import DEFAULT_JAR, DEFAULT_JAVA_HOME, simulate

ORK = REPO_ROOT / "meta" / "ork" / "ESTES Alpha 3.ork"


@pytest.mark.skipif(
    not DEFAULT_JAR.exists() or not (DEFAULT_JAVA_HOME / "bin" / "java").exists(),
    reason="OpenRocket JAR or JDK 17 not available",
)
def test_simulate_alpha3():
    result = simulate(str(ORK))

    assert 10 < result["apogee_m"] < 1000
    assert 5 < result["max_velocity_ms"] < 300
    assert 0 < result["time_to_apogee_s"] < result["flight_time_s"]
    assert 3 < result["flight_time_s"] < 300
    assert 0 <= result["ground_hit_ms"] < result["max_velocity_ms"]
    assert result["max_accel_ms2"] > 0
    assert result["runtime_ms"] > 0


if __name__ == "__main__":
    result = simulate(str(ORK))
    for k, v in result.items():
        print(f"{k:20} {v}")
