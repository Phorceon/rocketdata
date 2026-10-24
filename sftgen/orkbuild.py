"""Design JSON (sftgen.schema.Design) -> OpenRocket .ork XML.

The XML is loaded by OpenRocket through orhelper, so every number the tools
report comes from OpenRocket's own mass, aerodynamic and flight models. Motors
are resolved against the bundled motor database by `motors.resolve`, and the
chosen thrust curve's digest is written into the file so the same curve is
used every time.
"""

from __future__ import annotations

import itertools
import math
import re
import uuid
from xml.sax.saxutils import escape

from . import motors
from .contract import DEFAULT_SIM_CONDITIONS
from .schema import (
    BodyTube, Design, EllipticalFins, MassItem, MotorMount, NoseCone, Parachute, Stage,
    Streamer, TrapezoidalFins, Transition,
)

BULK_DENSITY = {
    "ABS - 100% infill": 1050.0, "Acrylic": 1190.0, "Aluminum": 2700.0, "Balsa": 170.0,
    "Basswood": 500.0, "Birch": 670.0, "Blue tube": 1300.0, "Brass": 8600.0,
    "Carbon fiber": 1780.0, "Cardboard": 680.0, "Cork": 240.0, "Delrin": 1420.0,
    "Fiberglass": 1850.0, "Kraft phenolic": 950.0, "Maple": 755.0, "Nylon": 1150.0,
    "PETG - 100% infill": 1250.0, "PLA - 100% infill": 1250.0, "PVC": 1390.0,
    "Paper (office)": 820.0, "Pine": 530.0, "Plywood (birch)": 630.0,
    "Polycarbonate (Lexan)": 1200.0, "Polystyrene": 1050.0, "Quantum tubing": 1050.0,
    "Spruce": 450.0, "Steel": 7850.0, "Titanium": 4500.0,
}
SURFACE_DENSITY = {
    "Cellophane": 0.018, "Crêpe paper": 0.025, "Mylar": 0.021, "Paper (office)": 0.08,
    "Polyethylene (heavy)": 0.04, "Polyethylene (thin)": 0.015, "Ripstop nylon": 0.067,
    "Silk": 0.06,
}
SHROUD_LINE = ("Braided nylon (2 mm, 1/16 in)", 0.001)

SHAPE_PARAMETER = {"ogive": 1.0, "power": 0.5, "haack": 0.0, "parabolic": 1.0}
CLUSTER_NAME = {1: "single", 2: "double", 3: "3-ring", 4: "4-ring"}

# Fixed configuration id so re-runs of the same design produce identical files.
CONFIG_ID = "00000000-0000-4000-8000-000000000001"


class BuildError(ValueError):
    pass


def _f(x: float) -> str:
    return repr(float(x))


def _bulk(name: str) -> str:
    return f'<material type="bulk" density="{_f(BULK_DENSITY[name])}">{escape(name)}</material>'


def _surface(name: str) -> str:
    return f'<material type="surface" density="{_f(SURFACE_DENSITY[name])}">{escape(name)}</material>'


def _nosecone(c: NoseCone) -> str:
    r = c.diameter_m / 2
    thick = "filled" if c.wall_thickness_m is None else _f(c.wall_thickness_m)
    sh_r = max(r - (c.wall_thickness_m or 0.0015) - 0.0005, r * 0.85)
    parts = [
        "<nosecone>", "<name>Nose cone</name>", "<finish>normal</finish>", _bulk(c.material),
        f"<length>{_f(c.length_m)}</length>", f"<thickness>{thick}</thickness>",
        f"<shape>{c.shape}</shape>",
    ]
    if c.shape in SHAPE_PARAMETER:
        parts.append(f"<shapeparameter>{_f(SHAPE_PARAMETER[c.shape])}</shapeparameter>")
    parts += [
        f"<aftradius>{_f(r)}</aftradius>",
        f"<aftshoulderradius>{_f(sh_r if c.shoulder_length_m > 0 else 0.0)}</aftshoulderradius>",
        f"<aftshoulderlength>{_f(c.shoulder_length_m)}</aftshoulderlength>",
        f"<aftshoulderthickness>{_f(c.wall_thickness_m or 0.0015)}</aftshoulderthickness>",
        "<aftshouldercapped>false</aftshouldercapped>", "<isflipped>false</isflipped>",
        "</nosecone>",
    ]
    return "".join(parts)


def _transition(c: Transition) -> str:
    thick = "filled" if c.wall_thickness_m is None else _f(c.wall_thickness_m)
    parts = [
        "<transition>", "<name>Transition</name>", "<finish>normal</finish>", _bulk(c.material),
        f"<length>{_f(c.length_m)}</length>", f"<thickness>{thick}</thickness>",
        f"<shape>{c.shape}</shape>",
    ]
    if c.shape in SHAPE_PARAMETER:
        parts.append(f"<shapeparameter>{_f(SHAPE_PARAMETER[c.shape])}</shapeparameter>")
    parts += [
        f"<foreradius>{_f(c.fore_diameter_m / 2)}</foreradius>",
        f"<aftradius>{_f(c.aft_diameter_m / 2)}</aftradius>",
        "<foreshoulderradius>0.0</foreshoulderradius><foreshoulderlength>0.0</foreshoulderlength>",
        "<foreshoulderthickness>0.0</foreshoulderthickness><foreshouldercapped>false</foreshouldercapped>",
        "<aftshoulderradius>0.0</aftshoulderradius><aftshoulderlength>0.0</aftshoulderlength>",
        "<aftshoulderthickness>0.0</aftshoulderthickness><aftshouldercapped>false</aftshouldercapped>",
        "</transition>",
    ]
    return "".join(parts)


def _motor_mount(mm: MotorMount, tube: BodyTube, from_bottom: int) -> str:
    m = motors.resolve(mm.motor.designation, mm.motor.manufacturer)
    if m["diameter_m"] > mm.outer_diameter_m - 2 * mm.wall_thickness_m + 1e-4:
        raise BuildError(
            f"motor {m['designation']} is {m['diameter_m'] * 1000:.0f} mm but the motor_mount "
            f"inner diameter is {(mm.outer_diameter_m - 2 * mm.wall_thickness_m) * 1000:.1f} mm"
        )
    if mm.cluster_count > 1:
        span = mm.outer_diameter_m * (2 if mm.cluster_count == 2 else 2.155 if mm.cluster_count == 3 else 2.414)
        if span > tube.inner_diameter_m + 1e-6:
            raise BuildError(
                f"a {mm.cluster_count}-motor cluster of {mm.outer_diameter_m * 1000:.1f} mm mounts "
                f"needs about {span * 1000:.0f} mm inside the tube; the tube ID is "
                f"{tube.inner_diameter_m * 1000:.1f} mm"
            )
    delay = "none" if mm.motor.delay_s is None else _f(mm.motor.delay_s)
    ignition = "automatic" if from_bottom == 0 else "burnout"
    ign_delay = 0.0 if from_bottom == 0 else mm.motor.ignition_delay_s
    mount = (
        "<innertube>"
        "<name>Motor mount</name>"
        '<axialoffset method="bottom">0.0</axialoffset><position type="bottom">0.0</position>'
        f"{_bulk(mm.material)}"
        f"<length>{_f(mm.length_m)}</length>"
        "<radialposition>0.0</radialposition><radialdirection>0.0</radialdirection>"
        f"<outerradius>{_f(mm.outer_diameter_m / 2)}</outerradius>"
        f"<thickness>{_f(mm.wall_thickness_m)}</thickness>"
        f"<clusterconfiguration>{CLUSTER_NAME[mm.cluster_count]}</clusterconfiguration>"
        "<clusterscale>1.0</clusterscale><clusterrotation>0.0</clusterrotation>"
        "<motormount>"
        f"<ignitionevent>{ignition}</ignitionevent><ignitiondelay>{_f(ign_delay)}</ignitiondelay>"
        f"<overhang>{_f(mm.overhang_m)}</overhang>"
        f'<motor configid="{CONFIG_ID}">'
        f"<type>{escape(m['or_type'])}</type>"
        f"<manufacturer>{escape(m['manufacturer'])}</manufacturer>"
        f"<digest>{m['digest']}</digest>"
        f"<designation>{escape(m['designation'])}</designation>"
        f"<diameter>{_f(m['diameter_m'])}</diameter><length>{_f(m['length_m'])}</length>"
        f"<delay>{delay}</delay>"
        "</motor>"
        f'<ignitionconfiguration configid="{CONFIG_ID}">'
        f"<ignitionevent>{ignition}</ignitionevent><ignitiondelay>{_f(ign_delay)}</ignitiondelay>"
        "</ignitionconfiguration>"
        "</motormount>"
        "</innertube>"
    )
    rings = []
    if mm.cluster_count == 1 and mm.centering_ring_count:
        ring_len = 0.003 if tube.outer_diameter_m < 0.05 else 0.006
        n = mm.centering_ring_count
        for i in range(n):
            frac = 0.0 if n == 1 else i / (n - 1)
            off = -(frac * (mm.length_m - ring_len))
            rings.append(
                "<centeringring><name>Centering ring</name><instancecount>1</instancecount>"
                "<instanceseparation>0.0</instanceseparation>"
                f'<axialoffset method="bottom">{_f(off)}</axialoffset><position type="bottom">{_f(off)}</position>'
                f"{_bulk(mm.centering_ring_material)}<length>{_f(ring_len)}</length>"
                "<radialposition>0.0</radialposition><radialdirection>0.0</radialdirection>"
                f"<outerradius>{_f(tube.inner_diameter_m / 2)}</outerradius>"
                f"<innerradius>{_f(mm.outer_diameter_m / 2)}</innerradius>"
                "</centeringring>"
            )
    return mount + "".join(rings)


def _fins(f) -> str:
    off = -f.offset_from_aft_m
    head = (
        f"<name>Fins</name><instancecount>{f.count}</instancecount><fincount>{f.count}</fincount>"
        '<radiusoffset method="surface">0.0</radiusoffset><angleoffset method="relative">0.0</angleoffset>'
        "<rotation>0.0</rotation>"
        f'<axialoffset method="bottom">{_f(off)}</axialoffset><position type="bottom">{_f(off)}</position>'
        f"<finish>normal</finish>{_bulk(f.material)}<thickness>{_f(f.thickness_m)}</thickness>"
        "<crosssection>rounded</crosssection><cant>0.0</cant><filletradius>0.0</filletradius>"
    )
    if isinstance(f, TrapezoidalFins):
        return (
            f"<trapezoidfinset>{head}<rootchord>{_f(f.root_chord_m)}</rootchord>"
            f"<tipchord>{_f(f.tip_chord_m)}</tipchord><sweeplength>{_f(f.sweep_m)}</sweeplength>"
            f"<height>{_f(f.span_m)}</height></trapezoidfinset>"
        )
    return (
        f"<ellipticalfinset>{head}<rootchord>{_f(f.root_chord_m)}</rootchord>"
        f"<height>{_f(f.span_m)}</height></ellipticalfinset>"
    )


def _deploy(x) -> str:
    alt = x.deploy_altitude_m if x.deploy_altitude_m is not None else 200.0
    return (
        f"<deployevent>{x.deploy_event}</deployevent><deployaltitude>{_f(alt)}</deployaltitude>"
        f"<deploydelay>{_f(x.deploy_delay_s)}</deploydelay>"
    )


def _parachute(p: Parachute, tube: BodyTube) -> str:
    packed_r = tube.inner_diameter_m / 2 * 0.9
    packed_len = min(max(p.diameter_m * 0.12, 0.03), max(tube.length_m * 0.5, 0.03))
    return (
        "<parachute><name>Parachute</name>"
        f'<axialoffset method="top">{_f(p.position_from_top_m)}</axialoffset>'
        f'<position type="top">{_f(p.position_from_top_m)}</position>'
        f"<packedlength>{_f(packed_len)}</packedlength><packedradius>{_f(packed_r)}</packedradius>"
        "<radialposition>0.0</radialposition><radialdirection>0.0</radialdirection>"
        f"<cd>{_f(p.cd)}</cd>{_surface(p.material)}{_deploy(p)}"
        f"<diameter>{_f(p.diameter_m)}</diameter><linecount>8</linecount>"
        f"<linelength>{_f(p.diameter_m)}</linelength>"
        f'<linematerial type="line" density="{_f(SHROUD_LINE[1])}">{escape(SHROUD_LINE[0])}</linematerial>'
        "</parachute>"
    )


def _streamer(s: Streamer, tube: BodyTube) -> str:
    packed_r = tube.inner_diameter_m / 2 * 0.9
    return (
        "<streamer><name>Streamer</name>"
        f'<axialoffset method="top">{_f(s.position_from_top_m)}</axialoffset>'
        f'<position type="top">{_f(s.position_from_top_m)}</position>'
        f"<packedlength>{_f(min(0.05, tube.length_m * 0.5))}</packedlength><packedradius>{_f(packed_r)}</packedradius>"
        "<radialposition>0.0</radialposition><radialdirection>0.0</radialdirection>"
        f"<cd>auto</cd>{_surface(s.material)}{_deploy(s)}"
        f"<striplength>{_f(s.strip_length_m)}</striplength><stripwidth>{_f(s.strip_width_m)}</stripwidth>"
        "</streamer>"
    )


def _mass(m: MassItem, tube: BodyTube) -> str:
    kind = "payload" if "payload" in m.name.lower() else "masscomponent"
    return (
        f"<masscomponent><name>{escape(m.name)}</name>"
        f'<axialoffset method="top">{_f(m.position_from_top_m)}</axialoffset>'
        f'<position type="top">{_f(m.position_from_top_m)}</position>'
        f"<packedlength>0.03</packedlength><packedradius>{_f(tube.inner_diameter_m / 2 * 0.9)}</packedradius>"
        "<radialposition>0.0</radialposition><radialdirection>0.0</radialdirection>"
        f"<mass>{_f(m.mass_kg)}</mass><masscomponenttype>{kind}</masscomponenttype>"
        "</masscomponent>"
    )


def _bodytube(t: BodyTube, from_bottom: int) -> str:
    inner = []
    for x in t.contents:
        if hasattr(x, "position_from_top_m") and x.position_from_top_m > t.length_m:
            raise BuildError(f"{x.type} position_from_top_m {x.position_from_top_m} is past the end of its {t.length_m} m bodytube")
        if isinstance(x, MotorMount):
            inner.append(_motor_mount(x, t, from_bottom))
        elif isinstance(x, (TrapezoidalFins, EllipticalFins)):
            inner.append(_fins(x))
        elif isinstance(x, Parachute):
            inner.append(_parachute(x, t))
        elif isinstance(x, Streamer):
            inner.append(_streamer(x, t))
        elif isinstance(x, MassItem):
            inner.append(_mass(x, t))
    name = escape(t.name or "Body tube")
    return (
        f"<bodytube><name>{name}</name><finish>normal</finish>{_bulk(t.material)}"
        f"<length>{_f(t.length_m)}</length><thickness>{_f(t.wall_thickness_m)}</thickness>"
        f"<radius>{_f(t.outer_diameter_m / 2)}</radius>"
        f"<subcomponents>{''.join(inner)}</subcomponents></bodytube>"
    )


def _stage(st: Stage, from_bottom: int) -> str:
    parts = [f"<stage><name>{escape(st.name)}</name>"]
    if st.separation_event is not None:
        parts.append(
            f"<separationevent>{st.separation_event}</separationevent>"
            f"<separationdelay>{_f(st.separation_delay_s)}</separationdelay>"
        )
    parts.append("<subcomponents>")
    for c in st.components:
        if isinstance(c, NoseCone):
            parts.append(_nosecone(c))
        elif isinstance(c, BodyTube):
            parts.append(_bodytube(c, from_bottom))
        elif isinstance(c, Transition):
            parts.append(_transition(c))
    parts.append("</subcomponents></stage>")
    return "".join(parts)


def conditions(overrides: dict | None = None) -> dict:
    out = dict(DEFAULT_SIM_CONDITIONS)
    for k, v in (overrides or {}).items():
        if v is not None and k in out:
            out[k] = v
    return out


def to_ork_xml(design: Design, cond: dict | None = None) -> str:
    """Return the .ork XML for a validated design. `cond` = merged sim conditions."""
    cond = conditions(cond)
    n = len(design.stages)
    # OpenRocket numbers stages top = 0; ignition "burnout" on upper stages refers to the stage below.
    stages_xml = "".join(_stage(st, n - 1 - i) for i, st in enumerate(design.stages))
    active = "".join(f'<stage number="{i}" active="true"/>' for i in range(n))
    return _with_ids(
        "<?xml version='1.0' encoding='utf-8'?>"
        '<openrocket version="1.9" creator="sftgen">'
        f"<rocket><name>{escape(design.name)}</name>"
        '<axialoffset method="absolute">0.0</axialoffset><position type="absolute">0.0</position>'
        f'<motorconfiguration configid="{CONFIG_ID}" default="true">{active}</motorconfiguration>'
        "<referencetype>maximum</referencetype>"
        f"<subcomponents>{stages_xml}</subcomponents></rocket>"
        '<simulations><simulation status="outdated"><name>sftgen</name>'
        "<simulator>RK4Simulator</simulator><calculator>BarrowmanCalculator</calculator>"
        f"<conditions><configid>{CONFIG_ID}</configid>"
        f"<launchrodlength>{_f(cond['rail_length_m'])}</launchrodlength>"
        f"<launchrodangle>{_f(math.radians(cond['launch_angle_deg']))}</launchrodangle>"
        "<launchroddirection>0.0</launchroddirection>"
        f"<windaverage>{_f(cond['wind_ms'])}</windaverage>"
        f"<windturbulence>{_f(cond['wind_turbulence'])}</windturbulence>"
        f"<launchaltitude>{_f(cond['site_altitude_m'])}</launchaltitude>"
        "<launchlatitude>45.0</launchlatitude><launchlongitude>0.0</launchlongitude>"
        '<geodeticmethod>flat</geodeticmethod><atmosphere model="isa"/>'
        f"<timestep>{_f(cond['time_step_s'])}</timestep>"
        "</conditions></simulation></simulations>"
        "</openrocket>"
    )


_COMPONENT_OPEN = re.compile(r"(<[a-z]+><name>[^<]*</name>)")


def _with_ids(xml: str) -> str:
    # OpenRocket gives components without an <id> a random UUID, and it iterates maps keyed by
    # those ids when summing forces, so unpinned ids make the last bits of every result vary.
    count = itertools.count(1)
    return _COMPONENT_OPEN.sub(lambda m: f"{m.group(1)}<id>00000000-0000-4000-8000-{next(count):012d}</id>", xml)


def new_config_id() -> str:
    return str(uuid.uuid4())
