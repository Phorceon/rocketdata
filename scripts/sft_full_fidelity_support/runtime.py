"""OpenRocket JVM snapshots for loaded component and simulation state."""

from __future__ import annotations

import math
from typing import Any

import jpype

GETTERS = [
    "getName",
    "getLength",
    "getOuterRadius",
    "getInnerRadius",
    "getThickness",
    "getForeRadius",
    "getAftRadius",
    "isForeRadiusAutomatic",
    "isAftRadiusAutomatic",
    "getShapeType",
    "getShapeParameter",
    "getAftShoulderLength",
    "getAftShoulderRadius",
    "getAftShoulderThickness",
    "isAftShoulderCapped",
    "isFilled",
    "getMaterial",
    "getFinish",
    "getAxialMethod",
    "getAxialOffset",
    "getPosition",
    "getComponentMass",
    "getComponentCG",
    "isMassOverridden",
    "isCGOverridden",
    "getOverrideMass",
    "getOverrideCGX",
    "getMass",
    "getRadius",
    "getRadialPosition",
    "getRadialDirection",
    "isRadiusAutomatic",
    "isOuterRadiusAutomatic",
    "isInnerRadiusAutomatic",
    "getInstanceCount",
    "getAngleMethod",
    "getAngleOffset",
    "getInstanceSeparation",
    "getFinPoints",
    "getFinCount",
    "getCrossSection",
    "getCantAngle",
    "getTabHeight",
    "getTabLength",
    "getTabOffset",
    "getFilletRadius",
    "getFilletMaterial",
    "getDiameter",
    "getCD",
    "isCDAutomatic",
    "getLineCount",
    "getLineLength",
    "isLineLengthAutomatic",
    "getLineMaterial",
    "getComponentPreset",
    "isMotorMount",
    "getMotorOverhang",
    "getClusterConfiguration",
]

OPTION_GETTERS = [
    "getLaunchRodLength",
    "getLaunchRodAngle",
    "getLaunchRodDirection",
    "getLaunchIntoWind",
    "getLaunchAltitude",
    "getLaunchLatitude",
    "getLaunchLongitude",
    "getLaunchTemperature",
    "getLaunchPressure",
    "isISAAtmosphere",
    "getWindSpeedAverage",
    "getWindSpeedDeviation",
    "getWindTurbulenceIntensity",
    "getWindDirection",
    "getWindModelType",
    "getGeodeticComputation",
    "getTimeStep",
    "getMaxSimulationTime",
    "getMaximumStepAngle",
    "getRandomSeed",
    "getSimulationEngine",
    "getCalculator",
]


def java_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if hasattr(value, "getDensity") and hasattr(value, "getName"):
        return {
            "name": str(value.getName()),
            "density": float(value.getDensity()),
            "type": str(value.getType()),
        }
    if hasattr(value, "x") and hasattr(value, "y"):
        out = {"x": float(value.x), "y": float(value.y)}
        if hasattr(value, "z"):
            out["z"] = float(value.z)
        if hasattr(value, "weight"):
            out["weight"] = float(value.weight)
        return out
    try:
        if value.getClass().isArray():
            return [java_value(x) for x in value]
    except AttributeError:
        pass
    if hasattr(value, "name"):
        try:
            return str(value.name())
        except Exception:
            pass
    return str(value)


def snapshot(obj: Any, methods: list[str] | None = None) -> dict[str, Any]:
    methods = methods or GETTERS
    result: dict[str, Any] = {}
    for key in methods:
        if not hasattr(obj, key):
            continue
        try:
            result[key] = java_value(getattr(obj, key)())
        except Exception as error:
            result[key] = {"error": str(error)}
    return result


def walk_components(rocket: Any) -> list[dict[str, Any]]:
    nodes: list[Any] = []

    def recurse(component: Any) -> None:
        for child in component.getChildren():
            nodes.append(child)
            recurse(child)

    recurse(rocket)
    rows: list[dict[str, Any]] = []
    for index, component in enumerate(nodes):
        rows.append(
            {
                "index": index,
                "openrocket_class": str(component.getClass().getSimpleName()),
                "name": str(component.getName()),
                "loaded": snapshot(component),
            }
        )
    return rows


def snapshot_simulation_options(sim: Any) -> dict[str, Any]:
    return snapshot(sim.getOptions(), OPTION_GETTERS)


def motor_config_for_fcid(component: Any, fcid_str: str) -> dict[str, Any] | None:
    if not hasattr(component, "isMotorMount") or not component.isMotorMount():
        return None
    Fcid = jpype.JClass("info.openrocket.core.rocketcomponent.FlightConfigurationId")
    fcid = Fcid(fcid_str)
    try:
        motor_config = component.getMotorConfig(fcid)
    except Exception:
        return None
    out = snapshot(
        motor_config,
        [
            "getEjectionDelay",
            "getIgnitionEvent",
            "getIgnitionDelay",
            "getMotorCount",
            "getX",
            "getPosition",
        ],
    )
    try:
        motor = motor_config.getMotor()
        out["motor"] = {
            "designation": str(motor.getDesignation()),
            "manufacturer": str(motor.getManufacturer().getDisplayName()),
            "digest": str(motor.getDigest()),
            "diameter_m": float(motor.getDiameter()),
            "length_m": float(motor.getLength()),
        }
    except Exception as error:
        out["motor_error"] = str(error)
    return out


def deployment_config_for_fcid(component: Any, fcid_str: str) -> dict[str, Any] | None:
    if not hasattr(component, "getDeploymentConfigurations"):
        return None
    Fcid = jpype.JClass("info.openrocket.core.rocketcomponent.FlightConfigurationId")
    fcid = Fcid(fcid_str)
    try:
        deployment = component.getDeploymentConfigurations().get(fcid)
    except Exception:
        return None
    if deployment is None:
        return None
    return snapshot(deployment, ["getDeployEvent", "getDeployDelay", "getDeployAltitude"])
