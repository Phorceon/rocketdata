"""Known-case suite for sftgen.checker (DATA_SPEC.md section 7).

Half of the rows must be kept, half must be dropped for a specific reason,
including a design in millimetres, an unknown motor, an unstable design that
still hits apogee, and a missing parachute.

Rows are built by executing the real tools through ``sftgen.tools.call``
exactly like ``sftgen.session`` does: tool base conditions are the contract
defaults minus the seed, and tool content is ``json.dumps(output,
ensure_ascii=False)``. Every number quoted after a tool turn is read from the
returned output and formatted into the reasoning, never typed in.

One JVM is shared for the whole module; each row is built once and cached.
"""

from __future__ import annotations

import copy
import functools
import json
from pathlib import Path

import pytest

from sftgen import contract, tools
from sftgen.checker import check_row

SFTGEN = Path(__file__).resolve().parents[1]
ALPHA = json.loads((SFTGEN / "examples" / "alpha_c6.json").read_text())
PILOT_ROW = json.loads((SFTGEN / "out" / "pilot.jsonl").read_text())


# --------------------------------------------------------------------------
# Designs
# --------------------------------------------------------------------------

def _contents(d):
    return d["stages"][0]["components"][1]["contents"]


def alpha_design(chute_m=0.305, fin_offset_m=0.0, extra=(), designation="C6", delay_s=5.0):
    """The example BT-50/C6 design with tweakable chute, fins, contents and motor."""
    d = copy.deepcopy(ALPHA)
    c = _contents(d)
    for x in list(c):
        if x["type"] == "parachute":
            if chute_m is None:
                c.remove(x)
            else:
                x["diameter_m"] = chute_m
        elif x["type"] == "motor_mount":
            x["motor"]["designation"] = designation
            x["motor"]["delay_s"] = delay_s
        elif x["type"] == "trapezoidal_fins":
            x["offset_from_aft_m"] = fin_offset_m
    for item in reversed(list(extra)):
        c.insert(0, item)
    return d


def d12_design():
    """BT-55-class airframe on an Estes D12 (24 mm motor in a 33.6 mm tube)."""
    return {
        "name": "BT-55 D12 sport",
        "stages": [{"name": "Sustainer", "components": [
            {"type": "nosecone", "shape": "ogive", "length_m": 0.12, "diameter_m": 0.0336,
             "wall_thickness_m": 0.002, "material": "Polystyrene"},
            {"type": "bodytube", "length_m": 0.55, "outer_diameter_m": 0.0336,
             "wall_thickness_m": 0.0006, "material": "Cardboard", "contents": [
                {"type": "parachute", "diameter_m": 0.45, "cd": 0.8, "deploy_event": "ejection",
                 "material": "Ripstop nylon", "position_from_top_m": 0.04},
                {"type": "motor_mount", "outer_diameter_m": 0.0250, "length_m": 0.07,
                 "wall_thickness_m": 0.0004, "material": "Cardboard",
                 "motor": {"manufacturer": "Estes", "designation": "D12", "delay_s": 5.0},
                 "overhang_m": 0.005},
                {"type": "trapezoidal_fins", "count": 3, "root_chord_m": 0.07,
                 "tip_chord_m": 0.03, "span_m": 0.05, "sweep_m": 0.03, "thickness_m": 0.002,
                 "material": "Balsa", "offset_from_aft_m": 0.0},
            ]},
        ]}],
    }


def h128w_design():
    """BT-60-class airframe on an AeroTech H128W (29 mm motor in a 41.6 mm tube)."""
    return {
        "name": "BT-60 H128W level1",
        "stages": [{"name": "Sustainer", "components": [
            {"type": "nosecone", "shape": "ogive", "length_m": 0.15, "diameter_m": 0.0416,
             "wall_thickness_m": 0.002, "material": "Polystyrene"},
            {"type": "bodytube", "length_m": 0.75, "outer_diameter_m": 0.0416,
             "wall_thickness_m": 0.0008, "material": "Cardboard", "contents": [
                {"type": "parachute", "diameter_m": 0.70, "cd": 0.8, "deploy_event": "ejection",
                 "material": "Ripstop nylon", "position_from_top_m": 0.05},
                {"type": "motor_mount", "outer_diameter_m": 0.0300, "length_m": 0.20,
                 "wall_thickness_m": 0.0004, "material": "Kraft phenolic",
                 "motor": {"manufacturer": "AeroTech", "designation": "H128W", "delay_s": 14.0},
                 "overhang_m": 0.01},
                {"type": "trapezoidal_fins", "count": 3, "root_chord_m": 0.11,
                 "tip_chord_m": 0.045, "span_m": 0.07, "sweep_m": 0.05, "thickness_m": 0.003,
                 "material": "Plywood (birch)", "offset_from_aft_m": 0.0},
            ]},
        ]}],
    }


def dual_deploy_design():
    """C6 airframe, plugged motor, drogue at apogee and main at 150 m altitude."""
    d = alpha_design(chute_m=None, delay_s=None)
    c = _contents(d)
    c.insert(0, {"type": "parachute", "diameter_m": 0.15, "cd": 0.8,
                 "deploy_event": "apogee", "material": "Ripstop nylon",
                 "position_from_top_m": 0.05})
    c.insert(1, {"type": "parachute", "diameter_m": 0.35, "cd": 0.8,
                 "deploy_event": "altitude", "deploy_altitude_m": 150.0,
                 "material": "Ripstop nylon", "position_from_top_m": 0.03})
    return d


def mm_variant(design):
    """The same design with every '*_m' field scaled x1000 (written in mm, not m)."""
    out = copy.deepcopy(design)

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k.endswith("_m") and isinstance(v, (int, float)) and not isinstance(v, bool):
                    o[k] = v * 1000
                else:
                    walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(out)
    return out


# --------------------------------------------------------------------------
# Row builder: same execution semantics as sftgen.session
# --------------------------------------------------------------------------

class Trace:
    """Appends assistant/tool messages, running each tool call for real.

    tools.call() gets seed=<row seed> and base_conditions = contract defaults
    minus seed, exactly as session.cmd_step does. Tool message content is the
    verbatim JSON dump of the output dict.
    """

    def __init__(self, prompt: str, seed: int):
        self.seed = seed
        self.messages = [
            {"role": "system", "content": contract.SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        self._n = 0
        self._base = dict(contract.DEFAULT_SIM_CONDITIONS)
        self._base.pop("seed", None)

    def step(self, reasoning: str, calls: list) -> list:
        tcs = []
        for name, args in calls:
            self._n += 1
            tcs.append({"id": f"call_{self._n}", "type": "function",
                        "function": {"name": name, "arguments": args}})
        self.messages.append({"role": "assistant", "reasoning_content": reasoning,
                              "content": "", "tool_calls": tcs})
        outs = []
        for c in tcs:
            fn = c["function"]
            out = tools.call(fn["name"], fn["arguments"],
                             seed=self.seed, base_conditions=self._base)
            self.messages.append({"role": "tool", "tool_call_id": c["id"],
                                  "name": fn["name"],
                                  "content": json.dumps(out, ensure_ascii=False)})
            outs.append(out)
        return outs

    def final(self, reasoning: str, content: str):
        self.messages.append({"role": "assistant", "reasoning_content": reasoning,
                              "content": content})

    def row(self, rid, targets, sim_over=None):
        cond = dict(contract.DEFAULT_SIM_CONDITIONS)
        cond.update(sim_over or {})
        cond["seed"] = self.seed
        return {
            "id": f"chk_{rid}",
            "group_id": "g_checker_suite",
            "split": "train",
            "source": "hand-written",
            "prompt_id": f"chk_{rid}",
            "prompt_type": "test",
            "targets": targets,
            "sim_conditions": cond,
            "tools": contract.TOOLS,
            "messages": self.messages,
            "verification": None,
            "generator": {"name": "checker-tests", "prompt_version": "test",
                          "contract": contract.CONTRACT_VERSION},
        }


def _sec(sim, i=0):
    return sim["sections"][i]


# --------------------------------------------------------------------------
# Row builders (one per known case). Each returns a full row dict.
# --------------------------------------------------------------------------

_BUILDERS = {}


def _case(fn):
    _BUILDERS[fn.__name__] = fn
    return fn


# -------------------------------------------------------------- MUST PASS --

@_case
def clean_pass():
    """Alpha C6, one simulate, passes everything on the first draft."""
    prompt = ("First club build: get me to about 340 m on a C motor or smaller, "
              "and it has to come down soft enough to fly again.")
    targets = {"apogee_m": {"value": 340, "kind": "about"},
               "motor_class": {"value": "C", "kind": "max"},
               "ground_hit_ms": {"value": 6.0, "kind": "max"}}
    design = alpha_design()
    tr = Trace(prompt, seed=6111)
    tr.step(
        "1. Understand: apogee about 340 m (approximate, aim inside 5%). Motor class at most C "
        "(fixed limit). Landing limit not stated, so I use the usual 6 m/s maximum. Wind, rail "
        "and site not given; assume the site defaults of 2 m/s wind on a 1.5 m rail. One stage.\n"
        "2. Feasibility: climbing 340 m needs a burnout speed of sqrt(2 * 9.81 * 340) = 82 m/s "
        "before drag. A light rocket loses a big share of that to drag, so a mid-C motor is the "
        "right order. Need the real C6 numbers before sizing.",
        [("motor_lookup", {"designation": "C6"})])
    m = tr.step(
        "2. Feasibility: the C6 returns 8.8 N*s total impulse and 4.8 N average thrust over "
        "1.83 s. A light bird of about 0.05 kg gets thrust-to-weight = 4.8 / (0.05 * 9.81) = 9.8, "
        "so the goal is feasible with margin for drag.\n"
        "3. Size: descent mass is about 0.04 kg; for a 5 m/s landing under Cd 0.8 the canopy "
        "needs 2 * 0.04 * 9.81 / (1.225 * 0.8 * 25) = 0.032 m^2, about a 0.20 m diameter. A "
        "0.305 m chute has margin.\n"
        "4. Draft: ogive nose, 24.9 mm tube 0.46 m long, 18 mm mount, three balsa fins and the "
        "0.305 m chute on the 5 s ejection delay. Simulating the draft.",
        [("simulate", {"design": design})])[0]
    s = _sec(m)
    tr.final(
        f"4. Check: the simulator gives {m['apogee_m']} m apogee against the 340 m goal, "
        f"{m['rail_exit_ms']} m/s off the rail, thrust-to-weight {m['thrust_to_weight']}, "
        f"margin {m['stability_rail_exit_cal']} cal at rail exit and {s['landing_ms']} m/s "
        "touchdown — inside every gate and all three targets.\n"
        "5. Fix: none needed; the first draft passed every check.\n"
        "6. Uncertainty: apogee leans on OpenRocket's drag model and the built weight — the "
        f"simulator used {m['liftoff_mass_kg']} kg. Canopy Cd is a model value, not measured.",
        f"C6-5 on a 24.9 mm airframe, 0.56 m overall, three balsa fins and a 0.305 m chute.\n"
        f"Simulated at site defaults: {m['apogee_m']} m apogee, {m['rail_exit_ms']} m/s off the "
        f"rail, {s['landing_ms']} m/s touchdown.\n"
        f"<design>{json.dumps(design)}</design>")
    return tr.row("clean_pass", targets)


@_case
def fix_chute():
    """First draft lands over 6 m/s on a 0.10 m chute; fix enlarges it to 0.305 m."""
    prompt = "About 340 m on an Estes C6, and it must touch down under 6 m/s."
    targets = {"apogee_m": {"value": 340, "kind": "about"},
               "ground_hit_ms": {"value": 6.0, "kind": "max"},
               "motor": {"value": ["C6"], "kind": "exact"}}
    draft = alpha_design(chute_m=0.10)
    fixed = alpha_design()
    tr = Trace(prompt, seed=6112)
    tr.step(
        "1. Understand: apogee about 340 m (approximate), touchdown at most 6 m/s, motor fixed "
        "to the Estes C6. Wind and rail not stated — assume the site defaults of 2 m/s wind and "
        "a 1.5 m rail.\n"
        "2. Feasibility: 340 m is well inside a C6's reach on a light airframe; get the motor "
        "data first.",
        [("motor_lookup", {"designation": "C6"})])
    s1 = tr.step(
        "2. Feasibility: the C6 gives 8.8 N*s and 4.8 N average thrust — plenty for a 0.05 kg "
        "bird, thrust-to-weight = 4.8 / (0.05 * 9.81) = 9.8.\n"
        "3. Size: standard 24.9 mm airframe. A compact 0.10 m canopy keeps the packing simple "
        "and the descent quick.\n"
        "4. Draft: ogive nose, 24.9 mm tube 0.46 m long, 18 mm mount, three balsa fins, 0.10 m "
        "chute on the 5 s delay. Simulating the draft.",
        [("simulate", {"design": draft})])[0]
    sec1 = _sec(s1)
    s2 = tr.step(
        f"4. Check: the simulator gives {s1['apogee_m']} m apogee — inside the band — but the "
        f"sustainer lands at {sec1['landing_ms']} m/s, over the 6 m/s limit. Rail "
        f"{s1['rail_exit_ms']} m/s, thrust-to-weight {s1['thrust_to_weight']} and margin "
        f"{s1['stability_rail_exit_cal']} cal all pass; the failure is the landing.\n"
        f"5. Fix: the {sec1['landing_ms']} m/s touchdown needs to come under 6 m/s. Descent "
        "speed scales as 1/diameter, so the canopy must grow by roughly "
        f"({sec1['landing_ms']} / 5.5) ^ 2 = 3. Enlarging the chute from 0.10 m to 0.305 m puts "
        "the estimate near 4 m/s. Re-flying.",
        [("simulate", {"design": fixed})])[0]
    sec2 = _sec(s2)
    tr.final(
        f"4. Check: the simulator gives {s2['apogee_m']} m apogee and {sec2['landing_ms']} m/s "
        f"landing — the touchdown target passes now, and rail {s2['rail_exit_ms']} m/s, "
        f"thrust-to-weight {s2['thrust_to_weight']} and margin {s2['stability_rail_exit_cal']} "
        "cal still pass.\n"
        "5. Fix: none needed after this round; the larger canopy cleared the landing limit.\n"
        "6. Uncertainty: the canopy sizing is model-based; a heavier build lands faster, so "
        "don't shave the fins.",
        f"C6-5 on a 24.9 mm airframe; enlarged the chute from 0.10 m to 0.305 m after the "
        f"first draft landed hot.\n"
        f"Simulated after the fix: {s2['apogee_m']} m apogee, {s2['rail_exit_ms']} m/s off the "
        f"rail, {sec2['landing_ms']} m/s touchdown.\n"
        f"<design>{json.dumps(fixed)}</design>")
    return tr.row("fix_chute", targets)


@_case
def fixed_motor_h128w():
    """Motor pinned to the AeroTech H128W on a BT-60-class airframe."""
    prompt = ("I'm Level 1 and have an AeroTech H128W ready to go. Get me to about 1,000 m "
              "and back down under 6 m/s.")
    targets = {"motor": {"value": ["H128W"], "kind": "exact"},
               "apogee_m": {"value": 1000, "kind": "about"},
               "ground_hit_ms": {"value": 6.0, "kind": "max"}}
    design = h128w_design()
    tr = Trace(prompt, seed=6113)
    tr.step(
        "1. Understand: apogee about 1,000 m (approximate), touchdown at most 6 m/s, motor "
        "fixed to the AeroTech H128W. Wind and rail not stated — assume the site defaults of "
        "2 m/s and a 1.5 m rail. One stage.\n"
        "2. Feasibility: an H motor is generous for 1,000 m; need the real impulse, mass and "
        "delay options first.",
        [("motor_lookup", {"designation": "H128W", "manufacturer": "AeroTech"})])
    st = tr.step(
        "2. Feasibility: the H128W returns 177.8 N*s over 1.16 s at 152.6 N average thrust, "
        "0.029 m diameter, 0.194 m long, 0.2016 kg loaded, with a single 14 s delay option. "
        "Even at 0.5 kg liftoff that is a thrust-to-weight of 152.6 / (0.5 * 9.81) = 31, far "
        "above 3 — 1,000 m is comfortable.\n"
        "3. Size: a 29 mm motor wants a mid-size airframe — a 41.6 mm tube (BT-60 class) 0.75 m "
        "long with a 30 mm phenolic mount 0.20 m long. Descent mass near 0.26 kg; for 5 m/s "
        "the canopy needs 2 * 0.26 * 9.81 / (1.225 * 0.8 * 25) = 0.21 m^2, about 0.52 m across; "
        "take 0.70 m for margin. Three plywood fins, 0.11 m root, 0.07 m span, at the tail.\n"
        "4. Draft: 0.15 m ogive nose on the 0.75 m tube, 0.70 m chute on the 14 s delay. "
        "Checking static stability before flying it.",
        [("stability", {"design": design})])[0]
    sim = tr.step(
        f"4. Check: the stability call returns liftoff mass {st['liftoff_mass_kg']} kg, CG "
        f"{st['cg_m']} m and CP {st['cp_m']} m — margin {st['static_margin_cal']} cal on a "
        f"{st['reference_diameter_m']} m reference, above the 1 cal minimum. The 14 s delay "
        "should fire close to apogee on a flight this size. Flying the design.",
        [("simulate", {"design": design})])[0]
    s = _sec(sim)
    tr.final(
        f"4. Check: the simulator gives {sim['apogee_m']} m apogee against the 1,000 m goal — "
        f"inside the 5% band — rail {sim['rail_exit_ms']} m/s, thrust-to-weight "
        f"{sim['thrust_to_weight']}, margin {sim['stability_rail_exit_cal']} cal at rail exit "
        f"and {s['landing_ms']} m/s under the chute. Every gate and the fixed motor check pass.\n"
        "5. Fix: none needed; the first draft passed every check.\n"
        "6. Uncertainty: the deploy fired late in the run (the 14 s delay overshoots apogee), "
        "so a shorter delay or dual deploy would be gentler on the airframe; the touchdown "
        "figure is still inside the limit.",
        f"H128W on a 41.6 mm airframe, 0.90 m overall, three plywood fins and a 0.70 m chute.\n"
        f"Simulated at site defaults: {sim['apogee_m']} m apogee, {sim['rail_exit_ms']} m/s off "
        f"the rail, {s['landing_ms']} m/s touchdown.\n"
        f"<design>{json.dumps(design)}</design>")
    return tr.row("fixed_motor_h128w", targets)


@_case
def motor_class_max():
    """motor_class 'max D' target on a D12 design."""
    prompt = ("Club rules cap me at a D motor. Around 360 m up and a soft landing "
              "would be great.")
    targets = {"motor_class": {"value": "D", "kind": "max"},
               "apogee_m": {"value": 360, "kind": "about"},
               "ground_hit_ms": {"value": 6.0, "kind": "max"}}
    design = d12_design()
    tr = Trace(prompt, seed=6114)
    tr.step(
        "1. Understand: apogee about 360 m (approximate), motor class at most D (fixed limit), "
        "touchdown limit not stated — assume the usual 6 m/s. Wind and rail not given, so site "
        "defaults. One stage.\n"
        "2. Feasibility: a D is generous for 360 m on a mid-size airframe; pull the D12 "
        "numbers first.",
        [("motor_lookup", {"designation": "D12"})])
    sim = tr.step(
        "2. Feasibility: the D12 returns 16.8 N*s at 10.4 N average — class D, at the limit. "
        "For a 0.10 kg liftoff mass, thrust-to-weight = 10.4 / (0.10 * 9.81) = 10.6 — fine.\n"
        "3. Size: the 24 mm motor needs at least a BT-55 airframe (33.6 mm). Descent mass "
        "about 0.08 kg wants 2 * 0.08 * 9.81 / (1.225 * 0.8 * 25) = 0.064 m^2 of canopy, "
        "a 0.29 m chute — take 0.45 m for margin.\n"
        "4. Draft: 0.12 m ogive nose, 0.55 m tube, 25 mm mount, three balsa fins, 0.45 m "
        "chute on the 5 s delay. Simulating.",
        [("simulate", {"design": design})])[0]
    s = _sec(sim)
    tr.final(
        f"4. Check: the simulator gives {sim['apogee_m']} m apogee against the 360 m goal, "
        f"{sim['rail_exit_ms']} m/s off the rail, thrust-to-weight {sim['thrust_to_weight']}, "
        f"margin {sim['stability_rail_exit_cal']} cal and a {s['landing_ms']} m/s touchdown. "
        "All gates and both targets pass on a class-D motor.\n"
        "5. Fix: none needed; the first draft passed every check.\n"
        "6. Uncertainty: apogee leans on the drag model; the heavier motor makes this one "
        "less sensitive to build weight than a C-class bird.",
        f"D12-5 on a 33.6 mm airframe, 0.67 m overall, three balsa fins and a 0.45 m chute.\n"
        f"Simulated at site defaults: {sim['apogee_m']} m apogee, {sim['rail_exit_ms']} m/s "
        f"off the rail, {s['landing_ms']} m/s touchdown.\n"
        f"<design>{json.dumps(design)}</design>")
    return tr.row("motor_class_max", targets)


@_case
def body_diameter_max():
    """body_diameter_m 'max 0.03' target on the 24.9 mm alpha design."""
    prompt = ("My launcher rack only takes airframes up to 30 mm. C motor, about 340 m, "
              "land under 6 m/s.")
    targets = {"body_diameter_m": {"value": 0.03, "kind": "max"},
               "motor_class": {"value": "C", "kind": "max"},
               "apogee_m": {"value": 340, "kind": "about"},
               "ground_hit_ms": {"value": 6.0, "kind": "max"}}
    design = alpha_design()
    tr = Trace(prompt, seed=6115)
    tr.step(
        "1. Understand: apogee about 340 m (approximate), motor class at most C, touchdown at "
        "most 6 m/s, and the body must fit a 30 mm rack — a fixed size limit. Wind and rail "
        "not given; site defaults.\n"
        "2. Feasibility: 30 mm fits a BT-50 (24.9 mm) with room to spare; get the C6 numbers.",
        [("motor_lookup", {"designation": "C6"})])
    sim = tr.step(
        "2. Feasibility: the C6 gives 8.8 N*s at 4.8 N average; for a 0.05 kg bird that is "
        "thrust-to-weight = 4.8 / (0.05 * 9.81) = 9.8 — feasible.\n"
        "3. Size: 24.9 mm BT-50 tube is under the 30 mm rack limit. Standard fin and chute "
        "sizing for a 0.04 kg descent mass.\n"
        "4. Draft: ogive nose, 24.9 mm tube 0.46 m long, 18 mm mount, three balsa fins, "
        "0.305 m chute on the 5 s delay. Simulating.",
        [("simulate", {"design": design})])[0]
    s = _sec(sim)
    tr.final(
        f"4. Check: the simulator gives {sim['apogee_m']} m apogee against the 340 m goal, "
        f"{sim['rail_exit_ms']} m/s off the rail, thrust-to-weight {sim['thrust_to_weight']}, "
        f"margin {sim['stability_rail_exit_cal']} cal, {s['landing_ms']} m/s touchdown — and "
        "the 24.9 mm airframe sits under the 30 mm limit.\n"
        "5. Fix: none needed; the first draft passed every check.\n"
        "6. Uncertainty: standard build-tolerance caveats; apogee leans on the drag model.",
        f"C6-5 on a 24.9 mm airframe with a 0.305 m chute — fits the 30 mm rack.\n"
        f"Simulated at site defaults: {sim['apogee_m']} m apogee, {s['landing_ms']} m/s "
        "touchdown.\n"
        f"<design>{json.dumps(design)}</design>")
    return tr.row("body_diameter_max", targets)


@_case
def dual_deploy():
    """recovery 'dual_deploy': drogue at apogee plus main at 150 m."""
    prompt = ("I want to try dual deployment on a small bird — drogue opens at apogee, "
              "main at 150 m on the way down. About 330 m on a C6.")
    targets = {"recovery": {"value": "dual_deploy", "kind": "exact"},
               "motor": {"value": ["C6"], "kind": "exact"},
               "apogee_m": {"value": 330, "kind": "about"},
               "ground_hit_ms": {"value": 6.0, "kind": "max"}}
    design = dual_deploy_design()
    tr = Trace(prompt, seed=6116)
    tr.step(
        "1. Understand: apogee about 330 m (approximate), motor fixed to the C6, and recovery "
        "must be dual deploy — drogue at apogee, main at 150 m. Wind and rail not given; "
        "site defaults.\n"
        "2. Feasibility: dual deploy on a small rocket is unusual but legal; get the C6 "
        "numbers.",
        [("motor_lookup", {"designation": "C6"})])
    sim = tr.step(
        "2. Feasibility: the C6 gives 8.8 N*s at 4.8 N average — enough for about 330 m on a "
        "light bird.\n"
        "3. Size: drogue 0.15 m for a fast but safe drop to main altitude; the main needs "
        "2 * 0.05 * 9.81 / (1.225 * 0.8 * 25) = 0.04 m^2 for 5 m/s at 0.05 kg descent mass, "
        "a 0.25 m chute — take 0.35 m. Motor delay set to plugged: deployment comes from the "
        "events, not the ejection charge.\n"
        "4. Draft: ogive nose, 24.9 mm tube 0.46 m long, 18 mm mount, three balsa fins, "
        "drogue at apogee and main at 150 m. Simulating.",
        [("simulate", {"design": design})])[0]
    s = _sec(sim)
    tr.final(
        f"4. Check: the simulator gives {sim['apogee_m']} m apogee and a {s['landing_ms']} m/s "
        f"touchdown; the first recovery event fires at {s['deploy_time_s']} s and the section "
        f"reaches the ground. Rail {sim['rail_exit_ms']} m/s, thrust-to-weight "
        f"{sim['thrust_to_weight']}, margin {sim['stability_rail_exit_cal']} cal — all pass, "
        "and the design is dual deploy by construction.\n"
        "5. Fix: none needed; the first draft passed every check.\n"
        "6. Uncertainty: the run fires the drogue at apogee and the main at 150 m as "
        "configured; a real dual deploy leans on the altimeter settings, not the motor.",
        f"C6 (plugged) on a 24.9 mm airframe with dual deployment: 0.15 m drogue at apogee, "
        f"0.35 m main at 150 m.\n"
        f"Simulated at site defaults: {sim['apogee_m']} m apogee, {s['landing_ms']} m/s "
        "touchdown.\n"
        f"<design>{json.dumps(design)}</design>")
    return tr.row("dual_deploy", targets)


@_case
def payload_min():
    """payload_kg 'min 0.04' target with a mass item named 'payload'."""
    prompt = ("Club night: loft a 40 g payload to about 250 m on a C motor, "
              "land under 6 m/s.")
    targets = {"payload_kg": {"value": 0.04, "kind": "min"},
               "motor_class": {"value": "C", "kind": "max"},
               "apogee_m": {"value": 250, "kind": "about"},
               "ground_hit_ms": {"value": 6.0, "kind": "max"}}
    design = alpha_design(extra=[{"type": "mass", "name": "payload", "mass_kg": 0.04,
                                  "position_from_top_m": 0.1}])
    tr = Trace(prompt, seed=6117)
    tr.step(
        "1. Understand: carry at least 40 g of payload, apogee about 250 m (approximate), "
        "motor class at most C, land under 6 m/s. Wind and rail not given — site defaults.\n"
        "2. Feasibility: 40 g is heavy on a C; thrust-to-weight and rail exit need care once "
        "sized.",
        [("motor_lookup", {"designation": "C6"})])
    sim = tr.step(
        "2. Feasibility: the C6 gives 8.8 N*s at 4.8 N average. With payload the bird masses "
        "about 0.09 kg: thrust-to-weight = 4.8 / (0.09 * 9.81) = 5.4, above 3. Rail exit is "
        "the worry: mean acceleration near (4.8 - 0.88) / 0.09 = 44 m/s^2 gives "
        "sqrt(2 * 44 * 1.5) = 11.5 m/s — marginal against 15 m/s, but the C6's ignition "
        "spike should carry it past. Worth a real run.\n"
        "3. Size: the standard 24.9 mm airframe; the 40 g payload rides at the top of the "
        "tube. Keep the 0.305 m chute for the heavier descent mass.\n"
        "4. Draft: ogive nose, 24.9 mm tube 0.46 m long, 18 mm mount, three balsa fins, "
        "0.04 kg payload and the chute on the 5 s delay. Simulating.",
        [("simulate", {"design": design})])[0]
    s = _sec(sim)
    tr.final(
        f"4. Check: the simulator gives {sim['apogee_m']} m apogee and {s['landing_ms']} m/s "
        f"landing; rail exit is {sim['rail_exit_ms']} m/s — the ignition spike cleared 15 "
        f"m/s as hoped — and thrust-to-weight {sim['thrust_to_weight']} and margin "
        f"{sim['stability_rail_exit_cal']} cal pass. The 0.04 kg payload is aboard.\n"
        "5. Fix: none needed; the first draft passed every check.\n"
        "6. Uncertainty: rail exit margin is thin; a draggier build could dip under 15 m/s, "
        "so keep the finish smooth.",
        f"C6-5 on a 24.9 mm airframe carrying a 40 g payload, with a 0.305 m chute.\n"
        f"Simulated at site defaults: {sim['apogee_m']} m apogee, {sim['rail_exit_ms']} m/s "
        f"off the rail, {s['landing_ms']} m/s touchdown.\n"
        f"<design>{json.dumps(design)}</design>")
    return tr.row("payload_min", targets)


@_case
def wind_conditions():
    """Prompt states ~8 mph wind; the simulate call passes it through conditions."""
    prompt = ("We're flying in about 8 mph of wind at the sod farm. C motor, around 340 m, "
              "under 6 m/s at touchdown.")
    targets = {"apogee_m": {"value": 340, "kind": "about"},
               "motor_class": {"value": "C", "kind": "max"},
               "ground_hit_ms": {"value": 6.0, "kind": "max"}}
    design = alpha_design()
    tr = Trace(prompt, seed=6118)
    tr.step(
        "1. Understand: apogee about 340 m (approximate), motor class at most C, touchdown "
        "at most 6 m/s, wind about 8 mph = 3.6 m/s — pass it to the simulator as a launch "
        "condition. Rail not given; assume 1.5 m.\n"
        "2. Feasibility: 3.6 m/s of wind is well under the 20 mph limit; a C6 has the legs "
        "for 340 m. Get the motor numbers.",
        [("motor_lookup", {"designation": "C6"})])
    sim = tr.step(
        "2. Feasibility: the C6 gives 8.8 N*s at 4.8 N average — feasible for a light bird.\n"
        "3. Size: standard 24.9 mm airframe, 0.305 m chute for a 5 m/s descent; a little "
        "extra margin helps in the wind.\n"
        "4. Draft: ogive nose, 24.9 mm tube 0.46 m long, 18 mm mount, three balsa fins, "
        "0.305 m chute on the 5 s delay. Simulating at the stated 3.6 m/s wind.",
        [("simulate", {"design": design, "conditions": {"wind_ms": 3.6}})])[0]
    s = _sec(sim)
    tr.final(
        f"4. Check: the simulator gives {sim['apogee_m']} m apogee and {s['landing_ms']} m/s "
        f"touchdown in the stated wind; rail {sim['rail_exit_ms']} m/s, thrust-to-weight "
        f"{sim['thrust_to_weight']}, margin {sim['stability_rail_exit_cal']} cal — all pass.\n"
        "5. Fix: none needed; the first draft passed every check.\n"
        "6. Uncertainty: it will weathercock into the wind and drift on descent; the canopy "
        "is sized with margin for that.",
        f"C6-5 on a 24.9 mm airframe with a 0.305 m chute, sized for an 8 mph day.\n"
        f"Simulated in the stated wind: {sim['apogee_m']} m apogee, {s['landing_ms']} m/s "
        "touchdown.\n"
        f"<design>{json.dumps(design)}</design>")
    return tr.row("wind_conditions", targets, sim_over={"wind_ms": 3.6})


@_case
def infeasible_prompt():
    """'3,000 m on a single C6' answered as infeasible, with motor_lookup evidence."""
    prompt = "Could a rocket reach 3,000 m on a single Estes C6?"
    targets = {"feasible": {"value": False, "kind": "exact"},
               "apogee_m": {"value": 3000, "kind": "about"},
               "motor": {"value": ["C6"], "kind": "exact"}}
    tr = Trace(prompt, seed=6119)
    tr.step(
        "1. Understand: apogee about 3,000 m (approximate), motor fixed to a single Estes "
        "C6. Nothing else stated; site defaults assumed.\n"
        "2. Feasibility: a ballistic climb to 3,000 m needs a burnout speed of "
        "sqrt(2 * 9.81 * 3000) = 243 m/s before drag losses. I need the C6's real impulse "
        "first.",
        [("motor_lookup", {"designation": "C6"})])
    tr.final(
        "2. Feasibility: the C6 carries 8.8 N*s and 4.8 N average thrust. A very light "
        "0.05 kg rocket on it reaches a few hundred metres in practice — an order of "
        "magnitude short of 3,000 m. The request is not feasible; the constraint that can't "
        "be met is the apogee on this motor.\n"
        "3. Size: nothing to size; no airframe changes the motor's impulse.\n"
        "4. Check: nothing to simulate — the impulse budget already rules the flight out.\n"
        "5. Fix: no fix inside the constraints; 3,000 m needs at least a mid-power motor "
        "such as an H or I.\n"
        "6. Uncertainty: my drag estimate is rough, but the gap between 8.8 N*s and what "
        "3,000 m takes is far larger than any modelling error.",
        "Infeasible: a single Estes C6 motor cannot meet the apogee target. Its 8.8 N*s "
        "reaches a few hundred metres, not 3,000 m.")
    return tr.row("infeasible_prompt", targets)


# -------------------------------------------------------------- MUST FAIL --

@_case
def millimetre_design():
    """Final design written in millimetres: fails schema bounds -> 'parse:'."""
    prompt = ("First club build: get me to about 340 m on a C motor or smaller, "
              "and it has to come down soft enough to fly again.")
    targets = {"apogee_m": {"value": 340, "kind": "about"},
               "motor_class": {"value": "C", "kind": "max"},
               "ground_hit_ms": {"value": 6.0, "kind": "max"}}
    design = mm_variant(alpha_design())
    tr = Trace(prompt, seed=6121)
    tr.step(
        "1. Understand: apogee about 340 m (approximate), motor class at most C, touchdown "
        "limit not stated — assume the usual 6 m/s. Site defaults for wind and rail.\n"
        "2. Feasibility: a mid-C motor is the right order; get the C6 numbers.",
        [("motor_lookup", {"designation": "C6"})])
    out = tr.step(
        "2. Feasibility: the C6 gives 8.8 N*s at 4.8 N average — feasible on a light bird.\n"
        "3. Size: a standard 24.9 mm tube about 460 mm long with 18 mm mount and a 305 mm "
        "chute.\n"
        "4. Draft: ogive nose, 24.9 mm tube, three balsa fins. Simulating the draft.",
        [("simulate", {"design": design})])[0]
    tr.final(
        "4. Check: the run returned an error, but the dimensions look like a standard BT-50 "
        "build. Submitting the draft as-is.\n"
        "5. Fix: none applied.\n"
        "6. Uncertainty: high; the tooling did not confirm this design.",
        f"C6-5 on a 24.9 mm airframe with three balsa fins and a 305 mm chute "
        f"(sim error: {str(out.get('error'))[:60]}).\n"
        f"<design>{json.dumps(design)}</design>")
    return tr.row("millimetre_design", targets)


@_case
def unknown_motor():
    """Motor 'C7' is not in the database: lookup and simulate both error."""
    prompt = "Something around 340 m on an Estes C7, landing under 6 m/s."
    targets = {"apogee_m": {"value": 340, "kind": "about"},
               "motor": {"value": ["C7"], "kind": "exact"},
               "ground_hit_ms": {"value": 6.0, "kind": "max"}}
    design = alpha_design(designation="C7")
    tr = Trace(prompt, seed=6122)
    tr.step(
        "1. Understand: apogee about 340 m (approximate), motor fixed to the Estes C7, "
        "touchdown at most 6 m/s. Site defaults for wind and rail.\n"
        "2. Feasibility: need the C7's impulse and dimensions first.",
        [("motor_lookup", {"designation": "C7"})])
    tr.step(
        "2. Feasibility: the lookup came back 'unknown motor C7' with suggestions C6 and "
        "C5, but the airframe is already cut for an 18 mm mount — trying the C7 anyway.\n"
        "3. Size: standard 24.9 mm airframe, 0.305 m chute.\n"
        "4. Draft: ogive nose, 24.9 mm tube 0.46 m long, 18 mm mount, three balsa fins. "
        "Simulating.",
        [("simulate", {"design": design})])
    tr.final(
        "4. Check: the run returned an error for the unknown motor — the design was never "
        "flown.\n"
        "5. Fix: none applied; still blocked on the motor.\n"
        "6. Uncertainty: the design is unflown; an in-catalog motor is required first.",
        "C7 on a 24.9 mm airframe — still blocked: the motor is not in the database.\n"
        f"<design>{json.dumps(design)}</design>")
    return tr.row("unknown_motor", targets)


@_case
def unstable_hits_apogee():
    """Fins moved 70 mm forward: apogee on target but launch margin ~0.9 cal."""
    prompt = "About 340 m on a C6, land under 6 m/s."
    targets = {"apogee_m": {"value": 340, "kind": "about"},
               "motor": {"value": ["C6"], "kind": "exact"},
               "ground_hit_ms": {"value": 6.0, "kind": "max"}}
    design = alpha_design(fin_offset_m=0.07)
    tr = Trace(prompt, seed=6123)
    tr.step(
        "1. Understand: apogee about 340 m (approximate), touchdown at most 6 m/s, motor "
        "fixed to the C6. Site defaults for wind and rail.\n"
        "2. Feasibility: a C6 has the legs for 340 m; get its numbers.",
        [("motor_lookup", {"designation": "C6"})])
    sim = tr.step(
        "2. Feasibility: the C6 gives 8.8 N*s at 4.8 N average — feasible on a light bird.\n"
        "3. Size: standard 24.9 mm airframe, fins mounted a bit forward for looks, "
        "0.305 m chute.\n"
        "4. Draft: ogive nose, 24.9 mm tube 0.46 m long, 18 mm mount, three balsa fins "
        "shifted 70 mm forward of the tail. Simulating.",
        [("simulate", {"design": design})])[0]
    s = _sec(sim)
    tr.final(
        f"4. Check: the simulator gives {sim['apogee_m']} m apogee — the altitude target is "
        f"met — but stability at rail exit is {sim['stability_rail_exit_cal']} cal, under "
        f"the 1 cal minimum. Rail {sim['rail_exit_ms']} m/s and landing {s['landing_ms']} "
        "m/s pass.\n"
        "5. Fix: none applied; submitting the draft anyway.\n"
        "6. Uncertainty: the margin is marginal, so it will weathercock hard in any real "
        "wind.",
        f"C6-5 on a 24.9 mm airframe; still under the 1.0 cal stability minimum at "
        f"{sim['stability_rail_exit_cal']} cal.\n"
        f"<design>{json.dumps(design)}</design>")
    return tr.row("unstable_hits_apogee", targets)


@_case
def missing_parachute():
    """No parachute or streamer anywhere: recovery gate + lawn-dart landing."""
    prompt = "About 340 m on a C6 — keep it simple, I don't care about recovery."
    targets = {"apogee_m": {"value": 340, "kind": "about"},
               "motor": {"value": ["C6"], "kind": "exact"}}
    design = alpha_design(chute_m=None)
    tr = Trace(prompt, seed=6124)
    tr.step(
        "1. Understand: apogee about 340 m (approximate), motor fixed to the C6, recovery "
        "not requested. Site defaults for wind and rail.\n"
        "2. Feasibility: a C6 has the legs; get its numbers.",
        [("motor_lookup", {"designation": "C6"})])
    sim = tr.step(
        "2. Feasibility: the C6 gives 8.8 N*s at 4.8 N average — feasible.\n"
        "3. Size: standard 24.9 mm airframe, no recovery device per the request.\n"
        "4. Draft: ogive nose, 24.9 mm tube 0.46 m long, 18 mm mount, three balsa fins. "
        "Simulating.",
        [("simulate", {"design": design})])[0]
    s = _sec(sim)
    tr.final(
        f"4. Check: the simulator gives {sim['apogee_m']} m apogee — target met — but the "
        f"section comes down at {s['landing_ms']} m/s with no recovery deployed. That is a "
        "lawn dart and fails the recovery and landing gates.\n"
        "5. Fix: none applied; still lands at speed.\n"
        "6. Uncertainty: none — falling rockets are bad.",
        f"C6-5 on a 24.9 mm airframe, still coming down at {s['landing_ms']} m/s with no "
        "recovery device.\n"
        f"<design>{json.dumps(design)}</design>")
    return tr.row("missing_parachute", targets)


@_case
def thrust_to_weight_low():
    """0.12 kg of ballast on a C6: thrust-to-weight ~2.9 < 3."""
    prompt = "Ballast test: strap 120 g of lead into a C6 rocket. Anything over about 90 m."
    targets = {"apogee_m": {"value": 90, "kind": "about"},
               "motor": {"value": ["C6"], "kind": "exact"}}
    design = alpha_design(extra=[{"type": "mass", "name": "ballast", "mass_kg": 0.12,
                                  "position_from_top_m": 0.2}])
    tr = Trace(prompt, seed=6125)
    tr.step(
        "1. Understand: carry 120 g of ballast, apogee about 90 m (approximate), motor "
        "fixed to the C6. Site defaults.\n"
        "2. Feasibility: that is a lot of lead on a C6; check the real thrust first.",
        [("motor_lookup", {"designation": "C6"})])
    sim = tr.step(
        "2. Feasibility: the C6 gives 4.8 N average; liftoff mass about 0.17 kg means "
        "thrust-to-weight = 4.8 / (0.17 * 9.81) = 2.9 — under the 3 minimum. Trying the "
        "flight anyway.\n"
        "3. Size: standard 24.9 mm airframe plus the ballast and a 0.305 m chute.\n"
        "4. Draft: ogive nose, 24.9 mm tube 0.46 m long, 18 mm mount, three balsa fins, "
        "0.12 kg ballast. Simulating.",
        [("simulate", {"design": design})])[0]
    s = _sec(sim)
    tr.final(
        f"4. Check: the simulator gives thrust-to-weight {sim['thrust_to_weight']} — under "
        f"the 3 minimum — with rail exit {sim['rail_exit_ms']} m/s and landing "
        f"{s['landing_ms']} m/s. Multiple gates fail.\n"
        "5. Fix: none applied; still too heavy for the motor.\n"
        "6. Uncertainty: a stronger motor is the real fix.",
        f"C6-5 with 120 g ballast — still under the 3:1 thrust-to-weight minimum at "
        f"{sim['thrust_to_weight']}.\n"
        f"<design>{json.dumps(design)}</design>")
    return tr.row("thrust_to_weight_low", targets)


@_case
def rail_exit_slow():
    """0.08 kg ballast: thrust-to-weight passes (~3.8) but rail exit ~13 < 15 m/s."""
    prompt = ("Same club rocket but with an 80 g camera strapped in — still want about "
              "150 m and a soft landing under 6 m/s.")
    targets = {"apogee_m": {"value": 150, "kind": "about"},
               "motor": {"value": ["C6"], "kind": "exact"},
               "ground_hit_ms": {"value": 6.0, "kind": "max"}}
    design = alpha_design(chute_m=0.35,
                          extra=[{"type": "mass", "name": "camera", "mass_kg": 0.08,
                                  "position_from_top_m": 0.2}])
    tr = Trace(prompt, seed=6126)
    tr.step(
        "1. Understand: carry an 80 g camera, apogee about 150 m (approximate), motor "
        "fixed to the C6, touchdown at most 6 m/s. Site defaults for wind and rail.\n"
        "2. Feasibility: 80 g extra is heavy on a C; thrust-to-weight should clear 3 but "
        "rail exit will be slow. Get the motor numbers.",
        [("motor_lookup", {"designation": "C6"})])
    sim = tr.step(
        "2. Feasibility: the C6 gives 4.8 N average; liftoff mass about 0.13 kg means "
        "thrust-to-weight = 4.8 / (0.13 * 9.81) = 3.8 — over 3 but low, so rail speed is "
        "the risk.\n"
        "3. Size: standard 24.9 mm airframe, 0.35 m chute for the heavier descent mass.\n"
        "4. Draft: ogive nose, 24.9 mm tube 0.46 m long, 18 mm mount, three balsa fins, "
        "0.08 kg camera. Simulating.",
        [("simulate", {"design": design})])[0]
    s = _sec(sim)
    tr.final(
        f"4. Check: the simulator gives rail exit {sim['rail_exit_ms']} m/s — under the 15 "
        f"m/s minimum — though thrust-to-weight {sim['thrust_to_weight']} clears 3 and "
        f"{sim['apogee_m']} m apogee meets the goal. Landing is {s['landing_ms']} m/s.\n"
        "5. Fix: none applied; still slow off the rail.\n"
        "6. Uncertainty: it is stable but comes off the rail too slowly to be safe in any "
        "crosswind.",
        f"C6-5 with an 80 g camera — still under the 15 m/s rail-exit minimum at "
        f"{sim['rail_exit_ms']} m/s.\n"
        f"<design>{json.dumps(design)}</design>")
    return tr.row("rail_exit_slow", targets)


@_case
def design_differs_from_sim():
    """Final <design> adds a 5 g nose weight never simulated -> 'lint:design'."""
    prompt = ("First club build: get me to about 340 m on a C motor or smaller, "
              "and it has to come down soft enough to fly again.")
    targets = {"apogee_m": {"value": 340, "kind": "about"},
               "motor_class": {"value": "C", "kind": "max"},
               "ground_hit_ms": {"value": 6.0, "kind": "max"}}
    simulated = alpha_design()
    submitted = alpha_design(extra=[{"type": "mass", "name": "nose weight (clay)",
                                     "mass_kg": 0.005, "position_from_top_m": 0.0}])
    tr = Trace(prompt, seed=6127)
    tr.step(
        "1. Understand: apogee about 340 m (approximate), motor class at most C, touchdown "
        "limit not stated — assume the usual 6 m/s. Site defaults.\n"
        "2. Feasibility: a mid-C motor is the right order; get the C6 numbers.",
        [("motor_lookup", {"designation": "C6"})])
    sim = tr.step(
        "2. Feasibility: the C6 gives 8.8 N*s at 4.8 N average — feasible on a light bird.\n"
        "3. Size: standard 24.9 mm airframe, 0.305 m chute.\n"
        "4. Draft: ogive nose, 24.9 mm tube 0.46 m long, 18 mm mount, three balsa fins. "
        "Simulating.",
        [("simulate", {"design": simulated})])[0]
    s = _sec(sim)
    tr.final(
        f"4. Check: the simulator gives {sim['apogee_m']} m apogee, {sim['rail_exit_ms']} "
        f"m/s off the rail, {s['landing_ms']} m/s touchdown — inside the band.\n"
        "5. Fix: added a 5 g clay nose weight in the final design for a little extra "
        "margin without re-running.\n"
        "6. Uncertainty: the extra gram or two only helps the margin.",
        f"C6-5 on a 24.9 mm airframe, plus a 5 g clay nose weight for margin.\n"
        f"Simulated at site defaults: {sim['apogee_m']} m apogee, {s['landing_ms']} m/s "
        "touchdown.\n"
        f"<design>{json.dumps(submitted)}</design>")
    return tr.row("design_differs_from_sim", targets)


@_case
def tampered_tool_output():
    """Recorded tool output edited after the fact -> 'replay:' mismatch."""
    prompt = ("First club build: get me to about 340 m on a C motor or smaller, "
              "and it has to come down soft enough to fly again.")
    targets = {"apogee_m": {"value": 340, "kind": "about"},
               "motor_class": {"value": "C", "kind": "max"},
               "ground_hit_ms": {"value": 6.0, "kind": "max"}}
    design = alpha_design()
    tr = Trace(prompt, seed=6128)
    tr.step(
        "1. Understand: apogee about 340 m (approximate), motor class at most C, touchdown "
        "limit not stated — assume the usual 6 m/s. Site defaults.\n"
        "2. Feasibility: a mid-C motor is the right order; get the C6 numbers.",
        [("motor_lookup", {"designation": "C6"})])
    sim = tr.step(
        "2. Feasibility: the C6 gives 8.8 N*s at 4.8 N average — feasible.\n"
        "3. Size: standard 24.9 mm airframe, 0.305 m chute.\n"
        "4. Draft: ogive nose, 24.9 mm tube 0.46 m long, 18 mm mount, three balsa fins. "
        "Simulating.",
        [("simulate", {"design": design})])[0]
    s = _sec(sim)
    tr.final(
        f"4. Check: the simulator gives {sim['apogee_m']} m apogee, {sim['rail_exit_ms']} "
        f"m/s off the rail, {s['landing_ms']} m/s touchdown — all gates pass.\n"
        "5. Fix: none needed; the first draft passed every check.\n"
        "6. Uncertainty: apogee leans on the drag model and build weight.",
        f"C6-5 on a 24.9 mm airframe with a 0.305 m chute.\n"
        f"Simulated at site defaults: {sim['apogee_m']} m apogee, {s['landing_ms']} m/s "
        "touchdown.\n"
        f"<design>{json.dumps(design)}</design>")
    row = tr.row("tampered_tool_output", targets)
    # Forge the recorded tool output: claim a shorter drift than the real run.
    for m in row["messages"]:
        if m.get("role") == "tool" and m.get("name") == "simulate":
            o = json.loads(m["content"])
            o["sections"][0]["drift_m"] = round(o["sections"][0]["drift_m"] * 0.4, 1)
            m["content"] = json.dumps(o, ensure_ascii=False)
    return row


@_case
def wind_not_flown():
    """Prompt states 8 mph wind but the simulate call never passes it -> 'conditions:'."""
    prompt = ("We're flying in about 8 mph of wind at the sod farm. C motor, around 340 m, "
              "under 6 m/s at touchdown.")
    targets = {"apogee_m": {"value": 340, "kind": "about"},
               "motor_class": {"value": "C", "kind": "max"},
               "ground_hit_ms": {"value": 6.0, "kind": "max"}}
    design = alpha_design()
    tr = Trace(prompt, seed=6129)
    tr.step(
        "1. Understand: apogee about 340 m (approximate), motor class at most C, touchdown "
        "at most 6 m/s, wind about 8 mph = 3.6 m/s. Rail not given; assume 1.5 m.\n"
        "2. Feasibility: a C6 has the legs for 340 m; get the motor numbers.",
        [("motor_lookup", {"designation": "C6"})])
    sim = tr.step(
        "2. Feasibility: the C6 gives 8.8 N*s at 4.8 N average — feasible.\n"
        "3. Size: standard 24.9 mm airframe, 0.305 m chute.\n"
        "4. Draft: ogive nose, 24.9 mm tube 0.46 m long, 18 mm mount, three balsa fins. "
        "Simulating the draft.",
        [("simulate", {"design": design})])[0]  # conditions never passed — the cheat
    s = _sec(sim)
    tr.final(
        f"4. Check: the simulator gives {sim['apogee_m']} m apogee and {s['landing_ms']} m/s "
        f"touchdown; rail {sim['rail_exit_ms']} m/s and margin "
        f"{sim['stability_rail_exit_cal']} cal pass.\n"
        "5. Fix: none needed; the first draft passed every check.\n"
        "6. Uncertainty: it will drift on descent; keep the canopy honest.",
        f"C6-5 on a 24.9 mm airframe with a 0.305 m chute, sized for an 8 mph day.\n"
        f"Simulated: {sim['apogee_m']} m apogee, {s['landing_ms']} m/s touchdown.\n"
        f"<design>{json.dumps(design)}</design>")
    return tr.row("wind_not_flown", targets, sim_over={"wind_ms": 3.6})


@_case
def apogee_missed():
    """Single simulate lands outside the 'about' band -> apogee_m target failure."""
    prompt = "Something around 300 m on a C6, landing under 6 m/s."
    targets = {"apogee_m": {"value": 300, "kind": "about"},
               "motor": {"value": ["C6"], "kind": "exact"},
               "ground_hit_ms": {"value": 6.0, "kind": "max"}}
    design = alpha_design()
    tr = Trace(prompt, seed=6130)
    tr.step(
        "1. Understand: apogee about 300 m (approximate), touchdown at most 6 m/s, motor "
        "fixed to the C6. Site defaults.\n"
        "2. Feasibility: a C6 should be about right for 300 m; get its numbers.",
        [("motor_lookup", {"designation": "C6"})])
    sim = tr.step(
        "2. Feasibility: the C6 gives 8.8 N*s at 4.8 N average — should be close.\n"
        "3. Size: standard 24.9 mm airframe, 0.305 m chute.\n"
        "4. Draft: ogive nose, 24.9 mm tube 0.46 m long, 18 mm mount, three balsa fins. "
        "Simulating.",
        [("simulate", {"design": design})])[0]
    s = _sec(sim)
    tr.final(
        f"4. Check: the simulator gives {sim['apogee_m']} m apogee — still outside the 5% "
        f"band around 300 m. Rail {sim['rail_exit_ms']} m/s, landing {s['landing_ms']} m/s "
        "and the margin pass; only the altitude misses.\n"
        "5. Fix: none applied; submitting the closest draft.\n"
        "6. Uncertainty: it overshoots; a heavier build or a streamer would pull it down.",
        f"C6-5 on a 24.9 mm airframe — still overshoots the 300 m goal at "
        f"{sim['apogee_m']} m.\n"
        f"<design>{json.dumps(design)}</design>")
    return tr.row("apogee_missed", targets)


@_case
def motor_class_exceeded():
    """D12 flown against a motor_class 'max C' limit -> 'target:motor_class'."""
    prompt = ("I only have a D12 in the box — but field rules cap us at a C this "
              "weekend. Get me to about 360 m and land under 6 m/s.")
    targets = {"motor_class": {"value": "C", "kind": "max"},
               "motor": {"value": ["D12"], "kind": "exact"},
               "apogee_m": {"value": 360, "kind": "about"},
               "ground_hit_ms": {"value": 6.0, "kind": "max"}}
    design = d12_design()
    tr = Trace(prompt, seed=6131)
    tr.step(
        "1. Understand: apogee about 360 m (approximate), touchdown at most 6 m/s, motor "
        "class capped at C by the field rules. Site defaults.\n"
        "2. Feasibility: need motor numbers; the D12 is what is in the box.",
        [("motor_lookup", {"designation": "D12"})])
    sim = tr.step(
        "2. Feasibility: the D12 returns 16.8 N*s — class D, over the field limit, but it "
        "is what I have. Trying it on a BT-55 airframe.\n"
        "3. Size: 24 mm motor needs a 33.6 mm tube; 0.45 m chute for the descent mass.\n"
        "4. Draft: 0.12 m ogive nose, 0.55 m tube, 25 mm mount, three balsa fins, 0.45 m "
        "chute on the 5 s delay. Simulating.",
        [("simulate", {"design": design})])[0]
    s = _sec(sim)
    tr.final(
        f"4. Check: the simulator gives {sim['apogee_m']} m apogee, {sim['rail_exit_ms']} "
        f"m/s off the rail, {s['landing_ms']} m/s touchdown — the flight is fine but the "
        "D12 is over the C-class field limit.\n"
        "5. Fix: none applied; the motor still breaks the class rule.\n"
        "6. Uncertainty: flies well but is not legal at this field.",
        f"D12-5 on a 33.6 mm airframe — still over the C-class limit.\n"
        f"<design>{json.dumps(design)}</design>")
    return tr.row("motor_class_exceeded", targets)


@_case
def fake_provenance():
    """'Verified' claim before any tool turn -> 'lint:provenance'."""
    prompt = ("First club build: get me to about 340 m on a C motor or smaller, "
              "and it has to come down soft enough to fly again.")
    targets = {"apogee_m": {"value": 340, "kind": "about"},
               "motor_class": {"value": "C", "kind": "max"},
               "ground_hit_ms": {"value": 6.0, "kind": "max"}}
    design = alpha_design()
    tr = Trace(prompt, seed=6132)
    tr.step(
        "1. Understand: apogee about 340 m (approximate), motor class at most C, touchdown "
        "limit not stated — assume the usual 6 m/s. Site defaults. Verified: this design "
        "reaches about 340 m.\n"
        "2. Feasibility: a mid-C motor is the right order; get the C6 numbers.",
        [("motor_lookup", {"designation": "C6"})])
    sim = tr.step(
        "2. Feasibility: the C6 gives 8.8 N*s at 4.8 N average — feasible.\n"
        "3. Size: standard 24.9 mm airframe, 0.305 m chute.\n"
        "4. Draft: ogive nose, 24.9 mm tube 0.46 m long, 18 mm mount, three balsa fins. "
        "Simulating.",
        [("simulate", {"design": design})])[0]
    s = _sec(sim)
    tr.final(
        f"4. Check: the simulator gives {sim['apogee_m']} m apogee, {sim['rail_exit_ms']} "
        f"m/s off the rail, {s['landing_ms']} m/s touchdown — all gates pass.\n"
        "5. Fix: none needed; the first draft passed every check.\n"
        "6. Uncertainty: apogee leans on the drag model and build weight.",
        f"C6-5 on a 24.9 mm airframe with a 0.305 m chute.\n"
        f"Simulated at site defaults: {sim['apogee_m']} m apogee, {s['landing_ms']} m/s "
        "touchdown.\n"
        f"<design>{json.dumps(design)}</design>")
    return tr.row("fake_provenance", targets)


# --------------------------------------------------------------------------
# Case registry
# --------------------------------------------------------------------------

@functools.lru_cache(maxsize=None)
def _built(name: str) -> dict:
    return _BUILDERS[name]()


PASS_CASES = [
    "clean_pass",
    "fix_chute",
    "fixed_motor_h128w",
    "motor_class_max",
    "body_diameter_max",
    "dual_deploy",
    "payload_min",
    "wind_conditions",
    "infeasible_prompt",
]

# (case name, substring that must appear in at least one drop reason)
FAIL_CASES = [
    ("millimetre_design", "parse:"),
    ("unknown_motor", "unknown motor"),
    ("unstable_hits_apogee", "stability_rail_exit_cal"),
    ("missing_parachute", "gate:recovery"),
    ("thrust_to_weight_low", "thrust_to_weight"),
    ("rail_exit_slow", "rail_exit_ms"),
    ("design_differs_from_sim", "lint:design"),
    ("tampered_tool_output", "replay:"),
    ("wind_not_flown", "conditions:"),
    ("apogee_missed", "apogee_m"),
    ("motor_class_exceeded", "target:motor_class"),
    ("fake_provenance", "lint:provenance"),
]


# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------

def _assert_kept(name, row):
    res = check_row(row)
    assert res["keep"], f"{name} dropped: {res['reasons']}"


def test_pilot_row_is_kept():
    """The real pilot row from sftgen/out/pilot.jsonl must pass the checker."""
    made_under = PILOT_ROW.get("verification", {}).get("contract")
    if made_under != contract.CONTRACT_VERSION:
        pytest.skip(f"pilot row was generated under {made_under}; regenerate it under {contract.CONTRACT_VERSION}")
    _assert_kept("pilot", copy.deepcopy(PILOT_ROW))


@pytest.mark.parametrize("name", PASS_CASES)
def test_must_pass(name):
    _assert_kept(name, _built(name))


@pytest.mark.parametrize("name, expect", FAIL_CASES, ids=[n for n, _ in FAIL_CASES])
def test_must_fail(name, expect):
    res = check_row(_built(name))
    assert not res["keep"], f"{name} unexpectedly kept"
    assert any(expect in r for r in res["reasons"]), (
        f"{name}: expected a reason containing {expect!r}, got {res['reasons']}")


def test_rail_exit_failure_is_isolated():
    """The heavy-on-the-rail row fails only the rail gate, not thrust-to-weight."""
    res = check_row(_built("rail_exit_slow"))
    assert not res["keep"]
    assert any("rail_exit_ms" in r for r in res["reasons"]), res["reasons"]
    assert not any("thrust_to_weight" in r for r in res["reasons"]), res["reasons"]


# ------------------------------------------------------------- regressions --

def test_malformed_tool_content_drops_not_crashes():
    row = copy.deepcopy(_built("clean_pass"))
    for m in row["messages"]:
        if m.get("role") == "tool" and m.get("name") == "simulate":
            m["content"] = "{not valid json"
    res = check_row(row)
    assert not res["keep"]
    assert res["reasons"]


def test_verification_targets_do_not_cross_mark():
    res = check_row(_built("motor_class_exceeded"))
    assert not res["keep"]
    assert res["verification"]["targets"]["motor"] == "pass", res["verification"]
    assert res["verification"]["targets"]["motor_class"] == "fail"


def test_simulate_output_is_deterministic():
    design = alpha_design()
    outs = [tools.call("simulate", {"design": design}, seed=4242) for _ in range(20)]
    assert all(o == outs[0] for o in outs), (
        "non-deterministic fields: "
        + json.dumps([k for k in outs[0] if any(o[k] != outs[0][k] for o in outs[1:])]))
