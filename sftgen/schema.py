"""Design schema for the <design> block (contract sft-v2.0).

Every key carries its SI unit, every count is an integer, and every component
needed to fly the rocket is explicit, so a design can be built and simulated in
OpenRocket without guessing. Stages are listed top (sustainer) first; within a
stage, external components are listed nose to tail.
"""

from __future__ import annotations

from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

BULK_MATERIALS = (
    "ABS - 100% infill", "Acrylic", "Aluminum", "Balsa", "Basswood", "Birch", "Blue tube",
    "Brass", "Carbon fiber", "Cardboard", "Cork", "Delrin", "Fiberglass", "Kraft phenolic",
    "Maple", "Nylon", "PETG - 100% infill", "PLA - 100% infill", "PVC", "Paper (office)",
    "Pine", "Plywood (birch)", "Polycarbonate (Lexan)", "Polystyrene", "Quantum tubing",
    "Spruce", "Steel", "Titanium",
)
SURFACE_MATERIALS = (
    "Cellophane", "Crêpe paper", "Mylar", "Paper (office)", "Polyethylene (heavy)",
    "Polyethylene (thin)", "Ripstop nylon", "Silk",
)

BulkMaterial = Literal[BULK_MATERIALS]  # type: ignore[valid-type]
SurfaceMaterial = Literal[SURFACE_MATERIALS]  # type: ignore[valid-type]
NoseShape = Literal["conical", "ogive", "ellipsoid", "power", "parabolic", "haack"]
TransitionShape = Literal["conical", "ogive", "ellipsoid", "power", "parabolic", "haack"]

# Range limits double as a units check: a design written in millimetres fails here.
Diameter = Annotated[float, Field(ge=0.008, le=0.40)]
Length = Annotated[float, Field(ge=0.005, le=6.0)]
Wall = Annotated[float, Field(ge=0.0002, le=0.03)]
FinDim = Annotated[float, Field(ge=0.0, le=1.0)]
FinThickness = Annotated[float, Field(ge=0.0008, le=0.02)]
Offset = Annotated[float, Field(ge=-0.5, le=6.0)]
Mass = Annotated[float, Field(gt=0.0, le=50.0)]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Motor(_Strict):
    manufacturer: Optional[str] = None
    designation: str = Field(min_length=1, max_length=24)
    delay_s: Optional[Annotated[float, Field(ge=0.0, le=30.0)]] = None  # None = plugged / no motor ejection
    ignition_delay_s: Annotated[float, Field(ge=0.0, le=30.0)] = 0.0    # upper stages: wait after booster burnout


class MotorMount(_Strict):
    type: Literal["motor_mount"]
    outer_diameter_m: Diameter
    length_m: Length
    wall_thickness_m: Wall
    material: BulkMaterial
    motor: Motor
    cluster_count: Literal[1, 2, 3, 4] = 1
    overhang_m: Annotated[float, Field(ge=0.0, le=0.2)] = 0.0
    centering_ring_count: Annotated[StrictInt, Field(ge=0, le=4)] = 2
    centering_ring_material: BulkMaterial = "Plywood (birch)"


class TrapezoidalFins(_Strict):
    type: Literal["trapezoidal_fins"]
    count: Annotated[StrictInt, Field(ge=2, le=8)]
    root_chord_m: Annotated[float, Field(ge=0.01, le=1.0)]
    tip_chord_m: FinDim
    span_m: Annotated[float, Field(ge=0.005, le=1.0)]
    sweep_m: Annotated[float, Field(ge=-0.5, le=1.0)]
    thickness_m: FinThickness
    material: BulkMaterial
    offset_from_aft_m: Offset = 0.0  # >0 moves the fin root trailing edge forward of the tube's aft end


class EllipticalFins(_Strict):
    type: Literal["elliptical_fins"]
    count: Annotated[StrictInt, Field(ge=2, le=8)]
    root_chord_m: Annotated[float, Field(ge=0.01, le=1.0)]
    span_m: Annotated[float, Field(ge=0.005, le=1.0)]
    thickness_m: FinThickness
    material: BulkMaterial
    offset_from_aft_m: Offset = 0.0


class Parachute(_Strict):
    type: Literal["parachute"]
    diameter_m: Annotated[float, Field(ge=0.08, le=8.0)]
    cd: Annotated[float, Field(ge=0.3, le=2.5)] = 0.8
    deploy_event: Literal["apogee", "altitude", "ejection"]
    deploy_altitude_m: Optional[Annotated[float, Field(ge=10.0, le=5000.0)]] = None
    deploy_delay_s: Annotated[float, Field(ge=0.0, le=30.0)] = 0.0
    material: SurfaceMaterial = "Ripstop nylon"
    position_from_top_m: Offset = 0.0

    @model_validator(mode="after")
    def _altitude_event(self):
        if self.deploy_event == "altitude" and self.deploy_altitude_m is None:
            raise ValueError("parachute with deploy_event 'altitude' needs deploy_altitude_m")
        return self


class Streamer(_Strict):
    type: Literal["streamer"]
    strip_length_m: Annotated[float, Field(ge=0.1, le=10.0)]
    strip_width_m: Annotated[float, Field(ge=0.01, le=1.0)]
    deploy_event: Literal["apogee", "altitude", "ejection"]
    deploy_altitude_m: Optional[Annotated[float, Field(ge=10.0, le=5000.0)]] = None
    deploy_delay_s: Annotated[float, Field(ge=0.0, le=30.0)] = 0.0
    material: SurfaceMaterial = "Mylar"
    position_from_top_m: Offset = 0.0


class MassItem(_Strict):
    type: Literal["mass"]
    name: str = Field(min_length=1, max_length=40)
    mass_kg: Mass
    position_from_top_m: Offset = 0.0


TubeContent = Annotated[
    Union[MotorMount, TrapezoidalFins, EllipticalFins, Parachute, Streamer, MassItem],
    Field(discriminator="type"),
]


class NoseCone(_Strict):
    type: Literal["nosecone"]
    shape: NoseShape
    length_m: Length
    diameter_m: Diameter
    wall_thickness_m: Optional[Wall] = None  # None = solid
    material: BulkMaterial
    shoulder_length_m: Annotated[float, Field(ge=0.0, le=0.5)] = 0.0


class BodyTube(_Strict):
    type: Literal["bodytube"]
    name: Optional[str] = None
    length_m: Length
    outer_diameter_m: Diameter
    wall_thickness_m: Wall
    material: BulkMaterial
    contents: list[TubeContent] = Field(default_factory=list)

    @property
    def inner_diameter_m(self) -> float:
        return self.outer_diameter_m - 2 * self.wall_thickness_m


class Transition(_Strict):
    type: Literal["transition"]
    shape: TransitionShape
    length_m: Length
    fore_diameter_m: Diameter
    aft_diameter_m: Diameter
    wall_thickness_m: Optional[Wall] = None  # None = solid
    material: BulkMaterial


External = Annotated[Union[NoseCone, BodyTube, Transition], Field(discriminator="type")]


class Stage(_Strict):
    name: str = Field(min_length=1, max_length=40)
    components: list[External] = Field(min_length=1)
    separation_event: Optional[Literal["burnout", "ejection"]] = None
    separation_delay_s: Annotated[float, Field(ge=0.0, le=30.0)] = 0.0

    def tubes(self) -> list[BodyTube]:
        return [c for c in self.components if isinstance(c, BodyTube)]

    def contents(self, kind) -> list:
        return [x for t in self.tubes() for x in t.contents if isinstance(x, kind)]


DIAMETER_MATCH_TOL_M = 0.0005


class Design(_Strict):
    name: str = Field(min_length=1, max_length=60)
    stages: list[Stage] = Field(min_length=1, max_length=3)

    @model_validator(mode="after")
    def _structure(self):
        errs = []
        for si, st in enumerate(self.stages):
            noses = [c for c in st.components if isinstance(c, NoseCone)]
            if si == 0:
                if not isinstance(st.components[0], NoseCone):
                    errs.append("the top stage must start with a nosecone")
                if len(noses) > 1:
                    errs.append("only one nosecone is allowed")
            elif noses:
                errs.append(f"stage {st.name!r}: only the top stage can have a nosecone")
            if not st.tubes():
                errs.append(f"stage {st.name!r} has no bodytube")
            if si > 0 and st.separation_event is None:
                errs.append(f"stage {st.name!r} is below the top stage and needs a separation_event")
            if si == 0 and st.separation_event is not None:
                errs.append("the top stage cannot have a separation_event")
            if not st.contents(MotorMount):
                errs.append(f"stage {st.name!r} has no motor_mount")
            for t in st.tubes():
                if t.inner_diameter_m <= 0:
                    errs.append(f"stage {st.name!r}: bodytube wall is thicker than its radius")
                for mm in (x for x in t.contents if isinstance(x, MotorMount)):
                    if mm.cluster_count == 1 and mm.outer_diameter_m > t.inner_diameter_m + 1e-6:
                        errs.append(
                            f"stage {st.name!r}: motor_mount OD {mm.outer_diameter_m} m exceeds "
                            f"bodytube ID {t.inner_diameter_m:.4f} m"
                        )
                    if mm.length_m > t.length_m + 1e-6:
                        errs.append(f"stage {st.name!r}: motor_mount is longer than its bodytube")

        # Neighbouring external diameters must meet (nose base, tubes, transition ends).
        chain = [c for st in self.stages for c in st.components]
        for a, b in zip(chain, chain[1:]):
            aft = _aft_d(a)
            fore = _fore_d(b)
            if abs(aft - fore) > DIAMETER_MATCH_TOL_M:
                errs.append(
                    f"diameter step between {a.type} (aft {aft:.4f} m) and {b.type} "
                    f"(fore {fore:.4f} m); add a transition"
                )
        if errs:
            raise ValueError("; ".join(errs))
        return self

    def motors(self) -> list[tuple[int, MotorMount]]:
        return [(si, mm) for si, st in enumerate(self.stages) for mm in st.contents(MotorMount)]


def _aft_d(c) -> float:
    if isinstance(c, NoseCone):
        return c.diameter_m
    if isinstance(c, BodyTube):
        return c.outer_diameter_m
    return c.aft_diameter_m


def _fore_d(c) -> float:
    if isinstance(c, NoseCone):
        return 0.0
    if isinstance(c, BodyTube):
        return c.outer_diameter_m
    return c.fore_diameter_m


def parse_design(obj) -> Design:
    """Validate a design dict (or JSON string). Raises pydantic.ValidationError / ValueError."""
    if isinstance(obj, (str, bytes)):
        return Design.model_validate_json(obj)
    return Design.model_validate(obj)


def design_json_schema() -> dict:
    return Design.model_json_schema()
