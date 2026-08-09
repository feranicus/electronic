"""email_auth.py — SPF / DMARC / DKIM / MTA-STS posture, from DNS alone.

WHY THIS EXISTS. The engine could describe a company's servers and say nothing at all about the
one asset every one of its customers, suppliers and staff sees every day: its email domain. Domain
spoofing does not need a single exposed host. It needs a domain with no DMARC policy, and it is the
delivery mechanism for the business-email-compromise losses that the C-BIQ deck prices.

ZERO PACKETS TO THE TARGET. Every check here is a DNS query answered by a public resolver over
DNS-over-HTTPS. Nothing is sent to the customer's infrastructure, so this ships in the default,
authorisation-free tier and the "not one packet" promise is untouched.

THE HARD RULE THIS MODULE MUST OBEY, twice:
  · absence of evidence is never a finding. A DNS lookup that FAILS returns None and produces
    nothing. Only a lookup that SUCCEEDED and came back empty is a finding.
  · DKIM CANNOT BE PROVEN ABSENT. A DKIM key lives at <selector>._domainkey.<domain> and the
    selector is arbitrary — "s1", "google", "mandrill2024", anything. Probing a list of common
    selectors can only ever prove PRESENCE. So a DKIM key that is found is reported as context;
    one that is not found is reported as NOT DETERMINABLE, never as "missing". Getting this wrong
    would put a false accusation of a missing control into a customer deck.

Sources: RFC 7208 (SPF), RFC 7489 (DMARC), RFC 8461 (MTA-STS), RFC 6376 (DKIM).
"""
import json
import re
import urllib.parse
import urllib.request

UA = {"User-Agent": "cybergod-assessment/1.0"}

# Selectors worth asking about. Presence is informative; absence proves nothing (see the header).
DKIM_SELECTORS = ("default", "google", "selector1", "selector2", "k1", "k2", "s1", "s2",
                  "dkim", "mail", "smtp", "mandrill", "zoho", "everlytickey1", "protonmail")

# Mechanisms that each cost a DNS lookup under RFC 7208 §4.6.4. More than ten and a receiver MUST
# return PermError, which in practice means the SPF record stops being evaluated at all.
#
# THEY MUST BE COUNTED BY TOKEN, NOT BY SUBSTRING. `a` and `mx` are legal bare (`v=spf1 a mx -all`
# costs two lookups), so matching on "a:" and "mx:" scored that record as ZERO and the check could
# never fire. Substring matching is also wrong in the other direction: "a" appears inside
# "include:", "ip4" and half the domain names in the record.
_LOOKUP_MECHANISMS = ("include", "a", "mx", "ptr", "exists", "redirect")


def _spf_lookups(record):
    """How many DNS lookups evaluating this SPF record costs, per RFC 7208 §4.6.4."""
    n = 0
    for tok in str(record).split():
        t = tok.lstrip("+-~?").lower()          # strip the qualifier
        name = re.split(r"[:=]", t, 1)[0]
        if name in _LOOKUP_MECHANISMS:
            n += 1
    return n


def _txt(name, timeout=8):
    """TXT records for a name, or None if the lookup FAILED.

    [] means "asked successfully, nothing published" -- that is a finding.
    None means "could not ask" -- that is never a finding.
    """
    try:
        u = "https://dns.google/resolve?name=%s&type=TXT" % urllib.parse.quote(str(name))
        with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=timeout) as r:
            j = json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return None
    if not isinstance(j, dict) or "Status" not in j:
        return None
    st = int(j.get("Status", -1))
    if st == 3:                      # NXDOMAIN: asked successfully, the name does not exist
        return []
    if st != 0:
        return None                  # SERVFAIL / REFUSED / anything else: we could not ask
    out = []
    for a in (j.get("Answer") or []):
        if a.get("type") != 16:
            continue
        # DoH returns TXT data quoted, and long records arrive as adjacent quoted chunks that the
        # DNS layer split at 255 bytes. They must be RE-JOINED before parsing or a long SPF record
        # is silently truncated mid-mechanism.
        v = str(a.get("data") or "")
        parts = re.findall(r'"([^"]*)"', v)
        out.append("".join(parts) if parts else v.strip('"'))
    return out


def parse_spf(records):
    """The SPF record and what it actually enforces. Returns None if no SPF record is published."""
    spf = [r for r in (records or []) if r.lower().startswith("v=spf1")]
    if not spf:
        return None
    out = {"record": spf[0], "duplicate": len(spf) > 1, "lookups": 0}
    txt = spf[0].lower()
    # RFC 7208 §4.5: more than one SPF record is a PermError -- the domain has NO working SPF.
    out["lookups"] = _spf_lookups(spf[0])
    m = re.search(r'([-~?+])all\b', txt)
    out["all"] = m.group(1) if m else None
    out["policy"] = {"-": "hardfail", "~": "softfail", "?": "neutral", "+": "pass"}.get(
        out.get("all") or "", "none")
    return out


def parse_dmarc(records):
    """The DMARC policy. Returns None if no DMARC record is published."""
    rec = [r for r in (records or []) if r.lower().replace(" ", "").startswith("v=dmarc1")]
    if not rec:
        return None
    txt = rec[0]
    tags = {}
    for part in txt.split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            tags[k.strip().lower()] = v.strip()
    pct = tags.get("pct", "100")
    try:
        pct = int(pct)
    except Exception:
        pct = 100
    return {"record": txt, "p": (tags.get("p") or "").lower(),
            "sp": (tags.get("sp") or "").lower(), "pct": pct,
            "rua": bool(tags.get("rua")), "ruf": bool(tags.get("ruf")),
            "adkim": (tags.get("adkim") or "r").lower(), "aspf": (tags.get("aspf") or "r").lower()}


def assess(domain, txt_of=None):
    """The full email-authentication posture of a domain.

    `txt_of` is injected for testing. Every value is either a fact from a successful lookup or the
    explicit string "unknown"; nothing here guesses.
    """
    look = txt_of or _txt
    apex = look(domain)
    dmarc_recs = look("_dmarc." + str(domain))
    mta = look("_mta-sts." + str(domain))

    out = {"domain": str(domain), "issues": [], "context": []}
    out["spf"] = parse_spf(apex) if apex is not None else "unknown"
    out["dmarc"] = parse_dmarc(dmarc_recs) if dmarc_recs is not None else "unknown"
    out["mta_sts"] = (bool([r for r in (mta or []) if "v=stsv1" in r.lower().replace(" ", "")])
                      if mta is not None else "unknown")

    # ---- DMARC. The single highest-value record here: without an enforcing policy, a receiving
    # mail server has no instruction to reject a forgery of this domain.
    d = out["dmarc"]
    if d == "unknown":
        out["context"].append("DMARC lookup failed — posture not determinable, no finding claimed")
    elif d is None:
        out["issues"].append({"id": "dmarc_missing", "sev": "HIGH",
                              "detail": "No DMARC record at _dmarc.%s" % domain})
    else:
        if d["p"] in ("", "none"):
            out["issues"].append({"id": "dmarc_monitor_only", "sev": "MEDIUM",
                                  "detail": "DMARC published but p=%s — monitoring only, no "
                                            "forgery is rejected" % (d["p"] or "absent")})
        elif d["p"] == "quarantine" and d["pct"] < 100:
            out["issues"].append({"id": "dmarc_partial", "sev": "MEDIUM",
                                  "detail": "DMARC p=quarantine but pct=%d — %d%% of forgeries are "
                                            "delivered untouched" % (d["pct"], 100 - d["pct"])})
        if not d["rua"]:
            out["issues"].append({"id": "dmarc_no_reporting", "sev": "LOW",
                                  "detail": "DMARC has no rua= address — nobody receives the "
                                            "aggregate reports that show who is forging the domain"})

    # ---- SPF.
    s = out["spf"]
    if s == "unknown":
        out["context"].append("SPF lookup failed — not determinable, no finding claimed")
    elif s is None:
        out["issues"].append({"id": "spf_missing", "sev": "MEDIUM",
                              "detail": "No SPF record published for %s" % domain})
    else:
        if s["duplicate"]:
            out["issues"].append({"id": "spf_duplicate", "sev": "MEDIUM",
                                  "detail": "More than one SPF record — RFC 7208 §4.5 makes this a "
                                            "PermError, so SPF does not evaluate at all"})
        if s["policy"] == "pass":
            out["issues"].append({"id": "spf_permissive", "sev": "HIGH",
                                  "detail": "SPF ends in +all — every sender on the internet is "
                                            "explicitly authorised for this domain"})
        elif s["policy"] in ("neutral", "none"):
            out["issues"].append({"id": "spf_no_enforcement", "sev": "MEDIUM",
                                  "detail": "SPF ends in %s — it expresses no opinion on an "
                                            "unlisted sender" % (s.get("all") or "no all mechanism")})
        elif s["policy"] == "softfail":
            out["context"].append("SPF ends in ~all (softfail): mail from unlisted senders is "
                                  "accepted and marked, not rejected")
        if s["lookups"] > 10:
            out["issues"].append({"id": "spf_too_many_lookups", "sev": "MEDIUM",
                                  "detail": "SPF needs about %d DNS lookups; RFC 7208 §4.6.4 caps "
                                            "it at 10 and a receiver MUST PermError beyond that"
                                            % s["lookups"]})

    if out["mta_sts"] is False:
        out["context"].append("No MTA-STS policy — mail to this domain can be downgraded to "
                              "cleartext by an attacker on the path")

    # ---- DKIM. PRESENCE ONLY, and the wording says so. See the module header for why claiming
    # absence here would be a false accusation.
    found = []
    for sel in DKIM_SELECTORS:
        recs = look("%s._domainkey.%s" % (sel, domain))
        if recs:
            if any("v=dkim1" in r.lower().replace(" ", "") or "p=" in r.lower() for r in recs):
                found.append(sel)
        if len(found) >= 3:
            break
    out["dkim_selectors"] = found
    out["context"].append(
        "DKIM selectors observed: %s" % (", ".join(found)) if found else
        "No DKIM key found on the common selectors — this is NOT evidence of absence, because a "
        "selector name is arbitrary and cannot be enumerated")
    return out
