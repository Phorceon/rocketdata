"""Tests for tools/build_requirements.py: reading requirements out of prompt text."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from rocket_reward.records import Requirements
from rocket_reward.tools import build_requirements as B

# The prompt metadata file (sft_v5_meta_c94ffa5.jsonl) is not in the repository.
# Set ROCKET_REWARD_PROMPT_META to its path to run the tests that read every
# real prompt; without it they are skipped. No machine path is written here.
META = Path(os.environ.get("ROCKET_REWARD_PROMPT_META", "") or "missing-prompt-meta.jsonl")


def one(parsed: B.ParsedPrompt, name: str) -> B.Item:
    found = parsed.by_field(name)
    assert len(found) == 1, f"expected one {name}, got {found}"
    return found[0]


def check_spans(parsed: B.ParsedPrompt) -> None:
    for it in parsed.items:
        if it.form != "none":                # "calm" has no number; its span covers the words
            assert parsed.text[it.span[0]:it.span[1]] == it.number_text
        if it.form == "digits":
            assert float(it.number_text.replace(",", "")) == it.stated
            assert parsed.text[it.unit_span[0]:it.unit_span[1]] == it.unit
            assert it.value == pytest.approx(it.stated * it.factor)
        if it.form == "words":
            unit_text = parsed.text[it.unit_span[0]:it.unit_span[1]]
            # "a minute and a half": number and unit interleave, so both spans cover the phrase
            assert unit_text == it.unit or (it.unit_span == it.span and it.unit in unit_text)
        if it.tol_span:
            assert float(parsed.text[it.tol_span[0]:it.tol_span[1]]) == pytest.approx(it.tol * 100)


# ---------------------------------------------------------------------------
# the three prompt styles


def test_original_style() -> None:
    text = ("Design a complete model rocket that reaches about 489 m apogee, and touches down under "
            "3.2 m/s, with total flight time under 117.3 s, launched in about 2 m/s wind. Provide the "
            "complete hardware design.")
    p = B.parse_prompt(text)
    assert p.unassigned == [] and p.other_asks == []
    assert (one(p, "apogee_m").value, one(p, "apogee_m").kind) == (489.0, "about")
    assert (one(p, "landing_ms").value, one(p, "landing_ms").kind) == (3.2, "max")
    assert (one(p, "flight_time_s").value, one(p, "flight_time_s").kind) == (117.3, "max")
    assert one(p, "wind_ms").value == 2.0
    check_spans(p)


def test_casual_style() -> None:
    p = B.parse_prompt("I want something that gets to about 1,600 ft and drifts down under 3.2 m/s. "
                       "Nothing wider than 70 mm please.")
    assert p.unassigned == []
    apo = one(p, "apogee_m")
    assert apo.value == pytest.approx(487.68) and apo.kind == "about"
    assert apo.number_text == "1,600" and apo.stated == 1600 and apo.unit == "ft"
    dia = one(p, "body_diameter_m")
    assert dia.value == pytest.approx(0.07) and dia.kind == "max"
    check_spans(p)


def test_engineering_style() -> None:
    p = B.parse_prompt("Requirements: apogee 490 m (+/- 5%); touchdown velocity at most 3.2 m/s; "
                       "wind 2 m/s; motor G74W.")
    assert p.unassigned == []
    apo = one(p, "apogee_m")
    assert (apo.value, apo.kind, apo.tol) == (490.0, "about", 0.05)
    assert one(p, "landing_ms").kind == "max"
    assert [i.value for i in p.by_field("motors")] == ["G74W"]
    check_spans(p)


# ---------------------------------------------------------------------------
# units


@pytest.mark.parametrize("text, field, value", [
    ("Reach about 3.5 km.", "apogee_m", 3500.0),
    ("Reach about 1,000 ft.", "apogee_m", 304.8),
    ("Body 2.5 in OD.", "body_diameter_m", 0.0635),
    ("It should fit in a 1 inch tube.", "body_diameter_m", 0.0254),
    ("Flight time 4.5 min.", "flight_time_s", 270.0),
    ("Flight near 16 minutes.", "flight_time_s", 960.0),
    ("Under 80 g total.", "mass_kg", 0.08),
    ("Under 2 lb total.", "mass_kg", 0.90718474),
    ("It has to handle a 12 mph breeze.", "wind_ms", 5.36448),
    ("Wind 18 km/h.", "wind_ms", 5.0),
])
def test_units_convert_to_si(text: str, field: str, value: float) -> None:
    p = B.parse_prompt(text)
    assert p.unassigned == []
    assert one(p, field).value == pytest.approx(value)
    check_spans(p)


def test_spelled_out_numbers() -> None:
    p = B.parse_prompt("Two and a half inches across is the max, and it stays up about a minute and a half.")
    assert one(p, "body_diameter_m").value == pytest.approx(0.0635)
    assert one(p, "body_diameter_m").kind == "max"
    t = one(p, "flight_time_s")
    assert t.value == 90.0 and t.form == "words"
    assert p.text[t.span[0]:t.span[1]] == "a minute and a half"
    p = B.parse_prompt("Keep the flight near four minutes.")
    assert one(p, "flight_time_s").value == 240.0


def test_in_as_a_word_is_not_inches() -> None:
    p = B.parse_prompt("I want it done in 2 minutes.")
    assert one(p, "flight_time_s").value == 120.0
    assert p.by_field("body_diameter_m") == []


# ---------------------------------------------------------------------------
# kinds


@pytest.mark.parametrize("text, field, kind", [
    ("touchdown velocity at most 3.2 m/s", "landing_ms", "max"),
    ("touchdown at 5.7 m/s or less", "landing_ms", "max"),
    ("Descent rate no higher than 6.5 m/s", "landing_ms", "max"),
    ("comes down slower than 8 m/s", "landing_ms", "max"),
    ("let it come down at 5 m/s, tops.", "landing_ms", "max"),
    ("bring it down at 8 m/s.", "landing_ms", "max"),          # a bare landing speed is a limit
    ("Nothing wider than 70 mm.", "body_diameter_m", "max"),
    ("Width around 115 mm tops.", "body_diameter_m", "max"),   # a limit word after beats "around"
    ("mass near 6.5 kg max", "mass_kg", "max"),
    ("weight 2.7 kg or less", "mass_kg", "max"),
    ("diameter up to 250 mm", "body_diameter_m", "max"),
    ("Diameter tops out at 3 inches.", "body_diameter_m", "max"),
    ("I don't want the body over 65 mm.", "body_diameter_m", "max"),
    ("mass at least 2 kg", "mass_kg", "min"),
    ("flight time 200 s or more", "flight_time_s", "min"),
    ("a flight over 60 s", "flight_time_s", "min"),
    ("flight time 300 s", "flight_time_s", "about"),
    ("Diameter 65 mm or so.", "body_diameter_m", "about"),
    ("weigh roughly 1.8 kg", "mass_kg", "about"),
    ("Up to 3.5 km and back.", "apogee_m", "about"),           # "up to" an altitude is a target
])
def test_kind_words(text: str, field: str, kind: str) -> None:
    p = B.parse_prompt(text)
    assert p.unassigned == []
    assert one(p, field).kind == kind


def test_limit_word_after_does_not_cross_a_comma() -> None:
    p = B.parse_prompt("Requirements: apogee 345 m, touchdown at most 6.5 m/s, motor E20W.")
    assert one(p, "apogee_m").kind == "about"
    assert one(p, "landing_ms").kind == "max"


def test_tolerance_without_brackets() -> None:
    p = B.parse_prompt("Spec: apogee 3.5 km +/-5%, descent rate at most 7.2 m/s.")
    apo = one(p, "apogee_m")
    assert (apo.value, apo.tol) == (3500.0, 0.05)
    check_spans(p)


def test_list_items_share_a_limit_word() -> None:
    p = B.parse_prompt("Keep it under 60 mm wide and 0.25 kg all in.")
    assert one(p, "mass_kg").kind == "max"
    p = B.parse_prompt("Stay under 85 seconds, 4.5 inches wide, and 1.8 kg total.")
    assert one(p, "body_diameter_m").kind == "max" and one(p, "mass_kg").kind == "max"
    # A new sentence starts fresh.
    p = B.parse_prompt("Keep the body under 60 mm. 0.25 kg total.")
    assert one(p, "mass_kg").kind == "about"


# ---------------------------------------------------------------------------
# wind and landing


def test_wind_and_landing_words() -> None:
    p = B.parse_prompt("I'd love something climbing to about 6.5 km with a 5.5 m/s breeze, and it "
                       "should touch down at no more than 8 m/s.")
    assert one(p, "wind_ms").value == 5.5
    assert one(p, "landing_ms").value == 8.0
    p = B.parse_prompt("There is almost no wind, about 0.1 m/s.")
    assert one(p, "wind_ms").value == 0.1


def test_calm_means_no_wind() -> None:
    p = B.parse_prompt("Calm-day shot to about 11,100 ft.")
    w = one(p, "wind_ms")
    assert w.value == 0.0 and w.form == "none"
    assert B.to_requirements("x", p)["wind_ms"] == 0.0


# ---------------------------------------------------------------------------
# numbers that cannot be placed


@pytest.mark.parametrize("text, reason", [
    ("Reach about 500 m with 3 fins.", "no unit"),
    ("Reach about 500 m, 20% lighter than last time.", "percentage"),
    ("Reach about 500 m at 30 m/s.", "speed"),
    ("Reach about 500 m on an H128W.", "motor"),
])
def test_unplaced_numbers_are_kept(text: str, reason: str) -> None:
    p = B.parse_prompt(text)
    assert len(p.unassigned) == 1 and reason in p.unassigned[0].reason
    assert not p.usable
    u = p.unassigned[0]
    assert text[u.span[0]:u.span[1]] in u.text
    with pytest.raises(ValueError):
        B.to_requirements("x", p)


def test_tolerance_with_no_target_is_unplaced() -> None:
    p = B.parse_prompt("Requirements: +/- 5% on everything; apogee 500 m.")
    assert [u.reason for u in p.unassigned] == ["a tolerance with no target before it"]


def test_other_asks() -> None:
    p = B.parse_prompt("Reach about 500 m. Keep it under 1.2 m long. Use dual deploy.")
    assert one(p, "apogee_m").value == 500.0
    texts = [a.text for a in p.other_asks]
    assert any("long" in t for t in texts) and any("dual deploy" in t for t in texts)
    assert p.unassigned == []            # the 1.2 belongs to the length ask
    # "flight length" is the flight time, not an ask the record cannot hold
    p = B.parse_prompt("Reach about 500 m, flight length about 2.6 minutes.")
    assert p.other_asks == [] and one(p, "flight_time_s").value == 156.0


def test_motors_named() -> None:
    p = B.parse_prompt("Requirements: apogee 9,700 m; motors 3147L935-P and K627LR.")
    assert [i.value for i in p.by_field("motors")] == ["3147L935-P", "K627LR"]
    p = B.parse_prompt("Requirements: apogee 2,870 m; motor I216-CL(I).")
    assert [i.value for i in p.by_field("motors")] == ["I216-CL(I)"]
    p = B.parse_prompt("Get about 11,600 ft on a 9977M2245-P motor.")
    assert [i.value for i in p.by_field("motors")] == ["9977M2245-P"]
    assert p.unassigned == []


# ---------------------------------------------------------------------------
# records


def test_to_requirements_loads_back() -> None:
    text = ("Requirements: apogee 1,200 m (+/- 5%); touchdown speed 8 m/s maximum; 2 m/s crosswind; "
            "OD 75 mm maximum; mass 2.9 kg maximum; flight time 100 s maximum; motor HP-I500T.")
    d = B.to_requirements("V4-0018-engineering:engineering", B.parse_prompt(text))
    req = Requirements.from_dict(d)
    assert req.apogee_m.value == 1200.0 and req.apogee_m.tol == 0.05
    assert req.body_diameter_m.value == pytest.approx(0.075) and req.body_diameter_m.kind == "max"
    assert req.mass_kg.value == 2.9 and req.flight_time_s.kind == "max"
    assert req.motors == ("HP-I500T",) and req.wind_ms == 2.0
    assert req.to_dict() == d


def test_to_requirements_needs_an_apogee() -> None:
    with pytest.raises(ValueError, match="no apogee"):
        B.to_requirements("x", B.parse_prompt("Land under 5 m/s."))


def test_to_requirements_refuses_two_different_values() -> None:
    with pytest.raises(ValueError, match="more than once"):
        B.to_requirements("x", B.parse_prompt("Apogee 500 m. Apogee 600 m."))


# ---------------------------------------------------------------------------
# checks against the reference rocket


def design(radius: Any = 0.03, nose_aft: Any = 0.03, motor: str = "G74W") -> dict[str, Any]:
    """A tiny design tree: nose cone, one body tube with a motor."""
    return {"openrocket": {"children": [{"rocket": {"children": [
        {"motorconfiguration": {"attrs": {"configid": "c1", "default": True}}},
        {"subcomponents": {"children": [{"stage": {"children": [{"subcomponents": {"children": [
            {"nosecone": {"children": [{"aftradius": {"value": nose_aft}}]}},
            {"bodytube": {"children": [
                {"radius": {"value": radius}},
                {"motormount": {"children": [{"motor": {"attrs": {"configid": "c1"}, "children": [
                    {"designation": {"value": motor}}]}}]}}]}},
        ]}}]}}]}}]}}]}}


def meta_row(prompt: str, style: str = "engineering", tree: Any = None, **targets: float) -> dict[str, Any]:
    answer = ("<thought>\nLiftoff mass is 0.526 kg, so the weight is 5.163 N.\n</thought>\n<design>\n"
              + json.dumps(tree if tree is not None else design()) + "\n</design>")
    base = {"apogee_m": 489.2, "ground_hit_ms": 3.19, "flight_time_s": 117.26, "wind_ms": 2.0}
    base.update(targets)
    return {"id": "V4-0001" + ("" if style == "original" else f"-{style}"), "group_id": "V4-0001",
            "prompt_style": style, "split": "train", "prompt_text": prompt, "targets": base,
            "messages": [{"role": "system", "content": "s"}, {"role": "user", "content": prompt},
                         {"role": "assistant", "content": answer}]}


def test_widest_body_tube_resolves_auto_radius() -> None:
    assert B.widest_body_tube(design(radius=0.03)) == pytest.approx(0.06)
    # "auto 0.025" is a stale default: the tube takes the nose cone's 12.5 mm radius.
    assert B.widest_body_tube(design(radius="auto 0.025", nose_aft=0.0125)) == pytest.approx(0.025)


def test_reference_of_reads_design_and_mass() -> None:
    ref = B.reference_of(meta_row("x"))
    assert ref.motors == ["G74W"] and ref.widest_body_m == pytest.approx(0.06)
    assert ref.liftoff_mass_kg == 0.526


def test_cross_check_agrees_with_a_matching_prompt() -> None:
    prompt = ("Requirements: apogee 490 m (+/- 5%); touchdown velocity at most 3.2 m/s; wind 2 m/s; "
              "OD 60 mm; mass 0.53 kg; motor G74W.")
    problems, notes = B.cross_check(B.parse_prompt(prompt), B.reference_of(meta_row(prompt)))
    assert problems == [] and notes == []


@pytest.mark.parametrize("prompt, word", [
    ("Apogee 600 m.", "apogee"),
    ("Apogee 490 m; touchdown at most 3.0 m/s.", "landing"),
    ("Apogee 490 m; flight time under 100 s.", "flight time"),
    ("Apogee 490 m; wind 5 m/s.", "wind"),
    ("Apogee 490 m; motor H128W.", "motor"),
    ("Apogee 490 m; OD 40 mm max.", "body diameter"),
    ("Apogee 490 m; mass 0.4 kg max.", "mass"),
])
def test_cross_check_finds_contradictions(prompt: str, word: str) -> None:
    problems, _ = B.cross_check(B.parse_prompt(prompt), B.reference_of(meta_row(prompt)))
    assert len(problems) == 1 and problems[0].startswith(word)


def test_about_number_above_reference_is_marked_as_headroom() -> None:
    prompt = "Apogee 490 m; flight time 130 s."
    problems, _ = B.cross_check(B.parse_prompt(prompt), B.reference_of(meta_row(prompt)))
    assert len(problems) == 1 and problems[0].endswith(B.HEADROOM_MARK)


def test_unstated_wind_is_noted() -> None:
    prompt = "Apogee 490 m."
    _, notes = B.cross_check(B.parse_prompt(prompt), B.reference_of(meta_row(prompt, wind_ms=5.36)))
    assert any("wind not stated" in n for n in notes)


# ---------------------------------------------------------------------------
# command line


def test_command_line(tmp_path: Path) -> None:
    rows = [
        meta_row("Design a complete model rocket that reaches about 489 m apogee, and touches down under "
                 "3.2 m/s, with total flight time under 117.3 s, launched in about 2 m/s wind.", "original"),
        meta_row("I want something that gets to about 1,600 ft and drifts down under 3.2 m/s. "
                 "Nothing wider than 70 mm please.", "casual"),
        meta_row("Requirements: apogee 490 m (+/- 5%); touchdown velocity at most 3.2 m/s; wind 2 m/s; "
                 "motor H128W.", "engineering"),
        meta_row("Reach about 500 m with 3 fins.", "engineering"),
    ]
    meta = tmp_path / "meta.jsonl"
    meta.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    out, report = tmp_path / "out.jsonl", tmp_path / "report.md"
    assert B.main(["parse", "--meta", str(meta), "--out", str(out), "--report", str(report)]) == 0
    got = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert len(got) == 4 and len({g["id"] for g in got}) == 4
    for g in got:
        assert {"id", "group_id", "prompt_style", "split", "prompt_text", "requirements", "items",
                "other_asks", "usable", "problems"} <= set(g)
    assert [g["usable"] for g in got] == [True, True, False, False]
    assert got[0]["id"] == "V4-0001:original" and got[1]["id"] == "V4-0001-casual:casual"
    assert "motor H128W" in got[2]["problems"][0]
    assert got[3]["requirements"] is None
    Requirements.from_dict(got[0]["requirements"])
    text = report.read_text(encoding="utf-8")
    for heading in ("## Usable rows by style and split", "## How often each field is stated",
                    "## Every wording pattern", "## Unusable rows", "## Landing limits above 8 m/s"):
        assert heading in text
    assert b"\r\n" not in out.read_bytes() and b"\r\n" not in report.read_bytes()


# ---------------------------------------------------------------------------
# the real prompts


@pytest.mark.skipif(not META.exists(), reason="set ROCKET_REWARD_PROMPT_META to the prompt meta file")
def test_every_real_prompt_is_fully_read() -> None:
    """Every number in every prompt is placed, every span is exact and every
    row with an apogee makes a record that loads back."""
    rows = [json.loads(line) for line in META.read_text(encoding="utf-8").splitlines() if line.strip()]
    for row in rows:
        p = B.parse_prompt(row["prompt_text"])
        assert p.unassigned == [], (row["id"], p.unassigned)
        check_spans(p)
        Requirements.from_dict(B.to_requirements(row["id"], p))


def real_rows() -> list[dict[str, Any]]:
    return [json.loads(line) for line in META.read_text(encoding="utf-8").splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# wordings found when checking the parser against the hand labels


def test_comma_and_field_name_starts_a_new_entry() -> None:
    # V4-0085-casual: the "no more than" belongs to the diameter only.
    p = B.parse_prompt("I'd like it to reach about 2,200 ft, come down under 7.5 m/s, and stay aloft around "
                       "75 seconds. Diameter no more than 110 mm, mass 3.7 kg, and a 2 m/s breeze on the pad.")
    assert one(p, "body_diameter_m").kind == "max"
    assert one(p, "mass_kg").kind == "about"
    # Without a field name the list still shares the limit word.
    p = B.parse_prompt("Hold it near 75 seconds, 4.5 inches across at most, total 1.7 kg.")
    assert one(p, "mass_kg").kind == "max"


def test_and_under_before_a_number_belongs_to_that_number() -> None:
    # V4-0092-casual: "and under" starts the mass limit; the diameter stays "about".
    p = B.parse_prompt("Hit about 1,610 ft, then drift down under 7 m/s over roughly 90 seconds. "
                       "Tube about 4.5 inches across and under 1.5 kg total.")
    assert one(p, "body_diameter_m").kind == "about"
    assert one(p, "mass_kg").kind == "max"
    # At the end of a clause "and under" is the limit of the number before it (V4-0099-casual).
    p = B.parse_prompt("Aim for about 1,450 ft, and keep it under 5.9 m/s on landing. Diameter 110 mm and under.")
    assert one(p, "body_diameter_m").kind == "max"
    p = B.parse_prompt("Diameter 110 mm and under, mass 2 kg.")
    assert one(p, "body_diameter_m").kind == "max" and one(p, "mass_kg").kind == "about"


def test_interleaved_words_are_reported_once() -> None:
    prompt = "Apogee 490 m; stays up about a minute and a half."
    problems, _ = B.cross_check(B.parse_prompt(prompt), B.reference_of(meta_row(prompt, flight_time_s=80.0)))
    assert len(problems) == 1 and "about a minute and a half (= 90 s)" in problems[0]


# ---------------------------------------------------------------------------
# spans: a later step rewrites the numbers in place


def rewrite(text: str, item: B.Item, new_number: str) -> str:
    return text[:item.span[0]] + new_number + text[item.span[1]:]


def new_number_for(item: B.Item) -> tuple[str, float]:
    """A different number written the same way (thousands separators, decimals)."""
    stated = item.stated * 1.1 + 1
    decimals = len(item.number_text.split(".")[1]) if "." in item.number_text else 0
    out = f"{stated:,.{decimals}f}" if "," in item.number_text else f"{stated:.{decimals}f}"
    return out, float(out.replace(",", ""))


def check_rewrite(text: str) -> int:
    """Rewrite each digit number of `text` in place, one at a time, and check that
    the parser reads the new number with the same field and kind, and nothing else
    changes. Returns how many numbers were rewritten."""
    base = B.parse_prompt(text)
    done = 0
    for k, it in enumerate(base.items):
        if it.form != "digits":
            continue
        new_text, new_stated = new_number_for(it)
        changed = rewrite(text, it, new_text)
        again = B.parse_prompt(changed)
        assert again.unassigned == [], (text, changed)
        assert len(again.items) == len(base.items), (text, changed)
        got = again.items[k]
        assert (got.field, got.kind, got.unit, got.tol) == (it.field, it.kind, it.unit, it.tol), (text, changed)
        assert got.stated == new_stated and got.number_text == new_text
        assert changed[got.span[0]:got.span[1]] == new_text
        assert got.value == pytest.approx(new_stated * it.factor)
        for j, other in enumerate(again.items):
            if j != k:
                assert (other.field, other.kind, other.value, other.tol) == (
                    base.items[j].field, base.items[j].kind, base.items[j].value, base.items[j].tol)
        check_spans(again)
        done += 1
    return done


def test_numbers_can_be_rewritten_in_place() -> None:
    text = ("Requirements: apogee 1,200 m (+/- 5%); touchdown speed 8 m/s maximum; flight time 2.4 min or less; "
            "OD 75 mm; mass 2.9 kg maximum; wind 8 mph; motor HP-I500T.")
    assert check_rewrite(text) == 6
    p = B.parse_prompt(text)
    apo = one(p, "apogee_m")
    changed = rewrite(text, apo, "1,315")
    assert "apogee 1,315 m (+/- 5%)" in changed
    assert one(B.parse_prompt(changed), "apogee_m").value == 1315.0


@pytest.mark.skipif(not META.exists(), reason="set ROCKET_REWARD_PROMPT_META to the prompt meta file")
def test_every_real_number_can_be_rewritten_in_place() -> None:
    assert sum(check_rewrite(row["prompt_text"]) for row in real_rows()) > 2000


# ---------------------------------------------------------------------------
# one real prompt per wording (field, kind and the words that set the kind)
# Made from the 594 prompts of sft_v5_meta_c94ffa5.jsonl: the first prompt for
# each distinct (field, kind, cue, form) the parser reports.

PINNED = [
    # (row id, prompt, field, kind, number as written, value in SI units, tol)
    # apogee_m about: N +/- N%
    ('V4-0001-engineering',
     'Requirements: apogee 490 m (+/- 5%); touchdown velocity at most 3.2 m/s; wind 2 m/s; motor G74W.',
     'apogee_m', 'about', '490', 490.0, 0.05),
    # apogee_m about: about N
    ('V4-0001',
     'Design a complete model rocket that reaches about 489 m apogee, and touches down under 3.2 m/s, with total flight time under 117.3 s, launched in about 2 m/s wind. Provide the complete hardware design.',
     'apogee_m', 'about', '489', 489.0, None),
    # apogee_m about: around N
    ('V4-0006-casual',
     'I want it to reach around 10,900 ft and float down at 5.7 m/s or less. Keep the flight near 200 seconds, and the body no wider than 170 mm.',
     'apogee_m', 'about', '10,900', 3322.32, None),
    # apogee_m about: bare
    ('V4-0013-engineering',
     'Spec: apogee 675 m. Descent rate no higher than 6.5 m/s. Total airtime 70 seconds. Motor H148R.',
     'apogee_m', 'about', '675', 675.0, None),
    # apogee_m about: close to N
    ('V4-0139-casual',
     "I'd like something close to 1,480 ft that lands under 4.4 m/s. Wide limit of 70 mm and under 0.45 kg.",
     'apogee_m', 'about', '1,480', 451.104, None),
    # apogee_m about: near N
    ('V4-0068-casual',
     "Something that peaks near 190 ft, drifts down under 6.5 m/s and stays up about 15 seconds. Keep it under 60 mm wide and 0.25 kg all in, and I'll fly it in a 2 m/s breeze.",
     'apogee_m', 'about', '190', 57.912, None),
    # apogee_m about: roughly N
    ('V4-0010-casual',
     'Get me up to roughly 11,600 ft, and I want it coming down slower than 8 m/s. Keep the body under 65 mm across.',
     'apogee_m', 'about', '11,600', 3535.68, None),
    # body_diameter_m about: N or so
    ('V4-0240-casual',
     'I want about 2,345 ft. Landing speed under 8 m/s, flight under 115 s. Diameter 65 mm or so, under 1 kg.',
     'body_diameter_m', 'about', '65', 0.065, None),
    # body_diameter_m about: about N
    ('V4-0092-casual',
     'Hit about 1,610 ft, then drift down under 7 m/s over roughly 90 seconds. Tube about 4.5 inches across and under 1.5 kg total.',
     'body_diameter_m', 'about', '4.5', 0.1143, None),
    # body_diameter_m about: around N
    ('V4-0040-casual',
     'Something that hits roughly 3,300 ft and drops back to earth under 5 m/s. Keep it around 90 mm wide, under 4.2 kg, and make sure the flight wraps up in about 2 minutes.',
     'body_diameter_m', 'about', '90', 0.09, None),
    # body_diameter_m about: bare
    ('V4-0016-casual',
     'Give me a little rocket that tops out around 125 ft and drifts down under 5.0 m/s. It should fit in a 1 inch tube, weigh about 0.09 kg, and be done in 13 seconds.',
     'body_diameter_m', 'about', '1', 0.0254, None),
    # body_diameter_m about: bare (words)
    ('V4-0232-casual',
     'Aim for 660 ft, with a 6 m/s touchdown limit. Just one inch wide, around 90 g, 55 seconds of flight, and an 8 mph breeze.',
     'body_diameter_m', 'about', 'one', 0.0254, None),
    # body_diameter_m about: near N
    ('V4-0105-casual',
     'Target roughly 5,700 ft, come down at 7.8 m/s at most, and keep the body near 80 mm. About 1.9 kg total weight, and the flight should take around 4 minutes.',
     'body_diameter_m', 'about', '80', 0.08, None),
    # body_diameter_m about: roughly N
    ('V4-0195-casual',
     "Something that goes around 8,680 ft, comes down at 6.9 m/s or less. I'll be flying in an 8 mph wind, body roughly 4 inches across, total weight about 7.5 kg.",
     'body_diameter_m', 'about', '4', 0.1016, None),
    # body_diameter_m max: (shares) N
    ('V4-0147-casual',
     'Shoot for about 2,220 ft, landing under 7 m/s. Keep it under 3.2 kg and 120 mm wide.',
     'body_diameter_m', 'max', '120', 0.12, None),
    # body_diameter_m max: N and under
    ('V4-0099-casual',
     'Aim for about 1,450 ft, and keep it under 5.9 m/s on landing. Air around 5.9 m/s. Diameter 110 mm and under.',
     'body_diameter_m', 'max', '110', 0.11, None),
    # body_diameter_m max: N at most
    ('V4-0143-casual',
     'Target about 805 ft, landing under 4.9 m/s, and a flight around 70 seconds. Keep it 30 mm wide at most, 150 g max.',
     'body_diameter_m', 'max', '30', 0.03, None),
    # body_diameter_m max: N at most (words)
    ('V4-0158-casual',
     'Something that climbs to about 165 ft, lands under 5 m/s, and flies roughly 18 seconds. One inch across at most, 75 g max.',
     'body_diameter_m', 'max', 'One', 0.0254, None),
    # body_diameter_m max: N is my max
    ('V4-0025-casual',
     "Shoot for about 9,400 ft up and have it land at no more than 8 m/s. A 2 inch body is my max, it should weigh roughly 1.8 kg, and I'd like the whole thing done in 2.5 minutes, with a 9 mph wind blowing.",
     'body_diameter_m', 'max', '2', 0.0508, None),
    # body_diameter_m max: N is the max (words)
    ('V4-0067-casual',
     'Make it reach roughly 190 ft, then float down at 6.5 m/s or less. Two and a half inches across is the max, it should weigh around 0.28 kg, and I want it done in 15 seconds with a 2 m/s wind.',
     'body_diameter_m', 'max', 'Two and a half', 0.0635, None),
    # body_diameter_m max: N max
    ('V4-0003-engineering',
     'Requirements: apogee 1,600 m (+/- 5%); touchdown velocity no more than 5.6 m/s; flight time 275 s or less; airframe OD 110 mm max; wind 2 m/s; motor J315R.',
     'body_diameter_m', 'max', '110', 0.11, None),
    # body_diameter_m max: N maximum
    ('V4-0006-engineering',
     'Requirements: apogee 3,320 m (+/- 5%); touchdown velocity 5.7 m/s maximum; flight time 200 s maximum; OD 170 mm maximum; liftoff mass 23.4 kg maximum; motor M2000R.',
     'body_diameter_m', 'max', '170', 0.17, None),
    # body_diameter_m max: N or less
    ('V4-0027-casual',
     "I'd like a rocket that climbs to about 12,300 ft. Keep the airframe at 50 mm or less and it should land under 7.5 m/s.",
     'body_diameter_m', 'max', '50', 0.05, None),
    # body_diameter_m max: N or narrower
    ('V4-0163-casual',
     'Get to around 390 ft, drift down under 6.0 m/s, flight about 32 seconds. Wind is an 8 mph breeze. Keep the body 50 mm or narrower and total under 150 g.',
     'body_diameter_m', 'max', '50', 0.05, None),
    # body_diameter_m max: N or thinner
    ('V4-0074-casual',
     "Shoot for around 1,950 ft and let it come down at 5 m/s, tops. Body should be 65 mm or thinner, it weighs about 1.9 kg, and I'd like it finished in 70 seconds.",
     'body_diameter_m', 'max', '65', 0.065, None),
    # body_diameter_m max: N or under
    ('V4-0119-casual',
     'Something around 1,510 ft that lands under 7 m/s. Keep the diameter at 65 mm or under and the weight below 0.7 kg.',
     'body_diameter_m', 'max', '65', 0.065, None),
    # body_diameter_m max: N tops
    ('V4-0013-casual',
     'Something that gets up to about 2,200 ft and floats down under 7 m/s. Width around 115 mm tops, and the whole thing under 3 kg.',
     'body_diameter_m', 'max', '115', 0.115, None),
    # body_diameter_m max: N tops (words)
    ('V4-0162-casual',
     'It should go about 1,250 ft, come down at 5 m/s, and handle an 8 mph breeze. One inch diameter tops, around 70 g, and the whole flight around 110 seconds.',
     'body_diameter_m', 'max', 'One', 0.0254, None),
    # body_diameter_m max: as wide as N
    ('V4-0097-casual',
     "Something that goes to about 5,790 ft and sets down gently under 4.5 m/s. I'd like it done in roughly 2.5 minutes. The body can be as wide as 7 inches, and the total weight should be under 19.5 kg.",
     'body_diameter_m', 'max', '7', 0.1778, None),
    # body_diameter_m max: at most N
    ('V4-0049-engineering',
     'Spec: apogee 8,630 m (+/- 5%); touchdown speed at most 8 m/s; flight time at most 420 s; launch wind 5.4 m/s; outer diameter at most 65 mm; liftoff mass at most 8.2 kg; motors 3147L935-P and K627LR.',
     'body_diameter_m', 'max', '65', 0.065, None),
    # body_diameter_m max: just under N
    ('V4-0178-casual',
     'Calm air launch, I want about 330 ft up and a gentle landing at 4.8 m/s or less. Just under 1.8 inches across and around 0.2 kg, and the flight should take about 30 seconds.',
     'body_diameter_m', 'max', '1.8', 0.04572, None),
    # body_diameter_m max: limit of N
    ('V4-0139-casual',
     "I'd like something close to 1,480 ft that lands under 4.4 m/s. Wide limit of 70 mm and under 0.45 kg.",
     'body_diameter_m', 'max', '70', 0.07, None),
    # body_diameter_m max: max N
    ('V4-0016-engineering',
     'Spec: apogee 38.5 m (+/- 5%), landing speed under 5.0 m/s, total time up to 13 s, body diameter max 1 in, motor A8.',
     'body_diameter_m', 'max', '1', 0.0254, None),
    # body_diameter_m max: no bigger than N
    ('V4-0095-casual',
     'Want about 5,400 ft. Descent under 7 m/s, and the diameter no bigger than 180 mm. Weight should stay below 18 kg.',
     'body_diameter_m', 'max', '180', 0.18, None),
    # body_diameter_m max: no more than N
    ('V4-0002-engineering',
     'Requirements: apogee 1,400 m (+/- 5%); touchdown velocity at most 5.6 m/s; flight time 300 s; airframe OD no more than 110 mm; motor G80T.',
     'body_diameter_m', 'max', '110', 0.11, None),
    # body_diameter_m max: no wider than N
    ('V4-0006-casual',
     'I want it to reach around 10,900 ft and float down at 5.7 m/s or less. Keep the flight near 200 seconds, and the body no wider than 170 mm.',
     'body_diameter_m', 'max', '170', 0.17, None),
    # body_diameter_m max: nothing wider than N
    ('V4-0001-casual',
     'I want something that gets to about 1,600 ft and drifts down under 3.2 m/s. Nothing wider than 70 mm please.',
     'body_diameter_m', 'max', '70', 0.07, None),
    # body_diameter_m max: over N
    ('V4-0050-casual',
     "I want to hit roughly 19,000 ft and it has to come down under 8 m/s. Launch wind is about 5.4 m/s and I don't want the body over 65 mm.",
     'body_diameter_m', 'max', '65', 0.065, None),
    # body_diameter_m max: tops out at N
    ('V4-0055-casual',
     "I'd love something climbing to about 6.5 km with a 5.5 m/s breeze, and it should touch down at no more than 8 m/s. Diameter tops out at 3 inches, mass around 10.5 kg, and the total time is 10 minutes or so.",
     'body_diameter_m', 'max', '3', 0.0762, None),
    # body_diameter_m max: under N
    ('V4-0002-casual',
     "I'd like something that climbs to about 4,600 ft and drifts down under 5.6 m/s. Keep the body under 110 mm across, and let the flight run around 300 seconds.",
     'body_diameter_m', 'max', '110', 0.11, None),
    # body_diameter_m max: up to N
    ('V4-0040-engineering',
     'Spec: apogee 1,000 m (+/- 5%), touchdown speed at most 5 m/s, flight duration 120 s, OD up to 90 mm, mass 4 kg or less, motor I216.',
     'body_diameter_m', 'max', '90', 0.09, None),
    # body_diameter_m max: within N
    ('V4-0060-casual',
     'Get me to about 13,000 ft, with a 2 m/s breeze, and bring it down at 8 m/s or under. Body should stay within 5 inches across, the whole thing around 12.5 kg, and the flight to about 4.5 minutes.',
     'body_diameter_m', 'max', '5', 0.127, None),
    # flight_time_s about: (shares) N
    ('V4-0232-casual',
     'Aim for 660 ft, with a 6 m/s touchdown limit. Just one inch wide, around 90 g, 55 seconds of flight, and an 8 mph breeze.',
     'flight_time_s', 'about', '55', 55.0, None),
    # flight_time_s about: N or so
    ('V4-0055-casual',
     "I'd love something climbing to about 6.5 km with a 5.5 m/s breeze, and it should touch down at no more than 8 m/s. Diameter tops out at 3 inches, mass around 10.5 kg, and the total time is 10 minutes or so.",
     'flight_time_s', 'about', '10', 600.0, None),
    # flight_time_s about: about N
    ('V4-0040-casual',
     'Something that hits roughly 3,300 ft and drops back to earth under 5 m/s. Keep it around 90 mm wide, under 4.2 kg, and make sure the flight wraps up in about 2 minutes.',
     'flight_time_s', 'about', '2', 120.0, None),
    # flight_time_s about: about N (words)
    ('V4-0228-casual',
     'Get it near 6,780 ft, touch down at 6.3 m/s or less, aloft about two minutes. Body up to 6.5 inches wide, weight near 20.5 kg max.',
     'flight_time_s', 'about', 'two', 120.0, None),
    # flight_time_s about: around N
    ('V4-0002-casual',
     "I'd like something that climbs to about 4,600 ft and drifts down under 5.6 m/s. Keep the body under 110 mm across, and let the flight run around 300 seconds.",
     'flight_time_s', 'about', '300', 300.0, None),
    # flight_time_s about: around N (words)
    ('V4-0107-casual',
     "I'm after roughly 3,680 ft with a gentle landing at 6 m/s or less. Keep the time around four minutes and the frame about 2.5 inches wide. Under 1.4 kg, please.",
     'flight_time_s', 'about', 'four', 240.0, None),
    # flight_time_s about: bare
    ('V4-0002-engineering',
     'Requirements: apogee 1,400 m (+/- 5%); touchdown velocity at most 5.6 m/s; flight time 300 s; airframe OD no more than 110 mm; motor G80T.',
     'flight_time_s', 'about', '300', 300.0, None),
    # flight_time_s about: close to N
    ('V4-0153-casual',
     "Shoot for around 3,100 ft and bring it down at 8 m/s. I'd like the body about 2 inches around, weigh something like 750 g, and last close to 165 seconds.",
     'flight_time_s', 'about', '165', 165.0, None),
    # flight_time_s about: near N
    ('V4-0006-casual',
     'I want it to reach around 10,900 ft and float down at 5.7 m/s or less. Keep the flight near 200 seconds, and the body no wider than 170 mm.',
     'flight_time_s', 'about', '200', 200.0, None),
    # flight_time_s about: near N (words)
    ('V4-0056-casual',
     'I want to reach about 16,100 ft, come down under 8 m/s, and keep the flight near four minutes. The body can be up to 90 mm across, and the mass should stay at 10.6 kg or below.',
     'flight_time_s', 'about', 'four', 240.0, None),
    # flight_time_s about: roughly N
    ('V4-0088-casual',
     'Can it hit about 2,400 ft and come back down at 6.8 m/s or below? Keep it around 3.5 inches across and 1.1 kg, and I want the flight to last roughly 2.3 minutes.',
     'flight_time_s', 'about', '2.3', 138.0, None),
    # flight_time_s max: N max
    ('V4-0048-engineering',
     'Requirements: apogee 9,700 m (+/- 5%); touchdown velocity 8 m/s max; flight time 8 min max; body diameter 60 mm; mass 9.5 kg; wind 5.4 m/s; motors 3147L935-P and K627LR.',
     'flight_time_s', 'max', '8', 480.0, None),
    # flight_time_s max: N maximum
    ('V4-0006-engineering',
     'Requirements: apogee 3,320 m (+/- 5%); touchdown velocity 5.7 m/s maximum; flight time 200 s maximum; OD 170 mm maximum; liftoff mass 23.4 kg maximum; motor M2000R.',
     'flight_time_s', 'max', '200', 200.0, None),
    # flight_time_s max: N or less
    ('V4-0003-engineering',
     'Requirements: apogee 1,600 m (+/- 5%); touchdown velocity no more than 5.6 m/s; flight time 275 s or less; airframe OD 110 mm max; wind 2 m/s; motor J315R.',
     'flight_time_s', 'max', '275', 275.0, None),
    # flight_time_s max: at most N
    ('V4-0027-engineering',
     'Requirement set: apogee 3.74 km; flight time at most 2.6 min; body diameter 48 mm max; wind 2 m/s; motor J530.',
     'flight_time_s', 'max', '2.6', 156.0, None),
    # flight_time_s max: under N
    ('V4-0001',
     'Design a complete model rocket that reaches about 489 m apogee, and touches down under 3.2 m/s, with total flight time under 117.3 s, launched in about 2 m/s wind. Provide the complete hardware design.',
     'flight_time_s', 'max', '117.3', 117.3, None),
    # flight_time_s max: up to N
    ('V4-0016-engineering',
     'Spec: apogee 38.5 m (+/- 5%), landing speed under 5.0 m/s, total time up to 13 s, body diameter max 1 in, motor A8.',
     'flight_time_s', 'max', '13', 13.0, None),
    # flight_time_s max: within N
    ('V4-0003-casual',
     'I want something that gets up to about 5,250 ft and comes down under 5.6 m/s. Keep the body under 110 mm across, and the whole flight should wrap up within 280 seconds. It will be flying in a 2 m/s breeze.',
     'flight_time_s', 'max', '280', 280.0, None),
    # landing_ms max: N at most
    ('V4-0105-casual',
     'Target roughly 5,700 ft, come down at 7.8 m/s at most, and keep the body near 80 mm. About 1.9 kg total weight, and the flight should take around 4 minutes.',
     'landing_ms', 'max', '7.8', 7.8, None),
    # landing_ms max: N cap
    ('V4-0188-casual',
     "Shoot for about 590 ft with a 5.5 m/s landing cap. It's a 1 inch rocket around 60 g, and the flight should run about 55 seconds in an 8 mph wind.",
     'landing_ms', 'max', '5.5', 5.5, None),
    # landing_ms max: N limit
    ('V4-0232-casual',
     'Aim for 660 ft, with a 6 m/s touchdown limit. Just one inch wide, around 90 g, 55 seconds of flight, and an 8 mph breeze.',
     'landing_ms', 'max', '6', 6.0, None),
    # landing_ms max: N max
    ('V4-0048-engineering',
     'Requirements: apogee 9,700 m (+/- 5%); touchdown velocity 8 m/s max; flight time 8 min max; body diameter 60 mm; mass 9.5 kg; wind 5.4 m/s; motors 3147L935-P and K627LR.',
     'landing_ms', 'max', '8', 8.0, None),
    # landing_ms max: N maximum
    ('V4-0006-engineering',
     'Requirements: apogee 3,320 m (+/- 5%); touchdown velocity 5.7 m/s maximum; flight time 200 s maximum; OD 170 mm maximum; liftoff mass 23.4 kg maximum; motor M2000R.',
     'landing_ms', 'max', '5.7', 5.7, None),
    # landing_ms max: N or below
    ('V4-0088-casual',
     'Can it hit about 2,400 ft and come back down at 6.8 m/s or below? Keep it around 3.5 inches across and 1.1 kg, and I want the flight to last roughly 2.3 minutes.',
     'landing_ms', 'max', '6.8', 6.8, None),
    # landing_ms max: N or less
    ('V4-0006-casual',
     'I want it to reach around 10,900 ft and float down at 5.7 m/s or less. Keep the flight near 200 seconds, and the body no wider than 170 mm.',
     'landing_ms', 'max', '5.7', 5.7, None),
    # landing_ms max: N or lower
    ('V4-0215-casual',
     'Get about 11,600 ft on a 9977M2245-P motor, and bring it down at 6 m/s or lower. Body 160 mm across, mass near 35 kg, and the flight should run about 4 minutes.',
     'landing_ms', 'max', '6', 6.0, None),
    # landing_ms max: N or slower
    ('V4-0142-casual',
     "I'd like it to hit around 880 ft, touch down at 5 m/s or slower, and hang in the air about 80 seconds. Keep it around 1.2 in across and roughly 0.15 kg.",
     'landing_ms', 'max', '5', 5.0, None),
    # landing_ms max: N or under
    ('V4-0060-casual',
     'Get me to about 13,000 ft, with a 2 m/s breeze, and bring it down at 8 m/s or under. Body should stay within 5 inches across, the whole thing around 12.5 kg, and the flight to about 4.5 minutes.',
     'landing_ms', 'max', '8', 8.0, None),
    # landing_ms max: N tops
    ('V4-0074-casual',
     "Shoot for around 1,950 ft and let it come down at 5 m/s, tops. Body should be 65 mm or thinner, it weighs about 1.9 kg, and I'd like it finished in 70 seconds.",
     'landing_ms', 'max', '5', 5.0, None),
    # landing_ms max: at most N
    ('V4-0001-engineering',
     'Requirements: apogee 490 m (+/- 5%); touchdown velocity at most 3.2 m/s; wind 2 m/s; motor G74W.',
     'landing_ms', 'max', '3.2', 3.2, None),
    # landing_ms max: bare N (landing is a limit)
    ('V4-0153-casual',
     "Shoot for around 3,100 ft and bring it down at 8 m/s. I'd like the body about 2 inches around, weigh something like 750 g, and last close to 165 seconds.",
     'landing_ms', 'max', '8', 8.0, None),
    # landing_ms max: below N
    ('V4-0066-engineering',
     'Requirements: apogee 308 m, touchdown below 5.5 m/s, airtime 55 s, body diameter 65 mm, motor G40W.',
     'landing_ms', 'max', '5.5', 5.5, None),
    # landing_ms max: limit of N
    ('V4-0260-casual',
     'Shoot for about 1,300 ft with a hard limit of 8 m/s on landing. I want about 65 seconds of flight, body 2.5 inches across, and under 0.9 kg.',
     'landing_ms', 'max', '8', 8.0, None),
    # landing_ms max: max N
    ('V4-0060-engineering',
     'Requirements: apogee 3,970 m (+/- 5%); touchdown speed max 8 m/s; flight time 270 s; OD 5 in; mass 12.5 kg; wind 2 m/s; motor L952W.',
     'landing_ms', 'max', '8', 8.0, None),
    # landing_ms max: no faster than N
    ('V4-0121-casual',
     'Aim for about 790 ft and a touchdown no faster than 8 m/s. It should be near 2.5 inches wide, weigh about 0.75 kg, and finish in roughly 42 seconds.',
     'landing_ms', 'max', '8', 8.0, None),
    # landing_ms max: no greater than N
    ('V4-0035-engineering',
     'Target apogee 451 m. Touchdown speed no greater than 5 m/s. Flight time 120 s. Motor F50T.',
     'landing_ms', 'max', '5', 5.0, None),
    # landing_ms max: no higher than N
    ('V4-0013-engineering',
     'Spec: apogee 675 m. Descent rate no higher than 6.5 m/s. Total airtime 70 seconds. Motor H148R.',
     'landing_ms', 'max', '6.5', 6.5, None),
    # landing_ms max: no more than N
    ('V4-0003-engineering',
     'Requirements: apogee 1,600 m (+/- 5%); touchdown velocity no more than 5.6 m/s; flight time 275 s or less; airframe OD 110 mm max; wind 2 m/s; motor J315R.',
     'landing_ms', 'max', '5.6', 5.6, None),
    # landing_ms max: slower than N
    ('V4-0010-casual',
     'Get me up to roughly 11,600 ft, and I want it coming down slower than 8 m/s. Keep the body under 65 mm across.',
     'landing_ms', 'max', '8', 8.0, None),
    # landing_ms max: softer than N
    ('V4-0244-casual',
     'Get it up around 1,145 ft, and make the landing softer than 7 m/s. Wind around 2 m/s. Max body 110 mm, under 4.2 kg.',
     'landing_ms', 'max', '7', 7.0, None),
    # landing_ms max: under N
    ('V4-0001',
     'Design a complete model rocket that reaches about 489 m apogee, and touches down under 3.2 m/s, with total flight time under 117.3 s, launched in about 2 m/s wind. Provide the complete hardware design.',
     'landing_ms', 'max', '3.2', 3.2, None),
    # mass_kg about: (shares) N
    ('V4-0088-casual',
     'Can it hit about 2,400 ft and come back down at 6.8 m/s or below? Keep it around 3.5 inches across and 1.1 kg, and I want the flight to last roughly 2.3 minutes.',
     'mass_kg', 'about', '1.1', 1.1, None),
    # mass_kg about: about N
    ('V4-0016-casual',
     'Give me a little rocket that tops out around 125 ft and drifts down under 5.0 m/s. It should fit in a 1 inch tube, weigh about 0.09 kg, and be done in 13 seconds.',
     'mass_kg', 'about', '0.09', 0.09, None),
    # mass_kg about: around N
    ('V4-0055-casual',
     "I'd love something climbing to about 6.5 km with a 5.5 m/s breeze, and it should touch down at no more than 8 m/s. Diameter tops out at 3 inches, mass around 10.5 kg, and the total time is 10 minutes or so.",
     'mass_kg', 'about', '10.5', 10.5, None),
    # mass_kg about: bare
    ('V4-0048-engineering',
     'Requirements: apogee 9,700 m (+/- 5%); touchdown velocity 8 m/s max; flight time 8 min max; body diameter 60 mm; mass 9.5 kg; wind 5.4 m/s; motors 3147L935-P and K627LR.',
     'mass_kg', 'about', '9.5', 9.5, None),
    # mass_kg about: near N
    ('V4-0049-casual',
     'Aim for roughly 28,300 ft, drift down under 8 m/s, and keep the flight going about 7 minutes. Body width under 65 mm, weight near 8.2 kg, and it has to handle a 12 mph breeze.',
     'mass_kg', 'about', '8.2', 8.2, None),
    # mass_kg about: roughly N
    ('V4-0025-casual',
     "Shoot for about 9,400 ft up and have it land at no more than 8 m/s. A 2 inch body is my max, it should weigh roughly 1.8 kg, and I'd like the whole thing done in 2.5 minutes, with a 9 mph wind blowing.",
     'mass_kg', 'about', '1.8', 1.8, None),
    # mass_kg about: something like N
    ('V4-0153-casual',
     "Shoot for around 3,100 ft and bring it down at 8 m/s. I'd like the body about 2 inches around, weigh something like 750 g, and last close to 165 seconds.",
     'mass_kg', 'about', '750', 0.75, None),
    # mass_kg max: (shares) N
    ('V4-0068-casual',
     "Something that peaks near 190 ft, drifts down under 6.5 m/s and stays up about 15 seconds. Keep it under 60 mm wide and 0.25 kg all in, and I'll fly it in a 2 m/s breeze.",
     'mass_kg', 'max', '0.25', 0.25, None),
    # mass_kg max: N at most
    ('V4-0265-casual',
     'Get it to roughly 925 ft with a 6.5 m/s touchdown or less. Flight about one minute, body up to 95 mm across, and weight 2 kg at most.',
     'mass_kg', 'max', '2', 2.0, None),
    # mass_kg max: N max
    ('V4-0025-engineering',
     'Requirements: apogee 2,870 m (+/- 5%); touchdown under 8 m/s; flight time 2.4 min or less; airframe OD 50 mm; mass 1.8 kg max; wind 4 m/s; motor I216-CL(I).',
     'mass_kg', 'max', '1.8', 1.8, None),
    # mass_kg max: N maximum
    ('V4-0006-engineering',
     'Requirements: apogee 3,320 m (+/- 5%); touchdown velocity 5.7 m/s maximum; flight time 200 s maximum; OD 170 mm maximum; liftoff mass 23.4 kg maximum; motor M2000R.',
     'mass_kg', 'max', '23.4', 23.4, None),
    # mass_kg max: N or below
    ('V4-0056-casual',
     'I want to reach about 16,100 ft, come down under 8 m/s, and keep the flight near four minutes. The body can be up to 90 mm across, and the mass should stay at 10.6 kg or below.',
     'mass_kg', 'max', '10.6', 10.6, None),
    # mass_kg max: N or less
    ('V4-0040-engineering',
     'Spec: apogee 1,000 m (+/- 5%), touchdown speed at most 5 m/s, flight duration 120 s, OD up to 90 mm, mass 4 kg or less, motor I216.',
     'mass_kg', 'max', '4', 4.0, None),
    # mass_kg max: N or lighter
    ('V4-0150-casual',
     'Small one, about 187 ft high, landing under 6 m/s, flight near 16 seconds. Keep it 32 mm across and 130 g or lighter.',
     'mass_kg', 'max', '130', 0.13, None),
    # mass_kg max: N tops
    ('V4-0130-casual',
     'Shoot for about 2,470 ft, come down under 5.8 m/s, and let it ride about 3 minutes. Diameter 95 mm max, weight 1 kg tops.',
     'mass_kg', 'max', '1', 1.0, None),
    # mass_kg max: at most N
    ('V4-0049-engineering',
     'Spec: apogee 8,630 m (+/- 5%); touchdown speed at most 8 m/s; flight time at most 420 s; launch wind 5.4 m/s; outer diameter at most 65 mm; liftoff mass at most 8.2 kg; motors 3147L935-P and K627LR.',
     'mass_kg', 'max', '8.2', 8.2, None),
    # mass_kg max: below N
    ('V4-0046-casual',
     'I want about 4,300 ft up, with a gentle landing under 6 m/s. Keep the body near 220 mm or less and the total weight below 14 kg.',
     'mass_kg', 'max', '14', 14.0, None),
    # mass_kg max: no heavier than N
    ('V4-0307-casual',
     'Up to about 2,310 ft, come down at 7.5 m/s or less, and fly about two minutes. Under 3 inches wide, and no heavier than 1.6 kg.',
     'mass_kg', 'max', '1.6', 1.6, None),
    # mass_kg max: no more than N
    ('V4-0045-casual',
     'Something that goes up around 2,120 ft, lands soft at under 6 m/s, and weighs no more than 5.5 kg.',
     'mass_kg', 'max', '5.5', 5.5, None),
    # mass_kg max: under N
    ('V4-0013-casual',
     'Something that gets up to about 2,200 ft and floats down under 7 m/s. Width around 115 mm tops, and the whole thing under 3 kg.',
     'mass_kg', 'max', '3', 3.0, None),
    # motors named: motor (designation)
    ('V4-0001-engineering',
     'Requirements: apogee 490 m (+/- 5%); touchdown velocity at most 3.2 m/s; wind 2 m/s; motor G74W.',
     'motors', 'named', 'G74W', 'G74W', None),
    # wind_ms about: about N
    ('V4-0001',
     'Design a complete model rocket that reaches about 489 m apogee, and touches down under 3.2 m/s, with total flight time under 117.3 s, launched in about 2 m/s wind. Provide the complete hardware design.',
     'wind_ms', 'about', '2', 2.0, None),
    # wind_ms about: around N
    ('V4-0057-casual',
     'Get it up to about 20,600 ft and let it drift down slower than 8 m/s. Wind around 5.4 m/s. Body no wider than 90 mm.',
     'wind_ms', 'about', '5.4', 5.4, None),
    # wind_ms about: bare
    ('V4-0001-engineering',
     'Requirements: apogee 490 m (+/- 5%); touchdown velocity at most 3.2 m/s; wind 2 m/s; motor G74W.',
     'wind_ms', 'about', '2', 2.0, None),
    # wind_ms about: calm (none)
    ('V4-0087-casual',
     'Calm-day shot to about 11,100 ft. Needs to land under 6.8 m/s, and the body can be up to 175 mm across. Keep the flight under 3 min.',
     'wind_ms', 'about', '', 0.0, None),
    # wind_ms about: near N
    ('V4-0112-casual',
     'About 105 ft up is plenty. Land under 5.2 m/s, wind near 2.2 m/s, and keep the width under 40 mm.',
     'wind_ms', 'about', '2.2', 2.2, None),
    # wind_ms about: roughly N
    ('V4-0051-casual',
     "I'm after something around 22,000 ft, landing under 8 m/s, with the whole flight staying under 10 min. Launch wind is roughly 5.4 m/s. Weight under 10 kg please.",
     'wind_ms', 'about', '5.4', 5.4, None),
]


@pytest.mark.parametrize("row_id, text, field, kind, number, value, tol", PINNED,
                         ids=[f"{p[0]}-{p[2]}-{i}" for i, p in enumerate(PINNED)])
def test_real_wording(row_id: str, text: str, field: str, kind: str, number: str, value: Any,
                      tol: Any) -> None:
    p = B.parse_prompt(text)
    assert p.unassigned == [] and p.other_asks == []
    found = [i for i in p.by_field(field) if i.number_text == number]
    assert len(found) == 1, (row_id, p.items)
    it = found[0]
    assert it.kind == kind and it.tol == tol
    assert it.value == (value if field == "motors" else pytest.approx(value))
    check_spans(p)
