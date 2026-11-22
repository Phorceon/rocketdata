"""Stage 3: every motor the rocket flies must be a real motor.

The motor table (data/motor_table.json) lists 1,409 real motors keyed by a
motor id such as "AeroTech-M2000R-v2": the maker, a dash, the designation and
sometimes a version suffix "-vN". It holds every motor OpenRocket 24.12 has a
thrust curve for, with OpenRocket's own numbers and the digest OpenRocket finds
it by (built by tools/build_motor_table.py). A design names its motor in a "motor" node
that sits inside a "motormount" node of a body tube or inner tube:

    {"motor": {"attrs": {"configid": "cfg0"}, "children": [
        {"manufacturer": {"value": "AeroTech"}},
        {"motor_id": {"value": "AeroTech-M2000R-v2"}},
        {"designation": {"value": "M2000R"}},
        {"diameter": {"value": 0.098}}, ...]}}

A motor id written by the design is accepted as a table motor when it is the
same id up to letter case, when it leaves out the "-vN" suffix (the lowest
version is used), or when there is no motor id at all and the maker and
designation together match exactly one motor. Nothing else is accepted: a
wrong id is never corrected, only named in the reason as a likely meant motor.

An unknown motor fails the stage. Its credit is the share of three facts that
are true (see DESIGN.md, stage 3), and with several motors the worst counts.
"""
from __future__ import annotations

import difflib
import json
import math
import re
from pathlib import Path
from typing import Any, Optional, Union

from . import limits as L
from .errors import RewardSetupError
from .records import StageCheck
from .tree import (Node, attr_of, body_of, children_named, children_of, copy_tree, iter_components, last_child,
                   number, read_number, rocket_of, stages_of, tag_of)

DEFAULT_TABLE_PATH = Path(__file__).resolve().parent / "data" / "motor_table.json"

# Guards against hostile answers. They bound the work done per answer and the
# size of the log; no real motor comes near them.
MAX_ID_CHARS = 200            # longer "motor ids" are not looked up past the exact match
MAX_NUMBER_CHARS = 40         # a written diameter longer than this is not read as a number
MAX_SHOWN_CHARS = 60          # ids are cut to this length inside reasons
MAX_SUGGESTED_IDS = 20        # fuzzy "did you mean" search runs for at most this many ids
MAX_REASONS = 10              # reasons after this are summed up in one line
MAX_INFO_MOTORS = 50          # info["motors"] keeps this many entries; info["motor_count"] has the total

_VERSION_RE = re.compile(r"-v(\d+)$", re.IGNORECASE)
_CLASS_RE = re.compile(r"^(?:HP-)?(?:\d+/\d+)?\d*([A-Z])", re.IGNORECASE)
# HyperTEK names its motors by tank size first: "440CC098J" is a J motor with a
# 440 cc tank and a 0.098 inch injector ("RG" marks a different grain).
_HYPERTEK_RE = re.compile(r"^\d+CC(?:\d+|RG)([A-Z])", re.IGNORECASE)
# A designation ending in "-L200" says its class in that last part.
_DASH_CLASS_RE = re.compile(r"^([A-Z])\d+", re.IGNORECASE)
# Animal Motor Works names a motor by propellant, diameter in mm and total
# impulse in newton-seconds: "BB-54-1750" is a 1,750 Ns (K) motor, not class B.
_AMW_RE = re.compile(r"^[A-Z]{2}-\d{2,3}-(\d{1,6})$", re.IGNORECASE)
# Cesaroni writes some motors impulse first: "4263-L1350-CS" is an L motor.
_CTI_IMPULSE_FIRST_RE = re.compile(r"^\d+-([A-Z])\d+-[A-Z]+$", re.IGNORECASE)
# Quest's "MICRO_MAXX" motors are 0.15-0.30 Ns, class A (the "M" is not a class).
_MICRO_MAXX_RE = re.compile(r"^MICRO_MAXX", re.IGNORECASE)

MOUNT_TAGS = ("bodytube", "innertube")   # the only OpenRocket parts that can hold a motor


# ---------------------------------------------------------------------------
# small text helpers

def _split_version(motor_id: str) -> tuple[str, Optional[int]]:
    """'AeroTech-M2000R-v2' -> ('AeroTech-M2000R', 2); no suffix -> (id, None)."""
    m = _VERSION_RE.search(motor_id)
    if not m:
        return motor_id, None
    digits = m.group(1)
    return motor_id[: m.start()], (int(digits) if len(digits) <= 6 else None)


def _norm_designation(text: str) -> str:
    """Designation compared ignoring case, an 'HP-' prefix and a '-vN' suffix."""
    base, _ = _split_version(text.strip())
    base = base.upper()
    return base[3:] if base.startswith("HP-") else base


def _norm_id(text: str) -> str:
    """Motor id compared loosely, for "did you mean" only: no case, no '-vN',
    no 'HP-' after the maker."""
    base, _ = _split_version(text.strip())
    return base.lower().replace("-hp-", "-")


def impulse_class(total_impulse_ns: Any) -> Optional[str]:
    """Impulse class letter for a total impulse in newton-seconds.

    A is up to 2.5 Ns (this includes the 1/2A and 1/4A motors), B up to 5 Ns,
    C up to 10 Ns and so on. Returns None for a missing, zero, negative or
    absurd impulse.
    """
    if isinstance(total_impulse_ns, bool) or not isinstance(total_impulse_ns, (int, float)):
        return None
    if not math.isfinite(total_impulse_ns) or total_impulse_ns <= 0:
        return None
    steps = max(0, math.ceil(math.log2(total_impulse_ns / L.CLASS_A_MAX_NS)))
    return chr(ord("A") + steps) if steps < 26 else None


def class_from_designation(designation: Any) -> Optional[str]:
    """Class letter as written in a designation: 'H195NT' -> 'H',
    'HP-H195NT' -> 'H', '1109J440-P' -> 'J', '1/2A3' -> 'A'.

    HyperTEK designations put the tank size first: '440CC098J' -> 'J', and
    '1685CC098L-L200' -> 'L' (a last part such as 'L200' names the class).
    Animal Motor Works writes the impulse in Ns last: 'BB-54-1750' -> 'K'.
    Cesaroni's impulse-first names: '4263-L1350-CS' -> 'L'. Quest's
    'MICRO_MAXX' motors are class 'A'.
    """
    if not isinstance(designation, str) or len(designation) > MAX_ID_CHARS:
        return None
    text = _split_version(designation.strip())[0]
    m = _AMW_RE.match(text)
    if m:
        return impulse_class(float(m.group(1)))
    m = _CTI_IMPULSE_FIRST_RE.match(text)
    if m:
        return m.group(1).upper()
    if _MICRO_MAXX_RE.match(text):
        return "A"
    if "-" in text:
        last = text.rsplit("-", 1)[1]
        m = _DASH_CLASS_RE.match(last)
        if m and not _VERSION_RE.search("-" + last):
            return m.group(1).upper()
    m = _HYPERTEK_RE.match(text)
    if m:
        return m.group(1).upper()
    m = _CLASS_RE.match(text)
    return m.group(1).upper() if m else None


def written_average_thrust(designation: Any) -> Optional[float]:
    """The average thrust in newtons a designation states: the number right
    after its class letter ('H1650R' -> 1650.0, '1109J440-P' -> 440.0,
    'HP-H195NT' -> 195.0). None when no class letter can be read or no number
    follows it (e.g. 'BB-54-1750', '440CC098J')."""
    letter = class_from_designation(designation)
    if letter is None or not isinstance(designation, str):
        return None
    text = _norm_designation(designation)
    m = re.search(re.escape(letter) + r"(\d{1,6}(?:\.\d{1,6})?)", text)
    if not m:
        return None
    value = float(m.group(1))
    return value if value > 0 else None


# How a design writes the motor type (OpenRocket's file values first) -> the
# motor table's "motor_type".
_MOTOR_TYPES = {"single": "Single-use", "single-use": "Single-use", "singleuse": "Single-use",
                "disposable": "Single-use", "reload": "Reloadable", "reloadable": "Reloadable",
                "hybrid": "Hybrid"}


def motor_type_of(written: Any) -> Optional[str]:
    """The motor table's type ("Single-use", "Reloadable" or "Hybrid") for a
    type as a design writes it ("single", "reload", "hybrid"; OpenRocket's file
    values, letter case ignored). None for anything else, such as "unknown"."""
    if not isinstance(written, str) or len(written) > MAX_NUMBER_CHARS:
        return None
    return _MOTOR_TYPES.get(written.strip().lower())


def _positive(x: Any) -> Optional[float]:
    """x as a float when it is a finite number above 0, else None."""
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return None
    try:
        v = float(x)
    except OverflowError:
        return None
    return v if math.isfinite(v) and v > 0 else None


def _shown(x: Any) -> str:
    """How a written value appears inside a reason: quoted and cut short."""
    text = x if isinstance(x, str) else repr(x)
    if len(text) > MAX_SHOWN_CHARS:
        text = text[:MAX_SHOWN_CHARS] + "..."
    return "'" + text + "'" if isinstance(x, str) else text


# ---------------------------------------------------------------------------
# the table

class MotorTable:
    """The real motors, with the lookups stage 3 needs. Build it with load()."""

    def __init__(self, entries: dict[str, dict]) -> None:
        self._entries: dict[str, dict] = entries
        self._by_lower: dict[str, str] = {}
        self._by_base: dict[str, list[tuple[int, str]]] = {}      # lower id without -vN -> (version, key)
        self._by_maker_des: dict[tuple[str, str], list[str]] = {}  # (maker, designation) lower -> keys
        self._by_loose: dict[str, list[str]] = {}                  # _norm_id -> keys
        self._by_designation: dict[str, list[str]] = {}            # _norm_designation -> keys
        self._makers: dict[str, str] = {}                          # lower maker -> maker
        self._class_diameters: dict[str, list[float]] = {}
        self._by_class: dict[str, list[tuple[str, str]]] = {}      # class letter -> (designation, key)
        for key in sorted(entries):
            e = entries[key]
            low = key.lower()
            self._by_lower[low] = key
            base, ver = _split_version(key)
            if ver is not None:
                self._by_base.setdefault(base.lower(), []).append((ver, key))
            maker = e.get("manufacturer")
            des = e.get("designation")
            if isinstance(maker, str) and maker:
                self._makers.setdefault(maker.lower(), maker)
            if isinstance(maker, str) and isinstance(des, str):
                self._by_maker_des.setdefault((maker.lower(), des.lower()), []).append(key)
            if isinstance(des, str) and des:
                self._by_designation.setdefault(_norm_designation(des), []).append(key)
            self._by_loose.setdefault(_norm_id(key), []).append(key)
            written_class = class_from_designation(des)
            if written_class and isinstance(des, str):
                self._by_class.setdefault(written_class, []).append((_norm_designation(des), key))
            # A motor's diameter is listed under the class its impulse gives
            # AND under the letter its designation is sold with: about one in
            # nine real motors is sold under a letter one off from its measured
            # impulse (AeroTech H128W measures as a G), and a real motor must
            # always satisfy fact 3 for its own designation and diameter.
            dia = e.get("diameter_m")
            if isinstance(dia, (int, float)) and not isinstance(dia, bool) and math.isfinite(dia):
                for cls in {impulse_class(e.get("total_impulse_ns")), written_class}:
                    if not cls:
                        continue
                    ds = self._class_diameters.setdefault(cls, [])
                    if dia not in ds:
                        ds.append(float(dia))
        for versions in self._by_base.values():
            versions.sort()
        for ds in self._class_diameters.values():
            ds.sort()
        self._lower_keys = sorted(self._by_lower)
        # Motors by class letter (impulse class OR the letter they are sold under,
        # the same two ways fact 3 counts), for nearest_real.
        self._class_keys: dict[str, list[str]] = {}
        for key in sorted(entries):
            e = entries[key]
            for cls in sorted({c for c in (impulse_class(e.get("total_impulse_ns")),
                                            class_from_designation(e.get("designation"))) if c}):
                self._class_keys.setdefault(cls, []).append(key)

    # -- building -----------------------------------------------------------

    @classmethod
    def load(cls, path: Union[str, Path, None] = None) -> "MotorTable":
        """Read the motor table. A missing or broken file raises RewardSetupError,
        because no answer can be scored fairly without it."""
        p = Path(path) if path is not None else DEFAULT_TABLE_PATH
        try:
            with open(p, encoding="utf-8") as fh:
                data = json.load(fh)
        except FileNotFoundError:
            raise RewardSetupError(
                f"motor table not found at {p}; restore rocket_reward/data/motor_table.json "
                "from the repository or pass the right path") from None
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            raise RewardSetupError(
                f"motor table at {p} cannot be read ({exc}); restore "
                "rocket_reward/data/motor_table.json from the repository") from None
        if not isinstance(data, dict) or not data:
            raise RewardSetupError(
                f"motor table at {p} must be a JSON object of motor id -> motor data and "
                "must not be empty; restore rocket_reward/data/motor_table.json")
        bad = [k for k, v in data.items() if not isinstance(v, dict)
               or not isinstance(v.get("manufacturer"), str) or not isinstance(v.get("designation"), str)]
        if bad:
            raise RewardSetupError(
                f"motor table at {p} has {len(bad)} entries without a manufacturer and designation "
                f"(first: {bad[0]!r}); restore rocket_reward/data/motor_table.json")
        return cls(data)

    # -- lookups ------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._entries)

    def __contains__(self, key: object) -> bool:
        return isinstance(key, str) and key in self._entries

    def get(self, key: str) -> dict:
        """The table entry for a canonical key (raises KeyError for an unknown key)."""
        return self._entries[key]

    def resolve(self, motor_id: Any, manufacturer: Any = None, designation: Any = None) -> Optional[str]:
        """The canonical table key for a motor as the design wrote it, or None.

        Accepted: the exact id; the id in other letter case; the id without
        its '-vN' suffix (the lowest version is used); and, only when no
        motor id is written, a maker and designation that match exactly one
        motor (versions of one motor count as one; the lowest is used).
        """
        if isinstance(motor_id, str) and motor_id.strip():
            mid = motor_id.strip()
            if mid in self._entries:
                return mid
            if len(mid) > MAX_ID_CHARS:
                return None
            low = mid.lower()
            if low in self._by_lower:
                return self._by_lower[low]
            if _VERSION_RE.search(low) is None and low in self._by_base:
                return self._by_base[low][0][1]
            return None
        if motor_id is not None and not (isinstance(motor_id, str)):
            return None   # a number or a list is not a motor id, and is not "left out" either
        if not (isinstance(manufacturer, str) and isinstance(designation, str)):
            return None
        if len(manufacturer) > MAX_ID_CHARS or len(designation) > MAX_ID_CHARS:
            return None
        keys = self._by_maker_des.get((manufacturer.strip().lower(), designation.strip().lower()), [])
        motors: dict[str, list[tuple[int, str]]] = {}
        for k in keys:
            base, ver = _split_version(k)
            motors.setdefault(base, []).append((ver or 0, k))
        if len(motors) != 1:
            return None
        return min(next(iter(motors.values())))[1]

    def is_maker(self, name: Any) -> bool:
        """True when `name` is a maker in the table (letter case ignored)."""
        return isinstance(name, str) and len(name) <= MAX_ID_CHARS and name.strip().lower() in self._makers

    def maker_prefix(self, motor_id: Any) -> Optional[str]:
        """The table maker a motor id starts with ('AeroTech-H195NT' -> 'AeroTech'), or None."""
        if not isinstance(motor_id, str) or len(motor_id) > MAX_ID_CHARS:
            return None
        low = motor_id.strip().lower()
        best = None
        for maker_low, maker in self._makers.items():
            if low.startswith(maker_low + "-") and (best is None or len(maker) > len(best)):
                best = maker
        return best

    def has_designation(self, designation: Any) -> bool:
        """True when some maker sells a motor with this designation (ignoring
        case, an 'HP-' prefix and a '-vN' suffix)."""
        return (isinstance(designation, str) and len(designation) <= MAX_ID_CHARS
                and _norm_designation(designation) in self._by_designation)

    def diameters_for_class(self, letter: Any) -> list[float]:
        """Every diameter (metres) a real motor of this class has: motors whose
        impulse falls in the class, and motors sold under that letter."""
        if not isinstance(letter, str):
            return []
        return list(self._class_diameters.get(letter.upper(), ()))

    def class_has_diameter(self, letter: Any, diameter_m: Any) -> bool:
        """True when a real motor of this class is this wide (within half a millimetre)."""
        if isinstance(diameter_m, bool) or not isinstance(diameter_m, (int, float)):
            return False
        if not math.isfinite(diameter_m) or diameter_m <= 0:
            return False
        if not isinstance(letter, str):
            return False
        return any(abs(d - diameter_m) <= L.MOTOR_DIAMETER_MATCH_M for d in self._class_diameters.get(letter.upper(), ()))

    def class_of(self, key: str) -> Optional[str]:
        """Impulse class letter of a table motor (None when the table has no impulse for it)."""
        e = self._entries.get(key)
        return impulse_class(e.get("total_impulse_ns")) if e else None

    def nearest_real(self, designation: Any, diameter_m: Any, maker: Any = None,
                     motor_type: Any = None) -> Optional[str]:
        """The real motor closest to an invented one, for shadow flights only.

        It is never accepted in place of the written motor: scoring flies it
        only to see how far the rest of the design would get. The rule is
        fixed, so the same answer always gets the same substitute:

        1. The class letter the written designation names
           (class_from_designation). No readable letter: no substitute (None).
        2. Motors of that class (by impulse, or sold under that letter) as
           wide as `diameter_m`, within limits.MOTOR_DIAMETER_MATCH_M. When
           none is that wide, those of the nearest diameter the class has (the
           smaller one on a tie). Without a usable diameter, every motor of the
           class. (substitute_unknown_motors passes the size that fits the
           design's mount, MotorTable.fitting_diameter, not the written one.)
        3. Of those, only the ones of the motor type the design wrote
           (`motor_type`: single-use, reload or hybrid, see motor_type_of),
           when at least one has it; a hybrid flies with a heavy tank, so the
           type matters more for the flight than the maker.
        4. Of those, only the ones sold by `maker` (letter case ignored), when
           at least one is.
        5. Among those, the one whose average thrust is closest to the number
           after the class letter in the written designation ("H1650R" ->
           1650 N). Without such a number this step is skipped.
        6. Ties: the smaller total impulse, then the motor id in sorting order.
        """
        letter = class_from_designation(designation)
        keys = self._class_keys.get(letter or "", [])
        if not keys:
            return None
        dia = _positive(diameter_m)

        def width(k: str) -> Optional[float]:
            return _positive(self._entries[k].get("diameter_m"))

        if dia is not None:
            sized = [k for k in keys if width(k) is not None]
            same = [k for k in sized if abs(width(k) - dia) <= L.MOTOR_DIAMETER_MATCH_M]  # type: ignore[operator]
            if not same and sized:
                nearest = min({width(k) for k in sized}, key=lambda d: (abs(d - dia), d))  # type: ignore[operator]
                same = [k for k in sized if abs(width(k) - nearest) <= L.MOTOR_DIAMETER_MATCH_M]  # type: ignore[operator]
            keys = same
        if not keys:
            return None
        kind = motor_type_of(motor_type)
        if kind is not None:
            keys = [k for k in keys if self._entries[k].get("motor_type") == kind] or keys
        if isinstance(maker, str) and maker.strip() and len(maker) <= MAX_ID_CHARS:
            low = maker.strip().lower()
            keys = [k for k in keys if str(self._entries[k].get("manufacturer", "")).lower() == low] or keys
        thrust = written_average_thrust(designation)

        def rank(k: str) -> tuple:
            e = self._entries[k]
            avg = _positive(e.get("average_thrust_n"))
            ns = _positive(e.get("total_impulse_ns"))
            miss = 0.0 if thrust is None else (abs(avg - thrust) if avg is not None else math.inf)
            return (miss, ns if ns is not None else math.inf, k)

        return min(keys, key=rank)

    def fitting_diameter(self, letter: Any, room_m: Any) -> Optional[float]:
        """The motor diameter (metres) a shadow flight uses for a mount with an
        inside diameter of `room_m`: the largest diameter a real motor of this
        class has that fits the mount (at most limits.MOTOR_DIAMETER_MAX_RATIO
        times its inside diameter, the stage 5 limit); when none fits, the
        smallest one the class has. None when the class has no sized motor or
        the room is not a positive number."""
        room = _positive(room_m)
        sizes = sorted(d for d in self.diameters_for_class(letter) if _positive(d) is not None)
        if room is None or not sizes:
            return None
        fits = [d for d in sizes if d <= room * L.MOTOR_DIAMETER_MAX_RATIO]
        return fits[-1] if fits else sizes[0]

    def suggest(self, motor_id: Any, designation: Any = None) -> Optional[str]:
        """A real motor the design probably meant, for the reason text only.
        It is never accepted in place of the written id."""
        if isinstance(motor_id, str) and 0 < len(motor_id) <= MAX_ID_CHARS:
            loose = self._by_loose.get(_norm_id(motor_id))
            if loose:
                return loose[0]
        if isinstance(designation, str) and 0 < len(designation) <= MAX_ID_CHARS:
            same = self._by_designation.get(_norm_designation(designation))
            if same:
                maker = self.maker_prefix(motor_id) if isinstance(motor_id, str) else None
                for k in same:
                    if maker and k.startswith(maker + "-"):
                        return k
                return same[0]
        # Last try: a motor of the same class letter whose designation is
        # spelled almost the same ('H160R' -> 'H165R'), from the same maker
        # when the design names a real one.
        if isinstance(designation, str) and 0 < len(designation) <= MAX_ID_CHARS:
            letter = class_from_designation(designation)
            pool = self._by_class.get(letter or "", [])
            maker = self.maker_prefix(motor_id) if isinstance(motor_id, str) else None
            if maker:
                same_maker = [p for p in pool if p[1].startswith(maker + "-")]
                pool = same_maker or pool
            names = sorted({d for d, _ in pool})
            close = difflib.get_close_matches(_norm_designation(designation), names, n=1, cutoff=0.75)
            if close:
                return next(k for d, k in pool if d == close[0])
        return None


# ---------------------------------------------------------------------------
# where the motors are (the tree is read with tree.py)

def mount_motors(root: Any, legal_only: bool = False) -> list[tuple[Node, Node]]:
    """(motor mount tube, motor node) for every motor inside a motor mount of a
    body tube or inner tube anywhere inside the rocket's stages, in document
    order. With `legal_only`, tubes placed where OpenRocket drops them are left out."""
    out = []
    for stage in stages_of(root):
        for comp in iter_components(stage, legal_only):
            if tag_of(comp) not in MOUNT_TAGS:
                continue
            for mm in children_named(comp, "motormount"):
                out.extend((comp, m) for m in children_named(mm, "motor"))
    return out


def _is_default(value: Any) -> bool:
    return value is True or (isinstance(value, str) and value.strip().lower() == "true")


def flown_config_id(root: Node) -> Optional[str]:
    """The motor configuration OpenRocket flies: the rocket's
    "motorconfiguration" marked default="true", else the first one. When
    several are marked default, the LAST one counts, because OpenRocket's
    loader selects each one it reads in turn. Returns its configid, or None
    when the rocket declares no usable configuration."""
    rocket = rocket_of(root)
    if rocket is None:
        return None
    first = None
    default = None
    for c in children_named(rocket, "motorconfiguration"):
        cid = attr_of(c, "configid")
        if not isinstance(cid, str) or not cid.strip():
            continue
        if _is_default(attr_of(c, "default")):
            default = cid
        if first is None:
            first = cid
    return default if default is not None else first


def flown_motors(root: Node) -> list[Node]:
    """The motor nodes OpenRocket flies: motors inside a motor mount whose
    configid is the flown configuration's id."""
    cid = flown_config_id(root)
    if cid is None:
        return []
    return [m for _, m in mount_motors(root) if attr_of(m, "configid") == cid]


# ---------------------------------------------------------------------------
# stage 3

_MOTOR_FIELDS = ("motor_id", "manufacturer", "designation", "diameter")


def _motor_fields(motor: Node) -> tuple:
    """The values of a motor node's motor_id, manufacturer, designation and
    diameter children (None when missing), read in one pass. When a field is
    written twice the LAST copy counts, as it does when OpenRocket loads the
    file (and clean.py keeps only that copy)."""
    found: dict[str, Any] = {}
    for c in children_of(motor):
        tag = tag_of(c)
        if tag in _MOTOR_FIELDS:
            found[tag] = body_of(c).get("value")
    return tuple(found.get(t) for t in _MOTOR_FIELDS)


def _motor_facts(fields: tuple, table: MotorTable) -> dict[str, Any]:
    """What one motor says, whether it is real, and the three credit facts."""
    written_id, maker, des, dia_raw = fields
    key = table.resolve(written_id, maker, des)

    # The maker: as written, else read from the front of the motor id.
    maker_used = maker if isinstance(maker, str) and maker.strip() else table.maker_prefix(written_id)
    # The designation: as written, else the motor id after its maker.
    des_used = des if isinstance(des, str) and des.strip() else None
    if des_used is None and isinstance(written_id, str):
        prefix = table.maker_prefix(written_id)
        if prefix:
            des_used = written_id.strip()[len(prefix) + 1:]
    letter = class_from_designation(des_used)
    dia = None if isinstance(dia_raw, str) and len(dia_raw) > MAX_NUMBER_CHARS else number(dia_raw)

    facts = {
        "maker_real": table.is_maker(maker_used),
        "designation_real": table.has_designation(des_used),
        "class_diameter_real": letter is not None and table.class_has_diameter(letter, dia),
    }
    return {"written_id": written_id if isinstance(written_id, (str, type(None))) else repr(written_id)[:MAX_SHOWN_CHARS],
            "manufacturer": maker if isinstance(maker, str) else None,
            "designation": des if isinstance(des, str) else None,
            "key": key, "class": letter, "diameter_m": dia, **facts,
            "_maker_used": maker_used, "_des_used": des_used}


def _unknown_reason(f: dict[str, Any], suggestion: Optional[str]) -> str:
    wid = f["written_id"]
    if isinstance(wid, str) and wid.strip():
        what = f"motor {_shown(wid)} is not a real motor"
    elif wid is None or (isinstance(wid, str) and not wid.strip()):
        what = (f"motor with no motor_id (maker {_shown(f['manufacturer'])}, designation "
                f"{_shown(f['designation'])}) does not match exactly one real motor")
    else:
        what = f"motor id {wid} is not text, so it is not a real motor"
    if suggestion:
        what += f"; did you mean {_shown(suggestion)}?"
    notes = []
    mk, ds = f["_maker_used"], f["_des_used"]
    notes.append(f"maker {_shown(mk)} is {'a real maker' if f['maker_real'] else 'not a maker in the motor table'}"
                 if mk is not None else "no maker given")
    notes.append(f"designation {_shown(ds)} {'exists' if f['designation_real'] else 'is not sold by any maker'}"
                 if ds is not None else "no designation given")
    if f["class"] is None:
        notes.append("no impulse class letter can be read from the designation")
    elif f["diameter_m"] is None:
        notes.append("no usable diameter given")
    else:
        mm = f["diameter_m"] * 1000.0
        mm_text = f"{mm:.1f} mm" if abs(mm) < 1e6 else "an absurd size"
        notes.append(f"a real {f['class']} motor {'is' if f['class_diameter_real'] else 'is never'} {mm_text} wide")
    return f"{what} ({'; '.join(notes)})"


_SUBSTITUTED_FIELDS = frozenset({"motor_id", "manufacturer", "designation", "diameter", "length", "digest"})


def mount_room_m(mount: Node) -> Optional[float]:
    """Inside diameter (metres) of a motor mount tube as written: twice its
    radius ("radius" of a body tube, "outerradius" of an inner tube) less its
    wall. None when the radius is not a positive number (for example
    "auto") or nothing is left inside. A setting written twice counts by its
    last copy, as OpenRocket reads it."""
    t = tag_of(mount)
    field = "radius" if t == "bodytube" else "outerradius" if t == "innertube" else None
    if field is None:
        return None
    c = last_child(mount, field)
    r = read_number(body_of(c).get("value"))[0] if c is not None else None
    if r is None or r <= 0:
        return None
    c = last_child(mount, "thickness")
    raw = body_of(c).get("value") if c is not None else None
    if isinstance(raw, str) and raw.strip().lower() == "filled":
        return None
    wall = read_number(raw)[0]
    inner = r - (wall if wall is not None and wall > 0 else 0.0)
    return 2.0 * inner if inner > 0 else None


def substitute_unknown_motors(root: Node, table: MotorTable,
                              same_maker: bool = True) -> tuple[Optional[Node], list[dict[str, Any]]]:
    """A copy of the design in which every unknown flown motor is replaced by
    MotorTable.nearest_real, for a shadow flight (scoring.py).

    Returns (copy, substitutes), where substitutes lists one
    {"written", "designation", "diameter_m", "substitute"} per unknown motor
    (at most MAX_INFO_MOTORS are listed). The copy is None when there is no
    unknown motor, or when some unknown motor gets no substitute (its
    designation names no class letter); the input is never changed. In the
    copy the motor's id, maker and designation are the substitute's; its size
    and digest are left to the cleaning, which takes them from the table.

    The substitute's diameter comes from the mount, never from the diameter
    the design writes for its motor (that one only decides stage 3's third
    fact): MotorTable.fitting_diameter of the mount's inside diameter
    (mount_room_m), or any diameter of the class when the mount's size cannot
    be read. So writing a true diameter never picks a worse substitute.

    Among the motors that fit, the substitute has the motor type the design
    wrote for this motor ("type": single, reload or hybrid) and, with
    `same_maker`, the maker it names (as written, else the front of its motor
    id), whenever such a motor exists (MotorTable.nearest_real, steps 3 and 4).
    Naming a real maker can therefore change the substitute; scoring.py also
    flies the copy made with same_maker=False and keeps the better of the two,
    so a true maker never lowers the score either.
    """
    shadow = copy_tree(root)
    subs: list[dict[str, Any]] = []
    possible = True
    cid = flown_config_id(shadow)
    pairs = [(mount, m) for mount, m in mount_motors(shadow) if cid is not None and attr_of(m, "configid") == cid]
    for mount, motor in pairs:
        fields = _motor_fields(motor)
        f = _motor_facts(fields, table)
        if f["key"] is not None:
            continue
        room = mount_room_m(mount)
        size = table.fitting_diameter(f["class"], room)
        type_node = last_child(motor, "type")
        written_type = body_of(type_node).get("value") if type_node is not None else None
        key = table.nearest_real(f["_des_used"], size, maker=f["_maker_used"] if same_maker else None,
                                 motor_type=written_type)
        if len(subs) < MAX_INFO_MOTORS:
            subs.append({"written": f["written_id"] if isinstance(f["written_id"], str) else None,
                         "designation": f["_des_used"] if isinstance(f["_des_used"], str) else None,
                         "diameter_m": f["diameter_m"], "mount_diameter_m": room, "substitute": key})
        if key is None:
            possible = False
            continue
        entry = table.get(key)
        body = motor[tag_of(motor)]
        if not isinstance(body, dict):
            possible = False
            continue
        kids = [c for c in children_of(motor) if tag_of(c) not in _SUBSTITUTED_FIELDS]
        kids += [{"manufacturer": {"value": entry["manufacturer"]}}, {"motor_id": {"value": key}},
                 {"designation": {"value": entry["designation"]}}]
        body["children"] = kids
    if not subs or not possible:
        return None, subs
    return shadow, subs


def check_motors(root: Node, table: MotorTable) -> StageCheck:
    """Stage 3: every motor in the flown configuration must be a real motor.

    info["motors"] holds one dict per flown motor (the first 50; the total is
    info["motor_count"]): the id as written, the table key it resolves to (or
    None) and the three credit facts. A failing design's credit is the share
    of true facts of its worst unknown motor.
    """
    motors = flown_motors(root)
    if not motors:
        cid = flown_config_id(root)
        why = ("the rocket declares no motor configuration, so OpenRocket would fly it with no motor"
               if cid is None else
               f"no motor inside a motor mount uses the flown configuration {_shown(cid)}, "
               "so OpenRocket would fly it with no motor")
        return StageCheck("motor", passed=False, credit=0.0, reasons=[why],
                          info={"motors": [], "motor_count": 0, "configid": cid})

    cache: dict[Any, dict[str, Any]] = {}
    infos: list[dict[str, Any]] = []
    reasons: list[str] = []
    unknown_count = 0
    suggested = 0
    worst = 1.0
    for m in motors:
        fields = _motor_fields(m)
        try:
            f = cache.get(fields)
            sig: Any = fields
        except TypeError:                     # a list or dict value cannot be a cache key
            sig = tuple(v if isinstance(v, (str, int, float, bool, type(None))) else repr(type(v))
                        for v in fields)
            f = cache.get(sig)
        new = f is None
        if new:
            f = _motor_facts(fields, table)
            cache[sig] = f
        if len(infos) < MAX_INFO_MOTORS:
            infos.append({k: v for k, v in f.items() if not k.startswith("_")})
        if f["key"] is not None:
            continue
        unknown_count += 1
        share = (int(f["maker_real"]) + int(f["designation_real"]) + int(f["class_diameter_real"])) / 3.0
        worst = min(worst, share)
        if new and len(reasons) < MAX_REASONS:
            suggestion = None
            if suggested < MAX_SUGGESTED_IDS:
                suggested += 1
                suggestion = table.suggest(f["written_id"] if isinstance(f["written_id"], str) else None,
                                           f["_des_used"])
            reasons.append(_unknown_reason(f, suggestion))
    if unknown_count == 0:
        return StageCheck("motor", passed=True, credit=1.0,
                          info={"motors": infos, "motor_count": len(motors)})
    distinct_unknown = sum(1 for f in cache.values() if f["key"] is None)
    if distinct_unknown > len(reasons):
        reasons.append(f"... and {distinct_unknown - len(reasons)} more unknown motors")
    return StageCheck("motor", passed=False, credit=worst, reasons=reasons,
                      info={"motors": infos, "motor_count": len(motors), "unknown_count": unknown_count})
