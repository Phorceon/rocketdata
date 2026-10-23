"""Build data/sft_v1.jsonl: a rebalanced SFT split that reuses sft_v0 and adds
new rockets, with family-aware deduplication and family-leakage exclusion.

Rules (approved):
  * never edit sft_v0 / sft_test / rl_heldout.
  * drop every v0 row whose FAMILY also appears in sft_test or rl_heldout
    (family leakage -> a training row and a held-out twin are the same rocket).
  * cap examples at 5 per FAMILY (Raketa 92 -> 5, etc.).
  * add 50-60 NEW rockets chosen for variety (1-2 files per family, <=5 examples
    per family), preferring distinct stored sims per file.
  * reuse each stored sim's real wind_ms.
  * reproduce the v0 row format byte-for-byte (schema validated by
    scripts/verify_sft_v1.py).

Fixed seed -> one command rebuilds the file deterministically.
"""
import json
import os
import random
import re
import sys
from collections import defaultdict, Counter
from xml.etree import ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from ork_design import build_design, fingerprint, load_bytes  # noqa: E402
from ork_family import build_all as build_families, stem_family  # noqa: E402
from sft_v1_lib import (SYSTEM_MSG, sims_of, targets_of, render_thought,  # noqa: E402
                        render_design_ir, n_stages, PROMPT_TEMPLATES,
                        pick_prompt, motor_label)

SEED = 20261020
NEW_TARGET = 55            # aim for 50-60 new rockets
MAX_PER_FAMILY = 5         # examples per family (applies to v0 and new)
MAX_FILES_PER_FAMILY = 2   # new files taken from any one family
ORK = os.path.join(REPO, "ork")


def load_split(path):
    rows = defaultdict(list)
    for line in open(os.path.join(REPO, path), encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            rows[r["file"]].append(r)
    return rows


def motor_class(design):
    """Leading alpha of the first motor designation (impulse class)."""
    for c in _iter(design["components"]):
        for m in c.get("motors", []):
            for ch in m["designation"]:
                if ch.isalpha():
                    return ch.upper()
    return "?"


def _iter(comps):
    for c in comps:
        yield c
        yield from _iter(c.get("contains", []))


def all_components(path):
    comps, _ = build_design(path)
    return comps


def has_shape(comps):
    types = {c["type"] for c in _iter(comps)}
    return "nosecone" in types and "bodytube" in types


def has_recovery(comps):
    return any(c["type"] in ("parachute", "streamer") for c in _iter(comps))


def is_complete_sim(sim):
    """A sim usable for a row: an active motor and every metric the prompt/thought
    templates read must be present."""
    need = ("apogee_m", "max_velocity_ms", "max_mach", "time_to_apogee_s",
            "flight_time_s", "ground_hit_ms", "max_acceleration_ms2")
    return bool(sim.get("active_motors")) and all(sim.get(k) is not None for k in need)


def build_row(rid, path, sim, design, prompt_text, split="train"):
    thought = render_thought(prompt_text, sim, design)
    ir = render_design_ir(design)
    assistant = thought + "\n<design>\n" + ir + "\n</design>"
    return {
        "id": rid,
        "file": path,
        "source_prompt": "SFT_V1_GENERATED.md",
        "sim": sim["name"],
        "prompt_text": prompt_text,
        "messages": [
            {"role": "system", "content": SYSTEM_MSG},
            {"role": "user", "content": prompt_text},
            {"role": "assistant", "content": assistant},
        ],
        "targets": targets_of(sim),
        "ir_chars": len(ir),
        "split": split,
    }


def main():
    rng = random.Random(SEED)
    paths = sorted("ork/" + f for f in os.listdir(ORK) if f.lower().endswith(".ork"))
    fam, fam_members = build_families(paths)

    v0 = load_split("data/sft_v0.jsonl")
    test = load_split("data/sft_test.jsonl")
    held = load_split("data/splits/rl_heldout.jsonl")
    used_files = set(v0) | set(test) | set(held)

    # ---- family leakage: any family in test/heldout is dropped from training ----
    fsplit = defaultdict(set)
    for lab, d in (("v0", v0), ("test", test), ("held", held)):
        for p in d:
            fsplit[fam[p]].add(lab)
    leak_families = {f for f, s in fsplit.items() if "test" in s or "held" in s}

    # fingerprints of held-out designs (belt-and-braces exact-match exclusion)
    held_fp = set()
    for p in used_files:
        try:
            held_fp.add(fingerprint(all_components(p)))
        except Exception:
            pass

    keep = []          # selected rows
    kept_ids = set()

    # ---- 1) keep v0 rows, minus leaked families, capped 5/family ----
    v0_rows = [r for p in v0 for r in v0[p]]
    v0_by_fam = defaultdict(list)
    for r in v0_rows:
        if fam[r["file"]] in leak_families:
            continue
        v0_by_fam[fam[r["file"]]].append(r)
    for f, rows in v0_by_fam.items():
        rows = sorted(rows, key=lambda r: (r["file"], r["sim"]))
        for r in rows[:MAX_PER_FAMILY]:
            keep.append(r)
            kept_ids.add(r["id"])

    v0_base = len(keep)
    v0_fams = len(v0_by_fam)

    # ---- 2) choose NEW rockets for variety ----
    # candidate (file, sim) pairs, one family at a time
    cand = []
    for p in paths:
        if p in used_files or fam[p] in leak_families:
            continue
        try:
            comps = all_components(p)
        except Exception:
            continue
        if fingerprint(comps) in held_fp or not has_shape(comps) or not has_recovery(comps):
            continue
        sims = [s for s in sims_of(p) if is_complete_sim(s)]
        if not sims:
            continue
        design = {"flight": {"motor": motor_label(sims[0]), "wind_ms": sims[0]["wind_ms"]},
                  "components": comps}
        cand.append({"file": p, "family": fam[p], "sims": sims, "comps": comps,
                     "mclass": motor_class(design)})

    # group candidates by family, pick <= MAX_FILES_PER_FAMILY files per family
    by_fam = defaultdict(list)
    for c in cand:
        by_fam[c["family"]].append(c)

    # round-robin across families (shuffled) to maximise family variety, with a
    # soft preference for motor-class diversity among the NEW picks
    fam_order = sorted(by_fam, key=lambda f: (len(by_fam[f]), f))
    rng.shuffle(fam_order)
    chosen = []
    class_seen = Counter()
    file_count = Counter()
    # sort each family's files by n_sims desc, then name, for determinism
    for f in by_fam:
        by_fam[f].sort(key=lambda c: (-len(c["sims"]), c["file"]))

    def fam_bonus(c):
        return -class_seen[c["mclass"]]

    progress = True
    idx = 0
    while len(chosen) < NEW_TARGET and progress:
        progress = False
        for f in fam_order:
            if len(chosen) >= NEW_TARGET:
                break
            if file_count[f] >= MAX_FILES_PER_FAMILY:
                continue
            avail = [c for c in by_fam[f] if c not in chosen]
            if not avail:
                continue
            avail.sort(key=lambda c: (fam_bonus(c), -len(c["sims"]), c["file"]))
            c = avail[0]
            chosen.append(c)
            file_count[f] += 1
            class_seen[c["mclass"]] += 1
            progress = True

    # ---- 3) turn chosen new files into 2-4 rows each (distinct sims, <=5) ----
    new_rows = []
    new_ids = 0
    used_prompts = set(r["prompt_text"] for r in keep)
    for c in sorted(chosen, key=lambda x: x["file"]):
        sims = c["sims"]
        # prefer different sims; take 2-4 examples, at most 5
        k = min(len(sims), rng.choice([2, 3, 4]) if len(sims) >= 2 else 1)
        k = min(k, MAX_PER_FAMILY)
        picked = sims[:k]
        comps = c["comps"]
        for sim in picked:
            design = {"flight": {"motor": motor_label(sim), "wind_ms": sim["wind_ms"]},
                      "components": comps}
            t = targets_of(sim)
            # pick a varied prompt; avoid duplicate prompt strings
            for _ in range(40):
                pt = pick_prompt(PROMPT_TEMPLATES, t, sim, motor_label(sim),
                                 n_stages(design), rng)
                if pt not in used_prompts:
                    break
            used_prompts.add(pt)
            new_ids += 1
            rid = f"V1-{new_ids:03d}"
            new_rows.append(build_row(rid, c["file"], sim, design, pt))

    rows = keep + new_rows

    # ---- write ----
    out = os.path.join(REPO, "data", "sft_v1.jsonl")
    with open(out, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    # ---- console summary ----
    shares = Counter(r["file"] for r in rows)
    fam_share = Counter(fam[r["file"]] for r in rows)
    print(f"WROTE {out}")
    print(f"v0 base rows: {v0_base}  (from {v0_fams} families)")
    print(f"new rows: {len(new_rows)}  from {len(chosen)} new files")
    print(f"total rows: {len(rows)}")
    print(f"distinct files: {len(shares)}")
    print(f"largest single-file share: {shares.most_common(1)}")
    print(f"largest family share: {[(os.path.basename(k), v) for k, v in fam_share.most_common(3)]}")

    json.dump({
        "seed": SEED,
        "v0_base": v0_base,
        "new_rows": len(new_rows),
        "total": len(rows),
        "leak_families": [os.path.basename(f) for f in sorted(leak_families)],
        "chosen_files": [c["file"] for c in chosen],
    }, open(os.path.join(REPO, "data", "sft_v1_build_meta.json"), "w"), indent=2)


if __name__ == "__main__":
    main()
