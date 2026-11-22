"""The material table: the real density of every material name the reward knows.

A design names a material in three kinds of node:

    {"material":       {"attrs": {"type": "bulk",    "density": 680.0}, "value": "Cardboard"}}
    {"filletmaterial": {"attrs": {"type": "bulk",    "density": 680.0}, "value": "Cardboard"}}
    {"linematerial":   {"attrs": {"type": "line",    "density": 0.001}, "value": "Braided nylon (2 mm, 1/16 in)"}}

The density the model writes is never trusted (DESIGN.md, section 5): the
cleaning (clean.apply_material_densities) replaces it by the table value for
the slot's type and the material's name, so the model cannot make its rocket
lighter by writing a made-up density. A name the table does not know cannot be
given a density: it keeps its written density, and stage 4
(limit_checks.check_material_names) fails it. Both follow what OpenRocket's
loader does with a material node (slot_type, loaded_type below).

The table (data/material_table.json) is built by tools/build_material_table.py
from three sources, in this order of trust:

  openrocket  OpenRocket 24.12's built-in material database
  preset      materials of the component preset files (.orc) shipped in the
              OpenRocket jar: manufacturers' real parts
  reference   names only the reference ("gold") designs use, mostly Rocksim
              imports written "RS: ...", with the density those designs write

Densities are in SI units: kg/m3 for "bulk", kg/m2 for "surface" (parachute
and streamer cloth) and kg/m for "line" (shroud lines, shock cords).

How a name is matched (MaterialTable.match), first rule that finds it wins:

  1. exact     the type and the name exactly as written in the table
  2. loose     the same name up to letter case and spacing: case is ignored
               (OpenRocket itself ignores case when it looks a material up),
               spaces at the ends are dropped and every run of spaces, tabs or
               line breaks counts as one space
  3. rocksim   the same name once a leading "RS:" is taken off both sides.
               OpenRocket writes "RS: " in front of every material it imports
               from a Rocksim file; the material is the same physical one
               (the reference designs' "RS: Birch", "RS: Brass", "RS: Kraft
               phenolic" are within 2% of OpenRocket's own Birch, Brass and
               Kraft phenolic). So "RS: Aluminum" is Aluminum, and a plain
               "Thin poly" is the table's "RS: Thin poly".

When one rule finds several table entries (for example "30 Lb. kevlar" and
"30 Lb. Kevlar" from two preset files), the heaviest one is used, so a choice
between spellings can never make a rocket lighter.

The type is read up to case and spacing ("Bulk" is "bulk"). An unknown type,
a name that is not text, an empty name or a name longer than MAX_NAME_CHARS
is never matched.
"""
from __future__ import annotations

import difflib
import json
import math
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Union

from .errors import RewardSetupError

DEFAULT_TABLE_PATH = Path(__file__).resolve().parent / "data" / "material_table.json"

MATERIAL_TYPES = ("bulk", "surface", "line")
UNITS = {"bulk": "kg/m3", "surface": "kg/m2", "line": "kg/m"}
SOURCES = ("openrocket", "preset", "reference")

# The prefix OpenRocket puts in front of materials it imports from Rocksim files.
ROCKSIM_PREFIX = "rs:"

# Guard against hostile answers: names longer than this are never matched
# (the longest name in the table has 70 characters). It bounds the work
# per lookup; it is not a tuning number and never changes a sound design's score.
MAX_NAME_CHARS = 200

MATCH_RULES = ("exact", "loose", "rocksim")

# How alike two names must be spelled (difflib's ratio, 0 to 1, up to case,
# spacing and a leading "RS:") before a reason suggests the table name: a
# close spelling only. For the reason text only; it never changes a score.
# Set between the two groups seen in the unknown names of the model's 48
# validation answers: every variant of a real name is at least 0.76 alike
# ('Braided nylon (1 mm, 1/16 in)' -> 'Braided nylon (2 mm, 1/16 in)' 0.97,
# a 'Paper, spiral kraft glassine, OK tubular, ...' tube -> another kraft
# glassine paper 0.76), and every different material is at most 0.67
# ('Bronze' -> 'Oak (Brown)' 0.47, 'Inconel' -> 'Pine' 0.55, 'Woods' ->
# 'Basswood' 0.62, 'RS: Flexible phenolic' -> 'Glassed Phenolic' 0.67).
CLOSE_NAME_RATIO_MIN = 0.7

# Where a student finds the names the reward knows, for the reason text.
NAME_LIST_HINT = ("the names the reward knows are OpenRocket's own material list plus its parts catalogue, "
                  "listed under \"materials\" in rocket_reward/data/material_table.json")


@dataclass(frozen=True)
class MaterialMatch:
    """What the table says about one material as a design wrote it.

    name     the table's own spelling of the matched name
    density  the table density in SI units (see UNITS)
    source   "openrocket", "preset" or "reference"
    rule     which matching rule found it: "exact", "loose" or "rocksim"
    """
    name: str
    density: float
    source: str
    rule: str


# The material type each slot holds when OpenRocket loads a file (its
# DocumentConfig): a recovery device's cloth is a surface material, a shock
# cord and a parachute's shroud lines are line materials, and every other
# part's material (and a fin set's fillet) is bulk. OpenRocket uses the
# slot's own type, not the file's: a material with no "type" attribute is
# loaded as the slot's type, and one whose "type" is anything other than
# exactly that type's lower-case name ("bulk", not "Bulk" or " bulk") is
# ignored with a warning, so the part keeps its default material.
_SURFACE_SLOTS = frozenset({"parachute", "streamer"})
_LINE_SLOTS = frozenset({"shockcord"})
_FIN_SETS = frozenset({"trapezoidfinset", "ellipticalfinset", "freeformfinset", "tubefinset"})
_NO_MATERIAL = frozenset({"masscomponent", "stage", "parallelstage", "podset", "rocket"})


def slot_type(component_tag: str, material_tag: str) -> Optional[str]:
    """The material type OpenRocket loads into this slot ("bulk", "surface"
    or "line"), or None when the component has no such slot."""
    if material_tag == "linematerial":
        return "line" if component_tag == "parachute" else None
    if material_tag == "filletmaterial":
        return "bulk" if component_tag in _FIN_SETS else None
    if material_tag != "material" or component_tag in _NO_MATERIAL:
        return None
    if component_tag in _SURFACE_SLOTS:
        return "surface"
    if component_tag in _LINE_SLOTS:
        return "line"
    return "bulk"


def loaded_type(component_tag: str, material_tag: str, written_type: Any) -> Optional[str]:
    """The type OpenRocket actually loads for a material node as written, or
    None when it ignores the node (wrong type) or the slot is unknown.

    No type written means the slot's type. For a slot this module does not
    know, the written type is returned when it is one of MATERIAL_TYPES."""
    expected = slot_type(component_tag, material_tag)
    if expected is None:
        return written_type if written_type in MATERIAL_TYPES else None
    if written_type is None:
        return expected
    return expected if written_type == expected else None


def name_text(value: Any) -> Optional[str]:
    """A material node's value as the name OpenRocket reads from the file:
    text as written, true/false and numbers as the file writer spells them,
    None for anything else (a list or object, which cannot be written).
    A missing value is the empty name."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return value
    if isinstance(value, int):
        return str(value) if abs(value) < 10 ** 30 else None
    if isinstance(value, float):
        return repr(value)
    return None


def means_no_material(name: str) -> bool:
    """True for a name that names no material: empty, only spaces, or only
    the Rocksim prefix "RS:" (the reference designs write "RS:" for a
    parachute's shroud lines when the Rocksim file gave none)."""
    return rocksim_name(name) == ""


def loose_name(name: str) -> str:
    """The name with case and spacing differences taken out (rule 2)."""
    return " ".join(name.split()).casefold()


def rocksim_name(name: str) -> str:
    """The loose name with a leading "RS:" taken off (rule 3)."""
    key = loose_name(name)
    if key.startswith(ROCKSIM_PREFIX):
        key = key[len(ROCKSIM_PREFIX):].strip()
    return key


def _type_key(material_type: Any) -> Optional[str]:
    if not isinstance(material_type, str) or len(material_type) > 20:
        return None
    t = material_type.strip().lower()
    return t if t in MATERIAL_TYPES else None


class MaterialTable:
    """Material names and densities, with the lookups clean.py and stage 4
    need. Build it with load()."""

    def __init__(self, materials: dict[str, dict[str, dict]]) -> None:
        self._exact: dict[str, dict[str, MaterialMatch]] = {}
        self._loose: dict[str, dict[str, MaterialMatch]] = {}
        self._rocksim: dict[str, dict[str, MaterialMatch]] = {}
        for mtype in MATERIAL_TYPES:
            exact: dict[str, MaterialMatch] = {}
            loose: dict[str, MaterialMatch] = {}
            rocksim: dict[str, MaterialMatch] = {}
            for name in sorted(materials.get(mtype, {})):
                e = materials[mtype][name]
                d = float(e["density"])
                src = e["source"]
                exact[name] = MaterialMatch(name, d, src, "exact")
                for index, key, rule in ((loose, loose_name(name), "loose"),
                                         (rocksim, rocksim_name(name), "rocksim")):
                    if not key:
                        continue
                    old = index.get(key)
                    if old is None or d > old.density:
                        index[key] = MaterialMatch(name, d, src, rule)
            self._exact[mtype] = exact
            self._loose[mtype] = loose
            self._rocksim[mtype] = rocksim

    # -- building -----------------------------------------------------------

    @classmethod
    def load(cls, path: Union[str, Path, None] = None) -> "MaterialTable":
        """Read the material table. A missing or broken file raises
        RewardSetupError, because no answer can be scored fairly without it."""
        p = Path(path) if path is not None else DEFAULT_TABLE_PATH
        fix = ("restore rocket_reward/data/material_table.json from the repository, or rebuild it "
               "with python -m rocket_reward.tools.build_material_table")
        try:
            with open(p, encoding="utf-8") as fh:
                data = json.load(fh)
        except FileNotFoundError:
            raise RewardSetupError(f"material table not found at {p}; {fix}, or pass the right path") from None
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            raise RewardSetupError(f"material table at {p} cannot be read ({exc}); {fix}") from None
        materials = data.get("materials") if isinstance(data, dict) else None
        if not isinstance(materials, dict) or not all(isinstance(materials.get(t), dict) and materials[t]
                                                      for t in MATERIAL_TYPES):
            raise RewardSetupError(
                f"material table at {p} must hold a \"materials\" object with a non-empty "
                f"list for each of {', '.join(MATERIAL_TYPES)}; {fix}")
        for mtype in MATERIAL_TYPES:
            for name, e in materials[mtype].items():
                d = e.get("density") if isinstance(e, dict) else None
                ok = (isinstance(name, str) and name.strip() != ""
                      and isinstance(d, (int, float)) and not isinstance(d, bool)
                      and math.isfinite(d) and d > 0 and e.get("source") in SOURCES)
                if not ok:
                    raise RewardSetupError(
                        f"material table at {p} has a broken {mtype} entry {name!r} (each entry needs a "
                        f"positive density and a source of {', '.join(SOURCES)}); {fix}")
        return cls(materials)

    # -- lookups ------------------------------------------------------------

    def match(self, material_type: Any, name: Any) -> Optional[MaterialMatch]:
        """The table entry for a material as a design wrote it, or None when
        the table does not know it. See the module text for the rules."""
        t = _type_key(material_type)
        if t is None or not isinstance(name, str) or len(name) > MAX_NAME_CHARS:
            return None
        hit = self._exact[t].get(name)
        if hit is not None:
            return hit
        key = loose_name(name)
        if not key:
            return None
        hit = self._loose[t].get(key)
        if hit is not None:
            return hit
        key = rocksim_name(name)
        return self._rocksim[t].get(key) if key else None

    def lookup(self, material_type: Any, name: Any) -> Optional[float]:
        """The table density (SI units) for this type and name, or None."""
        hit = self.match(material_type, name)
        return hit.density if hit is not None else None

    def names(self, material_type: Any) -> list[str]:
        """Every name of this type, sorted (an empty list for an unknown type)."""
        t = _type_key(material_type)
        return sorted(self._exact[t]) if t is not None else []

    def closest(self, material_type: Any, name: Any) -> Optional[str]:
        """The table name of this type spelled most like `name` (up to case,
        spacing and a leading "RS:"), for a reason text only; never used in
        place of the written name. None for an unknown type, an unusable name,
        or when no table name is spelled closely enough (at least
        CLOSE_NAME_RATIO_MIN alike): 'Bronze' gets no suggestion rather than
        'Oak (Brown)'."""
        t = _type_key(material_type)
        if t is None or not isinstance(name, str) or len(name) > MAX_NAME_CHARS:
            return None
        key = rocksim_name(name)
        if not key:
            return None
        pool = self._rocksim[t]
        best = difflib.get_close_matches(key, list(pool), n=1, cutoff=CLOSE_NAME_RATIO_MIN)
        return pool[best[0]].name if best else None

    def source(self, material_type: Any, name: Any) -> Optional[str]:
        """Where the matched entry's density came from, or None."""
        hit = self.match(material_type, name)
        return hit.source if hit is not None else None

    def __len__(self) -> int:
        return sum(len(v) for v in self._exact.values())


_table_lock = threading.Lock()
_table_cache: list[MaterialTable] = []   # holds the packaged table once it is loaded


def default_material_table() -> MaterialTable:
    """The packaged material table (data/material_table.json), loaded on first
    use and kept. A missing or broken file raises RewardSetupError."""
    with _table_lock:
        if not _table_cache:
            _table_cache.append(MaterialTable.load())
        return _table_cache[0]
