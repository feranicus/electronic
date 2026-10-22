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


@pytest.mark.parametrize("name", ["plan", "apply", "edit", "diff", "undo"])
def test_every_generated_script_is_valid_bash(name, tmp_path):
    """A remote script is assembled by %-formatting, and a stray placeholder or a mangled
    parameter expansion is invisible until it runs on the droplet. This repository has already
    shipped one `printf '%%s'` bug and one `%]` format error that masked a real traceback."""
    s = {"plan": lambda: D.plan_script(D.expand_sites(["jev"])),
         "apply": lambda: D.apply_script(["a.caddy"], ["polara-web"], "20260901-120000"),
         "edit": lambda: D.apply_script([], ["jev-web"], "20260901-120000",
                                        {"_base.caddy": "godeyes.ai {\n  respond 200\n}\n"}),
         "diff": lambda: D.diff_script("last"),
         "undo": lambda: D.undo_script("20260901-120000")}[name]()
    rc, err = _bash_ok(s, tmp_path, name)
    assert rc == 0, "%s script is not valid bash: %s" % (name, err)
    assert "%s" not in s.replace("printf '%s'", ""), "an unformatted placeholder reached the script"


def _b64(text):
    import base64
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


JEV_BLOCK = ("jev.best, www.jev.best {\n"
             "  handle /api/* {\n"
             "    reverse_proxy jev-api:8080\n"
             "  }\n"
             "  reverse_proxy jev-web:3000\n"
             "}\n")
BASE_FRAG = ("# shared base\n"
             "godeyes.ai {\n"
             "  reverse_proxy godeyes-web:8000\n"
             "}\n" + JEV_BLOCK +
             "s4biz.io {\n"
             "  reverse_proxy s4biz-web:8000\n"
             "}\n")


def test_a_shared_fragment_is_NOT_deleted_whole(capsys):
    """THE OUTAGE THIS PREVENTS. A Caddy fragment can declare several site names, and deleting the
    file takes all of them down.

    THE ORIGINAL DOCTRINE, KEPT BECAUSE IT IS STILL HALF RIGHT (class 17): this used to REFUSE
    outright, and refusing beat proceeding. But on this droplet most vhosts share `_base.caddy`,
    so "retire jev.best" could only ever answer no, and the honest conclusion was that the
    operation was unsupported rather than unsafe. The rule now is narrower and still never deletes
    a byte of somebody else's routing: the file is EDITED, the original is archived, the other
    domains must still appear in the kept text."""
    d = {"FRAGMENTS": "_base.caddy|godeyes.ai jev.best www.jev.best s4biz.io",
         "MATCHES": "jev.best|_base.caddy\nwww.jev.best|_base.caddy",
         "FRAGTEXT": "_base.caddy|" + _b64(BASE_FRAG),
         "CONTAINERS": "jev-web|i|Up 3d|\ncolt-web|c|Up 2h|", "UPSTREAMS": ""}
    plan, guess = D.show_plan(["jev.best", "www.jev.best"], d)
    assert plan is not None, "a shared fragment must now be editable, not a dead end"
    whole, extract = plan
    assert whole == [], "the shared file must never be removed outright"
    kept, removed, extra = extract["_base.caddy"]
    assert "jev.best" not in kept and "jev-web" not in kept, "the target block is still served"
    for survivor in ("godeyes.ai", "s4biz.io", "godeyes-web", "s4biz-web"):
        assert survivor in kept, "%s was lost from the fragment" % survivor
    assert "jev.best" in removed and sorted(extra) == ["godeyes.ai", "s4biz.io"]
    out = capsys.readouterr().out
    assert "WILL EDIT FRAGMENTS" in out, "the plan must say the file is edited, not removed"


def test_a_header_mixing_a_target_with_a_survivor_is_still_refused(capsys):
    """One header, two meanings. `jev.best, godeyes.ai { ... }` cannot be removed for one name and
    kept for the other without rewriting routing nobody asked us to touch."""
    mixed = "jev.best, godeyes.ai {\n  reverse_proxy shared:8000\n}\n"
    d = {"FRAGMENTS": "_base.caddy|jev.best godeyes.ai",
         "MATCHES": "jev.best|_base.caddy",
         "FRAGTEXT": "_base.caddy|" + _b64(mixed),
         "CONTAINERS": "", "UPSTREAMS": ""}
    plan, _ = D.show_plan(["jev.best"], d)
    assert plan is None, "a mixed header must be refused, not silently rewritten"
    out = capsys.readouterr().out
    assert "REFUSING" in out and "godeyes.ai" in out, "the refusal must NAME the collateral"


def test_an_unreadable_fragment_is_refused_rather_than_guessed(capsys):
    """Class 1: a check that cannot see its subject must not answer. No FRAGTEXT means we cannot
    compute the edit, and 'I could not read it' is not 'there was nothing to remove'."""
    d = {"FRAGMENTS": "_base.caddy|jev.best godeyes.ai", "MATCHES": "jev.best|_base.caddy",
         "CONTAINERS": "", "UPSTREAMS": ""}
    plan, _ = D.show_plan(["jev.best"], d)
    assert plan is None
    assert "could not read" in capsys.readouterr().out


def test_a_dedicated_fragment_is_removed_whole_and_never_targets_a_survivor(capsys):
    d = {"FRAGMENTS": "polara.caddy|klimaanlage-preise.de www.klimaanlage-preise.de\n"
                      "jev.caddy|jev.best www.jev.best\ncybergod.caddy|cybergod.ai",
         "MATCHES": "jev.best|jev.caddy\nwww.jev.best|jev.caddy\n"
                    "klimaanlage-preise.de|polara.caddy\nwww.klimaanlage-preise.de|polara.caddy",
         "FRAGTEXT": "jev.caddy|" + _b64(JEV_BLOCK),
         "CONTAINERS": "polara-web|p|Up 3d|\ncolt-web|c|Up 2h|\njhw-web|j|Up 5d|", "UPSTREAMS": ""}
    plan, guess = D.show_plan(["jev.best", "www.jev.best", "klimaanlage-preise.de",
                               "www.klimaanlage-preise.de"], d)
    whole, extract = plan
    assert whole == ["jev.caddy", "polara.caddy"] and not extract
    assert "cybergod.caddy" not in whole
    for keep in ("colt-web", "jhw-web"):
        assert keep not in (guess or []), "%s must never be proposed for stopping" % keep


def test_the_containers_to_stop_are_read_from_the_routing_not_the_name(capsys):
    """The old rule was `any(k in name for k in ("polara","klima","jev"))`: three hardcoded homes
    that would stop a container called `jev-archive` and miss one whose name says nothing about
    its domain. The config already names the upstream serving the block being removed."""
    d = {"FRAGMENTS": "_base.caddy|godeyes.ai jev.best www.jev.best s4biz.io",
         "MATCHES": "jev.best|_base.caddy",
         "FRAGTEXT": "_base.caddy|" + _b64(BASE_FRAG),
         "CONTAINERS": "jev-web|i|Up 3d|\njev-api|i|Up 3d|\njev-archive|i|Up 1d|\n"
                       "godeyes-web|g|Up 9d|", "UPSTREAMS": ""}
    _, guess = D.show_plan(["jev.best", "www.jev.best"], d)
    assert sorted(guess) == ["jev-api", "jev-web"], guess
    assert "jev-archive" not in guess, "a name-substring match would have stopped an unrelated box"
    assert "godeyes-web" not in guess, "the upstream of a KEPT block must never be stopped"


def test_nothing_is_proposed_when_nothing_matches(capsys):
    """Finding no match must be reported, not silently treated as 'nothing to do and success'.
    That distinction is the same one logship got wrong: 'I cannot see my subject' and 'there is
    nothing to do' produce the same output unless you make them different."""
    d = {"FRAGMENTS": "cybergod.caddy|cybergod.ai", "MATCHES": "", "CONTAINERS": "", "UPSTREAMS": ""}
    plan, _ = D.show_plan(["jev.best"], d)
    assert plan is None
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


def test_a_refusable_edit_runs_before_any_fragment_is_moved():
    """Each edit proves its payload by checksum and can REFUSE; `set -e` then stops the script.
    With the moves ahead of them, a refused edit would leave another project's fragment already
    archived and the config un-reassembled - a half-state for a change that decided not to happen.
    This matters the moment one run retires two sites by different paths."""
    s = D.apply_script(["polara__klima.caddy"], [], "t", {"_base.caddy": "godeyes.ai {\n}\n"})
    assert s.index("REFUSING to install") < s.index('mv "/opt/caddyguard/blocks/$f"'), \
        "a fragment is moved before the edit that might refuse"
    assert s.index("#### EDIT_FRAGMENTS") < s.index("#### MOVE_FRAGMENTS")


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


def test_naming_a_site_always_takes_its_www_partner_with_it():
    """Omitting `www.` is how you leave half a site served and trip the collateral check on the
    next run for a domain you thought you had already removed.

    THE DOCTRINE THAT CHANGED (class 17). This used to be asserted of `DEFAULT_SITES`, a module
    constant that `--sites` defaulted to — so the pairing was guaranteed only for the three
    domains someone had typed there, and `--apply` with no arguments retired all of them. The
    pairing is the property worth keeping; the default target was the hazard. expand_sites()
    enforces the pairing on whatever the operator actually names."""
    assert D.expand_sites(["jev.best"]) == ["jev.best", "www.jev.best"]
    assert sorted(D.expand_sites(["www.jev.best"])) == ["jev.best", "www.jev.best"]
    klima = D.expand_sites(["klima"])
    for base in ("klimaanlage-preise.de", "klimaanlage-montieren.de"):
        assert base in klima and "www." + base in klima
    assert D.expand_sites([""]) == [], "an empty argument must not expand into a target"


def test_there_is_no_default_target():
    """A destructive tool must not have a destructive default in EITHER half. Dry-run-by-default
    covered the action; nothing covered the target, and the target list shipped with a live
    project in it."""
    src = open(os.path.join(ROOT, "decommission.py"), encoding="utf-8").read()
    assert 'ap.add_argument("--sites", default=""' in src, (
        "--sites has a default again; `decommission.py --apply` would then retire whatever that "
        "default names")
    assert not hasattr(D, "DEFAULT_SITES"), "the implicit target list is back"


def test_the_edit_archives_the_original_before_it_writes():
    """`--undo` restores whatever is in the archive, so the ORIGINAL has to be what lands there.
    Archiving after the write would store the edited file and make undo a no-op."""
    s = D.apply_script([], ["jev-web"], "t", {"_base.caddy": "godeyes.ai {\n}\n"})
    assert s.index('cp -a "/opt/caddyguard/blocks/_base.caddy"') < s.index('mv "$DEST/_base.caddy.new"')
    assert s.index("tar czf") < s.index('cp -a "/opt/caddyguard/blocks/_base.caddy"')
    assert s.index('mv "$DEST/_base.caddy.new"') < s.index("assemble --apply"), \
        "the reduced fragment must be in place before the config is reassembled"


def test_the_write_proves_it_installed_what_was_computed():
    """NON-EMPTY IS NOT CORRECT (class 17 - the doctrine this test used to encode was too weak).

    The original gate was `[ -s "$DEST/<n>.new" ]`: refuse if the decoded file is empty. On
    2026-10-22 a 94-line `_base.caddy` reached the droplet as ONE line, which is non-empty, so
    that gate passed it and the assemble served it. godeyes.ai - a vhost declared as `{$DOMAIN} {`
    in that same file - went dark.

    Every local reproduction of the split, the base64 round trip and the remote write produced the
    correct result, so the cause is somewhere this code cannot see. A checksum does not care: it
    is exact, it is compared BEFORE anything is archived or moved, and a mismatch prints expected
    against actual, which is the diagnosis the next occurrence will need."""
    import hashlib
    body = "godeyes.ai {\n}\n"
    s = D.apply_script([], [], "t", {"_base.caddy": body})
    assert hashlib.sha256(body.encode()).hexdigest() in s, "no checksum is sent"
    assert "sha256sum" in s and "-ne 2" in s, "the line count is not verified"
    assert s.index("REFUSING to install") < s.index('cp -a "/opt/caddyguard/blocks/_base.caddy"'), \
        "the proof must come before anything is archived or moved"
    assert "UNCHANGED" in s, "the refusal must say the live config was not touched"


def test_a_corrupted_payload_is_refused_and_leaves_the_original_in_place(tmp_path, monkeypatch):
    """PROVE THE GATE BY BREAKING THE THING IT GUARDS (class 3). Hand the remote script a payload
    that does not match its own checksum - which is what 2026-10-22 looked like from the droplet's
    side - and the fragment on disk must be untouched."""
    ok, why = _posix_ok()
    if not ok:
        pytest.skip(why)
    guard = tmp_path / "caddyguard"
    (guard / "blocks").mkdir(parents=True)
    dest = guard / "decommissioned" / "t"
    dest.mkdir(parents=True)
    frag = guard / "blocks" / "_base.caddy"
    frag.write_bytes(BASE_FRAG.encode("utf-8"))

    monkeypatch.setattr(D, "GUARD", str(guard).replace("\\", "/"))
    kept, _, _ = D.split_fragment(BASE_FRAG, ["jev.best", "www.jev.best"])
    script = D.apply_script([], [], "t", {"_base.caddy": kept})
    seg = script.split('echo "#### EDIT_FRAGMENTS"\n')[1].split('echo "#### REASSEMBLE"')[0]

    # CORRUPT THE PAYLOAD, exactly as whatever happened on the droplet did: the base64 now carries
    # a single newline instead of the computed fragment.
    import base64 as b64
    good = b64.b64encode(kept.encode("utf-8")).decode("ascii")
    seg = seg.replace(good, b64.b64encode(b"\n").decode("ascii"))

    r = subprocess.run(["bash", "-c", 'DEST="%s"\n%s' % (str(dest).replace("\\", "/"), seg)],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out = r.stdout.decode("utf-8", "replace")
    assert r.returncode != 0, "a corrupted payload was accepted:\n%s" % out
    assert "REFUSING to install" in out and "got      sha256" in out, out
    assert frag.read_text(encoding="utf-8") == BASE_FRAG, "the original fragment was modified"
    assert not (dest / "_base.caddy").exists(), "it archived before it had proved anything"


def test_the_edit_never_touches_the_live_caddyfile():
    s = D.apply_script([], [], "t", {"_base.caddy": "godeyes.ai {\n}\n"})
    for forbidden in ("sed -i", "> /opt/videodead/Caddyfile", "caddy reload"):
        assert forbidden not in s, forbidden


@pytest.mark.parametrize("text,sites,why", [
    ("jev.best {\n  handle {\n    respond 200\n  }\n}\n", ["jev.best"], None),
    ("jev.best {\n  handle {\n    respond 200\n", ["jev.best"], "never closes"),
    ("godeyes.ai {\n  respond 200\n}\n", ["jev.best"], "no site block"),
])
def test_split_fragment_counts_braces_and_refuses_rather_than_guessing(text, sites, why):
    """A nested `handle { }` is ordinary Caddy, so a line-based rule cuts the file in half. And an
    unbalanced block means our counting disagrees with Caddy's parser, which is the one situation
    where changing nothing is the only safe answer."""
    kept, removed, refusal = D.split_fragment(text, sites)
    if why is None:
        assert refusal is None and removed.count("{") == removed.count("}")
        assert kept.strip() == "", kept
    else:
        assert refusal and why in refusal


def test_the_edit_segment_really_produces_the_reduced_fragment(tmp_path, monkeypatch):
    """PARSE IS NOT RUN (class 48). The write is base64 inside a shell string inside a Python
    %-format: it can be valid bash, pass every source assertion above, and still land the wrong
    bytes. Run it against a real file and compare.

    The fixture is proved first: the original must contain the block we expect to lose, or this
    would pass by removing nothing."""
    ok, why = _posix_ok()
    if not ok:
        pytest.skip(why)
    guard = tmp_path / "caddyguard"
    (guard / "blocks").mkdir(parents=True)
    (guard / "decommissioned" / "t").mkdir(parents=True)
    frag = guard / "blocks" / "_base.caddy"
    frag.write_bytes(BASE_FRAG.encode("utf-8"))          # BINARY: class 21
    assert "jev-web" in frag.read_text(encoding="utf-8"), "fixture does not hold the target block"

    kept, removed, why2 = D.split_fragment(BASE_FRAG, ["jev.best", "www.jev.best"])
    assert why2 is None and "jev-web" in removed

    monkeypatch.setattr(D, "GUARD", str(guard).replace("\\", "/"))
    script = D.apply_script([], [], "t", {"_base.caddy": kept})
    # Cut on the WHOLE echo lines. Splitting on the bare marker leaves the opening quote of the
    # next `echo "` behind and bash dies on a syntax error that says nothing about the write.
    seg = script.split('echo "#### EDIT_FRAGMENTS"\n')[1].split('echo "#### REASSEMBLE"')[0]
    r = subprocess.run(["bash", "-e", "-c", 'DEST="%s"\n%s' % (
        str(guard / "decommissioned" / "t").replace("\\", "/"), seg)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")

    now = frag.read_text(encoding="utf-8")
    assert now == kept, "the fragment on disk is not what the plan computed"
    assert "jev.best" not in now and "jev-web" not in now
    for survivor in ("godeyes.ai", "s4biz.io"):
        assert survivor in now
    archived = (guard / "decommissioned" / "t" / "_base.caddy").read_text(encoding="utf-8")
    assert archived == BASE_FRAG, "undo would restore the wrong bytes"


def _posix_ok():
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    from test_teamwork import shell_harness_allowed
    return shell_harness_allowed()


COMMENT_BRACE = ("godeyes.ai {\n  respond 200\n}\n"
                 "jev.best {\n  # handle { later\n  reverse_proxy jev-web:3000\n}\n"
                 "s4biz.io {\n  respond 200\n}\n}\n")


def test_a_stray_brace_in_a_comment_cannot_swallow_the_next_vhost():
    """THE POST-CONDITION, and why 'nothing vanished' was not enough.

    Caddy's parser ignores a `{` inside a comment or a quoted string; this splitter counts raw
    braces, so one stray brace makes the counter run past the closing brace and take the following
    vhost with it. The first version of the check asserted only that every header in the original
    turned up in kept-or-removed - and a swallowed block IS in removed, so it passed.

    The invariant that catches it: the removed side may contain NOTHING but target headers."""
    kept, removed, why = D.split_fragment(COMMENT_BRACE, ["jev.best"])
    assert kept is None and removed is None, "s4biz.io was removed along with jev.best"
    assert "s4biz.io" in why, "the refusal must NAME what it would have taken: %s" % why
    assert "Nothing is changed" in why


def test_the_split_accounts_for_every_line_of_the_input():
    """Arithmetic over the input and the output, so it holds whatever the mechanism was. On
    2026-10-22 a 94-line fragment reached the droplet as one line and nothing noticed."""
    kept, removed, why = D.split_fragment(BASE_FRAG, ["jev.best", "www.jev.best"])
    assert why is None
    assert len(kept.splitlines()) + len(removed.splitlines()) == len(BASE_FRAG.splitlines())


def test_every_post_condition_clause_can_actually_fail():
    """A CHECK THAT CANNOT FAIL IS NOT A CHECK (class 3), and two of these could not.

    Inside the loop, 'every line is accounted for' and 'no header vanished' are unreachable by any
    input: the loop puts each line on one side or the other by construction. Mutating them away
    changed nothing and the suite stayed green. They exist to guard FUTURE edits to that loop, so
    the test has to break the loop's OUTPUT on purpose - which is what 'prove a gate by breaking
    the thing it guards' means."""
    text = BASE_FRAG
    kept, removed, why = D.split_fragment(text, ["jev.best", "www.jev.best"])
    assert why is None and D.check_split(text, kept, removed, ["jev.best", "www.jev.best"]) is None

    dropped = "\n".join(kept.splitlines()[:-1]) + "\n"          # the loop loses a line
    assert "does not account for every line" in \
        D.check_split(text, dropped, removed, ["jev.best", "www.jev.best"])

    no_hdr = kept.replace("godeyes.ai {", "# godeyes.ai {")     # the loop loses a header
    assert "vanished" in D.check_split(text, no_hdr, removed, ["jev.best", "www.jev.best"])

    assert "still declared" in D.check_split(text, text, "", ["jev.best", "www.jev.best"])


def test_the_header_detector_sees_an_environment_placeholder_vhost():
    """`{$DOMAIN} {` is a real site header on this proxy - godeyes.ai is served by it, so that
    hostname appears NOWHERE in the file. The plan's name grep (`^[a-z0-9.*-]+...`) cannot match
    it, which is why a fragment holding two vhosts was recorded as holding one."""
    assert D._headers("{$DOMAIN} {\n  respond 200\n}\n") == {"{$DOMAIN} {"}
    assert D._headers("# a comment {\n(snippet) {\n\thandle {\n}\n") == set()


def test_the_survivors_are_derived_from_what_is_actually_served():
    """A hardcoded survivor list measures the day it was written. Editing the shared base can
    break any vhost in it, so every name the proxy serves that we are not removing is checked."""
    frag_names = {"_base.caddy": ["godeyes.ai", "jev.best", "s4biz.io"],
                  "colt.caddy": ["cybergod.ai"]}
    urls = D._survivor_urls(frag_names, ["jev.best", "www.jev.best"])
    hosts = [u.split("/")[2] for u in urls]
    assert "godeyes.ai" in hosts and "s4biz.io" in hosts
    assert "jev.best" not in hosts, "a site being removed must not be probed as a survivor"
    for floor in ("cybergod.ai", "www.jobhuntwow.com"):
        assert floor in hosts, "the pinned floor must survive derivation"


PLAN_OUT = ("#### FRAGMENTS\n"
            "_base.caddy|godeyes.ai jev.best www.jev.best s4biz.io\n"
            "#### CONTAINERS\njev-web|i|Up 3d|\n"
            "#### UPSTREAMS\nreverse_proxy jev-web:3000\n"
            "#### MATCHES\njev.best|_base.caddy\nwww.jev.best|_base.caddy\n"
            "#### FRAGTEXT\n_base.caddy|" + _b64(BASE_FRAG) + "\n"
            "#### DISK\n/dev/vda1  77G  19% /\n#### BACKUPS\n")


def _run_main(monkeypatch, capsys, argv, ssh_result):
    """main() end to end with the ONE boundary stubbed: what ssh actually returns.

    `ssh_result` is one (stdout, stderr, rc) tuple, or a list of them answered in order, so the
    apply path can be given a healthy plan followed by a failing change."""
    calls = []
    queue = list(ssh_result) if isinstance(ssh_result, list) else None

    def fake(script, timeout=240):
        calls.append(script)
        if queue is None:
            return ssh_result
        return queue.pop(0) if len(queue) > 1 else queue[0]

    monkeypatch.setattr(D, "ssh_script", fake)
    monkeypatch.setattr(D, "probe", lambda url, **kw: (200, "ok"))
    monkeypatch.setattr(sys, "argv", ["decommission.py"] + argv)
    rc = D.main()
    return rc, capsys.readouterr().out, calls


def test_the_dry_run_actually_runs(monkeypatch, capsys):
    """THE CRASH THIS PINS, 2026-10-22, the first end-to-end run of this script:

        d = sections(ssh_script(plan_script(sites), timeout=240))
        AttributeError: 'tuple' object has no attribute 'splitlines'

    `ssh_script()` returns `(stdout, stderr, rc)` and all three call sites passed the tuple
    straight into `sections()`. Every test above covered a PIECE - the generated scripts, the
    plan arithmetic, the splitter - and not one of them executed main(), so a script that could
    never run at all had a green suite (classes 2 and 9). The fix is this test, not the one-line
    unpack: stub the boundary, run the whole path."""
    rc, out, calls = _run_main(monkeypatch, capsys, ["--sites", "jev"], (PLAN_OUT, "", 0))
    assert rc == 0, out
    assert "DECOMMISSION PLAN" in out and "WILL EDIT FRAGMENTS" in out
    assert "jev-web" in out, "the plan never reached the container discovery"
    assert len(calls) == 1, "a dry run must open exactly one ssh session and change nothing"


def test_a_failed_ssh_is_never_rendered_as_a_finding_about_the_proxy(monkeypatch, capsys):
    """Class 1, and the same shape as `sshout()` on 2026-10-14. The return code was not read, so
    a dead connection produced empty output, `sections()` produced {}, and the plan would have
    announced 'none of the target sites is served by a caddyguard fragment' - a statement about
    the proxy, derived from never having reached it."""
    rc, out, _ = _run_main(monkeypatch, capsys, ["--sites", "jev"],
                           ("", "ssh: connect to host port 22: Connection refused", 255))
    assert rc == 1
    assert "255" in out and "NOTHING is concluded" in out
    assert "none of the target sites" not in out, \
        "an unreachable droplet was reported as a fact about what the proxy serves"


def test_an_empty_read_is_refused_rather_than_called_an_empty_proxy(monkeypatch, capsys):
    """rc 0 with no fragments at all is a probe that cannot see its subject, not a proxy with
    nothing on it. This droplet serves fifteen hostnames."""
    rc, out, _ = _run_main(monkeypatch, capsys, ["--sites", "jev"], ("#### DISK\nx\n", "", 0))
    assert rc == 1 and "not about the proxy" in out


def test_a_change_that_stopped_part_way_says_so_and_names_the_way_back(monkeypatch, capsys):
    """`set -e` stops the remote script at the FIRST failure, so a non-zero apply is a partial
    state, not a no-op. Reporting it as a clean run - or letting verify() alone decide, which
    passes whenever the survivors happen to be up - would leave a half-moved fragment with nobody
    told which stamp holds the original."""
    rc, out, calls = _run_main(
        monkeypatch, capsys, ["--sites", "jev", "--apply"],
        [(PLAN_OUT, "", 0),
         ("#### BACKUP\nsaved before.tgz\n", "assemble: refusing, 0 site blocks", 1)])
    assert rc == 1, out
    assert "stopped part-way" in out and "--undo" in out
    assert len(calls) == 2, "expected one plan session and one apply session"


def test_a_clean_apply_reports_success(monkeypatch, capsys):
    """The failure test above must not pass merely because this path always fails."""
    rc, out, _ = _run_main(
        monkeypatch, capsys, ["--sites", "jev", "--apply"],
        [(PLAN_OUT, "", 0), ("#### REMAINING\ncolt-web|Up\n#### NOTE\nkept\n", "", 0)])
    assert rc == 0, out
    assert "stopped part-way" not in out
    assert "all survivors answering" in out


def test_the_forensic_verb_cannot_change_anything():
    """`--diff` is reached for while reading an outage, which is the worst moment to run a script
    that writes. It reads the archive the undo left behind and the live config, and nothing else."""
    s = D.diff_script("last")
    for verb in ("mv ", "rm ", "cp -a", "assemble --apply", "docker stop", "docker update",
                 "base64 -d >", "sed -i"):
        assert verb not in s, "the read-only forensic contains %r" % verb
    assert "diff -u" in s and "#### CENSUS" in s


def test_the_header_census_is_wider_than_the_one_that_measured_its_own_pattern():
    """THE FIRST READING OF THIS INCIDENT WAS A GUESS, and the reason was this pattern.

    The undo's grep was `^[A-Za-z0-9*][^{]*\\{[[:space:]]*$`. Against the real `_base.caddy` it
    reported exactly ONE site header in a 95-line file that caddyguard counts as 13 brace pairs,
    so the restore output could not distinguish 'the edit removed only jev' from 'the edit removed
    jev and everything after it'. A census that finds one block in a file holding several is
    measuring its own pattern (class 1).

    The census must see a plain header, a multi-name header and a scheme-prefixed one, and must
    skip comments, snippet definitions and indented directives."""
    import re
    m = re.search(r"grep -nE '([^']+)' \"\$v\"", D.diff_script("last"))
    assert m, "the census grep moved; this guard is reading the wrong thing"
    # POSIX classes -> Python. `[[:space:]]` is a class of its own; `[:space:]` also appears
    # INSIDE a negated set (`[^[:space:]#(]`), where the outer brackets are the set's.
    ere = m.group(1).replace("[[:space:]]", r"\s").replace("[:space:]", r"\s")
    pat = re.compile(ere)
    for line in ("godeyes.ai {", "jev.best, www.jev.best {", "https://s4biz.io {",
                 "klimaanlage-preise.de, www.klimaanlage-preise.de {"):
        assert pat.match(line), "the census would miss the header %r" % line
    for line in ("# handle { later", "(common) {", "\thandle @spa {", "  reverse_proxy x:1 {"):
        assert not pat.match(line), "the census counts %r as a site header" % line


def test_a_site_that_goes_dark_is_restored_automatically(monkeypatch, capsys):
    """godeyes.ai was down for twenty minutes because the only signal was one line in the middle
    of a deploy that otherwise ended with DONE. The archive is byte-exact, so leaving somebody
    else's domain dark while a human reads a log is a choice, not a constraint.

    BOTH TERMS OVER THE SAME PERIOD: a site that was already down before the change must not be
    blamed on it, which is what the baseline probe is for."""
    seen = {"n": 0}

    def flaky(url, **kw):
        seen["n"] += 1
        # healthy for the baseline sweep, dark for the after sweep, healthy once restored
        if "godeyes" in url and 5 <= seen["n"] <= 8:
            return None, "URLError"
        return 200, "ok"

    calls = []

    def fake(script, timeout=240):
        calls.append(script)
        return [(PLAN_OUT, "", 0), ("#### NOTE\nok\n", "", 0),
                ("#### RESTORE_FRAGMENTS\nrestored _base.caddy\n", "", 0)][min(len(calls) - 1, 2)]

    monkeypatch.setattr(D, "ssh_script", fake)
    monkeypatch.setattr(D, "probe", flaky)
    monkeypatch.setattr(sys, "argv", ["decommission.py", "--sites", "jev", "--apply"])
    rc = D.main()
    out = capsys.readouterr().out
    assert rc == 1, out
    assert "THIS CHANGE TOOK A SITE DOWN" in out and "godeyes.ai" in out
    assert "restoring" in out and "was REVERSED" in out
    assert len(calls) == 3, "expected plan, apply, and an automatic undo - got %d" % len(calls)


def test_a_site_already_down_is_not_blamed_on_the_change(monkeypatch, capsys):
    """The baseline is what makes the check above able to be WRONG in the useful direction."""
    def dark_throughout(url, **kw):
        return (None, "URLError") if "godeyes" in url else (200, "ok")

    calls = []

    def fake(script, timeout=240):
        calls.append(script)
        return (PLAN_OUT, "", 0) if len(calls) == 1 else ("#### NOTE\nok\n", "", 0)

    monkeypatch.setattr(D, "ssh_script", fake)
    monkeypatch.setattr(D, "probe", dark_throughout)
    monkeypatch.setattr(sys, "argv", ["decommission.py", "--sites", "jev", "--apply"])
    D.main()
    out = capsys.readouterr().out
    assert "THIS CHANGE TOOK A SITE DOWN" not in out, \
        "a site that was already dark was attributed to this change"
    assert len(calls) == 2, "it ran an undo for damage it did not do"


def test_a_failed_undo_does_not_report_a_restore_that_did_not_happen(monkeypatch, capsys):
    """`--undo` is the thing you reach for when a decommission went wrong, so it is the last
    place that may report success it did not achieve."""
    rc, out, _ = _run_main(monkeypatch, capsys, ["--undo", "20260901-120000"],
                           ("#### RESTORE_FRAGMENTS\n", "no such decommission", 1))
    assert rc == 1
    assert "did not complete" in out and "20260901-120000" in out
    assert "all survivors answering" not in out, \
        "a failed restore ran the survivor probe and reported it as the outcome"


def test_no_call_site_hands_ssh_output_straight_to_the_parser():
    """ANCHOR ON THE CALL SITE (class 4). The repair is worthless if the next edit re-inlines it.
    ssh_script is reached through run_remote(), which unpacks the tuple AND checks the rc."""
    import ast
    src = open(os.path.join(ROOT, "decommission.py"), encoding="utf-8").read()
    bad = []
    for node in ast.walk(ast.parse(src)):
        if not isinstance(node, ast.Call):
            continue
        fn = getattr(node.func, "id", None)
        if fn == "sections" and node.args:
            inner = getattr(getattr(node.args[0], "func", None), "id", None)
            if inner == "ssh_script":
                bad.append(node.lineno)
        if fn == "ssh_script":
            bad.append(node.lineno) if not _inside_run_remote(src, node.lineno) else None
    assert not bad, "ssh_script's 3-tuple is being used raw at line(s) %s" % bad


def _inside_run_remote(src, lineno):
    import ast
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.FunctionDef) and node.name == "run_remote":
            return node.lineno <= lineno <= (node.end_lineno or node.lineno)
    return False


def _ship_src():
    """ship.py with comments and docstrings stripped. A guard has matched its own explanatory
    comment five separate times in this repository (class 4)."""
    import ast
    src = open(os.path.join(ROOT, "ship.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    drop = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str):
            drop.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))
    return "\n".join(ln for i, ln in enumerate(src.splitlines(), 1)
                     if i not in drop and not ln.strip().startswith("#"))


def test_ship_py_owns_the_decommission_so_the_operator_runs_ONE_command():
    """Operating principle 7. Retiring a vhost used to mean a second `python ...` line, which is
    the rule this repository keeps writing down and then breaking."""
    s = _ship_src()
    assert '"--decommission"' in s, "ship.py does not expose the verb"
    assert '"decommission.py"' in s and '"--apply"' in s, \
        "the flag exists but nothing invokes the script - a control that is unreachable is not a " \
        "control (class 9)"


def test_the_decommission_runs_after_the_ship_verified_and_never_on_a_failed_one():
    """Two properties in source ORDER, because both are about when it runs:

    * it comes after the safe-point tag, so the code performing the retirement is code that has
      been committed and pushed (principle 2, GitHub is the source of truth);
    * it is skipped when the ship did not verify. decommission.py ends by probing every surviving
      vhost, so running it on top of a broken deploy would blame the retirement for damage the
      deploy had already done."""
    s = _ship_src()
    i_tag = s.index("tag_known_good()")
    i_dec = s.index('"decommission.py"')
    assert i_tag < i_dec, "the decommission must run after the ship has verified and tagged"
    gate = s[s.index("if a.decommission"):i_dec]
    assert "not DRY" in gate, "--dry-run must not retire a vhost"
    assert "if not ok" in gate, "a ship that did not verify must not retire a vhost"


def test_dry_run_is_the_default(tmp_path):
    """--apply is opt-in. A destructive tool whose default is destructive gets run by accident."""
    src = open(os.path.join(ROOT, "decommission.py"), encoding="utf-8").read()
    assert 'add_argument("--apply", action="store_true"' in src
    assert "if not a.apply:\n        return 0" in src, \
        "the plan must return BEFORE anything is applied unless --apply was passed"
