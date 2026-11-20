"""Override settings are removed by the cleaning (2026-11-19).

A review showed that mass and balance overrides, even bounded against the same
rocket without them, could fake about 2 calibres of stability and hide a
too-fast landing. Every tag starting with "override" is now removed before
anything judges or flies the design, the second simulator run that compared
the two rockets is gone, and no stage 4 rule is excused by an override.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from rocket_reward import Requirements, ladder
from rocket_reward import limit_checks as LC
from rocket_reward import limits as L
from rocket_reward import scoring as S
from rocket_reward.clean import OVERRIDE_TAG_PREFIX, clean_design, override_count
from rocket_reward.tools import mutate as M
from rocket_reward.tree import tag_of, walk_nodes
from answers import design_of
from replies import load_reply

DATA = Path(__file__).resolve().parent / "data"
REQ = Requirements.from_dict({"id": "t-1", "apogee_m": {"value": 500, "kind": "about"}})
ALL_OVERRIDE_TAGS = ("overridemass", "overridecg", "overridecd", "overridesubcomponents",
                     "overridesubcomponentsmass", "overridesubcomponentscg", "overridesubcomponentscd")


class FakeSim:
    """Answers every run with a recorded reply and remembers each request."""

    def __init__(self, reply=None):
        self.reply = reply if reply is not None else load_reply("single_stage")
        self.calls: list[dict] = []
        self._lock = threading.Lock()

    def run(self, ork_text, rail_m, flights, config_id=None, **extra):
        with self._lock:
            self.calls.append({"ork": ork_text, "flights": flights, **extra})
        return self.reply


@pytest.fixture(name="quiet")
def quiet_scoring(monkeypatch, tmp_path):
    monkeypatch.setattr(S, "_default_tracker", S.ErrorTracker())
    monkeypatch.setenv(S.QUARANTINE_ENV, str(tmp_path / "quarantine"))
    return tmp_path


def _tags(root) -> list[str]:
    return [tag_of(n) for n in walk_nodes(root)]


def _with_overrides(design: dict) -> dict:
    """Every stage and part gets one of each override setting."""
    for node in walk_nodes(design):
        if tag_of(node) in ("stage", "nosecone", "bodytube", "trapezoidfinset", "parachute"):
            body = node[tag_of(node)]
            body.setdefault("children", []).extend({t: {"value": 0.5}} for t in ALL_OVERRIDE_TAGS)
    return design


def _passing_gold_with_overrides(gold_rows):
    for row in gold_rows:
        pre = S.preflight(row["answer"])
        if pre.passed and pre.overrides_removed:
            return row["answer"], pre
    raise AssertionError("no reference answer with overrides passes stages 1-4")


# ------------------------------------------------------------------ the cleaning

def test_every_override_setting_is_removed_and_counted(gold_rows):
    for row in gold_rows[:12]:
        d = _with_overrides(design_of(row["answer"]))
        before = json.dumps(d)
        n = override_count(d)
        out, notes = clean_design(d, S.default_motor_table())
        assert json.dumps(d) == before                       # the input is never changed
        assert not any(t.startswith(OVERRIDE_TAG_PREFIX) for t in _tags(out))
        assert n >= 5 * len(ALL_OVERRIDE_TAGS) and override_count(out) == 0
        assert any(f"removed {n} override setting(s)" in x and "mass component" in x for x in notes)


def test_override_inside_an_override_is_counted_once():
    tree = {"openrocket": {"children": [{"rocket": {"children": [
        {"overridemass": {"value": 1.0, "children": [{"overridecg": {"value": 0.1}}]}},
        {"overridecgsomething": {"value": 1}}, {"length": {"value": 0.5}}]}}]}}
    assert override_count(tree) == 2
    out, notes = clean_design(tree, S.default_motor_table())
    assert override_count(out) == 0 and any("removed 2 override setting(s)" in x for x in notes)


def test_cleaning_twice_changes_nothing(gold_rows):
    d = _with_overrides(design_of(gold_rows[0]["answer"]))
    once, _ = clean_design(d, S.default_motor_table())
    twice, notes = clean_design(once, S.default_motor_table())
    assert twice == once and notes == []


# ------------------------------------------------------------------ stage 4 sees the tree that flies

def test_stage_4_runs_on_the_cleaned_tree_and_no_override_excuses_a_zero_wall(gold_rows):
    """A 0 mm wall on a part with its own mass override passed stage 4 before
    2026-11-19; now the override is gone and the wall fails."""
    d = design_of(gold_rows[0]["answer"])
    tube = next(n for n in walk_nodes(d) if tag_of(n) == "bodytube")
    kids = tube["bodytube"]["children"]
    kids[:] = [c for c in kids if tag_of(c) != "thickness"] + [{"thickness": {"value": 0.0}},
                                                               {"overridemass": {"value": 0.3}}]
    pre = S.preflight("<design>" + json.dumps(d) + "</design>")
    assert pre.failed is not None and pre.failed.stage == "limits"
    assert any("0 mm" in r for r in pre.failed.reasons)
    assert pre.overrides_removed >= 1
    assert not any(t.startswith(OVERRIDE_TAG_PREFIX) for t in _tags(pre.clean_root))


def test_limit_checks_hold_no_override_rule():
    import inspect
    src = inspect.getsource(LC)
    assert "overridemass" not in src and "overridecg" not in src and "mass_overridden" not in src
    for name in ("OVERRIDE_MASS_RATIO_MIN", "OVERRIDE_MASS_RATIO_MAX", "OVERRIDE_CG_SHIFT_MAX_CAL",
                 "OVERRIDE_MASS_MAX_KG", "OVERRIDE_CD_MAX", "OVERRIDE_CG_MAX_M"):
        assert not hasattr(L, name), name


# ------------------------------------------------------------------ one simulator run

def test_one_run_per_answer_and_the_flag_counts_what_was_removed(quiet, gold_rows):
    answer, pre = _passing_gold_with_overrides(gold_rows)
    sim = FakeSim()
    r = S.score(answer, REQ, simulator=sim)
    assert len(sim.calls) == 1 and "max_sim_time_s" not in sim.calls[0]
    assert "override" not in sim.calls[0]["ork"]
    assert r.flags["overrides_removed"] == pre.overrides_removed > 0
    assert any("override setting(s)" in n for n in r.flags["clean_notes"])
    assert not hasattr(S, "NATURAL_MAX_SIM_TIME_S")


def test_the_flag_is_kept_when_stage_4_stops_the_answer(quiet, gold_rows):
    d = design_of(gold_rows[0]["answer"])
    for node in walk_nodes(d):
        if tag_of(node) == "parachute":
            node["parachute"]["children"] += [{"cd": {"value": 50.0}}, {"overridemass": {"value": 0.0}}]
    r = S.score("<design>" + json.dumps(d) + "</design>", REQ, simulator=FakeSim())
    assert r.stage == "limits" and r.flags["overrides_removed"] >= 1


def test_no_flag_without_overrides(quiet, gold_rows):
    answer, _ = _passing_gold_with_overrides(gold_rows)
    d = design_of(answer)
    M._mu_drop(d, M.OVERRIDE_TAGS)
    r = S.score("<design>" + json.dumps(d) + "</design>", REQ, simulator=FakeSim())
    assert "overrides_removed" not in r.flags


def test_build_check_takes_the_reply_and_the_tree_only():
    import inspect
    from rocket_reward import fit
    assert list(inspect.signature(fit.check_build).parameters) == ["reply", "root"]
    for gone in ("_check_overrides", "_check_stage_overrides", "_stage_structure"):
        assert not hasattr(fit, gone), gone


# ------------------------------------------------------------------ the mutation operators

def test_override_operators_must_change_nothing():
    for name in ("override_over_limit", "override_negative", "ballast_overrides", "ballast_cg_override",
                 "lighten_rocket_override", "lighten_one_stage_override", "drag_override",
                 "light_stage_mass_override"):
        assert M.operator_named(name).expect == M.EXPECT_SAME, name
    fake = M.operator_named("unstable_fake_cg_override")
    assert fake.expect == "flight" and fake.untagged is not None
    assert M.operator_named("light_stage_mass_override").untagged is not None


def test_review_cheats_differ_from_their_untagged_copy_only_by_override_tags(gold_rows):
    table = S.default_motor_table()
    seen = 0
    for row in gold_rows:
        d = design_of(row["answer"])
        for name in ("unstable_fake_cg_override", "light_stage_mass_override"):
            op = M.operator_named(name)
            tagged, plain = M.apply_operator(op, d, table), op.untagged(json.loads(json.dumps(d)), table)
            if tagged is None:
                continue
            seen += 1
            M._mu_drop(tagged, M.OVERRIDE_TAGS)
            M._mu_drop(plain, M.OVERRIDE_TAGS)
            assert tagged == plain, (row["id"], name)
    assert seen >= 6


def test_a_cheat_that_does_not_match_its_untagged_copy_is_reported(gold_rows):
    case = M.collect_designs([{"id": "x", "answer": gold_rows[0]["answer"], "requirements": {}}])[0][0]
    cases = [{"design": "x", "operator": "unstable_fake_cg_override", "expect": "flight", "answer": "",
              "untagged_answer": ""},
             {"design": "x", "operator": "light_stage_mass_override", "expect": M.EXPECT_SAME, "answer": "",
              "untagged_answer": ""}]
    outcomes = {"x": M.Outcome("targets", 1.0),
                "x|unstable_fake_cg_override": M.Outcome("targets", 1.0),
                "x|unstable_fake_cg_override" + M.UNTAGGED_SUFFIX: M.Outcome("flight", 0.537),
                "x|light_stage_mass_override": M.Outcome("flight", 0.6),
                "x|light_stage_mass_override" + M.UNTAGGED_SUFFIX: M.Outcome("flight", 0.6)}
    ops = [M.operator_named("unstable_fake_cg_override"), M.operator_named("light_stage_mass_override")]
    summary = M.summarize_mutations([case], cases, outcomes, ops)
    assert [f["operator"] for f in summary["failures"]] == ["unstable_fake_cg_override"]
    ok = next(r for r in summary["rows"] if r["operator"] == "light_stage_mass_override")
    assert ok["ok"] is True and "without the tags flight 0.6000" in ok["words"]


# ------------------------------------------------------------------ with Java: tags change nothing

@pytest.mark.needs_java
def test_review_cheats_score_exactly_as_without_their_tags(gold_rows):
    """The stability and landing cheats of the review, on three val designs:
    the copy with the override tags gets exactly the stage and score of the
    copy without them, and the halved fins stop at the flight stage."""
    from rocket_reward.sim import SimPool
    reqs = json.loads((DATA / "model_val_requirements.json").read_text(encoding="utf-8"))
    table = S.default_motor_table()
    texts, req_list, keys = [], [], []
    for name in ("unstable_fake_cg_override", "light_stage_mass_override"):
        op = M.operator_named(name)
        used = 0
        for row in gold_rows:
            case = M.collect_designs([{"id": row["id"], "answer": row["answer"], "requirements": reqs[row["id"]]}])[0][0]
            tagged = M.apply_operator(op, case.design, table)
            if tagged is None:
                continue
            plain = op.untagged(json.loads(json.dumps(case.design)), table)
            texts += [M.mutant_answer(case, tagged), M.mutant_answer(case, plain)]
            req_list += [Requirements.from_dict(reqs[row["id"]])] * 2
            keys.append((name, row["id"]))
            used += 1
            if used == 3:
                break
    with SimPool(2) as pool:
        got = S.score_many(texts, req_list, simulator=pool, tracker=S.ErrorTracker())
    for i, (name, rid) in enumerate(keys):
        tagged, plain = got[2 * i], got[2 * i + 1]
        assert tagged.score is not None and plain.score is not None, (name, rid)
        assert (tagged.stage, tagged.score) == (plain.stage, plain.score), (name, rid, tagged.reasons[:1])
        assert tagged.flags.get("overrides_removed", 0) >= max(1, plain.flags.get("overrides_removed", 0))
        if name == "unstable_fake_cg_override":
            assert tagged.stage == "flight" and ladder.stage("flight").floor <= tagged.score, (rid, tagged.reasons[:1])
