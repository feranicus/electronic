"""The scanner is a supply-chain dependency, and this one has been compromised before.

WHAT HAPPENED, and why these assertions exist (SecurityWeek, 23 Mar and 12 Aug 2026):
  Aqua's Trivy was compromised in late Feb 2026. After the 1 Mar disclosure the credential
  rotation was NOT atomic, so the attacker used a still-valid token to take the newly rotated
  secrets, and a second wave (~16-21 Mar) pushed a malicious Trivy v0.69.4 to GHCR, Amazon ECR
  Public and Docker Hub, force-pushed 76 of 77 trivy-action tags and every setup-trivy tag. The
  payload dumped Runner.Worker PROCESS MEMORY and took every secret in the job.
  LiteLLM was then compromised *because its CI installed the poisoned Trivy automatically*:
  2,500+ organisations and 434,000 pipelines, from one unrevoked token, three tools deep.

WE WERE NOT AFFECTED. The evidence is dates, not optimism: this repository's first commit is
2026-07-09, months after the window; we never used trivy-action or setup-trivy; and we have no
dependency on LiteLLM anywhere. But the SHAPE of the failure was live in our CI until this
change: `curl .../main/contrib/install.sh | sh` pulls an installer from a MOVING BRANCH and takes
whatever the newest release happens to be, inside a job holding DROPLET_SSH_KEY.

Every assertion below is negative-tested. A gate that has never failed is not a gate, which is
also the reason the second half of this file exists at all: all four Trivy calls used
--exit-code 0, and deploy.yml literally documented the intent ("flip --exit-code to 1 to gate")
without ever doing it.
"""
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOWS = [os.path.join(ROOT, ".github", "workflows", f)
             for f in ("deploy.yml", "security.yml")]


def _text(p):
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def _steps(path):
    d = yaml.safe_load(_text(path))
    for job in (d.get("jobs") or {}).values():
        for st in job.get("steps") or []:
            yield st


# ---------------------------------------------------------------------------------------------
# 1. THE INSTALL ITSELF
# ---------------------------------------------------------------------------------------------

def test_trivy_is_never_installed_from_a_moving_branch():
    """The LiteLLM mechanism, verbatim: CI installed a poisoned Trivy automatically."""
    for p in WORKFLOWS:
        s = _text(p)
        body = "\n".join(ln for ln in s.splitlines() if not ln.strip().startswith("#"))
        assert "contrib/install.sh" not in body, (
            "%s installs Trivy from a branch script; pin a release instead" % os.path.basename(p))
        assert "/main/" not in body or "raw.githubusercontent.com/aquasecurity" not in body, (
            "%s still fetches an aquasecurity asset from a moving ref" % os.path.basename(p))


def test_trivy_version_is_pinned_and_is_a_clean_one():
    """v0.69.4 was the MALICIOUS release. v0.69.2 and v0.69.3 are the ones Aqua published clean."""
    for p in WORKFLOWS:
        s = _text(p)
        m = re.search(r'TRIVY_VERSION:\s*"?([0-9.]+)"?', s)
        assert m, "%s does not pin a Trivy version" % os.path.basename(p)
        v = m.group(1)
        assert v != "0.69.4", "0.69.4 IS the compromised release"
        assert v in ("0.69.2", "0.69.3"), (
            "%s pins Trivy %s, which is not one of the versions confirmed clean" % (p, v))


def test_the_binary_is_checksum_verified_before_it_runs():
    """Pinning a version is not enough on its own: the attacker replaced published artifacts."""
    for p in WORKFLOWS:
        s = _text(p)
        assert "sha256sum -c" in s, (
            "%s does not verify the Trivy checksum before executing it" % os.path.basename(p))
        i_sum, i_run = s.index("sha256sum -c"), s.rindex("trivy --version")
        assert i_sum < i_run, "the checksum is verified AFTER the binary is run"


def test_we_do_not_use_the_two_worst_hit_vectors():
    """76 of 77 trivy-action tags and every setup-trivy tag were force-pushed to malware."""
    for p in WORKFLOWS:
        body = "\n".join(ln for ln in _text(p).splitlines() if not ln.strip().startswith("#"))
        for vector in ("trivy-action", "setup-trivy"):
            assert vector not in body, "%s uses %s, which was force-pushed to an infostealer" % (
                os.path.basename(p), vector)


# ---------------------------------------------------------------------------------------------
# 2. THE GATE. A scanner whose findings nobody acts on is a log file with a licence.
# ---------------------------------------------------------------------------------------------

def test_critical_findings_actually_fail_the_build():
    seen = 0
    for p in WORKFLOWS:
        for st in _steps(p):
            run = st.get("run") or ""
            if "trivy image" not in run and "trivy fs" not in run:
                continue
            if "CRITICAL" not in run:
                continue
            seen += 1
            crit = [ln for ln in run.splitlines() if "CRITICAL" in ln and "--exit-code" in ln]
            assert crit, "a CRITICAL scan step with no --exit-code: %s" % st.get("name")
            assert all("--exit-code 1" in ln for ln in crit), (
                "CRITICAL does not fail the build in step %r" % st.get("name"))
    assert seen >= 2, "expected CRITICAL gates on the images and the filesystem scan"


def test_each_scan_step_is_a_real_multi_line_command():
    """A plain YAML scalar FOLDS its continuation lines into ONE string. The first version of this
    change produced `trivy image ... trivy image ...` as a single nonsense command: valid YAML,
    broken shell. Parsing is not correctness."""
    for p in WORKFLOWS:
        for st in _steps(p):
            run = st.get("run") or ""
            if run.count("trivy image") + run.count("trivy fs") < 2:
                continue
            lines = [ln.strip() for ln in run.strip().splitlines() if ln.strip()]
            n_cmds = run.count("trivy image") + run.count("trivy fs")
            assert len(lines) >= n_cmds, (
                "step %r has %d trivy commands on %d line(s): a plain YAML scalar folded them "
                "into one shell command" % (st.get("name"), n_cmds, len(lines)))
            assert all(ln.startswith("trivy") for ln in lines), (
                "step %r has a non-command line in a trivy block" % st.get("name"))


def test_the_allowlist_demands_a_reason():
    p = os.path.join(ROOT, ".trivyignore")
    assert os.path.exists(p), "no .trivyignore, so a gate failure has no reviewed escape hatch"
    s = _text(p)
    assert "reason" in s.lower() and "date" in s.lower(), (
        "the allowlist does not require a reason and a date; an unexplained allowlist is "
        "--exit-code 0 with extra steps")
    for ln in s.splitlines():
        if ln.strip().startswith("CVE-"):
            assert "#" in ln, "allowlisted %s carries no reason" % ln.split()[0]


# ---------------------------------------------------------------------------------------------
# 3. THE IMAGE NOBODY WAS SCANNING
# ---------------------------------------------------------------------------------------------

def test_colt_web_is_scanned_where_it_is_built():
    """Trivy saw colttechbot and cassandra in CI. colt-web is built on the droplet by
    deploy_web_direct.py and was never scanned at all, despite being the only image on the
    internet."""
    s = _text(os.path.join(ROOT, "deploy_web_direct.py"))
    assert "trivy image" in s, "colt-web is still built without ever being scanned"
    assert "--exit-code 1" in s, "the colt-web scan cannot fail the deploy"
    assert "sha256sum -c" in s, "Trivy is fetched on the droplet without checksum verification"


def test_the_colt_web_verdict_is_consumed_not_just_printed():
    """The first cut echoed TRIVY_CRITICAL_FAIL and nothing read it, which is the same
    prints-but-does-not-gate defect this file exists to prevent."""
    s = _text(os.path.join(ROOT, "deploy_web_direct.py"))
    assert s.count("TRIVY_CRITICAL_FAIL") >= 2, "the marker is emitted but never inspected"
    i_emit = s.index("TRIVY_CRITICAL_FAIL")
    i_check = s.index('if "TRIVY_CRITICAL_FAIL" in out')
    assert i_check > i_emit
    assert "sys.exit" in s[i_check:i_check + 400], "the marker is read but does not stop the deploy"


# ---------------------------------------------------------------------------------------------
# 4. THE KERNEL CADENCE. 432 CVEs in two days cannot be triaged; cadence is the only lever.
# ---------------------------------------------------------------------------------------------

def test_the_audit_measures_cadence_not_cve_counts():
    s = _text(os.path.join(ROOT, "secaudit.py"))
    for probe in ("kernel_stale", "reboot_required", "patchwatch_timer", "unattended-upgrades"):
        assert probe in s, "secaudit does not measure %s" % probe
    assert "read-only" in s.lower() or "READ-ONLY" in s, "the audit must not change the host"
    for mutating in ("apt-get install", "apt-get upgrade\n", "systemctl restart", "shutdown"):
        assert mutating not in s, "secaudit performs a mutating action: %r" % mutating


def test_an_unreadable_host_is_never_reported_as_healthy():
    """Absence of evidence is not a clean bill of health. The oldest rule in this repository."""
    s = _text(os.path.join(ROOT, "secaudit.py"))
    assert "could not read kernel state" in s, (
        "a host whose kernel state could not be read must be flagged, not passed")


# ---------------------------------------------------------------------------------------------
# 5. THE THREE WARNINGS FROM THE 2026-08-13 DEPLOY. Two were defects in my own new checks.
# ---------------------------------------------------------------------------------------------

def test_the_live_header_check_does_not_announce_itself_as_a_bot():
    """It sent `Mozilla/5.0 (compatible; cybergod-verify)`. `(compatible;` is the classic crawler
    marker, so visitors.classify() called it a bot, BOT_404 answered 404, and the check reported
    "could not read the live security headers" about a site that was serving them perfectly.
    CLAUDE.md records this exact blind spot - it is what let www.cybergod.ai report healthy while
    returning 404 for weeks - and I wrote the warning comment and then walked into it.
    """
    sys.path.insert(0, ROOT)
    sys.path.insert(0, os.path.join(ROOT, "webapp", "backend"))
    import check_bot_gate as bg
    from app import visitors

    ship = _text(os.path.join(ROOT, "ship.py"))
    body = "\n".join(ln for ln in ship.splitlines() if not ln.strip().startswith("#"))
    assert "cybergod-verify" not in body, (
        "the live header check still sends a bot-shaped user agent; the gate will 404 it")
    assert "_bg2.BROWSER[1]" in body, (
        "the header check should reuse check_bot_gate.BROWSER so there is ONE browser UA in "
        "this repo and it cannot drift")

    class _Req(object):
        def __init__(self, ua):
            self.headers = {"user-agent": ua}
            self.url = type("U", (), {"path": "/"})()

    assert visitors.classify(_Req(bg.BROWSER[1])).get("bot") is not True, (
        "the shared browser UA is itself classified as a bot")


def test_a_damaged_config_alert_can_actually_reach_a_human():
    """The alert fired correctly on the real run and then printed "no telegram credentials".
    An alert nobody receives is not an alert. The host has no token; colt-web does, and it already
    resolves the chat the full way - so ask it, rather than giving the agent a SECOND home for a
    credential."""
    s = _text(os.path.join(ROOT, "deploy", "caddyguard", "agent.py"))
    body = s[s.index("def notify("):s.index("def cmd_migrate")]
    assert "docker" in body and "colt-web" in body, (
        "notify() gives up when the host has no token instead of asking the app that has one")
    assert "input=text.encode" in body, (
        "the alert text must go over STDIN, not argv: it can contain an attacker-shaped path, "
        "and argv has a length limit that already broke one payload in this repo")
    # BOTH halves, not just the call. The first version asserted only `notify.telegram`, so
    # deleting the import left a command that could never run and the check still passed - a
    # check aimed at half its subject cannot fail for the right reason.
    assert "from app import notify" in body, (
        "the fallback never imports the app's notifier, so the command it runs would fail")
    assert "notify.telegram" in body, "it should reuse the app's own notifier, not reimplement it"


def test_the_patchwatch_warning_is_scoped_to_where_it_is_actionable():
    """Staging is a DISPOSABLE TWIN, rebuilt every ship; an unattended patcher there could reboot
    it mid-validation. A warning that fires benignly on every run trains the operator to ignore
    the one that does not."""
    sys.path.insert(0, ROOT)
    import secaudit
    base = {"kernel_stale": "no", "reboot_required": "no", "security": "0",
            "unattended": None, "running": "6.8.0-137-generic", "distro": "x"}
    _b, w = secaudit.verdict("production", dict(base, patchwatch="not-found"))
    assert any("patchwatch" in x for x in w), "production with no patcher must still warn"
    _b, w = secaudit.verdict("staging", dict(base, patchwatch="not-found"))
    assert not any("patchwatch" in x for x in w), (
        "staging warns about a patcher it should not have, on every single run")


def test_a_drifted_twin_kernel_is_reported_by_the_real_code_path():
    """THE QUESTION THE OLD WARNING WAS GROPING AT. staging exists to run the one test production
    cannot: a real reboot. If its kernel has drifted, that reboot validates a kernel that will
    never ship and the gate's strongest check becomes decorative.

    This RUNS secaudit.main() against stubbed hosts rather than re-implementing the comparison -
    the first version of this check re-computed the expression itself and therefore proved nothing
    about the code that ships.
    """
    import contextlib
    import io
    sys.path.insert(0, ROOT)
    import secaudit

    def _fake(kernels):
        def run(host, timeout=180):
            k = kernels["production"] if host == secaudit.PROD else kernels["staging"]
            return 0, ("#### HOST\ndistro: x\n#### KERNEL\nrunning: %s\nkernel_stale: no\n"
                       "reboot_required: no\nsecurity: 0\nunattended-upgrades: enabled\n"
                       "patchwatch_timer: enabled\n" % k)
        return run

    real, real_argv = secaudit.run, sys.argv
    try:
        sys.argv = ["secaudit.py"]        # main() parses argv, and pytest owns the real one
        for kernels, expect_drift in (
                ({"production": "6.8.0-137-generic", "staging": "6.8.0-137-generic"}, False),
                ({"production": "6.8.0-137-generic", "staging": "6.8.0-131-generic"}, True)):
            secaudit.run = _fake(kernels)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = secaudit.main()
            out = buf.getvalue()
            if expect_drift:
                assert "TWIN DRIFT" in out, (
                    "staging on a different kernel is not reported, so the reboot test silently "
                    "validates something that will not ship:\n%s" % out[-400:])
                assert rc >= 1, "a drifted twin does not raise the exit code"
            else:
                assert "TWIN DRIFT" not in out, "matching kernels were reported as drift"
                assert "SAME kernel" in out, "the healthy twin case says nothing at all"
    finally:
        secaudit.run, sys.argv = real, real_argv
