"""Extract physical design + stored simulation metrics from OpenRocket .ork files.

A .ork may be a ZIP (member rocket.ork), a gzip stream, or plain XML.  Pure
standard library (zipfile, gzip, xml.etree) -- no OpenRocket.jar required.

The parser is intentionally defensive: OpenRocket XML has changed tag names
over versions (e.g. <finset> vs <trapezoidfinset>/<freeformfinset>, axialoffset
vs position), so several spellings are accepted.
"""

import gzip
import io
import re
import zipfile
import xml.etree.ElementTree as ET

FINSET_TAGS = {
    "finset",
    "trapezoidfinset",
    "freeformfinset",
    "ellipticalfinset",
}
COMPONENT_TAGS = {
    "nosecone", "bodytube", "transition", "tubecoupler", "innertube",
    "centeringring", "bulkhead", "finset", "trapezoidfinset",
    "freeformfinset", "ellipticalfinset", "parachute", "streamer",
    "shockcord", "masscomponent", "launchlug", "railbutton", "stage",
    "pod", "parallelstage",
}


def _read_bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


def load_xml_bytes(path):
    """Return (bytes, format) where format is 'zip'|'gzip'|'xml'."""
    b = _read_bytes(path)
    if b[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(b)) as z:
            members = z.namelist()
            for name in members:
                if name.endswith(".ork") or name.endswith(".xml"):
                    return z.read(name), "zip"
            return z.read(members[0]), "zip"
    if b[:2] == b"\x1f\x8b":
        return gzip.decompress(b), "gzip"
    return b, "xml"


def _num(text, default=None):
    if text is None:
        return default
    text = text.strip()
    m = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", text)
    if not m:
        return default
    try:
        return float(m.group(0))
    except ValueError:
        return default


def _text(el, tag, default=None):
    if el is None:
        return default
    child = el.find(tag)
    if child is None or child.text is None:
        return default
    return child.text.strip()


def _axial_offset(el):
    """Return (offset_m, method) from <axialoffset> or <position>."""
    for tag in ("axialoffset", "position"):
        child = el.find(tag)
        if child is not None:
            method = child.attrib.get("method") or child.attrib.get("type") or "top"
            return _num(child.text, 0.0), method
    return 0.0, "top"


def _radius_m(el):
    """Bodytube radius: <radius>auto 0.0125</radius> or <outerradius>."""
    for tag in ("radius", "outerradius"):
        child = el.find(tag)
        if child is not None and child.text:
            return _num(child.text)
    return None


def _od_m(el):
    r = _radius_m(el)
    return 2.0 * r if r is not None else None


def _finset_geometry(el):
    fincount = int(_num(_text(el, "fincount"), 0) or 0)
    thick = _num(_text(el, "thickness"))
    cross = _text(el, "crosssection")
    root = _num(_text(el, "rootchord"))
    tip = _num(_text(el, "tipchord"))
    span = _num(_text(el, "height"))
    sweep = _num(_text(el, "sweeplength"))
    if root is None and el.tag == "freeformfinset":
        pts = [
            (_num(p.get("x")), _num(p.get("y")))
            for p in el.findall(".//finpoints/point")
        ]
        pts = [(x, y) for x, y in pts if x is not None and y is not None]
        if pts:
            span = max(y for _, y in pts)
            root_pts = [x for x, y in pts if abs(y) < 1e-9]
            tip_pts = [x for x, y in pts if abs(y - span) < 1e-9]
            if root_pts:
                root = max(root_pts) - min(root_pts) or max(root_pts)
            if tip_pts:
                tip = max(tip_pts) - min(tip_pts)
                sweep = min(tip_pts) - (min(root_pts) if root_pts else 0.0)
    return {
        "kind": el.tag,
        "fincount": fincount,
        "thickness_m": thick,
        "crosssection": cross,
        "root_chord_m": root,
        "tip_chord_m": tip,
        "span_m": span,
        "sweep_m": sweep,
    }


# ---- recursive layout walk -------------------------------------------------

def walk(root_rocket):
    """Return (components, total_length_m, stage_count, cluster).

    components is a list of dicts with tag, name, station (nose=0), length, el.
    Stages are only the real airframe <stage> elements that live under a
    <subcomponents> element (motorconfiguration also contains <stage> markers).
    """
    comps = []
    total = [0.0]
    stages = [0]
    cluster = [False]

    def recurse(parent_el, base_station):
        station = base_station
        subs = parent_el.find("subcomponents")
        if subs is None:
            return
        for child in subs:
            if child.tag not in COMPONENT_TAGS:
                continue
            if child.tag in ("stage", "pod", "parallelstage"):
                stages[0] += 1
                recurse(child, base_station)
                continue
            ic = _num(_text(child, "instancecount"))
            if ic and ic > 1 and child.tag not in FINSET_TAGS:
                cluster[0] = True
            length = _num(_text(child, "length"), 0.0) or 0.0
            if child.tag in ("masscomponent", "parachute", "streamer",
                             "shockcord", "launchlug", "railbutton",
                             "centeringring", "bulkhead"):
                length = 0.0
                offset, _ = _axial_offset(child)
                cstation = station + offset
            elif child.tag in FINSET_TAGS:
                offset, method = _axial_offset(child)
                if method == "bottom":
                    cstation = station + length - offset
                else:
                    cstation = station + offset
                length = 0.0
            elif child.tag in ("nosecone", "bodytube", "transition"):
                cstation = station
            else:
                cstation = station
            comps.append({
                "tag": child.tag,
                "name": _text(child, "name"),
                "station_m": cstation,
                "length_m": length,
                "el": child,
            })
            if child.tag in ("nosecone", "bodytube", "transition",
                             "tubecoupler", "innertube"):
                recurse(child, cstation)
            station += length
            total[0] = max(total[0], station)

    recurse(root_rocket, 0.0)
    return comps, total[0], stages[0], cluster[0]


def parse_simulations(root):
    sims = []
    for sim in root.findall(".//simulations/simulation"):
        name = _text(sim, "name")
        cond = sim.find("conditions")
        configid = _text(cond, "configid") if cond is not None else None
        fd = sim.find("flightdata")
        metrics = None
        if fd is not None:
            a = fd.attrib
            def g(k, scale=1.0):
                v = a.get(k)
                return round(float(v) * scale, 4) if v not in (None, "") else None
            metrics = {
                "apogee_m": g("maxaltitude"),
                "max_velocity_mps": g("maxvelocity"),
                "max_acceleration_mps2": g("maxacceleration"),
                "max_mach": g("maxmach"),
                "time_to_apogee_s": g("timetoapogee"),
                "flight_time_s": g("flighttime"),
                "ground_hit_velocity_mps": g("groundhitvelocity"),
                "launchrod_velocity_mps": g("launchrodvelocity"),
                "deployment_velocity_mps": g("deploymentvelocity"),
                "optimum_delay_s": g("optimumdelay"),
            }
        sims.append({"name": name, "configid": configid, "metrics": metrics})
    return sims


def extract(path):
    raw, fmt = load_xml_bytes(path)
    root = ET.fromstring(raw)
    rocket = root.find("rocket")
    out = {
        "path": path,
        "format": fmt,
        "rocket_name": _text(rocket, "name"),
        "designer": _text(rocket, "designer"),
        "motor_configurations": [],
        "nose_cones": [],
        "body_tubes": [],
        "transitions": [],
        "finsets": [],
        "recovery": [],
        "mass_components": [],
        "motors": [],
        "stage_count": 0,
        "cluster": False,
        "pods": 0,
        "total_length_m": None,
        "simulations": [],
    }
    if rocket is None:
        return out

    # motor configurations
    for mc in rocket.findall("motorconfiguration"):
        out["motor_configurations"].append({
            "configid": mc.attrib.get("configid"),
            "name": _text(mc, "name"),
        })

    # motors (all occurrences, keep configid so a sim's motor can be resolved)
    for m in root.findall(".//motor"):
        man = _text(m, "manufacturer")
        des = _text(m, "designation")
        if not des:
            continue
        cls = re.match(r"^((?:\d+/\d+)?[A-O])(?=[0-9\-]|$)", des)
        out["motors"].append({
            "manufacturer": man,
            "designation": des,
            "impulse_class": cls.group(1) if cls else None,
            "diameter_m": _num(_text(m, "diameter")),
            "length_m": _num(_text(m, "length")),
            "configid": m.attrib.get("configid"),
        })

    comps, total_len, stage_count, cluster = walk(rocket)
    out["total_length_m"] = round(total_len, 5)

    out["stage_count"] = stage_count
    out["pods"] = len(rocket.findall(".//subcomponents/pod"))
    out["cluster"] = cluster

    for c in comps:
        el, tag = c["el"], c["tag"]
        if tag == "nosecone":
            ar = _num(_text(el, "aftradius"))
            out["nose_cones"].append({
                "name": c["name"],
                "shape": _text(el, "shape"),
                "length_m": c["length_m"],
                "od_m": (2 * ar) if ar is not None else None,
            })
        elif tag == "bodytube":
            od = _od_m(el)
            thick = _num(_text(el, "thickness"))
            out["body_tubes"].append({
                "name": c["name"],
                "length_m": c["length_m"],
                "od_m": od,
                "thickness_m": thick,
                "id_m": (od - 2 * thick) if (od is not None and thick is not None) else None,
                "station_m": round(c["station_m"], 4),
            })
        elif tag == "transition":
            fr = _num(_text(el, "foreradius"))
            ar = _num(_text(el, "aftradius"))
            out["transitions"].append({
                "name": c["name"],
                "length_m": c["length_m"],
                "fore_od_m": (2 * fr) if fr is not None else None,
                "aft_od_m": (2 * ar) if ar is not None else None,
            })
        elif tag in FINSET_TAGS:
            geo = _finset_geometry(el)
            geo["name"] = c["name"]
            geo["position_from_tail_m"] = round(max(0.0, total_len - c["station_m"]), 5)
            out["finsets"].append(geo)
        elif tag in ("parachute", "streamer"):
            out["recovery"].append({
                "kind": tag,
                "name": c["name"],
                "diameter_m": _num(_text(el, "diameter")),
                "deployevent": _text(el, "deployevent"),
                "deployaltitude_m": _num(_text(el, "deployaltitude")),
            })
        elif tag == "masscomponent":
            out["mass_components"].append({
                "name": c["name"],
                "mass_kg": _num(_text(el, "mass")),
                "type": _text(el, "masscomponenttype"),
            })

    # cluster detection is handled inside walk() (instancecount > 1 on a
    # non-finset component); a motormount holds one <motor> per flight
    # configuration, not a cluster, so it is deliberately not counted here.

    # ballast = mass components explicitly typed/ named ballast
    ballast = 0.0
    for mc in out["mass_components"]:
        label = (mc["name"] or "").lower() + " " + (mc["type"] or "").lower()
        if "ballast" in label or "nose weight" in label or "noseweight" in label:
            ballast += mc["mass_kg"] or 0.0
    out["ballast_mass_kg"] = round(ballast, 5)

    out["simulations"] = parse_simulations(root)
    return out


def pick_metrics(data, sim_name=None):
    """Return (metrics_dict, sim_name, source_tag).

    Prefer the simulation whose <name> equals sim_name; else the highest-apogee
    simulation that has metrics; else (None, None, 'unsimulated').
    """
    sims = [s for s in data.get("simulations", []) if s.get("metrics")]
    if not sims:
        return None, None, "unsimulated"
    if sim_name:
        for s in sims:
            if s["name"] == sim_name:
                return s["metrics"], s["name"], "stored"
    best = max(sims, key=lambda s: s["metrics"].get("apogee_m") or -1)
    return best["metrics"], best["name"], "stored"


if __name__ == "__main__":
    import json
    import sys
    for p in sys.argv[1:]:
        d = extract(p)
        for c in d["body_tubes"]:
            c.pop("el", None)
        d["simulations"] = d["simulations"][:2]
        print(json.dumps(d, indent=1, default=str)[:3000])
