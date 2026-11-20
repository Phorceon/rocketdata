"""Command line for the reward: python -m rocket_reward <command> ...

Commands:

  check
      Find Java and the OpenRocket jar, compile the helper, start it and fly
      the self-test rocket. Prints what it found, or what to fix.

  fetch-jar [--url URL] [--dest FILE]
      Download OpenRocket-24.12.jar from the official OpenRocket GitHub
      release into rocket_reward/lib/ (the place the reward looks when
      ROCKET_REWARD_JAR is not set). The file is kept only when its SHA-256 is
      the pinned one (sim.OPENROCKET_JAR_SHA256); anything else is deleted and
      refused. --url replaces the address (a mirror or a file:// URL; the
      SHA-256 check still applies), --dest the file to write.

  score ANSWERS.jsonl[.gz] [REQUIREMENTS] [--json] [--workers N]
      Score every answer through the whole ladder and print one line per
      answer (stage, score, first reason) and the count per stage. Each
      answer is matched with its requirements by its "id": REQUIREMENTS is a
      .json file holding {id: record}, a list of records, or one record for
      every answer, or a .jsonl[.gz] file of rows with "id" and
      "requirements" (like prompts/rl_prompts_v1.jsonl) or of bare records.
      Without REQUIREMENTS every answer row must carry its own
      "requirements". --workers sets the number of OpenRocket helpers
      (default 4); none is started when no answer gets past stage 4.

  preflight FILE.jsonl[.gz] [FILE ...] [--json]
      Run stages 1-4 (format, parts, motor, limits) on every answer in the
      files and print how many answers stop at each stage and how the scores
      spread. Needs no Java. Answers that pass all four stages have no score
      yet: the simulator stages (5-7) decide it.

In "score" and "preflight" a row's answer is read from its "content" field,
else "answer", else the last assistant message in "messages", and a row with
"truncated": true counts as cut off.

Output is UTF-8 whatever the console's own encoding is, because reasons can
quote text the model wrote (a motor id with any character in it).

Exit code: 0 when the command did its job, 1 when fetch-jar could not get the
right file, 2 for a usage or file problem, 3 when the reward itself is broken
or not set up (RewardSetupError, for example no Java or a missing motor table).
"""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import os
import statistics
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Iterator, Optional, Sequence, TextIO

from . import ladder
from .errors import RewardSetupError

# fetch-jar: the pinned jar is about 83 MB; a reply larger than this is not it.
FETCH_MAX_BYTES = 200 * 1024 * 1024
FETCH_TIMEOUT_S = 60.0
FETCH_BLOCK_BYTES = 1 << 20
DEFAULT_SCORE_WORKERS = 4
REASON_CHARS = 110       # first reason shown per answer in the score table
ID_CHARS = 30

PASSED = "passed"          # the row went through all four preflight stages
ERROR = "error"            # a check crashed on the row (a bug in the reward)
NO_ANSWER = "no_answer"    # the row has no answer text at all
PREFLIGHT_STAGES = ("format", "parts", "motor", "limits")
ROW_ORDER = PREFLIGHT_STAGES + (PASSED, ERROR, NO_ANSWER)


# --------------------------------------------------------------------------- reading rows

def answer_of(row: Any) -> Optional[str]:
    """The answer text of one row: "content", else "answer", else the last
    assistant message in "messages". None when the row has none of them."""
    if not isinstance(row, dict):
        return None
    for key in ("content", "answer"):
        if isinstance(row.get(key), str):
            return row[key]
    messages = row.get("messages")
    if isinstance(messages, list):
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "assistant" and isinstance(msg.get("content"), str):
                return msg["content"]
    return None


def read_numbered_rows(path: Path) -> Iterator[tuple[int, Any]]:
    """Yield (line number counted from 0, row) for every non-empty line of a
    .jsonl or .jsonl.gz file. Blank lines are skipped but still counted, so
    the number is always the real line. A line that is not JSON is yielded
    with row None, so it is counted, not lost."""
    opener = gzip.open if path.name.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as fh:  # type: ignore[operator]
        for n, line in enumerate(fh):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except ValueError:
                row = None
            yield n, row


def read_rows(path: Path) -> Iterator[tuple[str, Any]]:
    """Yield (row id, row) for every non-empty line of a .jsonl or .jsonl.gz file.

    The id is the row's "id" field when it has one, else "<file name>:<line>".
    A line that is not JSON is yielded as (id, None) so it is counted, not lost.
    """
    for n, row in read_numbered_rows(path):
        rid = row.get("id") if isinstance(row, dict) and isinstance(row.get("id"), str) else None
        yield (rid or f"{path.name}:{n}"), row


def unique_key(key: str, taken: Any) -> str:
    """`key`, or `key#2`, `key#3` ... when it is already in `taken`, so two
    rows with the same name (the same id in two files) stay two rows."""
    out, n = key, 2
    while out in taken:
        out, n = f"{key}#{n}", n + 1
    return out


def use_utf8_output() -> None:
    """Write stdout and stderr as UTF-8. On Windows they default to the
    console's code page (often cp1252), and printing a reason that quotes a
    model-written character outside it would crash the whole run."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="backslashreplace")
            except (ValueError, OSError):
                pass


# --------------------------------------------------------------------------- running

def run_row(row: Any, motor_table: Any = None) -> dict[str, Any]:
    """Run stages 1-4 on one row and return a small summary dict:
    {"stage", "score", "credit", "reasons"}. "score" is None for a row that
    passed all four stages (its score needs the simulator) and for a crash.
    A RewardSetupError (broken installation) is not caught."""
    from .scoring import preflight, preflight_result

    text = answer_of(row)
    if text is None:
        return {"stage": NO_ANSWER, "score": None, "credit": None,
                "reasons": ["the row has no \"content\", \"answer\" or assistant message"]}
    truncated = bool(row.get("truncated")) if isinstance(row, dict) else False
    try:
        pre = preflight(text, truncated=truncated, motor_table=motor_table)
    except RewardSetupError:
        raise
    except Exception as exc:  # a bug in a check: count it, keep going
        return {"stage": ERROR, "score": None, "credit": None,
                "reasons": [f"{type(exc).__name__}: {str(exc)[:200]}"]}
    result = preflight_result(pre)
    if result is None:
        return {"stage": PASSED, "score": None, "credit": 1.0, "reasons": [],
                "defects": pre.defects()}
    return {"stage": result.stage, "score": result.score, "credit": round(result.credit, 6),
            "reasons": list(result.reasons), "defects": list(result.defects)}


def summarize(results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Counts per stage and the spread of the scores of the failing answers."""
    counts = collections.Counter(r["stage"] for r in results.values())
    scores = [r["score"] for r in results.values() if r["score"] is not None]
    ties = collections.Counter(round(s, 4) for s in scores)
    spread: dict[str, Any] = {"scored": len(scores), "distinct": len(ties)}
    if scores:
        top_score, top_count = max(ties.items(), key=lambda kv: (kv[1], -kv[0]))
        spread.update(min=min(scores), median=statistics.median(scores), max=max(scores),
                      largest_tie={"score": top_score, "answers": top_count},
                      tied_answers=sum(c for c in ties.values() if c > 1))
    return {"answers": len(results),
            "stages": {k: counts.get(k, 0) for k in ROW_ORDER if counts.get(k, 0) or k in PREFLIGHT_STAGES + (PASSED,)},
            "score_spread": spread}


def _table(summary: dict[str, Any]) -> str:
    n = max(1, summary["answers"])
    lines = [f"{'stops at':<12}{'answers':>8}{'share':>8}  score band"]
    for key, count in summary["stages"].items():
        if key in ladder.STAGE_KEYS:
            s = ladder.stage(key)
            band = f"{s.floor:.2f}-{s.top:.2f}"
        elif key == PASSED:
            band = "needs the simulator (0.40 or more)"
        else:
            band = "-"
        lines.append(f"{key:<12}{count:>8}{count / n:>8.0%}  {band}")
    lines.append(f"{'total':<12}{summary['answers']:>8}")
    sp = summary["score_spread"]
    lines.append("")
    if sp["scored"]:
        tie = sp["largest_tie"]
        lines.append(f"scores of the {sp['scored']} answers that stop in stages 1-4: "
                     f"{sp['distinct']} distinct, min {sp['min']:.4f}, median {sp['median']:.4f}, "
                     f"max {sp['max']:.4f}")
        lines.append(f"largest group of equal scores: {tie['answers']} answers at {tie['score']:.4f}; "
                     f"{sp['tied_answers']} answers share their score with another")
    else:
        lines.append("no answer stops in stages 1-4")
    return "\n".join(lines)


def cmd_preflight(files: Sequence[str], as_json: bool, out: Optional[TextIO] = None) -> int:
    """Run stages 1-4 on every row of `files` and write the summary (a table,
    or JSON with every row) to `out` (standard output when None). Returns the
    exit code."""
    out = out if out is not None else sys.stdout
    results: dict[str, dict[str, Any]] = {}
    for name in files:
        path = Path(name)
        if not path.is_file():
            print(f"error: {name} is not a file", file=sys.stderr)
            return 2
        for rid, row in read_rows(path):
            results[unique_key(rid, results)] = run_row(row)
    summary = summarize(results)
    if as_json:
        json.dump({"summary": summary, "rows": results}, out, ensure_ascii=False, indent=1)
        out.write("\n")
    else:
        out.write(_table(summary) + "\n")
    return 0


# --------------------------------------------------------------------------- check

def cmd_check(out: Optional[TextIO] = None, command: Optional[Sequence[str]] = None) -> int:
    """Run sim.check_setup and print what it found. A RewardSetupError is
    printed with what to fix (exit code 3). `command` replaces the real
    helper (tests use the fake one)."""
    from . import sim

    out = out if out is not None else sys.stdout
    out.write("checking Java, the OpenRocket jar and the simulator helper (this can take a minute)...\n")
    try:
        facts = sim.check_setup(command=command)
    except RewardSetupError as exc:
        out.write(f"NOT READY: {exc}\n")
        out.write("Fix that, then run `python -m rocket_reward check` again. README.md, section "
                  "\"Set-up\", lists the steps.\n")
        return 3
    canary = facts.get("canary") or {}
    lines = []
    if "java" in facts:
        lines += [f"Java {facts['java']} at {facts['java_path']} (found through {facts['java_found_by']})",
                  f"OpenRocket jar: {facts['jar']} (SHA-256 matches the pinned {sim.OPENROCKET_VERSION} file)"]
    lines += [f"helper version {facts.get('helper')} running OpenRocket {facts.get('openrocket')} "
              f"on Java {facts.get('helper_java')}; started in {facts.get('boot_s')} s",
              "self-test rocket flew as expected: "
              + ", ".join(f"{k} {v:.4g}" if ladder.is_number(v) else f"{k} {v}" for k, v in canary.items()),
              f"helper log: {facts.get('log')}",
              f"READY ({facts.get('total_s')} s in all)"]
    out.write("\n".join(lines) + "\n")
    return 0


# --------------------------------------------------------------------------- fetch-jar

def fetch_jar(url: str, dest: Path, sha256: str, out: TextIO, max_bytes: int = FETCH_MAX_BYTES) -> int:
    """Download `url` to `dest`, keeping it only when its SHA-256 is `sha256`.

    The file is written next to `dest` under a temporary name and moved into
    place only after the check, so a failed or refused download never leaves
    a half file where the reward looks. Returns the exit code (0 done or
    already there, 1 refused or failed)."""
    from .sim import file_sha256

    if dest.is_file() and file_sha256(dest) == sha256:
        out.write(f"{dest} is already the right file (SHA-256 {sha256}); nothing to do\n")
        return 0
    if not url.lower().startswith(("https://", "http://", "file:")):
        out.write(f"refused: {url!r} is not an https://, http:// or file: address\n")
        return 1
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.write(f"downloading {url}\n")
    fd, tmp_name = tempfile.mkstemp(prefix=dest.name + ".", suffix=".part", dir=dest.parent)
    tmp = Path(tmp_name)
    digest, size = hashlib.sha256(), 0
    try:
        with os.fdopen(fd, "wb") as fh:
            request = urllib.request.Request(url, headers={"User-Agent": "rocket_reward-fetch-jar"})
            with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT_S) as reply:
                while True:
                    block = reply.read(FETCH_BLOCK_BYTES)
                    if not block:
                        break
                    size += len(block)
                    if size > max_bytes:
                        out.write(f"refused: the download is larger than {max_bytes // (1024 * 1024)} MB, "
                                  f"so it is not the OpenRocket jar\n")
                        return 1
                    digest.update(block)
                    fh.write(block)
        actual = digest.hexdigest()
        if actual != sha256:
            out.write(f"refused: the downloaded file ({size} bytes) has SHA-256 {actual}, but the pinned "
                      f"jar has {sha256}. A partial download, an error page or another version gives this; "
                      f"nothing was kept\n")
            return 1
        os.replace(tmp, dest)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        out.write(f"download failed: {exc}. Check the internet connection (or the address) and try again, "
                  f"or download the file by hand and set ROCKET_REWARD_JAR to it\n")
        return 1
    finally:
        if tmp.exists():
            tmp.unlink()
    out.write(f"saved {dest} ({size} bytes, SHA-256 checked). Run `python -m rocket_reward check` next.\n")
    return 0


def cmd_fetch_jar(url: Optional[str], dest: Optional[str], out: Optional[TextIO] = None) -> int:
    """fetch-jar with the pinned address, place and SHA-256 from sim.py unless replaced."""
    from . import sim

    out = out if out is not None else sys.stdout
    return fetch_jar(url or sim.OPENROCKET_JAR_URL, Path(dest) if dest else sim.DEFAULT_JAR_PATH,
                     sim.OPENROCKET_JAR_SHA256, out)


# --------------------------------------------------------------------------- score

def load_requirements_file(path: Path) -> tuple[dict[str, Any], Optional[Any]]:
    """Read a requirements file: ({id: record}, the one record for every answer or None).

    .json: {id: record}, a list of records (keyed by their "id"), or a single
    record (it has "apogee_m"), which then applies to every answer.
    .jsonl / .jsonl.gz: one row per line, either {"id", "requirements", ...}
    or a bare record. Raises ValueError with a plain message on a bad file."""
    if path.name.endswith((".jsonl", ".jsonl.gz")):
        by_id: dict[str, Any] = {}
        for n, row in read_numbered_rows(path):
            if not isinstance(row, dict):
                raise ValueError(f"{path.name} line {n + 1} is not a JSON object")
            rec = row.get("requirements", row)
            rid = row.get("id", rec.get("id") if isinstance(rec, dict) else None)
            if not isinstance(rid, str):
                raise ValueError(f"{path.name} line {n + 1} has no text \"id\"")
            by_id[rid] = rec
        return by_id, None
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict) and "apogee_m" in data:
        return {}, data
    if isinstance(data, list):
        if not all(isinstance(r, dict) and isinstance(r.get("id"), str) for r in data):
            raise ValueError(f"{path.name} is a list, so every entry must be a record with a text \"id\"")
        return {r["id"]: r for r in data}, None
    if isinstance(data, dict):
        return {str(k): v for k, v in data.items()}, None
    raise ValueError(f"{path.name} must hold a record, a list of records or {{id: record}}")


class _PoolOnDemand:
    """A SimPool of `size` helpers that starts only when a design must fly,
    so scoring answers that all stop in stages 1-4 needs no Java."""

    def __init__(self, size: int) -> None:
        self.size = size
        self._pool: Any = None
        self._lock = threading.Lock()

    def run(self, *args: Any, **kwargs: Any) -> Any:
        with self._lock:
            if self._pool is None:
                from .sim import SimPool
                self._pool = SimPool(self.size)
        return self._pool.run(*args, **kwargs)

    def close(self) -> None:
        with self._lock:
            pool, self._pool = self._pool, None
        if pool is not None:
            pool.close()


def _one_line(text: str, n: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[:n - 3] + "..."


def _score_table(rows: dict[str, dict[str, Any]]) -> str:
    lines = [f"{'answer':<{ID_CHARS}} {'stage':<8} {'score':>7}  first reason"]
    for rid, r in rows.items():
        sc = "-" if r["score"] is None else f"{r['score']:.4f}"
        first = (r["reasons"] or r["defects"] or [""])[0]
        lines.append(f"{_one_line(rid, ID_CHARS):<{ID_CHARS}} {r['stage']:<8} {sc:>7}  {_one_line(first, REASON_CHARS)}")
    counts = collections.Counter(r["stage"] for r in rows.values())
    lines += ["", f"{'stops at':<10}{'answers':>8}  score band"]
    for key in ladder.STAGE_KEYS + ("dropped",):
        if counts.get(key):
            band = "left out of training (reward error)" if key == "dropped" else \
                f"{ladder.stage(key).floor:.2f}-{ladder.stage(key).top:.2f}"
            lines.append(f"{key:<10}{counts[key]:>8}  {band}")
    scores = [r["score"] for r in rows.values() if r["score"] is not None]
    lines.append(f"{'total':<10}{len(rows):>8}")
    if scores:
        lines.append(f"scores: min {min(scores):.4f}, median {statistics.median(scores):.4f}, "
                     f"max {max(scores):.4f}, mean {statistics.fmean(scores):.4f}")
    return "\n".join(lines)


def cmd_score(answers_file: str, requirements_file: Optional[str], as_json: bool, workers: int,
              out: Optional[TextIO] = None, simulator: Any = None) -> int:
    """Score every answer row of `answers_file` with its requirements and
    write a table (or JSON) to `out`. `simulator` replaces the on-demand pool
    (tests pass a fake). Returns the exit code."""
    from .records import Requirements
    from .scoring import score_many

    out = out if out is not None else sys.stdout
    path = Path(answers_file)
    if not path.is_file():
        print(f"error: {answers_file} is not a file", file=sys.stderr)
        return 2
    if workers < 1:
        print("error: --workers must be 1 or more", file=sys.stderr)
        return 2
    by_id: dict[str, Any] = {}
    every: Optional[Any] = None
    if requirements_file is not None:
        if not Path(requirements_file).is_file():
            print(f"error: {requirements_file} is not a file", file=sys.stderr)
            return 2
        try:
            by_id, every = load_requirements_file(Path(requirements_file))
        except ValueError as exc:
            print(f"error: could not read the requirements: {exc}", file=sys.stderr)
            return 2
    ids, texts, reqs, cut = [], [], [], []
    problems = []
    for rid, row in read_rows(path):
        rid = unique_key(rid, set(ids))
        text = answer_of(row)
        own = row.get("requirements") if isinstance(row, dict) else None
        rec = own if own is not None else (every if every is not None else by_id.get(rid))
        if text is None:
            problems.append(f"{rid}: the row has no \"content\", \"answer\" or assistant message")
            continue
        if rec is None:
            problems.append(f"{rid}: no requirements with this id" + (
                "" if requirements_file else " (give a requirements file, or a \"requirements\" field in the row)"))
            continue
        try:
            reqs.append(Requirements.from_dict(rec))
        except ValueError as exc:
            problems.append(f"{rid}: bad requirements: {exc}")
            continue
        ids.append(rid)
        texts.append(text)
        cut.append(bool(row.get("truncated")) if isinstance(row, dict) else False)
    if problems:
        print(f"error: {len(problems)} answer row(s) cannot be scored; nothing was scored:", file=sys.stderr)
        for p in problems[:20]:
            print(f"  {p}", file=sys.stderr)
        if len(problems) > 20:
            print(f"  ... and {len(problems) - 20} more", file=sys.stderr)
        if by_id and not ids:
            sample = ", ".join(repr(k) for k in list(by_id)[:2])
            print(f"  no answer id matches the {len(by_id)} ids in {requirements_file} (they look like "
                  f"{sample}): the answers file and the requirements file must use the same ids",
                  file=sys.stderr)
        return 2
    pool = simulator if simulator is not None else _PoolOnDemand(workers)
    try:
        results = score_many(texts, reqs, cut, simulator=pool, threads=2 * workers)
    finally:
        if simulator is None:
            pool.close()
    rows = {rid: {"stage": r.stage, "score": r.score, "stages_passed": r.stages_passed,
                  "reasons": list(r.reasons), "defects": list(r.defects), "metrics": r.metrics,
                  "shadow": r.flags.get("shadow"), "quarantined": bool(r.flags.get("quarantined"))}
            for rid, r in zip(ids, results)}
    if as_json:
        counts = collections.Counter(r["stage"] for r in rows.values())
        json.dump({"summary": {"answers": len(rows), "stages": {k: counts[k] for k in ladder.STAGE_KEYS
                                                                + ("dropped",) if counts.get(k)}},
                   "rows": rows}, out, ensure_ascii=False, indent=1, default=str)
        out.write("\n")
    else:
        out.write(_score_table(rows) + "\n")
    return 0


# --------------------------------------------------------------------------- main

def main(argv: Optional[Sequence[str]] = None) -> int:
    """Entry point for `python -m rocket_reward`."""
    parser = argparse.ArgumentParser(prog="python -m rocket_reward",
                                     description="Score rocket-design answers (see README.md and DESIGN.md).")
    sub = parser.add_subparsers(dest="command", required=True)
    words = "check that Java, the OpenRocket jar and the simulator work"
    sub.add_parser("check", help=words, description=words + "; ends with READY or NOT READY and what to fix")
    words = "download the pinned OpenRocket 24.12 jar into rocket_reward/lib/"
    f = sub.add_parser("fetch-jar", help=words, description=words + " and check its SHA-256")
    f.add_argument("--url", help="download from this address instead of the official release "
                                 "(the SHA-256 check still applies)")
    f.add_argument("--dest", help="write the jar here instead of rocket_reward/lib/OpenRocket-24.12.jar")
    words = "score a file of answers through the whole ladder"
    s = sub.add_parser("score", help=words, description=words + " (stages 5-7 need Java; see README.md)")
    s.add_argument("answers", help="a .jsonl or .jsonl.gz file of answer rows with an \"id\"")
    s.add_argument("requirements", nargs="?",
                   help="requirements: .json ({id: record}, a list, or one record for all) or .jsonl rows "
                        "with \"id\" and \"requirements\"; leave out when every row has its own")
    s.add_argument("--json", action="store_true", help="print machine-readable JSON instead of a table")
    s.add_argument("--workers", type=int, default=DEFAULT_SCORE_WORKERS,
                   help=f"OpenRocket helpers to run side by side (default {DEFAULT_SCORE_WORKERS})")
    words = "run stages 1-4 (no Java) on .jsonl or .jsonl.gz files of answers"
    p = sub.add_parser("preflight", help=words, description=words)
    p.add_argument("files", nargs="+", help="rows with a \"content\" or \"answer\" field, "
                                            "or a \"messages\" list whose last assistant message is the answer")
    p.add_argument("--json", action="store_true", help="print machine-readable JSON instead of a table")
    args = parser.parse_args(argv)
    use_utf8_output()
    try:
        if args.command == "check":
            return cmd_check()
        if args.command == "fetch-jar":
            return cmd_fetch_jar(args.url, args.dest)
        if args.command == "score":
            return cmd_score(args.answers, args.requirements, args.json, args.workers)
        if args.command == "preflight":
            return cmd_preflight(args.files, args.json)
    except RewardSetupError as exc:
        print(f"setup error: {exc}", file=sys.stderr)
        print("run `python -m rocket_reward check` to see what is missing", file=sys.stderr)
        return 3
    except (OSError, EOFError) as exc:
        print(f"error: could not read the input ({exc})", file=sys.stderr)
        return 2
    return 2
