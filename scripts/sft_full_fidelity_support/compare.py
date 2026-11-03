"""Compare extracted designs, metrics, attachments, and audit snapshots."""

from __future__ import annotations

import math
from typing import Any

def filter_manifest_by_prefixes(
    manifest: list[dict[str, Any]], prefixes: tuple[str, ...]
) -> list[dict[str, Any]]:
    return [row for row in manifest if any(row["path"].startswith(p) for p in prefixes)]


AUTHORITATIVE_MANIFEST_PREFIXES = (
    "/parameter_tree",
    "/selected_simulation",
    "/bundle_entries",
    "/ork_container",
)

AUDIT_MANIFEST_PREFIXES = (
    "/component_index",
    "/simulation_options_snapshot",
)

MANDATORY_METRIC_KEYS = (
    "apogee_m",
    "max_velocity_ms",
    "time_to_apogee_s",
    "flight_time_s",
    "ground_hit_ms",
    "wind_ms",
)

OPTIONAL_METRIC_KEYS = (
    "max_accel_ms2",
    "max_mach",
    "deployment_velocity_ms",
    "stability_cal",
)


def strict_number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def sanitize_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in metrics.items():
        if key.endswith("_status") and isinstance(value, str):
            out[key] = value
            continue
        if key == "events":
            out[key] = sanitize_events(value)
            continue
        if key == "runtime_ms":
            n = strict_number(value)
            out[key] = n
            continue
        n = strict_number(value)
        if n is None and key in OPTIONAL_METRIC_KEYS:
            out[key] = None
            out[f"{key}_status"] = "unavailable"
        elif n is None:
            out[key] = None
        else:
            out[key] = n
    return out


def sanitize_events(events: Any) -> list[dict[str, Any]]:
    if not isinstance(events, list):
        return []
    out: list[dict[str, Any]] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        t = strict_number(event.get("t"))
        out.append(
            {
                "branch": int(event.get("branch", 0)),
                "type": str(event.get("type", "")),
                "t": t,
                "t_status": "ok" if t is not None else "unavailable",
            }
        )
    return out


def _leaf_manifest(manifest: list[dict[str, Any]]) -> dict[str, Any]:
    return {row["path"]: row["value"] for row in manifest}


def compare_manifests(
    left: list[dict[str, Any]],
    right: list[dict[str, Any]],
) -> list[str]:
    a = _leaf_manifest(left)
    b = _leaf_manifest(right)
    errors: list[str] = []
    for path in sorted(set(a) | set(b)):
        if path not in a:
            errors.append(f"missing in source manifest: {path}")
            continue
        if path not in b:
            errors.append(f"missing in rebuilt manifest: {path}")
            continue
        if not _values_equal(a[path], b[path]):
            errors.append(f"manifest value mismatch at {path}: {a[path]!r} vs {b[path]!r}")
    return errors


def compare_component_snapshots(
    left: list[dict[str, Any]],
    right: list[dict[str, Any]],
    *,
    rel_tol: float = 1e-8,
    abs_tol: float = 1e-6,
) -> list[str]:
    errors: list[str] = []
    if len(left) != len(right):
        errors.append(f"component count {len(left)} vs {len(right)}")
    for index, (a, b) in enumerate(zip(left, right)):
        if a.get("openrocket_class") != b.get("openrocket_class"):
            errors.append(
                f"component[{index}] class {a.get('openrocket_class')!r} vs {b.get('openrocket_class')!r}"
            )
        if a.get("name") != b.get("name"):
            errors.append(f"component[{index}] name {a.get('name')!r} vs {b.get('name')!r}")
        loaded_errors = _compare_loaded(
            a.get("loaded") or {},
            b.get("loaded") or {},
            f"/component_index/{index}/loaded",
            rel_tol=rel_tol,
            abs_tol=abs_tol,
        )
        errors.extend(loaded_errors)
    return errors


def compare_simulation_options(
    left: dict[str, Any] | None,
    right: dict[str, Any] | None,
    *,
    rel_tol: float = 1e-8,
    abs_tol: float = 1e-6,
) -> list[str]:
    if left is None and right is None:
        return []
    if left is None or right is None:
        return ["simulation_options_snapshot missing on one side"]
    skip = {"getRandomSeed"}  # internal PRNG stream id; flight reproducibility uses explicit seed + OrBatch.reseed
    errors: list[str] = []
    for key in sorted(set(left) | set(right)):
        if key in skip:
            continue
        if key not in left or key not in right:
            errors.append(f"simulation_options missing key {key}")
            continue
        if not _values_equal(left[key], right[key], rel_tol=rel_tol, abs_tol=abs_tol):
            errors.append(f"simulation_options.{key}: {left[key]!r} vs {right[key]!r}")
    return errors


def compare_bundle_entries(left: dict[str, Any], right: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if set(left) != set(right):
        errors.append(f"bundle entry names differ: {sorted(left)} vs {sorted(right)}")
    for name in sorted(set(left) & set(right)):
        if left[name].get("sha256") != right[name].get("sha256"):
            errors.append(f"bundle sha256 mismatch for {name}")
    return errors


def _compare_loaded(
    a: dict[str, Any],
    b: dict[str, Any],
    prefix: str,
    *,
    rel_tol: float,
    abs_tol: float,
) -> list[str]:
    errors: list[str] = []
    for key in sorted(set(a) | set(b)):
        if key not in a or key not in b:
            errors.append(f"{prefix}/{key}: missing on one side")
            continue
        va, vb = a[key], b[key]
        if isinstance(va, dict) and "error" in va:
            continue
        if isinstance(vb, dict) and "error" in vb:
            continue
        if _values_equal(va, vb, rel_tol=rel_tol, abs_tol=abs_tol):
            continue
        errors.append(f"{prefix}/{key}: {va!r} vs {vb!r}")
    return errors


def _values_equal(a: Any, b: Any, *, rel_tol: float = 1e-9, abs_tol: float = 1e-6) -> bool:
    if a == b:
        return True
    if isinstance(a, float) or isinstance(b, float):
        fa, fb = strict_number(a), strict_number(b)
        if fa is None and fb is None:
            return True
        if fa is None or fb is None:
            return False
        return math.isclose(fa, fb, rel_tol=rel_tol, abs_tol=abs_tol)
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            return False
        return all(_values_equal(a[k], b[k], rel_tol=rel_tol, abs_tol=abs_tol) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return False
        return all(_values_equal(x, y, rel_tol=rel_tol, abs_tol=abs_tol) for x, y in zip(a, b))
    return False


def compare_events(
    left: list[dict[str, Any]],
    right: list[dict[str, Any]],
    *,
    abs_tol: float = 1e-6,
) -> list[str]:
    errors: list[str] = []
    if len(left) != len(right):
        errors.append(f"event count {len(left)} vs {len(right)}")
    for index, (a, b) in enumerate(zip(left, right)):
        if a.get("branch") != b.get("branch") or a.get("type") != b.get("type"):
            errors.append(f"event[{index}] identity mismatch: {a} vs {b}")
            continue
        ta, tb = strict_number(a.get("t")), strict_number(b.get("t"))
        if ta is None or tb is None:
            if a.get("t_status") != b.get("t_status"):
                errors.append(f"event[{index}] time availability mismatch")
            continue
        if not math.isclose(ta, tb, rel_tol=0, abs_tol=abs_tol):
            errors.append(f"event[{index}] time {ta} vs {tb}")
    return errors


def metric_diffs(
    source_metrics: dict[str, Any],
    rebuilt_metrics: dict[str, Any],
    *,
    rel_tol: float = 1e-9,
    abs_tol: float = 1e-6,
) -> dict[str, Any]:
    source = sanitize_metrics(source_metrics)
    rebuilt = sanitize_metrics(rebuilt_metrics)
    diffs: dict[str, Any] = {}
    for key in MANDATORY_METRIC_KEYS + OPTIONAL_METRIC_KEYS:
        a, b = source.get(key), rebuilt.get(key)
        fa, fb = strict_number(a), strict_number(b)
        if key in OPTIONAL_METRIC_KEYS and fa is None and fb is None:
            diffs[key] = {
                "source": None,
                "rebuilt": None,
                "delta": None,
                "close": True,
                "status": "unavailable_both",
            }
            continue
        if fa is None or fb is None:
            diffs[key] = {
                "source": fa,
                "rebuilt": fb,
                "delta": None,
                "close": False,
                "status": "availability_mismatch",
            }
            continue
        delta = fb - fa
        diffs[key] = {
            "source": fa,
            "rebuilt": fb,
            "delta": delta,
            "close": math.isclose(fa, fb, rel_tol=rel_tol, abs_tol=abs_tol),
            "status": "ok",
        }
    event_errors = compare_events(source.get("events") or [], rebuilt.get("events") or [], abs_tol=abs_tol)
    diffs["events"] = {
        "source_count": len(source.get("events") or []),
        "rebuilt_count": len(rebuilt.get("events") or []),
        "close": len(event_errors) == 0,
        "errors": event_errors[:20],
    }
    return diffs


def metrics_pass(diffs: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    for key in MANDATORY_METRIC_KEYS:
        row = diffs.get(key)
        if not row or not row.get("close"):
            errors.append(f"mandatory metric mismatch or missing: {key}")
    events_row = diffs.get("events") or {}
    if not events_row.get("close"):
        errors.append("simulation event sequence mismatch")
    return len(errors) == 0, errors
