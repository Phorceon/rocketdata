"""Tests for sftgen/out/prompts_v1.jsonl and sftgen/out/groups.json (DATA_SPEC.md sections 3, 4, 8).

Run the generators first:

    .venv/bin/python -m sftgen.groups
    .venv/bin/python -m sftgen.prompts
    .venv/bin/python -m pytest sftgen/tests/test_prompts.py -q
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import pytest

from sftgen import contract, prompts as P

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "out"
PROMPTS = OUT / "prompts_v1.jsonl"
GROUPS = OUT / "groups.json"

GOAL_KEYS = {"apogee_m", "ground_hit_ms", "flight_time_s", "time_to_apogee_s", "payload_kg", "drift_m"}
ALLOWED_SIM = {"wind_ms", "rail_length_m", "launch_angle_deg", "site_altitude_m"}
SPLITS = {"train", "val", "test"}

# Per-key allowed kinds, from contract.TARGET_KEYS descriptions.
KIND_RULES = {
    "apogee_m": {"about", "min", "max", "range"},
    "ground_hit_ms": {"max"},
    "flight_time_s": {"max", "range"},
    "time_to_apogee_s": {"about", "range"},
    "motor": {"exact"},
    "motor_class": {"max"},
    "motor_diameter_m": {"max"},
    "body_diameter_m": {"max"},
    "total_impulse_ns": {"max"},
    "stages": {"exact"},
    "motor_count": {"exact"},
    "payload_kg": {"min"},
    "recovery": {"exact"},
    "drift_m": {"max"},
    "feasible": {"exact"},
}

MIX_RANGE = {  # spec 3.3 with a little slack around the target shares
    "altitude": (0.25, 0.35),
    "fixed_motor": (0.10, 0.20),
    "recovery": (0.10, 0.20),
    "multi": (0.05, 0.15),
    "fix": (0.05, 0.15),
    "missing_info": (0.05, 0.15),
    "infeasible": (0.05, 0.10),
    "timed": (0.0, 0.05),
}

# Decimals a person would actually write ("1.5 m rail", "4.5 m/s", "0.5 kg payload").
NICE_DECIMALS = {"0.5", "1.5", "2.5", "3.5", "4.5", "5.5", "7.5"}

QTY_WORDS = "two|three|four|five|six|seven|eight|nine|ten|\\d+"


@pytest.fixture(scope="module")
def rows() -> list[dict]:
    assert PROMPTS.exists(), f"run `python -m sftgen.prompts` first; {PROMPTS} missing"
    with PROMPTS.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


@pytest.fixture(scope="module")
def groups() -> dict:
    assert GROUPS.exists(), f"run `python -m sftgen.groups` first; {GROUPS} missing"
    return json.loads(GROUPS.read_text(encoding="utf-8"))


# ------------------------------------------------------------------- per-row shape

def test_required_fields(rows):
    need = {"prompt_id", "group_id", "split", "prompt_type", "template_id", "user_text",
            "targets", "sim_conditions", "missing_info", "expected_feasible",
            "infeasible_reason", "needs_design", "reference"}
    for p in rows:
        assert need <= set(p), (p.get("prompt_id"), need - set(p))
        assert p["split"] in SPLITS
        assert p["prompt_type"] in P.MIX
        assert isinstance(p["user_text"], str) and p["user_text"].strip()


def test_prompt_ids_unique(rows):
    ids = [p["prompt_id"] for p in rows]
    assert len(ids) == len(set(ids))


def test_every_prompt_has_a_goal(rows):
    for p in rows:
        assert GOAL_KEYS & set(p["targets"]), (p["prompt_id"], p["targets"])


def test_target_keys_and_kinds(rows):
    for p in rows:
        for k, t in p["targets"].items():
            assert k in contract.TARGET_KEYS, (p["prompt_id"], k)
            assert t["kind"] in contract.TARGET_KINDS, (p["prompt_id"], k, t["kind"])
            assert t["kind"] in KIND_RULES[k], (p["prompt_id"], k, t["kind"])
            if k == "feasible":
                assert t["value"] is False
            if k == "apogee_m" and t["kind"] == "range":
                lo, hi = t["value"]
                assert lo < hi
            if k == "flight_time_s" and t["kind"] == "range":
                lo, hi = t["value"]
                assert lo < hi


def test_applies_to_only_multi_section(rows):
    for p in rows:
        t = p["targets"].get("ground_hit_ms", {})
        if t.get("applies_to"):
            r = p["reference"]
            assert t["applies_to"] == "every section"
            assert r["stage_count"] > 1 or r["motor_count"] > 1 or r.get("parallel_boosters"), \
                p["prompt_id"]


def test_sim_conditions_only_stated_overrides(rows):
    for p in rows:
        assert set(p["sim_conditions"]) <= ALLOWED_SIM, p["prompt_id"]
        for k, v in p["sim_conditions"].items():
            assert isinstance(v, (int, float)) and v > 0, (p["prompt_id"], k, v)


def test_infeasible_rows(rows):
    for p in rows:
        if p["expected_feasible"]:
            assert p["infeasible_reason"] in (None, "")
            assert "feasible" not in p["targets"]
        else:
            assert p["targets"].get("feasible") == {"value": False, "kind": "exact"}
            assert p["infeasible_reason"], p["prompt_id"]


def test_fix_rows(rows):
    """Placeholders until fill_fix runs; after that the draft and the observed value are real."""
    for p in rows:
        if p["needs_design"]:
            fs = p.get("fix_spec")
            assert fs and fs.get("flaw") in P.FIX_FLAWS, (p["prompt_id"], fs)
            if isinstance(fs.get("draft_design"), dict):
                assert "{DESIGN_JSON}" not in p["user_text"], p["prompt_id"]
                assert "{OBSERVED}" not in p["user_text"], p["prompt_id"]
                assert fs.get("observed_text") and fs["observed_text"] in p["user_text"], p["prompt_id"]
                assert fs.get("base_source") in ("converted", "synthesized"), p["prompt_id"]
                assert fs.get("fix_check", {}).get("passes_targets_and_gates") is True, p["prompt_id"]
            else:
                assert "{DESIGN_JSON}" in p["user_text"], p["prompt_id"]
                assert "{OBSERVED}" in p["user_text"], p["prompt_id"]
        else:
            assert "{DESIGN_JSON}" not in p["user_text"], p["prompt_id"]


def test_missing_info_type_omits_something(rows):
    for p in rows:
        if p["prompt_type"] == "missing_info":
            assert p["missing_info"], p["prompt_id"]
            # the deliberately thin ones ask only for altitude
            assert set(p["targets"]) <= {"apogee_m"}, p["prompt_id"]


def test_multi_only_from_multi_groups(rows):
    for p in rows:
        if p["prompt_type"] == "multi":
            r = p["reference"]
            assert r["stage_count"] > 1 or r["motor_count"] > 1, p["prompt_id"]


def test_motor_targets_resolve(rows):
    """Every `targets.motor` value is a canonical pinned-DB designation: it must
    resolve through sftgen.motors.resolve and come back unchanged."""
    from sftgen import motors
    for p in rows:
        t = p["targets"].get("motor")
        if not t:
            continue
        for des in t["value"]:
            r = motors.resolve(des)
            assert r["designation"] == des, (p["prompt_id"], des, r["designation"])


def test_motors_resolved_reference(rows):
    """reference.motors_resolved aligns with reference.motors; non-null entries
    resolve to themselves under the same manufacturer."""
    from sftgen import motors
    for p in rows:
        ref = p["reference"]
        mr = ref.get("motors_resolved")
        assert isinstance(mr, list) and len(mr) == len(ref["motors"]), p["prompt_id"]
        for e in mr:
            if e is None:
                continue
            assert set(e) == {"manufacturer", "designation", "total_impulse_ns", "diameter_m"}, p["prompt_id"]
            r = motors.resolve(e["designation"])
            assert r["designation"] == e["designation"], (p["prompt_id"], e)
            # A bare resolve may prefer another maker that shares the designation
            # (e.g. Estes B4 vs Klima B4); the manufacturer hint is what fixed it.


# ------------------------------------------------------------------- wording

def _prose(p: dict) -> str:
    """Prompt wording with a filled design and its observed value taken back out.

    The design JSON is full of millimetre decimals, and a person-rounded margin
    such as '0.6 cal' is one decimal on purpose. Neither is a simulator-precision
    number sneaking into the sentence.
    """
    text = p["user_text"]
    fs = p.get("fix_spec") or {}
    draft = fs.get("draft_design")
    if isinstance(draft, dict):
        blob = json.dumps(draft, ensure_ascii=False, separators=(", ", ": "))
        text = text.replace(blob, " ")
    observed = fs.get("observed_text")
    if isinstance(observed, str):
        text = text.replace(observed, " ")
    return text


def test_no_sim_precision_numbers(rows):
    """No simulator-precision decimals; '1.5 m rail' or '4.5 m/s' are fine."""
    for p in rows:
        for m in re.finditer(r"\d+\.\d+", _prose(p)):
            assert m.group(0) in NICE_DECIMALS, (p["prompt_id"], m.group(0), p["user_text"])


def test_no_plural_motor_after_single(rows):
    pat = re.compile(rf"\b(?:a|an|one|single)\s+(?:\w+\s+){{0,2}}[A-P]\d+\w*\s+motors\b", re.I)
    for p in rows:
        assert not pat.search(p["user_text"]), (p["prompt_id"], p["user_text"])
        m = p["targets"].get("motor")
        if m and len(m["value"]) == 1:
            # a lone motor may only be named in the singular
            for mm in re.finditer(r"\b([A-P]\d[\w-]*)\s+motors\b", p["user_text"]):
                assert re.search(rf"\b(?:{QTY_WORDS})\s+{re.escape(mm.group(1))}\s+motors\b",
                                 p["user_text"], re.I), (p["prompt_id"], mm.group(0))


def test_articles_before_numbers(rows):
    for p in rows:
        for m in re.finditer(r"\b(a|an)\s+(\d[\d,]*(?:\.\d+)?)", p["user_text"]):
            assert (m.group(1) == "an") == P.num_needs_an(m.group(2)), \
                (p["prompt_id"], m.group(0))


def test_whitespace_clean(rows):
    for p in rows:
        t = p["user_text"]
        assert "  " not in t and " ." not in t and ".." not in t and ",." not in t, \
            (p["prompt_id"], t)


def test_feasible_about_targets_match_reference(rows):
    """'About X' apogee targets sit within ~5% of the group's reference apogee."""
    for p in rows:
        t = p["targets"].get("apogee_m")
        ref = p["reference"].get("apogee_m")
        if p["expected_feasible"] and t and t["kind"] == "about" and ref:
            assert abs(t["value"] - ref) / ref <= 0.055, (p["prompt_id"], t["value"], ref)


# ------------------------------------------------------------------- groups / dedup

def test_group_members_cover_all_source_rows(groups):
    import itertools
    src = Path(__file__).resolve().parents[2] / groups["source"]
    files = {json.loads(l)["file"] for l in src.open(encoding="utf-8") if l.strip()}
    members = set(itertools.chain.from_iterable(g["members"] for g in groups["groups"]))
    assert members == files


def test_group_split_consistency(rows, groups):
    gsplit = {g["group_id"]: g["split"] for g in groups["groups"]}
    for p in rows:
        assert p["group_id"] in gsplit, p["prompt_id"]
        assert p["split"] == gsplit[p["group_id"]], p["prompt_id"]


def test_no_nested_pairs_in_group(rows):
    by_group = defaultdict(list)
    for p in rows:
        by_group[p["group_id"]].append(p)
    for gid, ps in by_group.items():
        for i, a in enumerate(ps):
            for b in ps[i + 1:]:
                assert not P.nested_pair(a, b), (a["prompt_id"], b["prompt_id"])
                assert a["user_text"] != b["user_text"], a["prompt_id"]


def test_group_size_cap(rows):
    per = Counter(p["group_id"] for p in rows)
    assert max(per.values()) <= 4


def test_split_stratification(groups):
    strata = defaultdict(set)
    for g in groups["groups"]:
        strata[g["split"]].add(g["stratum"])
    assert "multistage" in strata["val"] and "multistage" in strata["test"]
    assert "cluster" in strata["val"] and "cluster" in strata["test"]


# ------------------------------------------------------------------- whole file

def test_mix_shares(rows):
    n = len(rows)
    c = Counter(p["prompt_type"] for p in rows)
    for t, (lo, hi) in MIX_RANGE.items():
        share = c[t] / n
        assert lo <= share <= hi, (t, share)


def test_max_skeleton_share(rows):
    n = len(rows)
    skel = Counter(P.skeleton(p["user_text"]) for p in rows)
    top, cnt = skel.most_common(1)[0]
    assert cnt / n <= 0.05, (top, cnt / n)


def test_determinism(groups):
    """Rebuilding two families from scratch gives byte-identical records."""
    subset = groups["groups"][:2] + groups["groups"][-2:]
    facts = [P.Facts(g) for g in subset]
    a = [P.build_family(f, ["altitude", "fix"]) for f in facts]
    b = [P.build_family(f, ["altitude", "fix"]) for f in facts]
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
