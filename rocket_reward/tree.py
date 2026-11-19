"""Helpers for reading and walking the design tree.

A design is an OpenRocket document written as JSON. Every node is a dict with
exactly one key, the tag, whose value is the node's body:

    {"bodytube": {"attrs": {...}, "value": ..., "children": [node, node, ...]}}

All three body keys are optional. `parse.py` checks this shape once, but the
tree comes from a language model and some callers (tests, tools, later
stages) hand trees over directly, so every helper here is safe on malformed
input: a body that is not a dict reads as empty, children that are not proper
nodes are skipped, and nothing recurses, so a very deep tree cannot overflow
the stack.

OpenRocket nests components like this: a component's child parts sit inside
its child node called "subcomponents". This is the only module that knows how
to walk that nesting; every stage uses it.
"""
from __future__ import annotations

import math
import re
from collections.abc import Sequence
from typing import Any, Iterator, Optional

Node = dict  # {tag: body}

BODY_KEYS = ("attrs", "value", "children")


# ---------------------------------------------------------------- building

def make_node(tag: str, value: Any = None, attrs: Optional[dict] = None,
              children: Optional[list] = None) -> Node:
    """Build a node. Only the pieces that are given are written."""
    body: dict[str, Any] = {}
    if attrs:
        body["attrs"] = dict(attrs)
    if value is not None:
        body["value"] = value
    if children is not None:
        body["children"] = list(children)
    return {tag: body}


def copy_tree(x: Any) -> Any:
    """An independent copy of JSON-like data (dicts, lists and plain values).

    Works with a loop instead of recursion, so a very deep tree from the model
    cannot overflow the stack the way copy.deepcopy would. Meant for JSON data:
    a dict or list that appears twice is copied twice, and the data must not
    contain itself.
    """
    def fresh(v: Any) -> Any:
        if isinstance(v, dict):
            return {}
        if isinstance(v, list):
            return []
        return v

    top = fresh(x)
    stack = [(x, top)] if isinstance(x, (dict, list)) else []
    while stack:
        src, dst = stack.pop()
        items = src.items() if isinstance(src, dict) else enumerate(src)
        for k, v in items:
            new = fresh(v)
            if isinstance(dst, dict):
                dst[k] = new
            else:
                dst.append(new)
            if isinstance(v, (dict, list)):
                stack.append((v, new))
    return top


# ---------------------------------------------------------------- one node

def is_node(x: Any) -> bool:
    """True for a proper tree node: a dict with exactly one text key (the tag)."""
    return isinstance(x, dict) and len(x) == 1 and isinstance(next(iter(x)), str)


def tag_of(node: Any) -> str:
    """The node's tag, for example "bodytube"; "" for anything that is not a node."""
    return next(iter(node)) if is_node(node) else ""


def body_of(node: Any) -> dict:
    """The node's body, or {} when it is not a dict (or `node` is not a node)."""
    if not is_node(node):
        return {}
    body = node[next(iter(node))]
    return body if isinstance(body, dict) else {}


def children_of(node: Any) -> list:
    """The node's children that are proper nodes; anything else is skipped."""
    kids = body_of(node).get("children")
    return [c for c in kids if is_node(c)] if isinstance(kids, list) else []


def child_list(node: Any) -> Optional[list]:
    """The node's own "children" list, unfiltered, for editing in place; None
    when the node has no children list."""
    kids = body_of(node).get("children")
    return kids if isinstance(kids, list) else None


def value_of(node: Any, default: Any = None) -> Any:
    """The node's "value", or `default` when it has none."""
    return body_of(node).get("value", default)


def attrs_of(node: Any) -> dict:
    """The node's attributes, or {} when it has none (or they are not a dict)."""
    attrs = body_of(node).get("attrs")
    return attrs if isinstance(attrs, dict) else {}


def attr_of(node: Any, name: str, default: Any = None) -> Any:
    """One attribute, or `default` when it is missing."""
    return attrs_of(node).get(name, default)


# ---------------------------------------------------------------- children by tag

def children_named(node: Any, tag: str) -> list:
    """Direct children with this tag, in document order."""
    return [c for c in children_of(node) if tag_of(c) == tag]


def child(node: Any, tag: str) -> Optional[Node]:
    """The FIRST direct child with this tag, or None. Used for holders such as
    "rocket" and "subcomponents"."""
    for c in children_of(node):
        if tag_of(c) == tag:
            return c
    return None


def last_child(node: Any, tag: str) -> Optional[Node]:
    """The LAST direct child with this tag, or None. When a design writes a
    setting twice, OpenRocket's loader keeps the last copy, so settings are
    read with this."""
    found = None
    for c in children_of(node):
        if tag_of(c) == tag:
            found = c
    return found


def child_value(node: Any, tag: str, default: Any = None) -> Any:
    """Value of the first direct child with this tag (`default` when missing)."""
    c = child(node, tag)
    return default if c is None else value_of(c, default)


def last_text(node: Any, tag: str) -> Optional[str]:
    """The value of the LAST child with this tag when it is text, else None."""
    c = last_child(node, tag)
    v = body_of(c).get("value") if c is not None else None
    return v if isinstance(v, str) else None


# ---------------------------------------------------------------- numbers

def number(x: Any) -> Optional[float]:
    """A JSON value read as a finite number the way OpenRocket reads it, or
    None when it is not one (a word, true/false, NaN, infinity, a list).

    This is read_number without the "broken" flag, for callers that only
    need the value. Every stage reads design numbers through read_number, so
    "0.5f" or "0x1p-3" counts as a number everywhere and "1_0" nowhere.
    """
    return read_number(x)[0]


def child_number(node: Any, tag: str) -> Optional[float]:
    """The first direct child with this tag, read as a number (None if it is
    missing or not a finite number)."""
    return number(child_value(node, tag))


# Number text as OpenRocket's reader (Java's Double.parseDouble) accepts it:
# surrounding spaces, a sign, "NaN", "Infinity", a decimal with an optional
# exponent and an optional f/d type letter ("0.5f"), or a hexadecimal number
# with a binary exponent ("0x1p-17"). Anything else is a word, not a number.
_JAVA_SPACE = "".join(chr(i) for i in range(33))
_JAVA_DECIMAL = re.compile(r"[+-]?(?:NaN|Infinity|(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][+-]?[0-9]+)?[fFdD]?)")
_JAVA_HEX = re.compile(r"[+-]?0[xX](?:[0-9a-fA-F]+\.?[0-9a-fA-F]*|\.[0-9a-fA-F]+)[pP][+-]?[0-9]+[fFdD]?")
_PYTHON_NUMBER_TEXT_MAX = 64   # longer text is not tried as a Python number (bounds the work)


def java_number(text: Any) -> Optional[float]:
    """The number OpenRocket would read from this text, or None when it would
    not read a number at all (or `text` is not text). May return NaN or
    infinity."""
    if not isinstance(text, str):
        return None
    t = text.strip(_JAVA_SPACE)
    if not t:
        return None
    if _JAVA_DECIMAL.fullmatch(t):
        if t[-1] in "fFdD":
            t = t[:-1]
        try:
            return float(t)
        except (ValueError, OverflowError):
            return None
    if _JAVA_HEX.fullmatch(t):
        if t[-1] in "fFdD":
            t = t[:-1]
        try:
            return float.fromhex(t)
        except OverflowError:
            return -math.inf if t.startswith("-") else math.inf
        except ValueError:
            return None
    return None


def _python_not_finite(text: str) -> bool:
    """True for short text Python reads as NaN or infinity ("inf", "nan")."""
    if len(text) > _PYTHON_NUMBER_TEXT_MAX:
        return False
    try:
        return not math.isfinite(float(text))
    except (ValueError, OverflowError):
        return False


def read_number(x: Any) -> tuple[Optional[float], bool]:
    """Read a JSON value as a number, the way OpenRocket will read it.

    Returns (value, broken). `value` is a finite float, or None when the value
    is not a number at all (a word such as "auto" or "filled"). `broken` is
    True when the value is meant as a number but is not a finite one: NaN,
    infinity, "1e999", or an integer too large to turn into a float.

    Text counts as a number exactly when OpenRocket's reader takes it as one,
    at any length: "0.00001f", "0x1p-17" and "  0.5  " are numbers, so a trick
    value cannot hide from the limits by being written oddly. For text such
    as "auto 0.025", only the last word is checked for being finite and the
    value counts as a word.
    """
    if isinstance(x, bool) or x is None:
        return None, False
    if isinstance(x, (int, float)):
        try:
            f = float(x)
        except OverflowError:
            return None, True
        return (f, False) if math.isfinite(f) else (None, True)
    if isinstance(x, str):
        t = x.strip(_JAVA_SPACE)
        if not t:
            return None, False
        f = java_number(t)
        if f is not None:
            return (f, False) if math.isfinite(f) else (None, True)
        if _python_not_finite(t):
            return None, True
        words = t.split()
        if len(words) > 1:
            last = java_number(words[-1])
            if (last is not None and not math.isfinite(last)) or _python_not_finite(words[-1]):
                return None, True
        return None, False
    return None, False


# ---------------------------------------------------------------- walking

class Ancestors(Sequence):
    """The nodes enclosing a node, from the top down, as `walk` and
    `walk_components` report them.

    It reads like a tuple (len, indexing, iteration, `+ (node,)`), but each
    step down the tree adds one link instead of copying the whole path, so a
    walk costs the same per node however deep the tree is. `ancestors[-1]`
    (the parent) is immediate; iterating costs the depth.
    """

    __slots__ = ("_up", "_node", "_size")

    def __init__(self, up: Optional["Ancestors"] = None, node: Any = None) -> None:
        self._up = up
        self._node = node
        self._size = 0 if up is None else up._size + 1

    def then(self, node: Any) -> "Ancestors":
        """These ancestors with `node` added at the bottom."""
        return Ancestors(self, node)

    def _items(self) -> list:
        out = []
        cur: Ancestors = self
        while cur._size:
            out.append(cur._node)
            cur = cur._up  # type: ignore[assignment]
        out.reverse()
        return out

    def __len__(self) -> int:
        return self._size

    def __bool__(self) -> bool:
        return self._size > 0

    def __iter__(self) -> Iterator[Any]:
        return iter(self._items())

    def __reversed__(self) -> Iterator[Any]:
        cur: Ancestors = self
        while cur._size:
            yield cur._node
            cur = cur._up  # type: ignore[assignment]

    def __getitem__(self, i: Any) -> Any:
        if isinstance(i, slice):
            return tuple(self._items()[i])
        n = self._size
        if i < 0:
            i += n
        if not 0 <= i < n:
            raise IndexError("ancestor index out of range")
        cur: Ancestors = self
        for _ in range(n - 1 - i):
            cur = cur._up  # type: ignore[assignment]
        return cur._node

    def __add__(self, other: Any) -> tuple:
        return tuple(self._items()) + tuple(other)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, (Ancestors, tuple)):
            return tuple(self) == tuple(other)
        return NotImplemented

    __hash__ = None  # type: ignore[assignment]

    def __repr__(self) -> str:
        return "Ancestors(" + " > ".join(tag_of(n) or "?" for n in self) + ")"


_NO_ANCESTORS = Ancestors()


def walk(node: Any) -> Iterator[tuple[Any, Ancestors]]:
    """Visit every node below and including `node`, parents before children,
    in document order.

    Yields (node, ancestors) where ancestors runs from the top down. Each node
    is yielded before its children are read, so a caller may edit a node's
    children list while walking and the walk follows the edited list.
    """
    stack: list[tuple[Any, Ancestors]] = [(node, _NO_ANCESTORS)]
    while stack:
        cur, parents = stack.pop()
        yield cur, parents
        below = parents.then(cur)
        for c in reversed(children_of(cur)):
            stack.append((c, below))


def walk_nodes(node: Any) -> Iterator[Any]:
    """Every node at or below `node`, parents before children, in document
    order, without the ancestors. Like `walk`, it reads a node's children only
    after yielding the node, so the caller may edit them on the way."""
    stack = [node]
    while stack:
        cur = stack.pop()
        yield cur
        stack.extend(reversed(children_of(cur)))


def find_all(node: Any, tag: str) -> list:
    """Every node with this tag anywhere below (or at) `node`, in document order."""
    return [n for n in walk_nodes(node) if tag_of(n) == tag]


# The nodes that name a material: {"material": {"attrs": {"type": "bulk",
# "density": 680.0}, "value": "Cardboard"}}. A parachute or streamer's cloth is
# its "material" (type surface); its shroud lines are "linematerial".
MATERIAL_TAGS = ("material", "filletmaterial", "linematerial")


def material_nodes(node: Any) -> list[tuple[str, Any, Any, Any]]:
    """(tag, type, name, written density) for every material node at or below
    `node`, in document order. The values are returned as written (any JSON
    value), so callers decide what a usable type, name or density is."""
    found = []
    for n in walk_nodes(node):
        tag = tag_of(n)
        if tag in MATERIAL_TAGS:
            attrs = attrs_of(n)
            found.append((tag, attrs.get("type"), value_of(n), attrs.get("density")))
    return found


# Which components OpenRocket lets each component hold (its "isCompatible"
# rules, checked against the 582 reference designs, which never break them).
# A part placed anywhere else is dropped when OpenRocket loads the file, so
# stage 2 does not count it. Recovery gear, mass parts, rings, lugs, rail
# buttons and fin sets hold nothing.
_INSIDE_PARTS = frozenset({"innertube", "tubecoupler", "centeringring", "bulkhead", "engineblock",
                           "masscomponent", "parachute", "streamer", "shockcord"})
_OUTSIDE_PARTS = frozenset({"trapezoidfinset", "ellipticalfinset", "freeformfinset", "tubefinset",
                            "launchlug", "railbutton"})
_SHELL_PARTS = frozenset({"nosecone", "bodytube", "transition"})
LEGAL_CHILDREN: dict[str, frozenset] = {
    "rocket": frozenset({"stage"}),
    "stage": _SHELL_PARTS,
    "podset": _SHELL_PARTS,
    "parallelstage": _SHELL_PARTS,
    "bodytube": _INSIDE_PARTS | _OUTSIDE_PARTS | {"podset", "parallelstage"},
    "nosecone": _INSIDE_PARTS | _OUTSIDE_PARTS | {"podset", "parallelstage"},
    "transition": _INSIDE_PARTS | _OUTSIDE_PARTS | {"podset", "parallelstage"},
    "innertube": _INSIDE_PARTS,
    "tubecoupler": _INSIDE_PARTS,
}


def is_legal_child(parent_tag: str, child_tag: str) -> bool:
    """True when OpenRocket accepts a `child_tag` part inside a `parent_tag` part."""
    return child_tag in LEGAL_CHILDREN.get(parent_tag, frozenset())


def subcomponents(component: Any) -> list:
    """The component nodes placed inside `component`: the children of EVERY
    "subcomponents" child, in order (OpenRocket adds the parts of each one).
    Empty when it has none."""
    found: list = []
    for holder in children_of(component):
        if tag_of(holder) == "subcomponents":
            found.extend(children_of(holder))
    return found


_SKIPPED_MAX = 1000   # walk_components records at most this many dropped parts


def walk_components(component: Any, legal_only: bool = False,
                    skipped: Optional[list] = None) -> Iterator[tuple[Node, Ancestors]]:
    """Every component nested inside `component` (not `component` itself),
    parents before children, with its enclosing components from the top down
    (starting with `component`).

    Only follows "subcomponents" (all of them, see `subcomponents`), so
    settings such as "material" or "finpoints" are not reported as
    components. With `legal_only`, a part OpenRocket would not accept in its
    parent is left out together with everything inside it, and (parent tag,
    part tag) is added to `skipped` when a list is given. A node reached
    twice (only possible in a tree built by hand) is visited once.
    """
    stack: list[tuple[Any, Ancestors]] = [(component, _NO_ANCESTORS)]
    seen: set[int] = set()
    while stack:
        cur, parents = stack.pop()
        if id(cur) in seen:
            continue
        seen.add(id(cur))
        if cur is not component:
            yield cur, parents
        below = parents.then(cur)
        here = tag_of(cur)
        for c in reversed(subcomponents(cur)):
            if legal_only and not is_legal_child(here, tag_of(c)):
                if skipped is not None and len(skipped) < _SKIPPED_MAX:
                    skipped.append((here, tag_of(c)))
                continue
            stack.append((c, below))


def iter_components(component: Any, legal_only: bool = False,
                    skipped: Optional[list] = None) -> Iterator[Node]:
    """The components of walk_components, without their ancestors."""
    for comp, _ in walk_components(component, legal_only, skipped):
        yield comp


# ---------------------------------------------------------------- the rocket

def rocket_of(root: Any) -> Optional[Node]:
    """The "rocket" node under the "openrocket" root, or None. A second
    top-level key next to "openrocket" (the model sometimes adds
    "simulations") is ignored."""
    if not isinstance(root, dict) or "openrocket" not in root:
        return None
    return child({"openrocket": root["openrocket"]}, "rocket")


def stages_of(root: Any) -> list[Node]:
    """The "stage" nodes inside the rocket's FIRST "subcomponents" holder,
    the only place OpenRocket accepts a stage."""
    rocket = rocket_of(root)
    holder = child(rocket, "subcomponents") if rocket is not None else None
    return children_named(holder, "stage") if holder is not None else []
