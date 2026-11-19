"""Parity check of the simulator link against the team's recorded flights.

Every row of the reference file whose metric_provenance.source is
"new_openrocket_simulation" was flown by the team in headless OpenRocket 24.12
from the row's own design JSON, with seed 42 and the launch conditions stored in
the design's first "simulations" block. This script flies the same designs
through the package's own chain:

    design JSON -> ork.design_to_ork -> sim.SimPool (RocketSim helper) -> reply

with those stored launch conditions put into the request (the reward itself
never does that: it sets its own conditions), and compares apogee, flight time,
time to apogee, max velocity and landing speed with the row's "targets".

Identical designs (the same rocket in several prompt styles) are flown once.
Writes <out>/sim_parity.json and <out>/sim_parity.md.

    python rocket_reward/tools/sim_parity.py DATA.jsonl [--out DIR] [--helpers N] [--limit N]

Needs ROCKET_REWARD_JAVA_HOME and ROCKET_REWARD_JAR (or Java and the jar in the
default places).
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import re
import sys
import time
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from rocket_reward import ork, sim  # noqa: E402

SEED = 42
BANDS = (0.001, 0.01, 0.05)
# target name -> flight field it is compared with
METRICS = {
    "apogee_m": "apogee_m",
    "flight_time_s": "flight_time_s",
    "time_to_apogee_s": "time_to_apogee_s",
    "max_velocity_ms": "max_velocity_ms",
    "ground_hit_ms": "landing_total_ms",  # the team's ground-hit speed (branch 0, total)
}
# OpenRocket's own defaults, used for a design that stores no simulation
# (the team then flew a Simulation created at run time with these values).
OR_DEFAULTS = {"launchrodlength": 1.0, "windaverage": 2.0, "windturbulence": 0.1,
               "winddirection": math.pi / 2, "launchaltitude": 0.0, "launchlatitude": 28.61,
               "launchlongitude": -80.6, "launchrodangle": 0.0, "launchroddirection": 90.0,
               "timestep": 0.05, "maxtime": 1200.0}


def design_text(row: dict) -> str | None:
    """The JSON text of the first complete <design> block of the row's last message (the answer)."""
    text = row["messages"][-1]["content"]
    i = text.find("<design>")
    j = text.find("</design>", i)
    if i < 0 or j < 0:
        return None
    return text[i + len("<design>"):j]


def _find(node: Any, tag: str, out: list) -> None:
    if isinstance(node, dict):
        for k, v in node.items():
            if k == tag:
                out.append(v)
            _find(v, tag, out)
    elif isinstance(node, list):
        for x in node:
            _find(x, tag, out)


def openrocket_root(design: dict) -> dict:
    """The {"openrocket": ...} node (a second top-level key such as "simulations" is dropped)."""
    return {"openrocket": design["openrocket"]}


def stored_conditions(design: dict) -> tuple[dict, list[str]]:
    """(run keyword arguments, notes) from the design's first stored simulation.

    Every launch condition the team's flight used is put into the request:
    rail, wind (average model), turbulence, wind direction, site, rod angle and
    direction, launch into wind, geodetic method, atmosphere, time step, max time.
    """
    notes: list[str] = []
    found: list = []
    _find(design, "conditions", found)
    cond: dict[str, Any] = {}
    if found:
        for ch in found[0].get("children", []):
            for k, v in ch.items():
                cond.setdefault(k, v)
    else:
        notes.append("no stored simulation: OpenRocket defaults")

    def val(key: str) -> Any:
        node = cond.get(key)
        if isinstance(node, dict) and "value" in node:
            return node["value"]
        return OR_DEFAULTS.get(key)

    wind = val("windaverage")
    wind_dir = val("winddirection")
    turbulence = val("windturbulence")
    model = (val("windmodeltype") or "Average").lower()
    if model != "average":
        notes.append(f"stored wind model {model} is not expressible; average used")
    winds: list = []
    _find(found[0] if found else {}, "wind", winds)
    for w in winds:
        if (w.get("attrs") or {}).get("model") == "average":
            sub = {k: v.get("value") for c in w.get("children", []) for k, v in c.items()}
            wind = sub.get("speed", wind)
            wind_dir = sub.get("direction", wind_dir)
            if sub.get("speed") and sub.get("standarddeviation") is not None:
                turbulence = sub["standarddeviation"] / sub["speed"]
    launch: dict[str, Any] = {
        "altitude_m": float(val("launchaltitude")),
        "latitude_deg": float(val("launchlatitude")),
        "longitude_deg": float(val("launchlongitude")),
        "rod_angle_deg": float(val("launchrodangle")),
        "rod_direction_deg": float(val("launchroddirection")),
        "wind_turbulence": float(turbulence),
        "wind_direction_deg": math.degrees(float(wind_dir)),
        "time_step_s": float(val("timestep")),
        # Unset in the file means the team's saved preference, which was "off"
        # (calibration/sim_parity.md explains how that was established).
        "launch_into_wind": bool(val("launchintowind") or False),
    }
    # A simulation that does not name its geodetic method gets OpenRocket's own
    # default, which is flat earth (the helper's default is spherical). Shown by
    # V4-0105 and V4-0159: flat reproduces the team's flight bit for bit.
    geo = val("geodeticmethod") or "flat"
    launch["geodetic"] = {"spherical": "spherical", "flat": "flat", "wgs84": "wgs84"}[str(geo).lower()]
    atm = cond.get("atmosphere")
    if isinstance(atm, dict) and (atm.get("attrs") or {}).get("model") == "extendedisa":
        sub = {k: v.get("value") for c in atm.get("children", []) for k, v in c.items()}
        launch["base_temperature_k"] = float(sub.get("basetemperature", 288.15))
        launch["base_pressure_pa"] = float(sub.get("basepressure", 101325.0))
        notes.append("extended ISA atmosphere")
    if launch["geodetic"] != "spherical":
        notes.append(f"{launch['geodetic']} earth" + ("" if val("geodeticmethod") else " (not stored: OpenRocket default)"))
    return ({"stored_config_id": val("configid"),
             "rail_m": float(val("launchrodlength")),
             "flights": [{"wind_ms": float(wind), "seed": SEED}],
             "launch": launch,
             "max_sim_time_s": float(val("maxtime"))}, notes)


def rel(got: Any, want: Any) -> float | None:
    if not isinstance(got, (int, float)) or not isinstance(want, (int, float)):
        return None
    if want == 0:
        return 0.0 if got == 0 else math.inf
    return abs(got - want) / abs(want)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("data", type=Path, help="reference JSONL (sft_v5_meta_*.jsonl)")
    ap.add_argument("--out", type=Path, required=True, help="folder for the results")
    ap.add_argument("--helpers", type=int, default=4, help="simulator helpers (default 4)")
    ap.add_argument("--limit", type=int, default=None, help="fly only the first N distinct designs")
    ap.add_argument("--compare", type=Path, default=None,
                    help="optional JSONL of another run of the same rows ({'id', 'flown': {...}}), for example "
                         "the team's OrBatch helper on this PC; outliers that match it exactly are explained")
    a = ap.parse_args(argv)

    rows = [json.loads(line) for line in a.data.open(encoding="utf-8") if line.strip()]
    rows = [r for r in rows if (r.get("metric_provenance") or {}).get("source") == "new_openrocket_simulation"]
    groups: dict[str, list[dict]] = collections.OrderedDict()
    for r in rows:
        groups.setdefault(design_text(r) or "", []).append(r)
    items = list(groups.items())[: a.limit] if a.limit else list(groups.items())

    jobs, results = [], []
    for text, members in items:
        first = members[0]
        res: dict[str, Any] = {"ids": [m["id"] for m in members], "file": first.get("source_file")}
        # the targets of every copy must agree, else the duplicate is not a duplicate
        tset = {json.dumps({k: m["targets"].get(k) for k in METRICS}, sort_keys=True) for m in members}
        res["targets_agree"] = len(tset) == 1
        res["targets"] = {k: first["targets"].get(k) for k in METRICS}
        try:
            design = json.loads(text)
            kwargs, notes = stored_conditions(design)
            res["notes"] = notes
            root = openrocket_root(design)
            # The configuration the team flew: the stored simulation's, else the one
            # the design declares (the same rule the reward uses).
            kwargs["config_id"] = kwargs.pop("stored_config_id", None) or ork.flight_config_id(root)
            res["request"] = kwargs
            # The team's OpenRocket flew whatever motor it found by name when a digest was
            # missing; the parity check does the same and reports it (motor_lookup).
            kwargs = dict(kwargs, ork_text_or_path=ork.design_to_ork(root), allow_motor_substitution=True)
            jobs.append((res, kwargs))
        except Exception as exc:  # reported in the output, never hidden
            res["error"] = f"could not write: {type(exc).__name__}: {exc}"
        results.append(res)

    t0 = time.monotonic()
    with sim.SimPool(a.helpers) as pool:
        replies = pool.run_many([kw for _, kw in jobs])
    wall = time.monotonic() - t0

    load_w, sim_w = collections.Counter(), collections.Counter()
    for (res, _), rep in zip(jobs, replies):
        res["ok"] = rep.get("ok")
        if not rep.get("ok"):
            res["error"] = f"{rep.get('error_kind')}: {rep.get('message')}"
            continue
        for w in rep.get("load_warnings", []):
            load_w[w] += 1
        f = rep["flights"][0]
        res["motor_lookup"] = [{k: e.get(k) for k in ("requested_designation", "found_by", "flown_designation")}
                               for e in rep.get("motor_lookup") or []]
        res["motor_substituted"] = rep["rocket"].get("motor_substituted")
        if not f.get("ok"):
            res["error"] = f"flight failed: {f.get('error_kind')}: {f.get('error')}"
            continue
        for w in f.get("warnings", []):
            sim_w[w] += 1
        b0 = (f.get("branches") or [{}])[0]
        tg = res["targets"]
        got = {k: (b0.get(field) if field == "landing_total_ms" else f.get(field)) for k, field in METRICS.items()}
        got["ground_hit_ms_openrocket"] = f.get("ground_hit_ms")
        res["flown"] = got
        res["diff"] = {k: rel(got[k], tg[k]) for k in METRICS}
        res["diff_ground_hit_openrocket"] = rel(f.get("ground_hit_ms"), tg["ground_hit_ms"])
        res["abort"] = f.get("abort")
        res["stages"] = rep["rocket"].get("stage_count")
        res["motors"] = rep["rocket"].get("motor_count")
        res["load_warnings"] = rep.get("load_warnings", [])
        res["sim_warnings"] = f.get("warnings", [])

    other = {}
    if a.compare:
        for line in a.compare.open(encoding="utf-8"):
            if line.strip():
                o = json.loads(line)
                other.setdefault(o.get("id"), o.get("flown"))
    for res in results:
        if not res.get("diff"):
            continue
        o = other.get(res["ids"][0])
        if o:
            mine = dict(res["flown"], ground_hit_ms=res["flown"]["ground_hit_ms_openrocket"])
            res["vs_compare"] = {k: rel(mine.get(k), v) for k, v in o.items()}
        res["reason"] = reason(res)

    flown = [r for r in results if r.get("diff")]
    summary: dict[str, Any] = {"rows": len(rows), "distinct_designs": len(groups), "checked": len(results),
                               "flown": len(flown), "not_flown": len(results) - len(flown),
                               "wall_s": round(wall, 1), "helpers": a.helpers, "bands": {}}
    if other:
        same = [r for r in flown if r.get("vs_compare") and max(r["vs_compare"].values()) <= SAME]
        summary["same_as_compare"] = {"file": str(a.compare), "designs": len(same),
                                      "compared": sum(bool(r.get("vs_compare")) for r in flown)}
    for k in METRICS:
        vals = [r["diff"][k] for r in flown if r["diff"][k] is not None]
        summary["bands"][k] = {f"{b:.1%}": sum(v <= b for v in vals) for b in BANDS}
        summary["bands"][k]["n"] = len(vals)
        summary["bands"][k]["worst"] = max(vals) if vals else None
    summary["motor_found_by"] = dict(collections.Counter(
        e["found_by"] for r in results for e in r.get("motor_lookup") or []))
    summary["designs_with_substituted_motor"] = sorted(r["ids"][0] for r in results if r.get("motor_substituted"))
    allv = [max(v for v in r["diff"].values() if v is not None) for r in flown]
    summary["bands"]["all_five"] = {f"{b:.1%}": sum(v <= b for v in allv) for b in BANDS}
    summary["load_warnings"] = dict(load_w.most_common())
    summary["sim_warnings"] = dict(sim_w.most_common())
    summary["sim_warning_kinds"] = dict(collections.Counter(
        re.sub(r"\(\d+(\.\d+)? m/s\)", "(N m/s)", w) for w in sim_w.elements()).most_common())
    outliers = [r for r in results if "error" in r or not r.get("diff")
                or max(v for v in r["diff"].values() if v is not None) > 0.001]
    summary["outliers"] = len(outliers)
    summary["outlier_reasons"] = dict(collections.Counter(r.get("reason", "not flown") for r in outliers))
    out = {"summary": summary, "designs": results}
    a.out.mkdir(parents=True, exist_ok=True)
    with open(a.out / "sim_parity.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1)
        fh.write("\n")
    with open(a.out / "sim_parity.md", "w", encoding="utf-8", newline="\n") as fh:
        fh.write(markdown(summary, outliers, a.data))
    print(json.dumps({k: v for k, v in summary.items() if "warning" not in k}, indent=1))
    return 0


SAME = 1e-9  # "the same number" when comparing two runs on this PC
CROSS_MACHINE = ("same numbers as the team's own helper (OrBatch) flying the same file on this PC; "
                 "the gap is between the team's machine and this one, not the chain")
NO_STORED_SIM = ("no stored simulation: the team flew it with their own saved OpenRocket preferences, "
                 "which the row does not record")


def reason(res: dict) -> str | None:
    """Why a flown design is more than 0.1% off on some number (None when it is not)."""
    worst = max(v for v in res["diff"].values() if v is not None)
    if worst <= 0.001:
        return None
    if any("no stored simulation" in n for n in res.get("notes", [])):
        return NO_STORED_SIM
    vs = res.get("vs_compare")
    if vs and max(vs.values()) <= SAME:
        return CROSS_MACHINE
    return "not explained"


def _pct(x: float | None) -> str:
    return "-" if x is None else f"{100 * x:.3g}%"


def markdown(s: dict, outliers: list[dict], data: Path) -> str:
    lines = [
        "# Simulator parity with the team's recorded flights",
        "",
        f"Made by `rocket_reward/tools/sim_parity.py {data.name}`. Chain: design JSON -> "
        "`ork.design_to_ork` -> `sim.SimPool` (RocketSim helper, OpenRocket 24.12) with the launch "
        "conditions stored in each design's own simulation block and seed 42.",
        "",
        f"* rows with source new_openrocket_simulation: {s['rows']}; distinct designs: "
        f"{s['distinct_designs']}; flown: {s['flown']}; not flown: {s['not_flown']}",
        f"* wall time {s['wall_s']} s with {s['helpers']} helpers",
    ]
    if "same_as_compare" in s:
        c = s["same_as_compare"]
        lines.append(f"* identical (within 1e-9) to the team's OrBatch helper flying the same designs on this PC: "
                     f"{c['designs']} of {c['compared']}")
    lines += ["", "## Designs within each band", "",
              "| number | n | within 0.1% | within 1% | within 5% | worst |", "|---|---|---|---|---|---|"]
    names = {"apogee_m": "apogee", "flight_time_s": "flight time", "time_to_apogee_s": "time to apogee",
             "max_velocity_ms": "max velocity", "ground_hit_ms": "landing speed (landing_total_ms vs ground_hit_ms)"}
    for k, label in names.items():
        b = s["bands"][k]
        lines.append(f"| {label} | {b['n']} | {b['0.1%']} | {b['1.0%']} | {b['5.0%']} | {_pct(b['worst'])} |")
    b = s["bands"]["all_five"]
    lines.append(f"| all five at once | {s['flown']} | {b['0.1%']} | {b['1.0%']} | {b['5.0%']} | |")
    lines += ["", f"## Outliers (any number more than 0.1% off): {len(outliers)}", ""]
    for why, n in s["outlier_reasons"].items():
        lines.append(f"* {n}: {why}")
    lines += ["", "| design (rows) | file | notes | apogee | flight time | time to apogee | max velocity | landing | reason |",
              "|---|---|---|---|---|---|---|---|---|"]
    for r in outliers:
        d = r.get("diff") or {}
        lines.append(f"| {r['ids'][0]} ({len(r['ids'])}) | {r.get('file')} | {'; '.join(r.get('notes', []))} | "
                     + " | ".join(_pct(d.get(k)) for k in names)
                     + f" | {r.get('reason') or r.get('error')} |")
    lines += ["", "## How the outliers were chased", "", *EXPLANATION, ""]
    lines += ["## Warnings OpenRocket gave on these flights", "", "Load warnings (designs):"]
    lines += [f"* {n}: {w}" for w, n in s["load_warnings"].items()] or ["* none"]
    lines += ["", "Simulation warnings, numbers replaced by N (designs):"]
    lines += [f"* {n}: {w}" for w, n in s["sim_warning_kinds"].items()] or ["* none"]
    lines.append("")
    return "\n".join(lines)


EXPLANATION = [
    "* Every flown design was also compared with the team's own OrBatch helper flying the same "
    "design JSON with its stored simulation on this PC (`--compare`, "
    "`ork_checks/parity_results_intowind_false.jsonl`). 146 of 147 designs give the same four "
    "numbers to 1e-9, most bit for bit, so for those the new chain (writer, request, helper) adds "
    "nothing. The one exception is level-1 (no stored simulation, see below).",
    "* For several outliers (APEX 30.08.2021, Comet Chaser, semroc_starfire_kv-20) the team's "
    "ORIGINAL .ork file flown through RocketSim on this PC (`java_checks/parity.jsonl`) also gives "
    "exactly our numbers. So the gap is between the team's machine and this one. Apogee and max "
    "velocity agree to 1e-7 or better there; only the numbers that amplify tiny differences move: "
    "the ground-hit speed (interpolated at touchdown), flight time of rockets with dropped stages, "
    "and time to apogee, which can move by one 0.05 s step on a flat-topped flight. Likely cause: "
    "a different JDK or CPU, where java.lang.Math functions may differ in the last bit. Not proven, "
    "because the team's machine is not available.",
    "* level-1 (V4-0182) stores no simulation. The team flew a Simulation created at run time, "
    "which takes its launch conditions from that user's saved OpenRocket preferences; the row does "
    "not record them. OpenRocket's built-in defaults (1 m rail, 2 m/s wind, flat earth) reproduce "
    "apogee to 0.006% and ground-hit speed to 1.6%. No combination of rail, wind direction, "
    "launch-into-wind and geodetic method tried reproduces it exactly.",
    "* Two things were found and fixed while chasing: (1) a stored simulation that names no "
    "geodetic method flies with OpenRocket's default, which is flat earth (V4-0105 and V4-0159 "
    "then match bit for bit); (2) the configuration to fly is the one the design declares "
    "(`cfg0`), not metric_provenance.configid (the source file's UUID), and it must be passed "
    "as config_id because many designs do not mark it default.",
    "* A stored `launchintowind` that is missing is flown as false; with true, some "
    "rockets (PhoenixIV: 3.3% on apogee) move by several percent (the ork-writer's check), and false "
    "matches the team.",
]


if __name__ == "__main__":
    sys.exit(main())
