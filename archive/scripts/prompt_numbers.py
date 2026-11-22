"""Find, classify and re-write the flight numbers inside an sft prompt.

Used by build_sft_v2.py (to update prompt numbers to the re-simulated values while
keeping the wording) and by verify_sft_v2.py (to prove every number in a v2 prompt
matches the v2 targets). Pure functions, no I/O.

A prompt number is one of:
  apogee_m, max_velocity_ms, max_accel_ms2, max_mach, time_to_apogee_s,
  flight_time_s, ground_hit_ms, deployment_velocity_ms
or a static design number (mass in g, length in cm) that a re-sim cannot change.
"""
import math
import re

# motor names ("on a 1526K160-6, 2833L805-P motor") and "2-stage" contain digits that are not
# flight numbers; they are masked with same-length filler so string offsets stay valid.
MOTOR_RE = re.compile(r"\b(?:on|for) (?:a|an|two|three) (.+?) motors?\b")
STAGE_RE = re.compile(r"\b\d+-stage\b")

NUM = r"(\d[\d,]*(?:\.\d+)?|None)"
TOKEN_RE = re.compile(
    r"Mach\s+" + NUM + r"(?![\w.])"
    r"|" + NUM + r"\s*(m/s²|m/s|seconds|s|m|g|cm)(?![\w/²])")

STATIC_UNITS = {"g", "cm"}
BOUND_WORDS = ("under", "less than", "below")


def mask(prompt):
    out = list(prompt)
    for rx, grp in ((MOTOR_RE, 1), (STAGE_RE, 0)):
        for m in rx.finditer(prompt):
            for i in range(m.start(grp), m.end(grp)):
                out[i] = "#"
    return "".join(out)


def _decimals(s):
    return len(s.split(".")[1]) if "." in s else 0


def tokens(prompt):
    """[(start, end, text, unit, quantity, is_bound)] for every number in the prompt."""
    mp = mask(prompt)
    toks = []
    prev_end = 0
    for m in TOKEN_RE.finditer(mp):
        if m.group(1) is not None:
            text, unit, s, e = m.group(1), "mach", m.start(1), m.end(1)
        else:
            text, unit, s, e = m.group(2), m.group(3), m.start(2), m.end(2)
        before = mp[prev_end:s].lower()
        after = mp[m.end():m.end() + 14].lower()
        bound = any(before.rstrip().endswith(w) for w in BOUND_WORDS)
        q = classify(unit, before, after)
        toks.append((s, e, text, unit, q, bound))
        prev_end = m.end()
    # leftover digits that are not part of a recognised token = unaccounted numbers
    covered = set()
    for s, e, *_ in toks:
        covered.update(range(s, e))
    stray = [i for i, ch in enumerate(mp) if ch in "0123456789" and i not in covered]
    return toks, stray


def classify(unit, before, after):
    if unit == "mach":
        return "max_mach"
    if unit in STATIC_UNITS:
        return "static"
    if unit == "m/s²":
        return "max_accel_ms2"
    if unit == "m/s":
        if "deploy" in before:
            return "deployment_velocity_ms"
        if re.search(r"touch|land|down|gentl|soft", before):
            return "ground_hit_ms"
        return "max_velocity_ms"
    if unit in ("s", "seconds"):
        if after.startswith(" to apogee") or re.search(r"apogee in (?:about|around) $", before):
            return "time_to_apogee_s"
        return "flight_time_s"
    if unit == "m":
        return "apogee_m"
    return None


def value(text):
    return None if text == "None" else float(text.replace(",", ""))


def fmt_like(x, text, quantity):
    """Format x with the precision / comma style of the original token text."""
    d = _decimals(text)
    s = f"{x:.{d}f}"
    if "," in text or (quantity == "apogee_m" and d == 0 and abs(x) >= 1000):
        ip, _, fp = s.partition(".")
        s = f"{int(ip):,}" + ("." + fp if fp else "")
    return s


def tight_bound(x, text, quantity):
    """Smallest number at the token's precision that is strictly greater than x."""
    d = _decimals(text)
    step = 10 ** -d
    b = math.floor(x / step + 1e-9) * step + step
    return fmt_like(b, text, quantity)


def close(token_val, true_val, text):
    """Does the displayed token plausibly display true_val? (rounding or <=6%)."""
    if token_val is None or true_val is None:
        return False
    half = 0.5 * 10 ** -_decimals(text)
    return abs(token_val - true_val) <= max(0.06 * abs(true_val), half + 1e-9)


# Qualitative phrases that pin a number without digits: (regex, quantity, lo, hi).
QUAL = [
    (r"just over a minute|bit (?:more|over) than a minute|a bit more than a minute", "flight_time_s", 60, 80),
    (r"(?:well over) a minute", "flight_time_s", 75, None),
    (r"(?<!well )(?:over|more than) a minute(?! and)", "flight_time_s", 60, None),
    (r"a minute and a half", "flight_time_s", 80, 100),
    (r"close to a minute", "flight_time_s", 50, 65),
    (r"for about a minute(?! and)", "flight_time_s", 50, 70),
    (r"half-minute|half a minute", "flight_time_s", 25, 35),
    (r"few hundred feet", "apogee_m", 61, 305),
    (r"few hundred meters", "apogee_m", 200, 999),
    (r"couple hundred meters", "apogee_m", 150, 350),
    (r"slow|gentl|soft|floaty|drifts? back down", "ground_hit_ms", None, 6.0),
    (r"long, slow descent", "flight_time_s", 60, None),
]


def qual_checks(prompt):
    out = []
    low = prompt.lower()
    for rx, q, lo, hi in QUAL:
        if re.search(rx, low):
            out.append((rx, q, lo, hi))
    return out


def _qual_viol(prompt, vals):
    bad = []
    for rx, q, lo, hi in qual_checks(prompt):
        v = vals.get(q)
        if v is None or (lo is not None and v <= lo) or (hi is not None and v > hi):
            bad.append((rx, q, lo, hi, v))
    return bad


def qual_ok(prompt, vals, old=None):
    """Problems with qualitative wording ("comes down gently", "over a minute") for vals.

    The ranges are judgement calls, so a phrase only counts as broken when it held for the
    v1 values the prompt was written from (`old`) and fails for `vals`. Phrases that v1's
    own templates already violated (e.g. "comes down gently, under 8.8 m/s") are inherited,
    not introduced by the re-sim, and are reported separately by the verifier."""
    held = None if old is None else {b[0] for b in _qual_viol(prompt, old)}
    out = []
    for rx, q, lo, hi, v in _qual_viol(prompt, vals):
        if held is not None and rx in held:
            continue
        out.append(f"'{rx}' needs {q} in ({lo},{hi}] but is {v}")
    return out


def rewrite(prompt, old, new):
    """Return (new_prompt, problems, notes). old/new: dict quantity -> value.

    Every flight number must be consistent with `old` (the v1 values the prompt was
    written from); it is replaced by the `new` value at the same precision. Bounds
    ("under N") are kept if they still hold, else tightened to the smallest value at
    that precision above the new value."""
    toks, stray = tokens(prompt)
    problems, notes = [], []
    if stray:
        problems.append(f"unrecognised digits at {stray}")
    out, last = [], 0
    for s, e, text, unit, q, bound in toks:
        out.append(prompt[last:s])
        last = e
        if q == "static":
            out.append(text)
            continue
        tv = value(text)
        ov, nv = old.get(q), new.get(q)
        if q == "deployment_velocity_ms" and not (ov is not None and close(tv, ov, text)) \
                and close(tv, old.get("ground_hit_ms"), text):
            # v1 template bug: "deployment at about X m/s" was filled with the touchdown
            # velocity. Accept it as consistent with v1 and write the real deployment velocity.
            ov = old.get("ground_hit_ms")
            notes.append("deployment_was_touchdown")
        if ov is None and tv is not None and nv is not None and close(tv, nv, text):
            # v1's stored sim lacks this value (e.g. no deploymentvelocity attribute);
            # the human-written number agrees with the re-sim, so it is consistent.
            ov = nv
        if tv is None or ov is None or nv is None or not math.isfinite(nv):
            problems.append(f"{text} {unit}: no value for {q}")
            out.append(text)
            continue
        if bound:
            # v1 templates wrote "under round(x)", which can sit just below x; that is still
            # "written from" x. Anything else is inconsistent.
            if not (tv > ov or close(tv, ov, text)):
                problems.append(f"bound {text} {unit} inconsistent with v1 {q}={ov}")
            if not tv > ov:
                notes.append("v1_bound_was_violated")
            out.append(text if tv > nv else tight_bound(nv, text, q))
        else:
            if not close(tv, ov, text):
                problems.append(f"{text} {unit} does not match v1 {q}={ov}")
            out.append(fmt_like(nv, text, q))
    out.append(prompt[last:])
    return "".join(out), problems, notes


def check(prompt, vals, old=None):
    """Verifier side: every flight number in prompt displays vals (bounds hold), and no
    qualitative phrase that held for `old` is broken for vals."""
    toks, stray = tokens(prompt)
    errs = []
    if stray:
        errs.append(f"unrecognised digits at {stray}")
    for s, e, text, unit, q, bound in toks:
        if q == "static":
            continue
        tv, v = value(text), vals.get(q)
        if tv is None or v is None:
            errs.append(f"{text} {unit}: missing {q}")
        elif bound:
            if not tv > v:
                errs.append(f"bound {text} {unit} not above {q}={v}")
        elif fmt_like(v, text, q) != text:
            errs.append(f"{text} {unit} != {q}={v} at that precision ({fmt_like(v, text, q)})")
    errs += qual_ok(prompt, vals, old)
    return errs
