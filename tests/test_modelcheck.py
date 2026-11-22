"""test_modelcheck.py — ENTITLEMENT IS NOT VISIBILITY, and a check that confuses them is blind.

THE INCIDENT (22 Nov 2026, the Verint run). `deepseek-v4.1-flash` replaced the deprecated
`deepseek-3.2` at the head of the chain. `modelcheck.py` passed, the staging gate passed, the
release shipped — and every call to the new head came back **HTTP 403**:

    [warn] enrich: model 'deepseek-v4.1-flash' returned HTTP 403 (not entitled)
    [enrich-mr] shard 0: 0/3 ids in 261ms  ERROR: HTTP Error 403: Forbidden
    [enrich-mr] shard 4: 0/1 ids in 144ms  ERROR: HTTP Error 403: Forbidden

The id was right. The model is in the catalogue. The KEY is not granted it. My check asked the
catalogue — `/models` — and called the chain verified, which measures whether DigitalOcean *lists*
the model, not whether we may *call* it. CLAUDE.md has carried the rule the whole time:
"Entitlement is not visibility: every `anthropic-*` and commercial `openai-gpt-*` returns 403 on
this account." I wrote a check that could not fail for the reason that actually occurs.

So the probe is now a REAL one-token call, and the three outcomes get three different diagnoses,
because they have three different repairs:

    200/400  usable            (400 = the model wants its own payload shape; kimi does this)
    403      id right, KEY not entitled   -> DigitalOcean console, grant the model to the key
    404      id wrong                     -> enrich.py::_FALLBACKS

And the HEAD is treated differently from the rest: the chain is built to degrade, so an unusable
model at position 2+ is a warning. An unusable head costs every single call a wasted round-trip
before it fails over, which is what those 261ms and 144ms shards were.
"""
import io
import os
import re
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELCHECK = os.path.join(ROOT, "modelcheck.py")


def _remote_source():
    """The payload that runs INSIDE colt-web, lifted from the module that ships it.

    Read rather than re-typed: a copy of the logic here would drift from the thing that actually
    runs, and then this file would be testing itself (class 3).
    """
    src = io.open(MODELCHECK, encoding="utf-8").read()
    m = re.search(r"REMOTE = r'''(.*?)'''", src, re.S)
    assert m, "the remote payload is no longer a REMOTE = r''' ... ''' block"
    return m.group(1)


HARNESS = '''
import json, io, sys, urllib.error, urllib.request

CODES = json.loads(%r)          # model id -> HTTP code the gateway answers
CATALOG = json.loads(%r)

class _Resp:
    def __init__(self, payload, status=200):
        self._b = json.dumps(payload).encode(); self.status = status
    def read(self): return self._b
    def __enter__(self): return self
    def __exit__(self, *a): return False

def fake_urlopen(req, timeout=0):
    url = req.full_url if hasattr(req, "full_url") else str(req)
    if url.endswith("/models"):
        return _Resp({"data": [{"id": i} for i in CATALOG]})
    body = json.loads(req.data.decode())
    code = CODES.get(body["model"], 200)
    if code in (200, 201):
        return _Resp({"ok": True}, code)
    raise urllib.error.HTTPError(url, code, "x", {}, io.BytesIO(b'{"detail":"nope"}'))

urllib.request.urlopen = fake_urlopen
'''


def _run(chain, codes, catalog, key="k" * 71):
    """Execute the REAL remote payload against a simulated gateway.

    SIMULATE, DO NOT SKIP (class 20). There is no DigitalOcean here and no key; skipping would
    leave this logic untested on every machine, which is how the catalogue-only check survived.
    """
    import json as _json
    prog = (HARNESS % (_json.dumps(codes), _json.dumps(catalog))) + _remote_source()
    env = dict(os.environ, OPENAI_API_KEY=key,
               OPENAI_BASE_URL="https://inference.do-ai.run/v1")
    env.pop("DO_INFERENCE_KEY", None)
    r = subprocess.run([sys.executable, "-c", prog, ",".join(chain)],
                       capture_output=True, text=True, env=env, timeout=60)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


CHAIN = ["deepseek-v4.1-flash", "openai-gpt-oss-120b", "mistral-3-14B", "kimi-k2.6"]
ALL_VISIBLE = CHAIN + ["deepseek-3.2", "llama-4-maverick"]


def test_a_usable_chain_passes():
    rc, out = _run(CHAIN, {m: 200 for m in CHAIN}, ALL_VISIBLE)
    assert rc == 0, out
    assert out.count("OK ") == len(CHAIN), out


def test_the_verint_failure_is_caught_and_named_as_entitlement():
    """THE WHOLE POINT. The head is in the catalogue and answers 403. A catalogue check calls this
    chain healthy; this one must fail and say the key is the problem, not the id."""
    rc, out = _run(CHAIN, {"deepseek-v4.1-flash": 403}, ALL_VISIBLE)
    assert rc == 1, out
    assert "FORBIDDEN" in out and "deepseek-v4.1-flash" in out, out
    assert "not entitled" in out, out
    assert "MISSING" not in out, "a 403 was reported as a missing id - the opposite repair"


def test_a_wrong_id_is_named_as_a_wrong_id_with_the_alternatives():
    """The OTHER failure, with the opposite repair: `deepseek-v4-flash` came off a pricing page
    and 404'd for days."""
    rc, out = _run(["deepseek-v4-flash"] + CHAIN[1:],
                   {"deepseek-v4-flash": 404}, ALL_VISIBLE)
    assert rc == 1, out
    assert "MISSING" in out and "FORBIDDEN" not in out, out
    assert "NEAR" in out and "deepseek-v4.1-flash" in out, (
        "it did not print the ids that vendor does serve, so the operator guesses again")


def test_an_unusable_model_behind_the_head_warns_and_does_not_block():
    """The chain is BUILT to degrade. Blocking a release over a model it is designed to fail past
    would make this check the reason a release cannot ship."""
    rc, out = _run(CHAIN, {"kimi-k2.6": 403}, ALL_VISIBLE)
    assert rc == 2, out
    assert "FORBIDDEN" in out and "kimi-k2.6" in out, out


def test_a_400_is_usable_because_the_model_answered():
    """kimi returns 400 to a bare probe - it wants its own payload. That proves the model exists
    AND the key may call it; scoring it as a failure would demote a working vendor."""
    rc, out = _run(CHAIN, {"kimi-k2.6": 400}, ALL_VISIBLE)
    assert rc == 0, out
    assert "wants its own payload" in out, out


def test_the_key_fingerprint_is_reported_and_is_not_the_key():
    """'Did the new key actually land?' is unanswerable from a 403, and it is the first thing you
    need. The fingerprint is a sha256 PREFIX: this repository is public."""
    rc, out = _run(CHAIN, {m: 200 for m in CHAIN}, ALL_VISIBLE, key="SUPERSECRETKEY" * 5)
    assert rc == 0, out
    m = re.search(r"KEY\s+fingerprint ([0-9a-f]{12}), (\d+) chars", out)
    assert m, out
    assert "SUPERSECRETKEY" not in out, "the key itself was printed"
    import hashlib
    assert m.group(1) == hashlib.sha256(("SUPERSECRETKEY" * 5).encode()).hexdigest()[:12]


def test_no_key_is_an_unknown_not_a_verdict_about_the_chain():
    """A check that cannot see its subject must not answer (class 1)."""
    import json as _json
    prog = (HARNESS % (_json.dumps({}), _json.dumps(ALL_VISIBLE))) + _remote_source()
    env = {k: v for k, v in os.environ.items()
           if k not in ("OPENAI_API_KEY", "DO_INFERENCE_KEY")}
    r = subprocess.run([sys.executable, "-c", prog, ",".join(CHAIN)],
                       capture_output=True, text=True, env=env, timeout=60)
    assert r.returncode == 3, r.stdout + r.stderr
    assert "UNKNOWN" in r.stdout, r.stdout


@pytest.mark.parametrize("word,why", [
    ("visible", "the catalogue tells you a model is LISTED, never that you may call it"),
    ("/models", "the catalogue endpoint alone is what let the Verint 403 through"),
])
def test_the_check_does_not_rest_on_the_catalogue_alone(word, why):
    """The repair for the incident is that a real call is made. Asserting the call exists is the
    wiring half (class 9); the simulated 403 above is the behaviour half."""
    remote = _remote_source()
    assert "/chat/completions" in remote, (
        "no real request is issued, so %s" % why)
    assert remote.index("/models") < remote.index("/chat/completions"), (
        "the catalogue is read for context, and the CALL is what decides")
