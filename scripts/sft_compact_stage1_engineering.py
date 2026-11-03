#!/usr/bin/env python3
"""Static engineering stats + loader-snapshot check for the compact repair.

FLIGHT-FREE by design (per the amended Stage-1 brief):

* engineering stats use only MassCalculator (liftoff/loaded mass, CG) and
  BarrowmanCalculator (CP, static margin) on the SELECTED simulation's flight
  configuration at Mach 0.3 / AOA 0 (the method of sftgen/tools.py
  _launch_stats, applied to the selected sim instead of simulation 0), plus
  motor data read from the resolved motor (database) instances.  Anything that
  would need a flight (rail-exit velocity, rail-exit/min-burn stability) is
  NOT computed here.
* the loader-snapshot check statically compares the ORIGINAL .ork and the
  compact-rebuilt .ork as loaded documents: per-component loader observations
  (geometry, materials, mass/CG overrides, per-config motor/deployment
  settings) as multisets, plus the selected simulation's options.  No
  simulation is run on either file.
"""

from __future__ import annotations

import json
import math
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import or_headless as oh  # noqa: E402
from scripts.sft_compact_design import (  # noqa: E402
    dump_compact_json,
    from_compact,
    to_compact,
)
from scripts.sft_full_fidelity_extract import build_ork  # noqa: E402
from scripts.sft_full_fidelity_support.runtime import (  # noqa: E402
    motor_config_for_fcid,
    deployment_config_for_fcid,
    snapshot,
    snapshot_simulation_options,
)

G0 = 9.80665  # tools.py convention

STAGE_CLASS_NAMES = {"AxialStage", "ParallelStage"}


def _find_sim(doc, sim_name):
    for i in range(doc.getSimulationCount()):
        sim = doc.getSimulation(i)
        if str(sim.getName()) == sim_name:
            return sim
    names = [str(doc.getSimulation(i).getName()) for i in range(doc.getSimulationCount())]
    raise KeyError(f"simulation {sim_name!r} not found; available: {names}")


# --------------------------------------------------------------------------
# loader-snapshot static check (no simulation)
# --------------------------------------------------------------------------

def _component_multiset(doc, fcid_str: str) -> Counter:
    import jpype

    comps: list[Any] = []

    def rec(node):
        for child in node.getChildren():
            comps.append(child)
            rec(child)

    rec(doc.getRocket())
    counter: Counter = Counter()
    for comp in comps:
        snap = snapshot(comp)
        snap.pop("getName", None)          # display only (dropped in compact)
        snap.pop("getComponentPreset", None)  # catalog identity only
        counter[json.dumps({
            "cls": str(comp.getClass().getSimpleName()),
            "loaded": snap,
            "motor": motor_config_for_fcid(comp, fcid_str),
            "deploy": deployment_config_for_fcid(comp, fcid_str),
        }, sort_keys=True, default=str)] += 1
    return counter


def loader_snapshot_check(design: dict, source_path: Path, sim_name: str,
                          rebuilt_path: Path) -> dict:
    """Compare original vs compact-rebuilt documents as loaded (static)."""
    import jpype

    helper = oh._helper()
    doc_o = helper.load_doc(str(source_path))
    doc_r = helper.load_doc(str(rebuilt_path))
    sim_o = _find_sim(doc_o, sim_name)
    sim_r = _find_sim(doc_r, sim_name)

    fcid_o = (design.get("selected_simulation") or {}).get("flight_configuration_id") or ""
    co = _component_multiset(doc_o, fcid_o)
    cr = _component_multiset(doc_r, "cfg0")

    diffs = []
    for key in (co - cr):
        diffs.append("missing in rebuilt: " + key[:300])
    for key in (cr - co):
        diffs.append("extra in rebuilt: " + key[:300])

    opts_o = snapshot_simulation_options(sim_o)
    opts_r = snapshot_simulation_options(sim_r)
    seed_diffs = []
    for k in sorted(set(opts_o) | set(opts_r)):
        if opts_o.get(k) == opts_r.get(k):
            continue
        if k == "getRandomSeed":
            # The source files store no <randomseed>; OpenRocket generates a
            # default per document.  or_headless.simulate() reseeds (seed=42)
            # before every run, so this value cannot affect any flight.
            seed_diffs.append({"option": k, "original": opts_o.get(k),
                               "rebuilt": opts_r.get(k)})
        else:
            diffs.append(f"options.{k}: {opts_o.get(k)!r} != {opts_r.get(k)!r}")
    return {"pass": not diffs, "differences": diffs, "random_seed_note": seed_diffs,
            "components_original": sum(co.values()), "components_rebuilt": sum(cr.values())}


# --------------------------------------------------------------------------
# static engineering stats (MassCalculator + Barrowman + motor database)
# --------------------------------------------------------------------------

def _jfloat(value) -> float | None:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def engineering_stats(ork_path: Path, sim_name: str) -> dict:
    """Liftoff mass/CG/CP/reference diameter/static margin + motor data.

    Static only: no simulation.  Values that need a flight are not produced.
    """
    import jpype
    from jpype import JClass

    oh._boot_or()
    doc = oh._helper().load_doc(str(ork_path))
    sim = _find_sim(doc, sim_name)
    rocket = doc.getRocket()
    fcid = sim.getFlightConfigurationId()
    config = rocket.getFlightConfiguration(fcid)

    MassCalculator = JClass("info.openrocket.core.masscalc.MassCalculator")
    Barrowman = JClass("info.openrocket.core.aerodynamics.BarrowmanCalculator")
    FlightConditions = JClass("info.openrocket.core.aerodynamics.FlightConditions")
    WarningSet = JClass("info.openrocket.core.logging.WarningSet")

    errors: list[str] = []
    out: dict[str, Any] = {}

    try:
        body = MassCalculator.calculateLaunch(config)
        fc = FlightConditions(config)
        fc.setMach(0.3)
        fc.setAOA(0.0)
        cp = Barrowman().getWorstCP(config, fc, WarningSet())
        ref_d = _jfloat(fc.getRefLength())
        mass = _jfloat(body.getMass())
        cg_x = _jfloat(body.getCM().x)
        cp_x = _jfloat(cp.x) if _jfloat(cp.weight) is not None and float(cp.weight) > 1e-9 else None
        if cp_x is None:
            errors.append("CP not computable (Barrowman weight ~ 0; e.g. no fins)")
        out["liftoff_mass_kg"] = mass
        out["loaded_mass_kg"] = mass
        out["cg_m"] = cg_x
        out["cp_m"] = cp_x
        out["reference_diameter_m"] = ref_d
        out["static_margin_cal"] = (cp_x - cg_x) / ref_d if cp_x is not None and ref_d and ref_d > 0 else None
        if out["static_margin_cal"] is None and cp_x is not None:
            errors.append("static margin not computable (reference diameter <= 0)")
    except Exception as exc:
        errors.append(f"mass/CP calculation failed: {exc.__class__.__name__}: {exc}")
        for k in ("liftoff_mass_kg", "loaded_mass_kg", "cg_m", "cp_m",
                  "reference_diameter_m", "static_margin_cal"):
            out.setdefault(k, None)

    # motors of the SELECTED configuration, data from the resolved motor instances
    motors: list[dict] = []
    stage_index = -1
    bottom_index = -1

    def walk(component, si):
        nonlocal bottom_index
        for child in component.getChildren():
            name = str(child.getClass().getSimpleName())
            child_si = si + 1 if name in STAGE_CLASS_NAMES else si
            bottom_index = max(bottom_index, child_si)
            if hasattr(child, "isMotorMount") and child.isMotorMount():
                motors.append(_motor_entry(child, child_si))
            walk(child, child_si)

    def _motor_entry(mount, si) -> dict:
        entry: dict[str, Any] = {"stage_index": si,
                                 "mount_name": None,
                                 "instance_count": None}
        try:
            entry["mount_name"] = str(mount.getName())
            entry["instance_count"] = int(mount.getInstanceCount())
            mcfg = mount.getMotorConfig(sim.getFlightConfigurationId())
            motor = mcfg.getMotor()
            if motor is None:
                entry["motor"] = None
                entry["reason"] = "no motor configured for the selected flight configuration"
                return entry
            entry["motor"] = {
                "designation": str(motor.getDesignation()),
                "manufacturer": str(motor.getManufacturer().getDisplayName()),
                "digest": str(motor.getDigest()),
                "diameter_m": _jfloat(motor.getDiameter()),
                "length_m": _jfloat(motor.getLength()),
                "ejection_delay_s": _jfloat(mcfg.getEjectionDelay()),
            }
            for key, method in (("total_impulse_ns", "getTotalImpulseEstimate"),
                                ("average_thrust_n", "getAverageThrustEstimate"),
                                ("burn_time_s", "getBurnTimeEstimate")):
                try:
                    entry["motor"][key] = _jfloat(getattr(motor, method)())
                except Exception as exc:
                    entry["motor"][key] = None
                    entry.setdefault("reason", f"{method} unavailable: {exc}")
        except Exception as exc:
            entry["motor"] = None
            entry["reason"] = f"motor config unavailable: {exc.__class__.__name__}: {exc}"
        return entry

    walk(rocket, -1)
    out["motors"] = motors

    usable = [m for m in motors if m.get("motor")]
    total_impulse = sum(
        (m["motor"]["total_impulse_ns"] or 0.0) * (m["instance_count"] or 1)
        for m in usable if m["motor"]["total_impulse_ns"] is not None)
    lit_thrust = sum(
        (m["motor"]["average_thrust_n"] or 0.0) * (m["instance_count"] or 1)
        for m in usable
        if m["stage_index"] == bottom_index and m["motor"]["average_thrust_n"] is not None)
    out["motor_aggregates"] = {
        "total_impulse_ns": total_impulse if usable else None,
        "bottom_stage_average_thrust_n": lit_thrust if usable else None,
        "thrust_to_weight": (lit_thrust / (out["liftoff_mass_kg"] * G0))
        if usable and out["liftoff_mass_kg"] else None,
        "note": ("totals over the SELECTED configuration's motors from the resolved "
                 "motor instances; thrust_to_weight uses bottom-stage (lit) average "
                 "thrust with G0=9.80665 (sftgen/tools.py convention)"),
    }
    if errors:
        out["errors"] = errors
    return out


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------

def _iter_jsonl(path: Path):
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def cmd_engineering(output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    candidate = REPO_ROOT / "sftgen/out/scratch/sft_full_fidelity_20261102/candidate/sft_v2_full_fidelity.jsonl"
    test_extract = output_dir / "test_extract" / "test_static_extract.jsonl"

    pairs: dict[tuple[str, str], dict] = {}
    first_row: dict[tuple[str, str], dict] = {}

    for row in _iter_jsonl(candidate):
        key = (row["file"], row["sim"])
        first_row.setdefault(key, row)
        pairs.setdefault(key, {"splits": ["train"]})
    for row in _iter_jsonl(test_extract):
        if "error" in row:
            continue
        key = (row["file"], row["sim"])
        first_row.setdefault(key, row)
        splits = pairs.setdefault(key, {"splits": []})["splits"]
        if "test" not in splits:
            splits.append("test")

    rebuilt_dir = output_dir / "rebuilt_ork"
    rebuilt_dir.mkdir(parents=True, exist_ok=True)
    loader_results, engineering = {}, {}
    import tempfile

    tmp = tempfile.mkdtemp(prefix="compact_rt_")
    for i, (key, meta) in enumerate(sorted(pairs.items())):
        file_rel, sim_name = key
        source = REPO_ROOT / file_rel
        entry = {"splits": meta["splits"]}
        try:
            row = first_row[key]
            if "messages" in row:  # candidate row: design lives in the message
                content = row["messages"][2]["content"]
                design = json.loads(content.split("<design>", 1)[1].rsplit("</design>", 1)[0])
            else:  # test row: already carries the statically extracted design
                design = row["design"]
            rebuilt = from_compact(to_compact(design))
            dest = Path(tmp) / f"pair{i:03d}.ork"
            build_ork(rebuilt, dest)
            entry["loader_check"] = loader_snapshot_check(design, source, sim_name, dest)
            entry["engineering"] = engineering_stats(source, sim_name)
        except Exception as exc:
            entry["error"] = f"{exc.__class__.__name__}: {exc}"
        loader_results[f"{file_rel}|{sim_name}"] = entry
        engineering[f"{file_rel}|{sim_name}"] = entry.get("engineering", {"errors": [entry.get("error", "not computed")]})

    (output_dir / "engineering.json").write_text(
        json.dumps(engineering, ensure_ascii=False, indent=1, allow_nan=False) + "\n")
    (output_dir / "loader_check.json").write_text(
        json.dumps({
            "method": ("static: original .ork vs compact-rebuilt .ork loaded headlessly; "
                       "per-component loader snapshots compared as multisets "
                       "(getName/getComponentPreset excluded as non-physics); selected-sim "
                       "options compared (getRandomSeed excluded: loader-generated default, "
                       "reseeding at simulate time makes it irrelevant). NO simulation ran."),
            "pairs": loader_results,
        }, ensure_ascii=False, indent=1, allow_nan=False) + "\n")

    n_ok = sum(1 for v in loader_results.values()
               if v.get("loader_check", {}).get("pass") and not v.get("error"))
    n_eng = sum(1 for v in engineering.values()
                if v.get("static_margin_cal") is not None)
    n_eng_err = sum(1 for v in engineering.values() if v.get("errors"))
    print(f"loader_check: {n_ok}/{len(loader_results)} pairs pass; "
          f"engineering static_margin computed for {n_eng}, "
          f"null-with-reason for {n_eng_err}")
    return 0


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO_ROOT / "sftgen/out/scratch/sft_compact_20261103"
    raise SystemExit(cmd_engineering(out))
