"""One shared helper for the tests: pull the design tree out of an answer.

This is a deliberately loose stand-in for parse.py. It does none of stage 1's
checks (tag names, depth, size), so tests of the later stages can also feed
them designs that stage 1 would reject.
"""
from __future__ import annotations

import json
from typing import Any, Optional


def design_of(text: Any, root_only: bool = False) -> Optional[dict]:
    """The JSON object between the first <design> and the next </design>, or
    None when there is no such block, the JSON does not parse, or it is not an
    object with an "openrocket" key.

    root_only=True keeps only the "openrocket" key, as parse.py does (it
    ignores a second top-level key such as "simulations").
    """
    if not isinstance(text, str):
        return None
    s = text.find("<design>")
    e = text.find("</design>", s) if s >= 0 else -1
    if s < 0 or e < 0:
        return None
    try:
        d = json.loads(text[s + len("<design>"):e])
    except ValueError:
        return None
    if not isinstance(d, dict) or "openrocket" not in d:
        return None
    return {"openrocket": d["openrocket"]} if root_only else d
