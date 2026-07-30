#!/usr/bin/env python3
"""
attribution.py — graded ownership confidence with a rule log, replacing the binary in/out gate.

WHY (this is the enterprise pattern, not an invention)
------------------------------------------------------
Every false-positive incident in this engine came from a BOOLEAN decision: brand token present ->
in, absent -> out. That cliff produced, in order: 1,003 cPanel hosts (bibeltv), 746 client
microsites (S-KON), 1,417 hoster IPs (rightmart), a law firm and a dental practice (angermann).
Each fix moved the cliff; none removed it.

Commercial EASM does not work that way. Qualys CSAM publishes an explicit **Attribution Confidence
Score** (High/Medium/Low) and LOGS the rules and execution details behind each score, precisely
because "when it's Low, it's not straightforward to infer if the asset belongs to your
organization" (docs.qualys.com/en/csam/latest/inventory/confidence_score.htm). The general industry
practice is to grade confidence BY DISCOVERY SOURCE — DNS + TLS + HTTP agreement = high confidence —
to cut time wasted on misattributed assets (ionix.io, devsecopsschool.com), drawing on whois,
certificates and DNS together. Shared hosting and CDNs are named as the specific cause of obscured
ownership — exactly the shared Colt /24 and the jweiland.cloud TYPO3 host in your decks.

THE MODEL
---------
Independent signals contribute points. Ownership is not a coin flip but a weight of evidence, and
crucially TWO WEAK SIGNALS THAT AGREE beat one strong signal that does not:

    100  seed apex itself
     92  named on the customer's own published group-structure page   (first-party assertion)
     88  certificate CN/SAN names the host and the apex is owned
     85  sibling TLD of a published group domain (exact label match)
     80  the host's OWN per-IP whois org corroborates the seed brand
     75  vendor-tenant label equals a brand token (angermann.3cx.eu)
     70  resolved from the customer's own DNS (pinned)
     40  brand token in the apex label, nothing else            <- the surname trap lives here
     25  same netblock as an owned host, different whois org    <- the co-tenant trap lives here
    -35  apex absent from a PUBLISHED group structure (positive counter-evidence)
    -30  whois org looks like a provider (hoster/"trading as"/>20 prefixes)

Bands: >=80 CONFIRMED (main deck) · 50-79 PROBABLE (main deck, flagged) · 25-49 UNCONFIRMED
(appendix + clarify question) · <25 REJECTED.

Every asset carries `signals` — the rules that fired, with points — so a disputed host can be
explained to the customer instead of argued about. That is the Qualys "logged rules" property.

    python attribution.py --demo        # scores the real angermann hosts
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

CONFIRMED, PROBABLE, UNCONFIRMED = 80, 50, 25

RULES = {
    "seed_apex":        (100, "the seed domain itself"),
    "group_structure":  (92,  "named on the customer's own published group-structure page"),
    "cert_names_host":  (88,  "a certificate on this host names an owned domain"),
    "sibling_tld":      (85,  "sibling TLD of a published group domain (exact label match)"),
    "own_whois_org":    (80,  "the host's own whois organisation corroborates the seed brand"),
    "vendor_tenant":    (75,  "brand is the tenant label on a known multi-tenant vendor domain"),
    "pinned_dns":       (70,  "resolved from the customer's own DNS"),
    "brand_token_only": (40,  "brand token in the label, no other corroboration"),
    "same_netblock":    (25,  "shares a netblock with an owned host but has a different whois org"),
    "absent_from_structure": (-35, "apex is ABSENT from the customer's published group structure"),
    "provider_org":     (-30, "whois organisation looks like a hosting provider"),
}


def score(signals):
    """[signal keys] -> (0..100, band, [explanations]).

    Not a plain sum: the strongest signal sets the floor, and each ADDITIONAL independent signal
    adds a diminishing bonus. Two agreeing weak signals therefore clear UNCONFIRMED, while ten
    repetitions of the same weak signal do not manufacture certainty.
    """
    pos = sorted([RULES[s][0] for s in signals if s in RULES and RULES[s][0] > 0], reverse=True)
    neg = sum(RULES[s][0] for s in signals if s in RULES and RULES[s][0] < 0)
    if not pos:
        base = 0
    else:
        base = pos[0]
        for i, p in enumerate(pos[1:], start=1):
            base += p * (0.25 / i)          # 2nd signal +25% of its weight, 3rd +12.5%, ...
    total = max(0, min(100, int(round(base + neg))))
    band = ("CONFIRMED" if total >= CONFIRMED else
            "PROBABLE" if total >= PROBABLE else
            "UNCONFIRMED" if total >= UNCONFIRMED else "REJECTED")
    why = ["%+d  %s" % (RULES[s][0], RULES[s][1]) for s in signals if s in RULES]
    return total, band, why


def signals_for(host, ctx):
    """Derive the signal set for one Shodan host record.

    ctx: {seed_apex, brand_tokens, group_domains, structure_known, owned_domains, pinned_ips}
    Pure function of evidence — no network, no model. Auditable and unit-testable.
    """
    import shodan_recon as R
    out = []
    seed = ctx.get("seed_apex") or ""
    btoks = set(ctx.get("brand_tokens") or [])
    group = set(ctx.get("group_domains") or [])
    owned = set(ctx.get("owned_domains") or []) | group | ({seed} if seed else set())

    names = {str(h).lower() for h in (host.get("hostnames") or [])}
    cert = ((host.get("ssl") or {}).get("cert") or {}).get("subject") or {}
    if cert.get("CN"):
        names.add(str(cert["CN"]).lower().lstrip("*."))
    org = host.get("org") or ""
    ip = host.get("ip_str") or ""

    apexes = {R._apex(n) for n in names if R._apex(n)}
    if seed in apexes:
        out.append("seed_apex")
    if apexes & group:
        out.append("group_structure")
    for a in apexes:
        lab = a.split(".")[0]
        if a not in group and any(lab == g.split(".")[0] for g in group):
            out.append("sibling_tld")
            break
    if names & {n for n in names if any(n == o or n.endswith("." + o) for o in owned)}:
        if cert.get("CN") and any(str(cert["CN"]).lower().lstrip("*.").endswith(o) for o in owned):
            out.append("cert_names_host")
    if org and R._org_is_the_target(org, seed):
        out.append("own_whois_org")
    # vendor_tenant ONLY when the apex is a KNOWN multi-tenant vendor domain and the label equals a
    # brand token. Calling _owns_host() alone was wrong: it also returns True via the brand-token
    # path, so ra-angermann.de (a law firm on Hetzner) was scored as a vendor tenant.
    for n in names:
        ap_n = R._apex(n)
        is_vendor = ap_n in R.TENANT_APEX or any(ap_n == t or ap_n.endswith("." + t)
                                                 for t in R.TENANT_APEX)
        if not is_vendor:
            continue
        lab = "".join(c for c in n.split(".")[0].lower() if c.isalnum())
        if any(t and len(t) >= 4 and t == lab for t in btoks):
            out.append("vendor_tenant")
            break
    if ip and ip in set(ctx.get("pinned_ips") or []):
        out.append("pinned_dns")
    if not out:
        for a in apexes:
            lab = "".join(c for c in a.split(".")[0] if c.isalnum())
            if any(t and len(t) >= 4 and t in lab for t in btoks):
                out.append("brand_token_only")
                # POSITIVE counter-evidence: the customer published a roster and this is not on it.
                if ctx.get("structure_known"):
                    out.append("absent_from_structure")
                break
    # The provider penalty must NOT fire when the host is a vendor-hosted tenant, is pinned by the
    # customer's own DNS, or is named by an owned certificate: all three are BY DEFINITION on
    # somebody else's infrastructure. Penalising them would delete exactly the assets we just
    # worked to find (the 3CX PBX sits on netcup; that is what SaaS means).
    _exempt = {"vendor_tenant", "pinned_dns", "cert_names_host", "own_whois_org", "seed_apex",
               "group_structure", "sibling_tld"}
    if org and R._looks_like_provider(org) and not (set(out) & _exempt):
        out.append("provider_org")
    return sorted(set(out))


def assess(host, ctx):
    sig = signals_for(host, ctx)
    total, band, why = score(sig)
    return {"ip": host.get("ip_str"), "confidence": total, "band": band,
            "signals": sig, "why": why}


def _demo():
    """Score the REAL angermann hosts — the ones that caused every complaint."""
    ctx = {"seed_apex": "angermann.de", "brand_tokens": ["angermann"],
           "group_domains": ["netbid.com", "leaseback.de", "buerosuche.de", "nordleasing.com",
                             "angermann-consult.de", "angermann-realestate.de", "oaklins.com"],
           "structure_known": True, "owned_domains": ["angermann.de"],
           "pinned_ips": ["217.110.51.2"]}
    hosts = [
        ({"ip_str": "217.110.51.7", "org": "Horst F.G. Angermann GmbH",
          "hostnames": ["passbolt.angermann.de"],
          "ssl": {"cert": {"subject": {"CN": "passbolt.angermann.de"}}}}, "Passbolt vault"),
        ({"ip_str": "87.234.246.51", "org": "Netbid Industrie Aukrion AG",
          "hostnames": ["netbid.com"]}, "NetBid (subsidiary)"),
        ({"ip_str": "185.58.227.251", "org": "Aruba S.p.A.", "hostnames": ["netbid.io"],
          "ssl": {"cert": {"subject": {"CN": "netbid.io"}}}}, "netbid.io mail (sibling TLD)"),
        ({"ip_str": "94.16.117.249", "org": "netcup GmbH", "hostnames": ["v22026.powersrv.de"],
          "ssl": {"cert": {"subject": {"CN": "angermann.3cx.eu"}}}}, "3CX PBX (vendor tenant)"),
        ({"ip_str": "142.132.178.138", "org": "Hetzner Online GmbH",
          "hostnames": ["ra-angermann.de"]}, "LAW FIRM (surname)"),
        ({"ip_str": "79.214.82.129", "org": "Deutsche Telekom AG",
          "hostnames": ["p4fd.dip0.t-ipconnect.de"],
          "ssl": {"cert": {"subject": {"CN": "praxisangermann.dyndns.org",
                                       "O": "Zahnarztpraxis Angermann"}}}}, "DENTIST"),
        ({"ip_str": "217.110.51.18", "org": "NORDRHEINISCHE AERZTEVERSORGUNG",
          "hostnames": ["naev.de"]}, "co-tenant on the shared /24"),
    ]
    print("  %-16s %-30s %5s  %-12s %s" % ("IP", "WHAT", "CONF", "BAND", "SIGNALS"))
    for h, label in hosts:
        r = assess(h, ctx)
        print("  %-16s %-30s %5d  %-12s %s"
              % (r["ip"], label, r["confidence"], r["band"], ",".join(r["signals"]) or "-"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--findings")
    a = ap.parse_args()
    if a.demo or not a.findings:
        _demo()
        return 0
    fj = json.load(open(a.findings, encoding="utf-8"))
    print(json.dumps(fj.get("target", {}).get("owned", {}), indent=2)[:400])
    return 0


if __name__ == "__main__":
    sys.exit(main())
