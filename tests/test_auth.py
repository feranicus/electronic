import colt_auth as CA

def mk(tmp_path): return CA.Auth("test", str(tmp_path / "auth.json"))

def test_email_regex():
    assert CA.EMAIL_RE.match("jev.vainsteins@colt.net")
    assert CA.EMAIL_RE.match("anna-maria.schmidt@colt.net")
    assert not CA.EMAIL_RE.match("attacker@gmail.com")
    assert not CA.EMAIL_RE.match("noreply@colt.net")           # no name.surname
    assert not CA.EMAIL_RE.match("x.y@colt.net.evil.com")      # suffix attack

def test_factor1_ok(tmp_path):
    a = mk(tmp_path)
    st, _ = a.begin(1, "jev.vainsteins@colt.net", "test-secret-123")
    assert st == "authed" and a.is_authed(1)

def test_wrong_password_and_domain(tmp_path):
    a = mk(tmp_path)
    assert a.begin(2, "jev.vainsteins@colt.net", "WRONG")[0] == "denied"
    assert a.begin(3, "attacker@gmail.com", "test-secret-123")[0] == "denied"
    assert not a.is_authed(2) and not a.is_authed(3)

def test_lockout(tmp_path):
    a = mk(tmp_path)
    for _ in range(6): a.begin(9, "jev.vainsteins@colt.net", "WRONG")
    assert a.locked(9) > 0

def test_otp_2fa_flow(tmp_path, monkeypatch):
    a = mk(tmp_path)
    monkeypatch.setattr(CA, "REQUIRE_2FA", True)
    cap = {}
    monkeypatch.setattr(a, "_send_otp", lambda to, code: cap.update(code=code) or True)
    st, _ = a.begin(5, "jev.vainsteins@colt.net", "test-secret-123")
    assert st == "otp_sent" and not a.is_authed(5)     # password alone is NOT enough
    assert a.verify(5, "000000")[0] is False           # wrong code
    assert a.verify(5, cap["code"])[0] is True         # correct code
    assert a.is_authed(5)

def test_partner_allowlist():
    """Who may START auth. Locked in so a future refactor cannot silently lock a partner out —
    or silently widen a named partner into a whole trusted domain."""
    # named partners (individual addresses)
    assert CA.email_allowed("ud@objectale.ch")            # Objectale
    assert CA.email_allowed("r.helle@lancon.de")          # LANCON
    assert CA.email_allowed("R.Helle@LANCON.de")          # case-insensitive
    assert CA.email_allowed("  r.helle@lancon.de  ")      # tolerant of stray whitespace
    # the other two routes still work
    assert CA.email_allowed("anyone@s4biz.io")            # trusted DOMAIN
    assert CA.email_allowed("jev.vainsteins@colt.net")    # Colt AE pattern
    # and what must stay out
    assert not CA.email_allowed("someone@lancon.de")      # the DOMAIN is NOT trusted, only the person
    assert not CA.email_allowed("r.helle@lancon.de.evil.com")   # suffix attack
    assert not CA.email_allowed("attacker@gmail.com")
    assert not CA.email_allowed("")
