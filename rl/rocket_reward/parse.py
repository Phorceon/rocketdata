"""Stage 1 (format): find the design tree in the model's answer.

The answer holds a <design> ... </design> block whose text is JSON: an
OpenRocket document written as a tree. Every node is a dict with exactly one
key, the tag, whose value (the body) may hold only

    "attrs"     a dict of plain values (text, numbers, true/false, null)
    "value"     one plain value
    "children"  a list of nodes

and the root tag is "openrocket". Every tag must be a valid XML element name,
because it becomes one in the OpenRocket file. Nothing is repaired: a cut-off answer, a
broken block or a tree of the wrong shape fails here. See DESIGN.md, stage 1.
"""
from __future__ import annotations

import json
import json.decoder
import math
import re
import sys
from typing import Any, Optional

from .ladder import (FORMAT_CREDIT_BAD_JSON, FORMAT_CREDIT_BAD_TREE, FORMAT_CREDIT_NO_BLOCK,
                     FORMAT_MAX_DEPTH, FORMAT_MAX_JSON_BYTES, FORMAT_READ_CEILING_BYTES)
from .records import StageCheck
from .tree import BODY_KEYS, Node

# The credits and the depth and size caps of this stage live in ladder.py.
OPEN_TAG = "<design>"
CLOSE_TAG = "</design>"
ROOT_TAG = "openrocket"
_BODY_KEYS = frozenset(BODY_KEYS)
_FLOAT_MAX = sys.float_info.max
# A tag becomes an XML element name in the OpenRocket file, so it must be one:
# ASCII letters, digits, "_", "-" and "." only, starting with a letter or "_".
# Anything else (a space, "<", a colon, an accented letter) makes the tree invalid.
_TAG_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_.\-]*")
_PLAIN_VALUE = "(a text, a number, true, false or null)"


class _BadJSON(ValueError):
    """The JSON text uses something strict JSON does not allow."""


def _no_constants(token: str) -> Any:
    raise _BadJSON(f"the JSON uses {token}, which is not a number in JSON")


class _DuplicateKeys:
    """object_pairs_hook that builds dicts and remembers repeated keys.

    Python's json keeps only the last of two equal keys, which would silently
    drop a part. We note the repeat and fail the shape check instead.
    """

    def __init__(self) -> None:
        self.repeated: list[str] = []

    def __call__(self, pairs: list[tuple[str, Any]]) -> dict:
        out = dict(pairs)
        if len(out) != len(pairs) and len(self.repeated) < 5:
            seen: set[str] = set()
            for k, _ in pairs:
                if k in seen:
                    self.repeated.append(k)
                    break
                seen.add(k)
        return out


_WS = re.compile(r"[ \t\n\r]*")
_NUMBER = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][-+]?[0-9]+)?")
_OPEN_RUN = re.compile(r"(?:\[[ \t\n\r]*)+")      # "[[ [[" : many lists opened in a row
_CLOSE_RUN = re.compile(r"(?:[ \t\n\r]*\])+")     # "]] ]]" : many lists closed in a row


def json_syntax_ok(text: str) -> bool:
    """True when `text` is one JSON value by the same rules json.loads uses
    here (no NaN or Infinity), however deeply it nests.

    json.loads gives up on very deep nesting before it reaches the end of the
    text, so it cannot tell deep-but-valid JSON from text that never closes
    its brackets. This loop keeps its own stack instead of recursing, and
    swallows runs of "[" and "]" in one step, so even a few megabytes of
    brackets take well under a second.
    """
    scan = json.decoder.scanstring
    n = len(text)
    stack: list[str] = []
    i = _WS.match(text, 0).end()
    state = "value"            # what may come next: "value", "key" or "after" (a value just ended)
    just_opened = False        # the last thing read was "[" (so "]" may close an empty list)
    while True:
        if state == "value":
            i = _WS.match(text, i).end()
            if i >= n:
                return False
            ch = text[i]
            if ch == "]" and just_opened:
                stack.pop()
                i += 1
                state, just_opened = "after", False
                continue
            just_opened = False
            if ch == "[":
                m = _OPEN_RUN.match(text, i)
                stack.extend("[" * m.group().count("["))
                i = m.end()
                just_opened = True
                continue
            if ch == "{":
                i = _WS.match(text, i + 1).end()
                if i < n and text[i] == "}":
                    i += 1
                    state = "after"
                else:
                    stack.append("{")
                    state = "key"
                continue
            if ch == '"':
                try:
                    _, i = scan(text, i + 1, True)
                except ValueError:
                    return False
            elif text.startswith("true", i):
                i += 4
            elif text.startswith("false", i):
                i += 5
            elif text.startswith("null", i):
                i += 4
            else:
                m = _NUMBER.match(text, i)
                if not m:
                    return False
                i = m.end()
            state = "after"
        elif state == "key":
            if i >= n or text[i] != '"':
                return False
            try:
                _, i = scan(text, i + 1, True)
            except ValueError:
                return False
            i = _WS.match(text, i).end()
            if i >= n or text[i] != ":":
                return False
            i += 1
            state = "value"
        else:  # after a value
            i = _WS.match(text, i).end()
            if not stack:
                return i == n
            if i >= n:
                return False
            ch, top = text[i], stack[-1]
            if ch == ",":
                i = _WS.match(text, i + 1).end()
                state = "key" if top == "{" else "value"
            elif ch == "]" and top == "[":
                m = _CLOSE_RUN.match(text, i)
                k = m.group().count("]")
                if stack[-k:].count("[") == k:
                    del stack[-k:]
                    i = m.end()
                else:
                    stack.pop()
                    i += 1
            elif ch == "}" and top == "{":
                stack.pop()
                i += 1
            else:
                return False


def _fail(credit: float, reason: str, info: dict) -> tuple[StageCheck, None]:
    return StageCheck(stage="format", passed=False, credit=credit, reasons=[reason], info=info), None


def find_design_block(text: str) -> tuple[Optional[str], dict]:
    """Return the JSON text of the first complete <design>...</design> block.

    "First complete" means: the first closing tag that has an opening tag
    before it, paired with the nearest such opening tag. So a stray
    "<design>" mentioned in the thought does not swallow the real block.
    Returns (None, info) when there is no complete block.
    """
    info: dict[str, Any] = {"open_tags": text.count(OPEN_TAG), "close_tags": text.count(CLOSE_TAG)}
    start = 0
    while True:
        j = text.find(CLOSE_TAG, start)
        if j < 0:
            return None, info
        i = text.rfind(OPEN_TAG, start, j)
        if i >= 0:
            after = text[j + len(CLOSE_TAG):]
            info["chars_after_block"] = len(after.strip())
            return text[i + len(OPEN_TAG):j], info
        start = j + len(CLOSE_TAG)


def _is_scalar(x: Any) -> bool:
    """A plain JSON value whose number, if any, fits in a float.

    An integer with hundreds of digits parses in Python but cannot become a
    float, and later checks would crash on it, so it counts as not plain.
    """
    if isinstance(x, bool) or x is None or isinstance(x, str):
        return True
    if isinstance(x, float):
        return math.isfinite(x)
    if isinstance(x, int):
        return abs(x) <= _FLOAT_MAX
    return False


def _describe(x: Any) -> str:
    if (isinstance(x, float) and not math.isfinite(x)) or (
            isinstance(x, int) and not isinstance(x, bool) and abs(x) > _FLOAT_MAX):
        return "a number too large to store"
    return {dict: "an object", list: "a list"}.get(type(x), type(x).__name__)


def _short(path: str) -> str:
    """The last few tags of a path such as "openrocket > rocket > ...", so a
    reason stays readable on a deep tree."""
    parts = path.split(" > ")
    return path if len(parts) <= 4 else "... > " + " > ".join(parts[-4:])


def check_tree(root: Any) -> Optional[str]:
    """Check the node shape of the whole tree with a loop (no recursion).

    Returns None when the tree is fine, otherwise one plain sentence saying
    what is wrong and where.
    """
    stack: list[tuple[Any, int, str]] = [(root, 1, ROOT_TAG)]
    while stack:
        node, depth, where = stack.pop()
        if depth > FORMAT_MAX_DEPTH:
            return f"the tree is nested more than {FORMAT_MAX_DEPTH} levels deep (at {_short(where)})"
        if not isinstance(node, dict) or len(node) != 1:
            if isinstance(node, dict) and node:
                got = f"{len(node)} keys ({', '.join(repr(str(k)[:40]) for k in list(node)[:3])})"
            else:
                got = f"{len(node)} keys" if isinstance(node, dict) else _describe(node)
            return (f"a node inside {_short(where)} must be an object with exactly one tag, got {got}: "
                    "write every child as its own {\"tag\": {...}} object in the children list")
        (tag, body), = node.items()
        if not isinstance(tag, str) or not tag:
            return f"a node inside {_short(where)} has an empty or non-text tag"
        if not _TAG_NAME.fullmatch(tag):
            return (f"the tag {tag[:40]!r} inside {_short(where)} is not a valid XML element name "
                    "(letters, digits, '_', '-' and '.' only, starting with a letter or '_'), "
                    "so OpenRocket could never read it")
        here = f"{where} > {tag[:40]}" if depth > 1 else tag[:40]
        if not isinstance(body, dict):
            return f"<{tag[:40]}> must hold an object with attrs/value/children, got {_describe(body)}"
        extra = set(body) - _BODY_KEYS
        if extra:
            return (f"<{_short(here)}> has keys {sorted(str(k)[:40] for k in extra)[:3]}; "
                    f"only attrs, value and children are allowed")
        if "attrs" in body:
            attrs = body["attrs"]
            if not isinstance(attrs, dict):
                return f"the attrs of <{_short(here)}> must be an object, got {_describe(attrs)}"
            for k, v in attrs.items():
                if not _is_scalar(v):
                    return (f"attribute {str(k)[:40]!r} of <{_short(here)}> must be a plain value "
                            f"{_PLAIN_VALUE}, got {_describe(v)}")
        if "value" in body and not _is_scalar(body["value"]):
            return f"the value of <{_short(here)}> must be a plain value {_PLAIN_VALUE}, got {_describe(body['value'])}"
        if "children" in body:
            kids = body["children"]
            if not isinstance(kids, list):
                return f"the children of <{_short(here)}> must be a list, got {_describe(kids)}"
            for c in reversed(kids):
                stack.append((c, depth + 1, here))
    return None


def parse_answer(answer_text: str, truncated: bool = False) -> tuple[StageCheck, Optional[Node]]:
    """Stage 1: read the design tree out of the model's answer.

    Returns the stage check and, when it passes, the {"openrocket": ...} root
    node (None otherwise). Credit when it fails: 0 for a cut-off answer or no
    complete block, 0.5 when the JSON does not parse, 0.75 when the JSON is
    not a tree of the right shape, is deeper than FORMAT_MAX_DEPTH levels or larger
    than FORMAT_MAX_JSON_BYTES.
    """
    info: dict[str, Any] = {}
    if truncated:
        return _fail(FORMAT_CREDIT_NO_BLOCK, "the answer was cut off before it finished", info)
    if not isinstance(answer_text, str):
        return _fail(FORMAT_CREDIT_NO_BLOCK, f"the answer must be text, got {type(answer_text).__name__}", info)

    block, found = find_design_block(answer_text)
    info.update(found)
    if block is None:
        why = ("the <design> block is never closed with </design>" if found["open_tags"]
               else "the answer has no <design>...</design> block")
        return _fail(FORMAT_CREDIT_NO_BLOCK, why, info)

    size = len(block.encode("utf-8", errors="replace"))
    info["json_bytes"] = size
    if size > FORMAT_READ_CEILING_BYTES:
        return _fail(FORMAT_CREDIT_BAD_JSON, f"the design is {size / 1000:.0f} kB, far too large to read "
                                      f"(the limit is {FORMAT_MAX_JSON_BYTES / 1000:.0f} kB)", info)

    dupes = _DuplicateKeys()
    try:
        data = json.loads(block, parse_constant=_no_constants, object_pairs_hook=dupes)
    except RecursionError:
        # Too deep for the JSON reader. Deep JSON that is complete is a tree of
        # the wrong shape (0.75); text that never closes its brackets does not
        # parse at all (0.5), so opening many brackets cannot raise the score.
        if json_syntax_ok(block):
            return _fail(FORMAT_CREDIT_BAD_TREE, f"the design JSON is nested far more than {FORMAT_MAX_DEPTH} levels deep", info)
        return _fail(FORMAT_CREDIT_BAD_JSON, "the design JSON does not parse: it is nested far more than "
                                      f"{FORMAT_MAX_DEPTH} levels deep and its brackets are never closed properly", info)
    except ValueError as exc:  # includes json.JSONDecodeError and _BadJSON
        return _fail(FORMAT_CREDIT_BAD_JSON, f"the design JSON does not parse: {str(exc)[:120]}", info)

    if size > FORMAT_MAX_JSON_BYTES:
        return _fail(FORMAT_CREDIT_BAD_TREE, f"the design is {size / 1000:.0f} kB of JSON; "
                                      f"the limit is {FORMAT_MAX_JSON_BYTES / 1000:.0f} kB", info)
    if dupes.repeated:
        return _fail(FORMAT_CREDIT_BAD_TREE, f"the design JSON repeats the key {dupes.repeated[0][:40]!r} "
                                      f"in one object, so one of them would be lost", info)
    if not isinstance(data, dict) or ROOT_TAG not in data:
        got = f"keys {sorted(k[:40] for k in data)[:3]}" if isinstance(data, dict) else _describe(data)
        return _fail(FORMAT_CREDIT_BAD_TREE, f"the design must be an object with an \"{ROOT_TAG}\" root, got {got}", info)
    extra = sorted(k[:40] for k in data if k != ROOT_TAG)
    if extra:
        info["ignored_top_keys"] = extra[:10]

    root: Node = {ROOT_TAG: data[ROOT_TAG]}
    problem = check_tree(root)
    if problem is not None:
        return _fail(FORMAT_CREDIT_BAD_TREE, problem, info)
    return StageCheck(stage="format", passed=True, credit=1.0, info=info), root
