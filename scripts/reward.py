"""Reward for Rocket AI: one model answer + the prompt's requirements -> one number in [-1, 1].

    from scripts.reward import reward
    r = reward(completion, requirements)    # requirements = the "requirements" dict of a data/splits row

The ladder (CLAUDE.md). The first gate that fails sets the score. Inside the failing tiers there is
partial credit, so GRPO still sees which of 8 failing answers was closer; a tier never reaches the next.

    gate       fails when                                                              score
    format     no closed <design> block, bad JSON, a node that is not {attrs?, value?,  -1.0
               children?}
    parts      no stage, nose cone, body tube, fin set, motor mount with a motor, or    -1.0 .. -0.92
               parachute/streamer                                                       (share of parts there)
    motors     a motor_id is not in the motor lookup                                    -1.0
    geometry   a number no real rocket can have (physical and catalog LIMITS), an       -0.8 .. -0.68
               unknown material, fins < 1.5 mm, OpenRocket can not build the rocket or  (fewer problems,
               skips a part or value, or - on OpenRocket's own resolved geometry -      more credit)
               parts do not fit: shell not one piece, fins off the shell, a part
               outside the rocket or wider than its bore, two solids in one place
    flight     in ANY of 3 flights (0.5x, 1x, 1.5x wind): recovery does not deploy,     -0.5 .. -0.22
               opens too fast, never lands, lands too fast, stability < 1 cal at the    (how close the
               rail or <= 0 in the burn, rail exit < 15 m/s                             worst flight came)
    spec       flew safely but broke a hard requirement (body diameter, motor class,    0.0
               max velocity)
    targets    graded on the WORST flight: apogee .40, flight time .25, landing .15     0..1
               (landing: full marks between 3.5 m/s and the limit; slower is a needlessly
               big chute that drifts.  cost .20 is not scored yet: there is no price data)

How it stays robust
  * Physics, not old designs. Numbers are checked against physical and catalog limits (LIMITS); the
    structure (which parts exist, where they sit, which words a field takes) is checked by OpenRocket
    itself. A new kind of rocket is judged the same as a familiar one.
  * The model does not set physics. Override tags and the model's <simulations> are removed, every
    material density is replaced by the real density for that material name, and the motor's
    name, size and digest come from the motor lookup.
  * Three flights in different winds; the worst one counts.
  * Requirements are data (data/splits rows). Nothing is parsed out of the prompt text.
  * OpenRocket runs in its own Java process (scripts/or_batch/OrBatch.java), one per Python process,
    with a timeout. A hung or dead sim is killed and restarted, so it can not stop training.
  * A problem in the design always gives a score. A problem in the setup (no Java, no OpenRocket jar,
    no materials or lookup file) raises SetupError, so training never gets a made-up number.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import re
import selectors
import statistics
import subprocess
import tempfile
import threading
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("reward_contract", REPO / "sftgen" / "contract.py")
contract = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(contract)

MATERIALS_PATH = REPO / "data" / "reward_materials.json"
LOOKUP_PATH = Path(os.environ.get("MOTOR_LOOKUP", REPO / "data" / "motor_lookup.json"))
JAR = Path(os.environ.get("OPENROCKET_JAR", REPO / "lib" / "OpenRocket.jar"))
OR_BATCH_SRC = REPO / "scripts" / "or_batch" / "OrBatch.java"
OR_BATCH_CLASSES = REPO / "lib" / "or_batch_classes"

LIM = contract.GATES
SIM = contract.DEFAULT_SIM_CONDITIONS
SOFT_LANDING_MS = 3.5            # landing slower than this scores less: a needlessly big chute drifts far
HARD_LANDING_MS = 8.0            # CLAUDE.md Tier 3 limit: a prompt can make it stricter, never looser
WEIGHTS = {"apogee": 0.40, "flight_time": 0.25, "cost": 0.20, "landing": 0.15}
FALLOFF = 0.50                   # past its tolerance, a target's score reaches 0 this far off (50 %)
MIN_FIN_THICKNESS_M = 0.0015     # CLAUDE.md week 8 ("razor fin" patch)
SIM_TIMEOUT_S, BOOT_TIMEOUT_S = 60, 300
MAX_DEPLOY_MS = 50.0             # parachute/streamer opening faster than this fails. OpenRocket warns at 20 m/s,
                                 # but most real designs open at 20-35 m/s (6 % of sft_v5 above 50)
MAX_DEPTH = 64

AIRFRAME = {"nosecone", "bodytube", "transition"}
FINS = {"trapezoidfinset", "ellipticalfinset", "freeformfinset", "tubefinset"}
RECOVERY = {"parachute", "streamer"}
MATERIAL_TAGS = {"material", "filletmaterial", "linematerial"}
NOT_IN_ORK = {"motor_id"}                       # v5 bookkeeping tag that OpenRocket does not know
FROM_LOOKUP = {"motor_id", "manufacturer", "designation", "diameter", "length", "digest"}  # motor fields: lookup
CLASSES = "ABCDEFGHIJKLMNO"
_TAG = re.compile(r"^[A-Za-z_][\w.-]{0,63}$")


class Reject(Exception):
    """The design failed a gate."""

    def __init__(self, gate, reasons, metrics=None, credit=None):
        super().__init__(gate)
        self.gate, self.reasons, self.metrics = gate, list(reasons)[:6], metrics or {}
        # credit in [0, 1): how close the design came to passing. Default: by the number of problems.
        self.credit = credit if credit is not None else max(0.0, 1.0 - len(list(reasons)) / 5)


class SetupError(RuntimeError):
    """The machine is not set up (Java, jar, materials, lookup). Never caught: it must stop training."""


SCORE = {"format": -1.0, "parts": -1.0, "motors": -1.0, "geometry": -0.8, "flight": -0.5, "spec": 0.0}
SPAN = {"parts": 0.1, "geometry": 0.15, "flight": 0.3}     # partial credit: SCORE + SPAN * credit (credit < 1)


# ====================================================================================== tree
class Node:
    """One element of the design. A leaf is a field (<length>0.3</length>); a container is a part."""
    __slots__ = ("tag", "attrs", "value", "kids", "parent", "leaf")

    def __init__(self, tag, attrs, value, leaf, parent):
        self.tag, self.attrs, self.value, self.leaf, self.parent, self.kids = tag, dict(attrs), value, leaf, parent, []

    def get(self, name):
        return next((k for k in self.kids if k.leaf and k.tag == name), None)

    def num(self, name, auto=False):
        """The field as a float. "auto 0.025" gives None, or 0.025 when auto=True."""
        f = self.get(name)
        return None if f is None else to_float(f.value, auto)

    def text(self, name):
        f = self.get(name)
        return None if f is None or f.value is None else str(f.value)

    def parts(self):
        """Child parts, looking through <subcomponents>."""
        for k in self.kids:
            if k.leaf:
                continue
            if k.tag == "subcomponents":
                yield from (c for c in k.kids if not c.leaf)
            else:
                yield k

    def owner(self):
        """The part this part is attached to (skips <subcomponents>)."""
        p = self.parent
        while p is not None and p.tag == "subcomponents":
            p = p.parent
        return p

    def walk(self):
        stack = [self]
        while stack:
            n = stack.pop()
            yield n
            stack.extend(reversed(n.kids))


def to_float(v, auto=False):
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, str):
        bits = v.split()
        if not bits:
            return None
        if bits[0] == "auto":
            if not auto or len(bits) < 2:
                return None
            bits = bits[1:]
        if len(bits) != 1:
            return None
        v = bits[0]
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def parse(obj):
    """{"openrocket": {...}} -> Node tree. Rejects anything that is not the v5 tree shape."""
    if isinstance(obj, dict) and "openrocket" in obj:
        obj = {"openrocket": obj["openrocket"]} if set(obj) <= {"openrocket", "simulations"} else obj
    if not (isinstance(obj, dict) and list(obj) == ["openrocket"]):
        extra = [k for k in obj if k != "openrocket"] if isinstance(obj, dict) else []
        raise Reject("format", [f"the design must be {{\"openrocket\": ...}} only; extra keys: {extra[:3]}"
                                if extra else "the design has no \"openrocket\" root"])
    root, stack = None, [("openrocket", obj["openrocket"], None, 0)]
    while stack:
        tag, body, parent, depth = stack.pop()
        if depth > MAX_DEPTH:
            raise Reject("format", ["the tree is nested too deep"])
        if not _TAG.match(tag):
            raise Reject("format", [f"bad tag name {tag[:30]!r}"])
        if not isinstance(body, dict) or not set(body) <= {"attrs", "value", "children"}:
            raise Reject("format", [f"<{tag}> is not {{attrs?, value?, children?}}"])
        attrs, value, kids = body.get("attrs") or {}, body.get("value"), body.get("children")
        if not isinstance(attrs, dict) or any(isinstance(v, (dict, list)) or not _TAG.match(str(k))
                                              for k, v in attrs.items()):
            raise Reject("format", [f"<{tag}> has bad attrs"])
        if isinstance(value, (dict, list)):
            raise Reject("format", [f"<{tag}> value is not a plain value"])
        node = Node(tag, attrs, value, kids is None, parent)
        if parent is None:
            root = node
        else:
            parent.kids.append(node)
        if kids is None:
            continue
        if isinstance(kids, dict):
            kids = [{k: v} for k, v in kids.items()]
        if not isinstance(kids, list) or not all(isinstance(c, dict) and len(c) == 1 for c in kids):
            raise Reject("format", [f"<{tag}> children is not a list of {{tag: node}}"])
        for c in reversed(kids):
            (k, v), = c.items()
            stack.append((str(k), v, node, depth + 1))
    return root


def drop(root, pred):
    """Remove every node matching pred. Returns how many were removed."""
    n = 0
    for node in list(root.walk()):
        keep = [k for k in node.kids if not pred(k)]
        n += len(node.kids) - len(keep)
        node.kids = keep
    return n


# ====================================================================================== gates 1-3
def gate_format(completion, finish):
    if finish in ("length", "error"):
        raise Reject("format", ["the answer did not finish" if finish == "length" else "the request failed"])
    i = completion.rfind("<design>")
    j = completion.find("</design>", i) if i >= 0 else -1
    if j < 0:
        raise Reject("format", ["no complete <design>...</design> block"])
    try:
        obj = json.loads(completion[i + len("<design>"):j])
    except (ValueError, RecursionError) as e:
        raise Reject("format", [f"design JSON does not parse: {str(e)[:80]}"])
    root = parse(obj)
    drop(root, lambda k: k.tag == "simulations")
    return root, drop(root, lambda k: k.tag.lower().startswith("override"))


def gate_parts(root):
    rocket = next((k for k in root.kids if k.tag == "rocket" and not k.leaf), None)
    stages = [p for p in rocket.parts() if p.tag == "stage"] if rocket else []
    have = {n.tag for s in stages for n in s.walk() if not n.leaf}
    missing = [t for t in ("nosecone", "bodytube", "motormount", "motor") if t not in have]
    if not have & FINS:
        missing.append("fin set")
    if not have & RECOVERY:
        missing.append("parachute or streamer")
    if not stages:
        missing.insert(0, "rocket > stage")
    if missing:
        raise Reject("parts", ["missing: " + ", ".join(missing)], credit=0.0 if not stages else 1 - len(missing) / 6)
    for mm in (n for n in root.walk() if n.tag == "motormount" and not n.leaf):
        if mm.owner() is None or mm.owner().tag not in ("bodytube", "innertube"):
            raise Reject("parts", [f"a motor mount sits on <{mm.owner().tag if mm.owner() else None}>, "
                                   "not a body or inner tube"], credit=5 / 6)
    return stages


def gate_motors(root, lookup):
    """Every motor_id must be real. The motor's name, size and digest are then taken from the lookup."""
    motors = [n for n in root.walk() if n.tag == "motor" and not n.leaf]
    bad, used = [], []
    for m in motors:
        mid = m.text("motor_id")
        if mid is not None and mid not in lookup and f"{mid}-v1" in lookup:
            mid = f"{mid}-v1"                       # a real motor written without its version suffix
            m.get("motor_id").value = mid
        if mid is None or mid not in lookup:
            bad.append(mid or m.text("designation") or "?")
            continue
        info = lookup[mid]
        used.append(info)
        for field, key in (("manufacturer", "manufacturer"), ("designation", "designation"),
                           ("diameter", "diameter_m"), ("length", "length_m"), ("digest", "digest")):
            if info.get(key) is None:
                continue
            f = m.get(field)
            if f is None:
                m.kids.append(Node(field, {}, info[key], True, m))
            else:
                f.value = info[key]
    if bad:
        raise Reject("motors", ["unknown motor_id: " + ", ".join(sorted(set(map(str, bad)))[:5])])
    return used


# Launch rail length by the biggest motor, as at real launch sites: small rockets fly off a short rod,
# high-power rockets off long rails. One short rail for all made 44 of 163 real reference rockets fail
# "rail exit >= 15 m/s" only because big rockets need more rail to get up to speed.
RAIL_M = [("F", 1.5), ("G", 1.8), ("I", 2.4), ("K", 3.0), ("O", 3.7)]   # up to and including that class


def rail_length(motors):
    worst = max((motor_class(i) for i in motors), key=CLASSES.index, default="A")
    return next(m for c, m in RAIL_M if CLASSES.index(worst) <= CLASSES.index(c))


def motor_class(info):
    i = info.get("total_impulse_ns") or 0
    return CLASSES[min(len(CLASSES) - 1, max(0, math.ceil(math.log2(i / 2.5)) if i > 0 else 0))]


# ====================================================================================== gate 4
# Physical limits. Every number must be one that a real hobby rocket can have, and each limit names
# its source:  catalog = the parts library inside lib/OpenRocket.jar (1,496 body tubes, 422 parachutes);
# spec = CLAUDE.md;  OR = OpenRocket's own limit;  size = nothing on a hobby rocket is bigger;
# judgment = no hard source yet.  Which parts exist, where they may sit, and which words a field takes
# is OpenRocket's call: it refuses or warns, and that fails the design too (gate_flight). Nothing here
# is compared with old designs, so a new kind of rocket is judged the same as a familiar one.
_LEN = ("aftradius aftshoulderlength aftshoulderradius aftshoulderthickness baseheight diameter filletradius "
        "flangeheight foreradius foreshoulderlength foreshoulderradius foreshoulderthickness height innerdiameter "
        "innerradius instanceseparation length outerdiameter outerradius packedlength packedradius radialposition "
        "radius rootchord screwheight stripwidth tabheight tablength tipchord thickness").split()
_SIGNED = "axialoffset position radiusoffset tabposition sweeplength overhang".split()
_ANGLE = "angleoffset radialdirection rotation clusterrotation".split()
_TIME = "delay deploydelay ignitiondelay separationdelay".split()
LIMITS = {   # field -> (lo, hi, source). Lengths in m, angles in degrees, times in s, mass in kg.
    **{f: (0.0, 5.0, "size") for f in _LEN},
    **{f: (-5.0, 5.0, "size") for f in _SIGNED},
    **{f: (-360.0, 360.0, "size") for f in _ANGLE},
    **{f: (0.0, 30.0, "size") for f in _TIME},
    "cordlength": (0.0, 30.0, "size"), "linelength": (0.0, 10.0, "size"), "striplength": (0.0, 10.0, "size"),
    "deployaltitude": (0.0, 10000.0, "size"), "separationaltitude": (0.0, 10000.0, "size"),
    "cant": (-15.0, 15.0, "OR"), "fincount": (1, 8, "OR"), "instancecount": (1, 32, "size"),
    "linecount": (0, 64, "size"), "shapeparameter": (0.0, 1.0, "OR"), "clusterscale": (0.0, 50.0, "size"),
    "mass": (0.0, 20.0, "size"), "cd": (0.0, 3.0, "size"),
}
PART_LIMITS = {   # (part, field) -> (lo, hi, source); wins over LIMITS
    ("bodytube", "radius"): (0.0025, 0.15, "catalog: tubes are 5-300 mm wide"),
    ("bodytube", "length"): (0.0, 3.66, "catalog: two of the longest tube (1.83 m)"),
    ("parachute", "diameter"): (0.15, 6.1, "catalog: chutes are 0.15-6.1 m"),
    ("parachute", "cd"): (0.6, 2.9, "catalog: chute Cd is 0.61-2.92"),   # a big Cd is the soft-landing cheat
    ("streamer", "cd"): (0.05, 0.6, "judgment"),
}
WALLS = {"bodytube", "nosecone", "transition"}       # the outer shell; inner tubes are left to the sim
MIN_WALL_M = 0.00013              # catalog: the thinnest real tube wall. Thinner is the light-rocket cheat.


def _number(v):
    """(x, problem). x is the number in v ("auto 0.02" -> 0.02), None for a word; problem for NaN/inf."""
    if isinstance(v, bool) or v is None:
        return None, None
    bits = str(v).split()
    try:
        x = float(bits[-1]) if bits else None
    except ValueError:
        return None, None
    if x is None or math.isfinite(x):
        return x, None
    return None, f"{bits[-1]} is not a finite number"


def limit_problems(root):
    out = []
    for f in root.walk():
        if not f.leaf or f.parent is None or f.tag in MATERIAL_TAGS:
            continue
        part = f.parent.tag
        if part == "motor" and f.tag in FROM_LOOKUP:
            continue
        if isinstance(f.value, str) and (len(f.value) > 200 or not f.value.isprintable()):
            out.append(f"<{part}><{f.tag}>: bad text")
        for a in ("x", "y"):                             # freeform fin points
            if f.tag == "point" and a in f.attrs:
                x, bad = _number(f.attrs[a])
                if bad or x is None or abs(x) > 5.0:
                    out.append(f"<{part}><point {a}=...>: {bad or f'{f.attrs[a]!r} is not in -5..5 m'}")
        rule = PART_LIMITS.get((part, f.tag)) or LIMITS.get(f.tag)
        if rule is None:
            continue
        x, bad = _number(f.value)
        if bad:
            out.append(f"<{part}><{f.tag}>: {bad}")
        elif x is not None and not rule[0] <= x <= rule[1]:
            out.append(f"<{part}><{f.tag}>: {x:g} is outside {rule[0]:g}..{rule[1]:g} ({rule[2]})")
        elif x is not None and f.tag == "thickness" and part in WALLS and x < MIN_WALL_M:
            out.append(f"<{part}> wall is {x * 1000:.3f} mm (catalog minimum {MIN_WALL_M * 1000:g} mm)")
    return out


def material_family(name):
    """"RS: Paper, spiral kraft glassine, PK IIIa, bulk" -> "paper"; "1/16 In. braided nylon" -> "braided"."""
    words = re.findall(r"[a-z]+", str(name).lower().replace("rs:", "").split(",")[0])
    return next((w for w in words if w not in ("in", "mm", "cm", "oz", "lb", "ft", "flat", "round")), "")


def material_problems(root, mats):
    """Replace every density with the real one for that material: the exact name (sft_v5 designs, then
    OpenRocket's own parts library), else the median of its family. A material of no known family fails."""
    out, mats, fams = [], mats["materials"], mats["material_families"]
    for f in root.walk():
        if f.leaf and f.tag in MATERIAL_TAGS:
            t, name = f.attrs.get("type"), str(f.value)
            clean = re.sub(r"^RS:\s*|,\s*bulk$", "", name)
            d = next((x for x in (mats.get(f"{t}|{name}"), mats.get(f"{t}|{clean}"),
                                  fams.get(f"{t}|{material_family(name)}")) if x is not None), None)
            if d is None:
                out.append(f"unknown material {t}|{name[:40]!r}")
            else:
                f.attrs["density"] = d
    return out


def part_problems(stages):
    """Checks on what the model wrote that OpenRocket would silently repair (it moves fins off a stage,
    fills in a default fin shape). Everything about where parts end up is checked on OpenRocket's own
    geometry instead (fit_problems)."""
    out = []
    for n in (n for s in stages for n in s.walk() if not n.leaf):
        if n.tag in AIRFRAME and n.tag != "nosecone" and n.tag != "transition":
            r, t = n.num("radius") if n.tag == "bodytube" else n.num("outerradius"), n.num("thickness")
            if r is not None and t is not None and t >= r:
                out.append(f"{n.tag} wall is thicker than its radius")
        if n.tag in AIRFRAME and (n.num("length") or 0) <= 0:
            out.append(f"{n.tag} has no length")
        if n.tag not in FINS:
            continue
        own = n.owner()
        if own is None or own.tag not in AIRFRAME:
            out.append(f"{n.tag} is on <{own.tag if own else None}>, not the airframe")
        if (n.num("fincount") or n.num("instancecount") or 0) < 1:
            out.append(f"{n.tag} has no fins")
        if n.tag != "tubefinset":
            t = n.num("thickness")
            if t is None or t < MIN_FIN_THICKNESS_M:
                out.append(f"{n.tag} is {0 if t is None else t * 1000:.2f} mm thick (min {MIN_FIN_THICKNESS_M * 1000:g})")
        if n.tag in ("trapezoidfinset", "ellipticalfinset") and not ((n.num("height") or 0) > 0 and (n.num("rootchord") or 0) > 0):
            out.append(f"{n.tag} has zero height or root chord")
        if n.tag == "freeformfinset" and len([p for fp in n.kids if fp.tag == "finpoints" for p in fp.kids]) < 3:
            out.append("freeform fin has fewer than 3 points")
    return out


def gate_geometry(root, stages, mats):
    probs = limit_problems(root) + material_problems(root, mats) + part_problems(stages)
    if probs:
        raise Reject("geometry", probs)


# ====================================================================================== gate 5: fit
# The model writes positions in many ways ("bottom - 0.02", "after", "absolute 0.8"). OpenRocket turns
# them into one rocket: every part with its absolute position x0 (m from the nose tip), length and radii
# (scripts/or_batch/OrBatch.java, sim name "__geometry__"). Four physical rules then run on that rocket,
# so we never re-implement OpenRocket's placement rules and never guess what the model meant.
#   1 the outer shell is one piece      2 fins sit on the shell
#   3 inside parts fit inside           4 no two solids in the same space
# Two exceptions, both physical: the diameter may change between stages (an interstage), and short
# hardware may sit on the outside of the tail if it touches the tail (motor retainers, thrust plates).
SHELL = {"NoseCone", "BodyTube", "Transition"}
SOLID_INSIDE = {"InnerTube", "TubeCoupler", "CenteringRing", "Bulkhead", "EngineBlock"}
PACKED = {"Parachute", "Streamer", "ShockCord", "MassComponent"}  # soft or placeholder size: position only
RINGS = {"CenteringRing", "Bulkhead", "EngineBlock"}
FIT_TOL_M = 0.001
FIN_CLASH_DEG = 3.0              # two fin sets on one tube with fins closer than this, and overlapping
MOTOR_FIT = 1.05                 # motor up to 5 % wider than its mount bore (as Shamik measured on 249 .ork)
INSIDE_FIT = 1.05                # a solid inside part up to 5 % wider than the bore it sits in


def _overlap(a0, a1, b0, b1):
    return min(a1, b1) - max(a0, b0)


def _bore(p):
    if p["type"] in ("InnerTube", "TubeCoupler"):
        return p.get("r_in") or 0.0
    wall = p.get("wall")
    return 0.0 if wall is None or wall < 0 else max(p.get("r_fore") or 0, p.get("r_aft") or 0) - wall


def fit_problems(parts):
    """(problems, widest shell radius) for OpenRocket's resolved parts."""
    by = {p["i"]: p for p in parts}

    def up(p, types):
        q = by.get(p["parent"])
        while q is not None and q["type"] not in types:
            q = by.get(q["parent"])
        return q

    out = []
    if not any("motor_d" in p for p in parts):
        out.append("no motor is left after OpenRocket loaded the design (parts nested wrongly)")
    stage_of = {p["i"]: (up(p, {"AxialStage", "ParallelStage", "PodSet"}) or {}) for p in parts}
    shell = sorted((p for p in parts if p["type"] in SHELL and stage_of[p["i"]].get("type") == "AxialStage"),
                   key=lambda p: p["x0"])
    max_r = max((max(p.get("r_fore") or 0, p.get("r_aft") or 0) for p in shell), default=0.0)
    if not shell:
        return out + ["no outer shell"], max_r
    lo, hi = shell[0]["x0"], max(p["x0"] + p["len"] for p in shell)
    tail_r = shell[-1].get("r_aft") or 0.0
    # Tail hardware: short solid parts behind the tail, each touching the tail or a part already on it.
    ends, tail = [hi], set()
    for p in sorted((p for p in parts if p["type"] in SOLID_INSIDE | {"MassComponent"} and 0 < p["len"] <= 2 * tail_r
                     and p["x0"] + p["len"] > hi + FIT_TOL_M), key=lambda p: p["x0"]):
        if p["x0"] <= max(ends) + 2 * FIT_TOL_M:       # starts on the tail or on a part already attached
            tail.add(p["i"])
            ends.append(p["x0"] + p["len"])
    # 1 the outer shell is one piece
    for a, b in zip(shell, shell[1:]):
        gap = b["x0"] - (a["x0"] + a["len"])
        if abs(gap) > FIT_TOL_M:
            out.append(f"{'gap' if gap > 0 else 'overlap'} of {abs(gap) * 1000:.0f} mm between {a['type']} and {b['type']}")
        step = abs((a.get("r_aft") or 0) - (b.get("r_fore") or 0)) * 2
        if step > FIT_TOL_M and stage_of[a["i"]].get("i") == stage_of[b["i"]].get("i"):
            out.append(f"diameter step of {step * 1000:.1f} mm between {a['type']} and {b['type']}")
    for p in parts:
        end = p["x0"] + p["len"]
        # 2 fins sit on the shell
        if "fins" in p:
            host = by.get(p["parent"])
            if host is not None and p["len"] > 0 and (
                    _overlap(p["x0"], end, lo, hi) < 0.5 * p["len"]
                    or _overlap(p["x0"], end, host["x0"], host["x0"] + host["len"]) <= 0):
                out.append(f"fins at {p['x0']:.3f}-{end:.3f} m are off their tube "
                           f"({host['x0']:.3f}-{host['x0'] + host['len']:.3f} m)")
        # 3 inside parts fit inside
        if p["type"] in SOLID_INSIDE | PACKED and p["len"] > 0:
            tail_hardware = p["i"] in tail
            if _overlap(p["x0"], end, lo, hi) < 0.5 * p["len"] and not tail_hardware:
                out.append(f"{p['type']} at {p['x0']:.3f}-{end:.3f} m is outside the rocket ({lo:.3f}-{hi:.3f} m)")
            host = up(p, SHELL if p["type"] in RINGS | {"InnerTube", "TubeCoupler"} else SHELL | {"InnerTube"})
            r = (p.get("r_out") or 0) + abs(p.get("r_pos") or 0)
            if (p["type"] in SOLID_INSIDE and host is not None and not tail_hardware
                    and _bore(host) > 0 and r > _bore(host) * INSIDE_FIT + 0.0005):
                out.append(f"{p['type']} {r * 2000:.1f} mm wide in a {_bore(host) * 2000:.1f} mm {host['type']}")
        if "motor_d" in p and _bore(p) and p["motor_d"] > _bore(p) * 2 * MOTOR_FIT:
            out.append(f"{p['motor_d'] * 1000:.0f} mm motor in a {_bore(p) * 2000:.1f} mm mount")
    # 4 no two solids in the same space
    kids = {}
    for p in parts:
        kids.setdefault(p["parent"], []).append(p)
    for sibs in kids.values():
        fins = [p for p in sibs if "fins" in p]
        for i, a in enumerate(fins):
            for b in fins[i + 1:]:
                ang = min(min(abs(x - y) % 360, 360 - abs(x - y) % 360)
                          for x in (a["rot"] + k * 360 / a["fins"] for k in range(a["fins"]))
                          for y in (b["rot"] + k * 360 / b["fins"] for k in range(b["fins"])))
                if _overlap(a["x0"], a["x0"] + a["len"], b["x0"], b["x0"] + b["len"]) > FIT_TOL_M and ang < FIN_CLASH_DEG:
                    out.append("two fin sets in the same place")
        rings = [p for p in sibs if p["type"] in RINGS]
        for i, a in enumerate(rings):
            for b in rings[i + 1:]:
                if (_overlap(a["x0"], a["x0"] + a["len"], b["x0"], b["x0"] + b["len"]) > FIT_TOL_M
                        and _overlap(a.get("r_in") or 0, a.get("r_out") or 0, b.get("r_in") or 0, b.get("r_out") or 0) > FIT_TOL_M):
                    out.append(f"{a['type']} and {b['type']} in the same space")
    return out, max_r


# ====================================================================================== gate 5
def config_id(root):
    found = []
    for n in root.walk():
        if n.tag in ("motorconfiguration", "motor") and n.attrs.get("configid"):
            found.append((n.tag != "motorconfiguration" or str(n.attrs.get("default")).lower() != "true",
                          n.tag != "motorconfiguration", str(n.attrs["configid"])))
    return sorted(found, key=lambda f: f[:2])[0][2] if found else None


def to_ork(root, req, rail=None):
    """The cleaned tree as .ork XML, with one simulation per FLIGHTS wind: "reward0", "reward1", ..."""
    def el(n):
        e = ET.Element(n.tag, {k: fmt(v) for k, v in n.attrs.items()})
        if n.value is not None:
            e.text = fmt(n.value)
        e.extend(el(k) for k in n.kids if k.tag not in NOT_IN_ORK)
        return e

    cid = config_id(root)
    if cid is None:
        raise Reject("flight", ["no motor configuration id (configid) to fly"])
    x = el(root)
    x.set("version", x.get("version") or "1.10")
    sims = ET.SubElement(x, "simulations")
    base = min(float(req.get("wind_ms", SIM["wind_ms"])), LIM["max_wind_ms"])
    for i, k in enumerate(FLIGHTS):
        sim = ET.SubElement(sims, "simulation", status="outdated")
        ET.SubElement(sim, "name").text = f"reward{i}"
        ET.SubElement(sim, "simulator").text = "RK4Simulator"
        ET.SubElement(sim, "calculator").text = "BarrowmanCalculator"
        c = ET.SubElement(sim, "conditions")
        for key, v in (("configid", cid), ("launchrodlength", rail or SIM["rail_length_m"]),
                       ("launchrodangle", SIM["launch_angle_deg"]), ("launchroddirection", 90.0),
                       ("windaverage", min(base * k, LIM["max_wind_ms"])), ("windturbulence", SIM["wind_turbulence"]),
                       ("launchaltitude", SIM["site_altitude_m"]), ("launchlatitude", 28.61),
                       ("launchlongitude", -80.6), ("geodeticmethod", "spherical"), ("timestep", SIM["time_step_s"])):
            ET.SubElement(c, key).text = fmt(v)
        ET.SubElement(c, "atmosphere", model="isa")
    return ET.tostring(x, encoding="unicode", xml_declaration=True)


def fmt(v):
    return ("true" if v else "false") if isinstance(v, bool) else str(v)


class OpenRocket:
    """One OrBatch Java process. fly() sends one .ork path and reads one JSON line, with a timeout."""

    def __init__(self):
        self.p, self.answered, self.buf, self.lock = None, 0, b"", threading.Lock()

    @staticmethod
    def _java(tool):
        for home in (os.environ.get("OPENROCKET_JAVA_HOME"), os.environ.get("JAVA_HOME"),
                     Path.home() / ".jdks" / "jdk-17.0.20.1+1" / "Contents" / "Home"):
            if home and (Path(home) / "bin" / tool).exists():
                return str(Path(home) / "bin" / tool)
        return tool

    def _start(self):
        if not JAR.exists():
            raise SetupError(f"OpenRocket jar not found at {JAR} (scripts/fetch_openrocket.sh)")
        stamp = OR_BATCH_CLASSES / "OrBatch.class"
        if not stamp.exists() or stamp.stat().st_mtime < OR_BATCH_SRC.stat().st_mtime:
            OR_BATCH_CLASSES.mkdir(parents=True, exist_ok=True)
            r = subprocess.run([self._java("javac"), "--release", "17", "-nowarn", "-cp", str(JAR), "-d",
                                str(OR_BATCH_CLASSES), str(OR_BATCH_SRC)], capture_output=True, text=True)
            if r.returncode:
                raise SetupError("could not compile OrBatch.java:\n" + r.stderr[-1000:])
        cmd = [self._java("java"), "-Djava.awt.headless=true", "-Dfile.encoding=UTF-8", "-Dsun.jnu.encoding=UTF-8",
               "-cp", os.pathsep.join([str(JAR), str(OR_BATCH_CLASSES)]), "OrBatch"]
        self.p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                  bufsize=0, cwd=REPO)
        self.answered, self.buf = 0, b""

    def _kill(self):
        if self.p is not None:
            self.p.kill()
            self.p.wait()
        self.p = None

    def fly(self, ork_path, seed=42, name="reward0"):
        with self.lock:
            if self.p is None or self.p.poll() is not None:
                self._start()
            timeout = SIM_TIMEOUT_S + (BOOT_TIMEOUT_S if self.answered == 0 else 0)
            try:
                self.p.stdin.write(f"{ork_path}\t{name}\t{int(seed)}\t1\t42\n".encode())
            except (BrokenPipeError, OSError):
                self._kill()
                raise SetupError("OpenRocket process would not take input")
            sel = selectors.DefaultSelector()
            sel.register(self.p.stdout, selectors.EVENT_READ)
            try:
                while True:
                    if b"\n" in self.buf:
                        line, self.buf = self.buf.split(b"\n", 1)
                        if line.startswith(b"{"):
                            self.answered += 1
                            return json.loads(line.decode("utf-8", "replace"))
                        continue
                    if not sel.select(timeout):
                        self._kill()
                        raise Reject("flight", [f"OpenRocket did not finish in {SIM_TIMEOUT_S} s"])
                    chunk = os.read(self.p.stdout.fileno(), 1 << 16)
                    if not chunk:                                  # the Java process died
                        booted = self.answered > 0
                        self._kill()
                        if not booted:
                            raise SetupError("OpenRocket process died before its first answer (check Java)")
                        raise Reject("flight", ["OpenRocket crashed on this design"])
                    self.buf += chunk
            finally:
                sel.close()


_OR = OpenRocket()


FLIGHTS = (0.5, 1.0, 1.5)         # every design flies 3 times: at 0.5x, 1x and 1.5x the wind, each with its own
                                  # gusts. The worst flight counts, so a design can not fit one lucky wind.


def flight_problems(sim, limit):
    """(problems, margin). margin in [0, 1] says how close an unsafe flight came to safe (partial credit)."""
    events = sim.get("events", [])
    aborts = [e.get("data", "") for e in events if e.get("type") == "SIM_ABORT"]
    out, fast, early = [f"simulation aborted: {a[:100]}" for a in aborts], 0.0, False
    for e in events:
        w = e.get("data", "") if e.get("type") == "SIM_WARN" else ""
        if m := re.search(r"deployment at high speed \(([\d.]+) m/s", w):
            fast = max(fast, float(m.group(1)))
        early |= bool(re.search(r"while (the )?motor", w, re.I))
    if fast > MAX_DEPLOY_MS:
        out.append(f"recovery opens at {fast:.0f} m/s (max {MAX_DEPLOY_MS:g})")
    if early:
        out.append("recovery opens while the motor burns")
    branches, recovered, land = sim.get("branches") or [], True, 0.0
    for b in branches:
        if not b["deployed"]:
            out.append(f"{b['name']}: recovery never deployed")
            recovered = False
        if not b["ground"]:
            out.append(f"{b['name']}: never reached the ground")
            recovered = False
        elif b["landing_ms"] is None or b["landing_ms"] > limit:
            out.append(f"{b['name']}: lands at {b['landing_ms'] or 0:.1f} m/s (limit {limit:g})")
        land = max(land, b["landing_ms"] if b["landing_ms"] is not None else math.inf)
    if not branches:
        out.append("no flight data")
    st, sb, rail = sim.get("stability_rail_cal"), sim.get("stability_min_burn_cal"), sim.get("rail_exit_ms") or 0.0
    if st is None:
        out.append("no stability data after the rail (the rocket never left the rail)")
    elif st < LIM["min_launch_margin_cal"]:
        out.append(f"stability at the rail {st:.2f} cal (needs >= {LIM['min_launch_margin_cal']:g})")
    if sb is not None and sb <= LIM["min_burn_margin_cal"]:
        out.append(f"stability falls to {sb:.2f} cal in the burn")
    if rail < LIM["min_rail_exit_ms"]:
        out.append(f"rail exit {rail:.1f} m/s (needs >= {LIM['min_rail_exit_ms']:g})")
    clamp = lambda x: max(0.0, min(1.0, x))
    margin = statistics.mean([
        0.0 if aborts else 1.0,
        0.0 if early else clamp(MAX_DEPLOY_MS / fast) if fast else 1.0,
        1.0 if recovered and branches else 0.0,
        clamp(limit / land) if branches and land > 0 else 0.0,
        clamp((st or 0.0) / LIM["min_launch_margin_cal"]),
        0.0 if sb is not None and sb <= LIM["min_burn_margin_cal"] else 1.0,
        clamp(rail / LIM["min_rail_exit_ms"])])
    return out, margin


def flight_metrics(sim, limit):
    m = {k: sim.get(k) for k in ("apogee_m", "flight_time_s", "max_velocity_ms", "rail_exit_ms",
                                  "stability_rail_cal", "stability_min_burn_cal", "deployment_velocity_ms", "wind_ms")}
    m["landing_ms"] = [b["landing_ms"] for b in sim.get("branches") or []]
    m["landing_limit_ms"] = limit
    return m


def gate_flight(root, req, seed, motors=()):
    """Check the fit on OpenRocket's geometry, then fly the design FLIGHTS times.
    Returns (metrics of every flight, fields OpenRocket ignored, widest body radius)."""
    limit = min(float(req.get("max_touchdown_ms", LIM["default_max_landing_ms"])), HARD_LANDING_MS)
    with tempfile.TemporaryDirectory(prefix="reward_") as d:
        path = Path(d) / "design.ork"
        path.write_text(to_ork(root, req, rail_length(motors)), encoding="utf-8")
        geo = _OR.fly(path, seed, "__geometry__")
        if geo.get("error"):
            raise Reject("geometry", [f"OpenRocket could not build it: {geo['error'][:160]}"], credit=0.0)
        fit, max_r = fit_problems(geo.get("parts") or [])
        if fit:
            raise Reject("geometry", fit)
        sims = []
        for i in range(len(FLIGHTS)):
            sims.append(_OR.fly(path, seed + i, f"reward{i}"))
            if sims[-1].get("error"):
                # OpenRocket could not build it (parts that can not connect, NaN mass): a CAD fault, so -0.8.
                # As an unsafe flight (-0.5) it would pay the model for crashing the sim.
                raise Reject("geometry", [f"OpenRocket could not build it: {sims[-1]['error'][:160]}"], credit=0.0)
    warns = [str(w) for w in sims[0].get("load_warnings") or []]
    ignored = sorted(re.sub(r", ignoring\.$", "", w) for w in warns if w.startswith("Unknown parameter type"))
    bad = [w for w in warns if not w.startswith("Unknown parameter type")]
    if bad:              # an unknown part, a part in the wrong place, a bad value: OpenRocket skipped it
        raise Reject("geometry", [f"OpenRocket: {w[:140]}" for w in bad], credit=0.0)
    flights = [(*flight_problems(s, limit), flight_metrics(s, limit)) for s in sims]
    failing = [f for f in flights if f[0]]
    if failing:
        probs, margin, m = min(failing, key=lambda f: f[1])
        raise Reject("flight", probs, m, credit=min(margin, 0.95))
    return [f[2] for f in flights], ignored, max_r



# ====================================================================================== gates 6-7
def gate_spec(req, max_r, motors, m):
    out = []
    if req.get("max_body_diameter_mm") and max_r * 2000 > req["max_body_diameter_mm"] + 0.5:
        out.append(f"body {max_r * 2000:.1f} mm is wider than {req['max_body_diameter_mm']:g} mm")
    if req.get("max_motor_class"):
        worst = max((motor_class(i) for i in motors), key=CLASSES.index)
        if CLASSES.index(worst) > CLASSES.index(req["max_motor_class"]):
            out.append(f"motor class {worst} is above {req['max_motor_class']}")
    if req.get("max_velocity_ms") and (m.get("max_velocity_ms") or 0) > req["max_velocity_ms"]:
        out.append(f"max velocity {m['max_velocity_ms']:.0f} m/s is above {req['max_velocity_ms']:g}")
    if out:
        raise Reject("spec", out)


def closeness(got, want, kind, tol):
    """1 inside the tolerance, then a straight line down to 0 at FALLOFF past it."""
    off = {"min": (want - got) / want, "max": (got - want) / want}.get(kind, abs(got - want) / want - tol)
    return max(0.0, 1.0 - max(0.0, off) / FALLOFF)


def targets(req, m):
    parts = {}
    if req.get("target_apogee_m"):
        parts["apogee"] = closeness(m["apogee_m"], req["target_apogee_m"], "about", req.get("apogee_tol_frac", 0.05))
    if req.get("max_flight_time_s"):
        parts["flight_time"] = closeness(m["flight_time_s"], req["max_flight_time_s"], "max", 0.0)
    lands = [v for v in m["landing_ms"] if v is not None]
    if lands:
        lim = m["landing_limit_ms"]
        soft = min(SOFT_LANDING_MS, 0.6 * lim)       # full marks from soft up to the limit; no prize for
        parts["landing"] = min(1.0, max(lands) / soft)  # a bigger chute than needed
    total = sum(WEIGHTS[k] for k in parts)
    return round(sum(v * WEIGHTS[k] for k, v in parts.items()) / total, 4) if total else 0.0, parts


# ====================================================================================== ladder
_CACHE = {}


def _load(path, what):
    if path not in _CACHE:
        if not Path(path).exists():
            raise SetupError(f"{what} not found at {path}")
        _CACHE[path] = json.loads(Path(path).read_text(encoding="utf-8"))
    return _CACHE[path]


def score(completion, requirements, finish="stop", lookup=None, materials=None, seed=42, flight=True):
    """Run the ladder. Returns {"score", "gate", "reasons", "parts", "metrics", "notes"}.
    gate is the gate that failed (None when the design reached the targets). flight=False stops after
    the geometry gate with score None (for debugging only: OpenRocket's structure check is skipped)."""
    req = requirements or {}
    lookup = lookup if lookup is not None else _load(LOOKUP_PATH, "motor lookup")
    materials = materials if materials is not None else _load(MATERIALS_PATH, "materials (run --build-materials)")
    res = {"score": None, "gate": None, "reasons": [], "parts": {}, "metrics": {}, "notes": {}}
    if req.get("budget_usd"):
        res["notes"]["not_scored"] = ["cost (no price data)"]
    try:
        try:
            root, res["notes"]["overrides_removed"] = gate_format(completion or "", finish)
            stages = gate_parts(root)
            motors = gate_motors(root, lookup)
            gate_geometry(root, stages, materials)
            if not flight:
                res["gate"] = "not flown"
                return res
            flights, res["notes"]["ignored_fields"], max_r = gate_flight(root, req, seed, motors)
            worst_v = max((m.get("max_velocity_ms") or 0) for m in flights)
            gate_spec(req, max_r, motors, {"max_velocity_ms": worst_v})
        except (Reject, SetupError):
            raise
        except Exception as e:                       # a bug in a check, never a reason to crash training
            raise Reject("geometry", [f"checker error: {type(e).__name__}: {str(e)[:100]}"], credit=0.0) from e
    except Reject as r:
        credit = min(max(r.credit, 0.0), 0.95) if r.gate in SPAN else 0.0
        res.update(score=round(SCORE[r.gate] + SPAN.get(r.gate, 0.0) * credit, 4), gate=r.gate, reasons=r.reasons)
        res["metrics"] = r.metrics or res["metrics"]
        res["notes"]["checker_error"] = any(s.startswith("checker error") for s in r.reasons)
        return res
    graded = [(targets(req, m), m) for m in flights]
    (res["score"], res["parts"]), res["metrics"] = min(graded, key=lambda g: g[0][0])
    res["notes"]["apogee_m_per_flight"] = [m.get("apogee_m") for m in flights]
    return res


def reward(completion, requirements, **kw) -> float:
    """The number for GRPO, in [-1, 1]."""
    r = score(completion, requirements, **kw)
    if r["score"] is None:
        raise RuntimeError("no score (flight=False is for debugging only)")
    return r["score"]


# ====================================================================================== materials
def build_materials(sft_jsonl):
    """data/reward_materials.json: every material's density (the median in the reference designs, plus
    OpenRocket's own parts library in lib/OpenRocket.jar), and the median of each material family."""
    mats = {}
    for line in open(sft_jsonl, encoding="utf-8"):
        text = json.loads(line)["messages"][-1]["content"]
        i = text.rfind("<design>")
        for f in parse(json.loads(text[i + 8:text.find("</design>", i)])).walk():
            if f.leaf and f.tag in MATERIAL_TAGS and to_float(f.attrs.get("density")) is not None:
                mats.setdefault(f"{f.attrs.get('type')}|{f.value}", []).append(float(f.attrs["density"]))
    table = {k: d for k, d in {**library_materials(), **{k: round(statistics.median(v), 6) for k, v in mats.items()}}
             .items() if DENSITY_RANGE.get(k.split("|")[0], (0, 0))[0] <= d <= DENSITY_RANGE.get(k.split("|")[0], (0, 0))[1]}
    fams = {}
    for k, d in table.items():
        t, name = k.split("|", 1)
        fams.setdefault(f"{t}|{material_family(name)}", []).append(d)
    return {"_source": f"built by scripts/reward.py --build-materials from {Path(sft_jsonl).name} + OpenRocket "
                       "parts library", "materials": dict(sorted(table.items())),
            "material_families": {k: round(statistics.median(v), 6) for k, v in sorted(fams.items()) if k[-1] != "|"}}


DENSITY_RANGE = {"bulk": (10.0, 25000.0), "surface": (0.0, 5.0), "line": (0.0, 1.0)}   # kg/m3, kg/m2, kg/m:
# anything outside is a mislabeled entry (e.g. an elastic cord typed "bulk"), never a real material


def library_materials():
    """{"bulk|Balsa, bulk, Estes typical": 160.2, ...} from the .orc parts files inside the OpenRocket jar."""
    import zipfile
    out, to_si = {}, {"kg/m3": 1.0, "kg/m2": 1.0, "kg/m": 1.0, "g/m2": 0.001, "g/cm3": 1000.0}
    if not JAR.exists():
        return out
    with zipfile.ZipFile(JAR) as z:
        for name in z.namelist():
            if not name.lower().endswith(".orc"):
                continue
            for m in ET.fromstring(z.read(name)).iter():
                if m.tag.split("}")[-1] != "Material":
                    continue
                get = {c.tag.split("}")[-1]: (c.text or "").strip() for c in m}
                d, k = to_float(get.get("Density")), to_si.get(m.attrib.get("UnitsOfMeasure", "kg/m3"))
                if d and k and get.get("Name") and get.get("Type"):
                    out.setdefault(f"{get['Type'].lower()}|{get['Name']}", round(d * k, 6))
    return out


# ====================================================================================== CLI
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--build-materials", metavar="SFT_JSONL", help="write data/reward_materials.json")
    ap.add_argument("--answer", help="one model answer (text file)")
    ap.add_argument("--requirements", help="requirements JSON for --answer")
    ap.add_argument("--answers", help="jsonl rows {id, completion[, finish]}")
    ap.add_argument("--prompts", help="data/splits/*.jsonl rows {id, requirements}")
    ap.add_argument("--no-flight", action="store_true", help="stop after the geometry gate (debug)")
    ap.add_argument("--out", help="write per-answer results here (json)")
    a = ap.parse_args()
    if a.build_materials:
        s = build_materials(a.build_materials)
        MATERIALS_PATH.write_text(json.dumps(s, indent=1) + "\n", encoding="utf-8")
        print(f"wrote {MATERIALS_PATH}: {len(s['materials'])} materials")
        return
    kw = dict(flight=not a.no_flight)
    if a.answer:
        rows = [("answer", Path(a.answer).read_text(encoding="utf-8"), json.loads(a.requirements or "{}"), "stop")]
    elif a.answers and a.prompts:
        req = {r["id"]: r.get("requirements", {}) for r in map(json.loads, open(a.prompts, encoding="utf-8"))}
        rows = [(r["id"], r["completion"], req[r["id"]], r.get("finish", "stop"))
                for r in map(json.loads, open(a.answers, encoding="utf-8"))]
    else:
        ap.error("give --answer (with --requirements), --answers with --prompts, or --build-materials")
    results, tally = [], {}
    for rid, text, rq, finish in rows:
        r = {"id": rid, **score(text, rq, finish=finish, **kw)}
        results.append(r)
        tally[r["gate"] or "flew"] = tally.get(r["gate"] or "flew", 0) + 1
        s = "-" if r["score"] is None else f"{r['score']:+.2f}"
        print(f"{rid:<14} {s:>6}  {r['gate'] or 'targets':<9} {'; '.join(r['reasons'])[:100]}", flush=True)
    scored = [r["score"] for r in results if r["score"] is not None]
    print(f"\n{len(results)} answers  {tally}  mean {sum(scored) / len(scored):+.3f}" if scored else tally)
    if a.out:
        Path(a.out).write_text(json.dumps(results, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
