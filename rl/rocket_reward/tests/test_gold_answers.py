"""Every one of the 48 reference ("gold") answers in tests/data must pass
stages 1-4. A sound reference rocket failing a check means the check is wrong.
"""
from __future__ import annotations

import pytest

from rocket_reward.cli import run_row


def test_there_are_48_gold_answers(gold_rows):
    assert len(gold_rows) == 48


@pytest.mark.parametrize("i", range(48))
def test_gold_answer_passes_preflight(gold_rows, i):
    row = gold_rows[i]
    got = run_row(row)
    assert got["stage"] == "passed", f"{row['id']} stops at {got['stage']}: {got['reasons'][:3]}"
