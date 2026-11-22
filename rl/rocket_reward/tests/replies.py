"""Recorded simulator replies for tests that must run without Java.

The two files in tests/data are real replies from the simulator helper (see
java/PROTOCOL.md) for two sound reference rockets, each flown three times:

  reply_single_stage.json  one stage, one section with a parachute, some mass overrides
  reply_two_stage.json     a sustainer with a parachute and a booster with no recovery device

Tests take a fresh copy and change the numbers they care about.
"""
from __future__ import annotations

import copy
import json
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"


@lru_cache(maxsize=None)
def _read_reply(name: str) -> dict:
    with open(DATA / f"reply_{name}.json", encoding="utf-8") as fh:
        return json.load(fh)


def load_reply(name: str = "single_stage") -> dict:
    """A fresh, editable copy of a recorded reply ("single_stage" or "two_stage")."""
    return copy.deepcopy(_read_reply(name))


def each_flight(reply: dict, **fields) -> dict:
    """Set the same fields on all three flights and return the reply."""
    for flight in reply["flights"]:
        flight.update(fields)
    return reply


def each_branch(reply: dict, index: int = 0, **fields) -> dict:
    """Set fields on branch `index` (0 is the main section) of every flight."""
    for flight in reply["flights"]:
        flight["branches"][index].update(fields)
    return reply


def parts_of(reply: dict, part_type: str) -> list:
    """The parts of one OpenRocket type, for example "TrapezoidFinSet"."""
    return [c for c in reply["components"] if c["type"] == part_type]
