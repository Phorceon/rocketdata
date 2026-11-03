"""Structured OpenRocket XML tree (JSON-serializable, not an opaque XML string)."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections import Counter
from typing import Any, Iterator

# Engineering leaf tags and typical units (manifest hints).
_TAG_UNITS: dict[str, str] = {
    "length": "m",
    "thickness": "m",
    "radius": "m",
    "outerradius": "m",
    "innerradius": "m",
    "foreradius": "m",
    "aftradius": "m",
    "diameter": "m",
    "mass": "kg",
    "density": "kg/m³ or kg/m² (material type dependent)",
    "delay": "s",
    "timestep": "s",
    "launchrodlength": "m",
    "launchrodangle": "deg",
    "launchroddirection": "deg",
    "windaverage": "m/s",
    "windturbulence": "dimensionless",
    "launchaltitude": "m",
    "launchlatitude": "deg",
    "launchlongitude": "deg",
    "deployaltitude": "m",
    "deploydelay": "s",
    "fincount": "dimensionless",
    "linecount": "dimensionless",
    "shapeparameter": "dimensionless",
    "cantangle": "rad",
    "clusterscale": "dimensionless",
    "clusterrotation": "rad",
    "radialdirection": "rad",
    "randomseed": "dimensionless",
}

_TAG_PURPOSE: dict[str, str] = {
    "length": "Component axial extent",
    "thickness": "Wall or fin thickness",
    "radius": "Outer or reference radius",
    "outerradius": "Outer radius",
    "innerradius": "Inner radius",
    "material": "Bulk/surface/line material specification",
    "position": "Axial placement method and offset",
    "motor": "Motor assignment for flight configuration",
    "configid": "Flight configuration / motor config identity",
    "finpoints": "Freeform fin outline control points",
    "deployevent": "Recovery deployment trigger",
    "preset": "Catalog component preset reference",
    "motormount": "Motor mount cluster and ignition settings",
    "conditions": "Simulation launch and environment inputs",
    "simulator": "Numerical integrator selection",
    "calculator": "Aerodynamic calculator selection",
}


def element_to_node(element: ET.Element) -> dict[str, Any]:
    children = list(element)
    if children:
        # Ignore pure formatting whitespace between child elements.
        text = None
    else:
        text = element.text
    return {
        "tag": element.tag,
        "attrs": dict(element.attrib) if element.attrib else {},
        "text": text,
        "children": [element_to_node(child) for child in children],
    }


def node_to_element(node: dict[str, Any]) -> ET.Element:
    element = ET.Element(node["tag"], node.get("attrs") or {})
    text = node.get("text")
    if text is not None:
        element.text = str(text)
    for child in node.get("children") or []:
        element.append(node_to_element(child))
    return element


def parse_openrocket_xml(data: bytes) -> dict[str, Any]:
    root = ET.fromstring(data)
    return element_to_node(root)


def serialize_openrocket_xml(tree: dict[str, Any]) -> bytes:
    root = node_to_element(tree)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _path_join(parts: list[str]) -> str:
    return ".".join(parts)


def iter_manifest_leaves(
    node: dict[str, Any],
    *,
    parts: list[str] | None = None,
    source_file: str = "rocket.ork",
) -> Iterator[dict[str, Any]]:
    """Yield field_manifest rows for explicit XML inputs."""
    if parts is None:
        parts = ["parameter_tree"]
    tag = node["tag"]
    node_path = _path_join(parts + [tag])
    for attr, value in (node.get("attrs") or {}).items():
        path = f"{node_path}@{attr}"
        yield _manifest_row(path, value, tag, attr, source_file, kind="attribute")
    text = node.get("text")
    if text is not None:
        path = f"{node_path}#text"
        yield _manifest_row(path, text, tag, None, source_file, kind="text")
    counters: Counter[str] = Counter()
    for child in node.get("children") or []:
        ct = child["tag"]
        idx = counters[ct]
        counters[ct] += 1
        child_parts = parts + [f"{tag}.{ct}[{idx}]"]
        yield from iter_manifest_leaves(child, parts=child_parts, source_file=source_file)


def _manifest_row(
    path: str,
    value: Any,
    tag: str,
    attr: str | None,
    source_file: str,
    *,
    kind: str,
) -> dict[str, Any]:
    key = attr or tag
    unit = _TAG_UNITS.get(str(key).lower(), "text" if isinstance(value, str) else "dimensionless")
    if value in ("true", "false", True, False):
        unit = "boolean"
    purpose = _TAG_PURPOSE.get(str(key).lower(), f"OpenRocket XML {kind} on <{tag}>")
    if tag in ("motorconfiguration", "stage", "nosecone", "bodytube") and kind == "attribute":
        purpose = f"Structural/metadata attribute on <{tag}>"
    basis = f"{source_file} XML path {path}"
    row: dict[str, Any] = {
        "path": path,
        "value": _json_leaf(value),
        "unit": unit,
        "purpose": purpose,
        "basis": basis,
    }
    return row


def _json_leaf(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def strip_simulation_flightdata(tree: dict[str, Any]) -> dict[str, Any]:
    """Remove cached flight results; they are not engineering inputs."""

    def walk(node: dict[str, Any]) -> dict[str, Any]:
        children = []
        for child in node.get("children") or []:
            if child["tag"] == "flightdata":
                continue
            children.append(walk(child))
        out = dict(node)
        out["children"] = children
        return out

    return walk(tree)


def find_simulation_nodes(tree: dict[str, Any]) -> list[dict[str, Any]]:
    sims: list[dict[str, Any]] = []
    for child in tree.get("children") or []:
        if child["tag"] == "simulations":
            sims.extend(child.get("children") or [])
    return sims


def find_simulation_by_name(tree: dict[str, Any], name: str) -> tuple[int, dict[str, Any]]:
    sims = find_simulation_nodes(tree)
    for index, sim in enumerate(sims):
        for child in sim.get("children") or []:
            if child["tag"] == "name" and child.get("text") == name:
                return index, sim
    available = []
    for sim in sims:
        for child in sim.get("children") or []:
            if child["tag"] == "name":
                available.append(child.get("text"))
    raise KeyError(f"simulation {name!r} not found; available: {available}")


def simulation_config_id(sim_node: dict[str, Any]) -> str | None:
    for child in sim_node.get("children") or []:
        if child["tag"] != "conditions":
            continue
        for cond in child.get("children") or []:
            if cond["tag"] == "configid":
                return cond.get("text")
    return None


def simulation_field(sim_node: dict[str, Any], tag: str) -> str | None:
    for child in sim_node.get("children") or []:
        if child["tag"] == tag:
            return child.get("text")
    return None


def normalize_path(path: str) -> str:
    return re.sub(r"\[\d+\]", "", path)
