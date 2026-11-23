"""test_dealreg.py — the four rules of deal registration that are NOT defaults.

The numbers in `dealreg.py` (90 days, +90, cap 270, five-day SLA, no minimum) are market-standard
DEFAULTS and they are meant to be replaced the day the business writes its own programme guide.
These four are not. Each is either a legal position or a doctrine this estate has already paid for
somewhere else, and each is enforced here so that changing it requires arguing with a test rather
than editing a line.

 1. A REGISTRATION IS AN INCENTIVE, NEVER A PROHIBITION. The second partner loses the discount,
    the protection and the deal support. They never lose the right to quote, to be supplied or to
    be priced. Operating it the other way turns a supplier's pricing decision into customer
    allocation, and blocking a reseller from answering an unsolicited enquiry restricts a PASSIVE
    sale — hardcore under Art. 4 VBER, which voids the exemption for the whole agreement.
 2. OPPORTUNITY-SCOPED, NEVER ACCOUNT-SCOPED. A second partner may hold a different opportunity at
    the same customer. Account-scoped lockout manufactures a false duplicate every time a customer
    runs two projects, and it is the shape that most resembles allocation.
 3. DETERMINISTIC CODE DECIDES; THE MODELS ARE A SIGNAL. The panel may flag and explain. It may
    not approve, reject or mark a duplicate. This is the third place in the estate that has needed
    the rule (engine FP auditor, perseus/vet.py), and the boundary erodes precisely because the
    model is right often enough that wiring it to the verdict feels like an improvement.
 4. A DUPLICATE IS A FORK, NOT A FAILURE. "Same customer, different deal, not enough detail to
    tell them apart" goes to `returned`, which the partner can fix, never to `rejected`.
"""
import importlib
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "webapp", "backend", "app")
if APP not in sys.path:
    sys.path.insert(0, APP)


@pytest.fixture
def dr(tmp_path, monkeypatch):
    """A real sqlite store per test. Not a mock: the duplicate check reads the table, and a fixture
    that does not reproduce the condition under test is a test of the fixture (class 12)."""
    monkeypatch.setenv("DEALREG_DB", str(tmp_path / "dealreg.sqlite"))
    import dealreg
    importlib.reload(dealreg)
    return dealreg


def _reg(dr, who, **kw):
    f = dict(company="Müller GmbH", domain="mueller.de", country="DE", product="herkos",
             description="x" * 60, close_date="2027-02-01", value_eur=90000)
    f.update(kw)
    return dr.submit(who, **f)


# --------------------------------------------------------------------- 1. incentive, not ban

def test_the_second_partner_is_told_they_may_still_quote(dr):
    """THE SENTENCE THAT KEEPS THIS LAWFUL. A partner who reads the refusal and concludes they are
    barred from the customer would be obeying a restriction we never imposed and may not impose."""
    a = _reg(dr, "anna@reseller-a.de")
    dr.decide(a, "approved", by="s4biz")
    b = _reg(dr, "bob@reseller-b.de", description="short", close_date="")
    msg = dr.get(b)["reason"].lower()
    assert "free to quote" in msg, "the refusal does not tell the second partner they may quote"
    assert "supply" in msg and "price" in msg, (
        "it does not say they will still be supplied and priced — which is the part that "
        "distinguishes an incentive from an allocation:\n" + msg)
    assert dr.get(b)["state"] == "duplicate"


@pytest.mark.parametrize("banned", ["may not quote", "must not approach", "exclusive to",
                                    "blocked from", "will not be supplied", "refuse to quote"])
def test_no_refusal_wording_anywhere_reads_as_a_prohibition(dr, banned):
    """Asserted on the SOURCE, not just on one message, because the wording that does the damage
    is whichever string a future change adds — not the one this test happened to build."""
    src = open(os.path.join(APP, "dealreg.py"), encoding="utf-8").read().lower()
    body = "\n".join(l for l in src.split("\n") if not l.strip().startswith("#"))
    assert banned not in body, (
        "%r appears in dealreg.py. Losing a registration costs the discount and the protection, "
        "never the right to quote or be supplied." % banned)


def test_losing_protection_changes_nothing_a_partner_can_be_refused_on(dr):
    """The refusal object carries exactly one power: naming who holds protection. If it ever grows
    a field that gates supply, pricing or quoting, this fails."""
    a = _reg(dr, "anna@reseller-a.de")
    dr.decide(a, "approved", by="s4biz")
    out = dr.refused_protection({"id": a, "evidence": []})
    assert set(out) == {"protected_by", "evidence", "message"}, (
        "the refusal grew a field beyond naming the holder and explaining: %s" % sorted(out))


# --------------------------------------------------------------------- 2. opportunity-scoped

def test_a_different_product_line_at_the_same_customer_is_not_a_duplicate(dr):
    """Zscaler states it hardest: granted by opportunity, not by account. A customer buying Herkos
    and buying Perseus is two deals, and the first partner must not hold the second hostage."""
    a = _reg(dr, "anna@reseller-a.de", product="herkos")
    dr.decide(a, "approved", by="s4biz")
    c = _reg(dr, "cara@reseller-c.de", product="perseus")
    assert dr.get(c)["state"] == "submitted", (
        "a different product line was treated as a duplicate — that is account-scoped lockout")


def test_an_expired_registration_protects_nothing(dr):
    a = _reg(dr, "anna@reseller-a.de")
    dr.decide(a, "approved", by="s4biz")
    import time
    rows = dr.visible_to("s4biz@s4biz.io", {"dealreg.view.all"})
    old = [dict(r, expires_at=time.time() - 10) for r in rows]
    assert dr.duplicate_of({"domain": "mueller.de", "country": "DE", "product": "herkos"},
                           old) is None, "expired protection still blocked a new registration"


def test_only_an_approved_registration_protects(dr):
    """A merely SUBMITTED registration must not block anyone: otherwise the race is won by typing
    first rather than by qualifying first, and every rejected filing leaves a landmine."""
    _reg(dr, "anna@reseller-a.de")                       # submitted, never approved
    b = _reg(dr, "bob@reseller-b.de", description="short", close_date="")
    assert dr.get(b)["state"] != "duplicate"


def test_an_unparseable_domain_never_matches_anything(dr):
    """ABSENCE OF EVIDENCE IS NEVER A FINDING. Two blank keys matching each other would hand the
    first partner with a broken domain protection over every other broken one."""
    assert dr.duplicate_of({"domain": "", "country": "DE", "product": "herkos"},
                           [{"id": "x", "state": "approved", "domain": "", "country": "DE",
                             "product": "herkos", "expires_at": 9e9}]) is None


def test_a_public_suffix_is_not_one_customer(dr):
    """`budget.gov.ru` must stay whole. "The last two labels" would make it `gov.ru`, so the first
    ministry to register would hold protection against the entire government — the engine already
    paid for this one."""
    assert dr._apex("https://www.budget.gov.ru/x") == "budget.gov.ru"
    assert dr._apex("nalog.gov.ru") == "nalog.gov.ru"
    assert dr._apex("shop.acme.de") == "acme.de"


# --------------------------------------------------------------------- 3. code decides

def test_the_panel_cannot_change_any_state(dr):
    """THE BOUNDARY THAT ERODES. `apply()` is the only path from the panel to the database, and it
    writes ONE column that no decision reads."""
    import dealreg_panel
    a = _reg(dr, "anna@reseller-a.de")
    before = dr.get(a)["state"]
    dealreg_panel.apply(a, [{"model": "m", "same": True, "confidence": "high", "why": "w"}],
                        {"flag": True, "reason": "r"}, db=dr.db_path())
    after = dr.get(a)
    assert after["state"] == before, "the panel moved a registration"
    assert after["panel"] is not None, "the panel's answer was not recorded at all"
    assert not after["dup_of"], "the panel marked a duplicate"


def test_no_decision_path_reads_the_panel_column(dr):
    """Behaviour and wiring (class 9). The docstring claims nothing reads `panel`; this measures
    it, because that claim is exactly what a future 'small improvement' would quietly break."""
    src = open(os.path.join(APP, "dealreg.py"), encoding="utf-8").read()
    body = "\n".join(l for l in src.split("\n") if not l.strip().startswith("#"))
    for fn in ("def duplicate_of", "def decide", "def distinguishable"):
        seg = body[body.index(fn):]
        seg = seg[:seg.index("\ndef ", 1)] if "\ndef " in seg[1:] else seg
        assert '"panel"' not in seg and "'panel'" not in seg and "panel[" not in seg, (
            "%s consults the model panel — code decides, models propose" % fn)


def test_the_panel_needs_two_models_to_raise_a_flag():
    """Agreement is required to RAISE a flag, never to clear one. One model's opinion wearing a
    panel's clothes is the failure this asymmetry exists to stop."""
    import dealreg_panel as p
    one = [{"model": "a", "same": True, "confidence": "high", "why": "w"},
           {"model": "b", "same": None, "confidence": "low", "why": ""},
           {"model": "c", "same": None, "error": "boom"},
           {"model": "d", "same": None, "confidence": "low", "why": ""}]
    assert p.verdict(one, deterministic_hit=False)["flag"] is False
    two = list(one)
    two[1] = {"model": "b", "same": True, "confidence": "medium", "why": "w2"}
    assert p.verdict(two, deterministic_hit=False)["flag"] is True


def test_a_high_confidence_disagreement_blocks_the_flag():
    import dealreg_panel as p
    ans = [{"model": "a", "same": True, "confidence": "high", "why": "w"},
           {"model": "b", "same": True, "confidence": "low", "why": "w"},
           {"model": "c", "same": False, "confidence": "high", "why": "different budget holder"}]
    assert p.verdict(ans, deterministic_hit=False)["flag"] is False


def test_a_crashed_model_is_named_not_silently_dropped():
    """A panel that silently shrinks is the two-model quorum this estate has already shipped once.
    'Three of four answered' and 'four of four answered' are different evidence."""
    import dealreg_panel as p
    ans = p.ask({"company": "A"}, {"company": "B"}, chain=["m1", "m2"],
                call=lambda m, _p: (_ for _ in ()).throw(RuntimeError("gateway down")))
    assert len(ans) == 2 and all(a.get("error") for a in ans), ans
    assert p.verdict(ans, deterministic_hit=False)["answered"] == 0


def test_the_panel_is_not_sent_the_commercially_sensitive_fields():
    """Data minimisation, and it is not only GDPR tidiness: the owner, the value and the contact
    are not evidence for 'is this the same opportunity', and a prompt is a place data goes."""
    import dealreg_panel as p
    slim = p._slim({"company": "A", "domain": "a.de", "owner": "bob@reseller-b.de",
                    "value_eur": 250000, "contact": "cfo@a.de", "competitor": "X",
                    "description": "d", "country": "DE", "product": "herkos"})
    for leaked in ("owner", "value_eur", "contact"):
        assert leaked not in slim, "the panel prompt carries %r" % leaked


# --------------------------------------------------------------------- 4. a fork, not a failure

def test_same_customer_but_well_described_goes_to_review_not_duplicate(dr):
    """Nutanix's second denial code. The burden is on the partner to make it distinguishable, and
    we say so — rather than silently rejecting it as a duplicate."""
    a = _reg(dr, "anna@reseller-a.de")
    dr.decide(a, "approved", by="s4biz")
    d2 = _reg(dr, "dan@reseller-d.de", description="z" * 60, close_date="2028-01-01")
    assert dr.get(d2)["state"] == "review", "a describable second opportunity was auto-duplicated"


def test_returned_is_fixable_and_rejected_is_terminal(dr):
    a = _reg(dr, "anna@reseller-a.de")
    dr.decide(a, "returned", by="s4biz", reason="which business unit?")
    dr.decide(a, "submitted", by="anna@reseller-a.de")       # the partner fixes it
    assert dr.get(a)["state"] == "submitted"
    dr.decide(a, "rejected", by="s4biz", reason="house account")
    with pytest.raises(ValueError):
        dr.decide(a, "submitted", by="anna@reseller-a.de")


def test_an_impossible_transition_is_refused_by_name(dr):
    a = _reg(dr, "anna@reseller-a.de")
    dr.decide(a, "approved", by="s4biz")
    with pytest.raises(ValueError) as e:
        dr.decide(a, "submitted", by="x")
    assert "cannot go from" in str(e.value) and "allowed" in str(e.value), str(e.value)


# --------------------------------------------------------------------- RBAC, the operator's ask

def test_every_s4biz_role_sees_every_registration_and_no_partner_role_does():
    """The operator's requirement, and the reason for the split: adjudicating "who got here first"
    is impossible from a partial view, while handing a reseller the view would make US the channel
    through which one reseller reads a rival's pipeline."""
    sys.path.insert(0, ROOT)
    import roles
    for r in ("admin", "s4biz_power"):
        assert "dealreg.view.all" in roles.perms_of(r), "%s cannot see all registrations" % r
        assert "dealreg.decide" in roles.perms_of(r)
    for r in ("reseller_admin", "company_admin", "sales_rep"):
        p = roles.perms_of(r)
        assert "dealreg.view.all" not in p, "%s can read every rival's pipeline" % r
        assert "dealreg.decide" not in p, "%s can approve its own registration" % r
        assert "dealreg.submit" in p and "dealreg.view.own" in p


def test_a_partner_sees_only_their_own(dr):
    a = _reg(dr, "anna@reseller-a.de")
    dr.decide(a, "approved", by="s4biz")
    b = _reg(dr, "bob@reseller-b.de", product="perseus")
    assert [r["id"] for r in dr.visible_to("bob@reseller-b.de", {"dealreg.view.own"})] == [b]
    assert len(dr.visible_to("s4biz@s4biz.io", {"dealreg.view.all"})) == 2


# --------------------------------------------------------------------- the clock

def test_protection_starts_at_approval_not_submission(dr):
    """Dell documents its own drift between the two; the current terms run from approval. Whichever
    is chosen has to be stated on the form, which is why config() reports it."""
    import sqlite3
    import time
    a = _reg(dr, "anna@reseller-a.de")
    assert dr.get(a)["expires_at"] is None, "the clock started before anyone approved anything"
    # AGE THE SUBMISSION. The first version approved a registration created milliseconds earlier,
    # so `now` and `created_at` were the same number to within the tolerance and the test could
    # not tell the two clocks apart — it passed cleanly against a mutation that ran the window
    # from submission. A fixture that does not reproduce the condition under test is a test of
    # the fixture (class 12). Thirty days apart, the two answers differ by thirty days.
    c = sqlite3.connect(dr.db_path())
    c.execute("UPDATE regs SET created_at=? WHERE id=?", (time.time() - 30 * 86400, a))
    c.commit()
    c.close()
    t = time.time()
    dr.decide(a, "approved", by="s4biz")
    got = dr.get(a)["expires_at"]
    assert abs(got - (t + dr.PROTECTION_DAYS * 86400)) < 5, (
        "protection expires %.1f days from approval; it must be %d — a window measured from "
        "SUBMISSION silently shortens every registration by however long we took to decide"
        % ((got - t) / 86400.0, dr.PROTECTION_DAYS))
    assert dr.config()["clock_starts"] == "approval"


def test_extension_is_capped_and_the_refusal_says_what_to_do(dr):
    a = _reg(dr, "anna@reseller-a.de")
    dr.decide(a, "approved", by="s4biz")
    dr.extend(a, by="s4biz")
    dr.extend(a, by="s4biz")
    with pytest.raises(ValueError) as e:
        dr.extend(a, by="s4biz")
    assert "cap is" in str(e.value) and "Re-register" in str(e.value), str(e.value)


def test_the_sweep_expires_and_reminds(dr):
    import time
    a = _reg(dr, "anna@reseller-a.de")
    dr.decide(a, "approved", by="s4biz")
    assert dr.sweep()["expired"] == []
    far = time.time() + (dr.PROTECTION_DAYS + 1) * 86400
    assert dr.sweep(now=far)["expired"] == [a]
    assert dr.get(a)["state"] == "expired"
    with pytest.raises(ValueError):
        dr.extend(a, by="s4biz")


def test_the_terms_are_one_home_and_report_their_provenance(dr):
    """The form, the partner pack and the deck all read config(). A term changed in one place and
    stale in another is class 32, and a programme term is exactly the kind of number that gets
    retyped into a UI string."""
    c = dr.config()
    for k in ("protection_days", "extension_days", "max_total_days", "sla_days", "clock_starts",
              "scope", "second_partner"):
        assert k in c, "config() does not report %s" % k
    assert c["scope"] == "opportunity"
    assert "quote" in c["second_partner"], (
        "the API does not carry the may-still-quote fact, so a UI could omit it")
