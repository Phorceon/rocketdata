"""Apply fresh flights to sft_v5 sources: drop 20 rockets, update 85 rockets' numbers and text."""
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRATCH = ROOT / "sftgen/out/scratch"
FACTS = SCRATCH / "sft_v5_reasoning"
PROMPTS = SCRATCH / "sft_v5_prompts"
MAIN = ROOT / "new_results/sft_v5.jsonl"
LIMIT_MS = 8.0
NUMBER = re.compile(
    r"(\d[\d,]*\.?\d*)\s*(meters|metres|meter|feet|foot|ft|km|m/s|mm|cm|inches|inch|in|"
    r"kg|grams|g|seconds|secs|sec|minutes|min|mph|s|m)\b", re.I)
TO_M = {"m": 1.0, "meter": 1.0, "meters": 1.0, "metres": 1.0, "ft": 0.3048, "feet": 0.3048,
        "foot": 0.3048, "km": 1000.0}
TARGET_KEYS = ("apogee_m", "ground_hit_ms", "flight_time_s", "time_to_apogee_s", "max_velocity_ms",
               "max_mach", "wind_ms")


def sig(value, digits=4):
    return float(f"{value:.{digits}g}")


def read_jsonl(path):
    return [json.loads(line) for line in path.open() if line.strip()]


def write_jsonl(path, items):
    with path.open("w") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def decimals(raw):
    raw = raw.rstrip(".")
    return len(raw.split(".")[1]) if "." in raw else 0


def fmt(value, raw):
    text = f"{value:.{decimals(raw)}f}"
    if "," in raw:
        whole, _, frac = text.partition(".")
        text = f"{int(whole):,}" + (f".{frac}" if frac else "")
    return text


def step_of(raw):
    """Rounding step of a stated number: its last decimal, or its trailing zeros."""
    raw = raw.replace(",", "").rstrip(".")
    if "." in raw:
        return 10.0 ** -decimals(raw)
    return 10.0 ** (len(raw) - len(raw.rstrip("0"))) if raw.rstrip("0") else 1.0


def wind_context(prompt, match):
    return re.search(r"wind|breeze|gust", prompt[max(0, match.start() - 22):match.end() + 16].lower())


def refresh_prompt(prompt, style, new):
    """Restate a number only where the new flight makes it false (always for the original style)."""
    land, flight, apogee, wind = new["ground_hit_ms"], new["flight_time_s"], new["apogee_m"], new.get("wind_ms")

    def fix(match):
        raw, unit_raw = match.group(1), match.group(2)
        unit, value = unit_raw.lower(), float(raw.replace(",", "").rstrip("."))
        step = step_of(raw)
        always = style == "original"
        if unit in TO_M:
            scale = TO_M[unit]
            if not always and abs(value * scale - apogee) <= 0.05 * apogee:
                return match.group(0)
            while step > 10.0 ** -decimals(raw) and abs(round(apogee / scale / step) * step * scale - apogee) > 0.04 * apogee:
                step /= 10
            return f"{fmt(round(apogee / scale / step) * step, raw)} {unit_raw}"
        if unit == "m/s" and wind is not None and abs(value - wind) <= 0.5 and wind_context(prompt, match):
            return match.group(0)
        if unit == "m/s":
            if land <= value <= min(land * 1.15 + 0.1, LIMIT_MS):
                return match.group(0)
            limit = max(math.ceil(land / step - 1e-9) * step, 0.1)
            if limit > land * 1.15 + 0.1:
                step = 0.1
                limit = math.ceil(land / step - 1e-9) * step
                return f"{limit:.1f} m/s"
            return f"{fmt(limit, raw)} m/s"
        if unit in {"s", "sec", "secs", "seconds", "min", "minutes"}:
            scale = 60.0 if unit in {"min", "minutes"} else 1.0
            if flight <= value * scale <= flight * 1.15 + 1:
                return match.group(0)
            limit = math.ceil(flight / scale / step - 1e-9) * step
            if limit * scale > flight * 1.15 + 1:
                step, raw_use = 0.1, "0.0"
                limit = math.ceil(flight / scale / step - 1e-9) * step
                return f"{fmt(limit, raw_use)} {unit_raw}"
            return f"{fmt(limit, raw)} {unit_raw}"
        return match.group(0)
    return NUMBER.sub(fix, prompt)


def replace_flight_numbers(text, old, new):
    """Swap each old flight number for the new one, matching on number plus unit."""
    groups = [(r"m(?![/\w])", ["apogee_m"]),
              (r"m/s", ["ground_hit_ms", "margin_to_8ms_limit_ms", "mean_sink_rate_ms", "max_velocity_ms", "wind_ms"]),
              (r"(?:s|sec|seconds)\b", ["flight_time_s", "time_to_apogee_s", "descent_time_s"])]
    count = 0

    def swap(raw, keys):
        nonlocal count
        value = float(raw.replace(",", ""))
        tolerance = 0.6 * 10.0 ** -decimals(raw)
        for key in keys:
            if key in old and key in new and abs(value - old[key]) <= tolerance:
                count += 1
                return fmt(new[key], raw)
        return raw
    for unit, keys in groups:
        text = re.sub(rf"(?<![\w.,])(\d[\d,]*\.\d+|\d{{2,}}[\d,]*)(\s*){unit}",
                      lambda m, keys=keys: swap(m.group(1), keys) + m.group(0)[len(m.group(1)):], text)
    text = re.sub(r"(Mach\s+)(\d+\.\d+)", lambda m: m.group(1) + swap(m.group(2), ["max_mach"]), text)
    return text, count


WIDE = re.compile(r"\b(wide|comfortabl\w*|clear margin|ample|plenty|gentle|gently|soft|softly)\b", re.I)
TIGHT = re.compile(r"\b(near the limit|close to the limit|at the limit|firm|not gentle|not wide|narrow|tight|"
                   r"essentially|close to the 8)\b", re.I)


def fix_landing_words(text, landing):
    """Remove landing descriptions that the new speed makes false."""
    head, _, rest = text.partition("RECOVERY:")
    recovery, _, tail = rest.partition("FLIGHT CHECK:")

    def clean(part):
        kept = []
        for sentence in re.split(r"(?<=[.])\s+", part.strip()):
            negated = re.search(r"\bnot\b|n't", sentence)
            if landing >= 7 and WIDE.search(sentence) and not negated and "m/s" not in sentence:
                continue
            if landing < 6.5 and TIGHT.search(sentence) and "m/s" not in sentence:
                continue
            if landing < 6.5 and TIGHT.search(sentence):
                sentence = re.sub(r",? (so|and) (the landing is |it is |this is )?[^,.]*\b(near|close to|at) the limit[^.]*", "", sentence)
                sentence = re.sub(r",? so the landing is firm, not gentle", "", sentence)
            if landing >= 7 and WIDE.search(sentence) and not negated:
                sentence = re.sub(r",? (a|with a|which is a) (wide|comfortable|clear|ample) [^.]*", "", sentence)
            kept.append(sentence)
        return " ".join(kept)
    recovery_new = clean(recovery)
    if landing >= 7 and not TIGHT.search(recovery_new):
        recovery_new += " This is close to the 8 m/s limit."
    return f"{head}RECOVERY:\n{recovery_new}\n\nFLIGHT CHECK:\n{clean(tail)}"


def main():
    flights = {r["catalog_id"]: r for r in read_jsonl(SCRATCH / "sft_v5_roundtrip/refresh_flights.jsonl")}
    fresh, removed = {}, {}
    for cid, flown in flights.items():
        land = flown.get("ground_hit_ms")
        if not flown.get("ground_hit_event") or not isinstance(land, float) or not math.isfinite(land):
            removed[cid] = "no thrust curve for the motor, so it cannot leave the ground"
        elif land > LIMIT_MS:
            removed[cid] = f"lands at {land:.2f} m/s in current OpenRocket, above the 8 m/s limit"
        else:
            fresh[cid] = flown
    assert len(fresh) == 85 and len(removed) == 20

    new_targets = {cid: {k: f[k] for k in TARGET_KEYS if isinstance(f.get(k), float) and math.isfinite(f[k])}
                   for cid, f in fresh.items()}
    swapped = 0
    for shard in sorted((FACTS / "shards").glob("shard_*.jsonl")):
        facts = {}
        kept = []
        for item in read_jsonl(shard):
            cid = item["catalog_id"]
            if cid in removed:
                continue
            if cid in fresh:
                t = new_targets[cid]
                old = dict(item["reference_flight"], **item["derived"])
                item["reference_flight"] = {k: sig(t[k]) for k in item["reference_flight"] if k in t}
                item["derived"]["margin_to_8ms_limit_ms"] = sig(LIMIT_MS - t["ground_hit_ms"])
                if "descent_time_s" in item["derived"] and "time_to_apogee_s" in t:
                    descent = t["flight_time_s"] - t["time_to_apogee_s"]
                    item["derived"]["descent_time_s"] = sig(descent, 3)
                    item["derived"]["mean_sink_rate_ms"] = sig(t["apogee_m"] / descent, 3)
                facts[cid] = (old, dict(item["reference_flight"], **item["derived"]))
            kept.append(item)
        write_jsonl(shard, kept)
        path = FACTS / "written" / shard.name
        out = []
        for item in read_jsonl(path):
            cid = item["catalog_id"]
            if cid in removed:
                continue
            if cid in facts:
                text, n = replace_flight_numbers(item["reasoning"], *facts[cid])
                swapped += n
                item["reasoning"] = fix_landing_words(text, new_targets[cid]["ground_hit_ms"])
            out.append(item)
        write_jsonl(path, out)

    def apply_prompts():
        for shard in sorted((PROMPTS / "shards").glob("shard_*.jsonl")):
            kept = []
            for item in read_jsonl(shard):
                cid = item["catalog_id"]
                if cid in removed:
                    continue
                if cid in fresh:
                    t = new_targets[cid]
                    item["original_prompt"] = refresh_prompt(item["original_prompt"], "original", t)
                    item["apogee_m"] = round(t["apogee_m"], 1)
                    item["touchdown_ms"] = round(t["ground_hit_ms"], 2)
                    item["flight_time_s"] = round(t["flight_time_s"], 1)
                    if "wind_ms" in item and "wind_ms" in t:
                        item["wind_ms"] = round(t["wind_ms"], 1)
                kept.append(item)
            write_jsonl(shard, kept)
        for path in sorted((PROMPTS / "written").glob("shard_*.jsonl")):
            out = []
            for item in read_jsonl(path):
                cid = item["catalog_id"]
                if cid in removed:
                    continue
                if cid in fresh:
                    item["prompt"] = refresh_prompt(item["prompt"], item["style"], new_targets[cid])
                out.append(item)
            write_jsonl(path, out)
    apply_prompts()

    rows = []
    for row in read_jsonl(MAIN):
        cid = row["catalog_id"]
        if cid in removed:
            continue
        if cid in fresh:
            t = new_targets[cid]
            row["targets"] = t
            prov = row["metric_provenance"]
            row["metric_provenance"] = {
                "source": "new_openrocket_simulation", "sim": prov.get("sim"), "sim_index": 0,
                "sim_status": "uptodate", "configid": prov.get("configid"),
                "config_motors_populated": True, "no_flight_rerun": False, "seed": 42,
                "replaced_saved_metrics": prov.get("notes"),
                "notes": "fresh headless OpenRocket 24.12 flight of the design rebuilt from this row's JSON; "
                         "replaces the saved flight metrics from the source file",
            }
            row["simulation_status"] = "uptodate"
            row["flags"] = [f for f in row["flags"] if isinstance(f, dict) or f not in
                            {"saved_flight_not_rerun", "saved_simulation_not_uptodate"}] + ["new_flight_simulation"]
            style = row["prompt_style"]
            if style == "original":
                prompt = refresh_prompt(row["messages"][1]["content"], "original", t)
            else:
                prompt = next(p["prompt"] for shard in (PROMPTS / "written").glob("shard_*.jsonl")
                              for p in read_jsonl(shard) if p["catalog_id"] == cid and p["style"] == style)
            row["messages"][1]["content"] = prompt
            row["prompt_text"] = prompt
        rows.append(row)
    write_jsonl(MAIN, rows)
    write_jsonl(SCRATCH / "sft_v5_roundtrip/removed.jsonl",
                [{"catalog_id": c, "reason": r} for c, r in sorted(removed.items())])
    print("rows", len(rows), "rockets", len({r["catalog_id"] for r in rows}), "numbers swapped", swapped)


if __name__ == "__main__":
    main()
