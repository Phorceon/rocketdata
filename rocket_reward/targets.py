"""Stage 7: does the rocket do what the prompt asked?

Every design that reaches this stage has flown safely. Here it earns a credit
`t` from 0 to 1: the product of one credit per target the requirements state,
all read from the nominal flight (the 1x-wind flight, limits.NOMINAL_FLIGHT)
of the simulator's reply (java/PROTOCOL.md). Every target counts the same way,
with no weights, so missing one target by a given amount costs the same
whatever else the prompt states, and missing two never beats missing one.

  apogee_m, flight_time_s, time_to_apogee_s, max_velocity_ms, max_accel_ms2
      the flight's own number, judged with ladder.closeness
  landing_ms
      the main section's vertical landing speed. For a "max" target the
      landing earns full credit from a comfort floor up to the limit with its
      tolerance (limits.LANDING_SLACK_DEFAULT when the target gives none: the
      prompts were written from one flight with no margin); slower than the
      floor the credit falls in proportion (a needlessly large parachute
      drifts far); faster than the limit ladder.closeness judges it. Stage 6
      judges only the landing limits that hold for every rocket, so this is
      the only place the prompt's landing number counts
  body_diameter_m
      the widest body tube OpenRocket built
  mass_kg
      the mass on the pad, motors included
  motors
      ladder.MOTORS_CREDIT_MIN plus the rest in proportion to the share of the
      motors the prompt names that the flown configuration really uses
  motor_class
      1 when the largest flown motor is of that impulse class,
      ladder.MOTOR_CLASS_NEAR_CREDIT when it is one letter away, else
      ladder.MOTOR_CLASS_FAR_CREDIT (also when no flown motor has a known
      impulse)

A numeric target whose measured value is missing earns 0, so t is 0. The
stage always passes; StageCheck.defects stays empty.
"""
from __future__ import annotations

import math
from typing import Any, Optional

from . import ladder
from .limits import LANDING_SLACK_DEFAULT, NOMINAL_FLIGHT
from .motors import (MotorTable, _motor_fields, _norm_designation, class_from_designation,
                     flown_motors, impulse_class)
from .records import TARGET_FIELDS, Requirements, StageCheck, Target
from .tree import Node

# How each target is named in a reason, its unit, and the factor that turns the
# stored SI value into the shown unit (diameters are shown in millimetres).
_TARGET_TEXT: dict[str, tuple[str, str, float]] = {
    "apogee_m": ("apogee", "m", 1.0),
    "landing_ms": ("landing speed", "m/s", 1.0),
    "flight_time_s": ("flight time", "s", 1.0),
    "time_to_apogee_s": ("time to apogee", "s", 1.0),
    "max_velocity_ms": ("top speed", "m/s", 1.0),
    "max_accel_ms2": ("top acceleration", "m/s2", 1.0),
    "body_diameter_m": ("body diameter", "mm", 1000.0),
    "mass_kg": ("liftoff mass", "kg", 1.0),
}
_FLIGHT_FIELDS = ("apogee_m", "flight_time_s", "time_to_apogee_s", "max_velocity_ms", "max_accel_ms2")
_TIMED_FIELDS = ("flight_time_s", "time_to_apogee_s")   # measured from the first ignition, not from the simulation start
_KIND_WORDS = {"about": "about", "max": "at most", "min": "at least"}
_FULL = 1.0 - 1e-9          # a credit at or above this has lost nothing worth reporting
_MAX_NAME_CHARS = 60        # motor names are cut to this length inside reasons
_MAX_NAMED_MOTORS = 50      # a prompt never names more; beyond this they are not compared


# ---------------------------------------------------------------------------
# reading the reply

def _dict(x: Any) -> dict:
    return x if isinstance(x, dict) else {}


def _reply_number(x: Any) -> Optional[float]:
    """A finite number from the reply, else None (booleans and text do not count)."""
    return float(x) if ladder.is_number(x) else None


def _nominal_flight(reply: dict) -> dict:
    """The 1x-wind flight, or {} when the reply has none with numbers."""
    flights = reply.get("flights")
    if not isinstance(flights, list) or len(flights) <= NOMINAL_FLIGHT:
        return {}
    flight = _dict(flights[NOMINAL_FLIGHT])
    return flight if flight.get("ok") is True else {}


def _main_landing_speed(flight: dict) -> Optional[float]:
    """Vertical landing speed of the main section (branch 0), m/s."""
    branches = flight.get("branches")
    if not isinstance(branches, list) or not branches:
        return None
    main = next((b for b in branches if isinstance(b, dict) and b.get("index") == 0), None)
    if main is None:
        main = _dict(branches[0])
    v = _reply_number(main.get("landing_vertical_ms"))
    # Downward and positive (java/PROTOCOL.md); anything else is an odd reply and
    # counts as no value, as stage 6 counts it.
    return v if v is not None and v > 0 else None


def _active_parts(reply: dict) -> list[dict]:
    parts = reply.get("components")
    if not isinstance(parts, list):
        return []
    return [c for c in parts if isinstance(c, dict) and c.get("active") is not False]


def _body_diameter(reply: dict) -> Optional[float]:
    """Outer diameter (m) of the widest main-body tube OpenRocket built (tubes
    inside a pod or side booster do not count: a stub there is not the
    rocket's body); the rocket's widest body part when the reply lists no
    main-body tube."""
    from .fit import _Parts   # the same safe parent links stage 5 uses
    comps = reply.get("components")
    parts = _Parts(comps if isinstance(comps, list) else [])
    widest = None
    for c in parts.all:
        if c.get("type") != "BodyTube" or c.get("active") is False or parts.in_pod(c):
            continue
        for key in ("outer_radius_fore_m", "outer_radius_aft_m"):
            r = _reply_number(c.get(key))
            if r is not None and r > 0 and (widest is None or r > widest):
                widest = r
    if widest is not None:
        return 2.0 * widest
    return _reply_number(_dict(reply.get("rocket")).get("max_diameter_m"))


def _flown_motor_list(reply: dict, root: Node, table: MotorTable) -> list[dict]:
    """Every motor the flown configuration uses, as {"designation", "names",
    "impulse_ns"}. `names` holds every designation the motor goes by (as flown,
    as the file asked for it, OpenRocket's common name), normalised as motors.py
    compares them. Read from the reply; from the design and the motor table
    when the reply lists no motor."""
    out = []
    for c in _active_parts(reply):
        m = c.get("motor")
        if not isinstance(m, dict):
            continue
        des = m.get("designation")
        names = {_norm_designation(n) for n in (des, m.get("requested_designation"))
                 if isinstance(n, str) and n.strip() and len(n) <= 200}
        out.append({"designation": des if isinstance(des, str) else None, "names": names,
                    "impulse_ns": _reply_number(m.get("total_impulse_ns"))})
    if out:
        return out
    for node in flown_motors(root) if isinstance(root, dict) else []:
        key = table.resolve(*_motor_fields(node)[:3])
        if key is None:
            continue
        e = table.get(key)
        names = {_norm_designation(n) for n in (e.get("designation"), e.get("openrocket_common_name"))
                 if isinstance(n, str) and n.strip()}
        out.append({"designation": e.get("designation"), "names": names,
                    "impulse_ns": _reply_number(e.get("total_impulse_ns"))})
    return out


# ---------------------------------------------------------------------------
# text

def _figure(x: float) -> str:
    """A measured or asked number, shown with sensible precision."""
    if not math.isfinite(x):
        return str(x)
    a = abs(x)
    if a >= 100:
        return f"{x:,.0f}"
    if a >= 10:
        return f"{x:.1f}"
    if a >= 1:
        return f"{x:.2f}"
    return f"{x:.3g}"


def _asked_text(field: str, target: Target) -> str:
    """'about 500 m (5% allowed)', 'at most 5.0 m/s'."""
    _, unit, factor = _TARGET_TEXT[field]
    text = f"{_KIND_WORDS.get(target.kind, target.kind)} {_figure(target.value * factor)} {unit}"
    tol = _landing_tol(target) if field == "landing_ms" else target.tol
    if tol is None:
        tol = ladder.DEFAULT_ABOUT_TOL if target.kind == "about" else 0.0
    if tol > 0:
        text += f" ({tol * 100:.4g}% allowed)"
    return text


def _cut(name: Any) -> str:
    text = name if isinstance(name, str) else repr(name)
    return text if len(text) <= _MAX_NAME_CHARS else text[:_MAX_NAME_CHARS] + "..."


# ---------------------------------------------------------------------------
# the credits

def landing_credit(speed: Optional[float], target: Target) -> float:
    """Credit for the main section's landing speed against a landing target.

    For a "max" target: full credit from the comfort floor, min(3.5 m/s, 60% of
    the limit) (ladder.LANDING_COMFORT_*), up to the limit with its tolerance
    (limits.LANDING_SLACK_DEFAULT when the target gives none; a given tol, 0.0
    included, is used as given); below the floor speed / floor; above the limit
    ladder.closeness. Other kinds use ladder.closeness alone. A missing or zero
    speed earns 0.
    """
    if speed is None or not ladder.is_number(speed) or speed <= 0:
        return 0.0
    if target.kind != "max":
        return ladder.closeness(speed, target.value, target.kind, target.tol)
    floor = _comfort_floor(target)
    if speed < floor:
        return ladder.clamp01(speed / floor)
    return ladder.closeness(speed, target.value, "max", _landing_tol(target))


def _landing_tol(target: Target) -> Optional[float]:
    """The tolerance a landing target is judged with: a "max" target that gives
    none gets limits.LANDING_SLACK_DEFAULT (the prompts were written from one
    flight with no margin); any other target keeps its own."""
    if target.kind == "max" and target.tol is None:
        return LANDING_SLACK_DEFAULT
    return target.tol


def _comfort_floor(target: Target) -> float:
    return min(ladder.LANDING_COMFORT_MIN_MS, ladder.LANDING_COMFORT_FRACTION * target.value)


def _number_target(field: str, value: Optional[float], target: Target) -> tuple[float, Optional[str]]:
    """Credit and reason (None when nothing was lost) for one numeric target."""
    name, unit, factor = _TARGET_TEXT[field]
    if field == "landing_ms":
        credit = landing_credit(value, target)
    else:
        credit = ladder.closeness(value, target.value, target.kind, target.tol)
    if credit >= _FULL:
        return credit, None
    asked = _asked_text(field, target)
    if value is None:
        return credit, f"{name}: the flight gives no value, asked for {asked}: credit 0"
    shown = f"{name} {_figure(value * factor)} {unit}"
    if field == "landing_ms" and target.kind == "max" and 0 < value < _comfort_floor(target):
        floor = _comfort_floor(target)
        return credit, (f"{shown}, {_figure(floor - value)} m/s slower than needed (full credit from "
                        f"{_figure(floor)} m/s up to the limit, {asked}), so the parachute is larger "
                        f"than it needs to be: credit {credit:.2f}")
    return credit, f"{shown}, asked for {asked}: credit {credit:.2f}"


def _motors_target(named: tuple[str, ...], flown: list[dict]) -> tuple[float, dict, Optional[str]]:
    """ladder.MOTORS_CREDIT_MIN plus the rest of the credit in proportion to the
    share of the named motors the flown configuration uses."""
    wanted: dict[str, str] = {}
    for n in named[:_MAX_NAMED_MOTORS]:
        if isinstance(n, str) and n.strip() and len(n) <= 200:
            wanted.setdefault(_norm_designation(n), n)
    flown_names = set().union(*(m["names"] for m in flown)) if flown else set()
    found = [w for w in wanted if w in flown_names]
    missing = [wanted[w] for w in wanted if w not in flown_names]
    share = len(found) / len(wanted) if wanted else 0.0
    credit = ladder.MOTORS_CREDIT_MIN + (1.0 - ladder.MOTORS_CREDIT_MIN) * share
    flown_shown = sorted({_cut(m["designation"]) for m in flown if m["designation"]})
    measured = {"flown": flown_shown, "matched": [wanted[w] for w in found]}
    if credit >= _FULL:
        return credit, measured, None
    flown_text = ", ".join(flown_shown) if flown_shown else "no motor"
    reason = (f"motors: flies {len(found)} of the {len(wanted)} motors the prompt names "
              f"(missing {', '.join(_cut(m) for m in missing)}; flown: {flown_text}): credit {credit:.2f}")
    return credit, measured, reason


def _motor_class_target(letter: str, flown: list[dict]) -> tuple[float, dict, Optional[str]]:
    """1 when the largest flown motor is of the asked class,
    ladder.MOTOR_CLASS_NEAR_CREDIT one letter away, else (also when no flown
    motor has a known impulse) ladder.MOTOR_CLASS_FAR_CREDIT.

    The largest motor is the one with the most total impulse. Its class is the
    letter its impulse gives or the letter it is sold under (some real motors
    are sold one letter off their measured impulse); the closer one counts.
    """
    rated = [m for m in flown if m["impulse_ns"] is not None]
    if not rated:
        credit = ladder.MOTOR_CLASS_FAR_CREDIT
        return credit, {"largest": None, "classes": []}, (
            f"motor class: no flown motor with a known impulse, asked for class {letter} (fly a real motor "
            f"of class {letter}): credit {credit:.2f}")
    largest = max(rated, key=lambda m: m["impulse_ns"])
    classes = sorted({c for c in (impulse_class(largest["impulse_ns"]),
                                  class_from_designation(largest["designation"])) if c})
    steps = min((abs(ord(c) - ord(letter)) for c in classes), default=None)
    credit = (1.0 if steps == 0 else ladder.MOTOR_CLASS_NEAR_CREDIT if steps == 1
              else ladder.MOTOR_CLASS_FAR_CREDIT)
    measured = {"largest": largest["designation"], "impulse_ns": largest["impulse_ns"], "classes": classes}
    if credit >= _FULL:
        return credit, measured, None
    shown = "/".join(classes) if classes else "unknown"
    away = "one letter away" if steps == 1 else (f"{steps} letters away" if steps is not None else "no class")
    return credit, measured, (
        f"motor class: largest motor {_cut(largest['designation'])} ({_figure(largest['impulse_ns'])} Ns) "
        f"is class {shown}, asked for class {letter} ({away}): credit {credit:.2f}")


def _ignition_s(flight: dict) -> float:
    """When the first motor lit (s after the simulation start): the helper's
    ignition_time_s, 0 when it is missing or not a usable number. Time the
    rocket spends waiting on the pad must not count as flight time."""
    v = _reply_number(flight.get("ignition_time_s"))
    return v if v is not None and v > 0 else 0.0


def _measured_value(field: str, reply: dict, flight: dict) -> Optional[float]:
    if field in _TIMED_FIELDS:
        v = _reply_number(flight.get(field))
        return v - _ignition_s(flight) if v is not None else None
    if field in _FLIGHT_FIELDS:
        return _reply_number(flight.get(field))
    if field == "landing_ms":
        return _main_landing_speed(flight)
    if field == "body_diameter_m":
        return _body_diameter(reply)
    if field == "mass_kg":
        return _reply_number(_dict(reply.get("rocket")).get("mass_kg"))
    return None


# ---------------------------------------------------------------------------
# stage 7

def check_targets(reply: dict, requirements: Requirements, root: Node, table: MotorTable) -> StageCheck:
    """Stage 7: how well the flown rocket meets every stated target.

    Always passes; credit is t, the product of the target credits.
    info["targets"] lists every target with its measured value and credit;
    reasons name each target that lost credit and by how much.
    """
    reply = _dict(reply)
    flight = _nominal_flight(reply)
    rows: list[dict[str, Any]] = []
    reasons: list[str] = []
    for field in TARGET_FIELDS:
        target = getattr(requirements, field)
        if target is None:
            continue
        value = _measured_value(field, reply, flight)
        credit, reason = _number_target(field, value, target)
        rows.append({"target": field, "kind": target.kind, "asked": target.value, "tol": target.tol,
                     "measured": value, "credit": credit})
        if reason:
            reasons.append(reason)
    if requirements.motors or requirements.motor_class:
        flown = _flown_motor_list(reply, root, table)
        if requirements.motors:
            credit, measured, reason = _motors_target(requirements.motors, flown)
            rows.append({"target": "motors", "asked": list(requirements.motors), "measured": measured,
                         "credit": credit})
            if reason:
                reasons.append(reason)
        if requirements.motor_class:
            credit, measured, reason = _motor_class_target(requirements.motor_class, flown)
            rows.append({"target": "motor_class", "asked": requirements.motor_class, "measured": measured,
                         "credit": credit})
            if reason:
                reasons.append(reason)
    t = 1.0   # apogee is always stated (records.Requirements), so there is at least one credit
    for r in rows:
        t *= ladder.clamp01(r["credit"])
    t = ladder.clamp01(t)
    info: dict[str, Any] = {"t": t, "targets": rows}
    if not flight:
        info["note"] = "the reply has no nominal flight with numbers"
    return StageCheck("targets", passed=True, credit=t, reasons=reasons, info=info)
