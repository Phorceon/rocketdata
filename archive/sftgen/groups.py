"""Source-design grouping, dedup and split assignment (DATA_SPEC.md section 8).

Reads the old SFT file (new_results/sft_all.jsonl) only as a list of source
designs plus reference facts, resolves each row's source .ork in meta/ork/, merges
exact duplicates and renamed copies into one group, summarises what each design
is known to achieve, and assigns a deterministic train/val/test split per
design family.

    .venv/bin/python -m sftgen.groups      -> sftgen/out/groups.json
"""

from __future__ import annotations

import difflib
import hashlib
import io
import json
import re
import sqlite3
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SFT_ALL = ROOT / "new_results" / "sft_all.jsonl"
ORK_DIR = ROOT / "meta" / "ork"
CATALOG = ROOT / "data" / "catalog.sqlite"
OUT = Path(__file__).resolve().parent / "out" / "groups.json"

HASH_SUFFIX = re.compile(r"__[0-9a-f]{6}$")
DATE = re.compile(r"[ _\-]?\d{1,2}[.:\-_]\d{1,2}(?:[.:\-_]\d{2,4})?")
VERSION = re.compile(r"(?:[ _\-]?(?:v\d+(?:\.\d+)*|updated[\w ]*|final|copy|\(\d+\)|\[\d+\]))+$", re.I)
GENERIC_STEMS = {
    "rocket", "rockets", "estes", "simulation", "test", "openrocket", "design", "example",
    "final", "simple", "model", "three", "two", "tube", "base", "the", "mock", "demo",
    "starfire", "quest", "semroc", "aerotech", "dual", "deployable", "parallel", "pods",
    "clustered", "chute", "airstart", "baseline", "big",
}
CLASS_LETTERS = "ABCDEFGHIJKLMNOP"
CLASS_TOP_NS = {c: 2.5 * 2 ** i for i, c in enumerate(CLASS_LETTERS)}  # A: <=2.5, B: <=5, ...
MANUFACTURER_SHORT = {
    "Cesaroni Technology": "Cesaroni", "Loki Research": "Loki", "Animal Motor Works": "AMW",
    "Raketenmodellbau Klima": "Klima", "Apogee Components": "Apogee", "Public Missiles Ltd": "PML",
}


# --------------------------------------------------------------------------- io

def load_rows() -> list[dict]:
    with SFT_ALL.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def design_json(row: dict) -> dict:
    content = row["messages"][-1]["content"]
    m = re.search(r"<design>(.*?)</design>", content, re.S)
    return json.loads(m.group(1))


def read_ork_xml(path: Path) -> str:
    raw = path.read_bytes()
    if raw[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            name = next((n for n in z.namelist() if n.endswith((".ork", ".xml"))), z.namelist()[0])
            raw = z.read(name)
    elif raw[:2] == b"\x1f\x8b":
        import gzip
        raw = gzip.decompress(raw)
    return raw.decode("utf-8", "replace")


# ---------------------------------------------------------------- name handling

def base_name(file: str) -> str:
    """'meta/ork/APEX 30.08.2021__10a283.ork' -> 'APEX 30.08.2021'."""
    stem = Path(file).name
    stem = stem[:-4] if stem.lower().endswith(".ork") else stem
    return HASH_SUFFIX.sub("", stem)


def norm_name(file: str) -> str:
    """Folder, extension, hash tag, dates, version suffixes, case and punctuation stripped."""
    s = base_name(file)
    s = DATE.sub("", s)
    s = VERSION.sub("", s)
    s = re.sub(r"[^a-z0-9]+", "", s.lower())
    return s


def family_stem(file: str) -> str:
    """Leading word of the normalised name, used to keep near-variants in one split."""
    s = DATE.sub("", base_name(file))
    s = VERSION.sub("", s)
    s = re.sub(r"^\d+[ ._\-]*", "", s)
    words = re.findall(r"[A-Za-z]+", s)
    lead = words[0].lower() if words else ""
    if len(lead) >= 4 and lead not in GENERIC_STEMS:
        return lead
    tag = HASH_SUFFIX.search(Path(file).stem)
    return norm_name(file) + (tag.group(0) if tag else "")


def merge_typo_families(groups: list[dict]) -> None:
    """'sirius' and 'siruis' are one project: same letters or near-identical stems share a family."""
    stems = sorted({g["family"] for g in groups})
    canon = {s: s for s in stems}
    for i, a in enumerate(stems):
        for b in stems[i + 1:]:
            if len(a) >= 5 and len(b) >= 5 and "_" not in a + b and (
                sorted(a) == sorted(b) or difflib.SequenceMatcher(None, a, b).ratio() >= 0.85
            ):
                canon[b] = canon[a]
    for g in groups:
        g["family"] = canon[g["family"]]


def names_related(a: str, b: str) -> bool:
    na, nb = norm_name(a), norm_name(b)
    if na == nb or na.startswith(nb) or nb.startswith(na):
        return True
    return difflib.SequenceMatcher(None, na, nb).ratio() >= 0.75


def slug(file: str, taken: set[str]) -> str:
    name = base_name(file)
    tag = HASH_SUFFIX.search(Path(file).stem)
    s = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    m = re.match(r"^(\d+)_(.+)$", s)
    if m:
        s = f"{m.group(2)}_{m.group(1)}"
    s = "g_" + s[:48].strip("_")
    if s in taken and tag:
        s = f"{s}_{tag.group(0)[2:]}"
    n = 2
    base = s
    while s in taken:
        s = f"{base}_{n}"
        n += 1
    taken.add(s)
    return s


# ------------------------------------------------------------- ork resolution

def ork_index() -> dict[str, list[Path]]:
    idx: dict[str, list[Path]] = defaultdict(list)
    for p in sorted(ORK_DIR.iterdir()):
        if p.is_file() and p.suffix.lower() == ".ork":
            key = p.stem.replace(":", ".")
            idx[key].append(p)
            m = re.match(r"^(.*)_\d+$", key)
            if m:
                idx[m.group(1)].append(p)
    return idx


def stored_sims(xml: str) -> list[dict]:
    sims = []
    for m in re.finditer(r"<simulation\b.*?</simulation>", xml, re.S):
        block = m.group(0)
        name = re.search(r"<name>(.*?)</name>", block, re.S)
        cfg = re.search(r"<configid>(.*?)</configid>", block)
        fd = re.search(r"<flightdata ([^>]*)>", block)
        cond = {k: re.search(fr"<{k}>(.*?)</{k}>", block) for k in ("launchrodlength", "windaverage", "launchrodangle", "launchaltitude")}
        attrs = dict(re.findall(r'(\w+)="([^"]*)"', fd.group(1))) if fd else {}
        sims.append({
            "name": (name.group(1).strip() if name else ""),
            "configid": cfg.group(1) if cfg else None,
            "flightdata": {k: float(v) for k, v in attrs.items() if re.fullmatch(r"-?[\d.eE+\-]+", v)},
            "conditions": {k: float(v.group(1)) for k, v in cond.items() if v and re.fullmatch(r"-?[\d.eE+\-]+", v.group(1))},
        })
    return sims


def resolve_ork(file: str, sim_name: str | None, apogee: float | None, idx: dict[str, list[Path]]) -> tuple[Path | None, dict | None]:
    """Find the real ork/ file behind an sft_all name, preferring the stored sim matching the reference apogee."""
    direct = ROOT / file
    cands = [direct] if direct.exists() else list(dict.fromkeys(idx.get(base_name(file).replace(":", "."), [])))
    best: tuple[float, Path, dict] | None = None
    for p in cands:
        try:
            sims = stored_sims(read_ork_xml(p))
        except Exception:
            continue
        for s in sims:
            alt = s["flightdata"].get("maxaltitude")
            score = 0.0
            if apogee and alt:
                score += abs(alt - apogee) / max(apogee, 1.0)
            elif apogee:
                score += 1.0
            if sim_name and s["name"] != sim_name:
                score += 0.5
            if best is None or score < best[0]:
                best = (score, p, s)
    if best is None:
        return (cands[0] if len(cands) == 1 else None), None
    if best[0] > 0.02 and len(cands) > 1:
        return None, None
    return best[1], best[2]


# --------------------------------------------------------------- ork parsing

def _f(el: ET.Element | None, tag: str) -> float | None:
    if el is None:
        return None
    t = el.find(tag)
    try:
        return float(t.text) if t is not None and t.text else None
    except ValueError:
        return None


def cluster_count(tube: ET.Element) -> int:
    ic = tube.find("instancecount")
    if ic is not None and ic.text and ic.text.strip().isdigit():
        return max(1, int(ic.text.strip()))
    cc = tube.find("clusterconfiguration")
    if cc is not None and cc.text:
        name = cc.text.strip().lower()
        if name == "double":
            return 2
        m = re.match(r"(\d+)", name)
        if m:
            return int(m.group(1))
    return 1


def parse_ork_structure(xml: str, configid: str | None) -> dict:
    """Per-stage motors for one motor configuration, cluster counts and recovery devices."""
    root = ET.fromstring(xml)
    rocket = root.find("rocket")
    stages_out = []

    def walk(el: ET.Element, mult: int, stage: dict, in_pod: bool):
        for child in el:
            tag = child.tag
            if tag == "subcomponents":
                walk(child, mult, stage, in_pod)
                continue
            if tag in ("parallelstage", "podset"):
                n = int((_f(child, "instancecount") or 1))
                if tag == "parallelstage":
                    sub = {"name": (child.findtext("name") or "Booster").strip(), "kind": "parallel",
                           "motors": [], "recovery": [], "instances": n}
                    stages_out.append(sub)
                    walk(child, n, sub, True)
                else:
                    walk(child, mult * n, stage, True)
                continue
            if tag in ("parachute", "streamer"):
                event = (child.findtext("deployevent") or "").strip()
                if configid:
                    for dc in child.findall("deploymentconfiguration"):
                        if dc.get("configid") == configid and dc.findtext("deployevent"):
                            event = dc.findtext("deployevent").strip()
                stage["recovery"].append({
                    "type": tag, "event": event, "altitude_m": _f(child, "deployaltitude"),
                    "diameter_m": _f(child, "diameter"), "name": (child.findtext("name") or "").strip(),
                })
            mm = child.find("motormount")
            if mm is not None:
                chosen = None
                motors = mm.findall("motor")
                for mo in motors:
                    if configid and mo.get("configid") == configid:
                        chosen = mo
                if chosen is None and not configid and motors:
                    chosen = motors[0]
                if chosen is not None and (chosen.findtext("designation") or "").strip():
                    ign = (mm.findtext("ignitionevent") or "automatic").strip()
                    for ic in mm.findall("ignitionconfiguration"):
                        if ic.get("configid") == configid and ic.findtext("ignitionevent"):
                            ign = ic.findtext("ignitionevent").strip()
                    stage["motors"].append({
                        "designation": chosen.findtext("designation").strip(),
                        "manufacturer": (chosen.findtext("manufacturer") or "").strip(),
                        "diameter_m": _f(chosen, "diameter"),
                        "length_m": _f(chosen, "length"),
                        "count": cluster_count(child) * mult,
                        "ignition": ign,
                        "in_pod": in_pod,
                    })
            if tag not in ("motormount", "motor"):
                walk(child, mult, stage, in_pod)

    if rocket is not None:
        sub = rocket.find("subcomponents")
        for st in (sub if sub is not None else []):
            if st.tag != "stage":
                continue
            stage = {"name": (st.findtext("name") or "Stage").strip(), "kind": "axial", "motors": [], "recovery": []}
            stages_out.append(stage)
            walk(st, 1, stage, False)
    return {"stages": stages_out}


# ------------------------------------------------------------- motor catalog

def _mkey(designation: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", designation.upper())


def core_designation(designation: str) -> str:
    """'HP-I280DM' -> 'I280DM', '2546K300-P' -> 'K300', 'C6-5' -> 'C6', 'J-326-LR' -> 'J326LR'."""
    d = designation.strip()
    d = re.sub(r"^(HP|RMS|DMS)-", "", d, flags=re.I)
    m = re.match(r"^\d{2,6}-?([A-P]\d+.*)$", d)
    if m:
        d = m.group(1)
    d = re.sub(r"^([A-P])-(\d)", r"\1\2", d)
    d = re.sub(r"-\d+[A-Z]?$", "", d) if re.match(r"^[A-P]\d+[A-Z]*-\d+[A-Z]?$", d) else d
    return d


def load_catalog() -> dict[str, list[dict]]:
    cat: dict[str, list[dict]] = defaultdict(list)
    if not CATALOG.exists():
        return cat
    con = sqlite3.connect(CATALOG)
    for des, man, dia, tot, avg, cls in con.execute(
        "select designation, manufacturer, diameter_mm, total_impulse_ns, avg_thrust_n, impulse_class from motors"
    ):
        rec = {"designation": des, "manufacturer": man, "diameter_mm": dia, "total_impulse_ns": tot,
               "avg_thrust_n": avg, "class": cls}
        cat[_mkey(des)].append(rec)
        cat[_mkey(core_designation(des))].append(rec)
    return cat


def impulse_class(total_ns: float | None) -> str | None:
    if not total_ns or total_ns <= 0:
        return None
    for c in CLASS_LETTERS:
        if total_ns <= CLASS_TOP_NS[c] * 1.0001:
            return c
    return "P"


def class_of(designation: str) -> str | None:
    m = re.match(r"^([A-P])\d", core_designation(designation))
    return m.group(1) if m else None


# ------------------------------------------------------------- pinned motor DB

def _maker_canon(mfr: str) -> str:
    from sftgen import motors
    return motors._norm(motors._canonical_manufacturer(mfr) or mfr)


def _maker_known(mfr: str) -> bool:
    """Is the .ork manufacturer string recognisably a real commercial maker?"""
    from sftgen import motors
    n = _maker_canon(mfr)
    names = list(motors.MANUFACTURER_PREFERENCE) + list(MANUFACTURER_SHORT.values()) + ["Klima", "PML"]
    return any(n.startswith(k) or k.startswith(n) or n in k for k in {motors._norm(x) for x in names})


def _maker_matches(mfr: str, resolved_manufacturer: str) -> bool:
    n = _maker_canon(mfr)
    return n in resolved_manufacturer or resolved_manufacturer in n


def resolve_motor(designation: str, manufacturer: str | None) -> dict | None:
    """Pinned motor-DB entry for one .ork motor entry: canonical designation, or None.

    The .ork manufacturer string is used to disambiguate shared common names
    (e.g. 'G54-RL' is the Cesaroni '159G54-12A', not the AeroTech 'G54W'). When
    the hinted lookup fails but a bare lookup hits a different recognised maker,
    the .ork entry is treated as absent from the DB (returns None).
    """
    from sftgen import motors
    try:
        r = motors.resolve(designation, manufacturer)
    except LookupError:
        try:
            r = motors.resolve(designation)
        except LookupError:
            return None
        if (manufacturer and _maker_known(manufacturer)
                and not _maker_matches(manufacturer, motors._norm(r["manufacturer"]))):
            return None
    return {"manufacturer": r["manufacturer"], "designation": r["designation"],
            "total_impulse_ns": r["total_impulse_ns"], "diameter_m": r["diameter_m"]}


# ------------------------------------------------------------- old-trace facts

def trace_facts(row: dict) -> dict:
    c = row["messages"][-1]["content"]
    out: dict = {}
    m = re.search(r"- Motor\(s\): (.*)", c)
    motors = []
    if m:
        for part in m.group(1).split(";"):
            pm = re.match(r"\s*(?:(\d+)x )?(.+?)(?: \[(.+?)\])? \((\w)-class, Itot (\d+) N\*s, avg (\d+) N, burn ([\d.]+) s\)", part)
            if pm:
                motors.append({"count": int(pm.group(1) or 1), "designation": pm.group(2), "stage": pm.group(3),
                               "class": pm.group(4), "itot_ns": float(pm.group(5)), "avg_n": float(pm.group(6)),
                               "burn_s": float(pm.group(7))})
    out["motors"] = motors
    for key, pat in {
        "max_body_od_mm": r"max body OD ([\d.]+) mm",
        "liftoff_mass_kg": r"m0 (?:~)?= ([\d.]+) kg",
        "static_margin_cal": r"static margin (?:estimate )?= (?:\([^)]*\) / [\d.]+ ~?= )?(-?[\d.]+) cal",
        "rail_exit_ms": r"rail-exit speed ([\d.]+) m/s",
        "thrust_to_weight": r"thrust-to-weight = .*?= ([\d.]+):1",
    }.items():
        mm = re.search(pat, c)
        if mm:
            out[key] = float(mm.group(1))
    out["dual_deploy_line"] = bool(re.search(r"^- Dual deploy:", c, re.M))
    out["no_recovery_line"] = "No deployable recovery device" in c
    return out


def design_facts(d: dict) -> dict:
    max_d = 0.0
    payload = 0.0
    fins = 0
    devices = []

    def walk(cs, in_pod=False):
        nonlocal max_d, payload, fins
        for c in cs:
            t = c.get("type")
            if t == "pod_set":
                walk(c.get("contains", []), True)
                continue
            if not in_pod:
                if t == "bodytube" and c.get("outer_d_m"):
                    max_d = max(max_d, float(c["outer_d_m"]))
                if t == "nosecone" and c.get("base_radius_m"):
                    max_d = max(max_d, 2 * float(c["base_radius_m"]))
                if t == "transition":
                    max_d = max(max_d, float(c.get("fore_d_m") or 0), float(c.get("aft_d_m") or 0))
            if t == "masscomponent" and re.search(r"payload|egg|altimeter payload|cargo", c.get("name", ""), re.I):
                payload += float(c.get("mass_kg") or 0)
            if t in ("trapezoidfin", "freeformfinset", "ellipticalfin", "tubefin"):
                fins += 1
            if t in ("parachute", "streamer"):
                devices.append({"type": t, "event": c.get("deploy_event")})
            walk(c.get("contains", []), in_pod)

    walk(d.get("components", []))
    return {"max_body_diameter_m": round(max_d, 4) if max_d else None,
            "payload_mass_kg": round(payload, 3) if payload else 0.0, "fin_sets": fins, "devices": devices}


# ------------------------------------------------------------- reference

def recovery_guess(stages: list[dict], tf: dict, dfacts: dict) -> str:
    devices = [r for s in stages for r in s["recovery"] if r["event"] not in ("never", "")]
    if not stages or not any(s["recovery"] for s in stages):
        devices = [{"type": d["type"], "event": d.get("event") or ""} for d in dfacts["devices"] if d.get("event") != "never"]
    if not devices or tf.get("no_recovery_line"):
        return "none"
    top = stages[0]["recovery"] if stages and stages[0]["recovery"] else devices
    top = [r for r in top if r.get("event") not in ("never", "")] or devices
    events = {r.get("event") for r in top}
    if tf.get("dual_deploy_line") or ("altitude" in events and len(top) >= 2):
        return "dual_deploy"
    if all(r["type"] == "streamer" for r in top):
        return "streamer"
    return "single_chute"


def build_reference(row: dict, all_rows: list[dict], ork_path: Path | None, sim: dict | None, cat) -> dict:
    d = design_json(row)
    tf = trace_facts(row)
    df = design_facts(d)
    stages = []
    if ork_path is not None and sim is not None:
        try:
            stages = parse_ork_structure(read_ork_xml(ork_path), sim["configid"])["stages"]
        except ET.ParseError:
            stages = []
    powered = [s for s in stages if s["motors"]]

    # Firing order: parallel boosters and the bottom axial stage first, sustainer last.
    firing = [s for s in powered if s["kind"] == "parallel"] + [s for s in reversed(powered) if s["kind"] == "axial"]
    motors_by_stage = []
    flat: list[str] = []
    for s in firing:
        ms = []
        for m in s["motors"]:
            rec = cat.get(_mkey(m["designation"])) or cat.get(_mkey(core_designation(m["designation"])))
            tot = rec[0]["total_impulse_ns"] if rec else None
            avg = rec[0]["avg_thrust_n"] if rec else None
            tm = next((t for t in tf["motors"] if _mkey(t["designation"]) == _mkey(m["designation"])), None)
            trace_ok = bool(tm and tm["class"] == class_of(m["designation"]))
            if tot is None and trace_ok:
                tot = tm["itot_ns"]
            if avg is None and trace_ok:
                avg = tm["avg_n"]
            if tot is None:
                lead = re.match(r"^(\d{3,6})[A-P]\d", m["designation"])
                tot = float(lead.group(1)) if lead else None
            ms.append({
                "designation": m["designation"], "core": core_designation(m["designation"]),
                "manufacturer": MANUFACTURER_SHORT.get(m["manufacturer"], m["manufacturer"]),
                "count": m["count"], "diameter_m": m["diameter_m"], "class": class_of(m["designation"]),
                "total_impulse_ns": round(tot, 1) if tot else None,
                "avg_thrust_n": round(avg, 1) if avg else None, "in_catalog": bool(rec),
                "ignition": m["ignition"],
            })
            flat += [m["designation"]] * m["count"]
        motors_by_stage.append({"stage": s["name"], "kind": s["kind"], "motors": ms})

    if not motors_by_stage:  # no resolvable .ork: fall back to the flight block / trace
        fm = d["flight"].get("motor")
        names = fm if isinstance(fm, list) else [x.strip() for x in str(fm).split(",") if x.strip()]
        ms = []
        for n in names:
            tm = next((t for t in tf["motors"] if _mkey(t["designation"]) == _mkey(n)), None)
            rec = cat.get(_mkey(n)) or cat.get(_mkey(core_designation(n)))
            cnt = tm["count"] if tm else 1
            tot = rec[0]["total_impulse_ns"] if rec else (tm["itot_ns"] if tm else None)
            avg = rec[0]["avg_thrust_n"] if rec else (tm["avg_n"] if tm else None)
            man = rec[0]["manufacturer"] if rec else ""
            ms.append({"designation": n, "core": core_designation(n),
                       "manufacturer": MANUFACTURER_SHORT.get(man, man), "count": cnt,
                       "diameter_m": (rec[0]["diameter_mm"] / 1000 if rec and rec[0]["diameter_mm"] else None),
                       "class": class_of(n), "total_impulse_ns": tot, "avg_thrust_n": avg,
                       "in_catalog": bool(rec), "ignition": "automatic"})
            flat += [n] * cnt
        motors_by_stage = [{"stage": "Sustainer", "kind": "axial", "motors": ms}]

    all_m = [m for s in motors_by_stage for m in s["motors"]]
    total = sum((m["total_impulse_ns"] or 0) * m["count"] for m in all_m) or None
    axial_powered = [s for s in motors_by_stage if s["kind"] == "axial"]

    # Pinned-DB truth for each motor instance, same firing order as "motors" (count-expanded);
    # None when the .ork entry has no entry in the pinned motor database.
    motors_resolved = []
    for s in motors_by_stage:
        for m in s["motors"]:
            motors_resolved += [resolve_motor(m["designation"], m["manufacturer"])] * m["count"]

    # Reference outputs: max non-null over the file's old rows, else the stored sim.
    rows = [r for r in all_rows if r["file"] == row["file"]]

    def pick(key, fd_key):
        vals = [r["targets"].get(key) for r in rows if isinstance(r["targets"].get(key), (int, float))]
        if vals:
            return float(vals[0])
        if sim and fd_key in sim["flightdata"]:
            return float(sim["flightdata"][fd_key])
        return None

    ref = {
        "motors": flat,
        "motors_resolved": motors_resolved,
        "motors_by_stage": motors_by_stage,
        "motor_count": len(flat),
        "stage_count": max(1, len(axial_powered)),
        "airframe_sections": max(1, sum(1 for x in d["components"] if x.get("type") == "stage_marker")),
        "parallel_boosters": any(s["kind"] == "parallel" for s in motors_by_stage),
        "cluster": any(m["count"] > 1 for m in all_m) or len(all_m) > len(motors_by_stage),
        "max_body_diameter_m": df["max_body_diameter_m"],
        "motor_diameters_m": sorted({round(m["diameter_m"], 3) for m in all_m if m["diameter_m"]}),
        "recovery": recovery_guess(stages, tf, df),
        "apogee_m": pick("apogee_m", "maxaltitude"),
        "time_to_apogee_s": pick("time_to_apogee_s", "timetoapogee"),
        "flight_time_s": pick("flight_time_s", "flighttime"),
        "ground_hit_ms": pick("ground_hit_ms", "groundhitvelocity"),
        "motor_classes": sorted({m["class"] for m in all_m if m["class"]}),
        "max_motor_class": max((m["class"] for m in all_m if m["class"]), default=None),
        "total_impulse_ns": round(total, 1) if total else None,
        "total_impulse_class": impulse_class(total),
        "all_motors_in_catalog": all(m["in_catalog"] for m in all_m),
        "payload_mass_kg": df["payload_mass_kg"],
        "liftoff_mass_kg": tf.get("liftoff_mass_kg"),
        "static_margin_cal": tf.get("static_margin_cal"),
        "rail_exit_ms": (sim["flightdata"].get("launchrodvelocity") if sim else None) or tf.get("rail_exit_ms"),
        "stored_sim": ({"name": sim["name"], **{k: sim["conditions"][k] for k in sim["conditions"]}} if sim else None),
        "design_source": row.get("design_source"),
    }
    if ref["apogee_m"] is None and ref["ground_hit_ms"] is None and sim:
        ref["ground_hit_ms"] = sim["flightdata"].get("groundhitvelocity")
    ref["quality"] = reference_quality(ref)
    return ref


def reference_quality(ref: dict) -> list[str]:
    """Flags that limit which prompt types the reference can back up."""
    q = []
    if ref["apogee_m"] is None:
        q.append("no_apogee")
    elif ref["apogee_m"] < 60:
        q.append("apogee_implausibly_low")
    if not ref["all_motors_in_catalog"]:
        q.append("motor_not_in_catalog")
    for s in ref["motors_by_stage"]:
        for m in s["motors"]:
            if m["class"] is None:
                q.append("custom_motor")
            elif m["total_impulse_ns"] and impulse_class(m["total_impulse_ns"]) not in (m["class"], None):
                q.append("motor_impulse_mismatch")
    if ref["static_margin_cal"] is not None and ref["static_margin_cal"] <= 0:
        q.append("reference_unstable")
    if ref["recovery"] == "none":
        q.append("no_recovery")
    return sorted(set(q))


# ------------------------------------------------------------- grouping

def sim_signature(row: dict) -> tuple | None:
    t = row["targets"]
    sig = (t.get("apogee_m"), t.get("max_velocity_ms"), t.get("flight_time_s"))
    return sig if all(isinstance(x, (int, float)) for x in sig) else None


def build_groups() -> dict:
    rows = load_rows()
    by_file: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_file[r["file"]].append(r)

    # Exact duplicate rows: identical messages, regardless of file name.
    seen_msgs: dict[str, dict] = {}
    exact_dups = []
    for r in rows:
        key = json.dumps(r["messages"], sort_keys=True)
        if key in seen_msgs:
            exact_dups.append({"dropped": r["id"], "file": r["file"], "duplicate_of": seen_msgs[key]["id"],
                               "duplicate_of_file": seen_msgs[key]["file"]})
        else:
            seen_msgs[key] = r

    files = sorted(by_file)
    first = {f: by_file[f][0] for f in files}
    sigs = {f: next((sim_signature(r) for r in by_file[f] if sim_signature(r)), None) for f in files}
    designs = {f: json.dumps(design_json(first[f]), sort_keys=True) for f in files}

    parent = {f: f for f in files}

    def find(f):
        while parent[f] != f:
            parent[f] = parent[parent[f]]
            f = parent[f]
        return f

    merges = []
    near_misses = []
    for i, a in enumerate(files):
        for b in files[i + 1:]:
            same_design = designs[a] == designs[b]
            same_sig = sigs[a] is not None and sigs[a] == sigs[b]
            related = names_related(a, b)
            if same_design or (same_sig and related):
                why = []
                if same_design:
                    why.append("identical design JSON")
                if same_sig:
                    why.append("identical stored sim outputs (apogee %.1f m, max velocity %.1f m/s, flight time %.1f s)" % sigs[a])
                if related:
                    why.append(f"related names ('{norm_name(a)}' ~ '{norm_name(b)}')")
                if not same_design:
                    import difflib as _dl
                    A = json.dumps(json.loads(designs[a]), indent=0, sort_keys=True).splitlines()
                    B = json.dumps(json.loads(designs[b]), indent=0, sort_keys=True).splitlines()
                    n = sum(1 for l in _dl.unified_diff(A, B, lineterm="", n=0) if l[:1] in "+-" and l[:3] not in ("+++", "---"))
                    why.append(f"design JSON differs in {n} lines (edited copy; its stored sim was not re-run)")
                merges.append({"a": a, "b": b, "reason": "; ".join(why)})
                parent[find(b)] = find(a)
            elif any(ra["prompt_text"] == rb["prompt_text"] for ra in by_file[a] for rb in by_file[b]):
                near_misses.append({"a": a, "b": b, "reason": "share one rounded old prompt but sim outputs differ "
                                    f"({sigs[a]} vs {sigs[b]}); kept as separate designs"})

    clusters: dict[str, list[str]] = defaultdict(list)
    for f in files:
        clusters[find(f)].append(f)

    idx = ork_index()
    cat = load_catalog()
    taken: set[str] = set()
    groups = []
    for rep, members in sorted(clusters.items(), key=lambda kv: kv[0].lower()):
        members = sorted(members, key=lambda f: (len(base_name(f)), f))
        rep = members[0]
        row = first[rep]
        resolved = {}
        ref_sim = None
        ref_path = None
        for f in members:
            apo = next((r["targets"].get("apogee_m") for r in by_file[f] if r["targets"].get("apogee_m")), None)
            p, s = resolve_ork(f, first[f].get("sim"), apo, idx)
            resolved[f] = str(p.relative_to(ROOT)) if p else None
            if f == rep:
                ref_path, ref_sim = p, s
        ref = build_reference(row, rows, ref_path, ref_sim, cat)
        groups.append({
            "group_id": slug(rep, taken),
            "family": family_stem(rep),
            "members": members,
            "ork_paths": resolved,
            "row_ids": sorted(r["id"] for f in members for r in by_file[f]),
            "reference": ref,
        })

    # Renamed copies inside ork/ that sft_all never used: same <rocket> XML as a resolved member.
    rocket_hash = {}
    for p in sorted(ORK_DIR.iterdir()):
        if p.is_file() and p.suffix.lower() == ".ork":
            try:
                x = read_ork_xml(p)
            except Exception:
                continue
            i, j = x.find("<rocket>"), x.find("<simulations>")
            rocket_hash[str(p.relative_to(ROOT))] = hashlib.md5(x[i:j].encode()).hexdigest() if i >= 0 else None
    by_hash = defaultdict(list)
    for k, h in rocket_hash.items():
        if h:
            by_hash[h].append(k)
    for g in groups:
        extra = set()
        for p in g["ork_paths"].values():
            if p and rocket_hash.get(p):
                extra |= set(by_hash[rocket_hash[p]]) - {p}
        g["unused_ork_copies"] = sorted(extra)

    merge_typo_families(groups)
    assign_splits(groups)
    return {
        "source": str(SFT_ALL.relative_to(ROOT)),
        "n_rows": len(rows),
        "n_files": len(files),
        "n_groups": len(groups),
        "exact_duplicate_rows": exact_dups,
        "merged_copies": merges,
        "checked_not_merged": near_misses,
        "groups": groups,
    }


# ------------------------------------------------------------- splits

def _h(s: str) -> float:
    return int(hashlib.sha256(s.encode()).hexdigest()[:12], 16) / 16 ** 12


def stratum(ref: dict) -> str:
    if ref["stage_count"] > 1:
        return "multistage"
    if ref["motor_count"] > 1:
        return "cluster"
    return "single"


def assign_splits(groups: list[dict], val_frac: float = 0.10, test_frac: float = 0.10) -> None:
    """Split per family (near-variants together), stratified by multistage / cluster / single."""
    fam_groups: dict[str, list[dict]] = defaultdict(list)
    for g in groups:
        fam_groups[g["family"]].append(g)
    order = {"multistage": 0, "cluster": 1, "single": 2}
    fam_stratum = {f: min((stratum(g["reference"]) for g in gs), key=order.get) for f, gs in fam_groups.items()}
    for st in order:
        fams = sorted((f for f in fam_groups if fam_stratum[f] == st), key=lambda f: _h("split:" + f))
        n = sum(len(fam_groups[f]) for f in fams)
        need = {"test": max(1, round(n * test_frac)) if n >= 3 else 0,
                "val": max(1, round(n * val_frac)) if n >= 3 else 0}
        got = {"test": 0, "val": 0}
        for f in fams:
            size = len(fam_groups[f])
            split = "train"
            for s in ("test", "val"):
                if got[s] < need[s] and got[s] + size <= need[s] + (1 if need[s] >= 3 else 0) and size <= 2:
                    split = s
                    got[s] += size
                    break
            for g in fam_groups[f]:
                g["split"] = split
                g["stratum"] = st


def main() -> None:
    data = build_groups()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    from collections import Counter
    print(f"{data['n_rows']} rows, {data['n_files']} files -> {data['n_groups']} groups")
    print(f"exact duplicate rows: {len(data['exact_duplicate_rows'])}; merged copies: {len(data['merged_copies'])}")
    print("splits:", Counter(g["split"] for g in data["groups"]))
    print("split x stratum:", Counter((g["split"], g["stratum"]) for g in data["groups"]))
    print("unresolved ork:", sum(1 for g in data["groups"] for v in g["ork_paths"].values() if v is None))
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
