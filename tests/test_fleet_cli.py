"""`python fleet.py` must tell the truth about the OTHER projects without a browser.

WHY IT EXISTS. The operator: "this is bull it will not show anything because it needs to show this
post IAM and IAM is on the server side". He is right -- the Admin -> Fleet page is behind the
session gate, so preview.py can never render it with real data, and sending him to look at it
locally is asking him to admire an empty box. This reads the droplet over ssh, like recover.py and
cost_report.py, which are the tools that have actually answered questions.

THE THREE QUESTIONS MUST STAY APART: the file is present · something imports it · it is running.
Conflating them is what made "copied" look like "installed" for days.
"""
import importlib.util
import json
import os
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location("fleetcli", os.path.join(ROOT, "fleet.py"))
F = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(F)


def _sec(events=(), containers="", wired="", beats=""):
    return {"CONTAINERS": containers, "WIRED": wired, "BEATS": beats,
            "EVENTS": "SIZE 1000\n" + "\n".join(json.dumps(e) for e in events)}


def test_present_but_unwired_is_reported_as_unguarded():
    """THE EXACT STATE THAT CAUSED THE SILENCE: the file is in the container and nothing imports
    it. A tool that showed only 'client file: present' would have called that installed."""
    out = F.render(F.analyse(_sec(
        containers="jhw-web\tUp 3 days",
        wired="jhw-web\t/app/app/perseus_client.py\tnone"), 24))
    assert "NO — nothing calls add_middleware" in out
    assert "UNGUARDED" in out and "jobhuntwow.com" in out


def test_wired_and_beating_is_not_reported_as_unguarded():
    now = int(time.time())
    out = F.render(F.analyse(_sec(
        events=[{"ts": now - 10, "evt": "http", "service": "colt-web", "ip": "1.1.1.1", "path": "/"}],
        containers="colt-web\tUp 1 hour",
        wired="colt-web\t/app/app/perseus_client.py\t/app/app/main.py",
        beats=json.dumps({"service": "colt-web", "ts": now - 5, "cycle": 9, "checks": 12})), 24))
    assert "heartbeat   : active" in out
    assert "cybergod.ai" not in out.split("UNGUARDED")[-1] if "UNGUARDED" in out else True


def test_a_stale_heartbeat_is_never_called_active():
    now = int(time.time())
    out = F.render(F.analyse(_sec(
        containers="colt-web\tUp 1 hour",
        beats=json.dumps({"service": "colt-web", "ts": now - 5000, "cycle": 9})), 24))
    assert "STALE" in out and "heartbeat   : active" not in out


def test_no_log_lines_is_blindness_not_safety():
    """The assertion this file exists for. A project shipping nothing must never read as quiet."""
    out = F.render(F.analyse(_sec(containers="jev-api\tUp 5 days"), 24))
    # Pin the HEADLINE as well as the explanation. A mutation that softened the headline to
    # "traffic: none" left the explanation untouched and went unnoticed -- a partial mutation
    # proves only that the part you asserted is still there.
    assert "NO LOG LINES AT ALL" in out
    assert "CANNOT SEE this project" in out
    assert "does not mean it is safe" in out
    assert "WE ARE BLIND TO" in out and "jev.best" in out


def test_a_missing_event_log_reports_nothing_rather_than_zeroes():
    """If the log is not there, every count is a statement about our blindness. Printing zeroes
    would be the logship defect: reporting success for work never done."""
    a = F.analyse({"CONTAINERS": "", "WIRED": "", "BEATS": "", "EVENTS": "NOLOG"}, 24)
    out = F.render(a)
    assert "not found on the droplet" in out
    assert "attack-shaped" not in out


def test_an_unimportable_classifier_is_admitted_not_counted_as_zero():
    """0 attacks by inability is not 0 attacks by measurement."""
    a = F.analyse(_sec(), 24)
    a["classifier"] = False
    out = F.render(a)
    # The phrase wraps across two printed lines, so assert on ONE line of it. A substring that
    # spans a line break can never match -- the same mistake as grepping with a padded regex.
    assert "inability, not by measurement" in out


def test_the_project_list_is_committed():
    """A list derived from the log could never report a project as missing."""
    svcs = {s for s, _ in F.PROJECTS}
    assert {"jhw-web", "jev-api", "polara-web", "colt-web"} <= svcs


def test_it_never_writes_to_the_droplet():
    """READ-ONLY. This tool is pointed at projects it does not own; a stray write would be an
    outage in somebody else's service to satisfy a status report."""
    src = open(os.path.join(ROOT, "fleet.py"), encoding="utf-8").read()
    code = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))
    for forbidden in ("docker restart", "docker stop", "rm -", " > /", "systemctl ", "docker rm"):
        assert forbidden not in code, "fleet.py must stay read-only: %r" % forbidden


def test_ssh_failure_decides_nothing():
    """A dead ssh is not evidence about anyone's security posture."""
    src = open(os.path.join(ROOT, "fleet.py"), encoding="utf-8").read()
    assert "BLIND is not the same as clean" in src


def test_the_generated_script_emits_a_PARSEABLE_size():
    """THE DEFECT THIS ASSERTS AGAINST CRASHED THE TOOL ON ITS FIRST REAL RUN.

        ValueError: invalid literal for int() with base 10: '%s'

    `_script()` builds its text with "\\n".join(...) and NO %-formatting, so writing `stat -c%%s`
    was wrong: stat received `%%s` and printed the literal `%s`. This repository's standing rule
    -- a literal % in a %-FORMATTED string must be doubled -- does not apply to a plain string, and
    applying it there breaks the command.

    AND THE OLD FIXTURE COULD NEVER HAVE CAUGHT IT, because it fed "SIZE 1000" straight in and
    bypassed the generator entirely. A fixture that does not exercise the code under test is a test
    of the fixture. So run the real script fragment.
    """
    src = F._script(24)
    assert "stat -c%s" in src and "%%s" not in src

    import shutil
    import subprocess
    if not shutil.which("bash"):
        import pytest
        pytest.skip("no bash here; the image build and CI run this")
    # NO HOST PATH CROSSES THE BOUNDARY. The first version wrote a temp file with tempfile and put
    # its path in the script -- on Windows that is `L=C:\Users\...`, which bash cannot resolve, so
    # `[ -f $L ]` was false and it printed nothing. That is the same trap as passing a Windows path
    # to `bash -n` instead of piping the script on stdin, and it failed on the operator's machine
    # while passing in a Linux sandbox. The script now creates its own file in bash's own
    # filesystem, so the check is about `stat -c%s` and nothing else.
    script = ('D=$(mktemp -d)\nL="$D/events.log"\nprintf "%4242s" "" > "$L"\n'
              'if [ -f "$L" ]; then echo "SIZE $(stat -c%s "$L")"; fi\nrm -rf "$D"\n')
    r = subprocess.run(["bash"], input=script.encode("utf-8"), capture_output=True)
    out = (r.stdout or b"").decode().strip()
    assert out.startswith("SIZE "), "bash said %r / %r" % (out, (r.stderr or b"").decode()[:200])
    assert int(out.split()[1]) == 4242, "stat must print a NUMBER, not a literal %s"


def test_an_unreadable_size_is_not_read_as_a_missing_log():
    """'The log is gone' and 'I could not read its size' are different facts. Collapsing them would
    report a healthy, busy log as missing -- and then print nothing about a real attack."""
    now = int(time.time())
    ev = [{"ts": now - 10, "evt": "http", "service": "jhw-web", "ip": "1.2.3.4", "path": "/.env"}]
    sec = {"CONTAINERS": "", "WIRED": "", "BEATS": "",
           "EVENTS": "SIZE %s\n" + "\n".join(json.dumps(e) for e in ev)}
    a = F.analyse(sec, 24)
    assert a["log_size"] == -1 and a["nolog"] is False
    out = F.render(a)
    assert "not found on the droplet" not in out
    assert "size unreadable" in out
    assert "jobhuntwow.com" in out


def test_an_explicit_NOLOG_still_reports_nothing():
    a = F.analyse({"CONTAINERS": "", "WIRED": "", "BEATS": "", "EVENTS": "NOLOG"}, 24)
    assert a["nolog"] is True
    assert "not found on the droplet" in F.render(a)
