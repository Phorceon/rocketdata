#!/usr/bin/env python3
"""Stage-2 reasoning renderer for the compact SFT rows (NO flights).

Builds the assistant message text for each row of the repaired dataset:

    <thought>
    REQUIREMENTS: ...          (the full prompt restated + targets with units)
    AIRFRAME: ...              (stages and structural parts, in order)
    HOW THE PARTS FIT: ...     (arithmetic fit checks from real numbers)
    FINS: ...                  (every fin input, incl. each freeform point)
    PROPULSION: ...            (active motors, resolved thrust data)
    BALANCE: ...               (mass, CG, CP, static margin arithmetic)
    RECOVERY: ...              (recovery devices + descent estimate)
    EXPECTED FLIGHT: ...       (targets at 3 significant figures + launch setup)
    </thought>
    <design>{compact JSON}</design>

Every physics input leaf of the (stripped) compact design must appear in the
thought with an equal value; ``coverage_gaps`` finds any that do not.  Flight
numbers come ONLY from each row's stored ``targets``; static numbers come from
``engineering.json`` and from the headless load dump (``digest_check.json``).
NO simulation runs anywhere in this module.

Honesty rules baked in: nothing is called safe/verified; a number that cannot
be computed from the file is reported as not computed; designs with a landing
speed above 8 m/s, static margin below 1 caliber, uncertain thrust-to-weight,
or a failed fit check carry that fact in their ``flags`` and in plain words.
"""

from __future__ import annotations

import json
from typing import Any

G0 = 9.80665

# --------------------------------------------------------------------------
# compact tree helpers
# --------------------------------------------------------------------------

def children_of(node: dict) -> list:
    kids = node.get("children")
    return kids if isinstance(kids, list) else []


def child(node: dict, tag: str) -> dict | None:
    for wrapper in children_of(node):
        if isinstance(wrapper, dict) and len(wrapper) == 1 and tag in wrapper:
            return wrapper[tag]
    return None


def value_of(node: dict | None) -> Any:
    return node.get("value") if isinstance(node, dict) else None


def attr_of(node: dict | None, key: str) -> Any:
    if not isinstance(node, dict):
        return None
    return (node.get("attrs") or {}).get(key)


def walk_components(node: dict, depth: int = 0):
    """Yield (tag, payload, depth) for every component below ``node`` in
    document order, following <subcomponents> (which the loader resolves as
    component children in the same order)."""
    subs = child(node, "subcomponents")
    if subs is None:
        return
    for wrapper in children_of(subs):
        if not (isinstance(wrapper, dict) and len(wrapper) == 1):
            continue
        (tag, payload), = wrapper.items()
        yield tag, payload, depth
        yield from walk_components(payload, depth + 1)


def stage_wrappers(rocket: dict) -> list[tuple[str, dict]]:
    """(tag, payload) for each stage/parallelstage under the rocket, in order."""
    out = []
    for wrapper in children_of(child(rocket, "subcomponents") or {}):
        if not (isinstance(wrapper, dict) and len(wrapper) == 1):
            continue
        (tag, payload), = wrapper.items()
        if tag in ("stage", "parallelstage"):
            out.append((tag, payload))
    return out


def find_rocket(compact: dict) -> dict:
    for wrapper in children_of(compact.get("openrocket") or {}):
        if isinstance(wrapper, dict) and "rocket" in wrapper:
            return wrapper["rocket"]
    raise ValueError("compact design has no rocket element")


def find_simulation(compact: dict) -> dict:
    for wrapper in children_of(compact.get("openrocket") or {}):
        if isinstance(wrapper, dict) and "simulations" in wrapper:
            sims = wrapper["simulations"]
            for sim_wrapper in children_of(sims):
                if isinstance(sim_wrapper, dict) and "simulation" in sim_wrapper:
                    return sim_wrapper["simulation"]
    raise ValueError("compact design has no simulation element")


# --------------------------------------------------------------------------
# value rendering (exact values; never rounded)
# --------------------------------------------------------------------------

def fmt_value(v: Any) -> str:
    """Exact textual form of a stored value, matching its JSON serialization."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return repr(v)
    if isinstance(v, int):
        return str(v)
    return str(v)


def fmt_sig3(v: float) -> str:
    """3-significant-figure rendering for derived/expected numbers only."""
    if v == 0:
        return "0"
    av = abs(v)
    if 0.01 <= av < 1e6:
        out = f"{v:.3g}"
        if "e" in out or "E" in out:
            out = f"{v:.0f}" if av >= 1000 else out
            if "e" in out or "E" in out:
                return f"{v:.3g}"
        return out
    return f"{v:.3g}"


def _unit_for(tag: str, unit: str | None) -> str:
    return f" {unit}" if unit else ""


METER_TAGS = {
    "length", "thickness", "radius", "outerradius", "innerradius", "foreradius",
    "aftradius", "aftshoulderradius", "aftshoulderlength", "aftshoulderthickness",
    "foreshoulderradius", "foreshoulderlength", "foreshoulderthickness",
    "position", "axialoffset", "radiusoffset", "radialposition",
    "packedlength", "packedradius", "cordlength", "linelength", "striplength",
    "stripwidth", "overhang", "tabheight", "tablength", "tabposition",
    "filletradius", "height", "diameter", "outerdiameter", "innerdiameter",
    "launchrodlength", "deployaltitude", "separationaltitude", "launchaltitude",
    "rootchord", "tipchord", "sweeplength", "instanceseparation",
}
DEGREE_TAGS = {
    "launchrodangle", "launchroddirection", "radialdirection", "rotation",
    "cant", "angleoffset", "launchlatitude", "launchlongitude",
}
RADIAN_TAGS = {"direction"}
SECOND_TAGS = {
    "delay", "ignitiondelay", "deploydelay", "separationdelay", "timestep",
    "maxtime",
}
SPEED_TAGS = {"windaverage", "speed", "standarddeviation"}
MASS_TAGS = {"mass", "overridemass"}
DIMLESS_TAGS = {"cd", "overridecd", "shapeparameter", "clusterscale",
                "windturbulence"}
PRESSURE_TAGS = {"basepressure"}
TEMP_TAGS = {"basetemperature"}

LEAF_PHRASES = {
    "length": "length", "thickness": "wall", "radius": "radius",
    "outerradius": "outer radius", "innerradius": "inner radius",
    "foreradius": "fore radius", "aftradius": "aft radius",
    "aftshoulderradius": "aft shoulder radius",
    "aftshoulderlength": "aft shoulder length",
    "aftshoulderthickness": "aft shoulder wall",
    "aftshouldercapped": "aft shoulder capped",
    "foreshoulderradius": "fore shoulder radius",
    "foreshoulderlength": "fore shoulder length",
    "foreshoulderthickness": "fore shoulder wall",
    "foreshouldercapped": "fore shoulder capped",
    "position": "position", "axialoffset": "axial offset",
    "radiusoffset": "radius offset", "angleoffset": "angle offset",
    "radialposition": "radial position", "radialdirection": "radial direction",
    "material": "material", "finish": "finish", "shape": "shape",
    "shapeparameter": "shape parameter", "shapeclipped": "shape clipped",
    "mass": "mass", "overridemass": "override mass", "overridecg": "override CG",
    "overridecd": "override Cd", "overridesubcomponents": "override incl. subcomponents",
    "overridesubcomponentsmass": "override incl. subcomponents (mass)",
    "overridesubcomponentscg": "override incl. subcomponents (CG)",
    "overridesubcomponentscd": "override incl. subcomponents (Cd)",
    "masscomponenttype": "mass component type",
    "packedlength": "packed length", "packedradius": "packed radius",
    "deployevent": "deploy event", "deployaltitude": "deploy altitude",
    "deploydelay": "deploy delay", "diameter": "diameter",
    "linecount": "shroud line count", "linelength": "shroud line length",
    "linematerial": "shroud line material", "cordlength": "cord length",
    "striplength": "strip length", "stripwidth": "strip width",
    "rootchord": "root chord", "tipchord": "tip chord",
    "sweeplength": "sweep length", "height": "height",
    "tabheight": "tab height", "tablength": "tab length",
    "tabposition": "tab position", "filletradius": "fillet radius",
    "filletmaterial": "fillet material", "fincount": "fin count",
    "rotation": "rotation", "cant": "cant", "crosssection": "cross section",
    "instancecount": "instance count", "instanceseparation": "instance separation",
    "clusterconfiguration": "cluster", "clusterscale": "cluster scale",
    "clusterrotation": "cluster rotation", "isflipped": "flipped",
    "ignitionevent": "ignition event", "ignitiondelay": "ignition delay",
    "overhang": "motor overhang", "type": "type",
    "manufacturer": "manufacturer", "designation": "designation",
    "delay": "ejection delay", "separationevent": "separation event",
    "separationaltitude": "separation altitude",
    "separationdelay": "separation delay", "referencetype": "reference length basis",
    "launchrodlength": "launch rod length", "launchrodangle": "launch rod angle",
    "launchroddirection": "launch rod direction", "launchintowind": "launch into wind",
    "windaverage": "wind speed", "windturbulence": "wind turbulence",
    "launchaltitude": "launch altitude", "launchlatitude": "launch latitude",
    "launchlongitude": "launch longitude", "geodeticmethod": "geodesy model",
    "atmosphere": "atmosphere model", "timestep": "time step",
    "simulator": "simulator", "calculator": "CP calculator",
    "windmodeltype": "wind model", "winddirection": "wind direction",
    "maxtime": "max sim time", "gravity": "gravity model",
    "basetemperature": "atmosphere base temperature",
    "basepressure": "atmosphere base pressure",
    "windlevel": "wind level", "standarddeviation": "deviation",
    "wind": "wind model", "speed": "speed", "direction": "direction",
    "altitude": "altitude", "altitudeRef": "altitude reference",
    "simulationsteppermethod": "simulator stepper",
    "designtype": "design type", "color": "color", "linestyle": "line style",
    "recoveryspeedwarning": "recovery speed warning",
    "drogueLowspeedwarning": "drogue low-speed warning",
    "drogueMainspeedwarning": "drogue/main speed warning",
    "recoverydroguemainlowspeedwarning": "drogue low-speed warning",
    "recoverydroguemainhighspeedwarning": "drogue high-speed warning",
    "configid": "flight configuration",
    "motorconfiguration": "motor configuration",
}

COMPONENT_NAMES = {
    "nosecone": "nose cone", "bodytube": "body tube", "transition": "transition",
    "innertube": "inner tube", "centeringring": "centering ring",
    "engineblock": "engine block", "bulkhead": "bulkhead",
    "tubecoupler": "tube coupler", "masscomponent": "mass component",
    "parachute": "parachute", "streamer": "streamer", "shockcord": "shock cord",
    "launchlug": "launch lug", "railbutton": "rail button",
    "freeformfinset": "freeform fin set", "trapezoidfinset": "trapezoidal fin set",
    "ellipticalfinset": "elliptical fin set", "tubefinset": "tube fin set",
    "podset": "pod set", "stage": "stage", "parallelstage": "parallel stage",
    "separationconfiguration": "separation configuration",
    "deploymentconfiguration": "deployment configuration",
    "ignitionconfiguration": "ignition configuration",
    "motorconfiguration": "motor configuration",
}

FINSET_TAGS = {"freeformfinset", "trapezoidfinset", "ellipticalfinset", "tubefinset"}
RECOVERY_TAGS = {"parachute", "streamer", "shockcord"}
# leaves rendered once by their owning section, skipped by the generic renderer
STRUCTURAL_SKIP = {"subcomponents", "motormount", "motorconfiguration",
                   "separationconfiguration", "ignitionconfiguration",
                   "deploymentconfiguration", "finpoints"}

TARGET_LABELS = [
    ("apogee_m", "apogee", "m"),
    ("max_velocity_ms", "max velocity", "m/s"),
    ("max_mach", "max Mach", None),
    ("time_to_apogee_s", "time to apogee", "s"),
    ("flight_time_s", "flight time", "s"),
    ("ground_hit_ms", "landing speed", "m/s"),
    ("wind_ms", "wind", "m/s"),
]


def _material_leaf(tag: str, payload: dict) -> str:
    phrase = LEAF_PHRASES.get(tag, tag)
    mtype = attr_of(payload, "type") or "bulk"
    density = attr_of(payload, "density")
    unit = "kg/m" if mtype == "line" else "kg/m3"
    group = attr_of(payload, "group")
    bits = [f"{phrase} {value_of(payload)}",
            f"{fmt_value(density)} {unit} {mtype}"]
    if group is not None:
        bits.append(f"group {group}")
    shear = attr_of(payload, "shearModulus")
    if shear is not None:
        bits.append(f"shear modulus {fmt_value(shear)} Pa")
    return ", ".join(bits)


def _offset_leaf(tag: str, payload: dict) -> str:
    phrase = LEAF_PHRASES.get(tag, tag)
    method = attr_of(payload, "method") or attr_of(payload, "type") \
        or attr_of(payload, "relativeto")
    value = value_of(payload)
    unit = "m" if tag in METER_TAGS else ("deg" if tag in DEGREE_TAGS else "")
    method_bit = f" {method}" if method is not None else ""
    return f"{phrase}{method_bit} {fmt_value(value)}{_unit_for(tag, unit)}"


def render_leaf(tag: str, payload: Any) -> str | None:
    """One leaf input as 'phrase value unit' (or None for structural keys)."""
    if tag in STRUCTURAL_SKIP:
        return None
    if not isinstance(payload, dict):
        return None
    if tag in ("material", "filletmaterial", "linematerial"):
        return _material_leaf(tag, payload)
    if tag in ("position", "axialoffset", "radiusoffset", "angleoffset",
               "tabposition"):
        return _offset_leaf(tag, payload)
    if tag == "atmosphere":
        model = attr_of(payload, "model")
        extra = ""
        if child(payload, "basetemperature") is not None:
            extra += f", base temperature {fmt_value(value_of(child(payload, 'basetemperature')))} K"
        if child(payload, "basepressure") is not None:
            extra += f", base pressure {fmt_value(value_of(child(payload, 'basepressure')))} Pa"
        return f"atmosphere model {model}{extra}"
    if tag == "wind":
        model = attr_of(payload, "model")
        bits = [f"wind model {model}"]
        alt_ref = attr_of(payload, "altituderef")
        if alt_ref is not None:
            bits.append(f"altitude reference {alt_ref}")
        for wtag in ("speed", "direction", "standarddeviation"):
            w = child(payload, wtag)
            if w is not None:
                unit = "m/s" if wtag in SPEED_TAGS else "rad"
                bits.append(f"{LEAF_PHRASES[wtag]} {fmt_value(value_of(w))} {unit}")
        for w in children_of(payload):
            if isinstance(w, dict) and len(w) == 1 and "windlevel" in w:
                bits.append(render_leaf("windlevel", w["windlevel"]))
        return ", ".join(bits)
    if tag == "windlevel":
        bits = ["wind level"]
        alt = attr_of(payload, "altitude")
        if alt is not None:
            bits.append(f"at {fmt_value(alt)} m")
        sp = attr_of(payload, "speed")
        if sp is not None:
            bits.append(f"speed {fmt_value(sp)} m/s")
        di = attr_of(payload, "direction")
        if di is not None:
            bits.append(f"direction {fmt_value(di)} rad")
        sd = attr_of(payload, "standarddeviation")
        if sd is not None:
            bits.append(f"deviation {fmt_value(sd)} m/s")
        return ", ".join(bits)
    if tag == "gravity":
        return f"gravity model {attr_of(payload, 'model')}"
    if tag == "motorconfiguration":
        cfg = attr_of(payload, "configid")
        default = attr_of(payload, "default")
        if default is None:
            return f"flight configuration {cfg} is the selected one"
        return f"flight configuration {cfg} is the default one ({fmt_value(default)})"
    # generic leaf
    unit = ("m" if tag in METER_TAGS else
            "deg" if tag in DEGREE_TAGS else
            "rad" if tag in RADIAN_TAGS else
            "s" if tag in SECOND_TAGS else
            "m/s" if tag in SPEED_TAGS else
            "kg" if tag in MASS_TAGS else
            "Pa" if tag in PRESSURE_TAGS else
            "K" if tag in TEMP_TAGS else None)
    if tag in DIMLESS_TAGS:
        unit = None
    phrase = LEAF_PHRASES.get(tag, tag)
    return f"{phrase} {fmt_value(value_of(payload))}{_unit_for(tag, unit)}"


def render_component(tag: str, payload: dict, prefix: str = "") -> str:
    """One component line: name + all its generic leaf inputs, in order."""
    name = COMPONENT_NAMES.get(tag, tag)
    bits = []
    if child(payload, "preset") is not None:
        pre = child(payload, "preset")
        bits.append(
            f"catalog preset {attr_of(pre, 'manufacturer')} "
            f"{attr_of(pre, 'partno')} ({attr_of(pre, 'type')})")
    cfg = attr_of(payload, "configid")
    if cfg is not None and tag.endswith("configuration"):
        bits.append(f"for flight configuration {cfg}")
    for wrapper in children_of(payload):
        if not (isinstance(wrapper, dict) and len(wrapper) == 1):
            continue
        (ctag, cpayload), = wrapper.items()
        rendered = render_leaf(ctag, cpayload)
        if rendered:
            bits.append(rendered)
    if not bits:
        return f"{prefix}{name}"
    return f"{prefix}{name}: " + ", ".join(bits)


# --------------------------------------------------------------------------
# fit checks (resolved numbers from the headless load dump)
# --------------------------------------------------------------------------

CLS_OF_TAG = {
    "nosecone": "NoseCone", "bodytube": "BodyTube", "transition": "Transition",
    "innertube": "InnerTube", "centeringring": "CenteringRing",
    "engineblock": "EngineBlock", "bulkhead": "Bulkhead",
    "tubecoupler": "TubeCoupler", "masscomponent": "MassComponent",
    "parachute": "Parachute", "streamer": "Streamer", "shockcord": "ShockCord",
    "launchlug": "LaunchLug", "railbutton": "RailButton",
    "freeformfinset": "FreeformFinSet", "trapezoidfinset": "TrapezoidFinSet",
    "ellipticalfinset": "EllipticalFinSet", "tubefinset": "TubeFinSet",
    "stage": "AxialStage", "parallelstage": "ParallelStage", "podset": "PodSet",
}

TOL = 1e-6  # meters; guards only float noise, never real gaps


def _num(x: Any) -> float | None:
    if isinstance(x, bool) or x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, dict) and "x" in x:
        return _num(x.get("x"))
    return None


def align_dump(design_components: list[tuple[str, dict]],
               dump_components: list[dict]) -> list[tuple[str, dict, dict | None]] | None:
    """Pair design components (DFS) with dump rows (DFS) by order and class.

    The design walk starts INSIDE each stage, so top-level stage rows
    (parent_index -1) of the dump are skipped; pod-internal stages align with
    the design's stage wrappers inside pod sets.
    """
    dump_rows = [row for row in dump_components
                 if not (row.get("cls") in ("AxialStage", "ParallelStage")
                         and row.get("parent_index") == -1)]
    if len(design_components) != len(dump_rows):
        return None
    out = []
    for (tag, payload), row in zip(design_components, dump_rows):
        if CLS_OF_TAG.get(tag) != row.get("cls"):
            return None
        out.append((tag, payload, row))
    return out


def _dump_length(row: dict | None) -> float | None:
    return _num((row or {}).get("loaded", {}).get("getLength"))


def _dump_value(row: dict | None, getter: str) -> float | None:
    return _num((row or {}).get("loaded", {}).get(getter))


def _dump_pos(row: dict | None) -> float | None:
    return _num((row or {}).get("loaded", {}).get("getPosition"))


def fit_checks(design_components: list[tuple[str, dict]],
               dump_components: list[dict] | None,
               eng: dict) -> tuple[list[str], list[str], list[str]]:
    """Return (lines, fit_failures, not_computed) for HOW THE PARTS FIT.

    Every check uses stored design values and/or resolved numbers from the
    headless load dump.  Anything that cannot be computed is said so.
    """
    lines: list[str] = []
    failures: list[str] = []
    not_computed: list[str] = []

    aligned = None
    if dump_components:
        aligned = align_dump(design_components, dump_components)
    if not aligned:
        not_computed.append("fit checks (component list did not align with the "
                            "loaded document)")
        return lines, failures, not_computed

    comps = aligned  # list of (tag, payload, dump_row); parent lookups use
    by_index = {entry[2].get("index"): entry for entry in comps}  # dump indices

    def parent_of(entry) -> dict | None:
        idx = entry[2].get("parent_index")
        row = by_index.get(idx)
        return row[2] if row else None

    def is_pod(entry) -> bool:
        idx = entry[2].get("parent_index")
        while idx is not None and idx >= 0:
            parent = by_index.get(idx)
            if parent is None:
                break
            if parent[0] in ("podset", "parallelstage"):
                return True
            idx = parent[2].get("parent_index")
        return False

    # -- motor vs mount (per motor block, using resolved motor data) --------
    motors_all = eng.get("motors") or []
    # same resolved-only pairing as PROPULSION: skip empty/unresolved entries
    motors = [m for m in motors_all if isinstance(m, dict) and m.get("motor")]
    motor_idx = 0
    for tag, payload, row in comps:
        mount_block = child(payload, "motormount")
        if mount_block is None or tag not in ("innertube", "bodytube"):
            continue
        motor_block = child(mount_block, "motor")
        if motor_block is None:
            continue
        entry = (motors[motor_idx] if motor_idx < len(motors) else {})
        motor_idx += 1
        mdata = entry.get("motor") or {}
        if not mdata:
            not_computed.append("motor fit (no resolved motor data)")
            continue
        inner_r = _dump_value(row, "getInnerRadius")
        m_len = _dump_length(row)
        m_dia = mdata.get("diameter_m")
        m_motor_len = mdata.get("length_m")
        desig = value_of(child(motor_block, "designation"))
        if inner_r is not None and isinstance(m_dia, (int, float)):
            mount_id = 2 * inner_r
            clear = mount_id - m_dia
            verdict = "fits" if clear >= -TOL else "does not fit"
            clear_text = "about 0" if abs(clear) <= TOL else f"{fmt_sig3(clear)} m"
            lines.append(
                f"motor {desig}: diameter {fmt_value(m_dia)} m vs mount inner "
                f"diameter {fmt_value(mount_id)} m (2 x {fmt_value(inner_r)} m) "
                f"- clearance {clear_text}, {verdict}")
            if clear < -TOL:
                failures.append(
                    f"motor {desig} diameter {m_dia} exceeds mount inner "
                    f"diameter {mount_id}")
        else:
            not_computed.append(f"motor {desig} diameter vs mount inner "
                                "diameter (automatic or unresolved radius)")
        if m_len is not None and isinstance(m_motor_len, (int, float)):
            # a motor longer than its mount simply overhangs; that is not a fault
            verdict = "fits" if m_motor_len <= m_len + TOL else (
                f"overhangs the mount by {fmt_sig3(m_motor_len - m_len)} m")
            lines.append(
                f"motor length {fmt_value(m_motor_len)} m vs mount length "
                f"{fmt_value(m_len)} m - {verdict}")
        else:
            not_computed.append("motor length vs mount length")

    # -- centering rings: outer vs parent tube inner, inner vs mount outer --
    for tag, payload, row in comps:
        if tag != "centeringring":
            continue
        parent = parent_of((tag, payload, row))
        tube_inner = _dump_value(parent, "getInnerRadius")
        ring_outer = _dump_value(row, "getOuterRadius")
        ring_inner = _dump_value(row, "getInnerRadius")
        mount_outer = None
        for sibling in comps:
            if sibling[2].get("parent_index") == row.get("parent_index") \
                    and sibling[0] in ("innertube", "bodytube") \
                    and child(sibling[1], "motormount") is not None:
                mount_outer = _dump_value(sibling[2], "getOuterRadius")
        if None not in (ring_outer, tube_inner):
            gap = tube_inner - ring_outer
            verdict = "fits the tube" if -TOL <= gap <= TOL else (
                "loose in the tube" if gap > TOL else "wider than the tube inner")
            lines.append(
                f"centering ring outer radius {fmt_value(ring_outer)} m vs tube "
                f"inner radius {fmt_value(tube_inner)} m - {verdict}")
        else:
            not_computed.append("centering ring outer vs tube inner (automatic)")
        if None not in (ring_inner, mount_outer):
            gap = ring_inner - mount_outer
            verdict = "slides over the mount" if gap >= -TOL else "tighter than the mount"
            lines.append(
                f"ring inner radius {fmt_value(ring_inner)} m vs mount outer "
                f"radius {fmt_value(mount_outer)} m - {verdict}")
        else:
            not_computed.append("centering ring inner vs mount outer (automatic)")

    # -- couplers and shoulders vs tubes ------------------------------------
    for tag, payload, row in comps:
        if tag == "tubecoupler":
            parent = parent_of((tag, payload, row))
            tube_inner = _dump_value(parent, "getInnerRadius")
            outer = _dump_value(row, "getOuterRadius")
            if tube_inner == 0:
                # parent has no bore value (e.g. a nose cone), so no radial check
                not_computed.append("coupler fit (parent has no tube inner radius)")
            elif None not in (outer, tube_inner):
                verdict = "slides inside" if outer <= tube_inner + TOL else "does not fit"
                lines.append(
                    f"tube coupler outer radius {fmt_value(outer)} m vs tube inner "
                    f"radius {fmt_value(tube_inner)} m - {verdict}")
                if outer > tube_inner + TOL:
                    failures.append(
                        f"tube coupler outer radius {outer} exceeds tube inner {tube_inner}")
            else:
                not_computed.append("coupler fit (automatic radius)")
        if tag in ("nosecone", "transition"):
            for side, sib_off in (("aft", +1), ("fore", -1)):
                shoulder_r = _dump_value(row, f"get{side.capitalize()}ShoulderRadius")
                if not shoulder_r or shoulder_r <= 0:
                    continue
                sib = _adjacent_component(comps, row, sib_off)
                if sib is None:
                    not_computed.append(f"{side} shoulder fit (no adjacent tube)")
                    continue
                tube_inner = _dump_value(sib[2], "getInnerRadius")
                if tube_inner is None:
                    not_computed.append(f"{side} shoulder fit (automatic tube radius)")
                    continue
                verdict = "fits inside" if shoulder_r <= tube_inner + TOL else "does not fit"
                lines.append(
                    f"{COMPONENT_NAMES[tag]} {side} shoulder radius "
                    f"{fmt_value(shoulder_r)} m vs adjacent tube inner radius "
                    f"{fmt_value(tube_inner)} m - {verdict}")
                if shoulder_r > tube_inner + TOL:
                    failures.append(
                        f"{COMPONENT_NAMES[tag]} {side} shoulder radius {shoulder_r} "
                        f"exceeds adjacent tube inner radius {tube_inner}")

    # -- internal parts stay inside their parent ----------------------------
    INTERNAL = {"innertube", "centeringring", "engineblock", "bulkhead",
                "masscomponent", "parachute", "streamer", "shockcord",
                "tubecoupler"}
    for tag, payload, row in comps:
        if tag not in INTERNAL:
            continue
        parent = parent_of((tag, payload, row))
        parent_len = _dump_length(parent)
        rel = _dump_pos(row)
        comp_len = _dump_length(row)
        if None in (parent_len, rel, comp_len):
            not_computed.append(
                f"{COMPONENT_NAMES[tag]} position span (automatic placement)")
            continue
        lo, hi = rel, rel + comp_len
        inside = lo >= -TOL and hi <= parent_len + TOL
        if inside:
            verdict = "inside"
            span = f"spans {fmt_sig3(lo)} to {fmt_sig3(hi)} m of its " \
                   f"{fmt_sig3(parent_len)} m parent"
        else:
            over = fmt_sig3((-lo) if lo < 0 else (hi - parent_len))
            side = ("above the parent's top" if lo < 0
                    else "past the parent's bottom")
            # OpenRocket allows this: a coupler bridges a joint, and a child's
            # position is only relative to its parent.  Stated, not a fault.
            verdict = f"extends {over} m {side}"
            span = f"spans {fmt_sig3(lo)} to {fmt_sig3(hi)} m in its " \
                   f"{fmt_sig3(parent_len)} m parent"
        lines.append(
            f"{COMPONENT_NAMES[tag]} {span} - {verdict}")

    # -- fin root vs body tube ----------------------------------------------
    for tag, payload, row in comps:
        if tag not in FINSET_TAGS:
            continue
        parent = parent_of((tag, payload, row))
        parent_len = _dump_length(parent)
        rel = _dump_pos(row)
        extent = _fin_extent(tag, payload)
        if None in (parent_len, rel, extent):
            not_computed.append("fin root span (automatic placement)")
            continue
        lo, hi = rel, rel + extent
        inside = lo >= -TOL and hi <= parent_len + TOL
        verdict = "root inside the tube" if inside else "root extends beyond the tube"
        lines.append(
            f"fin set root spans {fmt_sig3(lo)} to {fmt_sig3(hi)} m of the "
            f"{fmt_sig3(parent_len)} m tube - {verdict}")

    # -- axial stack-up ------------------------------------------------------
    airframe = [e for e in comps if e[0] in ("nosecone", "bodytube", "transition")
                and not is_pod(e)]
    total = sum(_dump_length(e[2]) or 0.0 for e in airframe)
    if total > 0:
        parts = " + ".join(f"{fmt_sig3(_dump_length(e[2]))}" for e in airframe)
        # resolved rocket extent: sum of the top-level core stages' lengths
        stage_lengths = [_dump_length(row) for row in dump_components
                         if row.get("cls") == "AxialStage"
                         and row.get("parent_index") == -1]
        loaded_extent = sum(x for x in stage_lengths if x is not None) \
            if stage_lengths else None
        if loaded_extent is not None and abs(loaded_extent - total) <= TOL:
            lines.append(
                f"axial stack-up: {parts} = {fmt_sig3(total)} m total, matching the "
                f"loaded rocket length {fmt_sig3(loaded_extent)} m")
        elif loaded_extent is None:
            lines.append(
                f"axial stack-up: {parts} = {fmt_sig3(total)} m total")
        else:
            lines.append(
                f"axial stack-up: {parts} = {fmt_sig3(total)} m but the loaded "
                f"rocket length is {fmt_sig3(loaded_extent)} m - mismatch")
            failures.append(
                f"stack-up sum {total} m differs from loaded extent {loaded_extent} m")
    return lines, failures, not_computed


def _adjacent_component(comps, row, offset: int):
    """The next/previous tube-or-transition sibling of ``row`` in its parent."""
    idx = row.get("index")
    parent_idx = row.get("parent_index")
    siblings = [e for e in comps if e[2].get("parent_index") == parent_idx
                and e[2].get("index") != idx]
    after = [e for e in siblings if e[2].get("index") > idx]
    before = [e for e in siblings if e[2].get("index") < idx]
    pool = after if offset > 0 else list(reversed(before))
    for e in pool:
        if e[0] in ("bodytube", "transition"):
            return e
    return None


def _fin_extent(tag: str, payload: dict) -> float | None:
    """Axial extent of one fin (root chord), from the design values."""
    if tag == "trapezoidfinset":
        rc = value_of(child(payload, "rootchord"))
        return float(rc) if isinstance(rc, (int, float)) else None
    pts = child(payload, "finpoints")
    if pts is not None:
        xs = [attr_of(p, "x") for w in children_of(pts)
              if isinstance(w, dict) and "point" in w
              for p in [w["point"]]]
        xs = [x for x in xs if isinstance(x, (int, float))]
        if xs:
            return float(max(xs))
    return None


# --------------------------------------------------------------------------
# section renderers
# --------------------------------------------------------------------------

def render_requirements(prompt_text: str, targets: dict) -> list[str]:
    lines = ["REQUIREMENTS:",
             f'request, in full: "{prompt_text}"']
    bits = []
    for key, label, unit in TARGET_LABELS:
        if key in targets:
            u = f" {unit}" if unit else ""
            bits.append(f"{label} {fmt_value(targets[key])}{u}")
    lines.append("reference-flight targets: " + "; ".join(bits) + ".")
    return lines


def render_airframe(rocket: dict) -> list[str]:
    lines = ["AIRFRAME (document order; inner parts indented under their tube):"]
    # the rocket's own placement leaves
    for wrapper in children_of(rocket):
        if isinstance(wrapper, dict) and len(wrapper) == 1:
            tag = next(iter(wrapper))
            if tag in ("position", "axialoffset"):
                rendered = render_leaf(tag, wrapper[tag])
                if rendered:
                    lines.append(f"- rocket placement: {rendered}.")
    for st_tag, st in stage_wrappers(rocket):
        number = attr_of(st, "number")
        active = attr_of(st, "active")
        bits = []
        if number is not None:
            bits.append(f"number {number}")
        if active is not None:
            bits.append(f"active {fmt_value(active)}")
        head = f"stage ({', '.join(bits)})" if bits else "stage"
        lines.append(f"- {head}.")
        # the stage's own placement/override leaves (parallel stages carry
        # position/angleoffset/override leaves directly)
        for wrapper in children_of(st):
            if not (isinstance(wrapper, dict) and len(wrapper) == 1):
                continue
            (ctag, cpayload), = wrapper.items()
            if ctag in ("subcomponents",):
                continue
            if ctag == "separationconfiguration":
                rendered = render_component(ctag, cpayload)
                if rendered:
                    lines.append(f"  - stage separation configuration: "
                                 f"{rendered}.")
                continue
            rendered = render_leaf(ctag, cpayload)
            if rendered:
                lines.append(f"  - stage-level {rendered}.")
        for tag, payload, depth in walk_components(st):
            indent = "  " * (depth + 1)
            if tag in FINSET_TAGS:
                lines.append(f"{indent}- {COMPONENT_NAMES[tag]}: all inputs in FINS.")
                continue
            if tag in RECOVERY_TAGS:
                lines.append(f"{indent}- {COMPONENT_NAMES[tag]}: inputs in RECOVERY.")
                continue
            if child(payload, "motormount") is not None and child(child(payload, "motormount"), "motor"):
                lines.append(f"{indent}- {render_component(tag, payload)}")
                continue
            lines.append(f"{indent}- {render_component(tag, payload)}")
    return lines


def render_fins(rocket: dict) -> list[str]:
    lines = []
    for st_tag, st in stage_wrappers(rocket):
        for tag, payload, depth in walk_components(st):
            if tag not in FINSET_TAGS:
                continue
            lines.append(f"FINS - {COMPONENT_NAMES[tag]}:")
            for wrapper in children_of(payload):
                if not (isinstance(wrapper, dict) and len(wrapper) == 1):
                    continue
                (ctag, cpayload), = wrapper.items()
                if ctag == "finpoints":
                    pts = []
                    for w in children_of(cpayload):
                        if isinstance(w, dict) and "point" in w:
                            p = w["point"]
                            pts.append(f"({fmt_value(attr_of(p, 'x'))}, "
                                       f"{fmt_value(attr_of(p, 'y'))}) m")
                    lines.append(f"- profile points: {', '.join(pts)}.")
                    continue
                rendered = render_leaf(ctag, cpayload)
                if rendered:
                    lines.append(f"- {rendered}.")
    return lines


def render_propulsion(compact: dict, rocket: dict, eng: dict,
                      sim_name_removed: bool = True) -> tuple[list[str], list[dict], bool]:
    """PROPULSION section.  Returns (lines, motor_diffs, ttw_certain)."""
    lines = ["PROPULSION:"]
    diffs: list[dict] = []
    for wrapper in children_of(rocket):
        if isinstance(wrapper, dict) and "motorconfiguration" in wrapper:
            block = wrapper["motorconfiguration"]
            cfg = attr_of(block, "configid")
            default = attr_of(block, "default")
            line = (f"- flight configuration {cfg} is the selected one"
                    if default is None else
                    f"- flight configuration {cfg} is the default one "
                    f"({fmt_value(default)})")
            active_stages = [
                (attr_of(w["stage"], "number"), attr_of(w["stage"], "active"))
                for w in children_of(block)
                if isinstance(w, dict) and "stage" in w]
            for number, active in active_stages:
                line += f"; active stage {fmt_value(number)}: " \
                        f"{fmt_value(active)}"
            lines.append(line + ".")

    motors_all = eng.get("motors") or []
    # pair each design motor with the next eng entry that actually resolved;
    # entries with motor: null are empty mounts or unresolved placeholders
    # and carry nothing to compare against
    motors = [m for m in motors_all if isinstance(m, dict) and m.get("motor")]
    design_motors = []
    for st_tag, st in stage_wrappers(rocket):
        for tag, payload, depth in walk_components(st):
            mount = child(payload, "motormount")
            if mount is None:
                continue
            motor = child(mount, "motor")
            if motor is not None:
                design_motors.append((tag, payload, mount, motor))

    aggregates = eng.get("motor_aggregates") or {}
    for (tag, payload, mount, motor), entry in zip(design_motors, motors):
        mdata = entry.get("motor") or {}
        desig = value_of(child(motor, "designation"))
        manuf = value_of(child(motor, "manufacturer"))
        mtype = value_of(child(motor, "type"))
        mid = value_of(child(motor, "motor_id"))
        dia = value_of(child(motor, "diameter"))
        length = value_of(child(motor, "length"))
        delay = value_of(child(motor, "delay"))
        bits = [f"motor on the {COMPONENT_NAMES.get(tag, tag)}",
                f"flight configuration {attr_of(motor, 'configid')}",
                f"manufacturer {manuf}", f"designation {desig}"]
        if mid is not None:
            # readable motor identity (the model-visible replacement for the
            # raw thrust-curve digest); coverage requires it below
            bits.append(f"motor id {mid}")
        if mtype is not None:
            bits.append(f"type {mtype}")
        if dia is not None:
            bits.append(f"diameter {fmt_value(dia)} m")
        if length is not None:
            bits.append(f"length {fmt_value(length)} m")
        bits.append(f"ejection delay {fmt_value(delay)}")
        resolved_desig = mdata.get("designation")
        if resolved_desig and resolved_desig != desig:
            bits.append(f"the motor database resolves this as {resolved_desig}")
            diffs.append({
                "designation_design": str(desig),
                "designation_resolved": str(resolved_desig),
                "digest_differs": _digest_differs(motor, mdata),
            })
        if mdata.get("total_impulse_ns") is not None:
            bits.append(f"total impulse {fmt_value(mdata['total_impulse_ns'])} N.s")
        if mdata.get("burn_time_s") is not None:
            bits.append(f"burn time {fmt_value(mdata['burn_time_s'])} s")
        if mdata.get("average_thrust_n") is not None:
            bits.append(f"average thrust {fmt_value(mdata['average_thrust_n'])} N")
        if entry.get("instance_count") is not None:
            bits.append(f"instance count {entry['instance_count']}")
        ev = value_of(child(mount, "ignitionevent"))
        evd = value_of(child(mount, "ignitiondelay"))
        if ev is not None:
            bits.append(f"ignition event {ev}")
        if evd is not None:
            bits.append(f"ignition delay {fmt_value(evd)} s")
        mount_ig = child(mount, "ignitionconfiguration")
        if mount_ig is not None:
            ig_ev = value_of(child(mount_ig, "ignitionevent"))
            ig_dl = value_of(child(mount_ig, "ignitiondelay"))
            bits.append(f"per-configuration ignition override (configuration "
                        f"{attr_of(mount_ig, 'configid')})"
                        + (f": event {ig_ev}" if ig_ev is not None else "")
                        + (f", delay {fmt_value(ig_dl)} s" if ig_dl is not None else ""))
        ov = value_of(child(mount, "overhang"))
        if ov is not None:
            bits.append(f"motor overhang {fmt_value(ov)} m")
        lines.append(f"- {', '.join(bits)}.")

    # rocket-level per-configuration ignition override
    for wrapper in children_of(rocket):
        if isinstance(wrapper, dict) and "ignitionconfiguration" in wrapper:
            block = wrapper["ignitionconfiguration"]
            ev = value_of(child(block, "ignitionevent"))
            evd = value_of(child(block, "ignitiondelay"))
            if ev is not None:
                lines.append(f"- configuration ignition override: event {ev}"
                             + (f", delay {fmt_value(evd)} s" if evd is not None else "")
                             + ".")
        if isinstance(wrapper, dict) and "separationconfiguration" in wrapper:
            block = wrapper["separationconfiguration"]
            ev = value_of(child(block, "separationevent"))
            alt = value_of(child(block, "separationaltitude"))
            dl = value_of(child(block, "separationdelay"))
            bits = []
            if ev is not None:
                bits.append(f"event {ev}")
            if alt is not None:
                bits.append(f"altitude {fmt_value(alt)} m")
            if dl is not None:
                bits.append(f"delay {fmt_value(dl)} s")
            if bits:
                lines.append(f"- stage separation configuration: {', '.join(bits)}.")

    total_impulse = aggregates.get("total_impulse_ns")
    if total_impulse is not None and len(motors) > 1:
        lines.append(f"- combined total impulse {fmt_value(total_impulse)} N.s.")

    liftoff = eng.get("liftoff_mass_kg")
    ttw_certain, ttw = thrust_to_weight(eng, rocket)
    if liftoff is not None:
        lines.append(f"- liftoff mass {fmt_value(liftoff)} kg.")
    if ttw_certain and ttw is not None:
        lines.append(
            f"- thrust-to-weight at liftoff {fmt_sig3(ttw)} "
            f"(lit average thrust / (liftoff mass x {G0})).")
    else:
        lines.append(
            "- thrust-to-weight could not be determined from the file: which "
            "motor lights first is not certain for this multi-motor design, so "
            "no number is printed.")
    return lines, diffs, ttw_certain and ttw is not None


def _digest_differs(design_motor: dict, mdata: dict) -> bool | None:
    d = value_of(child(design_motor, "digest"))
    r = mdata.get("digest")
    if d is None and r is None:
        return None
    return str(d) != str(r)


def thrust_to_weight(eng: dict, rocket: dict) -> tuple[bool, float | None]:
    """(certain, value).  Certain only when the liftoff-lit motor set is
    certain from the file: exactly one motor, or every mount ignites by an
    explicit launch event with zero delay."""
    motors = [m for m in (eng.get("motors") or [])
              if isinstance(m, dict) and m.get("motor")]
    liftoff = eng.get("liftoff_mass_kg")
    if not motors or liftoff is None:
        return False, None
    events = []
    for st_tag, st in stage_wrappers(rocket):
        for tag, payload, depth in walk_components(st):
            mount = child(payload, "motormount")
            if mount is None:
                continue
            if child(mount, "motor") is None:
                continue
            events.append((value_of(child(mount, "ignitionevent")),
                           value_of(child(mount, "ignitiondelay"))))
    if len(motors) == 1:
        lit = [m for m in motors]
    elif all(ev == "launch" for ev, _ in events) and \
            all(dlg in (0, 0.0, None) for _, dlg in events):
        lit = motors
    else:
        return False, None
    thrust = sum((m["motor"].get("average_thrust_n") or 0.0)
                 * (m.get("instance_count") or 1) for m in lit)
    if thrust <= 0 or liftoff <= 0:
        return False, None
    return True, thrust / (liftoff * G0)


def render_balance(eng: dict) -> list[str]:
    lines = ["BALANCE (static, at Mach 0.3 and 0 deg angle of attack):"]
    mass = eng.get("liftoff_mass_kg")
    cg = eng.get("cg_m")
    cp = eng.get("cp_m")
    ref = eng.get("reference_diameter_m")
    sm = eng.get("static_margin_cal")
    if mass is not None:
        lines.append(f"- liftoff mass {fmt_value(mass)} kg.")
    if cg is not None:
        lines.append(f"- center of gravity {fmt_value(cg)} m from the nose tip.")
    if cp is not None:
        lines.append(f"- center of pressure {fmt_value(cp)} m from the nose tip.")
    if ref is not None:
        lines.append(f"- reference diameter {fmt_value(ref)} m.")
    if None not in (cg, cp, ref, sm) and ref > 0:
        lines.append(
            f"- static margin = (CP - CG) / diameter = "
            f"({fmt_value(cp)} - {fmt_value(cg)}) / {fmt_value(ref)} = "
            f"{fmt_value(sm)} calibers.")
    elif sm is None:
        lines.append("- static margin could not be computed (no CP).")
    return lines


def render_recovery(rocket: dict, targets: dict) -> list[str]:
    lines = ["RECOVERY:"]
    found = False
    for st_tag, st in stage_wrappers(rocket):
        for tag, payload, depth in walk_components(st):
            if tag not in RECOVERY_TAGS:
                continue
            found = True
            lines.append(f"- {render_component(tag, payload, prefix='')}.")
        # per-configuration deployment overrides live at rocket level; the
        # device inputs above are the physics inputs.
    for wrapper in children_of(rocket):
        if isinstance(wrapper, dict) and "deploymentconfiguration" in wrapper:
            block = wrapper["deploymentconfiguration"]
            rendered = render_component("deploymentconfiguration", block, prefix="")
            if rendered and rendered != "deploymentconfiguration":
                lines.append(f"- deployment configuration: {rendered}.")
    if not found:
        lines.append("- no recovery device in this design.")
    # descent estimate from targets only
    apogee = targets.get("apogee_m")
    t_apo = targets.get("time_to_apogee_s")
    t_flight = targets.get("flight_time_s")
    landing = targets.get("ground_hit_ms")
    if None not in (apogee, t_apo, t_flight):
        descent = t_flight - t_apo
        sink = apogee / descent if descent > 0 else None
        lines.append(
            f"- descent time estimate {fmt_sig3(descent)} s (= {fmt_value(t_flight)} s "
            f"flight - {fmt_value(t_apo)} s to apogee; estimate).")
        if sink is not None:
            lines.append(
                f"- mean sink rate about {fmt_sig3(sink)} m/s (estimate: apogee / "
                f"descent time); expected landing speed {fmt_value(landing)} m/s.")
    if landing is not None:
        if landing > 8.0:
            lines.append(
                f"- landing speed about {fmt_sig3(landing)} m/s is above the 8 m/s "
                "structural limit; this design is not safe as-is.")
        else:
            lines.append(
                f"- landing speed about {fmt_sig3(landing)} m/s is within the "
                "8 m/s structural limit.")
    return lines


def render_expected_flight(rocket: dict, sim: dict, targets: dict,
                           prompt_text: str) -> list[str]:
    lines = ["EXPECTED FLIGHT (expected values from the reference flight of this "
             "design, rounded to 3 significant figures; confirm with a simulator):"]
    comparisons = {
        "apogee_m": ("expected apogee", "m"),
        "flight_time_s": ("expected flight time", "s"),
        "ground_hit_ms": ("expected landing speed", "m/s"),
        "max_velocity_ms": ("expected max velocity", "m/s"),
        "max_mach": ("expected max Mach", None),
        "time_to_apogee_s": ("expected time to apogee", "s"),
    }
    for key, (label, unit) in comparisons.items():
        if key not in targets:
            continue
        u = f" {unit}" if unit else ""
        lines.append(f"- {label} {fmt_sig3(targets[key])}{u} vs target "
                     f"{fmt_sig3(targets[key])}{u}.")
    if "wind_ms" in targets:
        lines.append(f"- wind {fmt_sig3(targets['wind_ms'])} m/s matches the "
                     "launch wind input below.")
    lines.append(f"- prompt in full: \"{prompt_text}\"")
    # motor requested by the prompt vs design motor (only when clearly stated)
    import re
    m = re.search(r"on an? ((?:[1-9]/2 )?[A-O]\d{1,4}[A-Z/]*(?:-\d{1,2})?)", prompt_text,
                  re.IGNORECASE)
    if m:
        asked = m.group(1).upper()
        design_desigs = []
        for st_tag, st in stage_wrappers(rocket):
            for tag, payload, depth in walk_components(st):
                mount = child(payload, "motormount")
                if mount is None:
                    continue
                motor = child(mount, "motor")
                if motor is not None:
                    d = value_of(child(motor, "designation"))
                    if d:
                        design_desigs.append(str(d).upper())
        if design_desigs:
            if any(asked in d or d in asked for d in design_desigs):
                lines.append(f"- the prompt asks for a {asked} motor and the design "
                             f"uses {', '.join(sorted(set(design_desigs)))}.")
            else:
                lines.append(f"- the prompt asks for a {asked} motor but the design "
                             f"uses {', '.join(sorted(set(design_desigs)))}; "
                             "the prompt is kept as written.")
    # launch conditions (inputs)
    cond = child(sim, "conditions") or {}
    launch_bits = []
    for wrapper in children_of(cond):
        if not (isinstance(wrapper, dict) and len(wrapper) == 1):
            continue
        (ctag, cpayload), = wrapper.items()
        if ctag == "configid":
            continue
        rendered = render_leaf(ctag, cpayload)
        if rendered:
            launch_bits.append(rendered)
    sim_bits = []
    for tag in ("simulator", "calculator"):
        node = child(sim, tag)
        if node is not None:
            rendered = render_leaf(tag, node)
            if rendered:
                sim_bits.append(rendered)
    for wrapper in children_of(rocket):
        if isinstance(wrapper, dict) and "referencetype" in wrapper:
            rendered = render_leaf("referencetype", wrapper["referencetype"])
            if rendered:
                sim_bits.append(rendered)
    lines.append("- LAUNCH AND SIMULATION SETUP: " + "; ".join(launch_bits + sim_bits)
                 + ". (all values are inputs of the reference flight)")
    return lines


# --------------------------------------------------------------------------
# coverage (every physics leaf of the design appears in the thought)
# --------------------------------------------------------------------------

def iter_design_leaves(compact: dict):
    """Yield (context_tag, leaf_tag, value, attrs) for every leaf of the
    compact design, including attribute values on leaves."""
    def visit(node, ctx):
        if not isinstance(node, dict):
            return
        for wrapper in children_of(node):
            if not (isinstance(wrapper, dict) and len(wrapper) == 1):
                continue
            (tag, payload), = wrapper.items()
            if not isinstance(payload, dict):
                continue
            for ak, av in (payload.get("attrs") or {}).items():
                yield ctx, f"{tag}@{ak}", av, None
            if "value" in payload:
                yield ctx, tag, payload.get("value"), payload.get("attrs")
            yield from visit(payload, tag)
    for wrapper in children_of(compact.get("openrocket") or {}):
        if isinstance(wrapper, dict) and "rocket" in wrapper:
            yield from visit(wrapper["rocket"], "rocket")
        if isinstance(wrapper, dict) and "simulations" in wrapper:
            yield from visit(wrapper["simulations"], "simulation")


def coverage_gaps(thought: str, design: dict) -> list[str]:
    """Leaf values of the design missing from the thought text."""
    gaps = []
    for ctx, tag, value, attrs in iter_design_leaves(design):
        if value is None:
            continue
        if tag in ("configid",):
            continue  # wiring; the flight configuration id appears via the
            # motor-configuration line as 'cfg0'
        # 'motor_id' is deliberately NOT skipped: every motor block's readable
        # id must appear in the PROPULSION section (rendered as 'motor id ...').
        text = fmt_value(value)
        if text not in thought:
            gaps.append(f"{ctx}/{tag} = {text}")
    return gaps


# --------------------------------------------------------------------------
# top-level renderer
# --------------------------------------------------------------------------

def render_thought(design: dict, eng: dict, targets: dict, prompt_text: str,
                   fit_dump: list[dict] | None) -> dict:
    """Build the <thought> text for one row.

    Returns {"thought": str, "motor_diffs": [...], "fit_failures": [...],
    "not_computed": [...]}.  NO simulation runs here.
    """
    rocket = find_rocket(design)
    sim = find_simulation(design)

    comps = [(tag, payload) for st_tag, st in stage_wrappers(rocket)
             for tag, payload, _ in walk_components(st)]
    dump = fit_dump or []

    req = render_requirements(prompt_text, targets)
    air = render_airframe(rocket)
    fit_lines, fit_failures, not_computed = fit_checks(comps, dump, eng)
    fit = (["HOW THE PARTS FIT (checked with the numbers of this design):"]
           + [f"- {line}" for line in fit_lines])
    if fit_failures:
        fit.append("- fit problems found by these checks: "
                   + "; ".join(fit_failures) + ".")
    if not_computed:
        fit.append("- not computed (input automatic or check not derivable): "
                   + "; ".join(not_computed) + ".")
    fins = render_fins(rocket)
    if not fins:
        fins = ["FINS: this design has no fin set."]
    prop, motor_diffs, ttw_certain = render_propulsion(design, rocket, eng)
    bal = render_balance(eng)
    rec = render_recovery(rocket, targets)
    flt = render_expected_flight(rocket, sim, targets, prompt_text)

    thought = "\n".join(
        req + [""] + air + [""] + fit + [""] + fins + [""] + prop + [""] + bal
        + [""] + rec + [""] + flt)
    return {"thought": thought, "motor_diffs": motor_diffs,
            "fit_failures": fit_failures, "not_computed": not_computed,
            "ttw_certain": ttw_certain}
