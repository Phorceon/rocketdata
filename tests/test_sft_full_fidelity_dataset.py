"""Tests for scripts/rebuild_sft_full_fidelity.py.

The Composer extractor (scripts/sft_full_fidelity_extract.py) is replaced by a
fake module injected into sys.modules with the EXACT agreed interface and the
real result shapes (JSON Pointer manifest with classification, roundtrip
result gated against metrics_comparison_baseline="original_source",
metric_diffs with per-key close/status and an events row).  No JVM, no network.
"""
import copy
import json
import math
import sys
import types
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import scripts.rebuild_sft_full_fidelity as R  # noqa: E402


@pytest.mark.parametrize("unit", ["m/s²", "m/s^2", "m/s2"])
def test_acceleration_unit_is_not_misread_as_altitude(unit):
    metrics = {**METRICS, "max_accel_ms2": 166.1}
    analysis = R.analyze_prompt(
        f"Design a rocket with about 69.1 m/s max velocity and about 166.1 {unit} peak acceleration.",
        composer_style_manifest(DESIGN), metrics,
    )
    assert not analysis["conflicts"]
    acceleration = [c for c in analysis["claims"] if c["kind"] == "acceleration"]
    assert len(acceleration) == 1
    assert acceleration[0]["targets"] == ["max_accel_ms2"]


def test_extractor_cache_fingerprint_tracks_support_modules(tmp_path):
    scripts = tmp_path / "scripts"
    support = scripts / "sft_full_fidelity_support"
    support.mkdir(parents=True)
    wrapper = scripts / "extractor.py"
    wrapper.write_text("# wrapper\n")
    helper = support / "manifest.py"
    helper.write_text("# first\n")
    module = types.SimpleNamespace(__file__=str(wrapper))
    before = R.extractor_fingerprint(module)
    helper.write_text("# corrected units\n")
    assert R.extractor_fingerprint(module) != before


@pytest.mark.parametrize("wording,key,value", [
    ("deployment at about", "deployment_velocity_ms", 18.2),
    ("touches down at about", "ground_hit_ms", 5.9),
    ("comes down gently, under", "ground_hit_ms", 5.9),
])
def test_speed_claim_uses_the_relevant_flight_phase(wording, key, value):
    metrics = {**METRICS, key: value, "max_velocity_ms": 400.0}
    analysis = R.analyze_prompt(
        f"Design a rocket reaching apogee with {wording} {value} m/s.",
        composer_style_manifest(DESIGN), metrics,
    )
    speed = [c for c in analysis["claims"] if c["kind"] == "speed"]
    assert len(speed) == 1
    assert speed[0]["targets"] == [key]
    assert not analysis["conflicts"]


@pytest.mark.parametrize("prompt_name,source_name", [
    ("I216", "636I216-14A"), ("F27", "F27R/L"), ("H123", "232H123-14A"),
])
def test_catalog_motor_designation_aliases(prompt_name, source_name):
    entries = [{"path": "/component_index/0/motor_configuration/motor/designation",
                "value": source_name}]
    analysis = R.analyze_prompt(f"Use an {prompt_name} motor.", entries, METRICS)
    assert not analysis["motor_conflicts"]


def test_approximate_integer_speed_keeps_its_stated_precision():
    metrics = {**METRICS, "ground_hit_ms": 3.4238}
    analysis = R.analyze_prompt(
        "Design a rocket that comes down gently, around 3 m/s.",
        composer_style_manifest(DESIGN), metrics,
    )
    assert not analysis["conflicts"]
    assert analysis["claims"][0]["rounding_tolerance_si"] == 0.5


@pytest.mark.parametrize("row_id", ["U-020", "U-268", "U-269"])
def test_user_approved_motor_label_correction_changes_only_prompt_fields(row_id):
    row = {"id": row_id, "file": "ork/rockets__bt_55.ork", "sim": "Simulation 1",
           "split": "train", "prompt_text": "Use a C11 motor to apogee in about 2.3 s.",
           "messages": [{"role": "system", "content": "unchanged"},
                        {"role": "user", "content": "Use a C11 motor to apogee in about 2.3 s."},
                        {"role": "assistant", "content": "old response"}]}
    original = copy.deepcopy(row)
    corrected, audit = R.correct_approved_motor_label(row, enabled=True)
    assert row == original
    assert corrected["prompt_text"] == original["prompt_text"].replace("C11", "C6")
    assert corrected["messages"][1]["content"] == corrected["prompt_text"]
    corrected["prompt_text"] = original["prompt_text"]
    corrected["messages"][1]["content"] = original["messages"][1]["content"]
    assert corrected == original
    assert audit["original_prompt_text"] == original["prompt_text"]


def test_motor_label_correction_requires_approval_and_exact_row_mapping():
    row = {"id": "U-020", "file": "wrong.ork", "sim": "Simulation 1"}
    assert R.correct_approved_motor_label(row, enabled=False) == (row, None)
    with pytest.raises(R.RowFailure):
        R.correct_approved_motor_label(row, enabled=True)
    other = {**row, "id": "unapproved"}
    assert R.correct_approved_motor_label(other, enabled=True) == (other, None)

SYSTEM_MSG = ("You are an autonomous aerospace design engineer. When given flight "
              "requirements, you must first calculate the required propulsion, stability, "
              "and descent parameters, then output the final verified hardware blueprint "
              "in JSON format inside <design> tags.")

METRICS = {
    "apogee_m": 83.2, "max_velocity_ms": 69.1, "max_mach": 0.202,
    "time_to_apogee_s": 2.27, "flight_time_s": 24.3, "ground_hit_ms": 3.6,
    "wind_ms": 2.0,
    "max_accel_ms2": None, "max_accel_ms2_status": "unavailable",
    "deployment_velocity_ms": None, "deployment_velocity_ms_status": "unavailable",
    "stability_cal": None, "stability_cal_status": "unavailable",
    "runtime_ms": 12.3,
    "events": [
        {"branch": 0, "type": "LIFTOFF", "t": 0.0, "t_status": "ok"},
        {"branch": 0, "type": "RECOVERY_DEVICE_DEPLOYMENT", "t": 1.7, "t_status": "ok"},
        {"branch": 0, "type": "APOGEE", "t": 2.27, "t_status": "ok"},
        {"branch": 0, "type": "GROUND_HIT", "t": 24.3, "t_status": "ok"},
    ],
}

DESIGN = {
    "schema_version": "full-fidelity-1.0",
    "reconstruction_contract": {"explicit_source_record": "parameter_tree",
                                "required_openrocket_jar_sha256": "jarsha"},
    "creator": "OpenRocket 22.02",
    "parameter_tree": {
        "tag": "rocket", "attrs": {"designer": "Estes", "version": "1.9"},
        "children": [
            {"tag": "nosecone", "attrs": {"shape": "ogive", "shapeparameter": "1.0"},
             "children": [
                 {"tag": "length", "text": 0.1016},
                 {"tag": "material", "children": [{"tag": "density", "text": 1050.0}]},
             ]},
            {"tag": "bodytube", "attrs": {"outerradius": 0.01683}, "children": [
                {"tag": "length", "text": 0.4572},
                {"tag": "motor", "attrs": {"designation": "C6", "manufacturer": "Estes"},
                 "children": []},
            ]},
            {"tag": "finpoints", "children": [
                {"tag": "point", "attrs": {"x": "0.0", "y": "0.0"}},
                {"tag": "point", "attrs": {"x": "0.05", "y": "0.038"}},
            ]},
        ],
    },
    "materialized_parameter_tree": {"tag": "rocket", "attrs": {"designer": "Estes"}},
    "bundle_entries": {"attachments/wings.csv": {"encoding": "base64", "data": "aGk=",
                                                 "sha256": "deadbeef"}},
    "selected_simulation": {"name": "Simulation 1", "index": 0,
                            "flight_configuration_id": "cfg-1"},
    "simulation_options_snapshot": {"getWindSpeedAverage": 2.0, "getLaunchRodLength": 1.0},
    "component_index": [
        {"index": 0, "name": "Nose cone", "loaded": {"getLength": 0.1016}},
        {"index": 1, "name": "Body tube", "loaded": {"getOuterRadius": 0.01683}},
    ],
}


def composer_style_manifest(design):
    """Mirror the extractor's manifest: JSON Pointers, terminal scalars,
    classification, unit/purpose/basis."""
    rows = []
    for ptr, val in R.design_leaves(design).items():
        if ptr.startswith("/component_index") or ptr.startswith("/simulation_options_snapshot"):
            cls = "audit_runtime"
        elif ptr.startswith(("/schema_version", "/reconstruction_contract")):
            cls = "schema_metadata"
        elif ptr.startswith("/materialized_parameter_tree"):
            cls = "runtime_derived"
        elif ptr.startswith("/bundle_entries"):
            cls = "archive"
        elif ptr.startswith("/creator"):
            cls = "display"
        elif ptr.startswith("/parameter_tree"):
            cls = "engineering_input"
        else:
            cls = "identity"
        rows.append({"path": ptr, "value": val,
                     "unit": "boolean" if isinstance(val, bool)
                     else ("text" if isinstance(val, str) else "dimensionless"),
                     "purpose": f"test engineering purpose for {ptr}",
                     "basis": "r1.ork explicit XML <x>",
                     "classification": cls})
    return rows


def make_rt(metrics=None, **over):
    metrics = metrics or METRICS
    diffs = {}
    for k, v in metrics.items():
        if k in ("events", "runtime_ms") or k.endswith("_status"):
            continue
        if v is None:
            diffs[k] = {"source": None, "rebuilt": None, "delta": None, "close": True,
                        "status": "unavailable_both"}
        else:
            diffs[k] = {"source": v, "rebuilt": v, "delta": 0.0, "close": True, "status": "ok"}
    diffs["events"] = {"source_count": len(metrics.get("events") or []),
                       "rebuilt_count": len(metrics.get("events") or []),
                       "close": True, "errors": []}
    rt = {"pass": True, "input_pass": True, "metrics_pass": True,
          "metrics_comparison_baseline": "original_source",
          "input_errors": [], "metric_errors": [], "metric_diffs": diffs,
          "source_vs_materialized_baseline": {}, "notes": [], "rebuilt_path": "/tmp/x.ork"}
    rt.update(over)
    return rt


class FakeExtractor:
    def __init__(self, design=None, metrics=None, rt=None, manifest=None,
                 extract_error=None, rt_error=None):
        self.design = design if design is not None else DESIGN
        self.metrics = metrics if metrics is not None else METRICS
        self.rt = rt if rt is not None else make_rt(self.metrics)
        self.manifest = manifest
        self.extract_error = extract_error
        self.rt_error = rt_error
        self.calls = []

    def extract_design(self, source_path, simulation_name, seed=42):
        self.calls.append(("extract", str(source_path), simulation_name, seed))
        if self.extract_error:
            raise self.extract_error
        manifest = (self.manifest if self.manifest is not None
                    else composer_style_manifest(self.design))
        return {"design": copy.deepcopy(self.design),
                "field_manifest": copy.deepcopy(manifest),
                "provenance": {"source_path": "ork/r1.ork", "source_sha256": "abc",
                               "selected_simulation": simulation_name,
                               "runtime": {"openrocket_jar_sha256": "jar",
                                           "java_version": "17", "uuid_seed": seed}},
                "flight_metrics": copy.deepcopy(self.metrics)}

    def build_ork(self, design, destination):
        self.calls.append(("build", str(destination)))
        p = Path(destination)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"PK-fake-ork")
        return p

    def validate_roundtrip(self, source_path, simulation_name, design, destination, seed=42):
        self.calls.append(("rt", str(source_path)))
        if self.rt_error:
            raise self.rt_error
        return copy.deepcopy(self.rt)


@pytest.fixture
def install_extractor(monkeypatch):
    def install(fake, version="v1"):
        mod = types.ModuleType("scripts.sft_full_fidelity_extract")
        mod.extract_design = fake.extract_design
        mod.build_ork = fake.build_ork
        mod.validate_roundtrip = fake.validate_roundtrip
        mod.fake_version = version
        monkeypatch.setitem(sys.modules, "scripts.sft_full_fidelity_extract", mod)
        return fake
    yield install


def make_row(rid, prompt, file="ork/r1.ork", sim="Simulation 1"):
    return {"id": rid, "file": file, "source_prompt": "ALL_UNIQUE_PROMPTS.md", "sim": sim,
            "prompt_text": prompt,
            "messages": [{"role": "system", "content": SYSTEM_MSG},
                         {"role": "user", "content": prompt},
                         {"role": "assistant",
                          "content": "<thought>old stale text</thought>\n<design>{\"old\": 1}</design>"}],
            "targets": {"apogee_m": 1.0, "max_velocity_ms": 1.0, "max_mach": 1.0,
                        "time_to_apogee_s": 1.0, "flight_time_s": 1.0, "ground_hit_ms": 1.0,
                        "wind_ms": 1.0},
            "ir_chars": 2, "split": "train"}


def write_input(tmp_path, rows, name="in.jsonl"):
    p = tmp_path / name
    p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                 encoding="utf-8")
    return p


def setup_repo(tmp_path, ork_bytes=b"fake-ork-zip-bytes"):
    (tmp_path / "ork").mkdir(exist_ok=True)
    (tmp_path / "ork" / "r1.ork").write_bytes(ork_bytes)


def run(tmp_path, input_path, extra=(), repo=None, workspace=None):
    extra = [str(e) for e in extra]
    if "--output-dir" in extra:
        out = Path(extra[extra.index("--output-dir") + 1])
    else:
        out = tmp_path / "out"
        extra += ["--output-dir", str(out)]
    rc = R.main(["--input", str(input_path), *extra],
                repo_root=str(repo or tmp_path), workspace_root=workspace)
    report = json.loads((out / "report.json").read_text())
    cand = out / "candidate" / "sft_v2_full_fidelity.jsonl"
    cand_rows = [json.loads(x) for x in cand.read_text().splitlines() if x.strip()] \
        if cand.exists() else []
    return rc, out, report, cand_rows


# --------------------------------------------------------------------------
# 1. row preservation, targets refresh, ir_chars, metadata
# --------------------------------------------------------------------------

def test_rows_preserved_order_count_prompts_and_metadata(tmp_path, install_extractor):
    install_extractor(FakeExtractor())
    setup_repo(tmp_path)
    rows = [make_row("U-001", "Design a rocket that flies on a C6 motor to apogee in about 2.3 s."),
            make_row("U-002", "Design a rocket that reaches about 84 m on a C6 motor.")]
    inp = write_input(tmp_path, rows)
    rc, out, report, cand = run(tmp_path, inp)
    assert rc == 0, report["rows"]
    assert [r["id"] for r in cand] == ["U-001", "U-002"]
    for orig, new in zip(rows, cand):
        # preserved keys and order (metadata key appended last)
        assert list(new.keys()) == list(orig.keys()) + [R.ROW_METADATA_KEY]
        for k in ("id", "file", "source_prompt", "sim", "prompt_text", "split"):
            assert new[k] == orig[k]
        # prompts stay unaltered
        assert new["messages"][0] == orig["messages"][0]
        assert new["messages"][1] == orig["messages"][1]
        assert new["prompt_text"] == orig["prompt_text"]
        # assistant content rebuilt with wrappers
        content = new["messages"][2]["content"]
        assert content.startswith("<thought>\n") and "</thought>\n<design>" in content
        assert content.endswith("</design>")
    # stale targets refreshed from verified extractor metrics, ir_chars from JSON
    d = R.design_leaves(DESIGN)
    design_json = R.json_dump_strict(DESIGN)
    assert len(d) > 15
    for new in cand:
        assert list(new["targets"].keys()) == R.TARGET_KEYS
        for k in R.TARGET_KEYS:
            assert new["targets"][k] == METRICS[k]
        assert new["ir_chars"] == len(design_json)
        ff = new[R.ROW_METADATA_KEY]
        assert ff["schema"] == R.SCHEMA_ID
        assert ff["source"]["file_repo_rel"] == "ork/r1.ork"
        assert ff["source"]["seed"] == 42
        assert "PENDING" in ff["generator"]["independent_review"]
        assert ff["coverage"]["manifest_entries"] == len(d)


def test_thought_covers_every_manifest_leaf_exactly(tmp_path, install_extractor):
    install_extractor(FakeExtractor())
    setup_repo(tmp_path)
    rows = [make_row("U-001", "Design a rocket that flies on a C6 motor to apogee in about 2.3 s.")]
    inp = write_input(tmp_path, rows)
    rc, out, report, cand = run(tmp_path, inp)
    assert rc == 0, report["rows"]
    content = cand[0]["messages"][2]["content"]
    thought = content.split("</thought>")[0]
    parsed = {p["path"]: p for p in R.parse_thought_fields(thought)}
    manifest = composer_style_manifest(DESIGN)
    assert len(parsed) == len(manifest)
    for e in manifest:
        p = parsed[e["path"]]
        assert R.values_equal(p["value"], e["value"]), e["path"]
        assert p["unit"] == e["unit"] and p["purpose"] == e["purpose"] and p["basis"] == e["basis"]
        assert p["class"] == e["classification"]
    # identity/display and audit data explicitly classified, never as physics
    assert parsed["/creator"]["class"] == "display"
    assert parsed["/parameter_tree/attrs/designer"]["class"] == "engineering_input"
    assert parsed["/component_index/0/name"]["class"] == "audit_runtime"
    assert "parameter_tree is the authoritative" in thought
    assert "audit" in thought and "would not change the reconstructed geometry" in thought
    assert "no design intent is invented" in thought
    assert "not a blanket claim that every requirement is met" in thought


# --------------------------------------------------------------------------
# 2. manifest contract rejections
# --------------------------------------------------------------------------

def test_manifest_contract_violations_block(tmp_path, install_extractor):
    setup_repo(tmp_path)
    base_rows = [make_row("U-001", "Design a rocket that flies on a C6 motor to apogee in about 2.3 s.")]
    inp = write_input(tmp_path, base_rows)

    leaves = sorted(R.design_leaves(DESIGN))
    def broken(kind):
        if kind == "object_value":
            m = composer_style_manifest(DESIGN)
            m[3] = {**m[3], "value": {"nested": 1}}
            return m
        if kind == "duplicate":
            m = composer_style_manifest(DESIGN)
            m.append(dict(m[0]))
            return m
        if kind == "value_mismatch":
            m = composer_style_manifest(DESIGN)
            m[2] = {**m[2], "value": m[2]["value"] + 1 if isinstance(m[2]["value"], (int, float))
                    else "wrong"}
            return m
        if kind == "missing_leaf":
            m = [e for e in composer_style_manifest(DESIGN) if e["path"] != "/creator"]
            return m
        if kind == "leak":
            m = composer_style_manifest(DESIGN)
            m[1] = {**m[1], "basis": "/Users/someone/secret/r1.ork XML"}
            return m
        if kind == "bad_pointer":
            m = composer_style_manifest(DESIGN)
            m[1] = {**m[1], "path": "/parameter_tree/children/99/text"}
            return m
        raise AssertionError(kind)

    for kind in ("object_value", "duplicate", "value_mismatch", "missing_leaf", "leak",
                 "bad_pointer"):
        fake = install_extractor(FakeExtractor(manifest=broken(kind)), version=kind)
        out = tmp_path / f"out_{kind}"
        rc = R.main(["--input", str(inp), "--output-dir", str(out)],
                    repo_root=str(tmp_path), workspace_root=None)
        assert rc == 1, (kind, "expected row failure")
        rep = json.loads((out / "report.json").read_text())
        assert rep["rows"][0]["status"] == "fail"
        reason = " | ".join(rep["rows"][0]["reasons"])
        assert kind in ("leak",) or reason, kind
        if kind == "object_value":
            assert "terminal scalar" in reason
        if kind == "duplicate":
            assert "duplicate path" in reason
        if kind == "value_mismatch":
            assert "!= design leaf" in reason
        if kind == "missing_leaf":
            assert "does not cover design leaf" in reason
        if kind == "leak":
            assert "leaks an absolute/local path" in reason
        if kind == "bad_pointer":
            assert "does not resolve" in reason
        cand = out / "candidate" / "sft_v2_full_fidelity.jsonl"
        assert not cand.read_text().strip(), "failed row must not enter the candidate"


# --------------------------------------------------------------------------
# 3. roundtrip acceptance: input_pass AND metrics/events/options vs ORIGINAL
# --------------------------------------------------------------------------

def test_roundtrip_gate_requires_all_flags_original_baseline(tmp_path, install_extractor):
    setup_repo(tmp_path)
    rows = [make_row("U-001", "Design a rocket that flies on a C6 motor to apogee in about 2.3 s.")]
    inp = write_input(tmp_path, rows)

    # bare pass flag only -> insufficient evidence, must block
    install_extractor(FakeExtractor(rt={"pass": True}), version="bare")
    rc, out, report, cand = run(tmp_path, inp, extra=("--output-dir", str(tmp_path / "o1")))
    assert rc == 1
    assert any("insufficient evidence" in r for r in report["rows"][0]["reasons"])

    # baseline must be original_source (never a normalized baseline)
    install_extractor(FakeExtractor(rt=make_rt(METRICS,
                                                metrics_comparison_baseline="materialized")),
                      version="base")
    rc, out, report, _ = run(tmp_path, inp, extra=("--output-dir", str(tmp_path / "o2")))
    assert rc == 1
    assert any("original_source" in r for r in report["rows"][0]["reasons"])

    # metrics_pass False -> block even if the combined pass flag is True
    rt = make_rt(METRICS, metrics_pass=False)
    rt["pass"] = True  # a lying combined flag must not be sufficient alone
    install_extractor(FakeExtractor(rt=rt), version="mfail")
    rc, out, report, _ = run(tmp_path, inp, extra=("--output-dir", str(tmp_path / "o3")))
    assert rc == 1
    assert any("metrics_pass is False" in r for r in report["rows"][0]["reasons"])

    # input_pass False -> block
    install_extractor(FakeExtractor(rt=make_rt(METRICS, input_pass=False,
                                                input_errors=["manifest mismatch at /x"])),
                      version="ifail")
    rc, out, report, _ = run(tmp_path, inp, extra=("--output-dir", str(tmp_path / "o4")))
    assert rc == 1
    assert any("input_pass is False" in r for r in report["rows"][0]["reasons"])
    assert any("manifest mismatch" in r for r in report["rows"][0]["reasons"])


def test_roundtrip_required_metric_mismatch_blocks(tmp_path, install_extractor):
    setup_repo(tmp_path)
    rows = [make_row("U-001", "Design a rocket that flies on a C6 motor to apogee in about 2.3 s.")]
    inp = write_input(tmp_path, rows)
    rt = make_rt(METRICS)
    drifted = dict(rt["metric_diffs"]["apogee_m"])
    drifted.update(rebuilt=91.0, delta=7.8, close=False)  # original-vs-native drift
    rt["metric_diffs"]["apogee_m"] = drifted
    rt["metric_errors"] = ["mandatory metric mismatch or missing: apogee_m"]
    install_extractor(FakeExtractor(rt=rt), version="drift")
    rc, out, report, cand = run(tmp_path, inp)
    assert rc == 1
    reasons = " | ".join(report["rows"][0]["reasons"])
    assert "apogee_m" in reasons and "does not match the original source" in reasons
    assert not cand


def test_optional_metrics_unavailable_both_sides_pass_and_are_marked(tmp_path, install_extractor):
    install_extractor(FakeExtractor())
    setup_repo(tmp_path)
    rows = [make_row("U-001", "Design a rocket that flies on a C6 motor to apogee in about 2.3 s.")]
    inp = write_input(tmp_path, rows)
    rc, out, report, cand = run(tmp_path, inp)
    assert rc == 0, report["rows"]
    ff = cand[0][R.ROW_METADATA_KEY]
    assert set(ff["roundtrip"]["unavailable_metrics"]) == {"max_accel_ms2",
                                                           "deployment_velocity_ms",
                                                           "stability_cal"}
    # unavailable optionals never create targets
    assert "stability_cal" not in cand[0]["targets"]
    assert all(math.isfinite(v) for v in cand[0]["targets"].values())
    assert ff["coverage"]["unavailable_metrics"] == ff["roundtrip"]["unavailable_metrics"]


def test_optional_metric_availability_mismatch_blocks(tmp_path, install_extractor):
    setup_repo(tmp_path)
    rows = [make_row("U-001", "Design a rocket that flies on a C6 motor to apogee in about 2.3 s.")]
    inp = write_input(tmp_path, rows)
    rt = make_rt(METRICS)
    rt["metric_diffs"]["stability_cal"] = {"source": None, "rebuilt": 1.4, "delta": None,
                                           "close": False, "status": "availability_mismatch"}
    install_extractor(FakeExtractor(rt=rt), version="avail")
    rc, out, report, _ = run(tmp_path, inp)
    assert rc == 1
    assert any("availability mismatch" in r and "stability_cal" in r
               for r in report["rows"][0]["reasons"])


def test_event_sequence_gate(tmp_path, install_extractor):
    setup_repo(tmp_path)
    rows = [make_row("U-001", "Design a rocket that flies on a C6 motor to apogee in about 2.3 s.")]
    inp = write_input(tmp_path, rows)

    # rebuilt event sequence differs -> block
    rt = make_rt(METRICS)
    rt["metric_diffs"]["events"] = {"source_count": 4, "rebuilt_count": 3, "close": False,
                                    "errors": ["event count 4 vs 3"]}
    install_extractor(FakeExtractor(rt=rt), version="ev1")
    rc, out, report, _ = run(tmp_path, inp, extra=("--output-dir", str(tmp_path / "o1")))
    assert rc == 1
    assert any("event sequence" in r for r in report["rows"][0]["reasons"])

    # source events missing GROUND_HIT -> block (source-side requirement)
    bad_metrics = copy.deepcopy(METRICS)
    bad_metrics["events"] = [e for e in bad_metrics["events"] if e["type"] != "GROUND_HIT"]
    install_extractor(FakeExtractor(metrics=bad_metrics,
                                    rt=make_rt(bad_metrics)), version="ev2")
    rc, out, report, _ = run(tmp_path, inp, extra=("--output-dir", str(tmp_path / "o2")))
    assert rc == 1
    assert any("events lack GROUND_HIT" in r for r in report["rows"][0]["reasons"])


def test_recovery_event_required_when_design_has_parachute(tmp_path, install_extractor):
    setup_repo(tmp_path)
    design = copy.deepcopy(DESIGN)
    design["component_index"].append({"index": 2, "name": "Parachute",
                                      "loaded": {"getDeployDelay": 5.0}})
    good = copy.deepcopy(METRICS)
    install_extractor(FakeExtractor(design=design, metrics=good,
                                    rt=make_rt(good)), version="rec1")
    rows = [make_row("U-001", "Design a rocket that flies on a C6 motor to apogee in about 2.3 s.")]
    inp = write_input(tmp_path, rows)
    rc, out, report, cand = run(tmp_path, inp, extra=("--output-dir", str(tmp_path / "o1")))
    assert rc == 0, report["rows"]

    no_dep = copy.deepcopy(METRICS)
    no_dep["events"] = [e for e in no_dep["events"] if e["type"] != "RECOVERY_DEVICE_DEPLOYMENT"]
    install_extractor(FakeExtractor(design=design, metrics=no_dep,
                                    rt=make_rt(no_dep)), version="rec2")
    rc, out, report, _ = run(tmp_path, inp, extra=("--output-dir", str(tmp_path / "o2")))
    assert rc == 1
    assert any("RECOVERY_DEVICE_DEPLOYMENT" in r for r in report["rows"][0]["reasons"])


# --------------------------------------------------------------------------
# 4. prompt-vs-config conflicts (U-020 case): reported and blocked, prompt kept
# --------------------------------------------------------------------------

def test_motor_contradiction_blocks_row_keeps_prompt(tmp_path, install_extractor):
    install_extractor(FakeExtractor())
    setup_repo(tmp_path)
    rows = [make_row("U-020", "Design a rocket that goes on a C11 motor to apogee in about 2.3 s."),
            make_row("U-021", "Design a rocket that flies on a C6 motor to apogee in about 2.3 s.")]
    inp = write_input(tmp_path, rows)
    rc, out, report, cand = run(tmp_path, inp)
    assert rc == 1
    assert [r["id"] for r in cand] == ["U-021"]  # conflicting row never emitted
    u020 = [r for r in report["rows"] if r["id"] == "U-020"][0]
    assert u020["status"] == "fail"
    assert any("prompt motor token 'C11'" in r and "'C6'" in r for r in u020["reasons"])
    assert u020["prompt"]["motor_conflicts"] == ["C11"]
    # the original prompt text is untouched everywhere it appears
    src_row = json.loads(inp.read_text().splitlines()[0])
    assert src_row["prompt_text"] == "Design a rocket that goes on a C11 motor to apogee in about 2.3 s."


def test_numeric_claim_conflicts_block_but_budget_only_warns(tmp_path, install_extractor):
    install_extractor(FakeExtractor())
    setup_repo(tmp_path)
    rows = [make_row("U-001", "Design a rocket that reaches about 300 m under $35 on a C6 motor.")]
    inp = write_input(tmp_path, rows)
    rc, out, report, cand = run(tmp_path, inp)
    assert rc == 1
    reasons = " | ".join(report["rows"][0]["reasons"])
    assert "300 m" in reasons and "conflicts with verified metrics" in reasons
    # budget claim is only a warning (no cost metric exists); never claimed as met
    assert any("$35" in w for w in report["rows"][0]["warnings"])
    assert not any("$35" in r for r in report["rows"][0]["reasons"])


def test_len_small_claims_are_warnings_not_conflicts(tmp_path, install_extractor):
    install_extractor(FakeExtractor())
    setup_repo(tmp_path)
    rows = [make_row("U-001", "Design a rocket on a C6 motor with 35 mm airframe, "
                                 "apogee about 84 m.")]
    inp = write_input(tmp_path, rows)
    rc, out, report, cand = run(tmp_path, inp)
    assert rc == 0, report["rows"][0]["reasons"]
    assert any("35 mm" in w for w in report["rows"][0]["warnings"])


# --------------------------------------------------------------------------
# 5. extractor / input robustness
# --------------------------------------------------------------------------

def test_extractor_failures_block_cleanly(tmp_path, install_extractor):
    setup_repo(tmp_path)
    rows = [make_row("U-001", "Design a rocket on a C6 motor."),
            make_row("U-002", "Design a rocket on a C6 motor.")]
    inp = write_input(tmp_path, rows)

    install_extractor(FakeExtractor(extract_error=RuntimeError("sim not loadable")),
                      version="e1")
    rc, out, report, _ = run(tmp_path, inp, extra=("--output-dir", str(tmp_path / "o1")))
    assert rc == 1
    assert any("extract_design failed" in r and "sim not loadable" in r
               for r in report["rows"][0]["reasons"])

    install_extractor(FakeExtractor(rt_error=RuntimeError("jvm boom")), version="e2")
    rc, out, report, _ = run(tmp_path, inp, extra=("--output-dir", str(tmp_path / "o2")))
    assert rc == 1
    assert any("validate_roundtrip failed" in r and "jvm boom" in r
               for r in report["rows"][0]["reasons"])


def test_missing_extractor_blocks_with_code_3(tmp_path, monkeypatch):
    setup_repo(tmp_path)
    rows = [make_row("U-001", "Design a rocket on a C6 motor.")]
    inp = write_input(tmp_path, rows)
    out = tmp_path / "out"
    rc = R.main(["--input", str(inp), "--output-dir", str(out)],
                repo_root=str(tmp_path), workspace_root=None,
                extractor_module_name="scripts.does_not_exist_xyz")
    assert rc == 3
    assert not (out / "candidate").exists() or \
        not (out / "candidate" / "sft_v2_full_fidelity.jsonl").exists()


def test_nan_design_and_missing_metrics_block(tmp_path, install_extractor):
    setup_repo(tmp_path)
    rows = [make_row("U-001", "Design a rocket on a C6 motor.")]
    inp = write_input(tmp_path, rows)

    bad_design = copy.deepcopy(DESIGN)
    bad_design["parameter_tree"]["children"][0]["children"][0]["text"] = float("nan")
    install_extractor(FakeExtractor(design=bad_design), version="n1")
    rc, out, report, _ = run(tmp_path, inp, extra=("--output-dir", str(tmp_path / "o1")))
    assert rc == 1
    assert any("finite" in r for r in report["rows"][0]["reasons"])

    bad_metrics = {k: v for k, v in METRICS.items() if k != "ground_hit_ms"}
    install_extractor(FakeExtractor(metrics=bad_metrics, rt=make_rt(bad_metrics)),
                      version="n2")
    rc, out, report, _ = run(tmp_path, inp, extra=("--output-dir", str(tmp_path / "o2")))
    assert rc == 1
    assert any("ground_hit_ms" in r for r in report["rows"][0]["reasons"])


def test_unknown_source_file_blocks(tmp_path, install_extractor):
    install_extractor(FakeExtractor())
    setup_repo(tmp_path)
    rows = [make_row("U-001", "Design a rocket on a C6 motor.", file="ork/missing.ork")]
    inp = write_input(tmp_path, rows)
    rc, out, report, _ = run(tmp_path, inp)
    assert rc == 1
    assert any("not found in repository" in r for r in report["rows"][0]["reasons"])


def test_workspace_fallback_requires_named_simulation(tmp_path, install_extractor):
    install_extractor(FakeExtractor())
    # NOTE: no repository copy of ork/r1.ork here - only the workspace has it
    ws = tmp_path / "workspace"
    (ws / "ork").mkdir(parents=True)
    (ws / "ork" / "r1.ork").write_bytes(b"workspace-copy")
    rows = [make_row("U-001", "Design a rocket on a C6 motor.")]
    inp = write_input(tmp_path, rows, name="in_ws.jsonl")

    # workspace copy cannot be verified to hold the named simulation -> block
    rc, out, report, _ = run(tmp_path, inp, repo=tmp_path, workspace=ws)
    assert rc == 1
    assert any("does not contain simulation" in r for r in report["rows"][0]["reasons"])

    # a verifiable workspace .ork (real zip with the named sim) is accepted
    import zipfile
    sim_xml = ("<rocket><simulations><simulation><name>Simulation 1</name>"
               "</simulation></simulations></rocket>")
    with zipfile.ZipFile(ws / "ork" / "r1.ork", "w") as zf:
        zf.writestr("rocket.ork", sim_xml)
    rc, out, report, cand = run(tmp_path, inp, repo=tmp_path, workspace=ws)
    assert rc == 0, report["rows"][0]["reasons"]
    assert "workspace" in report["rows"][0]["source_strategy"]


# --------------------------------------------------------------------------
# 6. snapshot protection, cache, determinism, apply gates
# --------------------------------------------------------------------------

def test_snapshot_protects_original_and_rerun_reads_snapshot(tmp_path, install_extractor):
    fake = install_extractor(FakeExtractor())
    setup_repo(tmp_path)
    rows = [make_row("U-001", "Design a rocket on a C6 motor."),
            make_row("U-002", "Design a rocket that reaches about 84 m on a C6 motor.")]
    inp = write_input(tmp_path, rows)
    original_bytes = inp.read_bytes()

    rc1, out, rep1, cand1 = run(tmp_path, inp)
    assert rc1 == 0
    snap = out / "original_snapshot" / "original__in.jsonl"
    assert snap.read_bytes() == original_bytes

    # a different input with the same output dir must never overwrite the backup
    inp.write_bytes(b'{"id": "DIFFERENT"}\n')
    rc = R.main(["--input", str(inp), "--output-dir", str(out)],
                repo_root=str(tmp_path), workspace_root=None)
    assert rc == 3
    assert snap.read_bytes() == original_bytes

    # restore identical input: rerun works and reads the immutable snapshot,
    # not its own previous output
    inp.write_bytes(original_bytes)
    (out / "candidate" / "sft_v2_full_fidelity.jsonl").write_text("CORRUPTED")
    rc, out, rep2, cand2 = run(tmp_path, inp)
    assert rc == 0
    assert snap.read_bytes() == original_bytes
    assert [r["id"] for r in cand2] == ["U-001", "U-002"]


def test_cache_by_file_sim_seed_sourcehash(tmp_path, install_extractor):
    fake = install_extractor(FakeExtractor())
    setup_repo(tmp_path)
    rows = [make_row("U-001", "Design a rocket that flies on a C6 motor to apogee in about 2.3 s."),
            make_row("U-002", "Design a rocket that reaches about 84 m on a C6 motor."),
            make_row("U-003", "Design a rocket on a C6 motor.", sim="Simulation 2")]
    inp = write_input(tmp_path, rows)
    rc, out, report, cand = run(tmp_path, inp)
    assert rc == 0, [r["reasons"] for r in report["rows"]]
    # rows 1-2 share (file, sim, seed, hash): exactly 2 extracts; row 2 hits the
    # cache stored by row 1 within the same run
    assert report["extract_calls"] == 2
    assert report["cache_hits"] == 1
    assert len(list((out / "cache").glob("*.json"))) == 2

    # rerun over the same output dir: everything cached
    rc, out, report2, cand2 = run(tmp_path, inp)
    assert rc == 0
    assert report2["extract_calls"] == 0
    assert report2["cache_hits"] == 3
    assert cand2 == cand

    # changed source bytes invalidate the cache
    setup_repo(tmp_path, ork_bytes=b"changed-bytes")
    rc, out, report3, _ = run(tmp_path, inp)
    assert rc == 0
    assert report3["extract_calls"] == 2

    # a new extractor fingerprint invalidates the cache too
    install_extractor(FakeExtractor(), version="v2")
    rc, out, report4, _ = run(tmp_path, inp)
    assert report4["extract_calls"] == 2  # full re-extract after extractor change


def test_deterministic_repeat_generation(tmp_path, install_extractor):
    install_extractor(FakeExtractor())
    setup_repo(tmp_path)
    rows = [make_row("U-001", "Design a rocket that flies on a C6 motor to apogee in about 2.3 s."),
            make_row("U-002", "Design a rocket that reaches about 84 m on a C6 motor.")]
    inp = write_input(tmp_path, rows)
    rc1, out1, _, _ = run(tmp_path, inp, extra=("--output-dir", str(tmp_path / "d1")))
    rc2, out2, _, _ = run(tmp_path, inp, extra=("--output-dir", str(tmp_path / "d2")))
    assert rc1 == rc2 == 0
    b1 = (out1 / "candidate" / "sft_v2_full_fidelity.jsonl").read_bytes()
    b2 = (out2 / "candidate" / "sft_v2_full_fidelity.jsonl").read_bytes()
    assert b1 == b2


def test_apply_gates(tmp_path, install_extractor):
    install_extractor(FakeExtractor())
    setup_repo(tmp_path)

    # --limit with --apply is a usage error: a sample can never replace the dataset
    rows3 = [make_row(f"U-00{i}", "Design a rocket on a C6 motor.") for i in (1, 2, 3)]
    inp = write_input(tmp_path, rows3)
    out = tmp_path / "o_lim"
    rc = R.main(["--input", str(inp), "--output-dir", str(out), "--limit", "2", "--apply"],
                repo_root=str(tmp_path), workspace_root=None)
    assert rc == 2
    assert inp.read_text().startswith('{"id": "U-001"')

    # a failing row refuses apply and preserves the original file
    install_extractor(FakeExtractor(), version="v1")
    rows_bad = [make_row("U-001", "Design a rocket that goes on a C11 motor to apogee in about 2.3 s."),
                make_row("U-002", "Design a rocket on a C6 motor.")]
    inp_bad = write_input(tmp_path, rows_bad, name="in_bad.jsonl")
    original_bad = inp_bad.read_bytes()
    out_b = tmp_path / "o_bad"
    rc = R.main(["--input", str(inp_bad), "--output-dir", str(out_b), "--apply"],
                repo_root=str(tmp_path), workspace_root=None)
    assert rc == 1
    assert inp_bad.read_bytes() == original_bad
    assert not (out_b / "APPLIED.json").exists()

    # all rows pass -> apply replaces the input with the candidate
    inp_ok = write_input(tmp_path, rows3, name="in_ok.jsonl")
    original_ok = inp_ok.read_bytes()
    out_ok = tmp_path / "o_ok"
    rc = R.main(["--input", str(inp_ok), "--output-dir", str(out_ok), "--apply"],
                repo_root=str(tmp_path), workspace_root=None)
    assert rc == 0
    candidate_bytes = (out_ok / "candidate" / "sft_v2_full_fidelity.jsonl").read_bytes()
    assert inp_ok.read_bytes() == candidate_bytes
    assert (out_ok / "APPLIED.json").exists()
    snap = (out_ok / "original_snapshot" / "original__in_ok.jsonl")
    assert snap.read_bytes() == original_ok

    # applying again refuses: the replaced input no longer matches the immutable
    # snapshot (rc 3 at the snapshot gate, before any processing)
    rc = R.main(["--input", str(inp_ok), "--output-dir", str(out_ok), "--apply"],
                repo_root=str(tmp_path), workspace_root=None)
    assert rc == 3


def test_do_apply_refuses_partial_candidate(tmp_path):
    inp = tmp_path / "x.jsonl"
    inp.write_text("a\nb\nc\n")
    snap = tmp_path / "snap.jsonl"
    snap.write_text("a\nb\nc\n")
    cand = tmp_path / "cand.jsonl"
    cand.write_text("a\n")
    rc = R.do_apply(inp, snap, cand, 3, 1, tmp_path, {})
    assert rc == 1
    assert inp.read_text() == "a\nb\nc\n"


# --------------------------------------------------------------------------
# 7. duplicate ids, source mapping, size accounting
# --------------------------------------------------------------------------

def test_duplicate_ids_preserved_and_reported(tmp_path, install_extractor):
    install_extractor(FakeExtractor())
    setup_repo(tmp_path)
    rows = [make_row("U-DUP", "Design a rocket that reaches about 84 m on a C6 motor."),
            make_row("U-DUP", "Design a rocket that flies on a C6 motor to apogee in about 2.3 s.")]
    inp = write_input(tmp_path, rows)
    rc, out, report, cand = run(tmp_path, inp)
    assert rc == 0, [r["reasons"] for r in report["rows"]]
    assert [r["id"] for r in cand] == ["U-DUP", "U-DUP"]
    assert report["duplicate_ids_in_original"] == {"U-DUP": 2}
    assert report["duplicate_ids_introduced"] == []


def test_source_mapping_and_size_accounting_reported(tmp_path, install_extractor):
    install_extractor(FakeExtractor())
    setup_repo(tmp_path)
    rows = [make_row("U-001", "Design a rocket that flies on a C6 motor to apogee in about 2.3 s.")]
    inp = write_input(tmp_path, rows)
    rc, out, report, cand = run(tmp_path, inp)
    assert rc == 0
    row = report["rows"][0]
    assert row["source_resolved"] == "ork/r1.ork"
    assert row["source_strategy"] == "repository"
    assert len(row["source_sha256"]) == 64
    assert report["size_stats"]["content_chars"]["max"] == \
        len(cand[0]["messages"][2]["content"])
    assert report["size_stats"]["design_chars"]["max"] == cand[0]["ir_chars"]
    assert report["size_stats"]["thought_chars"]["max"] > 0


def test_metadata_and_prompts_never_leak_local_paths(tmp_path, install_extractor):
    install_extractor(FakeExtractor())
    setup_repo(tmp_path)
    rows = [make_row("U-001", "Design a rocket that flies on a C6 motor to apogee in about 2.3 s.")]
    inp = write_input(tmp_path, rows)
    rc, out, report, cand = run(tmp_path, inp)
    assert rc == 0
    text = json.dumps(cand)
    assert "/Users/" not in text and str(tmp_path) not in text


# --------------------------------------------------------------------------
# 8. unit checks for the acceptance/analysis helpers
# --------------------------------------------------------------------------

def test_accept_roundtrip_unit_shapes():
    entries = composer_style_manifest(DESIGN)
    extract = {"flight_metrics": METRICS}
    ok, problems, notes, unavailable = R.accept_roundtrip(make_rt(METRICS), extract, entries)
    assert ok, problems
    assert set(unavailable) == {"max_accel_ms2", "deployment_velocity_ms", "stability_cal"}

    ok, problems, _, _ = R.accept_roundtrip({"pass": True}, extract, entries)
    assert not ok and any("insufficient evidence" in p for p in problems)

    ok, problems, _, _ = R.accept_roundtrip(make_rt(METRICS,
                                                     metrics_comparison_baseline="normalized"),
                                            extract, entries)
    assert not ok and any("original_source" in p for p in problems)


def test_analyze_prompt_unit():
    entries = composer_style_manifest(DESIGN)
    res = R.analyze_prompt("Design a rocket that goes on a C11 motor to apogee in about 2.3 s.",
                           entries, METRICS)
    assert res["motor_conflicts"] == ["C11"]
    res = R.analyze_prompt("Design a rocket that goes on a C6-5 motor to apogee in about 2.3 s.",
                           entries, METRICS)
    assert res["motor_conflicts"] == []
    res = R.analyze_prompt("Design a rocket that reaches 800 feet on a C6 motor.",
                           entries, {**METRICS, "apogee_m": 243.8})
    assert res["conflicts"] == []
    res = R.analyze_prompt("Total flight time under 25 s on a C6 motor, apogee about 84 m.",
                           entries, {**METRICS, "flight_time_s": 30.7, "apogee_m": 83.2})
    assert any("under 25" in c for c in res["conflicts"])
