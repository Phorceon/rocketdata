"""Full-fidelity OpenRocket extract → JSON design → ORK rebuild for SFT dataset repair."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import or_headless as oh  # noqa: E402
from scripts.sft_full_fidelity_support.compare import (  # noqa: E402
    AUTHORITATIVE_MANIFEST_PREFIXES,
    compare_bundle_entries,
    compare_component_snapshots,
    compare_manifests,
    compare_simulation_options,
    filter_manifest_by_prefixes,
    metric_diffs,
    metrics_pass,
    sanitize_metrics,
)
from scripts.sft_full_fidelity_support.manifest import (  # noqa: E402
    build_field_manifest,
    manifest_covers_design,
)
from scripts.sft_full_fidelity_support.ork_archive import (  # noqa: E402
    bundle_entries_from_json,
    bundle_entries_to_json,
    file_sha256,
    partition_bundle_entries,
    read_ork_archive,
    write_ork_archive,
)
from scripts.sft_full_fidelity_support.runtime import (  # noqa: E402
    deployment_config_for_fcid,
    motor_config_for_fcid,
    snapshot_simulation_options,
    walk_components,
)
from scripts.sft_full_fidelity_support.xml_tree import (  # noqa: E402
    find_simulation_by_name,
    simulation_config_id,
    simulation_field,
)

SCHEMA_VERSION = "full-fidelity-1.0"


class ExtractionBlockedError(RuntimeError):
    """Source row cannot be extracted faithfully (missing sim, unloadable file, etc.)."""


def _resolve_source(path: str | Path) -> Path:
    source = Path(path)
    if not source.is_absolute():
        source = REPO_ROOT / source
    if not source.exists():
        raise ExtractionBlockedError(f"source not found: {source}")
    return source


def _runtime_identity() -> dict[str, Any]:
    oh._boot_or()
    import jpype

    System = jpype.JClass("java.lang.System")
    jar_sha = file_sha256(Path(oh._jar()))
    return {
        "openrocket_jar_sha256": jar_sha,
        "java_version": str(System.getProperty("java.version")),
        "uuid_seed": 42,
    }


def _load_document(source: Path):
    oh._boot_or()
    try:
        return oh._helper().load_doc(str(source))
    except Exception as error:
        raise ExtractionBlockedError(f"OpenRocket failed to load {source}: {error}") from error


def _get_simulation(doc, simulation_name: str):
    for index in range(doc.getSimulationCount()):
        sim = doc.getSimulation(index)
        if str(sim.getName()) == simulation_name:
            return index, sim
    names = [str(doc.getSimulation(i).getName()) for i in range(doc.getSimulationCount())]
    raise ExtractionBlockedError(f"simulation {simulation_name!r} not found; available: {names}")


def _reconstruction_contract(jar_sha256: str) -> dict[str, Any]:
    return {
        "authoritative_for_rebuild": ["parameter_tree", "ork_container", "bundle_entries"],
        "audit_only_not_used_for_rebuild": [
            "component_index",
            "simulation_options_snapshot",
        ],
        "required_openrocket_jar_sha256": jar_sha256,
        "rebuild_policy": (
            "Structured source parameter_tree + engineering bundle attachments + original "
            "container format. No OpenRocket saver normalization."
        ),
    }


def _build_design(
    parameter_tree: dict[str, Any],
    ork_container: dict[str, Any],
    bundle_json: dict[str, Any],
    *,
    selected_simulation: dict[str, Any],
    component_index: list[dict[str, Any]],
    simulation_options_snapshot: dict[str, Any],
    jar_sha256: str,
) -> dict[str, Any]:
    root_attrs = parameter_tree.get("attrs") or {}
    return {
        "schema_version": SCHEMA_VERSION,
        "reconstruction_contract": _reconstruction_contract(jar_sha256),
        "openrocket_version": root_attrs.get("version"),
        "creator": root_attrs.get("creator"),
        "ork_container": ork_container,
        "parameter_tree": parameter_tree,
        "bundle_entries": bundle_json,
        "selected_simulation": selected_simulation,
        "simulation_options_snapshot": simulation_options_snapshot,
        "component_index": component_index,
    }


def _attach_fcid_configs(components: list[dict[str, Any]], doc, fcid: str) -> None:
    flat: list[Any] = []

    def collect(node):
        for child in node.getChildren():
            flat.append(child)
            collect(child)

    collect(doc.getRocket())
    if len(flat) != len(components):
        raise ExtractionBlockedError(
            f"component tree walk mismatch: {len(flat)} loaded vs {len(components)} indexed"
        )
    for row, component in zip(components, flat):
        row["motor_configuration"] = motor_config_for_fcid(component, fcid)
        row["deployment_configuration"] = deployment_config_for_fcid(component, fcid)


def extract_design(source_path: str | Path, simulation_name: str, seed: int = 42) -> dict[str, Any]:
    """Extract a complete engineering-input design JSON from a source .ork file."""
    source = _resolve_source(source_path)
    parameter_tree, entries, ork_container = read_ork_archive(source)
    try:
        sim_index, sim_node = find_simulation_by_name(parameter_tree, simulation_name)
    except KeyError as error:
        raise ExtractionBlockedError(str(error)) from error

    fcid = simulation_config_id(sim_node)
    selected = {
        "name": simulation_name,
        "index": sim_index,
        "flight_configuration_id": fcid,
        "simulator": simulation_field(sim_node, "simulator"),
        "calculator": simulation_field(sim_node, "calculator"),
    }

    runtime = _runtime_identity()
    jar_sha = runtime["openrocket_jar_sha256"]
    engineering_bytes, cosmetic_excluded = partition_bundle_entries(entries)

    doc = _load_document(source)
    sim_doc_index, sim = _get_simulation(doc, simulation_name)
    if sim_doc_index != sim_index:
        selected["index_warning"] = f"XML index {sim_index} vs document index {sim_doc_index}"

    components = walk_components(doc.getRocket())
    if fcid:
        _attach_fcid_configs(components, doc, fcid)

    import jpype

    jpype.JClass("OrBatch").reseed(sim.getOptions(), int(seed))
    simulation_options_snapshot = snapshot_simulation_options(sim)

    design = _build_design(
        parameter_tree,
        ork_container,
        bundle_entries_to_json(engineering_bytes),
        selected_simulation=selected,
        component_index=components,
        simulation_options_snapshot=simulation_options_snapshot,
        jar_sha256=jar_sha,
    )

    manifest = build_field_manifest(design, source_file=source.name, jar_sha256=jar_sha)
    coverage_errors = manifest_covers_design(design, manifest)
    if coverage_errors:
        raise ExtractionBlockedError(
            "field_manifest coverage failed: " + "; ".join(coverage_errors[:5])
        )

    try:
        flight_metrics = oh.simulate(str(source), sim_name=simulation_name, seed=seed)
    except Exception as error:
        raise ExtractionBlockedError(
            f"selected simulation {simulation_name!r} did not simulate for {source}: {error}"
        ) from error

    provenance = {
        "source_path": str(source.relative_to(REPO_ROOT)) if source.is_relative_to(REPO_ROOT) else str(source),
        "source_sha256": file_sha256(source),
        "selected_simulation": simulation_name,
        "flight_configuration_id": fcid,
        "runtime": runtime,
        "simulation_seed": seed,
        "cosmetic_bundle_excluded": cosmetic_excluded,
        "notes": [
            "Cached <flightdata> stripped from parameter_tree (not engineering inputs).",
            "Rebuild uses explicit source parameter_tree (not saver-normalized output).",
            "component_index / simulation_options_snapshot are audit-only.",
        ],
    }

    return {
        "design": design,
        "field_manifest": manifest,
        "provenance": provenance,
        "flight_metrics": sanitize_metrics(flight_metrics),
    }


def build_ork(design: dict[str, Any], destination: str | Path) -> Path:
    """Rebuild an .ork archive purely from a design dict (no source file access)."""
    if design.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"unsupported design schema: {design.get('schema_version')!r}")
    contract = design.get("reconstruction_contract") or {}
    required_jar = contract.get("required_openrocket_jar_sha256")
    runtime = _runtime_identity()
    if required_jar and required_jar != runtime["openrocket_jar_sha256"]:
        raise ExtractionBlockedError(
            f"JAR drift blocked rebuild: design requires sha256={required_jar}, "
            f"runtime has {runtime['openrocket_jar_sha256']}"
        )
    bundle = bundle_entries_from_json(design.get("bundle_entries") or {})
    return write_ork_archive(
        Path(destination),
        design["parameter_tree"],
        container=design.get("ork_container") or {"format": "zip"},
        bundle_entries=bundle,
    )


def _validate_passed_design_audit(design: dict[str, Any], rebuilt_design: dict[str, Any]) -> list[str]:
    """Compare audit snapshots captured at extract time with rebuilt observations."""
    errors: list[str] = []
    errors.extend(
        compare_component_snapshots(
            design.get("component_index") or [],
            rebuilt_design.get("component_index") or [],
        )
    )
    errors.extend(
        compare_simulation_options(
            design.get("simulation_options_snapshot"),
            rebuilt_design.get("simulation_options_snapshot"),
        )
    )
    return errors


def validate_roundtrip(
    source_path: str | Path,
    simulation_name: str,
    design: dict[str, Any],
    destination: str | Path,
    seed: int = 42,
) -> dict[str, Any]:
    """Compare original source vs rebuilt inputs, audit snapshots, and flight metrics."""
    source = _resolve_source(source_path)
    dest = Path(destination)
    built = build_ork(design, dest)

    original = extract_design(source, simulation_name, seed=seed)
    source_manifest = original["field_manifest"]
    rebuilt = extract_design(built, simulation_name, seed=seed)

    manifest_errors = compare_manifests(
        filter_manifest_by_prefixes(source_manifest, AUTHORITATIVE_MANIFEST_PREFIXES),
        filter_manifest_by_prefixes(rebuilt["field_manifest"], AUTHORITATIVE_MANIFEST_PREFIXES),
    )
    audit_errors = (
        _validate_passed_design_audit(original["design"], rebuilt["design"])
        + _validate_passed_design_audit(design, rebuilt["design"])
    )
    bundle_errors = compare_bundle_entries(
        design.get("bundle_entries") or {},
        rebuilt["design"].get("bundle_entries") or {},
    )

    input_errors = manifest_errors + audit_errors + bundle_errors

    source_metrics = original["flight_metrics"]
    rebuilt_metrics = rebuilt["flight_metrics"]
    diffs = metric_diffs(source_metrics, rebuilt_metrics)
    metrics_ok, metric_errors = metrics_pass(diffs)

    input_pass = len(input_errors) == 0
    overall_pass = input_pass and metrics_ok

    return {
        "pass": overall_pass,
        "input_pass": input_pass,
        "metrics_pass": metrics_ok,
        "metrics_comparison_baseline": "original_source",
        "input_errors": input_errors,
        "metric_errors": metric_errors,
        "metric_diffs": diffs,
        "notes": [
            "pass requires authoritative parameter_tree fidelity and original-source flight metrics.",
            "Audit snapshots compare the passed design vs rebuilt loader observations.",
        ],
        "rebuilt_path": str(built),
    }


def extract_design_from_result(result: dict[str, Any]) -> dict[str, Any]:
    """Helper for callers holding the full extract_design() return value."""
    return result["design"]
