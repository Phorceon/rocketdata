"""Pure, flight-free tests for the complete v4 catalog assembly.

The assembler is exercised end-to-end against representative mock fixtures
(the current source-contract shapes) with a fake tokenizer; no JVM, no
transformers download, no flights, no writes outside tmp_path.
"""
import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.sft_v4_assemble import (  # noqa: E402
    HARDWARE_MISSING,
    MAIN_FILE,
    SPLIT_FILES,
    ContractError,
    assemble,
    ceil_bound,
    conversation_tokens,
    design_from_row,
    geometry_key,
    hardware_prompt,
    sig3_plain,
    source_key,
    validate_source_contract,
)
from scripts.sft_v4_assemble_fixtures import (  # noqa: E402
    MOCK_DIGEST,
    MOCK_LOOKUP,
    MOCK_UNRESOLVED_DIGEST,
    mock_compact,
    mock_dump,
    mock_eng,
    mock_record,
    smoke_records,
    write_source_dir,
)
from scripts.sft_compact_motor_ids import apply_stage2_and_fix  # noqa: E402


class FakeTokenizer:
    """Deterministic stand-in: one token per character of the full render."""

    def apply_chat_template(self, messages, tokenize, add_generation_prompt):
        assert tokenize is False
        assert add_generation_prompt is False
        return "".join(m["content"] for m in messages)

    def encode(self, text, add_special_tokens):
        assert add_special_tokens is False
        return [0] * len(text)


def make_sources(tmp_path, records=None, **kwargs):
    records = records if records is not None else smoke_records()
    sources, catalog = write_source_dir(tmp_path / "sources", records=records,
                                        **kwargs)
    return sources, catalog, records


def run_assemble(tmp_path, records=None, token_limit=32768, **kwargs):
    sources, catalog, recs = make_sources(tmp_path, records=records)
    output = tmp_path / "out"
    report = assemble(sources, output, catalog, token_limit=token_limit,
                      tokenizer=FakeTokenizer(), overwrite=True, **kwargs)
    rows = [json.loads(line) for line in (output / MAIN_FILE).read_text()
            .splitlines() if line.strip()]
    return report, rows, output


def rows_by_catalog(rows):
    return {row["catalog_id"]: row for row in rows}


# ---------------------------------------------------------------------------
# pure helpers
# ---------------------------------------------------------------------------

def test_conversation_tokens_counts_ids_not_encoding_fields():
    class Tokenizer:
        def apply_chat_template(self, messages, tokenize, add_generation_prompt):
            assert tokenize is False
            assert add_generation_prompt is False
            return "complete conversation"

        def encode(self, text, add_special_tokens):
            assert text == "complete conversation"
            assert add_special_tokens is False
            return list(range(123))

    assert conversation_tokens(Tokenizer(), []) == 123


def test_prompt_bounds_satisfy_saved_outcomes():
    assert sig3_plain(491.609) == "492"
    assert sig3_plain(1234.56) == "1230"  # never scientific notation
    assert ceil_bound(2.669) == "2.7"
    assert ceil_bound(0.0) == "0.1"
    # a stored outcome always satisfies the bound the prompt asks for
    for value in (0.0, 2.669, 6.0, 9.9, 116.768):
        assert value < float(ceil_bound(value))
        assert abs(float(sig3_plain(value)) - value) <= max(abs(value) * 0.01,
                                                            0.05)


def test_source_key_groups_filled_and_original():
    assert source_key("/a/ork_filled/Alpha_filled.ork") == source_key("ork/Alpha.ork")


def test_geometry_ignores_motor_identity_but_not_structure():
    a = mock_compact()
    b = mock_compact(digest=MOCK_UNRESOLVED_DIGEST, designation="F9X")
    assert geometry_key(a) == geometry_key(b)
    assert geometry_key(a) != geometry_key(mock_compact(body_length=0.5))


# ---------------------------------------------------------------------------
# end-to-end mock assembly
# ---------------------------------------------------------------------------

def test_exact_one_row_per_catalog_id_despite_duplicate_designs(tmp_path):
    report, rows, output = run_assemble(tmp_path)
    records = smoke_records()
    assert report["rows"] == len(records) == 8
    assert [row["catalog_id"] for row in rows] == [r["catalog_id"]
                                                   for r in records]
    assert [row["id"] for row in rows] == [f"V4-{i:04d}" for i in
                                           range(1, len(rows) + 1)]
    by_id = rows_by_catalog(rows)
    # duplicate hardware families are both kept, not deduplicated away
    assert by_id["original:mock_alpha.ork"]["targets"] == \
        by_id["motor_filled:mock_alpha_filled.ork"]["targets"]
    assert geometry_key(design_from_row(
        by_id["original:mock_delta.ork"])) == geometry_key(design_from_row(
        by_id["original:mock_foxtrot.ork"]))
    assert report["catalog_rockets_included"] == report["rows"]
    assert report["excluded_records"] == 0


def test_design_is_complete_and_never_truncated(tmp_path):
    _report, rows, _output = run_assemble(tmp_path)
    id_by_digest = {entry["digest"]: mid for mid, entry in MOCK_LOOKUP.items()}
    records = {r["catalog_id"]: r for r in smoke_records()}
    for row in rows:
        record = records[row["catalog_id"]]
        expected_design, _fixes = apply_stage2_and_fix(
            record["compact"], id_by_digest, record["digest_entry"]["components"])
        assert design_from_row(row) == expected_design
        content = row["messages"][2]["content"]
        assert content.count("<thought>") == content.count("</thought>") == 1
        assert content.count("<design>") == content.count("</design>") == 1


def test_flight_rows_use_reference_data_not_circular_verification(tmp_path):
    _report, rows, _output = run_assemble(tmp_path)
    row = rows_by_catalog(rows)["original:mock_alpha.ork"]
    assistant = row["messages"][2]["content"]
    assert "REFERENCE FLIGHT (stored results for this exact design" in assistant
    assert "vs target" not in assistant
    assert "82.623" in assistant  # the exact stored apogee, as recorded data
    assert "marked up to date" in assistant
    assert "saved_flight_not_rerun" in row["flags"]
    prompt = row["messages"][1]["content"]
    assert "about 82.6 m apogee" in prompt
    assert "under 3.7 m/s" in prompt
    assert "under 30.7 s" in prompt


def test_outdated_saved_results_are_flagged_and_worded_honestly(tmp_path):
    _report, rows, _output = run_assemble(tmp_path)
    row = rows_by_catalog(rows)["original:mock_bravo.ork"]
    assert row["simulation_status"] == "outdated"
    assert "saved_simulation_not_uptodate" in row["flags"]
    assistant = row["messages"][2]["content"]
    assert "historical reference only" in assistant
    assert "guarantee" in assistant  # explicitly disclaimed


def test_hard_landing_source_is_kept_with_warnings_not_certified_safe(tmp_path):
    _report, rows, _output = run_assemble(tmp_path)
    row = rows_by_catalog(rows)["original:mock_charlie.ork"]
    assistant = row["messages"][2]["content"]
    assert "landing_over_8ms" in row["flags"]
    assert "above the 8 m/s structural limit" in assistant
    assert "not safe as-is" in assistant


def test_hardware_only_rows_state_missing_performance_and_invent_nothing(
        tmp_path):
    _report, rows, _output = run_assemble(tmp_path)
    by_id = rows_by_catalog(rows)
    delta = by_id["original:mock_delta.ork"]
    echo = by_id["original:mock_echo.ork"]
    for row in (delta, echo):
        assistant = row["messages"][2]["content"]
        assert HARDWARE_MISSING in assistant
        assert "REFERENCE FLIGHT" not in assistant
        assert row["targets"] == {}
        assert "no_trusted_flight_data" in row["flags"]
    # the prompt is grounded in real static dimensions of this design
    prompt = delta["messages"][1]["content"]
    for fact in ("25 mm in diameter", "527 mm long", "ogive nose cone",
                 "4 fins", "parachute recovery", "C6 motor",
                 "flight performance is unavailable"):
        assert fact in prompt, fact
    # stored-but-untrusted numbers never leak into supervised text
    assert "9876.5" not in echo["messages"][1]["content"] + \
        echo["messages"][2]["content"]
    assert "REFERENCE FLIGHT" not in echo["messages"][2]["content"]


def test_unresolved_motor_is_honest_and_coverage_fallback_quotes_values(
        tmp_path):
    report, rows, _output = run_assemble(tmp_path)
    row = rows_by_catalog(rows)["original:mock_echo.ork"]
    assistant = row["messages"][2]["content"]
    assert "Unknown-F9X" in assistant
    assert "motor fit (no resolved motor data)" in assistant
    assert "thought_coverage_fallback" in row["flags"]
    assert "OTHER STORED DESIGN VALUES" in assistant
    assert report["coverage_fallback_rows"]


def test_no_hash_path_or_banned_leakage_in_any_message(tmp_path):
    from scripts.sft_compact_finalize import banned_hits
    _report, rows, _output = run_assemble(tmp_path)
    for row in rows:
        for message in row["messages"]:
            assert banned_hits(message["content"]) == []
        design = design_from_row(row)
        assert "digest" not in json.dumps(design)
        assert "/Users/" not in json.dumps(row["messages"])
        # catalog ids contain the source filename; messages never do
        assert ".ork" not in json.dumps(row["messages"])
    assert "mock_alpha.ork" not in json.dumps(
        rows_by_catalog(rows)["original:mock_alpha.ork"]["messages"])


def test_token_counts_are_real_and_oversized_rows_are_kept(tmp_path):
    report, rows, output = run_assemble(tmp_path, token_limit=50)
    assert report["rows"] == 8  # nothing dropped for size
    assert report["tokens"]["over_limit_count"] == 8
    fake = FakeTokenizer()
    for row in rows:
        expected = conversation_tokens(fake, row["messages"])
        assert row["row_tokens"] == expected
        assert "context_over_limit" in row["flags"]
    # the complete design is still fully present in every oversized row
    row = rows_by_catalog(rows)["original:mock_alpha.ork"]
    design = design_from_row(row)
    assert design["openrocket"]["children"][0]["rocket"]["children"]
    main_rows = [json.loads(line) for line in
                 (output / MAIN_FILE).read_text().splitlines() if line.strip()]
    assert len(main_rows) == 8


def test_splits_are_disjoint_family_isolated_slices_of_main(tmp_path):
    report, rows, output = run_assemble(tmp_path)
    by_id = rows_by_catalog(rows)
    # duplicate hardware and original/filled families never cross splits
    assert by_id["original:mock_alpha.ork"]["split"] == \
        by_id["motor_filled:mock_alpha_filled.ork"]["split"]
    assert by_id["original:mock_alpha.ork"]["group_id"] == \
        by_id["motor_filled:mock_alpha_filled.ork"]["group_id"]
    assert by_id["original:mock_delta.ork"]["split"] == \
        by_id["original:mock_foxtrot.ork"]["split"]
    for row in rows:
        assert row["split"] in SPLIT_FILES
        assert row["group_id"].startswith("V4-")
    slice_rows = {}
    for split, filename in SPLIT_FILES.items():
        slice_rows[split] = [json.loads(line) for line in
                             (output / filename).read_text().splitlines()
                             if line.strip()]
        for row in slice_rows[split]:
            assert row["split"] == split
    total = sum(len(v) for v in slice_rows.values())
    assert total == len(rows)
    ids = [row["id"] for rows_ in slice_rows.values() for row in rows_]
    assert len(set(ids)) == total  # disjoint
    assert {split for split in SPLIT_FILES if slice_rows[split]} == \
        set(SPLIT_FILES)  # all three slices non-empty for 8 rockets
    # slices are the very same rows, not extra examples
    for split, rows_ in slice_rows.items():
        for row in rows_:
            assert row in rows


def test_combined_corpus_use_is_documented(tmp_path):
    report, rows, output = run_assemble(tmp_path)
    joined = " ".join(report["usage"])
    assert "NOT itself a" in joined
    assert "leak" in joined
    md = (output / "SFT_V4_REPORT.md").read_text()
    assert "sft_train_v4.jsonl" in md
    assert "not rerun" in md or "recorded" in md


def test_coverage_manifest_maps_every_catalog_id(tmp_path):
    _report, rows, output = run_assemble(tmp_path)
    coverage = json.loads((output / "sft_v4_coverage.json").read_text())
    assert coverage["catalog_size"] == len(rows) == 8
    entries = coverage["entries"]
    assert len(entries) == 8
    assert [e["catalog_id"] for e in entries] == [r["catalog_id"]
                                                  for r in rows]
    by_id = rows_by_catalog(rows)
    records = {r["catalog_id"]: r for r in smoke_records()}
    for entry in entries:
        row = by_id[entry["catalog_id"]]
        assert entry["row_id"] == row["id"]
        assert entry["split"] == row["split"]
        assert entry["label_mode"] == row["label_mode"]
        assert entry["source_id"] == records[entry["catalog_id"]]["source_id"]
        assert entry["metric_provenance"] == \
            records[entry["catalog_id"]]["metric_provenance"]
        assert entry["row_tokens"] == row["row_tokens"]


def test_assets_sidecar_copied_when_present(tmp_path):
    _report, rows, output = run_assemble(tmp_path)
    assets = json.loads((output / "sft_v4_assets.json").read_text())
    assert MOCK_UNRESOLVED_DIGEST in assets["assets"]


def test_existing_v3_files_are_preserved(tmp_path):
    before = {name: (ROOT / "new_results" / name).read_bytes()
              for name in ("sft_v3.jsonl", "sft_test_v3.jsonl",
                           "sft_v3_motor_lookup.json")}
    _report, _rows, _output = run_assemble(tmp_path)
    for name, content in before.items():
        assert (ROOT / "new_results" / name).read_bytes() == content


def test_output_collisions_are_refused_without_overwrite(tmp_path):
    sources, catalog = write_source_dir(tmp_path / "sources")[:2]
    output = tmp_path / "out"
    output.mkdir()
    (output / MAIN_FILE).write_text("stale\n")
    with pytest.raises(FileExistsError, match="sft_v4.jsonl"):
        assemble(sources, output, catalog, tokenizer=FakeTokenizer())
    assemble(sources, output, catalog, tokenizer=FakeTokenizer(),
             overwrite=True)
    assert len((output / MAIN_FILE).read_text().splitlines()) == 8


# ---------------------------------------------------------------------------
# contract enforcement (blockers, never placeholders or silent skips)
# ---------------------------------------------------------------------------

def test_error_records_and_missing_designs_block_assembly(tmp_path):
    records = smoke_records()
    records[2] = {**records[2], "excluded": True, "reason": "no_trusted_result"}
    del records[2]["compact"]
    with pytest.raises(ContractError, match="exclusion/error record"):
        run_assemble(tmp_path, records=records)


@pytest.mark.parametrize("load_pass, flag", [
    (False, "static_load_check_failed"),
    (None, "static_load_check_unavailable"),
])
def test_unconfirmed_load_keeps_complete_hardware_example(tmp_path, load_pass, flag):
    records = smoke_records()
    reference = copy.deepcopy(records[1]["targets"])
    records[1]["digest_entry"] = {"c_pass": load_pass, "components": []}
    report, rows, _output = run_assemble(tmp_path, records=records)
    assert report["rows"] == len(records)
    row = rows_by_catalog(rows)[records[1]["catalog_id"]]
    assert row["label_mode"] == "hardware_only"
    assert row["source_label_mode"] == "flight_grounded"
    assert row["static_load_check"]["c_pass"] is load_pass
    assert row["reference_targets"] == reference
    assert row["targets"] == {}
    assert flag in row["flags"]
    assistant = row["messages"][2]["content"]
    assert "static load-equivalence check" in assistant
    assert "REFERENCE FLIGHT" not in assistant
    assert HARDWARE_MISSING in assistant
    assert design_from_row(row)["openrocket"]


@pytest.mark.parametrize("load_pass", [0, 1, "true"])
def test_nonboolean_load_check_status_blocks_assembly(tmp_path, load_pass):
    records = smoke_records()
    records[1]["digest_entry"] = {"c_pass": load_pass, "components": []}
    with pytest.raises(ContractError, match="c_pass must be true, false, or null"):
        run_assemble(tmp_path, records=records)


def test_record_count_and_order_are_enforced(tmp_path):
    full_catalog = [{"id": r["catalog_id"], "source_file": r["source_file"],
                     "origin": r["origin"]} for r in smoke_records()]
    records = smoke_records()[:-1]
    sources, catalog = write_source_dir(tmp_path / "sources", records=records,
                                        catalog_rows=full_catalog)
    with pytest.raises(ContractError, match="record count"):
        assemble(sources, tmp_path / "out", catalog, tokenizer=FakeTokenizer(),
                 overwrite=True)
    swapped = smoke_records()
    swapped[0], swapped[1] = swapped[1], swapped[0]
    sources, catalog = write_source_dir(tmp_path / "sources", records=swapped,
                                        catalog_rows=full_catalog)
    with pytest.raises(ContractError, match="catalog order"):
        assemble(sources, tmp_path / "out", catalog, tokenizer=FakeTokenizer(),
                 overwrite=True)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -5.0, True, "82"])
def test_nonfinite_bool_or_negative_flight_targets_block(tmp_path, bad):
    records = smoke_records()
    records[0]["targets"] = {"apogee_m": bad, "ground_hit_ms": 2.0}
    with pytest.raises(ContractError, match="apogee_m"):
        run_assemble(tmp_path, records=records)


def test_flight_row_without_required_metrics_blocks(tmp_path):
    records = smoke_records()
    records[0]["targets"] = {"apogee_m": 82.623}
    with pytest.raises(ContractError, match="apogee_m and ground_hit_ms"):
        run_assemble(tmp_path, records=records)
    records[0]["targets"] = {"apogee_m": 82.623, "ground_hit_ms": 2.0}
    records[0]["simulation_status"] = None
    with pytest.raises(ContractError, match="honest simulation status"):
        run_assemble(tmp_path, records=records)


def test_unknown_motor_digest_blocks_assembly(tmp_path):
    records = smoke_records()
    records[0]["compact"] = mock_compact(digest="f" * 32)
    with pytest.raises(ContractError, match="missing from motor_lookup"):
        run_assemble(tmp_path, records=records)


def test_model_compact_mismatch_blocks_assembly(tmp_path):
    records = smoke_records()
    good = mock_record("original:mock_alpha.ork", include_model_compact=True,
                      targets=records[0]["targets"])
    records[0] = good
    # a tampered model_compact no longer matches the verified sanitizer output
    tampered = copy.deepcopy(good["model_compact"])
    tampered["openrocket"]["children"][0]["rocket"]["children"] = \
        tampered["openrocket"]["children"][0]["rocket"]["children"][:-1]
    records[0]["model_compact"] = tampered
    with pytest.raises(ContractError, match="model_compact"):
        run_assemble(tmp_path, records=records)


def test_base64_attachments_in_compact_block_assembly(tmp_path):
    records = smoke_records()
    records[0]["compact"] = {**records[0]["compact"],
                             "attachments": {"curve": "aGk="}}
    with pytest.raises(ContractError, match="attachments"):
        run_assemble(tmp_path, records=records)


def test_invalid_label_mode_blocks_assembly(tmp_path):
    records = smoke_records()
    records[0]["label_mode"] = "guess"
    with pytest.raises(ContractError, match="label_mode"):
        run_assemble(tmp_path, records=records)


def test_validate_source_contract_reports_all_problems():
    catalog = [{"id": "original:a.ork", "source_file": "a.ork",
                "origin": "original"},
               {"id": "original:b.ork", "source_file": "b.ork",
                "origin": "original"}]
    records = [
        mock_record("original:a.ork", label_mode="flight_grounded",
                    targets={"apogee_m": float("nan"),
                             "ground_hit_ms": 2.0}),
        mock_record("original:WRONG.ork", label_mode="hardware_only"),
    ]
    with pytest.raises(ContractError) as exc:
        validate_source_contract(records, catalog, {})
    message = str(exc.value)
    assert "non-finite" in message
    assert "catalog order" in message
    assert "missing from motor_lookup" in message  # no lookup entries at all


# ---------------------------------------------------------------------------
# deterministic re-run stability
# ---------------------------------------------------------------------------

def test_assembly_is_deterministic(tmp_path):
    report_a, rows_a, out_a = run_assemble(tmp_path / "a")
    report_b, rows_b, out_b = run_assemble(tmp_path / "b")
    assert rows_a == rows_b
    assert (out_a / MAIN_FILE).read_text() == (out_b / MAIN_FILE).read_text()
    assert report_a["flags"] == report_b["flags"]
