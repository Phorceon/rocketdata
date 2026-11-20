"""The saved mutation set (tools/mutate.py): named ways to break or cheat with a
rocket, each with what the reward must do with it.

Without Java, every operator judged at stages 1-4 runs on all 48 reference
answers (16 distinct designs) and must stop exactly where it says, and the
repairs of real model answers must reach a later stage. With Java, a fixed
subset (tests/data/mutation_expected.json: 5 reference designs times every
simulator-stage operator, plus the repairs) is scored and compared with the
snapshot (stage, and score to 4 places), and the ordering promises are checked.

Re-make the snapshot on purpose (and say why) with:

    python -m rocket_reward.tools.mutate --answers rocket_reward/tests/data/gold_val.jsonl.gz \\
        --requirements rocket_reward/tests/data/model_val_requirements.json \\
        --repair-answers rocket_reward/tests/data/model_val.jsonl.gz \\
        --designs <the "designs" list of the snapshot> --operators <its "operators" list> \\
        --out report.md --write-expected rocket_reward/tests/data/mutation_expected.json

Re-made 2026-11-19 after three changes made the same day ("targets": stage 7
is the product of the target credits and the prompt's landing number moved
from stage 6 to stage 7; "overrides": the cleaning removes every override
setting; "sizes": parts are judged by how far they lie outside the airframe,
and stage 4 bounds many more sizes). Same 10 designs; 91 cases -> 131.
Changes from the snapshot before them (2 cases dropped, 42 added):
  * 13 operators added, 42 cases: override_over_limit, override_negative,
    unstable_fake_cg_override and light_stage_mass_override (overrides; each
    scores exactly as its copy without the tags), far_away_thin_part,
    far_away_mass, far_away_recovery, pod_part_far_away, lug_behind_tail and
    closed_tail (sizes; all stop at build), chute_too_small_for_prompt,
    landing_just_under_hard_limit and swap_to_unnamed_motor (targets; each
    stays in targets with a lower score). pod_part_far_away has no case
    here: none of these designs has a pod.
  * ballast_overrides, ballast_cg_override, lighten_rocket_override and
    lighten_one_stage_override (17 cases): build 0.41-0.43 -> targets 1.0,
    like their originals (overrides)
  * chute_far_too_small no longer applies to row-007 (largest parachute
    0.38 m) and row-016 (0.30 m): the 0.15 m floor shrinks them less than four
    times, and row-016 landed at 7.8 m/s, under the 9 m/s limit;
    chute_too_small_for_prompt covers that case. On row-001, -028 and -040 it
    stays at flight and scores higher, 0.5310 -> 0.5492, 0.5391 -> 0.5647 and
    0.5379 -> 0.5667: no prompt-landing violation on top of the 9 m/s one
    (targets; -028 and -040 also fly without their overrides)
  * weaker_motor: row-001 0.8712 -> 0.7854, row-007 0.8678 -> 0.7819, row-016
    0.8852 -> 0.8086, row-040 0.8817 -> 0.8015; the apogee miss now
    multiplies instead of being averaged with the met targets (targets;
    -007 and -040 also fly without their overrides); row-028 flight
    0.6723 -> 0.6746 (overrides)
  * booster_without_recovery on row-007 0.5919 -> 0.5917 and
    zero_ejection_delay on row-040 0.5536 -> 0.5538: flown without overrides
  * model:row-013: motor 0.2471 -> 0.2423, and its repair_motor_spelling case
    build 0.4243 -> limits 0.3400: an unknown line material is no longer
    excused by a mass override (overrides)
  * model:row-048: motor 0.2740 -> 0.2651 (its shadow flight is scored by the
    product and flies without overrides), and its repair_motor_spelling case
    targets 0.9910 -> 0.9395: its 2.34 kg against the asked 2.20 kg (credit
    0.80) now counts in full (targets), and without overrides it weighs
    2.34 kg, not 2.38 kg (overrides)

Known findings (KNOWN_FINDINGS below) are cases where the reward does not yet
do what the operator says it must. They are left for the owner to decide; the
test checks that they still behave as recorded, so a fix shows up here.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from rocket_reward import ladder
from rocket_reward.scoring import default_motor_table
from rocket_reward.tools import mutate as M

DATA = Path(__file__).resolve().parent / "data"
REQUIREMENTS_PATH = DATA / "model_val_requirements.json"
EXPECTED = json.loads((DATA / "mutation_expected.json").read_text(encoding="utf-8"))

# (operator, design id) -> what happens instead. Empty today: the one finding
# of the first full run (floating_fins on row-016-5851080b, tube fins 1.5 lengths
# behind the body still reaching targets) was fixed in fit._check_fins, which
# now uses a tube fin set's own position and length as its root.
KNOWN_FINDINGS: dict[tuple[str, str], str] = {}

PREFLIGHT_OPS = [op for op in M.OPERATORS if not op.needs_simulator]
REFERENCE_OPS = [op for op in M.OPERATORS if not op.repair]
REPAIR_OPS = [op for op in M.OPERATORS if op.repair]


REQUIREMENTS = json.loads(REQUIREMENTS_PATH.read_text(encoding="utf-8"))


def _tm_cases(rows: list, key: str) -> list:
    """One DesignCase per row (no merging), as collect_designs builds them,
    with the row's own requirements (some operators size parts from them)."""
    out = []
    for r in rows:
        found, _ = M.collect_designs([{"id": r["id"], "answer": r.get(key) or "",
                                       "requirements": REQUIREMENTS.get(r["id"]) or {}}])
        out.extend(found)
    return out


@pytest.fixture(scope="module")
def mutation_gold_cases(gold_rows) -> list:
    cases = _tm_cases(gold_rows, "answer")
    assert len(cases) == 48
    return cases


@pytest.fixture(scope="module")
def mutation_model_cases(model_rows) -> list:
    return _tm_cases(model_rows, "content")


# ------------------------------------------------------------------ the list itself

def test_operator_list_is_well_formed():
    names = [op.name for op in M.OPERATORS]
    assert len(names) == len(set(names))
    for op in M.OPERATORS:
        assert op.expect in M.EXPECT_KINDS, op.name
        assert op.what.strip(), op.name
        assert op.repair == (op.expect == M.EXPECT_HIGHER), op.name
        assert M.operator_named(op.name) is op
    with pytest.raises(KeyError):
        M.operator_named("no_such_operator")
    # Every cheat named in the brief is covered, and each stage 1-6 has operators.
    assert {op.expect for op in M.OPERATORS} >= set(M.STOP_STAGES)
    assert len(M.OPERATORS) >= 40
    # The cheats the 2026-11-19 targets and sizes reviews asked for, with the stage that must stop them.
    wanted = {"far_away_thin_part": "build", "far_away_mass": "build", "far_away_recovery": "build",
              "pod_part_far_away": "build", "lug_behind_tail": "build", "closed_tail": "build",
              "zero_width_nose": "limits", "auto_negative": "limits", "giant_packed_chute": "limits",
              "floating_fin_root": "limits", "absurd_rail_button": "limits", "broken_counts": "limits",
              "endless_delay": "limits", "coin_weight": "limits", "absurd_angle_or_offset": "limits",
              "chute_far_too_small": "flight", "chute_too_small_for_prompt": M.EXPECT_LOWER_IN_TARGETS,
              "swap_to_unnamed_motor": M.EXPECT_LOWER_IN_TARGETS,
              "landing_just_under_hard_limit": M.EXPECT_LOWER_IN_TARGETS}
    assert {n: M.operator_named(n).expect for n in wanted} == wanted


def test_every_reference_operator_applies_to_some_val_design(mutation_gold_cases):
    table = default_motor_table()
    for op in REFERENCE_OPS:
        applied = sum(M.apply_operator(op, c.design, table, c.requirements) is not None
                      for c in mutation_gold_cases)
        assert applied >= 3, f"{op.name} applies to {applied} of 48 reference answers"


def test_operators_never_change_their_input(mutation_gold_cases):
    table = default_motor_table()
    case = mutation_gold_cases[0]
    before = json.dumps(case.design, sort_keys=True)
    for op in M.OPERATORS:
        M.apply_operator(op, case.design, table, case.requirements)
        M.apply_untagged(op, case.design, table, case.requirements)
    assert json.dumps(case.design, sort_keys=True) == before


def test_requirement_operators_need_a_landing_number(mutation_gold_cases):
    """The operators that size parachutes from the prompt's landing number do
    not apply without it, and the others do not look at the requirements."""
    table = default_motor_table()
    case = next(c for c in mutation_gold_cases if c.id.startswith("row-016"))
    users = [op for op in M.OPERATORS if op.uses_requirements]
    assert {op.name for op in users} == {"chute_too_small_for_prompt", "landing_just_under_hard_limit"}
    for op in users:
        assert M.apply_operator(op, case.design, table, case.requirements) is not None, op.name
        assert M.apply_operator(op, case.design, table) is None, op.name
        no_landing = {k: v for k, v in case.requirements.items() if k != "landing_ms"}
        assert M.apply_operator(op, case.design, table, no_landing) is None, op.name


def test_the_original_is_rewritten_the_same_way(mutation_gold_cases):
    """The baseline answer is the design re-written by the same code as the
    mutants, so only the mutation differs; it must score as the answer as written."""
    from rocket_reward.scoring import preflight
    for c in mutation_gold_cases[:6]:
        again = preflight(M.mutant_answer(c))
        assert again.passed
        assert json.dumps(again.root, sort_keys=True) == json.dumps({"openrocket": c.design["openrocket"]},
                                                                    sort_keys=True)


# ------------------------------------------------------------------ stages 1-4, no Java

@pytest.mark.parametrize("name", [op.name for op in PREFLIGHT_OPS])
def test_operator_stops_where_it_must(mutation_gold_cases, name):
    op = M.operator_named(name)
    table = default_motor_table()
    applied = 0
    for c in mutation_gold_cases:
        m = M.apply_operator(op, c.design, table, c.requirements)
        if m is None:
            continue
        applied += 1
        got = M.preflight_outcome(M.mutant_answer(c, m), table)
        stage = got.stage if got is not None else "passed stages 1-4"
        known = KNOWN_FINDINGS.get((name, c.id))
        if known:
            assert stage != op.expect, f"{name} on {c.id} now stops at {op.expect}: remove it from KNOWN_FINDINGS"
            continue
        assert stage == op.expect, f"{name} on {c.id}: stopped at {stage}, must stop at {op.expect}; " \
                                   f"{(got.reasons if got else [])[:2]}"
        assert ladder.stage(stage).floor - 1e-9 <= got.score <= ladder.stage(stage).top + 1e-9
    assert applied


def test_repairs_apply_to_real_model_answers_and_get_further(mutation_model_cases):
    table = default_motor_table()
    applied = {op.name: [] for op in REPAIR_OPS}
    for c in mutation_model_cases:
        before = M.preflight_outcome(M.mutant_answer(c), table)
        for op in REPAIR_OPS:
            m = M.apply_operator(op, c.design, table)
            if m is None:
                continue
            applied[op.name].append(c.id)
            after = M.preflight_outcome(M.mutant_answer(c, m), table)
            assert before is not None
            if after is None:      # passes stages 1-4: scores 0.40 or more
                continue
            gained = (ladder.stage_index(after.stage) > ladder.stage_index(before.stage)
                      or (after.stage == before.stage != "motor" and after.score > before.score))
            assert gained, f"{op.name} on {c.id}: {before.stage} {before.score} -> {after.stage} {after.score}"
    assert sorted(applied["repair_motor_spelling"]) == ["row-013-7608fb06", "row-033-adcf6c6e",
                                                        "row-048-e02c5b85"]
    assert sorted(applied["repair_stray_parts"]) == ["row-003-fca5ed76", "row-041-bbcf4448"]


def test_repairs_leave_sound_and_other_answers_alone(mutation_gold_cases):
    table = default_motor_table()
    for op in REPAIR_OPS:
        assert all(M.apply_operator(op, c.design, table, c.requirements) is None
                   for c in mutation_gold_cases), op.name


# ------------------------------------------------------------------ judging and the report

@pytest.mark.parametrize("expect, before, after, ok", [
    ("limits", ("targets", 0.9), ("limits", 0.31), True),
    ("limits", ("targets", 0.9), ("build", 0.41), False),
    ("flight", ("build", 0.42), ("build", 0.41), None),      # the original never reaches flight
    ("build", ("flight", 0.55), ("build", 0.41), True),
    (M.EXPECT_LOWER, ("targets", 0.9), ("targets", 0.8), True),
    (M.EXPECT_LOWER, ("targets", 0.9), ("targets", 0.9), False),
    (M.EXPECT_LOWER, ("flight", 0.55), ("flight", 0.6), None),
    (M.EXPECT_LOWER, ("targets", 0.9), ("flight", 0.6), True),
    (M.EXPECT_LOWER_IN_TARGETS, ("targets", 1.0), ("targets", 0.8), True),
    (M.EXPECT_LOWER_IN_TARGETS, ("targets", 1.0), ("flight", 0.6), False),
    (M.EXPECT_LOWER_IN_TARGETS, ("targets", 1.0), ("targets", 1.0), False),
    (M.EXPECT_LOWER_IN_TARGETS, ("targets", 0.9), ("targets", 0.95), None),   # the original misses a target
    (M.EXPECT_LOWER_IN_TARGETS, ("build", 0.42), ("build", 0.41), None),
    (M.EXPECT_SAME, ("targets", 0.9), ("targets", 0.9), True),
    (M.EXPECT_SAME, ("targets", 0.9), ("targets", 0.91), False),
    (M.EXPECT_SAME_OR_HIGHER, ("targets", 0.9), ("targets", 0.95), True),
    (M.EXPECT_SAME_OR_HIGHER, ("targets", 0.9), ("targets", 0.85), False),
    (M.EXPECT_HIGHER, ("motor", 0.25), ("build", 0.42), True),
    (M.EXPECT_HIGHER, ("motor", 0.25), ("motor", 0.25), False),
    ("limits", ("targets", 0.9), ("dropped", None), False),
])
def test_judge_outcome(expect, before, after, ok):
    got, words = M.judge_outcome(expect, M.Outcome(*before), M.Outcome(*after))
    assert got is ok and words


def test_report_lists_the_cases_that_failed(mutation_gold_cases):
    case = mutation_gold_cases[0]
    cases = [{"design": case.id, "operator": "razor_fins", "expect": "limits", "answer": ""},
             {"design": case.id, "operator": "drag_override", "expect": M.EXPECT_SAME, "answer": ""}]
    outcomes = {case.id: M.Outcome("targets", 1.0),
                f"{case.id}|razor_fins": M.Outcome("targets", 0.99, ["no reason"]),
                f"{case.id}|drag_override": M.Outcome("targets", 1.0)}
    ops = [M.operator_named("razor_fins"), M.operator_named("drag_override")]
    summary = M.summarize_mutations([case], cases, outcomes, ops)
    assert [f["operator"] for f in summary["failures"]] == ["razor_fins"]
    text = M.mutation_report_md(summary, {"score_s": 1.0, "s_per_answer": 0.1}, "Mutation report")
    assert "**razor_fins**" in text and "drag_override" in text and "\r" not in text
    snap = M.expected_snapshot(summary)
    assert snap["cases"][f"{case.id}|razor_fins"] == {"stage": "targets", "score": 0.99}


def test_command_runs_without_java(tmp_path):
    out = tmp_path / "report.md"
    code = M.main(["--answers", str(DATA / "gold_val.jsonl.gz"), "--requirements", str(REQUIREMENTS_PATH),
                   "--designs", "row-016-5851080b,row-022-02cbb911", "--operators", "razor_fins,cut_off,giant_lug",
                   "--out", str(out), "--json", str(tmp_path / "r.json"), "--preflight-only"])
    assert code == 0
    text = out.read_text(encoding="utf-8")
    assert "| razor_fins | limits | 1 | limits 1 |" in text      # row-016 has tube fins only
    assert "| giant_lug | limits | 2 | limits 2 |" in text
    assert json.loads((tmp_path / "r.json").read_text(encoding="utf-8"))["failures"] == []


# ------------------------------------------------------------------ the simulator stages (Java)

@pytest.fixture(scope="module")
def mutation_subset_results():
    from rocket_reward.sim import SimPool
    table = default_motor_table()
    ops = [M.operator_named(n) for n in EXPECTED["operators"]]
    designs, cases, _ = M.mutation_plan(DATA / "gold_val.jsonl.gz", REQUIREMENTS_PATH, ops, table,
                                        DATA / "model_val.jsonl.gz", set(EXPECTED["designs"]))
    with SimPool(4) as pool:
        outcomes = M.score_cases(designs, cases, simulator=pool, table=table)
    return designs, cases, outcomes, ops


@pytest.mark.needs_java
def test_subset_is_the_saved_one(mutation_subset_results):
    designs, cases, outcomes, _ = mutation_subset_results
    assert [d.id for d in designs] == EXPECTED["designs"]
    assert sorted(f"{c['design']}|{c['operator']}" for c in cases) == sorted(EXPECTED["cases"])
    assert all(op.needs_simulator for op in mutation_subset_results[3])


@pytest.mark.needs_java
def test_subset_keeps_its_stages_and_scores(mutation_subset_results):
    _, _, outcomes, _ = mutation_subset_results
    want = {**EXPECTED["originals"], **EXPECTED["cases"]}
    moved = []
    for key, w in want.items():
        got = outcomes[key]
        now = {"stage": got.stage, "score": None if got.score is None else round(got.score, 4)}
        if now != w:
            moved.append(f"{key}: now {now}, was {w} ({got.reasons[:1]})")
    assert not moved, "\n".join(moved)


@pytest.mark.needs_java
def test_ordering_promises(mutation_subset_results):
    """No cheat reaches the targets stage; every "lower" case scores lower;
    ignored cheats score the same; honest edits never score lower; every
    repair scores higher. Known findings must still behave as recorded."""
    designs, cases, outcomes, ops = mutation_subset_results
    summary = M.summarize_mutations(designs, cases, outcomes, ops)
    broken = []
    for row in summary["rows"]:
        key = (row["operator"], row["design"])
        if key in KNOWN_FINDINGS:
            assert row["ok"] is False, f"{key} now does what it must: remove it from KNOWN_FINDINGS"
            continue
        if row["expect"] in M.STOP_STAGES and row["stage"] == "targets":
            broken.append(f"{key}: a cheat reached the targets stage ({row['score']})")
        if row["ok"] is False:
            broken.append(f"{key}: must {row['expect']}, {row['words']}")
    assert not broken, "\n".join(broken)
    judged = [r for r in summary["rows"] if r["ok"] is not None]
    assert {r["expect"] for r in judged} >= {"build", "flight", M.EXPECT_LOWER, M.EXPECT_LOWER_IN_TARGETS,
                                             M.EXPECT_SAME, M.EXPECT_SAME_OR_HIGHER, M.EXPECT_HIGHER}
    repairs = [r for r in summary["rows"] if r["expect"] == M.EXPECT_HIGHER]
    assert len(repairs) == 5 and all(r["score"] > r["before_score"] for r in repairs)
