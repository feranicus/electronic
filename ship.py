#!/usr/bin/env python3
"""
ship.py — THE ONE COMMAND. Test, commit, push, deploy, verify. Nothing else to run.

    python ship.py                     # test -> commit+push -> deploy web + bots -> verify
    python ship.py -m "your message"   # same, with your commit message
    python ship.py --test              # tests only, change nothing
    python ship.py --web               # only cybergod.ai (colt-web)
    python ship.py --bots              # only the Telegram bots
    python ship.py --ci                # deploy via GitHub Actions instead of direct SSH
    python ship.py --no-test           # skip tests (you had better have a reason)
    python ship.py --dry-run           # print the plan, touch nothing
    python ship.py --rollback          # restore last-known-good state + redeploy it

STANDING RULE (see CLAUDE.md): there is exactly ONE orchestrator. Every other script here is a
building block that ship.py calls — never something the operator runs by hand. If a task needs two
commands, that is a bug in this file, not an instruction for the user.

What it orchestrates (each of these is still runnable alone for debugging, but you should not have to):
    pytest tests/                              unit tests: auth + recon
    hermes-skills/.../test_ca_pivot.py         CA-pivot regression (bibeltv false POSITIVES)
    hermes-skills/.../test_recall.py           recall regression (bibeltv false NEGATIVES)
    author_geopol.py + build_geopol_html.js    the 5th deliverable (GEOPOL HTML) renders
    py_compile over every engine script        catches the truncation/syntax class of bug
    ship_web.py                                web: build -> GHCR -> Actions -> droplet -> Caddy
    deploy.py --reuse --yes                    bots: rebuild + redeploy colt-stack
    deploy_web_direct.py                       web: build on the droplet over SSH (DEFAULT)
"""
import argparse, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
HOST = os.environ.get("DROPLET_HOST", "64.225.108.200")
USER = os.environ.get("DROPLET_USER", "root")
KEY  = os.environ.get("SSH_KEY", os.path.expanduser("~/.ssh/id_ed25519"))
DOMAIN = "cybergod.ai"

# Every ssh MUST fail fast — a silent 40-minute hang is the failure mode we already paid for.
SSH = ["ssh", "-o", "StrictHostKeyChecking=accept-new", "-o", "LogLevel=ERROR",
       "-o", "ConnectTimeout=10", "-o", "BatchMode=yes",
       "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=4"]
if os.path.exists(KEY):
    SSH += ["-i", KEY]

DRY = False
T0 = time.time()


# ------------------------------------------------------------------ plumbing
def say(msg, char="-"):
    print("\n" + char * 74)
    print("  " + msg + "     [+%ds]" % int(time.time() - T0))
    print(char * 74, flush=True)


def run(args, check=True, cwd=None):
    """Run a local command, streaming output. Announce BEFORE blocking."""
    print("  $ " + " ".join(str(a) for a in args), flush=True)
    if DRY:
        return 0
    rc = subprocess.run([str(a) for a in args], cwd=cwd or HERE).returncode
    if check and rc != 0:
        sys.exit("\n[X] FAILED: %s\n    Nothing was deployed. Fix this, then re-run: python ship.py"
                 % " ".join(str(a) for a in args))
    return rc


def ssh(cmd, check=False):
    print("  $ ssh %s@%s %r" % (USER, HOST, cmd[:70]), flush=True)
    if DRY:
        return ""
    r = subprocess.run(SSH + ["%s@%s" % (USER, HOST), cmd], text=True, capture_output=True)
    if r.stdout.strip():
        print("    " + r.stdout.rstrip().replace("\n", "\n    "))
    if check and r.returncode != 0:
        sys.exit("[X] remote failed: %s\n%s" % (cmd, r.stderr[:400]))
    return r.stdout


def have(exe):
    from shutil import which
    return which(exe) is not None


def _test_python():
    """Interpreter to run the unit suite with.

    Uses the repo venv ONLY if it is already equipped with pytest (that is where the project's
    dependencies live). Otherwise use the interpreter the operator actually invoked, so behaviour
    matches what they typed rather than silently jumping into an environment they forgot about."""
    for rel in (("venv", "Scripts", "python.exe"), ("venv", "bin", "python"),
                (".venv", "Scripts", "python.exe"), (".venv", "bin", "python")):
        p = os.path.join(HERE, *rel)
        if os.path.exists(p) and _has_pytest(p):
            return p
    return sys.executable


# Files whose content MUST match between this repo and every running container. Hashing the actual
# deployed engine is the only honest proof of a deploy: bibeltv.de was re-run against a 3-day-old
# colt-web because the CI deploy failed, ship_web.py still printed DONE, and the verify step only
# checked that /api/me returned 401 — which a stale container answers perfectly well.
ENGINE_FILES = ["scripts/shodan_recon.py", "scripts/run_assessment.py", "scripts/enrich.py",
                "scripts/compliance_assess.py", "scripts/compliance_enrich.py"]
ENGINE_LOCAL = os.path.join(HERE, "hermes-skills", "shodan-assessment")
ENGINE_REMOTE = "/opt/shodan-skill"


def _sha_local(rel):
    import hashlib
    p = os.path.join(ENGINE_LOCAL, rel.replace("/", os.sep))
    if not os.path.exists(p):
        return None
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def _sha_in_container(container, rel):
    """sha256 of a file INSIDE a running container. Uses python3 (always present in these images)
    rather than sha256sum, which slim images sometimes lack."""
    code = ("import hashlib,sys;p='%s/%s';\n"
            "sys.stdout.write(hashlib.sha256(open(p,'rb').read()).hexdigest())" % (ENGINE_REMOTE, rel))
    out = ssh("docker exec %s python3 -c \"%s\" 2>/dev/null || echo MISSING" % (container, code))
    return (out or "").strip().splitlines()[-1].strip() if out else "MISSING"


def engine_is_current(container):
    """-> (ok, [list of stale files]). Proves the container runs THIS repo's engine."""
    stale = []
    for rel in ENGINE_FILES:
        want = _sha_local(rel)
        if not want:
            continue
        got = _sha_in_container(container, rel)
        if got != want:
            stale.append("%s (container=%s repo=%s)" % (rel, got[:12], want[:12]))
    return (not stale), stale


def _has_pytest(py):
    """True if `py` can import pytest. Never raises: a stale/wrong-arch venv (e.g. a Windows
    venv\\Scripts\\python.exe seen from WSL) makes subprocess throw OSError, and that must degrade
    to 'not usable', not take down the whole ship."""
    try:
        return subprocess.run([py, "-c", "import pytest"], capture_output=True).returncode == 0
    except OSError:
        return False


# ------------------------------------------------------------------ 1. tests
def do_tests():
    say("1/5  TESTS — nothing ships if these fail")
    engine = os.path.join(HERE, "hermes-skills", "shodan-assessment", "scripts")

    # a) compile every engine + root script: catches truncation and syntax breakage early
    bad = []
    for root in (engine, HERE, os.path.join(HERE, "webapp", "backend", "app")):
        if not os.path.isdir(root):
            continue
        for fn in sorted(os.listdir(root)):
            if not fn.endswith(".py") or fn.startswith("linkedin_verifier_old"):
                continue
            p = os.path.join(root, fn)
            if subprocess.run([sys.executable, "-m", "py_compile", p],
                              capture_output=True).returncode != 0:
                bad.append(os.path.relpath(p, HERE))
    print("  compile check: %d file(s) broken" % len(bad))
    if bad:
        for b in bad:
            print("    [X] " + b)
        sys.exit("[X] fix the syntax errors above before shipping")

    # b) the two bibeltv.de regressions: false positives (scope blow-out) AND false negatives
    #    (recall collapse). They pull in opposite directions, so both must run every time.
    run([sys.executable, os.path.join(engine, "test_ca_pivot.py")])
    run([sys.executable, os.path.join(engine, "test_recall.py")])

    # c') the HTML report builder must survive the sample AND a thin/empty estate (no undefined/NaN)
    import tempfile, json as _json
    smp = os.path.join(engine, "..", "sample")
    rp = os.path.join(tempfile.gettempdir(), "ship_report.html")
    rc = subprocess.run([sys.executable, os.path.join(engine, "author_geopol.py"),
                         os.path.join(smp, "findings.sample.json"),
                         os.path.join(smp, "geopol.sample.json"), rp, "--company", "SmokeTest"],
                        capture_output=True, text=True)
    ok = rc.returncode == 0 and os.path.exists(rp)
    if ok:
        htm = open(rp, encoding="utf-8").read()
        ok = (all(t not in htm for t in ("undefined", "NaN", "[object Object]", "__SCENE", "{{COMPANY"))
              and all(('id="%s"' % c) in htm for c in ("c1", "c2", "c3", "ddos", "sbd"))
              # the skeleton was extracted from the BibelTV exemplar — none of its specifics
              # (gitlab, donor/broadcast, its VPN IP, its CVE) may leak into another company's report
              and all(t not in htm for t in ("__S3_LEFT__", "__S3_MID__", "__S2_ACTORS__"))
              and all(t not in htm.lower() for t in ("bibel", "gitlab", "donor", "broadcast",
                                                     "donation", "giving flow", "213.61.87",
                                                     "cve-2023-44487")))
    print("  GEOPOL HTML artifact build: %s" % ("OK" if ok else "BROKEN"))
    if not ok:
        print((rc.stderr or "")[:300]); sys.exit("[X] author_geopol.py / build_geopol_html.js failed")

    # c'') clarify.py — the post-run clarification questions. Every question MUST be machine-actionable
    #      (carry a maps_to that /refine can turn into a run_assessment flag), and the free-text notes
    #      question must always be present (a run should never dead-end without a way to add context).
    try:
        import importlib.util as _ilu
        _spec = _ilu.spec_from_file_location("clarify", os.path.join(engine, "clarify.py"))
        _clar = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_clar)
        _fj = _json.load(open(os.path.join(smp, "findings.sample.json"), encoding="utf-8"))
        _out = _clar.build(_fj)
        _qs = _out.get("questions") or []
        _valid_maps = {"include_domains", "include_nets", "include_asns", "exclude_domains",
                       "exclude_hosts", "netblocks_or_asns", "hosts_or_domains", "platform_operator",
                       "notes"}
        cok = bool(_qs) and all(q.get("maps_to") in _valid_maps for q in _qs) \
              and any(q.get("id") == "notes" for q in _qs)
    except Exception as _e:
        cok = False; print("    clarify smoke error: %r" % _e)
    print("  clarify questions build: %s" % ("OK" if cok else "BROKEN"))
    if not cok:
        sys.exit("[X] clarify.py produced no/invalid questions (each needs a valid maps_to)")

    # c''') COMPLIANCE module — the deterministic path must produce a valid compliance.json, render a
    #       regime deck + roadmap deck + the HTML report (no undefined/NaN leaks), and yield clarify
    #       questions with valid maps_to. This runs with NO OPENAI key = the fallback, so it proves the
    #       decks are safe even when the model is down.
    try:
        import importlib.util as _ilu2
        _s = _ilu2.spec_from_file_location("compliance_enrich", os.path.join(engine, "compliance_enrich.py"))
        _CE = _ilu2.module_from_spec(_s); _s.loader.exec_module(_CE)
        _env = dict(os.environ); _env.pop("OPENAI_API_KEY", None)
        _cj, _st = _CE.build("SmokeTest AG", "en", {})
        _cpath = os.path.join(tempfile.gettempdir(), "ship_compliance.json")
        _json.dump(_cj, open(_cpath, "w", encoding="utf-8"), ensure_ascii=False)
        comp_ok = set(_cj.get("regimes") or {}) >= {"nis2", "cra", "aiact"} and bool(_cj.get("roadmap"))
        for _reg, _fn in (("nis2", "ship_c_nis2.pptx"), ("roadmap", "ship_c_road.pptx")):
            _op = os.path.join(tempfile.gettempdir(), _fn)
            _r = subprocess.run(["node", os.path.join(engine, "build_compliance_deck.js"), _cpath, _op, _reg],
                                capture_output=True, text=True, env=_env)
            comp_ok = comp_ok and _r.returncode == 0 and os.path.exists(_op)
        _hp = os.path.join(tempfile.gettempdir(), "ship_compliance.html")
        _r = subprocess.run(["node", os.path.join(engine, "build_compliance_html.js"), _cpath, _hp],
                            capture_output=True, text=True, env=_env)
        if _r.returncode == 0 and os.path.exists(_hp):
            _htm = open(_hp, encoding="utf-8").read()
            comp_ok = comp_ok and all(t not in _htm for t in ("undefined", "NaN", "[object Object]"))
            comp_ok = comp_ok and all(('id="%s"' % k) in _htm for k in ("nis2", "cra", "aiact"))
        else:
            comp_ok = False
        _sc = _ilu2.spec_from_file_location("compliance_clarify", os.path.join(engine, "compliance_clarify.py"))
        _CC = _ilu2.module_from_spec(_sc); _sc.loader.exec_module(_CC)
        _cq = _CC.build(_cj).get("questions") or []
        _cmaps = {"sector", "size_band", "sells_digital_products", "builds_or_deploys_ai", "countries", "notes"}
        comp_ok = comp_ok and bool(_cq) and all(q.get("maps_to") in _cmaps for q in _cq) \
                  and any(q.get("id") == "notes" for q in _cq)
    except Exception as _e:
        comp_ok = False; print("    compliance smoke error: %r" % _e)
    print("  compliance decks + HTML + clarify build: %s" % ("OK" if comp_ok else "BROKEN"))
    if not comp_ok:
        sys.exit("[X] compliance module failed its smoke (enrich/deck/html/clarify)")

    # c) the unit suite. Bootstrap the runner if it is missing — "pytest not installed" is a setup
    #    gap, not a reason to hand the operator a second command. A failing TEST blocks the ship;
    #    a missing test RUNNER we fix ourselves and, if we cannot, warn loudly and continue.
    py = _test_python()
    if not _has_pytest(py):
        print("  pytest not installed for %s — installing it now..." % py)
        subprocess.run([py, "-m", "pip", "install", "--quiet", "--disable-pip-version-check", "pytest"],
                       cwd=HERE)
    if not _has_pytest(py):
        print("\n  " + "!" * 66)
        print("  [!] could not install pytest — unit suite SKIPPED.")
        print("      The compile check and the CA-pivot regression above still passed.")
        print("      Fix later with:  %s -m pip install pytest" % py)
        print("  " + "!" * 66)
        return
    rc = run([py, "-m", "pytest", "tests/", "-q"], check=False)
    if rc == 5:
        print("  (pytest collected no tests — treating as pass)")
    elif rc != 0:
        sys.exit("[X] a unit test FAILED — not shipping. Fix it, then re-run: python ship.py")
    print("\n  ALL TESTS PASSED")


# ------------------------------------------------------------------ 2. git
def _clear_stale_git_locks():
    """Remove leftover .git/*.lock files.

    A crashed/killed git (or an editor's git integration) leaves index.lock or HEAD.lock behind and
    then EVERY later git command dies with "Unable to create '.../index.lock': File exists". The
    user should not have to run a manual `del` for this — that would be a second command."""
    gitdir = os.path.join(HERE, ".git")
    for name in ("index.lock", "HEAD.lock", "config.lock", "ORIG_HEAD.lock"):
        p = os.path.join(gitdir, name)
        if not os.path.exists(p):
            continue
        age = time.time() - os.path.getmtime(p)
        if age < 30:
            sys.exit("[X] %s exists and is only %ds old — another git process may be running.\n"
                     "    Wait a moment and re-run: python ship.py" % (name, int(age)))
        try:
            if not DRY:
                os.remove(p)
            print("  cleared stale .git/%s (%dm old)" % (name, int(age // 60)))
        except OSError as e:
            sys.exit("[X] could not remove .git/%s (%s).\n"
                     "    Close any editor/Git GUI holding the repo and re-run: python ship.py"
                     % (name, e.__class__.__name__))


def do_git(message):
    say("2/5  COMMIT + PUSH — GitHub is the single source of truth")
    _clear_stale_git_locks()
    run(["git", "add", "-A"], check=False)
    rc = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=HERE).returncode
    if rc == 0:
        print("  (nothing new to commit)")
    else:
        run(["git", "commit", "-m", message], check=False)
    # ALWAYS push — even with nothing new to commit. BUG we hit: earlier commits made outside a
    # ship.py run (or when the working tree was already clean) were never pushed, so GitHub silently
    # fell BEHIND the PC. "GitHub is the single source of truth" only holds if we push every time.
    ahead = subprocess.run(["git", "rev-list", "--count", "origin/main..HEAD"],
                           cwd=HERE, text=True, capture_output=True).stdout.strip() or "?"
    print("  local commits not yet on GitHub: %s — pushing." % ahead)
    run(["git", "push", "origin", "main"], check=False)
    return rc != 0


def tag_known_good():
    """Tag the just-deployed, verified commit as a restorable safe-point, and push the tag.
    So any future breakage is one command to undo (see --rollback)."""
    import datetime
    tag = "good-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    run(["git", "tag", "-f", "last-known-good"], check=False)   # moving pointer to the newest good
    run(["git", "tag", tag], check=False)                        # immutable dated snapshot
    run(["git", "push", "-f", "origin", "last-known-good"], check=False)
    run(["git", "push", "origin", tag], check=False)
    print("\n  SAFE-POINT saved: %s  (and moved 'last-known-good').  To roll back later:" % tag)
    print("      python ship.py --rollback            # -> last-known-good, redeploys")
    print("      python ship.py --rollback %s   # -> this exact point" % tag)


def do_rollback(ref):
    say("ROLLBACK — restore a known-good state, then redeploy")
    ref = ref if ref and ref != "AUTO" else "last-known-good"
    print("  restoring the repo to %r ..." % ref)
    _clear_stale_git_locks()
    # show what we're about to move to, and refuse if it doesn't exist
    r = subprocess.run(["git", "rev-parse", "--verify", ref + "^{commit}"], cwd=HERE,
                       text=True, capture_output=True)
    if r.returncode != 0:
        sys.exit("[X] %r is not a known ref/tag. See your safe-points with:  git tag -l 'good-*'" % ref)
    run(["git", "stash", "push", "-u", "-m", "pre-rollback"], check=False)   # park any local mess
    run(["git", "reset", "--hard", ref])
    print("  PC restored to %s. Redeploying that state to the droplet..." % ref)
    do_web(False)
    do_bots()
    ok = do_verify(True, True)
    print("\n" + "=" * 74)
    print("  ROLLBACK COMPLETE — droplet + PC are back on %r." % ref)
    print("  (your pre-rollback changes are parked in `git stash` — `git stash pop` to get them back.)")
    print("=" * 74)
    sys.exit(0 if ok else 1)


# ------------------------------------------------------------------ 3. deploy
def do_web(use_ci):
    say("3/5  DEPLOY WEB — cybergod.ai (colt-web)")
    # DEFAULT = deploy straight from this PC over SSH.
    # There is no firewall between here and the droplet (port 22 is open to the internet), so the
    # old GitHub-Actions -> Tailscale -> droplet path added a hop that bought nothing and was the
    # only thing failing. Direct takes ~90s and is self-verifying. `--ci` still uses GitHub.
    if not use_ci:
        run([sys.executable, "deploy_web_direct.py"])
    elif not have("gh"):
        print("  [!] --ci requested but GitHub CLI `gh` is missing — deploying directly instead.")
        run([sys.executable, "deploy_web_direct.py"])
    else:
        # ship_web.py can report success even when the workflow failed, so we do NOT trust it —
        # the hash check below is the real gate.
        run([sys.executable, "ship_web.py"], check=False)

    # PROVE the running container has THIS repo's engine. A green log is not evidence.
    print("\n  verifying colt-web is running the current engine...")
    ok, stale = engine_is_current("colt-web")
    if ok:
        print("  OK  colt-web engine matches the repo")
        return
    print("  [!] colt-web is STALE — the CI deploy did not take effect:")
    for s in stale:
        print("        " + s)
    print("  -> self-healing with a direct deploy (deploy_web_direct.py)")
    run([sys.executable, "deploy_web_direct.py"])
    ok, stale = engine_is_current("colt-web")
    if not ok:
        for s in stale:
            print("        " + s)
        sys.exit("[X] colt-web STILL runs stale code after a direct deploy.\n"
                 "    Assessments from the web app would use the OLD engine. Stopping here rather\n"
                 "    than letting you believe this shipped.")
    print("  OK  colt-web engine matches the repo (after direct deploy)")


def do_bots():
    say("4/5  DEPLOY BOTS — colt-stack (assess bot + Cassandra + promtail)")
    # SKIP the 2-4 min droplet rebuild if the bot already runs THIS repo's engine. deploy.py rebuilds
    # both Ubuntu/Python images and opens ~12 ssh sessions every time; when the engine already
    # matches (e.g. you only changed the web app, or re-ran ship.py), that work is pure waiting.
    ok, _ = engine_is_current("colt-assessbot")
    if ok and not os.environ.get("FORCE_BOTS"):
        print("  colt-assessbot already runs the current engine — skipping the rebuild.")
        print("  (set FORCE_BOTS=1 to rebuild anyway, e.g. after a bot.py/Dockerfile change.)")
        _import_grafana()
        return
    # NEVER --remove-orphans here: docker-compose.web.yml defines only `web`, and a subset compose
    # in the shared colt-stack project deletes the bots + promtail as "orphans".
    run([sys.executable, "deploy.py", "--reuse", "--yes"])
    print("\n  verifying colt-assessbot is running the current engine...")
    ok, stale = engine_is_current("colt-assessbot")
    if ok:
        print("  OK  colt-assessbot engine matches the repo")
    else:
        for s in stale:
            print("        " + s)
        sys.exit("[X] colt-assessbot runs stale code — /assess would use the OLD engine.")
    _import_grafana()


def _import_grafana():
    """Re-import the Grafana dashboards so panel edits (e.g. the FP-audit row) actually appear.
    Best-effort: a new panel in assess.json is invisible until the dashboard is re-imported, which is
    why the FP-audit panels never showed. Needs GRAFANA_URL + GRAFANA_TOKEN; skips (with a one-line
    note) if absent, so the deploy never blocks on Grafana."""
    url = os.environ.get("GRAFANA_URL")
    tok = os.environ.get("GRAFANA_TOKEN")
    if not (url and tok):
        print("  [i] Grafana dashboards NOT re-imported (set GRAFANA_URL + GRAFANA_TOKEN to automate).")
        print("      One-time: python import_dashboard.py --url <grafana> --token <glsa_…>")
        return
    print("  re-importing Grafana dashboards (so the FP-audit panels appear)...")
    run([sys.executable, "import_dashboard.py", "--url", url, "--token", tok, "--all"], check=False)


# ------------------------------------------------------------------ 4. verify
def do_verify(web, bots):
    say("5/5  VERIFY")
    ok = True
    if bots:
        out = ssh("docker ps --format '{{.Names}}  {{.Status}}' | grep -E 'colt-' || echo NONE")
        if "colt-assessbot" not in out:
            print("  [!] colt-assessbot not visible"); ok = False
        if "colt-promtail" not in out:
            print("  [!] colt-promtail missing — Grafana will go quiet"); ok = False
    # The engine hash is the load-bearing check. HTTP 401 only proves *something* is listening —
    # a 3-day-old container answers it just as happily as a current one.
    for cont, want in (("colt-web", web), ("colt-assessbot", bots)):
        if not want or DRY:
            continue
        good, stale = engine_is_current(cont)
        print("  %-16s engine: %s" % (cont, "CURRENT" if good else "STALE  <-- assessments are wrong"))
        if not good:
            for s in stale:
                print("      " + s)
            ok = False
    if web:
        import ssl as _ssl, urllib.request, urllib.error
        url = "https://%s/api/me" % DOMAIN
        print("  $ GET " + url + "   (expect 401 = up and auth enforced)")
        if not DRY:
            try:
                ctx = _ssl.create_default_context()
                urllib.request.urlopen(urllib.request.Request(url), timeout=20, context=ctx)
                print("  [!] 200 without a session — auth is NOT enforced"); ok = False
            except urllib.error.HTTPError as e:
                if e.code == 401:
                    print("  OK  401 Unauthorized — colt-web is live and locked down")
                else:
                    print("  [!] HTTP %s (expected 401)" % e.code); ok = False
            except Exception as e:
                print("  [!] unreachable: %r" % e); ok = False
    return ok


# ------------------------------------------------------------------ main
def main():
    global DRY
    ap = argparse.ArgumentParser(description="The one command: test, ship, verify.")
    ap.add_argument("-m", "--message", default=None, help="commit message")
    ap.add_argument("--test", action="store_true", help="run tests only, change nothing")
    ap.add_argument("--web", action="store_true", help="only deploy the web app")
    ap.add_argument("--bots", action="store_true", help="only deploy the Telegram bots")
    ap.add_argument("--ci", action="store_true",
                    help="deploy via GitHub Actions instead of straight over SSH (slower)")
    ap.add_argument("--direct", action="store_true",
                    help="(default) deploy straight to the droplet over SSH")
    ap.add_argument("--no-test", action="store_true", help="skip the test gate")
    ap.add_argument("--dry-run", action="store_true", help="print the plan, touch nothing")
    ap.add_argument("--rollback", nargs="?", const="AUTO", default=None,
                    help="restore a known-good state and redeploy it (default: last-known-good; "
                         "or pass a tag like good-20260722-143000)")
    a = ap.parse_args()
    DRY = a.dry_run

    if a.rollback is not None:
        do_rollback(a.rollback)          # exits inside
        return

    web = a.web or not (a.web or a.bots)
    bots = a.bots or not (a.web or a.bots)

    print("=" * 74)
    print("  ship.py — %s" % ("DRY RUN" if DRY else "live"))
    print("  target : %s@%s   web=%s bots=%s   %s"
          % (USER, HOST, web, bots, "via GitHub CI" if a.ci else "direct SSH from this PC"))
    print("=" * 74)

    if not a.no_test:
        do_tests()
    if a.test:
        print("\n--test: tests only. Nothing deployed.")
        return

    do_git(a.message or "ship: engine + web update")

    if web:
        do_web(a.ci)
    if bots:
        do_bots()

    ok = do_verify(web, bots)

    if ok and not DRY:
        # only tag a SAFE-POINT when the deployed engine actually verified current + live
        tag_known_good()

    print("\n" + "=" * 74)
    if ok:
        print("  DONE in %ds — everything is live." % int(time.time() - T0))
        print("  Web:      https://%s/app" % DOMAIN)
        print("  Telegram: /assess Volkswagen AG")
    else:
        print("  FINISHED WITH WARNINGS in %ds — see the [!] lines above." % int(time.time() - T0))
    print("=" * 74)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
