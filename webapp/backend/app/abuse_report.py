"""
abuse_report.py — submit hostile IPs to AbuseIPDB (the correct, community-consumed way).

WHY AbuseIPDB and NOT auto-emailing BSI/ENISA/ISP abuse desks:
  * BSI and ENISA do not ingest individual-operator abuse reports — it is not their function.
  * A server that auto-blasts abuse email daily gets ITS OWN domain flagged as an abuse source and
    blocklisted, which is fatal for a host that sends OTP + reports over the same domain.
  * AbuseIPDB is purpose-built: one HTTPS POST per IP, categorised, deduplicated by their side,
    consumed by firewalls/WAFs worldwide. That is the KISS-correct channel.

OPT-IN: does nothing unless ABUSEIPDB_KEY is set. Rate-limited + deduped locally so we never double
report an IP within a day (their free tier is 1,000 reports/day; we send a handful).
Categories: https://www.abuseipdb.com/categories  (14=port scan, 21=web app attack, 18=brute force,
19=bad web bot, 15=hacking).
"""
import json, os, time, urllib.parse, urllib.request

KEY   = os.environ.get("ABUSEIPDB_KEY", "")
STATE = os.path.join(os.environ.get("DATA_DIR", "/data"), "abuseipdb_sent.json")
DEDUP_H = int(os.environ.get("ABUSEIPDB_DEDUP_HOURS", "24"))

# our rule -> AbuseIPDB category ids
RULE_CAT = {
    "path_probe": [21, 14], "dir_bruteforce": [21, 19], "ip_burst": [14],
    "authz_probe": [21], "login_failed": [18], "password_spray": [18],
    "otp_bruteforce": [18], "download_burst": [21], "ddos": [4], "session_multi_ip": [15],
}


def _load():
    try: return json.load(open(STATE))
    except Exception: return {}


def _save(d):
    try:
        os.makedirs(os.path.dirname(STATE), exist_ok=True)
        json.dump(d, open(STATE, "w"))
    except Exception: pass


def _report_one(ip, categories, comment):
    data = urllib.parse.urlencode({"ip": ip, "categories": ",".join(str(c) for c in sorted(set(categories))),
                                   "comment": comment[:1024]}).encode()
    req = urllib.request.Request("https://api.abuseipdb.com/api/v2/report", data=data,
          headers={"Key": KEY, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def report_digest(digest, dry_run=False):
    """Take threat_intel.build() output and submit each hostile IP. Returns a summary."""
    if not KEY and not dry_run:
        return {"status": "disabled", "reason": "ABUSEIPDB_KEY not set (reporting is opt-in)"}
    sent = _load()
    now = time.time()
    out = []
    for a in digest.get("attackers", []):
        ip = a["ip"]
        # skip research scanners you may not want to flag (Censys/Shodan do legitimate research)
        if a.get("provider", "").startswith(("Censys",)) and os.environ.get("ABUSEIPDB_SKIP_RESEARCH", "1") == "1":
            out.append({"ip": ip, "status": "skipped-research"}); continue
        if now - float(sent.get(ip, 0)) < DEDUP_H * 3600:
            out.append({"ip": ip, "status": "already-reported"}); continue
        cats = sorted({c for r in a.get("rules", []) for c in RULE_CAT.get(r, [14])}) or [14]
        mitre = " ".join(m["id"] for m in a.get("mitre", []))
        comment = ("Automated recon/scan against cybergod.ai. Rules: %s. MITRE: %s. "
                   "Sample paths: %s. Detected by colt-web security monitoring."
                   % (",".join(a.get("rules", [])) or "scan", mitre or "T1595.003",
                      ", ".join(a.get("sample_paths", [])[:5])))
        if dry_run:
            out.append({"ip": ip, "status": "would-report", "categories": cats, "comment": comment})
            continue
        try:
            _report_one(ip, cats, comment)
            sent[ip] = now
            out.append({"ip": ip, "status": "reported", "categories": cats})
        except Exception as e:
            out.append({"ip": ip, "status": "error", "error": repr(e)[:120]})
    if not dry_run:
        _save(sent)
    return {"status": "ok" if KEY else "dry-run", "results": out,
            "reported": sum(1 for r in out if r["status"] == "reported")}


if __name__ == "__main__":
    import sys
    from importlib import import_module
    sys.path.insert(0, os.path.dirname(__file__))
    ti = import_module("threat_intel")
    dry = "--send" not in sys.argv
    d = ti.build(24, sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else None)
    print(json.dumps(report_digest(d, dry_run=dry), indent=2))
    if dry:
        print("\n(dry-run — add --send and set ABUSEIPDB_KEY to actually submit)")


# =================================================================================================
# HUMAN-REVIEWED ABUSE COMPLAINT DRAFTER.
# The four models draft an evidence package for a REPEAT offender; a HUMAN files it. Nothing here
# is sent automatically. BSI, CISA and national CERTs act on evidence packages from a named
# reporter, not on automated pings - and a server that mass-mails abuse desks gets its own domain
# blocklisted, which is fatal when the same domain sends the login OTP. So this produces text; the
# operator reviews it and sends it to the hoster's abuse desk (which enrich() names) or attaches it
# to a formal complaint. Lawful, and it does not send one packet to the attacker.
# =================================================================================================
def draft_complaint(record, holder=None, abuse_email=None):
    """`record` is an ip_reputation repeat-offender dict. Returns plain text for a human to file."""
    net = record.get("net", "?")
    ips = ", ".join(record.get("ips", [])[:10]) or net
    days = record.get("days", [])
    paths = ", ".join(record.get("paths", [])[:12]) or "(various probe paths)"
    first = time.strftime("%Y-%m-%d", time.gmtime(record.get("first", time.time())))
    last = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(record.get("last", time.time())))
    lines = [
        "Subject: Abuse report - automated vulnerability scanning of cybergod.ai",
        "",
        "To: %s" % (abuse_email or "the network's published abuse contact"),
        "From: security@cybergod.ai (Cybergod LLC / S4Biz Group)",
        "",
        "We operate cybergod.ai (Frankfurt, DE). The addresses below, on your network%s, have"
        % ((" (%s)" % holder) if holder else ""),
        "repeatedly probed our service for exposed secrets and known vulnerable paths. This is",
        "unsolicited automated scanning, not legitimate traffic.",
        "",
        "Network      : %s" % net,
        "Addresses    : %s" % ips,
        "First seen   : %s" % first,
        "Last seen    : %s" % last,
        "Distinct days: %d  (%s)" % (len(days), ", ".join(days[-8:])),
        "Total probes : %d" % record.get("hostile", 0),
        "Sample paths : %s" % paths,
        "Technique    : MITRE ATT&CK T1595.003 (active scanning: wordlist), T1595.001.",
        "",
        "No data was exposed - every probe received an HTTP 404. We are reporting so you can act",
        "on your customer under your acceptable-use policy. Full request logs are available on",
        "request. This report is filed under GDPR Art. 6(1)(f) (network and information security).",
        "",
        "-- Cybergod LLC / S4Biz Group, security@cybergod.ai",
    ]
    return "\n".join(lines)


def complaints_for_repeat_offenders(min_days=2, enrich=True):
    """Build one complaint per returning actor. enrich() names the hoster + abuse desk (one RIPE
    lookup each); pass enrich=False for a fully offline draft."""
    import importlib
    rep = importlib.import_module("ip_reputation") if __package__ is None \
        else importlib.import_module(".ip_reputation", __package__)
    out = []
    for r in rep.repeat_offenders(min_days=min_days):
        holder = abuse = None
        if enrich and r.get("ips"):
            info = rep.enrich(r["ips"][0])
            holder = info.get("provider")
            abuse = rep.abuse_desk(info)
        out.append({"net": r["net"], "holder": holder, "abuse_email": abuse,
                    "complaint": draft_complaint(r, holder, abuse)})
    return out
