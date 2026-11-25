"""Row checker (DATA_SPEC section 7): parse, safety gates, targets, trace lint, tool replay.

    from sftgen.checker import check_row
    result = check_row(row)        # {"keep": bool, "reasons": [...], "verification": {...}}

Gate and simulation-target logic lives in lint.gate_failures so the linter's
"was this fix justified" test and the checker agree. Design-level targets
(motor, class, diameters, stages, payload, recovery) are checked here.
"""

from __future__ import annotations

import json
import re

from pydantic import ValidationError

from . import contract, motors, tools
from .schema import MassItem, MotorMount, Parachute, Streamer, parse_design

DESIGN_RE = re.compile(r"<design>(.*?)</design>", re.S)
INFEASIBLE_RE = re.compile(r"\b(infeasible|not feasible|can(?:no|')t be met|cannot be met|not possible|isn't possible|impossible)\b", re.I)
CLASS_ORDER = ["1/4A", "1/2A"] + list("ABCDEFGHIJKLMNOPQ")


def _norm_motor(name: str) -> str:
    base, _ = motors.split_delay(name)
    return re.sub(r"[^A-Z0-9]", "", base.upper())


def final_design_text(row: dict) -> str | None:
    content = row["messages"][-1].get("content") or ""
    blocks = DESIGN_RE.findall(content)
    return blocks[0] if len(blocks) == 1 else None


def recovery_kind(design) -> str:
    kinds = set()
    for st in design.stages:
        devices = st.contents(Parachute) + st.contents(Streamer)
        chutes = st.contents(Parachute)
        events = {d.deploy_event for d in devices}
        if len(devices) >= 2 and ("altitude" in events) and (events & {"apogee", "ejection"}):
            kinds.add("dual_deploy")
        elif chutes:
            kinds.add("single_chute")
        elif devices:
            kinds.add("streamer")
        else:
            kinds.add("none")
    if "none" in kinds:
        return "none"
    if "dual_deploy" in kinds:
        return "dual_deploy"
    if "single_chute" in kinds:
        return "single_chute"
    return "streamer" if "streamer" in kinds else "none"


def design_gate_failures(design, cond: dict) -> list[str]:
    out = []
    for st in design.stages:
        if not (st.contents(Parachute) or st.contents(Streamer)):
            out.append(f"gate:recovery: section {st.name!r} separates or lands with no parachute or streamer")
    if float(cond.get("wind_ms", 0.0)) >= contract.GATES["max_wind_ms"]:
        out.append(f"gate:wind: {cond['wind_ms']} m/s is at or above the 20 mph limit")
    return out


def design_target_failures(design, targets: dict) -> list[str]:
    out = []
    mms = [mm for _, mm in design.motors()]
    infos = [motors.resolve(mm.motor.designation, mm.motor.manufacturer) for mm in mms]
    for key, t in targets.items():
        v, kind = t.get("value"), t.get("kind")
        if key == "motor":
            want = sorted({_norm_motor(x) for x in (v if isinstance(v, list) else [v])})
            have = sorted({_norm_motor(i["designation"]) for i in infos})
            if want != have:
                out.append(f"target:motor: design uses {have}, prompt fixed {want}")
        elif key == "motor_class":
            worst = max((CLASS_ORDER.index(i["class"]) for i in infos if i["class"] in CLASS_ORDER), default=-1)
            if worst > CLASS_ORDER.index(v):
                out.append(f"target:motor_class: uses a {CLASS_ORDER[worst]} motor, limit {v}")
        elif key == "motor_diameter_m":
            big = max(i["diameter_m"] for i in infos)
            if big > float(v) + 1e-4:
                out.append(f"target:motor_diameter_m: {big} m motor, limit {v} m")
        elif key == "body_diameter_m":
            big = max(_max_diameter(st) for st in design.stages)
            if big > float(v) + 0.0005:
                out.append(f"target:body_diameter_m: {big} m body, limit {v} m")
        elif key == "stages":
            if len(design.stages) != int(v):
                out.append(f"target:stages: {len(design.stages)} stages, prompt asked {v}")
        elif key == "motor_count":
            n = sum(mm.cluster_count for mm in mms)
            if n != int(v):
                out.append(f"target:motor_count: {n} motors, prompt asked {v}")
        elif key == "payload_kg":
            got = sum(x.mass_kg for st in design.stages for x in st.contents(MassItem) if "payload" in x.name.lower())
            if got + 1e-9 < float(v):
                out.append(f"target:payload_kg: carries {got} kg payload, prompt asked at least {v} kg")
        elif key == "recovery":
            got = recovery_kind(design)
            if got != v:
                out.append(f"target:recovery: design has {got}, prompt asked {v}")
    return out


def _max_diameter(st) -> float:
    best = 0.0
    for c in st.components:
        for attr in ("diameter_m", "outer_diameter_m", "fore_diameter_m", "aft_diameter_m"):
            if hasattr(c, attr):
                best = max(best, getattr(c, attr))
    return best


def _tool_calls(row):
    msgs = row["messages"]
    for i, m in enumerate(msgs):
        if m.get("role") == "assistant" and m.get("tool_calls"):
            for j, c in enumerate(m["tool_calls"]):
                tool_msg = msgs[i + 1 + j] if i + 1 + j < len(msgs) else None
                yield c, tool_msg


def _tool_output(tool_msg) -> dict | None:
    try:
        out = json.loads(tool_msg["content"])
    except (TypeError, ValueError, KeyError):
        return None
    return out if isinstance(out, dict) else None


def _site_defaults() -> dict:
    c = dict(contract.DEFAULT_SIM_CONDITIONS)
    c.pop("seed", None)
    return c


def _last_simulate_conditions(row: dict) -> dict:
    last = {}
    for c, _ in _tool_calls(row):
        if c["function"]["name"] == "simulate":
            args = c["function"]["arguments"]
            last = (args.get("conditions") if isinstance(args, dict) else None) or {}
    return dict(last) if isinstance(last, dict) else {}


def condition_mismatches(row: dict) -> list[str]:
    """The last simulate call must have flown under the conditions the prompt stated."""
    last = None
    for c, tm in _tool_calls(row):
        if c["function"]["name"] == "simulate":
            last = tm
    if last is None:
        return []
    recorded = _tool_output(last)
    if recorded is None:
        return ["conditions: final simulate output is not a JSON object"]
    used = recorded.get("conditions") or {}
    want = row["sim_conditions"]
    out = []
    for k, v in used.items():
        if k in want and abs(float(want[k]) - float(v)) > max(0.05 * abs(float(want[k])), 0.06):
            out.append(f"conditions: final simulate used {k}={v}, prompt conditions say {want[k]}")
    return out


def replay_mismatches(row: dict) -> list[str]:
    seed = row["sim_conditions"]["seed"]
    cond = _site_defaults()
    out = []
    for c, tm in _tool_calls(row):
        fn = c["function"]
        again = tools.call(fn["name"], fn["arguments"], seed=seed, base_conditions=cond)
        if tm is None or _tool_output(tm) != again:
            out.append(f"replay: {c['id']} {fn['name']} output differs on re-run")
    return out


def check_row(row: dict, replay: bool = True) -> dict:
    from . import lint

    reasons: list[str] = []
    targets = row.get("targets") or {}
    cond = dict(row["sim_conditions"])
    seed = cond.pop("seed")
    infeasible = targets.get("feasible", {}).get("value") is False
    verification = {
        "openrocket_version": contract.OPENROCKET_VERSION,
        "motor_db_version": contract.MOTOR_DB_VERSION,
        "contract": contract.CONTRACT_VERSION,
        "seed": seed,
        "gates": {}, "targets": {},
    }

    # 1. Parses
    text = final_design_text(row)
    design = None
    if text is None:
        if not infeasible:
            reasons.append("parse: final turn must have exactly one <design> block")
    else:
        try:
            design = parse_design(text)
        except (ValidationError, ValueError) as e:
            reasons.append(f"parse: {str(e).splitlines()[0][:200]}")

    if infeasible:
        content = row["messages"][-1].get("content") or ""
        if not INFEASIBLE_RE.search(content):
            reasons.append("infeasible: answer does not say the request is infeasible")

    # 2-3. Gates and targets on a fresh re-simulation. A closest-version design offered for an
    # infeasible prompt must be safe under the conditions it was flown at, but cannot meet the targets.
    if design is not None:
        gate_cond = cond
        if infeasible:
            gate_cond = {**_site_defaults(), **_last_simulate_conditions(row)}
        sim = tools.simulate({"design": json.loads(text)}, seed=seed, base_conditions=gate_cond)
        verification["final_sim"] = sim
        if not sim.get("ok"):
            reasons.append(f"simulate: {sim.get('error')}")
        else:
            gate_targets = {} if infeasible else targets
            sim_fails = lint._failures(sim, gate_targets)
            sim_fail = [f.text for f in sim_fails]
            des_gate = design_gate_failures(design, gate_cond if infeasible else row["sim_conditions"])
            des_tgt = [] if infeasible else design_target_failures(
                design, {k: v for k, v in targets.items() if k != "feasible"})
            for f in sim_fail + des_gate + des_tgt:
                reasons.append(f)
            verification["gates"] = {"failures": [f for f in sim_fail + des_gate if "gate" in f]}
            failed_names = {f.name.split(" ")[-1] for f in sim_fails}
            if "ground_hit_ms" in targets and "landing_ms" in failed_names:
                failed_names.add("ground_hit_ms")
            verification["targets"] = {
                k: ("fail" if k in failed_names or any(f.startswith(f"target:{k}:") for f in des_tgt) else "pass")
                for k in targets if k != "feasible"
            }

    # 4. Lint + replay
    for issue in lint.lint_row(row):
        if issue.severity == "must":
            reasons.append(f"lint:{issue.code}: {issue.message}")
    if design is not None and not infeasible:
        reasons += condition_mismatches(row)
    if replay:
        reasons += replay_mismatches(row)

    verification["passed"] = not reasons
    return {"keep": not reasons, "reasons": reasons, "verification": verification}
