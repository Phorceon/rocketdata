"""Build one fact sheet per sft_v5 rocket, for writing short engineering reasoning."""
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "sftgen/out/scratch/sft_v5_reasoning"
SHARDS = 4
G = 9.80665
PART_KEYS = ("length", "wall", "radius", "shape ", "fin count", "root chord", "tip chord", "height",
             "sweep", "thickness", "fore radius", "aft radius", "cant", "outer radius", "inner radius",
             "override mass", "mass")
RECOVERY_KEYS = ("diameter", "cd", "deploy event", "deploy altitude", "deploy delay", "strip length",
                 "strip width", "cord length", "override mass")
MOTOR_KEYS = ("manufacturer", "designation", "diameter", "length", "total impulse", "burn time",
              "average thrust", "ejection delay", "instance count")


def sig(value, digits=4):
    return float(f"{value:.{digits}g}")


def tidy(text):
    return re.sub(r"\d+\.\d{5,}(?:[eE]-?\d+)?", lambda m: str(sig(float(m.group(0)))), text)


def section(text, name):
    m = re.search(rf"^{name}[^\n]*:\n(.*?)(?=\n\n[A-Z][A-Z /&-]{{3,}}(?: \(|:)|\n</thought>|\Z)",
                  text, re.M | re.S)
    return m.group(1) if m else ""


def keep(line, keys):
    name, _, rest = line.strip(" -").partition(":")
    parts = [p for p in rest.split(", ") if p.strip().startswith(keys)]
    return tidy(f"{name.strip()}: " + ", ".join(p.strip() for p in parts)) if parts else None


def find(pattern, text):
    m = re.search(pattern, text)
    return float(m.group(1)) if m else None


def design_nodes(node, names):
    """Yield (tag, {child tag: value}) for every named component in the design tree."""
    if isinstance(node, list):
        for item in node:
            yield from design_nodes(item, names)
    elif isinstance(node, dict):
        for key, value in node.items():
            if key in names and isinstance(value, dict):
                flat = {}
                for child in value.get("children", []):
                    for tag, inner in child.items():
                        if isinstance(inner, dict) and "value" in inner:
                            flat[tag] = inner["value"]
                yield key, flat
            yield from design_nodes(value, names)


def number(value):
    return sig(value) if isinstance(value, float) else value


def fin_sets(design):
    keys = {"fincount": "fin count", "rootchord": "root chord m", "tipchord": "tip chord m",
            "height": "span m", "sweeplength": "sweep m", "thickness": "thickness m", "material": "material"}
    found = []
    for tag, flat in design_nodes(design, {"trapezoidfinset", "ellipticalfinset", "freeformfinset"}):
        item = {label: number(flat[k]) for k, label in keys.items() if k in flat}
        text = tag.replace("finset", " fin set: ") + ", ".join(f"{k} {v}" for k, v in item.items())
        if text not in found:
            found.append(text)
    return found


def design_motors(design):
    found = []
    for _tag, flat in design_nodes(design, {"motor"}):
        text = "motor: " + ", ".join(f"{k} {number(flat[k])}" for k in
                                     ("manufacturer", "designation", "diameter", "length", "delay") if k in flat)
        if text not in found:
            found.append(text)
    return found


def facts_for(row):
    design = json.loads(re.search(r"<design>(.*)</design>", row["messages"][-1]["content"], re.S).group(1))
    text = row["messages"][-1]["content"].split("<design>")[0]
    t = row["targets"]
    prop, bal, rec = section(text, "PROPULSION"), section(text, "BALANCE"), section(text, "RECOVERY")
    air = section(text, "AIRFRAME") or section(text, "AIRFRAME AND GEOMETRY")
    mass = find(r"liftoff mass ([\d.Ee-]+) kg", bal)
    cg = find(r"center of gravity ([\d.Ee-]+) m", bal)
    cp = find(r"center of pressure ([\d.Ee-]+) m", bal)
    dia = find(r"reference diameter ([\d.Ee-]+) m", bal)
    margin = find(r"= ([\d.Ee-]+) calibers", bal)
    twr = find(r"thrust-to-weight at liftoff ([\d.]+)", prop)
    motors, seen = [], set()
    for line in prop.splitlines():
        if line.startswith("- motor"):
            item = keep("motor: " + line.split(", ", 1)[-1], MOTOR_KEYS)
            if item and item not in seen:
                seen.add(item)
                motors.append(item)
    parts = []
    for line in air.splitlines():
        if ":" in line and "placement" not in line:
            item = keep(line, PART_KEYS)
            if item and item not in parts:
                parts.append(item)
    recovery = []
    for line in rec.splitlines():
        if re.match(r"\s*- (parachute|streamer)", line):
            item = keep(line, RECOVERY_KEYS)
            if item and "deploy event altitude" not in item:
                item = re.sub(r"deploy altitude [\d.]+ m(, )?", "", item)
            if item and item not in recovery:
                recovery.append(item)
    motors = motors or design_motors(design)
    summary = [line.strip(" -") for line in air.splitlines()] if not parts else None
    fit_lines = [tidy(line.strip(" -")) for line in section(text, "HOW THE PARTS FIT").splitlines()
                 if line.strip(" -").startswith("motor") and "fits" in line][:2]
    fit = [d for x in row["flags"] if isinstance(x, dict) and x.get("flag") == "fit_issue"
           for d in x["details"]]
    combined = find(r"combined total impulse ([\d.Ee-]+)", prop)
    single = re.findall(r"total impulse ([\d.Ee-]+) N", prop)
    impulse = combined or (float(single[0]) if single else None)
    flight = {k: sig(v) for k, v in t.items() if isinstance(v, (int, float))}
    derived = {"weight_N": sig(mass * G), "margin_to_8ms_limit_ms": sig(8 - t["ground_hit_ms"]),
               "cp_behind_cg_mm": sig((cp - cg) * 1000),
               "frontal_area_cm2": sig(math.pi * (dia / 2) ** 2 * 1e4)}
    if impulse:
        derived["impulse_N_s"] = sig(impulse)
        derived["impulse_per_kg_N_s_per_kg"] = sig(impulse / mass)
    sink = find(r"mean sink rate about ([\d.]+) m/s", rec)
    descent = find(r"descent time estimate ([\d.]+) s", rec)
    if sink:
        derived["mean_sink_rate_ms"], derived["descent_time_s"] = sink, descent
    rod = find(r"launch rod length ([\d.]+) m", text)
    return {
        "catalog_id": row["catalog_id"],
        "stages": len(re.findall(r"^\s*- stage\.", air, re.M)) or None,
        "airframe_parts": parts[:22],
        "airframe_summary": summary,
        "fins": fin_sets(design)[:6],
        "motors": motors[:6],
        "motor_mount_checks": fit_lines,
        "liftoff_mass_kg": sig(mass),
        "thrust_to_weight": twr if twr is not None else "unknown: do not state a value",
        "cg_m": sig(cg), "cp_m": sig(cp), "diameter_m": sig(dia), "static_margin_cal": sig(margin),
        "recovery": recovery[:6],
        "launch_rod_length_m": rod,
        "reference_flight": flight,
        "derived": derived,
        "fit_issues": [tidy(d) for d in fit],
    }


def main():
    rows = [json.loads(line) for line in (ROOT / "new_results/sft_v5.jsonl").open()]
    seen, facts = set(), []
    for row in rows:
        if row["catalog_id"] not in seen:
            seen.add(row["catalog_id"])
            facts.append(facts_for(row))
    for i in range(SHARDS):
        with (OUT / "shards" / f"shard_{i}.jsonl").open("w") as f:
            for item in facts[i::SHARDS]:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(len(facts), [len(facts[i::SHARDS]) for i in range(SHARDS)])
    print("no parts", sum(not x["airframe_parts"] for x in facts), "no motors", sum(not x["motors"] for x in facts),
          "no recovery", sum(not x["recovery"] for x in facts), "no fins", sum(not x["fins"] for x in facts), "twr known",
          sum(isinstance(x["thrust_to_weight"], float) for x in facts), "fit", sum(bool(x["fit_issues"]) for x in facts))
    print(json.dumps({k: facts[0][k] for k in ("fins", "motors", "motor_mount_checks")}, indent=0))


if __name__ == "__main__":
    main()
