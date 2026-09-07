"""Daily consequence for attacker infrastructure, without setting fire to our own mail reputation.

THE OPERATOR'S POINT, and it is right: *"otherwise this infrastructure stays same and just disrupts
the world."* Blocking an address protects us and costs the attacker nothing. The hosting provider
is the only party who can actually take the machine away, and nobody tells them.

THE OPERATOR'S OWN EARLIER RULE, which this file respects rather than overturns (CLAUDE.md):
*"DO NOT auto-email BSI/ENISA/ISP abuse desks daily: they don't ingest individual-operator reports,
and a server that mass-mails abuse gets its OWN domain blocklisted (fatal - it sends OTP over the
same domain)."* That risk is real and it is asymmetric: a degraded s4biz.io reputation breaks the
one-time passwords for cybergod AND jobhuntwow, which is a self-inflicted outage of the login path.

SO THE POLICY HE CHOSE (2026-09-07) IS TWO CHANNELS WITH DIFFERENT RULES:

  ABUSEIPDB -- FULLY AUTOMATIC, DAILY. It is an API, not email. It dedupes per address for 24h by
  design, it is the community channel built for exactly this, and submitting to it cannot affect
  our sending reputation because we are not sending anything. No cap needed beyond its own.

  HOSTER / CLOUD ABUSE DESKS -- GATED, and every gate is arithmetic:
    * the actor must be a REPEAT OFFENDER: seen on >= MIN_DAYS distinct days. A single burst is
      noise, and a complaint about noise is how a reporter stops being read.
    * at most MAX_PER_DAY complaints leave in 24 hours. Volume is what triggers reputation
      damage, not content.
    * deduped per /24 for DEDUPE_DAYS. One rented range is one actor; reporting its 256 addresses
      separately is spam with our name on it.
    * research scanners (Censys, Shodan, academic) are SKIPPED. They are not abuse, and reporting
      them destroys the credibility of every other complaint we file.
  A complaint that clears all four is a legitimate, evidenced operator report. A handful a week is
  normal behaviour that no provider penalises.

EVERY COMPLAINT CARRIES EVIDENCE: UTC timestamps, request counts per day, the routes touched, and
the MITRE ATT&CK technique. A complaint without evidence is a request for the recipient to do work
on our behalf, and it is deleted.

NEVER: scanning back, connecting to the address, or anything reaching the attacker's host. Criminal
under StGB s.202a/s.303b, EU Directive 2013/40, US CFAA s.1030, Canada CC s.342.1 -- and the
address is usually a compromised third party, so it would also be aimed at a victim.
"""
import ipaddress
import json
import os
import time

MIN_DAYS = int(os.environ.get("PERSEUS_ABUSE_MIN_DAYS", "2"))
MAX_PER_DAY = int(os.environ.get("PERSEUS_ABUSE_MAX_PER_DAY", "5"))
DEDUPE_DAYS = int(os.environ.get("PERSEUS_ABUSE_DEDUPE_DAYS", "30"))
STATE = os.environ.get("PERSEUS_ABUSE_STATE", "/var/log/colt/perseus_abuse.json")
ENABLED = os.environ.get("PERSEUS_ABUSE", "1") != "0"

# Reporting a research scanner is how a reporter stops being believed.
RESEARCH = ("censys", "shodan", "internet-census", "rwth-aachen", "netsystems",
            "onyphe", "leakix", "binaryedge", "driftnet", "securitytrails", "stretchoid",
            "internet-measurement", "bufferover", "arbor", "alphastrike")


def _load():
    try:
        with open(STATE, encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _save(d):
    try:
        os.makedirs(os.path.dirname(STATE), exist_ok=True)
        tmp = STATE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(d, fh, indent=1)
        os.replace(tmp, STATE)
        return True
    except Exception:
        return False


def net_of(ip):
    """One rented /24 is one actor. Reporting its addresses separately is spam with our name."""
    try:
        a = ipaddress.ip_address(ip)
    except ValueError:
        return ip
    return str(ipaddress.ip_network(ip + ("/24" if a.version == 4 else "/48"), strict=False))


def is_research(holder, org=""):
    blob = ("%s %s" % (holder or "", org or "")).lower()
    return any(m in blob for m in RESEARCH)


def eligible(actor, state=None, now=None):
    """(ok, reason). Every clause is arithmetic on observed behaviour, not a judgement call."""
    now = now or time.time()
    state = state if state is not None else _load()
    if not ENABLED:
        return False, "reporting disabled (PERSEUS_ABUSE=0)"
    days = len(actor.get("days") or {})
    if days < MIN_DAYS:
        return False, "seen on %d day(s), needs %d: one burst is noise" % (days, MIN_DAYS)
    if is_research(actor.get("holder"), actor.get("org")):
        return False, "research scanner (%s): reporting it would discredit every other complaint" \
                      % (actor.get("holder") or "?")
    net = net_of(actor.get("ip", ""))
    last = (state.get("sent") or {}).get(net)
    if last and now - float(last) < DEDUPE_DAYS * 86400:
        age_d = (now - float(last)) / 86400.0
        return False, "%s already reported %.0f day(s) ago (dedupe window %d)" % (net, age_d, DEDUPE_DAYS)
    today = time.strftime("%Y-%m-%d", time.gmtime(now))
    if (state.get("per_day") or {}).get(today, 0) >= MAX_PER_DAY:
        return False, "daily cap reached (%d): volume is what damages sending reputation" % MAX_PER_DAY
    return True, "repeat offender on %d days, %s not reported in %d days" % (days, net, DEDUPE_DAYS)


def record_sent(actor, state=None, now=None):
    now = now or time.time()
    state = state if state is not None else _load()
    today = time.strftime("%Y-%m-%d", time.gmtime(now))
    state.setdefault("sent", {})[net_of(actor.get("ip", ""))] = now
    state.setdefault("per_day", {})[today] = (state.get("per_day") or {}).get(today, 0) + 1
    # keep the ledger from growing without bound
    cutoff = now - (DEDUPE_DAYS + 7) * 86400
    state["sent"] = {k: v for k, v in (state.get("sent") or {}).items() if float(v) >= cutoff}
    state["per_day"] = {k: v for k, v in (state.get("per_day") or {}).items()
                        if k >= time.strftime("%Y-%m-%d", time.gmtime(now - 14 * 86400))}
    _save(state)
    return state


def complaint(actor):
    """The message. Evidence first, ask last: a complaint without timestamps and counts is a
    request that the recipient do the work, and it goes in the bin."""
    days = sorted((actor.get("days") or {}).items())
    routes = sorted((actor.get("routes") or {}).items(), key=lambda kv: -kv[1])
    first, last = actor.get("first"), actor.get("last")
    def _t(ts):
        return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(float(ts or 0)))
    body = [
        "Subject: Abuse report - automated scanning / resource abuse from %s" % actor.get("ip"),
        "",
        "Address       : %s" % actor.get("ip"),
        "Allocation    : %s" % (actor.get("holder") or "unknown"),
        "First seen    : %s" % _t(first),
        "Last seen     : %s" % _t(last),
        "Total requests: %d across %d day(s)" % (actor.get("total", 0), len(days)),
        "",
        "Requests per day (UTC):",
    ]
    body += ["  %s  %d" % (d, n) for d, n in days]
    body += ["", "Routes targeted:"]
    body += ["  %-44s %d" % (r[:44], n) for r, n in routes[:10]]
    body += [
        "",
        "Classification: %s" % (actor.get("classes") or "automated scanning"),
        "MITRE ATT&CK  : T1595.003 (Active Scanning: Wordlist Scanning), "
        "T1595.001 (Scanning IP Blocks)",
        "",
        "The traffic above was refused by our systems and caused no compromise. We are reporting",
        "it so you can act under your acceptable-use policy. Full request lines with status codes",
        "are available on request. We have not scanned, probed or contacted this host in return.",
        "",
        "Operator: Cybergod LLC / S4Biz Group",
        "Contact : feranicus@s4biz.io",
    ]
    return "\n".join(body)


def run(actors, dry_run=False, now=None):
    """Daily pass. Returns what was sent, what was skipped and WHY each was skipped: a silent
    skip teaches nothing, and the skip reasons are the most useful lines in the daily report."""
    now = now or time.time()
    state = _load()
    out = {"abuseipdb": [], "sent": [], "skipped": [], "errors": []}

    # ── channel 1: AbuseIPDB, automatic, no cap of ours ─────────────────────────────────
    try:
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "webapp", "backend"))
        from app import abuse_report as ar
        for a in actors:
            if is_research(a.get("holder"), a.get("org")):
                continue
            if dry_run:
                out["abuseipdb"].append({"ip": a.get("ip"), "dry_run": True})
                continue
            try:
                r = ar._report_one(a.get("ip"), "14,21", complaint(a)[:1000])
                out["abuseipdb"].append({"ip": a.get("ip"), "result": str(r)[:80]})
            except Exception as e:
                out["errors"].append("abuseipdb %s: %r" % (a.get("ip"), e))
    except Exception as e:
        out["errors"].append("AbuseIPDB channel unavailable: %r" % e)

    # ── channel 2: hoster desks, gated ──────────────────────────────────────────────────
    for a in sorted(actors, key=lambda x: -(x.get("total") or 0)):
        ok, why = eligible(a, state, now)
        if not ok:
            out["skipped"].append({"ip": a.get("ip"), "why": why})
            continue
        to = a.get("abuse") or []
        if not to:
            out["skipped"].append({"ip": a.get("ip"), "why": "no abuse contact published in RDAP"})
            continue
        if dry_run:
            out["sent"].append({"ip": a.get("ip"), "to": to, "dry_run": True, "why": why})
            continue
        try:
            import sys
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__))), "webapp", "backend"))
            from app import notify
            sent = notify.email("Abuse report - %s" % a.get("ip"), complaint(a), to=",".join(to))
            if sent:
                state = record_sent(a, state, now)
                out["sent"].append({"ip": a.get("ip"), "to": to, "why": why})
            else:
                out["errors"].append("%s: mail gateway refused; NOT recorded as sent" % a.get("ip"))
        except Exception as e:
            out["errors"].append("%s: %r" % (a.get("ip"), e))
    return out
