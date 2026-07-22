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

UA = {"User-Agent": "colt-shodan-recon/1.2"}
# ISPs/telcos: the assigned netblock IS the target's — net: sweep is valid.
CARRIERS = ("deutsche telekom","telekom","vodafone","telefonica","orange","bt ","gtt",
            "level 3","lumen","init7","1&1","ionos","kpn","swisscom","telia","telefonica")
# CDNs / shared front-ends: the IP is NOT the target's — net:/asn: sweeps return the CDN.
CDNS = ("cloudflare","akamai","fastly","cloudfront","amazon","aws","google","incapsula",
        "imperva","sucuri","edgecast","stackpath","bunny","cdn77","limelight","azure","microsoft",
        "hetzner","ovh","mittwald","leaseweb","digitalocean","hosttech","exoscale","contabo",
        "plusserver","strato","1blu","netcup","gcore","oracle")

def _is(name, tup): return bool(name) and any(t in name.lower() for t in tup)

# ------------------------------------------------------------------ identity ---
def _get_json(url, timeout=15):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
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

def _apex(d):
    p = d.split('.'); return ".".join(p[-2:]) if len(p) >= 2 else d

CIDR_RE = re.compile(r'^\d{1,3}(\.\d{1,3}){3}/\d{1,2}$')

def resolve_identity(seed):
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
        ident["domains"] = sorted({dom, apex}); ident["brand"] = apex
        try:
            ip = socket.gethostbyname(dom); ident["seed_ip"] = ip
            asn, prefix, holder = _ip_to_asn(ip)
            if asn:
                ident["asns"].append(asn); ident["asn_holder"] = holder
                ident["org_is_carrier"] = _is(holder,CARRIERS); ident["org_is_cdn"] = _is(holder,CDNS)
                if ident["org_is_cdn"]:
                    pass                                   # CDN: rely on cert/hostname only
                elif ident["org_is_carrier"]:
                    # carrier: announced prefixes are the CARRIER's — use the RDAP assignment (the /27)
                    cidr, netname = _rdap_assignment(ip)
                    if cidr: ident["nets"] = [cidr]; ident["assignment_netname"] = netname
                    elif prefix: ident["nets"] = [prefix]
                else:
                    nets = _ripe_prefixes(asn)
                    if prefix and prefix not in nets: nets = [prefix] + nets
                    ident["nets"] = nets
                ident["org"] = None if (ident["org_is_carrier"] or ident["org_is_cdn"]) else holder
        except Exception as e:
            print(f"[warn] DNS resolve {dom}: {e}", file=sys.stderr)
    else:                                                             # ---- org name
        ident["org"] = s; ident["brand"] = s
    return ident

def company_name(ident):
    return ident.get("brand") or ident.get("org") or ident.get("asn_holder") or ident["seed"]

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


def _certspotter_domains(domain, cap=200):
    """CT via SSLMate's CertSpotter — free, no API key. A SECOND CT source so one outage cannot
    blind the whole assessment (crt.sh returned timeout/404/503 on three consecutive bibeltv runs)."""
    out = set()
    u = ("https://api.certspotter.com/v1/issuances?domain=" + urllib.parse.quote(domain) +
         "&include_subdomains=true&expand=dns_names")
    try:
        for row in (_get_json(u, timeout=25) or [])[:cap]:
            for nm in (row.get("dns_names") or []):
                nm = str(nm).strip().lstrip("*.").lower()
                if nm and "." in nm and " " not in nm:
                    out.add(nm)
    except Exception as e:
        print(f"[warn] certspotter {domain}: {e}", file=sys.stderr)
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


def _owns_apex(apex, brand_tokens, seed_apex):
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
    squash = re.sub(r"[^a-z0-9]", "", apex.split(".")[0])   # the registrable label, separators removed
    for t in brand_tokens:
        if t and len(t) >= 4 and t in squash:
            return True, "brand token %r" % t
    return False, "third-party apex (no brand token)"


# Legal-form suffixes to strip when building an `org:` filter. The S-KON WatchGuard was MISSED
# because cybergod queried org:"S-KON Sales Kontor Hamburg GmbH" while Shodan stores the netblock
# whois-org as "S-KON SALES KONTOR HAMBURG AG" — the wrong suffix meant zero matches. Stripping the
# suffix makes org:"S-KON Sales Kontor Hamburg" match every legal-form variant (GmbH/AG/KG/SE...).
_LEGAL_SUFFIX = re.compile(
    r"\s*(?:\b(?:gmbh(?:\s*&\s*co\.?\s*kg)?|ag|kg|se|mbh|ohg|ug|e\.?v|"
    r"ltd|limited|inc|incorporated|llc|l\.?l\.?c|plc|corp|corporation|co|company|"
    r"bv|nv|sarl|s\.?a\.?r\.?l|srl|sas|s\.?p\.?a|oy|ab|a\/s|as|holding|group)\.?\s*)+$",
    re.I)


def _org_core(o):
    """The distinctive part of an org name, legal suffix stripped, for a robust `org:` phrase.
    'S-KON Sales Kontor Hamburg GmbH' -> 'S-KON Sales Kontor Hamburg' (matches the …AG variant too)."""
    o = re.sub(r"\s+", " ", str(o or "").strip())
    core = _LEGAL_SUFFIX.sub("", o).strip(" .,-")
    return core if len(core) >= 4 else o


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
             "solutions", "systems", "technologies", "technology", "international", "und", "co", "kg"}
    for name in (org_names or []):
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
                 issuers=None, cert_orgs=None, jarms=None, cpes=None):
    """One input in, full anchor block out. Resolves ASNs+prefixes (bgpview + RIPE),
    brand domains (crt.sh CT logs), cert subject O, and favicon — then folds in any manual
    overrides. The internal-CA issuer pivot is auto-harvested live during the sweep (run())."""
    orgs=list(orgs or []); brands=list(brands or []); domains=list(domains or [])
    favicons=list(favicons or []); cert_orgs=list(cert_orgs or [])
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
                if _is(_h, CDNS) or _is(_h, CARRIERS):
                    print("[auto] ASN %s holder %r is shared hosting/carrier — kept as context, "
                          "NOT an ownership anchor" % (a, _h), file=sys.stderr)
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
        if seed_cert_o not in cert_orgs:
            cert_orgs.append(seed_cert_o)            # -> ssl.cert.subject.o: pivot (best filter)
        print("[auto] seed cert subject-O: %r (used as ownership anchor)" % seed_cert_o, file=sys.stderr)
    btoks = _brand_tokens_from(seed_apex, ([seed_cert_o] if seed_cert_o else []) +
                               ([name] if is_name else []) + list(orgs))
    ident["brand_tokens"] = sorted(btoks)
    print("[auto] brand tokens: %s" % (", ".join(sorted(btoks)) or "(none)"), file=sys.stderr)

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
        ok, why = _owns_apex(ap, btoks, seed_apex)
        if not ok:
            unowned.add(ap)
            return
        candidate_apexes.add(ap)
        if d not in domains and d not in ident["domains"]:
            domains.append(d)
            if ap != seed_apex:
                print("[auto] owned domain (%s): %s [%s]" % (source, d, why), file=sys.stderr)

    # 3) CT logs (crt.sh + CertSpotter fallback)
    for d in _crtsh_domains(domain=seed_dom, org=(name if (is_name and not seed_dom) else None)):
        _consider_domain(d, "CT")
    # 3b) sibling domains from the seed certificate SAN list (bibel.tv came from here)
    for san in seed_sans:
        _consider_domain(san, "cert-SAN")
    if seed_apex:
        candidate_apexes.add(seed_apex)

    # 3c) DNS subdomain probe — OWNED apexes only (never a client's apex).
    probed = _probe_subdomains(sorted(candidate_apexes))
    for fqdn, ips in probed.items():
        low = fqdn.lower()
        ap = _apex(low)
        # belt-and-braces: a microsite prefix must never sneak in on a non-brand apex
        first = low.split(".")[0]
        if any(first.startswith(mp) for mp in _MICROSITE_PREFIXES) and \
           not _owns_apex(ap, btoks, seed_apex)[0]:
            continue
        if not _owns_apex(ap, btoks, seed_apex)[0]:
            continue
        if fqdn not in domains and fqdn not in ident["domains"]:
            domains.append(fqdn)
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
    def add(n, name, clause, run=False, note="", cat=None):
        if clause: F.append({"n": n, "name": name, "clause": clause, "run": run, "note": note,
                             "cat": cat or _cat(clause)})
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
        add(4, "TLS cert subject CN", f'ssl.cert.subject.cn:"{d}"', run=True, note="real origin even behind a CDN/hoster")
        add(4, "TLS cert SAN (wildcard)", f'ssl.cert.subject.cn:"*.{d}"', run=True, note="wildcard certs covering every subdomain")
    for b in brands:                     # #4/#5 cert free-text across ANY ASN (cross-ASN estate)
        add(5, "TLS free-text / cert org", f'ssl:"{b}"', run=True, note="wildcard & SAN certs across any ASN")
    for d in _apexes:                    # #5 hostname / rDNS — leading dot = "any host under it"
        add(6, "Hostname / domain", f'hostname:".{d}"', run=True, note="reverse-DNS / HTTP host")
        add(6, "HTTP host header", f'http.host:"{d}"', run=True, note="vhost behind a shared reverse proxy")
    for b in brands:                     # #6 branded HTTP title/body (portals, shadow IT)
        add(14, "HTTP title (branded)", f'http.title:"{b}"', run=True, note="branded portals/login pages on any host")
        add(15, "HTTP body (branded)", f'http.html:"{b}"', run=True, note="branded body content / shadow IT")
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


def classify(m):
    port = m.get("port"); prod = (m.get("product") or ""); vulns = m.get("vulns") or {}
    ssl = m.get("ssl") or {}; tags = m.get("tags") or []
    title = ((m.get("http") or {}).get("title") or "")
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
    versions = ssl.get("versions") or []
    if any(v.lstrip("-") in ("TLSv1","TLSv1.0","SSLv3","SSLv2","TLSv1.1") for v in versions): return "MEDIUM","legacy_tls"
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
 "rdp":        ("Internet-facing RDP", ["#1 ransomware entry vector","Credential brute-force"], ["Colt SASE / ZTNA — retire the exposed RDP; broker access with MFA","Colt Managed Firewall — block 3389 at the edge"], ["MITRE T1133"]),
 "db_exposed": ("Exposed database", ["Direct data-exfiltration path","Often unauthenticated"], ["Colt Managed Firewall — remove the DB from the internet","Colt DPI/NDR — detect exfiltration attempts"], ["MITRE T1190"]),
 "ics":        ("Exposed ICS/OT protocol", ["Safety/availability impact","NIS2 / ISO 27001 driver"], ["Colt Managed Firewall + IT/OT segmentation","Colt SD-WAN secure OT transport; Colt IP Guardian (DDoS)"], ["MITRE ICS","NIS2 Art.21"]),
 "vuln_tagged":("Shodan-tagged vulnerabilities (CVE)", ["Pre-mapped exploit paths; check CISA KEV"], ["Colt WAF — virtual-patch the exposed CVE","Colt Managed Security — KEV/EPSS-prioritised patch orchestration"], ["Shodan vulns","CISA KEV"]),
 "edge_appliance":("Exposed edge-security appliance (firewall / SSL-VPN / UTM)", ["KEV-heavy edge — WatchGuard / Barracuda / Fortinet / Citrix / Ivanti class; the #1 ransomware entry vector. An internet-facing appliance management plane is exploited faster than it can be patched."], ["Colt SASE / ZTNA — retire the internet-facing appliance mgmt plane entirely (no public gateway to exploit)","Colt Managed Firewall — restrict mgmt to an allowlist + enforce MFA","Colt Managed Security — KEV/EPSS-prioritised virtual patching"], ["CISA KEV","MITRE T1133"]),
 "snmp_exposed":("Exposed SNMP management service", ["Internet-reachable SNMP (161/UDP) leaks device model, firmware, interfaces and topology — reconnaissance gold, and weak community strings enable config read/write."], ["Colt Managed Firewall — block 161/162 at the edge; SNMP is a management protocol, never internet-facing","Colt Managed Security — enforce SNMPv3 with auth+priv where monitoring is required"], ["MITRE T1046","BSI IT-Grundschutz"]),
 "vpn_appliance":("Exposed VPN / firewall mgmt", ["Edge-appliance CVEs = top ransomware vector"], ["Colt SASE / ZTNA — replace the legacy VPN","Colt Managed Firewall — restrict mgmt to allowlist + MFA"], ["CISA KEV"]),
 "remote_admin":("Exposed remote-admin (Telnet/VNC/WinRM/SMB)", ["Brute-force / cleartext protocols"], ["Colt SASE / ZTNA — broker admin access","Colt Managed Firewall — block cleartext admin ports"], ["MITRE T1133"]),
 "exposed_panel":("Exposed login / admin / OWA panel", ["Credential attacks; panel-CVE surface"], ["Colt WAF — shield the panel + rate-limit","Colt SASE — identity-broker + geofence"], ["OWASP"]),
 "legacy_tls": ("Legacy / weak TLS (SSLv3/TLS1.0/1.1)", ["MITM / downgrade; PCI/DORA gap"], ["Colt Managed Firewall — enforce TLS>=1.2 policy","Colt WAF — terminate modern TLS"], ["RFC 8996"]),
 "expired_tls":("Expired TLS certificate", ["Trust failure; eases MITM"], ["Colt Managed Security — certificate lifecycle + monitoring"], []),
 "self_signed":("Self-signed certificate", ["No trust anchor"], ["Colt Managed Security — CA-signed certs + automated renewal"], []),
 "verbose_banner":("Verbose service banners", ["Eases attacker recon"], ["Colt WAF / Managed Firewall — suppress product/version banners"], []),
 "standard_service":("Standard services exposed", ["Baseline exposure — monitor for drift"], ["Colt IP Guardian (DDoS) for exposed services; Colt Managed Firewall — confirm intended"], []),
}
SEV_ORDER = ["CRITICAL","HIGH","MEDIUM","LOW"]

# ------------------------------------------------------------------- run ---
def run(ident, F, audience, limit_per_query=500):
    import shodan
    api = shodan.Shodan(os.environ["SHODAN_API_KEY"])
    own_asns = set(ident["asns"])
    hosts = {}; asns=set(); countries=set(); records=0; dropped=0; inv={}
    for f in [f for f in F if f.get("run")]:
        q = f["clause"]; cat = f.get("cat", "sweep")
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
    for _cn in [c for c, n in sorted(seen_iss.items(), key=lambda x: -x[1]) if n >= 2][:6]:
        if _cn in ident.get("internal_cas", []): continue
        ok, why = _private_ca_ok(_cn, ident, api)
        if not ok:
            print(f"[auto] internal-CA pivot REFUSED on {_cn!r}: {why}", file=sys.stderr)
            continue
        ident.setdefault("internal_cas", []).append(_cn)
        print(f"[auto] internal-CA pivot on {_cn!r} ({why})", file=sys.stderr)
        try:
            k = 0; kept = 0; skipped = 0
            for _m in api.search_cursor(f'ssl.cert.issuer.cn:"{_cn}"'):
                ip2 = _m.get("ip_str")
                if ip2 and ip2 not in hosts:
                    # a pivot may only ADD a host it can independently tie to the target
                    if not _corroborates(_m, ident, own_asns):
                        skipped += 1
                    else:
                        hosts.setdefault(ip2, []).append(_m)
                        if _m.get("asn"): asns.add(_m["asn"])
                        kept += 1; pivot_added += 1
                k += 1
                if k >= limit_per_query: break
            print(f"[auto]   pivot {_cn!r}: +{kept} hosts, {skipped} rejected (no tie to target)",
                  file=sys.stderr)
        except shodan.APIError:
            pass

    # auto-harvest the CERT SUBJECT-O pivot: the seed cert (on a Google/CDN LB) is often a DV cert
    # with NO organisation, so the strongest anchor — the OV subject-O — is only visible on the
    # estate's OWN appliances. skon.de: the WatchGuard Firebox at 213.61.141.198 presents
    # O="S-KON Sales Kontor Hamburg GmbH"; harvesting it here and re-pivoting on
    # ssl.cert.subject.o: is what finds the owned Colt-netblock hosts the seed cert never revealed.
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
            k = 0; kept = 0
            for _m in api.search_cursor('ssl.cert.subject.o:"%s"' % _o):
                ip2 = _m.get("ip_str")
                if ip2 and ip2 not in hosts:
                    hosts.setdefault(ip2, []).append(_m)      # a target-O cert IS proof of ownership
                    if _m.get("asn"): asns.add(_m["asn"])
                    kept += 1; pivot_added += 1
                k += 1
                if k >= limit_per_query: break
            print(f"[auto]   ssl.cert.subject.o: +{kept} hosts", file=sys.stderr)
        except shodan.APIError:
            pass

    # org: pivot — brand-token whois ORGS, LEGAL SUFFIX STRIPPED. This is what finds the S-KON
    # WatchGuard Firebox + SNMP/appliance netblocks: org:"S-KON Sales Kontor Hamburg" matches the
    # stored field "S-KON SALES KONTOR HAMBURG AG" that the full 'GmbH' string missed.
    _org_pivots = {_org_core(o) for o in seen_org if _brandish(o)}
    _org_pivots |= {_org_core(o) for o in ident.get("cert_orgs", []) if _brandish(o)}
    for _oc in sorted(_org_pivots, key=len, reverse=True)[:4]:
        if len(_oc) < 5:
            continue
        print(f"[auto] whois-org pivot on org:\"{_oc}\" (legal suffix stripped)", file=sys.stderr)
        try:
            k = 0; kept = 0
            for _m in api.search_cursor('org:"%s"' % _oc):
                ip2 = _m.get("ip_str")
                if ip2 and ip2 not in hosts:
                    # org: is broad — keep only if the host's own org/whois carries the phrase, or it
                    # otherwise corroborates (own ASN / brand domain). Guards against a shared parent.
                    _ho = ((_m.get("org") or "") + " " + (_m.get("isp") or "")).lower()
                    if _oc.lower() not in _ho and not _corroborates(_m, ident, own_asns):
                        continue
                    hosts.setdefault(ip2, []).append(_m)
                    if _m.get("asn"): asns.add(_m["asn"])
                    kept += 1; pivot_added += 1
                k += 1
                if k >= limit_per_query: break
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
                                  "pivot_added": pivot_added}
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
    # Every IP the sweep KEPT has already passed recon's ownership gate, so it is owned by
    # definition. The FP auditor uses this set to avoid dropping a legitimately-scanned host that
    # simply wasn't in the DNS-probe pin list (that dropped skon.de's real critical).
    ident["scanned_ips"] = sorted(hosts.keys())
    return {"target": {"company": company_name(ident), "audience": audience or "Internal — Colt Sales Engineering",
                       "date": datetime.date.today().isoformat(),
                       "scope": f"ASN {','.join(ident['asns']) or '—'} · {len(ident['nets'])} prefixes · domains {','.join(ident['domains']) or '—'}"},
            "identity": ident,
            "summary": {"records": records, "unique_ips": len(hosts), "asns": len(asns) or len(ident["asns"]),
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
