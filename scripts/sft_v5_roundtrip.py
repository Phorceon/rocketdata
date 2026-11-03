"""Rebuild each sft_v5 design from its JSON alone, fly it, compare with its stored targets."""
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

OUT = ROOT / "sftgen/out/scratch/sft_v5_roundtrip/results.jsonl"


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    _lookup, _ids, digest_by_id = load_lookup(ROOT / "new_results/sft_v4_motor_lookup.json")
    rows = {}
    for line in (ROOT / "new_results/sft_v5.jsonl").open():
        row = json.loads(line)
        rows.setdefault(row["catalog_id"], row)
    work = Path(tempfile.mkdtemp(prefix="v5rt"))
    with OUT.open("w") as out:
        for n, (cid, row) in enumerate(rows.items()):
            if limit and n >= limit:
                break
            text = row["messages"][-1]["content"]
            compact = json.loads(re.search(r"<design>(.*)</design>", text, re.S).group(1))
            result = {"catalog_id": cid, "source": row["metric_provenance"].get("source"),
                      "targets": {k: row["targets"].get(k) for k in ("apogee_m", "ground_hit_ms", "flight_time_s")},
                      "flags": [f if isinstance(f, str) else f.get("flag") for f in row["flags"]]}
            try:
                design = from_compact(copy.deepcopy(compact))
                restore_motor_digests(design["parameter_tree"], digest_by_id)
                path = work / f"{n}.ork"
                build_ork(design, path)
                helper = oh._helper()
                doc = helper.load_doc(str(path))
                count = doc.getSimulationCount()
                result["sim_count"] = int(count)
                meta = {"warmup_calls": 0, "measured_calls": 0, "simulator_exceptions": 0}
                flown = flights.simulate_exact(path, 0 if count else None, meta)
                flown = flown[0] if isinstance(flown, tuple) else flown
                result["flown"] = {k: flown.get(k) for k in ("apogee_m", "ground_hit_ms", "flight_time_s")}
                result["motors"] = flown.get("flown_motors")
            except Exception as exc:  # recorded, never hidden
                result["error"] = f"{type(exc).__name__}: {str(exc)[:220]}"
            out.write(json.dumps(result) + "\n")
            out.flush()


if __name__ == "__main__":
    main()
