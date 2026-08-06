"""Per-user assessment quota + the two whitelisted evaluation accounts (2026-08).

Two things are asserted together on purpose: an allow-list entry without a quota is an open tap,
and a quota on an identity that cannot log in is dead code. They are one feature.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import colt_auth


def test_the_two_new_accounts_can_log_in():
    assert colt_auth.email_allowed("mr.nvisinc@gmail.com")
    assert colt_auth.email_allowed("mordechai.rabinovich@rbc.com")


def test_each_is_capped_at_five():
    assert colt_auth.quota_for("mr.nvisinc@gmail.com") == 5
    assert colt_auth.quota_for("mordechai.rabinovich@rbc.com") == 5
    # case and whitespace must not be a way around the cap
    assert colt_auth.quota_for("  MR.NVISINC@Gmail.com ") == 5


def test_rbc_domain_is_not_trusted_wholesale():
    """Only the named person was asked for. Trusting rbc.com would admit ~90,000 people."""
    assert not colt_auth.email_allowed("someone.else@rbc.com")
    assert not colt_auth.email_allowed("attacker@gmail.com")


def test_existing_users_are_unlimited():
    """Absent from the map = no cap. Every current user must be unaffected."""
    assert colt_auth.quota_for("feranicus@s4biz.io") is None
    assert colt_auth.quota_for("jevgenijs.vainsteins@colt.net") is None
    assert colt_auth.quota_for("") is None


def test_quota_is_overridable_without_a_code_change():
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "colt_auth.py"), encoding="utf-8").read()
    assert "USER_QUOTAS" in src and 'os.environ.get("USER_QUOTAS"' in src


def test_both_front_doors_enforce_it():
    """The web app counts its jobs table; the bot counts the shared cost ledger. If only one
    enforced, the other would simply be the way around the cap."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    main = open(os.path.join(root, "webapp/backend/app/main.py"), encoding="utf-8").read()
    assert main.count("_enforce_quota(email)") >= 2, "assess AND compliance must both check"
    assert "quota_exceeded" in main
    bot = open(os.path.join(root, "assess-bot/bot.py"), encoding="utf-8").read()
    assert "quota_for" in bot and "count_for_user" in bot
    store = open(os.path.join(root, "webapp/backend/app/store.py"), encoding="utf-8").read()
    assert "def count_jobs" in store
