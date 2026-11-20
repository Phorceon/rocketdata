"""Stages 5-7 inside score(), shadow flights, score_many and the default
simulator, all without Java.

The simulator is a small stand-in that returns recorded replies
(tests/replies.py). Some tests also swap the stage hooks of scoring.py for
fakes, to check the running order alone.
"""
from __future__ import annotations

import threading

import pytest

from rocket_reward import Requirements, RewardSetupError, StageCheck, ladder
from rocket_reward import scoring as S
from rocket_reward.motors import MotorTable, substitute_unknown_motors, written_average_thrust
from answers import design_of
from replies import load_reply

REQ = Requirements.from_dict({"id": "t-1", "apogee_m": {"value": 500, "kind": "about"}})


class FakeSim:
    """Answers every run with `reply` (a dict, or a function of the request)."""

    def __init__(self, reply=None, size=2):
        self.reply = reply if reply is not None else load_reply("single_stage")
        self.size = size
        self.calls: list[dict] = []
        self._lock = threading.Lock()

    def run(self, ork_text, rail_m, flights, config_id=None, **extra):
        with self._lock:
            self.calls.append({"ork": ork_text, "rail_m": rail_m, "flights": flights, "config_id": config_id,
                               **extra})
        return self.reply(self.calls[-1]) if callable(self.reply) else self.reply


@pytest.fixture
def quiet(monkeypatch, tmp_path):
    """A fresh tracker and quarantine folder for each test."""
    monkeypatch.setattr(S, "_default_tracker", S.ErrorTracker())
    monkeypatch.setenv(S.QUARANTINE_ENV, str(tmp_path / "quarantine"))
    return tmp_path


@pytest.fixture(scope="module")
def table():
    return S.default_motor_table()


def _first_passing(gold_rows):
    for row in gold_rows:
        pre = S.preflight(row["answer"])
        if pre.passed:
            return row["answer"], pre
    raise AssertionError("no reference answer passes stages 1-4")


# ------------------------------------------------------------------ order, with fake stages

class Stages:
    """Fake stages 5-7 that record their calls."""

    def __init__(self, monkeypatch):
        self.calls: list[str] = []
        self.build = StageCheck("build", True, 1.0)
        self.flight = StageCheck("flight", True, 1.0, info={"metrics": {"apogee_m": 480.0}})
        self.targets = StageCheck("targets", True, 0.6)
        monkeypatch.setattr(S, "_check_build", self.check_build)
        monkeypatch.setattr(S, "_check_flight", self.check_flight)
        monkeypatch.setattr(S, "_check_targets", self.check_targets)

    def check_build(self, reply, root):
        self.calls.append("build")
        return self.build

    def check_flight(self, reply, requirements):
        self.calls.append("flight")
        return self.flight

    def check_targets(self, reply, requirements, root, table):
        self.calls.append("targets")
        return self.targets


def test_all_stages_pass(quiet, monkeypatch, gold_rows):
    answer, _ = _first_passing(gold_rows)
    st = Stages(monkeypatch)
    sim = FakeSim()
    r = S.score(answer, REQ, simulator=sim)
    assert st.calls == ["build", "flight", "targets"]
    assert r.stage == "targets" and r.stages_passed == 7
    assert r.score == ladder.stage_score("targets", 0.6) and r.credit == 0.6
    assert r.metrics == {"apogee_m": 480.0}
    assert len(sim.calls) == 1 and sim.calls[0]["flights"] == [
        {"wind_ms": 1.0, "seed": 1}, {"wind_ms": 2.0, "seed": 2}, {"wind_ms": 3.0, "seed": 3}]
    assert sim.calls[0]["ork"].startswith("<?xml") and sim.calls[0]["config_id"] == r.flags["config_id"]


def test_build_failure_stops_the_ladder(quiet, monkeypatch, gold_rows):
    answer, _ = _first_passing(gold_rows)
    st = Stages(monkeypatch)
    st.build = StageCheck("build", False, 0.5, reasons=["fins off the tube"], defects=["d1"])
    r = S.score(answer, REQ, simulator=FakeSim())
    assert st.calls == ["build"]
    assert r.stage == "build" and r.stages_passed == 4 and r.reasons == ["fins off the tube"]
    assert r.score == ladder.stage_score("build", 0.5, 1) and r.defects == ["d1"]
    assert r.metrics.get("apogee_m") is not None   # the nominal flight's numbers, from the reply


def test_flight_failure_stops_before_targets(quiet, monkeypatch, gold_rows):
    answer, _ = _first_passing(gold_rows)
    st = Stages(monkeypatch)
    st.build = StageCheck("build", True, 1.0, defects=["small fit problem: a"])
    st.flight = StageCheck("flight", False, 0.25, reasons=["unstable"], info={"metrics": {"apogee_m": 3.0}})
    r = S.score(answer, REQ, simulator=FakeSim())
    assert st.calls == ["build", "flight"]
    assert r.stage == "flight" and r.stages_passed == 5
    assert r.score == ladder.stage_score("flight", 0.25, 1) and r.metrics == {"apogee_m": 3.0}


def test_defects_of_every_stage_lower_the_score(quiet, monkeypatch, gold_rows):
    answer, _ = _first_passing(gold_rows)
    st = Stages(monkeypatch)
    st.build = StageCheck("build", True, 1.0, defects=["a", "b"])
    st.targets = StageCheck("targets", True, 1.0, defects=["c"])
    r = S.score(answer, REQ, simulator=FakeSim())
    assert r.defects[-3:] == ["a", "b", "c"]
    assert r.score == ladder.stage_score("targets", 1.0, len(r.defects))


# ------------------------------------------------------------------ real stages, odd replies

@pytest.mark.parametrize("kind", ["load", "build", "hang", "crash"])
def test_design_faults_score_the_build_floor(quiet, gold_rows, kind):
    answer, _ = _first_passing(gold_rows)
    r = S.score(answer, REQ, simulator=FakeSim({"ok": False, "error_kind": kind, "message": "it broke"}))
    assert r.stage == "build" and r.credit == 0.0 and r.score == ladder.stage("build").floor
    assert r.flags["sim_error_kind"] == kind and "it broke" in r.reasons[0]


def test_a_crashed_flight_scores_the_build_floor(quiet, gold_rows):
    answer, _ = _first_passing(gold_rows)
    reply = load_reply("single_stage")
    reply["flights"][2] = {"ok": False, "error_kind": "crash", "error": "NullPointerException"}
    r = S.score(answer, REQ, simulator=FakeSim(reply))
    assert r.stage == "build" and r.score == ladder.stage("build").floor


@pytest.mark.parametrize("reply", [None, {}, [], "text", {"ok": True}, {"ok": True, "flights": None},
                                   {"ok": True, "flights": [None, {}, {"ok": True}], "components": "x"},
                                   {"ok": True, "rocket": {"mass_kg": None}, "components": [{"type": 3}],
                                    "flights": [{"ok": True, "apogee_m": None, "branches": [None]}] * 3}])
def test_odd_replies_give_a_normal_result(quiet, gold_rows, reply):
    answer, _ = _first_passing(gold_rows)
    r = S.score(answer, REQ, simulator=FakeSim(lambda req: reply))
    assert r.score is not None and ladder.stage("build").floor <= r.score <= 1.0
    assert r.stage in ("build", "flight", "targets")


def test_a_recorded_reply_gives_a_score_in_a_band(quiet, gold_rows):
    answer, _ = _first_passing(gold_rows)
    for name in ("single_stage", "two_stage"):
        r = S.score(answer, REQ, simulator=FakeSim(load_reply(name)))
        s = ladder.stage(r.stage)
        assert s.floor <= r.score <= s.top and r.reasons is not None


def test_a_file_that_cannot_be_written_is_a_build_failure(quiet, monkeypatch, gold_rows):
    from rocket_reward.ork import OrkWriteError
    answer, _ = _first_passing(gold_rows)

    def no_file(root):
        raise OrkWriteError("tag 'x y' is not an XML name")

    monkeypatch.setattr(S, "_write_ork", no_file)
    sim = FakeSim()
    r = S.score(answer, REQ, simulator=sim)
    assert r.stage == "build" and r.score == 0.40 and "XML name" in r.reasons[0] and sim.calls == []


def test_setup_errors_from_the_simulator_are_raised(quiet, gold_rows):
    answer, _ = _first_passing(gold_rows)

    def broken(req):
        raise RewardSetupError("the self-test rocket failed")

    with pytest.raises(RewardSetupError, match="self-test"):
        S.score(answer, REQ, simulator=FakeSim(broken))
    assert S._default_tracker.errors == 0


def test_a_closed_simulator_is_a_setup_error(quiet, gold_rows):
    answer, _ = _first_passing(gold_rows)

    def closed(req):
        raise RuntimeError("this Simulator is closed")

    with pytest.raises(RewardSetupError, match="closed"):
        S.score(answer, REQ, simulator=FakeSim(closed))


def test_a_crash_inside_stage_6_is_quarantined(quiet, monkeypatch, gold_rows):
    answer, _ = _first_passing(gold_rows)
    Stages(monkeypatch)

    def boom(reply, requirements):
        raise ZeroDivisionError("wind divided by zero")

    monkeypatch.setattr(S, "_check_flight", boom)
    r = S.score(answer, REQ, simulator=FakeSim())
    assert r.score is None and r.flags["quarantined"] and r.stages_passed == 4
    assert list((quiet / "quarantine").glob("*.json"))


# ------------------------------------------------------------------ shadow flights

def _invented(answer: str, designation: str = "H1650R") -> str:
    """The same answer with the first flown motor renamed to a motor that does not exist."""
    import json
    tree = design_of(answer, root_only=True)
    from rocket_reward.motors import flown_motors
    motor = flown_motors(tree)[0]
    kids = [c for c in motor["motor"]["children"] if next(iter(c)) not in ("motor_id", "designation")]
    kids += [{"motor_id": {"value": "AeroTech-" + designation}}, {"designation": {"value": designation}}]
    motor["motor"]["children"] = kids
    return "<design>" + json.dumps(tree) + "</design>"


def test_shadow_credit_follows_the_rule(quiet, monkeypatch, gold_rows):
    answer, _ = _first_passing(gold_rows)
    st = Stages(monkeypatch)
    st.targets = StageCheck("targets", True, 0.5)
    bad = _invented(answer)
    r = S.score(bad, REQ, simulator=FakeSim())
    shadow = r.flags["shadow"]
    assert r.stage == "motor" and shadow["stage"] == "targets"
    floor = ladder.stage("limits").floor
    assert shadow["progress"] == pytest.approx((shadow["score"] - floor) / (1 - floor))
    want = ladder.MOTOR_FACTS_SHARE * r.flags["motor_facts_credit"] + ladder.MOTOR_SHADOW_SHARE * shadow["progress"]
    assert r.credit == pytest.approx(want)
    assert r.score == ladder.stage_score("motor", want, len(r.defects))
    assert shadow["substitutes"][0]["written"] == "AeroTech-H1650R"
    assert "nearest real motor" in r.reasons[-1] and shadow["substitutes"][0]["substitute"] in r.reasons[-1]
    # preflight never flies: facts only
    pre_r = S.preflight_result(S.preflight(bad))
    assert pre_r.score == ladder.stage_score("motor", r.flags["motor_facts_credit"], len(pre_r.defects))


def test_shadow_reason_says_why_the_stand_in_stopped(quiet, monkeypatch, gold_rows):
    """A student reading 'would stop at the build stage' needs the cause: the
    shadow's own first reason is quoted. A shadow that reaches targets adds none."""
    answer, _ = _first_passing(gold_rows)
    st = Stages(monkeypatch)
    st.build = StageCheck("build", False, 0.5, reasons=["the fins sit past the tail by 2 chords"])
    r = S.score(_invented(answer), REQ, simulator=FakeSim())
    assert r.flags["shadow"]["stage"] == "build"
    assert r.flags["shadow"]["reason"] == "the fins sit past the tail by 2 chords"
    assert r.reasons[-1].endswith(", because the fins sit past the tail by 2 chords")
    assert "fits its mount" in r.reasons[-1]
    st.build = StageCheck("build", False, 0.5, reasons=["x" * 1000])
    long = S.score(_invented(answer), REQ, simulator=FakeSim())
    assert long.reasons[-1].endswith("...") and len(long.reasons[-1]) < 600
    st.build = StageCheck("build", True, 1.0)
    st.targets = StageCheck("targets", True, 0.5, reasons=["apogee 10 m short"])
    ok = S.score(_invented(answer), REQ, simulator=FakeSim())
    assert ok.flags["shadow"]["reason"] is None and "because" not in ok.reasons[-1]


def test_a_real_motor_beats_the_same_design_with_an_invented_one(quiet, monkeypatch, gold_rows):
    answer, _ = _first_passing(gold_rows)
    st = Stages(monkeypatch)
    st.build = StageCheck("build", False, 0.0)      # the worst a real motor can do after stage 4
    real = S.score(answer, REQ, simulator=FakeSim())
    st.build = StageCheck("build", True, 1.0)       # the best an invented one can do
    st.targets = StageCheck("targets", True, 1.0)
    fake = S.score(_invented(answer), REQ, simulator=FakeSim())
    assert fake.stage == "motor" and fake.score <= ladder.stage("motor").top < real.score


def test_shadow_never_leaves_the_motor_band(quiet, monkeypatch, gold_rows):
    answer, _ = _first_passing(gold_rows)
    st = Stages(monkeypatch)
    for t in (0.0, 1.0, 5.0, float("nan"), -2.0):
        st.targets = StageCheck("targets", True, t)
        r = S.score(_invented(answer), REQ, simulator=FakeSim())
        s = ladder.stage("motor")
        assert s.floor <= r.score <= s.top and 0.0 <= r.flags["shadow"]["progress"] <= 1.0


def test_no_class_letter_means_no_substitute_and_no_flight(quiet, gold_rows):
    answer, _ = _first_passing(gold_rows)
    sim = FakeSim()
    r = S.score(_invented(answer, "Zorp"), REQ, simulator=sim)   # 'Z' is no class a table motor has
    assert r.stage == "motor" and r.flags["shadow"]["progress"] == 0.0 and sim.calls == []
    assert r.score == ladder.stage_score("motor", ladder.MOTOR_FACTS_SHARE * r.flags["motor_facts_credit"],
                                         len(r.defects))
    assert "no real motor could stand in" in r.reasons[-1]


def test_no_motor_at_all_starts_no_simulator(quiet, monkeypatch):
    def never(size):
        raise AssertionError("the default simulator must not start")

    monkeypatch.setattr(S, "_sim_cache", [])
    monkeypatch.setattr(S, "_start_simulator", never)
    tree = ('<design>{"openrocket": {"children": [{"rocket": {"children": [{"subcomponents": {"children": '
            '[{"stage": {"children": []}}]}}]}}]}}</design>')
    r = S.score(tree, REQ)
    assert r.stage in ("parts", "motor")


# ------------------------------------------------------------------ nearest real motor

def test_nearest_real_motor(table):
    first = table.nearest_real("H1650R", 0.038)
    assert first == table.nearest_real("H1650R", 0.038)          # the same every time
    e = table.get(first)
    assert table.class_has_diameter("H", 0.038) and abs(e["diameter_m"] - 0.038) <= 0.0005
    same_size = [table.get(k) for k in table._class_keys["H"]
                 if abs(table.get(k)["diameter_m"] - 0.038) <= 0.0005]
    best = min(abs(x["average_thrust_n"] - 1650) for x in same_size)
    assert abs(e["average_thrust_n"] - 1650) == best
    assert table.nearest_real("G80T", 0.029) == "AeroTech-G80T"   # a real one finds itself
    assert table.nearest_real("Zorp", 0.03) is None
    assert table.nearest_real(None, 0.03) is None and table.nearest_real(12, 0.03) is None
    far = table.nearest_real("H1650R", 5.0)                     # no H motor is 5 m wide
    assert far is not None and table.get(far)["diameter_m"] == max(table.diameters_for_class("H"))
    assert table.nearest_real("H1650R", float("nan")) is not None


def test_written_average_thrust():
    assert written_average_thrust("H1650R") == 1650.0
    assert written_average_thrust("1109J440-P") == 440.0
    assert written_average_thrust("HP-H195NT-v2") == 195.0
    assert written_average_thrust("BB-54-1750") is None
    assert written_average_thrust("440CC098J") is None
    assert written_average_thrust(None) is None and written_average_thrust("x" * 500) is None


def test_ties_break_by_impulse_then_id():
    entries = {
        "A-H100X": {"manufacturer": "A", "designation": "H100X", "diameter_m": 0.029,
                    "average_thrust_n": 100.0, "total_impulse_ns": 200.0},
        "B-H100Y": {"manufacturer": "B", "designation": "H100Y", "diameter_m": 0.029,
                    "average_thrust_n": 100.0, "total_impulse_ns": 180.0},
        "C-H100Z": {"manufacturer": "C", "designation": "H100Z", "diameter_m": 0.029,
                    "average_thrust_n": 100.0, "total_impulse_ns": 180.0},
    }
    t = MotorTable(entries)
    assert t.nearest_real("H100Q", 0.029) == "B-H100Y"
    assert t.nearest_real("H100Q", 0.054) == "B-H100Y"   # nearest size the class has


def test_substitution_leaves_the_input_alone(table, gold_rows):
    import json
    answer, _ = _first_passing(gold_rows)
    tree = design_of(_invented(answer), root_only=True)
    before = json.dumps(tree)
    shadow, subs = substitute_unknown_motors(tree, table)
    assert json.dumps(tree) == before and shadow is not None and len(subs) >= 1
    from rocket_reward.motors import check_motors
    assert check_motors(shadow, table).passed
    real, none = substitute_unknown_motors(design_of(answer, root_only=True), table)
    assert real is None and none == []


def _invented_with(answer: str, designation: str, diameter) -> str:
    """_invented, with the written motor diameter set to `diameter` (None: removed)."""
    import json
    from rocket_reward.motors import flown_motors
    tree = design_of(_invented(answer, designation), root_only=True)
    motor = flown_motors(tree)[0]
    kids = [c for c in motor["motor"]["children"] if next(iter(c)) != "diameter"]
    if diameter is not None:
        kids.append({"diameter": {"value": diameter}})
    motor["motor"]["children"] = kids
    return "<design>" + json.dumps(tree) + "</design>"


def test_fitting_diameter(table):
    sizes = sorted(table.diameters_for_class("J"))
    assert table.fitting_diameter("J", 0.0381) == max(d for d in sizes if d <= 0.0381 * 1.05)
    assert table.fitting_diameter("J", 0.001) == sizes[0]            # nothing fits: the smallest
    assert table.fitting_diameter("J", 10.0) == sizes[-1]
    for bad in (None, 0.0, -1.0, float("nan"), "0.04", True):
        assert table.fitting_diameter("J", bad) is None
    assert table.fitting_diameter("Zorp", 0.04) is None


def test_substitute_size_comes_from_the_mount_not_the_written_diameter(table, gold_rows):
    """Writing a true fact (a real diameter of the class) never picks a worse
    substitute: the substitute is chosen from the mount's inside diameter."""
    from rocket_reward.motors import mount_motors, mount_room_m
    answer, _ = _first_passing(gold_rows)
    picks = set()
    for dia in (0.040, 0.081, 0.054, 0.0001, None, "big"):
        tree = design_of(_invented_with(answer, "J547QX", dia), root_only=True)
        _, subs = substitute_unknown_motors(tree, table)
        picks.add(subs[0]["substitute"])
    assert len(picks) == 1
    tree = design_of(_invented_with(answer, "J547QX", 0.081), root_only=True)
    room = next(mount_room_m(m) for m, _ in mount_motors(tree))
    sub = table.get(substitute_unknown_motors(tree, table)[1][0]["substitute"])
    assert room is not None and sub["diameter_m"] == pytest.approx(table.fitting_diameter("J", room))


def test_true_class_diameter_never_lowers_the_motor_score(quiet, gold_rows):
    """Fact 3 true (a real J diameter, here one that does not match the mount)
    scores at least as high as fact 3 false on the same mount."""
    answer, _ = _first_passing(gold_rows)
    sim = FakeSim()
    false_fact = S.score(_invented_with(answer, "J547QX", 0.040), REQ, simulator=sim)
    true_fact = S.score(_invented_with(answer, "J547QX", 0.081), REQ, simulator=sim)
    assert false_fact.stage == true_fact.stage == "motor"
    assert true_fact.flags["motor_facts_credit"] > false_fact.flags["motor_facts_credit"]
    assert true_fact.flags["shadow"]["substitutes"][0]["substitute"] ==         false_fact.flags["shadow"]["substitutes"][0]["substitute"]
    assert true_fact.score >= false_fact.score


def test_motor_type_of():
    from rocket_reward.motors import motor_type_of
    assert motor_type_of("single") == motor_type_of(" Single-Use ") == "Single-use"
    assert motor_type_of("reload") == motor_type_of("RELOADABLE") == "Reloadable"
    assert motor_type_of("hybrid") == "Hybrid"
    for bad in ("unknown", "", None, 3, "x" * 500, ["reload"]):
        assert motor_type_of(bad) is None


def _typed_table() -> MotorTable:
    def motor(maker, des, kind, thrust, dia=0.029, ns=200.0):
        return {"manufacturer": maker, "designation": des, "diameter_m": dia, "motor_type": kind,
                "average_thrust_n": thrust, "total_impulse_ns": ns}
    return MotorTable({
        "A-H100S": motor("A", "H100S", "Single-use", 100.0),
        "A-H150R": motor("A", "H150R", "Reloadable", 150.0),
        "B-H100R": motor("B", "H100R", "Reloadable", 100.0, ns=190.0),
        "C-H100H": motor("C", "H100H", "Hybrid", 100.0, ns=210.0),
        "D-H100R": motor("D", "H100R", "Reloadable", 100.0, dia=0.054),   # does not fit a 29 mm mount
    })


def test_nearest_real_prefers_the_written_type_then_the_maker():
    t = _typed_table()
    assert t.nearest_real("H100Q", 0.029) == "B-H100R"                       # thrust, then impulse
    assert t.nearest_real("H100Q", 0.029, motor_type="single") == "A-H100S"
    assert t.nearest_real("H100Q", 0.029, motor_type="hybrid") == "C-H100H"
    assert t.nearest_real("H100Q", 0.029, maker="a") == "A-H100S"            # maker, letter case ignored
    assert t.nearest_real("H100Q", 0.029, maker="A", motor_type="reload") == "A-H150R"
    # the type comes first: no hybrid of maker A, so the hybrid of another maker
    assert t.nearest_real("H100Q", 0.029, maker="A", motor_type="hybrid") == "C-H100H"
    # nothing of that maker or type: the rule falls back to the rest
    assert t.nearest_real("H100Q", 0.029, maker="Nobody", motor_type="unknown") == "B-H100R"
    assert t.nearest_real("H100Q", 0.029, maker="D") == "B-H100R"            # D has none that fits
    # never outside the class and the fitting size
    for maker in (None, "A", "B", "C", "D"):
        for kind in (None, "single", "reload", "hybrid"):
            k = t.nearest_real("H100Q", 0.029, maker=maker, motor_type=kind)
            assert k == t.nearest_real("H100Q", 0.029, maker=maker, motor_type=kind)   # the same every time
            assert t.get(k)["diameter_m"] == 0.029


def _invented_by(answer: str, maker: str, designation: str, motor_type=None) -> str:
    """_invented with the maker (and its motor id) and the motor type set."""
    import json
    from rocket_reward.motors import flown_motors
    tree = design_of(_invented(answer, designation), root_only=True)
    motor = flown_motors(tree)[0]
    kids = [c for c in motor["motor"]["children"] if next(iter(c)) not in ("manufacturer", "motor_id", "type")]
    kids += [{"manufacturer": {"value": maker}}, {"motor_id": {"value": f"{maker}-{designation}"}}]
    if motor_type is not None:
        kids.append({"type": {"value": motor_type}})
    motor["motor"]["children"] = kids
    return "<design>" + json.dumps(tree) + "</design>"


def _fitting_candidates(table, answer, letter):
    from rocket_reward.motors import mount_motors, mount_room_m
    tree = design_of(answer, root_only=True)
    size = table.fitting_diameter(letter, next(mount_room_m(m) for m, _ in mount_motors(tree)))
    return size, [k for k in table._class_keys[letter] if abs(table.get(k)["diameter_m"] - size) <= 0.0005]


def test_substitute_has_the_written_type_and_maker_when_one_fits(table, gold_rows):
    answer, _ = _first_passing(gold_rows)
    size, fits = _fitting_candidates(table, answer, "H")
    for written, kind in (("single", "Single-use"), ("reload", "Reloadable"), ("hybrid", "Hybrid")):
        tree = design_of(_invented_by(answer, "Nobody", "H1650R", written), root_only=True)
        sub = substitute_unknown_motors(tree, table)[1][0]["substitute"]
        assert abs(table.get(sub)["diameter_m"] - size) <= 0.0005
        if any(table.get(k)["motor_type"] == kind for k in fits):
            assert table.get(sub)["motor_type"] == kind
    makers = sorted({table.get(k)["manufacturer"] for k in fits})
    assert len(makers) >= 2
    for maker in makers:
        tree = design_of(_invented_by(answer, maker, "H1650R"), root_only=True)
        sub = substitute_unknown_motors(tree, table)[1][0]["substitute"]
        assert table.get(sub)["manufacturer"] == maker
        plain = substitute_unknown_motors(tree, table, same_maker=False)[1][0]["substitute"]
        assert plain == table.nearest_real("H1650R", size)


@pytest.mark.parametrize("worse", ["same_maker", "plain"])
def test_a_true_maker_never_lowers_the_motor_score(quiet, table, gold_rows, worse):
    """Naming a real maker makes fact 1 true and also changes the substitute;
    whichever of the two substitutes flies worse, the true maker never scores lower."""
    answer, _ = _first_passing(gold_rows)
    size, fits = _fitting_candidates(table, answer, "H")
    plain = table.nearest_real("H1650R", size)
    maker = next(m for m in sorted({table.get(k)["manufacturer"] for k in fits})
                 if m != table.get(plain)["manufacturer"])
    preferred = table.nearest_real("H1650R", size, maker=maker)
    assert preferred != plain
    bad_digest = table.get(preferred if worse == "same_maker" else plain)["digest"]

    def reply(call):
        if bad_digest in call["ork"]:
            return {"ok": False, "error_kind": "build", "message": "build"}
        return load_reply("single_stage")

    false_fact = S.score(_invented_by(answer, "Nobody Rocketry", "H1650R"), REQ, simulator=FakeSim(reply))
    true_fact = S.score(_invented_by(answer, maker, "H1650R"), REQ, simulator=FakeSim(reply))
    assert false_fact.stage == true_fact.stage == "motor"
    assert true_fact.flags["motor_facts_credit"] > false_fact.flags["motor_facts_credit"]
    assert true_fact.score >= false_fact.score
    kept = true_fact.flags["shadow"]["substitutes"][0]["substitute"]
    assert kept == (plain if worse == "same_maker" else preferred)
    assert kept in true_fact.reasons[-1]


def test_mount_room_reads_the_tube_as_written():
    from rocket_reward.motors import mount_room_m
    from rocket_reward.tree import make_node

    def tube(tag, **fields):
        return make_node(tag, children=[make_node(k, value=v) for k, v in fields.items()])

    assert mount_room_m(tube("innertube", outerradius=0.02, thickness=0.001)) == pytest.approx(0.038)
    assert mount_room_m(tube("bodytube", radius=0.03, thickness=0.002)) == pytest.approx(0.056)
    assert mount_room_m(tube("bodytube", radius=0.03)) == pytest.approx(0.06)
    for bad in (tube("bodytube", radius="auto"), tube("innertube", outerradius=-1.0),
                tube("bodytube", radius=0.03, thickness="filled"), tube("bodytube", radius=0.01, thickness=0.02),
                tube("nosecone", radius=0.03), {"innertube": 5}, None):
        assert mount_room_m(bad) is None


# ------------------------------------------------------------------ score_many and the default simulator

def test_score_many_keeps_the_order(quiet, gold_rows):
    sim = FakeSim(size=3)
    answers = [r["answer"] for r in gold_rows[:6]] + ["no design here", _invented(gold_rows[0]["answer"])]
    many = S.score_many(answers, [REQ] * len(answers), simulator=sim)
    one = [S.score(a, REQ, simulator=sim) for a in answers]
    assert [m.to_dict() for m in many] == [o.to_dict() for o in one]


def test_score_many_checks_its_lists(quiet):
    with pytest.raises(ValueError):
        S.score_many(["a", "b"], [REQ])
    with pytest.raises(ValueError):
        S.score_many(["a"], [REQ], truncated=[True, False])
    assert S.score_many([], []) == []
    r = S.score_many(["<design>{}</design>"], [REQ], truncated=[True], simulator=FakeSim())
    assert r[0].score == 0.0 and r[0].flags["truncated"]


def test_default_workers(monkeypatch):
    monkeypatch.setattr(S.os, "cpu_count", lambda: 16)
    monkeypatch.delenv(S.WORKERS_ENV, raising=False)
    assert S.default_workers() == 4
    monkeypatch.setenv(S.WORKERS_ENV, "6")
    assert S.default_workers() == 6
    monkeypatch.setenv(S.WORKERS_ENV, "64")
    assert S.default_workers() == 15
    monkeypatch.setattr(S.os, "cpu_count", lambda: 1)
    assert S.default_workers() == 1
    for bad in ("0", "-2", "four", "2.5"):
        monkeypatch.setenv(S.WORKERS_ENV, bad)
        with pytest.raises(RewardSetupError, match=S.WORKERS_ENV):
            S.default_workers()


def test_default_simulator_starts_once_and_closes(monkeypatch):
    started = []

    class Pool:
        def __init__(self, size):
            self.size, self.closed = size, False

        def close(self):
            self.closed = True

    def start(size):
        started.append(Pool(size))
        return started[-1]

    monkeypatch.setattr(S, "_sim_cache", [])
    monkeypatch.setattr(S, "_start_simulator", start)
    monkeypatch.delenv(S.WORKERS_ENV, raising=False)
    got = []
    threads = [threading.Thread(target=lambda: got.append(S.default_simulator())) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(started) == 1 and all(g is started[0] for g in got)
    S.close_default_simulator()
    assert started[0].closed and S._sim_cache == []
