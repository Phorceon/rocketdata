#!/usr/bin/env python3
"""Flight-free COMPLETE source recovery for ALL 330 catalog rockets (NO flights).

For EVERY record of ``data/rockets_full.jsonl`` (249 originals + 81
motor-filled, catalog order, no silent exclusions) this script emits one
source record for the SFT v4 assembler:

  * a complete compact design of the exact catalog rocket is recovered
    statically from its source .ork (``read_ork_archive`` + ``to_compact``,
    no JVM) -- stages, component order, materials, mass/CG overrides,
    relative positions, fin points, motor setup/delay and recovery are
    preserved verbatim; only documented cosmetic/audit junk and non-selected
    flight configurations are removed; no value is rounded, nothing invented;
  * flight labels are used ONLY when actually saved AND matching: a trusted
    stored simulation (``uptodate`` preferred over ``outdated``, which stays
    an explicit reference with a warning) whose flight configuration really
    has motors in the .ork, or -- for motor-filled rockets whose stored sim
    is ``notsimulated`` -- the separately persisted fill-pipeline result in
    ``fill_info``, and only when the motors written into the filled .ork
    match that exact configuration.  Everything else is an honest
    ``hardware_only`` record with empty/absent targets and no invented
    numbers;
  * static engineering stats (MassCalculator/Barrowman on the loaded source,
    resolved motors) and the digest/motor-id load-equivalence check
    (``c_pass``) run headlessly; a JVM error never prevents raw geometry
    recovery and never triggers a simulation -- the record keeps an explicit
    ``unavailable`` / ``c_pass=false`` state instead;
  * the readable motor lookup covers EVERY design-side digest, including
    motors the shipped database cannot resolve (their numbers stay absent);
    motor blocks without any digest get deterministic readable identities
    (never invented hashes) registered in the sidecar assets registry;
  * custom/base64 thrust-curve attachments never enter supervised text: the
    raw compact keeps them, the model-visible ``model_compact`` strips them,
    and the exact bytes plus the restore path are preserved in the sidecar
    ``assets.json`` registry keyed by readable motor IDs.  Custom-motor
    rockets are never dropped.

Outputs under ``sftgen/out/scratch/sft_v4_complete/``:
    sources.jsonl        EXACTLY one record per catalog row, catalog order
    motor_lookup.json     readable motor_id -> fields (one-to-one on digests)
    assets.json           exact attachment bytes + digestless identities
    sources_summary.json  counts, labels/provenance, warnings, ID equality
    eng_checkpoint.jsonl / digest_checkpoint.jsonl
                         append-only JVM-phase checkpoints (resumable)

``flight_simulations_run`` is always 0: no ``simulate()`` call exists in this
script, only loaders and static calculators.
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import math
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.sft_compact_design import (  # noqa: E402
    CONFIGID_ELEMENTS,
    CONFIGID_PLACEHOLDER,
    REMOVED_ATTRS,
    REMOVED_TAGS,
    CompactError,
    _compact_node,
    _kept_attrs,
    diff_trees,
    dump_compact_json,
    from_compact,
    static_check,
    to_compact,
)
from scripts.sft_compact_motor_ids import (  # noqa: E402
    apply_stage2_and_fix,
    build_motor_lookup,
    build_stage2_design,
    restore_motor_digests,
)
from scripts.sft_compact_reasoning import (  # noqa: E402
    child,
    find_rocket,
    stage_wrappers,
    value_of,
    walk_components,
)
from scripts.sft_full_fidelity_support.ork_archive import (  # noqa: E402
    bundle_entries_to_json,
    partition_bundle_entries,
    read_ork_archive,
)
from scripts.sft_full_fidelity_support.xml_tree import (  # noqa: E402
    find_simulation_nodes,
    simulation_config_id,
    simulation_field,
)

WORKSPACE = ROOT.parents[1]
CATALOG_REL = "data/rockets_full.jsonl"
STAGE_DIR = ROOT / "sftgen/out/scratch/sft_compact_20261103"
DEFAULT_OUTPUT_DIR = ROOT / "sftgen/out/scratch/sft_v4_complete"
V3_TRAIN = ROOT / "new_results/sft_v3.jsonl"
V3_TEST = ROOT / "new_results/sft_test_v3.jsonl"
V3_LOOKUP = ROOT / "new_results/sft_v3_motor_lookup.json"
MOTOR_DB = STAGE_DIR / "motor_db_full.json"

TRUSTED_STATUSES = ("uptodate", "outdated")
STATUS_UNAVAILABLE = "unavailable"

TARGET_SOURCES = (
    ("apogee_m", "maxaltitude"),
    ("ground_hit_ms", "groundhitvelocity"),
    ("flight_time_s", "flighttime"),
    ("time_to_apogee_s", "timetoapogee"),
    ("max_velocity_ms", "maxvelocity"),
    ("max_mach", "maxmach"),
)
FILL_TARGET_SOURCES = (
    ("apogee_m", "apogee_m"),
    ("ground_hit_ms", "ground_hit_mps"),
    ("flight_time_s", "flight_time_s"),
    ("max_velocity_ms", "max_velocity_mps"),
    ("rail_exit_ms", "rail_exit_mps"),
)

PRESERVED_FIELDS = (
    "stages", "component_order", "materials", "mass_and_cg_overrides",
    "relative_positions", "fin_points", "motor_setup_and_delay", "recovery",
    "selected_flight_configuration",
)


# --------------------------------------------------------------------------
# pure helpers
# --------------------------------------------------------------------------

def finite(value: Any) -> float | None:
    """float(value) when the result is a finite number, else None.

    Booleans are NOT numbers here: True would silently become 1.0.
    """
    if isinstance(value, bool):
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def sim_targets(sim: dict) -> dict:
    """Saved flight metrics of one catalog simulation; absent stays absent."""
    fd = sim.get("flightdata") or {}
    cond = sim.get("conditions") or {}
    targets: dict[str, float] = {}
    for key, attr in TARGET_SOURCES:
        value = finite(fd.get(f"@{attr}"))
        if value is not None:
            targets[key] = value
    wind = finite(cond.get("windaverage"))
    if wind is not None:
        targets["wind_ms"] = wind
    return targets


def fill_targets(fill_info: dict) -> dict:
    """Persisted fill-pipeline result metrics; only keys that exist there."""
    targets: dict[str, float] = {}
    for key, attr in FILL_TARGET_SOURCES:
        value = finite(fill_info.get(attr))
        if value is not None:
            targets[key] = value
    return targets


def source_key(file: str) -> str:
    """Catalog identity of a source path: basename, _filled suffix stripped."""
    name = Path(file).name
    if name.lower().endswith("_filled.ork"):
        return name[:-len("_filled.ork")] + ".ork"
    return name


def source_path_for(record: dict, workspace: Path) -> Path:
    """Original sources live in <workspace>/ork, filled ones in ork_filled."""
    name = record["source_file"]
    if record.get("origin") == "motor_filled":
        return workspace / "ork_filled" / (name[:-4] + "_filled.ork")
    return workspace / "ork" / name


def populated_motor_configs(tree: dict) -> set[str]:
    """Config ids that have an actual motor block on some mount in the XML."""
    configs: set[str] = set()

    def walk(node: dict) -> None:
        for child_node in node.get("children") or []:
            if child_node.get("tag") == "motormount":
                for element in child_node.get("children") or []:
                    if element.get("tag") != "motor":
                        continue
                    configid = (element.get("attrs") or {}).get("configid")
                    kids = {k.get("tag") for k in element.get("children") or []}
                    if configid and ({"digest", "designation"} & kids):
                        configs.add(str(configid))
            walk(child_node)

    walk(tree)
    return configs


def xml_sim_name(sim_node: dict) -> str | None:
    name = next((c for c in sim_node.get("children") or []
                 if c.get("tag") == "name"), None)
    return name.get("text") if name is not None else None


def default_configid(tree: dict) -> str | None:
    """The rocket's default flight configuration id (attr default="true")."""
    for top in tree.get("children") or []:
        if top.get("tag") != "rocket":
            continue
        configs = [c for c in top.get("children") or []
                   if c.get("tag") == "motorconfiguration"]
        for c in configs:
            if str((c.get("attrs") or {}).get("default")) == "true":
                return str((c.get("attrs") or {}).get("configid"))
        for c in configs:
            cfg = (c.get("attrs") or {}).get("configid")
            if cfg is not None:
                return str(cfg)
    return None


def config_motor_blocks(tree: dict, configid: str) -> list[dict]:
    """Design-side motor blocks of one flight configuration (document order)."""
    blocks: list[dict] = []

    def walk(node: dict) -> None:
        for c in node.get("children") or []:
            if (c.get("tag") == "motor"
                    and str((c.get("attrs") or {}).get("configid")) == configid):
                fields = {k.get("tag"): k.get("text")
                          for k in c.get("children") or []}
                blocks.append({
                    "manufacturer": fields.get("manufacturer"),
                    "designation": fields.get("designation"),
                    "digest": fields.get("digest"),
                    "diameter": fields.get("diameter"),
                    "length": fields.get("length"),
                    "delay": fields.get("delay"),
                })
            walk(c)

    walk(tree)
    return blocks


def json_line(value: dict) -> str:
    """Strict JSON line; raises ValueError on NaN/Infinity leaves."""
    return json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n"


def _fs_safe_key(key: str) -> str:
    """Filesystem-safe form of a checkpoint/record key."""
    return "".join(c if (c.isalnum() or c in "-_.") else "_" for c in key)


# --------------------------------------------------------------------------
# fill-pipeline result matching (motor_filled rockets, notsimulated XML)
# --------------------------------------------------------------------------

def _norm_manufacturer(name: Any) -> str:
    return re.sub(r"\s+", " ", str(name or "").strip().lower().rstrip("."))


def _manufacturer_matches(fill: Any, design: Any) -> bool:
    a, b = _norm_manufacturer(fill), _norm_manufacturer(design)
    if not a or not b:
        return False
    return a == b or a.startswith(b + " ") or b.startswith(a + " ")


def parse_fill_parts(designation: Any) -> list[tuple[str, float | None]]:
    """Split a fill designation into per-motor (designation, delay) parts.

    Handles both stored shapes: "G71R-10.5 + H225BL-0.0" (delay suffixes,
    spaced plus) and "J350-SF+I65W" (plain designations, bare plus).  A
    trailing "-<float>" is a delay suffix only when it parses as a number,
    so "J615ST-20A" stays one designation.
    """
    parts: list[tuple[str, float | None]] = []
    for raw in str(designation or "").split("+"):
        p = raw.strip()
        if not p:
            continue
        m = re.match(r"^(.+)-(\d+(?:\.\d+)?)$", p)
        if m:
            parts.append((m.group(1).strip(), float(m.group(2))))
        else:
            parts.append((p, None))
    return parts


def _designation_matches(a: str, b: str) -> bool:
    return a == b or a.startswith(b) or b.startswith(a)


def match_fill_configuration(fill_info: dict,
                             design_motors: list[dict]) -> tuple[bool, str]:
    """Does the persisted fill result describe THIS exact motor set?

    ``design_motors`` are the motor blocks of one flight configuration in the
    filled .ork.  The fill designation may combine sustainer + booster
    ("J350-SF+I65W") and the fill manufacturer may name only the first motor;
    delays must agree with the design (booster delay 0, sustainer delay =
    fill ``delay_s``).  Any inconsistency means the persisted metrics are NOT
    used: no silent substitution, never a different motor.
    """
    if not fill_info:
        return False, "no fill_info recorded"
    parts = parse_fill_parts(fill_info.get("designation"))
    if len(parts) != len(design_motors):
        return False, (f"fill lists {len(parts)} motor(s), the design "
                       f"configuration has {len(design_motors)}")
    used = [False] * len(design_motors)
    for des, part_delay in parts:
        idx = next((j for j, dm in enumerate(design_motors)
                    if not used[j]
                    and dm["designation"] is not None
                    and _designation_matches(des, str(dm["designation"]))), None)
        if idx is None:
            return False, (f"fill motor {des!r} matches no design motor "
                           f"of this configuration")
        used[idx] = True
        if part_delay is not None:
            design_delay = finite(design_motors[idx].get("delay"))
            if design_delay is None or abs(design_delay - part_delay) > 1e-9:
                return False, (f"fill motor {des!r} delay {part_delay} "
                               f"!= design delay {design_motors[idx].get('delay')!r}")
    delays = [finite(dm.get("delay")) for dm in design_motors]
    delays = [d for d in delays if d is not None]
    fill_delay = finite(fill_info.get("delay_s"))
    if fill_delay is None:
        return False, "fill_info has no finite delay_s"
    if not delays:
        return False, "design motors carry no delay to verify against"
    if abs(max(delays) - fill_delay) > 1e-9:
        return False, (f"fill delay_s {fill_delay} != design sustainer delay "
                       f"{max(delays)}")
    fill_mans = [m.strip() for m in
                 str(fill_info.get("manufacturer") or "").split("+") if m.strip()]
    design_mans = [str(dm.get("manufacturer")) for dm in design_motors
                   if dm.get("manufacturer") is not None]
    if not design_mans:
        return False, "design motors carry no manufacturer to verify against"
    for fm in fill_mans:
        if not any(_manufacturer_matches(fm, dm) for dm in design_mans):
            return False, (f"fill manufacturer {fm!r} matches no design "
                           f"motor manufacturer {design_mans}")
    detail = (f"{len(parts)} motor(s) "
              + "+".join(str(dm.get("designation")) for dm in design_motors)
              + f", sustainer delay {fill_delay}s")
    return True, detail


# --------------------------------------------------------------------------
# selection: which stored sim / configuration defines the record
# --------------------------------------------------------------------------

def _catalog_xml_agree(catalog_sim: dict, node: dict) -> bool:
    """Catalog entry i mirrors XML simulation node i (they are index-paired)."""
    status = (node.get("attrs") or {}).get("status")
    return (catalog_sim.get("name") == xml_sim_name(node)
            and catalog_sim.get("@status") == status
            and (catalog_sim.get("conditions") or {}).get("configid")
            == simulation_config_id(node))


def select_simulation(catalog_sims: list[dict], tree: dict, origin: str,
                      fill_info: dict | None) -> dict:
    """Choose the stored simulation / configuration that defines the record.

    Tier 1 (flight_grounded): trusted saved result (uptodate before outdated)
    with finite positive apogee, finite nonnegative landing speed and motors
    actually populated for its configuration, catalog entry agreeing with
    its XML node.
    Tier 2 (flight_grounded, motor_filled only): the stored sim is
    notsimulated but the fill pipeline persisted real metrics for exactly
    this motor configuration in fill_info -- use them with explicit
    provenance when they match the motors in the file.
    Tier 3 (hardware_only): no trusted matching metrics; pick the sim that
    best defines the hardware (populated config, default config, trusted
    status, then document order).  No labels are emitted.
    Config-only: no simulations at all; the default configuration defines
    the design and the record is hardware_only.

    Returns a dict with sim_index/name/status/configid, targets, provenance,
    selection rationale, label_mode and source flags.  Never raises and
    never fabricates a metric.
    """
    nodes = find_simulation_nodes(tree)
    populated = populated_motor_configs(tree)
    default_cfg = default_configid(tree)
    out: dict[str, Any] = {
        "sim_index": None, "name": None, "status": None, "configid": None,
        "targets": {}, "label_mode": "hardware_only", "flags": [],
        "provenance": {"source": None, "no_flight_rerun": True,
                       "notes": ""}, "selection": "",
    }

    # ---- tier 1: trusted, matching, populated saved results ----
    candidates: list[tuple] = []
    mismatches = 0
    for index, sim in enumerate(catalog_sims):
        status = sim.get("@status")
        if status not in TRUSTED_STATUSES:
            continue
        configid = str((sim.get("conditions") or {}).get("configid"))
        if configid not in populated:
            continue
        if index >= len(nodes) or not _catalog_xml_agree(sim, nodes[index]):
            mismatches += 1
            continue
        targets = sim_targets(sim)
        if (targets.get("apogee_m") is None or targets["apogee_m"] <= 0
                or targets.get("ground_hit_ms") is None
                or targets["ground_hit_ms"] < 0):
            continue
        candidates.append((0 if status == "uptodate" else 1,
                           0 if "flight_time_s" in targets else 1,
                           index, sim, targets, configid, status))
    if candidates:
        candidates.sort(key=lambda c: c[:3])
        _r, _d, index, sim, targets, configid, status = candidates[0]
        name = sim.get("name")
        others = len(candidates) - 1
        out.update({
            "sim_index": index, "name": name, "status": status,
            "configid": configid, "targets": targets,
            "label_mode": "flight_grounded",
            "provenance": {
                "source": "catalog_simulation", "sim": name,
                "sim_status": status, "configid": configid,
                "config_motors_populated": True, "no_flight_rerun": True,
                "notes": "saved flight metrics of the stored simulation; "
                         "never re-simulated",
            },
            "selection": (
                f"trusted saved result: status={status}, finite saved apogee "
                f"and landing speed, motors populated for configid "
                f"{configid[:8]}..."
                + (f"; preferred over {others} other eligible saved "
                   f"simulation(s) by (status, finite duration, order)"
                   if others else "; only eligible saved simulation")),
        })
        if status == "outdated":
            out["flags"].append("outdated_saved_results_reference_only")
        if status != "uptodate":
            out["flags"].append("saved_simulation_not_uptodate")
        return out

    # ---- tier 3 ranking used for configuration selection ----
    def config_rank(index: int, sim: dict) -> tuple:
        configid = (sim.get("conditions") or {}).get("configid")
        status = sim.get("@status")
        return (0 if configid in populated else 1,
                0 if configid == default_cfg else 1,
                0 if status in TRUSTED_STATUSES else 1,
                index)

    ordered = sorted(range(len(catalog_sims)), key=lambda i: config_rank(
        i, catalog_sims[i])) if catalog_sims else []

    # ---- tier 2: persisted fill-pipeline result for the exact motors ----
    if origin == "motor_filled" and fill_info:
        for index in ordered:
            sim = catalog_sims[index]
            configid = str((sim.get("conditions") or {}).get("configid"))
            design_motors = config_motor_blocks(tree, configid)
            if not design_motors:
                continue
            ok, detail = match_fill_configuration(fill_info, design_motors)
            if ok:
                name = sim.get("name")
                status = sim.get("@status")
                out.update({
                    "sim_index": index, "name": name, "status": status,
                    "configid": configid,
                    "targets": fill_targets(fill_info),
                    "label_mode": "flight_grounded",
                    "provenance": {
                        "source": "fill_pipeline", "sim": name,
                        "sim_status": status, "configid": configid,
                        "config_motors_populated": True,
                        "no_flight_rerun": True,
                        "fill_match": detail,
                        "notes": "the fill pipeline's separately persisted "
                                 "result for this exact motor configuration; "
                                 "the stored XML sim was not re-run",
                    },
                    "selection": (
                        f"motor-filled design: stored sim status={status}; "
                        f"real metrics recovered from the persisted "
                        f"fill-pipeline result after verifying the motors "
                        f"in the file match it ({detail})"),
                })
                out["flags"].append("fill_pipeline_metrics_not_resimulated")
                if status != "uptodate":
                    out["flags"].append("saved_simulation_not_uptodate")
                return out
            out["flags"].append("fill_result_configuration_mismatch")
            out["provenance"]["fill_match_failure"] = detail
            out["provenance"]["notes"] = (
                f"fill-pipeline result NOT used: {detail}")
            break

    # ---- tier 3 / config-only: hardware_only ----
    if ordered:
        index = ordered[0]
        sim = catalog_sims[index]
        configid = (sim.get("conditions") or {}).get("configid")
        name = sim.get("name")
        status = sim.get("@status")
        # keep any finite trusted partial metrics for the record, honestly
        targets: dict[str, float] = {}
        if status in TRUSTED_STATUSES and configid in populated:
            targets = sim_targets(sim)
            if targets:
                out["flags"].append("saved_metrics_partial_no_landing_speed")
        if mismatches:
            out["flags"].append("catalog_xml_sim_mismatch")
        duplicate = sum(1 for n in nodes if xml_sim_name(n) == name) > 1
        if duplicate:
            out["flags"].append("duplicate_simulation_name")
        note = ("no trusted saved flight result for this design; "
                "hardware-only record, no flight labels")
        if targets:
            note = ("trusted saved metrics exist but lack the finite "
                    "positive-apogee AND landing-speed pair a label needs; "
                    "kept as reference only, no flight labels")
        out.update({
            "sim_index": index, "name": name, "status": status,
            "configid": configid, "targets": targets,
            "label_mode": "hardware_only",
            "provenance": {
                "source": None, "sim": name, "sim_status": status,
                "configid": configid,
                "config_motors_populated": configid in populated,
                "no_flight_rerun": True,
                "notes": note,
            },
            "selection": (
                "no trusted saved result usable as a label; simulation "
                f"{name!r} (status={status}) selected only to define the "
                f"flight configuration (configid {str(configid)[:8]}..., "
                f"motors populated={configid in populated}) for static "
                "hardware extraction"),
        })
        return out

    # no simulations at all: the default configuration defines the design
    out.update({
        "sim_index": None, "name": None, "status": STATUS_UNAVAILABLE,
        "configid": default_cfg, "targets": {}, "label_mode": "hardware_only",
        "provenance": {
            "source": None, "sim": None, "sim_status": None,
            "configid": default_cfg,
            "config_motors_populated": default_cfg in populated,
            "no_flight_rerun": True,
            "notes": "the design stores no simulation; the default flight "
                     "configuration defines the hardware; hardware-only "
                     "record",
        },
        "selection": "no simulations recorded; default flight configuration "
                     f"{str(default_cfg)[:8]}... defines the hardware",
    })
    out["flags"].append("no_simulations_in_design")
    return out


# --------------------------------------------------------------------------
# static extraction (no JVM anywhere)
# --------------------------------------------------------------------------

def filter_simulations(tree: dict, keep_index: int) -> dict:
    """Keep only simulation node keep_index inside <simulations> (deep copy)."""
    out = copy.deepcopy(tree)

    def walk(node: dict) -> None:
        kids = node.get("children") or []
        for i, c in enumerate(kids):
            if c.get("tag") == "simulations":
                sims = [s for j, s in enumerate(c.get("children") or [])
                        if j == keep_index]
                kept = dict(c)
                kept["children"] = sims
                kids[i] = kept
            walk(c)

    walk(out)
    return out


def read_full_design(source_path: Path, sim_index: int | None) -> dict:
    """Full-fidelity design dict for one stored sim (or the whole rocket).

    With ``sim_index`` the parameter tree keeps ONLY that simulation node
    (catalog entries and XML nodes are index-paired), so duplicate sim names
    can never compact the wrong instance.  Without it (no simulations in the
    file) the tree is returned unchanged and the default configuration
    defines the design.  Cached flightdata is always stripped.
    """
    tree, entries, container = read_ork_archive(source_path)
    engineering_bytes, _cosmetic = partition_bundle_entries(entries)
    root_attrs = tree.get("attrs") or {}
    if sim_index is None:
        return {
            "schema_version": "full-fidelity-1.0",
            "openrocket_version": root_attrs.get("version"),
            "ork_container": container,
            "parameter_tree": tree,
            "bundle_entries": bundle_entries_to_json(engineering_bytes),
            "selected_simulation": None,
        }
    nodes = find_simulation_nodes(tree)
    if sim_index >= len(nodes):
        raise CompactError(f"{source_path}: simulation index {sim_index} "
                           f"out of range ({len(nodes)} sims)")
    node = nodes[sim_index]
    name = xml_sim_name(node)
    if name is None:
        raise CompactError(f"{source_path}: simulation node {sim_index} "
                           "has no <name>")
    fcid = simulation_config_id(node)
    return {
        "schema_version": "full-fidelity-1.0",
        "openrocket_version": root_attrs.get("version"),
        "ork_container": container,
        "parameter_tree": filter_simulations(tree, sim_index),
        "bundle_entries": bundle_entries_to_json(engineering_bytes),
        "selected_simulation": {
            "name": name,
            "index": sim_index,
            "flight_configuration_id": fcid,
            "simulator": simulation_field(node, "simulator"),
            "calculator": simulation_field(node, "calculator"),
        },
    }


def to_compact_config(full_design: dict, fcid: str | None) -> dict:
    """Compact a design that has NO simulation: the given configuration
    (normally the default one) selects which motor/deployment/separation/
    ignition configuration blocks survive.  Same documented removals and
    placeholder rules as ``to_compact``; no <simulations> wrapper is kept."""
    tree = full_design.get("parameter_tree")
    if not tree or tree.get("tag") != "openrocket":
        raise CompactError("design has no openrocket parameter_tree")
    root_children: list = []
    for child in tree.get("children") or []:
        tag = child["tag"]
        if tag == "simulations":
            continue  # nothing to keep: this design stores no simulation
        kept = _compact_node(child, fcid=fcid, parent_tag=None)
        if kept is not None:
            root_children.append({tag: kept})
    root_attrs = _kept_attrs("openrocket", tree.get("attrs"))
    openrocket: dict[str, Any] = {}
    if root_attrs:
        openrocket["attrs"] = root_attrs
    openrocket["children"] = root_children
    compact: dict[str, Any] = {"openrocket": openrocket}
    attachments = full_design.get("bundle_entries") or {}
    if attachments:
        compact["attachments"] = {
            name: {"data_base64": meta["data"]}
            for name, meta in attachments.items()
            if name.startswith("thrustcurves/")
        }
    return compact


def normalize_config_tree(tree: dict, fcid: str | None) -> dict:
    """Expected tree after the documented removals for a no-sim design."""
    kept_tree = {
        "tag": tree["tag"],
        "attrs": {k: v for k, v in (tree.get("attrs") or {}).items()
                  if k not in (REMOVED_ATTRS.get("openrocket") or set())},
        "text": tree.get("text"),
        "children": [],
    }

    def keep(node: dict, parent_tag: str | None) -> dict | None:
        tag = node["tag"]
        if tag in REMOVED_TAGS or tag == "simulations":
            return None
        out = {
            "tag": tag,
            "attrs": {k: v for k, v in (node.get("attrs") or {}).items()
                      if k not in (REMOVED_ATTRS.get(tag) or set())},
            "text": node.get("text"),
            "children": [],
        }
        if tag in CONFIGID_ELEMENTS:
            cfg = out["attrs"].get("configid")
            if cfg is None or cfg != fcid:
                return None
            out["attrs"]["configid"] = CONFIGID_PLACEHOLDER
        for child in node.get("children") or []:
            if child["tag"] == "flightdata":
                continue
            kept_child = keep(child, tag)
            if kept_child is not None:
                out["children"].append(kept_child)
        return out

    for child in tree.get("children") or []:
        kept = keep(child, kept_tree["tag"])
        if kept is not None:
            kept_tree["children"].append(kept)
    return kept_tree


def static_check_config(full_design: dict, fcid: str | None) -> dict:
    """Flight-free round-trip gate for a no-sim design (mirrors static_check)."""
    try:
        compact = to_compact_config(full_design, fcid)
        rebuilt = from_compact(compact)
    except (CompactError, KeyError, ValueError) as exc:
        return {"pass": False, "differences": [
            f"conversion failed: {exc.__class__.__name__}: {exc}"],
            "dropped_attachments": []}
    expected = normalize_config_tree(full_design["parameter_tree"], fcid)
    diffs = diff_trees(expected, rebuilt["parameter_tree"])

    def count_sims(node: dict) -> int:
        n = 0
        for c in node.get("children") or []:
            n += 1 if c.get("tag") == "simulation" else 0
            n += count_sims(c)
        return n

    if count_sims(rebuilt["parameter_tree"]) != 0:
        diffs.append("simulations: no simulation may survive in a no-sim "
                     "design")
    dropped = [name for name in (full_design.get("bundle_entries") or {})
               if not name.startswith("thrustcurves/")]
    return {"pass": not diffs, "differences": diffs,
            "dropped_attachments": sorted(dropped)}


# --------------------------------------------------------------------------
# design-side motors
# --------------------------------------------------------------------------

def design_mounts(compact: dict) -> list[dict]:
    """All motor mounts of the compact design in DFS document order.

    The loader walks the same order (stage children, then subcomponents), so
    ``engineering['motors'][j]`` pairs with mount j.
    """
    mounts: list[dict] = []
    rocket = find_rocket(compact)
    for _stage_tag, stage in stage_wrappers(rocket):
        for tag, payload, _depth in walk_components(stage):
            mount = child(payload, "motormount")
            if mount is None:
                continue
            mounts.append({"component_tag": tag,
                           "motor": child(mount, "motor")})
    return mounts


def compact_motor_digests(compact: dict) -> list[str]:
    """Design-side motor digests in DFS order (mounts with a motor block)."""
    digests = []
    for mount in design_mounts(compact):
        motor = mount["motor"]
        if motor is not None:
            digest = value_of(child(motor, "digest"))
            if digest is not None:
                digests.append(str(digest))
    return digests


def _identity_for_block(motor: dict) -> str:
    """Deterministic readable identity for a digest-less motor block."""
    manufacturer = str(value_of(child(motor, "manufacturer")) or "Unknown")
    designation = str(value_of(child(motor, "designation")) or "Motor")

    def clean(s: str) -> str:
        s = re.sub(r"[^A-Za-z0-9.+ -]", "_", s).strip()
        return s or "X"

    return f"{clean(manufacturer)}-{clean(designation)}"


def digestless_identities(payloads: list[dict]) -> dict[str, dict]:
    """Readable registry entries for design motor blocks without a digest.

    Identity is derived from the block's own text (manufacturer,
    designation, dimensions) -- deterministic and readable, never an
    invented hash.  The digest the loader resolved such a block to (when it
    does resolve one from the database) is recorded as metadata.
    """
    registry: dict[str, dict] = {}
    for payload in payloads:
        compact = payload.get("compact") or {}
        catalog_id = payload.get("catalog_id")
        if not compact:
            continue
        eng_motors = (payload.get("engineering") or {}).get("motors") or []
        for j, mount in enumerate(design_mounts(compact)):
            motor = mount["motor"]
            if motor is None or value_of(child(motor, "digest")) is not None:
                continue
            diameter = value_of(child(motor, "diameter"))
            length = value_of(child(motor, "length"))
            delay = value_of(child(motor, "delay"))
            identity = _identity_for_block(motor)
            entry = registry.setdefault(identity, {
                "identity": identity,
                "manufacturer": str(value_of(child(motor, "manufacturer"))),
                "designation": str(value_of(child(motor, "designation"))),
                "diameter_m": finite(diameter) if diameter is not None else None,
                "length_m": finite(length) if length is not None else None,
                "delay_s": finite(delay) if delay is not None else None,
                "resolved_digest": None,
                "used_by": [],
            })
            existing = (entry["diameter_m"], entry["length_m"], entry["delay_s"])
            current = (finite(diameter) if diameter is not None else None,
                       finite(length) if length is not None else None,
                       finite(delay) if delay is not None else None)
            if existing != current:
                suffix = ""
                if current[0] is not None and current[1] is not None:
                    suffix = (f"-{current[0] * 1000:g}x"
                              f"{current[1] * 1000:g}mm")
                identity2 = f"{identity}{suffix}" if suffix else f"{identity}-2"
                entry = registry.setdefault(identity2, {
                    "identity": identity2,
                    "manufacturer": entry["manufacturer"],
                    "designation": entry["designation"],
                    "diameter_m": current[0], "length_m": current[1],
                    "delay_s": current[2], "resolved_digest": None,
                    "used_by": [],
                })
            if j < len(eng_motors):
                resolved = (eng_motors[j] or {}).get("motor") or {}
                if resolved.get("digest") and not entry["resolved_digest"]:
                    entry["resolved_digest"] = str(resolved["digest"])
            if catalog_id not in entry["used_by"]:
                entry["used_by"].append(catalog_id)
    return registry


def collect_dataset_motor_entries(payloads: list[dict]) -> list[dict]:
    """One entry per distinct design-side digest across ALL source records.

    Identity comes from the design's motor blocks; impulse/burn-time/thrust
    numbers come from the RESOLVED motor of the SAME mount in the static
    engineering stats, paired by mount index (the loaded document walks the
    same DFS order).  A digest whose motor fails to resolve in the loaded
    document (engineering motor is None) is still collected with the
    numbers absent: every design-side digest needs a readable ID and no
    rocket may be dropped for an unresolved motor.  Numbers only steer sort
    order and lookup metadata; identity is the design block itself.
    """
    blocks: dict[str, set] = {}
    resolved_by_digest: dict[str, dict] = {}
    for payload in payloads:
        compact = payload.get("compact") or {}
        if not compact:
            continue
        eng_motors = (payload.get("engineering") or {}).get("motors") or []
        for j, mount in enumerate(design_mounts(compact)):
            motor = mount["motor"]
            if motor is None:
                continue
            digest = value_of(child(motor, "digest"))
            if digest is None:
                continue  # digest-less blocks: readable identities registry
            digest = str(digest)
            block = {
                "manufacturer": str(value_of(child(motor, "manufacturer"))),
                "designation": str(value_of(child(motor, "designation"))),
                "diameter_m": finite(value_of(child(motor, "diameter"))),
                "length_m": finite(value_of(child(motor, "length"))),
            }
            blocks.setdefault(digest, set()).add(tuple(sorted(block.items())))
            rdata = (eng_motors[j].get("motor") or {}) if j < len(eng_motors) else {}
            resolved_by_digest.setdefault(digest, {
                "total_impulse_ns": rdata.get("total_impulse_ns"),
                "burn_time_s": rdata.get("burn_time_s"),
                "average_thrust_n": rdata.get("average_thrust_n"),
            })
    entries = []
    for digest in sorted(blocks):
        canonical = dict(min(blocks[digest]))
        canonical.update(resolved_by_digest.get(digest, {}))
        canonical["digest"] = digest
        entries.append(canonical)
    return entries


# --------------------------------------------------------------------------
# no-simulation JVM helpers (static load only, never a flight)
# --------------------------------------------------------------------------

def engineering_stats_default(ork_path: Path) -> dict:
    """engineering_stats for a design with no stored simulation: static
    MassCalculator/Barrowman numbers of the DEFAULT flight configuration."""
    import jpype
    from jpype import JClass

    from scripts import or_headless as oh
    from scripts.sft_compact_stage1_engineering import G0, STAGE_CLASS_NAMES, _jfloat

    oh._boot_or()
    doc = oh._helper().load_doc(str(ork_path))
    rocket = doc.getRocket()
    config = rocket.getSelectedConfiguration()
    fcid = config.getFlightConfigurationID()

    MassCalculator = JClass("info.openrocket.core.masscalc.MassCalculator")
    Barrowman = JClass("info.openrocket.core.aerodynamics.BarrowmanCalculator")
    FlightConditions = JClass("info.openrocket.core.aerodynamics.FlightConditions")
    WarningSet = JClass("info.openrocket.core.logging.WarningSet")

    errors: list[str] = []
    out: dict[str, Any] = {"calculation_basis": "default flight configuration "
                         "(no stored simulation in the design)"}
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

    motors: list[dict] = []
    bottom_index = -1

    def walk(component, si):
        nonlocal bottom_index
        for ch in component.getChildren():
            name = str(ch.getClass().getSimpleName())
            child_si = si + 1 if name in STAGE_CLASS_NAMES else si
            bottom_index = max(bottom_index, child_si)
            if hasattr(ch, "isMotorMount") and ch.isMotorMount():
                entry: dict[str, Any] = {"stage_index": child_si,
                                         "mount_name": None,
                                         "instance_count": None}
                try:
                    entry["mount_name"] = str(ch.getName())
                    entry["instance_count"] = int(ch.getInstanceCount())
                    mcfg = ch.getMotorConfig(fcid)
                    motor = mcfg.getMotor()
                    if motor is None:
                        entry["motor"] = None
                        entry["reason"] = ("no motor configured for the "
                                           "default flight configuration")
                    else:
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
                motors.append(entry)
            walk(ch, child_si)

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
        "note": "totals over the DEFAULT configuration's motors from the "
                "resolved motor instances; no simulation involved",
    }
    if errors:
        out["errors"] = errors
    return out


def check_pair_config(source_path: Path, compact: dict, workdir: Path,
                      id_by_digest: dict, digest_by_id: dict) -> dict:
    """Actual load equivalence for a no-sim design (mirrors check_pair).

    doc_a: the compact exactly as written; doc_c: the final model-visible
    state (motor ids, presets/cosmetics stripped) restored to digests through
    the lookup.  c_pass is TRUE only when BOTH loads agree with the as-is
    source document AND the round trip: actual loaded state, no simulation.
    """
    from scripts import or_headless as oh
    from scripts.sft_compact_digest_check import (
        component_rows,
        diff_multisets,
        multiset,
    )
    from scripts.sft_full_fidelity_extract import build_ork

    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    helper = oh._helper()

    design_a = from_compact(copy.deepcopy(compact))
    path_a = workdir / "nosim_a.ork"
    build_ork(design_a, path_a)
    doc_a = helper.load_doc(str(path_a))
    fcid_a = str(doc_a.getRocket().getSelectedConfiguration()
                 .getFlightConfigurationID())
    rows_a = component_rows(doc_a, fcid_a)

    stage2 = build_stage2_design(copy.deepcopy(compact), id_by_digest)
    design_c = from_compact(stage2)
    restore_motor_digests(design_c["parameter_tree"], digest_by_id)
    path_c = workdir / "nosim_c.ork"
    build_ork(design_c, path_c)
    doc_c = helper.load_doc(str(path_c))
    fcid_c = str(doc_c.getRocket().getSelectedConfiguration()
                 .getFlightConfigurationID())
    rows_c = component_rows(doc_c, fcid_c)

    doc_s = helper.load_doc(str(source_path))
    fcid_s = str(doc_s.getRocket().getSelectedConfiguration()
                 .getFlightConfigurationID())
    rows_s = component_rows(doc_s, fcid_s)

    diffs_sc = diff_multisets(multiset(rows_s, with_preset=True),
                              multiset(rows_a, with_preset=True))
    diffs_c = diff_multisets(multiset(rows_a, with_preset=True),
                             multiset(rows_c, with_preset=False))
    results: dict[str, Any] = {
        "check_kind": "no_simulation_load_equivalence",
        "source_vs_compact_pass": not diffs_sc,
        "source_vs_compact_diff_count": len(diffs_sc),
        "source_vs_compact_diffs": diffs_sc[:20],
        "c_diff_count": len(diffs_c),
        "c_diffs": diffs_c[:20],
        "c_pass": (not diffs_sc) and (not diffs_c),
        "components": rows_c,
        "component_count": len(rows_c),
    }
    return results


# --------------------------------------------------------------------------
# checkpoint helpers (append-only JSONL, resumable)
# --------------------------------------------------------------------------

def load_checkpoint(path: Path) -> dict[str, dict]:
    store: dict[str, dict] = {}
    if not path.is_file():
        return store
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue  # truncated tail line from an interrupted run
        if isinstance(row, dict) and "key" in row:
            store[row["key"]] = row.get("value")
    return store


def append_checkpoint(path: Path, key: str, value: dict) -> None:
    with path.open("a") as stream:
        stream.write(json_line({"key": key, "value": value}))


def read_catalog(catalog_path: Path) -> list[dict]:
    rows = []
    for line in catalog_path.read_text().splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def v3_legacy_keys(paths: list[Path]) -> set[str]:
    """source_file keys already covered by the retained v3 conversations."""
    keys: set[str] = set()
    for path in paths:
        if not path.is_file() or path.suffix != ".jsonl":
            continue
        for line in path.read_text().splitlines():
            if line.strip():
                keys.add(source_key(json.loads(line)["file"]))
    return keys


# --------------------------------------------------------------------------
# record assembly
# --------------------------------------------------------------------------

def make_source_record(*, catalog_id: str, source_id: str, source_file: str,
                       origin: str, file: str, sim: str | None,
                       simulation_status: str, selection: str,
                       targets: dict, metric_provenance: dict,
                       compact: dict, model_compact: dict | None,
                       engineering: dict, digest_entry: dict,
                       flags: list, label_mode: str,
                       source_preservation: dict) -> dict:
    """Source record in the exact shared-contract field order."""
    return {
        "catalog_id": catalog_id,
        "source_id": source_id,
        "source_file": source_file,
        "origin": origin,
        "file": file,
        "sim": sim,
        "simulation_status": simulation_status,
        "selection": selection,
        "targets": targets,
        "metric_provenance": metric_provenance,
        "compact": compact,
        "model_compact": model_compact,
        "engineering": engineering,
        "digest_entry": digest_entry,
        "flags": flags,
        "label_mode": label_mode,
        "source_preservation": source_preservation,
    }


# --------------------------------------------------------------------------
# runner
# --------------------------------------------------------------------------

def _recover_static(record: dict, workspace: Path, legacy: set[str]) -> dict:
    """Phase A for one catalog row: selection + static compact (no JVM)."""
    catalog_id = record["id"]
    identity = {
        "catalog_id": catalog_id, "source_id": catalog_id,
        "source_file": record["source_file"], "origin": record["origin"],
    }
    src = source_path_for(record, workspace)
    result: dict[str, Any] = {**identity, "file": str(src),
                              "flags": [], "warnings": {}}
    if source_key(record["source_file"]) in legacy:
        result["flags"].append("already_in_v3")

    if not src.is_file():
        result["compact"] = None
        result["flags"].append("source_file_missing")
        result["warnings"]["source_file_missing"] = f"no file at {src}"
        result["pick"] = select_simulation(record.get("simulations") or [],
                                           {"tag": "openrocket", "children": []},
                                           record["origin"],
                                           record.get("fill_info"))
        result["pick"]["flags"] = (result["pick"].get("flags") or []) + \
            ["source_file_missing"]
        return result
    try:
        tree, _entries, _container = read_ork_archive(src)
    except Exception as exc:
        result["compact"] = None
        result["flags"].append("unreadable_source")
        result["warnings"]["unreadable_source"] = (
            f"{exc.__class__.__name__}: {exc}")
        result["pick"] = select_simulation(record.get("simulations") or [],
                                           {"tag": "openrocket", "children": []},
                                           record["origin"],
                                           record.get("fill_info"))
        result["pick"]["flags"] = (result["pick"].get("flags") or []) + \
            ["unreadable_source"]
        return result

    pick = select_simulation(record.get("simulations") or [], tree,
                             record["origin"], record.get("fill_info"))
    result["pick"] = pick
    result["tree_loaded"] = True

    try:
        full = read_full_design(src, pick["sim_index"])
        if pick["sim_index"] is None:
            compact = to_compact_config(full, pick["configid"])
            check = static_check_config(full, pick["configid"])
        else:
            compact = to_compact(full)
            check = static_check(full)
    except (CompactError, KeyError, ValueError) as exc:
        result["compact"] = None
        result["flags"].append("compact_extraction_failed")
        result["warnings"]["compact_extraction_failed"] = (
            f"{exc.__class__.__name__}: {exc}")
        return result
    result["compact"] = compact
    result["compact_chars"] = len(dump_compact_json(compact))
    result["static_check"] = check
    if not check.get("pass"):
        result["flags"].append("static_check_failed")
        result["warnings"]["static_check_failed"] = "; ".join(
            check.get("differences", [])[:5])
    # honest status on the record: no fake passes, no silent exclusions
    if compact.get("attachments"):
        result["flags"].append("custom_thrust_curve_attachments")
    mounts = design_mounts(compact)
    for mount in mounts:
        motor = mount["motor"]
        if motor is None:
            continue
        if value_of(child(motor, "digest")) is None:
            result["flags"].append("motor_block_without_digest")
            break
    for f in pick.get("flags") or []:
        if f not in result["flags"]:
            result["flags"].append(f)
    if pick.get("sim_index") is not None:
        nodes = find_simulation_nodes(tree)
        if sum(1 for n in nodes if xml_sim_name(n) == pick["name"]) > 1:
            if "duplicate_simulation_name" not in result["flags"]:
                result["flags"].append("duplicate_simulation_name")
        first_index = next(
            (i for i, n in enumerate(nodes) if xml_sim_name(n) == pick["name"]),
            None)
        result["first_instance_of_name"] = first_index
    return result


def run(output_dir: Path, workspace: Path, catalog_path: Path,
        limit: int = 0, jvm: bool = True,
        motor_db_path: Path | None = None,
        v3_paths: list[Path] | None = None) -> dict:
    from scripts.sft_compact_digest_check import check_pair  # JVM on first use
    from scripts.sft_full_fidelity_extract import build_ork

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    sources_path = output_dir / "sources.jsonl"
    lookup_path = output_dir / "motor_lookup.json"
    summary_path = output_dir / "sources_summary.json"
    assets_path = output_dir / "assets.json"
    eng_ckpt = output_dir / "eng_checkpoint.jsonl"
    digest_ckpt = output_dir / "digest_checkpoint.jsonl"

    motor_db_path = Path(motor_db_path or MOTOR_DB)
    v3_paths = v3_paths if v3_paths is not None else [V3_TRAIN, V3_TEST, V3_LOOKUP]

    catalog = read_catalog(catalog_path)
    if limit:
        catalog = catalog[:limit]
    legacy = v3_legacy_keys(v3_paths)

    # ---- phase A: selection + static extraction for every catalog row ----
    recovered: list[dict] = []
    for row in catalog:
        recovered.append(_recover_static(row, workspace, legacy))

    payloads = [
        {"catalog_id": r["catalog_id"], "compact": r.get("compact"),
         "engineering": {}}
        for r in recovered if r.get("compact")
    ]

    # ---- phase B: static engineering stats (JVM, resumable) ----
    if jvm:
        from scripts.sft_compact_stage1_engineering import engineering_stats
        eng_store = load_checkpoint(eng_ckpt)
        with tempfile.TemporaryDirectory(prefix="sft_v4_eng_") as eng_tmp:
            for r in recovered:
                key = f"{r['catalog_id']}|{r['pick'].get('name') or '<nosim>'}"
                if not r.get("compact"):
                    r["engineering"] = {"unavailable":
                                        "no compact design recovered"}
                    continue
                if key in eng_store:
                    r["engineering"] = eng_store[key]
                    continue
                src = Path(r["file"])
                try:
                    if r["pick"]["sim_index"] is None:
                        eng = engineering_stats_default(src)
                    else:
                        # engineering_stats looks the sim up BY NAME in the
                        # source file; when that name is duplicated and the
                        # selected catalog entry is NOT the first XML
                        # instance, compute the stats on the single-sim
                        # rebuilt design instead so the numbers describe the
                        # exact selected configuration.
                        first = (r.get("first_instance_of_name")
                                 == r["pick"]["sim_index"])
                        if not first:
                            rebuilt = Path(eng_tmp) / _fs_safe_key(key)
                            build_ork(from_compact(r["compact"]), rebuilt)
                            eng = engineering_stats(rebuilt, r["pick"]["name"])
                            r.setdefault("warnings", {})[
                                "engineering_source"] = (
                                "computed on the single-sim rebuilt design "
                                "(selected sim shares its name with another "
                                "XML instance)")
                        else:
                            eng = engineering_stats(src, r["pick"]["name"])
                    append_checkpoint(eng_ckpt, key, eng)
                    r["engineering"] = eng
                except Exception as exc:
                    r["engineering"] = {"unavailable":
                                         f"{exc.__class__.__name__}: {exc}"}
                    r["flags"].append("engineering_unavailable")
                    r["warnings"]["engineering_unavailable"] = (
                        f"{exc.__class__.__name__}: {exc}")
    else:
        eng_store = load_checkpoint(eng_ckpt)
        for r in recovered:
            key = f"{r['catalog_id']}|{r['pick'].get('name') or '<nosim>'}"
            r["engineering"] = eng_store.get(
                key, {"unavailable": "No cached static calculation; JVM disabled"})

    # unresolved design motors: engineering resolved nothing for them
    for r in recovered:
        if not r.get("compact") or not isinstance(r["engineering"], dict):
            continue
        eng_motors = r["engineering"].get("motors")
        if not isinstance(eng_motors, list):
            continue  # stats unavailable: nothing was resolved, say nothing
        for j, mount in enumerate(design_mounts(r["compact"])):
            motor = mount["motor"]
            if motor is None or value_of(child(motor, "digest")) is None:
                continue
            res = (eng_motors[j].get("motor") if j < len(eng_motors) else None)
            if res is None:
                if "unresolved_motor_digest" not in r["flags"]:
                    r["flags"].append("unresolved_motor_digest")
                break

    # ---- phase C: readable motor lookup over db + dataset + v3 entries ----
    payloads = [
        {"catalog_id": r["catalog_id"], "compact": r.get("compact"),
         "engineering": r.get("engineering") or {}}
        for r in recovered if r.get("compact")
    ]
    dataset_entries = collect_dataset_motor_entries(payloads)
    db_entries = json.loads(motor_db_path.read_text())
    v3_entries = []
    for path in v3_paths:
        if path.suffix == ".json" and path.is_file() and "lookup" in path.name:
            v3_entries = list(json.loads(path.read_text()).values())
    lookup = build_motor_lookup(db_entries, dataset_entries + v3_entries)
    id_by_digest = {v["digest"]: k for k, v in lookup.items()}
    digest_by_id = {k: v["digest"] for k, v in lookup.items()}
    if len(id_by_digest) != len(lookup) or len(digest_by_id) != len(lookup):
        raise RuntimeError("built motor lookup is not one-to-one")

    # ---- phase D: digest / motor-id round-trip load check (JVM) ----
    if jvm:
        digest_store = load_checkpoint(digest_ckpt)
        with tempfile.TemporaryDirectory(prefix="sft_v4_sources_") as tmp:
            for r in recovered:
                key = f"{r['catalog_id']}|{r['pick'].get('name') or '<nosim>'}"
                if not r.get("compact"):
                    r["digest_entry"] = {"c_pass": False, "components": [],
                                         "error": "no compact design recovered"}
                    continue
                if key in digest_store:
                    r["digest_entry"] = digest_store[key]
                    continue
                try:
                    if r["pick"]["sim_index"] is None:
                        entry = check_pair_config(
                            Path(r["file"]), r["compact"],
                            Path(tmp) / _fs_safe_key(key),
                            id_by_digest, digest_by_id)
                    else:
                        entry = check_pair(key, r["compact"], Path(tmp),
                                           id_by_digest, digest_by_id)
                except Exception as exc:
                    entry = {"c_pass": False, "components": [],
                             "error": f"{exc.__class__.__name__}: {exc}"}
                try:
                    append_checkpoint(digest_ckpt, key, entry)
                except ValueError:
                    # non-finite leaf in the loaded-state dump: the
                    # equivalence verdict was computed in memory; the dump
                    # itself cannot be persisted
                    entry = {**entry, "components": [],
                             "components_dropped": "non-finite value in "
                                                  "loaded-state dump"}
                    append_checkpoint(digest_ckpt, key, entry)
                r["digest_entry"] = entry
    else:
        digest_store = load_checkpoint(digest_ckpt)
        for r in recovered:
            key = f"{r['catalog_id']}|{r['pick'].get('name') or '<nosim>'}"
            r["digest_entry"] = digest_store.get(key, {
                "c_pass": None, "components": [],
                "error": "Optional load comparison not run; source geometry "
                         "was checked structurally",
            })

    # ---- phase E: model_compact, assets registry, records, outputs ----
    assets_registry: dict[str, Any] = {
        "schema": "sft_v4_assets-1",
        "purpose": ("exact bytes of engineering thrust-curve attachments "
                    "that never enter supervised text, plus readable "
                    "identities for design motor blocks without a digest"),
        "restore_path": (
            "To rebuild a flyable .ork from a model_compact: (1) replace "
            "each motor_id leaf with the digest from motor_lookup.json "
            "(restore_motor_digests in scripts/sft_compact_motor_ids.py); "
            "(2) rebuild the compact 'attachments' dict {attachment_name: "
            "{'data_base64': ...}} from this registry, keyed by the readable "
            "motor ID recorded in the record's source_preservation.assets "
            "(attachment names embed the motor digest as "
            "thrustcurves/<digest>.rse); (3) call scripts.sft_compact_design."
            "from_compact and scripts.sft_full_fidelity_extract.build_ork. "
            "Digest-less motor blocks are already fully described in the "
            "model design by their manufacturer/designation/dimensions."),
        "assets": {},
        "digestless_identities": {},
    }

    records: list[dict] = []
    for r in recovered:
        compact = r.get("compact")
        digest_entry = r.get("digest_entry") or {"c_pass": False,
                                                 "components": []}
        model_compact = None
        model_notes: dict[str, Any] = {}
        if compact is not None:
            try:
                components = digest_entry.get("components") or []
                if components:
                    stage2, fixes = apply_stage2_and_fix(
                        copy.deepcopy(compact), id_by_digest, components)
                    model_notes["derivation"] = (
                        "apply_stage2_and_fix(compact, id_by_digest, "
                        "digest_entry.components), attachments stripped")
                    model_notes["preset_fixes"] = fixes
                else:
                    stage2 = build_stage2_design(copy.deepcopy(compact),
                                                 id_by_digest)
                    model_notes["derivation"] = (
                        "build_stage2_design(compact, id_by_digest), "
                        "attachments stripped; no component dump was "
                        "available for the explicit preset-override fix")
                stage2.pop("attachments", None)
                model_compact = stage2
                model_notes["chars"] = len(dump_compact_json(stage2))
            except Exception as exc:
                r["flags"].append("model_compact_unavailable")
                model_notes["error"] = f"{exc.__class__.__name__}: {exc}"

        # attachment registry entries (exact bytes, readable keys)
        record_assets: list[dict] = []
        for name, meta in sorted((compact or {}).get("attachments", {}).items()):
            m = re.match(r"^thrustcurves/(.+)\.rse$", name)
            digest = m.group(1) if m else None
            motor_id = id_by_digest.get(digest or "")
            if motor_id is None:
                motor_id = f"curve-{len(assets_registry['assets']) + 1}"
            data = meta["data_base64"]
            raw = base64.b64decode(data, validate=True)
            if motor_id in assets_registry["assets"]:
                entry = assets_registry["assets"][motor_id]
            else:
                entry = {"motor_id": motor_id, "attachment_name": name,
                         "motor_digest": digest,
                         "sha256": hashlib.sha256(raw).hexdigest(),
                         "size_bytes": len(raw),
                         "data_base64": data, "used_by": []}
                assets_registry["assets"][motor_id] = entry
            if r["catalog_id"] not in entry["used_by"]:
                entry["used_by"].append(r["catalog_id"])
            record_assets.append({"motor_id": motor_id, "attachment_name": name,
                                  "motor_digest": digest})

        pick = r["pick"]
        status = pick.get("status") or STATUS_UNAVAILABLE
        flags = list(dict.fromkeys(
            ["saved_flight_not_rerun"] + list(r.get("flags") or [])))
        if pick.get("label_mode") == "hardware_only" and \
                "hardware_only_no_flight_labels" not in flags:
            flags.append("hardware_only_no_flight_labels")
        if digest_entry.get("c_pass") is None:
            flags.append("load_equivalence_unavailable")
        elif digest_entry.get("c_pass") is False:
            error_text = str(digest_entry.get("error") or "")
            if "disabled" in error_text or "not verified" in error_text:
                flag_name = "load_equivalence_not_verified"
            elif "no compact design" in error_text:
                flag_name = "load_equivalence_not_verified"
            else:
                flag_name = "load_equivalence_failed"
            if flag_name not in flags:
                flags.append(flag_name)
        r["flags"] = flags

        source_preservation = {
            "source_sha256": hashlib.sha256(
                Path(r["file"]).read_bytes()).hexdigest()
            if Path(r["file"]).is_file() else None,
            "catalog": {
                "id": r["catalog_id"], "origin": r["origin"],
                "source_file": r["source_file"],
                "source_repo": None,
                "looks_machine_generated": None,
                "motor_chosen_by_pipeline": None,
                "openrocket_version": None,
            },
            "v3": {"covered_by_v3": "already_in_v3" in flags},
            "preserved": list(PRESERVED_FIELDS),
            "removed": {
                "documented_cosmetic_and_audit":
                    ["appearance", "insideappearance", "photostudio",
                     "docprefs", "comment", "designer", "revision", "id",
                     "component names", "cached flightdata"],
                "non_selected_flight_configurations": True,
                "non_selected_simulations": True,
                "values_rounded": False,
            },
            "extraction": {
                "sim_index": pick.get("sim_index"),
                "flight_configuration_id": pick.get("configid"),
                "compact_chars": r.get("compact_chars"),
                "static_check_passed": bool((r.get("static_check") or {})
                                            .get("pass")),
                "static_check_differences": (r.get("static_check") or {}).get(
                    "differences", [])[:10],
                "model_compact": model_notes,
            },
        }
        # catalog metadata from the catalog row itself
        row_meta = next((c for c in catalog
                         if c["id"] == r["catalog_id"]), {})
        source_preservation["catalog"].update({
            "source_repo": row_meta.get("source_repo"),
            "looks_machine_generated": row_meta.get(
                "looks_machine_generated"),
            "motor_chosen_by_pipeline": row_meta.get(
                "motor_chosen_by_pipeline"),
            "openrocket_version": row_meta.get("openrocket_version"),
        })
        if record_assets:
            source_preservation["assets"] = {
                "registry": "assets.json", "entries": record_assets,
                "note": "exact thrust-curve bytes live in assets.json; "
                        "model_compact strips them",
            }
        dl = [m for m in (design_mounts(compact) if compact else [])
              if m["motor"] is not None
              and value_of(child(m["motor"], "digest")) is None]
        if dl:
            source_preservation["digestless_motor_identities"] = [
                _identity_for_block(m["motor"]) for m in dl]
        if r.get("warnings"):
            source_preservation["warnings"] = r["warnings"]

        digest_out = {"c_pass": digest_entry.get("c_pass"),
                      "components": digest_entry.get("components") or []}
        for extra in ("error", "components_dropped", "check_kind",
                      "source_vs_compact_pass", "source_vs_compact_diff_count",
                      "preset_fix_applied", "dump_variant"):
            if extra in digest_entry:
                digest_out[extra] = digest_entry[extra]
        for vk in ("b0_pass", "b1_pass", "b2_pass", "b3_pass", "c_pass"):
            if vk in digest_entry and vk != "c_pass":
                digest_out[f"variant_{vk}"] = digest_entry[vk]

        record = make_source_record(
            catalog_id=r["catalog_id"], source_id=r["catalog_id"],
            source_file=r["source_file"], origin=r["origin"],
            file=r["file"], sim=pick.get("name"),
            simulation_status=status if status else STATUS_UNAVAILABLE,
            selection=pick.get("selection") or "",
            targets=pick.get("targets") or {},
            metric_provenance=pick.get("provenance") or {},
            compact=compact, model_compact=model_compact,
            engineering=r.get("engineering") or {"unavailable": "unknown"},
            digest_entry=digest_out, flags=flags,
            label_mode=pick.get("label_mode") or "hardware_only",
            source_preservation=source_preservation)
        records.append(record)

    # digestless identities registry (readable, deterministic, no hashes)
    dl_registry = digestless_identities(payloads)
    assets_registry["digestless_identities"] = dl_registry

    # ---- hard invariants before writing ----
    catalog_ids = [c["id"] for c in catalog]
    record_ids = [rec["catalog_id"] for rec in records]
    id_order_match = record_ids == catalog_ids
    id_set_match = set(record_ids) == set(catalog_ids)
    if not id_set_match or not id_order_match:
        missing = [i for i in catalog_ids if i not in set(record_ids)]
        extra = [i for i in record_ids if i not in set(catalog_ids)]
        raise RuntimeError(
            f"source records do not match the catalog exactly: "
            f"missing={missing[:10]} extra={extra[:10]} order_match="
            f"{id_order_match}")

    design_digests = set()
    for rec in records:
        if rec["compact"]:
            design_digests.update(compact_motor_digests(rec["compact"]))
    digests_in_lookup = design_digests <= set(id_by_digest)

    # ---- write outputs ----
    with sources_path.open("w") as stream:
        for record in records:
            try:
                stream.write(json_line(record))
            except ValueError as exc:
                # never fake success: report the exact record and evidence
                raise RuntimeError(
                    f"record {record['catalog_id']} carries non-finite "
                    f"values that cannot be serialized honestly: {exc}"
                ) from exc
    lookup_path.write_text(json.dumps(lookup, ensure_ascii=False, indent=1,
                                      sort_keys=True, allow_nan=False) + "\n")
    assets_path.write_text(json.dumps(assets_registry, ensure_ascii=False,
                                      indent=1, sort_keys=True,
                                      allow_nan=False) + "\n")

    label_counts = Counter(rec["label_mode"] for rec in records)
    prov_counts = Counter(
        str((rec["metric_provenance"] or {}).get("source"))
        for rec in records)
    status_counts = Counter(rec["simulation_status"] for rec in records)
    origin_counts = Counter(rec["origin"] for rec in records)
    flags_hist: Counter = Counter()
    for rec in records:
        for f in rec["flags"]:
            flags_hist[f] += 1
    c_pass_count = sum(1 for rec in records
                       if rec["digest_entry"].get("c_pass"))
    warning_lists = {
        "static_check_failed": [r["catalog_id"] for r in recovered
                                if "static_check_failed" in r["flags"]],
        "load_equivalence_failed": [r["catalog_id"] for r in recovered
                                    if "load_equivalence_failed" in r["flags"]],
        "engineering_unavailable": [r["catalog_id"] for r in recovered
                                   if "engineering_unavailable" in r["flags"]],
        "compact_extraction_failed": [r["catalog_id"] for r in recovered
                                      if "compact_extraction_failed" in r["flags"]],
        "unresolved_motor_digest": [r["catalog_id"] for r in recovered
                                    if "unresolved_motor_digest" in r["flags"]],
        "motor_block_without_digest": [r["catalog_id"] for r in recovered
                                       if "motor_block_without_digest" in r["flags"]],
        "custom_thrust_curve_attachments": [
            r["catalog_id"] for r in recovered
            if "custom_thrust_curve_attachments" in r["flags"]],
        "fill_result_configuration_mismatch": [
            r["catalog_id"] for r in recovered
            if "fill_result_configuration_mismatch" in r["flags"]],
        "duplicate_simulation_name": [r["catalog_id"] for r in recovered
                                      if "duplicate_simulation_name" in r["flags"]],
        "no_simulations_in_design": [r["catalog_id"] for r in recovered
                                     if "no_simulations_in_design" in r["flags"]],
        "model_compact_unavailable": [r["catalog_id"] for r in recovered
                                      if "model_compact_unavailable" in r["flags"]],
    }
    summary = {
        "catalog_rows": len(catalog),
        "records_emitted": len(records),
        "catalog_id_order_match": id_order_match,
        "catalog_id_set_equal": id_set_match,
        "limit_run": bool(limit),
        "jvm_enabled": bool(jvm),
        "label_mode_counts": dict(label_counts),
        "metric_provenance_source_counts": dict(prov_counts),
        "simulation_status_counts": dict(status_counts),
        "origin_counts": dict(origin_counts),
        "records_with_c_pass": c_pass_count,
        "records_with_c_fail": len(records) - c_pass_count,
        "flags_histogram": dict(sorted(flags_hist.items())),
        "warnings": warning_lists,
        "motor_lookup": {
            "size": len(lookup),
            "design_side_digests": len(design_digests),
            "all_design_digests_in_lookup": digests_in_lookup,
            "note": "includes every design-side digest, also unresolved "
                    "ones; numbers stay absent when the shipped database "
                    "cannot resolve them",
        },
        "digestless_identity_count": len(dl_registry),
        "custom_asset_count": len(assets_registry["assets"]),
        "preserved_fields": list(PRESERVED_FIELDS),
        "flight_simulations_run": 0,
        "notes": [
            "No flight simulation ran anywhere: saved catalog/fill-pipeline "
            "metrics only, static loading, MassCalculator/Barrowman stats "
            "and headless load equivalence checks.",
            "Every catalog rocket got a complete source record; missing "
            "flight labels make it an honest hardware_only record, never "
            "an exclusion.",
            "simulation_status is the stored XML status (or 'unavailable' "
            "for designs with no simulation); outdated saved results stay "
            "an explicit reference with a warning flag.",
            "c_pass reflects ONLY actual load equivalence; false values "
            "are honest hardware-only warnings, not fabricated passes.",
            "Hardware-only records are SFT-capable source designs, not "
            "verified-safe flight data.",
            "Custom thrust-curve attachments never enter model_compact; "
            "exact bytes and the restore path live in assets.json.",
            "Digest-less motor blocks keep readable deterministic "
            "identities; no invented hashes.",
        ],
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2,
                                       allow_nan=False) + "\n")
    print(json.dumps({k: summary[k] for k in (
        "catalog_rows", "records_emitted", "catalog_id_order_match",
        "catalog_id_set_equal", "label_mode_counts",
        "metric_provenance_source_counts", "simulation_status_counts",
        "records_with_c_pass", "records_with_c_fail",
        "flags_histogram", "motor_lookup", "custom_asset_count",
        "digestless_identity_count", "flight_simulations_run")}, indent=2))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--workspace", type=Path, default=WORKSPACE)
    parser.add_argument("--catalog", type=Path, default=None,
                        help=f"default: <workspace>/{CATALOG_REL}")
    parser.add_argument("--limit", type=int, default=0,
                        help="debug: only the first N catalog rows")
    parser.add_argument("--no-jvm", action="store_true",
                        help="structural run: skip JVM engineering/load "
                             "checks (recorded as unavailable/not verified)")
    args = parser.parse_args()
    catalog = args.catalog or (args.workspace / CATALOG_REL)
    run(args.output_dir, args.workspace, catalog, args.limit,
        jvm=not args.no_jvm)
    return 0


if __name__ == "__main__":
    sys.exit(main())
