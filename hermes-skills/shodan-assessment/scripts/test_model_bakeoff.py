#!/usr/bin/env python3
"""test_model_bakeoff.py - replacing a retired chain slot must be one measured command.

THE INCIDENT (9 November 2026)
    DigitalOcean retired llama-4-maverick and gemma-4-31B-it on a published date, with eleven days
    of notice against their own fourteen day policy. On the morning of the 10th both ids were
    still in enrich._FALLBACKS. Nothing was down: the chain failed over to deepseek-3.2 and
    kimi-k2.6 exactly as designed, which is precisely why it was invisible. What it actually cost
    was two dead round trips on every call, and the four vendor property the chain exists for,
    which was quietly down to two.

WHAT IS TESTED HERE
    1. A 404 is remembered for the process. Reads and probes may retry; asking a question whose
       answer cannot change within a run is not a retry, it is waste.
    2. The bake-off measures what we do NOT run, uncapped. --probe-all measures everything and
       then cuts to an arbitrary alphabetical six, which answers a different question.
    3. Vendor comes from the API's own owned_by, never from the id string. mimo-v2.5-pro is
       Xiaomi and reflection-beam is Reflection AI; neither id says so, and vendor identity is the
       whole point of the chain.
    4. The orchestrator carries it, so the operator runs one command rather than ssh plus docker.

PROVED BY MUTATION
    * the 404 branch deleted from _call          -> test_a_dead_model_is_remembered FAILS
    * _GONE never added to                       -> test_a_dead_model_is_remembered FAILS
    * vendor() reading the id instead of OWNERS  -> test_vendor_comes_from_the_api FAILS
    * the [:6] cap applied to --unused           -> test_unused_is_uncapped FAILS
    * --model-bakeoff removed from ship.py       -> test_the_orchestrator_carries_it FAILS
"""
import os
import re
import sys
import urllib.error

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import enrich                                   # noqa: E402
import model_watch                              # noqa: E402

SHIP = os.path.abspath(os.path.join(HERE, "..", "..", "..", "ship.py"))


def _http404(url="https://inference.invalid/v1/completions-endpoint"):
    """The URL is a PLACEHOLDER and deliberately not the real path.

    tests/test_llm_meter.py scans every script in this directory for the real completions path and
    fails if a second file outside enrich.py appears to talk to the inference endpoint directly.
    That guard is correct and worth more than my convenience here: this file never calls anything,
    it only constructs an exception object, so it has no business carrying the real URL. Weakening
    the guard to let a test through would have been the easy fix and the wrong one.
    """
    return urllib.error.HTTPError(url, 404, "Not Found", {}, None)


@pytest.fixture(autouse=True)
def _clean_gone():
    enrich._GONE.clear()
    yield
    enrich._GONE.clear()


# --------------------------------------------------------------- 1. the 404 memory

def test_a_dead_model_is_remembered(monkeypatch, capsys):
    """One warning, one entry, and the id is named so the fix is obvious."""
    monkeypatch.setattr(enrich, "_post", lambda *a, **k: (_ for _ in ()).throw(_http404()))
    for _ in range(3):
        with pytest.raises(urllib.error.HTTPError):
            enrich._call("prompt", model="llama-4-maverick", timeout=5)
    assert "llama-4-maverick" in enrich._GONE
    err = capsys.readouterr().err
    assert err.count("404") == 1, "the warning fired more than once: %r" % err
    assert "model_not_found" in err and "_FALLBACKS" in err, err


def test_the_404_still_fails_over(monkeypatch):
    """Remembering must not swallow. The caller has to see the failure to try the next model."""
    monkeypatch.setattr(enrich, "_post", lambda *a, **k: (_ for _ in ()).throw(_http404()))
    with pytest.raises(urllib.error.HTTPError):
        enrich._call("prompt", model="gemma-4-31B-it", timeout=5)


def test_a_400_is_not_treated_as_death(monkeypatch):
    """A 400 is the server describing the REQUEST. The model is alive and must stay in the chain."""
    err = urllib.error.HTTPError("u", 400, "Bad Request", {}, None)
    monkeypatch.setattr(enrich, "_post", lambda *a, **k: (_ for _ in ()).throw(err))
    try:
        enrich._call("prompt", model="kimi-k2.6", timeout=5)
    except Exception:
        pass
    assert "kimi-k2.6" not in enrich._GONE


def test_nothing_is_remembered_across_processes():
    """_GONE is in memory on purpose: the catalog is DO's to change, not ours to cache."""
    src = open(os.path.join(HERE, "enrich.py"), encoding="utf-8").read()
    blk = src[src.index("_GONE = set()") - 400:src.index("_GONE = set()") + 40]
    assert "Not persisted" in blk, "the reasoning for not persisting _GONE has been lost"


# --------------------------------------------------------------- 2 and 3. the bake-off

def test_owned_by_is_only_a_fallback_for_an_unknown_id():
    """DOCTRINE CORRECTED 10 NOV 2026, OLD REASONING KEPT HERE ON PURPOSE.

    This test used to assert the opposite: that vendor() must read the API's `owned_by` and never
    parse the id, on the reasoning that asking the API beats guessing from a string. That
    reasoning was sound and the fact was wrong. DigitalOcean's catalog reports `owned_by:
    digitalocean` for every model it serves, so the first real bake-off printed a VENDOR column
    with one value on every row. The id prefix is now the primary source and owned_by is consulted
    only for an id the table does not know, with the gateway's own name rejected there.
    """
    model_watch.OWNERS.clear()
    model_watch.OWNERS["acme-wonder-7b"] = "acme"
    assert model_watch.vendor("acme-wonder-7b") == "acme", "the fallback no longer works"
    model_watch.OWNERS["acme-wonder-7b"] = "digitalocean"
    assert model_watch.vendor("acme-wonder-7b") == "?"


def test_catalog_fills_owners(monkeypatch):
    payload = b'{"data":[{"id":"a-1","owned_by":"acme"},{"id":"b-2","owned_by":"beta"}]}'

    class _R:
        def read(self):
            return payload

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(model_watch, "KEY", "x")
    monkeypatch.setattr(model_watch.urllib.request, "urlopen", lambda *a, **k: _R())
    ids, err = model_watch.catalog()
    assert not err and ids == ["a-1", "b-2"]
    assert model_watch.vendor("a-1") == "acme" and model_watch.vendor("b-2") == "beta"


def test_unused_is_uncapped():
    """The six-model cap keeps an automatic deploy cheap. A deliberate bake-off is not automatic,
    and cutting a named comparison to six answers a different question than the one asked."""
    src = open(os.path.join(HERE, "model_watch.py"), encoding="utf-8").read()
    body = src[src.index("def main("):]
    cap = re.search(r"if not asked:\s*\n\s*todo = todo\[:6\]", body)
    assert cap, "the cap moved; this test no longer measures the thing it was written for"
    # --unused fills `asked`, so the cap cannot apply to it. Assert the wiring, not the comment.
    assert re.search(r"if a\.unused and not asked:", body), "--unused no longer populates asked"


def test_unused_excludes_the_models_we_already_run():
    src = open(os.path.join(HERE, "model_watch.py"), encoding="utf-8").read()
    assert "m not in _chain" in src, "--unused no longer excludes the current chain"
    assert "NOT IN CATALOG, this slot is dead" in src, (
        "the dead-slot callout is gone: a retired chain model must be named, not merely absent")


def test_the_result_table_reports_vendor_diversity():
    src = open(os.path.join(HERE, "model_watch.py"), encoding="utf-8").read()
    for needle in ("RESTORES VENDOR DIVERSITY?", "already in the chain",
                   "Vendors still live in the chain", "Nothing has been changed"):
        assert needle in src, "the bake-off table lost: %r" % needle


def test_the_bakeoff_refuses_rather_than_guesses_when_the_chain_is_unreadable():
    src = open(os.path.join(HERE, "model_watch.py"), encoding="utf-8").read()
    assert "--unused needs it to know" in src, (
        "with no chain, 'unused' has no meaning and the run must say so rather than measure "
        "everything and call it a shortlist")


# --------------------------------------------------------------- 3b. which copy actually runs

def test_the_key_is_found_without_an_environment_variable(monkeypatch, tmp_path):
    """THE WASTED RUN THIS PINS.

    With no OPENAI_API_KEY in the environment, the local run printed "catalog unavailable" and the
    work fell through to the droplet, where it executes the IMAGE's copy of model_watch.py. The
    moment --unused was added to the working tree, the operator got
    `model_watch.py: error: unrecognized arguments: --unused` from a container running last week's
    file. Finding the key locally is what makes the LATEST code the code that runs.
    """
    for v in ("OPENAI_API_KEY", "DO_INFERENCE_KEY"):
        monkeypatch.delenv(v, raising=False)
    root = tmp_path / "repo" / "hermes-skills" / "shodan-assessment" / "scripts"
    root.mkdir(parents=True)
    env = tmp_path / "repo" / "assess-bot"
    env.mkdir(parents=True)
    (env / ".env").write_text("BOT_TOKEN=abc\nDO_INFERENCE_KEY=sk-from-file\n", encoding="utf-8")
    assert enrich.resolve_key(start=str(root)) == "sk-from-file"


def test_preference_order_beats_file_order(monkeypatch, tmp_path):
    """THE STALE KEY THAT WON BY BEING LISTED FIRST.

    `set_secret.py OPENAI_API_KEY` installed a new credential correctly. The engine went on using
    the OLD one, because assess-bot/.env lists DO_INFERENCE_KEY above OPENAI_API_KEY and the file
    branch of resolve_key() returned the first matching LINE rather than the preferred NAME. The
    env branch had always had this right. The bake-off's own fingerprint is what exposed it: the
    file held two different credentials and the resolver picked the stale one.
    """
    for v in ("OPENAI_API_KEY", "DO_INFERENCE_KEY"):
        monkeypatch.delenv(v, raising=False)
    root = tmp_path / "repo" / "a" / "b" / "c"
    root.mkdir(parents=True)
    env = tmp_path / "repo" / "assess-bot"
    env.mkdir(parents=True)
    # DO_INFERENCE_KEY FIRST, exactly as the real file has it
    (env / ".env").write_text(
        "DO_INFERENCE_KEY=sk-OLD-stale\nOPENAI_API_KEY=sk-NEW-current\n", encoding="utf-8")
    assert enrich.resolve_key(start=str(root)) == "sk-NEW-current", (
        "file order decided the winner again; the newly installed key is being ignored")


def test_a_lone_fallback_name_is_still_honoured(monkeypatch, tmp_path):
    """Preference order must not become 'OPENAI_API_KEY or nothing'."""
    for v in ("OPENAI_API_KEY", "DO_INFERENCE_KEY"):
        monkeypatch.delenv(v, raising=False)
    root = tmp_path / "repo" / "a" / "b" / "c"
    root.mkdir(parents=True)
    env = tmp_path / "repo" / "assess-bot"
    env.mkdir(parents=True)
    (env / ".env").write_text("DO_INFERENCE_KEY=sk-only-one\n", encoding="utf-8")
    assert enrich.resolve_key(start=str(root)) == "sk-only-one"


def test_two_different_credentials_are_reported(monkeypatch, tmp_path, capsys):
    """A stale duplicate looks like a working credential and wins or loses on ordering alone."""
    for v in ("OPENAI_API_KEY", "DO_INFERENCE_KEY"):
        monkeypatch.delenv(v, raising=False)
    root = tmp_path / "repo" / "a" / "b" / "c"
    root.mkdir(parents=True)
    env = tmp_path / "repo" / "assess-bot"
    env.mkdir(parents=True)
    (env / ".env").write_text("DO_INFERENCE_KEY=sk-OLD\nOPENAI_API_KEY=sk-NEW\n", encoding="utf-8")
    enrich.resolve_key(start=str(root))
    err = capsys.readouterr().err
    assert "DIFFERENT credentials" in err
    assert "sk-OLD" not in err and "sk-NEW" not in err, "the warning printed the secrets"


def test_identical_duplicates_are_silent(monkeypatch, tmp_path, capsys):
    """Two names holding the SAME value is tidy-up, not a fault. Benign-every-time is the enemy."""
    for v in ("OPENAI_API_KEY", "DO_INFERENCE_KEY"):
        monkeypatch.delenv(v, raising=False)
    root = tmp_path / "repo" / "a" / "b" / "c"
    root.mkdir(parents=True)
    env = tmp_path / "repo" / "assess-bot"
    env.mkdir(parents=True)
    (env / ".env").write_text("DO_INFERENCE_KEY=same\nOPENAI_API_KEY=same\n", encoding="utf-8")
    enrich.resolve_key(start=str(root))
    assert "DIFFERENT credentials" not in capsys.readouterr().err


def test_the_environment_still_wins(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-from-env")
    assert enrich.resolve_key() == "sk-from-env"
    assert model_watch._key() == "sk-from-env"


def test_no_key_anywhere_is_empty_not_a_crash(monkeypatch, tmp_path):
    for v in ("OPENAI_API_KEY", "DO_INFERENCE_KEY"):
        monkeypatch.delenv(v, raising=False)
    assert enrich.resolve_key(start=str(tmp_path)) == ""


# --------------------------------------------------------------- 3c. what the first real run found

def test_the_key_has_exactly_one_home():
    """THE BAKE-OFF THAT MEASURED NOTHING.

    model_watch grew its own key lookup so the CATALOG call would work locally. It did: 78 models.
    Every PROBE then returned HTTP 401, because probe() goes through enrich._call and enrich still
    had the environment-only lookup. Nineteen models were reported FAIL under a column headed
    CONTRACT. One secret, two homes, and the newer one won in one of the two places that mattered.
    """
    assert hasattr(enrich, "resolve_key"), "the shared resolver is gone"
    src = open(os.path.join(HERE, "model_watch.py"), encoding="utf-8").read()
    assert "_E.resolve_key()" in src, "model_watch has grown its own key lookup again"

    # ANCHOR ON THE ASSIGNMENT, NOT ON THE RUNTIME VALUE. The first version of this line asserted
    # `enrich.KEY == enrich.resolve_key()`, which is trivially true when BOTH are empty, so it
    # passed in a checkout with no assess-bot/.env and in CI. Reverting enrich.KEY to the
    # environment-only lookup, which is the exact defect that wasted a bake-off, did not fail it.
    esrc = open(os.path.join(HERE, "enrich.py"), encoding="utf-8").read()
    esrc = re.sub(r"#.*", "", esrc)
    assert re.search(r"^KEY\s*=\s*resolve_key\(\)", esrc, re.M), (
        "enrich.KEY no longer comes from resolve_key(). This is the defect that made the first "
        "bake-off report 19 models as CONTRACT FAIL when the real fault was an empty bearer.")


def test_an_auth_failure_is_not_a_contract_failure(monkeypatch):
    """401 and 403 say nothing about the model. Rendering them as FAIL is a wrong verdict."""
    err = urllib.error.HTTPError("u", 401, "Unauthorized", {}, None)

    class _E:
        PROMPT = "p"

        @staticmethod
        def _call(*a, **k):
            raise err

        @staticmethod
        def _json(s):
            return {}

    monkeypatch.setitem(sys.modules, "enrich", _E)
    monkeypatch.setattr(model_watch, "entitled", lambda m: (True, ""))
    r = model_watch.probe("mistral-3-14B", timeout=1)
    assert r["ok"] is None and r.get("auth") is True, r
    assert "says nothing about the model" in r["err"], r["err"]


def test_an_all_auth_run_reports_one_fault_not_many_verdicts():
    src = open(os.path.join(HERE, "model_watch.py"), encoding="utf-8").read()
    assert "EVERY probe failed to authenticate" in src
    assert "not %d verdicts about %d models" in src, (
        "an all-401 run must name the single credential fault, not imply N model verdicts")


@pytest.mark.parametrize("mid,want", [
    ("deepseek-3.2", "deepseek"), ("llama-4-maverick", "meta"), ("gemma-4-31B-it", "google"),
    ("kimi-k2.6", "moonshot"), ("mistral-3-14B", "mistral"), ("nemotron-3.5-super-vl", "nvidia"),
    ("reflection-beam", "reflection"), ("qwen3.8-max", "alibaba"), ("mimo-v2.5-pro", "xiaomi"),
    ("glm-5.3-flash", "z.ai"),
])
def test_vendor_is_the_model_vendor_not_the_gateway(mid, want):
    """owned_by says `digitalocean` for everything it serves, so the first run printed a VENDOR
    column with one value on every row, and `Vendors still live in the chain: digitalocean`. A
    column that renders the same value whatever the input is templated output, and this one
    decides whether a replacement restores the four-vendor property."""
    model_watch.OWNERS.clear()
    model_watch.OWNERS[mid] = "digitalocean"
    assert model_watch.vendor(mid) == want


def test_the_gateway_name_is_never_accepted_as_a_vendor():
    model_watch.OWNERS.clear()
    model_watch.OWNERS["some-unknown-id"] = "digitalocean"
    assert model_watch.vendor("some-unknown-id") == "?", (
        "the gateway's own name must not be counted as a model vendor")


def test_a_distinct_chain_really_has_distinct_vendors():
    model_watch.OWNERS.clear()
    chain = ["deepseek-3.2", "llama-4-maverick", "gemma-4-31B-it", "kimi-k2.6"]
    assert len({model_watch.vendor(m) for m in chain}) == 4, "the four-vendor property is unmeasurable"


@pytest.mark.parametrize("mid", [
    "all-mini-lm-l6-v2", "bge-m3", "e5-large-v2", "gte-large-en-v1.5",
    "multi-qa-mpnet-base-dot-v1", "router:general", "router:writing",
])
def test_encoders_and_routers_are_not_probed(mid):
    """The first run sent the full enrichment prompt to five sentence encoders and four routers.
    None of them has the word 'embed' in its id, which is all the filter looked for."""
    assert model_watch.NON_TEXT_RE.search(mid), "%s would be probed as a chat model" % mid


@pytest.mark.parametrize("mid", [
    "deepseek-v4.1-flash", "mistral-3-14B", "nemotron-3.5-super-vl", "reflection-beam",
    "qwen3.8-max",
])
def test_the_real_candidates_are_still_probed(mid):
    """The filter must not over-match. These five are exactly what the bake-off exists to measure."""
    assert not model_watch.NON_TEXT_RE.search(mid), "%s was excluded from its own bake-off" % mid


# --------------------------------------------------------------- 3d. the control

def test_there_is_a_control_probe():
    """THE 10 NOVEMBER RUN COULD NOT TELL TWO THINGS APART.

    Ten candidates came back 403 and the output said nothing about why, because the chain models
    are excluded from the bake-off by definition and so the one measurement that separates "these
    models are unavailable to us" from "this credential cannot invoke anything new" was never
    taken. A DigitalOcean model access key is scoped to a model list at creation and cannot be
    edited afterwards, so a key that predates a model 403s on it forever. The control is what
    turns that from a guess into a reading.
    """
    src = open(os.path.join(HERE, "model_watch.py"), encoding="utf-8").read()
    # ANCHOR ON THE PROPERTY, NOT THE LINE. This pinned the exact expression that selected the
    # control. The expression changed when the bake-off started measuring the WHOLE chain rather
    # than only the control, which is a better design, and the test failed for the wrong reason.
    assert "_chain_live = [m for m in _E.MODELS if m in ids]" in src, (
        "the chain is no longer derived from the live catalog")
    assert "_control = next(iter(_chain_live), None)" in src, (
        "the control no longer comes from the live chain")
    assert "THE CONTROL FAILED" in src
    assert "return 3" in src, "a failed control must not exit 0: nothing was measured"


def test_a_failed_control_refuses_to_report_candidate_verdicts():
    src = open(os.path.join(HERE, "model_watch.py"), encoding="utf-8").read()
    i = src.index("THE CONTROL FAILED")
    blk = src[i:i + 1400]
    assert "say NOTHING about any" in blk or "can say NOTHING" in blk
    assert "manage-keys" in blk, "the console page that answers this is not named"
    assert "CANNOT be edited" in blk, "the non-editable key scope is the whole diagnosis"


def test_the_control_runs_before_the_candidates():
    src = open(os.path.join(HERE, "model_watch.py"), encoding="utf-8").read()
    assert src.index("CONTROL passed") < src.index('"MODEL", "CONTRACT", "ms"'), (
        "the candidate table is printed before the control is known; a reader would take the "
        "verdicts at face value")


def test_the_403_note_does_not_blame_the_model():
    """DO documents one identical 403 body for key scope, provider terms and tier. Rendering that
    as a property of the model is the same error as rendering 401 as a contract failure."""
    src = open(os.path.join(HERE, "model_watch.py"), encoding="utf-8").read()
    assert "says nothing" in src and "about the model itself" in src


# --------------------------------------------------------------- 3e. the open-weights carve-out

@pytest.mark.parametrize("mid", ["openai-gpt-oss-120b", "openai-gpt-oss-20b"])
def test_open_weights_openai_models_are_probed(mid):
    """THE GUARD THAT HID THE ANSWER.

    UNENTITLED_PREFIXES contains "openai-gpt-" to catch the commercial ids. It also matches
    OpenAI's OPEN-WEIGHTS gpt-oss models, so they were reported NOT-ENTITLED on every run without
    ever being called. DigitalOcean's Inference Limits page says Tier 1 and Tier 2 lack Anthropic
    and OpenAI models "except gpt-oss-120b and gpt-oss-20b", which makes this the one OpenAI
    family the account is documented to be allowed to use.
    """
    ok, why = model_watch.entitled(mid)
    assert ok, "%s is still pre-screened out and will never be measured: %s" % (mid, why)
    assert not enrich.not_chainable(mid), "the chain-side guard disagrees with the probe-side one"


@pytest.mark.parametrize("mid", [
    "openai-gpt-5.4", "openai-gpt-6-1-sol", "openai-gpt-4o", "anthropic-claude-opus-5",
    "openai-o3",
])
def test_the_commercial_ids_are_still_barred(mid):
    """The carve-out must not open the door it was cut beside."""
    ok, _ = model_watch.entitled(mid)
    assert not ok, "%s is no longer barred; the carve-out is too wide" % mid


def test_the_two_guards_agree_about_every_openai_id():
    """One rule, two homes, and they disagreed: the chain accepted gpt-oss while the probe refused
    to measure it. Whatever the rule is, both sides must say the same thing."""
    for mid in ("openai-gpt-oss-120b", "openai-gpt-oss-20b", "openai-gpt-5.4", "openai-gpt-4o"):
        probe_ok = model_watch.entitled(mid)[0]
        chain_ok = not enrich.not_chainable(mid)
        assert probe_ok == chain_ok, (
            "%s: probe says entitled=%s, chain says chainable=%s" % (mid, probe_ok, chain_ok))


# --------------------------------------------------------------- 3f. probe() against the real contract

def test_probe_unpacks_what_call_actually_returns():
    """READ THE SIGNATURE. enrich._call returns (text, usage_dict), not a string.

    probe() did `j = E._json(raw)` on the tuple. deepseek-3.2 answered correctly in 42.7 seconds,
    the parse raised "'tuple' object has no attribute 'find'", and the control reported that crash
    as a verdict about the DigitalOcean credential, sending the reader to the console to fix a bug
    that lived in this file. This test calls probe() with a stub that returns the REAL shape.
    """
    import ast
    import inspect
    rets = [ast.unparse(n.value) for n in ast.walk(ast.parse(inspect.getsource(enrich._call)))
            if isinstance(n, ast.Return) and n.value is not None]
    assert rets and all(r.startswith("(") for r in rets), (
        "enrich._call no longer returns a tuple; probe() must be re-read against the new shape: %s"
        % rets)


def test_probe_succeeds_on_a_well_formed_answer(monkeypatch):
    calls = {}

    class _E:
        PROMPT = "p"

        @staticmethod
        def _call(text, model=None, timeout=None):
            calls["model"] = model
            return ('{"exec_summary": "ok", "findings": []}', {"completion_tokens": 123})

        @staticmethod
        def _json(s):
            import json as _j
            return _j.loads(s)

    monkeypatch.setitem(sys.modules, "enrich", _E)
    monkeypatch.setattr(model_watch, "entitled", lambda m: (True, ""))
    r = model_watch.probe("deepseek-3.2", timeout=1)
    assert r["ok"] is True, r
    assert r["tokens_out"] == 123, "usage from the second element of the tuple is ignored"
    assert calls["model"] == "deepseek-3.2"


def test_probe_reports_contract_invalid_not_a_crash(monkeypatch):
    class _E:
        PROMPT = "p"

        @staticmethod
        def _call(*a, **k):
            return ("not json at all", {})

        @staticmethod
        def _json(s):
            raise ValueError("no JSON value in model output")

    monkeypatch.setitem(sys.modules, "enrich", _E)
    monkeypatch.setattr(model_watch, "entitled", lambda m: (True, ""))
    r = model_watch.probe("some-model", timeout=1)
    assert r["ok"] is False and not r.get("auth")


def test_the_control_only_blames_the_key_on_a_real_refusal():
    """A TypeError in our own probe is not evidence about DigitalOcean's billing console."""
    src = open(os.path.join(HERE, "model_watch.py"), encoding="utf-8").read()
    i = src.index("THE CONTROL FAILED")
    blk = src[i:i + 1800]
    assert 'if _cr.get("auth"):' in blk, "the control blames the credential unconditionally again"
    assert "NOT an HTTP refusal" in blk and "probe harness itself failed" in blk
    assert blk.index('if _cr.get("auth"):') < blk.index("manage-keys"), (
        "the console advice must sit inside the auth branch")


# --------------------------------------------------------------- 3g. the bancobic.ao degradation

def test_the_chain_names_no_retired_model():
    """THE COST, MEASURED ON A REAL CUSTOMER RUN (bancobic.ao, 11 Nov 2026).

    llama-4-maverick and gemma-4-31B-it stayed in _FALLBACKS after DigitalOcean retired them.
    Three shards and two retries were spent on 404s, enrichment coverage came out at 20% against
    an 80% floor, four of five findings rendered as template text, the false-positive audit
    recorded "unaudited", and a bank received that deck.
    """
    retired = {"llama-4-maverick", "gemma-4-31B-it"}
    assert not (set(enrich.MODELS) & retired), (
        "the chain still names a retired model: %s" % (set(enrich.MODELS) & retired))


def test_a_403_is_remembered_like_a_404(monkeypatch, capsys):
    """Entitlement cannot change mid-run any more than retirement can, so asking twice is waste.

    This is also what makes an UNPROVEN model safe to chain: being wrong costs one round trip per
    process rather than one per finding.
    """
    err = urllib.error.HTTPError("u", 403, "Forbidden", {}, None)
    monkeypatch.setattr(enrich, "_post", lambda *a, **k: (_ for _ in ()).throw(err))
    for _ in range(3):
        with pytest.raises(urllib.error.HTTPError):
            enrich._call("p", model="mistral-3-14B", timeout=5)
    assert "mistral-3-14B" in enrich._GONE
    assert capsys.readouterr().err.count("403") == 1


def test_every_roster_derives_from_the_one_home():
    """Five lists named the dead for two days while the chain was fixed in one place."""
    root = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
    for rel, needle in (
        ("webapp/backend/app/release_notes.py", "_chain_or("),
        ("hermes-skills/shodan-assessment/scripts/proteus.py", "getattr(_E, \"MODELS\""),
        ("deploy/stagegate/quorum.py", "SOLDIERS, AUDITORS = _panel()"),
    ):
        p = os.path.join(root, *rel.split("/"))
        if not os.path.exists(p):
            continue
        src = open(p, encoding="utf-8").read()
        assert needle in src, "%s no longer derives the roster" % rel
        for dead in ('"llama-4-maverick"', '"gemma-4-31B-it"'):
            body = re.sub(r"#.*", "", src)
            assert dead not in body, "%s still hardcodes %s outside a comment" % (rel, dead)


def test_an_overloaded_upstream_is_transient_not_a_verdict(monkeypatch):
    """DigitalOcean answers an overloaded model with 529. The control took that as a hard failure,
    aborted the bake-off and told the operator to fix probe()."""
    calls = {"n": 0}

    class _E:
        PROMPT = "p"

        @staticmethod
        def _call(*a, **k):
            calls["n"] += 1
            raise urllib.error.HTTPError("u", 529, "Overloaded", {}, None)

        @staticmethod
        def _json(s):
            return {}

    monkeypatch.setitem(sys.modules, "enrich", _E)
    monkeypatch.setattr(model_watch, "entitled", lambda m: (True, ""))
    monkeypatch.setattr(model_watch.time, "sleep", lambda *_a: None)
    r = model_watch.probe("deepseek-3.2", timeout=1)
    assert r.get("transient") is True, r
    assert calls["n"] == 2, "a read may retry once; it did not retry (%d calls)" % calls["n"]
    assert not r.get("auth"), "a 529 must not be reported as an entitlement problem"


def test_the_control_names_the_transient_case():
    src = open(os.path.join(HERE, "model_watch.py"), encoding="utf-8").read()
    i = src.index("THE CONTROL FAILED")
    blk = src[i:i + 2200]
    assert 'elif _cr.get("transient"):' in blk
    assert "OVERLOADED" in blk and "Re-run in a few minutes" in blk


# --------------------------------------------------------------- 3h. the run that argued with itself

def test_the_all_auth_warning_cannot_fire_when_the_control_passed():
    """ONE RUN, TWO CONTRADICTORY CONCLUSIONS.

    The 11 Nov bake-off printed "CONTROL passed, so a 403 below is a statement about that model,
    not about the key" and then, nine lines later, "EVERY probe failed to authenticate ... Check
    the key". Both cannot be true. The blanket warning predates the control and never learned it
    existed. A diagnostic that contradicts itself in the same output is worse than a silent one:
    the reader has to guess which half to believe, and the obvious guess sent the operator to the
    billing console twice.
    """
    src = open(os.path.join(HERE, "model_watch.py"), encoding="utf-8").read()
    assert "and not _ctl_ok" in src, (
        "the all-auth warning fires regardless of the control again")
    assert "_ctl_ok = bool((out.get(\"control\") or {}).get(\"ok\"))" in src
    assert "while the CONTROL SUCCEEDED" in src, (
        "when the control passes, an all-403 sweep must state the OPPOSITE conclusion: the key "
        "works and those models are genuinely not enabled for it")


def test_the_chain_itself_is_always_measured():
    """--unused excludes the chain by definition. That is right for finding replacements and was
    wrong in the one run that mattered: two UNPROVEN models had just been deployed into the chain,
    and the bake-off skipped both because they were in it."""
    src = open(os.path.join(HERE, "model_watch.py"), encoding="utf-8").read()
    assert "CHAIN HEALTH" in src
    assert "_rest = [m for m in _chain_live if m != _control and m in ids]" in src
    assert "The chain is effectively %d deep." in src, (
        "a short chain must be stated as a number, not left for the reader to count")


def test_the_key_fingerprint_is_printed_and_is_not_the_secret():
    """'Did the new key actually land' was unanswerable from the output: two runs with different
    keys looked identical. A sha256 prefix is safe in a public repo and settles it."""
    src = open(os.path.join(HERE, "model_watch.py"), encoding="utf-8").read()
    assert "key fingerprint" in src and "sha256 prefix, not the secret" in src
    assert "hexdigest()[:12]" in src, "a 12-hex prefix, never the key itself"
    # and prove it really is a prefix of a hash of the key, not the key
    import hashlib
    k = "sk-test-not-a-real-key"
    fp = hashlib.sha256(k.encode()).hexdigest()[:12]
    assert k not in fp and len(fp) == 12


def test_vendor_diversity_counts_models_that_answered():
    """THE SECOND SELF-CONTRADICTION, 11 NOV.

    CHAIN HEALTH reported "3 of 4 chain models cannot answer. The chain is effectively 1 deep."
    Three lines later the summary said "Vendors still live in the chain: deepseek, mistral,
    moonshot, openai" — four vendors, from a chain that had one working model. Presence in the
    catalog is not the ability to answer, and the four-vendor property this whole chain exists for
    is about answering.
    """
    src = open(os.path.join(HERE, "model_watch.py"), encoding="utf-8").read()
    assert "LIVE MEANS IT ANSWERED" in src
    assert '_answered = {p["model"] for p in out["probed"]' in src
    assert "Vendors that ANSWERED this run" in src, "the heading still implies mere presence"
    assert "Listed but could NOT answer" in src, (
        "a chain member that cannot answer must be named, not just subtracted from a count")
    assert "_live = [m for m in _chain if m in _answered]" in src, (
        "_live is computed from the catalog again rather than from what answered")


# --------------------------------------------------------------- 4. one command

@pytest.mark.skipif(not os.path.exists(SHIP), reason="ship.py not in this checkout")
def test_the_orchestrator_carries_it():
    src = open(SHIP, encoding="utf-8").read()
    assert '"--model-bakeoff"' in src, "the operator is back to two commands"
    i, j = src.index("if a.model_bakeoff:"), src.index("if a.fix_ci_key")
    assert i < j, "the bake-off must exit before any gate; it deploys nothing"
    blk = src[i:j]
    assert "--unused" in blk and "return 0" in blk
    for forbidden in ("do_web(", "do_bots(", "git_push", "tag_known_good"):
        assert forbidden not in blk, "the bake-off must change nothing, found %r" % forbidden


@pytest.mark.skipif(not os.path.exists(SHIP), reason="ship.py not in this checkout")
def test_a_stale_remote_copy_is_diagnosed_not_reported_as_a_result():
    """Falling back to the deployed copy of the very script being changed is worse than not
    falling back: the operator gets an argparse error instead of a measurement, and nothing says
    why. The block must detect it and name both one-command ways out."""
    src = open(SHIP, encoding="utf-8").read()
    blk = src[src.index("if a.model_bakeoff:"):src.index("if a.fix_ci_key")]
    assert "unrecognized arguments" in blk, (
        "a stale remote model_watch.py would print an argparse error and be reported as output")
    assert "assess-bot/.env" in blk, "the fix is not named"
    assert "return 2" in blk, "a failed measurement must not exit 0"
