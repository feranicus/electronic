#!/usr/bin/env python3
"""
clarify.py — post-run clarification questions for the Assess flow (cybergod.ai).

Same interaction model as jobhuntwow's Tailor (docs/TAILOR_LOGIC.md §4): the artifacts are
delivered FIRST, then the engine surfaces what it could NOT resolve as a short list of
questions. The operator answers (or adds extra facts), and a REFINE run re-scopes and
regenerates the affected decks. Answers are the ONE sanctioned way new scope enters — it keeps
the zero-false-positive ownership gate intact because the human asserted the fact.

Design choice (deliberate, matches CLAUDE.md "a static table beats an LLM here"): the questions
are DETERMINISTIC, derived from findings.json + the persisted owned-set + recon metadata. A
deterministic question is auditable, free and never hallucinates a domain. An optional LLM note
can be layered on top but never replaces the deterministic core.

    python clarify.py findings.json                 # -> prints clarify JSON to stdout
    python clarify.py findings.json -o clarify.json  # -> writes the file

Each question is machine-actionable: `maps_to` names the refine override the answer feeds, so the
backend can turn a UI answer straight into a run_assessment flag without re-deriving anything.

Question shape:
  {
    "id":     "include_unscoped",
    "kind":   "domains_multi" | "hosts_multi" | "text" | "yesno",
    "title":  "<short>",
    "body":   "<why we ask, what happens if you answer>",
    "options": [...],           # for *_multi kinds
    "placeholder": "...",       # for text kind
    "maps_to": "include_domains" | "exclude_domains" | "include_nets" |
               "include_asns" | "pin_hosts" | "platform_operator" | "notes"
  }

maps_to -> run_assessment.py flag (applied by main.py::refine):
  include_domains  -> --domain           exclude_domains  -> --exclude-domain
  include_nets     -> --net              pin_hosts        -> --pin
  include_asns     -> --asn              platform_operator-> --platform-operator
  include_org      -> --org              notes            -> --notes
"""
import argparse, json, os, sys

# a run with fewer than this many internet-facing hosts is "thin" — likely the auto-recon missed
# owned infrastructure (CDN-fronted apex, sibling domain, self-signed edge on an un-scanned netblock).
THIN_HOSTS = 6


def _load(p):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return {}


def _hosts_from_findings(fj):
    """Every distinct evidence host:port currently in the deck — the set the operator can prune."""
    seen, out = set(), []
    for f in (fj.get("findings") or []):
        for ev in (f.get("evidence") or []):
            host = str(ev).split()[0].strip()
            if host and host not in seen:
                seen.add(host)
                out.append({"host": host, "title": f.get("title", ""), "sev": f.get("sev", "")})
    return out


def build(fj):
    """findings.json -> {company, summary, questions[]}. Pure function of the persisted state."""
    tgt = fj.get("target") or {}
    owned = tgt.get("owned") or {}
    summ = fj.get("summary") or {}
    company = tgt.get("company") or fj.get("company") or "the target"

    asns = owned.get("asns") or []
    nets_n = len(tgt.get("nets") or owned.get("nets") or [])
    hosts_n = summ.get("unique_ips") or summ.get("hosts") or len(_hosts_from_findings(fj))
    related = owned.get("related_unscoped") or []
    is_cdn = bool(tgt.get("org_is_cdn") or owned.get("org_is_cdn"))

    qs = []

    # 1) Third-party / white-label apexes were EXCLUDED. This is the S-KON class: on a platform or
    #    agency target we drop client domains to keep the deck clean — but if one is actually theirs,
    #    the operator says so and we pull it back in.
    if related:
        qs.append({
            "id": "include_unscoped",
            "kind": "domains_multi",
            "title": "Are any of these related domains actually yours?",
            "body": ("I found these domains near %s but excluded them because they look like "
                     "third-party or white-label / client sites. Tick any that are genuinely YOUR "
                     "infrastructure and I will bring them into scope." % company),
            "options": related[:40],
            "maps_to": "include_domains",
        })
        # the same signal is the strongest hint this is a platform operator
        qs.append({
            "id": "platform_operator",
            "kind": "yesno",
            "title": "Do you run websites or portals on behalf of clients?",
            "body": ("If yes, I keep your clients' domains out of your report (they are the client's "
                     "attack surface, not yours). This is on by default when related domains are found."),
            "maps_to": "platform_operator",
        })

    # 2) No owned ASN / CDN-fronted (skon.de on Google): auto-discovery cannot see owned netblocks.
    #    Ask for them directly — a known CIDR or AS number is the highest-value manual anchor.
    if not asns or is_cdn:
        qs.append({
            "id": "known_netblocks",
            "kind": "text",
            "title": "Do you know your owned IP ranges or AS numbers?",
            "body": ("%s appears to front on a CDN / shared host, so automatic ASN discovery found no "
                     "owned network. If you know your public IP ranges (CIDR, e.g. 213.61.141.192/29) "
                     "or AS numbers (e.g. AS8220), add them and I will scan them directly." % company),
            "placeholder": "213.61.141.192/29, AS8220",
            "maps_to": "netblocks_or_asns",   # backend splits CIDR->--net, ASxxxx->--asn
        })

    # 3) Thin estate: likely we missed hosts. Ask for the well-known edges by name.
    if (hosts_n or 0) < THIN_HOSTS:
        qs.append({
            "id": "extra_hosts",
            "kind": "text",
            "title": "Any known systems I should add?",
            "body": ("I resolved a small footprint (%s host%s). If you know specific systems — VPN, "
                     "mail, GitLab, OWA, extranet, firewalls — give me the hostnames or IPs and I will "
                     "include them." % (hosts_n or 0, "" if hosts_n == 1 else "s")),
            "placeholder": "vpn.example.com, gitlab.example.com, 203.0.113.10",
            "maps_to": "hosts_or_domains",   # backend: resolves names, IPs->--pin, domains->--domain
        })

    # 4) Prune: let the operator drop anything in the current deck that is NOT theirs. Always offered
    #    when there is a deck to prune — it is the direct counterpart to "include", and the cheapest
    #    way to remove a stray shared-hosting neighbour the gate let through.
    cur_hosts = _hosts_from_findings(fj)
    if cur_hosts:
        qs.append({
            "id": "exclude_hosts",
            "kind": "hosts_multi",
            "title": "Is anything in the report NOT yours?",
            "body": ("These hosts are in the current findings. Tick any that do not belong to %s and I "
                     "will remove them and rebuild the decks." % company),
            "options": [h["host"] for h in cur_hosts][:60],
            "maps_to": "exclude_hosts",   # backend: IP-> exclude pin, domain-> --exclude-domain
        })

    # 5) Always: a free-text box for anything the questions did not cover (sector focus, "ignore our
    #    marketing CDN", "we also own brand X"). Fed to the LLM prose + GEOPOL as operator context.
    qs.append({
        "id": "notes",
        "kind": "text",
        "title": "Anything else I should know?",
        "body": ("Free text — extra context to steer the assessment: business focus, systems to ignore, "
                 "other brands you own, compliance drivers (NIS2/DSGVO), OT/ICS in scope, etc."),
        "placeholder": "e.g. We also own brand-x.com; ignore the marketing CDN; OT network is in scope.",
        "maps_to": "notes",
    })

    return {
        "company": company,
        "summary": {
            "hosts": hosts_n or 0, "asns": len(asns), "nets": nets_n,
            "critical": summ.get("critical", 0), "high": summ.get("high", 0),
            "excluded_related": len(related),
        },
        "questions": qs,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("findings")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()
    fj = _load(a.findings)
    if not fj:
        print("clarify: could not read %s" % a.findings, file=sys.stderr)
        sys.exit(1)
    out = build(fj)
    txt = json.dumps(out, ensure_ascii=False, indent=2)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(txt)
        print("clarify: wrote %d question(s) -> %s" % (len(out["questions"]), a.out), file=sys.stderr)
    else:
        print(txt)


if __name__ == "__main__":
    main()
