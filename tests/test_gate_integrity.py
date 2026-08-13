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


def test_propagation_check_is_non_destructive():
    """The propagation check may never be able to empty the proxy it is testing.

    THE DOCTRINE HERE IS NOW THE OPPOSITE OF THE FIRST VERSION, and the reason is kept rather than
    deleted. The first version asserted that the check calls `agent.py assemble --apply`, because
    plain `assemble` writes and reloads nothing and the check could only ever fail. True, and the
    wrong fix: STAGING IS NOT FRAGMENT-MANAGED. Its Caddyfile is composed directly by the
    provisioning step, so /opt/caddyguard/blocks/ held nothing but the probe; the reassembly was
    EMPTY, apply() wrote it, Caddy carried on serving from memory, and the reboot detonated it —
    post_reboot_proxy_routes 000, roster MISSING cybergod.ai, Caddyfile hash 01ba4719c80b, which is
    the sha256 of a single newline. The check written to detect the 2026-08-07 outage caused one.
    The property is therefore no longer "does it apply" but "can it destroy anything": snapshot the
    live bytes, APPEND to the config that is actually live, apply through the guard's own
    validate-write-mount-reload path, restore the snapshot, and VERIFY the restore.
    """
    src = open(os.path.join(ROOT, "stagegate.py"), encoding="utf-8").read()
    body = src[src.index("config_change_propagates"):]

    assert "agent.py assemble" not in body, (
        "the propagation check rebuilds the config from /opt/caddyguard/blocks/ again. On a box "
        "that is not fragment-managed that assembly is EMPTY and wipes the live proxy.")
    assert "docker inspect -f" in body and "/etc/caddy/Caddyfile" in body, (
        "the check must READ the proxy's own bind-mount source, never assume a path")
    assert "cp -p" in body and "/tmp/cg_snapshot.caddy" in body, "it must snapshot the live bytes"
    assert "cmp -s /tmp/cg_snapshot.caddy" in body, "and VERIFY the restore, not hope for it"
    assert "NOT restored byte-for-byte" in body, "a failed restore must be a FAILURE"


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


def test_apply_refuses_to_empty_a_live_proxy():
    """The guardrail that would have prevented the outage regardless of the check's own bug.

    It lives in apply(), so it protects EVERY caller — caddyguard, the 10-minute watchdog, any
    future script — not just the one check that failed. The behaviour is proven end-to-end in
    hermes-skills/shodan-assessment/scripts/test_drift.py, which ship.py runs as BLOCKING; this
    asserts the guard exists, runs BEFORE the write, and that the escape is explicit.
    """
    src = open(os.path.join(ROOT, "deploy", "caddyguard", "agent.py"), encoding="utf-8").read()
    body = src[src.index("def apply(text"):]
    body = body[:body.index("\ndef ")]
    assert "site_blocks(text)" in body and "site_blocks(before)" in body, (
        "apply() no longer compares the sites it is about to write against the sites now live")
    assert "CADDYGUARD_ALLOW_EMPTY" in body, (
        "emptying a proxy must remain possible, but only by an explicit, named opt-in")
    assert body.index("old_sites and not new_sites") < body.index("write_inplace(LIVE, text)"), (
        "the empty-config guard must refuse BEFORE anything is written, not after")




# --------------------------------------------------------------------------------------
# THE PANEL'S OWN INTEGRITY. The safeguard that HALTS a green gate on a unanimous NO-GO needs
# >= 3 reviewers. gemma has now dropped out on two consecutive runs, so at one more dropout the
# safeguard is silently disarmed and nothing says so. And its dropout was OUR fault: max_tokens
# was 900 while the panel's own contract permits ~1020 tokens of content, so the JSON was cut
# mid-string and reported as "did not answer" - blaming the model for our ceiling.
# --------------------------------------------------------------------------------------

def _q():
    with open(os.path.join(ROOT, "deploy", "stagegate", "quorum.py"), encoding="utf-8") as fh:
        return fh.read()


def test_the_panel_can_actually_fit_its_own_contract():
    """reasons(3x400) + risks(3x400) + diagnosis(500) + proposed_fix(500) ~= 1020 tokens."""
    s = _q()
    m = re.search(r"max_tokens=(\d+)", s)
    assert m, "the panel no longer states a token ceiling"
    assert int(m.group(1)) >= 1400, (
        "max_tokens=%s truncates the panel's own contract — that is what made gemma 'fail'"
        % m.group(1))


def test_a_truncated_answer_is_not_blamed_on_the_model():
    s = _q()
    assert "max_tokens ceiling, not the model" in s, \
        "a cut-off JSON is reported as the model failing, which sent two reviews down a blind alley"


def test_below_quorum_is_announced():
    """A safeguard that cannot fire must say so. Silence is indistinguishable from 'it passed'."""
    s = _q()
    assert "PANEL BELOW QUORUM" in s, "nothing warns when the unanimous-NO-GO halt cannot fire"
    assert "len(answered) < 3" in s, \
        "the warning threshold no longer matches the >=3 the halt rule requires"
    # And it must agree with the rule it describes.
    with open(os.path.join(ROOT, "stagegate.py"), encoding="utf-8") as fh:
        st = fh.read()
    assert "len(revs) >= 3" in st, "the halt rule's quorum changed; the warning now lies"


def test_the_bot_gate_only_warns_about_bots_it_did_not_mean_to_allow():
    """Googlebot and Bingbot are allowed BY DESIGN (the SEO fix). Flagging that every run is how
    the roster warning went stale and stopped being read."""
    with open(os.path.join(ROOT, "check_bot_gate.py"), encoding="utf-8") as fh:
        s = fh.read()
    assert "_INTENTIONALLY_ALLOWED" in s, "the intended allow-list is not named"
    cond = [ln for ln in s.splitlines()
            if "elif blocked <" in ln or (ln.strip().startswith("elif") and "blocked" in ln)]
    assert cond, "the warning's condition disappeared"
    assert any("_INTENTIONALLY_ALLOWED" in ln for ln in cond), (
        "the warning fires whenever ANY bot is served (%s) — Googlebot and Bingbot are allowed on "
        "purpose, so that flags a correct configuration on every single run" % "; ".join(cond))


def test_model_watch_runs_where_it_can_see_the_catalog():
    """It printed 'catalog unavailable - skipping' on every run since it was written, so the
    NEW/DISAPPEARED-model diff it exists to produce has never once been computed."""
    with open(os.path.join(ROOT, "ship.py"), encoding="utf-8") as fh:
        s = fh.read()
    i = s.index("os.path.join(_eng, 'model_watch.py')")
    seg = s[i:i + 900]
    assert "docker exec colt-web" in seg, \
        "model_watch still only runs on the PC, where OPENAI_API_KEY does not exist"


def test_no_check_implies_a_bare_file_edit_propagates():
    """The 2026-08-07 outage was a config edited and silently not applied for twelve hours. A
    check whose detail reads 'propagated with no restart' teaches exactly that belief, even
    though the check itself goes through an explicit reload. Name the mechanism."""
    with open(os.path.join(ROOT, "stagegate.py"), encoding="utf-8") as fh:
        s = fh.read()
    claims = [ln for ln in s.splitlines()
              if "chk config_change_propagates yes" in ln and "running config" in ln]
    assert claims, "no pass branch claims a change reached the running config"
    for d in claims:
        assert "EXPLICIT caddy reload" in d or "agent.apply" in d, \
            "a branch claims propagation without saying HOW: %s" % d[:120]
        assert "a bare file edit does NOT propagate" in d, \
            "nothing warns that editing the file alone is not enough — that belief IS the outage"


def test_every_committed_caddy_block_is_checked_against_the_repo():
    """CONSISTENCY IS NOT AUTHENTICITY (raised by kimi-k2.6, 11 Aug 2026, and correct).

    mount_fresh and config_drift prove the three hops agree with each other. Neither asks whether
    the file is OURS. caddyguard makes that worse by design: `migrate` re-splits whatever is LIVE
    into fragments, so a hand-edit on the droplet is captured and `assemble` writes it back.
    Only the jhw block was ever compared to its committed counterpart.
    """
    import importlib.util as _u
    sp = _u.spec_from_file_location("cg", os.path.join(ROOT, "caddyguard.py"))
    m = _u.module_from_spec(sp)
    sp.loader.exec_module(m)
    script = m.build(restore=True, check_only=False)

    committed = [f for f in os.listdir(os.path.join(ROOT, "deploy", "caddy"))
                 if f.endswith(".caddy")]
    assert committed, "no committed caddy blocks found — has the layout changed?"
    for f in committed:
        stem = f.replace(".caddy", "")
        frag = {"cybergod": "colt__cybergod", "jobhuntwow": "jhw__jobhuntwow"}.get(stem)
        assert frag, "committed block %s has no known fragment name — add it to the map" % f
        assert frag + ".caddy" in script, (
            "%s is committed but caddyguard never compares the live fragment to it — a host-side "
            "edit would be migrated into the fragment and reassembled, surviving every ship" % f)
    live = "\n".join(ln for ln in script.splitlines() if not ln.strip().startswith("#"))
    assert "TAMPER" in live, (
        "a difference from the repo is not REPORTED as tampering on any line the operator sees "
        "(the word survives only in a comment)")


# =============================================================================================
# 2026-08-13 RUN REVIEW. Two of these came from the panel; the biggest came from reading the log.
# =============================================================================================

def _agent_src():
    with open(os.path.join(ROOT, "deploy", "caddyguard", "agent.py"), encoding="utf-8") as fh:
        return fh.read()


def test_a_damaged_live_config_alerts_instead_of_printing_quietly():
    """THE ITEM NO MODEL FLAGGED, and it was in the log in capital letters.

    The 2026-08-13 run captured `jhw:jobhuntwow 14 lines braces 3/2 <-- UNBALANCED` from the LIVE
    shared Caddyfile. migrate splits whatever is currently live, so that is not a bad fragment: it
    is proof the file on disk was damaged at that moment. Caddy reads config only at start, so the
    running process kept serving fine from memory and nothing looked wrong - which is precisely
    the 12-hour latent gap that took every domain on the box down together on 6 August.
    It was PRINTED, inside a table, in a deploy log nobody re-reads, and then quietly repaired.
    Silent repair of recurring damage means whatever is causing it is never found.
    """
    body = _agent_src()
    mig = body[body.index("def cmd_migrate"):body.index("def cmd_restore")]
    assert "broken.append" in mig, "unbalanced blocks are printed but never collected"
    assert "notify(" in mig, (
        "a damaged LIVE shared config does not reach a human; it is invisible until a reboot")
    assert mig.rstrip().endswith("return 0"), (
        "migrate now fails the deploy on damage it repairs itself, which trains the operator "
        "to reach for --force")


def test_the_refusal_path_is_exercised_without_touching_live_state():
    """kimi-k2.6: only the happy path is tested. True, and an earlier fix for it wrote a broken
    fragment into the LIVE blocks directory and took staging down. agent.py selftest feeds garbage
    to validate(), which uses a temp dir and a THROWAWAY container, then asserts the live file's
    hash is unchanged."""
    body = _agent_src()
    st = body[body.index("def cmd_selftest"):body.index("def main(")]
    assert "validate(" in st and "site_blocks(" in st
    # NEVER ASSUME `LIVE`. It defaults to PRODUCTION's /opt/videodead/Caddyfile; staging's proxy
    # mounts a different path, so the first version read "" there, validated an empty string, and
    # reported "the LIVE config does not validate" about a healthy box - failing the gate and
    # refusing a good release. mount_source() exists three functions above for exactly this, and
    # its docstring says NEVER ASSUME LIVE in capital letters. All four review models diagnosed it
    # correctly as a broken check rather than a broken system.
    assert "mount_source(" in st, (
        "cmd_selftest reads the hardcoded LIVE path instead of asking docker where THIS "
        "container's config actually comes from; on staging that file does not exist")
    assert "if not before.strip():" in st, (
        "an unreadable or empty config source must SKIP, not FAIL - absence of evidence is never "
        "a finding, and that is the oldest rule in this repository")
    assert "read(LIVE)" not in st, "a direct read(LIVE) survives in cmd_selftest"
    assert "h0 != h1" in st, "the selftest does not prove it left the live file alone"
    assert "if not live_ok" in st, (
        "nothing requires the LIVE config to still validate; a validator that rejects everything "
        "would pass a reject-the-garbage test perfectly and be useless")
    # EVERY use must be wrapped, not just one. The first version asserted `len(site_blocks(` was
    # present somewhere, so unwrapping ONE of the two calls left it green - a check that passes
    # because a sibling line is still correct is measuring the sibling.
    bare = [ln.strip() for ln in st.splitlines()
            if re.search(r"=\s*site_blocks\(", ln) and "len(site_blocks(" not in ln]
    assert not bare, (
        "site_blocks() returns a LIST; comparing it to an integer raises TypeError the first "
        "time this runs on the droplet: %s" % bare)
    assert 'if cmd == "selftest"' in body, (
        "selftest is defined but never reachable from the command line")

    with open(os.path.join(ROOT, "stagegate.py"), encoding="utf-8") as fh:
        sg = fh.read()
    # STRIP THE COMMENTS FIRST. My comment above the invocation contains the words
    # "agent.py selftest", so grepping the raw file passed even when the real command was renamed
    # AND when the whole line was commented out. This repository has now paid for this exact
    # lesson four times (the brand gate, recover.py, the caddyguard TAMPER check, this).
    sg_live = "\n".join(ln for ln in sg.splitlines() if not ln.strip().startswith("#"))
    # Two separate claims: the gate INVOKES the agent, and it RECORDS a verdict from it. Asserting
    # only that the name appears somewhere passed even when one of three branches was renamed.
    assert "agent.py selftest" in sg_live, "the staging gate never invokes the refusal check"
    assert re.search(r"^\s*ST=\$\(python3", sg_live, re.M), (
        "the refusal check's output is never captured, so no branch can read it")
    assert len(re.findall(r"chk\s+refuses_bad_config\s+(yes|no)", sg)) >= 3, (
        "the refusal check has no complete OK/SKIP/fallback verdict set, so an unrecognised "
        "answer would fall through - the exact defect that scored a FAIL as a PASS on 11 Aug")


def test_check_details_are_wrapped_not_truncated():
    """kimi-k2.6, and it was right. The detail is where a check states WHAT it measured, so
    cutting it mid-word destroys exactly the evidence the check exists to provide - silently, on
    the passing path. It also feeds the review panel, so a reviewer reads half the facts."""
    with open(os.path.join(ROOT, "stagegate.py"), encoding="utf-8") as fh:
        sg = fh.read()
    line = [ln for ln in sg.splitlines() if 'c["name"], "OK "' in ln]
    assert line, "could not find the check-printing line"
    assert '_d[:90]' in sg and "_rest" in sg, (
        "check details are still truncated with no continuation; a cut-off detail reads as a "
        "logging bug and hides what the check actually proved")


def test_an_unrecognised_patchwatch_state_is_never_read_as_healthy():
    """`systemctl is-enabled` prints 'not-found' for a missing unit. The first version only knew
    'absent' and None, so the 2026-08-13 run printed `patchwatch_timer: not-found` for STAGING and
    then reported OK: nothing applies security updates to that box unattended and the audit said
    it was fine."""
    import importlib
    sa = importlib.import_module("secaudit")
    base = {"kernel_stale": "no", "reboot_required": "no", "security": "0",
            "unattended": None, "running": "x", "distro": "x"}
    for state in ("not-found", "absent", "disabled", "masked", None, ""):
        _bad, warn = sa.verdict("t", dict(base, patchwatch=state))
        assert any("patchwatch" in w for w in warn), (
            "patchwatch=%r was treated as healthy" % state)
    _bad, warn = sa.verdict("t", dict(base, patchwatch="enabled"))
    assert not any("patchwatch" in w for w in warn), "an enabled timer must not warn"
