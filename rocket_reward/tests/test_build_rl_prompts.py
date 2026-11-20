"""The RL prompt builder (tools/build_rl_prompts.py).

Without Java: the rewriting rules on small hand-made prompts (rounding in the
written style for every unit and for spelled-out numbers, spans that stay
valid, kinds that stay the same), the wind fix, families, and the whole
build with a stand-in scorer that reads a recorded simulator reply
(tests/replies.py) through the real targets stage. With Java: a handful of
reference rows rebuilt end to end.
"""
from __future__ import annotations

import json

import pytest

from rocket_reward import ladder, limits
from rocket_reward.records import Requirements, Result
from rocket_reward.targets import check_targets
from rocket_reward.tools import build_rl_prompts as B
from rocket_reward.tools.build_requirements import parse_prompt
from replies import load_reply


def _rewrite(text: str, measured: dict) -> tuple[str, list]:
    """Rewrite `text` and check what must always hold: the new text parses with
    no unplaced number, every span points at its number, and the fields,
    kinds and tolerances are the ones the old text had."""
    old = parse_prompt(text)
    new_text, changes = B.rewrite_prompt(text, old, measured)
    new = parse_prompt(new_text)
    assert not new.unassigned, new.unassigned
    assert B._shape(new) == B._shape(old)
    for it in new.items:
        assert new_text[it.span[0]:it.span[1]] == it.number_text
    return new_text, changes


# ------------------------------------------------------------------ numbers in the written style

@pytest.mark.parametrize("value, decimals, mode, expected", [
    (3.0 * 1.1, 1, "up", 3.3),            # float noise never rounds up a whole step
    (121.79, 1, "up", 121.8), (121.71, 1, "down", 121.7), (2.25, 1, "nearest", 2.3),
    (1611.8, 0, "nearest", 1612.0), (0.0371, 2, "up", 0.04),
])
def test_round_written(value, decimals, mode, expected):
    assert B.round_written(value, decimals, mode) == expected


def test_format_written_keeps_separators_and_decimals():
    assert B.format_written(1612.0, 0, True) == "1,612"
    assert B.format_written(1612.0, 0, False) == "1612"
    assert B.format_written(4.0, 1, False) == "4.0"
    assert B.format_written(12345.67, 2, True) == "12,345.67"


# ------------------------------------------------------------------ rewriting, per unit

@pytest.mark.parametrize("text, measured, expected", [
    # metres, "about": the measured value, decimals as written
    ("Design a rocket that reaches about 489 m apogee.", {"apogee_m": 491.27}, "about 491 m"),
    ("Design a rocket that reaches about 489.2 m apogee.", {"apogee_m": 491.27}, "about 491.3 m"),
    # feet with a thousands separator
    ("I want something that gets to about 1,600 ft.", {"apogee_m": 500.0}, "about 1,640 ft"),
    # km: one more decimal when the written one is too coarse
    ("Requirement set: apogee 2 km; wind 2 m/s.", {"apogee_m": 1730.0}, "apogee 1.7 km"),
    ("Requirement set: apogee 2 km; wind 2 m/s.", {"apogee_m": 1985.0}, "apogee 2 km"),
    # mm, "max": +2% rounded up
    ("Reach about 500 m with a body under 60 mm wide.", {"apogee_m": 500.0, "body_diameter_m": 0.0416},
     "under 43 mm wide"),
    # inches, "max": rounding up to a whole inch would add 15%, so one decimal is written
    ("Reach about 500 m. Under 3 inches wide.", {"apogee_m": 500.0, "body_diameter_m": 2.6 * 0.0254},
     "Under 2.7 inches wide"),
    ("Reach about 500 m, OD 2.5 in maximum.", {"apogee_m": 500.0, "body_diameter_m": 2.05 * 0.0254},
     "OD 2.1 in maximum"),
    ("Reach about 500 m, OD 2.5 in maximum.", {"apogee_m": 500.0, "body_diameter_m": 2.0 * 0.0254},
     "OD 2.04 in maximum"),
    # seconds, "max": +5% rounded up with the written decimal
    ("Reach about 489 m, with total flight time under 117.3 s.", {"apogee_m": 489.0, "flight_time_s": 116.0},
     "under 121.8 s"),
    ("Reach about 489 m and keep the flight near 200 seconds.", {"apogee_m": 489.0, "flight_time_s": 187.4},
     "near 187 seconds"),
    # minutes, "max": 8 min would be 13% headroom, so 7.5
    ("Requirements: apogee 9,700 m; flight time 8 min max.", {"apogee_m": 9677.0, "flight_time_s": 426.0},
     "flight time 7.5 min max"),
    # kg and g, "max": +5% rounded up
    ("Requirements: apogee 441 m; liftoff mass 1.6 kg maximum.", {"apogee_m": 441.0, "mass_kg": 1.52},
     "liftoff mass 1.6 kg maximum"),
    ("Shoot for about 451 m. Under 45 g total.", {"apogee_m": 451.0, "mass_kg": 0.0382}, "Under 41 g"),
    ("Requirements: apogee 441 m; mass 3.7 kg.", {"apogee_m": 441.0, "mass_kg": 3.214}, "mass 3.2 kg"),
    # landing speed, "max": +10% rounded up, never above the hard landing limit
    ("Reach about 489 m and touch down under 3.2 m/s.", {"apogee_m": 489.0, "landing_ms": 3.0}, "under 3.3 m/s"),
    ("Specs: apogee 6,500 m, touchdown 8 m/s max.", {"apogee_m": 6500.0, "landing_ms": 8.6}, "touchdown 9 m/s max"),
    ("Specs: apogee 6,500 m, touchdown 8 m/s max.", {"apogee_m": 6500.0, "landing_ms": 5.1}, "touchdown 6 m/s max"),
    # "min": the measured value minus the margin, rounded down
    ("Reach about 489 m and stay up at least 60 s.", {"apogee_m": 489.0, "flight_time_s": 70.0}, "at least 66 s"),
])
def test_rewrite_in_the_written_style(text, measured, expected):
    new_text, _ = _rewrite(text, measured)
    assert expected in new_text, new_text


@pytest.mark.parametrize("text, measured, expected", [
    ("Reach about 500 m and fly near four minutes.", {"apogee_m": 500.0, "flight_time_s": 237.0},
     "near four minutes"),
    ("Reach about 500 m and fly near four minutes.", {"apogee_m": 500.0, "flight_time_s": 222.0},
     "near 3.7 minutes"),
    ("Reach about 500 m. Stay up around three minutes.", {"apogee_m": 500.0, "flight_time_s": 237.0},
     "around four minutes"),
    ("Reach about 500 m and stay up about two minutes.", {"apogee_m": 500.0, "flight_time_s": 110.0},
     "about 1.8 minutes"),
    ("Reach about 500 m and fly near a minute.", {"apogee_m": 500.0, "flight_time_s": 60.5}, "near a minute"),
    ("Reach about 500 m and fly near a minute.", {"apogee_m": 500.0, "flight_time_s": 51.0}, "near 0.85 minutes"),
    ("Reach about 500 m and stay up about a minute and a half.", {"apogee_m": 500.0, "flight_time_s": 84.0},
     "about 1.4 minutes"),
    ("Reach about 500 m and stay up about a minute and a half.", {"apogee_m": 500.0, "flight_time_s": 90.5},
     "about a minute and a half"),
    ("Reach about 500 m. Two and a half inches across is the max.",
     {"apogee_m": 500.0, "body_diameter_m": 2.45 * 0.0254}, "Two and a half inches across is the max"),
    ("Reach about 500 m. Two and a half inches across is the max.",
     {"apogee_m": 500.0, "body_diameter_m": 3.42 * 0.0254}, "Three and a half inches across is the max"),
    ("Reach about 500 m. Two and a half inches across is the max.",
     {"apogee_m": 500.0, "body_diameter_m": 2.9 * 0.0254}, "3 inches across is the max"),
    ("Reach about 500 m. One inch across at most.", {"apogee_m": 500.0, "body_diameter_m": 0.024},
     "0.97 inches across at most"),
])
def test_spelled_out_numbers(text, measured, expected):
    """A word stays a word when one fits, else it becomes digits; the unit
    follows the new number ("a minute" -> "0.85 minutes")."""
    new_text, _ = _rewrite(text, measured)
    assert expected in new_text, new_text


def test_every_number_of_a_long_prompt_is_rewritten_last_to_first():
    text = ("Requirements: apogee 1,120 m (+/- 5%); touchdown speed 6 m/s maximum; flight time 240 s maximum; "
            "OD 2.5 in maximum; mass 1.4 kg maximum; motors E12 and I115W.")
    measured = {"apogee_m": 1234.5, "landing_ms": 4.4, "flight_time_s": 201.0,
                "body_diameter_m": 0.0559, "mass_kg": 1.21}
    new_text, changes = _rewrite(text, measured)
    assert new_text == ("Requirements: apogee 1,235 m (+/- 5%); touchdown speed 5 m/s maximum; flight time 212 s "
                        "maximum; OD 2.25 in maximum; mass 1.3 kg maximum; motors E12 and I115W.")
    assert [c.field for c in changes] == ["apogee_m", "landing_ms", "flight_time_s", "body_diameter_m", "mass_kg"]
    _, rec = B.record_from_text("r-1", new_text)
    assert rec["apogee_m"] == {"value": 1235.0, "kind": "about", "tol": 0.05}
    assert rec["landing_ms"] == {"value": 5.0, "kind": "max", "tol": 0.0}
    assert rec["mass_kg"]["tol"] == 0.0 and rec["body_diameter_m"]["tol"] == 0.0
    assert rec["motors"] == ["E12", "I115W"]


def test_wind_and_motors_are_never_rewritten():
    text = "Reach about 489 m in about 4.47 m/s wind with an H128W motor."
    new_text, changes = _rewrite(text, {"apogee_m": 500.0, "wind_ms": 9.0})
    assert "4.47 m/s wind" in new_text and "H128W" in new_text and len(changes) == 1


def test_a_stated_field_without_a_measured_value_is_refused():
    text = "Reach about 489 m and weigh under 2 kg."
    with pytest.raises(ValueError, match="mass_kg"):
        B.rewrite_prompt(text, parse_prompt(text), {"apogee_m": 500.0, "mass_kg": None})


@pytest.mark.parametrize("measured", [0.5, 2.0, 7.9, 8.2, 8.99])
def test_a_landing_limit_is_never_above_the_hard_limit(measured):
    text = "Reach about 489 m and touch down under 5 m/s."
    new_text, changes = _rewrite(text, {"apogee_m": 489.0, "landing_ms": measured})
    landing = next(c for c in changes if c.field == "landing_ms")
    assert measured <= landing.new_value <= limits.LANDING_HARD_MAX_MS


def test_apply_changes_checks_the_text_it_replaces():
    ch = B.NumberChange("apogee_m", "about", 6, 9, "489", "500", 489.0, 500.0, 500.0)
    assert B.apply_changes("about 489 m", [ch]) == "about 500 m"
    with pytest.raises(ValueError):
        B.apply_changes("about 488 m", [ch])


# ------------------------------------------------------------------ wind fix and families

def _row(rid, style, prompt, answer="<design>{}</design>", **extra):
    return {"id": rid, "group_id": rid.split("-c")[0], "prompt_style": style, "split": "train",
            "prompt_text": prompt, "source_file": "Kit_29mm.ork", "targets": {"wind_ms": 4.47},
            "messages": [{"role": "system", "content": "SYS"}, {"role": "user", "content": prompt},
                         {"role": "assistant", "content": answer}], **extra}


def test_a_wind_its_siblings_contradict_is_fixed():
    rows = [_row("V4-0099", "original", "Reach about 443 m in about 4.47 m/s wind."),
            _row("V4-0099-casual", "casual", "Aim for about 1,450 ft. Air around 5.9 m/s."),
            _row("V4-0099-engineering", "engineering", "Requirements: apogee 441 m; wind 4.5 m/s.")]
    fixed = B.fix_winds(rows)
    assert list(fixed) == [1]
    assert fixed[1][0] == "Aim for about 1,450 ft. Air around 4.5 m/s."
    # Siblings that disagree too leave it alone.
    rows[2]["prompt_text"] = "Requirements: apogee 441 m; wind 5.9 m/s."
    assert B.fix_winds(rows) == {}


@pytest.mark.parametrize("name, family", [
    ("PML_AMRAAM4-withCPR3000_38mm.ork", "pml amraam4"),
    ("PML_AMRAAM4_29mmMAC.ork", "pml amraam4"),
    ("PML_QuantumLeapCPR3K_54mmConfigurationE.ork", "pml quantumleap"),
    ("PML_QuantumLeapII_54mmConfigurationB.ork", "pml quantumleapii"),
    ("PML_Intruder_29-38ADPTR.ork", "pml intruder"),
    ("PML_SmallEndeavour_38-8.ork", "pml smallendeavour"),
    ("PML_MiniBBXwithTerrierBooster.ork", "pml minibbx"),
    ("PML_1-4Patriot_29mm.ork", "pml 1 4patriot"),
    ("Argonia_2p242OD_K250W_SIM_9-25-24_NoDeploymentBags.ork", "argonia"),
    ("NASA_Rocket_FRR_L1420_Nose_Shift.ork", "nasa rocket"),
    ("NASA_Rocket_V3_L1420.ork", "nasa rocket"),
    ("hyperion_II_v2.ork", "hyperion ii"),
    ("estes_boosted_bertha_1946_mod24.ork", "estes boosted bertha 1946"),
    ("2024_IREC_Subscale.ork", "2024 irec"),
    ("ASTRAwFairing.ork", "astra"),
    ("APEX 30.08.2021.ork", "apex"),
    ("aerotech_arreaux_1.ork", "aerotech arreaux"),
    ("rocket_10.ork", "rocket"),
    ("Base drag hack (short-wide).ork", "base drag hack"),
    ("01.One-stage.ork", "01 one stage"),
])
def test_family_name(name, family):
    assert B.family_name(name) == family


def test_families_also_join_group_ids_and_design_blocks():
    rows = [_row("A-1", "original", "x", answer="<design>1</design>", source_file="Alpha.ork", group_id="G1"),
            _row("A-2", "original", "x", answer="<design>2</design>", source_file="Beta.ork", group_id="G1"),
            _row("A-3", "original", "x", answer="<design>1</design>", source_file="Gamma.ork", group_id="G3"),
            _row("A-4", "original", "x", answer="<design>4</design>", source_file="Delta.ork", group_id="G4")]
    assert B.families(rows) == ["alpha", "alpha", "alpha", "delta"]


# ------------------------------------------------------------------ the whole build, no Java

_SINGLE_STAGE_PROMPT = ("Design a complete model rocket that reaches about 1,400 m apogee, and touches down "
                        "under 4.5 m/s, with total flight time under 85 s, launched in about 2 m/s wind. "
                        "Nothing wider than 210 mm, and under 12 kg.")


class ReplyScorer:
    """Stands in for score_many: every answer is flown as the recorded
    single-stage reply and judged by the real targets stage. An answer that
    holds "STOP-AT-FLIGHT" stops at the flight stage instead."""

    def __init__(self):
        from rocket_reward.scoring import default_motor_table
        self.table = default_motor_table()
        self.calls = 0

    def __call__(self, answers, reqs):
        self.calls += 1
        out = []
        for a, req in zip(answers, reqs):
            if "STOP-AT-FLIGHT" in a:
                out.append(Result(ladder.stage_score("flight", 0.5), "flight", 5, 0.5, reasons=["unstable"]))
                continue
            check = check_targets(load_reply("single_stage"), req, {}, self.table)
            out.append(Result(ladder.stage_score("targets", check.credit), "targets", 7, check.credit,
                              reasons=check.reasons, flags={"stage_info": check.info}))
        return out


def _build_rows():
    return [
        _row("K-1", "original", _SINGLE_STAGE_PROMPT, answer="<design>1</design>", split="train",
             source_file="PML_Kit_29mm.ork"),
        _row("K-1-casual", "casual", "Get to about 4,600 ft and land under 5 m/s, weight around 13 kg.",
             answer="<design>1</design>", split="val", source_file="PML_Kit_29mm.ork"),
        _row("K-2", "original", "Reach about 1,300 m with an H128W motor.", answer="<design>2</design>",
             split="test", source_file="PML_Kit_38mm.ork"),
        _row("K-3", "original", "Reach about 900 m.", answer="<design>STOP-AT-FLIGHT</design>", split="test",
             source_file="Other.ork"),
        _row("K-4", "original", "Reach about 900 m in 3 parts.", answer="<design>4</design>", split="train",
             source_file="Odd.ork"),
    ]


def test_build_keeps_sound_rows_and_says_why_it_drops_the_rest():
    rows = _build_rows()
    scorer = ReplyScorer()
    outcomes = B.build_rows(rows, scorer)
    assert scorer.calls == 2                      # one measuring batch, one proving batch
    by_id = {o.row_id: o for o in outcomes}
    kept = by_id["K-1:original"].kept
    assert kept is not None and kept["reference_score"] >= B.PROOF_MIN
    reply = load_reply("single_stage")
    nominal = reply["flights"][limits.NOMINAL_FLIGHT]
    req = Requirements.from_dict(kept["requirements"])
    assert abs(req.apogee_m.value - nominal["apogee_m"]) <= 1.0        # "about": the measured value
    assert req.flight_time_s.kind == "max" and req.flight_time_s.tol == 0.0
    assert nominal["flight_time_s"] < req.flight_time_s.value <= nominal["flight_time_s"] * 1.10 + 1
    landing = nominal["branches"][0]["landing_vertical_ms"]
    assert landing * 1.1 <= req.landing_ms.value <= landing * 1.2
    assert req.mass_kg.value >= reply["rocket"]["mass_kg"] * 1.05 and req.wind_ms == 2.0
    assert kept["system"] == "SYS" and kept["family"] == "pml kit" and kept["leaks_family"] is False
    assert "1,318 m apogee" in kept["prompt"]

    casual = by_id["K-1-casual:casual"].kept
    assert casual is not None and casual["leaks_family"] is True      # val row, its family has a train row
    assert casual["requirements"]["mass_kg"]["kind"] == "about" and "tol" not in casual["requirements"]["mass_kg"]

    assert by_id["K-2:original"].excluded["code"] == "motor_not_flown"
    assert by_id["K-3:original"].excluded["code"] == "stage_flight"
    assert by_id["K-3:original"].excluded["stage"] == "flight"
    assert by_id["K-4:original"].excluded["code"] == "prompt_unparsed"
    assert all((o.kept is None) != (o.excluded is None) for o in outcomes)


def test_outputs_are_sorted_lf_and_repeatable(tmp_path):
    rows = _build_rows()
    files = []
    for name in ("a", "b"):
        outcomes = B.build_rows(rows, ReplyScorer())
        B.write_outputs(rows, outcomes, tmp_path / name, "meta.jsonl")
        files.append({p.name: p.read_bytes() for p in sorted((tmp_path / name).iterdir())})
    assert files[0] == files[1]
    assert sorted(files[0]) == sorted([B.OUT_PROMPTS, B.OUT_EXCLUDED, B.OUT_README])
    for raw in files[0].values():
        assert b"\r" not in raw
    kept = [json.loads(line) for line in files[0][B.OUT_PROMPTS].decode("utf-8").splitlines()]
    assert [k["id"] for k in kept] == sorted(k["id"] for k in kept)
    assert list(kept[0]) == ["id", "group_id", "family", "split", "prompt_style", "system", "prompt",
                             "requirements", "reference_score", "leaks_family"]
    readme = files[0][B.OUT_README].decode("utf-8")
    assert "Recommended use" in readme and "leaks_family" in readme and "meta.jsonl" in readme


# ------------------------------------------------------------------ end to end with Java

@pytest.mark.needs_java
def test_a_few_reference_rows_rebuild_end_to_end(gold_rows):
    from rocket_reward.scoring import ErrorTracker, score_many
    from rocket_reward.sim import SimPool

    rows = []
    for g in gold_rows[:6]:
        rows.append({"id": g["id"], "group_id": g["id"], "prompt_style": "gold", "split": "val",
                     "prompt_text": g["prompt"], "source_file": g["id"],
                     "messages": [{"role": "system", "content": "SYS"}, {"role": "user", "content": g["prompt"]},
                                  {"role": "assistant", "content": g["answer"]}]})
    with SimPool(4) as pool:
        tracker = ErrorTracker(window=10**6, run=10**6)

        def scorer(answers, reqs):
            return score_many(answers, reqs, simulator=pool, tracker=tracker)

        outcomes = B.build_rows(rows, scorer)
        kept = [o.kept for o in outcomes if o.kept]
        assert len(kept) >= 3, [o.excluded for o in outcomes]
        again = scorer([g["answer"] for g in gold_rows[:6] if any(k["id"] == f"{g['id']}:gold" for k in kept)],
                       [Requirements.from_dict(k["requirements"]) for k in kept])
    for k, res in zip(kept, again):
        assert k["reference_score"] >= B.PROOF_MIN and res.score == k["reference_score"]
        assert parse_prompt(k["prompt"]).usable
    for o in outcomes:
        assert (o.kept is None) != (o.excluded is None)
        if o.excluded:
            assert o.excluded["reason"]
