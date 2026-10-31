"""Turn a design JSON into positioned parts. Pure Python, no CAD library.

The design JSON lists parts and their sizes but not where each part sits. This file
decides the positions, using the same rules OpenRocket uses by default:

  * external parts (nose cone, body tubes, transitions) stack end to end along the
    rocket axis, in the order they appear, starting at the nose tip (x = 0)
  * a fin set sits at the back end of the tube that contains it
  * a missing diameter is copied from the neighbouring part ("auto" in OpenRocket)

Everything here is in METERS. cad.py converts to millimeters when it builds solids.
The .ork builder can reuse layout() so both agree on where every part is.
"""
import math
from dataclasses import dataclass, field

# the three part types that make up the outside of the rocket
EXTERNAL = ("nosecone", "bodytube", "transition")

# fin types the data uses that we cannot build, and why
UNSUPPORTED = {
    "freeformfinset": "free-form fins: the design JSON has no fin outline points",
    "ellipticalfin": "elliptical fins are not built yet",
    "tubefin": "tube fins are not built yet",
    "pod_set": "side pods / boosters are not built yet",
}

# parts that are inside the rocket and have no size in the JSON, so no mass either
NO_SIZE = ("centeringring", "bulkhead", "engineblock", "parachute", "streamer",
           "launchlug", "railbutton", "shockcord", "tubecoupler")

# OpenRocket's default shape parameter for each nose shape, used when the JSON leaves it out
DEFAULT_SHAPE_PARAM = {"ogive": 1.0, "power": 0.5, "parabolic": 1.0, "haack": 0.0}


class DesignError(Exception):
    """The design JSON is malformed: it cannot be turned into a rocket at all."""


@dataclass
class Part:
    kind: str                 # "nosecone", "bodytube", "transition" or "fins"
    name: str
    x0: float                 # front end, meters behind the nose tip
    length: float             # along the axis, meters
    r_fore: float = 0.0       # outer radius at the front end
    r_aft: float = 0.0        # outer radius at the back end
    wall: float = None        # wall thickness (tubes, nose cones), None if not given
    material: str = None
    shape: str = None         # nose / transition shape
    shape_param: float = None
    fin: dict = None          # fins only: root, tip, span, sweep, thickness, count
    host: int = None          # fins only: index of the tube they are attached to
    guessed: bool = False     # True if a diameter was copied from a neighbour, not given

    @property
    def x1(self):
        return self.x0 + self.length


@dataclass
class Layout:
    parts: list = field(default_factory=list)          # Part, in order nose to tail
    internal_tubes: list = field(default_factory=list)  # (name, comp, x_center, host index)
    point_masses: list = field(default_factory=list)    # (name, mass_kg, x_center)
    unknown_mass: list = field(default_factory=list)    # names of parts with no size
    unsupported: list = field(default_factory=list)     # reasons we cannot build it
    assumptions: list = field(default_factory=list)     # every guess we made
    failures: list = field(default_factory=list)        # real design problems found here


# ---------------------------------------------------------------- nose cone math

def nose_radius(shape, param, length, radius, x):
    """Radius of a nose cone at distance x behind its tip (same formulas as OpenRocket)."""
    x = min(max(x, 0.0), length)
    if shape == "conical" or (shape == "ogive" and param < 0.001):
        return radius * x / length
    if shape == "ogive":
        # a circular arc; param 1.0 is the tangent ogive, smaller values are blunter
        big_r = math.sqrt((length ** 2 + radius ** 2)
                          * (((2 - param) * length) ** 2 + (param * radius) ** 2)
                          / (4 * (param * radius) ** 2))
        lp = length / param
        y0 = math.sqrt(max(big_r ** 2 - lp ** 2, 0.0))
        return math.sqrt(max(big_r ** 2 - (lp - x) ** 2, 0.0)) - y0
    if shape == "ellipsoid":
        xs = x * radius / length
        return math.sqrt(max(2 * radius * xs - xs * xs, 0.0))
    if shape == "power":
        if param <= 1e-5:
            return 0.0 if x <= 1e-5 else radius
        return radius * (x / length) ** param
    if shape == "parabolic":
        k = x / length
        return radius * (2 * k - param * k * k) / (2 - param)
    if shape == "haack":
        theta = math.acos(1 - 2 * x / length)
        inner = (theta - math.sin(2 * theta) / 2 + param * math.sin(theta) ** 3) / math.pi
        return radius * math.sqrt(max(inner, 0.0))
    raise ValueError(f"unknown nose shape {shape!r}")


# ---------------------------------------------------------------- the layout

def _num(c, key):
    v = c.get(key)
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _collect_external(components, out, lay):
    """Walk the tree and list the external parts in order. Stages are stacked in the
    order they appear; anything unsupported is recorded."""
    for c in components:
        if not isinstance(c, dict):
            raise DesignError("a component is not a JSON object")
        t = c.get("type")
        if t in UNSUPPORTED:
            lay.unsupported.append(f"{c.get('name', t)}: {UNSUPPORTED[t]}")
        if t == "stage_marker":
            _collect_external(c.get("contains", []), out, lay)
        elif t in EXTERNAL:
            out.append(c)


def layout(design):
    """design (dict) -> Layout. Raises DesignError if it is not a rocket at all."""
    if not isinstance(design, dict) or not isinstance(design.get("components"), list):
        raise DesignError("design must be a JSON object with a 'components' list")
    lay = Layout()
    ext = []
    _collect_external(design["components"], ext, lay)
    if not ext:
        raise DesignError("no nose cone, body tube or transition found")

    # every external part needs a real length
    for c in ext:
        length = _num(c, "length_m")
        if not length or length <= 0:
            raise DesignError(f"{c.get('name', c['type'])}: length_m missing or not positive")

    # 1. radii as given (None where missing)
    rf, ra = [], []
    for c in ext:
        t = c["type"]
        if t == "nosecone":
            rf.append(0.0)
            ra.append(_num(c, "base_radius_m"))
        elif t == "bodytube":
            d = _num(c, "outer_d_m")
            rf.append(d / 2 if d else None)
            ra.append(d / 2 if d else None)
        else:  # transition
            fd, ad = _num(c, "fore_d_m"), _num(c, "aft_d_m")
            rf.append(fd / 2 if fd else None)
            ra.append(ad / 2 if ad else None)

    # 2. fill missing radii from neighbours, like OpenRocket's "automatic" setting:
    #    first from the part in front, then from the part behind
    guessed = [False] * len(ext)
    for _ in range(len(ext) + 1):
        for i, c in enumerate(ext):
            if c["type"] == "bodytube":  # a tube has one diameter
                if rf[i] is None and ra[i] is not None:
                    rf[i] = ra[i]
                if ra[i] is None and rf[i] is not None:
                    ra[i] = rf[i]
            if rf[i] is None and i > 0 and ra[i - 1] is not None:
                rf[i] = ra[i - 1]
                guessed[i] = True
                lay.assumptions.append(f"{c.get('name')}: front diameter copied from the part in front")
            if ra[i] is None and i + 1 < len(ext) and rf[i + 1] is not None:
                ra[i] = rf[i + 1]
                guessed[i] = True
                lay.assumptions.append(f"{c.get('name')}: back diameter copied from the part behind")
    for i, c in enumerate(ext):
        if rf[i] is None or ra[i] is None:
            lay.unsupported.append(f"{c.get('name')}: diameter missing and no neighbour to copy it from")
            return lay
        if ra[i] <= 0 or rf[i] < 0:
            raise DesignError(f"{c.get('name')}: diameter must be positive")

    # 3. stack the external parts nose to tail
    x = 0.0
    for i, c in enumerate(ext):
        length = _num(c, "length_m")
        p = Part(kind=c["type"], name=c.get("name", c["type"]), x0=x, length=length,
                 r_fore=rf[i], r_aft=ra[i], wall=_num(c, "wall_thickness_m"),
                 material=c.get("material"), guessed=guessed[i])
        if c["type"] == "nosecone":
            p.shape = c.get("shape")
            p.shape_param = _num(c, "shape_param")
            if p.shape_param is None and p.shape in DEFAULT_SHAPE_PARAM:
                p.shape_param = DEFAULT_SHAPE_PARAM[p.shape]
                lay.assumptions.append(f"{p.name}: shape_param missing, used OpenRocket default {p.shape_param}")
        if c["type"] == "transition" and c.get("shape") not in (None, "conical"):
            lay.assumptions.append(f"{p.name}: {c.get('shape')} transition built as a straight cone")
        if c["type"] == "bodytube" and p.wall is None:
            lay.unsupported.append(f"{p.name}: wall_thickness_m missing")
        elif c["type"] == "bodytube" and p.wall <= 0:
            # OpenRocket files sometimes use 0-wall tubes as weightless placeholders,
            # but a real tube cannot have no wall
            lay.failures.append(f"{p.name}: wall thickness is 0, a real tube needs a wall")
        lay.parts.append(p)
        x += length

    # 4. things attached to or inside each external part
    for host_i, c in enumerate(ext):
        _attach(c.get("contains", []), host_i, lay, inner_r=_inner_radius(lay.parts[host_i]))

    # several fin sets on one tube: the design does not say where each one sits along the
    # tube or how far it is rotated, so stacking them all at the back would be a made-up
    # collision. We cannot judge those designs.
    per_tube = {}
    for p in lay.parts:
        if p.kind == "fins":
            per_tube.setdefault(p.host, []).append(p.name)
    for host_i, names in per_tube.items():
        if len(names) > 1:
            lay.unsupported.append(f"{lay.parts[host_i].name}: {len(names)} fin sets on one tube, "
                                   f"positions not in the design")
    return lay


def _inner_radius(part):
    """Inside radius of a tube, or None if we do not know it."""
    if part.kind != "bodytube" or part.wall is None:
        return None
    return part.r_aft - part.wall


def _attach(components, host_i, lay, inner_r):
    host = lay.parts[host_i]
    for c in components:
        if not isinstance(c, dict):
            raise DesignError("a component is not a JSON object")
        t = c.get("type")
        name = c.get("name", t)
        if t == "trapezoidfin":
            if host.kind != "bodytube":
                lay.unsupported.append(f"{name}: fins on a {host.kind} are not built yet")
                continue
            f = {k: _num(c, k) for k in ("root_chord_m", "tip_chord_m", "span_m", "sweep_m", "thickness_m")}
            missing = [k for k, v in f.items() if v is None]
            if missing:
                raise DesignError(f"{name}: missing {', '.join(missing)}")
            if min(f["root_chord_m"], f["span_m"], f["thickness_m"]) <= 0 or f["tip_chord_m"] < 0:
                raise DesignError(f"{name}: fin sizes must be positive")
            count = c.get("fin_count")
            if count is None:
                count = 3
                lay.assumptions.append(f"{name}: fin_count missing, used OpenRocket default 3")
            f["count"] = int(round(float(count)))
            # OpenRocket default: the fins' back edge is flush with the back of the tube
            lay.parts.append(Part(kind="fins", name=name, x0=host.x1 - f["root_chord_m"],
                                  length=f["root_chord_m"], r_fore=host.r_aft, r_aft=host.r_aft,
                                  material=c.get("material"), fin=f, host=host_i,
                                  guessed=host.guessed))
        elif t == "innertube":
            d, wall, length = _num(c, "outer_d_m"), _num(c, "wall_thickness_m"), _num(c, "length_m")
            # a real check, independent of where we guess it sits: it must fit inside
            if d is not None and inner_r is not None and d / 2 > inner_r + 1e-4:
                lay.failures.append(f"{name} (outer diameter {d * 1000:.1f} mm) does not fit inside "
                                    f"{host.name} (inner diameter {inner_r * 2000:.1f} mm)")
            if d is not None and wall is not None and length:
                # motor mounts sit at the back of their tube (OpenRocket's usual placement)
                xc = max(host.x1 - length / 2, host.x0)
                lay.internal_tubes.append((name, c, xc, host_i))
                lay.assumptions.append(f"{name}: placed at the back of {host.name}")
            else:
                lay.unknown_mass.append(name)
            # parts nested inside an inner tube are not fit-checked: OpenRocket files often
            # use solid inner tubes as stand-ins for masses, which would give false alarms
            _attach(c.get("contains", []), host_i, lay, inner_r=None)
        elif t == "masscomponent":
            m = _num(c, "mass_kg")
            if m is None:
                lay.unknown_mass.append(name)
            else:
                lay.point_masses.append((name, m, (host.x0 + host.x1) / 2))
                lay.assumptions.append(f"{name}: {m} kg placed at the middle of {host.name}")
            _attach(c.get("contains", []), host_i, lay, inner_r=None)
        elif t in UNSUPPORTED:
            lay.unsupported.append(f"{name}: {UNSUPPORTED[t]}")
        else:
            if t in NO_SIZE:
                lay.unknown_mass.append(name)
            _attach(c.get("contains", []), host_i, lay, inner_r=None)
