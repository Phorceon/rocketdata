"""The model's 48 saved answers through the whole ladder, simulator included.

tests/data/model_val_requirements.json holds the requirements of each answer's
prompt (the parsed record of the same prompt text, val split).
tests/data/model_val_scored.json is the frozen result: the stage where each
answer stops and its score to 4 places. If a change to any stage moves an
answer, this test names it: either the change is a mistake, or the snapshot
must be re-made on purpose (and the reason written down).

Re-made 2026-11-19 after the stage 5-7 review (13 answers moved):
  * row-042: targets 0.8947 -> build 0.4072; its four motors sit 0.4-1.9 m
    ahead of the tail and fire into the airframe (new rule, limits.MOTOR_AHEAD_OF_TAIL_MAX_M)
  * row-023: flight 0.5444 -> 0.5179; the simulator reports its main section
    landing at 0 m/s (the last sample is after touchdown), now counted as unknown
  * 11 unknown-motor answers move inside the motor band: the shadow substitute
    is now chosen from the mount's inside diameter, not the written motor
    diameter, and several shadows now stop at build on the motor-position rule

Re-made again 2026-11-19 after four small corrections (6 answers moved):
  * row-023: flight 0.5179 -> 0.5362; the helper now reads the landing speed at
    the touchdown sample, not the at-rest last sample: 8.4-8.7 m/s instead of
    0 (unknown). It passes the 9 m/s limit but not the prompt's 4.6 m/s.
  * 5 unknown-motor answers move inside the motor band because the shadow
    substitute now has the motor type the design wrote (single or reload) and,
    where that flies at least as well, the design's maker (AeroTech):
    row-026 0.2474 -> 0.2471 (I357T reload -> HP-I280DM single-use),
    row-028 0.2591 -> 0.2580 (Contrail H141 hybrid -> H100W_DMS single-use),
    row-043 0.2443 -> 0.2310 (Contrail H300 hybrid -> Gorilla H225BL reload;
    AeroTech's I218R flew worse, so the maker-free choice counted),
    row-046 0.2615 -> 0.2657 (Contrail H211 hybrid -> AeroTech H219T single-use),
    row-048 0.2761 -> 0.2740 (Cesaroni 475I445 reload -> AeroTech I65W single-use)

Re-made 2026-11-19 after three changes made the same day (18 answers moved;
"from" is the snapshot before them): stage 7 is the product of the target
credits and the prompt's landing number moved from stage 6 to stage 7
("targets"); the cleaning removes every override setting, so nothing is
excused by one ("overrides"); an inside part is judged by how far it lies
outside the airframe, and stage 4 bounds many more sizes ("sizes"):
  * row-021: targets 0.8568 -> 0.7107 (targets); it misses the apogee (credit
    0.20), the flight time (0.21) and the body diameter (0.84), which now
    multiply instead of averaging
  * row-023: flight 0.5362 -> limits 0.3400 (overrides); with its mass
    overrides gone, its unknown material 'Paper, spiral kraft glassine, PK
    IIIa, bulk' gives four parts their mass, so the name counts. Alone, the
    targets change gives flight 0.5444 (no prompt-landing violation in stage 6)
    and the sizes change build 0.4324 (a 2 mm bulkhead 50.8 mm behind the tail);
    stage 4 comes first
  * row-022: build 0.4000 -> 0.4380 (overrides); OpenRocket could not read its
    overridemass 'auto'; the tag is now removed and only the rail button
    warning is left
  * row-036: flight 0.5105 -> 0.5108 (overrides); flown without its overrides
    it is still unstable (-1.5 cal on the pad instead of -1.7)
  * 14 unknown-motor answers move inside the motor band, because half their
    credit is their shadow flight (the same rocket with a real motor):
    - overrides only, the shadow stops at limits on a material its overrides
      used to excuse: row-001 0.2145 -> 0.2142, row-002 0.2290 -> 0.2282,
      row-017 0.2286 -> 0.2270, row-013 0.2471 -> 0.2423 (its shadow now
      stops at limits 0.34 instead of build 0.4243)
    - sizes only, the shadow gains an outside-the-airframe finding:
      row-004 0.2330 -> 0.2329 (a ring 50.8 mm outside), row-012 0.2340 ->
      0.2339 (a packed part 63.5 mm outside, a defect), row-047 0.2387 ->
      0.2327 (its shadow stops at build, a 4.8 mm ring 0.24 m behind the tail,
      instead of flight)
    - targets, the shadow reaches stage 7 and is scored by the product:
      row-026 0.2471 -> 0.2497 (its shadow's 8.0 m/s landing no longer stops
      it at flight), row-010 0.2581 -> 0.2524, row-028 0.2580 -> 0.2508,
      row-032 0.2624 -> 0.2546, row-046 0.2657 -> 0.2556, row-048 0.2740 ->
      0.2651; the last five also fly without overrides, which moves their
      shadow's flight a little (row-010 0.2523 with the targets change alone)
    - overrides and targets: row-043 0.2310 -> 0.2453; without its overrides
      its shadow no longer opens the recovery at 89 m/s and reaches stage 7
      (0.86 with the product)
"""
from __future__ import annotations

import collections
import json
from pathlib import Path

import pytest

from rocket_reward import Requirements, ladder
from rocket_reward.scoring import ErrorTracker, score_many

DATA = Path(__file__).resolve().parent / "data"
REQUIREMENTS = json.loads((DATA / "model_val_requirements.json").read_text(encoding="utf-8"))
SCORED = json.loads((DATA / "model_val_scored.json").read_text(encoding="utf-8"))


def test_files_cover_every_answer(model_rows):
    ids = [r["id"] for r in model_rows]
    assert list(REQUIREMENTS) == ids and list(SCORED) == ids
    for rid, rec in REQUIREMENTS.items():
        Requirements.from_dict(rec)   # every record is valid


def test_frozen_scores_sit_in_their_bands():
    for rid, e in SCORED.items():
        s = ladder.stage(e["stage"])
        assert s.floor - 1e-9 <= e["score"] <= s.top + 1e-9, rid


@pytest.fixture(scope="module")
def scored_results(model_rows):
    from rocket_reward.sim import SimPool
    reqs = [Requirements.from_dict(REQUIREMENTS[r["id"]]) for r in model_rows]
    with SimPool(4) as pool:
        got = score_many([r.get("content") or "" for r in model_rows], reqs,
                         [bool(r.get("truncated")) for r in model_rows], simulator=pool,
                         tracker=ErrorTracker())
    return {r["id"]: g for r, g in zip(model_rows, got)}


@pytest.mark.needs_java
@pytest.mark.parametrize("rid", list(SCORED))
def test_answer_keeps_its_stage_and_score(scored_results, rid):
    want, got = SCORED[rid], scored_results[rid]
    assert got.score is not None, f"{rid} was quarantined: {got.reasons}"
    assert (got.stage, round(got.score, 4)) == (want["stage"], want["score"]), \
        f"{rid}: now {got.stage} {got.score} ({got.reasons[:2]}), was {want}"


@pytest.mark.needs_java
def test_stage_counts_and_ties(scored_results):
    counts = collections.Counter(r.stage for r in scored_results.values())
    assert counts == collections.Counter(e["stage"] for e in SCORED.values())
    # Shadow flights break the ties among unknown-motor answers.
    ties = collections.Counter(round(r.score, 6) for r in scored_results.values())
    assert ties.most_common(1)[0][1] <= 5
