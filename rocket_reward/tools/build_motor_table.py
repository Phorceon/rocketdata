"""Rebuild the reward's motor table from OpenRocket's own motor list.

"A real motor" should mean "a motor OpenRocket 24.12 can fly, with the thrust
curve it will actually use". This script:

1. asks the reward's simulator helper (rocket_reward.sim) for OpenRocket's
   built-in motor list, and runs java/MotorStats.java (in this package) for the
   curve statistics the helper does not report (burn time, average and peak
   thrust, masses, delays). Both read the same OpenRocket motor database;
   the two lists are joined and cross-checked;
2. flies a small probe rocket (the package's canary.ork with its motor
   replaced) once per old table id, writing the id's maker, designation and
   digest exactly as the reward's cleaned file would (no motor type, see
   below), and records how OpenRocket found the motor (digest / name / none)
   and which list entry it flew;
3. applies the rebuild rule:
   * an id whose digest OpenRocket has stays, with the numbers of the list
     entry OpenRocket actually flies for it;
   * an id OpenRocket finds by name only stays only when exactly one
     OpenRocket thrust curve has that manufacturer and designation; it takes
     that curve's digest and numbers;
   * everything else is dropped;
   * OpenRocket list entries that no surviving id flies and whose
     manufacturer + designation no surviving id has are added under a new id
     "<manufacturer>-<designation>" (source "added");
4. flies the probe once per id of the new table and checks that every id is
   found by digest and flies the entry whose numbers it carries (repeats the
   assignment until it is stable);
5. writes the new table (same shape as the old one plus provenance fields)
   and a details file with every match, every changed number and every
   impulse-class mismatch.

The motor type is left out of the probe on purpose: OpenRocket's name
fallback filters by type, so a missing type gives the widest name match and
the 19 / 13 split recorded in tests/test_sim_java.py.

Usage (from the repo root; standard library only):
  python -X utf8 -m rocket_reward.tools.build_motor_table --out NEW.json
      [--old-table OLD.json] [--java-home /path/to/jdk-17] [--jar /path/to/OpenRocket-24.12.jar]
      [--details DETAILS.json] [--or-dump OR_MOTORS.jsonl] [--workers 4] [--no-add]
      [--rescue-by-curve]

--old-table defaults to the packaged data/motor_table.json; --java-home and
--jar default to the ROCKET_REWARD_JAVA_HOME and ROCKET_REWARD_JAR settings
the simulator uses. The packaged table was built with --rescue-by-curve from
the earlier 1,421-id table (2026-11-19): 1,409 ids, every one found by
OpenRocket 24.12 by its digest. Rerun this whenever the OpenRocket jar changes,
then check the result with the needs_java test
tests/test_sim_java.py::test_every_table_motor_is_found_by_digest.

--rescue-by-curve: an id whose digest OpenRocket lacks is also kept when
exactly one OpenRocket curve of the same maker has the same total impulse,
burn time and average thrust (to 1e-6).
"""
from __future__ import annotations

import argparse
import collections
import html
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

STATS_SOURCE = Path(__file__).resolve().parents[1] / "java" / "MotorStats.java"
DEFAULT_OLD_TABLE = Path(__file__).resolve().parents[1] / "data" / "motor_table.json"
STATS_CLASS = "MotorStats"

# Numbers copied from OpenRocket into every surviving entry (old keys first).
OLD_NUMBER_FIELDS = ("total_impulse_ns", "average_thrust_n", "burn_time_s", "diameter_m", "length_m")
EXTRA_NUMBER_FIELDS = ("max_thrust_n", "launch_mass_kg", "burnout_mass_kg")
REL_CHANGE_REPORTED = 0.02      # the task's "differs by more than 2%"

SOURCE_DIGEST = "openrocket_digest"          # old id, digest found in OpenRocket's list
SOURCE_NAME = "openrocket_name_unique"       # old id, found by name; exactly one curve has that name
SOURCE_ADDED = "added_from_openrocket"       # new id for an OpenRocket entry no old id flies
SOURCE_CURVE = "openrocket_same_curve"       # --rescue-by-curve: same maker, same impulse/burn/thrust
CURVE_MATCH_REL = 1e-6


def say(*a: object) -> None:
    print(*a, file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# OpenRocket's list

def run_motor_stats(sim: Any, java: Any, jar: Path) -> list[dict]:
    """Compile and run MotorStats.java against the compiled reward helper."""
    classes, _ = sim.compile_helper(java, jar)
    with tempfile.TemporaryDirectory(prefix="motorstats-") as tmp:
        cp = os.pathsep.join([str(jar), str(classes)])
        r = subprocess.run([str(java.javac), "--release", "17", "-nowarn", "-encoding", "UTF-8",
                            "-cp", cp, "-d", tmp, str(STATS_SOURCE)], capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"MotorStats.java did not compile:\n{r.stderr[-3000:]}")
        r = subprocess.run([str(java.java), *sim.JVM_ARGS, "-cp", cp + os.pathsep + tmp, STATS_CLASS],
                           capture_output=True, timeout=900)
        if r.returncode != 0:
            raise SystemExit(f"MotorStats failed (exit {r.returncode}):\n{r.stderr.decode('utf-8', 'replace')[-3000:]}")
    return [json.loads(line) for line in r.stdout.decode("utf-8").splitlines() if line.strip()]


def entry_key(m: dict) -> tuple:
    return (m["digest"], m["manufacturer"], m["designation"])


def join_lists(helper_list: list[dict], stats: list[dict]) -> list[dict]:
    """Attach MotorStats' numbers to the helper's list; both must describe the same entries."""
    def k(m: dict) -> tuple:
        return (m["digest"], m["manufacturer"], m["designation"], m.get("common_name"),
                m["diameter_m"], m["length_m"], m["total_impulse_ns"])
    pool = collections.defaultdict(list)
    for s in stats:
        pool[k(s)].append(s)
    out = []
    for h in helper_list:
        cands = pool.get(k(h))
        if not cands:
            raise SystemExit(f"MotorStats has no entry matching the helper's {k(h)}")
        s = cands.pop()
        merged = dict(s)
        merged.update({kk: h[kk] for kk in h})
        out.append(merged)
    left = sum(len(v) for v in pool.values())
    if left:
        raise SystemExit(f"MotorStats lists {left} entries the helper does not")
    return out


# ---------------------------------------------------------------------------
# probe flights

_MOTOR_RE = re.compile(r'<motor configid="cfg0">.*?</motor>', re.S)


def probe_ork(base: str, manufacturer: str, designation: str, digest: str | None,
              diameter_m: Any, length_m: Any) -> str:
    x = lambda s: html.escape(str(s), quote=False)
    parts = [f'<motor configid="cfg0">', f"<manufacturer>{x(manufacturer)}</manufacturer>",
             f"<designation>{x(designation)}</designation>"]
    if digest:
        parts.append(f"<digest>{x(digest)}</digest>")
    dia = diameter_m if isinstance(diameter_m, (int, float)) else 0.038
    ln = length_m if isinstance(length_m, (int, float)) else 0.2
    parts.append(f"<diameter>{dia}</diameter><length>{ln}</length><delay>10.0</delay></motor>")
    text, n = _MOTOR_RE.subn(lambda _: "".join(parts), base)
    if n != 1:
        raise SystemExit("the probe rocket (canary.ork) no longer has exactly one cfg0 motor")
    return text


def probe(sim: Any, base: str, items: list[tuple[str, dict]], workers: int) -> dict[str, dict]:
    """Fly the probe rocket once per (key, entry); return key -> first motor_lookup entry."""
    reqs = [dict(ork_text_or_path=probe_ork(base, e["manufacturer"], e["designation"], e.get("digest"),
                                            e.get("diameter_m"), e.get("length_m")),
                 rail_m=1.5, flights=[{"wind_ms": 2.0, "seed": 1}], allow_motor_substitution=True,
                 max_sim_time_s=5.0)
            for _, e in items]
    t = time.time()
    with sim.SimPool(workers, canary=None) as pool:
        replies = pool.run_many(reqs)
    say(f"  probed {len(reqs)} motors in {time.time() - t:.1f} s")
    out = {}
    for (key, _), r in zip(items, replies):
        ml = r.get("motor_lookup") or []
        look = dict(ml[0]) if ml else {"found_by": None}
        look["reply_ok"] = bool(r.get("ok"))
        look["error_kind"] = r.get("error_kind")
        out[key] = look
    return out


# ---------------------------------------------------------------------------
# names

def norm_text(s: str) -> str:
    return s.strip().lower()


def _maker_words(s: str) -> list[str]:
    words = re.sub(r"[^a-z0-9]+", " ", s.lower()).split()
    while words and words[-1] in ("inc", "ltd", "llc", "gmbh", "co"):
        words.pop()
    return words


def same_maker(a: str, b: str) -> bool:
    """'Cesaroni Technology' ~ 'Cesaroni Technology Inc.', 'Estes' ~ 'Estes Industries, Inc.':
    equal after dropping punctuation and a company suffix, or one is a whole-word prefix
    of the other. Different companies that share a curve (AeroTech / Quest) stay apart."""
    wa, wb = _maker_words(a), _maker_words(b)
    if not wa or not wb:
        return False
    n = min(len(wa), len(wb))
    return wa[:n] == wb[:n]


def maker_aliases(old: dict, or_list: list[dict]) -> dict[str, set]:
    """Old-table maker (lower) -> the OpenRocket makers (lower) that are the same company."""
    or_makers = {norm_text(m["manufacturer"]) for m in or_list}
    alias = collections.defaultdict(set)
    for v in old.values():
        mk = norm_text(v["manufacturer"])
        alias[mk].add(mk)
        alias[mk].update(o for o in or_makers if same_maker(mk, o))
    for o in or_makers:
        alias[o].add(o)
    return alias


def same_name(or_list: list[dict], makers: set, designation: str) -> list[dict]:
    des = norm_text(designation)
    return [m for m in or_list if norm_text(m["manufacturer"]) in makers and norm_text(m["designation"]) == des]


# ---------------------------------------------------------------------------
# impulse class (same rules as rocket_reward.motors)

def class_check(motors_mod: Any, key: str, e: dict) -> dict | None:
    by_impulse = motors_mod.impulse_class(e.get("total_impulse_ns"))
    written = motors_mod.class_from_designation(e.get("designation"))
    if by_impulse == written:
        return None
    step = (ord(by_impulse) - ord(written)) if (by_impulse and written) else None
    return {"id": key, "designation": e.get("designation"), "total_impulse_ns": e.get("total_impulse_ns"),
            "class_by_impulse": by_impulse, "class_in_designation": written, "letters_off": step}


# ---------------------------------------------------------------------------

def rel_change(a: Any, b: Any) -> float | None:
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        return None
    if a == 0:
        return 0.0 if b == 0 else math.inf
    return (b - a) / a


def numbers_from(m: dict) -> dict:
    out = {f: m[f] for f in OLD_NUMBER_FIELDS}
    out.update({f: m.get(f) for f in EXTRA_NUMBER_FIELDS})
    out["digest"] = m["digest"]
    out["motor_type"] = m.get("type")
    out["standard_delays_s"] = m.get("delays_s")
    out["openrocket_manufacturer"] = m["manufacturer"]
    out["openrocket_designation"] = m["designation"]
    out["openrocket_common_name"] = m.get("common_name")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--old-table", default=str(DEFAULT_OLD_TABLE),
                    help="the table to rebuild (default: the packaged data/motor_table.json)")
    ap.add_argument("--out", required=True, help="where to write the new motor table JSON")
    ap.add_argument("--java-home", help="JDK folder (default: ROCKET_REWARD_JAVA_HOME)")
    ap.add_argument("--jar", help="OpenRocket 24.12 jar (default: ROCKET_REWARD_JAR)")
    ap.add_argument("--details", help="details JSON (default: <out stem>_details.json)")
    ap.add_argument("--or-dump", help="also save OpenRocket's joined motor list (JSON lines) here")
    ap.add_argument("--workers", type=int, default=4, help="simulator helpers for the probe flights (default 4)")
    ap.add_argument("--no-add", action="store_true", help="do not add OpenRocket motors no old id points to")
    ap.add_argument("--rescue-by-curve", action="store_true",
                    help="also keep an id OpenRocket lacks when exactly one OpenRocket curve of the same maker "
                         "has the same total impulse, burn time and average thrust (variant, not the agreed rule)")
    a = ap.parse_args(argv)

    if a.java_home:
        os.environ["ROCKET_REWARD_JAVA_HOME"] = a.java_home
    if a.jar:
        os.environ["ROCKET_REWARD_JAR"] = a.jar
    from rocket_reward import sim, motors as motors_mod

    old = json.loads(Path(a.old_table).read_text(encoding="utf-8"))
    out_path = Path(a.out)
    details_path = Path(a.details) if a.details else out_path.with_name(out_path.stem + "_details.json")
    base = (Path(sim.PACKAGE_DIR) / "data" / "canary.ork").read_text(encoding="utf-8")

    # 1. OpenRocket's list -------------------------------------------------
    say("reading OpenRocket's motor list through the reward helper ...")
    with sim.Simulator() as s:
        helper_list = s.motor_list()
        ping = dict(s.ping_reply)
    java = sim.find_java()
    jar = sim.find_jar()
    say("running MotorStats.java for burn time, thrust and masses ...")
    or_list = join_lists(helper_list, run_motor_stats(sim, java, jar))
    or_list.sort(key=lambda m: (m["digest"], m["manufacturer"], m["designation"], m["total_impulse_ns"], m["length_m"]))
    if a.or_dump:
        with open(a.or_dump, "w", encoding="utf-8", newline="\n") as fh:
            for m in sorted(or_list, key=lambda m: (m["digest"], m["manufacturer"], m["designation"])):
                fh.write(json.dumps(m, ensure_ascii=False) + "\n")
    by_digest = collections.defaultdict(list)
    for m in or_list:
        by_digest[m["digest"]].append(m)
    by_entry = {}
    for m in or_list:
        by_entry.setdefault(entry_key(m), m)   # a key listed twice: numbers nearly equal (checked below)
    dup_same_key = [k for k, n in collections.Counter(entry_key(m) for m in or_list).items() if n > 1]
    dup_same_key_numbers = {}
    for k in dup_same_key:
        ms = [m for m in or_list if entry_key(m) == k]
        spread = {f: max(abs(rel_change(ms[0][f], m[f]) or 0.0) for m in ms) for f in OLD_NUMBER_FIELDS + EXTRA_NUMBER_FIELDS}
        dup_same_key_numbers["|".join(k)] = spread
        if max(spread.values()) > 1e-3:
            say(f"  warning: OpenRocket lists {k} more than once with numbers up to "
                f"{max(spread.values()):.2%} apart")
    say(f"  {len(or_list)} list entries, {len(by_digest)} distinct thrust curves (digests); helper ping says "
        f"motor_database_size {ping.get('motor_database_size')}")

    # 2. probe every old id ------------------------------------------------
    say("probing every old table id ...")
    old_items = sorted(old.items())
    looks = probe(sim, base, old_items, a.workers)
    alias = maker_aliases(old, or_list)
    say("  maker names treated as one company: " + "; ".join(
        f"{k} = {sorted(v - {k})}" for k, v in sorted(alias.items()) if len(v) > 1))

    matches = {}
    for key, e in old_items:
        lk = looks[key]
        in_list = e.get("digest") in by_digest
        named = same_name(or_list, alias[norm_text(e["manufacturer"])], e["designation"])
        named_digests = sorted({m["digest"] for m in named})
        same_curve = sorted({m["digest"] for m in or_list
                             if norm_text(m["manufacturer"]) in alias[norm_text(e["manufacturer"])]
                             and all(isinstance(e.get(f), (int, float)) and e[f] and
                                     abs(m[f] - e[f]) <= CURVE_MATCH_REL * abs(e[f])
                                     for f in ("total_impulse_ns", "burn_time_s", "average_thrust_n"))})
        rec = {"found_by": lk.get("found_by"), "digest_in_openrocket": in_list,
               "flown": None if not lk.get("flown_digest") else
               {"digest": lk["flown_digest"], "manufacturer": lk["flown_manufacturer"],
                "designation": lk["flown_designation"]},
               "same_name_entries": len(named), "same_name_curves": len(named_digests),
               "same_name_digests": named_digests, "same_curve_digests": same_curve}
        if in_list and lk.get("found_by") != "digest":
            say(f"  warning: {key} has a listed digest but OpenRocket found it by {lk.get('found_by')}")
        if in_list:
            rec["decision"] = "keep"
            rec["source"] = SOURCE_DIGEST
            rec["new_digest"] = e["digest"]
        elif len(named_digests) == 1:
            rec["decision"] = "keep"
            rec["source"] = SOURCE_NAME
            rec["new_digest"] = named_digests[0]
        elif a.rescue_by_curve and not in_list and len(same_curve) == 1:
            rec["decision"] = "keep"
            rec["source"] = SOURCE_CURVE
            rec["new_digest"] = same_curve[0]
        else:
            rec["decision"] = "drop"
            rec["drop_reason"] = (
                "OpenRocket cannot load it (no curve with this digest or name)" if lk.get("found_by") in (None, "none")
                else f"OpenRocket finds it by name only and {len(named_digests)} curves have exactly this "
                     f"manufacturer and designation" if named_digests
                else "OpenRocket finds it by name only, through a looser name match "
                     f"(flies {lk.get('flown_manufacturer')} {lk.get('flown_designation')}); no curve has exactly "
                     "this manufacturer and designation")
        matches[key] = rec

    # 3. the new table -----------------------------------------------------
    new: dict[str, dict] = {}
    for key, e in old_items:
        rec = matches[key]
        if rec["decision"] != "keep":
            continue
        d = rec["new_digest"]
        # first guess: the flown entry for a digest match, else the entry with this name
        flown = rec["flown"]
        if rec["source"] == SOURCE_DIGEST and flown and flown["digest"] == d:
            m = by_entry[(flown["digest"], flown["manufacturer"], flown["designation"])]
        else:
            cands = ([m for m in by_digest[d] if norm_text(m["designation"]) == norm_text(e["designation"])]
                     or ([m for m in by_digest[d] if (m["digest"], m["manufacturer"], m["designation"]) ==
                          (flown["digest"], flown["manufacturer"], flown["designation"])] if flown else [])
                     or by_digest[d])
            m = cands[0]
        ne = {"manufacturer": e["manufacturer"], "designation": e["designation"]}
        ne.update(numbers_from(m))
        ne["in_dataset"] = e.get("in_dataset")
        ne["source"] = rec["source"]
        new[key] = ne

    added = []
    if not a.no_add:
        flown_entries = set()
        for rec in matches.values():
            if rec["decision"] == "keep" and rec["flown"]:
                flown_entries.add((rec["flown"]["digest"], rec["flown"]["manufacturer"], rec["flown"]["designation"]))
        survivor_names = set()
        for e in new.values():
            for mk in alias.get(norm_text(e["manufacturer"]), {norm_text(e["manufacturer"])}):
                survivor_names.add((mk, norm_text(e["designation"])))
        lower_keys = {k.lower() for k in new}
        survivor_digests = {e["digest"] for e in new.values()}
        for m in sorted(or_list, key=lambda m: (m["manufacturer"], m["designation"], m["digest"])):
            name = (norm_text(m["manufacturer"]), norm_text(m["designation"]))
            if entry_key(m) in flown_entries and m["digest"] in survivor_digests:
                continue
            if name in survivor_names and m["digest"] in survivor_digests:
                continue
            nid = f"{m['manufacturer']}-{m['designation']}"
            if nid.lower() in lower_keys:
                n = 2
                while f"{nid}-v{n}".lower() in lower_keys:
                    n += 1
                nid = f"{nid}-v{n}"
            ne = {"manufacturer": m["manufacturer"], "designation": m["designation"]}
            ne.update(numbers_from(m))
            ne["in_dataset"] = False
            ne["source"] = SOURCE_ADDED
            ne["shares_curve_with"] = sorted(k for k, v in new.items() if v["digest"] == m["digest"])
            new[nid] = ne
            lower_keys.add(nid.lower())
            survivor_names.add(name)
            added.append(nid)

    # 4. verify: every id flies by digest, and carries the flown entry's numbers
    rounds = []
    for rnd in range(1, 4):
        say(f"verifying the new table, round {rnd} ...")
        vlooks = probe(sim, base, sorted(new.items()), a.workers)
        changed, bad = [], []
        for key, lk in vlooks.items():
            if lk.get("found_by") != "digest" or not lk.get("reply_ok"):
                bad.append({"id": key, "found_by": lk.get("found_by"), "error_kind": lk.get("error_kind")})
                continue
            fk = (lk["flown_digest"], lk["flown_manufacturer"], lk["flown_designation"])
            cur = new[key]
            if (cur["digest"], cur["openrocket_manufacturer"], cur["openrocket_designation"]) != fk:
                cur.update(numbers_from(by_entry[fk]))
                changed.append(key)
        rounds.append({"round": rnd, "changed": changed, "not_found_by_digest": bad})
        if not changed:
            break
    if rounds[-1]["changed"] or rounds[-1]["not_found_by_digest"]:
        say(f"  WARNING: verification not clean: {rounds[-1]}")
    for key, lk in vlooks.items():
        new[key]["flown_as"] = f"{lk.get('flown_manufacturer')} {lk.get('flown_designation')}"

    # 5. compare and write ---------------------------------------------------
    diffs = []
    for key, e in old_items:
        if key not in new:
            continue
        ne = new[key]
        row = {"id": key, "source": ne["source"], "digest_changed": ne["digest"] != e.get("digest")}
        worst = 0.0
        for f in OLD_NUMBER_FIELDS:
            r = rel_change(e.get(f), ne.get(f))
            row[f] = {"old": e.get(f), "new": ne.get(f), "rel": r}
            if r is None:
                worst = math.inf
            else:
                worst = max(worst, abs(r))
        row["max_abs_rel"] = worst if math.isfinite(worst) else None
        for f in OLD_NUMBER_FIELDS:
            if row[f]["rel"] is not None and not math.isfinite(row[f]["rel"]):
                row[f]["rel"] = None
        diffs.append(row)
    class_mismatch = [c for k in sorted(new) if (c := class_check(motors_mod, k, new[k]))]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({k: dict(sorted(new[k].items())) for k in sorted(new)}, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    details = {
        "openrocket": {"version": ping.get("openrocket"), "helper": ping.get("helper"),
                       "motor_database_size_ping": ping.get("motor_database_size"),
                       "list_entries": len(or_list), "distinct_digests": len(by_digest),
                       "digests_with_several_entries": sum(1 for v in by_digest.values() if len(v) > 1),
                       "same_entry_listed_twice": len(dup_same_key),
                       "same_entry_listed_twice_max_rel_spread": dup_same_key_numbers},
        "old_ids": len(old), "new_ids": len(new),
        "counts": dict(collections.Counter(r["found_by"] for r in matches.values())),
        "decisions": dict(collections.Counter(r.get("source", "drop") for r in matches.values())),
        "dropped": {k: r for k, r in matches.items() if r["decision"] == "drop"},
        "kept_by_name": {k: r for k, r in matches.items() if r.get("source") == SOURCE_NAME},
        "kept_by_curve": {k: r for k, r in matches.items() if r.get("source") == SOURCE_CURVE},
        "added": {k: new[k] for k in added},
        "matches": matches,
        "number_diffs": diffs,
        "class_mismatches": class_mismatch,
        "verification_rounds": rounds,
    }
    with open(details_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(details, fh, indent=1, ensure_ascii=False, default=lambda x: None)
        fh.write("\n")
    n_changed = sum(1 for d in diffs if d["max_abs_rel"] is None or d["max_abs_rel"] > REL_CHANGE_REPORTED)
    say(f"done: {len(old)} old ids -> {len(new)} ids ({details['decisions']}, added {len(added)}); "
        f"{n_changed} kept ids change a number by more than {REL_CHANGE_REPORTED:.0%}; "
        f"{len(class_mismatch)} class-letter mismatches; wrote {out_path} and {details_path}")
    if sim.live_processes():
        say("warning: helper processes still alive")
    return 0


if __name__ == "__main__":
    sys.exit(main())
