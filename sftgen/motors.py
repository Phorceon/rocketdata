"""Motor resolution against OpenRocket's bundled motor database.

`resolve(designation, manufacturer)` always returns the same thrust curve for the
same inputs: delay suffixes are stripped ("C6-5" -> "C6"), names are compared
case- and punctuation-insensitively, and ties are broken by manufacturer
preference, availability, curve resolution and digest.
"""

from __future__ import annotations

import re
from functools import lru_cache

# Preferred manufacturer order when the caller doesn't name one.
MANUFACTURER_PREFERENCE = (
    "Estes", "AeroTech", "Cesaroni Technology", "Quest", "Apogee", "Loki Research",
    "Animal Motor Works", "Kosdon by AeroTech", "Public Missiles, Ltd.",
)
MANUFACTURER_ALIASES = {
    "aerotech": "AeroTech", "at": "AeroTech", "estes": "Estes", "cesaroni": "Cesaroni Technology",
    "cti": "Cesaroni Technology", "quest": "Quest", "quest aerospace": "Quest", "apogee": "Apogee",
    "apogee components": "Apogee", "loki": "Loki Research",
    "amw": "Animal Motor Works", "animal motor works": "Animal Motor Works",
}
TYPE_NAME = {"Single-use": "single-use", "Reloadable": "reloadable", "Hybrid": "hybrid", "Unknown": "unknown"}
OR_TYPE = {"Single-use": "single", "Reloadable": "reload", "Hybrid": "hybrid", "Unknown": "unknown"}


class UnknownMotor(LookupError):
    def __init__(self, designation: str, suggestions: list[str]):
        super().__init__(f"unknown motor {designation!r}")
        self.designation = designation
        self.suggestions = suggestions


def _norm(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def split_delay(designation: str) -> tuple[str, float | None]:
    """'C6-5' -> ('C6', 5.0); 'H128W-14A' -> ('H128W', 14.0); 'C6-0' -> ('C6', 0.0); 'I300T' -> ('I300T', None)."""
    d = designation.strip()
    m = re.match(r"^(.*?[A-Za-z][0-9]+[A-Za-z]*)-(\d+)[A-Za-z]?$", d)
    if m:
        return m.group(1), float(m.group(2))
    m = re.match(r"^(.*?[A-Za-z][0-9]+[A-Za-z]*)-P$", d, re.I)
    if m:
        return m.group(1), None
    return d, None


def motor_class(total_impulse_ns: float) -> str:
    if total_impulse_ns <= 0.3125:
        return "1/4A"
    if total_impulse_ns <= 0.625:
        return "1/2A"
    letters = "ABCDEFGHIJKLMNOPQ"
    hi = 2.5
    for L in letters:
        if total_impulse_ns <= hi + 1e-9:
            return L
        hi *= 2
    return "R+"


def _canonical_manufacturer(name: str | None) -> str | None:
    if not name:
        return None
    key = name.strip().lower()
    return MANUFACTURER_ALIASES.get(key, name.strip())


@lru_cache(maxsize=1)
def _index():
    from scripts.or_headless import _helper

    _helper()
    from jpype import JClass

    db = JClass("info.openrocket.core.startup.Application").getThrustCurveMotorSetDatabase()
    by_name: dict[str, list] = {}
    for s in db.getMotorSets():
        for m in s.getMotors():
            keys = {_norm(str(m.getDesignation())), _norm(str(m.getCommonName()))}
            for k in keys:
                if k:
                    by_name.setdefault(k, []).append(m)
    return by_name


def _pref(m) -> tuple:
    manu = str(m.getManufacturer().getDisplayName())
    try:
        rank = MANUFACTURER_PREFERENCE.index(manu)
    except ValueError:
        rank = len(MANUFACTURER_PREFERENCE)
    return (rank, 0 if m.isAvailable() else 1, -int(m.getDataSize()), str(m.getDigest()))


def _describe(m) -> dict:
    impulse = float(m.getTotalImpulseEstimate())
    delays = [float(x) for x in m.getStandardDelays()]
    delays = sorted({round(d, 1) for d in delays if d == d and d != float("inf")})
    t = str(m.getMotorType())
    return {
        "manufacturer": str(m.getManufacturer().getDisplayName()),
        "designation": str(m.getDesignation()),
        "class": motor_class(impulse),
        "total_impulse_ns": round(impulse, 1),
        "average_thrust_n": round(float(m.getAverageThrustEstimate()), 1),
        "max_thrust_n": round(float(m.getMaxThrustEstimate()), 1),
        "burn_time_s": round(float(m.getBurnTimeEstimate()), 2),
        "diameter_m": round(float(m.getDiameter()), 4),
        "length_m": round(float(m.getLength()), 4),
        "loaded_mass_kg": round(float(m.getLaunchMass()), 4),
        "propellant_mass_kg": round(float(m.getLaunchMass()) - float(m.getBurnoutMass()), 4),
        "delays_s": delays,
        "type": TYPE_NAME.get(t, t.lower()),
        # internal fields (stripped from tool output)
        "digest": str(m.getDigest()),
        "or_type": OR_TYPE.get(t, "single"),
    }


# Cesaroni Pro-series propellant codes written after the designation ("G54-RL", "I216-CL").
CTI_PROPELLANTS = {"CL", "RL", "BS", "SS", "IM", "MY", "GR", "WT", "SK", "VM", "WH", "BL", "RD", "LB", "CS", "SM", "DT"}

CORE_RE = re.compile(r"(?:^|[^A-Z]|(?<=\d))([A-O])(\d+)([A-Z]*)")


def core_name(designation: str) -> tuple[str, str] | None:
    """'2014K1200-16A' -> ('K1200', ''); 'J350W-L' -> ('J350', 'W'); 'H128W' -> ('H128', 'W')."""
    m = CORE_RE.search(designation.upper().replace(" ", ""))
    if not m:
        return None
    return m.group(1) + m.group(2), m.group(3)


def _candidates(designation: str) -> list:
    idx = _index()
    base, _ = split_delay(designation)
    if _norm(base) in idx:
        return list(idx[_norm(base)])
    full = _norm(designation)
    if full in idx:
        return list(idx[full])
    core = core_name(designation)
    if not core:
        return []
    common, prop = core
    cands = list(idx.get(common, []))
    if prop:
        same = [m for m in cands if core_name(str(m.getDesignation())) == (common, prop)]
        cands = same or cands
    tokens = [t for t in re.split(r"[^A-Z]+", designation.upper()) if len(t) >= 2]
    if any(t in CTI_PROPELLANTS for t in tokens):
        cti = [m for m in cands if "Cesaroni" in str(m.getManufacturer().getDisplayName())]
        if cti:
            return cti
    if tokens:
        tok = [m for m in cands if any(t in str(m.getDesignation()).upper() for t in tokens)]
        cands = tok or cands
    return cands


@lru_cache(maxsize=4096)
def resolve(designation: str, manufacturer: str | None = None) -> dict:
    base, _ = split_delay(designation)
    cands = _candidates(designation)
    if not cands:
        raise UnknownMotor(designation, suggest(base))
    manu = _canonical_manufacturer(manufacturer)
    if manu:
        sel = [m for m in cands if _norm(str(m.getManufacturer().getDisplayName())).startswith(_norm(manu))
               or _norm(manu) in {_norm(str(a)) for a in m.getManufacturer().getAllNames()}]
        if not sel:
            raise UnknownMotor(f"{manufacturer} {designation}", sorted({
                f"{m.getManufacturer().getDisplayName()} {m.getDesignation()}" for m in cands})[:5])
        cands = sel
    best = min(cands, key=_pref)
    return _describe(best)


def suggest(base: str, n: int = 5) -> list[str]:
    """Closest designations: same impulse letter and similar average thrust number."""
    idx = _index()
    key = _norm(base)
    m = re.match(r"^([A-Z])(\d+)", key)
    names = sorted({str(x.getDesignation()) for v in idx.values() for x in v})
    if not m:
        return names[:n]
    letter, num = m.group(1), int(m.group(2))
    same = []
    for nm in names:
        mm = re.match(r"^([A-Z])(\d+)", _norm(nm))
        if mm and mm.group(1) == letter:
            same.append((abs(int(mm.group(2)) - num), nm))
    return [nm for _, nm in sorted(same)[:n]]


def public(info: dict) -> dict:
    return {k: v for k, v in info.items() if k not in ("digest", "or_type")}
