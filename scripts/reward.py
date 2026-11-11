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

Result per answer: the first gate it failed (None if it cleared all), the reasons, per-gate status, and
score = gates passed / 6. A gate that could not run (no cadquery, no OpenRocket) is marked "skipped",
counts as not passed, and is listed in "unverified" so a partial score is never read as a full one.
"slop" = the answer failed a gate it could be checked on.

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
    return design, None


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


def landing_limit(prompt):
    m = re.search(r"(?:under|below|less than|at most|no more than|max(?:imum)?(?: of)?|<)\s*(?:about |around )?"
                  r"(\d+(?:\.\d+)?)\s*m/s", prompt, re.I)
    return float(m.group(1)) if m else LIMITS["default_max_landing_ms"]


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


def asked_apogee(prompt):
    """(metres, kind) for the altitude goal in a prompt, else None. kind: about | min | max.

    A length counts when an altitude word sits just before or after it, or, failing that, when it is 30 m
    or more and not a rail/length/diameter figure. Ambiguous prompts return None and skip the target gate."""
    cands = []
    for m in _LEN.finditer(prompt):
        v = float(m.group("num").replace(",", "")) * UNIT_M[m.group("unit").lower()]
        before, after = prompt[max(0, m.start() - 30): m.start()], prompt[m.end(): m.end() + 14]
        if _NOT_ALTITUDE.match(after):
            continue
        near = bool(_ALT_WORDS.search(before) or re.match(r"\s*(?:apogee|altitude)", after, re.I))
        if near and v >= 5 or v >= 30:
            cands.append((not near, m.start(), v, before[-14:].lower()))
    if not cands:
        return None
    _, _, v, before = sorted(cands)[0]
    tail = r"\s*(?:of |to |a |an )?$"            # the qualifier has to sit right in front of the number
    if re.search(r"(?:at least|minimum|min|clear|over|above|more than|exceed\w*)" + tail, before):
        return v, "min"
    if re.search(r"(?:under|below|at most|no more than|max|maximum)" + tail, before):
        return v, "max"
    return v, "about"


def target_problems(sim, prompt):
    want = asked_apogee(prompt)
    if not want:
        return [], None
    v, kind = want
    got = sim["apogee_m"]
    if kind == "min" and got < v:
        return [f"apogee {got:.0f} m is below the {v:.0f} m asked for"], want
    if kind == "max" and got > v:
        return [f"apogee {got:.0f} m is above the {v:.0f} m limit"], want
    if kind == "about" and abs(got - v) > ABOUT_TOL * v:
        return [f"apogee {got:.0f} m is {100 * (got - v) / v:+.0f}% from the {v:.0f} m asked for (limit {ABOUT_TOL:.0%})"], want
    return [], want


# ============================================================================ the ladder
def score_answer(content, prompt, lookup=None, finish="stop", flight=True, cad=True, cond=None, seed=0):
    cond = {**DEFAULT_COND, **(cond or {})}
    res = {"gate_failed": None, "reasons": [], "gates": {g: "not reached" for g in GATES}, "unverified": [],
           "score": 0.0, "slop": False, "metrics": {}, "motor_check": None}

    def fail(gate, reasons):
        res["gate_failed"], res["reasons"], res["gates"][gate] = gate, list(reasons), "FAIL"
        res["slop"] = True
        return finish_up()

    def finish_up():
        passed = sum(1 for g in GATES if res["gates"][g].startswith("pass"))
        res["score"] = round(passed / len(GATES), 3)
        return res

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

    probs = fit_problems(to_node("openrocket", design["openrocket"]))
    if cad:
        cprobs, skipped = cad_problems(design["openrocket"])
        probs += cprobs
        if skipped:
            res["unverified"].append(f"cad solids: {skipped}")
    else:
        res["unverified"].append("cad solids: skipped by --no-cad")
    if probs:
        return fail("cad", probs)
    res["gates"]["cad"] = "pass" if not any(u.startswith("cad solids") for u in res["unverified"]) else "pass (fit checks only)"

    if not flight:
        res["unverified"].append("flight: skipped by --no-flight")
        res["gates"]["flight"] = res["gates"]["targets"] = "skipped"
        return finish_up()
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
        except ImportError as e:
            res["unverified"].append(f"flight: OpenRocket not available ({e})")
            res["gates"]["flight"] = res["gates"]["targets"] = "skipped"
            return finish_up()
        except FileNotFoundError as e:
            res["unverified"].append(f"flight: {e}")
            res["gates"]["flight"] = res["gates"]["targets"] = "skipped"
            return finish_up()
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
    fp = flight_problems(sim, landing_limit(prompt))
    if fp:
        return fail("flight", fp)
    res["gates"]["flight"] = "pass"

    tp, want = target_problems(sim, prompt)
    res["metrics"]["asked_apogee_m"] = want[0] if want else None
    if tp:
        return fail("targets", tp)
    res["gates"]["targets"] = "pass"
    return finish_up()


def reward(content, prompt, **kw) -> float:
    """The single number for a training loop. Only comparable between runs with the same gates enabled."""
    return score_answer(content, prompt, **kw)["score"]


# ============================================================================ batch / CLI
def summarize(results):
    n = len(results)
    by = {g: sum(1 for r in results if r["gate_failed"] == g) for g in GATES}
    cleared = sum(1 for r in results if r["gate_failed"] is None)
    unver = sum(1 for r in results if r["gate_failed"] is None and r["unverified"])
    return {"n": n, "slop": sum(r["slop"] for r in results), "failed_at_gate": by,
            "cleared_every_gate_that_ran": cleared, "of_which_not_fully_verified": unver,
            "mean_score": round(sum(r["score"] for r in results) / n, 3) if n else None}


def print_summary(s):
    print(f"\n{s['n']} answers, slop (failed a gate): {s['slop']}")
    for g in GATES:
        print(f"  fails at {g:<10} {s['failed_at_gate'][g]}")
    print(f"  cleared every gate that ran: {s['cleared_every_gate_that_ran']}"
          f"  (not fully verified: {s['of_which_not_fully_verified']})")
    print(f"  mean score: {s['mean_score']}  (gates passed / {len(GATES)}; skipped gates count as not passed)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", help="results_<label>.json written by sft/eval_test.py")
    ap.add_argument("--test", help="the prompts file those answers were generated from (jsonl)")
    ap.add_argument("--answer", help="one raw model answer (text file)")
    ap.add_argument("--prompt", help="the prompt for --answer")
    ap.add_argument("--motor-lookup", help="new_results/sft_v4_motor_lookup.json (branch sft-v5-data)")
    ap.add_argument("--no-flight", action="store_true")
    ap.add_argument("--no-cad", action="store_true")
    ap.add_argument("--wind", type=float, help="wind m/s (default 2.0)")
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
                  f"{r['score']:.2f}  {'; '.join(r['reasons'])[:110]}", flush=True)
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
