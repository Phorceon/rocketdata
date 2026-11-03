"""Compact design JSON for the SFT dataset repair (Stage 1, flight-free).

Converts the full-fidelity design JSON produced by
``scripts/sft_full_fidelity_extract.py`` (the ``<design>`` payload of the
candidate rows in ``sft_full_fidelity_20261102``) into a compact, readable,
deterministic JSON that a model can emit, and back:

    full design dict  --to_compact-->  compact dict
    compact dict      --from_compact--> full design dict (rebuildable via
                                        sft_full_fidelity_extract.build_ork)

Scope (per the Stage-1 brief, as amended): keep every input of the SELECTED
simulation that changes the physics, drop everything else, and never change a
value.  NO flight simulation is run anywhere in this module.

Compact format
--------------
The full design's ``parameter_tree`` is a generic OpenRocket XML tree of
``{tag, attrs, text, children}`` wrappers.  The compact format restyles that
tree with real engineering key names AND exact sibling order:

* an element becomes a JSON object with up to three keys: ``attrs`` (the
  element's attributes), ``value`` (the element's text content), and
  ``children`` (its child elements);
* ``children`` is a JSON array of single-key objects, one per child element in
  document order, the key being the child's XML tag (``{"length": {...}}``,
  ``{"nosecone": {...}}``, ...); repeated tags simply appear multiple times;
* SIBLING ORDER IS PRESERVED EXACTLY: OpenRocket resolves relative placements
  (AxialMethod AFTER/TOP, ...) from sibling document order, so the order is
  physics and is never regrouped by tag;
* XML text/attribute strings are typed ONLY when the exact spelling is
  canonical for the parsed value (``"true"``/``"false"``, or a number whose
  Python ``repr`` reproduces the string exactly, e.g. ``"0.1016"`` -> 0.1016,
  ``"3"`` -> 3).  Any other spelling is kept as a string verbatim, so
  ``from_compact`` reproduces the original XML text exactly.  Values are never
  rounded.

The top level is::

    {"openrocket": {"attrs": {...}, "children": [ ... ]},
     "attachments": {"thrustcurves/<digest>.rse": {"data_base64": "..."}}
    }

``attachments`` is present only when the source bundle carried engineering
attachments (custom motor thrust curves, which OpenRocket loads from the bundle).
Cosmetic bundle entries (textures/decals, previews) are dropped because every
``<decal>``/appearance reference that used them is dropped too; dropping them is
reported by the Stage-1 runner, never silent.

Removals (documented; their physics-neutrality for the selected configuration
is verified statically by the Stage-1 runner)
----------------------------------------------------------------
* full-design keys that are audit/provenance only: ``component_index``,
  ``simulation_options_snapshot``, ``reconstruction_contract``, plus any source
  file name or content hash;
* all simulations except the selected one;
* all non-selected motor/deployment/separation/ignition configurations and
  their motors; the selected configuration's id becomes the deterministic
  placeholder ``cfg0`` everywhere (a valid, stable FlightConfigurationId);
* cosmetic XML subtrees: ``appearance``, ``insideappearance`` (and their
  ``paint``/``shine``/``color``/``linestyle``/``decal`` children),
  ``photostudio``, ``docprefs``;
* document metadata: ``rocket/comment``, ``rocket/designer``,
  ``rocket/revision``, ``openrocket@creator``, ``simulation@status``;
* instance identity: every ``<id>`` element (loader-assigned UUIDs) and every
  component ``<name>`` (display only).  The single exception is the ``<name>``
  directly under the selected ``<simulation>``, which is the key
  ``or_headless.simulate(ork, sim_name)`` looks up and is therefore kept.

Kept (physics): exact sibling order, all component geometry including freeform
``finpoints``, placement (``position``/``axialoffset``/``radiusoffset``/
``angleoffset`` type + offset), materials (density, type, group, text) incl.
fillet/line materials, mass/CG/CD overrides, finish, cluster/instance settings,
stages and separation configurations, the active motor (manufacturer,
designation, digest, diameter, length, delay), motor/deployment/separation/
ignition configurations of the selected flight configuration, stage active
flags, presets (catalog identity incl. digest used to resolve the preset), and
the selected simulation's launch conditions.

Motor and preset ``digest`` fields are intentionally kept: they identify the
exact thrust curve / catalog preset inside OpenRocket's databases and are
required to resolve the same physics on rebuild (they are content identities,
not source-file hashes).  The Stage-1 loader-snapshot check statically verifies
the rebuilt file resolves identical materials, geometry and motors.
"""

from __future__ import annotations

import base64
import hashlib
import json
import math
import re
from typing import Any

from scripts.sft_full_fidelity_support.xml_tree import (
    find_simulation_by_name,
    simulation_config_id,
)

SCHEMA_VERSION = "full-fidelity-1.0"
CONFIGID_PLACEHOLDER = "cfg0"
RESERVED_KEYS = ("attrs", "value", "children")

# Documented removals (see module docstring).
REMOVED_TAGS = {
    "appearance",
    "insideappearance",
    "decal",
    "photostudio",
    "docprefs",
    "comment",
    "designer",
    "revision",
    "id",
    "name",
}
KEEP_NAME_PARENT_TAGS = {"simulation"}  # <simulation><name> is the lookup key
REMOVED_ATTRS = {
    "openrocket": {"creator"},
    "simulation": {"status"},
}
# Elements keyed by a flight-configuration id; only the selected config is kept.
CONFIGID_ELEMENTS = {
    "motorconfiguration",
    "motor",
    "deploymentconfiguration",
    "separationconfiguration",
    "ignitionconfiguration",
}
# bundle_entries names kept (engineering) vs dropped (cosmetic)
ATTACHMENT_PHYSICS_PREFIX = ("thrustcurves/",)

_INT_RE = re.compile(r"-?\d+\Z")


class CompactError(RuntimeError):
    """The design cannot be converted without losing selected-config physics."""


# --------------------------------------------------------------------------
# value typing (exact-spelling round trip only; never rounds)
# --------------------------------------------------------------------------

def type_text(s: str) -> Any:
    """Type an XML text/attribute string, preserving the exact value.

    Only canonical spellings are converted: "true"/"false", integers whose
    str() reproduces the input, and floats whose repr() reproduces the input.
    Everything else stays a string so from_compact restores it verbatim.
    """
    if s == "true":
        return True
    if s == "false":
        return False
    if _INT_RE.match(s):
        if str(int(s)) == s:
            return int(s)
        return s
    try:
        f = float(s)
    except ValueError:
        return s
    if math.isfinite(f) and repr(f) == s:
        return f
    return s


def untype_value(v: Any) -> str:
    """Inverse of type_text for values it may have produced."""
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return repr(v)
    return str(v)


def dump_compact_json(compact: dict) -> str:
    """Exact serialization used for the model-facing design JSON."""
    return json.dumps(compact, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


# --------------------------------------------------------------------------
# to_compact
# --------------------------------------------------------------------------

def _kept_attrs(tag: str, attrs: dict | None) -> dict | None:
    if not attrs:
        return None
    drop = REMOVED_ATTRS.get(tag)
    out = {k: type_text(v) for k, v in attrs.items()
           if not (drop and k in drop)}
    return out or None


def _configid_of(node: dict) -> str | None:
    cfg = (node.get("attrs") or {}).get("configid")
    return str(cfg) if cfg is not None else None


def _add_child(children: list, tag: str, payload: dict) -> None:
    if tag in RESERVED_KEYS:
        raise CompactError(f"element tag {tag!r} collides with a reserved compact key")
    children.append({tag: payload})


def _compact_node(node: dict, *, fcid: str | None, parent_tag: str | None) -> dict | None:
    tag = node["tag"]
    if tag in REMOVED_TAGS and not (tag == "name" and parent_tag in KEEP_NAME_PARENT_TAGS):
        return None
    if tag == "flightdata":
        return None  # cached flight results; never an input

    if tag == "simulation":
        return _compact_selected_simulation(node)

    if tag in CONFIGID_ELEMENTS and fcid is not None:
        node_cfg = _configid_of(node)
        if node_cfg != fcid:
            return None  # non-selected configuration (or motor): dropped

    out: dict[str, Any] = {}
    attrs = _kept_attrs(tag, node.get("attrs"))
    if tag in CONFIGID_ELEMENTS:
        attrs = dict(attrs or {})
        attrs["configid"] = CONFIGID_PLACEHOLDER
    if attrs:
        out["attrs"] = attrs

    text = node.get("text")
    if text is not None:
        out["value"] = type_text(text)

    kids: list = []
    for child in node.get("children") or []:
        compact_child = _compact_node(child, fcid=fcid, parent_tag=tag)
        if compact_child is not None:
            _add_child(kids, child["tag"], compact_child)
    if kids:
        out["children"] = kids
    return out


def _compact_selected_simulation(sim_node: dict) -> dict:
    """Compact one <simulation> element, placeholdering its conditions configid."""
    out: dict[str, Any] = {}
    kids: list = []
    for child in sim_node.get("children") or []:
        tag = child["tag"]
        if tag == "flightdata":
            continue
        compact_child = _compact_node(child, fcid=None, parent_tag=sim_node["tag"])
        if compact_child is not None:
            _add_child(kids, tag, compact_child)
    # conditions>configid is the simulation's own flight configuration id:
    # replace the original uuid text with the deterministic placeholder.
    for wrapper in kids:
        if "conditions" not in wrapper:
            continue
        conditions = wrapper["conditions"]
        if "children" in conditions:
            for item in conditions["children"]:
                if "configid" in item:
                    item["configid"] = {"value": CONFIGID_PLACEHOLDER}
    out["children"] = kids
    return out


def _physics_attachments(bundle_entries: dict | None) -> tuple[dict[str, dict], list[str]]:
    """Split bundle entries into compact attachments and dropped cosmetic names."""
    kept: dict[str, dict] = {}
    dropped: list[str] = []
    for name, meta in (bundle_entries or {}).items():
        if name.startswith(ATTACHMENT_PHYSICS_PREFIX):
            data = base64.b64decode(meta["data"], validate=True)
            kept[name] = {"data_base64": base64.b64encode(data).decode("ascii")}
        else:
            dropped.append(name)
    return kept, sorted(dropped)


def to_compact(full_design: dict) -> dict:
    """Compact a full-fidelity design dict for the SELECTED simulation only."""
    tree = full_design.get("parameter_tree")
    if not tree or tree.get("tag") != "openrocket":
        raise CompactError("design has no openrocket parameter_tree")
    selected = full_design.get("selected_simulation") or {}
    sim_name = selected.get("name")
    if not sim_name:
        raise CompactError("design has no selected_simulation name")

    # The selected simulation inside the tree provides the flight config id that
    # keys every motor/deployment/separation/ignition configuration.
    _, sim_node = find_simulation_by_name(tree, sim_name)  # raises KeyError if absent
    fcid = simulation_config_id(sim_node)
    if not fcid:
        raise CompactError(
            f"selected simulation {sim_name!r} has no conditions>configid; "
            "cannot identify its flight configuration"
        )

    root_children: list = []
    for child in tree.get("children") or []:
        tag = child["tag"]
        if tag == "simulations":
            # only the selected simulation survives
            kept_sim = _compact_node(sim_node, fcid=None, parent_tag="simulations")
            _add_child(root_children, "simulations", {"children": [
                {"simulation": kept_sim}]})
            continue
        # rocket and other top-level subtrees go through the generic rules
        kept = _compact_node(child, fcid=fcid, parent_tag=None)
        if kept is not None:
            _add_child(root_children, tag, kept)

    root_attrs = _kept_attrs("openrocket", tree.get("attrs"))
    openrocket: dict[str, Any] = {}
    if root_attrs:
        openrocket["attrs"] = root_attrs
    openrocket["children"] = root_children

    compact: dict[str, Any] = {"openrocket": openrocket}
    attachments, _dropped = _physics_attachments(full_design.get("bundle_entries"))
    if attachments:
        compact["attachments"] = attachments
    return compact


# --------------------------------------------------------------------------
# from_compact
# --------------------------------------------------------------------------

def _expand_item(item: Any) -> tuple[str, dict]:
    if not isinstance(item, dict) or len(item) != 1:
        raise CompactError(
            f"each child must be a single-key object {{tag: node}}, got: {str(item)[:80]}")
    (tag, payload), = item.items()
    return tag, payload


def _expand_node(tag: str, obj: Any) -> dict:
    if not isinstance(obj, dict):
        raise CompactError(f"compact node for <{tag}> must be an object, got {type(obj).__name__}")
    attrs = obj.get("attrs")
    node: dict[str, Any] = {
        "tag": tag,
        "attrs": {k: untype_value(v) for k, v in attrs.items()} if attrs else {},
        "text": None,
        "children": [],
    }
    if "value" in obj:
        node["text"] = untype_value(obj["value"])
    for item in obj.get("children") or []:
        child_tag, payload = _expand_item(item)
        node["children"].append(_expand_node(child_tag, payload))
    return node


def from_compact(compact: dict) -> dict:
    """Rebuild a full-fidelity design dict (parameter_tree + bundle_entries).

    The result loads and rebuilds through
    ``scripts.sft_full_fidelity_extract.build_ork``; config ids are all the
    deterministic placeholder ``cfg0``.
    """
    openrocket = compact.get("openrocket")
    if not isinstance(openrocket, dict):
        raise CompactError("compact design has no openrocket root")

    tree = _expand_node("openrocket", openrocket)

    bundle = {}
    for name, meta in (compact.get("attachments") or {}).items():
        data = base64.b64decode(meta["data_base64"], validate=True)
        bundle[name] = {
            "encoding": "base64",
            "sha256": hashlib.sha256(data).hexdigest(),
            "data": base64.b64encode(data).decode("ascii"),
        }

    version = (openrocket.get("attrs") or {}).get("version")
    return {
        "schema_version": SCHEMA_VERSION,
        "openrocket_version": untype_value(version) if version is not None else None,
        "ork_container": {"format": "zip"},
        "parameter_tree": tree,
        "bundle_entries": bundle,
    }


# --------------------------------------------------------------------------
# static equivalence check (NO flight simulation anywhere)
# --------------------------------------------------------------------------

def normalize_tree(parameter_tree: dict, sim_name: str) -> dict:
    """Apply the documented removals/placeholdering directly to a parameter tree.

    Independent of to_compact/from_compact: the Stage-1 static check compares
    this normalization against the compact round trip.  Only the removal
    constants above are shared (they are the documented physics judgment).
    """
    kept_tree = {
        "tag": parameter_tree["tag"],
        "attrs": {k: v for k, v in (parameter_tree.get("attrs") or {}).items()
                  if k not in REMOVED_ATTRS.get(parameter_tree["tag"], set())},
        "text": parameter_tree.get("text"),
        "children": [],
    }
    _, sim_node = find_simulation_by_name(parameter_tree, sim_name)
    fcid = simulation_config_id(sim_node)
    if not fcid:
        raise CompactError(f"selected simulation {sim_name!r} has no conditions>configid")

    def keep(node: dict, parent_tag: str | None) -> dict | None:
        tag = node["tag"]
        if tag in REMOVED_TAGS and not (tag == "name" and parent_tag in KEEP_NAME_PARENT_TAGS):
            return None
        out = {
            "tag": tag,
            "attrs": {k: v for k, v in (node.get("attrs") or {}).items()
                      if k not in REMOVED_ATTRS.get(tag, set())},
            "text": node.get("text"),
            "children": [],
        }
        if tag in CONFIGID_ELEMENTS:
            cfg = out["attrs"].get("configid")
            if cfg is None or cfg != fcid:
                return None
            out["attrs"]["configid"] = CONFIGID_PLACEHOLDER
        if tag == "configid" and parent_tag == "conditions":
            out["text"] = CONFIGID_PLACEHOLDER  # the selected sim's own config id
        for child in node.get("children") or []:
            if child["tag"] == "flightdata":
                continue
            if tag == "simulations" and child["tag"] == "simulation":
                sim_child_name = next((g.get("text") for g in child.get("children") or []
                                       if g["tag"] == "name"), None)
                if sim_child_name != sim_name:
                    continue  # non-selected simulation: dropped
            kept_child = keep(child, tag)
            if kept_child is not None:
                out["children"].append(kept_child)
        return out

    for child in parameter_tree.get("children") or []:
        kept = keep(child, kept_tree["tag"])
        if kept is not None:
            kept_tree["children"].append(kept)
    return kept_tree


def diff_trees(expected: dict, actual: dict, path: str = "") -> list[str]:
    """Exact structural/value differences, INCLUDING sibling order
    (order is physics: relative placements resolve against it)."""
    diffs: list[str] = []
    here = f"{path}/{expected.get('tag')}" if path else f"/{expected.get('tag')}"
    if expected.get("tag") != actual.get("tag"):
        diffs.append(f"{here}: tag {expected.get('tag')!r} != {actual.get('tag')!r}")
        return diffs
    exp_attrs, act_attrs = expected.get("attrs") or {}, actual.get("attrs") or {}
    for k in sorted(set(exp_attrs) | set(act_attrs)):
        if k not in act_attrs:
            diffs.append(f"{here}@{k}: expected {exp_attrs[k]!r}, compact dropped it")
        elif k not in exp_attrs:
            diffs.append(f"{here}@{k}: compact added {act_attrs[k]!r}")
        elif exp_attrs[k] != act_attrs[k]:
            diffs.append(f"{here}@{k}: {exp_attrs[k]!r} != {act_attrs[k]!r}")
    if expected.get("text") != actual.get("text"):
        diffs.append(f"{here}#text: {expected.get('text')!r} != {actual.get('text')!r}")
    exp_kids, act_kids = expected.get("children") or [], actual.get("children") or []
    if len(exp_kids) != len(act_kids):
        exp_tags = [c["tag"] for c in exp_kids]
        act_tags = [c["tag"] for c in act_kids]
        diffs.append(f"{here}: expected {len(exp_kids)} children {exp_tags}, "
                     f"compact round trip has {len(act_kids)} {act_tags}")
        return diffs
    for i, (e, a) in enumerate(zip(exp_kids, act_kids)):
        diffs.extend(diff_trees(e, a, f"{here}/{i}"))
    return diffs


def static_check(full_design: dict) -> dict:
    """Flight-free equivalence gate for one (file, sim) pair.

    Verifies that from_compact(to_compact(design)) preserves every physics
    input of the selected configuration exactly:

    * the parameter tree after the documented removals/placeholdering
      (normalize_tree) is reproduced leaf-for-leaf in exact sibling order,
      with exact values;
    * every kept (thrustcurve) attachment round trips byte-identically;
    * no non-selected simulation or configuration survives.

    Returns {"pass", "differences", "dropped_attachments"}; never simulates.
    """
    selected = (full_design.get("selected_simulation") or {}).get("name")
    if not selected:
        return {"pass": False,
                "differences": ["design has no selected_simulation name"],
                "dropped_attachments": []}
    try:
        compact = to_compact(full_design)
        rebuilt = from_compact(compact)
    except (CompactError, KeyError, ValueError) as exc:
        return {"pass": False,
                "differences": [f"conversion failed: {exc.__class__.__name__}: {exc}"],
                "dropped_attachments": []}

    expected_tree = normalize_tree(full_design["parameter_tree"], selected)
    diffs = diff_trees(expected_tree, rebuilt["parameter_tree"])

    kept_orig, dropped = _physics_attachments(full_design.get("bundle_entries"))
    orig_att = {
        name: base64.b64decode(meta["data_base64"], validate=True)
        for name, meta in kept_orig.items()
    }
    rebuilt_att = {
        name: base64.b64decode(meta["data"], validate=True)
        for name, meta in (rebuilt.get("bundle_entries") or {}).items()
    }
    if set(rebuilt_att) != set(orig_att):
        diffs.append(f"attachments: expected {sorted(orig_att)}, rebuilt {sorted(rebuilt_att)}")
    for name in sorted(set(rebuilt_att) & set(orig_att)):
        if rebuilt_att[name] != orig_att[name]:
            diffs.append(f"attachment {name}: bytes differ after round trip")

    # no non-selected simulation may survive anywhere
    sims_found: list[str] = []

    def count_sims(node: dict) -> None:
        for child in node.get("children") or []:
            if child["tag"] == "simulation":
                sims_found.append(child["tag"])
            count_sims(child)

    count_sims(rebuilt["parameter_tree"])
    if len(sims_found) != 1:
        diffs.append(f"simulations: expected exactly 1 selected simulation, "
                     f"rebuilt has {len(sims_found)}")

    return {"pass": not diffs, "differences": diffs, "dropped_attachments": dropped}
