"""Chain the model's design through CadQuery AND OpenRocket.

    .venv/bin/python scripts/chain_design.py model_out/results_val.json
    .venv/bin/python scripts/chain_design.py answer.txt              # one model answer

For every model answer (v5 format: an OpenRocket tree written as JSON):
  1. CAD:  scripts/json_to_cad.py builds it with CadQuery (STEP + STL), and we check no
           body tube / fin set was dropped on the way
  2. .ork: the same tree is written back out as an OpenRocket .ork file (XML). If the model
           gave no <simulations> block, a default launch (1 m rail, 2 m/s wind) is added
  3. fly:  scripts/or_batch/OrBatch.java flies the .ork in OpenRocket 24.12 with the same
           fixed seeds as the rest of the project (seed 42, UUID seed 42, one warm-up run).
           If OpenRocket aborts (no motor, never ignites, ...) the reason string is shown in
           the table and summary.json; .ork load warnings (e.g. "no motor with designation
           found") are saved as sim["load_warnings"]

Writes model_out/chain/<id>.ork, model_out/chain/<id>/ (CAD files) and
model_out/chain/summary.json, and prints one line per design plus totals.
Needs: CadQuery in .venv, a JDK (javac/java on PATH) and lib/OpenRocket.jar
(gitignored - created by scripts/fetch_openrocket.sh).
"""
import argparse
import collections
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import json_to_cad as j2c  # noqa: E402  (parse_design_text / normalise / design_to_cad)

SIM_NAME = "chain"
DEFAULT_CONDITIONS = [  # used only when the model wrote no <simulations> block
    ("launchrodlength", "1.0"), ("launchrodangle", "0.0"), ("launchroddirection", "90.0"),
    ("windaverage", "2.0"), ("windturbulence", "0.1"), ("launchaltitude", "0.0"),
    ("launchlatitude", "28.61"), ("launchlongitude", "-80.6"), ("geodeticmethod", "spherical"),
    ("timestep", "0.05"),
]
BODY = {"nosecone", "bodytube", "transition"}
FINS = {"trapezoidfinset", "freeformfinset", "ellipticalfinset", "tubefinset"}
V2_FINS = {"trapezoidfin", "freeformfinset", "ellipticalfin", "tubefin"}


# ----------------------------------------------------------------------------- tree -> .ork
def _fmt(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


def _kids(body):
    ch = (body.get("children") or []) if isinstance(body, dict) else []
    if isinstance(ch, dict):
        ch = [{k: v} for k, v in ch.items()]
    for c in ch:
        if isinstance(c, dict):
            yield from c.items()


def tree_to_xml(tag, body):
    """One node of the v5 JSON tree -> an XML element: {"attrs":{..}, "value":.., "children":[{tag: node}]}."""
    el = ET.Element(tag)
    if isinstance(body, dict):
        for k, v in (body.get("attrs") or {}).items():
            el.set(k, _fmt(v))
        if body.get("value") is not None:
            el.text = _fmt(body["value"])
        for k, v in _kids(body):
            el.append(tree_to_xml(k, v))
    elif body is not None:
        el.text = _fmt(body)
    return el


# v5 IR bookkeeping tags that OpenRocket's .ork format does not know. tree_to_xml would write
# them and OpenRocket logs "Unknown text in element ..." for every one on every load.
ORK_ONLY_DROP = {"motor_id"}


def _drop_ir_only_tags(parent):
    for child in list(parent):
        if child.tag in ORK_ONLY_DROP:
            parent.remove(child)
        else:
            _drop_ir_only_tags(child)


def design_to_ork(raw, path):
    """Write the model's v5 tree as an .ork file with exactly one simulation called SIM_NAME.
    v5-only tags that the .ork format does not know (ORK_ONLY_DROP) are dropped.
    Returns a list of notes (e.g. 'no simulations block, default launch added')."""
    notes = []
    root = tree_to_xml("openrocket", raw["openrocket"])
    _drop_ir_only_tags(root)
    root.set("version", root.get("version") or "1.8")
    root.set("creator", "rocketdata chain_design.py")
    rocket = root.find("rocket")
    if rocket is None:
        raise ValueError("design has no <rocket>")
    mc = rocket.find("motorconfiguration")
    configid = mc.get("configid") if mc is not None and mc.get("configid") else None
    sims = root.find("simulations")
    sim = sims.find("simulation") if sims is not None else None
    if sim is None:
        notes.append("no <simulations> in the design: default launch added (1 m rail, 2 m/s wind)")
        if sims is None:
            sims = ET.SubElement(root, "simulations")
        sim = ET.SubElement(sims, "simulation")
        ET.SubElement(sim, "simulator").text = "RK4Simulator"
        ET.SubElement(sim, "calculator").text = "BarrowmanCalculator"
        cond = ET.SubElement(sim, "conditions")
        if configid:
            ET.SubElement(cond, "configid").text = configid
        for k, v in DEFAULT_CONDITIONS:
            ET.SubElement(cond, k).text = v
        ET.SubElement(cond, "atmosphere").set("model", "isa")
    for extra in list(sims)[1:]:  # keep only the first simulation
        sims.remove(extra)
    sim.set("status", "outdated")
    name = sim.find("name")
    if name is None:
        name = ET.Element("name")
        sim.insert(0, name)
    name.text = SIM_NAME
    cond = sim.find("conditions")
    if cond is not None and cond.find("configid") is None and configid:
        ET.SubElement(cond, "configid").text = configid
    if configid is None:
        notes.append("design has no <motorconfiguration>: OpenRocket will fly it with no motor selected")
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
    return notes


# ----------------------------------------------------------------------------- OpenRocket
def fly_all(ork_paths, jar):
    """Fly every .ork once (after a warm-up run) in one JVM. Returns {path: result dict}."""
    src = os.path.join(HERE, "or_batch", "OrBatch.java")
    with tempfile.TemporaryDirectory() as classes:
        subprocess.run(["javac", "--release", "17", "-nowarn", "-cp", jar, "-d", classes, src],
                       check=True, capture_output=True)
        lines = "".join(f"{p}\t{SIM_NAME}\t42\t2\t42\n" for p in ork_paths)
        env = dict(os.environ, LC_ALL="C.UTF-8", LANG="C.UTF-8")
        p = subprocess.run(["java", "-Dsun.jnu.encoding=UTF-8", "-Dfile.encoding=UTF-8",
                            "-Djava.awt.headless=true", "-cp", jar + os.pathsep + classes, "OrBatch"],
                           input=lines, capture_output=True, text=True, encoding="utf-8", env=env, cwd=REPO)
    out = {}
    for line in p.stdout.splitlines():
        if line.strip().startswith("{"):
            r = json.loads(line)
            if r.get("rep") == 1:  # rep 0 is the warm-up run
                out[r["file"]] = r
    if not out and p.returncode:
        raise RuntimeError("OrBatch failed:\n" + p.stderr[-2000:])
    return out


# ----------------------------------------------------------------------------- CAD
def count_model_parts(tag, body, acc):
    if tag in BODY:
        acc["body"] += 1
    if tag in FINS:
        acc["fins"] += 1
    for k, v in _kids(body):
        count_model_parts(k, v, acc)


def count_built_parts(items, acc, in_stage=False):
    for c in items:
        t = c.get("type")
        if t in BODY:
            acc["body"] += 1
        if t in V2_FINS and not in_stage:
            acc["fins"] += 1
        count_built_parts(c.get("contains", []), acc, t == "stage_marker")


def build_cad(raw, out_dir, name):
    design = j2c.normalise(raw)
    rep = j2c.design_to_cad(design, out_dir, name)
    m, b = {"body": 0, "fins": 0}, {"body": 0, "fins": 0}
    count_model_parts("openrocket", raw["openrocket"], m)
    count_built_parts(design.get("components", []), b)
    lost = (f"model wrote {m['body']} body parts + {m['fins']} fin sets, CAD has {b['body']} + {b['fins']}"
            if b["body"] < m["body"] or b["fins"] < m["fins"] else None)
    return {"parts": rep["parts"], "length_mm": rep["length_mm"], "lost": lost, "warnings": rep["warnings"]}


# ----------------------------------------------------------------------------- main
def load_answers(path):
    if path.endswith(".json"):
        data = json.load(open(path, encoding="utf-8"))
        rows = data["results"] if isinstance(data, dict) else data
        return [(str(r.get("id", i)), r.get("content") or "") for i, r in enumerate(rows)]
    return [(os.path.splitext(os.path.basename(path))[0], open(path, encoding="utf-8").read())]


def fin(x, d=1):
    return f"{x:.{d}f}" if isinstance(x, (int, float)) and math.isfinite(x) else "-"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("answers", help="results_<label>.json from sft/eval_test.py, or one answer .txt")
    ap.add_argument("--out", default="model_out/chain")
    ap.add_argument("--jar", default=os.path.join(REPO, "lib", "OpenRocket.jar"),
                    help="OpenRocket jar (default lib/OpenRocket.jar, gitignored - scripts/fetch_openrocket.sh)")
    ap.add_argument("--no-cad", action="store_true", help="skip CadQuery (OpenRocket half only)")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    if not os.path.isfile(a.jar):
        ap.error(f"--jar not found: {a.jar}  (pass --jar or run scripts/fetch_openrocket.sh)")

    answers = load_answers(a.answers)
    if a.limit:
        answers = answers[:a.limit]
    out = os.path.abspath(a.out)
    if os.path.isdir(out):
        print(f"removing existing out dir {out}")
        shutil.rmtree(out)
    os.makedirs(out)

    rows, orks = [], []
    for rid, text in answers:
        name = j2c.safe(rid)
        row = {"id": rid}
        try:
            raw = j2c.parse_design_text(text)
            if "openrocket" not in raw:
                raise ValueError("not a v5 (OpenRocket tree) design")
        except Exception as e:
            row.update(stage="parse", error=f"{type(e).__name__}: {e}")
            rows.append(row)
            continue
        if not a.no_cad:
            try:
                row["cad"] = build_cad(raw, os.path.join(out, name), name)
            except Exception as e:
                row["cad"] = {"error": f"{type(e).__name__}: {e}"}
        ork = os.path.join(out, name + ".ork")
        try:
            row["ork_notes"] = design_to_ork(raw, ork)
            orks.append(ork)
            row["ork"] = ork
        except Exception as e:
            row.update(stage="ork", error=f"{type(e).__name__}: {e}")
        rows.append(row)

    flights = fly_all(orks, a.jar) if orks else {}
    for row in rows:
        if "ork" not in row:
            continue
        f = flights.get(row["ork"])
        if f is None:
            row["sim"] = {"error": "no result from OpenRocket"}
        elif "error" in f:
            row["sim"] = {"error": f["error"]}
        else:
            ev = [e for e in f.get("events", []) if e["branch"] == 0]
            types = [e["type"] for e in ev]
            abort = next((e["data"] for e in f.get("events", [])
                          if e["type"] == "SIM_ABORT" and e.get("data")), None)
            row["sim"] = {k: f.get(k) for k in ("apogee_m", "max_velocity_ms", "time_to_apogee_s",
                                                "flight_time_s", "ground_hit_ms", "deployment_velocity_ms")}
            if abort:
                row["sim"]["abort"] = abort
            if f.get("load_warnings"):
                row["sim"]["load_warnings"] = f["load_warnings"]
            row["sim"]["recovery_deployed"] = "RECOVERY_DEVICE_DEPLOYMENT" in types
            row["sim"]["ground_hit"] = "GROUND_HIT" in types
            for k in ("stability_launch_cal", "stability_min_burn_cal"):
                if k in f:
                    row["sim"][k] = f[k]

    # ---- report
    tally = collections.Counter()
    print(f"{'id':22s} {'CAD':18s} {'OpenRocket':52s}")
    for row in rows:
        if "error" in row and "sim" not in row:
            cad_s, sim_s = "-", f"{row['stage']} failed: {row['error'][:45]}"
            tally[f"{row['stage']} failed"] += 1
        else:
            c = row.get("cad")
            if c is None:
                cad_s = "skipped"
            elif "error" in c:
                cad_s = "CRASHED"
                tally["cad crashed"] += 1
            elif c["lost"]:
                cad_s = f"{c['parts']} parts, LOST"
                tally["cad lost parts"] += 1
            else:
                cad_s = f"{c['parts']} parts ok"
                tally["cad ok"] += 1
            s = row.get("sim", {})
            if "error" in s:
                sim_s = "FAILED: " + s["error"][:44]
                tally["sim failed"] += 1
            else:
                sim_s = (f"apogee {fin(s['apogee_m'], 0)} m, lands {fin(s['ground_hit_ms'])} m/s, "
                         f"{fin(s['flight_time_s'], 0)} s" + ("" if s["recovery_deployed"] else ", NO CHUTE"))
                tally["sim ok"] += 1
                if s.get("abort"):
                    sim_s += f"  ABORT: {s['abort'][:60]}"
                    tally["sim: aborted"] += 1
                if not s["recovery_deployed"]:
                    tally["sim: recovery never deployed"] += 1
                if isinstance(s.get("ground_hit_ms"), (int, float)) and s["ground_hit_ms"] > 6:
                    tally["sim: lands faster than 6 m/s"] += 1
        print(f"{row['id'][:22]:22s} {cad_s:18s} {sim_s}")
    print("\ntotals:")
    for k, v in sorted(tally.items()):
        print(f"   {k:32s} {v}")
    notes = collections.Counter(n for r in rows for n in r.get("ork_notes", []))
    for n, v in notes.items():
        print(f"   note: {v} x {n}")
    json.dump(rows, open(os.path.join(out, "summary.json"), "w"), indent=1, default=str)
    print(f"\nwrote {os.path.join(out, 'summary.json')} and one .ork per design in {out}")


if __name__ == "__main__":
    main()
