#!/usr/bin/env python3
"""
shodan_recon.py — seed -> identity -> canonical Shodan filters -> findings.

Filters + severity mirror the Colt playbook MDs in reference/. This script AUTOMATES:
  identity resolution (ASN/netblocks/org/domains via RIPEstat + DNS),
  the canonical Top-10 Super Filters, running the scope clauses, classifying, and
  dropping false positives (CDN/shared-host tenants, honeypots).

Seed can be: a domain/URL, an ASN (AS12345), a CIDR (1.2.3.0/24), or a company name.
You can also add/override identity:  --asn AS3320  --net 212.184.104.224/27

Outputs into --outdir: filters.md, findings.json, findings.md.
Prints a machine-readable last line:  RESULT ips=<n> cdn=<true|false> asns=<n>

Usage:
    export SHODAN_API_KEY=xxxx
    python3 shodan_recon.py --seed "keb.de" --outdir /root/work
    python3 shodan_recon.py --seed "KEB Automation" --asn AS3320 --net 212.184.104.224/27 --outdir /root/work
"""
import os, re, sys, json, socket, argparse, datetime, urllib.request, urllib.parse

_SEV_ORDER = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}

UA = {"User-Agent": "colt-shodan-recon/1.2"}
# ISPs/telcos: the assigned netblock IS the target's — net: sweep is valid.
CARRIERS = ("deutsche telekom","telekom","vodafone","telefonica","orange","bt ","gtt",
            "level 3","lumen","init7","1&1","ionos","kpn","swisscom","telia","telefonica")
# CDNs / shared front-ends: the IP is NOT the target's — net:/asn: sweeps return the CDN.
CDNS = ("cloudflare","akamai","fastly","cloudfront","amazon","aws","google","incapsula",
        "imperva","sucuri","edgecast","stackpath","bunny","cdn77","limelight","azure","microsoft",
        "hetzner","ovh","mittwald","leaseweb","digitalocean","hosttech","exoscale","contabo",
        "plusserver","strato","1blu","netcup","gcore","oracle",
        # named from real engagements: these announce large multi-tenant estates
        "ip-projects","ip projects","vcserver","vcserver network","myloc","velia","combahton",
        "df.eu","domainfactory","host europe","hosteurope","all-inkl","alfahosting","goneo",
        "profihost","noris","anexia","artfiles","evanzo","serverloft","webgo","timme","wiit")

def _is(name, tup): return bool(name) and any(t in name.lower() for t in tup)

# ------------------------------------------------------------------ identity ---
def _get_json(url, timeout=15, headers=None):
    # `headers` is additive on top of UA. It was added for CertSpotter's optional API key, and
    # calling this with an argument it did not accept would have raised TypeError INSIDE the
    # caller's own `except Exception`, silently disabling the second CT source with a warning that
    # blamed the network. Read the helper's signature before calling it.
    h = dict(UA)
    if headers:
        h.update(headers)
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))

def _ripe_prefixes(asn, cap=20):
    try:
        d = _get_json(f"https://stat.ripe.net/data/announced-prefixes/data.json?resource={asn}")
        pfx = [p["prefix"] for p in d.get("data", {}).get("prefixes", [])]
        v4 = [p for p in pfx if ":" not in p]; v6 = [p for p in pfx if ":" in p]
        return v4[:cap] + v6[:3]
    except Exception as e:
        print(f"[warn] RIPEstat prefixes {asn}: {e}", file=sys.stderr); return []

def _ripe_holder(asn):
    try:
        return _get_json(f"https://stat.ripe.net/data/as-overview/data.json?resource={asn}").get("data",{}).get("holder")
    except Exception: return None

def _ip_to_asn(ip):
    try:
        data = _get_json(f"https://stat.ripe.net/data/prefix-overview/data.json?resource={ip}").get("data",{})
        asns = data.get("asns", [])
        return (("AS"+str(asns[0]["asn"])) if asns else None,
                data.get("resource"), asns[0].get("holder") if asns else None)
    except Exception as e:
        print(f"[warn] RIPEstat prefix-overview {ip}: {e}", file=sys.stderr); return None, None, None

def _rdap_assignment(ip):
    """Most-specific RIPE RDAP inetnum for an IP (the customer sub-allocation, e.g. a /27),
    NOT the carrier's big announced prefix."""
    try:
        d = _get_json(f"https://rdap.db.ripe.net/ip/{ip}")
        c = (d.get("cidr0_cidrs") or [])
        if c and c[0].get("v4prefix") and c[0].get("length") is not None:
            return f"{c[0]['v4prefix']}/{c[0]['length']}", d.get("name")
        return None, d.get("name")
    except Exception as e:
        print(f"[warn] RDAP {ip}: {e}", file=sys.stderr); return None, None

def _clean_domain(seed):
    s = re.sub(r'(?i)^\w+://', '', seed.strip()).split('/')[0].split('?')[0].split('@')[-1]
    return s.lower().lstrip('.')

import psl as _PSL
import email_auth
import cert_intel
import naming
import active_probe

# Authoritative scope denylist, shared with group_discovery.py. Enforced at the ownership gate
# (_owns_apex) so it covers EVERY source a domain can arrive from -- group structure, certificate
# SAN, CT log, DNS probe or an operator's refine answer -- not just the one path that produced the
# abakus-tk.de failure. Fails OPEN on import error: a missing denylist must not stop assessments,
# and the per-domain contribution budget in run() is the independent backstop.
try:
    from scope_deny import is_denied as _DENY, why_denied as _DENY_WHY
except Exception:                                             # pragma: no cover
    def _DENY(a): return False
    def _DENY_WHY(a): return ""


class ScopeRefused(Exception):
    """The request is well-formed but must not be assessed, and we can say exactly why.

    This is a PRODUCT DECISION surfaced to the operator, not a failure: seeding a public suffix
    (`gov.ru`, `co.uk`) would mix thousands of unrelated organisations into one customer deck — the
    budget.gov.ru incident. Carrying its own type lets run_assessment.py render it as advice with a
    concrete next step, rather than as the generic `assess_error` a real crash produces."""

    def __init__(self, reason, hint="", code="scope_refused"):
        super().__init__(reason)
        self.reason, self.hint, self.code = reason, hint, code


def _apex(d):
    """The REGISTRABLE domain — the unit of ownership. NOT "the last two labels".

    THE budget.gov.ru INCIDENT: this used to be `".".join(p[-2:])`, so `budget.gov.ru` became
    `gov.ru` — and so did duma.gov.ru, nalog.gov.ru, mchs.gov.ru and every other ministry. The
    ownership gate then agreed the entire Russian federal government was one customer: 203 IPs and
    €11-28M of priced risk for a request about ONE budget site. `gov.ru` / `co.uk` / `com.au` are
    PUBLIC SUFFIXES — sharing one means sharing nothing. See psl.py."""
    return _PSL.registrable(d)

CIDR_RE = re.compile(r'^\d{1,3}(\.\d{1,3}){3}/\d{1,2}$')

def resolve_identity(seed, allow_public_suffix=False):
    """`allow_public_suffix=True` = the operator has DELIBERATELY asked for a whole shared zone.

    Refusing outright was wrong: "show me every Russian federal body" is a legitimate request from a
    regulator or a threat researcher. But it is a ZONE SURVEY, not an assessment of one company, and
    the artifact must say so rather than quietly implying a single owner. So: declined by default
    (which catches the typo and the misunderstanding), permitted on an explicit assertion, and the
    result is labelled `zone_survey` all the way through to the deck."""
    ident = {"seed": seed, "asns": [], "nets": [], "org": None, "brand": None,
             "asn_holder": None, "domains": [], "org_is_carrier": False, "org_is_cdn": False, "assignment_netname": None,
             "internal_cas": [], "cert_orgs": [], "jarms": [], "cpes": [], "pinned": []}
    s = seed.strip()
    if re.match(r'(?i)^AS?\d+$', s):                                   # ---- ASN
        asn = "AS" + re.sub(r'(?i)^AS?', '', s); holder = _ripe_holder(asn)
        ident.update(asns=[asn], nets=_ripe_prefixes(asn), asn_holder=holder, brand=holder,
                     org=None if (_is(holder,CARRIERS) or _is(holder,CDNS)) else holder,
                     org_is_carrier=_is(holder,CARRIERS), org_is_cdn=_is(holder,CDNS))
    elif CIDR_RE.match(s):                                             # ---- CIDR
        ident.update(nets=[s], brand=s)
    elif re.search(r'[A-Za-z]', s) and '.' in _clean_domain(s) and ' ' not in s:   # ---- domain/URL
        dom = _clean_domain(s); apex = _apex(dom)
        ident["zone_survey"] = bool(_PSL.is_public_suffix(dom))
        # A PUBLIC SUFFIX IS NOT A CUSTOMER. Seeding `gov.ru`, `co.uk` or `com.au` asks us to assess
        # everything anyone has ever registered under a shared namespace — there is no owner to
        # corroborate against, so every downstream ownership check degenerates and the estate grows
        # without limit. Refuse loudly instead of producing a confident deck about a whole country.
        if _PSL.is_public_suffix(dom) and not allow_public_suffix:
            raise ScopeRefused(
                "%s is a public suffix, not a company — nobody owns it and anyone can register "
                "under it." % dom,
                hint="Give one organisation's own domain (e.g. budget.%s) for a normal assessment. "
                     "If you deliberately want the WHOLE zone — every body registered under %s — "
                     "re-run with 'Survey the whole zone' enabled: you will get a ZONE SURVEY, "
                     "clearly labelled as many independent organisations rather than one customer."
                     % (dom, dom),
                code="public_suffix")
        ident["domains"] = sorted({dom, apex}); ident["brand"] = apex
        try:
            ip = socket.gethostbyname(dom); ident["seed_ip"] = ip
            asn, prefix, holder = _ip_to_asn(ip)
            if asn:
                ident["asn_holder"] = holder
                ident["org_is_carrier"] = _is(holder,CARRIERS); ident["org_is_cdn"] = _is(holder,CDNS)
                # ---- OWNERSHIP GATE ON THE SEED'S OWN ASN (the rightmart.de collapse, 2026-07) ----
                # The ASN that announces the seed's IP belongs to whoever HOSTS the seed. Adopting it
                # is only safe when its holder corroborates the target's brand. rightmart.de sits in
                # AS48314 (IP-Projects, ~130 prefixes): the old CDN/CARRIER check did not list that
                # hoster, so 24 of ITS prefixes were swept as if rightmart owned them — which is
                # where all 1,417 "in scope" IPs and all 78 evidence IPs came from.
                _prefs = _ripe_prefixes(asn)
                _owned = _org_is_the_target(holder, apex) and not _looks_like_provider(holder, len(_prefs))
                if not _owned:
                    ident.setdefault("shared_asns", []).append(asn)
                    ident["org_is_cdn"] = True      # reuse the proven "cert/hostname only" path
                    ident["org"] = None
                    print("[auto] ASN %s holder %r does NOT corroborate the seed brand %r — treating "
                          "it as PROVIDER space. Not an ownership anchor; scope falls back to pinned "
                          "hosts + cert/hostname identity (%d prefixes NOT swept)."
                          % (asn, str(holder)[:60], apex, len(_prefs)), file=sys.stderr)
                elif ident["org_is_cdn"]:
                    ident["asns"].append(asn)
                    pass                                   # CDN: rely on cert/hostname only
                elif ident["org_is_carrier"]:
                    ident["asns"].append(asn)
                    # carrier: announced prefixes are the CARRIER's — use the RDAP assignment (the /27)
                    cidr, netname = _rdap_assignment(ip)
                    if cidr: ident["nets"] = [cidr]; ident["assignment_netname"] = netname
                    elif prefix: ident["nets"] = [prefix]
                elif _owned:
                    ident["asns"].append(asn)
                    nets = list(_prefs)
                    if prefix and prefix not in nets: nets = [prefix] + nets
                    ident["nets"] = nets
                if _owned:
                    ident["org"] = None if (ident["org_is_carrier"] or ident["org_is_cdn"]) else holder
        except Exception as e:
            print(f"[warn] DNS resolve {dom}: {e}", file=sys.stderr)
    else:                                                             # ---- org name
        ident["org"] = s; ident["brand"] = s
    return ident

def _dedupe_lead(name):
    """'COLT COLT Technology Services Group Limited' -> 'COLT Technology Services Group Limited'.

    Registries store an ASN HANDLE ("COLT") and an org NAME ("Colt Technology Services Group
    Limited"); joined, the leading token repeats. It is the first line of the title slide, so a
    duplicated word reads as a defect. Case-insensitive, and only ever removes an EXACT repeat of
    the first word — "Colt Colt" collapses, "New New York" would too, and nothing else is touched.
    """
    parts = str(name or "").split()
    while len(parts) > 1 and parts[0].lower() == parts[1].lower():
        parts.pop(0)
    return " ".join(parts)


def company_name(ident):
    return _dedupe_lead(ident.get("brand") or ident.get("org")
                        or ident.get("asn_holder") or ident["seed"])

def merge_variants(ident, orgs=None, brands=None, domains=None, favicons=None,
                   issuers=None, cert_orgs=None, jarms=None, cpes=None):
    """Fold in org-name / brand / domain / favicon / internal-CA / cert-org / JARM / CPE variants
    (playbook Part 2 §1-§4) so recon searches the target's IDENTITY across ALL ASNs, not just the
    seed ASN's sweep. The internal-CA issuer pivot is the single most productive of these."""
    orgs = orgs or []; brands = brands or []; domains = domains or []; favicons = favicons or []
    issuers = issuers or []; cert_orgs = cert_orgs or []; jarms = jarms or []; cpes = cpes or []
    base_o = [ident["org"]] if ident.get("org") else []
    ident["org_variants"] = list(dict.fromkeys([o for o in (base_o + orgs) if o]))
    base_b = [ident["brand"]] if ident.get("brand") else []
    ident["brand_variants"] = list(dict.fromkeys([b for b in (base_b + brands) if b]))
    for d in domains:
        dd = _clean_domain(d)
        if dd and dd not in ident["domains"]: ident["domains"].append(dd)
    ident["favicons"] = list(dict.fromkeys([str(h).strip() for h in favicons if str(h).strip()]))
    ident["internal_cas"] = list(dict.fromkeys([str(c).strip() for c in issuers if str(c).strip()]))
    ident["cert_orgs"]    = list(dict.fromkeys([str(o).strip() for o in cert_orgs if str(o).strip()]))
    ident["jarms"]        = list(dict.fromkeys([str(j).strip() for j in jarms if str(j).strip()]))
    ident["cpes"]         = list(dict.fromkeys([str(p).strip() for p in cpes if str(p).strip()]))
    return ident

# ------------------------------------------------------------ auto-discovery ---
# KISS: from ONE input (a company name or domain) resolve the whole recon anchor block.
PUBLIC_CAS = ("let's encrypt","digicert","globalsign","sectigo","comodo","entrust","godaddy",
              "amazon","google trust","microsoft","cloudflare","actalis","buypass","zerossl",
              "starfield","geotrust","thawte","rapidssl","certum","ssl.com","isrg","baltimore",
              "quovadis","identrust","d-trust","t-systems","telesec","swisssign","letsencrypt",
              # --- opaque intermediates, spelled out (see _private_ca_ok for the STRUCTURAL guard) ---
              # Let's Encrypt issues under bare codes R3/R10..R14, E1..E9; Google Trust Services under
              # WR1..WR4/WE1../YR1../YE1..  None of these strings contain a vendor name, so the
              # substring test above cannot see them. bibeltv.de: 'R12' + 'YR2' were mistaken for the
              # customer's PRIVATE CA and pivoted on -> 998 unrelated hosts worldwide in the deck.
              "gts ca","gts root","google internet authority","apple public","e-tugra","hydrant",
              "trustasia","wotrus","xinnet","secure site","encryption everywhere","cpanel, inc",
              "cpanel","plesk","sni.cloudflaressl","alphassl","firebase","vercel","netlify","fastly")

# A public intermediate's CN is typically a short opaque code: R3, R10, R12, E5, WR1, WE1, YR2, X1.
# A genuine private/enterprise CA is named after the organisation ("Bibel TV Issuing CA 01").
_OPAQUE_CA_RE = re.compile(r"^[A-Za-z]{1,3}[0-9]{0,4}$")
_CA_WORDS = ("ca", "certificate", "cert", "issuing", "root", "intermediate", "pki",
             "authority", "trust", "sub-ca", "subca", "zertifi")
# A private CA signs an estate (tens/hundreds of hosts). Anything signing more of the internet than
# this is by definition shared, whoever it belongs to.
PIVOT_MAX_HOSTS = int(os.environ.get("PIVOT_MAX_HOSTS", "2000"))


def _brand_tokens(ident):
    """Distinctive lowercase tokens for the target: brand, org, seed and apex domains."""
    out = set()
    vals = [ident.get("brand"), ident.get("org"), ident.get("seed")]
    vals += list(ident.get("domains") or [])
    vals += list(ident.get("org_variants") or []) + list(ident.get("brand_variants") or [])
    for v in vals:
        if not v:
            continue
        s = str(v).lower()
        s = re.sub(r"\.(com|net|org|de|ch|at|io|ai|eu|co|uk|fr|it|es|nl|se|pl)$", "", s)
        for t in re.split(r"[^a-z0-9]+", s):
            # drop legal-form noise and anything too short to be distinctive
            if len(t) > 3 and t not in ("gmbh", "corp", "inc", "ltd", "group", "holding", "www",
                                        "the", "and", "company", "co", "ag", "se", "plc", "bv"):
                out.add(t)
    return out


def _private_ca_ok(cn, ident, api=None):
    """Is this issuer CN plausibly the TARGET'S OWN private CA?  -> (bool, reason)

    THE BIBELTV.DE INCIDENT: 'R12' (Let's Encrypt) and 'YR2' (Google Trust Services) passed the
    PUBLIC_CAS substring test, because those CNs contain no vendor name. The pivot then ran
    `ssl.cert.issuer.cn:"R12"` against ALL of Shodan and adopted 998 unrelated hosts — cPanel
    resellers in Brazil, Shopify, DigitalOcean droplets in Japan — as the customer's estate.

    This gate FAILS CLOSED: an issuer we cannot positively justify is refused. A missed pivot costs
    us some recall; a wrong pivot puts a stranger's infrastructure in a customer-facing deck.
    """
    cn = (cn or "").strip()
    if not cn:
        return False, "empty CN"
    # NO BRAND TOKENS -> NO PIVOT. budget.gov.ru produced `brand tokens: (none)` (the seed apex was
    # wrongly `gov.ru` and `gov` is legal-form noise), and with nothing to corroborate against, the
    # rarity test alone let 'Russian Trusted Sub CA' through — a NATIONAL certificate authority that
    # signs the whole federal government. Rarity is not ownership: an issuer can be rare in Shodan's
    # index and still belong to somebody else entirely. When we hold no distinctive token for the
    # target, every downstream corroboration check is a no-op, so the honest answer is to widen
    # nothing at all. Fail closed.
    if not _brand_tokens(ident):
        return False, "no brand token known for the target — cannot corroborate any pivot"
    if _is(cn, PUBLIC_CAS):
        return False, "known public CA"
    if _OPAQUE_CA_RE.match(cn):
        return False, "opaque short code (public intermediate, e.g. R12/YR2/WE1)"
    if len(cn) < 6:
        return False, "CN too short to name an organisation"
    low = cn.lower()
    # Compare brand tokens against a SQUASHED CN: an internal CA is written "Bibel TV Issuing CA 01"
    # while the brand token is "bibeltv". Without stripping separators the two never match, and the
    # gate would fall back to CA-wording — which every public CA also has.
    squash = re.sub(r"[^a-z0-9]", "", low)
    owns = any(t in squash for t in _brand_tokens(ident))
    looks_ca = any(w in low for w in _CA_WORDS)
    if not (owns or looks_ca):
        return False, "no brand token and no CA wording"
    # The decisive, vendor-agnostic test: how much of the internet does this issuer actually sign?
    rarity_ok = False
    if api is not None:
        try:
            n = int((api.count('ssl.cert.issuer.cn:"%s"' % cn) or {}).get("total", 0))
            if n > PIVOT_MAX_HOSTS:
                return False, "signs %d hosts globally (> %d) — shared, not private" % (n, PIVOT_MAX_HOSTS)
            rarity_ok = True
        except Exception:
            rarity_ok = False          # quota/plan/network — treated exactly like "no api"
    if not rarity_ok and not owns:
        # We could not prove the issuer is rare AND it does not carry the customer's own name.
        # CA-wording alone is not evidence. Refuse: a wrong pivot is far worse than a missed one.
        return False, "rarity check unavailable and CN carries no brand token"
    return True, "ok"


def _corroborates(m, ident, own_asns):
    """Does this Shodan match plausibly belong to the target, independent of the pivot that found it?
    Defence in depth: even a genuine private CA must not silently import hosts we cannot tie back."""
    masn = ("AS" + str(m.get("asn"))) if str(m.get("asn") or "").isdigit() else (m.get("asn") or "")
    if own_asns and masn in own_asns:
        return True
    doms = [str(d).lower().lstrip(".") for d in (ident.get("domains") or []) if d]
    hay = " ".join([str(h).lower() for h in (m.get("hostnames") or [])])
    ssl = (m.get("ssl") or {}).get("cert") or {}
    subj = ssl.get("subject") or {}
    hay += " " + str(subj.get("CN", "")).lower() + " " + str(subj.get("O", "")).lower()
    for alt in ((m.get("ssl") or {}).get("cert", {}).get("extensions") or []):
        hay += " " + str(alt.get("data", "")).lower()
    if any(d and (d in hay) for d in doms):
        return True
    toks = _brand_tokens(ident)
    org = ((m.get("org") or "") + " " + (m.get("isp") or "")).lower()
    return bool(toks) and any(t in org for t in toks)

def _bgpview_asns(term, cap=12):
    """Company name -> ASNs (bgp.he.net-equivalent, via the bgpview.io JSON API)."""
    try:
        d = _get_json("https://api.bgpview.io/search?query_term=" + urllib.parse.quote(term), timeout=20)
        toks = [t for t in re.split(r'\W+', term.lower()) if len(t) > 2]
        out = []
        for a in (d.get("data", {}) or {}).get("asns", []):
            nm = ((a.get("name") or "") + " " + (a.get("description") or "")).lower()
            if any(t in nm for t in toks):
                out.append("AS" + str(a["asn"]))
        return list(dict.fromkeys(out))[:cap]
    except Exception as e:
        print(f"[warn] bgpview {term}: {e}", file=sys.stderr); return []

# Subdomains worth a direct DNS lookup on a shared-hosting target. For Bibel TV the whole estate
# that matters — gitlab, vpn, mail — lives on names like these, and CT-log enumeration missed all of
# it because crt.sh was down. One DNS query each, passive, ~1s for the whole list.
PROBE_SUBS = (
    "www", "gitlab", "git", "vpn", "mail", "smtp", "imap", "webmail", "owa", "autodiscover",
    "autoconfig", "ftp", "sftp", "remote", "portal", "sso", "auth", "id", "api", "dev", "test",
    "staging", "stage", "admin", "intranet", "extranet", "cloud", "nextcloud", "jira", "confluence",
    "wiki", "ci", "jenkins", "build", "registry", "docker", "vpn2", "fw", "firewall", "rdp", "ts",
    "citrix", "exchange", "lync", "teams", "share", "files", "backup", "monitor", "grafana",
    "status", "cdn", "static", "media", "img", "video", "stream", "live", "shop", "app", "my",
)


def _resolve(name):
    """A/AAAA for a hostname, or [] — passive DNS only."""
    out = []
    try:
        for fam, _, _, _, sa in socket.getaddrinfo(name, None):
            ip = sa[0]
            if ip not in out:
                out.append(ip)
    except Exception:
        pass
    return out


# A probed subdomain that CNAMEs into one of these is a SaaS TENANCY, not a host the customer owns.
# THE ABAKUS-TK.DE FAILURE (2026-08): the DNS probe resolved autodiscover./webmail./exchange./auth.
# — all CNAMEd into Microsoft 365 — and PINNED the answers. Pinned hosts deliberately bypass the
# CDN/hoster drop in run() (that exemption exists so a legitimately-pinned S-KON host on shared
# infrastructure is not discarded), so Microsoft's shared Exchange Online front ends (52.98.x.x,
# 40.99.x.x) entered scope as "the customer's own hosts" and dragged in every co-tenant on them.
# The customer's DNS pointing at Microsoft means THEY USE MICROSOFT. It is not an address they own,
# nobody can remediate it, and anything observed on it belongs to millions of other tenants.
SAAS_CNAME = (
    "outlook.com", "office.com", "office365.com", "microsoft.com", "microsoftonline.com",
    "lync.com", "skypeforbusiness.com", "sharepoint.com", "onmicrosoft.com", "azurefd.net",
    "trafficmanager.net", "azureedge.net", "windows.net",
    "google.com", "googlemail.com", "googlehosted.com", "ghs.google.com", "googleusercontent.com",
    "zoho.eu", "zoho.com", "zohohost.com", "zohomail.eu",
    "mailgun.org", "sendgrid.net", "mandrillapp.com", "pphosted.com", "mimecast.com",
    "hornetsecurity.com", "retarus.com", "nospamproxy.de", "securemail.de",
    "salesforce.com", "force.com", "hubspot.net", "zendesk.com", "freshdesk.com",
    "cloudflare.net", "akamaiedge.net", "akamai.net", "edgekey.net", "edgesuite.net",
    "cloudfront.net", "awsglobalaccelerator.com", "elb.amazonaws.com",
    "wixdns.net", "squarespace.com", "shopify.com", "myshopify.com", "webflow.io",
)


def _caa(domain):
    """CAA records for a domain via DoH, or None if the lookup FAILED.

    [] means "queried successfully, no CAA published" -- a real finding.
    None means "could not ask" -- never a finding (absence of evidence is never a finding).
    Python's stdlib resolver cannot query type 257, so this goes over DNS-over-HTTPS, which the
    engine already uses elsewhere and which works from inside the container.
    """
    try:
        j = _get_json("https://dns.google/resolve?name=%s&type=CAA"
                      % urllib.parse.quote(str(domain)), timeout=8)
    except Exception:
        return None
    if not isinstance(j, dict) or "Status" not in j:
        return None
    if int(j.get("Status", -1)) != 0:
        return None
    return [a.get("data", "") for a in (j.get("Answer") or []) if a.get("type") == 257]


def _mx(domain):
    """MX hostnames for a domain, or [] on any failure.

    ADDED BECAUSE I ASSUMED THE KEY EXISTED. The Exchange check was written against
    `ident["mx"]`, which nothing in this codebase has ever set -- the fifth time in this workstream
    that I referenced a key or a signature without reading it first. The corroboration would have
    silently fallen back to its other two paths and nobody would have noticed. Read the data, or
    create it.

    One DoH query, no packets to the target.
    """
    try:
        j = _get_json("https://dns.google/resolve?name=%s&type=MX"
                      % urllib.parse.quote(str(domain)), timeout=8)
    except Exception:
        return []
    if not isinstance(j, dict) or int(j.get("Status", -1)) != 0:
        return []
    out = []
    for a in (j.get("Answer") or []):
        if a.get("type") != 15:
            continue
        # "10 mail.example.com." -> mail.example.com
        parts = str(a.get("data") or "").split()
        if parts:
            out.append(parts[-1].rstrip(".").lower())
    return out


def _cname_chain(name):
    """The CNAME aliases a hostname resolves through, lowercased. [] on any failure.

    getaddrinfo() throws the chain away, which is precisely the information needed to tell
    'a host we own' from 'a SaaS tenancy we rent'."""
    try:
        _canon, aliases, _ips = socket.gethostbyname_ex(name)
        out = [str(_canon or "").lower().rstrip(".")]
        out += [str(a).lower().rstrip(".") for a in (aliases or [])]
        return [a for a in out if a and a != str(name).lower()]
    except Exception:
        return []


def _is_saas_tenancy(name):
    """True if this hostname is a tenancy on somebody else's SaaS platform -> never pin its IPs."""
    for c in _cname_chain(name):
        if any(c == s or c.endswith("." + s) for s in SAAS_CNAME):
            return True
    return False


def _probe_subdomains(domains, cap=120):
    """Resolve a curated subdomain list against each known domain.

    WHY THIS EXISTS (bibeltv.de): crt.sh failed on three consecutive runs (timeout, 404, 503) and it
    was the ONLY source of subdomains, so the engine never saw gitlab.bibel.tv or vpn.bibeltv.de —
    the two most valuable hosts in the estate. DNS is a second, independent source that cannot be
    taken out by one flaky service, and a name that RESOLVES is proof the host exists."""
    found = {}
    for d in list(domains)[:4]:                       # apexes only; keep the query count sane
        d = str(d).lower().lstrip(".")
        for sub in PROBE_SUBS:
            fqdn = sub + "." + d
            ips = _resolve(fqdn)
            if ips:
                found[fqdn] = ips
            if len(found) >= cap:
                break
    if found:
        print("[auto] dns probe: %d live subdomain(s): %s" %
              (len(found), ", ".join(sorted(found)[:8]) + (" ..." if len(found) > 8 else "")),
              file=sys.stderr)
    return found


# CertSpotter's free tier is rate-limited per hour for unauthenticated callers. Paging multiplies
# requests, so it is bounded. Set CERTSPOTTER_TOKEN to raise the limit (SSLMate API key).
CERTSPOTTER_PAGES = int(os.environ.get("CERTSPOTTER_PAGES", "6"))


def _certspotter_issuances(domain, max_pages=None):
    """Every UNEXPIRED CT issuance for a domain and its subdomains, with the issuer expanded.

    WHY PAGING IS NOT OPTIONAL, and why the previous version quietly lost recall: SSLMate's
    documentation is explicit that "if the after parameter is empty or omitted, the API will
    return the LEAST-recently-discovered issuances". So a single call plus [:200] returned the
    OLDEST 200 certificates of the estate -- the exact opposite of what a recon step wants. On a
    domain with more than one page of history the recently-issued names, which are the live hosts,
    were never seen at all. Page with `after=<last id>` until an empty array comes back.

    The endpoint returns only UNEXPIRED issuances, so this is a view of the CURRENT certificate
    estate, not an archive. That matters for what may honestly be claimed from it.

    expand=issuer.caa_domains is the field SSLMate provides precisely so a caller can compare an
    issuer against the domain's CAA record set. It is what makes the unauthorised-issuance check
    possible without a paid monitoring product.
    """
    pages = CERTSPOTTER_PAGES if max_pages is None else max_pages
    tok = os.environ.get("CERTSPOTTER_TOKEN", "").strip()
    base = ("https://api.certspotter.com/v1/issuances?domain=" + urllib.parse.quote(domain) +
            "&include_subdomains=true&expand=dns_names&expand=issuer&expand=issuer.caa_domains")
    out, after = [], None
    for _ in range(max(1, pages)):
        u = base + ("&after=" + urllib.parse.quote(str(after)) if after else "")
        try:
            rows = _get_json(u, timeout=25, headers=({"Authorization": "Bearer " + tok} if tok else None))
        except Exception as e:
            print(f"[warn] certspotter {domain}: {e}", file=sys.stderr)
            break
        if not isinstance(rows, list) or not rows:
            break
        out.extend(r for r in rows if isinstance(r, dict))
        after = rows[-1].get("id")
        if not after:
            break
    return out


def _certspotter_domains(domain, cap=200):
    """CT via SSLMate's CertSpotter -- free, no API key. A SECOND CT source so one outage cannot
    blind the whole assessment (crt.sh returned timeout/404/503 on three consecutive bibeltv runs).
    Names only; _certspotter_issuances() is the one that talks to the API."""
    out = set()
    for row in _certspotter_issuances(domain):
        for nm in (row.get("dns_names") or []):
            nm = str(nm).strip().lstrip("*.").lower()
            if nm and "." in nm and " " not in nm:
                out.add(nm)
        if len(out) >= cap:
            break
    return out


def _caa_issuers(records):
    """The CA domains a CAA record set AUTHORISES, from the issue/issuewild tags.

    A record looks like `0 issue "letsencrypt.org"`, and may carry parameters after a semicolon
    (`"letsencrypt.org; validationmethods=dns-01"`). The special value `;` means NO certificate
    authority is authorised. `iodef` is a reporting address, not an issuer, and must not be read
    as one. Returns (issue_set, issuewild_set) lowercased.
    """
    issue, wild = set(), set()
    for rec in (records or []):
        txt = str(rec or "").strip()
        m = re.match(r'^\s*\d+\s+(issue|issuewild|iodef)\s+"?([^"]*)"?\s*$', txt, re.I)
        if not m:
            continue
        tag, val = m.group(1).lower(), m.group(2).strip()
        if tag == "iodef":
            continue
        val = val.split(";")[0].strip().lower().rstrip(".")
        target = wild if tag == "issuewild" else issue
        target.add(val)          # "" (from a bare ";") means: authorise nobody
    return issue, wild


def _unauthorised_issuances(domain, issuances, caa_records, caa_of=None):
    """Live certificates whose issuer is NOT authorised by the domain's own CAA record.

    This is the check CAA exists to make possible, and SSLMate publishes `issuer.caa_domains`
    specifically so it can be made. A certificate outside the policy is either a mis-issuance or,
    far more often, a real and useful finding: somebody inside the organisation bought a
    certificate for a company name outside the process that everyone believes is mandatory.

    IT FAILS CLOSED IN FOUR PLACES, because a false accusation of mis-issuance is the worst thing
    this engine could put in a customer deck:
      · no CAA published        -> nothing is authorised OR unauthorised. That is the no_caa
                                   finding instead. Return nothing here.
      · CAA lookup failed       -> caller passes None. Absence of evidence is never a finding.
      · issuer.caa_domains null -> SSLMate does not know who this issuer is authorised as. Skip
                                   the issuance rather than guess.
      · a SUBDOMAIN with its own CAA -> CAA is resolved at the closest name, so a subdomain may
                                   legitimately authorise a different CA than the apex. Each
                                   candidate is re-checked against its own name's CAA before it
                                   is reported. `caa_of` is injected for testing.
    """
    if caa_records is None or not caa_records:
        return []
    issue, wild = _caa_issuers(caa_records)
    if not (issue | wild):
        return []
    lookup = caa_of or _caa
    out, rechecked = [], {}
    for row in issuances:
        allowed = (row.get("issuer") or {}).get("caa_domains")
        if not allowed:                       # null/absent -> no claim
            continue
        names = [str(n).strip().lower().rstrip(".") for n in (row.get("dns_names") or []) if n]
        if not names:
            continue
        wanted = wild if any(n.startswith("*.") for n in names) else issue
        allowed_l = {str(a).strip().lower().rstrip(".") for a in allowed}
        if allowed_l & (wanted or issue):
            continue                          # authorised at the apex

        # The apex says no. Before claiming anything, ask whether a closer name authorises it --
        # CAA is resolved at the closest label with a record, so this is not an edge case.
        ok_closer = False
        for n in names:
            base = n.lstrip("*.")
            if base == domain or not base.endswith("." + domain):
                continue
            if base not in rechecked:
                rechecked[base] = lookup(base)
            recs = rechecked[base]
            if recs is None:                  # could not ask -> do not accuse
                ok_closer = True
                break
            if recs:
                i2, w2 = _caa_issuers(recs)
                if allowed_l & ((w2 if base.startswith("*.") else i2) or i2):
                    ok_closer = True
                    break
        if ok_closer:
            continue
        out.append({"names": sorted(names)[:6],
                    "issuer": str((row.get("issuer") or {}).get("friendly_name") or "unknown"),
                    "not_before": str(row.get("not_before") or ""),
                    "not_after": str(row.get("not_after") or ""),
                    "authorised": sorted(allowed_l)[:4]})

    # BLAST-RADIUS GUARD, same doctrine as the co-tenant guard and the FP auditor.
    # If EVERY live certificate is "unauthorised", the overwhelmingly likelier explanation is that
    # the CAA record itself is wrong or was added after the certificates -- `0 issue ";"` (authorise
    # nobody) is a common misconfiguration and would flag the entire estate. Claiming N
    # mis-issuances there would be spectacularly wrong in a customer deck. The condition is still
    # reported, but as a CAA-policy problem, which is what it almost always is.
    considered = [r for r in issuances if (r.get("issuer") or {}).get("caa_domains")]
    if considered and len(out) == len(considered) and len(considered) > 1:
        return [{"policy_conflict": True, "count": len(out),
                 "issuers": sorted({o["issuer"] for o in out})[:6],
                 "authorised": sorted(issue | wild)[:4]}]
    return out


def _crtsh_domains(domain=None, org=None, cap=60):
    """CT-log harvest -> brand domains & subdomains on any cloud/CDN.
    Two independent sources (crt.sh + CertSpotter); either alone is a single point of failure."""
    doms = set(); urls = []
    if domain: urls.append("https://crt.sh/?q=%25." + urllib.parse.quote(domain) + "&output=json")
    if org:    urls.append("https://crt.sh/?O=" + urllib.parse.quote(org) + "&output=json")
    for u in urls:
        try:
            for row in (_get_json(u, timeout=30) or [])[:500]:
                for nm in (row.get("name_value", "") or "").split("\n"):
                    nm = nm.strip().lstrip("*.").lower()
                    if nm and "." in nm and " " not in nm and not nm.endswith(".arpa"):
                        doms.add(nm)
        except Exception as e:
            print(f"[warn] crt.sh {u}: {e}", file=sys.stderr)
    if domain:
        before = len(doms)
        doms |= _certspotter_domains(domain)
        if len(doms) > before:
            print("[auto] certspotter added %d name(s) crt.sh did not return"
                  % (len(doms) - before), file=sys.stderr)
    return sorted(doms)[:cap]

def _cert_info(domain, port=443):
    """(SAN list, subject-Organization) from the host's live TLS certificate. One handshake."""
    import ssl as _ssl
    for host in (domain, "www." + domain):
        try:
            ctx = _ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = _ssl.CERT_NONE
            with socket.create_connection((host, port), timeout=8) as s:
                with ctx.wrap_socket(s, server_hostname=host) as ss:
                    cert = ss.getpeercert()
            sans = set()
            for typ, val in (cert or {}).get("subjectAltName", ()):
                if typ.lower() == "dns":
                    v = str(val).strip().lstrip("*.").lower()
                    if v and "." in v and " " not in v:
                        sans.add(v)
            org = None
            for rdn in (cert or {}).get("subject", ()):
                for k, v in rdn:
                    if k in ("organizationName", "O") and v:
                        org = v
            if sans or org:
                return sorted(sans), org
        except Exception:
            continue
    return [], None


def _cert_sans(domain, port=443, cap=80):
    return _cert_info(domain, port)[0][:cap]


# White-label / microsite prefixes. On a THIRD-PARTY apex these are a client's brand, not the
# target's — S-KON runs `vorteile.otto.de`, `praemie.tng.de`, `aktion.eam.de` FOR its clients, and
# their exposures are the client's attack surface, never S-KON's. Hard-exclude them unless the apex
# itself carries the target's brand.
_MICROSITE_PREFIXES = ("vorteile", "vorteil", "praemie", "prämie", "aktion", "bonus", "vorteilswelt",
                       "rewards", "loyalty", "kampagne", "campaign", "promo")


def _owns_apex(apex, brand_tokens, seed_apex, group_domains=None, structure_known=False):
    """Is this registrable apex plausibly the TARGET'S OWN domain?  -> (bool, reason)

    THE S-KON INCIDENT: the domain-discovery step (CertSpotter + DNS probe + cert SANs) pulled in
    every client domain of a loyalty-platform operator — vorteile.otto.de, vorteile.mediamarkt.de,
    praemie.tng.de, ...  — and pinned their ISP IPs, producing 746 hosts (718 of them on the
    clients' ISPs TNG/DNS:NET) for a customer with 2 real hosts. A discovered domain is a CANDIDATE,
    not proof of ownership. Fail closed: include only what carries the target's identity."""
    apex = (apex or "").lower().strip(".")
    if not apex:
        return False, "empty"
    if apex == (seed_apex or "").lower():
        return True, "seed apex"
    # THE ABAKUS-TK.DE GATE (2026-08). This runs AFTER the seed check -- a media or social company
    # can legitimately BE the customer -- but BEFORE everything else, including the group-structure
    # assertion below. That order is the whole point: `wa.me` reached scope because group discovery
    # asserted ownership and _owns_apex then DEFERRED to that assertion, which is circular. Shared
    # infrastructure operated for millions of unrelated parties is never the customer's, no matter
    # which discovery step vouched for it.
    if _DENY(apex):
        return False, "shared infrastructure, never a customer asset (%s)" % (_DENY_WHY(apex) or "denied")
    # THE ANGERMANN FIX (recall). A brand token can only ever find domains that SPELL the brand, so
    # netbid.com / nordleasing.com / leaseback.de / buerosuche.de were structurally unreachable from
    # seed angermann.de — and they held the best findings in the engagement. group_domains comes from
    # group_discovery.py: domains the customer's OWN group-structure page links to. That is a
    # first-party assertion of ownership and is STRONGER evidence than a string match, so it is
    # checked first.
    if apex in set(group_domains or ()):
        return True, "named on the customer's own group-structure page"
    # A group publishes one TLD and often operates others: angermann.de's structure page names
    # netbid.com, while the group's MAIL cluster (expired cert on 7 ports - the best finding in the
    # engagement) lives on netbid.io. Same registrable LABEL, different TLD. Matched EXACTLY, so
    # "netbid-fake.com" (label netbid-fake) can never qualify.
    _lab = apex.split(".")[0]
    for _g in (group_domains or ()):
        if _lab and _lab == str(_g).split(".")[0]:
            return True, "sibling TLD of the published group domain %s" % _g
    squash = re.sub(r"[^a-z0-9]", "", apex.split(".")[0])   # the registrable label, separators removed
    for t in brand_tokens:
        if t and len(t) >= 4 and t in squash:
            # THE ANGERMANN FIX (precision). "Angermann" is a SURNAME, so the token also matches a
            # law firm (ra-angermann.de), renner-angermann.de, a web agency and a DENTAL PRACTICE.
            # When the customer has PUBLISHED its group structure we have an authoritative roster of
            # its companies — and a lookalike apex absent from that roster is positive evidence it is
            # someone else's, not merely missing evidence. So it becomes a CANDIDATE the operator
            # confirms (clarify.py), never an auto-scoped host. If no structure page was found we
            # know nothing extra, so the historic brand-token behaviour is left exactly as it was
            # (this is what keeps the S-KON kontor-token recall intact).
            if structure_known:
                return False, ("lookalike: token %r but absent from the customer's published group "
                               "structure - needs operator confirmation" % t)
            return True, "brand token %r" % t
    return False, "third-party apex (no brand token, not in the published group structure)"


# Vendor/SaaS domains where the customer is a TENANT: the apex belongs to the vendor but a
# subdomain labelled with the brand is unambiguously the customer's own service instance.
# angermann.de's 3CX phone system lives at angermann.3cx.eu on netcup — the certificate names it
# outright, yet _owns_apex rejected it because the apex (3cx.eu) is 3CX's, not Angermann's. An
# exposed 3CX management interface is a first-rank finding (CVE-2023-29059 supply-chain attack),
# so losing it is expensive. Same shape: <brand>.sharepoint.com, <brand>.zoom.us, <brand>.myshopify.com.
TENANT_APEX = (
    "3cx.eu", "3cx.us", "3cx.com.au", "my3cx.com",
    "sharepoint.com", "onmicrosoft.com", "zoom.us", "atlassian.net", "myshopify.com",
    "zendesk.com", "freshdesk.com", "service-now.com", "salesforce.com", "force.com",
    "hubspotpagebuilder.com", "sitecore.net", "cloudapp.azure.com", "azurewebsites.net",
    "elasticbeanstalk.com", "herokuapp.com", "netlify.app", "vercel.app", "web.app",
    "firebaseapp.com", "github.io", "gitlab.io", "bitbucket.io", "wixsite.com",
)

# DELIBERATELY EXCLUDED from TENANT_APEX: consumer dynamic-DNS (dyndns.org, ddns.net, no-ip.org,
# goip.de, synology.me, quickconnect.to). Anyone can register ANY label there, so the label carries
# no ownership signal whatsoever. Including them admitted 79.214.82.129 —
# cert CN praxisangermann.dyndns.org, O "Zahnarztpraxis Angermann" — a DENTAL PRACTICE on a Telekom
# dynamic IP, into a commercial property group's attack surface.


def _owns_host(fqdn, brand_tokens, seed_apex, group_domains=None, structure_known=False):
    """Ownership for a FULL hostname, not just its registrable apex. -> (bool, reason)

    Needed because a vendor-hosted tenant carries the brand in the LEFTMOST LABEL while the apex
    belongs to the vendor. Deliberately narrow: the label must carry a brand token AND the apex must
    be a KNOWN multi-tenant vendor domain, so this can never widen scope to a random third party.
    """
    low = (fqdn or "").strip().lower().rstrip(".")
    if not low or "." not in low:
        return False, "empty"
    ap = _apex(low)
    ok, why = _owns_apex(ap, brand_tokens, seed_apex, group_domains, structure_known)
    if ok:
        return True, why
    if ap in TENANT_APEX or any(ap.endswith("." + t) or ap == t for t in TENANT_APEX):
        # EXACT label match only. A substring test admitted "praxisangermann" (a dentist) because it
        # contains "angermann". A vendor provisions the tenant subdomain as the customer's name, so
        # equality is the correct test and it costs no real recall.
        label = re.sub(r"[^a-z0-9]", "", low.split(".")[0])
        for t in brand_tokens:
            if t and len(t) >= 4 and t == label:
                return True, "brand %r is the tenant label on vendor domain %s" % (t, ap)
    return False, why


# Legal-form suffixes to strip when building an `org:` filter. The S-KON WatchGuard was MISSED
# because cybergod queried org:"S-KON Sales Kontor Hamburg GmbH" while Shodan stores the netblock
# whois-org as "S-KON SALES KONTOR HAMBURG AG" — the wrong suffix meant zero matches. Stripping the
# suffix makes org:"S-KON Sales Kontor Hamburg" match every legal-form variant (GmbH/AG/KG/SE...).
_LEGAL_SUFFIX = re.compile(
    r"\s*(?:\b(?:gmbh(?:\s*&\s*co\.?\s*kg)?|ag|kg|se|mbh|ohg|ug|e\.?v|"
    r"ltd|limited|inc|incorporated|llc|l\.?l\.?c|plc|corp|corporation|co|company|"
    r"bv|nv|sarl|s\.?a\.?r\.?l|srl|sas|s\.?p\.?a|oy|ab|a\/s|as|holding|group)\.?\s*)+$",
    re.I)


# A whois org field very often carries a POSTAL ADDRESS after the company name:
#     "Lotto24 AG Hamburg, Germany"
# _LEGAL_SUFFIX is anchored with $, so it strips nothing here (the string ends in "Germany") and the
# CITY AND COUNTRY were shipped to Shodan as the identity anchor. `org:` is a full-text match, not a
# string equality, so org:"Lotto24 AG Hamburg, Germany" matched every Hamburg-registered netblock:
# +381 hosts on an estate whose identity queries had proved 15. That is the lotto24.de failure.
#
# THE DISCRIMINATOR IS POSITIONAL, and it is a property of how companies are registered, not a
# heuristic: in a registered name the legal form comes LAST ("… GmbH", "… AG"). So if a legal form
# appears MID-STRING, everything after it is address, not name — truncate there.
#     "Lotto24 AG Hamburg, Germany"     -> AG is mid-string      -> "Lotto24"
#     "S-KON Sales Kontor Hamburg GmbH" -> GmbH is final         -> "S-KON Sales Kontor Hamburg"
#     "Rosneft Deutschland GmbH"        -> GmbH is final         -> "Rosneft Deutschland"
# Note this is why we cannot simply strip trailing place names: "Deutschland" is part of Rosneft's
# registered name, while "Hamburg" is Lotto24's address. Position tells them apart; a word list cannot.
#
# Deliberately EXCLUDED from the mid-string rule: co / company / group / holding / as / se — too
# word-like, and a false truncation would narrow the pivot for no reason. Narrower is fail-safe;
# these are excluded only to avoid pointless damage, not for safety.
_ORG_LEGAL_MID = re.compile(
    r"\s(?:gmbh|ag|kg|mbh|ug|ltd|limited|inc|incorporated|llc|l\.l\.c|plc|corp|corporation|"
    r"bv|nv|sarl|srl|sas|s\.?p\.?a|oy|ab|a/s)\b[\s,.]+\S", re.I)


def _org_core(o):
    """The distinctive part of an org name: address tail cut, legal suffix stripped.

    Used to build `org:"…"` pivots, so over-broadness here is not cosmetic — it imports a
    stranger's infrastructure into a customer's deck.
    """
    o = re.sub(r"\s+", " ", str(o or "").strip())
    m = _ORG_LEGAL_MID.search(o)
    head = o[:m.start()].strip(" .,-") if m else o
    if len(head) < 4:                       # truncation ate the name -> keep the original
        head = o
    core = _LEGAL_SUFFIX.sub("", head).strip(" .,-")
    return core if len(core) >= 4 else head


# Generic markers of a PROVIDER's whois/cert organisation. A blocklist of hoster names can never be
# complete (there are thousands), so these are shape markers, used only as a secondary signal — the
# primary test is always _org_is_the_target() below.
PROVIDER_MARKERS = ("trading as", " t/a ", "hosting", "hoster", "rootserver", "root-server",
                    "datacenter", "data center", "rechenzentrum", "colocation", "colo ",
                    "webhosting", "server network", "servernetwork", "vserver", "vps",
                    "dedicated server", "internet services", "internet service", "network operations")


def _squash(x):
    return re.sub(r"[^a-z0-9]", "", str(x or "").lower())


def _seed_label(seed_apex):
    """'rightmart.de' -> 'rightmart'. The one token we know is genuinely the target's."""
    if not seed_apex:
        return ""
    return re.sub(r"[^a-z0-9]", "", str(seed_apex).split(".")[0].lower())


def _org_is_the_target(org, seed_ref):
    """Does this organisation name belong to the SEED, or to whoever hosts the seed?

    THE rightmart.de COLLAPSE (2026-07): rightmart.de resolves into IP-Projects, a shared hoster.
    The seed's TLS cert-O and its netblock whois-org therefore both read
    'IP-PROJECTS Michael Sebastian Schinzel trading as IP-Projects GmbH & Co. KG'. Every token of
    that string became a "brand token" (michael, schinzel, sebastian, trading, projects), which then
    authorised org: pivots into TWO UNRELATED HOSTING COMPANIES — +582 hosts, 78 evidence IPs in the
    deck, none of them the customer's.

    An org name may only act as an identity anchor if it CORROBORATES the seed label:
        seed 'skon.de'      + O 'S-KON Sales Kontor Hamburg GmbH'
                            -> squashes to '...skonsaleskontor...' which CONTAINS 'skon'  -> the
                               target's own O; its tokens ('kontor') are trustworthy.
        seed 'rightmart.de' + O 'IP-PROJECTS Michael ... GmbH & Co. KG'
                            -> no 'rightmart' anywhere -> somebody else's O. Contributes NOTHING.

    Fails CLOSED: no usable seed label -> no corroboration -> not the target."""
    lbl = _seed_label(seed_ref) if (seed_ref and "." in str(seed_ref)) else _squash(seed_ref)
    if len(lbl) < 4:
        return False
    o = _squash(org)
    if not o:
        return False
    if lbl in o:                      # the org carries the brand: 'skon' inside 'S-KON Sales Kontor'
        return True
    for t in re.split(r"[^a-z0-9]+", str(org or "").lower()):
        if len(t) >= 5 and t in lbl:  # or the brand carries a distinctive org token
            return True
    return False


def _looks_like_provider(name, prefix_count=None):
    """Secondary signal: a hoster/carrier shape, or an ASN announcing a provider-sized estate.
    Never the sole basis for a decision — _org_is_the_target() is."""
    n = str(name or "").lower()
    if any(m in n for m in PROVIDER_MARKERS):
        return True
    if _is(n, CDNS) or _is(n, CARRIERS):
        return True
    if prefix_count is not None and prefix_count > 20:
        return True                   # AS48314 announces ~130 prefixes; no SMB owns that
    return False


def _cert_names(m):
    """Every DNS name a host's certificate asserts: subject CN + all subjectAltName entries.

    Certificates are the highest-yield identity source in the whole pipeline — a cert is the one
    place the operator has DECLARED which names a host serves. Shodan stores the SAN extension with
    its raw DER length prefix still attached ('0\x1e\x82\x0crightmart.de\x82\x0e*.rightmart.de'),
    so a naive split returns binary garbage; pull hostnames out with a regex instead."""
    out = set()
    cert = ((m.get("ssl") or {}).get("cert") or {})
    cn = (cert.get("subject") or {}).get("CN")
    if cn:
        out.add(str(cn))
    for ext in (cert.get("extensions") or []):
        if str(ext.get("name", "")).lower() != "subjectaltname":
            continue
        raw = str(ext.get("data", ""))
        # The DER length bytes arrive either as real control characters or as the LITERAL text
        # '\x0c'. Blank both to a space first, or the regex welds the prefix onto the hostname and
        # yields 'x0crightmart.de' instead of 'rightmart.de'.
        raw = re.sub(r"\\x[0-9a-fA-F]{2}", " ", raw)
        raw = re.sub(r"[^\x20-\x7e]", " ", raw)
        for nm in re.findall(r"[A-Za-z0-9*_-]+(?:\.[A-Za-z0-9*_-]+)+", raw):
            out.add(nm)
    clean = set()
    for n in out:
        n = str(n).strip().lstrip("*.").strip(".").lower()
        n = re.sub(r"^x[0-9a-f]{2}(?=[a-z0-9])", "", n)      # belt and braces
        if "." in n and not n.replace(".", "").isdigit() and len(n) > 3:
            clean.add(n)
    return clean


def _record_names(m):
    """Every hostname this Shodan RECORD claims: rDNS, HTTP Host, domains and certificate names.

    Distinct from _cert_names(), which reads the certificate only. This is the full set of names
    by which a single observation identifies itself."""
    out = set()
    for h in (m.get("hostnames") or []):
        out.add(str(h).lower().strip("."))
    for d in (m.get("domains") or []):
        out.add(str(d).lower().strip("."))
    hh = ((m.get("http") or {}).get("host"))
    if hh:
        out.add(str(hh).lower().strip("."))
    for n in _cert_names(m):
        out.add(str(n).lower().strip(". *"))
    return {n for n in out if n and "." in n}


def _names_the_target(m, own_names):
    """Does this record identify itself with one of the customer's own names?"""
    for n in _record_names(m):
        for ap in own_names:
            if n == ap or n.endswith("." + ap):
                return True
    return False


def _brand_tokens_from(seed_apex, org_names):
    """Distinctive tokens from the seed domain label AND the cert subject Organization.

    The cert-O is what rescues the real S-KON brands: seed 'skon.de' alone gives token 'skon'
    (which matches saleskontor via the embedded 'skon' but NOT praemienkontor). The OV cert O
    'S-KON Sales Kontor Hamburg GmbH' adds 'kontor', so praemienkontor/managementkontor/ekontor24
    all resolve as owned — while otto.de / mediamarkt.de still do not."""
    toks = set()
    if seed_apex:
        lbl = re.sub(r"[^a-z0-9]", "", seed_apex.split(".")[0].lower())
        if len(lbl) >= 4:
            toks.add(lbl)
    NOISE = {"gmbh", "corp", "inc", "ltd", "group", "holding", "www", "the", "and", "company",
             "sales", "hamburg", "berlin", "munich", "deutschland", "germany", "services",
             "solutions", "systems", "technologies", "technology", "international", "und", "co", "kg",
             # legal-form / proprietor filler that turned a hoster's whois into "brand" tokens
             "trading", "mbh", "ohg", "gbr", "kgaa", "ug", "haftungsbeschraenkt", "projects",
             "project", "network", "networks", "server", "servers", "hosting", "host", "media",
             "consulting", "partner", "partners", "digital", "online", "web", "cloud", "data"}
    for name in (org_names or []):
        # THE GATE. An organisation only contributes brand tokens if it is demonstrably the TARGET's
        # organisation. Without this, a shared hoster's whois-O donates its proprietor's personal
        # name to the target's identity — which is exactly how rightmart.de acquired 'michael',
        # 'schinzel' and 'sebastian' and then pivoted into two unrelated hosting companies.
        if not _org_is_the_target(name, seed_apex):
            print("[auto] org %r contributes NO brand tokens — it does not corroborate the seed "
                  "(likely the hoster/registrar, not the target)" % str(name)[:70], file=sys.stderr)
            continue
        for t in re.split(r"[^a-z0-9]+", str(name).lower()):
            if len(t) >= 4 and t not in NOISE:
                toks.add(t)
    return toks


def _favicon_hash(domain):
    """Favicon MurmurHash3 for the http.favicon.hash pivot (best-effort; needs mmh3)."""
    try:
        import mmh3, codecs
        req = urllib.request.Request("https://www." + domain + "/favicon.ico", headers=UA)
        with urllib.request.urlopen(req, timeout=12) as r:
            return str(mmh3.hash(codecs.encode(r.read(), "base64")))
    except Exception:
        return None

# --- Shodan entitlement gate --------------------------------------------------------------
# `vuln:` needs a Small Business subscription or higher; `tag:` needs Corporate. On a "basic"
# (Freelancer) key those queries are REJECTED — they still cost a round-trip and they spam the log
# with scary warnings that look like a broken API key. They are not: the key is fine, the PLAN
# lacks the entitlement. So ask api-info once and simply do not build queries we cannot run.
_PLAN = {"plan": None, "vuln": False, "tag": False, "checked": False}
_VULN_PLANS = {"corp", "corporate", "smallbiz", "small-business", "stream-100", "edu", "academic"}
_TAG_PLANS  = {"corp", "corporate", "stream-100"}

def shodan_plan():
    if _PLAN["checked"]:
        return _PLAN
    _PLAN["checked"] = True
    key = os.environ.get("SHODAN_API_KEY", "")
    if not key:
        return _PLAN
    try:
        d = _get_json("https://api.shodan.io/api-info?key=" + key, timeout=15) or {}
        p = str(d.get("plan") or "").lower()
        _PLAN.update(plan=p, vuln=(p in _VULN_PLANS), tag=(p in _TAG_PLANS))
        print("[shodan] plan=%s  vuln:=%s  tag:=%s  credits=%s"
              % (p or "?", _PLAN["vuln"], _PLAN["tag"], d.get("query_credits")), file=sys.stderr)
        if not _PLAN["vuln"]:
            print("[shodan] note: 'vuln:'/'has_vuln:' need Small Business+; skipping those queries "
                  "(saves query credits). This is a PLAN limit, not a key problem.", file=sys.stderr)
    except Exception as e:
        print("[warn] shodan api-info failed (%s) — assuming no paid filters" % repr(e)[:80], file=sys.stderr)
    return _PLAN


def autodiscover(ident, orgs=None, brands=None, domains=None, favicons=None,
                 issuers=None, cert_orgs=None, jarms=None, cpes=None,
                 excludes=None, pins=None, platform_operator=False):
    """One input in, full anchor block out. Resolves ASNs+prefixes (bgpview + RIPE),
    brand domains (crt.sh CT logs), cert subject O, and favicon — then folds in any manual
    overrides. The internal-CA issuer pivot is auto-harvested live during the sweep (run()).

    REFINE overrides (from the post-run clarification loop, clarify.py):
      excludes          — apexes/hostnames/IPs the operator says are NOT theirs (client/white-label
                          sites, stray shared-hosting neighbours). Domains are force-unowned and never
                          scanned; IPs are dropped from the final host set in run().
      pins              — exact host IPs the operator supplied (VPN/mail/GitLab edges the auto-recon
                          missed). Scanned directly via the always-on pinned-host filter.
      platform_operator — the operator confirmed they run sites for clients; recorded so the report
                          can state it and the gate stays strict (client domains never adopted)."""
    orgs=list(orgs or []); brands=list(brands or []); domains=list(domains or [])
    favicons=list(favicons or []); cert_orgs=list(cert_orgs or [])
    # --- REFINE overrides: normalise excludes into apexes + IPs, and force-pin supplied hosts -------
    exclude_apexes=set(); exclude_ips=set()
    for x in (excludes or []):
        x=str(x).strip().lower().split()[0] if str(x).strip() else ""
        if not x: continue
        if CIDR_RE.match(x) or (x.replace(".","").isdigit() and x.count(".")==3):
            exclude_ips.add(x.split("/")[0])       # exact host IP (CIDR range-match not supported)
        else:
            exclude_apexes.add(_apex(_clean_domain(x.split(":")[0])))   # drop any :port
    if exclude_apexes: ident["exclude_apexes"]=sorted(exclude_apexes)
    if exclude_ips:    ident["exclude_ips"]=sorted(exclude_ips)
    for ip in (pins or []):
        ip=str(ip).strip()
        if ip and ip not in ident["pinned"] and ip not in exclude_ips:
            ident["pinned"].append(ip)
            ident["org_is_cdn"]=ident.get("org_is_cdn")  # pins work via filter #2b regardless
    if platform_operator: ident["platform_operator"]=True
    name = ident.get("org") or ident.get("brand") or ident["seed"]
    is_name = bool(name) and not CIDR_RE.match(str(name))
    if is_name:                                              # 1) ASNs: RIPE + CAIDA + PeeringDB + bgpview
        # Was bgpview.io ONLY. That single source stopped resolving inside the container
        # ("[Errno -5] No address associated with hostname") while stat.ripe.net answered in 1ms,
        # so every run produced asns=0 -> no ASN scoping and an empty BGP/NIS2 slide. Now four
        # sources are merged; RIPE DB is authoritative for the RIPE region (all of DACH).
        try:
            import asn_sources as _ASN
            _res = _ASN.discover(name)
            # asn_sources returns ints (a clean API); ident["asns"] has always held "AS1234" STRINGS
            # (build_filters does ",".join(ident["asns"])). Convert at the boundary — mixing the two
            # is what crashed the Yamaha run with "expected str instance, int found".
            _found = ["AS%d" % a for a in _res["asns"]]
            if not _found and _res["errors"]:
                print("[warn] ASN discovery: every source failed (%s) — ASNs unknown, NOT 'none'"
                      % ", ".join(e["source"] for e in _res["errors"]), file=sys.stderr)
        except Exception as _e:
            print("[warn] asn_sources unavailable (%s) — falling back to bgpview only" % _e, file=sys.stderr)
            _found = _bgpview_asns(name)
        for a in _found:
            if a not in ident["asns"]:
                # LATENT TWIN OF THE BIBELTV BUG: the domain-seed path re-checks the ASN holder
                # against CDNS/CARRIERS (line ~104) but this NAME-seed path never did. Seeding
                # "Bibel TV" instead of "bibeltv.de" would therefore adopt AS24940 (Hetzner) as an
                # OWNED ASN and sweep every other tenant of that hoster.
                _h = _ripe_holder(a)
                _ref = (ident["domains"][0] if ident.get("domains") else None) or name
                if _looks_like_provider(_h, len(_ripe_prefixes(a))) or not _org_is_the_target(_h, _ref):
                    print("[auto] ASN %s holder %r is provider space / does not corroborate %r — kept "
                          "as context, NOT an ownership anchor" % (a, _h, _ref), file=sys.stderr)
                    ident.setdefault("shared_asns", []).append(a)
                    continue
                ident["asns"].append(a); ident["asn_holder"] = ident["asn_holder"] or _h
    if not ident.get("org_is_cdn"):                          # 2) prefixes for every ASN we now hold
        for a in ident["asns"]:
            for p in _ripe_prefixes(a):
                if p not in ident["nets"]: ident["nets"].append(p)
    seed_dom = ident["domains"][0] if ident["domains"] else None
    seed_apex = _apex(seed_dom) if seed_dom else None

    # OWNERSHIP BASIS. Read the seed's TLS cert ONCE: its subject-Organization is the single
    # strongest ownership signal (the S-KON OV cert O = "S-KON Sales Kontor Hamburg GmbH"), and its
    # SAN list reveals sibling domains. Brand tokens are derived from the seed label + that O.
    seed_sans, seed_cert_o = _cert_info(seed_dom) if seed_dom else ([], None)
    if seed_cert_o:
        ident["cert_org_seen"] = seed_cert_o
        # ssl.cert.subject.o: is normally the HIGHEST-precision pivot — but only when the O is the
        # target's. rightmart.de's seed cert carried its hoster's Plesk O, which inverted it into the
        # LOWEST-precision pivot in the run: it returns the hoster's entire TLS-serving fleet.
        if _org_is_the_target(seed_cert_o, seed_apex) and not _looks_like_provider(seed_cert_o):
            if seed_cert_o not in cert_orgs:
                cert_orgs.append(seed_cert_o)        # -> ssl.cert.subject.o: pivot (best filter)
            print("[auto] seed cert subject-O: %r (used as ownership anchor)" % seed_cert_o, file=sys.stderr)
        else:
            ident["cert_org_rejected"] = seed_cert_o
            print("[auto] seed cert subject-O %r REJECTED as an anchor — it does not corroborate %r "
                  "(hoster/registrar certificate, not the target's)"
                  % (str(seed_cert_o)[:70], seed_apex), file=sys.stderr)
    btoks = _brand_tokens_from(seed_apex, ([seed_cert_o] if seed_cert_o else []) +
                               ([name] if is_name else []) + list(orgs))
    ident["brand_tokens"] = sorted(btoks)
    print("[auto] brand tokens: %s" % (", ".join(sorted(btoks)) or "(none)"), file=sys.stderr)

    # ---- FIRST-PARTY GROUP STRUCTURE (the angermann.de recall fix) -----------------------------
    # A brand token can only find domains that SPELL the brand. Angermann's subsidiaries trade as
    # NetBid, Nord Leasing, leaseback and buerosuche — zero string overlap with the seed — so they
    # were structurally unreachable, and they carried the engagement's best findings (an expired
    # certificate on the netbid.io mail cluster across 7 ports). The customer's own group-structure
    # page names and links every one of them: a first-party assertion of ownership, which is
    # STRONGER evidence than a substring match. Best-effort and fails closed (no page -> no domains).
    _group_doms, _group_weak, _structure_known = set(), [], False
    if seed_apex and not platform_operator:
        try:
            import group_discovery as _GD
            _g = _GD.discover(seed_apex)
            # Re-apply the denylist HERE as well as inside group_discovery. Defence in depth is
            # deliberate: group_discovery is best-effort and may be swapped, mocked in a test, or
            # fail its own import of scope_deny. The abakus lesson is that a rule enforced in one
            # place protects one code path.
            _group_doms = {x["domain"] for x in _g.get("strong") or []
                           if x.get("domain") and not _DENY(x["domain"])}
            _group_weak = [x["domain"] for x in _g.get("weak") or []]
            ident["group_domains"] = sorted(_group_doms)
            ident["group_pages"] = list(_g.get("pages") or [])
            # Recorded so clarify.py can ASK. A group page legitimately lists joint ventures and
            # global network brands the customer does not operate (Angermann's M&A arm trades as
            # Oaklins Germany AG, but oaklins.com is a worldwide network's shared infrastructure).
            ident["group_domains_unconfirmed"] = sorted(_group_doms)
            # Authoritative only if the customer actually published a structure page AND it named
            # companies. An empty or unreachable page must NOT be read as "they have no subsidiaries"
            # (absence of evidence is never a finding) - that would silently drop real lookalikes.
            # >= 2 named companies, not >= 1. A "structure page" that yields a SINGLE external link
            # is far more likely to be a mis-selected page whose footer we harvested than a
            # published group roster -- which is exactly the abakus-tk.de shape (one link: wa.me).
            # Treating that as an authoritative roster would ALSO switch on the lookalike rejection
            # in _owns_apex and silently shrink a real estate, so the bar is raised at both ends.
            _structure_known = bool(_g.get("pages")) and len(_group_doms) >= 2
        except Exception as _e:
            print("[auto] group-structure discovery unavailable (%s) - continuing without it"
                  % type(_e).__name__, file=sys.stderr)
    if _group_doms:
        print("[auto] group structure: %d subsidiary domain(s) from the customer's own site: %s"
              % (len(_group_doms), ", ".join(sorted(_group_doms))), file=sys.stderr)

    # A candidate is any apex/host surfaced by CT, cert-SANs or the DNS probe. It enters scope ONLY
    # if it carries the target's identity. Everything else is recorded as related-but-unscoped and
    # NEVER pinned or swept — this is what stops a platform operator's client estate from flooding in.
    candidate_apexes = set()
    unowned = set()

    def _consider_domain(d, source):
        d = _clean_domain(str(d))
        if not d or "." not in d:
            return
        ap = _apex(d)
        # REFINE: the operator explicitly said this apex is not theirs — force it out, never scan it.
        if ap in exclude_apexes:
            unowned.add(ap)
            return
        ok, why = _owns_apex(ap, btoks, seed_apex, _group_doms, _structure_known)
        if not ok:
            unowned.add(ap)
            return
        candidate_apexes.add(ap)
        if d not in domains and d not in ident["domains"]:
            domains.append(d)
            if ap != seed_apex:
                print("[auto] owned domain (%s): %s [%s]" % (source, d, why), file=sys.stderr)

    # 3-pre) FEED THE SUBSIDIARIES INTO DISCOVERY. This is the step whose absence made the whole
    #        group-structure fix invisible: `group_domains` was consulted by the ownership GATE but
    #        never added to ident["domains"], and ident["domains"] is what drives CT enumeration,
    #        the DNS probe and the hostname:/cert-CN Shodan clauses. Result: netbid.com was
    #        "owned" and never searched, and the deck came out byte-identical. Each subsidiary is
    #        now treated as a first-class seed: its own CT enumeration, its own subdomain probe,
    #        its own identity clauses.
    for _gd in sorted(_group_doms):
        if _gd in exclude_apexes:
            continue
        # THE ABAKUS-TK.DE FIX (2026-08). This loop used to append straight into `domains`,
        # bypassing _consider_domain() and therefore every check the engine has -- and _owns_apex
        # then returned True for these apexes BECAUSE they were in group_domains. Discovery
        # vouching for itself is not a gate. Each subsidiary now passes the same gate as any other
        # candidate; group membership still WINS inside _owns_apex, so the angermann recall
        # (netbid.com has zero string overlap with the seed) is untouched -- but a denylisted or
        # public-suffix apex can no longer ride in on the strength of the assertion alone.
        if _DENY(_gd) or _PSL.is_public_suffix(_gd):
            unowned.add(_gd)
            print("[auto] subsidiary REFUSED: %s (%s)"
                  % (_gd, _DENY_WHY(_gd) or "public suffix - nobody owns it"), file=sys.stderr)
            continue
        candidate_apexes.add(_gd)
        if _gd not in domains and _gd not in ident["domains"]:
            domains.append(_gd)
            print("[auto] subsidiary INTO SCOPE (will be enumerated + swept): %s" % _gd,
                  file=sys.stderr)
        # CT-enumerate the subsidiary too — netbid.io was found this way in the operator's export
        try:
            for _sd in _crtsh_domains(domain=_gd, org=None):
                _consider_domain(_sd, "CT/%s" % _gd)
        except Exception:
            pass

    # 3) CT logs (crt.sh + CertSpotter fallback)
    for d in _crtsh_domains(domain=seed_dom, org=(name if (is_name and not seed_dom) else None)):
        _consider_domain(d, "CT")
    # 3b) sibling domains from the seed certificate SAN list (bibel.tv came from here)
    for san in seed_sans:
        _consider_domain(san, "cert-SAN")
    if seed_apex:
        candidate_apexes.add(seed_apex)

    # 3c) DNS subdomain probe — OWNED apexes only (never a client's apex), and only those that
    #     actually CARRY THE BRAND. The ~60-name wordlist costs one DNS query per name per apex, so
    #     probing every group domain took the angermann run from 27s to 181s and produced 122
    #     "live" names, 14 of them under oaklins.com — a GLOBAL M&A NETWORK whose international
    #     infrastructure (careers-nl, porto2026, bedrijf-verkopen) is emphatically not the
    #     customer's attack surface. Non-brand group domains still get full CT enumeration above,
    #     which is what actually found the real netbid/leaseback/nordleasing names; they just do not
    #     get the expensive speculative probe. Recall is preserved, noise and wall-clock are not.
    _probe_apexes = {a for a in candidate_apexes
                     if a == seed_apex
                     or any(t and len(t) >= 4 and t in re.sub(r"[^a-z0-9]", "", a.split(".")[0])
                            for t in btoks)}
    _skipped = sorted(candidate_apexes - _probe_apexes)
    if _skipped:
        print("[auto] DNS probe SKIPPED for %d non-brand group domain(s) (CT enumeration only, "
              "avoids speculative noise on a partner/network brand): %s"
              % (len(_skipped), ", ".join(_skipped[:6])), file=sys.stderr)
    probed = _probe_subdomains(sorted(_probe_apexes))

    # ---- RESOLVE WHAT CT ACTUALLY TOLD US (ns03.ru, 2026-08-09) --------------------------------
    # THE BUG THIS FIXES, and it silently gutted a whole assessment: Certificate Transparency
    # returned 13 names for ns03.ru -- srv-kap-gt, ventil.nzn, ventil2.nzn, ing.nzn, iiko.nzn, oo,
    # nextcloud -- and NOT ONE OF THEM WAS EVER RESOLVED. They were added to `domains` so they
    # could become Shodan `hostname:` clauses, and that was all. The consequences compounded:
    #   · none of them was pinned, so the estate had 4 addresses instead of the real set;
    #   · none reached ident["resolved"], and cert_intel joins its findings against exactly that
    #     map -- so the TWO REVOKED CERTIFICATES the feature was built for produced NOTHING;
    #   · the DNS probe's ~60-word list found 6 generic names and the deck shipped "IPs 0".
    # CT records INTENT: somebody requested a certificate for that name. Checking whether it also
    # RESOLVES costs one DNS query and is the difference between a name and a host.
    _ct_fqdns = [d for d in domains
                 if d not in probed and d.count(".") >= 1
                 and any(d == a or d.endswith("." + a) for a in candidate_apexes)]
    if _ct_fqdns:
        _ct_live = {}
        for _n in _ct_fqdns[:120]:            # bounded: one query each, and CT lists can be long
            _ips = _resolve(_n)
            if _ips:
                _ct_live[_n] = _ips
        if _ct_live:
            probed.update(_ct_live)
        print("[auto] CT names resolved: %d of %d discovered name(s) are live%s"
              % (len(_ct_live), len(_ct_fqdns),
                 (" -> " + ", ".join(sorted(_ct_live)[:6])) if _ct_live else ""),
              file=sys.stderr)

    # ---- CONVENTION-DERIVED CANDIDATES (ns03.ru) -----------------------------------------------
    # A blind dictionary is close to useless: on ns03.ru every generic name (vpn, portal, remote,
    # owa) returned NXDOMAIN, while the target's OWN grammar -- learned from what it published in
    # CT -- produced ventil/ing/iiko under a site zone `nzn` and `srv-<site>-<role>`. Generating
    # from the customer's vocabulary is both higher recall AND fewer queries than a wordlist.
    #
    # The language set is DERIVED from where the company operates (its ccTLDs, its estate's
    # countries), never from what languages the product happens to support. Asking a German
    # manufacturer about `kotelnaya` is wasted queries; asking a Russian one about it found the
    # boiler house.
    try:
        # READ THE LIST THAT ACTUALLY HOLDS THE CT NAMES. `ident["domains"]` does not receive them
        # until merge_variants() runs at the END of resolve_identity, and `ident["ct_domains"]`
        # has never existed at all -- I assumed a key instead of reading one, so this miner
        # silently found no site codes and skipped itself on every single run.
        _known_names = sorted(set(list(domains) + list(ident.get("domains") or []) + list(probed)))
        _gram = naming.learn(_known_names, sorted(_probe_apexes))
        if _gram.get("sites") or _gram.get("sequenced"):
            _langs = naming.langs_for(domains=sorted(_probe_apexes),
                                      countries=(ident.get("countries") or []),
                                      country=ident.get("country"))
            _cands = naming.candidates(_gram, sorted(_probe_apexes)[:2], _langs,
                                       cap=int(os.environ.get("NAMING_CAP", "220")),
                                       known=_known_names)
            _hits = {}
            for _c2 in _cands:
                _ips2 = _resolve(_c2)
                if _ips2:
                    _hits[_c2] = _ips2
            ident["naming"] = {"grammar": _gram, "langs": _langs,
                               "tried": len(_cands), "found": sorted(_hits)}
            print("[auto] naming convention: sites=%s roles=%s langs=%s -> %d candidate(s), "
                  "%d resolved" % (_gram.get("sites")[:3], _gram.get("roles")[:3], _langs,
                                   len(_cands), len(_hits)), file=sys.stderr)
            probed.update(_hits)
    except Exception as _e:
        print("[warn] naming-convention mining failed: %s" % _e, file=sys.stderr)

    # Keep the name -> address map. run() needs it to spot names that resolve but have no
    # observable service (the possible-dangling-DNS candidate), which is a DNS-derived finding
    # and cannot be reconstructed from the Shodan results alone.
    ident["resolved"] = {k: list(v) for k, v in probed.items()}
    # The MX set, used to corroborate a self-hosted mail platform. One query per seed apex.
    try:
        ident["mx"] = _mx(seed_apex) if seed_apex else []
    except Exception:
        ident["mx"] = []
    for fqdn, ips in probed.items():
        low = fqdn.lower()
        ap = _apex(low)
        # belt-and-braces: a microsite prefix must never sneak in on a non-brand apex
        first = low.split(".")[0]
        if any(first.startswith(mp) for mp in _MICROSITE_PREFIXES) and \
           not _owns_apex(ap, btoks, seed_apex, _group_doms, _structure_known)[0]:
            continue
        if not _owns_apex(ap, btoks, seed_apex, _group_doms, _structure_known)[0]:
            continue
        if fqdn not in domains and fqdn not in ident["domains"]:
            domains.append(fqdn)
        # A name that CNAMEs into Microsoft 365, Google Workspace, Zoho or a CDN is a TENANCY.
        # Pinning it puts a provider's shared front end into scope as the customer's own host --
        # and because pinned hosts bypass the CDN/hoster drop, every co-tenant on that front end
        # comes with it. abakus-tk.de: autodiscover/webmail/exchange/auth pinned 10 Microsoft IPs.
        if _is_saas_tenancy(fqdn):
            ident.setdefault("saas_tenancies", [])
            if fqdn not in ident["saas_tenancies"]:
                ident["saas_tenancies"].append(fqdn)
                print("[auto] SaaS tenancy NOT pinned: %s (CNAME into a provider platform - the "
                      "customer uses it, they do not own the address)" % fqdn, file=sys.stderr)
            continue
        # PIN resolved IPs as exact hosts (ident["pinned"], not nets: run_net is off for hosters).
        # Only owned hostnames reach here, so a pinned IP is always the target's.
        for ip in ips:
            if ":" in ip:
                continue
            if ip not in ident["pinned"]:
                ident["pinned"].append(ip)

    if unowned:
        ident["related_unscoped"] = sorted(unowned)
        print("[auto] EXCLUDED %d third-party apex(es) as out-of-scope (client/white-label): %s"
              % (len(unowned), ", ".join(sorted(unowned)[:8]) + (" ..." if len(unowned) > 8 else "")),
              file=sys.stderr)

    if is_name and name not in cert_orgs: cert_orgs.append(name)   # 4) cert-org + favicon
    dom0 = (domains + ident["domains"])
    if dom0:
        fh = _favicon_hash(_apex(dom0[0]))
        if fh and fh not in favicons: favicons.append(fh)
    print(f"[auto] asns={len(ident['asns'])} nets={len(ident['nets'])} pinned={len(ident['pinned'])} "
          f"+ct_domains={len(domains)} cert_orgs={cert_orgs}", file=sys.stderr)
    if ident["pinned"]:
        print("[auto] pinned hosts: " + ", ".join(ident["pinned"][:10])
              + (" ..." if len(ident["pinned"]) > 10 else ""), file=sys.stderr)
    return merge_variants(ident, orgs, brands, domains, favicons,
                          issuers=issuers, cert_orgs=cert_orgs, jarms=jarms, cpes=cpes)

# ----------------------------------------------------------- canonical filters ---
P_REMOTE_DB = "3389,22,23,5900,445,3306,1433,5432,6379,27017,9200,21"
P_RDP_WINRM = "3389,3390,5985,5986,5900,5800"
P_VPN_MGMT  = "443,4433,8443,10443,4443,500,4500,1194"
P_ICS       = "102,502,4840,44818,20000,1911,47808,789,9600,2404,20547"
P_MAIL      = "25,587,465,143,993,110,995"
P_CHECKPOINT = "264,18264"                         # Check Point SecuRemote topology + ICA mgmt
PROD_ICS    = '"Modbus","Siemens S7","BACnet","DNP3","IEC-104","OPC-UA"'
PROD_PANEL  = '"Citrix","Fortinet","Pulse Secure","Palo Alto","OpenVPN","SonicWall","Sophos","Cisco ASA","Ivanti","Check Point"'
PROD_DB     = '"MySQL","PostgreSQL","MongoDB","Redis","Elasticsearch"'   # DBs never public
PROD_WEBAPP = '"Grafana","Jenkins","Kibana","phpMyAdmin"'               # admin UIs
# CISA-KEV edge-appliance CVEs the playbook checks: Citrix Bleed, Check Point info-disc, F5 iControl, HTTP/2 Rapid Reset
KEV_CVES    = "CVE-2023-4966,CVE-2024-24919,CVE-2022-1388,CVE-2023-44487"
CLOUD_HOSTERS = ("Amazon", "Microsoft Azure", "Akamai", "Cloudflare")   # brand-on-3rd-party pivot
# named edge appliances whose exposed mgmt plane is CRITICAL (KEV-heavy), not just HIGH
CRIT_APPLIANCES = ("citrix", "netscaler", "ivanti", "pulse secure", "check point", "fortinet", "palo alto")

def build_filters(ident):
    # coerce defensively: one bad type must never take down a whole assessment (see Yamaha crash)
    asns = ",".join(("AS%d" % a) if isinstance(a, int) else str(a) for a in ident.get("asns") or [])
    nets = ",".join(str(n) for n in ident.get("nets") or [])
    org = ident["org"]; domains = ident["domains"]; cdn = ident["org_is_cdn"]
    own_asn = bool(ident["asns"]) and not ident["org_is_carrier"] and not cdn
    run_net = bool(nets) and not cdn
    scope = (f"asn:{asns}" if own_asn else (f"net:{nets}" if run_net else (f'org:"{org}"' if org else "")))
    F = []
    def _cat(clause):
        c = clause.lower()
        return "identity" if any(k in c for k in ("ssl", "hostname:", "org:", "http.title", "http.html", "favicon")) else "sweep"
    def add(n, name, clause, run=False, note="", cat=None, dom=None, guard=None, sel=None):
        # `dom` records WHICH discovered domain produced this clause. run() uses it to measure each
        # domain's contribution separately, so one bad domain can be rolled back without taking the
        # assessment with it (the abakus-tk.de / wa.me failure). None = not attributable to a single
        # discovered domain (ASN sweep, pinned hosts, brand text, org name).
        if clause: F.append({"n": n, "name": name, "clause": clause, "run": run, "note": note,
                             "cat": cat or _cat(clause), "dom": dom, "guard": guard, "sel": sel})
    if own_asn:
        add(1, "ASN sweep", f"asn:{asns}", run=True, note="every host announced from the org's ASNs")
    elif ident["asns"]:
        why = "CDN" if cdn else "carrier"
        add(1, "ASN sweep — SKIPPED", f'# {asns} is {why} "{ident["asn_holder"]}", not the target', run=False,
            note=f"{why} ASN would return the whole {why} estate — use net/ssl/hostname or the real ASN")
    add(2, "Netblock / CIDR (master)", f"net:{nets}" if nets else "", run=run_net,
        note=("SKIPPED — belongs to the CDN, not the target" if (nets and cdn) else "the target's own IP space"))
    # #2b PINNED HOSTS — exact IPs the customer's OWN DNS resolves to (gitlab./vpn./mail. ...).
    # These always run: a /32 we resolved is not a hoster range, and on a shared-hosting target it
    # is the ONLY thing that scopes correctly. This is what was missing when the bibeltv.de deck
    # shipped without gitlab.bibel.tv (SCM) or vpn.bibeltv.de (the Colt AS8220 edge).
    _pin = ",".join(str(i) for i in (ident.get("pinned") or []))
    # cat="pinned" bypasses the CDN/hoster drop in run(): we resolved these IPs from the target's
    # OWN owned hostnames, so a Google/Host-Europe holder is the target's shared-hosting tenancy,
    # not noise to discard. Without this, pinned S-KON hosts on shared infra would be dropped.
    add(2.5, "Pinned hosts (DNS-resolved)", f"net:{_pin}" if _pin else "", run=bool(_pin),
        note="exact hosts from the target's own DNS — valid even on shared hosting", cat="pinned")
    orgs = ident.get("org_variants") or ([org] if org else [])
    brands = [b for b in (ident.get("brand_variants") or ([ident["brand"]] if ident.get("brand") else [])) if b and not CIDR_RE.match(str(b))]
    favicons = ident.get("favicons") or []
    for o in orgs:                       # #3 org-name match (+ variants: subsidiaries, native spellings)
        add(3, "Org-name match", f'org:"{o}"', run=True, note="reassigned/cloud/subsidiary ranges — try name variants")
    # Query APEX domains only for the identity clauses. `hostname:".bibel.tv"` already covers
    # gitlab.bibel.tv, so emitting one clause per discovered subdomain just multiplies the query
    # count (and the Shodan credit burn) for zero extra recall. The individual hosts are covered
    # exactly by the pinned net: clause above.
    _apexes = list(dict.fromkeys(_apex(str(d)) for d in domains if d))[:6]
    for d in _apexes:                    # #4 cert CN — finds origin behind CDN/hoster, any ASN
        add(4, "TLS cert subject CN", f'ssl.cert.subject.cn:"{d}"', run=True, note="real origin even behind a CDN/hoster", dom=d)
        add(4, "TLS cert SAN (wildcard)", f'ssl.cert.subject.cn:"*.{d}"', run=True, note="wildcard certs covering every subdomain", dom=d)
    # BRAND FREE-TEXT SELECTORS ARE RARITY-GATED (the abakus-tk.de failure, 2026-08).
    # "Abakus" is the German word for abacus and the name of dozens of unrelated companies, so
    # ssl:"abakus" / http.title:"abakus" / http.html:"abakus" matched Cloudflare, Hetzner, OVH,
    # Vultr, Scaleway, Infomaniak, Google and Amazon -- 192 IPs across 44 ASNs and 15 countries for
    # a company with ZERO announced prefixes. http.html: is the worst of the three: it matches any
    # page whose BODY merely contains the word.
    # The rule already existed for the CA pivot after bibeltv ("never let a selector that can match
    # the whole internet become an ownership anchor") and was enforced by an api.count() test in
    # _private_ca_ok. It was never applied to the BRAND selectors, which are the same shape.
    # guard="rarity" makes run() count the selector first and refuse it if it is not distinctive.
    for b in brands:                     # #4/#5 cert free-text across ANY ASN (cross-ASN estate)
        add(5, "TLS free-text / cert org", f'ssl:"{b}"', run=True, note="wildcard & SAN certs across any ASN",
            guard="rarity", sel="brand:%s" % b)
    for d in _apexes:                    # #5 hostname / rDNS — leading dot = "any host under it"
        add(6, "Hostname / domain", f'hostname:".{d}"', run=True, note="reverse-DNS / HTTP host", dom=d)
        add(6, "HTTP host header", f'http.host:"{d}"', run=True, note="vhost behind a shared reverse proxy", dom=d)
    for b in brands:                     # #6 branded HTTP title/body (portals, shadow IT)
        add(14, "HTTP title (branded)", f'http.title:"{b}"', run=True, note="branded portals/login pages on any host",
            guard="rarity", sel="brand:%s" % b)
        add(15, "HTTP body (branded)", f'http.html:"{b}"', run=True, note="branded body content / shadow IT",
            guard="rarity", sel="brand:%s" % b)
    for h in favicons:                   # #7 favicon hash (branded icon, any host)
        add(16, "Favicon hash", f'http.favicon.hash:{h}', run=True, note="every host serving the branded icon")
    # ---- §3 advanced identity pivots (the *super* part) ----
    for ca in ident.get("internal_cas", []):   # internal-CA issuer — THE killer pivot: whole estate, any IP/cloud
        add(17, "Internal-CA issuer (estate pivot)", f'ssl.cert.issuer.cn:"{ca}"', run=True,
            note="every host fronted by the org's private issuing CA — across ANY ASN/cloud (highest-yield pivot)")
    for o in ident.get("cert_orgs", []):        # cert subject Organisation (distinct from CN)
        add(18, "TLS cert subject O", f'ssl.cert.subject.o:"{o}"', run=True, note="cert subject organisation across any ASN")
    for b in brands[:1]:                        # cloud/hosting overlap — brand assets on 3rd-party infra
        for h in CLOUD_HOSTERS:
            add(19, f"Cloud overlap · {h}", f'ssl:"{b}" org:"{h}"', run=True, note="brand assets on cloud/CDN infra the ASN misses")
    for j in ident.get("jarms", []):            # JARM — cluster identical TLS stacks (appliance/LB fleet); paid facet
        add(20, "JARM TLS-stack cluster", f'ssl.jarm:{j}', run=True, note="rest of the appliance/LB fleet (paid)")
    if scope:
        add(7, "Remote-access & DB ports", f"{scope} port:{P_REMOTE_DB}", note="RDP/SSH/Telnet/VNC/SMB/DB/FTP")
        add(8, "VPN / firewall mgmt", f"{scope} port:{P_VPN_MGMT} product:{PROD_PANEL}", note="edge-VPN = top ransomware vector")
        add(9, "RDP / WinRM / VNC", f"{scope} port:{P_RDP_WINRM}", note="remote desktop / mgmt")
        _pl = shodan_plan()
        add(10, "OT / ICS / SCADA",
            (f"{scope} tag:ics port:{P_ICS} product:{PROD_ICS}" if _pl["tag"]
             else f"{scope} port:{P_ICS} product:{PROD_ICS}"),          # tag: needs Corporate
            note="industrial protocols" + ("" if _pl["tag"] else " (tag: needs Corporate — omitted)"))
        add(11, "Mail / Exchange / OWA", f"{scope} port:{P_MAIL}", note="on-prem mail + OWA")
        add(12, "Vuln & TLS/EOL hygiene",
            ((f"{scope} has_vuln:true  |  " if shodan_plan()["vuln"] else "")
             + f"{scope} ssl.cert.expired:true  |  {scope} ssl.version:sslv3,tlsv1,tlsv1.1"),
            note="CISA KEV = CRITICAL")
        add(13, "Logins / panels / non-prod",
            f'{scope} http.title:"login","admin","portal","vpn","dashboard","phpMyAdmin","Webmin"', note="forgotten admin UIs")
        add(21, "Check Point mgmt plane", f"{scope} port:{P_CHECKPOINT}", note="SecuRemote topology + ICA mgmt")
        add(22, "Databases (never public)", f"{scope} port:3306,5432,27017,6379,9200,1433 product:{PROD_DB}", note="direct data-exfil path")
        add(23, "Admin UIs / web apps",
            f'{scope} product:{PROD_WEBAPP}  |  {scope} http.component:"Outlook Web App"', note="Grafana/Jenkins/Kibana/phpMyAdmin/OWA")
        if shodan_plan()["vuln"]:
            add(24, "KEV edge-appliance CVEs", f"{scope} vuln:{KEV_CVES}", run=True, note="Citrix Bleed / Check Point / F5 / HTTP-2 Rapid Reset — CISA KEV (paid)")
        if shodan_plan()["vuln"]:
            add(28, "Vulnerable hosts (has_vuln)", f"{scope} has_vuln:true", run=True, note="every host with a Shodan-tagged CVE across the estate (paid)")
        if shodan_plan()["tag"]:
            add(29, "ICS/OT tagged hosts", f"{scope} tag:ics", run=True, note="industrial systems across the estate (paid)")
        add(25, "Weak keys / full cert inventory",
            f"{scope} ssl.cert.pubkey.bits:1024  |  {scope} ssl.cert.subject.cn:*", note="1024-bit keys + full TLS inventory")
        for c in ident.get("cpes", []):
            add(27, "CPE inventory", f'{scope} cpe:"{c}"', note="pin an exact platform/appliance across hosts")
    for b in brands[:1]:                         # non-prod / brand-fragmentation discovery (any host)
        add(26, "Non-prod / brand fragmentation",
            f'ssl.cert.subject.cn:*{b}* hostname:dev-,test-,staging-,sandbox-,qs-', note="dev/test/staging portals carrying the brand")
    return F

def filters_md(ident, F):
    L = [f"# Shodan Super Filters — {company_name(ident)}", "",
         f"_Seed: `{ident['seed']}` · {datetime.date.today().isoformat()} · passive OSINT only._", ""]
    if ident["org_is_cdn"]:
        L += [f"> ⚠ **Behind a CDN ({ident['asn_holder']}).** The domain's IP is shared CDN infra, not the "
              f"target's. Real origin is found via `ssl.cert.subject.cn` / `hostname`, and the target's REAL "
              f"netblock via bgp.he.net / RIPE / northdata (search the company name). Then re-run with `--asn/--net`.", ""]
    elif ident["org_is_carrier"]:
        L += [f"> ℹ Carrier-hosted under **{ident['asn_holder']}** — `org:`/`isp:` read the carrier. "
              f"Discovery uses `net:` (assigned block) + `ssl:`/`hostname:`.", ""]
    L += ["## Identity",
          f"- ASNs: {', '.join(ident['asns']) or '—'}",
          f"- ASN holder: {ident.get('asn_holder') or '—'}",
          f"- Netblocks: {', '.join(ident['nets']) or '—'}",
          f"- Brand/Org: {company_name(ident)}",
          f"- Domains: {', '.join(ident['domains']) or '—'}",
          f"- Internal CA(s): {', '.join(ident.get('internal_cas') or []) or '—'}",
          f"- Cert subject O: {', '.join(ident.get('cert_orgs') or []) or '—'}", "", "## Super filters", ""]
    for f in F:
        L.append(f"### {f['n']}. {f['name']}")
        if f["note"]: L.append(f"_{f['note']}_")
        L += ["```", f["clause"], "```", ""]
    L += cross_engine_dorks(ident)
    return "\n".join(L)

def cross_engine_dorks(ident):
    """§5 — equivalent dorks on other scan engines (different scanners see different hosts)."""
    org = company_name(ident); asn0 = (ident["asns"] or ["AS0"])[0].replace("AS", "")
    dom = (ident["domains"] or ["example.com"])[0]
    ca = (ident.get("internal_cas") or [""])[0]
    fav = (ident.get("favicons") or [""])[0]
    L = ["## Cross-engine dorks (§5 — cross-check; each scanner sees different hosts)", "",
         "**Censys** (`search.censys.io`)", "```",
         f'services.tls.certificates.leaf_data.subject.organization: "{org}"',
         f'services.tls.certificates.leaf_data.issuer.common_name: "{ca}"' if ca else "# (add internal-CA to enable issuer dork)",
         f"autonomous_system.asn: {asn0}", "```", "",
         "**FOFA** (`fofa.info`)", "```",
         f'cert="{org}" || org="{org}" || asn="{asn0}"' + (f' || icon_hash="{fav}"' if fav else ""), "```", "",
         "**ZoomEye** (`zoomeye.hk`)", "```",
         f'ssl:"{org}" +ssl.cert:"{dom}"' + (f' +asn:"{asn0}"' if asn0 != "0" else ""), "```", "",
         "**Netlas** (`app.netlas.io`)", "```",
         f'certificate.subject.organization:"{org}"' + (f'  ·  certificate.issuer.common_name:"{ca}"' if ca else ""), "```", "",
         f"**CT harvest** → `https://crt.sh/?q=%25.{dom}` (feed SANs back into `hostname:`/`net:`)", ""]
    return L

# ------------------------------------------------------------------ classify ---
DB_PORTS = {27017:"MongoDB",9200:"Elasticsearch",6379:"Redis",5432:"PostgreSQL",3306:"MySQL",
            1433:"MSSQL",5984:"CouchDB",11211:"Memcached",9042:"Cassandra"}
ICS_PORTSET = {102:"S7",502:"Modbus",4840:"OPC-UA",44818:"EtherNet/IP",20000:"DNP3",1911:"Fox",
               47808:"BACnet",789:"Red Lion",2404:"IEC-104",20547:"ProConOS",9600:"OMRON"}
REMOTE_HI = {23:"Telnet",5900:"VNC",5800:"VNC-http",445:"SMB",5985:"WinRM",5986:"WinRM",3390:"RDP"}
VPN_PORTS = {4433,8443,10443,4443,500,4500,1194}

# Edge security appliances (firewall / UTM / SSL-VPN). An exposed MGMT plane on one of these is
# KEV-heavy and CRITICAL. Detected by product banner OR by the tell-tale self-signed cert issuer/
# subject the device ships (e.g. WatchGuard's 'Firebox webCA', Barracuda's own CA) — the S-KON
# WatchGuard has NO product banner, so the cert issuer is the only anchor and was being missed.
_APPLIANCE_RE = re.compile(
    r"(?i)watchguard|firebox|barracuda|sonicwall|fortigate|fortinet|forti-?os|citrix|netscaler|"
    r"pulse\s*secure|ivanti|palo\s*alto|globalprotect|pan-os|check\s*point|sophos|sma\b|"
    r"cisco\s*asa|meraki|zyxel|draytek|kemp|f5\s*big-?ip|big-?ip|silverpeak|velocloud")


# CATEGORIES THAT PRODUCED "CRIT 0" ON A GENUINELY CRITICAL ESTATE (angermann.de, 2026-07)
# 217.110.51.7:443 served "Passbolt | Open source password manager for teams" behind nginx with a
# valid cert. classify() saw port 443 + nginx and filed it as standard_service, so a deck containing
# an INTERNET-FACING PASSWORD VAULT reported CRITICAL 0. A secrets manager is the single highest-value
# target on an estate: it is the credentials to everything else. Likewise 94.16.117.249:5001 is a 3CX
# PBX web client (angermann.3cx.eu) — 3CX is the CVE-2023-29059 supply-chain vector and its mgmt plane
# is heavily targeted; and NAS appliances (Synology/QNAP) are the #1 ransomware target for SMEs.
# Detection is by PRODUCT, HTTP TITLE, cert CN and PORT, because a reverse proxy hides the product.
_SECRETS_RE = re.compile(
    r"(?i)(passbolt|vaultwarden|bitwarden|hashicorp vault|\bvault\b|keycloak|authelia|authentik"
    r"|psono|teampass|passwordstate|cyberark|thycotic|delinea|secret server|keeper security"
    r"|1password|lastpass|padloc|pleasant password)")
_PBX_RE = re.compile(
    r"(?i)(3cx|asterisk|freepbx|elastix|issabel|yeastar|grandstream|mitel|avaya|innovaphone"
    r"|starface|pascom|sip ?server|voipmonitor|kamailio|opensips)")
_NAS_RE = re.compile(
    r"(?i)(synology|diskstation|rackstation|qnap|qts|truenas|freenas|openmediavault|unraid"
    r"|western digital my ?cloud|netgear readynas|buffalo terastation)")
_BACKUP_RE = re.compile(
    r"(?i)(veeam|acronis|bacula|bareos|urbackup|nakivo|altaro|arcserve|commvault|rubrik|cohesity)")
_NAS_PORTS = {5000, 5001, 8080, 8443}          # Synology DSM / QNAP QTS web UI (5000/5001 canonical)
_PBX_PORTS = {5060, 5061, 5090, 5001}          # SIP + 3CX web client


def _redirect_trail(m):
    """Every URL/host this record redirects THROUGH, plus its own Host header.

    THE adpolice.gov.ae MISS (2026-08). Host 151.253.157.21:443 was reported as "a mail service
    gateway" because the engine read `port` and `product`. Its own Shodan record contained:
        301 -> https://mediahubtest.adpolice.gov.ae/otmm/ux-html/index.html
        302 -> /otdsws/login?logon_appname=Digital+Asset+Management+CE+25.4
    That is OpenText Media Management behind OpenText Directory Services, and the hostname says
    TEST. The single internet-facing host the force owns under its own certificate is a
    NON-PRODUCTION media repository — the most serious finding in the engagement, and it was
    already in data we had.
    A redirect chain names the application far more reliably than a port ever will."""
    http = m.get("http") or {}
    out = []
    for r in (http.get("redirects") or []):
        if isinstance(r, dict):
            out += [str(r.get("location") or ""), str(r.get("host") or "")]
            out.append(str((r.get("data") or ""))[:200])
        else:
            out.append(str(r)[:200])
    out += [str(http.get("location") or ""), str(http.get("host") or "")]
    return " ".join(x for x in out if x)


def _hay(m):
    """Every string on a host record that can name a product: banner, cert, HTTP server + title,
    AND the redirect chain — see _redirect_trail for why that last one is load-bearing."""
    ssl = (m.get("ssl") or {}).get("cert") or {}
    subj = ssl.get("subject") or {}
    http = m.get("http") or {}
    return " ".join([str(m.get("product") or ""), str(m.get("version") or ""),
                     str(subj.get("CN", "")), str(subj.get("O", "")),
                     str(http.get("server") or ""), str(http.get("title") or ""),
                     str(http.get("html_hash") or ""), str(m.get("data") or "")[:400],
                     _redirect_trail(m),
                     " ".join(str(h) for h in (m.get("hostnames") or []))])


# A NON-PRODUCTION system on the public internet is a first-rank finding regardless of what it runs:
# test data is real data, test instances are patched last, and their credentials are weakest.
# Matched on a delimited token so "attestation", "protest" and "devices" do not trigger it.
_NONPROD_RE = re.compile(
    r"(?i)(?<![a-z])(test|testing|dev|devel|development|staging|stage|uat|qa|sandbox|preprod"
    r"|pre-prod|demo|poc|lab|training|schulung|abnahme)(?![a-z])")

# Enterprise content, DAM and identity platforms. These hold the crown jewels and hide behind a
# generic reverse proxy, so they never match on `product`. OpenText OTMM/OTDS is the adpolice case.
_ECM_RE = re.compile(
    r"(?i)(otmm|otdsws|opentext|documentum|media management|digital asset management"
    r"|alfresco|nuxeo|sharepoint|filenet|hyland|onbase|laserfiche|m-files|elo enterprise"
    r"|censhare|bynder|canto cumulus|adobe experience manager|/aem/)")


# OPERATIONAL TECHNOLOGY / BUILDING MANAGEMENT, identified by the NAME the customer gave the host.
#
# THE OPERATOR'S POINT, and the evidence is on his side: an OT or building-management interface
# reachable from the internet is not a HIGH, it is a CRITICAL. Jaguar Land Rover's September 2025
# intrusion stopped vehicle production for weeks; the Cyber Monitoring Centre put total UK economic
# damage at about GBP 1.9bn across 5,000+ organisations, with the manufacturer losing roughly GBP
# 108m per week of halted output. The distinguishing feature of that class of incident is not data
# loss, it is that PRODUCTION STOPS -- and a compromise reaching ventilation, heating, access
# control or a plant automation gateway has exactly that reach.
#
# ns03.ru published certificates for `ventil.nzn` (ventilation), `ventil2.nzn` and `ing.nzn`
# (инженерные системы, building services) at a named production branch. Those are not web servers.
_OT_WORDS = (
    # English
    "hvac", "bms", "bacnet", "modbus", "scada", "plc", "rtu", "hmi", "chiller", "boiler",
    "ventilation", "cooling", "heating", "access-control", "badge", "turnstile", "cctv",
    # German
    "lueftung", "luftung", "heizung", "klima", "kessel", "zutritt", "leitstand", "gebaeude",
    # Russian (transliterated, as they appear in hostnames)
    "ventil", "ventilyaciya", "kotel", "kotelnaya", "skud", "energo", "teplo", "nasos",
    "avtomatika", "dispetcher", "elektro",
)
_OT_RE = re.compile(r"(?<![a-z])(" + "|".join(_OT_WORDS) + r")(?![a-z])", re.I)
# Ambiguous on their own; admissible ONLY inside a site zone already proven to be OT.
_OT_WEAK_RE = re.compile(r"^(ing|eng|tech|avt|em|bms|ot|prom|proiz)\d*$", re.I)


def ot_names(resolved, apexes=()):
    """Hostnames that name an OT / building-management function and resolve on the public internet.

    PASSIVE AND EVIDENCE-BASED. The evidence is the customer's own DNS record plus, usually, a
    certificate they requested for that name. What this does NOT claim is that the service is
    vulnerable, or even what it is: confirming that needs the customer, and the finding says so.
    Naming a host `ventil` is not proof of a ventilation controller -- but on a production site it
    is a far better hypothesis than chance, and it is the operator's own estate to confirm.
    """
    out, zones = [], set()
    for name in sorted(resolved or {}):
        n = str(name).lower()
        if apexes and not any(n == a or n.endswith("." + a) for a in apexes):
            continue
        m = _OT_RE.search(n.split(".")[0]) or _OT_RE.search(n)
        if m:
            out.append({"name": name, "token": m.group(1), "why": "name",
                        "addresses": sorted(resolved[name])[:3]})
            labs = n.split(".")
            if len(labs) >= 3:
                zones.add(".".join(labs[1:]))       # the site zone the OT host lives in

    # CORROBORATION FOR THE AMBIGUOUS TOKENS. `ing` is the Russian abbreviation for инженерные
    # системы (building services) and it is also a substring of half the internet -- marketing,
    # hosting, a surname. On its own it is exactly the common-word anchor the abakus incident
    # taught us to refuse. But a host called `ing` sitting in the SAME SITE ZONE as a confirmed
    # ventilation controller is corroborated by that zone, which is the standard this engine
    # applies to every other weak signal.
    for name in sorted(resolved or {}):
        n = str(name).lower()
        if any(o["name"] == name for o in out):
            continue
        labs = n.split(".")
        if len(labs) >= 3 and ".".join(labs[1:]) in zones and _OT_WEAK_RE.match(labs[0]):
            out.append({"name": name, "token": labs[0], "addresses": sorted(resolved[name])[:3],
                        "why": "shares the site zone %s with a confirmed OT host" % ".".join(labs[1:])})
    return out


def _eol_hit(m):
    """(sev, kind, detail) when the banner we ALREADY hold names an out-of-support version.

    ZERO PACKETS. The ns03.ru engagement read the OWA build path by connecting to the server; the
    same string is frequently present in a scan engine's stored record, and mapping it there costs
    nothing and touches nobody. Running software past its end of support means no security update
    exists for the next vulnerability, whatever the patching process does.
    """
    info = active_probe.eol_from_banner(_hay(m))
    if not info:
        return "", "", None
    return "HIGH", "eol_software", info


def _high_value_hit(m):
    """(sev, kind) for a high-value management plane, or ('','') — checked BEFORE generic buckets."""
    hay = _hay(m)
    port = m.get("port")
    if _SECRETS_RE.search(hay):
        return "CRITICAL", "secrets_manager"        # the credentials to everything else
    if _NAS_RE.search(hay) or (port in _NAS_PORTS and re.search(r"(?i)dsm|diskstation|qnap", hay)):
        return "CRITICAL", "nas_exposed"            # #1 SME ransomware target
    if _BACKUP_RE.search(hay):
        return "CRITICAL", "backup_console"         # own the backups, own the recovery
    if _PBX_RE.search(hay) or port in (5060, 5061):
        return "HIGH", "pbx_exposed"                # toll fraud + 3CX supply-chain history
    # An enterprise content / DAM / records platform is a crown-jewel store. On adpolice.gov.ae the
    # engine had the OpenText redirect chain in hand and still called the host a mail gateway.
    _nonprod = bool(_NONPROD_RE.search(hay))
    if _ECM_RE.search(hay):
        return ("CRITICAL" if _nonprod else "HIGH"), ("nonprod_exposed" if _nonprod else "ecm_exposed")
    # Any non-production system on the public internet, whatever it runs.
    if _nonprod and (port in (80, 443, 8080, 8443) or (m.get("http") or {}).get("title")):
        return "HIGH", "nonprod_exposed"
    return "", ""


def _appliance_hit(m):
    """Return the appliance family name if this host is an edge security appliance, else ''."""
    prod = (m.get("product") or "") + " " + (m.get("version") or "")
    ssl = (m.get("ssl") or {}).get("cert") or {}
    subj = ssl.get("subject") or {}; iss = ssl.get("issuer") or {}
    hay = " ".join([prod, str(subj.get("CN", "")), str(subj.get("O", "")),
                    str(iss.get("CN", "")), str(iss.get("O", "")),
                    ((m.get("http") or {}).get("server") or ""),
                    ((m.get("http") or {}).get("title") or "")])
    mm = _APPLIANCE_RE.search(hay)
    return mm.group(0) if mm else ""


def _scope_line(ident):
    """One SHORT line for the deck's DATA SOURCE footer field.

    This used to interpolate EVERY domain. Once group discovery started enumerating the whole
    corporate group the string reached ~4,000 characters and was rendered into a 3.1-inch footer
    box — the deck's title slide became an unreadable block of overlapping text. A summary belongs
    in the footer; the full inventory belongs on the asset slide, where it already is.
    """
    doms = list(ident.get("domains") or [])
    apexes = sorted({_apex(d) for d in doms if _apex(d)})
    asns = ",".join(ident.get("asns") or []) or "\u2014"
    nets = len(ident.get("nets") or [])
    if not doms:
        dom_txt = "\u2014"
    elif len(apexes) <= 3:
        dom_txt = ", ".join(apexes)
    else:
        dom_txt = "%s +%d more (%d hostnames)" % (", ".join(apexes[:2]), len(apexes) - 2, len(doms))
    if not apexes:
        # No domains is a legitimate outcome for an ASN/prefix-seeded run — do not render an empty
        # field with a dangling em-dash ("0 domains: —"), which reads as missing data rather than
        # as the accurate statement that scope is the routed estate.
        return "ASN %s \u00b7 %d prefixes \u00b7 scope: routed estate (no domains resolved)" % (asns, nets)
    return "ASN %s \u00b7 %d prefixes \u00b7 %d domain%s: %s" % (
        asns, nets, len(apexes), "" if len(apexes) == 1 else "s", dom_txt)


def classify(m):
    port = m.get("port"); prod = (m.get("product") or ""); vulns = m.get("vulns") or {}
    ssl = m.get("ssl") or {}; tags = m.get("tags") or []
    title = ((m.get("http") or {}).get("title") or "")
    # HIGH-VALUE MANAGEMENT PLANES FIRST. These hide behind a generic reverse proxy (nginx on 443),
    # so they must be tested before the port-based buckets or they fall through to standard_service —
    # which is exactly how an internet-facing Passbolt vault produced "CRITICAL 0".
    _hv_sev, _hv_kind = _high_value_hit(m)
    if _hv_sev:
        return _hv_sev, _hv_kind
    # OUT OF SUPPORT, read from the banner we already hold. Checked before the generic buckets for
    # the same reason as the management planes: an out-of-support Exchange behind IIS on 443 is
    # otherwise filed as `standard_service`, which is how a platform with no security updates
    # available ends up rated LOW. A detector that is never called cannot fire, so this line is
    # the point of the whole check.
    _eol_sev, _eol_kind, _ = _eol_hit(m)
    if _eol_sev:
        return _eol_sev, _eol_kind
    if "ics" in tags or "scada" in tags or port in ICS_PORTSET: return "CRITICAL","ics"
    if port in DB_PORTS:  return "CRITICAL","db_exposed"
    if port in (3389, 3390): return "CRITICAL","rdp"
    # exposed edge-appliance mgmt plane = KEV-heavy, CRITICAL — by product OR cert-issuer fingerprint
    if port in (264, 18264) or _is(prod, CRIT_APPLIANCES) or _appliance_hit(m):
        return "CRITICAL","edge_appliance"
    if vulns:             return "HIGH","vuln_tagged"
    if port in VPN_PORTS or re.search(r'(?i)fortinet|pulse|palo alto|sonicwall|citrix|cisco asa|openvpn|sophos', prod):
        return "HIGH","vpn_appliance"
    if port == 161 or port == 162 or "snmp" in (prod or "").lower():  # exposed SNMP = mgmt/info-disclosure
        return "HIGH","snmp_exposed"
    if port in REMOTE_HI: return "HIGH","remote_admin"
    if title and re.search(r'(?i)login|admin|portal|vpn|dashboard|phpmyadmin|webmin|outlook|exchange', title):
        return "HIGH","exposed_panel"
    # ---- THE TLS NEGATION BUG (adpolice.gov.ae, 2026-08) ----------------------------------------
    # Shodan's ssl.versions array lists EVERY protocol it tested and marks the UNSUPPORTED ones with
    # a leading minus:
    #     5.194.255.186:443  ['-TLSv1','-SSLv2','-SSLv3','-TLSv1.1','TLSv1.2','-TLSv1.3']
    # That host is TLS-1.2-only and correctly configured. The old line did `v.lstrip("-")` — it
    # STRIPPED the minus and then matched, so a host that had explicitly DISABLED TLS 1.0 was
    # reported as offering it. Every modern host lists its disabled protocols, so this raised a
    # legacy-TLS finding on essentially every host the engine ever saw. It is the single widest
    # false-positive source in the product's history and it affects every deck already delivered.
    # Filter on the SIGN, never on membership.
    versions = [str(v) for v in (ssl.get("versions") or [])]
    enabled = [v for v in versions if not v.startswith("-")]
    if any(v in ("TLSv1", "TLSv1.0", "SSLv3", "SSLv2", "TLSv1.1") for v in enabled):
        return "MEDIUM", "legacy_tls"
    cert = ssl.get("cert") or {}
    if cert.get("expired"): return "MEDIUM","expired_tls"
    # self-signed: issuer == subject, OR the issuer is a device/private CA (not a public CA)
    _iss = cert.get("issuer") or {}
    _isscn = str(_iss.get("CN", "") if isinstance(_iss, dict) else _iss)
    if (cert.get("issuer") and cert.get("issuer") == cert.get("subject")) or \
       (_isscn and not _is(_isscn, PUBLIC_CAS) and _OPAQUE_CA_RE.match(_isscn) is None
        and re.search(r"(?i)\b(ca|webca|self|internal|issuing)\b", _isscn)):
        return "MEDIUM","self_signed"
    if prod and m.get("version"): return "MEDIUM","verbose_banner"
    return "LOW","standard_service"

TEMPLATES = {
 "secrets_manager": ("Internet-facing secrets / password manager",
   ["This is the credential store for the rest of the estate: one successful authentication bypass or unpatched CVE here yields the keys to every other system, so it is the single highest-value target on the perimeter.",
    "Vault and password-manager products are actively scanned for and exploited within days of a CVE (Passbolt, Vaultwarden and Keycloak have all had authentication-bypass advisories), and a public login page permits unlimited offline credential stuffing.",
    "Under DSGVO Art. 32 and NIS2 Art. 21(2)(d)(i) a credential store is a critical asset requiring state-of-the-art access control; exposing its login to the whole internet is difficult to defend to a regulator."],
   [{"tag":"COLT","title":"SASE / ZTNA — remove the vault from the public internet",
     "body":"WHY THIS SERVICE: a patch closes one CVE; brokering the vault behind identity-aware access removes the entire public attack surface, so the next authentication-bypass advisory is a non-event. WHAT YOU GET: the vault reachable only by enrolled, MFA-verified identities on managed devices — credential stuffing and pre-auth exploits become impossible from the internet. HOW: a ZTNA connector inside your network, no inbound firewall rule, no published DNS record; delivered and operated as a managed service with 24x7 monitoring."},
    {"tag":"COLT","title":"Managed Security Service — patch orchestration prioritised by KEV/EPSS",
     "body":"WHY THIS SERVICE: vault CVEs are exploited in days, faster than a quarterly maintenance window. WHAT YOU GET: the vault tracked as a tier-0 asset with emergency patch SLAs. HOW: KEV/EPSS-driven prioritisation with operated change execution."},
    {"tag":"PSF","title":"Managed WAF — rate-limit and geofence the login until ZTNA is live",
     "body":"WHY THIS SERVICE: an immediate compensating control while the ZTNA rollout completes. WHAT YOU GET: brute-force and stuffing traffic stopped at the edge. HOW: managed WAF policy in front of the host, no application change."}],
   ["MITRE T1190","MITRE T1555","NIS2 Art.21(2)(d)","DSGVO Art.32"]),
 "nas_exposed": ("Internet-facing NAS / storage appliance",
   ["A NAS is where the file shares and often the backups live, which makes it the primary ransomware objective for a mid-sized business rather than a stepping stone.",
    "Synology and QNAP management interfaces are continuously scanned; Deadbolt and eCh0raix campaigns encrypted tens of thousands of internet-exposed appliances, and vendor advisories are frequently exploited before customers patch.",
    "If the appliance also holds the backup copies, a single compromise removes the recovery path — the NIS2 Art. 21(2)(c) business-continuity obligation."],
   [{"tag":"COLT","title":"SASE / ZTNA — take the NAS management plane off the internet",
     "body":"WHY THIS SERVICE: appliance firmware lags and cannot be hardened enough to survive continuous exploitation; removing public reachability ends the exposure class outright. WHAT YOU GET: staff and site-to-site access without a published management port. HOW: a managed ZTNA broker with MFA, no inbound NAT."},
    {"tag":"COLT","title":"Managed Firewall — allowlist management to known sources",
     "body":"WHY THIS SERVICE: a default-deny edge policy is enforced independently of the appliance's own settings. WHAT YOU GET: scanners never reach the login. HOW: a managed rulebase, change-controlled."},
    {"tag":"VENDOR","title":"Offline / immutable backup copy",
     "body":"WHY: an encrypted NAS must not also destroy the recovery point. WHAT YOU GET: a restorable copy outside the blast radius. HOW: immutable object storage or offline rotation, verified by restore test."}],
   ["MITRE T1190","MITRE T1486","NIS2 Art.21(2)(c)"]),
 "backup_console": ("Internet-facing backup / recovery console",
   ["Modern ransomware deletes backups before encrypting production, so the backup console is targeted first; owning it converts a recoverable incident into an existential one.",
    "Veeam and Acronis management components have carried critical pre-authentication CVEs (for example CVE-2023-27532) that were weaponised quickly, and the console holds credentials to every system it protects.",
    "NIS2 Art. 21(2)(c) requires backup and crisis management; an internet-reachable backup control plane undermines the control it is meant to provide."],
   [{"tag":"COLT","title":"SASE / ZTNA — the backup plane must never be internet-reachable",
     "body":"WHY THIS SERVICE: the console stores credentials for the whole estate, so exposure is a full-estate risk, not a single-host one. WHAT YOU GET: administrative access brokered per identity with MFA and session logging. HOW: ZTNA, no published port."},
    {"tag":"COLT","title":"Managed Security Service — monitor and alert on backup-plane authentication",
     "body":"WHY THIS SERVICE: backup deletion is the earliest reliable ransomware indicator. WHAT YOU GET: alerting on anomalous console logins and job deletions. HOW: log ingestion into managed monitoring with 24x7 response."}],
   ["MITRE T1490","MITRE T1190","NIS2 Art.21(2)(c)"]),
 "pbx_exposed": ("Internet-facing PBX / telephony management",
   ["An exposed PBX carries direct financial risk through toll fraud — attackers place premium-rate international calls, and losses accrue in hours, billed to the customer.",
    "3CX specifically was the vector of the CVE-2023-29059 supply-chain compromise, and SIP registrars are brute-forced continuously for extension credentials.",
    "Call metadata and recordings are personal data under DSGVO Art. 32, and a compromised PBX also enables convincing voice-phishing against staff and customers."],
   [{"tag":"COLT","title":"SASE / ZTNA — publish the PBX web client only to enrolled users",
     "body":"WHY THIS SERVICE: the softphone must reach the PBX, but the whole internet does not. WHAT YOU GET: remote working preserved while the management interface disappears from scans. HOW: ZTNA for the web client; the SIP trunk kept on managed voice transport instead of the public internet."},
    {"tag":"COLT","title":"Managed Voice / SIP trunking — carrier-side fraud controls",
     "body":"WHY THIS SERVICE: destination and spend limits stop toll fraud at the carrier, not after the invoice. WHAT YOU GET: capped exposure with anomaly alerting. HOW: SIP trunk policy plus monitoring."},
    {"tag":"COLT","title":"Managed Firewall — restrict SIP and mgmt to known peers",
     "body":"WHY THIS SERVICE: SIP needs a handful of peers, never 0.0.0.0/0. WHAT YOU GET: registrar brute-force eliminated. HOW: managed allowlist."}],
   ["MITRE T1190","MITRE T1621","DSGVO Art.32"]),
 "rdp":        ("Internet-facing RDP", ["#1 ransomware entry vector","Credential brute-force"], ["SASE / ZTNA — retire the exposed RDP; broker access with MFA","Managed Firewall — block 3389 at the edge"], ["MITRE T1133"]),
 "db_exposed": ("Exposed database", ["Direct data-exfiltration path","Often unauthenticated"], ["Managed Firewall — remove the DB from the internet","DPI / NDR — detect exfiltration attempts"], ["MITRE T1190"]),
 "ics":        ("Exposed ICS/OT protocol", ["Safety/availability impact","NIS2 / ISO 27001 driver"], ["Managed Firewall + IT/OT segmentation","SD-WAN secure OT transport; Managed DDoS protection (DDoS)"], ["MITRE ICS","NIS2 Art.21"]),
 "vuln_tagged":("Shodan-tagged vulnerabilities (CVE)", ["Pre-mapped exploit paths; check CISA KEV"], ["Managed WAF — virtual-patch the exposed CVE","Managed Security Service — KEV/EPSS-prioritised patch orchestration"], ["Shodan vulns","CISA KEV"]),
 "edge_appliance":("Exposed edge-security appliance (firewall / SSL-VPN / UTM)", ["KEV-heavy edge — WatchGuard / Barracuda / Fortinet / Citrix / Ivanti class; the #1 ransomware entry vector. An internet-facing appliance management plane is exploited faster than it can be patched."], ["SASE / ZTNA — retire the internet-facing appliance mgmt plane entirely (no public gateway to exploit)","Managed Firewall — restrict mgmt to an allowlist + enforce MFA","Managed Security Service — KEV/EPSS-prioritised virtual patching"], ["CISA KEV","MITRE T1133"]),
 "snmp_exposed":("Exposed SNMP management service", ["Internet-reachable SNMP (161/UDP) leaks device model, firmware, interfaces and topology — reconnaissance gold, and weak community strings enable config read/write."], ["Managed Firewall — block 161/162 at the edge; SNMP is a management protocol, never internet-facing","Managed Security Service — enforce SNMPv3 with auth+priv where monitoring is required"], ["MITRE T1046","BSI IT-Grundschutz"]),
 "vpn_appliance":("Exposed VPN / firewall mgmt", ["Edge-appliance CVEs = top ransomware vector"], ["SASE / ZTNA — replace the legacy VPN","Managed Firewall — restrict mgmt to allowlist + MFA"], ["CISA KEV"]),
 "remote_admin":("Exposed remote-admin (Telnet/VNC/WinRM/SMB)", ["Brute-force / cleartext protocols"], ["SASE / ZTNA — broker admin access","Managed Firewall — block cleartext admin ports"], ["MITRE T1133"]),
 "exposed_panel":("Exposed login / admin / OWA panel", ["Credential attacks; panel-CVE surface"], ["Managed WAF — shield the panel + rate-limit","SASE — identity-broker + geofence"], ["OWASP"]),
 "legacy_tls": ("Legacy / weak TLS (SSLv3/TLS1.0/1.1)", ["MITM / downgrade; PCI/DORA gap"], ["Managed Firewall — enforce TLS>=1.2 policy","Managed WAF — terminate modern TLS"], ["RFC 8996"]),
 "nonprod_exposed": ("Non-production system reachable from the public internet",
            ["A system whose own hostname or application banner identifies it as test, development, staging, UAT or a demo is reachable from the internet. Non-production environments are patched last, monitored least and configured most loosely — default credentials, verbose errors and debug endpoints survive there long after they are removed from production.",
             "Test systems are routinely loaded with a copy of real production data, so the data-protection exposure is identical to production while the control set is not. For a public authority that means real case, personnel or citizen records sitting behind the weakest configuration in the estate.",
             "This is also the classic lateral-movement entry point: the test instance usually authenticates against the same directory as production, so a credential harvested here is a credential that works there."],
            [{"tag": "COLT", "title": "Remove the non-production estate from the public internet",
              "body": "WHY THIS SERVICE: a test system has no legitimate reason to answer an anonymous request from the internet, and no patch cycle will ever make it as safe as production. Removing reachability is the only fix that scales. WHAT YOU GET: the environment stays fully usable to the people who need it and disappears from every scanner and every opportunistic attack. HOW: published through an identity-aware access layer, so access is by named user and device rather than by network position, with the public listener retired."},
             {"tag": "COLT", "title": "Access control before the application",
              "body": "WHY THIS SERVICE: the login page of a test instance is itself the exposure — it discloses the platform, the version and often the tenant. Authenticating at the edge means an unauthenticated request never reaches the application at all. WHAT YOU GET: brute force, credential stuffing and pre-auth vulnerabilities all stop at the edge. HOW: enforced at the access proxy with MFA, delivered and monitored as a managed service."},
             {"tag": "PSF", "title": "Environment inventory and separation review",
              "body": "WHY THIS SERVICE: non-production systems reach the internet because nobody owns the question of which environments exist and how they are reached. An inventory answers it once. WHAT YOU GET: a list of every environment, who may reach it and from where, plus the data-handling rules for test copies of live records. HOW: a structured workshop with the platform and application owners, ending in a documented separation standard."}],
            ["ISO/IEC 27001 A.8.31", "NIST SP 800-53 CM-2", "MITRE T1190"]),
 "ecm_exposed": ("Enterprise content / digital-asset platform exposed",
            ["An enterprise content-management or digital-asset platform is reachable from the internet. These systems are the document of record for an organisation — case files, media, contracts, evidence — so a single credential compromise yields the archive rather than one application's data.",
             "The platforms are large, integrate with the corporate directory and are typically internet-facing only for a small group of external contributors, which makes the exposure disproportionate to the use case.",
             "Their login portals disclose the product and the exact release in the redirect chain, giving an attacker a precise version to match against known vulnerabilities before sending a single unusual request."],
            [{"tag": "COLT", "title": "Publish the archive through identity-aware access",
              "body": "WHY THIS SERVICE: the platform needs to be reachable by named people, not by the internet. An access layer separates those two things, which no amount of patching does. WHAT YOU GET: external contributors keep working, the anonymous internet loses its route to the archive, and every access is attributable. HOW: published through a managed access proxy with MFA and per-group policy."},
             {"tag": "COLT", "title": "Managed WAF in front of the portal",
              "body": "WHY THIS SERVICE: where the portal must stay public, exploit delivery has to be blocked ahead of the application, because a content platform's patch cycle is measured in quarters. WHAT YOU GET: pre-authentication exploit attempts are stopped before they reach the software, with the attempts logged as evidence. HOW: deployed in front of the existing portal with no change to the application."}],
            ["ISO/IEC 27001 A.5.15", "MITRE T1190", "OWASP A01"]),
 # DNS-derived findings. These come from the zone, not from a Shodan record, and they are the two
 # cheapest real findings on a target whose whole estate is shared hosting -- abakus-tk.de, where
 # every Shodan observation belonged to a co-tenant, had both of them.
 "no_caa": ("No CAA record — any certificate authority may issue for this domain",
            ["A CAA record tells every public CA which issuers you authorise. Without one, ANY of the ~90 trusted CAs may issue a certificate for this domain, and a mis-issued or fraudulently obtained certificate is indistinguishable from a legitimate one to a browser.",
             "For an organisation whose brand is the trust vehicle in customer correspondence and invoicing, a valid certificate on a name the customer recognises is the missing piece of a convincing phishing or business-email-compromise campaign.",
             "This compounds with any hostname that resolves to an address no longer under the organisation's control: whoever receives that address next can complete an HTTP-01 or TLS-ALPN challenge and obtain a genuine certificate for the subdomain."],
            [{"tag": "COLT", "title": "Publish CAA and monitor issuance",
              "body": "WHY THIS SERVICE: a CAA record is a five-minute DNS change that removes an entire class of mis-issuance, and it is the only control that constrains which CAs may act on your name at all. WHAT YOU GET: issuance restricted to the authorities you actually use, plus certificate-transparency monitoring that alerts on any certificate issued for your domains. HOW: we publish the CAA set alongside your existing DNS, add the incident-report contact, and wire CT log monitoring into your alerting."},
             {"tag": "OSS", "title": "Certificate Transparency monitoring",
              "body": "WHY THIS SERVICE: CAA prevents; CT detects. Free CT monitors watch every public log and notify on certificates issued for your names, including ones you did not request. WHAT YOU GET: notification within minutes of an unexpected issuance. HOW: subscribe the domain set to a CT monitor and route alerts to the same mailbox that receives your security notifications."}],
            ["RFC 8659", "CA/Browser Forum Baseline Requirements", "BSI TR-02102"]),
 # EMAIL AUTHENTICATION. Pure DNS, zero packets, and the biggest gap the engine had: a company's
 # domain can be forged without a single exposed host. This is the delivery mechanism for the
 # business-email-compromise losses the C-BIQ deck prices, so it belongs beside the host findings.
 "eol_software": ("Software running past its end of support",
            ["The version identified here is past the vendor's end-of-support date. That is a different condition from being unpatched: for software out of support, no security update exists to apply, so the next vulnerability disclosed against it stays open permanently.",
             "This class of host is specifically hunted. Mail and collaboration platforms out of support have been the entry point for some of the most widely exploited intrusion campaigns of recent years, precisely because the population of unsupported installations is large and cannot be fixed by patching.",
             "It is also a compliance exposure in its own right: an operator running unsupported software on an internet-facing service will struggle to argue it has taken state-of-the-art technical measures, which is the standard both NIS2 Article 21 and GDPR Article 32 apply."],
            [{"tag": "COLT", "title": "Plan and execute the version upgrade",
              "body": "WHY THIS SERVICE: an out-of-support platform is usually still running because upgrading it is entangled with mailbox migration, connector rebuilds and an application nobody wants to touch. The blocker is the plan, not the software. WHAT YOU GET: a supported platform with a migration path that does not interrupt mail flow, and the entanglements identified before they become an outage. HOW: we inventory dependencies, stage the upgrade or the move to a hosted service, and cut over in a window you set."},
             {"tag": "COLT", "title": "Reduce exposure while the upgrade is planned",
              "body": "WHY THIS SERVICE: an upgrade takes months and the exposure is live now. Publishing the service through a proxy that terminates and inspects the session removes direct internet reachability without touching the platform. WHAT YOU GET: the vulnerable surface no longer addressable from the internet, immediately, with the upgrade proceeding on its own timetable. HOW: place the service behind a managed gateway with authentication in front of it."},
             {"tag": "OSS", "title": "Track end-of-support dates against the estate",
              "body": "WHY THIS SERVICE: end of support arrives on a published date, so it is the one exposure that can be prevented entirely by knowing it is coming. WHAT YOU GET: advance warning per product, mapped to the hosts that run it. HOW: reconcile your software inventory against published vendor lifecycle dates on a schedule."}],
            ["NIS2 Art. 21", "GDPR Art. 32", "ISO/IEC 27001 A.8.8"]),
 "exchange_onprem": ("Self-hosted Exchange is published to the internet, and it is past end of support",
            ["Autodiscover resolves to an address the organisation owns rather than to Microsoft 365, which means the mail platform is on-premises and its web endpoints — Outlook Web Access, Exchange Web Services, Autodiscover and MAPI — are reachable from the internet.",
             "Exchange Server 2016 and 2019 reached end of support on 14 October 2025, and the one-time Extended Security Update programme ended on 14 April 2026. An installation of either running today therefore has NO security update available at any price: the next vulnerability disclosed against it stays open permanently.",
             "This is not a theoretical class. Internet-facing Exchange has been the entry point for the most widely exploited intrusion campaigns of recent years, and the reason is structural: the platform authenticates the whole organisation, it is exposed by design, and the population of unsupported installations is large enough to be worth an attacker's tooling."],
            [{"tag": "COLT", "title": "Move the mailbox estate to a supported platform",
              "body": "WHY THIS SERVICE: an unsupported mail platform cannot be made safe by patching, because there are no patches. The only durable answers are migration to a hosted service or an upgrade to the current subscription edition, and both are entangled with connectors, relay rules and applications nobody has inventoried. That entanglement, not the software, is what makes this take months. WHAT YOU GET: a supported platform with mail flow uninterrupted and every dependency identified before it becomes an outage. HOW: we inventory the senders and connectors, stage the migration or upgrade, and cut over in a window you set."},
             {"tag": "COLT", "title": "Remove direct internet exposure now, while the migration runs",
              "body": "WHY THIS SERVICE: the migration takes months and the exposure is live today. Publishing the web endpoints through an authenticating gateway removes direct reachability without touching the platform itself. WHAT YOU GET: Outlook Web Access, Exchange Web Services and Autodiscover reachable only through brokered, authenticated access, so an unpatched server is no longer directly addressable from the internet. HOW: we place the endpoints behind a managed access gateway with modern authentication in front, then withdraw the public exposure."},
             {"tag": "COLT", "title": "Confirm the build and the authentication configuration",
              "body": "WHY THIS SERVICE: this finding is derived from public DNS and certificate data, which establishes that the platform is self-hosted and exposed but not which version or which authentication methods it offers. Both change the urgency materially. WHAT YOU GET: the exact cumulative update, whether legacy or basic authentication is still accepted, and a prioritised list. HOW: a short authenticated review with your messaging team, or an authorised external check under written authorisation."}],
            ["NIS2 Art. 21", "GDPR Art. 32", "ISO/IEC 27001 A.8.8", "CISA KEV"]),
 "cert_name_gap": ("Live hostnames that no certificate covers",
            ["These names resolve and answer, but no unexpired publicly-trusted certificate covers them. Every visitor reaching them over HTTPS is shown a browser trust warning before they see anything else.",
             "The operational effect is that the service is unusable to a careful visitor and, worse, that regular users are trained to click through certificate warnings to do their job. Once that habit exists, the warning that matters — the one raised by an actual interception — is dismissed with the same reflex.",
             "It is also a reliable indicator of an unmanaged endpoint: a name that was published without being added to the certificate is usually one that is outside whatever process governs the rest of the estate."],
            [{"tag": "COLT", "title": "Bring every published name under certificate management",
              "body": "WHY THIS SERVICE: the gap is almost never deliberate. A name gets published, the certificate is renewed from an old list, and nobody notices because the people who use that service learned to click through the warning. WHAT YOU GET: an inventory reconciled between what DNS publishes and what your certificates cover, with the gaps closed and an owner against each name. HOW: we reconcile the zone against certificate transparency and your own issuance records, then reissue to the corrected name set."},
             {"tag": "COLT", "title": "Automate issuance so the list cannot drift",
              "body": "WHY THIS SERVICE: a manually maintained certificate name list drifts every time a service is added. Automation removes the failure mode rather than correcting it once. WHAT YOU GET: certificates that follow the estate instead of trailing it. HOW: automated issuance and deployment against your existing authority, covering the appliances that are usually left out."},
             {"tag": "OSS", "title": "Monitor the gap continuously",
              "body": "WHY THIS SERVICE: the reconciliation is only true on the day it is done. WHAT YOU GET: an alert when a published name has no covering certificate. HOW: a scheduled comparison of the zone against public certificate logs."}],
            ["CA/Browser Forum Baseline Requirements", "ISO/IEC 27001 A.5.15", "NIS2 Art. 21"]),
 "ot_exposed": ("Operational-technology and building-management systems are named on the public internet",
            ["These hostnames name plant and building-services functions — ventilation, heating, engineering systems, access control — and they resolve publicly, with certificates the organisation requested for them. That is an operational-technology interface published to the internet, not an office application.",
             "The distinguishing feature of an intrusion that reaches this layer is not data loss, it is that production stops. Jaguar Land Rover's September 2025 compromise halted vehicle manufacturing for weeks; the Cyber Monitoring Centre assessed total United Kingdom economic damage at approximately GBP 1.9 billion across more than 5,000 organisations, with the manufacturer losing in the order of GBP 108 million for every week of stopped output.",
             "These systems are also the least defensible part of an estate: they run for a decade or more without a patch cycle, they authenticate weakly or not at all, and the teams that own them are engineering rather than IT. A control that is adequate for a web server is not available here, which is why the exposure itself has to be removed rather than monitored."],
            [{"tag": "COLT", "title": "Take the operational estate off the public internet",
              "body": "WHY THIS SERVICE: an engineering interface cannot be hardened to the standard the internet demands, because the equipment behind it was designed for a private network and cannot be patched on a monthly cycle. The only durable control is that it stops being reachable. WHAT YOU GET: plant and building systems reachable only through authenticated, brokered access, so a stolen credential or an unpatched controller is no longer directly addressable from the internet. HOW: we publish these services through a zero-trust access broker and withdraw the public DNS and firewall exposure, in a change window agreed with the engineering owner."},
             {"tag": "COLT", "title": "Segment the operational network from the corporate one",
              "body": "WHY THIS SERVICE: the damage in this class of incident comes from lateral movement into production after an ordinary corporate compromise, which is precisely how the Jaguar Land Rover outage propagated. Removing the internet exposure without segmenting the interior leaves the same path open from inside. WHAT YOU GET: an enforced boundary between office and plant networks with brokered, logged crossings, so an intrusion on one side does not stop production on the other. HOW: we map the existing flows, place enforcement at the boundary, and cut over without interrupting the process."},
             {"tag": "COLT", "title": "Confirm what each of these hosts actually is",
              "body": "WHY THIS SERVICE: these systems are identified here from their names and certificates, which is strong evidence of function but is not an inventory. An accurate one is the prerequisite for every decision that follows, and it usually does not exist because the equipment was commissioned by contractors rather than by the technology function. WHAT YOU GET: a confirmed register of the internet-facing operational estate, with an owner and a criticality against each entry. HOW: a short workshop with your engineering and facilities owners, reconciled against this external view."}],
            ["IEC 62443", "NIS2 Art. 21", "BSI ICS Security Compendium"]),
 "dmarc_missing": ("No DMARC policy — this domain can be forged and receiving servers are told nothing",
            ["DMARC is the record that tells a receiving mail server what to do with a message that claims to come from this domain but fails authentication. With no record published, the answer is: deliver it. Anyone can send mail as any address at this domain and it will land in the inbox looking legitimate.",
             "This needs no exposed host and no vulnerability. It is the standard opening move for invoice fraud and payment redirection, because a forged message from a real domain passes every human check an employee, customer or supplier applies.",
             "It also removes the organisation's own visibility: DMARC aggregate reports are the only mechanism that shows who is currently sending mail using this domain, so today nobody would know a campaign was running until a customer complained."],
            [{"tag": "COLT", "title": "Publish DMARC and move it to enforcement",
              "body": "WHY THIS SERVICE: DMARC cannot simply be switched to reject — that would break legitimate mail sent by payroll, marketing and ticketing systems nobody has inventoried. The work is the inventory, not the DNS record. WHAT YOU GET: a full picture of every system sending as your domain, then an enforcing policy that rejects forgeries without dropping a single legitimate message. HOW: publish at p=none with reporting, read the reports for a few weeks, authorise what is real, then step through quarantine to reject."},
             {"tag": "COLT", "title": "Align SPF and DKIM behind the policy",
              "body": "WHY THIS SERVICE: DMARC only passes if SPF or DKIM passes AND the domain aligns. A policy published over unaligned authentication rejects the company's own mail. WHAT YOU GET: SPF and DKIM configured for every legitimate sender, so enforcement is safe to switch on. HOW: we reconcile the sending inventory against the records and correct both together."},
             {"tag": "OSS", "title": "Aggregate report monitoring",
              "body": "WHY THIS SERVICE: the reports arrive as XML from every major mail provider and are unreadable by hand. WHAT YOU GET: a dashboard showing who sends as your domain, which sources fail, and whether enforcement is safe yet. HOW: point the rua address at a report processor and review it during the rollout."}],
            ["RFC 7489", "NIS2 Art. 21", "ISO/IEC 27001 A.5.14"]),
 "dmarc_weak": ("DMARC is published but does not reject anything",
            ["A DMARC record exists, which is often taken as the control being in place, but its policy does not instruct receivers to reject or quarantine a forgery. In its current state it is a monitoring configuration, not a defence.",
             "The practical consequence is identical to having no DMARC at all: a forged message claiming to be from this domain is delivered to the recipient's inbox. The difference is that the organisation may believe the control is working.",
             "Partial deployment has the same shape. A policy that applies to only a fraction of messages leaves the remainder delivered untouched, and an attacker only needs the messages that get through."],
            [{"tag": "COLT", "title": "Complete the rollout to enforcement",
              "body": "WHY THIS SERVICE: the hard part of DMARC is finishing it. Most deployments stall at monitoring because nobody owns the inventory of legitimate senders and nobody wants to be the person who blocked the invoice run. WHAT YOU GET: a policy at reject, with every legitimate sender authorised first, so forgeries stop and your own mail is unaffected. HOW: we read the existing reports, close the gaps in SPF and DKIM, then step the policy up in stages you approve."},
             {"tag": "COLT", "title": "Cover the subdomains too",
              "body": "WHY THIS SERVICE: a policy on the organisational domain can leave subdomains open depending on the sp tag, and a forged subdomain is just as convincing to a recipient. WHAT YOU GET: an explicit subdomain policy so there is no gap to find. HOW: one tag in the same record, verified against a test send."},
             {"tag": "OSS", "title": "Keep the reports under review",
              "body": "WHY THIS SERVICE: sending estates change every time a department buys a tool. Without ongoing report review, an enforcing policy eventually blocks something real and gets rolled back. WHAT YOU GET: early warning when a new sender appears. HOW: continuous processing of the aggregate reports you already receive."}],
            ["RFC 7489", "NIS2 Art. 21", "ISO/IEC 27001 A.5.14"]),
 "spf_weak": ("The SPF record does not usefully constrain who may send as this domain",
            ["SPF lists the servers permitted to send mail for a domain. The record published here does not achieve that: it either authorises everyone, expresses no opinion on an unlisted sender, or is malformed in a way that makes a receiving server stop evaluating it entirely.",
             "A receiver that cannot get a usable answer from SPF falls back to delivering the message. The record's presence therefore provides assurance to the organisation without providing protection to the recipient.",
             "SPF is also the foundation the DMARC policy stands on. An unusable SPF record means DMARC cannot be moved to enforcement safely, so this one record blocks the control that would actually stop forgery."],
            [{"tag": "COLT", "title": "Rebuild the SPF record against a real sender inventory",
              "body": "WHY THIS SERVICE: an SPF record accumulates includes for years as departments add tools, until it exceeds the ten-lookup limit and silently stops working. Rewriting it needs the sending inventory, which is the part nobody has. WHAT YOU GET: a compact, valid record that authorises exactly your real senders and ends in a hard fail. HOW: we enumerate the senders from your own mail flow and DMARC reports, then flatten and publish."},
             {"tag": "COLT", "title": "Bring it under the ten-lookup limit",
              "body": "WHY THIS SERVICE: RFC 7208 caps SPF evaluation at ten DNS lookups and a receiver must return a permanent error beyond it, which means no SPF at all. This is invisible without testing. WHAT YOU GET: a record that evaluates correctly at every receiver. HOW: consolidate includes, replace what can be expressed as addresses, and verify against live validators."},
             {"tag": "OSS", "title": "Automated record validation",
              "body": "WHY THIS SERVICE: the record breaks when somebody adds one more include, and nothing announces it. WHAT YOU GET: an alert when the record becomes invalid or approaches the limit. HOW: a scheduled validation check against the published record."}],
            ["RFC 7208", "NIS2 Art. 21", "ISO/IEC 27001 A.5.14"]),
 # CERTIFICATE INTELLIGENCE. From Certificate Transparency, which cannot be blocked and which sees
 # hosts a scanner cannot -- the ns03.ru estate returned nothing to Shodan across twelve queries.
 "cert_revoked_live": ("A revoked certificate covers a hostname that is still live",
            ["A certificate authority has revoked these certificates, which is a formal statement that they must no longer be trusted. The hostnames they cover still resolve in public DNS.",
             "Revocation is normally requested for one of two reasons, and both matter here: the private key was exposed or suspected of exposure, or the service was decommissioned. If it was a key incident, the question is whether the replacement key was generated cleanly and whether anything else shared that key.",
             "If instead the service was retired, the DNS record outliving it is the dangling-record problem: whoever is assigned that address next controls what visitors reach at a name that still carries the organisation's brand."],
            [{"tag": "COLT", "title": "Close out the revocation",
              "body": "WHY THIS SERVICE: a revocation is an unfinished incident until somebody records why it happened. If a key was compromised, every other service that shared that key or that host is in scope, and nothing in the certificate tells you which. WHAT YOU GET: a documented reason for each revocation, the blast radius if it was a key event, and confirmation the replacement was issued to a fresh key. HOW: we reconcile the revocations against your change records and certificate inventory."},
             {"tag": "COLT", "title": "Retire the DNS record if the service is gone",
              "body": "WHY THIS SERVICE: decommissioning a server and editing the zone are two tasks owned by different people, so the record survives the service by months. WHAT YOU GET: a zone where every name points at something you still control. HOW: reconcile the zone against the live estate and retire what is stale, with the retirement step wired into your change process."},
             {"tag": "OSS", "title": "Certificate Transparency monitoring",
              "body": "WHY THIS SERVICE: revocations and new issuance both appear in public logs within minutes, and nobody is watching them. WHAT YOU GET: notification when a certificate for your names is issued or revoked. HOW: subscribe the domain set to a CT monitor routed to your security mailbox."}],
            ["RFC 5280", "CA/Browser Forum Baseline Requirements", "ISO/IEC 27001 A.5.15"]),
 "cert_expiring": ("Certificates are days from expiry on live hostnames",
            ["These certificates expire within weeks on hostnames that are answering today. A lapse is not a degradation: at the moment of expiry every browser, mobile application and machine-to-machine client refuses the connection outright, and it happens to all users simultaneously.",
             "Expiry is the one outage with a published date, which makes it the one that should never occur. When it does, the cause is almost always that renewal was manual and the person who owned it changed role, or that automated renewal has been failing quietly for weeks.",
             "The operational damage is compounded by the response: an expiry outage is usually resolved under pressure, which is when a certificate ends up issued to a hastily generated key or deployed with an incomplete chain."],
            [{"tag": "COLT", "title": "Automate issuance and renewal",
              "body": "WHY THIS SERVICE: a calendar reminder is not a control, because it depends on a person still being in the role. Automated issuance removes the failure mode rather than reminding somebody about it. WHAT YOU GET: certificates that renew and deploy without human involvement, on every host including the appliances that are usually left out. HOW: we deploy an automated client against your existing authority and cover the exceptions individually."},
             {"tag": "COLT", "title": "Inventory and expiry alerting",
              "body": "WHY THIS SERVICE: renewal that fails silently looks exactly like renewal that works, until the day it does not. WHAT YOU GET: a single inventory of every certificate you serve, with alerting well before expiry and an owner against each one. HOW: continuous discovery from public logs plus your own estate, reconciled into one list."},
             {"tag": "OSS", "title": "External expiry monitoring",
              "body": "WHY THIS SERVICE: monitoring that runs inside the estate cannot see what an outside client sees, including chain and intermediate problems. WHAT YOU GET: an independent check from outside your network. HOW: scheduled external probes of the published names."}],
            ["CA/Browser Forum Baseline Requirements", "ISO/IEC 27001 A.5.15", "NIS2 Art. 21"]),
 "cert_shared_key": ("One certificate and one private key serve several separate services",
            ["A single certificate covers several distinct services here. That means one private key must be installed on every host that serves any of those names, and the security of all of them is the security of the weakest.",
             "The consequence is concentration. Exposure of that key on the least-defended of those hosts allows impersonation of all of them, including the mail and gateway services that carry the most trust. A single botched renewal takes every one of them offline at the same moment.",
             "It also constrains operations: the services can no longer be moved, re-hosted or handed to different teams independently, because they are tied together by a shared secret rather than by any deliberate design decision."],
            [{"tag": "COLT", "title": "Separate the certificates by service",
              "body": "WHY THIS SERVICE: shared certificates are almost always an artefact of a manual purchase where adding a name was cheaper than buying another certificate. With automated issuance that saving disappears and the coupling has no remaining justification. WHAT YOU GET: an independent certificate and key per service, so a compromise or a renewal failure is contained to one. HOW: automated per-service issuance, cut over one service at a time with no interruption."},
             {"tag": "COLT", "title": "Reduce where the key is present",
              "body": "WHY THIS SERVICE: the key is currently on every host serving any of these names, which is a larger footprint than any of those services needs individually. WHAT YOU GET: each key present only where it is used, and terminated at the edge rather than distributed. HOW: consolidate termination and reissue per service."},
             {"tag": "OSS", "title": "Track key reuse across the estate",
              "body": "WHY THIS SERVICE: key reuse is visible in public logs and is a reliable indicator of shared administration you did not intend. WHAT YOU GET: visibility of which hosts share a key. HOW: monitor the public key fingerprint across issued certificates."}],
            ["ISO/IEC 27001 A.5.15", "NIST SP 1800-16", "CA/Browser Forum Baseline Requirements"]),
 "cert_unauthorised": ("Certificates issued outside your own CAA policy",
            ["A CAA record names the certificate authorities you authorise to issue for this domain. Certificate Transparency logs show live, publicly-trusted certificates for these names issued by an authority your CAA record does not list.",
             "The common cause is not an attack: it is a certificate bought outside the process everyone believes is mandatory, by a team that needed a site up quickly. It means the inventory of who can present your name to a customer is incomplete, and nobody is monitoring the part that is missing.",
             "The serious cause is the same evidence: a certificate obtained by someone who proved control of the name without your knowledge. Both are indistinguishable to a browser, and both are visible here only because CT logging is mandatory."],
            [{"tag": "COLT", "title": "Reconcile certificate issuance against policy",
              "body": "WHY THIS SERVICE: a CAA record only constrains authorities that honour it at issuance time; it does not remove certificates already issued, and nothing tells you about them unless somebody is watching the logs. WHAT YOU GET: a reconciled inventory of every live certificate for your names, each one attributed to an owner and an authority, and the ones nobody claims retired. HOW: we pull the Certificate Transparency record for the domain set, match it against your CAA policy and your known estate, and hand back the exceptions with an owner beside each."},
             {"tag": "OSS", "title": "Continuous Certificate Transparency monitoring",
              "body": "WHY THIS SERVICE: this finding is a snapshot. Issuance is continuous, so the control has to be too. Free CT monitors watch every public log and alert within minutes of a certificate appearing for a name you own. WHAT YOU GET: notification of the next unexpected certificate rather than a discovery at the next assessment. HOW: subscribe the domain set to a CT monitor and route the alerts to the mailbox that already receives your security notifications."},
             {"tag": "COLT", "title": "Tighten the CAA record set",
              "body": "WHY THIS SERVICE: if an authority is legitimately in use it belongs in the CAA record, and if it is not, the record is what stops the next one. Either way the policy and the reality have to be made to agree. WHAT YOU GET: a CAA set that lists exactly the authorities you use, including the wildcard and reporting entries, so a future exception is unambiguous. HOW: one DNS change per domain, published alongside your existing records."}],
            ["RFC 8659", "CA/Browser Forum Baseline Requirements", "ISO/IEC 27001 A.5.15"]),
 "dns_no_service": ("Hostnames resolve to addresses with no observable service — possible dangling DNS",
            ["These names still resolve in public DNS, but no service is observable at their addresses in public data. That is consistent with a decommissioned host whose DNS record was never removed.",
             "If the address has been returned to the hosting provider and reassigned, whoever receives it next controls what your customers reach at that hostname — and can complete a domain-validation challenge to obtain a genuine TLS certificate for it.",
             "This is reported as a CANDIDATE, not a confirmed weakness: absence of a record in public data is not proof that a host is gone. Confirm which of these are still in service, and the assessment will be rebuilt with your answer."],
            [{"tag": "COLT", "title": "DNS hygiene review and record retirement",
              "body": "WHY THIS SERVICE: dangling records accumulate silently because decommissioning a server and editing a zone are two different tasks owned by two different people. A review catches them in one pass. WHAT YOU GET: a zone where every record points at something you still control, and a retirement step wired into your change process so it does not recur. HOW: we reconcile the zone against your live estate, retire what is stale, and hand back a documented record set."},
             {"tag": "COLT", "title": "Publish CAA to blunt the takeover path",
              "body": "WHY THIS SERVICE: a dangling record becomes dangerous mainly because a stranger can get a valid certificate for it. CAA closes that even before the record is cleaned up. WHAT YOU GET: issuance restricted to your own authorities, so a reassigned address cannot be turned into a trusted lookalike. HOW: one DNS change, deployed alongside the record retirement above."}],
            ["MITRE T1584.001", "NIST SP 800-81", "BSI IT-Grundschutz NET.2"]),
 "expired_tls":("Expired TLS certificate", ["Trust failure; eases MITM"], ["Managed Security Service — certificate lifecycle + monitoring"], []),
 "self_signed":("Self-signed certificate", ["No trust anchor"], ["Managed Security Service — CA-signed certs + automated renewal"], []),
 "verbose_banner":("Verbose service banners", ["Eases attacker recon"], ["Managed WAF / Firewall — suppress product/version banners"], []),
 "standard_service":("Standard services exposed", ["Baseline exposure — monitor for drift"], ["Managed DDoS protection (DDoS) for exposed services; Managed Firewall — confirm intended"], []),
}
SEV_ORDER = ["CRITICAL","HIGH","MEDIUM","LOW"]

# ------------------------------------------------------------------- run ---
def run(ident, F, audience, limit_per_query=500):
    import shodan
    api = shodan.Shodan(os.environ["SHODAN_API_KEY"])
    own_asns = set(ident["asns"])
    hosts = {}; asns=set(); countries=set(); records=0; dropped=0; inv={}
    _by_dom = {}          # discovered domain -> {ips it returned}
    _no_dom = set()       # ips proved by something NOT attributable to one discovered domain

    # ---- RARITY GATE ON BRAND SELECTORS (the abakus-tk.de failure, 2026-08) ---------------------
    # "Abakus" is the German word for abacus. ssl:"abakus" / http.title:"abakus" / http.html:"abakus"
    # therefore matched dozens of unrelated companies across Cloudflare, Hetzner, OVH, Vultr,
    # Scaleway, Infomaniak, Google and Amazon: 192 IPs, 44 ASNs, 15 countries, for a target with
    # ZERO announced prefixes. These clauses are cat="identity", which means they ALSO bypass the
    # CDN/hoster drop below and are never put through _corroborates -- so nothing was checking them
    # at all.
    # This is the SAME test _private_ca_ok has run since bibeltv: ask Shodan how many hosts the
    # selector matches globally, and refuse it if the answer says it is not distinctive. It is
    # vendor-agnostic, needs no word list, costs one count() call, and it runs BEFORE the query so
    # no credits are burned on a selector we are going to discard anyway.
    BRAND_MAX_HOSTS = int(os.environ.get("BRAND_MAX_HOSTS", "2000"))
    _rejected_sel = {}

    def _selector_is_distinctive(f):
        if f.get("guard") != "rarity":
            return True
        try:
            n = int((api.count(f["clause"]) or {}).get("total", 0))
        except Exception as e:
            # Fail OPEN but say so: count() is unavailable on some plans, and silently dropping
            # every brand clause would gut recall on targets where the brand is genuinely rare.
            print("[auto] rarity check unavailable for %s (%s) - clause kept"
                  % (f["clause"], type(e).__name__), file=sys.stderr)
            return True
        if n > BRAND_MAX_HOSTS:
            _rejected_sel[f["clause"]] = n
            print("[auto] brand selector REFUSED: %s matches %d hosts globally (> %d) - it is a "
                  "common word, not an ownership anchor" % (f["clause"], n, BRAND_MAX_HOSTS),
                  file=sys.stderr)
            return False
        return True

    for f in [f for f in F if f.get("run")]:
        if not _selector_is_distinctive(f):
            continue
        q = f["clause"]; cat = f.get("cat", "sweep")
        _fdom = f.get("dom")
        n = 0
        try:
            for m in api.search_cursor(q):
                tags = m.get("tags") or []
                if "honeypot" in tags: dropped += 1; continue
                if cat == "sweep":
                    horg = (m.get("org") or "") + " " + (m.get("isp") or "")
                    masn = ("AS" + str(m.get("asn"))) if str(m.get("asn") or "").isdigit() else (m.get("asn") or "")
                    if _is(horg, CDNS) and (own_asns and masn not in own_asns): dropped += 1; continue
                hosts.setdefault(m.get("ip_str"), []).append(m)
                if _fdom:
                    _by_dom.setdefault(_fdom, set()).add(m.get("ip_str"))
                else:
                    _no_dom.add(m.get("ip_str"))
                ma = m.get("asn"); c = (m.get("location") or {}).get("country_code")
                if ma:
                    asns.add(ma)
                    e = inv.setdefault(ma, {"holder": None, "cc": set(), "ips": set()})
                    e["holder"] = e["holder"] or (m.get("org") or m.get("isp"))
                    if c: e["cc"].add(c)
                    e["ips"].add(m.get("ip_str"))
                if c: countries.add(c)
                n += 1
                if n >= limit_per_query: break
        except shodan.APIError as e:
            print(f"[warn] query {q!r}: {e}", file=sys.stderr)
    # ---- PER-DOMAIN CONTRIBUTION BUDGET (the abakus-tk.de failure, 2026-08) ----------------------
    # abakus-tk.de is a 20-person reseller with one shared IONOS VIP. The deck claimed 401 IPs across
    # 42 ASNs and 49 countries, 236 of them Meta's, because `wa.me` -- the WhatsApp shortener in the
    # site footer -- was harvested as a subsidiary and became a first-class seed.
    #
    # The upstream causes are fixed (anchored STRUCTURE_HINTS, scope_deny, a real gate on group
    # domains). This is the guard that does NOT depend on any of them being right. It is the
    # generalisation of the per-pivot budget to IDENTITY queries, and it exists because of a
    # structural blind spot the lotto24 fix did not cover:
    #
    #   `identity_ips = set(hosts)` is the baseline every later guard measures against, and it is
    #   assigned AFTER all identity queries have run. When the poison arrives THROUGH an identity
    #   query, it becomes part of the baseline. scope_blowout compared 401 hosts against a baseline
    #   of 401 and could never fire; the co-tenant guard exempted the Meta hosts because `wa.me` was
    #   registered as an owned apex. One bad domain disarmed every downstream check at once.
    #
    # So each DISCOVERED domain is now measured on its own, against what the SEED itself proved.
    # A subsidiary may enlarge the estate; it may not BE the estate.
    if _rejected_sel:
        ident["selectors_refused"] = [{"clause": c, "global_hosts": n}
                                      for c, n in sorted(_rejected_sel.items())]
    _seed_ap = _apex(ident["domains"][0]) if ident.get("domains") else None
    _seed_proved = set(_no_dom) | set(_by_dom.get(_seed_ap, set()))
    DOMAIN_MAX_ADD = int(os.environ.get("DOMAIN_MAX_ADD", "40"))
    _dom_budget = max(DOMAIN_MAX_ADD, 3 * len(_seed_proved))
    ident["domain_budget"] = _dom_budget
    for _d in sorted(_by_dom, key=lambda x: -len(_by_dom[x])):
        if not _d or _d == _seed_ap:
            continue
        _others = set(_no_dom)
        for _o, _ips in _by_dom.items():
            if _o != _d:
                _others |= _ips
        _exclusive = _by_dom[_d] - _others          # hosts ONLY this domain brought in
        if len(_exclusive) <= _dom_budget:
            continue
        for _ip in _exclusive:
            hosts.pop(_ip, None)
        print("[auto] domain ROLLED BACK: %s contributed %d hosts on its own but the budget is %d "
              "(the seed proved %d). A discovered domain may enlarge the estate, never be it."
              % (_d, len(_exclusive), _dom_budget, len(_seed_proved)), file=sys.stderr)
        ident.setdefault("domains_rolled_back", []).append(
            {"domain": _d, "added": len(_exclusive), "budget": _dom_budget,
             "seed_proved": len(_seed_proved)})
        # Strip it from the owned set too, or the co-tenant guard would still treat every host
        # carrying its name as the customer's -- which is exactly how the Meta hosts survived.
        ident["domains"] = [x for x in (ident.get("domains") or []) if _apex(str(x)) != _d]
        ident["group_domains"] = [x for x in (ident.get("group_domains") or []) if x != _d]
        ident.setdefault("related_unscoped", [])
        if _d not in ident["related_unscoped"]:
            ident["related_unscoped"].append(_d)

    # auto-harvest the internal-CA issuer pivot: PRIVATE issuers seen on the estate -> re-pivot.
    # Every candidate goes through _private_ca_ok(), which fails closed. See the bibeltv.de incident:
    # 'R12'/'YR2' are public intermediates and this pivot imported ~998 strangers' hosts.
    identity_ips = set(hosts)          # what the identity/ASN queries proved — the baseline estate
    seen_iss = {}
    for _ms in hosts.values():
        for _m in _ms:
            _cn = (((_m.get("ssl") or {}).get("cert") or {}).get("issuer") or {}).get("CN")
            if _cn: seen_iss[_cn] = seen_iss.get(_cn, 0) + 1
    pivot_added = 0

    # ---- PER-PIVOT BUDGET (the lotto24.de failure, 2026-07) --------------------------------------
    # A malformed pivot phrase (org:"Lotto24 AG Hamburg, Germany") added 381 hosts to an estate whose
    # identity queries had proved 15. Every downstream guard then behaved exactly as designed and the
    # run still died: the co-tenant guard correctly identified 379 of them, hit its own >75% "an
    # automatic filter must not empty a deck" valve, refused, and the scope-blowout check aborted the
    # whole assessment. The operator got nothing.
    #
    # The lesson is not "fix that string" (done above) — it is that ONE unverified selector was able
    # to own the estate at all. A pivot exists to WIDEN scope at the margin. If a single one adds
    # more than the whole proven estate several times over, it has over-matched, whatever the reason,
    # and the correct response is to discard THAT PIVOT and keep the assessment, not to discard the
    # assessment. Recall is cheap; a stranger's infrastructure in a customer deck is not; and a
    # refusal that produces no deck at all helps nobody.
    #
    # Rollback is whole-pivot and includes its ASNs: a bad selector's ASNs must not survive to widen
    # a later sweep. Raise PIVOT_MAX_ADD only for a target you have verified by hand.
    PIVOT_MAX_ADD = int(os.environ.get("PIVOT_MAX_ADD", "60"))
    # AND IT MUST NEVER EXCEED WHAT THE BLOW-OUT CHECK WILL ACCEPT.
    #
    # Two guards with independent thresholds, and the pivot budget was the LOOSER of the two: it
    # floors at 60 while the blow-out refusal fires above max(25, 4*identity). On a small estate —
    # 6 proven hosts, threshold 24 — the pool would happily authorise 60 additions and the run would
    # then be REFUSED for a total the budget had just approved. Guards that do not agree on the
    # limit produce exactly the outcome both exist to prevent: no deck at all. Same class as the
    # lotto24 finding that three individually-correct guards composed into a total failure.
    _blowout_max = max(25, 4 * max(1, len(identity_ips)))
    _pivot_budget = max(PIVOT_MAX_ADD, 3 * len(identity_ips))
    _pivot_budget = max(0, min(_pivot_budget, _blowout_max - len(identity_ips)))
    ident["pivot_budget"] = _pivot_budget

    # AND THE SAME BUDGET ACROSS ALL PIVOTS TOGETHER.
    #
    # bottomline.com, 2026-08-21: the per-pivot rule worked perfectly and the assessment still died.
    #     org:"BOTTOMLINE TECHNOLOGIES (DE)"  +310  > 270  -> ROLLED BACK   (correct)
    #     org:"BOTTOMLINE TECHNOLOGIES"       +202  <= 270 -> kept
    #     org:"Bottomline Technologies"       +117  <= 270 -> kept
    # Each survivor was individually "widening at the margin"; together they added 330 to a 90-host
    # proven estate, the scope-blowout check then fired at 420, and the operator got NOTHING.
    # A rule enforced one pivot at a time does not bound N pivots — three at 75% of budget is 225%.
    # The principle was always "a pivot may widen scope, never own it", and OWN is a property of the
    # total. So the budget is now a POOL: whatever is left after earlier pivots is what the next one
    # may spend, and a pivot that would exceed the remainder is rolled back whole, exactly as before.
    _pool = {"spent": 0}

    def _accept_pivot(label, added, added_asns):
        """Commit a pivot's hosts, or roll the whole pivot back if it dominates the estate."""
        _left = _pivot_budget - _pool["spent"]
        if len(added) <= _left:
            _pool["spent"] += len(added)
            for _a in added_asns:
                asns.add(_a)
            return len(added)
        if len(added) <= _pivot_budget:      # fits the per-pivot rule, but the POOL is exhausted
            for _ip in added:
                hosts.pop(_ip, None)
            print("[auto] pivot ROLLED BACK: %s added %d hosts and only %d of the %d-host pivot "
                  "budget is left (%d already spent by earlier pivots). Pivots widen the estate "
                  "TOGETHER; the budget is the total, not per selector."
                  % (label, len(added), max(_left, 0), _pivot_budget, _pool["spent"]),
                  file=sys.stderr)
            ident.setdefault("pivots_rolled_back", []).append(
                {"pivot": label, "added": len(added), "budget": _pivot_budget,
                 "reason": "cumulative budget exhausted", "spent": _pool["spent"]})
            return 0
        for _ip in added:
            hosts.pop(_ip, None)
        print("[auto] pivot ROLLED BACK: %s added %d hosts but the budget is %d "
              "(identity queries proved %d). A single selector may widen scope, never own it."
              % (label, len(added), _pivot_budget, len(identity_ips)), file=sys.stderr)
        ident.setdefault("pivots_rolled_back", []).append(
            {"pivot": label, "added": len(added), "budget": _pivot_budget})
        return 0

    for _cn in [c for c, n in sorted(seen_iss.items(), key=lambda x: -x[1]) if n >= 2][:6]:
        if _cn in ident.get("internal_cas", []): continue
        ok, why = _private_ca_ok(_cn, ident, api)
        if not ok:
            print(f"[auto] internal-CA pivot REFUSED on {_cn!r}: {why}", file=sys.stderr)
            continue
        ident.setdefault("internal_cas", []).append(_cn)
        print(f"[auto] internal-CA pivot on {_cn!r} ({why})", file=sys.stderr)
        try:
            k = 0; skipped = 0; _add, _aasn = [], []
            for _m in api.search_cursor(f'ssl.cert.issuer.cn:"{_cn}"'):
                ip2 = _m.get("ip_str")
                if ip2 and ip2 not in hosts:
                    # a pivot may only ADD a host it can independently tie to the target
                    if not _corroborates(_m, ident, own_asns):
                        skipped += 1
                    else:
                        hosts.setdefault(ip2, []).append(_m)
                        if _m.get("asn"): _aasn.append(_m["asn"])
                        _add.append(ip2)
                k += 1
                if k >= limit_per_query: break
            kept = _accept_pivot("internal-CA %r" % _cn, _add, _aasn)
            pivot_added += kept
            print(f"[auto]   pivot {_cn!r}: +{kept} hosts, {skipped} rejected (no tie to target)",
                  file=sys.stderr)
        except shodan.APIError:
            pass

    # auto-harvest the CERT SUBJECT-O pivot: the seed cert (on a Google/CDN LB) is often a DV cert
    # with NO organisation, so the strongest anchor — the OV subject-O — is only visible on the
    # estate's OWN appliances. skon.de: the WatchGuard Firebox at 213.61.141.198 presents
    # O="S-KON Sales Kontor Hamburg GmbH"; harvesting it here and re-pivoting on
    # ssl.cert.subject.o: is what finds the owned Colt-netblock hosts the seed cert never revealed.
    # ---- CERT-NAME HARVEST: the highest-yield identity source we were not using -------------
    # A certificate is the one place the operator DECLARES which names a host serves, so it finds
    # what CT and the DNS probe cannot. rightmart.de proved it: the mail archive lives on
    # 'email-archiv-rightmart.de' — a SEPARATE REGISTRABLE DOMAIN, so CT enumeration of
    # '%.rightmart.de' could never return it, and the subdomain probe never guessed it. Its cert
    # (self-signed, EXPIRED, mailcow, IMAPS/993) named it outright. Same class as the
    # bibeltv.de -> bibel.tv sibling. Ownership still goes through _owns_apex, so a shared-hosting
    # neighbour's cert can never drag its own domain into scope.
    _seed_apex0 = _apex(ident["domains"][0]) if ident.get("domains") else None
    _btoks0 = set(ident.get("brand_tokens") or [])
    _cert_new = {}
    for _ip, _ms in hosts.items():
        for _m in _ms:
            for _nm in _cert_names(_m):
                _ap = _apex(_nm)
                if _ap in (ident.get("exclude_apexes") or []):
                    continue
                _own, _why = _owns_apex(_ap, _btoks0, _seed_apex0, (ident.get("group_domains") or []),
                                          bool(ident.get("group_pages")))
                if not _own:
                    continue
                # THE abakusconsulting.co.uk FALSE POSITIVE (2026-08). The comment above claims "a
                # shared-hosting neighbour's cert can never drag its own domain into scope". That
                # holds only while the brand token is DISTINCTIVE. "abakus" is the German word for
                # abacus, so it matched "abakusconsulting" -- a different company, in the UK, whose
                # certificate merely happened to sit on the same IONOS elastic-SSL VIP. It was then
                # scoped as a first-class seed and produced the deck's only remaining false finding.
                #
                # A certificate is STRONG evidence of common operation when it names the customer
                # TOO -- that is exactly how bibeltv.de found bibel.tv, and that recall must not be
                # lost. It is WEAK evidence when it names only the other party and the host is
                # shared infrastructure: then all we have observed is that two customers of the same
                # hoster have similar-looking names.
                if _ap != _seed_apex0 and _why.startswith("brand token"):
                    _shared_h = False
                    for _mm in _ms:
                        _o = (_mm.get("org") or "") + " " + (_mm.get("isp") or "")
                        if _is(_o, CDNS) or _looks_like_provider(_o):
                            _shared_h = True
                            break
                    _names_here = {n.lower().lstrip("*.") for n in _cert_names(_m)}
                    _also_ours = any(x == _o2 or x.endswith("." + _o2)
                                     for x in _names_here
                                     for _o2 in ({_seed_apex0} | {_apex(d) for d in ident["domains"]})
                                     if _o2)
                    if _shared_h and not _also_ours:
                        ident.setdefault("cert_names_refused", [])
                        if _nm not in ident["cert_names_refused"]:
                            ident["cert_names_refused"].append(_nm)
                            print("[auto] cert-name REFUSED: %s (on shared infrastructure %s, and "
                                  "the certificate does not also name the customer -- a brand-token "
                                  "substring is not ownership)" % (_nm, _ip), file=sys.stderr)
                        continue
                if _nm not in ident["domains"]:
                    _cert_new.setdefault(_nm, set()).add(_ip)
                if _ip not in ident["pinned"]:
                    ident["pinned"].append(_ip)      # the cert proves this host is the target's
    for _nm, _ips in sorted(_cert_new.items()):
        ident["domains"].append(_nm)
        print("[auto] cert-name discovery: %s (from the certificate on %s) — OWNED, added to scope"
              % (_nm, ", ".join(sorted(_ips)[:3])), file=sys.stderr)
    ident["cert_names_found"] = sorted(_cert_new)
    # A brand token that is also a SURNAME over-matches: angermann.de (Angermann Group) pulled in
    # ra-angermann.de and renner-angermann.de — plausibly different legal entities that merely share
    # a family name. Cert evidence justifies SCOPING them, but a separate registrable domain must be
    # CONFIRMED by the operator, not silently trusted. Surfaced by clarify.py.
    ident["cert_sibling_apexes"] = sorted({_apex(n) for n in _cert_new
                                           if _seed_apex0 and _apex(n) != _seed_apex0})
    if ident["cert_sibling_apexes"]:
        print("[auto] cert discovery crossed into %d separate domain(s): %s — scoped on certificate "
              "evidence, flagged for operator confirmation"
              % (len(ident["cert_sibling_apexes"]), ", ".join(ident["cert_sibling_apexes"])),
              file=sys.stderr)

    seen_o = {}
    seen_org = {}
    for _ms in hosts.values():
        for _m in _ms:
            _o = (((_m.get("ssl") or {}).get("cert") or {}).get("subject") or {}).get("O")
            if _o: seen_o[_o] = seen_o.get(_o, 0) + 1
            # ALSO harvest the whois-org (m.org) — this is the S-KON WatchGuard's only anchor: its
            # cert is self-signed ('Firebox webCA') but its netblock whois-org is the company.
            _wo = _m.get("org")
            if _wo and not _is(_wo, CDNS) and not _is(_wo, CARRIERS):
                seen_org[_wo] = seen_org.get(_wo, 0) + 1
    _btoks = set(ident.get("brand_tokens") or [])

    def _brandish(name):
        sq = re.sub(r"[^a-z0-9]", "", str(name).lower())
        return any(t in sq for t in _btoks) and not _is(name, CDNS) and not _is(name, PUBLIC_CAS)

    # ssl.cert.subject.o: pivot — brand-token cert Organisations seen on the estate.
    for _o in [o for o, n in sorted(seen_o.items(), key=lambda x: -x[1])][:6]:
        if not _brandish(_o) or _o in ident.get("cert_orgs", []):
            continue
        ident.setdefault("cert_orgs", []).append(_o)
        print(f"[auto] cert subject-O pivot on {_o!r}", file=sys.stderr)
        try:
            k = 0; _add, _aasn = [], []
            for _m in api.search_cursor('ssl.cert.subject.o:"%s"' % _o):
                ip2 = _m.get("ip_str")
                if ip2 and ip2 not in hosts:
                    hosts.setdefault(ip2, []).append(_m)      # a target-O cert IS proof of ownership
                    if _m.get("asn"): _aasn.append(_m["asn"])
                    _add.append(ip2)
                k += 1
                if k >= limit_per_query: break
            kept = _accept_pivot("cert-O %r" % _o, _add, _aasn)
            pivot_added += kept
            print(f"[auto]   ssl.cert.subject.o: +{kept} hosts", file=sys.stderr)
        except shodan.APIError:
            pass

    # org: pivot — brand-token whois ORGS, LEGAL SUFFIX STRIPPED. This is what finds the S-KON
    # WatchGuard Firebox + SNMP/appliance netblocks: org:"S-KON Sales Kontor Hamburg" matches the
    # stored field "S-KON SALES KONTOR HAMBURG AG" that the full 'GmbH' string missed.
    _org_pivots = {_org_core(o) for o in seen_org if _brandish(o)}
    _org_pivots |= {_org_core(o) for o in ident.get("cert_orgs", []) if _brandish(o)}
    # SHODAN'S org: IS CASE-INSENSITIVE, so two spellings of one name are ONE query run twice.
    # bottomline.com produced org:"BOTTOMLINE TECHNOLOGIES" (+202) and org:"Bottomline Technologies"
    # (+117) as separate pivots — the same search, paged differently, charged twice against the
    # budget and counted twice toward the scope-blowout total. Fold case-equal cores to one pivot,
    # keeping the spelling that reads best on the log line.
    _by_fold = {}
    for _o in _org_pivots:
        _k = " ".join(_o.casefold().split())
        if _k not in _by_fold or _o.istitle():
            _by_fold[_k] = _o
    if len(_by_fold) < len(_org_pivots):
        print("[auto] org pivots: %d spelling(s) folded to %d distinct query(ies) — org: is "
              "case-insensitive, so the extras were the same search"
              % (len(_org_pivots), len(_by_fold)), file=sys.stderr)
    _org_pivots = set(_by_fold.values())
    for _oc in sorted(_org_pivots, key=len, reverse=True)[:4]:
        if len(_oc) < 5:
            continue
        print(f"[auto] whois-org pivot on org:\"{_oc}\" (legal suffix stripped)", file=sys.stderr)
        try:
            k = 0; _add, _aasn = [], []
            for _m in api.search_cursor('org:"%s"' % _oc):
                ip2 = _m.get("ip_str")
                if ip2 and ip2 not in hosts:
                    # org: is broad — keep only if the host's own org/whois carries the phrase, or it
                    # otherwise corroborates (own ASN / brand domain). Guards against a shared parent.
                    _ho = ((_m.get("org") or "") + " " + (_m.get("isp") or "")).lower()
                    if _oc.lower() not in _ho and not _corroborates(_m, ident, own_asns):
                        continue
                    hosts.setdefault(ip2, []).append(_m)
                    if _m.get("asn"): _aasn.append(_m["asn"])
                    _add.append(ip2)
                k += 1
                if k >= limit_per_query: break
            kept = _accept_pivot('org:"%s"' % _oc, _add, _aasn)
            pivot_added += kept
            print(f"[auto]   org:\"{_oc}\": +{kept} hosts", file=sys.stderr)
        except shodan.APIError:
            pass

    # SAFETY NET: findings must not be computed over an estate the identity queries never proved.
    # If this ever trips again, the deck is wrong — say so loudly instead of shipping it silently.
    if len(hosts) > max(25, 4 * max(1, len(identity_ips))):
        print("[ERROR] scope blow-out: identity queries proved %d hosts but the host set is %d. "
              "A pivot has over-matched — treat this assessment as UNSAFE."
              % (len(identity_ips), len(hosts)), file=sys.stderr)
        ident["scope_blowout"] = {"identity_hosts": len(identity_ips), "total_hosts": len(hosts),
                                  "pivot_added": pivot_added,
                                  "pivots_rolled_back": len(ident.get("pivots_rolled_back") or [])}
    # ---- CO-TENANT GUARD: a netblock is not a customer (angermann.de, 2026-07) ------------------
    # 217.110.51.0/24 is a SHARED Colt /24. Angermann holds .2 and .7; the rest of the block belongs
    # to Nordrheinische Aerzteversorgung (a doctors' pension fund), FACT, NAGASE, Regus and Mane —
    # complete with their SNMP, MikroTik Winbox and Exchange exposure. Sweeping the prefix as "the
    # customer's" would put another company's attack surface in an Angermann deck, which is the
    # worst failure this engine can produce. Shodan carries a PER-IP whois org, so the discriminator
    # already exists in the data: keep a host only if its own org corroborates the target, or it
    # carries one of the target's own names, or an identity query found it in the first place.
    _own_aps = set()
    for _d in (list(ident.get("domains") or []) + list(ident.get("group_domains") or [])):
        _a = _apex(_d)
        if _a: _own_aps.add(_a)
    if _seed_apex0: _own_aps.add(_seed_apex0)

    # ---- SHARED-VIP ATTRIBUTION GATE (proved on abakus-tk.de, 2026-08) --------------------------
    # abakus-tk.de resolves to an IONOS elastic-SSL VIP. Both of its addresses are legitimately
    # PINNED -- their own DNS points there -- and pinned hosts deliberately bypass the hoster drop.
    # But the operator pulled Shodan's actual records for those two IPs, and this is what they say:
    #
    #   217.160.0.136          :80   http.host = mlslight.com
    #   217.160.0.136          :443  hostnames = bboca.de
    #   2001:8d8:100f:f000::269 :80  http.host = cpi-projects.co.uk
    #   2001:8d8:100f:f000::269 :443 http.host = www.stefan-ried.de, cert CN *.stefan-ried.de
    #
    # NOT ONE record names abakus-tk.de. The deck's "Standard services exposed - nginx" finding was
    # literally a stranger's private blog. The cause is mechanical: the VIP requires SNI (without
    # it the server aborts the handshake with alert 80 - verified by hand), and Shodan scans by IP
    # with whatever hostname it happens to know. The customer's vhost is therefore invisible to it.
    #
    # RULE: pinning proves the ADDRESS is theirs. It does not make every OBSERVATION on it theirs.
    # On provider/multi-tenant infrastructure a record may only become a finding if it identifies
    # itself with one of the customer's names.
    #
    # THE FAIL-OPEN, AND THE TWO CASES WHERE IT IS WRONG (aminagroup.com, 2026-08).
    # A record carrying NO names at all cannot be shown to be a co-tenant's either, so it USED to be
    # kept unconditionally. That single line shipped a Swiss crypto bank a CRITICAL finding on
    # 83.111.84.114 -- netname PERI-EMIRNET, "Peri llc", Dubai, Etisalat AS5384: a German formwork
    # manufacturer's UAE subsidiary. It also produced the HIGH (smartTrade Technologies' own trading
    # cloud) and the LOW (a WHM port on WPEngine shared hosting). All three are nameless records:
    # a FortiGate on :541 has no HTTP host, no certificate names and -- verified -- no PTR at all,
    # so `_record_names` returns the empty set and the gate waved it through.
    # It is now refused in two situations, each an independent barrier:
    #
    #   1. THE TARGET OWNS NO ADDRESS SPACE. This gate's own reasoning, four lines up, is that when
    #      a customer owns no ASN and no prefix "identity -- a name or a certificate -- is the ONLY
    #      evidence available". A record with no names carries no identity, so on such a target it is
    #      not evidence of anything. Keeping it contradicted the rule the same block had just stated.
    #   2. THE ADDRESS HAS ALREADY BEEN PROVEN MULTI-TENANT. On 141.193.213.21 the gate dropped 323
    #      records for naming strangers (nwpewaf.com and friends) and then kept a nameless one on the
    #      very same IP. If somebody else's names are on this address, a nameless record here is far
    #      more likely theirs than the customer's -- and "the gate is applied unevenly" is exactly
    #      what the false-positive review said.
    #
    # THE FAIL-OPEN SURVIVES WHERE IT WAS EARNED: a customer that DOES own address space, on an
    # address where nobody else has been seen. That is the S-KON WatchGuard -- a self-signed Firebox
    # on S-KON's own Colt /29 -- whose only anchor is a certificate carrying no dotted name.
    _attr_dropped = []
    _no_space0 = not (ident.get("asns") or ident.get("nets"))
    # PASS 1: which addresses carry somebody else's names? Computed BEFORE any decision, because a
    # per-record loop cannot know what the rest of the address looks like -- and a guard whose
    # baseline is computed while it is still consuming untrusted input is not a guard.
    _stranger_on = {}
    for ip in list(hosts.keys()):
        for m in hosts[ip]:
            _nm0 = _record_names(m)
            if _nm0 and not _names_the_target(m, _own_aps):
                _stranger_on.setdefault(ip, set()).update(_nm0)
    for ip in list(hosts.keys()):
        _kept = []
        for m in hosts[ip]:
            _org_m = (m.get("org") or "") + " " + (m.get("isp") or "")
            # THE TAMM FALSE POSITIVE (adpolice.gov.ae, 2026-08). 5.194.255.186 was reported as Abu
            # Dhabi Police's "core portal". It presents cert CN `tamm.abudhabi`, O `Department of
            # Government Enablement` — the shared TAMM government platform, on which the police are
            # one tenant of roughly 160. The gate did not fire because its holder is a government
            # digital authority, which is multi-tenant but looks nothing like a hoster: no "hosting"
            # in the name, and 16 announced prefixes, under the >20 provider threshold.
            # The general rule is not about what the holder looks like. It is about whether the
            # customer has any address space of its own: if they own NO ASN and NO prefixes, then
            # nothing can be attributed to them by IP, and identity — a name or a certificate — is
            # the ONLY evidence available. That is exactly what the S-KON playbook has always said.
            _shared = _no_space0 or _is(_org_m, CDNS) or _looks_like_provider(_org_m)
            if not _shared:
                _kept.append(m); continue            # not provider space -> the IP itself attributes
            _nm = _record_names(m)
            if not _nm:
                # No identity on the record. Keep it ONLY where the fail-open was earned: the
                # customer owns address space, and nobody else has been seen on this address.
                if _no_space0:
                    _attr_dropped.append((ip, m.get("port"),
                                          "<no name; target owns no address space>"))
                    continue
                if ip in _stranger_on:
                    _attr_dropped.append((ip, m.get("port"),
                                          "<no name; %s also on this address>"
                                          % sorted(_stranger_on[ip])[0][:26]))
                    continue
                _kept.append(m); continue            # no names at all -> cannot disprove ownership
            if _names_the_target(m, _own_aps):
                _kept.append(m); continue            # the record names the customer
            # Log the most INFORMATIVE name, not the alphabetically first one: the reverse-DNS of
            # a shared VIP ("217-160-0-136.elastic-ssl.ui-r.com") sorts ahead of the co-tenant's
            # real domain and tells the reader nothing about whose record this is.
            _hh = ((m.get("http") or {}).get("host") or "").lower().strip(".")
            _pick = _hh if (_hh and "." in _hh and not _hh.replace(".", "").isdigit()) else ""
            if not _pick:
                _nonptr = [n for n in sorted(_nm)
                           if not re.match(r"^[\d\-]+\.", n) and not _is(n, CDNS)]
                _pick = (_nonptr or sorted(_nm))[0]
            _attr_dropped.append((ip, m.get("port"), _pick[:40]))
        if _kept:
            hosts[ip] = _kept
        else:
            del hosts[ip]
    if _attr_dropped:
        # COUNT THEM. The methodology slide printed "0 DROPPED FALSE-POS" on a run where this gate
        # removed 339 records -- the single heaviest piece of false-positive work in the assessment.
        # `dropped` only ever counted honeypot and CDN drops, so the deck advertised that the FP
        # machinery had done nothing, on exactly the run where it did the most. A methodology slide
        # that understates its own filtering is a credibility problem in front of a bank.
        dropped += len(_attr_dropped)
        ident["records_unattributable"] = [{"ip": i, "port": p, "name": n}
                                           for i, p, n in _attr_dropped][:40]
        print("[auto] attribution gate: dropped %d record(s) on shared/provider infrastructure that "
              "name someone else (e.g. %s) - pinning proves the address, not the observation"
              % (len(_attr_dropped),
                 ", ".join("%s:%s=%s" % t for t in _attr_dropped[:3])), file=sys.stderr)
    # NOTE: do NOT skip on identity_ips here. It is assigned as set(hosts) AFTER every filter has
    # run, so on a net/prefix sweep it contains the co-tenants too and the guard would never fire.
    # Only a PINNED host (resolved from the target's own DNS) is ours by definition.
    _pinned_ips = set(ident.get("pinned") or [])
    _cotenant, _dropped_backup = [], {}
    for ip in list(hosts.keys()):
        if ip in _pinned_ips:
            continue                                    # the target's own DNS points here
        _orgs_h, _names = set(), set()
        for m in hosts[ip]:
            if m.get("org"): _orgs_h.add(str(m["org"]))
            for h in (m.get("hostnames") or []): _names.add(str(h).lower())
            cn = (((m.get("ssl") or {}).get("cert") or {}).get("subject") or {}).get("CN")
            if cn: _names.add(str(cn).lower().lstrip("*."))
        if not _orgs_h:
            continue                                    # no org recorded -> no evidence -> keep
        if any(_org_is_the_target(o, _seed_apex0) for o in _orgs_h):
            continue                                    # the host's OWN whois names the customer
        if any(nm == ap or nm.endswith("." + ap) for nm in _names for ap in _own_aps):
            continue                                    # carries one of the customer's own names
        _cotenant.append((ip, sorted(_orgs_h)[0][:38]))
        _dropped_backup[ip] = hosts[ip]
        del hosts[ip]
    # GUARDRAIL, same doctrine as audit_fp: an automatic filter that can EMPTY a deck is worse than
    # no filter. If the org data would delete everything (or almost everything) the org data is what
    # is wrong, not the estate - keep it all and say so loudly.
    #
    # THE ABAKUS-TK.DE CORRECTION (2026-08). The valve fired on a run where the guard was RIGHT:
    # it flagged 182 of 192 hosts (95%) as co-tenants -- correctly, they were Microsoft, Cloudflare,
    # Hetzner and OVH tenants -- then refused and kept every one of them.
    # The 75% threshold encodes an assumption that only holds when the target HAS its own address
    # space: there, a mass drop means the whois data is wrong. On a target with NO ASN and NO
    # prefixes, whose whole estate is shared multi-tenant hosting, co-tenants dominating is the
    # EXPECTED result, not a malfunction -- so applying the threshold there guarantees the wrong
    # answer on the most common shape of German SMB prospect we see (S-KON, rightmart, abakus).
    # The invariant worth keeping is the narrow one: never drop into an EMPTY deck.
    #
    # 2026-08, SECOND CORRECTION. "Never drop into an EMPTY deck" was still a refusal trigger, and
    # on the next abakus-tk.de run it fired: the attribution gate had already removed every record
    # on the IONOS VIP (that day Shodan's records for it named pro-tec.org and parcarmeen.com), so
    # the 25 hosts left were ALL strangers. Dropping them would have emptied the estate, the valve
    # refused, and 25 other companies' hosts became SIX findings and a EUR 6-16M price tag on a
    # 20-person reseller.
    # An empty estate is an HONEST outcome, and on a target whose whole presence is shared hosting
    # it is frequently the CORRECT one: "nothing of yours is externally observable" is a true,
    # defensible and even saleable result. A deck full of strangers is neither.
    # So emptiness is no longer a reason to keep anything. The only surviving refusal is the
    # lotto24/angermann one: a mass drop on a target that DOES own address space means the whois
    # data is the suspect, not the estate. Pinned hosts and hosts carrying the customer's own names
    # are exempt before we ever get here, so for this to empty the estate every remaining host must
    # be unpinned, unnamed and whois-owned by somebody else -- which is exactly "they are strangers".
    _owns_space = bool(ident.get("asns")) or bool(ident.get("nets"))
    _mass_drop = len(_cotenant) > 0.75 * (len(hosts) + len(_cotenant))
    if _cotenant and _mass_drop and _owns_space:
        # Snapshot the denominator BEFORE restoring. The old message computed it after the restore
        # loop, so the co-tenants were counted twice and lotto24.de reported "dropped 379 of 783"
        # against a real estate of 404. A guard that misreports its own arithmetic sends the next
        # investigation down the wrong path — which is exactly what it did.
        _total_before = len(hosts) + len(_cotenant)
        for ip, _o in _cotenant:
            hosts.setdefault(ip, _dropped_backup.get(ip, []))
        print("[auto] co-tenant guard REFUSED: it would have dropped %d of %d hosts (%.0f%%) - "
              "keeping everything (the whois data is the suspect, not the estate)"
              % (len(_cotenant), _total_before, 100.0 * len(_cotenant) / max(1, _total_before)),
              file=sys.stderr)
        ident["cotenants_refused"] = [{"ip": i, "org": o} for i, o in _cotenant][:40]
        _cotenant = []
    if _cotenant:
        ident["cotenants_dropped"] = [{"ip": i, "org": o} for i, o in _cotenant][:40]
        print("[auto] co-tenant guard: dropped %d host(s) sharing a netblock but whois-owned by "
              "someone else (e.g. %s)" % (len(_cotenant),
              ", ".join("%s=%s" % (i, o) for i, o in _cotenant[:3])), file=sys.stderr)

    # REFINE exclusions: drop any host the operator said is not theirs (by IP, or by any hostname/
    # rDNS/cert-CN under an excluded apex). Applied AFTER all pivots so it prunes whatever slipped in.
    _ex_ips = set(ident.get("exclude_ips") or [])
    _ex_aps = tuple(ident.get("exclude_apexes") or [])
    if _ex_ips or _ex_aps:
        _before = len(hosts)
        for ip in list(hosts.keys()):
            if ip in _ex_ips:
                del hosts[ip]; continue
            if _ex_aps:
                names = set()
                for m in hosts[ip]:
                    for h in (m.get("hostnames") or []): names.add(str(h).lower())
                    for h in (m.get("domains") or []): names.add(str(h).lower())
                    cn = (((m.get("ssl") or {}).get("cert") or {}).get("subject") or {}).get("CN")
                    if cn: names.add(str(cn).lower())
                if any(nm == ap or nm.endswith("." + ap) for nm in names for ap in _ex_aps):
                    del hosts[ip]
        if len(hosts) != _before:
            print("[refine] excluded %d host(s) at operator request" % (_before - len(hosts)),
                  file=sys.stderr)

    buckets = {}
    for ip, ms in hosts.items():
        for m in ms:
            records += 1
            sev, ft = classify(m); b = buckets.setdefault((sev, ft), {"evidence": [], "ips": set(), "prods": {}, "cves": []})
            b["ips"].add(ip)
            svc = m.get("product") or DB_PORTS.get(m.get("port")) or ICS_PORTSET.get(m.get("port")) or REMOTE_HI.get(m.get("port")) or ""
            pf = (svc + (" " + str(m.get("version")) if m.get("version") else "")).strip()
            if pf: b["prods"][pf] = b["prods"].get(pf, 0) + 1
            vs = m.get("vulns") or {}
            for c in vs:
                if c not in b["cves"]: b["cves"].append(c)
            ev = f"{ip}:{m.get('port')}  {pf}".strip()
            if vs: ev += "  vulns:" + ",".join(list(vs)[:3])
            if len(b["evidence"]) < 8: b["evidence"].append(ev)
    findings = []; counts = {s: 0 for s in SEV_ORDER}; idc = {s: 0 for s in SEV_ORDER}
    for sev in SEV_ORDER:
        for (s, ft), b in sorted(buckets.items()):
            if s != sev: continue
            idc[sev] += 1; counts[sev] += 1
            title, why, rem, refs = TEMPLATES.get(ft, (ft.replace("_"," ").title(), ["Exposure"], ["Review"], []))
            extra = ""
            if b.get("cves"):
                extra = ": " + b["cves"][0] + (f" +{len(b['cves'])-1} more CVEs" if len(b["cves"]) > 1 else "")
            elif b.get("prods"):
                extra = " — " + max(b["prods"], key=b["prods"].get)
            nhost = len(b["ips"])
            findings.append({"sev": sev, "id": sev[0] + str(idc[sev]),
                "title": f"{title}{extra} ({nhost} host{'s' if nhost > 1 else ''})",
                "what": [f"{len(b['ips'])} host(s) match this exposure pattern."],
                "evidence": b["evidence"], "why": why, "rem": rem, "refs": refs})
    # ---- DNS-DERIVED FINDINGS (abakus-tk.de, 2026-08) -------------------------------------------
    # On a target whose entire estate is shared hosting, Shodan can produce NOTHING attributable --
    # every record on the VIP belongs to a co-tenant, and the customer's own vhost is invisible
    # because the front end requires SNI. The zone, however, is unambiguously theirs. These two
    # checks are pure DNS, cost nothing, and on abakus-tk.de both fire: no CAA at all, and two
    # names (intranet., dev.) resolving to addresses where a router answers host-unreachable.
    _dns_findings = []
    _seedd = _apex(ident["domains"][0]) if ident.get("domains") else None
    # Fetched ONCE and shared by the CAA authorisation check and the certificate intelligence.
    # Paging CertSpotter twice would double the requests against a rate-limited free tier to learn
    # exactly the same thing.
    _ct_issuances = []
    if _seedd:
        try:
            _ct_issuances = _certspotter_issuances(_seedd)
            print("[auto] CT: %d unexpired issuance(s) for %s" % (len(_ct_issuances), _seedd),
                  file=sys.stderr)
        except Exception as _e:
            print("[warn] CT issuance fetch failed for %s: %s" % (_seedd, _e), file=sys.stderr)
    if _seedd:
        _c = _caa(_seedd)
        if _c is not None and not _c:          # queried OK and genuinely empty
            _t, _w, _r, _f = TEMPLATES["no_caa"]
            _dns_findings.append({"sev": "MEDIUM", "ft": "no_caa", "title": _t,
                                  "what": ["No CAA record is published for %s." % _seedd],
                                  "evidence": ["%s  CAA -> no records (NXRRSET)" % _seedd],
                                  "why": _w, "rem": _r, "refs": _f})
        elif _c is None:
            print("[auto] CAA lookup failed for %s - reported as unknown, no finding claimed"
                  % _seedd, file=sys.stderr)
        elif _c:
            # CAA IS PUBLISHED -> the far more interesting question becomes answerable: is every
            # LIVE certificate for this name issued by an authority the policy actually allows?
            # CT logging is mandatory for publicly-trusted certificates, so this sees issuance the
            # customer never told anyone about -- including on hosts Shodan can never observe
            # because the front end requires SNI (the abakus-tk.de lesson). Zero packets to them.
            try:
                _uz = _unauthorised_issuances(_seedd, _ct_issuances, _c)
            except Exception as _e:
                _uz = []
                print("[warn] CT issuance check failed for %s: %s" % (_seedd, _e), file=sys.stderr)
            if _uz and _uz[0].get("policy_conflict"):
                print("[auto] CAA policy conflict on %s: the record authorises %s yet ALL %d live "
                      "certificate(s) are outside it - reported as a policy problem, NOT as mass "
                      "mis-issuance" % (_seedd, _uz[0]["authorised"] or "nobody", _uz[0]["count"]),
                      file=sys.stderr)
            elif _uz:
                _t, _w, _r, _f = TEMPLATES["cert_unauthorised"]
                _ev = ["%s  issued by %s  (CAA authorises %s)  valid %s -> %s"
                       % (", ".join(u["names"][:3]), u["issuer"],
                          ", ".join(_caa_issuers(_c)[0]) or "nobody",
                          u["not_before"][:10], u["not_after"][:10]) for u in _uz[:8]]
                _dns_findings.append({
                    "sev": "MEDIUM", "ft": "cert_unauthorised", "title": _t,
                    "what": ["%d live certificate(s) for %s were issued by an authority the "
                             "domain's CAA record does not list." % (len(_uz), _seedd)],
                    "evidence": _ev, "why": _w, "rem": _r, "refs": _f})
                print("[auto] CT: %d live certificate(s) outside the CAA policy of %s"
                      % (len(_uz), _seedd), file=sys.stderr)

    # ---- SELF-HOSTED EXCHANGE, AND NAMES NO CERTIFICATE COVERS (zero packets: DNS + CT) --------
    # BOTH WERE MISSED ON ns03.ru while the operator's own browser was looking at an Outlook Web
    # Access sign-in page on the raw address, over a certificate the browser rejected. Every
    # Exchange detector we had read a scan-engine BANNER, and this estate has no scan-engine
    # record at all -- so the most attacked platform in the enterprise produced nothing.
    if _seedd:
        try:
            _cert_names_all = [n for r in (_ct_issuances or []) for n in (r.get("dns_names") or [])]
            _ex = cert_intel.onprem_exchange(
                ident.get("resolved") or {}, ident.get("domains") or [],
                cert_names=_cert_names_all, is_saas=_is_saas_tenancy,
                mx_hosts=ident.get("mx") or [])
        except Exception as _e:
            _ex = None
            print("[warn] Exchange check failed: %s" % _e, file=sys.stderr)
        if _ex:
            _t, _w, _r, _f = TEMPLATES["exchange_onprem"]
            _dns_findings.append({
                "sev": "CRITICAL", "ft": "exchange_onprem", "title": _t,
                "what": ["Autodiscover resolves to the organisation's own address, not to a hosted "
                         "platform: the mail estate is self-hosted and internet-facing."],
                "evidence": _ex["evidence"] + ["corroborated by: " + "; ".join(_ex["corroboration"])],
                "why": _w, "rem": _r, "refs": _f})
            print("[auto] SELF-HOSTED EXCHANGE exposed (CRITICAL): %s"
                  % ", ".join(_ex["evidence"][:3]), file=sys.stderr)

        try:
            _gap = cert_intel.uncovered_names(ident.get("resolved") or {}, _ct_issuances,
                                              ident.get("domains") or [],
                                              is_saas=_is_saas_tenancy)
        except Exception as _e:
            _gap = []
            print("[warn] certificate coverage check failed: %s" % _e, file=sys.stderr)
        if _gap:
            _t, _w, _r, _f = TEMPLATES["cert_name_gap"]
            _dns_findings.append({
                "sev": "MEDIUM", "ft": "cert_name_gap", "title": _t,
                "what": ["%d live hostname(s) are covered by no unexpired certificate."
                         % len(_gap)],
                "evidence": ["%s -> %s  (no certificate covers this name)"
                             % (g["name"], ", ".join(g["addresses"])) for g in _gap[:8]],
                "why": _w, "rem": _r, "refs": _f})
            print("[auto] %d live name(s) covered by NO certificate: %s"
                  % (len(_gap), ", ".join(g["name"] for g in _gap[:5])), file=sys.stderr)

    # ---- OPERATIONAL TECHNOLOGY, NAMED BY THE CUSTOMER (zero packets: DNS + CT) ----------------
    # CRITICAL, not HIGH. A ventilation or building-services controller reachable from the internet
    # threatens PRODUCTION, and the loss scale is different in kind from an office exposure -- the
    # Jaguar Land Rover precedent is in the template. Identified from the customer's own hostnames
    # and certificates, with the confirmation step written into the remediation because a name is
    # strong evidence of function and is not an inventory.
    try:
        _ot = ot_names(ident.get("resolved") or {}, ident.get("domains") or [])
    except Exception as _e:
        _ot = []
        print("[warn] OT name check failed: %s" % _e, file=sys.stderr)
    if _ot:
        _t, _w, _r, _f = TEMPLATES["ot_exposed"]
        _dns_findings.append({
            "sev": "CRITICAL", "ft": "ot_exposed", "title": _t,
            "what": ["%d hostname(s) naming plant or building-services functions resolve publicly."
                     % len(_ot)],
            "evidence": ["%s -> %s  (%s)" % (o["name"], ", ".join(o["addresses"]), o["why"])
                         for o in _ot[:8]],
            "why": _w, "rem": _r, "refs": _f})
        print("[auto] OT/BMS named on the public internet (CRITICAL): %s"
              % ", ".join(o["name"] for o in _ot[:6]), file=sys.stderr)

    # ---- EMAIL AUTHENTICATION (zero packets: DNS only) -----------------------------------------
    # A domain with no DMARC can be forged without a single exposed host, and that forgery is the
    # delivery mechanism for the invoice fraud the C-BIQ deck prices. The engine described servers
    # and said nothing about the asset every customer and supplier sees daily.
    if _seedd:
        try:
            _mail = email_auth.assess(_seedd)
        except Exception as _e:
            _mail = None
            print("[warn] email auth check failed for %s: %s" % (_seedd, _e), file=sys.stderr)
        if _mail:
            ident["email_auth"] = _mail
            _SEV = {"dmarc_missing": ("HIGH", "dmarc_missing"),
                    "dmarc_monitor_only": ("MEDIUM", "dmarc_weak"),
                    "dmarc_partial": ("MEDIUM", "dmarc_weak"),
                    "dmarc_no_reporting": ("LOW", "dmarc_weak"),
                    "spf_missing": ("MEDIUM", "spf_weak"),
                    "spf_permissive": ("HIGH", "spf_weak"),
                    "spf_no_enforcement": ("MEDIUM", "spf_weak"),
                    "spf_duplicate": ("MEDIUM", "spf_weak"),
                    "spf_too_many_lookups": ("MEDIUM", "spf_weak")}
            # One finding per TEMPLATE, not per issue: three SPF defects are one story on the slide.
            _by_tpl = {}
            for _iss in _mail["issues"]:
                _sev, _tpl = _SEV.get(_iss["id"], ("LOW", "spf_weak"))
                _cur = _by_tpl.setdefault(_tpl, {"sev": _sev, "details": []})
                _cur["details"].append(_iss["detail"])
                if _SEV_ORDER.get(_sev, 0) > _SEV_ORDER.get(_cur["sev"], 0):
                    _cur["sev"] = _sev
            for _tpl, _agg in _by_tpl.items():
                _t, _w, _r, _f = TEMPLATES[_tpl]
                _dns_findings.append({
                    "sev": _agg["sev"], "ft": _tpl, "title": _t,
                    "what": ["%s: %s" % (_seedd, _agg["details"][0])],
                    "evidence": ["%s  %s" % (_seedd, d) for d in _agg["details"][:6]],
                    "why": _w, "rem": _r, "refs": _f})
            if _mail.get("context"):
                print("[auto] email auth %s: %s" % (_seedd, " | ".join(_mail["context"][:3])),
                      file=sys.stderr)

    # ---- CERTIFICATE INTELLIGENCE (zero packets: Certificate Transparency) ----------------------
    # CT cannot be blocked and records INTENT rather than reachability, so it sees hosts a scanner
    # never will -- the ns03.ru estate returned nothing to Shodan across twelve query families.
    if _seedd and _ct_issuances:
        _live = set(ident.get("resolved") or {})
        try:
            _rev = cert_intel.revoked_live(_ct_issuances, _live)
            _exp = cert_intel.expiring(_ct_issuances, _live)
            _shared = cert_intel.shared_blast(_ct_issuances, _live)
            ident["cert_profile"] = cert_intel.ca_profile(_ct_issuances)
            ident["cert_internal_names"] = cert_intel.internal_names(_ct_issuances, ident.get("domains") or [])
        except Exception as _e:
            _rev = _exp = _shared = []
            print("[warn] certificate intelligence failed: %s" % _e, file=sys.stderr)
        if _rev:
            _t, _w, _r, _f = TEMPLATES["cert_revoked_live"]
            _dns_findings.append({"sev": "HIGH", "ft": "cert_revoked_live", "title": _t,
                "what": ["%d revoked certificate(s) cover hostnames that still resolve." % len(_rev)],
                "evidence": ["%s  REVOKED by %s  (was valid to %s)"
                             % (", ".join(x["names"][:3]), x["issuer"], x["not_after"][:10])
                             for x in _rev[:6]],
                "why": _w, "rem": _r, "refs": _f})
        if _exp:
            _t, _w, _r, _f = TEMPLATES["cert_expiring"]
            _dns_findings.append({"sev": "MEDIUM", "ft": "cert_expiring", "title": _t,
                "what": ["%d live hostname(s) have a certificate expiring within 21 days." % len(_exp)],
                "evidence": ["%s  expires %s (%d days)  issuer %s"
                             % (x["name"], x["not_after"][:10], x["days"], x["issuer"])
                             for x in _exp[:8]],
                "why": _w, "rem": _r, "refs": _f})
        if _shared:
            _t, _w, _r, _f = TEMPLATES["cert_shared_key"]
            _dns_findings.append({"sev": "LOW", "ft": "cert_shared_key", "title": _t,
                "what": ["One certificate and private key serve %d distinct services."
                         % _shared[0]["count"]],
                "evidence": ["%d names on one key: %s  (issuer %s)"
                             % (x["count"], ", ".join(x["names"][:6]), x["issuer"])
                             for x in _shared[:3]],
                "why": _w, "rem": _r, "refs": _f})

    # A name that resolves but has NO record anywhere in the sweep is a CANDIDATE for a retired
    # host whose DNS was never cleaned up. It is deliberately not asserted: Shodan not holding a
    # record is not proof a host is gone (absence of evidence is never a finding), so the wording
    # says "possible" and clarify.py puts it to the operator. Confirming it in a refine run is what
    # turns it into a real finding.
    _no_service = []
    for _fq, _ips in (ident.get("resolved") or {}).items():
        _v4 = [i for i in _ips if ":" not in str(i)]
        if not _v4:
            continue
        if any(i in hosts for i in _v4):
            continue                            # something IS observable there
        if _is_saas_tenancy(_fq):
            continue                            # a SaaS tenancy is not their host to begin with
        _no_service.append((_fq, _v4[0]))
    if _no_service:
        # DEMOTED TO A QUESTION (adpolice.gov.ae, 2026-08). I built this as a MEDIUM finding on the
        # strength of abakus-tk.de, where nmap later proved the addresses genuinely dead. On Abu
        # Dhabi Police the same logic flagged `mail.`, `autodiscover.` and `media.` — all perfectly
        # alive. Their MX hosts are absent from every Shodan export too, because Shodan indexes what
        # it has scanned and mail infrastructure frequently is not.
        # "Not in Shodan" is ABSENCE OF EVIDENCE, and the standing rule in this repo is that absence
        # of evidence is never a finding. My own detector broke it. It is now surfaced ONLY as a
        # clarification question; the operator's answer is what turns it into a finding on a refine
        # run, which is the same contract every other candidate here follows.
        ident["resolved_no_service"] = [{"name": n, "ip": i} for n, i in sorted(_no_service)][:20]
        print("[auto] %d name(s) resolve with no observable service - put to the operator as a "
              "question, NOT raised as a finding (absence of evidence is never a finding): %s"
              % (len(_no_service), ", ".join(n for n, _ in sorted(_no_service)[:5])),
              file=sys.stderr)

    for _df in _dns_findings:
        _sev = _df["sev"]
        idc[_sev] = idc.get(_sev, 0) + 1
        counts[_sev] = counts.get(_sev, 0) + 1
        _df["id"] = _sev[0] + str(idc[_sev])
        findings.append(_df)
    if _dns_findings:
        findings.sort(key=lambda f: SEV_ORDER.index(f["sev"]) if f["sev"] in SEV_ORDER else 9)
        print("[auto] DNS hygiene: %d finding(s) from the zone itself (%s)"
              % (len(_dns_findings), ", ".join(f["ft"] for f in _dns_findings)), file=sys.stderr)

    # A target can legitimately end with NOTHING externally observable — a small company whose whole
    # presence is shared hosting and SaaS. Say so explicitly rather than letting a silent zero look
    # like a broken run, and record it so the decks and the LLM prose can state the honest headline
    # ("no attributable external exposure") instead of reaching for filler.
    if not hosts and (ident.get("pinned") or ident.get("domains")):
        ident["no_attributable_estate"] = True
        print("[auto] NO ATTRIBUTABLE ESTATE: every observed record belonged to a co-tenant or a "
              "provider. The customer's own addresses are known (%d pinned) but nothing on them "
              "identifies itself as theirs. That is a finding, not a failure."
              % len(ident.get("pinned") or []), file=sys.stderr)

    # ---- REBUILD THE INVENTORY FROM THE FINAL ESTATE (defect D8/A11, closed 2026-08) ------------
    # `inv`, `asns` and `countries` were accumulated DURING the query loop and never re-derived, so
    # they still counted every record the attribution gate, the co-tenant guard and the rollbacks
    # had since removed. The abakus-tk.de deck showed the result on two adjacent slides:
    # "1 UNIQUE IPS · 47 ASNS · 15 COUNTRIES" against an asset inventory of "144 HOSTS · 12 ASNs".
    # One host cannot span 47 autonomous systems. A reader who compares two slides stops trusting
    # the whole document, which is exactly what the rightmart forensics said about this defect.
    # There is now ONE source for these numbers: the surviving host set.
    inv, asns, countries = {}, set(), set()
    for _ip, _ms in hosts.items():
        for _m in _ms:
            _ma = _m.get("asn")
            _cc = (_m.get("location") or {}).get("country_code")
            if _ma:
                asns.add(_ma)
                _e = inv.setdefault(_ma, {"holder": None, "cc": set(), "ips": set()})
                _e["holder"] = _e["holder"] or (_m.get("org") or _m.get("isp"))
                if _cc:
                    _e["cc"].add(_cc)
                _e["ips"].add(_ip)
            if _cc:
                countries.add(_cc)

    # Every IP the sweep KEPT has already passed recon's ownership gate, so it is owned by
    # definition. The FP auditor uses this set to avoid dropping a legitimately-scanned host that
    # simply wasn't in the DNS-probe pin list (that dropped skon.de's real critical).
    ident["scanned_ips"] = sorted(hosts.keys())
    # The estate's dominant country. The deck builders bind the FRAMEWORK set to it: citing NIS2,
    # GDPR and automotive TISAX at an Emirati police force told that reader the document was not
    # written for them (adpolice.gov.ae, 2026-08 — the third recurrence of this defect).
    #
    # THE HOSTER'S COUNTRY IS NOT THE CUSTOMER'S (aminagroup.com, 2026-08). AMINA is a Swiss bank
    # regulated by FINMA. Its entire estate is other people's infrastructure -- Cloudflare (US/IE),
    # WPEngine (IE/US), ti&m (CH), Microsoft (CH), plus two false positives in GB and AE -- so the
    # "dominant country" of the ASN inventory is a fact about its suppliers and nothing about the
    # customer. This is the same rule already enforced for whois-org, cert-O and netblock holders,
    # one level over: a name that arrives from infrastructure the customer merely RENTS is evidence
    # about the PROVIDER. When they own no address space, the ccTLD is the only country signal that
    # is actually theirs -- and when that is generic (.com/.io) the honest answer is that we do not
    # know, which makes the deck fall back to ISO 27001 / NIST CSF instead of naming a regulator that
    # does not supervise them. Citing the wrong regulator tells the reader the document was not
    # written for them.
    _cc = ""
    _own_space = bool(ident.get("asns") or ident.get("nets"))
    if countries and _own_space:
        _cc = sorted(countries, key=lambda c: -sum(1 for _e in inv.values() if c in _e["cc"]))[0]
    elif ident.get("tld_cc"):
        _cc = str(ident["tld_cc"]).upper()
    elif countries and not _own_space:
        print("[auto] country NOT inferred from the estate: every host is on provider space, so "
              "those countries belong to the suppliers (%s). Frameworks fall back to the "
              "jurisdiction-neutral set." % ",".join(sorted(countries)[:6]), file=sys.stderr)
    return {"target": {"company": company_name(ident), "audience": audience or "Internal — Cybergod LLC · S4Biz Group",
                       "date": datetime.date.today().isoformat(),
                       "country": _cc,
                       "scope": _scope_line(ident)},
            "identity": ident,
            # THE ESTATE THE CUSTOMER'S OWN DNS PROVES, reported ALONGSIDE what a scanner saw.
            # ns03.ru delivered a deck reading "0 UNIQUE IPS · 0 ASNS · 0 COUNTRIES" for a company
            # with 12 live hostnames on 4 addresses. Every one of those addresses is theirs -- their
            # DNS says so -- and every name carries a certificate they requested. What was actually
            # zero is what SHODAN could see, because the estate is SNI-only and filters scanners.
            # Publishing only the scanner's number tells the customer they have no internet presence,
            # which is false, and it is the single most damaging thing this deck can say.
            "summary": {"records": records, "unique_ips": len(hosts), "asns": len(asns) or len(ident["asns"]),
                        "dns_hosts": len(ident.get("resolved") or {}),
                        "dns_addresses": len({ip for v in (ident.get("resolved") or {}).values()
                                              for ip in v}),
                        "scanner_blind": (not hosts) and bool(ident.get("resolved")),
                        "countries": len(countries), "dropped_false_positives": dropped,
                        "behind_cdn": ident["org_is_cdn"],
                        "inventory": sorted(
                            ({"asn": ("AS"+str(a)) if str(a).isdigit() else str(a), "holder": e["holder"] or "—",
                              "country": ",".join(sorted(e["cc"])) or "—", "hosts": len(e["ips"])} for a, e in inv.items()),
                            key=lambda r: -r["hosts"])[:12],
                        "critical": counts["CRITICAL"], "high": counts["HIGH"], "medium": counts["MEDIUM"], "low": counts["LOW"]},
            "findings": findings}

def findings_md(o):
    t = o["target"]; s = o["summary"]
    L = [f"# {t['company']} — Shodan findings", "", f"- Scope: {t['scope']}",
         f"- Records: {s['records']} · IPs: {s['unique_ips']} · dropped FPs: {s['dropped_false_positives']} · behind CDN: {s['behind_cdn']}",
         f"- Severity: CRIT {s['critical']} · HIGH {s['high']} · MED {s['medium']} · LOW {s['low']}", ""]
    for f in o["findings"]:
        L.append(f"## [{f['sev']}] {f['id']} — {f['title']}")
        for e in f["evidence"]: L.append(f"    {e}")
        L.append("")
    return "\n".join(L)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", required=True, help="domain/URL, ASN, CIDR, or company name")
    ap.add_argument("--asn", action="append", default=[], help="add/override ASN (repeatable)")
    ap.add_argument("--net", action="append", default=[], help="add/override CIDR (repeatable)")
    ap.add_argument("--org", action="append", default=[], help="org-name variant (repeatable)")
    ap.add_argument("--brand", action="append", default=[], help="brand / ssl free-text variant (repeatable)")
    ap.add_argument("--domain", action="append", default=[], help="extra domain for cert/hostname (repeatable)")
    ap.add_argument("--favicon", action="append", default=[], help="favicon mmh3 hash (repeatable)")
    ap.add_argument("--issuer", "--internal-ca", dest="issuer", action="append", default=[],
                    help="internal/issuing-CA CN — the killer estate pivot (repeatable)")
    ap.add_argument("--cert-org", dest="cert_org", action="append", default=[], help="cert subject Organisation (repeatable)")
    ap.add_argument("--jarm", action="append", default=[], help="JARM hash to cluster the TLS-stack fleet (repeatable)")
    ap.add_argument("--cpe", action="append", default=[], help="CPE to pin a platform across hosts (repeatable)")
    ap.add_argument("--audience"); ap.add_argument("--outdir", default=".")
    ap.add_argument("--print-filters", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    ident = resolve_identity(a.seed)
    for asn in a.asn:
        asn = "AS" + re.sub(r'(?i)^AS?', '', asn)
        if asn not in ident["asns"]:
            ident["asns"].append(asn)
            ident["asn_holder"] = ident["asn_holder"] or _ripe_holder(asn)
            ident["org_is_cdn"] = False; ident["org_is_carrier"] = _is(ident["asn_holder"],CARRIERS)
            for p in _ripe_prefixes(asn):
                if p not in ident["nets"]: ident["nets"].append(p)
    for n in a.net:
        if n not in ident["nets"]: ident["nets"].append(n)
        ident["org_is_cdn"] = False
    autodiscover(ident, a.org, a.brand, a.domain, a.favicon,
                 issuers=a.issuer, cert_orgs=a.cert_org, jarms=a.jarm, cpes=a.cpe)
    F = build_filters(ident)
    open(os.path.join(a.outdir, "filters.md"), "w").write(filters_md(ident, F))
    print(f"✓ identity: ASNs={ident['asns']} holder={ident.get('asn_holder')!r} cdn={ident['org_is_cdn']} carrier={ident['org_is_carrier']} nets={len(ident['nets'])} domains={ident['domains']}")
    print(f"✓ filters.md ({len(F)} filters)")
    if a.print_filters:
        print(f"RESULT ips=0 cdn={str(ident['org_is_cdn']).lower()} asns={len(ident['asns'])}"); return
    if not os.environ.get("SHODAN_API_KEY"):
        print("SHODAN_API_KEY not set — wrote filters.md only", file=sys.stderr); sys.exit(2)
    o = run(ident, F, a.audience)
    json.dump(o, open(os.path.join(a.outdir, "findings.json"), "w"), indent=2, ensure_ascii=False)
    open(os.path.join(a.outdir, "findings.md"), "w").write(findings_md(o))
    s = o["summary"]
    print(f"✓ findings.json: {len(o['findings'])} findings (CRIT {s['critical']} HIGH {s['high']} MED {s['medium']} LOW {s['low']}) · dropped {s['dropped_false_positives']} FPs")
    print(f"RESULT ips={s['unique_ips']} cdn={str(s['behind_cdn']).lower()} asns={s['asns']}")

if __name__ == "__main__":
    main()
