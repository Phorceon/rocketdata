"""Tests for the readable motor ids (Task: replace digests with motor ids).

Purely static: no JVM, no simulation, no flights.  Uses the synthetic
compact-design fixture shape (single-key-wrapper children) and small
hand-written motor-database entries mirroring motor_db_full.json.
"""

from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.sft_compact_motor_ids import (  # noqa: E402
    add_explicit_preset_overrides,
    build_motor_lookup,
    build_stage2_design,
    collect_dataset_motor_entries,
    load_lookup,
    replace_motor_digests_with_ids,
    restore_motor_digests,
)
from scripts.sft_compact_design import from_compact  # noqa: E402
from scripts.sft_compact_reasoning import child, find_rocket, walk_components

HEX_RE = re.compile(r"\b[0-9a-f]{32,}\b", re.IGNORECASE)


def _leaf(tag, value, attrs=None):
    payload: dict = {}
    if attrs:
        payload["attrs"] = attrs
    payload["value"] = value
    return {tag: payload}


def _comp(tag, attrs=None, children=None):
    payload: dict = {}
    if attrs:
        payload["attrs"] = attrs
    payload["children"] = children or []
    return {tag: payload}


def db_entry(manuf, desig, digest, dia=0.018, length=0.07, ti=10.0,
             burn=1.6, avg=6.26, mtype="Single-use"):
    return {"manufacturer": manuf, "designation": desig, "digest": digest,
            "diameter_m": dia, "length_m": length, "total_impulse_ns": ti,
            "burn_time_s": burn, "average_thrust_n": avg, "motor_type": mtype}


def sample_db() -> list[dict]:
    d1 = "1f2e3d4c5b6a79887766554433221100"
    d2 = "0123456789abcdef0123456789abcdef"
    d3 = "deadbeefdeadbeefdeadbeefdeadbeef"
    return [
        # Estes C6 under two manufacturer spellings, same digest
        db_entry("Estes", "C6", d1),
        db_entry("Estes Industries, Inc.", "C6", d1),
        # two distinct motors sharing the designation B6
        db_entry("Estes", "B6", d2, dia=0.018, length=0.07, ti=5.0),
        db_entry("Estes", "B6", d3, dia=0.018, length=0.07, ti=5.01),
        # a motor nobody uses
        db_entry("Klima", "D21", "aaaa0000aaaa0000aaaa0000aaaa0000"),
    ]


def sample_dataset() -> list[dict]:
    # dataset uses the Estes spelling for C6 and BOTH B6 curves
    return [
        db_entry("Estes", "C6", "1f2e3d4c5b6a79887766554433221100"),
        db_entry("Estes", "B6", "0123456789abcdef0123456789abcdef"),
        db_entry("Estes", "B6", "deadbeefdeadbeefdeadbeefdeadbeef"),
        # a stale design digest the shipped database does not list
        db_entry("Estes", "C6X", "11112222333344445555666677778888",
                 dia=0.018, length=0.07, ti=9.0, burn=1.5, avg=6.0),
    ]


# --------------------------------------------------------------------------
# lookup build
# --------------------------------------------------------------------------

def test_lookup_is_one_to_one_and_hex_free():
    lookup = build_motor_lookup(sample_db(), sample_dataset())
    ids = set(lookup)
    digests = {v["digest"] for v in lookup.values()}
    assert len(ids) == len(lookup)
    assert len(digests) == len(lookup)
    for mid, meta in lookup.items():
        assert not HEX_RE.search(mid), mid
        assert mid.startswith(f"{meta['manufacturer']}-"
                              f"{meta['designation']}") or \
            mid.startswith(f"{meta['manufacturer']}-"), mid
        assert meta["digest"] and not HEX_RE.search(
            json.dumps({k: v for k, v in meta.items() if k != "digest"}))


def test_lookup_id_format_and_required_fields():
    lookup = build_motor_lookup(sample_db(), sample_dataset())
    for mid, meta in lookup.items():
        assert re.fullmatch(r".+-.+(-v\d+)?", mid)
        assert set(meta) == {"manufacturer", "designation", "digest",
                             "diameter_m", "length_m", "total_impulse_ns",
                             "burn_time_s", "average_thrust_n", "in_dataset"}
        assert isinstance(meta["in_dataset"], bool)


def test_lookup_deterministic_under_shuffling():
    db = sample_db()
    ds = sample_dataset()
    lookup1 = build_motor_lookup(db, ds)
    for seed in range(5):
        shuffled_db = db[:]
        shuffled_ds = ds[:]
        random.Random(seed).shuffle(shuffled_db)
        random.Random(seed + 100).shuffle(shuffled_ds)
        assert build_motor_lookup(shuffled_db, shuffled_ds) == lookup1


def test_suffixes_when_names_collide_and_dataset_spelling_wins():
    lookup = build_motor_lookup(sample_db(), sample_dataset())
    # two distinct B6 curves: versioned ids
    b6 = sorted(k for k in lookup
                if lookup[k]["manufacturer"] == "Estes"
                and lookup[k]["designation"] == "B6")
    assert b6 == ["Estes-B6-v1", "Estes-B6-v2"]
    # the dataset digest spelled "Estes" wins the C6 representative
    c6 = [k for k in lookup
          if lookup[k]["digest"] == "1f2e3d4c5b6a79887766554433221100"]
    assert c6 == ["Estes-C6"]
    assert lookup["Estes-C6"]["in_dataset"] is True
    # the stale dataset-only digest gets an id too
    stale = [k for k in lookup
             if lookup[k]["digest"] == "11112222333344445555666677778888"]
    assert stale == ["Estes-C6X"]
    assert lookup["Estes-C6X"]["in_dataset"] is True
    # names without collisions carry no suffix
    assert "Klima-D21" in lookup


def test_digest_tiebreak_is_last_resort_only():
    # two identical-in-property motors may only differ by digest: the sort
    # must still be stable (no hash, no Java object id)
    db = [db_entry("Estes", "A8", "0" * 31 + "1"),
          db_entry("Estes", "A8", "0" * 31 + "2")]
    lookup = build_motor_lookup(db, [])
    assert sorted(lookup) == ["Estes-A8-v1", "Estes-A8-v2"]
    assert [lookup[i]["digest"] for i in ("Estes-A8-v1", "Estes-A8-v2")] == \
        ["0" * 31 + "1", "0" * 31 + "2"]


def test_load_lookup_round_trip(tmp_path):
    lookup = build_motor_lookup(sample_db(), sample_dataset())
    path = tmp_path / "motor_lookup.json"
    path.write_text(json.dumps(lookup, indent=1, sort_keys=True))
    got, id_by_digest, digest_by_id = load_lookup(path)
    assert got == lookup
    assert id_by_digest == {v["digest"]: k for k, v in lookup.items()}
    assert digest_by_id == {k: v["digest"] for k, v in lookup.items()}
    assert len(id_by_digest) == len(digest_by_id) == len(lookup)


# --------------------------------------------------------------------------
# compact-tree replacement and restore
# --------------------------------------------------------------------------

def design_with_digest(digest: str | None) -> dict:
    motor = [_leaf("type", "single"),
             _leaf("manufacturer", "Estes"),
             _leaf("designation", "C6"),
             _leaf("diameter", 0.018),
             _leaf("length", 0.07),
             _leaf("delay", 0.0)]
    if digest is not None:
        motor.insert(3, _leaf("digest", digest))
    mount = _comp("motormount", children=[
        _leaf("ignitionevent", "launch"),
        _comp("motor", attrs={"configid": "cfg0"}, children=motor),
    ])
    inner = _comp("innertube", children=[
        _leaf("position", 0.02), _leaf("length", 0.2),
        _leaf("radius", 0.014), _leaf("thickness", 0.001), mount])
    tube = _comp("bodytube", children=[
        _leaf("length", 0.457), _leaf("radius", 0.0124),
        _leaf("thickness", 0.0005), _leaf("position", 0.12),
        _comp("subcomponents", children=[inner])])
    stage = _comp("stage", children=[
        _comp("subcomponents", children=[tube])])
    rocket = _comp("rocket", attrs={"referencetype": "maximum"}, children=[
        _comp("subcomponents", children=[stage])])
    return {"openrocket": {"attrs": {"version": "1.9"},
                           "children": [rocket]}}


def design_motors(design: dict):
    """Every <motor> payload anywhere under the rocket, document order."""
    rocket = find_rocket(design)
    out = []

    def visit(node: dict) -> None:
        kids = node.get("children")
        if not isinstance(kids, list):
            return
        for wrapper in kids:
            if not (isinstance(wrapper, dict) and len(wrapper) == 1):
                continue
            (tag, payload), = wrapper.items()
            if tag == "motor":
                out.append(payload)
            visit(payload)

    visit(rocket)
    return out


def test_replace_swaps_digest_for_motor_id_in_place():
    digest = "1f2e3d4c5b6a79887766554433221100"
    design = design_with_digest(digest)
    lookup = build_motor_lookup(sample_db(), sample_dataset())
    id_by_digest = {v["digest"]: k for k, v in lookup.items()}
    out = replace_motor_digests_with_ids(design, id_by_digest)
    (motor,) = design_motors(out)
    kids = [next(iter(w)) for w in motor["children"]]
    assert "digest" not in kids and "motor_id" in kids
    # same position: right after designation
    assert kids.index("motor_id") == kids.index("designation") + 1
    assert child(motor, "motor_id")["value"] == "Estes-C6"


def test_replace_ignores_digestless_motors_and_rejects_unknown():
    lookup = build_motor_lookup(sample_db(), sample_dataset())
    id_by_digest = {v["digest"]: k for k, v in lookup.items()}
    clean = design_with_digest(None)
    out = replace_motor_digests_with_ids(clean, id_by_digest)
    assert json.dumps(out, sort_keys=True) == json.dumps(clean, sort_keys=True)
    junk = design_with_digest("f" * 32)
    with pytest.raises(ValueError, match="no motor_id"):
        replace_motor_digests_with_ids(junk, id_by_digest)


def expanded_motors(node: dict):
    """Every <motor> node of an expanded {tag, attrs, text, children} tree."""
    out = []

    def rec(n: dict) -> None:
        for c in n.get("children") or []:
            if not isinstance(c, dict):
                continue
            if c.get("tag") == "motor":
                out.append(c)
            rec(c)

    rec(node)
    return out


def test_round_trip_through_from_compact_and_restore():
    digest = "1f2e3d4c5b6a79887766554433221100"
    design = design_with_digest(digest)
    lookup = build_motor_lookup(sample_db(), sample_dataset())
    id_by_digest = {v["digest"]: k for k, v in lookup.items()}
    digest_by_id = {k: v["digest"] for k, v in lookup.items()}

    stage2 = build_stage2_design(design, id_by_digest)
    full = from_compact(stage2)
    restore_motor_digests(full["parameter_tree"], digest_by_id)

    (motor,) = expanded_motors(full["parameter_tree"])
    digest_node = next(c for c in motor["children"]
                       if isinstance(c, dict) and c.get("tag") == "digest")
    assert digest_node["text"] == digest
    assert not any(c.get("tag") == "motor_id" for c in motor["children"])


def test_stage2_design_equals_removals_plus_id_swap():
    from scripts.sft_compact_removals import apply_approved_removals
    digest = "1f2e3d4c5b6a79887766554433221100"
    design = design_with_digest(digest)
    lookup = build_motor_lookup(sample_db(), sample_dataset())
    id_by_digest = {v["digest"]: k for k, v in lookup.items()}

    stage2 = build_stage2_design(design, id_by_digest)
    plain = apply_approved_removals(design)
    orig_kids = [next(iter(w)) for w in design_motors(design)[0]["children"]]
    (motor_s2,) = design_motors(stage2)
    (motor_plain,) = design_motors(plain)
    s2_kids = [next(iter(w)) for w in motor_s2["children"]]
    plain_kids = [next(iter(w)) for w in motor_plain["children"]]
    # the motor_id leaf sits exactly where the digest leaf used to be
    assert "digest" in orig_kids and "motor_id" not in orig_kids
    assert "digest" not in plain_kids and "motor_id" not in plain_kids
    assert orig_kids.index("digest") == s2_kids.index("motor_id")
    assert "digest" not in s2_kids
    # everything else identical between the two removal states
    s2_without_id = [w for w in motor_s2["children"] if "motor_id" not in w]
    assert motor_plain["children"] == s2_without_id


# --------------------------------------------------------------------------
# explicit preset-override fix
# --------------------------------------------------------------------------

def add_chute(rocket: dict, chute_wrapper: dict) -> None:
    """Append a {'parachute': payload} wrapper to the body tube's
    subcomponents."""
    tube = next(payload for tag, payload, _ in walk_components(rocket)
                if tag == "bodytube")
    subs = next(w for w in tube["children"] if "subcomponents" in w)
    subs["subcomponents"]["children"].append(chute_wrapper)


def test_preset_override_fix_writes_dump_values():
    digest = "1f2e3d4c5b6a79887766554433221100"
    design = design_with_digest(digest)
    rocket = find_rocket(design)
    # chute without explicit override leaves
    chute_payload = _comp("parachute", children=[
        _leaf("cd", 0.8), _leaf("diameter", 0.3),
        _leaf("deployevent", "apogee"), _leaf("position", 0.1)])
    add_chute(rocket, chute_payload)
    dump_rows = [{
        "cls": "Parachute",
        "loaded": {"isMassOverridden": True, "getOverrideMass": 0.0058967,
                   "isCGOverridden": False, "getOverrideCGX": None},
    }]
    out, fixed = add_explicit_preset_overrides(design, dump_rows)
    assert fixed == ["parachute"]
    chute_out = next(payload for tag, payload, _ in walk_components(
        find_rocket(out)) if tag == "parachute")
    assert child(chute_out, "overridemass")["value"] == 0.0058967
    assert child(chute_out, "overridesubcomponentsmass")["value"] is False
    # inserted right after position, before nothing else was moved
    kids = [next(iter(w)) for w in chute_out["children"]]
    assert kids.index("overridemass") == kids.index("position") + 1


def test_preset_override_fix_is_noop_when_design_has_leaves():
    design = design_with_digest(None)
    rocket = find_rocket(design)
    chute_payload = _comp("parachute", children=[
        _leaf("cd", 0.8), _leaf("overridemass", 0.004),
        _leaf("position", 0.1)])
    add_chute(rocket, chute_payload)
    dump_rows = [{
        "cls": "Parachute",
        "loaded": {"isMassOverridden": True, "getOverrideMass": 0.0058967,
                   "isCGOverridden": False, "getOverrideCGX": None},
    }]
    out, fixed = add_explicit_preset_overrides(design, dump_rows)
    assert fixed == []
    chute_out = next(payload for tag, payload, _ in walk_components(
        find_rocket(out)) if tag == "parachute")
    assert child(chute_out, "overridemass")["value"] == 0.004


def test_collect_dataset_motor_entries_reads_the_real_stage():
    """Integration with the real Stage-1 rows: 83 design digests, all with
    designations; no digest appears twice."""
    stage_dir = REPO_ROOT / "sftgen" / "out" / "scratch" / "sft_compact_20261103"
    if not (stage_dir / "compact" / "train_rows.jsonl").exists():
        pytest.skip("stage rows not generated")
    entries = collect_dataset_motor_entries(stage_dir)
    digests = [e["digest"] for e in entries]
    assert len(digests) == len(set(digests)) == 83
    for e in entries:
        assert e["designation"]
        assert e["manufacturer"]
