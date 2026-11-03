"""Materialize explicit XML trees through the pinned OpenRocket saver (no hand-invented params)."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import jpype

from .ork_archive import read_ork_archive, write_ork_archive


def materialize_through_openrocket(
    parameter_tree: dict[str, Any],
    bundle_entries: dict[str, bytes] | None,
    *,
    load_doc,
) -> dict[str, Any]:
    """Load explicit tree, save with GeneralRocketSaver, re-read rocket.ork."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        src = tmp_path / "explicit.ork"
        write_ork_archive(src, parameter_tree, bundle_entries)
        doc = load_doc(str(src))
        dest = tmp_path / "materialized.ork"
        GeneralRocketSaver = jpype.JClass("info.openrocket.core.file.GeneralRocketSaver")
        File = jpype.JClass("java.io.File")
        saver = GeneralRocketSaver()
        options = doc.getDefaultStorageOptions()
        saver.save(File(str(dest)), doc, options)
        tree, _entries = read_ork_archive(dest)
        return tree
