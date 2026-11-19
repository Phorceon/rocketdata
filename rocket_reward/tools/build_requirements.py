"""Turn prompt text into requirement records for the reward.

The reward never reads prompt text while training, so every prompt needs a
record (records.Requirements) that lists exactly what the prompt asks for.
This tool reads the prompts, finds every stated requirement, and checks each
one against the reference rocket the prompt was written from.

Usage (from the folder that holds rocket_reward):

    python -m rocket_reward.tools.build_requirements parse --meta META.jsonl \\
        --out parsed.jsonl --report report.md

How a prompt is read (a few small rules, applied in this order):

1. Tokens. Every number in the text is found first. A number that is part of
   a motor designation ("H128W", "3147L935-P") or of a tolerance ("+/- 5%")
   is claimed by that; every other number must be followed by a unit
   ("489 m", "1,600 ft", "2.5 min"). A few spelled-out numbers are read too
   ("two minutes", "a minute and a half", "Two and a half inches").
2. Field. The unit's kind decides most fields: a distance in m/ft/km is the
   apogee, in mm/cm/in it is the body diameter; a time is the flight time; a
   mass is the liftoff mass. A speed is the wind when wind words ("wind",
   "breeze", "air") sit next to it and the landing speed when landing words
   ("touchdown", "land", "descent", "down" ...) do.
3. Kind. Words next to the number decide "about", "max" or "min" (see
   BEFORE_CUES and AFTER_CUES). A limit word after the number ("or less",
   "max", "tops") beats an "about" word before it ("near 6.5 kg max" is a
   maximum). A size or mass with no word of its own that follows another size
   or mass with only "and" between them shares its kind ("under 60 mm wide
   and 0.25 kg" means both are maxima). A number with no word is "about",
   except a landing speed, which is always a limit ("max").
4. Anything left over. A number the rules cannot place goes to `unassigned`,
   with the reason. A prompt is usable only when that list is empty.

Every item keeps the character span of its number in the text, the unit as
written and the factor to SI units, so a later step can rewrite the numbers
in place.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, Iterator, Optional, Sequence

from rocket_reward.records import Requirements, Target

# ---------------------------------------------------------------------------
# units

# unit as written (lower case) -> (dimension, factor to SI)
UNITS: dict[str, tuple[str, float]] = {
    "m/s": ("speed", 1.0), "mph": ("speed", 0.44704), "km/h": ("speed", 1 / 3.6),
    "kph": ("speed", 1 / 3.6), "knots": ("speed", 0.514444), "kt": ("speed", 0.514444),
    "m/s2": ("accel", 1.0), "m/s^2": ("accel", 1.0), "m/s²": ("accel", 1.0),
    "km": ("length", 1000.0), "mm": ("length", 0.001), "cm": ("length", 0.01),
    "m": ("length", 1.0), "ft": ("length", 0.3048), "feet": ("length", 0.3048),
    "foot": ("length", 0.3048), "in": ("length", 0.0254), "inch": ("length", 0.0254),
    "inches": ("length", 0.0254),
    "s": ("time", 1.0), "sec": ("time", 1.0), "secs": ("time", 1.0),
    "second": ("time", 1.0), "seconds": ("time", 1.0),
    "min": ("time", 60.0), "mins": ("time", 60.0), "minute": ("time", 60.0),
    "minutes": ("time", 60.0),
    "kg": ("mass", 1.0), "g": ("mass", 0.001), "gram": ("mass", 0.001),
    "grams": ("mass", 0.001), "lb": ("mass", 0.45359237), "lbs": ("mass", 0.45359237),
    "pound": ("mass", 0.45359237), "pounds": ("mass", 0.45359237),
    "oz": ("mass", 0.028349523125),
    "%": ("percent", 0.01),
}
# Longest first, so "m/s" wins over "m" and "minutes" over "min".
_UNIT_RE = re.compile(
    r"[ \t-]?(" + "|".join(re.escape(u) for u in sorted(UNITS, key=len, reverse=True))
    + r")(?![A-Za-z0-9/^²])", re.IGNORECASE)

# Units that name a diameter rather than an apogee.
DIAMETER_UNITS = {"mm", "cm", "in", "inch", "inches"}
APOGEE_UNITS = {"m", "km", "ft", "feet", "foot"}

_NUMBER_RE = re.compile(r"(?<![\w.])(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?![\w])|(?<![\w.])\d*\.\d+")

_WORD_VALUES = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "half a": 0.5}
_WORD_NUMBER_RE = re.compile(
    r"\b(?P<num>(?:one|two|three|four|five|six|seven|eight|nine|ten)(?:\s+and\s+a\s+half)?|half\s+a|an?)"
    r"\s+(?P<unit>minutes?|inch(?:es)?|seconds?)\b"
    r"(?P<half>\s+and\s+a\s+half\b)?", re.IGNORECASE)

# A motor designation: one run of letters, digits and - / ( ) holding at least
# one digit and one capital letter ("G74W", "HP-I500T", "I216-CL(I)", "21062-O3400-IM").
_MOTOR_TOKEN_RE = re.compile(r"(?<![\w-])[A-Za-z0-9][A-Za-z0-9()/\-]*[A-Za-z0-9)]|(?<![\w-])[A-Z0-9]")
_MOTOR_WORD_RE = re.compile(r"\bmotors?\b", re.IGNORECASE)
_TOL_RE = re.compile(r"(?:\+/-|±|\+-)\s*(?P<num>\d+(?:\.\d+)?)\s*%")
_MOTOR_CLASS_RE = re.compile(r"\b(?:an?\s+)?(?P<cls>[A-O])[- ]class\b|\ban?\s+(?P<cls2>[A-O])\s+motor\b")

# Characters that end a clause. A "." between two digits is a decimal point and
# never reaches this check, because numbers are masked out first.
_HARD_BREAKS = set(";:.!?()[],\n")
_SENTENCE_BREAKS = set(".!?;\n")

# ---------------------------------------------------------------------------
# wording rules

# Kind words that come before the number. The one nearest the number wins.
BEFORE_CUES: tuple[tuple[str, str], ...] = (
    (r"(?:no|nothing|not)\s+(?:wider|bigger|larger|heavier|faster|higher|greater|more|longer|taller)\s+than", "max"),
    (r"no\s+(?:less|lower|slower|smaller|lighter)\s+than", "min"),
    (r"(?:less|lower|slower|softer|narrower|thinner|lighter|smaller)\s+than", "max"),
    (r"at\s+(?:the\s+)?most", "max"),
    (r"at\s+least", "min"),
    (r"just\s+under", "max"),
    (r"under", "max"),
    (r"below", "max"),
    (r"up\s+to", "max"),
    (r"within", "max"),
    (r"tops\s+out\s+at", "max"),
    (r"as\s+(?:wide|big|large|heavy)\s+as", "max"),
    (r"(?:limit|cap)\s+of", "max"),
    (r"max(?:imum)?", "max"),
    (r"min(?:imum)", "min"),
    (r"more\s+than", "min"),
    (r"over", "min"),
    (r"above", "min"),
    (r"about", "about"),
    (r"around", "about"),
    (r"roughly", "about"),
    (r"approx(?:imately|\.)?", "about"),
    (r"close\s+to", "about"),
    (r"nearly", "about"),
    (r"near", "about"),
    (r"something\s+like", "about"),
    (r"~", "about"),
)
_BEFORE_RE = re.compile(r"(?<![\w])(?:" + "|".join(f"(?P<c{i}>{p})" for i, (p, _) in enumerate(BEFORE_CUES))
                        + r")(?![\w])", re.IGNORECASE)

# Kind words right after the number and unit (a few filler words may sit between).
AFTER_CUES: tuple[tuple[str, str], ...] = (
    (r"or\s+(?:less|under|below|lower|slower|thinner|narrower|lighter|smaller|shorter|fewer)", "max"),
    (r"or\s+(?:more|over|above|higher|faster|longer)", "min"),
    # "110 mm and under." only when the clause ends there: in "about 4.5 inches
    # across and under 1.5 kg" the "under" belongs to the next number.
    (r"and\s+(?:under|below|less)(?=\s*(?:[,.;!?)]|$))", "max"),
    (r"and\s+(?:over|above|more)(?=\s*(?:[,.;!?)]|$))", "min"),
    (r"(?:is\s+)?(?:my|the)\s+max(?:imum)?", "max"),
    (r"at\s+(?:the\s+)?most", "max"),
    (r"at\s+least", "min"),
    (r"max(?:imum)?", "max"),
    (r"minimum", "min"),
    (r"tops", "max"),
    (r"cap", "max"),
    (r"limit", "max"),
    (r"or\s+so", "about"),
)
_AFTER_FILLER = (r"(?:across|wide|in|diameter|body|tube|total|touchdown|landing|flight|all|up|"
                 r"on|of|airtime|mass|weight|width|speed|time|velocity)")
_AFTER_ALTS = "|".join(f"(?P<c{i}>{p})" for i, (p, _) in enumerate(AFTER_CUES))
# Inside the clause: a few filler words may sit between the unit and the cue.
# Both are matched on the whole text at the unit's end (no "^": `match` anchors
# there), so "$" means the real end of the prompt, not the start of the next number.
_AFTER_RE = re.compile(r"\s*(?:" + _AFTER_FILLER + r"\s+){0,2}(?:" + _AFTER_ALTS + r")(?![\w])",
                       re.IGNORECASE)
# Across a comma only a bare limit word counts ("5 m/s, tops"), never "..., touchdown at most".
_AFTER_COMMA_RE = re.compile(r"\s*,\s*(?:" + _AFTER_ALTS + r")(?=\s*[,.;!?]|\s*$)", re.IGNORECASE)

_NEGATION_RE = re.compile(r"\b(?:don't|dont|do\s+not|doesn't|not|never)\b", re.IGNORECASE)
# What may sit between two items of one list for the second to share the first's
# kind word ("under 60 mm wide and 0.25 kg", "under 85 seconds, 4.5 inches wide, and 1.8 kg").
_SHARE_KIND_RE = re.compile(r"^(?:\s|,|and|the|total|weight|mass|body|tube|diameter|width|wide|across|it)+$",
                            re.IGNORECASE)
_SHARE_FROM = {"flight_time_s", "time_to_apogee_s", "body_diameter_m", "mass_kg"}
# ...but a comma and then a field name right before the number starts a new,
# labelled entry of its own: in "Diameter no more than 110 mm, mass 3.7 kg" the
# mass is a plain number, like "mass 3.7 kg" in a spec list.
_NEW_ENTRY_RE = re.compile(r",\s*(?:and\s+)?(?:the\s+)?(?:total\s+)?(?:mass|weight|diameter|body|width|OD)\s*$",
                           re.IGNORECASE)

_WIND_WORDS = re.compile(r"\b(?:wind|winds|windy|breeze|crosswind|air|gusts?)\b", re.IGNORECASE)
_LANDING_WORDS = re.compile(
    r"\b(?:land|lands|landing|touch(?:es)?|touch-down|touchdown|touchdowns|descent|descend\w*|down|drop\w*|"
    r"drift\w*|ground|comes?\s+in|coming\s+in|softer|slower|faster|sets?\s+down|recovery\s+speed)\b",
    re.IGNORECASE)
_SPEED_WORDS = re.compile(r"\b(?:top\s+speed|max(?:imum)?\s+(?:speed|velocity)|peak\s+(?:speed|velocity))\b",
                          re.IGNORECASE)
_TO_APOGEE_WORDS = re.compile(r"\b(?:to\s+apogee|time\s+to\s+apogee|coast)\b", re.IGNORECASE)
_LENGTH_WORDS = re.compile(r"\b(?:long|length|tall|height\s+of\s+the\s+rocket)\b", re.IGNORECASE)
_DIAMETER_WORDS = re.compile(r"\b(?:diameter|OD|wide|width|across|tube|body|airframe|frame)\b", re.IGNORECASE)
_CALM_RE = re.compile(r"\b(?:calm(?:-day)?|no\s+wind)\b", re.IGNORECASE)

# Asks no record field can hold. The clause holding the word is kept as text.
OTHER_ASK_WORDS = re.compile(
    r"\b(?:length|long|tall|stages?|two-stage|single-stage|staged|parachutes?|chutes?|streamers?|"
    r"recovery|dual[- ]deploy\w*|fins?|payload|altimeter|camera|fiberglass|carbon|cardboard|plywood|"
    r"reusable|nose\s*cone|stability|caliber)\b", re.IGNORECASE)


# ---------------------------------------------------------------------------
# records


@dataclass(frozen=True)
class Item:
    """One requirement found in the text.

    `span` is where the number sits in the text (start, end), so
    text[span[0]:span[1]] == number_text. `stated` is that number as a value in
    the stated `unit`; `value` is the same in SI units (stated * factor).
    For motors, field is "motors", kind "named", value the designation and
    `span` the designation's place.
    """

    field: str
    kind: str
    value: Any
    tol: Optional[float]
    words: str
    span: tuple[int, int]
    number_text: str
    unit: Optional[str] = None
    unit_span: Optional[tuple[int, int]] = None
    stated: Optional[float] = None
    factor: Optional[float] = None
    cue: str = "bare"
    tol_span: Optional[tuple[int, int]] = None
    form: str = "digits"        # "digits", "words" (spelled out) or "none" (no number, e.g. "calm")

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        for k in ("span", "unit_span", "tol_span"):
            if d[k] is not None:
                d[k] = list(d[k])
        return d


@dataclass(frozen=True)
class Unassigned:
    """A number the parser could not place, and why."""

    text: str
    span: tuple[int, int]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.text, "span": list(self.span), "reason": self.reason}


@dataclass(frozen=True)
class OtherAsk:
    """An ask that fits no record field, kept as text. `numbers` holds the
    spans of numbers that belong to it."""

    text: str
    span: tuple[int, int]
    numbers: tuple[tuple[int, int], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.text, "span": list(self.span), "numbers": [list(n) for n in self.numbers]}


@dataclass
class ParsedPrompt:
    """Everything the parser found in one prompt."""

    text: str
    items: list[Item] = field(default_factory=list)
    other_asks: list[OtherAsk] = field(default_factory=list)
    unassigned: list[Unassigned] = field(default_factory=list)
    motor_class: Optional[str] = None

    @property
    def usable(self) -> bool:
        """True when every number was placed."""
        return not self.unassigned

    def by_field(self, name: str) -> list[Item]:
        return [i for i in self.items if i.field == name]


# ---------------------------------------------------------------------------
# tokens


@dataclass
class _Token:
    """A piece of text found in step 1."""

    kind: str                    # "qty", "motor", "tol", "bare"
    start: int                   # start of the whole token (number, or word number)
    end: int                     # end of the whole token (after the unit)
    num_span: tuple[int, int]
    stated: float = 0.0
    unit: Optional[str] = None
    unit_span: Optional[tuple[int, int]] = None
    form: str = "digits"


def _to_float(text: str) -> float:
    return float(text.replace(",", ""))


def _overlaps(a: tuple[int, int], spans: Sequence[tuple[int, int]]) -> bool:
    return any(a[0] < e and s < a[1] for s, e in spans)


def _motor_tokens(text: str) -> list[tuple[int, int]]:
    """Spans of runs that look like motor designations."""
    out = []
    for m in _MOTOR_TOKEN_RE.finditer(text):
        tok = m.group(0)
        if any(c.isdigit() for c in tok) and any(c.isupper() for c in tok):
            # "(I)" at the end of "I216-CL(I)" is kept; a lone ")" is not.
            end = m.end()
            if tok.count(")") > tok.count("("):
                end -= 1
            out.append((m.start(), end))
    return out


def _unit_after(text: str, pos: int) -> Optional[tuple[str, tuple[int, int]]]:
    """The unit written right after position `pos`, or None."""
    m = _UNIT_RE.match(text, pos)
    if not m:
        return None
    unit = m.group(1)
    if unit.lower() == "in":
        # "in" is inches only when it does not start a phrase ("done in a minute").
        rest = text[m.end():]
        if re.match(r"\s+(?:a|an|the|about|around|under|less|\d)\b", rest, re.IGNORECASE):
            return None
    return unit, (m.start(1), m.end(1))


def _tokens(text: str) -> list[_Token]:
    """Step 1: find every number and what it is attached to."""
    toks: list[_Token] = []
    taken: list[tuple[int, int]] = []
    for s, e in _motor_tokens(text):
        toks.append(_Token("motor", s, e, (s, e)))
        taken.append((s, e))
    for m in _TOL_RE.finditer(text):
        span = (m.start("num"), m.end("num"))
        if _overlaps(span, taken):
            continue
        toks.append(_Token("tol", m.start(), m.end(), span, stated=float(m.group("num")), unit="%"))
        taken.append((m.start(), m.end()))
    for m in _WORD_NUMBER_RE.finditer(text):
        if _overlaps((m.start(), m.end()), taken):
            continue
        num = m.group("num").lower()
        value = float(_WORD_VALUES.get(num.split()[0] if num != "half a" else num, 0))
        if "and a half" in num:
            value += 0.5
        unit = m.group("unit")
        if m.group("half"):
            if num not in ("a", "an", "one"):
                continue
            value = 1.5
            span = (m.start(), m.end())          # "a minute and a half": number and unit interleave
            toks.append(_Token("qty", m.start(), m.end(), span, value, unit, span, "words"))
        else:
            if num in ("a", "an") and unit.lower() not in ("minute", "inch", "second"):
                continue
            toks.append(_Token("qty", m.start(), m.end(), (m.start("num"), m.end("num")), value, unit,
                               (m.start("unit"), m.end("unit")), "words"))
        taken.append((m.start(), m.end()))
    for m in _NUMBER_RE.finditer(text):
        span = (m.start(), m.end())
        if _overlaps(span, taken):
            continue
        u = _unit_after(text, m.end())
        if u is None:
            toks.append(_Token("bare", m.start(), m.end(), span, _to_float(m.group(0))))
        else:
            unit, uspan = u
            toks.append(_Token("qty", m.start(), uspan[1], span, _to_float(m.group(0)), unit, uspan))
    toks.sort(key=lambda t: t.start)
    return toks


# ---------------------------------------------------------------------------
# step 2 and 3


def _mask(text: str, toks: Sequence[_Token]) -> str:
    """The text with every token replaced by '#', so its dots and commas are not
    taken for clause breaks."""
    chars = list(text)
    for t in toks:
        for i in range(t.start, t.end):
            chars[i] = "#"
    return "".join(chars)


def _left_bound(masked: str, pos: int, floor: int, breaks: set[str] = _HARD_BREAKS) -> int:
    i = pos
    while i > floor and masked[i - 1] not in breaks:
        i -= 1
    return i


def _right_bound(masked: str, pos: int, ceil: int, breaks: set[str] = _HARD_BREAKS) -> int:
    i = pos
    while i < ceil and masked[i] not in breaks:
        i += 1
    return i


def _nearest_cue(before: str, field_name: str) -> Optional[tuple[str, str]]:
    """The kind word nearest the end of `before`, as (kind, words)."""
    best = None
    for m in _BEFORE_RE.finditer(before):
        i = next(int(k[1:]) for k, v in m.groupdict().items() if v is not None)
        kind = BEFORE_CUES[i][1]
        words = m.group(0)
        if field_name == "apogee_m" and re.fullmatch(r"up\s+to", words, re.IGNORECASE):
            continue                     # "gets up to 5,000 ft" is a target, not a ceiling
        if kind == "min" and _NEGATION_RE.search(before[:m.start()]):
            kind = "max"                 # "I don't want the body over 65 mm"
        if best is None or m.end() >= best[2]:
            best = (kind, words, m.end())
    return (best[0], best[1]) if best else None


def _after_cue(text: str, pos: int, limit: int) -> Optional[tuple[str, str, int]]:
    """The kind word right after the unit (which ends at `pos`), as (kind,
    words, end counted from `pos`). The cue must end before `limit`, the start
    of the next number."""
    m = _AFTER_RE.match(text, pos) or _AFTER_COMMA_RE.match(text, pos)
    if not m or m.end() > limit:
        return None
    i = next(int(k[1:]) for k, v in m.groupdict().items() if v is not None)
    return AFTER_CUES[i][1], m.group(f"c{i}"), m.end() - pos


def _speed_field(before: str, after: str, sentence: str) -> Optional[str]:
    """Wind or landing speed, from the words next to the number."""
    if _SPEED_WORDS.search(before + " " + after):
        return "max_velocity_ms"
    near = []
    for m in _WIND_WORDS.finditer(before):
        near.append((len(before) - m.end(), "wind_ms"))
    for m in _LANDING_WORDS.finditer(before):
        near.append((len(before) - m.end(), "landing_ms"))
    for m in _WIND_WORDS.finditer(after):
        near.append((m.start(), "wind_ms"))
    for m in _LANDING_WORDS.finditer(after):
        near.append((m.start(), "landing_ms"))
    if near:
        return min(near)[1]
    wind, land = bool(_WIND_WORDS.search(sentence)), bool(_LANDING_WORDS.search(sentence))
    if wind != land:
        return "wind_ms" if wind else "landing_ms"
    return None


def _field_of(tok: _Token, before: str, after: str, sentence: str) -> tuple[Optional[str], str]:
    """Step 2: the record field a quantity belongs to, or (None, reason)."""
    dim = UNITS[tok.unit.lower()][0]
    unit = tok.unit.lower()
    near = before + " " + after
    if dim == "length":
        if _LENGTH_WORDS.search(near):
            return "other:length", ""
        if unit in DIAMETER_UNITS:
            return "body_diameter_m", ""
        if unit == "m" and _DIAMETER_WORDS.search(near) and not re.search(r"apogee|altitude|high|up\b",
                                                                          near, re.IGNORECASE):
            return "body_diameter_m", ""
        return "apogee_m", ""
    if dim == "time":
        return ("time_to_apogee_s" if _TO_APOGEE_WORDS.search(near) else "flight_time_s"), ""
    if dim == "mass":
        if re.search(r"\baccel", near, re.IGNORECASE) and unit == "g":
            return None, "a 'g' next to acceleration words is ambiguous"
        return "mass_kg", ""
    if dim == "speed":
        f = _speed_field(before, after, sentence)
        return (f, "") if f else (None, "a speed with no wind or landing words near it")
    if dim == "accel":
        return "max_accel_ms2", ""
    return None, f"a {dim} is not a requirement on its own"


def _pattern(words: str, spans: Sequence[tuple[int, int]], offset: int) -> str:
    """`words` in lower case with every number replaced by N, for counting wordings."""
    out = words.lower()
    for s, e in sorted(spans, reverse=True):
        s, e = s - offset, e - offset
        if 0 <= s < e <= len(words):
            out = out[:s] + "N" + out[e:]
    return re.sub(r"\s+", " ", out).strip(" ,;.")


def parse_prompt(text: str) -> ParsedPrompt:
    """Find every requirement stated in `text`. Never drops a number: what
    cannot be placed is listed in `unassigned`."""
    parsed = ParsedPrompt(text=text)
    toks = _tokens(text)
    masked = _mask(text, toks)
    n = len(text)
    prev_qty: Optional[tuple[_Token, Item, int]] = None   # last quantity, its item, end of its words
    last_end = 0
    pending: list[tuple[_Token, Item]] = []

    for idx, tok in enumerate(toks):
        next_start = toks[idx + 1].start if idx + 1 < len(toks) else n
        s_left = _left_bound(masked, tok.start, 0, _SENTENCE_BREAKS)
        s_right = _right_bound(masked, tok.end, n, _SENTENCE_BREAKS)
        sentence = text[s_left:s_right]

        if tok.kind == "motor":
            name = text[tok.start:tok.end]
            if _MOTOR_WORD_RE.search(sentence):
                parsed.items.append(Item("motors", "named", name, None, sentence.strip(),
                                         (tok.start, tok.end), name, cue="motor", form="designation"))
            elif any(c.isdigit() for c in name):
                parsed.unassigned.append(Unassigned(name, (tok.start, tok.end),
                                                    "looks like a motor designation but no 'motor' word is near it"))
            last_end = tok.end
            continue

        if tok.kind == "tol":
            target = pending[-1] if pending else None
            gap = masked[target[0].end:tok.start] if target else ""
            if target and target[1].kind == "about" and not any(c in ";." for c in gap):
                t0, it = target
                start = text.rfind(it.words, 0, tok.start) if it.words else -1
                start = start if start >= 0 else t0.start
                new = replace(it, tol=tok.stated / 100.0, tol_span=tok.num_span,
                              cue=f"{it.cue} +/- N%" if it.cue != "bare" else "N +/- N%",
                              words=text[start:tok.end + (text[tok.end:tok.end + 1] == ")")].strip(" ,"))
                parsed.items[parsed.items.index(it)] = new
                pending[-1] = (t0, new)
                if prev_qty and prev_qty[1] is it:
                    prev_qty = (t0, new, prev_qty[2])
            else:
                parsed.unassigned.append(Unassigned(text[tok.start:tok.end], tok.num_span,
                                                    "a tolerance with no target before it"))
            last_end = tok.end
            continue

        if tok.kind == "bare":
            parsed.unassigned.append(Unassigned(text[tok.start:tok.end], tok.num_span, "a number with no unit"))
            last_end = tok.end
            continue

        if tok.unit == "%":
            parsed.unassigned.append(Unassigned(text[tok.start:tok.end], tok.num_span,
                                                "a percentage that is not a +/- tolerance"))
            last_end = tok.end
            continue

        left = _left_bound(masked, tok.start, last_end)
        right = _right_bound(masked, tok.end, next_start)
        before = text[left:tok.start]
        after = text[tok.end:right]
        fname, why = _field_of(tok, before, after, sentence)
        last_end = tok.end
        if fname is None:
            parsed.unassigned.append(Unassigned(text[tok.num_span[0]:tok.end], tok.num_span, why))
            prev_qty = None
            continue
        if fname.startswith("other:"):
            clause = text[left:right].strip()
            parsed.other_asks.append(OtherAsk(clause, (left, right), (tok.num_span,)))
            prev_qty = None
            continue

        # step 3: kind
        cue_words = "bare"
        kind: Optional[str] = None
        ac = _after_cue(text, tok.end, next_start)
        words_end = right
        prev_end = prev_qty[2] if prev_qty else 0
        if ac and ac[0] in ("max", "min"):
            kind, cue_words = ac[0], f"N {ac[1].lower()}"
            words_end = max(right, tok.end + ac[2])
        else:
            bc = _nearest_cue(before, fname)
            if bc:
                kind, cue_words = bc[0], f"{bc[1].lower()} N"
            elif ac:
                kind, cue_words = ac[0], f"N {ac[1].lower()}"
                words_end = max(right, tok.end + ac[2])
            elif (prev_qty and fname in _SHARE_FROM and prev_qty[1].field in _SHARE_FROM
                  and prev_qty[1].cue != "bare"
                  and _SHARE_KIND_RE.match(text[prev_end:tok.start] or "-")
                  and not _NEW_ENTRY_RE.search(text[prev_end:tok.start])):
                kind, cue_words = prev_qty[1].kind, f"(shares '{prev_qty[1].cue}') N"
            elif fname == "landing_ms":
                kind, cue_words = "max", "bare N (landing is a limit)"
            else:
                kind = "about"
        unit_l = tok.unit.lower()
        factor = UNITS[unit_l][1]
        value = round(tok.stated * factor, 9)
        words = text[left:words_end].strip(" ,")
        item = Item(fname, kind, value, None, words, tok.num_span, text[tok.num_span[0]:tok.num_span[1]],
                    tok.unit, tok.unit_span, tok.stated, factor, cue_words, None, tok.form)
        parsed.items.append(item)
        pending.append((tok, item))
        cue_end = tok.end + ac[2] if ac and kind == ac[0] and cue_words.startswith("N ") else tok.end
        prev_qty = (tok, item, cue_end)

    # No wind number but "calm" or "no wind": the wind is zero.
    if not parsed.by_field("wind_ms"):
        m = _CALM_RE.search(text)
        if m:
            parsed.items.append(Item("wind_ms", "about", 0.0, None, m.group(0), (m.start(), m.end()), "",
                                     "m/s", None, 0.0, 1.0, "calm", None, "none"))

    m = _MOTOR_CLASS_RE.search(text)
    if m:
        parsed.motor_class = (m.group("cls") or m.group("cls2")).upper()

    # Qualitative asks no record field holds ("dual deploy", "under 1 m long" ...).
    for m in OTHER_ASK_WORDS.finditer(text):
        if any(a.span[0] <= m.start() < a.span[1] for a in parsed.other_asks):
            continue
        if _overlaps((m.start(), m.end()), [i.span for i in parsed.items if i.field == "motors"]):
            continue
        s = _left_bound(masked, m.start(), 0)
        e = _right_bound(masked, m.end(), n)
        if any(s <= i.span[0] < e for i in parsed.items):
            continue                     # "flight length about 2.6 minutes" is the flight time
        nums = tuple(t.num_span for t in toks if s <= t.start < e and t.kind != "motor"
                     and not _overlaps(t.num_span, [i.span for i in parsed.items]))
        parsed.other_asks.append(OtherAsk(text[s:e].strip(), (s, e), nums))
    parsed.items.sort(key=lambda i: i.span[0])
    return parsed


def item_pattern(item: Item, text: str) -> str:
    """The wording of one item with its number replaced by N."""
    start = -1
    for m in re.finditer(re.escape(item.words), text) if item.words else ():
        if m.start() <= item.span[0] < m.end():
            start = m.start()
            break
    if start < 0:
        return item.words.lower()
    spans = [item.span] + ([item.tol_span] if item.tol_span else [])
    return _pattern(item.words, spans, start)


# ---------------------------------------------------------------------------
# record


def to_requirements(row_id: str, parsed: ParsedPrompt) -> dict[str, Any]:
    """The Requirements record (as Requirements.to_dict() gives it) for one
    parsed prompt. Raises ValueError when the prompt cannot make a valid
    record: no apogee, a field stated twice with different values, or a
    number that was not placed."""
    if parsed.unassigned:
        raise ValueError(f"{row_id}: {len(parsed.unassigned)} number(s) not placed: "
                         + "; ".join(f"{u.text!r} ({u.reason})" for u in parsed.unassigned))
    kwargs: dict[str, Any] = {"id": row_id}
    for name in ("apogee_m", "landing_ms", "flight_time_s", "time_to_apogee_s", "max_velocity_ms",
                 "max_accel_ms2", "body_diameter_m", "mass_kg"):
        found = parsed.by_field(name)
        if not found:
            continue
        distinct = {(i.value, i.kind, i.tol) for i in found}
        if len(distinct) > 1:
            raise ValueError(f"{row_id}: {name} is stated more than once with different values")
        it = found[0]
        kwargs[name] = Target(value=it.value, kind=it.kind, tol=it.tol)
    winds = {i.value for i in parsed.by_field("wind_ms")}
    if len(winds) > 1:
        raise ValueError(f"{row_id}: the wind is stated more than once with different values")
    if winds:
        kwargs["wind_ms"] = winds.pop()
    motors: list[str] = []
    for i in parsed.by_field("motors"):
        if i.value not in motors:
            motors.append(i.value)
    kwargs["motors"] = tuple(motors)
    if parsed.motor_class:
        kwargs["motor_class"] = parsed.motor_class
    if "apogee_m" not in kwargs:
        raise ValueError(f"{row_id}: the prompt states no apogee")
    req = Requirements(**kwargs)
    out = req.to_dict()
    Requirements.from_dict(out)          # must load back
    return out


# ---------------------------------------------------------------------------
# checks against the reference rocket

LANDING_JUST_ABOVE_MS = 1.0      # a landing limit more than this above the reference flight is "loose"
WIND_MATCH_MS = 0.15             # stated wind and the reference wind may differ by this (mph rounding)
UNSAFE_LANDING_MS = 8.0          # landing limits above this are listed as unsafe
# Added to a problem when an "about" number sits above the reference value, so it
# reads like a limit with headroom ("about 100 s" for a 94 s flight).
HEADROOM_MARK = "; the stated number is above the reference, like a limit with headroom"


@dataclass
class Reference:
    """What the reference rocket did and is made of."""

    targets: dict[str, Any]
    motors: list[str]
    widest_body_m: Optional[float]
    liftoff_mass_kg: Optional[float]


def _radius(value: Any) -> Optional[float]:
    """A radius written as a number. "auto" radii (OpenRocket copies them from
    the next part, and the number after "auto" is only a stale default) give None.
    The number is read as OpenRocket reads it (tree.number)."""
    from rocket_reward import tree as T

    if isinstance(value, str) and "auto" in value.lower():
        return None
    return T.number(value)


def widest_body_tube(root: Any) -> Optional[float]:
    """Outer diameter (m) of the widest body tube. An "auto" body tube takes
    the radius of the part in front of it (or, failing that, behind it), as
    OpenRocket does."""
    from rocket_reward import tree as T

    rocket = T.rocket_of(root)
    if rocket is None:
        return None
    # The outside of the rocket, front to back: (tag, fore radius, aft radius).
    parts: list[list[Any]] = []
    for comp, _ in T.walk_components(rocket):
        tag = T.tag_of(comp)
        if tag == "nosecone":
            parts.append([tag, None, _radius(T.child_value(comp, "aftradius"))])
        elif tag == "bodytube":
            r = _radius(T.child_value(comp, "radius"))
            parts.append([tag, r, r])
        elif tag == "transition":
            parts.append([tag, _radius(T.child_value(comp, "foreradius")),
                          _radius(T.child_value(comp, "aftradius"))])
    for _ in range(len(parts) + 1):          # pass the radii along until nothing changes
        changed = False
        for i, p in enumerate(parts):
            if p[1] is None and p[0] != "nosecone" and i > 0 and parts[i - 1][2] is not None:
                p[1] = parts[i - 1][2]
                changed = True
            if p[2] is None and i + 1 < len(parts) and parts[i + 1][1] is not None:
                p[2] = parts[i + 1][1]
                changed = True
            if p[0] == "bodytube" and (p[1] is None) != (p[2] is None):
                p[1] = p[2] = p[1] if p[1] is not None else p[2]
                changed = True
        if not changed:
            break
    radii = [p[1] for p in parts if p[0] == "bodytube" and p[1] is not None and p[1] > 0]
    return 2 * max(radii) if radii else None


_MASS_RE = re.compile(r"[Ll]iftoff (?:mass is|weight is [\d.]+ N at) ([\d.]+) kg")


def reference_of(row: dict[str, Any]) -> Reference:
    """Read the reference flight numbers, motors, widest body tube and liftoff
    mass of one meta row. Missing pieces are None or empty."""
    from rocket_reward import motors as M
    from rocket_reward import tree as T
    from rocket_reward.parse import find_design_block

    answer = ""
    for msg in row.get("messages") or []:
        if isinstance(msg, dict) and msg.get("role") == "assistant":
            answer = msg.get("content") or ""
    motors: list[str] = []
    widest: Optional[float] = None
    block, _ = find_design_block(answer)
    if block:
        try:
            root = json.loads(block)
        except ValueError:
            root = None
        if root is not None:
            for m in M.flown_motors(root):
                d = T.child_value(m, "designation")
                if isinstance(d, str) and d not in motors:
                    motors.append(d)
            widest = widest_body_tube(root)
    thought = answer.split("</thought>")[0]
    m = _MASS_RE.search(thought)
    mass = float(m.group(1)) if m else None
    return Reference(dict(row.get("targets") or {}), motors, widest, mass)


def _judge(label: str, item: Item, actual: float, unit: str) -> Optional[str]:
    """Compare one stated target with the reference value the way the reward
    grades it ("about": within tol, 5% when none is stated; "max": at or
    below; "min": at or above). Returns the problem, or None when the
    reference meets its own requirement."""
    v = item.value
    # "a minute and a half": the number and the unit share one span, so the unit is not repeated.
    unit_text = "" if item.unit_span is not None and item.unit_span == item.span else f" {item.unit}"
    said = f"{label} {item.kind} {item.number_text or item.words}{unit_text} (= {v:g} {unit})"
    ref = f"the reference is {actual:.4g} {unit}"
    if item.kind == "about":
        tol = item.tol if item.tol is not None else 0.05
        diff = abs(actual - v)
        if diff <= tol * v:
            return None
        headroom = HEADROOM_MARK if actual < v else ""
        return f"{said}: {ref}, {diff / v:.1%} off (allowed {tol:.0%}){headroom}"
    if item.kind == "max":
        return None if actual <= v else f"{said}: {ref}, above the limit"
    return None if actual >= v else f"{said}: {ref}, below the limit"


def cross_check(parsed: ParsedPrompt, ref: Reference) -> tuple[list[str], list[str]]:
    """Problems (contradictions with the reference rocket) and notes for one row."""
    problems: list[str] = []
    notes: list[str] = []
    t = ref.targets

    def add(problem: Optional[str]) -> None:
        if problem:
            problems.append(problem)

    pairs = (("apogee_m", "apogee", "apogee_m", "m"), ("landing_ms", "landing", "ground_hit_ms", "m/s"),
             ("flight_time_s", "flight time", "flight_time_s", "s"),
             ("time_to_apogee_s", "time to apogee", "time_to_apogee_s", "s"),
             ("max_velocity_ms", "top speed", "max_velocity_ms", "m/s"))
    for fname, label, tkey, unit in pairs:
        for it in parsed.by_field(fname):
            if not isinstance(t.get(tkey), (int, float)):
                notes.append(f"{label} is stated but the reference has no {tkey} to check it against")
                continue
            add(_judge(label, it, float(t[tkey]), unit))
            if fname == "landing_ms" and it.kind == "max" and it.value > float(t[tkey]) + LANDING_JUST_ABOVE_MS:
                notes.append(f"landing limit {it.value:g} m/s is loose: the reference lands at "
                             f"{float(t[tkey]):.3g} m/s")
    for it in parsed.by_field("max_accel_ms2"):
        notes.append("top acceleration is stated but the reference has no number to check it against")
    for it in parsed.by_field("body_diameter_m"):
        if ref.widest_body_m is None:
            notes.append("diameter is stated but the reference design has no readable body tube radius")
        else:
            add(_judge("body diameter", it, ref.widest_body_m, "m"))
    for it in parsed.by_field("mass_kg"):
        if ref.liftoff_mass_kg is None:
            notes.append("mass is stated but the reference answer gives no liftoff mass")
        else:
            add(_judge("mass", it, ref.liftoff_mass_kg, "kg"))
    winds = parsed.by_field("wind_ms")
    ref_wind = t.get("wind_ms")
    for it in winds:
        if not isinstance(ref_wind, (int, float)):
            notes.append("wind is stated but the reference has no wind_ms to check it against")
        elif abs(it.value - float(ref_wind)) > max(WIND_MATCH_MS, 0.05 * float(ref_wind)):
            problems.append(f"wind {it.number_text or it.words} {it.unit} (= {it.value:g} m/s): "
                            f"the reference flew in {float(ref_wind):.3g} m/s")
    if not winds and isinstance(ref_wind, (int, float)) and abs(float(ref_wind) - 2.0) > WIND_MATCH_MS:
        notes.append(f"wind not stated, so the reward uses 2 m/s; the reference flew in {float(ref_wind):.3g} m/s")
    flown = {m.upper() for m in ref.motors}
    for it in parsed.by_field("motors"):
        if it.value.upper() not in flown:
            problems.append(f"motor {it.value} is not one the reference design flies ({', '.join(ref.motors) or 'none'})")
    for ask in parsed.other_asks:
        if ask.numbers:
            problems.append(f"asks for something the record cannot hold: {ask.text!r}")
    return problems, notes


# ---------------------------------------------------------------------------
# command line


def _row_key(row: dict[str, Any], taken: set[str]) -> str:
    key = f"{row.get('id')}:{row.get('prompt_style')}"
    base, n = key, 2
    while key in taken:
        key = f"{base}#{n}"
        n += 1
    taken.add(key)
    return key


def process_rows(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parse and check every meta row; return the output rows."""
    out = []
    taken: set[str] = set()
    for row in rows:
        rid = _row_key(row, taken)
        text = row.get("prompt_text") or ""
        parsed = parse_prompt(text)
        problems: list[str] = []
        notes: list[str] = []
        req = None
        try:
            req = to_requirements(rid, parsed)
        except ValueError as exc:
            problems.append(str(exc).split(": ", 1)[-1])
        p2, notes = cross_check(parsed, reference_of(row))
        problems.extend(p2)
        items = []
        for it in parsed.items:
            d = it.to_dict()
            d["pattern"] = item_pattern(it, text)
            items.append(d)
        out.append({
            "id": rid, "group_id": row.get("group_id"), "prompt_style": row.get("prompt_style"),
            "split": row.get("split"), "prompt_text": text, "requirements": req,
            "items": items, "other_asks": [a.to_dict() for a in parsed.other_asks],
            "unassigned": [u.to_dict() for u in parsed.unassigned],
            "usable": req is not None and not problems and not parsed.unassigned,
            "problems": problems, "notes": notes,
        })
    return out


def _count_table(header: Sequence[str], rows: Sequence[Sequence[Any]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(str(c).replace("|", "\\|") for c in r) + " |" for r in rows]
    return lines


def build_report(out_rows: Sequence[dict[str, Any]], meta_name: str) -> str:
    """The Markdown report for a parse run."""
    styles = sorted({r["prompt_style"] for r in out_rows})
    splits = sorted({r["split"] for r in out_rows})
    lines = ["# Requirement records built from prompts", "",
             f"Source: `{meta_name}`, {len(out_rows)} rows. "
             f"Usable: {sum(r['usable'] for r in out_rows)}.", "",
             "A row is usable when every number in its prompt was placed, the prompt states an apogee, "
             "and nothing it states contradicts its own reference rocket.", "",
             "## Usable rows by style and split", ""]
    tab = []
    for st in styles:
        cells = [st]
        for sp in splits:
            rs = [r for r in out_rows if r["prompt_style"] == st and r["split"] == sp]
            cells.append(f"{sum(r['usable'] for r in rs)} / {len(rs)}")
        rs = [r for r in out_rows if r["prompt_style"] == st]
        cells.append(f"{sum(r['usable'] for r in rs)} / {len(rs)}")
        tab.append(cells)
    cells = ["all"] + [f"{sum(r['usable'] for r in out_rows if r['split'] == sp)} / "
                       f"{sum(1 for r in out_rows if r['split'] == sp)}" for sp in splits]
    cells.append(f"{sum(r['usable'] for r in out_rows)} / {len(out_rows)}")
    tab.append(cells)
    lines += _count_table(["style"] + splits + ["all"], tab)

    lines += ["", "## How often each field is stated", "",
              "Counted once per row. Kinds in brackets.", ""]
    fc: dict[str, dict[str, collections.Counter]] = collections.defaultdict(
        lambda: collections.defaultdict(collections.Counter))
    for r in out_rows:
        seen = set()
        for it in r["items"]:
            if (it["field"], it["kind"]) in seen:
                continue
            seen.add((it["field"], it["kind"]))
            fc[it["field"]][r["prompt_style"]][it["kind"]] += 1
    tab = []
    for f in sorted(fc):
        row = [f]
        total: collections.Counter = collections.Counter()
        for st in styles:
            c = fc[f][st]
            total += c
            row.append(f"{sum(c.values())} ({', '.join(f'{k} {v}' for k, v in sorted(c.items()))})"
                       if c else "0")
        row.append(f"{sum(total.values())} ({', '.join(f'{k} {v}' for k, v in sorted(total.items()))})")
        tab.append(row)
    lines += _count_table(["field"] + styles + ["all"], tab)

    lines += ["", "## Kind words", "", "Which words set the kind (N is the number).", ""]
    cue = collections.Counter((it["field"], it["kind"], it["cue"]) for r in out_rows for it in r["items"])
    lines += _count_table(["field", "kind", "words", "count"],
                          [[f, k, f"`{c}`", n] for (f, k, c), n in sorted(cue.items())])

    lines += ["", "## Every wording pattern", "",
              "The words of each item with the number replaced by N, lower case.", ""]
    pat = collections.Counter((it["field"], it["pattern"]) for r in out_rows for it in r["items"]
                              if it["field"] != "motors")
    lines += _count_table(["field", "pattern", "count"],
                          [[f, f"`{p}`", n] for (f, p), n in sorted(pat.items(), key=lambda x: (x[0][0], -x[1], x[0][1]))])
    mot = collections.Counter(re.sub(r"\S*\d\S*", "MOTOR", it["words"].lower()) for r in out_rows
                              for it in r["items"] if it["field"] == "motors")
    lines += ["", "Motor sentences (designations replaced by MOTOR):", ""]
    lines += _count_table(["sentence", "count"], [[f"`{p}`", n] for p, n in mot.most_common()])

    asks = [(r["id"], a["text"]) for r in out_rows for a in r["other_asks"]]
    lines += ["", "## Other asks (no record field)", ""]
    lines += [f"- {i}: {t}" for i, t in asks] or ["None."]

    lines += ["", "## Unusable rows", ""]
    bad = [r for r in out_rows if not r["usable"]]
    head = [r for r in bad if r["problems"] and not r["unassigned"]
            and all(p.endswith(HEADROOM_MARK) for p in r["problems"])]
    reasons = collections.Counter()
    for r in bad:
        for u in r["unassigned"]:
            reasons["number not placed"] += 1
        for p in r["problems"]:
            reasons[p.split(" ")[0] + (" (about-number above the reference)" if p.endswith(HEADROOM_MARK)
                                       else "")] += 1
    lines += [f"{len(bad)} rows. Reasons (a row can have several):", ""]
    lines += _count_table(["reason starts with", "count"], [[k, v] for k, v in reasons.most_common()])
    lines += ["", f"{len(head)} of these rows fail only because an \"about\" number (flight time, mass or "
              "diameter) sits above the reference value by more than 5%. Those numbers read like limits "
              "with headroom; reading them as \"max\" would make these rows usable, but that changes what "
              "the prompt says, so it is left to the owner.", ""]
    if not bad:
        lines.append("None.")
    for r in bad:
        lines.append(f"- **{r['id']}** ({r['split']}): {r['prompt_text']}")
        for u in r["unassigned"]:
            lines.append(f"  - number not placed: `{u['text']}` ({u['reason']})")
        for p in r["problems"]:
            lines.append(f"  - {p}")

    lines += ["", f"## Landing limits above {UNSAFE_LANDING_MS:g} m/s (unsafe)", ""]
    unsafe = [(r["id"], it) for r in out_rows for it in r["items"]
              if it["field"] == "landing_ms" and it["value"] > UNSAFE_LANDING_MS]
    lines += [f"- {i}: `{it['words']}` = {it['value']:g} m/s ({it['kind']})" for i, it in unsafe] or ["None."]

    lines += ["", "## Notes (do not make a row unusable)", ""]
    nc = collections.Counter(re.sub(r"[-\d.]+", "N", n) for r in out_rows for n in r["notes"])
    lines += _count_table(["note", "rows"], [[f"`{k}`", v] for k, v in nc.most_common()])
    lines += ["", "Each row's own notes are in the JSONL output."]
    return "\n".join(lines) + "\n"


def _read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


def cmd_parse(meta: Path, out: Path, report: Path) -> int:
    rows = list(_read_jsonl(meta))
    result = process_rows(rows)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="\n") as fh:
        for r in result:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(build_report(result, meta.name), encoding="utf-8", newline="\n")
    usable = sum(r["usable"] for r in result)
    print(f"{len(result)} rows, {usable} usable; wrote {out} and {report}")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m rocket_reward.tools.build_requirements",
                                 description="Build requirement records from prompt text.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("parse", help="parse every prompt of a meta file")
    p.add_argument("--meta", required=True, type=Path, help="reference rows with prompt_text and targets (.jsonl)")
    p.add_argument("--out", required=True, type=Path, help="parsed prompts to write (.jsonl)")
    p.add_argument("--report", required=True, type=Path, help="Markdown report to write")
    args = ap.parse_args(argv)
    if args.cmd == "parse":
        return cmd_parse(args.meta, args.out, args.report)
    return 2


if __name__ == "__main__":
    sys.exit(main())
