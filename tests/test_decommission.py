"""Retiring a site from the SHARED droplet, without repeating 2026-08-07.

That outage: a deploy truncated another project's block in the shared Caddyfile, Caddy served from
memory for twelve hours, and the next kernel reboot took cybergod.ai, godeyes.ai, jobhuntwow.com
and klimaanlage-preise.de down together for six hours. Removing a site is exactly the operation
that caused it, so these tests pin the properties that make it safe:

  * it REFUSES when a fragment also serves a domain nobody asked to remove;
  * it backs up before it moves anything, and reassembles only through the guard;
  * it disables the restart policy BEFORE stopping, or the container returns at the next reboot;
  * it never deletes data;
  * it verifies that the surviving sites still answer.
"""
import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

D = pytest.importorskip("decommission")


def _bash_ok(script, tmp_path, name):
    """Syntax-check a script by piping it to `bash -n` on STDIN, never via a path.

    THE FIRST VERSION WROTE A TEMP FILE AND PASSED ITS PATH. That works on Linux, where I checked
    it, and fails on Windows: pytest's tmp_path is `C:\\Users\\...`, and the bash on that machine
    cannot resolve a Windows drive path -- it received `C:UsersferanAppData...` with the
    backslashes eaten and answered "No such file or directory", exit 127. The scripts were valid
    the whole time; the harness was not portable. Eighth instance in this repository of validating
    on one toolchain and handing the operator another.

    stdin has no path to mangle, so it behaves identically everywhere. BYTES, not text: Python's
    text mode on Windows rewrites every \\n into \\r\\n and bash then chokes on the \\r, which is
    the same CRLF trap already recorded for the ssh payloads and for `git archive`.
    """
    if not shutil.which("bash"):
        pytest.skip("no bash on PATH - the image build and CI still run this check")
    r = subprocess.run(["bash", "-n"], input=script.encode("utf-8"),
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return r.returncode, r.stderr.decode("utf-8", "replace")


@pytest.mark.parametrize("name", ["plan", "apply", "undo"])
def test_every_generated_script_is_valid_bash(name, tmp_path):
    """A remote script is assembled by %-formatting, and a stray placeholder or a mangled
    parameter expansion is invisible until it runs on the droplet. This repository has already
    shipped one `printf '%%s'` bug and one `%]` format error that masked a real traceback."""
    s = {"plan": lambda: D.plan_script(D.DEFAULT_SITES),
         "apply": lambda: D.apply_script(["a.caddy"], ["polara-web"], "20260901-120000"),
         "undo": lambda: D.undo_script("20260901-120000")}[name]()
    rc, err = _bash_ok(s, tmp_path, name)
    assert rc == 0, "%s script is not valid bash: %s" % (name, err)
    assert "%s" not in s.replace("printf '%s'", ""), "an unformatted placeholder reached the script"


def test_a_shared_fragment_is_refused(capsys):
    """THE OUTAGE THIS PREVENTS. A Caddy fragment can declare several site names. Removing one
    that also carries cybergod.ai would take cybergod.ai down, and you would find out from a
    customer rather than from the plan."""
    d = {"FRAGMENTS": "misc.caddy|jev.best cybergod.ai\npolara.caddy|klimaanlage-preise.de",
         "MATCHES": "jev.best|misc.caddy\nklimaanlage-preise.de|polara.caddy",
         "CONTAINERS": "polara-web|p|Up 3d|", "UPSTREAMS": ""}
    frags, _ = D.show_plan(["jev.best", "klimaanlage-preise.de"], d)
    assert frags is None, "a fragment that also serves an unlisted domain must be REFUSED"
    out = capsys.readouterr().out
    assert "cybergod.ai" in out and "REFUSING" in out, "the refusal must NAME the collateral"


def test_a_clean_split_proceeds_and_never_targets_a_survivor(capsys):
    d = {"FRAGMENTS": "polara.caddy|klimaanlage-preise.de www.klimaanlage-preise.de\n"
                      "jev.caddy|jev.best www.jev.best\ncybergod.caddy|cybergod.ai",
         "MATCHES": "jev.best|jev.caddy\nwww.jev.best|jev.caddy\n"
                    "klimaanlage-preise.de|polara.caddy\nwww.klimaanlage-preise.de|polara.caddy",
         "CONTAINERS": "polara-web|p|Up 3d|\ncolt-web|c|Up 2h|\njhw-web|j|Up 5d|", "UPSTREAMS": ""}
    frags, guess = D.show_plan(["jev.best", "www.jev.best", "klimaanlage-preise.de",
                                "www.klimaanlage-preise.de"], d)
    assert frags == ["jev.caddy", "polara.caddy"]
    assert "cybergod.caddy" not in frags
    for keep in ("colt-web", "jhw-web"):
        assert keep not in (guess or []), "%s must never be proposed for stopping" % keep


def test_nothing_is_proposed_when_nothing_matches(capsys):
    """Finding no match must be reported, not silently treated as 'nothing to do and success'.
    That distinction is the same one logship got wrong: 'I cannot see my subject' and 'there is
    nothing to do' produce the same output unless you make them different."""
    d = {"FRAGMENTS": "cybergod.caddy|cybergod.ai", "MATCHES": "", "CONTAINERS": "", "UPSTREAMS": ""}
    frags, _ = D.show_plan(["jev.best"], d)
    assert frags is None
    assert "none of the target sites" in capsys.readouterr().out


def test_the_restart_policy_is_disabled_before_the_container_is_stopped():
    """A stopped container whose policy is `always` is decommissioned until the next reboot, and
    a reboot is exactly when nobody is watching. This droplet reboots itself for kernel patches."""
    s = D.apply_script(["x.caddy"], ["polara-web"], "t")
    assert s.index("--restart=no") < s.index("docker stop"), \
        "set restart=no FIRST or the container comes back on the next kernel reboot"


def test_the_decommission_deletes_no_data():
    """Volumes, images and databases are kept. `--undo` only means something if the data survives,
    and an irreversible action taken to save a few euros is a bad trade."""
    s = D.apply_script(["x.caddy"], ["polara-web"], "t")
    for verb in ("docker rm ", "volume rm", "docker rmi", "rm -rf"):
        assert verb not in s, "decommission must never %s" % verb.strip()
    assert "mv " in s, "fragments must be MOVED to the archive, not deleted"


def test_it_backs_up_before_it_changes_anything():
    s = D.apply_script(["x.caddy"], ["polara-web"], "t")
    assert s.index("tar czf") < s.index("mv "), "back up BEFORE moving fragments"
    assert s.index("Caddyfile.before") < s.index("assemble --apply"), \
        "the live Caddyfile must be copied before the config is reassembled"


def test_the_config_is_applied_only_through_the_guard():
    """NEVER a hand-edit of the shared Caddyfile. `agent.py assemble --apply` validates in the
    proxy's own image AND environment, refuses a config with no site blocks, checks the bind mount
    is fresh, and only then reloads. Each of those exists because of a real incident."""
    s = D.apply_script(["x.caddy"], ["polara-web"], "t")
    assert "agent.py assemble --apply" in s
    for forbidden in ("sed -i", "caddy reload", "> /opt/videodead/Caddyfile"):
        assert forbidden not in s, "the shared Caddyfile must not be touched directly (%s)" % forbidden


def test_the_survivors_are_verified_and_the_list_is_not_empty():
    """A decommission that reports success while having broken cybergod.ai is worse than one that
    fails. The check has to be able to fail, so the list has to be non-empty."""
    assert D.SURVIVORS, "an empty survivor list makes verify() a check that cannot fail"
    assert any("cybergod.ai" in s for s in D.SURVIVORS)
    assert any("jobhuntwow" in s for s in D.SURVIVORS), \
        "jobhuntwow shares this proxy and was one of the sites lost on 2026-08-07"


def test_the_default_targets_include_the_www_variants():
    """Omitting `www.` is how you leave half a site served and trip the collateral check on the
    next run for a domain you thought you had already removed."""
    for base in ("jev.best", "klimaanlage-preise.de"):
        assert base in D.DEFAULT_SITES and "www." + base in D.DEFAULT_SITES


def test_dry_run_is_the_default(tmp_path):
    """--apply is opt-in. A destructive tool whose default is destructive gets run by accident."""
    src = open(os.path.join(ROOT, "decommission.py"), encoding="utf-8").read()
    assert 'add_argument("--apply", action="store_true"' in src
    assert "if not a.apply:\n        return 0" in src, \
        "the plan must return BEFORE anything is applied unless --apply was passed"
