"""test_run_log.py — the customer-facing run log leaks nothing, and still says something.

The operator asked for the full run log per company, downloadable by the assessed company. The
log is a good artifact: it shows the method, the timings, and every place the system REFUSED to
draw a conclusion. It is also, unredacted, a disclosure of the operator's email, our internal
paths and our cost book. Both halves are tested here, and each is negative-tested.
"""
import importlib.util
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RL = os.path.join(ROOT, "hermes-skills", "shodan-assessment", "scripts", "run_log.py")

# The REAL sberautotech.ru run, 11 Aug 2026, trimmed but not otherwise altered.
RAW = """{"evt": "assess_start", "company": "sberautotech.ru", "ts": 1786479900.51, "user": "feranicus@s4biz.io", "service": "colt-web"}
[auto] ASN AS51115 holder 'HLL-AS HLL LLC' does NOT corroborate the seed brand 'sberautotech.ru' - treating it as PROVIDER space.
[warn] ASN discovery: every source failed (ripe-db, bgpview) - ASNs unknown, NOT 'none'
[group] sberautotech.ru: homepage unreachable - no structure discovery (fails closed)
[auto] dns probe: 3 live subdomain(s): mail.sberautotech.ru, sso.sberautotech.ru
[auto] OT/BMS named on the public internet (CRITICAL): hmi.sberautotech.ru
[auto] 4 name(s) resolve with no observable service - put to the operator as a question, NOT raised as a finding (absence of evidence is never a finding)
[auto] NO ATTRIBUTABLE ESTATE: every observed record belonged to a co-tenant or a provider. That is a finding, not a failure.
{"evt": "phase", "name": "recon", "status": "ok", "ms": 61372, "ts": 1786479961.89, "user": "feranicus@s4biz.io"}
{"evt": "qwen", "model": "deepseek-3.2", "status": "ok", "tokens_in": 3771, "tokens_out": 2679, "cost_usd": 0.00516, "user": "feranicus@s4biz.io"}
QA: Conclusions rest on passive OSINT only; internal state and software versions were not checked.
FP-AUDIT: auditor=llama-4-maverick vs deck-author=deepseek-3.2 -> verdict=clean
{"evt": "fp_audit", "auditor": "llama-4-maverick", "author": "deepseek-3.2", "verdict": "clean", "ts": 1786479987.48, "user": "feranicus@s4biz.io"}
{"evt": "assess_done", "company": "sberautotech.ru", "lang": "ru", "crit": 1, "high": 0, "med": 1, "low": 0, "decks": 3, "qwen_cost_usd": 0.00516, "ts": 1786479993.81, "user": "feranicus@s4biz.io"}
{"evt": "cost_snapshot", "ledger": "/var/log/colt/cost_ledger.sqlite", "lifetime_usd": 0.954448, "assessments_total": 193, "avg_usd": 0.004945, "tokens_in_total": 603189, "user": "feranicus@s4biz.io"}
OK /data/jobs/feranicus_s4biz.io/ddc87bfa0fdc497c993c370d754c1f24/sberautotech.ru_Shodan_Findings_RU.pptx
OK /data/jobs/feranicus_s4biz.io/ddc87bfa0fdc497c993c370d754c1f24/sberautotech.ru_GEOPOL_Animated_RU.html
"""


@pytest.fixture
def rl():
    spec = importlib.util.spec_from_file_location("run_log", RL)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture
def out(rl):
    return rl.build(RAW, "sberautotech.ru", "ru")


# ------------------------------------------------------------------ what must NEVER appear
def test_the_operator_is_not_in_it(out):
    """His email is on literally every structured line of the raw log."""
    assert "feranicus" not in out
    assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", out), "an email address survived redaction"


def test_no_internal_paths_or_job_ids(out):
    assert "/data/jobs" not in out
    assert "/var/log/colt" not in out
    assert "ddc87bfa0fdc497c993c370d754c1f24" not in out
    # the deliverables are still named, just without the path they live at
    assert "sberautotech.ru_Shodan_Findings_RU.pptx" in out


def test_the_cost_book_is_not_handed_over(out):
    """THE COMMERCIALLY DANGEROUS ONE.

    cost_snapshot carries lifetime spend, the total number of assessments ever run and the average
    per run. On this run that is 193 assessments at $0.0049. Giving the assessed company the exact
    AI cost of the report they are being invoiced for, plus the size of the whole book, is not a
    privacy problem. It is a negotiating position given away for free.
    """
    for leak in ("0.00516", "0.954448", "193", "0.004945", "603189", "cost", "lifetime",
                 "tokens_in", "assessments_total"):
        assert leak not in out, "the cost ledger leaked into the customer log: %r" % leak


def test_unknown_lines_are_dropped_not_passed_through(rl):
    """Fails safe. A log line a future engine invents must go missing, never leak."""
    o = rl.build(RAW + "\nINTERNAL: api_key=sk-secret123 operator_note=do-not-ship\n",
                 "x.ru", "ru")
    assert "sk-secret123" not in o and "do-not-ship" not in o


# ------------------------------------------------------------------ what must SURVIVE
def test_the_refusals_are_the_point(out):
    """The value of this artifact is the places the system declined to conclude."""
    for keep in ("does NOT corroborate", "NOT 'none'", "fails closed",
                 "absence of evidence is never a finding", "NO ATTRIBUTABLE ESTATE"):
        assert keep in out, "the log lost a refusal, which is what makes it worth reading: %r" % keep


def test_the_independent_audit_is_shown(out):
    """Two models, two vendors, and the customer can see the auditor was not the author."""
    assert "deepseek-3.2" in out and "llama-4-maverick" in out
    assert "clean" in out


def test_the_result_and_the_caveat_survive(out):
    assert "CRITICAL 1" in out and "MEDIUM 1" in out
    assert "passive OSINT" in out
    assert "sberautotech.ru" in out


def test_it_is_russian_when_the_run_was_russian(out, rl):
    assert "ЖУРНАЛ ОЦЕНКИ" in out and "ЧТО СИСТЕМА ОТКАЗАЛАСЬ УТВЕРЖДАТЬ" in out
    en = rl.build(RAW, "sberautotech.ru", "en")
    assert "ASSESSMENT RUN LOG" in en and "WHAT THE SYSTEM REFUSED TO CLAIM" in en


def test_it_never_raises(rl):
    """A broken log must not fail a completed assessment."""
    for junk in ("", None, "{not json", ["", None, 12345], "\x00\x01"):
        assert isinstance(rl.build(junk, "x", "ru"), str)


# ------------------------------------------------------------------ the delivery path
def test_only_the_generated_log_is_downloadable():
    """run.log itself carries the operator's email on every line."""
    src = open(os.path.join(ROOT, "webapp", "backend", "app", "main.py"), encoding="utf-8").read()
    body = src[src.index("def assess_deck("):]
    body = body[:body.index("\n@app.")] if "\n@app." in body else body
    assert '"_run_log_" in low' in body, (
        "a bare .txt is downloadable, which would expose run.log with the operator's email")
    assert 'low.endswith(".txt")' in body
    assert "text/plain" in src, "the log must be served as text, not as a binary attachment"


def test_the_log_is_collected_as_a_deliverable():
    src = open(os.path.join(ROOT, "webapp", "backend", "app", "main.py"), encoding="utf-8").read()
    assert '*_Run_Log_*.txt' in src, "the log never reaches History"
    assert 'glob("run.log")' not in src, "the RAW log must never be collected"

def test_the_allow_list_is_the_primary_protection(rl):
    """Documents WHICH layer is load-bearing, because it matters when changing the file.

    Three negative tests did not fail: removing the email regex, un-dropping cost_snapshot, and
    removing the path stripper all left the output clean. That is not weak testing, it is the
    architecture: only recognised events and line shapes are rendered at all, so the operator's
    email and the cost ledger never reach the renderer to be redacted. Removing the ALLOW-LIST
    does leak instantly, and that test does fail.
    So: the line to protect in this module is the final `continue`, not the regexes.
    """
    leaky = ('{"evt": "totally_new_event", "user": "feranicus@s4biz.io", "cost_usd": 0.99}\n'
             "INTERNAL some/path/feranicus_s4biz.io/secret\n")
    out = rl.build(RAW + leaky, "x.ru", "ru")
    assert "feranicus" not in out and "0.99" not in out, (
        "an unrecognised line reached the output; the allow-list is what stops that")

