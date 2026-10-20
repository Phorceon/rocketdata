"""Score a GGUF model on the held-out SFT test prompts (data/sft_test.jsonl) with llama-server.

Checks format only: the repo has no simulator, so "does the rocket fly" is not tested. Per answer
(the <design> block is looked for in the final answer only, not in the reasoning):
  design_found   <design>...</design> present        json_ok      the design JSON parses
  schema_ok      flight.motor + components, every component type is one seen in the data,
                 at least one nosecone and one bodytube        recovery     a parachute or streamer
  motor_known    every motor is in data/catalog.sqlite or the SFT data
  motor_match    when the prompt names a motor, the design uses it (a miss if there is no valid design)
  claim_vs_ask   when the prompt gives a target apogee, the "Simulated apogee" the model writes is within
                 10% of it. This is the model's own claim, not a simulation.
  truncated      hit --max-tokens before finishing        error       the request itself failed

Usage (Unsloth Studio's Python; llama-server ships with Studio):
    python sft\\eval_test.py --gguf C:\\ft\\agents-a1-rocket\\gguf\\<file>.gguf --label finetuned
    python sft\\eval_test.py --rescore C:\\ft\\agents-a1-rocket\\eval\\results_finetuned.json   (no GPU)
"""
import argparse
import importlib.util
import json
import os
import re
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data"
DEFAULT_SERVER = Path.home() / ".unsloth" / "llama.cpp" / "build" / "bin" / "Release" / "llama-server.exe"
NUM = r"([\d][\d,]*(?:\.\d+)?)"
KEYS = ["design_found", "json_ok", "schema_ok", "recovery", "motor_known", "motor_match", "claim_vs_ask",
        "truncated", "error"]


def num(s):
    return float(s.replace(",", ""))


def walk(components):
    """Yield every component dict; malformed entries yield a placeholder with type None."""
    for c in components if isinstance(components, list) else []:
        if not isinstance(c, dict):
            yield {"type": None}
            continue
        yield c
        yield from walk(c.get("contains"))


def reference_vocab():
    """Component types and motor names that appear in the SFT data, plus the motor catalog."""
    types, motors = set(), set()
    for name in ("sft_v0.jsonl", "sft_test.jsonl"):
        for line in open(DATA / name, encoding="utf-8"):
            ans = json.loads(line)["messages"][-1]["content"]
            d = json.loads(ans.split("<design>")[1].split("</design>")[0])
            m = d["flight"]["motor"]
            motors.update(m if isinstance(m, list) else [m])
            types.update(c["type"] for c in walk(d["components"]))
    with sqlite3.connect(DATA / "catalog.sqlite") as db:
        motors.update(r[0] for r in db.execute("select designation from motors"))
    return types, motors


def load_rows(path):
    """SFT rows carry "messages"; RL rows (data/splits/rl_heldout.jsonl) carry "prompt" with no answer."""
    rows = []
    for line in open(path, encoding="utf-8"):
        if line.strip():
            row = json.loads(line)
            row.setdefault("messages", row.get("prompt"))
            rows.append(row)
    return rows


def last_design(content):
    """Body of the last <design>...</design> block in the answer, or None."""
    i = content.rfind("<design>")
    j = content.find("</design>", i) if i != -1 else -1
    return content[i + len("<design>"):j].strip() if j != -1 else None


def score(row, reasoning, content, finish, types, motors):
    prompt = row["messages"][1]["content"]
    r = {"id": row["id"], "truncated": finish == "length", "error": finish == "error"}
    body = last_design(content)
    r["design_found"] = body is not None
    design = None
    if body is not None:
        try:
            design = json.loads(body)
        except json.JSONDecodeError:
            pass
    r["json_ok"] = isinstance(design, dict)
    r["schema_ok"] = r["recovery"] = r["motor_known"] = False
    asked = re.search(r"\bon (?:a|an|two|three) (.+?) motors?\b", prompt)
    r["asked_motor"] = asked.group(1) if asked else None
    r["motor_match"] = False if asked else None
    if r["json_ok"]:
        flight, comps = design.get("flight"), design.get("components")
        mot = flight.get("motor") if isinstance(flight, dict) else None
        mlist = [x for x in (mot if isinstance(mot, list) else [mot]) if isinstance(x, str) and x]
        ctypes = [c.get("type") for c in walk(comps)]
        r["schema_ok"] = bool(mlist) and bool(ctypes) and all(isinstance(t, str) and t in types for t in ctypes) \
            and "nosecone" in ctypes and "bodytube" in ctypes
        r["recovery"] = "parachute" in ctypes or "streamer" in ctypes
        r["motor_known"] = bool(mlist) and all(x in motors for x in mlist)
        if asked:
            # the prompt may give a label like "APEX | Cesaroni I216-CL(I)-14" for catalog motor I216-CL(I)
            r["motor_match"] = any(x == asked.group(1) or (x in motors and x in asked.group(1)) for x in mlist)
    ask = re.search(NUM + r"\s*m apogee", prompt) or re.search(NUM + r"\s*m\b(?!/)", prompt)
    claim = re.search(r"Simulated apogee:\s*" + NUM + r"\s*m", reasoning + "\n" + content)
    r["asked_apogee_m"] = num(ask.group(1)) if ask else None
    r["claimed_apogee_m"] = num(claim.group(1)) if claim else None
    r["claim_vs_ask"] = None
    if ask:
        r["claim_vs_ask"] = claim is not None and \
            abs(r["claimed_apogee_m"] - r["asked_apogee_m"]) <= 0.1 * r["asked_apogee_m"]
    return r


def summarize(results, meta):
    summary = dict(meta, n=len(results))
    for k in KEYS:
        vals = [r[k] for r in results if r.get(k) is not None]
        summary[k] = f"{sum(vals)}/{len(vals)}"
    toks = [r["completion_tokens"] for r in results if r.get("completion_tokens")]
    summary["mean_completion_tokens"] = round(sum(toks) / len(toks)) if toks else None
    return summary


def server_env():
    """Studio's prebuilt llama-server ships ggml-cuda.dll but not the CUDA runtime; borrow torch's copy."""
    env = dict(os.environ)
    spec = importlib.util.find_spec("torch")
    if spec and spec.submodule_search_locations:
        torch_lib = Path(spec.submodule_search_locations[0]) / "lib"
        if torch_lib.is_dir():
            env["PATH"] = f"{torch_lib}{os.pathsep}{env.get('PATH', '')}"
    return env


def port_free(port):
    with socket.socket() as s:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def wait_ready(port, proc, timeout=300):
    t = time.time()
    while time.time() - t < timeout:
        if proc.poll() is not None:
            raise RuntimeError("llama-server exited during startup; see its log")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as resp:
                if resp.status == 200:
                    return
        except Exception:
            pass
        time.sleep(1)
    raise TimeoutError("llama-server did not become ready")


def ask_model(port, row, args):
    body = {
        "messages": row["messages"][:2],
        "temperature": args.temperature, "top_p": 0.95, "top_k": 20,
        "presence_penalty": args.presence_penalty,
        "max_tokens": args.max_tokens, "seed": 3407,
        "chat_template_kwargs": {"enable_thinking": not args.no_think},
    }
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions",
                                 data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=1800) as resp:
            out = json.loads(resp.read())
        choice = out["choices"][0]
        msg = choice["message"]
    except urllib.error.HTTPError as e:
        return {"reasoning": "", "content": "", "finish": "error", "completion_tokens": None,
                "seconds": round(time.time() - t, 1), "error_message": f"HTTP {e.code}: {e.read()[:500]!r}"}
    except (OSError, KeyError, IndexError, ValueError) as e:
        return {"reasoning": "", "content": "", "finish": "error", "completion_tokens": None,
                "seconds": round(time.time() - t, 1), "error_message": f"{type(e).__name__}: {e}"}
    return {"reasoning": msg.get("reasoning_content") or "", "content": msg.get("content") or "",
            "finish": choice.get("finish_reason"), "completion_tokens": out.get("usage", {}).get("completion_tokens"),
            "seconds": round(time.time() - t, 1)}


def split_output(saved):
    """Reasoning and answer of a saved result (older result files only kept the combined text)."""
    if "content" in saved:
        return saved.get("reasoning", ""), saved["content"]
    text = saved.get("output", "")
    if text.startswith("<think>\n") and "\n</think>\n\n" in text:
        reasoning, content = text[len("<think>\n"):].split("\n</think>\n\n", 1)
        return reasoning, content
    return "", text


def rescore(path, test_path):
    """Re-score a saved results file in place with the current scoring rules (no GPU needed)."""
    saved = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = {row["id"]: row for row in load_rows(test_path)}
    types, motors = reference_vocab()
    results = []
    for old in saved["results"]:
        reasoning, content = split_output(old)
        finish = "error" if old.get("error") else ("length" if old.get("truncated") else "stop")
        r = score(rows[old["id"]], reasoning, content, finish, types, motors)
        r.update(completion_tokens=old.get("completion_tokens"), seconds=old.get("seconds"),
                 reasoning=reasoning, content=content)
        results.append(r)
    meta = {k: v for k, v in saved["summary"].items()
            if k in ("label", "gguf", "wall_minutes", "temperature", "presence_penalty", "thinking")}
    summary = summarize(results, meta)
    Path(path).write_text(json.dumps({"summary": summary, "results": results}, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gguf")
    ap.add_argument("--label")
    ap.add_argument("--rescore", metavar="RESULTS_JSON", help="re-score a saved results file instead of generating")
    ap.add_argument("--test", default=str(DATA / "sft_test.jsonl"))
    ap.add_argument("--out-dir", default=r"C:\ft\agents-a1-rocket\eval")
    ap.add_argument("--server", default=str(DEFAULT_SERVER))
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--parallel", type=int, default=4)
    ap.add_argument("--max-tokens", type=int, default=4096)
    ap.add_argument("--temperature", type=float, default=0.3)
    ap.add_argument("--presence-penalty", type=float, default=0.0, help="the model card recommends 1.1")
    ap.add_argument("--no-think", action="store_true", help="prompt with thinking off (for --keep-thought models)")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--overwrite", action="store_true", help="replace an existing results_<label>.json")
    args = ap.parse_args()

    if args.rescore:
        return rescore(args.rescore, args.test)
    if not (args.gguf and args.label):
        ap.error("--gguf and --label are required unless --rescore is given")

    rows = load_rows(args.test)
    rows = rows[: args.limit] if args.limit else rows
    types, motors = reference_vocab()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    res_path, log_path = out_dir / f"results_{args.label}.json", out_dir / f"server_{args.label}.log"
    if res_path.exists() and not args.overwrite:
        sys.exit(f"{res_path} already exists; pass a new --label or --overwrite")
    if not port_free(args.port):
        sys.exit(f"port {args.port} is already in use (another llama-server?); stop it or pass --port")

    devices = subprocess.run([args.server, "--list-devices"], env=server_env(),
                             capture_output=True, text=True).stdout.strip()
    print(devices, flush=True)
    if "CUDA" not in devices:
        print("WARNING: llama-server sees no CUDA device; generation will run on the CPU", flush=True)

    with open(log_path, "w", encoding="utf-8") as log:
        proc = subprocess.Popen([args.server, "-m", args.gguf, "--port", str(args.port), "-ngl", "999",
                                 "-c", str((args.max_tokens + 1024) * args.parallel), "-np", str(args.parallel),
                                 "--jinja", "--reasoning-format", "deepseek", "--no-webui"],
                                stdout=log, stderr=subprocess.STDOUT, env=server_env())
        try:
            wait_ready(args.port, proc)
            t0 = time.time()
            with ThreadPoolExecutor(args.parallel) as pool:
                answers = list(pool.map(lambda r: ask_model(args.port, r, args), rows))
            wall = time.time() - t0
        finally:
            proc.terminate()
            proc.wait(timeout=60)

    results = []
    for row, a in zip(rows, answers):
        r = score(row, a["reasoning"], a["content"], a["finish"], types, motors)
        r.update({k: v for k, v in a.items() if k != "finish"})
        results.append(r)
    meta = {"label": args.label, "gguf": args.gguf, "wall_minutes": round(wall / 60, 1),
            "temperature": args.temperature, "presence_penalty": args.presence_penalty,
            "thinking": not args.no_think}
    summary = summarize(results, meta)
    res_path.write_text(json.dumps({"summary": summary, "results": results}, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    sys.exit(main())
