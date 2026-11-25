"""Trace linter for SFT rows (DATA_SPEC.md sections 5.3, 5.4, 6, 7.4 and the row checklist in 9).

Pure Python over row JSON; never starts a JVM. Public API:

    Issue                      one finding (code, severity, message, msg_index)
    lint_row(row, stats=None)  row-level checks; optional dict receives math/fix counters
    lint_file(rows, report=None) row-level + file-level checks; optional dict receives the file report
    gate_failures(sim_output, targets) safety gates and numeric targets a simulate output fails

Number matching (used by leakage, precision, provenance and the fix-quote check):
  * a number shown in text "matches" a value when the value rounds to it. "Decimal" mode rounds to the
    shown decimals (245 ~ 245.3, 245.3 !~ 245.31); "sig" mode rounds to the last significant digit
    (250 ~ 245.3, since integer trailing zeros are not significant).
  * values are also matched after a x1000 or /1000 scale (m <-> mm, kg <-> g).
"""

from __future__ import annotations

import bisect
import json
import math
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from . import contract
from .schema import parse_design

__all__ = ["Issue", "lint_row", "lint_file", "gate_failures"]

Severity = Literal["must", "should"]


@dataclass
class Issue:
    code: str
    severity: Severity
    message: str
    msg_index: Optional[int] = None


# --------------------------------------------------------------------------------------------------
# Numbers in text
# --------------------------------------------------------------------------------------------------

_NUM_RE = re.compile(
    r"(?<![A-Za-z0-9_.])(?:(?:\d{1,3}(?:,\d{3})+(?!\d)|\d+)(?:\.\d+)?|\.\d+)(?:[eE][-+]?\d+(?![\d.]))?"
)


@dataclass(frozen=True)
class Num:
    text: str
    value: float  # absolute value
    sig: int
    dec_unit: float  # 10**-decimals (1 for integers)
    sig_unit: float  # place value of the last significant digit
    start: int


def _parse_num(text: str, start: int = 0) -> Num:
    t = text.replace(",", "")
    mant, _, exp = t.lower().partition("e")
    scale = 10.0 ** int(exp) if exp else 1.0
    if "." in mant:
        ip, fp = mant.split(".", 1)
        digits = (ip + fp).lstrip("0")
        sig = max(len(digits), 1)
        dec_unit = 10.0 ** (-len(fp))
        sig_unit = dec_unit
    else:
        stripped = mant.lstrip("0")
        core = stripped.rstrip("0")
        sig = max(len(core), 1)
        dec_unit = 1.0
        sig_unit = 10.0 ** (len(stripped) - len(core)) if core else 1.0
    return Num(text, abs(float(mant or 0)) * scale, sig, dec_unit * scale, sig_unit * scale, start)


def _numbers(text: str) -> list[Num]:
    return [_parse_num(m.group(), m.start()) for m in _NUM_RE.finditer(text)]


def _dec_tol(n: Num) -> float:
    return 0.5 * n.dec_unit * (1 + 1e-9) + 1e-12 * max(1.0, n.value)


def _sig_tol(n: Num) -> float:
    return 0.5 * n.sig_unit * (1 + 1e-9) + 1e-12 * max(1.0, n.value)


_COMMON_VALUES = sorted({
    9.81, 9.8, 9.807, 9.80665, 1.225, 3.14, 3.142, 3.1416, 3.14159, 0.3048, 3.281, 3.28, 3.2808,
    0.0254, 25.4, 2.205, 2.2046, 0.4536, 0.45359, 453.6, 28.35, 343.0, 340.0, 0.447, 0.44704,
    1.609, 1.6093, 0.5, 1.0, 2.0, 3.0, 4.0, 100.0, 1000.0, 101325.0, 1.4,
    float(contract.OPENROCKET_VERSION),
    *(float(v) for v in contract.GATES.values()),
    *(float(v) for v in contract.TOLERANCES.values()),
})


def _is_common(n: Num) -> bool:
    i = bisect.bisect_left(_COMMON_VALUES, n.value - 1e-9)
    return i < len(_COMMON_VALUES) and abs(_COMMON_VALUES[i] - n.value) <= 1e-9 * max(1.0, n.value)


def _flatten(obj: Any, out: list[float]) -> list[float]:
    """Every number in a JSON value (numbers inside strings included)."""
    if isinstance(obj, bool) or obj is None:
        return out
    if isinstance(obj, (int, float)):
        if math.isfinite(obj):
            out.append(abs(float(obj)))
    elif isinstance(obj, str):
        out.extend(n.value for n in _numbers(obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            _flatten(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _flatten(v, out)
    return out


class _Index:
    """Sorted value set answering 'is any value within tol of x' (optionally after x1000 / /1000)."""

    __slots__ = ("arr",)

    def __init__(self, values=(), scaled: bool = True):
        scales = (1.0, 1000.0, 0.001) if scaled else (1.0,)
        self.arr = sorted(v * s for v in values for s in scales)

    def hit(self, x: float, tol: float) -> bool:
        i = bisect.bisect_left(self.arr, x - tol)
        return i < len(self.arr) and self.arr[i] <= x + tol


# --------------------------------------------------------------------------------------------------
# Text cleaning: drop step headings, <design> blocks and inline JSON blobs (drafted designs)
# --------------------------------------------------------------------------------------------------

_HEADING_RE = re.compile(contract.STEP_HEADING_REGEX)
_DESIGN_BLOCK_RE = re.compile(r"<design>.*?</design>", re.S)
_DECODER = json.JSONDecoder()


def _strip_json(text: str, sink: Optional[list[float]] = None) -> str:
    """Replace <design> blocks and inline JSON objects with newlines; their numbers go to `sink`."""
    sink = [] if sink is None else sink
    for m in _DESIGN_BLOCK_RE.finditer(text):
        inner = m.group()[len("<design>"):-len("</design>")]
        try:
            _flatten(json.loads(inner), sink)
        except ValueError:
            sink.extend(n.value for n in _numbers(inner))
    text = _DESIGN_BLOCK_RE.sub("\n", text)
    out, i, pos = [], 0, text.find("{")
    while pos != -1:
        try:
            obj, end = _DECODER.raw_decode(text, pos)
        except ValueError:
            pos = text.find("{", pos + 1)
            continue
        _flatten(obj, sink)
        out.append(text[i:pos] + "\n")
        i = end
        pos = text.find("{", end)
    out.append(text[i:])
    return "".join(out)


def _clean(text: str) -> tuple[str, list[float]]:
    """Text with headings, <design> blocks and JSON blobs replaced by newlines, plus the blob numbers."""
    drafted: list[float] = []
    text = _strip_json(text, drafted)
    return _HEADING_RE.sub("\n", text), drafted


# --------------------------------------------------------------------------------------------------
# Arithmetic: tiny tokenizer + recursive-descent parser (no eval)
# --------------------------------------------------------------------------------------------------

_UNIT = (
    r"(?:N[*·-]?s|m/s(?:\^2|²|2)|m/s|ft/s|km/h|mph|kg/m(?:\^3|³)|g/cm(?:\^3|³)|m(?:\^[23]|[²³])"
    r"|mm|cm|km|kg|g|m|s|N|cal|ft|in|lb|oz|deg|°|%|J|W|kPa|Pa|Hz|:1)"
)
_UNIT_RE = re.compile(r"[ \t]*(" + _UNIT + r")(?![A-Za-z0-9])")
_TNUM_RE = re.compile(r"(?:\d{1,3}(?:,\d{3})+(?!\d)|\d+)(?:\.\d+)?|\.\d+")
_WORD_RE = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")
_RHS_RE = re.compile(r"[ \t]*(?:~|≈)?[ \t]*([-−]?)((?:\d{1,3}(?:,\d{3})+(?!\d)|\d+)(?:\.\d+)?|\.\d+)(?![\d.]\d)")
_RHS_CONT_RE = re.compile(r"[ \t]*(?:\*\*|[*×·/÷^+]|[-−](?=[ \t]*[\d(.])|[xX](?=[ \t]*[\d(.]))")
_SINGLE = {"^": "pow", "*": "mul", "×": "mul", "·": "mul", "/": "div", "÷": "div", "+": "add",
           "-": "sub", "−": "sub", "(": "lp", ")": "rp", "√": "sqrt", "π": "pi", "²": "sup", "³": "sup"}
_BINARY = {"pow", "sup", "mul", "div", "add", "sqrt"}


@dataclass
class _Tok:
    kind: str  # num pow sup mul div add sub lp rp sqrt pi word other
    start: int
    end: int
    value: float = 0.0
    unit: Optional[str] = None


def _tokenize(s: str) -> list[_Tok]:
    toks: list[_Tok] = []
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c.isspace():
            i += 1
            continue
        m = _TNUM_RE.match(s, i)
        if m:
            tok = _Tok("num", i, m.end(), float(m.group().replace(",", "")))
            i = m.end()
            mu = _UNIT_RE.match(s, i)
            if mu:
                tok.unit = mu.group(1)
                i = mu.end()
            tok.end = i
            toks.append(tok)
            continue
        if s.startswith("**", i):
            toks.append(_Tok("pow", i, i + 2))
            i += 2
            continue
        if c in _SINGLE:
            tok = _Tok(_SINGLE[c], i, i + 1)
            if c in "²³":
                tok.value = 2.0 if c == "²" else 3.0
            toks.append(tok)
            i += 1
            continue
        if c in "xX" and toks and toks[-1].kind in ("num", "rp", "pi", "sup") and (
            i + 1 >= n or not (s[i + 1].isalpha() or s[i + 1] == "_")
        ):
            toks.append(_Tok("mul", i, i + 1))
            i += 1
            continue
        m = _WORD_RE.match(s, i)
        if m:
            w = m.group().lower()
            kind = "sqrt" if w == "sqrt" else "pi" if w == "pi" else "word"
            toks.append(_Tok(kind, i, m.end()))
            i = m.end()
            continue
        toks.append(_Tok("other", i, i + 1))
        i += 1
    return toks


class _ParseError(Exception):
    pass


class _Parser:
    def __init__(self, toks: list[_Tok]):
        self.t = toks
        self.i = 0

    def _peek(self) -> Optional[str]:
        return self.t[self.i].kind if self.i < len(self.t) else None

    def parse(self) -> float:
        v = self._expr()
        if self.i != len(self.t):
            raise _ParseError("trailing tokens")
        return v

    def _expr(self) -> float:
        v = self._term()
        while self._peek() in ("add", "sub"):
            op = self.t[self.i].kind
            self.i += 1
            r = self._term()
            v = v + r if op == "add" else v - r
        return v

    def _term(self) -> float:
        v = self._unary()
        while True:
            k = self._peek()
            if k in ("mul", "div"):
                self.i += 1
                r = self._unary()
                if k == "mul":
                    v *= r
                else:
                    if r == 0:
                        raise _ParseError("division by zero")
                    v /= r
            elif k in ("pi", "sqrt", "lp"):  # implicit multiplication: 2pi, 2(3 + 1), 2 sqrt(3)
                v *= self._unary()
            else:
                return v

    def _unary(self) -> float:
        k = self._peek()
        if k == "sub":
            self.i += 1
            return -self._unary()
        if k == "add":
            self.i += 1
            return self._unary()
        return self._power()

    def _power(self) -> float:
        b = self._postfix()
        if self._peek() == "pow":
            self.i += 1
            e = self._unary()
            if abs(e) > 64 or (b < 0 and e != int(e)) or (b == 0 and e < 0):
                raise _ParseError("bad power")
            return b ** e
        return b

    def _postfix(self) -> float:
        v = self._atom()
        while self._peek() == "sup":
            v = v ** self.t[self.i].value
            self.i += 1
        return v

    def _atom(self) -> float:
        k = self._peek()
        if k == "num":
            v = self.t[self.i].value
            self.i += 1
            return v
        if k == "pi":
            self.i += 1
            return math.pi
        if k == "sqrt":
            self.i += 1
            a = self._postfix()
            if a < 0:
                raise _ParseError("sqrt of negative")
            return math.sqrt(a)
        if k == "lp":
            self.i += 1
            v = self._expr()
            if self._peek() != "rp":
                raise _ParseError("unbalanced parenthesis")
            self.i += 1
            return v
        raise _ParseError(f"unexpected {k}")


@dataclass
class _MathResult:
    checked: int = 0
    skipped: int = 0
    bad: list[str] = field(default_factory=list)
    verified_rhs: set[int] = field(default_factory=set)  # start offsets of correctly computed results


def _check_math(text: str) -> _MathResult:
    res = _MathResult()
    for pos, ch in enumerate(text):
        if ch not in "=≈":
            continue
        if ch == "=" and ((pos > 0 and text[pos - 1] in "<>!=") or text[pos + 1:pos + 2] in ("=", ">")):
            continue
        seg_start = max(text.rfind(c, 0, pos) for c in "\n=≈") + 1
        seg = text[seg_start:pos].rstrip()
        if seg.endswith("~"):
            seg = seg[:-1]
        toks = _tokenize(seg)
        blk = max((i for i, t in enumerate(toks) if t.kind in ("word", "other")), default=-1)
        suffix = toks[blk + 1:]
        if not suffix or not any(t.kind == "num" for t in suffix):
            continue
        has_op = any(t.kind in _BINARY for t in suffix) or any(t.kind == "sub" for t in suffix[1:])
        if not has_op:
            continue

        rm = _RHS_RE.match(text, pos + 1)
        if not rm:
            continue
        rhs_end = rm.end()
        mu = _UNIT_RE.match(text, rhs_end)
        rhs_unit = mu.group(1) if mu else None
        if mu:
            rhs_end = mu.end()
        if _RHS_CONT_RE.match(text, rhs_end):
            continue  # "a = b * c = d": the right side is itself an expression, checked at the next '='

        if blk >= 0:
            b, first = toks[blk], suffix[0]
            if b.kind == "word" and (
                first.kind in ("pow", "sup", "mul", "div", "add", "rp")
                or (b.end == first.start and first.kind in ("lp", "sub"))
            ):
                res.skipped += 1  # a symbol is an operand ("v^2 * 1.2", "exp(2)"): not evaluable
                continue
        expr_text = seg[suffix[0].start:].strip()
        try:
            lhs = _Parser(suffix).parse()
        except (_ParseError, OverflowError, ValueError, ZeroDivisionError):
            res.skipped += 1
            continue
        if not math.isfinite(lhs):
            res.skipped += 1
            continue
        rnum = _parse_num(rm.group(2))
        rhs = -rnum.value if rm.group(1) else rnum.value
        res.checked += 1
        tol = max(0.03 * abs(rhs), 0.5 * rnum.sig_unit)
        candidates = [lhs]
        if rhs_unit == "%":
            candidates.append(lhs * 100)
        lhs_units = {t.unit for t in suffix if t.unit}
        if rhs_unit and lhs_units and rhs_unit not in lhs_units:
            candidates.extend(lhs * f for f in (1e3, 1e-3, 1e2, 1e-2, 1e6, 1e-6))
        if any(abs(c - rhs) <= tol * (1 + 1e-9) for c in candidates):
            res.verified_rhs.add(rm.start(2))
        else:
            shown = f"{expr_text} = {rm.group(1)}{rm.group(2)}{(' ' + rhs_unit) if rhs_unit else ''}"
            res.bad.append(f"'{shown}' but the left side evaluates to {lhs:.4g}")
    return res


# --------------------------------------------------------------------------------------------------
# Safety gates and targets
# --------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class _Fail:
    name: str
    value: Optional[float]
    text: str


def _isnum(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _fmt(v: Any) -> str:
    return f"{v:g}" if _isnum(v) else str(v)


def _target_fail(name: str, actual: float, t: dict, about_rel: float) -> Optional[_Fail]:
    kind, val = t.get("kind"), t.get("value")
    if kind == "range" and isinstance(val, (list, tuple)) and len(val) == 2 and all(map(_isnum, val)):
        lo, hi = val
        if not lo <= actual <= hi:
            return _Fail(name, actual, f"{name} {_fmt(actual)} outside range [{_fmt(lo)}, {_fmt(hi)}]")
        return None
    if not _isnum(val):
        return None
    if kind == "min" and actual < val:
        return _Fail(name, actual, f"{name} {_fmt(actual)} < target min {_fmt(val)}")
    if kind == "max" and actual > val:
        return _Fail(name, actual, f"{name} {_fmt(actual)} > target max {_fmt(val)}")
    if kind in ("about", "exact") and abs(actual - val) > about_rel * abs(val):
        return _Fail(name, actual, f"{name} {_fmt(actual)} not within {about_rel:.0%} of {_fmt(val)}")
    return None


def _failures(sim: Any, targets: Any) -> list[_Fail]:
    if not isinstance(sim, dict):
        return [_Fail("simulate_error", None, "no simulate output")]
    if sim.get("ok") is not True:
        return [_Fail("simulate_error", None, f"simulate returned an error: {sim.get('error')!r}")]
    targets = targets if isinstance(targets, dict) else {}
    G = contract.GATES
    out: list[_Fail] = []

    def below(key: str, limit: float, label: str, strict: bool = False):
        v = sim.get(key)
        if not _isnum(v):
            out.append(_Fail(key, None, f"{key} missing or non-numeric ({label})"))
        elif (v <= limit) if strict else (v < limit):
            out.append(_Fail(key, v, f"{key} {_fmt(v)} {'<=' if strict else '<'} {_fmt(limit)} ({label})"))

    below("thrust_to_weight", G["min_thrust_to_weight"], "min thrust-to-weight")
    below("rail_exit_ms", G["min_rail_exit_ms"], "min rail-exit speed")
    below("stability_rail_exit_cal", G["min_launch_margin_cal"], "min launch margin")
    below("min_stability_burn_cal", G["min_burn_margin_cal"], "margin must stay above 0 in the burn", strict=True)

    imp = sim.get("total_impulse_ns")
    t_imp = targets.get("total_impulse_ns")
    imp_limit = G["max_total_impulse_ns"]
    if isinstance(t_imp, dict) and t_imp.get("kind") == "max" and _isnum(t_imp.get("value")):
        imp_limit = min(imp_limit, t_imp["value"])
    if not _isnum(imp):
        out.append(_Fail("total_impulse_ns", None, "total_impulse_ns missing or non-numeric"))
    elif imp > imp_limit:
        out.append(_Fail("total_impulse_ns", imp, f"total_impulse_ns {_fmt(imp)} > {_fmt(imp_limit)}"))

    wind = (sim.get("conditions") or {}).get("wind_ms") if isinstance(sim.get("conditions"), dict) else None
    if not _isnum(wind):
        out.append(_Fail("wind_ms", None, "conditions.wind_ms missing or non-numeric"))
    elif wind >= G["max_wind_ms"]:
        out.append(_Fail("wind_ms", wind, f"wind_ms {_fmt(wind)} >= {_fmt(G['max_wind_ms'])}"))

    gh = targets.get("ground_hit_ms")
    gh_limit, gh_applies = None, None
    if isinstance(gh, dict) and gh.get("kind") == "max" and _isnum(gh.get("value")):
        gh_limit = gh["value"]
        applies = gh.get("applies_to")
        if isinstance(applies, str) and applies.strip().lower() not in ("every section", "all", "all sections"):
            gh_applies = applies.strip().lower()
    dr = targets.get("drift_m")
    sections = sim.get("sections")
    if not isinstance(sections, list) or not sections:
        out.append(_Fail("sections", None, "no section data; landing and recovery cannot be checked"))
        sections = []
    for i, sec in enumerate(sections):
        if not isinstance(sec, dict):
            continue
        name = str(sec.get("name") or f"section {i}")
        limit = G["default_max_landing_ms"]
        if gh_limit is not None and (gh_applies is None or gh_applies in name.lower()):
            limit = gh_limit
        land = sec.get("landing_ms")
        if not _isnum(land):
            out.append(_Fail("landing_ms", None, f"{name} landing_ms missing or non-numeric"))
        elif land > limit:
            out.append(_Fail("landing_ms", land, f"{name} landing_ms {_fmt(land)} > {_fmt(limit)}"))
        if sec.get("recovery_deployed") is not True:
            out.append(_Fail("recovery_deployed", None, f"{name} recovery not deployed"))
        if sec.get("reached_ground") is False:
            out.append(_Fail("reached_ground", None, f"{name} still airborne when the simulation ended"))
        if isinstance(dr, dict):
            v = sec.get("drift_m")
            if not _isnum(v):
                out.append(_Fail("drift_m", None, f"{name} drift_m missing or non-numeric; "
                                                 "target cannot be checked"))
            else:
                f = _target_fail(f"{name} drift_m", v, dr, contract.TOLERANCES["about_rel"])
                if f:
                    out.append(f)

    for key, rel in (("apogee_m", contract.TOLERANCES["about_rel"]),
                     ("flight_time_s", contract.TOLERANCES["about_rel_time"]),
                     ("time_to_apogee_s", contract.TOLERANCES["about_rel_time"])):
        t = targets.get(key)
        if isinstance(t, dict):
            v = sim.get(key)
            if not _isnum(v):
                out.append(_Fail(key, None, f"{key} missing or non-numeric; target cannot be checked"))
            else:
                f = _target_fail(key, v, t, rel)
                if f:
                    out.append(f)
    return out


def gate_failures(sim_output: dict, targets: dict) -> list[str]:
    """Safety gates (contract.GATES) and numeric targets that a simulate output fails; [] = clean pass."""
    return [f.text for f in _failures(sim_output, targets)]


# --------------------------------------------------------------------------------------------------
# Row parsing (shared by every check)
# --------------------------------------------------------------------------------------------------


@dataclass
class _Call:
    msg_idx: int
    id: Any
    name: Any
    args: Any
    output: Any = None  # parsed tool content (dict) or None
    out_idx: Optional[int] = None


@dataclass
class _Turn:
    idx: int
    reasoning: str
    content: str
    calls: list[_Call]
    text: str = ""
    nums: list[Num] = field(default_factory=list)
    drafted: list[float] = field(default_factory=list)
    batch: list[int] = field(default_factory=list)  # tool messages directly before this turn
    math: _MathResult = field(default_factory=_MathResult)


@dataclass
class _Parsed:
    msgs: list
    prompt: str
    turns: list[_Turn]
    calls: list[_Call]
    tool_out: dict[int, Any]  # message index -> parsed tool content
    targets: dict
    final: Optional[_Turn]


def _str(x: Any) -> str:
    return x if isinstance(x, str) else ""


def _parse_row(row: dict) -> _Parsed:
    msgs = row.get("messages") if isinstance(row.get("messages"), list) else []
    prompt = _str(msgs[1].get("content")) if len(msgs) > 1 and isinstance(msgs[1], dict) else ""
    turns: list[_Turn] = []
    calls: list[_Call] = []
    tool_out: dict[int, Any] = {}
    by_id: dict[Any, _Call] = {}
    pending: list[_Call] = []
    for i, m in enumerate(msgs):
        if not isinstance(m, dict):
            continue
        role = m.get("role")
        if role == "assistant":
            tcs = m.get("tool_calls") if isinstance(m.get("tool_calls"), list) else []
            tcalls = []
            for tc in tcs:
                fn = tc.get("function") if isinstance(tc, dict) and isinstance(tc.get("function"), dict) else {}
                c = _Call(i, tc.get("id") if isinstance(tc, dict) else None, fn.get("name"), fn.get("arguments"))
                tcalls.append(c)
                if c.id is not None:
                    by_id.setdefault(c.id, c)
            calls.extend(tcalls)
            pending = list(tcalls)
            t = _Turn(i, _str(m.get("reasoning_content")), _str(m.get("content")), tcalls)
            j = i - 1
            while j >= 0 and isinstance(msgs[j], dict) and msgs[j].get("role") == "tool":
                t.batch.insert(0, j)
                j -= 1
            turns.append(t)
        elif role == "tool":
            try:
                out = json.loads(m.get("content"))
            except (TypeError, ValueError):
                out = None
            tool_out[i] = out
            c = by_id.get(m.get("tool_call_id"))
            if c is None and pending:
                c = pending[0]
            if c is not None and c.out_idx is None:
                c.output, c.out_idx = out, i
                if c in pending:
                    pending.remove(c)
    for t in turns:
        t.text, t.drafted = _clean(t.reasoning + "\n" + t.content)
        t.nums = _numbers(t.text)
        t.math = _check_math(t.text)
    final = turns[-1] if turns and turns[-1].idx == len(msgs) - 1 else None
    targets = row.get("targets") if isinstance(row.get("targets"), dict) else {}
    return _Parsed(msgs, prompt, turns, calls, tool_out, targets, final)


def _canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False)


def _design_of(c: _Call) -> Optional[str]:
    if isinstance(c.args, dict) and c.name in ("simulate", "stability") and "design" in c.args:
        return _canon(c.args["design"])
    return None


def _sims(p: _Parsed) -> list[_Call]:
    return [c for c in p.calls if c.name == "simulate" and isinstance(c.args, dict)]


# --------------------------------------------------------------------------------------------------
# Row checks
# --------------------------------------------------------------------------------------------------

_THINK_TAG_RE = re.compile(r"</?\s*(?:think|thought)\s*>", re.I)
_REQUIRED_ARGS = {t["function"]["name"]: tuple(t["function"]["parameters"].get("required", ())) for t in contract.TOOLS}
_OUTPUT_SHAPES = {"motor_lookup": contract.MOTOR_LOOKUP_OUTPUT, "stability": contract.STABILITY_OUTPUT,
                  "simulate": contract.SIMULATE_OUTPUT}


def _check_structure(row: dict, p: _Parsed, out: list[Issue]) -> None:
    def bad(msg: str, idx: Optional[int] = None, sev: Severity = "must"):
        out.append(Issue("structure", sev, msg, idx))

    if row.get("tools") != contract.TOOLS:
        bad("row['tools'] differs from contract.TOOLS")
    msgs = p.msgs
    if len(msgs) < 3:
        bad(f"expected system, user and at least one assistant turn, got {len(msgs)} messages")
    if not msgs:
        return
    m0 = msgs[0] if isinstance(msgs[0], dict) else {}
    if m0.get("role") != "system" or m0.get("content") != contract.SYSTEM_PROMPT:
        bad("messages[0] must be the system turn with exactly contract.SYSTEM_PROMPT", 0)
    if len(msgs) > 1:
        m1 = msgs[1] if isinstance(msgs[1], dict) else {}
        if m1.get("role") != "user" or not _str(m1.get("content")).strip():
            bad("messages[1] must be a non-empty user turn", 1)

    seen_ids: set = set()
    i, n = 2, len(msgs)
    while i < n:
        m = msgs[i] if isinstance(msgs[i], dict) else {}
        role = m.get("role")
        if role == "tool":
            bad("tool message without a matching assistant tool call", i)
            i += 1
            continue
        if role != "assistant":
            bad(f"unexpected role {role!r} after the user turn", i)
            i += 1
            continue
        for key in ("reasoning_content", "content"):
            if _THINK_TAG_RE.search(_str(m.get(key))):
                bad(f"literal <think>/<thought> tag typed inside {key}", i)
        if not _str(m.get("reasoning_content")).strip():
            bad("assistant turn has empty reasoning_content", i)
        tcs = m.get("tool_calls")
        if tcs in (None, []):
            if i != n - 1:
                bad("assistant turn without tool_calls before the final turn", i)
            i += 1
            continue
        if not isinstance(tcs, list):
            bad("tool_calls is not a list", i)
            i += 1
            continue
        expected = []
        for tc in tcs:
            fn = tc.get("function") if isinstance(tc, dict) else None
            if not isinstance(fn, dict) or tc.get("type") != "function":
                bad("tool call must be {'id', 'type': 'function', 'function': {'name', 'arguments'}}", i)
                expected.append((tc.get("id") if isinstance(tc, dict) else None, None))
                continue
            name, args, cid = fn.get("name"), fn.get("arguments"), tc.get("id")
            if not isinstance(cid, str) or not cid:
                bad("tool call has no id", i)
            elif cid in seen_ids:
                bad(f"duplicate tool_call id {cid!r}", i)
            seen_ids.add(cid)
            if name not in contract.TOOL_NAMES:
                bad(f"unknown tool {name!r}", i)
            if not isinstance(args, dict):
                bad(f"{name} arguments must be a dict, got {type(args).__name__}", i)
            else:
                missing = [k for k in _REQUIRED_ARGS.get(name, ()) if k not in args]
                if missing:
                    bad(f"{name} call missing required argument(s) {missing}", i)
            expected.append((cid, name))
        j = i + 1
        while j < n and isinstance(msgs[j], dict) and msgs[j].get("role") == "tool":
            j += 1
        got = j - (i + 1)
        if got != len(expected):
            bad(f"assistant turn made {len(expected)} tool call(s) but {got} tool message(s) follow", i)
        for k, (cid, name) in enumerate(expected[:got]):
            tm = msgs[i + 1 + k]
            if tm.get("tool_call_id") != cid or tm.get("name") != name:
                bad(f"tool message {k + 1} does not match call {cid!r}/{name!r} "
                    f"(got {tm.get('tool_call_id')!r}/{tm.get('name')!r})", i + 1 + k)
            try:
                o = json.loads(tm.get("content"))
            except (TypeError, ValueError):
                bad("tool content is not valid JSON", i + 1 + k)
                continue
            if not isinstance(o, dict) or not isinstance(o.get("ok"), bool):
                bad("tool content must be a JSON object with a boolean 'ok'", i + 1 + k)
                continue
            shape = _OUTPUT_SHAPES.get(name) if o["ok"] else contract.TOOL_ERROR_OUTPUT
            missing = [key for key in (shape or {}) if key not in o and key != "suggestions"]
            if missing:
                out.append(Issue("tool_shape", "should", f"{name} output missing keys {missing}", i + 1 + k))
        i = j

    last = msgs[-1] if isinstance(msgs[-1], dict) else {}
    if len(msgs) >= 3 and (
        last.get("role") != "assistant" or last.get("tool_calls")
        or not _str(last.get("reasoning_content")).strip() or not _str(last.get("content")).strip()
    ):
        bad("final message must be an assistant turn with reasoning_content and content and no tool_calls",
            len(msgs) - 1)


def _sim_read_turns(p: _Parsed) -> list[int]:
    """Assistant turn indices that directly follow a tool batch containing a simulate result."""
    sim_out = {c.out_idx for c in p.calls if c.name == "simulate" and c.out_idx is not None}
    return [t.idx for t in p.turns if any(j in sim_out for j in t.batch)]


def _check_steps(p: _Parsed, out: list[Issue]) -> None:
    heads = []  # (turn, step, name)
    for t in p.turns:
        for m in _HEADING_RE.finditer(t.reasoning):
            heads.append((t, int(m.group(1)), m.group(2)))
    for t, n, name in heads:
        if name not in contract.STEP_HEADINGS[n]:
            out.append(Issue("steps", "must", f"heading '{n}. {name}:' does not belong to step {n}", t.idx))
    present = {n for _, n, _ in heads}
    missing = [n for n in range(1, 7) if n not in present]
    if missing:
        out.append(Issue("steps", "must", f"missing step heading(s) {missing}", None))

    recheck_turns = {t.idx for t in p.turns if any(
        isinstance(p.tool_out.get(j), dict) and p.msgs[j].get("name") in ("simulate", "stability") for j in t.batch)}
    prev, prev_turn = 0, None
    for t, n, name in heads:
        if n < prev:
            # Re-check after a fix: '4. Check:' may follow '5. Fix:' in a later turn that reads a new result.
            if not (n == 4 and name == "Check" and prev == 5 and t.idx != prev_turn and t.idx in recheck_turns):
                out.append(Issue("steps", "must", f"step {n} ('{name}') comes after step {prev}", t.idx))
        prev, prev_turn = n, t.idx

    if 6 in present and p.final is not None and not any(n == 6 and t is p.final for t, n, _ in heads):
        out.append(Issue("steps", "must", "step 6 (Uncertainty) must appear in the final turn", p.final.idx))
    reads = _sim_read_turns(p)
    if reads and 5 in present and not any(n == 5 and t.idx >= reads[0] for t, n, _ in heads):
        out.append(Issue("steps", "must", "step 5 (Fix) must appear in or after the first turn that reads a "
                                          "simulate result", reads[0]))


def _msg_values(p: _Parsed) -> list[tuple[int, str, list[float]]]:
    """(message index, 'tool' | 'self', values) for every tool result and every assistant turn's own numbers."""
    out = []
    turn_by_idx = {t.idx: t for t in p.turns}
    for i, m in enumerate(p.msgs):
        if not isinstance(m, dict):
            continue
        if m.get("role") == "tool":
            o = p.tool_out.get(i)
            out.append((i, "tool", _flatten(o, []) if o is not None else [n.value for n in _numbers(_str(m.get("content")))]))
        elif i in turn_by_idx:
            t = turn_by_idx[i]
            vals = list(t.drafted)
            for c in t.calls:
                _flatten(c.args, vals)
            out.append((i, "self", vals))
    return out


def _check_numbers(p: _Parsed, out: list[Issue]) -> None:
    """[leakage] and [precision]."""
    prompt_vals = [n.value for n in _numbers(p.prompt)]
    prompt_nums = _numbers(p.prompt)
    mv = _msg_values(p)
    target_vals = _flatten({k: v.get("value") for k, v in p.targets.items()
                            if isinstance(v, dict) and k != "feasible"}, [])
    # Target values the prompt states, with the coarsest precision it used for each.
    stated: list[tuple[float, float]] = []
    for v in target_vals:
        units = [pn.sig_unit for pn in prompt_nums if abs(pn.value - v) <= _sig_tol(pn)]
        if units:
            stated.append((v, min(units)))
    conv = (0.3048, 1 / 0.3048, 0.0254, 1 / 0.0254, 0.45359237, 1 / 0.45359237, 0.0283495, 1 / 0.0283495,
            0.44704, 1 / 0.44704, 1.609344, 1 / 1.609344)
    conv_idx = _Index([v * f for v in prompt_vals for f in conv], scaled=True)
    # simulate echoes the conditions it was called with; those are the model's own inputs, not results.
    future_outputs = []
    for i, m in enumerate(p.msgs):
        if isinstance(m, dict) and m.get("role") == "tool":
            o = p.tool_out.get(i)
            if isinstance(o, dict):
                o = {key: val for key, val in o.items() if key != "conditions"}
                future_outputs.append((i, _flatten(o, [])))
            else:
                future_outputs.append((i, [n.value for n in _numbers(_str(m.get("content")))]))

    for t in p.turns:
        k = t.idx
        # What the model could know while writing turn k: the prompt, earlier tool results, and its own
        # drafted designs / tool-call arguments up to and including this turn.
        known = _Index(prompt_vals + [v for i, kind, vals in mv if (i < k and kind == "tool") or
                                      (i <= k and kind == "self") for v in vals])
        future = _Index([v for i, o in future_outputs if i > k for v in o])
        reported = set()
        for n in t.nums:
            if _is_common(n) or n.sig < 3:
                continue
            derived = n.start in t.math.verified_rhs
            if not derived and not known.hit(n.value, _dec_tol(n)) and \
                    not conv_idx.hit(n.value, _dec_tol(n) + 1e-3 * n.value):
                leak, sev = None, "must"
                if future.hit(n.value, _dec_tol(n)):
                    leak = f"{n.text} appears before the tool call that returns it"
                    # Three significant figures is estimate precision; a match there may be coincidence.
                    sev = "must" if n.sig >= 4 else "should"
                elif any(abs(n.value - v) <= _dec_tol(n) and n.sig_unit < unit for v, unit in stated):
                    leak = f"target value {n.text} is stated more precisely than the prompt gives it"
                if leak:
                    if n.text not in reported:
                        reported.add(n.text)
                        out.append(Issue("leakage", sev, leak, k))
                    continue
            if n.sig <= 3 or known.hit(n.value, _sig_tol(n)):
                continue
            derived = derived or conv_idx.hit(n.value, _sig_tol(n) + 1e-3 * n.value)
            # spec: should at 4 sig figs, must at >=5; arithmetic on earlier numbers (checked by the math
            # rule) or a unit conversion of the prompt is only a warning, since it invents no precision.
            sev: Severity = "should" if n.sig == 4 or derived else "must"
            what = "derived value" if derived else "number"
            out.append(Issue("precision", sev, f"{what} {n.text} has {n.sig} significant figures but is not "
                                               "tool output", k))


_SENT_SPLIT_RE = re.compile(r"\n+|(?<=[.!?])\s+")
_PROV_RE = re.compile(r"\b(" + "|".join(re.escape(w) for w in contract.PROVENANCE_WORDS) + r")\b", re.I)
# Negated / future / conditional use ("not simulated yet", "once simulated") is not a provenance claim.
_HEDGE_RE = re.compile(r"\b(?:not|never|no|nothing|yet|without|until|unless|before|once|if|will|would|should|"
                       r"needs?|must|to be|can|could|then)\b|n't", re.I)
_HEDGE_AFTER_RE = re.compile(r"^\s*(?:yet|later|next)\b", re.I)


def _check_provenance(p: _Parsed, out: list[Issue]) -> None:
    for t in p.turns:
        raw = (t.reasoning + "\n" + t.content).lower()
        for phrase in contract.BANNED_PHRASES:
            if phrase in raw:
                out.append(Issue("provenance", "must", f"banned phrase {phrase!r}", t.idx))
        batch_idx = None
        for sent in _SENT_SPLIT_RE.split(t.text):
            # Evaluate every provenance word in the sentence: a hedged one early on must not
            # mask an unhedged claim later in the same sentence.
            matches = [m for m in _PROV_RE.finditer(sent)
                       if not (_HEDGE_RE.search(sent[:m.start()]) or _HEDGE_AFTER_RE.match(sent[m.end():]))]
            if not matches:
                continue
            word = matches[0].group(1)
            if not t.batch:
                out.append(Issue("provenance", "must",
                                 f"'{word}' without a tool result directly before this turn: {sent.strip()[:120]!r}",
                                 t.idx))
                continue
            if batch_idx is None:
                batch_idx = _Index([v for j in t.batch for v in _flatten(p.tool_out.get(j), [])])
            if not any(batch_idx.hit(n.value, _sig_tol(n)) for n in _numbers(sent)):
                out.append(Issue("provenance", "must",
                                 f"'{word}' sentence quotes no number from the preceding tool result: "
                                 f"{sent.strip()[:120]!r}", t.idx))


def _check_math_issues(p: _Parsed, out: list[Issue], stats: Optional[dict]) -> None:
    for t in p.turns:
        for msg in t.math.bad:
            out.append(Issue("math", "must", msg, t.idx))
        if stats is not None:
            stats["math_checked"] = stats.get("math_checked", 0) + t.math.checked
            stats["math_skipped"] = stats.get("math_skipped", 0) + t.math.skipped
            stats["math_failed"] = stats.get("math_failed", 0) + len(t.math.bad)


_INFEASIBLE_RE = re.compile(r"infeasible|not feasible|can(?:'|’|no)?t be met|can not be met|not achievable|"
                            r"isn(?:'|’)t achievable|not possible|impossible", re.I)
_TARGET_WORDS = {
    "apogee_m": ("apogee", "altitude", "height", "high"),
    "ground_hit_ms": ("landing", "touchdown", "land", "descent"),
    "flight_time_s": ("flight time", "duration", "time", "seconds"),
    "time_to_apogee_s": ("time to apogee", "apogee"),
    "motor": ("motor",),
    "motor_class": ("class", "motor", "impulse", "level"),
    "motor_diameter_m": ("motor", "diameter"),
    "body_diameter_m": ("diameter", "body"),
    "total_impulse_ns": ("impulse",),
    "stages": ("stage",),
    "motor_count": ("motor", "cluster"),
    "payload_kg": ("payload",),
    "recovery": ("recovery", "chute", "parachute", "streamer", "dual"),
    "drift_m": ("drift", "field", "distance"),
}


def _check_design(p: _Parsed, out: list[Issue]) -> None:
    f = p.final
    if f is None:
        return
    content = f.content
    infeasible = isinstance(p.targets.get("feasible"), dict) and p.targets["feasible"].get("value") is False

    def bad(msg: str):
        out.append(Issue("design", "must", msg, f.idx))

    if infeasible:
        low = content.lower()
        if not _INFEASIBLE_RE.search(content):
            bad("infeasible prompt: final content must say it is infeasible / not feasible / can't be met")
        words = [w for k in p.targets if k != "feasible" for w in _TARGET_WORDS.get(k, ())]
        mt = p.targets.get("motor")
        if isinstance(mt, dict):
            words += [str(x).lower() for x in (mt.get("value") if isinstance(mt.get("value"), list) else [mt.get("value")])]
        if words and not any(w in low for w in words):
            bad("infeasible prompt: final content does not name the constraint that can't be met")

    n_open, n_close = content.count("<design>"), content.count("</design>")
    if n_open == 0 and n_close == 0:
        if not infeasible:
            bad("final content has no <design> block")
        lines = [ln for ln in content.splitlines() if ln.strip()]
        if len(lines) > contract.FINAL_SUMMARY_MAX_LINES:
            bad(f"final summary has {len(lines)} lines (max {contract.FINAL_SUMMARY_MAX_LINES})")
        return
    if n_open != 1 or n_close != 1:
        bad(f"final content must hold exactly one <design> block (found {n_open} open, {n_close} close tags)")
    m = re.search(r"<design>(.*?)</design>", content, re.S)
    if not m:
        bad("malformed <design> block")
        return
    lines = [ln for ln in content[:m.start()].splitlines() if ln.strip()]
    if len(lines) > contract.FINAL_SUMMARY_MAX_LINES:
        bad(f"summary before <design> has {len(lines)} lines (max {contract.FINAL_SUMMARY_MAX_LINES})")
    if content[m.end():].strip():
        bad("text after </design>")
    try:
        design = json.loads(m.group(1))
    except ValueError as e:
        bad(f"design JSON does not parse: {e}")
        return
    try:
        parse_design(design)
    except Exception as e:  # pydantic.ValidationError or ValueError
        first = str(e).strip().splitlines()
        bad(f"design fails schema.parse_design: {' '.join(first[:3])[:300]}")
    if infeasible:
        return
    sims = _sims(p)
    if not sims:
        bad("final design was never simulated")
        return
    last = sims[-1]
    if _canon(design) != _canon(last.args.get("design")):
        bad("final design differs from the design in the last simulate call")
    elif not (isinstance(last.output, dict) and last.output.get("ok") is True):
        bad("the last simulate call did not return ok=true")


_STILL_RE = re.compile(r"\bstill\b|does not meet|doesn't meet|not met|\bmiss(?:es|ed)?\b|falls? short|short of|"
                       r"\bfails?\b|\bfailing\b|\bexceeds?\b|over the limit|under the limit", re.I)


def _turn_window(p: _Parsed, after: int, upto: int) -> list[_Turn]:
    return [t for t in p.turns if after < t.idx <= upto]


def _check_fix(p: _Parsed, out: list[Issue], stats: Optional[dict]) -> None:
    sims = _sims(p)
    rounds = 0
    for a, b in zip(sims, sims[1:]):
        same_design = _canon(a.args.get("design")) == _canon(b.args.get("design"))
        if same_design:
            if _canon(a.args.get("conditions") or {}) == _canon(b.args.get("conditions") or {}):
                out.append(Issue("fix", "must", "no-op re-run: simulate called again with an identical design and "
                                                "conditions", b.msg_idx))
            continue
        rounds += 1
        fails = _failures(a.output, p.targets)
        if not fails:
            out.append(Issue("fix", "must", "fix without a failure: the design changed although the previous "
                                            "simulate passed every gate and target", b.msg_idx))
            continue
        window = _turn_window(p, a.out_idx if a.out_idx is not None else a.msg_idx, b.msg_idx)
        if not any("5. Fix:" in t.reasoning for t in window):
            out.append(Issue("fix", "must", "the turn that changes the design has no '5. Fix:' section", b.msg_idx))
        vals = [f.value for f in fails if f.value is not None]
        if vals:
            nums = [n for t in window for n in _numbers(t.text)]
            if not any(abs(n.value - abs(v)) <= _sig_tol(n) for n in nums for v in vals):
                out.append(Issue("fix", "must", "fix does not quote the failing value ("
                                 + "; ".join(f.text for f in fails) + ")", b.msg_idx))
    if rounds > contract.FIX_ROUND_CAP:
        out.append(Issue("fix", "should", f"{rounds} fix rounds (cap {contract.FIX_ROUND_CAP})", None))
    if sims and p.final is not None:
        fails = _failures(sims[-1].output, p.targets)
        if fails and not _STILL_RE.search(p.final.content):
            out.append(Issue("fix", "should", "the last simulate still fails (" + "; ".join(f.text for f in fails)
                             + ") but the final content does not say what is still failing", p.final.idx))
    if stats is not None:
        stats["fix_rounds"] = rounds
        stats["simulate_calls"] = len(sims)
        stats["clean_first_pass"] = bool(sims) and rounds == 0 and not _failures(sims[0].output, p.targets)


_REFLECT_RE = re.compile(r"\bwait\b|\bhmm+\b|let me (?:double[- ]check|re-?check|reconsider)|on second thought|"
                         r"\bactually,", re.I)


def _check_reflection(p: _Parsed, out: list[Issue]) -> None:
    designs = [(c.msg_idx, d) for c in p.calls if (d := _design_of(c)) is not None]
    for t in p.turns:
        m = _REFLECT_RE.search(t.reasoning)
        if not m:
            continue
        prev = next((d for i, d in reversed(designs) if i < t.idx), None)
        nxt = next((d for i, d in designs if i >= t.idx), None)
        if nxt is None or (prev is not None and nxt == prev):
            out.append(Issue("reflection", "must", f"empty reflection: '{m.group()}' but the design does not change "
                                                   "in the next tool call", t.idx))


def _step_sections(text: str, step: int) -> list[str]:
    ms = list(_HEADING_RE.finditer(text))
    return [text[m.end():(ms[k + 1].start() if k + 1 < len(ms) else len(text))]
            for k, m in enumerate(ms) if int(m.group(1)) == step]


def _check_clean_pass(p: _Parsed, out: list[Issue]) -> None:
    sims = _sims(p)
    if len(sims) != 1 or _failures(sims[0].output, p.targets):
        return
    for t in p.turns:
        for sec in _step_sections(t.reasoning, 5):
            body = sec.strip()
            if len(body) > 200 or len([ln for ln in body.splitlines() if ln.strip()]) > 1:
                out.append(Issue("clean_pass", "should", f"clean first pass but step 5 is {len(body)} chars; "
                                                         "one short line is enough", t.idx))


_CHECKS = (
    ("structure", lambda row, p, out, st: _check_structure(row, p, out)),
    ("steps", lambda row, p, out, st: _check_steps(p, out)),
    ("leakage/precision", lambda row, p, out, st: _check_numbers(p, out)),
    ("provenance", lambda row, p, out, st: _check_provenance(p, out)),
    ("math", lambda row, p, out, st: _check_math_issues(p, out, st)),
    ("design", lambda row, p, out, st: _check_design(p, out)),
    ("fix", lambda row, p, out, st: _check_fix(p, out, st)),
    ("reflection", lambda row, p, out, st: _check_reflection(p, out)),
    ("clean_pass", lambda row, p, out, st: _check_clean_pass(p, out)),
)


def lint_row(row: dict, stats: Optional[dict] = None) -> list[Issue]:
    """All row-level issues. If `stats` is a dict it receives math_checked / math_skipped / math_failed,
    fix_rounds, simulate_calls and clean_first_pass."""
    out: list[Issue] = []
    if not isinstance(row, dict):
        return [Issue("structure", "must", "row is not a JSON object", None)]
    p = _parse_row(row)
    for name, check in _CHECKS:
        try:
            check(row, p, out, stats)
        except Exception as e:  # a malformed row must not abort a whole file run
            out.append(Issue("lint_error", "must", f"{name} check crashed: {type(e).__name__}: {e}", None))
    return out


# --------------------------------------------------------------------------------------------------
# File checks
# --------------------------------------------------------------------------------------------------

_MOTOR_TOKEN_RE = re.compile(r"\b(?:\d[x×])?[A-O]\d{1,5}[A-Z]{0,3}(?:-\d{1,2}[A-Z]?)?\b")
_DIGITS_RE = re.compile(r"\d+(?:[.,]\d+)*")


def _skeletons(reasoning: str) -> set[str]:
    text = _HEADING_RE.sub("\n", _strip_json(reasoning))
    out = set()
    for sent in _SENT_SPLIT_RE.split(text):
        sent = _MOTOR_TOKEN_RE.sub("M", sent)
        sent = _DIGITS_RE.sub("#", sent).lower()
        sent = " ".join(sent.split())
        if len(sent.split()) >= 6:
            out.add(sent)
    return out


def lint_file(rows: list[dict], report: Optional[dict] = None) -> list[tuple[Any, Issue]]:
    """Row-level issues for every row plus file-level checks ([dup], [repetition], [clean_pass_share]).
    File-level issues that are not about one row carry row_id None. If `report` is a dict it receives
    n_rows, clean_pass_share, math counters, top_skeletons (top 20) and repetition (skeleton -> row ids)."""
    out: list[tuple[Any, Issue]] = []
    n = len(rows)
    by_prompt: dict[str, list] = defaultdict(list)
    skel_rows: dict[str, list] = defaultdict(list)
    clean = 0
    math_tot = {"math_checked": 0, "math_skipped": 0, "math_failed": 0}
    for i, row in enumerate(rows):
        rid = row.get("id", i) if isinstance(row, dict) else i
        st: dict = {}
        for iss in lint_row(row, st):
            out.append((rid, iss))
        clean += bool(st.get("clean_first_pass"))
        for k in math_tot:
            math_tot[k] += st.get(k, 0)
        msgs = row.get("messages") if isinstance(row, dict) and isinstance(row.get("messages"), list) else []
        if len(msgs) > 1 and isinstance(msgs[1], dict):
            by_prompt[" ".join(_str(msgs[1].get("content")).lower().split())].append(rid)
        sk: set[str] = set()
        for m in msgs:
            if isinstance(m, dict) and m.get("role") == "assistant":
                sk |= _skeletons(_str(m.get("reasoning_content")))
        for s in sk:
            skel_rows[s].append(rid)

    for prompt, rids in by_prompt.items():
        for rid in rids[1:]:
            out.append((rid, Issue("dup", "must", f"user prompt identical to row {rids[0]!r}", 1)))

    ranked = sorted(skel_rows.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    for skel, rids in ranked:
        c = len(rids)
        if c < 3 or n == 0:
            break
        share = c / n
        sev: Optional[Severity] = "must" if share > 0.15 else "should" if share > 0.05 else None
        if sev:
            out.append((None, Issue("repetition", sev, f"sentence skeleton in {c}/{n} rows ({share:.0%}): {skel!r} "
                                                       f"e.g. rows {rids[:5]}", None)))
    share_clean = clean / n if n else 0.0
    if n and share_clean < 0.30:
        out.append((None, Issue("clean_pass_share", "should",
                                f"only {clean}/{n} rows ({share_clean:.0%}) pass on the first simulate with no fix "
                                "(want >= 30%)", None)))
    if report is not None:
        report.update(
            n_rows=n,
            clean_pass_share=share_clean,
            **math_tot,
            top_skeletons=[(s, len(r), len(r) / n if n else 0.0) for s, r in ranked[:20]],
            repetition={s: r for s, r in ranked if n and len(r) >= 3 and len(r) / n > 0.05},
        )
    return out
