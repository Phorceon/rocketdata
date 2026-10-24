"""The three tools the deployed model gets: motor_lookup, stability, simulate.

Each takes the tool-call arguments dict and returns a JSON-serialisable dict in
the shapes pinned in contract.py. Errors come back as {"ok": false, "error": ...}
rather than raising, exactly as the deployed harness will return them.

    from sftgen import tools
    tools.call("simulate", {"design": {...}}, seed=7)
"""

from __future__ import annotations

import json
import math
import os
import tempfile
import threading

from pydantic import ValidationError

from . import motors, orkbuild
from .schema import MotorMount, Parachute, Streamer, parse_design

G0 = 9.80665
# Long enough for a main-only descent from ~15 km; OpenRocket's default 1200 s cuts high flights off mid-air.
MAX_SIM_TIME_S = 3600.0
_LOCK = threading.Lock()


def _err(msg: str, **extra) -> dict:
    return {"ok": False, "error": msg, **extra}


def _validation_message(e: ValidationError) -> str:
    out = []
    for err in e.errors()[:6]:
        loc = ".".join(str(p) for p in err["loc"])
        out.append(f"{loc}: {err['msg']}")
    more = len(e.errors()) - 6
    if more > 0:
        out.append(f"... and {more} more")
    return "invalid design: " + "; ".join(out)


def _parse(design_arg):
    try:
        return parse_design(design_arg), None
    except ValidationError as e:
        return None, _err(_validation_message(e))
    except (ValueError, TypeError) as e:
        return None, _err(f"invalid design: {e}")


# ---------------------------------------------------------------- motor_lookup

def motor_lookup(args: dict) -> dict:
    desig = args.get("designation")
    if not isinstance(desig, str) or not desig.strip():
        return _err("designation is required")
    try:
        info = motors.resolve(desig, args.get("manufacturer"))
    except motors.UnknownMotor as e:
        return _err(str(e), suggestions=e.suggestions)
    return {"ok": True, **motors.public(info)}


# ---------------------------------------------------------------- OpenRocket plumbing

def _load(design, cond: dict):
    from scripts.or_headless import _helper

    orh = _helper()
    xml = orkbuild.to_ork_xml(design, cond)
    fd, path = tempfile.mkstemp(suffix=".ork", prefix="sftgen_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(xml)
        doc = orh.load_doc(path)
    finally:
        os.unlink(path)
    return orh, doc


def _launch_stats(doc):
    from jpype import JClass

    sim = doc.getSimulation(0)
    rocket = doc.getRocket()
    config = rocket.getFlightConfiguration(sim.getFlightConfigurationId())
    MassCalculator = JClass("info.openrocket.core.masscalc.MassCalculator")
    Barrowman = JClass("info.openrocket.core.aerodynamics.BarrowmanCalculator")
    FlightConditions = JClass("info.openrocket.core.aerodynamics.FlightConditions")
    WarningSet = JClass("info.openrocket.core.logging.WarningSet")
    body = MassCalculator.calculateLaunch(config)
    fc = FlightConditions(config)
    fc.setMach(0.3)
    fc.setAOA(0.0)
    cp = Barrowman().getWorstCP(config, fc, WarningSet())
    ref_d = float(fc.getRefLength())
    mass = float(body.getMass())
    cg_x = float(body.getCM().x)
    cp_x = float(cp.x) if float(cp.weight) > 1e-9 else float("nan")
    return {
        "liftoff_mass_kg": mass,
        "cg_m": cg_x,
        "cp_m": cp_x,
        "length_m": float(rocket.getLength()) if hasattr(rocket, "getLength") else float("nan"),
        "reference_diameter_m": ref_d,
        "static_margin_cal": (cp_x - cg_x) / ref_d if ref_d > 0 else float("nan"),
    }


def _r(x, nd):
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return None
    return round(float(x), nd)


def _sig(x, sig=3):
    if x is None or not math.isfinite(x) or x == 0:
        return _r(x, 3)
    nd = max(0, sig - 1 - int(math.floor(math.log10(abs(x)))))
    return round(x, nd)


# ---------------------------------------------------------------- stability

def stability(args: dict) -> dict:
    design, err = _parse(args.get("design"))
    if err:
        return err
    try:
        with _LOCK:
            _, doc = _load(design, None)
            st = _launch_stats(doc)
    except motors.UnknownMotor as e:
        return _err(str(e), suggestions=e.suggestions)
    except orkbuild.BuildError as e:
        return _err(f"invalid design: {e}")
    if not math.isfinite(st["static_margin_cal"]):
        return _err("could not compute CP for this design (no fins or zero-area body?)")
    return {
        "ok": True,
        "liftoff_mass_kg": _sig(st["liftoff_mass_kg"]),
        "cg_m": _r(st["cg_m"], 3),
        "cp_m": _r(st["cp_m"], 3),
        "length_m": _r(_design_length(design), 3),
        "reference_diameter_m": _r(st["reference_diameter_m"], 4),
        "static_margin_cal": _r(st["static_margin_cal"], 2),
    }


def _design_length(design) -> float:
    total = 0.0
    for st in design.stages:
        for c in st.components:
            total += c.length_m
    return total


# ---------------------------------------------------------------- simulate

def _first_stage_thrust(design) -> tuple[float, float]:
    """(sum of average thrust, total impulse) for motors lit at launch, and impulse of all motors."""
    lit = 0.0
    total_impulse = 0.0
    bottom = len(design.stages) - 1
    for si, mm in design.motors():
        info = motors.resolve(mm.motor.designation, mm.motor.manufacturer)
        total_impulse += info["total_impulse_ns"] * mm.cluster_count
        if si == bottom:
            lit += info["average_thrust_n"] * mm.cluster_count
    return lit, total_impulse


def simulate(args: dict, seed: int = 0, base_conditions: dict | None = None) -> dict:
    design, err = _parse(args.get("design"))
    if err:
        return err
    over = args.get("conditions") or {}
    if not isinstance(over, dict):
        return _err("conditions must be an object")
    cond = orkbuild.conditions({**(base_conditions or {}), **over})
    try:
        lit_thrust, total_impulse = _first_stage_thrust(design)
        with _LOCK:
            orh, doc = _load(design, cond)
            launch = _launch_stats(doc)
            sim = doc.getSimulation(0)
            sim.getOptions().setRandomSeed(int(seed))
            sim.getOptions().setMaxSimulationTime(MAX_SIM_TIME_S)
            # orhelper.Helper.run_simulation() re-randomises the seed, and OpenRocket 24.12 builds
            # its turbulent wind model unseeded, so swap in a seeded one when the run starts.
            sim.simulate(_seeded_wind_listeners(int(seed), cond, sim.getOptions()))
            out = _collect(sim, design, cond, launch)
    except motors.UnknownMotor as e:
        return _err(str(e), suggestions=e.suggestions)
    except orkbuild.BuildError as e:
        return _err(f"invalid design: {e}")
    out["thrust_to_weight"] = _r(lit_thrust / (launch["liftoff_mass_kg"] * G0), 1)
    out["total_impulse_ns"] = _r(total_impulse, 1)
    order = [
        "ok", "apogee_m", "time_to_apogee_s", "max_velocity_ms", "max_mach", "rail_exit_ms",
        "liftoff_mass_kg", "thrust_to_weight", "stability_rail_exit_cal", "min_stability_burn_cal",
        "flight_time_s", "total_impulse_ns", "sections", "warnings", "conditions",
    ]
    return {k: out[k] for k in order}


def _seeded_wind_listeners(seed: int, cond: dict, options):
    import jpype
    import orhelper

    PinkNoise = jpype.JClass("info.openrocket.core.models.wind.PinkNoiseWindModel")
    direction = float(options.getWindDirection())

    class SeededWind(orhelper.AbstractSimulationListener):
        def startSimulation(self, status):
            wind = PinkNoise(jpype.JInt(seed))
            wind.setAverage(float(cond["wind_ms"]))
            wind.setTurbulenceIntensity(float(cond["wind_turbulence"]))
            wind.setDirection(direction)
            status.getSimulationConditions().setWindModel(wind)

    core = "info.openrocket.core.simulation.listeners."
    proxy = jpype.JProxy(
        (
            jpype.JClass(core + "SimulationListener"),
            jpype.JClass(core + "SimulationEventListener"),
            jpype.JClass(core + "SimulationComputationListener"),
            jpype.java.lang.Cloneable,
        ),
        inst=SeededWind(),
    )
    return [proxy]


def _collect(sim, design, cond, launch) -> dict:
    from jpype import JClass

    T = JClass("info.openrocket.core.simulation.FlightDataType")
    Ev = JClass("info.openrocket.core.simulation.FlightEvent$Type")
    sd = sim.getSimulatedData()

    main = sd.getBranch(0)
    times = list(main.get(T.TYPE_TIME))
    stab = list(main.get(T.TYPE_STABILITY))
    rod_t = None
    burnout_t = None
    for e in main.getEvents():
        et = e.getType()
        if et == Ev.LAUNCHROD and rod_t is None:
            rod_t = float(e.getTime())
        if et == Ev.BURNOUT:
            burnout_t = float(e.getTime())

    def stab_at(t):
        best = None
        for ti, si in zip(times, stab):
            if ti >= t and math.isfinite(si):
                return float(si)
            best = si
        return float(best) if best is not None and math.isfinite(best) else None

    rail_stab = stab_at(rod_t) if rod_t is not None else None
    burn_vals = [float(s) for t, s in zip(times, stab)
                 if rod_t is not None and burnout_t is not None and rod_t <= t <= burnout_t and math.isfinite(s)]
    min_burn = min(burn_vals) if burn_vals else rail_stab

    # Which stages carry recovery, by OpenRocket branch name (= stage name of the section's top stage).
    sections = []
    for bi in range(sd.getBranchCount()):
        br = sd.getBranch(bi)
        bt = list(br.get(T.TYPE_TIME))
        vz = list(br.get(T.TYPE_VELOCITY_Z))
        vtot = list(br.get(T.TYPE_VELOCITY_TOTAL))
        xy = list(br.get(T.TYPE_POSITION_XY))
        deploy_t = deploy_v = None
        ground = False
        for e in br.getEvents():
            et = e.getType()
            if et == Ev.RECOVERY_DEVICE_DEPLOYMENT and deploy_t is None:
                deploy_t = float(e.getTime())
            if et == Ev.GROUND_HIT:
                ground = True
        if deploy_t is not None:
            for ti, v in zip(bt, vtot):
                if ti >= deploy_t:
                    deploy_v = float(v)
                    break
        landing = None
        if vz and math.isfinite(vz[-1]):
            # Vertical descent rate at touchdown; the horizontal part is wind drift, which no
            # recovery device can remove, and landing limits in rocketry mean descent rate.
            landing = abs(float(vz[-1]))
        sections.append({
            "name": str(br.getName()),
            "landing_ms": _r(landing, 1),
            "drift_m": _r(float(xy[-1]) if xy else None, 0),
            "recovery_deployed": deploy_t is not None,
            "deploy_time_s": _r(deploy_t, 1),
            "deploy_velocity_ms": _r(deploy_v, 1),
            "flight_time_s": _r(float(bt[-1]) if bt else None, 1),
            "reached_ground": ground,
        })

    warnings = sorted({str(w) for w in sim.getSimulatedWarnings()}) if sim.getSimulatedWarnings() else []
    return {
        "ok": True,
        "apogee_m": _r(sd.getMaxAltitude(), 1),
        "time_to_apogee_s": _r(sd.getTimeToApogee(), 2),
        "max_velocity_ms": _r(sd.getMaxVelocity(), 1),
        "max_mach": _r(sd.getMaxMachNumber(), 2),
        "rail_exit_ms": _r(sd.getLaunchRodVelocity(), 1),
        "liftoff_mass_kg": _sig(launch["liftoff_mass_kg"]),
        "stability_rail_exit_cal": _r(rail_stab, 2),
        "min_stability_burn_cal": _r(min_burn, 2),
        "flight_time_s": _r(sd.getFlightTime(), 1),
        "sections": sections,
        "warnings": warnings,
        "conditions": {k: cond[k] for k in ("wind_ms", "rail_length_m", "launch_angle_deg", "site_altitude_m")},
    }


# ---------------------------------------------------------------- dispatch

def call(name: str, args: dict, seed: int = 0, base_conditions: dict | None = None) -> dict:
    if not isinstance(args, dict):
        return _err("arguments must be an object")
    if name == "motor_lookup":
        return motor_lookup(args)
    if name == "stability":
        return stability(args)
    if name == "simulate":
        return simulate(args, seed=seed, base_conditions=base_conditions)
    return _err(f"unknown tool {name!r}")


def dumps(out: dict) -> str:
    return json.dumps(out, ensure_ascii=False)


if __name__ == "__main__":
    import sys

    name = sys.argv[1]
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else json.load(sys.stdin)
    print(json.dumps(call(name, payload), indent=1, ensure_ascii=False))
