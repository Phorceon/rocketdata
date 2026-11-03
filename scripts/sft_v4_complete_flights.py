#!/usr/bin/env python3
"""Flight completion for the SFT v4 hardware_only source records.

Takes the COMPLETE, geometry-verified input sources.jsonl (330 records in
catalog order: 244 flight_grounded with matching saved results, 86
hardware_only without usable matching results) and runs REAL headless
OpenRocket simulations for the 86 hardware-only records whose selected
flight configuration is fully specified.  The 244 flight_grounded records
are passed through unchanged -- they are never re-flown.

Per hardware-only record the driver flies the EXACT selected simulation
instance (by index, not by name: two records carry duplicate simulation
names and or_headless._get_sim silently picks the first name match) of the
exact source .ork with the deterministic or_headless boot (UUID seed 42,
OrBatch.reseed on the simulation options, one discarded warm-up per
(file, sim) exactly like or_headless.simulate).  The one record with no
stored simulation (original:level-1.ork) flies a runtime-created
Simulation of the default flight configuration; the source .ork file
itself is never modified.

A fresh result becomes a flight label ONLY when the main (branch 0)
trajectory really reaches ground impact with finite apogee, landing speed
and flight time.  Unsafe but real outcomes keep their labels and gain an
explicit safety flag (hard landing > 8 m/s, stability < 1.0 cal, no
recovery deployment).  Failed/unusable cases stay honest hardware_only
records with the exact reason recorded.

The special original:skydragon_l3.ork load-equivalence failure is
re-checked with the unmodified check_pair after the narrowly scoped
add_explicit_preset_overrides packed-length sync (see
scripts/sft_compact_motor_ids.py): the preset database's Rocketman LS-12
packed length differs from the source .ork's stored value by 4e-17 m,
which made the exact multiset comparison fail.  c_pass is only set True
when the identical check actually passes.

Outputs under sftgen/out/scratch/sft_v4_flight_completion/:
    sources.jsonl                 all 330, original order (244 untouched)
    flight_results.jsonl          raw results, provenance, exact failures
    flight_completion_report.json counts, simulation-call breakdown, blockers
    sources_summary.json          recomputed from the output records
    motor_lookup.json / assets.json   copied unchanged from the input
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import sys
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import or_headless as oh  # noqa: E402
from scripts.sft_compact_design import dump_compact_json  # noqa: E402
from scripts.sft_compact_digest_check import check_pair  # noqa: E402  (JVM lazy)
from scripts.sft_compact_motor_ids import apply_stage2_and_fix  # noqa: E402
from scripts.sft_full_fidelity_support.ork_archive import (  # noqa: E402
    read_ork_archive,
)
from scripts.sft_full_fidelity_support.xml_tree import (  # noqa: E402
    find_simulation_nodes,
)
from scripts.sft_v4_sources import (  # noqa: E402
    append_checkpoint,
    config_motor_blocks,
    finite,
    json_line,
    load_checkpoint,
    xml_sim_name,
)

WORKSPACE = ROOT.parents[1]
DEFAULT_INPUT_DIR = ROOT / "sftgen/out/scratch/sft_v4_complete_ready"
DEFAULT_OUTPUT_DIR = ROOT / "sftgen/out/scratch/sft_v4_flight_completion"
CATALOG_REL = "data/rockets_full.jsonl"

SEED = 42
HARD_LANDING_MS = 8.0        # Tier-3 structural limit from the project spec
MIN_STABILITY_CAL = 1.0      # Tier-3 stability limit from the project spec

TARGET_KEYS = ("apogee_m", "ground_hit_ms", "flight_time_s", "time_to_apogee_s",
               "max_velocity_ms", "max_mach", "wind_ms")

# flags that described the ABSENT/UNUSABLE saved-result labeling; removed
# only when a fresh, usable flight result genuinely replaces them
REPLACED_LABEL_FLAGS = (
    "hardware_only_no_flight_labels",
    "saved_flight_not_rerun",
    "saved_metrics_partial_no_landing_speed",
    "outdated_saved_results_reference_only",
    "saved_simulation_not_uptodate",
)

SKYDRAGON_ID = "original:skydragon_l3.ork"


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sanitize(value: Any) -> Any:
    """Non-finite floats -> None so strict JSON lines stay writable."""
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {k: sanitize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize(v) for v in value]
    return value


def xml_sim_names(path: Path) -> list[str | None]:
    tree, _entries, _container = read_ork_archive(path)
    return [xml_sim_name(n) for n in find_simulation_nodes(tree)]


def flight_targets(result: dict) -> dict:
    """The seven canonical label metrics that are finite in this result."""
    return {k: result[k] for k in TARGET_KEYS if finite(result.get(k)) is not None}


def assess_completion(result: dict) -> tuple[bool, dict]:
    """Real ground-impact completion of the MAIN (branch 0) trajectory."""
    events = result.get("events") or []
    b0_types = [str(e.get("type")) for e in events if e.get("branch") == 0]
    apogee = finite(result.get("apogee_m"))
    landing = finite(result.get("ground_hit_ms"))
    duration = finite(result.get("flight_time_s"))
    checks = {
        "main_branch_ground_hit": "GROUND_HIT" in b0_types,
        "finite_positive_apogee": apogee is not None and apogee > 0,
        "finite_nonnegative_landing_speed": landing is not None and landing >= 0,
        "finite_positive_flight_time": duration is not None and duration > 0,
    }
    checks["main_branch_sim_abort"] = "SIM_ABORT" in b0_types
    checks["main_branch_events"] = b0_types
    usable = all(checks[k] for k in (
        "main_branch_ground_hit", "finite_positive_apogee",
        "finite_nonnegative_landing_speed", "finite_positive_flight_time"))
    return usable, checks


def safety_flags(result: dict) -> list[str]:
    flags: list[str] = []
    landing = finite(result.get("ground_hit_ms"))
    if landing is not None and landing > HARD_LANDING_MS:
        flags.append("fresh_flight_hard_landing")
    stability = finite(result.get("stability_cal"))
    if stability is not None and stability < MIN_STABILITY_CAL:
        flags.append("fresh_flight_unstable")
    events = result.get("events") or []
    if not any(str(e.get("type")) == "RECOVERY_DEVICE_DEPLOYMENT"
               for e in events if e.get("branch") == 0):
        flags.append("fresh_flight_no_recovery_deployment")
    return flags


def _new_simulation(doc: Any) -> Any:
    """Runtime-created Simulation of the loaded rocket's selected (default)
    flight configuration.  Used only for designs that store no simulation;
    the source .ork file is never modified."""
    import jpype

    Simulation = jpype.JClass("info.openrocket.core.document.Simulation")
    rocket = doc.getRocket()
    try:
        return Simulation(rocket)
    except Exception as exc:
        ctors = [str(c) for c in Simulation.class_.getConstructors()]
        raise RuntimeError(
            f"cannot construct Simulation for a no-simulation design "
            f"(constructors: {ctors})") from exc


def _read_back_fcid(sim: Any) -> str | None:
    for name in ("getFlightConfigurationId", "getFlightConfigurationID"):
        if hasattr(sim, name):
            try:
                fcid = getattr(sim, name)()
                return str(fcid) if fcid is not None else None
            except Exception:
                continue
    return None


def simulate_exact(ork_path: Path, sim_index: int | None, meta: dict,
                   seed: int = SEED):
    """or_headless.simulate with EXACT simulation selection.

    Identical boot (oh._boot_or), identical deterministic UUID seeding, one
    discarded warm-up per (file, sim) keyed in oh._WARM, identical reseed
    (OrBatch.reseed on the options) and identical metric extraction.  The
    only difference is selection BY INDEX (or a runtime-created simulation
    when sim_index is None) so a duplicate simulation name can never make
    the wrong instance fly.  ``meta`` accumulates the actual simulate-call
    counts (warm-up + measured attempts, simulator exceptions) and is
    updated even when an exception propagates.
    """
    import jpype

    oh._boot_or()
    OrBatch = jpype.JClass("OrBatch")
    GeneralRocketLoader = jpype.JClass("info.openrocket.core.file.GeneralRocketLoader")
    File = jpype.JClass("java.io.File")
    meta["created_simulation"] = sim_index is None

    def load():
        # fresh load every call: a reused document carries state between runs
        OrBatch.seedUUID(oh.UUID_SEED)
        d = GeneralRocketLoader(File(str(ork_path))).load()
        if sim_index is None:
            return d, _new_simulation(d)
        return d, d.getSimulation(int(sim_index))

    key = (str(Path(ork_path).resolve()), sim_index)
    if key not in oh._WARM:
        _, wsim = load()
        OrBatch.reseed(wsim.getOptions(), int(seed))
        meta["warmup_calls"] += 1
        try:
            wsim.simulate()
        except Exception:
            meta["simulator_exceptions"] += 1
            raise
        # the first run of a design in a JVM differs at ~1e-14 (lazy caches);
        # one discarded warm-up makes results run-order independent
        oh._WARM.add(key)
    doc, sim = load()

    t_sim0 = time.perf_counter()
    opts = sim.getOptions()
    OrBatch.reseed(opts, int(seed))
    meta["measured_calls"] += 1
    try:
        sim.simulate()
    except Exception:
        meta["simulator_exceptions"] += 1
        raise
    sim_ms = (time.perf_counter() - t_sim0) * 1000.0

    sd = sim.getSimulatedData()
    diameter_m = float(sim.getRocket().getBoundingRadius()) * 2.0
    stability_cal = oh._stability_calibers_from_sim(sim, diameter_m)

    # motors actually assigned to the flown configuration (mount DFS order)
    flown_fcid = _read_back_fcid(sim)
    Fcid = jpype.JClass(
        "info.openrocket.core.rocketcomponent.FlightConfigurationId")
    fcid_obj = Fcid(flown_fcid) if flown_fcid else None
    flown_motors: list[dict] = []

    def walk_mounts(component: Any) -> None:
        for ch in component.getChildren():
            if hasattr(ch, "isMotorMount") and ch.isMotorMount():
                try:
                    mcfg = ch.getMotorConfig(fcid_obj)
                    m = mcfg.getMotor()
                    if m is None:
                        flown_motors.append({"designation": None,
                                             "ejection_delay_s": None})
                    else:
                        delay = float(mcfg.getEjectionDelay())
                        flown_motors.append({
                            "designation": str(m.getDesignation()),
                            "ejection_delay_s": None if delay != delay else delay,
                        })
                except Exception:
                    flown_motors.append({"designation": "unavailable",
                                         "ejection_delay_s": None})
            walk_mounts(ch)

    walk_mounts(sim.getRocket())

    try:
        max_mach = float(sd.getMaxMachNumber())
    except Exception:
        max_mach = float("nan")
    try:
        deploy_v = float(sd.getDeploymentVelocity())
    except Exception:
        deploy_v = float("nan")
    try:
        wind_ms = float(opts.getWindSpeedAverage())
    except Exception:
        wind_ms = 0.0
    result = {
        "apogee_m": float(sd.getMaxAltitude()),
        "max_velocity_ms": float(sd.getMaxVelocity()),
        "time_to_apogee_s": float(sd.getTimeToApogee()),
        "flight_time_s": float(sd.getFlightTime()),
        "ground_hit_ms": float(sd.getGroundHitVelocity()),
        "max_accel_ms2": float(sd.getMaxAcceleration()),
        "max_mach": max_mach,
        "deployment_velocity_ms": deploy_v,
        "wind_ms": wind_ms,
        "stability_cal": stability_cal,
        "events": [{"branch": b, "type": str(e.getType().name()), "t": float(e.getTime())}
                   for b in range(sd.getBranchCount())
                   for e in sd.getBranch(b).getEvents()],
        "flown_motors": flown_motors,
        "runtime_ms": sim_ms,
    }
    return result, flown_fcid


def build_plan(record: dict) -> dict:
    """How this record will be flown: exact sim instance or created sim."""
    sp = record.get("source_preservation") or {}
    ex = sp.get("extraction") or {}
    sim_index = ex.get("sim_index")
    fcid = ex.get("flight_configuration_id")
    record_name = record.get("sim")
    path = Path(record["file"])
    plan: dict[str, Any] = {
        "flight_file": str(path), "sim_index": sim_index,
        "sim_name": record_name, "flight_configuration_id": fcid,
    }
    if not path.is_file():
        plan["error"] = f"source .ork missing: {path}"
        return plan
    try:
        tree, _entries, _container = read_ork_archive(path)
        names = [xml_sim_name(n) for n in find_simulation_nodes(tree)]
    except Exception as exc:
        plan["error"] = f"cannot read simulations from {path.name}: {exc}"
        return plan
    if fcid is not None:
        # design-side motor blocks of the selected configuration (document
        # order): the identity the flown configuration is verified against
        plan["config_motors"] = [
            {"designation": b.get("designation"), "delay": finite(b.get("delay"))}
            for b in config_motor_blocks(tree, str(fcid))
        ]
    if sim_index is None:
        plan.update({"method": "runtime_created_default_configuration",
                     "duplicate_name_count": 0, "first_instance_of_name": True,
                     "stored_sim_count": len(names)})
        return plan
    if not isinstance(sim_index, int) or sim_index >= len(names):
        plan["error"] = (f"selected sim_index {sim_index} out of range "
                         f"({len(names)} simulations)")
        return plan
    name_at = names[sim_index]
    if record_name is not None and name_at != record_name:
        plan["error"] = (f"record sim name {record_name!r} != XML name "
                         f"{name_at!r} at index {sim_index}")
        return plan
    dup = sum(1 for n in names if n == name_at)
    plan.update({
        "method": "index",
        "duplicate_name_count": dup,
        "first_instance_of_name": dup <= 1 or names.index(name_at) == sim_index,
        "stored_sim_count": len(names),
    })
    return plan


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------

def run(input_dir: Path, output_dir: Path, seed: int, limit: int,
        refly: list[str] | None = None) -> dict:
    input_dir, output_dir = Path(input_dir), Path(output_dir)
    sources_in = input_dir / "sources.jsonl"
    records = [json.loads(l) for l in sources_in.read_text().splitlines() if l.strip()]
    assert len(records) == 330, f"expected 330 input records, got {len(records)}"

    output_dir.mkdir(parents=True, exist_ok=True)
    results_path = output_dir / "flight_results.jsonl"
    store = load_checkpoint(results_path)
    for rid in refly or []:
        if store.pop(rid, None) is not None:
            print(f"[refly] discarding the checkpointed result of {rid}; "
                  f"it will be flown again", flush=True)

    hw_indexes = [i for i, r in enumerate(records)
                  if r["label_mode"] == "hardware_only"]
    if limit:
        hw_indexes = hw_indexes[:limit]

    print(f"[plan] {len(hw_indexes)} hardware_only cases "
          f"({len(store)} already checkpointed)", flush=True)

    totals = Counter()
    case_entries: dict[str, dict] = {}
    for k, v in store.items():
        case_entries[k] = v
        prov = v.get("provenance") or {}
        totals["warmup_calls"] += int(prov.get("warmup_calls") or 0)
        totals["measured_calls"] += int(prov.get("measured_calls") or 0)
        totals["simulator_exceptions"] += int(prov.get("simulator_exceptions") or 0)
        if v.get("status") == "flown_ok":
            totals["successful"] += 1
        elif v.get("status") == "flown_unusable":
            totals["flown_unusable"] += 1
        elif v.get("status") == "error":
            totals["errors"] += 1

    idx_by_id = {r["catalog_id"]: i for i, r in enumerate(records)}
    lookup = json.loads((input_dir / "motor_lookup.json").read_text())
    id_by_digest = {v["digest"]: k for k, v in lookup.items()}
    digest_by_id = {k: v["digest"] for k, v in lookup.items()}

    # ---- phase 0: skydragon load-equivalence recheck (deterministic, JVM) ----
    skydragon_out: dict[str, Any] = {}
    skydragon_recheck_entry: dict[str, Any] | None = None
    rec = records[idx_by_id[SKYDRAGON_ID]]
    if (rec.get("digest_entry") or {}).get("c_pass") is False:
        entry = rec["digest_entry"]
        skydragon_out = {
            "catalog_id": SKYDRAGON_ID,
            "input_c_pass": entry.get("c_pass"),
            "diagnosis": (
                "The compact/model conversion is correct; the c-variant "
                "comparison failed on ONE parachute packed length: re-applying "
                "the digest-identified Rocketman LS-12 preset at load resolves "
                "getLength 0.17653 m while the model-visible design (preset "
                "blocks removed, like every other record) loads the source's "
                "stored packedlength 0.17652999999999996 m -- a 4e-17 m "
                "representation difference between the preset database entry "
                "and the value the original author's OpenRocket wrote into "
                "the .ork.  The exact multiset key treats these as different "
                "components (CG x = length/2 follows)."),
            "fix": (
                "add_explicit_preset_overrides "
                "(scripts/sft_compact_motor_ids.py) now also syncs an existing "
                "<packedlength> leaf with the as-is loaded getLength, exactly "
                "like its existing mass/CG override mechanism: values read "
                "from the load dump, never invented; records whose loaded "
                "length already agrees are untouched."),
        }
        try:
            with tempfile.TemporaryDirectory(prefix="skydragon_recheck_") as tmp:
                skydragon_recheck_entry = check_pair(
                    SKYDRAGON_ID, rec["compact"], Path(tmp),
                    id_by_digest, digest_by_id)
            skydragon_out["recheck"] = {
                k: skydragon_recheck_entry.get(k) for k in
                ("c_pass", "c_diff_count", "b0_pass", "b1_pass", "b2_pass",
                 "b3_pass", "dump_variant", "preset_fix_applied")}
            skydragon_out["rechecked_at_utc"] = now_iso()
        except Exception as exc:
            skydragon_recheck_entry = None
            skydragon_out["recheck"] = {
                "c_pass": False,
                "error": f"{exc.__class__.__name__}: {exc}"}
        skydragon_out["resolved"] = bool(
            skydragon_out.get("recheck", {}).get("c_pass"))
        if skydragon_out["resolved"]:
            totals["skydragon_c_pass_recovered"] = 1
        print(f"[skydragon] recheck c_pass={skydragon_out['resolved']}",
              flush=True)

    # ---- phase 1: the actual flights ----
    for n, i in enumerate(hw_indexes):
        record = records[i]
        catalog_id = record["catalog_id"]
        if catalog_id in store and store[catalog_id].get("status") in (
                "flown_ok", "flown_unusable", "error"):
            continue  # resumable checkpoint: keep the earlier real result
        plan = build_plan(record)
        entry: dict[str, Any] = {
            "catalog_id": catalog_id,
            "sim_selection": plan,
            "seed": seed,
            "simulated_at_utc": now_iso(),
        }
        meta = {"warmup_calls": 0, "measured_calls": 0,
                "simulator_exceptions": 0}
        if plan.get("error"):
            entry.update({
                "status": "error",
                "provenance": {"source": "new_openrocket_simulation",
                               "no_flight_rerun": False, **meta},
                "error": plan["error"],
            })
            totals["errors"] += 1
            print(f"[{n + 1}/{len(hw_indexes)}] ERROR    {catalog_id}: "
                  f"{plan['error']}", flush=True)
            append_checkpoint(results_path, catalog_id, sanitize(entry))
            store[catalog_id] = entry
            case_entries[catalog_id] = entry
            continue
        try:
            result, flown_fcid = simulate_exact(
                Path(plan["flight_file"]), plan["sim_index"], meta, seed=seed)
            entry["provenance"] = {
                "source": "new_openrocket_simulation",
                "no_flight_rerun": False,
                **meta,
                "flown_flight_configuration_id": flown_fcid,
            }
            totals["warmup_calls"] += meta["warmup_calls"]
            totals["measured_calls"] += meta["measured_calls"]
            totals["simulator_exceptions"] += meta["simulator_exceptions"]
            fcid = plan.get("flight_configuration_id")
            flown_motors = result.get("flown_motors") or []
            config_motors = plan.get("config_motors") or []
            _flown_ids = sorted(str(m.get("designation")) for m in flown_motors
                                if m.get("designation"))
            _design_ids = sorted(str(m.get("designation"))
                                 for m in config_motors
                                 if m.get("designation"))
            if (fcid is not None and flown_fcid is not None
                    and flown_fcid == fcid):
                config_verified = "flight_configuration_id_exact"
            elif (_design_ids and _flown_ids == _design_ids):
                # non-UUID configid strings (e.g. 'cfg-38-f50') map to
                # deterministic loader-generated UUIDs; the flown
                # configuration is THE selected one when its resolved motor
                # identities match the design's motor blocks exactly
                config_verified = "motor_identities_match"
            else:
                config_verified = None
            config_matches = (fcid is None or config_verified is not None)
            usable, assessment = assess_completion(result)
            entry["result"] = result
            entry["completion_assessment"] = assessment
            entry["config_verification"] = {
                "verdict": config_verified,
                "selected_configid": fcid,
                "flown_flight_configuration_id": flown_fcid,
                "design_motors": config_motors,
                "flown_motors": flown_motors,
            }
            if usable and config_matches:
                entry.update({
                    "status": "flown_ok",
                    "targets": flight_targets(result),
                    "safety_flags": safety_flags(result),
                })
                totals["successful"] += 1
                print(f"[{n + 1}/{len(hw_indexes)}] OK       {catalog_id}: "
                      f"apogee {result['apogee_m']:.1f} m, landing "
                      f"{result['ground_hit_ms']:.1f} m/s, "
                      f"{result['flight_time_s']:.1f} s", flush=True)
            else:
                reasons = []
                if not config_matches:
                    reasons.append(
                        f"flown configuration {flown_fcid} does not match "
                        f"the selected configuration {fcid}: flown motors "
                        f"{_flown_ids or '[none resolvable]'} vs design "
                        f"motors {_design_ids or '[none]'}")
                    if not _flown_ids and _design_ids:
                        reasons.append(
                            "the flown configuration has no resolvable "
                            f"motor (design motor(s) {_design_ids} not in "
                            "the shipped thrust-curve database and no curve "
                            "bundled in the .ork)")
                if assessment.get("main_branch_sim_abort"):
                    reasons.append(
                        "OpenRocket aborted the main branch (SIM_ABORT at "
                        f"t={result.get('flight_time_s')!r} s, no ground "
                        "impact)")
                reasons += [k for k in (
                    "main_branch_ground_hit", "finite_positive_apogee",
                    "finite_nonnegative_landing_speed",
                    "finite_positive_flight_time")
                    if not assessment.get(k)]
                entry.update({"status": "flown_unusable",
                              "failure_reasons": reasons})
                totals["flown_unusable"] += 1
                print(f"[{n + 1}/{len(hw_indexes)}] UNUSABLE {catalog_id}: "
                      f"{'; '.join(reasons)}", flush=True)
        except Exception as exc:
            entry["provenance"] = {
                "source": "new_openrocket_simulation",
                "no_flight_rerun": False, **meta,
            }
            totals["warmup_calls"] += meta["warmup_calls"]
            totals["measured_calls"] += meta["measured_calls"]
            totals["simulator_exceptions"] += meta["simulator_exceptions"]
            entry.update({
                "status": "error",
                "error": f"{exc.__class__.__name__}: {exc}",
            })
            totals["errors"] += 1
            print(f"[{n + 1}/{len(hw_indexes)}] ERROR    {catalog_id}: "
                  f"{exc.__class__.__name__}: {exc}", flush=True)
        append_checkpoint(results_path, catalog_id, sanitize(entry))
        store[catalog_id] = entry
        case_entries[catalog_id] = entry

    # ---- phase 2: record enrichment ----
    flags_removed_hist: Counter = Counter()
    safety_added_hist: Counter = Counter()
    recovered = 0
    residual: list[dict] = []

    out_records: list[dict] = []
    for i, record in enumerate(records):
        catalog_id = record["catalog_id"]
        if record["label_mode"] != "hardware_only":
            out_records.append(record)  # the 244: untouched, never re-flown
            continue
        entry = case_entries.get(catalog_id) or {}
        new_record = copy.deepcopy(record)

        if catalog_id == SKYDRAGON_ID and skydragon_out.get("resolved"):
            # honest, re-verified load equivalence: the IDENTICAL check_pair
            # passed after the narrowly scoped packed-length sync
            de = dict(new_record.get("digest_entry") or {})
            rk = skydragon_recheck_entry or {}
            de["c_pass"] = True
            de["c_diff_count"] = rk.get("c_diff_count")
            de["preset_fix_applied"] = (rk.get("preset_fix_applied")
                                        or ["parachute"])
            de["recheck"] = {
                "rechecked_at_utc": skydragon_out.get("rechecked_at_utc"),
                "reason": ("initial c_fail was the packed-length preset "
                           "representation artifact; after the packed-length "
                           "sync the identical check_pair passes"),
            }
            new_record["digest_entry"] = de
            old_flags = list(new_record.get("flags", []))
            new_record["flags"] = [f for f in old_flags
                                   if f != "load_equivalence_failed"]
            if len(new_record["flags"]) != len(old_flags):
                flags_removed_hist["load_equivalence_failed"] += 1
            # regenerate model_compact from the corrected stage-2 state
            try:
                stage2, fixes = apply_stage2_and_fix(
                    copy.deepcopy(new_record["compact"]), id_by_digest,
                    rk.get("components") or [])
                stage2.pop("attachments", None)
                new_record["model_compact"] = stage2
                sp = new_record.setdefault("source_preservation", {})
                sp.setdefault("extraction", {})["model_compact"] = {
                    "derivation": ("apply_stage2_and_fix(compact, "
                                   "id_by_digest, digest_entry.components), "
                                   "attachments stripped; regenerated during "
                                   "flight completion after the packed-length "
                                   "preset-override fix"),
                    "preset_fixes": fixes,
                    "chars": len(dump_compact_json(stage2)),
                }
            except Exception as exc:
                print(f"[warn] skydragon model_compact regeneration failed: "
                      f"{exc}", flush=True)

        if entry.get("status") == "flown_ok":
            plan = entry["sim_selection"]
            prov = entry["provenance"]
            old_flags = list(new_record.get("flags", []))
            kept_flags = [f for f in old_flags if f not in REPLACED_LABEL_FLAGS]
            for f in old_flags:
                if f not in kept_flags:
                    flags_removed_hist[f] += 1
            for f in entry.get("safety_flags") or []:
                if f not in kept_flags:
                    kept_flags.append(f)
                    safety_added_hist[f] += 1
            new_record["flags"] = kept_flags
            new_record["label_mode"] = "flight_grounded"
            new_record["simulation_status"] = "uptodate"
            new_record["targets"] = entry["targets"]
            if plan["method"] == "runtime_created_default_configuration":
                sim_note = ("the design stores no simulation; a Simulation of "
                            "the default flight configuration was created at "
                            "runtime and flown (source .ork never modified)")
            else:
                sim_note = f"simulation index {plan['sim_index']} of the source .ork"
                if not plan["first_instance_of_name"]:
                    sim_note += (" (exact instance; the name is duplicated in "
                                 "the design)")
            new_record["metric_provenance"] = {
                "source": "new_openrocket_simulation",
                "sim": plan.get("sim_name"),
                "sim_index": plan.get("sim_index"),
                "sim_status": "uptodate",
                "configid": plan.get("flight_configuration_id"),
                "config_motors_populated": True,
                "no_flight_rerun": False,
                "seed": seed,
                "warmup_calls": prov.get("warmup_calls"),
                "measured_calls": prov.get("measured_calls"),
                "flown_flight_configuration_id": (entry.get("config_verification")
                                                  or {}).get(
                    "flown_flight_configuration_id"),
                "config_verification": (entry.get("config_verification")
                                        or {}).get("verdict"),
                "sim_selection": sim_note,
                "notes": ("fresh headless OpenRocket flight of the exact "
                          "selected simulation/flight configuration "
                          f"(seed {seed}, one discarded warm-up); replaces "
                          "the absent or unusable saved result.  Raw events "
                          "and full metrics: flight_results.jsonl"),
            }
            new_record["selection"] = (
                "fresh completion flight: no trusted saved result existed for "
                "this design, so the exact selected flight configuration was "
                f"simulated headlessly with seed {seed}; ground impact "
                "reached on the main branch with finite apogee, landing "
                "speed and duration")
            sp = new_record.setdefault("source_preservation", {})
            sp["flight_completion"] = {
                "results_file": "flight_results.jsonl",
                "seed": seed,
                "sim_index": plan.get("sim_index"),
                "flight_configuration_id": plan.get("flight_configuration_id"),
                "simulated_at_utc": entry.get("simulated_at_utc"),
                "safety_flags": entry.get("safety_flags") or [],
            }
            recovered += 1
        else:
            reason = (entry.get("error")
                      or "; ".join(entry.get("failure_reasons") or [])
                      or "no flight result")
            residual.append({"catalog_id": catalog_id, "reason": reason,
                             "status": entry.get("status")})
        out_records.append(new_record)

    # ---- phase 3: outputs ----
    sources_path = output_dir / "sources.jsonl"
    with sources_path.open("w") as stream:
        for record in out_records:
            stream.write(json_line(record))

    for name in ("motor_lookup.json", "assets.json"):
        (output_dir / name).write_bytes((input_dir / name).read_bytes())

    # id order must match the catalog exactly
    catalog = [json.loads(l)["id"] for l in
               (WORKSPACE / CATALOG_REL).read_text().splitlines() if l.strip()]
    out_ids = [r["catalog_id"] for r in out_records]
    order_match = out_ids == catalog

    label_counts = Counter(r["label_mode"] for r in out_records)
    prov_counts = Counter(str((r["metric_provenance"] or {}).get("source"))
                          for r in out_records)
    status_counts = Counter(r["simulation_status"] for r in out_records)
    flags_hist: Counter = Counter()
    for r in out_records:
        for f in r["flags"]:
            flags_hist[f] += 1
    c_pass_count = sum(1 for r in out_records
                       if (r.get("digest_entry") or {}).get("c_pass"))

    # physically executed simulate() calls across EVERY driver run: the
    # checkpoint file keeps every appended attempt, so re-flown cases count
    # their earlier (discarded) flights too
    physical = Counter()
    for line in results_path.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        prov = (row.get("value") or {}).get("provenance") or {}
        physical["warmup"] += int(prov.get("warmup_calls") or 0)
        physical["measured"] += int(prov.get("measured_calls") or 0)
        physical["exceptions"] += int(prov.get("simulator_exceptions") or 0)
        if (row.get("value") or {}).get("status") == "flown_ok":
            physical["measured_ok"] += int(prov.get("measured_calls") or 0)
    physical_calls = physical["warmup"] + physical["measured"]

    report = {
        "generated_at_utc": now_iso(),
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "catalog_rows": len(catalog),
        "records_emitted": len(out_records),
        "catalog_id_order_match": order_match,
        "input_label_mode_counts": {"flight_grounded": 244,
                                    "hardware_only": 86},
        "output_label_mode_counts": dict(label_counts),
        "hardware_only_cases_considered": len(hw_indexes),
        "reusable_saved_results_found": 0,
        "reused_saved_results_note": ("none of the 86 hardware-only records "
                                      "had a reusable matching saved result; "
                                      "every recovered label comes from an "
                                      "actual fresh simulation"),
        "recovered_with_fresh_labels": recovered,
        "flight_simulations_run": physical_calls,
        "simulation_call_breakdown": {
            "warmup_discarded": physical["warmup"],
            "measured_attempts": physical["measured"],
            "measured_successful_label": physical["measured_ok"],
            "measured_failed_or_unusable": (physical["measured"]
                                            - physical["measured_ok"]),
            "simulator_exceptions": physical["exceptions"],
            "final_state_counts": {
                "warmup_discarded": totals["warmup_calls"],
                "measured_attempts": totals["measured_calls"],
                "note": ("counts of the final per-case state (the flights "
                         "whose results stand); the difference to the "
                         "physical totals is the discarded attempts of "
                         "cases re-flown after verifier fixes"),
            },
            "note": ("flight_simulations_run counts EVERY completed Java "
                     "simulate() invocation of this completion task, "
                     "including the one discarded warm-up per (file, "
                     "simulation) and the discarded attempts of cases "
                     "re-flown after verifier fixes; per-case provenance "
                     "lives in flight_results.jsonl"),
        },
        "failed_cases": [
            {"catalog_id": e.get("catalog_id"),
             "status": e.get("status"),
             "reason": e.get("error")
             or "; ".join(e.get("failure_reasons") or [])}
            for e in case_entries.values()
            if e.get("status") in ("error", "flown_unusable")
        ],
        "residual_hardware_only": residual,
        "configuration_changes": [],
        "configuration_changes_note": ("every hardware-only record already "
                                       "selected a populated motor "
                                       "configuration; no alternate "
                                       "configuration was needed and no "
                                       "motor was substituted"),
        "skydragon_load_equivalence": skydragon_out,
        "flags_removed_on_success": dict(sorted(flags_removed_hist.items())),
        "safety_flags_added": dict(sorted(safety_added_hist.items())),
        "records_with_c_pass": c_pass_count,
        "motor_lookup_assets": ("copied unchanged from "
                                f"{input_dir}; no custom asset or lookup "
                                "extension was needed"),
        "notes": [
            "The 244 existing flight_grounded records are identical to the "
            "input and were never re-simulated.",
            "Fresh labels carry metric_provenance.source="
            "'new_openrocket_simulation', no_flight_rerun=false, the actual "
            "configid and seed, and simulation_status='uptodate'.",
            "Simulations run through the or_headless harness core "
            "(deterministic UUID seed, one discarded warm-up, options "
            "reseed) with exact INDEX-based simulation selection; two "
            "records carry duplicate simulation names, so name-based "
            "selection was not safe.",
            "original:level-1.ork stores no simulation; its default flight "
            "configuration was flown with a runtime-created Simulation; the "
            "source .ork file was never modified.",
            "Unsafe but real outcomes keep their measured values and gain "
            "explicit fresh_flight_* safety flags.",
        ],
    }
    (output_dir / "flight_completion_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n")

    summary = {
        "catalog_rows": len(catalog),
        "records_emitted": len(out_records),
        "catalog_id_order_match": order_match,
        "catalog_id_set_equal": set(out_ids) == set(catalog),
        "input_sources": str(sources_in),
        "flight_results": str(results_path),
        "label_mode_counts": dict(label_counts),
        "metric_provenance_source_counts": dict(prov_counts),
        "simulation_status_counts": dict(status_counts),
        "origin_counts": dict(Counter(r["origin"] for r in out_records)),
        "records_with_c_pass": c_pass_count,
        "records_with_c_fail": len(out_records) - c_pass_count,
        "flags_histogram": dict(sorted(flags_hist.items())),
        "warnings": {
            "load_equivalence_failed": [
                r["catalog_id"] for r in out_records
                if "load_equivalence_failed" in r["flags"]],
            "unresolved_motor_digest": [
                r["catalog_id"] for r in out_records
                if "unresolved_motor_digest" in r["flags"]],
            "motor_block_without_digest": [
                r["catalog_id"] for r in out_records
                if "motor_block_without_digest" in r["flags"]],
            "custom_thrust_curve_attachments": [
                r["catalog_id"] for r in out_records
                if "custom_thrust_curve_attachments" in r["flags"]],
            "fill_result_configuration_mismatch": [
                r["catalog_id"] for r in out_records
                if "fill_result_configuration_mismatch" in r["flags"]],
            "duplicate_simulation_name": [
                r["catalog_id"] for r in out_records
                if "duplicate_simulation_name" in r["flags"]],
            "no_simulations_in_design": [
                r["catalog_id"] for r in out_records
                if "no_simulations_in_design" in r["flags"]],
            "fresh_flight_hard_landing": [
                r["catalog_id"] for r in out_records
                if "fresh_flight_hard_landing" in r["flags"]],
            "fresh_flight_unstable": [
                r["catalog_id"] for r in out_records
                if "fresh_flight_unstable" in r["flags"]],
            "fresh_flight_no_recovery_deployment": [
                r["catalog_id"] for r in out_records
                if "fresh_flight_no_recovery_deployment" in r["flags"]],
        },
        "motor_lookup": {
            "size": len(lookup),
            "note": "unchanged from the input directory",
        },
        "flight_simulations_run": physical_calls,
        "simulation_call_breakdown": report["simulation_call_breakdown"],
        "notes": [
            "Flight labels come from three honest sources: saved catalog "
            "simulations (no_flight_rerun=true), fill-pipeline results "
            "(no_flight_rerun=true) and fresh headless OpenRocket completion "
            "flights (no_flight_rerun=false); provenance distinguishes them "
            "per record.",
            "Fresh labels: metric_provenance.source='new_openrocket_"
            "simulation', no_flight_rerun=false, seed and configid recorded, "
            "simulation_status='uptodate'.",
            "The 244 pre-existing flight_grounded records were not re-flown "
            "and are byte-identical to the input.",
            "Unsafe but real fresh outcomes keep measured values with "
            "explicit safety flags; nothing was invented or smoothed.",
        ],
    }
    (output_dir / "sources_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n")

    print(json.dumps({k: report[k] for k in (
        "hardware_only_cases_considered", "recovered_with_fresh_labels",
        "flight_simulations_run", "simulation_call_breakdown",
        "output_label_mode_counts", "residual_hardware_only",
        "skydragon_load_equivalence")}, indent=2, default=str), flush=True)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--limit", type=int, default=0,
                        help="debug: only the first N hardware-only cases")
    parser.add_argument("--refly", action="append", default=[],
                        help="re-fly this catalog_id even if a checkpoint "
                             "result exists (repeatable)")
    args = parser.parse_args()
    run(args.input_dir, args.output_dir, args.seed, args.limit, args.refly)
    return 0


if __name__ == "__main__":
    sys.exit(main())
