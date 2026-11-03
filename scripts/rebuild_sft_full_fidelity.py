#!/usr/bin/env python3
"""Full-fidelity rebuild of new_results/sft_v2.jsonl (163 existing rows only).

Scope
-----
Rebuild every existing row of ``new_results/sft_v2.jsonl`` (the user's old,
incomplete training JSONL) from its ORIGINAL ``.ork`` source file and named
simulation, using the agreed extraction contract implemented by Cursor
Composer in ``scripts/sft_full_fidelity_extract.py``:

    extract_design(source_path, simulation_name, seed=42) ->
        {"design", "field_manifest", "provenance", "flight_metrics"}
    build_ork(design, destination) -> Path
    validate_roundtrip(source_path, simulation_name, design, destination,
                       seed=42) -> dict

The extractor is imported lazily (never at module import time) so this module
stays testable with a mocked extractor.

What each rebuilt row keeps / changes
-------------------------------------
Kept verbatim: id, file, source_prompt, sim, prompt_text, the system message,
the user message, split, and every other original top-level key and its order.
Changed: the assistant message (new <thought> + <design>), targets (refreshed
from the verified selected-source simulation metrics), ir_chars (length of the
actual serialized design JSON), and appended provenance/coverage metadata
under one new key ``full_fidelity``.

Safety model
------------
* The original input bytes are snapshotted (bytes + sha256) into the output
  dir before anything else.  An existing different snapshot is never
  overwritten; a rerun always reads the immutable snapshot, never its own
  output.
* The candidate JSONL is written separately and contains only rows that
  passed every gate, in original order.  ``--apply`` (the parent's job)
  replaces the input file only when ALL original rows passed, no --limit was
  used, and the input file is still byte-identical to the snapshot.
* Rows are never dropped silently and unresolved/insufficient evidence is
  reported as a blocking failure, never guessed into a success.

Full-fidelity acceptance per row
--------------------------------
* extractor result well-formed; design JSON-serializable without NaN/Infinity
* field_manifest covers every design leaf exactly once with standard JSON
  Pointer paths, terminal scalar values only, exact value equality, honest
  unit/purpose/basis, and no local-username/absolute-path leakage
* roundtrip acceptance requires ``pass`` AND ``input_pass`` AND
  ``metrics_pass`` AND ``metrics_comparison_baseline == "original_source"``
  (metrics gated directly against the original source, never against a
  saver-normalized baseline) AND empty ``input_errors``/``metric_errors`` AND
  per-key ``metric_diffs``: every required metric close, optional
  stability/deployment metrics marked ``unavailable_both`` when absent on both
  sides (never blocking, never fabricated), and a matching event sequence
* prompt-vs-config analysis: motor tokens and unit-bearing numeric claims in
  the unaltered prompt are compared against the selected source configuration
  and verified metrics; real conflicts block the row (the prompt is never
  rewritten here).  A known real case: row U-020 prompts a C11 motor while
  the selected original Simulation 1 uses C6 -- that row is reported and
  blocked rather than silently re-simulated or relabelled.
* <thought> is a mechanically validated, reverse-simulation-grounded
  explanation that covers every manifest field (path/value/unit/purpose/basis)
  and explicitly labels identity/display metadata and runtime audit data
  (component_index) as non-physics; parameter_tree is authoritative.

Size accounting (no silent spec dropping): per-row design/thought/content
character counts and dataset size statistics are reported so training
usability of very large designs (bt_55: ~52k chars, ~1.6k leaves) can be
assessed; every engineering spec is always kept.

Selected-model provenance (honest record, never claim the review passed):
    extractor author: Cursor Composer 2.5 (fastMode=false)
    builder model:    Factory Droid - GLM-5.3-Flash, reasoning_effort=max
    independent review: Cursor Grok4.7 final review PENDING

Exit codes: 0 ok, 1 row failures / apply refused, 2 usage error,
3 environment blocker (missing extractor, snapshot conflict, missing input).
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import json
import math
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# --------------------------------------------------------------------------
# constants
# --------------------------------------------------------------------------

EXTRACT_MODULE = "scripts.sft_full_fidelity_extract"

DEFAULT_INPUT_REL = "new_results/sft_v2.jsonl"
DEFAULT_OUTPUT_DIR_REL = "sftgen/out/scratch/sft_full_fidelity_20261102"
DEFAULT_SEED = 42
EXPECTED_ROWS = 163  # informational only; never enforced by dropping rows
EXPECTED_UNIQUE_FILES = 79  # parent preflight: sft_full_fidelity_source_batch_20261102
EXPECTED_UNIQUE_PAIRS = 146  # unique (file, simulation) configurations in scope

# Target keys of the existing dataset (verify_sft_v2 parity).  These are also
# the metrics this rebuild requires to be finite in flight_metrics: each one
# becomes a refreshed target, so None/unavailable here cannot become a target.
TARGET_KEYS = ["apogee_m", "max_velocity_ms", "max_mach", "time_to_apogee_s",
               "flight_time_s", "ground_hit_ms", "wind_ms"]
REQUIRED_METRICS = TARGET_KEYS
# Extractor-optional metrics (sft_full_fidelity_support.compare): unavailable
# on both sides is acceptable and is reported, never fabricated.
OPTIONAL_METRICS = ["max_accel_ms2", "deployment_velocity_ms", "stability_cal"]
REQUIRED_EVENTS = ["LIFTOFF", "APOGEE", "GROUND_HIT"]
RECOVERY_EVENT = "RECOVERY_DEVICE_DEPLOYMENT"
RECOVERY_PATH_TOKENS = ("parachute", "streamer")

ROW_METADATA_KEY = "full_fidelity"
SCHEMA_ID = "sft_full_fidelity_v1"
REQUIRED_METRICS_BASELINE = "original_source"
APPROVED_MOTOR_LABEL_IDS = {"U-020", "U-268", "U-269"}

BUILDER_PROVENANCE = {
    "builder": "scripts/rebuild_sft_full_fidelity.py",
    "builder_model": "Factory Droid - GLM-5.3-Flash",
    "builder_reasoning_effort": "max",
    "extractor_model": "Cursor Composer 2.5 (fastMode=false)",
    "extractor_module": EXTRACT_MODULE,
    "independent_review": "Cursor Grok4.7 final review PENDING (not performed)",
}

MANIFEST_ENTRY_KEYS = {"path", "value", "unit", "purpose", "basis"}
CLASS_EXPLICIT_KEYS = ("class", "classification", "kind", "category")

# identity / display metadata: not physics; explicitly labelled in the narrative
IDENTITY_TOKENS = {"name", "id", "uuid", "guid", "text", "comment", "description",
                   "title", "label", "color", "colour", "preset", "reference",
                   "notes", "note", "summary", "info"}
# runtime-derived audit data (never authoritative geometry)
AUDIT_TOKENS = ("component_index",)

METRIC_TOLERANCE = dict(rel_tol=1e-9, abs_tol=1e-12)


class RebuildError(Exception):
    """Fatal, non-row-specific blocker."""


class ExtractorUnavailable(RebuildError):
    """The agreed Composer extractor module could not be imported."""


class RowFailure(Exception):
    """A per-row blocking failure; args[0] is the list of reasons."""


# --------------------------------------------------------------------------
# small utilities
# --------------------------------------------------------------------------

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def slug(s: str, limit: int = 80) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", s)[:limit] or "x"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _reject_constant(name):  # JSON NaN / Infinity literals
    raise ValueError(f"non-finite JSON literal {name!r} in input")


def json_loads_strict(text: str):
    return json.loads(text, parse_constant=_reject_constant)


def json_dump_strict(obj, sort_keys: bool = False) -> str:
    return json.dumps(obj, ensure_ascii=False, allow_nan=False, sort_keys=sort_keys)


def values_equal(a, b) -> bool:
    """Exact value equality that keeps JSON types apart (true != 1, 1 != 1.0)."""
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return (isinstance(a, int) == isinstance(b, int)) and a == b
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(values_equal(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(values_equal(x, y) for x, y in zip(a, b))
    return a == b


def metrics_equal(a, b) -> bool:
    if a is None or b is None:
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) \
            and not isinstance(a, bool) and not isinstance(b, bool):
        return math.isclose(float(a), float(b), **METRIC_TOLERANCE)
    return a == b


def is_finite_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


# ---- JSON Pointers (RFC 6901) --------------------------------------------

def _escape_token(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


def _unescape_token(token: str) -> str:
    return token.replace("~1", "/").replace("~0", "~")


def resolve_pointer(doc, pointer: str):
    if pointer == "":
        return doc
    if not pointer.startswith("/"):
        raise KeyError(f"not an absolute JSON Pointer: {pointer!r}")
    cur = doc
    for raw in pointer.split("/")[1:]:
        token = _unescape_token(raw)
        if isinstance(cur, dict):
            if token not in cur:
                raise KeyError(f"pointer {pointer!r}: missing key {token!r}")
            cur = cur[token]
        elif isinstance(cur, list):
            if not re.fullmatch(r"0|[1-9][0-9]*", token):
                raise KeyError(f"pointer {pointer!r}: bad array index {token!r}")
            idx = int(token)
            if idx >= len(cur):
                raise KeyError(f"pointer {pointer!r}: index {idx} out of range")
            cur = cur[idx]
        else:
            raise KeyError(f"pointer {pointer!r}: cannot descend into scalar")
    return cur


def design_leaves(design) -> dict:
    """Every terminal scalar leaf of the design, keyed by its JSON Pointer.

    Matches the extractor's iter_design_pointers semantics: empty containers
    produce no leaves; dict keys and list indices are pointer-escaped.
    """
    leaves: dict[str, object] = {}

    def walk(node, ptr):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, ptr + "/" + _escape_token(str(k)))
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, ptr + f"/{i}")
        else:
            leaves[ptr] = node

    walk(design, "")
    return leaves


# --------------------------------------------------------------------------
# leakage control (no local usernames / absolute paths in training content)
# --------------------------------------------------------------------------

LEAK_PATTERNS = ("/Users/", "/home/", "C:\\Users\\", "\\Users\\")


def sanitize_path_string(s: str, repo: Path, workspace, home) -> tuple[str, bool]:
    """Redact known absolute prefixes to repo-relative / tagged forms."""
    changed = False
    if s.startswith(str(repo)):
        s = "<repo>" + s[len(str(repo)):]
        changed = True
    if workspace and s.startswith(str(workspace)):
        s = "<workspace>" + s[len(str(workspace)):]
        changed = True
    if home and s.startswith(home):
        s = "~" + s[len(home):]
        changed = True
    if s.startswith("/tmp/"):
        s = "<tmp>" + s[len("/tmp"):]
        changed = True
    return s, changed


def training_string_ok(s: str) -> bool:
    return not any(p in s for p in LEAK_PATTERNS)


def sanitize_provenance(obj, repo: Path, workspace, home):
    """Recursively redact absolute paths inside extractor provenance metadata."""
    if isinstance(obj, dict):
        return {k: sanitize_provenance(v, repo, workspace, home) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_provenance(v, repo, workspace, home) for v in obj]
    if isinstance(obj, str):
        out, _ = sanitize_path_string(obj, repo, workspace, home)
        return out
    return obj


# --------------------------------------------------------------------------
# field manifest validation and classification
# --------------------------------------------------------------------------

def classify_entry(entry: dict, pointer: str) -> str:
    for key in CLASS_EXPLICIT_KEYS:
        if key in entry and isinstance(entry[key], str) and entry[key].strip():
            return re.sub(r"[^A-Za-z0-9]+", "_", entry[key].strip().lower()).strip("_")
    last = pointer.rsplit("/", 1)[-1].lower()
    if any(tok in pointer.lower() for tok in AUDIT_TOKENS):
        return "runtime_audit"
    if last in IDENTITY_TOKENS or last.endswith("_id") or last.endswith("_uuid") \
            or last.endswith("_name") or last.endswith("_text"):
        return "identity_display"
    return "physics_input"


def validate_manifest(manifest, design, repo: Path, workspace, home):
    """Validate the extractor's field_manifest against the design.

    Returns (entries, class_counts, sanitized_notes).  Raises RowFailure on any
    contract violation, including object-valued (incomplete) manifest entries.
    """
    problems = []
    if not isinstance(manifest, list) or not manifest:
        raise RowFailure(["field_manifest must be a non-empty list"])
    leaves = design_leaves(design)
    entries = []
    seen = {}
    sanitized_notes = []
    for i, entry in enumerate(manifest):
        if not isinstance(entry, dict):
            problems.append(f"manifest[{i}]: not an object")
            continue
        missing = MANIFEST_ENTRY_KEYS - set(entry)
        if missing:
            problems.append(f"manifest[{i}]: missing keys {sorted(missing)}")
            continue
        ptr = entry["path"]
        if not isinstance(ptr, str) or not ptr.startswith("/"):
            problems.append(f"manifest[{i}].path: not an absolute JSON Pointer: {ptr!r}")
            continue
        if ptr in seen:
            problems.append(f"manifest[{i}]: duplicate path {ptr!r} (first at index {seen[ptr]})")
            continue
        try:
            leaf = resolve_pointer(design, ptr)
        except KeyError as exc:
            problems.append(f"manifest[{i}]: path does not resolve into design: {exc}")
            continue
        value = entry["value"]
        if isinstance(value, (dict, list)):
            problems.append(
                f"manifest[{i}] ({ptr}): value is {type(value).__name__}; the contract "
                "requires terminal scalar values only (reject object-valued manifests)")
            continue
        if not values_equal(value, leaf):
            problems.append(
                f"manifest[{i}] ({ptr}): value {value!r} != design leaf {leaf!r}")
            continue
        unit, purpose, basis = entry["unit"], entry["purpose"], entry["basis"]
        if not isinstance(unit, str) or not unit.strip():
            problems.append(f"manifest[{i}] ({ptr}): unit must be a non-empty string")
            continue
        if not isinstance(purpose, str) or not purpose.strip():
            problems.append(f"manifest[{i}] ({ptr}): purpose must be a non-empty string")
            continue
        if not isinstance(basis, str) or not basis.strip():
            problems.append(f"manifest[{i}] ({ptr}): basis must be a non-empty string")
            continue
        redactions = []
        clean = []
        for label, s in (("unit", unit), ("purpose", purpose), ("basis", basis)):
            s2, changed = sanitize_path_string(s, repo, workspace, home)
            if changed:
                redactions.append(label)
            if not training_string_ok(s2):
                problems.append(
                    f"manifest[{i}] ({ptr}): {label} leaks an absolute/local path: {s!r}")
            clean.append(s2)
        unit, purpose, basis = clean
        if redactions:
            sanitized_notes.append({"path": ptr, "fields": redactions})
        seen[ptr] = i
        entries.append({
            "path": ptr, "value": leaf, "unit": unit, "purpose": purpose,
            "basis": basis, "class": classify_entry(entry, ptr),
        })

    manifest_paths = {e["path"] for e in entries}
    missing_ptrs = sorted(set(leaves) - manifest_paths)
    extra = sorted(manifest_paths - set(leaves))
    for ptr in missing_ptrs:
        problems.append(f"manifest does not cover design leaf {ptr!r}")
    for ptr in extra:
        problems.append(f"manifest path {ptr!r} is not a design leaf (extra)")
    if problems:
        raise RowFailure(problems)
    class_counts: dict[str, int] = {}
    for e in entries:
        class_counts[e["class"]] = class_counts.get(e["class"], 0) + 1
    return entries, class_counts, sanitized_notes


# --------------------------------------------------------------------------
# flight metrics / events / options acceptance
# --------------------------------------------------------------------------

def event_types(events) -> list:
    out = []
    for e in events or []:
        if isinstance(e, str):
            t = e
        elif isinstance(e, dict):
            t = e.get("type") or e.get("event") or ""
        else:
            t = str(e)
        if t and t not in out:
            out.append(t)
    return out


def design_has_recovery(manifest_entries) -> bool:
    if not manifest_entries:
        return False
    for e in manifest_entries:
        hay = (str(e.get("path", "")) + " " + str(e.get("value", ""))).lower()
        if any(tok in hay for tok in RECOVERY_PATH_TOKENS):
            return True
    return False


def accept_roundtrip(rt, extract, manifest_entries):
    """Full-fidelity roundtrip acceptance against the current Composer contract.

    Requires ``pass`` AND ``input_pass`` AND ``metrics_pass`` AND
    ``metrics_comparison_baseline == "original_source"`` (a saver-normalized
    baseline must never conceal materialization drift) AND empty
    ``input_errors``/``metric_errors`` AND concrete per-key ``metric_diffs``
    evidence: every required metric close, optional metrics either matching or
    explicitly ``unavailable_both``, and a matching event sequence.

    Returns (ok, problems, notes, unavailable_metrics).
    """
    problems, notes, unavailable = [], [], []
    if not isinstance(rt, dict):
        return False, ["roundtrip result is not a dict"], [], []
    src_metrics = extract.get("flight_metrics") if isinstance(extract, dict) else None
    if not isinstance(src_metrics, dict) or not src_metrics:
        return False, ["extract flight_metrics missing or empty"], [], []

    for flag in ("pass", "input_pass", "metrics_pass"):
        v = rt.get(flag)
        if v is None:
            problems.append(f"roundtrip result missing {flag!r} flag: contract "
                            "insufficient evidence, refusing to assume")
        elif v is not True:
            problems.append(f"roundtrip {flag} is False")
    baseline = rt.get("metrics_comparison_baseline")
    if baseline is None:
        problems.append("roundtrip result missing metrics_comparison_baseline; cannot confirm "
                        "metrics were gated against the original source")
    elif baseline != REQUIRED_METRICS_BASELINE:
        problems.append(f"roundtrip metrics gated against {baseline!r}, not "
                        f"{REQUIRED_METRICS_BASELINE!r}; a normalized baseline must never "
                        "replace the original source as ground truth")
    for errkey in ("input_errors", "metric_errors"):
        errs = rt.get(errkey)
        if errs is None:
            problems.append(f"roundtrip result missing {errkey!r}: contract insufficient "
                            "evidence, refusing to assume")
        elif errs:
            problems.extend(f"{errkey}: {e}" for e in list(errs)[:10])

    diffs = rt.get("metric_diffs")
    if not isinstance(diffs, dict):
        problems.append("roundtrip result missing metric_diffs: contract insufficient "
                        "evidence, refusing to assume")
    else:
        for k in REQUIRED_METRICS:
            row = diffs.get(k)
            if not isinstance(row, dict):
                problems.append(f"metric_diffs missing required metric {k!r}")
            elif not row.get("close"):
                problems.append(f"required metric {k} does not match the original source: {row!r}")
        for k in OPTIONAL_METRICS:
            row = diffs.get(k)
            if not isinstance(row, dict):
                continue
            if row.get("status") == "unavailable_both" or (row.get("close") and
                                                           row.get("source") is None and
                                                           row.get("rebuilt") is None):
                unavailable.append(k)
            elif row.get("status") == "availability_mismatch":
                problems.append(f"optional metric {k}: availability mismatch between the "
                                f"original source and the rebuild: {row!r}")
            elif not row.get("close"):
                notes.append(f"optional metric {k} diverges between source and rebuild "
                             f"(informational, not gated): {row!r}")
        ev = diffs.get("events")
        if not isinstance(ev, dict):
            problems.append("metric_diffs missing the events comparison: contract "
                            "insufficient evidence, refusing to assume")
        elif not ev.get("close"):
            problems.append(f"roundtrip event sequence does not match the original source: {ev!r}")

    src_events = event_types(src_metrics.get("events"))
    needs_recovery = design_has_recovery(manifest_entries)
    for ev_name in REQUIRED_EVENTS + ([RECOVERY_EVENT] if needs_recovery else []):
        if ev_name not in src_events:
            problems.append(f"selected source simulation events lack {ev_name}")

    return (not problems), problems, notes, sorted(set(unavailable))


# --------------------------------------------------------------------------
# prompt-vs-config analysis (existing prompts stay unaltered)
# --------------------------------------------------------------------------

MOTOR_TOKEN_RE = re.compile(
    r"\b((?:1/[248])?[A-Z][0-9]{1,4}(?:\.[0-9]+)?"
    r"(?:[A-Za-z]+(?:/[A-Za-z]+)?)?(?:-[0-9]{1,2})?)\b"
)

UNIT_SPECS = [  # (unit text, kind, SI factor); longest first
    ("m/s²", "acceleration", 1.0), ("m/s^2", "acceleration", 1.0),
    ("m/s2", "acceleration", 1.0),
    ("m/s", "speed", 1.0), ("km/h", "speed", 0.277778), ("mph", "speed", 0.44704),
    ("ft/s", "speed", 0.3048), ("fps", "speed", 0.3048),
    ("seconds", "time", 1.0), ("second", "time", 1.0), ("secs", "time", 1.0),
    ("sec", "time", 1.0), ("s", "time", 1.0),
    ("meters", "len", 1.0), ("metres", "len", 1.0), ("meter", "len", 1.0),
    ("metre", "len", 1.0), ("m", "len", 1.0), ("km", "len", 1000.0),
    ("mm", "len_small", 0.001), ("cm", "len_small", 0.01),
    ("feet", "len", 0.3048), ("foot", "len", 0.3048), ("ft", "len", 0.3048),
]
_UNIT_ALT = "|".join(re.escape(u) for u, _, _ in UNIT_SPECS)
_CLAIM_RE = re.compile(
    r"(?P<pre>[^\d]{0,34}?)(?P<num>\d[\d,]*(?:\.\d+)?)\s*(?P<unit>" + _UNIT_ALT + r")(?![\w/^²³])",
    re.IGNORECASE)
COST_RE = re.compile(r"\$\s?(\d[\d,]*(?:\.\d+)?)")
UPPER_RE = re.compile(r"(?:under|within|less than|no more than|at most|below|"
                      r"max(?:imum)?|no longer than|no higher than|<=|≤)\s*$", re.IGNORECASE)
LOWER_RE = re.compile(r"(?:at least|more than|over|above|min(?:imum)?|>=|≥)\s*$", re.IGNORECASE)
ABOUT_RE = re.compile(r"(?:about|approx(?:imately)?|roughly|around|near|~|≈)\s*$", re.IGNORECASE)
TIME_FLIGHT_HINT = re.compile(r"flight|total|land|descent|touchdown|ground", re.IGNORECASE)
TIME_APOGEE_HINT = re.compile(r"apogee|apex|peak", re.IGNORECASE)
SPEED_DEPLOY_HINT = re.compile(r"deploy|eject|opening", re.IGNORECASE)
SPEED_GROUND_HINT = re.compile(
    r"touchdown|touch(?:es|ing)?\s+down|comes?\s+down|coming\s+down|"
    r"land|descent|ground|impact|sink", re.IGNORECASE
)
SPEED_MAX_HINT = re.compile(r"peak|max|velocity|apogee|top", re.IGNORECASE)


def design_motor_values(manifest_entries) -> list:
    """String values from manifest paths that look like motor designations."""
    out = []
    for e in manifest_entries:
        if isinstance(e["value"], str) and \
                e["path"].lower().endswith(("/designation", "/common_name")):
            if e["value"] not in out:
                out.append(e["value"])
    return out


def prompt_motor_tokens(prompt_text: str) -> list:
    return MOTOR_TOKEN_RE.findall(prompt_text)


def _motor_core(designation: str) -> str:
    match = re.search(r"(?:1/[248])?[A-Z]\d+(?:\.\d+)?", designation.upper())
    return match.group(0) if match else designation.upper()


def _match_eq(claim_si: float, candidates: list, about: bool,
              rounding_tolerance: float = 0.0) -> bool:
    for m in candidates:
        if not is_finite_number(m) or m <= 0:
            continue
        rel = abs(claim_si - m) / abs(m)
        if rel <= (0.05 if about else 0.03) or (
                about and abs(claim_si - m) <= rounding_tolerance):
            return True
    return False


def analyze_prompt(prompt_text: str, manifest_entries, metrics: dict) -> dict:
    """Compare the unaltered prompt against the selected source configuration.

    The old reduced exporter wrote wrong motor text into some examples, and at
    least one real row (U-020) prompts C11 while the selected original
    simulation uses C6.  Conflicts are reported and block the row; prompts are
    never rewritten and no other simulation is silently chosen.
    """
    design_motors = design_motor_values(manifest_entries)
    design_bases = {_motor_core(d) for d in design_motors}
    motor_conflicts, claims, unverified = [], [], []

    prompt_motors = prompt_motor_tokens(prompt_text)
    for tok in prompt_motors:
        base = _motor_core(tok)
        if base not in design_bases and tok.upper() not in {d.upper() for d in design_motors}:
            motor_conflicts.append(tok)

    for m in COST_RE.finditer(prompt_text):
        unverified.append({"claim": m.group(0),
                           "why": "budget/cost has no simulation metric"})
    for m in _CLAIM_RE.finditer(prompt_text):
        pre, num, unit = m.group("pre"), m.group("num"), m.group("unit").lower()
        try:
            value = float(num.replace(",", ""))
        except ValueError:
            continue
        kind, factor = next((k, f) for u, k, f in UNIT_SPECS if u.lower() == unit)
        si = value * factor
        about = bool(ABOUT_RE.search(pre))
        upper = bool(UPPER_RE.search(pre))
        lower = bool(LOWER_RE.search(pre))
        if kind == "acceleration":
            targets = ["max_accel_ms2"]
        elif kind == "time":
            if TIME_FLIGHT_HINT.search(pre):
                targets = ["flight_time_s"]
            elif TIME_APOGEE_HINT.search(pre):
                targets = ["time_to_apogee_s"]
            else:
                targets = ["time_to_apogee_s", "flight_time_s"]
        elif kind == "speed":
            if SPEED_DEPLOY_HINT.search(pre):
                targets = ["deployment_velocity_ms"]
            elif SPEED_GROUND_HINT.search(pre):
                targets = ["ground_hit_ms"]
            elif SPEED_MAX_HINT.search(pre):
                targets = ["max_velocity_ms"]
            else:
                targets = ["max_velocity_ms", "ground_hit_ms"]
        elif kind == "len_small":
            # airframe dimensions (mm/cm) are not flight metrics
            unverified.append({"claim": m.group(0),
                               "why": "small length likely an airframe dimension; "
                                      "no geometry metric in flight results"})
            continue
        else:  # len
            if si < 10.0:  # sub-10 m is a physical dimension, not an apogee
                unverified.append({"claim": m.group(0),
                                   "why": "small length likely an airframe dimension; "
                                          "no geometry metric in flight results"})
                continue
            targets = ["apogee_m"]
        cands = [metrics.get(t) for t in targets if t in metrics]
        claim = {"claim": m.group(0), "kind": kind, "targets": targets,
                 "mode": "about" if about else ("upper" if upper else ("lower" if lower else "eq")),
                 "value_si": si}
        finite = [c for c in cands if is_finite_number(c)]
        if not finite:
            claims.append({**claim, "verdict": "unverified",
                           "detail": "no finite metric available to check against"})
            continue
        detail = "; ".join(f"{t}={metrics.get(t)!r}" for t in targets)
        if about or (not upper and not lower):
            # Approximate integer wording such as "around 3 m/s" represents
            # a rounded value, not an unsupported extra decimal of precision.
            digits = len(num.partition(".")[2])
            rounding = 0.5 * (10.0 ** -digits) * factor
            ok = _match_eq(si, finite, about, rounding)
            if about:
                claim["rounding_tolerance_si"] = rounding
        elif upper:
            ok = all(c <= si + 1e-9 for c in finite)
        else:
            ok = all(c >= si - 1e-9 for c in finite)
        claims.append({**claim, "verdict": "consistent" if ok else "conflict",
                       "detail": detail})

    conflicts = [f"prompt motor token {t!r} does not match any motor designation in the "
                 f"selected source design {design_motors!r}" for t in motor_conflicts]
    conflicts += [f"prompt claim {c['claim']!r} conflicts with verified metrics: {c['detail']}"
                  for c in claims if c["verdict"] == "conflict"]
    warnings = [f"prompt claim {c['claim']!r}: {c['detail']}"
                for c in claims if c["verdict"] == "unverified"]
    warnings += [f"prompt claim {u['claim']!r}: {u['why']}" for u in unverified]
    return {
        "prompt_motor_tokens": prompt_motors,
        "design_motor_values": design_motors,
        "motor_conflicts": motor_conflicts,
        "claims": claims,
        "conflicts": conflicts,
        "warnings": warnings,
        "unverified": unverified,
    }


# --------------------------------------------------------------------------
# <thought> rendering (reverse-simulation grounded, mechanically validated)
# --------------------------------------------------------------------------

def _field_line(entry: dict) -> str:
    payload = {"path": entry["path"], "value": entry["value"], "unit": entry["unit"],
               "purpose": entry["purpose"], "basis": entry["basis"], "class": entry["class"]}
    return "- " + json_dump_strict(payload)


def parse_thought_fields(thought: str) -> list:
    out = []
    for line in thought.splitlines():
        s = line.strip()
        if s.startswith("- {"):
            out.append(json.loads(s[2:]))
    return out


def validate_thought_coverage(thought: str, entries: list) -> list:
    """Mechanically re-parse the per-field lines and require exact equality."""
    problems = []
    parsed = parse_thought_fields(thought)
    by_path = {}
    for i, p in enumerate(parsed):
        if set(p) != {"path", "value", "unit", "purpose", "basis", "class"}:
            problems.append(f"thought field line {i}: wrong keys {sorted(p)}")
            continue
        if p["path"] in by_path:
            problems.append(f"thought field line {i}: duplicate path {p['path']!r}")
        by_path[p["path"]] = p
    if len(parsed) != len(entries):
        problems.append(f"thought field lines ({len(parsed)}) != manifest entries ({len(entries)})")
    for e in entries:
        p = by_path.get(e["path"])
        if p is None:
            problems.append(f"thought is missing field line for {e['path']!r}")
            continue
        if not values_equal(p["value"], e["value"]):
            problems.append(f"thought field {e['path']!r}: value {p['value']!r} != manifest {e['value']!r}")
        for k in ("unit", "purpose", "basis", "class"):
            if p[k] != e[k]:
                problems.append(f"thought field {e['path']!r}: {k} {p[k]!r} != manifest {e[k]!r}")
    extra = sorted(set(by_path) - {e["path"] for e in entries})
    for ptr in extra:
        problems.append(f"thought has field line for non-manifest path {ptr!r}")
    return problems


def render_thought(*, prompt_text: str, source_rel: str, source_sha: str, sim_name: str,
                   seed: int, entries: list, class_counts: dict, metrics: dict,
                   unavailable: list, analysis: dict) -> str:
    lines = []
    lines.append("<thought>")
    lines.append(
        f"SOURCE AND PROVENANCE: This answer is reverse-simulation grounded. The design JSON "
        f"below is the complete structured reconstruction of simulation {sim_name!r} "
        f"in source file {source_rel} (sha256 {source_sha[:16]}), recorded simulation seed "
        f"{seed}. Every value comes from that verified source; no design intent is invented "
        f"and no requirement is claimed as satisfied without a verified comparison.")
    lines.append("")
    lines.append("PROMPT CROSS-CHECK (the request stays as written; this is a factual "
                 "comparison, not a success claim):")
    lines.append(f"- request: {prompt_text!r}")
    lines.append(f"- motor tokens in prompt: {analysis['prompt_motor_tokens'] or 'none'}; "
                 f"motor designation value(s) in the selected source design: "
                 f"{analysis['design_motor_values'] or 'none'}"
                 + ("" if not analysis["motor_conflicts"]
                    else " -> MISMATCH between the prompt and the selected source "
                         "configuration, reported rather than resolved"))
    for c in analysis["claims"]:
        lines.append(f"- prompt claim {c['claim']!r} ({c['kind']}, {c['mode']}): checked against "
                     f"{c['targets']} -> {c['verdict']}; {c['detail']}")
    for u in analysis["unverified"]:
        lines.append(f"- prompt claim {u['claim']!r}: cannot be verified from recorded flight "
                     f"metrics ({u['why']}); it is not claimed as satisfied")
    if not analysis["conflicts"]:
        lines.append("- no numeric or motor conflict was found between the prompt and the "
                     "selected source simulation/configuration; this is a factual consistency "
                     "statement about the recorded data, not a blanket claim that every "
                     "requirement is met")
    lines.append("")
    lines.append("VERIFIED FLIGHT METRICS (selected source simulation; recorded outcomes of "
                 "simulating the SOURCE, not guarantees for rebuilt hardware):")
    for k in REQUIRED_METRICS + OPTIONAL_METRICS:
        if k in metrics:
            v = metrics[k]
            if v is None:
                lines.append(f"- {k}: unavailable in the extractor output (explicitly marked; "
                             "not used as a target)")
            else:
                lines.append(f"- {k} = {v!r}")
    for k, v in sorted(metrics.items()):
        if k in REQUIRED_METRICS or k in OPTIONAL_METRICS or k == "events":
            continue
        if k.endswith("_status") or k == "runtime_ms":
            continue
        lines.append(f"- {k} = {v!r} (informational)")
    lines.append(f"- events: {event_types(metrics.get('events'))}")
    if unavailable:
        lines.append(f"- unavailable optional metrics (absent on both the original source and "
                     f"the rebuild, so no target is claimed): {unavailable}")
    lines.append("")
    lines.append("COMPLETE DESIGN INPUTS: every field of the design JSON below, one line per "
                 "leaf (path, value, unit, engineering purpose, basis, classification). The "
                 "original parameter_tree is the authoritative geometry description; "
                 "simulation_options_snapshot records the selected simulation under the "
                 "pinned runtime; component_index entries are runtime-derived audit data "
                 "only - they record how the source file was indexed at runtime, and editing "
                 "an audit-only value would not change the reconstructed geometry.")
    groups: dict[str, list] = {}
    for e in entries:
        groups.setdefault("/" + e["path"].split("/")[1], []).append(e)
    for group, fields in groups.items():
        lines.append(f"GROUP {group} ({len(fields)} fields):")
        lines.extend(_field_line(e) for e in fields)
    lines.append("")
    ident = class_counts.get("identity", 0) + class_counts.get("identity_display", 0) + \
        class_counts.get("display", 0)
    audit = class_counts.get("audit_runtime", 0) + class_counts.get("runtime_audit", 0)
    lines.append(f"IDENTITY AND AUDIT DATA: {ident} field(s) are identity/display metadata "
                 f"(names, ids, UUIDs, presets, display text) and {audit} field(s) are "
                 f"runtime-derived audit data; neither kind is a physics input, and the "
                 f"per-field classification above says so explicitly rather than dressing "
                 f"them up as aerodynamics.")
    lines.append("RECONSTRUCTION NOTE: the design JSON block at the end is byte-for-byte the "
                 "validated reconstruction input; the per-field lines above are mechanically "
                 "checked against it (same paths, values, units, purposes, bases).")
    lines.append("</thought>")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# extractor loading (lazy; mock-friendly)
# --------------------------------------------------------------------------

def load_extractor(module_name: str = EXTRACT_MODULE):
    try:
        mod = importlib.import_module(module_name)
    except Exception as exc:  # ImportError and anything broken inside it
        raise ExtractorUnavailable(
            f"cannot import agreed extractor {module_name!r}: {exc.__class__.__name__}: {exc}; "
            "no data invented, run blocked") from exc
    for name in ("extract_design", "build_ork", "validate_roundtrip"):
        if not callable(getattr(mod, name, None)):
            raise ExtractorUnavailable(
                f"extractor {module_name!r} is missing callable {name!r}: contract insufficient")
    return mod


def extractor_fingerprint(mod) -> str:
    f = getattr(mod, "__file__", None)
    if f and Path(f).is_file():
        path = Path(f)
        files = [path]
        support = path.parent / "sft_full_fidelity_support"
        if support.is_dir():
            files.extend(sorted(support.glob("*.py")))
        for dependency in (path.parent / "or_headless.py",
                           path.parent / "or_batch" / "OrBatch.java",
                           path.parent.parent / "lib" / "OpenRocket.jar"):
            if dependency.is_file():
                files.append(dependency)
        hashes = [(p.name, sha256_file(p)) for p in files]
        return sha256_bytes(json_dump_strict(hashes, sort_keys=True).encode())
    parts = sorted(n for n in dir(mod) if not n.startswith("__"))
    for vkey in ("__version__", "extractor_version", "fake_version"):
        v = getattr(mod, vkey, None)
        if isinstance(v, str):
            parts.append(f"{vkey}={v}")
    return sha256_bytes(json_dump_strict(parts, sort_keys=True).encode())


# --------------------------------------------------------------------------
# source resolution (no guessing; ambiguities block)
# --------------------------------------------------------------------------

def ork_contains_simulation(path: Path, sim_name: str) -> bool:
    try:
        with zipfile.ZipFile(path) as zf:
            xml = zf.read("rocket.ork").decode("utf-8", "replace")
        root = ET.fromstring(xml)
        return any((s.findtext("name") or "") == sim_name for s in root.iter("simulation"))
    except Exception:
        return False


def resolve_source(rel: str, sim_name: str, repo: Path, workspace) -> tuple:
    """Return (path, strategy). Repository first; workspace only if the same
    intended source is verifiable (named simulation present). Ambiguity blocks."""
    p = Path(rel)
    if p.is_absolute():
        for base, tag in ((repo, "repository"), (workspace, "workspace")):
            if base and base in p.parents:
                rp = p.relative_to(base)
                if (base / rp).is_file():
                    return base / rp, f"{tag}:{rp}"
        raise RowFailure([f"row file {rel!r} is absolute and not inside the repository "
                          f"or workspace; refusing to guess"])
    repo_path = repo / rel
    if repo_path.is_file():
        return repo_path, "repository"
    if workspace is not None:
        ws_path = workspace / rel
        if ws_path.is_file():
            if ork_contains_simulation(ws_path, sim_name):
                return ws_path, "workspace (verified: contains the named simulation)"
            raise RowFailure([f"row file {rel!r} not in repository; workspace candidate "
                               f"{ws_path} does not contain simulation {sim_name!r}; blocking "
                               f"rather than guessing the source"])
        raise RowFailure([f"row file {rel!r} not found in repository ({repo_path}) nor "
                           f"workspace ({ws_path})"])
    raise RowFailure([f"row file {rel!r} not found in repository ({repo_path}); "
                       f"no workspace fallback configured"])


# --------------------------------------------------------------------------
# per-row rebuild
# --------------------------------------------------------------------------

def _structure_problems(row) -> list:
    problems = []
    if not isinstance(row, dict):
        return ["row is not a JSON object"]
    for key in ("id", "file", "sim", "prompt_text", "messages", "targets", "split"):
        if key not in row:
            problems.append(f"row missing key {key!r}")
    if "targets" in row and not isinstance(row["targets"], dict):
        problems.append("targets must be an object")
    msgs = row.get("messages")
    if not isinstance(msgs, list) or [m.get("role") for m in msgs if isinstance(m, dict)] \
            != ["system", "user", "assistant"]:
        problems.append("messages must be [system, user, assistant]")
    return problems


def validate_metrics(metrics: dict) -> tuple:
    """Return (problems, unavailable). Required metrics must be finite; optional
    ones may be None (explicitly unavailable) but never non-finite."""
    problems, unavailable = [], []
    if not isinstance(metrics, dict) or not metrics:
        return ["extract flight_metrics missing or empty"], []
    for k in REQUIRED_METRICS:
        if k not in metrics:
            problems.append(f"required metric {k} missing from flight_metrics")
        elif not is_finite_number(metrics[k]):
            problems.append(f"required metric {k}={metrics[k]!r} is not a finite number")
        elif k == "wind_ms":
            if metrics[k] < 0:
                problems.append(f"metric wind_ms={metrics[k]!r} is negative")
        elif metrics[k] <= 0:
            problems.append(f"required metric {k}={metrics[k]!r} is not positive")
    for k in OPTIONAL_METRICS:
        if k in metrics:
            if metrics[k] is None:
                unavailable.append(k)
            elif not is_finite_number(metrics[k]):
                problems.append(f"optional metric {k}={metrics[k]!r} is present but non-finite")
    return problems, unavailable


def rebuild_row(row, extract, rt, seed: int, repo: Path, workspace,
                source_rel: str, source_sha: str, report_entry=None):
    """Rebuild one row. Returns (new_row, report_entry).

    Raises RowFailure with a list of blocking reasons; report_entry (when
    given) receives partial analysis details even when the row fails.
    """
    info: dict = {"reasons": [], "warnings": []}
    source_rel_repo = source_rel

    def publish(*keys):
        if report_entry is not None:
            for k in keys:
                if k in info:
                    report_entry[k] = info[k]

    def fail(*extra_reasons):
        publish("warnings", "roundtrip", "sizes")
        raise RowFailure(info["reasons"] + list(extra_reasons))
    struct = _structure_problems(row)
    if struct:
        raise RowFailure(struct)

    # ---- extractor result sanity + metric finiteness ----
    metrics = extract.get("flight_metrics")
    m_problems, unavailable = validate_metrics(metrics)
    info["reasons"] += m_problems

    design = extract.get("design")
    if not isinstance(design, dict):
        info["reasons"].append("extract design is not a JSON object")
        fail()
    try:
        design_json = json_dump_strict(design, sort_keys=True)  # canonical: cache-stable
    except ValueError as exc:
        info["reasons"].append(f"design is not finite/serializable JSON: {exc}")
        fail()

    # ---- manifest contract ----
    manifest = extract.get("field_manifest")
    try:
        entries, class_counts, sanitized = validate_manifest(manifest, design, repo, workspace,
                                                             os.path.expanduser("~"))
    except RowFailure as exc:
        info["reasons"] += exc.args[0]
        fail()
    info["manifest"] = {"leaves": len(design_leaves(design)), "entries": len(entries),
                        "class_counts": class_counts, "sanitized": sanitized}
    publish("manifest")
    if sanitized:
        info["warnings"].append(f"redacted absolute paths in manifest strings: {sanitized}")

    prov = extract.get("provenance")
    prov_clean = sanitize_provenance(prov if isinstance(prov, dict) else {"raw": prov},
                                     repo, workspace, os.path.expanduser("~"))

    # ---- prompt-vs-config analysis ----
    analysis = analyze_prompt(row["prompt_text"], entries, metrics)
    info["prompt"] = {k: analysis[k] for k in ("prompt_motor_tokens", "design_motor_values",
                                               "motor_conflicts", "claims", "unverified")}
    publish("prompt")
    info["reasons"] += analysis["conflicts"]
    info["warnings"] += analysis["warnings"]

    if info["reasons"]:
        fail()

    # ---- full-fidelity roundtrip acceptance ----
    ok, rt_problems, rt_notes, rt_unavailable = accept_roundtrip(rt, extract, entries)
    info["roundtrip"] = {"accepted": ok, "problems": rt_problems, "notes": rt_notes}
    publish("roundtrip")
    info["warnings"] += rt_notes
    unavailable = sorted(set(unavailable) | set(rt_unavailable))
    if not ok:
        info["reasons"] += rt_problems
        fail()

    # ---- thought + design ----
    thought = render_thought(prompt_text=row["prompt_text"],
                             source_rel=source_rel_repo, source_sha=source_sha,
                             sim_name=row["sim"], seed=seed, entries=entries,
                             class_counts=class_counts, metrics=metrics,
                             unavailable=unavailable, analysis=analysis)
    coverage = validate_thought_coverage(thought, entries)
    if coverage:
        info["reasons"] += [f"thought coverage: {p}" for p in coverage]
        fail()

    content = thought + "\n<design>" + design_json + "</design>"
    info["sizes"] = {"design_chars": len(design_json), "thought_chars": len(thought),
                     "content_chars": len(content)}

    # ---- final content self-checks ----
    if content.count("<thought>") != 1 or content.count("</thought>") != 1 \
            or content.count("<design>") != 1 or content.count("</design>") != 1:
        info["reasons"].append("content does not contain exactly one <thought>/<design> "
                               "wrapper pair")
        fail()
    try:
        parsed_design = json_loads_strict(
            content.split("<design>", 1)[1].rsplit("</design>", 1)[0])
    except ValueError as exc:
        info["reasons"].append(f"emitted <design> JSON does not parse strictly: {exc}")
        fail()
    if parsed_design != design or \
            json_dump_strict(parsed_design, sort_keys=True) != json_dump_strict(design,
                                                                                sort_keys=True):
        info["reasons"].append("emitted <design> JSON is not exactly the extractor design")
        fail()

    # ---- assemble the new row, preserving original key order and metadata ----
    new_row = {}
    for key in row:  # keep the original key order exactly
        if key == "messages":
            new_row[key] = [dict(row["messages"][0]), dict(row["messages"][1]),
                            {"role": "assistant", "content": content}]
        elif key == "targets":
            new_row[key] = {k: metrics[k] for k in TARGET_KEYS}
        elif key == "ir_chars":
            new_row[key] = len(design_json)
        else:
            new_row[key] = row[key]
    new_row[ROW_METADATA_KEY] = {
        "schema": SCHEMA_ID,
        "source": {"file_repo_rel": row["file"], "simulation": row["sim"], "seed": seed,
                   "sha256": source_sha},
        "extractor_provenance": prov_clean,
        "roundtrip": {"input_pass": rt.get("input_pass", rt.get("pass")),
                      "metrics_pass": rt.get("metrics_pass"),
                      "metrics_comparison_baseline": rt.get("metrics_comparison_baseline"),
                      "accepted": ok, "unavailable_metrics": unavailable},
        "coverage": {"design_leaves": len(design_leaves(design)),
                     "manifest_entries": len(entries),
                     "thought_field_lines": len(parse_thought_fields(thought)),
                     "class_counts": class_counts, "unavailable_metrics": unavailable,
                     "prompt_conflicts": analysis["conflicts"],
                     "prompt_warnings": analysis["warnings"]},
        "generator": {
            "builder": BUILDER_PROVENANCE["builder"],
            "builder_model": BUILDER_PROVENANCE["builder_model"],
            "builder_reasoning_effort": BUILDER_PROVENANCE["builder_reasoning_effort"],
            "extractor_model": BUILDER_PROVENANCE["extractor_model"],
            "independent_review": BUILDER_PROVENANCE["independent_review"],
        },
    }
    try:
        leak_scan = json_dump_strict(new_row)
    except ValueError as exc:
        info["reasons"].append(f"rebuilt row is not finite/serializable JSON: {exc}")
        fail()
    if not training_string_ok(leak_scan):
        info["reasons"].append("rebuilt row would leak an absolute/local path; blocked")
        fail()
    return new_row, info


# --------------------------------------------------------------------------
# snapshot, cache, candidate, report, apply
# --------------------------------------------------------------------------

def snapshot_original(input_path: Path, output_dir: Path, repo: Path) -> tuple:
    """Create-or-verify the immutable original snapshot inside output_dir.

    Returns (snapshot_path, snapshot_bytes, created_bool).
    Never overwrites an existing different backup.
    """
    snap_dir = output_dir / "original_snapshot"
    snap_path = snap_dir / ("original__" + input_path.name)
    manifest_path = snap_dir / "snapshot.json"
    input_bytes = input_path.read_bytes()
    input_sha = sha256_bytes(input_bytes)
    if snap_path.exists():
        existing = snap_path.read_bytes()
        if sha256_bytes(existing) != input_sha:
            raise RebuildError(
                f"existing snapshot {snap_path} differs from the current input {input_path} "
                f"({sha256_bytes(existing)[:12]} != {input_sha[:12]}); refusing to overwrite a "
                f"different backup - use a fresh --output-dir")
        return snap_path, existing, False
    snap_dir.mkdir(parents=True, exist_ok=True)
    snap_path.write_bytes(input_bytes)
    manifest_path.write_text(json_dump_strict({
        "original_input_repo_rel": str(input_path.relative_to(repo))
        if input_path.is_relative_to(repo) else str(input_path),
        "sha256": input_sha, "bytes": len(input_bytes),
        "snapshot_sha256": sha256_bytes(snap_path.read_bytes()),
        "created_at": now_iso(),
        "note": "immutable original snapshot; reruns must read this, never their own output",
    }, sort_keys=True) + "\n")
    return snap_path, input_bytes, True


class Cache:
    """Cache extract+roundtrip by file+simulation+seed+source-hash+extractor-sha."""

    def __init__(self, directory: Path):
        self.dir = directory
        self.dir.mkdir(parents=True, exist_ok=True)
        self.hits = 0

    def _path(self, key: dict) -> Path:
        raw = (f"{key['file_rel']}::{key['sim']}::{key['seed']}::{key['source_sha256']}"
               f"::{key['extractor_sha']}")
        return self.dir / (slug(raw, 160) + ".json")

    def load(self, key: dict):
        p = self._path(key)
        if not p.exists():
            return None
        try:
            entry = json_loads_strict(p.read_text())
            if entry.get("key") != key:
                return None
            extract, rt = entry.get("extract"), entry.get("roundtrip")
            if not isinstance(extract, dict) or not isinstance(rt, dict):
                return None
            if sha256_bytes(json_dump_strict(extract.get("design"), sort_keys=True).encode()) \
                    != entry.get("design_sha256"):
                return None
        except Exception:
            return None
        self.hits += 1
        return entry

    def store(self, key: dict, extract: dict, roundtrip: dict, design_sha: str):
        entry = {"key": key, "design_sha256": design_sha,
                 "extract": extract, "roundtrip": roundtrip}
        self._path(key).write_text(json_dump_strict(entry, sort_keys=True) + "\n")


def _size_stats(values) -> dict:
    if not values:
        return {}
    vs = sorted(values)
    n = len(vs)

    def q(p):
        return vs[min(n - 1, int(p * n))]

    return {"min": vs[0], "median": q(0.5), "p90": q(0.9), "max": vs[-1],
            "mean": round(sum(vs) / n, 1)}


def write_report(path_json: Path, path_md: Path, report: dict):
    path_json.write_text(json_dump_strict(report, sort_keys=True) + "\n")
    md = []
    md.append("# sft_v2 full-fidelity rebuild report")
    md.append("")
    md.append(f"- generated_at: {report['generated_at']}")
    md.append(f"- input: {report['input_repo_rel']} (sha256 {report['input_sha256'][:16]})")
    md.append(f"- snapshot: {report['snapshot_repo_rel_or_path']}")
    md.append(f"- seed: {report['seed']}  rows processed: {report['rows_processed']} "
              f"(limit: {report['limit']})")
    md.append(f"- passed: {report['passed']}  failed: {report['failed']}")
    md.append(f"- expected original rows: {report['expected_rows']} "
              f"({'match' if report['rows_in_original'] == report['expected_rows'] else 'MISMATCH'})")
    md.append(f"- unique source files: {report['unique_files']} "
              f"(expected {report['expected_unique_files']}); unique (file, sim) "
              f"configurations: {report['unique_pairs']} (expected {report['expected_unique_pairs']})")
    md.append(f"- cache: {report['cache_hits']} hits / {report['extract_calls']} extract calls")
    md.append("- extractor: Cursor Composer 2.5 (fastMode=false) via "
              "scripts/sft_full_fidelity_extract.py; roundtrip metrics gated against "
              "metrics_comparison_baseline=original_source")
    md.append("- builder model: Factory Droid - GLM-5.3-Flash, reasoning_effort=max")
    md.append("- independent review: Cursor Grok4.7 final review PENDING (not performed); "
              "this report does not claim the review passed")
    md.append("")
    md.append("## Size accounting (no specs dropped; rough token estimate = chars/4)")
    md.append("")
    for key in ("content_chars", "thought_chars", "design_chars"):
        st = report.get("size_stats", {}).get(key)
        if st:
            md.append(f"- {key}: median {st['median']}, p90 {st['p90']}, max {st['max']} "
                      f"(~{st['max'] // 4} tokens at max)")
    md.append("")
    md.append("## Prompt-vs-config conflicts (reported, prompts unaltered)")
    md.append("")
    conflict_rows = [r for r in report["rows"] if r.get("prompt", {}).get("motor_conflicts")
                     or any(c.get("verdict") == "conflict" for c in r.get("prompt", {}).get("claims", []))]
    if conflict_rows:
        for r in conflict_rows:
            md.append(f"- {r['id']} ({r['file']} / {r['sim']}): motors prompt="
                      f"{r['prompt'].get('motor_tokens', r['prompt'].get('prompt_motor_tokens'))} "
                      f"vs design={r['prompt'].get('design_motor_values')}; conflicts: "
                      f"{r.get('reasons', [])[:3]}")
    else:
        md.append("- none detected")
    md.append("")
    md.append("## Per-row results")
    md.append("")
    md.append("| # | id | file | sim | status | sizes (content) | reasons |")
    md.append("|---|----|------|-----|--------|-----------------|---------|")
    for r in report["rows"]:
        status = "PASS" if r["status"] == "pass" else "FAIL"
        sizes = r.get("sizes", {})
        reasons = "; ".join(r.get("reasons", []))[:180]
        md.append(f"| {r['index']} | {r['id']} | {r['file']} | {r['sim']} | {status} | "
                  f"{sizes.get('content_chars', '-')} | {reasons} |")
    md.append("")
    md.append("## Failure categories")
    md.append("")
    for cat, ids in sorted(report["failure_categories"].items()):
        md.append(f"- {cat}: {len(ids)} {ids[:10]}")
    if not report["failure_categories"]:
        md.append("- none")
    md.append("")
    if report.get("approved_prompt_corrections"):
        md.extend(["## User-approved prompt corrections", ""])
        for correction in report["approved_prompt_corrections"]:
            md.append(f"- {correction['id']}: C11 → C6 in prompt_text and the user message only.")
    path_md.write_text("\n".join(md) + "\n")


def do_apply(input_path: Path, snapshot_path: Path, candidate_path: Path,
             n_snapshot_rows: int, n_candidate_rows: int, output_dir: Path,
             applied_note: dict) -> int:
    if n_candidate_rows != n_snapshot_rows:
        print(f"APPLY REFUSED: candidate has {n_candidate_rows} rows, the original snapshot has "
              f"{n_snapshot_rows}; a partial or limited candidate can never replace the dataset",
              file=sys.stderr)
        return 1
    current = input_path.read_bytes()
    snap = snapshot_path.read_bytes()
    if sha256_bytes(current) != sha256_bytes(snap):
        print("APPLY REFUSED: input file is no longer byte-identical to the immutable "
              "snapshot; refusing to overwrite changed data", file=sys.stderr)
        return 1
    tmp = input_path.with_suffix(input_path.suffix + ".rebuild_tmp")
    tmp.write_bytes(candidate_path.read_bytes())
    os.replace(tmp, input_path)
    (output_dir / "APPLIED.json").write_text(json_dump_strict(
        {**applied_note, "applied_at": now_iso(),
         "input_sha256_before": sha256_bytes(snap),
         "input_sha256_after": sha256_bytes(input_path.read_bytes())}, sort_keys=True) + "\n")
    print(f"APPLIED: {input_path} now holds the full-fidelity rebuild "
          f"({n_candidate_rows} rows); original bytes preserved in {snapshot_path}")
    return 0


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def correct_approved_motor_label(row: dict, enabled: bool) -> tuple:
    """Apply only the three explicitly user-approved prompt-label corrections."""
    if not enabled or row.get("id") not in APPROVED_MOTOR_LABEL_IDS:
        return row, None
    if row.get("file") != "ork/rockets__bt_55.ork" or row.get("sim") != "Simulation 1":
        raise RowFailure(["approved motor-label correction source mapping differs from the approved rows"])
    prompt = row.get("prompt_text")
    messages = row.get("messages")
    if (not isinstance(prompt, str) or not re.search(r"\bC11\b", prompt)
            or not isinstance(messages, list) or len(messages) < 2
            or messages[1].get("role") != "user" or messages[1].get("content") != prompt):
        raise RowFailure(["approved motor-label correction does not match the original C11 prompt/user message"])
    corrected = copy.deepcopy(row)
    corrected_prompt = re.sub(r"\bC11\b", "C6", prompt)
    corrected["prompt_text"] = corrected_prompt
    corrected["messages"][1]["content"] = corrected_prompt
    return corrected, {
        "id": row["id"], "old_motor": "C11", "new_motor": "C6",
        "fields_changed": ["prompt_text", "messages[1].content"],
        "original_prompt_text": prompt, "corrected_prompt_text": corrected_prompt,
        "basis": "Explicit user approval to correct only these three motor labels to the selected original C6 simulation.",
    }


def main(argv=None, repo_root=None, workspace_root=None,
         extractor_module_name: str = EXTRACT_MODULE) -> int:
    repo = Path(repo_root) if repo_root else _REPO_ROOT
    workspace = Path(workspace_root) if workspace_root else \
        (repo.parents[1] if len(repo.parents) > 1 and repo.parent.name == "_repos" else None)
    ap = argparse.ArgumentParser(
        description="Rebuild existing new_results/sft_v2.jsonl rows at full input fidelity "
                    "using the agreed Composer extractor (see module docstring).")
    ap.add_argument("--input", default=DEFAULT_INPUT_REL,
                    help="input JSONL (default: repository " + DEFAULT_INPUT_REL + ")")
    ap.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR_REL,
                    help="isolated output directory (default: " + DEFAULT_OUTPUT_DIR_REL + ")")
    ap.add_argument("--limit", type=int, default=None,
                    help="process only the first N rows (smoke test; can never be applied)")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--correct-approved-motor-labels", action="store_true",
                    help="apply the user-approved C11→C6 prompt-label correction only in U-020, U-268 and U-269")
    ap.add_argument("--apply", action="store_true",
                    help="replace the input file with the candidate AFTER all original rows "
                         "pass (parent-only; refused with --limit or on any failure)")
    args = ap.parse_args(argv)

    if args.apply and args.limit is not None:
        print("USAGE ERROR: --limit is a sampling smoke test and can never replace the full "
              "dataset; rerun without --limit before --apply", file=sys.stderr)
        return 2
    if args.limit is not None and args.limit <= 0:
        print("USAGE ERROR: --limit must be positive", file=sys.stderr)
        return 2

    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = repo / input_path
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = repo / output_dir

    if not input_path.is_file():
        print(f"BLOCKED: input not found: {input_path}", file=sys.stderr)
        return 3
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. immutable snapshot first (before anything else); reruns read it, never
    #    their own output.
    try:
        snapshot_path, source_bytes, _created = snapshot_original(input_path, output_dir, repo)
    except RebuildError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 3

    try:
        rows = [json_loads_strict(line) for line in source_bytes.decode("utf-8").splitlines()
                if line.strip()]
    except (ValueError, UnicodeDecodeError) as exc:
        print(f"BLOCKED: input JSONL does not parse strictly: {exc}", file=sys.stderr)
        return 3
    if len(rows) != EXPECTED_ROWS:
        print(f"note: input has {len(rows)} rows (expected {EXPECTED_ROWS}); proceeding, "
              f"count is reported", file=sys.stderr)

    # 2. extractor (lazy; clean blocker message if integration is not ready)
    try:
        extractor = load_extractor(extractor_module_name)
    except ExtractorUnavailable as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 3
    ext_sha = extractor_fingerprint(extractor)

    selection = rows if args.limit is None else rows[:args.limit]
    cache = Cache(output_dir / "cache")
    rt_scratch = output_dir / "rt"
    rt_scratch.mkdir(parents=True, exist_ok=True)

    candidate_rows, row_reports = [], []
    extract_calls = 0
    for idx, row in enumerate(selection):
        entry = {"index": idx, "id": row.get("id", "?") if isinstance(row, dict) else "?",
                 "file": row.get("file") if isinstance(row, dict) else "?",
                 "sim": row.get("sim") if isinstance(row, dict) else "?",
                 "status": "pass", "reasons": [], "warnings": []}
        try:
            if not isinstance(row, dict):
                raise RowFailure(["row is not a JSON object"])
            source_path, strategy = resolve_source(row["file"], row["sim"], repo, workspace)
            row, correction = correct_approved_motor_label(row, args.correct_approved_motor_labels)
            if correction:
                entry["approved_prompt_correction"] = correction
            source_sha = sha256_file(source_path)
            entry["source_resolved"] = str(source_path.relative_to(repo))
            entry["source_strategy"] = strategy
            entry["source_sha256"] = source_sha

            cache_key = {"file_rel": row["file"], "sim": row["sim"], "seed": args.seed,
                         "source_sha256": source_sha, "extractor_sha": ext_sha}
            hit = cache.load(cache_key)
            if hit is not None:
                extract, rt = hit["extract"], hit["roundtrip"]
                entry["cache"] = "hit"
            else:
                extract_calls += 1
                try:
                    extract = extractor.extract_design(source_path, row["sim"], seed=args.seed)
                except Exception as exc:
                    raise RowFailure([f"extract_design failed: "
                                      f"{exc.__class__.__name__}: {exc}"])
                if not isinstance(extract, dict):
                    raise RowFailure(["extract_design did not return a dict"])
                try:
                    design_sha = sha256_bytes(
                        json_dump_strict(extract.get("design"), sort_keys=True).encode())
                except ValueError as exc:
                    raise RowFailure([f"extract design is not finite/serializable JSON: {exc}"])
                destination = rt_scratch / f"{slug(str(row['id']))}__{source_sha[:12]}.ork"
                try:
                    built = extractor.build_ork(extract["design"], destination)
                except Exception as exc:
                    raise RowFailure([f"build_ork failed: {exc.__class__.__name__}: {exc}"])
                try:
                    rt = extractor.validate_roundtrip(source_path, row["sim"],
                                                      extract["design"], built,
                                                      seed=args.seed)
                except Exception as exc:
                    raise RowFailure([f"validate_roundtrip failed: "
                                      f"{exc.__class__.__name__}: {exc}"])
                ok0, prob0, _n0, _u0 = accept_roundtrip(rt, extract,
                                                        extract.get("field_manifest"))
                if not ok0:
                    raise RowFailure([f"roundtrip acceptance failed: {x}" for x in prob0])
                cache.store(cache_key, extract, rt, design_sha)
                entry["cache"] = "store"

            new_row, info = rebuild_row(row, extract, rt, args.seed, repo, workspace,
                                        source_rel=row["file"], source_sha=source_sha,
                                        report_entry=entry)
            if correction:
                new_row[ROW_METADATA_KEY]["approved_prompt_correction"] = correction
            for k in ("sizes", "roundtrip"):
                if k in info:
                    entry[k] = info[k]
            entry["warnings"] = info.get("warnings", [])
            candidate_rows.append(new_row)
        except RowFailure as exc:
            entry["status"] = "fail"
            reasons = exc.args[0] if exc.args else [str(exc)]
            entry["reasons"] = list(dict.fromkeys(entry.get("reasons", []) + reasons))
        except Exception as exc:  # never let one row kill the run
            entry["status"] = "fail"
            entry["reasons"] = [f"unexpected {exc.__class__.__name__}: {exc}"]
        row_reports.append(entry)

    # duplicate-id preservation check (never introduce, never silently drop)
    id_counts: dict[str, int] = {}
    for r in rows:
        k = r.get("id") if isinstance(r, dict) else None
        id_counts[k] = id_counts.get(k, 0) + 1
    cand_counts: dict[str, int] = {}
    for r in candidate_rows:
        cand_counts[r["id"]] = cand_counts.get(r["id"], 0) + 1
    dup_introduced = sorted(i for i, c in cand_counts.items() if c > 1
                            and id_counts.get(i, 0) < c)

    unique_files = {r.get("file") for r in rows if isinstance(r, dict)}
    unique_pairs = {(r.get("file"), r.get("sim")) for r in rows if isinstance(r, dict)}

    failures = [e for e in row_reports if e["status"] != "pass"]
    failure_categories: dict[str, list] = {}
    for e in failures:
        for reason in e["reasons"]:
            cat = reason.split(":")[0].split(" (")[0][:60]
            failure_categories.setdefault(cat, []).append(e["id"])

    candidate_dir = output_dir / "candidate"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    candidate_path = candidate_dir / "sft_v2_full_fidelity.jsonl"
    candidate_path.write_text("".join(json_dump_strict(r) + "\n" for r in candidate_rows))

    size_stats = {}
    for key in ("content_chars", "thought_chars", "design_chars"):
        vals = [r.get("sizes", {}).get(key) for r in row_reports if r.get("sizes")]
        vals = [v for v in vals if v is not None]
        size_stats[key] = _size_stats(vals)

    report = {
        "generated_at": now_iso(),
        "input_repo_rel": str(input_path.relative_to(repo))
        if input_path.is_relative_to(repo) else str(input_path),
        "input_sha256": sha256_bytes(source_bytes),
        "snapshot_repo_rel_or_path": str(snapshot_path.relative_to(repo))
        if snapshot_path.is_relative_to(repo) else str(snapshot_path),
        "seed": args.seed, "limit": args.limit,
        "rows_processed": len(selection), "rows_in_original": len(rows),
        "expected_rows": EXPECTED_ROWS,
        "unique_files": len(unique_files), "expected_unique_files": EXPECTED_UNIQUE_FILES,
        "unique_pairs": len(unique_pairs), "expected_unique_pairs": EXPECTED_UNIQUE_PAIRS,
        "passed": len(selection) - len(failures), "failed": len(failures),
        "cache_hits": cache.hits, "extract_calls": extract_calls,
        "size_stats": size_stats,
        "duplicate_ids_in_original": {str(k): v for k, v in id_counts.items() if v > 1},
        "duplicate_ids_introduced": dup_introduced,
        "failure_categories": failure_categories,
        "approved_prompt_corrections": [
            e["approved_prompt_correction"] for e in row_reports if e.get("approved_prompt_correction")
        ],
        "provenance": BUILDER_PROVENANCE,
        "rows": row_reports,
    }
    write_report(output_dir / "report.json", output_dir / "report.md", report)

    verb = "smoke" if args.limit is not None else "rebuild"
    median = size_stats.get("content_chars", {}).get("median", 0)
    print(f"{verb}: {len(selection) - len(failures)}/{len(selection)} rows passed; "
          f"candidate={candidate_path} (applyable rows: {len(candidate_rows)}/{len(rows)}); "
          f"median assistant content {median} chars")
    if dup_introduced:
        print(f"BLOCKED: duplicate ids introduced in candidate: {dup_introduced}",
              file=sys.stderr)
        return 1
    if failures:
        print(f"{len(failures)} row(s) failed; --apply refused. See "
              f"{output_dir / 'report.md'} for every reason.")
        return 1
    if args.apply:
        return do_apply(input_path, snapshot_path, candidate_path,
                        len(rows), len(candidate_rows), output_dir,
                        {"seed": args.seed, "rows": len(candidate_rows),
                         "candidate_sha256": sha256_file(candidate_path)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
