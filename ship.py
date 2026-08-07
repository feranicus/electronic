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
    hermes-skills/.../test_scope_abakus.py     scope regression (abakus wa.me -> 236 Meta hosts)
    author_geopol.py + build_geopol_html.js    the 5th deliverable (GEOPOL HTML) renders
    py_compile over every engine script        catches the truncation/syntax class of bug
    ship_web.py                                web: build -> GHCR -> Actions -> droplet -> Caddy
    deploy.py --reuse --yes                    bots: rebuild + redeploy colt-stack
    deploy_web_direct.py                       web: build on the droplet over SSH (DEFAULT)
"""
import argparse, base64, os, subprocess, sys, time

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


def ssh(cmd, check=False, timeout=180):
    # `timeout` was being PASSED by do_verify's model probe but the signature never accepted it, so
    # that call raised TypeError inside a try/except and the probe silently never ran. A check that
    # cannot execute is not a check — the same class as the ruff gate that skipped for weeks.
    print("  $ ssh %s@%s %r" % (USER, HOST, cmd[:70]), flush=True)
    if DRY:
        return ""
    # HARD TIMEOUT. CLAUDE.md already mandates this for every ssh in every script — ship.py's own
    # helper never got it, and a remote command that hangs (sshd throttling after ~12 rapid
    # sessions, or a slow docker restart) froze the deploy with no output and no way to tell why.
    try:
        r = subprocess.run(SSH + ["%s@%s" % (USER, HOST), cmd], text=True, capture_output=True,
                           timeout=180)
    except subprocess.TimeoutExpired:
        print("    [!] ssh TIMED OUT after 180s: %s" % cmd[:90])
        if check:
            sys.exit("[X] remote command timed out: %s" % cmd[:120])
        class _R:                       # keep the caller's contract; a timeout is not a crash
            stdout, stderr, returncode = "", "timeout", 124
        r = _R()
    if r.stdout.strip():
        print("    " + r.stdout.rstrip().replace("\n", "\n    "))
    if check and r.returncode != 0:
        sys.exit("[X] remote failed: %s\n%s" % (cmd, r.stderr[:400]))
    return r.stdout


def ssh_script(script, timeout=180, check=False):
    """Run a MULTI-LINE bash script on the droplet in ONE ssh session.

    WHY THIS EXISTS — researched, not guessed:
      * The Windows OpenSSH client has NO ControlMaster/ControlPersist multiplexing
        (PowerShell/Win32-OpenSSH issue #1328 is still open), so the usual fix — reuse one TCP
        connection for every command — is simply unavailable on the operator's machine. Each ssh()
        is a full TCP + key exchange + auth handshake.
      * OpenSSH 9.8 (Jul 2024) enables `PerSourcePenalties` by DEFAULT: sshd records a penalty
        against a source address for connections that do not complete as expected, penalties ACCRUE
        with repetition, and further connections from that address are refused while a penalty is
        live. Add `MaxStartups` (default 10:30:100) and a burst of short-lived sessions from one IP
        is exactly the shape both mechanisms exist to damp.
    So the only lever available is: OPEN FEWER SESSIONS. CLAUDE.md has said "prefer the
    single-connection pattern for anything new" since deploy.py hit this wall; deploy_web_direct.py
    already does its whole deploy in ONE session and has never hung. This helper makes that pattern
    available to every other step.

    The script is base64'd so no quoting layer (PowerShell -> ssh -> remote bash) can corrupt nested
    quotes — the same trick deploy_web_direct.py uses for its payload."""
    b64 = base64.b64encode(script.encode("utf-8")).decode("ascii")
    return ssh("echo %s | base64 -d | bash" % b64, check=check, timeout=timeout)


def _sections(out, names):
    """Split ssh_script output on '#### <NAME>' delimiters -> {name: text}."""
    got = {n: "" for n in names}
    cur = None
    for line in (out or "").splitlines():
        if line.startswith("#### "):
            cur = line[5:].strip()
            continue
        if cur in got:
            got[cur] += line + "\n"
    return got


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
                "scripts/compliance_assess.py", "scripts/compliance_enrich.py",
                "scripts/creed.js", "scripts/group_discovery.py", "scripts/engine_config.py",
                "scripts/enrich_parallel.py", "scripts/attribution.py",
                "scripts/model_probe.py", "scripts/demo_build.py",
                # scope_deny.py is the authoritative shortener/social/platform denylist. It is a
                # SCOPE-CORRECTNESS file: a container running an older copy would happily admit
                # wa.me again (the abakus-tk.de failure), so its hash has to be proved deployed.
                "scripts/scope_deny.py", "scripts/psl.py", "scripts/asn_sources.py", "scripts/clarify.py"]
ENGINE_LOCAL = os.path.join(HERE, "hermes-skills", "shodan-assessment")
ENGINE_REMOTE = "/opt/shodan-skill"


def _sha_local(rel):
    import hashlib
    p = os.path.join(ENGINE_LOCAL, rel.replace("/", os.sep))
    if not os.path.exists(p):
        return None
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


_SHA_CACHE = {}                       # container -> {relpath: sha}, for ONE ship.py run


def _sha_all_in_container(container, fresh=False):
    """sha256 of EVERY ENGINE_FILE inside a running container, in ONE ssh + ONE docker exec.

    MEMOISED PER RUN, and that is the fix for a real hang. `engine_is_current()` was called FIVE
    times in one ship (colt-web twice, colt-assessbot three times) — deploy, self-heal check, bots
    skip-check, and then AGAIN in 5/5 VERIFY. Each call is a fresh ssh + docker exec, and sshd
    throttles rapid repeat connections (MaxStartups / PerSourcePenalties): the run froze for
    minutes on the last redundant probe, after everything had already succeeded.
    The hashes cannot change between two probes in the same run unless we redeployed that container
    in between — and the deploy paths pass `fresh=True` to invalidate. Everything else reuses the
    answer we already paid for. Same doctrine as "prefer the single-connection pattern".

    WHY one call: the old code opened one ssh PER FILE. sshd throttles rapid repeat connections, so
    growing ENGINE_FILES (e.g. adding the compliance engine) pushed the per-file loop past the throttle
    threshold and the whole ship HUNG mid-verify. Hashing all files in a single remote python keeps the
    connection count flat no matter how many files we verify. The remote code is a SINGLE line (no
    newlines, no double quotes) so it survives ssh's shell quoting; missing files report 'MISSING'."""
    if not fresh and container in _SHA_CACHE:
        return _SHA_CACHE[container]
    code = ("import hashlib,os;b=%r;fs=%r;"
            "print(chr(10).join(r+' '+(hashlib.sha256(open(os.path.join(b,r),'rb').read()).hexdigest() "
            "if os.path.exists(os.path.join(b,r)) else 'MISSING') for r in fs))"
            % (ENGINE_REMOTE, list(ENGINE_FILES)))
    # A READ-ONLY probe must fail fast: 180s of silence teaches the operator to distrust the tool.
    out = ssh("docker exec %s python3 -c \"%s\" 2>/dev/null || true" % (container, code), timeout=60)
    got = {}
    for line in (out or "").splitlines():
        parts = line.strip().split(" ")
        if len(parts) == 2 and "/" in parts[0]:
            got[parts[0]] = parts[1]
    if got:                          # never cache an empty answer (a throttled ssh returns nothing)
        _SHA_CACHE[container] = got
    return got


def _prime_sha_cache(containers):
    """Hash the engine in SEVERAL containers in ONE ssh session, into _SHA_CACHE.

    Two probes that ask different containers the same question are still two handshakes, and on a
    link with no multiplexing and per-source penalties that is the cost that hurts. Ask once."""
    want = [c for c in containers if c not in _SHA_CACHE]
    if not want or DRY:
        return
    code = ("import hashlib,os;b=%r;fs=%r;"
            "print(chr(10).join(r+' '+(hashlib.sha256(open(os.path.join(b,r),'rb').read()).hexdigest() "
            "if os.path.exists(os.path.join(b,r)) else 'MISSING') for r in fs))"
            % (ENGINE_REMOTE, list(ENGINE_FILES)))
    script = "\n".join("echo '#### %s'; docker exec %s python3 -c \"%s\" 2>/dev/null || true"
                       % (c, c, code) for c in want)
    sec = _sections(ssh_script(script, timeout=120), want)
    for c in want:
        got = {}
        for line in sec.get(c, "").splitlines():
            bits = line.strip().split(" ")
            if len(bits) == 2 and "/" in bits[0]:
                got[bits[0]] = bits[1]
        if got:
            _SHA_CACHE[c] = got


def engine_is_current(container, fresh=False):
    """-> (ok, [list of stale files]). Proves the container runs THIS repo's engine.

    `fresh=True` after a (re)deploy of that container; otherwise the per-run cache answers, so a
    single ship opens ONE session per container instead of five."""
    got = _sha_all_in_container(container, fresh=fresh)
    stale = []
    for rel in ENGINE_FILES:
        want = _sha_local(rel)
        if not want:
            continue
        have = got.get(rel, "MISSING")
        if have != want:
            stale.append("%s (container=%s repo=%s)" % (rel, have[:12], want[:12]))
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
    #     EVERY language the shell has a dictionary for is built, not just English. This artifact has
    #     already shipped a bare skeleton with empty <h1></h1> while printing success once; a
    #     localisation layer is exactly the kind of change that reintroduces that in ONE language and
    #     leaves the others green. The language list is DERIVED from the files on disk (same doctrine
    #     as deck_langs.py), so dropping in geopol_html/i18n/de.json gates German with no edit here.
    import tempfile, json as _json, re as _re
    smp = os.path.join(engine, "..", "sample")
    _gpi = os.path.join(engine, "geopol_html", "i18n")
    _gp_langs = ["en"] + sorted(f[:-5] for f in (os.listdir(_gpi) if os.path.isdir(_gpi) else [])
                                if f.endswith(".json") and f != "en.json")
    ok, _htm_en = True, None
    for _lang in _gp_langs:
        rp = os.path.join(tempfile.gettempdir(), "ship_report_%s.html" % _lang)
        rc = subprocess.run([sys.executable, os.path.join(engine, "author_geopol.py"),
                             os.path.join(smp, "findings.sample.json"),
                             os.path.join(smp, "geopol.sample.json"), rp, "--company", "SmokeTest"],
                            capture_output=True, text=True, env=dict(os.environ, DECK_LANG=_lang))
        lok = rc.returncode == 0 and os.path.exists(rp)
        if lok:
            htm = open(rp, encoding="utf-8").read()
            lok = (all(t not in htm for t in ("undefined", "NaN", "[object Object]", "__SCENE", "{{COMPANY"))
                   and all(('id="%s"' % c) in htm for c in ("c1", "c2", "c3", "ddos", "sbd"))
                   # a heading that renders EMPTY is the historic failure mode — a file existing is
                   # not a file being right
                   and not _re.search(r"<(h1|h2)[^>]*>\s*</\1>", htm) and "SmokeTest" in htm
                   # the two scene-04 animation LOOKUP KEYS must survive localisation: they are
                   # compared with === / indexOf, so translating them silently breaks the animation
                   and '"SASE · ZTNA"' in htm and "'EGRESS'" in htm
                   # nothing customer-facing may name a carrier (Cybergod LLC / S4Biz rebrand)
                   and "colt" not in htm.lower() and "ip guardian" not in htm.lower()
                   # the skeleton was extracted from the BibelTV exemplar — none of its specifics
                   # (gitlab, donor/broadcast, its VPN IP, its CVE) may leak into another company's report
                   and all(t not in htm for t in ("__S3_LEFT__", "__S3_MID__", "__S2_ACTORS__"))
                   and all(t not in htm.lower() for t in ("bibel", "gitlab", "donor", "broadcast",
                                                          "donation", "giving flow", "213.61.87",
                                                          "cve-2023-44487")))
            if _lang == "en":
                _htm_en = htm
            elif lok:
                # A DICTIONARY THAT CHANGES NOTHING IS A DICTIONARY THAT WAS NEVER APPLIED — the
                # exact way a translation gate goes green while shipping English. Comparing against
                # the English build is NOT enough: the builder also rewrites <html lang>, so an
                # empty pack still produces a "different" file. Assert the translations themselves
                # are on the page. Templated entries (%(company)s, {{COMPANY}}) are substituted by
                # render time, so the bar is a MAJORITY, not every string.
                _p = _json.load(open(os.path.join(_gpi, _lang + ".json"), encoding="utf-8"))
                _vals = [v for sec in ("strings", "canvas") for v in (_p.get(sec) or {}).values()
                         if isinstance(v, str) and len(v) > 3]
                _hit = sum(1 for v in _vals if v in htm)
                if not _vals or _hit < 0.6 * len(_vals):
                    lok = False
                    print("    [X] DECK_LANG=%s: only %d/%d dictionary strings reached the page"
                          % (_lang, _hit, len(_vals)))
                # …and the other direction: the builder reports every skeleton string that fell
                # through to English. Add a paragraph to skeleton.html without translating it and
                # THIS is what stops it — the dictionary-hit ratio above never would, because a
                # string nobody keyed is absent from both the numerator and the denominator.
                if "UNTRANSLATED" in (rc.stderr or ""):
                    lok = False
                    print("    [X] DECK_LANG=%s: untranslated skeleton strings —\n%s"
                          % (_lang, "\n".join(l for l in rc.stderr.splitlines() if "i18n:" in l)[:900]))
        print("  GEOPOL HTML artifact build [%s]: %s" % (_lang, "OK" if lok else "BROKEN"))
        if not lok:
            print((rc.stderr or "")[:300])
        ok = ok and lok
    if not ok:
        sys.exit("[X] author_geopol.py / build_geopol_html.js failed")

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

    # LEGAL GUARD - a German Impressum (Sec. 5 DDG) must carry a real name, postal address and
    # phone number. An incomplete one is the classic Abmahnung risk, so make it impossible to
    # miss. Loud WARNING, not a hard fail: when to publish is the operator's call.
    try:
        _legal = open(os.path.join(HERE, 'webapp', 'frontend', 'src', 'legal.jsx'), encoding='utf-8').read()
        import re as _re
        _todo = len(_re.findall(r':\s*"TODO', _legal))   # only real field VALUES, not the comments
    except Exception:
        _todo = 0
    if _todo:
        print('\n  ' + '!' * 68)
        print('  [!] IMPRESSUM INCOMPLETE - %d field(s) still say TODO in' % _todo)
        print('      webapp/frontend/src/legal.jsx  ->  export const OPERATOR')
        print('      Germany requires a real name, postal address and reachable phone (Sec. 5 DDG).')
        print('      Publishing without them is legally actionable.')
        print('  ' + '!' * 68 + '\n')
    else:
        print('  legal: Impressum operator details complete')

    # c''''') STATIC UNDEFINED-NAME CHECK - the gate that would have stopped the angermann outage.
    #        I shipped `if seed_apex:` into run() where the local is named _seed_apex0. Every unit
    #        test passed because they exercised the HELPERS, not the module: NameError only fires
    #        when the line actually executes, and no test executed run(). ruff F821 finds it
    #        statically in under a second. F-rules only (pyflakes): real bugs, never style.
    #        F821=undefined name, F811=redefinition, F822=undefined export, F401 is excluded
    #        because unused imports are not outages.
    _lint = subprocess.run([sys.executable, '-m', 'ruff', 'check', '--no-cache',
                            '--select', 'F821,F811,F822', '--quiet',
                            os.path.join(engine, '.'),
                            os.path.join(HERE, 'webapp', 'backend', 'app'), HERE],
                           capture_output=True, text=True, timeout=180)
    if _lint.returncode not in (0,):
        _out = (_lint.stdout or '') + (_lint.stderr or '')
        if 'No module named' in _out or 'not found' in _out.lower():
            # A gate that silently skips is not a gate. This check is the one that would have
            # stopped the angermann NameError outage, and it was skipping on the operator's
            # machine every run. Install it once, automatically — "no manual steps" (principle 1).
            print('  ruff missing - installing it once so the static check cannot be skipped...')
            subprocess.run([sys.executable, '-m', 'pip', 'install', '--quiet', 'ruff'],
                           capture_output=True, text=True, timeout=300)
            _lint = subprocess.run([sys.executable, '-m', 'ruff', 'check', '--no-cache',
                                    '--select', 'F821,F811,F822', '--quiet',
                                    os.path.join(engine, '.'),
                                    os.path.join(HERE, 'webapp', 'backend', 'app'), HERE],
                                   capture_output=True, text=True, timeout=180)
            if _lint.returncode == 0:
                print('  static check: no undefined names (ruff installed)')
            else:
                _o2 = (_lint.stdout or '') + (_lint.stderr or '')
                if 'No module named' in _o2:
                    print('  [!] could not install ruff - static check SKIPPED. Run: pip install ruff')
                else:
                    print(_o2.strip()[:4000])
                    sys.exit('[X] undefined/duplicate names found - the angermann NameError class.')
        else:
            print(_out.strip()[:4000])
            sys.exit('[X] undefined/duplicate names found - this is the angermann NameError '
                     'class; it WILL crash at runtime. Fix before deploying.')
    else:
        print('  static check: no undefined names in engine, webapp or root scripts')

    # c''''''''') Print the RESOLVED config. The operator's own fix for three deploys of guessing:
    #             stop reading five files to answer 'which model will actually run?' — resolve it
    #             once, with provenance, and print it. Same payload is served at GET /api/diag.
    _dg = subprocess.run([sys.executable, os.path.join(engine, 'engine_config.py')],
                         capture_output=True, text=True, timeout=60)
    for _l in (_dg.stdout or '').splitlines():
        if _l.strip():
            print('  ' + _l)

    # STRIP THE LEGACY OVERRIDE FROM THE *LOCAL* .env FIRST.
    # CLAUDE.md's own landmine: `deploy.py --reuse` PACKS the local assess-bot/.env and extracts
    # it OVER the droplet's copy. So deleting ENRICH_MODEL on the droplet is undone by the very
    # next bots deploy — which is why the chain kept coming back as
    #   ['deepseek-3.2', 'kimi-k2.6', ...]  instead of the committed kimi-first order.
    # _chain() prepends a singular ENRICH_MODEL as the HEAD, silently reordering everything.
    # The repo is the source of truth; strip both forms locally, then the droplet copy follows.
    _lenv = os.path.join(HERE, 'assess-bot', '.env')
    if os.path.exists(_lenv):
        try:
            _lines = open(_lenv, encoding='utf-8').read().splitlines()
            _isover = lambda l: l.strip().startswith(('ENRICH_MODEL=', 'ENRICH_MODELS='))
            _keep = [l for l in _lines if not _isover(l)]
            if len(_keep) != len(_lines):
                _drop = [l.strip() for l in _lines if _isover(l)]
                open(_lenv, 'w', encoding='utf-8').write('\n'.join(_keep) + '\n')
                print('  local assess-bot/.env: removed %d stale chain override(s): %s'
                      % (len(_drop), ', '.join(_drop)))
                print('    (this is what kept reordering the chain after every bots deploy)')
            else:
                print('  local assess-bot/.env: no chain override - repo order will apply')
        except Exception as _e:
            print('  [!] could not clean local assess-bot/.env (%s)' % type(_e).__name__)

    # c'''''''') NOTHING may hardcode ENRICH_MODELS. docker-compose `environment:` BEATS
    #            `env_file`, so a value committed there silently outranks enrich.py::_FALLBACKS —
    #            that is exactly why gemma stayed at the head of the chain and deepseek-v4-flash
    #            was never once called, even after the repo chain was changed and deployed.
    _bad = []
    for _f in ('docker-compose.web.yml', 'docker-compose.reuse.yml'):
        _fp = os.path.join(HERE, _f)
        if not os.path.exists(_fp):
            continue
        for _ln in open(_fp, encoding='utf-8'):
            _st = _ln.strip()
            if _st.startswith('-') and 'ENRICH_MODELS=' in _st:
                _bad.append('%s: %s' % (_f, _st))
    if _bad:
        for _b in _bad:
            print('    ' + _b)
        sys.exit('[X] ENRICH_MODELS is hardcoded in compose - it will BEAT enrich.py::_FALLBACKS '
                 'and the committed chain will never run. Remove it.')
    print('  enrich chain: not hardcoded in compose - enrich.py::_FALLBACKS is authoritative')

    # DECK QUALITY GATE — the customer-facing artifact finally has a test. Renders real decks and
    # inspects OOXML geometry: text must fit its shape, boxes must not overlap, no undefined/NaN
    # leakage, no empty deck. The 4,000-character DATA SOURCE footer that produced 'all the
    # letters are on top of each other' is reproduced verbatim as the fixture.
    _dq = subprocess.run([sys.executable, os.path.join(engine, 'test_deck_quality.py')],
                         capture_output=True, text=True, timeout=300)
    if _dq.returncode != 0:
        print((_dq.stdout or '') + (_dq.stderr or ''))
        sys.exit('[X] deck quality gate failed - do not ship a deck that renders badly')
    print('  deck quality: text fits, no overlaps, no placeholder leakage')

    # ATTRIBUTION scorer — graded confidence must keep discriminating on the real angermann hosts.
    _at = subprocess.run([sys.executable, os.path.join(engine, 'attribution.py'), '--demo'],
                         capture_output=True, text=True, timeout=60,
                         env={**os.environ, 'SHODAN_API_KEY': os.environ.get('SHODAN_API_KEY', 'x')})
    _ao = _at.stdout or ''
    _bad_attr = []
    for _needle, _want in (('Passbolt', 'CONFIRMED'), ('NetBid (subsidiary)', 'CONFIRMED'),
                           ('LAW FIRM', 'REJECTED'), ('DENTIST', 'REJECTED'),
                           ('co-tenant', 'REJECTED')):
        _ln = next((l for l in _ao.splitlines() if _needle in l), '')
        if _want not in _ln:
            _bad_attr.append('%s -> expected %s, got: %s' % (_needle, _want, _ln.strip()[:80]))
    if _bad_attr:
        print(_ao)
        for _b in _bad_attr:
            print('    ' + _b)
        sys.exit('[X] attribution scorer regressed on the known angermann ground truth')
    print('  attribution: confidence bands correct on the real angermann hosts')

    # c''''''') PARITY — the acceptance test the operator asked for: the platform must not find
    #           LESS than his own manual Shodan filtering. Replays his real angermann.de exports
    #           (75 host:port) and asserts recall (subsidiaries, vendor-hosted tenants, the
    #           Passbolt vault, the netbid.io mail cluster) AND precision (co-tenants, the law
    #           firm, the dental practice) AND severity (a password vault is not 'standard service').
    _pa = subprocess.run([sys.executable, os.path.join(engine, 'test_parity.py')],
                         capture_output=True, text=True, timeout=180)
    if _pa.returncode != 0:
        print((_pa.stdout or '') + (_pa.stderr or ''))
        sys.exit('[X] PARITY FAILED - the platform disagrees with manual Shodan work. Do not ship.')
    print('  parity: engine matches the operator\'s manual Shodan harvest (recall + precision + severity)')

    # c'''''') EXECUTE run() — the test that was missing when the angermann NameError shipped.
    #          Every other engine test exercises HELPERS; a NameError only fires when the line
    #          actually runs. This drives shodan_recon.run() against a mocked Shodan API and
    #          asserts the co-tenant guard's behaviour on the real shared Colt /24.
    _rp = subprocess.run([sys.executable, os.path.join(engine, 'test_run_path.py')],
                         capture_output=True, text=True, timeout=120)
    if _rp.returncode != 0:
        print((_rp.stdout or '') + (_rp.stderr or ''))
        sys.exit('[X] run() path test failed - the engine would crash or mis-scope in production')
    print('  run() path: executes clean, co-tenant guard correct on the shared /24')

    # c''''''') THE ABAKUS-TK.DE SCOPE REGRESSION (2026-08). A 20-person telecoms reseller with one
    #           shared IONOS VIP was shipped a deck claiming 401 IPs across 42 ASNs and 49 countries,
    #           236 of them Meta's — all from ONE href in the site footer (`wa.me`, the WhatsApp
    #           shortener), because `/it-infrastruktur/` matched `struktur` as a bare substring and
    #           was read as a corporate group-structure page.
    #           This asserts all four fixes AND that none of them cost recall: the anchored page
    #           hints, the shared denylist, the ownership gate on group domains, and the per-domain
    #           contribution budget — which is the one that works even if the other three fail,
    #           because the poison arrived through an IDENTITY query and therefore poisoned the very
    #           baseline scope_blowout and the co-tenant guard measure against.
    _ab = subprocess.run([sys.executable, os.path.join(engine, 'test_scope_abakus.py')],
                         capture_output=True, text=True, timeout=180)
    if _ab.returncode != 0:
        print((_ab.stdout or '') + (_ab.stderr or ''))
        sys.exit('[X] SCOPE REGRESSION - a discovered domain can own the estate again. Do not ship.')
    print('  abakus scope: shorteners denied, group domains gated, per-domain budget enforced')

    # c'''''''') THE ABU DHABI POLICE CLASSIFY REGRESSION (2026-08). Three defects, all in data the
    #            engine already had: (1) `v.lstrip("-")` on Shodan's ssl.versions array stripped the
    #            NEGATION sign, so a TLS-1.2-only host was reported as offering TLS 1.0 — the widest
    #            false-positive source in the product's history, firing on essentially every host
    #            ever scanned; (2) the OpenText Media Management TEST instance was called "a mail
    #            service gateway" because the classifier read `port` and `product` instead of
    #            http.redirects; (3) the framework list cited NIS2, GDPR, TISAX and UNECE R155 at an
    #            Emirati police force — the third recurrence of D9/A7.
    _ap = subprocess.run([sys.executable, os.path.join(engine, 'test_classify_adpolice.py')],
                         capture_output=True, text=True, timeout=120)
    if _ap.returncode != 0:
        print((_ap.stdout or '') + (_ap.stderr or ''))
        sys.exit('[X] CLASSIFY REGRESSION - TLS negation / service identity / jurisdiction. Do not ship.')
    print('  adpolice classify: TLS sign respected, redirects read, frameworks follow jurisdiction')

    # c''''''''') THE ENTERPRISE ASN REGRESSION (Royal Bank of Canada, 2026-08). RBC announces at
    #             least twelve autonomous systems; the engine found TWO. Every discovery source was
    #             RIPE/DACH-shaped — ripe_db covers only the RIPE region and RBC is ARIN, caida
    #             returned nothing, bgpview does not resolve in the container, and PeeringDB lists
    #             only networks that peer publicly. Structurally blind on every North American,
    #             Asian and Gulf enterprise, i.e. on the accounts worth the most. This replays the
    #             real captured RIPEstat response and asserts both recall (7 RBC ASNs) and precision
    #             (Bosch, Raiffeisenbank and a Catholic college share the handle prefix and must not
    #             be adopted).
    _ae = subprocess.run([sys.executable, os.path.join(engine, 'test_asn_enterprise.py')],
                         capture_output=True, text=True, timeout=120)
    if _ae.returncode != 0:
        print((_ae.stdout or '') + (_ae.stderr or ''))
        sys.exit('[X] ASN DISCOVERY REGRESSION - an enterprise estate would be truncated. Do not ship.')
    print('  enterprise ASNs: global source first, holder-corroborated, cap 40')

    # c''''') THE DRIFT CHECK ITSELF. Its first version md5'd `caddy adapt` against the admin API's
    #        `GET /config/` and failed a HEALTHY staging box twice, blocking a deploy on a defect
    #        that did not exist. Those are two serialisations of one config, so byte equality was
    #        never achievable. The tell was in the check's own output: the hashes were identical
    #        BEFORE and AFTER a reboot, and a reboot is exactly what fixes a genuinely stale Caddy.
    #        It now compares what is SERVED. This test pins both directions so the gate can never
    #        again cry wolf, and can never again miss the 2026-08-07 shape.
    _dr = subprocess.run([sys.executable, os.path.join(engine, 'test_drift.py')],
                         capture_output=True, text=True, timeout=60)
    if _dr.returncode != 0:
        print((_dr.stdout or '') + (_dr.stderr or ''))
        sys.exit('[X] DRIFT CHECK REGRESSION - the staging gate would block or miss wrongly. Do not ship.')
    print('  config drift: healthy box never flagged, truncated/wrong-handler always caught')

    # c'''') The creed (the Cassandra line) sits on the cover of all five decks and is translated by
    #       TWO independent paths: deck_i18n/de.json for the four security builders, and creed.js
    #       itself for build_compliance_deck.js (which has no deck_i18n). test_creed.js pins them
    #       together so one family can never silently ship different German.
    _cr = subprocess.run(['node', os.path.join(engine, 'test_creed.js')],
                         capture_output=True, text=True, timeout=60)
    if _cr.returncode != 0:
        print(_cr.stdout + _cr.stderr)
        sys.exit('[X] creed check failed - the Cassandra line drifted between de.json and creed.js')
    print('  creed: Cassandra line pinned EN + DE')

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

    # c'''') PUBLIC DEMO — "Trojan Empire". This one is customer-facing to ANONYMOUS visitors, which
    #        makes two properties non-negotiable and therefore testable:
    #          1. the artifacts BUILD (a demo that 404s is worse than no demo — it is the first thing
    #             a prospect clicks, and /api/demo builds lazily so a broken builder shows as an
    #             empty page rather than an error anyone would notice);
    #          2. every IP is inside an RFC 5737 documentation range. That is the whole safety story.
    #             If a real address ever leaks into the fixture we are publishing an unsolicited
    #             exposure claim about a stranger's host, worldwide, with no authorisation.
    #        Both are cheap to check and expensive to get wrong, so they block the ship.
    try:
        import glob as _glob, zipfile as _zipfile, re
        _dout = os.path.join(tempfile.gettempdir(), "ship_demo")
        _r = subprocess.run([sys.executable, os.path.join(engine, "demo_build.py"), "--out", _dout],
                            capture_output=True, text=True, timeout=420)
        _dfiles = sorted(_glob.glob(os.path.join(_dout, "*.pptx")) +
                         _glob.glob(os.path.join(_dout, "*.html")))
        demo_ok = _r.returncode == 0 and len(_dfiles) >= 4
        if not demo_ok:
            print("    demo build rc=%s out=%s" % (_r.returncode, (_r.stderr or _r.stdout)[-300:]))

        # Pull every dotted quad out of the fixture SOURCE (not the rendered pptx — a version string
        # like 1.24.0 is not an address, and the source is where a mistake would actually be made).
        _dsrc = open(os.path.join(engine, "demo_build.py"), encoding="utf-8").read()
        _ips = set(re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", _dsrc))
        _docnet = ("192.0.2.", "198.51.100.", "203.0.113.")     # RFC 5737 TEST-NET-1/2/3
        _real = sorted(i for i in _ips
                       if not i.startswith(_docnet)
                       and not re.match(r"^\d+\.\d+\.\d+$", i))  # (belt and braces)
        if _real:
            demo_ok = False
            print("    !! demo fixture contains NON-documentation IPs: %s" % _real[:8])

        # The fabrication notice must physically reach the artifacts, not just the web page. A deck
        # forwarded by email loses every bit of surrounding context the /demo page provides.
        if demo_ok:
            _pptx = [f for f in _dfiles if f.endswith(".pptx")]
            _txt = ""
            for _f in _pptx:
                _z = _zipfile.ZipFile(_f)
                _txt += " ".join("".join(re.findall(r"<a:t>(.*?)</a:t>",
                                                    _z.read(_n).decode("utf8"), re.S))
                                 for _n in _z.namelist()
                                 if re.match(r"ppt/slides/slide\d+\.xml$", _n))
            demo_ok = ("FABRICATED" in _txt.upper()) and ("Trojan Empire" in _txt)
            if not demo_ok:
                print("    !! demo decks do not carry the FABRICATED notice on any slide")

        # And the HTML must be POPULATED, not a hollow skeleton. Caught for real: the builder was
        # handed a content file that was never written, so node rendered the empty shell, a 35KB
        # file appeared, the build reported success — and every headline was <h1></h1>. "The file
        # exists" is not "the file is right"; assert on the content.
        if demo_ok:
            _hs = [f for f in _dfiles if f.endswith(".html")]
            _hh = open(_hs[0], encoding="utf-8").read() if _hs else ""
            _blank = _hh.count("<h1></h1>") + _hh.count('<p class="sub"></p>')
            demo_ok = (bool(_hs) and _blank == 0 and "Trojan Empire" in _hh
                       and "FABRICATED DATA" in _hh and _hh.count("<canvas") >= 5)
            if not demo_ok:
                print("    !! demo GEOPOL HTML is hollow or unlabelled "
                      "(%d blank headings, %d canvases, banner=%s)"
                      % (_blank, _hh.count("<canvas"), "FABRICATED DATA" in _hh))
    except Exception as _e:
        demo_ok = False; print("    demo smoke error: %r" % _e)
    print("  public demo artifacts (Trojan Empire, RFC 5737 only): %s"
          % ("OK" if demo_ok else "BROKEN"))
    if not demo_ok:
        sys.exit("[X] public demo failed its smoke (build / documentation-IPs / fabrication notice)")

    # c''''') The /demo HERO FILM. Demo.jsx hard-codes /media/cassandra.mp4 and its poster. A missing
    #         binary is invisible to vite (it copies public/ verbatim and never validates references)
    #         and invisible to the SSR render (the src is just a string) — the failure only shows up
    #         as a black hero in a customer's browser. So assert the files exist, are non-trivial,
    #         and that every /media/ path the page references is actually present in public/.
    _refs = []
    try:
        _fe = os.path.join(HERE, "webapp", "frontend")
        _dj = open(os.path.join(_fe, "src", "pages", "Demo.jsx"), encoding="utf-8").read()
        _refs = sorted(set(re.findall(r'"(/media/[^"]+)"', _dj)))
        media_ok = bool(_refs)
        for _r in _refs:
            _p = os.path.join(_fe, "public", _r.lstrip("/").replace("/", os.sep))
            _sz = os.path.getsize(_p) if os.path.exists(_p) else 0
            if _sz < 10000:
                media_ok = False
                print("    !! %s missing or truncated (%d bytes)" % (_r, _sz))
        # faststart: the moov atom must precede mdat or the browser buffers the whole file before
        # the first frame. `ffmpeg -movflags +faststart` puts it first; verify, do not assume.
        _mp4 = os.path.join(_fe, "public", "media", "cassandra.mp4")
        if media_ok and os.path.exists(_mp4):
            _hd = open(_mp4, "rb").read(65536)
            _mv, _md = _hd.find(b"moov"), _hd.find(b"mdat")
            if _mv < 0 or (0 <= _md < _mv):
                media_ok = False
                print("    !! cassandra.mp4 is not faststart (moov=%d mdat=%d) — re-run "
                      "ffmpeg -movflags +faststart" % (_mv, _md))
    except Exception as _e:
        media_ok = False; print("    demo media smoke error: %r" % _e)
    print("  /demo hero film present + faststart (%d ref(s)): %s"
          % (len(_refs), "OK" if media_ok else "BROKEN"))
    if not media_ok:
        sys.exit("[X] /demo hero media missing, truncated, or not faststart")

    # c''''''0) i18n GATE — six languages, and every one of them proved by RENDERING.
    #
    # Three separate production defects live behind this gate, all of them invisible to `vite build`:
    #   * a fallback that prints the KEY looks like content — `q3.h` and `earn.01b` shipped live, in
    #     BOTH languages, because the key was written into one dictionary and read from the other;
    #   * a trailing-space mismatch between `tx("... is ")` and a trimmed dictionary key made five
    #     German strings fall back to English mid-headline — the "mixed language" report;
    #   * `tx` was a fresh arrow per render, so a useEffect dep changed every render and the
    #     architecture map was appended again and again — the "repeated chunks" report.
    # So: the catalogue must be 100% in every locale, and the SSR audit must render all six public
    # pages in all six languages and MEASURE the English residue instead of anyone eyeballing it.
    i18n_ok = True
    try:
        _fe = os.path.join(HERE, "webapp", "frontend")
        # Call `node` DIRECTLY, never through npx: `npx --no-install node` asks npm to install a
        # `node` PACKAGE and aborts non-interactively ("npx canceled due to missing packages"),
        # which is a gate failing on its own launcher rather than on the thing it checks.
        if not have("node"):
            sys.exit("[X] node is not on PATH - the i18n gate cannot run. Install Node 18+ "
                     "(the frontend build needs it too), then re-run: python ship.py")

        # api.js has TWO helpers with different return contracts (getJSON -> the body, postJSON ->
        # {ok,data}). Destructuring the wrong one compiles, runs, and silently yields undefined —
        # it made the document-language selector show English only, and made the assessment
        # re-attach always bail. Pure static check, no toolchain, so it runs everywhere.
        if run(["node", "tools/api_contract.mjs"], check=False, cwd=_fe) != 0:
            i18n_ok = False
            print("    !! an api.js call site consumes the wrong response shape")

        # HEADER LAYOUT. A fixed-height flex row is ARITHMETIC: brand + every control + gaps, in
        # the LONGEST language. Adding "Who we are" to the nav pushed the GERMAN row past the
        # viewport and "Zur Anwendung" landed on top of the page heading. CLAUDE.md had recorded
        # that rule twice; I added a control and did not re-measure. This also pins "exactly one
        # language toggle" - the operator was shown two on every legal page.
        if run(["node", "tools/header_layout.mjs"], check=False, cwd=_fe) != 0:
            i18n_ok = False
            print("    !! the header row overflows, or a duplicate language control is back")

        # `run()` here STREAMS and returns an int returncode; it does not capture. The audit prints
        # its own per-language table, so streaming is what we want.
        if run(["node", "tools/i18n_catalogue.mjs", "--check"], check=False, cwd=_fe) != 0:
            i18n_ok = False
            print("    !! a locale is incomplete - see webapp/frontend/tools/gap.*.json")

        # THE RENDER AUDIT RUNS IN THE DOCKER BUILD, not here — see webapp/Dockerfile.
        #
        # esbuild's binary is a PER-PLATFORM optional dependency and this repo's node_modules is
        # Linux-native (it is a shared folder), so on Windows the bundle dies with
        # "@esbuild/win32-x64 could not be found". Three ship.py runs in a row failed on that
        # plumbing instead of on a translation. Rather than make the operator repair a toolchain,
        # the audit moved into the frontend image build, which does a fresh npm install on
        # linux/amd64 — correct by construction, nothing to drift, still one command.
        #
        # This is NOT a silent skip: it runs on every web deploy and fails the image (and therefore
        # the deploy) if a page falls back to English or a raw key reaches the DOM. Try it locally
        # anyway when the toolchain happens to be usable, because failing here is faster feedback.
        # Exit codes are the contract: 1 = a REAL defect (fail the ship), 2 = toolchain unusable on
        # this platform (note it and move on — the image build enforces it). Conflating them would
        # either block the operator over a toolchain they never installed, or swallow a real defect.
        _audit = run(["node", "tools/run_i18n_audit.mjs"], check=False, cwd=_fe)
        if _audit == 2:
            print("    render audit skipped locally (no esbuild binary for this platform) - it is "
                  "ENFORCED in the frontend image build, see webapp/Dockerfile")
        elif _audit != 0:
            i18n_ok = False
    except SystemExit:
        raise
    except Exception as _e:
        i18n_ok = False; print("    i18n gate error: %r" % _e)
    print("  i18n: 6 locales complete + every page renders in each: %s"
          % ("OK" if i18n_ok else "BROKEN"))
    if not i18n_ok:
        sys.exit("[X] i18n gate failed - a locale is incomplete, a raw key reached the DOM, "
                 "or a page falls back to English")

    # c''''''1) DECK LANGUAGES — every language the engine CLAIMS it can produce must actually build,
    #          and must not fall back to English mid-deck.
    #
    # deck_langs.doc_langs() is a capability CLAIM served to the UI and the bots at /api/langs. A claim
    # nobody tests is how `--lang it` used to reach an engine that silently answered in English. So:
    # for every claimed language, render the three security decks from the sample fixture with the
    # dictionary audit on, and FAIL if any string the GERMAN pack covers is still English — German is
    # the reference locale, so "German translates it, this one does not" is the definition of a gap.
    lang_ok = True
    try:
        import importlib.util as _ilu2
        _sp = _ilu2.spec_from_file_location("deck_langs", os.path.join(engine, "deck_langs.py"))
        _dl = _ilu2.module_from_spec(_sp); _sp.loader.exec_module(_dl)
        _claimed = [c for c in _dl.doc_langs() if c != "en"]
        _de = _json.load(open(os.path.join(engine, "i18n", "de.json"), encoding="utf-8"))["strings"]
        _ld = os.path.join(tempfile.gettempdir(), "ship_langs")
        os.makedirs(_ld, exist_ok=True)
        for _lc in _claimed:
            _gaps = set()
            for _b, _src in (("build_findings_deck.js", "findings.sample.json"),
                             ("build_cbiq_deck.js", "cbiq.sample.json"),
                             ("build_geopol_deck.js", "geopol.sample.json")):
                _au = os.path.join(_ld, "audit_%s_%s.json" % (_lc, _b[6:9]))
                _env = dict(os.environ, DECK_LANG=_lc, DECK_I18N_AUDIT="1",
                            DECK_I18N_AUDIT_OUT=_au)
                subprocess.run(["node", os.path.join(engine, _b), os.path.join(smp, _src),
                                os.path.join(_ld, "%s_%s.pptx" % (_lc, _b[6:9]))],
                               capture_output=True, text=True, env=_env, timeout=180)
                try:
                    for _it in _json.load(open(_au, encoding="utf-8")):
                        if _it["s"] in _de:
                            _gaps.add(_it["s"])
                except Exception:
                    pass
            print("    %s: %d string(s) the German pack covers but %s does not"
                  % (_lc, len(_gaps), _lc))
            for _g in sorted(_gaps)[:6]:
                print("       !! %r" % _g[:88])
            if _gaps:
                lang_ok = False
    except Exception as _e:
        lang_ok = False; print("    deck-language gate error: %r" % _e)
    print("  deck languages build with no fallback-to-English: %s" % ("OK" if lang_ok else "BROKEN"))
    if not lang_ok:
        sys.exit("[X] a claimed deck language falls back to English - /api/langs would be lying")

    # c'''''') BRAND GATE. The product is Cybergod LLC / S4Biz Group; nothing a customer sees may say
    #          Colt. Grep the RENDERED ARTIFACT, never the source: the enum key "COLT" legitimately
    #          survives in tagMap / TAGWORDS / enrich's tag validation (renaming an enum makes
    #          remediation rows silently vanish), and `coltControl` is a JSON key shared by engine and
    #          builder. Only what reaches a slide or a screen is in scope, so only that is checked.
    try:
        brand_ok = True
        _bd = os.path.join(tempfile.gettempdir(), "ship_brand")
        os.makedirs(_bd, exist_ok=True)
        for _lang in ("en", "de"):
            for _b, _fx in (("findings", "findings"), ("cbiq", "cbiq"), ("geopol", "geopol")):
                _o = os.path.join(_bd, "%s_%s.pptx" % (_b, _lang))
                subprocess.run(["node", os.path.join(engine, "build_%s_deck.js" % _b),
                                os.path.join(engine, "..", "sample", "%s.sample.json" % _fx), _o],
                               capture_output=True, text=True, timeout=180,
                               env={**os.environ, "DECK_LANG": _lang})
                if not os.path.exists(_o):
                    continue
                _z = _zipfile.ZipFile(_o)
                _t = " ".join("".join(re.findall(r"<a:t>(.*?)</a:t>", _z.read(_n).decode("utf8"), re.S))
                              for _n in _z.namelist()
                              if re.match(r"ppt/slides/slide\d+\.xml$", _n))
                _h = re.findall(r"(?i)\S{0,22}colt\S{0,22}", _t)
                if _h:
                    brand_ok = False
                    print("    !! %s_%s.pptx renders 'Colt': %s" % (_b, _lang, _h[:3]))
        # EVERY surface a user touches, not just the web pages. The first pass missed the PWA
        # manifest (the name a phone puts on the HOME SCREEN), the browser tab title, the OTP email
        # subject and BOTH Telegram bots — all of them customer-facing, none of them a React page.
        _fe = os.path.join(HERE, "webapp", "frontend")
        _SURFACES = [
            (os.path.join(_fe, "src", "pages", "Landing.jsx"), "js"),
            (os.path.join(_fe, "src", "pages", "Login.jsx"), "js"),
            (os.path.join(_fe, "src", "pages", "Demo.jsx"), "js"),
            (os.path.join(_fe, "src", "pages", "Experience.jsx"), "js"),
            (os.path.join(_fe, "src", "pages", "Contact.jsx"), "js"),
            (os.path.join(_fe, "src", "pages", "Impressum.jsx"), "js"),
            (os.path.join(_fe, "src", "legal.jsx"), "js"),
            (os.path.join(_fe, "src", "components", "Sidebar.jsx"), "js"),
            (os.path.join(_fe, "index.html"), "html"),                    # browser tab
            (os.path.join(_fe, "public", "manifest.webmanifest"), "html"),  # phone home screen
            (os.path.join(HERE, "assess-bot", "bot.py"), "py"),           # Telegram
            (os.path.join(HERE, "cassandra-bot", "cassandra_bot.py"), "py"),
            # the 404 page every scanner AND every mistyped URL lands on
            (os.path.join(HERE, "webapp", "backend", "app", "visitors.py"), "py"),
        ]
        # Infrastructure identifiers legitimately keep the old name (log paths, the auth-store key,
        # the shared auth module, container/volume names). They are never shown to a user.
        _INFRA = re.compile(r"/var/log/colt|colt_auth|COLT_USER|colt_events|colt-|colttechbot")
        # ONE DELIBERATE EXCEPTION, NARROWLY SCOPED: the principal's EMPLOYMENT HISTORY on
        # /experience names Huawei, Colt and Cogent as carriers he has worked for. That is
        # biography — the same line appears on the operator's own approved capability deck — and it
        # is categorically different from branding the PRODUCT as Colt, which is what this gate
        # exists to prevent. The exception matches only the exact tribes-array line in legal.jsx;
        # a second occurrence anywhere, including elsewhere in that file, still fails.
        _BIO = re.compile(r'names:\s*\["Huawei",\s*"Colt",\s*"Cogent"\]')
        for _p, _kind in _SURFACES:
            if not os.path.exists(_p):
                continue
            _src = open(_p, encoding="utf-8").read()
            _vis = (re.sub(r"#[^\n]*", "", _src) if _kind == "py"
                    else re.sub(r"/\*.*?\*/", "", re.sub(r"//[^\n]*", "", _src), flags=re.S))
            _bad = [h for h in re.findall(r"(?i).{0,40}colt.{0,40}", _vis)
                    if not _INFRA.search(h) and not _BIO.search(h)]
            # Prove the exception cannot widen: legal.jsx may carry the employer name EXACTLY once.
            if os.path.basename(_p) == "legal.jsx" and len(re.findall(r"(?i)colt", _vis)) != 1:
                brand_ok = False
                print("    !! legal.jsx names 'Colt' %d times - the bio exception allows exactly 1"
                      % len(re.findall(r"(?i)colt", _vis)))
            if _bad:
                brand_ok = False
                print("    !! %s still shows 'Colt': %s"
                      % (os.path.basename(_p), [b.strip()[:60] for b in _bad[:2]]))
        # the one-time-code email a user receives
        _ca = open(os.path.join(HERE, "colt_auth.py"), encoding="utf-8").read()
        if re.search(r'msg\["Subject"\] = "[^"]*(?i:colt)', _ca):
            brand_ok = False
            print("    !! the OTP email subject still says Colt")
    except Exception as _e:
        brand_ok = False; print("    brand gate error: %r" % _e)
    _lg = open(os.path.join(HERE, "webapp", "frontend", "src", "legal.jsx"), encoding="utf-8").read()
    _noaddr = re.findall(r'name: "([^"]+)"[^}]*?street: ""', _lg)
    if _noaddr:
        print("  [i] group entities with no registered street address (pages omit it, no invented "
              "data): %s" % ", ".join(_noaddr))

    print("  brand: nothing customer-facing says 'Colt' "
          "(6 decks EN+DE · web · PWA shell · 2 Telegram bots · OTP email): %s"
          % ("OK" if brand_ok else "BROKEN"))
    if not brand_ok:
        sys.exit("[X] brand gate failed - a customer-facing surface still says Colt")

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
    _SHA_CACHE.pop("colt-web", None)               # colt-web was just rebuilt -> its hash is stale
    _prime_sha_cache(["colt-web", "colt-assessbot"])   # ONE session answers both, and do_bots reuses it
    ok, stale = engine_is_current("colt-web")
    if ok:
        print("  OK  colt-web engine matches the repo")
        return
    print("  [!] colt-web is STALE — the CI deploy did not take effect:")
    for s in stale:
        print("        " + s)
    print("  -> self-healing with a direct deploy (deploy_web_direct.py)")
    run([sys.executable, "deploy_web_direct.py"])
    ok, stale = engine_is_current("colt-web", fresh=True)   # just self-healed -> re-probe
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
    ok, stale = engine_is_current("colt-assessbot", fresh=True)   # just rebuilt -> re-probe
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
    """5/5 VERIFY — everything read-only in ONE ssh session.

    THE HANG THIS FIXES: this step used to open FIVE separate ssh sessions (docker ps, two engine
    hashes, the model probe, the .env read) plus up to three more if it had to correct drift. On
    Windows there is no ssh multiplexing to fall back on and sshd penalises repeated connections, so
    the last one in the burst would sit there for minutes — AFTER the deploy had already succeeded.
    One session, delimited sections, parsed locally. A correction (rare) opens a second."""
    say("5/5  VERIFY")
    ok = True
    if DRY:
        return True

    # Build the batch from what this run does NOT already know. The engine hashes are usually cached
    # by do_web/do_bots, so most runs ask only for `docker ps`, the model probe and the .env line.
    parts, names = [], []
    if bots:
        parts.append("echo '#### PS'; docker ps --format '{{.Names}}  {{.Status}}' "
                     "| grep -E 'colt-' || echo NONE")
        names.append("PS")
    hash_code = ("import hashlib,os;b=%r;fs=%r;"
                 "print(chr(10).join(r+' '+(hashlib.sha256(open(os.path.join(b,r),'rb').read()).hexdigest() "
                 "if os.path.exists(os.path.join(b,r)) else 'MISSING') for r in fs))"
                 % (ENGINE_REMOTE, list(ENGINE_FILES)))
    for cont, want in (("colt-web", web), ("colt-assessbot", bots)):
        if want and cont not in _SHA_CACHE:
            parts.append("echo '#### SHA_%s'; docker exec %s python3 -c \"%s\" 2>/dev/null || true"
                         % (cont, cont, hash_code))
            names.append("SHA_%s" % cont)
    if web:
        parts.append("echo '#### MODELS'; docker exec colt-web python3 "
                     "/opt/shodan-skill/scripts/model_probe.py --existence 2>&1 || true")
        parts.append("echo '#### ENV'; grep -hE '^ENRICH_MODELS?=' "
                     "/opt/colt-stack/assess-bot/.env 2>/dev/null | tail -1 || true")
        names += ["MODELS", "ENV"]
    sec = _sections(ssh_script("\n".join(parts), timeout=150), names)

    if bots:
        psout = sec.get("PS", "")
        print("    " + "\n    ".join(l for l in psout.splitlines() if l.strip()))
        if "colt-assessbot" not in psout:
            print("  [!] colt-assessbot not visible"); ok = False
        if "colt-promtail" not in psout:
            print("  [!] colt-promtail missing — Grafana will go quiet"); ok = False

    # The engine hash is the load-bearing check. HTTP 401 only proves *something* is listening —
    # a 3-day-old container answers it just as happily as a current one.
    for cont, want in (("colt-web", web), ("colt-assessbot", bots)):
        if not want:
            continue
        if cont not in _SHA_CACHE:                      # came back in this batch, not from cache
            got = {}
            for line in sec.get("SHA_%s" % cont, "").splitlines():
                bits = line.strip().split(" ")
                if len(bits) == 2 and "/" in bits[0]:
                    got[bits[0]] = bits[1]
            if got:
                _SHA_CACHE[cont] = got
        good, stale = engine_is_current(cont)          # now answered from the cache, no new ssh
        print("  %-16s engine: %s" % (cont, "CURRENT" if good else "STALE  <-- assessments are wrong"))
        if not good:
            for st in stale:
                print("      " + st)
            ok = False

    if web:
        # MODEL PROBE — run INSIDE the container, where OPENAI_API_KEY actually lives. On the PC the
        # key is absent, so model_watch.py printed "catalog unavailable - skipping" on every run: a
        # check that cannot see the thing it checks is not a check. This asserts every model in the
        # effective chain EXISTS in the live catalog (free, no tokens). deepseek-v4-flash 404'd in
        # production because nothing looked.
        _mp = sec.get("MODELS", "")
        seen = set()
        for _l in _mp.splitlines():                    # model_probe prints its header twice; dedupe
            t = _l.rstrip()
            if t.strip() and t not in seen:
                seen.add(t); print("    " + t)
        if "MISSING" in _mp:
            sys.exit("[X] a model in the enrichment chain does NOT exist on the inference API. "
                     "Every assessment would waste a round-trip and silently degrade. "
                     "Fix enrich.py::_FALLBACKS using the ids model_probe.py printed.")

        # CONFIG DRIFT: a stale ENRICH_MODELS in the droplet's .env silently beats the committed
        # chain (angermann.de ran gemma-first even though the repo had already demoted it).
        _envline = sec.get("ENV", "").strip()
        _envchain = _envline.split("=", 1)[1].strip().strip('\'"') if "=" in _envline else ""
        _repo = ""
        try:
            for _l in open(os.path.join(ENGINE_LOCAL, "scripts", "enrich.py"), encoding="utf-8"):
                if _l.startswith("_FALLBACKS = ["):
                    _repo = ",".join(x.strip().strip('"\'') for x in
                                     _l.split("[", 1)[1].rstrip("]\n ").split(","))
                    break
        except OSError:
            pass
        if _envchain and _repo and _envchain.replace(" ", "") != _repo.replace(" ", ""):
            # AUTO-CORRECT, do not merely warn, and do it in ONE more session. DELETE the override
            # rather than rewrite it: enrich.py::_FALLBACKS is the single source of truth, and a
            # value present in .env silently outranks it forever after. BOTH forms — the legacy
            # singular ENRICH_MODEL is prepended as the chain HEAD by enrich._chain(), so it
            # silently REORDERS the committed order.
            print("  [!] ENRICH_MODELS drift — droplet %s vs repo %s; correcting the droplet"
                  % (_envchain, _repo))
            fix = ssh_script(
                "sed -i -E '/^ENRICH_MODELS?=/d' /opt/colt-stack/assess-bot/.env\n"
                "cd /opt/colt-stack && docker compose -p colt-stack -f docker-compose.web.yml "
                "up -d web >/dev/null 2>&1 || true\n"
                "echo '#### NOW'; grep -hE '^ENRICH_MODELS?=' /opt/colt-stack/assess-bot/.env "
                "| tail -1 || true", timeout=120)
            if not _sections(fix, ["NOW"])["NOW"].strip():
                print("  enrich chain: stale droplet override REMOVED, repo order now in force "
                      "(%s); colt-web restarted" % _repo)
            else:
                print("  [!] could not correct ENRICH_MODELS on the droplet")
        elif _repo:
            print("  enrich chain: repo order in force (%s)" % _repo)

    if web and not DRY:
        # Prove the bot-404 gate: real users must be served, crawlers must get 404, and /api/me must
        # still answer 401 (every deploy verifier in this repo depends on that — see check_bot_gate.py).
        try:
            sys.path.insert(0, HERE)
            import check_bot_gate as _bg
            _r = _bg.run(DOMAIN, "https", insecure=False)
            if _r["failures"]:
                ok = False
        except Exception as _e:
            print("  [!] bot-gate check skipped (%s)" % type(_e).__name__)
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
    ap.add_argument("--no-stage", action="store_true",
                    help="skip the staging validation and deploy straight to production")
    ap.add_argument("--fast-stage", action="store_true",
                    help="validate on staging but SKIP the reboot test (faster, weaker — the "
                         "reboot is the test that would have caught the 2026-08-07 outage)")
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

    # ---- STAGING GATE — validate on the twin BEFORE production is touched -------------------
    #      The 2026-08-07 outage had no environment in which the change could be REBOOTED first.
    #      stagegate deploys to the staging droplet, health-checks it, reboots it, health-checks it
    #      again, then has 2 soldiers + 2 auditors write the verdict digest to email + Telegram.
    #      The gate itself is deterministic (operating principle 5: the LLM assists, never decides).
    #      Skipped by --no-stage, and never blocks a rollback.
    if not a.no_stage and not DRY:
        print("\n" + "-" * 74)
        print("  STAGING GATE — validate on the twin, reboot it, then decide     [+%ds]"
              % int(time.time() - T0))
        print("-" * 74)
        try:
            import stagegate
            gate, digest = stagegate.run(reboot_test=not a.fast_stage)
            print("\n" + (digest or "").replace("\n", "\n  "))
            print("\n  STAGING GATE: %s" % gate)
            print("  " + (stagegate.notify("cybergod staging validation: %s" % gate, digest) or ""))
            if gate != "GO":
                print("\n  [!] REFUSING TO DEPLOY TO PRODUCTION — staging did not validate.")
                print("      Nothing was changed on %s." % HOST)
                # GOVERNANCE LOOP: the panel already produced an RCA and a proposal. Rather than
                # ending here and costing another full round-trip, offer to execute an ALLOWLISTED
                # action — on STAGING only, behind an explicit approval and a TOTP code — then
                # re-check and re-review. Production is reachable from there only after a second
                # approval, a second code, and an automatic backup.
                try:
                    import govern
                    res = govern.run(stagegate.last_verdict(), stagegate.STAGING, HOST,
                                     stagegate.ssh_script,
                                     lambda: stagegate.run(reboot_test=False),
                                     notify=stagegate.notify)
                    if res in ("fixed-staging", "promote"):
                        print("\n  Staging is green again. Re-run `python ship.py` to deploy.")
                except (EOFError, KeyboardInterrupt):
                    print("\n  (governance skipped — no interactive terminal)")
                except Exception as _g:
                    print("  [!] governance loop unavailable (%s)" % type(_g).__name__)
                print("      Override deliberately with:  python ship.py --no-stage")
                sys.exit(2)
        except SystemExit:
            raise
        except Exception as _e:
            # A broken GATE must not become a broken DEPLOY. Report loudly, continue — the same
            # doctrine as the FP auditor: a check is a signal, not an authority over the pipeline.
            print("  [!] staging gate could not run (%s: %s) — continuing to production."
                  % (type(_e).__name__, str(_e)[:160]))

    if web:
        do_web(a.ci)
    if bots:
        do_bots()

    ok = do_verify(web, bots)

    # ---- SHARED-PROXY GUARDRAILS (2026-08-07 outage) -----------------------------------------
    #      Every project on this box appends a MARKED block into ONE shared /opt/videodead/
    #      Caddyfile. On 6 Aug a deploy truncated jobhuntwow's block; Caddy reads its config only
    #      at start, so the damage sat invisible for 12 hours until patchwatch's kernel reboot made
    #      it re-read the file — and every domain died together.
    #
    #      caddyguard.py is a BUILDING BLOCK, not a second command (operating principle 7). It is
    #      idempotent: it re-splits the live file into per-project fragments, restores a fragment
    #      ONLY if it is missing/empty/unbalanced, re-assembles, validates and ensures the watchdog
    #      timer is enabled. Non-blocking on install problems, but a FAILED HEALTH CHECK is a real
    #      warning — a shared proxy that would not survive a restart is the definition of fragile.
    if not DRY:
        try:
            _cg = subprocess.run([sys.executable, os.path.join(HERE, "caddyguard.py")],
                                 capture_output=True, text=True, encoding="utf-8",
                                 errors="replace", timeout=600)
            print("")
            # STDERR TOO. caddyguard crashed with a TypeError and printed NOTHING here, because
            # only stdout was echoed — so "reported a problem" appeared with no problem visible.
            # Same defect just fixed for patchwatch; a building block that fails must be able to
            # say why, or the operator re-runs it blind.
            _cgout = ((_cg.stdout or "") + (_cg.stderr or "")).rstrip()
            print(_cgout or "  caddyguard: no output at all (crashed before printing?)")

            # THE REBOOT GATE MUST BE ON THE BOX, NOT JUST IN THE REPO.
            # caddyguard reports whether the droplet's patchwatch copy carries the gate that
            # refuses to reboot into an invalid proxy config. It was MISSING for a whole run and
            # the only remedy printed was "run this other script" — which is operating principle 7
            # broken, and a live safety hole meanwhile. Install it here, automatically, once.
            if "reboot gate MISSING" in _cgout:
                print("\n  Installing the patchwatch reboot gate on the droplet (was missing)...")
                _pw = subprocess.run([sys.executable,
                                      os.path.join(HERE, "patchwatch", "provision_patchwatch.py")],
                                     capture_output=True, text=True, encoding="utf-8",
                                     errors="replace", timeout=900)
                # PRINT STDERR TOO. Last run this failed and showed NOTHING, because only
                # stdout was echoed — the same "silent skip" class as the ruff gate. A failure
                # that cannot explain itself is a failure you will keep re-running.
                _tail = ((_pw.stdout or "") + (_pw.stderr or "")).rstrip().splitlines()[-14:]
                print("  " + "\n  ".join(_tail) if _tail else "  (no output at all)")
                if _pw.returncode != 0:
                    print("  [!] patchwatch provisioning failed — the droplet can still reboot")
                    print("      into a broken proxy config. Not fatal to this deploy, but fix it.")

            if _cg.returncode != 0:
                ok = False
                print("  [!] caddyguard reported a problem with the shared proxy — see above.")
        except Exception as _e:
            print("  [!] caddyguard skipped (%s)" % type(_e).__name__)

    # ---- has DigitalOcean shipped anything new, and does it answer fast? ----------------------
    #      Runs after verify so it can never delay the deploy, and is NON-BLOCKING by design: a
    #      new model is information, not a broken build. It exists because the enrichment chain is
    #      chosen from evidence that goes stale SILENTLY - gemma sat at the head of the chain
    #      returning empty answers for weeks, and DeepSeek V4 Flash shipped at ~4x cheaper than
    #      the V3.2 we still run, and nothing ever looked. Now every deploy looks.
    try:
        _eng = os.path.join(HERE, 'hermes-skills', 'shodan-assessment', 'scripts')
        _mw = subprocess.run([sys.executable, os.path.join(_eng, 'model_watch.py')],
                             capture_output=True, text=True, timeout=240)
        print('')
        print((_mw.stdout or '').rstrip() or '  model-watch: no output')
    except Exception as _e:
        print('  [!] model-watch skipped (%s) - never blocks a deploy' % type(_e).__name__)


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
