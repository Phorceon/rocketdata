"""Generate data/sft_train.jsonl from the teammate prompt set.

One line per prompt label in prompts/ALL_UNIQUE_LE3_PARAMS.md (exactly as written,
no edits).  Each line is a chat sample in the plan's Section 3 "messages" format
plus a "metadata" object.  The assistant reply is a <thought> block (physics
reasoning grounded in the matched .ork + its stored simulation metrics) followed
by a <design> block (the IR JSON).

Run:  python3 scripts/generate_sft_labels.py
"""

import json
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from extract_ork import extract, pick_metrics, load_xml_bytes  # noqa: E402

PROMPTS_FILE = os.path.join(REPO, "prompts", "ALL_UNIQUE_LE3_PARAMS.md")
ORK_DIR = os.path.join(REPO, "ork")
OUT_FILE = os.path.join(REPO, "data", "sft_train.jsonl")

SYSTEM_MESSAGE = (
    "You are an autonomous aerospace design engineer. When given flight "
    "requirements, you must first calculate the required propulsion, stability, "
    "and descent parameters, then output the final verified hardware blueprint "
    "in JSON format inside <design> tags."
)

# Files that contain prompts, with their git author (used for metadata.prompt_author)
PROMPT_SOURCE_FILES = {
    os.path.join(REPO, "prompts", "ALL_UNIQUE_LE3_PARAMS.md"): "nitikapadala13-sys",
    os.path.join(REPO, "prompts", "ALL_PROMPTS_SINGULAR.md"): "nitikapadala13-sys",
    os.path.join(REPO, "prompts", "ALL_UNIQUE_PROMPTS.md"): "nitikapadala13-sys",
    os.path.join(REPO, "prompts", "ALL_UNIQUE_BY_ROCKET_TYPE.md"): "nitikapadala13-sys",
    os.path.join(REPO, "prompts", "more_ork_prompts_3style.md"): "nitikapadala13-sys",
    os.path.join(REPO, "rocket_prompts.md"): "Shamik123456",
    os.path.join(REPO, "rocket_prompts_more.md"): "Shamik123456",
}


# --------------------------------------------------------------------------
# parsing
# --------------------------------------------------------------------------

def parse_le3(path):
    txt = open(path, encoding="utf-8").read()
    entries = []
    for block in re.split(r"\n(?=- \*\*\[)", txt):
        m = re.match(r"- \*\*\[(U-\d+)\]\*\*\s*\(([^)]*)\)\s*\n\s*>\s*(.+)", block)
        if not m:
            continue
        label, params, prompt = m.group(1), m.group(2), m.group(3).strip()
        npar = re.match(r"(\d+) params", params)
        src = re.search(r"File: `([^`]+\.ork)`", block)
        sname = re.search(r"Sim: `([^`]*)`", block)
        rname = re.search(r"Rocket: `([^`]*)`", block)
        entries.append({
            "label": label,
            "prompt": prompt,
            "params": params,
            "nparams": int(npar.group(1)) if npar else 0,
            "params_list": [p.strip() for p in params.split("params:", 1)[-1].split(",") if p.strip()],
            "rocket_name": rname.group(1) if rname else None,
            "source_ref": src.group(1) if src else None,
            "sim_name": sname.group(1) if sname else None,
        })
    return entries


# --------------------------------------------------------------------------
# .ork resolution
# --------------------------------------------------------------------------

class OrkIndex:
    def __init__(self, ork_dir):
        self.dir = ork_dir
        self.files = sorted(f for f in os.listdir(ork_dir) if f.lower().endswith(".ork"))
        self._data = {}
        self._by_name = defaultdict(list)
        for fn in self.files:
            name = self.get(fn)["rocket_name"]
            if name:
                self._by_name[name].append(fn)

    def get(self, fn):
        if fn not in self._data:
            self._data[fn] = extract(os.path.join(self.dir, fn))
        return self._data[fn]

    def candidates(self, ref):
        """Repo filenames that could correspond to a prompt's File pointer."""
        cands = []
        if ref in self.files:
            cands.append(ref)
        base = ref[:-4] if ref.lower().endswith(".ork") else ref
        parts = base.split("__")
        names = []
        if len(parts) > 1:
            names.append(parts[-1] + ".ork")
        names.append(base + ".ork")
        if len(parts) > 1:
            names.append(parts[-2] + ".ork")
        for n in names:
            if n in self.files:
                cands.append(n)
        # separator variants (: vs .)
        for n in names:
            for fn in self.files:
                if fn not in cands and (fn.replace(":", ".") == n or fn.replace(".", ":") == n):
                    cands.append(fn)
        # by internal rocket name (prefer a filename matching the name)
        seen = set(cands)
        return list(dict.fromkeys(cands)), seen

    def by_rocket_name(self, rocket_name):
        return list(self._by_name.get(rocket_name, []))

    def resolve(self, ref, rocket_name):
        if not ref:
            return None
        cands, _ = self.candidates(ref)
        if cands:
            return cands[0]
        files = self.by_rocket_name(rocket_name) if rocket_name else []
        if len(files) == 1:
            return files[0]
        if len(files) > 1:
            # prefer a file whose stem equals the rocket name
            for fn in files:
                if os.path.splitext(fn)[0] == rocket_name:
                    return fn
            return sorted(files)[0]
        return None


# --------------------------------------------------------------------------
# stability margin (best effort, from stored datapoints)
# --------------------------------------------------------------------------

def stability_margin(xml_bytes):
    x = xml_bytes.decode("utf-8", "replace")
    types_m = re.search(r'<databranch[^>]*types="([^"]*)"', x)
    if not types_m:
        return None
    types = [t.strip() for t in types_m.group(1).split(",")]
    if "Stability margin calibers" not in types:
        return None
    col = types.index("Stability margin calibers")
    for dp in re.finditer(r"<datapoint>([^<]*)</datapoint>", x):
        vals = dp.group(1).split(",")
        if col < len(vals):
            v = vals[col]
            if v not in ("NaN", "", "nan"):
                try:
                    return round(float(v), 3)
                except ValueError:
                    continue
    return None


# --------------------------------------------------------------------------
# notes / difficulty
# --------------------------------------------------------------------------

UNSAFE_RE = re.compile(
    r"(?:ground-hit|touchdown|touches down|lands?|landing)[^.]*?"
    r"(?:under|about|at|below|~|max(?:imum)?|<=?)\s*~?([\d\.]+)\s*m/s",
    re.I,
)


def unsafe_touchdown(prompt):
    for m in UNSAFE_RE.finditer(prompt):
        try:
            if float(m.group(1)) > 6.0:
                return float(m.group(1))
        except ValueError:
            pass
    return None


def infer_class_from_text(prompt):
    m = re.search(r"\b(?:on a|on an|use motors?|motor class|class of)\s+([0-9/]*[A-O]\d+)", prompt, re.I)
    return m.group(1) if m else None


def compute_features(data, prompt, nparams):
    p = prompt.lower()
    motor_classes = set(m.get("impulse_class") for m in (data or {}).get("motors", []) if m.get("impulse_class"))
    feats = {
        "stages": (data or {}).get("stage_count") if data else None,
        "cluster": (data or {}).get("cluster") if data else None,
        "pods": (data or {}).get("pods") if data else None,
        "freeform_fins": any(f.get("kind") == "freeformfinset" for f in (data or {}).get("finsets", [])),
        "n_finsets": len((data or {}).get("finsets", [])),
        "has_transition": bool((data or {}).get("transitions")),
        "n_recovery": len((data or {}).get("recovery", [])),
        "ballast_kg": (data or {}).get("ballast_mass_kg", 0.0) or 0.0,
        "motor_classes": sorted(motor_classes),
        "prompt_stage_text": bool(re.search(r"\b\d+-stage\b", p)),
        "prompt_cluster_text": "cluster" in p,
        "prompt_payload_text": ("egg" in p or "payload" in p),
        "prompt_motor_text": infer_class_from_text(prompt),
    }
    return feats


def difficulty_of(feats, nparams, notes):
    stages = feats["stages"] or 1
    multistage = stages > 1 or feats["prompt_stage_text"]
    cluster = bool(feats["cluster"]) or feats["prompt_cluster_text"]
    pods = bool(feats["pods"])

    med = 0
    if feats["has_transition"]:
        med += 1
    if feats["prompt_payload_text"]:
        med += 1
    if feats["freeform_fins"]:
        med += 1
    if (feats["ballast_kg"] or 0) > 0:
        med += 1
    if feats["n_recovery"] >= 2:
        med += 1
    if set(feats["motor_classes"]) & {"E", "F", "G"}:
        med += 1

    if multistage or cluster or pods or med >= 3:
        return "hard"
    if med >= 1:
        return "medium"
    return "easy"


def difficulty_reason(diff, feats, nparams):
    bits = []
    if feats["stages"] and feats["stages"] > 1:
        bits.append("%d-stage" % feats["stages"])
    if feats["prompt_stage_text"]:
        bits.append("prompt states multi-stage")
    if feats["cluster"]:
        bits.append("cluster motors")
    if feats["pods"]:
        bits.append("pods")
    if feats["has_transition"]:
        bits.append("transition/boattail")
    if feats["prompt_payload_text"]:
        bits.append("payload")
    if feats["freeform_fins"]:
        bits.append("freeform fins")
    if feats["ballast_kg"]:
        bits.append("ballast for stability")
    if feats["n_recovery"] >= 2:
        bits.append("dual deploy")
    if set(feats["motor_classes"]) & {"E", "F", "G", "H", "I", "J", "K"}:
        bits.append("%s-class motor" % "/".join(sorted(set(feats["motor_classes"]) & set("EFGHIJKLMNOP"))))
    if not bits:
        bits.append("single stage, standard fins, one recovery, %d constraint(s)" % nparams)
    return "; ".join(dict.fromkeys(bits))


# --------------------------------------------------------------------------
# author lookup
# --------------------------------------------------------------------------

def build_author_lookup():
    texts = {}
    for path, author in PROMPT_SOURCE_FILES.items():
        if os.path.exists(path):
            try:
                texts[path] = (open(path, encoding="utf-8", errors="replace").read(), author)
            except OSError:
                pass
    def lookup(prompt):
        for path, (txt, author) in texts.items():
            if prompt in txt:
                return author, os.path.relpath(path, REPO)
        return "nitikapadala13-sys", "prompts/ALL_UNIQUE_LE3_PARAMS.md"
    return lookup


# --------------------------------------------------------------------------
# label building
# --------------------------------------------------------------------------

def r(v, n=4):
    return None if v is None else round(float(v), n)


def build_design(data, sim_configid):
    if not data:
        return None
    nose = data["nose_cones"][0]["name"] if data["nose_cones"] else None
    tube_ids = [b["name"] for b in data["body_tubes"]]
    # motor for the simulated config if known, else first motor
    motor = None
    for m in data["motors"]:
        if sim_configid and m.get("configid") == sim_configid:
            motor = m
            break
    if motor is None and data["motors"]:
        motor = data["motors"][0]
    fins = data["finsets"][0] if data["finsets"] else {}
    recovery = data["recovery"][0]["name"] if data["recovery"] else None
    od = data["body_tubes"][0]["od_m"] if data["body_tubes"] else None

    design = {
        "nose_cone_id": nose,
        "body_tube_ids": tube_ids,
        "motor_id": motor["designation"] if motor else None,
        "fin_root_chord_m": r(fins.get("root_chord_m")),
        "fin_tip_chord_m": r(fins.get("tip_chord_m")),
        "fin_span_m": r(fins.get("span_m")),
        "fin_sweep_m": r(fins.get("sweep_m")),
        "fin_position_from_tail_m": r(fins.get("position_from_tail_m")),
        "recovery_id": recovery,
        "ballast_mass_kg": r(data.get("ballast_mass_kg", 0.0)),
        # extra fields
        "stages": data["stage_count"],
        "fin_count": fins.get("fincount"),
        "motor_manufacturer": motor["manufacturer"] if motor else None,
        "motor_class": motor["impulse_class"] if motor else None,
        "body_tube_od_m": r(od),
        "num_body_tubes": len(tube_ids),
    }
    if data["cluster"]:
        design["cluster"] = True
    if data["pods"]:
        design["pods"] = data["pods"]
    if data["transitions"]:
        design["transitions"] = [t["name"] for t in data["transitions"]]
    if len(data["finsets"]) > 1:
        design["num_fin_sets"] = len(data["finsets"])
    return design


def build_thought(data, metrics, sim_name, sim_configid, prompt):
    lines = []
    if data:
        nose = data["nose_cones"][0] if data["nose_cones"] else None
        tube = data["body_tubes"][0] if data["body_tubes"] else None
        lines.append("1. AIRFRAME SELECTION:")
        if nose:
            od_bit = ", base diameter %.3f m" % nose["od_m"] if nose["od_m"] else ""
            lines.append("- Nose cone: %s, shape %s, length %.3f m%s." % (
                nose["name"], nose["shape"] or "unspecified", nose["length_m"] or 0.0, od_bit))
        if tube:
            lines.append("- Body tube: %s, outer diameter %.3f m, wall %.4f m, total airframe length %.3f m." % (
                tube["name"], tube["od_m"] or 0.0, tube["thickness_m"] or 0.0, data["total_length_m"] or 0.0))
        motor_desc = "uses a motor cluster" if data["cluster"] else "single motor"
        lines.append("- Airframe is %d stage(s), %s, %d pod(s)." % (
            data["stage_count"], motor_desc, data["pods"]))

        motor = None
        for m in data["motors"]:
            if sim_configid and m.get("configid") == sim_configid:
                motor = m
                break
        if motor is None and data["motors"]:
            motor = data["motors"][0]
        lines.append("2. PROPULSION & APOGEE SIZING:")
        if motor:
            lines.append("- Motor: %s %s (impulse class %s), casing diameter %.3f m." % (
                motor["manufacturer"] or "", motor["designation"], motor["impulse_class"] or "?", motor["diameter_m"] or 0.0))
        if metrics:
            lines.append("- Stored OpenRocket simulation \"%s\": apogee %.1f m, time to apogee %.2f s, max velocity %.1f m/s (Mach %.3f), max acceleration %.1f m/s^2." % (
                sim_name or "?", metrics.get("apogee_m") or 0.0, metrics.get("time_to_apogee_s") or 0.0,
                metrics.get("max_velocity_mps") or 0.0, metrics.get("max_mach") or 0.0,
                metrics.get("max_acceleration_mps2") or 0.0))
        else:
            lines.append("- No stored flight simulation is available for this airframe; propulsion is taken from the design file only.")

        lines.append("3. STABILITY MARGIN (CG vs CP):")
        fins = data["finsets"][0] if data["finsets"] else {}
        if fins:
            lines.append("- %d fins, root chord %.3f m, tip chord %.3f m, span %.3f m, sweep %.3f m, thickness %.4f m, mounted %.3f m from the tail." % (
                fins.get("fincount") or 0, fins.get("root_chord_m") or 0.0, fins.get("tip_chord_m") or 0.0,
                fins.get("span_m") or 0.0, fins.get("sweep_m") or 0.0, fins.get("thickness_m") or 0.0,
                fins.get("position_from_tail_m") or 0.0))
        sm = data.get("stability_margin_cal")
        if sm is not None:
            lines.append("- OpenRocket Barrowman calculation gives a static stability margin of %.2f calibers." % sm)
        else:
            lines.append("- Fin sizing is taken directly from the design; the OpenRocket Barrowman model is used for the static margin (no margin value stored in the file).")

        lines.append("4. RECOVERY & DESCENT TIMING:")
        if data["recovery"]:
            for rec in data["recovery"]:
                if rec["kind"] == "parachute":
                    lines.append("- %s: parachute diameter %.3f m, deployment event %s at %.0f m." % (
                        rec["name"], rec["diameter_m"] or 0.0, rec["deployevent"] or "?", rec["deployaltitude_m"] or 0.0))
                else:
                    lines.append("- %s: streamer." % rec["name"])
        if metrics:
            lines.append("- Stored descent: deployment velocity %.1f m/s, ground-hit velocity %.1f m/s, total flight time %.1f s." % (
                metrics.get("deployment_velocity_mps") or 0.0, metrics.get("ground_hit_velocity_mps") or 0.0,
                metrics.get("flight_time_s") or 0.0))
        else:
            lines.append("- No stored descent data.")
    else:
        lines.append("No OpenRocket design file could be matched to this prompt, so no verified hardware blueprint is produced.")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main():
    entries = parse_le3(PROMPTS_FILE)
    idx = OrkIndex(ORK_DIR)
    author_lookup = build_author_lookup()

    # resolve each unique source_ref and count collisions (ambiguity)
    resolved = {}
    for e in entries:
        if e["source_ref"]:
            resolved[e["source_ref"]] = idx.resolve(e["source_ref"], e["rocket_name"])
    refs_per_file = Counter(v for v in resolved.values() if v)
    ambiguous_files = {f for f, n in refs_per_file.items() if n > 1}

    lines_out = []
    stats = Counter()
    note_counts = Counter()
    metrics_src_counts = Counter()
    diff_counts = Counter()
    source_counts = Counter()

    for e in entries:
        notes = []
        data = None
        ork_file = None
        metrics = None
        sim_used = None
        metrics_source = "unsimulated"
        if e["source_ref"]:
            ork_file = resolved.get(e["source_ref"])
        if ork_file:
            data = idx.get(ork_file)
            sim_configid = None
            metrics, sim_used, metrics_source = pick_metrics(data, e["sim_name"])
            if metrics is None:
                metrics_source = "unsimulated"
                notes.append("unsimulated")
            else:
                if e["sim_name"] and sim_used != e["sim_name"]:
                    notes.append("sim_name_not_found")
            # best-effort stability margin
            try:
                raw = load_xml_bytes(os.path.join(ORK_DIR, ork_file))[0]
                data["stability_margin_cal"] = stability_margin(raw)
            except Exception:
                data["stability_margin_cal"] = None
            # sim configid
            for s in data.get("simulations", []):
                if s.get("name") == sim_used:
                    sim_configid = s.get("configid")
                    break
            if ork_file in ambiguous_files:
                notes.append("ambiguous_ork")
        else:
            notes.append("no_ork")

        ut = unsafe_touchdown(e["prompt"])
        if ut is not None:
            notes.append("unsafe_touchdown")

        author, srcfile = author_lookup(e["prompt"])

        feats = compute_features(data, e["prompt"], e["nparams"])
        diff = difficulty_of(feats, e["nparams"], notes)
        reason = difficulty_reason(diff, feats, e["nparams"])

        if data:
            sim_configid = None
            for s in data.get("simulations", []):
                if s.get("name") == sim_used:
                    sim_configid = s.get("configid")
                    break
            thought = build_thought(data, metrics, sim_used, sim_configid, e["prompt"])
            design = build_design(data, sim_configid)
            assistant = "<thought>\n%s\n</thought>\n<design>\n%s\n</design>" % (
                thought, json.dumps(design, ensure_ascii=False))
        else:
            assistant = ""

        sample = {
            "messages": [
                {"role": "system", "content": SYSTEM_MESSAGE},
                {"role": "user", "content": e["prompt"]},
                {"role": "assistant", "content": assistant},
            ],
            "metadata": {
                "label": e["label"],
                "source_ork": ork_file,
                "source_ref": e["source_ref"],
                "prompt_source_file": srcfile,
                "prompt_author": author,
                "metrics": metrics or {},
                "metrics_source": metrics_source,
                "num_params": e["nparams"],
                "difficulty": diff,
                "difficulty_reason": reason,
                "features": feats,
                "notes": notes,
            },
        }
        lines_out.append(sample)
        stats["total"] += 1
        diff_counts[diff] += 1
        metrics_src_counts[metrics_source] += 1
        source_counts[srcfile] += 1
        for n in notes or ["(none)"]:
            note_counts[n] += 1

    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as fh:
        for s in lines_out:
            fh.write(json.dumps(s, ensure_ascii=False) + "\n")

    print("wrote %s" % OUT_FILE)
    print("total:", stats["total"])
    print("difficulty:", dict(diff_counts))
    print("metrics_source:", dict(metrics_src_counts))
    print("notes:", dict(note_counts))
    print("prompt_source_file:", dict(source_counts))


if __name__ == "__main__":
    main()
