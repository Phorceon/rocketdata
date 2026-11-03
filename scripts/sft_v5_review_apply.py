"""Apply reviewed text fixes to sft_v5 reasoning, keeping general fin physics on simple rockets."""
import collections
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "sftgen/out/scratch/sft_v5_reasoning"
FIN_CLAIM = re.compile(r"\btail\b|far aft|behind the center|toward the rear|far back", re.I)
NEAR_LIMIT = re.compile(r"near the limit|close to the limit|close to the 8|at the limit|firm|narrow|tight", re.I)


def main():
    facts = {}
    for path in (BASE / "shards").glob("shard_*.jsonl"):
        for line in path.open():
            item = json.loads(line)
            facts[item["catalog_id"]] = item
    fixes = collections.defaultdict(list)
    for path in sorted((BASE / "review").glob("part_*.jsonl")):
        for line in path.open():
            fix = json.loads(line)
            fixes[fix["catalog_id"]].append(fix)
    stats = collections.Counter()
    for path in sorted((BASE / "written").glob("shard_*.jsonl")):
        out = []
        for line in path.open():
            item = json.loads(line)
            cid, text = item["catalog_id"], item["reasoning"]
            fact = facts[cid]
            simple = fact["stages"] in (1, None) and len(fact["fins"]) <= 1
            for fix in fixes[cid]:
                if simple and FIN_CLAIM.search(fix["old"]) and not re.search(r"\d+ ?m\b(?!/)", fix["new"] or "") \
                        and not re.search(r"200|deploy|opens", fix["old"]):
                    stats["kept general fin physics"] += 1
                    continue
                if text.count(fix["old"]) != 1:
                    stats["no longer matches"] += 1
                    continue
                new = re.sub(r"\b(fins?|set|sets)\b([^.]*?)\b(are|is) listed\b", r"\1\2\3 fitted", fix["new"])
                text = text.replace(fix["old"], new)
                stats["applied"] += 1
            land = fact["reference_flight"]["ground_hit_ms"]
            head, sep, tail = text.partition("FLIGHT CHECK:")
            if land >= 7 and not NEAR_LIMIT.search(text):
                head = head.rstrip() + " This is close to the 8 m/s limit.\n\n"
                text = head + sep + tail
                stats["near-limit sentence restored"] += 1
            item["reasoning"] = re.sub(r"  +", " ", re.sub(r" +\n", "\n", text))
            out.append(item)
        with path.open("w") as f:
            for item in out:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(dict(stats))


if __name__ == "__main__":
    main()
