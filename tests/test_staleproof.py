"""test_staleproof.py — the reload doctrine's negative control, proved without docker.

WHAT IS UNDER TEST. `agent.cmd_staleproof()` is the answer to mistral-3-14B's finding on the
22 Nov staging panel: `guard_write_path_reloads` measures that a change written through apply()
DOES reach the running config, and then asserts the other half in prose - "a bare file edit does
NOT propagate" - which is the 2026-08-07 mechanism and the only clause nobody measured.

WHY A STUB RATHER THAN A SKIP. Docker is not installed on every machine the suite runs on, and a
`sys.platform`/`shutil.which` skip hides the defect from the machine that needs it (class 20, and
test_caddy_wiring.py learned it the expensive way: it skipped on Windows, was never reached in CI,
and two red tests sat unseen for weeks). So docker is SIMULATED: a fake `sh` answers the real
commands with the state a real caddy would have, and the tests assert the stub WAS consulted.

The stub models the one fact the whole doctrine rests on - Caddy reads its config at start or on
reload, never because a file changed - and a second stub models a hypothetical caddy that does
hot-reload on write, so the check can be shown to FAIL when its claim is false. Without that
second case the test would only prove the check can say yes (class 3).
"""
import importlib.util
import io
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT = os.path.join(ROOT, "deploy", "caddyguard", "agent.py")


def _agent():
    spec = importlib.util.spec_from_file_location("_cg_agent_for_test", AGENT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class _R:
    def __init__(self, rc=0, out="", err=""):
        self.returncode, self.stdout, self.stderr = rc, out, err


def _config_json(hosts):
    """The shape agent._served() reads: a route per host with a host matcher."""
    return json.dumps({"apps": {"http": {"servers": {"srv0": {"routes": [
        {"match": [{"host": [h]}],
         "handle": [{"handler": "static_response", "status_code": 200}]} for h in sorted(hosts)
    ]}}}}})


class FakeDocker:
    """A caddy that behaves like the real one: it serves what it was last TOLD, not what is on
    disk. `hot_reload=True` makes it the hypothetical broken one that follows the file."""

    def __init__(self, cfgdir, hot_reload=False, start_fails=False, never_answers=False,
                 serves_nothing=False, ignores_loads=False):
        self.cfgdir = cfgdir
        self.hot_reload = hot_reload
        self.start_fails = start_fails
        self.never_answers = never_answers
        self.serves_nothing = serves_nothing      # a container that came up dead
        self.ignores_loads = ignores_loads        # a container that accepts no change at all
        self.running = set()
        self.removed = False
        self.seen = []

    def _hosts_on_disk(self):
        txt = ""
        p = os.path.join(self.cfgdir, "Caddyfile")
        if os.path.exists(p):
            txt = io.open(p, encoding="utf-8").read()
        out = set()
        for line in txt.split("\n"):
            line = line.strip()
            if line.endswith("{") and ":" in line and not line.startswith(("#", "{")):
                out.add(line.split("{")[0].strip().split(":")[0])
        return out

    def __call__(self, cmd, **kw):
        self.seen.append(list(cmd))
        j = " ".join(cmd)
        if cmd[:3] == ["docker", "ps", "-a"]:
            return _R(0, "caddy\n")
        if cmd[:2] == ["docker", "inspect"]:
            if "Mounts" in j:
                return _R(0, "/opt/videodead/Caddyfile\n")
            if "Config.Image" in j:
                return _R(0, "caddy:2-alpine\n")
            return _R(0, "\n")
        if cmd[:2] == ["docker", "run"]:
            if self.start_fails:
                return _R(1, "", "no such image")
            # THE START is the only moment a real caddy reads the file by itself.
            self.running = set() if self.serves_nothing else self._hosts_on_disk()
            return _R(0, "deadbeef\n")
        if cmd[:2] == ["docker", "exec"] and "2019/config/" in j and "/load" not in j:
            if self.never_answers:
                return _R(1, "", "connection refused")
            if self.hot_reload:
                self.running = self._hosts_on_disk()      # the behaviour under suspicion
            return _R(0, _config_json(self.running))
        if cmd[:2] == ["docker", "exec"] and "/load" in j:
            if not self.ignores_loads:
                self.running = self._hosts_on_disk()      # an EXPLICIT load, which is apply()
            return _R(0, "")
        if cmd[:3] == ["docker", "rm", "-f"]:
            self.removed = True
            return _R(0, "")
        return _R(0, "")


@pytest.fixture()
def agent(tmp_path, monkeypatch):
    m = _agent()
    # The "live" file the experiment must leave untouched. Pointing it at a scratch path is the
    # point: if cmd_staleproof ever writes to the live source, this fixture catches it.
    live = tmp_path / "live.Caddyfile"
    live.write_text("example.com {\n  respond \"live\"\n}\n", encoding="utf-8")
    monkeypatch.setattr(m, "LIVE", str(live), raising=False)
    monkeypatch.setattr(m, "mount_source", lambda c: str(live))
    monkeypatch.setattr(m, "time", type("T", (), {"sleep": staticmethod(lambda *_a: None)}))
    return m, str(live)


def _run(m, fake, monkeypatch, capsys):
    monkeypatch.setattr(m, "sh", fake)
    rc = m.cmd_staleproof()
    return rc, capsys.readouterr().out


def test_a_correct_caddy_passes_and_the_stub_was_actually_consulted(agent, monkeypatch, capsys):
    m, live = agent
    fake = FakeDocker("/tmp/_cgstale")
    rc, out = _run(m, fake, monkeypatch, capsys)
    assert rc == 0, out
    assert out.startswith("OK"), out
    # A CHECK THAT NEVER REACHED ITS SUBJECT CAN STILL PRINT OK. Assert the experiment happened.
    assert any(c[:2] == ["docker", "run"] for c in fake.seen), "no throwaway container was started"
    assert sum(1 for c in fake.seen if "2019/config/" in " ".join(c)) >= 3, (
        "the running config was not read before the edit, after the edit and after the load")
    assert any("/load" in " ".join(c) for c in fake.seen), "the explicit load was never issued"
    assert fake.removed, "the throwaway container was left running"


def test_a_caddy_that_hot_reloads_on_write_FAILS_the_check(agent, monkeypatch, capsys):
    """THE MUTATION THAT MATTERS. If a bare edit ever did reach the running config, every write
    path in this repo would be built on a false premise - so the check must say so loudly rather
    than pass. Without this case the test above only proves the check can say yes (class 3)."""
    m, _live = agent
    fake = FakeDocker("/tmp/_cgstale", hot_reload=True)
    rc, out = _run(m, fake, monkeypatch, capsys)
    assert rc == 1, out
    assert "A BARE FILE EDIT REACHED THE RUNNING CONFIG" in out, out
    assert fake.removed, "the throwaway was left running on the failure path"


def test_a_container_that_serves_nothing_is_a_FIXTURE_failure_not_a_pass(agent, monkeypatch,
                                                                         capsys):
    """PROVE THE FIXTURE BEFORE BELIEVING THE RESULT (class 12). A throwaway that came up serving
    nothing would score "B is not in the running config" perfectly, every time, while measuring
    nothing at all. That is the exact shape of a check that cannot fail."""
    m, _live = agent
    fake = FakeDocker("/tmp/_cgstale", serves_nothing=True)
    rc, out = _run(m, fake, monkeypatch, capsys)
    assert rc == 1, out
    assert "the fixture does not reproduce the condition" in out, out


def test_a_container_that_accepts_no_change_FAILS_rather_than_passing(agent, monkeypatch, capsys):
    """THE CONTROL. If the explicit admin load does not publish B either, then step 3 proved
    nothing: a container that refuses every change passes "a bare edit did not propagate" for the
    wrong reason. The check must notice and say so (class 13 - defeat every guard on the path)."""
    m, _live = agent
    fake = FakeDocker("/tmp/_cgstale", ignores_loads=True)
    rc, out = _run(m, fake, monkeypatch, capsys)
    assert rc == 1, out
    assert "did NOT publish" in out and "proves nothing about bare edits" in out, out


def test_a_throwaway_that_never_starts_is_a_SKIP_not_a_pass(agent, monkeypatch, capsys):
    m, _live = agent
    fake = FakeDocker("/tmp/_cgstale", start_fails=True)
    rc, out = _run(m, fake, monkeypatch, capsys)
    assert rc == 0 and out.startswith("SKIP"), out
    # And the GATE must not score that SKIP as a pass - asserted in tests/test_gate_claims.py.


def test_a_throwaway_that_never_answers_reports_blindness_not_a_finding(agent, monkeypatch,
                                                                        capsys):
    """ABSENCE OF EVIDENCE IS NEVER A FINDING - the oldest rule in the repository. A container
    that will not answer its admin API tells us nothing about bare edits."""
    m, _live = agent
    fake = FakeDocker("/tmp/_cgstale", never_answers=True)
    rc, out = _run(m, fake, monkeypatch, capsys)
    assert rc == 0 and out.startswith("SKIP"), out
    assert "failure to OBSERVE" in out, out
    assert fake.removed, "the throwaway was left running after the skip"


def test_the_live_config_is_untouched_and_proved_so(agent, monkeypatch, capsys):
    m, live = agent
    before = io.open(live, encoding="utf-8").read()
    fake = FakeDocker("/tmp/_cgstale")
    rc, out = _run(m, fake, monkeypatch, capsys)
    assert rc == 0
    assert io.open(live, encoding="utf-8").read() == before, "the live config was modified"
    # ...and the PASS detail says so with the hash, rather than leaving the reader to trust it.
    assert live in out and "byte-identical" in out, out


def test_a_changed_live_file_is_caught_even_when_the_experiment_itself_succeeded(agent,
                                                                                monkeypatch,
                                                                                capsys):
    """DEFEAT EVERY GUARD ON THE PATH (class 13). The hash comparison must be able to fail on its
    own, not only alongside some other failure."""
    m, live = agent
    fake = FakeDocker("/tmp/_cgstale")

    class Meddling(FakeDocker):
        def __call__(self, cmd, **kw):
            if cmd[:2] == ["docker", "run"]:
                io.open(live, "a", encoding="utf-8").write("\n# somebody wrote here\n")
            return FakeDocker.__call__(self, cmd, **kw)

    rc, out = _run(m, Meddling("/tmp/_cgstale"), monkeypatch, capsys)
    assert rc == 1 and "THE LIVE FILE CHANGED" in out, out
    assert fake is not None


def test_the_experiment_uses_unresolvable_names(agent, monkeypatch, capsys):
    """RFC 2606 reserves .invalid so a test hostname cannot collide with, or be routed to, a real
    one. On a box that also runs the production proxy that is not a detail."""
    src = io.open(AGENT, encoding="utf-8").read()
    i = src.index("def cmd_staleproof(")
    body = src[i:src.index("\ndef ", i + 10)]
    assert 'A = "a.invalid"' in body and 'B = "b.invalid"' in body, body[:400]
    assert "auto_https off" in body, (
        "the throwaway would try to obtain a certificate for the test names")


def test_it_refuses_when_there_is_no_caddy_at_all(agent, monkeypatch, capsys):
    m, _live = agent
    monkeypatch.setattr(m, "container", lambda: "")
    rc, out = _run(m, FakeDocker("/tmp/_cgstale"), monkeypatch, capsys)
    assert rc == 0 and out.startswith("SKIP"), out


def test_the_verb_is_reachable_from_the_command_line():
    """IMPORT IS NOT RUN, and a verb nobody dispatched is a function nobody calls (class 48/9)."""
    src = io.open(AGENT, encoding="utf-8").read()
    assert '"staleproof"' in src and "return cmd_staleproof()" in src, (
        "the verb exists but main() never dispatches to it")
    m = _agent()
    assert hasattr(m, "cmd_staleproof")
