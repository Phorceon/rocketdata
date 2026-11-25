"""Shared helpers for building sft_v1: sim extraction, thought/prompt rendering.

The thought and prompt rendering reproduce the exact string formats found in
data/sft_v0.jsonl (validated by scripts/verify_sft_v1.py).
"""
import re
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from ork_design import load_bytes  # noqa: E402
from xml.etree import ElementTree as ET  # noqa: E402

SYSTEM_MSG = ("You are an autonomous aerospace design engineer. When given flight "
              "requirements, you must first calculate the required propulsion, "
              "stability, and descent parameters, then output the final verified "
              "hardware blueprint in JSON format inside <design> tags.")


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def active_motors(root, configid):
    """Designations of the motors selected by a simulation's configid (each mount
    motor carries a configid; a cluster shares one, so return them all)."""
    out = []
    for m in root.iter("motor"):
        if m.get("configid") == configid:
            d = m.findtext("designation")
            if d and d not in out:
                out.append(d)
    return out


def sims_of(path):
    """All simulations with metrics, in document order: list of dicts."""
    root = ET.fromstring(load_bytes(path))
    out = []
    for sim in root.iter("simulation"):
        fd = sim.find("flightdata")
        if fd is None or fd.get("maxaltitude") is None:
            continue
        cond = sim.find("conditions")
        wind = None
        if cond is not None:
            wind = _f(cond.findtext("windaverage"))
        cid = (sim.findtext("conditions/configid") or sim.findtext("configid"))
        out.append({
            "name": sim.findtext("name"),
            "configid": cid,
            "active_motors": active_motors(root, cid),
            "apogee_m": _f(fd.get("maxaltitude")),
            "max_velocity_ms": _f(fd.get("maxvelocity")),
            "max_acceleration_ms2": _f(fd.get("maxacceleration")),
            "max_mach": _f(fd.get("maxmach")),
            "time_to_apogee_s": _f(fd.get("timetoapogee")),
            "flight_time_s": _f(fd.get("flighttime")),
            "ground_hit_ms": _f(fd.get("groundhitvelocity")),
            "deployment_velocity_ms": _f(fd.get("deploymentvelocity")),
            "wind_ms": wind if wind is not None else 0.0,
        })
    return out


def targets_of(sim):
    return {
        "apogee_m": sim["apogee_m"],
        "max_velocity_ms": sim["max_velocity_ms"],
        "max_mach": sim["max_mach"],
        "time_to_apogee_s": sim["time_to_apogee_s"],
        "flight_time_s": sim["flight_time_s"],
        "ground_hit_ms": sim["ground_hit_ms"],
        "wind_ms": sim["wind_ms"],
    }


# ------------------------------------------------------------- number format

def _comma(n):
    return f"{n:,}"


def fmt_apogee(x):
    return _comma(round(x))


def fmt_feet(x):
    return _comma(round(x * 3.28084))


def fmt_1(x):
    return f"{round(x, 1)}"


def fmt_2(x):
    return f"{x:.2f}"


# --------------------------------------------------------------- thought text

def render_thought(prompt_text, sim, design):
    """Reproduce the v0 <thought> block from the prompt, sim metrics, design."""
    a = sim["apogee_m"]
    lines = []
    lines.append("<thought>")
    lines.append("1. REQUIREMENTS PARSED:")
    lines.append("- " + prompt_text.strip())
    lines.append("")
    lines.append("2. PROPULSION & ASCENT:")
    lines.append("- Motor: " + motor_label(sim))
    lines.append(f"- Simulated apogee: {fmt_apogee(a)} m ({fmt_feet(a)} ft)")
    lines.append(f"- Time to apogee: {fmt_1(sim['time_to_apogee_s'])} s")
    lines.append(f"- Peak velocity: {round(sim['max_velocity_ms'])} m/s "
                 f"(Mach {fmt_2(sim['max_mach'])})")
    lines.append("")
    lines.append("3. RECOVERY & DESCENT:")
    for ln in recovery_lines(design):
        lines.append("- " + ln)
    ft = sim["flight_time_s"]
    desc = ft - sim["time_to_apogee_s"]
    lines.append(f"- Total flight time {round(ft)} s; descent from apogee takes "
                 f"{round(desc)} s")
    if sim.get("ground_hit_ms") is not None:
        lines.append(f"- Touchdown velocity: {fmt_2(sim['ground_hit_ms'])} m/s")
    lines.append("</thought>")
    return "\n".join(lines)


def motor_label(sim):
    """v0 shows the sim's single active motor, or a comma-joined list."""
    ms = sim.get("active_motors") or []
    if not ms:
        return "?"
    return ms[0] if len(ms) == 1 else ", ".join(ms)


def recovery_lines(design):
    """One line per parachute/streamer, in tree order; streamers emit 'Streamer
    recovery'."""
    out = []

    def walk(cs):
        for c in cs:
            if c["type"] == "parachute":
                ev = c.get("deploy_event")
                d = c.get("diameter_m")
                if ev == "apogee":
                    out.append(f"Parachute {d:.2f} m diameter, deploys at apogee")
                elif ev == "altitude" and c.get("deploy_altitude_m") is not None:
                    alt = c["deploy_altitude_m"]
                    # NOTE: v0 writes the deploy-altitude metres/feet WITHOUT a
                    # thousands separator (unlike the apogee line).
                    out.append(f"Parachute {d:.2f} m diameter, deploys at "
                               f"{round(alt)} m ({round(alt * 3.28084)} ft)")
                elif ev == "ejection":
                    out.append(f"Parachute {d:.2f} m diameter, deploys at ejection")
                else:
                    out.append(f"Parachute {d:.2f} m diameter, deploys at {ev}")
            elif c["type"] == "streamer":
                out.append("Streamer recovery")
            walk(c.get("contains", []))
    walk(design["components"])
    return out


# --------------------------------------------------------------- prompts

def render_design_ir(design):
    import json
    # v0 uses json.dumps defaults (ensure_ascii=True -> \uXXXX escapes).
    return json.dumps(design, separators=(",", ":"))


# --------------------------------------------------------------- prompts

def n_stages(design):
    n = 0

    def walk(cs):
        nonlocal n
        for c in cs:
            if c["type"] == "stage_marker":
                n += 1
            walk(c.get("contains", []))
    walk(design["components"])
    return max(n, 1)


def _p_apogee(t):
    return _comma(round(t["apogee_m"]))


def _p_vel(t):
    return fmt_1(t["max_velocity_ms"])


def _p_mach(t):
    return fmt_2(t["max_mach"])


def _p_tap(t):
    return fmt_1(t["time_to_apogee_s"])


def _p_flight(t):
    return fmt_1(t["flight_time_s"])


def _p_gh(t):
    return fmt_1(t["ground_hit_ms"])


def _p_acc(t, sim):
    return fmt_1(sim["max_acceleration_ms2"])


# A bank of prompt templates. Each takes (t=targets, sim, motor, stages, ft)
# and returns a single-line prompt. Phrasing mirrors the v0 prompt families so
# the schema and tone match exactly while phrasing/param-count varies.
PROMPT_TEMPLATES = [
    lambda t, s, m, n, ft: f"Design a rocket that goes to about {_p_apogee(t)} m apogee in about {_p_tap(t)} s to apogee.",
    lambda t, s, m, n, ft: f"Design a rocket that goes to about {_p_apogee(t)} m apogee in about {_p_tap(t)} s to apogee on a {m} motor.",
    lambda t, s, m, n, ft: f"Design a rocket that goes to about {_p_apogee(t)} m apogee on a {m} motor, taking about {_p_tap(t)} s to apogee.",
    lambda t, s, m, n, ft: f"Design a rocket that goes on a {m} motor to apogee in about {_p_tap(t)} s.",
    lambda t, s, m, n, ft: f"Design a rocket that goes to about {_p_apogee(t)} m apogee with a total flight time of about {_p_flight(t)} s.",
    lambda t, s, m, n, ft: f"Design a rocket that goes to about {_p_apogee(t)} m apogee, reaching about {_p_vel(t)} m/s max velocity.",
    lambda t, s, m, n, ft: f"Design a rocket that goes to about {_p_apogee(t)} m apogee and touches down at about {_p_gh(t)} m/s.",
    lambda t, s, m, n, ft: f"Design a rocket that goes to about {_p_vel(t)} m/s max velocity at about {_p_acc(t, s)} m/s\u00b2 max acceleration.",
    lambda t, s, m, n, ft: f"Design a rocket that goes to about {_p_vel(t)} m/s on a {m} motor, reaching apogee in about {_p_tap(t)} s.",
    lambda t, s, m, n, ft: f"Design a rocket that goes to about {_p_vel(t)} m/s max velocity with a {_p_flight(t)} s flight and touchdown at about {_p_gh(t)} m/s.",
    lambda t, s, m, n, ft: f"Design a rocket that goes through about {_p_acc(t, s)} m/s\u00b2 max acceleration over a {_p_flight(t)} s flight.",
    lambda t, s, m, n, ft: f"Design a rocket that goes to about {_p_apogee(t)} m apogee with deployment at about {_p_gh(t)} m/s and a {_p_flight(t)} s flight.",
    lambda t, s, m, n, ft: f"Design a rocket that goes to about {_p_apogee(t)} m apogee in about {_p_tap(t)} s to apogee.",
    lambda t, s, m, n, ft: f"Design a rocket that goes to about {_p_apogee(t)} m apogee, hitting about {_p_acc(t, s)} m/s\u00b2 max acceleration.",
    lambda t, s, m, n, ft: f"Make a rocket that hits {_p_apogee(t)} m and stays up about {round(t['flight_time_s'])} s on a {m} motor.",
    lambda t, s, m, n, ft: f"Make a rocket that hits {_p_apogee(t)} m and stays up about {round(t['flight_time_s'])} s.",
    lambda t, s, m, n, ft: f"Build a rocket on a {m} motor that reaches about {_p_apogee(t)} m and is back down in about {round(t['flight_time_s'])} seconds.",
    lambda t, s, m, n, ft: f"Design a rocket on a {m} motor that reaches about {_p_apogee(t)} m and stays up close to {round(t['flight_time_s'])} seconds.",
    lambda t, s, m, n, ft: f"I want a rocket that climbs about {_p_apogee(t)} m and comes down gently, under {_p_gh(t)} m/s.",
    lambda t, s, m, n, ft: f"Design a rocket that goes to about {_p_apogee(t)} m apogee, hitting about Mach {_p_mach(t)} and {_p_acc(t, s)} m/s\u00b2 max acceleration.",
    lambda t, s, m, n, ft: f"Make a rocket that reaches about {_p_apogee(t)} m on a {m} motor and is down in about {round(t['flight_time_s'])} seconds.",
    lambda t, s, m, n, ft: f"Design a rocket that goes to apogee in about {_p_tap(t)} s with a total flight of about {_p_flight(t)} s.",
    lambda t, s, m, n, ft: f"Design a rocket that goes to about {_p_apogee(t)} m apogee in about {_p_tap(t)} s to apogee on a {m} motor.",
    lambda t, s, m, n, ft: f"Give me a rocket that tops out near {_p_apogee(t)} m and lands under {_p_gh(t)} m/s.",
    lambda t, s, m, n, ft: f"I need a rocket on a {m} motor that gets up close to {_p_apogee(t)} m.",
    lambda t, s, m, n, ft: f"Design a rocket that goes about {_p_apogee(t)} m and is back down in under {round(t['flight_time_s'])} seconds.",
]


def pick_prompt(templates, t, sim, motor, stages, rng):
    fn = templates[rng.randrange(len(templates))]
    return fn(t, sim, motor, stages, fmt_feet(t["apogee_m"]))
