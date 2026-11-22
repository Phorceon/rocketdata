"""Tests of the real simulator link: design -> ork.py -> sim.py -> RocketSim -> OpenRocket.

Every test here needs Java 17 and the OpenRocket 24.12 jar (set
ROCKET_REWARD_JAVA_HOME and ROCKET_REWARD_JAR); without them they are skipped
by conftest.py. One helper is shared by most tests to keep the run short.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import pytest

from rocket_reward import ork, sim
from rocket_reward.errors import RewardSetupError

pytestmark = pytest.mark.needs_java

FLIGHTS = [{"wind_ms": 1.0, "seed": 1}, {"wind_ms": 2.0, "seed": 2}, {"wind_ms": 3.0, "seed": 3}]


@pytest.fixture(scope="module")
def helper():
    with sim.Simulator() as s:
        yield s
    assert s.pid is None


@pytest.fixture(scope="module", autouse=True)
def nothing_left_running():
    yield
    leaked = sim.live_processes()
    for p in leaked:
        p.kill()
        p.wait(10)
    assert leaked == [], "helper processes were left running"


def gold_design(gold_rows, n: int = 0) -> dict:
    text = gold_rows[n]["answer"]
    i = text.find("<design>")
    j = text.find("</design>", i)
    design = json.loads(text[i + len("<design>"):j])
    return {"openrocket": design["openrocket"]}


def canary_without_motor() -> str:
    text = sim.load_canary().ork_text
    stripped = re.sub(r"<motor configid=\"cfg0\">.*?</motor>", "", text, flags=re.S)
    assert stripped != text
    return stripped


def test_ping(helper):
    reply = helper.ping_reply
    assert reply["ok"] is True and reply["openrocket"] == "24.12"
    assert str(reply["java"]).startswith("17") and reply["helper"] >= 1


def test_real_flight_of_a_reference_design_has_sane_numbers(helper, gold_rows):
    root = gold_design(gold_rows)
    reply = helper.run(ork.design_to_ork(root), 1.5, FLIGHTS, config_id=ork.flight_config_id(root))
    assert reply["ok"] is True, reply
    rocket = reply["rocket"]
    assert rocket["motor_count"] >= 1 and rocket["mass_kg"] > rocket["dry_mass_kg"] > 0
    assert rocket["length_m"] > 0 and rocket["stability_cal"] is not None
    assert reply["components"] and reply["components"][0]["parent"] == -1
    assert [f["seed"] for f in reply["flights"]] == [1, 2, 3]
    for f in reply["flights"]:
        assert f["ok"] is True and f["abort"] is None
        assert 10 < f["apogee_m"] < 100000
        assert 0 < f["time_to_apogee_s"] < f["flight_time_s"]
        assert f["max_velocity_ms"] > f["rail_exit_ms"] > 0
        assert not f["hit_step_cap"] and not f["hit_time_cap"]
        main = f["branches"][0]
        assert main["landed"] is True and 0 < main["landing_total_ms"] < 100


def test_same_request_gives_identical_numbers_in_one_helper_and_a_fresh_one(helper):
    c = sim.load_canary()
    first = helper.run(c.ork_text, c.rail_m, FLIGHTS, launch=c.launch)
    again = helper.run(c.ork_text, c.rail_m, FLIGHTS, launch=c.launch)
    with sim.Simulator(canary=None) as fresh:
        other = fresh.run(c.ork_text, c.rail_m, FLIGHTS, launch=c.launch)
    for a in (again, other):
        assert json.dumps(a["flights"], sort_keys=True) == json.dumps(first["flights"], sort_keys=True)
        assert json.dumps(a["components"], sort_keys=True) == json.dumps(first["components"], sort_keys=True)


def test_design_without_a_motor_is_a_design_fault(helper):
    reply = helper.run(canary_without_motor(), 1.5, FLIGHTS)
    assert reply["ok"] is False and reply["error_kind"] == "build"
    assert "motor" in reply["message"]
    assert helper.stats["crashes"] == 0 and helper.stats["hangs"] == 0


def test_unreadable_file_is_a_load_fault(helper):
    reply = helper.run("<?xml version='1.0'?>\n<openrocket version='1.10'><rocket>", 1.5, FLIGHTS)
    assert reply["ok"] is False and reply["error_kind"] == "load"


def test_undeclared_default_configuration_needs_the_config_id(helper, gold_rows):
    """A design that declares its configuration without default="true" flies only
    when the request names the id (ork.flight_config_id)."""
    text = sim.load_canary().ork_text.replace(' default="true"', "")
    assert helper.run(text, 1.5, FLIGHTS[:1])["error_kind"] == "build"
    root_id = "cfg0"
    reply = helper.run(text, 1.5, FLIGHTS[:1], config_id=root_id)
    assert reply["ok"] is True and reply["rocket"]["motor_count"] == 1


def test_tiny_step_cap_sets_hit_step_cap(helper):
    c = sim.load_canary()
    reply = helper.run(c.ork_text, c.rail_m, FLIGHTS[:1], max_steps=10)
    f = reply["flights"][0]
    assert f["ok"] is True and f["hit_step_cap"] is True and f["steps"] <= 10
    assert f["branches"][0]["landed"] is False


def test_tiny_time_cap_sets_hit_time_cap(helper):
    c = sim.load_canary()
    f = helper.run(c.ork_text, c.rail_m, FLIGHTS[:1], max_sim_time_s=3.0)["flights"][0]
    assert f["ok"] is True and f["hit_time_cap"] is True and not f["hit_step_cap"]


def test_hang_is_killed_retried_after_the_canary_and_reported(helper):
    """A run that cannot finish within the wall-clock limit: the helper is
    killed, restarted, the canary flies, the design is retried once, then it is
    reported as a hang (a design fault). The next request works again.

    OpenRocket keeps its own time step above a floor, so a real endless flight
    is hard to build; a slow run (fine time step, three flights) against a
    0.3 s limit takes the same path through sim.py and the same kill."""
    c = sim.load_canary()
    canary_runs = helper.stats["canary_runs"]
    started = time.monotonic()
    reply = helper.run(c.ork_text, c.rail_m, FLIGHTS,
                       launch=dict(c.launch, time_step_s=0.001), timeout_s=0.3)
    assert reply["ok"] is False and reply["error_kind"] == "hang"
    assert helper.stats["canary_runs"] == canary_runs + 1
    assert time.monotonic() - started < 120
    assert helper.pid is None  # stopped after the second hang; nothing left running
    again = helper.run(c.ork_text, c.rail_m, FLIGHTS[:1], launch=c.launch)
    assert again["ok"] is True


def test_canary_flies_within_tolerance(helper):
    c = sim.load_canary()
    reply = helper.fly_canary()
    assert c.problems(reply) == []
    assert reply["load_warnings"] == []
    # this PC reproduces the stored numbers exactly; other machines may differ slightly
    for key, want in c.expected.items():
        assert reply["flights"][0][key] == pytest.approx(want, rel=1e-9)


def test_check_setup_reports_a_working_chain():
    facts = sim.check_setup()
    assert facts["openrocket"] == "24.12" and set(facts["canary"]) == set(sim.load_canary().expected)


def test_wrong_canary_numbers_raise_setup_error():
    c = sim.load_canary()
    wrong = sim.Canary(name="wrong", ork_text=c.ork_text, rail_m=c.rail_m, flights=c.flights,
                       expected={"apogee_m": c.expected["apogee_m"] * 2}, launch=c.launch)
    with pytest.raises(RewardSetupError) as err:
        sim.check_setup(canary=wrong)
    assert "wrong numbers" in str(err.value)


CANARY_MOTOR = ("<manufacturer>AeroTech</manufacturer><designation>H170M</designation>"
                "<diameter>0.038</diameter><length>0.191</length>")


def canary_with(old: str, new: str, count: int = 1) -> str:
    text = sim.load_canary().ork_text
    assert text.count(old) >= count, old
    return text.replace(old, new, count)


def dual_deploy() -> str:
    """The canary with a 0.15 m drogue opening at ejection and its 0.91 m main at 200 m."""
    drogue = ('<parachute><name>Drogue</name><axialoffset method="top">0.02</axialoffset><packedlength>0.03</packedlength>'
              '<packedradius>0.02</packedradius><cd>0.8</cd><material type="surface" density="0.067">Ripstop nylon</material>'
              '<deployevent>ejection</deployevent><deploydelay>0.0</deploydelay><diameter>0.15</diameter>'
              '<linecount>6</linecount><linelength>0.3</linelength>'
              '<linematerial type="line" density="0.0025">Tubular nylon</linematerial></parachute>')
    text = canary_with("<subcomponents><parachute>", "<subcomponents>" + drogue + "<parachute><name>Main</name>")
    return text.replace("<deployevent>ejection</deployevent><deploydelay>0.0</deploydelay><diameter>0.91</diameter>",
                        "<deployevent>altitude</deployevent><deployaltitude>200</deployaltitude>"
                        "<deploydelay>0.0</deploydelay><diameter>0.91</diameter>")


def test_every_recovery_device_counts_for_deploy_speed(helper):
    """Review finding: only the first opening was judged. With a drogue at apogee and
    the main at 200 m, the main opens much faster; deploy_speed_ms is the fastest
    opening and deployments lists both."""
    c = sim.load_canary()
    reply = helper.run(dual_deploy(), c.rail_m, [{"wind_ms": 2.0, "seed": 1}], launch=c.launch)
    assert reply["ok"] is True, reply
    b = reply["flights"][0]["branches"][0]
    names = [d["device"] for d in b["deployments"]]
    assert names == ["Drogue", "Main"], b["deployments"]
    speeds = [d["speed_ms"] for d in b["deployments"]]
    assert speeds[1] > 3 * speeds[0] and speeds[1] > 15
    assert b["deploy_speed_ms"] == max(speeds)
    assert b["deploy_time_s"] == b["deployments"][0]["time_s"] < b["deployments"][1]["time_s"]
    assert b["deploy_during_burn"] is False and not any(d["during_burn"] for d in b["deployments"])


def test_opening_during_the_burn_is_flagged_on_any_device(helper):
    """The main opens at launch, while the motor burns; the drogue opens later."""
    text = dual_deploy().replace("<deployevent>altitude</deployevent><deployaltitude>200</deployaltitude>",
                                 "<deployevent>launch</deployevent>")
    c = sim.load_canary()
    f = helper.run(text, c.rail_m, [{"wind_ms": 2.0, "seed": 1}], launch=c.launch)["flights"][0]
    b = f["branches"][0]
    assert b["deploy_during_burn"] is True
    assert any(d["during_burn"] for d in b["deployments"])


def test_landing_speed_is_read_at_the_touchdown_sample(helper):
    c = sim.load_canary()
    f = helper.run(c.ork_text, c.rail_m, [{"wind_ms": 2.0, "seed": 1}], launch=c.launch)["flights"][0]
    main = f["branches"][0]
    assert main["landing_total_ms"] == f["ground_hit_ms"]
    assert main["landing_time_s"] == main["last_time_s"] == f["flight_time_s"]


def test_landing_speed_is_the_touchdown_speed_when_openrocket_keeps_simulating(helper, model_rows):
    """Model answer row-023 lands while its motor still burns; OpenRocket keeps
    simulating it on the ground, so its last sample is at rest. The landing
    speeds are read at the GROUND_HIT moment instead (about 6.9 m/s since the
    cleaning removes its mass overrides; 8.4 m/s with them)."""
    from rocket_reward import Requirements, scoring
    from rocket_reward.flight import flight_plan, rail_length_m

    row = next(r for r in model_rows if r["id"].startswith("row-023"))
    root = scoring.preflight(row["content"]).clean_root
    flights = flight_plan(Requirements.from_dict({"id": "r", "apogee_m": {"value": 100, "kind": "about"}}))
    reply = helper.run(ork.design_to_ork(root), rail_length_m(root, scoring.default_motor_table()), flights,
                       config_id=ork.flight_config_id(root))
    for f in reply["flights"]:
        main = f["branches"][0]
        assert main["landed"] and main["landing_time_s"] < main["last_time_s"] - 1.0   # kept simulating
        assert 6.0 < main["landing_vertical_ms"] <= main["landing_total_ms"] < 10.0
        assert main["landing_total_ms"] == pytest.approx(f["ground_hit_ms"], rel=1e-9)


@pytest.mark.parametrize("old, new", [
    ("<mass>0.06</mass>", "<mass>NaN</mass>"),
    ("<mass>0.06</mass>", "<mass>Infinity</mass>"),
    ("<diameter>0.91</diameter>", "<diameter>NaN</diameter>"),
    ("<radius>0.033</radius>", "<radius>NaN</radius>"),
])
def test_value_openrocket_skips_is_a_build_fault(helper, old, new):
    """Review finding: OpenRocket skips a value it cannot read and keeps a default, so a
    different rocket flew with ok true. The helper makes it a build fault."""
    reply = helper.run(canary_with(old, new), 1.5, FLIGHTS[:1])
    assert reply["ok"] is False and reply["error_kind"] == "build", reply
    assert "Invalid parameter encountered" in reply["message"]


def test_rocket_without_a_finite_mass_is_a_build_fault_not_a_flight(helper):
    """Review finding: a NaN density crashed OpenRocket inside the flight, which came
    back as an aborted flight with apogee 0. Now it stops at the build stage."""
    reply = helper.run(canary_with('density="950.0"', 'density="NaN"'), 1.5, FLIGHTS[:1])
    assert reply["ok"] is False and reply["error_kind"] == "build", reply
    assert "mass_kg" in reply["message"]


def test_abort_text_is_plain_and_an_abort_is_not_a_crash(helper):
    """An aborted flight keeps ok true and its numbers; its reason has no HTML."""
    reply = helper.run(canary_with("<mass>0.06</mass>", "<mass>500</mass>"), 1.5, FLIGHTS[:1])
    f = reply["flights"][0]
    assert f["ok"] is True and "error_kind" not in f
    assert f["abort"] == "Motor burnout without liftoff. Use more (powerful) motors, or decrease the rocket mass."
    assert all("<" not in w for w in f["warnings"] + reply["load_warnings"])


def test_rocket_that_never_starts_flying_is_a_failed_flight_but_not_a_crash(helper):
    c = sim.load_canary()
    text = canary_with("<ignitiondelay>0.0</ignitiondelay>", "<ignitiondelay>5000</ignitiondelay>")
    crashes = helper.stats["flight_crashes"]
    f = helper.run(text, c.rail_m, FLIGHTS[:1], launch=c.launch)["flights"][0]
    assert f["ok"] is False and f["error_kind"] == "build" and "never started" in f["error"]
    assert helper.stats["flight_crashes"] == crashes  # not retried as machine trouble


def test_first_ignition_time_is_reported(helper):
    """ignition_time_s is 0 for a motor lit at launch and the delay for one lit
    later; the rocket waits on the pad meanwhile, so the flight is the same
    flight shifted by the delay (targets.py measures times from it)."""
    c = sim.load_canary()
    now = helper.run(c.ork_text, c.rail_m, FLIGHTS[:1], launch=c.launch)["flights"][0]
    text = canary_with("<ignitiondelay>0.0</ignitiondelay>", "<ignitiondelay>3.0</ignitiondelay>")
    later = helper.run(text, c.rail_m, FLIGHTS[:1], launch=c.launch)["flights"][0]
    assert now["ok"] is True and later["ok"] is True
    assert now["ignition_time_s"] == 0.0
    assert later["ignition_time_s"] == pytest.approx(3.0, abs=0.06)
    for key in ("flight_time_s", "time_to_apogee_s"):
        assert later[key] - later["ignition_time_s"] == pytest.approx(now[key], rel=0.02, abs=0.1), key
    assert later["apogee_m"] == pytest.approx(now["apogee_m"], rel=0.02)


def motor_design(v: dict) -> str:
    """The canary rocket flying the motor described by `v` (maker, designation,
    digest and diameter, as a table entry holds them), with no motor type."""
    text = canary_with(CANARY_MOTOR, f"<manufacturer>{v['manufacturer']}</manufacturer>"
                                     f"<designation>{v['designation']}</designation><digest>{v['digest']}</digest>")
    return text.replace("<type>reload</type>", "").replace(
        "<outerradius>0.0205</outerradius>", f"<outerradius>{v['diameter_m'] / 2 + 0.0005}</outerradius>")


# Two motors of the earlier (1,421-id) table that OpenRocket 24.12 cannot fly by
# digest, with the digests that table gave them. Neither is in today's table.
OLD_G75J_V4 = {"manufacturer": "AeroTech", "designation": "G75J", "diameter_m": 0.029,
               "digest": "8cc88c1180b7ded51fd377cec51cde52"}
OLD_ASAT_M2544 = {"manufacturer": "ASAT", "designation": "M2544", "diameter_m": 0.1,
                  "digest": "0331491ff5c7a85e6c1dfa6edf9e0b66"}


@pytest.mark.parametrize("motor, found_by, flown", [
    ("AeroTech-H170M", "digest", "H170M"),
    ("AeroTech-G75J-v4", "digest", "G75J"),  # re-pointed to the curve OpenRocket has
    (OLD_G75J_V4, "name", "G75M"),           # an unknown digest: OpenRocket flies another motor
    (OLD_ASAT_M2544, "none", None),          # OpenRocket has no such motor at all
])
def test_each_motor_says_how_openrocket_found_it(helper, motor, found_by, flown):
    """Owner's decision (b): per motor, found by digest, by name only, or not at all."""
    v = ork.motor_table_entries()[motor] if isinstance(motor, str) else motor
    reply = helper.run(motor_design(v), 1.5, FLIGHTS[:1])
    lookup = reply["motor_lookup"]
    assert len(lookup) == 1 and lookup[0]["found_by"] == found_by
    assert lookup[0]["requested_digest"] == v["digest"]
    assert lookup[0]["flown_designation"] == flown
    if found_by == "digest":
        assert reply["ok"] is True and reply["rocket"]["motor_substituted"] is False
        m = next(c["motor"] for c in reply["components"] if c["motor"])
        assert m["found_by"] == "digest" and m["requested_digest"] == m["digest"]
    else:  # never flown as the requested motor: a build fault that names the motor
        assert reply["ok"] is False and reply["error_kind"] == "build"
        assert v["designation"] in reply["message"]
    if found_by == "name":  # parity checks may still fly the substitute, and see that they do
        allowed = helper.run(motor_design(v), 1.5, FLIGHTS[:1], allow_motor_substitution=True)
        m = next(c["motor"] for c in allowed["components"] if c["motor"])
        assert allowed["rocket"]["motor_substituted"] is True
        assert m["found_by"] == "name" and m["substituted"] is True and m["designation"] == flown


def test_forcing_the_file_version_changes_no_flight_number(helper, gold_rows):
    """The cleaning writes version 1.10 (what OpenRocket 24.12 writes). On the
    reference designs that wrote another version, the flights are identical
    either way (all 72 such reference designs were checked once by hand)."""
    from rocket_reward.scoring import preflight
    tried = 0
    for row in gold_rows:
        own = gold_design(gold_rows, gold_rows.index(row))["openrocket"].get("attrs", {}).get("version")
        if str(own) == "1.10":
            continue
        pre = preflight(row["answer"])
        assert pre.passed, row["id"]
        forced = ork.design_to_ork(pre.clean_root)
        back = forced.replace('<openrocket version="1.10"', f'<openrocket version="{own}"', 1)
        assert back != forced
        cid = ork.flight_config_id(pre.clean_root)
        a = helper.run(forced, 1.5, FLIGHTS[:1], config_id=cid)
        b = helper.run(back, 1.5, FLIGHTS[:1], config_id=cid)
        assert a["ok"] and b["ok"], row["id"]
        for k in ("apogee_m", "max_velocity_ms", "flight_time_s", "rail_exit_ms"):
            assert a["flights"][0][k] == b["flights"][0][k], (row["id"], own, k)
        tried += 1
        if tried == 4:
            break
    assert tried >= 1


def test_motor_list_holds_every_table_digest(helper):
    """The table was rebuilt from OpenRocket's own list (tools/build_motor_table.py):
    every digest it holds is one OpenRocket 24.12 lists. The helper counts list
    entries (1,452); they hold 1,389 distinct thrust curves."""
    listed = helper.motor_list()
    assert len(listed) == helper.ping_reply["motor_database_size"] == 1452
    digests = {m["digest"] for m in listed}
    assert len(digests) == 1389
    missing = {k for k, v in ork.motor_table_entries().items() if v.get("digest") not in digests}
    assert missing == set()


def test_every_table_motor_is_found_by_digest():
    """Fly the probe rocket once for every table id, as the cleaned file names
    it (maker, designation, the table's digest, no motor type): OpenRocket must
    find each one by its digest and fly that very curve, never a substitute."""
    entries = ork.motor_table_entries()
    keys = sorted(entries)
    assert len(keys) == 1409
    requests = [dict(ork_text_or_path=motor_design(entries[k]), rail_m=1.5,
                     flights=[{"wind_ms": 2.0, "seed": 1}], allow_motor_substitution=True,
                     max_sim_time_s=5.0) for k in keys]
    with sim.SimPool(4, canary=None) as pool:
        replies = pool.run_many(requests)
    bad = []
    for k, r in zip(keys, replies):
        look = (r.get("motor_lookup") or [{}])[0]
        if look.get("found_by") != "digest" or look.get("flown_digest") != entries[k]["digest"]:
            bad.append((k, look.get("found_by"), r.get("error_kind")))
    assert bad == []


def test_request_the_real_helper_cannot_read_is_marked_request(helper):
    """The helper answers a malformed request with error_kind "request", never "internal"."""
    with helper._lock:
        reply = helper._request({"op": "run", "id": "bad1", "ork": "x.ork", "rail_m": 1.5,
                                 "flights": [{"wind_ms": -1.0, "seed": 1}]}, "bad1", 60)
        assert reply["ok"] is False and reply["error_kind"] == "request" and "wind_ms" in reply["message"]
        reply = helper._request({"op": "run", "id": "bad2", "ork": "x.ork", "rail_m": 1.5, "flights": [],
                                 "launch": {"rod_angle": 5}}, "bad2", 60)
        assert reply["error_kind"] == "request" and "rod_angle" in reply["message"]


def _alive(pid: int) -> bool:
    if sys.platform == "win32":
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True).stdout
        return str(pid) in out
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


ORPHAN_CHILD = """
import sys
sys.path.insert(0, sys.argv[1])
from rocket_reward import sim
c = sim.load_canary()
s = sim.Simulator(canary=None)
print(s.pid, flush=True)
s.run(c.ork_text, c.rail_m, [{"wind_ms": 2.0, "seed": i} for i in range(1, 9)],
      launch=dict(c.launch, time_step_s=0.0005), timeout_s=3000)
"""


def test_helper_exits_when_its_python_parent_is_killed_mid_request(tmp_path):
    """Review finding: a helper kept flying (and holding 600 MB) after its parent died."""
    script = tmp_path / "child.py"
    script.write_text(ORPHAN_CHILD, encoding="utf-8", newline="\n")
    temp = tmp_path / "tmp"  # the killed child cannot delete its temporary .ork; keep it in pytest's folder
    temp.mkdir()
    env = dict(os.environ, TMPDIR=str(temp), TEMP=str(temp), TMP=str(temp))
    child = subprocess.Popen([sys.executable, str(script), str(Path(sim.__file__).resolve().parents[1])],
                             stdout=subprocess.PIPE, text=True, env=env)
    java_pid = None
    try:
        java_pid = int(child.stdout.readline().strip())
        time.sleep(3.0)  # the long request is now running inside the helper
        assert _alive(java_pid)
        child.kill()  # a hard kill: no atexit, no close()
        child.wait(30)
        deadline = time.monotonic() + 20
        while _alive(java_pid) and time.monotonic() < deadline:
            time.sleep(0.25)
        assert not _alive(java_pid), "the helper kept running after its parent was killed"
    finally:
        if child.poll() is None:
            child.kill()
        if java_pid is not None and _alive(java_pid):
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/F", "/PID", str(java_pid)], capture_output=True)
            else:
                os.kill(java_pid, 9)


def test_pool_of_two_gives_the_same_numbers_as_one_helper(helper):
    c = sim.load_canary()
    want = helper.run(c.ork_text, c.rail_m, FLIGHTS, launch=c.launch)["flights"]
    request = {"ork_text_or_path": c.ork_text, "rail_m": c.rail_m, "flights": FLIGHTS, "launch": c.launch}
    with sim.SimPool(2, canary=None) as pool:
        replies = pool.run_many([request] * 4)
    for r in replies:
        assert json.dumps(r["flights"], sort_keys=True) == json.dumps(want, sort_keys=True)
