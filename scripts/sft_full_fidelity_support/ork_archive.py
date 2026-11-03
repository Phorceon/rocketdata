"""Read/write OpenRocket .ork containers (ZIP, gzip-compressed XML, plain XML)."""

from __future__ import annotations

import base64
import gzip
import hashlib
import io
import zipfile
from pathlib import Path
from typing import Any

from .xml_tree import parse_openrocket_xml, serialize_openrocket_xml, strip_simulation_flightdata

ENGINEERING_BUNDLE_PREFIXES = ("thrustcurves/",)
COSMETIC_BUNDLE_PREFIXES = ("decals/", "photos/", "preview/")


def detect_container_format(raw: bytes) -> str:
    if raw[:2] == b"PK":
        return "zip"
    if raw[:2] == b"\x1f\x8b":
        return "gzip_xml"
    if raw.removeprefix(b"\xef\xbb\xbf").lstrip().startswith(b"<"):
        return "plain_xml"
    raise ValueError(f"unrecognized .ork container (magic={raw[:4]!r})")


def _rocket_bytes_from_container(raw: bytes, fmt: str) -> tuple[bytes, dict[str, bytes]]:
    if fmt == "zip":
        entries: dict[str, bytes] = {}
        with zipfile.ZipFile(io.BytesIO(raw), "r") as archive:
            for name in archive.namelist():
                entries[name] = archive.read(name)
        if "rocket.ork" not in entries:
            raise ValueError("missing rocket.ork inside zip archive")
        return entries["rocket.ork"], entries
    if fmt == "gzip_xml":
        xml_bytes = gzip.decompress(raw)
        return xml_bytes, {"rocket.ork": xml_bytes}
    if fmt == "plain_xml":
        return raw, {"rocket.ork": raw}
    raise ValueError(f"unsupported container format {fmt!r}")


def partition_bundle_entries(entries: dict[str, bytes]) -> tuple[dict[str, bytes], list[str]]:
    """Split ZIP members into engineering rebuild inputs vs excluded cosmetic assets."""
    engineering: dict[str, bytes] = {}
    excluded: list[str] = []
    for name, data in entries.items():
        if name == "rocket.ork":
            continue
        if name.startswith(ENGINEERING_BUNDLE_PREFIXES):
            engineering[name] = data
        elif name.startswith(COSMETIC_BUNDLE_PREFIXES):
            excluded.append(name)
        else:
            # Unknown paths are kept for rebuild fidelity unless clearly cosmetic.
            engineering[name] = data
    return engineering, excluded


def read_ork_archive(path: Path) -> tuple[dict[str, Any], dict[str, bytes], dict[str, Any]]:
    """Return (parameter_tree, all_zip_entries, container_spec)."""
    raw = path.read_bytes()
    fmt = detect_container_format(raw)
    rocket_bytes, entries = _rocket_bytes_from_container(raw, fmt)
    tree = strip_simulation_flightdata(parse_openrocket_xml(rocket_bytes))
    container = {"format": fmt}
    return tree, entries, container


def bundle_entries_to_json(entries: dict[str, bytes]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, data in entries.items():
        if name == "rocket.ork":
            continue
        out[name] = {
            "encoding": "base64",
            "sha256": hashlib.sha256(data).hexdigest(),
            "data": base64.standard_b64encode(data).decode("ascii"),
        }
    return out


def bundle_entries_from_json(spec: dict[str, Any]) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    for name, meta in (spec or {}).items():
        if meta.get("encoding") != "base64":
            raise ValueError(f"unsupported bundle entry encoding for {name!r}")
        data = base64.b64decode(meta["data"], validate=True)
        if hashlib.sha256(data).hexdigest() != meta.get("sha256"):
            raise ValueError(f"bundle entry integrity mismatch for {name!r}")
        out[name] = data
    return out


def write_ork_archive(
    destination: Path,
    parameter_tree: dict[str, Any],
    *,
    container: dict[str, Any],
    bundle_entries: dict[str, bytes] | None = None,
) -> Path:
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    rocket_bytes = serialize_openrocket_xml(parameter_tree)
    fmt = container.get("format", "zip")
    bundle_entries = bundle_entries or {}
    if fmt == "zip":
        with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("rocket.ork", rocket_bytes)
            for name, data in sorted(bundle_entries.items()):
                archive.writestr(name, data)
    elif fmt == "plain_xml":
        destination.write_bytes(rocket_bytes)
    elif fmt == "gzip_xml":
        destination.write_bytes(gzip.compress(rocket_bytes))
    else:
        raise ValueError(f"unsupported ork_container.format {fmt!r}")
    return destination


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
