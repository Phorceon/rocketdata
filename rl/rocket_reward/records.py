"""Plain data records passed between the parts of the reward.

Target and Requirements describe what a prompt asked for. StageCheck is what
one stage reports. Result is what `score()` returns. See DESIGN.md.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from typing import Any, Optional

from .ladder import is_number
from .limits import DEFAULT_WIND_MS

TARGET_KINDS = ("about", "max", "min")

# Requirement fields that hold a Target, with the unit each one uses.
TARGET_FIELDS = (
    "apogee_m",          # highest point of the flight, metres
    "landing_ms",        # vertical speed at touchdown, metres per second
    "flight_time_s",     # launch to touchdown, seconds
    "time_to_apogee_s",  # launch to highest point, seconds
    "max_velocity_ms",   # top speed, metres per second
    "max_accel_ms2",     # top acceleration, metres per second squared
    "body_diameter_m",   # widest body tube, metres
    "mass_kg",           # mass on the pad with motors, kilograms
)


@dataclass(frozen=True)
class Target:
    """One number the prompt asked for.

    kind "about": the design should be close to `value` (within `tol`).
    kind "max":   the design should be at or below `value`.
    kind "min":   the design should be at or above `value`.
    `tol` is a fraction (0.05 means 5%). When it is None the reward uses 5%
    for "about" and no slack for "max" and "min".
    """

    value: float
    kind: str
    tol: Optional[float] = None

    def __post_init__(self) -> None:
        if not is_number(self.value) or self.value <= 0:
            raise ValueError(f"a target value must be a positive number, got {self.value!r}")
        if self.kind not in TARGET_KINDS:
            raise ValueError(f"a target kind must be one of {TARGET_KINDS}, got {self.kind!r}")
        if self.tol is not None and (not is_number(self.tol) or not 0 <= self.tol < 1):
            raise ValueError(f"a target tolerance must be a fraction from 0 to 1, got {self.tol!r}")

    @classmethod
    def from_dict(cls, d: Any, name: str = "target") -> "Target":
        if not isinstance(d, dict):
            raise ValueError(f"{name} must look like {{'value': 900, 'kind': 'about'}}, got {d!r}")
        unknown = set(d) - {"value", "kind", "tol"}
        if unknown:
            raise ValueError(f"{name} has unknown keys {sorted(unknown)}")
        if "value" not in d or "kind" not in d:
            raise ValueError(f"{name} needs both 'value' and 'kind', got {d!r}")
        try:
            return cls(value=d["value"], kind=d["kind"], tol=d.get("tol"))
        except ValueError as exc:
            raise ValueError(f"{name}: {exc}") from None


@dataclass(frozen=True)
class Requirements:
    """What one prompt asked for. Built together with the prompt text.

    Only `id` and `apogee_m` are required. A target that is None is not graded.
    """

    id: str
    apogee_m: Target
    landing_ms: Optional[Target] = None
    flight_time_s: Optional[Target] = None
    time_to_apogee_s: Optional[Target] = None
    max_velocity_ms: Optional[Target] = None
    max_accel_ms2: Optional[Target] = None
    body_diameter_m: Optional[Target] = None
    mass_kg: Optional[Target] = None
    motors: tuple[str, ...] = ()        # motor designations the prompt names, e.g. ("H128W",)
    motor_class: Optional[str] = None   # impulse class letter the prompt names, e.g. "H"
    wind_ms: float = DEFAULT_WIND_MS    # wind speed the prompt states, metres per second

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id:
            raise ValueError("requirements need a non-empty text 'id'")
        if not isinstance(self.apogee_m, Target):
            raise ValueError(f"requirements {self.id!r}: 'apogee_m' is required")
        if not is_number(self.wind_ms) or self.wind_ms < 0:
            raise ValueError(f"requirements {self.id!r}: 'wind_ms' must be zero or more, got {self.wind_ms!r}")
        if self.motor_class is not None and not (
                isinstance(self.motor_class, str) and len(self.motor_class) == 1
                and self.motor_class.isalpha() and self.motor_class.isupper()):
            raise ValueError(f"requirements {self.id!r}: 'motor_class' must be one capital letter, "
                             f"got {self.motor_class!r}")
        if not all(isinstance(m, str) and m for m in self.motors):
            raise ValueError(f"requirements {self.id!r}: 'motors' must be a list of designations")

    @classmethod
    def from_dict(cls, d: Any) -> "Requirements":
        """Build from a plain dict (one JSON record). Unknown keys are an error,
        so a typo cannot silently drop a target."""
        if not isinstance(d, dict):
            raise ValueError(f"requirements must be a dict, got {type(d).__name__}")
        rid = d.get("id")
        known = {f.name for f in fields(cls)}
        unknown = set(d) - known
        if unknown:
            raise ValueError(f"requirements {rid!r}: unknown keys {sorted(unknown)}; "
                             f"allowed keys are {sorted(known)}")
        if "apogee_m" not in d or d["apogee_m"] is None:
            raise ValueError(f"requirements {rid!r}: 'apogee_m' is required")
        kwargs: dict[str, Any] = {"id": rid}
        for name in TARGET_FIELDS:
            if d.get(name) is not None:
                kwargs[name] = Target.from_dict(d[name], f"requirements {rid!r}: {name}")
        if d.get("motors") is not None:
            if isinstance(d["motors"], str) or not isinstance(d["motors"], (list, tuple)):
                raise ValueError(f"requirements {rid!r}: 'motors' must be a list")
            kwargs["motors"] = tuple(d["motors"])
        if d.get("motor_class") is not None:
            kwargs["motor_class"] = d["motor_class"]
        if d.get("wind_ms") is not None:
            kwargs["wind_ms"] = d["wind_ms"]
        return cls(**kwargs)

    def to_dict(self) -> dict[str, Any]:
        """The same record as a plain dict, leaving out everything not stated."""
        out: dict[str, Any] = {"id": self.id}
        for name in TARGET_FIELDS:
            t = getattr(self, name)
            if t is not None:
                out[name] = {k: v for k, v in asdict(t).items() if v is not None}
        if self.motors:
            out["motors"] = list(self.motors)
        if self.motor_class:
            out["motor_class"] = self.motor_class
        out["wind_ms"] = self.wind_ms
        return out

    def targets(self) -> dict[str, Target]:
        """Every stated target, by field name."""
        return {n: getattr(self, n) for n in TARGET_FIELDS if getattr(self, n) is not None}


@dataclass
class StageCheck:
    """What one stage reports about one design."""

    stage: str                     # stage key from ladder.STAGE_KEYS
    passed: bool
    credit: float = 0.0            # 0..1: how close a failing design came (targets: how well they were met)
    reasons: list[str] = field(default_factory=list)   # why it failed, in plain words
    defects: list[str] = field(default_factory=list)   # small problems that do not stop the ladder
    info: dict[str, Any] = field(default_factory=dict)  # numbers worth logging


@dataclass
class Result:
    """What `score()` returns for one answer."""

    score: Optional[float]         # 0..1, or None when the answer must be left out of training
    stage: str                     # stage where scoring stopped ("targets" when every gate passed)
    stages_passed: int             # how many stages were passed, 0..7
    credit: float                  # the credit used at that stage
    reasons: list[str] = field(default_factory=list)
    defects: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)   # flight numbers, when flown
    flags: dict[str, Any] = field(default_factory=dict)     # truncated, sim_timeout, quarantined, ...

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
