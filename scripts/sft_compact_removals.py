"""Approved leaf removals for the Stage-2 compact SFT rows (pure, flight-free).

Stage 2 must turn the Stage-1 compact designs into JSON a language model can
actually generate.  Three kinds of leaves are removed, each with a named,
purely-structural function that transforms the compact dict BEFORE
``sft_compact_design.from_compact`` rebuilds a full design:

* ``strip_digests``         - motor ``<digest>`` elements and ``digest``
  attributes on ``<preset>`` blocks (content hashes; a model cannot emit them).
  Applied only for rows whose headless load check (``sft_compact_digest_check``)
  shows the digests are not required; rows that need them stay out of the
  main files.
* ``strip_motor_digests_only`` - only the motor ``<digest>`` elements (preset
  blocks and their digest attrs untouched); used to attribute B0-vs-B1 check
  failures to motor vs preset digests.
* ``strip_preset_blocks``   - whole ``<preset>`` catalog-reference blocks,
  removed when the same headless check shows identical resolved geometry and
  motors without them.
* ``strip_simulation_name`` - the ``<name>`` directly under the selected
  ``<simulation>`` (the simulation name; banned from message text by the
  Stage-2 linter).  The row's top-level ``sim`` metadata keeps the name for
  tooling.

Compact shape reminder: a node is ``{"attrs": {...}, "value": ..., "children":
[...]}`` and each child is a single-key wrapper ``{tag: payload}`` in document
order (top-level ``attachments`` entries are dict values, never list items).

Every function is purely structural: it deletes whole wrappers or attribute
entries and never edits, rounds or invents a value.  Each returns a deep copy
and is a no-op on trees without the targeted leaves.  NO simulation runs
anywhere; these are dict transformations.
"""

from __future__ import annotations

import copy
from typing import Any, Callable


def _transform(node: Any, fn: Callable[[str, Any], Any]) -> Any:
    """Apply fn(tag, payload) to every single-key wrapper below node (in place).

    A wrapper is a one-key dict that is an ITEM of a list (compact children
    lists).  When fn returns None the wrapper is dropped.  Dict/list values
    are descended recursively; scalars are never touched.
    """
    if isinstance(node, dict):
        for key, value in list(node.items()):
            if isinstance(value, list):
                new_list = []
                for item in value:
                    if isinstance(item, dict) and len(item) == 1:
                        (tag, payload), = item.items()
                        payload = _transform(payload, fn)
                        payload = fn(tag, payload)
                        if payload is not None:
                            new_list.append({tag: payload})
                    else:
                        new_list.append(item)
                node[key] = new_list
            elif isinstance(value, dict):
                _transform(value, fn)
    return node


def strip_digests(compact: dict) -> dict:
    """Remove motor <digest> elements and digest attrs on <preset> blocks."""
    out = copy.deepcopy(compact)

    def fn(tag: str, payload: Any) -> Any:
        if tag == "digest":
            return None  # <digest> elements only occur inside <motor> elements
        if tag == "preset" and isinstance(payload, dict):
            attrs = payload.get("attrs") or {}
            if "digest" in attrs:
                payload = copy.deepcopy(payload)
                payload["attrs"] = {k: v for k, v in attrs.items() if k != "digest"}
                if not payload["attrs"]:
                    payload.pop("attrs")
        return payload

    return _transform(out, fn)


def apply_approved_removals(compact: dict) -> dict:
    """The full Stage-2 removal state, in the canonical order:
    digests, preset blocks, cosmetic leaves, simulation name.

    This is the transformation whose loaded-state neutrality the headless
    check (``sft_compact_digest_check``) verifies per pair as variant B3.
    """
    return strip_simulation_name(
        strip_cosmetic(
            strip_preset_blocks(
                strip_digests(compact)
            )
        )
    )


def strip_motor_digests_only(compact: dict) -> dict:
    """Remove only motor <digest> elements; preset blocks keep their digests."""
    out = copy.deepcopy(compact)

    def fn(tag: str, payload: Any) -> Any:
        return None if tag == "digest" else payload

    return _transform(out, fn)


def strip_cosmetic(compact: dict) -> dict:
    """Remove cosmetic ``<color>``, ``<linestyle>`` and ``<designtype>`` leaves.

    Stage 1 left these in some rows (they sit directly under components or
    under ``<rocket>``, not under the removed ``<appearance>``).  They carry no
    physics input (display color, 2D line style, design-type label), and the
    headless load check verifies their removal changes no loaded geometry,
    material or motor.
    """
    out = copy.deepcopy(compact)
    cosmetic = {"color", "linestyle", "designtype"}

    def fn(tag: str, payload: Any) -> Any:
        return None if tag in cosmetic else payload

    return _transform(out, fn)


def strip_preset_blocks(compact: dict) -> dict:
    """Remove whole <preset> catalog-reference blocks."""
    out = copy.deepcopy(compact)

    def fn(tag: str, payload: Any) -> Any:
        return None if tag == "preset" else payload

    return _transform(out, fn)


def strip_simulation_name(compact: dict) -> dict:
    """Remove the <name> element directly under the selected <simulation>.

    Stage 1 kept exactly one <name> (under the selected simulation) as the
    sim-lookup key; Stage 2 bans simulation names from message text, so the
    element is dropped.  The row's top-level ``sim`` metadata still carries
    the name for tooling.
    """
    out = copy.deepcopy(compact)

    def fn(tag: str, payload: Any) -> Any:
        if tag == "simulation" and isinstance(payload, dict):
            kids = payload.get("children")
            if isinstance(kids, list):
                kept = [w for w in kids
                        if not (isinstance(w, dict) and len(w) == 1 and "name" in w)]
                if kept:
                    payload["children"] = kept
                else:
                    payload.pop("children", None)
        return payload

    return _transform(out, fn)
