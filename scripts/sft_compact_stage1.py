#!/usr/bin/env python3
"""Stage-1 runner for the compact SFT design repair (FLIGHT-FREE).

Subcommands
-----------
measure     Compact every candidate row (train: from the full-fidelity
            candidate JSONL; test: statically extracted from the source .ork,
            no JVM), run the static equivalence check per (file, sim) pair,
            and measure compact design sizes in characters and real
            Qwen/Qwen2.5-3B-Instruct tokens.  Writes compact/train_rows.jsonl,
            test_extract/test_static_extract.jsonl, static_check.json and
            token_stats.json under the output dir.
engineering Static-only engineering stats per pair (MassCalculator +
            BarrowmanCalculator on the SELECTED simulation's flight
            configuration, motor data from the resolved motor database
            entries).  No simulation is run; values needing a flight
            (rail-exit/min-burn stability, rail exit velocity) are not
            produced.  Writes engineering.json.
report      Compile stage1_report.json / stage1_report.md from the outputs
            above.

NO flight simulation happens anywhere in this pipeline: no simulate() call,
no re-flying.  Flight-derived numbers are taken only from the `targets`
already stored on each row.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.sft_compact_design import (  # noqa: E402
    CompactError,
    dump_compact_json,
    static_check,
    to_compact,
)
from scripts.sft_full_fidelity_support.ork_archive import (  # noqa: E402
    bundle_entries_to_json,
    partition_bundle_entries,
    read_ork_archive,
)
from scripts.sft_full_fidelity_support.xml_tree import (  # noqa: E402
    find_simulation_by_name,
    simulation_config_id,
    simulation_field,
)

CANDIDATE_REL = "sftgen/out/scratch/sft_full_fidelity_20261102/candidate/sft_v2_full_fidelity.jsonl"
TEST_INPUT_REL = "new_results/sft_test_v2.jsonl"
DEFAULT_OUTPUT_DIR = "sftgen/out/scratch/sft_compact_20261103"
TOKENIZER_MODEL = "Qwen/Qwen2.5-3B-Instruct"


def parse_candidate_design(row: dict) -> dict:
    content = row["messages"][2]["content"]
    design_text = content.split("<design>", 1)[1].rsplit("</design>", 1)[0]
    return json.loads(design_text)


def percentile(values: list[float], p: float) -> float:
    if not values:
        return float("nan")
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    idx = p / 100.0 * (len(xs) - 1)
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return xs[lo]
    return xs[lo] + (xs[hi] - xs[lo]) * (idx - lo)


def stats_block(values: list[float]) -> dict:
    return {
        "min": min(values),
        "median": percentile(values, 50),
        "p90": percentile(values, 90),
        "max": max(values),
        "over_20000": sum(1 for v in values if v > 20_000),
        "over_32768": sum(1 for v in values if v > 32_768),
    } if values else {}


def iter_jsonl(path: Path):
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


# --------------------------------------------------------------------------
# static extraction of test rows (no JVM, no flights)
# --------------------------------------------------------------------------

def extract_test_design_static(source_path: Path, sim_name: str) -> dict:
    """Full-fidelity design dict for a test row, without any flight or JVM."""
    tree, entries, container = read_ork_archive(source_path)  # strips cached flightdata
    sim_index, sim_node = find_simulation_by_name(tree, sim_name)
    fcid = simulation_config_id(sim_node)
    if not fcid:
        raise CompactError(f"simulation {sim_name!r} has no conditions>configid in {source_path}")
    engineering_bytes, _cosmetic = partition_bundle_entries(entries)
    root_attrs = tree.get("attrs") or {}
    return {
        "schema_version": "full-fidelity-1.0",
        "openrocket_version": root_attrs.get("version"),
        "ork_container": container,
        "parameter_tree": tree,
        "bundle_entries": bundle_entries_to_json(engineering_bytes),
        "selected_simulation": {
            "name": sim_name,
            "index": sim_index,
            "flight_configuration_id": fcid,
            "simulator": simulation_field(sim_node, "simulator"),
            "calculator": simulation_field(sim_node, "calculator"),
        },
    }


# --------------------------------------------------------------------------
# measure
# --------------------------------------------------------------------------

def cmd_measure(output_dir: Path, skip_tokenizer: bool) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    candidate = REPO_ROOT / CANDIDATE_REL
    test_input = REPO_ROOT / TEST_INPUT_REL

    train_rows = list(iter_jsonl(candidate))
    test_rows = list(iter_jsonl(test_input)) if test_input.is_file() else []

    # ---- train: compact per row, static check per pair ----
    train_pair_checks: dict[tuple[str, str], dict] = {}
    train_design_shas: dict[tuple[str, str], set] = {}
    train_out = []
    for row in train_rows:
        try:
            design = parse_candidate_design(row)
        except Exception as exc:
            train_out.append({"id": row.get("id"), "file": row.get("file"),
                              "sim": row.get("sim"), "error": f"design parse: {exc}"})
            continue
        key = (row["file"], row["sim"])
        sha = hashlib.sha256(dump_compact_json(to_compact(design)).encode()).hexdigest()
        train_design_shas.setdefault(key, set()).add(sha)
        if key not in train_pair_checks:
            train_pair_checks[key] = static_check(design)
        compact = to_compact(design)
        text = dump_compact_json(compact)
        train_out.append({
            "id": row["id"], "file": row["file"], "sim": row["sim"], "split": "train",
            "design_chars": len(row["messages"][2]["content"].split("<design>", 1)[1]
                                .rsplit("</design>", 1)[0]),
            "compact_chars": len(text),
            "compact": compact,
        })
    train_inconsistent = {k: sorted(v) for k, v in train_design_shas.items() if len(v) > 1}

    # ---- test: static extraction, compact, static check ----
    test_out, test_pair_checks = [], {}
    test_errors = []
    test_pairs = {}
    for row in test_rows:
        rec = {"id": row["id"], "file": row["file"], "sim": row["sim"], "split": "test",
               "targets": row.get("targets")}
        try:
            design = extract_test_design_static(REPO_ROOT / row["file"], row["sim"])
        except Exception as exc:
            rec["error"] = f"static extraction failed: {exc.__class__.__name__}: {exc}"
            test_errors.append(rec)
            test_out.append(rec)
            continue
        compact = to_compact(design)
        text = dump_compact_json(compact)
        key = (row["file"], row["sim"])
        if key not in test_pairs:
            test_pairs[key] = static_check(design)
        rec.update({
            "design_chars": len(json.dumps(design, separators=(",", ":"), allow_nan=False)),
            "design": design,  # full static extraction; kept in test_static_extract.jsonl
            "compact_chars": len(text),
            "compact": compact,
            "static_check": test_pairs[key],
        })
        test_out.append(rec)
    test_pair_checks = test_pairs

    # ---- write artifacts ----
    compact_dir = output_dir / "compact"
    compact_dir.mkdir(parents=True, exist_ok=True)
    with (compact_dir / "train_rows.jsonl").open("w") as fh:
        for rec in train_out:
            fh.write(json.dumps(rec, ensure_ascii=False, allow_nan=False) + "\n")
    with (compact_dir / "test_rows.jsonl").open("w") as fh:
        for rec in test_out:
            lean = {k: v for k, v in rec.items() if k != "design"}
            fh.write(json.dumps(lean, ensure_ascii=False, allow_nan=False) + "\n")

    test_extract_dir = output_dir / "test_extract"
    test_extract_dir.mkdir(parents=True, exist_ok=True)
    with (test_extract_dir / "test_static_extract.jsonl").open("w") as fh:
        for rec in test_out:
            fh.write(json.dumps(rec, ensure_ascii=False, allow_nan=False) + "\n")

    static_check_report = {
        "method": ("static, flight-free: from_compact(to_compact(design)) must reproduce "
                   "the parameter_tree of the selected configuration exactly after the "
                   "documented removals/placeholdering (normalize_tree); kept thrustcurve "
                   "attachments must round trip byte-identically. NO flight simulation ran."),
        "train_pairs": {f"{f}|{s}": v for (f, s), v in train_pair_checks.items()},
        "test_pairs": {f"{f}|{s}": v for (f, s), v in test_pair_checks.items()},
        "train_rows_with_inconsistent_compact_for_same_pair": {
            f"{f}|{s}": shas for (f, s), shas in train_inconsistent.items()},
    }
    (output_dir / "static_check.json").write_text(
        json.dumps(static_check_report, ensure_ascii=False, indent=1) + "\n")

    # ---- tokens ----
    token_stats: dict[str, Any] = {"tokenizer": TOKENIZER_MODEL, "note": "real Qwen tokenizer, add_special_tokens=False"}
    if not skip_tokenizer:
        try:
            from transformers import AutoTokenizer
            tok = AutoTokenizer.from_pretrained(TOKENIZER_MODEL)
        except Exception as exc:
            token_stats["error"] = f"tokenizer unavailable: {exc.__class__.__name__}: {exc}"
        else:
            def n_tokens(text: str) -> int:
                return len(tok(text, add_special_tokens=False)["input_ids"])

            for split, records in (("train", train_out), ("test", test_out)):
                done, rows = [], []
                for rec in records:
                    if "compact" not in rec:
                        continue
                    text = dump_compact_json(rec["compact"])
                    t = n_tokens(text)
                    rec["compact_tokens"] = t
                    rows.append({"id": rec["id"], "file": rec["file"], "sim": rec["sim"],
                                 "tokens": t, "chars": rec.get("compact_chars")})
                    done.append(t)
                token_stats[split] = {
                    "rows": len(done),
                    **stats_block(done),
                    "largest_rows": sorted(rows, key=lambda r: -r["tokens"])[:10],
                }
            # unique designs (dedupe rows sharing a (file, sim) pair)
            for split, records, seen in (("train_unique_pairs", train_out, set()),
                                         ("test_unique_pairs", test_out, set())):
                vals = []
                for rec in records:
                    if "compact" not in rec:
                        continue
                    key = (rec["file"], rec["sim"])
                    if key in seen:
                        continue
                    seen.add(key)
                    vals.append(n_tokens(dump_compact_json(rec["compact"])))
                token_stats[split] = {"pairs": len(vals), **stats_block(vals)} if vals else {}

            # rewrite row artifacts including token counts
            with (compact_dir / "train_rows.jsonl").open("w") as fh:
                for rec in train_out:
                    fh.write(json.dumps(rec, ensure_ascii=False, allow_nan=False) + "\n")
            with (compact_dir / "test_rows.jsonl").open("w") as fh:
                for rec in test_out:
                    lean = {k: v for k, v in rec.items() if k != "design"}
                    fh.write(json.dumps(lean, ensure_ascii=False, allow_nan=False) + "\n")
            with (test_extract_dir / "test_static_extract.jsonl").open("w") as fh:
                for rec in test_out:
                    fh.write(json.dumps(rec, ensure_ascii=False, allow_nan=False) + "\n")

    (output_dir / "token_stats.json").write_text(json.dumps(token_stats, indent=1) + "\n")

    # ---- console summary ----
    train_pass = sum(1 for v in train_pair_checks.values() if v["pass"])
    test_pass = sum(1 for v in test_pair_checks.values() if v["pass"])
    print(f"train: {len(train_out)} rows, {len(train_pair_checks)} pairs, "
          f"static-check pass {train_pass}/{len(train_pair_checks)}")
    print(f"test:  {len(test_out)} rows ({len(test_errors)} extraction errors), "
          f"{len(test_pair_checks)} pairs, static-check pass {test_pass}/{len(test_pair_checks)}")
    for split in ("train", "test"):
        if split in token_stats and "rows" in token_stats[split]:
            s = token_stats[split]
            print(f"tokens {split}: min={s['min']} median={s['median']} p90={s['p90']} "
                  f"max={s['max']} over20000={s['over_20000']} over32768={s['over_32768']}")
            print(f"tokens {split} largest: " + json.dumps(s["largest_rows"][:3]))
    if "error" in token_stats:
        print("TOKENIZER ERROR:", token_stats["error"])
    return 0


def cmd_report(output_dir: Path) -> int:
    from scripts.sft_compact_stage1_engineering import REPO_ROOT as _root  # noqa: F401

    static_report = json.loads((output_dir / "static_check.json").read_text())
    loader_report = json.loads((output_dir / "loader_check.json").read_text())
    engineering = json.loads((output_dir / "engineering.json").read_text())
    token_stats = json.loads((output_dir / "token_stats.json").read_text())

    # leakage: source files / pairs shared between the train candidate and the test rows
    train_rows = list(iter_jsonl(REPO_ROOT / CANDIDATE_REL))
    test_rows = list(iter_jsonl(REPO_ROOT / TEST_INPUT_REL))
    train_files = {r["file"] for r in train_rows}
    test_files = {r["file"] for r in test_rows}
    train_pairs_set = {(r["file"], r["sim"]) for r in train_rows}
    test_pairs_set = {(r["file"], r["sim"]) for r in test_rows}

    def pair_failures(pairs: dict) -> dict:
        return {k: v["differences"][:5] for k, v in pairs.items() if not v["pass"]}

    train_pair_fail = pair_failures(static_report["train_pairs"])
    test_pair_fail = pair_failures(static_report["test_pairs"])
    loader_fail = {
        k: (v.get("error") or v["loader_check"]["differences"][:5])
        for k, v in loader_report["pairs"].items()
        if v.get("error") or not v["loader_check"]["pass"]}

    # rows whose pair dropped cosmetic bundle attachments
    dropped_by_pair = {k: v.get("dropped_attachments") or []
                       for k, v in {**static_report["train_pairs"],
                                    **static_report["test_pairs"]}.items()}
    rows_dropping_attachments = {}
    for split in ("train", "test"):
        for rec in iter_jsonl(output_dir / "compact" / f"{split}_rows.jsonl"):
            dropped = dropped_by_pair.get(f'{rec["file"]}|{rec["sim"]}')
            if dropped:
                rows_dropping_attachments.setdefault(rec["id"], dropped)

    engineering_coverage = {
        "pairs": len(engineering),
        "with_static_margin": sum(1 for v in engineering.values()
                                  if v.get("static_margin_cal") is not None),
        "null_fields_with_reason": {
            k: v.get("errors") for k, v in engineering.items() if v.get("errors")},
    }

    def summarize(split_key: str) -> dict:
        s = token_stats.get(split_key) or {}
        return {k: s.get(k) for k in ("rows", "pairs", "min", "median", "p90", "max",
                                      "over_20000", "over_32768")} if s else None

    report = {
        "generated_for": "Stage 1 of 2, dataset repair (compact design JSON)",
        "scope_changes_applied": [
            "NO flight simulation ran anywhere in this stage: no simulate() call, no re-flying.",
            "The flight round-trip gate was replaced by a static equivalence check per pair.",
            "manifest.py was NOT edited (Task 3 cancelled); the short text will not use that manifest.",
            "Rail-exit/min-burn stability and rail-exit velocity were NOT computed (need flights).",
            "Test rows were extracted statically (no JVM flights); their existing targets are kept.",
        ],
        "static_equivalence_check": {
            "method": static_report["method"],
            "train_pairs": len(static_report["train_pairs"]),
            "train_pass": len(static_report["train_pairs"]) - len(train_pair_fail),
            "test_pairs": len(static_report["test_pairs"]),
            "test_pass": len(static_report["test_pairs"]) - len(test_pair_fail),
            "train_failures": train_pair_fail,
            "test_failures": test_pair_fail,
        },
        "loader_snapshot_check": {
            "method": loader_report["method"],
            "pairs": len(loader_report["pairs"]),
            "pass": len(loader_report["pairs"]) - len(loader_fail),
            "failures": loader_fail,
        },
        "engineering": engineering_coverage,
        "test_rows": {
            "rows": len(test_rows),
            "extraction_errors": [r for r in
                                  (iter_jsonl(output_dir / "test_extract" / "test_static_extract.jsonl"))
                                  if "error" in r],
        },
        "leakage": {
            "shared_source_files": sorted(train_files & test_files),
            "shared_file_sim_pairs": [f"{f}|{s}" for f, s in sorted(train_pairs_set & test_pairs_set)],
        },
        "rows_dropping_cosmetic_attachments": rows_dropping_attachments,
        "token_stats": {
            "tokenizer": token_stats.get("tokenizer"),
            "error": token_stats.get("error"),
            "train_rows": summarize("train"),
            "test_rows": summarize("test"),
            "train_unique_pairs": summarize("train_unique_pairs"),
            "test_unique_pairs": summarize("test_unique_pairs"),
            "largest_train_rows": (token_stats.get("train") or {}).get("largest_rows"),
            "largest_test_rows": (token_stats.get("test") or {}).get("largest_rows"),
        },
        "files_written": [
            "compact/train_rows.jsonl", "compact/test_rows.jsonl",
            "test_extract/test_static_extract.jsonl",
            "static_check.json", "loader_check.json", "engineering.json",
            "token_stats.json", "stage1_report.json", "stage1_report.md",
        ],
    }
    (output_dir / "stage1_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1, allow_nan=False) + "\n")

    ts_train = token_stats.get("train") or {}
    ts_test = token_stats.get("test") or {}

    def fmt_row(s):
        if not s:
            return "unavailable"
        return (f"min {s['min']:,} / median {round(s['median']):,} / "
                f"p90 {round(s['p90']):,} / max {s['max']:,}")

    md = []
    md.append("# Stage 1 report — compact design JSON (flight-free)\n")
    md.append("## Compact design token sizes (real Qwen/Qwen2.5-3B-Instruct tokenizer)\n")
    md.append("| rows | min | median | p90 | max | >20,000 tok | >32,768 tok |")
    md.append("|---|---|---|---|---|---|---|")
    if ts_train:
        md.append(f"| train ({ts_train['rows']}) | {ts_train['min']:,} | "
                  f"{round(ts_train['median']):,} | {round(ts_train['p90']):,} | {ts_train['max']:,} | "
                  f"{ts_train['over_20000']} | {ts_train['over_32768']} |")
    if ts_test:
        md.append(f"| test ({ts_test['rows']}) | {ts_test['min']:,} | "
                  f"{round(ts_test['median']):,} | {round(ts_test['p90']):,} | {ts_test['max']:,} | "
                  f"{ts_test['over_20000']} | {ts_test['over_32768']} |")
    md.append("")
    md.append(f"Train: {fmt_row(ts_train)}  |  Test: {fmt_row(ts_test)}")
    md.append("(Original candidate rows: median ~213,000 tokens; the compact design is what the "
              "model must emit in Stage 2; the <thought> rewrite is Stage 2's job.)\n")
    if ts_train.get("largest_rows"):
        md.append("### 10 largest train rows (compact tokens)\n")
        md.append("| id | tokens | chars | file | sim |")
        md.append("|---|---|---|---|---|")
        for r in ts_train["largest_rows"]:
            md.append(f"| {r['id']} | {r['tokens']:,} | {r['chars']:,} | {r['file']} | {r['sim']} |")
        md.append("")
    if ts_test.get("largest_rows"):
        md.append("### 10 largest test rows (compact tokens)\n")
        md.append("| id | tokens | chars | file | sim |")
        md.append("|---|---|---|---|---|")
        for r in ts_test["largest_rows"]:
            md.append(f"| {r['id']} | {r['tokens']:,} | {r['chars']:,} | {r['file']} | {r['sim']} |")
        md.append("")
    md.append("## Scope changes applied (per user amendment)\n")
    for line in report["scope_changes_applied"]:
        md.append(f"* {line}")
    md.append("")
    md.append("## Static equivalence check (replaces the flight round-trip gate; NO flight ran)\n")
    md.append(report["static_equivalence_check"]["method"])
    sc = report["static_equivalence_check"]
    md.append(f"\n* train pairs: **{sc['train_pass']}/{sc['train_pairs']} pass**")
    md.append(f"* test pairs: **{sc['test_pass']}/{sc['test_pairs']} pass**")
    if sc["train_failures"] or sc["test_failures"]:
        md.append("\n### Failures with causes\n")
        for k, v in {**sc["train_failures"], **sc["test_failures"]}.items():
            md.append(f"* {k}: {v}")
    md.append("")
    md.append("## Loader-snapshot static check (original vs compact-rebuilt .ork, loaded; no simulation)\n")
    ls = report["loader_snapshot_check"]
    md.append(f"\n**{ls['pass']}/{ls['pairs']} pairs pass.** " + loader_report["method"])
    if ls["failures"]:
        md.append("\n### Failures\n")
        for k, v in ls["failures"].items():
            md.append(f"* {k}: {v}")
    md.append("")
    md.append("## engineering.json (static: MassCalculator + BarrowmanCalculator at Mach 0.3 / AOA 0 on the selected sim's config; motor data from resolved motor instances)\n")
    ec = report["engineering"]
    md.append(f"\n* pairs: {ec['pairs']}; static margin computed for {ec['with_static_margin']}")
    md.append("* NOT computed (need flights): rail-exit stability, min-burn stability, rail-exit velocity.")
    if ec["null_fields_with_reason"]:
        md.append(f"* null-with-reason fields: {json.dumps(ec['null_fields_with_reason'])[:1000]}")
    md.append("")
    md.append("## Test rows (38) — static extraction, no flights\n")
    md.append(f"\n* extraction errors: {len(report['test_rows']['extraction_errors'])}")
    for r in report["test_rows"]["extraction_errors"]:
        md.append(f"  * {r['id']} {r['file']}|{r['sim']}: {r['error']}")
    md.append("* existing `targets` on each test row are kept untouched; rows were not moved.")
    md.append("")
    md.append("## Leakage (source .ork files in both train and test)\n")
    md.append(f"\n* shared files: {report['leakage']['shared_source_files'] or 'none'}")
    md.append(f"* shared (file, sim) pairs: {report['leakage']['shared_file_sim_pairs'] or 'none'}")
    md.append("")
    md.append("## Rows whose pair dropped cosmetic bundle attachments (textures/previews; no physics)\n")
    if rows_dropping_attachments:
        for rid, dropped in rows_dropping_attachments.items():
            md.append(f"* {rid}: {dropped}")
    else:
        md.append("none")
    md.append("")
    md.append("## Files written\n")
    for f in report["files_written"]:
        md.append(f"* {output_dir / f}")
    md.append("")
    (output_dir / "stage1_report.md").write_text("\n".join(md) + "\n")
    print(f"report written: {output_dir / 'stage1_report.md'}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("measure")
    m.add_argument("--skip-tokenizer", action="store_true")
    sub.add_parser("engineering")
    sub.add_parser("report")
    args = ap.parse_args(argv)
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = REPO_ROOT / output_dir
    if args.cmd == "measure":
        return cmd_measure(output_dir, skip_tokenizer=args.skip_tokenizer)
    if args.cmd == "engineering":
        from scripts.sft_compact_stage1_engineering import cmd_engineering  # type: ignore
        return cmd_engineering(output_dir)
    if args.cmd == "report":
        return cmd_report(output_dir)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
