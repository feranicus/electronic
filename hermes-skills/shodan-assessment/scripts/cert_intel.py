"""cert_intel.py — what a certificate estate reveals, from Certificate Transparency alone.

PURE ANALYSIS. Every function here takes the issuance records `shodan_recon._certspotter_issuances`
already fetched and returns findings. No network, no packets to the target, fully testable.

WHY CT IS THE HIGHEST-YIELD SOURCE, and this is the transferable lesson from the ns03.ru engagement
where Shodan returned nothing across twelve query families:
  · it cannot be blocked — logging is mandatory for a publicly-trusted certificate, so the record
    exists whether or not the host answers a scanner;
  · it records INTENT, not reachability — a name appears the moment somebody requested a
    certificate for it, including hosts behind SNI-only front ends that no scanner can see;
  · it leaks organisational structure — site codes, branch names and internal roles, in the
    customer's own vocabulary.

THE RULES THIS MODULE OBEYS:
  · A finding must be about a name the customer still USES. A revoked certificate for a name that
    no longer resolves is history, not exposure, so every check is joined against resolution.
  · The CertSpotter issuances endpoint returns only UNEXPIRED certificates. Nothing may be claimed
    here about historic or already-expired issuance.
  · `revoked` is nullable. null means the revocation status is UNKNOWN (an expired certificate, a
    CA that publishes no usable CRL); it does not mean "not revoked". Only an explicit True counts.
"""
import datetime
import re


def _dt(s):
    """RFC 3339 -> datetime, or None. CT timestamps are always Z-suffixed UTC."""
    try:
        return datetime.datetime.strptime(str(s)[:19], "%Y-%m-%dT%H:%M:%S")
    except Exception:
        return None


def _names(row):
    return sorted({str(n).strip().lower().lstrip("*.").rstrip(".")
                   for n in (row.get("dns_names") or []) if n})


def revoked_live(issuances, resolves):
    """Certificates the CA has REVOKED, for names that still resolve.

    Revocation is an assertion by the issuing authority that this certificate must no longer be
    trusted — most often because a key was compromised, a service was decommissioned, or a
    certificate was mis-issued. A revoked certificate on a name that is still live is therefore one
    of two things, and both are worth the customer's attention: a service that was retired without
    its DNS being cleaned up, or a key incident nobody closed out.

    `resolves` is a callable or a set: the caller supplies which names still answer, because THIS
    module never touches the network.
    """
    live = resolves if callable(resolves) else (lambda n: n in set(resolves or ()))
    out = []
    for row in issuances or []:
        if row.get("revoked") is not True:      # null = unknown, never treat as revoked
            continue
        names = [n for n in _names(row) if live(n)]
        if names:
            out.append({"names": names,
                        "issuer": str((row.get("issuer") or {}).get("friendly_name") or "unknown"),
                        "not_after": str(row.get("not_after") or "")})
    return out


def expiring(issuances, resolves, days=21, now=None):
    """Unexpired certificates about to lapse, on names that still resolve.

    A lapse is a total outage of that service for every visitor at once, and it arrives on a known
    date. Deliberately NOT a finding at 60 or 90 days: a 90-day ACME certificate is renewed at 30
    by design, so a wide threshold would flag correct automation as a weakness on every run.
    """
    live = resolves if callable(resolves) else (lambda n: n in set(resolves or ()))
    now = now or datetime.datetime.utcnow()
    best = {}
    for row in issuances or []:
        na = _dt(row.get("not_after"))
        if not na:
            continue
        for n in _names(row):
            if not live(n):
                continue
            # A name usually has several overlapping certificates. Only the LATEST expiry matters:
            # flagging the older one would report an outage that renewal has already prevented.
            if n not in best or na > best[n][0]:
                best[n] = (na, row)
    out = []
    for n, (na, row) in sorted(best.items()):
        left = (na - now).days
        if left <= days:
            out.append({"name": n, "days": left, "not_after": str(row.get("not_after") or ""),
                        "issuer": str((row.get("issuer") or {}).get("friendly_name") or "unknown")})
    return out


def shared_blast(issuances, resolves, min_names=3):
    """One certificate covering several distinct services: one private key, N services.

    On ns03.ru a single certificate carried the corporate gateway, the mail server, Exchange
    autodiscover and a site gateway. That is not a misconfiguration in itself, but it concentrates
    risk: compromise of that one key, or a botched renewal of that one certificate, takes every one
    of those services down or impersonates all of them together. It also means the private key must
    be present on every host that serves any of those names.
    """
    live = resolves if callable(resolves) else (lambda n: n in set(resolves or ()))
    out = []
    for row in issuances or []:
        names = [n for n in _names(row) if live(n)]
        if len(names) >= min_names:
            out.append({"names": names, "count": len(names),
                        "issuer": str((row.get("issuer") or {}).get("friendly_name") or "unknown"),
                        "not_after": str(row.get("not_after") or "")})
    # The same SAN set is reissued at every renewal; report the estate shape once, not per renewal.
    seen, uniq = set(), []
    for o in sorted(out, key=lambda x: -x["count"]):
        k = tuple(o["names"])
        if k not in seen:
            seen.add(k)
            uniq.append(o)
    return uniq


def ca_profile(issuances):
    """How the estate is managed, read from certificate lifetime and issuer.

    A 90-day certificate is ACME automation. A ~13-month one is a commercial CA renewed by hand.
    Both present on one domain means two different teams, or two eras of practice, on the same
    estate — which is exactly where the forgotten host lives. Reported as CONTEXT for the analyst,
    never as a finding: neither pattern is a weakness on its own.
    """
    prof = {"acme": 0, "commercial": 0, "issuers": {}, "mixed": False}
    for row in issuances or []:
        nb, na = _dt(row.get("not_before")), _dt(row.get("not_after"))
        iss = str((row.get("issuer") or {}).get("friendly_name") or "unknown")
        prof["issuers"][iss] = prof["issuers"].get(iss, 0) + 1
        if not (nb and na):
            continue
        span = (na - nb).days
        if span <= 100:
            prof["acme"] += 1
        elif span >= 300:
            prof["commercial"] += 1
    prof["mixed"] = prof["acme"] > 0 and prof["commercial"] > 0
    prof["issuers"] = sorted(prof["issuers"], key=lambda k: -prof["issuers"][k])
    return prof


def internal_names(issuances, apexes):
    """Hostnames in CT that look like internal infrastructure rather than a public service.

    A certificate request publishes the name FOREVER, so an estate's internal naming — site codes,
    server roles, branch abbreviations — ends up in a public log. This is context for the analyst
    and the input to naming.py, not a finding by itself.
    """
    pat = re.compile(r"^(srv|vm|host|node|sv)[-.]|"
                     r"(^|\.)(dc\d?|sql|db|bck|bak|test|dev|staging|uat|int|intranet|adfs|ca)(\.|$)")
    out = set()
    for row in issuances or []:
        for n in _names(row):
            if any(n.endswith("." + a) or n == a for a in (apexes or [])) and pat.search(n):
                out.add(n)
    return sorted(out)
