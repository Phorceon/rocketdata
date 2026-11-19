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
