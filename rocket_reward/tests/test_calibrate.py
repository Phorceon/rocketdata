"""The gold calibration tool: python -m rocket_reward.tools.calibrate_preflight."""
from __future__ import annotations

import json

from rocket_reward.tools.calibrate_preflight import calibrate


def _write(path, lines):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    return path


def test_rows_are_named_by_their_real_line(tmp_path):
    row = json.dumps({"content": "no design"})
    path = _write(tmp_path / "train.jsonl", [row, "", row])
    cal = calibrate([str(path)])
    assert cal["rows"] == 2
    assert set(cal["failures"]) == {"train-0", "train-2"}


def test_files_with_the_same_name_keep_all_their_rows(tmp_path):
    row = json.dumps({"content": "no design"})
    a = _write(tmp_path / "a" / "val.jsonl", [row, row])
    b = _write(tmp_path / "b" / "val.jsonl", [row, row])
    cal = calibrate([str(a), str(b)])
    assert cal["rows"] == 4
    assert set(cal["failures"]) == {"val-0", "val-1", "val-0#2", "val-1#2"}


# ------------------------------------------------------------------ the whole-ladder report (tools/calibrate.py)

def _ladder_row(rid, design, stage, score, reasons=(), findings=(), defects=()):
    return {"id": rid, "design": design, "block": design, "split": "train", "requirements_ok": True,
            "joined_by": "id", "stage": stage, "score": score, "credit": 0.0, "reasons": list(reasons),
            "defects": list(defects), "findings": list(findings), "metrics": {}, "shadow": None,
            "motor_facts_credit": None}


def test_ladder_summary_matches_failures_with_predictions():
    from rocket_reward.tools.calibrate import ladder_report_md, summarize_ladder
    results = [_ladder_row("a", "D1", "targets", 1.0), _ladder_row("a2", "D1", "targets", 1.0),
               _ladder_row("b", "D2", "flight", 0.6, ["too fast"], [{"rule": "deploy_speed", "size": 0.4}]),
               _ladder_row("c", "D3", "build", 0.42, ["step"], [{"rule": "shell_step", "value": 1.0, "limit": 0.1,
                                                              "size": 3.0, "defect": False}]),
               _ladder_row("d", "D4", "limits", 0.34, ["Custom"]),
               _ladder_row("e", "D5", "targets", 0.9, defects=["small fit problem: x"])]
    expected = {"D2": {"stage": "flight", "why": "fast opening"}, "D4": {"stage": "build", "why": "fins"},
                "D5": {"stage": "flight", "why": "unstable"}}
    s = summarize_ladder(results, expected)
    assert s["stage_rows"] == {"targets": 3, "flight": 1, "build": 1, "limits": 1}
    assert s["unexpected"] == ["D3"] and s["other_stage"] == ["D4"]
    assert list(s["predicted_but_reached_targets"]) == ["D5"]
    assert s["largest_tie"] == {"score": 1.0, "rows": 2}
    md = ladder_report_md(s, {"workers": 4, "score_s": 1.0, "s_per_answer": 0.1, "pool_start_s": 2.0}, "T")
    assert md.index("Failures nobody predicted") < md.index("### D3") < md.index("### D4") < md.index("### D2")
    assert "shell_step value 1 limit 0.1 size 3" in md and "small fit problem: x" in md
    assert "\r" not in md


def test_reference_rows_join_by_id_then_prompt(tmp_path):
    from rocket_reward.tools.calibrate import reference_rows
    meta = _write(tmp_path / "meta.jsonl", [
        json.dumps({"id": "V4-1", "group_id": "V4-1", "prompt_text": "p1", "split": "train",
                    "messages": [{}, {}, {"role": "assistant", "content": "<design>{}</design>"}]}),
        json.dumps({"id": "V4-2", "group_id": "V4-2", "prompt_text": "p2", "split": "val",
                    "messages": [{}, {}, {"role": "assistant", "content": "x"}]}),
        json.dumps({"id": "V4-3", "group_id": "V4-3", "prompt_text": "p3", "messages": []})])
    prompts = _write(tmp_path / "parsed.jsonl", [
        json.dumps({"id": "V4-1:original", "prompt_text": "other", "requirements": {"id": "r1"}}),
        json.dumps({"id": "zzz:casual", "prompt_text": "p2", "requirements": {"id": "r2"}})])
    rows = reference_rows(meta, prompts)
    assert [(r["id"], r["joined_by"], (r["requirements"] or {}).get("id")) for r in rows] == [
        ("V4-1", "id", "r1"), ("V4-2", "prompt", "r2"), ("V4-3", None, None)]
    assert rows[0]["answer"] == "<design>{}</design>" and rows[2]["answer"] == ""
