#!/usr/bin/env python3
"""Parse .orc XMLs (dimensions, material densities, masses) + motors.db.gz into data/catalog.sqlite.

Tables:
  parts(id, source_file, manufacturer, part_number, description, comp_type,
        material, material_type, density, density_unit,
        dims_json, mass_g, validated)
  motors(id, designation, manufacturer, diameter_mm, length_mm,
         total_impulse_ns, avg_thrust_n, max_thrust_n, burn_time_s,
         prop_weight_g, total_weight_g, impulse_class, mtype)
"""
import gzip
import json
import shutil
import sqlite3
import tempfile
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
ORC_DIR = RAW / "orc"
DB_OUT = ROOT / "data" / "catalog.sqlite"

MASS_TO_G = {"g": 1.0, "kg": 1000.0, "oz": 28.349523125, "lb": 453.59237}
LEN_TO_MM = {"mm": 1.0, "cm": 10.0, "m": 1000.0, "in": 25.4, "ft": 304.8}
# density units seen: kg/m3, g/cm3, lb/ft3 (BULK); kg/m2, g/m2, oz/in2 (SURFACE); kg/m, g/m, oz/ft (LINE)
DENSITY_TO_SI = {  # -> (si_unit, factor)
    "kg/m3": ("kg/m3", 1.0), "g/cm3": ("kg/m3", 1000.0), "lb/ft3": ("kg/m3", 16.018463),
    "kg/m2": ("kg/m2", 1.0), "g/m2": ("kg/m2", 0.001), "oz/in2": ("kg/m2", 43.94185),
    "kg/m": ("kg/m", 1.0), "g/m": ("kg/m", 0.001), "oz/ft": ("kg/m", 0.092903),
}

META_TAGS = {"Manufacturer", "PartNumber", "Description", "Material", "Mass",
             "Shape", "Filled", "DragCoefficient", "Sides", "LineCount"}

def to_g(value, unit):
    if value is None: return None
    f = MASS_TO_G.get((unit or "g").strip())
    return float(value) * f if f else None

def parse_orc_file(path: Path):
    root = ET.parse(path).getroot()
    # material lookup within same file
    mat_db = {}
    for m in root.findall(".//Material"):
        name = (m.findtext("Name") or "").strip()
        try: dens = float((m.findtext("Density") or "").strip())
        except: dens = None
        mat_db[name] = (dens, m.findtext("Type"), m.get("UnitsOfMeasure"))
    comps = root.find("Components")
    if comps is None: return []
    out = []
    for e in list(comps):
        mat_el = e.find("Material")
        mat_name = (mat_el.text or "").strip() if mat_el is not None and mat_el.text else ""
        mat_type = mat_el.get("Type") if mat_el is not None else None
        dens, _, dens_uom = mat_db.get(mat_name, (None, None, None))
        dims = {}
        for ch in list(e):
            if ch.tag in META_TAGS: continue
            dims[ch.tag] = {"value": (ch.text or "").strip(), "unit": ch.get("Unit")}
        mass_el = e.find("Mass")
        mass_g = None
        if mass_el is not None and (mass_el.text or "").strip():
            try: mass_g = to_g(float(mass_el.text.strip()), mass_el.get("Unit"))
            except: pass
        out.append({
            "source_file": path.name,
            "manufacturer": e.findtext("Manufacturer") or "",
            "part_number": e.findtext("PartNumber") or "",
            "description": e.findtext("Description") or "",
            "comp_type": e.tag,
            "material": mat_name, "material_type": mat_type,
            "density": dens, "density_unit": dens_uom,
            "dims_json": json.dumps(dims),
            "mass_g": mass_g,
        })
    return out

def main():
    if not ORC_DIR.exists() or not list(ORC_DIR.glob("*.orc")) + list(ORC_DIR.glob("*.ORC")):
        raise SystemExit(f"no .orc files in {ORC_DIR} — run scripts/fetch_raw_data.py first")
    DB_OUT.parent.mkdir(parents=True, exist_ok=True)
    if DB_OUT.exists(): DB_OUT.unlink()
    con = sqlite3.connect(DB_OUT)
    con.execute("""CREATE TABLE parts(
      id INTEGER PRIMARY KEY, source_file TEXT, manufacturer TEXT, part_number TEXT,
      description TEXT, comp_type TEXT, material TEXT, material_type TEXT,
      density REAL, density_unit TEXT, dims_json TEXT, mass_g REAL, validated INTEGER)""")
    con.execute("""CREATE TABLE motors(
      id INTEGER PRIMARY KEY, designation TEXT, manufacturer TEXT,
      diameter_mm REAL, length_mm REAL, total_impulse_ns REAL, avg_thrust_n REAL,
      max_thrust_n REAL, burn_time_s REAL, prop_weight_g REAL, total_weight_g REAL,
      impulse_class TEXT, mtype TEXT)""")

    n_parts = 0
    for f in sorted(ORC_DIR.glob("*")):
        if not f.is_file() or f.suffix.lower() != ".orc": continue
        for p in parse_orc_file(f):
            has_dims = len(json.loads(p["dims_json"])) > 0
            has_mat = bool(p["material"]) and p["density"] is not None or p["mass_g"] is not None
            has_mfr = bool(p["manufacturer"])
            validated = 1 if (has_dims and has_mat and has_mfr) else 0
            con.execute("""INSERT INTO parts(source_file,manufacturer,part_number,description,
              comp_type,material,material_type,density,density_unit,dims_json,mass_g,validated)
              VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
              (p["source_file"], p["manufacturer"], p["part_number"], p["description"],
               p["comp_type"], p["material"], p["material_type"], p["density"],
               p["density_unit"], p["dims_json"], p["mass_g"], validated))
            n_parts += 1

    # motors: gunzip raw to temp, attach and copy
    gz = RAW / "motors.db.gz"
    if not gz.exists():
        raise SystemExit(f"missing {gz} — run scripts/fetch_raw_data.py first")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "motors.db"
        with gzip.open(gz, "rb") as fi, open(tmp, "wb") as fo:
            shutil.copyfileobj(fi, fo)
        src = sqlite3.connect(tmp)
        rows = list(src.execute("""SELECT m.designation, mf.name, m.diameter, m.length,
          m.total_impulse, m.avg_thrust, m.max_thrust, m.burn_time,
          m.propellant_weight, m.total_weight, m.impulse_class, m.type
          FROM motors m JOIN manufacturers mf ON mf.id=m.manufacturer_id"""))
        src.close()
    con.executemany("""INSERT INTO motors(designation,manufacturer,diameter_mm,length_mm,
      total_impulse_ns,avg_thrust_n,max_thrust_n,burn_time_s,prop_weight_g,total_weight_g,
      impulse_class,mtype) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", rows)

    con.execute("CREATE INDEX idx_parts_mfr ON parts(manufacturer)")
    con.execute("CREATE INDEX idx_parts_type ON parts(comp_type)")
    con.execute("CREATE INDEX idx_motors_desig ON motors(designation)")
    con.commit()
    vp = con.execute("SELECT COUNT(*) FROM parts WHERE validated=1").fetchone()[0]
    tp = con.execute("SELECT COUNT(*) FROM parts").fetchone()[0]
    tm = con.execute("SELECT COUNT(*) FROM motors").fetchone()[0]
    con.close()
    print(f"parts total={tp} validated={vp} | motors={tm} -> {DB_OUT}")
    if vp + tm < 150:
        raise SystemExit(f"FAIL: validated parts ({vp}) + motors ({tm}) < 150")
    print(f"OK: catalog.sqlite contains {vp}+{tm} = {vp+tm} >= 150 validated entries")

if __name__ == "__main__":
    main()
