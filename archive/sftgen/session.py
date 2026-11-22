"""Trace-generation harness: the generator writes reasoning, the harness runs the tools.

A generator (model or person) works one prompt at a time and only ever sees the
system prompt, the user prompt and the tool schemas, never the row's targets.
Every tool call is executed here for real and its output is recorded verbatim,
so no tool number in a trace can be typed in by hand.

    python -m sftgen.session start  PROMPT_ID [--generator NAME] [--draft N]
    python -m sftgen.session step   SESSION_ID --reasoning FILE --call NAME ARGS [--call NAME ARGS ...]
    python -m sftgen.session final  SESSION_ID --reasoning FILE --content FILE [--dry-run]
    python -m sftgen.session show   SESSION_ID
    python -m sftgen.session abandon SESSION_ID --reason TEXT

ARGS is a JSON object or @path/to/args.json. Sessions live in sftgen/out/sessions/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

from . import contract

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
SESSIONS = OUT / "sessions"
PROMPTS_FILE = OUT / "prompts_v1.jsonl"
PROMPT_VERSION = "prompts_v1"
FORMAT_CODES = {"structure", "steps", "leakage", "precision", "provenance", "math", "design", "reflection"}


def _load_prompts() -> dict[str, dict]:
    rows = {}
    with open(PROMPTS_FILE, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                r = json.loads(line)
                rows[r["prompt_id"]] = r
    return rows


def seed_for(prompt_id: str, draft: int) -> int:
    h = hashlib.sha256(f"{prompt_id}#{draft}".encode()).hexdigest()
    return int(h[:8], 16) % 1_000_000


def _path(sid: str) -> Path:
    return SESSIONS / f"{sid}.json"


def _load(sid: str) -> dict:
    p = _path(sid)
    if not p.exists():
        sys.exit(f"no such session {sid}")
    return json.loads(p.read_text(encoding="utf-8"))


def _save(s: dict) -> None:
    SESSIONS.mkdir(parents=True, exist_ok=True)
    tmp = _path(s["session_id"]).with_suffix(".tmp")
    tmp.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(_path(s["session_id"]))


def _read_text(arg: str) -> str:
    text = Path(arg).read_text(encoding="utf-8") if arg != "-" else sys.stdin.read()
    text = text.strip("\n")
    if not text.strip():
        sys.exit("empty text")
    return text


def _read_args(arg: str) -> dict:
    raw = Path(arg[1:]).read_text(encoding="utf-8") if arg.startswith("@") else arg
    try:
        val = json.loads(raw)
    except json.JSONDecodeError as e:
        sys.exit(f"tool arguments are not valid JSON: {e}")
    if not isinstance(val, dict):
        sys.exit("tool arguments must be a JSON object")
    return val


def _visible_prompt(p: dict) -> str:
    return p["user_text"]


def cmd_start(a) -> None:
    prompts = _load_prompts()
    if a.prompt_id not in prompts:
        sys.exit(f"unknown prompt {a.prompt_id}")
    p = prompts[a.prompt_id]
    if p.get("needs_design") and "{DESIGN_JSON}" in p["user_text"]:
        sys.exit(f"prompt {a.prompt_id} still has a {{DESIGN_JSON}} placeholder; fill it first")
    sid = f"{a.prompt_id}__d{a.draft}"
    if _path(sid).exists() and not a.force:
        sys.exit(f"session {sid} exists (use --force to overwrite or another --draft)")
    seed = seed_for(a.prompt_id, a.draft)
    base_cond = {**contract.DEFAULT_SIM_CONDITIONS, **(p.get("sim_conditions") or {}), "seed": seed}
    s = {
        "session_id": sid,
        "prompt_id": a.prompt_id,
        "draft": a.draft,
        "generator": {"name": a.generator, "prompt_version": PROMPT_VERSION, "contract": contract.CONTRACT_VERSION},
        "sim_conditions": base_cond,
        "status": "open",
        "started_at": time.time(),
        "messages": [
            {"role": "system", "content": contract.SYSTEM_PROMPT},
            {"role": "user", "content": _visible_prompt(p)},
        ],
        "call_counter": 0,
    }
    _save(s)
    print(json.dumps({
        "session_id": sid,
        "system": contract.SYSTEM_PROMPT,
        "user": _visible_prompt(p),
        "tools": [t["function"]["name"] for t in contract.TOOLS],
        "site_defaults": {k: v for k, v in contract.DEFAULT_SIM_CONDITIONS.items() if k != "seed"},
    }, ensure_ascii=False, indent=1))


def _tool_base_conditions(s: dict) -> dict:
    """Tools see only site defaults; conditions from the prompt must be passed by the caller."""
    c = dict(contract.DEFAULT_SIM_CONDITIONS)
    c.pop("seed", None)
    return c


def cmd_step(a) -> None:
    from . import tools

    s = _load(a.session_id)
    if s["status"] != "open":
        sys.exit(f"session is {s['status']}")
    reasoning = _read_text(a.reasoning)
    if not a.call:
        sys.exit("a step needs at least one --call")
    calls = []
    for name, raw in a.call:
        if name not in contract.TOOL_NAMES:
            sys.exit(f"unknown tool {name}")
        s["call_counter"] += 1
        calls.append({"id": f"call_{s['call_counter']}", "type": "function",
                      "function": {"name": name, "arguments": _read_args(raw)}})
    s["messages"].append({"role": "assistant", "reasoning_content": reasoning, "content": "", "tool_calls": calls})
    outputs = []
    for c in calls:
        out = tools.call(c["function"]["name"], c["function"]["arguments"],
                         seed=s["sim_conditions"]["seed"], base_conditions=_tool_base_conditions(s))
        content = tools.dumps(out)
        s["messages"].append({"role": "tool", "tool_call_id": c["id"], "name": c["function"]["name"], "content": content})
        outputs.append({"id": c["id"], "name": c["function"]["name"], "output": out})
    _save(s)
    print(json.dumps(outputs, ensure_ascii=False, indent=1))


def cmd_final(a) -> None:
    s = _load(a.session_id)
    if s["status"] != "open":
        sys.exit(f"session is {s['status']}")
    s["messages"].append({
        "role": "assistant",
        "reasoning_content": _read_text(a.reasoning),
        "content": _read_text(a.content),
    })
    if not a.dry_run:
        s["status"] = "final"
        s["finished_at"] = time.time()
        _save(s)
    report = {"session_id": s["session_id"], "status": "dry-run (nothing saved)" if a.dry_run else "final"}
    try:
        from . import lint

        # Targets stay hidden from the generator, so only format/honesty checks are reported here;
        # whether each fix was justified is judged later by the checker, which has the targets.
        issues = lint.lint_row({"messages": s["messages"], "tools": contract.TOOLS, "targets": {}})
        report["format_issues"] = [
            {"code": i.code, "severity": i.severity, "message": i.message, "msg_index": i.msg_index}
            for i in issues if i.code in FORMAT_CODES
        ]
    except Exception as e:  # linter not available yet
        report["format_issues"] = f"linter unavailable: {e}"
    print(json.dumps(report, ensure_ascii=False, indent=1))


def cmd_show(a) -> None:
    print(json.dumps(_load(a.session_id), ensure_ascii=False, indent=1))


def cmd_abandon(a) -> None:
    s = _load(a.session_id)
    s["status"] = "abandoned"
    s["abandon_reason"] = a.reason
    _save(s)
    print(json.dumps({"session_id": s["session_id"], "status": "abandoned"}))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="sftgen.session")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("start"); p.add_argument("prompt_id"); p.add_argument("--generator", default="unknown")
    p.add_argument("--draft", type=int, default=1); p.add_argument("--force", action="store_true"); p.set_defaults(fn=cmd_start)
    p = sub.add_parser("step"); p.add_argument("session_id"); p.add_argument("--reasoning", required=True)
    p.add_argument("--call", nargs=2, action="append", metavar=("NAME", "ARGS")); p.set_defaults(fn=cmd_step)
    p = sub.add_parser("final"); p.add_argument("session_id"); p.add_argument("--reasoning", required=True)
    p.add_argument("--content", required=True); p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_final)
    p = sub.add_parser("show"); p.add_argument("session_id"); p.set_defaults(fn=cmd_show)
    p = sub.add_parser("abandon"); p.add_argument("session_id"); p.add_argument("--reason", required=True); p.set_defaults(fn=cmd_abandon)
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
