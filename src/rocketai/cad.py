"""Pass 1 of the verifier: the CAD gate.

Builds the model's rocket design as real 3D solids with CadQuery, checks the geometry,
and estimates mass and CG. During GRPO, a design that fails here gets reward -0.8 and
is never flown; a design that passes goes on to Pass 2 (OpenRocket).

    from rocketai.cad import cad_gate
    result = cad_gate(design_json_or_dict)

result["status"] is one of
    "pass"         geometry is fine, go on to the flight sim
    "fail"         the design itself is broken (bad JSON, overlap, floating fins, ...): reward -0.8
    "unsupported"  we cannot build this kind of design yet (e.g. free-form fins): no reward given
    "error"        our own code crashed: no reward given, so the model is never punished for our bugs

Units: designs are in meters, the CAD solids are built in millimeters.
Axis: the rocket points along +X, nose tip at x = 0, tail at +x (OpenRocket's convention).
"""
import json
import math
import os
import sqlite3
from dataclasses import dataclass, field

import cadquery as cq
from OCP.BRepExtrema import BRepExtrema_DistShapeShape

try:  # works both as "python src/rocketai/cad.py" and as "from rocketai import cad"
    from rocketai.layout import DesignError, layout, nose_radius
except ImportError:
    from layout import DesignError, layout, nose_radius

M_TO_MM = 1000.0  # designs are in meters, CAD files are in millimeters

FAIL_REWARD = -0.8          # Tier 2 of the reward ladder in the master plan
MIN_SOLID_VOLUME_MM3 = 1.0  # smaller than this = a degenerate, paper-thin solid
MAX_OVERLAP_MM3 = 1.0       # two parts sharing more than this = they collide
MAX_FIN_GAP_MM = 0.5        # fin further than this from its tube = it is floating
NOSE_PROFILE_POINTS = 48    # how finely the nose curve is sampled

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CATALOG = os.path.join(REPO, "data", "catalog.sqlite")

# Densities in kg/m^3: OpenRocket's built-in material values, plus a few from
# data/catalog.sqlite for names OpenRocket does not ship. Keys are lowercase.
DENSITY = {
    "acrylic": 1190, "aluminum": 2700, "balsa": 170, "basswood": 500, "birch": 670,
    "blue tube": 1300, "brass": 8600, "cardboard": 680, "carbon fiber": 1780,
    "cork": 240, "fiberglass": 1850, "kraft phenolic": 950, "maple": 755,
    "paper (office)": 820, "paper": 820, "pine": 530, "plywood (birch)": 630,
    "plywood": 630, "polycarbonate (lexan)": 1200, "polycarbonate": 1200,
    "polystyrene": 1050, "polystyrene ps": 1050, "styrene plastic": 1050, "pvc": 1390,
    "spruce": 450, "steel": 7850, "titanium": 4500, "quantum tubing": 1050,
    "pla": 1250, "abs": 1050, "petg - 100% infill": 1270, "polyethylene ldpe": 920,
    # from data/catalog.sqlite
    "aircraft plywood (birch)": 725, "1/8 aircraft plywood": 725, "lite plywood": 352,
    "fiber": 657, "spiral/glassine": 796, "kraft paper": 796,
}


# ---------------------------------------------------------------- materials

def density(material):
    """kg/m^3 for a material name, or None if we do not know it (never a silent default)."""
    if not material:
        return None
    key = material.lower().strip()
    if key.startswith("rs: "):  # Rocksim imports prefix names with "RS: "
        key = key[4:]
    if key in DENSITY:
        return DENSITY[key]
    if os.path.exists(CATALOG):
        with sqlite3.connect(CATALOG) as db:
            row = db.execute("select avg(density) from parts where lower(material) = ? "
                             "and material_type = 'BULK' and density_unit = 'kg/m3'",
                             (material.lower(),)).fetchone()
        # the catalog has a few broken entries (e.g. paper at 0.0011 kg/m^3); ignore those
        if row and row[0] and 50 <= row[0] <= 20000:
            return row[0]
    return None


# ---------------------------------------------------------------- solids

def body_tube(length_m, outer_d_m, wall_m):
    """Hollow cylinder along the X axis, starting at x = 0."""
    length = length_m * M_TO_MM
    r_out = outer_d_m * M_TO_MM / 2
    r_in = r_out - wall_m * M_TO_MM
    wp = cq.Workplane("YZ").circle(r_out)
    if r_in > 0:  # a wall as thick as the radius means a solid rod
        wp = wp.circle(r_in)
    return wp.extrude(length)


def _revolve_profile(points_mm):
    """Spin a 2D outline (x, r) around the X axis into a solid. The outline must start
    and end on the axis (r = 0)."""
    pts = [points_mm[0]]
    for p in points_mm[1:]:  # drop repeated points, CadQuery rejects zero-length edges
        if abs(p[0] - pts[-1][0]) > 1e-9 or abs(p[1] - pts[-1][1]) > 1e-9:
            pts.append(p)
    # drop points that sit on a straight line between their neighbours (a cone's side
    # would otherwise be 48 touching pieces of the same surface, which is not a valid solid)
    straight = [pts[0]]
    for i in range(1, len(pts) - 1):
        (x0, y0), (x1, y1), (x2, y2) = straight[-1], pts[i], pts[i + 1]
        if abs((x1 - x0) * (y2 - y0) - (y1 - y0) * (x2 - x0)) > 1e-6:
            straight.append(pts[i])
    pts = straight + [pts[-1]]
    return cq.Workplane("XY").polyline(pts).close().revolve(360, (0, 0, 0), (1, 0, 0))


def nose_cone(part):
    length, radius = part.length * M_TO_MM, part.r_aft * M_TO_MM
    profile = [(0.0, 0.0)]
    for i in range(1, NOSE_PROFILE_POINTS + 1):
        x = length * i / NOSE_PROFILE_POINTS
        profile.append((x, nose_radius(part.shape, part.shape_param, length, radius, x)))
    profile.append((length, 0.0))
    return _revolve_profile(profile)


def transition(part):
    length = part.length * M_TO_MM
    rf, ra = part.r_fore * M_TO_MM, part.r_aft * M_TO_MM
    return _revolve_profile([(0.0, 0.0), (0.0, rf), (length, ra), (length, 0.0)])


def one_fin(part, angle_deg):
    """One trapezoid fin. Drawn flat in the XY plane with its root edge on the tube's
    outer surface (y = tube radius), thickened equally to both sides, then rotated
    around the rocket axis to its place."""
    f = part.fin
    r = part.r_aft * M_TO_MM
    root, tip = f["root_chord_m"] * M_TO_MM, f["tip_chord_m"] * M_TO_MM
    span, sweep = f["span_m"] * M_TO_MM, f["sweep_m"] * M_TO_MM
    t = f["thickness_m"] * M_TO_MM
    outline = [(0.0, r), (root, r), (sweep + tip, r + span), (sweep, r + span)]
    if tip == 0:  # a triangle fin: the two tip corners are the same point
        outline = outline[:3]
    fin = cq.Workplane("XY").polyline(outline).close().extrude(t / 2, both=True)
    return fin.rotate((0, 0, 0), (1, 0, 0), angle_deg)


@dataclass
class Solid:
    name: str
    kind: str        # nosecone, bodytube, transition, fin
    shape: object    # the CadQuery shape, in mm
    part: object     # the layout Part it came from
    angle: float = 0.0  # fins only: angle around the axis, degrees


@dataclass
class Built:
    solids: list = field(default_factory=list)
    lay: object = None
    uncertain: list = field(default_factory=list)  # problems that depend on a guessed size


def build(lay):
    """Layout -> 3D solids, each moved to its place along the axis."""
    built = Built(lay=lay)
    for p in lay.parts:
        dx = p.x0 * M_TO_MM
        if p.kind == "nosecone":
            built.solids.append(Solid(p.name, p.kind, nose_cone(p).translate((dx, 0, 0)).val(), p))
        elif p.kind == "bodytube":
            if not p.wall or p.wall <= 0:
                continue  # already reported by layout(); a 0-wall tube cannot be built
            tube = body_tube(p.length, p.r_aft * 2, p.wall).translate((dx, 0, 0))
            built.solids.append(Solid(p.name, p.kind, tube.val(), p))
        elif p.kind == "transition":
            built.solids.append(Solid(p.name, p.kind, transition(p).translate((dx, 0, 0)).val(), p))
        elif p.kind == "fins":
            n = p.fin["count"]
            for k in range(n):
                angle = 360.0 * k / n
                fin = one_fin(p, angle).translate((dx, 0, 0))
                built.solids.append(Solid(f"{p.name} #{k + 1}", "fin", fin.val(), p, angle))
    return built


# ---------------------------------------------------------------- checks

def _distance_mm(a, b):
    d = BRepExtrema_DistShapeShape(a.wrapped, b.wrapped)
    d.Perform()
    return d.Value()


def _boxes_touch(a, b, pad=0.1):
    ba, bb = a.BoundingBox(), b.BoundingBox()
    return not (ba.xmax + pad < bb.xmin or bb.xmax + pad < ba.xmin or
                ba.ymax + pad < bb.ymin or bb.ymax + pad < ba.ymin or
                ba.zmax + pad < bb.zmin or bb.zmax + pad < ba.zmin)


def check(built):
    """Run the geometry checks. Returns a list of failure messages (empty = good)."""
    failures = list(built.lay.failures)  # e.g. motor tube does not fit, found in layout
    s = built.solids

    # 1. every solid is a valid, closed, real solid
    for x in s:
        if not x.shape.isValid():
            failures.append(f"{x.name}: {x.kind} is not a valid solid")
        vol = x.shape.Volume()
        if vol < MIN_SOLID_VOLUME_MM3:
            failures.append(f"{x.name}: volume {vol:.3f} mm^3 is too small to be a real part")

    # 2. no two parts collide
    for i in range(len(s)):
        for j in range(i + 1, len(s)):
            if not _boxes_touch(s[i].shape, s[j].shape):
                continue  # far apart, skip the expensive check
            shared = s[i].shape.intersect(s[j].shape).Volume()
            if shared > MAX_OVERLAP_MM3:
                msg = f"{s[i].name} and {s[j].name} overlap by {shared:.1f} mm^3"
                if s[i].part.guessed or s[j].part.guessed:
                    # we guessed a diameter here, so this collision may be our mistake
                    built.uncertain.append(msg + " (involves a diameter we had to guess)")
                else:
                    failures.append(msg)

    # 3. every fin touches the tube it belongs to (found by position in the layout,
    #    not by name: several tubes are often all called "Body tube")
    for x in s:
        if x.kind != "fin":
            continue
        host = built.lay.parts[x.part.host]
        tube = next((y for y in s if y.part is host), None)
        if tube is None:
            failures.append(f"{x.name}: its tube {host.name} was not built")
            continue
        gap = _distance_mm(x.shape, tube.shape)
        if gap > MAX_FIN_GAP_MM:
            failures.append(f"{x.name}: {gap:.2f} mm away from {host.name} (fin not attached)")
    return failures


# ---------------------------------------------------------------- mass and CG

def mass_and_cg(built):
    """Structure mass (kg) and CG (m behind the nose tip). Motors are NOT included, and
    parts with no size or unknown material are listed instead of guessed."""
    items, unknown = [], list(built.lay.unknown_mass)
    for x in built.solids:
        rho = density(x.part.material)
        if rho is None:
            unknown.append(f"{x.name} (material {x.part.material!r} unknown)")
            continue
        if x.kind == "nosecone" and x.part.wall:
            # hollow nose: outer skin area times wall thickness (the base disk is open)
            area = x.shape.Area() - math.pi * (x.part.r_aft * M_TO_MM) ** 2
            vol_mm3 = area * x.part.wall * M_TO_MM
        else:
            vol_mm3 = x.shape.Volume()
        m = vol_mm3 * 1e-9 * rho
        items.append((m, cq.Shape.centerOfMass(x.shape).x / M_TO_MM))
    for name, comp, xc, _ in built.lay.internal_tubes:
        rho = density(comp.get("material"))
        if rho is None:
            unknown.append(f"{name} (material {comp.get('material')!r} unknown)")
            continue
        r_out = comp["outer_d_m"] / 2
        r_in = max(r_out - comp["wall_thickness_m"], 0.0)
        vol = math.pi * (r_out ** 2 - r_in ** 2) * comp["length_m"]
        items.append((vol * rho, xc))
    for name, m, xc in built.lay.point_masses:
        items.append((m, xc))
    total = sum(m for m, _ in items)
    cg = sum(m * x for m, x in items) / total if total > 0 else None
    return total, cg, unknown


# ---------------------------------------------------------------- the gate

def cad_gate(design):
    """design: the JSON text inside <design>...</design>, or the already-parsed dict."""
    out = {"status": None, "reward": None, "failures": [], "unsupported": [],
           "assumptions": [], "mass_kg": None, "cg_m": None, "mass_unknown": []}
    try:
        if isinstance(design, str):
            design = json.loads(design)
        lay = layout(design)
    except (json.JSONDecodeError, DesignError) as e:
        out.update(status="fail", reward=FAIL_REWARD, failures=[f"design cannot be read: {e}"])
        return out
    out["assumptions"] = lay.assumptions
    if lay.unsupported:
        out.update(status="unsupported", unsupported=lay.unsupported, failures=lay.failures)
        return out
    try:
        built = build(lay)
        failures = check(built)
        mass, cg, unknown = mass_and_cg(built)
    except Exception as e:  # our bug or a CadQuery crash: never punish the model for it
        out.update(status="error", failures=[f"CAD code crashed: {type(e).__name__}: {e}"])
        return out
    out.update(failures=failures, mass_kg=mass, cg_m=cg, mass_unknown=unknown)
    if failures:
        out.update(status="fail", reward=FAIL_REWARD)
    elif built.uncertain:
        out.update(status="unsupported", unsupported=built.uncertain)
    else:
        out["status"] = "pass"
    return out


def export(design, out_dir, name="rocket"):
    """Write <name>.step (open in Fusion) and <name>.glb (3D viewers) for a design."""
    if isinstance(design, str):
        design = json.loads(design)
    built = build(layout(design))
    os.makedirs(out_dir, exist_ok=True)
    assy = cq.Assembly()
    for i, x in enumerate(built.solids):
        # assembly names cannot contain "/" (it separates sub-assemblies)
        assy.add(x.shape, name=f"{i:02d} {x.name}".replace("/", "_"))
    step = os.path.join(out_dir, f"{name}.step")
    glb = os.path.join(out_dir, f"{name}.glb")
    cq.exporters.export(cq.Compound.makeCompound([x.shape for x in built.solids]), step)
    save = getattr(assy, "export", None) or assy.save
    save(glb)
    return step, glb


def design_from_row(row):
    """Pull the design dict out of an sft jsonl row."""
    content = row["messages"][-1]["content"]
    return json.loads(content.split("<design>", 1)[1].split("</design>", 1)[0])


if __name__ == "__main__":
    import sys
    rid = sys.argv[1] if len(sys.argv) > 1 else "U-020"
    for line in open(os.path.join(REPO, "new_results", "sft_v2.jsonl"), encoding="utf-8"):
        row = json.loads(line)
        if row["id"] == rid:
            break
    else:
        sys.exit(f"{rid} not found in sft_v2.jsonl")
    design = design_from_row(row)
    result = cad_gate(design)
    print(json.dumps(result, indent=2))
    if result["status"] == "pass":
        print("wrote", *export(design, os.path.join(REPO, "cad_out"), rid))
