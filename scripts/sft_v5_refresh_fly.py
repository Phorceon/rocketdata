"""Fly saved-result sft_v5 rockets from their design JSON, in the current OpenRocket."""
import copy
import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import or_headless as oh  # noqa: E402
from scripts import sft_v4_complete_flights as flights  # noqa: E402
from scripts.sft_compact_motor_ids import load_lookup, restore_motor_digests  # noqa: E402
from scripts.sft_full_fidelity_extract import build_ork  # noqa: E402
from scripts.sft_v4_sources import from_compact  # noqa: E402

OUT = ROOT / "sftgen/out/scratch/sft_v5_roundtrip/refresh_flights.jsonl"


def main():
    _lookup, _ids, digest_by_id = load_lookup(ROOT / "new_results/sft_v4_motor_lookup.json")
    rows = {}
    for line in (ROOT / "new_results/sft_v5.jsonl").open():
        row = json.loads(line)
        if row["metric_provenance"].get("source") == "catalog_simulation":
            rows.setdefault(row["catalog_id"], row)
    work = Path(tempfile.mkdtemp(prefix="v5fresh"))
    oh._helper()
    with OUT.open("w") as out:
        for n, (cid, row) in enumerate(rows.items()):
            text = row["messages"][-1]["content"]
            compact = json.loads(re.search(r"<design>(.*)</design>", text, re.S).group(1))
            result = {"catalog_id": cid}
            try:
                design = from_compact(copy.deepcopy(compact))
                restore_motor_digests(design["parameter_tree"], digest_by_id)
                path = work / f"{n}.ork"
                build_ork(design, path)
                meta = {"warmup_calls": 0, "measured_calls": 0, "simulator_exceptions": 0}
                flown, _fcid = flights.simulate_exact(path, 0, meta)
                result.update(flown)
                result["ground_hit_event"] = any(e["type"] == "GROUND_HIT" and e["branch"] == 0 for e in flown["events"])
                result["sim_abort"] = any(e["type"] == "SIM_ABORT" and e["branch"] == 0 for e in flown["events"])
                result.pop("events", None)
            except Exception as exc:  # recorded, never hidden
                result["error"] = f"{type(exc).__name__}: {str(exc)[:220]}"
            out.write(json.dumps(result) + "\n")
            out.flush()


if __name__ == "__main__":
    main()
