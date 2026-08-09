"""test_passive_checks.py — the ns03.ru feature set, replayed against that engagement's real data.

Wired into ship.py and BLOCKING. Everything asserted here is derived from the operator's own run
against ns03.ru, so a regression is measured against ground truth rather than against a fixture I
invented to agree with my code.

THE LINE THIS FILE POLICES. Every check below is PASSIVE: public DNS, public certificate logs, or a
banner a scan engine already stored. Not one of them sends a packet to the assessed organisation.
The active tier (active_probe.py) is asserted to REFUSE unless an authorisation reference has been
recorded, because that is the difference between lawful and unlawful in every jurisdiction we
operate in, and because it is what the public site, the Terms of Use and the signed legal pack say.
"""
import datetime
import importlib
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.modules.setdefault("shodan", types.ModuleType("shodan"))

import active_probe  # noqa: E402
import cert_intel  # noqa: E402
import email_auth  # noqa: E402
import naming  # noqa: E402

FAILED = []


def check(cond, label):
    print(("  PASS  " if cond else "  FAIL  ") + label)
    if not cond:
        FAILED.append(label)


# ---------------------------------------------------------------- ns03.ru ground truth ----------
GS = {"friendly_name": "GlobalSign"}
LE = {"friendly_name": "Let's Encrypt"}


def _iss(names, nb, na, issuer=LE, revoked=False):
    return {"dns_names": names, "not_before": nb + "T00:00:00Z", "not_after": na + "T00:00:00Z",
            "issuer": issuer, "revoked": revoked}


NS03_CT = [
    _iss(["autodiscover.ns03.ru", "mail.ns03.ru", "ns03.ru", "srv-kap-gt.ns03.ru"],
         "2025-12-05", "2027-01-06", GS),
    _iss(["ventil2.nzn.ns03.ru"], "2026-05-25", "2026-08-23"),
    _iss(["iiko.nzn.ns03.ru"], "2026-06-03", "2026-09-01", LE, True),      # REVOKED
    _iss(["ing.nzn.ns03.ru"], "2026-06-09", "2026-09-07"),
    _iss(["nextcloud.ns03.ru"], "2026-06-11", "2026-09-09"),
    _iss(["ventil.nzn.ns03.ru"], "2026-06-17", "2026-09-15"),
    _iss(["oo.ns03.ru"], "2026-06-20", "2026-09-18", LE, True),            # REVOKED
    _iss(["ventil.nzn.ns03.ru"], "2026-06-26", "2026-09-24"),
    _iss(["nextcloud.ns03.ru"], "2026-07-05", "2026-10-03"),
    _iss(["ventil2.nzn.ns03.ru"], "2026-07-24", "2026-10-22"),
    _iss(["ing.nzn.ns03.ru"], "2026-08-08", "2026-11-06"),
]
NS03_LIVE = {"autodiscover.ns03.ru", "mail.ns03.ru", "ns03.ru", "srv-kap-gt.ns03.ru",
             "ventil2.nzn.ns03.ru", "iiko.nzn.ns03.ru", "ing.nzn.ns03.ru", "nextcloud.ns03.ru",
             "ventil.nzn.ns03.ru", "oo.ns03.ru", "vpn.ns03.ru", "www.ns03.ru"}
NOW = datetime.datetime(2026, 8, 9)


def test_email_auth():
    print("\n" + "=" * 78)
    print("[1] EMAIL AUTHENTICATION — the asset every customer sees, that the engine ignored")

    # ns03.ru's REAL apex TXT records. Good SPF, and no DMARC at all.
    ns03 = {"ns03.ru": ["google-site-verification=kSq5eJu4XHWmW3z3K02Q_fiwO3EqiHPJURBkKkakdwA",
                        "v=spf1 ip4:80.246.245.158 ip4:213.170.88.162 a mx -all"]}
    r = email_auth.assess("ns03.ru", txt_of=lambda n: ns03.get(n, []))
    ids = [i["id"] for i in r["issues"]]
    check("dmarc_missing" in ids, "ns03.ru: no DMARC is caught (the domain can be forged today)")
    check(r["spf"]["policy"] == "hardfail", "ns03.ru: its SPF is correctly read as a hard fail")
    check("spf_missing" not in ids and "spf_no_enforcement" not in ids,
          "a GOOD SPF record raises no SPF finding (no false positive)")

    # RFC 7208 §4.6.4 lookup counting, which decides whether SPF evaluates at all.
    check(email_auth._spf_lookups("v=spf1 ip4:1.2.3.4 a mx -all") == 2,
          "bare `a` and `mx` each cost a lookup (matching 'a:' scored this record ZERO)")
    check(email_auth._spf_lookups("v=spf1 -all") == 0, "an ip4-only record costs no lookups")
    many = "v=spf1 " + " ".join("include:s%d.x.de" % i for i in range(11)) + " -all"
    check("spf_too_many_lookups" in
          [i["id"] for i in email_auth.assess("x.de", txt_of=lambda n: [many] if n == "x.de" else []
                                              )["issues"]],
          "11 lookups exceeds the RFC cap, so SPF silently stops evaluating -- caught")

    # FAIL CLOSED. A lookup that could not be made is never a finding.
    check(not email_auth.assess("x.de", txt_of=lambda n: None)["issues"],
          "DNS lookup FAILED -> no findings at all (absence of evidence is never a finding)")

    # DKIM cannot be proven absent: a selector name is arbitrary and cannot be enumerated.
    ctx = " ".join(email_auth.assess("x.de", txt_of=lambda n: [])["context"])
    check("NOT evidence of absence" in ctx,
          "no DKIM found is reported as NOT DETERMINABLE, never as a missing control")

    # A clean domain must produce nothing.
    clean = email_auth.assess("x.de", txt_of=lambda n: (
        ["v=DMARC1; p=reject; rua=mailto:dmarc@x.de"] if n.startswith("_dmarc") else
        ["v=spf1 ip4:1.2.3.4 -all"] if n == "x.de" else []))
    check(not clean["issues"], "a correctly configured domain raises NO findings")


def test_cert_intel():
    print("\n" + "=" * 78)
    print("[2] CERTIFICATE INTELLIGENCE — Certificate Transparency cannot be blocked")

    rev = cert_intel.revoked_live(NS03_CT, NS03_LIVE)
    names = sorted(n for x in rev for n in x["names"])
    check(names == ["iiko.nzn.ns03.ru", "oo.ns03.ru"],
          "both REVOKED certificates whose names still resolve are found (got %s)" % names)
    check(not cert_intel.revoked_live(NS03_CT, set()),
          "a revoked certificate on a DEAD name is history, not exposure -> no finding")
    check(not cert_intel.revoked_live([{"dns_names": ["a.x.de"], "revoked": None}], {"a.x.de"}),
          "revoked=null means status UNKNOWN and is never treated as revoked")

    # Expiry must respect renewal: nextcloud's served cert expires in 31 days but a NEWER one is
    # already issued to 2026-10-03. Reporting the older one would invent an outage that renewal
    # has already prevented -- and that is exactly what reading the served certificate alone does.
    exp = [x["name"] for x in cert_intel.expiring(NS03_CT, NS03_LIVE, 21, now=NOW)]
    check("nextcloud.ns03.ru" not in exp,
          "a name with a newer certificate already issued is NOT flagged as expiring")
    # `... is False or True` was the first version of this line: an assertion that cannot fail,
    # which is the exact disease this repo keeps recording. Assert the PROPERTY instead: ventil2's
    # earliest certificate ends 2026-08-23 (14 days out) but a later one runs to 2026-10-22, so at
    # a 30-day threshold it must NOT be flagged. Reading the earliest would report a false outage.
    soon = [x["name"] for x in cert_intel.expiring(NS03_CT, NS03_LIVE, 30, now=NOW)]
    check("ventil2.nzn.ns03.ru" not in soon,
          "a superseded certificate never raises an expiry its renewal already prevented")
    only_old = [x["name"] for x in cert_intel.expiring(
        [_iss(["ventil2.nzn.ns03.ru"], "2026-05-25", "2026-08-23")], NS03_LIVE, 30, now=NOW)]
    check(only_old == ["ventil2.nzn.ns03.ru"],
          "...but with NO renewal issued, the same name IS flagged (the check really can fire)")

    blast = cert_intel.shared_blast(NS03_CT, NS03_LIVE)
    check(blast and blast[0]["count"] == 4,
          "the gateway certificate covering 4 services on one key is identified")
    check(len(blast) == 1, "renewals of the same SAN set are reported once, not per issuance")

    prof = cert_intel.ca_profile(NS03_CT)
    check(prof["mixed"] is True,
          "mixed estate detected: 90-day ACME beside a 13-month commercial certificate "
          "(two teams, or two eras, on one domain)")
    check("srv-kap-gt.ns03.ru" in cert_intel.internal_names(NS03_CT, ["ns03.ru"]),
          "internal-looking names leaked into public logs are surfaced")


def test_naming():
    print("\n" + "=" * 78)
    print("[3] NAMING CONVENTIONS — generate from the target's grammar, not from a wordlist")

    ct = ["autodiscover.ns03.ru", "mail.ns03.ru", "ns03.ru", "srv-kap-gt.ns03.ru",
          "ventil2.nzn.ns03.ru", "iiko.nzn.ns03.ru", "ing.nzn.ns03.ru", "nextcloud.ns03.ru",
          "ventil.nzn.ns03.ru", "oo.ns03.ru", "vpn.ns03.ru", "www.ns03.ru"]
    g = naming.learn(ct, ["ns03.ru"])
    check("nzn" in g["sites"] and "kap" in g["sites"],
          "both site codes are recovered: nzn (Nizino branch) and kap (Kapitolovo)")
    check(g["roles"] == ["gt"], "the role token `gt` is decomposed from srv-kap-gt")
    check("srv" in g["prefixes"], "the `srv-` prefix convention is learned")
    check("ventil" in g["sequenced"], "ventil2 reveals a numbered sequence")
    check("srv-kap-gt" not in g["services"],
          "a srv-<site>-<role> compound is PARSED, not tokenised as a service word")

    # Language follows the TARGET. The operator's rule: if the company does not operate somewhere
    # that speaks the language, there is no reason to spend queries asking in it.
    check(naming.langs_for(domains=["ns03.ru"]) == ["en", "ru"], "a .ru target earns Russian")
    check(naming.langs_for(domains=["angermann.de"]) == ["en", "de"], "a .de target earns German")
    check(naming.langs_for(domains=["x.com"]) == ["en"],
          "a target with no country evidence gets English ONLY, not all seven languages")
    check(naming.langs_for(domains=["x.com"], countries=["DE", "AT"]) == ["en", "de"],
          "an estate hosted in DACH earns German even on a .com")

    c = naming.candidates(g, ["ns03.ru"], naming.langs_for(domains=["ns03.ru"]), known=ct)
    check(not (set(c) & {n.lower() for n in ct}),
          "a name already known is never re-queried as a candidate")
    check(any(x.startswith("kotel.") for x in c),
          "Russian building-services vocabulary is generated (no English wordlist contains it)")
    check(any(x.startswith("srv-nzn-") for x in c),
          "the srv-<site>-<role> pattern is applied to the OTHER site code")
    check(len(c) <= 400, "the candidate list stays bounded (%d) -- fewer queries than a "
                         "blind dictionary, not more" % len(c))


def test_active_tier_is_off():
    print("\n" + "=" * 78)
    print("[4] THE ACTIVE TIER — must refuse unless an authorisation reference is recorded")

    for env, label, want in (
        ({}, "default: nothing set", False),
        ({"ACTIVE_PROBE": "1"}, "flag set but NO authorisation reference", False),
        ({"ACTIVE_PROBE_AUTH": "SOW-2026-114"}, "authorisation but no flag", False),
        ({"ACTIVE_PROBE": "1", "ACTIVE_PROBE_AUTH": "SOW-2026-114"}, "flag AND authorisation", True),
    ):
        for k in ("ACTIVE_PROBE", "ACTIVE_PROBE_AUTH"):
            os.environ.pop(k, None)
        os.environ.update(env)
        importlib.reload(active_probe)
        check(active_probe.enabled() is want, "%s -> enabled=%s" % (label, want))
        if not want:
            check(active_probe.tls_certificate("example.com").get("refused") is True,
                  "   ...and the probe REFUSES rather than connecting")

    for k in ("ACTIVE_PROBE", "ACTIVE_PROBE_AUTH"):
        os.environ.pop(k, None)
    importlib.reload(active_probe)
    check("not one packet" in active_probe.status()["note"],
          "the default run states the passive claim the public site and the ToU make")

    # The PASSIVE half: the same intelligence from a banner we already hold.
    r = active_probe.eol_from_banner("Server: Microsoft-IIS/10.0 /owa/auth/15.2.1748/themes/")
    check(r and r["product"] == "Exchange Server 2019 CU15",
          "an OWA build in a STORED banner maps to the product with no packet sent")
    check(r and r["end_of_support"] == "2025-10-14",
          "...and to its end-of-support date, which is what makes it a finding")
    check("not externally determinable" in r["caveat"],
          "the finding carries the honesty caveat: the CU is knowable, a patch level is NOT")




def _read_js(name):
    return open(os.path.join(os.path.dirname(os.path.abspath(__file__)), name),
                encoding="utf-8").read()


def test_ot_and_blind_scanner():
    print("\n" + "=" * 78)
    print("[5] ns03.ru DECK DEFECTS — an empty inventory, an enum on a slide, OT rated too low")

    import shodan_recon as R

    # --- OT / BMS. The operator's point, and the Jaguar Land Rover precedent is why it is CRITICAL.
    resolved = {"ventil.nzn.ns03.ru": ["193.218.140.18"], "ventil2.nzn.ns03.ru": ["193.218.140.18"],
                "ing.nzn.ns03.ru": ["193.218.140.18"], "iiko.nzn.ns03.ru": ["193.218.140.18"],
                "mail.ns03.ru": ["80.246.245.158"], "www.ns03.ru": ["195.208.1.101"],
                "nextcloud.ns03.ru": ["193.218.140.18"]}
    ot = {o["name"]: o for o in R.ot_names(resolved, ["ns03.ru"])}
    check("ventil.nzn.ns03.ru" in ot, "a ventilation controller on the public internet is detected")
    check("ing.nzn.ns03.ru" in ot,
          "`ing` is admitted ONLY because it shares the OT site zone (corroboration, not the token)")
    for benign in ("mail.ns03.ru", "www.ns03.ru", "nextcloud.ns03.ru"):
        check(benign not in ot, "%-22s is NOT mistaken for OT" % benign)
    # iiko is a restaurant point-of-sale platform and it sits INSIDE the OT site zone. Zone
    # membership corroborates an ambiguous OT token; it must never promote an unrelated name on
    # its own, or the zone becomes the same blanket anchor the abakus incident was about.
    check("iiko.nzn.ns03.ru" not in ot,
          "a non-OT host inside the OT zone is NOT swept in (zone corroborates, it does not admit)")
    check(not R.ot_names({"marketing.acme.de": ["1.2.3.4"], "ing.corp.acme.de": ["1.2.3.4"]},
                         ["acme.de"]),
          "an ambiguous token with NO OT zone around it raises nothing (the abakus lesson)")

    # THE SEVERITY. Read it from the ENGINE, not from a literal I typed into the assertion.
    src = _read_js("shodan_recon.py")
    blk = src[src.index("OPERATIONAL TECHNOLOGY, NAMED BY THE CUSTOMER"):]
    blk = blk[:blk.index("EMAIL AUTHENTICATION")]
    check('"sev": "CRITICAL", "ft": "ot_exposed"' in blk,
          "OT exposure is emitted CRITICAL, not HIGH: this class of incident stops production")
    check("ot_exposed" in R.TEMPLATES, "the finding has a deck template")
    _t, _w, _r, _f = R.TEMPLATES["ot_exposed"]
    check("Jaguar Land Rover" in " ".join(_w),
          "the template carries the precedent that justifies the severity")
    check(any("confirm" in x["title"].lower() for x in _r),
          "and a confirmation step, because a NAME is evidence of function, not an inventory")
    check("IEC 62443" in _f, "mapped to the OT security standard, not just the IT ones")

    # --- THE EMPTY INVENTORY. The delivered deck said "0 UNIQUE IPS" to a customer with 12 live
    # hostnames on 4 addresses. What was zero is what the SCANNER saw.
    js = _read_js("build_findings_deck.js")
    check("scanner_blind" in js,
          "the deck distinguishes 'the scanner saw nothing' from 'the customer has nothing'")
    check("HOSTS FROM DNS + CT" in js,
          "and reports the estate the customer's own DNS proves")
    check("dns_hosts" in src and "scanner_blind" in src,
          "the engine publishes the DNS-known estate for the deck to read")

    # --- THE ENUM ON A SLIDE. The LOW table printed "COLT: SASE/SSE with ZTNA" to a customer.
    check("(tagLabel[rem.tag] || rem.tag)" in js,
          "the LOW/baseline table renders the LABEL, never the raw COLT enum")
    check('rem.tag + ": "' not in js, "no code path prints the raw tag any more")


def main():
    print("=" * 78)
    print("  passive checks — replayed against the real ns03.ru engagement")
    test_email_auth()
    test_cert_intel()
    test_naming()
    test_active_tier_is_off()
    test_ot_and_blind_scanner()
    print("\n" + "=" * 78)
    if FAILED:
        print("  %d FAILED" % len(FAILED))
        for f in FAILED:
            print("    - " + f)
        return 1
    print("  ALL PASSED — new findings land, false positives do not, active tier stays shut")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())

