#!/usr/bin/env python3
"""json_to_cad.py: turn a rocket design JSON into CAD (STEP + STL) with CadQuery.

Accepted inputs
  * the raw model answer (text containing <design>{...}</design>)      -> v2 schema
  * a bare design JSON file: {"flight":..,"components":[..]}           -> v2 schema
  * a bare design JSON file: {"openrocket": {tag: {attrs,value,children}}} -> v5 schema
  * an OpenRocket .ork file (zipped or plain XML)
  * a .jsonl row from new_results/sft_*.jsonl (use --row N)

Outputs (in --out): <name>.step (named assembly), <name>.stl (all parts),
<name>_report.json, optional parts/*.stl (--parts) and <name>.png (--png).

Units: JSON is metres, CAD is millimetres. Rocket axis = Z, nose at the top, aft end at z=0.
Geometry the JSON does not specify (ring positions, motor, fin shape of freeform sets...)
gets a documented default and a warning in the report.
"""
import argparse, json, math, os, re, sqlite3, sys, zipfile
from contextlib import contextmanager
import xml.etree.ElementTree as ET
import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB = os.path.join(HERE, "..", "data", "catalog.sqlite")
STRUCT = ("nosecone", "bodytube", "transition")
COLORS = {"nosecone": (0.85, 0.2, 0.2), "bodytube": (0.9, 0.9, 0.9), "transition": (0.3, 0.5, 0.8),
          "fin": (0.95, 0.75, 0.2), "inner": (0.7, 0.6, 0.45), "ring": (0.55, 0.4, 0.25),
          "motor": (0.2, 0.2, 0.2), "misc": (0.5, 0.5, 0.5)}


# ----------------------------------------------------------------------------- input handling
def repair_json(s):
    """Close unbalanced brackets/strings (the model sometimes stops or closes early)."""
    stack, in_str, esc, out = [], False, False, []
    for ch in s:
        out.append(ch)
        if in_str:
            if esc: esc = False
            elif ch == "\\": esc = True
            elif ch == '"': in_str = False
            continue
        if ch == '"': in_str = True
        elif ch in "{[": stack.append("}" if ch == "{" else "]")
        elif ch in "}]" and stack: stack.pop()
    if in_str: out.append('"')
    txt = "".join(out).rstrip().rstrip(",")
    return txt + "".join(reversed(stack))


def parse_design_text(text):
    m = re.search(r"<design>\s*(.*?)\s*(?:</design>|$)", text, re.S)
    body = m.group(1) if m else text.strip()
    i = body.find("{")
    body = body[i:] if i >= 0 else body
    dec = json.JSONDecoder()
    try:                                   # first complete object; ignore any trailing junk ("Extra data")
        return dec.raw_decode(body)[0]
    except json.JSONDecodeError:
        pass
    try:
        return dec.raw_decode(repair_json(body))[0]
    except json.JSONDecodeError:
        pass
    for cut in range(len(body) - 1, 0, -1):   # last resort: cut back to the last place a repair parses
        if body[cut] in "}]":
            try: return dec.raw_decode(repair_json(body[:cut + 1]))[0]
            except json.JSONDecodeError: continue
    raise ValueError("could not parse any design JSON from the model answer")


class N:
    """Tiny tree node shared by the .ork XML reader and the v5 JSON-tree reader."""
    def __init__(self, tag, attrs=None, text=None, children=None):
        self.tag, self.attrs, self.text, self.children = tag, attrs or {}, text, children or []
    def find(self, tag):
        return next((c for c in self.children if c.tag == tag), None)
    def findall(self, tag):
        return [c for c in self.children if c.tag == tag]
    def val(self, tag, default=None):
        c = self.find(tag)
        return default if c is None or c.text is None else c.text.strip()
    def num(self, tag, default=None):
        v = self.val(tag)
        if v is None: return default
        try: return float(v.split()[-1] if v.startswith("auto") and len(v.split()) > 1 else v)
        except ValueError: return default


def from_xml(el):
    return N(el.tag, dict(el.attrib), (el.text or "").strip() or None, [from_xml(c) for c in el])


def from_json_tree(tag, body):
    if not isinstance(body, dict): return N(tag, text=str(body))
    ch = body.get("children") or []
    if isinstance(ch, dict): ch = [{k: v} for k, v in ch.items()]
    if not isinstance(ch, list): ch = []
    kids = [from_json_tree(k, v) for c in ch if isinstance(c, dict) for k, v in c.items()]
    val = body.get("value")
    return N(tag, body.get("attrs") or {}, None if val is None else str(val), kids)


def load_ork(path):
    data = open(path, "rb").read()
    if data[:2] == b"\x1f\x8b":                      # old OpenRocket files are gzipped XML
        import gzip
        data = gzip.decompress(data)
    if data[:2] == b"PK":
        with zipfile.ZipFile(path) as z:
            name = next(n for n in z.namelist() if n.endswith(".ork") or n.endswith(".xml"))
            data = z.read(name)
    return from_xml(ET.fromstring(data))


# ----------------------------------------------------------------------------- OpenRocket tree -> v2 dict
def _fnum(n, tag, default=None):
    return n.num(tag, default)


def or_to_design(root):
    rocket = root.find("rocket") or root
    design = {"flight": {}, "components": [], "_source": "openrocket"}
    sims = root.find("simulations")
    if sims is not None:
        for s in sims.findall("simulation"):
            conf = s.find("conditions")
            break
    subs = rocket.find("subcomponents")
    stages = subs.findall("stage") if subs is not None else []
    for st in stages:
        design["components"].append({"type": "stage_marker", "name": st.val("name", "Stage"),
                                     "contains": _or_children(st)})
    _fill_auto_radii(design)
    return _strip_none(design)


def _or_motors(c, d):
    mm = c.find("motormount")
    if mm is None: return
    ms = []
    for m in mm.findall("motor"):
        e = {"manufacturer": m.val("manufacturer", ""), "designation": m.val("designation", "")}
        if m.num("diameter"): e["diameter_m"] = m.num("diameter")
        if m.num("length"): e["length_m"] = m.num("length")
        ms.append(e)
    if ms:
        d["motors"] = ms
        d["motor_overhang_m"] = mm.num("overhang", 0.0) or 0.0


def _strip_none(o):
    if isinstance(o, dict): return {k: _strip_none(v) for k, v in o.items() if v is not None}
    if isinstance(o, list): return [_strip_none(v) for v in o]
    return o


def _wall(n, r):
    t = n.val("thickness")
    if t is None: return None
    if t == "filled": return r
    try: return float(t)
    except ValueError: return None


def _or_children(parent):
    out = []
    subs = parent.find("subcomponents")
    if subs is None: return out
    for c in subs.children:
        d = _or_component(c)
        if d is not None: out.append(d)
    return out


def _or_component(c):
    t = c.tag
    name = c.val("name", t)
    kids = lambda: _or_children(c)
    if t == "nosecone":
        r = c.num("aftradius")
        d = {"type": "nosecone", "shape": c.val("shape", "ogive"), "length_m": c.num("length", 0.1), "name": name,
             "shape_param": c.num("shapeparameter", 1.0), "_auto_r": c.val("aftradius", "auto").startswith("auto")}
        if r: d["base_radius_m"] = r
        w = _wall(c, r or 0.01)
        if w: d["wall_thickness_m"] = w
    elif t == "bodytube":
        r = c.num("radius")
        d = {"type": "bodytube", "length_m": c.num("length", 0.3), "name": name,
             "_auto_r": c.val("radius", "auto").startswith("auto")}
        if r: d["outer_d_m"] = 2 * r
        w = _wall(c, r or 0.01)
        if w: d["wall_thickness_m"] = w
        _or_motors(c, d)
    elif t == "transition":
        fr, ar = c.num("foreradius"), c.num("aftradius")
        d = {"type": "transition", "shape": c.val("shape", "conical"), "length_m": c.num("length", 0.05), "name": name,
             "_auto_f": c.val("foreradius", "auto").startswith("auto"), "_auto_a": c.val("aftradius", "auto").startswith("auto")}
        if fr: d["fore_d_m"] = 2 * fr
        if ar: d["aft_d_m"] = 2 * ar
        w = _wall(c, max(fr or 0.01, ar or 0.01))
        if w: d["wall_thickness_m"] = w
    elif t == "trapezoidfinset":
        d = {"type": "trapezoidfin", "fin_count": c.num("fincount", 3), "root_chord_m": c.num("rootchord", 0.05),
             "tip_chord_m": c.num("tipchord", 0.02), "span_m": c.num("height", 0.04),
             "sweep_m": c.num("sweeplength", 0.02), "thickness_m": c.num("thickness", 0.002), "name": name}
    elif t == "ellipticalfinset":
        d = {"type": "ellipticalfin", "fin_count": c.num("fincount", 3), "root_chord_m": c.num("rootchord", 0.05),
             "span_m": c.num("height", 0.04), "thickness_m": c.num("thickness", 0.002), "name": name}
    elif t == "freeformfinset":
        pts = []
        fp = c.find("finpoints")
        if fp is not None:
            for p in fp.findall("point"):
                try:
                    if p.attrs.get("x") is not None and p.attrs.get("y") is not None:
                        pts.append([float(p.attrs["x"]), float(p.attrs["y"])])   # v5 design JSON: {"point": {"attrs": {"x": .., "y": ..}}}
                    elif p.text:
                        x, y = [float(v) for v in p.text.split(",")]             # .ork XML: <point>x,y</point>
                        pts.append([x, y])
                except Exception: pass
        d = {"type": "freeformfinset", "fin_count": c.num("fincount", 3), "thickness_m": c.num("thickness", 0.002), "name": name}
        if len(pts) >= 3: d["points_m"] = pts
    elif t == "tubefinset":
        d = {"type": "tubefin", "fin_count": c.num("fincount", 3), "thickness_m": c.num("thickness", 0.001), "name": name,
             "length_m": c.num("length"), "outer_d_m": (2 * c.num("outerradius")) if c.num("outerradius") else None}
    elif t == "innertube":
        r = c.num("outerradius", 0.01)
        d = {"type": "innertube", "length_m": c.num("length", 0.07), "outer_d_m": 2 * r,
             "wall_thickness_m": _wall(c, r) or 0.0005, "name": name}
        _or_motors(c, d)
    elif t in ("centeringring", "bulkhead", "engineblock"):
        d = {"type": t, "name": name}
        if c.num("length"): d["length_m"] = c.num("length")
    elif t == "launchlug":
        d = {"type": "launchlug", "length_m": c.num("length", 0.03), "name": name}
        if c.num("radius"): d["outer_d_m"] = 2 * c.num("radius")
    elif t == "railbutton":
        d = {"type": "railbutton", "name": name}
    elif t == "parachute":
        d = {"type": "parachute", "diameter_m": c.num("diameter", 0.3), "name": name}
    elif t in ("streamer", "shockcord", "masscomponent", "trapezoidfinset"):
        d = {"type": "streamer" if t == "streamer" else "masscomponent", "name": name}
    elif t in ("podset", "parallelstage"):
        d = {"type": "pod_set", "count": c.num("instancecount", 2), "name": name, "contains": _or_children(c),
             "align": "aft" if t == "parallelstage" else "fore30", "radius_offset_m": c.num("radiusoffset")}
        return d
    else:
        return None
    if kids and t in ("bodytube", "nosecone", "transition", "innertube"):
        sub = _or_children(c)
        if sub: d["contains"] = sub
    return d


def _fill_auto_radii(design):
    items = [i for st in design["components"] for i in st["contains"] if i["type"] in STRUCT]
    last = None
    for it in items:                       # forward fill from previous aft diameter
        if it["type"] == "transition":
            if "fore_d_m" not in it and last: it["fore_d_m"] = last
            last = it.get("aft_d_m", last)
        elif it["type"] == "bodytube":
            if "outer_d_m" not in it and last: it["outer_d_m"] = last
            last = it.get("outer_d_m", last)
        else:
            last = 2 * it["base_radius_m"] if "base_radius_m" in it else last
    nxt = None
    for it in reversed(items):             # backward fill (nose cone radius = next part)
        if it["type"] == "bodytube":
            nxt = it.get("outer_d_m", nxt)
        elif it["type"] == "transition":
            if "aft_d_m" not in it and nxt: it["aft_d_m"] = nxt
            nxt = it.get("fore_d_m", nxt)
        elif it["type"] == "nosecone" and "base_radius_m" not in it and nxt:
            it["base_radius_m"] = nxt / 2


def load_any(path, row=None):
    if path == "-":
        return normalise(parse_design_text(sys.stdin.read()))
    low = path.lower()
    if low.endswith(".ork"):
        return or_to_design(load_ork(path))
    if low.endswith(".jsonl"):
        rows = [json.loads(l) for l in open(path) if l.strip()]
        r = rows[row or 0]
        return normalise(parse_design_text(r["messages"][-1]["content"]))
    return normalise(parse_design_text(open(path, encoding="utf-8").read()))


def normalise(d):
    if isinstance(d, dict) and "openrocket" in d:
        body = d["openrocket"]
        return or_to_design(from_json_tree("openrocket", body))
    return d


# ----------------------------------------------------------------------------- geometry helpers (mm)
def nose_r(shape, param, R, L, x):
    """Radius of a nose-cone profile at distance x from the tip."""
    u = min(max(x / L, 0.0), 1.0)
    s = (shape or "ogive").lower()
    if s.startswith("con"): return R * u
    if s.startswith("ell"): return R * math.sqrt(max(0.0, 1 - (1 - u) ** 2))
    if s.startswith("para"):
        k = 0.5 if param is None else min(max(param, 0.0), 1.0)
        return R * (2 * u - k * u * u) / (2 - k)
    if s.startswith("pow"):
        return R * u ** (0.5 if not param else max(param, 0.05))
    if s.startswith("haack") or s.startswith("von"):
        c = 0.0 if param is None else param
        th = math.acos(1 - 2 * u)
        return R / math.sqrt(math.pi) * math.sqrt(max(0.0, th - math.sin(2 * th) / 2 + c * math.sin(th) ** 3))
    # ogive: tangent when param >= 1, secant (larger arc radius) otherwise
    p = 1.0 if not param else min(max(param, 0.05), 1.0)
    rho = (R * R + L * L) / (2 * R) / p
    if p >= 0.999:
        return max(0.0, math.sqrt(max(rho * rho - (L - x) ** 2, 0.0)) + R - rho)
    y = math.sqrt(max(rho * rho - (L - x) ** 2, 0.0)) - math.sqrt(max(rho * rho - L * L, 0.0))
    y_end = rho - math.sqrt(max(rho * rho - L * L, 0.0))
    return max(0.0, y * R / max(y_end, 1e-9))


def tube(z0, h, ro, ri=0.0):
    wp = cq.Workplane("XY").workplane(offset=z0).circle(ro)
    if ri > 0.01: wp = wp.circle(ri)
    return wp.extrude(h)


def revolve(pts):
    return cq.Workplane("XZ").polyline(pts).close().revolve(360, (0, 0, 0), (0, 1, 0))


def shell(rfun, L, z_fore, t, n=40, fore_r=None):
    """Hollow body of revolution from z_fore (fore) down to z_fore-L (aft). rfun(x): outer radius, x from fore."""
    xs = [L * i / n for i in range(n + 1)]
    outer = [(max(rfun(x), 0.0), z_fore - x) for x in xs]
    inner = [(max(rfun(x) - t, 0.0), z_fore - x) for x in xs]
    pts = outer + [p for p in reversed(inner) if p[0] > 1e-6]
    pts = [(r, z) for r, z in pts]
    # close along the axis for the filled tip
    if pts[0][0] > 1e-6: pts = [(0.0, pts[0][1])] + pts
    if pts[-1][0] > 1e-6 and inner[0][0] <= 1e-6:
        pts.append((0.0, inner[0][1] if False else pts[-1][1]))
    clean = [pts[0]]
    for p in pts[1:]:
        if abs(p[0] - clean[-1][0]) > 1e-9 or abs(p[1] - clean[-1][1]) > 1e-9: clean.append(p)
    return revolve(clean)


def fin_solid(poly_yz, thick, r_in, angle, zshift=0.0):
    """poly_yz: [(radial, z)] in mm. Extruded symmetrically by thickness, rotated about Z."""
    pts = [poly_yz[0]]
    for q in poly_yz[1:]:                       # drop repeated points (e.g. tip chord 0 -> triangle)
        if abs(q[0] - pts[-1][0]) > 1e-6 or abs(q[1] - pts[-1][1]) > 1e-6: pts.append(q)
    if len(pts) > 1 and abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][1] - pts[-1][1]) < 1e-6: pts.pop()
    wp = cq.Workplane("YZ").polyline(pts).close().extrude(thick / 2.0, both=True)
    sh = wp.val()
    return sh.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), angle) if angle else sh


class Builder:
    def __init__(self, db=None, flight_motor=None):
        self.parts, self.warn, self.db, self.flight_motor = [], [], db, flight_motor

    def emit(self, name, cat, shape):
        shape = shape.val() if hasattr(shape, "val") else shape
        self.parts.append({"name": name, "cat": cat, "shape": shape})

    # -- top level -------------------------------------------------------------------------
    @staticmethod
    def total_len(items):
        return sum(1000 * i.get("length_m", 0) for i in items if i.get("type") in STRUCT)

    def build_design(self, design):
        items = []
        for c in design.get("components", []):
            if c.get("type") == "stage_marker": items += c.get("contains", [])
            else: items.append(c)
        self.build_stack(items, self.total_len(items))

    def build_stack(self, items, Ltot, s0=0.0):
        s = s0
        structural = [i for i in items if i.get("type") in STRUCT]
        for it in items:
            t = it.get("type")
            if t not in STRUCT:
                if t not in ("masscomponent", "parachute", "streamer"):
                    self.warn.append(f"stage-level part '{t}' ignored (no position info)")
                continue
            L = 1000 * (it.get("length_m") or 0)
            geom = None
            with self.guard(it.get("name", t)):
                geom = self.structural(it, s, L, Ltot, structural)
            if geom:
                self.children(it, geom)
            s += L

    def structural(self, it, s, L, Ltot, structural):
        t, nm, zf = it["type"], it.get("name", it["type"]), Ltot - s
        if L <= 0.05: return None
        if t == "nosecone":
            R = 1000 * (it.get("base_radius_m") or 0) or self._next_r(structural, it) or 12.0
            if not it.get("base_radius_m"): self.warn.append(f"{nm}: base radius missing, used {R:.1f} mm")
            tw = min(max(1000 * (it.get("wall_thickness_m") or 0.002), 0.4), R * 0.5)
            shp, par = it.get("shape", "ogive"), it.get("shape_param")
            self.emit(nm, "nosecone", shell(lambda x: nose_r(shp, par, R, L, x), L, zf, tw, 48))
            geom = dict(s0=s, L=L, r=R, rt=R, wall=tw)
        elif t == "bodytube":
            R = 500 * (it.get("outer_d_m") or 0.0248)
            tw = min(max(1000 * (it.get("wall_thickness_m") or 0.0005), 0.3), R * 0.9)
            self.emit(nm, "bodytube", tube(zf - L, L, R, R - tw))
            geom = dict(s0=s, L=L, r=R, rt=R, wall=tw)
        else:  # transition
            rf = 500 * (it.get("fore_d_m") or it.get("aft_d_m") or 0.025)
            ra = 500 * (it.get("aft_d_m") or it.get("fore_d_m") or 0.025)
            tw = max(1000 * (it.get("wall_thickness_m") or 0.001), 0.4)
            shp, par = it.get("shape", "conical"), it.get("shape_param")
            if abs(ra - rf) < 1e-6: fun = lambda x: rf
            else: fun = lambda x: rf + (ra - rf) * nose_r(shp, par, 1.0, L, x)
            self.emit(nm, "transition", shell(fun, L, zf, min(tw, max(rf, ra) * 0.5), 32))
            geom = dict(s0=s, L=L, r=ra, rt=rf, wall=tw)
        geom["Ltot"], geom["type"] = Ltot, t
        return geom

    @staticmethod
    def _next_r(structural, it):
        i = structural.index(it)
        for nx in structural[i + 1:]:
            if nx["type"] == "bodytube": return 500 * nx.get("outer_d_m", 0)
            if nx["type"] == "transition": return 500 * nx.get("fore_d_m", 0)
        return None

    # -- children of a structural part --------------------------------------------------------
    @contextmanager
    def guard(self, label):
        try:
            yield
        except Exception as e:                   # one bad part must not kill the whole rocket
            self.warn.append(f"{label}: skipped ({type(e).__name__}: {str(e)[:50]})")

    def inner_tube(self, k, zb, Lmax, rid, depth=0):
        """Draw an inner tube plus anything mounted inside it: nested inner tubes,
        engine blocks, motor mounts. v5 JSON carries no positions, so nested parts
        are aft-aligned inside their parent's bore. Returns (zb, kl, ro, tw) --
        the centering-ring layout depends on the outermost tube's tuple."""
        ro = 500 * (k.get("outer_d_m") or 0.019)
        if 1000 * (k.get("length_m") or 0.07) < 1.0 or ro < 2.0:
            self.warn.append(f"skipped degenerate inner tube '{k.get('name')}' (length < 1 mm or diameter < 4 mm)")
            return None
        ro = min(ro, rid - 0.2)
        if ro < 1.0: return None
        tw = min(max(1000 * (k.get("wall_thickness_m") or 0.0005), 0.3), ro * 0.9)
        kl = min(1000 * (k.get("length_m") or 0.07), Lmax)
        self.emit(k.get("name", "Inner tube"), "inner", tube(zb, kl, ro, ro - tw))
        bore = ro - tw
        for kk in k.get("contains", []):
            if kk.get("type") == "engineblock":
                idm = max(bore * 0.8, bore - 1.5)
                self.emit("Engine block", "ring", tube(zb + kl - 3.0, 3.0, bore, idm))
            elif kk.get("type") == "innertube":
                if depth >= 8:
                    self.warn.append("inner tube nesting deeper than 8 levels skipped")
                    continue
                with self.guard(kk.get("name", "Inner tube")):
                    self.inner_tube(kk, zb, kl, bore, depth + 1)
                self.warn.append(f"inner tube '{kk.get('name', 'Inner tube')}' nested inside another inner tube: aft-aligned (JSON has no positions)")
        if k.get("motors"): self.motor(k, zb, kl, bore)
        return (zb, kl, ro, tw)

    def children(self, it, g):
        kids = it.get("contains", [])
        Ltot, s0, L, r, wall = g["Ltot"], g["s0"], g["L"], g["r"], g["wall"]
        z_aft, z_fore = Ltot - (s0 + L), Ltot - s0
        rid = max(r - wall, 0.5)
        inner_tubes = []
        for k in kids:                           # inner tubes first (rings depend on them)
            if k.get("type") != "innertube": continue
            with self.guard(k.get("name", "Inner tube")):
                found = self.inner_tube(k, z_aft, L, rid)
                if found: inner_tubes.append(found)
        if it.get("motors") and not inner_tubes and it.get("type") == "bodytube":
            with self.guard("Motor"):
                self.motor(it, z_aft, L, rid)
        if len(inner_tubes) > 1:
            self.warn.append(f"{it.get('name')}: {len(inner_tubes)} inner tubes all aft-aligned (JSON has no positions)")
        rings = [k for k in kids if k.get("type") == "centeringring"]
        if rings and inner_tubes:
            zb, kl, ro, tw = inner_tubes[0]
            th = min(3.0, kl / (len(rings) + 1))
            zs = [zb] if len(rings) == 1 else [zb + (kl - th) * i / (len(rings) - 1) for i in range(len(rings))]
            for z in zs:
                with self.guard("Centering ring"):
                    self.emit("Centering ring", "ring", tube(z, th, rid, ro))
            self.warn.append(f"{it.get('name')}: ring positions not in JSON, spread along the inner tube")
        elif rings:
            self.warn.append(f"{it.get('name')}: centering rings skipped (no inner tube)")
        for i, k in enumerate([k for k in kids if k.get("type") == "bulkhead"]):
            with self.guard("Bulkhead"):
                self.emit("Bulkhead", "ring", tube(z_fore - 2.0 * (i + 1), 2.0, rid, 0))
        fin_n = 3
        for k in kids:
            if k.get("type") in ("trapezoidfin", "ellipticalfin", "freeformfinset", "tubefin"):
                with self.guard(k.get("name", "Fin")):
                    self.fins(k, g)
                fin_n = int(round(k.get("fin_count") or 3)) or 3
        for k in kids:
            t = k.get("type")
            with self.guard(k.get("name", t or "part")):
                if t == "launchlug":
                    ll = min(1000 * (k.get("length_m") or 0.03), L)
                    od = 1000 * (k.get("outer_d_m") or 0.0) or 6.0
                    zl = min(z_aft + L * 0.45, z_fore - ll)
                    ang = math.radians(180.0 / max(fin_n, 1))
                    cx, cy = (r + od / 2 - 0.4) * math.cos(ang), (r + od / 2 - 0.4) * math.sin(ang)
                    lug = cq.Workplane("XY").workplane(offset=zl).center(cx, cy).circle(od / 2).circle(od / 2 - 1.0).extrude(ll)
                    self.emit("Launch lug", "misc", lug)
                elif t == "railbutton":
                    zl = z_aft + L * 0.6
                    stem = cq.Workplane("XY").workplane(offset=zl).center(r + 1.5, 0).circle(1.6).extrude(3.0)
                    cap = cq.Workplane("XY").workplane(offset=zl).center(r + 3.0, 0).circle(4.0).extrude(2.2)
                    self.emit("Rail button", "misc", cap.union(stem))
                elif t == "pod_set":
                    self.pods(k, g)

    def motor(self, k, zb, kl, rid):
        ms = k.get("motors") or []
        m0 = ms[0] if ms else {}
        des = m0.get("designation") or self.flight_motor
        d_mm, l_mm = 1000 * (m0.get("diameter_m") or 0), 1000 * (m0.get("length_m") or 0)
        if not (d_mm and l_mm):                      # not in the design: try the catalog
            dims = self.lookup_motor(des, m0.get("manufacturer"))
            if not dims:
                self.warn.append(f"motor {des!r}: no size in design or catalog, no motor solid drawn")
                return
            d_mm, l_mm = dims
        over = 1000 * (k.get("motor_overhang_m") or 0)
        d_mm = min(d_mm, 2 * rid - 0.2)
        self.emit(f"Motor {des}", "motor", tube(zb - over, l_mm, d_mm / 2, 0))

    def lookup_motor(self, des, man=None):
        if not self.db or not des: return None
        rows = self.db.execute("select manufacturer, diameter_mm, length_mm from motors where lower(designation)=lower(?)", (des,)).fetchall()
        if not rows: return None
        pick = next((r for r in rows if man and man.lower()[:4] in (r[0] or "").lower() and r[1] and r[2]), None)
        pick = pick or next((r for r in rows if r[1] and r[2]), None)
        return (pick[1], pick[2]) if pick else None

    def fins(self, k, g):
        Ltot, s0, L, r, wall = g["Ltot"], g["s0"], g["L"], g["r"], g["wall"]
        n = int(round(k.get("fin_count") or 0))
        if n < 1: return
        z_aft = Ltot - (s0 + L)
        d = 2 * r
        th = max(1000 * k.get("thickness_m", 0.002), 0.5)
        r_in = r - min(wall * 0.5, 0.5)
        t = k["type"]
        if t == "tubefin":
            ro_f = 1000 * (k.get("outer_d_m") or 0) / 2 or min(r * 0.45, 8.0)
            lf = 1000 * (k.get("length_m") or 0) or min(2 * d, L)
            rc = r + ro_f - 0.3
            for i in range(n):
                a = math.radians(360.0 * i / n)
                tb = cq.Workplane("XY").workplane(offset=z_aft).center(rc * math.cos(a), rc * math.sin(a)).circle(ro_f).circle(max(ro_f - max(th, 0.4), 0.2)).extrude(lf)
                self.emit("Tube fin", "fin", tb)
            if not k.get("outer_d_m"): self.warn.append("tube fins: size not in JSON, estimated from body diameter")
            return
        if t == "trapezoidfin":
            root, tip = 1000 * k["root_chord_m"], 1000 * k["tip_chord_m"]
            span, sweep = 1000 * k["span_m"], 1000 * k["sweep_m"]
            poly = [(r_in, z_aft), (r_in, z_aft + root), (r + span, z_aft + root - sweep - tip), (r + span, z_aft + root - sweep)]
            # ^ z grows toward the nose: root leading edge is at z_aft+root, trailing edge at z_aft
            poly = [(r_in, z_aft), (r_in, z_aft + root), (r + span, z_aft + root - sweep), (r + span, z_aft + root - sweep - tip)]
        elif t == "ellipticalfin":
            root, span = 1000 * k["root_chord_m"], 1000 * k["span_m"]
            pts = [(r + span * math.sqrt(max(0, 1 - ((x - 0.5) / 0.5) ** 2)), z_aft + root * x) for x in [i / 24 for i in range(25)]]
            poly = [(r_in, z_aft)] + pts[1:-1] + [(r_in, z_aft + root)]
            poly = [(r_in, z_aft), (r_in, z_aft + root)] + [(r + span * math.sqrt(max(0, 1 - ((x - 0.5) / 0.5) ** 2)), z_aft + root * x) for x in [1 - i / 24 for i in range(1, 24)]]
        else:  # freeform
            pts = k.get("points_m")
            if pts:
                # OpenRocket points: (x = distance aft from fin root leading edge, y = outward). Leading edge at z_aft+root.
                xs = [p[0] for p in pts]
                root_len = max(xs)
                z_lead = z_aft + max(root_len, 0.0) * 1000
                poly = [(r_in if abs(p[1]) < 1e-9 else r + 1000 * p[1], z_lead - 1000 * p[0]) for p in pts]
            else:
                root, tip, span, sweep = 1.6 * d, 0.7 * d, 0.9 * d, 0.8 * d
                poly = [(r_in, z_aft), (r_in, z_aft + root), (r + span, z_aft + root - sweep), (r + span, z_aft + root - sweep - tip)]
                self.warn.append(f"freeform fin '{k.get('name')}': shape not in JSON, default swept fin used")
        for i in range(n):
            self.emit(k.get("name", "Fin") + f" {i + 1}", "fin", fin_solid(poly, th, r_in, 360.0 * i / n))

    def pods(self, k, g):
        n = int(round(k.get("count", 2)))
        sub_items = k.get("contains", [])
        lp = self.total_len(sub_items)
        if n < 1 or lp <= 0: return
        sub = Builder(self.db, self.flight_motor)
        sub.build_stack(sub_items, lp)
        self.warn += sub.warn
        pr = max([500 * i.get("outer_d_m", 0) for i in sub_items if i.get("type") == "bodytube"] +
                 [1000 * i.get("base_radius_m", 0) for i in sub_items if i.get("type") == "nosecone"] + [3.0])
        Ltot, s0, L, r = g["Ltot"], g["s0"], g["L"], g["r"]
        if k.get("align") == "aft": s_fore = s0 + L - lp
        else: s_fore = s0 + min(0.3 * L, max(0.0, L - lp))
        z_aft = Ltot - (s_fore + lp)
        roff = 1000 * k["radius_offset_m"] if k.get("radius_offset_m") else r + pr - 0.2
        for i in range(n):
            ang = 360.0 * i / n
            for p in sub.parts:
                sh = p["shape"].translate(cq.Vector(roff, 0, z_aft))
                sh = sh.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), ang)
                self.parts.append({"name": f"{k.get('name', 'Pod')} {i + 1}: {p['name']}", "cat": p["cat"], "shape": sh})


# ----------------------------------------------------------------------------- export
def safe(s):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", s).strip("_")[:60] or "part"


def design_to_cad(design, out_dir, name="rocket", parts=False, db_path=DEFAULT_DB, png=False):
    os.makedirs(out_dir, exist_ok=True)
    db = sqlite3.connect(db_path) if db_path and os.path.exists(db_path) else None
    b = Builder(db, (design.get("flight") or {}).get("motor"))
    b.build_design(design)
    if not b.parts: raise ValueError("design produced no geometry (no nosecone/bodytube/transition found)")
    asm = cq.Assembly(name=name)
    for i, p in enumerate(b.parts):
        asm.add(p["shape"], name=f"{i:02d}_{safe(p['name'])}", color=cq.Color(*COLORS.get(p["cat"], COLORS["misc"])))
    step = os.path.join(out_dir, f"{name}.step")
    asm.save(step)
    comp = cq.Compound.makeCompound([p["shape"] for p in b.parts])
    stl = os.path.join(out_dir, f"{name}.stl")
    cq.exporters.export(cq.Workplane(obj=comp), stl, tolerance=0.05, angularTolerance=0.15)
    if parts:
        pd = os.path.join(out_dir, "parts")
        os.makedirs(pd, exist_ok=True)
        for i, p in enumerate(b.parts):
            cq.exporters.export(cq.Workplane(obj=p["shape"]), os.path.join(pd, f"{i:02d}_{safe(p['name'])}.stl"), tolerance=0.05, angularTolerance=0.15)
    bb = comp.BoundingBox()
    report = {"name": name, "step": step, "stl": stl, "parts": len(b.parts),
              "length_mm": round(bb.zlen, 2), "max_diameter_mm": round(max(bb.xlen, bb.ylen), 2),
              "bbox_mm": [round(bb.xlen, 2), round(bb.ylen, 2), round(bb.zlen, 2)],
              "part_list": [{"name": p["name"], "kind": p["cat"], "volume_mm3": round(p["shape"].Volume(), 1)} for p in b.parts],
              "warnings": sorted(set(b.warn))}
    json.dump(report, open(os.path.join(out_dir, f"{name}_report.json"), "w"), indent=2)
    if png:
        try: preview_png(stl, os.path.join(out_dir, f"{name}.png"))
        except Exception as e: report["warnings"].append(f"png preview failed: {e}")
    return report


def preview_png(stl_path, png_path):
    import numpy as np, trimesh
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    m = trimesh.load(stl_path)
    tri, nrm = m.triangles, m.face_normals
    fig, axes = plt.subplots(1, 2, figsize=(12, 7))
    for ax, (ix, iy, view_dir) in zip(axes, [(1, 2, np.array([1.0, 0, 0])), (0, 2, np.array([0, -1.0, 0]))]):
        order = np.argsort((tri.mean(1) @ view_dir))
        light = np.clip(nrm @ view_dir * -1, 0, 1) * 0.6 + 0.35
        ok = light[order]
        polys = tri[order][:, :, [ix, iy]]
        ax.add_collection(PolyCollection(polys, facecolors=np.stack([ok * 0.85, ok * 0.88, ok], 1), edgecolors="none"))
        ax.set_xlim(polys[..., 0].min() - 10, polys[..., 0].max() + 10); ax.set_ylim(polys[..., 1].min() - 10, polys[..., 1].max() + 10)
        ax.set_aspect("equal"); ax.axis("off")
    plt.tight_layout(); plt.savefig(png_path, dpi=110); plt.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="model answer .txt / design .json / .jsonl row / .ork / - for stdin")
    ap.add_argument("-o", "--out", default="cad_out")
    ap.add_argument("--name", default=None)
    ap.add_argument("--row", type=int, default=0, help="row of a .jsonl file")
    ap.add_argument("--parts", action="store_true", help="also write one STL per part")
    ap.add_argument("--png", action="store_true", help="write a quick side/front preview")
    ap.add_argument("--db", default=DEFAULT_DB, help="data/catalog.sqlite (for motor sizes)")
    a = ap.parse_args()
    design = load_any(a.input, a.row)
    name = a.name or safe(os.path.splitext(os.path.basename(a.input))[0] if a.input != "-" else "rocket")
    rep = design_to_cad(design, a.out, name, a.parts, a.db, a.png)
    print(json.dumps({k: rep[k] for k in ("step", "stl", "parts", "length_mm", "max_diameter_mm", "warnings")}, indent=2))


if __name__ == "__main__":
    main()
