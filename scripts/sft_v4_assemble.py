#!/usr/bin/env python3
"""Assemble the complete v4 SFT corpus: exactly one complete conversation per
catalog rocket.

Input contract (owned by the source agent):
``sftgen/out/scratch/sft_v4_complete/sources.jsonl`` holds EXACTLY one record
per catalog id of the outer ``data/rockets_full.jsonl`` (330 rockets), in
catalog order.  Each record carries the raw ``compact`` design, an optional
sanitized ``model_compact``, static ``engineering`` values, an honest
``digest_entry`` (c_pass from a real load compare, or unavailable), ``flags``,
``label_mode`` (``flight_grounded`` or ``hardware_only``) and, for flight
rows, the stored ``targets`` of the selected simulation.  Adjacent
``motor_lookup.json`` maps readable motor ids to digests/fields (unresolved
motors included) and an optional ``assets.json`` sidecar holds custom thrust
curve assets.

Output (default ``new_results/``):
    sft_v4.jsonl             the main file: EXACTLY one row per catalog id
    sft_train_v4.jsonl       disjoint slices of the main file, family-isolated
    sft_val_v4.jsonl
    sft_test_v4.jsonl
    sft_v4_motor_lookup.json readable-id -> digest/fields lookup
    sft_v4_assets.json       copy of the source assets sidecar, when present
    sft_v4_coverage.json     every catalog id -> row/split/source/label_mode
    sft_v4_report.json       machine-readable report
    SFT_V4_REPORT.md         concise report

Honesty rules: no flight, training or CAD run happens in this assembler.
Flight numbers appear only in flight-grounded rows as recorded reference
data. Fresh dataset-preparation simulations are distinguished from older
saved results; neither is a safety guarantee. Hardware-only rows state missing performance and never invent
flight numbers.  Unsafe sources are kept with honest warnings, never called
safe.  Existing v3 artifacts are preserved byte-for-byte.  Contract failures
abort the run with named catalog ids; there are no placeholder rows and no
silent exclusions.  Rows whose complete conversation exceeds the token limit
stay in the main file with a context flag and their exact token count.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.sft_compact_design import dump_compact_json  # noqa: E402
from scripts.sft_compact_finalize import banned_hits, compute_flags  # noqa: E402
from scripts.sft_compact_motor_ids import apply_stage2_and_fix, load_lookup  # noqa: E402
from scripts.sft_compact_reasoning import (  # noqa: E402
    CLS_OF_TAG,
    COMPONENT_NAMES,
    FINSET_TAGS,
    RECOVERY_TAGS,
    TARGET_LABELS,
    child,
    children_of,
    coverage_gaps,
    find_rocket,
    fit_checks,
    fmt_value,
    render_airframe,
    render_balance,
    render_fins,
    render_leaf,
    render_propulsion,
    render_recovery,
    stage_wrappers,
    value_of,
    walk_components,
)

TOKENIZER_MODEL = "Qwen/Qwen2.5-3B-Instruct"
DEFAULT_SOURCES = ROOT / "sftgen/out/scratch/sft_v4_complete/sources.jsonl"
DEFAULT_CATALOG = ROOT.parents[1] / "data/rockets_full.jsonl"
MAIN_FILE = "sft_v4.jsonl"
SPLIT_FILES = {"train": "sft_train_v4.jsonl", "val": "sft_val_v4.jsonl",
               "test": "sft_test_v4.jsonl"}
LOOKUP_FILE = "sft_v4_motor_lookup.json"
ASSETS_FILE = "sft_v4_assets.json"
COVERAGE_FILE = "sft_v4_coverage.json"
REPORT_JSON = "sft_v4_report.json"
REPORT_MD = "SFT_V4_REPORT.md"
OUTPUT_NAMES = [MAIN_FILE, *SPLIT_FILES.values(), LOOKUP_FILE, ASSETS_FILE,
                COVERAGE_FILE, REPORT_JSON, REPORT_MD]
V3_NAMES = ("sft_v3.jsonl", "sft_test_v3.jsonl", "sft_v3_motor_lookup.json")
LABEL_MODES = ("flight_grounded", "hardware_only")

SYSTEM = {
    "role": "system",
    "content": (
        "You are an aerospace design assistant. Explain the airframe, "
        "propulsion, stability, and recovery choices inside <thought> tags, "
        "then output the complete OpenRocket design JSON inside <design> tags. "
        "Distinguish stored reference-flight results from static "
        "calculations. Do not claim to have run tools or guarantee flight "
        "safety. State missing data and safety limits."
    ),
}

HARDWARE_MISSING = ("flight performance (apogee, flight time, landing speed) "
                    "is unavailable and not invented")
FLIGHT_MARKER = "REFERENCE FLIGHT (stored results for this exact design"
USAGE_NOTES = [
    "sft_v4.jsonl is the complete 330-rocket corpus for curation and "
    "inspection; it CONTAINS the val and test slices, so it is NOT itself a "
    "held-out training split.",
    "For comparisons, train only on sft_train_v4.jsonl, tune on "
    "sft_val_v4.jsonl, and evaluate once on sft_test_v4.jsonl.",
    "Training on sft_v4.jsonl would leak every held-out rocket into "
    "training and invalidate test metrics.",
    "Duplicate hardware and original/motor-filled families never cross "
    "splits; group_id marks each family in every row.",
]
NOTES = [
    "The assembler itself runs no flights, training, CAD or installs. "
    "Upstream flight simulations are counted separately, and all flight "
    "numbers remain recorded reference data rather than safety guarantees.",
    "Fresh dataset-preparation simulations and reused saved results have "
    "distinct provenance and flags.",
    "Exactly one complete conversation per catalog id; duplicate designs are "
    "kept, not deduplicated away.",
    "Hardware-only rows never quote stored flight numbers; their prompts use "
    "real static dimensions, layout and constraints.",
    "Unsafe sources (hard landings, poor stability, fit problems) are kept "
    "with honest warnings in text and flags.",
    "Outdated saved simulations are marked as historical reference, never "
    "as current predictions.",
    "Rows over the token limit keep their complete design and carry "
    "context_over_limit with the exact token count.",
    "Oversized explanations are shortened to engineering summaries first; "
    "their complete design JSON is unchanged.",
    "v3 artifacts are preserved byte-for-byte; this assembler never writes "
    "them.",
    "Dataset-contract validation is not a claim that the full source-code "
    "unit-test suite passes.",
]


class ContractError(RuntimeError):
    """A source/input contract violation; assembly refuses to continue."""


# ---------------------------------------------------------------------------
# small pure helpers
# ---------------------------------------------------------------------------

def read_jsonl(path):
    with Path(path).open() as stream:
        return [json.loads(line) for line in stream if line.strip()]


def write_jsonl(path, rows):
    with Path(path).open("w") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def conversation_tokens(tokenizer, messages):
    # Transformers versions differ: apply_chat_template(tokenize=True) may
    # return a BatchEncoding whose len() is the number of fields, not tokens.
    # Always render the complete conversation, then count real token ids.
    rendered = tokenizer.apply_chat_template(messages, tokenize=False,
                                             add_generation_prompt=False)
    return len(tokenizer.encode(rendered, add_special_tokens=False))


_TOKENIZERS = {}


def cached_tokenizer(model=TOKENIZER_MODEL):
    if model not in _TOKENIZERS:
        from transformers import AutoTokenizer
        _TOKENIZERS[model] = AutoTokenizer.from_pretrained(model,
                                                          local_files_only=True)
    return _TOKENIZERS[model]


def is_number(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value))


def is_fresh_flight(record):
    return (record.get("metric_provenance") or {}).get("source") == \
        "new_openrocket_simulation"


def sig3_plain(value):
    """3 significant figures without scientific notation (for prompt bounds)."""
    return format(float(f"{value:.3g}"), "g")


def ceil_bound(value):
    """Round up to a tenth so a stored outcome satisfies the stated bound."""
    return f"{math.ceil((value + 0.01) * 10) / 10:g}"


def design_from_row(row):
    content = row["messages"][2]["content"]
    if any(content.count(tag) != 1 for tag in
           ("<thought>", "</thought>", "<design>", "</design>")):
        raise ValueError(f"{row['id']}: expected exactly one thought and design")
    return json.loads(content.split("<design>", 1)[1].split("</design>", 1)[0])


def source_key(file):
    """Group original and motor-filled copies of the same base file together."""
    return re.sub(r"_filled(?=\.ork$)", "", Path(file).name, flags=re.I)


def geometry_key(design):
    """Fingerprint the ordered rocket tree, ignoring motor/config/name metadata.

    Different motors in otherwise identical hardware belong to one family,
    even if that reduces the number of independent examples.
    """
    ignored = {"name", "id", "motorconfiguration", "motormount", "digest",
               "motor_id", "preset", "color", "linestyle", "designtype"}

    def clean(node):
        if isinstance(node, list):
            return [clean(v) for v in node]
        if not isinstance(node, dict):
            return node
        out = {}
        for key, value in node.items():
            if key == "children":
                children = []
                for wrapper in value:
                    if isinstance(wrapper, dict) and len(wrapper) == 1:
                        tag = next(iter(wrapper))
                        if tag in ignored:
                            continue
                    children.append(clean(wrapper))
                if children:
                    out[key] = children
            elif key == "attrs":
                attrs = {k: v for k, v in value.items()
                         if k not in {"id", "configid", "default"}}
                if attrs:
                    out[key] = attrs
            else:
                out[key] = clean(value)
        return out

    rocket = next(w["rocket"] for w in design["openrocket"]["children"]
                  if "rocket" in w)
    return hashlib.sha256(canonical(clean(rocket)).encode()).hexdigest()


def find_simulation_or_none(compact):
    for wrapper in children_of(compact.get("openrocket") or {}):
        if isinstance(wrapper, dict) and "simulations" in wrapper:
            for sim_wrapper in children_of(wrapper["simulations"]):
                if isinstance(sim_wrapper, dict) and "simulation" in sim_wrapper:
                    return sim_wrapper["simulation"]
    return None


def raw_motor_digests(compact):
    digests = []
    rocket = find_rocket(compact)
    for _tag, stage in stage_wrappers(rocket):
        for _tag2, payload, _depth in walk_components(stage):
            mount = child(payload, "motormount")
            if mount is None:
                continue
            motor = child(mount, "motor")
            if motor is not None:
                digests.append(value_of(child(motor, "digest")))
    return digests


def first_diff_path(left, right, path="root"):
    """Path of the first structural difference between two trees (or None)."""
    if type(left) is not type(right):
        return path
    if isinstance(left, dict):
        for key in sorted(set(left) | set(right), key=str):
            if key not in left or key not in right:
                return f"{path}.{key}"
            sub = first_diff_path(left[key], right[key], f"{path}.{key}")
            if sub:
                return sub
        return None
    if isinstance(left, list):
        if len(left) != len(right):
            return f"{path}[len {len(left)} != {len(right)}]"
        for i, (a, b) in enumerate(zip(left, right)):
            sub = first_diff_path(a, b, f"{path}[{i}]")
            if sub:
                return sub
        return None
    return None if left == right else f"{path} = {left!r} != {right!r}"


# ---------------------------------------------------------------------------
# input contract validation
# ---------------------------------------------------------------------------

def load_catalog(path):
    rows = read_jsonl(path)
    if not rows:
        raise ContractError(f"catalog {path} is empty")
    ids = [row.get("id") for row in rows]
    if any(not isinstance(rid, str) or not rid for rid in ids):
        raise ContractError("every catalog row needs a non-empty string id")
    if len(set(ids)) != len(ids):
        dupes = [rid for rid, n in Counter(ids).items() if n > 1]
        raise ContractError(f"catalog ids not unique: {dupes}")
    for row in rows:
        if not isinstance(row.get("source_file"), str) or not row["source_file"]:
            raise ContractError(f"catalog row {row.get('id')}: bad source_file")
    return rows


def assert_finite_tree(node, path, problems):
    """Reject non-finite floats anywhere in a source record value tree."""
    if isinstance(node, bool):
        return
    if isinstance(node, float):
        if not math.isfinite(node):
            problems.append(f"non-finite value at {path}")
        return
    if isinstance(node, dict):
        for key, value in node.items():
            assert_finite_tree(value, f"{path}.{key}", problems)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            assert_finite_tree(value, f"{path}[{i}]", problems)


def validate_flight_targets(targets, catalog_id, problems):
    if not isinstance(targets, dict) or not targets:
        problems.append(f"{catalog_id}: flight_grounded needs stored target metrics")
        return
    for key, value in targets.items():
        if not is_number(value):
            problems.append(
                f"{catalog_id}: target {key} is {value!r}; must be a finite "
                f"non-bool number")
        elif key in ("apogee_m",) and value <= 0:
            problems.append(f"{catalog_id}: apogee_m must be positive, got {value}")
        elif key != "apogee_m" and value < 0:
            problems.append(f"{catalog_id}: target {key} must be >= 0, got {value}")
    if "apogee_m" not in targets or "ground_hit_ms" not in targets:
        problems.append(f"{catalog_id}: flight_grounded needs apogee_m and "
                        f"ground_hit_ms")


def validate_source_contract(records, catalog, id_by_digest, assets=None):
    problems = []
    if len(records) != len(catalog):
        problems.append(f"source record count {len(records)} != catalog size "
                        f"{len(catalog)} (the contract is EXACT330)")
    for index, (rec, cat) in enumerate(zip(records, catalog)):
        cid = cat["id"]
        if rec.get("catalog_id") != cid:
            problems.append(f"record {index}: catalog_id "
                            f"{rec.get('catalog_id')!r} != catalog id {cid!r}; "
                            f"records must be in catalog order")
            continue
        if rec.get("error") or rec.get("excluded"):
            reason = rec.get("reason") or rec.get("error") or rec.get("excluded")
            problems.append(f"{cid}: source record is an exclusion/error record "
                            f"({reason}); the v4 goal needs a complete design "
                            f"for every catalog id")
            continue
        if rec.get("source_file") != cat.get("source_file"):
            problems.append(f"{cid}: source_file {rec.get('source_file')!r} != "
                            f"catalog source_file {cat.get('source_file')!r}")
        file = rec.get("file")
        if not isinstance(file, str) or not Path(file).is_absolute() \
                or not file.endswith(".ork"):
            problems.append(f"{cid}: 'file' must be an absolute .ork path, "
                            f"got {file!r}")
        if not isinstance(rec.get("source_id"), str) or not rec["source_id"]:
            problems.append(f"{cid}: missing source_id")
        label = rec.get("label_mode")
        if label not in LABEL_MODES:
            problems.append(f"{cid}: label_mode {label!r} not in {LABEL_MODES}")
            continue
        compact = rec.get("compact")
        if not isinstance(compact, dict):
            problems.append(f"{cid}: missing complete compact design")
        else:
            if compact.get("attachments"):
                registry = (assets or {}).get("assets") or {}
                for name, attachment in compact["attachments"].items():
                    if not any(
                        entry.get("attachment_name") == name
                        and entry.get("data_base64") == attachment.get("data_base64")
                        and cid in (entry.get("used_by") or [])
                        for entry in registry.values()
                    ):
                        problems.append(
                            f"{cid}: base64 thrust-curve attachment has no "
                            f"matching exact asset in the sidecar")
            try:
                find_rocket(compact)
            except (ValueError, KeyError, TypeError):
                problems.append(f"{cid}: compact has no rocket element")
            for digest in raw_motor_digests(compact):
                if digest is not None and str(digest) not in id_by_digest:
                    problems.append(f"{cid}: motor digest {digest} missing from "
                                    f"motor_lookup.json")
            for section, value in (("compact", compact),
                                   ("engineering", rec.get("engineering")),
                                   ("targets", rec.get("targets"))):
                assert_finite_tree(value, f"{cid}:{section}", problems)
        digest_entry = rec.get("digest_entry")
        if not isinstance(digest_entry, dict):
            problems.append(f"{cid}: digest_entry must record the load-check status")
        elif (digest_entry.get("c_pass") is not True
              and digest_entry.get("c_pass") is not False
              and digest_entry.get("c_pass") is not None):
            problems.append(f"{cid}: digest_entry.c_pass must be true, false, or null")
        elif not isinstance(digest_entry.get("components", []), list):
            problems.append(f"{cid}: digest_entry.components must be a list")
        flags = rec.get("flags")
        if not isinstance(flags, list) or any(not isinstance(f, str) for f in flags):
            problems.append(f"{cid}: flags must be a list of strings")
        if label == "flight_grounded":
            validate_flight_targets(rec.get("targets"), cid, problems)
            if is_fresh_flight(rec) and (
                    rec.get("metric_provenance") or {}).get("no_flight_rerun") is not False:
                problems.append(f"{cid}: fresh simulation provenance must "
                                f"set no_flight_rerun to false")
            if not isinstance(rec.get("sim"), str) or not rec["sim"]:
                problems.append(f"{cid}: flight_grounded needs the selected "
                                f"simulation name")
            if not isinstance(rec.get("simulation_status"), str) or \
                    not rec["simulation_status"]:
                problems.append(f"{cid}: flight_grounded needs an honest "
                                f"simulation status")
        else:
            if rec.get("sim") is not None and not isinstance(rec.get("sim"), str):
                problems.append(f"{cid}: sim must be a name or null")
            if isinstance(rec.get("targets"), dict):
                for key, value in rec["targets"].items():
                    if not is_number(value):
                        problems.append(
                            f"{cid}: hardware_only target {key} is {value!r}; "
                            f"untrusted values must still be finite or absent")
    if problems:
        shown = "\n".join(f"- {p}" for p in problems[:60])
        more = "" if len(problems) <= 60 else f"\n... and {len(problems) - 60} more"
        raise ContractError("source contract violations "
                            f"({len(problems)} problems):\n{shown}{more}")


# ---------------------------------------------------------------------------
# prompts
# ---------------------------------------------------------------------------

def flight_prompt(targets):
    parts = [f"Design a complete model rocket that reaches about "
             f"{sig3_plain(targets['apogee_m'])} m apogee"]
    parts.append(f"and touches down under {ceil_bound(targets['ground_hit_ms'])} m/s")
    duration = targets.get("flight_time_s")
    if is_number(duration) and duration > 0:
        parts.append(f"with total flight time under {ceil_bound(duration)} s")
    wind = targets.get("wind_ms")
    if is_number(wind) and wind >= 0:
        parts.append(f"launched in about {sig3_plain(wind)} m/s wind")
    return ", ".join(parts) + ". Provide the complete hardware design."


def _numeric_radius(payload):
    radius = value_of(child(payload, "radius"))
    if is_number(radius):
        return float(radius)
    for tag in ("aftradius", "foreradius"):
        value = value_of(child(payload, tag))
        if is_number(value):
            return float(value)
    return None


def hardware_facts(design, eng, dump_rows):
    """Real, static, design-specific facts for hardware-only prompts."""
    rocket = find_rocket(design)
    facts = []
    stages = stage_wrappers(rocket)
    facts.append("single stage" if len(stages) == 1 else f"{len(stages)} stages")
    diameter = eng.get("reference_diameter_m") if isinstance(eng, dict) else None
    if not is_number(diameter):
        radii = []
        for _tag, stage in stage_wrappers(rocket):
            for _t, payload, _d in walk_components(stage):
                radius = _numeric_radius(payload)
                if radius is not None:
                    radii.append(radius)
        diameter = 2 * max(radii) if radii else None
    if is_number(diameter) and diameter > 0:
        facts.append(f"airframe about {diameter * 1000:.0f} mm in diameter")
    lengths = [row.get("loaded", {}).get("getLength") for row in dump_rows
                if row.get("cls") == "AxialStage" and row.get("parent_index") == -1]
    lengths = [v for v in lengths if is_number(v)]
    if lengths:
        facts.append(f"about {sum(lengths) * 1000:.0f} mm long")
    nose = None
    for _tag, stage in stage_wrappers(rocket):
        for tag, payload, _d in walk_components(stage):
            if tag == "nosecone" and nose is None:
                nose = (value_of(child(payload, "shape")),
                        value_of(child(payload, "length")))
    if nose is not None:
        shape, length = nose
        bits = []
        if isinstance(shape, str) and shape:
            bits.append(f"{shape} nose cone")
        else:
            bits.append("nose cone")
        if is_number(length) and length > 0:
            bits.append(f"about {length * 1000:.0f} mm")
        facts.append(" ".join(bits))
    finsets = [(tag, payload) for _tag, stage in stage_wrappers(rocket)
               for tag, payload, _d in walk_components(stage)
               if tag in FINSET_TAGS]
    if finsets:
        counts = [value_of(child(payload, "fincount")) for _tag, payload in finsets]
        counts = [int(c) for c in counts if is_number(c)]
        total = sum(counts) if counts else None
        desc = COMPONENT_NAMES.get(finsets[0][0], "fin set")
        if total is not None:
            word = "fins" if len(finsets) == 1 else f"fins in {len(finsets)} fin sets"
            facts.append(f"{total} {word} ({desc})")
        else:
            facts.append(desc)
    recovery = {tag for _tag, stage in stage_wrappers(rocket)
                for tag, _p, _d in walk_components(stage)
                if tag in RECOVERY_TAGS}
    if "parachute" in recovery:
        facts.append("parachute recovery")
    elif "streamer" in recovery:
        facts.append("streamer recovery")
    elif recovery:
        facts.append("shock cord but no parachute or streamer")
    designations = []
    for _tag, stage in stage_wrappers(rocket):
        for _t, payload, _d in walk_components(stage):
            mount = child(payload, "motormount")
            motor = child(mount or {}, "motor") if mount is not None else None
            if motor is not None:
                desig = value_of(child(motor, "designation"))
                if isinstance(desig, str) and desig:
                    designations.append(desig)
    if not designations and isinstance(eng, dict):
        for entry in eng.get("motors") or []:
            if isinstance(entry, dict) and isinstance(entry.get("motor"), dict):
                desig = entry["motor"].get("designation")
                if isinstance(desig, str) and desig:
                    designations.append(desig)
    if designations:
        names = "/".join(dict.fromkeys(designations))
        facts.append(f"{names} motor" if len(set(designations)) == 1
                     else f"{names} motors")
    return facts


def hardware_prompt(facts):
    spec = "; ".join(facts) if facts else "the complete stored hardware tree"
    return ("Design a complete model rocket to this hardware specification: "
            f"{spec}. No trustworthy flight results are stored for this "
            "configuration, so provide the complete hardware blueprint with "
            "static fit and stability reasoning, and state that flight "
            "performance is unavailable.")


# ---------------------------------------------------------------------------
# thought rendering (v4: reference data, never circular verification)
# ---------------------------------------------------------------------------

def launch_setup_lines(sim, rocket, label_mode):
    rocket_bits = []
    for wrapper in children_of(rocket):
        if isinstance(wrapper, dict) and "referencetype" in wrapper:
            rendered = render_leaf("referencetype", wrapper["referencetype"])
            if rendered:
                rocket_bits.append(rendered)
    if sim is None:
        lines = ["LAUNCH SETUP:", "- no stored launch setup is available for "
                 "this design."]
        if rocket_bits:
            lines.append("- stored rocket-level input: "
                         + "; ".join(rocket_bits) + ".")
        return lines
    header = ("LAUNCH SETUP (stored inputs of the reference flight):"
              if label_mode == "flight_grounded" else
              "STORED LAUNCH SETUP (inputs of a stored simulation; its flight "
              "results are not used):")
    bits = []
    conditions = child(sim, "conditions") or {}
    for wrapper in children_of(conditions):
        if not (isinstance(wrapper, dict) and len(wrapper) == 1):
            continue
        (ctag, cpayload), = wrapper.items()
        if ctag == "configid":
            continue
        rendered = render_leaf(ctag, cpayload)
        if rendered:
            bits.append(rendered)
    for tag in ("simulator", "calculator"):
        node = child(sim, tag)
        if node is not None:
            rendered = render_leaf(tag, node)
            if rendered:
                bits.append(rendered)
    bits.extend(rocket_bits)
    line = "; ".join(bits) + "."
    if label_mode == "flight_grounded":
        line += " (all values are stored inputs of the reference flight)"
    return [header, f"- {line}"]


def render_v4_thought(design, eng, record, prompt_text):
    """One <thought> for a v4 row. Returns rendered pieces and honesty data.

    Same section contract as the current pipeline, except the flight section
    presents stored results as reference data (no expected-vs-target
    circularity) and hardware-only rows state missing performance.
    """
    rocket = find_rocket(design)
    sim = find_simulation_or_none(design)
    label_mode = record["label_mode"]
    targets = record.get("targets") if label_mode == "flight_grounded" else {}
    targets = targets or {}

    req = ["REQUIREMENTS:", f'request, in full: "{prompt_text}"']
    if label_mode == "flight_grounded":
        if is_fresh_flight(record):
            req.append(
                "flight results simulated during dataset preparation for "
                "this exact design are reference data: recorded outcomes, "
                "not values computed in this response and not a guarantee. "
                "See REFERENCE FLIGHT below.")
        else:
            req.append(
                "stored flight results for this exact design are reference data: "
                "recorded outcomes, not values computed here and not a guarantee. "
                "See REFERENCE FLIGHT below.")
    else:
        req.append(
            "no trustworthy stored flight result exists for this design: "
            + HARDWARE_MISSING + ". This answer is hardware-based; the static "
            "values below come from the stored design and static loading.")
    if record.get("load_warning"):
        req.append(record["load_warning"])

    comps = [(tag, payload) for _st_tag, stage in stage_wrappers(rocket)
             for tag, payload, _depth in walk_components(stage)]
    dump = (record.get("digest_entry") or {}).get("components") or []
    fit_lines, fit_failures, not_computed = fit_checks(comps, dump, eng)
    fit = (["HOW THE PARTS FIT (checked with the numbers of this design):"]
           + [f"- {line}" for line in fit_lines])
    if fit_failures:
        fit.append("- fit problems found by these checks: "
                   + "; ".join(fit_failures) + ".")
    if not_computed:
        fit.append("- not computed (input automatic or check not derivable): "
                   + "; ".join(not_computed) + ".")
    fins = render_fins(rocket) or ["FINS: this design has no fin set."]
    propulsion, motor_diffs, ttw_certain = render_propulsion(design, rocket, eng)
    balance = render_balance(eng)
    recovery = render_recovery(rocket, targets)

    if label_mode == "flight_grounded":
        bits = []
        for key, label, unit in TARGET_LABELS:
            if key in targets:
                u = f" {unit}" if unit else ""
                bits.append(f"{label} {fmt_value(targets[key])}{u}")
        framing = ("; simulated during dataset preparation, not a guarantee):"
                   if is_fresh_flight(record) else
                   "; recorded data, not rerun here, not a guarantee):")
        flight = [FLIGHT_MARKER + framing,
                  "- " + "; ".join(bits) + "."]
        status = record.get("simulation_status")
        if is_fresh_flight(record):
            flight.append("- the matching configuration was simulated during "
                          "dataset preparation; these outcomes are not a "
                          "flight-safety certification.")
        elif status == "uptodate":
            flight.append("- the stored result is marked up to date with the "
                          "design as loaded.")
        else:
            flight.append(f"- the stored result is marked {status}; the design "
                          "may have changed since it was produced, so treat "
                          "these numbers as historical reference only.")
    else:
        flight = ["FLIGHT PERFORMANCE:",
                  "- unavailable for this design: no flight was run here and "
                  "no stored flight result is trusted; apogee, flight time "
                  "and landing speed are missing (not zero)."]
        if sim is not None:
            flight.append("- a stored launch setup exists (below), but its "
                          "stored flight results are not used.")

    launch = launch_setup_lines(sim, rocket, label_mode)
    thought = "\n".join(
        req + [""] + render_airframe(rocket) + [""] + fit + [""] + fins + [""]
        + propulsion + [""] + balance + [""] + recovery + [""] + flight + [""]
        + launch)

    gaps = coverage_gaps(thought, design)
    if gaps:
        lines = ["", "OTHER STORED DESIGN VALUES (kept complete; not "
                  "explained by the sections above):"]
        for start in range(0, len(gaps), 8):
            lines.append("- " + "; ".join(gaps[start:start + 8]) + ".")
        thought += "\n" + "\n".join(lines)
        remaining = coverage_gaps(thought, design)
        if remaining:  # cannot happen: every gap value is quoted verbatim
            raise ContractError("coverage fallback failed to quote values: "
                                + "; ".join(remaining[:5]))
    return {"thought": thought, "motor_diffs": motor_diffs,
            "fit_failures": fit_failures, "not_computed": not_computed,
            "ttw_certain": ttw_certain, "coverage_fallback": gaps,
            "simulation": sim}


def enrich_motor_diffs(motor_diffs, raw_compact, eng):
    """Digest comparison computed from the RAW compact (its digests are gone
    from the rendered design), matching the verified build_row behaviour."""
    rocket_raw = find_rocket(raw_compact)
    raw_digests = []
    for _tag, stage in stage_wrappers(rocket_raw):
        for _tag2, payload, _depth in walk_components(stage):
            mount = child(payload, "motormount")
            if mount is None:
                continue
            motor = child(mount, "motor")
            if motor is not None:
                digest = child(motor, "digest")
                raw_digests.append(value_of(digest) if digest is not None else None)
    resolved = [(m.get("motor") or {}).get("digest")
                for m in ((eng or {}).get("motors") or [])
                if isinstance(m, dict) and m.get("motor")]
    for i, md in enumerate(motor_diffs):
        raw_digest = raw_digests[i] if i < len(raw_digests) else None
        resolved_digest = resolved[i] if i < len(resolved) else None
        md["digest_differs"] = (None if raw_digest is None or resolved_digest is None
                               else str(raw_digest) != str(resolved_digest))
    return motor_diffs


# ---------------------------------------------------------------------------
# row building
# ---------------------------------------------------------------------------

def build_model_design(record, catalog_id, id_by_digest):
    compact = record["compact"]
    design, preset_fixes = apply_stage2_and_fix(
        compact, id_by_digest, (record.get("digest_entry") or {}).get("components")
        or [])
    design.pop("attachments", None)
    model_compact = record.get("model_compact")
    if model_compact is not None:
        path = first_diff_path(model_compact, design)
        if path is not None:
            raise ContractError(
                f"{catalog_id}: model_compact differs from the design built "
                f"from compact through the verified sanitizer, first "
                f"difference at {path}")
    return design, preset_fixes


def build_row(index, record, catalog, id_by_digest):
    cat = catalog
    catalog_id = cat["id"]
    source_label_mode = record["label_mode"]
    load_pass = (record.get("digest_entry") or {}).get("c_pass")
    if load_pass is not True:
        record = dict(record)
        structure_preserved = (
            (record.get("source_preservation") or {}).get("extraction") or {}
        ).get("static_check_passed") is True
        if load_pass is False or not structure_preserved:
            record["label_mode"] = "hardware_only"
        record["load_warning"] = (
            "The static load-equivalence check failed; this hardware example "
            "retains the source parameters, but its converted flight behavior "
            "has not been established."
            if load_pass is False else
            "The static load-equivalence check is unavailable; this hardware "
            "example retains the source parameters, but its converted flight "
            "behavior has not been established."
        )
    label_mode = record["label_mode"]
    status = record.get("simulation_status")
    design, preset_fixes = build_model_design(record, catalog_id, id_by_digest)
    eng = record.get("engineering") if isinstance(record.get("engineering"), dict) \
        else {}
    dump_rows = (record.get("digest_entry") or {}).get("components") or []

    if label_mode == "flight_grounded":
        prompt_text = flight_prompt(record["targets"])
    else:
        prompt_text = hardware_prompt(hardware_facts(design, eng, dump_rows))

    rendered = render_v4_thought(design, eng, record, prompt_text)
    motor_diffs = enrich_motor_diffs(rendered["motor_diffs"],
                                     record["compact"], eng)
    targets = dict(record["targets"]) if label_mode == "flight_grounded" else {}

    flags = compute_flags(targets, eng, motor_diffs,
                          rendered["fit_failures"], rendered["ttw_certain"])
    if label_mode == "flight_grounded":
        flags.append("new_flight_simulation" if is_fresh_flight(record)
                     else "saved_flight_not_rerun")
        if not is_fresh_flight(record) and status != "uptodate":
            flags.append("saved_simulation_not_uptodate")
    else:
        flags.append("no_trusted_flight_data")
    if load_pass is not True:
        flags.append("static_load_check_failed" if load_pass is False else
                     "static_load_check_unavailable")
    if rendered["coverage_fallback"]:
        flags.append("thought_coverage_fallback")
    for flag in record.get("flags") or []:
        if label_mode == "flight_grounded" and is_fresh_flight(record) and \
                flag in {"saved_flight_not_rerun", "saved_simulation_not_uptodate",
                         "hardware_only_no_flight_labels", "no_trusted_flight_data"}:
            continue
        if flag not in flags:
            flags.append(flag)

    design_json = dump_compact_json(design)
    assistant = (f"<thought>\n{rendered['thought']}\n</thought>\n"
                 f"<design>\n{design_json}\n</design>")
    row = {
        "id": f"V4-{index:04d}",
        "catalog_id": catalog_id,
        "source_id": record.get("source_id"),
        "source_file": record.get("source_file"),
        "origin": record.get("origin"),
        "file": record.get("file"),
        "sim": record.get("sim"),
        "label_mode": label_mode,
        "source_label_mode": source_label_mode,
        "static_load_check": {
            "c_pass": load_pass,
            "reason": (record.get("digest_entry") or {}).get("error"),
        },
        "metric_provenance": copy.deepcopy(record.get("metric_provenance") or {}),
        "source_preservation": copy.deepcopy(record.get("source_preservation") or {}),
        "reference_targets": (copy.deepcopy(record.get("targets") or {})
                              if source_label_mode != label_mode else {}),
        "simulation_status": status,
        "split": None,
        "group_id": None,
        "prompt_text": prompt_text,
        "messages": [copy.deepcopy(SYSTEM), {"role": "user",
                                            "content": prompt_text},
                     {"role": "assistant", "content": assistant}],
        "targets": targets,
        "flags": flags,
        "row_tokens": None,
        "source_version": "v4",
        "preset_fixes": preset_fixes,
    }
    return row, design


def compact_reasoning(row, record, design):
    """Summarize repeated explanations without changing any design JSON."""
    assistant = row["messages"][2]["content"]
    thought = assistant.split("<thought>", 1)[1].split("</thought>", 1)[0].strip()
    requirements = thought.split("\n\n", 1)[0]
    rocket = find_rocket(design)
    eng = record.get("engineering") or {}
    dump = (record.get("digest_entry") or {}).get("components") or []
    facts = hardware_facts(design, eng, dump)
    comps = [(tag, payload) for _stage_tag, stage in stage_wrappers(rocket)
             for tag, payload, _depth in walk_components(stage)]
    fit_lines, fit_failures, not_computed = fit_checks(comps, dump, eng)
    propulsion, _motor_diffs, _ttw_certain = render_propulsion(design, rocket, eng)
    if FLIGHT_MARKER in thought:
        flight = FLIGHT_MARKER + thought.split(FLIGHT_MARKER, 1)[1].split("\n\n", 1)[0]
    else:
        flight = "FLIGHT PERFORMANCE:\n- " + HARDWARE_MISSING + "."
    lines = [
        requirements, "", "AIRFRAME AND GEOMETRY:",
        "- " + "; ".join(facts) + ".",
        "- The ordered stages, dimensions, materials, fin shapes, positions, "
        "and overrides remain complete in the design JSON below.",
        "", "REPRESENTATIVE FIT RELATIONSHIPS:",
        *["- " + line for line in fit_lines[:8]],
    ]
    if fit_failures:
        lines.append("- Some source size checks report conflicts; do not "
                     "assume this hardware is free of fit problems.")
    if not_computed:
        lines.append("- Some automatic dimensions or fit checks need "
                     "downstream resolution; they are not assumed to pass.")
    lines += [
        "", *propulsion[:20], "", *render_balance(eng),
        "", *render_recovery(rocket, row["targets"])[:8],
        "", flight,
        "", *launch_setup_lines(find_simulation_or_none(design), rocket,
                                row["label_mode"])[:8],
        "", "Only repeated explanations are summarized here. All hardware "
        "parameters remain in the complete design; summarizing them does "
        "not run a flight simulation.",
    ]
    design_suffix = assistant.split("<design>", 1)[1]
    row["messages"][2]["content"] = (
        "<thought>\n" + "\n".join(lines) + "\n</thought>\n<design>" + design_suffix)
    row["reasoning_compacted"] = True
    row["flags"] = [flag for flag in row["flags"]
                    if flag != "thought_coverage_fallback"]
    row["flags"].append("reasoning_summarized_for_context")


# ---------------------------------------------------------------------------
# splits
# ---------------------------------------------------------------------------

def assign_splits(rows, seed=42):
    """Union filename families and geometry families; hold out whole groups."""
    parent = list(range(len(rows)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        parent[find(j)] = find(i)

    seen = {}
    for i, row in enumerate(rows):
        for key in (("file", source_key(row["file"])),
                    ("geometry", geometry_key(design_from_row(row)))):
            if key in seen:
                union(i, seen[key])
            else:
                seen[key] = i
    groups = defaultdict(list)
    for i in range(len(rows)):
        groups[find(i)].append(i)
    ordered = sorted(groups.values(), key=lambda g: g[0])
    rng = random.Random(seed)
    rng.shuffle(ordered)
    n_test = max(1, round(len(ordered) * 0.1)) if len(ordered) >= 3 else 0
    n_val = max(1, round(len(ordered) * 0.1)) if len(ordered) >= 3 else 0
    assignment = {}
    for split, group_list in (("test", ordered[:n_test]),
                              ("val", ordered[n_test:n_test + n_val]),
                              ("train", ordered[n_test + n_val:])):
        for group in group_list:
            group_id = rows[group[0]]["id"]
            for i in group:
                assignment[i] = (split, group_id)
    for i, row in enumerate(rows):
        row["split"], row["group_id"] = assignment[i]
    return rows


# ---------------------------------------------------------------------------
# validation
# ---------------------------------------------------------------------------

def _walk(node, fn):
    if isinstance(node, dict):
        fn(node)
        for value in node.values():
            _walk(value, fn)
    elif isinstance(node, list):
        for value in node:
            _walk(value, fn)


def check_row(row, design, lookup, token_count, limit):
    rid = row["id"]
    issues = []
    roles = [m["role"] for m in row["messages"]]
    if roles != ["system", "user", "assistant"]:
        issues.append(f"{rid}: invalid role sequence")
        return issues
    if row["messages"][0] != SYSTEM:
        issues.append(f"{rid}: system message changed")
    if row["messages"][1]["content"] != row["prompt_text"]:
        issues.append(f"{rid}: prompt mismatch")
    assistant = row["messages"][2]["content"]
    for message in row["messages"]:
        for hit in banned_hits(message["content"]):
            issues.append(f"{rid}: banned text in {message['role']} message: {hit}")
    for leak in ("/Users/", "\\Users", "C:\\", ".ork"):
        if leak in row["messages"][1]["content"] + assistant:
            issues.append(f"{rid}: path or filename leakage: {leak}")
    try:
        parsed = design_from_row(row)
    except (ValueError, json.JSONDecodeError) as exc:
        issues.append(f"{rid}: broken design tags: {exc}")
        return issues
    if canonical(parsed) != canonical(design):
        issues.append(f"{rid}: design in message differs from the built design "
                      f"(truncation is forbidden)")
    if "vs target" in assistant:
        issues.append(f"{rid}: circular expected-vs-target comparison text")

    def visit(node):
        if isinstance(node, dict):
            for tag, payload in node.items():
                if tag == "motor_id":
                    if payload.get("value") not in lookup:
                        issues.append(f"{rid}: unknown motor id "
                                      f"{payload.get('value')}")
                elif tag == "digest":
                    issues.append(f"{rid}: model-visible motor digest")
                visit(payload)
        elif isinstance(node, list):
            for value in node:
                visit(value)
    visit(parsed)

    if row["label_mode"] == "flight_grounded":
        if FLIGHT_MARKER not in assistant:
            issues.append(f"{rid}: flight row missing reference-flight framing")
        expected_flag = ("new_flight_simulation" if is_fresh_flight(row)
                         else "saved_flight_not_rerun")
        if expected_flag not in row["flags"]:
            issues.append(f"{rid}: flight row missing {expected_flag} flag")
        if is_fresh_flight(row) and "saved_flight_not_rerun" in row["flags"]:
            issues.append(f"{rid}: fresh flight incorrectly flagged as not rerun")
        if not is_fresh_flight(row) and row["simulation_status"] != "uptodate" and \
                "saved_simulation_not_uptodate" not in row["flags"]:
            issues.append(f"{rid}: outdated saved result not flagged")
        if row["targets"].get("ground_hit_ms", 0) > 8 and \
                "landing_over_8ms" not in row["flags"]:
            issues.append(f"{rid}: missing unsafe-landing flag")
    else:
        if HARDWARE_MISSING not in assistant:
            issues.append(f"{rid}: hardware row missing missing-performance "
                          f"statement")
        if FLIGHT_MARKER in assistant:
            issues.append(f"{rid}: hardware row must not cite reference flight")
        if "no_trusted_flight_data" not in row["flags"]:
            issues.append(f"{rid}: hardware row missing its flag")
        if row["targets"]:
            issues.append(f"{rid}: hardware row must not carry target metrics")
    count = token_count(row["messages"])
    if count != row["row_tokens"]:
        issues.append(f"{rid}: stored token count {row['row_tokens']} != "
                      f"actual {count}")
    if count > limit and "context_over_limit" not in row["flags"]:
        issues.append(f"{rid}: over the token limit without context flag")
    if count <= limit and "context_over_limit" in row["flags"]:
        issues.append(f"{rid}: context flag on a row within the limit")
    return issues


def validate_corpus(rows, designs, lookup, token_count, limit, catalog):
    issues = []
    seen_texts = set()
    for i, (row, cat) in enumerate(zip(rows, catalog), start=1):
        if row["id"] != f"V4-{i:04d}" or row["catalog_id"] != cat["id"]:
            issues.append(f"row {i}: main file must keep catalog order "
                          f"({row['id']}/{row['catalog_id']})")
        issues.extend(check_row(row, designs[row["id"]], lookup, token_count,
                                limit))
        if row["split"] not in SPLIT_FILES or not row["group_id"]:
            issues.append(f"{row['id']}: missing split metadata")
        text_key = canonical(row["messages"])
        if text_key in seen_texts:
            pass  # duplicate hardware across catalog ids is allowed
        seen_texts.add(text_key)
    file_splits, geometry_splits, group_splits = defaultdict(set), defaultdict(set), defaultdict(set)
    for row in rows:
        file_splits[source_key(row["file"])].add(row["split"])
        geometry_splits[geometry_key(design_from_row(row))].add(row["split"])
        group_splits[row["group_id"]].add(row["split"])
    for name, splits in (("source rocket", file_splits),
                         ("identical geometry", geometry_splits),
                         ("family group", group_splits)):
        for key, values in splits.items():
            if len(values) > 1:
                issues.append(f"{name} {key} appears in multiple splits: "
                              f"{sorted(values)}")
    return issues


# ---------------------------------------------------------------------------
# assembly
# ---------------------------------------------------------------------------

def assemble(sources_path, output_dir, catalog_path=None, token_limit=32768,
             overwrite=False, tokenizer=None, seed=42, exclude_file=None):
    sources_path, output_dir = Path(sources_path), Path(output_dir)
    catalog_path = Path(catalog_path) if catalog_path else DEFAULT_CATALOG
    if not sources_path.exists():
        raise ContractError(f"sources file {sources_path} does not exist; run "
                            f"scripts/sft_v4_sources.py first (source agent)")
    if not catalog_path.exists():
        raise ContractError(f"catalog file {catalog_path} does not exist")
    existing = [name for name in OUTPUT_NAMES if (output_dir / name).exists()]
    if existing and not overwrite:
        raise FileExistsError(
            "v4 outputs already exist (" + ", ".join(existing)
            + "); use --overwrite to regenerate them")
    inputs_dir = ROOT / "new_results"
    v3_before = {name: sha(inputs_dir / name) for name in V3_NAMES}

    catalog = load_catalog(catalog_path)
    full_catalog_size = len(catalog)
    excluded_entries = []
    if exclude_file is not None:
        # Deliberate, owner-approved exclusions. Only the listed catalog ids
        # leave the contract; every other check still applies.
        excluded_entries = json.loads(Path(exclude_file).read_text())
        if not isinstance(excluded_entries, list) or not all(
                isinstance(e, dict) and isinstance(e.get("catalog_id"), str)
                for e in excluded_entries):
            raise ContractError("exclude file must be a JSON list of objects "
                                "with a catalog_id string")
        excluded_ids = [e["catalog_id"] for e in excluded_entries]
        if len(set(excluded_ids)) != len(excluded_ids):
            raise ContractError("exclude file lists a catalog id twice")
        catalog_ids = {cat["id"] for cat in catalog}
        missing = sorted(set(excluded_ids) - catalog_ids)
        if missing:
            raise ContractError(f"exclude file names unknown catalog ids: {missing}")
        catalog = [cat for cat in catalog if cat["id"] not in set(excluded_ids)]
    records = read_jsonl(sources_path)
    lookup, id_by_digest, _digest_by_id = load_lookup(
        sources_path.parent / "motor_lookup.json")
    assets_path = sources_path.parent / "assets.json"
    assets = None
    if assets_path.exists():
        assets = json.loads(assets_path.read_text())
        if not isinstance(assets, dict):
            raise ContractError("assets sidecar must be a JSON object")
    validate_source_contract(records, catalog, id_by_digest, assets)
    completion_path = sources_path.parent / "flight_completion_report.json"
    completion = {}
    if completion_path.exists():
        completion = json.loads(completion_path.read_text())
        if not isinstance(completion, dict):
            raise ContractError("flight completion report must be a JSON object")
    if any(is_fresh_flight(record) for record in records) and not completion:
        raise ContractError("fresh flight records require an adjacent "
                            "flight_completion_report.json")
    flight_simulations_run = completion.get("flight_simulations_run", 0)
    if type(flight_simulations_run) is not int or flight_simulations_run < 0:
        raise ContractError("flight_simulations_run must be a non-negative integer")

    rows, designs, problems = [], {}, []
    for index, (record, cat) in enumerate(zip(records, catalog), start=1):
        try:
            row, design = build_row(index, record, cat, id_by_digest)
        except ContractError as exc:
            problems.append(str(exc))
            continue
        except Exception as exc:  # surfaced honestly, never silently skipped
            problems.append(f"{cat['id']}: {type(exc).__name__}: {exc}")
            continue
        rows.append(row)
        designs[row["id"]] = design
    if problems:
        raise ContractError("row building failed for "
                             f"{len(problems)} rocket(s):\n"
                             + "\n".join(f"- {p}" for p in problems[:40])
                             + ("" if len(problems) <= 40 else
                                f"\n... and {len(problems) - 40} more"))

    rows = assign_splits(rows, seed=seed)
    tokenizer = tokenizer or cached_tokenizer()

    def token_count(messages):
        return conversation_tokens(tokenizer, messages)

    records_by_id = {record["catalog_id"]: record for record in records}
    for row in rows:
        row["row_tokens"] = token_count(row["messages"])
        if row["row_tokens"] > token_limit:
            compact_reasoning(row, records_by_id[row["catalog_id"]],
                              designs[row["id"]])
            row["row_tokens"] = token_count(row["messages"])
        if row["row_tokens"] > token_limit:
            row["flags"].append("context_over_limit")
    issues = validate_corpus(rows, designs, lookup, token_count, token_limit,
                             catalog)
    if issues:
        raise ContractError("final validation failed:\n"
                            + "\n".join(f"- {i}" for i in issues[:40])
                            + ("" if len(issues) <= 40 else
                               f"\n... and {len(issues) - 40} more"))
    v3_after = {name: sha(inputs_dir / name) for name in V3_NAMES}
    if v3_after != v3_before:
        raise RuntimeError("v3 inputs changed during assembly")

    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_dir / MAIN_FILE, rows)
    for split, filename in SPLIT_FILES.items():
        write_jsonl(output_dir / filename,
                    [row for row in rows if row["split"] == split])
    (output_dir / LOOKUP_FILE).write_text(
        json.dumps(lookup, ensure_ascii=False, indent=1, allow_nan=False) + "\n")
    if assets is not None:
        (output_dir / ASSETS_FILE).write_text(
            json.dumps(assets, ensure_ascii=False, indent=1, allow_nan=False)
            + "\n")

    entries = []
    for row, record in zip(rows, records):
        entries.append({
            "catalog_id": row["catalog_id"],
            "row_id": row["id"],
            "row_index": int(row["id"].split("-")[1]),
            "split": row["split"],
            "group_id": row["group_id"],
            "source_id": row["source_id"],
            "source_file": row["source_file"],
            "origin": row["origin"],
            "sim": row["sim"],
            "simulation_status": row["simulation_status"],
            "label_mode": row["label_mode"],
            "row_tokens": row["row_tokens"],
            "row_flags": row["flags"],
            "source_flags": record.get("flags") or [],
            "selection": record.get("selection"),
            "metric_provenance": record.get("metric_provenance"),
            "source_preservation": record.get("source_preservation"),
        })
    coverage = {
        "generated_by": "scripts/sft_v4_assemble.py",
        "catalog_path": str(catalog_path),
        "catalog_size": len(catalog),
        "main_file": MAIN_FILE,
        "rows": len(rows),
        "splits": {split: {"rows": sum(r["split"] == split for r in rows),
                           "file": SPLIT_FILES[split]}
                   for split in SPLIT_FILES},
        "usage": USAGE_NOTES,
        "entries": entries,
    }
    (output_dir / COVERAGE_FILE).write_text(
        json.dumps(coverage, ensure_ascii=False, indent=1, allow_nan=False) + "\n")

    tokens = sorted(row["row_tokens"] for row in rows)
    over_limit = [{"row_id": row["id"], "catalog_id": row["catalog_id"],
                   "row_tokens": row["row_tokens"]}
                  for row in rows if row["row_tokens"] > token_limit]
    report = {
        "assembler": "scripts/sft_v4_assemble.py",
        "goal": ("exactly one complete SFT conversation per catalog id; "
                 "no exclusions, no placeholders"),
        "validation_errors": issues,
        "flight_simulations_run": flight_simulations_run,
        "assembler_flight_simulations_run": 0,
        "flight_completion_report": str(completion_path) if completion else None,
        "flight_completion": completion,
        "sources_path": str(sources_path),
        "sources_sha256": sha(sources_path),
        "catalog_path": str(catalog_path),
        "catalog_sha256": sha(catalog_path),
        "tokenizer": TOKENIZER_MODEL,
        "token_count_method": ("apply_chat_template render + encode of the "
                               "complete system/user/assistant conversation"),
        "token_limit": token_limit,
        "rows": len(rows),
        "rockets": len(rows),
        "catalog_size": len(catalog),
        "catalog_rockets_included": len(rows),
        "label_modes": dict(Counter(row["label_mode"] for row in rows)),
        "flight_label_sources": dict(Counter(
            "new_simulation" if is_fresh_flight(row) else "saved_result"
            for row in rows if row["label_mode"] == "flight_grounded")),
        "simulation_status": dict(Counter(
            row["simulation_status"] if row["simulation_status"] else "none"
            for row in rows)),
        "full_catalog_size": full_catalog_size,
        "excluded_records": len(excluded_entries),
        "excluded_catalog_ids": excluded_entries,
        "exclusion_policy": ("input contract failures abort the assembly with "
                             "named catalog ids; rows are never silently "
                             "dropped or replaced, except catalog ids listed "
                             "in --exclude-file as owner-approved exclusions"),
        "splits": {split: {
            "rows": sum(r["split"] == split for r in rows),
            "rockets": sum(r["split"] == split for r in rows),
            "groups": len({r["group_id"] for r in rows if r["split"] == split}),
            "file": SPLIT_FILES[split],
        } for split in SPLIT_FILES},
        "family_groups": len({row["group_id"] for row in rows}),
        "tokens": {
            "min": tokens[0] if tokens else None,
            "median": tokens[len(tokens) // 2] if tokens else None,
            "max": tokens[-1] if tokens else None,
            "over_limit": over_limit,
            "over_limit_count": len(over_limit),
        },
        "flags": dict(Counter(
            flag if isinstance(flag, str) else flag.get("flag", "dict_flag")
            for row in rows for flag in row["flags"])),
        "coverage_fallback_rows": [
            {"row_id": row["id"], "catalog_id": row["catalog_id"]}
            for row in rows if "thought_coverage_fallback" in row["flags"]],
        "model_compact_checked": sum(
            1 for rec in records if rec.get("model_compact") is not None),
        "assets_sidecar": str(assets_path) if assets is not None else None,
        "v3_inputs_unchanged": True,
        "v3_input_sha256": v3_before,
        "usage": USAGE_NOTES,
        "notes": NOTES,
    }
    (output_dir / REPORT_JSON).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n")

    lines = ["# SFT v4 — complete catalog assembly", "",
             f"- **{report['rows']} rows, one per catalog rocket "
             f"({report['catalog_rockets_included']}/{report['catalog_size']})**.",
             f"- Label modes: {report['label_modes']}.",
             f"- Flight-label sources: {report['flight_label_sources']}.",
             f"- Upstream flight simulation calls: {flight_simulations_run} "
             f"(assembler calls: 0).",
             f"- Saved-simulation status: {report['simulation_status']}."]
    lines += ["", "## Splits (disjoint slices of the main file)", ""]
    for split, stats in report["splits"].items():
        lines.append(f"- {split}: {stats['rows']} rows / {stats['groups']} "
                      f"families -> {stats['file']}")
    lines += ["", "## Use", ""]
    lines += [f"- {note}" for note in USAGE_NOTES]
    lines += ["", "## Honesty and limits", ""]
    lines += [f"- {note}" for note in NOTES]
    lines += [
        "", "## Tokens", "",
        f"- Full-conversation tokens: min {report['tokens']['min']}, "
        f"median {report['tokens']['median']}, max {report['tokens']['max']}; "
        f"{len(over_limit)} row(s) over the {token_limit} limit, kept "
        f"complete with the context_over_limit flag.",
        "", "Files: sft_v4.jsonl (main), sft_train_v4.jsonl, sft_val_v4.jsonl, "
        "sft_test_v4.jsonl, sft_v4_motor_lookup.json"
        + (", sft_v4_assets.json" if assets is not None else "")
        + ", sft_v4_coverage.json, sft_v4_report.json.", "",
        "Every catalog id maps to its row in sft_v4_coverage.json. "
        "v3 files are byte-for-byte unchanged.", ""]
    (output_dir / REPORT_MD).write_text("\n".join(lines))

    summary = {key: report[key] for key in
               ("rows", "label_modes", "simulation_status", "splits", "tokens",
                "flags", "family_groups")}
    print(json.dumps(summary, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "new_results")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--token-limit", type=int, default=32768)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--exclude-file", type=Path, default=None,
                        help="JSON list of owner-approved catalog exclusions")
    args = parser.parse_args()
    assemble(args.sources, args.output_dir, args.catalog, args.token_limit,
             args.overwrite, seed=args.seed, exclude_file=args.exclude_file)


if __name__ == "__main__":
    main()
