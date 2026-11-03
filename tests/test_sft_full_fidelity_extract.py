"""Tests for full-fidelity OpenRocket extract / rebuild."""

from __future__ import annotations

import json
import re
import sys
import tempfile
from copy import deepcopy
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts import or_headless as oh
from scripts.sft_full_fidelity_extract import (
    SCHEMA_VERSION,
    build_ork,
    extract_design,
    validate_roundtrip,
)
from scripts.sft_full_fidelity_support.manifest import manifest_covers_design
from scripts.sft_full_fidelity_support.xml_tree import find_simulation_by_name

pytestmark = pytest.mark.skipif(
    not oh.DEFAULT_JAR.exists() or not (oh.DEFAULT_JAVA_HOME / "bin" / "java").exists(),
    reason="OpenRocket JAR or JDK 17 not available",
)

FIXTURES = [
    ("ork/rockets__bt_55.ork", "Simulation 1"),
    ("ork/1. Rounded Spline.ork", "Simulation 1"),
    ("ork/DarkStar_Mini[1].ork", "Simulation 2"),
]

JSON_POINTER = re.compile(r"^(/[^/]+)*(/[^/]+)*$")


def test_schema_manifest_json_pointers_and_coverage():
    source = REPO_ROOT / "ork/rockets__bt_55.ork"
    result = extract_design(source, "Simulation 1", seed=42)
    design = result["design"]
    assert design["schema_version"] == SCHEMA_VERSION
    assert design["parameter_tree"]["tag"] == "openrocket"
    assert design["reconstruction_contract"]["authoritative_for_rebuild"] == [
        "parameter_tree",
        "ork_container",
        "bundle_entries",
    ]
    for row in result["field_manifest"]:
        assert row["path"].startswith("/")
        assert "classification" in row
        assert not isinstance(row["value"], (dict, list))
        if row["path"].startswith("/parameter_tree") and row["path"].endswith("/text") and row["value"] is not None:
            assert "source_xml_path" in row
    assert not manifest_covers_design(design, result["field_manifest"])
    manifest_loaded = [
        r["path"] for r in result["field_manifest"] if "/component_index/" in r["path"] and "/loaded/" in r["path"]
    ]
    assert len(manifest_loaded) > 20
    assert any("getFinPoints" in p or "getLength" in p for p in manifest_loaded)


def test_freeform_fin_points_units_and_basis():
    source = REPO_ROOT / "ork/1. Rounded Spline.ork"
    result = extract_design(source, "Simulation 1", seed=42)
    fin_rows = [
        r
        for r in result["field_manifest"]
        if "finpoints" in r["path"]
        or "finpoints" in (r.get("source_xml_path") or "")
        or ("/attrs/x" in r["path"] and "point" in r["path"].lower())
    ]
    assert fin_rows
    assert any(r["unit"] == "m" for r in fin_rows if r["path"].endswith("/x") or r["path"].endswith("/y"))


@pytest.mark.parametrize("ork_rel,sim_name", FIXTURES)
def test_roundtrip_pass_includes_metrics(ork_rel: str, sim_name: str):
    source = REPO_ROOT / ork_rel
    extracted = extract_design(source, sim_name, seed=42)
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / "roundtrip.ork"
        report = validate_roundtrip(
            source,
            sim_name,
            extracted["design"],
            dest,
            seed=42,
        )
        assert dest.exists()
        assert report["metrics_pass"], report.get("metric_errors")
        assert report["pass"], report.get("input_errors", [])[:10]


def test_flight_metrics_strict_json():
    source = REPO_ROOT / "ork/rockets__bt_55.ork"
    metrics = extract_design(source, "Simulation 1", seed=42)["flight_metrics"]
    blob = json.dumps(metrics)
    assert "NaN" not in blob and "Infinity" not in blob
    assert metrics["apogee_m"] > 0


def test_build_ork_uses_source_tree_and_flags_contradictory_audit(tmp_path):
    source = REPO_ROOT / "ork/rockets__bt_55.ork"
    design = extract_design(source, "Simulation 1", seed=42)["design"]
    design["component_index"] = []
    dest = tmp_path / "rebuilt.ork"
    build_ork(design, dest)
    again = extract_design(dest, "Simulation 1", seed=42)
    assert again["design"]["selected_simulation"]["flight_configuration_id"]
    report = validate_roundtrip(source, "Simulation 1", design, dest, seed=42)
    assert not report["input_pass"]


def test_two_stage_bundle_attachments(tmp_path):
    source = REPO_ROOT / "ork/02.Two-stage.ork"
    design = extract_design(source, "Simulation 1", seed=42)["design"]
    assert all(not name.startswith("decals/") for name in design["bundle_entries"])
    dest = tmp_path / "two_stage.ork"
    report = validate_roundtrip(source, "Simulation 1", design, dest, seed=42)
    assert report["input_pass"]
    # Direct source-tree reconstruction avoids the native saver's trajectory drift.
    assert report["metrics_comparison_baseline"] == "original_source"
    assert report["metrics_pass"], report["metric_errors"]
    assert report["pass"], report["input_errors"]


@pytest.mark.parametrize("filename,simulation", [
    ("ork/ASCENSION.ork", "Simulation 1 (Florida baseline)"),
    ("ork/Argonia_3p120OD_K160-P_SIM_9-22-24.ork", "Simulation 12"),
    ("ork/demo-payload-separation.ork", "Simulation 1"),
    ("ork/falconHeavey.ork", "Simulation 4"),
])
def test_legacy_containers_whitespace_config_ids_and_freeform_fidelity(tmp_path, filename, simulation):
    source = REPO_ROOT / filename
    extracted = extract_design(source, simulation)
    report = validate_roundtrip(source, simulation, extracted["design"], tmp_path / "rebuilt.ork")
    assert report["pass"], report


def test_source_input_mutation_is_rejected_even_without_flight_change(tmp_path):
    source = REPO_ROOT / "ork/rockets__bt_55.ork"
    design = deepcopy(extract_design(source, "Simulation 1")["design"])
    # An inactive geometry setting or display-name change still differs from the source.
    def rename(node):
        if node["tag"] == "name" and node.get("text"):
            node["text"] += " altered"
            return True
        return any(rename(child) for child in node.get("children", []))
    assert rename(design["parameter_tree"])
    report = validate_roundtrip(source, "Simulation 1", design, tmp_path / "changed.ork")
    assert not report["input_pass"]


def test_container_magic_and_attachment_integrity():
    from scripts.sft_full_fidelity_support.ork_archive import (
        bundle_entries_from_json, bundle_entries_to_json, detect_container_format,
    )
    assert detect_container_format(b"<openrocket/>") == "plain_xml"
    assert detect_container_format(b"\xef\xbb\xbf<?xml version='1.0'?><openrocket/>") == "plain_xml"
    bundle = bundle_entries_to_json({"thrustcurves/test.rse": b"curve"})
    assert bundle_entries_from_json(bundle)["thrustcurves/test.rse"] == b"curve"
    bundle["thrustcurves/test.rse"]["data"] = "YWx0ZXJlZA=="
    with pytest.raises(ValueError, match="integrity"):
        bundle_entries_from_json(bundle)


def test_manifest_physical_units_and_exact_value_bijection():
    from scripts.sft_full_fidelity_support.manifest import build_field_manifest
    children = [
        {"tag": "material", "attrs": {"type": kind, "density": "0.1"}, "text": "Material", "children": []}
        for kind in ("bulk", "surface", "line")
    ] + [
        {"tag": "point", "attrs": {"x": "0.025", "y": "0.05"}, "text": None, "children": []},
        {"tag": "axialoffset", "attrs": {}, "text": "-0.01", "children": []},
        {"tag": "cant", "attrs": {}, "text": "2", "children": []},
        {"tag": "overridemass", "attrs": {}, "text": "0.2", "children": []},
        {"tag": "overridecg", "attrs": {}, "text": "0.3", "children": []},
    ]
    design = {"parameter_tree": {"tag": "openrocket", "attrs": {}, "text": None, "children": children}}
    manifest = build_field_manifest(design, source_file="fixture.ork", jar_sha256="test")
    by_path = {row["path"]: row for row in manifest}
    assert [by_path[f"/parameter_tree/children/{i}/attrs/density"]["unit"] for i in range(3)] == [
        "kg/m³", "kg/m²", "kg/m",
    ]
    assert by_path["/parameter_tree/children/3/attrs/x"]["unit"] == "m"
    assert by_path["/parameter_tree/children/4/text"]["unit"] == "m"
    assert by_path["/parameter_tree/children/5/text"]["unit"] == "deg"
    assert by_path["/parameter_tree/children/6/text"]["unit"] == "kg"
    assert by_path["/parameter_tree/children/7/text"]["unit"] == "m"
    assert not manifest_covers_design(design, manifest)
    assert manifest_covers_design(design, manifest + [manifest[0]])
    corrupt = deepcopy(manifest)
    corrupt[0]["value"] = "wrong"
    assert manifest_covers_design(design, corrupt)
