"""Named ways to break or cheat with a rocket, and what the reward must do with each.

Earlier reward attempts spoke of a "fuzz set" of broken rockets that was never
saved, so nobody could check it again. This file is that set, written down:
each operator takes a sound reference design and returns a changed copy (or
None when it does not apply to that design), together with what must happen
when the copy is scored:

  a stage key ("format" ... "flight")  scoring must stop at exactly that stage
  "lower"           the copy must score lower than the original (judged only
                    when the original reaches the targets stage)
  "lower_in_targets" the copy must still reach the targets stage and score
                    lower than the original: a miss of the prompt's own
                    numbers, which stage 7 scores, not a safety rule (judged
                    only when the original meets every target, score 1.0;
                    an original that misses one can trade it for another)
  "same"          a cheat the reward must ignore: the copy scores exactly
                    the same as the original
  "same_or_higher"  an honest edit: the copy may score the same or higher
  "higher"          a repair of a broken model answer: the fixed copy must
                    score higher than the answer as written

An operator can also give the same edit without its cheat ("untagged"; the
override cheats do): the copy with the cheat must then get exactly the stage
and score of the copy without it, and a "same" promise is judged against that
copy. Since 2026-11-19 the cleaning removes every override setting, so every
override operator must change nothing.

A few operators also read the design's requirements ("uses_requirements"):
they size a part from the prompt's own landing number. They apply only to
designs whose requirements state one.

The cheats and defects come from the two attack reviews of the reward (stages
1-4, then stages 5-7), the 2026-11-19 review of targets, overrides and sizes
and its second round (pods, weights in another stage, slender rockets and
parachutes that open at the ground) and third round (pods nested in pods, a
booster's pods beside the stage above, a thin flared disk that hid a needle
rocket), and the earlier rewards' notes; the repairs start
from real model answers that fail for one clear reason.

Usage (from the repo root; Java and the OpenRocket jar must be set up unless
--preflight-only is given):

    python -m rocket_reward.tools.mutate --answers FILE.jsonl[.gz] --requirements FILE.json \\
        --out REPORT.md [--json REPORT.json] [--repair-answers MODEL.jsonl[.gz]] \\
        [--designs ID,ID] [--operators NAME,NAME] [--workers 4] [--preflight-only] \\
        [--write-expected EXPECTED.json]

--answers holds reference answers ({"id", "answer" or "content" or "messages"});
rows that carry the same design block count once (the first row's
requirements are used). --requirements maps every answer id to its
requirements record. --repair-answers holds model answers (same requirements
file); only the repairs run on them. The report lists, for every operator, how
many designs it applied to, where they stopped, the scores before and after,
and every case that did not do what it must: those are findings for the owner.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional, Sequence, Union

from rocket_reward import ladder
from rocket_reward import limits as L
from rocket_reward.limits import KNOWN_COMPONENT_TYPES
from rocket_reward.tree import (Node, attr_of, body_of, child, child_list, children_named, children_of, copy_tree,
                                is_legal_child, iter_components, last_child, make_node, read_number, rocket_of,
                                stages_of, tag_of, value_of, walk_nodes)

# What must happen to a mutant (see the module notes).
EXPECT_LOWER = "lower"
EXPECT_SAME = "same"
EXPECT_SAME_OR_HIGHER = "same_or_higher"
EXPECT_HIGHER = "higher"
EXPECT_LOWER_IN_TARGETS = "lower_in_targets"
STOP_STAGES = tuple(k for k in ladder.STAGE_KEYS if k != "targets")
EXPECT_KINDS = STOP_STAGES + (EXPECT_LOWER, EXPECT_LOWER_IN_TARGETS, EXPECT_SAME, EXPECT_SAME_OR_HIGHER,
                              EXPECT_HIGHER)
# Stages 1-4 run without the simulator; everything after needs it.
PREFLIGHT_STAGES = ("format", "parts", "motor", "limits")

MODEL_PREFIX = "model:"    # marks a model answer's design id in reports (the ids match the references')
SCORE_EPS = 1e-9          # scores are rounded to 6 places; closer than this is "the same"
FIN_SET_TAGS = ("trapezoidfinset", "ellipticalfinset", "freeformfinset")
ALL_FIN_TAGS = FIN_SET_TAGS + ("tubefinset",)
SHELL_TAGS = ("nosecone", "bodytube", "transition")
RECOVERY_TAGS = ("parachute", "streamer")
OVERRIDE_TAGS = ("overridemass", "overridecg", "overridecd", "overridesubcomponents",
                 "overridesubcomponentsmass", "overridesubcomponentscg", "overridesubcomponentscd")
UNTAGGED_SUFFIX = "|untagged"   # outcome key of a case's copy without its cheat
# The two override cheats of the 2026-11-19 review, rebuilt without a simulator:
FAKE_CG_FIN_FACTOR = 0.5        # fins halved, as in the review's V4-0238 case
FAKE_CG_AT_LENGTH = 1.0 / 3.0   # stage balance point written a third of the stage's length behind its front
SMALL_CHUTE_FACTOR = 0.6        # parachutes at 0.6 times their diameter, as in the review's V4-0201 case
LIFTOFF_PER_MOTOR_MASS = 4.0    # liftoff mass guessed as four times the flown motors' loaded mass
FAKE_MASS_SHARE = 0.5           # stage mass written as half that liftoff mass, as in the review
# Parachute sizes. A parachute's landing speed goes as 1 / its diameter, and
# the prompt's landing number is the reference flight's own landing rounded up
# (the 48 val answers: 0.95 to 1.0 times), so it stands in for that speed.
FAR_SMALL_CHUTE_DIVISOR = 5.0   # chute_far_too_small: every parachute a fifth of its size ...
FAR_SMALL_CHUTE_MIN_SHRINK = 4.0  # ... and only where the largest really shrinks at least 4 times (0.15 m floor)
PROMPT_MISS_PAST_BAND = 1.17    # chute_too_small_for_prompt: land 1.17 times past the prompt's number and its slack ...
PROMPT_MISS_HARD_SHARE = 0.9    # ... only where that stays under 0.9 times the 9 m/s safety limit
NEAR_HARD_LANDING_MS = 8.8      # landing_just_under_hard_limit: aim at 8.8 m/s, just under the 9 m/s limit ...
NEAR_HARD_PROMPT_MARGIN = 1.1   # ... only where that is 1.1 times past the prompt's number with its slack
# swap_to_unnamed_motor: a real motor of the next class down (or up), same
# diameter, whose total impulse is at least this many times away, so the
# apogee clearly moves; its length at most this share longer (it must fit).
SWAP_IMPULSE_MIN_RATIO = 1.3
SWAP_LENGTH_MAX_RATIO = 1.1
# Parts placed outside the airframe (stage 5 must stop them): this far ahead
# of the nose tip or behind the tail, in metres; under limits.POSITION_MAX_M
# (5 m), so stage 4 lets the position through.
FAR_AHEAD_M = 1.5
FAR_BEHIND_M = 1.0
THIN_PART_MAX_M = 0.006         # far_away_thin_part moves a ring, bulkhead or engine block at most 6 mm long
# Round 2 of the 2026-11-19 review (each as in the attackers' own edits):
POD_STICK_AHEAD_M = 2.0         # pod_weight_ahead_of_nose: the pod's front this far ahead of the first body tube's front ...
POD_STICK_RADIUS_M = 0.01       # ... a pod 10 mm in radius (at most half the body's) ...
POD_STICK_WEIGHT_SHARE = 0.1    # ... holding a tenth of the liftoff guess ...
POD_STICK_FIN_FACTOR = 0.6      # ... with the fins at 0.6 times their size (unstable without the weight)
BOOSTER_WEIGHT_SHARE = 0.15     # booster_weight_in_upper_stage: 0.15 times the liftoff guess ...
BOOSTER_WEIGHT_AT_NOSE = 0.6    # ... placed 0.6 nose lengths behind the tip
POD_WRAP_RADIUS_FACTOR = 1.04   # motor tube wrapped in a pod: the pod tube 1.04 times the motor tube's radius ...
POD_WRAP_RADIUS_EXTRA_M = 0.0008  # ... plus 0.8 mm
POD_SIDE_OFFSET_M = 0.25        # pod_far_to_the_side: pods 0.25 m out from their body tube
NEEDLE_SLENDERNESS = 120.0      # needle_rocket: length at least 120 times the widest diameter (the limit is 60, limits.SLENDERNESS_MAX)
GROUND_OPEN_ALTITUDE_M = 4.0    # parachute_opens_at_ground
LOW_MAIN_ALTITUDE_M = 15.0      # main_opens_low_drogue_kept
# Round 3 of the 2026-11-19 review (each as in the attackers' own edits):
NESTED_OUTER_RADIUS_SHARE = 0.3  # motor_pods_inside_pods: two outer pods 0.3 times the body tube's radius ...
NESTED_SUNK_SHARE = 0.6         # ... each holding a motor pod whose axis lies 0.6 inner-pod radii outside the outer pod's
NESTED_FIN_FACTOR = 0.6         # ... with the fins at 0.6 times their size (the attackers' best case)
SIDE_POD_RADIUS_SHARE = 0.3     # booster_pod_beside_upper_stage: two pods 0.3 times the widest radius ...
SIDE_POD_AT_NOSE = 0.5          # ... their front 0.5 nose lengths behind the tip ...
SIDE_POD_WEIGHT_SHARE = 0.15    # ... holding 0.15 times the liftoff guess between them
TAIL_DISK_LENGTH_M = 0.002      # needle_rocket_with_tail_disk: a 2 mm flared transition ...
TAIL_DISK_RADIUS_FACTOR = 2.5   # ... opening to 2.5 times the radius of the shell in front of it


@dataclass(frozen=True)
class RawDesign:
    """Design text written between the tags exactly as given, for mutations
    JSON cannot express. closed=False leaves out the closing </design> tag
    and everything after it (an answer cut off mid-way)."""

    text: str
    closed: bool = True


Mutant = Union[dict, RawDesign]
Apply = Callable[..., Optional[Mutant]]   # (design, table) or, with uses_requirements, (design, table, requirements)


@dataclass(frozen=True)
class Operator:
    """One named way to break, cheat with or repair a design."""

    name: str
    expect: str      # one of EXPECT_KINDS
    what: str        # what it does, in plain words
    apply: Apply     # (design copy, motor table) -> changed design, RawDesign, or None
    repair: bool = False   # True: runs on model answers, not on references
    # The same edit without its cheat (for example without the override tags).
    # When given, the mutant must also get exactly the stage and score of this
    # copy, and a "same" promise is judged against it instead of the original.
    untagged: Optional[Apply] = None
    # True: apply is called as apply(design, table, requirements) and returns
    # None when the requirements do not give what it needs.
    uses_requirements: bool = False

    @property
    def needs_simulator(self) -> bool:
        """True when judging this operator needs the simulator stages."""
        return self.expect not in PREFLIGHT_STAGES


# --------------------------------------------------------------------------- tree editing

def _mu_view(design: dict) -> Node:
    """The "openrocket" node of a design dict, sharing its body (edits go through)."""
    return {"openrocket": design.get("openrocket")}


def _mu_kids(node: Node) -> list:
    """The node's children list, created when missing, for editing in place."""
    tag = tag_of(node)
    body = node[tag]
    if not isinstance(body, dict):
        body = node[tag] = {}
    kids = body.get("children")
    if not isinstance(kids, list):
        kids = body["children"] = []
    return kids


def _mu_parts(design: dict, *tags: str) -> list[Node]:
    """Every component with one of these tags inside the rocket's stages."""
    out = []
    for st in stages_of(_mu_view(design)):
        out.extend(c for c in iter_components(st) if tag_of(c) in tags)
    return out


def _mu_set(node: Node, tag: str, value: Any, attrs: Optional[dict] = None) -> None:
    """Set every child setting `tag` of `node` to `value` (adding one when none
    is written), so the value holds whichever copy a reader keeps."""
    found = False
    for c in _mu_kids(node):
        if tag_of(c) == tag:
            body = c[tag] if isinstance(c[tag], dict) else {}
            c[tag] = body
            body["value"] = value
            if attrs is not None:
                body["attrs"] = dict(attrs)
            found = True
    if not found:
        _mu_kids(node).append(make_node(tag, value, attrs))


def _mu_drop(design: dict, tags: Sequence[str]) -> int:
    """Remove every node with one of these tags anywhere in the rocket; returns how many."""
    gone = 0
    for node in walk_nodes(_mu_view(design)):
        kids = child_list(node)
        if kids is None:
            continue
        keep = [c for c in kids if tag_of(c) not in tags]
        gone += len(kids) - len(keep)
        kids[:] = keep
    return gone


def _mu_holder(component: Node) -> list:
    """The parts list of the component's first "subcomponents" holder (made when missing)."""
    holder = child(component, "subcomponents")
    if holder is None:
        holder = make_node("subcomponents", children=[])
        _mu_kids(component).append(holder)
    return _mu_kids(holder)


def _mu_num(node: Node, tag: str) -> Optional[float]:
    """The last copy of a setting as a number; for text such as "auto 0.025"
    the last word is read."""
    c = last_child(node, tag)
    if c is None:
        return None
    raw = value_of(c)
    v = read_number(raw)[0]
    if v is None and isinstance(raw, str) and raw.split():
        v = read_number(raw.split()[-1])[0]
    return v


def _mu_place(node: Node, method: str, value: float) -> None:
    """Place a component: its axial offset (and the older "position" setting
    when it is written) relative to `method` ("top", "bottom" ...)."""
    _mu_set(node, "axialoffset", value, {"method": method})
    if child(node, "position") is not None:
        _mu_set(node, "position", value, {"type": method})


def _mu_widest_radius(design: dict) -> float:
    """The widest outer radius written on a nose cone, body tube or transition (metres)."""
    radii = []
    for p in _mu_parts(design, *SHELL_TAGS):
        for tag in ("radius", "aftradius", "foreradius"):
            v = _mu_num(p, tag)
            if v is not None and v > 0:
                radii.append(v)
    return max(radii) if radii else 0.05


def _mu_fin_tube(design: dict) -> Optional[Node]:
    """The first component that holds a fin set, or the first body tube."""
    for p in _mu_parts(design, *SHELL_TAGS):
        if any(tag_of(c) in ALL_FIN_TAGS for c in _mu_holder_parts(p)):
            return p
    tubes = _mu_parts(design, "bodytube")
    return tubes[0] if tubes else None


def _mu_holder_parts(component: Node) -> list:
    """The parts of the component's first holder, without creating one."""
    holder = child(component, "subcomponents")
    return children_of(holder) if holder is not None else []


def _mu_motor_fields(motor: Node) -> tuple[Any, Any, Any]:
    """(motor id, maker, designation) as written; the last copy counts."""
    out = []
    for tag in ("motor_id", "manufacturer", "designation"):
        c = last_child(motor, tag)
        out.append(value_of(c) if c is not None else None)
    return out[0], out[1], out[2]


def _mu_flown(design: dict) -> list[Node]:
    from rocket_reward.motors import flown_motors
    return flown_motors(_mu_view(design))


def _mu_mounts(design: dict) -> list[tuple[Node, Node]]:
    """(mount tube, motor) for the flown motors."""
    from rocket_reward.motors import flown_config_id, mount_motors
    view = _mu_view(design)
    cid = flown_config_id(view)
    return [(t, m) for t, m in mount_motors(view) if cid is not None and attr_of(m, "configid") == cid]


def _mu_key(table: Any, motor: Node) -> Optional[str]:
    mid, maker, des = _mu_motor_fields(motor)
    return table.resolve(mid, maker, des)


def _mu_entries() -> dict:
    from rocket_reward.ork import motor_table_entries
    return dict(motor_table_entries())


def _mu_set_motor(motor: Node, key: str, entry: dict) -> None:
    """Make a motor node name this table motor (id, maker and designation)."""
    _mu_set(motor, "motor_id", key)
    _mu_set(motor, "manufacturer", entry.get("manufacturer"))
    _mu_set(motor, "designation", entry.get("designation"))


def _mu_invent(motor: Node, designation: str, table: Any) -> bool:
    """Rename a motor to `designation` under its own maker; True when the new
    id is not a real motor."""
    mid, maker, _ = _mu_motor_fields(motor)
    prefix = maker if isinstance(maker, str) and maker else (table.maker_prefix(mid) or "AeroTech")
    new_id = f"{prefix}-{designation}"
    if table.resolve(new_id) is not None:
        return False
    _mu_set(motor, "motor_id", new_id)
    _mu_set(motor, "designation", designation)
    return True


def _mu_bottom_stage(design: dict) -> Optional[Node]:
    st = stages_of(_mu_view(design))
    return st[-1] if st else None


def _mu_razor_fin() -> Node:
    return {"trapezoidfinset": {"children": [
        {"fincount": {"value": 4}}, {"rootchord": {"value": 0.1}}, {"tipchord": {"value": 0.05}},
        {"height": {"value": 0.08}}, {"thickness": {"value": 0.00001}},
        {"axialoffset": {"attrs": {"method": "bottom"}, "value": 0.0}}]}}


def _mu_drag_chute() -> Node:
    return {"parachute": {"children": [{"diameter": {"value": 1.0}}, {"cd": {"value": 50.0}},
                                       {"deployevent": {"value": "apogee"}}]}}


def _mu_lug(radius: float, length: float, offset: float = 0.0) -> Node:
    return {"launchlug": {"children": [
        {"axialoffset": {"attrs": {"method": "top"}, "value": offset}},
        {"material": {"attrs": {"type": "bulk", "density": 680.0}, "value": "Cardboard"}},
        {"radius": {"value": radius}}, {"length": {"value": length}}, {"thickness": {"value": 0.0005}}]}}


def _mu_scale_fins(design: dict, factor: float) -> int:
    """Scale every fin set's span and chords (freeform: every point) by `factor`."""
    done = 0
    for f in _mu_parts(design, *FIN_SET_TAGS):
        if tag_of(f) == "freeformfinset":
            for pts in children_named(f, "finpoints"):
                for p in children_named(pts, "point"):
                    attrs = body_of(p).get("attrs")
                    if isinstance(attrs, dict):
                        for axis in ("x", "y"):
                            v = read_number(attrs.get(axis))[0]
                            if v is not None:
                                attrs[axis] = v * factor
            done += 1
            continue
        for tag in ("height", "rootchord", "tipchord", "sweeplength"):
            v = _mu_num(f, tag)
            if v is not None:
                _mu_set(f, tag, v * factor)
        done += 1
    return done


def _mu_root_chord(fin: Node) -> Optional[float]:
    if tag_of(fin) == "freeformfinset":
        xs = [read_number(attr_of(p, "x"))[0] for pts in children_named(fin, "finpoints")
              for p in children_named(pts, "point")]
        xs = [x for x in xs if x is not None]
        return max(xs) - min(xs) if xs else None
    if tag_of(fin) == "tubefinset":
        return _mu_num(fin, "length")
    return _mu_num(fin, "rootchord")


# --------------------------------------------------------------------------- stage 1: format

def op_tag_not_xml(design: dict, table: Any) -> Optional[Mutant]:
    """The nose cone's length setting renamed to a tag with a space in it."""
    noses = _mu_parts(design, "nosecone")
    if not noses:
        return None
    for c in _mu_kids(noses[0]):
        if tag_of(c) == "length":
            c["nose length"] = c.pop("length")
            return design
    _mu_kids(noses[0]).append({"nose length": {"value": 0.1}})
    return design


def op_cut_off(design: dict, table: Any) -> Optional[Mutant]:
    """The design text stops half-way, with no closing tag."""
    text = json.dumps(design)
    return RawDesign(text[: len(text) // 2], closed=False)


# --------------------------------------------------------------------------- stage 2: parts

def op_motor_deleted(design: dict, table: Any) -> Optional[Mutant]:
    return design if _mu_drop(design, ("motor",)) else None


def op_recovery_deleted(design: dict, table: Any) -> Optional[Mutant]:
    return design if _mu_drop(design, RECOVERY_TAGS) else None


def op_config_id_missing(design: dict, table: Any) -> Optional[Mutant]:
    """The rocket's motor configurations lose their configuration ids."""
    rocket = rocket_of(design)
    configs = children_named(rocket, "motorconfiguration") if rocket is not None else []
    if not configs:
        return None
    for c in configs:
        attrs = body_of(c).get("attrs")
        if isinstance(attrs, dict):
            attrs.pop("configid", None)
    return design


# --------------------------------------------------------------------------- stage 3: motor

def op_invented_motor(design: dict, table: Any) -> Optional[Mutant]:
    """Every flown motor renamed to a designation no maker sells (same class letter)."""
    from rocket_reward.motors import class_from_designation
    motors = _mu_flown(design)
    if not motors:
        return None
    for m in motors:
        key = _mu_key(table, m)
        letter = (table.class_of(key) if key else None) or class_from_designation(_mu_motor_fields(m)[2]) or "H"
        if not _mu_invent(m, f"{letter}9999X", table):
            return None
    return design


def op_near_miss_motor(design: dict, table: Any) -> Optional[Mutant]:
    """One digit of every flown motor's designation changed (a near miss of a real id)."""
    motors = _mu_flown(design)
    if not motors:
        return None
    for m in motors:
        key = _mu_key(table, m)
        if key is None:
            return None
        des = str(table.get(key).get("designation"))
        done = False
        for i in range(len(des) - 1, -1, -1):
            if not des[i].isdigit():
                continue
            new = des[:i] + str((int(des[i]) + 1) % 10) + des[i + 1:]
            if not table.has_designation(new) and _mu_invent(m, new, table):
                done = True
                break
        if not done:
            return None
    return design


def op_wrong_version_suffix(design: dict, table: Any) -> Optional[Mutant]:
    """Every flown motor's id given a version suffix the table does not have (-v9)."""
    motors = _mu_flown(design)
    if not motors:
        return None
    for m in motors:
        key = _mu_key(table, m)
        if key is None:
            return None
        base = re.sub(r"-v\d+$", "", key, flags=re.IGNORECASE)
        if table.resolve(base + "-v9") is not None:
            return None
        _mu_set(m, "motor_id", base + "-v9")
    return design


def op_second_default_config(design: dict, table: Any) -> Optional[Mutant]:
    """A second configuration marked default, whose motors are invented."""
    rocket = rocket_of(design)
    mounts = _mu_mounts(design)
    if rocket is None or not mounts:
        return None
    _mu_kids(rocket).append({"motorconfiguration": {"attrs": {"configid": "cfgX", "default": "true"}}})
    seen = set()
    for tube, _ in mounts:
        if id(tube) in seen:
            continue
        seen.add(id(tube))
        for mm in children_named(tube, "motormount"):
            _mu_kids(mm).append({"motor": {"attrs": {"configid": "cfgX"}, "children": [
                {"manufacturer": {"value": "AeroTech"}}, {"motor_id": {"value": "AeroTech-O25000X"}},
                {"designation": {"value": "O25000X"}}, {"diameter": {"value": 0.15}}]}})
    return design


# --------------------------------------------------------------------------- stage 4: limits

def op_override_over_limit(design: dict, table: Any) -> Optional[Mutant]:
    """The nose cone's mass overridden to 50 kg of ballast (the cleaning removes every override)."""
    noses = _mu_parts(design, "nosecone")
    if not noses:
        return None
    _mu_set(noses[0], "overridemass", 50.0)
    _mu_set(noses[0], "overridesubcomponentsmass", False)
    return design


def op_override_negative(design: dict, table: Any) -> Optional[Mutant]:
    """The nose cone's mass overridden to -1 kg to lighten the rocket (the cleaning removes it)."""
    noses = _mu_parts(design, "nosecone")
    if not noses:
        return None
    _mu_set(noses[0], "overridemass", -1.0)
    _mu_set(noses[0], "overridesubcomponentsmass", False)
    return design


def op_chute_cd_over_limit(design: dict, table: Any) -> Optional[Mutant]:
    chutes = _mu_parts(design, "parachute")
    for c in chutes:
        _mu_set(c, "cd", 50.0)
    return design if chutes else None


def op_chute_too_large(design: dict, table: Any) -> Optional[Mutant]:
    chutes = _mu_parts(design, "parachute")
    for c in chutes:
        _mu_set(c, "diameter", 20.0)
    return design if chutes else None


def op_razor_fins(design: dict, table: Any) -> Optional[Mutant]:
    fins = _mu_parts(design, *FIN_SET_TAGS)
    for f in fins:
        _mu_set(f, "thickness", 0.00001)
    return design if fins else None


def op_java_number_text(design: dict, table: Any) -> Optional[Mutant]:
    """Razor fins written as number text only Java reads ("0.00001f")."""
    fins = _mu_parts(design, *FIN_SET_TAGS)
    for f in fins:
        _mu_set(f, "thickness", "0.00001f")
    return design if fins else None


def op_paper_thin_walls(design: dict, table: Any) -> Optional[Mutant]:
    """Every nose cone, body tube and transition wall 0.01 mm (their own mass overrides removed)."""
    shells = [p for p in _mu_parts(design, *SHELL_TAGS) if child(p, "thickness") is not None]
    _mu_drop(design, OVERRIDE_TAGS)
    for p in shells:
        _mu_set(p, "thickness", 0.00001)
    return design if shells else None


def op_foam_walls(design: dict, table: Any) -> Optional[Mutant]:
    """Shells and fins of foam at the thinnest allowed thickness (0.13 mm walls, 0.5 mm fins)."""
    parts = _mu_parts(design, *SHELL_TAGS, *FIN_SET_TAGS)
    if not parts:
        return None
    _mu_drop(design, OVERRIDE_TAGS)
    for p in parts:
        _mu_set(p, "material", "Styrofoam (generic EPS)", {"type": "bulk", "density": 20.0})
        _mu_set(p, "thickness", 0.0005 if tag_of(p) in FIN_SET_TAGS else 0.00013)
    return design


def op_air_brake_fins(design: dict, table: Any) -> Optional[Mutant]:
    """Fin span six times the widest body diameter (fins used as air brakes)."""
    fins = _mu_parts(design, *FIN_SET_TAGS)
    if not fins:
        return None
    span = 6.0 * 2.0 * _mu_widest_radius(design)
    for f in fins:
        if tag_of(f) == "freeformfinset":
            ys = [read_number(attr_of(p, "y"))[0] for pts in children_named(f, "finpoints")
                  for p in children_named(pts, "point")]
            top = max((y for y in ys if y is not None), default=0.0)
            if top > 0:
                _mu_scale_points_y(f, min(span, 0.99) / top)
        else:
            _mu_set(f, "height", span)
    return design


def _mu_scale_points_y(fin: Node, factor: float) -> None:
    for pts in children_named(fin, "finpoints"):
        for p in children_named(pts, "point"):
            attrs = body_of(p).get("attrs")
            if isinstance(attrs, dict):
                v = read_number(attrs.get("y"))[0]
                if v is not None:
                    attrs["y"] = v * factor


def op_giant_lug(design: dict, table: Any) -> Optional[Mutant]:
    """A launch lug 0.3 m wide and 0.76 m long (an air brake beside the rocket)."""
    tube = _mu_fin_tube(design)
    if tube is None:
        return None
    _mu_holder(tube).append(_mu_lug(0.15, 0.76))
    return design


def op_hundreds_of_parts(design: dict, table: Any) -> Optional[Mutant]:
    """300 tiny launch lugs on one body tube."""
    tube = _mu_fin_tube(design)
    if tube is None:
        return None
    _mu_holder(tube).extend(_mu_lug(0.003, 0.01, 0.001 * (i % 50)) for i in range(300))
    return design


def op_made_up_material(design: dict, table: Any) -> Optional[Mutant]:
    """Every bulk material renamed to a material that does not exist."""
    found = 0
    for node in walk_nodes(_mu_view(design)):
        if tag_of(node) == "material" and attr_of(node, "type") == "bulk":
            body_of(node)["value"] = "Unobtainium alloy"
            found += 1
    return design if found else None


def op_repeated_setting(design: dict, table: Any) -> Optional[Mutant]:
    """Every parachute writes its drag coefficient twice; the second copy is 50."""
    chutes = _mu_parts(design, "parachute")
    for c in chutes:
        _mu_kids(c).append({"cd": {"value": 50.0}})
    return design if chutes else None


def op_paper_tail_cone(design: dict, table: Any) -> Optional[Mutant]:
    """A pointed paper tail cone with a 0.025 mm wall behind the last body part."""
    bottom = _mu_bottom_stage(design)
    if bottom is None:
        return None
    _mu_drop(design, OVERRIDE_TAGS)
    _mu_holder(bottom).append({"transition": {"children": [
        {"material": {"attrs": {"type": "bulk", "density": 1121.29}, "value": "Paper"}},
        {"length": {"value": 0.15}}, {"thickness": {"value": 0.000025}}, {"shape": {"value": "conical"}},
        {"foreradius": {"value": "auto"}}, {"aftradius": {"value": 0.000015}},
        {"foreshoulderlength": {"value": 0.0}}, {"aftshoulderlength": {"value": 0.0}}]}})
    return design


def op_cheat_parts_in_second_holder(design: dict, table: Any) -> Optional[Mutant]:
    """Razor fins and a Cd 50 parachute hidden in a second "subcomponents" holder."""
    tube = _mu_fin_tube(design)
    if tube is None:
        return None
    _mu_holder(tube)   # make sure a first holder exists
    _mu_kids(tube).append(make_node("subcomponents", children=[_mu_razor_fin(), _mu_drag_chute()]))
    return design


# The sizes review of 2026-11-19: absurd sizes, counts, delays and places that
# stage 4 now bounds (limit_checks.py).

def op_zero_width_nose(design: dict, table: Any) -> Optional[Mutant]:
    """Every nose cone's base radius written as 0 (only the word "auto" takes
    the next part's size; a written 0 is a nose of no width)."""
    noses = _mu_parts(design, "nosecone")
    for n in noses:
        _mu_set(n, "aftradius", 0.0)
    return design if noses else None


def op_auto_negative(design: dict, table: Any) -> Optional[Mutant]:
    """Every body tube's radius written "auto -0.0125": OpenRocket keeps the
    number after "auto", so it is a negative size."""
    tubes = _mu_parts(design, "bodytube")
    for t in tubes:
        _mu_set(t, "radius", "auto -0.0125")
    return design if tubes else None


def op_giant_packed_chute(design: dict, table: Any) -> Optional[Mutant]:
    """Every parachute's and shock cord's packed length 1000 times longer
    (25 m when none is written)."""
    parts = _mu_parts(design, "parachute", "shockcord")
    for p in parts:
        v = _mu_num(p, "packedlength")
        _mu_set(p, "packedlength", round(v * 1000.0, 4) if v is not None and v > 0 else 25.0)
    return design if parts else None


def op_floating_fin_root(design: dict, table: Any) -> Optional[Mutant]:
    """Every trapezoid and elliptical fin set's root chord 0.05 mm: a fin held
    on by almost nothing."""
    fins = _mu_parts(design, "trapezoidfinset", "ellipticalfinset")
    for f in fins:
        _mu_set(f, "rootchord", 0.00005)
    return design if fins else None


def op_absurd_rail_button(design: dict, table: Any) -> Optional[Mutant]:
    """Every rail button's base height 2 m (a design without one gets one rail
    button with that base on its fin tube)."""
    buttons = _mu_parts(design, "railbutton")
    if not buttons:
        tube = _mu_fin_tube(design)
        if tube is None:
            return None
        button = {"railbutton": {"children": [
            {"axialoffset": {"attrs": {"method": "middle"}, "value": 0.0}},
            {"material": {"attrs": {"type": "bulk", "density": 1200.0}, "value": "Delrin"}},
            {"outerdiameter": {"value": 0.0097}}, {"innerdiameter": {"value": 0.008}},
            {"height": {"value": 0.0080}}, {"baseheight": {"value": 0.002}}, {"flangeheight": {"value": 0.002}}]}}
        _mu_holder(tube).append(button)
        buttons = [button]
    for b in buttons:
        _mu_set(b, "baseheight", 2.0)
    return design


def op_broken_counts(design: dict, table: Any) -> Optional[Mutant]:
    """Every parachute's shroud lines written as 2.5 and every launch lug's
    copy count as 1.5 (counts must be whole numbers)."""
    chutes = _mu_parts(design, "parachute")
    lugs = _mu_parts(design, "launchlug")
    for c in chutes:
        _mu_set(c, "linecount", 2.5)
    for g in lugs:
        _mu_set(g, "instancecount", 1.5)
    return design if chutes or lugs else None


def op_endless_delay(design: dict, table: Any) -> Optional[Mutant]:
    """Every parachute and streamer opens 1e308 s after its event (it never
    opens, while the delay reads as a number)."""
    devices = _mu_parts(design, *RECOVERY_TAGS)
    for d in devices:
        _mu_set(d, "deploydelay", 1e308)
    return design if devices else None


def op_coin_weight(design: dict, table: Any) -> Optional[Mutant]:
    """A 19 kg mass component 2 mm long and 12.5 mm in radius (about 19,000,000
    kg/m3, a weight the size of a coin) added to the fin tube; 19 kg stays under
    the 20 kg mass bound, so only the density rule stops it."""
    tube = _mu_fin_tube(design)
    if tube is None:
        return None
    _mu_holder(tube).append({"masscomponent": {"children": [
        {"axialoffset": {"attrs": {"method": "top"}, "value": 0.0}}, {"mass": {"value": 19.0}},
        {"packedlength": {"value": 0.002}}, {"packedradius": {"value": 0.0125}}]}})
    return design


def op_absurd_angle_or_offset(design: dict, table: Any) -> Optional[Mutant]:
    """Every launch lug's and rail button's radial direction 1e308 degrees,
    and every mass component 2 m off the rocket's axis."""
    guides = _mu_parts(design, "launchlug", "railbutton")
    masses = _mu_parts(design, "masscomponent")
    for g in guides:
        _mu_set(g, "radialdirection", 1e308)
    for m in masses:
        _mu_set(m, "radialposition", 2.0)
    return design if guides or masses else None


# --------------------------------------------------------------------------- overrides (must change nothing)
# Since 2026-11-19 the cleaning removes every override setting, so each of
# these must score exactly as the design without the added tags.

def op_ballast_overrides(design: dict, table: Any) -> Optional[Mutant]:
    """Every nose cone and body tube overridden to 20 kg of ballast."""
    shells = _mu_parts(design, "nosecone", "bodytube")
    _mu_drop(design, OVERRIDE_TAGS)   # the original's own overrides go too (the cleaning removes them anyway)
    for p in shells:
        _mu_set(p, "overridemass", 20.0)
    return design if shells else None


def op_ballast_cg_override(design: dict, table: Any) -> Optional[Mutant]:
    """Every stage's balance point overridden to its front end (ballast in the nose, on paper)."""
    stages = stages_of(_mu_view(design))
    for st in stages:
        _mu_set(st, "overridecg", 0.0)
        _mu_set(st, "overridesubcomponentscg", True)
    return design if stages else None


def op_lighten_rocket_override(design: dict, table: Any) -> Optional[Mutant]:
    """Every stage's mass overridden to 1 g."""
    stages = stages_of(_mu_view(design))
    for st in stages:
        _mu_set(st, "overridemass", 0.001)
        _mu_set(st, "overridesubcomponentsmass", True)
    return design if stages else None


def op_lighten_one_stage_override(design: dict, table: Any) -> Optional[Mutant]:
    """On a rocket with more than one stage, the top stage's mass overridden to 1 g."""
    stages = stages_of(_mu_view(design))
    if len(stages) < 2:
        return None
    _mu_set(stages[0], "overridemass", 0.001)
    _mu_set(stages[0], "overridesubcomponentsmass", True)
    return design


def _mu_single_stage(design: dict) -> Optional[Node]:
    """The stage of a single-stage design, else None."""
    stages = stages_of(_mu_view(design))
    return stages[0] if len(stages) == 1 else None


def _mu_stage_length(stage: Node) -> float:
    """The written lengths of the nose cones, body tubes and transitions that sit in the stage."""
    return sum(v for p in _mu_holder_parts(stage) if tag_of(p) in SHELL_TAGS
               for v in [_mu_num(p, "length")] if v is not None and v > 0)


def untagged_unstable_fins(design: dict, table: Any) -> Optional[Mutant]:
    """A sound single-stage design with its fins halved, so it is unstable."""
    stage = _mu_single_stage(design)
    if stage is None or not _mu_scale_fins(design, FAKE_CG_FIN_FACTOR):
        return None
    return design


def op_unstable_fake_cg_override(design: dict, table: Any) -> Optional[Mutant]:
    """The review's stability cheat: fins halved (the rocket is unstable), then
    the stage's balance point overridden far forward, with
    overridesubcomponentscg, to read 1 cal or more again."""
    if untagged_unstable_fins(design, table) is None:
        return None
    stage = stages_of(_mu_view(design))[0]
    length = _mu_stage_length(stage)
    if length <= 0:
        return None
    _mu_set(stage, "overridecg", round(FAKE_CG_AT_LENGTH * length, 4))
    _mu_set(stage, "overridesubcomponentscg", True)
    return design


def untagged_small_chutes(design: dict, table: Any) -> Optional[Mutant]:
    """A single-stage design with every parachute at 0.6 times its diameter
    (at least the catalogue's smallest, 0.15 m), or with a motor one class
    weaker when it has no parachute: it lands too fast or flies too low."""
    if _mu_single_stage(design) is None:
        return None
    chutes = _mu_parts(design, "parachute")
    sizes = [_mu_num(c, "diameter") for c in chutes]
    if chutes and all(s is not None and s > 0 for s in sizes):
        for c, s in zip(chutes, sizes):
            _mu_set(c, "diameter", max(0.15, round(SMALL_CHUTE_FACTOR * s, 4)))   # type: ignore[operator]
        return design
    return op_weaker_motor(design, table)


def op_light_stage_mass_override(design: dict, table: Any) -> Optional[Mutant]:
    """The review's landing cheat: smaller parachutes (or a weaker motor), then
    the stage's mass overridden, with overridesubcomponentsmass, to half a
    guess of the liftoff mass (four times the flown motors' loaded mass), so
    the rocket would come down slower."""
    if untagged_small_chutes(design, table) is None:
        return None
    motor_kg = 0.0
    for m in _mu_flown(design):
        key = _mu_key(table, m)
        kg = table.get(key).get("launch_mass_kg") if key else None
        if isinstance(kg, (int, float)) and kg > 0:
            motor_kg += float(kg)
    if motor_kg <= 0:
        return None
    stage = stages_of(_mu_view(design))[0]
    _mu_set(stage, "overridemass", round(FAKE_MASS_SHARE * LIFTOFF_PER_MOTOR_MASS * motor_kg, 4))
    _mu_set(stage, "overridesubcomponentsmass", True)
    return design


# --------------------------------------------------------------------------- stage 5: build

def op_floating_fins(design: dict, table: Any) -> Optional[Mutant]:
    """Every fin set moved 1.5 root chords behind the end of the part it sits on."""
    fins = _mu_parts(design, *ALL_FIN_TAGS)
    moved = 0
    for f in fins:
        chord = _mu_root_chord(f)
        if chord is None or chord <= 0:
            continue
        _mu_place(f, "bottom", 1.5 * chord)
        moved += 1
    return design if moved else None


def op_duplicated_fin_sets(design: dict, table: Any) -> Optional[Mutant]:
    """Every fin set written twice in the same place."""
    done = 0
    for p in _mu_parts(design, *SHELL_TAGS):
        holder = _mu_holder_parts(p)
        fins = [c for c in holder if tag_of(c) in ALL_FIN_TAGS]
        if fins:
            _mu_holder(p).extend(copy_tree(f) for f in fins)
            done += 1
    return design if done else None


def op_motor_far_forward(design: dict, table: Any) -> Optional[Mutant]:
    """Every flown motor's inner tube moved to the front of its body tube, firing into the body."""
    moved = 0
    for st in stages_of(_mu_view(design)):
        for parent in iter_components(st):
            if tag_of(parent) != "bodytube":
                continue
            plen = _mu_num(parent, "length")
            for it in _mu_holder_parts(parent):
                if tag_of(it) != "innertube" or child(it, "motormount") is None:
                    continue
                ilen = _mu_num(it, "length")
                if plen is None or ilen is None or plen < ilen + 0.35:
                    continue
                _mu_place(it, "top", 0.0)
                moved += 1
    return design if moved else None


def _mu_rocket_length(design: dict) -> float:
    """The written length of the main airframe: every stage's nose cones,
    body tubes and transitions (pods left out)."""
    return sum(_mu_stage_length(st) for st in stages_of(_mu_view(design)))


def _mu_behind_tail(design: dict, extra: float) -> Optional[float]:
    """An "absolute" position (from the nose tip) `extra` metres behind the
    tail, or None when that is past limits.POSITION_MAX_M (stage 4 would stop it)."""
    total = _mu_rocket_length(design)
    at = round(total + extra, 4)
    return at if 0 < total and at < L.POSITION_MAX_M - 0.1 else None


def op_far_away_thin_part(design: dict, table: Any) -> Optional[Mutant]:
    """The first centering ring, bulkhead or engine block at most 6 mm long
    placed 1.5 m ahead of the nose tip (within the 5 m position bound, so
    stage 4 lets it through). Its own length is tiny, so only a distance
    measure catches it: stage 5 (ring_outside_airframe)."""
    for p in _mu_parts(design, "centeringring", "bulkhead", "engineblock"):
        length = _mu_num(p, "length")
        if length is not None and 0 <= length <= THIN_PART_MAX_M:
            _mu_place(p, "absolute", -FAR_AHEAD_M)
            return design
    return None


def op_far_away_mass(design: dict, table: Any) -> Optional[Mutant]:
    """The first mass component placed 1.5 m ahead of the nose tip, where it
    would act as nose ballast on a stick: stage 5 (part_outside_airframe)."""
    masses = _mu_parts(design, "masscomponent")
    if not masses:
        return None
    _mu_place(masses[0], "absolute", -FAR_AHEAD_M)
    return design


def op_far_away_recovery(design: dict, table: Any) -> Optional[Mutant]:
    """The first parachute, streamer or shock cord placed 1 m behind the tail:
    stage 5 (part_outside_airframe)."""
    parts = _mu_parts(design, "parachute", "streamer", "shockcord")
    at = _mu_behind_tail(design, FAR_BEHIND_M)
    if not parts or at is None:
        return None
    _mu_place(parts[0], "absolute", at)
    return design


def op_lug_behind_tail(design: dict, table: Any) -> Optional[Mutant]:
    """Every launch lug and rail button placed 1 m behind the tail (as the
    review moved V4-0180's lug from -1.035 to 1.035): stage 5
    (part_outside_airframe)."""
    guides = _mu_parts(design, "launchlug", "railbutton")
    at = _mu_behind_tail(design, FAR_BEHIND_M)
    if not guides or at is None:
        return None
    for g in guides:
        _mu_place(g, "absolute", at)
    return design


POD_TAGS = ("podset", "parallelstage")
POD_INSIDE_TAGS = ("centeringring", "bulkhead", "engineblock", "tubecoupler", "innertube", "masscomponent",
                   "shockcord", "parachute", "streamer", "launchlug", "railbutton")


def op_pod_part_far_away(design: dict, table: Any) -> Optional[Mutant]:
    """The first inside part of the first pod or side booster that has one,
    placed 1 m ahead of the front of the pod part that holds it: usually still
    alongside the main body, but outside the pod's own shell, which stage 5
    judges it against since 2026-11-19 (before, pod parts were skipped).
    It applies only to designs with pods: one of the 16 val designs (row-025,
    which already stops at build on other rules; the moved rail button adds a
    finding, 0.4183 -> 0.4109) and 3 of the 197 reference designs, where
    V4-0107 goes from targets 0.999 to build 0.42 (a centering ring 0.96 m
    ahead of its pod's shell) and V4-0227 is row-025's design (2026-11-19)."""
    for pod in _mu_parts(design, *POD_TAGS):
        for shell in iter_components(pod):
            if tag_of(shell) not in SHELL_TAGS:
                continue
            for p in _mu_holder_parts(shell):
                if tag_of(p) in POD_INSIDE_TAGS:
                    _mu_place(p, "top", -1.0)
                    return design
    return None


def op_closed_tail(design: dict, table: Any) -> Optional[Mutant]:
    """The tail closed to a point: a sound 10 cm cardboard tail cone closing
    to 0.01 mm is added behind the bottom stage's last shell (as V4-0205's
    transition aft radius). The motor fires into the cone: stage 5
    (tail_closed). The cone is added rather than an existing transition
    closed, because fins on that transition would then stand on a body
    0.02 mm wide and stage 4 would stop it first (V4-0166)."""
    bottom = _mu_bottom_stage(design)
    if bottom is None or not any(tag_of(p) in SHELL_TAGS for p in _mu_holder_parts(bottom)):
        return None
    _mu_holder(bottom).append({"transition": {"children": [
        {"material": {"attrs": {"type": "bulk", "density": 680.0}, "value": "Cardboard"}},
        {"length": {"value": 0.1}}, {"thickness": {"value": 0.002}}, {"shape": {"value": "conical"}},
        {"foreradius": {"value": "auto"}}, {"aftradius": {"value": 0.00001}},
        {"foreshoulderlength": {"value": 0.0}}, {"aftshoulderlength": {"value": 0.0}}]}})
    return design


def op_motor_too_wide(design: dict, table: Any) -> Optional[Mutant]:
    """Every inner tube that holds a flown motor shrunk to 0.55 times the motor's radius."""
    done = 0
    seen = set()
    for tube, motor in _mu_mounts(design):
        if tag_of(tube) != "innertube" or id(tube) in seen:
            continue
        key = _mu_key(table, motor)
        dia = table.get(key).get("diameter_m") if key else None
        if not isinstance(dia, (int, float)) or dia <= 0:
            continue
        seen.add(id(tube))
        _mu_set(tube, "outerradius", round(0.55 * dia / 2.0, 6))
        _mu_set(tube, "thickness", 0.0005)
        done += 1
    return design if done else None


# The cheats of the second 2026-11-19 review (round 2), rebuilt from the
# attackers' own edits. Each must stop at stage 5 (build), or at stage 6 for
# the two late-opening ones further down.
CARDBOARD = {"material": {"attrs": {"type": "bulk", "density": 680.0}, "value": "Cardboard"}}


def _mu_liftoff_guess(design: dict, table: Any) -> float:
    """A guess of the liftoff mass without a simulator: four times the flown
    motors' loaded mass (0 when no flown motor is known)."""
    motor_kg = 0.0
    for m in _mu_flown(design):
        key = _mu_key(table, m)
        kg = table.get(key).get("launch_mass_kg") if key else None
        if isinstance(kg, (int, float)) and kg > 0:
            motor_kg += float(kg)
    return LIFTOFF_PER_MOTOR_MASS * motor_kg


def _mu_weight(mass: float, method: str, at: float, length: float = 0.0, radius: float = 0.0) -> Node:
    """A mass component of `mass` kg placed `at` metres by `method`."""
    return {"masscomponent": {"children": [
        {"mass": {"value": mass}}, {"packedlength": {"value": length}}, {"packedradius": {"value": radius}},
        {"axialoffset": {"attrs": {"method": method}, "value": at}}]}}


def _mu_pod(children: list, radius_method: str, radius_offset: float, axial_method: str, axial: float,
            copies: int = 1) -> Node:
    """A pod set holding `children`, placed by the given radius and axial offsets."""
    return {"podset": {"children": [
        {"instancecount": {"value": copies}},
        {"radiusoffset": {"attrs": {"method": radius_method}, "value": radius_offset}},
        {"angleoffset": {"attrs": {"method": "relative"}, "value": 0.0}},
        {"axialoffset": {"attrs": {"method": axial_method}, "value": axial}},
        {"subcomponents": {"children": children}}]}}


def op_pod_weight_ahead_of_nose(design: dict, table: Any) -> Optional[Mutant]:
    """The review's "nose weight on a stick": fins at 0.6 times their size
    (unstable), and a one-copy pod (a 5 cm nose cone and a 10 cm tube, 10 mm
    in radius, or half the body's radius when that is less) on the first body
    tube, its front 2 m ahead of that tube's front, holding a weight of a
    tenth of the liftoff guess. The weight steadies the rocket from far ahead
    of the nose: stage 5 (pod_outside_airframe). On the attackers' V4-0060 it
    went 0.511 -> 1.0 before the rule; now 0.42 (build)."""
    tubes = _mu_parts(design, "bodytube")
    weight = round(POD_STICK_WEIGHT_SHARE * _mu_liftoff_guess(design, table), 4)
    if not tubes or weight <= 0:
        return None
    _mu_scale_fins(design, POD_STICK_FIN_FACTOR)
    r = round(min(POD_STICK_RADIUS_M, 0.5 * _mu_widest_radius(design)), 5)
    tube_kids = [dict(CARDBOARD), {"length": {"value": 0.1}}, {"thickness": {"value": 0.0005}},
                 {"radius": {"value": r}}, {"subcomponents": {"children": [_mu_weight(weight, "top", 0.01)]}}]
    nose = {"nosecone": {"children": [dict(CARDBOARD), {"length": {"value": 0.05}}, {"thickness": {"value": 0.0005}},
                                      {"shape": {"value": "ogive"}}, {"aftradius": {"value": r}}]}}
    _mu_holder(tubes[0]).append(_mu_pod([nose, {"bodytube": {"children": tube_kids}}],
                                        "relative", 0.0, "top", -POD_STICK_AHEAD_M))
    return design


def op_booster_weight_in_upper_stage(design: dict, table: Any) -> Optional[Mutant]:
    """On a multi-stage rocket, a weight of 0.15 times the liftoff guess
    (3 cm long, 8 mm in radius; at most half the density bound) owned by the
    bottom stage's first body tube but placed inside the top stage's nose
    cone (0.6 nose lengths behind the tip, an absolute position). It steadies
    the rocket on the way up and drops away with the booster: stage 5
    (part_ahead_of_stage). The attackers' V4-0051 scored 0.986 with it; now
    0.42 (build)."""
    stages = stages_of(_mu_view(design))
    if len(stages) < 2:
        return None
    nose = next((p for p in iter_components(stages[0]) if tag_of(p) == "nosecone"), None)
    tube = next((p for p in iter_components(stages[-1]) if tag_of(p) == "bodytube"), None)
    nose_len = _mu_num(nose, "length") if nose is not None else None
    if tube is None or nose_len is None or nose_len <= 0:
        return None
    length, radius = 0.03, 0.008
    cap = 0.5 * L.MASS_COMPONENT_DENSITY_MAX_KG_M3 * 3.141592653589793 * radius ** 2 * length
    weight = round(min(cap, BOOSTER_WEIGHT_SHARE * _mu_liftoff_guess(design, table)), 4)
    if weight <= 0:
        return None
    _mu_holder(tube).append(_mu_weight(weight, "absolute", round(BOOSTER_WEIGHT_AT_NOSE * nose_len, 4),
                                       length, radius))
    return design


def _mu_wrap_motor_in_pod(design: dict, outside: bool) -> Optional[Mutant]:
    """Every inner tube that holds a motor mount, in a body tube, wrapped in a
    one-copy pod (a 1 cm nose cone and a tube 1.04 times the inner tube's
    radius plus 0.8 mm, as long as the inner tube) at the back of that body
    tube, the motor tube at the front of the pod's tube. outside=False: the
    pod's axis on the rocket's centre line ("free" radius offset 0), so the
    motor still sits inside the body; outside=True: the pod flush on the
    outside of the body tube (its axis the body's radius plus the pod's
    radius from the centre line). Only where the pod is narrower than 0.98
    times the body tube."""
    done = 0
    for st in stages_of(_mu_view(design)):
        for parent in list(iter_components(st)):
            if tag_of(parent) != "bodytube":
                continue
            kids = _mu_holder(parent)
            for i, it in enumerate(list(kids)):
                if tag_of(it) != "innertube" or child(it, "motormount") is None:
                    continue
                r, length, big = _mu_num(it, "outerradius"), _mu_num(it, "length"), _mu_num(parent, "radius")
                if not r or not length or r <= 0 or length <= 0 or big is None or big <= 0:
                    continue
                pr = round(r * POD_WRAP_RADIUS_FACTOR + POD_WRAP_RADIUS_EXTRA_M, 6)
                if pr >= 0.98 * big:
                    continue
                inner = copy_tree(it)
                _mu_place(inner, "top", 0.0)
                shell = {"bodytube": {"children": [dict(CARDBOARD), {"length": {"value": length}},
                                                   {"thickness": {"value": 0.0005}}, {"radius": {"value": pr}},
                                                   {"subcomponents": {"children": [inner]}}]}}
                nose = {"nosecone": {"children": [dict(CARDBOARD), {"length": {"value": 0.01}},
                                                  {"thickness": {"value": 0.0005}}, {"shape": {"value": "conical"}},
                                                  {"aftradius": {"value": "auto"}}]}}
                offset = round(big + pr, 6) if outside else 0.0
                kids[i] = _mu_pod([nose, shell], "free", offset, "bottom", 0.0)
                done += 1
    return design if done else None


def op_motor_in_pod_inside_body(design: dict, table: Any) -> Optional[Mutant]:
    """The review's pod-wrapped motor: every motor tube wrapped in a one-copy
    pod whose axis is the rocket's centre line, inside the body tube. Before
    round 2, motors in pods skipped the motor-position rules, so the motor
    could fire into the airframe: stage 5 (pod_inside_body, and
    pod_motor_one_sided). The attackers' 26 such cases now build 0.41-0.44."""
    return _mu_wrap_motor_in_pod(design, outside=False)


def op_one_sided_motor_pod(design: dict, table: Any) -> Optional[Mutant]:
    """The same wrap, but the one-copy pod sits flush on the outside of the
    body tube: the motor pushes on one side of the rocket, which the
    simulator flies straight: stage 5 (pod_motor_one_sided)."""
    return _mu_wrap_motor_in_pod(design, outside=True)


def op_pod_far_to_the_side(design: dict, table: Any) -> Optional[Mutant]:
    """Every pod and side booster moved 0.25 m out from the body tube that
    holds it ("relative" radius offset), where nothing holds it: stage 5
    (pod_detached). Only designs with pods: one of the 16 val designs
    (row-025, which already stops at build: its pods sit on the centre
    line)."""
    pods = _mu_parts(design, *POD_TAGS)
    for p in pods:
        _mu_set(p, "radiusoffset", POD_SIDE_OFFSET_M, {"method": "relative"})
    return design if pods else None


def op_needle_rocket(design: dict, table: Any) -> Optional[Mutant]:
    """The first body tube lengthened until the rocket is at least 120 times
    as long as its widest written diameter, a tube that would buckle (the
    simulator does not model bending): stage 5 (slenderness). Only where the
    longer tube stays within limits.TUBE_LENGTH_MAX_M, so stage 4 lets it
    through: on the 16 val designs, row-016 and row-019 (the thinnest)."""
    tubes = _mu_parts(design, "bodytube")
    tube_len = _mu_num(tubes[0], "length") if tubes else None
    if tube_len is None or tube_len <= 0:
        return None
    need = NEEDLE_SLENDERNESS * 2.0 * _mu_widest_radius(design) - _mu_rocket_length(design)
    new = round(tube_len + need + 0.001, 4)
    if need <= 0 or new > L.TUBE_LENGTH_MAX_M:
        return None
    _mu_set(tubes[0], "length", new)
    return design


# The cheats of the third 2026-11-19 review (round 3), rebuilt from the
# attackers' own edits; each must stop at stage 5 (build).

def _mu_nose(radius: Any, length: float, shape: str = "ogive") -> Node:
    return {"nosecone": {"children": [dict(CARDBOARD), {"length": {"value": length}}, {"thickness": {"value": 0.001}},
                                      {"shape": {"value": shape}}, {"aftradius": {"value": radius}}]}}


def _mu_tube(radius: float, length: float, kids: Optional[list] = None) -> Node:
    body = [dict(CARDBOARD), {"length": {"value": length}}, {"thickness": {"value": 0.001}},
            {"radius": {"value": radius}}]
    if kids:
        body.append({"subcomponents": {"children": kids}})
    return {"bodytube": {"children": body}}


def op_motor_pods_inside_pods(design: dict, table: Any) -> Optional[Mutant]:
    """The attackers' nested pods: on the first body tube that holds a motor
    tube, two outer pods (0.3 times the body's radius, flush on its surface,
    at its back) each hold a one-copy pod whose motor tube is the design's
    own (moved there), its axis 0.6 inner-pod radii outside the outer pod's
    surface measured towards the rocket's axis: so the motor pods sit inside
    the main body and fire into it, while round 2 judged them against the
    outer pod's small radius only. Fins at 0.6 times their size. Only where
    the inner pod stays inside 0.98 times the body's radius. Stage 5
    (pod_in_pod, round 3): V4-0099 with fins x0.6 scored 0.7394 in round 2
    against 0.594 for the honest version; now 0.44 (build)."""
    for st in stages_of(_mu_view(design)):
        for parent in iter_components(st):
            if tag_of(parent) != "bodytube":
                continue
            kids = _mu_holder(parent)
            for i, it in enumerate(kids):
                if tag_of(it) != "innertube" or child(it, "motormount") is None:
                    continue
                big, length = _mu_num(parent, "radius"), _mu_num(parent, "length")
                rm, lt = _mu_num(it, "outerradius"), _mu_num(it, "length")
                if not all(x is not None and x > 0 for x in (big, length, rm, lt)):
                    return None
                ro = round(NESTED_OUTER_RADIUS_SHARE * big, 6)
                ri = round(rm + 0.001, 6)
                axis = ro + NESTED_SUNK_SHARE * ri    # the inner pod's axis from the rocket's centre line
                if axis + ri > 0.98 * big:
                    return None
                outer_len = round(min(0.4 * length, max(lt + 0.05, 0.2)), 6)
                inner_tube = copy_tree(it)
                _mu_place(inner_tube, "top", 0.0)
                inner = _mu_pod([_mu_nose(ri, 0.01), _mu_tube(ri, lt, [inner_tube])],
                                "free", round(big + ro - axis, 6), "bottom", 0.0)
                _mu_set(inner, "angleoffset", 180.0, {"method": "relative"})
                outer = _mu_pod([_mu_nose(ro, 0.05), _mu_tube(ro, outer_len, [inner])], "surface", 0.0,
                                "bottom", 0.0, copies=2)
                kids.pop(i)
                kids.append(outer)
                _mu_scale_fins(design, NESTED_FIN_FACTOR)
                return design
    return None


def op_booster_pod_beside_upper_stage(design: dict, table: Any) -> Optional[Mutant]:
    """On a multi-stage rocket, two pods (a 4 cm nose cone and a 12 cm tube,
    0.3 times the widest radius) held by the bottom stage's first body tube
    but placed beside the top stage's nose (their front 0.5 nose lengths
    behind the tip, an absolute position), each holding half of 0.15 times
    the liftoff guess (at most half the density bound). They lie inside the
    whole rocket's span, but would drop away from the stage they touch:
    stage 5 (pod_outside_airframe, judged since round 3 against the shells
    of the stage that holds the pod). The attackers' V4-0050, V4-0051 and
    V4-0063 scored 0.972, 0.986 and 0.965 in round 2; now 0.42 (build)."""
    stages = stages_of(_mu_view(design))
    if len(stages) < 2:
        return None
    nose = next((p for p in iter_components(stages[0]) if tag_of(p) == "nosecone"), None)
    tube = next((p for p in iter_components(stages[-1]) if tag_of(p) == "bodytube"), None)
    nose_len = _mu_num(nose, "length") if nose is not None else None
    if tube is None or nose_len is None or nose_len <= 0:
        return None
    r = round(SIDE_POD_RADIUS_SHARE * _mu_widest_radius(design), 5)
    wl, wr = 0.03, round(0.8 * r, 6)
    cap = 0.5 * L.MASS_COMPONENT_DENSITY_MAX_KG_M3 * 3.141592653589793 * wr ** 2 * wl
    weight = round(min(cap, 0.5 * SIDE_POD_WEIGHT_SHARE * _mu_liftoff_guess(design, table)), 4)
    if weight <= 0:
        return None
    pod = _mu_pod([_mu_nose(r, 0.04), _mu_tube(r, 0.12, [_mu_weight(weight, "top", 0.0, wl, wr)])],
                  "surface", 0.0, "absolute", round(SIDE_POD_AT_NOSE * nose_len, 4), copies=2)
    _mu_holder(tube).append(pod)
    return design


def op_needle_rocket_with_tail_disk(design: dict, table: Any) -> Optional[Mutant]:
    """The needle_rocket edit, plus a flared transition 2 mm long behind the
    bottom stage's last shell, opening from that shell's radius to 2.5 times
    it: in round 2 the widest diameter counted, so the disk cut the measured
    ratio of a 100:1 rocket to 40. Since round 3 the width is the largest
    diameter that at least limits.SLENDERNESS_WIDTH_SHARE of the main body's
    length has, so the disk does not count: stage 5 (slenderness). The
    attackers' V4-0050 at 100 times with the disk scored 0.8158 in round 2;
    now 0.446 (build)."""
    width = _mu_widest_radius(design)
    if op_needle_rocket(design, table) is None:
        return None
    bottom = _mu_bottom_stage(design)
    shells = [p for p in _mu_holder_parts(bottom) if tag_of(p) in SHELL_TAGS] if bottom is not None else []
    if not shells:
        return None
    last = shells[-1]
    r = next((v for v in (_mu_num(last, "radius"), _mu_num(last, "aftradius")) if v is not None and v > 0), width)
    _mu_holder(bottom).append({"transition": {"children": [
        dict(CARDBOARD), {"length": {"value": TAIL_DISK_LENGTH_M}}, {"thickness": {"value": 0.001}},
        {"shape": {"value": "conical"}}, {"foreradius": {"value": r}},
        {"aftradius": {"value": round(TAIL_DISK_RADIUS_FACTOR * r, 6)}}]}})
    return design


# --------------------------------------------------------------------------- stage 6: flight

def _mu_largest_impulse(design: dict, table: Any) -> float:
    best = 0.0
    for m in _mu_flown(design):
        key = _mu_key(table, m)
        ns = table.get(key).get("total_impulse_ns") if key else None
        if isinstance(ns, (int, float)):
            best = max(best, float(ns))
    return best


def op_zero_ejection_delay(design: dict, table: Any) -> Optional[Mutant]:
    """On a fast rocket (an H motor or bigger), every recovery device opens at
    motor ejection with a 0 s delay: right at burnout, at top speed."""
    if _mu_largest_impulse(design, table) < 160.0:
        return None
    devices = _mu_parts(design, *RECOVERY_TAGS)
    if not devices:
        return None
    for d in devices:
        _mu_set(d, "deployevent", "ejection")
        _mu_set(d, "deploydelay", 0.0)
    for m in _mu_flown(design):
        _mu_set(m, "delay", 0.0)
    return design


def _mu_chutes(design: dict) -> Optional[list[tuple[Node, float]]]:
    """(parachute, diameter) for every parachute, on a design that lands on
    parachutes alone (no streamer) and writes every diameter; else None."""
    if _mu_parts(design, "streamer"):
        return None
    chutes = [(c, _mu_num(c, "diameter")) for c in _mu_parts(design, "parachute")]
    if not chutes or any(s is None or s <= 0 for _, s in chutes):
        return None
    return chutes   # type: ignore[return-value]


def op_chute_far_too_small(design: dict, table: Any) -> Optional[Mutant]:
    """Every parachute a fifth of its size (at least the catalogue's smallest,
    0.15 m); only on designs that land on parachutes alone, and only where the
    largest parachute really shrinks at least four times, so the landing is
    about four times as fast or more and clearly past the 9 m/s safety limit
    (limits.LANDING_HARD_MAX_MS; references land at 3.6 to 8 m/s). A small
    parachute held up by the 0.15 m floor (row-016's 0.30 m one shrinks only
    twice and lands at 7.8 m/s) is a miss of the prompt's landing number, which
    chute_too_small_for_prompt covers."""
    chutes = _mu_chutes(design)
    if chutes is None:
        return None
    new = [max(L.CHUTE_DIAMETER_MIN_M, round(s / FAR_SMALL_CHUTE_DIVISOR, 4)) for _, s in chutes]
    largest = max(range(len(chutes)), key=lambda i: chutes[i][1])
    if chutes[largest][1] / new[largest] < FAR_SMALL_CHUTE_MIN_SHRINK:
        return None
    for (c, _), d in zip(chutes, new):
        _mu_set(c, "diameter", d)
    return design


def _mu_landing_limit(requirements: Any) -> Optional[tuple[float, float]]:
    """(the prompt's landing number, its tolerance) for a "max" landing target, else None.
    Without a written tolerance stage 7 allows limits.LANDING_SLACK_DEFAULT."""
    t = requirements.get("landing_ms") if isinstance(requirements, dict) else None
    if not isinstance(t, dict) or t.get("kind") != "max":
        return None
    v = t.get("value")
    if not isinstance(v, (int, float)) or isinstance(v, bool) or v <= 0:
        return None
    tol = t.get("tol")
    tol = float(tol) if isinstance(tol, (int, float)) and not isinstance(tol, bool) and tol >= 0 \
        else L.LANDING_SLACK_DEFAULT
    return float(v), tol


def _mu_land_at(design: dict, landing_now: float, landing_ms: float) -> Optional[Mutant]:
    """Every parachute scaled so a design landing at `landing_now` lands at
    `landing_ms` (speed goes as 1 / diameter). None when a parachute would fall
    under the catalogue's smallest (the speed would then not follow)."""
    chutes = _mu_chutes(design)
    if chutes is None:
        return None
    factor = landing_now / landing_ms
    new = [round(s * factor, 4) for _, s in chutes]
    if min(new) < L.CHUTE_DIAMETER_MIN_M:
        return None
    for (c, _), d in zip(chutes, new):
        _mu_set(c, "diameter", d)
    return design


def op_chute_too_small_for_prompt(design: dict, table: Any, requirements: Any) -> Optional[Mutant]:
    """On a single-stage design, every parachute shrunk so the rocket lands
    1.17 times past the prompt's own landing number with its slack (1.35
    times the number at the usual 15%), but well under the 9 m/s safety
    limit: only where that is under 0.9 x 9 m/s (the prompt's number stands
    in for the reference's landing speed, which it exceeds by up to 6% on the
    val answers). Single-stage only, so no other section's landing is pushed
    past 9 m/s. Stage 6 has no rule on the prompt's number since 2026-11-19,
    so this must reach the targets stage with a lower score. Where a prompt's
    number is well above the reference's own landing the shrink is too small:
    on the 197 reference designs (2026-11-19), 4 of the 20 judged ones
    (V4-0069, V4-0099, V4-0154, V4-0156, landing at 0.75-0.82 times their
    prompt's number) still meet it and keep 1.0."""
    got = _mu_landing_limit(requirements)
    if got is None or _mu_single_stage(design) is None:
        return None
    limit, tol = got
    target = PROMPT_MISS_PAST_BAND * (1.0 + tol) * limit
    if target > PROMPT_MISS_HARD_SHARE * L.LANDING_HARD_MAX_MS:
        return None
    return _mu_land_at(design, limit, target)


def op_landing_just_under_hard_limit(design: dict, table: Any, requirements: Any) -> Optional[Mutant]:
    """On a single-stage design, every parachute shrunk so the rocket lands
    at about 8.8 m/s, just under the 9 m/s safety limit, on a design whose prompt asks for much less (the
    body's own drag keeps the val designs at 7.5 to 8.6 m/s): only where
    8.8 m/s is at least 1.1 times past the prompt's landing number with
    its slack. It must reach the targets stage and score lower than the
    original (closeness, not a stage 6 stop). On the 197 reference designs
    (2026-11-19) it did so on 36 of the 38 judged ones; the other two
    (V4-0016, V4-0150) sit at 1.0 cal on the pad, and the lighter parachute
    leaves them at 0.99-0.996 cal, which stage 6 stops."""
    got = _mu_landing_limit(requirements)
    if got is None or _mu_single_stage(design) is None:
        return None
    limit, tol = got
    if NEAR_HARD_LANDING_MS < NEAR_HARD_PROMPT_MARGIN * (1.0 + tol) * limit:
        return None
    return _mu_land_at(design, limit, NEAR_HARD_LANDING_MS)


def op_fins_shrunk(design: dict, table: Any) -> Optional[Mutant]:
    """Every fin set shrunk to a quarter of its span and chords (an unstable rocket)."""
    return design if _mu_scale_fins(design, 0.25) else None


def op_booster_without_recovery(design: dict, table: Any) -> Optional[Mutant]:
    """On a rocket with more than one stage, the bottom stage (booster) loses its
    recovery and carries 0.5 kg more, so it falls hard."""
    stages = stages_of(_mu_view(design))
    if len(stages) < 2:
        return None
    gone = 0
    for node in walk_nodes(stages[-1]):
        kids = child_list(node)
        if kids is None:
            continue
        keep = [c for c in kids if tag_of(c) not in RECOVERY_TAGS]
        gone += len(kids) - len(keep)
        kids[:] = keep
    tubes = [c for c in iter_components(stages[-1]) if tag_of(c) == "bodytube"]
    if not gone or not tubes:
        return None
    _mu_holder(tubes[0]).append({"masscomponent": {"children": [
        {"axialoffset": {"attrs": {"method": "top"}, "value": 0.0}}, {"mass": {"value": 0.5}},
        {"packedlength": {"value": 0.02}}, {"packedradius": {"value": 0.005}}]}})
    return design


def _mu_open_at(devices: list, altitude: float) -> bool:
    """Set every device to open at `altitude` metres on the way down, with no delay; False for no device."""
    for d in devices:
        _mu_set(d, "deployevent", "altitude")
        _mu_set(d, "deployaltitude", altitude)
        _mu_set(d, "deploydelay", 0.0)
    return bool(devices)


def op_parachute_opens_at_ground(design: dict, table: Any) -> Optional[Mutant]:
    """Every parachute and streamer set to open 4 m above the ground (as in
    the review, any drogue goes too). OpenRocket fills a parachute the
    instant it opens, so before round 2 a 23 kg rocket falling at 34 m/s
    "landed softly" and scored 1.0: stage 6 (the device is set below
    limits.DEPLOY_ALTITUDE_MIN_M, and it opens less than
    limits.RECOVERY_OPEN_BEFORE_LANDING_MIN_S before landing)."""
    return design if _mu_open_at(_mu_parts(design, *RECOVERY_TAGS), GROUND_OPEN_ALTITUDE_M) else None


def op_main_opens_low_drogue_kept(design: dict, table: Any) -> Optional[Mutant]:
    """Every parachute set to open 15 m above the ground; streamers keep their
    settings (a drogue streamer still opens where it did): stage 6 (the
    parachute is set below limits.DEPLOY_ALTITUDE_MIN_M)."""
    return design if _mu_open_at(_mu_parts(design, "parachute"), LOW_MAIN_ALTITUDE_M) else None


# --------------------------------------------------------------------------- worse but honest

def op_weaker_motor(design: dict, table: Any) -> Optional[Mutant]:
    """Every flown motor replaced by a real motor of the same diameter one class lower."""
    motors = _mu_flown(design)
    if not motors:
        return None
    entries = _mu_entries()
    for m in motors:
        key = _mu_key(table, m)
        if key is None:
            return None
        e = table.get(key)
        letter = table.class_of(key)
        dia, ns = e.get("diameter_m"), e.get("total_impulse_ns")
        if not letter or letter == "A" or not isinstance(dia, (int, float)) or not isinstance(ns, (int, float)):
            return None
        lower = chr(ord(letter) - 1)
        pool = [k for k, v in entries.items() if table.class_of(k) == lower
                and isinstance(v.get("diameter_m"), (int, float)) and abs(v["diameter_m"] - dia) <= 0.0005]
        same_type = [k for k in pool if entries[k].get("motor_type") == e.get("motor_type")]
        pool = same_type or pool
        if not pool:
            return None
        pick = min(pool, key=lambda k: (abs(float(entries[k].get("total_impulse_ns") or 0) - ns / 2.0), k))
        _mu_set_motor(m, pick, entries[pick])
    return design


def op_swap_to_unnamed_motor(design: dict, table: Any) -> Optional[Mutant]:
    """Every flown motor replaced by a real motor of the next class down (the
    next class up when there is none), same diameter and type, no more than
    10% longer, whose total impulse is the closest at least 1.3 times away,
    with at least 0.8 times the average thrust, and recovery that opened at
    motor ejection opens at apogee: a real motor, so every stage passes, but
    not the one the design (or its prompt) names. Since
    2026-11-19 a motor the prompt names but the answer does not fly halves
    stage 7's credit (ladder.MOTORS_CREDIT_MIN) instead of zeroing it, and
    the apogee moves too; so the copy must reach the targets stage and score
    lower than the original. (A design that misses its apogee by more than
    about 1.35 times with the named motor can score higher with a swap that
    meets it: that trade-off is by design and is not what this operator
    builds.)"""
    motors = _mu_flown(design)
    if not motors:
        return None
    entries = _mu_entries()
    for m in motors:
        key = _mu_key(table, m)
        if key is None:
            return None
        e = table.get(key)
        letter = table.class_of(key)
        dia, ns, length = e.get("diameter_m"), e.get("total_impulse_ns"), e.get("length_m")
        thrust = e.get("average_thrust_n")
        if not letter or not all(isinstance(x, (int, float)) and x > 0 for x in (dia, ns, length, thrust)):
            return None
        pick = None
        for step in (-1, 1):
            other = chr(ord(letter) + step)
            pool = [k for k, v in entries.items() if table.class_of(k) == other
                    and v.get("motor_type") == e.get("motor_type")
                    and isinstance(v.get("diameter_m"), (int, float)) and abs(v["diameter_m"] - dia) <= 0.0005
                    and isinstance(v.get("length_m"), (int, float)) and v["length_m"] <= SWAP_LENGTH_MAX_RATIO * length
                    and isinstance(v.get("average_thrust_n"), (int, float)) and v["average_thrust_n"] >= 0.8 * thrust
                    and isinstance(v.get("total_impulse_ns"), (int, float)) and v["total_impulse_ns"] > 0
                    and max(v["total_impulse_ns"] / ns, ns / v["total_impulse_ns"]) >= SWAP_IMPULSE_MIN_RATIO]
            if pool:
                pick = min(pool, key=lambda k: (abs(float(entries[k]["total_impulse_ns"]) - ns), k))
                break
        if pick is None:
            return None
        _mu_set_motor(m, pick, entries[pick])
    # The design's ejection delay was chosen for its own motor; with another
    # motor it can open the recovery on the way up or after landing (seen on
    # V4-0018, V4-0150 and V4-0273), so a device that opens at motor ejection
    # opens at apogee instead, as a designer swapping motors would set it.
    for d in _mu_parts(design, *RECOVERY_TAGS):
        c = last_child(d, "deployevent")
        if c is not None and str(value_of(c)).strip().lower() == "ejection":
            _mu_set(d, "deployevent", "apogee")
            _mu_set(d, "deploydelay", 0.0)
    return design


# --------------------------------------------------------------------------- cheats that must change nothing

def op_drag_override(design: dict, table: Any) -> Optional[Mutant]:
    """Every stage's drag overridden to 0.01 (the cleaning removes drag overrides)."""
    stages = stages_of(_mu_view(design))
    for st in stages:
        _mu_set(st, "overridecd", 0.01)
        _mu_set(st, "overridesubcomponentscd", True)
    return design if stages else None


def op_delayed_ignition(design: dict, table: Any) -> Optional[Mutant]:
    """The bottom stage's motors light 16 s after launch, so the rocket sits on the pad
    (the cleaning sets that delay to 0)."""
    bottom = _mu_bottom_stage(design)
    if bottom is None:
        return None
    done = 0
    for comp in iter_components(bottom):
        for mm in children_named(comp, "motormount"):
            _mu_set(mm, "ignitiondelay", 16.0)
            for ic in children_named(mm, "ignitionconfiguration"):
                _mu_set(ic, "ignitiondelay", 16.0)
            done += 1
    return design if done else None


def op_model_digest(design: dict, table: Any) -> Optional[Mutant]:
    """Every flown motor carries the digest of the strongest real motor of its
    diameter (OpenRocket finds a motor by its digest; the cleaning rewrites it)."""
    motors = _mu_flown(design)
    if not motors:
        return None
    entries = _mu_entries()
    for m in motors:
        key = _mu_key(table, m)
        if key is None:
            return None
        dia = table.get(key).get("diameter_m")
        pool = [k for k, v in entries.items() if k != key and v.get("digest")
                and isinstance(v.get("diameter_m"), (int, float)) and isinstance(dia, (int, float))
                and abs(v["diameter_m"] - dia) <= 0.0005]
        if not pool:
            return None
        pick = max(pool, key=lambda k: (float(entries[k].get("total_impulse_ns") or 0), k))
        _mu_set(m, "digest", entries[pick]["digest"])
    return design


def op_extra_top_level_key(design: dict, table: Any) -> Optional[Mutant]:
    """Next to "openrocket", a "simulations" key and a second rocket with a Cd 50
    parachute (other top-level keys are ignored)."""
    shadow = copy_tree(design.get("openrocket"))
    design["simulations"] = {"simulation": {"children": [{"launchrodlength": {"value": 50.0}},
                                                         {"windaverage": {"value": 0.0}}]}}
    design["openrocket_v2"] = shadow
    for node in walk_nodes({"openrocket_v2": shadow}):
        if tag_of(node) == "parachute":
            _mu_set(node, "cd", 50.0)
    return design


# --------------------------------------------------------------------------- honest edits

def op_honest_second_holder(design: dict, table: Any) -> Optional[Mutant]:
    """The last half of one body tube's parts moved, in order, to a second holder
    (OpenRocket adds the parts of every holder)."""
    for tube in _mu_parts(design, "bodytube"):
        holder = child(tube, "subcomponents")
        parts = child_list(holder) if holder is not None else None
        if parts is None or len(parts) < 2:
            continue
        # The second holder must come last among the tube's holders, so the order is kept.
        if [tag_of(c) for c in children_of(tube)].count("subcomponents") != 1:
            continue
        half = len(parts) // 2
        moved = parts[half:]
        parts[:] = parts[:half]
        _mu_kids(tube).append(make_node("subcomponents", children=moved))
        return design
    return None


def op_numbers_as_text(design: dict, table: Any) -> Optional[Mutant]:
    """Every fin thickness written as plain number text ("0.003")."""
    fins = _mu_parts(design, *ALL_FIN_TAGS)
    done = 0
    for f in fins:
        v = _mu_num(f, "thickness")
        if v is not None:
            _mu_set(f, "thickness", repr(v))
            done += 1
    return design if done else None


def op_slipped_density(design: dict, table: Any) -> Optional[Mutant]:
    """Every material density written a million times too small (a unit slip; the
    cleaning gives every known material its table density)."""
    found = 0
    for node in walk_nodes(_mu_view(design)):
        if tag_of(node) in ("material", "filletmaterial", "linematerial"):
            attrs = body_of(node).get("attrs")
            v = read_number(attrs.get("density"))[0] if isinstance(attrs, dict) else None
            if v is not None and v > 0:
                attrs["density"] = v * 1e-6   # type: ignore[index]
                found += 1
    return design if found else None


# --------------------------------------------------------------------------- repairs of model answers

def _mu_stops_at(design: dict, table: Any) -> Optional[str]:
    """Where the design as it stands stops in stages 1-4 (None: it passes them)."""
    got = preflight_outcome("<design>" + json.dumps(design) + "</design>", table)
    return None if got is None else got.stage


def op_repair_motor_spelling(design: dict, table: Any) -> Optional[Mutant]:
    """On an answer that stops at the motor stage, every unknown flown motor
    renamed to the real motor it plainly means: the table's suggestion, when it
    sells the same designation (only the maker, an "HP-" prefix or the version
    differ)."""
    from rocket_reward.motors import _norm_designation
    if _mu_stops_at(design, table) != "motor":
        return None
    motors = _mu_flown(design)
    unknown = [m for m in motors if _mu_key(table, m) is None]
    if not unknown:
        return None
    for m in unknown:
        mid, maker, des = _mu_motor_fields(m)
        if not isinstance(des, str) and isinstance(mid, str):
            prefix = table.maker_prefix(mid)
            des = mid[len(prefix) + 1:] if prefix else None
        guess = table.suggest(mid, des)
        if guess is None or not isinstance(des, str):
            return None
        entry = table.get(guess)
        if _norm_designation(str(entry.get("designation"))) != _norm_designation(des):
            return None
        _mu_set_motor(m, guess, entry)
    return design


def op_repair_stray_parts(design: dict, table: Any) -> Optional[Mutant]:
    """On an answer that stops at the parts stage, parts written straight into a
    part's settings (outside its "subcomponents") moved into its holder, when
    OpenRocket accepts them there."""
    if _mu_stops_at(design, table) != "parts":
        return None
    stray: list[tuple[Node, Node]] = []
    for node in walk_nodes(_mu_view(design)):
        here = tag_of(node)
        if here != "rocket" and here not in KNOWN_COMPONENT_TYPES:
            continue
        for c in children_of(node):
            if tag_of(c) in KNOWN_COMPONENT_TYPES:
                stray.append((node, c))
    if not stray or not all(is_legal_child(tag_of(p), tag_of(c)) for p, c in stray):
        return None
    for parent, part in stray:
        kids = _mu_kids(parent)
        kids[:] = [k for k in kids if k is not part]
        _mu_holder(parent).append(part)
    return design


# --------------------------------------------------------------------------- the list

OPERATORS: tuple[Operator, ...] = (
    Operator("tag_not_xml", "format", "a setting's tag has a space in it, so it is not valid XML", op_tag_not_xml),
    Operator("cut_off", "format", "the design text stops half-way with no closing tag", op_cut_off),
    Operator("motor_deleted", "parts", "every motor deleted", op_motor_deleted),
    Operator("recovery_deleted", "parts", "every parachute and streamer deleted", op_recovery_deleted),
    Operator("config_id_missing", "parts", "the motor configurations have no configuration id",
             op_config_id_missing),
    Operator("invented_motor", "motor", "every flown motor renamed to a designation no maker sells",
             op_invented_motor),
    Operator("near_miss_motor", "motor", "one digit of every flown motor's designation changed",
             op_near_miss_motor),
    Operator("wrong_version_suffix", "motor", "every flown motor id given a version suffix (-v9) no motor has",
             op_wrong_version_suffix),
    Operator("second_default_config", "motor", "a second configuration marked default, flying invented motors",
             op_second_default_config),
    Operator("chute_cd_over_limit", "limits", "every parachute's drag coefficient 50", op_chute_cd_over_limit),
    Operator("chute_too_large", "limits", "every parachute 20 m across", op_chute_too_large),
    Operator("razor_fins", "limits", "every fin 0.01 mm thick", op_razor_fins),
    Operator("java_number_text", "limits", "razor fins written as Java-only number text '0.00001f'",
             op_java_number_text),
    Operator("paper_thin_walls", "limits", "every shell wall 0.01 mm, its mass overrides removed",
             op_paper_thin_walls),
    Operator("foam_walls", "limits", "shells and fins of foam at the thinnest allowed thickness", op_foam_walls),
    Operator("air_brake_fins", "limits", "fin span six times the body diameter", op_air_brake_fins),
    Operator("giant_lug", "limits", "a launch lug 0.3 m wide and 0.76 m long", op_giant_lug),
    Operator("hundreds_of_parts", "limits", "300 tiny launch lugs", op_hundreds_of_parts),
    Operator("made_up_material", "limits", "every bulk material named 'Unobtainium alloy'", op_made_up_material),
    Operator("repeated_setting", "limits", "every parachute's drag written twice, the second copy 50",
             op_repeated_setting),
    Operator("paper_tail_cone", "limits", "a pointed paper tail cone with a 0.025 mm wall", op_paper_tail_cone),
    Operator("cheat_parts_in_second_holder", "limits",
             "razor fins and a Cd 50 parachute in a second 'subcomponents' holder",
             op_cheat_parts_in_second_holder),
    Operator("zero_width_nose", "limits", "every nose cone's base radius written as 0", op_zero_width_nose),
    Operator("auto_negative", "limits", "every body tube's radius written 'auto -0.0125'", op_auto_negative),
    Operator("giant_packed_chute", "limits", "every parachute's and shock cord's packed length 1000 times longer",
             op_giant_packed_chute),
    Operator("floating_fin_root", "limits", "every trapezoid and elliptical fin's root chord 0.05 mm",
             op_floating_fin_root),
    Operator("absurd_rail_button", "limits", "every rail button's base 2 m high (one is added when there is none)",
             op_absurd_rail_button),
    Operator("broken_counts", "limits", "parachute shroud lines 2.5 and launch lug copies 1.5", op_broken_counts),
    Operator("endless_delay", "limits", "every recovery device opens 1e308 s after its event", op_endless_delay),
    Operator("coin_weight", "limits", "a 19 kg mass component 2 mm long and 12.5 mm in radius", op_coin_weight),
    Operator("absurd_angle_or_offset", "limits",
             "launch lugs and rail buttons turned 1e308 degrees, mass components 2 m off the axis",
             op_absurd_angle_or_offset),
    Operator("floating_fins", "build", "every fin set 1.5 root chords behind its part", op_floating_fins),
    Operator("duplicated_fin_sets", "build", "every fin set written twice in the same place",
             op_duplicated_fin_sets),
    Operator("motor_far_forward", "build", "the motor's inner tube moved to the front of its body tube",
             op_motor_far_forward),
    Operator("motor_too_wide", "build", "the motor's inner tube 0.55 times the motor's radius", op_motor_too_wide),
    Operator("far_away_thin_part", "build", "a ring, bulkhead or engine block of at most 6 mm placed 1.5 m "
             "ahead of the nose", op_far_away_thin_part),
    Operator("far_away_mass", "build", "a mass component placed 1.5 m ahead of the nose", op_far_away_mass),
    Operator("far_away_recovery", "build", "a parachute, streamer or shock cord placed 1 m behind the tail",
             op_far_away_recovery),
    Operator("pod_part_far_away", "build", "a part inside a pod placed 1 m ahead of the pod's shell",
             op_pod_part_far_away),
    Operator("lug_behind_tail", "build", "every launch lug and rail button placed 1 m behind the tail",
             op_lug_behind_tail),
    Operator("closed_tail", "build", "the tail closed to a 0.01 mm point around the motor", op_closed_tail),
    Operator("pod_weight_ahead_of_nose", "build",
             "fins at 0.6 times, and a weighted one-copy pod held 2 m ahead of the first body tube",
             op_pod_weight_ahead_of_nose),
    Operator("booster_weight_in_upper_stage", "build",
             "a weight owned by the booster placed inside the top stage's nose cone", op_booster_weight_in_upper_stage),
    Operator("motor_in_pod_inside_body", "build",
             "every motor tube wrapped in a one-copy pod on the centre line, inside the body",
             op_motor_in_pod_inside_body),
    Operator("one_sided_motor_pod", "build",
             "every motor tube wrapped in a one-copy pod flush on the outside of the body", op_one_sided_motor_pod),
    Operator("pod_far_to_the_side", "build", "every pod and side booster 0.25 m out from its body tube",
             op_pod_far_to_the_side),
    Operator("needle_rocket", "build", "the first body tube lengthened to 120 times the widest diameter",
             op_needle_rocket),
    Operator("motor_pods_inside_pods", "build",
             "the motor tube moved into pods nested in two outer pods, so it sits inside the body; fins at 0.6 times",
             op_motor_pods_inside_pods),
    Operator("booster_pod_beside_upper_stage", "build",
             "two weighted pods held by the booster but placed beside the top stage's nose",
             op_booster_pod_beside_upper_stage),
    Operator("needle_rocket_with_tail_disk", "build",
             "the needle_rocket edit plus a 2 mm flared disk 2.5 times the body's width at the tail",
             op_needle_rocket_with_tail_disk),
    Operator("zero_ejection_delay", "flight", "on an H-or-bigger rocket, recovery opens at burnout (0 s delay)",
             op_zero_ejection_delay),
    Operator("chute_far_too_small", "flight", "every parachute a fifth of its size (it lands past 9 m/s)",
             op_chute_far_too_small),
    Operator("fins_shrunk", "flight", "every fin set a quarter of its size (unstable)", op_fins_shrunk),
    Operator("booster_without_recovery", "flight",
             "the booster of a multi-stage rocket loses its recovery and carries 0.5 kg more",
             op_booster_without_recovery),
    Operator("parachute_opens_at_ground", "flight", "every parachute and streamer opens 4 m above the ground",
             op_parachute_opens_at_ground),
    Operator("main_opens_low_drogue_kept", "flight", "every parachute opens 15 m above the ground, streamers kept",
             op_main_opens_low_drogue_kept),
    Operator("weaker_motor", EXPECT_LOWER, "every motor replaced by a real one a class lower, same diameter",
             op_weaker_motor),
    Operator("chute_too_small_for_prompt", EXPECT_LOWER_IN_TARGETS,
             "parachutes shrunk to land 1.17 times past the prompt's landing number and slack, under 9 m/s",
             op_chute_too_small_for_prompt, uses_requirements=True),
    Operator("landing_just_under_hard_limit", EXPECT_LOWER_IN_TARGETS,
             "parachutes shrunk to land at about 8.8 m/s on a prompt that asks for much less",
             op_landing_just_under_hard_limit, uses_requirements=True),
    Operator("swap_to_unnamed_motor", EXPECT_LOWER_IN_TARGETS,
             "every motor replaced by a real one of the next class, same diameter, not the one named",
             op_swap_to_unnamed_motor),
    Operator("drag_override", EXPECT_SAME, "every stage's drag overridden to 0.01", op_drag_override),
    Operator("override_over_limit", EXPECT_SAME, "the nose cone's mass overridden to 50 kg", op_override_over_limit),
    Operator("override_negative", EXPECT_SAME, "the nose cone's mass overridden to -1 kg", op_override_negative),
    Operator("ballast_overrides", EXPECT_SAME, "every nose cone and body tube overridden to 20 kg",
             op_ballast_overrides),
    Operator("ballast_cg_override", EXPECT_SAME, "every stage's balance point overridden to its front end",
             op_ballast_cg_override),
    Operator("lighten_rocket_override", EXPECT_SAME, "every stage's mass overridden to 1 g",
             op_lighten_rocket_override),
    Operator("lighten_one_stage_override", EXPECT_SAME, "the top stage of a multi-stage rocket overridden to 1 g",
             op_lighten_one_stage_override),
    Operator("unstable_fake_cg_override", "flight",
             "fins halved (unstable), then the stage's balance point overridden forward; scores as without the tags",
             op_unstable_fake_cg_override, untagged=untagged_unstable_fins),
    Operator("light_stage_mass_override", EXPECT_SAME,
             "parachutes at 0.6x (or a weaker motor), then the stage's mass overridden to half the liftoff mass; "
             "scores as without the tags", op_light_stage_mass_override, untagged=untagged_small_chutes),
    Operator("delayed_ignition", EXPECT_SAME, "the bottom stage's motors light 16 s after launch",
             op_delayed_ignition),
    Operator("model_digest", EXPECT_SAME, "each motor carries the digest of the strongest motor of its size",
             op_model_digest),
    Operator("extra_top_level_key", EXPECT_SAME, "a 'simulations' key and a second rocket next to 'openrocket'",
             op_extra_top_level_key),
    Operator("honest_second_holder", EXPECT_SAME_OR_HIGHER, "half of one tube's parts moved to a second holder",
             op_honest_second_holder),
    Operator("numbers_as_text", EXPECT_SAME_OR_HIGHER, "fin thickness written as number text",
             op_numbers_as_text),
    Operator("slipped_density", EXPECT_SAME_OR_HIGHER, "every material density written a million times too small",
             op_slipped_density),
    Operator("repair_motor_spelling", EXPECT_HIGHER, "an invented motor renamed to the real motor it plainly means",
             op_repair_motor_spelling, repair=True),
    Operator("repair_stray_parts", EXPECT_HIGHER, "parts written outside 'subcomponents' moved into it",
             op_repair_stray_parts, repair=True),
)


def operator_named(name: str) -> Operator:
    """The operator called `name` (KeyError for an unknown name)."""
    for op in OPERATORS:
        if op.name == name:
            return op
    raise KeyError(f"no mutation operator is called {name!r}; known: {', '.join(o.name for o in OPERATORS)}")


# --------------------------------------------------------------------------- designs and mutants

@dataclass
class DesignCase:
    """One distinct design taken from an answer file."""

    id: str                 # id of the first row that carries this design block
    rows: list[str]         # every row id with the same block
    design: dict            # the parsed design JSON (the whole object between the tags)
    prefix: str             # answer text before <design>
    suffix: str             # answer text after </design>
    requirements: Any       # the requirements record (dict) of the first row


def collect_designs(rows: Sequence[dict]) -> tuple[list[DesignCase], list[str]]:
    """Distinct designs of answer rows (as tools.calibrate.answer_rows gives
    them), with the rows whose design could not be read."""
    from rocket_reward.parse import CLOSE_TAG, OPEN_TAG, find_design_block
    by_block: dict[str, DesignCase] = {}
    unread: list[str] = []
    for r in rows:
        text = str(r.get("answer") or "")
        block, _ = find_design_block(text)
        try:
            design = json.loads(block) if block is not None else None
        except ValueError:
            design = None
        if not isinstance(design, dict) or not isinstance(design.get("openrocket"), dict):
            unread.append(str(r.get("id")))
            continue
        key = json.dumps(design, sort_keys=True)
        if key in by_block:
            by_block[key].rows.append(str(r.get("id")))
            continue
        whole = OPEN_TAG + block + CLOSE_TAG   # type: ignore[operator]
        at = text.find(whole)
        by_block[key] = DesignCase(id=str(r.get("id")), rows=[str(r.get("id"))], design=design,
                                   prefix=text[:at], suffix=text[at + len(whole):],
                                   requirements=r.get("requirements"))
    return list(by_block.values()), unread


def mutant_answer(case: DesignCase, mutant: Optional[Mutant] = None) -> str:
    """The answer text with the design replaced by `mutant` (None: the original
    design, written the same way, so only the mutation differs)."""
    from rocket_reward.parse import CLOSE_TAG, OPEN_TAG
    if mutant is None:
        mutant = case.design
    if isinstance(mutant, RawDesign):
        return case.prefix + OPEN_TAG + mutant.text + ((CLOSE_TAG + case.suffix) if mutant.closed else "")
    return case.prefix + OPEN_TAG + json.dumps(mutant) + CLOSE_TAG + case.suffix


def apply_operator(op: Operator, design: dict, table: Any, requirements: Any = None) -> Optional[Mutant]:
    """Run one operator on an independent copy of `design` (the input never
    changes). `requirements` (the design's requirements record) is passed to
    the operators that use it; without it they do not apply."""
    if op.uses_requirements:
        return op.apply(copy_tree(design), table, requirements) if isinstance(requirements, dict) else None
    return op.apply(copy_tree(design), table)


def apply_untagged(op: Operator, design: dict, table: Any, requirements: Any = None) -> Optional[Mutant]:
    """The operator's copy without its cheat (op.untagged), on an independent copy."""
    if op.untagged is None:
        return None
    if op.uses_requirements:
        return op.untagged(copy_tree(design), table, requirements) if isinstance(requirements, dict) else None
    return op.untagged(copy_tree(design), table)


# --------------------------------------------------------------------------- judging

@dataclass
class Outcome:
    """Where one answer stopped and what it scored."""

    stage: str
    score: Optional[float]
    reasons: list[str] = field(default_factory=list)


def preflight_outcome(answer_text: str, table: Any = None) -> Optional[Outcome]:
    """Stages 1-4 only (no simulator): where the answer stops, or None when it
    passes all four (its score then needs the simulator). An unknown motor
    gets the facts-only credit here."""
    from rocket_reward.scoring import preflight, preflight_result
    res = preflight_result(preflight(answer_text, motor_table=table))
    return None if res is None else Outcome(res.stage, res.score, list(res.reasons))


def judge_outcome(expect: str, before: Outcome, after: Outcome) -> tuple[Optional[bool], str]:
    """Did the mutant do what it must? Returns (ok, words); ok is None when the
    promise cannot be judged here (a "lower" promise on an original that does
    not reach the targets stage)."""
    if after.score is None:
        return False, "the answer was quarantined (the reward hit an unexpected error)"
    if expect in STOP_STAGES:
        if before.stage in ladder.STAGE_KEYS and ladder.stage_index(before.stage) < ladder.stage_index(expect):
            return None, f"not judged: the original already stops at {before.stage}"
        ok = after.stage == expect
        return ok, f"stopped at {after.stage}" + ("" if ok else f", not at {expect}")
    if before.score is None:
        return None, "the original has no score"
    diff = after.score - before.score
    if expect in (EXPECT_LOWER, EXPECT_LOWER_IN_TARGETS):
        if before.stage != "targets":
            return None, f"not judged: the original stops at {before.stage}"
        words = f"score {before.score:.4f} -> {after.score:.4f}"
        if expect == EXPECT_LOWER_IN_TARGETS:
            if before.score < 1.0 - SCORE_EPS:
                return None, f"not judged: the original misses a target ({before.score:.4f})"
            if after.stage != "targets":
                return False, words + f", stopped at {after.stage}, not in targets"
        return diff < -SCORE_EPS, words
    if expect == EXPECT_SAME:
        return abs(diff) <= SCORE_EPS, f"score {before.score:.4f} -> {after.score:.4f}"
    if expect == EXPECT_SAME_OR_HIGHER:
        return diff >= -SCORE_EPS, f"score {before.score:.4f} -> {after.score:.4f}"
    if expect == EXPECT_HIGHER:
        return diff > SCORE_EPS, f"score {before.score:.4f} -> {after.score:.4f}"
    raise ValueError(f"unknown expectation {expect!r}")


def build_cases(designs: Sequence[DesignCase], operators: Sequence[Operator], table: Any
                ) -> list[dict[str, Any]]:
    """Every (design, operator) pair whose operator applies, with the answer text to score."""
    cases = []
    for d in designs:
        for op in operators:
            m = apply_operator(op, d.design, table, d.requirements)
            if m is None:
                continue
            case = {"design": d.id, "operator": op.name, "expect": op.expect, "answer": mutant_answer(d, m)}
            if op.untagged is not None:
                plain = apply_untagged(op, d.design, table, d.requirements)
                if plain is None:
                    continue
                case["untagged_answer"] = mutant_answer(d, plain)
            cases.append(case)
    return cases


def score_cases(designs: Sequence[DesignCase], cases: list[dict[str, Any]], simulator: Any = None,
                table: Any = None, preflight_only: bool = False) -> dict[str, Outcome]:
    """Score the originals and every case. Keys: design id for an original,
    "<design id>|<operator>" for a case, and that plus UNTAGGED_SUFFIX for a
    case's copy without its cheat. With preflight_only, an answer that
    passes stages 1-4 gets stage "passed 1-4" and no score."""
    from rocket_reward.records import Requirements
    from rocket_reward.scoring import ErrorTracker, score_many
    reqs = {d.id: Requirements.from_dict(d.requirements) for d in designs}
    plain = [c for c in cases if "untagged_answer" in c]
    keys = ([d.id for d in designs] + [f"{c['design']}|{c['operator']}" for c in cases]
            + [f"{c['design']}|{c['operator']}{UNTAGGED_SUFFIX}" for c in plain])
    texts = [mutant_answer(d) for d in designs] + [c["answer"] for c in cases] + [c["untagged_answer"] for c in plain]
    req_list = ([reqs[d.id] for d in designs] + [reqs[c["design"]] for c in cases]
                + [reqs[c["design"]] for c in plain])
    out: dict[str, Outcome] = {}
    if preflight_only:
        for k, t in zip(keys, texts):
            got = preflight_outcome(t, table)
            out[k] = got if got is not None else Outcome("passed 1-4", None)
        return out
    results = score_many(texts, req_list, simulator=simulator, motor_table=table,
                         tracker=ErrorTracker(window=10**6, run=10**6))
    for k, r in zip(keys, results):
        out[k] = Outcome(r.stage, r.score, list(r.reasons))
    return out


def summarize_mutations(designs: Sequence[DesignCase], cases: list[dict[str, Any]],
                        outcomes: dict[str, Outcome], operators: Sequence[Operator]) -> dict[str, Any]:
    """Per operator: designs applied to, stages reached, mean scores before and
    after, and every case that did not do what it must."""
    per_op: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    for op in operators:
        per_op[op.name] = {"operator": op.name, "expect": op.expect, "what": op.what, "applied": 0,
                           "stages": collections.Counter(), "before": [], "after": [], "failed": 0,
                           "not_judged": 0}
    for c in cases:
        before, after = outcomes[c["design"]], outcomes[f"{c['design']}|{c['operator']}"]
        if after.score is None and after.stage == "passed 1-4":
            ok = False if c["expect"] in PREFLIGHT_STAGES else None
            words = "passed stages 1-4" + ("" if ok is False else " (judging it needs the simulator)")
        else:
            plain = outcomes.get(f"{c['design']}|{c['operator']}{UNTAGGED_SUFFIX}") if "untagged_answer" in c else None
            ok, words = judge_outcome(c["expect"], plain if plain and c["expect"] == EXPECT_SAME else before, after)
            if plain is not None and after.score is not None:
                same = (after.stage == plain.stage and plain.score is not None
                        and abs(after.score - plain.score) <= SCORE_EPS)
                words += f"; without the tags {plain.stage} {_mu_fmt(plain.score)}"
                if not same:
                    ok = False
        s = per_op[c["operator"]]
        s["applied"] += 1
        s["stages"][after.stage] += 1
        if before.score is not None:
            s["before"].append(before.score)
        if after.score is not None:
            s["after"].append(after.score)
        row = {"design": c["design"], "operator": c["operator"], "expect": c["expect"],
               "before_stage": before.stage, "before_score": before.score,
               "stage": after.stage, "score": after.score, "ok": ok, "words": words,
               "reasons": after.reasons[:3]}
        rows.append(row)
        if ok is False:
            s["failed"] += 1
            failures.append(row)
        elif ok is None:
            s["not_judged"] += 1
    table_rows = []
    for s in per_op.values():
        table_rows.append({**s, "stages": dict(s["stages"]),
                           "before": round(statistics.fmean(s["before"]), 4) if s["before"] else None,
                           "after": round(statistics.fmean(s["after"]), 4) if s["after"] else None})
    originals = {d.id: {"rows": d.rows, "stage": outcomes[d.id].stage, "score": outcomes[d.id].score}
                 for d in designs}
    return {"designs": len(designs), "cases": len(cases), "originals": originals, "operators": table_rows,
            "failures": failures, "rows": rows}


def _mu_fmt(x: Any) -> str:
    return "-" if x is None else (f"{x:.4f}" if isinstance(x, float) else str(x))


def mutation_report_md(summary: dict[str, Any], timing: dict[str, Any], title: str) -> str:
    """The report as Markdown."""
    lines = [f"# {title}", "",
             f"{summary['designs']} distinct designs, {summary['cases']} mutants, "
             f"{len(summary['failures'])} cases that did not do what they must. "
             f"Scoring took {timing.get('score_s', '-')} s ({timing.get('s_per_answer', '-')} s per answer).", "",
             "## Originals", "", "| design | rows | stage | score |", "|---|---|---|---|"]
    for did, o in summary["originals"].items():
        lines.append(f"| {did} | {len(o['rows'])} | {o['stage']} | {_mu_fmt(o['score'])} |")
    lines += ["", "## Operators", "",
              "| operator | must | applied to | stopped at | mean score before | after | not done | not judged |",
              "|---|---|---|---|---|---|---|---|"]
    for s in summary["operators"]:
        where = ", ".join(f"{k} {v}" for k, v in sorted(s["stages"].items())) or "-"
        lines.append(f"| {s['operator']} | {s['expect']} | {s['applied']} | {where} | {_mu_fmt(s['before'])} | "
                     f"{_mu_fmt(s['after'])} | {s['failed']} | {s['not_judged']} |")
    lines += ["", "## Cases that did not do what they must", ""]
    if not summary["failures"]:
        lines.append("None.")
    for f in summary["failures"]:
        lines.append(f"- **{f['operator']}** on {f['design']} (must: {f['expect']}): original {f['before_stage']} "
                     f"{_mu_fmt(f['before_score'])}, mutant {f['stage']} {_mu_fmt(f['score'])}; {f['words']}")
        for r in f["reasons"]:
            lines.append(f"    - {r[:300]}")
    lines += ["", "## What each operator does", ""]
    for s in summary["operators"]:
        lines.append(f"- `{s['operator']}` ({s['expect']}): {s['what']}")
    return "\n".join(lines) + "\n"


def expected_snapshot(summary: dict[str, Any]) -> dict[str, Any]:
    """For tests: the designs and operators that ran, and the stage and score
    (4 places) of every original and every "<design id>|<operator>" case."""
    out: dict[str, Any] = {"designs": list(summary["originals"]),
                           "operators": [s["operator"] for s in summary["operators"]],
                           "originals": {d: {"stage": o["stage"], "score": None if o["score"] is None
                                             else round(o["score"], 4)}
                                         for d, o in summary["originals"].items()},
                           "cases": {}}
    for r in summary["rows"]:
        out["cases"][f"{r['design']}|{r['operator']}"] = {
            "stage": r["stage"], "score": None if r["score"] is None else round(r["score"], 4)}
    return out


# --------------------------------------------------------------------------- command

def _mu_names(text: Optional[str]) -> Optional[set[str]]:
    return {t.strip() for t in text.split(",") if t.strip()} if text else None


def mutation_plan(answers: Path, requirements: Path, operators: Sequence[Operator], table: Any,
                  repair_answers: Optional[Path] = None, wanted: Optional[set[str]] = None
                  ) -> tuple[list[DesignCase], list[dict[str, Any]], list[str]]:
    """The designs and cases the command scores: every non-repair operator on
    the distinct reference designs, and the repairs on the model answers they
    apply to (their ids start with MODEL_PREFIX, because model answers often
    share their ids with the references). `wanted` keeps only those design ids.
    Returns (designs, cases, ids of rows whose design could not be read)."""
    from rocket_reward.tools.calibrate import answer_rows
    refs, unread = collect_designs(answer_rows(answers, requirements))
    refs = [d for d in refs if wanted is None or d.id in wanted]
    designs = list(refs)
    cases = build_cases(refs, [o for o in operators if not o.repair], table)
    if repair_answers is not None:
        rep, more = collect_designs(answer_rows(repair_answers, requirements))
        unread += more
        for d in rep:
            d.id = MODEL_PREFIX + d.id
        rep = [d for d in rep if wanted is None or d.id in wanted]
        rep_cases = build_cases(rep, [o for o in operators if o.repair], table)
        used = {c["design"] for c in rep_cases}
        designs += [d for d in rep if d.id in used]
        cases += rep_cases
    return designs, cases, unread


def main(argv: Optional[Sequence[str]] = None) -> int:
    from rocket_reward.cli import use_utf8_output
    from rocket_reward.scoring import default_motor_table

    use_utf8_output()
    ap = argparse.ArgumentParser(prog="python -m rocket_reward.tools.mutate",
                                 description="Score every mutation operator on every design and report "
                                             "the cases that did not do what they must.")
    ap.add_argument("--answers", required=True, help="reference answers (.jsonl or .jsonl.gz)")
    ap.add_argument("--requirements", required=True, help="JSON file {answer id: requirements record}")
    ap.add_argument("--out", required=True, help="Markdown report to write")
    ap.add_argument("--json", help="also write every case as JSON here")
    ap.add_argument("--repair-answers", help="model answers the repairs run on (same requirements file)")
    ap.add_argument("--designs", help="only these design ids (comma-separated first-row ids)")
    ap.add_argument("--operators", help="only these operators (comma-separated names)")
    ap.add_argument("--workers", type=int, default=4, help="simulator helpers (default 4)")
    ap.add_argument("--preflight-only", action="store_true",
                    help="no simulator: run only operators judged at stages 1-4")
    ap.add_argument("--write-expected", help="write the stage and score of every case here (for tests)")
    args = ap.parse_args(argv)

    wanted_ops = _mu_names(args.operators)
    unknown = sorted((wanted_ops or set()) - {o.name for o in OPERATORS})
    if unknown:
        ap.error(f"unknown operators: {', '.join(unknown)}")
    ops = [o for o in OPERATORS if wanted_ops is None or o.name in wanted_ops]
    if args.preflight_only:
        ops = [o for o in ops if not o.needs_simulator]

    table = default_motor_table()
    designs, cases, unread = mutation_plan(Path(args.answers), Path(args.requirements), ops, table,
                                           Path(args.repair_answers) if args.repair_answers else None,
                                           _mu_names(args.designs))
    missing = [d.id for d in designs if not isinstance(d.requirements, dict)]
    if missing:
        print(f"no requirements for {', '.join(missing[:5])}: add them to {args.requirements}", file=sys.stderr)
        return 2

    t0 = time.perf_counter()
    if args.preflight_only:
        outcomes = score_cases(designs, cases, table=table, preflight_only=True)
    else:
        from rocket_reward.sim import SimPool
        with SimPool(args.workers) as pool:
            t0 = time.perf_counter()
            outcomes = score_cases(designs, cases, simulator=pool, table=table)
    dt = time.perf_counter() - t0
    summary = summarize_mutations(designs, cases, outcomes, ops)
    summary["unread_rows"] = unread
    timing = {"score_s": round(dt, 1), "s_per_answer": round(dt / max(1, len(cases) + len(designs)), 3)}
    title = "Mutation report" + (" (stages 1-4 only)" if args.preflight_only else "")
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(mutation_report_md(summary, timing, title))
    if args.json:
        with open(args.json, "w", encoding="utf-8", newline="\n") as fh:
            json.dump({**summary, "timing": timing}, fh, ensure_ascii=False, indent=1, default=str)
    if args.write_expected:
        with open(args.write_expected, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(expected_snapshot(summary), fh, ensure_ascii=False, indent=1)
            fh.write("\n")
    print(f"{len(designs)} designs, {len(cases)} mutants, {len(summary['failures'])} not as they must; "
          f"report: {args.out}")
    for f in summary["failures"]:
        print(f"  {f['operator']} on {f['design']}: must {f['expect']}, got {f['stage']} {_mu_fmt(f['score'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
