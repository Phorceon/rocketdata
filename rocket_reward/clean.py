"""The cleaned copy of a design (DESIGN.md section 5).

The model chooses parts, sizes, materials and the motor id. It must not choose
its own physics. Before a design is flown, clean_design() makes a copy in which:

  * every "simulations" block is gone, wherever it sits (the model's own wind,
    launch rail, launch site and time step go with it; the reward writes those)
  * the stability reference is OpenRocket's default ("maximum"), and any
    custom reference length is gone, so a tiny reference cannot inflate the
    stability margin
  * every setting means what OpenRocket will read: a component's parts sit
    in ONE "subcomponents" holder (several holders are merged, in order, as
    OpenRocket would add them), and a setting written twice keeps only its
    LAST copy, the one OpenRocket's loader ends up with. So stage 4 checks
    exactly the values that will be flown.
  * only the flown motor configuration is kept (motors.flown_config_id), with
    the motors and per-configuration settings that use it; a second
    configuration cannot fly a motor stage 3 never saw
  * each motor's maker, designation, diameter, length and digest come from
    the motor table for its motor id, the motor id is written in the table's
    spelling, and any other motor setting is removed
  * the motors of the bottom stage light with no ignition delay
    (_no_wait_on_the_pad): a rocket waiting on the pad must not gain flight time
  * the file format version is the one OpenRocket 24.12 writes
    (ork.FILE_VERSION): the version changes how OpenRocket reads the file
    (below 1.4 it ignores the motor digest), so the model cannot choose it
  * every drag override ("overridecd" and its "overridesubcomponentscd"
    switch) is removed: the drag is the one OpenRocket computes from the
    shape. Mass and balance overrides stay (82% of the reference designs
    weigh their kit parts); stage 5 bounds what they do to the whole rocket
  * every material's density comes from the material table, the way
    OpenRocket's loader reads a material (apply_material_densities)

natural_copy (at the end) gives the same design without its mass and balance
overrides; scoring.py flies it so that stage 5 can bound what they do.

The input tree is never changed. Cleaning a cleaned design changes nothing.
"""
from __future__ import annotations

from typing import Any, Optional

from .limits import KNOWN_COMPONENT_TYPES
from .materials import MaterialTable, UNITS, default_material_table, means_no_material, name_text, slot_type
from .motors import flown_config_id
from .ork import FILE_VERSION
from .tree import (MATERIAL_TAGS, Node, body_of, child_list, children_named, children_of, copy_tree, is_node,
                   java_number, last_text, read_number, rocket_of, stages_of, tag_of, walk_components, walk_nodes)

REFERENCE_TYPE = "maximum"  # OpenRocket's default: the widest part of the rocket is the reference
REFERENCE_TAGS = ("customreference", "referencelength")  # model-written reference lengths
# Motor fields copied from the table: (field in the design, key in the table).
# The digest is how OpenRocket finds a motor's thrust curve, so it must be the
# table's, never one the model wrote (a digest can point at a bigger motor).
MOTOR_FIELDS = (("manufacturer", "manufacturer"), ("designation", "designation"),
                ("diameter", "diameter_m"), ("length", "length_m"), ("digest", "digest"))
# Every setting a motor of the flown configuration may keep. The reference
# motors use exactly these (the digest is written from the table).
MOTOR_CHILDREN = frozenset({"type", "manufacturer", "motor_id", "designation", "diameter",
                            "length", "delay", "digest"})
# Holders whose repeats are merged: OpenRocket adds the contents of each copy.
MERGED_HOLDERS = ("subcomponents", "motormount")
# Settings that may legitimately appear more than once in one place. The
# reference designs write "tabposition" twice (old and new form, different
# "relativeto"), and the rocket lists one "motorconfiguration" per configuration.
REPEATABLE = frozenset({"tabposition", "motorconfiguration"})
# Nodes whose settings are de-duplicated: every component, the rocket, a motor.
_SETTING_OWNERS = KNOWN_COMPONENT_TYPES | {"rocket", "motor"}
# Drag overrides: a part's own drag coefficient, and the switch that makes it
# stand for the parts inside it.
DRAG_OVERRIDE_TAGS = ("overridecd", "overridesubcomponentscd")


# ------------------------------------------------------------------ editing helpers

def _set_value(node: Node, tag: str, value: Any) -> bool:
    """Make the first child `tag` hold `value` (adding it when missing) and
    drop any further children with the same tag. True when something changed."""
    kids = child_list(node)
    if kids is None:
        body = node[tag_of(node)]
        if not isinstance(body, dict):
            body = {}
            node[tag_of(node)] = body
        kids = body["children"] = []
    changed = False
    first = None
    keep = []
    for c in kids:
        if is_node(c) and tag_of(c) == tag:
            if first is not None:
                changed = True
                continue
            first = c
        keep.append(c)
    if first is None:
        keep.append({tag: {"value": value}})
        changed = True
    elif first[tag] != {"value": value}:
        first[tag] = {"value": value}
        changed = True
    kids[:] = keep
    return changed


def _remove_tags(root: Node, tags: tuple[str, ...]) -> int:
    """Remove every node with one of these tags anywhere below `root`. Returns
    how many were removed."""
    removed = 0
    for node in walk_nodes(root):
        kids = child_list(node)
        if not kids:
            continue
        keep = [c for c in kids if not (is_node(c) and tag_of(c) in tags)]
        if len(keep) != len(kids):
            removed += len(kids) - len(keep)
            kids[:] = keep
    return removed


# ------------------------------------------------------------------ the rules

def _one_copy_of_each_setting(rocket: Node, notes: list[str]) -> None:
    """Make every setting mean what OpenRocket reads.

    On the rocket, every component and every motor: repeated "subcomponents"
    (or "motormount") holders are merged into the first one, keeping their
    parts in order, and a setting written more than once keeps only its last
    copy. Settings in REPEATABLE are left alone.
    """
    merged = 0
    dropped: list[str] = []
    for node in walk_nodes(rocket):
        if tag_of(node) not in _SETTING_OWNERS:
            continue
        kids = child_list(node)
        if not kids:
            continue
        last: dict[str, int] = {}
        first_holder: dict[str, Node] = {}
        for i, c in enumerate(kids):
            if is_node(c):
                last[tag_of(c)] = i
        keep = []
        for i, c in enumerate(kids):
            if not is_node(c):
                keep.append(c)
                continue
            t = tag_of(c)
            if t in MERGED_HOLDERS:
                if t not in first_holder:
                    first_holder[t] = c
                    keep.append(c)
                    continue
                target = first_holder[t]
                body = target[t]
                if not isinstance(body, dict):
                    body = target[t] = {}
                if not isinstance(body.get("children"), list):
                    body["children"] = []
                body["children"].extend(child_list(c) or [])
                merged += 1
                continue
            if t in REPEATABLE or last[t] == i:
                keep.append(c)
            else:
                dropped.append(f"{t[:40]} on {tag_of(node)[:40]}")
        if len(keep) != len(kids):
            kids[:] = keep
    if merged:
        notes.append(f"merged {merged} extra 'subcomponents'/'motormount' holder(s) into the first one, "
                     "as OpenRocket adds the parts of each")
    if dropped:
        shown = ", ".join(sorted(set(dropped))[:4])
        notes.append(f"removed {len(dropped)} repeated setting(s) ({shown}); "
                     "OpenRocket keeps the last copy, so only that one is kept and checked")


def _keep_flown_configuration(root: Node, rocket: Node, notes: list[str]) -> None:
    """Keep only the motor configuration OpenRocket flies, and the motors and
    per-configuration settings that use it."""
    cid = flown_config_id(root)
    if cid is None:
        return
    removed = 0
    kids = child_list(rocket) or []
    keep = []
    for c in kids:
        if is_node(c) and tag_of(c) == "motorconfiguration":
            a = body_of(c).get("attrs")
            if not (isinstance(a, dict) and a.get("configid") == cid):
                removed += 1
                continue
        keep.append(c)
    kids[:] = keep
    for node in walk_nodes(rocket):
        kids = child_list(node)
        if not kids:
            continue
        keep = []
        for c in kids:
            a = body_of(c).get("attrs") if is_node(c) else None
            if isinstance(a, dict) and "configid" in a and a.get("configid") != cid:
                removed += 1
                continue
            keep.append(c)
        if len(keep) != len(kids):
            kids[:] = keep
    if removed:
        notes.append(f"removed {removed} motor configuration(s), motor(s) and setting(s) that do not "
                     f"belong to the flown configuration {cid[:40]!r}")


def _drop_simulations(root: Node, notes: list[str]) -> Node:
    """Remove every "simulations" node, and any second top-level key next to
    "openrocket" (the model sometimes puts its simulations there)."""
    if isinstance(root, dict) and "openrocket" in root and len(root) > 1:
        extra = sorted(str(k)[:40] for k in root if k != "openrocket")
        root = {"openrocket": root["openrocket"]}
        notes.append(f"removed top-level {', '.join(extra)} next to the design")
    n = _remove_tags(root, ("simulations",))
    if n:
        notes.append(f"removed {n} simulations block(s): launch conditions are set by the reward")
    return root


def _force_reference(rocket: Node, notes: list[str]) -> None:
    """Stability is measured against the rocket's widest part, as OpenRocket does by default."""
    old = [body_of(c).get("value") for c in children_of(rocket) if tag_of(c) == "referencetype"]
    if _set_value(rocket, "referencetype", REFERENCE_TYPE):
        was = repr(old[0])[:40] if old else "missing"
        notes.append(f"stability reference set to {REFERENCE_TYPE!r} (was {was})")
    n = _remove_tags(rocket, REFERENCE_TAGS)
    if n:
        notes.append(f"removed {n} custom reference length(s)")


def _motor_table_values(rocket: Node, table: Any, notes: list[str]) -> None:
    """Replace each known motor's maker, designation, diameter and length with
    the table's values, and write its motor id as the table spells it. A motor
    the table does not know is left alone: stage 3 fails it."""
    for motor in [n for n in walk_nodes(rocket) if tag_of(n) == "motor"]:
        written = last_text(motor, "motor_id")
        key = table.resolve(written, last_text(motor, "manufacturer"), last_text(motor, "designation"))
        if key is None:
            continue
        info = table.get(key) or {}
        changed = []
        kids = child_list(motor) or []
        known = [c for c in kids if is_node(c) and tag_of(c) in MOTOR_CHILDREN]
        if len(known) != len(kids):
            changed.append(f"{len(kids) - len(known)} unknown setting(s) removed")
            kids[:] = known
        if _set_value(motor, "motor_id", key):
            changed.append("motor id")
        for field, src in MOTOR_FIELDS:
            value = info.get(src)
            if value is None:
                if _remove_tags(motor, (field,)):
                    changed.append(field)
            elif _set_value(motor, field, value):
                changed.append(field)
        if changed:
            notes.append(f"motor {key}: {', '.join(changed)} taken from the motor table")


def _force_file_version(root: Node, notes: list[str]) -> None:
    """Write the file format version OpenRocket 24.12 itself writes. A root
    whose attributes are not an object is left alone (the file writer refuses it)."""
    body = root.get("openrocket")
    if not isinstance(body, dict):
        return
    attrs = body.get("attrs")
    if attrs is None:
        attrs = body["attrs"] = {}
    if not isinstance(attrs, dict) or attrs.get("version") == FILE_VERSION:
        return
    old = attrs.get("version")
    attrs["version"] = FILE_VERSION
    was = repr(old)[:20] if old is not None else "missing"
    notes.append(f"file format version set to {FILE_VERSION!r}, the one OpenRocket 24.12 writes (was {was})")


def _drop_drag_overrides(rocket: Node, notes: list[str]) -> None:
    """Remove every drag override: the drag is what OpenRocket computes."""
    n = _remove_tags(rocket, DRAG_OVERRIDE_TAGS)
    if n:
        notes.append(f"removed {n} drag override setting(s) (overridecd, overridesubcomponentscd): "
                     "the drag of every part is the one OpenRocket computes from its shape")


def _no_wait_on_the_pad(root: Node, notes: list[str]) -> None:
    """The motors of the bottom stage (the last stage, the one that lifts off)
    light with no ignition delay, on the motor mount and in its
    per-configuration ignition settings. A delay there only keeps the rocket
    sitting on the pad, which would count as flight time. The ignition event
    is kept, and so is every setting of the upper stages and of side boosters
    (their own stages), where a delay is a real air start."""
    stages = stages_of(root)
    if not stages:
        return
    bottom = stages[-1]
    comps = [bottom] + [c for c, parents in walk_components(bottom)
                        if tag_of(c) != "parallelstage" and not any(tag_of(p) == "parallelstage" for p in parents)]
    changed = 0
    for comp in comps:
        for mount in children_named(comp, "motormount"):
            for holder in [mount] + children_named(mount, "ignitionconfiguration"):
                if not is_node(holder):
                    continue
                for c in children_named(holder, "ignitiondelay"):
                    if read_number(body_of(c).get("value"))[0] != 0:
                        changed += 1
                        _set_value(holder, "ignitiondelay", 0.0)
                        break
    if changed:
        notes.append(f"set {changed} ignition delay(s) of the bottom stage's motors to 0 s: the rocket must not "
                     "wait on the pad, because flight times are measured from the start")


def _density_parses(value: Any) -> bool:
    """True when OpenRocket's loader can read this written density as a number."""
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return True
    return java_number(value) is not None


def apply_material_densities(rocket: Node, notes: list[str],
                             materials: Optional[MaterialTable] = None) -> None:
    """Give every material the density from the material table, following
    what OpenRocket's loader does with a material node.

    OpenRocket uses a material node only when its name is not empty, its
    density reads as a number and its type is missing or exactly the type its
    slot holds (materials.slot_type: cloth is "surface", shock cords and
    shroud lines "line", the rest "bulk"); otherwise it keeps the part's
    default material. So, for each material node of a known slot:

      * one OpenRocket would ignore is removed (the part keeps OpenRocket's
        default, exactly as before), and so is one whose name names no
        material ("" or only "RS:"), so OpenRocket uses its default there too
      * a name the table knows gets the table's density for the slot's type,
        and the slot's type is written explicitly
      * a name the table does not know keeps its written density (stage 4
        fails the name) and gets the slot's type written explicitly

    Nodes in places that hold no material are left alone.
    """
    table = materials if materials is not None else default_material_table()
    replaced = 0
    ignored: list[str] = []
    empty = 0
    for parent in walk_nodes(rocket):
        kids = child_list(parent)
        if not kids:
            continue
        keep = []
        for c in kids:
            mtag = tag_of(c)
            slot = slot_type(tag_of(parent), mtag) if mtag in MATERIAL_TAGS else None
            body = c[mtag] if slot is not None else None
            if slot is None or not isinstance(body, dict):
                keep.append(c)
                continue
            attrs = body.get("attrs")
            name = name_text(body.get("value"))
            if name is None:              # a list or object: the file writer refuses it
                keep.append(c)
                continue
            where = f"{mtag} {name[:40]!r} on {tag_of(parent)[:40]}"
            if not isinstance(attrs, dict) or not _density_parses(attrs.get("density")) \
                    or attrs.get("type") not in (None, slot) or not name.strip():
                ignored.append(where)
                continue
            if means_no_material(name):
                empty += 1
                continue
            new = dict(attrs)
            new["type"] = slot
            hit = table.match(slot, name)
            if hit is not None:
                new["density"] = hit.density
                if attrs.get("density") != hit.density:
                    replaced += 1
            if new != attrs:
                body["attrs"] = new
            keep.append(c)
        if len(keep) != len(kids):
            kids[:] = keep
    if replaced:
        notes.append(f"{replaced} material density(ies) replaced by the material table's value for the "
                     f"material name ({', '.join(f'{t} in {u}' for t, u in UNITS.items())})")
    if ignored:
        shown = ", ".join(sorted(set(ignored))[:3])
        notes.append(f"removed {len(ignored)} material(s) OpenRocket would ignore (empty name, density that "
                     f"is not a number, or a type other than the slot's), so the part keeps OpenRocket's "
                     f"default material as before: {shown}")
    if empty:
        notes.append(f"removed {empty} material(s) with no name (\"\" or only \"RS:\"): OpenRocket uses its "
                     "default material there")


def clean_design(root: Node, table: Any, materials: Optional[MaterialTable] = None) -> tuple[Node, list[str]]:
    """Make the cleaned copy of a design.

    `root` is the parsed design tree (root tag "openrocket"); `table` is the
    motor table (motors.MotorTable); `materials` is the material table
    (materials.MaterialTable, by default the packaged one). Returns the edited
    copy and plain-language notes saying what was changed. The input is never
    modified, and cleaning the result again changes nothing.
    """
    notes: list[str] = []
    out = copy_tree(root)
    if not isinstance(out, dict) or not out:
        return out, notes
    out = _drop_simulations(out, notes)
    rocket = rocket_of(out)
    if rocket is not None:
        _force_file_version(out, notes)
        _one_copy_of_each_setting(rocket, notes)
        _keep_flown_configuration(out, rocket, notes)
        _no_wait_on_the_pad(out, notes)
        _force_reference(rocket, notes)
        _motor_table_values(rocket, table, notes)
        _drop_drag_overrides(rocket, notes)
        apply_material_densities(rocket, notes, materials)
    return out, notes


# ------------------------------------------------------------------ the natural rocket (stage 5)

# Mass and balance overrides ("overridemass", "overridecg" and their
# "overridesubcomponents..." switches) stay in the cleaned copy: 155 of 183
# sound references use them (kit parts weighed by their maker). Stage 5 bounds
# what they do to the whole rocket by comparing it with the "natural" rocket:
# the same cleaned design with every override tag removed (fit.check_build,
# limits.OVERRIDE_MASS_RATIO_MIN/_MAX and OVERRIDE_CG_SHIFT_MAX_CAL). Drag
# overrides never get this far: the cleaning removes them.
OVERRIDE_TAG_PREFIX = "override"


def override_count(root: Node) -> int:
    """How many override settings (tags starting with "override") the design holds."""
    return sum(1 for node in walk_nodes(root) for c in children_of(node)
               if tag_of(c).startswith(OVERRIDE_TAG_PREFIX))


def natural_copy(root: Node) -> tuple[Node, int]:
    """The same design with every override setting removed, as OpenRocket
    would build it from its parts and materials alone. Returns the copy and
    how many settings were removed; the input is never changed."""
    out = copy_tree(root)
    removed = 0
    for node in walk_nodes(out):
        kids = child_list(node)
        if not kids:
            continue
        keep = [c for c in kids if not (is_node(c) and tag_of(c).startswith(OVERRIDE_TAG_PREFIX))]
        if len(keep) != len(kids):
            removed += len(kids) - len(keep)
            kids[:] = keep
    return out, removed
