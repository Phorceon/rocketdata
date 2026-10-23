"""Rebuild the <design> IR + fingerprint exactly as data/sft_v0.jsonl does, reading
the raw OpenRocket .ork XML directly (materials, presets, nesting, per-component
masses). The v0 builder is not in the repo; this reconstruction is validated
against every sft_v0 row by scripts/build_sft_v1.py and emits identical key order.
"""
import gzip
import zipfile
from xml.etree import ElementTree as ET

TAG2TYPE = {
    "nosecone": "nosecone",
    "bodytube": "bodytube",
    "transition": "transition",
    "trapezoidfinset": "trapezoidfin",
    "finset": "trapezoidfin",
    "freeformfinset": "freeformfinset",
    "ellipticalfinset": "ellipticalfin",
    "tubefinset": "tubefin",
    "parachute": "parachute",
    "streamer": "streamer",
    "masscomponent": "masscomponent",
    "innertube": "innertube",
    "centeringring": "centeringring",
    "bulkhead": "bulkhead",
    "engineblock": "engineblock",
    "launchlug": "launchlug",
    "railbutton": "railbutton",
    "stage": "stage_marker",
    "podset": "pod_set",
    "parallelstage": "pod_set",
}


def load_bytes(path):
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if n.endswith(".ork") or n.endswith(".xml")]
            return z.read(names[0] if names else z.namelist()[0])
    raw = open(path, "rb").read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return raw


def _text(el, tag):
    c = el.find(tag)
    return c.text.strip() if c is not None and c.text else None


def _num(el, tag):
    v = _text(el, tag)
    if v is None:
        return None
    # OpenRocket writes computed dimensions as "auto 0.025"; keep the numeric part.
    if v.startswith("auto"):
        v = v[len("auto"):].strip()
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _rk(v, n=5):
    return None if v is None else round(float(v), n)


def _r2(radius):
    """v0 rounds the radius to 5 dp, then doubles it for the diameter. A missing or
    zero radius yields no diameter field (v0 never stores outer_d_m == 0.0)."""
    if not radius:
        return None
    return round(radius, 5) * 2.0


def _material(el):
    """v0 keeps only the first comma-separated segment of the material description."""
    m = el.find("material")
    if m is None or not m.text:
        return None
    return m.text.strip().split(",")[0].strip()


def _preset(el):
    p = el.find("preset")
    if p is None:
        return None
    manuf, partno = p.get("manufacturer"), p.get("partno")
    if manuf and partno:
        return "%s %s" % (manuf, partno)
    return manuf or partno


def _motors(el):
    """Motors on this component's mount, de-duplicated by (manufacturer, designation)."""
    out = []
    mm = el.find("motormount")
    if mm is None:
        return out
    seen = set()
    for mc in mm.findall("motor"):
        desig = _text(mc, "designation")
        if not desig or desig in seen:
            continue
        seen.add(desig)
        out.append({"manufacturer": _text(mc, "manufacturer") or "", "designation": desig})
    return out


def build_component(el):
    """Return an ordered dict matching the v0 IR for one XML component."""
    t = TAG2TYPE.get(el.tag)
    if t is None:
        return None
    name = _text(el, "name")
    c = {"type": t}

    if t == "nosecone":
        c["shape"] = _text(el, "shape")
        if el.find("shapeparameter") is not None:
            c["shape_param"] = _num(el, "shapeparameter")
        c["length_m"] = _rk(_num(el, "length"))
        c["base_radius_m"] = _rk(_num(el, "aftradius"))
        c["wall_thickness_m"] = _rk(_num(el, "thickness"))
        mat = _material(el)
        if mat:
            c["material"] = mat
        pre = _preset(el)
        if pre:
            c["preset"] = pre
    elif t == "bodytube":
        c["length_m"] = _rk(_num(el, "length"))
        c["outer_d_m"] = _r2(_num(el, "radius"))
        c["wall_thickness_m"] = _rk(_num(el, "thickness"))
        mat = _material(el)
        if mat:
            c["material"] = mat
        pre = _preset(el)
        if pre:
            c["preset"] = pre
    elif t == "transition":
        c["shape"] = _text(el, "shape")
        c["length_m"] = _rk(_num(el, "length"))
        c["fore_d_m"] = _r2(_num(el, "foreradius"))
        c["aft_d_m"] = _r2(_num(el, "aftradius"))
        mat = _material(el)
        if mat:
            c["material"] = mat
    elif t == "trapezoidfin":
        fc = _num(el, "fincount")
        if fc is not None:
            c["fin_count"] = fc
        c["root_chord_m"] = _rk(_num(el, "rootchord"))
        c["tip_chord_m"] = _rk(_num(el, "tipchord"))
        c["span_m"] = _rk(_num(el, "height"))
        c["sweep_m"] = _rk(_num(el, "sweeplength"))
        c["thickness_m"] = _rk(_num(el, "thickness"))
        mat = _material(el)
        if mat:
            c["material"] = mat
    elif t == "freeformfinset":
        fc = _num(el, "fincount")
        if fc is not None:
            c["fin_count"] = fc
        c["thickness_m"] = _rk(_num(el, "thickness"))
        mat = _material(el)
        if mat:
            c["material"] = mat
    elif t == "ellipticalfin":
        fc = _num(el, "fincount")
        if fc is not None:
            c["fin_count"] = fc
        c["root_chord_m"] = _rk(_num(el, "rootchord"))
        c["span_m"] = _rk(_num(el, "height"))
        c["thickness_m"] = _rk(_num(el, "thickness"))
        mat = _material(el)
        if mat:
            c["material"] = mat
    elif t == "tubefin":
        fc = _num(el, "fincount")
        if fc is not None:
            c["fin_count"] = fc
        c["thickness_m"] = _rk(_num(el, "thickness"))
        mat = _material(el)
        if mat:
            c["material"] = mat
    elif t == "parachute":
        c["diameter_m"] = _rk(_num(el, "diameter"))
        c["deploy_event"] = _text(el, "deployevent")
        c["deploy_altitude_m"] = _num(el, "deployaltitude")
        c["deploy_delay_s"] = _num(el, "deploydelay")
        lc = _num(el, "linecount")
        if lc is not None:
            c["line_count"] = float(lc)
        mat = _material(el)
        if mat:
            c["material"] = mat
        pre = _preset(el)
        if pre:
            c["preset"] = pre
    elif t == "streamer":
        c["strip_length_m"] = _rk(_num(el, "striplength"))
        c["strip_width_m"] = _rk(_num(el, "stripwidth"))
        c["deploy_event"] = _text(el, "deployevent")
        mat = _material(el)
        if mat:
            c["material"] = mat
    elif t == "masscomponent":
        c["mass_kg"] = _rk(_num(el, "mass"))
        kind = _text(el, "masscomponenttype")
        if kind:
            c["kind"] = kind
    elif t == "innertube":
        c["length_m"] = _rk(_num(el, "length"))
        c["outer_d_m"] = _r2(_num(el, "outerradius"))
        c["wall_thickness_m"] = _rk(_num(el, "thickness"))
        mat = _material(el)
        if mat:
            c["material"] = mat
    elif t == "centeringring":
        mat = _material(el)
        if mat:
            c["material"] = mat
    elif t == "bulkhead":
        mat = _material(el)
        if mat:
            c["material"] = mat
    elif t == "engineblock":
        pass
    elif t == "launchlug":
        c["length_m"] = _rk(_num(el, "length"))
    elif t == "railbutton":
        pass
    elif t == "stage_marker":
        pass
    elif t == "pod_set":
        ic = _num(el, "instancecount")
        if ic is not None:
            c["count"] = float(ic)

    # "name" sits right after "type" for masscomponent/engineblock, else after the
    # physical fields and before contains/motors.
    if t in ("masscomponent", "engineblock"):
        c = {"type": t, "name": name, **{k: v for k, v in c.items() if k != "type"}}
    else:
        c["name"] = name

    subs = el.find("subcomponents")
    if subs is not None:
        children = [cc for cc in (build_component(ch) for ch in subs) if cc is not None]
        if children:
            c["contains"] = children

    # v0 never emits null fields: drop any optional field with no value.
    c = {k: v for k, v in c.items() if v is not None}

    # Marker consumed by _propagate_motors: components carrying a motormount.
    if el.find("motormount") is not None:
        motors = _motors(el)
        if motors:
            c["_has_motors"] = motors
    return c


def _propagate_motors(comps):
    """The .ork declares motors on the motor mount (usually an innertube). The v0 IR
    copies that motor list onto the mount owner and onto every stage_marker and
    bodytube ancestor up the chain. Returns the motor list seen in this subtree."""
    def rec(node):
        motors = node.pop("_has_motors", None)
        child_motors = []
        for ch in node.get("contains", []):
            child_motors.extend(rec(ch))
        if node.get("type") == "bodytube":
            child_motors = [] if motors else child_motors
        if node.get("type") == "stage_marker":
            child_motors = [] if motors else child_motors
        inherited = motors or (child_motors[0] if child_motors else None)
        if inherited and (motors or node.get("type") in ("stage_marker", "bodytube")):
            node["motors"] = inherited
        return [inherited] if inherited else []

    for c in comps:
        rec(c)


def build_design(path):
    root = ET.fromstring(load_bytes(path))
    rocket = root.find("rocket")
    if rocket is None:
        return None, root
    subs = rocket.find("subcomponents")
    comps = []
    if subs is not None:
        comps = [cc for cc in (build_component(ch) for ch in subs) if cc is not None]
    _propagate_motors(comps)
    return comps, root


def fingerprint(comps):
    """Stable structural fingerprint: type + name + rounded dims, recursively.
    Deterministic across processes (uses hashlib, not the salted built-in hash)."""
    import hashlib

    parts = []

    def rec(c):
        # every field of the component (type, name, dims, material, mass, kind,
        # motors) participates, so files differing only in a motor or a mass are
        # NOT the same design.
        sig = []
        for k in sorted(c.keys()):
            if k in ("contains",):
                continue
            v = c[k]
            if k == "motors":
                v = tuple((m.get("manufacturer"), m.get("designation")) for m in v)
            sig.append((k, v))
        parts.append(tuple(sig))
        for ch in c.get("contains", []):
            rec(ch)

    for c in comps:
        rec(c)
    return hashlib.sha1(repr(parts).encode("utf-8")).hexdigest()
