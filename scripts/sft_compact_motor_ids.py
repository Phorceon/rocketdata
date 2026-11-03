#!/usr/bin/env python3
"""Readable motor IDs for the Stage-2 compact SFT rows (flight-free).

A motor ``<digest>`` is a content hash that selects the exact thrust curve when
several database motors share a name.  A language model cannot reproduce a
hash, so every model-visible motor carries a readable ``<motor_id>`` instead:

    <Manufacturer>-<Designation>              when that name selects one motor
    <Manufacturer>-<Designation>-v1, -v2, ... when several motors share it

IDs are assigned over the FULL OpenRocket motor database (listed from a
headless boot; ``motor_db_full.json``) plus the handful of dataset-only
digests (stale design-side digests that OpenRocket resolves through its
property fallback, and attachment thrust curves).  Motors are grouped by
(manufacturer, designation) and ordered inside each group by stable non-hash
properties (diameter, length, burn time, total impulse, average thrust, motor
type), the digest being the last tie-break, so version numbers are
deterministic and stable for motors outside this dataset.  The digest of a
motor that appears under several names is represented by exactly one entry
(designation spellings seen in this dataset win, then the stable sort), so
motor_lookup.json maps IDs one-to-one to digests in both directions.

``final/motor_lookup.json`` maps ``motor_id`` to
``{manufacturer, designation, digest, diameter_m, length_m, total_impulse_ns,
burn_time_s, average_thrust_n, in_dataset}``.  ``restore_motor_digests`` is
the from_compact-side inverse: it swaps every ``<motor_id>`` element of a
rebuilt parameter tree back to the ``<digest>`` element that reproduces the
as-is load (for dataset rows that is always the digest the design carried).

The module also holds the parachute-preset fix: five ``rockets__bt_55`` designs
rely on a digest-identified parachute preset to apply a mass override at load
time.  Preset blocks are removed in Stage 2, so the override is written
explicitly (non-hash leaves, values taken from the as-is headless load dump of
the same document) and the load check verifies the result.  NO simulation runs
anywhere in this module: everything is dict transformation and JSON.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from scripts.sft_compact_removals import (
    strip_cosmetic,
    strip_preset_blocks,
    strip_simulation_name,
)

LOOKUP_FIELDS = ("manufacturer", "designation", "digest", "diameter_m",
                 "length_m", "total_impulse_ns", "burn_time_s",
                 "average_thrust_n", "in_dataset")

# stable non-hash sort properties (the digest is appended as the last tie-break)
_SORT_KEYS = ("diameter_m", "length_m", "burn_time_s", "total_impulse_ns",
              "average_thrust_n", "motor_type")


# --------------------------------------------------------------------------
# lookup construction
# --------------------------------------------------------------------------

def _sort_key(entry: dict) -> tuple:
    # None sorts last per property; types are consistent per property
    return tuple(
        (entry.get(k) is None, entry.get(k))
        for k in _SORT_KEYS
    ) + (str(entry.get("digest")),)


def _name_key(entry: dict) -> tuple:
    return (str(entry.get("manufacturer")), str(entry.get("designation")))


def build_motor_lookup(db_entries: list[dict],
                       dataset_entries: list[dict]) -> dict[str, dict]:
    """motor_id -> lookup fields, one-to-one with digests.

    ``db_entries`` is the full headless motor-database listing
    (motor_db_full.json).  ``dataset_entries`` holds one entry per dataset
    design-side digest (same field names; numbers from the resolved motors)
    and may carry digests that are not in the shipped database.  ``in_dataset``
    is true exactly for digests that occur in a Stage-1 compact row.
    """
    dataset_digests = {e["digest"] for e in dataset_entries}
    dataset_names = {_name_key(e) for e in dataset_entries}

    # one representative per digest; designation spellings that occur in this
    # dataset win (so a dataset motor keeps its own name in its ID), then the
    # stable non-hash order with the digest as the last tie-break.
    by_digest: dict[str, list[dict]] = {}
    for entry in db_entries + dataset_entries:
        by_digest.setdefault(entry["digest"], []).append(entry)

    representatives: list[dict] = []
    for digest in sorted(by_digest):
        cands = by_digest[digest]

        def rep_key(e: dict) -> tuple:
            name = _name_key(e)
            return ((0 if name in dataset_names else 1,
                     str(name[0]), str(name[1]))
                    + _sort_key(e))

        reps = sorted(cands, key=rep_key)
        chosen = dict(reps[0])
        chosen["in_dataset"] = digest in dataset_digests
        representatives.append(chosen)

    # group by (manufacturer, designation), order inside the group on stable
    # properties with the digest as the last tie-break, then version-suffix.
    groups: dict[tuple, list[dict]] = {}
    for entry in representatives:
        groups.setdefault(_name_key(entry), []).append(entry)

    lookup: dict[str, dict] = {}
    for name in sorted(groups):
        members = sorted(groups[name], key=_sort_key)
        suffixed = len(members) > 1
        for i, entry in enumerate(members, 1):
            base = f"{entry['manufacturer']}-{entry['designation']}"
            motor_id = f"{base}-v{i}" if suffixed else base
            if motor_id in lookup:
                raise ValueError(f"motor id collision: {motor_id}")
            lookup[motor_id] = {
                "manufacturer": entry["manufacturer"],
                "designation": entry["designation"],
                "digest": entry["digest"],
                "diameter_m": entry["diameter_m"],
                "length_m": entry["length_m"],
                "total_impulse_ns": entry["total_impulse_ns"],
                "burn_time_s": entry["burn_time_s"],
                "average_thrust_n": entry["average_thrust_n"],
                "in_dataset": entry["in_dataset"],
            }

    digests = [v["digest"] for v in lookup.values()]
    if len(digests) != len(set(digests)):
        raise ValueError("lookup is not one-to-one on digests")
    return lookup


def load_lookup(path: Path) -> tuple[dict[str, dict], dict[str, str], dict[str, str]]:
    """(lookup, id_by_digest, digest_by_id) from a motor_lookup.json file."""
    lookup = json.loads(Path(path).read_text())
    id_by_digest = {v["digest"]: k for k, v in lookup.items()}
    digest_by_id = {k: v["digest"] for k, v in lookup.items()}
    if len(id_by_digest) != len(lookup) or len(digest_by_id) != len(lookup):
        raise ValueError("motor lookup is not one-to-one")
    return lookup, id_by_digest, digest_by_id


# --------------------------------------------------------------------------
# dataset-side motor entries (design digests, resolved numbers)
# --------------------------------------------------------------------------

def collect_dataset_motor_entries(stage_dir: Path) -> list[dict]:
    """One entry per distinct design-side motor digest across the Stage-1
    compact rows.

    Identity (manufacturer, designation, diameter, length) comes from the
    design's motor blocks; total impulse, burn time and average thrust come
    from the RESOLVED motor of the same mount in engineering.json (the numbers
    every row already keeps).  Includes digests that the shipped database does
    not list (stale design digests that OpenRocket resolves through its
    property fallback, and attachment thrust curves).
    """
    from scripts.sft_compact_reasoning import (
        child,
        find_rocket,
        stage_wrappers,
        value_of,
        walk_components,
    )

    stage_dir = Path(stage_dir)
    blocks: dict[str, set] = {}
    resolved_by_digest: dict[str, dict] = {}
    eng = json.loads((stage_dir / "engineering.json").read_text())

    for name in ("train", "test"):
        for line in (stage_dir / "compact" / f"{name}_rows.jsonl").read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            key = f"{row['file']}|{row['sim']}"
            rocket = find_rocket(row["compact"])
            design_motors = []
            for _st, st in stage_wrappers(rocket):
                for tag, payload, _depth in walk_components(st):
                    mount = child(payload, "motormount")
                    if mount is None:
                        continue
                    motor = child(mount, "motor")
                    if motor is not None:
                        design_motors.append((tag, payload, motor))
            resolved = [m for m in (eng.get(key, {}).get("motors") or [])
                        if isinstance(m, dict) and m.get("motor")]
            for (_tag, _payload, motor), res in zip(design_motors, resolved):
                digest = value_of(child(motor, "digest"))
                if digest is None:
                    continue
                digest = str(digest)
                block = {
                    "manufacturer": str(value_of(child(motor, "manufacturer"))),
                    "designation": str(value_of(child(motor, "designation"))),
                    "diameter_m": value_of(child(motor, "diameter")),
                    "length_m": value_of(child(motor, "length")),
                }
                blocks.setdefault(digest, set()).add(
                    tuple(sorted(block.items())))
                rdata = res.get("motor") or {}
                resolved_by_digest.setdefault(digest, {
                    "total_impulse_ns": rdata.get("total_impulse_ns"),
                    "burn_time_s": rdata.get("burn_time_s"),
                    "average_thrust_n": rdata.get("average_thrust_n"),
                })

    out = []
    for digest in sorted(blocks):
        # one digest can be written with different manufacturer spellings in
        # different designs (e.g. "Estes" vs "Estes Industries, Inc."): pick
        # the lexicographically first block as the canonical identity.
        canonical = dict(min(blocks[digest]))
        canonical.update(resolved_by_digest.get(digest, {}))
        canonical["digest"] = digest
        out.append(canonical)
    return out


# --------------------------------------------------------------------------
# compact-tree replacement (design side, model-visible)
# --------------------------------------------------------------------------

def _transform_wrappers(node: Any, fn) -> Any:
    """Apply fn(tag, payload) to every single-key wrapper below node.

    Mirrors sft_compact_removals._transform: wrappers are one-key dict ITEMS of
    children lists; fn returns the payload (None drops the wrapper).
    """
    if isinstance(node, dict):
        for key, value in list(node.items()):
            if isinstance(value, list):
                new_list = []
                for item in value:
                    if isinstance(item, dict) and len(item) == 1:
                        (tag, payload), = item.items()
                        payload = _transform_wrappers(payload, fn)
                        payload = fn(tag, payload)
                        if payload is not None:
                            new_list.append({tag: payload})
                    else:
                        new_list.append(item)
                node[key] = new_list
            elif isinstance(value, dict):
                _transform_wrappers(value, fn)
    return node


def replace_motor_digests_with_ids(compact: dict, id_by_digest: dict) -> dict:
    """Swap every motor <digest> leaf for a <motor_id> leaf (same position).

    Motors without a digest leaf (resolution falls back to properties) are
    left untouched.  Raises when a digest has no ID: every dataset digest must
    be in the lookup.
    """
    out = copy.deepcopy(compact)

    def fn(tag: str, payload: Any) -> Any:
        if tag != "motor" or not isinstance(payload, dict):
            return payload
        kids = payload.get("children")
        if not isinstance(kids, list):
            return payload
        out_kids = []
        for wrapper in kids:
            if isinstance(wrapper, dict) and len(wrapper) == 1 and "digest" in wrapper:
                digest = (wrapper["digest"] or {}).get("value")
                if digest is None:  # <digest> with no value: drop it
                    continue
                motor_id = id_by_digest.get(str(digest))
                if motor_id is None:
                    raise ValueError(f"no motor_id for digest {digest!r}")
                out_kids.append({"motor_id": {"value": motor_id}})
            else:
                out_kids.append(wrapper)
        payload["children"] = out_kids
        return payload

    return _transform_wrappers(out, fn)


def build_stage2_design(compact: dict, id_by_digest: dict) -> dict:
    """The full Stage-2 model-visible state for one row:
    motor digests -> motor ids, preset blocks, cosmetic leaves and the
    simulation name removed (the approved removals, with the digest leaf
    replaced rather than dropped)."""
    return strip_simulation_name(strip_cosmetic(strip_preset_blocks(
        replace_motor_digests_with_ids(compact, id_by_digest))))


# --------------------------------------------------------------------------
# expanded-tree restore (from_compact side, back to digests)
# --------------------------------------------------------------------------

def restore_motor_digests(tree: dict, digest_by_id: dict) -> dict:
    """Replace every <motor_id> element of an expanded parameter tree with the
    <digest> element it stands for.  In place; returns tree.

    ``tree`` is the from_compact output shape (``design["parameter_tree"]``):
    ``{tag, attrs, text, children}`` nodes.  This is the restore half of the
    round trip a JSON-to-.ork converter performs: model-visible ``motor_id``
    in, digest back out through ``final/motor_lookup.json``."""
    def rec(node: dict) -> None:
        kids = node.get("children")
        if not isinstance(kids, list):
            return
        for i, child_node in enumerate(kids):
            if not isinstance(child_node, dict):
                continue
            if child_node.get("tag") == "motor_id":
                motor_id = child_node.get("text")
                digest = digest_by_id.get(str(motor_id))
                if digest is None:
                    raise ValueError(f"motor id {motor_id!r} not in the lookup")
                kids[i] = {"tag": "digest", "attrs": {}, "text": digest,
                           "children": []}
            else:
                rec(child_node)

    rec(tree)
    return tree


# --------------------------------------------------------------------------
# parachute preset fix (explicit non-hash values from the as-is load dump)
# --------------------------------------------------------------------------

def _design_parachutes(rocket: dict) -> list[dict]:
    """Parachute payloads in document order (walks <subcomponents>)."""
    out = []

    def visit(node: dict) -> None:
        kids = node.get("children")
        if not isinstance(kids, list):
            return
        for wrapper in kids:
            if not (isinstance(wrapper, dict) and len(wrapper) == 1):
                continue
            (tag, payload), = wrapper.items()
            if tag == "parachute":
                out.append(payload)
            visit(payload)

    visit(rocket)
    return out


def _child_index(payload: dict, tag: str) -> int | None:
    kids = payload.get("children") or []
    for i, wrapper in enumerate(kids):
        if isinstance(wrapper, dict) and len(wrapper) == 1 and tag in wrapper:
            return i
    return None


def add_explicit_preset_overrides(design: dict,
                                  dump_rows: list[dict]) -> tuple[dict, list[str]]:
    """Write preset-supplied override values explicitly (deep copy).

    A digest-identified component preset can apply a mass override at load
    time even when the design carries no override leaf.  Preset blocks are
    removed in Stage 2, so for every parachute whose AS-IS load shows a mass
    override while the design has no explicit leaf, the resolved numbers from
    the as-is load dump are written into the design as ordinary
    ``<overridemass>`` / ``<overridesubcomponentsmass>`` leaves (and the CG
    pair analogously).  The same applies to a parachute packed length that
    the preset replaces at load: when the as-is load resolves a different
    ``getLength`` than the design's explicit ``<packedlength>`` leaf, that
    leaf is set to the loaded value (the leaf itself always stays an
    ordinary, visible design value).  Values are read from the dump, never
    invented; the load check verifies the result loads identically.

    Returns (design, fixed) with fixed naming the component kinds touched."""
    out = copy.deepcopy(design)
    fixed: list[str] = []
    rocket = None
    for wrapper in out.get("openrocket", {}).get("children", []):
        if isinstance(wrapper, dict) and "rocket" in wrapper:
            rocket = wrapper["rocket"]
    if rocket is None:
        return out, fixed

    chutes = _design_parachutes(rocket)
    dump_chutes = [row for row in dump_rows if row.get("cls") == "Parachute"]
    if len(chutes) != len(dump_chutes):
        return out, fixed  # cannot align: the load check decides this pair's fate

    for chute, row in zip(chutes, dump_chutes):
        loaded = row.get("loaded") or {}
        kids = chute.get("children") or []

        def has(tag: str) -> bool:
            return any(isinstance(w, dict) and len(w) == 1 and tag in w
                       for w in kids)

        # insert right after the position/axialoffset leaf, matching the
        # canonical leaf order used across the dataset
        at = _child_index(chute, "position")
        if at is None:
            at = _child_index(chute, "axialoffset")
        at = (at + 1) if at is not None else 0

        chute_fixed = False
        if loaded.get("isMassOverridden") and not has("overridemass"):
            mass = loaded.get("getOverrideMass")
            if mass is not None:
                kids.insert(at, {"overridemass": {"value": mass}})
                kids.insert(at + 1, {"overridesubcomponentsmass":
                                     {"value": False}})
                at += 2
                chute_fixed = True
        if loaded.get("isCGOverridden") and not has("overridecg"):
            cgx = loaded.get("getOverrideCGX")
            if cgx is not None:
                kids.insert(at, {"overridecg": {"value": cgx}})
                kids.insert(at + 1, {"overridesubcomponentscg":
                                     {"value": False}})
                chute_fixed = True
        # preset-supplied packed length: when re-applying the preset at load
        # resolves a different length than the stored explicit leaf (only
        # happens when the preset database's value differs from the value
        # the original author's OpenRocket wrote into the .ork), the Stage-2
        # design must carry the loaded value explicitly or it loads to a
        # (sub-ulp) different rocket.  Update only an existing leaf; a leaf
        # that already agrees stays untouched.
        loaded_length = loaded.get("getLength")
        idx = _child_index(chute, "packedlength")
        if loaded_length is not None and idx is not None:
            leaf = kids[idx]["packedlength"]
            if isinstance(leaf, dict) and leaf.get("value") != loaded_length:
                leaf["value"] = loaded_length
                chute_fixed = True
        if chute_fixed:
            fixed.append("parachute")
        chute["children"] = kids
    return out, fixed


def apply_stage2_and_fix(compact: dict, id_by_digest: dict,
                         as_is_rows: list[dict]) -> tuple[dict, list[str]]:
    """Full Stage-2 compact state plus the explicit preset-override fix.

    Returns (stage2_compact, fixes) with fixes naming the component kinds
    that received explicit override leaves."""
    stage2 = build_stage2_design(compact, id_by_digest)
    return add_explicit_preset_overrides(stage2, as_is_rows)
