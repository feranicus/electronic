#!/usr/bin/env python3
"""
test_classify_adpolice.py — the Abu Dhabi Police regression (2026-08).

adpolice.gov.ae produced a four-finding deck. One finding was a false positive, one was the most
serious exposure in the engagement WRONGLY LABELLED, and the framework list cited EU and automotive
law at an Emirati police force. All three defects were in data the engine already had.

  D1  THE TLS NEGATION BUG — the widest false-positive source in the product's history.
      Shodan marks UNSUPPORTED protocols with a leading minus:
          5.194.255.186:443  ['-TLSv1','-SSLv2','-SSLv3','-TLSv1.1','TLSv1.2','-TLSv1.3']
      That host is TLS-1.2-only and correctly configured. classify() did `v.lstrip("-")` — it
      stripped the sign and then matched — so it raised "legacy TLS" on it. Every modern host lists
      its disabled protocols, so this fired on essentially every host the engine ever saw, and every
      deck already delivered is suspect.

  D2  THE SERVICE WAS NAMED FROM THE PORT, NOT THE REDIRECT CHAIN.
      151.253.157.21:443 was reported as "a mail service gateway". Its own record contained:
          301 -> https://mediahubtest.adpolice.gov.ae/otmm/ux-html/index.html
          302 -> /otdsws/login?logon_appname=Digital+Asset+Management+CE+25.4
      OpenText Media Management behind OpenText Directory Services, and the hostname says TEST.
      The one internet-facing host the force owns under its own certificate is a NON-PRODUCTION
      media repository. Rated Medium, for a TLS issue that was itself half false.

  D3  FRAMEWORKS WERE HARDCODED to a German automotive supplier: TISAX and UNECE R155 (vehicle
      type-approval) plus NIS2 and GDPR, in front of a UAE police force. Third recurrence.

    python test_classify_adpolice.py
"""
import os, sys

os.environ.setdefault("SHODAN_API_KEY", "test")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import shodan_recon as R                                                    # noqa: E402

FAILS = []


def check(cond, label):
    print(("  PASS  " if cond else "  FAIL  ") + label)
    if not cond:
        FAILS.append(label)


# =============================================================== D1 the TLS negation bug
print("== D1. a leading '-' in ssl.versions means NOT SUPPORTED ==")


def _tls(vers):
    return R.classify({"port": 443, "product": "", "hostnames": [], "http": {},
                       "ssl": {"versions": vers}})[1]


# The two REAL arrays from the adpolice export.
check(_tls(["-TLSv1", "-SSLv2", "-SSLv3", "-TLSv1.1", "TLSv1.2", "-TLSv1.3"]) != "legacy_tls",
      "5.194.255.186: every legacy version NEGATED -> not a legacy-TLS finding")
check(_tls(["TLSv1", "-SSLv2", "-SSLv3", "TLSv1.1", "TLSv1.2", "-TLSv1.3"]) == "legacy_tls",
      "151.253.157.21: TLSv1 and TLSv1.1 genuinely ENABLED -> still a finding")

check(_tls(["-TLSv1", "-SSLv3", "TLSv1.2", "TLSv1.3"]) != "legacy_tls",
      "a modern TLS1.2+1.3 host is clean")
check(_tls(["SSLv3", "TLSv1.2"]) == "legacy_tls", "genuinely enabled SSLv3 is still caught")
check(_tls([]) != "legacy_tls", "no version data -> no claim (absence of evidence)")
check(_tls(["-SSLv2", "-SSLv3", "-TLSv1", "-TLSv1.1", "-TLSv1.2", "-TLSv1.3"]) != "legacy_tls",
      "everything negated -> nothing claimed")


# =============================================================== D2 identify from the redirect chain
print("\n== D2. the redirect chain names the application, the port does not ==")

ADPOLICE = {
    "port": 443, "product": "", "hostnames": [], "asn": "AS5384",
    "ssl": {"versions": ["TLSv1", "TLSv1.1", "TLSv1.2"]},
    "http": {"title": None, "host": "151.253.157.21", "redirects": [
        {"location": "https://mediahubtest.adpolice.gov.ae/otmm/ux-html/index.html",
         "host": "151.253.157.21"},
        {"location": "/otdsws/login?logon_appname=Digital+Asset+Management+CE+25.4",
         "host": "mediahubtest.adpolice.gov.ae"}]}}

_sev, _kind = R.classify(ADPOLICE)
check(_sev in ("CRITICAL", "HIGH"),
      "the OpenText host is HIGH or above, not a Medium TLS note (got %s)" % _sev)
check(_kind in ("ecm_exposed", "nonprod_exposed"),
      "it is identified as a content platform / non-production system, not a mail gateway (%s)" % _kind)
check("mediahubtest" in R._redirect_trail(ADPOLICE),
      "the redirect trail is actually read")
check("otdsws" in R._hay(ADPOLICE) and "otmm" in R._hay(ADPOLICE),
      "the OpenText markers reach the classifier's haystack")

# A non-production system is a first-rank finding whatever it runs.
check(R.classify({"port": 443, "http": {"title": "Login"}, "hostnames": ["staging.acme.de"]})[0] == "HIGH",
      "a staging portal is HIGH on its own")
check(R.classify({"port": 443, "http": {"title": "Portal"}, "hostnames": ["uat.acme.de"]})[0] == "HIGH",
      "a UAT portal is HIGH on its own")

# ...but the token must be DELIMITED. A substring rule here would fire on half the internet.
for host, why in (("attestation.acme.de", "attestation contains 'test'"),
                  ("devices.acme.de", "devices contains 'dev'"),
                  ("protest.example.org", "protest contains 'test'"),
                  ("labour.example.org", "labour contains 'lab'")):
    _s, _k = R.classify({"port": 443, "product": "nginx", "http": {}, "hostnames": [host]})
    check(_k != "nonprod_exposed", "%s is NOT flagged non-production (%s)" % (host, why))

# A plain web server must stay a plain web server.
check(R.classify({"port": 443, "product": "nginx", "http": {}, "hostnames": ["www.acme.de"]})[0] == "LOW",
      "an ordinary web host is still LOW")


# =============================================================== D3 frameworks follow jurisdiction
print("\n== D3. the framework set follows the estate's country ==")
import re, subprocess, tempfile, json                                        # noqa: E402

_src = open(os.path.join(HERE, "build_findings_deck.js"), encoding="utf-8").read()
check("UAE Information Assurance" in _src, "UAE regime set exists for .ae estates")
check("NCSC Cyber Essentials" in _src, "UK regime set exists")
check("revFADP" in _src, "Swiss regime set exists")
check(_src.count("TISAX") <= 1,
      "TISAX is no longer an unconditional entry in the findings deck")
check("d.target && (d.target.country" in _src,
      "the deck reads the country the recon determined, rather than assuming")

# The engine must actually publish that country, or the deck falls back to the EU default forever.
check("\"country\": _cc" in open(os.path.join(HERE, "shodan_recon.py"), encoding="utf-8").read(),
      "shodan_recon publishes target.country")


# =============================================================== D4 absence is not a finding
print("\n== D4. 'not in Shodan' is not 'dead' ==")
_rs = open(os.path.join(HERE, "shodan_recon.py"), encoding="utf-8").read()
check("dns_no_service" not in _rs.split("TEMPLATES = ")[-1].split("_dns_findings.append")[-1][:400]
      or "resolved_no_service" in _rs,
      "the dangling-DNS candidate is recorded")
check("NOT raised as a finding" in _rs,
      "dangling DNS is put to the operator as a question, not asserted as a finding")
check("clarify" in open(os.path.join(HERE, "clarify.py"), encoding="utf-8").read(),
      "clarify.py still carries the stale_dns question")

print("\n" + ("FAILED: %d" % len(FAILS) if FAILS else "ALL ADPOLICE CLASSIFY CHECKS PASSED"))
for f in FAILS:
    print("   - " + f)
sys.exit(1 if FAILS else 0)
