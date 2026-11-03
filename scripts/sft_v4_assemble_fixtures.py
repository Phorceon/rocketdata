#!/usr/bin/env python3
"""Representative mock fixtures for v4 assembly tests and smoke runs.

Pure, flight-free, self-contained.  These are NOT source-agent data: they
mirror the shape of the ``sft_v4_complete`` source contract (compact compact
trees, aligned load dumps, engineering stats, motor lookup, honest label
modes) so the assembler can be exercised end-to-end before the real EXACT330
sources exist.  Running this module writes a mock catalog, a mock sources
directory (sources.jsonl + motor_lookup.json + assets.json) and a full smoke
assembly under ``sftgen/out/scratch/sft_v4_complete_assembly/``.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.sft_compact_motor_ids import apply_stage2_and_fix  # noqa: E402

SMOKE_DIR = ROOT / "sftgen/out/scratch/sft_v4_complete_assembly"
MOCK_DIGEST = "0123456789abcdef0123456789abcdef"
MOCK_UNRESOLVED_DIGEST = "fedcba9876543210fedcba9876543210"
MOCK_MOTOR_ID = "Estes-C6"
MOCK_UNRESOLVED_MOTOR_ID = "Unknown-F9X"

MOCK_LOOKUP = {
    MOCK_MOTOR_ID: {
        "manufacturer": "Estes", "designation": "C6",
        "digest": MOCK_DIGEST, "diameter_m": 0.018, "length_m": 0.07,
        "total_impulse_ns": 10.0, "burn_time_s": 1.6,
        "average_thrust_n": 6.25, "in_dataset": True,
    },
    MOCK_UNRESOLVED_MOTOR_ID: {
        "manufacturer": None, "designation": None,
        "digest": MOCK_UNRESOLVED_DIGEST, "diameter_m": None, "length_m": None,
        "total_impulse_ns": None, "burn_time_s": None,
        "average_thrust_n": None, "in_dataset": False,
        "note": "unresolved custom curve; asset in assets.json",
    },
}

MOCK_ASSETS = {
    "assets": {
        MOCK_UNRESOLVED_DIGEST: {
            "kind": "custom_thrust_curve", "designation": "F9X",
            "points": [[0.0, 20.0], [1.0, 0.0]],
        },
    },
    "note": "mock sidecar",
}


def _leaf(tag, value, attrs=None):
    payload = {}
    if attrs:
        payload["attrs"] = attrs
    payload["value"] = value
    return {tag: payload}


def _material(value, density, mtype="bulk"):
    return {"material": {"attrs": {"type": mtype, "density": density},
                         "value": value}}


def mock_compact(*, digest=MOCK_DIGEST, designation="C6", fincount=3,
                 nose_shape="ogive", with_sim=True, radius=0.0124,
                 body_length=0.457, nose_length=0.07):
    """A complete single-stage compact design in the current tree contract."""
    nose = {"nosecone": {"children": [
        _leaf("finish", "smooth"),
        _material("Polystyrene", 1050.0),
        _leaf("length", nose_length),
        _leaf("thickness", 0.002),
        _leaf("shape", nose_shape),
        _leaf("shapeparameter", 1.0),
        _leaf("aftradius", radius),
        _leaf("aftshoulderradius", radius - 0.0005),
        _leaf("aftshoulderlength", 0.0254),
        _leaf("aftshoulderthickness", 0.002),
        _leaf("aftshouldercapped", False),
        _leaf("isflipped", False),
    ]}}
    body = {"bodytube": {"children": [
        _leaf("finish", "polished"),
        _material("Cardboard", 1199.7828787),
        _leaf("length", body_length),
        _leaf("thickness", 0.0005),
        _leaf("radius", radius),
        {"motormount": {"children": [
            _leaf("ignitionevent", "launch"),
            _leaf("ignitiondelay", 0.0),
            _leaf("overhang", 0.003),
            {"motor": {"attrs": {"configid": "cfg0"}, "children": [
                _leaf("type", "single"),
                {"manufacturer": {"value": "Estes"}},
                {"digest": {"value": digest}},
                _leaf("designation", designation),
                _leaf("diameter", 0.018),
                _leaf("length", 0.07),
                _leaf("delay", 5.0),
            ]}},
        ]}},
        {"subcomponents": {"children": [
            {"parachute": {"children": [
                _material("Polyethylene", 1050.0),
                _leaf("packedradius", 0.011),
                _leaf("packedlength", 0.05),
                _leaf("diameter", 0.3048),
                _leaf("linecount", 6),
                _leaf("linelength", 0.3048),
                _material("Carpet string", 1120.0, mtype="line"),
                _leaf("cordlength", 0.4),
                _leaf("deployevent", "ejection"),
                _leaf("deployaltitude", 0.0),
                _leaf("deploydelay", 5.0),
            ]}},
        ]}},
    ]}}
    fins = {"trapezoidfinset": {"children": [
        _leaf("fincount", fincount),
        _leaf("cant", 0.0),
        _leaf("crosssection", "rounded"),
        _leaf("rootchord", 0.055),
        _leaf("tipchord", 0.022),
        _leaf("height", 0.038),
        _leaf("sweeplength", 0.02),
    ]}}
    rocket = {"rocket": {"children": [
        _leaf("axialoffset", 0.0, attrs={"method": "absolute"}),
        _leaf("position", 0.0, attrs={"type": "absolute"}),
        {"motorconfiguration": {
            "attrs": {"configid": "cfg0", "default": True},
            "children": [{"stage": {"attrs": {"number": 0, "active": True}}}],
        }},
        _leaf("referencetype", "maximum"),
        {"subcomponents": {"children": [{"stage": {"children": [
            {"subcomponents": {"children": [nose, body, fins]}},
        ]}}]}},
    ]}}
    children = [rocket]
    if with_sim:
        children.append({"simulations": {"children": [{"simulation": {
            "children": [
                _leaf("simulator", "RK4Simulator"),
                _leaf("calculator", "BarrowmanCalculator"),
                {"conditions": {"children": [
                    _leaf("configid", "cfg0"),
                    _leaf("launchrodlength", 1.0),
                    _leaf("launchrodangle", 0.0),
                    _leaf("launchroddirection", 90.0),
                    _leaf("windaverage", 2.0),
                    _leaf("windturbulence", 0.1),
                    _leaf("launchaltitude", 0.0),
                    _leaf("launchlatitude", 28.61),
                    _leaf("launchlongitude", -80.6),
                    _leaf("geodeticmethod", "spherical"),
                    {"atmosphere": {"attrs": {"model": "isa"}}},
                    _leaf("timestep", 0.05),
                ]}},
            ]}}]}})
    return {"openrocket": {"attrs": {"version": 1.8}, "children": children}}


def mock_eng(*, digest=MOCK_DIGEST, designation="C6", diameter=0.0248,
             liftoff=0.065, cg=0.31, cp=0.352, static_margin=None,
             unresolved=False):
    if static_margin is None:
        static_margin = (cp - cg) / diameter
    motor = None if unresolved else {
        "designation": designation, "manufacturer": "Estes", "digest": digest,
        "diameter_m": 0.018, "length_m": 0.07, "ejection_delay_s": 5.0,
        "total_impulse_ns": 10.0, "average_thrust_n": 6.25,
        "burn_time_s": 1.6,
    }
    return {
        "liftoff_mass_kg": liftoff, "loaded_mass_kg": liftoff,
        "cg_m": cg, "cp_m": cp, "reference_diameter_m": diameter,
        "static_margin_cal": static_margin,
        "motors": [{"stage_index": 0, "mount_name": "Body tube",
                    "instance_count": 1, "motor": motor}],
        "motor_aggregates": {
            "total_impulse_ns": 10.0, "bottom_stage_average_thrust_n": 6.25,
            "thrust_to_weight": 6.25 / (liftoff * 9.80665),
            "note": "mock aggregate",
        },
    }


def mock_dump(*, radius=0.0124, body_length=0.457, nose_length=0.07,
              fincount=3):
    """Aligned headless load dump matching mock_compact's component walk."""
    position = {"x": 0.0, "y": 0.0, "z": 0.0, "weight": 0.0}
    stage_row = {"index": 0, "parent_index": -1, "cls": "AxialStage",
                "loaded": {"getLength": nose_length + body_length,
                           "getAxialOffset": 0.0, "getPosition": position,
                           "getComponentMass": 0.0, "isMotorMount": False}}
    nose_row = {"index": 1, "parent_index": 0, "cls": "NoseCone",
                "loaded": {"getLength": nose_length, "getInnerRadius": 0.0,
                           "getThickness": 0.002, "getForeRadius": 0.0,
                           "getAftRadius": radius,
                           "getAftShoulderRadius": radius - 0.0005,
                           "getAxialOffset": 0.0, "getPosition": position,
                           "getMass": 0.008, "getFinish": "NORMAL",
                           "getInstanceCount": 1, "isMotorMount": False}}
    body_row = {"index": 2, "parent_index": 0, "cls": "BodyTube",
                "loaded": {"getLength": body_length, "getOuterRadius": radius,
                           "getInnerRadius": radius - 0.0005,
                           "getThickness": 0.0005, "getForeRadius": radius,
                           "getAftRadius": radius,
                           "getAxialOffset": nose_length,
                           "getPosition": position, "getMass": 0.03,
                           "getMaterial": {"name": "Cardboard",
                                            "density": 1199.7828787,
                                            "type": "Bulk"},
                           "getFinish": "NORMAL", "isMotorMount": True,
                           "getInstanceCount": 1}}
    chute_row = {"index": 3, "parent_index": 2, "cls": "Parachute",
                "loaded": {"getLength": 0.05, "getAxialOffset": 0.1,
                           "getPosition": {"x": 0.1, "y": 0.0, "z": 0.0,
                                            "weight": 0.0},
                           "getMass": 0.02, "getInstanceCount": 1,
                           "isMotorMount": False}}
    fin_row = {"index": 4, "parent_index": 0, "cls": "TrapezoidFinSet",
               "loaded": {"getLength": 0.055, "getAxialOffset": 0.005,
                          "getPosition": {"x": 0.005, "y": 0.0, "z": 0.0,
                                           "weight": 0.0},
                          "getMass": 0.01, "getInstanceCount": fincount,
                          "isMotorMount": False}}
    return [stage_row, nose_row, body_row, chute_row, fin_row]


def mock_targets(*, apogee=82.623, landing=3.599, flight_time=30.676,
                 to_apogee=2.266, max_velocity=68.656, max_mach=0.2024,
                 wind=2.0, include_duration=True, include_wind=True):
    targets = {"apogee_m": apogee, "ground_hit_ms": landing,
               "time_to_apogee_s": to_apogee, "max_velocity_ms": max_velocity,
               "max_mach": max_mach}
    if include_duration:
        targets["flight_time_s"] = flight_time
    if include_wind:
        targets["wind_ms"] = wind
    return targets


def mock_record(catalog_id, *, source_file=None, origin="original",
                label_mode="flight_grounded", sim="Simulation 1",
                status="uptodate", targets=None, compact=None, eng=None,
                dump=None, model_compact=False, flags=None, with_sim=True,
                metric_provenance=None, source_preservation=None,
                include_model_compact=False, compact_kwargs=None,
                eng_kwargs=None, dump_kwargs=None):
    """One source-contract record for the given exact catalog id."""
    source_file = source_file or catalog_id.split(":", 1)[1]
    compact_kwargs = compact_kwargs or {}
    compact = compact or mock_compact(with_sim=with_sim, **compact_kwargs)
    dump = dump or mock_dump(**(dump_kwargs or {}))
    eng = eng or mock_eng(**(eng_kwargs or {}))
    record = {
        "catalog_id": catalog_id,
        "source_id": catalog_id,
        "source_file": source_file,
        "origin": origin,
        "file": f"/Users/aditya/mock/ork/{source_file}",
        "sim": sim if (sim is None or with_sim) else None,
        "simulation_status": status,
        "selection": "mock selection for tests",
        "targets": targets if targets is not None else {},
        "metric_provenance": metric_provenance or {
            "source": "stored simulation data of the selected configuration"},
        "compact": compact,
        "engineering": eng,
        "digest_entry": {"c_pass": True, "components": dump},
        "flags": flags or [],
        "label_mode": label_mode,
        "source_preservation": source_preservation or {
            "raw_source_kept": True},
    }
    if include_model_compact:
        id_by_digest = {entry["digest"]: mid
                        for mid, entry in MOCK_LOOKUP.items()}
        record["model_compact"] = apply_stage2_and_fix(
            compact, id_by_digest, dump)[0]
    return record


def smoke_records():
    """Eight representative records covering every assembler path.

    Geometries are deliberately varied so the roster spans several
    independent families (the alpha pair and the delta/foxtrot pair are the
    two duplicate-hardware families).
    """
    records = [
        # 1. flight-grounded, current saved result, model_compact cross-check
        mock_record("original:mock_alpha.ork", label_mode="flight_grounded",
                    status="uptodate", targets=mock_targets(),
                    include_model_compact=True),
        # 2. motor-filled twin of alpha: same hardware, one family
        mock_record("motor_filled:mock_alpha_filled.ork",
                    source_file="mock_alpha_filled.ork", origin="motor_filled",
                    label_mode="flight_grounded", status="uptodate",
                    targets=mock_targets()),
        # 3. flight-grounded but the saved result is outdated
        mock_record("original:mock_bravo.ork", label_mode="flight_grounded",
                    status="outdated", targets=mock_targets(),
                    compact_kwargs={"fincount": 4, "body_length": 0.5},
                    dump_kwargs={"fincount": 4, "body_length": 0.5}),
        # 4. hard landing: kept, with honest warnings
        mock_record("original:mock_charlie.ork", label_mode="flight_grounded",
                    status="uptodate", targets=mock_targets(landing=9.9),
                    compact_kwargs={"body_length": 0.61},
                    dump_kwargs={"body_length": 0.61}),
        # 5. hardware-only, no simulation stored at all (4 fins: own family
        #    shared only with record 7)
        mock_record("original:mock_delta.ork", label_mode="hardware_only",
                    sim=None, with_sim=False,
                    compact_kwargs={"fincount": 4},
                    dump_kwargs={"fincount": 4}),
        # 6. hardware-only, unresolved motor + untrusted stored numbers
        mock_record("original:mock_echo.ork", label_mode="hardware_only",
                    sim="Simulation 2", status="outdated", with_sim=True,
                    targets={"apogee_m": 9876.5, "ground_hit_ms": 12.5},
                    compact_kwargs={"digest": MOCK_UNRESOLVED_DIGEST,
                                    "designation": "F9X", "fincount": 4,
                                    "body_length": 0.45},
                    dump_kwargs={"fincount": 4, "body_length": 0.45},
                    eng_kwargs={"unresolved": True}),
        # 7. duplicate hardware of delta under another catalog id
        mock_record("original:mock_foxtrot.ork", label_mode="hardware_only",
                    sim=None, with_sim=False,
                    compact_kwargs={"fincount": 4},
                    dump_kwargs={"fincount": 4}),
        # 8. flight-grounded with only apogee + landing stored
        mock_record("original:mock_golf.ork", label_mode="flight_grounded",
                    status="uptodate",
                    targets=mock_targets(include_duration=False,
                                         include_wind=False),
                    compact_kwargs={"body_length": 0.5, "radius": 0.015},
                    dump_kwargs={"body_length": 0.5, "radius": 0.015},
                    eng_kwargs={"diameter": 0.030}),
    ]
    return records


def smoke_catalog():
    rows = []
    for record in smoke_records():
        rows.append({"id": record["catalog_id"],
                     "source_file": record["source_file"],
                     "origin": record["origin"]})
    return rows


def write_source_dir(directory, records=None, catalog_rows=None,
                      include_assets=True):
    """Write a mock sources directory (sources.jsonl, motor_lookup.json,
    assets.json) plus a mock catalog next to it.  Returns the paths."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    records = records if records is not None else smoke_records()
    catalog_rows = catalog_rows if catalog_rows is not None else \
        [{"id": r["catalog_id"], "source_file": r["source_file"],
          "origin": r["origin"]} for r in records]
    sources_path = directory / "sources.jsonl"
    with sources_path.open("w") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    (directory / "motor_lookup.json").write_text(
        json.dumps(MOCK_LOOKUP, ensure_ascii=False, indent=1) + "\n")
    if include_assets:
        (directory / "assets.json").write_text(
            json.dumps(MOCK_ASSETS, ensure_ascii=False, indent=1) + "\n")
    catalog_path = directory / "rockets_full.jsonl"
    with catalog_path.open("w") as stream:
        for row in catalog_rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    return sources_path, catalog_path


def main():
    from scripts.sft_v4_assemble import assemble, cached_tokenizer
    fixture_dir = SMOKE_DIR / "fixtures"
    sources_path, catalog_path = write_source_dir(fixture_dir)
    output_dir = SMOKE_DIR / "output"
    report = assemble(sources_path, output_dir, catalog_path,
                      token_limit=32768, overwrite=True,
                      tokenizer=cached_tokenizer())
    print(json.dumps({"smoke_output": str(output_dir),
                      "rows": report["rows"],
                      "label_modes": report["label_modes"],
                      "tokens": {k: report["tokens"][k] for k in
                                 ("min", "median", "max", "over_limit_count")}},
                     indent=2))


if __name__ == "__main__":
    main()
