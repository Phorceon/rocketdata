"""Fill the {DESIGN_JSON} and {OBSERVED} placeholders in fix prompts.

Each fix prompt gets a draft that really fails the complaint, simulated at the
prompt's conditions (seed 0), plus a one-change restoration that passes every
target and safety gate. Unfillable prompts are left untouched.

    PYTHONPATH=. .venv/bin/python -m sftgen.fill_fix
    PYTHONPATH=. .venv/bin/python -m sftgen.fill_fix --only g_rockets_bt_55__p3 --dry-run

Reads sftgen/out/prompts_v1.prefill.jsonl when that backup already exists, so a
second run repeats the same fill from the original placeholders. The first run
copies prompts_v1.jsonl there before writing.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import sys
import time
import traceback
from pathlib import Path

from pydantic import ValidationError

from sftgen import checker, contract, lint, motors, prompts, tools
from sftgen.schema import parse_design

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
PROMPTS = OUT / "prompts_v1.jsonl"
PREFILL = OUT / "prompts_v1.prefill.jsonl"
REPORT = OUT / "fill_fix_report.md"
GROUPS = OUT / "groups.json"
CONVERTED = OUT / "converted_designs.jsonl"

FT = 0.3048
NOSE = "nose weight"
SIM_BUDGET = 120
CLASS_ORDER = ["1/4A", "1/2A"] + list("ABCDEFGHIJKLMNOPQ")

# Gates a draft is allowed to break. Everything else should still pass.
IGNORE_GATES = {
    "low_margin": {"stability_rail_exit_cal"},
    "landing_fast": {"landing_ms"},
    "apogee_low": set(),
    "apogee_high": set(),
    "rail_exit_slow": {"rail_exit_ms"},
}


class BudgetError(RuntimeError):
    pass


class Search:
    """Simulation cache and a per-prompt call budget. Cached hits are free."""

    def __init__(self):
        self.cache: dict = {}
        self.used = 0
        self.calls = 0

    def reset(self):
        self.used = 0

    def _run(self, kind, design, cond):
        key = (kind, design_blob(design), json.dumps(cond, sort_keys=True))
        if key in self.cache:
            return self.cache[key]
        if self.used >= SIM_BUDGET:
            raise BudgetError(f"stopped after {SIM_BUDGET} simulations")
        self.used += 1
        self.calls += 1
        if kind == "sim":
            out = tools.call("simulate", {"design": design, "conditions": cond}, seed=0)
        else:
            out = tools.call("stability", {"design": design})
        self.cache[key] = out
        return out

    def sim(self, design, cond):
        return self._run("sim", design, cond)

    def stab(self, design):
        return self._run("stab", design, None)


def design_blob(d: dict) -> str:
    return json.dumps(d, ensure_ascii=False, separators=(", ", ": "))


def clone(d):
    return json.loads(json.dumps(d))


def conditions_of(prompt: dict) -> dict:
    """Prompt overrides on top of the site defaults, without the seed key."""
    base = {k: v for k, v in contract.DEFAULT_SIM_CONDITIONS.items() if k != "seed"}
    for k, v in (prompt.get("sim_conditions") or {}).items():
        if k in base and v is not None:
            base[k] = v
    return base


def commas(n: float) -> str:
    if abs(n - round(n)) < 1e-9:
        return f"{int(round(n)):,}"
    return f"{n:,.1f}"


def class_index(name: str | None) -> int:
    if name in CLASS_ORDER:
        return CLASS_ORDER.index(name)
    return 99


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


# ------------------------------------------------------------------- walkers


def tubes(stage):
    return [c for c in stage["components"] if c.get("type") == "bodytube"]


def longest_tube(stage):
    ts = tubes(stage)
    return max(ts, key=lambda t: t["length_m"]) if ts else None


def walk_contents(design):
    for si, st in enumerate(design["stages"]):
        for ci, c in enumerate(st["components"]):
            if c.get("type") != "bodytube":
                continue
            for xi, x in enumerate(c["contents"]):
                yield si, ci, xi, x


def fins_of(design):
    return [x for *_, x in walk_contents(design) if x.get("type") in ("trapezoidal_fins", "elliptical_fins")]


def chutes_of(design):
    return [x for *_, x in walk_contents(design) if x.get("type") == "parachute"]


def streamers_of(design):
    return [x for *_, x in walk_contents(design) if x.get("type") == "streamer"]


def masses_of(design):
    return [x for *_, x in walk_contents(design) if x.get("type") == "mass"]


def mounts_of(design):
    return [x for *_, x in walk_contents(design) if x.get("type") == "motor_mount"]


def max_diameter(design) -> float:
    best = 0.0
    for st in design["stages"]:
        for c in st["components"]:
            for k in ("diameter_m", "outer_diameter_m", "fore_diameter_m", "aft_diameter_m"):
                v = c.get(k)
                if isinstance(v, (int, float)):
                    best = max(best, float(v))
    return best


def landings(sim) -> list[float]:
    if not isinstance(sim, dict):
        return []
    out = []
    for sec in sim.get("sections") or []:
        v = sec.get("landing_ms") if isinstance(sec, dict) else None
        if isinstance(v, (int, float)) and math.isfinite(v):
            out.append(float(v))
    return out


def round_walk(obj, nd):
    if isinstance(obj, dict):
        return {k: round_walk(v, nd) for k, v in obj.items()}
    if isinstance(obj, list):
        return [round_walk(v, nd) for v in obj]
    if isinstance(obj, float):
        return round(obj, nd)
    return obj


def quantize(design, nd=5):
    q = round_walk(design, nd)
    try:
        parse_design(q)
    except (ValidationError, ValueError):
        return design
    return q


def changed_fields(a, b, prefix=""):
    rows = []
    if type(a) is not type(b):
        rows.append((prefix or "$", a, b))
        return rows
    if isinstance(a, dict):
        keys = list(dict.fromkeys(list(a) + list(b)))
        for k in keys:
            path = f"{prefix}.{k}" if prefix else k
            if k not in a or k not in b:
                rows.append((path, a.get(k, "<missing>"), b.get(k, "<missing>")))
            else:
                rows.extend(changed_fields(a[k], b[k], path))
        return rows
    if isinstance(a, list):
        if len(a) != len(b):
            rows.append((prefix or "$", f"len {len(a)}", f"len {len(b)}"))
            return rows
        for i, (x, y) in enumerate(zip(a, b)):
            rows.extend(changed_fields(x, y, f"{prefix}[{i}]"))
        return rows
    if a != b:
        rows.append((prefix or "$", a, b))
    return rows


def describe_change(draft, base) -> str:
    """What the fix does to the draft: draft value -> passing value."""
    fields = changed_fields(draft, base)
    if not fields:
        return "draft already matched the passing design"
    bits = []
    for path, old, new in fields[:6]:
        short = path.replace("stages", "s").replace("components", "c").replace("contents", "x")
        bits.append(f"{short}: {old} -> {new}")
    extra = f" (+{len(fields) - 6} more)" if len(fields) > 6 else ""
    return "; ".join(bits) + extra


# ------------------------------------------------------------------- mutations


def set_nose(design, kg: float):
    for st in design["stages"]:
        for c in tubes(st):
            c["contents"] = [x for x in c["contents"] if not (x.get("type") == "mass" and x.get("name") == NOSE)]
    if kg < 0.001:
        return design
    tube = longest_tube(design["stages"][0])
    tube["contents"].append({
        "type": "mass",
        "name": NOSE,
        "mass_kg": round(min(kg, 50.0), 4),
        "position_from_top_m": 0.0,
    })
    return design


def with_nose(design, kg: float):
    return set_nose(clone(design), kg)


def lighten_masses(design, factor: float):
    """Shrink every ballast item that is not the nose weight we add ourselves."""
    d = clone(design)
    changed = False
    for st in d["stages"]:
        for c in tubes(st):
            kept = []
            for x in c["contents"]:
                if x.get("type") == "mass" and x.get("name") != NOSE:
                    nxt = x["mass_kg"] * factor
                    if nxt < 0.002:
                        changed = True
                        continue
                    if abs(nxt - x["mass_kg"]) > 1e-6:
                        x = dict(x)
                        x["mass_kg"] = round(nxt, 4)
                        changed = True
                kept.append(x)
            c["contents"] = kept
    return d if changed else None


def ensure_recovery(design, diameter: float):
    diameter = clamp(diameter, 0.12, 6.0)
    for st in design["stages"]:
        has = False
        for c in tubes(st):
            if any(x.get("type") in ("parachute", "streamer") for x in c["contents"]):
                has = True
        if has:
            continue
        tube = longest_tube(st)
        if tube is None:
            continue
        tube["contents"].insert(0, {
            "type": "parachute",
            "diameter_m": round(diameter, 4),
            "cd": 0.8,
            "deploy_event": "apogee",
            "deploy_delay_s": 0.0,
            "material": "Polyethylene (thin)",
            "position_from_top_m": 0.0,
        })
    return design


def force_apogee_deploy(design):
    d = clone(design)
    for x in chutes_of(d) + streamers_of(d):
        x["deploy_event"] = "apogee"
        x["deploy_delay_s"] = 0.0
        x.pop("deploy_altitude_m", None)
    return d


def scale_recovery(design, factor: float, cd: float | None = None):
    d = clone(design)
    touched = False
    for p in chutes_of(d):
        nd = clamp(p["diameter_m"] * factor, 0.08, 8.0)
        if abs(nd - p["diameter_m"]) > 1e-6:
            p["diameter_m"] = round(nd, 4)
            touched = True
        if cd is not None and abs(p.get("cd", 0.8) - cd) > 1e-6:
            p["cd"] = round(cd, 3)
            touched = True
        if p["diameter_m"] >= 1.5 and p.get("material") != "Polyethylene (thin)":
            p["material"] = "Polyethylene (thin)"
            touched = True
    for s in streamers_of(d):
        nl = clamp(s["strip_length_m"] * factor, 0.1, 10.0)
        nw = clamp(s["strip_width_m"] * factor, 0.01, 1.0)
        if abs(nl - s["strip_length_m"]) > 1e-6 or abs(nw - s["strip_width_m"]) > 1e-6:
            s["strip_length_m"] = round(nl, 4)
            s["strip_width_m"] = round(nw, 4)
            touched = True
    return d if touched else None


def grow_recovery(design):
    d = clone(design)
    grew = False
    for p in chutes_of(d):
        if p["diameter_m"] < 7.5:
            p["diameter_m"] = round(min(8.0, p["diameter_m"] * 1.5), 4)
            grew = True
        elif p.get("cd", 0.8) < 2.3:
            p["cd"] = round(min(2.5, p.get("cd", 0.8) + 0.4), 3)
            grew = True
        if p["diameter_m"] >= 1.5:
            p["material"] = "Polyethylene (thin)"
    for s in streamers_of(d):
        if s["strip_length_m"] < 9.5:
            s["strip_length_m"] = round(min(10.0, s["strip_length_m"] * 1.45), 4)
            grew = True
        elif s["strip_width_m"] < 0.9:
            s["strip_width_m"] = round(min(1.0, s["strip_width_m"] * 1.45), 4)
            grew = True
    return d if grew else None


def scale_fins(design, factor: float):
    d = clone(design)
    touched = False
    for f in fins_of(d):
        if f["type"] == "trapezoidal_fins":
            span = clamp(f["span_m"] * factor, 0.005, 1.0)
            root = clamp(f["root_chord_m"] * factor, 0.01, 1.0)
            tip = clamp(f["tip_chord_m"] * factor, 0.0, root)
            sweep = clamp(f.get("sweep_m", 0.0) * factor, -0.5, 1.0)
            if abs(span - f["span_m"]) < 1e-6 and abs(root - f["root_chord_m"]) < 1e-6:
                continue
            f["span_m"] = round(span, 5)
            f["root_chord_m"] = round(root, 5)
            f["tip_chord_m"] = round(tip, 5)
            f["sweep_m"] = round(sweep, 5)
            touched = True
        else:
            span = clamp(f["span_m"] * factor, 0.005, 1.0)
            root = clamp(f["root_chord_m"] * factor, 0.01, 1.0)
            if abs(span - f["span_m"]) < 1e-6:
                continue
            f["span_m"] = round(span, 5)
            f["root_chord_m"] = round(root, 5)
            touched = True
    return d if touched else None


def shift_fins(design, offset_m: float):
    d = clone(design)
    if not fins_of(d):
        return None
    for f in fins_of(d):
        f["offset_from_aft_m"] = round(clamp(offset_m, 0.0, 1.0), 5)
    return d


def drop_one_fin(design):
    d = clone(design)
    for f in fins_of(d):
        if f["count"] > 3:
            f["count"] = int(f["count"]) - 1
            return d
    return None


# ------------------------------------------------------------------- scoring


def split_failures(design, sim, targets, cond):
    """(gate_failures, target_failures). A clean pass is both empty."""
    if not isinstance(sim, dict) or sim.get("ok") is not True:
        err = sim.get("error") if isinstance(sim, dict) else "no simulation"
        msg = f"simulate: {err}"
        return [msg], [msg]
    try:
        obj = parse_design(design)
    except (ValidationError, ValueError) as e:
        msg = f"parse: {str(e).splitlines()[0][:180]}"
        return [msg], [msg]
    gates, tgts = [], []
    for f in lint._failures(sim, targets):
        if f.name in ("apogee_m", "flight_time_s", "time_to_apogee_s") or "drift" in f.name:
            tgts.append(f"{f.name}: {f.text}")
        elif f.name == "landing_ms" and "ground_hit_ms" in targets:
            gates.append(f.text)
            tgts.append(f.text)
        else:
            gates.append(f.text)
    gates.extend(checker.design_gate_failures(obj, cond))
    tgts.extend(checker.design_target_failures(obj, {k: v for k, v in targets.items() if k != "feasible"}))
    return gates, tgts


def draft_gate_targets(targets, flaw):
    """Safety-gate targets for a draft. Altitude misses are the flaw, not a surprise."""
    out = {}
    if flaw != "landing_fast" and "ground_hit_ms" in targets:
        out["ground_hit_ms"] = targets["ground_hit_ms"]
    return out


def extra_gate_failures(design, sim, targets, cond, flaw):
    gates, _ = split_failures(design, sim, draft_gate_targets(targets, flaw), cond)
    ignore = IGNORE_GATES[flaw]
    kept = []
    for text in gates:
        # lint names the metric at the start of the message ("rail_exit_ms 9 < 15 ...").
        name = text.split(" ", 1)[0]
        if name in ignore or text.startswith("gate:recovery") and False:
            continue
        if any(text.startswith(n) or f" {n} " in f" {text} " for n in ignore):
            continue
        # landing lines look like "Sustainer landing_ms 11 > 6"
        if "landing_ms" in ignore and "landing_ms" in text:
            continue
        kept.append(text)
    return kept


def full_pass(design, sim, targets, cond) -> list[str]:
    g, t = split_failures(design, sim, targets, cond)
    return g + t


def metric_value(flaw, sim, stab):
    if flaw == "low_margin":
        if not isinstance(stab, dict) or not stab.get("ok"):
            return None
        return stab.get("static_margin_cal")
    if flaw == "landing_fast":
        lands = landings(sim)
        return max(lands) if lands else None
    if flaw == "rail_exit_slow":
        return sim.get("rail_exit_ms") if isinstance(sim, dict) else None
    if isinstance(sim, dict):
        return sim.get("apogee_m")
    return None


def in_band(flaw, value, targets) -> bool:
    if value is None or not isinstance(value, (int, float)) or not math.isfinite(value):
        return False
    if flaw == "low_margin":
        return 0.30 <= float(value) <= 0.90
    if flaw == "landing_fast":
        limit = float(targets["ground_hit_ms"]["value"])
        return float(value) + 1e-9 >= max(7.0, 1.3 * limit)
    if flaw == "apogee_low":
        t = float(targets["apogee_m"]["value"])
        return 0.60 * t - 1e-6 <= float(value) <= 0.85 * t + 1e-6
    if flaw == "apogee_high":
        t = float(targets["apogee_m"]["value"])
        return 1.10 * t - 1e-6 <= float(value) <= 1.40 * t + 1e-6
    if flaw == "rail_exit_slow":
        return 9.0 - 1e-9 <= float(value) <= 13.0 + 1e-9
    return False


def fixed_metric_ok(flaw, sim, stab, targets) -> bool:
    if flaw == "low_margin":
        return isinstance(stab, dict) and stab.get("ok") and stab.get("static_margin_cal", 0) >= 1.0
    if flaw == "landing_fast":
        lands = landings(sim)
        limit = float(targets["ground_hit_ms"]["value"])
        return bool(lands) and max(lands) <= limit + 1e-9
    if flaw == "apogee_low":
        t = float(targets["apogee_m"]["value"])
        a = sim.get("apogee_m") if isinstance(sim, dict) else None
        return isinstance(a, (int, float)) and abs(a - t) <= 0.05 * abs(t)
    if flaw == "apogee_high":
        t = float(targets["apogee_m"]["value"])
        a = sim.get("apogee_m") if isinstance(sim, dict) else None
        return isinstance(a, (int, float)) and a <= t + 1e-9
    if flaw == "rail_exit_slow":
        v = sim.get("rail_exit_ms") if isinstance(sim, dict) else None
        return isinstance(v, (int, float)) and v + 1e-9 >= contract.GATES["min_rail_exit_ms"]
    return False


# ------------------------------------------------------------------- wording


def alt_unit(text: str) -> str:
    if " km" in text or text.endswith("km") or " km." in text:
        return "km"
    stripped = text.replace("ft/s", "")
    if " ft" in stripped or " feet" in stripped:
        return "ft"
    return "m"


def person_speed(ms: float, text: str, flaw: str, targets: dict) -> str:
    use_ft = "ft/s" in text
    if use_ft:
        shown = int(round(ms / FT))
        limit = float(targets.get("ground_hit_ms", {}).get("value", 6.0))
        # Keep the sentence true: a fast landing stays above the written limit,
        # a slow rail exit stays obviously under 15 m/s (about 49 ft/s).
        if flaw == "landing_fast" and shown <= int(round(limit / FT)):
            shown = int(math.floor(limit / FT)) + 1
        if flaw == "rail_exit_slow" and shown >= 45:
            shown = int(round(ms / FT))
        return f"{shown} ft/s"
    shown = int(round(ms))
    if flaw == "landing_fast":
        limit = float(targets["ground_hit_ms"]["value"])
        if shown <= int(math.floor(limit)):
            shown = int(math.floor(limit)) + 1
    return f"{shown} m/s"


def person_altitude(meters: float, text: str, flaw: str, targets: dict) -> str:
    unit = alt_unit(text)
    bound = float(targets["apogee_m"]["value"])
    side = "below" if flaw == "apogee_low" else "above"
    if unit == "km":
        x, b = meters / 1000.0, bound / 1000.0
        step = 1.0 if x >= 8 else 0.5
        n = round(x / step) * step
        if side == "below" and n >= b - 1e-9:
            n = math.floor((b - 0.05) / step) * step
        if side == "above" and n <= b + 1e-9:
            n = math.ceil((b + 0.05) / step) * step
        n = max(step, n)
        label = f"{int(n)} km" if abs(n - round(n)) < 1e-9 else f"{n:.1f} km"
        return label
    if unit == "ft":
        x, b = meters / FT, bound / FT
        word = "ft"
    else:
        x, b = meters, bound
        word = "m"
    step = 5 if x < 80 else 10 if x < 400 else 50 if x < 2000 else 100 if x < 8000 else 500
    n = round(x / step) * step
    if side == "below" and n >= b - 1e-6:
        n = math.floor((b - 1) / step) * step
    if side == "above" and n <= b + 1e-6:
        n = math.ceil((b + 1) / step) * step
    n = max(step, n)
    return f"{commas(n)} {word}"


def person_text(flaw, value, user_text, targets) -> str:
    if flaw == "low_margin":
        shown = round(float(value), 1)
        shown = clamp(shown, 0.3, 0.9)
        return f"{shown:.1f} cal"
    if flaw in ("landing_fast", "rail_exit_slow"):
        return person_speed(float(value), user_text, flaw, targets)
    return person_altitude(float(value), user_text, flaw, targets)


# ------------------------------------------------------------------- motors


_CATALOG = None


def catalog() -> list[dict]:
    global _CATALOG
    if _CATALOG is None:
        seen = set()
        rows = []
        for group in motors._index().values():
            for jm in group:
                des = str(jm.getDesignation())
                manu = str(jm.getManufacturer().getDisplayName())
                key = (des, manu)
                if key in seen:
                    continue
                seen.add(key)
                rows.append(motors._describe(jm))
        _CATALOG = rows
    return _CATALOG


def motor_candidates(mount_id, length_max, impulse_lo, impulse_hi, class_max, prefer_manu=None, limit=5):
    found = []
    for info in catalog():
        if info["diameter_m"] > mount_id + 1e-4:
            continue
        if info["length_m"] > length_max + 1e-4:
            continue
        if not (impulse_lo <= info["total_impulse_ns"] <= impulse_hi):
            continue
        if class_max and class_index(info["class"]) > class_index(class_max):
            continue
        found.append(info)
    mid = (impulse_lo + impulse_hi) / 2

    def key(info):
        same = 0 if prefer_manu and prefer_manu.split()[0] in info["manufacturer"] else 1
        return (same, abs(info["total_impulse_ns"] - mid), -info["average_thrust_n"], info["designation"])

    found.sort(key=key)
    out, seen = [], set()
    for info in found:
        if info["designation"] in seen:
            continue
        seen.add(info["designation"])
        out.append(info)
        if len(out) == limit:
            break
    return out


def class_max_of(targets) -> str | None:
    t = targets.get("motor_class")
    if isinstance(t, dict) and t.get("kind") == "max":
        return t.get("value")
    return None


def set_stage_motor(design, stage_index, info):
    """Swap the single mount on one stage. Returns None if the motor will not fit."""
    d = clone(design)
    st = d["stages"][stage_index]
    mounts = []
    for c in tubes(st):
        for x in c["contents"]:
            if x.get("type") == "motor_mount":
                mounts.append((c, x))
    if len(mounts) != 1:
        return None
    tube, mount = mounts[0]
    mid = mount["outer_diameter_m"] - 2 * mount["wall_thickness_m"]
    if info["diameter_m"] > mid + 1e-4:
        return None
    if info["length_m"] > tube["length_m"] + 1e-4:
        return None
    mount["motor"]["designation"] = info["designation"]
    mount["motor"]["manufacturer"] = info["manufacturer"]
    return d


def resolve_ref_motor(entry: dict, prompt: dict):
    """Pinned-DB motor for a reference stage entry, honouring an exact-motor keep."""
    keep = prompt["fix_spec"].get("keep") or []
    if "motor" in keep:
        values = prompt["targets"].get("motor", {}).get("value") or []
        if len(values) == 1:
            return motors.resolve(values[0])
    try:
        return motors.resolve(entry["designation"], entry.get("manufacturer"))
    except motors.UnknownMotor:
        pass
    canon = prompts.canonical_motor(entry)
    if canon is None:
        return None
    return motors.resolve(canon["designation"], canon["manufacturer"])


# ------------------------------------------------------------------- synthesis


def top_first(stages: list[dict]) -> list[dict]:
    if len(stages) <= 1:
        return list(stages)
    names = [s["stage"].lower() for s in stages]

    def topish(n):
        return any(k in n for k in ("sustain", "dart", "payload", "upper"))

    def botish(n):
        return "boost" in n

    if botish(names[0]) or topish(names[-1]):
        return list(reversed(stages))
    if topish(names[0]) or botish(names[-1]):
        return list(stages)
    ign = (stages[0]["motors"][0].get("ignition") or "")
    if ign in ("automatic", "launch"):
        return list(reversed(stages))
    return list(stages)


def body_size(mounts: list[tuple[dict, int]], prefer: float):
    """(outer_diameter, wall) large enough for the mounts and close to prefer."""
    need_id = 0.0
    groups = []
    for info, count in mounts:
        count = int(clamp(count, 1, 4))
        od = info["diameter_m"] + 0.0012
        span = od * {1: 1.0, 2: 2.0, 3: 2.155, 4: 2.414}[count]
        groups.append(span)
        need_id = max(need_id, span)
    if len(groups) > 1:
        need_id = max(need_id, sum(groups) * 1.05)
    wall = 0.001 if (prefer or 0) < 0.08 else 0.0015
    min_od = need_id + 2 * wall
    od = max(prefer or 0.0, min_od, 0.014)
    od = min(od, 0.39)
    if od - 2 * wall < need_id:
        wall = max(0.0004, (od - need_id) / 2)
    return round(od, 5), round(wall, 5)


def synthesize(prompt: dict):
    ref = prompt["reference"]
    stages = ref["motors_by_stage"]
    if ref.get("parallel_boosters") or any(s.get("kind") == "parallel" for s in stages):
        entries = [m for s in stages for m in s["motors"]]
        ordered = [{"stage": "Sustainer", "motors": entries}]
    else:
        ordered = top_first(stages)
    if len(ordered) != int(ref["stage_count"]) and not (
        ref.get("parallel_boosters") or any(s.get("kind") == "parallel" for s in stages)
    ):
        # Still build what the motor list describes; stage_count is the reference's.
        pass
    prefer = ref.get("max_body_diameter_m") or 0.025
    prefer = clamp(float(prefer), 0.014, 0.39)
    built = []
    for st in ordered:
        infos = []
        for entry in st["motors"]:
            info = resolve_ref_motor(entry, prompt)
            if info is None:
                return None, f"motor {entry.get('designation')!r} is not in the pinned database"
            count = int(entry.get("count") or 1)
            if count < 1 or count > 4:
                return None, f"cluster of {count} is outside the schema (1-4)"
            infos.append((info, count))
        if not infos:
            return None, "a stage has no motors"
        od, wall = body_size(infos, prefer)
        motor_len = max(i["length_m"] for i, _ in infos)
        # Several calibers of airframe ahead of the motor keep the CG forward of the CP.
        # A tube that is only as long as the motor is a lawn dart.
        ahead = max(0.08, min(od * 5.0, 0.5))
        tube_len = max(motor_len + ahead, od * 8.0, 0.22)
        tube_len = clamp(tube_len, motor_len + 0.01, 4.0)
        est_mass = sum(i["loaded_mass_kg"] * c for i, c in infos) * 1.8 + 0.05
        built.append({
            "name": st["stage"], "infos": infos, "od": od, "wall": wall,
            "tube": round(tube_len, 4), "chute": round(chute_guess(est_mass, 5.0), 3),
        })

    rocket_name = prompt["group_id"][:60]
    stages_out = []
    prev_aft = None
    for i, b in enumerate(built):
        is_top = i == 0
        is_bottom = i == len(built) - 1
        comps = []
        if is_top:
            nose_d = b["od"]
            comps.append({
                "type": "nosecone",
                "shape": "ogive",
                "length_m": round(clamp(b["od"] * 2.4, 0.05, 0.45), 4),
                "diameter_m": nose_d,
                "wall_thickness_m": 0.002,
                "material": "Polystyrene",
                "shoulder_length_m": round(clamp(b["od"] * 0.35, 0.01, 0.06), 4),
            })
        elif prev_aft is not None and abs(prev_aft - b["od"]) > 0.0005:
            comps.append({
                "type": "transition",
                "shape": "conical",
                "length_m": round(clamp(abs(prev_aft - b["od"]) * 2.5, 0.02, 0.25), 4),
                "fore_diameter_m": prev_aft,
                "aft_diameter_m": b["od"],
                "wall_thickness_m": 0.002,
                "material": "Cardboard",
            })
        contents = []
        # One chute per stage, sized later from the simulated mass.
        contents.append({
            "type": "parachute",
            "diameter_m": b["chute"],
            "cd": 0.8,
            "deploy_event": "apogee",
            "deploy_delay_s": 0.0,
            "material": "Polyethylene (thin)" if b["chute"] >= 1.2 else "Ripstop nylon",
            "position_from_top_m": 0.0,
        })
        for info, count in b["infos"]:
            mount_od = round(info["diameter_m"] + 0.0012, 5)
            mount_wall = 0.0004
            body_id = b["od"] - 2 * b["wall"]
            if count == 1 and mount_od > body_id:
                mount_od = round(body_id - 0.0002, 5)
            span = mount_od * {1: 1.0, 2: 2.0, 3: 2.155, 4: 2.414}[count]
            if span > body_id + 1e-6:
                return None, (
                    f"a {count}-motor {info['designation']} mount does not fit a "
                    f"{b['od'] * 1000:.0f} mm tube"
                )
            rings = 2 if count == 1 and body_id - mount_od > 0.0015 else 0
            contents.append({
                "type": "motor_mount",
                "outer_diameter_m": mount_od,
                "length_m": round(min(b["tube"], max(info["length_m"], 0.05)), 4),
                "wall_thickness_m": mount_wall,
                "material": "Cardboard",
                "motor": {
                    "manufacturer": info["manufacturer"],
                    "designation": info["designation"],
                    "delay_s": None,
                    "ignition_delay_s": 0.0,
                },
                "cluster_count": count,
                "overhang_m": 0.0,
                "centering_ring_count": rings,
                "centering_ring_material": "Cardboard",
            })
        span = round(clamp(b["od"] * 1.7, 0.025, 0.2), 4)
        root = round(clamp(b["od"] * 2.2, 0.035, 0.3), 4)
        contents.append({
            "type": "trapezoidal_fins",
            "count": 4 if b["od"] >= 0.05 else 3,
            "root_chord_m": root,
            "tip_chord_m": round(root * 0.45, 4),
            "span_m": span,
            "sweep_m": round(root * 0.3, 4),
            "thickness_m": 0.003 if b["od"] >= 0.08 else 0.0016,
            "material": "Balsa",
            "offset_from_aft_m": 0.0,
        })
        stage_name = "Sustainer" if is_top else ("Booster" if is_bottom and len(built) == 2 else f"Stage {i + 1}")
        if not is_top and "boost" in b["name"].lower():
            stage_name = b["name"][:40]
        stage = {"name": stage_name[:40], "components": comps + [{
            "type": "bodytube",
            "name": "Body tube",
            "length_m": b["tube"],
            "outer_diameter_m": b["od"],
            "wall_thickness_m": b["wall"],
            "material": "Cardboard",
            "contents": contents,
        }]}
        if not is_top:
            stage["separation_event"] = "burnout"
            stage["separation_delay_s"] = 0.0
        stages_out.append(stage)
        prev_aft = b["od"]
    design = {"name": rocket_name, "stages": stages_out}
    try:
        parse_design(design)
    except (ValidationError, ValueError) as e:
        return None, f"synthesized design failed schema: {str(e).splitlines()[0][:200]}"
    return design, None


# ------------------------------------------------------------------- search


def chute_guess(mass_kg: float, v_ms: float = 5.0) -> float:
    """Canopy diameter whose equilibrium descent is about v_ms."""
    m = max(mass_kg, 0.05)
    v = max(float(v_ms), 2.5)
    d = math.sqrt(8 * m * 9.81 / (math.pi * 1.22 * 0.75 * v * v))
    return clamp(d, 0.12, 6.5)


def nose_mass(design) -> float:
    return sum(m["mass_kg"] for m in masses_of(design) if m.get("name") == NOSE)


def landing_limit_of(targets) -> float:
    t = targets.get("ground_hit_ms")
    if isinstance(t, dict) and isinstance(t.get("value"), (int, float)):
        return float(t["value"])
    return float(contract.GATES["default_max_landing_ms"])


def fin_material_lighten(design):
    """Heavy fins at the tail drag the CG back and can make a bigger fin less stable."""
    d = clone(design)
    changed = False
    for f in fins_of(d):
        if f.get("material") not in ("Balsa", "Basswood"):
            f["material"] = "Balsa"
            changed = True
        if f.get("thickness_m", 0) > 0.004:
            f["thickness_m"] = 0.003
            changed = True
    return d if changed else None


def set_chute_diameter(design, diameter, cd=None):
    d = clone(design)
    ensure_recovery(d, diameter)
    for p in chutes_of(d):
        p["diameter_m"] = round(clamp(diameter, 0.08, 8.0), 4)
        p["deploy_event"] = "apogee"
        p["deploy_delay_s"] = 0.0
        p.pop("deploy_altitude_m", None)
        if p["diameter_m"] >= 1.2:
            p["material"] = "Polyethylene (thin)"
        if cd is not None:
            p["cd"] = round(clamp(cd, 0.3, 2.5), 3)
    return d


def motor_not_kept(prompt) -> bool:
    return "motor" not in (prompt["fix_spec"].get("keep") or [])


def stage_mounts(design, si):
    found = []
    for c in tubes(design["stages"][si]):
        for x in c["contents"]:
            if x.get("type") == "motor_mount":
                found.append((c, x))
    return found


def impulse_options(design, factors, class_max):
    """Single-mount motor swaps near each impulse factor. Top stage first."""
    out, seen = [], set()
    order = list(range(len(design["stages"])))
    for si in order:
        mounts = stage_mounts(design, si)
        if len(mounts) != 1:
            continue
        tube, mount = mounts[0]
        try:
            cur = motors.resolve(mount["motor"]["designation"], mount["motor"].get("manufacturer"))
        except motors.UnknownMotor:
            continue
        mid = mount["outer_diameter_m"] - 2 * mount["wall_thickness_m"]
        for factor in factors:
            lo = cur["total_impulse_ns"] * factor * 0.82
            hi = cur["total_impulse_ns"] * factor * 1.18
            for info in motor_candidates(mid, tube["length_m"], lo, hi, class_max, cur["manufacturer"], limit=3):
                if info["designation"] == cur["designation"] and info["manufacturer"] == cur["manufacturer"]:
                    continue
                d = set_stage_motor(design, si, info)
                if d is None:
                    continue
                key = (si, info["designation"], info["manufacturer"])
                if key in seen:
                    continue
                seen.add(key)
                out.append(d)
                if len(out) >= 10:
                    return out
    return out


def hotter_motors(design, class_max, limit=3):
    """Same-class-ish motors with more thrust, so a sluggish rocket can clear the rail.

    The bottom stage is tried first: that is the motor that is burning at liftoff.
    """
    out, seen = [], set()
    order = list(range(len(design["stages"]) - 1, -1, -1))
    for si in order:
        mounts = stage_mounts(design, si)
        if len(mounts) != 1:
            continue
        tube, mount = mounts[0]
        try:
            cur = motors.resolve(mount["motor"]["designation"], mount["motor"].get("manufacturer"))
        except motors.UnknownMotor:
            continue
        mid_id = mount["outer_diameter_m"] - 2 * mount["wall_thickness_m"]
        cands = []
        for info in catalog():
            if info["diameter_m"] > mid_id + 1e-4:
                continue
            if info["length_m"] > tube["length_m"] + 1e-4:
                continue
            if class_max and class_index(info["class"]) > class_index(class_max):
                continue
            if info["average_thrust_n"] < cur["average_thrust_n"] * 1.3:
                continue
            if not (cur["total_impulse_ns"] * 0.55 <= info["total_impulse_ns"] <= cur["total_impulse_ns"] * 1.7):
                continue
            if info["designation"] == cur["designation"]:
                continue
            cands.append(info)
        cands.sort(key=lambda i: (
            abs(i["total_impulse_ns"] - cur["total_impulse_ns"]) / max(cur["total_impulse_ns"], 1.0),
            -i["average_thrust_n"],
            i["designation"],
        ))
        for info in cands:
            d = set_stage_motor(design, si, info)
            if d is None:
                continue
            key = (si, info["designation"], info["manufacturer"])
            if key in seen:
                continue
            seen.add(key)
            out.append(d)
            if len(out) >= limit:
                return out
    return out


def _gate_bad(design, sim, targets, cond):
    """Safety-gate texts, ignoring altitude targets. A clean flight is an empty list."""
    if not sim.get("ok"):
        return [f"simulate: {sim.get('error')}"]
    gates, _ = split_failures(design, sim, draft_gate_targets(targets, "apogee_low"), cond)
    return [t for t in gates if not (t.startswith("apogee") or "apogee_m" in t[:12])]


def repair(search: Search, design, cond, targets):
    """Fins, nose weight, ballast and recovery until the safety gates pass.

    Altitude targets are allowed to miss; the flaw search tunes those.
    Stability is fixed before recovery, because a lawn dart never deploys a chute.
    Fins are lightened before they are grown: plywood at the tail can move the CG
    back faster than the extra area moves the CP.
    """
    d = clone(design)
    ensure_recovery(d, 0.35)
    last = "no simulation"
    seen = set()
    for _ in range(16):
        key = design_blob(d)
        if key in seen:
            return None, f"safety repair stalled ({last})"
        seen.add(key)
        sim = search.sim(d, cond)
        if not sim.get("ok"):
            if "deploy" in str(sim.get("error", "")).lower():
                d = force_apogee_deploy(d)
                continue
            return None, f"simulation failed: {sim.get('error')}"
        bad = _gate_bad(d, sim, targets, cond)
        if not bad:
            return d, None
        last = "; ".join(bad[:4])
        blob = " ".join(bad)
        margin = sim.get("stability_rail_exit_cal")
        burn = sim.get("min_stability_burn_cal")
        mass = float(sim.get("liftoff_mass_kg") or 0.3)
        unstable = (
            (isinstance(margin, (int, float)) and margin < 1.0)
            or (isinstance(burn, (int, float)) and burn <= 0.0)
        )
        if unstable:
            light = fin_material_lighten(d)
            if light is not None and design_blob(light) not in seen:
                d = light
                continue
            spans = [f["span_m"] for f in fins_of(d)]
            od = max_diameter(d) or 0.04
            if spans and max(spans) < max(od * 1.8, 0.06):
                grown = scale_fins(d, 1.3)
                if grown is not None and design_blob(grown) not in seen:
                    d = grown
                    continue
            if nose_mass(d) > 0.4 * mass:
                return None, "nose weight is already large and the margin is still under 1 caliber"
            d = with_nose(d, nose_mass(d) + max(0.02, round(mass * 0.07, 4)))
            continue
        if "rail_exit" in blob or "thrust_to_weight" in blob or "thrust-to-weight" in blob:
            if nose_mass(d) >= 0.01:
                d = with_nose(d, nose_mass(d) * 0.5)
                continue
            lighter = lighten_masses(d, 0.45)
            if lighter is not None and design_blob(lighter) not in seen:
                d = lighter
                continue
            return None, "rail exit or thrust-to-weight stays under the gate after removing ballast"
        if "recovery" in blob.lower() and ("not deployed" in blob or "no parachute" in blob):
            nxt = force_apogee_deploy(d)
            if design_blob(nxt) != design_blob(d):
                d = nxt
                continue
            ensure_recovery(d, chute_guess(mass, landing_limit_of(targets)))
            if design_blob(d) in seen:
                return None, "recovery never deploys"
            continue
        if "landing_ms" in blob:
            limit = landing_limit_of(targets)
            guess = chute_guess(mass, max(limit * 0.8, 3.2))
            current = max((p["diameter_m"] for p in chutes_of(d)), default=0.15)
            nxt_d = set_chute_diameter(d, max(guess, current * 1.45))
            new_d = max((p["diameter_m"] for p in chutes_of(nxt_d)), default=0.0)
            if new_d <= current + 0.01 or design_blob(nxt_d) in seen:
                cd = max((p.get("cd", 0.8) for p in chutes_of(d)), default=0.8)
                if cd >= 2.3:
                    return None, "recovery is already as large as the schema allows and landing is still hard"
                nxt_d = set_chute_diameter(d, current, cd=min(2.5, cd + 0.45))
            d = nxt_d
            continue
        return None, f"unhandled safety failure: {last}"
    return None, f"safety repair did not converge ({last})"


def mass_series(search: Search, design, cond):
    """Nose-weight sweep, stopped once the rocket is clearly too heavy to fly higher."""
    masses = [0.0, 0.02, 0.05, 0.1, 0.2, 0.4, 0.8, 1.5, 3.0, 6.0, 10.0, 18.0, 30.0, 45.0]
    rows = []
    prev_apo = None
    for m in masses:
        d = with_nose(design, m)
        sim = search.sim(d, cond)
        rows.append((m, d, sim))
        if not sim.get("ok"):
            continue
        apo = sim.get("apogee_m")
        rail = sim.get("rail_exit_ms") or 0
        tw = sim.get("thrust_to_weight") or 0
        if prev_apo and apo and apo < prev_apo * 0.98 and apo < 30 and rail < 10:
            break
        if tw and tw < 2.5 and rail < 8:
            break
        prev_apo = apo or prev_apo
    return rows


def bisect_mass(search: Search, design, cond, lo, hi, ok):
    best = None
    for _ in range(6):
        mid = round((lo + hi) / 2, 4)
        d = with_nose(design, mid)
        sim = search.sim(d, cond)
        if not sim.get("ok"):
            break
        state = ok(sim)
        if state == "good":
            return mid, d, sim
        if state == "high":
            lo = mid
            best = (mid, d, sim)
        elif state == "low":
            hi = mid
        else:
            break
        if hi - lo < 0.01:
            break
    return best


def passing_base(search: Search, design, cond, targets, prompt=None, _motor_try=True):
    """Ancestor that passes every target and gate, using nose weight as the tuner."""
    ancestor, err = repair(search, design, cond, targets)
    if ancestor is None:
        return None, err
    # Size the chute for the repaired mass before the altitude search.
    sim0 = search.sim(ancestor, cond)
    if sim0.get("ok") and sim0.get("liftoff_mass_kg"):
        sized = scale_recovery(ancestor, 1.0)  # no-op, just to have chutes
        guess = chute_guess(float(sim0["liftoff_mass_kg"]), landing_limit_of(targets) * 0.85)
        for chute in chutes_of(ancestor):
            if chute["diameter_m"] < guess:
                chute["diameter_m"] = round(min(guess, 6.5), 4)
                if chute["diameter_m"] >= 1.2:
                    chute["material"] = "Polyethylene (thin)"

    def acceptable(sim, d):
        return not full_pass(d, sim, targets, cond)

    rows = mass_series(search, ancestor, cond)
    good = [(m, d, sim) for m, d, sim in rows if sim.get("ok") and acceptable(sim, d)]
    if good:
        # Least added weight that already passes.
        return min(good, key=lambda r: r[0])[1], None

    t = targets.get("apogee_m")
    if not t:
        # No altitude target: the miss is something the mass sweep did not fix.
        fails = []
        if rows and rows[0][2].get("ok"):
            fails = full_pass(rows[0][1], rows[0][2], targets, cond)
        return None, "no design on the mass sweep passes: " + "; ".join(fails[:4])

    def state_of(sim):
        if not sim.get("ok"):
            return "bad"
        a = sim.get("apogee_m")
        if not isinstance(a, (int, float)):
            return "bad"
        v = float(t["value"])
        if t["kind"] == "max":
            return "high" if a > v else "good"
        if t["kind"] == "min":
            return "low" if a < v else "good"
        if abs(a - v) <= 0.05 * abs(v):
            return "good"
        return "high" if a > v else "low"

    # Bisect between a too-high point and a too-low point.
    high = [(m, d, sim) for m, d, sim in rows if state_of(sim) == "high"]
    low = [(m, d, sim) for m, d, sim in rows if state_of(sim) == "low"]
    if high and low and high[0][0] < low[-1][0]:
        # More mass lowers apogee: bracket (last high, first low after it).
        lo_m = high[-1][0]
        hi_candidates = [m for m, _, sim in low if m > lo_m]
        if hi_candidates:
            found = bisect_mass(search, ancestor, cond, lo_m, hi_candidates[0], state_of)
            if found and state_of(found[2]) == "good":
                d = found[1]
                if acceptable(found[2], d):
                    return d, None
                # In the altitude window but a gate failed. Grow the chute and retry once.
                grown = grow_recovery(ancestor)
                if grown is not None:
                    simg = search.sim(with_nose(grown, found[0]), cond)
                    if simg.get("ok") and acceptable(simg, with_nose(grown, found[0])):
                        return with_nose(grown, found[0]), None
                    if simg.get("ok") and state_of(simg) == "good":
                        return None, "altitude is in range but gates still fail: " + "; ".join(
                            full_pass(with_nose(grown, found[0]), simg, targets, cond)[:4])
    # Altitude never entered the window. A larger motor is a fair base when the
    # reference motor cannot reach the target and the prompt does not keep it.
    a0 = rows[0][2].get("apogee_m") if rows and rows[0][2].get("ok") else None
    t = targets.get("apogee_m")
    short = False
    if t and isinstance(a0, (int, float)):
        want = float(t["value"])
        if t["kind"] == "about":
            short = a0 < want * 0.95
        elif t["kind"] == "min":
            short = a0 < want
    if short and _motor_try and prompt is not None and motor_not_kept(prompt):
        for alt in impulse_options(ancestor, (1.3, 1.7, 2.2, 2.8), class_max_of(targets)):
            got, _err = passing_base(search, alt, cond, targets, prompt=prompt, _motor_try=False)
            if got is not None:
                return got, None
    if isinstance(a0, (int, float)):
        return None, f"could not put apogee on the target (lightest design reaches {a0} m)"
    err = rows[0][2].get("error") if rows else "no simulations"
    return None, f"base simulations failed: {err}"


def consider(best, cand):
    """Prefer a clean gate list, then the earlier (smaller) change."""
    if cand is None:
        return best
    if best is None:
        return cand
    if len(cand["extra"]) < len(best["extra"]):
        return cand
    return best


def finish_pair(search: Search, draft, base, prompt, cond, targets, flaw):
    """Quantize, re-simulate, and require the flaw plus a real fix."""
    for nd in (5, 6, None):
        dq = quantize(draft, nd) if nd else draft
        bq = quantize(base, nd) if nd else base
        dsim = search.sim(dq, cond)
        dstab = search.stab(dq) if flaw == "low_margin" else None
        dval = metric_value(flaw, dsim, dstab)
        if not in_band(flaw, dval, targets):
            continue
        dextra = extra_gate_failures(dq, dsim, targets, cond, flaw)
        bsim = search.sim(bq, cond)
        bstab = search.stab(bq) if flaw == "low_margin" else None
        if not fixed_metric_ok(flaw, bsim, bstab, targets):
            continue
        fails = full_pass(bq, bsim, targets, cond)
        if fails:
            continue
        return {
            "draft": dq,
            "base": bq,
            "observed_value": dval,
            "observed_text": person_text(flaw, dval, prompt["user_text"], targets),
            "change": describe_change(dq, bq),
            "fix_value": metric_value(flaw, bsim, bstab),
            "extra": dextra,
            "base_sim": bsim,
        }
    return None


def solve_landing(search, base, prompt, cond, targets):
    best = None
    # Shrink recovery from the passing (soft-landing) base. Mild cuts first.
    factors = [0.8, 0.65, 0.5, 0.4, 0.3, 0.22, 0.16, 0.12]
    cds = [None, 0.45, 0.32]
    for cd in cds:
        for factor in factors:
            d = scale_recovery(base, factor, cd=cd)
            if d is None:
                continue
            sim = search.sim(d, cond)
            val = metric_value("landing_fast", sim, None)
            if not in_band("landing_fast", val, targets):
                continue
            extra = extra_gate_failures(d, sim, targets, cond, "landing_fast")
            cand = {"design": d, "extra": extra, "value": val}
            if not extra:
                pair = finish_pair(search, d, base, prompt, cond, targets, "landing_fast")
                if pair:
                    return pair
            best = consider(best, cand)
            if cd is None and not extra:
                break
        if best and not best["extra"]:
            break
    if best:
        pair = finish_pair(search, best["design"], base, prompt, cond, targets, "landing_fast")
        if pair:
            return pair
    return None, "no smaller chute lands hard enough while the enlarged chute still passes"


def solve_margin(search, base, prompt, cond, targets):
    best = None
    # Forgotten nose weight is a one-number change and leaves the fins alone.
    cur = nose_mass(base)
    if cur >= 0.015:
        lo, hi = 0.0, cur
        for _ in range(7):
            if hi - lo < 0.008:
                break
            mid = round((lo + hi) / 2, 4)
            d = with_nose(base, mid)
            stab = search.stab(d)
            val = metric_value("low_margin", None, stab)
            if in_band("low_margin", val, targets):
                sim = search.sim(d, cond)
                extra = extra_gate_failures(d, sim, targets, cond, "low_margin")
                if any("min_stability_burn" in e or "margin must stay" in e for e in extra):
                    lo = mid
                    continue
                best = consider(best, {"design": d, "extra": extra})
                if not extra:
                    pair = finish_pair(search, d, base, prompt, cond, targets, "low_margin")
                    if pair:
                        return pair
                lo = mid
            else:
                shown = stab.get("static_margin_cal") if isinstance(stab, dict) else None
                if isinstance(shown, (int, float)) and shown > 0.9:
                    hi = mid
                else:
                    lo = mid
    scales = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.32, 0.25, 0.18]
    for sc in scales:
        d = scale_fins(base, sc)
        if d is None:
            continue
        stab = search.stab(d)
        val = metric_value("low_margin", None, stab)
        if not in_band("low_margin", val, targets):
            continue
        sim = search.sim(d, cond)
        extra = extra_gate_failures(d, sim, targets, cond, "low_margin")
        if any("min_stability_burn" in e or "margin must stay" in e for e in extra):
            continue
        cand = {"design": d, "extra": extra}
        if not extra:
            pair = finish_pair(search, d, base, prompt, cond, targets, "low_margin")
            if pair:
                return pair
        best = consider(best, cand)
    # Sliding the fins forward, span left alone.
    for offset in (0.02, 0.04, 0.07, 0.1, 0.15, 0.22, 0.3, 0.4):
        d = shift_fins(base, offset)
        if d is None:
            continue
        stab = search.stab(d)
        val = metric_value("low_margin", None, stab)
        if not in_band("low_margin", val, targets):
            continue
        sim = search.sim(d, cond)
        extra = extra_gate_failures(d, sim, targets, cond, "low_margin")
        if any("min_stability_burn" in e or "margin must stay" in e for e in extra):
            continue
        cand = {"design": d, "extra": extra}
        if not extra:
            pair = finish_pair(search, d, base, prompt, cond, targets, "low_margin")
            if pair:
                return pair
        best = consider(best, cand)
    fewer = drop_one_fin(base)
    if fewer is not None:
        stab = search.stab(fewer)
        val = metric_value("low_margin", None, stab)
        if in_band("low_margin", val, targets):
            sim = search.sim(fewer, cond)
            extra = extra_gate_failures(fewer, sim, targets, cond, "low_margin")
            best = consider(best, {"design": fewer, "extra": extra})
    # The discrete scales can step over 0.3–0.9 cal. Bisect between them.
    lo, hi = 0.15, 0.92
    for _ in range(6):
        mid = round((lo + hi) / 2, 3)
        d = scale_fins(base, mid)
        if d is None:
            break
        stab = search.stab(d)
        val = metric_value("low_margin", None, stab)
        if in_band("low_margin", val, targets):
            sim = search.sim(d, cond)
            extra = extra_gate_failures(d, sim, targets, cond, "low_margin")
            if not any("min_stability_burn" in e or "margin must stay" in e for e in extra):
                best = consider(best, {"design": d, "extra": extra})
                if not extra:
                    pair = finish_pair(search, d, base, prompt, cond, targets, "low_margin")
                    if pair:
                        return pair
            lo = mid
        else:
            shown = stab.get("static_margin_cal") if isinstance(stab, dict) else None
            if isinstance(shown, (int, float)) and shown > 0.9:
                hi = mid
            else:
                lo = mid
        if hi - lo < 0.03:
            break
    if best:
        pair = finish_pair(search, best["design"], base, prompt, cond, targets, "low_margin")
        if pair:
            return pair
    return None, "could not put the static margin between 0.3 and 0.9 cal without losing the rest of the design"


def solve_by_mass(search, ancestor, prompt, cond, targets, flaw, band_fn, base_fn):
    """One nose-weight sweep. band_fn/base_fn(sim) -> bool, ignoring gates."""
    rows = mass_series(search, ancestor, cond)
    draft_c = None
    base_c = None
    for m, d, sim in rows:
        if not sim.get("ok"):
            continue
        if base_c is None and base_fn(sim) and not full_pass(d, sim, targets, cond):
            base_c = (m, d, sim)
        if draft_c is None and band_fn(sim):
            extra = extra_gate_failures(d, sim, targets, cond, flaw)
            draft_c = (m, d, sim, extra)
            if not extra and base_c and m != base_c[0]:
                break
    # Finer bracket for the draft band if the grid stepped over it.
    if draft_c is None and len(rows) >= 2:
        tval = float(targets["apogee_m"]["value"])
        for (m0, _, s0), (m1, _, s1) in zip(rows, rows[1:]):
            if not s0.get("ok") or not s1.get("ok"):
                continue
            a0, a1 = s0.get("apogee_m"), s1.get("apogee_m")
            if not isinstance(a0, (int, float)) or not isinstance(a1, (int, float)):
                continue
            lo, hi = (0.60 * tval, 0.85 * tval) if flaw == "apogee_low" else (1.10 * tval, 1.40 * tval)
            if (a0 - lo) * (a1 - lo) < 0 or (a0 - hi) * (a1 - hi) < 0 or (lo <= a0 <= hi) != (lo <= a1 <= hi):
                for _ in range(5):
                    mid = round((m0 + m1) / 2, 4)
                    d = with_nose(ancestor, mid)
                    sim = search.sim(d, cond)
                    if not sim.get("ok"):
                        break
                    if band_fn(sim):
                        draft_c = (mid, d, sim, extra_gate_failures(d, sim, targets, cond, flaw))
                        break
                    a = sim.get("apogee_m")
                    # Heavier is lower. If still above the band, add mass.
                    if isinstance(a, (int, float)) and a > hi:
                        m0 = mid
                    else:
                        m1 = mid
                if draft_c:
                    break
    if draft_c is None:
        return None, "no nose weight put the observed metric in the required band"
    if base_c is None:
        return None, "no nose weight on this airframe passes every target and gate"
    if abs(draft_c[0] - base_c[0]) < 1e-4:
        return None, "the failing draft and the passing design need the same nose weight"
    # Prefer a draft whose other gates are clean; the masses above may not be.
    if draft_c[3]:
        for m, d, sim in rows:
            if not sim.get("ok") or abs(m - base_c[0]) < 1e-4:
                continue
            if not band_fn(sim):
                continue
            extra = extra_gate_failures(d, sim, targets, cond, flaw)
            if len(extra) < len(draft_c[3]):
                draft_c = (m, d, sim, extra)
            if not extra:
                break
    pair = finish_pair(search, draft_c[1], base_c[1], prompt, cond, targets, flaw)
    if pair:
        return pair
    return None, "the mass pair left the band once the designs were rounded, or the fix stopped passing"


def solve_apogee(search, base_design, prompt, cond, targets, flaw):
    t = float(targets["apogee_m"]["value"])

    def band(sim):
        return in_band(flaw, sim.get("apogee_m"), targets)

    def base_ok(sim):
        a = sim.get("apogee_m")
        if not isinstance(a, (int, float)):
            return False
        if flaw == "apogee_low":
            return abs(a - t) <= 0.05 * abs(t)
        return a <= t + 1e-9

    pair = solve_by_mass(search, base_design, prompt, cond, targets, flaw, band, base_ok)
    if not isinstance(pair, tuple):
        return pair
    # A heavier draft lands harder. Size the canopy for that mass and sweep again,
    # so the only difference between draft and fix is still the nose weight.
    sim0 = search.sim(base_design, cond)
    a0 = sim0.get("apogee_m") if sim0.get("ok") else None
    if sim0.get("ok") and sim0.get("liftoff_mass_kg"):
        heavy = float(sim0["liftoff_mass_kg"]) * 1.35
        sized = set_chute_diameter(base_design, chute_guess(heavy, landing_limit_of(targets) * 0.8))
        if design_blob(sized) != design_blob(base_design):
            again = solve_by_mass(search, sized, prompt, cond, targets, flaw, band, base_ok)
            if not isinstance(again, tuple):
                return again
    if not motor_not_kept(prompt):
        return pair
    reason = pair[1]
    class_max = class_max_of(targets)
    # Short of the target: put a larger motor on the same airframe, then use nose
    # weight so the fix hits the target and the draft falls in the low band.
    if flaw == "apogee_low" and isinstance(a0, (int, float)) and a0 < t * 0.95:
        stripped = lighten_masses(base_design, 0.0)
        if stripped is not None:
            got = solve_by_mass(search, stripped, prompt, cond, targets, flaw, band, base_ok)
            if not isinstance(got, tuple):
                return got
        for alt in impulse_options(base_design, (1.25, 1.6, 2.1, 2.8), class_max):
            fixed, _ferr = repair(search, alt, cond, targets)
            if fixed is None:
                continue
            got = solve_by_mass(search, fixed, prompt, cond, targets, flaw, band, base_ok)
            if not isinstance(got, tuple):
                return got
    # Already under the waiver: a hotter motor is the draft, the current rocket is the fix.
    if flaw == "apogee_high" and isinstance(a0, (int, float)) and a0 <= t:
        for alt in impulse_options(base_design, (1.15, 1.45, 1.8), class_max):
            sim = search.sim(alt, cond)
            if not sim.get("ok") or not band(sim):
                continue
            if extra_gate_failures(alt, sim, targets, cond, flaw):
                continue
            if full_pass(base_design, sim0, targets, cond):
                continue
            got = finish_pair(search, alt, base_design, prompt, cond, targets, flaw)
            if got:
                return got
    # In the high band already: a milder motor can be the whole fix.
    if flaw == "apogee_high" and isinstance(a0, (int, float)) and in_band(flaw, a0, targets):
        for alt in impulse_options(base_design, (0.8, 0.6), class_max):
            sim = search.sim(alt, cond)
            if not sim.get("ok") or not base_ok(sim):
                continue
            if full_pass(alt, sim, targets, cond):
                continue
            got = finish_pair(search, base_design, alt, prompt, cond, targets, flaw)
            if got:
                return got
    # Mass could not open the band. Try a different motor on the single-mount stages.
    mounts = mounts_of(base_design)
    if not mounts:
        return pair
    # Try the top stage first so rail exit (bottom motor) stays put, then the bottom.
    order = list(range(len(base_design["stages"])))
    class_max = class_max_of(targets)
    for si in order:
        st_mounts = []
        for c in tubes(base_design["stages"][si]):
            for x in c["contents"]:
                if x.get("type") == "motor_mount":
                    st_mounts.append((c, x))
        if len(st_mounts) != 1:
            continue
        tube, mount = st_mounts[0]
        try:
            cur = motors.resolve(mount["motor"]["designation"], mount["motor"].get("manufacturer"))
        except motors.UnknownMotor:
            continue
        mid = mount["outer_diameter_m"] - 2 * mount["wall_thickness_m"]
        if flaw == "apogee_low":
            lo, hi = cur["total_impulse_ns"] * 0.45, cur["total_impulse_ns"] * 0.85
        else:
            lo, hi = cur["total_impulse_ns"] * 1.15, cur["total_impulse_ns"] * 2.2
        cands = motor_candidates(mid, tube["length_m"], lo, hi, class_max, cur["manufacturer"], limit=4)
        for info in cands:
            d = set_stage_motor(base_design, si, info)
            if d is None:
                continue
            sim = search.sim(d, cond)
            if not sim.get("ok") or not band(sim):
                continue
            extra = extra_gate_failures(d, sim, targets, cond, flaw)
            if extra:
                continue
            got = finish_pair(search, d, base_design, prompt, cond, targets, flaw)
            if got:
                return got
    return None, reason


def solve_rail(search, ancestor, prompt, cond, targets, _chute_retry=True):
    rows = mass_series(search, ancestor, cond)
    base_c = None
    draft_c = None
    for m, d, sim in rows:
        if not sim.get("ok"):
            continue
        if base_c is None and fixed_metric_ok("rail_exit_slow", sim, None, targets) and not full_pass(d, sim, targets, cond):
            base_c = (m, d, sim)
        if in_band("rail_exit_slow", sim.get("rail_exit_ms"), targets):
            extra = extra_gate_failures(d, sim, targets, cond, "rail_exit_slow")
            if draft_c is None or len(extra) < len(draft_c[3]):
                draft_c = (m, d, sim, extra)
            if not extra and base_c is not None:
                break
    if draft_c is None:
        for (m0, _, s0), (m1, _, s1) in zip(rows, rows[1:]):
            v0, v1 = s0.get("rail_exit_ms"), s1.get("rail_exit_ms")
            if not s0.get("ok") or not s1.get("ok"):
                continue
            if not isinstance(v0, (int, float)) or not isinstance(v1, (int, float)):
                continue
            if not (v0 > 13 >= v1 or v0 >= 13 > v1):
                continue
            lo, hi = m0, m1
            for _ in range(6):
                mid = round((lo + hi) / 2, 4)
                if hi - lo < 0.008:
                    break
                d = with_nose(ancestor, mid)
                sim = search.sim(d, cond)
                v = sim.get("rail_exit_ms") if sim.get("ok") else None
                if not isinstance(v, (int, float)):
                    break
                if in_band("rail_exit_slow", v, targets):
                    draft_c = (mid, d, sim, extra_gate_failures(d, sim, targets, cond, "rail_exit_slow"))
                    break
                if v > 13:
                    lo = mid
                else:
                    hi = mid
            if draft_c:
                break
    if draft_c and draft_c[3] and _chute_retry and any("landing" in e for e in draft_c[3]):
        mass = float(draft_c[2].get("liftoff_mass_kg") or 0.5)
        sized = set_chute_diameter(ancestor, chute_guess(mass, landing_limit_of(targets) * 0.8))
        if design_blob(sized) != design_blob(ancestor):
            alt = solve_rail(search, sized, prompt, cond, targets, _chute_retry=False)
            if not isinstance(alt, tuple):
                return alt
    if draft_c is None:
        return None, "adding nose weight never put rail exit between 9 and 13 m/s"
    if base_c is None:
        return None, "the lighter rocket never clears the rail-exit gate and the other targets together"
    if abs(draft_c[0] - base_c[0]) < 1e-4:
        return None, "rail exit cannot be both too slow and fast enough at the same mass"
    pair = finish_pair(search, draft_c[1], base_c[1], prompt, cond, targets, "rail_exit_slow")
    if pair:
        return pair
    return None, "rail-exit pair failed the final check"


def solve(search: Search, prompt: dict, design: dict, source: str):
    search.reset()
    got, err = _solve_once(search, prompt, design, source)
    if got is None and err and ("rail exit" in err or "rail_exit" in err) and motor_not_kept(prompt):
        for alt in hotter_motors(design, class_max_of(prompt["targets"])):
            got, err2 = _solve_once(search, prompt, alt, source)
            if got is not None:
                return got, None
    return got, err


def _solve_once(search: Search, prompt: dict, design: dict, source: str):
    flaw = prompt["fix_spec"]["flaw"]
    cond = conditions_of(prompt)
    targets = dict(prompt["targets"])
    try:
        parse_design(design)
    except (ValidationError, ValueError) as e:
        return None, f"starting design failed schema: {str(e).splitlines()[0][:180]}"

    if flaw == "rail_exit_slow":
        ancestor, err = repair(search, design, cond, targets)
        if ancestor is None:
            return None, err
        got = solve_rail(search, ancestor, prompt, cond, targets)
    elif flaw in ("apogee_low", "apogee_high"):
        ancestor, err = repair(search, design, cond, targets)
        if ancestor is None:
            return None, err
        got = solve_apogee(search, ancestor, prompt, cond, targets, flaw)
    else:
        base, err = passing_base(search, design, cond, targets, prompt)
        if base is None:
            return None, err
        if flaw == "landing_fast":
            got = solve_landing(search, base, prompt, cond, targets)
        else:
            got = solve_margin(search, base, prompt, cond, targets)
    if isinstance(got, tuple):
        return None, got[1]
    # Body-diameter keep: the checker should hold the draft's tube size.
    if "body_diameter" in (prompt["fix_spec"].get("keep") or []):
        targets = dict(targets)
        targets["body_diameter_m"] = {"value": max_diameter(got["draft"]), "kind": "max"}
        fails = full_pass(got["base"], search.sim(got["base"], cond), targets, cond)
        if fails:
            return None, "adding the body-diameter limit makes the fix fail: " + "; ".join(fails[:3])
        got["targets"] = targets
    else:
        got["targets"] = None
    got["source"] = source
    got["sims"] = search.used
    return got, None


# ------------------------------------------------------------------- loading


def load_converted():
    by_file = {}
    with CONVERTED.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("status") == "ok" and row.get("design"):
                by_file[row["file"]] = row["design"]
    return by_file


def load_groups():
    doc = json.loads(GROUPS.read_text(encoding="utf-8"))
    return {g["group_id"]: g for g in doc["groups"]}


def starting_design(prompt, groups, converted):
    members = groups[prompt["group_id"]]["members"]
    for member in members:
        if member in converted:
            return clone(converted[member]), "converted"
    design, err = synthesize(prompt)
    if design is None:
        return None, err
    return design, "synthesized"


# ------------------------------------------------------------------- report / write


def apply_fill(prompt, got):
    flaw = prompt["fix_spec"]["flaw"]
    text = prompt["user_text"]
    if "{DESIGN_JSON}" not in text or "{OBSERVED}" not in text:
        raise RuntimeError("fix prompt is missing a placeholder")
    blob = design_blob(got["draft"])
    text = text.replace("{DESIGN_JSON}", blob, 1).replace("{OBSERVED}", got["observed_text"], 1)
    prompt["user_text"] = text
    if got["targets"] is not None:
        prompt["targets"] = got["targets"]
    fs = prompt["fix_spec"]
    fs["draft_design"] = got["draft"]
    fs["observed_value"] = got["observed_value"]
    fs["observed_text"] = got["observed_text"]
    fs["base_source"] = got["source"]
    fs["fix_check"] = {
        "change": got["change"],
        "metric": fs["observed"],
        "value": got["fix_value"],
        "passes_targets_and_gates": True,
        "draft_extra_gate_failures": got["extra"],
    }


def write_report(rows_info: list[dict]):
    filled = [r for r in rows_info if r["status"] == "filled"]
    failed = [r for r in rows_info if r["status"] != "filled"]
    by_flaw = {}
    for r in filled:
        by_flaw.setdefault(r["flaw"], {"converted": 0, "synthesized": 0})
        by_flaw[r["flaw"]][r["source"]] += 1
    lines = [
        "# Fix-prompt fill",
        "",
        f"Filled {len(filled)} of {len(rows_info)}. Left {len(failed)} unchanged.",
        "",
        "| flaw | converted | synthesized | filled |",
        "|---|---:|---:|---:|",
    ]
    for flaw in ("low_margin", "landing_fast", "apogee_low", "apogee_high", "rail_exit_slow"):
        c = by_flaw.get(flaw, {"converted": 0, "synthesized": 0})
        lines.append(f"| {flaw} | {c['converted']} | {c['synthesized']} | {c['converted'] + c['synthesized']} |")
    lines += ["", "## Per prompt", "",
              "| prompt | flaw | base | observed | fix check | extra gates |",
              "|---|---|---|---|---|---|"]
    for r in rows_info:
        if r["status"] != "filled":
            continue
        extra = "; ".join(r["extra"]) if r["extra"] else ""
        lines.append(
            f"| `{r['prompt_id']}` | {r['flaw']} | {r['source']} | {r['observed']} | {r['change']} | {extra} |"
        )
    lines += ["", "## Not filled", ""]
    if not failed:
        lines.append("None.")
    else:
        for r in failed:
            lines.append(f"- `{r['prompt_id']}` ({r['flaw']}, {r['source']}): {r['reason']}")
    lines.append("")
    text = "\n".join(lines)
    tmp = REPORT.with_suffix(".md.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, REPORT)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Fill fix-prompt placeholders from real simulations")
    parser.add_argument("--only", help="comma-separated prompt ids")
    parser.add_argument("--dry-run", action="store_true", help="do not write prompts or the backup")
    args = parser.parse_args(argv)
    only = set(args.only.split(",")) if args.only else None

    if args.dry_run:
        source = PROMPTS
    else:
        if not PREFILL.exists():
            shutil.copyfile(PROMPTS, PREFILL)
            print(f"backed up placeholders to {PREFILL.name}", flush=True)
        source = PREFILL

    raw_lines = source.read_text(encoding="utf-8").splitlines(keepends=True)
    groups = load_groups()
    converted = load_converted()
    search = Search()
    info = []
    out_lines = []
    t0 = time.time()
    n_fix = 0
    for raw in raw_lines:
        if not raw.strip():
            out_lines.append(raw)
            continue
        prompt = json.loads(raw)
        if prompt.get("prompt_type") != "fix" or (only and prompt["prompt_id"] not in only):
            out_lines.append(raw if raw.endswith("\n") else raw + "\n")
            continue
        n_fix += 1
        pid = prompt["prompt_id"]
        flaw = prompt["fix_spec"]["flaw"]
        print(f"[{n_fix}] {pid} {flaw}", flush=True)
        design, source_or_err = starting_design(prompt, groups, converted)
        if design is None:
            print(f"    skip: {source_or_err}", flush=True)
            info.append({"prompt_id": pid, "flaw": flaw, "source": "none", "status": "skipped",
                         "reason": source_or_err, "extra": []})
            out_lines.append(raw if raw.endswith("\n") else raw + "\n")
            continue
        source_name = source_or_err
        try:
            got, err = solve(search, prompt, design, source_name)
        except BudgetError as e:
            got, err = None, str(e)
        except Exception as e:
            traceback.print_exc()
            got, err = None, f"{type(e).__name__}: {e}"
        if got is None:
            print(f"    unfilled ({source_name}, {search.used} sims): {err}", flush=True)
            info.append({"prompt_id": pid, "flaw": flaw, "source": source_name, "status": "unfilled",
                         "reason": err, "extra": []})
            out_lines.append(raw if raw.endswith("\n") else raw + "\n")
            continue
        apply_fill(prompt, got)
        print(f"    filled {source_name} observed={got['observed_text']} "
              f"fix={got['fix_value']} sims={search.used} extra={len(got['extra'])}", flush=True)
        if args.dry_run:
            shown = prompt["user_text"].replace(design_blob(got["draft"]), "<design>")
            print("    text:", shown, flush=True)
            print("    change:", got["change"], flush=True)
            if got["extra"]:
                print("    extra:", got["extra"], flush=True)
        info.append({
            "prompt_id": pid, "flaw": flaw, "source": source_name, "status": "filled",
            "observed": f"{got['observed_text']} ({got['observed_value']})",
            "change": got["change"], "extra": got["extra"], "reason": "",
        })
        out_lines.append(json.dumps(prompt, ensure_ascii=False) + "\n")

    if not args.dry_run:
        tmp = PROMPTS.with_suffix(".jsonl.tmp")
        tmp.write_text("".join(out_lines), encoding="utf-8")
        os.replace(tmp, PROMPTS)
        write_report(info)
        print(f"wrote {PROMPTS.name} and {REPORT.name}", flush=True)
    filled = sum(1 for r in info if r["status"] == "filled")
    print(f"done in {time.time() - t0:.0f}s, {filled}/{len(info)} filled, {search.calls} simulations", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
