"""Sessions -> checked dataset rows (DATA_SPEC section 4 record format).

    python -m sftgen.assemble [--sessions GLOB] [--out sftgen/out/sft_v2.jsonl] [--no-replay]

Every finished session is turned into a row, run through the checker, and either
kept or logged with its drop reasons in sftgen/out/drops.jsonl. Prompts whose
drafts were all dropped are listed in sftgen/out/unsolved.jsonl.
"""

from __future__ import annotations

import argparse
import glob
import json
from collections import Counter, defaultdict
from pathlib import Path

from . import contract
from .session import OUT, SESSIONS, _load_prompts


def session_to_row(s: dict, prompt: dict) -> dict:
    return {
        "id": f"sftv2_{s['session_id']}",
        "group_id": prompt["group_id"],
        "split": prompt["split"],
        "source": "ork",
        "prompt_id": prompt["prompt_id"],
        "prompt_type": prompt["prompt_type"],
        "targets": prompt["targets"],
        "sim_conditions": s["sim_conditions"],
        "tools": contract.TOOLS,
        "messages": s["messages"],
        "verification": None,
        "generator": s["generator"],
    }


def main(argv=None) -> None:
    from .checker import check_row

    ap = argparse.ArgumentParser(prog="sftgen.assemble")
    ap.add_argument("--sessions", default=str(SESSIONS / "*.json"))
    ap.add_argument("--out", default=str(OUT / "sft_v2.jsonl"))
    ap.add_argument("--no-replay", action="store_true")
    a = ap.parse_args(argv)

    prompts = _load_prompts()
    kept, drops = [], []
    tried = defaultdict(list)
    for path in sorted(glob.glob(a.sessions)):
        s = json.loads(Path(path).read_text(encoding="utf-8"))
        tried[s["prompt_id"]].append(s["session_id"])
        if s["status"] != "final":
            drops.append({"session_id": s["session_id"], "reasons": [f"session {s['status']}: {s.get('abandon_reason', '')}"]})
            continue
        made_under = s["generator"].get("contract")
        if made_under != contract.CONTRACT_VERSION:
            drops.append({"session_id": s["session_id"],
                          "reasons": [f"stale contract: made under {made_under}, current {contract.CONTRACT_VERSION}"]})
            continue
        row = session_to_row(s, prompts[s["prompt_id"]])
        res = check_row(row, replay=not a.no_replay)
        row["verification"] = res["verification"]
        if res["keep"]:
            kept.append(row)
        else:
            drops.append({"session_id": s["session_id"], "reasons": res["reasons"]})

    solved = {r["prompt_id"] for r in kept}
    unsolved = [{"prompt_id": p, "sessions": ss} for p, ss in tried.items() if p not in solved]
    with open(a.out, "w", encoding="utf-8") as fh:
        for r in kept:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(OUT / "drops.jsonl", "w", encoding="utf-8") as fh:
        for d in drops:
            fh.write(json.dumps(d, ensure_ascii=False) + "\n")
    with open(OUT / "unsolved.jsonl", "w", encoding="utf-8") as fh:
        for u in unsolved:
            fh.write(json.dumps(u, ensure_ascii=False) + "\n")
    reasons = Counter(r.split(":")[0] + ":" + r.split(":")[1] if r.count(":") >= 1 else r
                      for d in drops for r in d["reasons"])
    print(json.dumps({"kept": len(kept), "dropped": len(drops), "unsolved_prompts": len(unsolved),
                      "drop_reasons": reasons.most_common(20)}, indent=1))
    for d in drops[:10]:
        print(d["session_id"], d["reasons"][:4])


if __name__ == "__main__":
    main()
