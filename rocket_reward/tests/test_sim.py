"""Tests for sim.py.

Most tests drive sim.py with tests/fake_helper.py, a Python stand-in for the
Java helper that can misbehave on purpose. Tests marked needs_java use the
real JDK and OpenRocket jar (set ROCKET_REWARD_JAVA_HOME and ROCKET_REWARD_JAR).
After every test no helper process may still be running and no temporary .ork
file may be left behind.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

from rocket_reward import sim
from rocket_reward.errors import RewardSetupError

HERE = Path(__file__).resolve().parent
FAKE = [sys.executable, str(HERE / "fake_helper.py")]
FLIGHTS = [{"wind_ms": 1.0, "seed": 1}, {"wind_ms": 2.0, "seed": 2}, {"wind_ms": 3.0, "seed": 3}]


def ork(marker: str = "") -> str:
    """A small .ork text; the fake helper reacts to the marker."""
    return f'<?xml version="1.0"?>\n<openrocket version="1.10"><!-- {marker} --><rocket/></openrocket>\n'


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    """Own cache and temp folders; afterwards check nothing is left running or lying around."""
    cache = tmp_path / "cache"
    temp = tmp_path / "tmp"
    temp.mkdir()
    monkeypatch.setenv(sim.ENV_CACHE, str(cache))
    monkeypatch.setattr(tempfile, "tempdir", str(temp))
    for key in list(os.environ):
        if key.startswith("FAKE_HELPER_"):
            monkeypatch.delenv(key)
    state = tmp_path / "state"
    state.mkdir()
    monkeypatch.setenv("FAKE_HELPER_STATE_DIR", str(state))
    yield temp
    leaked = sim.live_processes()
    for p in leaked:
        p.kill()
        p.wait(10)
    assert leaked == [], "helper processes were left running"
    left = list(temp.glob("*.ork"))
    assert left == [], f"temporary .ork files were left behind: {left}"


@pytest.fixture
def simulator():
    with sim.Simulator(FAKE) as s:
        yield s


def log_text(s: sim.Simulator) -> str:
    return s.log_path.read_text(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------- finding Java and the jar

def test_parse_java_version():
    assert sim.parse_java_version('openjdk version "17.0.21" 2026-10-20\n') == ("17.0.21", 17)
    assert sim.parse_java_version('java version "1.8.0_402"') == ("1.8.0_402", 8)
    assert sim.parse_java_version('openjdk version "21" 2023-09-19') == ("21", 21)
    assert sim.parse_java_version("command not found") is None


def test_java_home_setting_that_is_wrong_is_reported(tmp_path, monkeypatch):
    monkeypatch.setenv(sim.ENV_JAVA_HOME, str(tmp_path / "nojdk"))
    with pytest.raises(RewardSetupError) as err:
        sim.find_java()
    assert sim.ENV_JAVA_HOME in str(err.value) and "bin/java" in str(err.value)


def test_no_java_anywhere(tmp_path, monkeypatch):
    monkeypatch.delenv(sim.ENV_JAVA_HOME, raising=False)
    monkeypatch.setenv("JAVA_HOME", str(tmp_path / "gone"))
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(RewardSetupError) as err:
        sim.find_java()
    msg = str(err.value)
    assert "Java was not found" in msg and sim.ENV_JAVA_HOME in msg and "PATH" in msg and "adoptium" in msg


def _dummy_jdk(root: Path, javac: bool) -> Path:
    (root / "bin").mkdir(parents=True)
    names = ["java"] + (["javac"] if javac else [])
    for name in names:
        (root / "bin" / (name + (".exe" if os.name == "nt" else ""))).write_bytes(b"")
    return root


def test_old_java_is_refused(tmp_path, monkeypatch):
    monkeypatch.setenv(sim.ENV_JAVA_HOME, str(_dummy_jdk(tmp_path / "jdk11", javac=True)))
    monkeypatch.setattr(sim, "_java_version", lambda java: ("11.0.2", 11))
    with pytest.raises(RewardSetupError) as err:
        sim.find_java()
    assert "11.0.2" in str(err.value) and "17 or newer" in str(err.value)


def test_runtime_without_javac_is_refused(tmp_path, monkeypatch):
    monkeypatch.setenv(sim.ENV_JAVA_HOME, str(_dummy_jdk(tmp_path / "jre", javac=False)))
    monkeypatch.setattr(sim, "_java_version", lambda java: ("17.0.1", 17))
    with pytest.raises(RewardSetupError) as err:
        sim.find_java()
    assert "javac" in str(err.value) and sim.ENV_JAVA_HOME in str(err.value)


def test_java_found_through_home(tmp_path, monkeypatch):
    home = _dummy_jdk(tmp_path / "jdk", javac=True)
    monkeypatch.setenv(sim.ENV_JAVA_HOME, str(home))
    monkeypatch.setattr(sim, "_java_version", lambda java: ("17.0.21", 17))
    tools = sim.find_java()
    assert tools.source == sim.ENV_JAVA_HOME and tools.major == 17
    assert tools.java.parent == home / "bin" and tools.javac.name.startswith("javac")


def test_missing_jar_message(tmp_path, monkeypatch):
    monkeypatch.setenv(sim.ENV_JAR, str(tmp_path / "missing.jar"))
    with pytest.raises(RewardSetupError) as err:
        sim.find_jar()
    msg = str(err.value)
    assert sim.OPENROCKET_JAR_URL in msg and sim.ENV_JAR in msg and "24.12" in msg


def test_java_home_set_to_the_bin_folder_names_the_right_folder(tmp_path, monkeypatch):
    """A new user's slip: the setting points at ...\\bin. The message names the parent."""
    home = _dummy_jdk(tmp_path / "jdk", javac=True)
    monkeypatch.setenv(sim.ENV_JAVA_HOME, str(home / "bin"))
    with pytest.raises(RewardSetupError) as err:
        sim.find_java()
    msg = str(err.value)
    assert "bin folder itself" in msg and f"to {home} instead" in msg


def test_java_home_message_gives_a_windows_and_a_linux_example(tmp_path, monkeypatch):
    monkeypatch.setenv(sim.ENV_JAVA_HOME, str(tmp_path / "nojdk"))
    with pytest.raises(RewardSetupError) as err:
        sim.find_java()
    msg = str(err.value)
    assert "Eclipse Adoptium" in msg and "/usr/lib/jvm/" in msg and "/opt/jdk-17" not in msg


def test_missing_jar_message_names_fetch_jar(tmp_path, monkeypatch):
    """Without the setting the message names the README's command; with a wrong
    setting it says to correct or unset it first."""
    monkeypatch.delenv(sim.ENV_JAR, raising=False)
    monkeypatch.setattr(sim, "DEFAULT_JAR_PATH", tmp_path / "lib" / "OpenRocket-24.12.jar")
    with pytest.raises(RewardSetupError) as err:
        sim.find_jar()
    msg = str(err.value)
    assert "python -m rocket_reward fetch-jar" in msg and "the default place" in msg
    assert sim.OPENROCKET_JAR_URL in msg
    monkeypatch.setenv(sim.ENV_JAR, str(tmp_path / "missing.jar"))
    with pytest.raises(RewardSetupError) as err:
        sim.find_jar()
    msg = str(err.value)
    assert f"Correct {sim.ENV_JAR}, or unset it" in msg and "fetch-jar" in msg


def test_wrong_jar_message(tmp_path, monkeypatch):
    fake_jar = tmp_path / "OpenRocket-24.12.jar"
    fake_jar.write_bytes(b"not a jar")
    monkeypatch.setenv(sim.ENV_JAR, str(fake_jar))
    with pytest.raises(RewardSetupError) as err:
        sim.find_jar()
    msg = str(err.value)
    assert "SHA-256" in msg and sim.OPENROCKET_JAR_SHA256 in msg and sim.OPENROCKET_JAR_URL in msg


def test_cache_root_follows_setting(tmp_path, monkeypatch):
    monkeypatch.setenv(sim.ENV_CACHE, str(tmp_path / "c"))
    assert sim.cache_root() == tmp_path / "c"
    monkeypatch.delenv(sim.ENV_CACHE)
    assert "rocket_reward" in str(sim.cache_root())


def test_missing_helper_source(tmp_path, monkeypatch):
    tools = sim.JavaTools(Path("java"), Path("javac"), "17.0.1", 17, "PATH")
    jar = tmp_path / "x.jar"
    jar.write_bytes(b"x")
    with pytest.raises(RewardSetupError) as err:
        sim.compile_helper(tools, jar, tmp_path / "RocketSim.java")
    assert "RocketSim.java" in str(err.value)


def test_main_class_follows_package():
    assert sim._main_class("import x;\npublic class RocketSim {}") == "RocketSim"
    assert sim._main_class("package org.reward;\nclass RocketSim {}") == "org.reward.RocketSim"


# ---------------------------------------------------------------- normal runs

def test_ping_and_run(simulator, isolated):
    assert simulator.ping_reply["openrocket"] == "24.12"
    reply = simulator.run(ork(), rail_m=2.4, flights=FLIGHTS, launch={"altitude_m": 100.0})
    assert reply["ok"] is True
    assert [f["seed"] for f in reply["flights"]] == [1, 2, 3]
    assert reply["fake_rail_m"] == 2.4 and reply["fake_launch"] == {**sim.FIXED_LAUNCH, "altitude_m": 100.0}
    used = Path(reply["fake_ork_path"])
    assert used.parent == isolated and not used.exists(), "the temporary .ork must be deleted"
    assert "started" in log_text(simulator)


def test_run_from_path_keeps_the_file(simulator, tmp_path):
    path = tmp_path / "design.ork"
    path.write_text(ork(), encoding="utf-8")
    reply = simulator.run(path, 1.5, FLIGHTS[:1])
    assert reply["ok"] and Path(reply["fake_ork_path"]) == path.resolve() and path.exists()
    assert simulator.run(str(path), 1.5, FLIGHTS[:1])["ok"]


def test_run_from_bytes(simulator):
    assert simulator.run(ork().encode("utf-8"), 1.5, FLIGHTS[:1])["ok"]


def test_bad_arguments(simulator, tmp_path):
    with pytest.raises(ValueError):
        simulator.run(ork(), 1.5, [])
    with pytest.raises(ValueError):
        simulator.run(ork(), float("nan"), FLIGHTS)
    with pytest.raises(FileNotFoundError):
        simulator.run(tmp_path / "none.ork", 1.5, FLIGHTS)


@pytest.mark.parametrize("kind", ["load", "build"])
def test_design_fault_is_returned_without_restart(simulator, kind):
    pid = simulator.pid
    canary_runs = simulator.stats["canary_runs"]
    reply = simulator.run(ork(f"fake:{kind}"), 1.5, FLIGHTS)
    assert reply == {"id": reply["id"], "ok": False, "error_kind": kind, "message": f"fake {kind} error"}
    assert simulator.pid == pid and simulator.stats["restarts"] == 0
    assert simulator.stats["canary_runs"] == canary_runs
    assert simulator.run(ork(), 1.5, FLIGHTS)["ok"]


def test_slow_answer_within_the_limit(simulator):
    reply = simulator.run(ork("fake:slow=0.5"), 1.5, FLIGHTS, timeout_s=10)
    assert reply["ok"] and simulator.stats["restarts"] == 0


def test_close_is_safe_and_final():
    s = sim.Simulator(FAKE)
    proc = s._proc.popen
    s.close()
    s.close()
    assert proc.poll() == 0, "quit should let the helper exit cleanly"
    with pytest.raises(RuntimeError):
        s.run(ork(), 1.5, FLIGHTS)


def test_helper_that_died_while_idle_is_restarted(simulator):
    old = simulator._proc.popen
    old.kill()
    old.wait()
    reply = simulator.run(ork(), 1.5, FLIGHTS)
    assert reply["ok"] and simulator.pid != old.pid and simulator.stats["restarts"] == 1


# ---------------------------------------------------------------- start-up failures

@pytest.mark.parametrize("env, text", [
    ("FAKE_HELPER_DIE_ON_START", "exited before its first reply"),
    ("FAKE_HELPER_DIE_ON_PING", "exited before its first reply"),
    ("FAKE_HELPER_PING_GARBAGE", "not valid protocol"),
])
def test_start_failures_are_setup_errors(monkeypatch, env, text):
    monkeypatch.setenv(env, "1")
    with pytest.raises(RewardSetupError) as err:
        sim.Simulator(FAKE)
    msg = str(err.value)
    assert text in msg and "Helper log:" in msg


def test_ping_timeout_is_a_setup_error(monkeypatch):
    monkeypatch.setenv("FAKE_HELPER_PING_HANG", "1")
    started = time.monotonic()
    with pytest.raises(RewardSetupError) as err:
        sim.Simulator(FAKE, boot_timeout_s=1.0)
    assert "did not answer ping within 1 s" in str(err.value)
    assert time.monotonic() - started < 15


def test_wrong_openrocket_version_is_a_setup_error(monkeypatch):
    monkeypatch.setenv("FAKE_HELPER_OPENROCKET", "23.09")
    with pytest.raises(RewardSetupError) as err:
        sim.Simulator(FAKE)
    assert "23.09" in str(err.value) and sim.ENV_JAR in str(err.value)


def test_command_that_cannot_start(tmp_path):
    with pytest.raises(RewardSetupError) as err:
        sim.Simulator([str(tmp_path / "no-such-java")])
    assert "could not start" in str(err.value)


def test_log_tail_is_in_the_message(monkeypatch):
    monkeypatch.setenv("FAKE_HELPER_DIE_ON_START", "1")
    with pytest.raises(RewardSetupError) as err:
        sim.Simulator(FAKE)
    assert "dying on start on purpose" in str(err.value)


# ---------------------------------------------------------------- hang and crash policy

def test_hang_is_retried_then_returned_as_design_fault(simulator):
    canary_runs = simulator.stats["canary_runs"]
    started = time.monotonic()
    reply = simulator.run(ork("fake:hang"), 1.5, FLIGHTS, timeout_s=1.0)
    elapsed = time.monotonic() - started
    assert reply["ok"] is False and reply["error_kind"] == "hang"
    assert "did not finish" in reply["message"]
    assert simulator.stats["hangs"] == 2 and simulator.stats["canary_runs"] == canary_runs + 1
    assert elapsed < 20, f"the wall-clock timeout did not work ({elapsed:.1f} s)"
    # the next design gets a fresh, working helper
    assert simulator.run(ork(), 1.5, FLIGHTS)["ok"]


@pytest.mark.parametrize("marker", ["fake:die", "fake:garbage", "fake:wrongid", "fake:internal"])
def test_crash_kinds_are_retried_then_returned_as_design_fault(simulator, marker):
    canary_runs = simulator.stats["canary_runs"]
    reply = simulator.run(ork(marker), 1.5, FLIGHTS)
    assert reply["ok"] is False and reply["error_kind"] == "crash", reply
    assert "crashed" in reply["message"]
    assert simulator.stats["crashes"] == 2 and simulator.stats["canary_runs"] == canary_runs + 1
    assert simulator.stats["restarts"] >= 1
    assert simulator.run(ork(), 1.5, FLIGHTS)["ok"]


@pytest.mark.parametrize("marker, counter", [("fake:hang-once:a", "hangs"), ("fake:die-once:b", "crashes")])
def test_failure_that_does_not_repeat_gives_the_real_answer(simulator, marker, counter):
    first_pid = simulator.pid
    canary_runs = simulator.stats["canary_runs"]
    reply = simulator.run(ork(marker), 1.5, FLIGHTS, timeout_s=1.0)
    assert reply["ok"] is True
    assert simulator.stats[counter] == 1 and simulator.stats["canary_runs"] == canary_runs + 1
    assert simulator.pid != first_pid
    assert "restarting the helper" in log_text(simulator)


def test_slow_answer_past_the_limit_is_a_hang(simulator):
    reply = simulator.run(ork("fake:slow=5"), 1.5, FLIGHTS, timeout_s=0.5)
    assert reply["error_kind"] == "hang"


def test_canary_with_wrong_numbers_stops_everything(monkeypatch, simulator):
    monkeypatch.setenv("FAKE_HELPER_APOGEE", "500")  # read by the restarted helper
    with pytest.raises(RewardSetupError) as err:
        simulator.run(ork("fake:hang"), 1.5, FLIGHTS, timeout_s=1.0)
    msg = str(err.value)
    assert "self-test rocket" in msg and "apogee_m is 500" in msg


def test_canary_that_hangs_stops_everything(monkeypatch):
    hanging = sim.Canary(name="stuck", ork_text=ork("fake:hang"), rail_m=1.5,
                         flights=({"wind_ms": 2.0, "seed": 1},), expected={"apogee_m": 1041.905})
    monkeypatch.setattr(sim, "CANARY_TIMEOUT_S", 1.0)
    # at start-up (the self-test every new Simulator flies) ...
    with pytest.raises(RewardSetupError) as err:
        sim.Simulator(FAKE, canary=hanging)
    assert "'stuck' failed (hang" in str(err.value)
    # ... and before a design that crashed the helper is retried
    with sim.Simulator(FAKE, canary=hanging, self_test=False) as s:
        with pytest.raises(RewardSetupError) as err:
            s.run(ork("fake:die"), 1.5, FLIGHTS)
    assert "'stuck' failed (hang" in str(err.value)


def test_helper_that_cannot_restart_stops_everything(simulator, monkeypatch):
    simulator.env = {**os.environ, "FAKE_HELPER_DIE_ON_START": "1"}
    with pytest.raises(RewardSetupError) as err:
        simulator.run(ork("fake:die"), 1.5, FLIGHTS)
    assert "exited before its first reply" in str(err.value)


def test_no_canary_still_retries(tmp_path):
    with sim.Simulator(FAKE, canary=None) as s:
        reply = s.run(ork("fake:die-once:c"), 1.5, FLIGHTS)
        assert reply["ok"] and s.stats["canary_runs"] == 0 and s.stats["crashes"] == 1


# ---------------------------------------------------------------- the canary interface

def test_canary_problems():
    c = sim.DEFAULT_CANARY
    rocket = dict(c.expected_rocket)
    good = {"ok": True, "rocket": rocket, "flights": [{"ok": True, **c.expected}]}
    assert c.problems(good) == []
    off = {"ok": True, "rocket": rocket,
           "flights": [{"ok": True, **c.expected, "apogee_m": c.expected["apogee_m"] * 1.05}]}
    assert any("apogee_m" in p for p in c.problems(off))
    missing = {"ok": True, "rocket": rocket, "flights": [{"ok": True, "apogee_m": None}]}
    assert len(c.problems(missing)) == len(c.expected)
    no_motor = {"ok": True, "rocket": dict(rocket, motor_count=0), "flights": [{"ok": True, **c.expected}]}
    assert c.problems(no_motor) == ["rocket motor_count is 0, expected 1"]
    assert c.problems({"ok": False, "error_kind": "load", "message": "x"})
    assert c.problems({"ok": True, "flights": []})
    assert c.ork_text.startswith("<?xml") and "H170M" in c.ork_text


def test_fly_canary_and_check_setup_with_fake():
    with sim.Simulator(FAKE) as s:
        assert s.fly_canary()["ok"]
    facts = sim.check_setup(command=FAKE)
    assert facts["openrocket"] == "24.12" and facts["canary"]["apogee_m"] == pytest.approx(1041.905)
    assert facts["boot_s"] >= 0 and facts["canary_s"] >= 0


# ---------------------------------------------------------------- the pool

def test_default_pool_size():
    assert 1 <= sim.default_pool_size() <= 8


def test_pool_keeps_order():
    requests = [{"ork_text_or_path": ork(f"fake:slow={0.3 if i % 3 == 0 else 0}"), "rail_m": 1.0 + i,
                 "flights": [{"wind_ms": 1.0, "seed": i}]} for i in range(12)]
    with sim.SimPool(3, FAKE) as pool:
        assert len(pool.simulators) == 3
        replies = pool.run_many(requests)
    assert [r["fake_rail_m"] for r in replies] == [1.0 + i for i in range(12)]
    assert [r["flights"][0]["seed"] for r in replies] == list(range(12))
    assert len({r["fake_pid"] for r in replies}) > 1, "work should be spread over the helpers"


def test_pool_run_is_safe_from_many_threads():
    """Many threads share one pool through run(): every call gets its own reply,
    no helper flies two designs at once, and a closed pool refuses at once."""
    import threading
    with sim.SimPool(2, FAKE) as pool:
        got: dict[int, dict] = {}

        def one(i: int) -> None:
            got[i] = pool.run(ork("fake:slow=0.05"), 1.0 + i, [{"wind_ms": 1.0, "seed": i}])

        threads = [threading.Thread(target=one, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert sorted(got) == list(range(10))
        assert all(got[i]["fake_rail_m"] == 1.0 + i and got[i]["flights"][0]["seed"] == i for i in got)
        assert pool._free.qsize() == 2
    with pytest.raises(RuntimeError, match="closed"):
        pool.run(ork(), 1.5, FLIGHTS)


def test_one_hung_design_does_not_block_the_others():
    hang = {"ork_text_or_path": ork("fake:hang"), "rail_m": 1.5, "flights": FLIGHTS, "timeout_s": 3.0}
    normal = {"ork_text_or_path": ork("fake:slow=0.1"), "rail_m": 1.5, "flights": FLIGHTS}
    with sim.SimPool(2, FAKE) as pool:
        started = time.monotonic()
        replies = pool.run_many([hang] + [normal] * 20)
        elapsed = time.monotonic() - started
    assert replies[0]["error_kind"] == "hang"
    assert all(r["ok"] for r in replies[1:])
    # the hang costs ~6 s on its own helper (two timeouts); 20 normal designs
    # at 0.1 s each on one helper alone would take ~2 s more if they waited.
    assert elapsed < 12, elapsed


def test_pool_raises_setup_error_after_the_others_finish(monkeypatch):
    with sim.SimPool(2, FAKE) as pool:
        monkeypatch.setenv("FAKE_HELPER_APOGEE", "1")  # every restarted helper fails its self-test
        requests = [{"ork_text_or_path": ork("fake:die"), "rail_m": 1.5, "flights": FLIGHTS}]
        requests += [{"ork_text_or_path": ork(), "rail_m": 1.5, "flights": FLIGHTS}] * 4
        with pytest.raises(RewardSetupError):
            pool.run_many(requests)


def test_pool_that_cannot_start_leaves_nothing_running(monkeypatch):
    monkeypatch.setenv("FAKE_HELPER_DIE_ON_START", "1")
    with pytest.raises(RewardSetupError):
        sim.SimPool(3, FAKE)


# ---------------------------------------------------------------- real Java

TINY_HELPER = r"""
import java.io.*;
import java.nio.file.*;
public class RocketSim {
  public static void main(String[] a) throws Exception {
    BufferedReader in = new BufferedReader(new InputStreamReader(System.in, "UTF-8"));
    PrintStream out = new PrintStream(new FileOutputStream(FileDescriptor.out), true, "UTF-8");
    System.err.println("tiny helper started");
    String line;
    while ((line = in.readLine()) != null) {
      java.util.regex.Matcher m = java.util.regex.Pattern.compile("\"id\": \"([^\"]*)\"").matcher(line);
      String id = m.find() ? m.group(1) : "";
      if (line.contains("\"quit\"")) System.exit(0);
      if (line.contains("\"ping\"")) { out.println("{\"id\": \"" + id + "\", \"ok\": true, \"openrocket\": \"24.12\", \"java\": \"" + System.getProperty("java.version") + "\", \"helper\": 0, \"motor_database_size\": 1389}"); continue; }
      java.util.regex.Matcher p = java.util.regex.Pattern.compile("\"ork\": \"([^\"]*)\"").matcher(line);
      String path = p.find() ? p.group(1).replace("\\\\", "\\") : "";
      String text = new String(Files.readAllBytes(Paths.get(path)), "UTF-8");
      if (text.contains("tiny:hang")) { Thread.sleep(1000000L); }
      out.println("{\"id\": \"" + id + "\", \"ok\": false, \"error_kind\": \"load\", \"message\": \"tiny helper cannot fly\"}");
    }
  }
}
"""


@pytest.fixture
def tiny_source(tmp_path) -> Path:
    src = tmp_path / "tinysrc" / "RocketSim.java"
    src.parent.mkdir()
    src.write_text(TINY_HELPER, encoding="utf-8", newline="\n")
    return src


@pytest.mark.needs_java
def test_real_java_and_jar_are_found():
    tools = sim.find_java()
    assert tools.major >= 17
    assert sim.find_jar().is_file()


@pytest.mark.needs_java
def test_compile_once_and_in_parallel(tiny_source, tmp_path):
    cache = Path(os.environ[sim.ENV_CACHE])
    code = ("import sys, json; sys.path.insert(0, sys.argv[1]); from rocket_reward import sim; "
            "d, c = sim.compile_helper(source=sys.argv[2]); print(json.dumps([str(d), c]))")
    repo = str(HERE.parents[1])
    procs = [subprocess.Popen([sys.executable, "-c", code, repo, str(tiny_source)], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE) for _ in range(4)]
    outs = [p.communicate(timeout=300) for p in procs]
    assert all(p.returncode == 0 for p in procs), [o[1][-500:] for o in outs]
    results = {tuple(json.loads(o[0])) for o in outs}
    assert len(results) == 1
    folder = Path(next(iter(results))[0])
    assert (folder / "RocketSim.class").is_file() and (folder / "COMPILED").is_file()
    assert [p.name for p in cache.iterdir() if p.name.startswith("compile-")] == []
    assert len([p for p in cache.iterdir() if p.name.startswith("helper-")]) == 1
    # a second call reuses the cache without running javac
    started = time.monotonic()
    assert sim.compile_helper(source=tiny_source)[0] == folder
    assert time.monotonic() - started < 2


@pytest.mark.needs_java
def test_broken_source_gives_compiler_message(tmp_path):
    src = tmp_path / "RocketSim.java"
    src.write_text("public class RocketSim { nonsense }", encoding="utf-8", newline="\n")
    with pytest.raises(RewardSetupError) as err:
        sim.compile_helper(source=src)
    assert "did not compile" in str(err.value)


@pytest.mark.needs_java
def test_real_java_process_is_killed_on_timeout(tiny_source):
    command = sim.helper_command(source=tiny_source)
    with sim.Simulator(command, canary=None) as s:
        assert s.ping_reply["openrocket"] == "24.12"
        assert s.run(ork(), 1.5, FLIGHTS)["error_kind"] == "load"
        started = time.monotonic()
        reply = s.run(ork("tiny:hang"), 1.5, FLIGHTS, timeout_s=2.0)
        assert reply["error_kind"] == "hang" and time.monotonic() - started < 30
        assert "tiny helper started" in log_text(s)


@pytest.mark.needs_java
def test_check_setup_with_the_real_helper():
    if not sim.HELPER_SOURCE.is_file():
        pytest.skip(f"{sim.HELPER_SOURCE} is not written yet")
    facts = sim.check_setup()
    assert facts["openrocket"] == "24.12"
    for key, want in sim.DEFAULT_CANARY.expected.items():
        assert facts["canary"][key] == pytest.approx(want, rel=sim.DEFAULT_CANARY.rel_tol)


# ---------------------------------------------------------------- review fixes (fake helper)

def test_refused_request_is_machine_trouble_until_it_repeats_after_the_canary(simulator):
    """Owner's rule: a request the helper refuses as malformed is a machine or helper
    problem; only when the same design is refused again after the self-test rocket
    flew does it count against the design (as a crash, the build floor)."""
    reply = simulator.run(ork("fake:request"), 1.5, FLIGHTS)
    assert reply["ok"] is False and reply["error_kind"] == "crash"
    assert "refused the request" in reply["message"] and "self-test" in reply["message"]
    assert simulator.stats["restarts"] == 1 and simulator.stats["canary_runs"] == 2
    assert simulator.stats["refused"] == 2
    assert simulator.run(ork(), 1.5, FLIGHTS)["ok"]


def test_refusal_that_does_not_repeat_gives_the_real_answer(simulator):
    reply = simulator.run(ork("fake:request-once:r1"), 1.5, FLIGHTS)
    assert reply["ok"] is True and len(reply["flights"]) == 3
    assert simulator.stats["restarts"] == 1 and simulator.stats["canary_runs"] == 2


def test_crashed_flight_is_retried_after_the_canary_then_returned(simulator):
    """A flight on which OpenRocket threw an error: retried once on a fresh helper
    after the canary; when it crashes again the reply is returned with that
    flight failed (ok false, error_kind crash, no numbers)."""
    reply = simulator.run(ork("fake:flightcrash"), 1.5, FLIGHTS)
    assert reply["ok"] is True
    last = reply["flights"][-1]
    assert last["ok"] is False and last["error_kind"] == "crash" and "apogee_m" not in last
    assert simulator.stats["restarts"] == 1 and simulator.stats["canary_runs"] == 2
    assert simulator.stats["flight_crashes"] == 2


def test_crashed_flight_that_does_not_repeat_gives_the_real_answer(simulator):
    reply = simulator.run(ork("fake:flightcrash-once:f1"), 1.5, FLIGHTS)
    assert all(f["ok"] for f in reply["flights"])
    assert simulator.stats["restarts"] == 1 and simulator.stats["flight_crashes"] == 1


def test_aborted_flight_is_a_normal_result_without_retry(simulator):
    reply = simulator.run(ork("fake:abort"), 1.5, FLIGHTS)
    f = reply["flights"][0]
    assert f["ok"] is True and f["abort"] and f["apogee_m"] is not None
    assert simulator.stats["restarts"] == 0 and simulator.stats["canary_runs"] == 1


def test_every_request_names_the_launch_settings_explicitly(simulator):
    """Owner's rule: launch_into_wind (false), the geodetic model and the wind
    direction are always sent, so nothing comes from defaults or preferences."""
    sent = simulator.run(ork(), 1.5, FLIGHTS)["fake_launch"]
    assert sent["launch_into_wind"] is False and sent["geodetic"] == "spherical"
    assert sent["wind_direction_deg"] == 90.0
    sent = simulator.run(ork(), 1.5, FLIGHTS, launch={"geodetic": "flat", "altitude_m": 10.0})["fake_launch"]
    assert sent["geodetic"] == "flat" and sent["altitude_m"] == 10.0 and sent["launch_into_wind"] is False


@pytest.mark.parametrize("flights, launch, text", [
    ([{"wind_ms": -1.0, "seed": 1}], None, "wind_ms"),
    ([{"wind_ms": float("nan"), "seed": 1}], None, "wind_ms"),
    ([{"wind_ms": 1.0, "seed": 1.5}], None, "seed"),
    ([{"wind_ms": 1.0, "seed": 2 ** 40}], None, "seed"),
    ([{"wind_ms": 1.0}], None, "seed"),
    ([{"wind_ms": 1.0, "seed": 1, "gust": 3}], None, "unknown field"),
    (FLIGHTS, {"rod_angle": 5.0}, "rod_angle"),
    (FLIGHTS, {"time_step_s": 0.0}, "time_step_s"),
    (FLIGHTS, {"wind_turbulence": -0.1}, "wind_turbulence"),
    (FLIGHTS, {"altitude_m": float("inf")}, "altitude_m"),
    (FLIGHTS, {"latitude_deg": "28"}, "latitude_deg"),
    (FLIGHTS, {"launch_into_wind": 1}, "launch_into_wind"),
    (FLIGHTS, {"geodetic": "round"}, "geodetic"),
    (FLIGHTS, {"base_pressure_pa": -5.0}, "base_pressure_pa"),
    (FLIGHTS, [("altitude_m", 1.0)], "mapping"),
])
def test_bad_flights_and_launch_fields_are_refused_before_sending(simulator, flights, launch, text):
    with pytest.raises(sim.SimRequestError) as err:
        simulator.run(ork(), 1.5, flights, launch=launch)
    assert text in str(err.value)
    assert simulator.stats["runs"] == 0 and simulator.stats["starts"] == 1


@pytest.mark.parametrize("kwargs, text", [
    ({"max_sim_time_s": 0}, "max_sim_time_s"), ({"max_sim_time_s": float("nan")}, "max_sim_time_s"),
    ({"max_steps": 0}, "max_steps"), ({"max_steps": 2.5}, "max_steps"), ({"max_steps": True}, "max_steps"),
    ({"config_id": 5}, "config_id"), ({"rail_m": 0.0}, "rail_m"),
])
def test_bad_caps_and_config_id_are_refused_before_sending(simulator, kwargs, text):
    args = {"rail_m": 1.5, **kwargs}
    with pytest.raises(sim.SimRequestError) as err:
        simulator.run(ork(), args.pop("rail_m"), FLIGHTS, **args)
    assert text in str(err.value) and simulator.stats["runs"] == 0


def test_whole_float_seed_is_sent_as_an_integer(simulator):
    reply = simulator.run(ork(), 1.5, [{"wind_ms": 1, "seed": 7.0}])
    assert reply["flights"][0]["seed"] == 7 and isinstance(reply["flights"][0]["seed"], int)


@pytest.mark.parametrize("motors", ["0", "12"])
def test_helper_with_a_broken_motor_list_is_a_setup_error(monkeypatch, motors):
    monkeypatch.setenv("FAKE_HELPER_MOTORS", motors)
    with pytest.raises(RewardSetupError) as err:
        sim.Simulator(FAKE)
    assert "motor list" in str(err.value) and sim.ENV_JAR in str(err.value)
    with pytest.raises(RewardSetupError):
        sim.SimPool(2, FAKE)


def test_new_simulator_flies_the_self_test_rocket(monkeypatch):
    with sim.Simulator(FAKE) as s:
        assert s.stats["canary_runs"] == 1
    with sim.Simulator(FAKE, self_test=False) as s:
        assert s.stats["canary_runs"] == 0
    monkeypatch.setenv("FAKE_HELPER_APOGEE", "500")  # wrong numbers from the very first helper
    with pytest.raises(RewardSetupError) as err:
        sim.Simulator(FAKE)
    assert "apogee_m is 500" in str(err.value)
    with pytest.raises(RewardSetupError):
        sim.SimPool(2, FAKE)


def test_hang_while_the_helper_holds_the_file_leaves_no_temporary_file(simulator, isolated):
    reply = simulator.run(ork("fake:hold"), 1.5, FLIGHTS, timeout_s=1.0)
    assert reply["error_kind"] == "hang"
    assert list(isolated.glob("*.ork")) == []


def test_close_cuts_short_a_request_in_another_thread():
    import threading
    s = sim.Simulator(FAKE)
    outcome: list = []

    def fly():
        try:
            outcome.append(s.run(ork("fake:slow=30"), 1.5, FLIGHTS, timeout_s=100))
        except BaseException as exc:  # recorded and checked below
            outcome.append(exc)

    t = threading.Thread(target=fly)
    t.start()
    time.sleep(1.0)
    started = time.monotonic()
    s.close()
    took = time.monotonic() - started
    t.join(30)
    assert not t.is_alive()
    assert took < 10, f"close() waited {took:.1f} s for the running request"
    assert len(outcome) == 1 and isinstance(outcome[0], RuntimeError), outcome
    assert s.stats["restarts"] == 0, "a closed Simulator must not restart its helper"


def test_pool_close_cuts_short_requests_in_flight():
    import threading
    pool = sim.SimPool(2, FAKE)
    errors: list = []
    t = threading.Thread(target=lambda: errors.append(_catch(lambda: pool.run_many(
        [{"ork_text_or_path": ork("fake:slow=30"), "rail_m": 1.5, "flights": FLIGHTS, "timeout_s": 100}] * 4))))
    t.start()
    time.sleep(1.0)
    started = time.monotonic()
    pool.close()
    t.join(30)
    assert time.monotonic() - started < 10 and not t.is_alive()
    assert errors and isinstance(errors[0], (RuntimeError, concurrent_cancelled())), errors


def _catch(fn):
    try:
        return fn()
    except BaseException as exc:  # returned to the caller to check
        return exc


def concurrent_cancelled():
    import concurrent.futures
    return concurrent.futures.CancelledError


def test_old_temporary_files_are_swept_at_start(isolated):
    old = isolated / "rocket_reward_old.ork"
    young = isolated / "rocket_reward_young.ork"
    other = isolated / "someone_else.ork"
    for p in (old, young, other):
        p.write_text("<x/>", encoding="utf-8")
    long_ago = time.time() - 2 * sim.STALE_TEMP_S
    os.utime(old, (long_ago, long_ago))
    os.utime(other, (long_ago, long_ago))
    with sim.Simulator(FAKE, canary=None):
        pass
    assert not old.exists() and young.exists() and other.exists()
    young.unlink()
    other.unlink()


def test_motor_list_with_fake(simulator):
    motors = simulator.motor_list()
    assert motors and motors[0]["designation"] == "H170M"


def test_atexit_kill_is_registered_once_a_helper_starts(simulator):
    assert sim._ATEXIT_REGISTERED is True


def test_java_arg_path_keeps_plain_paths_and_refuses_unreadable_ones(tmp_path):
    plain = tmp_path / "plain"
    assert sim.java_arg_path(plain, "cache folder", sim.ENV_CACHE, encoding="ascii") == str(plain)
    missing = tmp_path / "日本" / "cache"  # does not exist: no short name to fall back on
    with pytest.raises(RewardSetupError) as err:
        sim.java_arg_path(missing, "cache folder", sim.ENV_CACHE, encoding="ascii")
    msg = str(err.value)
    assert sim.ENV_CACHE in msg and "ASCII" in msg and "jar" not in msg.lower()


@pytest.mark.skipif(sys.platform != "win32", reason="8.3 short names exist only on Windows")
def test_java_arg_path_uses_the_windows_short_name(tmp_path):
    folder = tmp_path / "dir ü 日本"
    folder.mkdir()
    try:
        text = sim.java_arg_path(folder, "cache folder", sim.ENV_CACHE, encoding="ascii")
    except RewardSetupError as err:  # short names switched off on this drive: the message must say what to do
        assert sim.ENV_CACHE in str(err)
        return
    text.encode("ascii")
    assert os.path.samefile(text, folder)
