"""The command line: python -m rocket_reward check / fetch-jar / score / preflight.

fetch-jar is tested only against local files and a tiny local web server,
never the real download. score uses recorded simulator replies, so no Java
is needed."""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from rocket_reward import cli
from test_scoring_sim import quiet  # noqa: F401  (a pytest fixture shared with that file)

DATA = Path(__file__).resolve().parent / "data"
REPO = Path(__file__).resolve().parents[2]


def _write(tmp_path, rows, name="rows.jsonl"):
    path = tmp_path / name
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    return path


def test_answer_is_read_from_content_answer_or_messages():
    assert cli.answer_of({"content": "a"}) == "a"
    assert cli.answer_of({"answer": "b"}) == "b"
    assert cli.answer_of({"messages": [{"role": "user", "content": "q"},
                                       {"role": "assistant", "content": "c"}]}) == "c"
    assert cli.answer_of({"other": 1}) is None
    assert cli.answer_of(["not", "a", "row"]) is None


def test_table_counts_the_model_answers():
    out = io.StringIO()
    assert cli.cmd_preflight([str(DATA / "model_val.jsonl.gz")], as_json=False, out=out) == 0
    text = out.getvalue()
    assert "motor" in text and "passed" in text and "total" in text and "48" in text


def test_json_output(tmp_path):
    path = _write(tmp_path, [{"id": "a", "content": "no design here"},
                             {"id": "b", "answer": "<design>{bad json</design>"},
                             {"id": "c", "content": "<design>{}</design>", "truncated": True},
                             {"id": "d"}])
    out = io.StringIO()
    assert cli.cmd_preflight([str(path)], as_json=True, out=out) == 0
    data = json.loads(out.getvalue())
    rows = data["rows"]
    assert rows["a"]["stage"] == "format" and rows["a"]["score"] == 0.0
    assert rows["b"]["score"] == 0.04          # JSON does not parse: credit 0.5
    assert rows["c"]["score"] == 0.0           # cut off
    assert rows["d"]["stage"] == "no_answer"
    assert data["summary"]["answers"] == 4
    assert data["summary"]["stages"]["format"] == 3


def test_gzip_input_and_garbage_lines(tmp_path):
    path = tmp_path / "rows.jsonl.gz"
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        fh.write('{"content": "x"}\nnot json\n\n')
    out = io.StringIO()
    assert cli.cmd_preflight([str(path)], as_json=True, out=out) == 0
    assert json.loads(out.getvalue())["summary"]["answers"] == 2


def test_missing_file_is_a_usage_error(tmp_path, capsys):
    assert cli.main(["preflight", str(tmp_path / "nope.jsonl")]) == 2


def test_module_entry_point_runs(tmp_path):
    path = _write(tmp_path, [{"content": "nothing"}])
    run = subprocess.run([sys.executable, "-m", "rocket_reward", "preflight", str(path), "--json"],
                         cwd=REPO, capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert run.returncode == 0, run.stderr
    assert json.loads(run.stdout)["summary"]["answers"] == 1


def test_non_ascii_answer_text_does_not_crash_the_output(tmp_path, gold_rows):
    """Reasons quote model-written text. With no PYTHONIOENCODING the console
    encoding on Windows is cp1252, which cannot hold every character."""
    answer = gold_rows[0]["answer"].replace("AeroTech-M2000R", "AeroTech-M2000R–火", 1)
    path = _write(tmp_path, [{"id": "odd-火", "answer": answer}])
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONIOENCODING", "PYTHONUTF8")}
    for extra in (["--json"], []):
        run = subprocess.run([sys.executable, "-m", "rocket_reward", "preflight", str(path), *extra],
                             cwd=REPO, capture_output=True, env=env, timeout=120)
        assert run.returncode == 0, run.stderr.decode("utf-8", "replace")
        text = run.stdout.decode("utf-8")
        if extra:
            rows = json.loads(text)["rows"]
            assert "odd-火" in rows
            assert "火" in " ".join(rows["odd-火"]["reasons"])


def test_cmd_preflight_writes_to_the_current_stdout(tmp_path, capsys):
    path = _write(tmp_path, [{"content": "nothing"}])
    assert cli.cmd_preflight([str(path)], as_json=True) == 0
    assert json.loads(capsys.readouterr().out)["summary"]["answers"] == 1


def test_documented_exit_codes():
    doc = cli.__doc__ or ""
    assert "3" in doc and "RewardSetupError" in doc
    for command in ("check", "fetch-jar", "score", "preflight"):
        assert f"  {command}" in doc, command


# ------------------------------------------------------------------ check

def test_check_with_the_fake_helper_says_ready():
    from test_sim import FAKE
    out = io.StringIO()
    assert cli.cmd_check(out, command=FAKE) == 0
    text = out.getvalue()
    assert "READY" in text and "self-test rocket flew" in text and "apogee" in text


def test_check_prints_what_to_fix(monkeypatch, tmp_path):
    """A wrong ROCKET_REWARD_JAVA_HOME stops the check before anything starts."""
    monkeypatch.setenv("ROCKET_REWARD_JAVA_HOME", str(tmp_path / "no-jdk-here"))
    out = io.StringIO()
    assert cli.cmd_check(out) == 3
    text = out.getvalue()
    assert "NOT READY" in text and "ROCKET_REWARD_JAVA_HOME" in text and "no bin/java" in text


def test_check_from_the_command_line_exit_code(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("ROCKET_REWARD_JAVA_HOME", str(tmp_path / "no-jdk-here"))
    assert cli.main(["check"]) == 3
    assert "NOT READY" in capsys.readouterr().out


# ------------------------------------------------------------------ fetch-jar (never the real download)

def _fake_jar(tmp_path, data=b"not really a jar, but pinned for this test\n" * 50):
    src = tmp_path / "src" / "OpenRocket-24.12.jar"
    src.parent.mkdir()
    src.write_bytes(data)
    return src, hashlib.sha256(data).hexdigest()


def test_fetch_jar_from_a_file_url_keeps_a_matching_file(tmp_path):
    src, digest = _fake_jar(tmp_path)
    dest = tmp_path / "lib" / "OpenRocket-24.12.jar"
    out = io.StringIO()
    assert cli.fetch_jar(src.as_uri(), dest, digest, out) == 0
    assert dest.read_bytes() == src.read_bytes() and "SHA-256 checked" in out.getvalue()
    out = io.StringIO()
    assert cli.fetch_jar("https://unused.invalid/x.jar", dest, digest, out) == 0   # already there: no download
    assert "nothing to do" in out.getvalue()


def test_fetch_jar_refuses_a_file_with_another_sha256(tmp_path):
    src, _ = _fake_jar(tmp_path)
    dest = tmp_path / "lib" / "OpenRocket-24.12.jar"
    out = io.StringIO()
    assert cli.fetch_jar(src.as_uri(), dest, "0" * 64, out) == 1
    assert "refused" in out.getvalue() and "nothing was kept" in out.getvalue()
    assert list(dest.parent.iterdir()) == []                  # no jar, no .part file left behind


def test_fetch_jar_replaces_a_wrong_file_only_with_the_right_one(tmp_path):
    src, digest = _fake_jar(tmp_path)
    dest = tmp_path / "lib" / "OpenRocket-24.12.jar"
    dest.parent.mkdir()
    dest.write_bytes(b"an old partial download")
    assert cli.fetch_jar(src.as_uri(), dest, "f" * 64, io.StringIO()) == 1
    assert dest.read_bytes() == b"an old partial download"   # a refused download changes nothing
    assert cli.fetch_jar(src.as_uri(), dest, digest, io.StringIO()) == 0
    assert dest.read_bytes() == src.read_bytes()


def test_fetch_jar_refuses_a_download_that_is_too_large(tmp_path):
    src, digest = _fake_jar(tmp_path)
    dest = tmp_path / "lib" / "OpenRocket-24.12.jar"
    out = io.StringIO()
    assert cli.fetch_jar(src.as_uri(), dest, digest, out, max_bytes=100) == 1
    assert "larger than" in out.getvalue() and list(dest.parent.iterdir()) == []


@pytest.mark.parametrize("url, words", [("ftp://example.invalid/OpenRocket-24.12.jar", "refused"),
                                        ("http://127.0.0.1:9/OpenRocket-24.12.jar", "download failed")])
def test_fetch_jar_bad_address(tmp_path, url, words):
    out = io.StringIO()
    assert cli.fetch_jar(url, tmp_path / "lib" / "x.jar", "0" * 64, out) == 1
    assert words in out.getvalue()


def test_fetch_jar_from_a_tiny_local_web_server(tmp_path):
    import functools
    import http.server
    import threading
    src, digest = _fake_jar(tmp_path)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(src.parent))
    handler.log_message = lambda *a, **k: None          # type: ignore[attr-defined]
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}/{src.name}"
        dest = tmp_path / "lib" / src.name
        assert cli.fetch_jar(url, dest, digest, io.StringIO()) == 0
        assert dest.read_bytes() == src.read_bytes()
    finally:
        server.shutdown()
        server.server_close()


def test_fetch_jar_defaults_are_the_pinned_release(monkeypatch):
    from rocket_reward import sim
    seen = {}
    monkeypatch.setattr(cli, "fetch_jar", lambda url, dest, sha, out: seen.update(url=url, dest=dest, sha=sha) or 0)
    assert cli.main(["fetch-jar"]) == 0
    assert seen == {"url": sim.OPENROCKET_JAR_URL, "dest": sim.DEFAULT_JAR_PATH, "sha": sim.OPENROCKET_JAR_SHA256}
    assert seen["url"].startswith("https://github.com/openrocket/openrocket/releases/download/")
    assert sim.DEFAULT_JAR_PATH.parent.name == "lib" and sim.DEFAULT_JAR_PATH.parent.parent == sim.PACKAGE_DIR


def test_the_jar_folder_is_never_committed():
    ignore = (REPO / "rocket_reward" / ".gitignore").read_text(encoding="utf-8").split("\n")
    assert "lib/" in ignore


# ------------------------------------------------------------------ score (recorded replies, no Java)

def _score(tmp_path, rows, requirements, *extra_args, simulator=None):
    answers = _write(tmp_path, rows, "answers.jsonl")
    req_path = None
    if requirements is not None:
        req_path = tmp_path / ("reqs" + (".jsonl" if isinstance(requirements, list) and requirements
                                         and "requirements" in requirements[0] else ".json"))
        if req_path.suffix == ".jsonl":
            _write(tmp_path, requirements, req_path.name)
        else:
            req_path.write_text(json.dumps(requirements), encoding="utf-8", newline="\n")
    out = io.StringIO()
    code = cli.cmd_score(str(answers), None if req_path is None else str(req_path), "--json" in extra_args,
                         2, out=out, simulator=simulator)
    return code, out.getvalue()


REQ_500 = {"id": "t-1", "apogee_m": {"value": 500, "kind": "about"}}


def test_score_table_with_recorded_replies(quiet, tmp_path, gold_rows):
    from test_scoring_sim import FakeSim
    rows = [{"id": "good", "answer": gold_rows[0]["answer"]}, {"id": "empty", "answer": "no design here"},
            {"id": "cut", "answer": gold_rows[0]["answer"], "truncated": True}]
    code, text = _score(tmp_path, rows, {"good": REQ_500, "empty": REQ_500, "cut": REQ_500},
                        simulator=FakeSim())
    assert code == 0
    lines = text.splitlines()
    assert lines[0].split()[:3] == ["answer", "stage", "score"]
    assert lines[2].split()[:3] == ["empty", "format", "0.0000"]
    assert lines[3].split()[:3] == ["cut", "format", "0.0000"]
    assert lines[1].split()[1] in ("build", "flight", "targets")
    assert "total" in text and "scores: min 0.0000" in text


def test_score_json_matches_score(quiet, tmp_path, gold_rows):
    from rocket_reward import Requirements, score
    from test_scoring_sim import FakeSim
    rows = [{"id": "a", "answer": gold_rows[0]["answer"]}]
    code, text = _score(tmp_path, rows, REQ_500, "--json", simulator=FakeSim())   # one record for every answer
    assert code == 0
    data = json.loads(text)
    direct = score(gold_rows[0]["answer"], Requirements.from_dict(REQ_500), simulator=FakeSim())
    assert data["rows"]["a"]["score"] == direct.score and data["rows"]["a"]["stage"] == direct.stage
    assert data["summary"]["answers"] == 1


def test_score_reads_jsonl_requirements_and_rows_with_their_own(quiet, tmp_path, gold_rows):
    from test_scoring_sim import FakeSim
    rows = [{"id": "a", "answer": gold_rows[0]["answer"]}, {"id": "b", "answer": "x", "requirements": REQ_500}]
    code, text = _score(tmp_path, rows, [{"id": "a", "requirements": REQ_500, "prompt": "..."}], "--json",
                        simulator=FakeSim())
    assert code == 0 and set(json.loads(text)["rows"]) == {"a", "b"}
    code, text = _score(tmp_path, [rows[1]], None, "--json", simulator=FakeSim())
    assert code == 0 and json.loads(text)["rows"]["b"]["stage"] == "format"


def test_score_refuses_rows_it_cannot_match(quiet, tmp_path, capsys):
    rows = [{"id": "a", "answer": "x"}, {"id": "b", "answer": "y"}]
    code, _ = _score(tmp_path, rows, {"a": REQ_500})
    assert code == 2
    err = capsys.readouterr().err
    assert "b: no requirements with this id" in err and "nothing was scored" in err
    assert "must use the same ids" not in err          # one id matched, so the files do fit
    code, _ = _score(tmp_path, rows, {"a": REQ_500, "b": {"id": "b", "apogee": 3}})
    assert code == 2 and "unknown keys" in capsys.readouterr().err


def test_score_says_when_no_id_matches_at_all(quiet, tmp_path, capsys):
    """A new user's slip: the model answers with the RL prompt file. Every id
    misses, so the message shows what the requirement ids look like."""
    rows = [{"id": f"row-{i}", "answer": "x"} for i in range(25)]
    code, _ = _score(tmp_path, rows, {"V4-0001:original": REQ_500, "V4-0002:casual": REQ_500})
    err = capsys.readouterr().err
    assert code == 2 and "and 5 more" in err
    assert "no answer id matches the 2 ids" in err and "'V4-0001:original'" in err


def test_score_starts_no_simulator_when_nothing_flies(quiet, tmp_path, monkeypatch):
    from rocket_reward import sim

    def no_pool(*a, **k):
        raise AssertionError("a simulator was started")
    monkeypatch.setattr(sim, "SimPool", no_pool)
    code, text = _score(tmp_path, [{"id": "a", "content": "no design"}], {"a": REQ_500})
    assert code == 0 and "format" in text


def test_score_command_line_errors(tmp_path):
    assert cli.main(["score", str(tmp_path / "nope.jsonl")]) == 2
    answers = _write(tmp_path, [{"id": "a", "content": "x"}])
    assert cli.main(["score", str(answers), str(tmp_path / "nope.json")]) == 2
    assert cli.main(["score", str(answers), "--workers", "0"]) == 2
