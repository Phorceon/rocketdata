"""RFC 6901 JSON Pointer helpers for design manifests."""

from __future__ import annotations

from typing import Any, Iterator


def escape_segment(segment: str) -> str:
    return str(segment).replace("~", "~0").replace("/", "~1")


def pointer(*segments: str | int) -> str:
    if not segments:
        return ""
    return "/" + "/".join(escape_segment(str(s)) for s in segments)


def append_pointer(base: str, segment: str | int) -> str:
    seg = escape_segment(str(segment))
    if not base:
        return f"/{seg}"
    return f"{base}/{seg}"


def iter_design_pointers(value: Any, base: str = "") -> Iterator[str]:
    """Yield every JSON Pointer to a terminal leaf in a JSON value."""
    if isinstance(value, dict):
        if not value:
            return
        for key, child in value.items():
            seg = append_pointer(base, key)
            yield from iter_design_pointers(child, seg)
    elif isinstance(value, list):
        if not value:
            return
        for index, child in enumerate(value):
            seg = append_pointer(base, index)
            yield from iter_design_pointers(child, seg)
    else:
        yield base if base else "/"


def get_at_pointer(root: Any, ptr: str) -> Any:
    if ptr in ("", "/"):
        return root
    if not ptr.startswith("/"):
        raise ValueError(f"invalid JSON Pointer: {ptr!r}")
    cur = root
    for raw in ptr.lstrip("/").split("/"):
        key = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(cur, dict):
            cur = cur[key]
        elif isinstance(cur, list):
            cur = cur[int(key)]
        else:
            raise KeyError(ptr)
    return cur
