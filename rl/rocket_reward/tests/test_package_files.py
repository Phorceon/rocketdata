"""Checks on the package's own files: one copy of each helper, LF endings,
no machine-specific paths."""
from __future__ import annotations

import ast
import collections
import re
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".py", ".md", ".java", ".json"}


def package_files() -> list[Path]:
    return sorted(p for p in PACKAGE.rglob("*") if p.is_file() and p.suffix in TEXT_SUFFIXES
                  and "__pycache__" not in p.parts)


def test_no_helper_is_defined_twice():
    """A top-level function name appears in one module only (tools may each
    have their own main), and the tests share one design_of."""
    seen = collections.defaultdict(list)
    for p in sorted(PACKAGE.rglob("*.py")):
        if "__pycache__" in p.parts:
            continue
        for node in ast.parse(p.read_text(encoding="utf-8")).body:
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("test_") and node.name != "main":
                seen[node.name].append(p.relative_to(PACKAGE).as_posix())
    # pytest fixtures with the same name in two test files are separate on purpose
    fixtures_ok = {"gold", "gold_designs", "table", "_write", "fails"}
    twice = {k: v for k, v in seen.items() if len(v) > 1 and k not in fixtures_ok}
    assert twice == {}, twice


def test_lf_endings_and_no_machine_paths():
    drive = re.compile(r"\b[A-Za-z]:(?:/|\x5c)[A-Za-z]")  # C:/ or C:\ (\x5c is a backslash)
    for p in package_files():
        raw = p.read_bytes()
        assert b"\r" not in raw, p
        text = raw.decode("utf-8")
        assert not drive.search(text), (p, drive.search(text).group(0))
