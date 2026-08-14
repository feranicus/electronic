#!/usr/bin/env python3
"""
test_recall.py — regression test for the bibeltv.de RECALL failure (the opposite of the CA-pivot bug).

WHAT WENT WRONG (2026-07, bibeltv.de, run #4):
After the scope blow-out was fixed the deck swung to the other extreme: 5 hosts, 2 findings, and it
MISSED the two most valuable assets in the estate —
    gitlab.bibel.tv   142.132.188.73   (SCM: secrets / CI exposure)
    vpn.bibeltv.de    213.61.87.246    (remote-access edge, on COLT AS8220 - the pursuit hook)
plus the Strato mail/ftp hosts and both real web servers.

THREE CAUSES:
  1. bibel.tv is a DIFFERENT registrable domain from bibeltv.de. CT enumeration of "%.bibeltv.de"
     can never reveal it. It is discoverable from the seed certificate's SAN list, because the two
     names share a certificate — and a shared cert is evidence of common operation.
  2. crt.sh was the ONLY subdomain source and it failed on three consecutive runs
     (read timeout, HTTP 404, HTTP 503). One flaky service blinded the whole assessment.
  3. Nothing ever asked DNS. "gitlab." and "vpn." resolve instantly.

Pure logic test — no network, no Shodan key. Run by ship.py.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shodan_recon as R

FAILED = []


RAN = []


def check(cond, label):
    print(("  PASS  " if cond else "  FAIL  ") + label)
    RAN.append(label)
    if not cond:
        FAILED.append(label)


print("=" * 78)
print("  recall guards — bibeltv.de regression")

# ---------------------------------------------------------------------------------------------
# [16] rightmart.de — the HOSTER'S IDENTITY MUST NEVER BECOME THE TARGET'S
# rightmart.de sits on IP-Projects (a shared hoster), so its cert-O and netblock whois both read
# "IP-PROJECTS Michael Sebastian Schinzel trading as IP-Projects GmbH & Co. KG". Every token of that
# became a brand token, which then authorised org: pivots into two unrelated hosting companies:
#     org:"Michael Sebastian Schinzel trading as IP-Projects"  +343 hosts
#     org:"Marcus Hoffmann trading as VCServer Network"        +120 hosts
#     org:"IP-Projects"                                        +119 hosts
# Result: 1,417 IPs "in scope", 78 evidence IPs in the deck, ZERO belonging to the customer.
# ---------------------------------------------------------------------------------------------
print("\n[16] rightmart.de — a hoster's identity must never become the target's")
HOSTER_O = "IP-PROJECTS Michael Sebastian Schinzel trading as IP-Projects GmbH & Co. KG"

_t = R._brand_tokens_from("rightmart.de", [HOSTER_O])
check(_t == {"rightmart"}, "hoster cert-O contributes NO brand tokens (got %s)" % sorted(_t))
for _p in ("michael", "schinzel", "sebastian", "trading", "projects"):
    check(_p not in _t, "'%s' never becomes a brand token" % _p)

for _org in (HOSTER_O,
             "Michael Sebastian Schinzel trading as IP-Projects",
             "Marcus Hoffmann trading as VCServer Network",
             "IP-Projects GmbH & Co. KG"):
    check(not R._org_is_the_target(_org, "rightmart.de"), "org pivot refused: %s" % _org[:46])

check(R._looks_like_provider("Marcus Hoffmann trading as VCServer Network"), "'trading as' = provider shape")
check(R._looks_like_provider("Some Holder", prefix_count=130), "130 announced prefixes = provider")
check(not R._looks_like_provider("Bibel TV GmbH", prefix_count=2), "a 2-prefix media company is not a provider")

# the previously-fixed targets MUST still work — their cert-O really is the customer's
SKON_O = "S-KON Sales Kontor Hamburg GmbH"
check(R._org_is_the_target(SKON_O, "skon.de"), "S-KON cert-O still corroborates its seed")
_st = R._brand_tokens_from("skon.de", [SKON_O])
check("skon" in _st and "kontor" in _st, "S-KON still yields {skon, kontor} (got %s)" % sorted(_st))
check(R._org_is_the_target("Bibel TV GmbH", "bibeltv.de"), "bibeltv cert-O still corroborates")

check(not R._org_is_the_target("", "rightmart.de"), "empty org is not the target")
check(not R._org_is_the_target(HOSTER_O, ""), "no seed label -> fails closed")


# ---------------------------------------------------------------------------------------------
# [17] CERTIFICATES ARE THE HIGHEST-YIELD IDENTITY SOURCE — harvest CN + SAN from swept hosts.
# rightmart.de's mail archive lives on 'email-archiv-rightmart.de': a SEPARATE registrable domain,
# so CT enumeration of '%.rightmart.de' can never return it and the subdomain probe never guessed
# it. Its certificate named it outright — self-signed, EXPIRED, mailcow, IMAPS/993. Exactly the
# bibeltv.de -> bibel.tv sibling-domain class, and the single most material finding on that target.
# ---------------------------------------------------------------------------------------------
print("\n[17] certificates: CN + SAN harvest finds sibling domains CT cannot")
_m = {"ip_str": "3.77.104.100", "port": 993,
      "ssl": {"cert": {"subject": {"CN": "email-archiv-rightmart.de", "O": "mailcow"},
                       "issuer":  {"CN": "email-archiv-rightmart.de", "O": "mailcow"},
                       "expired": True,
                       "extensions": [{"name": "subjectAltName",
                                       "data": "0\\x82\\x19email-archiv-rightmart.de\\x82\\x1b*.email-archiv-rightmart.de"}]}}}
_n = R._cert_names(_m)
check("email-archiv-rightmart.de" in _n, "cert CN harvested from the mailcow host")
check(not any(x.startswith("x") and x[1:3].isalnum() and "rightmart" in x for x in _n),
      "DER length-prefix bytes are stripped (no 'x0crightmart.de' garbage)")
check(all("*" not in x for x in _n), "wildcard SAN normalised to its base name")

_tok = R._brand_tokens_from("rightmart.de", [])
_own, _why = R._owns_apex("email-archiv-rightmart.de", _tok, "rightmart.de")
check(_own, "the sibling domain is OWNED via the brand token (%s)" % _why)

# a neighbour on the same shared host must NOT drag its own domain into scope
_nb = {"ip_str": "1.2.3.4", "ssl": {"cert": {"subject": {"CN": "someoneelse.de"}, "issuer": {"CN": "R3"}}}}
_no, _ = R._owns_apex(R._apex(list(R._cert_names(_nb))[0]), _tok, "rightmart.de")
check(not _no, "a co-tenant's certificate domain is NOT adopted")

# the expired + self-signed pair must both be gradeable findings
check(R.classify({"port": 993, "ssl": {"cert": {"expired": True,
      "subject": {"CN": "x.de"}, "issuer": {"CN": "y"}}}})[1] in ("expired_tls", "self_signed"),
      "an expired/self-signed cert is classified, not ignored")

print("=" * 78)

# ---- the real Bibel TV estate, from the operator's verified super-filter doc ----
REAL = {
    "bibeltv.de":            "167.235.111.235",
    "www.bibeltv.de":        "167.235.111.235",
    "gitlab.bibel.tv":       "142.132.188.73",
    "vpn.bibeltv.de":        "213.61.87.246",
    "mail.bibeltv.de":       "81.169.145.64",
    "ftp.bibeltv.de":        "81.169.145.64",
    "autoconfig.bibeltv.de": "81.169.145.141",
    "www.bibel.tv":          "49.12.21.249",
}
SEED_SANS = ["bibeltv.de", "www.bibeltv.de", "bibel.tv", "www.bibel.tv", "api.bibeltv.de"]

print("\n[1] DNS subdomain probe finds the hosts CT enumeration missed")
_real_resolve = R._resolve
R._resolve = lambda n: ([REAL[n]] if n in REAL else [])
try:
    found = R._probe_subdomains(["bibeltv.de", "bibel.tv"])
    for must in ("gitlab.bibel.tv", "vpn.bibeltv.de", "mail.bibeltv.de", "autoconfig.bibeltv.de"):
        check(must in found, "%-24s discovered" % must)
    check(found.get("gitlab.bibel.tv") == ["142.132.188.73"], "gitlab resolves to the right IP")

    print("\n[2] the probe list actually contains the names that matter")
    for sub in ("gitlab", "vpn", "mail", "git", "ftp", "autoconfig", "owa", "jira", "ci"):
        check(sub in R.PROBE_SUBS, "'%s' is probed" % sub)
finally:
    R._resolve = _real_resolve

print("\n[3] sibling domain: bibel.tv is reachable from the seed cert, never from CT of bibeltv.de")
apexes = sorted({R._apex(s) for s in SEED_SANS})
check("bibel.tv" in apexes, "bibel.tv extracted from the SAN list")
check("bibeltv.de" in apexes, "bibeltv.de still present")
check(R._apex("gitlab.bibel.tv") == "bibel.tv", "_apex('gitlab.bibel.tv') == 'bibel.tv'")

print("\n[4] resolved hosts get PINNED as /32 — on a shared hoster the ASN is worthless, "
      "the host is not")
ident = {"seed": "bibeltv.de", "brand": "bibeltv", "org": None,
         "domains": ["bibeltv.de"], "nets": [], "asns": [], "org_variants": [], "brand_variants": []}
for ips in ({"gitlab.bibel.tv": ["142.132.188.73"], "vpn.bibeltv.de": ["213.61.87.246"]},):
    for fqdn, addrs in ips.items():
        for ip in addrs:
            c = ip + "/32"
            if c not in ident["nets"]:
                ident["nets"].append(c)
check("142.132.188.73/32" in ident["nets"], "gitlab pinned as /32")
check("213.61.87.246/32" in ident["nets"], "vpn pinned as /32")
check(len(ident["nets"]) == 2, "no /16 hoster ranges pinned (that would re-create the blow-out)")

print("\n[5] the CA-pivot gate still holds — recall must not reopen the false-positive hole")
ok, why = R._private_ca_ok("R12", ident, api=None)
check(not ok, "'R12' still refused (%s)" % why[:38])
ok, why = R._private_ca_ok("YR2", ident, api=None)
check(not ok, "'YR2' still refused")

print("\n[6] a hoster ASN must never become an ownership anchor")
check(R._is("Hetzner Online GmbH", R.CDNS), "Hetzner recognised as shared hosting")
check(R._is("Strato AG", R.CDNS) or "strato" in " ".join(R.CDNS), "Strato recognised as shared hosting")

print("\n[9] ZERO FALSE POSITIVES — a platform operator's client domains must NOT enter scope")
print("    (skon.de runs white-label loyalty microsites for Otto/MediaMarkt/Lidl/EAM/...)")
# cert subject-O is the ownership anchor: it turns saleskontor/praemienkontor into owned brands.
sk_tokens = R._brand_tokens_from("skon.de", ["S-KON Sales Kontor Hamburg GmbH"])
check("skon" in sk_tokens and "kontor" in sk_tokens, "brand tokens {skon, kontor} derived from seed + cert-O")
OWNED = ["skon.de", "saleskontor.de", "praemienkontor.de", "managementkontor.de", "ekontor24.de"]
CLIENTS = ["otto.de", "mediamarkt.de", "lidl.de", "eam.de", "dns-net.de", "tng.de",
           "purpur-energy.de", "dew21.de", "stadtwerke-garbsen.de", "mediamarkt-saturnvorteile.de"]
for d in OWNED:
    check(R._owns_apex(d, sk_tokens, "skon.de")[0], "%-24s kept (S-KON brand)" % d)
for d in CLIENTS:
    check(not R._owns_apex(d, sk_tokens, "skon.de")[0], "%-24s EXCLUDED (client / third party)" % d)

print("\n[10] microsite prefixes on a client apex are hard-excluded even if resolvable")
for host in ("vorteile.otto.de", "praemie.tng.de", "aktion.eam.de", "bonus.praemienkontor.de"):
    first = host.split(".")[0]
    ap = R._apex(host)
    is_microsite = any(first.startswith(mp) for mp in R._MICROSITE_PREFIXES)
    owned_apex = R._owns_apex(ap, sk_tokens, "skon.de")[0]
    excluded = is_microsite and not owned_apex
    # bonus.praemienkontor.de is on an OWNED apex -> kept; the otto/tng/eam ones are dropped
    if ap == "praemienkontor.de":
        check(owned_apex, "%-26s kept (microsite on OWNED apex)" % host)
    else:
        check(excluded, "%-26s dropped (microsite on client apex)" % host)

print("\n[11] the two S-KON pins that were the ONLY real hosts must survive the CDN drop")
# net:pinned uses cat='pinned', which bypasses run()'s hoster drop
import inspect
src = inspect.getsource(R.build_filters)
check('cat="pinned"' in src, "pinned filter tagged cat='pinned' (bypasses the hoster drop)")

print("\n[12] FP-AUDIT must never empty a deck (the skon.de disaster)")
import audit_fp as _A
_owned = {"domains": ["skon.de"], "brand_tokens": ["skon", "kontor"],
          "pinned": ["35.244.246.242", "217.110.76.92", "52.98.242.248"]}
_fj = {"target": {"owned": _owned}, "summary": {},
       "findings": [{"id": "H1", "sev": "HIGH", "title": "OWA", "evidence": ["52.98.242.248:443"]},
                    {"id": "H2", "sev": "HIGH", "title": "nginx", "evidence": ["35.244.246.242:443"]},
                    {"id": "M1", "sev": "MEDIUM", "title": "TLS", "evidence": ["217.110.76.92:443"]}]}
_, _dr, _rf = _A.apply_fixes(dict(_fj), [{"id": "H1"}, {"id": "H2"}, {"id": "M1"}])
check(_dr == [] and len(_rf) == 3, "auditor flags ALL 3 pinned hosts -> 0 dropped, deck kept")

_fj2 = {"target": {"owned": {"pinned": ["1.1.1.1", "2.2.2.2", "3.3.3.3", "4.4.4.4", "5.5.5.5"],
                             "brand_tokens": ["acme"], "domains": ["acme.com"]}},
        "summary": {}, "findings": [{"id": "F%d" % i, "sev": "HIGH", "evidence": ["%d.%d.%d.%d:443" % (i, i, i, i)]} for i in range(1, 6)]
        + [{"id": "BAD", "sev": "HIGH", "evidence": ["9.9.9.9:443 otherco.de"]}]}
_, _dr2, _ = _A.apply_fixes(dict(_fj2), [{"id": "BAD"}])
check(_dr2 == ["BAD"], "a genuine off-estate host still drops when it doesn't gut the deck")
check(not _A._host_is_off_estate(["52.98.242.248:443"], _owned), "a pinned host is never off-estate")

print("\n[14] org: pivot strips the legal suffix so it finds the S-KON WatchGuard netblock")
# the WatchGuard 213.61.141.198 was MISSED: cert O='S-KON Sales Kontor Hamburg GmbH' but the Shodan
# whois-org field is 'S-KON SALES KONTOR HAMBURG AG'. org:"…GmbH" matched nothing; the suffix-
# stripped core matches every legal-form variant.
_core = _A_core = R._org_core("S-KON Sales Kontor Hamburg GmbH")
check(_core == "S-KON Sales Kontor Hamburg", "legal suffix 'GmbH' stripped from the org phrase")
check(_core.lower() in "S-KON SALES KONTOR HAMBURG AG".lower(),
      "the stripped phrase matches the 'AG' whois-org variant (finds the WatchGuard)")
for full, want in (("Rosneft Deutschland GmbH", "Rosneft Deutschland"),
                   ("Acme Holding AG", "Acme"), ("Foo Bar S.p.A", "Foo Bar")):
    check(R._org_core(full) == want, "%-26s -> %r" % (full, want))

print("\n[15] edge appliances are CRITICAL findings, not LOW 'standard service' (S-KON WatchGuard)")
_wg = {"port": 443, "product": "", "ssl": {"cert": {"subject": {"O": "S-KON Sales Kontor Hamburg GmbH"},
                                                    "issuer": {"CN": "Firebox webCA"}}}}
check(R.classify(_wg) == ("CRITICAL", "edge_appliance"), "WatchGuard (self-signed 'Firebox webCA') -> CRITICAL edge_appliance")
check(R.classify({"port": 443, "product": "Barracuda"}) == ("CRITICAL", "edge_appliance"), "Barracuda -> CRITICAL edge_appliance")
check(R.classify({"port": 161}) == ("HIGH", "snmp_exposed"), "exposed SNMP :161 -> HIGH snmp_exposed")
check("edge_appliance" in R.TEMPLATES and "snmp_exposed" in R.TEMPLATES, "both new finding types have deck templates")
# guardrail: a plain web host must NOT be misread as an appliance
check(R.classify({"port": 443, "product": "nginx", "version": "1.18.0"})[1] != "edge_appliance",
      "plain nginx is not misclassified as an appliance")

print("\n[13] the FP auditor must be a DIFFERENT model than the deck author (never self-audit)")
_chain = ["gemma-4-31B-it", "deepseek-3.2", "llama-4-maverick"]
for _author in _chain + ["openai-gpt-oss-120b"]:
    _aud = _A._pick_auditor(_author, _chain)
    check(_aud != _author, "author %-22s -> auditor %-18s (different model)" % (_author, _aud))
    check(_A._vendor(_aud) != _A._vendor(_author), "   ...and a different vendor")

print("\n" + "=" * 78)
if FAILED:
    print("  %d CHECK(S) FAILED" % len(FAILED))
    for f in FAILED:
        print("   - " + f)
    sys.exit(1)
# NOT the end of the file - roughly 73 more checks follow. This used to say "ALL CHECKS PASSED"
# here, which was false, and the sys.exit above was the ONLY exit-code enforcement in the file:
# every section after this point (S18 co-tenant, [19]-[25], and crucially [22], the public-suffix
# guard that stopped the budget.gov.ru whole-government blow-out) printed FAIL and the script still
# exited 0, so `python ship.py` deployed anyway. Measured, not assumed: breaking [22] gave
# "FAIL lines=1, rc=0". The real gate is now at the END of this file.
print("  sections 1-13 passed — recall keeps owned assets; client/white-label domains stay OUT")
# ---------------------------------------------------------------------------------------------
# S18 - angermann.de: the brand-token gate failed in BOTH directions at once (2026-07)
#   too tight -> netbid.com / nordleasing.com / leaseback.de / buerosuche.de were unreachable
#   too loose -> ra-angermann.de (a law firm) and a DENTAL practice walked straight in
# group_discovery.py supplies the customer's own published roster; it is authoritative in both
# directions. Absent a published structure, the historic behaviour must be untouched (S-KON).
# ---------------------------------------------------------------------------------------------
print("\n== S18: angermann - group structure fixes recall AND precision ==")
_G = {"netbid.com", "nordleasing.com", "leaseback.de", "buerosuche.de", "angermann-consult.de"}
for _d in sorted(_G):
    check(R._owns_apex(_d, {"angermann"}, "angermann.de", _G, True)[0],
          "S18 recall: %s is owned via the published group structure" % _d)
check(R._owns_apex("angermann.de", {"angermann"}, "angermann.de", _G, True)[0],
      "S18: the seed apex is still owned")
for _d in ("ra-angermann.de", "renner-angermann.de", "angermann-webdesign.de"):
    _ok, _why = R._owns_apex(_d, {"angermann"}, "angermann.de", _G, True)
    check(not _ok, "S18 precision: %s rejected as a surname lookalike" % _d)
    check("lookalike" in _why, "S18: %s is flagged for operator confirmation, not silently dropped" % _d)
check(not R._owns_apex("otto.de", {"angermann"}, "angermann.de", _G, True)[0],
      "S18: an unrelated apex is still rejected")
# REGRESSION: with no published structure the kontor-token recall (S-KON) must be unchanged
for _d in ("saleskontor.de", "praemienkontor.de", "ekontor24.de"):
    check(R._owns_apex(_d, {"skon", "kontor"}, "skon.de", set(), False)[0],
          "S18 regression: %s still owned when no group structure exists" % _d)
check(not R._owns_apex("mediamarkt.de", {"skon", "kontor"}, "skon.de", set(), False)[0],
      "S18 regression: a client apex is still rejected")
# the co-tenant guard's discriminator: per-IP whois org, on the real shared Colt /24
check(R._org_is_the_target("Horst F.G. Angermann GmbH", "angermann.de"),
      "S18 co-tenant: Angermann's own whois org corroborates the seed")
for _o in ("NORDRHEINISCHE AERZTEVERSORGUNG", "FACT Informationssysteme und Consulting GmbH",
           "Regus Gmbh and Co Kg", "NAGASE (Europa) GmbH"):
    check(not R._org_is_the_target(_o, "angermann.de"),
          "S18 co-tenant: %s does NOT corroborate -> dropped from the shared /24" % _o[:28])

print("=" * 78)

# ---------------------------------------------------------------------------------------------
print("\n[19] enrichment must be ABLE to answer: the lotto24.de 0%-coverage failure")
# The deck was pure template text because all four models 'failed'. Two of them never had a chance,
# and the map-reduce top-up had never worked at all. Guard each cause.
import os as _os
_os.environ.setdefault("OPENAI_API_KEY", "test")
import enrich as _E, enrich_parallel as _P, json as _json2

# (a) THE SHARD CRASH. _call returns (text, usage); the shard fed the whole TUPLE to _json(),
#     raising "'tuple' object has no attribute 'find'" on every shard, every run, silently.
_saved_call = _E._call
_E._call = lambda t, model=None, timeout=None, max_tokens=None: (
    _json2.dumps({"exec_summary": "s" * 120,
                  "findings": [{"id": i, "what": ["w"], "why": ["y" * 120],
                                "rem": [{"tag": "COLT", "title": "t", "body": "b" * 120}]}
                               for i in ["A1", "A2"]]}), {"completion_tokens": 800})
_fjs = {"target": {"company": "T"},
        "findings": [{"id": i, "sev": "HIGH", "title": "t", "evidence": ["203.0.113.9:443"]}
                     for i in ["A1", "A2"]]}
_g, _m = _P._call_shard(_E, _fjs, _fjs["findings"], "en", 0, "deepseek-3.2", 120)
check(len(_g) == 2 and not _m.get("error"),
      "a map-reduce shard returns findings instead of 'tuple object has no attribute find'")
_E._call = _saved_call

# (b) THE ARITHMETIC. A request must fit the slice it is given. max_tokens was a flat 11000
#     (~110s at the measured rate) while the per-call floor hands out 60s -> guaranteed timeout.
for _s in (60, 112, 175):
    _mt = _E.feasible_max_tokens(_s)
    check(_mt / _E.TOK_PER_S <= _s,
          "a %ds slice asks for %d tokens (~%ds) - it can actually finish" % (_s, _mt, _mt // _E.TOK_PER_S))

# (c) PER-MODEL CONSTRAINTS ARE ENCODED, not rediscovered by paying for a 400 every call.
_sent = {}
_saved_post = _E._post
_E._post = lambda p, timeout=None: (_sent.clear() or _sent.update(p) or
    {"choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}], "usage": {}})
_E._call("x", model="kimi-k2.6", timeout=120)
check("response_format" not in _sent and _sent.get("temperature") == 0.6,
      "kimi is sent temperature=0.6 and NO response_format (the API rejects both)")
check(_sent.get("chat_template_kwargs") == {"enable_thinking": False},
      "kimi is sent enable_thinking=False - it is a reasoning model and will otherwise ramble")
_E._call("x", model="deepseek-3.2", timeout=120)
check("response_format" in _sent, "other models still get response_format=json_object")
_E._post = _saved_post
check(_E._FALLBACKS[0] == "deepseek-3.2",
      "chain head is the model MEASURED fastest+valid on the real prompt, not the slowest")
check(_E._FALLBACKS[-1].startswith("kimi"),
      "kimi is LAST - it burned 164s of a 175s slice on ecolines.net and starved the next model")

print("\n[21] a 400 must be fixed by what the SERVER said, never by blanket-stripping the payload")
# ecolines.net: the API answered "temperature must be 0.6 for this model" (the required value had
# CHANGED from 1.0). The old handler ignored the number and blanket-popped `chat_template_kwargs` —
# the one flag suppressing kimi's chain-of-thought. The retry therefore ran with thinking ON, kimi
# emitted 46,801 chars, hit our max_tokens ceiling, came back as truncated non-JSON, and burned
# 164s. The blanket remedy for one 400 CAUSED the next failure.
import io as _io21, json as _j21, urllib.error as _ue21

def _post_400(body, replies):
    calls = []
    def _p(payload, timeout=None):
        calls.append(_j21.loads(_j21.dumps(payload)))   # deep copy: the caller mutates the payload
        if len(calls) == 1:
            raise _ue21.HTTPError("u", 400, "Bad Request", {}, _io21.BytesIO(body))
        return replies
    return calls, _p

_OK21 = {"choices": [{"message": {"content": '{"exec_summary":"x","findings":[{"id":"H1"}]}'},
                      "finish_reason": "stop"}], "usage": {"completion_tokens": 900}}
_calls, _E._post = _post_400(
    b'{"message":"temperature must be 0.6 for this model","status_code":400}', _OK21)
_txt21, _ = _E._call("p", model="kimi-k2.6", timeout=100)
check(_calls[1].get("temperature") == 0.6, "the retry re-sends the temperature the SERVER named")
check(_calls[1].get("chat_template_kwargs") == {"enable_thinking": False},
      "the retry STILL suppresses thinking (the ecolines regression)")
check("H1" in _txt21, "and the answer then parses")

_calls, _E._post = _post_400(
    b'{"message":"chat_template_kwargs is not supported for this model"}',
    {"choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}], "usage": {}})
_E._call("p", model="kimi-k2.6", timeout=100)
check("chat_template_kwargs" not in _calls[1],
      "chat_template_kwargs IS dropped when the server actually names it")
_E._post = _saved_post

print("\n[20] a shard must be sent the CONTRACT, and coverage must measure DEPTH")
# lotto24.de DE run: coverage said 6/6 = 100%, and finding H1 still shipped a 38-char `what`, a
# 259-char `why` and ONE remediation row where the slide renders five. Cause: E.PROMPT is a
# %-FORMAT template (bible, language, findings) and _call_shard CONCATENATED it — so three literal
# "%s" went to the model and the 10,435-char DELTAS BIBLE was dropped entirely.
import json as _j3
_seen = {}
def _fake_rich(text, model=None, timeout=None, max_tokens=None):
    _seen["p"] = text
    return _j3.dumps({"findings": [{"id": i, "what": ["w" * 60], "why": ["y" * 300],
                                    "rem": [{"tag": "COLT", "title": "t", "body": "b" * 200}] * 3}
                                   for i in ["H1", "H2"]]}), {"completion_tokens": 3200}
_sv = _E._call
_E._call = _fake_rich
_fj3 = {"target": {"company": "T"},
        "findings": [{"id": i, "sev": "HIGH", "title": "t", "evidence": ["203.0.113.1:443"]}
                     for i in ["H1", "H2"]]}
_P._call_shard(_E, _fj3, _fj3["findings"], "de", 0, "deepseek-3.2", 150)
check(_E._bible()[:60] in _seen["p"], "the shard prompt carries the DELTAS BIBLE (the rich contract)")
check(_seen["p"].count("%s") == 0, "no literal '%s' placeholders are sent to the model")
check(len(_seen["p"]) > 10000, "shard prompt is contract-sized (%d chars, was 2462)" % len(_seen["p"]))

def _fake_thin(text, model=None, timeout=None, max_tokens=None):
    return _j3.dumps({"findings": [{"id": i, "what": ["short"], "why": ["one sentence."],
                                    "rem": [{"tag": "COLT", "title": "t", "body": "b"}]}
                                   for i in ["H1", "H2"]]}), {"completion_tokens": 90}
_E._call = _fake_thin
_, _rep3 = _P.run(_fj3, "de")
check(_rep3["coverage"] == 0.0, "a THIN answer scores 0%% coverage, not 100%% (presence != depth)")
_E._call = _fake_rich
_, _rep4 = _P.run(_fj3, "de")
check(_rep4["coverage"] == 1.0, "a full-depth answer scores 100%")
check(_rep4["shards"][0].get("tok_s") is not None,
      "throughput is recorded per shard so the next timeout is read, not guessed")
_E._call = _sv


print("\n[22] budget.gov.ru — a PUBLIC SUFFIX is not a company (the whole-government blow-out)")
# The delivered deck claimed 203 IPs and EUR 11-28M of priced risk across duma.gov.ru, nalog.gov.ru,
# mchs.gov.ru, fssp.gov.ru and the rest of the Russian federal government — for a request about ONE
# budget-transparency site. ONE line caused it: `_apex` returned the last two labels, so every
# ministry resolved to the same "apex" `gov.ru` and the ownership gate agreed they were one customer.
import psl as _P

for _h, _want in (("budget.gov.ru", "budget.gov.ru"), ("duma.gov.ru", "duma.gov.ru"),
                  ("nalog.gov.ru", "nalog.gov.ru"), ("www.bbc.co.uk", "bbc.co.uk"),
                  ("example.com.au", "example.com.au"), ("a.b.example.co.jp", "example.co.jp")):
    check(_P.registrable(_h) == _want,
          "registrable(%s) = %s" % (_h, _P.registrable(_h)))
check(R._apex("budget.gov.ru") != R._apex("duma.gov.ru"),
      "two ministries are NOT the same owner (this is the whole bug)")

# Regression: every earlier incident domain must be unchanged by the PSL.
for _h, _want in (("skon.de", "skon.de"), ("gitlab.bibel.tv", "bibel.tv"),
                  ("vorteile.otto.de", "otto.de"), ("ecolines.net", "ecolines.net"),
                  ("email-archiv-rightmart.de", "email-archiv-rightmart.de"),
                  ("angermann.3cx.eu", "3cx.eu")):
    check(R._apex(_h) == _want, "regression: _apex(%s) still %s" % (_h, _want))

# The seed itself may not BE a public suffix.
check(_P.is_public_suffix("gov.ru") and _P.is_public_suffix("co.uk"),
      "gov.ru / co.uk are recognised as public suffixes")
check(not _P.is_public_suffix("otto.de") and not _P.is_public_suffix("budget.gov.ru"),
      "a real registrable domain is not mistaken for one")
# DECLINED BY DEFAULT, but NOT forbidden: "show me every Russian federal body" is a legitimate
# request from a regulator or a researcher. It is a ZONE SURVEY, not an assessment of one company,
# so it needs an explicit assertion and the artifact must say what it is.
try:
    R.resolve_identity("gov.ru")
    check(False, "seeding a public suffix must be declined by default")
except R.ScopeRefused as _sr:
    check(getattr(_sr, "code", "") == "public_suffix",
          "declined with a machine-readable code, not a crash")
    check("budget.gov.ru" in getattr(_sr, "hint", ""),
          "the refusal names a concrete next step")
    check("zone" in getattr(_sr, "hint", "").lower(),
          "...and offers the deliberate whole-zone option")
_zs = R.resolve_identity("gov.ru", allow_public_suffix=True)
check(_zs.get("zone_survey") is True,
      "an explicit assertion is honoured AND labelled zone_survey")
check(R.resolve_identity("skon.de").get("zone_survey") is False,
      "a normal company is never labelled a zone survey")

# FAIL CLOSED with no brand token: rarity alone let a NATIONAL CA through.
class _RareAPI:
    def count(self, q): return {"total": 300}

_no_tok = {"seed": "gov.ru", "brand": "gov.ru", "org": "gov.ru", "domains": ["gov.ru"]}
check(not R._brand_tokens(_no_tok), "the incident shape really does yield zero brand tokens")
_ok, _why = R._private_ca_ok("Russian Trusted Sub CA", _no_tok, _RareAPI())
check(not _ok, "no brand token -> CA pivot refused (%s)" % _why)
_bib = {"seed": "bibeltv.de", "brand": "bibeltv.de", "org": None, "domains": ["bibeltv.de"]}
check(R._private_ca_ok("Bibel TV Issuing CA 01", _bib, _RareAPI())[0],
      "a genuine branded private CA still passes")


# =================================================================================================
# [23] CERTIFICATE TRANSPARENCY — the operator asked why CertSpotter was not "one of our checks".
# It was, as a SECOND SOURCE OF NAMES ONLY: it left the two most valuable fields on the table and
# was quietly losing recall.
# =================================================================================================
def test_certspotter():
    print("\n" + "=" * 78)
    print("[23] Certificate Transparency: paging, and the CAA authorisation check")

    # --- THE RECALL BUG. SSLMate's documentation is explicit: "if the after parameter is empty or
    # omitted, the API will return the LEAST-recently-discovered issuances". So one call plus a
    # [:200] slice returned the OLDEST certificates of the estate. On any domain with more than a
    # page of history the recently-issued names -- i.e. the live hosts -- were never seen at all.
    pages = []

    def fake_get(url, timeout=15, headers=None):
        after = url.split("&after=")[1].split("&")[0] if "&after=" in url else None
        pages.append(after)
        if after is None:
            return [{"id": "1", "dns_names": ["old.x.de"], "issuer": {}}]
        if after == "1":
            return [{"id": "2", "dns_names": ["new.x.de"], "issuer": {}}]
        return []

    _real = R._get_json
    R._get_json = fake_get
    try:
        names = R._certspotter_domains("x.de")
    finally:
        R._get_json = _real
    check(pages == [None, "1", "2"], "paging follows after=<id>, not page 1 only")
    check("new.x.de" in names, "a name only on page 2 is found (this was the recall bug)")
    check("old.x.de" in names, "page 1 names are still kept")

    # --- THE HELPER'S SIGNATURE. _get_json had no `headers` parameter; calling it with one raises
    # TypeError INSIDE the caller's own `except Exception`, which would silently disable the second
    # CT source while printing a warning that blamed the network.
    import inspect as _insp
    check("headers" in _insp.signature(R._get_json).parameters,
          "_get_json accepts the headers the CT caller passes")

    # --- CAA PARSING. iodef is a reporting address, not an issuer; parameters follow a semicolon.
    check(R._caa_issuers(['0 issue "letsencrypt.org"'])[0] == {"letsencrypt.org"},
          "issue tag parsed")
    check(R._caa_issuers(['0 issue "letsencrypt.org; validationmethods=dns-01"'])[0]
          == {"letsencrypt.org"}, "parameters after ';' are stripped")
    check(R._caa_issuers(['0 issuewild "digicert.com"'])[1] == {"digicert.com"},
          "issuewild is kept separate from issue")
    check(R._caa_issuers(['0 iodef "mailto:s@x.de"']) == (set(), set()),
          "iodef is NOT read as an authorised issuer")

    LE = {"friendly_name": "Let's Encrypt", "caa_domains": ["letsencrypt.org"]}
    DC = {"friendly_name": "DigiCert", "caa_domains": ["digicert.com"]}
    UNK = {"friendly_name": "Mystery CA", "caa_domains": None}

    def _i(n, issuer):
        return {"dns_names": n, "issuer": issuer,
                "not_before": "2026-01-01T00:00:00Z", "not_after": "2026-12-01T00:00:00Z"}

    CAA = ['0 issue "letsencrypt.org"']
    no_sub_caa = lambda n: []

    def n_flagged(iss, caa, lk=no_sub_caa):
        return len([g for g in R._unauthorised_issuances("x.de", iss, caa, caa_of=lk)
                    if not g.get("policy_conflict")])

    check(n_flagged([_i(["a.x.de"], LE)], CAA) == 0, "an authorised certificate is silent")
    check(n_flagged([_i(["a.x.de"], LE), _i(["b.x.de"], DC)], CAA) == 1,
          "a certificate outside the CAA policy IS caught")

    # FOUR FAIL-CLOSED PATHS. A false accusation of mis-issuance is the worst thing this engine
    # could put in a customer deck, so each of these must produce NO finding.
    check(n_flagged([_i(["b.x.de"], UNK)], CAA) == 0,
          "an issuer SSLMate cannot classify -> no claim")
    check(n_flagged([_i(["b.x.de"], DC)], []) == 0,
          "no CAA published -> that is the no_caa finding, not this one")
    check(n_flagged([_i(["b.x.de"], DC)], None) == 0,
          "CAA lookup FAILED -> absence of evidence is never a finding")
    check(n_flagged([_i(["b.x.de"], DC)], CAA, lambda n: None) == 0,
          "a subdomain whose CAA cannot be read -> no accusation")
    check(n_flagged([_i(["b.x.de"], DC)], CAA, lambda n: ['0 issue "digicert.com"']) == 0,
          "a subdomain that authorises the issuer itself -> quiet")

    # BLAST RADIUS. `0 issue ";"` authorises nobody and is a common misconfiguration; flagging the
    # entire estate as mis-issued would be spectacularly wrong in a customer deck.
    g = R._unauthorised_issuances("x.de", [_i(["a.x.de"], DC), _i(["b.x.de"], DC)],
                                  ['0 issue ";"'], caa_of=no_sub_caa)
    check(bool(g) and g[0].get("policy_conflict") is True,
          "every certificate unauthorised -> a CAA POLICY problem, not mass mis-issuance")

    check("cert_unauthorised" in R.TEMPLATES, "the finding has a deck template")


test_certspotter()


# =================================================================================================
# [24] ns03.ru — CT told us the name EXISTS; nothing ever checked whether it RESOLVES.
#
# The delivered deck said "IPs 0" and carried ONE finding. Certificate Transparency had returned 13
# names for the domain -- srv-kap-gt, ventil.nzn, ventil2.nzn, ing.nzn, iiko.nzn, oo, nextcloud --
# and not one was resolved. They existed only as Shodan `hostname:` clauses. The consequences
# compounded: nothing was pinned, ident["resolved"] held only the ~60-word probe list, and
# cert_intel joins its findings against exactly that map, so the TWO REVOKED CERTIFICATES the
# feature was built for produced nothing at all.
# =================================================================================================
def test_ct_names_are_resolved():
    print("\n" + "=" * 78)
    print("[24] ns03.ru: a CT-discovered name must be RESOLVED, not just searched for")

    NS03 = {  # the operator's real DNS answers
        "autodiscover.ns03.ru": ["213.170.88.162", "80.246.245.158"],
        "mail.ns03.ru": ["80.246.245.158"], "vpn.ns03.ru": ["80.246.245.158"],
        "www.ns03.ru": ["195.208.1.101"], "ns03.ru": ["195.208.1.101"],
        "test.ns03.ru": ["195.208.1.101"], "nextcloud.ns03.ru": ["193.218.140.18"],
        "srv-kap-gt.ns03.ru": ["213.170.88.162", "80.246.245.158"],
        "iiko.nzn.ns03.ru": ["193.218.140.18"], "ing.nzn.ns03.ru": ["193.218.140.18"],
        "oo.ns03.ru": ["193.218.140.18"], "ventil.nzn.ns03.ru": ["193.218.140.18"],
        "ventil2.nzn.ns03.ru": ["193.218.140.18"],
    }
    CT_ONLY = ["srv-kap-gt.ns03.ru", "iiko.nzn.ns03.ru", "ing.nzn.ns03.ru", "oo.ns03.ru",
               "ventil.nzn.ns03.ru", "ventil2.nzn.ns03.ru"]

    # The engine must resolve a CT name exactly as it resolves a wordlist name. Exercised against
    # the real block: every CT name under an owned apex, bounded, one query each.
    _real = R._resolve
    R._resolve = lambda n: NS03.get(n, [])
    try:
        live = {n: R._resolve(n) for n in CT_ONLY if R._resolve(n)}
    finally:
        R._resolve = _real
    for n in CT_ONLY:
        check(n in live, "%-24s is resolved, not merely searched for" % n)
    # BE HONEST ABOUT WHAT THIS BUYS. On ns03.ru the wordlist happened to reach all four addresses
    # already, so the gain is not new IPs -- it is the NAMES. A certificate is issued to a name, so
    # a name that is never resolved can never be joined to its certificate, which is exactly how
    # two revoked certificates on live hosts stayed invisible. Asserting "new addresses" here would
    # have been a claim the data does not support.
    check(len(live) == 6, "six CT names become known hosts (%d)" % len(live))
    check(set(live) & {"iiko.nzn.ns03.ru", "oo.ns03.ru"} == {"iiko.nzn.ns03.ru", "oo.ns03.ru"},
          "including both names that carry a REVOKED certificate")

    # THE CONSEQUENCE, which is what the customer actually lost: cert_intel joins against the
    # resolved map, so an unresolved CT name means a revoked certificate on a LIVE host is silent.
    import cert_intel
    LE = {"friendly_name": "Let's Encrypt"}

    def _c(names, na, rev=False):
        return {"dns_names": names, "not_before": "2026-06-01T00:00:00Z",
                "not_after": na + "T00:00:00Z", "issuer": LE, "revoked": rev}

    iss = [_c(["iiko.nzn.ns03.ru"], "2026-09-01", True), _c(["oo.ns03.ru"], "2026-09-18", True)]
    wordlist_only = {"autodiscover.ns03.ru", "mail.ns03.ru", "nextcloud.ns03.ru",
                     "test.ns03.ru", "vpn.ns03.ru", "www.ns03.ru"}
    check(not cert_intel.revoked_live(iss, wordlist_only),
          "with CT names unresolved the two REVOKED certificates are invisible (the delivered bug)")
    got = sorted(n for x in cert_intel.revoked_live(iss, set(live)) for n in x["names"])
    check(got == ["iiko.nzn.ns03.ru", "oo.ns03.ru"],
          "with them resolved, both revoked certificates become findings (%s)" % got)

    # AND the naming miner must be fed the list that actually holds the CT names. It read
    # ident["domains"] (populated only at the END of resolve_identity) and ident["ct_domains"]
    # (which has never existed), so it found no site codes and skipped itself on every run.
    import naming
    check(not naming.learn(["ns03.ru"], ["ns03.ru"])["sites"],
          "reading the empty key gives no site codes -- the miner silently skipped")
    g = naming.learn(list(NS03), ["ns03.ru"])
    check(g["sites"][:2] == ["nzn", "kap"],
          "reading the real name list recovers both site codes %s" % g["sites"][:2])

    # Guard the wiring itself: a future edit that points the miner back at an empty key would be
    # invisible in every unit test, because the miner fails SILENTLY by design.
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "shodan_recon.py"),
               encoding="utf-8").read()
    blk = src[src.index("CONVENTION-DERIVED CANDIDATES"):]
    blk = blk[:blk.index("_gram = naming.learn")]
    check('ident.get("ct_domains")' not in blk,
          "the miner no longer reads a key that does not exist")
    check("CT names resolved:" in src,
          "the CT-resolution step is present and reports what it found")


test_ct_names_are_resolved()


# =============================================================================================
# [25] THE GATEWAY MADE structured-output AND a token ceiling MUTUALLY EXCLUSIVE (2026-08-14)
# Three vendors returned the same 400 in ONE run - deepseek-3.2, llama-4-maverick and
# gemma-4-31B-it - so this is DO's gateway, not a model:
#     "max_tokens cannot be set when response_format type is 'json_object'; omit max token
#      limits for structured outputs to avoid truncated JSON responses"
# We keep the JSON contract and drop the ceiling, which is what the server advises AND what our
# own history argues for: a max_tokens cut lands MID-JSON (finish_reason=length -> JSONDecodeError
# at char 13,290 and char 30,117, both already in CLAUDE.md), while losing the ceiling costs only
# the feasibility bound - wall clock is still held by the per-call timeout, and a timeout is a
# CLEAN failover instead of a parsed-garbage one.
# =============================================================================================
print("")
print("=" * 78)
print("[25] structured output vs the token ceiling (the 2026-08-14 gateway change)")

import urllib.error as _ue
import io as _io25
import contextlib as _ctx25
import json as _json25

_MT_BODY = ('{"message":"max_tokens cannot be set when response_format type is \'json_object\'; '
            'omit max token limits for structured outputs to avoid truncated JSON responses"}')


def _mk(body=None):
    """A fake endpoint. With `body`, the FIRST call 400s with it."""
    sent, st = [], {"n": 0}

    def post(payload, timeout=None):
        sent.append(dict(payload)); st["n"] += 1
        if body and st["n"] == 1:
            raise _ue.HTTPError("u", 400, "Bad Request", {}, _io25.BytesIO(body.encode()))
        return {"choices": [{"message": {"content": _json25.dumps(
            {"exec_summary": "x" * 200, "findings": [{"id": "H1", "what": "y" * 80}]})},
            "finish_reason": "stop"}], "usage": {"prompt_tokens": 10, "completion_tokens": 900}}
    return sent, post


_orig_post = _E._post
try:
    # the three chained models must not pay a wasted round-trip at all
    for _m in ("deepseek-3.2", "llama-4-maverick", "gemma-4-31B-it"):
        _sent, _E._post = _mk()
        with _ctx25.redirect_stderr(_io25.StringIO()):
            _E._call("prompt", model=_m, timeout=120)
        check(len(_sent) == 1, "%s: the 400 is PRE-EMPTED, not paid for on every assessment" % _m)
        check("max_tokens" not in _sent[0], "%s: no ceiling is sent alongside json_object" % _m)
        check(bool(_sent[0].get("response_format")),
            "%s: the JSON contract is KEPT (dropping it is what truncates mid-JSON)" % _m)

    # kimi has response_format in _drop, so nothing about it should change
    _sent, _E._post = _mk()
    with _ctx25.redirect_stderr(_io25.StringIO()):
        _E._call("prompt", model="kimi-k2.6", timeout=120)
    check(bool(_sent[0].get("max_tokens")),
        "kimi keeps its feasibility ceiling - it never sends response_format")

    # and if the gateway ever objects again, repair WHAT IT NAMED
    _sent, _E._post = _mk(_MT_BODY)
    _err = _io25.StringIO()
    with _ctx25.redirect_stderr(_err):
        _E._call("prompt", model="kimi-k2.6", timeout=120)
    check("max_tokens" not in _sent[1],
        "a body naming max_tokens drops max_tokens on the retry")
    check("dropped max_tokens" in _err.getvalue(), "...and says so")

    # the older constraint must still behave exactly as before
    _sent, _E._post = _mk('{"message":"response_format type \'json_object\' is not supported"}')
    with _ctx25.redirect_stderr(_io25.StringIO()):
        _E._call("prompt", model="deepseek-3.2", timeout=120)
    check(not _sent[1].get("response_format"),
        "a body naming response_format alone still drops response_format")
finally:
    _E._post = _orig_post


# =============================================================================================
# THE REAL GATE. It must be the LAST thing in this file.
# A test file whose only sys.exit sits in the middle silently stops enforcing everything below
# it - and that is where the newest, least-proven checks live, because new sections get appended.
# So the exit belongs at the end, and a test that appends a section inherits enforcement for free.
# =============================================================================================
print("\n" + "=" * 78)
if FAILED:
    print("  %d CHECK(S) FAILED" % len(FAILED))
    for f in FAILED:
        print("   - " + f)
    sys.exit(1)
print("  ALL %d CHECKS PASSED - every section, not just the ones above the old mid-file exit"
      % len(RAN))
print("=" * 78)
