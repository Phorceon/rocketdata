"""Convert old-lossy .ork reference designs into the new <design> schema.

`convert(old_row_or_ork_path)` reads the .ork XML directly (the old JSON lost
axial positions, mass overrides, freeform fin points and per-configuration
motor/deploy settings) and returns a dict:

    {
      "status": "ok" | "unsupported" | "convert_error" | "missing_file",
      "design": {...} | None,          # passes sftgen.schema.parse_design
      "notes": [...],                  # every lossy assumption made
      "reason"/"error": str,           # for unsupported / convert_error
      "resolved_file": str | None,     # the file actually read
      "name": str, "sim_name": str, "configid": str,
      "sim_conditions": {...},         # launch conditions from the chosen sim
    }

Everything OpenRocket represents that the schema cannot (pods, parallel
boosters, tube fins, clusters > 4, a stage with no motor, ...) is marked
"unsupported" with a reason instead of being silently approximated.

With use_or_masses=True (default) a two-pass correction is applied: the
converted design is built and loaded into OpenRocket, per-stage structural
mass is compared against the original file (which includes component mass
overrides and dropped parts like shock cords and launch lugs), and a
"avionics/ballast (override)" mass item is added so the stage mass matches.
"""

from __future__ import annotations

import gzip
import io
import math
import os
import re
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

from . import orkbuild
from .schema import parse_design

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ORK_XML_DIR = REPO_ROOT.parent.parent / "ork_xml"

NUM = re.compile(r"-?\d+\.?\d*(?:[eE][-+]?\d+)?")

CLUSTER_MAP = {"single": 1, "double": 2, "3-ring": 3, "4-ring": 4}
DEPLOY_MAP = {"apogee": "apogee", "altitude": "altitude", "ejection": "ejection"}
SEP_MAP = {"burnout": "burnout", "ejection": "ejection"}


class Unsupported(Exception):
    pass


class ConvertError(Exception):
    pass


# ---------------------------------------------------------------- materials

_BULK_ALIAS = {
    "abs": "ABS - 100% infill", "abs plastic": "ABS - 100% infill",
    "pla": "PLA - 100% infill", "petg": "PETG - 100% infill", "petg-cf": "PETG - 100% infill",
    "polycarbonate": "Polycarbonate (Lexan)",
    "polystyrene ps": "Polystyrene", "styrene plastic": "Polystyrene", "styrene": "Polystyrene",
    "aircraft plywood (birch)": "Plywood (birch)", "aircraft plywood (loc)": "Plywood (birch)",
    "1/8 aircraft plywood": "Plywood (birch)", "aircraft plywood": "Plywood (birch)",
    "plywood": "Plywood (birch)", "rs: aircraft plywood (birch)": "Plywood (birch)",
    "spiral/glassine": "Cardboard", "kraft paper": "Cardboard",
    "paper, spiral kraft glassine": "Cardboard", "paper": "Cardboard",
    "g10 fiberglass": "Fiberglass", "g10": "Fiberglass", "kevlar": "Fiberglass",
    "polyethylene": "Kraft phenolic", "polyethylene (heavy)": "Kraft phenolic",
    "polyethylene (thin)": "Kraft phenolic",
    "aluminium": "Aluminum", "copper": "Brass", "carbon fibre": "Carbon fiber",
    "vulcanized fiber": "Kraft phenolic", "fiber": "Cardboard",
    "nomex": "Cardboard", "phenolic": "Kraft phenolic",
}
_SURFACE_ALIAS = {
    "paper": "Paper (office)", "polyethylene": "Polyethylene (thin)",
    "polyethylene film": "Polyethylene (thin)", "polyethylene ldpe": "Polyethylene (thin)",
    "nylon fabric": "Ripstop nylon", "rip stop nylon": "Ripstop nylon",
    "ripstop": "Ripstop nylon", "mylar polyester film": "Mylar", "mylar film": "Mylar",
    "nylon": "Ripstop nylon", "plastic": "Polyethylene (thin)",
}


def _clean_mat_name(text: str) -> str:
    """'BULK|Cardboard|680.0|Custom' -> 'Cardboard'; 'Tubular nylon (14 mm' -> 'Tubular nylon'."""
    t = (text or "").split(",")[0].strip()
    t = re.sub(r"^(BULK|SURFACE|LINE)\|", "", t)
    t = re.sub(r"\|[0-9.eE+-]+\|[A-Za-z ]+$", "", t)
    return t.strip()


def _map_material(el, surface: bool, notes, where: str) -> str:
    m = el.find("material")
    if m is None or not m.text:
        notes.append(f"{where}: no material; used default")
        return "Ripstop nylon" if surface else "Cardboard"
    name = _clean_mat_name(m.text)
    density = float(m.get("density")) if m.get("density") else None
    table = orkbuild.SURFACE_DENSITY if surface else orkbuild.BULK_DENSITY
    if name in table:
        return name
    alias = (_SURFACE_ALIAS if surface else _BULK_ALIAS).get(name.lower())
    if alias:
        notes.append(f"{where}: material {name!r} mapped to {alias!r}")
        return alias
    if density is not None:
        best = min(table, key=lambda k: abs(table[k] - density))
        notes.append(
            f"{where}: material {name!r} (density {density:g}) mapped to {best!r} "
            f"(density {table[best]:g}, nearest)"
        )
        return best
    notes.append(f"{where}: unknown material {name!r} with no density; used default")
    return "Mylar" if surface else "Cardboard"


def _map_material_text(name, notes, where):
    fake = ET.fromstring(f'<x><material>{escape(name)}</material></x>')
    return _map_material(fake, False, notes, where)


# ---------------------------------------------------------------- xml helpers

def _t(el, tag):
    return el.findtext(tag)


def _num(el, tag, default=None):
    """Numeric child text; 'auto'/'auto <stale>'/'filled'/'none' -> default.

    NOTE: OpenRocket writes 'auto <computed>' and RE-RESOLVES it on load from
    the neighbours, so the recorded number is stale and must not be trusted."""
    v = el.findtext(tag)
    if v is None or v in ("auto", "filled", "none") or v.startswith("auto "):
        return default
    m = NUM.search(v)
    return float(m.group()) if m else default


def _num_text(txt, default=None):
    if txt is None:
        return default
    m = NUM.search(txt)
    return float(m.group()) if m else default


def _axial(el) -> tuple[str, float]:
    """Return (method, offset) from <axialoffset> or legacy <position>."""
    ax = el.find("axialoffset")
    if ax is not None:
        return ax.get("method", "top"), _num_text(ax.text, 0.0)
    p = el.find("position")
    if p is not None:
        return p.get("type", "top"), _num_text(p.text, 0.0)
    return "top", 0.0


def _front_pos(el, tube_len: float, comp_len: float, tube_abs: float) -> float:
    """Convert a child's axial offset to its front position from the parent tube's top."""
    method, v = _axial(el)
    if method == "top":
        return v
    if method == "bottom":
        return tube_len - v - comp_len
    if method == "middle":
        return tube_len / 2 + v - comp_len / 2
    if method == "absolute":
        return v - tube_abs
    return v


# ---------------------------------------------------------------- file loading

def _load_ork_bytes(p: Path) -> ET.Element:
    d = p.read_bytes()
    if d[:2] == b"\x1f\x8b":
        d = gzip.decompress(d)
    if d[:2] == b"PK":
        z = zipfile.ZipFile(io.BytesIO(d))
        for n in z.namelist():
            if "ork" in n.lower() or n.endswith(".xml"):
                d = z.read(n)
                break
    return ET.fromstring(d)


def _resolve_ork(file_key: str, repo_root: Path, ork_xml_dir: Path | None, notes):
    """Locate the best XML for a row's 'file' key. Returns (root, resolved_path)."""
    name = Path(file_key).name
    ork_path = Path(file_key)
    if not ork_path.is_absolute():
        ork_path = repo_root / file_key
    if not ork_path.exists() and (repo_root / "ork" / name).exists():
        ork_path = repo_root / "ork" / name
    if ork_path.exists():
        return _load_ork_bytes(ork_path), ork_path

    if ork_xml_dir is not None:
        x = ork_xml_dir / (name + ".xml")
        if x.exists():
            return ET.parse(x).getroot(), x
    if "__" in name:
        base = name.split("__")[0] + ".ork"
        for cand in (repo_root / "ork" / base,
                     (ork_xml_dir / (base + ".xml")) if ork_xml_dir else None):
            if cand is not None and cand.exists():
                notes.append(
                    f"variant file {name!r} is missing; used base file {cand.name!r} "
                    f"(masses/motors may differ from the variant)"
                )
                if cand.suffix == ".xml":
                    return ET.parse(cand).getroot(), cand
                return _load_ork_bytes(cand), cand
    return None, None


# ---------------------------------------------------------------- conditions

def _sim_info(root, sim_name, notes):
    """Pick the <simulation> matching sim_name (else the first)."""
    sims = list(root.iter("simulation"))
    if not sims:
        return None, {}, None
    sel = sims[0]
    if sim_name:
        for s in sims:
            if s.findtext("name") == sim_name:
                sel = s
                break
        else:
            notes.append(f"simulation {sim_name!r} not found; used {sims[0].findtext('name')!r}")
    cond_el = sel.find("conditions")
    configid = cond_el.findtext("configid") if cond_el is not None else None
    cond = {
        "wind_ms": _num(cond_el, "windaverage", 2.0) if cond_el is not None else 2.0,
        "wind_turbulence": _num(cond_el, "windturbulence", 0.1) if cond_el is not None else 0.1,
        "rail_length_m": _num(cond_el, "launchrodlength", 1.5) if cond_el is not None else 1.5,
        "launch_angle_deg": math.degrees(_num(cond_el, "launchrodangle", 0.0)) if cond_el is not None else 0.0,
        "site_altitude_m": _num(cond_el, "launchaltitude", 0.0) if cond_el is not None else 0.0,
        "time_step_s": _num(cond_el, "timestep", 0.05) if cond_el is not None else 0.05,
        "launch_latitude_deg": _num(cond_el, "launchlatitude", 45.0) if cond_el is not None else 45.0,
        "geodetic": (cond_el.findtext("geodeticmethod") or "flat") if cond_el is not None else "flat",
    }
    sim_kind = sel.findtext("simulator") or ""
    if sim_kind and "RK4" not in sim_kind:
        notes.append(f"simulator {sim_kind!r} is not RK4Simulator; builder always writes RK4")
    if cond.get("geodetic") not in ("flat", None):
        notes.append(f"geodetic method {cond['geodetic']!r}; builder always writes 'flat'")
    if cond.get("launch_latitude_deg") not in (None, 45.0):
        notes.append(f"launch latitude {cond['launch_latitude_deg']}; builder always writes 45.0")
    return configid, cond, sel.findtext("name")


def _default_configid(root):
    for mc in root.iter("motorconfiguration"):
        if mc.get("default") == "true":
            return mc.get("configid")
    for mc in root.iter("motorconfiguration"):
        return mc.get("configid")
    return None


# ---------------------------------------------------------------- components

def _external_radius(el) -> tuple[float | None, float | None]:
    """(fore_radius, aft_radius) raw from XML; None = auto/unknown."""
    tag = el.tag
    if tag == "nosecone":
        return 0.0, _num(el, "aftradius")
    if tag == "bodytube":
        return _num(el, "radius"), _num(el, "radius")
    if tag == "transition":
        return _num(el, "foreradius"), _num(el, "aftradius")
    return None, None


def _freeform_to_trap(el, notes, name) -> dict:
    pts = [(float(p.get("x")), float(p.get("y"))) for p in el.iter("point")]
    if len(pts) < 3:
        raise Unsupported(f"freeform fin set {name!r} has {len(pts)} points")
    if min(y for _, y in pts) < -1e-6:
        notes.append(f"{name}: fin tab (points below root) dropped from freeform fin")
    clipped = _clip_poly(pts, 0.0)
    if len(clipped) < 3:
        raise Unsupported(f"freeform fin set {name!r} has no area above the root")
    area = abs(_shoelace(clipped))
    span = max(y for _, y in clipped)
    root_pts = sorted(x for x, y in clipped if abs(y) < 1e-9)
    if len(root_pts) >= 2:
        root = root_pts[-1] - root_pts[0]
        le_x = root_pts[0]
    else:
        root = max(x for x, _ in clipped) - min(x for x, _ in clipped)
        le_x = min(x for x, _ in clipped)
    cx = _centroid_x(clipped)
    tip = 2 * area / span - root if span > 0 else 0.0
    tip = min(max(tip, 0.0), 1.0)
    sweep = _solve_sweep(root, tip, span, cx - le_x)
    notes.append(
        f"{name}: freeform fin ({len(pts)} pts) approximated as trapezoid "
        f"(root {root * 1000:.1f} mm, tip {tip * 1000:.1f} mm, span {span * 1000:.1f} mm, "
        f"sweep {sweep * 1000:.1f} mm; same root/span/area, centroid-matched sweep)"
    )
    return {"root_chord_m": root, "tip_chord_m": tip, "span_m": span, "sweep_m": sweep}


def _clip_poly(pts, y0):
    out = []
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        if y1 >= y0:
            out.append((x1, y1))
        if (y1 - y0) * (y2 - y0) < 0:
            t = (y0 - y1) / (y2 - y1)
            out.append((x1 + t * (x2 - x1), y0))
    return out


def _shoelace(pts):
    return 0.5 * sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]))


def _centroid_x(pts):
    a = _shoelace(pts)
    if abs(a) < 1e-12:
        return sum(x for x, _ in pts) / len(pts)
    return sum((x1 + x2) * (x1 * y2 - x2 * y1)
               for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1])) / (6 * a)


def _trap_cx(root, tip, span, sweep):
    return _centroid_x([(0, 0), (root, 0), (sweep + tip, span), (sweep, span)])


def _solve_sweep(root, tip, span, target_cx):
    c0 = _trap_cx(root, tip, span, 0.0)
    c1 = _trap_cx(root, tip, span, 0.01)
    slope = (c1 - c0) / 0.01
    if abs(slope) < 1e-9:
        return 0.0
    return (target_cx - c0) / slope


def _clamp(v, lo, hi, what, notes):
    if v < lo:
        notes.append(f"{what} {v:g} m below schema min {lo} m; clamped")
        return lo
    if v > hi:
        notes.append(f"{what} {v:g} m above schema max {hi} m; clamped")
        return hi
    return v


def _fins(el, tube_len, tube_abs, notes, parent_len=None, parent_abs=None) -> dict:
    """Convert a finset. `parent_*` describe the element the fin is mounted on
    (normally the same tube); when a fin is mounted on a transition/nose we
    re-host it on `tube_*` while preserving its absolute position."""
    parent_len = tube_len if parent_len is None else parent_len
    parent_abs = tube_abs if parent_abs is None else parent_abs
    tag = el.tag
    name = _t(el, "name") or tag
    count = int(round(_num(el, "fincount", 3)))
    count = int(_clamp(count, 2, 8, f"{name} fin count", notes))
    thick = _clamp(_num(el, "thickness", 0.003), 0.0008, 0.02, f"{name} thickness", notes)
    mat = _map_material(el, False, notes, name)
    if tag == "freeformfinset":
        dims = _freeform_to_trap(el, notes, name)
        kind = "trapezoidal_fins"
        root = dims["root_chord_m"]
    elif tag == "ellipticalfinset":
        kind = "elliptical_fins"
        root = _num(el, "rootchord", 0.05)
        dims = {"span_m": _num(el, "height", 0.05)}
    else:
        kind = "trapezoidal_fins"
        root = _num(el, "rootchord", 0.05)
        dims = {
            "tip_chord_m": _num(el, "tipchord", root * 0.5),
            "span_m": _num(el, "height", 0.05),
            "sweep_m": _num(el, "sweeplength", 0.0),
        }
    if root < 0.01:
        f = 0.01 / max(root, 1e-9)
        notes.append(f"{name}: root chord {root * 1000:.1f} mm below 10 mm schema min; "
                     f"raised to 10 mm (area and fin centroid preserved)")
        if kind == "trapezoidal_fins":
            area = (root + dims["tip_chord_m"]) / 2 * dims["span_m"]
            cx0 = _trap_cx(root, dims["tip_chord_m"], dims["span_m"], dims["sweep_m"])
            dims["tip_chord_m"] = max(0.0, min(1.0, 2 * area / dims["span_m"] - 0.01))
            dims["sweep_m"] = _solve_sweep(0.01, dims["tip_chord_m"], dims["span_m"], cx0)
        root = 0.01
    if kind == "trapezoidal_fins":
        dims["tip_chord_m"] = _clamp(dims["tip_chord_m"], 0.0, 1.0, f"{name} tip chord", notes)
        dims["sweep_m"] = _clamp(dims["sweep_m"], -0.5, 1.0, f"{name} sweep", notes)
    dims["span_m"] = _clamp(dims["span_m"], 0.005, 1.0, f"{name} span", notes)
    root = _clamp(root, 0.01, 1.0, f"{name} root chord", notes)

    method, v = _axial(el)
    # fin root leading edge in absolute rocket coordinates
    if method == "absolute":
        le_abs = v
    elif method == "top":
        le_abs = parent_abs + v
    elif method == "bottom":
        le_abs = parent_abs + parent_len + v - root
    elif method == "middle":
        le_abs = parent_abs + parent_len / 2 + v - root / 2
    else:
        le_abs = parent_abs + v
    off = (tube_abs + tube_len) - (le_abs + root)  # host tube aft -> fin root TE
    if parent_abs != tube_abs or parent_len != tube_len:
        notes.append(f"{name}: fin mounted on a non-tube component; re-hosted on a "
                     f"neighbouring body tube (offset_from_aft {off * 1000:.1f} mm)")
    elif method != "bottom":
        notes.append(f"{name}: fin axial method {method!r} -> offset_from_aft "
                     f"{off * 1000:.1f} mm")
    off = _clamp(off, -0.5, 6.0, f"{name} offset_from_aft", notes)
    out = {"type": kind, "count": count, "thickness_m": thick, "material": mat,
           "offset_from_aft_m": round(off, 6), "root_chord_m": root}
    out.update({k: round(vv, 6) for k, vv in dims.items() if k != "root_chord_m"})
    return out


def _deploy(el, configid, notes, name):
    dc = None
    for c in el.findall("deploymentconfiguration"):
        if c.get("configid") == configid:
            dc = c
    src = dc if dc is not None else el
    if dc is not None:
        notes.append(f"{name}: deploy settings taken from deploymentconfiguration "
                     f"{str(configid)[:8]}")
    event = (_t(src, "deployevent") or "ejection").lower()
    if event not in DEPLOY_MAP:
        notes.append(f"{name}: deploy event {event!r} not representable; "
                     f"approximated as 'ejection'")
        event = "ejection"
    alt = _num(src, "deployaltitude")
    delay = _clamp(_num(src, "deploydelay", 0.0), 0.0, 30.0,
                   f"{name} deploy delay", notes)
    if event == "altitude" and (alt is None or alt < 10.0):
        notes.append(f"{name}: deploy altitude {alt}; clamped to 10 m")
        alt = max(alt or 10.0, 10.0)
    if alt is not None and alt > 5000.0:
        notes.append(f"{name}: deploy altitude {alt} clamped to 5000 m")
        alt = 5000.0
    return event, alt, delay


def _tube_pos(el, tube_len, tube_abs, comp_len, notes, name):
    pos = _front_pos(el, tube_len, comp_len, tube_abs)
    hi = max(tube_len - 0.005, -0.5)
    if pos > hi:
        notes.append(f"{name}: position {pos * 1000:.0f} mm past tube end; clamped")
        pos = hi
    return _clamp(pos, -0.5, 6.0, f"{name} position", notes)


def _recovery(el, tube_len, tube_abs, configid, notes) -> dict:
    name = _t(el, "name") or el.tag
    event, alt, delay = _deploy(el, configid, notes, name)
    packed_len = _num(el, "packedlength", 0.05)
    pos = _tube_pos(el, tube_len, tube_abs, packed_len, notes, name)
    mat = _map_material(el, True, notes, name)
    if el.tag == "parachute":
        cd = _t(el, "cd")
        cdm = NUM.search(cd) if cd and cd != "auto" else None
        cd = _clamp(float(cdm.group()) if cdm else 0.8, 0.3, 2.5, f"{name} cd", notes)
        d = _clamp(_num(el, "diameter", 0.3), 0.08, 8.0, f"{name} diameter", notes)
        return {"type": "parachute", "diameter_m": d, "cd": cd, "deploy_event": event,
                "deploy_altitude_m": alt, "deploy_delay_s": delay, "material": mat,
                "position_from_top_m": round(pos, 6)}
    return {"type": "streamer",
            "strip_length_m": _clamp(_num(el, "striplength", 0.5), 0.1, 10.0,
                                     f"{name} strip length", notes),
            "strip_width_m": _clamp(_num(el, "stripwidth", 0.05), 0.01, 1.0,
                                    f"{name} strip width", notes),
            "deploy_event": event, "deploy_altitude_m": alt, "deploy_delay_s": delay,
            "material": mat, "position_from_top_m": round(pos, 6)}


def _mass_item(el, tube_len, tube_abs, notes) -> dict | None:
    name = (_t(el, "name") or "Mass component")[:40]
    if (_t(el, "masscomponenttype") or "") == "payload" and "payload" not in name.lower():
        name = ("payload " + name)[:40]
    m = _num(el, "mass")
    if m is None or m <= 0:
        notes.append(f"{name}: mass {m}; dropped (schema requires positive mass)")
        return None
    m = _clamp(m, 1e-6, 50.0, f"{name} mass", notes)
    pos = _tube_pos(el, tube_len, tube_abs, _num(el, "packedlength", 0.03), notes, name)
    return {"type": "mass", "name": name, "mass_kg": m,
            "position_from_top_m": round(pos, 6)}


# ---------------------------------------------------------------- motor mount

_DIGEST_INDEX = None


def _motor_by_digest(mm_el):
    """Resolve any <motor> in this mount by thrust-curve digest -> (designation, manufacturer)."""
    global _DIGEST_INDEX
    digests = [m.get("digest") for m in mm_el.findall("motor") if m.get("digest")]
    if not digests:
        return None
    if _DIGEST_INDEX is None:
        _DIGEST_INDEX = {}
        try:
            from scripts.or_headless import _helper
            _helper()
            from jpype import JClass
            db = JClass("info.openrocket.core.startup.Application").getThrustCurveMotorSetDatabase()
            for s in db.getMotorSets():
                for mo in s.getMotors():
                    d = str(mo.getDigest())
                    if d not in _DIGEST_INDEX:
                        _DIGEST_INDEX[d] = (str(mo.getDesignation()),
                                            str(mo.getManufacturer().getDisplayName()))
        except Exception:
            _DIGEST_INDEX = {}
            return None
    for d in digests:
        if d in _DIGEST_INDEX:
            return _DIGEST_INDEX[d]
    return None


def _motor_of(mm, configid, stage_name, notes) -> dict:
    motors = mm.findall("motor")
    if not motors:
        raise Unsupported(f"stage {stage_name!r}: motor mount has no <motor> "
                          f"for any configuration")
    sel = [m for m in motors if m.get("configid") == configid]
    if not sel:
        sel = motors[:1]
        if len(motors) > 1:
            notes.append(
                f"stage {stage_name!r}: no motor matches configid {str(configid)[:8]}; "
                f"used {_t(sel[0], 'designation')!r} (of {len(motors)} configs)"
            )
    m = sel[0]
    designation = _t(m, "designation")
    if not designation:
        raise ConvertError(f"stage {stage_name!r}: motor has no designation")
    delay_txt = (_t(m, "delay") or "none").strip().lower()
    if delay_txt in ("none", "plugged"):
        delay = None
    else:
        delay = _clamp(_num_text(delay_txt, 0.0), 0.0, 30.0, "motor delay", notes)

    ign = None
    for c in mm.findall("ignitionconfiguration"):
        if c.get("configid") == configid:
            ign = c
    isrc = ign if ign is not None else mm
    event = (_t(isrc, "ignitionevent") or "automatic").lower()
    ign_delay = _clamp(_num(isrc, "ignitiondelay", 0.0), 0.0, 30.0,
                       "motor ignition delay", notes)
    return {
        "manufacturer": _t(m, "manufacturer"),
        "designation": designation,
        "delay_s": delay,
        "_ignition_event": event,
        "_ignition_delay_s": ign_delay,
    }


def _motor_mount(parent_el, mm_parent_tag, tube_len, tube_id, configid, stage_name,
                 from_bottom, notes) -> dict:
    """Build a motor_mount dict from an <innertube> or a <bodytube> that is itself a mount."""
    mm = parent_el.find("motormount")
    motor = _motor_of(mm, configid, stage_name, notes)

    from . import motors as _motors
    minfo = None
    try:
        minfo = _motors.resolve(motor["designation"], motor["manufacturer"])
    except Exception:
        hit = _motor_by_digest(mm)
        if hit:
            notes.append(
                f"stage {stage_name!r}: motor {motor['designation']!r} not in the "
                f"database; resolved by thrust-curve digest to {hit[0]!r} ({hit[1]})")
            motor["designation"], motor["manufacturer"] = hit
            minfo = _motors.resolve(hit[0], hit[1])
        else:
            raise Unsupported(
                f"stage {stage_name!r}: motor {motor['designation']!r} is not in the "
                f"bundled motor database (custom thrust curve)")

    if mm_parent_tag == "innertube":
        od = _num(parent_el, "outerradius", 0.0) * 2
        wall = _num(parent_el, "thickness", 0.0005)
        mlen = _num(parent_el, "length", 0.05)
        clus = _t(parent_el, "clusterconfiguration") or "single"
        scale = _num(parent_el, "clusterscale", 1.0)
        rot = _num(parent_el, "clusterrotation", 0.0)
        if scale != 1.0 or rot != 0.0:
            notes.append(f"stage {stage_name!r}: cluster scale {scale}/rotation {rot} "
                         f"not representable; geometry only")
        mat = _map_material(parent_el, False, notes, "motor mount")
        method, v = _axial(parent_el)
        if method == "bottom":
            gap = -v  # gap between mount aft end and tube aft end (positive = forward)
        elif method == "top":
            gap = tube_len - v - mlen
        elif method == "middle":
            gap = tube_len / 2 - v - mlen / 2
        else:
            gap = 0.0
        if abs(gap) > 0.001:
            notes.append(
                f"stage {stage_name!r}: motor mount sits {gap * 1000:+.1f} mm from the tube "
                f"aft end; schema mounts are flush, motor overhang adjusted"
            )
    else:  # bodytube-as-motormount (minimum diameter)
        wall = 0.0005
        mlen = (minfo["length_m"] + 0.005) if minfo else tube_len
        clus = "single"
        mat = "Cardboard"
        od = tube_id
        gap = 0.0
        notes.append(f"stage {stage_name!r}: body tube is itself the motor mount "
                     f"(minimum-diameter); modelled as a mount filling the tube")

    if clus in CLUSTER_MAP:
        n = CLUSTER_MAP[clus]
    elif clus == "4-row":
        n = 4
        notes.append(f"stage {stage_name!r}: cluster '4-row' approximated as 4-ring")
    else:
        raise Unsupported(f"stage {stage_name!r}: cluster configuration {clus!r} "
                          f"exceeds schema maximum of 4 motors")

    wall = _clamp(wall, 0.0002, 0.03, "motor mount wall", notes)
    if od > tube_id + 1e-6:
        if mm_parent_tag == "innertube":
            notes.append(f"stage {stage_name!r}: inner tube OD {od * 1000:.1f} mm > tube ID "
                         f"{tube_id * 1000:.1f} mm; clamped to tube ID")
        od = tube_id
    # the mount must swallow the resolved motor
    if minfo is not None:
        need_od = minfo["diameter_m"] + 2 * wall + 1e-4
        if od < need_od:
            if need_od <= tube_id + 1e-6:
                od = need_od
            elif wall > 0.0002:
                wall = 0.0002
                need_od = minfo["diameter_m"] + 2 * wall + 1e-4
                if need_od <= tube_id + 1e-6:
                    od = need_od
        if od < minfo["diameter_m"] + 2 * wall - 1e-6:
            raise Unsupported(
                f"stage {stage_name!r}: motor {motor['designation']!r} "
                f"(d {minfo['diameter_m'] * 1000:.1f} mm) cannot fit inside tube ID "
                f"{tube_id * 1000:.1f} mm even with minimum mount wall"
            )

    overhang = _clamp(_num(mm, "overhang", 0.0) - gap, 0.0, 0.2,
                      "motor overhang", notes)
    mlen = _clamp(mlen, 0.005, min(6.0, tube_len), "motor mount length", notes)

    if from_bottom == 0:
        if motor["_ignition_event"] not in ("automatic", "launch"):
            notes.append(f"stage {stage_name!r}: bottom-stage ignition event "
                         f"{motor['_ignition_event']!r} not representable; ignites at launch")
        ign_delay = 0.0
    else:
        if motor["_ignition_event"] not in ("automatic", "burnout"):
            notes.append(f"stage {stage_name!r}: upper-stage ignition event "
                         f"{motor['_ignition_event']!r} approximated as ignition at "
                         f"booster burnout + delay")
        ign_delay = motor["_ignition_delay_s"]

    return {
        "type": "motor_mount",
        "outer_diameter_m": round(od, 6),
        "length_m": round(mlen, 6),
        "wall_thickness_m": round(wall, 6),
        "material": mat,
        "motor": {"manufacturer": motor["manufacturer"], "designation": motor["designation"],
                  "delay_s": motor["delay_s"], "ignition_delay_s": ign_delay},
        "cluster_count": n,
        "overhang_m": round(overhang, 6),
        "centering_ring_count": 0,  # filled in by caller
        "centering_ring_material": "Plywood (birch)",
    }


# ---------------------------------------------------------------- stage build

_DROPPED = ("shockcord", "launchlug", "railbutton", "bulkhead", "engineblock",
            "tubecoupler", "centeringring")
_UNSUPPORTED = {"podset": "pod set", "parallelstage": "parallel booster stage",
                "boosterset": "parallel booster set", "tubefinset": "tube fins"}


def _resolve_radii(externals, prev_aft=None):
    """Resolve fore/aft radii (None = auto) by neighbour inheritance.

    OR auto semantics: a body tube's auto radius = previous external's radius;
    a nose cone's auto aft radius = next external's radius; a transition's
    auto fore = previous external's aft, auto aft = next external's fore.
    `prev_aft` seeds the first component of a lower stage with the previous
    stage's last aft radius (stages stack contiguously).
    """
    fore = []
    aft = []
    for ch in externals:
        f, a = _external_radius(ch)
        fore.append(f)
        aft.append(a)
    n = len(externals)
    for _ in range(4):
        for i, ch in enumerate(externals):
            if ch.tag == "nosecone":
                fore[i] = 0.0
            if fore[i] is None:
                if i > 0 and aft[i - 1] is not None:
                    fore[i] = aft[i - 1]
                elif i == 0 and prev_aft is not None:
                    fore[i] = prev_aft
            if aft[i] is None and i + 1 < n and fore[i + 1] is not None:
                aft[i] = fore[i + 1]
            if ch.tag == "bodytube":
                if fore[i] is None and aft[i] is not None:
                    fore[i] = aft[i]
                if aft[i] is None and fore[i] is not None:
                    aft[i] = fore[i]
    for i, ch in enumerate(externals):
        if fore[i] is None:
            nxt = next((r for r in (fore[i + 1:] + aft[i + 1:]) if r is not None),
                       prev_aft if i == 0 else None)
            fore[i] = nxt if nxt is not None else (aft[i] if aft[i] is not None else 0.01)
        if aft[i] is None:
            prv = next((r for r in reversed(aft[:i] + fore[:i]) if r is not None), None)
            aft[i] = prv if prv is not None else fore[i]
        if ch.tag == "bodytube":
            aft[i] = fore[i]
    return fore, aft


def _build_stage(st_el, idx, n_stages, stage_top_x, configid, notes,
                 prev_aft=None) -> tuple[dict, float]:
    name = (_t(st_el, "name") or f"Stage {idx}")[:40]
    sc = st_el.find("subcomponents")
    if sc is None or len(sc) == 0:
        raise Unsupported(f"stage {name!r} has no components")

    externals = []
    for ch in sc:
        tag = ch.tag
        if tag in _UNSUPPORTED:
            raise Unsupported(f"{_UNSUPPORTED[tag]} on stage {name!r} "
                              f"cannot be represented (no parallel/pod components)")
        if tag not in ("nosecone", "bodytube", "transition"):
            raise Unsupported(f"unexpected stage component <{tag}> on stage {name!r}")
        externals.append(ch)

    fore, aft = _resolve_radii(externals, prev_aft)

    # cumulative absolute x of each external's front
    comp_x = []
    x = stage_top_x
    for i, ch in enumerate(externals):
        comp_x.append(x)
        x += _num(ch, "length", 0.0) or 0.0
    stage_len = x - stage_top_x

    comps = []
    dropped = set()
    tubes = []          # (comp_x, length, comp dict) for re-hosting
    orphans = []        # (child_el, parent_len, parent_abs) fin sets on non-tube externals
    orphan_masses = []  # same for mass components
    from_bottom = n_stages - 1 - idx
    for i, ch in enumerate(externals):
        cname = _t(ch, "name") or ch.tag
        where = f"stage {name!r} {cname!r}"
        length = _clamp(_num(ch, "length", 0.05), 0.005, 6.0, f"{where} length", notes)
        thick_raw = _t(ch, "thickness")
        thick = None if thick_raw == "filled" else _num(ch, "thickness")
        mat = _map_material(ch, False, notes, where)

        if ch.tag in ("nosecone", "transition"):
            nsub = ch.find("subcomponents")
            if nsub is not None:
                for och in nsub:
                    if och.tag in ("trapezoidfinset", "ellipticalfinset", "freeformfinset"):
                        orphans.append((och, length, comp_x[i]))
                    elif och.tag == "masscomponent":
                        orphan_masses.append((och, length, comp_x[i]))
                    elif och.tag in _UNSUPPORTED:
                        raise Unsupported(
                            f"{_UNSUPPORTED[och.tag]} ({_t(och, 'name')!r}) inside {where} "
                            f"cannot be represented")
                    else:
                        dropped.add(f"{och.tag} {_t(och, 'name') or ''!r} on {cname!r}")

        if ch.tag == "nosecone":
            shape = (_t(ch, "shape") or "ogive").lower()
            if shape not in ("conical", "ogive", "ellipsoid", "power", "parabolic", "haack"):
                notes.append(f"{where}: nose shape {shape!r} approximated as 'ogive'")
                shape = "ogive"
            if (_t(ch, "isflipped") or "false") == "true":
                raise Unsupported(f"{where}: flipped nose cone (tail cone) not representable")
            shoulder = _clamp(_num(ch, "aftshoulderlength", 0.0), 0.0, 0.5,
                              f"{where} shoulder", notes)
            wall = None if thick is None else _clamp(thick, 0.0002, 0.03,
                                                     f"{where} wall", notes)
            comps.append({
                "type": "nosecone", "shape": shape, "length_m": length,
                "diameter_m": _clamp(2 * aft[i], 0.008, 0.40, f"{where} diameter", notes),
                "wall_thickness_m": wall, "material": mat,
                "shoulder_length_m": shoulder,
            })
        elif ch.tag == "transition":
            shape = (_t(ch, "shape") or "conical").lower()
            if shape not in ("conical", "ogive", "ellipsoid", "power", "parabolic", "haack"):
                notes.append(f"{where}: transition shape {shape!r} approximated as 'conical'")
                shape = "conical"
            wall = None if thick is None else _clamp(thick, 0.0002, 0.03,
                                                     f"{where} wall", notes)
            for sh_tag in ("foreshoulderlength", "aftshoulderlength"):
                if (_num(ch, sh_tag, 0.0) or 0.0) > 1e-6:
                    notes.append(f"{where}: {sh_tag} not representable; dropped")
            comps.append({
                "type": "transition", "shape": shape, "length_m": length,
                "fore_diameter_m": _clamp(2 * fore[i], 0.008, 0.40,
                                          f"{where} fore diameter", notes),
                "aft_diameter_m": _clamp(2 * aft[i], 0.008, 0.40,
                                         f"{where} aft diameter", notes),
                "wall_thickness_m": wall, "material": mat,
            })
        else:  # bodytube
            thick = _clamp(thick if thick is not None else _num(ch, "thickness", 0.002),
                           0.0002, 0.03, f"{where} wall", notes)
            od = _clamp(2 * fore[i], 0.008, 0.40, f"{where} diameter", notes)
            tube_id = od - 2 * thick
            if tube_id <= 0:
                raise Unsupported(f"{where}: wall {thick * 1000:.1f} mm eats the whole "
                                  f"{od * 1000:.1f} mm tube")
            tube_abs = comp_x[i]
            inner = []
            mounts = []
            n_rings = 0
            ring_mat = None
            sub = ch.find("subcomponents")
            if sub is not None:
                for ich in sub:
                    itag = ich.tag
                    iname = _t(ich, "name") or itag
                    if itag in _UNSUPPORTED:
                        raise Unsupported(
                            f"{_UNSUPPORTED[itag]} ({iname!r}) inside {where} "
                            f"cannot be represented")
                    if itag == "innertube":
                        if ich.find("motormount") is not None:
                            mounts.append(ich)
                        else:
                            dropped.add("inner tube without motor mount")
                    elif itag in ("trapezoidfinset", "ellipticalfinset", "freeformfinset"):
                        inner.append(_fins(ich, length, tube_abs, notes))
                    elif itag in ("parachute", "streamer"):
                        inner.append(_recovery(ich, length, tube_abs, configid, notes))
                    elif itag == "masscomponent":
                        mi = _mass_item(ich, length, tube_abs, notes)
                        if mi is not None:
                            inner.append(mi)
                    elif itag == "centeringring":
                        n_rings += int(round(_num(ich, "instancecount", 1)))
                        mel = ich.find("material")
                        if ring_mat is None and mel is not None:
                            ring_mat = _clean_mat_name(mel.text or "")
                    elif itag in _DROPPED:
                        dropped.add(f"{itag} {iname!r}")
                    else:
                        dropped.add(f"{itag} {iname!r}")
            if ch.find("motormount") is not None:
                mounts.append(ch)  # bodytube-as-mount (minimum diameter)
            for m_el in mounts:
                tag_kind = "innertube" if m_el.tag == "innertube" else "bodytube"
                inner.append(_motor_mount(m_el, tag_kind, length, tube_id, configid,
                                          name, from_bottom, notes))
            if n_rings and any(c["type"] == "motor_mount" for c in inner):
                for c in inner:
                    if c["type"] == "motor_mount":
                        c["centering_ring_count"] = min(n_rings, 4)
                        if n_rings > 4:
                            notes.append(f"{where}: {n_rings} centering rings; capped at 4")
                        if ring_mat:
                            c["centering_ring_material"] = _map_material_text(
                                ring_mat, notes, f"{where} centering ring")
                        break
            elif n_rings:
                dropped.add(f"{n_rings} centering rings (no motor mount)")
            comp = {
                "type": "bodytube", "name": cname[:40], "length_m": length,
                "outer_diameter_m": od, "wall_thickness_m": thick, "material": mat,
                "contents": inner,
            }
            tubes.append((tube_abs, length, comp))
            comps.append(comp)

    # re-host fins / masses mounted on non-tube externals (transitions, nose)
    for och, plen, pabs in orphans:
        fin = _fins(och, plen, pabs, notes)  # parent frame -> offset = parent_aft - TE
        te_abs = (pabs + plen) - fin["offset_from_aft_m"]
        if not tubes:
            raise Unsupported(
                f"{_t(och, 'name') or 'fin set'!r} mounted on a non-tube component "
                f"and stage has no bodytube")
        hx, hlen, host = min(
            tubes, key=lambda t: abs((t[0] + t[1]) - te_abs))
        off = _clamp((hx + hlen) - te_abs, -0.5, 6.0, "re-hosted fin offset", notes)
        fin["offset_from_aft_m"] = round(off, 6)
        host["contents"].append(fin)
    # Merge fin sets that sit at the same position: authors split a pattern
    # into several fincount=1 sets with different angle offsets; the schema
    # has no angle offset, so merge them into one set with summed count.
    for comp in comps:
        if comp["type"] != "bodytube":
            continue
        groups = {}
        for x in comp["contents"]:
            if "fins" in x["type"]:
                key = tuple(sorted((k, v) for k, v in x.items() if k != "count"))
                groups.setdefault(key, []).append(x)
        merged = []
        for key, group in groups.items():
            if len(group) > 1:
                total = sum(g["count"] for g in group)
                group[0]["count"] = min(8, total)
                notes.append(
                    f"stage {name!r}: merged {len(group)} same-position fin sets "
                    f"into one {group[0]['count']}-fin set")
            merged.append(group[0])
        comp["contents"] = merged + [x for x in comp["contents"] if "fins" not in x["type"]]

    for och, plen, pabs in orphan_masses:
        fp = _front_pos(och, plen, _num(och, "packedlength", 0.03), pabs)
        x_abs = pabs + fp
        if not tubes:
            dropped.add(f"masscomponent {_t(och, 'name') or ''!r} on non-tube component")
            continue
        hx, hlen, host = min(tubes, key=lambda t: abs((t[0] + t[1] / 2) - x_abs))
        pos = _clamp(x_abs - hx, -0.5, 6.0, "re-hosted mass position", notes)
        pos = min(pos, hlen - 0.005)
        name = (_t(och, "name") or "Mass component")[:40]
        if (_t(och, "masscomponenttype") or "") == "payload" and "payload" not in name.lower():
            name = ("payload " + name)[:40]
        m = _num(och, "mass")
        if m and m > 0:
            host["contents"].append({"type": "mass", "name": name, "mass_kg": m,
                                     "position_from_top_m": round(pos, 6)})
            notes.append(f"{name}: mass component re-hosted from a non-tube component")

    for d in sorted(dropped):
        notes.append(f"stage {name!r}: dropped {d} (mass folded into override correction)")

    if not any(c["type"] == "bodytube"
               and any(x["type"] == "motor_mount" for x in c["contents"])
               for c in comps):
        raise Unsupported(f"stage {name!r} has no motor mount "
                          f"(schema requires one per stage)")

    st = {"name": name, "components": comps}
    if idx > 0:
        st["separation_event"], st["separation_delay_s"] = _separation(
            st_el, configid, name, notes)
    return st, stage_len, aft[-1]


def _separation(st_el, configid, name, notes):
    src = None
    for c in st_el.findall("separationconfiguration"):
        if c.get("configid") == configid:
            src = c
    if src is None and st_el.find("separationevent") is not None:
        src = st_el
    if src is None:
        notes.append(f"stage {name!r}: no separation config; assumed 'ejection' "
                     f"(OpenRocket default)")
        return "ejection", 0.0
    if src is not st_el:
        notes.append(f"stage {name!r}: separation taken from separationconfiguration "
                     f"{str(configid)[:8]}")
    event = (_t(src, "separationevent") or "ejection").lower()
    delay = _clamp(_num(src, "separationdelay", 0.0), 0.0, 30.0,
                   f"stage {name!r} separation delay", notes)
    if _t(src, "separationaltitude"):
        notes.append(f"stage {name!r}: separationaltitude not representable; ignored")
    if event in SEP_MAP:
        return SEP_MAP[event], delay
    if event in ("upperignition", "ignition"):
        notes.append(f"stage {name!r}: separation event {event!r} approximated as 'burnout' "
                     f"(upper stages ignite at booster burnout anyway)")
        return "burnout", delay
    if event == "never":
        raise Unsupported(f"stage {name!r} never separates (sep event 'never')")
    notes.append(f"stage {name!r}: separation event {event!r} approximated as 'burnout'")
    return "burnout", delay


def _fix_diameter_chain(stages, notes):
    """Insert short conical transitions wherever neighbouring externals step > 0.5 mm."""
    def aft_d(c):
        return (c["diameter_m"] if c["type"] == "nosecone" else
                c["outer_diameter_m"] if c["type"] == "bodytube" else c["aft_diameter_m"])

    def fore_d(c):
        return (c["diameter_m"] if c["type"] == "nosecone" else
                c["outer_diameter_m"] if c["type"] == "bodytube" else c["fore_diameter_m"])

    for st in stages:
        out = [st["components"][0]]
        for c in st["components"][1:]:
            prev = out[-1]
            if abs(aft_d(prev) - fore_d(c)) > 0.0005:
                notes.append(
                    f"stage {st['name']!r}: diameter step {aft_d(prev) * 1000:.1f} -> "
                    f"{fore_d(c) * 1000:.1f} mm; inserted a short conical transition")
                out.append(_bridge(aft_d(prev), fore_d(c), prev, c))
            out.append(c)
        st["components"] = out
    for i in range(len(stages) - 1):
        upper_last = stages[i]["components"][-1]
        lower_first = stages[i + 1]["components"][0]
        if abs(aft_d(upper_last) - fore_d(lower_first)) > 0.0005:
            notes.append(
                f"stage boundary: {stages[i]['name']!r} tail "
                f"{aft_d(upper_last) * 1000:.1f} mm vs {stages[i + 1]['name']!r} fore "
                f"{fore_d(lower_first) * 1000:.1f} mm; inserted a short conical "
                f"transition at the top of the lower stage")
            stages[i + 1]["components"].insert(
                0, _bridge(aft_d(upper_last), fore_d(lower_first), upper_last, lower_first))


def _bridge(fore_d, aft_d, prev_c, next_c):
    lo, hi = min(fore_d, aft_d), max(fore_d, aft_d)
    wall = next((c.get("wall_thickness_m") for c in (next_c, prev_c)
                 if c.get("wall_thickness_m")), 0.002)
    return {
        "type": "transition", "shape": "conical",
        "length_m": min(0.02, max(0.005, (hi - lo) / 2)),
        "fore_diameter_m": max(fore_d, 0.008), "aft_diameter_m": max(aft_d, 0.008),
        "wall_thickness_m": wall, "material": next_c.get("material") or "Cardboard",
    }


# ---------------------------------------------------------------- OR masses

def _or_stage_masses(doc):
    """Per-stage (top-first) component mass sums honoring mass overrides."""
    def subtree(comp):
        if comp.isMassOverridden():
            if comp.isSubcomponentsOverriddenMass():
                return float(comp.getOverrideMass())
            m = float(comp.getOverrideMass())
        else:
            m = float(comp.getComponentMass())
        for c in comp.getChildren():
            m += subtree(c)
        return m

    return [subtree(st) for st in doc.getRocket().getStageList()]


def _or_stage_cg(doc):
    """Per-stage (top-first) CG x in absolute coordinates (structure only)."""
    out = []
    for st in doc.getRocket().getStageList():
        num = den = 0.0

        def rec(comp):
            nonlocal num, den
            if comp.isMassOverridden() and comp.isSubcomponentsOverriddenMass():
                m = float(comp.getOverrideMass())
            else:
                m = (float(comp.getOverrideMass()) if comp.isMassOverridden()
                     else float(comp.getComponentMass()))
            if m > 0:
                locs = comp.getComponentLocations()
                x = float(locs[0].x) if len(locs) else 0.0
                try:
                    x += float(comp.getComponentCG().x)
                except Exception:
                    pass
                num += m * x
                den += m
            if not (comp.isMassOverridden() and comp.isSubcomponentsOverriddenMass()):
                for c in comp.getChildren():
                    rec(c)
        if st.isMassOverridden() and st.isSubcomponentsOverriddenMass():
            m = float(st.getOverrideMass())
            x = float(st.getOverrideCGX()) if st.isCGOverridden() else 0.0
            num, den = m * x, m
        else:
            for c in st.getChildren():
                rec(c)
        out.append(num / den if den > 0 else None)
    return out


def _or_temp_doc(orh, root: ET.Element):
    xml = ET.tostring(root, encoding="unicode")
    if not xml.startswith("<?xml"):
        xml = '<?xml version="1.0" encoding="utf-8"?>' + xml
    fd, path = tempfile.mkstemp(suffix=".ork", prefix="conv_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(xml)
        return orh.load_doc(path)
    finally:
        os.unlink(path)


def apply_or_mass_correction(result: dict, doc_orig, notes) -> None:
    """Add a mass item per stage so each converted stage's structural mass
    matches the original file's (overrides and dropped parts included), as
    computed by OpenRocket itself. Mutates result['design']."""
    from scripts.or_headless import _helper

    orh = _helper()
    design = result["design"]
    orig_masses = _or_stage_masses(doc_orig)
    orig_cgs = _or_stage_cg(doc_orig)

    try:
        d = parse_design(design)
        xml = orkbuild.to_ork_xml(d, None)
        fd, p = tempfile.mkstemp(suffix=".ork", prefix="conv_")
        try:
            with os.fdopen(fd, "w") as fh:
                fh.write(xml)
            doc_conv = orh.load_doc(p)
        finally:
            os.unlink(p)
    except Exception as e:
        notes.append(f"mass-correction pass skipped (converted build failed: {e})")
        return
    conv_masses = _or_stage_masses(doc_conv)
    conv_cgs = _or_stage_cg(doc_conv)

    tops = []
    x = 0.0
    for st in design["stages"]:
        tops.append(x)
        x += sum(c["length_m"] for c in st["components"])

    for i, st in enumerate(design["stages"]):
        if i >= len(orig_masses):
            break
        delta = orig_masses[i] - conv_masses[i]
        if abs(delta) < 0.0005:
            continue
        if delta < 0:
            notes.append(
                f"stage {st['name']!r}: converted structure is {-delta * 1000:.1f} g heavier "
                f"than the original (overrides/geometry not representable); left as-is")
            continue
        tubes = [c for c in st["components"] if c["type"] == "bodytube"]
        if not tubes:
            notes.append(f"stage {st['name']!r}: +{delta * 1000:.1f} g correction needed "
                         f"but stage has no bodytube to hold it")
            continue
        tube = max(tubes, key=lambda t: t["length_m"])
        tube_top = tops[i] + sum(c["length_m"] for c in st["components"][:st["components"].index(tube)])
        m_c, dm = conv_masses[i], delta
        cg_o, cg_c = orig_cgs[i], conv_cgs[i]
        if cg_o is not None and cg_c is not None and dm > 1e-9:
            x_target = cg_o + (m_c / dm) * (cg_o - cg_c)
        else:
            x_target = tube_top + tube["length_m"] / 2
        lo, hi = tube_top + 0.005, tube_top + tube["length_m"] - 0.005
        x_clamped = min(max(x_target, lo), hi)
        if abs(x_clamped - x_target) > 1e-6:
            notes.append(f"stage {st['name']!r}: correction-mass CG target outside the "
                         f"tube; clamped")
        item = {"type": "mass", "name": "avionics/ballast (override)",
                "mass_kg": round(dm, 6),
                "position_from_top_m": round(x_clamped - tube_top, 6)}
        tube["contents"].append(item)
        notes.append(
            f"stage {st['name']!r}: +{dm * 1000:.1f} g override/dropped-part mass added "
            f"in {(tube.get('name') or 'body tube')!r} at "
            f"{item['position_from_top_m'] * 1000:.0f} mm from top")


# ---------------------------------------------------------------- public API

def convert(source, sim_name: str | None = None, repo_root=None,
            ork_xml_dir=None, use_or_masses: bool = True) -> dict:
    """Convert one old design into the new schema. `source` is a row dict
    (keys 'file', 'sim') or an .ork path string."""
    notes: list[str] = []
    repo_root = Path(repo_root) if repo_root else REPO_ROOT
    ork_xml_dir = Path(ork_xml_dir) if ork_xml_dir else DEFAULT_ORK_XML_DIR
    if not ork_xml_dir.exists():
        ork_xml_dir = None

    if isinstance(source, dict):
        file_key = source.get("file")
        sim_name = sim_name or source.get("sim")
    else:
        file_key = str(source)
    if not file_key:
        return {"status": "convert_error", "error": "no file key", "design": None,
                "notes": notes}

    root, resolved = _resolve_ork(file_key, repo_root, ork_xml_dir, notes)
    if root is None:
        return {"status": "missing_file", "error": f"no .ork found for {file_key!r}",
                "design": None, "notes": notes, "resolved_file": None}

    rocket = root.find("rocket")
    if rocket is None:
        return {"status": "convert_error", "error": "no <rocket> in file",
                "design": None, "notes": notes, "resolved_file": str(resolved)}

    configid, cond, picked_sim = _sim_info(root, sim_name, notes)
    if configid is None:
        configid = _default_configid(root)
        notes.append("no configid on the simulation; used the default motor configuration")

    common = {"resolved_file": str(resolved), "name": _t(rocket, "name"),
              "sim_name": picked_sim, "configid": configid, "sim_conditions": cond}
    try:
        for mc in root.iter("motorconfiguration"):
            if mc.get("configid") == configid:
                for s in mc.findall("stage"):
                    if s.get("active") != "true":
                        notes.append(f"stage number {s.get('number')} is inactive in "
                                     f"configuration {str(configid)[:8]}; "
                                     f"builder activates all")
                break

        sc = rocket.find("subcomponents")
        stage_els = [c for c in sc if c.tag == "stage"] if sc is not None else []
        if not stage_els:
            raise Unsupported("rocket has no stages")
        if len(stage_els) > 3:
            raise Unsupported(f"{len(stage_els)} stages; schema max is 3")

        stages = []
        x = 0.0
        prev_aft = None
        for i, st_el in enumerate(stage_els):
            st, st_len, prev_aft = _build_stage(st_el, i, len(stage_els), x,
                                              configid, notes, prev_aft)
            stages.append(st)
            x += st_len

        _fix_diameter_chain(stages, notes)

        design = {"name": (_t(rocket, "name") or Path(file_key).stem)[:60],
                  "stages": stages}
        d = parse_design(design)
        design = d.model_dump(mode="json")
        result = {"status": "ok", "design": design, "notes": notes, **common}

        if use_or_masses:
            from scripts.or_headless import _helper
            orh = _helper()
            if str(resolved).endswith(".ork") and Path(resolved).exists():
                doc_orig = orh.load_doc(str(resolved))
            else:
                doc_orig = _or_temp_doc(orh, root)
            apply_or_mass_correction(result, doc_orig, notes)
            try:
                parse_design(result["design"])
            except Exception as e:
                notes.append(f"design failed validation after mass correction: {e}; "
                             f"reverted to uncorrected design")
                result["design"] = d.model_dump(mode="json")
        return result
    except Unsupported as e:
        return {"status": "unsupported", "reason": str(e), "design": None,
                "notes": notes, **common}
    except Exception as e:
        return {"status": "convert_error", "error": f"{type(e).__name__}: {e}",
                "design": None, "notes": notes, **common}
