"""ip_reputation.py — is this address a person, or infrastructure?

WHAT IT IS FOR
    The visitor alert said "A person just opened cybergod.ai" for 45.148.10.5. That address is in
    AS48090 (TECHOFF SRV LIMITED) and resolves to DMZHOST/Amsterdam - bulletproof hosting and VPN
    exit space, and the same /24 that ran /.env and /aws-ses.json probes on 21 Jul and 10 Aug. It
    is not a person. Calling it one is the same class of bug as trusting a spoofed user agent: a
    signal the attacker controls was read as trust.

    This module answers, passively, "what kind of address is this" - residential ISP, hoster,
    VPN, bulletproof, cloud, or research scanner - so a visit from infrastructure is never
    announced as a human, and so a repeat offender can be named in the daily digest and in a
    human-reviewed abuse complaint.

TWO SPEEDS, ON PURPOSE
    classify(ip)  is OFFLINE and fast: a committed list of well-known hosting / VPN / bulletproof
                  ASNs and CIDRs plus the cloud ranges threat_intel already knows. Safe to call on
                  every request in the middleware, because it makes NO network call.
    enrich(ip)    adds the live ASN holder from RIPEstat. It DOES make a network call, so it is
                  used only by the daily digest and the abuse-report drafter, never inline.

WHAT IT IS NOT
    It never scans the address, never probes it, never tries to "see behind" a VPN or hoster -
    that is illegal in DE/EU (StGB 202a/b, 303a/b; even the tooling under 202c) and technically
    impossible from here anyway: the packets terminate at the provider. The only lawful path to
    the human is a complaint to that provider, which enrich() names but does not send.
"""
import ipaddress
import json
import os
import time
import urllib.request

# --------------------------------------------------------------------------------------------
# COMMITTED INFRASTRUCTURE LIST. Not secret, so it lives in code = auditable in git, reviewable
# in a PR. ASNs are the durable key (a hoster keeps its ASN across prefix changes); a few CIDRs
# are pinned where the ASN lookup is not available offline. "bulletproof" = a hoster with a
# documented pattern of ignoring abuse reports; naming one is a factual reputation statement, not
# an accusation against a visitor.
#   kind: hoster | vpn | bulletproof | cloud | scanner
INFRA_ASNS = {
    # the actor in front of us
    "AS48090": ("TECHOFF SRV LIMITED", "bulletproof"),
    "AS140227": ("Hong Kong Communications International", "hoster"),
    # common abuse-heavy hosting / VPN exit operators seen in the logs
    "AS9009": ("M247 (VPN/hosting)", "vpn"),
    "AS16276": ("OVH", "hoster"),
    "AS24940": ("Hetzner", "hoster"),
    "AS14061": ("DigitalOcean", "cloud"),
    "AS16509": ("Amazon AWS", "cloud"),
    "AS8075": ("Microsoft Azure", "cloud"),
    "AS15169": ("Google", "cloud"),
    "AS14618": ("Amazon AWS", "cloud"),
    "AS45102": ("Alibaba Cloud", "cloud"),
    "AS398324": ("Censys (research scanner)", "scanner"),
    "AS398722": ("Censys (research scanner)", "scanner"),
    "AS211298": ("Shodan / recon", "scanner"),
    "AS208046": ("Internet-measurement scanner", "scanner"),
}

# CIDRs pinned where we do not want to depend on a live ASN lookup to make the call.
INFRA_CIDRS = [
    ("45.148.10.0/24", "TECHOFF SRV LIMITED / DMZHOST", "bulletproof"),
    ("216.144.248.0/24", "Censys (research scanner)", "scanner"),
    ("167.94.138.0/24", "Censys (research scanner)", "scanner"),
    ("162.142.125.0/24", "Censys (research scanner)", "scanner"),
]

# The abuse desk to name per operator. threat_intel has a cloud map; this covers the rest.
ABUSE_DESKS = {
    "AS48090": "abuse@techoffshore.com",
    "AS140227": "abuse@hkcinternational.com",
    "AS9009": "abuse@m247.com",
    "AS16276": "abuse@ovh.net",
    "AS24940": "abuse@hetzner.com",
    "AS14061": "abuse@digitalocean.com",
    "AS16509": "abuse@amazonaws.com",
    "AS8075": "abuse@microsoft.com",
    "AS15169": "network-abuse@google.com",
}

_CIDRS = []
for _c, _who, _kind in INFRA_CIDRS:
    try:
        _CIDRS.append((ipaddress.ip_network(_c), _who, _kind))
    except ValueError:
        pass


def _valid(ip):
    try:
        return ipaddress.ip_address(ip)
    except ValueError:
        return None


def classify(ip):
    """OFFLINE. Returns {kind, provider, asn, source}. `kind` is one of residential/hoster/vpn/
    bulletproof/cloud/scanner/unknown. Makes NO network call - safe on the request path."""
    a = _valid(ip)
    if a is None:
        return {"kind": "unknown", "provider": None, "asn": None, "source": "invalid"}
    if a.is_private or a.is_loopback:
        return {"kind": "internal", "provider": None, "asn": None, "source": "rfc1918"}
    for net, who, kind in _CIDRS:
        if a in net:
            return {"kind": kind, "provider": who, "asn": None, "source": "committed-cidr"}
    # no offline ASN match without a lookup; unknown here means "not on the known-infra list",
    # which is treated as POSSIBLY residential and enriched later when it matters.
    return {"kind": "unknown", "provider": None, "asn": None, "source": "offline"}


def is_infrastructure(cls):
    """True when the address is a hoster/VPN/cloud/scanner rather than a residential ISP. Used to
    LABEL a visit and to record it - NOT to suppress it. `unknown` is deliberately NOT
    infrastructure: absence of evidence is not a finding."""
    return cls.get("kind") in ("hoster", "vpn", "bulletproof", "cloud", "scanner")


def never_human(cls):
    """True ONLY for kinds that never carry a real browsing person - bulletproof hosting and
    research/vuln scanners. THIS is what suppresses the 'a person just opened' alert.

    WHY NOT vpn/cloud: the first cut suppressed those too, and it blinded the operator to every
    visitor behind a consumer VPN (Kaspersky/Nord exit through M247, GB Network Solutions, etc.) -
    including the operator's own tests and real privacy-conscious prospects. A VPN visit is still a
    person; it is just labelled 'via VPN' so it is not mistaken for a residential visitor. A
    bulletproof-hosting or scanner hit (45.148.10.5) is not a person and stays suppressed."""
    return cls.get("kind") in ("bulletproof", "scanner")


def _ripestat(url, timeout=6):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "cybergod-repute/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return None


def enrich(ip):
    """OFFLINE classification PLUS a live ASN holder from RIPEstat. Network call - digest/report
    only, never inline. Fails soft to the offline result."""
    base = classify(ip)
    a = _valid(ip)
    if a is None or base["kind"] == "internal":
        return base
    d = _ripestat("https://stat.ripe.net/data/network-info/data.json?resource=%s" % ip)
    asn = None
    if d and d.get("data", {}).get("asns"):
        asn = "AS%s" % d["data"]["asns"][0]
    holder = None
    if asn:
        h = _ripestat("https://stat.ripe.net/data/as-overview/data.json?resource=%s" % asn)
        if h:
            holder = h.get("data", {}).get("holder")
    out = dict(base, asn=asn or base.get("asn"))
    if asn and asn in INFRA_ASNS and INFRA_ASNS[asn][0]:
        out["kind"] = INFRA_ASNS[asn][1]
        out["provider"] = INFRA_ASNS[asn][0]
        out["source"] = "asn"
    elif holder:
        out["provider"] = holder
        # a holder that describes itself as hosting/VPN is infrastructure; otherwise leave the
        # offline verdict (unknown = treat as residential). We NEVER upgrade to a harsher kind on
        # a keyword alone - only name it.
        low = holder.lower()
        if base["kind"] == "unknown" and any(w in low for w in (
                "hosting", "server", "datacenter", "data center", "vpn", "cloud", "colo")):
            out["kind"] = "hoster"
            out["source"] = "asn-holder"
    return out


def abuse_desk(cls):
    """The address to file a complaint with. Never used to auto-send - named only."""
    asn = cls.get("asn")
    if asn and asn in ABUSE_DESKS:
        return ABUSE_DESKS[asn]
    return None


# --------------------------------------------------------------------------------------------
# REPEAT-OFFENDER MEMORY. Keyed on the /24 (or /48 for IPv6) so a rotating single address inside
# one hosting block is still recognised as one actor. Persisted on the shared colt_events volume
# so it survives a redeploy, like the cost ledger.
_STORE = os.environ.get("REPUTE_STORE", "/var/log/colt/reputation.json")


def _net_key(ip):
    a = _valid(ip)
    if a is None:
        return None
    if a.version == 4:
        return str(ipaddress.ip_network("%s/24" % ip, strict=False))
    return str(ipaddress.ip_network("%s/48" % ip, strict=False))


def _load():
    try:
        with open(_STORE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(d):
    try:
        tmp = _STORE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f)
        os.replace(tmp, _STORE)
    except Exception:
        pass


def observe(ip, hostile=False, path=None, now=None):
    """Record that we saw this network. Returns the running record for it. `hostile` marks a
    probe/scan (as opposed to a plain visit). This is what makes 'returning again' visible."""
    key = _net_key(ip)
    if key is None:
        return {}
    now = now or time.time()
    day = time.strftime("%Y-%m-%d", time.gmtime(now))
    d = _load()
    r = d.get(key) or {"first": now, "days": [], "visits": 0, "hostile": 0, "ips": [], "paths": []}
    r["last"] = now
    r["visits"] += 1
    if hostile:
        r["hostile"] += 1
    if day not in r["days"]:
        r["days"].append(day)
        r["days"] = r["days"][-30:]
    if ip not in r["ips"]:
        r["ips"] = (r["ips"] + [ip])[-20:]
    if path and path not in r["paths"]:
        r["paths"] = (r["paths"] + [path])[-20:]
    d[key] = r
    _save(d)
    return dict(r, net=key)


def repeat_offenders(min_days=2):
    """Networks seen hostile across >= min_days DISTINCT days. Variety across days, not volume in
    one burst, is what distinguishes a returning actor from a one-off scan."""
    out = []
    for net, r in _load().items():
        if r.get("hostile", 0) and len(r.get("days", [])) >= min_days:
            out.append(dict(r, net=net))
    return sorted(out, key=lambda r: (-len(r["days"]), -r.get("hostile", 0)))
