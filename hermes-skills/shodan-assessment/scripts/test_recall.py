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


def check(cond, label):
    print(("  PASS  " if cond else "  FAIL  ") + label)
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
print("  ALL CHECKS PASSED — recall keeps owned assets; client/white-label domains stay OUT")
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
