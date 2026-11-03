#!/usr/bin/env python3
"""Stage-2 finalize: build the final SFT rows (NO flights).

Reads the Stage-1 compact rows, the source prompt files, engineering.json and
the headless digest check, renders each row's assistant message
(<thought> + <design>), computes honest flags, and writes ONLY under
``final/``:

    final/train.jsonl       main training rows
    final/test.jsonl        main test rows (prompts untouched)
    final/excluded.jsonl    rows moved out (base64 attachments, required
                            digests) with their data kept
    final/oversized.jsonl   complete rows over the 32,768-token limit
    final/summary.json      machine-readable numbers for the report
    final/sample_median.txt the median-length train row, printed out

Flight numbers come ONLY from each row's stored ``targets``; static numbers
come from engineering.json and the headless load dump.  No simulate() call
exists in this pipeline.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.sft_compact_design import dump_compact_json  # noqa: E402
from scripts.sft_compact_motor_ids import apply_stage2_and_fix  # noqa: E402
from scripts.sft_compact_reasoning import (  # noqa: E402
    coverage_gaps,
    child,
    find_rocket,
    render_thought,
    stage_wrappers,
    value_of,
    walk_components,
)

STAGE_DIR = REPO_ROOT / "sftgen" / "out" / "scratch" / "sft_compact_20261103"
CANDIDATE_REL = REPO_ROOT / "sftgen/out/scratch/sft_full_fidelity_20261102/candidate/sft_v2_full_fidelity.jsonl"
TEST_INPUT_REL = REPO_ROOT / "new_results" / "sft_test_v2.jsonl"
TOKENIZER_MODEL = "Qwen/Qwen2.5-3B-Instruct"
ROW_TOKEN_LIMIT = 32_768

# assistant-text linter (mirrored independently in scripts/sft_compact_validate.py)
BANNED_RES = [
    ("word verified", re.compile(r"verified", re.IGNORECASE)),
    ("sha256", re.compile(r"sha256", re.IGNORECASE)),
    ("hex digest", re.compile(r"\b[0-9a-f]{32,}\b", re.IGNORECASE)),
    ("uuid", re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
                        r"[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE)),
    (".ork", re.compile(r"\.ork\b", re.IGNORECASE)),
    ("seed", re.compile(r"seed", re.IGNORECASE)),
    ("getter name", re.compile(r"get[A-Z]")),
    ("audit", re.compile(r"audit", re.IGNORECASE)),
    ("reverse-simulation", re.compile(r"reverse-simulation", re.IGNORECASE)),
    ("provenance", re.compile(r"provenance", re.IGNORECASE)),
    ("base64", re.compile(r"base64", re.IGNORECASE)),
]

PROMPT_MOTOR_RE = re.compile(
    r"on an? ((?:[1-9]/2 )?[A-O]\d{1,4}(?:-\d{1,2})?(?:[A-Z])?)\b", re.IGNORECASE)


def iter_jsonl(path: Path):
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def percentile(values: list[float], p: float) -> float:
    if not values:
        return float("nan")
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    idx = p / 100.0 * (len(xs) - 1)
    lo, hi = int(idx // 1), int(idx // 1) + 1
    if lo == hi:
        return xs[lo]
    return xs[lo] + (xs[hi] - xs[lo]) * (idx - lo)


def stats_block(values: list[float]) -> dict:
    if not values:
        return {}
    return {
        "min": min(values),
        "median": percentile(values, 50),
        "p90": percentile(values, 90),
        "max": max(values),
    }


def banned_hits(text: str) -> list[str]:
    return [name for name, rx in BANNED_RES if rx.search(text)]


def compute_flags(targets: dict, eng: dict, motor_diffs: list[dict],
                  fit_failures: list[str], ttw_certain: bool) -> list:
    flags: list = []
    gh = targets.get("ground_hit_ms")
    if gh is not None and gh > 8.0:
        flags.append("landing_over_8ms")
    sm = eng.get("static_margin_cal")
    if sm is not None:
        if sm < 0:
            flags.append("stability_under_1cal")
            flags.append("stability_negative")
        elif sm < 1:
            flags.append("stability_under_1cal")
    if fit_failures:
        flags.append({"flag": "fit_issue", "details": fit_failures})
    for md in motor_diffs:
        flags.append({"flag": "motor_name_differs", **md})
    if not ttw_certain:
        flags.append("ttw_undetermined")
    return flags


def _leaves(design: dict):
    """(ctx, tag, value, attrs) for every leaf of the compact design."""
    def visit(node, ctx):
        if not isinstance(node, dict):
            return
        kids = node.get("children")
        if not isinstance(kids, list):
            return
        for wrapper in kids:
            if not (isinstance(wrapper, dict) and len(wrapper) == 1):
                continue
            (tag, payload), = wrapper.items()
            if not isinstance(payload, dict):
                continue
            for ak, av in (payload.get("attrs") or {}).items():
                yield ctx, f"{tag}@{ak}", av, None
            if "value" in payload:
                yield ctx, tag, payload.get("value"), payload.get("attrs")
            yield from visit(payload, tag)

    for wrapper in (design.get("openrocket") or {}).get("children") or []:
        if isinstance(wrapper, dict) and "rocket" in wrapper:
            yield from visit(wrapper["rocket"], "rocket")


def fp_noise_stats(designs: list[dict], n_tokens) -> dict:
    """Count float leaves with long repr tails and the hypothetical token
    cost of that noise (measurement only; values are never changed)."""
    noise = 0
    actual_chars = 0
    hypothetical_chars = 0
    actual_tokens = 0
    hypothetical_tokens = 0
    for design in designs:
        for _ctx, _tag, value, _attrs in _leaves(design):
            if isinstance(value, float) and not isinstance(value, bool):
                r = repr(value)
                tail = r.split(".")[-1].split("e")[0] if "." in r else ""
                if len(tail) > 10:
                    noise += 1
                    actual_chars += len(r)
                    hypothetical_chars += len(f"{value:.6f}")
                    actual_tokens += n_tokens(r)
                    hypothetical_tokens += n_tokens(f"{value:.6f}")
    return {
        "float_leaves_with_repr_over_10_decimals": noise,
        "noise_tokens_actual": actual_tokens,
        "noise_tokens_if_6_decimals": hypothetical_tokens,
        "note": ("hypothetical only: writing those values with 6 decimals would "
                 "change them, so the dataset keeps the exact values"),
    }


def build_row(stage_row: dict, src_row: dict, eng: dict,
              digest_entry: dict, id_by_digest: dict) -> dict:
    """Render one row (or an exclusion record)."""
    compact = stage_row["compact"]
    targets = src_row["targets"]
    prompt_text = src_row["prompt_text"]

    if compact.get("attachments"):
        return {
            "excluded": True,
            "reason": "base64_thrust_curve_attachments",
            "detail": ("the design JSON would need base64 thrust-curve "
                       "attachments, which a model cannot generate"),
        }
    if not digest_entry.get("c_pass"):
        return {
            "excluded": True,
            "reason": "load_check_failed",
            "detail": ("the final design state (motor ids, no preset blocks, "
                       "no cosmetic leaves) restored to digests through "
                       "motor_lookup.json does not load identically to the "
                       "as-is design; the row stays out of the main files"),
        }

    # final model-visible design: motor digests replaced by readable motor
    # ids, preset blocks / cosmetic leaves / simulation name removed, and
    # preset-supplied parachute overrides written out explicitly; the values
    # for the fix come from the loaded state the check verified (for a
    # c-passing pair identical to the as-is load).
    design, preset_fixes = apply_stage2_and_fix(
        compact, id_by_digest, digest_entry.get("components") or [])
    fit_dump = digest_entry.get("components") or []
    rendered = render_thought(design, eng, targets, prompt_text, fit_dump)

    # true digest comparison, computed from the RAW compact (digests are
    # removed from the rendered design, so the renderer cannot compare them)
    rocket_raw = find_rocket(compact)
    raw_digests = []
    for _tag, st in stage_wrappers(rocket_raw):
        for _tag2, payload, _depth in walk_components(st):
            mount = child(payload, "motormount")
            if mount is None:
                continue
            motor = child(mount, "motor")
            if motor is not None:
                dg = child(motor, "digest")
                raw_digests.append(value_of(dg) if dg is not None else None)
    resolved_digests = [(m.get("motor") or {}).get("digest")
                        for m in (eng.get("motors") or [])
                        if isinstance(m, dict) and m.get("motor")]
    for i, md in enumerate(rendered["motor_diffs"]):
        raw_dg = raw_digests[i] if i < len(raw_digests) else None
        res_dg = resolved_digests[i] if i < len(resolved_digests) else None
        md["digest_differs"] = (None if raw_dg is None or res_dg is None
                                else str(raw_dg) != str(res_dg))

    flags = compute_flags(targets, eng, rendered["motor_diffs"],
                          rendered["fit_failures"], rendered["ttw_certain"])

    design_json = dump_compact_json(design)
    assistant = (f"<thought>\n{rendered['thought']}\n</thought>\n"
                 f"<design>\n{design_json}\n</design>")

    row = {
        "id": stage_row["id"],
        "file": stage_row["file"],
        "sim": stage_row["sim"],
        "split": stage_row["split"],
        "prompt_text": prompt_text,
        "messages": [
            src_row["messages"][0],
            src_row["messages"][1],
            {"role": "assistant", "content": assistant},
        ],
        "targets": targets,
        "flags": flags,
        "source_prompt": src_row.get("source_prompt"),
        "ir_chars": src_row.get("ir_chars"),
        "design_chars": stage_row.get("design_chars"),
        "compact_chars": stage_row.get("compact_chars"),
        "compact_tokens": stage_row.get("compact_tokens"),
    }
    return {
        "excluded": False,
        "row": row,
        "thought": rendered["thought"],
        "design_json": design_json,
        "design": design,
        "preset_fixes": preset_fixes,
        "not_computed": rendered["not_computed"],
        "coverage_gaps": coverage_gaps(rendered["thought"], design),
        "banned": banned_hits(assistant),
    }


def _count_tag(node: Any, tag: str) -> int:
    n = 0
    kids = node.get("children") if isinstance(node, dict) else None
    if isinstance(kids, list):
        for wrapper in kids:
            if isinstance(wrapper, dict) and len(wrapper) == 1:
                (t, payload), = wrapper.items()
                if t == tag:
                    n += 1
                n += _count_tag(payload, tag)
    return n


def _count_attr(node: Any, tag: str, attr: str) -> int:
    n = 0
    kids = node.get("children") if isinstance(node, dict) else None
    if isinstance(kids, list):
        for wrapper in kids:
            if isinstance(wrapper, dict) and len(wrapper) == 1:
                (t, payload), = wrapper.items()
                if t == tag and attr in (payload.get("attrs") or {}):
                    n += 1
                n += _count_attr(payload, tag, attr)
    return n


def _write_jsonl(path: Path, rows: list[dict], append: bool = False) -> None:
    mode = "a" if append else "w"
    with path.open(mode) as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(STAGE_DIR / "final"))
    parser.add_argument("--no-tokenizer", action="store_true")
    args = parser.parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for stale in ("train.jsonl", "test.jsonl", "excluded.jsonl",
                  "oversized.jsonl", "sample_median.txt", "summary.json"):
        (out_dir / stale).unlink(missing_ok=True)

    eng = json.loads((STAGE_DIR / "engineering.json").read_text())
    digest_check = json.loads((STAGE_DIR / "digest_check.json").read_text())
    digest_pairs = digest_check["pairs"]
    lookup = json.loads(
        (STAGE_DIR / "final" / "motor_lookup.json").read_text())
    id_by_digest = {v["digest"]: k for k, v in lookup.items()}
    assert len(id_by_digest) == len(lookup) == len(
        {v["digest"] for v in lookup.values()}), "motor lookup not one-to-one"

    if args.no_tokenizer:
        def n_tokens(_text: str) -> int:
            return 0
        token_note = "tokenizer disabled (counts are 0)"
    else:
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(TOKENIZER_MODEL, local_files_only=True)

        def n_tokens(text: str) -> int:
            return len(tok(text, add_special_tokens=False)["input_ids"])

        token_note = f"real {TOKENIZER_MODEL} tokenizer, add_special_tokens=False"

    src_by_id: dict[str, dict] = {}
    for row in iter_jsonl(CANDIDATE_REL):
        src_by_id[row["id"]] = {
            "messages": row["messages"],
            "targets": row["targets"],
            "prompt_text": row["prompt_text"],
            "source_prompt": row.get("source_prompt"),
            "ir_chars": row.get("ir_chars"),
        }
    for row in iter_jsonl(TEST_INPUT_REL):
        src_by_id[row["id"]] = {
            "messages": row["messages"],
            "targets": row["targets"],
            "prompt_text": row["prompt_text"],
            "source_prompt": row.get("source_prompt"),
            "ir_chars": row.get("ir_chars"),
        }

    removal_counts: Counter = Counter()
    preset_fix_ids: list[str] = []
    summary: dict[str, Any] = {
        "tokenizer": token_note,
        "motor_lookup": {
            "path": "final/motor_lookup.json",
            "size": len(lookup),
            "in_dataset_ids": sum(1 for v in lookup.values() if v["in_dataset"]),
            "ids_with_version_suffix": sum(
                1 for k, v in lookup.items()
                if "-v" in k and k.rsplit("-v", 1)[-1].isdigit()),
        },
        "splits": {},
        "excluded": [],
        "oversized_ids": [],
        "flag_counts": Counter(),
        "coverage_failures": [],
        "banned_failures": [],
        "fit_not_computed_total": 0,
        "rows_with_fit_not_computed": 0,
        "motor_name_differs_ids": [],
        "ttw_undetermined_ids": [],
        "test_motor_conflicts": [],
        "row_tokens_by_id": {},
    }
    all_designs: list[dict] = []
    train_sample: dict | None = None

    for split, n_expected in (("train", 163), ("test", 38)):
        stage_rows = list(iter_jsonl(STAGE_DIR / "compact" / f"{split}_rows.jsonl"))
        assert len(stage_rows) == n_expected, f"{split}: {len(stage_rows)} rows"
        main_rows: list[dict] = []
        excluded_rows: list[dict] = []
        oversized_rows: list[dict] = []
        tokens_for_sample: list[tuple[int, dict]] = []
        stats = {"thought_chars": [], "thought_tokens": [], "design_tokens": [],
                 "row_tokens": []}

        for stage_row in stage_rows:
            key = f"{stage_row['file']}|{stage_row['sim']}"
            digest_entry = digest_pairs.get(key) or {}
            compact = stage_row["compact"]
            removal_counts[f"motor_digest_elements_replaced_{split}"] += _count_tag(compact.get("openrocket"), "digest")
            removal_counts[f"preset_digest_attrs_removed_{split}"] += _count_attr(compact.get("openrocket"), "preset", "digest")
            removal_counts[f"preset_blocks_removed_{split}"] += _count_tag(compact.get("openrocket"), "preset")
            removal_counts[f"cosmetic_leaves_removed_{split}"] += (
                _count_tag(compact.get("openrocket"), "color")
                + _count_tag(compact.get("openrocket"), "linestyle")
                + _count_tag(compact.get("openrocket"), "designtype"))
            removal_counts[f"simulation_name_elements_removed_{split}"] += _count_tag(compact.get("openrocket"), "name")

            built = build_row(stage_row, src_by_id[stage_row["id"]],
                              eng[key], digest_entry, id_by_digest)
            removal_counts[f"motor_id_elements_written_{split}"] += (
                _count_tag(built["design"].get("openrocket"), "motor_id")
                if not built.get("excluded") else 0)

            if built.get("excluded"):
                excluded_rows.append({
                    "id": stage_row["id"],
                    "file": stage_row["file"],
                    "sim": stage_row["sim"],
                    "split": split,
                    "prompt_text": src_by_id[stage_row["id"]]["prompt_text"],
                    "targets": src_by_id[stage_row["id"]]["targets"],
                    "excluded_reason": built["reason"],
                    "detail": built["detail"],
                    "compact": compact,
                })
                summary["excluded"].append({"id": stage_row["id"], "split": split,
                                            "reason": built["reason"]})
                continue

            row = built["row"]
            if built["preset_fixes"]:
                preset_fix_ids.append(row["id"])
            if built["coverage_gaps"]:
                summary["coverage_failures"].append(
                    {"id": row["id"], "gaps": built["coverage_gaps"][:10]})
            if built["banned"]:
                summary["banned_failures"].append(
                    {"id": row["id"], "banned": built["banned"]})
            if built["not_computed"]:
                summary["fit_not_computed_total"] += len(built["not_computed"])
                summary["rows_with_fit_not_computed"] += 1
            summary["flag_counts"] += Counter(
                f if isinstance(f, str) else f["flag"] for f in row["flags"])
            for f in row["flags"]:
                if isinstance(f, dict) and f["flag"] == "motor_name_differs":
                    summary["motor_name_differs_ids"].append(row["id"])
                if isinstance(f, str) and f == "ttw_undetermined":
                    summary["ttw_undetermined_ids"].append(row["id"])

            row_tokens = sum(n_tokens(m["content"]) for m in row["messages"])
            summary["row_tokens_by_id"][row["id"]] = row_tokens
            stats["thought_chars"].append(len(built["thought"]))
            stats["thought_tokens"].append(n_tokens(built["thought"]))
            stats["design_tokens"].append(n_tokens(built["design_json"]))
            stats["row_tokens"].append(row_tokens)
            all_designs.append(built["design"])
            tokens_for_sample.append((row_tokens, row))

            # test rows: prompt motor vs design motor conflict (reported, never fixed)
            if split == "test":
                asked = [m.upper().replace(" ", "") for m in
                         PROMPT_MOTOR_RE.findall(row["prompt_text"])]
                design_desigs = [str(v).upper() for _c, _t, v, _a in _leaves(built["design"])
                                 if _t == "designation" and v is not None]
                for tok_ in asked:
                    if not any(tok_ in d or d in tok_ for d in design_desigs):
                        summary["test_motor_conflicts"].append(
                            {"id": row["id"], "prompt_motor": tok_,
                             "design_motors": sorted(set(design_desigs))})

            if row_tokens > ROW_TOKEN_LIMIT:
                oversized_rows.append(row)
                summary["oversized_ids"].append(row["id"])
            else:
                main_rows.append(row)

        _write_jsonl(out_dir / f"{split}.jsonl", main_rows)
        _write_jsonl(out_dir / "excluded.jsonl", excluded_rows,
                     append=split == "test")
        _write_jsonl(out_dir / "oversized.jsonl", oversized_rows,
                     append=split == "test")

        summary["splits"][split] = {
            "expected": n_expected,
            "main": len(main_rows),
            "excluded": len(excluded_rows),
            "oversized": len(oversized_rows),
            "thought_chars": stats_block(stats["thought_chars"]),
            "thought_tokens": stats_block(stats["thought_tokens"]),
            "design_tokens": stats_block(stats["design_tokens"]),
            "row_tokens": stats_block(stats["row_tokens"]),
            "rows_over_20000": sum(1 for v in stats["row_tokens"] if v > 20_000),
            "rows_over_32768": sum(1 for v in stats["row_tokens"] if v > 32_768),
        }

        if split == "train" and tokens_for_sample:
            tokens = [t for t, _ in tokens_for_sample]
            med = statistics.median(tokens)
            _idx = min(range(len(rows := [r for _, r in tokens_for_sample])),
                       key=lambda i: abs(tokens[i] - med))
            train_sample = rows[_idx]

    if train_sample is not None:
        with (out_dir / "sample_median.txt").open("w") as fh:
            fh.write(json.dumps(train_sample, indent=1, ensure_ascii=False) + "\n")

    summary["fp_noise"] = fp_noise_stats(all_designs, n_tokens)
    summary["preset_override_fix_ids"] = preset_fix_ids
    summary["flag_counts"] = dict(summary["flag_counts"])
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=1, ensure_ascii=False) + "\n")

    print(json.dumps({
        "splits": summary["splits"],
        "removal_counts": dict(removal_counts),
        "excluded": summary["excluded"],
        "oversized_ids": summary["oversized_ids"],
        "flag_counts": summary["flag_counts"],
        "coverage_failures": len(summary["coverage_failures"]),
        "banned_failures": len(summary["banned_failures"]),
        "test_motor_conflicts": summary["test_motor_conflicts"],
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
