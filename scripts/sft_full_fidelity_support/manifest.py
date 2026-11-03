"""Build field_manifest with JSON Pointers covering every design leaf."""

from __future__ import annotations

import math
from typing import Any

from .json_pointer import get_at_pointer, iter_design_pointers, pointer

CLASS_SCHEMA = "schema_metadata"
CLASS_ENGINEERING = "engineering_input"
CLASS_IDENTITY = "identity"
CLASS_DISPLAY = "display"
CLASS_ARCHIVE = "archive"
CLASS_AUDIT = "audit_runtime"
CLASS_RUNTIME_DERIVED = "runtime_derived"

# XML element text/attribute keys -> unit (file format uses degrees for angles below).
_XML_TAG_UNITS: dict[str, str] = {
    "length": "m",
    "thickness": "m",
    "radius": "m",
    "outerradius": "m",
    "innerradius": "m",
    "foreradius": "m",
    "aftradius": "m",
    "diameter": "m",
    "mass": "kg",
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
    "cant": "deg",
    "clusterscale": "dimensionless",
    "clusterrotation": "deg",
    "radialdirection": "deg",
    "radialposition": "m",
    "x": "m",
    "y": "m",
    "z": "m",
    "randomseed": "dimensionless",
    "overhang": "m",
    "position": "m",
    "axialoffset": "m",
    "radiusoffset": "m",
    "rootchord": "m",
    "tipchord": "m",
    "sweeplength": "m",
    "height": "m",
    "aftshoulderlength": "m",
    "aftshoulderradius": "m",
    "aftshoulderthickness": "m",
    "foreshoulderlength": "m",
    "foreshoulderradius": "m",
    "foreshoulderthickness": "m",
    "overridemass": "kg",
    "overridecg": "m",
    "overridecd": "dimensionless",
    "cd": "dimensionless",
    "angleoffset": "deg",
    "rotation": "deg",
    "cantangle": "deg",
    "winddirection": "rad",
    "tabheight": "m",
    "tablength": "m",
    "linelength": "m",
    "ignitiondelay": "s",
    "separationdelay": "s",
    "fillet": "m",
}

_XML_TAG_PURPOSE: dict[str, str] = {
    "length": "Component axial extent",
    "thickness": "Wall, ring, or fin thickness",
    "material": "Bulk/surface/line material specification",
    "position": "Axial placement method and offset",
    "motor": "Motor assignment for flight configuration",
    "configid": "Flight configuration identity",
    "finpoints": "Freeform fin outline control points",
    "point": "Fin outline vertex in body coordinates",
    "deployevent": "Recovery deployment trigger",
    "preset": "Catalog component preset reference",
    "mass": "Override or component mass",
    "override": "Mass or CG override flag/value",
    "density": "Material surface/bulk density",
    "rootchord": "Fin chord at the body attachment; sets planform area and aerodynamic forces",
    "tipchord": "Fin chord at the outer edge; sets planform area and aerodynamic forces",
    "sweeplength": "Fin sweep; affects the longitudinal center of pressure",
    "height": "Fin span or component transverse extent",
    "axialoffset": "Axial position relative to the specified reference; affects geometry and mass lever arms",
    "overridemass": "Explicit mass override used for loaded mass and acceleration",
    "overridecg": "Explicit longitudinal CG override used for stability",
    "overridecd": "Explicit aerodynamic drag coefficient override",
    "cd": "Recovery-device drag coefficient used with deployed area",
    "linelength": "Suspension-line length used in recovery-device mass",
    "linecount": "Number of suspension lines used in recovery-device mass",
    "fincount": "Number of aerodynamic fin instances",
    "finish": "Surface finish roughness used in skin-friction drag",
    "cant": "Fin cant angle relative to the rocket axis",
    "rotation": "Component angular orientation about the rocket axis",
    "overhang": "Motor protrusion relative to the mount end; affects its axial position",
}

_RUNTIME_GETTER_UNITS: dict[str, str] = {
    "getLength": "m",
    "getOuterRadius": "m",
    "getInnerRadius": "m",
    "getThickness": "m",
    "getForeRadius": "m",
    "getAftRadius": "m",
    "getAftShoulderLength": "m",
    "getAftShoulderRadius": "m",
    "getAftShoulderThickness": "m",
    "getAxialOffset": "m",
    "getRadialPosition": "m",
    "getRadialDirection": "rad",
    "getCantAngle": "rad",
    "getTabHeight": "m",
    "getTabLength": "m",
    "getTabOffset": "m",
    "getFilletRadius": "m",
    "getDiameter": "m",
    "getLineLength": "m",
    "getMotorOverhang": "m",
    "getOverrideMass": "kg",
    "getOverrideCGX": "m",
    "getComponentMass": "kg",
    "getMass": "kg",
    "getComponentCG": "m",
    "getFinPoints": "m",
    "getDeployAltitude": "m",
    "getDeployDelay": "s",
    "getEjectionDelay": "s",
    "getIgnitionDelay": "s",
    "getLaunchRodLength": "m",
    "getLaunchRodAngle": "rad",
    "getLaunchRodDirection": "rad",
    "getLaunchAltitude": "m",
    "getLaunchLatitude": "deg",
    "getLaunchLongitude": "deg",
    "getLaunchTemperature": "K",
    "getLaunchPressure": "Pa",
    "getWindSpeedAverage": "m/s",
    "getWindSpeedDeviation": "m/s",
    "getWindTurbulenceIntensity": "dimensionless",
    "getWindDirection": "rad",
    "getAngleOffset": "rad",
    "getInstanceSeparation": "m",
    "getTimeStep": "s",
    "getMaxSimulationTime": "s",
    "getMaximumStepAngle": "rad",
    "getRandomSeed": "dimensionless",
    "digest": "text",
    "diameter_m": "m",
    "length_m": "m",
    "density": "kg/m³ or kg/m² (material type dependent)",
}


def _terminal_value(value: Any) -> Any:
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        return value
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    raise TypeError(f"manifest leaf must be terminal JSON value, got {type(value)}")


def _classify_pointer(ptr: str) -> str:
    if ptr.startswith("/schema_version") or ptr.startswith("/openrocket_version"):
        return CLASS_SCHEMA
    if ptr.startswith("/creator"):
        return CLASS_DISPLAY
    if ptr.startswith("/reconstruction_contract"):
        return CLASS_SCHEMA
    if ptr.startswith("/parameter_tree"):
        return CLASS_ENGINEERING
    if ptr.startswith("/ork_container"):
        return CLASS_SCHEMA
    if ptr.startswith("/bundle_entries"):
        return CLASS_ARCHIVE
    if ptr.startswith("/selected_simulation"):
        return CLASS_ENGINEERING
    if ptr.startswith("/simulation_options_snapshot"):
        return CLASS_AUDIT
    if ptr.startswith("/component_index"):
        return CLASS_AUDIT
    return CLASS_IDENTITY


def _infer_unit(ptr: str, value: Any, tag_hint: str | None) -> str:
    leaf = ptr.rsplit("/", 1)[-1]
    key = leaf.replace("~1", "/").replace("~0", "~")
    if isinstance(value, bool):
        return "boolean"
    if value in ("true", "false"):
        return "boolean"
    if key == "weight" and "/component_index/" in ptr:
        return "kg"
    if key in _RUNTIME_GETTER_UNITS:
        return _RUNTIME_GETTER_UNITS[key]
    if key.startswith("get") and key in _RUNTIME_GETTER_UNITS:
        return _RUNTIME_GETTER_UNITS[key]
    lowered = key.lower()
    if lowered in _XML_TAG_UNITS:
        return _XML_TAG_UNITS[lowered]
    if tag_hint and tag_hint.lower() in _XML_TAG_UNITS:
        return _XML_TAG_UNITS[tag_hint.lower()]
    if key in ("x", "y", "z") or ptr.endswith("/attrs/x") or ptr.endswith("/attrs/y"):
        if "finpoint" in ptr.lower() or "point" in ptr.lower() or tag_hint == "point":
            return "m"
    if key in ("type", "name", "manufacturer", "designation", "digest", "partno", "simulator", "calculator"):
        return "text"
    if key in ("encoding", "sha256", "data"):
        return "text"
    if isinstance(value, str):
        return "text"
    if isinstance(value, int):
        return "dimensionless"
    if isinstance(value, float):
        return "dimensionless"
    return "dimensionless"


def _infer_purpose(ptr: str, classification: str, tag_hint: str | None) -> str:
    leaf = ptr.rsplit("/", 1)[-1]
    key = leaf.replace("~1", "/").replace("~0", "~")
    if classification == CLASS_SCHEMA:
        return "Design schema / reconstruction contract metadata"
    if classification == CLASS_ARCHIVE:
        if key == "sha256":
            return "Attachment content integrity digest"
        if key == "data":
            return "Bundled non-rocket.ork archive bytes (base64)"
        return "ORK bundle attachment metadata"
    if classification == CLASS_AUDIT:
        if "getOverrideMass" in ptr or "isMassOverridden" in ptr:
            return "Loaded mass override state (audit; compare roundtrip)"
        if "getOverrideCGX" in ptr or "isCGOverridden" in ptr:
            return "Loaded CG override state (audit; compare roundtrip)"
        if "getComponentMass" in ptr or "getMass" in ptr:
            return "Loaded aggregate mass (audit; compare roundtrip)"
        if "getComponentCG" in ptr:
            return "Loaded component CG (audit; compare roundtrip)"
        if "getFinPoints" in ptr:
            return "Loaded freeform fin vertex (runtime; compare to XML finpoints)"
        if "motor_configuration" in ptr:
            return "Motor mount configuration for selected flight configuration (audit)"
        if "deployment_configuration" in ptr:
            return "Recovery deployment configuration for selected flight configuration (audit)"
        if ptr.startswith("/simulation_options_snapshot"):
            return "Loaded simulation options for selected simulation (audit; must match XML conditions)"
        return "Runtime loader observation; not authoritative for rebuild"
    if classification == CLASS_RUNTIME_DERIVED:
        return "OpenRocket saver materialization of effective parameters (authoritative for rebuild)"
    if classification == CLASS_DISPLAY:
        return "Document creator string (display metadata)"
    if key.lower() in _XML_TAG_PURPOSE:
        return _XML_TAG_PURPOSE[key.lower()]
    if tag_hint and tag_hint.lower() in _XML_TAG_PURPOSE:
        return _XML_TAG_PURPOSE[tag_hint.lower()]
    if key == "tag":
        return "OpenRocket XML element tag name"
    if ptr.endswith("/attrs") or "/attrs/" in ptr:
        return f"XML attribute on <{tag_hint or 'element'}>"
    if ptr.endswith("/text"):
        return f"XML text content on <{tag_hint or 'element'}>"
    return f"Engineering input at {ptr}"


def _source_xml_path(ptr: str, xml_index: dict[str, str]) -> str | None:
    return xml_index.get(ptr)


def _basis(
    ptr: str,
    classification: str,
    *,
    source_file: str,
    source_xml_path: str | None,
    jar_sha256: str | None,
) -> str:
    if classification == CLASS_ENGINEERING and source_xml_path:
        return f"{source_file} explicit XML {source_xml_path}"
    if classification == CLASS_ENGINEERING and ptr.startswith("/parameter_tree"):
        return f"{source_file} explicit XML (see source_xml_path)"
    if classification == CLASS_RUNTIME_DERIVED:
        return f"materialized via GeneralRocketSaver on pinned JAR sha256={jar_sha256}"
    if classification == CLASS_AUDIT:
        return f"runtime OpenRocket loader on pinned JAR sha256={jar_sha256}"
    if classification == CLASS_ARCHIVE:
        return f"{source_file} ZIP attachment"
    if classification == CLASS_SCHEMA:
        return "design schema contract"
    return source_file


def build_xml_pointer_index(root_key: str, parameter_tree: dict[str, Any]) -> dict[str, str]:
    """Map design JSON Pointers under /{root_key} to rocket.ork XML paths."""
    index: dict[str, str] = {}

    def walk(node: dict[str, Any], json_parts: list[str], xml_path: str) -> None:
        tag = node["tag"]
        index[pointer(*json_parts, "tag")] = f"{xml_path} (element)"
        for attr in (node.get("attrs") or {}):
            index[pointer(*json_parts, "attrs", attr)] = f"{xml_path}/@{attr}"
        if node.get("text") is not None:
            index[pointer(*json_parts, "text")] = f"{xml_path}/text()"
        children = node.get("children") or []
        counts: dict[str, int] = {}
        for idx, child in enumerate(children):
            ct = child["tag"]
            counts[ct] = counts.get(ct, 0) + 1
            walk(child, json_parts + ["children", str(idx)], f"{xml_path}/{ct}[{counts[ct]}]")

    walk(parameter_tree, [root_key], "/" + parameter_tree["tag"])
    return index


def build_field_manifest(
    design: dict[str, Any],
    *,
    source_file: str,
    jar_sha256: str | None,
) -> list[dict[str, Any]]:
    xml_index = build_xml_pointer_index("parameter_tree", design["parameter_tree"])

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for ptr in sorted(iter_design_pointers(design)):
        value = get_at_pointer(design, ptr)
        if isinstance(value, (dict, list)):
            continue
        terminal = _terminal_value(value)
        classification = _classify_pointer(ptr)
        tag_hint = None
        xml_node = None
        if ptr.startswith("/parameter_tree/"):
            try:
                parent_ptr = (ptr.rsplit("/attrs/", 1)[0] if "/attrs/" in ptr
                              else ptr.rsplit("/", 1)[0])
                parent = get_at_pointer(design, parent_ptr)
                if isinstance(parent, dict) and "tag" in parent:
                    xml_node = parent
                    tag_hint = parent.get("tag")
            except (KeyError, ValueError):
                pass
        row = {
            "path": ptr,
            "value": terminal,
            "unit": _infer_unit(ptr, terminal, tag_hint),
            "purpose": _infer_purpose(ptr, classification, tag_hint),
            "basis": _basis(
                ptr,
                classification,
                source_file=source_file,
                source_xml_path=_source_xml_path(ptr, xml_index),
                jar_sha256=jar_sha256,
            ),
            "classification": classification,
        }
        if tag_hint in ("name", "comment", "designer") and ptr.endswith("/text"):
            row["classification"] = CLASS_DISPLAY
            row["purpose"] = "Source display/documentation text; does not set geometry or propulsion"
        if tag_hint == "point" and ptr.endswith(("/attrs/x", "/attrs/y")):
            row["unit"] = "m"
            row["purpose"] = "Freeform fin outline vertex; sets planform geometry and aerodynamic forces"
        if ptr.endswith("/density"):
            if xml_node is not None:
                material_type = (xml_node.get("attrs") or {}).get("type", "")
            else:
                parent = get_at_pointer(design, ptr.rsplit("/", 1)[0])
                material_type = parent.get("type", "") if isinstance(parent, dict) else ""
            density_units = {"bulk": "kg/m³", "surface": "kg/m²", "line": "kg/m"}
            row["unit"] = density_units.get(str(material_type).lower(), "material-type dependent")
            row["purpose"] = "Material mass per volume, area, or length used to calculate component mass"
        sx = _source_xml_path(ptr, xml_index)
        if sx:
            row["source_xml_path"] = sx
        if ptr in seen:
            raise ValueError(f"duplicate manifest path {ptr}")
        seen.add(ptr)
        rows.append(row)
    return rows


def manifest_covers_design(design: dict[str, Any], manifest: list[dict[str, Any]]) -> list[str]:
    expected = {
        p
        for p in iter_design_pointers(design)
        if not isinstance(get_at_pointer(design, p), (dict, list))
    }
    got = {row["path"] for row in manifest}
    errors = []
    if len(got) != len(manifest):
        errors.append("manifest contains duplicate pointers")
    for missing in sorted(expected - got):
        errors.append(f"manifest missing pointer {missing}")
    for extra in sorted(got - expected):
        errors.append(f"manifest extra pointer {extra}")
    for row in manifest:
        val = row.get("value")
        if isinstance(val, (dict, list)):
            errors.append(f"manifest non-terminal value at {row['path']}")
        if isinstance(val, float) and not math.isfinite(val):
            errors.append(f"manifest non-finite float at {row['path']}")
        if row["path"] in expected and get_at_pointer(design, row["path"]) != val:
            errors.append(f"manifest value differs from design at {row['path']}")
    return errors
