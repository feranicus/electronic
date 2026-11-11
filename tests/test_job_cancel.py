"""test_job_cancel.py — stopping an assessment, and never showing a dead one as live.

THE INCIDENT (11 Nov 2026). The operator started an assessment of `verint`, then ran `python
ship.py`, which recreated colt-web. `_RUNNING` is in-process state, so it died with the container;
the DB row still said `running`; the page re-attached, printed "Reconnected to an assessment
already running on the server" and sat at 88% / 7m07s forever. There was no way out — not
refreshing, not logging out — because nothing in the product could end a run.

Two separate defects, and both are tested here:
  1. no CANCEL at all, for a run that is genuinely executing;
  2. a run that is NOT executing was indistinguishable from one that is.

WHY MOST OF THIS RUNS IN A SUBPROCESS. DATA_DIR / JOBS_DIR are read at import time by settings.py
and store.py, and `app.main` is already imported by other test files in the same session with the
real paths. Monkeypatching after the fact would test a half-configured module; reloading would
leak into the next file. So the lifecycle scenarios run in their own interpreter with their own
environment and hand back measurements as JSON. That also means the REAL ASGI app, the REAL
asyncio task and a REAL engine subprocess are exercised — the point of the exercise is that a
live OS process gets killed, which no in-process stub can demonstrate.
"""
import json
import os
import re
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN = os.path.join(ROOT, "webapp", "backend", "app", "main.py")


def _src(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def _no_comments(src):
    """Strip comments and docstrings. A check has matched its own explanatory comment here
    five separate times (class 4), and this file comments heavily."""
    import ast
    out = re.sub(r"(?m)^\s*#.*$", "", src)
    try:
        tree = ast.parse(src)
    except SyntaxError:                                     # pragma: no cover
        return out
    docs = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            d = ast.get_docstring(node, clean=False)
            if d:
                docs.append(d)
    for d in docs:
        out = out.replace(d, "")
    return out


# ---------------------------------------------------------------------------------------------
# THE HARNESS — one subprocess, every lifecycle measurement
# ---------------------------------------------------------------------------------------------

SCENARIOS = r'''
import asyncio, json, os, sys, time

sys.path.insert(0, os.environ["BACKEND"])
sys.path.insert(0, os.environ["REPO"])
from app import main
from app import store
from app.auth import make_session

OUT = {}
EMAIL = "feranicus@s4biz.io"
STRANGER = "someone.else@s4biz.io"

# A fake engine: prints a line so the log is non-empty, then sleeps far longer than any test will
# wait. It is a REAL child process, which is the whole point — "cancelled" has to mean a pid is
# gone, not that a dictionary entry was removed.
FAKE = os.path.join(os.environ["TMP_DIR"], "fake_engine.py")
with open(FAKE, "w", encoding="utf-8") as fh:
    fh.write("import os, sys, time\n"
             # Record our OWN pid where the test can read it. No production code is added for the
             # test's convenience: the engine is told its --outdir and writes there, like it does
             # with every other artifact.
             "d = sys.argv[sys.argv.index('--outdir') + 1]\n"
             "open(os.path.join(d, 'engine.pid'), 'w').write(str(os.getpid()))\n"
             "print('PROGRESS: [4%] pretending to work', flush=True)\n"
             "time.sleep(600)\n")


async def request(path, method="GET", email=None, body=None):
    raw = json.dumps(body or {}).encode()
    headers = [(b"host", b"testserver"), (b"content-type", b"application/json")]
    if email:
        headers.append((b"cookie", ("colt_session=" + make_session(email)).encode()))
    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": method,
             "scheme": "http", "path": path, "raw_path": path.encode(), "query_string": b"",
             "root_path": "", "headers": headers,
             "client": ("127.0.0.1", 1), "server": ("testserver", 80)}
    got = {"status": 0, "body": b""}

    async def receive():
        return {"type": "http.request", "body": raw, "more_body": False}

    async def send(msg):
        if msg.get("type") == "http.response.start":
            got["status"] = msg["status"]
        elif msg.get("type") == "http.response.body":
            got["body"] += msg.get("body") or b""

    await main.app(scope, receive, send)
    try:
        got["json"] = json.loads(got["body"] or b"{}")
    except Exception:
        got["json"] = {}
    return got


def alive(pid):
    if pid is None:
        return False
    try:
        if os.name == "nt":
            import subprocess as sp
            r = sp.run(["tasklist", "/FI", "PID eq %d" % pid], capture_output=True, text=True)
            return str(pid) in (r.stdout or "")
        os.kill(pid, 0)
        return True
    except OSError:
        return False


async def start(job_id, company="acme"):
    """Launch a real _run_job against the fake engine and wait until its child is up."""
    store.create_job(job_id, EMAIL, company, "en")
    task = asyncio.ensure_future(
        main._run_job(job_id, EMAIL, company, "en", engine=FAKE))
    for _ in range(200):
        await asyncio.sleep(0.05)
        logp = main._job_dir(EMAIL, job_id) / "run.log"
        pidf = main._job_dir(EMAIL, job_id) / "engine.pid"
        if (job_id in main._RUNNING and logp.exists()
                and "pretending" in logp.read_text() and pidf.exists()):
            break
    return task


def engine_pid(job_id):
    """The fake engine's OWN pid, as it reported it — not the shell's, not a guess."""
    p = main._job_dir(EMAIL, job_id) / "engine.pid"
    return int(p.read_text().strip()) if p.exists() else None


async def scenarios():
    # ---- A. the orphan reaper -----------------------------------------------------------------
    store.create_job("orphanA", EMAIL, "ghost-corp", "en")
    OUT["A_before"] = store.get_job("orphanA")["status"]
    OUT["A_reaped"] = main._reap_orphans()
    OUT["A_after"] = store.get_job("orphanA")["status"]
    logp = main._job_dir(EMAIL, "orphanA") / "run.log"
    OUT["A_log"] = logp.read_text(encoding="utf-8") if logp.exists() else ""
    # and the page's own re-attach lookup must now report it as not running
    OUT["A_status_running"] = (await request("/api/assess/orphanA/status", email=EMAIL))["json"].get("running")

    # ---- B. cancel a run that is genuinely executing -------------------------------------------
    task = await start("liveB")
    pid = engine_pid("liveB")
    OUT["B_pid_alive_before"] = alive(pid)
    r = await request("/api/assess/liveB/cancel", method="POST", email=EMAIL)
    OUT["B_http"] = r["status"]
    OUT["B_body"] = r["json"]
    try:
        await task
    except asyncio.CancelledError:
        pass
    for _ in range(60):                       # the kill is asynchronous; give the OS a moment
        if not alive(pid):
            break
        await asyncio.sleep(0.05)
    OUT["B_pid_alive_after"] = alive(pid)
    OUT["B_status"] = store.get_job("liveB")["status"]
    OUT["B_in_running"] = "liveB" in main._RUNNING

    # ---- C. a stranger must not be able to stop somebody else's run ----------------------------
    task = await start("liveC")
    pid = engine_pid("liveC")
    r = await request("/api/assess/liveC/cancel", method="POST", email=STRANGER)
    OUT["C_http"] = r["status"]
    OUT["C_status"] = store.get_job("liveC")["status"]
    OUT["C_pid_alive"] = alive(pid)
    # anonymous too
    OUT["C_anon_http"] = (await request("/api/assess/liveC/cancel", method="POST"))["status"]
    # clean up
    await request("/api/assess/liveC/cancel", method="POST", email=EMAIL)
    try:
        await task
    except asyncio.CancelledError:
        pass

    # ---- D. the hard wall ----------------------------------------------------------------------
    main.JOB_WALL_S = 1
    t0 = time.time()
    task = await start("wallD")
    pid = engine_pid("wallD")
    try:
        await asyncio.wait_for(task, timeout=30)
    except Exception as e:
        OUT["D_raised"] = type(e).__name__
    OUT["D_seconds"] = round(time.time() - t0, 1)
    OUT["D_status"] = store.get_job("wallD")["status"]
    OUT["D_pid_alive"] = alive(pid)
    OUT["D_log"] = (main._job_dir(EMAIL, "wallD") / "run.log").read_text(encoding="utf-8")
    main.JOB_WALL_S = 2700

    # ---- E. idempotent on a run that already ended ----------------------------------------------
    r = await request("/api/assess/wallD/cancel", method="POST", email=EMAIL)
    OUT["E_http"] = r["status"]
    OUT["E_body"] = r["json"]
    OUT["E_status_unchanged"] = store.get_job("wallD")["status"]

    # ---- F. an orphan row this process does not own -----------------------------------------
    store.create_job("orphanF", EMAIL, "ghost-two", "en")
    r = await request("/api/assess/orphanF/cancel", method="POST", email=EMAIL)
    OUT["F_http"] = r["status"]
    OUT["F_body"] = r["json"]
    OUT["F_status"] = store.get_job("orphanF")["status"]


loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(scenarios())
print("@@RESULT@@" + json.dumps(OUT))
'''


@pytest.fixture(scope="module")
def out(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("jobs")
    script = tmp / "scenarios.py"
    script.write_bytes(SCENARIOS.encode("utf-8"))        # BYTES: no newline translation (class 21)
    env = dict(os.environ)
    env.update({
        "DATA_DIR": str(tmp / "data"),
        "JOBS_DIR": str(tmp / "data" / "jobs"),
        "TMP_DIR": str(tmp),
        "BACKEND": os.path.join(ROOT, "webapp", "backend"),
        "REPO": ROOT,
        # The container runs `python3`; this machine may not have one on PATH at all.
        "ENGINE_PYTHON": sys.executable,
        "SESSION_SECRET": "test-secret-for-job-cancel",
        "PYTHONIOENCODING": "utf-8",
    })
    r = subprocess.run([sys.executable, str(script)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env, timeout=300)
    m = re.search(r"@@RESULT@@(\{.*\})\s*$", r.stdout or "", re.S)
    if not m:
        pytest.fail("the scenario harness produced no result.\nrc=%s\nSTDOUT:\n%s\nSTDERR:\n%s"
                    % (r.returncode, (r.stdout or "")[-3000:], (r.stderr or "")[-3000:]))
    return json.loads(m.group(1))


# ---------------------------------------------------------------------------------------------
# 1. THE ORPHAN — a run that is not running must never be shown as running
# ---------------------------------------------------------------------------------------------

def test_a_row_left_running_by_a_dead_process_is_reaped_at_boot(out):
    assert out["A_before"] == "running", "fixture: the row must start out looking live"   # class 12
    assert out["A_reaped"] >= 1, "the reaper found nothing to reap, so it proved nothing"
    assert out["A_after"] == "interrupted", (
        "the orphan row is still %r — the page will re-attach to it forever" % out["A_after"])


def test_the_reaped_job_says_in_its_own_log_what_happened(out):
    """The next thing a person does is open the log and ask why it stopped."""
    assert "restart" in out["A_log"], (
        "the log says nothing about a restart, so the run looks like it vanished: %r"
        % out["A_log"][-300:])


def test_the_status_route_reports_a_reaped_job_as_not_running(out):
    assert out["A_status_running"] is False


def test_the_reaper_runs_on_startup_and_not_in_the_background():
    """Wiring, not intention (class 9). A reaper nobody calls is a function, not a fix.

    It must also be synchronous within the startup hook: reaping AFTER this process has begun
    accepting work could mark a live job as an orphan.
    """
    import ast
    tree = ast.parse(_src("webapp/backend/app/main.py"))
    wired = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        decorated = any("startup" in ast.dump(d) for d in node.decorator_list)
        if not decorated:
            continue
        calls = {getattr(c.func, "id", "") for c in ast.walk(node) if isinstance(c, ast.Call)}
        if "_reap_orphans" in calls:
            wired.append(node.name)
    assert wired, "no startup handler calls _reap_orphans — the fix is unreachable"
    body = _no_comments(_src("webapp/backend/app/main.py"))
    assert "create_task(_reap_orphans" not in body and "sleep" not in body.split(
        "async def _reap_on_boot")[1].split("\n\n")[0], (
        "the reaper must not be deferred: a delayed reap can kill a job started in the meantime")


# ---------------------------------------------------------------------------------------------
# 2. CANCEL — and "cancelled" has to mean the engine is dead
# ---------------------------------------------------------------------------------------------

def test_cancel_kills_the_real_engine_process(out):
    assert out["B_pid_alive_before"] is True, (
        "fixture: the engine subprocess was never alive, so killing it proves nothing")  # class 12
    assert out["B_http"] == 200, "cancel answered %s" % out["B_http"]
    assert out["B_body"].get("stopped") is True
    assert out["B_pid_alive_after"] is False, (
        "the row was marked cancelled while the engine kept running — Shodan queries and paid "
        "model calls would continue behind a page that says it stopped")
    assert out["B_status"] == "cancelled", (
        "a cancel is not a crash; the run ended as %r" % out["B_status"])
    assert out["B_in_running"] is False, "the job is still registered as in flight"


def test_a_stranger_cannot_stop_somebody_elses_assessment(out):
    assert out["C_http"] == 404, "another signed-in user got %s, not 404" % out["C_http"]
    assert out["C_anon_http"] in (401, 403), (
        "an anonymous caller got %s — every non-public route refuses one" % out["C_anon_http"])
    assert out["C_status"] == "running", "the victim's run was ended by someone else"
    assert out["C_pid_alive"] is True, "the victim's engine was killed by someone else"


def test_cancelling_a_finished_run_changes_nothing(out):
    assert out["E_http"] == 200, "a double click must not 500"
    assert out["E_body"].get("already") is True
    assert out["E_status_unchanged"] == "timeout", (
        "cancel rewrote a run that had already ended as %r" % out["E_status_unchanged"])


def test_an_orphan_row_is_corrected_and_says_nothing_was_killed(out):
    assert out["F_http"] == 200
    assert out["F_body"].get("stopped") is False, (
        "the endpoint claimed it stopped an engine that was never there")
    assert out["F_status"] == "interrupted"


# ---------------------------------------------------------------------------------------------
# 3. THE WALL — a hang must end itself
# ---------------------------------------------------------------------------------------------

def test_a_run_past_its_limit_is_killed_and_labelled_timeout(out):
    assert out["D_status"] == "timeout", (
        "a run that blew its wall ended as %r; 'error' hides the one fact that explains it"
        % out["D_status"])
    assert out["D_pid_alive"] is False, "the wall fired but the engine kept running"
    assert out["D_seconds"] < 25, (
        "the wall took %ss with JOB_WALL_S=1 — it is not actually bounding the run"
        % out["D_seconds"])
    assert "limit" in out["D_log"], "the log does not say why it stopped: %r" % out["D_log"][-300:]
    assert "assessment failed" not in out["D_log"], (
        "the timeout is also reported as a generic failure — one event, two voices")


def test_the_wall_is_configurable_and_finite():
    body = _no_comments(_src("webapp/backend/app/main.py"))
    assert "JOB_WALL_S" in body, "there is no wall"
    m = re.search(r"JOB_WALL_S\s*=\s*int\(os\.environ\.get\(\"JOB_WALL_S\"\)\s*or\s*(\d+)\)", body)
    assert m, "JOB_WALL_S must come from the environment with a default"
    assert 300 <= int(m.group(1)) <= 7200, (
        "the default wall is %ss: too tight kills real large-estate runs, too loose is no wall"
        % m.group(1))


# ---------------------------------------------------------------------------------------------
# 4. THE PAGE — the button exists, in every language, on both engines
# ---------------------------------------------------------------------------------------------

def test_both_pages_can_stop_a_run():
    for page in ("NewAssessment.jsx", "Compliance.jsx"):
        src = _src(os.path.join("webapp", "frontend", "src", "pages", page))
        assert "assessCancel" in src, "%s cannot stop a run" % page
        assert "assess.cancelConfirm" in src, "%s stops a paid run with no confirmation" % page
        assert "assess.timedOut" in src and "assess.interrupted" in src, (
            "%s renders every ending as the same sentence" % page)


def test_the_four_endings_are_translated_everywhere():
    """The catalogue gate enforces 100%, but it would also pass if the keys existed only in
    English and nowhere else — so assert the keys are PRESENT per locale, here."""
    keys = ["assess.cancel", "assess.cancelling", "assess.cancelConfirm", "assess.cancelled",
            "assess.cancelOrphan", "assess.timedOut", "assess.interrupted"]
    en = _src(os.path.join("webapp", "frontend", "src", "locales", "en.js"))
    for code in ("de", "it", "fr", "es", "pl"):
        src = _src(os.path.join("webapp", "frontend", "src", "locales", code + ".js"))
        for k in keys:
            assert '"%s"' % k in src, "%s is missing %s" % (code, k)
            val = re.search(r'"%s":\s*"(.*?)(?<!\\)"' % re.escape(k), src)
            ref = re.search(r'"%s":\s*"(.*?)(?<!\\)"' % re.escape(k), en)
            assert val and ref, "%s: %s is unreadable" % (code, k)
            assert val.group(1) != ref.group(1), (
                "%s left %s in English" % (code, k))
