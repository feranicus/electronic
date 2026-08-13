"""The digest exists to see what the DETECTOR CANNOT, so its own blind spots are the whole test.

The panel that reviews the shield's decisions can only ever look at traffic the classifier already
understands. A scanner using a technique our corpus does not name scores nothing, is never
blocked, never becomes evidence, and is therefore invisible precisely because it is new. That is a
blind spot with a feedback loop. attack_digest.unknowns() is the way out, and it has exactly one
way to be wrong that matters: accusing a real person.

MEASURED, NOT IMAGINED. On the real event log on 10 Aug two genuine visitors produced 439 and 362
404s each, entirely on our own stale routes. A 404 COUNT would have flagged both. The first
version of unknowns() did flag them, because our own routes are not probe shapes either and so
survived the "unrecognised" filter. Both directions are pinned below.

Every assertion is negative-tested.
"""
import json
import os
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "webapp", "backend"))

from app import attack_digest as AD  # noqa: E402

NOW = time.time()

# A real person: hundreds of 404s, every one on a route of ours.
VISITOR = ["/app", "/", "/api/me", "/demo", "/contact", "/privacy", "/partners",
           "/media/cassandra.mp4", "/assets/index-a1b2.js", "/sw.js"]
# A scanner the corpus already names.
KNOWN = ["/wp-login.php", "/.env", "/phpmyadmin/", "/.git/config",
         "/vendor/phpunit/phpunit/eval-stdin.php", "/backup.sql"]
# A technique the corpus does NOT name: LLM gateway discovery, the class TeamPCP went after.
NOVEL = ["/v1/chat/completions", "/v1/models", "/openai/v1/models", "/anthropic/v1/messages",
         "/gateway/v1/completions", "/inference/v1/chat"]


def _log(rows):
    fd, p = tempfile.mkstemp(suffix=".log")
    with os.fdopen(fd, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    return p


def _ev(ip, path, status=404, ua="curl/8", cc="DE", day=0, blocked=False, bot=True):
    return {"evt": "http", "ip": ip, "path": path, "status": status, "ua": ua, "country": cc,
            "ts": NOW - day * 86400, "blocked": blocked, "bot": bot}


def _corpus():
    rows = []
    for p in VISITOR:
        rows += [_ev("198.51.100.7", p, ua="Mozilla/5.0", bot=False) for _ in range(45)]
    for d in (0, 1, 2):
        rows += [_ev("203.0.113.9", p, day=d, blocked=True, cc="NL") for p in KNOWN]
    for p in NOVEL:
        rows.append(_ev("192.0.2.55", p, ua="python-requests/2.31", cc="SG"))
        rows.append(_ev("192.0.2.55", p, ua="Mozilla/5.0 (iPhone)", cc="SG"))
    return _log(rows)


# ---------------------------------------------------------------------------------------------
# 1. THE DISCRIMINATION. Both directions, because either one alone is easy to satisfy.
# ---------------------------------------------------------------------------------------------

def test_a_real_visitor_with_hundreds_of_404s_is_never_flagged():
    """450 404s, all on our own routes. This is the exact shape of the two real visitors in the
    10 Aug log, and it is the failure that would matter most."""
    flagged = {r["ip"] for r in AD.unknowns(2, _corpus())["sources"]}
    assert "198.51.100.7" not in flagged, (
        "a real visitor missing our own stale routes was reported as an attacker")


def test_a_scanner_the_corpus_already_names_is_not_reported_as_new():
    """It is not NEW, so it belongs to the shield and the panel, not to this digest. Reporting it
    here would bury the one line that matters under traffic we already handle."""
    flagged = {r["ip"] for r in AD.unknowns(2, _corpus())["sources"]}
    assert "203.0.113.9" not in flagged


def test_a_genuinely_novel_technique_is_surfaced():
    u = AD.unknowns(2, _corpus())
    assert "192.0.2.55" in {r["ip"] for r in u["sources"]}, (
        "a scanner using a technique the corpus cannot name was NOT surfaced, which is the one "
        "job this module has")
    assert any("/v1/chat/completions" in p for p in u["paths"])


def test_a_couple_of_odd_404s_is_not_a_scanner():
    """VARIETY IS THE DISCRIMINATOR, AND THIS IS THE TEST THAT PROVES IT.

    The first version of this file tried to prove the floor by removing it and watching a real
    visitor get flagged - and nothing happened, because _ours() was ALSO protecting that visitor.
    A negative test that passes because of a second guard measures the second guard. So this
    fixture is built so the floor is the ONLY thing standing between the source and a report:
    two paths, neither ours, neither a known probe shape. That is a stale inbound link or a
    misconfigured integration, which is a support question and not an attack.
    """
    rows = []
    for p in ("/old-pricing-page", "/partners/legacy-brochure"):
        rows += [_ev("203.0.113.200", p, ua="Mozilla/5.0", bot=False) for _ in range(30)]
    u = AD.unknowns(2, _log(rows))
    assert "203.0.113.200" not in {r["ip"] for r in u["sources"]}, (
        "two odd paths, repeated, were reported as a new scanning technique; volume is not "
        "variety and a person hitting one dead link 30 times is still a person")


def test_user_agent_rotation_is_recorded():
    """Several browser identities from one source in seconds is the signal an attacker cannot
    remove by trying harder: the evasion IS the evidence."""
    row = [r for r in AD.unknowns(2, _corpus())["sources"] if r["ip"] == "192.0.2.55"][0]
    assert row["uas"] >= 2


def test_our_own_routes_are_read_from_the_app_not_retyped():
    """Two lists of our routes would drift, and a new page would become an anomaly for one and a
    route for the other."""
    s = open(os.path.join(ROOT, "webapp", "backend", "app", "attack_digest.py"),
             encoding="utf-8").read()
    assert "_APP_ROUTES" in s, "the digest keeps its own private idea of what our routes are"


# ---------------------------------------------------------------------------------------------
# 2. THE MODELS PROPOSE, THEY NEVER INSTALL. A model-authored regex on the blocking path could
#    take the site off the internet for real people.
# ---------------------------------------------------------------------------------------------

def test_a_proposal_that_matches_our_own_site_is_refused():
    keep, refused = AD.vet([
        {"name": "kills_the_app", "pattern": "/app"},
        {"name": "kills_the_api", "pattern": "^/api/"},
        {"name": "kills_home", "pattern": "^/$"},
        {"name": "kills_every_script", "pattern": r"\.js$"},
        {"name": "greedy", "pattern": ".*"},
        {"name": "fine", "pattern": "/litellm/config"},
    ])
    assert [p["name"] for p in keep] == ["fine"]
    assert len(refused) == 5
    for p in refused:
        assert p["refused"], "a refusal with no reason is not reviewable"


def test_an_invalid_regex_is_refused_rather_than_raising():
    keep, refused = AD.vet([{"name": "broken", "pattern": "/(unclosed"}])
    assert not keep and "not a valid regex" in refused[0]["refused"]


def test_nothing_in_this_module_can_install_a_pattern():
    """The standing rule: code decides, models advise. A proposal reaches a review file and the
    operator's Telegram, and only a human tap can promote it - and then to DETECTION, not to an
    automatic block."""
    s = open(os.path.join(ROOT, "webapp", "backend", "app", "attack_digest.py"),
             encoding="utf-8").read()
    body = "\n".join(ln for ln in s.splitlines() if not ln.strip().startswith("#"))
    for forbidden in ("EXTRA_PROBE_PATHS.add", "shield.block", "_blocked[", "BLOCK_NETS.add"):
        assert forbidden not in body, (
            "attack_digest reaches into the enforcement path (%s); a model-authored pattern "
            "could then deny real visitors with no human in the loop" % forbidden)


def test_two_vendors_agreeing_outranks_one():
    c = AD.consensus([
        {"model": "deepseek-3.2", "proposals": [{"name": "a", "pattern": "/litellm"}]},
        {"model": "kimi-k2.6", "proposals": [{"name": "b", "pattern": "/litellm"}]},
        {"model": "gemma-4-31B-it", "proposals": [{"name": "c", "pattern": "/solo"}]},
    ])
    assert c[0]["pattern"] == "/litellm" and c[0]["agreement"] == 2
    assert c[-1]["agreement"] == 1


# ---------------------------------------------------------------------------------------------
# 3. THE VISUALISATION AND DELIVERY
# ---------------------------------------------------------------------------------------------

def test_the_series_has_one_entry_per_day_including_quiet_ones():
    """A missing day is not a zero day: a gap in the chart reads as an outage in the logging."""
    s = AD.per_day(14, _corpus())["series"]
    assert len(s) == 14
    assert all(set(r) >= {"day", "attacks", "blocked", "sources"} for r in s)
    assert [r["day"] for r in s] == sorted(r["day"] for r in s), "days are out of order"


def test_the_digest_reads_the_shield_vocabulary_not_its_own():
    """One vocabulary for the detector, the public siege feed and this digest, or the three
    disagree about what an attack was."""
    classes = AD.per_day(5, _corpus())["classes"]
    from app import shield
    known = {n for n, _ in shield.CLASSES} | {"other"}
    assert classes and set(classes) <= known


def test_the_report_states_when_there_is_nothing_new():
    """Silence must be legible. "no unknowns" and "the check did not run" have to look different,
    or a broken digest reads as a quiet day."""
    txt = AD.render_text(AD.per_day(5, _log([])), {"sources": [], "paths": []})
    assert "none" in txt.lower() and "NEW OR UNRECOGNISED" in txt


def test_delivery_uses_the_gmail_api_and_a_plain_telegram_message():
    """SMTP is blocked outbound on this droplet, and an attacker controls the path text in this
    body - so Markdown would let a stray _ or * make Telegram reject the whole message."""
    s = open(os.path.join(ROOT, "webapp", "backend", "app", "attack_digest.py"),
             encoding="utf-8").read()
    assert "smtplib" not in s, "SMTP is blocked on this droplet; mail goes via the Gmail API"
    assert "markdown=" not in s, (
        "notify.telegram(text, reply_markup=None) has no markdown parameter, and an "
        "attacker-controlled path would break the message anyway")


def test_the_digest_is_actually_scheduled():
    """A correct module nobody calls is not a control. This is the ruff-gate lesson: a check that
    cannot execute is not a check."""
    s = open(os.path.join(ROOT, "webapp", "backend", "app", "main.py"), encoding="utf-8").read()
    assert "_digest_loop" in s and "create_task(_digest_loop())" in s, (
        "attack_digest is never scheduled, so the daily report would never be sent")
