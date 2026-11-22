"""Generate OpenRocket-verified synthetic RL prompts across motor classes A-O.

    python -m rocket_reward.tools.generate_synthetic_rl_prompts --pilot
    python -m rocket_reward.tools.generate_synthetic_rl_prompts --batch 100 --seed 1001 --out rocket_reward/prompts/synthetic/batches/clean_01.jsonl
    python -m rocket_reward.tools.generate_synthetic_rl_prompts --train 2000 --val 50 --test 50

For every prompt:
  1. Procedurally builds a fresh rocket in Python around a real motor from motor_table.json
     (no SFT kits, no LLM guesswork; ~10% of motor designations per class are held out for val/test).
  2. Flies it in real OpenRocket 24.12 through rocket_reward (3 winds, all 7 stages).
  3. Keeps only rockets that pass stages 1-6 cleanly with zero defects and clear the class apogee floor.
  4. Builds the prompt text and Requirements dict from the real simulated flight metrics
     (including gram weight caps like "under 650 grams" below 1.5 kg, plus optional velocity,
     acceleration, and time-to-apogee limits, subtracting ignition_time_s on timed fields).
  5. Re-scores the same rocket against the final Requirements and requires score >= 0.99.
  6. Writes ONLY the prompt + Requirements (not the rocket) to
     rocket_reward/prompts/synthetic/rl_prompts_v2.jsonl.
"""
from __future__ import annotations

import argparse
import collections
import concurrent.futures
import json
import math
import random
import statistics
import time
from pathlib import Path
from typing import Any

from .. import scoring
from ..motors import class_from_designation, impulse_class
from ..records import Requirements, Target
from ..sim import SimPool

REPO = Path(__file__).resolve().parents[2]
MOTOR_TABLE_PATH = REPO / "rocket_reward" / "data" / "motor_table.json"
DEFAULT_OUT = REPO / "rocket_reward" / "prompts" / "synthetic" / "rl_prompts_v2.jsonl"

M_TO_FT = 3.28084
ALL_CLASSES = tuple("ABCDEFGHIJKLMNO")

SYSTEM_PROMPT = (
    "You are an aerospace design assistant. Explain the airframe, propulsion, stability, and recovery choices "
    "inside <thought> tags, then output the complete OpenRocket design JSON inside <design> tags. Distinguish "
    "stored reference-flight results from static calculations. Do not claim to have run tools or guarantee "
    "flight safety. State missing data and safety limits."
)

# Relative quota weights across classes A..O (covers low, mid, high, and extreme power)
CLASS_WEIGHTS: dict[str, float] = {
    "A": 0.04, "B": 0.05, "C": 0.07, "D": 0.08,
    "E": 0.09, "F": 0.10, "G": 0.11, "H": 0.11,
    "I": 0.09, "J": 0.08, "K": 0.06, "L": 0.04,
    "M": 0.035, "N": 0.025, "O": 0.02,
}

# Minimum apogee (m) per class to reject noisy ultra-low / degenerate flights
CLASS_MIN_APOGEE_M: dict[str, float] = {
    "A": 40.0, "B": 60.0, "C": 80.0, "D": 120.0,
    "E": 160.0, "F": 200.0, "G": 250.0, "H": 320.0,
    "I": 450.0, "J": 650.0, "K": 900.0, "L": 1200.0,
    "M": 1600.0, "N": 2200.0, "O": 3000.0,
}

MOTOR_TYPE_MAP = {
    "Single-use": "single",
    "Reloadable": "reload",
    "Hybrid": "hybrid",
}

# Verified OpenRocket built-in materials (exact names & densities from material_table.json)
BULK_MATERIALS: dict[str, tuple[str, float]] = {
    "balsa": ("Balsa", 170.0),
    "basswood": ("Basswood", 500.0),
    "plywood": ("Plywood (birch)", 630.0),
    "cardboard": ("Cardboard", 680.0),
    "phenolic": ("Kraft phenolic", 950.0),
    "abs": ("ABS - 100% infill", 1050.0),
    "pla": ("PLA - 100% infill", 1250.0),
    "bluetube": ("Blue tube", 1300.0),
    "carbon": ("Carbon fiber", 1780.0),
    "fiberglass": ("Fiberglass", 1850.0),
}


def load_clean_motors(path: Path) -> dict[str, list[dict[str, Any]]]:
    """Load real motors grouped by impulse class A..O, excluding non-flyable/glider motors."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    seen: set[tuple[str, str]] = set()
    by_class: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for mid in sorted(raw):
        rec = raw[mid]
        if not rec.get("in_dataset"):
            continue
        imp = rec.get("total_impulse_ns")
        diam = rec.get("diameter_m")
        length = rec.get("length_m")
        mass = rec.get("launch_mass_kg")
        burnout = rec.get("burnout_mass_kg")
        thrust = rec.get("average_thrust_n")
        desig = rec.get("openrocket_designation") or rec.get("designation")
        mfr = rec.get("openrocket_manufacturer") or rec.get("manufacturer")
        if not (imp and diam and length and mass and thrust and desig and mfr):
            continue
        if imp <= 0 or diam <= 0 or length <= 0 or mass <= 0 or thrust <= 0:
            continue
        # Exclude RC-glider / ultra-low-thrust sustainers that cannot lift an airframe safely
        if thrust / (9.81 * mass) < 10.0:
            continue
        cls = impulse_class(imp)
        if cls not in ALL_CLASSES:
            continue
        if class_from_designation(desig) != cls:
            continue
        key = (cls, desig.upper())
        if key in seen:
            continue
        seen.add(key)
        by_class[cls].append({
            "motor_id": mid,
            "designation": desig,
            "common_name": str(rec.get("openrocket_common_name") or desig).upper(),
            "manufacturer": mfr,
            "motor_type": MOTOR_TYPE_MAP.get(rec.get("motor_type", ""), "single"),
            "impulse_ns": float(imp),
            "diameter_m": float(diam),
            "length_m": float(length),
            "launch_mass_kg": float(mass),
            "burnout_mass_kg": float(burnout if burnout and burnout > 0 else mass * 0.5),
            "average_thrust_n": float(thrust),
            "max_thrust_n": float(rec.get("max_thrust_n") or thrust * 1.4),
        })
    return by_class


def split_motors_ood(
    by_class: dict[str, list[dict[str, Any]]],
    holdout_frac: float = 0.10,
    seed: int = 42,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    """Hold out ~10% of physical motor families (min 2 when >= 6 families) per class for val/test.

    Groups by (manufacturer, common_name) so near-twins like AeroTech J350W / J350W-OLD never split
    across train and eval.
    """
    rng = random.Random(seed)
    train_by_class: dict[str, list[dict[str, Any]]] = {}
    eval_by_class: dict[str, list[dict[str, Any]]] = {}
    for cls, motors in by_class.items():
        families: dict[tuple[str, str], list[dict[str, Any]]] = collections.defaultdict(list)
        for m in motors:
            key = (
                str(m.get("manufacturer", "")).strip().lower(),
                str(m.get("common_name") or m.get("designation", "")).strip().upper(),
            )
            families[key].append(m)
        fam_keys = sorted(families)
        rng.shuffle(fam_keys)
        if len(fam_keys) >= 4 and holdout_frac > 0:
            min_eval = 2 if len(fam_keys) >= 6 else 1
            n_eval = max(min_eval, int(round(len(fam_keys) * holdout_frac)))
            n_eval = min(n_eval, len(fam_keys) - 2)
            eval_keys = fam_keys[:n_eval]
            train_keys = fam_keys[n_eval:]
            eval_by_class[cls] = [m for k in eval_keys for m in families[k]]
            train_by_class[cls] = [m for k in train_keys for m in families[k]]
        else:
            train_by_class[cls] = list(motors)
            eval_by_class[cls] = list(motors)
    return train_by_class, eval_by_class


# --------------------------------------------------------------------------- procedural rocket tree

def _n(tag: str, value: Any = None, attrs: dict[str, Any] | None = None,
       children: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {}
    if attrs:
        body["attrs"] = attrs
    if value is not None:
        body["value"] = value
    if children is not None:
        body["children"] = children
    return {tag: body}


def _mat(name: str, density: float, mtype: str = "bulk") -> dict[str, Any]:
    return _n("material", name, {"type": mtype, "density": density})


def build_procedural_rocket(rng: random.Random, motor: dict[str, Any], cls: str) -> tuple[str, float]:
    """Return (<design>JSON</design> answer text, outer body diameter m) for a fresh procedural rocket."""
    m_diam = motor["diameter_m"]
    m_len = motor["length_m"]
    m_mass = motor["launch_mass_kg"]
    m_burnout = motor["burnout_mass_kg"]
    m_thrust = motor["average_thrust_n"]
    cls_idx = ALL_CLASSES.index(cls)

    if cls_idx <= 3:  # A-D
        tube_name, tube_rho = BULK_MATERIALS[rng.choice(["cardboard", "phenolic"])]
        nose_name, nose_rho = BULK_MATERIALS[rng.choice(["balsa", "pla", "abs"])]
        fin_name, fin_rho = BULK_MATERIALS[rng.choice(["balsa", "basswood", "plywood"])]
        wall_t = rng.uniform(0.0005, 0.0012)
        fin_t = rng.uniform(0.0020, 0.0032)
    elif cls_idx <= 6:  # E-G
        tube_name, tube_rho = BULK_MATERIALS[rng.choice(["cardboard", "phenolic", "bluetube"])]
        nose_name, nose_rho = BULK_MATERIALS[rng.choice(["abs", "pla", "fiberglass"])]
        fin_name, fin_rho = BULK_MATERIALS[rng.choice(["plywood", "basswood", "fiberglass"])]
        wall_t = rng.uniform(0.0010, 0.0020)
        fin_t = rng.uniform(0.0025, 0.0040)
    else:  # H-O
        tube_name, tube_rho = BULK_MATERIALS[rng.choice(["fiberglass", "bluetube", "carbon", "phenolic"])]
        nose_name, nose_rho = BULK_MATERIALS[rng.choice(["fiberglass", "carbon", "abs"])]
        fin_name, fin_rho = BULK_MATERIALS[rng.choice(["fiberglass", "plywood", "carbon"])]
        wall_t = rng.uniform(0.0015, 0.0035)
        fin_t = rng.uniform(0.0030, 0.0065)

    min_diam_design = rng.random() < 0.25
    if min_diam_design:
        r_inner = m_diam / 2.0 + 0.0002
        r_outer = r_inner + wall_t
    else:
        mm_wall = min(0.002, max(0.0005, m_diam * 0.03))
        mm_r_inner = m_diam / 2.0 + 0.0002
        mm_r_outer = mm_r_inner + mm_wall
        diam_mult = rng.uniform(1.25, 2.05) if cls_idx <= 7 else rng.uniform(1.20, 1.75)
        r_outer = max(mm_r_outer + 0.004 + wall_t, (m_diam * diam_mult) / 2.0)
        r_inner = r_outer - wall_t

    d_body = 2.0 * r_outer

    nose_shape = rng.choice(["ogive", "conical", "haack", "ellipsoid"])
    nose_len = d_body * rng.uniform(2.8, 4.8)
    nose_wall = min(r_outer * 0.4, max(0.0015, wall_t * 1.4))
    shoulder_len = min(nose_len * 0.35, d_body * rng.uniform(0.5, 1.0))
    shoulder_r = max(0.002, r_inner - 0.0003)

    # Body length must comfortably hold motor + recovery + provide stability lever arm (<= 3.45 m limit)
    min_body_len = min(3.2, max(m_len * rng.uniform(1.8, 2.5), d_body * rng.uniform(7.5, 12.5)))
    max_body_len = min(3.45, max(min_body_len, d_body * 18.0 - nose_len))
    body_len = rng.uniform(min_body_len, max(min_body_len, min(max_body_len, min_body_len * 1.65)))

    fin_count = rng.choice([3, 4])
    fin_root = min(body_len * 0.45, d_body * rng.uniform(1.5, 2.5))
    fin_tip = fin_root * rng.uniform(0.35, 0.72)
    fin_height = d_body * rng.uniform(1.05, 1.75)
    fin_sweep = (fin_root - fin_tip) * rng.uniform(0.35, 1.15)
    fin_t = max(fin_t, 0.25 / fin_rho)

    tube_mass = math.pi * (r_outer**2 - r_inner**2) * body_len * tube_rho
    nose_mass = 0.55 * math.pi * d_body * nose_len * nose_wall * nose_rho
    fin_mass = fin_count * 0.5 * (fin_root + fin_tip) * fin_height * fin_t * fin_rho
    mm_len = min(body_len * 0.75, max(m_len * 1.05, m_len + 0.015))
    mm_mass = 0.0 if min_diam_design else math.pi * ((m_diam / 2.0 + 0.0015) ** 2 - (m_diam / 2.0) ** 2) * mm_len * tube_rho

    base_dry_mass = tube_mass + nose_mass + fin_mass + mm_mass + m_burnout
    max_safe_liftoff = m_thrust / (7.5 * 9.81)
    headroom = max(0.0, max_safe_liftoff - (base_dry_mass - m_burnout + m_mass))
    ballast_mass = min(
        15.0,
        headroom * rng.uniform(0.08, 0.35),
        max(0.005, base_dry_mass * rng.uniform(0.10, 0.40)),
    )
    if ballast_mass < 0.005:
        ballast_mass = 0.0

    est_burnout_mass = base_dry_mass + ballast_mass

    v_land = rng.uniform(4.4, 7.2)
    chute_cd = 0.80
    chute_area = (2.0 * est_burnout_mass * 9.81) / (1.225 * chute_cd * v_land * v_land)
    chute_diam = max(0.20, min(6.5, math.sqrt(4.0 * chute_area / math.pi)))
    line_count = 6 if chute_diam < 1.2 else (8 if chute_diam < 2.5 else 12)
    line_len = max(0.20, min(chute_diam * 1.1, 4.0))
    line_name, line_rho = (
        ("Braided nylon (2 mm, 1/16 in)", 0.001)
        if chute_diam < 1.5
        else ("Braided nylon (3 mm, 1/8 in)", 0.0035)
    )

    packed_r = max(0.005, min(r_inner * 0.82, 0.12))
    packed_len = max(0.02, min(body_len * 0.22, chute_diam * 0.12))
    main_pos_top = min(body_len * 0.15, shoulder_len + 0.01)

    use_dual = cls_idx >= 8  # I-O
    recovery_nodes: list[dict[str, Any]] = []
    if use_dual:
        drogue_diam = max(0.25, min(1.2, chute_diam * 0.28))
        drogue_packed_len = max(0.02, min(body_len * 0.10, drogue_diam * 0.12))
        recovery_nodes.append(_n("parachute", children=[
            _n("axialoffset", main_pos_top + packed_len + 0.02, {"method": "top"}),
            _n("position", main_pos_top + packed_len + 0.02, {"type": "top"}),
            _n("packedlength", drogue_packed_len),
            _n("packedradius", packed_r),
            _n("radialposition", 0.0),
            _n("radialdirection", 0.0),
            _n("cd", "auto"),
            _n("material", "Ripstop nylon", {"type": "surface", "density": 0.067}),
            _n("deployevent", "apogee"),
            _n("deployaltitude", 200.0),
            _n("deploydelay", 0.0),
            _n("diameter", drogue_diam),
            _n("linecount", 6),
            _n("linelength", max(0.25, drogue_diam)),
            _n("linematerial", line_name, {"type": "line", "density": line_rho}),
        ]))
        main_event = "altitude"
        main_alt = round(rng.uniform(150.0, 380.0), 1)
    else:
        main_event = "apogee"
        main_alt = 200.0

    recovery_nodes.append(_n("parachute", children=[
        _n("axialoffset", main_pos_top, {"method": "top"}),
        _n("position", main_pos_top, {"type": "top"}),
        _n("packedlength", packed_len),
        _n("packedradius", packed_r),
        _n("radialposition", 0.0),
        _n("radialdirection", 0.0),
        _n("cd", "auto"),
        _n("material", "Ripstop nylon", {"type": "surface", "density": 0.067}),
        _n("deployevent", main_event),
        _n("deployaltitude", main_alt),
        _n("deploydelay", 0.0),
        _n("diameter", chute_diam),
        _n("linecount", line_count),
        _n("linelength", line_len),
        _n("linematerial", line_name, {"type": "line", "density": line_rho}),
    ]))

    motor_mount_node = _n("motormount", children=[
        _n("ignitionevent", "automatic"),
        _n("ignitiondelay", 0.0),
        _n("overhang", 0.0),
        _n("motor", attrs={"configid": "cfg0"}, children=[
            _n("type", motor["motor_type"]),
            _n("manufacturer", motor["manufacturer"]),
            _n("motor_id", motor["motor_id"]),
            _n("designation", motor["designation"]),
            _n("diameter", m_diam),
            _n("length", m_len),
            _n("delay", 0.0),
        ]),
        _n("ignitionconfiguration", attrs={"configid": "cfg0"}, children=[
            _n("ignitionevent", "automatic"),
            _n("ignitiondelay", 0.0),
        ]),
    ])

    body_children: list[dict[str, Any]] = [
        _n("finish", "normal"),
        _mat(tube_name, tube_rho, "bulk"),
        _n("length", body_len),
        _n("thickness", wall_t),
        _n("radius", r_outer),
    ]

    body_sub: list[dict[str, Any]] = []
    if ballast_mass > 0.0:
        b_rad = max(0.004, min(r_inner * 0.70, 0.08))
        b_len = max(0.015, min(body_len * 0.12, b_rad * 2.0))
        b_pos = min(body_len * 0.08, max(0.005, shoulder_len * 0.5))
        body_sub.append(_n("masscomponent", children=[
            _n("axialoffset", b_pos, {"method": "top"}),
            _n("position", b_pos, {"type": "top"}),
            _n("packedlength", b_len),
            _n("packedradius", b_rad),
            _n("radialposition", 0.0),
            _n("radialdirection", 0.0),
            _n("mass", ballast_mass),
            _n("masscomponenttype", "masscomponent"),
        ]))

    body_sub.extend(recovery_nodes)

    if min_diam_design:
        body_children.append(motor_mount_node)
    else:
        mm_wall = min(0.002, max(0.0005, m_diam * 0.03))
        mm_r_inner = m_diam / 2.0 + 0.0002
        mm_r_outer = mm_r_inner + mm_wall
        body_sub.append(_n("innertube", children=[
            _n("axialoffset", 0.0, {"method": "bottom"}),
            _n("position", 0.0, {"type": "bottom"}),
            _mat(tube_name, tube_rho, "bulk"),
            _n("length", mm_len),
            _n("radialposition", 0.0),
            _n("radialdirection", 0.0),
            _n("outerradius", mm_r_outer),
            _n("thickness", mm_wall),
            _n("clusterconfiguration", "single"),
            _n("clusterscale", 1.0),
            _n("clusterrotation", 0.0),
            motor_mount_node,
        ]))
        ring_t = min(0.012, max(0.003, mm_len * 0.05))
        for offset in (-ring_t * 1.5, -(mm_len - ring_t * 2.0)):
            body_sub.append(_n("centeringring", children=[
                _n("instancecount", 1),
                _n("instanceseparation", 0.0),
                _n("axialoffset", offset, {"method": "bottom"}),
                _n("position", offset, {"type": "bottom"}),
                _mat("Plywood (birch)", 630.0, "bulk"),
                _n("length", ring_t),
                _n("radialposition", 0.0),
                _n("radialdirection", 0.0),
                _n("outerradius", r_inner - 0.0001),
                _n("innerradius", mm_r_outer + 0.0001),
            ]))

    body_sub.append(_n("trapezoidfinset", children=[
        _n("instancecount", fin_count),
        _n("fincount", fin_count),
        _n("radiusoffset", 0.0, {"method": "surface"}),
        _n("angleoffset", 0.0, {"method": "relative"}),
        _n("rotation", 0.0),
        _n("axialoffset", 0.0, {"method": "bottom"}),
        _n("position", 0.0, {"type": "bottom"}),
        _n("finish", "normal"),
        _mat(fin_name, fin_rho, "bulk"),
        _n("thickness", fin_t),
        _n("crosssection", "rounded"),
        _n("cant", 0.0),
        _n("filletradius", 0.0),
        _n("rootchord", fin_root),
        _n("tipchord", fin_tip),
        _n("sweeplength", fin_sweep),
        _n("height", fin_height),
    ]))

    body_children.append(_n("subcomponents", children=body_sub))

    nose_children = [
        _n("finish", "normal"),
        _mat(nose_name, nose_rho, "bulk"),
        _n("length", nose_len),
        _n("thickness", nose_wall),
        _n("shape", nose_shape),
        _n("shapeparameter", 1.0 if nose_shape == "ogive" else 0.0),
        _n("aftradius", r_outer),
        _n("aftshoulderradius", shoulder_r),
        _n("aftshoulderlength", shoulder_len),
        _n("aftshoulderthickness", nose_wall),
        _n("aftshouldercapped", False),
        _n("isflipped", False),
    ]

    doc = _n("openrocket", attrs={"version": 1.8}, children=[
        _n("rocket", children=[
            _n("axialoffset", 0.0, {"method": "absolute"}),
            _n("position", 0.0, {"type": "absolute"}),
            _n("motorconfiguration", attrs={"configid": "cfg0", "default": True}, children=[
                _n("stage", attrs={"number": 0, "active": True}),
            ]),
            _n("referencetype", "maximum"),
            _n("subcomponents", children=[
                _n("stage", children=[
                    _n("subcomponents", children=[
                        _n("nosecone", children=nose_children),
                        _n("bodytube", children=body_children),
                    ]),
                ]),
            ]),
        ]),
    ])
    return f"<design>\n{json.dumps(doc)}\n</design>", d_body


# --------------------------------------------------------------------------- prompt rendering

def _round_up(val: float, step: float) -> float:
    return math.ceil(val / step - 1e-9) * step


def _fmt_num(x: float) -> str:
    if abs(x - round(x)) < 1e-6:
        return f"{int(round(x)):,}"
    return f"{x:,.1f}"


_AN_LETTERS = frozenset("AEFHILMNORSX")


def _article(token: str) -> str:
    """Return 'an' or 'a' for a motor designation (handles letter names like A6/E20W/F25W and 8/11/18...)."""
    s = token.strip()
    if not s:
        return "a"
    if s[0].isalpha():
        return "an" if s[0].upper() in _AN_LETTERS else "a"
    # Numeric prefix: 8* ("eight..."), or 11*/18* with 2, 4, or 5+ digits ("eleven...", "eighteen...")
    digits = ""
    for ch in s:
        if ch.isdigit():
            digits += ch
        else:
            break
    if digits:
        if digits.startswith("8"):
            return "an"
        if digits[:2] in ("11", "18") and len(digits) != 3:
            return "an"
    return "a"


def _format_mass_phrase(rng: random.Random, mass_kg: float) -> tuple[float, str]:
    """Return (rounded_mass_kg, human_string).

    Always uses grams below 0.3 kg (tight 10 g step), uses grams ~65% of the time in 0.3..1.5 kg,
    and picks the kg format branch from the rounded value (never '1.00 kg' or '10.0 kg').
    """
    if mass_kg < 0.3 or (mass_kg < 1.5 and rng.random() < 0.65):
        grams = int(_round_up(mass_kg * 1000.0, 10.0 if mass_kg < 0.3 else 25.0))
        unit = rng.choice(["grams", "g"])
        return round(grams / 1000.0, 4), f"{grams:,} {unit}"
    kg = round(_round_up(mass_kg, 0.05), 2)
    if kg < 1.0:
        return kg, f"{kg:.2f} kg"
    kg = round(_round_up(mass_kg, 0.1), 1)
    if kg < 10.0:
        return kg, f"{kg:.1f} kg"
    kg = round(_round_up(mass_kg, 0.5), 1)
    return kg, f"{_fmt_num(kg)} kg"


def build_prompt_from_metrics(
    rng: random.Random,
    rid: str,
    style: str,
    cls: str,
    motor: dict[str, Any],
    wind_ms: float,
    metrics: dict[str, Any],
    body_diam_m: float,
    split: str = "train",
) -> tuple[str, dict[str, Any]]:
    """Build (prompt_text, requirements_dict) grounded in exact OpenRocket flight metrics."""
    apogee = float(metrics["apogee_m"])
    apogee_rounded = float(round(apogee)) if apogee >= 100 else round(apogee, 1)
    # Only engineering states tolerance explicitly; casual/original always use the 5% default
    tol = (0.05 if rng.random() < 0.65 else 0.10) if style == "engineering" else 0.05
    ign_s = float(metrics.get("ignition_time_s") or 0.0)

    req: dict[str, Any] = {
        "id": rid,
        "apogee_m": {"value": apogee_rounded, "kind": "about", "tol": tol},
        "wind_ms": wind_ms,
    }

    landing_str: str | None = None
    if "landing_ms" in metrics and rng.random() < 0.95:
        v_meas = float(metrics["landing_ms"])
        v_cap = min(9.0, round(_round_up(v_meas * rng.uniform(1.05, 1.18), 0.1), 1))
        v_cap = max(v_cap, round(_round_up(v_meas, 0.1), 1))
        if v_cap <= 9.0:
            req["landing_ms"] = {"value": v_cap, "kind": "max", "tol": 0.0}
            landing_str = f"{v_cap:.1f} m/s"

    # Train: 50% open / 25% class / 25% named motor; val/test: 50% named OOD motor / 25% class / 25% open
    u = rng.random()
    if split == "train":
        if u < 0.25:
            req["motor_class"] = cls
        elif u < 0.50:
            req["motors"] = [motor["designation"]]
    else:
        if u < 0.50:
            req["motors"] = [motor["designation"]]
        elif u < 0.75:
            req["motor_class"] = cls

    mass_str: str | None = None
    if "mass_kg" in metrics and rng.random() < 0.52:
        m_cap_raw = float(metrics["mass_kg"]) * rng.uniform(1.06, 1.22)
        m_cap, mass_str = _format_mass_phrase(rng, m_cap_raw)
        req["mass_kg"] = {"value": m_cap, "kind": "max", "tol": 0.0}

    diam_mm: int | None = None
    if rng.random() < 0.50:
        diam_mm = int(_round_up(body_diam_m * 1000.0 * rng.uniform(1.03, 1.15), 1.0))
        req["body_diameter_m"] = {"value": round(diam_mm / 1000.0, 4), "kind": "max", "tol": 0.0}

    ftime_s: int | None = None
    if "flight_time_s" in metrics and rng.random() < 0.45:
        ft_meas = max(1.0, float(metrics["flight_time_s"]) - ign_s)
        ftime_s = int(_round_up(ft_meas * rng.uniform(1.08, 1.25), 5.0))
        req["flight_time_s"] = {"value": float(ftime_s), "kind": "max", "tol": 0.0}

    t_apogee_s: float | None = None
    if "time_to_apogee_s" in metrics and rng.random() < 0.15:
        ta_meas = max(1.0, float(metrics["time_to_apogee_s"]) - ign_s)
        t_apogee_s = round(_round_up(ta_meas * rng.uniform(1.10, 1.30), 0.5), 1)
        req["time_to_apogee_s"] = {"value": t_apogee_s, "kind": "max", "tol": 0.0}

    vmax_ms: int | None = None
    if "max_velocity_ms" in metrics and rng.random() < 0.15:
        vmax_ms = int(_round_up(float(metrics["max_velocity_ms"]) * rng.uniform(1.10, 1.25), 5.0))
        req["max_velocity_ms"] = {"value": float(vmax_ms), "kind": "max", "tol": 0.0}

    amax_ms2: int | None = None
    if "max_accel_ms2" in metrics and rng.random() < 0.15:
        amax_ms2 = int(_round_up(float(metrics["max_accel_ms2"]) * rng.uniform(1.12, 1.30), 10.0))
        req["max_accel_ms2"] = {"value": float(amax_ms2), "kind": "max", "tol": 0.0}

    motors = req.get("motors")
    motor_class = req.get("motor_class")

    if style == "engineering":
        parts = [f"apogee {_fmt_num(apogee_rounded)} m (+/- {int(round(tol * 100))}%)"]
        if landing_str:
            parts.append(rng.choice([f"touchdown velocity at most {landing_str}",
                                     f"touchdown velocity {landing_str} maximum"]))
        if ftime_s is not None:
            parts.append(f"flight time {ftime_s} s maximum")
        if t_apogee_s is not None:
            parts.append(f"time to apogee {_fmt_num(t_apogee_s)} s maximum")
        if vmax_ms is not None:
            parts.append(f"max velocity {vmax_ms} m/s maximum")
        if amax_ms2 is not None:
            parts.append(f"max acceleration {amax_ms2} m/s^2 maximum")
        if diam_mm is not None:
            parts.append(f"OD {diam_mm} mm maximum")
        if mass_str is not None:
            parts.append(f"liftoff mass {mass_str} maximum")
        parts.append(f"wind {_fmt_num(wind_ms)} m/s")
        if motors:
            parts.append(f"motor {motors[0]}")
        elif motor_class:
            parts.append(f"class {motor_class} motor")
        text = "Requirements: " + "; ".join(parts) + "."
    elif style == "casual":
        if rng.random() < 0.45:
            ft_val = int(round(apogee * M_TO_FT))
            req["apogee_m"]["value"] = round(ft_val / M_TO_FT, 4)
            alt_str = f"{ft_val:,} ft"
        else:
            alt_str = f"{_fmt_num(apogee_rounded)} m"
        opener_kind = rng.choice(["want", "design", "build"])
        if opener_kind == "want":
            lead = f"I want a rocket that reaches about {alt_str}"
            join = rng.choice([f" and lands under {landing_str}.",
                               f" and drifts down at {landing_str} or less."]) if landing_str else "."
        elif opener_kind == "design":
            lead = f"Design something that hits around {alt_str}"
            join = rng.choice([f" and lands under {landing_str}.",
                               f" and drifts down at {landing_str} or less."]) if landing_str else "."
        else:
            lead = f"Build me a rocket targeting roughly {alt_str}"
            join = rng.choice([f" that lands under {landing_str}.",
                               f" that drifts down at {landing_str} or less."]) if landing_str else "."
        lead += join
        extras = []
        if motors:
            extras.append(f"Use {_article(motors[0])} {motors[0]} motor.")
        elif motor_class:
            extras.append(f"Use a class {motor_class} motor.")
        if mass_str is not None:
            extras.append(rng.choice([f"Keep liftoff weight under {mass_str}.",
                                      f"Total weight must stay under {mass_str}."]))
        if diam_mm is not None:
            extras.append(rng.choice([f"Nothing wider than {diam_mm} mm please.",
                                      f"Keep the airframe no wider than {diam_mm} mm."]))
        if ftime_s is not None:
            extras.append(f"Keep total flight time under {ftime_s} s.")
        if t_apogee_s is not None:
            extras.append(f"Reach apogee in under {_fmt_num(t_apogee_s)} s.")
        if vmax_ms is not None:
            extras.append(f"Stay under {vmax_ms} m/s top speed.")
        if amax_ms2 is not None:
            extras.append(f"Keep peak acceleration under {amax_ms2} m/s^2.")
        extras.append(f"Assume about {_fmt_num(wind_ms)} m/s wind.")
        text = " ".join([lead, *extras])
    else:
        clauses = [f"reaches about {_fmt_num(apogee_rounded)} m apogee"]
        if landing_str:
            clauses.append(f"touches down under {landing_str}")
        if ftime_s is not None:
            clauses.append(f"with total flight time under {ftime_s} s")
        if t_apogee_s is not None:
            clauses.append(f"reaches apogee within {_fmt_num(t_apogee_s)} s")
        if vmax_ms is not None:
            clauses.append(f"keeps peak speed under {vmax_ms} m/s")
        if amax_ms2 is not None:
            clauses.append(f"keeps peak acceleration under {amax_ms2} m/s^2")
        if diam_mm is not None:
            clauses.append(f"with body diameter at most {diam_mm} mm")
        if mass_str is not None:
            clauses.append(f"with liftoff mass under {mass_str}")
        if motors:
            clauses.append(f"using {_article(motors[0])} {motors[0]} motor")
        elif motor_class:
            clauses.append(f"using a class {motor_class} motor")
        clauses.append(f"launched in about {_fmt_num(wind_ms)} m/s wind")
        text = "Design a complete model rocket that " + ", ".join(clauses) + ". Provide the complete hardware design."

    Requirements.from_dict(req)
    return text, req


# --------------------------------------------------------------------------- attempt & verification

def try_one(
    seed: int,
    cls: str,
    motors: list[dict[str, Any]],
    style: str,
    rid: str,
    split: str,
    pool: SimPool,
) -> tuple[dict[str, Any] | None, str, str]:
    """Generate one procedural rocket, fly in OpenRocket via rocket_reward, and prove score >= 0.99."""
    rng = random.Random(seed)
    motor = rng.choice(motors)
    wind_ms = round(rng.choice([0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]), 1)
    answer, d_body = build_procedural_rocket(rng, motor, cls)

    probe_req = Requirements(id=rid, apogee_m=Target(1000.0, "about"), wind_ms=wind_ms)
    res = scoring.score(answer, probe_req, truncated=False, simulator=pool)
    if res.stage != "targets" or res.defects or "apogee_m" not in res.metrics:
        why = (res.reasons[0] if res.reasons else (res.defects[0] if res.defects else res.stage))
        return None, res.stage, why

    min_apogee = CLASS_MIN_APOGEE_M.get(cls, 40.0)
    if float(res.metrics["apogee_m"]) < min_apogee:
        return None, "low_apogee", f"apogee {res.metrics['apogee_m']:.1f} m < floor {min_apogee:.0f} m"

    text, req_dict = build_prompt_from_metrics(rng, rid, style, cls, motor, wind_ms, res.metrics, d_body, split=split)
    proof = scoring.score(answer, Requirements.from_dict(req_dict), truncated=False, simulator=pool)
    if proof.score is None or proof.score < 0.99 or proof.stage != "targets" or proof.defects:
        why = (proof.reasons[0] if proof.reasons else f"proof_score={proof.score}")
        return None, f"proof:{proof.stage}", why

    row = {
        "id": rid,
        "group_id": rid.split(":")[0],
        "family": f"synthetic_{cls}",
        "split": split,
        "prompt_style": style,
        "system": SYSTEM_PROMPT,
        "prompt": text,
        "requirements": req_dict,
        "reference_score": round(float(proof.score), 6),
        "leaks_family": False,
    }
    return row, "ok", ""


def class_quotas(total: int, available: list[str]) -> dict[str, int]:
    """Compute exact integer counts per class summing to `total` without looping when total < len(available)."""
    if total < 0:
        raise ValueError(f"total must be >= 0, got {total}")
    if total == 0 or not available:
        return {c: 0 for c in available}
    order = sorted(available, key=lambda c: (-CLASS_WEIGHTS[c], c))
    if total <= len(available):
        return {c: (1 if c in set(order[:total]) else 0) for c in available}
    wsum = sum(CLASS_WEIGHTS[c] for c in available)
    quotas = {c: max(1, int(round(total * CLASS_WEIGHTS[c] / wsum))) for c in available}
    diff = total - sum(quotas.values())
    i = 0
    while diff != 0:
        c = order[i % len(order)]
        if diff > 0:
            quotas[c] += 1
            diff -= 1
        elif quotas[c] > 1:
            quotas[c] -= 1
            diff += 1
        i += 1
    return quotas


def print_summary(rows: list[dict[str, Any]], label: str) -> None:
    by_cls: dict[str, list[float]] = collections.defaultdict(list)
    modes = collections.Counter()
    styles = collections.Counter()
    fields = collections.Counter()
    for r in rows:
        cls = r["family"].split("_")[-1]
        req = r["requirements"]
        by_cls[cls].append(req["apogee_m"]["value"])
        modes["motors" if "motors" in req else ("motor_class" if "motor_class" in req else "open")] += 1
        styles[r["prompt_style"]] += 1
        for k in req:
            if k != "id":
                fields[k] += 1
    print(f"\n=== Summary: {label} ({len(rows)} rows) ===")
    print("motor modes:", dict(modes), "| styles:", dict(styles))
    print("fields:", dict(fields))
    print("per-class apogee (m): min / med / max")
    for cls in ALL_CLASSES:
        aps = by_cls.get(cls)
        if not aps:
            continue
        print(f"  {cls}: n={len(aps):3d} | {min(aps):7.1f} / {statistics.median(aps):7.1f} / {max(aps):7.1f}")


def generate_split(
    split: str,
    count: int,
    prefix: str,
    by_class: dict[str, list[dict[str, Any]]],
    pool: SimPool,
    workers: int,
    base_seed: int,
    seen_prompts: set[str],
) -> list[dict[str, Any]]:
    available = [c for c in ALL_CLASSES if by_class.get(c)]
    quotas = class_quotas(count, available)
    styles = ("original", "casual", "engineering")
    rows: list[dict[str, Any]] = []
    shortfalls: list[str] = []
    attempt = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        for cls in available:
            need = quotas[cls]
            if need == 0:
                continue
            got: list[dict[str, Any]] = []
            max_attempts = max(need * 15, 80)
            cls_attempts = 0
            while len(got) < need and cls_attempts < max_attempts:
                batch_n = min(max(workers * 2, need - len(got)), max_attempts - cls_attempts)
                futs = []
                for _ in range(batch_n):
                    attempt += 1
                    cls_attempts += 1
                    style = styles[(len(rows) + len(got) + len(futs)) % 3]
                    rid = f"{prefix}-{len(rows) + len(got) + len(futs) + 1:04d}:{style}"
                    futs.append(ex.submit(
                        try_one, base_seed + attempt * 10007, cls, by_class[cls], style, rid, split, pool
                    ))
                for fut in futs:
                    row, _, _ = fut.result()
                    if row is None or len(got) >= need:
                        continue
                    if row["prompt"] in seen_prompts:
                        continue
                    seen_prompts.add(row["prompt"])
                    got.append(row)
            rows.extend(got)
            print(f"  [{split}] class {cls}: {len(got)}/{need} verified ({cls_attempts} tries)", flush=True)
            if len(got) < need:
                shortfalls.append(f"{split}/{cls}: got {len(got)}/{need}")
    if shortfalls:
        raise RuntimeError(f"generation shortfall: {', '.join(shortfalls)}")
    for idx, row in enumerate(rows, 1):
        style = row["prompt_style"]
        rid = f"{prefix}-{idx:04d}:{style}"
        row["id"] = rid
        row["group_id"] = f"{prefix}-{idx:04d}"
        row["requirements"]["id"] = rid
    return rows


def run_pilot(by_class: dict[str, list[dict[str, Any]]], per_class: int, workers: int, seed: int) -> None:
    t0 = time.time()
    styles = ("original", "casual", "engineering")
    jobs = []
    k = 0
    for cls in ALL_CLASSES:
        if not by_class.get(cls):
            continue
        for j in range(per_class):
            k += 1
            jobs.append((seed + k * 7919, cls, by_class[cls], styles[j % 3], f"PILOT-{cls}-{j + 1}:{styles[j % 3]}"))

    stats: dict[str, collections.Counter[str]] = {c: collections.Counter() for c in ALL_CLASSES}
    reasons: dict[str, list[str]] = collections.defaultdict(list)
    ok_rows: list[dict[str, Any]] = []

    with SimPool(workers) as pool, concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(try_one, s, cls, ms, st, rid, "train", pool) for s, cls, ms, st, rid in jobs]
        for (s, cls, ms, st, rid), fut in zip(jobs, futs):
            row, status, why = fut.result()
            stats[cls][status] += 1
            if row is not None:
                ok_rows.append(row)
            else:
                reasons[cls].append(f"[{status}] {why[:110]}")

    print(f"\nPILOT DONE in {time.time() - t0:.1f} s: {len(ok_rows)}/{len(jobs)} passed (>= 0.99 in OpenRocket)\n")
    for cls in ALL_CLASSES:
        if not by_class.get(cls):
            continue
        ok = stats[cls]["ok"]
        fails = {k: v for k, v in stats[cls].items() if k != "ok"}
        print(f"  {cls}: {ok}/{per_class} ok | fails={fails}")
        for r in reasons[cls][:2]:
            print(f"      fail: {r}")
    print_summary(ok_rows, "pilot")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", action="store_true", help="Run a fast pilot across classes A-O without writing")
    ap.add_argument("--per-class", type=int, default=3, help="Pilot attempts per class (default 3)")
    ap.add_argument("--batch", type=int, default=0, help="Generate a single batch of N prompts to --out")
    ap.add_argument("--split", default="train", help="Split name when using --batch (default train)")
    ap.add_argument("--exclude-prompts", nargs="*", default=[],
                    help="Earlier JSONL files whose prompt texts must be excluded (cross-batch dedup)")
    ap.add_argument("--train", type=int, default=2000)
    ap.add_argument("--val", type=int, default=50)
    ap.add_argument("--test", type=int, default=50)
    ap.add_argument("--holdout-frac", type=float, default=0.10, help="Fraction of motors held out for val/test")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    a = ap.parse_args()

    by_class = load_clean_motors(MOTOR_TABLE_PATH)
    if a.pilot:
        run_pilot(by_class, a.per_class, a.workers, a.seed)
        return

    train_motors, eval_motors = split_motors_ood(by_class, holdout_frac=a.holdout_frac, seed=42)

    t0 = time.time()
    seen: set[str] = set()
    for p in a.exclude_prompts:
        path = Path(p)
        if not path.is_file():
            raise SystemExit(f"--exclude-prompts file not found: {path}")
        for line in path.open(encoding="utf-8"):
            if line.strip():
                seen.add(json.loads(line)["prompt"])
    with SimPool(a.workers) as pool:
        if a.batch > 0:
            motors = train_motors if a.split == "train" else eval_motors
            prefix = f"B{a.seed}"
            all_rows = generate_split(a.split, a.batch, prefix, motors, pool, a.workers, a.seed, seen)
        else:
            train_rows = generate_split("train", a.train, "SYN", train_motors, pool, a.workers, a.seed, seen)
            val_rows = generate_split("val", a.val, "SYNVAL", eval_motors, pool, a.workers, a.seed + 50_000_000, seen)
            test_rows = generate_split("test", a.test, "SYNTEST", eval_motors, pool, a.workers, a.seed + 90_000_000, seen)
            all_rows = train_rows + val_rows + test_rows

    for r in all_rows:
        Requirements.from_dict(r["requirements"])

    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("w", encoding="utf-8", newline="\n") as fh:
        for r in all_rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\nWrote {len(all_rows)} OpenRocket-verified prompts to {a.out} in {time.time() - t0:.1f} s")
    for sp in ("train", "val", "test"):
        sp_rows = [r for r in all_rows if r["split"] == sp]
        if sp_rows:
            print_summary(sp_rows, sp)


if __name__ == "__main__":
    main()
