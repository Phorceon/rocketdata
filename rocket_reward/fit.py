"""Stage 5: build. OpenRocket must build the design, and its parts must fit.

The cleaned design is loaded by OpenRocket itself (sim.py). This module reads
OpenRocket's reply: whether it could build and fly the rocket, which warnings
it gave while reading the file, and where it placed every part
(java/PROTOCOL.md, "components"). The fit rules are judged on those positions,
never on our own copy of OpenRocket's placement rules:

* the outer shell is in one piece (no big radius step between neighbouring
  nose cones, body tubes and transitions)
* fins sit on the part that holds them
* inside parts fit inside the airframe (a frame with no room inside is judged
  by its outer radius), and every inside part lies inside it along the axis
  (a pod's parts inside the pod's shell), judged as a distance
* the motor fits its mount, does not hang far out of it, and fires out of the
  back of its stage, not into the airframe
* pods and side boosters are no wider than the main body and have a nose cone
  or transition at the front
* no two fin sets, and no two rings, take the same place
* every motor the design gives is still there after loading

The cleaned design holds no override settings (clean.py removes them), so the
masses and balance points in the reply are the ones OpenRocket computes from
the parts and materials.

Every limit is in limits.py, section "fit (stage 5)", with the measurement it
came from (flight statistics report, section 5). A violation smaller than
ladder.FIT_DEFECT_BELOW is a defect (it does not stop the ladder); a larger
one fails the stage, with credit 1 / (1 + sum of failure sizes). A design that
OpenRocket cannot read, build or fly gets credit 0.

The reply comes from another program and the design from a language model, so
nothing here trusts either: missing fields, nulls, wrong types and odd part
links skip the measurement that needs them, and a reply that cannot be judged
at all is a normal failing result.
"""
from __future__ import annotations

import math
from typing import Any, Optional

from . import limits as L
from .ladder import (FIT_DEFECT_BELOW, MAX_VIOLATION, YES_NO_VIOLATION, credit_from_violations, is_number,
                     over_limit, under_limit)
from .limit_checks import _fmt
from .motors import flown_config_id, mount_motors
from .records import StageCheck
from .tree import Node, attr_of

STAGE = "build"
MAX_REASONS = 12          # failure reasons listed in full; the rest are counted in one line
MAX_DEFECTS = 12          # defects listed; ten already take the largest defect cost (ladder.MAX_DEFECT_COST)
MAX_FINDINGS_KEPT = 60    # info["findings"] keeps this many entries; info["violations"] has the total
MAX_COMPONENTS = 5000     # parts read from one reply (the largest reference design has a few dozen)
MAX_FINS_PER_SET = 64     # fin angles compared per fin set (stage 4 already fails more than 8 fins)
MAX_TEXT_CHARS = 200      # simulator texts are cut to this length inside reasons
LENGTH_SLACK_M = 1e-9     # rounding noise in OpenRocket's positions; smaller overlaps are no overlap

# Load warnings that change nothing about the rocket that flies. OpenRocket
# gave no load warning at all on any of the 183 sound reference designs
# (flight statistics report, section 6); the only warnings seen were on the
# six references whose motor OpenRocket replaces (those are build faults
# already) and "Unsupported document version 1.11" on one of them, which the
# cleaning now prevents by writing version 1.10. So no warning is known to be
# harmless, and every warning OpenRocket gives counts as something it skipped
# or changed. Add a text here (it is matched at the start of the warning) only
# after checking that the warned-about thing does not change the flight.
HARMLESS_LOAD_WARNINGS: tuple[str, ...] = ()

SHELL_TYPES = ("NoseCone", "BodyTube", "Transition")
STAGE_TYPES = ("AxialStage",)
POD_TYPES = ("ParallelStage", "PodSet")
FIN_SET_TYPES = ("TrapezoidFinSet", "EllipticalFinSet", "FreeformFinSet", "TubeFinSet")
RING_TYPES = ("CenteringRing", "Bulkhead", "EngineBlock")
RIGID_INSIDE_TYPES = RING_TYPES + ("InnerTube", "TubeCoupler")
SOFT_INSIDE_TYPES = ("Parachute", "Streamer", "ShockCord", "MassComponent")
RAIL_GUIDE_TYPES = ("LaunchLug", "RailButton")

_PLAIN = {
    "NoseCone": "nose cone", "BodyTube": "body tube", "Transition": "transition",
    "InnerTube": "inner tube", "TubeCoupler": "tube coupler", "CenteringRing": "centering ring",
    "Bulkhead": "bulkhead", "EngineBlock": "engine block", "MassComponent": "mass component",
    "Parachute": "parachute", "Streamer": "streamer", "ShockCord": "shock cord",
    "TrapezoidFinSet": "fin set", "EllipticalFinSet": "fin set", "FreeformFinSet": "fin set",
    "TubeFinSet": "tube fin set", "AxialStage": "stage", "ParallelStage": "booster set", "PodSet": "pod set",
}

_ERROR_WORDS = {
    "load": "OpenRocket could not read the design file",
    "build": "OpenRocket read the design file but could not build the rocket",
    "hang": "OpenRocket did not finish loading or flying this design in time",
    "crash": "OpenRocket crashed on this design",
}

# OpenRocket's warning for a value it could not read (java/PROTOCOL.md). It never names the
# value, so the reason adds where to look. Display only: none of this shapes a score.
INVALID_VALUE_WARNING = "Invalid parameter encountered"
INVALID_VALUE_HINT = (" (OpenRocket does not say which value; usually it is a word or NaN where it expects"
                      " a number: write a number there or leave the tag out)")
MAX_WARNINGS_SHOWN = 3


# ------------------------------------------------------------------ reading the reply

def _num(d: Any, key: str) -> Optional[float]:
    """d[key] as a finite float, else None (also when d is not a dict)."""
    if not isinstance(d, dict):
        return None
    v = d.get(key)
    return float(v) if is_number(v) else None


def _short_text(x: Any) -> str:
    """Any value as a short single-line text for a reason."""
    if isinstance(x, str):
        s = x
    elif x is None or isinstance(x, (bool, int, float)):
        try:
            s = repr(x)
        except ValueError:  # an integer with too many digits to print
            s = "a very large number"
    else:
        s = f"a {type(x).__name__}"   # never repr a container: it may be huge or nested very deep
    s = " ".join(s[:4 * MAX_TEXT_CHARS].split())
    return s if len(s) <= MAX_TEXT_CHARS else s[:MAX_TEXT_CHARS - 3] + "..."


def _part(c: dict) -> str:
    """A part as a student would name it: its kind and its name, e.g. body tube 'Main tube'."""
    kind = _PLAIN.get(c.get("type"), _short_text(c.get("type") or "part"))
    name = c.get("name")
    return f"{kind} '{_short_text(name)}'" if isinstance(name, str) and name.strip() else kind


def _end(c: dict) -> Optional[float]:
    """Where a part ends, measured from the nose tip (its front plus its length)."""
    x0 = _num(c, "x0_m")
    if x0 is None:
        return None
    return x0 + (_num(c, "length_m") or 0.0)


def _outer_radius(c: dict) -> Optional[float]:
    """The larger of a part's fore and aft outer radius, or None when neither is given."""
    rs = [r for r in (_num(c, "outer_radius_fore_m"), _num(c, "outer_radius_aft_m")) if r is not None]
    return max(rs) if rs else None


def _airframe_inner(c: dict) -> Optional[float]:
    """Inside radius of a nose cone, body tube or transition; None or 0 when it has no room inside."""
    if c.get("type") == "BodyTube":
        return _num(c, "inner_radius_m")
    if c.get("filled") is True:
        return 0.0
    r = _outer_radius(c)
    return None if r is None else r - (_num(c, "thickness_m") or 0.0)


class _Parts:
    """The parts of one reply, by index, with safe links to their parents."""

    def __init__(self, components: list) -> None:
        self.all: list[dict] = []
        self.by_index: dict[int, dict] = {}
        for c in components[:MAX_COMPONENTS]:
            if not isinstance(c, dict):
                continue
            if not isinstance(c.get("type"), str):
                c = dict(c, type="")   # an odd type matches no rule (and is never used as a key)
            self.all.append(c)
            i = c.get("index")
            if isinstance(i, int) and not isinstance(i, bool) and i not in self.by_index:
                self.by_index[i] = c

    def parent(self, c: dict) -> Optional[dict]:
        p = c.get("parent")
        if isinstance(p, bool) or not isinstance(p, int):
            return None
        found = self.by_index.get(p)
        return None if found is c else found

    def ancestors(self, c: dict):
        """The enclosing parts from the parent outwards. Stops on a loop of links."""
        seen = {id(c)}
        cur = self.parent(c)
        while cur is not None and id(cur) not in seen:
            yield cur
            seen.add(id(cur))
            cur = self.parent(cur)

    def in_pod(self, c: dict) -> bool:
        return any(a.get("type") in POD_TYPES for a in self.ancestors(c))


# ------------------------------------------------------------------ collecting findings

class _Findings:
    """Violations of the fit rules, split into failures and defects."""

    def __init__(self) -> None:
        self.failures: list[float] = []
        self.reasons: list[str] = []
        self.defect_sizes: list[float] = []
        self.defects: list[str] = []
        self.kept: list[dict[str, Any]] = []
        self.count = 0
        self.worst: dict[str, float] = {}   # rule -> worst measured value (also when it holds)

    def measure(self, rule: str, value: float, high_is_bad: bool = True) -> None:
        """Remember the worst value of a rule, for logging and calibration."""
        if not is_number(value):
            return
        cur = self.worst.get(rule)
        if cur is None or (value > cur if high_is_bad else value < cur):
            self.worst[rule] = round(float(value), 6)

    def add(self, rule: str, size: float, reason: str, value: Any = None, limit: Any = None) -> None:
        """One broken rule of `size` (see ladder.py). Small ones become defects."""
        if not (size > 0):
            return
        self.count += 1
        defect = size < FIT_DEFECT_BELOW
        if len(self.kept) < MAX_FINDINGS_KEPT:
            self.kept.append({"rule": rule, "size": round(size, 4), "defect": defect,
                              "value": round(value, 6) if is_number(value) else value,
                              "limit": limit})
        if defect:
            self.defect_sizes.append(size)
            self.defects.append("small fit problem: " + reason)
        else:
            self.failures.append(size)
            self.reasons.append(reason)


def _over(out: _Findings, rule: str, value: float, limit: float, reason: str) -> None:
    out.measure(rule, value)
    if value > limit:
        out.add(rule, over_limit(value, limit), reason, value, limit)


# ------------------------------------------------------------------ the rules

def _check_warnings(reply: dict, out: _Findings) -> int:
    """Every load warning that is not known to be harmless is a yes/no violation."""
    warnings = reply.get("load_warnings")
    if warnings is None:
        return 0
    if not isinstance(warnings, list):
        warnings = [warnings]
    seen: set[str] = set()
    for w in warnings[:MAX_COMPONENTS]:
        text = _short_text(w)
        if text in seen or any(text.startswith(h) for h in HARMLESS_LOAD_WARNINGS):
            continue
        seen.add(text)
        out.add("load_warning", YES_NO_VIOLATION,
                f"OpenRocket skipped or changed something while reading the design: \"{text}\"; "
                f"fix the setting it names so the rocket that flies is the one you wrote")
    return len(seen)


def _check_shell(parts: _Parts, out: _Findings) -> None:
    """Radius steps between neighbouring shell parts, within a stage (or pod) and between stages."""
    chain: list[tuple[dict, int]] = []
    for holder in parts.all:
        htype = holder.get("type")
        if htype not in STAGE_TYPES + POD_TYPES:
            continue
        shells = [c for c in parts.all if c.get("type") in SHELL_TYPES and parts.parent(c) is holder
                  and c.get("active", True) is not False and _num(c, "x0_m") is not None]
        shells.sort(key=lambda c: _num(c, "x0_m"))
        if htype in STAGE_TYPES:
            chain += [(c, id(holder)) for c in shells]
        else:
            for p, n in zip(shells, shells[1:]):
                _shell_pair(p, n, True, out)
    chain.sort(key=lambda t: _num(t[0], "x0_m"))
    for (p, sp), (n, sn) in zip(chain, chain[1:]):
        _shell_pair(p, n, sp == sn, out)


def _shell_pair(p: dict, n: dict, same_stage: bool, out: _Findings) -> None:
    rp = _num(p, "outer_radius_aft_m")
    rn = _num(n, "outer_radius_fore_m")
    if rp is None or rn is None:
        return
    big = max(abs(rp), abs(rn))
    step = abs(rp - rn) / big if big > 0 else 0.0
    if same_stage:
        rule, limit, where = "shell_step", L.SHELL_STEP_MAX_FRACTION, "inside one stage"
    else:
        rule, limit, where = "shell_step_between_stages", L.SHELL_STEP_BETWEEN_STAGES_MAX_FRACTION, \
            "where two stages meet"
    _over(out, rule, step, limit,
          f"the outer radius jumps from {_fmt(rp, 'mm')} at the back of {_part(p)} to {_fmt(rn, 'mm')} "
          f"at the front of {_part(n)} {where}, a step of {step:.0%} of the larger radius; the limit is "
          f"{limit:.0%}: match the radii or put a transition between them")


def _check_fins(parts: _Parts, out: _Findings) -> None:
    """A fin root must not run far past the front or back end of the part that holds it.

    Tube fins have no fin outline in the reply (OpenRocket does not treat them
    as a fin set), so their root is the tubes themselves: they start at the
    part's x0_m and their "root chord" is the tube length."""
    for c in parts.all:
        if c.get("type") not in FIN_SET_TYPES:
            continue
        fins = c.get("fins")
        par = parts.parent(c)
        tube_fins = c.get("type") == "TubeFinSet" and not isinstance(fins, dict)
        chord = _num(c, "length_m") if tube_fins else _num(fins, "root_chord_m")
        if par is None or chord is None or chord <= 0:
            continue
        rx0 = None if tube_fins else _num(fins, "root_x0_m")
        rx0 = rx0 if rx0 is not None else _num(c, "x0_m")
        px0, pend = _num(par, "x0_m"), _end(par)
        if rx0 is None or px0 is None or pend is None:
            continue
        front_m = px0 - rx0
        back_m = rx0 + chord - pend
        # A fin that ends exactly where its part starts must not fail on rounding noise.
        front = max(0.0, front_m - LENGTH_SLACK_M) / chord
        back = max(0.0, back_m - LENGTH_SLACK_M) / chord
        root, unit, s = ("the tubes", "tube length", "") if tube_fins else ("the root", "root chord", "s")
        _over(out, "fin_past_front", front, L.FIN_PAST_FRONT_MAX_CHORDS,
              f"{root} of {_part(c)} start{s} {_fmt(front_m, 'm')} ({front:.2f} {unit}s) ahead of the front "
              f"of {_part(par)} that holds it; the limit is {L.FIN_PAST_FRONT_MAX_CHORDS:g} {unit} "
              f"({_fmt(L.FIN_PAST_FRONT_MAX_CHORDS * chord, 'm')}): move the fins back onto the part")
        _over(out, "fin_past_back", back, L.FIN_PAST_BACK_MAX_CHORDS,
              f"{root} of {_part(c)} run{s} {_fmt(back_m, 'm')} ({back:.2f} {unit}s) past the back end "
              f"of {_part(par)} that holds it; the limit is {L.FIN_PAST_BACK_MAX_CHORDS:g} {unit} "
              f"({_fmt(L.FIN_PAST_BACK_MAX_CHORDS * chord, 'm')}): move the fins forward onto the part")


def _check_inside_radius(parts: _Parts, out: _Findings) -> None:
    """Inside parts must not be wider than the airframe around them (the nearest
    enclosing nose cone, body tube or transition, not the immediate parent).

    A frame with no room inside (solid, "filled", or a wall as thick as its
    radius) still holds what the design puts in it, such as nose weight cast
    into a solid nose cone: such a part is judged against the frame's outer
    radius, with the same limits. It is never skipped, so writing "filled"
    cannot hide an oversized part."""
    for c in parts.all:
        t = c.get("type")
        if t in RIGID_INSIDE_TYPES:
            rule, limit, kind = "rigid_inside_radius", L.RIGID_INSIDE_RADIUS_MAX_RATIO, "rigid"
        elif t in SOFT_INSIDE_TYPES:
            rule, limit, kind = "soft_inside_radius", L.SOFT_INSIDE_RADIUS_MAX_RATIO, "packed"
        else:
            continue
        r = _outer_radius(c)
        if r is None:
            continue
        r += abs(_num(c, "radial_offset_m") or 0.0)
        frame = next((a for a in parts.ancestors(c) if a.get("type") in SHELL_TYPES), None)
        inner = _airframe_inner(frame) if frame is not None else None
        if inner is None:
            continue
        room, what = inner, "inside radius"
        if inner <= 0:
            room, what = _outer_radius(frame), "outer radius (it has no room inside)"
            if room is None or room <= 0:
                continue
        ratio = r / room
        _over(out, rule, ratio, limit,
              f"{_part(c)} reaches {_fmt(r, 'mm')} from the axis, {ratio - 1:.0%} wider than the "
              f"{_fmt(room, 'mm')} {what} of {_part(frame)} around it; a {kind} part may be at most "
              f"{limit - 1:.0%} wider: make it narrower or the airframe wider")


def _pod_of(parts: _Parts, c: dict) -> Optional[dict]:
    """The nearest enclosing pod or side booster of a part, or None for the main body."""
    return next((a for a in parts.ancestors(c) if a.get("type") in POD_TYPES), None)


def _merge(spans: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Stretches along the axis, sorted, with touching ones joined."""
    union: list[tuple[float, float]] = []
    for lo, hi in sorted(spans):
        if union and lo <= union[-1][1] + LENGTH_SLACK_M:
            union[-1] = (union[-1][0], max(union[-1][1], hi))
        else:
            union.append((lo, hi))
    return union


def _shell_union(parts: _Parts, pod: Optional[dict] = None) -> list[tuple[float, float]]:
    """The stretches along the axis that an airframe covers: the main body's
    shells (pod None), or the shells of one pod or side booster."""
    spans = []
    for c in parts.all:
        if c.get("type") in SHELL_TYPES and _pod_of(parts, c) is pod:
            x0, end = _num(c, "x0_m"), _end(c)
            if x0 is not None and end is not None:
                spans.append((min(x0, end), max(x0, end)))
    return _merge(spans)


def _outside_distance(x0: float, end: float, union: list[tuple[float, float]]) -> tuple[float, str]:
    """How far a part from x0 to end lies outside the covered stretches, and where.

    For each covered stretch, how much the part sticks out ahead of its front
    plus how much it sticks out behind its back; the stretch that needs the
    least counts. So a part fully inside measures 0, a ring 2 mm thick placed
    63 m ahead of the nose measures 63 m (not its own 2 mm), and a part in a
    gap between two stretches measures its distance to the nearer one."""
    best, where = math.inf, ""
    for lo, hi in union:
        ahead, behind = max(0.0, lo - x0), max(0.0, end - hi)
        d = ahead + behind
        if d < best:
            best = d
            if lo == union[0][0] and ahead > 0 and behind == 0:
                where = "ahead of the front of"
            elif hi == union[-1][1] and behind > 0 and ahead == 0:
                where = "behind the back of"
            else:
                where = "outside"
    return max(0.0, best - LENGTH_SLACK_M), where


def _check_outside_airframe(parts: _Parts, out: _Findings) -> None:
    """Every inside part must lie inside its airframe: motor tubes, rings,
    bulkheads, engine blocks, tube couplers, mass components, shock cords,
    parachutes and streamers; and the launch lugs and rail buttons on the
    outside must sit along it, not beyond its ends.

    The size of a violation is a distance along the axis (_outside_distance),
    never the part's own length, so a thin part far away is caught. Parts in
    a pod or side booster are judged against that pod's own shells (the main
    body's when the pod has none). A ring, bulkhead, engine block or coupler
    may also sit on the motor tube that holds it where that tube sticks out
    behind the tail (motor retainers); the tube itself has its own limit."""
    unions: dict[int, list[tuple[float, float]]] = {}
    main = _shell_union(parts)
    for c in parts.all:
        t = c.get("type")
        if t == "InnerTube":
            rule, limit, kind = "motor_tube_outside_airframe", L.MOTOR_TUBE_BEHIND_TAIL_MAX_M, "a motor tube"
        elif t in RING_TYPES or t == "TubeCoupler":
            rule, limit, kind = "ring_outside_airframe", L.RING_OUTSIDE_AIRFRAME_MAX_M, "a rigid inside part"
        elif t in SOFT_INSIDE_TYPES:
            rule, limit, kind = "part_outside_airframe", L.PACKED_OUTSIDE_AIRFRAME_MAX_M, "a packed inside part"
        elif t in RAIL_GUIDE_TYPES:
            rule, limit, kind = "part_outside_airframe", L.PACKED_OUTSIDE_AIRFRAME_MAX_M, "a launch lug or rail button"
        else:
            continue
        x0 = _num(c, "x0_m")
        if x0 is None:
            continue
        length = max(0.0, _num(c, "length_m") or 0.0)
        pod = _pod_of(parts, c)
        if pod is None:
            union = main
        else:
            if id(pod) not in unions:
                unions[id(pod)] = _shell_union(parts, pod) or main
            union = unions[id(pod)]
        if not union:
            continue
        if kind == "a rigid inside part":
            tubes = [(_num(a, "x0_m"), _end(a)) for a in parts.ancestors(c) if a.get("type") == "InnerTube"]
            union = _merge(union + [(lo, hi) for lo, hi in tubes if lo is not None and hi is not None])
        outside, where = _outside_distance(x0, x0 + length, union)
        frame = "its pod's shell" if pod is not None and unions.get(id(pod)) is not main else "the airframe"
        _over(out, rule, outside, limit,
              f"{_part(c)} lies {_fmt(outside, 'm')} {where} {frame} (it is {_fmt(length, 'm')} long); "
              f"{kind} may lie at most {_fmt(limit, 'm')} outside it: move it "
              + ("onto a body tube" if t in RAIL_GUIDE_TYPES else "inside a body tube"))


def _check_motor_fit(parts: _Parts, out: _Findings) -> int:
    """The motor must fit its mount and not hang far out behind it. Returns how many mounts hold a motor."""
    loaded = 0
    for c in parts.all:
        mo = c.get("motor")
        if not isinstance(mo, dict):
            continue
        loaded += 1
        what = f"motor '{_short_text(mo.get('designation'))}'" if mo.get("designation") else "the motor"
        dia, inner = _num(mo, "diameter_m"), _num(c, "inner_radius_m")
        if dia is not None and dia > 0 and inner is not None:
            if inner > 0:
                ratio = dia / (2 * inner)
                _over(out, "motor_diameter", ratio, L.MOTOR_DIAMETER_MAX_RATIO,
                      f"{what} is {_fmt(dia, 'mm')} wide but the inside of its mount {_part(c)} is "
                      f"{_fmt(2 * inner, 'mm')}, {ratio:.2f} times; the limit is "
                      f"{L.MOTOR_DIAMETER_MAX_RATIO:g} times: use a mount that matches the motor")
            else:
                out.add("motor_diameter", MAX_VIOLATION,
                        f"{what} is {_fmt(dia, 'mm')} wide but its mount {_part(c)} has no room inside; "
                        f"give the mount an inside diameter that matches the motor", None,
                        L.MOTOR_DIAMETER_MAX_RATIO)
        length, hang = _num(mo, "length_m"), _num(mo, "overhang_m")
        if length is not None and length > 0 and hang is not None:
            share = max(0.0, hang) / length
            _over(out, "motor_overhang", share, L.MOTOR_OVERHANG_MAX_FRACTION,
                  f"{what} hangs {_fmt(hang, 'm')} out behind its mount {_part(c)}, {share:.0%} of its "
                  f"{_fmt(length, 'm')} length; the limit is {L.MOTOR_OVERHANG_MAX_FRACTION:.0%}: "
                  f"make the mount longer or move the motor forward")
    return loaded


def _stage_of(parts: _Parts, c: dict) -> Optional[dict]:
    """The nearest enclosing stage (AxialStage) of a part, or None."""
    return next((a for a in parts.ancestors(c) if a.get("type") in STAGE_TYPES), None)


def _check_motor_position(parts: _Parts, out: _Findings) -> None:
    """A motor must fire out of the back of its stage, not into the airframe:
    its back end may sit at most limits.MOTOR_AHEAD_OF_TAIL_MAX_M ahead of the
    back end of the main-airframe shells of its stage. Motors in pods and side
    boosters are left out (they have their own tails).

    The tail must also be open: the aft radius of the stage's last shell is
    at least limits.TAIL_RADIUS_PER_MOTOR_MIN times the motor's radius, so a
    tail closed to a point cannot hide the motor behind a sharp boat tail."""
    tails: dict[int, Optional[float]] = {}
    tail_radius: dict[int, Optional[tuple[float, dict]]] = {}
    for c in parts.all:
        mo = c.get("motor")
        if not isinstance(mo, dict) or parts.in_pod(c):
            continue
        stage = _stage_of(parts, c)
        if stage is None:
            continue
        if id(stage) not in tails:
            ends = [_end(s) for s in parts.all if s.get("type") in SHELL_TYPES and not parts.in_pod(s)
                    and s.get("active", True) is not False and _stage_of(parts, s) is stage]
            ends = [e for e in ends if e is not None]
            tails[id(stage)] = max(ends) if ends else None
            last = max((s for s in parts.all if s.get("type") in SHELL_TYPES and not parts.in_pod(s)
                        and s.get("active", True) is not False and _stage_of(parts, s) is stage
                        and _end(s) is not None), key=_end, default=None)
            ra = _num(last, "outer_radius_aft_m") if last is not None else None
            tail_radius[id(stage)] = (ra, last) if ra is not None else None
        tail = tails[id(stage)]
        dia = _num(mo, "diameter_m")
        tr = tail_radius[id(stage)]
        if tr is not None and dia is not None and dia > 0:
            ratio = max(0.0, tr[0]) / (dia / 2)
            out.measure("tail_radius_per_motor", ratio, high_is_bad=False)
            if ratio < L.TAIL_RADIUS_PER_MOTOR_MIN:
                what = f"motor '{_short_text(mo.get('designation'))}'" if mo.get("designation") else "the motor"
                out.add("tail_closed", under_limit(ratio, L.TAIL_RADIUS_PER_MOTOR_MIN),
                        f"the back of {_part(tr[1])} is {_fmt(tr[0], 'mm')} in radius, {ratio:.2f} times the "
                        f"{_fmt(dia / 2, 'mm')} radius of {what} that fires out of it; the limit is "
                        f"{L.TAIL_RADIUS_PER_MOTOR_MIN:g} times: open the tail so the motor can fire out of it",
                        ratio, L.TAIL_RADIUS_PER_MOTOR_MIN)
        x0, length = _num(mo, "x0_m"), _num(mo, "length_m")
        if tail is None or x0 is None or length is None or length <= 0:
            continue
        gap = tail - (x0 + length)
        what = f"motor '{_short_text(mo.get('designation'))}'" if mo.get("designation") else "the motor"
        _over(out, "motor_ahead_of_tail", gap, L.MOTOR_AHEAD_OF_TAIL_MAX_M,
              f"the back end of {what} in {_part(c)} sits {_fmt(gap, 'm')} ahead of the back end of "
              f"the airframe of {_part(stage)}, so it fires into the rocket; the limit is "
              f"{_fmt(L.MOTOR_AHEAD_OF_TAIL_MAX_M, 'm')}: move the motor mount back to the tail")


def _check_pods(parts: _Parts, out: _Findings) -> None:
    """Pods and side boosters: no shell wider than the main body, and each
    pod's front is a nose cone or transition, not an open tube."""
    main = [r for r in (_outer_radius(c) for c in parts.all
                        if c.get("type") in SHELL_TYPES and not parts.in_pod(c)) if r is not None]
    body = max(main) if main else None
    for pod in parts.all:
        if pod.get("type") not in POD_TYPES:
            continue
        shells = [c for c in parts.all if c.get("type") in SHELL_TYPES and c.get("active", True) is not False
                  and next((a for a in parts.ancestors(c) if a.get("type") in POD_TYPES), None) is pod]
        if body is not None and body > 0:
            widest = max(shells, key=lambda c: _outer_radius(c) or 0.0, default=None)
            r = _outer_radius(widest) if widest is not None else None
            if r is not None:
                ratio = r / body
                _over(out, "pod_width", ratio, L.POD_RADIUS_PER_BODY_MAX,
                      f"{_part(widest)} in {_part(pod)} is {_fmt(r, 'mm')} in radius, {ratio:.2f} times the "
                      f"main body's {_fmt(body, 'mm')}; the limit is {L.POD_RADIUS_PER_BODY_MAX:g} times: "
                      f"make the pod narrower than the body")
        real = [c for c in shells if (_num(c, "length_m") or 0.0) > 0 and (_outer_radius(c) or 0.0) > 0
                and _num(c, "x0_m") is not None]
        if real:
            front = min(real, key=lambda c: _num(c, "x0_m"))
            if front.get("type") == "BodyTube":
                out.add("pod_open_front", YES_NO_VIOLATION,
                        f"{_part(pod)} starts with an open {_part(front)} ({_fmt(_outer_radius(front) or 0.0, 'mm')} "
                        f"in radius); put a nose cone or transition at the front of every pod or booster",
                        None, None)


def _fin_angles(c: dict) -> list[float]:
    """Angles (degrees, 0-360) of the fins of one fin set around the body."""
    fins = c.get("fins") if isinstance(c.get("fins"), dict) else {}
    count = _num(fins, "count")
    if count is None:
        count = _num(c, "instances")
    n = int(min(MAX_FINS_PER_SET, max(1.0, count))) if count is not None else 1
    base = _num(fins, "base_rotation_deg") or 0.0
    return [(base + k * 360.0 / n) % 360.0 for k in range(n)]


def _worst_match(these: list[float], others: list[float]) -> float:
    """For the fin of `these` that is furthest from every fin of `others`, that
    distance in degrees. Below FIN_SETS_SAME_ANGLE_DEG, every fin of `these`
    has a twin in `others`: the set is the same fins twice. One shared angle
    alone (a 3-fin and a 4-fin set both starting at 0 degrees) is not."""
    return max(min(min(abs(a - b), 360.0 - abs(a - b)) for b in others) for a in these)


def _overlap(p: dict, n: dict) -> Optional[float]:
    """How far two parts overlap along the axis (metres; 0 or less: they do not)."""
    pe, ne = _end(p), _end(n)
    px, nx = _num(p, "x0_m"), _num(n, "x0_m")
    if None in (pe, ne, px, nx):
        return None
    return min(pe, ne) - max(px, nx)


def _by_parent(parts: _Parts, types: tuple[str, ...]) -> list[list[dict]]:
    groups: dict[int, list[dict]] = {}
    for c in parts.all:
        if c.get("type") in types:
            p = parts.parent(c)
            if p is not None:
                groups.setdefault(id(p), []).append(c)
    return [g for g in groups.values() if len(g) > 1]


def _check_doubles(parts: _Parts, out: _Findings) -> None:
    """Two fin sets on one part at the same angle, or two rings pushed into each other."""
    for group in _by_parent(parts, FIN_SET_TYPES):
        for i, p in enumerate(group):
            for n in group[i + 1:]:
                ov = _overlap(p, n)
                if ov is None or ov <= LENGTH_SLACK_M:
                    continue
                ap, an = _fin_angles(p), _fin_angles(n)
                gap = min(_worst_match(ap, an), _worst_match(an, ap))
                out.measure("fin_sets_angle_gap", gap, high_is_bad=False)
                if gap < L.FIN_SETS_SAME_ANGLE_DEG:
                    out.add("fin_sets_same_angle", under_limit(gap, L.FIN_SETS_SAME_ANGLE_DEG),
                            f"{_part(p)} and {_part(n)} on {_part(parts.parent(p) or {})} overlap for "
                            f"{_fmt(ov, 'm')} along the body and every fin of one sits within {gap:.2g} degrees "
                            f"of a fin of the other, so they are the same fins twice; the sets need at least "
                            f"{L.FIN_SETS_SAME_ANGLE_DEG:g} degrees between their fins: remove one set or turn it",
                            gap, L.FIN_SETS_SAME_ANGLE_DEG)
    for group in _by_parent(parts, RING_TYPES):
        for i, p in enumerate(group):
            for n in group[i + 1:]:
                ov = _overlap(p, n)
                if ov is None or ov <= LENGTH_SLACK_M:
                    continue
                _over(out, "rings_overlap", ov, L.RING_OVERLAP_MAX_M,
                      f"{_part(p)} and {_part(n)} are pushed {_fmt(ov, 'm')} into each other; the limit is "
                      f"{_fmt(L.RING_OVERLAP_MAX_M, 'm')}: move one of them")


def _expected_motor_mounts(root: Any) -> int:
    """How many tubes of the design hold a motor of the flown configuration."""
    cid = flown_config_id(root)
    if cid is None:
        return 0
    return len({id(mount) for mount, motor in mount_motors(root) if attr_of(motor, "configid") == cid})


def _check_motor_present(root: Node, loaded: int, out: _Findings) -> int:
    """Every motor the design gives must still be there after OpenRocket loaded it."""
    expected = _expected_motor_mounts(root)
    if loaded == 0 and expected == 0:
        out.add("motor_missing", YES_NO_VIOLATION,
                "OpenRocket loaded no motor at all; put a motor of the flown configuration inside the motor "
                "mount of a body tube or inner tube")
        return expected
    missing = max(expected - loaded, 0)
    for _ in range(missing):  # one yes/no violation per missing motor
        out.add("motor_missing", YES_NO_VIOLATION,
                f"the design puts a motor in {expected} mount(s) of the flown configuration, but OpenRocket "
                f"loaded only {loaded} motor(s), so {missing} motor(s) went missing: put every motor inside the "
                f"motor mount of a body tube or inner tube that OpenRocket keeps")
    return expected


# ------------------------------------------------------------------ stage 5

def _broken(reason: str, info: dict[str, Any]) -> StageCheck:
    return StageCheck(STAGE, False, credit=0.0, reasons=[reason], info=info)


def _not_built(reply: Any) -> Optional[str]:
    """Why OpenRocket could not build or fly the design at all, or None when it could."""
    if not isinstance(reply, dict):
        return "the simulator gave no reply for this design"
    if reply.get("ok") is not True:
        kind = reply.get("error_kind")
        words = _ERROR_WORDS.get(kind, "OpenRocket could not build this design") if isinstance(kind, str) \
            else "OpenRocket could not build this design"
        msg = reply.get("message")
        text = f"{words}: {_short_text(msg)}" if msg else words
        if isinstance(msg, str) and INVALID_VALUE_WARNING in msg:
            text += INVALID_VALUE_HINT
            others = [w for w in reply.get("load_warnings") or []
                      if isinstance(w, str) and INVALID_VALUE_WARNING not in w]
            if others:
                shown = "; ".join(f'"{_short_text(w)}"' for w in others[:MAX_WARNINGS_SHOWN])
                more = f" and {len(others) - MAX_WARNINGS_SHOWN} more" if len(others) > MAX_WARNINGS_SHOWN else ""
                text += f"; it also skipped: {shown}{more}"
        return text
    flights = reply.get("flights")
    for i, f in enumerate(flights if isinstance(flights, list) else []):
        if not isinstance(f, dict) or f.get("ok") is not True:
            err = f.get("error") if isinstance(f, dict) else None
            kind = f.get("error_kind") if isinstance(f, dict) else None
            how = "crashed" if kind == "crash" else "could not start"
            text = f"flight {i + 1} {how} in OpenRocket"
            return f"{text}: {_short_text(err)}" if err else text
    return None


def check_build(reply: dict, root: Node) -> StageCheck:
    """Stage 5: OpenRocket built the design, and its parts fit together.

    `reply` is the simulator's reply for the cleaned design (java/PROTOCOL.md);
    `root` is the cleaned design tree. Credit 0 when OpenRocket could not
    read, build or fly the design; otherwise 1 / (1 + sum of failure sizes).
    Violations smaller than ladder.FIT_DEFECT_BELOW are listed as defects and
    do not fail the stage. info holds the worst value of every rule ("measures").
    """
    info: dict[str, Any] = {}
    why = _not_built(reply)
    if why is not None:
        info["built"] = False
        return _broken(why, info)
    info["built"] = True
    out = _Findings()
    info["load_warnings"] = _check_warnings(reply, out)
    components = reply.get("components")
    if not isinstance(components, list) or not components:
        out.add("components", MAX_VIOLATION, "OpenRocket reported no part positions for this design, "
                                             "so the fit of its parts cannot be checked")
        components = []
    parts = _Parts(components)
    info["components"] = len(parts.all)
    _check_shell(parts, out)
    _check_fins(parts, out)
    _check_inside_radius(parts, out)
    _check_outside_airframe(parts, out)
    loaded = _check_motor_fit(parts, out)
    _check_motor_position(parts, out)
    _check_pods(parts, out)
    _check_doubles(parts, out)
    info["motor_mounts_expected"] = _check_motor_present(root, loaded, out)
    info["motor_mounts_loaded"] = loaded
    info["measures"] = dict(sorted(out.worst.items()))
    info["findings"] = out.kept
    info["violations"] = out.count
    info["failure_sizes"] = [round(s, 4) for s in out.failures]
    info["defect_sizes"] = [round(s, 4) for s in out.defect_sizes]
    defects = list(dict.fromkeys(out.defects))[:MAX_DEFECTS]
    if not out.failures:
        return StageCheck(STAGE, True, credit=1.0, defects=defects, info=info)
    reasons = list(dict.fromkeys(out.reasons))
    if len(reasons) > MAX_REASONS:
        reasons = reasons[:MAX_REASONS] + [f"... and {len(reasons) - MAX_REASONS} more fit problems"]
    credit = credit_from_violations(out.failures)
    return StageCheck(STAGE, False, credit=credit if math.isfinite(credit) else 0.0, reasons=reasons,
                      defects=defects, info=info)
