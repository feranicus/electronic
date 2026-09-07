"""The abuse pipeline must create consequence for attackers WITHOUT risking our own mail domain.

s4biz.io carries the OTP for cybergod and jobhuntwow. A degraded sending reputation is a
self-inflicted outage of the login path, which is why every gate here is arithmetic and why the
operator's earlier rule against mass-mailing abuse desks is respected rather than reversed.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from perseus import abuse as A          # noqa: E402


def _fresh():
    """A UNIQUE state file per test. The first version shared one, so record_sent() in an earlier
    test put an address inside the dedupe window and the dry-run test then measured the dedupe
    rather than the dry run. A test that depends on the order of its neighbours is not a test."""
    import tempfile
    A.STATE = os.path.join(tempfile.mkdtemp(), "abuse.json")
    return {}


def _actor(ip="203.0.113.7", days=3, holder="DIGITALOCEAN", total=900):
    d = {time.strftime("%Y-%m-%d", time.gmtime(time.time() - i * 86400)): 10 for i in range(days)}
    return {"ip": ip, "days": d, "holder": holder, "total": total,
            "abuse": ["abuse@example.net"], "first": time.time() - days * 86400,
            "last": time.time(), "routes": {"/wp-login.php": 400, "/.env": 200}}


def test_a_single_burst_is_not_reported():
    """One bad afternoon is noise. A reporter who files noise stops being read."""
    ok, why = A.eligible(_actor(days=1), {})
    assert not ok and "needs" in why


def test_a_repeat_offender_is_reported():
    ok, why = A.eligible(_actor(days=3), {})
    assert ok, why


def test_a_research_scanner_is_never_reported():
    """Censys and Shodan are not abuse. Reporting them discredits every other complaint we file."""
    for h in ("Censys, Inc.", "Shodan", "Internet-Census"):
        ok, why = A.eligible(_actor(holder=h), {})
        assert not ok and "research" in why, h


def test_a_24_is_reported_once_not_256_times():
    """One rented range is one actor. Per-address complaints are spam with our name on them."""
    st = _fresh()
    a1 = _actor(ip="203.0.113.7")
    assert A.eligible(a1, st)[0]
    st = A.record_sent(a1, st)
    ok, why = A.eligible(_actor(ip="203.0.113.200"), st)   # same /24, different address
    assert not ok and "already reported" in why


def test_the_daily_cap_protects_the_sending_reputation():
    """VOLUME is what gets a domain blocklisted, not content. This is the gate that keeps the
    OTP working."""
    st = {"per_day": {time.strftime("%Y-%m-%d", time.gmtime()): A.MAX_PER_DAY}}
    ok, why = A.eligible(_actor(ip="198.51.100.9"), st)
    assert not ok and "cap" in why


def test_a_complaint_carries_evidence_not_just_an_accusation():
    c = A.complaint(_actor())
    for must in ("203.0.113.7", "UTC", "Requests per day", "/wp-login.php", "T1595",
                 "have not scanned", "feranicus@s4biz.io"):
        assert must in c, must


def test_a_dry_run_sends_nothing_and_records_nothing():
    _fresh()
    st_before = A._load()
    out = A.run([_actor()], dry_run=True)
    assert out["sent"] and out["sent"][0].get("dry_run") is True
    assert A._load() == st_before, "a dry run must not consume the daily budget"


def test_every_skip_says_why():
    _fresh()
    """A silent skip teaches nothing. The skip reasons are the useful half of the daily report."""
    out = A.run([_actor(days=1), _actor(ip="1.2.3.4", holder="Censys")], dry_run=True)
    assert len(out["skipped"]) == 2
    assert all(s.get("why") for s in out["skipped"])


def test_a_failed_send_is_not_recorded_as_sent():
    """Otherwise the dedupe window silently swallows an actor nobody was ever told about."""
    import perseus.abuse as M
    src = open(M.__file__, encoding="utf-8").read()
    i = src.index("sent = notify.email(")
    seg = src[i:i + 500]
    assert "if sent:" in seg and "NOT recorded as sent" in seg


if __name__ == "__main__":
    import traceback
    fails = 0
    for n, f in sorted(globals().items()):
        if n.startswith("test_") and callable(f):
            try:
                f(); print("  ok    %s" % n)
            except Exception:
                fails += 1; print("  FAIL  %s\n%s" % (n, traceback.format_exc()[-400:]))
    print("%d failed" % fails)
    raise SystemExit(1 if fails else 0)
