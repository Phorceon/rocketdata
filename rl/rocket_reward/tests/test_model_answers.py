"""The model's 48 saved answers must keep stopping where they stopped when the
checks were calibrated (tests/data/model_val_expected.json).

Each expected stage was compared with an independent hand label; the three
disagreements were read and settled (see the note at the end of this file).
If a change to a check moves an answer, this test fails and names it: either
the change is a mistake, or the snapshot must be re-made on purpose.
"""
from __future__ import annotations

import collections
import json
from pathlib import Path

import pytest

from rocket_reward.cli import run_row
from rocket_reward import ladder

DATA = Path(__file__).resolve().parent / "data"
EXPECTED = json.loads((DATA / "model_val_expected.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def results(model_rows):
    return {row["id"]: run_row(row) for row in model_rows}


def test_snapshot_covers_every_answer(model_rows):
    assert [r["id"] for r in model_rows] == list(EXPECTED)


@pytest.mark.parametrize("rid", list(EXPECTED))
def test_answer_stops_at_the_same_stage_with_the_same_score(results, rid):
    want, got = EXPECTED[rid], results[rid]
    assert got["stage"] == want["stage"], f"{rid}: now {got['stage']} ({got['reasons'][:2]}), was {want}"
    score = None if got["score"] is None else round(got["score"], 4)
    assert score == want["score"], f"{rid}: score now {score}, was {want['score']}"


def test_scores_sit_inside_their_stage_band(results):
    for rid, got in results.items():
        if got["score"] is None:
            assert got["stage"] == "passed", rid
            continue
        s = ladder.stage(got["stage"])
        assert s.floor - 1e-9 <= got["score"] <= s.top + 1e-9, rid


def test_stage_counts(results):
    counts = collections.Counter(r["stage"] for r in results.values())
    assert counts == {"format": 5, "parts": 6, "motor": 26, "limits": 3, "passed": 8}


def test_snapshot_file_is_consistent():
    for rid, e in EXPECTED.items():
        if e["score"] is None:
            assert e["stage"] == "passed", rid
        else:
            s = ladder.stage(e["stage"])
            assert s.floor - 1e-9 <= e["score"] <= s.top + 1e-9, rid


# Settled disagreements with the hand labels (an independent reading of each answer):
#   row-003: label said all parts present; the fins, motor tube and parachute sit directly under
#            the stage, outside "subcomponents", so OpenRocket ignores them -> parts (code right).
#   row-007: label said motor; a node carries "attrs" whose value is an object, which is not a
#            tree of the agreed shape -> format (code right).
#   row-009: label said limits on unusual material names. Settled with the material table: the
#            label was right (see below).
# Re-made on purpose after the stage 1-4 review:
#   row-006: motor -> parts. Its only parachute (with a fin set, a launch lug and a mass) sits
#            directly in the stage; OpenRocket accepts only nose cones, body tubes and
#            transitions there and drops the rest, so the rocket has no recovery device.
#   row-031: parts -> format. Its shock cord holds nodes tagged "cord diameter" and "cord diameter
#            method"; a tag with a space is not an XML element name, so OpenRocket could never
#            read the file (stage 1 tag rule, decided by the owner).
# Re-made on purpose when stage 4 started checking material names (unknown names fail):
#   row-009: passed -> limits. 'Paper, spiral kraft glassine, RK Tubes, loc:03a' (five parts) and
#            'Bronze' (launch lug) are not in the material table, so no real density can be given.
#   row-027: passed -> limits. Shock cord 'RS: Elastic cord (flat 10 mm, 3/8 in)' is not in the
#            material table (OpenRocket's lists have 19 mm and round 2-6 mm elastic cord).
#   row-023 still passed then: its unknown 'Paper, spiral kraft glassine, PK IIIa, bulk' sat only on
#            parts that override their own mass, so it was noted, not counted.
# Re-made on purpose 2026-11-19 after the targets, overrides and sizes changes of that day; only one
# answer moved (stage counts: limits 2 -> 3, passed 9 -> 8):
#   row-023: passed -> limits 0.34 (overrides). With its mass overrides removed, the unknown material
#            'Paper, spiral kraft glassine, PK IIIa, bulk' gives four parts their mass, so it counts.
#   The targets change works only in stage 7, and the new stage 4 size bounds change no stage or
#   score here (the sizes change moves answers only through stage 5, in test_model_scores.py).
#   Checked again after the second round of fixes the same day (stages 5 and 6 only): no stage or
#   score moved, so the file is unchanged.
