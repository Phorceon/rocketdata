"""Shared pytest setup.

Test data in tests/data (gzip, one JSON object per line):
  gold_val.jsonl.gz   48 reference answers: {"id", "prompt", "answer"}
  model_val.jsonl.gz  the fine-tuned model's 48 answers to the same prompts:
                      {"id", "truncated", "completion_tokens", "content"}
The two files use the same ids in the same order.
"""
from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
REPO = HERE.parents[1]
if str(REPO) not in sys.path:  # lets `pytest rocket_reward/tests` work from any folder
    sys.path.insert(0, str(REPO))


def pytest_configure(config):
    config.addinivalue_line("markers", "needs_java: needs Java 17 and the OpenRocket jar")


_JAVA_PROBLEM: list = []  # filled once: [None] when Java and the jar were found, else [reason]


def java_problem() -> "str | None":
    """Why the needs_java tests cannot run here, or None when Java and the jar are found."""
    if not _JAVA_PROBLEM:
        from rocket_reward.errors import RewardSetupError
        from rocket_reward.sim import find_jar, find_java
        try:
            find_java()
            find_jar()
            _JAVA_PROBLEM.append(None)
        except RewardSetupError as exc:
            _JAVA_PROBLEM.append(str(exc).splitlines()[0])
    return _JAVA_PROBLEM[0]


def pytest_collection_modifyitems(config, items):
    """Skip tests marked needs_java, with the reason, when Java or the jar is missing."""
    marked = [item for item in items if item.get_closest_marker("needs_java")]
    if not marked:
        return
    problem = java_problem()
    if problem:
        skip = pytest.mark.skip(reason=f"needs Java 17 and the OpenRocket jar: {problem}")
        for item in marked:
            item.add_marker(skip)


def read_jsonl_gz(path: Path) -> list:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


@pytest.fixture(scope="session")
def gold_rows() -> list:
    """The 48 reference answers."""
    return read_jsonl_gz(DATA / "gold_val.jsonl.gz")


@pytest.fixture(scope="session")
def model_rows() -> list:
    """The model's 48 saved answers."""
    return read_jsonl_gz(DATA / "model_val.jsonl.gz")
