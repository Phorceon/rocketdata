"""Build the RL prompt set: reference prompts rewritten to match the reward's own flights.

The reference prompts were written from flights under each design's own stored
launch settings and densities. The reward flies its own conditions (sea level,
a rail by motor class, the material table's densities, three winds), so some
prompt numbers no longer match what the reward measures. This tool rewrites
every stated number from the reward's own nominal flight of the reference
design, so that the prompt text, the requirements record and the reward's
physics agree, and every kept reference scores at the top on its own prompt.

Usage (from the folder that holds rocket_reward; Java through the usual
ROCKET_REWARD_JAVA_HOME and ROCKET_REWARD_JAR variables):

    python -m rocket_reward.tools.build_rl_prompts --meta META.jsonl --out-dir DIR [--workers 4]

It writes DIR/rl_prompts_v1.jsonl, DIR/excluded_references.jsonl and DIR/README.md.

What happens to one reference row:

1. Wind fix. A stated wind that disagrees with the wind the reference flew in,
   while every sibling prompt of the same design agrees with it, is rewritten
   to the reference wind (the one known case is V4-0099 casual).
2. Measure. The reference answer is scored through the whole ladder with the
   record parsed from the prompt, except that a stated landing limit is set to
   limits.LANDING_HARD_MAX_MS for this run: an old landing number must not stop
   a sound rocket before it is measured. The measured values are the ones the
   targets stage reads (Result.flags["stage_info"]["targets"]).
3. Keep only references that pass stages 1-6, fly every motor the prompt names
   and are of the class it names. Everything else is excluded with the stage
   and the reason.
4. Rewrite every stated number in place, last to first, keeping the unit,
   thousands separators and decimals as written (see `rewrite_prompt`):
   "about" gets the measured value, "max" the measured value plus MARGINS
   rounded up, "min" minus MARGINS rounded down. Wind and motors stay.
5. Re-parse the new text, build the record from it (tol 0.0 on every "max" and
   "min" target: the margin is in the number), and prove it: the same fields
   and kinds as before, no unplaced number, and the reference scores at least
   PROOF_MIN on its own new record.
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import re
import statistics
import sys
from dataclasses import dataclass, field
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

from rocket_reward import limits
from rocket_reward.cli import read_numbered_rows
from rocket_reward.records import TARGET_FIELDS, Requirements, Result
from rocket_reward.tools.build_requirements import (WIND_MATCH_MS, Item, ParsedPrompt, _row_key, parse_prompt,
                                                    to_requirements)
from rocket_reward.tools.calibrate import _answer_text, _block_hash

# ---------------------------------------------------------------------------
# rewriting rules (prompt data, not reward tuning: they only decide which
# number the new prompt states)

# Headroom added to a measured value for a "max" target (taken away for "min").
MARGINS: dict[str, float] = {
    "landing_ms": 0.10,
    "flight_time_s": 0.05,
    "mass_kg": 0.05,
    "body_diameter_m": 0.02,
    # Not stated as max/min in today's prompts; the same 5% as times and mass.
    "apogee_m": 0.05, "time_to_apogee_s": 0.05, "max_velocity_ms": 0.05, "max_accel_ms2": 0.05,
}
# Rounding up may add at most this many times the margin again before one
# more decimal is written ("under 3 inches" for a 2.6 in body becomes 2.7).
ROUNDING_SLACK_MARGINS = 1.0
# An "about" number is written to within this share of the measured value
# (or half the prompt's tolerance, whichever is smaller) before one more
# decimal is written: "about 2 km" stays for 1.97 km, becomes 1.73 km for 1.73.
ABOUT_ROUNDING_MAX = 0.02
EXTRA_DECIMALS_MAX = 3
# A kept reference must score at least this on its own new prompt.
PROOF_MIN = 0.99

OUT_PROMPTS = "rl_prompts_v1.jsonl"
OUT_EXCLUDED = "excluded_references.jsonl"
OUT_README = "README.md"

_NUMBER_WORDS = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten")
_PLURAL_UNITS = {"minute": "minutes", "second": "seconds", "inch": "inches"}
_REWRITTEN = set(TARGET_FIELDS)


# ---------------------------------------------------------------------------
# numbers in the written style


def _decimals_of(number_text: str) -> int:
    """How many decimals a number is written with ("117.3" -> 1, "1,600" -> 0)."""
    t = number_text.replace(",", "")
    return len(t.split(".", 1)[1]) if "." in t else 0


def round_written(value: float, decimals: int, mode: str) -> float:
    """`value` rounded to `decimals` places: mode "nearest" (halves up), "up" or
    "down". The value is first cut to 9 significant digits, so float noise
    (3.0 * 1.1 = 3.3000000000000003) never rounds up a whole step."""
    rounding = {"nearest": ROUND_HALF_UP, "up": ROUND_CEILING, "down": ROUND_FLOOR}[mode]
    q = Decimal(1).scaleb(-decimals)
    return float(Decimal(f"{value:.9g}").quantize(q, rounding=rounding))


def format_written(value: float, decimals: int, commas: bool) -> str:
    """A number with `decimals` places, with thousands separators when `commas`."""
    return f"{value:,.{decimals}f}" if commas else f"{value:.{decimals}f}"


def _word_number(k: int, like: str) -> str:
    """A whole number 1-10 spelled out, capitalised like `like`."""
    w = _NUMBER_WORDS[k]
    return w.capitalize() if like[:1].isupper() else w


def _inflect_unit(unit: str, value: float) -> str:
    """'minute' -> 'minutes' when the new number is not 1 (and back), keeping
    the capital letter. Other units are returned as written."""
    low = unit.lower()
    if value != 1 and low in _PLURAL_UNITS:
        new = _PLURAL_UNITS[low]
    elif value == 1 and low in _PLURAL_UNITS.values():
        new = next(k for k, v in _PLURAL_UNITS.items() if v == low)
    else:
        return unit
    return new.capitalize() if unit[:1].isupper() else new


def _word_candidates(item: Item, text: str) -> list[tuple[float, str]]:
    """Every value the spelled-out number of `item` can take without adding or
    removing a word, as (value in the stated unit, text over the number span)."""
    num = text[item.span[0]:item.span[1]]
    low = num.lower()
    if item.unit_span == item.span or low in ("a", "an") or low.startswith("half"):
        return [(float(item.stated), num)]          # "a minute and a half", "a minute", "half a"
    if "and a half" in low:
        return [(k + 0.5, f"{_word_number(k, num)} and a half") for k in range(1, 10)]
    return [(float(k), _word_number(k, num)) for k in range(1, 11)]


@dataclass
class NumberChange:
    """One rewritten number: where it sits, what it said and what it says now."""

    field: str
    kind: str
    start: int                 # replaced text, start and end in the old prompt
    end: int
    old_text: str
    new_text: str
    old_value: float           # SI
    new_value: float           # SI, as written
    measured: float            # SI
    extra_decimals: int = 0    # decimals written beyond the original's
    words_to_digits: bool = False


def _accept(kind: str, v: float, m: float, margin: float, cap: Optional[float], about_max: float) -> bool:
    """Is `v` (stated unit) a good written number for measured `m`?"""
    if v <= 0:
        return False
    if kind == "about":
        return abs(v - m) <= about_max * m
    if kind == "max":
        return v >= m and v <= m * (1 + margin * (1 + ROUNDING_SLACK_MARGINS)) * (1 + 1e-9) and (
            cap is None or v <= cap * (1 + 1e-9))
    return v <= m and v >= m * (1 - margin * (1 + ROUNDING_SLACK_MARGINS)) * (1 - 1e-9)


def rewrite_item(item: Item, text: str, measured_si: float) -> NumberChange:
    """The new written number for one stated target, from the measured value
    (SI units). Raises ValueError when no written number fits."""
    if item.factor is None or item.stated is None or not item.factor > 0:
        raise ValueError(f"{item.field}: the stated number has no unit factor")
    factor = item.factor
    m = measured_si / factor
    margin = MARGINS.get(item.field, 0.05)
    cap = limits.LANDING_HARD_MAX_MS / factor if item.field == "landing_ms" else None
    tol = item.tol if item.tol is not None else 0.05
    about_max = min(ABOUT_ROUNDING_MAX, tol / 2)
    if item.kind == "about":
        target, mode = m, "nearest"
    elif item.kind == "max":
        target, mode = m * (1 + margin), "up"
        if cap is not None:
            target = min(target, cap)
    elif item.kind == "min":
        target, mode = m * (1 - margin), "down"
    else:
        raise ValueError(f"{item.field}: unknown kind {item.kind!r}")

    def change(new_text: str, v: float, start: int, end: int, extra: int, digits: bool) -> NumberChange:
        return NumberChange(item.field, item.kind, start, end, text[start:end], new_text, float(item.value),
                            round(v * factor, 9), measured_si, extra, digits)

    s0, s1 = item.span
    if item.form == "words":
        cands = _word_candidates(item, text)
        if mode == "nearest":
            pick = min(cands, key=lambda c: (abs(c[0] - target), c[0]))
        elif mode == "up":
            pick = min((c for c in cands if c[0] >= target - 1e-9), key=lambda c: c[0], default=None)
        else:
            pick = max((c for c in cands if c[0] <= target + 1e-9), key=lambda c: c[0], default=None)
        if pick is not None and _accept(item.kind, pick[0], m, margin, cap, about_max):
            return change(pick[1], pick[0], s0, s1, 0, False)
        base, commas = 0, False
    else:
        base, commas = _decimals_of(item.number_text), "," in item.number_text
    for extra in range(EXTRA_DECIMALS_MAX + 1):
        d = base + extra
        v = round_written(target, d, mode)
        if mode == "up" and cap is not None and v > cap:
            v = round_written(cap, d, "down")
        if not _accept(item.kind, v, m, margin, cap, about_max):
            continue
        number = format_written(v, d, commas)
        if item.form == "words" and item.unit_span == item.span:
            # "a minute and a half": number and unit share the span
            unit = _inflect_unit(item.unit or "", v)
            return change(f"{number} {unit}", v, s0, s1, extra, True)
        unit = item.unit or ""
        new_unit = _inflect_unit(unit, v)
        if new_unit != unit and item.unit_span is not None:
            u0, u1 = item.unit_span
            return change(number + text[s1:u0] + new_unit, v, s0, u1, extra, item.form == "words")
        return change(number, v, s0, s1, extra, item.form == "words")
    raise ValueError(f"{item.field}: no written number within the rules fits the measured {m:.6g} {item.unit}")


def apply_changes(text: str, changes: Sequence[NumberChange]) -> str:
    """`text` with every change applied, last to first so earlier spans stay valid."""
    out = text
    last = len(text) + 1
    for c in sorted(changes, key=lambda c: c.start, reverse=True):
        if c.end > last:
            raise ValueError("two rewritten numbers overlap")
        if out[c.start:c.end] != c.old_text:
            raise ValueError(f"the text at {c.start}-{c.end} is not {c.old_text!r}")
        out = out[:c.start] + c.new_text + out[c.end:]
        last = c.start
    return out


def rewrite_prompt(text: str, parsed: ParsedPrompt, measured: dict[str, Optional[float]]
                   ) -> tuple[str, list[NumberChange]]:
    """Rewrite every stated target number of `parsed` (the parse of `text`)
    from `measured` (field -> SI value). Wind, motors and anything else stay.
    Raises ValueError when a stated field has no measured value."""
    changes = []
    for it in parsed.items:
        if it.field not in _REWRITTEN:
            continue
        m = measured.get(it.field)
        if m is None or not math.isfinite(m) or m <= 0:
            raise ValueError(f"the reward measured no {it.field} for this design")
        changes.append(rewrite_item(it, text, float(m)))
    return apply_changes(text, changes), changes


def _shape(parsed: ParsedPrompt) -> list[tuple[str, str, Optional[float]]]:
    """Fields, kinds and tolerances of the stated items, in text order."""
    return [(i.field, i.kind, i.tol) for i in parsed.items]


def record_from_text(row_id: str, text: str) -> tuple[ParsedPrompt, dict[str, Any]]:
    """Parse `text` and build its record with tol 0.0 on every "max" and "min"
    target (the margin is already in the number). Raises ValueError when the
    text does not make a valid record."""
    parsed = parse_prompt(text)
    rec = to_requirements(row_id, parsed)
    for name in TARGET_FIELDS:
        t = rec.get(name)
        if isinstance(t, dict) and t.get("kind") in ("max", "min"):
            t["tol"] = 0.0
    Requirements.from_dict(rec)
    return parsed, rec


# ---------------------------------------------------------------------------
# wind fix

def fix_winds(rows: Sequence[dict[str, Any]]) -> dict[int, tuple[str, NumberChange]]:
    """Rows (by index) whose stated wind disagrees with the wind their reference
    flew in while every sibling prompt of the same design agrees with it:
    the new text and the change. A sibling is a row with the same design block."""
    by_block: dict[str, list[int]] = collections.defaultdict(list)
    for i, r in enumerate(rows):
        by_block[_block_hash(_answer_text(r))].append(i)
    out: dict[int, tuple[str, NumberChange]] = {}
    for i, r in enumerate(rows):
        ref = (r.get("targets") or {}).get("wind_ms")
        if not isinstance(ref, (int, float)):
            continue
        text = r.get("prompt_text") or ""
        parsed = parse_prompt(text)
        winds = [w for w in parsed.by_field("wind_ms") if w.form == "digits"]
        if len(winds) != 1 or _wind_agrees(winds[0].value, ref):
            continue
        sib = [j for j in by_block[_block_hash(_answer_text(r))] if j != i]
        sib_winds = [w.value for j in sib for w in parse_prompt(rows[j].get("prompt_text") or "").by_field("wind_ms")]
        if not sib_winds or not all(_wind_agrees(v, ref) for v in sib_winds):
            continue
        w = winds[0]
        d, commas = _decimals_of(w.number_text), "," in w.number_text
        for extra in range(EXTRA_DECIMALS_MAX + 1):
            v = round_written(ref / w.factor, d + extra, "nearest")
            if _wind_agrees(v * w.factor, ref):
                break
        new = format_written(v, d + extra, commas)
        ch = NumberChange("wind_ms", "about", w.span[0], w.span[1], w.number_text, new, float(w.value),
                          round(v * w.factor, 9), float(ref), extra)
        out[i] = (apply_changes(text, [ch]), ch)
    return out


def _wind_agrees(stated: float, ref: float) -> bool:
    """The same rule build_requirements.cross_check uses for the wind."""
    return abs(stated - ref) <= max(WIND_MATCH_MS, 0.05 * ref)


# ---------------------------------------------------------------------------
# families

_PARENS_RE = re.compile(r"\([^)]*\)")
_DATE_RE = re.compile(r"\b\d{1,2}[.\-]\d{1,2}[.\-]\d{2,4}\b")
# Glued to the end of a name word: options and variants ("QuantumLeapCPR3K",
# "MiniBBXwithTerrierBooster", "ASTRAwFairing", "APEXJTentative").
_GLUED_SUFFIX_RE = re.compile(r"(?:with[a-z0-9]+|cpr3k|wfairing|tentative)$")
# A word from which the rest of the name is a size, version, motor or variant.
_MARKER_RE = re.compile(
    r"^(?:\d+mm\w*|\d+in|\d*adptr|\d+p\d+od|v\d+|mod\d+|configuration\w*|sim|subscale|frr|trans|"
    r"[a-o]\d{2,4}[a-z]*|longburn\w*|skinny\w*|nodeploymentbags|spinny\d*|[0-9a-f]{8,})$")


def family_name(source_file: str) -> str:
    """The kit a reference rocket belongs to, from its file name: lower case,
    no extension; text in brackets and dates removed; options glued to a word
    removed; everything from the first size, version, motor or variant word
    on removed (29mm, 38mmConfigurationE, 29-38ADPTR, 1p79OD, V2, mod24, SIM,
    Subscale, FRR, L1420, a hash); then trailing one- or two-digit numbers
    removed. "PML_AMRAAM4-withCPR3000_38mm" -> "pml amraam4",
    "NASA_Rocket_V3_L1420" -> "nasa rocket", "rocket_10" -> "rocket"."""
    name = re.sub(r"\.ork$", "", source_file.strip(), flags=re.IGNORECASE).lower()
    name = _DATE_RE.sub(" sim ", _PARENS_RE.sub(" ", name))
    words = []
    for w in re.split(r"[^a-z0-9]+", name):
        if not w:
            continue
        if words and _MARKER_RE.match(w):
            break
        w = _GLUED_SUFFIX_RE.sub("", w) if len(w) > 6 else w
        if w and words and w.startswith("with"):
            break
        if w:
            words.append(w)
    while len(words) > 1 and words[-1].isdigit() and len(words[-1]) <= 2:
        words.pop()
    return " ".join(words) or name


def families(rows: Sequence[dict[str, Any]]) -> list[str]:
    """One family per row: rows share a family when their file names give the
    same family_name, they share a group_id, or they share a design block.
    The family is named after the smallest family_name in it."""
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    keys = []
    for r in rows:
        src = str(r.get("source_file") or r.get("id") or "")
        name = "n:" + family_name(src)
        keys.append(name)
        union(name, "g:" + str(r.get("group_id") or r.get("id")))
        union(name, "b:" + _block_hash(_answer_text(r)))
    # Name each family after its smallest name key.
    best: dict[str, str] = {}
    for k in keys:
        root = find(k)
        best[root] = min(best.get(root, k), k)
    return [best[find(k)][2:] for k in keys]


# ---------------------------------------------------------------------------
# the build

Scorer = Callable[[list[str], list[Requirements]], list[Result]]


@dataclass
class Outcome:
    """What happened to one reference row."""

    index: int
    row_id: str
    kept: Optional[dict[str, Any]] = None
    excluded: Optional[dict[str, Any]] = None
    changes: list[NumberChange] = field(default_factory=list)
    wind_fix: Optional[NumberChange] = None


def _measured(result: Result) -> dict[str, Any]:
    """Target name -> measured value, from the targets stage's info."""
    info = result.flags.get("stage_info") if isinstance(result.flags, dict) else None
    rows = info.get("targets") if isinstance(info, dict) else None
    return {r["target"]: r.get("measured") for r in rows or [] if isinstance(r, dict) and "target" in r}


def _target_credits(result: Result) -> dict[str, float]:
    info = result.flags.get("stage_info") if isinstance(result.flags, dict) else None
    rows = info.get("targets") if isinstance(info, dict) else None
    return {r["target"]: r.get("credit") for r in rows or [] if isinstance(r, dict) and "target" in r}


def _measure_record(rec: dict[str, Any]) -> dict[str, Any]:
    """The record used to measure: the prompt's own, with a stated landing
    limit at the hard landing limit so an old number cannot stop a sound rocket."""
    out = json.loads(json.dumps(rec))
    if "landing_ms" in out:
        out["landing_ms"] = {"value": limits.LANDING_HARD_MAX_MS, "kind": "max", "tol": 0.0}
    return out


def _system_of(row: dict[str, Any]) -> Optional[str]:
    for m in row.get("messages") or []:
        if isinstance(m, dict) and m.get("role") == "system":
            return str(m.get("content") or "")
    return None


def _exclusion(row: dict[str, Any], row_id: str, stage: str, code: str, reason: str,
               score: Optional[float] = None) -> dict[str, Any]:
    return {"id": row_id, "group_id": row.get("group_id"), "split": row.get("split"),
            "prompt_style": row.get("prompt_style"), "source_file": row.get("source_file"),
            "stage": stage, "code": code, "reason": reason,
            "score": None if score is None else round(score, 6)}


def build_rows(rows: Sequence[dict[str, Any]], scorer: Scorer) -> list[Outcome]:
    """Run the whole build (module notes, steps 1-5) on meta rows. `scorer`
    scores a batch of answers against their records (score_many with a pool)."""
    taken: set[str] = set()
    ids = [_row_key(r, taken) for r in rows]
    fams = families(rows)
    winds = fix_winds(rows)
    outcomes = [Outcome(i, ids[i]) for i in range(len(rows))]
    texts: list[str] = []
    parsed0: list[Optional[ParsedPrompt]] = []
    recs0: list[Optional[dict[str, Any]]] = []
    for i, r in enumerate(rows):
        text = r.get("prompt_text") or ""
        if i in winds:
            text, outcomes[i].wind_fix = winds[i]
        texts.append(text)
        p = parse_prompt(text)
        try:
            rec = to_requirements(ids[i], p)
        except ValueError as exc:
            outcomes[i].excluded = _exclusion(r, ids[i], "prompt", "prompt_unparsed",
                                              f"the prompt does not make a record: {exc}")
            p, rec = None, None
        parsed0.append(p)
        recs0.append(rec)

    todo = [i for i in range(len(rows)) if recs0[i] is not None]
    results = scorer([_answer_text(rows[i]) for i in todo],
                     [Requirements.from_dict(_measure_record(recs0[i])) for i in todo])
    proof: list[tuple[int, dict[str, Any], str]] = []
    for i, res in zip(todo, results):
        r, o = rows[i], outcomes[i]
        if res.score is None:
            o.excluded = _exclusion(r, ids[i], "dropped", "quarantined", "the reward hit an unexpected error")
            continue
        if res.stage != "targets":
            o.excluded = _exclusion(r, ids[i], res.stage, f"stage_{res.stage}",
                                    "; ".join(res.reasons[:3]) or f"stops at the {res.stage} stage", res.score)
            continue
        meas = _measured(res)
        credits = _target_credits(res)
        if "motors" in meas and credits.get("motors", 0) < 1:
            flown = (meas["motors"] or {}).get("flown") if isinstance(meas["motors"], dict) else None
            o.excluded = _exclusion(r, ids[i], "targets", "motor_not_flown",
                                    f"the prompt names {', '.join(recs0[i].get('motors', []))} but the design "
                                    f"flies {', '.join(flown or []) or 'no motor'} as the reward reads it",
                                    res.score)
            continue
        if "motor_class" in meas and credits.get("motor_class", 0) < 1:
            o.excluded = _exclusion(r, ids[i], "targets", "motor_class",
                                    "the design's largest motor is not of the class the prompt names", res.score)
            continue
        try:
            new_text, changes = rewrite_prompt(texts[i], parsed0[i], meas)
            new_parsed, rec = record_from_text(ids[i], new_text)
        except ValueError as exc:
            o.excluded = _exclusion(r, ids[i], "rewrite", "rewrite_failed", str(exc), res.score)
            continue
        if new_parsed.unassigned or _shape(new_parsed) != _shape(parsed0[i]) or \
                rec.get("motors") != recs0[i].get("motors") or rec.get("wind_ms") != recs0[i].get("wind_ms"):
            o.excluded = _exclusion(r, ids[i], "rewrite", "rewrite_changed_parse",
                                    f"the rewritten prompt reads differently: {new_text!r}", res.score)
            continue
        o.changes = changes
        proof.append((i, rec, new_text))

    results = scorer([_answer_text(rows[i]) for i, _, _ in proof],
                     [Requirements.from_dict(rec) for _, rec, _ in proof])
    for (i, rec, new_text), res in zip(proof, results):
        r, o = rows[i], outcomes[i]
        if res.score is None or res.score < PROOF_MIN:
            why = "; ".join((res.reasons + res.defects)[:4]) if res.score is not None else "quarantined"
            o.excluded = _exclusion(r, ids[i], res.stage, "proof_below_min",
                                    f"scores {res.score} on its own new prompt (needs {PROOF_MIN}): {why}",
                                    res.score)
            o.changes = []
            continue
        o.kept = {"id": ids[i], "group_id": r.get("group_id"), "family": fams[i], "split": r.get("split"),
                  "prompt_style": r.get("prompt_style"), "system": _system_of(r), "prompt": new_text,
                  "requirements": rec, "reference_score": round(res.score, 6), "leaks_family": False}
    train_fams = {fams[i] for i, r in enumerate(rows) if r.get("split") == "train"}
    for o in outcomes:
        if o.kept and o.kept["split"] in ("val", "test"):
            o.kept["leaks_family"] = o.kept["family"] in train_fams
    return outcomes


# ---------------------------------------------------------------------------
# writing

def _jsonl(rows: Sequence[dict[str, Any]]) -> str:
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)


def _md_table(header: Sequence[str], body: Sequence[Sequence[Any]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(str(c).replace("|", "\\|") for c in row) + " |" for row in body]
    return lines


def _signed_pct(x: float) -> str:
    return f"{x * 100:+.1f}%"


def readme_text(rows: Sequence[dict[str, Any]], outcomes: Sequence[Outcome], meta_name: str) -> str:
    """The README written next to the two JSONL files."""
    kept = [o.kept for o in outcomes if o.kept]
    excl = [o.excluded for o in outcomes if o.excluded]
    splits = ("train", "val", "test")
    styles = sorted({str(r.get("prompt_style")) for r in rows})
    fams = families(rows)
    systems = {s for s in (_system_of(r) for r in rows) if s is not None}
    out = ["# RL prompts v1", "",
           f"`{OUT_PROMPTS}` holds {len(kept)} prompts for reinforcement learning, one per line. Each is a "
           "reference prompt whose numbers were rewritten from the reward's own flight of the reference "
           "design, so the prompt text, its requirements record and the reward's physics agree, and the "
           f"reference answer scores at least {PROOF_MIN} on it. `{OUT_EXCLUDED}` lists the "
           f"{len(excl)} reference rows that were left out, with the stage and the reason.", "",
           "## Fields", "",
           "- `id`: the reference row and prompt style (`V4-0001:original`); also the record's id.",
           "- `group_id`, `split` (train / val / test) and `prompt_style`: as in the reference row.",
           "- `family`: the kit the rocket belongs to (see Families). Siblings of one kit share it.",
           f"- `system`: the exact system prompt the model was trained with ({len(systems)} distinct "
           "text in the reference rows).",
           "- `prompt`: the user prompt, rewritten.",
           "- `requirements`: the record to score against (`Requirements.from_dict`). Every `max` and `min` "
           "target carries `\"tol\": 0.0`: the margin is already in the number. An `about` target keeps the "
           "prompt's own tolerance (none written means 5%).",
           "- `reference_score`: what the reference answer scores on this record.",
           "- `leaks_family`: true for a val or test row whose family also has a train row in the "
           "reference set (the model saw a sibling rocket during fine-tuning).", "",
           "## How it was made", "",
           f"Source: `{meta_name}` ({len(rows)} reference rows). For every row:", "",
           "1. A stated wind that disagrees with the wind the reference flew in, while every sibling prompt of "
           "the same design agrees, is set to the reference wind "
           f"({sum(1 for o in outcomes if o.wind_fix)} row(s): "
           + (", ".join(f"{o.row_id} {o.wind_fix.old_text} -> {o.wind_fix.new_text} m/s"
                        for o in outcomes if o.wind_fix) or "none") + ").",
           "2. The reference answer is scored through the whole ladder with the record parsed from its prompt "
           f"(a stated landing limit is set to {limits.LANDING_HARD_MAX_MS:g} m/s for this run only, so an old "
           "number cannot stop a sound rocket before it is measured). The measured values are the ones the "
           "targets stage reads from the 1x-wind flight: times from the first ignition, the main section's "
           "landing speed, the widest main-body tube, the liftoff mass.",
           "3. Only references that pass stages 1-6 and fly the motors the prompt names are kept.",
           "4. Every stated number is rewritten in place, keeping the unit, thousands separators and "
           "decimals as written: `about` gets the measured value; `max` the measured value plus a margin, "
           "rounded up (landing speed +10% and never above "
           f"{limits.LANDING_HARD_MAX_MS:g} m/s, flight time +5%, mass +5%, body diameter +2%); `min` the "
           "measured value minus the margin, rounded down. Wind and motor names are not changed. When the "
           "written precision is too coarse (an `about` number more than 2% (or half its tolerance) off the "
           "measured value, or a rounded-up limit with more than twice its margin), one more decimal is "
           "written. A spelled-out number stays spelled out when a word fits (`four minutes` -> `three "
           "minutes`), else it becomes digits (`a minute` -> `1.4 minutes`).",
           "5. The new text is parsed again and must give the same fields and kinds with no unplaced "
           f"number; the reference must score at least {PROOF_MIN} on the new record.", "",
           "Rebuild (from the folder that holds `rocket_reward`, with `ROCKET_REWARD_JAVA_HOME` and "
           "`ROCKET_REWARD_JAR` set):", "",
           "```",
           f"python -m rocket_reward.tools.build_rl_prompts --meta {meta_name} --out-dir rocket_reward/prompts",
           "```", "",
           "The output is sorted by id and the same byte for byte on every run.", "",
           "## Counts", "", "Kept / all reference rows:", ""]
    body = []
    for st in styles + ["all"]:
        cells = [st]
        for sp in list(splits) + ["all"]:
            rs = [o for o, r in zip(outcomes, rows) if (st == "all" or r.get("prompt_style") == st)
                  and (sp == "all" or r.get("split") == sp)]
            cells.append(f"{sum(1 for o in rs if o.kept)} / {len(rs)}")
        body.append(cells)
    out += _md_table(["style"] + list(splits) + ["all"], body)
    leak = collections.Counter((k["split"], k["leaks_family"]) for k in kept)
    out += ["", "Kept val and test rows whose family has a train row (`leaks_family`): "
            + ", ".join(f"{sp} {leak[(sp, True)]} of {leak[(sp, True)] + leak[(sp, False)]}"
                        for sp in ("val", "test")) + ".", "",
            "Excluded rows by reason:", ""]
    reasons = collections.Counter((e["stage"], e["code"]) for e in excl)
    body = []
    for (stage, code), n in sorted(reasons.items(), key=lambda x: (-x[1], x[0])):
        per = collections.Counter(e["split"] for e in excl if (e["stage"], e["code"]) == (stage, code))
        sty = collections.Counter(e["prompt_style"] for e in excl if (e["stage"], e["code"]) == (stage, code))
        designs = sorted({str(e["id"]).split(":")[0].split("-casual")[0].split("-engineering")[0]
                          for e in excl if (e["stage"], e["code"]) == (stage, code)})
        body.append([stage, code, n, ", ".join(f"{sp} {per[sp]}" for sp in splits if per[sp]),
                     ", ".join(f"{s} {sty[s]}" for s in styles if sty[s]), ", ".join(designs)])
    out += _md_table(["stage", "reason", "rows", "by split", "by style", "designs"], body)

    out += ["", "## How far the numbers moved", "",
            "Over the kept prompts, per field and kind: how many numbers were stated, how many now read "
            "differently, and the change of the value (new over old, minus 1).", ""]
    groups: dict[tuple[str, str], list[NumberChange]] = collections.defaultdict(list)
    for o in outcomes:
        if o.kept:
            for c in o.changes:
                groups[(c.field, c.kind)].append(c)
    body = []
    for (f, k), cs in sorted(groups.items()):
        rel = [c.new_value / c.old_value - 1 for c in cs if c.old_value > 0]
        moved = sum(1 for c in cs if c.new_text != c.old_text)
        absr = sorted(abs(x) for x in rel)
        body.append([f, k, len(cs), moved, _signed_pct(statistics.median(rel)) if rel else "-",
                     f"{statistics.median(absr) * 100:.1f}%" if absr else "-",
                     f"{absr[-1] * 100:.1f}%" if absr else "-",
                     f"{min(rel) * 100:+.1f}% .. {max(rel) * 100:+.1f}%" if rel else "-",
                     sum(1 for c in cs if c.extra_decimals), sum(1 for c in cs if c.words_to_digits)])
    out += _md_table(["field", "kind", "stated", "text changed", "median change", "median size", "largest size",
                   "range", "one more decimal", "words to digits"], body)

    fam_rows: dict[str, list[int]] = collections.defaultdict(list)
    for i, f in enumerate(fams):
        fam_rows[f].append(i)
    big = sorted(fam_rows.items(), key=lambda x: (-len({rows[i].get("source_file") for i in x[1]}), x[0]))
    out += ["", "## Families", "",
            "A family groups the sibling rockets of one kit. It comes from the reference file name "
            "(`tools/build_rl_prompts.family_name`): lower case, no extension, text in brackets and dates "
            "removed, options glued to a word removed (`withCPR3000`, `CPR3K`, `wFairing`, `Tentative`), "
            "everything from the first size, version, motor or variant word on removed (`29mm`, "
            "`38mmConfigurationE`, `29-38ADPTR`, `1p79OD`, `V2`, `mod24`, `SIM`, `Subscale`, `FRR`, `L1420`, "
            "a hash), then trailing one- or two-digit numbers removed. Rows that share a group id or a design "
            "block are in one family too. Names that differ only in spelling are not merged.", "",
            f"{len(fam_rows)} families over {len({r.get('source_file') for r in rows})} reference files. "
            "The largest:", ""]
    body = []
    for name, idx in big[:15]:
        files = sorted({str(rows[i].get("source_file")) for i in idx})
        sp = collections.Counter(rows[i].get("split") for i in idx)
        body.append([f"`{name}`", len(files), ", ".join(f"{s} {sp[s]}" for s in splits if sp[s]),
                     ", ".join(files[:6]) + (" ..." if len(files) > 6 else "")])
    out += _md_table(["family", "files", "rows by split", "files (first 6)"], body)

    out += ["", "## Recommended use", "",
            "- Train RL on the rows with `split` train.",
            "- Use the val rows to pick a checkpoint and keep the test rows for the final number.",
            "- Report val and test results twice: on all rows and on the rows with `leaks_family` false, "
            "because a sibling of a leaking rocket was in the fine-tuning data.",
            "- Score with `Requirements.from_dict(row[\"requirements\"])`; the reward never reads the prompt "
            "text.", ""]
    return "\n".join(out)


def write_outputs(rows: Sequence[dict[str, Any]], outcomes: Sequence[Outcome], out_dir: Path,
                  meta_name: str) -> tuple[int, int]:
    """Write the three files; returns (kept, excluded)."""
    kept = sorted((o.kept for o in outcomes if o.kept), key=lambda k: k["id"])
    excl = sorted((o.excluded for o in outcomes if o.excluded), key=lambda e: e["id"])
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / OUT_PROMPTS).write_text(_jsonl(kept), encoding="utf-8", newline="\n")
    (out_dir / OUT_EXCLUDED).write_text(_jsonl(excl), encoding="utf-8", newline="\n")
    (out_dir / OUT_README).write_text(readme_text(rows, outcomes, meta_name), encoding="utf-8", newline="\n")
    return len(kept), len(excl)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m rocket_reward.tools.build_rl_prompts",
                                 description="Rewrite the reference prompts from the reward's own flights.")
    ap.add_argument("--meta", required=True, type=Path, help="reference rows (.jsonl)")
    ap.add_argument("--out-dir", required=True, type=Path, help="folder for the three output files")
    ap.add_argument("--workers", type=int, default=4, help="simulator helpers (default 4)")
    a = ap.parse_args(argv)
    from rocket_reward.scoring import ErrorTracker, score_many
    from rocket_reward.sim import SimPool

    rows = [r for _, r in read_numbered_rows(a.meta) if isinstance(r, dict)]
    with SimPool(a.workers) as pool:
        tracker = ErrorTracker(window=10**6, run=10**6)

        def scorer(answers: list[str], reqs: list[Requirements]) -> list[Result]:
            return score_many(answers, reqs, simulator=pool, tracker=tracker)

        outcomes = build_rows(rows, scorer)
    kept, excl = write_outputs(rows, outcomes, a.out_dir, a.meta.name)
    print(f"{len(rows)} reference rows: {kept} kept, {excl} excluded; wrote {a.out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
