"""Score a GGUF model on held-out prompts with llama-server (default: the 38 prompts in new_results/sft_test_v2.jsonl).

Defaults match the shipped Qwen3.5-4B model: thinking off, sft/design.gbnf as the output grammar, temperature 0.7.
--think (which also drops the grammar) and --no-grammar give the raw model, as used for the Agents-A1-4B run.

Checks format only: designs aren't simulated, so "does the rocket fly" is not tested. Per answer
(the <design> block is looked for in the final answer only, not in the reasoning), for the old
{"flight", "components"} designs (sft_v0 to sft_v2):
  design_found   <design>...</design> present        json_ok      the design JSON parses
  schema_ok      flight.motor + components, every component type is one seen in the data,
                 at least one nosecone and one bodytube        recovery     a parachute or streamer
  motor_known    every motor is in data/catalog.sqlite or the SFT data
  motor_match    when the prompt names a motor, the design uses it (a miss if there is no valid design)
  claim_vs_ask   when the prompt gives a target apogee, the "Simulated apogee" the model writes is within
                 10% of it. This is the model's own claim, not a simulation.
  truncated      hit --max-tokens before finishing        error       the request itself failed

For sft_v5 designs (an OpenRocket XML tree as JSON; pass --motor-lookup with new_results/sft_v4_motor_lookup.json
from branch sft-v5-data):
  tree_ok        every node is {tag: {attrs?, value?, children?}} under one "openrocket" root
  schema_ok      tree_ok, and the parts sit where OpenRocket puts them: a stage under rocket/subcomponents,
                 a nosecone, bodytube and fin set inside it, a motor inside a motormount of a body or inner tube
  recovery       a parachute or streamer inside the stage
  motor_known    every motor_id is a motor file in the lookup
                 (a second top-level key next to "openrocket" fails tree_ok and schema_ok, but the parts and
                 motors in it still count for recovery, motor_known and motor_match)
  motor_match    every motor the prompt names ("motor K550W", "motors G71R and H225BL") is in the design, by its
                 designation text or its motor_id (the reference answers sometimes pair a motor_id with a sibling
                 designation, so either one counts)

Usage (Unsloth Studio's Python; llama-server ships with Studio):
    python sft\\eval_test.py --gguf C:\\ft\\qwen35-rocket\\gguf\\Qwen3.5-4B-rocketdata.Q4_K_M.gguf --label test
    python sft\\eval_test.py --gguf ... --label rl --test data\\splits\\rl_heldout.jsonl
    python sft\\eval_test.py --rescore C:\\ft\\qwen35-rocket\\eval\\results_test.json   (no GPU)
    python sft\\eval_test.py --gguf ... --label val --test <sft_v5 val.jsonl> --max-tokens 16384 ^
        --motor-lookup <new_results\\sft_v4_motor_lookup.json from branch sft-v5-data>
"""
import argparse
import hashlib
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
NEW_RESULTS = REPO / "new_results"
DEFAULT_GRAMMAR = REPO / "sft" / "design.gbnf"
DEFAULT_SERVER = Path.home() / ".unsloth" / "llama.cpp" / "build" / "bin" / "Release" / "llama-server.exe"
NUM = r"([\d][\d,]*(?:\.\d+)?)"
KEYS = ["design_found", "json_ok", "tree_ok", "schema_ok", "recovery", "motor_known", "motor_match",
        "claim_vs_ask", "truncated", "error"]
# sft_v5 designs are an OpenRocket XML tree written as JSON: {"openrocket": {"attrs", "children": [...]}}
V5_NODE_KEYS = {"attrs", "value", "children"}
V5_REQUIRED = {"rocket", "stage", "nosecone", "bodytube", "motormount", "motor"}
V5_FINSETS = {"trapezoidfinset", "ellipticalfinset", "freeformfinset", "tubefinset"}
V5_IN_STAGE = {"nosecone", "bodytube", "parachute", "streamer"} | V5_FINSETS
MOTOR_RE = r"[0-9/]*[A-O][0-9]{1,4}[A-Z]{0,4}(?:-[0-9A-Z]+)?"
# motor names as sft_v5 prompts write them, e.g. K550W, HP-H195NT, G79W/L, I216-CL(I), 3147L935-P
V5_MOTOR_RE = r"(?:HP-)?[0-9/]*[A-O][0-9]{1,4}[A-Z]{0,4}(?:/[A-Z]{1,2})?(?:-[0-9A-Z]+)?(?:\([A-Z]\))?"


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
    for path in (DATA / "sft_v0.jsonl", DATA / "sft_test.jsonl", REPO / "new_results" / "sft_v1.jsonl",
                 REPO / "new_results" / "sft_v2.jsonl", REPO / "new_results" / "sft_test_v2.jsonl"):
        if not path.exists():
            continue
        for line in open(path, encoding="utf-8"):
            ans = json.loads(line)["messages"][-1]["content"]
            d = json.loads(ans.split("<design>")[1].split("</design>")[0])
            m = d["flight"]["motor"]
            motors.update(m if isinstance(m, list) else [m])
            types.update(c["type"] for c in walk(d["components"]))
    with sqlite3.connect(DATA / "catalog.sqlite") as db:
        motors.update(r[0] for r in db.execute("select designation from motors"))
    return types, motors


def load_rows(path):
    """SFT rows carry "messages"; RL rows (data/splits/rl_heldout.jsonl) carry "prompt" with no answer.

    Rows without an "id" (sft_v5 keeps only "messages") get one from their line number and prompt, so
    --rescore against the wrong --test file fails instead of pairing answers with other prompts.
    """
    rows = []
    for line in open(path, encoding="utf-8"):
        if line.strip():
            row = json.loads(line)
            row.setdefault("messages", row.get("prompt"))
            digest = hashlib.sha1(json.dumps(row["messages"][:2], sort_keys=True).encode("utf-8")).hexdigest()
            row.setdefault("id", f"row-{len(rows) + 1:03d}-{digest[:8]}")
            rows.append(row)
    return rows


def v5_tree(design):
    """(tree_ok, placed, motors) for an sft_v5 design.

    placed: the part tags found where OpenRocket puts them (rocket under openrocket, a stage component under
    rocket/subcomponents, parts inside that stage, a motormount on a body or inner tube, a motor in a motormount).
    motors: [(motor_id, designation)] per <motor> node, None for a missing or non-string value.
    """
    placed, motors, ok = set(), [], True
    stack = [(design, None, None, False)]  # node, parent tag, grandparent tag, inside a stage component
    while stack:
        node, parent, grand, in_stage = stack.pop()
        if not (isinstance(node, dict) and node):
            ok = False
            continue
        if len(node) > 1:  # e.g. "simulations" next to "openrocket": malformed, but still walk each part
            ok = False
            stack.extend(({k: v}, parent, grand, in_stage) for k, v in node.items())
            continue
        (tag, body), = node.items()
        if not isinstance(body, dict):
            ok = False
            continue
        if not set(body) <= V5_NODE_KEYS:
            ok = False  # keep walking, so one stray key doesn't hide the parts below it
        kids = body.get("children", [])
        if not isinstance(kids, list):
            ok, kids = False, []
        if tag == "rocket" and parent == "openrocket":
            placed.add(tag)
        elif tag == "stage" and parent == "subcomponents" and grand == "rocket":
            placed.add(tag)
            in_stage = True
        elif in_stage and (tag in V5_IN_STAGE or tag == "motormount" and parent in ("bodytube", "innertube")
                           or tag == "motor" and parent == "motormount"):
            placed.add(tag)
        if tag == "motor":
            fields = {k: b.get("value") for c in kids if isinstance(c, dict) and len(c) == 1
                      for k, b in c.items() if isinstance(b, dict)}
            motors.append(tuple(v if isinstance(v, str) else None
                                for v in (fields.get("motor_id"), fields.get("designation"))))
        stack.extend((kid, tag, parent, in_stage) for kid in kids)
    return ok, placed, motors


def asked_motors(prompt):
    """Motors an sft_v5 prompt asks for: "motor K550W", "Motor F50T", "motors G71R and H225BL", "the M1297W motor"."""
    m = re.search(r"\b[Mm]otors?(?: is)?\s*[:=]?\s*(" + V5_MOTOR_RE + r"(?:\s*(?:,|and|&|\+)\s*" + V5_MOTOR_RE
                  + r")*)", prompt)
    if m:
        return re.findall(V5_MOTOR_RE, m.group(1))
    m = re.search(r"\b(" + V5_MOTOR_RE + r") [Mm]otors?\b", prompt)
    return [m.group(1)] if m else []


def score_v5(r, design, prompt, lookup):
    """Fill r with the sft_v5 checks: a well-formed OpenRocket tree with the parts a flyable rocket needs."""
    tree_ok, placed, motors = v5_tree(design)
    r["tree_ok"] = tree_ok and "openrocket" in design
    r["schema_ok"] = r["tree_ok"] and V5_REQUIRED <= placed and bool(placed & V5_FINSETS)
    r["recovery"] = bool(placed & {"parachute", "streamer"})
    r["motors"] = [m[0] or m[1] for m in motors]
    # A real motor file; the reference answers themselves sometimes pair a motor_id with a sibling designation
    # (AeroTech-J90 written as J90W), so the designation is not checked here.
    r["motor_known"] = bool(motors) and all(mid in lookup for mid, des in motors)
    wants = asked_motors(prompt)
    r["asked_motor"] = " + ".join(wants) or None
    if wants:
        r["motor_match"] = all(any(w in (des, lookup.get(mid, {}).get("designation")) or (mid or "").endswith("-" + w)
                                   for mid, des in motors) for w in wants)
    r["claim_vs_ask"] = None  # v5 reasoning cites stored reference flights, not a "Simulated apogee" line


def last_design(content):
    """Body of the last <design>...</design> block in the answer, or None."""
    i = content.rfind("<design>")
    j = content.find("</design>", i) if i != -1 else -1
    return content[i + len("<design>"):j].strip() if j != -1 else None


def score(row, reasoning, content, finish, types, motors, lookup=None):
    prompt = row["messages"][1]["content"]
    r = {"id": row["id"], "truncated": finish == "length", "error": finish == "error"}
    body = last_design(content)
    r["design_found"] = body is not None
    design = None
    if body is not None:
        try:
            design = json.loads(body)
        except (ValueError, RecursionError):  # bad JSON, a 4,300+ digit number, or very deep nesting
            pass
    r["json_ok"] = isinstance(design, dict)
    r["tree_ok"] = None
    r["schema_ok"] = r["recovery"] = r["motor_known"] = False
    if r["json_ok"] and "openrocket" in design or lookup is not None:
        r["tree_ok"] = False
        r["motor_match"] = None
        if r["json_ok"]:
            score_v5(r, design, prompt, lookup or {})
            if lookup is None:
                r["motor_known"] = None  # can't tell without --motor-lookup; the summary shows 0/0, not 0/N
        else:
            wants = asked_motors(prompt)
            r["asked_motor"] = " + ".join(wants) or None
            r["motor_match"] = False if wants else None
            r["claim_vs_ask"] = None
        return r
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
    if args.grammar_text:
        body["grammar"] = args.grammar_text
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


def load_lookup(path):
    """motor_id -> motor info for sft_v5 scoring (new_results/sft_v4_motor_lookup.json, branch sft-v5-data), or None."""
    return json.loads(Path(path).read_text(encoding="utf-8")) if path else None


def rescore(path, test_path, lookup=None, lookup_path=None):
    """Re-score a saved results file in place with the current scoring rules (no GPU needed)."""
    saved = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = {row["id"]: row for row in load_rows(test_path)}
    types, motors = reference_vocab()
    results = []
    for old in saved["results"]:
        reasoning, content = split_output(old)
        finish = old.get("finish") or ("error" if old.get("error") else ("length" if old.get("truncated") else "stop"))
        r = score(rows[old["id"]], reasoning, content, finish, types, motors, lookup)
        r.update(completion_tokens=old.get("completion_tokens"), seconds=old.get("seconds"),
                 reasoning=reasoning, content=content)
        results.append(r)
    meta = {k: v for k, v in saved["summary"].items()
            if k in ("label", "gguf", "wall_minutes", "temperature", "presence_penalty", "thinking", "grammar")}
    meta.update(test=str(test_path), motor_lookup=lookup_path)
    summary = summarize(results, meta)
    Path(path).write_text(json.dumps({"summary": summary, "results": results}, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gguf")
    ap.add_argument("--label")
    ap.add_argument("--rescore", metavar="RESULTS_JSON", help="re-score a saved results file instead of generating")
    ap.add_argument("--test", default=str(NEW_RESULTS / "sft_test_v2.jsonl"))
    ap.add_argument("--out-dir", default=r"C:\ft\qwen35-rocket\eval")
    ap.add_argument("--server", default=str(DEFAULT_SERVER))
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--parallel", type=int, default=4)
    ap.add_argument("--max-tokens", type=int, default=4096)
    ap.add_argument("--temperature", type=float, default=0.7, help="0.3 makes the Qwen model loop")
    ap.add_argument("--presence-penalty", type=float, default=0.0, help="keep 0: any penalty breaks the JSON")
    ap.add_argument("--no-think", dest="no_think", action="store_true", default=True,
                    help="prompt with thinking off (the default; for models trained verbatim)")
    ap.add_argument("--think", dest="no_think", action="store_false",
                    help="prompt with thinking on (for --move-thought models); also turns the grammar off")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--overwrite", action="store_true", help="replace an existing results_<label>.json")
    ap.add_argument("--grammar", default=str(DEFAULT_GRAMMAR),
                    help="GBNF file that constrains every answer (default sft\\design.gbnf)")
    ap.add_argument("--no-grammar", dest="grammar", action="store_const", const=None,
                    help="score the raw model, with no output grammar")
    ap.add_argument("--motor-lookup",
                    help="sft_v5 scoring: motor_id lookup JSON (new_results/sft_v4_motor_lookup.json on branch sft-v5-data)")
    args = ap.parse_args()
    if not args.no_think:
        args.grammar = None  # the grammar starts at <thought>, so it can't cover a <think> block
    args.grammar_text = Path(args.grammar).read_text(encoding="utf-8") if args.grammar else None
    lookup = load_lookup(args.motor_lookup)
    if lookup is None and any('{"openrocket"' in str(row["messages"][-1].get("content", ""))
                              for row in load_rows(args.test)):
        ap.error("this --test file has sft_v5 (OpenRocket tree) answers; pass --motor-lookup")

    if args.rescore:
        return rescore(args.rescore, args.test, lookup, args.motor_lookup)
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

    meta = {"label": args.label, "gguf": args.gguf, "wall_minutes": round(wall / 60, 1),
            "temperature": args.temperature, "presence_penalty": args.presence_penalty,
            "thinking": not args.no_think, "grammar": args.grammar, "test": args.test,
            "motor_lookup": args.motor_lookup}
    # save the raw answers first, so a scoring error can't lose the generation (fix the scorer, then --rescore)
    raw = [dict(a, id=row["id"]) for row, a in zip(rows, answers)]
    res_path.write_text(json.dumps({"summary": meta, "results": raw}, indent=1), encoding="utf-8")
    results = []
    for row, a in zip(rows, answers):
        r = score(row, a["reasoning"], a["content"], a["finish"], types, motors, lookup)
        r.update({k: v for k, v in a.items() if k != "finish"})
        results.append(r)
    summary = summarize(results, meta)
    res_path.write_text(json.dumps({"summary": summary, "results": results}, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    sys.exit(main())
