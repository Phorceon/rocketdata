import copy
import json
from pathlib import Path

import pytest

from sftgen import contract
from sftgen.lint import Issue, _check_math, gate_failures, lint_file, lint_row

DESIGN = json.loads((Path(__file__).resolve().parents[1] / "examples" / "alpha_c6.json").read_text())


def fins(d):
    return d["stages"][0]["components"][1]["contents"][2]


def chute(d):
    return d["stages"][0]["components"][1]["contents"][0]


def small_fin_design():
    d = copy.deepcopy(DESIGN)
    fins(d)["root_chord_m"] = 0.045
    fins(d)["span_m"] = 0.03
    return d


def sim_out(**kw):
    o = copy.deepcopy(contract.SIMULATE_OUTPUT)
    o["rail_exit_ms"] = 15.8  # the contract example is 14.2 m/s, which fails the 15 m/s gate
    o.update(kw)
    return o


TARGETS = {
    "apogee_m": {"value": 250, "kind": "about"},
    "ground_hit_ms": {"value": 6.0, "kind": "max"},
    "motor": {"value": ["C6"], "kind": "exact"},
}


# ---- message builders ---------------------------------------------------------------------------

def system(text=contract.SYSTEM_PROMPT):
    return {"role": "system", "content": text}


def user(text):
    return {"role": "user", "content": text}


def call(cid, name, args):
    return {"id": cid, "type": "function", "function": {"name": name, "arguments": args}}


def asst(reasoning, calls=None, content=""):
    m = {"role": "assistant", "reasoning_content": reasoning, "content": content}
    if calls:
        m["tool_calls"] = calls
    return m


def tool(cid, name, output):
    return {"role": "tool", "tool_call_id": cid, "name": name, "content": json.dumps(output, ensure_ascii=False)}


def final_content(design, summary="C6-powered BT-50 sport rocket with a 0.305 m chute."
                                  "\nSimulated apogee 245.3 m, rail exit 15.8 m/s, margin 2.31 cal, landing 4.1 m/s."):
    return f"{summary}\n<design>{json.dumps(design)}</design>"


def make_row(messages, targets=None, rid="r1"):
    return {"id": rid, "messages": messages, "tools": copy.deepcopy(contract.TOOLS),
            "targets": copy.deepcopy(targets if targets is not None else TARGETS)}


def prompt(apogee=250):
    return f"Beginner rocket on an Estes C6 that gets to about {apogee} m and lands under 6 m/s."


def t1(apogee=250, extra=""):
    return (f"1. Understand: apogee about {apogee} m (approximate, within 5%); landing at most 6 m/s; motor fixed "
            "to the C6. Rail and wind not given, so I assume a 1.5 m rail and 2 m/s wind.\n"
            "2. Feasibility: I need the C6 data first." + extra)


FEAS = ("2. Feasibility: the C6 gives 8.8 N*s total impulse and 14.1 N peak thrust. A BT-50 build weighs about "
        "0.06 kg loaded, so peak thrust-to-weight is 14.1 / (0.06 * 9.81) = 24:1 and average "
        "4.8 / (0.06 * 9.81) = 8.2:1, well above 3:1.\n")
SIZE = ("3. Size: BT-50 body 0.0249 m across and 0.46 m long, ogive nose 0.1 m, three balsa fins with {root} m "
        "root chord and {span} m span. Descent on a 0.305 m chute with Cd 0.8: "
        "v = sqrt(2 * 0.06 * 9.81 / (1.225 * 0.8 * pi * 0.15^2)) = 4.1 m/s.\n")
DRAFT = "4. Draft: C6-5 in a BT-50 airframe with the fins above. Checking it in the simulator."


def t2(root="0.055", span="0.04", extra="", order=("feas", "size")):
    parts = {"feas": FEAS, "size": SIZE.format(root=root, span=span)}
    return "".join(parts[k] for k in order) + DRAFT + extra


CHECK_PASS = ("4. Check: apogee 245.3 m against about {apogee} m, inside the 5% band. Rail exit 15.8 m/s against "
              "the 15 m/s minimum, thrust-to-weight 8.0:1, margin 2.31 cal at rail exit and 2.05 cal at its lowest "
              "in the burn, landing 4.1 m/s under the 6 m/s limit. My descent estimate agrees.\n")
FIX_NONE = "5. Fix: none needed, every check passed.\n"
UNC = "6. Uncertainty: drag and the chute Cd are model values, so real apogee can be 10 to 15% off; wind was assumed."


def clean_row(apogee=250, t1_extra="", t2_extra="", t3=None, content=None, sys_text=contract.SYSTEM_PROMPT,
              t2_order=("feas", "size"), targets=None):
    t3 = t3 if t3 is not None else CHECK_PASS.format(apogee=apogee) + FIX_NONE + UNC
    tg = copy.deepcopy(targets if targets is not None else TARGETS)
    tg["apogee_m"]["value"] = apogee
    return make_row([
        system(sys_text),
        user(prompt(apogee)),
        asst(t1(apogee, t1_extra), [call("call_1", "motor_lookup", {"designation": "C6"})]),
        tool("call_1", "motor_lookup", contract.MOTOR_LOOKUP_OUTPUT),
        asst(t2(extra=t2_extra, order=t2_order), [call("call_2", "simulate", {"design": copy.deepcopy(DESIGN)})]),
        tool("call_2", "simulate", sim_out()),
        asst(t3, content=content if content is not None else final_content(DESIGN)),
    ], tg)


FIX_CHECK = ("4. Check: apogee 251.0 m is inside 5% of 250 m and landing is 4.1 m/s, but the margin at rail exit is "
             "0.62 cal, below the 1.0 cal minimum.\n"
             "5. Fix: the fins are too small to pull the CP far enough aft. Raise the root chord from 0.045 m to "
             "0.055 m and the span from 0.03 m to 0.04 m, then fly it again.")
RECHECK = ("4. Check: the re-run gives a margin of 2.31 cal at rail exit and 2.05 cal minimum in the burn, apogee "
           "245.3 m, rail exit 15.8 m/s and landing 4.1 m/s, so every check now passes.\n" + UNC)


def fix_row(rid="f1", user_text=None):
    return make_row([
        system(),
        user(user_text or prompt()),
        asst(t1(), [call("call_1", "motor_lookup", {"designation": "C6"})]),
        tool("call_1", "motor_lookup", contract.MOTOR_LOOKUP_OUTPUT),
        asst(t2(root="0.045", span="0.03"), [call("call_2", "simulate", {"design": small_fin_design()})]),
        tool("call_2", "simulate", sim_out(apogee_m=251.0, stability_rail_exit_cal=0.62, min_stability_burn_cal=0.55)),
        asst(FIX_CHECK, [call("call_3", "simulate", {"design": copy.deepcopy(DESIGN)})]),
        tool("call_3", "simulate", sim_out()),
        asst(RECHECK, content=final_content(DESIGN)),
    ], rid=rid)


def two_sim_row(second_design, check_text, final_reasoning, final_design):
    return make_row([
        system(),
        user(prompt()),
        asst(t1(), [call("call_1", "motor_lookup", {"designation": "C6"})]),
        tool("call_1", "motor_lookup", contract.MOTOR_LOOKUP_OUTPUT),
        asst(t2(), [call("call_2", "simulate", {"design": copy.deepcopy(DESIGN)})]),
        tool("call_2", "simulate", sim_out()),
        asst(check_text, [call("call_3", "simulate", {"design": second_design})]),
        tool("call_3", "simulate", sim_out()),
        asst(final_reasoning, content=final_content(final_design)),
    ])


def must(issues):
    return [i for i in issues if i.severity == "must"]


def must_codes(row):
    return {i.code for i in must(lint_row(row))}


# ---- clean rows ---------------------------------------------------------------------------------

def test_clean_row_has_no_issues():
    stats = {}
    issues = lint_row(clean_row(), stats)
    assert issues == [], issues
    assert stats["math_checked"] == 3 and stats["math_failed"] == 0
    assert stats["clean_first_pass"] is True and stats["fix_rounds"] == 0


def test_clean_fix_round_has_no_issues():
    stats = {}
    issues = lint_row(fix_row(), stats)
    assert issues == [], issues
    assert stats["fix_rounds"] == 1 and stats["clean_first_pass"] is False


def test_hedged_provenance_word_is_allowed():
    assert lint_row(clean_row(t1_extra=" Nothing is simulated yet.")) == []


# ---- failing rows: each triggers exactly the intended must-level code ---------------------------

def test_leakage_sim_value_before_simulate():
    row = clean_row(t2_extra=" I expect an apogee near 245.3 m.")
    issues = must(lint_row(row))
    assert {i.code for i in issues} == {"leakage"}
    assert issues[0].msg_index == 4 and "245.3" in issues[0].message


def test_leakage_target_more_precise_than_prompt():
    tg = copy.deepcopy(TARGETS)
    tg["apogee_m"] = {"value": 252.7, "kind": "about"}
    row = clean_row(t1_extra=" Aiming for 252.7 m.")
    row["targets"] = tg
    row["messages"][1]["content"] = "Beginner rocket on an Estes C6 that gets to about 253 m and lands under 6 m/s."
    issues = must(lint_row(row))
    assert {i.code for i in issues} == {"leakage"}
    assert "more precisely" in issues[0].message


def test_provenance_before_any_tool():
    row = clean_row(apogee=245, t1_extra="\nVerified apogee 245 m with this layout.")
    issues = must(lint_row(row))
    assert {i.code for i in issues} == {"provenance"}
    assert issues[0].msg_index == 2


def test_provenance_before_tool_also_leaks_when_prompt_differs():
    row = clean_row(t1_extra="\nVerified apogee 245 m with this layout.")
    assert must_codes(row) == {"provenance"}
    # 245 has three significant figures, so the early match alone is only a warning.
    assert any(i.code == "leakage" and i.severity == "should" for i in lint_row(row))


def test_provenance_without_number_after_tool():
    row = clean_row(t3=CHECK_PASS.format(apogee=250) + "Everything is confirmed by the run.\n" + FIX_NONE + UNC)
    assert must_codes(row) == {"provenance"}


def test_banned_phrase():
    row = clean_row(t3=CHECK_PASS.format(apogee=250) + "The landing speed measured in the flight data is fine.\n"
                    + FIX_NONE + UNC)
    issues = must(lint_row(row))
    assert {i.code for i in issues} == {"provenance"}
    assert "banned phrase" in issues[0].message


def test_bad_math():
    row = clean_row(t2_extra=" Weight is 0.061 * 9.81 = 0.9 N.")
    issues = must(lint_row(row))
    assert {i.code for i in issues} == {"math"}
    assert "0.061 * 9.81 = 0.9" in issues[0].message


def test_final_design_differs_from_last_simulated():
    d = copy.deepcopy(DESIGN)
    chute(d)["diameter_m"] = 0.35
    issues = must(lint_row(clean_row(content=final_content(d))))
    assert {i.code for i in issues} == {"design"}
    assert "differs" in issues[0].message


def test_two_designs_in_final_content():
    block = f"<design>{json.dumps(DESIGN)}</design>"
    assert must_codes(clean_row(content=final_content(DESIGN) + "\n" + block)) == {"design"}


def test_text_after_design_block():
    issues = must(lint_row(clean_row(content=final_content(DESIGN) + "\nGood luck at the launch!")))
    assert {i.code for i in issues} == {"design"}
    assert "after </design>" in issues[0].message


def test_float_fin_count_fails_schema():
    d = copy.deepcopy(DESIGN)
    fins(d)["count"] = 3.0
    issues = must(lint_row(clean_row(content=final_content(d))))
    assert {i.code for i in issues} == {"design"}
    assert any("parse_design" in i.message for i in issues)


def test_no_op_rerun():
    check = CHECK_PASS.format(apogee=250) + "5. Fix: none needed, every check passed. Running it once more."
    final = "4. Check: same result, apogee 245.3 m and margin 2.31 cal.\n" + UNC
    issues = must(lint_row(two_sim_row(copy.deepcopy(DESIGN), check, final, DESIGN)))
    assert {i.code for i in issues} == {"fix"}
    assert "no-op" in issues[0].message


def test_fix_without_failure():
    big = copy.deepcopy(DESIGN)
    chute(big)["diameter_m"] = 0.35
    check = ("4. Check: apogee 245.3 m and every gate passes, landing 4.1 m/s.\n"
             "5. Fix: a larger chute would land softer, so I go to a 0.35 m chute.")
    final = "4. Check: apogee 245.3 m, landing 4.1 m/s, margin 2.31 cal.\n" + UNC
    issues = must(lint_row(two_sim_row(big, check, final, big)))
    assert {i.code for i in issues} == {"fix"}
    assert "without a failure" in issues[0].message


def test_fix_must_quote_failing_value():
    row = fix_row()
    row["messages"][6]["reasoning_content"] = FIX_CHECK.replace("0.62 cal", "too low")
    issues = must(lint_row(row))
    assert {i.code for i in issues} == {"fix"}
    assert "quote" in issues[0].message


def test_empty_wait():
    t3 = (CHECK_PASS.format(apogee=250) + "Wait, let me double-check the thrust-to-weight: it is 8.0:1, fine.\n"
          + FIX_NONE + UNC)
    issues = must(lint_row(clean_row(t3=t3)))
    assert {i.code for i in issues} == {"reflection"}


def test_steps_out_of_order():
    issues = must(lint_row(clean_row(t2_order=("size", "feas"))))
    assert {i.code for i in issues} == {"steps"}
    assert "comes after step 3" in issues[0].message


def test_missing_step_6():
    issues = must(lint_row(clean_row(t3=CHECK_PASS.format(apogee=250) + FIX_NONE)))
    assert {i.code for i in issues} == {"steps"}
    assert "[6]" in issues[0].message


def test_wrong_system_prompt():
    row = clean_row(sys_text="You are an autonomous aerospace design engineer. Output the final verified design.")
    assert must_codes(row) == {"structure"}


def test_tool_message_count_mismatch():
    row = clean_row()
    row["messages"][2]["tool_calls"].append(call("call_1b", "motor_lookup", {"designation": "D12"}))
    issues = must(lint_row(row))
    assert {i.code for i in issues} == {"structure"}
    assert "2 tool call(s) but 1 tool message(s)" in issues[0].message


def test_think_tag_and_tools_mismatch():
    row = clean_row(t1_extra=" <think>")
    row["tools"] = row["tools"][:2]
    msgs = [i.message for i in must(lint_row(row))]
    assert any("<think>" in m for m in msgs) and any("contract.TOOLS" in m for m in msgs)


def test_infeasible_row_without_design():
    tg = {"apogee_m": {"value": 3000, "kind": "about"}, "motor": {"value": ["C6"], "kind": "exact"},
          "feasible": {"value": False, "kind": "exact"}}
    t3 = ("4. Check: no draft; 8.8 N*s cannot lift even a 0.03 kg rocket that high.\n"
          "5. Fix: not applicable.\n6. Uncertainty: drag estimates are rough, but the gap is far too large.")
    row = make_row([
        system(), user("3,000 m on a single C6."),
        asst("1. Understand: apogee about 3,000 m, motor fixed to a C6.\n2. Feasibility: need the C6 data.\n"
             "3. Size: depends on the impulse.", [call("call_1", "motor_lookup", {"designation": "C6"})]),
        tool("call_1", "motor_lookup", contract.MOTOR_LOOKUP_OUTPUT),
        asst(t3, content="Infeasible: a C6 cannot reach 3,000 m apogee; it tops out near 300 m."),
    ], tg)
    assert must(lint_row(row)) == []
    row["messages"][-1]["content"] = "Try a bigger rocket."
    assert must_codes(row) == {"design"}


def test_precision_flags_overprecise_estimate():
    issues = lint_row(clean_row(t2_extra=" CG estimate 0.32154 m from the nose."))
    assert {(i.code, i.severity) for i in issues} == {("precision", "must")}


def test_precision_4_sig_figs_is_should():
    issues = lint_row(clean_row(t2_extra=" CG estimate 0.3215 m from the nose."))
    assert {(i.code, i.severity) for i in issues} == {("precision", "should")}


def test_wait_with_real_design_change_is_allowed():
    check = ("4. Check: apogee 251.0 m is inside the band, but wait, the margin at rail exit is "
             "0.62 cal, under the 1.0 cal minimum.\n"
             "5. Fix: raise the root chord to 0.055 m and the span to 0.04 m, then fly it again.")
    final = "4. Check: the re-run gives margin 2.31 cal, apogee 245.3 m and landing 4.1 m/s.\n" + UNC
    row = make_row([
        system(), user(prompt()),
        asst(t1(), [call("call_1", "motor_lookup", {"designation": "C6"})]),
        tool("call_1", "motor_lookup", contract.MOTOR_LOOKUP_OUTPUT),
        asst(t2(root="0.045", span="0.03"), [call("call_2", "simulate", {"design": small_fin_design()})]),
        tool("call_2", "simulate", sim_out(apogee_m=251.0, stability_rail_exit_cal=0.62,
                                         min_stability_burn_cal=0.55)),
        asst(check, [call("call_3", "simulate", {"design": copy.deepcopy(DESIGN)})]),
        tool("call_3", "simulate", sim_out()),
        asst(final, content=final_content(DESIGN)),
    ])
    assert lint_row(row) == []


def test_clean_pass_step5_too_long():
    long5 = "5. Fix: none needed. " + "Everything is comfortably inside its limit and nothing has to move. " * 4 + "\n"
    issues = lint_row(clean_row(t3=CHECK_PASS.format(apogee=250) + long5 + UNC))
    assert {(i.code, i.severity) for i in issues} == {("clean_pass", "should")}


def test_still_failing_needs_mention():
    row = clean_row()
    row["messages"][5] = tool("call_2", "simulate", sim_out(apogee_m=200.1))
    row["messages"][6]["reasoning_content"] = (
        "4. Check: apogee 200.1 m against about 250 m is outside the 5% band; the rest pass.\n"
        "5. Fix: the C6 is the largest allowed motor, so I stop here.\n" + UNC)
    row["messages"][6]["content"] = final_content(DESIGN, "BT-50 on a C6.\nApogee 200.1 m in the run.")
    issues = lint_row(row)
    assert {(i.code, i.severity) for i in issues} == {("fix", "should")}
    row["messages"][6]["content"] = final_content(DESIGN, "BT-50 on a C6.\nApogee 200.1 m, still short of 250 m.")
    assert lint_row(row) == []


def test_malformed_row_does_not_crash():
    issues = lint_row({"messages": [None, {"role": "user"}], "tools": []})
    assert issues and all(isinstance(i, Issue) for i in issues)
    assert "lint_error" not in {i.code for i in issues}


# ---- math parser --------------------------------------------------------------------------------

@pytest.mark.parametrize("text,checked,bad,skipped", [
    ("speed sqrt(2*9.81*1400) = 166 m/s", 1, 0, 0),
    ("span 2 * 0.0249 m = 49.8 mm", 1, 0, 0),
    ("ratio 245.3 / 250 = 98%", 1, 0, 0),
    ("T/W = 14.1 N / (0.061 kg × 9.81 m/s^2) = 23.6:1", 1, 0, 0),
    ("area π(0.15)² = 0.0707 m²", 1, 0, 0),
    ("3 x 0.055 = 0.2", 1, 0, 0),  # 0.165 is within half of the last shown digit
    ("3 x 0.055 = 0.25", 1, 1, 0),
    ("q = 0.5 * 1.225 * v^2 = 5", 0, 0, 1),
    ("margin = 1.5 cal", 0, 0, 0),
    ("the 5-7 = whatever", 0, 0, 0),
])
def test_math_parser(text, checked, bad, skipped):
    r = _check_math(text)
    assert (r.checked, len(r.bad), r.skipped) == (checked, bad, skipped), r


# ---- gate_failures ------------------------------------------------------------------------------

def test_gate_failures_contract_example_fails_rail_exit():
    fails = gate_failures(contract.SIMULATE_OUTPUT, {})
    assert len(fails) == 1 and fails[0].startswith("rail_exit_ms 14.2")


def test_gate_failures_clean_and_targets():
    assert gate_failures(sim_out(), TARGETS) == []
    assert any("stability_rail_exit_cal" in f for f in gate_failures(sim_out(stability_rail_exit_cal=0.62), {}))
    assert any("min_stability_burn_cal" in f for f in gate_failures(sim_out(min_stability_burn_cal=0.0), {}))
    assert any("thrust_to_weight" in f for f in gate_failures(sim_out(thrust_to_weight=2.5), {}))
    assert any("total_impulse_ns" in f for f in gate_failures(sim_out(total_impulse_ns=50000.0), {}))
    assert gate_failures(sim_out(apogee_m=300.0), {"apogee_m": {"value": 250, "kind": "about"}})
    assert gate_failures(sim_out(), {"apogee_m": {"value": 200, "kind": "min"}}) == []
    assert gate_failures(sim_out(), {"apogee_m": {"value": 200, "kind": "max"}})
    assert gate_failures(sim_out(), {"apogee_m": {"value": [240, 250], "kind": "range"}}) == []
    assert gate_failures(sim_out(), {"flight_time_s": {"value": 30, "kind": "max"}})
    assert gate_failures(sim_out(), {"time_to_apogee_s": {"value": 6.0, "kind": "about"}}) == []
    assert gate_failures(sim_out(), {"drift_m": {"value": 50, "kind": "max"}})


def test_gate_failures_section_still_airborne():
    s = sim_out()
    s["sections"][0]["reached_ground"] = False
    assert any("still airborne" in f for f in gate_failures(s, {}))


def test_gate_failures_landing_and_recovery():
    s = sim_out()
    s["sections"][0]["landing_ms"] = 7.0
    assert any("landing_ms 7" in f for f in gate_failures(s, {}))
    assert gate_failures(sim_out(), {"ground_hit_ms": {"value": 4.0, "kind": "max", "applies_to": "every section"}})
    s = sim_out()
    s["sections"][0]["recovery_deployed"] = False
    assert any("recovery not deployed" in f for f in gate_failures(s, {}))
    assert gate_failures(contract.TOOL_ERROR_OUTPUT, {})[0].startswith("simulate returned an error")


def test_gate_failures_missing_values_count_as_failures():
    s = sim_out()
    del s["rail_exit_ms"]
    assert any(f.startswith("rail_exit_ms missing") for f in gate_failures(s, {}))
    s = sim_out()
    del s["sections"]
    assert any("no section data" in f for f in gate_failures(s, {}))
    s = sim_out()
    s["sections"][0]["landing_ms"] = None
    assert any("landing_ms missing" in f for f in gate_failures(s, {}))
    s = sim_out()
    del s["conditions"]
    assert any("wind_ms" in f for f in gate_failures(s, {}))
    s = sim_out()
    del s["apogee_m"]
    assert any("apogee_m missing" in f for f in gate_failures(s, TARGETS))


# ---- file-level ---------------------------------------------------------------------------------

def test_lint_file_dup_repetition_and_report():
    rows = [clean_row(apogee=a) for a in (240, 245, 250, 255)]
    for i, r in enumerate(rows):
        r["id"] = f"c{i}"
    rows.append(copy.deepcopy(rows[0]))
    rows[-1]["id"] = "c0-copy"
    report = {}
    issues = lint_file(rows, report)
    dups = [(rid, i) for rid, i in issues if i.code == "dup"]
    assert [rid for rid, _ in dups] == ["c0-copy"]
    reps = [i for rid, i in issues if i.code == "repetition"]
    assert reps and all(i.severity == "must" for i in reps)
    assert not any(i.code == "clean_pass_share" for _, i in issues)
    assert report["n_rows"] == 5 and report["clean_pass_share"] == 1.0
    assert 0 < len(report["top_skeletons"]) <= 20
    skels = [s for s, _, _ in report["top_skeletons"]]
    assert "the m gives # n*s total impulse and # n peak thrust." in skels
    assert not any(s.startswith(("draft:", "check:", "fix:")) for s in skels)


def test_lint_file_clean_pass_share():
    rows = [fix_row(rid=f"f{i}", user_text=prompt(240 + 10 * i)) for i in range(4)]
    issues = lint_file(rows)
    share = [i for rid, i in issues if i.code == "clean_pass_share"]
    assert len(share) == 1 and share[0].severity == "should"
    assert not any(i.code == "dup" for _, i in issues)
