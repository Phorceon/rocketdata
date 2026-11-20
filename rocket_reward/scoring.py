"""Run the stages in order and turn the outcome into one score.

The package exports the function `score` from here; this module is called
scoring.py so that the function does not hide the module.

    preflight(answer_text)                          stages 1-4, no simulator needed
    score(answer_text, requirements, simulator=...) the full ladder, one answer
    score_many(answers, requirements_list, ...)     the full ladder, many answers in parallel

Stages 1-4 are format (parse.py), parts (parts.py), motor (motors.py) and
limits (limit_checks.py). Stage 4 and everything after it look at the cleaned
copy of the design (clean.py), never at the model's own copy. Stages 5-7 are
build (fit.py), flight (flight.py) and targets (targets.py); they read the
reply of the OpenRocket simulator (sim.py) for the cleaned copy, written as an
OpenRocket file by ork.py.

When `score` is given no simulator it uses one shared default: a SimPool
started on first use (ROCKET_REWARD_WORKERS helpers, default 4, at most the
CPU count minus one) and closed when Python exits.

Unknown motors (stage 3): with a simulator, half the credit comes from three
facts about the written motor and half from a "shadow flight": the same design
with each unknown motor replaced by the nearest real one
(motors.MotorTable.nearest_real), scored through stages 4-7. The score stays
inside the motor band whatever the shadow does.

Unexpected errors (DESIGN.md section 3): when a check crashes on one answer,
`score` saves the answer and the traceback to a quarantine folder and returns
score=None, so the answer is left out of training. If that happens too often
the reward is broken, and `score` raises RewardSetupError instead.
"""
from __future__ import annotations

import atexit
import collections
import concurrent.futures
import hashlib
import json
import os
import tempfile
import threading
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Sequence

from . import ladder
from .errors import RewardSetupError
from .parse import parse_answer
from .records import Requirements, Result, StageCheck
from .tree import Node

QUARANTINE_ENV = "ROCKET_REWARD_QUARANTINE"
QUARANTINE_DIRNAME = "rocket_reward_quarantine"
WORKERS_ENV = "ROCKET_REWARD_WORKERS"
DEFAULT_WORKERS = 4       # simulator helpers in the default pool; 4 is the fastest measured on an 8-core PC

# When the reward itself keeps crashing it is broken, not the answers.
ERROR_WINDOW = 500        # how many recent answers are remembered
ERROR_SHARE = 0.01        # more than 1% of them crashing means the reward is broken ...
ERROR_MIN_COUNT = 5       # ... but only once at least this many crashed
ERROR_RUN = 5             # this many crashes in a row also means it is broken

MAX_SHADOW_SHOWN = 3      # substitutes named in the reason of a shadow flight
MAX_SHADOW_REASON_CHARS = 240  # the shadow's own first reason, shortened (display only)
# The natural rocket (overrides removed) is built only for its mass and balance
# point, which OpenRocket reports before flying; its one flight is cut short
# after this many simulated seconds. On all 158 reference designs with overrides
# the reported mass, balance point and reference length are identical to a full
# flight's, at about a tenth of the time.
NATURAL_MAX_SIM_TIME_S = 0.05


# --------------------------------------------------------------------------- stage hooks
# Each stage lives in its own module. They are imported only when first needed,
# so importing this module does no work, and tests can swap one hook for a fake.

def _check_parts(root: Node) -> StageCheck:
    from .parts import check_parts
    return check_parts(root)


def _check_motors(root: Node, table: Any) -> StageCheck:
    from .motors import check_motors
    return check_motors(root, table)


def _clean_design(root: Node, table: Any) -> tuple[Node, list[str]]:
    from .clean import clean_design
    return clean_design(root, table)   # with the packaged material table


def _check_limits(root: Node, table: Any) -> StageCheck:
    from .limit_checks import check_limits
    return check_limits(root, table)


def _write_ork(root: Node) -> str:
    from .ork import design_to_ork
    return design_to_ork(root)


def _flight_config_id(root: Node) -> Optional[str]:
    from .ork import flight_config_id
    return flight_config_id(root)


def _rail_length(root: Node, table: Any) -> float:
    from .flight import rail_length_m
    return rail_length_m(root, table)


def _flight_plan(requirements: Requirements) -> list[dict]:
    from .flight import flight_plan
    return flight_plan(requirements)


def _natural_copy(root: Node) -> tuple[Node, int]:
    from .clean import natural_copy
    return natural_copy(root)


def _check_build(reply: Any, natural: Optional[dict], root: Node) -> StageCheck:
    from .fit import check_build
    return check_build(reply, natural, root)


def _check_flight(reply: Any, requirements: Requirements) -> StageCheck:
    from .flight import check_flight
    return check_flight(reply, requirements)


def _check_targets(reply: Any, requirements: Requirements, root: Node, table: Any) -> StageCheck:
    from .targets import check_targets
    return check_targets(reply, requirements, root, table)


def _flight_metrics(reply: Any) -> dict[str, Any]:
    from .flight import nominal_metrics
    return nominal_metrics(reply)


def _substitute_motors(root: Node, table: Any, same_maker: bool = True) -> tuple[Optional[Node], list[dict[str, Any]]]:
    from .motors import substitute_unknown_motors
    return substitute_unknown_motors(root, table, same_maker=same_maker)


def _load_motor_table() -> Any:
    from .motors import MotorTable
    return MotorTable.load()


def _start_simulator(size: int) -> Any:
    from .sim import SimPool
    return SimPool(size)


_table_lock = threading.Lock()
_table_cache: list[Any] = []   # holds the motor table once it is loaded


def default_motor_table() -> Any:
    """The motor table from data/motor_table.json, loaded on first use and kept.

    A missing or unreadable table is a broken installation, so any failure here
    raises RewardSetupError (never a score, never a quarantined answer).
    """
    with _table_lock:
        if not _table_cache:
            try:
                _table_cache.append(_load_motor_table())
            except RewardSetupError:
                raise
            except Exception as exc:
                raise RewardSetupError(
                    f"could not load the motor table ({type(exc).__name__}: {exc}); "
                    f"check that rocket_reward/data/motor_table.json is present and readable") from exc
        return _table_cache[0]


# --------------------------------------------------------------------------- default simulator

_sim_lock = threading.Lock()
_sim_cache: list[Any] = []     # holds the default simulator once it is started
_atexit_done: list[bool] = []


def default_workers() -> int:
    """Size of the default simulator pool: $ROCKET_REWARD_WORKERS (default 4),
    at most the CPU count minus one, at least 1. A value that is not a whole
    number of 1 or more is a setup mistake and raises RewardSetupError."""
    raw = os.environ.get(WORKERS_ENV)
    wanted = DEFAULT_WORKERS
    if raw is not None and raw.strip():
        try:
            wanted = int(raw.strip())
        except ValueError:
            wanted = 0
        if wanted < 1:
            raise RewardSetupError(f"{WORKERS_ENV} must be a whole number of 1 or more, got {raw!r}")
    return max(1, min(wanted, (os.cpu_count() or 2) - 1))


def default_simulator() -> Any:
    """The shared simulator `score` uses when it is given none: a SimPool of
    default_workers() helpers, started on first use (this takes a few
    seconds and needs Java and the OpenRocket jar) and closed when Python
    exits. Safe to call from many threads; only one pool is ever started."""
    with _sim_lock:
        if not _sim_cache:
            pool = _start_simulator(default_workers())
            _sim_cache.append(pool)
            if not _atexit_done:
                atexit.register(close_default_simulator)
                _atexit_done.append(True)
        return _sim_cache[0]


def close_default_simulator() -> None:
    """Stop the default simulator if it was started (the next score starts a new one)."""
    with _sim_lock:
        pools = list(_sim_cache)
        _sim_cache.clear()
    for pool in pools:
        close = getattr(pool, "close", None)
        if callable(close):
            close()


def _expect(check: Any, stage_key: str) -> StageCheck:
    """A stage must return a StageCheck for its own stage. Anything else is a
    bug in the reward, raised so that it is quarantined and counted."""
    if not isinstance(check, StageCheck) or check.stage != stage_key:
        raise TypeError(f"the {stage_key} stage returned {check!r}, not a StageCheck for {stage_key!r}")
    return check


# --------------------------------------------------------------------------- preflight

@dataclass
class Preflight:
    """What stages 1-4 found out about one answer.

    checks:     one StageCheck per stage that ran, in ladder order; it stops at
                the first failure
    failed:     the failing StageCheck, or None when all four passed
    root:       the model's design tree ("openrocket" node), when it parsed
    clean_root: the cleaned copy (clean.py), when stage 3 passed
    notes:      what the cleaning changed, in plain words
    """

    checks: list[StageCheck] = field(default_factory=list)
    failed: Optional[StageCheck] = None
    root: Optional[Node] = None
    clean_root: Optional[Node] = None
    notes: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True when the design passed stages 1-4."""
        return self.failed is None and len(self.checks) == 4

    def defects(self) -> list[str]:
        """Small problems found by the stages that ran."""
        return [d for c in self.checks for d in c.defects]


def preflight(answer_text: str, truncated: bool = False, motor_table: Any = None) -> Preflight:
    """Run stages 1-4 (format, parts, motor, limits) on one answer.

    `motor_table` defaults to the packaged table, loaded once. Errors inside a
    check are not caught here: `score` handles them. Use this to see why an
    answer fails without needing the simulator. It never flies anything, so a
    design with an unknown motor gets the facts-only credit here (no shadow
    flight); `score` with a simulator can give it more.
    """
    pre = Preflight()
    _run_preflight(pre, answer_text, truncated, motor_table)
    return pre


def _run_preflight(pre: Preflight, answer_text: str, truncated: bool, motor_table: Any) -> None:
    """Fill `pre` stage by stage, so a crash still leaves what was done so far."""
    check, root = parse_answer(answer_text, truncated)
    pre.checks.append(_expect(check, "format"))
    if not check.passed:
        pre.failed = check
        return
    if root is None:
        raise TypeError("the format stage passed but gave no design tree")
    _preflight_tree(pre, root, motor_table)


def _preflight_tree(pre: Preflight, root: Node, motor_table: Any) -> None:
    """Stages 2-4 on a design tree that passed stage 1 (also used for shadow flights)."""

    def record(check: StageCheck) -> bool:
        pre.checks.append(check)
        if not check.passed:
            pre.failed = check
        return check.passed

    pre.root = root
    if not record(_expect(_check_parts(root), "parts")):
        return

    table = motor_table if motor_table is not None else default_motor_table()
    if not record(_expect(_check_motors(root, table), "motor")):
        return

    cleaned = _clean_design(root, table)
    if not (isinstance(cleaned, tuple) and len(cleaned) == 2 and isinstance(cleaned[0], dict)):
        raise TypeError(f"clean_design returned {type(cleaned).__name__}, not (tree, notes)")
    pre.clean_root, notes = cleaned
    pre.notes = [str(n) for n in (notes or [])]

    record(_expect(_check_limits(pre.clean_root, table), "limits"))


# --------------------------------------------------------------------------- error tracking

class ErrorTracker:
    """Remembers whether each of the last answers crashed the reward.

    `record(crashed)` raises RewardSetupError once more than ERROR_SHARE of
    the remembered answers (and at least ERROR_MIN_COUNT of them) crashed, or
    ERROR_RUN crashed in a row. Each test can make its own tracker. Safe to
    use from many threads.
    """

    def __init__(self, window: int = ERROR_WINDOW, share: float = ERROR_SHARE,
                 min_count: int = ERROR_MIN_COUNT, run: int = ERROR_RUN) -> None:
        self.window = max(1, int(window))
        self.share = share
        self.min_count = min_count
        self.run = run
        self._recent: collections.deque[bool] = collections.deque(maxlen=self.window)
        self._in_a_row = 0
        self._lock = threading.Lock()

    @property
    def errors(self) -> int:
        """How many of the remembered answers crashed."""
        return sum(self._recent)

    @property
    def in_a_row(self) -> int:
        """How many answers in a row crashed, counting back from the latest."""
        return self._in_a_row

    def __len__(self) -> int:
        return len(self._recent)

    def reset(self) -> None:
        with self._lock:
            self._recent.clear()
            self._in_a_row = 0

    def record(self, crashed: bool) -> None:
        with self._lock:
            self._recent.append(bool(crashed))
            self._in_a_row = self._in_a_row + 1 if crashed else 0
            errors, seen, row = sum(self._recent), len(self._recent), self._in_a_row
        if not crashed:
            return
        if row >= self.run:
            raise RewardSetupError(
                f"the reward crashed on {row} answers in a row; it is probably broken. "
                f"Look at the saved answers in {quarantine_dir()} and fix the failing check")
        if errors >= self.min_count and errors > self.share * seen:
            raise RewardSetupError(
                f"the reward crashed on {errors} of the last {seen} answers "
                f"(more than {self.share:.0%}); look at the saved answers in "
                f"{quarantine_dir()} and fix the failing check")


_default_tracker = ErrorTracker()


def default_tracker() -> ErrorTracker:
    """The tracker `score` uses when none is given."""
    return _default_tracker


def quarantine_dir() -> Path:
    """Folder for answers that crashed the reward: $ROCKET_REWARD_QUARANTINE,
    or a "rocket_reward_quarantine" folder in the system temp folder."""
    env = os.environ.get(QUARANTINE_ENV)
    return Path(env) if env else Path(tempfile.gettempdir()) / QUARANTINE_DIRNAME


def _quarantine(answer_text: Any, truncated: bool, requirements: Any, tb: str) -> Path:
    """Save the answer and the traceback as one JSON file and return its path.

    Failing to save is a broken machine (full disk, no permission), so it
    raises RewardSetupError.
    """
    folder = quarantine_dir()
    text = answer_text if isinstance(answer_text, str) else repr(answer_text)
    digest = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]
    path = folder / (f"{time.strftime('%Y%m%d-%H%M%S')}-{time.time_ns() % 10**9:09d}-"
                     f"{threading.get_ident() % 10**6:06d}-{digest}.json")
    record = {
        "answer_text": text,
        "truncated": bool(truncated),
        "requirements_id": getattr(requirements, "id", None),
        "traceback": tb,
    }
    try:
        folder.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(record, fh, ensure_ascii=False, indent=1)
    except OSError as exc:
        raise RewardSetupError(
            f"an answer crashed the reward and could not be saved to {folder} ({exc}); "
            f"make that folder writable or set {QUARANTINE_ENV} to one that is") from exc
    return path


# --------------------------------------------------------------------------- stages 1-4 results

def _stopped_at(pre: Preflight) -> Result:
    """Result for a design that failed one of stages 1-4."""
    failed = pre.failed
    if failed is None:
        raise TypeError("_stopped_at needs a preflight with a failed stage")
    defects = pre.defects()
    return Result(
        score=ladder.stage_score(failed.stage, failed.credit, len(defects)),
        stage=failed.stage,
        stages_passed=ladder.stage_index(failed.stage),
        credit=ladder.clamp01(failed.credit),
        reasons=list(failed.reasons),
        defects=defects,
    )


def preflight_result(pre: Preflight) -> Optional[Result]:
    """The Result a design that stopped in stages 1-4 gets without a
    simulator, or None when it passed all four (its score then needs the
    simulator stages). It flies nothing: an unknown motor gets the
    facts-only credit, while `score` with a simulator adds a shadow flight."""
    return _stopped_at(pre) if pre.failed is not None else None


# --------------------------------------------------------------------------- stages 5-7

def _fly(simulator: Any, ork_text: str, rail_m: float, flights: list[dict], config_id: Optional[str],
         **extra: Any) -> Any:
    """One simulator run. A simulator that was closed under us is a setup
    problem, never a design's fault, so its RuntimeError becomes RewardSetupError."""
    try:
        return simulator.run(ork_text, rail_m=rail_m, flights=flights, config_id=config_id, **extra)
    except RewardSetupError:
        raise
    except RuntimeError as exc:
        raise RewardSetupError(f"the simulator stopped while an answer was being scored ({exc}); "
                               f"start a new one") from exc


def _sim_result(check: StageCheck, defects: list[str], metrics: dict[str, Any],
                flags: dict[str, Any]) -> Result:
    """Result for a design that stopped at `check` (one of stages 5-7)."""
    stage = check.stage
    passed_all = stage == "targets"
    return Result(
        score=ladder.stage_score(stage, check.credit, len(defects)),
        stage=stage,
        stages_passed=len(ladder.STAGES) if passed_all else ladder.stage_index(stage),
        credit=ladder.clamp01(check.credit),
        reasons=list(check.reasons),
        defects=list(defects),
        metrics=dict(metrics),
        flags={**flags, "stage_info": check.info},
    )


def _run_simulator_stages(pre: Preflight, requirements: Requirements, simulator: Any,
                          table: Any) -> Result:
    """Stages 5-7 (build, flight, targets) on `pre.clean_root`, which passed stages 1-4.

    The cleaned design is written as an OpenRocket file (a file that cannot be
    written fails the build stage with credit 0) and flown on the launch rail
    and in the three winds stage 6 asks for. When it carries mass or balance
    overrides, the same design without them is also built (one flight, cut
    short after NATURAL_MAX_SIM_TIME_S) so that stage 5 can bound what they do. The first stage that does not pass ends
    the ladder; defects from every stage run lower the score.
    """
    root = pre.clean_root
    if root is None:
        raise TypeError("the simulator stages need the cleaned design")
    defects = pre.defects()
    flags: dict[str, Any] = {}
    from .ork import OrkWriteError
    try:
        text = _write_ork(root)
    except OrkWriteError as exc:
        check = StageCheck("build", False, 0.0,
                           reasons=[f"the design cannot be written as an OpenRocket file: {exc}"],
                           info={"built": False})
        return _sim_result(check, defects, {}, flags)
    rail = _rail_length(root, table)
    plan = _flight_plan(requirements)
    config_id = _flight_config_id(root)
    flags.update(rail_m=rail, config_id=config_id)
    reply = _fly(simulator, text, rail, plan, config_id)
    if isinstance(reply, dict) and reply.get("ok") is not True and isinstance(reply.get("error_kind"), str):
        flags["sim_error_kind"] = reply["error_kind"]

    natural: Optional[dict] = None
    if isinstance(reply, dict) and reply.get("ok") is True:
        nat_root, removed = _natural_copy(root)
        if removed:
            flags["overrides_removed"] = removed
            try:
                nat_text = _write_ork(nat_root)
            except OrkWriteError as exc:
                natural = {"ok": False, "error_kind": "load", "message": str(exc)}
            else:
                from .limits import NOMINAL_FLIGHT
                got = _fly(simulator, nat_text, rail, [plan[min(NOMINAL_FLIGHT, len(plan) - 1)]], config_id,
                           max_sim_time_s=NATURAL_MAX_SIM_TIME_S)
                natural = got if isinstance(got, dict) else {"ok": False, "message": "no reply"}

    build = _expect(_check_build(reply, natural, root), "build")
    defects += build.defects
    metrics = _flight_metrics(reply)
    if not build.passed:
        return _sim_result(build, defects, metrics, flags)

    flight = _expect(_check_flight(reply, requirements), "flight")
    defects += flight.defects
    fm = flight.info.get("metrics") if isinstance(flight.info, dict) else None
    if isinstance(fm, dict) and fm:
        metrics = fm
    if not flight.passed:
        return _sim_result(flight, defects, metrics, flags)

    targets = _expect(_check_targets(reply, requirements, root, table), "targets")
    defects += targets.defects
    return _sim_result(targets, defects, metrics, flags)


# --------------------------------------------------------------------------- shadow flights

def _shadow_flight(pre: Preflight, requirements: Requirements, simulator: Any, table: Any) -> dict[str, Any]:
    """How far the design would get with each unknown motor replaced by the
    nearest real motor (motors.MotorTable.nearest_real).

    Returns {"substitutes", "score", "stage", "progress", "reason"} (reason: the
    shadow's first reason when it stops before targets, else None). progress is 0..1:
    (shadow score - floor of the limits stage) / (1 - that floor), and 0 when
    no substitute can be chosen. The shadow's own score never becomes the
    answer's score; it only sets part of the motor-stage credit.

    The substitutes prefer the maker the design names. Naming a real maker is
    one of stage 3's facts, so when that preference changes a substitute, the
    copy made without it is flown too and the better shadow counts: a true
    fact never lowers the score.
    """
    out: dict[str, Any] = {"substitutes": [], "score": None, "stage": None, "progress": 0.0, "reason": None}
    if pre.root is None:
        return out
    shadow_root, subs = _substitute_motors(pre.root, table)
    out["substitutes"] = subs
    if shadow_root is None:
        return out
    res = _shadow_result(shadow_root, requirements, simulator, table)
    plain_root, plain_subs = _substitute_motors(pre.root, table, same_maker=False)
    if plain_root is not None and [s.get("substitute") for s in plain_subs] != [s.get("substitute") for s in subs]:
        plain = _shadow_result(plain_root, requirements, simulator, table)
        if plain.score is not None and (res.score is None or plain.score > res.score):
            res = plain
            out["substitutes"] = plain_subs
    floor = ladder.stage("limits").floor
    out["score"] = res.score
    out["stage"] = res.stage
    out["reason"] = res.reasons[0] if res.stage != "targets" and res.reasons else None
    if res.score is not None:
        out["progress"] = ladder.clamp01((res.score - floor) / (1.0 - floor))
    return out


def _shadow_result(shadow_root: Node, requirements: Requirements, simulator: Any, table: Any) -> Result:
    """The design with its motors replaced, scored through stages 4-7."""
    sp = Preflight()
    _preflight_tree(sp, shadow_root, table)
    if sp.failed is not None:
        return _stopped_at(sp)
    return _run_simulator_stages(sp, requirements, simulator, table)


def _shadow_words(shadow: dict[str, Any]) -> Optional[str]:
    """One plain sentence about the shadow flight, for the reasons."""
    subs = [s for s in shadow.get("substitutes", []) if isinstance(s, dict)]
    if not subs:
        return None
    if any(s.get("substitute") is None for s in subs):
        return ("no real motor could stand in for the invented one, because its designation names no impulse "
                "class letter, so the rest of the design could not be tried")
    named = list(dict.fromkeys(f"'{str(s.get('written') or s.get('designation'))[:60]}' -> '{s['substitute']}'"
                               for s in subs))
    pairs = ", ".join(named[:MAX_SHADOW_SHOWN])
    if len(named) > MAX_SHADOW_SHOWN:
        pairs += f" and {len(named) - MAX_SHADOW_SHOWN} more"
    stage = shadow.get("stage")
    score = shadow.get("score")
    if stage == "targets":
        how = f"pass every safety check (score {score:.2f})"
    elif isinstance(score, float):
        how = f"stop at the {stage} stage (score {score:.2f})"
        why = shadow.get("reason")
        if isinstance(why, str) and why:
            how += f", because {why if len(why) <= MAX_SHADOW_REASON_CHARS else why[:MAX_SHADOW_REASON_CHARS - 3] + '...'}"
    else:
        how = "not be scored"
    return (f"with the nearest real motor of its class that fits its mount in its place ({pairs}) "
            f"the same rocket would {how}")


def _with_shadow(result: Result, pre: Preflight, requirements: Requirements, simulator: Any,
                 table: Any) -> Result:
    """Motor-stage result with the shadow-flight share of the credit added."""
    facts = result.credit
    shadow = _shadow_flight(pre, requirements, simulator, table)
    credit = ladder.clamp01(ladder.MOTOR_FACTS_SHARE * facts + ladder.MOTOR_SHADOW_SHARE * shadow["progress"])
    result.credit = credit
    result.score = ladder.stage_score("motor", credit, len(result.defects))
    words = _shadow_words(shadow)
    if words:
        result.reasons.append(words)
    result.flags["motor_facts_credit"] = facts
    result.flags["shadow"] = shadow
    return result


# --------------------------------------------------------------------------- score

def score(answer_text: str, requirements: Requirements, truncated: bool = False,
          simulator: Any = None, *, motor_table: Any = None,
          tracker: Optional[ErrorTracker] = None) -> Result:
    """Score one answer from 0 to 1 (see DESIGN.md).

    A design that fails stage k of 1-4 scores inside that stage's band. One
    that passes all four is written as an OpenRocket file and flown by
    `simulator` (anything with Simulator.run's signature: a sim.Simulator or a
    sim.SimPool); without one the shared default_simulator() is used, started
    the first time a design needs it. A design with an unknown motor also gets
    a shadow flight. An unexpected error inside a check returns score=None
    with flags["quarantined"] = True; too many of them raise RewardSetupError.
    A broken machine (no Java, wrong jar, failed self-test) always raises
    RewardSetupError.
    """
    tracker = tracker if tracker is not None else default_tracker()
    if simulator is not None and not callable(getattr(simulator, "run", None)):
        raise RewardSetupError(f"the simulator must have a run() method like sim.Simulator or sim.SimPool, "
                               f"got {type(simulator).__name__}")
    pre = Preflight()
    try:
        _run_preflight(pre, answer_text, truncated, motor_table)
        if pre.failed is not None:
            result = _stopped_at(pre)
            if pre.failed.stage == "motor":
                table = motor_table if motor_table is not None else default_motor_table()
                sim = simulator if simulator is not None else _LazySimulator()
                result = _with_shadow(result, pre, requirements, sim, table)
        else:
            table = motor_table if motor_table is not None else default_motor_table()
            sim = simulator if simulator is not None else default_simulator()
            result = _run_simulator_stages(pre, requirements, sim, table)
    except RewardSetupError:
        raise
    except Exception as exc:
        path = _quarantine(answer_text, truncated, requirements, traceback.format_exc())
        result = Result(
            score=None,
            stage="dropped",
            stages_passed=sum(1 for c in pre.checks if c.passed),
            credit=0.0,
            reasons=[f"the reward hit an unexpected error ({type(exc).__name__}: {str(exc)[:200]}); "
                     f"the answer was saved to {path} and is left out of training"],
            defects=pre.defects(),
            flags={"quarantined": True, "quarantine_file": str(path),
                   "error": f"{type(exc).__name__}: {str(exc)[:200]}"},
        )
        if truncated:
            result.flags["truncated"] = True
        tracker.record(True)
        return result
    tracker.record(False)
    if truncated:
        result.flags["truncated"] = True
    if pre.notes:
        result.flags.setdefault("clean_notes", list(pre.notes))
    return result


class _LazySimulator:
    """Stands for the default simulator and starts it only when a design is
    really flown (a shadow flight needs no simulator when no substitute can
    be chosen)."""

    def run(self, *args: Any, **kwargs: Any) -> Any:
        return default_simulator().run(*args, **kwargs)


def score_many(answers: Sequence[str], requirements_list: Sequence[Requirements],
               truncated: Optional[Sequence[bool]] = None, simulator: Any = None, *,
               motor_table: Any = None, tracker: Optional[ErrorTracker] = None,
               threads: Optional[int] = None) -> list[Result]:
    """Score many answers in parallel threads; the results keep the input order.

    `requirements_list[i]` and `truncated[i]` (default all False) belong to
    `answers[i]`. `simulator` is shared by every thread (a SimPool flies one
    design per helper at a time; default: default_simulator()). `threads`
    defaults to twice the pool size, so the Python checks of one answer
    overlap the flights of others. Each answer is scored exactly as
    `score` would; a RewardSetupError from any answer is raised after the
    others finish.
    """
    n = len(answers)
    if len(requirements_list) != n:
        raise ValueError(f"score_many got {n} answers but {len(requirements_list)} requirements")
    flags = [False] * n if truncated is None else [bool(t) for t in truncated]
    if len(flags) != n:
        raise ValueError(f"score_many got {n} answers but {len(flags)} truncated flags")
    if n == 0:
        return []
    if threads is None:
        size = getattr(simulator, "size", None) if simulator is not None else default_workers()
        threads = 2 * size if isinstance(size, int) and size > 0 else 2
    threads = max(1, min(int(threads), n))

    def one(i: int) -> Result:
        return score(answers[i], requirements_list[i], flags[i], simulator,
                     motor_table=motor_table, tracker=tracker)

    with concurrent.futures.ThreadPoolExecutor(max_workers=threads, thread_name_prefix="rocket-score") as ex:
        futures = [ex.submit(one, i) for i in range(n)]
        concurrent.futures.wait(futures)
    for f in futures:
        exc = f.exception()
        if exc is not None:
            raise exc
    return [f.result() for f in futures]
