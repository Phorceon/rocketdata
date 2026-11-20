"""Stage 2: all the parts a flyable rocket needs are there.

Eight things are looked for (DESIGN.md, stage 2). The credit is the share
found. Parts count only where OpenRocket would see them: a stage must sit
directly inside the rocket's "subcomponents", and every other part must sit
inside a stage, reached through "subcomponents" nodes, in a parent that
OpenRocket lets hold it (tree.LEGAL_CHILDREN: a fin set on a tube, nose cone
or transition, never inside a parachute; only nose cones, body tubes and
transitions directly in a stage). OpenRocket drops a part placed anywhere
else when it loads the file. A motor mount is a body tube or inner tube that
holds a "motormount" node; the motor is a "motor" node inside that "motormount".
"""
from __future__ import annotations

from typing import Any

from .limits import FIN_COUNT_MIN
from .motors import MOUNT_TAGS, flown_config_id, mount_motors
from .records import StageCheck
from .tree import (Node, attr_of, body_of, child, iter_components, last_child, number, rocket_of, stages_of,
                   tag_of)

ITEMS = ("stage", "nose_cone", "body_tube", "fin_set", "motor_mount", "motor",
         "motor_configuration", "recovery")

# Every fin set OpenRocket has. DESIGN.md names trapezoid, elliptical and
# freeform; tube fins are fins too, and 3 of the 582 reference rockets have
# only tube fins, so they count as well.
FIN_SET_TAGS = ("trapezoidfinset", "ellipticalfinset", "freeformfinset", "tubefinset")
RECOVERY_TAGS = ("parachute", "streamer")

_WHAT = {
    "stage": "a stage directly inside the rocket's subcomponents",
    "nose_cone": "a nose cone inside a stage",
    "body_tube": "a body tube inside a stage",
    "fin_set": "a fin set (trapezoid, elliptical, freeform or tube fins) with at least one fin",
    "motor_mount": "a motor mount (a body tube or inner tube holding a 'motormount' node)",
    "motor": "a motor inside a motor mount",
    "motor_configuration": ("a motor configuration: the rocket declares a configid and a mounted motor "
                            "uses the flown one (without this OpenRocket flies the rocket with no motor)"),
    "recovery": "a recovery device (parachute or streamer) inside a stage",
}


def fin_count(finset: Node) -> Any:
    """How many fins a fin set says it has.

    Reads "fincount", else "instancecount" (newer OpenRocket files write that
    instead; 33 of the 582 reference fin sets do). When a tag is written twice
    the LAST copy counts, as OpenRocket's loader and the cleaned copy keep
    it (tree.last_child). Returns the number as a
    float, the raw value when it is not a usable number (which may itself be
    None), or None when neither tag is written, in which case OpenRocket uses
    its default of 3 fins.
    """
    for tag in ("fincount", "instancecount"):
        c = last_child(finset, tag)
        if c is not None:
            raw = body_of(c).get("value")
            n = number(raw)
            return n if n is not None else raw
    return None


def has_fins(finset: Node) -> bool:
    """True when the fin set has at least one fin (no count written means 3)."""
    if all(child(finset, tag) is None for tag in ("fincount", "instancecount")):
        return True
    n = fin_count(finset)
    return isinstance(n, float) and n >= FIN_COUNT_MIN


def check_parts(root: Node) -> StageCheck:
    """Stage 2: look for the eight needed parts.

    info["found"] maps each item name in ITEMS to True or False. A failing
    design's credit is found / 8, and the reasons name every missing item.
    """
    found = {k: False for k in ITEMS}
    rocket = rocket_of(root)
    finsets_without_fins = 0
    stages = stages_of(root)
    found["stage"] = bool(stages)
    misplaced: list = []
    for stage in stages:
        for comp in iter_components(stage, legal_only=True, skipped=misplaced):
            tag = tag_of(comp)
            if tag == "nosecone":
                found["nose_cone"] = True
            elif tag == "bodytube":
                found["body_tube"] = True
            elif tag in RECOVERY_TAGS:
                found["recovery"] = True
            elif tag in FIN_SET_TAGS:
                if has_fins(comp):
                    found["fin_set"] = True
                else:
                    finsets_without_fins += 1
            if tag in MOUNT_TAGS and child(comp, "motormount") is not None:
                found["motor_mount"] = True
    mounted = [m for _, m in mount_motors(root, legal_only=True)]
    found["motor"] = bool(mounted)
    cid = flown_config_id(root)
    found["motor_configuration"] = cid is not None and any(attr_of(m, "configid") == cid for m in mounted)

    n_found = sum(found.values())
    if n_found == len(ITEMS):
        return StageCheck("parts", passed=True, credit=1.0, info={"found": found})

    reasons = [f"{len(ITEMS) - n_found} of {len(ITEMS)} needed parts are missing"]
    if rocket is None:
        reasons.append("the design has no 'rocket' node under 'openrocket', so no part can be found")
    if misplaced:
        shown = ", ".join(f"a {c[:40]} inside a {p[:40]}" for p, c in list(dict.fromkeys(misplaced))[:3])
        where = ("; a stage holds only nose cones, body tubes and transitions, so put fins, lugs, rings, "
                 "mass components and recovery parts in the subcomponents of a body tube"
                 if all(p in ("stage", "podset", "parallelstage") for p, _ in misplaced) else
                 "; fins, lugs and rail buttons go on a nose cone, body tube or transition, and inner tubes, "
                 "couplers, rings, mass components and recovery parts inside one of those or an inner tube")
        reasons.append(f"{len(misplaced)} part(s) sit where OpenRocket does not accept them and are "
                       f"dropped when it loads the file ({shown}){where}")
    for k in ITEMS:
        if found[k]:
            continue
        text = f"missing {_WHAT[k]}"
        if k == "fin_set" and finsets_without_fins:
            text += f" ({finsets_without_fins} fin set(s) found, but each has a fin count below 1)"
        if k == "stage" and rocket is not None and child(rocket, "stage") is not None:
            text += " (a stage sits directly under 'rocket'; it belongs inside the rocket's 'subcomponents')"
        if k == "motor_configuration" and mounted:
            used = sorted({str(attr_of(m, 'configid'))[:40] for m in mounted})
            text += (f" (the flown configuration is {cid!r} but the motors use {', '.join(used)})"
                     if cid is not None else " (the rocket declares no 'motorconfiguration' with a configid)")
        reasons.append(text)
    return StageCheck("parts", passed=False, credit=n_found / len(ITEMS), reasons=reasons,
                      info={"found": found})
