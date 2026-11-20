"""The score ladder.

Every number that shapes the score lives in this file: the order of the
stages, the band of scores each stage owns, and the formulas that turn "how
badly was a rule broken" into a credit between 0 and 1. See DESIGN.md.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Optional


@dataclass(frozen=True)
class Stage:
    """One rung of the ladder."""

    key: str      # short name used in results and logs
    floor: float  # score of the worst design that stops at this stage
    width: float  # floor + width is the score of the best design that stops here
    title: str    # what passing this stage means, in plain words

    @property
    def top(self) -> float:
        return self.floor + self.width


# The gap between one stage's top and the next stage's floor is what makes
# "getting further always scores higher" true. test_ladder.py checks it.
STAGES: tuple[Stage, ...] = (
    Stage("format", 0.00, 0.08, "the answer holds a readable design tree"),
    Stage("parts", 0.10, 0.08, "all the needed parts are there"),
    Stage("motor", 0.20, 0.08, "every motor is a real one"),
    Stage("limits", 0.30, 0.08, "sizes, counts and materials are physically sensible"),
    Stage("build", 0.40, 0.08, "OpenRocket can build it and the parts fit together"),
    Stage("flight", 0.50, 0.18, "it flies safely in every wind"),
    Stage("targets", 0.70, 0.30, "it does what the prompt asked"),
)
STAGE_KEYS: tuple[str, ...] = tuple(s.key for s in STAGES)
_BY_KEY = {s.key: s for s in STAGES}

# Stage 1 (format) credits, one per way an answer can be unreadable.
FORMAT_CREDIT_NO_BLOCK = 0.0   # cut off, or no complete <design>...</design> block
FORMAT_CREDIT_BAD_JSON = 0.5   # a block is there but its JSON does not parse
FORMAT_CREDIT_BAD_TREE = 0.75  # JSON parses but is not a design tree (shape, root, depth, size)

# Stage 1 caps on the design tree. The reference rockets nest at most 13 levels
# deep and their JSON is at most about 45 kB, so both caps leave a wide margin
# for honest designs while keeping hostile input cheap to reject.
FORMAT_MAX_DEPTH = 64              # node levels, counting the "openrocket" root as level 1
FORMAT_MAX_JSON_BYTES = 300_000    # UTF-8 bytes of the JSON text between the tags
# Above this size the JSON is not even read: it scores like text that does not
# parse (FORMAT_CREDIT_BAD_JSON). This keeps a huge answer from costing time,
# and it can never beat a readable tree that is merely too large.
FORMAT_READ_CEILING_BYTES = 10 * FORMAT_MAX_JSON_BYTES

# Violation sizes (see "How credit is computed" in DESIGN.md).
MAX_VIOLATION = 3.0     # eight times past a limit, or a missing value
YES_NO_VIOLATION = 1.0  # a broken yes/no rule costs the same as twice the limit

# Defects: small problems that do not stop the ladder.
DEFECT_COST = 0.05      # share of the credit each defect removes
MAX_DEFECT_COST = 0.50  # defects never remove more than half the credit

# Unknown material names (stage 4): each distinct unknown name is a yes/no
# violation, but at most this many count, so a design that names ten made-up
# materials is not pushed far below one with three (it is equally unflyable).
MATERIAL_NAMES_COUNTED_MAX = 3

# Fit problems (stage 5): a violation smaller than this (the value is under
# about 1.41 times its limit) is a defect, not a failure.
FIT_DEFECT_BELOW = 0.5

# An aborted flight, or a section that never lands, costs this much on top of
# whatever else is wrong with the flight.
NO_FLIGHT_VIOLATION = MAX_VIOLATION

# Stability rules whose limit is 0 cal (stage 6) cannot use the log formula. Their
# violation is (limit - value) in calibres plus this step, so a rocket exactly at
# the limit (neutrally stable) fails; -0.4 cal, the worst sound-looking reference
# miss, then costs 0.5, and anything 2.9 cal or more below the limit costs the most.
STABILITY_ZERO_STEP = 0.1

# Unknown motors (stage 3) when a simulator is available: half the credit comes
# from the three facts about the motor as written, half from how far the same
# design gets when flown with the nearest real motor ("shadow flight").
MOTOR_FACTS_SHARE = 0.5
MOTOR_SHADOW_SHARE = 0.5

# Targets (stage 7).
# A landing slower than this earns less: a needlessly large parachute drifts far.
LANDING_COMFORT_MIN_MS = 3.5       # full credit from here up to the limit ...
LANDING_COMFORT_FRACTION = 0.6     # ... or from this share of the limit, whichever is lower
TARGET_FALLOFF = 0.25   # how fast credit falls once a target is missed
DEFAULT_ABOUT_TOL = 0.05
APOGEE_WEIGHT = 3.0
OTHER_TARGET_WEIGHT = 1.0


def stage(key: str) -> Stage:
    """Return the stage called `key`. An unknown name is a programming error."""
    return _BY_KEY[key]


def stage_index(key: str) -> int:
    """Position of a stage on the ladder, starting at 0 for "format"."""
    return STAGE_KEYS.index(key)


def is_number(x: object) -> bool:
    """True for a real, finite int or float (bool does not count)."""
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return False
    try:
        return math.isfinite(x)
    except OverflowError:  # an integer too large to be a float, e.g. 10**400
        return False


def clamp01(x: object) -> float:
    """Clamp to 0..1. Anything that is not a finite number becomes 0."""
    if not is_number(x):
        return 0.0
    return min(1.0, max(0.0, float(x)))  # type: ignore[arg-type]


def stage_score(key: str, credit: float, defects: int = 0) -> float:
    """Score of a design that stopped at stage `key` with this credit.

    `defects` is the number of small problems found along the way. The result
    always lies inside the stage's band.
    """
    s = stage(key)
    # A defect count that is not a finite number is a caller's mistake; charge the
    # full defect cost rather than guess.
    cost = min(MAX_DEFECT_COST, DEFECT_COST * max(0, int(defects))) if is_number(defects) else MAX_DEFECT_COST
    return round(s.floor + s.width * clamp01(credit) * (1.0 - cost), 6)


def over_limit(value: Optional[float], limit: float) -> float:
    """Size of the violation of a "no more than `limit`" rule (0 when it holds)."""
    if not is_number(value):
        return MAX_VIOLATION
    if value <= limit:  # type: ignore[operator]
        return 0.0
    if limit <= 0:
        return MAX_VIOLATION
    return min(MAX_VIOLATION, math.log2(value / limit))  # type: ignore[operator]


def under_limit(value: Optional[float], limit: float) -> float:
    """Size of the violation of a "no less than `limit`" rule (0 when it holds)."""
    if not is_number(value):
        return MAX_VIOLATION
    if value >= limit:  # type: ignore[operator]
        return 0.0
    if value <= 0:  # type: ignore[operator]
        return MAX_VIOLATION
    return min(MAX_VIOLATION, math.log2(limit / value))  # type: ignore[operator]


def credit_from_violations(violations: Iterable[float]) -> float:
    """Turn a list of violation sizes into a credit: 1 / (1 + their sum).

    No violations gives 1. Each size is clamped to 0..MAX_VIOLATION first, and
    anything that is not a number counts as MAX_VIOLATION.
    """
    total = 0.0
    for v in violations:
        total += min(MAX_VIOLATION, max(0.0, float(v))) if is_number(v) else MAX_VIOLATION
    return 1.0 / (1.0 + total)


def closeness(value: Optional[float], target: float, kind: str = "about",
              tol: Optional[float] = None) -> float:
    """Credit (0..1] for how well `value` meets a target. Never reaches 0 for a
    positive value, so being closer always scores higher.

    kind "about": full credit within +-tol of the target.
    kind "max":   full credit at or below target * (1 + tol).
    kind "min":   full credit at or above target / (1 + tol).
    A missing, non-positive or non-finite value gets 0.
    """
    if not is_number(value) or value <= 0 or not is_number(target) or target <= 0:  # type: ignore[operator]
        return 0.0
    if tol is None:
        tol = DEFAULT_ABOUT_TOL if kind == "about" else 0.0
    slack = math.log1p(max(0.0, tol))
    ratio = math.log(value / target)  # type: ignore[operator]
    if kind == "about":
        miss = abs(ratio) - slack
    elif kind == "max":
        miss = ratio - slack
    elif kind == "min":
        miss = -ratio - slack
    else:
        raise ValueError(f"unknown target kind {kind!r}")
    return 1.0 / (1.0 + max(0.0, miss) / TARGET_FALLOFF)
