"""Prompt families for the SFT v2 dataset (DATA_SPEC.md sections 3 and 4).

One family of 2-4 prompts per source-design group (sftgen/out/groups.json). The
group's reference facts only prove a request can be met; they are never the
answer. Prompts are composed from independently chosen phrase slots so that no
composed template or numbers-stripped skeleton dominates the file.

    .venv/bin/python -m sftgen.prompts     -> sftgen/out/prompts_v1.jsonl
                                              sftgen/out/prompts_v1_report.md
"""

from __future__ import annotations

import json
import math
import random
import re
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

from sftgen import contract, groups as _groups, motors as _motors

HERE = Path(__file__).resolve().parent
GROUPS = HERE / "out" / "groups.json"
OUT = HERE / "out" / "prompts_v1.jsonl"
REPORT = HERE / "out" / "prompts_v1_report.md"

SEED = "sftgen-prompts-v1"
PROMPT_VERSION = "prompts-v1"
G = 9.81
FT = 0.3048
MPH = 0.44704

MIX = {  # spec 3.3 shares (infeasible 5-10 %, timed <= 5 %)
    "altitude": 0.30, "fixed_motor": 0.15, "recovery": 0.15, "multi": 0.10,
    "fix": 0.10, "missing_info": 0.10, "infeasible": 0.07, "timed": 0.03,
}
GOAL_KEYS = ("apogee_m", "ground_hit_ms", "flight_time_s", "time_to_apogee_s", "payload_kg", "drift_m")
CLASSES = "ABCDEFGHIJKLMNO"
# Rough single-stage, single-motor altitude ceilings (m) for any sane airframe on that class.
CLASS_CEILING_M = {"A": 200, "B": 350, "C": 600, "D": 900, "E": 1200, "F": 1700, "G": 2500, "H": 3500,
                   "I": 4500, "J": 6000, "K": 8000, "L": 10000, "M": 13000, "N": 17000, "O": 25000}
STD_MOTOR_MM = (13, 18, 24, 29, 38, 54, 75, 98)
COMMERCIAL = {"AeroTech": "AeroTech", "Cesaroni": "Cesaroni", "Estes": "Estes", "Estes Industries, Inc.": "Estes",
              "Loki": "Loki", "Quest": "Quest", "Quest Aerospace": "Quest", "Klima": "Klima", "AMW": "AMW",
              "Apogee": "Apogee"}
ESTES_DELAY = {"A8": 3, "B4": 4, "B6": 4, "C6": 5, "C11": 5, "D12": 5, "E9": 6, "E12": 6, "E16": 6, "A10": 3}


# =========================================================================== helpers

def fmt_num(x: float) -> str:
    if abs(x - round(x)) < 1e-9:
        return f"{int(round(x)):,}"
    return f"{x:,.1f}"


def num_needs_an(text: str) -> bool:
    """Does the leading number read with a vowel sound ('an 8 ft', 'an 80 g', 'an 18,000 ft')?"""
    m = re.match(r"(\d[\d,]*)(?:\.\d+)?", text.strip())
    if not m:
        return False
    d = m.group(1).replace(",", "").lstrip("0") or "0"
    if d in ("8", "11", "18"):
        return True
    if len(d) >= 2 and d[0] == "8":
        return True  # eighty-, eight hundred, eight thousand
    if len(d) in (4, 5) and d[:2] in ("11", "18"):
        return True  # eleven/eighteen hundred or thousand
    return False


def article(word: str) -> str:
    w = word.strip()
    if not w:
        return "a"
    if w[0].isdigit():
        return "an" if num_needs_an(w) else "a"
    if re.match(r"^[A-Z][A-Z0-9]", w) or re.match(r"^[A-Z]\d", w) or re.match(r"^[A-Z]$", w):
        return "an" if w[0] in "AEFHILMNORSX" else "a"
    return "an" if w[0].lower() in "aeio" else "a"


def with_article(word: str) -> str:
    return f"{article(word)} {word}"


def nice_about(v: float, steps: tuple, max_err: float = 0.035) -> float:
    for s in steps:
        if s > v / 3:
            continue
        r = round(v / s) * s
        if r > 0 and abs(r - v) / v <= max_err:
            return r
    return round(v)


def nice_floor(v: float, steps: tuple, lo: float = 0.86) -> float:
    for s in steps:
        if s > v / 3:
            continue
        r = math.floor(v / s) * s
        if r >= lo * v and r > 0:
            return r
    return math.floor(v)


def nice_ceil(v: float, ladder: tuple) -> float | None:
    for x in ladder:
        if x >= v:
            return x
    return None


def nice_floor_ladder(v: float, ladder: tuple) -> float | None:
    best = None
    for x in ladder:
        if x <= v:
            best = x
    return best


M_STEPS = (5000, 2500, 1000, 500, 250, 100, 50, 25, 10, 5)
FT_STEPS = (5000, 1000, 500, 250, 100, 50, 25, 10)
TIME_LADDER = (20, 25, 30, 40, 45, 50, 60, 75, 90, 100, 120, 150, 180, 200, 240, 300, 360, 400, 450, 480, 500, 600, 720, 900)
DRIFT_LADDER_M = (100, 150, 200, 250, 300, 400, 500, 600, 750, 800, 1000, 1200, 1500, 2000, 2500, 3000, 4000, 5000, 6000, 8000)
IMPULSE_LADDER = (5, 10, 20, 40, 50, 80, 100, 160, 200, 250, 320, 400, 500, 640, 800, 1000, 1500, 2000, 2500, 3000,
                  4000, 5000, 6000, 8000, 10000, 15000, 20000, 30000, 40000)
BODY_MM_LADDER = (20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 90, 100, 110, 120, 130, 140, 150, 160, 180, 200, 250)
BODY_IN_LADDER = (1, 1.5, 2, 2.5, 3, 4, 5, 6, 7.5, 8, 10)


class Alt:
    """An altitude a person would write, plus its SI value."""

    def __init__(self, text: str, value_m: float):
        self.text, self.value_m = text, round(value_m, 1)


def alt_about(rng: random.Random, apo: float, imperial: bool) -> Alt:
    if imperial:
        ft = nice_about(apo / FT, FT_STEPS)
        word = rng.choice(["ft", "ft", "feet"])
        return Alt(f"{fmt_num(ft)} {word}", ft * FT)
    m = nice_about(apo, M_STEPS)
    if m >= 10000 and m % 500 == 0 and rng.random() < 0.6:
        return Alt(f"{fmt_num(m / 1000)} km", m)
    return Alt(f"{fmt_num(m)} m", m)


def alt_floor(rng: random.Random, apo: float, imperial: bool) -> Alt:
    if imperial:
        ft = nice_floor(apo / FT, FT_STEPS)
        word = rng.choice(["ft", "feet"])
        return Alt(f"{fmt_num(ft)} {word}", ft * FT)
    m = nice_floor(apo, M_STEPS)
    if m >= 10000 and m % 500 == 0 and rng.random() < 0.6:
        return Alt(f"{fmt_num(m / 1000)} km", m)
    return Alt(f"{fmt_num(m)} m", m)


def alt_text_raw(m: float, imperial: bool, rng: random.Random) -> Alt:
    """For numbers that are already 'nice' (infeasible asks, ceilings)."""
    if imperial:
        ft = nice_about(m / FT, (10000, 5000, 1000, 500))
        return Alt(f"{fmt_num(ft)} ft", ft * FT)
    if m >= 10000 and rng.random() < 0.7:
        return Alt(f"{fmt_num(m / 1000)} km", m)
    return Alt(f"{fmt_num(m)} m", m)


def alt_cap(cap_m: float, imperial: bool) -> Alt:
    """A person-rounded altitude ceiling strictly below cap_m; never None."""
    if imperial:
        ft = nice_floor_ladder(cap_m / FT, (50, 75, 100, 150, 200, 250, 300, 400)
                               + tuple(range(500, 200001, 500)))
        if ft is None:
            ft = max(50, round(cap_m / FT / 25) * 25)
        return Alt(f"{fmt_num(ft)} ft", ft * FT)
    m = nice_floor_ladder(cap_m, (15, 20, 25, 30, 40) + tuple(range(50, 60001, 50)))
    if m is None:
        m = max(15, round(cap_m / 5) * 5)
    return Alt(f"{fmt_num(m)} m", m)


def landing_limit(rng: random.Random, soft_ok: bool = True) -> tuple[str, float]:
    opts = [("6 m/s", 6.0)] * 5 + [("5 m/s", 5.0)] * 2 + [("15 ft/s", 15 * FT), ("18 ft/s", 18 * FT)]
    if soft_ok:
        opts += [("4.5 m/s", 4.5), ("5.5 m/s", 5.5)]
    t, v = rng.choice(opts)
    return t, round(v, 2)


def wind_choice(rng: random.Random, imperial: bool) -> tuple[str, float]:
    if imperial:
        mph = rng.choice([5, 5, 8, 10, 10, 12, 15])
        return f"{mph} mph", round(mph * MPH, 2)
    ms = rng.choice([2, 3, 3, 4, 4, 5, 6])
    if rng.random() < 0.15:
        kmh = rng.choice([10, 15, 20])
        return f"{kmh} km/h", round(kmh / 3.6, 2)
    return f"{ms} m/s", float(ms)


def rail_choice(rng: random.Random, ref: dict, imperial: bool) -> tuple[str, float] | None:
    """A rail long enough that the reference design would leave it at >= 15 m/s."""
    need = 0.9
    ss = ref.get("stored_sim") or {}
    L, v = ss.get("launchrodlength"), ref.get("rail_exit_ms")
    if L and v and v > 0:
        need = max(need, L * (15.0 / v) ** 2 * 1.1)
    heavy = (ref.get("liftoff_mass_kg") or 0) > 3
    if heavy:
        need = max(need, 2.4)
    if imperial:
        opts = [(f"{ft} ft", ft * FT) for ft in (3, 4, 6, 8, 10, 12) if ft * FT >= need]
    else:
        opts = [(f"{m} m", m) for m in (1, 1.5, 2, 2.5, 3, 3.5) if m >= need]
    if not opts:
        return None
    txt, val = opts[0] if rng.random() < 0.6 else rng.choice(opts[:3])
    return txt, round(val, 2)


def motor_mm_ceiling(ref: dict) -> int | None:
    ds = ref.get("motor_diameters_m") or []
    if not ds:
        return None
    d = max(ds) * 1000
    for s in STD_MOTOR_MM:
        if s >= d - 0.6:
            return s
    return None


def cert_for_class(c: str | None) -> str:
    if c is None:
        return "unknown"
    i = CLASSES.index(c) if c in CLASSES else 15
    if i <= CLASSES.index("D"):
        return "low"
    if i <= CLASSES.index("G"):
        return "mid"
    if i <= CLASSES.index("I"):
        return "L1"
    if i <= CLASSES.index("L"):
        return "L2"
    return "L3"


def display_designation(designation: str, manufacturer: str, rng: random.Random | None = None, delay: bool = False) -> str:
    d = re.sub(r"^(HP|RMS|DMS)-", "", designation.strip(), flags=re.I)
    m = re.search(r"([A-P])-?(\d+)([A-Z]{0,3})", d)
    core = (m.group(1) + m.group(2) + m.group(3)) if m else d
    if manufacturer in ("Cesaroni", "Loki"):
        core = re.sub(r"(\d)(LR|LW|LB|CT|RL|WT|SS|BS|VM|CS|IM|PS)$", r"\1", core)
    if delay and core in ESTES_DELAY:
        core = f"{core}-{ESTES_DELAY[core]}"
    return core


# Pinned-DB manufacturer display name -> hobbyist short name used in prompt text.
SHORT_MAKER = {
    "CESARONI": "Cesaroni", "ANIMALMOTORWORKS": "AMW", "LOKIRESEARCH": "Loki",
    "KLIMA": "Klima", "APOGEE": "Apogee", "PUBLICMISSILES": "PML",
    "KOSDON": "Kosdon", "AEROTECH": "AeroTech", "ESTES": "Estes", "QUEST": "Quest",
}


def maker_short(display: str) -> str:
    n = _motors._norm(display)
    return next((v for k, v in SHORT_MAKER.items() if k in n), display)


@lru_cache(maxsize=1)
def _common_names() -> dict[str, str]:
    return {str(jm.getDesignation()): str(jm.getCommonName())
            for ms in _motors._index().values() for jm in ms}


def _resolve_info(m: dict) -> dict | None:
    """Full pinned-DB describe for a .ork motor entry, honouring the manufacturer hint."""
    r = _groups.resolve_motor(m["designation"], m.get("manufacturer"))
    return _motors.resolve(r["designation"]) if r else None


@lru_cache(maxsize=None)
def _replacement(des: str, mfr: str, dia: float, cls: str | None, itot: float | None) -> dict | None:
    """Closest pinned-DB motor of the same maker and case diameter for a .ork
    motor the DB doesn't carry (e.g. AMW 'O3800' 98 mm -> 'BB-98-17500' / N4000)."""
    maker = COMMERCIAL.get(mfr)
    if not maker or not dia:
        return None
    want = _motors._norm(_motors.MANUFACTURER_ALIASES.get(maker.lower(), maker))
    cands, seen = [], set()
    for ms in _motors._index().values():
        for jm in ms:
            d = str(jm.getDesignation())
            if d in seen:
                continue
            mn = _motors._norm(str(jm.getManufacturer().getDisplayName()))
            if want not in mn and mn not in want:
                continue
            if abs(float(jm.getDiameter()) - dia) > 0.001:
                continue
            seen.add(d)
            cands.append(jm)
    if not cands:
        return None

    def key(jm):
        imp = float(jm.getTotalImpulseEstimate())
        cd = abs(CLASSES.index(_motors.motor_class(imp)) - CLASSES.index(cls)) if cls in CLASSES else 0
        return cd, (abs(imp - itot) if itot else -imp), str(jm.getDesignation())

    jm = min(cands, key=key)
    imp = float(jm.getTotalImpulseEstimate())
    return {"designation": str(jm.getDesignation()),
            "manufacturer": str(jm.getManufacturer().getDisplayName()),
            "class": _motors.motor_class(imp),
            "total_impulse_ns": round(imp, 1),
            "average_thrust_n": round(float(jm.getAverageThrustEstimate()), 1),
            "diameter_m": round(float(jm.getDiameter()), 4)}


def canonical_motor(m: dict) -> dict | None:
    """Canonical pinned-DB view of a reference .ork motor entry; None => never name it.

    Resolved by designation + manufacturer hint; when the .ork entry is absent
    from the DB but reads as a real commercial motor, the closest same-maker /
    same-diameter motor is substituted so the prompt can still name something real.
    """
    info = _resolve_info(m)
    sub = info is None
    if sub:
        info = _replacement(m["designation"], m.get("manufacturer") or "",
                            m.get("diameter_m") or 0.0, m.get("class"), m.get("total_impulse_ns"))
    if info is None:
        return None
    common = _common_names().get(info["designation"])
    return {"designation": info["designation"], "manufacturer": info["manufacturer"],
            "maker": maker_short(info["manufacturer"]), "class": info["class"],
            "total_impulse_ns": info["total_impulse_ns"], "avg_thrust_n": info["average_thrust_n"],
            "diameter_m": info["diameter_m"],
            "common": common if common and re.search(r"[A-P]-?\d+", common) else None,
            "raw": m["designation"], "substituted": sub}


def display_name(c: dict, delay: bool = False) -> str:
    """Hobbyist motor name for a canonical motor: the DB common name when it
    exists ('N4000'), else a cleaned-up designation ('2546K300-P' -> 'K300')."""
    core = c["common"] or display_designation(c["designation"], c["maker"])
    if delay and core in ESTES_DELAY:
        core = f"{core}-{ESTES_DELAY[core]}"
    return core


def motor_phrase(c: dict, rng: random.Random, with_maker: bool | None = None) -> str:
    maker = c["maker"]
    delay = maker in ("Estes", "Quest") and rng.random() < 0.5
    core = display_name(c, delay)
    if with_maker is None:
        with_maker = bool(maker) and rng.random() < 0.6
    return f"{maker} {core}" if with_maker and maker else core


def numword(n: int) -> str:
    return {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}.get(n, str(n))


# =========================================================================== reference facts

class Facts:
    def __init__(self, g: dict):
        r = g["reference"]
        self.g, self.r = g, r
        self.apo = r["apogee_m"]
        self.apo_ok = self.apo is not None and "apogee_implausibly_low" not in r["quality"] and self.apo >= 60
        self.all_m = [m for s in r["motors_by_stage"] for m in s["motors"]]
        self.canon = [canonical_motor(m) for m in self.all_m]
        self.canon_by = {id(m): c for m, c in zip(self.all_m, self.canon)}
        self.single_motor = r["motor_count"] == 1 and len(self.all_m) == 1
        self.multi = r["stage_count"] > 1 or r["motor_count"] > 1
        self.named = bool(self.canon) and all(
            c is not None and c["maker"] in COMMERCIAL.values() and c["class"] in CLASSES
            for c in self.canon)
        tic = r.get("total_impulse_class")
        self.max_class = max((m["class"] for m in self.all_m
                              if isinstance(m.get("class"), str) and m["class"] in CLASSES),
                             default=tic if isinstance(tic, str) and tic in CLASSES else None)
        self.total_ns = r.get("total_impulse_ns")
        self.D = r.get("max_body_diameter_m")
        self.motor_mm = motor_mm_ceiling(r)
        self.recovery = r["recovery"]
        self.m0 = r.get("liftoff_mass_kg")
        self.t_ap = r.get("time_to_apogee_s") or (math.sqrt(2 * self.apo / G) * 1.1 if self.apo else None)
        self.payload = r.get("payload_mass_kg") or 0.0
        self.low_power = self.max_class is not None and CLASSES.index(self.max_class) <= CLASSES.index("D")
        self.hpr = self.max_class is not None and CLASSES.index(self.max_class) >= CLASSES.index("H")

    def canon_of(self, m: dict) -> dict | None:
        return self.canon_by.get(id(m))


# =========================================================================== phrase banks

OPENINGS = {
    "casual": ["Hey!", "Hi,", "Quick one:", "Okay, so", "Need a hand.", "Looking for help with a build.",
               "Hey folks,", "So here's the deal:", "Got a project for you.", "", "", ""],
    "formal": ["Our team needs a rocket design.", "We are preparing a vehicle for a club launch.", "Requirement:",
               "Design request.", "For an upcoming launch:", "Please propose a design.", "Project brief:", ""],
    "beginner": ["I'm new to rocketry.", "First real build here.", "I'm pretty new at this.", "Beginner question:",
                 "Still learning, so bear with me.", "My first scratch build!", ""],
    "competition": ["For our competition entry:", "Team project:", "For the club altitude contest:",
                    "Our university team is entering a contest.", "Contest build:", "Competition rules for us:"],
    "terse": [""],
}
CLOSINGS = {
    "casual": ["Thanks!", "What would you build?", "Cheers.", "Any ideas?", "Show me what you've got.", "", "", ""],
    "formal": ["Please provide the full design.", "Provide the design and expected performance.",
               "Please include your assumptions.", "", ""],
    "beginner": ["Keep it simple if you can.", "Something I can actually build, please.", "Thanks for the help!",
                 "Explain what you pick, please.", ""],
    "competition": ["We'd like the full design.", "Please flag anything risky.", "Thanks.", ""],
    "terse": [""],
}
REGISTERS = ["casual", "formal", "beginner", "competition", "terse"]
REG_WEIGHTS = [0.32, 0.2, 0.14, 0.12, 0.22]


def pick(rng: random.Random, options: list, slot: str, used: list) -> str:
    i = rng.randrange(len(options))
    used.append(f"{slot}{i}")
    return options[i]


# ---------------------------------------------------------------- goal phrasings

def goal_about(rng, alt: Alt, terse: bool, used) -> str:
    if terse:
        return pick(rng, [f"about {alt.text}", f"~{alt.text}", f"around {alt.text}", f"{alt.text} apogee",
                          f"roughly {alt.text}", f"target {alt.text}"], "ga", used)
    return pick(rng, [
        f"I want it to hit about {alt.text}.", f"Target apogee is around {alt.text}.",
        f"It should get to roughly {alt.text}.", f"Aiming for {alt.text} or so.",
        f"Can you design something that reaches about {alt.text}?", f"Need around {alt.text} apogee.",
        f"Looking for roughly {alt.text}.", f"Design a rocket that goes about {alt.text}.",
        f"Build me something for about {alt.text}.", f"Goal is about {alt.text}.",
        f"Shooting for about {alt.text}.", f"We'd like an apogee near {alt.text}.",
        f"Something that tops out around {alt.text}.", f"I'm after roughly {alt.text} of altitude.",
    ], "ga", used)


def goal_min(rng, alt: Alt, terse: bool, used) -> str:
    if terse:
        return pick(rng, [f"at least {alt.text}", f"clear {alt.text}", f"{alt.text} minimum", f"over {alt.text}",
                          f"min apogee {alt.text}"], "gm", used)
    return pick(rng, [
        f"It needs to clear {alt.text}.", f"It has to get above {alt.text}.", f"Minimum apogee is {alt.text}.",
        f"It needs to break {alt.text}.", f"Must reach at least {alt.text}.", f"I want to beat {alt.text}.",
        f"Anything over {alt.text} works.", f"Get me past {alt.text}.", f"The bar is {alt.text}; go higher if you can.",
        f"At least {alt.text}, please.",
    ], "gm", used)


def goal_max(rng, alt: Alt, terse: bool, used) -> str:
    if terse:
        return pick(rng, [f"stay under {alt.text}", f"{alt.text} ceiling", f"below {alt.text}"], "gx", used)
    return pick(rng, [
        f"Our waiver is {alt.text}, so it can't go higher than that.", f"It must stay under {alt.text}.",
        f"Ceiling is {alt.text}; get close without going over.", f"Keep apogee below {alt.text} for the waiver.",
        f"The field has {with_article(alt.text)} ceiling.",
    ], "gx", used)


def landing_phrase(rng, txt: str, terse: bool, used, every: bool = False, both: bool = False) -> str:
    if every:
        if terse:
            opts = [f"every section under {txt}", f"all parts land under {txt}"]
            if both:
                opts.append(f"both stages under {txt}")
            return pick(rng, opts, "le", used)
        opts = [f"Every section needs to land under {txt}.", f"All parts should come down under {txt}.",
                f"Each piece that separates must land under {txt}.", f"Each stage has to land under {txt}."]
        if both:
            opts += [f"Both stages need to land under {txt}.", f"Booster and sustainer both land under {txt}."]
        return pick(rng, opts, "le", used)
    if terse:
        return pick(rng, [f"land under {txt}", f"touchdown < {txt}", f"landing under {txt}", f"{txt} max at landing"], "lt", used)
    return pick(rng, [
        f"It should land under {txt}.", f"Touchdown under {txt}.", f"It needs to come down at {txt} or less.",
        f"Landing speed below {txt}, please.", f"Keep the landing under {txt}.", f"I'd like it to land under {txt}.",
        f"Has to land softer than {txt}.", f"Soft landing, under {txt}.",
    ], "lt", used)


# ---------------------------------------------------------------- constraint axes
# Each returns (text, targets_update, sim_update, axis_name) or None if it can't admit the reference.

def ax_cert(rng, f: Facts, terse, used):
    c = cert_for_class(f.max_class)
    if c == "unknown":
        return None
    if c == "low":
        opts = (["Only standard Estes-size motors, D or smaller.", "Low power only, D motors max.",
                 "The field is low-power only, so D or smaller."],
                ["D motor max", "low power only (D max)", "D or smaller"], "D")
    elif c == "mid":
        opts = (["I'm not high-power certified, so G or smaller.", "No HPR cert yet, nothing above a G.",
                 "It has to stay mid-power, G max.", "I don't have my L1 yet, so G is the limit."],
                ["G max (no cert)", "no HPR, G or smaller", "mid-power only"], "G")
    elif c == "L1":
        opts = (["I'm Level 1 certified, so H or I motors only.", "I only have my L1.", "Keep it to Level 1 motors.",
                 "I'm L1, so H and I motors.", "It has to fly on my Level 1 cert."],
                ["L1 motors only", "Level 1 (H/I) max", "L1 cert"], "I")
    elif c == "L2":
        opts = (["I have my L2, so up to an L motor is fine.", "Level 2 motors max.",
                 "Our team lead is L2 certified, so J to L is fine.", "Nothing bigger than an L, that's my cert."],
                ["L2 motors max", "Level 2 cert", "J-L motors OK"], "L")
    else:
        opts = (["We have an L3 flyer on the team.", "I'm L3 certified.", "Our mentor holds an L3, so M and up is fine."],
                ["L3 OK", "Level 3 cert"], "O")
    sent, frag, cls = opts
    text = pick(rng, frag if terse else sent, "cert", used)
    return text, {"motor_class": {"value": cls, "kind": "max"}}, {}, "motor_limit"


def ax_class(rng, f: Facts, terse, used):
    if f.max_class is None:
        return None
    i = CLASSES.index(f.max_class)
    letter = CLASSES[min(len(CLASSES) - 1, i + (1 if rng.random() < 0.3 else 0))]
    a = article(letter)
    text = pick(rng, [f"{letter} motor max", f"{letter} or smaller", f"nothing above {a} {letter}"] if terse else [
        f"{letter} motor or smaller.", f"Nothing bigger than {a} {letter}.", f"Keep it to {a} {letter} or below.",
        f"The biggest motor I can use is {a} {letter}.", f"Motor class {letter} at most.",
    ], "cls", used)
    return text, {"motor_class": {"value": letter, "kind": "max"}}, {}, "motor_limit"


def ax_motor_diam(rng, f: Facts, terse, used):
    if f.motor_mm is None or f.motor_mm == 13:
        return None
    d = f.motor_mm
    if rng.random() < 0.25 and d < 98:
        d = STD_MOTOR_MM[STD_MOTOR_MM.index(d) + 1]
    a = article(str(d))
    text = pick(rng, [f"{d} mm motor max", f"{d} mm mount", f"motor {d} mm or smaller"] if terse else [
        f"{d} mm motor max.", f"It has to take {a} {d} mm motor.", f"The motor mount is {d} mm.",
        f"Motor no bigger than {d} mm.", f"It should fit {a} {d} mm motor case.", f"I only have {d} mm hardware.",
    ], "md", used)
    return text, {"motor_diameter_m": {"value": d / 1000, "kind": "max"}}, {}, "motor_limit"


def ax_body_diam(rng, f: Facts, terse, used):
    if not f.D:
        return None
    need = f.D * 1000 * 1.01
    if rng.random() < 0.4:
        inch = nice_ceil(need / 25.4, BODY_IN_LADDER)
        if inch is None:
            return None
        s = fmt_num(inch)
        plural = "inch" if inch == 1 else "inches"
        text = pick(rng, [f"{s} in body max", f"{s}-inch airframe max"] if terse else [
            f"The airframe can't be wider than {s} {plural}.", f"{s}-inch airframe or smaller.",
            f"Keep it under {s} in diameter.", f"Body tube {s} {plural} max.",
        ], "bdi", used)
        return text, {"body_diameter_m": {"value": round(inch * 0.0254, 4), "kind": "max"}}, {}, "size_limit"
    mm = nice_ceil(need, BODY_MM_LADDER)
    if mm is None:
        return None
    text = pick(rng, [f"{mm} mm body max", f"body under {mm} mm"] if terse else [
        f"Body tube no wider than {mm} mm.", f"Max body diameter is {mm} mm.", f"Keep the airframe under {mm} mm across.",
        f"{mm} mm OD max.", f"It has to fit in {with_article(str(mm))} mm envelope.",
    ], "bdm", used)
    return text, {"body_diameter_m": {"value": mm / 1000, "kind": "max"}}, {}, "size_limit"


def ax_impulse(rng, f: Facts, terse, used):
    if not f.total_ns:
        return None
    lim = nice_ceil(f.total_ns * 1.05, IMPULSE_LADDER)
    if lim is None or lim > contract.GATES["max_total_impulse_ns"]:
        return None
    s = fmt_num(lim)
    unit = rng.choice(["N·s", "Ns", "N-s"])
    text = pick(rng, [f"{s} {unit} max", f"under {s} {unit} total"] if terse else [
        f"No more than {s} {unit} total impulse.", f"Total impulse has to stay under {s} {unit}.",
        f"Impulse budget is {s} {unit}.", f"Keep total impulse at {s} {unit} or less.",
    ], "imp", used)
    return text, {"total_impulse_ns": {"value": float(lim), "kind": "max"}}, {}, "motor_limit"


def ax_landing(rng, f: Facts, terse, used, every=False):
    txt, v = landing_limit(rng)
    t = {"ground_hit_ms": {"value": v, "kind": "max"}}
    if every:
        t["ground_hit_ms"]["applies_to"] = "every section"
    both = every and f.r["stage_count"] == 2 and not f.r.get("parallel_boosters")
    return landing_phrase(rng, txt, terse, used, every, both), t, {}, "landing_limit"


def ax_payload(rng, f: Facts, terse, used):
    if f.payload < 0.04:
        return None
    p = f.payload
    if p >= 1:
        if rng.random() < 0.4:
            lb = math.floor(p / 0.4536 * 2) / 2
            if lb >= 1:
                txt, val = f"{fmt_num(lb)} lb", lb * 0.4536
            else:
                txt, val = f"{fmt_num(math.floor(p * 2) / 2)} kg", math.floor(p * 2) / 2
        else:
            val = math.floor(p * 2) / 2
            txt = f"{fmt_num(val)} kg"
    else:
        g = int(nice_floor(p * 1000, (100, 50, 25, 10), lo=0.75))
        txt, val = f"{g} g", g / 1000
    what = rng.choice(["payload", "altimeter payload", "camera payload", "science payload", "payload module"])
    at = with_article(f"{txt} {what}")
    text = pick(rng, [f"{txt} {what}", f"carry {txt}"] if terse else [
        f"It has to carry {at}.", f"There's {at} to fly.", f"Room for {at}, please.",
        f"It needs to lift {at}.",
    ], "pl", used)
    return text, {"payload_kg": {"value": round(val, 3), "kind": "min"}}, {}, "payload"


def ax_single_stage(rng, f: Facts, terse, used):
    if f.multi:
        return None
    text = pick(rng, ["single-stage", "one stage", "no staging"] if terse else [
        "Single stage only.", "No staging, one motor.", "Keep it single-stage.", "One stage, nothing fancy.",
    ], "ss", used)
    return text, {"stages": {"value": 1, "kind": "exact"}}, {}, "stages"


AXES = {"cert": ax_cert, "class": ax_class, "motor_diam": ax_motor_diam, "body_diam": ax_body_diam,
        "impulse": ax_impulse, "landing": ax_landing, "payload": ax_payload, "single_stage": ax_single_stage}


# ---------------------------------------------------------------- launch conditions

def cond_wind(rng, f, imperial, terse, used):
    txt, v = wind_choice(rng, imperial)
    text = pick(rng, [f"{txt} wind", f"wind ~{txt}"] if terse else [
        f"Expect about {txt} of wind.", f"It usually blows around {txt} at our field.", f"Plan for {txt} wind.",
        f"Winds are typically {txt}.", f"It should handle {txt} wind.",
    ], "w", used)
    return text, {"wind_ms": v}


def cond_rail(rng, f, imperial, terse, used):
    rc = rail_choice(rng, f.r, imperial)
    if rc is None:
        return None
    txt, v = rc
    kind = "rod" if v < 1.4 else "rail"
    at = with_article(f"{txt} {kind}")
    text = pick(rng, [f"{txt} {kind}", f"off {at}"] if terse else [
        f"We launch off {at}.", f"Our pad has {at}.", f"The {kind} is {txt} long.",
        f"We've got {at} to work with.",
    ], "r", used)
    return text, {"rail_length_m": v}


def cond_site(rng, f, imperial, terse, used):
    if imperial:
        ft = rng.choice([1000, 2500, 4000, 4500])
        txt, v = f"{fmt_num(ft)} ft", ft * FT
    else:
        m = rng.choice([300, 600, 1200, 1300])
        txt, v = f"{fmt_num(m)} m", float(m)
    text = pick(rng, [f"site at {txt} elevation"] if terse else [
        f"The launch site is at {txt} elevation.", f"Our field sits about {txt} above sea level.",
    ], "sa", used)
    return text, {"site_altitude_m": round(v, 1)}


def cond_angle(rng, f, imperial, terse, used):
    deg = rng.choice([3, 5, 5, 10])
    text = pick(rng, [f"rail at {deg} degrees"] if terse else [
        f"The RSO wants the rail angled {deg} degrees off vertical.", f"Rail will be tilted {deg} degrees away from the crowd.",
    ], "ang", used)
    return text, {"launch_angle_deg": float(deg)}


CONDS = {"wind": cond_wind, "rail_length": cond_rail, "site_altitude": cond_site, "launch_angle": cond_angle}


# =========================================================================== prompt record helpers

class Draft:
    def __init__(self, ptype: str, register: str):
        self.ptype, self.register = ptype, register
        self.parts: list[str] = []
        self.targets: dict = {}
        self.sim: dict = {}
        self.used: list[str] = [ptype, register]
        self.axes: list[str] = []
        self.feasible = True
        self.reason = None
        self.needs_design = False
        self.fix_spec = None
        self.omitted: list[str] = []

    @property
    def terse(self) -> bool:
        return self.register == "terse"

    def add(self, text: str | None):
        if text:
            self.parts.append(text.strip())

    def apply(self, res):
        if res is None:
            return False
        text, t, s, axis = res
        self.add(text)
        self.targets.update(t)
        self.sim.update(s)
        self.axes.append(axis)
        return True

    def cond(self, res, name):
        if res is None:
            return False
        text, s = res
        self.add(text)
        self.sim.update(s)
        self.axes.append(name)
        return True

    def render(self, rng: random.Random, opening: bool = True, closing: bool = True) -> str:
        reg = self.register
        parts = list(self.parts)
        if self.terse:
            body = ", ".join(p.rstrip(".") for p in parts if p)
            text = body[:1].upper() + body[1:] + "."
            text = re.sub(r"\?\.$", "?", text)
            return text
        o = pick(rng, OPENINGS[reg], "o", self.used) if opening else ""
        c = pick(rng, CLOSINGS[reg], "c", self.used) if closing else ""
        # An opener like "Okay, so" runs on: lowercase the first content word.
        if o and not o.rstrip().endswith((".", "!", "?", ":")) and parts:
            parts[0] = parts[0][:1].lower() + parts[0][1:]
        out = " ".join(x for x in [o] + parts + [c] if x)
        out = re.sub(r"\s+", " ", out).strip()
        return out[:1].upper() + out[1:]


def sentence(s: str) -> str:
    s = s.strip()
    return s if s.endswith((".", "?", "!")) else s + "."


def missing_list(d: Draft) -> list[str]:
    have = set(d.axes) | set(d.sim)
    keys = d.targets.keys()
    out = []
    if "wind_ms" not in d.sim:
        out.append("wind")
    if "rail_length_m" not in d.sim:
        out.append("rail_length")
    if "ground_hit_ms" not in keys:
        out.append("landing_limit")
    if not ({"motor", "motor_class", "motor_diameter_m", "total_impulse_ns"} & set(keys)):
        out.append("motor_limit")
    if "body_diameter_m" not in keys:
        out.append("size_limit")
    if "recovery" not in keys and "recovery" not in have:
        out.append("recovery_type")
    return out


def choose_register(rng: random.Random, allowed: list[str] | None = None) -> str:
    regs, w = REGISTERS, REG_WEIGHTS
    if allowed:
        pairs = [(r, x) for r, x in zip(regs, w) if r in allowed]
        regs, w = [p[0] for p in pairs], [p[1] for p in pairs]
    return rng.choices(regs, weights=w)[0]


def maybe_conditions(rng, d: Draft, f: Facts, imperial: bool, p_wind=0.35, p_rail=0.25, p_site=0.07, p_angle=0.05):
    if rng.random() < p_wind:
        d.cond(cond_wind(rng, f, imperial, d.terse, d.used), "wind")
    if rng.random() < p_rail:
        d.cond(cond_rail(rng, f, imperial, d.terse, d.used), "rail_length")
    if rng.random() < p_site:
        d.cond(cond_site(rng, f, imperial, d.terse, d.used), "site_altitude")
    if rng.random() < p_angle:
        d.cond(cond_angle(rng, f, imperial, d.terse, d.used), "launch_angle")


def motor_list_phrase(rng, cs: list[dict]) -> str:
    return " and ".join(with_article(motor_phrase(c, rng)) for c in cs)


# =========================================================================== builders

def build_altitude(rng, f: Facts, avoid_axes: set[str], variant: int) -> Draft:
    d = Draft("altitude", choose_register(rng))
    imperial = rng.random() < 0.4
    kind = rng.choices(["about", "min", "max"], weights=[0.55, 0.35, 0.10])[0] if variant == 0 else \
        rng.choices(["about", "min", "max"], weights=[0.35, 0.5, 0.15])[0]
    if kind == "about":
        alt = alt_about(rng, f.apo, imperial)
        goal = goal_about(rng, alt, d.terse, d.used)
        d.targets["apogee_m"] = {"value": alt.value_m, "kind": "about"}
    elif kind == "min":
        alt = alt_floor(rng, f.apo, imperial)
        goal = goal_min(rng, alt, d.terse, d.used)
        d.targets["apogee_m"] = {"value": alt.value_m, "kind": "min"}
    else:
        raw = f.apo * rng.uniform(1.06, 1.2)
        alt = Alt(*((lambda ft: (f"{fmt_num(ft)} ft", ft * FT))(nice_ceil(raw / FT, tuple(range(500, 200001, 500))))) if imperial
                  else (lambda m: (f"{fmt_num(m)} m", m))(nice_ceil(raw, tuple(range(50, 60001, 50)))))
        goal = goal_max(rng, alt, d.terse, d.used)
        d.targets["apogee_m"] = {"value": alt.value_m, "kind": "max"}
    names = ["cert", "class", "motor_diam", "body_diam", "impulse", "landing", "payload", "single_stage"]
    weights = [3, 2, 3, 2, 1, 3, 2 if f.payload >= 0.04 else 0, 1]
    n_axes = rng.choice([1, 2, 2])
    picked: list[str] = []
    pend = []
    pool = [(n, w * (0.25 if n in avoid_axes else 1.0)) for n, w in zip(names, weights) if w > 0]
    for _ in range(12):
        if len(picked) >= n_axes or not pool:
            break
        n = rng.choices([p[0] for p in pool], weights=[p[1] for p in pool])[0]
        pool = [p for p in pool if p[0] != n]
        if n in ("cert", "class", "impulse") and any(x in picked for x in ("cert", "class", "impulse")):
            continue
        res = AXES[n](rng, f, d.terse, d.used)
        if res is not None:
            picked.append(n)
            pend.append(res)
    if rng.random() < 0.75:
        d.add(goal)
        for res in pend:
            d.apply(res)
    else:
        for res in pend:
            d.apply(res)
        d.add(goal)
    maybe_conditions(rng, d, f, imperial)
    return d


def build_fixed_motor(rng, f: Facts, avoid_axes: set[str], variant: int) -> Draft:
    d = Draft("fixed_motor", choose_register(rng, ["casual", "beginner", "formal", "terse", "competition"]))
    m = f.all_m[0]
    cm = f.canon_of(m)
    mp = motor_phrase(cm, rng)
    d.targets["motor"] = {"value": [cm["designation"]], "kind": "exact"}
    cert = cert_for_class(cm["class"])
    cert_txt = {"L1": ["I'm Level 1", "I just got my L1", "Fresh L1 here"], "L2": ["I'm L2 certified", "I have my L2"],
                "L3": ["We're an L3 team", "I'm L3"], "mid": ["No HPR cert needed for this one", ""],
                "low": ["", "My kid and I are getting into rocketry"]}.get(cert, [""])
    imperial = rng.random() < 0.4
    if d.terse:
        d.add(pick(rng, [f"{mp} only", f"fixed motor: {mp}", f"must fly on {with_article(mp)}"], "fm", d.used))
    else:
        lead = pick(rng, cert_txt, "fc", d.used)
        has = pick(rng, [
            f"I have {with_article(mp)}.", f"I've got {with_article(mp)} sitting in my range box.",
            f"Got a spare {mp}.", f"My club gave me {with_article(mp)}.", f"I want to fly {with_article(mp)}.",
            f"The motor is fixed: {with_article(mp)}.", f"We bought {with_article(mp)} for this.",
        ], "fh", d.used)
        d.add((sentence(lead) + " " if lead else "") + has)
    goal_kind = rng.choices(["landing", "min_alt", "both"], weights=[0.45, 0.25, 0.30])[0] if f.apo_ok else "landing"
    if goal_kind in ("landing", "both"):
        txt, v = landing_limit(rng)
        d.targets["ground_hit_ms"] = {"value": v, "kind": "max"}
        if d.terse:
            d.add(pick(rng, [f"as high as sensible, land under {txt}", f"max altitude, stable, land < {txt}",
                             f"go high, touchdown under {txt}"], "fg", d.used))
        else:
            d.add(pick(rng, [
                f"Build something that goes as high as it sensibly can and lands under {txt}.",
                f"What's the highest stable rocket I can build for it? It has to land under {txt}.",
                f"Make it fly as high as is sensible, but it must come down under {txt}.",
                f"I'd like a stable rocket that gets the most out of it and lands under {txt}.",
                f"Design around it. Stable, as much altitude as is reasonable, landing under {txt}.",
            ], "fg", d.used))
    if goal_kind in ("min_alt", "both"):
        alt = alt_floor(rng, f.apo * rng.uniform(0.7, 0.85), imperial)
        d.targets["apogee_m"] = {"value": alt.value_m, "kind": "min"}
        d.add(goal_min(rng, alt, d.terse, d.used) if goal_kind == "min_alt" else pick(rng, [
            f"Ideally it clears {alt.text}.", f"Bonus if it gets past {alt.text}.", f"I'd like at least {alt.text} out of it.",
        ] if not d.terse else [f"at least {alt.text}"], "fb", d.used))
    extra = [n for n in ("body_diam", "single_stage") if n not in avoid_axes]
    if extra and rng.random() < 0.35:
        d.apply(AXES[rng.choice(extra)](rng, f, d.terse, d.used))
    maybe_conditions(rng, d, f, imperial, p_wind=0.45, p_rail=0.3)
    return d


def recovery_options(f: Facts) -> list[str]:
    opts = []
    if f.recovery == "dual_deploy" or (f.apo >= 450 and (f.D or 0) >= 0.038):
        opts.append("dual_deploy")
    if f.apo <= 1200 and f.recovery != "streamer":
        opts.append("single_chute")
    if f.recovery == "streamer" and (f.m0 or 1) <= 0.12 or ((f.m0 or 1) <= 0.06 and f.apo <= 400):
        opts.append("streamer")
    return opts or ["single_chute"]


def build_recovery(rng, f: Facts, avoid_axes: set[str], variant: int) -> Draft:
    d = Draft("recovery", choose_register(rng))
    imperial = rng.random() < 0.4
    opts = recovery_options(f)
    rec = rng.choice(opts)
    if f.recovery in opts and rng.random() < 0.5:
        rec = f.recovery
    alt = alt_about(rng, f.apo, imperial) if rng.random() < 0.6 else alt_floor(rng, f.apo, imperial)
    kind = "about" if abs(alt.value_m - f.apo) / f.apo <= 0.035 else "min"
    d.targets["apogee_m"] = {"value": alt.value_m, "kind": kind}
    d.targets["recovery"] = {"value": rec, "kind": "exact"}
    wtxt, wv = wind_choice(rng, imperial)
    sub = rng.choices(["drift", "time", "landing"], weights=[0.35, 0.3, 0.35])[0]
    if rec == "streamer":
        sub = "landing"
    rec_txt = {
        "dual_deploy": (["Dual deploy is fine.", "Dual deploy, drogue at apogee and main low.",
                         "Use dual deployment.", "We want dual deploy on this one."], ["dual deploy"]),
        "single_chute": (["A single chute is fine.", "Just one parachute, keep it simple.",
                          "Single-chute recovery.", "One main chute at apogee is what we fly."], ["single chute"]),
        "streamer": (["Streamer recovery, it's light.", "Use a streamer instead of a chute.",
                      "Streamer only, no parachute."], ["streamer recovery"]),
    }[rec]
    goal_txt = (f"about {alt.text}" if kind == "about" else f"at least {alt.text}")
    if sub == "drift":
        if rec == "dual_deploy":
            t_desc = max(f.apo - 200, 0) / 25 + 200 / 5.0
        else:
            t_desc = f.apo / 5.0
        est = wv * t_desc + 0.1 * f.apo
        lim_m = nice_ceil(1.6 * est, DRIFT_LADDER_M)
        if lim_m is None:
            sub = "landing"
        else:
            if imperial and lim_m <= 1500 and rng.random() < 0.7:
                ft = nice_ceil(lim_m / FT, (500, 1000, 1500, 2000, 2500, 3000, 4000, 5000))
                dtxt, dv = f"{fmt_num(ft)} ft", ft * FT
            elif imperial and lim_m >= 1600 and rng.random() < 0.5:
                mi = nice_ceil(lim_m / 1609.3, (1, 1.5, 2, 3, 4, 5))
                dtxt, dv = (f"{fmt_num(mi)} mile" + ("s" if mi != 1 else "")), mi * 1609.3
            else:
                dtxt, dv = f"{fmt_num(lim_m)} m", float(lim_m)
            d.targets["drift_m"] = {"value": round(dv, 1), "kind": "max"}
            d.sim["wind_ms"] = wv
            d.axes += ["wind", "drift"]
            if d.terse:
                d.add(f"{goal_txt}, land within {dtxt} of the pad in {wtxt} wind")
                d.add(pick(rng, rec_txt[1], "rt", d.used))
            else:
                d.add(pick(rng, [
                    f"Needs to hit {goal_txt} and come down within {dtxt} of the pad in {wtxt} wind.",
                    f"We want {goal_txt}, but the field is small: it has to land within {dtxt} of the pad, and it's usually {wtxt} wind.",
                    f"Goal is {goal_txt}. With {wtxt} wind it still has to land inside {dtxt} of the pad.",
                    f"Get it to {goal_txt} and keep the drift under {dtxt} in {wtxt} wind.",
                ], "rd", d.used))
                d.add(pick(rng, rec_txt[0], "rr", d.used))
    if sub == "time":
        L = 6.0
        if rec == "dual_deploy":
            t_min = f.t_ap + max(f.apo - 200, 0) / 25 + 200 / (0.9 * L)
        else:
            t_min = f.t_ap + f.apo / (0.9 * L)
        lim = nice_ceil(1.35 * t_min, TIME_LADDER)
        if lim is None:
            sub = "landing"
        else:
            ttxt = (f"{lim // 60} minutes" if lim % 60 == 0 and lim >= 120 and rng.random() < 0.6 else f"{lim} s")
            if ttxt.endswith(" s") and rng.random() < 0.3:
                ttxt = f"{lim} seconds"
            reason = pick(rng, ["so it doesn't drift off the field", "because the range gives us short windows",
                                "since there's a highway downwind", "so we can recover it before the next flight",
                                "because the farmer next door gets nervous"], "rrs", d.used)
            d.targets["flight_time_s"] = {"value": float(lim), "kind": "max"}
            if d.terse:
                d.add(f"{goal_txt}, on the ground within {ttxt} ({reason})")
                d.add(pick(rng, rec_txt[1], "rt", d.used))
            else:
                d.add(pick(rng, [
                    f"It should reach {goal_txt} and be back on the ground in under {ttxt}, {reason}.",
                    f"Target is {goal_txt}. Total flight under {ttxt} {reason}.",
                    f"We need {goal_txt}, and it has to land within {ttxt} of liftoff {reason}.",
                ], "rtm", d.used))
                d.add(pick(rng, rec_txt[0], "rr", d.used))
            if rng.random() < 0.5:
                d.sim["wind_ms"] = wv
                d.add(f"Wind is usually around {wtxt}." if not d.terse else f"{wtxt} wind")
                d.axes.append("wind")
    if sub == "landing":
        txt, v = landing_limit(rng)
        d.targets["ground_hit_ms"] = {"value": v, "kind": "max"}
        if d.terse:
            d.add(f"{goal_txt}, {pick(rng, rec_txt[1], 'rt', d.used)}, land under {txt}")
        else:
            d.add(pick(rng, [
                f"I want {goal_txt} with a gentle landing, under {txt}.",
                f"It needs to reach {goal_txt} and land under {txt} so it flies again.",
                f"Target {goal_txt}; recovery matters most to me, so under {txt} at touchdown.",
                f"Looking for {goal_txt}. Landing under {txt} is a must.",
            ], "rl", d.used))
            d.add(pick(rng, rec_txt[0], "rr", d.used))
        if rng.random() < 0.6:
            d.sim["wind_ms"] = wv
            d.axes.append("wind")
            d.add(f"Plan for {wtxt} wind." if not d.terse else f"{wtxt} wind")
    if rng.random() < 0.25:
        d.cond(cond_rail(rng, f, imperial, d.terse, d.used), "rail_length")
    return d


def build_multi(rng, f: Facts, avoid_axes: set[str], variant: int) -> Draft:
    d = Draft("multi", choose_register(rng, ["casual", "formal", "terse", "competition"]))
    r = f.r
    imperial = rng.random() < 0.35
    staged = r["stage_count"] > 1
    firing = r["motors_by_stage"]
    style = variant % 3 if f.named else 1 + (variant % 2)
    every = rng.random() < 0.8
    if staged:
        n = r["stage_count"]
        d.targets["stages"] = {"value": n, "kind": "exact"}
        word = {2: "Two-stage", 3: "Three-stage"}.get(n, f"{n}-stage")
        if style == 0:
            ms = [m for s in firing for m in s["motors"]]
            d.targets["motor"] = {"value": [f.canon_of(m)["designation"] for s in firing for m in s["motors"] for _ in range(m["count"])], "kind": "exact"}
            names = [motor_phrase(f.canon_of(m), rng) for m in ms]
            if n == 2 and len(names) == 2:
                lead = pick(rng, [f"{word} rocket: {names[0]} booster, {names[1]} sustainer.",
                                  f"{word}, {with_article(names[0])} in the booster and {with_article(names[1])} up top.",
                                  f"I want to stage {with_article(names[0])} to {with_article(names[1])}."], "ms0", d.used)
            else:
                lead = pick(rng, [f"{word} stack: " + ", then ".join(names) + ".",
                                  f"{word} rocket, motors in firing order: " + ", ".join(names) + "."], "ms0", d.used)
        elif style == 1:
            classes = [m["class"] for s in firing for m in s["motors"] if m.get("class")]
            mx = max(classes) if classes else None
            if mx:
                d.targets["motor_class"] = {"value": mx, "kind": "max"}
            if n == 2 and len(classes) == 2:
                lead = pick(rng, [f"{word}, {with_article(classes[0])} booster and {with_article(classes[1])} sustainer.",
                                  f"{word} rocket with {with_article(classes[0])}-class booster and {with_article(classes[1])}-class sustainer."], "ms1", d.used)
            else:
                lead = pick(rng, [f"{word} rocket, nothing bigger than {with_article(mx)} motor in any stage." if mx else f"{word} rocket.",
                                  f"{word}, {mx} motors max." if mx else f"{word} rocket please."], "ms1", d.used)
        else:
            lead = pick(rng, [f"{word} rocket.", f"I want to try {with_article(word.lower())} flight.",
                              f"Our next project is {with_article(word.lower())} rocket."], "ms2", d.used)
            mm = f.motor_mm
            if mm and mm > 13:
                d.targets["motor_diameter_m"] = {"value": mm / 1000, "kind": "max"}
                lead += " " + pick(rng, [f"{mm} mm motors max.", f"All motors {mm} mm or smaller."], "ms2d", d.used)
    else:
        n = r["motor_count"]
        d.targets["motor_count"] = {"value": n, "kind": "exact"}
        ms = [m for s in firing for m in s["motors"]]
        parallel = r.get("parallel_boosters")
        same = len({m["designation"] for m in ms}) == 1
        if style == 0:
            d.targets["motor"] = {"value": [f.canon_of(m)["designation"] for m in ms for _ in range(m["count"])], "kind": "exact"}
            if same:
                mp = motor_phrase(f.canon_of(ms[0]), rng)
                lead = pick(rng, [f"Cluster of {numword(n)} {mp}s.", f"I want to cluster {numword(n)} {mp} motors.",
                                  f"{numword(n).capitalize()}-motor cluster, all {mp}s."], "mc0", d.used)
            elif parallel:
                core = [s for s in firing if s["kind"] == "axial"]
                side = [s for s in firing if s["kind"] == "parallel"]
                cm = [motor_phrase(f.canon_of(m), rng) for s in core for m in s["motors"]]
                sm = side[0]["motors"][0]
                smp = motor_phrase(f.canon_of(sm), rng)
                lead = pick(rng, [f"Core motor {' and '.join(cm)} with {numword(sm['count'])} {smp} strap-on boosters.",
                                  f"I'd like {with_article(cm[0])} core plus {numword(sm['count'])} {smp} side boosters."], "mc0", d.used)
            else:
                parts = []
                for m in ms:
                    mp = motor_phrase(f.canon_of(m), rng)
                    parts.append(f"{numword(m['count'])} {mp}s" if m["count"] > 1 else with_article(mp))
                lead = pick(rng, [f"Cluster: {', '.join(parts[:-1])} and {parts[-1]}." if len(parts) > 1 else f"Cluster of {parts[0]}.",
                                  f"I want to fly a cluster with {' plus '.join(parts)}."], "mc0", d.used)
                if any(m["ignition"] not in ("automatic", "launch") for m in ms) or "airstart" in f.g["group_id"]:
                    lead += " " + pick(rng, ["Some of them air-start.", "The outboard motors can be air-started."], "mca", d.used)
        else:
            classes = sorted({m["class"] for m in ms if m.get("class")})
            mx = max(classes) if classes else None
            if mx:
                d.targets["motor_class"] = {"value": mx, "kind": "max"}
            lead = pick(rng, [f"{numword(n).capitalize()}-motor cluster, {mx} motors or smaller." if mx else f"{numword(n).capitalize()}-motor cluster.",
                              f"I want to try a {numword(n)}-motor cluster" + (f", nothing above {with_article(mx)}." if mx else "."),
                              f"Cluster build with {numword(n)} motors" + (f", max class {mx}." if mx else ".")], "mc1", d.used)
    if d.terse:
        lead = lead.rstrip(".")
    d.add(lead)
    if f.apo_ok:
        alt = alt_about(rng, f.apo, imperial) if rng.random() < 0.5 else alt_floor(rng, f.apo, imperial)
        about = abs(alt.value_m - f.apo) / f.apo <= 0.035
        d.targets["apogee_m"] = {"value": alt.value_m, "kind": "about" if about else "min"}
        d.add(goal_about(rng, alt, d.terse, d.used) if about else goal_min(rng, alt, d.terse, d.used))
    land = ax_landing(rng, f, d.terse, d.used, every=(staged or bool(r.get("parallel_boosters"))) and every)
    d.apply(land)
    maybe_conditions(rng, d, f, imperial, p_wind=0.3, p_rail=0.35)
    return d


FIX_FLAWS = {
    "low_margin": "static_margin_cal",
    "landing_fast": "ground_hit_ms",
    "apogee_low": "apogee_m",
    "apogee_high": "apogee_m",
    "rail_exit_slow": "rail_exit_ms",
}


def build_fix(rng, f: Facts, avoid_axes: set[str], variant: int) -> Draft:
    d = Draft("fix", choose_register(rng, ["casual", "formal", "beginner", "competition"]))
    d.needs_design = True
    imperial = rng.random() < 0.35
    flaws = ["low_margin", "landing_fast"] + (["apogee_low", "apogee_high"] if f.apo_ok else []) + ["rail_exit_slow"]
    weights = [3, 3] + ([2, 1] if f.apo_ok else []) + [1]
    flaw = rng.choices(flaws, weights=weights)[0]
    intro = pick(rng, ["Here's my design: {DESIGN_JSON}", "This is what I have so far: {DESIGN_JSON}",
                       "My current design is below. {DESIGN_JSON}", "Can you fix this? {DESIGN_JSON}",
                       "Design attached: {DESIGN_JSON}", "We drafted this: {DESIGN_JSON}"], "xi", d.used)
    d.add(intro)
    keep: list[str] = []
    if flaw == "low_margin":
        d.add(pick(rng, ["OpenRocket says the margin is only {OBSERVED}.", "Stability margin comes out at {OBSERVED}, which seems low.",
                         "The sim shows {OBSERVED} of static margin.", "I'm getting a margin of {OBSERVED}."], "xf", d.used))
        if f.named and f.single_motor:
            keep = ["motor"]
            d.targets["motor"] = {"value": [f.canon_of(f.all_m[0])["designation"]], "kind": "exact"}
            d.add(pick(rng, ["Fix it without changing the motor.", "Keep the same motor.", "The motor has to stay."], "xk", d.used))
        if f.apo_ok and rng.random() < 0.5:
            alt = alt_floor(rng, f.apo * 0.9, imperial)
            d.targets["apogee_m"] = {"value": alt.value_m, "kind": "min"}
            d.add(pick(rng, [f"It still has to clear {alt.text}.", f"Don't let apogee drop below {alt.text}."], "xg", d.used))
        else:
            txt, v = landing_limit(rng)
            d.targets["ground_hit_ms"] = {"value": v, "kind": "max"}
            d.add(pick(rng, [f"It still needs to land under {txt}.", f"And keep the landing under {txt}."], "xg", d.used))
    elif flaw == "landing_fast":
        txt, v = landing_limit(rng)
        d.targets["ground_hit_ms"] = {"value": v, "kind": "max"}
        keep = ["airframe"] if rng.random() < 0.5 else []
        d.add(pick(rng, [f"It comes down at {{OBSERVED}}, too hard. Get it under {txt}.",
                         f"Landing speed is {{OBSERVED}} and I keep cracking fins. I need under {txt}.",
                         f"OpenRocket shows {{OBSERVED}} at touchdown. Can you get that below {txt}?"], "xf", d.used))
        if keep:
            d.add(pick(rng, ["Keep the airframe the same.", "Don't change the body or fins."], "xk", d.used))
    elif flaw == "apogee_low":
        alt = alt_about(rng, f.apo, imperial)
        d.targets["apogee_m"] = {"value": alt.value_m, "kind": "about"}
        keep = ["body_diameter"] if rng.random() < 0.5 else []
        d.add(pick(rng, [f"It only reaches {{OBSERVED}}; I need about {alt.text}.",
                         f"Apogee comes out at {{OBSERVED}}, short of the {alt.text} I want.",
                         f"The sim says {{OBSERVED}}. Target is around {alt.text}."], "xf", d.used))
        if keep and f.D:
            d.add(pick(rng, ["Keep the same body diameter.", "Same tube size, please."], "xk", d.used))
        if f.max_class and rng.random() < 0.5:
            d.apply(ax_cert(rng, f, False, d.used))
    elif flaw == "apogee_high":
        cap = f.apo * rng.uniform(0.75, 0.88)
        alt = alt_cap(cap, imperial)
        d.targets["apogee_m"] = {"value": alt.value_m, "kind": "max"}
        d.add(pick(rng, [f"It goes to {{OBSERVED}}, but our waiver is {alt.text}. Bring it under that.",
                         f"Apogee is {{OBSERVED}}, over our {alt.text} ceiling.",
                         f"The sim shows {{OBSERVED}}; the field limit is {alt.text}."], "xf", d.used))
        if rng.random() < 0.5:
            txt, v = landing_limit(rng)
            d.targets["ground_hit_ms"] = {"value": v, "kind": "max"}
            d.add(f"Still needs to land under {txt}.")
    else:  # rail_exit_slow
        rc = rail_choice(rng, f.r, imperial)
        if rc:
            d.sim["rail_length_m"] = rc[1]
            d.axes.append("rail_length")
            d.add(pick(rng, [f"It leaves our {rc[0]} rail at only {{OBSERVED}}.",
                             f"Rail exit speed is {{OBSERVED}} off {with_article(rc[0])} rail, too slow."], "xf", d.used))
        else:
            d.add(pick(rng, ["It leaves the rail at only {OBSERVED}.", "Rail exit speed is just {OBSERVED}."], "xf", d.used))
        keep = ["body_diameter"]
        d.add(pick(rng, ["Fix that without changing the tube size.", "Keep the same body tube."], "xk", d.used))
        if f.apo_ok and rng.random() < 0.6:
            alt = alt_floor(rng, f.apo * 0.85, imperial)
            d.targets["apogee_m"] = {"value": alt.value_m, "kind": "min"}
            d.add(f"It should still clear {alt.text}.")
        else:
            txt, v = landing_limit(rng)
            d.targets["ground_hit_ms"] = {"value": v, "kind": "max"}
            d.add(f"It has to land under {txt} too.")
    d.fix_spec = {"flaw": flaw, "observed": FIX_FLAWS[flaw], "keep": keep,
                  "fill": {"{DESIGN_JSON}": "failing draft design JSON",
                           "{OBSERVED}": f"that draft's simulated {FIX_FLAWS[flaw]}, person-rounded with units"}}
    return d


def build_missing(rng, f: Facts, avoid_axes: set[str], variant: int) -> Draft:
    d = Draft("missing_info", choose_register(rng, ["casual", "beginner", "terse", "formal"]))
    imperial = rng.random() < 0.5
    alt = alt_about(rng, f.apo, imperial) if rng.random() < 0.65 else alt_floor(rng, f.apo, imperial)
    about = abs(alt.value_m - f.apo) / f.apo <= 0.035
    d.targets["apogee_m"] = {"value": alt.value_m, "kind": "about" if about else "min"}
    a = alt.text
    if about:
        opts = [f"Build me a rocket that goes about {a}.", f"Can you design a rocket for around {a}?",
                f"I need something that gets to {a} or so.", f"Rocket for roughly {a}, please.",
                f"What would get me to about {a}?", f"I'd like to reach about {a}. What should I build?",
                f"Looking for a design that flies to around {a}.", f"Design something for a {a} flight.",
                f"How would you build a rocket for about {a}?", f"{a}-ish rocket. Go."]
    else:
        opts = [f"I want a rocket that clears {a}.", f"Something that gets above {a}?",
                f"Need a design that beats {a}.", f"What can you build that reaches at least {a}?",
                f"Design a rocket that tops {a}.", f"Help me get past {a}."]
    opts = [o.replace(f"for a {a} flight", f"for {with_article(a)} flight") for o in opts]
    if d.terse:
        d.add(pick(rng, [f"rocket for {a}", f"{a}, design it", f"need {a} apogee"], "mi", d.used))
    else:
        d.add(pick(rng, opts, "mi", d.used))
        if rng.random() < 0.35:
            d.add(pick(rng, ["It's for a club launch next month.", "This is for a school project.",
                             "My son wants to fly it this summer.", "We've never flown anything this big.",
                             "Not sure where to start."], "mx", d.used))
    d.omitted = ["wind", "rail_length", "motor_limit", "landing_limit", "size_limit"]
    return d


def build_infeasible(rng, f: Facts, avoid_axes: set[str], variant: int) -> Draft:
    d = Draft("infeasible", choose_register(rng))
    d.feasible = False
    imperial = rng.random() < 0.4
    kinds = []
    m = f.all_m[0] if f.all_m else None
    cm = f.canon_of(m) if m else None
    if f.single_motor and f.named and cm and cm["class"]:
        kinds += ["motor_ceiling"] * 3
        if cm["diameter_m"] and cm["diameter_m"] >= 0.024:
            kinds += ["size_conflict"]
        if cm["avg_thrust_n"]:
            kinds += ["payload_twr"]
    if f.max_class and CLASSES.index(f.max_class) <= CLASSES.index("I"):
        kinds += ["cert_ceiling"] * 2
    if f.apo_ok and f.apo >= 400:
        kinds += ["descent_time"] * 2
    if f.apo_ok:
        kinds += ["wind_gate"]
    if f.max_class and CLASSES.index(f.max_class) >= CLASSES.index("L") and f.apo_ok:
        kinds += ["p_motor"]
    kind = rng.choice(kinds or ["wind_gate"])
    if kind == "wind_gate" and not f.apo_ok:
        kind = "cert_ceiling"
    d.used.append(kind)
    if kind == "motor_ceiling":
        ceil = CLASS_CEILING_M[cm["class"]]
        ask = max(4 * ceil, 5 * (f.apo or 0))
        ask = nice_ceil(ask, (1000, 1500, 2000, 2500, 3000, 4000, 5000, 6000, 8000, 10000, 12000, 15000, 20000,
                              25000, 30000, 40000, 50000, 60000, 80000, 100000))
        alt = alt_text_raw(ask, imperial, rng)
        mp = motor_phrase(cm, rng)
        d.targets["motor"] = {"value": [cm["designation"]], "kind": "exact"}
        d.targets["stages"] = {"value": 1, "kind": "exact"}
        d.targets["apogee_m"] = {"value": alt.value_m, "kind": "min"}
        d.add(pick(rng, [f"{alt.text} on a single {mp}.", f"Can I get {alt.text} out of a single {mp}?",
                         f"I want to hit {alt.text} with one {mp}, single stage.",
                         f"Design a single-stage rocket on {with_article(mp)} that reaches {alt.text}."] if not d.terse
                    else [f"{alt.text} on one {mp}, single stage"], "if", d.used))
        d.reason = (f"apogee: a single {display_name(cm)} ({cm['class']} class, "
                    f"~{fmt_num(round(cm['total_impulse_ns'] or CLASS_ceiling_ns(cm['class'])))} N·s) cannot lift any sensible "
                    f"airframe to {alt.text}; a realistic single-stage ceiling on that class is about {fmt_num(ceil)} m")
    elif kind == "cert_ceiling":
        c = cert_for_class(f.max_class)
        if c in ("low",):
            cls, ask, who = "D", 3500, ["Low-power motors only (D max)", "The field only allows D motors and smaller"]
        elif c in ("mid", "unknown"):
            cls, ask, who = "G", 9000, ["I'm not certified, so G motors max", "No HPR cert, nothing above a G"]
        else:
            cls, ask, who = "I", 15000, ["I'm Level 1", "I only have my L1 (H and I motors)"]
        alt = alt_text_raw(ask, imperial, rng)
        d.targets["motor_class"] = {"value": cls, "kind": "max"}
        d.targets["apogee_m"] = {"value": alt.value_m, "kind": "min"}
        lead = pick(rng, who, "ic", d.used)
        d.add(pick(rng, [f"{lead}. Design something that reaches {alt.text}.", f"{lead}, and I want {alt.text}.",
                         f"{lead}. What would it take to get to {alt.text}?"], "if", d.used))
        d.reason = (f"apogee vs motor limit: {alt.text} is far beyond what {cls}-class motors can reach, even staged "
                    f"(next class up tops out near {fmt_num(CLASS_CEILING_M[CLASSES[CLASSES.index(cls) + 1]])} m single-stage)")
    elif kind == "descent_time":
        alt = alt_about(rng, f.apo, imperial)
        h = alt.value_m
        tmax = nice_floor_ladder(1.25 * math.sqrt(2 * h / G), (5, 10, 15, 20, 25, 30, 40, 45, 50, 60, 75, 90))
        if tmax is None:  # extreme apogee: any plausible time cap still conflicts
            tmax = 90
        lt, lv = rng.choice([("5 m/s", 5.0), ("4 m/s", 4.0), ("15 ft/s", round(15 * FT, 2))])
        d.targets["apogee_m"] = {"value": h, "kind": "about"}
        d.targets["flight_time_s"] = {"value": float(tmax), "kind": "max"}
        d.targets["ground_hit_ms"] = {"value": lv, "kind": "max"}
        d.add(pick(rng, [f"From {alt.text}, under {tmax} s total flight, landing under {lt}.",
                         f"I need about {alt.text}, the whole flight done in under {tmax} seconds, and landing under {lt}.",
                         f"Go to about {alt.text} and be back on the ground within {tmax} s, touching down under {lt}."] if not d.terse
                    else [f"about {alt.text}, total flight under {tmax} s, land under {lt}"], "if", d.used))
        d.reason = (f"flight time vs apogee: even free fall from {alt.text} takes about "
                    f"{fmt_num(round(math.sqrt(2 * h / G)))} s, plus the climb, so a {tmax} s total flight cannot also land under {lt}")
    elif kind == "size_conflict":
        mm = cm["diameter_m"] * 1000
        body = nice_floor_ladder(mm - 4, (10, 12, 15, 18, 20, 22, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90))
        mp = motor_phrase(cm, rng)
        d.targets["motor"] = {"value": [cm["designation"]], "kind": "exact"}
        d.targets["body_diameter_m"] = {"value": body / 1000, "kind": "max"}
        txt, v = landing_limit(rng)
        d.targets["ground_hit_ms"] = {"value": v, "kind": "max"}
        d.add(pick(rng, [f"Use {with_article(mp)}, but the body can't be wider than {body} mm. Land under {txt}.",
                         f"I want {with_article(mp)} in a {body} mm airframe, landing under {txt}.",
                         f"Fit {with_article(mp)} into a body no wider than {body} mm and bring it down under {txt}."], "if", d.used))
        d.reason = (f"body diameter vs motor: the {display_name(cm)} is {round(mm)} mm across, "
                    f"so it cannot fit inside a body of at most {body} mm")
    elif kind == "payload_twr":
        thrust = cm["avg_thrust_n"]
        p = thrust / (G * 1.5)
        pk = nice_ceil(p, (0.1, 0.2, 0.25, 0.5, 1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10, 15, 20, 25, 30, 40, 50, 75, 100))
        if pk is None:
            pk = float(math.ceil(p / 10) * 10)
        ptxt = f"{int(pk * 1000)} g" if pk < 1 else f"{fmt_num(pk)} kg"
        mp = motor_phrase(cm, rng)
        d.targets["motor"] = {"value": [cm["designation"]], "kind": "exact"}
        d.targets["payload_kg"] = {"value": float(pk), "kind": "min"}
        txt, v = landing_limit(rng)
        d.targets["ground_hit_ms"] = {"value": v, "kind": "max"}
        d.add(pick(rng, [f"Carry {with_article(ptxt)} payload on {with_article(mp)} and land under {txt}.",
                         f"I need to loft {ptxt} of instruments with {with_article(mp)}, landing under {txt}.",
                         f"Can {with_article(mp)} fly {with_article(ptxt)} payload? Land it under {txt}."], "if", d.used))
        d.reason = (f"thrust-to-weight: the {display_name(cm)} averages about {fmt_num(round(thrust))} N, "
                    f"so {with_article(ptxt)} payload alone gives under 1.5:1, below the 3:1 minimum")
    elif kind == "wind_gate":
        alt = alt_about(rng, f.apo, imperial)
        wtxt, wv = (("25 mph", round(25 * MPH, 2)) if imperial else rng.choice([("12 m/s", 12.0), ("45 km/h", 12.5)]))
        d.targets["apogee_m"] = {"value": alt.value_m, "kind": "about"}
        d.sim["wind_ms"] = wv
        d.add(pick(rng, [f"We have to fly in {wtxt} wind tomorrow. Aim for about {alt.text}.",
                         f"Forecast is {wtxt} sustained and we can't reschedule. Design for about {alt.text}.",
                         f"Make it reach about {alt.text} in {wtxt} wind."], "if", d.used))
        d.reason = f"wind: {wtxt} is above the 20 mph (8.9 m/s) safety-code limit, so the flight cannot be made safely"
    else:  # p_motor
        alt = alt_about(rng, f.apo * 2.5, imperial)
        d.targets["apogee_m"] = {"value": alt.value_m, "kind": "about"}
        d.targets["total_impulse_ns"] = {"value": 81920.0, "kind": "max"}
        d.add(pick(rng, [f"Let's go big: a P motor, about {alt.text}.", f"Design a P-motor rocket for about {alt.text}.",
                         f"We want to fly a P to roughly {alt.text}."], "if", d.used))
        d.reason = "total impulse: a P motor exceeds the 40,960 N·s amateur limit (O class is the largest allowed)"
    d.targets["feasible"] = {"value": False, "kind": "exact"}
    if rng.random() < 0.3 and kind not in ("wind_gate",):
        d.cond(cond_wind(rng, f, imperial, d.terse, d.used), "wind")
    return d


def CLASS_ceiling_ns(c: str) -> float:
    return 2.5 * 2 ** CLASSES.index(c)


def build_timed(rng, f: Facts, avoid_axes: set[str], variant: int) -> Draft:
    d = Draft("timed", choose_register(rng, ["competition", "competition", "formal", "casual"]))
    imperial = rng.random() < 0.6
    alt = alt_about(rng, f.apo, imperial)
    d.targets["apogee_m"] = {"value": alt.value_m, "kind": "about"}
    v = rng.uniform(3.6, 4.6)
    t_c = f.t_ap + alt.value_m / v
    width = 5 if t_c < 60 else 10
    lo = int(round(t_c / 5) * 5)
    hi = lo + width
    t_min = f.t_ap + alt.value_m / 5.7
    if lo < t_min * 1.05:
        lo = int(math.ceil(t_min * 1.05 / 5) * 5)
        hi = lo + width
    d.targets["flight_time_s"] = {"value": [float(lo), float(hi)], "kind": "range"}
    pay = ""
    if f.payload >= 0.03 or rng.random() < 0.5:
        g = rng.choice([50, 60, 60, 100]) if f.payload < 0.03 else int(nice_floor(f.payload * 1000, (50, 25, 10), lo=0.75))
        what = rng.choice(["egg", "payload", "raw egg"]) if g <= 60 else "payload"
        pay = with_article(f"{g} g {what}") if what != "egg" else "an egg (about 60 g)" if g == 60 else with_article(f"{g} g egg")
        d.targets["payload_kg"] = {"value": g / 1000 if "egg (about" not in pay else 0.06, "kind": "min"}
    lead = pick(rng, [
        (f"Carry {pay} to {alt.text} and stay up {lo} to {hi} s." if pay else f"Hit {alt.text} and stay up {lo} to {hi} s."),
        (f"Contest rules: {pay}, apogee around {alt.text}, total flight between {lo} and {hi} seconds." if pay
         else f"Contest rules: apogee around {alt.text}, total flight between {lo} and {hi} seconds."),
        (f"We need about {alt.text} with {pay}, and the flight time window is {lo}-{hi} s." if pay
         else f"We need about {alt.text}, and the flight time window is {lo}-{hi} s."),
    ], "tl", d.used)
    d.add(lead)
    if f.max_class and rng.random() < 0.6:
        cls = f.max_class if CLASSES.index(f.max_class) >= CLASSES.index("F") else "F"
        d.targets["motor_class"] = {"value": cls, "kind": "max"}
        d.add(pick(rng, [f"Motors are limited to {cls} or smaller.", f"{cls} impulse max under the rules."], "tm", d.used))
    if rng.random() < 0.4:
        d.cond(cond_wind(rng, f, imperial, d.terse, d.used), "wind")
    return d


BUILDERS = {"altitude": build_altitude, "fixed_motor": build_fixed_motor, "recovery": build_recovery,
            "multi": build_multi, "fix": build_fix, "missing_info": build_missing,
            "infeasible": build_infeasible, "timed": build_timed}


# =========================================================================== eligibility / allocation

def eligible(f: Facts) -> dict[str, bool]:
    return {
        "altitude": f.apo_ok,
        "fixed_motor": f.single_motor and f.named,
        "recovery": f.apo_ok and f.apo >= 100,
        "multi": f.multi,
        "fix": True,
        "missing_info": f.apo_ok,
        "infeasible": True,
        "timed": f.apo_ok and 120 <= f.apo <= 900 and not f.multi and (f.max_class or "Z") <= "H",
    }


def allocate(facts: list[Facts]) -> dict[str, list[str]]:
    rng = random.Random(SEED + ":alloc")
    slots = {f.g["group_id"]: (4 if f.multi else 3) for f in facts}
    total = sum(slots.values())
    quota = {k: int(round(v * total)) for k, v in MIX.items()}
    quota["altitude"] += total - sum(quota.values())
    plan: dict[str, list[str]] = {f.g["group_id"]: [] for f in facts}
    el = {f.g["group_id"]: eligible(f) for f in facts}
    by_id = {f.g["group_id"]: f for f in facts}

    def free(gid):
        return slots[gid] - len(plan[gid])

    # Two multi prompts per multi group first (only multi groups may have them).
    multi_groups = [f.g["group_id"] for f in facts if f.multi]
    rng.shuffle(multi_groups)
    for gid in multi_groups:
        for _ in range(2):
            if quota["multi"] > 0 and free(gid) > 0:
                plan[gid].append("multi")
                quota["multi"] -= 1
    for gid in multi_groups:
        if quota["multi"] > 0 and free(gid) > 1:
            plan[gid].append("multi")
            quota["multi"] -= 1

    order = ["timed", "fixed_motor", "infeasible", "fix", "missing_info", "recovery", "altitude"]
    for t in order:
        gids = [g for g in plan if el[g][t]]
        rng.shuffle(gids)
        # Groups with the fewest options get first pick of scarce types.
        gids.sort(key=lambda g: sum(el[g].values()))
        passes = 0
        while quota[t] > 0 and passes < 3:
            progressed = False
            for gid in gids:
                if quota[t] <= 0:
                    break
                cap_same = 2 if t == "altitude" else 1
                if free(gid) > 0 and plan[gid].count(t) < cap_same + (1 if passes == 2 and t == "altitude" else 0):
                    if passes == 0 and t in plan[gid]:
                        continue
                    plan[gid].append(t)
                    quota[t] -= 1
                    progressed = True
            passes += 1
            if not progressed and passes >= 2:
                break
    # Fill anything left with whatever the group is eligible for, least-used first.
    for gid in plan:
        while free(gid) > 0:
            opts = [t for t in order if el[gid][t] and plan[gid].count(t) < 2]
            if not opts:
                break
            t = min(opts, key=lambda x: (plan[gid].count(x), order.index(x)))
            plan[gid].append(t)
    return plan


# =========================================================================== family generation

def goal_set(p: dict) -> frozenset:
    return frozenset((k, json.dumps(v, sort_keys=True)) for k, v in p["targets"].items() if k in GOAL_KEYS)


def constraint_set(p: dict) -> frozenset:
    c = {(k, json.dumps(v, sort_keys=True)) for k, v in p["targets"].items() if k not in GOAL_KEYS}
    c |= {("sim:" + k, json.dumps(v)) for k, v in p["sim_conditions"].items()}
    return frozenset(c)


def nested_pair(a: dict, b: dict) -> bool:
    if goal_set(a) != goal_set(b):
        return False
    ca, cb = constraint_set(a), constraint_set(b)
    return ca < cb or cb < ca or ca == cb


def skeleton(text: str) -> str:
    s = re.sub(r"\{[A-Z_]+\}", "<X>", text)
    s = re.sub(r"\b(?:AeroTech|Cesaroni|Estes|Loki|Quest|Klima|AMW|Apogee)\b", "<MFR>", s)
    s = re.sub(r"\b[A-P]-?\d{1,5}[A-Z]{0,3}(?:-\d+)?\b", "<M>", s)
    s = re.sub(r"\d[\d,]*(?:\.\d+)?", "<N>", s)
    return s


def template_id(used: list[str]) -> str:
    return "|".join(used)


def finalize(d: Draft, rng: random.Random, f: Facts, idx: int) -> dict:
    text = d.render(rng)
    for k in list(d.targets):
        assert k in contract.TARGET_KEYS, k
    missing = sorted(set(d.omitted) | set(missing_list(d))) if d.ptype == "missing_info" else missing_list(d)
    rec = {
        "prompt_id": f"{f.g['group_id']}__p{idx}",
        "group_id": f.g["group_id"],
        "split": f.g["split"],
        "prompt_type": d.ptype,
        "template_id": template_id(d.used),
        "user_text": text,
        "targets": d.targets,
        "sim_conditions": d.sim,
        "missing_info": missing,
        "expected_feasible": d.feasible,
        "infeasible_reason": d.reason,
        "needs_design": d.needs_design,
        "reference": f.r,
        "prompt_version": PROMPT_VERSION,
    }
    if d.needs_design:
        rec["fix_spec"] = d.fix_spec
    return rec


def build_family(f: Facts, types: list[str]) -> list[dict]:
    out: list[dict] = []
    avoid: set[str] = set()
    counts: Counter = Counter()
    for i, t in enumerate(types):
        for attempt in range(25):
            rng = random.Random(f"{SEED}:{f.g['group_id']}:{i}:{t}:{attempt}")
            d = BUILDERS[t](rng, f, avoid, counts[t] + attempt)
            if not any(k in GOAL_KEYS for k in d.targets):
                continue
            rec = finalize(d, rng, f, i + 1)
            if any(nested_pair(rec, o) for o in out):
                continue
            if any(rec["user_text"] == o["user_text"] for o in out):
                continue
            out.append(rec)
            avoid |= set(d.axes)
            counts[t] += 1
            break
        else:
            raise RuntimeError(f"could not build a {t} prompt for {f.g['group_id']}")
    return out


# =========================================================================== report

def shares(c: Counter, n: int) -> dict:
    return {k: round(v / n, 4) for k, v in sorted(c.items())}


def write_report(prompts: list[dict], groups: dict, renames: Counter, subs: Counter,
                 missing: Counter) -> str:
    n = len(prompts)
    types = Counter(p["prompt_type"] for p in prompts)
    by_split = Counter(p["split"] for p in prompts)
    ts = Counter((p["prompt_type"], p["split"]) for p in prompts)
    per_group = Counter(p["group_id"] for p in prompts)
    dist = Counter(per_group.values())
    tmpl = Counter(p["template_id"] for p in prompts)
    skel = Counter(skeleton(p["user_text"]) for p in prompts)
    gsplit = Counter(g["split"] for g in groups["groups"])
    lines = [
        "# prompts_v1 report", "",
        f"Generated by `sftgen/prompts.py` (seed `{SEED}`, {PROMPT_VERSION}) from `sftgen/out/groups.json`.", "",
        f"- Prompts: **{n}** from **{len(per_group)}** groups ({len(groups['groups'])} groups total).",
        f"- Groups per split: {dict(sorted(gsplit.items()))}. Prompts per split: {dict(sorted(by_split.items()))}.",
        f"- Prompts per group: max **{max(per_group.values())}**, distribution {dict(sorted(dist.items()))}.",
        f"- Most common composed template: **{tmpl.most_common(1)[0][1]}** prompts ({tmpl.most_common(1)[0][1] / n:.1%}); "
        f"{len(tmpl)} distinct templates.",
        f"- Most common skeleton (numbers and motor names stripped): **{skel.most_common(1)[0][1]}** prompts "
        f"({skel.most_common(1)[0][1] / n:.1%}); {len(skel)} distinct skeletons.",
        f"- Infeasible prompts: {sum(1 for p in prompts if not p['expected_feasible'])}; fix-a-design prompts needing a "
        f"draft: {sum(1 for p in prompts if p['needs_design'])}.", "",
        "## Mix per prompt type", "",
        "| type | count | share | spec | train | val | test |", "|---|---|---|---|---|---|---|",
    ]
    spec = {"altitude": "30%", "fixed_motor": "15%", "recovery": "15%", "multi": "10%", "fix": "10%",
            "missing_info": "10%", "infeasible": "5-10%", "timed": "<=5%"}
    for t in MIX:
        lines.append(f"| {t} | {types[t]} | {types[t] / n:.1%} | {spec[t]} | {ts[(t, 'train')]} | {ts[(t, 'val')]} | {ts[(t, 'test')]} |")
    lines += ["", "## Target keys used", "", "| key | prompts |", "|---|---|"]
    kc = Counter(k for p in prompts for k in p["targets"])
    for k, v in kc.most_common():
        lines.append(f"| {k} | {v} |")
    sc = Counter(k for p in prompts for k in p["sim_conditions"])
    lines += ["", "Sim-condition overrides stated in prompts: " + ", ".join(f"{k} {v}" for k, v in sc.most_common()) + ".", "",
              "## Motor canonicalisation", "",
              "`targets.motor` values are canonical pinned motor-DB designations (`sftgen.motors.resolve` with the "
              ".ork manufacturer hint); prompt text keeps the hobbyist name.", ""]
    if renames:
        lines.append(f"- {sum(renames.values())} reference motor entries renamed to the canonical designation:")
        for (raw, des), n in sorted(renames.items()):
            lines.append(f"  - `{raw}` -> `{des}` ({n} entries)")
    if subs:
        lines.append("- Reference motors absent from the pinned DB, substituted by the closest same-maker / "
                     "same-diameter motor in text and targets:")
        for (raw, des), n in sorted(subs.items()):
            lines.append(f"  - `{raw}` -> `{des}` ({n} entries)")
    if missing:
        lines.append("- Reference motors with no pinned-DB entry and no same-maker/diameter substitute; never "
                     "named in text or targets (`reference.motors_resolved` = null):")
        for des, n in sorted(missing.items()):
            lines.append(f"  - `{des}` ({n} entries)")
    lines.append("")
    lines += ["## Dedup decisions", "",
              f"- Old rows: {groups['n_rows']}; source files: {groups['n_files']}; groups after merging: {groups['n_groups']}.",
              f"- Exact duplicate rows dropped ({len(groups['exact_duplicate_rows'])}):"]
    for x in groups["exact_duplicate_rows"]:
        lines.append(f"  - `{x['dropped']}` ({x['file']}) duplicates `{x['duplicate_of']}` ({x['duplicate_of_file']})")
    lines.append(f"- Renamed copies merged into one group ({len(groups['merged_copies'])} pairs):")
    for x in groups["merged_copies"]:
        lines.append(f"  - `{x['a']}` + `{x['b']}`: {x['reason']}")
    lines.append("- Checked and not merged:")
    for x in groups["checked_not_merged"]:
        lines.append(f"  - `{x['a']}` vs `{x['b']}`: {x['reason']}")
    fams = Counter(g["family"] for g in groups["groups"])
    lines.append("- Near-variant families kept in one split (same project, different designs): " +
                 ", ".join(f"{k} ({v} groups)" for k, v in fams.most_common() if v > 1) + ".")
    lines += ["", "## 25 random sample prompts", ""]
    rng = random.Random(SEED + ":report")
    for p in rng.sample(prompts, 25):
        lines.append(f"- **{p['prompt_type']}** `{p['prompt_id']}` ({p['split']}): {p['user_text']}")
        lines.append(f"  - targets: `{json.dumps(p['targets'], ensure_ascii=False)}`"
                     + (f"; sim: `{json.dumps(p['sim_conditions'])}`" if p["sim_conditions"] else "")
                     + (f"; infeasible: {p['infeasible_reason']}" if p["infeasible_reason"] else "")
                     + (f"; fix_spec: `{json.dumps(p['fix_spec'])}`" if p.get("fix_spec") else ""))
    lines += ["", "## Not satisfied / needs a decision", ""] + NOTES
    return "\n".join(lines) + "\n"


NOTES = [
    "- Two-stage/cluster sources are thin: only the multi-stage or multi-motor groups can back those prompts, so "
    "they carry 4 prompts each (2-3 of them multi) and single designs carry 3. More multi-stage sources are still needed (spec 8).",
    "- `motor` targets hold the canonical pinned motor-DB designation (`sftgen.motors.resolve` with the .ork "
    "manufacturer hint; e.g. .ork 'I216-CL(I)' -> '636I216-14A', 'G54-RL' -> '159G54-12A'), while the prompt text "
    "keeps the hobbyist name (DB common name where it exists: 'I216', 'a Cesaroni G54', 'an AMW N4000'). "
    "`reference.motors_resolved` carries the same resolved entry per motor (null when absent from the DB).",
    "- Fix prompts carry `{DESIGN_JSON}` and `{OBSERVED}` placeholders; the stage that injects the failing draft must "
    "also fill `{OBSERVED}` with that draft's simulated value, person-rounded (e.g. '0.6 cal', '9 m/s').",
    "- Two-stage prompts that name per-stage classes ('an I booster and a G sustainer') can only be encoded as "
    "`stages` + `motor_class` max with the current TARGET_KEYS; per-stage class limits are not checkable.",
    "- Drift and flight-time limits in recovery prompts use a rough descent model (drogue 25 m/s, main 5 m/s, "
    "x1.35-1.6 margin); they are feasible for a sensible dual-deploy/chute design but not proven by the reference sim.",
    "- Reference motors missing from the pinned DB are substituted by the closest same-maker / same-diameter "
    "motor when a prompt would name them (AMW 'O3800' 98 mm -> 'BB-98-17500' / N4000). Designs whose reference "
    "motor is custom or has no same-maker substitute (KERON, GragasMAY24, Amalia, Team01, HyperTEK L540, ASAT "
    "M2544, NKJ E17, LFS L839, UBI fenix...) never get the motor named; their prompts use altitude, size and "
    "class limits only.",
    "- Infeasible ceilings use a hand-set per-class single-stage altitude table (`CLASS_CEILING_M`) with a 4x margin; "
    "worth a sanity check by someone who knows the current class records.",
    "- `missing_info` is populated on every row, not only the 10% missing-information prompts: it always lists "
    "important items the prompt leaves unstated (wind, rail length, landing limit, motor limit, size limit, "
    "recovery type). On `missing_info` rows the omission is deliberate and drives the stated-assumption behaviour; "
    "elsewhere it is descriptive metadata.",
    "- 15 source files could not be resolved to a real `.ork` in `ork/` (see `groups.json` `ork_paths` = null); "
    "their references come from the old trace text and the `<design>` flight block only, so motor per-stage "
    "detail and stored-sim conditions may be missing there.",
]


# =========================================================================== main

def main() -> None:
    groups = json.loads(GROUPS.read_text(encoding="utf-8"))
    facts = [Facts(g) for g in groups["groups"]]
    plan = allocate(facts)
    prompts: list[dict] = []
    for f in facts:
        prompts += build_family(f, plan[f.g["group_id"]])
    renames: Counter = Counter()
    subs: Counter = Counter()
    missing: Counter = Counter()
    for f in facts:
        for c in f.canon:
            if c is None:
                continue
            (subs if c["substituted"] else renames)[(c["raw"], c["designation"])] += 1
        for m, c in zip(f.all_m, f.canon):
            if c is None:
                missing[m["designation"]] += 1
    renames = Counter({k: v for k, v in renames.items() if k[0] != k[1]})
    OUT.write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in prompts), encoding="utf-8")
    REPORT.write_text(write_report(prompts, groups, renames, subs, missing), encoding="utf-8")
    n = len(prompts)
    print(f"{n} prompts -> {OUT.relative_to(HERE.parent)}")
    print("mix:", shares(Counter(p["prompt_type"] for p in prompts), n))
    print("max/group:", max(Counter(p["group_id"] for p in prompts).values()))
    sk = Counter(skeleton(p["user_text"]) for p in prompts).most_common(1)[0]
    tm = Counter(p["template_id"] for p in prompts).most_common(1)[0]
    print(f"max skeleton share {sk[1] / n:.3f}: {sk[0]!r}")
    print(f"max template share {tm[1] / n:.3f}: {tm[0]!r}")


if __name__ == "__main__":
    main()
