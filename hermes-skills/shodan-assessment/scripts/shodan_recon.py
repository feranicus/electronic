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
import os, re, sys, json, socket, argparse, datetime, urllib.request

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
             "asn_holder": None, "domains": [], "org_is_carrier": False, "org_is_cdn": False, "assignment_netname": None}
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

def merge_variants(ident, orgs=None, brands=None, domains=None, favicons=None):
    """Fold in org-name / brand / domain / favicon variants (playbook #3-#7) so recon
    searches the target's IDENTITY across ALL ASNs, not just the seed ASN's sweep."""
    orgs = orgs or []; brands = brands or []; domains = domains or []; favicons = favicons or []
    base_o = [ident["org"]] if ident.get("org") else []
    ident["org_variants"] = list(dict.fromkeys([o for o in (base_o + orgs) if o]))
    base_b = [ident["brand"]] if ident.get("brand") else []
    ident["brand_variants"] = list(dict.fromkeys([b for b in (base_b + brands) if b]))
    for d in domains:
        dd = _clean_domain(d)
        if dd and dd not in ident["domains"]: ident["domains"].append(dd)
    ident["favicons"] = list(dict.fromkeys([str(h).strip() for h in favicons if str(h).strip()]))
    return ident

# ----------------------------------------------------------- canonical filters ---
P_REMOTE_DB = "3389,22,23,5900,445,3306,1433,5432,6379,27017,9200,21"
P_RDP_WINRM = "3389,3390,5985,5986,5900,5800"
P_VPN_MGMT  = "443,4433,8443,10443,4443,500,4500,1194"
P_ICS       = "102,502,4840,44818,20000,1911,47808,789,9600,2404,20547"
P_MAIL      = "25,587,465,143,993,110,995"
PROD_ICS    = '"Modbus","Siemens S7","BACnet","DNP3","IEC-104","OPC-UA"'
PROD_PANEL  = '"Citrix","Fortinet","Pulse Secure","Palo Alto","OpenVPN","SonicWall","Sophos","Cisco ASA"'

def build_filters(ident):
    asns = ",".join(ident["asns"]); nets = ",".join(ident["nets"])
    org = ident["org"]; domains = ident["domains"]; cdn = ident["org_is_cdn"]
    own_asn = bool(ident["asns"]) and not ident["org_is_carrier"] and not cdn
    run_net = bool(nets) and not cdn
    scope = (f"asn:{asns}" if own_asn else (f"net:{nets}" if run_net else (f'org:"{org}"' if org else "")))
    F = []
    def _cat(clause):
        c = clause.lower()
        return "identity" if any(k in c for k in ("ssl", "hostname:", "org:", "http.title", "http.html", "favicon")) else "sweep"
    def add(n, name, clause, run=False, note=""):
        if clause: F.append({"n": n, "name": name, "clause": clause, "run": run, "note": note, "cat": _cat(clause)})
    if own_asn:
        add(1, "ASN sweep", f"asn:{asns}", run=True, note="every host announced from the org's ASNs")
    elif ident["asns"]:
        why = "CDN" if cdn else "carrier"
        add(1, "ASN sweep — SKIPPED", f'# {asns} is {why} "{ident["asn_holder"]}", not the target', run=False,
            note=f"{why} ASN would return the whole {why} estate — use net/ssl/hostname or the real ASN")
    add(2, "Netblock / CIDR (master)", f"net:{nets}" if nets else "", run=run_net,
        note=("SKIPPED — belongs to the CDN, not the target" if (nets and cdn) else "the target's own IP space"))
    orgs = ident.get("org_variants") or ([org] if org else [])
    brands = [b for b in (ident.get("brand_variants") or ([ident["brand"]] if ident.get("brand") else [])) if b and not CIDR_RE.match(str(b))]
    favicons = ident.get("favicons") or []
    for o in orgs:                       # #3 org-name match (+ variants: subsidiaries, native spellings)
        add(3, "Org-name match", f'org:"{o}"', run=True, note="reassigned/cloud/subsidiary ranges — try name variants")
    for d in domains:                    # #4 cert CN — finds origin behind CDN/hoster, any ASN
        add(4, "TLS cert subject CN", f'ssl.cert.subject.cn:"{d}"', run=True, note="real origin even behind a CDN/hoster")
    for b in brands:                     # #4/#5 cert free-text across ANY ASN (cross-ASN estate)
        add(5, "TLS free-text / cert org", f'ssl:"{b}"', run=True, note="wildcard & SAN certs across any ASN")
    for d in domains:                    # #5 hostname / rDNS
        add(6, "Hostname / domain", f'hostname:".{d}"', run=True, note="reverse-DNS / HTTP host")
    for b in brands:                     # #6 branded HTTP title/body (portals, shadow IT)
        add(14, "HTTP title (branded)", f'http.title:"{b}"', run=True, note="branded portals/login pages on any host")
        add(15, "HTTP body (branded)", f'http.html:"{b}"', run=True, note="branded body content / shadow IT")
    for h in favicons:                   # #7 favicon hash (branded icon, any host)
        add(16, "Favicon hash", f'http.favicon.hash:{h}', run=True, note="every host serving the branded icon")
    if scope:
        add(7, "Remote-access & DB ports", f"{scope} port:{P_REMOTE_DB}", note="RDP/SSH/Telnet/VNC/SMB/DB/FTP")
        add(8, "VPN / firewall mgmt", f"{scope} port:{P_VPN_MGMT} product:{PROD_PANEL}", note="edge-VPN = top ransomware vector")
        add(9, "RDP / WinRM / VNC", f"{scope} port:{P_RDP_WINRM}", note="remote desktop / mgmt")
        add(10, "OT / ICS / SCADA", f"{scope} tag:ics port:{P_ICS} product:{PROD_ICS}", note="industrial protocols")
        add(11, "Mail / Exchange / OWA", f"{scope} port:{P_MAIL}", note="on-prem mail + OWA")
        add(12, "Vuln & TLS/EOL hygiene",
            f"{scope} has_vuln:true  |  {scope} ssl.cert.expired:true  |  {scope} ssl.version:sslv3,tlsv1,tlsv1.1",
            note="CISA KEV = CRITICAL")
        add(13, "Logins / panels / non-prod",
            f'{scope} http.title:"login","admin","portal","vpn","dashboard","phpMyAdmin","Webmin"', note="forgotten admin UIs")
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
          f"- Domains: {', '.join(ident['domains']) or '—'}", "", "## Super filters", ""]
    for f in F:
        L.append(f"### {f['n']}. {f['name']}")
        if f["note"]: L.append(f"_{f['note']}_")
        L += ["```", f["clause"], "```", ""]
    return "\n".join(L)

# ------------------------------------------------------------------ classify ---
DB_PORTS = {27017:"MongoDB",9200:"Elasticsearch",6379:"Redis",5432:"PostgreSQL",3306:"MySQL",
            1433:"MSSQL",5984:"CouchDB",11211:"Memcached",9042:"Cassandra"}
ICS_PORTSET = {102:"S7",502:"Modbus",4840:"OPC-UA",44818:"EtherNet/IP",20000:"DNP3",1911:"Fox",
               47808:"BACnet",789:"Red Lion",2404:"IEC-104",20547:"ProConOS",9600:"OMRON"}
REMOTE_HI = {23:"Telnet",5900:"VNC",5800:"VNC-http",445:"SMB",5985:"WinRM",5986:"WinRM",3390:"RDP"}
VPN_PORTS = {4433,8443,10443,4443,500,4500,1194}

def classify(m):
    port = m.get("port"); prod = (m.get("product") or ""); vulns = m.get("vulns") or {}
    ssl = m.get("ssl") or {}; tags = m.get("tags") or []
    title = ((m.get("http") or {}).get("title") or "")
    if "ics" in tags or "scada" in tags or port in ICS_PORTSET: return "CRITICAL","ics"
    if port in DB_PORTS:  return "CRITICAL","db_exposed"
    if port in (3389, 3390): return "CRITICAL","rdp"
    if vulns:             return "HIGH","vuln_tagged"
    if port in VPN_PORTS or re.search(r'(?i)fortinet|pulse|palo alto|sonicwall|citrix|cisco asa|openvpn|sophos', prod):
        return "HIGH","vpn_appliance"
    if port in REMOTE_HI: return "HIGH","remote_admin"
    if title and re.search(r'(?i)login|admin|portal|vpn|dashboard|phpmyadmin|webmin|outlook|exchange', title):
        return "HIGH","exposed_panel"
    versions = ssl.get("versions") or []
    if any(v.lstrip("-") in ("TLSv1","TLSv1.0","SSLv3","SSLv2","TLSv1.1") for v in versions): return "MEDIUM","legacy_tls"
    cert = ssl.get("cert") or {}
    if cert.get("expired"): return "MEDIUM","expired_tls"
    if cert.get("issuer") and cert.get("issuer") == cert.get("subject"): return "MEDIUM","self_signed"
    if prod and m.get("version"): return "MEDIUM","verbose_banner"
    return "LOW","standard_service"

TEMPLATES = {
 "rdp":        ("Internet-facing RDP", ["#1 ransomware entry vector","Credential brute-force"], ["Colt SASE / ZTNA — retire the exposed RDP; broker access with MFA","Colt Managed Firewall — block 3389 at the edge"], ["MITRE T1133"]),
 "db_exposed": ("Exposed database", ["Direct data-exfiltration path","Often unauthenticated"], ["Colt Managed Firewall — remove the DB from the internet","Colt DPI/NDR — detect exfiltration attempts"], ["MITRE T1190"]),
 "ics":        ("Exposed ICS/OT protocol", ["Safety/availability impact","NIS2 / ISO 27001 driver"], ["Colt Managed Firewall + IT/OT segmentation","Colt SD-WAN secure OT transport; Colt IP Guardian (DDoS)"], ["MITRE ICS","NIS2 Art.21"]),
 "vuln_tagged":("Shodan-tagged vulnerabilities (CVE)", ["Pre-mapped exploit paths; check CISA KEV"], ["Colt WAF — virtual-patch the exposed CVE","Colt Managed Security — KEV/EPSS-prioritised patch orchestration"], ["Shodan vulns","CISA KEV"]),
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
    hosts = {}; asns=set(); countries=set(); records=0; dropped=0
    for f in [f for f in F if f.get("run")]:
        q = f["clause"]; cat = f.get("cat", "sweep")
        n = 0
        try:
            for m in api.search_cursor(q):
                tags = m.get("tags") or []
                if "honeypot" in tags: dropped += 1; continue
                # FP drop applies ONLY to broad sweeps (asn:/net:). Identity matches
                # (org/ssl/hostname/http/favicon) ARE the target by name/cert — always keep,
                # even on a hoster/cloud ASN. This is how we catch the cross-ASN estate
                # (e.g. a Cisco ASA VPN on a hoster that the target's own ASN sweep misses).
                if cat == "sweep":
                    horg = (m.get("org") or "") + " " + (m.get("isp") or "")
                    masn = ("AS" + str(m.get("asn"))) if str(m.get("asn") or "").isdigit() else (m.get("asn") or "")
                    if _is(horg, CDNS) and (own_asns and masn not in own_asns): dropped += 1; continue
                hosts.setdefault(m.get("ip_str"), []).append(m)
                if m.get("asn"): asns.add(m["asn"])
                c = (m.get("location") or {}).get("country_code")
                if c: countries.add(c)
                n += 1
                if n >= limit_per_query: break
        except shodan.APIError as e:
            print(f"[warn] query {q!r}: {e}", file=sys.stderr)
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
    return {"target": {"company": company_name(ident), "audience": audience or "Internal — Colt Sales Engineering",
                       "date": datetime.date.today().isoformat(),
                       "scope": f"ASN {','.join(ident['asns']) or '—'} · {len(ident['nets'])} prefixes · domains {','.join(ident['domains']) or '—'}"},
            "identity": ident,
            "summary": {"records": records, "unique_ips": len(hosts), "asns": len(asns) or len(ident["asns"]),
                        "countries": len(countries), "dropped_false_positives": dropped,
                        "behind_cdn": ident["org_is_cdn"],
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
    ap.add_argument("--audience"); ap.add_argument("--outdir", default=".")
    ap.add_argument("--print-filters", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    ident = resolve_identity(a.seed)
    for asn in a.asn:                                   # manual real-ASN injection (e.g. behind CDN)
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
    merge_variants(ident, a.org, a.brand, a.domain, a.favicon)
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
