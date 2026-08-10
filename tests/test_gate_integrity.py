"""test_gate_integrity.py — the gate must not be able to lie, and a unanimous panel must be heard.

THE INCIDENT THIS PINS (2026-08-07, promoted to production on a green gate):

    mount_fresh    OK   container reads the current file (3af610cdeb71) - bind mount is not stale
    config_drift   OK   drift check unavailable: STALE MOUNT STALE MOUNT: host= container=3af610cdeb71
    GATE: GO (33/33)
    ...all four reviewers: NO-GO, all four naming config_drift...
    STAGING GATE: GO   -> deployed to production

Three separate defects composed into a false green:

  1. `agent.py` hashed a HARDCODED host path (production's /opt/videodead/Caddyfile). Staging's
     proxy mounts a different file, so the host hash came back EMPTY and mount_sync read "no file"
     as "stale mount". Absence of evidence became a finding — the oldest rule in this repo.
  2. `stagegate`'s case statement had a catch-all that scored an UNRECOGNISED verdict as a PASS
     (`chk config_drift yes "drift check unavailable: $D"`). A fallback that turns an unknown
     answer into success is strictly worse than having no check at all.
  3. Nothing noticed that a check reporting PASS had "STALE MOUNT" in its own detail. All four
     models did notice, in four different sentences — and the architecture gave their unanimous
     dissent no power to stop anything.

The fixes are asserted below. Note what is NOT changed: models still cannot veto a release. The
deterministic checks decide. What is new is that UNANIMOUS dissent against a green gate halts and
asks a human, because that specific pattern has now twice meant "a check is lying".
"""
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
_s = importlib.util.spec_from_file_location("stagegate", os.path.join(ROOT, "stagegate.py"))
sg = importlib.util.module_from_spec(_s)
sys.modules["stagegate"] = sg
_s.loader.exec_module(sg)


# ---------------------------------------------------------------- 1. the self-contradiction rule
def test_the_exact_line_that_shipped_is_now_a_failure():
    """Verbatim from the 2026-08-07 run. It reported PASS; it must now be a FAILURE."""
    line = ("CHECK|config_drift|yes|drift check unavailable: STALE MOUNT STALE MOUNT: "
            "host= container=3af610cdeb71    the cont")
    (c,) = sg.parse_checks(line)
    assert c["ok"] is False, "the line that fooled the gate still passes"
    assert "SELF-CONTRADICTORY" in c["detail"]
    assert "stale" in c["detail"].lower()


def test_healthy_details_are_not_flagged():
    """A guard that cries wolf gets ignored. These are all REAL passing details from live runs."""
    benign = [
        "CHECK|config_drift|yes|running config serves exactly what the file says (11 host(s), 9 handler(s))",
        "CHECK|config_drift|yes|running config == file on disk (e774f8ef1e33) - no silent drift",
        "CHECK|mount_fresh|yes|container reads the current file (3af610cdeb71) - bind mount is not stale",
        "CHECK|config_drift|yes|admin API unreachable (nothing to compare - not a fault)",
        "CHECK|engine_runs|yes|3 decks + 39256b html, zero undefined/NaN leaks (output CHECKED, not just exit 0)",
        "CHECK|api_auth|yes|GET /api/me -> 401 (up + locked)",
        "CHECK|bot_gate|yes|a bot UA still gets 404",
        "CHECK|restart_count|yes|restarts=0",
    ]
    for ln in benign:
        (c,) = sg.parse_checks(ln)
        assert c["ok"] is True, "false positive on a healthy check: %s" % c["detail"]


def test_a_genuine_failure_stays_a_failure():
    (c,) = sg.parse_checks("CHECK|proxy_routes|no|proxy -> colt-web -> 000")
    assert c["ok"] is False


def test_the_rule_is_general_not_a_patch_for_one_string():
    """Any PASS whose detail describes a failure, in any wording, must be demoted."""
    for detail in ("check unavailable: something went wrong",
                   "could not read the running config",
                   "unrecognised drift verdict",
                   "the proxy is serving a replaced inode",
                   "reload failed, falling back"):
        (c,) = sg.parse_checks("CHECK|x|yes|%s" % detail)
        assert c["ok"] is False, "not demoted: %r" % detail


# ---------------------------------------------------------------- 2. no catch-all pass in bash
def test_no_branch_in_HEALTH_scores_an_unknown_answer_as_a_pass():
    """The bash gate must not contain a wildcard branch that reports success.

    This is the defect in its original form: `*) chk config_drift yes "..."`. Grepping for the
    shape rather than the exact string means a future check cannot reintroduce it under a new name.
    """
    health = re.search(r'HEALTH\s*=\s*r?"""(.*?)"""', open(os.path.join(ROOT, "stagegate.py"),
                                                           encoding="utf-8").read(), re.S).group(1)
    bad = re.findall(r"^\s*\*\)\s*chk\s+\w+\s+yes\b.*$", health, re.M)
    assert not bad, "a wildcard branch reports PASS on an unknown answer: %s" % bad


# ---------------------------------------------------------------- 3. unanimous dissent halts
def _verdict(gate, verdicts):
    return {"gate": gate, "digest": "d",
            "reviews": [{"model": "m%d" % i, "verdict": v} for i, v in enumerate(verdicts)]}


def test_unanimous_no_go_against_a_green_gate_halts(monkeypatch=None):
    os.environ.pop("OVERRIDE_PANEL", None)
    g, d = sg._decide_from_verdict(_verdict("GO", ["no-go"] * 4))
    assert g == "NO-GO", "4/4 dissent against a green gate still promoted"
    assert "HALTED" in d and "OVERRIDE_PANEL" in d


def test_a_split_panel_does_not_block():
    """Models must NOT get a veto. One dissenter, or two, cannot stop a green gate."""
    os.environ.pop("OVERRIDE_PANEL", None)
    for vs in (["go", "no-go", "go", "go"], ["no-go", "no-go", "go", "unsure"],
               ["go", "go", "go", "unsure"]):
        g, _ = sg._decide_from_verdict(_verdict("GO", vs))
        assert g == "GO", "a split panel blocked the release: %s" % vs


def test_an_unavailable_panel_never_blocks():
    """A 429 or an outage must not be able to stop a good release."""
    os.environ.pop("OVERRIDE_PANEL", None)
    g, _ = sg._decide_from_verdict({"gate": "GO", "digest": "d", "reviews": []})
    assert g == "GO"
    g, _ = sg._decide_from_verdict({"gate": "GO", "digest": "d", "reviews":
                                    [{"model": "a", "verdict": "no-go"}]})
    assert g == "GO", "a single reviewer must not be a quorum"


def test_the_override_is_explicit_and_works():
    os.environ["OVERRIDE_PANEL"] = "1"
    try:
        g, _ = sg._decide_from_verdict(_verdict("GO", ["no-go"] * 4))
        assert g == "GO", "the documented override does not work"
    finally:
        os.environ.pop("OVERRIDE_PANEL", None)


def test_a_failed_gate_is_never_rescued_by_a_happy_panel():
    os.environ.pop("OVERRIDE_PANEL", None)
    g, _ = sg._decide_from_verdict(_verdict("NO-GO", ["go"] * 4))
    assert g == "NO-GO", "an agreeable panel overrode a failing deterministic gate"


# ---------------------------------------------------------------- 4. the agent's own defect
def test_missing_host_file_is_a_skip_not_a_stale_mount():
    """Absence of evidence is never a finding — the rule this repo has held since bgp_resilience."""
    _a = importlib.util.spec_from_file_location(
        "cg_agent", os.path.join(ROOT, "deploy", "caddyguard", "agent.py"))
    ag = importlib.util.module_from_spec(_a)
    _a.loader.exec_module(ag)
    ag.mount_source = lambda c: "/nonexistent/Caddyfile"
    ag._sha_in_container = lambda c: "3af610cdeb71" + "0" * 52
    ok, msg = ag.mount_sync("staging-caddy", fix=False)
    assert ok is True, "a missing host file is still reported as a stale mount: %s" % msg
    assert "nothing to compare" in msg
    # And the message must NOT be the one that broke the gate.
    assert not msg.startswith("STALE MOUNT")


def test_the_mount_source_is_asked_for_not_assumed():
    src = open(os.path.join(ROOT, "deploy", "caddyguard", "agent.py"), encoding="utf-8").read()
    assert "def mount_source(" in src, "the host path is still assumed rather than resolved"
    assert "mount_source(c) or LIVE" in src, "mount_sync does not use the resolved source"


# ============================================================================================
def _read(path):
    return open(path, encoding="utf-8").read()


# The panel keeps proposing fixes for checks that already work, because the briefing it is given
# describes the TRAP without describing the IMPLEMENTATION. kimi-k2.6 has now claimed three runs
# running that config_drift hash-compares two serialisations. It does not, and has not since
# 7 Aug 2026. That is a defect in the map we hand the reviewers, not in their reasoning.
# ============================================================================================
def test_the_panel_is_told_what_each_check_measures():
    arch = _read(os.path.join(ROOT, "deploy", "stagegate", "quorum.py"))
    i = arch.find("ARCH = ")
    assert i > 0, "ARCH briefing not found in quorum.py"
    block = arch[i:i + 4000]
    for check in ("mount_fresh", "config_drift", "vhost_roster", "admin_api_closed"):
        assert check in block, (
            "the ARCH briefing does not say what %s measures, so a reviewer can only guess. "
            "Three panels in a row have spent a slot on a refuted claim for exactly this "
            "reason." % check)
    assert "does NOT hash" in block or "not hash" in block, (
        "the briefing must state that config_drift compares SETS, not hashes — otherwise a "
        "reviewer reads the 'a hash comparison is a false positive' warning and attributes the "
        "removed method to the current check.")


def test_no_check_name_claims_more_than_it_measures():
    """A check's NAME is read far more often than its detail text.

    `config_reread` asserted only that the process started after the file was written. It proves
    ORDERING; the name promised content. kimi was right that renaming it is the honest fix, and a
    detail string saying "this does not prove what my name says" is not a substitute.
    """
    sg = _read(os.path.join(ROOT, "stagegate.py"))
    assert "config_reread" not in sg, (
        "config_reread is back. It measures write/start ORDERING only — name it for what it "
        "measures (config_write_ordering), or make it actually prove a re-read.")
    assert "config_write_ordering" in sg, "the ordering check disappeared entirely"


def test_certificate_expiry_is_a_gate_and_is_also_checked_off_box():
    """A lapsed certificate takes EVERY domain on the shared proxy down at the same instant, and
    it is the one outage that arrives on a published schedule. It used to be printed only."""
    cg = _read(os.path.join(ROOT, "caddyguard.py"))
    assert "CERT GATE FAILED" in cg, "caddyguard no longer gates on certificate expiry"
    assert "warn.append" in cg and "return 1" in cg, (
        "the cert/reboot verdicts are printed but not folded into the exit code — a line in a "
        "400-line deploy log is a fact nobody reads, not a warning.")

    up = _read(os.path.join(ROOT, ".github", "workflows", "uptime.yml"))
    assert "x509" in up and "enddate" in up, (
        "certificate expiry is not checked OFF-BOX. The droplet's own monitoring sits behind the "
        "proxy it monitors, so it is mute exactly when it matters.")


def test_the_reboot_gate_installs_itself_without_a_cloud_credential():
    """The 6 Aug outage mechanism: patchwatch rebooted into a damaged Caddyfile.

    The gate was reported MISSING across several ships because it was gated behind
    `provision_patchwatch.py`, which hard-fails without DO_API_TOKEN. That token buys SNAPSHOTS and
    Spaces backups; the gate is pure code, and patchwatch's credentials live in
    /etc/patchwatch/patchwatch.env, which installing the code never touches.
    """
    cg = _read(os.path.join(ROOT, "caddyguard.py"))
    assert "/opt/patchwatch/patchwatch.py" in cg and "base64 -d > /opt/patchwatch" in cg, (
        "caddyguard no longer installs the reboot gate. Telling the operator to run a second "
        "script breaks the one-command rule AND leaves the guardrail uninstalled.")
    # STRIP COMMENTS FIRST. The first version of this assertion matched the comment that EXPLAINS
    # why the token is not needed, and failed on a file that was correct. Same false positive the
    # brand gate already learned to avoid: grep the code, not the prose about the code.
    code = "\n".join(ln for ln in cg.splitlines() if not ln.lstrip().startswith("#"))
    assert "DO_API_TOKEN" not in code, (
        "the reboot gate depends on a cloud credential again. That token buys snapshots and "
        "Spaces backups; the gate is pure code and patchwatch's own env file holds its secrets.")
    # It must verify what it installed rather than assuming the copy worked.
    assert "does not parse" in cg and "restoring the previous copy" in cg, (
        "the installer does not validate what it wrote. Overwriting a droplet's patch automation "
        "with a file that does not parse would disable unattended security updates silently.")


def test_the_preview_stamp_is_platform_independent():
    """The stamp must mean "this UI was previewed", not "previewed on this operating system".

    It hashed RAW BYTES, so a Windows checkout (CRLF, because core.autocrlf rewrites on checkout)
    and a Linux checkout of the SAME COMMIT produced different digests. The gate then could not be
    evaluated from anywhere except the machine that wrote it. Third appearance of this trap: see
    also `git archive` applying autocrlf to the deploy artefact.
    """
    import hashlib
    import importlib.util as _ilu
    spec = _ilu.spec_from_file_location("ups", os.path.join(ROOT, "ui_preview_stamp.py"))
    ups = _ilu.module_from_spec(spec)
    spec.loader.exec_module(ups)

    def digest(nl):
        h = hashlib.sha256()
        for name, body in (("a.jsx", "const a = 1;\nexport default a;\n"),
                           ("b.css", ".x{color:red}\n")):
            h.update(name.encode())
            h.update(b"\0")
            raw = body.replace("\n", nl).encode()
            if os.path.splitext(name)[1] in ups._TEXT_SUFFIXES:
                raw = raw.replace(b"\r\n", b"\n")
            h.update(raw)
            h.update(b"\0")
        return h.hexdigest()

    assert digest("\n") == digest("\r\n"), (
        "the UI hash still depends on line endings, so Windows and Linux disagree about whether "
        "the same commit was previewed.")

    # And binaries must NOT be normalised: a PNG can legitimately contain 0d 0a.
    for binext in (".png", ".jpg", ".mp4", ".ico", ".woff2"):
        assert binext not in ups._TEXT_SUFFIXES, (
            "%s is treated as text, so its bytes would be rewritten before hashing" % binext)


# ============================================================================================
# THE PANEL, 9 Aug 2026 (third run). kimi-k2.6 returned NO-GO with three risks. One mechanism was
# wrong, two were worth building. These pin what was built.
# ============================================================================================
def test_the_roster_reports_unexpected_vhosts_too():
    """kimi's symmetry argument, and it is correct.

    The roster's premise is "a vhost that silently disappears is a failure". On a SHARED proxy a
    vhost that silently APPEARS is the same class of event: something is claiming traffic and
    certificates for a name nobody committed. It is reported as a WARNING rather than a failure,
    because launching a new site is a normal operation and a gate that fails every launch gets
    switched off.
    """
    a = _read(os.path.join(ROOT, "deploy", "caddyguard", "agent.py"))
    blk = a[a.index("def cmd_roster"):a.index("def cmd_drift")]
    assert "NOT on the committed roster" in blk, (
        "the roster ignores unexpected vhosts again — it only checks that expected ones are there")
    assert "_INTERNAL" in blk, (
        "Caddy's own internal names would be reported as unexpected vhosts on every run, which is "
        "the noise that gets a check disabled")


def test_admin_isolation_is_measured_not_inferred():
    """kimi's MECHANISM was wrong; the doctrine behind the objection was right.

    Each container has its own network namespace, so `localhost` inside the proxy is not reachable
    from another container, and nothing here shares a namespace. But a check that reasons about its
    subject is weaker than one that reproduces it — the rule this whole file exists for. So the
    check now actually tries the connection from a different container.
    """
    a = _read(os.path.join(ROOT, "deploy", "caddyguard", "agent.py"))
    blk = a[a.index("def cmd_admin"):a.index("def cmd_roster")]
    # `sh()` takes an ARGV LIST, so the literal "docker exec" never appears -- it is
    # `["docker", "exec", ...]`. My first version of this assertion looked for the joined string
    # and failed a file that was correct: the same "assume the shape instead of reading it"
    # mistake this file keeps cataloguing, committed inside the test that catalogues it.
    assert '"docker", "exec", probe_from' in blk and ":2019/config/" in blk, (
        "the admin check no longer PROVES isolation by attempting the connection from another "
        "container; it is back to inferring it from configuration")
    assert "ANSWERED a request from another container" in blk, (
        "a successful cross-container probe must be reported as EXPOSED")


def test_a_config_change_is_proven_to_propagate():
    """The valuable half of kimi's third risk.

    Every deploy writes, applies and then runs config_drift — so the reload path IS exercised, and
    the claim that it is not was wrong. But each run writes essentially the SAME config, so drift
    passing does not prove a DIFFERENT one would propagate. That is exactly the 6 Aug mechanism:
    the file changed and the process served the old bytes for twelve hours.
    """
    sg = _read(os.path.join(ROOT, "stagegate.py"))
    assert "config_change_propagates" in sg, (
        "nothing proves that a CHANGED config reaches the running proxy without a reboot")
    blk = sg[sg.index("DOES A CONFIG *CHANGE* ACTUALLY PROPAGATE"):]
    blk = blk[:blk.index("chk config_change_propagates no \"the probe vhost")]
    assert "rm -f /opt/caddyguard/blocks/zz__reloadprobe.caddy" in blk, (
        "the probe fragment is not removed — a test that can leave staging serving a probe vhost "
        "is an outage with a pass/fail label")
    # The revert must come BEFORE the pass/fail decision, so it runs whatever the result was.
    assert blk.index("rm -f /opt/caddyguard/blocks") < blk.index("SERVED_GONE"), (
        "the revert runs after the verdict, so a failure would leave the probe in place")
    assert "$CADDY\"" not in sg, (
        "a container-name variable that this script never defines is back — read the name, do not "
        "assume it")

# =================================================================================================
# TWO GREEN-BOX FAILURES, 10 Aug 2026. The staging gate said NO-GO on a healthy box and refused to
# promote a good build -- twice, for two different reasons, and BOTH were in the checking layer.
# The panel caught both; three of four models then proposed fixes to the SYSTEM, which was fine.
# =================================================================================================
def _agent_src():
    return open(os.path.join(ROOT, "deploy", "caddyguard", "agent.py"), encoding="utf-8").read()


def test_agent_verdict_is_the_first_line():
    """A machine-read verdict must be the FIRST line of stdout, and every UNINDENTED line is one.

    `cmd_admin` printed a diagnostic ("   probed from colt-web -> ...") BEFORE its verdict. The
    caller flattens the output and matches `OK*`, so a CORRECT result never matched, fell through
    to the wildcard -- which the day before I had (correctly) made a FAILURE -- and a healthy,
    properly isolated admin API was reported as EXPOSED, twice, blocking a good release.

    THE RULE IS NOT "every print starts with a token": continuation notes legitimately do not, and
    they are INDENTED, which is exactly what distinguishes them. So: any line that starts at column
    zero is a verdict and must say so. That also caught `cmd_drift` printing "[!] no caddy
    container" and returning 0 -- a SKIP wearing a pass's clothes.
    """
    import ast
    VERDICTS = ("OK", "SKIP", "DRIFT", "EXPOSED", "STALE", "MISSING")
    tree = ast.parse(_agent_src())
    checked = 0
    for fn in [n for n in ast.walk(tree)
               if isinstance(n, ast.FunctionDef)
               and n.name in ("cmd_admin", "cmd_roster", "cmd_drift")]:
        seen = False
        for node in ast.walk(fn):
            if not (isinstance(node, ast.Call) and getattr(node.func, "id", "") == "print"
                    and node.args):
                continue
            a = node.args[0]
            v = a.value if isinstance(a, ast.Constant) else (
                a.left.value if isinstance(a, ast.BinOp) and isinstance(a.left, ast.Constant)
                else None)
            if not isinstance(v, str) or not v.strip():
                continue                      # a formatted expression or a blank line
            if v[:1].isspace():
                continue                      # an indented note, which is allowed AFTER a verdict
            seen = True
            assert v.split()[0] in VERDICTS, (
                "%s line %d prints the unindented line %r, which is not a verdict token %s. The "
                "caller matches on the first token, so this can never be classified."
                % (fn.name, node.lineno, v[:60], list(VERDICTS)))
        assert seen, "%s emits no literal verdict at all" % fn.name
        checked += 1
    assert checked == 3, "expected 3 verdict-emitting commands, checked %d" % checked


def test_agent_admin_prints_its_verdict_first_when_RUN():
    """The static check above cannot see ordering, so RUN the command and read line 1.

    The mutation that reproduces the real defect prints a FORMATTED note (`print(n)`) before the
    verdict. That is not a string literal, so an AST check skips it and reports green -- which is
    precisely the "a check that reasons about its subject is weaker than one that reproduces it"
    lesson that produced the container-to-container admin probe in the first place. So: stub docker
    to describe a HEALTHY box, run cmd_admin, and assert the first line is the verdict.
    """
    import io, contextlib, types
    spec = importlib.util.spec_from_file_location(
        "cg_agent", os.path.join(ROOT, "deploy", "caddyguard", "agent.py"))
    ag = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ag)

    def fake_sh(cmd, **kw):
        j = " ".join(cmd)
        out = ""
        if "/config/" in j:
            out = "" if "wget" in j and ":2019" in j and "exec" in j and "127.0.0.1" not in j else \
                  '{"admin": {"listen": "localhost:2019"}}'
        elif ".NetworkSettings.Networks" in j:
            out = "172.18.0.2 "
        elif ".State.Running" in j:
            out = "true"
        elif "ps" in j:
            out = ""                      # no published ports
        return types.SimpleNamespace(stdout=out, stderr="", returncode=0)

    ag.sh = fake_sh
    ag.container = lambda *a, **k: "videodead-caddy"
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = ag.cmd_admin()
    lines = [x for x in buf.getvalue().splitlines() if x.strip()]
    assert lines, "cmd_admin printed nothing at all"
    first = lines[0].split()[0]
    assert first in ("OK", "SKIP", "EXPOSED"), (
        "cmd_admin's FIRST line is %r, not a verdict. The caller does `case $AD in OK*)`, so a "
        "healthy box scores as a failure -- which is exactly what blocked two good releases."
        % lines[0][:80])
    assert rc == 0, "a healthy, loopback-only admin API must not return non-zero"


def test_propagation_check_actually_applies():
    """`agent.py assemble` WITHOUT --apply writes nothing and reloads nothing.

    config_change_propagates wrote a probe vhost, called plain `assemble`, then asserted the vhost
    had reached the running config. It never could: `cmd_assemble(do_apply)` only calls apply()
    when the flag is present. So the check reported the 2026-08-07 latent-outage mechanism on a box
    where nothing was wrong, and blocked promotion twice.
    kimi-k2.6 was right that the check was broken by construction; its proposed fix (call `caddy
    reload` directly) was wrong -- the guard's own validate-then-apply path is what production uses,
    and testing anything else would prove nothing about production.
    """
    src = open(os.path.join(ROOT, "stagegate.py"), encoding="utf-8").read()
    body = src[src.index("config_change_propagates"):]
    body = body[:body.index("#### KERNEL")] if "#### KERNEL" in body else body
    calls = re.findall(r"agent\.py assemble(?: --apply)?", body)
    assert calls, "the propagation check no longer assembles anything"
    assert all(c.endswith("--apply") for c in calls), (
        "config_change_propagates calls `agent.py assemble` without --apply (%r). That command "
        "writes nothing and reloads nothing, so the check can only ever fail." % calls)
    assert "cmd_assemble(\"--apply\" in rest)" in _agent_src(), (
        "agent.py no longer gates apply on --apply; re-read this test's premise before changing it")

