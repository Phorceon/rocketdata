"""Design tree -> OpenRocket file.

`design_to_ork(root)` writes a design tree (see tree.py; the root tag is
"openrocket") as the text of an OpenRocket .ork file: plain UTF-8 XML that
OpenRocket 24.12 loads directly.

What it does on the way:

* Every node becomes one XML element: "attrs" become attributes, "value"
  becomes the element's text and "children" become child elements, in the
  same order (order matters to OpenRocket: relative positions follow it).
* Numbers are written so that OpenRocket reads exactly the value the
  reward's own number reader (tree.java_number, used by every stage) read:
  floats use Python's shortest round-trip spelling (Java's Double.parseDouble
  reads the same double), integers as digits, true/false as "true"/"false".
  Text that reads as a number ("0.5f", "0x1p-3", " 6.9E-4 ") is written the
  same way, as that number. Counts OpenRocket reads as whole numbers
  (fincount, instancecount, linecount) are written as digits when they are
  whole (3.0 is "3"; Java's integer reader would refuse "3.0" and keep its
  default). Other text is written as given (for example "auto 0.0335").
* The file format version is always FILE_VERSION, the one OpenRocket 24.12
  itself writes, whatever the design says: the version changes how
  OpenRocket reads a file (below 1.4 it ignores the motor digest).
* Every string is escaped for XML. Characters XML cannot hold at all (most
  control characters, lone surrogates) are replaced by the replacement
  character U+FFFD.
* Tags that exist only in the JSON design and that OpenRocket does not know
  ("motor_id") are not written.
* The motor: OpenRocket finds a motor in a file by its thrust-curve digest
  first, then by maker and designation (it ignores diameter and length). So
  every <motor> gets the digest of its motor id from the motor table, in the
  place where "motor_id" stood. A digest written by the design itself is
  never used: only the table decides which thrust curve flies.
* Every "simulations" node, wherever it sits, is left out. The Java helper
  sets launch conditions itself.

A tree that cannot be written (bad tag or attribute names, a value that is
a list or an object, a malformed node) raises `OrkWriteError`. The caller
treats that as a fault of the design, never of the machine.
"""
from __future__ import annotations

import functools
import json
import math
import re
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Optional, Union

from .limits import FIN_COUNT_WHOLE_TOLERANCE
from .tree import Node, java_number

__all__ = ["OrkWriteError", "design_to_ork", "flight_config_id", "motor_table_entries", "MotorSource"]

# Tags present in the JSON designs that OpenRocket's file format does not know.
JSON_ONLY_TAGS = frozenset({"motor_id"})
# Subtrees never written: launch conditions belong to the reward, not the design.
DROPPED_TAGS = frozenset({"simulations"})
# Elements whose text OpenRocket keeps as words and never reads as a number, so
# a part named "Infinity" is allowed. Every other value that reads as NaN or
# infinity is refused (see _scalar).
FREE_TEXT_TAGS = frozenset({"name", "comment", "designer", "revision", "material", "manufacturer",
                            "designation", "digest", "motor_id", "type", "finish", "shape", "deployevent",
                            "ignitionevent", "crosssection", "position", "axialoffset_method",
                            "preset", "partno", "description"})
# Element texts OpenRocket reads as words (names and choices), so a number
# written there is kept as written. Every other element's text that reads as a
# number is written in its canonical form.
WORD_TAGS = FREE_TEXT_TAGS - {"position"}
# Attributes OpenRocket reads as numbers; every other attribute (configid,
# version, method, type ...) is written as given.
NUMBER_ATTRS = frozenset({"density", "shearModulus", "x", "y"})
# Settings OpenRocket reads with Java's integer reader (DocumentConfig's
# IntSetter in OpenRocket 24.12).
INT_TAGS = frozenset({"fincount", "instancecount", "linecount"})
# The file format version OpenRocket 24.12 writes (OpenRocketSaver's
# calculateNecessaryFileVersion returns 110, written "1.10").
FILE_VERSION = "1.10"

# A conservative XML name: ASCII letter or "_" first, then letters, digits,
# "_", "-" or ".". No ":" (OpenRocket's parser is namespace-aware).
_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_.\-]*\Z")
# Characters XML 1.0 cannot carry, not even as character references:
# C0 controls other than tab, newline and carriage return, surrogates
# (only lone ones can reach here), and the two non-characters FFFE and FFFF.
_ILLEGAL = re.compile("[" + "\x00-\x08\x0b\x0c\x0e-\x1f"
                      + chr(0xD800) + "-" + chr(0xDFFF) + chr(0xFFFE) + chr(0xFFFF) + "]")
_REPLACEMENT = chr(0xFFFD)
_TEXT_ESC = {"&": "&amp;", "<": "&lt;", ">": "&gt;", "\r": "&#13;"}
_ATTR_ESC = {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;",
             "\t": "&#9;", "\n": "&#10;", "\r": "&#13;"}
_TEXT_RE = re.compile("[&<>\r]")
_ATTR_RE = re.compile("[&<>\"\t\n\r]")

MotorInfo = Mapping[str, Any]
MotorSource = Union[Mapping[str, MotorInfo], Callable[[str], Optional[MotorInfo]]]

_TABLE_PATH = Path(__file__).resolve().parent / "data" / "motor_table.json"


class OrkWriteError(ValueError):
    """The design tree cannot be written as an OpenRocket file.

    This is a fault of the design (for example a tag that is not a valid XML
    name), never of the machine. The message says what is wrong.
    """


@functools.lru_cache(maxsize=1)
def motor_table_entries() -> Mapping[str, MotorInfo]:
    """The packaged motor table (data/motor_table.json) as plain entries
    {motor id: {...}}, read on first use. Scoring uses motors.MotorTable
    (scoring.default_motor_table); this plain form is what the file writer needs."""
    with open(_TABLE_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def _resolver(motors: Optional[MotorSource]) -> Callable[[str], Optional[MotorInfo]]:
    """Turn a motor table or a lookup function into a lookup function.

    A table is searched by exact motor id first, then ignoring letter case.
    """
    if motors is None:
        motors = motor_table_entries()
    if callable(motors) and not isinstance(motors, Mapping):
        return motors
    table = motors
    lowered: dict[str, str] = {}

    def look(motor_id: str) -> Optional[MotorInfo]:
        if motor_id in table:
            return table[motor_id]
        if not lowered:
            for key in table:
                lowered.setdefault(str(key).lower(), key)
        key = lowered.get(motor_id.lower())
        return table[key] if key is not None else None

    return look


# ----------------------------------------------------------------- values

def _clean(s: str) -> str:
    return _ILLEGAL.sub(_REPLACEMENT, s)


def _not_finite_word(text: str) -> Optional[str]:
    """The first whitespace-separated word of `text` that reads as NaN or infinity, else None.

    Java's number reader (which OpenRocket uses) accepts "NaN", "Infinity" and
    numbers too large for a double such as "1e999"; OpenRocket then either
    skips the value and keeps a default or flies with it. Python's float()
    accepts the same spellings in any letter case, plus "inf".
    """
    for word in text.split():
        try:
            number = float(word)
        except (ValueError, OverflowError):
            continue
        if not math.isfinite(number):
            return word
    return None


def _number_text(value: Any, whole: bool) -> Optional[str]:
    """The canonical text of a finite number (a JSON number, or text that
    tree.java_number reads as one), or None when `value` is not a finite
    number. With `whole`, a value within FIN_COUNT_WHOLE_TOLERANCE of a whole
    number is written as that whole number's digits."""
    if isinstance(value, bool):
        return None
    if isinstance(value, str):
        if len(value) > 4000:   # longer than any real number; _scalar refuses or keeps it
            return None
        number = java_number(value)
        if number is None or not math.isfinite(number):
            return None
        text = value.strip()
        if text.lstrip("+-").isdigit() and text.isascii():
            return str(int(text))
        value = number
    if isinstance(value, int):
        return None   # written as digits by _scalar
    if not isinstance(value, float) or not math.isfinite(value):
        return None
    if whole and abs(value - round(value)) <= FIN_COUNT_WHOLE_TOLERANCE:
        return str(int(round(value)))
    return repr(value)


def _scalar(value: Any, where: str, free_text: bool = False) -> str:
    """One JSON scalar as the text OpenRocket should read.

    A number that is not finite (NaN, infinity, or an integer too large for a
    double) raises OrkWriteError, and so does text that reads as such a number
    ("NaN", "Infinity", "auto 1e999"): OpenRocket would quietly fly a different
    rocket instead. Text in a free-text element (`free_text`, for example a
    part's name) is never read as a number and is not checked.
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        try:
            text = str(value)
        except ValueError:  # more digits than Python will print
            raise OrkWriteError(f"{where}: the number is far too long") from None
        try:
            float(value)
        except OverflowError:
            raise OrkWriteError(f"{where}: the number {text[:20]}... is too large to be a real size") from None
        return text
    if isinstance(value, float):
        if not math.isfinite(value):
            raise OrkWriteError(f"{where}: the value {value!r} is not a finite number")
        return repr(value)
    if isinstance(value, str):
        bad = None if free_text else _not_finite_word(value)
        if bad is not None:
            raise OrkWriteError(f"{where}: {_clean(bad[:40])!r} is not a finite number")
        return _clean(value)
    raise OrkWriteError(f"{where}: a value must be text, a number or true/false, "
                        f"not {type(value).__name__}")


def _text(value: Any, where: str, tag: str = "") -> str:
    s = _number_text(value, tag in INT_TAGS) if tag not in WORD_TAGS else None
    if s is None:
        s = _scalar(value, where, free_text=tag in FREE_TEXT_TAGS)
    return _TEXT_RE.sub(lambda m: _TEXT_ESC[m.group()], s)


def _attr(value: Any, where: str, name: str = "") -> str:
    s = _number_text(value, False) if name in NUMBER_ATTRS else None
    if s is None:
        s = _scalar(value, where)
    return _ATTR_RE.sub(lambda m: _ATTR_ESC[m.group()], s)


def _name(name: Any, what: str) -> str:
    if not isinstance(name, str) or not _NAME.match(name):
        shown = _clean(repr(name)[:40])
        raise OrkWriteError(f"{what} {shown} is not a name an OpenRocket file can hold")
    return name


# ----------------------------------------------------------------- tree

def _split(node: Any) -> tuple[str, dict]:
    if not isinstance(node, dict) or len(node) != 1:
        raise OrkWriteError("every node must be an object with exactly one tag")
    (tag, body), = node.items()
    if body is None:
        body = {}
    if not isinstance(body, dict):
        raise OrkWriteError(f"<{_clean(str(tag)[:40])}> must hold an object with attrs, value or children")
    return tag, body


def _children(tag: str, body: dict) -> list:
    kids = body.get("children")
    if kids is None:
        return []
    if not isinstance(kids, list):
        raise OrkWriteError(f"<{tag}> children must be a list")
    return kids


def _motor_children(kids: list, look: Callable[[str], Optional[MotorInfo]]) -> list:
    """The children of a <motor> as OpenRocket should see them: motor_id
    replaced by the table's digest, any digest from the design dropped, and
    maker and designation filled in from the table when missing."""
    present = set()
    motor_id = None
    for k in kids:
        t, b = _split(k)
        present.add(t)
        if t == "motor_id" and motor_id is None and isinstance(b.get("value"), str):
            motor_id = b["value"].strip()
    info = look(motor_id) if motor_id else None
    digest = info.get("digest") if info else None
    out: list = []
    for k in kids:
        t, _ = _split(k)
        if t == "digest":
            continue
        if t == "motor_id":
            if digest:
                out.append({"digest": {"value": str(digest)}})
                digest = None  # one digest only
            continue
        out.append(k)
    if info:
        for field in ("manufacturer", "designation"):
            if field not in present and isinstance(info.get(field), str):
                out.append({field: {"value": info[field]}})
    return out


def _lines(root: Node, look: Callable[[str], Optional[MotorInfo]],
           keep: Callable[[str], bool]) -> Iterator[str]:
    """XML lines for `root` and everything below it, without recursion."""
    # Stack items: ("open", node, depth) or ("close", tag, depth).
    stack: list[tuple[str, Any, int]] = [("open", root, 0)]
    while stack:
        kind, item, depth = stack.pop()
        pad = "  " * depth
        if kind == "close":
            yield f"{pad}</{item}>"
            continue
        tag, body = _split(item)
        _name(tag, "tag")
        attrs = body.get("attrs") or {}
        if not isinstance(attrs, dict):
            raise OrkWriteError(f"<{tag}> attrs must be an object")
        parts = [tag]
        for key, val in attrs.items():
            _name(key, f"attribute of <{tag}>")
            parts.append(f'{key}="{_attr(val, f"<{tag} {key}>", key)}"')
        head = " ".join(parts)
        value = body.get("value")
        text = "" if value is None else _text(value, f"<{tag}>", tag)
        kids = _children(tag, body)
        if tag == "motor":
            kids = _motor_children(kids, look)
        kids = [k for k in kids if keep(_split(k)[0])]
        if not kids:
            yield f"{pad}<{head}>{text}</{tag}>" if text else f"{pad}<{head}/>"
            continue
        yield f"{pad}<{head}>{text}"
        stack.append(("close", tag, depth))
        for k in reversed(kids):
            stack.append(("open", k, depth + 1))


def _keep(tag: str) -> bool:
    return tag not in JSON_ONLY_TAGS and tag not in DROPPED_TAGS


def _element_xml(node: Node, motors: Optional[MotorSource] = None,
                 keep: Callable[[str], bool] = _keep, depth: int = 0) -> str:
    """One subtree as XML lines (internal; also used by the parity checks)."""
    look = _resolver(motors)
    pad = "  " * depth
    return "\n".join(pad + line for line in _lines(node, look, keep))


def flight_config_id(root: Node) -> Optional[str]:
    """The flight configuration id the design declares, to pass to the helper.

    The configid of the rocket's <motorconfiguration> marked default="true",
    else of its first <motorconfiguration>, else None. Many designs declare
    their configuration without marking it default; OpenRocket then selects a
    new empty configuration on load and flies the rocket with no motor, so the
    caller must name this id in the run request (sim.Simulator.run config_id).
    The id is passed exactly as written: OpenRocket turns a non-UUID id such as
    "cfg0" into the same internal id when it reads the file and the request.
    """
    found = []
    try:
        tag, body = _split(root)
        rocket = next((k for k in _children(tag, body) if isinstance(k, dict) and "rocket" in k), None)
        rtag, rbody = _split(rocket) if rocket is not None else ("rocket", {})
        for kid in _children(rtag, rbody):
            if isinstance(kid, dict) and isinstance(kid.get("motorconfiguration"), dict):
                attrs = kid["motorconfiguration"].get("attrs") or {}
                if isinstance(attrs, dict) and isinstance(attrs.get("configid"), str) and attrs["configid"]:
                    found.append((str(attrs.get("default")).lower() == "true", attrs["configid"]))
    except OrkWriteError:
        return None
    for is_default, cid in found:
        if is_default:
            return cid
    return found[0][1] if found else None


def design_to_ork(root: Node, motors: Optional[MotorSource] = None) -> str:
    """Write a design tree as the text of an OpenRocket .ork file.

    `root` is the design tree with root tag "openrocket". `motors` is the motor
    table ({motor_id: {"digest", "manufacturer", "designation", ...}}) or a
    function that returns that entry for a motor id (or None); by default the
    packaged data/motor_table.json is used. The tree itself is not changed.
    Raises OrkWriteError when the tree cannot be written.
    """
    tag, body = _split(root)
    if tag != "openrocket":
        raise OrkWriteError(f"the root tag must be 'openrocket', not {_clean(str(tag)[:40])!r}")
    if not any(_split(k)[0] == "rocket" for k in _children(tag, body)):
        raise OrkWriteError("the design has no <rocket>")
    attrs = body.get("attrs") or {}
    if not isinstance(attrs, dict):
        raise OrkWriteError("<openrocket> attrs must be an object")
    attrs = dict(attrs)
    attrs["version"] = FILE_VERSION
    fixed = {tag: dict(body, attrs=attrs)}
    xml = _element_xml(fixed, motors)
    return "<?xml version='1.0' encoding='utf-8'?>\n" + xml + "\n"
