"""Repeatability, speed and warning survey of the simulator link.

    python rocket_reward/tools/sim_bench.py repeat   DATA.jsonl [--designs 20]
    python rocket_reward/tools/sim_bench.py speed    DATA.jsonl [--designs 100] [--pools 1,4,8] [--xmx 1g]
    python rocket_reward/tools/sim_bench.py warnings DATA.jsonl [--helpers 4]

DATA.jsonl holds reference rows whose last message has a <design> block
(for example sft_v5_meta_*.jsonl). Every design is written with
ork.design_to_ork and flown the way the reward flies it: three flights at 1, 2
and 3 m/s wind (seeds 1, 2, 3), a 1.5 m rail and the protocol's default launch
site, in the configuration the design declares (ork.flight_config_id).

repeat   flies each design 3 times in one helper, once more in each of 2 fresh
         helpers and once more with 4 helpers at once; every reply must be
         byte-identical (the whole reply, not only the flight numbers).
speed    helper start-up, first request, steady-state seconds per request with
         1 helper, and throughput with pools of 4 and 8; memory per helper.
warnings every distinct load warning and simulation warning, with counts.

Results are printed as JSON and written to --out/sim_<command>.json (--out is
required: the folder for calibration results).
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from rocket_reward import ork, sim  # noqa: E402

FLIGHTS = [{"wind_ms": 1.0, "seed": 1}, {"wind_ms": 2.0, "seed": 2}, {"wind_ms": 3.0, "seed": 3}]
RAIL_M = 1.5


def designs(data: Path) -> list[dict[str, Any]]:
    """Distinct designs of the file, in file order, as run() keyword arguments plus an id."""
    seen: dict[str, dict] = {}
    for line in data.open(encoding="utf-8"):
        if not line.strip():
            continue
        row = json.loads(line)
        text = row["messages"][-1]["content"]
        i = text.find("<design>")
        j = text.find("</design>", i)
        if i < 0 or j < 0:
            continue
        body = text[i + len("<design>"):j]
        if body in seen:
            seen[body]["rows"] += 1
            continue
        root = {"openrocket": json.loads(body)["openrocket"]}
        seen[body] = {"id": row.get("id"), "rows": 1,
                      "request": {"ork_text_or_path": ork.design_to_ork(root), "rail_m": RAIL_M,
                                  "flights": FLIGHTS, "config_id": ork.flight_config_id(root)}}
    return list(seen.values())


def canon(reply: dict) -> str:
    """The whole reply as text, without the request id (which differs by design)."""
    return json.dumps({k: v for k, v in reply.items() if k != "id"}, sort_keys=True)


def first_difference(a: Any, b: Any, path: str = "") -> str | None:
    """Where two replies first differ, as a readable path, or None."""
    if type(a) is not type(b):
        return f"{path}: {a!r} vs {b!r}"
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if path == "" and k == "id":
                continue
            d = first_difference(a.get(k), b.get(k), f"{path}.{k}")
            if d:
                return d
        return None
    if isinstance(a, list):
        if len(a) != len(b):
            return f"{path}: {len(a)} items vs {len(b)}"
        for n, (x, y) in enumerate(zip(a, b)):
            d = first_difference(x, y, f"{path}[{n}]")
            if d:
                return d
        return None
    return None if a == b else f"{path}: {a!r} vs {b!r}"


def peak_memory_mb(pid: int) -> float | None:
    """Peak resident memory of a process in MB (Windows, Linux; None elsewhere)."""
    try:
        if sys.platform == "win32":
            out = subprocess.run(["powershell", "-NoProfile", "-Command",
                                  f"(Get-Process -Id {int(pid)}).PeakWorkingSet64"],
                                 capture_output=True, text=True, timeout=60).stdout.strip()
            return round(int(out) / 2**20, 1)
        status = Path(f"/proc/{int(pid)}/status")
        if status.is_file():
            m = re.search(r"VmHWM:\s+(\d+) kB", status.read_text())
            return round(int(m.group(1)) / 1024, 1) if m else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    return None


def pick(items: list, n: int) -> list:
    """n items spread evenly over the list (repeatable)."""
    if n >= len(items):
        return list(items)
    step = len(items) / n
    return [items[int(k * step)] for k in range(n)]


# --------------------------------------------------------------------------- repeat

def cmd_repeat(a) -> dict:
    chosen = pick(designs(a.data), a.designs)
    reqs = [d["request"] for d in chosen]
    out: dict[str, Any] = {"designs": [d["id"] for d in chosen], "differences": []}
    base: list[str] = []
    with sim.Simulator(canary=None) as s:
        for d in chosen:
            replies = [s.run(**d["request"]) for _ in range(3)]
            base.append(canon(replies[0]))
            for k in (1, 2):
                if canon(replies[k]) != base[-1]:
                    out["differences"].append({"id": d["id"], "where": f"same helper, run {k + 1}",
                                               "first": first_difference(replies[0], replies[k])})
    for n in (1, 2):
        with sim.Simulator(canary=None) as s:
            for d, b in zip(chosen, base):
                r = s.run(**d["request"])
                if canon(r) != b:
                    out["differences"].append({"id": d["id"], "where": f"fresh helper {n}",
                                               "first": first_difference(json.loads(b), r)})
    with sim.SimPool(4, canary=None) as pool:
        replies = pool.run_many(reqs * 2)
    for k, r in enumerate(replies):
        d, b = chosen[k % len(chosen)], base[k % len(chosen)]
        if canon(r) != b:
            out["differences"].append({"id": d["id"], "where": "4 helpers at once",
                                       "first": first_difference(json.loads(b), r)})
    oks = [json.loads(b) for b in base]
    out["flown_ok"] = sum(r.get("ok") is True for r in oks)
    out["faults"] = {d["id"]: r.get("error_kind") for d, r in zip(chosen, oks) if not r.get("ok")}
    out["stages"] = dict(collections.Counter(r["rocket"]["stage_count"] for r in oks if r.get("ok")))
    out["motors"] = dict(collections.Counter(r["rocket"]["motor_count"] for r in oks if r.get("ok")))
    out["comparisons"] = len(chosen) * (2 + 2 + 2)
    out["identical"] = out["comparisons"] - len(out["differences"])
    return out


# --------------------------------------------------------------------------- speed

def cmd_speed(a) -> dict:
    if a.xmx:
        sim.JVM_ARGS = tuple(x for x in sim.JVM_ARGS if not x.startswith("-Xmx")) + (f"-Xmx{a.xmx}",)
    chosen = pick(designs(a.data), a.designs)
    reqs = [d["request"] for d in chosen]
    command = sim.helper_command()  # compiled before any timing
    out: dict[str, Any] = {"designs": len(chosen), "jvm_args": list(sim.JVM_ARGS), "cpus": os.cpu_count()}
    t0 = time.perf_counter()
    with sim.Simulator(command, canary=None) as s:
        out["startup_s"] = round(time.perf_counter() - t0, 3)
        times, kinds = [], collections.Counter()
        for r in reqs:
            t = time.perf_counter()
            rep = s.run(**r)
            times.append(time.perf_counter() - t)
            kinds["ok" if rep.get("ok") else rep.get("error_kind")] += 1
        out["first_request_s"] = round(times[0], 3)
        steady = sorted(times[1:])
        out["one_helper"] = {
            "total_s": round(sum(times), 2), "median_s": round(statistics.median(steady), 3),
            "mean_s": round(statistics.fmean(steady), 3), "p90_s": round(steady[int(0.9 * (len(steady) - 1))], 3),
            "max_s": round(steady[-1], 3), "replies": dict(kinds)}
        # a second pass over the same designs: the JIT is warm now
        warm = []
        for r in reqs:
            t = time.perf_counter()
            s.run(**r)
            warm.append(time.perf_counter() - t)
        out["one_helper_warm"] = {"median_s": round(statistics.median(warm), 3),
                                  "mean_s": round(statistics.fmean(warm), 3)}
        out["peak_memory_mb_one_helper"] = peak_memory_mb(s.pid)
    for size in a.pools:
        t = time.perf_counter()
        with sim.SimPool(size, command, canary=None) as pool:
            started = time.perf_counter() - t
            pool.run_many(reqs[: size])  # one request per helper before timing
            t = time.perf_counter()
            pool.run_many(reqs)
            cold = time.perf_counter() - t
            t = time.perf_counter()
            pool.run_many(reqs)  # the same 100 again: helpers warmed up, as in a long RL run
            wall = time.perf_counter() - t
            mem = [peak_memory_mb(x.pid) for x in pool.simulators]
        out[f"pool_{size}"] = {"startup_s": round(started, 2),
                               "first_pass_wall_s": round(cold, 2),
                               "warm_wall_s": round(wall, 2),
                               "warm_s_per_request": round(wall / len(reqs), 3),
                               "warm_requests_per_s": round(len(reqs) / wall, 2),
                               "peak_memory_mb": mem}
    return out


# --------------------------------------------------------------------------- warnings

def cmd_warnings(a) -> dict:
    chosen = designs(a.data)
    with sim.SimPool(a.helpers, canary=None) as pool:
        replies = pool.run_many([d["request"] for d in chosen])
    load_w, sim_w, kinds, faults = (collections.Counter() for _ in range(4))
    rows_load, rows_sim = collections.Counter(), collections.Counter()
    for d, r in zip(chosen, replies):
        if not r.get("ok"):
            kinds[r.get("error_kind")] += 1
            faults[f"{r.get('error_kind')}: {r.get('message')}"] += 1
            for w in r.get("load_warnings", []):
                load_w[w] += 1
                rows_load[w] += d["rows"]
            continue
        kinds["ok"] += 1
        for w in r.get("load_warnings", []):
            load_w[w] += 1
            rows_load[w] += d["rows"]
        seen = set()
        for f in r["flights"]:
            for w in f.get("warnings", []):
                seen.add(re.sub(r"\(\d+(\.\d+)? m/s\)", "(N m/s)", w))
        for w in seen:
            sim_w[w] += 1
            rows_sim[w] += d["rows"]
    return {"designs": len(chosen), "rows": sum(d["rows"] for d in chosen), "replies": dict(kinds),
            "faults": dict(faults.most_common()),
            "load_warnings": {w: {"designs": n, "rows": rows_load[w]} for w, n in load_w.most_common()},
            "sim_warnings": {w: {"designs": n, "rows": rows_sim[w]} for w, n in sim_w.most_common()}}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("command", choices=("repeat", "speed", "warnings"), help="which survey to run (see above)")
    ap.add_argument("data", type=Path, help="reference rows whose last message has a <design> block (.jsonl)")
    ap.add_argument("--designs", type=int, default=None,
                    help="designs to use (default 20 for repeat, 100 for speed, all for warnings)")
    ap.add_argument("--pools", type=lambda s: [int(x) for x in s.split(",") if x], default=[4, 8],
                    help="pool sizes for speed, comma separated (default 4,8)")
    ap.add_argument("--helpers", type=int, default=4, help="helpers for warnings (default 4)")
    ap.add_argument("--xmx", default=None, help="Java heap limit to try instead of sim.JVM_ARGS's, e.g. 256m")
    ap.add_argument("--out", type=Path, required=True, help="folder for the results")
    a = ap.parse_args(argv)
    if a.designs is None:
        a.designs = {"repeat": 20, "speed": 100}.get(a.command, 0)
    started = time.perf_counter()
    result = {"repeat": cmd_repeat, "speed": cmd_speed, "warnings": cmd_warnings}[a.command](a)
    result["elapsed_s"] = round(time.perf_counter() - started, 1)
    a.out.mkdir(parents=True, exist_ok=True)
    name = f"sim_{a.command}" + (f"_xmx{a.xmx}" if a.xmx else "") + ".json"
    with open(a.out / name, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(result, fh, indent=1)
        fh.write("\n")
    print(json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
