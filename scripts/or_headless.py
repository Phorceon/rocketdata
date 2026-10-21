"""Headless OpenRocket simulation driver.

Runs OpenRocket simulations from Python with no GUI, using orhelper (a thin
JPype wrapper around OpenRocket's Java API).

Requires a JDK 17 and the OpenRocket 24.12 JAR. Set OPENROCKET_JAVA_HOME and
OPENROCKET_JAR to override the defaults. See scripts/fetch_openrocket.sh for the
JAR and the README notes for the JDK.

Example:
    from scripts.or_headless import simulate
    result = simulate("ork/ESTES Alpha 3.ork")
"""

from __future__ import annotations

import os
import time
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import orhelper

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_JAR = REPO_ROOT / "lib" / "OpenRocket.jar"
DEFAULT_JAVA_HOME = Path.home() / ".jdks" / "jdk-17.0.20.1+1" / "Contents" / "Home"

JVM_ARGS = ["-Djava.awt.headless=true"]


def _java_home() -> Path:
    return Path(os.environ.get("OPENROCKET_JAVA_HOME", DEFAULT_JAVA_HOME))


def _jar() -> Path:
    return Path(os.environ.get("OPENROCKET_JAR", DEFAULT_JAR))


def _libjvm() -> str:
    jvm = _java_home() / "lib" / "server" / "libjvm.dylib"
    if not jvm.exists():
        jvm = _java_home() / "lib" / "server" / "libjvm.so"
    return str(jvm)


_INSTANCE = None
_HELPER = None


def _helper(log_level: str = "ERROR"):
    """Return a process-wide Helper, starting the JVM once (JPype cannot restart it)."""
    global _INSTANCE, _HELPER
    if _HELPER is not None:
        return _HELPER
    if not _jar().exists():
        raise FileNotFoundError(
            f"OpenRocket JAR not found at {_jar()}. Run scripts/fetch_openrocket.sh."
        )
    _INSTANCE = orhelper.OpenRocketInstance(
        jar=str(_jar()), jvm=_libjvm(), jvm_args=JVM_ARGS, log_level=log_level
    )
    _INSTANCE.__enter__()
    _HELPER = orhelper.Helper(_INSTANCE)
    return _HELPER


@contextmanager
def _instance(log_level: str = "ERROR"):
    """Backwards-compatible context manager; JVM stays up for the whole process."""
    yield _helper(log_level)


def _pick_simulation(doc, sim_name):
    if sim_name is None:
        return doc.getSimulation(0)
    for i in range(doc.getSimulationCount()):
        sim = doc.getSimulation(i)
        if str(sim.getName()) == sim_name:
            return sim
    names = [str(doc.getSimulation(i).getName()) for i in range(doc.getSimulationCount())]
    raise KeyError(f"simulation {sim_name!r} not found; available: {names}")


def _stability_calibers(timeseries, diameter_m):
    D = orhelper.FlightDataType
    cg = np.asarray(timeseries[D.TYPE_CG_LOCATION], dtype=float)
    cp = np.asarray(timeseries[D.TYPE_CP_LOCATION], dtype=float)
    valid = np.isfinite(cg) & np.isfinite(cp) & (cp > 0)
    if not valid.any() or diameter_m <= 0:
        return float("nan")
    idx = int(np.argmax(valid))
    return float((cp[idx] - cg[idx]) / diameter_m)


def simulate(ork_path, sim_name=None):
    """Run one OpenRocket simulation headless.

    Returns a dict with apogee_m, max_velocity_ms, time_to_apogee_s,
    flight_time_s, ground_hit_ms, max_accel_ms2, stability_cal, runtime_ms.
    """
    ork_path = Path(ork_path)
    if not ork_path.exists():
        raise FileNotFoundError(ork_path)

    t0 = time.perf_counter()
    with _instance() as inst:
        orh = _helper()
        doc = orh.load_doc(str(ork_path))
        sim = _pick_simulation(doc, sim_name)
        orh.run_simulation(sim)

        D = orhelper.FlightDataType
        ts = orh.get_timeseries(
            sim,
            [
                D.TYPE_TIME,
                D.TYPE_CG_LOCATION,
                D.TYPE_CP_LOCATION,
            ],
        )

        diameter_m = float(sim.getRocket().getBoundingRadius()) * 2.0
        sd = sim.getSimulatedData()

        result = {
            "apogee_m": float(sd.getMaxAltitude()),
            "max_velocity_ms": float(sd.getMaxVelocity()),
            "time_to_apogee_s": float(sd.getTimeToApogee()),
            "flight_time_s": float(sd.getFlightTime()),
            "ground_hit_ms": float(sd.getGroundHitVelocity()),
            "max_accel_ms2": float(sd.getMaxAcceleration()),
            "stability_cal": _stability_calibers(ts, diameter_m),
        }
    result["runtime_ms"] = (time.perf_counter() - t0) * 1000.0
    return result


if __name__ == "__main__":
    import json
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "ork/ESTES Alpha 3.ork"
    name = sys.argv[2] if len(sys.argv) > 2 else None
    print(json.dumps(simulate(path, name), indent=2))
