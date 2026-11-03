"""Validate written sft_v5 reasoning: structure, real numbers only, no false claims."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "sftgen/out/scratch/sft_v5_reasoning"
HEADINGS = ["AIRFRAME:", "PROPULSION:", "STABILITY:", "RECOVERY:", "FLIGHT CHECK:"]
ALWAYS = {1.0, 5.0, 8.0, 9.8, 9.81, 0.3}
NUMBER = re.compile(r"(?<![\w.\-])\d[\d,]*\.?\d*(?![\w])")
BANNED = re.compile(r"\bdesigner|\bbuilder|\bauthor|\bI (ran|simulated|tested|verified|checked)|\btool\b|"
                    r"\bthe facts?\b|\bshould not be called\b|\bno fit (issue|problem)|\bfit issues? (is|are) listed|\bguarantee[sd]?\b|\bproven\b|\$|\bcost|\bprice|\bbudget|\bcheap|\boptimal\b|\bbest\b", re.I)
LINKS = re.compile(r"\b(because|so|therefore|which|since|this keeps|this gives|this puts|as a result)\b", re.I)


def collect(value, out):
    if isinstance(value, bool) or value is None:
        return
    if isinstance(value, (int, float)):
        out.add(abs(float(value)))
    elif isinstance(value, str):
        for raw in re.findall(r"\d+\.?\d*(?:[eE]-?\d+)?", value):
            out.add(float(raw))
    elif isinstance(value, dict):
        for item in value.values():
            collect(item, out)
    elif isinstance(value, list):
        for item in value:
            collect(item, out)


def allowed_numbers(facts):
    base = set()
    collect({k: v for k, v in facts.items() if k != "catalog_id"}, base)
    scaled = base | {x * 2 for x in base}  # radius to diameter
    return scaled | {x * 1000 for x in scaled} | {x / 1000 for x in scaled} | {x * 100 for x in scaled} | ALWAYS


def number_ok(raw, allowed):
    value = float(raw.replace(",", "").rstrip("."))
    if "." not in raw and value <= 12:
        return True
    return any(abs(value - x) <= max(0.01 * x, 0.0051) for x in allowed)


def text_problems(text, facts):
    issues, at = [], -1
    for heading in HEADINGS:
        found = text.find(heading)
        if found <= at:
            issues.append(f"missing or misplaced heading {heading}")
        at = max(found, at)
    words = len(text.split())
    if not 110 <= words <= 350:
        issues.append(f"{words} words; need 110 to 350")
    if BANNED.search(text):
        issues.append(f"banned wording: {BANNED.search(text).group(0)}")
    if len(LINKS.findall(text)) < 4:
        issues.append("needs at least 4 cause-and-effect links such as because or so")
    if "reference flight" not in text.lower():
        issues.append("must say reference flight")
    if facts["fit_issues"] and "fit" not in text.lower():
        issues.append("must state the fit issue")
    if not isinstance(facts["thrust_to_weight"], (int, float)) and re.search(r"thrust-to-weight (?:is |of |ratio of )?(?:about )?\d", text):
        issues.append("thrust-to-weight is unknown for this rocket")
    allowed = allowed_numbers(facts)
    for raw in NUMBER.findall(text):
        if not number_ok(raw, allowed):
            issues.append(f"number {raw} is not in the facts")
    return issues


def load_facts():
    facts = {}
    for path in sorted((OUT / "shards").glob("shard_*.jsonl")):
        for line in path.open():
            item = json.loads(line)
            item["_shard"] = path.stem.split("_")[1]
            facts[item["catalog_id"]] = item
    return facts


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    facts, problems, seen = load_facts(), [], {}
    for path in sorted((OUT / "written").glob("shard_*.jsonl")):
        shard = path.stem.split("_")[1]
        if only and shard != only:
            continue
        for number, line in enumerate(path.open(), 1):
            where = f"{path.name}:{number}"
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                problems.append(f"{where}: bad JSON")
                continue
            cid = item.get("catalog_id")
            if set(item) != {"catalog_id", "reasoning"} or cid not in facts:
                problems.append(f"{where}: bad keys or unknown rocket {cid}")
                continue
            if cid in seen:
                problems.append(f"{where}: duplicate rocket {cid}")
            seen[cid] = item["reasoning"]
            facts_item = {k: v for k, v in facts[cid].items() if k != "_shard"}
            problems += [f"{where}: {cid}: {x}" for x in text_problems(item["reasoning"], facts_item)]
    want = [c for c, f in facts.items() if not only or f["_shard"] == only]
    missing = [c for c in want if c not in seen]
    print(f"rockets {len(want)}  problems {len(problems)}  rockets missing reasoning {len(missing)}")
    for line in problems[:50]:
        print(line[:240])
    sys.exit(1 if problems or missing else 0)


if __name__ == "__main__":
    main()
