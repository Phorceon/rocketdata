"""Reward ladder for sft_v5-style rocket answers (an OpenRocket tree written as JSON inside <design>).

One answer goes down six gates, cheapest first, and stops at the first gate it fails. Everything here
comes from what is in the repo today: sft/eval_test.py (format and parts checks), sftgen/contract.py
(the safety limits and the 5% "about" tolerance), scripts/json_to_cad.py (CAD) and
scripts/or_headless.py (OpenRocket). There are no weights from the plan document.

  gate            passes when
  1 format        the answer finished, the <design> JSON parses, one "openrocket" root, every node is
                  {tag: {attrs?, value?, children?}}                      (eval_test.v5_tree)
  2 structure     stage, nosecone, bodytube, a fin set, a motormount with a motor are where OpenRocket
                  puts them, and there is a parachute or streamer         (eval_test.v5_tree)
  3 motors        every motor_id is a real motor file, and every motor the prompt names is used
  4 cad           diameters line up, the motor fits its mount, inner tubes fit their parent, fins sit on
                  a body tube, and (needs cadquery) every solid is valid, fins touch the airframe and
                  fin sets do not overlap
  5 flight        OpenRocket loads and flies it; recovery deploys in every section; landing is at most
                  6 m/s (or the prompt's limit); stability at the rail is at least 1 cal and above 0 in
                  the burn; rail exit is at least 15 m/s                    (contract.GATES)
  6 targets       apogee is within the tolerance of the apogee the prompt asks for (5% for "about",
                  one-sided for "at least"/"at most"; skipped when the prompt gives none)

Gate 4 thresholds were set on 249 real .ork designs from ork/ (converted to the v5 tree shape) so reference
designs mostly pass: motor wider than its mount by >5%, inner tube >10% wider than the body bore, nose-to-body
or body-to-body step >1 mm (transitions and "auto" radii are exempt). About 4% of those real designs still
fail gate 4, and they are real mismatches (e.g. a 29 mm motor in a 26.6 mm mount).

Override tags (<overridemass>, <overridecg>, <overridecd>, <overridesubcomponents*>) are removed from the
model's tree before gates 4-6, so mass, CG and drag come from the geometry and materials. Without this a
model could set its own CG (fake stability) or its own drag (fake apogee). The count is in
"stripped_overrides".

Score (the reward ladder in CLAUDE.md):
  -1.0  failed format, structure or motors (bad JSON, missing parts, made-up motor)
  -0.8  failed cad
  -0.5  failed flight (unsafe: stability, landing speed, rail exit, recovery)
  0..1  flew safely: weighted closeness to the prompt's targets. Weights: apogee 0.40, flight time 0.25,
        cost 0.20, landing speed 0.15. A target the prompt does not give is left out and the other
        weights are scaled up. Cost is never scored yet (no price data; see "not_scored").
        Inside the tolerance (5% apogee, 10% time, one-sided for "at least"/"at most") a target scores 1;
        outside it the score falls linearly to 0 at TARGET_FALLOFF past the tolerance. Landing speed
        scores 1 at or below half the limit and 0 at the limit.
The "targets" gate is "pass" when every given target is inside its tolerance, else "miss"; a miss is
not slop, it only lowers the 0..1 score.

A gate that could not run (no cadquery, no OpenRocket, --no-cad, --no-flight) is listed in "unverified"
and the score is None (the would-be number is in "provisional_score"), because a skipped gate could
have failed. reward() raises on None unless allow_unverified=True, so training never gets a fake number.
"slop" = the answer failed a gate it could be checked on (format to flight).

Usage (from the repo root):
    python scripts/reward.py --results RESULTS.json --test VAL.jsonl --motor-lookup LOOKUP.json
    python scripts/reward.py --answer answer.txt --prompt "Design a rocket to about 900 m ..."
    add --no-flight / --no-cad to skip the slow gates; --out FILE to choose the output file.
Python:
    from scripts.reward import score_answer
    r = score_answer(content, prompt, lookup=lookup, finish="stop")
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import re
import sqlite3
import sys
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

GATES = ["format", "structure", "motors", "cad", "flight", "targets"]


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


ev = _load_module("eval_test_for_reward", REPO / "sft" / "eval_test.py")   # the repo's own v5 checks
contract = _load_module("contract_for_reward", REPO / "sftgen" / "contract.py")  # safety limits
LIMITS = contract.GATES
ABOUT_TOL = contract.TOLERANCES["about_rel"]
DEFAULT_COND = {"rail_length_m": contract.DEFAULT_SIM_CONDITIONS["rail_length_m"],
                "wind_ms": contract.DEFAULT_SIM_CONDITIONS["wind_ms"],
                "wind_turbulence": contract.DEFAULT_SIM_CONDITIONS["wind_turbulence"],
                "launch_angle_deg": 0.0, "site_altitude_m": 0.0, "time_step_s": 0.05}

STEP_TOL_M = 0.001      # diameter step between neighbouring body parts
MOTOR_RATIO = 1.05      # motor wider than its mount bore by more than 5% does not fit (18 mm in 16.9 mm = 6.5%)
INNER_TUBE_RATIO = 1.10  # inner tube wider than the body bore by more than 10% (real files go up to ~9.6%)
FIN_GAP_MM = 0.5        # a fin farther than this from the airframe is floating
FIN_CLASH_MM3 = 1.0     # fin sets overlapping by more than this clash

TIER = {"format": -1.0, "structure": -1.0, "motors": -1.0, "cad": -0.8, "flight": -0.5}
WEIGHTS = {"apogee": 0.40, "flight_time": 0.25, "cost": 0.20, "landing": 0.15}
TARGET_FALLOFF = 0.50       # past the tolerance, a target's score reaches 0 this far off (50% of the target)
HARD_MAX_LANDING_MS = 8.0   # Tier 3 limit in CLAUDE.md; a prompt can make it stricter, never looser
ABOUT_TOL_TIME = contract.TOLERANCES["about_rel_time"]
MAX_WIND_MS = LIMITS["max_wind_ms"]
sys.setrecursionlimit(max(sys.getrecursionlimit(), 5000))   # deep trees: to_node / tree_to_xml recurse


# ============================================================================ tree helpers
class Node:
    def __init__(self, tag, attrs=None, text=None, kids=None):
        self.tag, self.attrs, self.text, self.kids = tag, attrs or {}, text, kids or []

    def find(self, tag):
        return next((k for k in self.kids if k.tag == tag), None)

    def findall(self, tag):
        return [k for k in self.kids if k.tag == tag]

    def num(self, tag, default=None, auto=False):
        """Number in a child tag. "auto 0.0125" (OpenRocket follows the neighbour; the number can be stale)
        is None unless auto=True."""
        k = self.find(tag)
        if k is None or k.text is None:
            return default
        v = k.text.strip().split()
        if v and v[0] == "auto" and not auto:
            return default
        try:
            return float(v[-1]) if v else default
        except ValueError:
            return default

    def val(self, tag, default=None):
        k = self.find(tag)
        return default if k is None or k.text is None else k.text.strip()

    def parts(self):
        sub = self.find("subcomponents")
        return sub.kids if sub is not None else []


def to_node(tag, body):
    if not isinstance(body, dict):
        return Node(tag, text=str(body))
    ch = body.get("children") or []
    if isinstance(ch, dict):
        ch = [{k: v} for k, v in ch.items()]
    kids = [to_node(k, v) for c in (ch if isinstance(ch, list) else []) if isinstance(c, dict) for k, v in c.items()]
    val = body.get("value")
    attrs = body.get("attrs") if isinstance(body.get("attrs"), dict) else {}
    return Node(tag, attrs, None if val is None else str(val), kids)


def tree_to_xml(node: Node) -> str:
    attrs = "".join(f" {k}={quoteattr(str(v))}" for k, v in node.attrs.items())
    if not node.kids and node.text is None:
        return f"<{node.tag}{attrs}/>"
    inner = escape(node.text) if node.text is not None else ""
    return f"<{node.tag}{attrs}>{inner}{''.join(tree_to_xml(k) for k in node.kids)}</{node.tag}>"


def _inner_r(n: Node):
    """(outer radius, inner radius) of a body tube or inner tube, None when unknown."""
    r = n.num("radius") if n.tag == "bodytube" else n.num("outerradius")
    if not r:
        return None, None
    t = n.val("thickness")
    if t == "filled":
        return r, 0.0
    try:
        return r, r - float(t or 0.0)
    except ValueError:
        return r, r


# ============================================================================ gates 1-2 (format, structure)
def last_design(content):
    return ev.last_design(content or "")


def gate_format(content, finish):
    """Returns (design_dict or None, reason or None)."""
    if finish == "length":
        return None, "ran out of tokens (looped or never finished)"
    if finish == "error":
        return None, "the request itself failed"
    body = last_design(content)
    if body is None:
        return None, "no complete <design>...</design> block (cut off or missing closing tag)"
    try:
        design = json.loads(body)
    except (ValueError, RecursionError) as e:
        return None, f"design JSON does not parse: {str(e)[:80]}"
    if not isinstance(design, dict):
        return None, "design JSON is not an object"
    if "openrocket" not in design:
        return None, "no \"openrocket\" root (not the OpenRocket tree format)"
    ok, _, _ = ev.v5_tree(design)
    if not ok:
        extra = [k for k in design if k != "openrocket"]
        if extra:
            return None, f"root closed early: {extra} sits next to \"openrocket\" instead of inside it"
        return None, "tree is malformed: a node is not {tag: {attrs?, value?, children?}}"
    try:
        to_node("openrocket", design["openrocket"])
    except RecursionError:
        return None, "tree is nested too deep"
    return design, None


def strip_overrides(body) -> int:
    """Remove every override* child from the v5 tree in place. Returns how many were removed.

    Mass, CG and drag must come from the parts, not from numbers the model writes: an <overridecg> can
    move the CG forward (fake stability) and an <overridecd> can tune the drag to hit the apogee."""
    n = 0
    stack = [body]
    while stack:
        b = stack.pop()
        if not isinstance(b, dict):
            continue
        ch = b.get("children")
        if isinstance(ch, dict):
            ch = b["children"] = [{k: v} for k, v in ch.items()]
        if not isinstance(ch, list):
            continue
        keep = []
        for c in ch:
            if isinstance(c, dict) and len(c) == 1 and next(iter(c)).lower().startswith("override"):
                n += 1
                continue
            keep.append(c)
            if isinstance(c, dict):
                stack.extend(c.values())
        b["children"] = keep
    return n


def gate_structure(design):
    ok, placed, motors = ev.v5_tree(design)
    missing = sorted(ev.V5_REQUIRED - placed)
    if not (placed & ev.V5_FINSETS):
        missing.append("fin set")
    if missing:
        return None, "parts missing or in the wrong place: " + ", ".join(missing)
    if not (placed & {"parachute", "streamer"}):
        return None, "no parachute or streamer in the stage"
    return motors, None


# ============================================================================ gate 3 (motors)
_CATALOG = None


def catalog_designations():
    global _CATALOG
    if _CATALOG is None:
        db = REPO / "data" / "catalog.sqlite"
        _CATALOG = set()
        if db.exists():
            with sqlite3.connect(db) as c:
                _CATALOG = {r[0] for r in c.execute("select designation from motors")}
    return _CATALOG


def gate_motors(motors, prompt, lookup):
    """motors: [(motor_id, designation)]. With a lookup the motor_id must be in it; without one only the
    designation is checked against data/catalog.sqlite, which is weaker (and reported as such)."""
    if not motors:
        return None, "no motor in the design", "none"
    bad = []
    if lookup:
        for mid, des in motors:
            if mid not in lookup:
                bad.append(mid or des or "?")
        mode = "lookup"
    else:
        cat = catalog_designations()
        for mid, des in motors:
            if (des or "") not in cat:
                bad.append(des or mid or "?")
        mode = "catalog-designation (weak: pass --motor-lookup for the real check)"
    if bad:
        return None, "made-up or unknown motor(s): " + ", ".join(sorted(set(map(str, bad)))), mode
    for w in ev.asked_motors(prompt):
        used = any(w in (des, (lookup or {}).get(mid, {}).get("designation")) or (mid or "").endswith("-" + w)
                   for mid, des in motors)
        if not used:
            return None, f"prompt asks for motor {w} but the design does not use it", mode
    return True, None, mode


# ============================================================================ gate 4 (cad)
def fit_problems(root: Node):
    """Numeric fit checks straight on the tree (no CAD library needed)."""
    out = []
    flown = _config_id(root)

    def visit(n: Node):
        items = n.parts()
        struct = [c for c in items if c.tag in ("nosecone", "bodytube", "transition")]
        for a, b in zip(struct, struct[1:]):
            # nose cone -> body and body -> body only: transitions legitimately change diameter, and
            # "auto" radii follow their neighbour, so they never step
            if (a.tag, b.tag) not in (("nosecone", "bodytube"), ("bodytube", "bodytube")):
                continue
            aft = a.num("aftradius") if a.tag == "nosecone" else a.num("radius")
            fore = b.num("radius")
            if aft and fore and abs(aft - fore) * 2 > STEP_TOL_M:
                out.append(f"diameter step of {abs(aft - fore) * 2000:.1f} mm between {a.tag} and {b.tag}")
        for c in items:
            if c.tag in ev.V5_FINSETS:
                if n.tag in ("parachute", "streamer", "masscomponent"):
                    out.append(f"{c.tag} is attached to a {n.tag}, not a body tube")
                if (c.num("fincount") or c.num("instancecount") or 0) < 1:
                    out.append(f"{c.tag} has no fins")
                if c.tag in ("trapezoidfinset", "ellipticalfinset") and ((c.num("height") or 0) <= 0 or (c.num("rootchord") or 0) <= 0):
                    out.append(f"{c.tag} has zero height or root chord")
            if c.tag == "innertube":
                if n.tag == "bodytube":
                    _, pin = _inner_r(n)
                    cr, _ = _inner_r(c)
                    if pin and cr and cr > pin * INNER_TUBE_RATIO:
                        out.append(f"inner tube {cr * 2000:.1f} mm wider than its parent bore {pin * 2000:.1f} mm")
        mm = n.find("motormount")
        if mm is not None and n.tag in ("bodytube", "innertube"):
            _, inner = _inner_r(n)
            for m in mm.findall("motor"):
                if flown and m.attrs.get("configid") not in (None, flown):
                    continue        # leftover motor of a configuration that is not flown
                d = m.num("diameter")
                if d and inner and inner > 0.002 and d > inner * 2 * MOTOR_RATIO:
                    out.append(f"{d * 1000:.1f} mm motor does not fit a {inner * 2000:.1f} mm mount")
        for k in n.kids:
            visit(k)

    sys.setrecursionlimit(max(sys.getrecursionlimit(), 5000))
    visit(root)
    return sorted(set(out))


def cad_problems(design_body):
    """Solid checks with cadquery via scripts/json_to_cad.py. Returns (problems, skipped_reason)."""
    try:
        import json_to_cad as j2c  # needs cadquery
    except Exception as e:  # ImportError, or a broken cadquery install
        return [], f"cadquery not available ({type(e).__name__})"
    probs = []
    try:
        d = j2c.normalise({"openrocket": design_body})
        db_path = REPO / "data" / "catalog.sqlite"
        db = sqlite3.connect(db_path) if db_path.exists() else None
        b = j2c.Builder(db, None)
        b.build_design(d)
    except Exception as e:
        return [f"CAD build failed: {type(e).__name__}: {str(e)[:100]}"], None
    if not b.parts:
        return ["design produced no geometry"], None
    for w in b.warn:
        if ": skipped (" in w:
            probs.append(f"part failed to build: {w[:100]}")
    for p in b.parts:
        try:
            if not p["shape"].isValid():
                probs.append(f"invalid solid: {p['name']}")
            elif p["shape"].Volume() <= 0:
                probs.append(f"empty or inside-out solid: {p['name']}")
        except Exception as e:
            probs.append(f"could not check solid {p['name']}: {type(e).__name__}")
    try:
        import cadquery as cq
        air = [p["shape"] for p in b.parts if p["cat"] in ("nosecone", "bodytube", "transition")]
        fins = [p for p in b.parts if p["cat"] == "fin" and ":" not in p["name"]]   # pod fins sit on pods
        if air and fins:
            airframe = cq.Compound.makeCompound(air)
            floating = {p["name"].rsplit(" ", 1)[0] for p in fins if p["shape"].distance(airframe) > FIN_GAP_MM}
            probs += [f"fins not attached to the airframe: {n}" for n in sorted(floating)]
        sets = {}
        for p in fins:
            sets.setdefault(p["name"].rsplit(" ", 1)[0], []).append(p["shape"])
        names = sorted(sets)
        for i, a in enumerate(names):
            for c in names[i + 1:]:
                if any(x.intersect(y).Volume() > FIN_CLASH_MM3 for x in sets[a] for y in sets[c]):
                    probs.append(f"fin sets overlap: {a} and {c}")
    except Exception as e:
        return probs, f"fin checks skipped ({type(e).__name__}: {str(e)[:60]})" if not probs else None
    return probs, None


# ============================================================================ gate 5 (flight)
SIM_XML = (
    '<simulations><simulation status="outdated"><name>reward</name><simulator>RK4Simulator</simulator>'
    '<calculator>BarrowmanCalculator</calculator><conditions><configid>{cid}</configid>'
    '<launchrodlength>{rail}</launchrodlength><launchrodangle>{ang}</launchrodangle>'
    '<launchroddirection>90.0</launchroddirection><windaverage>{wind}</windaverage>'
    '<windturbulence>{turb}</windturbulence><launchaltitude>{alt}</launchaltitude>'
    '<launchlatitude>28.61</launchlatitude><launchlongitude>-80.6</launchlongitude>'
    '<geodeticmethod>spherical</geodeticmethod><atmosphere model="isa"/><timestep>{dt}</timestep>'
    '</conditions></simulation></simulations>')


def _config_id(root: Node):
    found = []

    def walk(n):
        if n.tag in ("motorconfiguration", "motor") and n.attrs.get("configid"):
            found.append((n.tag == "motorconfiguration" and n.attrs.get("default") == "true",
                          n.tag == "motorconfiguration", n.attrs["configid"]))
        for k in n.kids:
            walk(k)
    walk(root)
    if found:                       # the default flight configuration, else the first one written
        return sorted(found, key=lambda f: (not f[0], not f[1]))[0][2]
    sims = root.find("simulations")           # fall back to the model's own simulation block
    if sims is not None:
        for s in sims.findall("simulation"):
            c = s.find("conditions")
            if c is not None and c.val("configid"):
                return c.val("configid")
    return None


def design_to_ork_xml(design, cond):
    """The model's tree, with its own simulation block thrown away and a standard one put in."""
    root = to_node("openrocket", design["openrocket"])
    cid = _config_id(root)
    if not cid:
        raise ValueError("no flight configuration id (no motor with a configid)")
    root.kids = [k for k in root.kids if k.tag != "simulations"]
    attrs = dict(root.attrs)
    attrs.setdefault("version", "1.10")
    attrs.setdefault("creator", "OpenRocket 24.12")
    root.attrs = attrs
    xml = tree_to_xml(root)
    sim = SIM_XML.format(cid=escape(cid), rail=cond["rail_length_m"], ang=cond["launch_angle_deg"],
                         wind=cond["wind_ms"], turb=cond["wind_turbulence"], alt=cond["site_altitude_m"],
                         dt=cond["time_step_s"])
    return "<?xml version='1.0' encoding='utf-8'?>\n" + xml[: -len("</openrocket>")] + sim + "</openrocket>"


def run_openrocket(ork_path, seed=0, max_time_s=3600.0):
    """Fly the first simulation in the file. Returns a dict shaped like sftgen.tools.simulate's output."""
    import or_headless as orh
    import jpype

    orh._boot_or()
    OrBatch = jpype.JClass("OrBatch")
    Loader = jpype.JClass("info.openrocket.core.file.GeneralRocketLoader")
    File = jpype.JClass("java.io.File")
    T = jpype.JClass("info.openrocket.core.simulation.FlightDataType")
    Ev = jpype.JClass("info.openrocket.core.simulation.FlightEvent$Type")
    OrBatch.seedUUID(orh.UUID_SEED)
    doc = Loader(File(str(ork_path))).load()
    if doc.getSimulationCount() < 1:
        raise ValueError("OpenRocket found no simulation in the file")
    sim = doc.getSimulation(0)
    OrBatch.reseed(sim.getOptions(), int(seed))
    sim.getOptions().setMaxSimulationTime(float(max_time_s))
    sim.simulate()
    sd = sim.getSimulatedData()
    main = sd.getBranch(0)
    times, stab = list(main.get(T.TYPE_TIME)), list(main.get(T.TYPE_STABILITY))
    rod_t = burn_t = None
    for e in main.getEvents():
        if e.getType() == Ev.LAUNCHROD and rod_t is None:
            rod_t = float(e.getTime())
        if e.getType() == Ev.BURNOUT:
            burn_t = float(e.getTime())
    rail_stab = next((float(s) for t, s in zip(times, stab) if rod_t is not None and t >= rod_t and math.isfinite(s)), None)
    burn = [float(s) for t, s in zip(times, stab) if rod_t is not None and burn_t is not None
            and rod_t <= t <= burn_t and math.isfinite(s)]
    sections = []
    for bi in range(sd.getBranchCount()):
        br = sd.getBranch(bi)
        vz = list(br.get(T.TYPE_VELOCITY_Z))
        deployed = ground = False
        for e in br.getEvents():
            deployed |= e.getType() == Ev.RECOVERY_DEVICE_DEPLOYMENT
            ground |= e.getType() == Ev.GROUND_HIT
        sections.append({"name": str(br.getName()), "reached_ground": ground, "recovery_deployed": deployed,
                         "landing_ms": abs(float(vz[-1])) if vz and math.isfinite(vz[-1]) else None})
    return {"apogee_m": float(sd.getMaxAltitude()), "flight_time_s": float(sd.getFlightTime()),
            "rail_exit_ms": float(sd.getLaunchRodVelocity()), "stability_rail_exit_cal": rail_stab,
            "min_stability_burn_cal": min(burn) if burn else rail_stab, "sections": sections}


_SPEED = re.compile(r"(\d+(?:\.\d+)?)\s*(m/s|mph|ft/s|fps)\b", re.I)
_SPEED_UNIT = {"m/s": 1.0, "mph": 0.44704, "ft/s": 0.3048, "fps": 0.3048}
_LANDING_WORDS = re.compile(r"land|touch|descen|impact|come[s]? (?:down|in)|ground|hit", re.I)
_WIND_WORDS = re.compile(r"wind|breeze|gust", re.I)


def _speeds(prompt):
    """(m/s, text before, text after) for every speed in the prompt."""
    for m in _SPEED.finditer(prompt):
        yield (float(m.group(1)) * _SPEED_UNIT[m.group(2).lower()],
               prompt[max(0, m.start() - 40): m.start()], prompt[m.end(): m.end() + 12])


def _is_wind(before, after):
    """A speed is a wind figure when a wind word is right after it, or is the last cue word before it."""
    if _WIND_WORDS.match(after.strip()):
        return True
    cues = [(m.start(), "w") for m in _WIND_WORDS.finditer(before)] + \
           [(m.start(), "l") for m in _LANDING_WORDS.finditer(before)]
    return bool(cues) and max(cues)[1] == "w"


def landing_limit(prompt):
    """The landing speed limit: the prompt's limit when it gives one, else the contract default (6 m/s),
    never above HARD_MAX_LANDING_MS. Only a speed near a landing word counts (not the wind speed)."""
    asked = [v for v, before, after in _speeds(prompt)
             if not _is_wind(before, after) and _LANDING_WORDS.search(before)]
    lim = min(asked) if asked else LIMITS["default_max_landing_ms"]
    return min(lim, HARD_MAX_LANDING_MS)


def asked_wind(prompt):
    """Wind speed the prompt gives (m/s, capped at the contract's 20 mph), else None."""
    for v, before, after in _speeds(prompt):
        if _is_wind(before, after):
            return min(v, MAX_WIND_MS)
    return None


def flight_problems(sim, limit):
    out = []
    secs = sim.get("sections") or []
    if not secs:
        out.append("no flight sections")
    for s in secs:
        n = s["name"]
        if not s["recovery_deployed"]:
            out.append(f"{n}: recovery never deployed")
        if not s["reached_ground"]:
            out.append(f"{n}: never reached the ground in the simulated time")
        elif s["landing_ms"] is None:
            out.append(f"{n}: landing speed unavailable")
        elif s["landing_ms"] > limit:
            out.append(f"{n}: lands at {s['landing_ms']:.1f} m/s (limit {limit:g})")
    st, bst = sim.get("stability_rail_exit_cal"), sim.get("min_stability_burn_cal")
    if st is None or st < LIMITS["min_launch_margin_cal"]:
        out.append(f"stability at the rail is {'unknown' if st is None else f'{st:.2f}'} cal (needs >= {LIMITS['min_launch_margin_cal']:g})")
    if bst is not None and bst <= LIMITS["min_burn_margin_cal"]:
        out.append(f"stability drops to {bst:.2f} cal during the burn")
    if sim["rail_exit_ms"] < LIMITS["min_rail_exit_ms"]:
        out.append(f"rail exit {sim['rail_exit_ms']:.1f} m/s (needs >= {LIMITS['min_rail_exit_ms']:g})")
    return out


# ============================================================================ gate 6 (targets)
UNIT_M = {"m": 1.0, "meter": 1.0, "meters": 1.0, "metre": 1.0, "metres": 1.0, "km": 1000.0,
          "ft": 0.3048, "foot": 0.3048, "feet": 0.3048}


_LEN = re.compile(r"(?P<num>\d[\d,]*(?:\.\d+)?)\s*(?P<unit>km|meters?|metres?|feet|foot|ft|m)\b(?!/)", re.I)
_NOT_ALTITUDE = re.compile(r"^\s*(?:rail|long|length|tall|wide|diameter|body|tube|payload|field|radius|of drift|drift)", re.I)
_ALT_WORDS = re.compile(r"apogee|altitude|reach|clear|height|go up to|goes? to|get to|hit|up to|exceed", re.I)


_TAIL = r"\s*(?:of |to |a |an |about |around )?$"     # the qualifier has to sit right in front of the number
_MIN_Q = re.compile(r"(?:at least|minimum|min|clear|over|above|more than|longer than|exceed\w*)" + _TAIL)
_MAX_Q = re.compile(r"(?:under|below|at most|no more than|max|maximum|within|less than|shorter than|"
                    r"no longer than|up to)" + _TAIL)


def _kind(before):
    before = before.lower()
    if _MIN_Q.search(before):
        return "min"
    if _MAX_Q.search(before):
        return "max"
    return "about"


def asked_apogees(prompt):
    """Every altitude goal in a prompt as [(metres, kind)], kind: about | min | max.

    A length counts when an altitude word sits just before or after it. If no length has one, the first
    length of 30 m or more that is not a rail/length/diameter figure counts. "Stay below 500 ft apogee,
    about 120 m" gives both goals; the score takes the worst of them."""
    near, far = [], []
    for m in _LEN.finditer(prompt):
        v = float(m.group("num").replace(",", "")) * UNIT_M[m.group("unit").lower()]
        before, after = prompt[max(0, m.start() - 30): m.start()], prompt[m.end(): m.end() + 14]
        if _NOT_ALTITUDE.match(after):
            continue
        is_near = bool(_ALT_WORDS.search(before) or re.match(r"\s*(?:apogee|altitude)", after, re.I))
        if is_near and v >= 5:
            near.append((v, _kind(before[-16:])))
        elif v >= 30:
            far.append((v, _kind(before[-16:])))
    return near or far[:1]


def asked_apogee(prompt):
    """The first altitude goal, (metres, kind), else None (kept for callers of the old API)."""
    a = asked_apogees(prompt)
    return a[0] if a else None


_WORD_NUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
             "nine": 9, "ten": 10, "a": 1, "half a": 0.5}
_TIME = re.compile(r"(?P<num>\d+(?:\.\d+)?|half a|one|two|three|four|five|six|seven|eight|nine|ten|a)\s*"
                   r"(?P<unit>minutes?|mins?|seconds?|secs?|s)\b(?!/)", re.I)
_NOT_FLIGHT_TIME = re.compile(r"burn|delay|ejection|coast|thrust|to apogee", re.I)


def asked_flight_time(prompt):
    """(seconds, kind) for the total flight time a prompt asks for, else None. kind: about | min | max."""
    for m in _TIME.finditer(prompt):
        raw = m.group("num").lower()
        v = _WORD_NUM[raw] if raw in _WORD_NUM else float(raw)
        if m.group("unit").lower().startswith("m"):
            v *= 60.0
        before, after = prompt[max(0, m.start() - 40): m.start()], prompt[m.end(): m.end() + 14]
        if _NOT_FLIGHT_TIME.search(before[-20:]) or _NOT_FLIGHT_TIME.match(after.strip()):
            continue
        if raw == "a" and not re.search(r"(?:under|within|in|about|around|near) $", before.lower()):
            continue                     # "a s..." or "a min..." in ordinary words
        if v <= 0:
            continue
        return v, _kind(before[-20:])
    return None


def closeness(got, want, kind, tol):
    """1 inside the tolerance, then linear down to 0 at TARGET_FALLOFF past it."""
    if kind == "min":
        off = max(0.0, (want - got) / want)
    elif kind == "max":
        off = max(0.0, (got - want) / want)
    else:
        off = max(0.0, abs(got - want) / want - tol)
    return max(0.0, 1.0 - off / TARGET_FALLOFF)


def target_scores(sim, prompt, limit):
    """({component: 0..1}, problems, asked). Components the prompt does not give are left out."""
    comps, probs, asked = {}, [], {}
    got = sim["apogee_m"]
    apos = asked_apogees(prompt)
    if apos:
        asked["apogee_m"] = apos
        comps["apogee"] = min(closeness(got, v, k, ABOUT_TOL) for v, k in apos)
        for v, k in apos:
            if k == "min" and got < v:
                probs.append(f"apogee {got:.0f} m is below the {v:.0f} m asked for")
            elif k == "max" and got > v:
                probs.append(f"apogee {got:.0f} m is above the {v:.0f} m limit")
            elif k == "about" and abs(got - v) > ABOUT_TOL * v:
                probs.append(f"apogee {got:.0f} m is {100 * (got - v) / v:+.0f}% from the {v:.0f} m asked for "
                             f"(tolerance {ABOUT_TOL:.0%})")
    ft = asked_flight_time(prompt)
    if ft:
        v, k = ft
        t = sim["flight_time_s"]
        asked["flight_time_s"] = ft
        comps["flight_time"] = closeness(t, v, k, ABOUT_TOL_TIME)
        if comps["flight_time"] < 1.0:
            probs.append(f"flight time {t:.1f} s misses the {k} {v:g} s asked for")
    lands = [s["landing_ms"] for s in sim["sections"] if s["landing_ms"] is not None]
    if lands:
        comps["landing"] = max(0.0, min(1.0, (limit - max(lands)) / (0.5 * limit)))
    return comps, probs, asked


def tier4_score(comps):
    """Weighted mean of the components present, weights rescaled to sum to 1."""
    w = {k: WEIGHTS[k] for k in comps}
    tot = sum(w.values())
    return round(sum(comps[k] * w[k] for k in comps) / tot, 4) if tot else 0.0


# ============================================================================ the ladder
def score_answer(content, prompt, lookup=None, finish="stop", flight=True, cad=True, cond=None, seed=0):
    """Run the ladder on one answer. cond overrides the sim conditions; the prompt's wind is used when the
    prompt gives one and cond does not set wind_ms."""
    cond = dict(cond or {})
    if "wind_ms" not in cond and asked_wind(prompt) is not None:
        cond["wind_ms"] = asked_wind(prompt)
    cond = {**DEFAULT_COND, **cond}
    res = {"gate_failed": None, "reasons": [], "gates": {g: "not reached" for g in GATES}, "unverified": [],
           "score": None, "provisional_score": None, "tier": None, "components": {}, "not_scored": ["cost"],
           "slop": False, "metrics": {}, "motor_check": None, "stripped_overrides": 0}
    skipped = []                    # gates that could not run, in ladder order

    def finish_up(score, tier):
        res["tier"], res["provisional_score"] = tier, score
        failed = res["gate_failed"]
        # a failure before the first skipped gate is real; anything after a skipped gate is not verified
        ok = not skipped or (failed is not None and GATES.index(failed) < GATES.index(skipped[0]))
        res["score"] = score if ok else None
        return res

    def fail(gate, reasons):
        res["gate_failed"], res["reasons"], res["gates"][gate] = gate, list(reasons), "FAIL"
        res["slop"] = True
        return finish_up(TIER[gate], {"format": 1, "structure": 1, "motors": 1, "cad": 2, "flight": 3}[gate])

    def skip(gate, why):
        skipped.append(gate)
        res["gates"][gate] = "skipped"
        res["unverified"].append(f"{gate}: {why}")

    design, why = gate_format(content, finish)
    if why:
        return fail("format", [why])
    res["gates"]["format"] = "pass"

    motors, why = gate_structure(design)
    if why:
        return fail("structure", [why])
    res["gates"]["structure"] = "pass"

    ok, why, mode = gate_motors(motors, prompt, lookup)
    res["motor_check"] = mode
    if why:
        return fail("motors", [why])
    res["gates"]["motors"] = "pass"

    res["stripped_overrides"] = strip_overrides(design["openrocket"])
    probs = fit_problems(to_node("openrocket", design["openrocket"]))
    cad_skip = "skipped by --no-cad"
    if cad:
        cprobs, cad_skip = cad_problems(design["openrocket"])
        probs += cprobs
    if probs:
        return fail("cad", probs)
    if cad_skip:
        skip("cad", f"solid checks not run ({cad_skip}); fit checks passed")
    else:
        res["gates"]["cad"] = "pass"

    if not flight:
        skip("flight", "skipped by --no-flight")
        skip("targets", "needs the flight")
        return finish_up(None, None)
    try:
        xml = design_to_ork_xml(design, cond)
    except Exception as e:
        return fail("flight", [f"cannot build an .ork from the tree: {e}"])
    fd, path = tempfile.mkstemp(suffix=".ork", prefix="reward_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(xml)
        try:
            sim = run_openrocket(path, seed)
        except (ImportError, FileNotFoundError) as e:
            skip("flight", f"OpenRocket not available ({e})")
            skip("targets", "needs the flight")
            return finish_up(None, None)
        except Exception as e:
            return fail("flight", [f"OpenRocket could not load or fly it: {str(e).splitlines()[0][:160] if str(e) else type(e).__name__}"])
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
    res["metrics"] = {k: sim[k] for k in ("apogee_m", "flight_time_s", "rail_exit_ms", "stability_rail_exit_cal",
                                           "min_stability_burn_cal")}
    res["metrics"]["landing_ms"] = [s["landing_ms"] for s in sim["sections"]]
    res["metrics"]["wind_ms"] = cond["wind_ms"]
    limit = landing_limit(prompt)
    res["metrics"]["landing_limit_ms"] = limit
    fp = flight_problems(sim, limit)
    if fp:
        return fail("flight", fp)
    res["gates"]["flight"] = "pass"

    comps, tp, asked = target_scores(sim, prompt, limit)
    res["components"], res["metrics"]["asked"] = comps, asked
    res["gates"]["targets"] = "miss" if tp else "pass"
    res["reasons"] = tp
    return finish_up(tier4_score(comps), 4)


def reward(content, prompt, allow_unverified=False, **kw) -> float:
    """The single number for a training loop, in [-1, 1]. Raises when a gate could not run (no cadquery,
    no OpenRocket), because then the number is not real; allow_unverified=True returns the provisional one."""
    r = score_answer(content, prompt, **kw)
    if r["score"] is None:
        if allow_unverified:
            return r["provisional_score"] if r["provisional_score"] is not None else 0.0
        raise RuntimeError("reward not verified: " + "; ".join(r["unverified"]))
    return r["score"]


# ============================================================================ batch / CLI
def summarize(results):
    n = len(results)
    by = {g: sum(1 for r in results if r["gate_failed"] == g) for g in GATES if g != "targets"}
    flown = [r for r in results if r["tier"] == 4]
    scored = [r["score"] for r in results if r["score"] is not None]
    return {"n": n, "slop": sum(r["slop"] for r in results), "failed_at_gate": by,
            "flew_safely": len(flown), "met_every_target": sum(1 for r in flown if r["gates"]["targets"] == "pass"),
            "unverified": sum(1 for r in results if r["score"] is None),
            "mean_score": round(sum(scored) / len(scored), 3) if scored else None}


def print_summary(s):
    print(f"\n{s['n']} answers, slop (failed a gate): {s['slop']}")
    for g, k in s["failed_at_gate"].items():
        print(f"  fails at {g:<10} {k}")
    print(f"  flew safely: {s['flew_safely']}  (met every target: {s['met_every_target']})")
    print(f"  mean score: {s['mean_score']}  (-1 / -0.8 / -0.5 / 0..1 ladder; {s['unverified']} unverified "
          f"answers left out)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", help="results_<label>.json written by sft/eval_test.py")
    ap.add_argument("--test", help="the prompts file those answers were generated from (jsonl)")
    ap.add_argument("--answer", help="one raw model answer (text file)")
    ap.add_argument("--prompt", help="the prompt for --answer")
    ap.add_argument("--motor-lookup", help="new_results/sft_v4_motor_lookup.json (branch sft-v5-data)")
    ap.add_argument("--no-flight", action="store_true")
    ap.add_argument("--no-cad", action="store_true")
    ap.add_argument("--wind", type=float, help="wind m/s (default: the prompt's wind, else 2.0)")
    ap.add_argument("--rail", type=float, help="rail length m (default 1.5)")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", help="where to write the per-answer results (json)")
    a = ap.parse_args()
    lookup = json.loads(Path(a.motor_lookup).read_text(encoding="utf-8")) if a.motor_lookup else None
    cond = {k: v for k, v in (("wind_ms", a.wind), ("rail_length_m", a.rail)) if v is not None}
    kw = dict(lookup=lookup, flight=not a.no_flight, cad=not a.no_cad, cond=cond)

    results = []
    if a.answer:
        r = score_answer(Path(a.answer).read_text(encoding="utf-8"), a.prompt or "", **kw)
        r["id"] = Path(a.answer).name
        results.append(r)
    elif a.results and a.test:
        rows = {row["id"]: row for row in ev.load_rows(a.test)}
        saved = json.loads(Path(a.results).read_text(encoding="utf-8"))["results"]
        for old in saved[: a.limit or None]:
            _, content = ev.split_output(old)
            finish = old.get("finish") or ("error" if old.get("error") else ("length" if old.get("truncated") else "stop"))
            r = score_answer(content, rows[old["id"]]["messages"][1]["content"], finish=finish, **kw)
            r["id"] = old["id"]
            results.append(r)
            print(f"{r['id']:<22} {'ok' if not r['slop'] else 'SLOP at ' + r['gate_failed']:<18} "
                  f"{'unverified' if r['score'] is None else format(r['score'], '+.2f'):>10}  "
                  f"{'; '.join(r['reasons'])[:110]}", flush=True)
    else:
        ap.error("give --answer (with --prompt) or --results and --test")
    s = summarize(results)
    print_summary(s)
    uv = sorted({u for r in results for u in r["unverified"]})
    if uv:
        print("not verified:", "; ".join(uv))
    if a.out or a.results:
        out = a.out or str(Path(a.results).with_name("reward_" + Path(a.results).name))
        Path(out).write_text(json.dumps({"summary": s, "results": results}, indent=1), encoding="utf-8")
        print("wrote", out)


if __name__ == "__main__":
    main()
