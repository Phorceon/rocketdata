#!/usr/bin/env python3
"""Headless digest/preset removal check for the compact SFT designs (NO flights).

For every unique (file, sim) pair in the Stage-1 compact rows this script:

  1. rebuilds six .ork files purely from the compact design (from_compact +
     build_ork, no source .ork access):
       doc_a  : compact exactly as Stage 1 wrote it (digests + presets kept);
       doc_b0 : compact with motor <digest> elements removed (preset blocks
                and their digest attrs untouched);
       doc_b1 : compact with motor <digest> elements AND preset digest attrs
                removed (preset blocks themselves kept);
       doc_b2 : doc_b1 with the whole <preset> blocks removed as well;
       doc_b3 : doc_b2 with the cosmetic <color>/<linestyle>/<designtype>
                leaves and the selected <simulation><name> removed as well
                (the full Stage-2 removal state);
       doc_c  : the full Stage-2 MODEL-VISIBLE state -- motor digests replaced
                by readable <motor_id> values (sft_compact_motor_ids), preset
                blocks, cosmetic leaves and the simulation name removed, and
                preset-supplied parachute overrides written out explicitly --
                with every motor_id restored to its digest through
                final/motor_lookup.json before the document is built.  This is
                exactly the round trip a JSON-to-.ork converter will perform.
  2. loads each document headlessly (GeneralRocketLoader only; nothing is
     simulated) and compares loaded state against doc_a:
       B0 pass: per-component loaded snapshot multiset identical INCLUDING the
                resolved component preset identity and the resolved motor;
                isolates whether motor thrust-curve digests alone are needed;
       B1 pass: same criterion after also removing the preset digest attrs;
       B2 pass: same comparison with preset identity excluded (removing the
                catalog reference is expected to unset it; geometry,
                materials and motors must still be identical);
       B3 pass: B2's criterion for the full Stage-2 removal state;
       C  pass: B2's criterion for the motor_id round trip of the FINAL row
                state (the gate a row must pass to enter the main files).
  3. dumps per-component resolved geometry (lengths, radii, relative and
     absolute axial positions, DFS order with parent indices) from the loaded
     document whose removal state the final dataset uses, so the Stage-2
     reasoning generator can narrate fit checks from resolved numbers instead
     of re-interpreting XML axial semantics.

If B1 passes the pair's digests are removable; if B1 fails, at least one
digest is required and the row must stay out of the digest-free main file
(B0 vs B1 failure attribution says whether a motor or a preset digest is the
required one).  If B2 passes the preset blocks are removable too.  If B3
passes the cosmetic leaves and the simulation name are removable too.  C
passing means the model-visible motor_id design, converted back to digests
through the lookup, loads identically to the as-is design.

NO flight simulation runs here: documents are loaded and inspected only.
Writes digest_check.json under the output dir.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import or_headless as oh  # noqa: E402
from scripts.sft_compact_design import from_compact  # noqa: E402
from scripts.sft_compact_motor_ids import (  # noqa: E402
    add_explicit_preset_overrides,
    apply_stage2_and_fix,
    build_motor_lookup,
    build_stage2_design,
    collect_dataset_motor_entries,
    restore_motor_digests,
)
from scripts.sft_compact_removals import (  # noqa: E402
    strip_cosmetic,
    strip_digests,
    strip_motor_digests_only,
    strip_preset_blocks,
    strip_simulation_name,
)
from scripts.sft_full_fidelity_extract import build_ork  # noqa: E402
from scripts.sft_full_fidelity_support.runtime import snapshot  # noqa: E402

STAGE_DIR = REPO_ROOT / "sftgen" / "out" / "scratch" / "sft_compact_20261103"

# Loaded-snapshot getters: geometry, materials, overrides, placement.
# getComponentPreset is handled separately as an explicit preset identity
# (str(ComponentPreset) is a Java object id, not a stable value).
SNAPSHOT_GETTERS = [
    "getLength",
    "getOuterRadius",
    "getInnerRadius",
    "getThickness",
    "getForeRadius",
    "getAftRadius",
    "isForeRadiusAutomatic",
    "isAftRadiusAutomatic",
    "getShapeType",
    "getShapeParameter",
    "getAftShoulderLength",
    "getAftShoulderRadius",
    "getAftShoulderThickness",
    "isAftShoulderCapped",
    "isFilled",
    "getMaterial",
    "getFinish",
    "getAxialMethod",
    "getAxialOffset",
    "getPosition",
    "getAbsolutePosition",
    "getComponentMass",
    "getComponentCG",
    "isMassOverridden",
    "isCGOverridden",
    "getOverrideMass",
    "getOverrideCGX",
    "getMass",
    "getRadius",
    "getRadialPosition",
    "getRadialDirection",
    "isRadiusAutomatic",
    "isOuterRadiusAutomatic",
    "isInnerRadiusAutomatic",
    "getInstanceCount",
    "getAngleMethod",
    "getAngleOffset",
    "getInstanceSeparation",
    "getFinPoints",
    "getFinCount",
    "getCrossSection",
    "getCantAngle",
    "getTabHeight",
    "getTabLength",
    "getTabOffset",
    "getFilletRadius",
    "getFilletMaterial",
    "getDiameter",
    "getCD",
    "isCDAutomatic",
    "getLineCount",
    "getLineLength",
    "isLineLengthAutomatic",
    "getLineMaterial",
    "isMotorMount",
    "getMotorOverhang",
    "getClusterConfiguration",
]


def preset_identity(comp: Any) -> str | None:
    """Stable catalog identity of a loaded component preset, or None."""
    try:
        preset = comp.getComponentPreset()
    except Exception:
        return None
    if preset is None:
        return None
    try:
        return "|".join([
            str(preset.getType()),
            str(preset.getManufacturer().getDisplayName()),
            str(preset.getPartNo()),
        ])
    except Exception:
        return "unreadable-preset"


def _is_mount(comp: Any) -> bool:
    try:
        return bool(comp.isMotorMount())
    except Exception:
        return False


def _motor_state(comp: Any, fcid_str: str, Fcid: Any) -> dict[str, Any] | None:
    try:
        config = comp.getMotorConfig(Fcid(fcid_str))
    except Exception:
        return None
    out: dict[str, Any] = {}
    try:
        out["ejection_delay"] = str(config.getEjectionDelay())
    except Exception:
        out["ejection_delay"] = None
    try:
        motor = config.getMotor()
        out["designation"] = str(motor.getDesignation())
        out["manufacturer"] = str(motor.getManufacturer().getDisplayName())
        out["digest"] = str(motor.getDigest())
        out["diameter_m"] = float(motor.getDiameter())
        out["length_m"] = float(motor.getLength())
    except Exception as exc:
        out["motor_error"] = str(exc)
    return out


def component_rows(doc: Any, fcid_str: str) -> list[dict[str, Any]]:
    """DFS component dump with parent indices and resolved geometry."""
    comps: list[Any] = []
    parents: list[int] = []

    def rec(node: Any, parent: int) -> None:
        for child in node.getChildren():
            idx = len(comps)
            comps.append(child)
            parents.append(parent)
            rec(child, idx)

    rec(doc.getRocket(), -1)
    import jpype
    Fcid = jpype.JClass("info.openrocket.core.rocketcomponent.FlightConfigurationId")
    rows: list[dict[str, Any]] = []
    for idx, (comp, parent) in enumerate(zip(comps, parents)):
        snap = snapshot(comp, SNAPSHOT_GETTERS)
        snap.pop("getComponentPreset", None)
        motor = _motor_state(comp, fcid_str, Fcid) if _is_mount(comp) else None
        rows.append({
            "index": idx,
            "parent_index": parent,
            "cls": str(comp.getClass().getSimpleName()),
            "loaded": snap,
            "preset": preset_identity(comp),
            "motor": motor,
        })
    return rows


def multiset(rows: list[dict[str, Any]], with_preset: bool) -> Counter:
    counter: Counter = Counter()
    for row in rows:
        key = json.dumps({
            "cls": row["cls"],
            "loaded": row["loaded"],
            "preset": row["preset"] if with_preset else None,
            "motor": row["motor"],
        }, sort_keys=True, default=str)
        counter[key] += 1
    return counter


def diff_multisets(a: Counter, b: Counter) -> list[dict[str, Any]]:
    """Structured differences between two loaded-component multisets.

    Each entry names the component class, the resolved preset identity, the
    resolved motor digest/designation (when present) and carries the full
    snapshot key, so a failure can be attributed to the exact motor or preset
    whose resolution changed.
    """
    entries: list[dict[str, Any]] = []
    for direction, counter in (("missing", a - b), ("extra", b - a)):
        for key, count in counter.items():
            try:
                parsed = json.loads(key)
            except ValueError:
                parsed = {"raw": key}
            entries.append({
                "direction": direction,
                "count": count,
                "cls": parsed.get("cls"),
                "preset": parsed.get("preset"),
                "motor": (parsed.get("motor") or {}).get("motor") if isinstance(parsed.get("motor"), dict) else parsed.get("motor"),
                "motor_state": parsed.get("motor"),
                "key": key,
            })
    return entries


def check_pair(pair_key: str, compact: dict, workdir: Path,
               id_by_digest: dict, digest_by_id: dict) -> dict[str, Any]:
    """B0/B1/B2/B3 removal checks + C motor_id round trip + geometry dump."""
    designs = {
        "a": from_compact(copy.deepcopy(compact)),
        "b0": from_compact(strip_motor_digests_only(copy.deepcopy(compact))),
        "b1": from_compact(strip_digests(copy.deepcopy(compact))),
        "b2": from_compact(strip_preset_blocks(strip_digests(copy.deepcopy(compact)))),
        "b3": from_compact(strip_simulation_name(strip_cosmetic(
            strip_preset_blocks(strip_digests(copy.deepcopy(compact)))))),
    }
    paths = {}
    for variant, design in designs.items():
        path = workdir / f"{_fs_safe(pair_key)}_{variant}.ork"
        build_ork(design, path)
        paths[variant] = path

    helper = oh._helper()
    docs = {variant: helper.load_doc(str(path)) for variant, path in paths.items()}

    rows = {}
    for variant, doc in docs.items():
        fcid = str(doc.getSimulation(0).getFlightConfigurationId())
        rows[variant] = component_rows(doc, fcid)

    # Variant c: the final model-visible state (motor_id, no preset blocks,
    # no cosmetics, no simulation name, explicit preset overrides) converted
    # back to digests through the lookup, then loaded.
    stage2, c_fixed = apply_stage2_and_fix(copy.deepcopy(compact),
                                           id_by_digest, rows["a"])
    design_c = from_compact(stage2)
    restore_motor_digests(design_c["parameter_tree"], digest_by_id)
    path_c = workdir / f"{_fs_safe(pair_key)}_c.ork"
    build_ork(design_c, path_c)
    doc_c = helper.load_doc(str(path_c))
    fcid_c = str(doc_c.getSimulation(0).getFlightConfigurationId())
    rows["c"] = component_rows(doc_c, fcid_c)
    paths["c"] = path_c

    results: dict[str, Any] = {"pair": pair_key, "preset_fix_applied": c_fixed}

    def compare(variant: str, with_preset: bool) -> None:
        diffs = diff_multisets(multiset(rows["a"], with_preset=True),
                               multiset(rows[variant], with_preset=with_preset))
        results[f"{variant}_pass"] = not diffs
        results[f"{variant}_diff_count"] = len(diffs)
        results[f"{variant}_diffs"] = diffs[:40]

    compare("b0", with_preset=True)
    compare("b1", with_preset=True)
    compare("b2", with_preset=False)
    compare("b3", with_preset=False)
    compare("c", with_preset=False)

    # Resolved-geometry dump from the most-stripped passing variant: that is
    # the state the final dataset's design JSON will be in.
    for variant in ("c", "b3", "b2", "b1"):
        if results[f"{variant}_pass"]:
            dump_variant = variant
            break
    else:
        dump_variant = "a"
    results["dump_variant"] = dump_variant
    results["components"] = rows[dump_variant]
    results["component_count"] = len(rows[dump_variant])

    for path in paths.values():
        path.unlink(missing_ok=True)
    return results


def _fs_safe(key: str) -> str:
    return "".join(c if (c.isalnum() or c in "-_.") else "_" for c in key)


def iter_jsonl(path: Path):
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(STAGE_DIR / "digest_check.json"))
    parser.add_argument("--limit", type=int, default=0, help="debug: only first N pairs")
    args = parser.parse_args()

    pairs: dict[str, dict] = {}
    for name in ("train", "test"):
        for row in iter_jsonl(STAGE_DIR / "compact" / f"{name}_rows.jsonl"):
            key = f"{row['file']}|{row['sim']}"
            pairs.setdefault(key, row["compact"])

    if args.limit:
        pairs = dict(list(pairs.items())[: args.limit])

    # Motor lookup over the FULL OpenRocket motor database, with dataset-side
    # digests (stale design digests, attachment thrust curves) included.
    db = json.loads((STAGE_DIR / "motor_db_full.json").read_text())
    ds_entries = collect_dataset_motor_entries(STAGE_DIR)
    lookup = build_motor_lookup(db, ds_entries)
    id_by_digest = {v["digest"]: k for k, v in lookup.items()}
    digest_by_id = {k: v["digest"] for k, v in lookup.items()}
    lookup_path = STAGE_DIR / "final" / "motor_lookup.json"
    lookup_path.parent.mkdir(parents=True, exist_ok=True)
    lookup_path.write_text(json.dumps(lookup, indent=1, sort_keys=True) + "\n")
    print(f"motor lookup: {len(lookup)} ids over {len(set(id_by_digest.values()))} digests -> {lookup_path}")

    results: dict[str, Any] = {"method": (
        "static: .ork rebuilt from compact (as-is / digests removed / digests+presets "
        "removed), loaded headlessly, per-component loaded snapshots compared as "
        "multisets; B1 requires preset identity + resolved motor identical, B2 "
        "requires geometry + resolved motor identical; C restores motor ids to "
        "digests through final/motor_lookup.json before loading. NO simulation ran."),
        "motor_lookup_size": len(lookup),
        "pairs": {},
    }
    with tempfile.TemporaryDirectory(prefix="digestchk_") as tmp:
        workdir = Path(tmp)
        for i, (key, compact) in enumerate(sorted(pairs.items()), 1):
            try:
                results["pairs"][key] = check_pair(
                    key, compact, workdir, id_by_digest, digest_by_id)
            except Exception as exc:
                results["pairs"][key] = {
                    "error": f"{exc.__class__.__name__}: {exc}",
                    "b0_pass": False,
                    "b1_pass": False,
                    "b2_pass": False,
                    "b3_pass": False,
                    "c_pass": False,
                    "dump_variant": "a",
                    "components": [],
                }
            entry = results["pairs"][key]
            note = f" ERR={entry['error']}" if "error" in entry else ""
            print(f"[{i}/{len(pairs)}] {key}: b0={entry['b0_pass']} "
                  f"b1={entry['b1_pass']} b2={entry['b2_pass']} "
                  f"b3={entry['b3_pass']} c={entry['c_pass']}{note}", flush=True)

    n_b0 = sum(1 for v in results["pairs"].values() if v["b0_pass"])
    n_b1 = sum(1 for v in results["pairs"].values() if v["b1_pass"])
    n_b2 = sum(1 for v in results["pairs"].values() if v["b2_pass"])
    n_b3 = sum(1 for v in results["pairs"].values() if v["b3_pass"])
    n_c = sum(1 for v in results["pairs"].values() if v["c_pass"])
    print(f"pairs: {len(results['pairs'])}  b0: {n_b0}  b1: {n_b1}  b2: {n_b2}  "
          f"b3: {n_b3}  c: {n_c}")

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=1, default=str) + "\n")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
