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


# =================================================================================================
# ON-PREMISES EXCHANGE, AND THE NAMES NO CERTIFICATE COVERS.
#
# Both were missed on ns03.ru and both are visible in data the run ALREADY held. The operator's own
# browser found an Outlook Web Access sign-in page on the raw address, over a certificate the
# browser rejected, and the engine said nothing at all -- because Shodan has no record for that
# host and every Exchange detector we had reads a scan-engine banner.
# =================================================================================================
_EXCHANGE_NAMES = ("autodiscover", "owa", "ews", "mail", "exchange", "webmail", "outlook")


def onprem_exchange(resolved, apexes, cert_names=(), is_saas=None, mx_hosts=()):
    """Evidence of a self-hosted Exchange estate, from DNS and certificates only.

    THE DISCRIMINATOR IS AUTODISCOVER. It is an Exchange-specific service name, and where a company
    uses Microsoft 365 it CNAMEs into Microsoft's platform. When it resolves instead to an address
    the customer owns, the mail platform is on-premises and its web endpoints are internet-facing.

    WHY THIS IS CRITICAL RATHER THAN INFORMATIONAL, and the dates are the argument:
      · Exchange Server 2016 and 2019 reached end of support on 14 October 2025.
      · The one-time Extended Security Update option ran out on 14 April 2026.
    So a 2016 or 2019 installation running today has NO security updates available at any price.
    Its OWA, EWS, Autodiscover and MAPI endpoints are also the most consistently attacked surface
    in the enterprise estate.

    FAILS CLOSED. A name that CNAMEs into Microsoft 365 is a tenancy, not a server, and produces
    nothing. `is_saas` is injected so this module never touches the network.
    """
    saas = is_saas or (lambda n: False)
    hits, evidence = {}, []
    certset = {str(c).lower().lstrip("*.") for c in (cert_names or [])}
    for name in sorted(resolved or {}):
        n = str(name).lower()
        if apexes and not any(n == a or n.endswith("." + a) for a in apexes):
            continue
        label = n.split(".")[0]
        if label not in _EXCHANGE_NAMES:
            continue
        if saas(n):                                  # Microsoft 365 tenancy -> not a server
            continue
        hits[label] = sorted(resolved[name])
        evidence.append("%s -> %s" % (n, ", ".join(sorted(resolved[name])[:3])))

    # AUTODISCOVER IS THE ANCHOR. `mail` alone is a generic name that any provider uses; without
    # autodiscover on the customer's own address this is not evidence of Exchange specifically.
    if "autodiscover" not in hits:
        return None

    corroboration = []
    if certset & {"autodiscover." + a for a in (apexes or [])}:
        corroboration.append("a certificate the organisation requested names autodiscover")
    for extra in ("mail", "owa", "ews", "webmail", "exchange"):
        if extra in hits:
            corroboration.append("%s resolves to the same estate" % extra)
            break
    for m in (mx_hosts or []):
        if any(str(m).lower().rstrip(".") == k or str(m).lower().rstrip(".").startswith(k + ".")
               for k in ("mail", "owa", "exchange")):
            corroboration.append("the domain's MX points at the same host")
            break
    if not corroboration:
        return None                                  # autodiscover alone is not enough

    return {"names": hits, "evidence": evidence[:6], "corroboration": corroboration,
            "addresses": sorted({ip for v in hits.values() for ip in v})[:6]}


def uncovered_names(resolved, issuances, apexes=()):
    """Live hostnames that NO unexpired certificate covers.

    Every visitor to such a name gets a browser trust warning, which is a real operational finding
    twice over: the service is unusable to a cautious user, and an organisation whose staff are
    trained to click through certificate warnings has lost the control that certificates provide.
    The operator's own screenshot of this estate shows exactly that: a sign-in page served on an
    address the browser marks Not secure.

    FAILS CLOSED: with no issuances at all the CT lookup failed or returned nothing, and absence of
    evidence is never a finding.
    """
    if not issuances:
        return []
    covered, wildcards = set(), set()
    for row in issuances:
        for n in _names(row):
            covered.add(n)
    for row in issuances:
        for raw in (row.get("dns_names") or []):
            r = str(raw).strip().lower()
            if r.startswith("*."):
                wildcards.add(r[2:])
    out = []
    for name in sorted(resolved or {}):
        n = str(name).lower()
        if apexes and not any(n == a or n.endswith("." + a) for a in apexes):
            continue
        if n in covered:
            continue
        parent = n.split(".", 1)[1] if "." in n else ""
        if parent in wildcards:                      # *.example.com covers vpn.example.com
            continue
        out.append({"name": n, "addresses": sorted(resolved[name])[:3]})
    return out
