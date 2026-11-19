"""Stage 4: limits. Sizes, counts and materials must be physically sensible.

The rules here block trick values that a simulator would happily fly: fins as
thin as paper, a parachute with fifty times the real drag, fins many times the
body width used as air brakes, a part type nobody has heard of, a material
the reward cannot give a real density, walls or fins of foam film, oversized
launch lugs, rail buttons or tube fins, and designs with so many parts that
one answer would take a minute to fly. Every bound lives in limits.py with its
source; this file only applies them.

Each broken rule adds a violation size (see ladder.py and DESIGN.md, "How
credit is computed"), and the stage credit is 1 / (1 + sum of sizes), so a
design that is only a little past a limit keeps most of its credit.

The tree comes from a language model, so nothing here trusts its shape: wrong
types, missing pieces, NaN, huge numbers and odd nesting all give a normal
result.
"""
from __future__ import annotations

import re
from typing import Any, Optional

from . import limits as L
from .materials import (NAME_LIST_HINT, UNITS, MaterialTable, default_material_table, loaded_type, loose_name,
                        means_no_material, name_text)
from .ladder import (MATERIAL_NAMES_COUNTED_MAX, YES_NO_VIOLATION, MAX_VIOLATION, credit_from_violations,
                     over_limit, under_limit)
from .motors import flown_motors
from .records import StageCheck
from .tree import (MATERIAL_TAGS, Node, attrs_of, body_of, children_named, children_of, is_node, last_child, last_text,
                   read_number, rocket_of, tag_of, value_of, walk_components, walk_nodes)

STAGE = "limits"
MAX_REASONS = 12  # reasons listed in full; the rest are counted in one line

FIN_SETS = frozenset({"trapezoidfinset", "ellipticalfinset", "freeformfinset"})
SHELL_WALLS = frozenset({"bodytube", "nosecone", "transition", "tubefinset"})
MULTI_INSTANCE = frozenset({"podset", "parallelstage"})

# Size fields that can never be negative, on any component.
NON_NEGATIVE = frozenset({
    "length", "radius", "outerradius", "innerradius", "aftradius", "foreradius",
    "thickness", "diameter", "mass", "height", "rootchord", "tipchord",
    "packedlength", "packedradius", "striplength", "stripwidth", "cordlength",
    "linelength", "aftshoulderlength", "aftshoulderradius", "aftshoulderthickness",
    "foreshoulderlength", "foreshoulderradius", "foreshoulderthickness", "cd",
    "overridemass", "overridecd", "overridecg",
})

# The unit of each size field, so a reason can say "-0.9 m" and not just "-0.9".
_UNITS = {"mass": "kg", "overridemass": "kg", "cd": "", "overridecd": ""}

_SUBCOMPONENT_SWITCHES = ("overridesubcomponents", "overridesubcomponentsmass")

# Range rules: (component types or None for every type, field, lowest, highest,
# unit, zero means "auto"). A zero radius means "take it from the neighbouring
# part" in OpenRocket, so it is skipped. A missing field is OpenRocket's default
# and is not a violation.
_RANGE_RULES: tuple[tuple[Optional[frozenset], str, Optional[float], Optional[float], str, bool], ...] = (
    (frozenset({"bodytube"}), "radius", L.TUBE_RADIUS_MIN_M, L.TUBE_RADIUS_MAX_M, "mm", True),
    (frozenset({"innertube", "tubecoupler"}), "outerradius", None, L.TUBE_RADIUS_MAX_M, "mm", True),
    (frozenset({"bodytube", "innertube", "tubecoupler"}), "length", None, L.TUBE_LENGTH_MAX_M, "m", False),
    (frozenset({"nosecone"}), "length", None, L.NOSE_LENGTH_MAX_M, "m", False),
    (frozenset({"nosecone"}), "aftradius", None, L.SHELL_RADIUS_MAX_M, "mm", True),
    (frozenset({"transition"}), "length", None, L.TRANSITION_LENGTH_MAX_M, "m", False),
    (frozenset({"transition"}), "foreradius", None, L.SHELL_RADIUS_MAX_M, "mm", True),
    (frozenset({"transition"}), "aftradius", None, L.SHELL_RADIUS_MAX_M, "mm", True),
    (frozenset({"parachute"}), "diameter", L.CHUTE_DIAMETER_MIN_M, L.CHUTE_DIAMETER_MAX_M, "m", False),
    (frozenset({"parachute"}), "cd", L.CHUTE_CD_MIN, L.CHUTE_CD_MAX, "", False),
    (frozenset({"streamer"}), "striplength", None, L.STREAMER_LENGTH_MAX_M, "m", False),
    (frozenset({"streamer"}), "stripwidth", None, L.STREAMER_WIDTH_MAX_M, "m", False),
    (frozenset({"streamer"}), "cd", None, L.STREAMER_CD_MAX, "", False),
    (frozenset({"masscomponent"}), "mass", None, L.MASS_COMPONENT_MAX_KG, "kg", False),
    (frozenset({"launchlug"}), "radius", None, L.LAUNCH_LUG_RADIUS_MAX_M, "mm", False),
    (frozenset({"launchlug"}), "length", None, L.LAUNCH_LUG_LENGTH_MAX_M, "m", False),
    (frozenset({"railbutton"}), "outerdiameter", None, L.RAIL_BUTTON_DIAMETER_MAX_M, "mm", False),
    (frozenset({"railbutton"}), "height", None, L.RAIL_BUTTON_HEIGHT_MAX_M, "mm", False),
    (FIN_SETS, "rootchord", None, L.FIN_CHORD_MAX_M, "m", False),
    (FIN_SETS, "tipchord", None, L.FIN_CHORD_MAX_M, "m", False),
    (None, "overridemass", None, L.OVERRIDE_MASS_MAX_KG, "kg", False),
    (None, "overridecd", None, L.OVERRIDE_CD_MAX, "", False),
    (None, "overridecg", None, L.OVERRIDE_CG_MAX_M, "m", False),
)


# ------------------------------------------------------------------ reading the tree
# The tree is read with tree.py. Settings are read from the LAST child with
# their tag (tree.last_child): when a design writes a setting twice,
# OpenRocket's loader keeps the last copy. Numbers are read the way OpenRocket
# reads them (tree.read_number).

def _components(rocket: Node):
    """Every component inside the rocket, with its enclosing components.

    Follows every "subcomponents" holder of every component, the same walk
    stages 2 and 3 use (tree.walk_components). It also visits parts placed
    where OpenRocket would drop them (stage 2 does not count those): checking
    a part that will not fly costs a sound design nothing, while skipping one
    that does fly would let a trick value through.
    """
    return walk_components(rocket)


def _field(component: Node, tag: str) -> Optional[float]:
    """The last child `tag` of a component as a finite number, else None."""
    c = last_child(component, tag)
    if c is None:
        return None
    return read_number(body_of(c).get("value"))[0]


def _switched_on(component: Node, tags: tuple[str, ...]) -> bool:
    """True when one of these yes/no settings is on (true, "true" or a non-zero number)."""
    for tag in tags:
        c = last_child(component, tag)
        if c is None:
            continue
        v = body_of(c).get("value")
        if v is True or (isinstance(v, str) and v.strip().lower() == "true"):
            return True
        n, _ = read_number(v)
        if n is not None and n != 0:
            return True
    return False


def _overrides_mass(comp: Node) -> bool:
    """True when the part sets its own mass with a usable "overridemass"."""
    m = _field(comp, "overridemass")
    return m is not None and m >= 0


def _overrides_inside(comp: Node) -> bool:
    """True when the part's mass override also stands for everything inside it."""
    return _overrides_mass(comp) and _switched_on(comp, _SUBCOMPONENT_SWITCHES)


# ------------------------------------------------------------------ formatting

def _fmt(x: float, unit: str) -> str:
    """A number with its unit, in the unit a student would use."""
    if unit == "mm":
        return f"{x * 1000:.4g} mm"
    if unit == "m" and abs(x) < 0.1:
        return f"{x * 1000:.4g} mm"
    return f"{x:.4g} {unit}".rstrip()


class _Findings:
    """Violation sizes and the matching plain-language reasons."""

    def __init__(self) -> None:
        self.sizes: list[float] = []
        self.reasons: list[str] = []

    def add(self, size: float, reason: str) -> None:
        if size > 0:
            self.sizes.append(size)
            self.reasons.append(reason)

    def above(self, value: float, limit: float, unit: str, what: str) -> None:
        if value > limit:
            self.add(over_limit(value, limit),
                     f"{what} is {_fmt(value, unit)}, more than the limit of {_fmt(limit, unit)}")

    def below(self, value: float, limit: float, unit: str, what: str) -> None:
        if value < limit:
            self.add(under_limit(value, limit),
                     f"{what} is {_fmt(value, unit)}, less than the limit of {_fmt(limit, unit)}")


# ------------------------------------------------------------------ the rules

def _check_finite(root: Node, out: _Findings) -> None:
    """Every number anywhere in the tree (values and attributes) must be finite."""
    for node in walk_nodes(root):
        body = body_of(node)
        if read_number(body.get("value"))[1]:
            out.add(MAX_VIOLATION, f"<{tag_of(node)}> holds {str(body.get('value'))[:24]!r}, "
                                   "which is not a finite number")
        for name, val in attrs_of(node).items():
            if read_number(val)[1]:
                out.add(MAX_VIOLATION, f"<{tag_of(node)}> attribute {str(name)[:24]!r} holds "
                                       f"{str(val)[:24]!r}, which is not a finite number")


def _check_component_types(root: Node, out: _Findings) -> None:
    """Only component types the reference designs use may sit in a "subcomponents" list."""
    for node in walk_nodes(root):
        if tag_of(node) != "subcomponents":
            continue
        for c in children_of(node):
            t = tag_of(c)
            if t not in L.KNOWN_COMPONENT_TYPES:
                out.add(YES_NO_VIOLATION, f"<{t[:40]}> is not a known OpenRocket component type")


def _check_fin_count(name: str, comp: Node, out: _Findings) -> None:
    """1 to 8 fins, a whole number. A count within a millionth of a whole
    number is that number. A count that is not whole costs at least a yes/no
    violation, and more when it is also past the 8-fin limit, so 20.5 fins
    never scores better than 8.5 fins."""
    for tag in ("fincount", "instancecount"):
        n = _field(comp, tag)
        if n is None:
            continue
        whole = round(n)
        if abs(n - whole) <= L.FIN_COUNT_WHOLE_TOLERANCE:
            n = float(whole)
        if n < L.FIN_COUNT_MIN:
            out.add(MAX_VIOLATION, f"{name} has {n:.6g} fins; a fin set needs at least {L.FIN_COUNT_MIN}")
        elif n != whole:
            out.add(max(YES_NO_VIOLATION, over_limit(n, L.FIN_COUNT_MAX)),
                    f"{name} has {n:.6g} fins; a fin count must be a whole number"
                    + (f" no more than {L.FIN_COUNT_MAX}" if n > L.FIN_COUNT_MAX else ""))
        else:
            out.above(n, L.FIN_COUNT_MAX, "fins", f"{name}'s fin count")


def _body_radius(parent: Optional[Node], largest: Optional[float]) -> Optional[float]:
    """Radius of the part a fin set is attached to; the rocket's widest part
    when that radius is "auto" or unknown."""
    r = None
    if parent is not None:
        t = tag_of(parent)
        if t == "bodytube":
            r = _field(parent, "radius")
        elif t in ("innertube", "tubecoupler"):
            r = _field(parent, "outerradius")
        elif t == "nosecone":
            r = _field(parent, "aftradius")
        elif t == "transition":
            r = max((x for x in (_field(parent, "foreradius"), _field(parent, "aftradius")) if x),
                    default=None)
    return r if r is not None and r > 0 else largest


def _fin_points(name: str, comp: Node, out: _Findings) -> Optional[float]:
    """Check a freeform fin's outline. Returns its span (largest y), or None."""
    holder = last_child(comp, "finpoints")
    if holder is None:
        return None
    points = children_of(holder)
    if len(points) > L.FIN_POINTS_MAX:
        out.above(float(len(points)), L.FIN_POINTS_MAX, "points", f"{name}'s outline")
        return None
    worst, span, missing = 0.0, None, 0
    for p in points:
        x, _ = read_number(attrs_of(p).get("x"))
        y, _ = read_number(attrs_of(p).get("y"))
        if x is None or y is None:
            missing += 1
            continue
        worst = max(worst, abs(x), abs(y))
        span = y if span is None else max(span, y)
    if missing:
        out.add(MAX_VIOLATION, f"{name} has {missing} outline point(s) without a usable x and y")
    out.above(worst, L.FIN_POINT_COORD_MAX_M, "m", f"{name}'s farthest outline point")
    return span


def _bulk_density(comp: Node, materials: MaterialTable) -> Optional[tuple[float, str]]:
    """(density in kg/m3, material name) of the bulk material a shell or fin
    set is made of, as it will fly: the table's density for a name the table
    knows (the cleaning writes it), else the written one. None when the part names no material OpenRocket uses,
    so it keeps OpenRocket's default material."""
    found = None
    for mtag, kind, mname, density, hit in _materials_of(comp, materials):
        if mtag != "material" or kind != "bulk":
            continue
        d = hit.density if hit is not None else read_number(density)[0]
        if d is not None and d >= 0:
            found = (float(d), mname)
    return found


def _check_areal_density(name: str, comp: Node, thickness: float, limit: float, what: str,
                         materials: MaterialTable, out: _Findings) -> None:
    """A wall or fin must weigh at least `limit` kg per square metre (thickness
    times density): a film of foam is not a rocket part."""
    found = _bulk_density(comp, materials)
    if found is None or thickness < 0:
        return
    density, mname = found
    areal = thickness * density
    if areal < limit:
        out.add(under_limit(areal, limit),
                f"{name}'s {what} {'weigh' if what.endswith('s') else 'weighs'} {areal:.4g} kg/m2 ({_fmt(thickness, 'mm')} of {mname[:60]!r} at "
                f"{density:.4g} kg/m3), less than the limit of {limit:g} kg/m2: make it thicker or use a "
                f"denser material")


def _check_fin_set(name: str, comp: Node, parent: Optional[Node], largest: Optional[float],
                   out: _Findings, mass_overridden: bool = False,
                   materials: Optional[MaterialTable] = None) -> None:
    _check_fin_count(name, comp, out)
    cant = _field(comp, "cant")
    if cant is not None:
        out.above(abs(cant), L.FIN_CANT_MAX_DEG, "deg", f"{name}'s cant angle (either way)")
    thick = _field(comp, "thickness")
    if thick is not None:
        out.below(thick, L.FIN_THICKNESS_MIN_M, "mm", f"{name}'s fin thickness")
        if not mass_overridden and materials is not None:
            _check_areal_density(name, comp, thick, L.FIN_AREAL_DENSITY_MIN_KG_M2, "fins", materials, out)
    if tag_of(comp) == "freeformfinset":
        span = _fin_points(name, comp, out)
    else:
        span = _field(comp, "height")
    radius = _body_radius(parent, largest)
    if span is not None and span > 0 and radius:
        ratio = span / (2 * radius)
        if ratio > L.FIN_SPAN_PER_DIAMETER_MAX:
            out.add(over_limit(ratio, L.FIN_SPAN_PER_DIAMETER_MAX),
                    f"{name}'s fins reach out {_fmt(span, 'mm')} from a body {_fmt(2 * radius, 'mm')} wide, "
                    f"{ratio:.3g} times its width (limit {L.FIN_SPAN_PER_DIAMETER_MAX:g} times)")


def _check_ranges(name: str, comp: Node, out: _Findings) -> None:
    t = tag_of(comp)
    for c in children_of(comp):
        field = tag_of(c)
        if field in NON_NEGATIVE:
            x = read_number(body_of(c).get("value"))[0]
            if x is not None and x < 0:
                out.add(MAX_VIOLATION, f"{name}'s {field} is {_fmt(x, _UNITS.get(field, 'm'))}; "
                                       "a size cannot be negative")
    for types, field, low, high, unit, zero_is_auto in _RANGE_RULES:
        if types is not None and t not in types:
            continue
        x = _field(comp, field)
        if x is None or x < 0 or (zero_is_auto and x == 0):
            continue
        if low is not None:
            out.below(x, low, unit, f"{name}'s {field}")
        if high is not None:
            out.above(x, high, unit, f"{name}'s {field}")


def _check_wall(name: str, comp: Node, mass_overridden: bool, out: _Findings,
                materials: Optional[MaterialTable] = None) -> None:
    """Outer shell walls must not be paper-thin: a thin wall makes a light
    rocket. A wall of exactly 0 mm is a shell with no wall and so no mass, the
    far end of that trick, so it costs the most (as a zero value does,
    DESIGN.md). The word "filled" is OpenRocket's solid part and is fine.

    A part whose mass is overridden is skipped: its wall no longer changes
    its mass, so no wall, thin or zero, can gain anything there. The same
    holds for a 0 mm wall on a part of length 0 (one reference rocket uses
    such an empty tube to hold other parts).

    With the material table, the wall must also weigh at least
    limits.WALL_AREAL_DENSITY_MIN_KG_M2 (thickness times density), so a
    catalogue-thin wall of foam does not pass as a light rocket.
    """
    if tag_of(comp) not in SHELL_WALLS or mass_overridden:
        return
    c = last_child(comp, "thickness")
    if c is None:
        return
    raw = body_of(c).get("value")
    if isinstance(raw, str) and raw.strip().lower() == "filled":
        return
    wall = read_number(raw)[0]
    if wall is None or wall < 0:
        return   # a word is OpenRocket's default; a negative size is reported by _check_ranges
    if wall == 0:
        if _field(comp, "length") == 0:
            return   # a part with no length has no shell to weigh, so its wall changes nothing
        out.add(MAX_VIOLATION, f"{name}'s wall is 0 mm, a shell with no mass; write \"filled\" "
                               f"for a solid part or a wall of at least {_fmt(L.WALL_MIN_M, 'mm')}")
    else:
        out.below(wall, L.WALL_MIN_M, "mm", f"{name}'s wall")
    if materials is not None:
        _check_areal_density(name, comp, wall, L.WALL_AREAL_DENSITY_MIN_KG_M2, "wall", materials, out)


def _instances(comp: Node) -> float:
    """How many copies of a part OpenRocket makes ("instancecount"; 1 when
    missing or not a usable number)."""
    n = _field(comp, "instancecount")
    return n if n is not None and n >= 1 else 1.0


def _check_counts(comps: list, out: _Findings) -> dict[str, float]:
    """Not too many parts, not too many copies of one part, and only a few
    launch lugs and rail buttons. Each count past its limit is judged with
    the "no more than" formula. Returns the counts, for info."""
    total = len(comps)
    out.above(float(total), float(L.COMPONENTS_MAX), "parts",
              "the number of parts in the design (every component inside the rocket)")
    lugs = buttons = 0.0
    worst: Optional[tuple[float, str]] = None
    seen: dict[str, int] = {}
    for comp, _ in comps:
        t = tag_of(comp)
        if t not in L.KNOWN_COMPONENT_TYPES:
            continue
        seen[t] = seen.get(t, 0) + 1
        n = _instances(comp)
        if t == "launchlug":
            lugs += n
        elif t == "railbutton":
            buttons += n
        if t not in FIN_SETS and t != "tubefinset" and n > L.PART_INSTANCES_MAX:
            if worst is None or n > worst[0]:
                worst = (n, f"{t} #{seen[t]}")
    if worst is not None:
        out.above(worst[0], float(L.PART_INSTANCES_MAX), "copies", f"{worst[1]}'s instance count")
    out.above(lugs, float(L.LAUNCH_LUG_COUNT_MAX), "lugs", "the number of launch lugs (copies counted)")
    out.above(buttons, float(L.RAIL_BUTTON_COUNT_MAX), "buttons", "the number of rail buttons (copies counted)")
    return {"parts": total, "launch_lugs": lugs, "rail_buttons": buttons}


def _check_tube_fins(name: str, comp: Node, parent: Optional[Node], largest: Optional[float],
                     out: _Findings) -> None:
    """Tube fins may be no wider than the body they sit on ("auto" takes the body's size)."""
    r = _field(comp, "radius")
    body = _body_radius(parent, largest)
    if r is None or r <= 0 or not body:
        return
    ratio = r / body
    if ratio > L.TUBE_FIN_RADIUS_PER_BODY_MAX:
        out.add(over_limit(ratio, L.TUBE_FIN_RADIUS_PER_BODY_MAX),
                f"{name}'s tubes are {_fmt(r, 'mm')} in radius on a body {_fmt(body, 'mm')} in radius, "
                f"{ratio:.3g} times (limit {L.TUBE_FIN_RADIUS_PER_BODY_MAX:g} times): make the tube fins "
                f"narrower or write \"auto\"")


def _materials_of(comp: Node, materials: MaterialTable):
    """(material tag, type OpenRocket loads, name, written density, table
    match) for each material node of a component that OpenRocket would use:
    its type is the slot's (or none) and its name names a material."""
    for c in children_of(comp):
        mtag = tag_of(c)
        if mtag not in MATERIAL_TAGS:
            continue
        a = attrs_of(c)
        kind = loaded_type(tag_of(comp), mtag, a.get("type"))
        name = name_text(value_of(c))
        if kind is None or name is None or means_no_material(name):
            continue
        yield mtag, kind, name, a.get("density"), materials.match(kind, name)


def _check_materials(name: str, comp: Node, mass_overridden: bool, out: _Findings,
                     materials: MaterialTable) -> None:
    """A density must never be negative. The cleaning gives every material
    the table knows its table density, so the physical ranges (limits.py,
    "material densities") are judged only on names the table does not know,
    and are skipped on a part whose mass is overridden, because OpenRocket
    then never uses the density."""
    for c in children_of(comp):
        if tag_of(c) not in MATERIAL_TAGS:
            continue
        d, _ = read_number(attrs_of(c).get("density"))
        if d is not None and d < 0:
            out.add(MAX_VIOLATION, f"{name}'s {tag_of(c)} density is {d:.4g}; a density cannot be negative")
    if mass_overridden:
        return
    for mtag, kind, _, density, hit in _materials_of(comp, materials):
        d, _ = read_number(density)
        if hit is not None or d is None or d < 0:
            continue
        what = f"{name}'s {mtag} density"
        if kind == "bulk":
            out.below(d, L.BULK_DENSITY_MIN_KG_M3, "kg/m3", what)
            out.above(d, L.BULK_DENSITY_MAX_KG_M3, "kg/m3", what)
        elif kind == "surface":
            out.above(d, L.SURFACE_DENSITY_MAX_KG_M2, "kg/m2", what)
        elif kind == "line":
            out.above(d, L.LINE_DENSITY_MAX_KG_M, "kg/m", what)


def _collect_unknown_names(name: str, comp: Node, own_mass_overridden: bool, materials: MaterialTable,
                           found: dict[tuple[str, str], dict[str, Any]]) -> None:
    """Record every material name on this part that the table does not know,
    keyed by its type and its name up to case and spacing."""
    for mtag, kind, mname, density, hit in _materials_of(comp, materials):
        if hit is not None:
            continue
        rec = found.setdefault((kind, loose_name(mname[:200])), {
            "name": mname, "kind": kind, "parts": [], "counted_parts": [], "density": density})
        rec["parts"].append(f"{name}'s {mtag}")
        if not own_mass_overridden:
            rec["counted_parts"].append(f"{name}'s {mtag}")


def _shown_parts(parts: list[str]) -> str:
    return ", ".join(parts[:3]) + (f" and {len(parts) - 3} more" if len(parts) > 3 else "")


def check_material_names(found: dict[tuple[str, str], dict[str, Any]],
                         materials: MaterialTable) -> tuple[list[tuple[float, str]], list[str]]:
    """Every material name must be one the material table knows, so the reward
    can give it its real density.

    `found` is what _collect_unknown_names recorded. Each distinct unknown name
    is a yes/no violation (at most MATERIAL_NAMES_COUNTED_MAX of them count),
    unless every part using it overrides its own mass: the material then does
    not change the rocket, and the name is only noted. Returns (violation
    size, reason) pairs and the notes.
    """
    pairs: list[tuple[float, str]] = []
    notes: list[str] = []
    counted = [r for r in found.values() if r["counted_parts"]]
    for r in found.values():
        if r["counted_parts"]:
            continue
        notes.append(f"material {r['name'][:60]!r} ({r['kind']}) is not in the material table, but every part "
                     f"using it ({_shown_parts(r['parts'])}) overrides its own mass, so it changes nothing")
    for i, r in enumerate(counted[:MATERIAL_NAMES_COUNTED_MAX]):
        d, _ = read_number(r["density"])
        written = f"{d:.4g} {UNITS[r['kind']]}" if d is not None else "no usable density"
        near = materials.closest(r["kind"], r["name"])
        verb = "uses" if len(r["counted_parts"]) == 1 else "use"
        reason = (f"{_shown_parts(r['counted_parts'])} {verb} material {r['name'][:60]!r}, which is not in the "
                  f"material table of {r['kind']} materials, so the reward cannot give it its real density "
                  f"(the design wrote {written}); "
                  + (f"use a known material name, for example {near!r}" if near else
                     f"no {r['kind']} material in OpenRocket's list is spelled like it, so pick one from that "
                     f"list ({NAME_LIST_HINT})"))
        if i == MATERIAL_NAMES_COUNTED_MAX - 1 and len(counted) > MATERIAL_NAMES_COUNTED_MAX:
            rest = counted[MATERIAL_NAMES_COUNTED_MAX:]
            reason += (f"; {len(rest)} more unknown material name(s) are not counted: "
                       + ", ".join(repr(x["name"][:40]) for x in rest[:3]) + (" ..." if len(rest) > 3 else ""))
        pairs.append((YES_NO_VIOLATION, reason))
    return pairs, notes


def _cluster_count(component: Node) -> float:
    """How many motors one motor node stands for in a cluster mount:
    "single" 1, "double" 2, "4-ring" 4, and so on. Unknown names count as 1."""
    c = last_child(component, "clusterconfiguration")
    name = body_of(c).get("value") if c is not None else None
    if not isinstance(name, str):
        return 1.0
    name = name.strip().lower()
    m = re.match(r"(\d{1,3})", name)
    if m:
        return float(max(1, int(m.group(1))))
    return {"double": 2.0, "triangle": 3.0, "square": 4.0}.get(name, 1.0)


def _motor_multiplicity(rocket: Node) -> dict[int, float]:
    """For each motor node (by id), how many real motors it stands for: the
    cluster size of its mount times the copies made by pods and side boosters."""
    out: dict[int, float] = {}
    for comp, parents in _components(rocket):
        mounts = children_named(comp, "motormount")
        if not mounts:
            continue
        n = _cluster_count(comp)
        for p in parents + (comp,):
            if tag_of(p) in MULTI_INSTANCE:
                k = _field(p, "instancecount")
                if k is not None and k >= 1:
                    n *= k
        for mount in mounts:
            for m in children_of(mount):
                if tag_of(m) == "motor":
                    out[id(m)] = n
    return out


def _check_total_impulse(root: Node, rocket: Node, table: Any, out: _Findings) -> float:
    """Total impulse of every motor that fires in the flown configuration,
    clusters and pods counted, must stay within the contract limit. Motors the
    table does not know are left to stage 3."""
    counts = _motor_multiplicity(rocket)
    total = 0.0
    for m in flown_motors(root):
        if not is_node(m):
            continue
        key = table.resolve(last_text(m, "motor_id"), last_text(m, "manufacturer"), last_text(m, "designation"))
        if key is None:
            continue
        info = table.get(key) or {}
        imp, _ = read_number(info.get("total_impulse_ns"))
        if imp is not None and imp > 0:
            total += imp * counts.get(id(m), 1.0)
    out.above(total, L.TOTAL_IMPULSE_MAX_NS, "Ns", "the total impulse of the flown motors")
    return total


# ------------------------------------------------------------------ the stage

def check_limits(root: Node, table: Any, materials: Optional[MaterialTable] = None) -> StageCheck:
    """Stage 4: check every size, count, type and material name against limits.py.

    `root` is the cleaned design tree (root tag "openrocket"); `table` is the
    motor table (motors.MotorTable); `materials` is the material table (by
    default the packaged one). Returns a StageCheck whose credit is
    1 / (1 + sum of violation sizes); it passes only with no violation.
    Unknown material names on parts that override their own mass are listed
    in info["notes"] without a cost.
    """
    materials = materials if materials is not None else default_material_table()
    out = _Findings()
    if not is_node(root):
        out.add(MAX_VIOLATION, "the design is not a tree of parts")
        return _result(out, {})
    rocket = rocket_of(root)
    _check_finite(root, out)
    _check_component_types(root, out)
    info: dict[str, Any] = {}
    if rocket is not None:
        comps = list(_components(rocket))
        largest = max((x for c, _ in comps if tag_of(c) in ("bodytube", "nosecone", "transition")
                       for x in (_field(c, "radius"), _field(c, "aftradius"), _field(c, "foreradius"))
                       if x is not None and 0 < x <= L.TUBE_RADIUS_MAX_M), default=None)
        seen: dict[str, int] = {}
        unknown_names: dict[tuple[str, str], dict[str, Any]] = {}
        # Parts whose mass a part around them overrides, found in one pass
        # (parents come before children), so deep trees stay fast.
        covered: set[int] = set()
        for comp, parents in comps:
            if parents and (id(parents[-1]) in covered or _overrides_inside(parents[-1])):
                covered.add(id(comp))
        for comp, parents in comps:
            t = tag_of(comp)
            if t not in L.KNOWN_COMPONENT_TYPES:
                continue
            seen[t] = seen.get(t, 0) + 1
            name = f"{t} #{seen[t]}"
            own = _overrides_mass(comp)
            overridden = id(comp) in covered or own
            if t == "tubefinset":
                _check_fin_count(name, comp, out)
                _check_tube_fins(name, comp, parents[-1] if parents else None, largest, out)
            if t in FIN_SETS:
                _check_fin_set(name, comp, parents[-1] if parents else None, largest, out, overridden, materials)
            _check_ranges(name, comp, out)
            _check_wall(name, comp, overridden, out, materials)
            _check_materials(name, comp, overridden, out, materials)
            _collect_unknown_names(name, comp, own, materials, unknown_names)
        info["total_impulse_ns"] = round(_check_total_impulse(root, rocket, table, out), 3)
        info["components"] = len(comps)
        info["counts"] = _check_counts(comps, out)
        pairs, notes = check_material_names(unknown_names, materials)
        # Listed first: naming a real material fixes its density too.
        out.sizes[:0] = [size for size, _ in pairs]
        out.reasons[:0] = [reason for _, reason in pairs]
        if notes:
            info["notes"] = notes
    return _result(out, info)


def _result(out: _Findings, info: dict) -> StageCheck:
    info["violations"] = len(out.sizes)
    if not out.sizes:
        return StageCheck(STAGE, True, credit=1.0, info=info)
    reasons = list(dict.fromkeys(out.reasons))
    if len(reasons) > MAX_REASONS:
        reasons = reasons[:MAX_REASONS] + [f"... and {len(reasons) - MAX_REASONS} more limit problems"]
    return StageCheck(STAGE, False, credit=credit_from_violations(out.sizes), reasons=reasons, info=info)
