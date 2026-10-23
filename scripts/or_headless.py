"""Headless OpenRocket simulation driver.

Results are reproducible: before OpenRocket boots we install the deterministic
SecureRandom provider from scripts/or_batch/OrBatch.java (component UUIDs, which key
OpenRocket's motor HashMap, are otherwise random per load), every call loads the .ork
fresh with UUID seed 42, and the wind models are rebuilt from `seed` (setRandomSeed()
alone does not reseed them). Same inputs -> bit-identical outputs, and the same numbers
as scripts/resim_v2.py / new_results/sft_v2_sims.jsonl.
"""

from __future__ import annotations

import os
import time
from contextlib import contextmanager
from pathlib import Path

import subprocess

import jpype
import jpype.imports
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_JAR = REPO_ROOT / "lib" / "OpenRocket.jar"
DEFAULT_JAVA_HOME = Path.home() / ".jdks" / "jdk-17.0.20.1+1" / "Contents" / "Home"

JVM_ARGS = ["-Djava.awt.headless=true", "-Dsun.jnu.encoding=UTF-8", "-Dfile.encoding=UTF-8"]
OR_BATCH_SRC = REPO_ROOT / "scripts" / "or_batch" / "OrBatch.java"
OR_BATCH_CLASSES = REPO_ROOT / "lib" / "or_batch_classes"
UUID_SEED = 42

JVM_STARTED = False
BOOTED = False
_WARM = set()


def _java_home() -> Path:
    return Path(os.environ.get("OPENROCKET_JAVA_HOME", DEFAULT_JAVA_HOME))


def _jar() -> Path:
    return Path(os.environ.get("OPENROCKET_JAR", DEFAULT_JAR))


def _libjvm() -> str:
    jvm = _java_home() / "lib" / "server" / "libjvm.dylib"
    if not jvm.exists():
        jvm = _java_home() / "lib" / "server" / "libjvm.so"
    if not jvm.exists():
        raise FileNotFoundError(f"libjvm not found under {_java_home()}")
    return str(jvm)


def _compile_or_batch(jar: str) -> str:
    """Compile OrBatch.java (determinism helpers) into lib/or_batch_classes if stale."""
    out = OR_BATCH_CLASSES
    stamp = out / "OrBatch.class"
    if not stamp.exists() or stamp.stat().st_mtime < OR_BATCH_SRC.stat().st_mtime:
        out.mkdir(parents=True, exist_ok=True)
        javac = _java_home() / "bin" / "javac"
        subprocess.run([str(javac), "--release", "17", "-nowarn", "-cp", jar, "-d", str(out),
                        str(OR_BATCH_SRC)], check=True, capture_output=True)
    return str(out)


def _start_jvm():
    global JVM_STARTED
    if JVM_STARTED:
        return
    jar = str(_jar())
    if not os.path.exists(jar):
        raise FileNotFoundError(f"OpenRocket JAR not found at {jar}")
    if not jpype.isJVMStarted():
        cp = os.pathsep.join([jar, _compile_or_batch(jar)])
        jpype.startJVM(_libjvm(), "-ea", f"-Djava.class.path={cp}", *JVM_ARGS)
    JVM_STARTED = True


def _boot_or():
    global BOOTED
    if BOOTED:
        return
    _start_jvm()
    # must run before anything in the JVM calls UUID.randomUUID()
    jpype.JClass("OrBatch").installDet()
    Guice = jpype.JClass("com.google.inject.Guice")
    PluginModule = jpype.JClass("info.openrocket.core.plugin.PluginModule")
    GuiModule = jpype.JClass("info.openrocket.swing.startup.GuiModule")
    Application = jpype.JClass("info.openrocket.core.startup.Application")
    gui = GuiModule()
    injector = Guice.createInjector(gui, PluginModule())
    Application.setInjector(injector)
    Application.getPreferences()
    try:
        gui.startLoader()
    except Exception:
        pass
    try:
        presets = gui.getClass().getDeclaredField("presetLoader")
        presets.setAccessible(True)
        pl = presets.get(gui)
        if pl is not None:
            pl.blockUntilLoaded()
    except Exception:
        pass
    try:
        motors = gui.getClass().getDeclaredField("motorLoader")
        motors.setAccessible(True)
        ml = motors.get(gui)
        if ml is not None:
            ml.blockUntilLoaded()
    except Exception:
        pass
    BOOTED = True


def _get_sim(doc, sim_name):
    if sim_name is None:
        return doc.getSimulation(0)
    for i in range(doc.getSimulationCount()):
        sim = doc.getSimulation(i)
        if str(sim.getName()) == sim_name:
            return sim
    names = [str(doc.getSimulation(i).getName()) for i in range(doc.getSimulationCount())]
    raise KeyError(f"simulation {sim_name!r} not found; available: {names}")


def _stability_calibers_from_sim(sim, diameter_m):
    try:
        sd = sim.getSimulatedData()
        cg = sd.getCGPoints()
        cp = sd.getCPPoints()
        if cg is None or cp is None:
            return float("nan")
        n = cg.getLength()
        if n == 0 or diameter_m <= 0:
            return float("nan")
        for i in range(n - 1, -1, -1):
            try:
                cgv = cg.get(i)
                cpv = cp.get(i)
                if cgv is not None and cpv is not None and float(cpv) > 0:
                    return float((float(cpv) - float(cgv)) / diameter_m)
            except Exception:
                continue
    except Exception:
        pass
    return float("nan")


@contextmanager
def _instance(log_level: str = "ERROR"):
    _boot_or()
    yield None


def simulate(ork_path, sim_name=None, seed=42):
    ork_path = Path(ork_path)
    if not ork_path.exists():
        raise FileNotFoundError(ork_path)

    _boot_or()
    OrBatch = jpype.JClass("OrBatch")
    GeneralRocketLoader = jpype.JClass("info.openrocket.core.file.GeneralRocketLoader")
    File = jpype.JClass("java.io.File")
    def load():
        # fresh load every call: a reused document carries state between runs
        OrBatch.seedUUID(UUID_SEED)
        d = GeneralRocketLoader(File(str(ork_path))).load()
        return d, _get_sim(d, sim_name)

    key = (str(ork_path.resolve()), sim_name)
    if key not in _WARM:
        # the first run of a design in a JVM differs at ~1e-14 (OpenRocket fills lazy
        # caches on first use); one discarded warm-up run makes results run-order independent
        _, wsim = load()
        OrBatch.reseed(wsim.getOptions(), int(seed))
        wsim.simulate()
        _WARM.add(key)
    doc, sim = load()

    t_sim0 = time.perf_counter()
    opts = sim.getOptions()
    OrBatch.reseed(opts, int(seed))
    sim.simulate()
    sim_ms = (time.perf_counter() - t_sim0) * 1000.0

    sd = sim.getSimulatedData()
    diameter_m = float(sim.getRocket().getBoundingRadius()) * 2.0
    stability_cal = _stability_calibers_from_sim(sim, diameter_m)

    try:
        max_mach = float(sd.getMaxMachNumber())
    except Exception:
        max_mach = float("nan")
    try:
        deploy_v = float(sd.getDeploymentVelocity())
    except Exception:
        deploy_v = float("nan")
    try:
        opts = sim.getOptions()
        wind_ms = float(opts.getWindSpeedAverage())
    except Exception:
        wind_ms = 0.0
    result = {
        "apogee_m": float(sd.getMaxAltitude()),
        "max_velocity_ms": float(sd.getMaxVelocity()),
        "time_to_apogee_s": float(sd.getTimeToApogee()),
        "flight_time_s": float(sd.getFlightTime()),
        "ground_hit_ms": float(sd.getGroundHitVelocity()),
        "max_accel_ms2": float(sd.getMaxAcceleration()),
        "max_mach": max_mach,
        "deployment_velocity_ms": deploy_v,
        "wind_ms": wind_ms,
        "stability_cal": stability_cal,
        "events": [{"branch": b, "type": str(e.getType().name()), "t": float(e.getTime())}
                   for b in range(sd.getBranchCount())
                   for e in sd.getBranch(b).getEvents()],
        "runtime_ms": sim_ms,
    }
    return result


if __name__ == "__main__":
    import json
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "ork/ESTES Alpha 3.ork"
    name = sys.argv[2] if len(sys.argv) > 2 else None
    print(json.dumps(simulate(path, name), indent=2))
