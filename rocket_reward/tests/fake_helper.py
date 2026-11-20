"""A stand-in for the Java helper that speaks java/PROTOCOL.md.

It lets the tests drive sim.py without Java. Run it as
``python fake_helper.py``. It answers ping, and answers run with fixed
numbers equal to the default self-test rocket's expected numbers.

It misbehaves on purpose when asked to.

Environment variables (whole process):
  FAKE_HELPER_DIE_ON_START=1   exit with code 3 before reading anything
  FAKE_HELPER_DIE_ON_PING=1    exit with code 4 when the ping arrives
  FAKE_HELPER_PING_GARBAGE=1   answer ping with a line that is not JSON
  FAKE_HELPER_PING_HANG=1      never answer ping
  FAKE_HELPER_OPENROCKET=x     report OpenRocket version x (default 24.12)
  FAKE_HELPER_APOGEE=x         report apogee x for every flight
  FAKE_HELPER_MOTORS=n         report n motors in the motor list (default 1452)
  FAKE_HELPER_STATE_DIR=dir    folder for the "-once" markers below

Markers written anywhere in the .ork file (design-level behaviour, so a retry
on a fresh helper behaves the same way):
  fake:hang       never answer
  fake:die        exit with code 9 in the middle of the request
  fake:garbage    print a line that is not JSON
  fake:wrongid    answer with another request id
  fake:internal   reply {"ok": false, "error_kind": "internal"}
  fake:load       reply {"ok": false, "error_kind": "load"}
  fake:build      reply {"ok": false, "error_kind": "build"}
  fake:request    reply {"ok": false, "error_kind": "request"}
  fake:hold       keep the .ork file open and never answer (a loader stuck in the file)
  fake:flightcrash  the last flight fails with error_kind "crash" (OpenRocket threw)
  fake:abort      the first flight is aborted (abort text, ok true, numbers kept)
  fake:slow=S     wait S seconds, then answer normally
  fake:MODE-once:NAME  (for example hang-once, die-once, request-once, flightcrash-once)
                  misbehave only if FAKE_HELPER_STATE_DIR/NAME does not exist
                  yet (the file is created first), else answer normally

Every reply to run also carries "fake_ork_path" (the file it read) and
"fake_pid", extra fields the protocol allows.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time

APOGEE = 1041.905
NUMBERS = {"max_velocity_ms": 278.779, "max_accel_ms2": 233.98, "max_mach": 0.822,
           "time_to_apogee_s": 11.537, "flight_time_s": 240.702}


def log(text: str) -> None:
    sys.stderr.write(f"fake helper {os.getpid()}: {text}\n")
    sys.stderr.flush()


def send(obj) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def hang() -> None:
    log("hanging on purpose")
    while True:
        time.sleep(3600)


def flight(spec: dict) -> dict:
    apogee = float(os.environ.get("FAKE_HELPER_APOGEE", APOGEE))
    out = {"wind_ms": spec.get("wind_ms"), "seed": spec.get("seed"), "ok": True, "abort": None,
           "apogee_m": apogee, **NUMBERS,
           "rail_exit_ms": 25.0, "stability_rail_cal": 1.8, "stability_min_burn_cal": 1.6,
           "burnout_time_s": 2.1, "liftoff_twr": 9.0,
           "branches": [{"index": 0, "name": "Sustainer", "has_recovery": True, "deployed": True,
                         "deploy_time_s": 21.5, "deploy_speed_ms": 5.7, "deploy_during_burn": False,
                         "landed": True, "landing_time_s": 240.7, "landing_vertical_ms": 4.8,
                         "landing_total_ms": 5.2}],
           "warnings": [], "steps": 2400, "hit_step_cap": False, "hit_time_cap": False}
    return out


def once(name: str) -> bool:
    """True the first time NAME is seen (across processes)."""
    state = os.environ.get("FAKE_HELPER_STATE_DIR")
    if not state:
        return True
    path = os.path.join(state, name)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    os.close(fd)
    return True


def answer_run(req: dict) -> None:
    rid = req.get("id")
    path = req.get("ork", "")
    try:
        with open(path, "rb") as fh:
            text = fh.read().decode("utf-8", "replace")
    except OSError as exc:
        send({"id": rid, "ok": False, "error_kind": "load", "message": f"cannot read {path}: {exc}"})
        return
    match = re.search(r"fake:([a-z]+(?:-once:[\w.-]+|=[0-9.]+)?)", text)
    mode = match.group(1) if match else ""
    if "-once:" in mode:
        base, name = mode.split("-once:", 1)
        mode = base if once(name) else ""
    log(f"run {rid} mode={mode or 'normal'}")
    if mode == "hang":
        hang()
    if mode == "hold":
        held = open(path, "rb")  # noqa: F841 - kept open on purpose until the process is killed
        hang()
    if mode == "die":
        sys.stdout.write('{"id": "')  # half a line, then gone
        sys.stdout.flush()
        os._exit(9)
    if mode == "garbage":
        sys.stdout.write("Exception in thread main: something broke\n")
        sys.stdout.flush()
        return
    if mode == "wrongid":
        send({"id": "nobody", "ok": True, "flights": []})
        return
    if mode in ("internal", "load", "build", "request"):
        send({"id": rid, "ok": False, "error_kind": mode, "message": f"fake {mode} error"})
        return
    if mode.startswith("slow="):
        time.sleep(float(mode.split("=", 1)[1]))
    flights = [flight(f) for f in req.get("flights", [])]
    if mode == "flightcrash" and flights:  # OpenRocket threw an error during the last flight
        last = flights[-1]
        flights[-1] = {"wind_ms": last["wind_ms"], "seed": last["seed"], "ok": False, "error_kind": "crash",
                       "error": "OpenRocket failed during the flight: BugException: fake", "steps": 1}
    if mode == "abort" and flights:  # OpenRocket aborted the flight: a normal result with numbers
        flights[0]["abort"] = "Motor burnout without liftoff."
    send({"id": rid, "ok": True, "load_warnings": [],
          "rocket": {"length_m": 1.18, "max_diameter_m": 0.066, "stage_count": 1, "mass_kg": 1.2,
                     "dry_mass_kg": 0.9, "cg_m": 0.7, "cp_m": 0.9, "stability_cal": 2.9,
                     "motor_count": 1, "total_impulse_ns": 300.0, "config_id": "cfg0"},
          "components": [], "flights": flights,
          "fake_ork_path": path, "fake_pid": os.getpid(), "fake_rail_m": req.get("rail_m"),
          "fake_launch": req.get("launch")})


def main() -> int:
    if os.environ.get("FAKE_HELPER_DIE_ON_START"):
        log("dying on start on purpose")
        return 3
    log("started")
    for raw in sys.stdin.buffer:
        line = raw.decode("utf-8").strip()
        if not line:
            continue
        req = json.loads(line)
        op = req.get("op")
        if op == "quit":
            log("quit")
            return 0
        if op == "ping":
            if os.environ.get("FAKE_HELPER_DIE_ON_PING"):
                log("dying on ping on purpose")
                return 4
            if os.environ.get("FAKE_HELPER_PING_HANG"):
                hang()
            if os.environ.get("FAKE_HELPER_PING_GARBAGE"):
                sys.stdout.write("Picked up JAVA_TOOL_OPTIONS: nonsense\n")
                sys.stdout.flush()
                continue
            send({"id": req.get("id"), "ok": True,
                  "openrocket": os.environ.get("FAKE_HELPER_OPENROCKET", "24.12"),
                  "java": "17.0.21", "helper": 2,
                  "motor_database_size": int(os.environ.get("FAKE_HELPER_MOTORS", "1452"))})
            continue
        if op == "motors":
            send({"id": req.get("id"), "ok": True,
                  "motors": [{"digest": "fake-digest", "manufacturer": "AeroTech", "designation": "H170M",
                              "common_name": "H170", "diameter_m": 0.038, "length_m": 0.191,
                              "total_impulse_ns": 300.0}]})
            continue
        if op == "run":
            answer_run(req)
            continue
        send({"id": req.get("id"), "ok": False, "error_kind": "internal", "message": f"unknown op {op}"})
    log("stdin closed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
