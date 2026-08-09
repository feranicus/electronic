"""active_probe.py — the AUTHORISED tier. Sends packets to the customer. OFF by default.

=================================================================================================
READ THIS BEFORE ENABLING ANYTHING HERE
=================================================================================================
Every other check in this engine is passive: public logs, public DNS, a scan engine's existing
index. Nothing is sent to the assessed company, which is why cybergod needs no permission from
them, and why the product can honestly say so on the public site, in the Terms of Use, in the
Article 13 privacy notice and in the signed partner legal pack.

The techniques in this module BREAK THAT. A TLS handshake, an HTTP request, an application version
probe and an NTLM negotiation are all connections to the customer's own infrastructure.

WHAT THE LAW ACTUALLY TURNS ON. Not the jurisdiction, and not the technique: AUTHORISATION.
  · Germany   — §202a StGB (Ausspähen von Daten) and §202b (Abfangen von Daten) criminalise
                obtaining data not intended for you where access protection is overcome; §202c
                covers preparatory acts. Requesting a page a server publishes to the world is
                generally outside §202a, but probing an authentication endpoint is much closer to
                the line, and §303b (Computersabotage) covers anything that disrupts.
  · EU        — Directive 2013/40/EU frames the offence as access "without right". With the asset
                owner's authorisation there is a right; without it there may not be.
  · USA       — CFAA 18 U.S.C. §1030, "without authorization or exceeding authorized access".
                Van Buren (2021) narrowed it to a gates-up-or-down question, and requesting a
                public page is generally not an offence, but an authentication endpoint is a gate.
  · Canada    — Criminal Code s.342.1 (unauthorized use of a computer) and s.430(1.1) (mischief in
                relation to computer data).
With written authorisation from the party that controls the asset, all of this is lawful in all
four jurisdictions. Without it, the answer ranges from "grey" to "criminal offence" depending on
which endpoint is touched, and no amount of care in the code changes that.

THIS IS NOT LEGAL ADVICE. It is the reason the gate below exists and refuses to open by itself.

=================================================================================================
THE GATE
=================================================================================================
`enabled()` returns True only when BOTH are present:
    ACTIVE_PROBE=1
    ACTIVE_PROBE_AUTH="<a reference to the written authorisation>"
The reference is recorded in the run's own evidence and printed into the artifact, so a deck built
from active data always carries the authority it was collected under. A boolean flag on its own is
not enough: somebody must have written down who authorised it.

Rate limits are deliberate and low. This tier reads banners; it never enumerates, never
authenticates, never sends a credential, and never touches anything that could disrupt a service.
"""
import os
import re
import socket
import ssl

DEFAULT_DELAY = float(os.environ.get("ACTIVE_PROBE_DELAY", "3.0"))
DEFAULT_TIMEOUT = float(os.environ.get("ACTIVE_PROBE_TIMEOUT", "10.0"))


def authorisation():
    """The recorded written-authorisation reference, or "" if none was supplied."""
    return str(os.environ.get("ACTIVE_PROBE_AUTH", "")).strip()


def enabled():
    """True only with the flag AND a recorded authorisation reference.

    Deliberately NOT a single boolean. A flag says somebody wanted this; a reference says somebody
    is accountable for it, and that is the thing a court, a customer or an insurer would ask for.
    """
    return os.environ.get("ACTIVE_PROBE", "").strip() in ("1", "true", "yes") and bool(authorisation())


def status():
    """Why the tier is or is not running, in words fit for the run log and the artifact."""
    if enabled():
        return {"active": True, "authorisation": authorisation(),
                "note": "Active probing ENABLED under recorded authorisation %s. Findings in this "
                        "run may include data obtained by connecting to the assessed "
                        "organisation's systems." % authorisation()}
    if os.environ.get("ACTIVE_PROBE", "").strip() in ("1", "true", "yes"):
        return {"active": False, "authorisation": "",
                "note": "Active probing was requested but REFUSED: no ACTIVE_PROBE_AUTH reference "
                        "was recorded. Set it to the written authorisation you hold."}
    return {"active": False, "authorisation": "",
            "note": "Passive assessment: not one packet was sent to the assessed organisation."}


# =================================================================================================
# Version -> support-status mapping. THIS HALF IS PASSIVE and is the point of the module.
#
# The ns03.ru run read an OWA build path of 15.2.1748 and turned it into "Exchange 2019 CU15, end
# of support 2025-10-14". Reading it from the customer's server needs the active tier -- but the
# SAME string frequently appears in a scan engine's stored banner, which we already hold. So the
# MAPPING is exposed separately and runs on passive data whenever the banner contains a version.
# =================================================================================================
EXCHANGE_BUILDS = {
    "15.2.1748": ("Exchange Server 2019 CU15", "2025-10-14"),
    "15.2.1544": ("Exchange Server 2019 CU14", "2025-10-14"),
    "15.2.1258": ("Exchange Server 2019 CU12", "2025-10-14"),
    "15.1.2507": ("Exchange Server 2016 CU23", "2025-10-14"),
    "15.0.1497": ("Exchange Server 2013 CU23", "2023-04-11"),
}


def exchange_from_build(build):
    """Map an OWA build path to a product and its end-of-support date.

    THE HONESTY CONSTRAINT, taken from the source engagement and worth keeping verbatim: OWA
    exposes major.minor.build only. The security-update REVISION is not externally determinable, so
    the finding must name the cumulative update, never a patch level. Claiming a host is missing a
    specific security update from this data would be an unsupportable assertion in a customer deck.
    """
    b = str(build or "").strip()
    m = re.match(r"^(\d+\.\d+\.\d+)", b)
    if not m:
        return None
    key = m.group(1)
    if key not in EXCHANGE_BUILDS:
        return None
    name, eos = EXCHANGE_BUILDS[key]
    return {"product": name, "end_of_support": eos, "build": key,
            "caveat": "Build path gives major.minor.build only; the security-update revision is "
                      "not externally determinable. This identifies the cumulative update, not a "
                      "patch level."}


def eol_from_banner(text):
    """Find a version string in data we ALREADY hold and map it to a support status.

    Passive by construction: `text` comes from a scan engine's stored record, not from a connection
    we made. This is how the highest-value half of the active playbook is delivered without sending
    a packet.
    """
    t = str(text or "")
    m = re.search(r"/owa/auth/(\d+\.\d+\.\d+)", t) or re.search(r"\b(15\.[012]\.\d{3,4})\b", t)
    if m:
        return exchange_from_build(m.group(1))
    return None


# =================================================================================================
# The active checks themselves. Each one asserts the gate first and returns a refusal otherwise.
# =================================================================================================
def _refused(what):
    return {"ok": False, "refused": True, "check": what, "reason": status()["note"]}


def tls_certificate(host, ip=None, port=443, timeout=None):
    """Read the certificate a host serves for a given SNI name.

    WHY IT MATTERS AND WHY IT IS ACTIVE: on SNI-only shared hosting a scan engine sees whatever
    hostname it happened to know, which is frequently a co-tenant's. The customer's own virtual
    host is structurally invisible to it. A handshake with the correct SNI is the only way to read
    the certificate that is actually served -- and it is a connection to their server.
    """
    if not enabled():
        return _refused("tls_certificate")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with socket.create_connection((ip or host, port), timeout=timeout or DEFAULT_TIMEOUT) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ss:
                cert = ss.getpeercert()
                return {"ok": True, "host": host, "ip": ip or host, "tls": ss.version(),
                        "cipher": (ss.cipher() or [None])[0], "cert": cert,
                        "authorisation": authorisation()}
    except Exception as e:
        # A FAILURE IS DATA. "unrecognized name" means the host does not serve this virtual host at
        # all, which is evidence about stale DNS; a timeout means something is filtering. Recording
        # the reason is what makes a negative finding reportable.
        return {"ok": False, "host": host, "ip": ip or host,
                "error": "%s: %s" % (type(e).__name__, e), "authorisation": authorisation()}
