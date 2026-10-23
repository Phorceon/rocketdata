"""Build new_results/sft_v1_readable.md from new_results/sft_v1.jsonl.

Read-only w.r.t. sft_v1.jsonl. Difficulty is labelled by the number of
requirements stated in each prompt (more requirements = easier to satisfy).
A requirement counts when its value appears in the prompt and matches the
corresponding target / simulated value (rounding, thousands separators and
unit conversions allowed; surrounding words decide which quantity a number
belongs to). Quantities considered: apogee, max velocity, max mach, time to
apogee, flight time and touchdown speed (from the row's ``targets``), max
acceleration (from the stored simulation), and the motor designation(s) named
in the prompt. Deterministic.
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
JSONL = os.path.join(REPO, "new_results", "sft_v1.jsonl")
OUT = os.path.join(REPO, "new_results", "sft_v1_readable.md")

sys.path.insert(0, HERE)
from sft_v1_lib import sims_of  # noqa: E402

# Requirement-count thresholds (choice (a): a named motor is a requirement).
EASY_MIN = 3      # 3 requirements
MEDIUM_MIN = 2    # 2 requirements
# 0-1 requirements -> hard

# Rows whose prompt numbers grossly disagree with the stored rocket (or that
# carry a broken "None" template), verified by hand. See README section.
MISMATCH_ROWS = {
    "U-197": "prompt contains literal 'None m/s' for deployment (broken template)",
    "U-199": "prompt asks for 5,899 m apogee / 317 s flight; rocket actually "
             "flies 5,748 m and lands after 28.5 s",
    "U-441": "prompt asks for 244 m / 61 s; rocket actually flies 31.9 m over "
             "10.3 s",
    "U-443": "prompt asks for 263 m / 73 s; rocket actually flies 31.8 m over "
             "10.8 s",
    "U-444": "prompt asks for 273 m / 70 s; rocket actually flies 38.7 m over "
             "12.2 s",
    "U-452": "prompt asks for 307 m / 59 s; rocket actually flies 57.9 m over "
             "13.7 s",
}


# --------------------------------------------------------------------------- #
# data helpers
# --------------------------------------------------------------------------- #
def load_rows():
    return [json.loads(l) for l in open(JSONL, encoding="utf-8") if l.strip()]


def design_of(row):
    return json.loads(re.search(r"<design>\n(.*)\n</design>",
                                row["messages"][2]["content"], re.S).group(1))


def walk(comps):
    for c in comps:
        yield c
        yield from walk(c.get("contains", []))


def split_motors(motor):
    items = motor if isinstance(motor, list) else [motor]
    out = []
    for it in items:
        out += [t.strip() for t in str(it).split(",") if t.strip()]
    return out


def _max_accel_index():
    """id -> max acceleration (m/s^2) from the stored simulation."""
    idx = {}
    for r in load_rows():
        try:
            for s in sims_of(r["file"]):
                if s.get("name") == r["sim"]:
                    idx[r["id"]] = s.get("max_acceleration_ms2")
                    break
        except Exception:
            pass
    return idx


# --------------------------------------------------------------------------- #
# requirement counting
# --------------------------------------------------------------------------- #
TOL = {
    "apogee": 0.12,
    "max velocity": 0.08,
    "max acceleration": 0.12,
    "time to apogee": 0.15,
    "flight time": 0.15,
    "touchdown speed": 0.15,
    "max mach": 0.15,
}
NUM_RE = (r"(\d{1,3}(?:,\d{3})+|\d+[.,]\d+|\d+)\s*"
          r"(m/s²|m/s\^2|m/s2|m/s|ft/s|m|meters?|metres?|km|kilometers?|ft|feet|"
          r"s|seconds?|sec|min|minutes?|mach)\b")


def _norm_num(raw):
    if re.fullmatch(r"\d{1,3}(,\d{3})+", raw):
        return float(raw.replace(",", ""))
    return float(raw.replace(",", "."))


def _to_m(n, u):
    if u in ("m", "meters", "meter", "metres", "metre"):
        return n
    if u in ("km", "kilometers", "kilometer"):
        return n * 1000
    if u in ("ft", "feet", "foot"):
        return n * 0.3048
    return None


def _to_s(n, u):
    if u in ("s", "seconds", "sec"):
        return n
    if u in ("min", "minutes", "minute"):
        return n * 60
    return None


def _to_ms(n, u):
    if u in ("m/s", "meters/s"):
        return n
    if u == "ft/s":
        return n * 0.3048
    return None


def _strip_motors(prompt, motors):
    s = prompt
    for mot in sorted(motors, key=len, reverse=True):
        s = re.sub(re.escape(mot), " [MOTOR] ", s, flags=re.I)
    s = re.sub(r"\b[A-O]\d{1,4}[A-Za-z0-9\-()]*\b", " [MOTOR] ", s)
    s = re.sub(r"\b\d{3,4}[A-Z]\d{2,4}[A-Z0-9\-]*\b", " [MOTOR] ", s)
    return s


def count_requirements(row, max_accel=None):
    """Return the set of requirement labels satisfied by the prompt."""
    p = row["prompt_text"]
    pl = p.lower()
    t = row["targets"]
    motors = split_motors(design_of(row)["flight"]["motor"])
    ma = (max_accel or {}).get(row["id"])
    s = _strip_motors(p, motors)
    found = set()

    # qualitative time statements
    if re.search(r"a bit (more|over|longer) than a minute|just over a minute|"
                 r"over a minute|more than a minute|well over a minute|"
                 r"minute and a half|a minute and a half", pl):
        found.add("flight time")
    if re.search(r"(long|slow)[- ,]{0,3}(float|descent)|floaty|"
                 r"slow-floating|slow floating|drift\w* (back )?down slowly|"
                 r"comes down slowly|down slowly", pl):
        found.add("flight time")
    for _ in re.finditer(r"\b(half|one|two|three|four|five|six|seven|eight|nine|"
                         r"ten|fifteen|twenty|thirty)[ -]?(minute|minutes|min)\b",
                         pl):
        found.add("flight time")
    # qualitative altitude statements
    if re.search(r"a few hundred (meters|metres|feet|foot)|"
                 r"a couple hundred (meters|metres|feet|foot)|"
                 r"few hundred (m|ft)\b", pl):
        found.add("apogee")

    for m in re.finditer(NUM_RE, s, re.I):
        num = _norm_num(m.group(1))
        u = m.group(2).lower()
        i, j = m.start(), m.end()
        lb = s[max(0, i - 40):i].lower()
        la = s[j:j + 40].lower()
        bound = (bool(re.search(r"\b(under|below|around|about|near|close to|"
                                r"roughly|approximately|over)\s*$", lb))
                 or bool(re.search(r"^\s*(or (less|under)|max)\b", la)))
        cand = []
        if u in ("m/s²", "m/s^2", "m/s2") and ma:
            cand.append(("max acceleration", abs(num - ma) / max(1, ma)))
        elif u == "mach" and t["max_mach"]:
            cand.append(("max mach",
                         abs(num - t["max_mach"]) / max(0.01, abs(t["max_mach"]))))
        elif u in ("m/s", "meters/s", "ft/s"):
            v = _to_ms(num, u)
            if v is not None:
                cand.append(("max velocity",
                             abs(v - t["max_velocity_ms"]) / max(1, t["max_velocity_ms"])))
                if t["ground_hit_ms"]:
                    cand.append(("touchdown speed",
                                 abs(v - t["ground_hit_ms"]) / max(0.01, t["ground_hit_ms"])))
        elif u in ("m", "meters", "metre", "metres", "meter", "km", "kilometers",
                   "kilometer", "ft", "feet"):
            v = _to_m(num, u)
            if v is not None:
                cand.append(("apogee", abs(v - t["apogee_m"]) / max(1, t["apogee_m"])))
        elif u in ("s", "seconds", "sec", "min", "minutes", "minute"):
            v = _to_s(num, u)
            if v is not None:
                cand.append(("time to apogee",
                             abs(v - t["time_to_apogee_s"]) / max(1, t["time_to_apogee_s"])))
                cand.append(("flight time",
                             abs(v - t["flight_time_s"]) / max(1, t["flight_time_s"])))
        ok = [(f, e) for f, e in cand if e <= TOL.get(f, 0.15)]
        if not ok and bound:
            ok = [(f, e) for f, e in cand if e <= TOL.get(f, 0.15) * 2.0]
        if not ok:
            continue
        ok.sort(key=lambda fe: fe[1])
        best = ok[0]
        labels = {f for f, _ in ok}
        if (best[0] == "max velocity" and t["ground_hit_ms"]
                and any(x in la for x in ("touch", "ground", "land", "deployment", "under"))
                and "touchdown speed" in labels):
            best = ("touchdown speed", dict(ok)["touchdown speed"])
        if {"time to apogee", "flight time"} <= labels:
            d = dict(ok)
            if "apogee" in la[:20] or "apogee" in lb[-20:]:
                best = ("time to apogee", d["time to apogee"])
            elif any(x in lb[-25:] + " " + la[:25]
                     for x in ("flight", "total", "down in", "back", "up about",
                               "stays", "hangs", "flies")):
                best = ("flight time", d["flight time"])
        found.add(best[0])

    # named motor
    for mot in motors:
        if re.search(r"\b" + re.escape(mot) + r"\b", p, re.I):
            found.add("motor")
            break
    return found


def bucket(n):
    if n >= EASY_MIN:
        return "easy"
    if n >= MEDIUM_MIN:
        return "medium"
    return "hard"


# --------------------------------------------------------------------------- #
# formatting
# --------------------------------------------------------------------------- #
LEVEL_TITLE = {"easy": "🟢 Easy", "medium": "🟡 Medium", "hard": "🔴 Hard"}
LEVEL_WORD = {"easy": "EASY", "medium": "MEDIUM", "hard": "HARD"}
LEVEL_RANGE = {"easy": "3 requirements", "medium": "2 requirements",
               "hard": "0–1 requirements"}
LEVEL_MEANS = {
    "easy": "Prompt states 3 target values, so lots of freedom is allowed",
    "medium": "Prompt states 2 target values",
    "hard": "Prompt states 0 or 1 target value (very open-ended)",
}


def fmt(x):
    if x is None:
        return "—"
    if abs(x - round(x)) < 1e-9:
        return str(int(round(x)))
    return f"{x:g}"


def targets_line(t):
    vals = [
        ("apogee", f"{fmt(t['apogee_m'])} m"),
        ("max velocity", f"{fmt(t['max_velocity_ms'])} m/s"),
        ("time to apogee", f"{fmt(t['time_to_apogee_s'])} s"),
        ("flight time", f"{fmt(t['flight_time_s'])} s"),
        ("touchdown", f"{fmt(t['ground_hit_ms'])} m/s"),
        ("wind", f"{fmt(t['wind_ms'])} m/s"),
    ]
    return " · ".join(f"{k} {v}" for k, v in vals)


def motor_text(motor):
    if isinstance(motor, list):
        return ", ".join(motor)
    return motor


def parts_list(comps, stages, chutes, stream, mass):
    has = lambda t: any(c["type"] == t for c in comps)
    items = []
    if has("nosecone"):
        items.append("nose cone")
    nb = sum(1 for c in comps if c["type"] == "bodytube")
    if nb:
        items.append(f"{nb} body tube" + ("s" if nb != 1 else ""))
    if has("transition"):
        items.append("transition")
    if has("freeformfinset"):
        items.append("freeform fins")
    fin_n = 0
    for c in comps:
        if c["type"] in ("trapezoidfin", "ellipticalfin", "tubefin"):
            fin_n += int(c.get("fin_count") or 1)
    if fin_n:
        items.append(f"{fin_n} fins")
    if has("pod_set"):
        items.append("pods")
    if stages:
        items.append(f"{stages} stage" + ("s" if stages != 1 else ""))
    rec = []
    if chutes:
        rec.append(f"{chutes} parachute" + ("s" if chutes != 1 else ""))
    if stream:
        rec.append(f"{stream} streamer" + ("s" if stream != 1 else ""))
    if rec:
        items.append(" + ".join(rec) + " recovery")
    if has("innertube") or has("engineblock"):
        items.append("motor mount")
    if mass:
        items.append("mass/ballast")
    return ", ".join(items) if items else "—"


def why_line(level, reqs):
    """e.g. 'Why easy: 3 requirements: apogee, flight time, motor'."""
    ordered = [r for r in ("apogee", "max velocity", "max mach", "time to apogee",
                           "flight time", "max acceleration", "touchdown speed",
                           "motor") if r in reqs]
    n = len(ordered)
    if n == 0:
        return f"Why {level}: 0 requirements (no target value stated in the prompt)"
    word = "requirement" if n == 1 else "requirements"
    return f"Why {level}: {n} {word}: {', '.join(ordered)}"


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main():
    rows = load_rows()
    max_accel = _max_accel_index()
    for r in rows:
        r["_reqs"] = count_requirements(r, max_accel)
        r["_level"] = bucket(len(r["_reqs"]))

    levels = defaultdict(list)
    for r in rows:
        levels[r["_level"]].append(r)
    for lv in levels:
        levels[lv].sort(key=lambda r: r["id"])

    order = ["easy", "medium", "hard"]
    counts = {lv: len(levels[lv]) for lv in order}
    nfiles = len(set(r["file"] for r in rows))
    mismatches = [r for r in rows if r["id"] in MISMATCH_ROWS]

    L = []
    L.append("# Readable SFT v1")
    L.append("")
    L.append("A human-readable view of `new_results/sft_v1.jsonl` (the balanced "
             "SFT v1 training split), one section per difficulty level. Difficulty "
             "is based ONLY on the number of requirements stated in the prompt: a "
             "requirement is counted when its value appears in the prompt and "
             "matches the rocket's target or simulated value (rounding, thousands "
             "separators and unit conversions allowed). A named motor counts as a "
             "requirement. More stated requirements = easier, because the task is "
             "more constrained.")
    L.append("")
    L.append("| Level | Requirements | Count | What it means |")
    L.append("|---|---|---|---|")
    for lv in order:
        L.append(f"| {LEVEL_TITLE[lv].split(' ',1)[1]} | {LEVEL_RANGE[lv]} | "
                 f"{counts[lv]} | {LEVEL_MEANS[lv]} |")
    L.append("")
    L.append(f"**Total rows:** {len(rows)} · **Distinct rockets:** {nfiles}")
    L.append("")

    if mismatches:
        L.append("## ⚠️ Prompt doesn't match its rocket")
        L.append("")
        L.append("These rows have a prompt whose numbers do not describe the "
                 "rocket they are paired with (or contain a broken value). They "
                 "are listed here for visibility and left unchanged.")
        L.append("")
        for r in sorted(mismatches, key=lambda r: r["id"]):
            L.append(f"- **{r['id']}** — {MISMATCH_ROWS[r['id']]}")
            L.append(f"  - Prompt: {r['prompt_text']}")
            L.append(f"  - Targets: {targets_line(r['targets'])}")
        L.append("")

    L.append("## Contents")
    L.append("")
    for lv in order:
        L.append(f"- [{LEVEL_TITLE[lv]} ({counts[lv]})](#{lv}-{counts[lv]})")
    L.append("")

    for lv in order:
        L.append(f'<a id="{lv}-{counts[lv]}"></a>')
        L.append("")
        L.append(f"## {LEVEL_TITLE[lv]} ({counts[lv]})")
        L.append("")
        for r in levels[lv]:
            d = design_of(r)
            comps = list(walk(d["components"]))
            stages = sum(1 for c in comps if c["type"] == "stage_marker")
            chutes = sum(1 for c in comps if c["type"] == "parachute")
            stream = sum(1 for c in comps if c["type"] == "streamer")
            mass = sum(1 for c in comps if c["type"] == "masscomponent")
            L.append(f"### {r['id']} · {LEVEL_WORD[lv]}")
            L.append(f"**Prompt:** {r['prompt_text']}")
            L.append(f"**Rocket:** `{r['file']}` · **Sim:** {r['sim']} · "
                     f"**Motor:** {motor_text(d['flight']['motor'])}")
            L.append(f"**{why_line(lv, r['_reqs'])}**")
            if r["id"] in MISMATCH_ROWS:
                L.append(f"**⚠️ prompt/target mismatch:** {MISMATCH_ROWS[r['id']]}")
            L.append(f"**Targets:** {targets_line(r['targets'])}")
            L.append(f"**Parts:** {parts_list(comps, stages, chutes, stream, mass)}")
            L.append("<details><summary>Full model answer</summary>")
            L.append("")
            L.append("```")
            L.append(r["messages"][2]["content"])
            L.append("```")
            L.append("</details>")
            L.append("")

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))

    print(f"WROTE {OUT}")
    print("counts:", counts)
    print("total:", len(rows), "distinct rockets:", nfiles,
          "mismatch rows:", len(mismatches))


if __name__ == "__main__":
    main()


# --- Extended API for v2 builder ---
def _fmt_for_apogee(tval, unit_orig):
    if unit_orig in ('ft', 'feet', 'foot'):
        nv = tval * 3.28084
        if nv >= 1000:
            return f"{int(round(nv))} feet"
        return f"{round(nv)} feet"
    if tval >= 1000:
        return f"{int(round(tval))} m"
    return f"{round(tval)} m"


def _fmt_for_vel(tval, unit_orig):
    if unit_orig == 'ft/s':
        nv = tval * 3.28084
        return f"{round(nv)} ft/s"
    if abs(tval) < 10:
        return f"{tval:.2f} m/s"
    if abs(tval) < 100:
        return f"{round(tval, 1)} m/s"
    return f"{round(tval)} m/s"


def _fmt_for_time(tval_s, unit_orig):
    if unit_orig in ('min', 'minutes', 'minute'):
        mv = tval_s / 60.0
        if mv >= 1.5:
            return f"{round(mv)} minutes"
        return f"{round(mv)} minutes"
    if tval_s >= 120:
        return f"{round(tval_s)} seconds"
    return f"{round(tval_s)} seconds"


def count_requirements_with_spans(row, max_accel=None, new_targets=None):
    """Return (found_set, spans) where spans have start,end,new_str,quantity."""
    p = row["prompt_text"]
    pl = p.lower()
    t = new_targets if new_targets is not None else row["targets"]
    motors = split_motors(design_of(row)["flight"]["motor"])
    ma = (max_accel or {}).get(row["id"])
    if new_targets is None:
        ma_use = ma
    else:
        # for new targets, max accel might come from sim; try to get from stored
        ma_use = ma
    s2 = _strip_motors(p, motors)
    found = set()
    spans = []

    # qualitative - skip for now (can't map numerically)
    for m in re.finditer(NUM_RE, s2, re.I):
        num = _norm_num(m.group(1))
        u = m.group(2).lower()
        i, j = m.start(), m.end()
        lb = s2[max(0, i - 40):i].lower()
        la = s2[j:j + 40].lower()
        bound = (bool(re.search(r"\b(under|below|around|about|near|close to|"
                                r"roughly|approximately|over)\s*$", lb))
                 or bool(re.search(r"^\s*(or (less|under)|max)\b", la)))
        cand = []
        if u in ("m/s²", "m/s^2", "m/s2"):
            if ma_use is not None:
                cand.append(("max acceleration", abs(num - ma_use) / max(1, abs(ma_use))))
        elif u == "mach" and t.get("max_mach") is not None:
            cand.append(("max mach",
                         abs(num - t["max_mach"]) / max(0.01, abs(t["max_mach"]))))
        elif u in ("m/s", "meters/s", "ft/s"):
            v = _to_ms(num, u)
            if v is not None and t.get("max_velocity_ms") is not None:
                cand.append(("max velocity",
                             abs(v - t["max_velocity_ms"]) / max(1, abs(t["max_velocity_ms"]))))
            if v is not None and t.get("ground_hit_ms") is not None and t["ground_hit_ms"] == t["ground_hit_ms"]:
                cand.append(("touchdown speed",
                             abs(v - abs(t["ground_hit_ms"])) / max(0.01, abs(t["ground_hit_ms"]))))
        elif u in ("m", "meters", "metre", "metres", "meter", "km", "kilometers",
                   "kilometer", "ft", "feet"):
            v = _to_m(num, u)
            if v is not None and t.get("apogee_m") is not None:
                cand.append(("apogee", abs(v - t["apogee_m"]) / max(1, abs(t["apogee_m"]))))
        elif u in ("s", "seconds", "sec", "min", "minutes", "minute"):
            v = _to_s(num, u)
            if v is not None and t.get("time_to_apogee_s") is not None:
                cand.append(("time to apogee",
                             abs(v - t["time_to_apogee_s"]) / max(1, abs(t["time_to_apogee_s"]))))
            if v is not None and t.get("flight_time_s") is not None:
                cand.append(("flight time",
                             abs(v - t["flight_time_s"]) / max(1, abs(t["flight_time_s"]))))
        ok = [(f, e) for f, e in cand if e <= TOL.get(f, 0.15)]
        if not ok and bound:
            ok = [(f, e) for f, e in cand if e <= TOL.get(f, 0.15) * 2.0]
        if not ok:
            continue
        ok.sort(key=lambda fe: fe[1])
        best = ok[0]
        labels = {f for f, _ in ok}
        if (best[0] == "max velocity" and t.get("ground_hit_ms") is not None and t["ground_hit_ms"] == t["ground_hit_ms"]
                and any(x in la for x in ("touch", "ground", "land", "deployment", "under"))
                and "touchdown speed" in labels):
            best = ("touchdown speed", dict(ok)["touchdown speed"])
        if {"time to apogee", "flight time"} <= labels:
            d = dict(ok)
            if "apogee" in la[:20] or "apogee" in lb[-20:]:
                best = ("time to apogee", d["time to apogee"])
            elif any(x in lb[-25:] + " " + la[:25]
                     for x in ("flight", "total", "down in", "back", "up about",
                               "stays", "hangs", "flies")):
                best = ("flight time", d["flight time"])
        found.add(best[0])
        # map to new string
        if best[0] == "apogee":
            unit_orig = m.group(2)
            if unit_orig.lower() in ('ft','feet','foot'):
                new_str = _fmt_for_apogee(t['apogee_m'], 'ft')
            elif unit_orig.lower() in ('m','meters','metre','metres','meter'):
                new_str = _fmt_for_apogee(t['apogee_m'], 'm')
            elif unit_orig.lower() in ('km','kilometers','kilometer'):
                new_str = f"{round(t['apogee_m']/1000.0)} km"
            else:
                new_str = _fmt_for_apogee(t['apogee_m'], 'm')
            spans.append((i, j, new_str, 'apogee'))
            continue
        if best[0] == "max velocity":
            unit_orig = m.group(2)
            if unit_orig.lower() == 'ft/s':
                new_str = _fmt_for_vel(t['max_velocity_ms'], 'ft/s')
            else:
                new_str = _fmt_for_vel(t['max_velocity_ms'], 'm/s')
            spans.append((i, j, new_str, 'max_velocity'))
            continue
        if best[0] == "touchdown speed":
            unit_orig = m.group(2)
            gh = abs(t.get('ground_hit_ms', 0))
            if unit_orig.lower() == 'ft/s':
                nv = gh * 3.28084
                if nv < 10: new_str = f"{nv:.2f} ft/s"
                elif nv < 100: new_str = f"{round(nv,1)} ft/s"
                else: new_str = f"{round(nv)} ft/s"
            else:
                if gh < 10: new_str = f"{gh:.2f} m/s"
                elif gh < 100: new_str = f"{round(gh,1)} m/s"
                else: new_str = f"{round(gh)} m/s"
            spans.append((i, j, new_str, 'touchdown'))
            continue
        if best[0] == "time to apogee":
            unit_orig = m.group(2)
            if unit_orig.lower() in ('min','minutes','minute'):
                mv = t['time_to_apogee_s']/60.0
                new_str = f"{round(mv)} minutes"
            else:
                new_str = f"{round(t['time_to_apogee_s'])} seconds"
            spans.append((i, j, new_str, 'time_to_apogee'))
            continue
        if best[0] == "flight time":
            unit_orig = m.group(2)
            if unit_orig.lower() in ('min','minutes','minute'):
                mv = t['flight_time_s']/60.0
                if mv >= 2: new_str = f"{round(mv)} minutes"
                else: new_str = f"{round(mv)} minutes"
            else:
                if t['flight_time_s'] >= 120: new_str = f"{round(t['flight_time_s'])} seconds"
                else: new_str = f"{round(t['flight_time_s'])} seconds"
            spans.append((i, j, new_str, 'flight_time'))
            continue
        if best[0] == "max mach":
            tm = t.get('max_mach')
            if tm is None or (isinstance(tm,float) and tm!=tm): 
                continue
            if tm < 1: new_str = f"{round(tm,3)} mach"
            else: new_str = f"{round(tm,2)} mach"
            spans.append((i, j, new_str, 'max_mach'))
            continue
        if best[0] == "max acceleration":
            ma_t = new_targets.get('max_acceleration_ms2') if new_targets else None
            if ma_t is None: ma_t = ma_use
            if ma_t is None: continue
            new_str = f"{round(ma_t)} m/s²"
            spans.append((i, j, new_str, 'max_accel'))
            continue
    # motors
    for mot in motors:
        if mot and re.search(r"\b" + re.escape(mot) + r"\b", p):
            found.add(mot)
            break
    return found, spans
