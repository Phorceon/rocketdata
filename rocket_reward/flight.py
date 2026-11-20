"""Stage 6: does the design fly safely in every wind?

The design is flown three times (`flight_plan`): in half, one and one and a
half times the wind the prompt states, with fixed seeds, on a launch rail whose
length follows the impulse class of the largest motor (`rail_length_m`). Each
flight is judged on the safety rules below, with the limits from the "flight
safety (stage 6)" section of limits.py:

  * stable on the pad (judged once, from the rocket, not per flight)
  * the flight did not abort and was not stopped by the step or time cap
  * fast enough off the rail, enough thrust to lift off briskly
  * stable when leaving the rail and while the motors burn
  * every section with a recovery device opens it, nothing opens while a motor
    burns, and the fastest opening is not too fast
  * every section lands, at a safe vertical speed

Stage 6 judges only safety that holds for every rocket. The prompt's own
landing limit is a target like the apogee and is scored in stage 7
(targets.py), so a rocket that lands safely but a little faster than asked
keeps the credit its other targets earn.

A flight's total is the sum of its violation sizes. The worst flight counts:
credit = ladder.credit_from_violations(static violation + worst flight's
violations). The stage passes only when nothing at all is violated.

`check_flight` reads only the simulator's reply (java/PROTOCOL.md) and the
requirements. Any number a rule needs that is missing, null or not a number
counts as ladder.MAX_VIOLATION for that rule, never as a pass, and an odd reply
(wrong types, missing parts) becomes a normal result, never an exception.
"""
from __future__ import annotations

from typing import Any, Optional

from . import ladder
from . import limits as L
from .ladder import is_number
from .motors import MotorTable, _motor_fields, class_from_designation, flown_motors, impulse_class
from .records import Requirements, StageCheck
from .tree import Node

STAGE_KEY = "flight"

# Numbers copied from the nominal flight into info["metrics"] (and so into the
# result's metrics), for logging and for stage 7.
_FLIGHT_METRICS = (
    "wind_ms", "seed", "apogee_m", "max_velocity_ms", "max_accel_ms2", "max_mach",
    "time_to_apogee_s", "flight_time_s", "ground_hit_ms", "rail_exit_ms",
    "stability_rail_cal", "stability_min_burn_cal", "burnout_time_s", "liftoff_twr", "ignition_time_s",
)
_ROCKET_METRICS = ("mass_kg", "dry_mass_kg", "max_diameter_m", "length_m", "stability_cal",
                   "total_impulse_ns", "stage_count")

MAX_REASONS = 12   # reasons after this many are summed up in one line (display only)


# --------------------------------------------------------------------------- plan

def rail_length_m(root: Node, table: MotorTable) -> float:
    """Launch rail length in metres for this design.

    It follows the impulse class of the largest single motor in the flown
    configuration (limits.RAIL_LENGTH_BY_CLASS_M; class L and above get
    limits.RAIL_LENGTH_LARGEST_M), as launch sites do. A motor's impulse comes
    from the motor table; a motor the table does not know (stage 3 stops those
    first) counts by the class letter its designation names. With no class at
    all the shortest rail is used.
    """
    best_ns: Optional[float] = None
    best_letter: Optional[str] = None
    for motor in flown_motors(root):
        written_id, maker, designation, _ = _motor_fields(motor)
        key = table.resolve(written_id, maker, designation)
        if key is not None:
            ns = table.get(key).get("total_impulse_ns")
            if is_number(ns) and ns > 0 and (best_ns is None or ns > best_ns):
                best_ns = float(ns)
            continue
        letter = class_from_designation(designation)
        if letter is not None and (best_letter is None or letter > best_letter):
            best_letter = letter
    letters = [x for x in (impulse_class(best_ns), best_letter) if x]
    if not letters:
        return L.RAIL_LENGTH_BY_CLASS_M[0][1]
    letter = max(letters)
    for upto, metres in L.RAIL_LENGTH_BY_CLASS_M:
        if letter <= upto:
            return metres
    return L.RAIL_LENGTH_LARGEST_M


def flight_plan(requirements: Requirements) -> list[dict]:
    """The three flights every design flies: limits.WIND_FACTORS times the
    prompt's wind (each capped at limits.WIND_MAX_MS), with limits.FLIGHT_SEEDS.
    A stated wind of 0 m/s flies all three in still air."""
    wind = float(requirements.wind_ms)
    return [{"wind_ms": min(L.WIND_MAX_MS, wind * f), "seed": s}
            for f, s in zip(L.WIND_FACTORS, L.FLIGHT_SEEDS)]


# --------------------------------------------------------------------------- helpers

def _field_number(d: Any, key: str) -> Optional[float]:
    """d[key] as a float when it is a finite number, else None."""
    if not isinstance(d, dict):
        return None
    v = d.get(key)
    return float(v) if is_number(v) else None


def _value_text(value: float, limit: float) -> str:
    """The value with enough decimals (1 to 4) that it does not print as the limit."""
    for digits in range(1, 5):
        text = f"{value:.{digits}f}"
        if float(text) != limit:
            return text
    return f"{value:.4f}"


def _wind_words(wind: Optional[float]) -> str:
    if wind is None:
        return "in an unknown wind"
    if wind == 0:
        return "in still air"
    return f"in {wind:.1f} m/s wind"


def _stability_violation(value: Optional[float], limit: float) -> float:
    """Size of a broken "stability above `limit` cal" rule.

    The limits are 0 cal, so the log formula cannot be used. The size is the
    shortfall (limit - value) in calibres plus ladder.STABILITY_ZERO_STEP, so a
    value exactly at the limit (a neutrally stable rocket) fails, capped at
    ladder.MAX_VIOLATION. A missing value counts as MAX_VIOLATION.
    """
    if value is None:
        return ladder.MAX_VIOLATION
    if value > limit:
        return 0.0
    return min(ladder.MAX_VIOLATION, (limit - value) + ladder.STABILITY_ZERO_STEP)


class _Flight:
    """The violations found on one flight: (rule, size, reason) triples."""

    def __init__(self, wind: Optional[float]) -> None:
        self.wind = wind
        self.where = _wind_words(wind)
        self.items: list[tuple[str, float, str]] = []

    def add(self, rule: str, size: float, reason: str) -> None:
        if size > 0:
            self.items.append((rule, float(size), reason))

    @property
    def total(self) -> float:
        return sum(min(ladder.MAX_VIOLATION, s) for _, s, _ in self.items)


def _section_label(branch: dict, position: int) -> str:
    name = branch.get("name")
    if isinstance(name, str) and name.strip():
        text = name.strip()[:40]
        return f"section {position} ('{text}')"
    return f"section {position}"


# --------------------------------------------------------------------------- rules

def _judge_flight(flight: Any, planned_wind: Optional[float]) -> _Flight:
    """Every per-flight rule on one flight of the reply."""
    f = flight if isinstance(flight, dict) else {}
    wind = _field_number(f, "wind_ms")
    out = _Flight(wind if wind is not None else planned_wind)
    w = out.where

    # Did it fly to the end?
    if f.get("ok") is not True:
        out.add("no_flight", ladder.NO_FLIGHT_VIOLATION,
                f"{w} the simulator could not fly the rocket at all, so nothing about this flight is known")
    else:
        abort = f.get("abort")
        if abort is not None:
            text = str(abort).strip()[:120] or "no reason given"
            out.add("no_flight", ladder.NO_FLIGHT_VIOLATION,
                    f"{w} the simulator stopped the flight early ({text}); the rocket must fly from launch to landing")
        elif f.get("hit_step_cap") is True or f.get("hit_time_cap") is True:
            out.add("no_flight", ladder.NO_FLIGHT_VIOLATION,
                    f"{w} the flight was still going after {L.MAX_SIM_TIME_S:g} s or {L.MAX_SIM_STEPS} steps "
                    f"and was stopped; the rocket must land well before that")

    # Off the rail.
    v = _field_number(f, "rail_exit_ms")
    size = ladder.under_limit(v, L.RAIL_EXIT_MIN_MS)
    out.add("rail_exit", size,
            f"{w} the rail-exit speed is unknown; it must be at least {L.RAIL_EXIT_MIN_MS:g} m/s" if v is None else
            f"{w} the rocket leaves the rail at {_value_text(v, L.RAIL_EXIT_MIN_MS)} m/s; it needs at least "
            f"{L.RAIL_EXIT_MIN_MS:g} m/s (use a motor with more initial thrust or a lighter rocket)")
    v = _field_number(f, "liftoff_twr")
    size = ladder.under_limit(v, L.THRUST_TO_WEIGHT_MIN)
    out.add("thrust_to_weight", size,
            f"{w} the liftoff thrust-to-weight ratio is unknown; it must be at least {L.THRUST_TO_WEIGHT_MIN:g}"
            if v is None else
            f"{w} the liftoff thrust-to-weight ratio is {_value_text(v, L.THRUST_TO_WEIGHT_MIN)}; it needs at least "
            f"{L.THRUST_TO_WEIGHT_MIN:g} (more thrust or less mass)")

    # Stability in flight.
    v = _field_number(f, "stability_rail_cal")
    size = _stability_violation(v, L.RAIL_STABILITY_MIN_CAL)
    out.add("rail_stability", size,
            f"{w} the stability margin when leaving the rail is unknown; it must be above "
            f"{L.RAIL_STABILITY_MIN_CAL:g} cal" if v is None else
            f"{w} the stability margin when leaving the rail is {v:.2f} cal, "
            f"{L.RAIL_STABILITY_MIN_CAL - v:.2f} cal short of the limit; it must be above "
            f"{L.RAIL_STABILITY_MIN_CAL:g} cal (move mass forward or enlarge the fins)")
    v = _field_number(f, "stability_min_burn_cal")
    size = _stability_violation(v, L.BURN_STABILITY_MIN_CAL)
    out.add("burn_stability", size,
            f"{w} the lowest stability margin while the motors burn is unknown; it must stay above "
            f"{L.BURN_STABILITY_MIN_CAL:g} cal" if v is None else
            f"{w} the stability margin falls to {v:.2f} cal between leaving the rail and the last burnout, "
            f"{L.BURN_STABILITY_MIN_CAL - v:.2f} cal short of the limit; it must stay above "
            f"{L.BURN_STABILITY_MIN_CAL:g} cal (move mass forward, enlarge the fins, or shorten a coast "
            f"before an upper stage lights)")

    _judge_sections(f, out)
    return out


def _judge_sections(f: dict, out: _Flight) -> None:
    """Recovery and landing rules, per section (branch) of one flight."""
    w = out.where
    branches = f.get("branches")
    if not isinstance(branches, list) or not branches:
        out.add("sections", ladder.MAX_VIOLATION,
                f"{w} the simulator reported no flying sections, so recovery and landing cannot be judged")
        return

    burn_flags: list[Any] = []      # deploy_during_burn of every section that opened something
    deploy_speeds: list[tuple[Optional[float], str]] = []
    for position, b in enumerate(branches):
        if not isinstance(b, dict):
            out.add(f"section_{position}", ladder.MAX_VIOLATION,
                    f"{w} the simulator reported section {position} without any numbers")
            continue
        name = _section_label(b, position)
        index = b.get("index")
        is_main = index == 0 if is_number(index) else position == 0
        rec = b.get("has_recovery")
        if not isinstance(rec, bool):
            out.add(f"recovery_known_{position}", ladder.MAX_VIOLATION,
                    f"{w} the simulator did not say whether {name} has a recovery device")
            rec = True   # judge it on the stricter limits
        deployed = b.get("deployed") is True
        if rec and not deployed:
            out.add(f"deploys_{position}", ladder.YES_NO_VIOLATION,
                    f"{w} the recovery device of {name} never opens; check its deployment event and "
                    f"ejection delay")
        if deployed:
            burn_flags.append(b.get("deploy_during_burn"))
            deploy_speeds.append((_field_number(b, "deploy_speed_ms"), name))

        # Landing.
        if b.get("landed") is not True:
            out.add(f"lands_{position}", ladder.NO_FLIGHT_VIOLATION,
                    f"{w} {name} never reaches the ground in the simulation")
            continue   # its landing speed does not exist; landing is already charged
        v = _field_number(b, "landing_vertical_ms")
        unknown = "is unknown"
        if v is not None and v <= 0:
            # Downward and positive by the protocol: a landed section that is not
            # moving down is an odd reply (the helper reads the touchdown sample, so
            # this should not happen; an older helper read the last sample, which can
            # come after the touchdown), so the speed counts as unknown, the largest
            # violation, never as a soft landing.
            unknown = f"is unknown (the simulator reported {v:.3g} m/s, which is not a downward speed)"
            v = None
        if rec or is_main:
            # A recovered section, and the main section in any case (it carries the
            # nose and payload; only spent boosters may come down without recovery).
            limit = L.LANDING_HARD_MAX_MS
            size = ladder.over_limit(v, limit)
            out.add(f"landing_hard_{position}", size,
                    f"{w} the landing speed of {name} {unknown}; it must be at most {limit:g} m/s"
                    if v is None else
                    f"{w} {name} lands at {_value_text(v, limit)} m/s vertical speed; any section with a recovery "
                    f"device must land at {limit:g} m/s or slower (use a larger parachute)")
        else:
            limit = L.UNRECOVERED_LANDING_MAX_MS
            size = ladder.over_limit(v, limit)
            out.add(f"landing_unrecovered_{position}", size,
                    f"{w} the landing speed of {name} {unknown}; it must be at most {limit:g} m/s"
                    if v is None else
                    f"{w} {name} has no recovery device and hits the ground at {_value_text(v, limit)} m/s; a "
                    f"section without recovery must come down at {limit:g} m/s or slower (give it a "
                    f"streamer or parachute, or make it tumble instead of falling nose-first)")

    # Recovery timing, once per flight over every section that opened something.
    if any(flag is True for flag in burn_flags):
        out.add("deploy_during_burn", ladder.YES_NO_VIOLATION,
                f"{w} a recovery device opens while a motor is still burning; delay the deployment "
                f"until after the last burnout")
    elif any(not isinstance(flag, bool) for flag in burn_flags):
        out.add("deploy_during_burn", ladder.MAX_VIOLATION,
                f"{w} the simulator did not say whether a recovery device opened during a burn")
    if deploy_speeds:
        known = [s for s, _ in deploy_speeds if s is not None]
        if len(known) < len(deploy_speeds):
            out.add("deploy_speed", ladder.MAX_VIOLATION,
                    f"{w} the speed at which a recovery device opens is unknown; it must be at most "
                    f"{L.DEPLOY_SPEED_MAX_MS:g} m/s")
        else:
            fastest, name = max(deploy_speeds, key=lambda p: p[0])  # type: ignore[arg-type, return-value]
            limit = L.DEPLOY_SPEED_MAX_MS
            size = ladder.over_limit(fastest, limit)
            out.add("deploy_speed", size,
                    f"{w} a recovery device of {name} opens at {_value_text(fastest, limit)} m/s; it must open at "
                    f"{limit:g} m/s or slower (open nearer apogee: adjust the ejection delay)")


def _pad_stability(reply: dict) -> tuple[float, Optional[str], Optional[float]]:
    """Stability on the pad, judged once: (size, reason or None, value)."""
    rocket = reply.get("rocket")
    v = _field_number(rocket, "stability_cal")
    limit = L.STATIC_STABILITY_MIN_CAL
    size = ladder.under_limit(v, limit)
    if size == 0:
        return 0.0, None, v
    if v is None:
        return size, f"the rocket's stability margin on the pad is unknown; it must be at least {limit:g} cal", v
    return size, (f"on the pad the rocket's stability margin is {_value_text(v, limit)} cal; it needs at least "
                  f"{limit:g} cal (move mass forward or enlarge the fins)"), v


def _nominal_metrics(reply: dict, flight: Any) -> dict[str, Any]:
    """Numbers of the nominal flight worth logging, and that stage 7 reads."""
    out: dict[str, Any] = {}
    f = flight if isinstance(flight, dict) else {}
    for key in _FLIGHT_METRICS:
        v = f.get(key)
        if is_number(v):
            out[key] = v
    branches = f.get("branches")
    if isinstance(branches, list):
        main = next((b for b in branches if isinstance(b, dict) and b.get("index") == 0),
                    branches[0] if branches and isinstance(branches[0], dict) else None)
        if isinstance(main, dict):
            for src, dst in (("landing_vertical_ms", "landing_ms"), ("landing_total_ms", "landing_total_ms"),
                             ("deploy_speed_ms", "deploy_speed_ms")):
                v = main.get(src)
                if is_number(v):
                    out[dst] = v
    rocket = reply.get("rocket")
    if isinstance(rocket, dict):
        for key in _ROCKET_METRICS:
            v = rocket.get(key)
            if is_number(v):
                out[key] = v
    return out


def nominal_metrics(reply: Any) -> dict[str, Any]:
    """The nominal (1x-wind) flight's numbers and the rocket's, from any reply;
    {} when the reply has none. scoring.py uses it for Result.metrics when the
    ladder stops before stage 6."""
    rep = reply if isinstance(reply, dict) else {}
    if rep.get("ok") is not True:
        return {}
    flights = rep.get("flights")
    nominal = flights[L.NOMINAL_FLIGHT] if isinstance(flights, list) and L.NOMINAL_FLIGHT < len(flights) else {}
    return _nominal_metrics(rep, nominal)


# --------------------------------------------------------------------------- stage 6

def check_flight(reply: dict, requirements: Requirements) -> StageCheck:
    """Stage 6 on one simulator reply (java/PROTOCOL.md) of the flights in
    `flight_plan(requirements)`.

    info carries: "metrics" (the nominal flight's numbers), "worst_flight"
    (its index in the plan), "flight_violations" (per flight, a list of
    {"rule", "size"}), "flight_totals", "static_violation" and "winds_ms".
    """
    rep = reply if isinstance(reply, dict) else {}
    plan = flight_plan(requirements)
    flights = rep.get("flights")
    flights = list(flights) if isinstance(flights, list) else []
    # A flight the reply leaves out counts as one that never flew.
    count = max(len(plan), len(flights))
    flights += [{}] * (count - len(flights))
    planned = [p["wind_ms"] for p in plan] + [None] * (count - len(plan))

    judged = [_judge_flight(f, w) for f, w in zip(flights, planned)]
    static_size, static_reason, static_value = _pad_stability(rep)

    totals = [j.total for j in judged]
    worst = max(range(count), key=lambda i: (totals[i], -i))   # the first of equally bad flights
    credit = ladder.credit_from_violations([static_size] + [s for _, s, _ in judged[worst].items])
    passed = static_size == 0 and all(t == 0 for t in totals)

    # One reason per broken rule: the flight where it is worst, largest first.
    by_rule: dict[str, tuple[float, str]] = {}
    for j in judged:
        for rule, size, reason in j.items:
            if rule not in by_rule or size > by_rule[rule][0]:
                by_rule[rule] = (size, reason)
    ordered = sorted(by_rule.values(), key=lambda p: -p[0])
    reasons = ([static_reason] if static_reason else []) + [r for _, r in ordered]
    if len(reasons) > MAX_REASONS:
        extra = len(reasons) - MAX_REASONS
        reasons = reasons[:MAX_REASONS] + [f"... and {extra} more flight problems"]

    nominal = flights[L.NOMINAL_FLIGHT] if L.NOMINAL_FLIGHT < len(flights) else {}
    info: dict[str, Any] = {
        "metrics": _nominal_metrics(rep, nominal),
        "worst_flight": worst,
        "flight_totals": [round(t, 6) for t in totals],
        "flight_violations": [[{"rule": r, "size": round(s, 6)} for r, s, _ in j.items] for j in judged],
        "static_violation": round(static_size, 6),
        "static_stability_cal": static_value,
        "winds_ms": [j.wind for j in judged],
    }
    return StageCheck(stage=STAGE_KEY, passed=passed, credit=credit if not passed else 1.0,
                      reasons=reasons if not passed else [], info=info)
