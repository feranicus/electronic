"""client_truth.py -- does the client's OWN behaviour agree with the client's OWN claim?

LABELLING ONLY. Nothing in this file blocks, tarpits, rate-limits, scores an address, proposes a
rule or reaches a firewall, and `tests/test_client_truth.py` asserts each of those as a property
rather than as a grep for a word. It reads one already-written `evt=http` record and returns a list
of reasons; a caller can do nothing else with it.

WHY IT EXISTS. Until now the estate's ONLY bot signal was `telemetry.classify_ua()`, a substring
match on the User-Agent. The doctrine this repository already writes down says a user agent is
attacker-controlled and the PATH is the evidence -- and then the fleet page counted `len(set(ip))`
over every `evt=http` line and called the answer VISITORS, so one `curl` was one visitor.

THE IDEA, AND IT IS THE WHOLE IDEA: a claim is evidence only when CONTRADICTING it costs the
attacker something. Sending `User-Agent: Mozilla/5.0 ... Chrome/131` costs nothing. Making a
Python or Go HTTP client actually emit the fetch-metadata header set a Chromium browser emits, or
actually negotiate HTTP/2, costs real work. So the claim is compared against two things that are
not free to fake.

CONSERVATIVE BY CONSTRUCTION, because the cost of being wrong here is a real customer counted as a
scanner on the operator's own dashboard:
  * Anything we cannot measure is NOT DETERMINABLE. Absence of evidence is never a finding.
  * A contradiction is ONE WEAK SIGNAL. It is never a conviction, and it never becomes enforcement.
  * A client that identifies itself honestly (curl, wget, Googlebot) is already `bot: true` from
    `classify_ua()`. This module returns nothing for it, so it is never counted twice.
  * `/api/` and `/.well-known/` are exempt from everything here, as they are everywhere else in
    this estate: every deploy verifier fetches `/api/me` with curl and asserts 401.
  * Every exception resolves to "no reasons, not determinable". Fail open, always.

VENDORABLE. Standard library only, no relative import, no package assumption, so a sibling project
can copy this file next to its own code and get the identical verdict from the identical evidence.
`perseus/client.py` may NOT import it -- that file's import floor is asserted to be exactly seven
stdlib modules -- so the client restates the four `SF_*` bit values, and
`test_client_truth.py::test_the_sidecar_and_this_module_agree_on_the_bitmask` reads
`perseus/client.py` OFF DISK with `ast` and fails if the two ever drift. Same pattern the shield's
detection table already uses; a value with two homes needs a test that makes them one.
"""
import re

# ---------------------------------------------------------------------------------------------
# THE `sf` BITMASK -- WHICH FETCH-METADATA HEADERS WERE PRESENT, NEVER WHAT THEY SAID.
#
# Only PRESENCE is recorded. The values are useless to us and carry navigation context we have no
# business keeping in Loki for 24h next to an IP address (these lines are personal data; see the
# privacy note at the top of telemetry.py). Four bits fit in one digit and these lines are written
# on every request.
#
# `sf` ABSENT and `sf == 0` ARE DIFFERENT FACTS. Absent means the line predates this change, or was
# written by a project that has not redeployed -- we never looked. Zero means we looked and the
# client sent none of them, which is the signal. Collapsing the two would be exactly the confident
# wrong number the fleet page exists to prevent.
# ---------------------------------------------------------------------------------------------
SF_SITE = 1          # sec-fetch-site
SF_MODE = 2          # sec-fetch-mode
SF_DEST = 4          # sec-fetch-dest
SF_CHUA = 8          # sec-ch-ua

# The three FETCH METADATA headers proper (RFC draft / W3C Fetch Metadata). A browser that supports
# them sends all three on a navigation. sec-ch-ua is deliberately NOT in this mask: it is a Client
# Hint, Chromium-only, and Firefox and Safari never send it -- requiring it would flag every Firefox
# user on the estate. It is recorded as a fourth bit because it is free to record and it is a
# positive corroboration when present, never a requirement.
FETCH_METADATA_BITS = SF_SITE | SF_MODE | SF_DEST

_SF_HEADERS = (
    ("sec-fetch-site", SF_SITE),
    ("sec-fetch-mode", SF_MODE),
    ("sec-fetch-dest", SF_DEST),
    ("sec-ch-ua", SF_CHUA),
)

# ---------------------------------------------------------------------------------------------
# WHOSE HTTP VERSION IS `hv`? THE FIELD IS USELESS UNTIL THAT QUESTION IS ANSWERED.
#
# THE MEASUREMENT THAT DECIDED THIS. Every public site in this estate sits behind ONE shared Caddy
# (`videodead-caddy-1`) which terminates TLS and reverse-proxies to the application over a fresh
# upstream connection. uvicorn does not implement HTTP/2 at all. So `scope["http_version"]` inside
# colt-web describes the PROXY-TO-APP hop and is "1.1" for a Chrome user, a Firefox user and a Go
# program alike. A check built on it would fire on 100% of real browsers -- a check that cannot
# fail in the other direction, which is the same defect one sign over.
#
# So the record carries the version AND ITS SUBJECT, and the contradiction below arms itself only
# when the subject is the CLIENT. Today that means it is dormant in production and says so. It
# becomes live the moment the shared Caddy block gains
#
#     header_up X-Client-Proto {http.request.proto}
#
# which is a one-line proxy change the operator can make when he wants it, with no code change --
# and until he does, this module reports "not determinable" instead of inventing a verdict.
# ---------------------------------------------------------------------------------------------
HV_FROM_CLIENT = "p"     # a proxy that saw the client told us (X-Client-Proto)
HV_FROM_HOP    = "s"     # the ASGI scope: the last hop only, says NOTHING about the client
HV_CLIENT_HEADER = "x-client-proto"

# HTTP/2 has been shipping in every one of these engines for a decade (Chrome 41, Firefox 36,
# Safari 9, Edge always), and Caddy offers h2 in its ALPN list on every one of our vhosts. A client
# claiming one of these engines at a version at or above the floor below, that then speaks HTTP/1.1
# to a TLS endpoint offering h2, is contradicting itself. The floor is set far higher than the
# engine versions that first shipped h2 on purpose: a spoofed UA claims a CURRENT browser, and the
# gap buys room for anything genuinely old, embedded, or behind a downgrading middlebox.
H2_EXPECTED_SINCE = {"chrome": 76, "edge": 79, "opera": 63, "firefox": 90, "safari": (16, 4)}

# FETCH METADATA, per engine, with the release it shipped in:
#   Chrome 76 (Aug 2019) / Edge 79 (Jan 2020, first Chromium Edge) / Opera 63 (Chromium 76)
#   Firefox 90 (Jul 2021) / Safari 16.4 (Mar 2023, the late one -- and the reason Safari has its
#   own floor rather than sharing a single number).
# A client claiming a version AT OR ABOVE its engine's floor and sending NONE of the three is
# contradicting itself. Below the floor we say nothing at all, because the browser genuinely did
# not send them.
FETCH_METADATA_SINCE = {"chrome": 76, "edge": 79, "opera": 63, "firefox": 90, "safari": (16, 4)}

# THE ENUM KEYS. Never translated, never composed, never parsed for substrings by a caller -- the
# estate has already paid for a translated lookup key making rows vanish. A label is chosen at
# render time from these.
REASON_HTTP11 = "claims_h2_browser_but_spoke_http11"
REASON_NO_FETCH_METADATA = "claims_modern_browser_but_sent_no_fetch_metadata"

# Exempt from EVERYTHING here, the same two prefixes visitors.py exempts from the bot gate, for the
# same reason: every deploy verifier in this repo proves the site is live by fetching `/api/me`
# with curl or urllib and asserting 401, and ACME needs /.well-known. Restated rather than imported
# because this file must stay vendorable into a project that has no visitors.py; the equality is
# asserted by test_client_truth.py so the two cannot drift.
EXEMPT_PREFIXES = ("/api/", "/.well-known/")

_RE_EDGE    = re.compile(r"\bedg/(\d+)", re.I)          # Chromium Edge ONLY. Legacy `Edge/18` is
                                                        # EdgeHTML, sends no fetch metadata, and is
                                                        # deliberately unmatched -> no verdict.
_RE_OPERA   = re.compile(r"\bopr/(\d+)", re.I)
_RE_CHROME  = re.compile(r"\b(?:chrome|crios)/(\d+)", re.I)
_RE_FIREFOX = re.compile(r"\b(?:firefox|fxios)/(\d+)", re.I)
_RE_SAFARI_V = re.compile(r"\bversion/(\d+)\.(\d+)", re.I)
_RE_SAFARI_TOKEN = re.compile(r"\bsafari/", re.I)
# Automation that carries a browser UA on purpose. `classify_ua()` already marks these `bot: true`,
# so they normally never reach the comparison below -- this is belt and braces for a caller that
# hands us a record with no `bot` field at all.
_RE_AUTOMATION = re.compile(r"headless|phantomjs|electron/|puppeteer|playwright|selenium", re.I)


class Verdict(object):
    """WHAT THIS MODULE IS ALLOWED TO SAY, AND IT IS ALL IT CAN SAY.

    Two fields, and neither of them is a decision. There is deliberately no `block`, no `action`,
    no `verdict`, no severity and no score: a caller that wanted to enforce on this would have to
    invent the decision itself, in its own file, where a reviewer can see it. `__slots__` means a
    caller cannot bolt one on at runtime either.

      reasons       tuple of REASON_* enum keys. Empty is the normal case and means "nothing
                    contradicted itself", which is NOT the same as "this is a human".
      determinable  False when the record did not carry the fields to look at. A caller must render
                    that as UNKNOWN; counting it as either a visitor or a bot is the confident
                    wrong number.
    """
    __slots__ = ("reasons", "determinable")

    def __init__(self, reasons=(), determinable=False):
        self.reasons = tuple(reasons)
        self.determinable = bool(determinable)

    def as_dict(self):
        return {"reasons": list(self.reasons), "determinable": self.determinable}

    def __repr__(self):
        return "Verdict(reasons=%r, determinable=%r)" % (self.reasons, self.determinable)


def sf_mask(get_header):
    """-> int bitmask of which fetch-metadata headers were PRESENT. Never raises.

    `get_header` is any callable taking a lower-case header name and returning the value or None,
    which is what both emitters already have to hand (Starlette's `request.headers.get` and the
    sidecar's own decoded dict). Presence only: an empty-string value still counts as sent, because
    the client sent the header.
    """
    mask = 0
    try:
        for name, bit in _SF_HEADERS:
            if get_header(name) is not None:
                mask |= bit
    except Exception:
        return 0
    return mask


def claimed_engine(ua):
    """-> (engine, version) for a UA claiming a mainstream browser, else None. Never raises.

    ORDER IS THE WHOLE FUNCTION. Edge's UA contains `Chrome/`, Opera's contains both, and iOS
    Chrome calls itself `CriOS`. Matching `Chrome/` first would file every Edge user as Chrome and
    compare them against the wrong floor.

    `version` is an int for the Chromium family and Firefox, and a (major, minor) tuple for Safari,
    because Safari's fetch-metadata support arrives at 16.4 and "16" is not enough to decide.
    Unparseable, absent, or automation-shaped -> None, and None means this module says nothing.
    """
    try:
        u = ua or ""
        if not u.strip() or _RE_AUTOMATION.search(u):
            return None
        m = _RE_EDGE.search(u)
        if m:
            return ("edge", int(m.group(1)))
        m = _RE_OPERA.search(u)
        if m:
            return ("opera", int(m.group(1)))
        m = _RE_CHROME.search(u)
        if m:
            return ("chrome", int(m.group(1)))
        m = _RE_FIREFOX.search(u)
        if m:
            return ("firefox", int(m.group(1)))
        if _RE_SAFARI_TOKEN.search(u):
            m = _RE_SAFARI_V.search(u)
            if m:
                return ("safari", (int(m.group(1)), int(m.group(2))))
        return None
    except Exception:
        return None


def _at_least(version, floor):
    """True when a parsed version is at or above its engine's floor. Shapes must match or we say no."""
    try:
        if isinstance(floor, tuple):
            return isinstance(version, tuple) and version >= floor
        return (not isinstance(version, tuple)) and version >= floor
    except Exception:
        return False


def exempt(path):
    """The two prefixes nothing in this estate is allowed to judge. Never raises."""
    try:
        return str(path or "/").startswith(EXEMPT_PREFIXES)
    except Exception:
        return True                      # cannot tell -> treat as exempt. One safe direction.


def has_evidence(ev):
    """True when this record carries the fields this module reads.

    BOTH, not either. A line written before this change shipped, and a line from a sibling project
    that has not redeployed, carry neither -- and a caller must be able to tell "we looked and found
    nothing" apart from "we never looked". This is the predicate the fleet page uses to decide
    whether a row can support the visitors/clients split at all.
    """
    try:
        return "hv" in ev and "sf" in ev
    except Exception:
        return False


def evaluate(ev):
    """-> Verdict. Reads ONE `evt=http` record. Never raises, never enforces, never persists.

    The record is the one both `telemetry._safe_emit` and `perseus.client.observe` write, so the
    same arithmetic runs over cybergod's own lines and over a sibling project's lines read from
    Loki, and neither gets a different answer for the same evidence.
    """
    try:
        if not isinstance(ev, dict):
            return Verdict()
        if exempt(ev.get("path")):
            return Verdict()
        # ALREADY COUNTED, ONCE. A client that says `curl/8.5` or `Googlebot` is honest about what
        # it is; classify_ua has already filed it and the caller has already put it in the bot
        # column. Adding a contradiction on top would double-count one address in one column.
        if ev.get("bot"):
            return Verdict()
        if not has_evidence(ev):
            return Verdict()

        engine = claimed_engine(ev.get("ua"))
        if engine is None:
            # No mainstream-browser claim to contradict. A caller still has `bot` from classify_ua;
            # this module has nothing to add and says so rather than guessing.
            return Verdict(determinable=True)
        name, version = engine
        reasons = []

        # ---- 1. FETCH METADATA. The live signal, and the only one that can fire today. ----------
        # Sec-Fetch-* are forwarded verbatim by the shared proxy, so unlike the protocol version
        # this IS a fact about the client. A browser at or above its engine's floor sends all three
        # on a navigation; sending none of them while claiming that browser is the contradiction.
        # `sf` is read as an int: a malformed value is treated as "we did not measure".
        try:
            sf = int(ev.get("sf"))
        except Exception:
            sf = None
        if sf is not None and _at_least(version, FETCH_METADATA_SINCE.get(name, 10 ** 9)):
            if not (sf & FETCH_METADATA_BITS):
                reasons.append(REASON_NO_FETCH_METADATA)

        # ---- 2. PROTOCOL VERSION. Dormant until the proxy forwards the CLIENT's version. --------
        # See the HV_* block at the top: `hv` taken from the ASGI scope describes the proxy-to-app
        # hop, is "1.1" for every visitor including real browsers, and must never convict anybody.
        # The check arms itself only for a record whose `hvs` says a proxy reported what the CLIENT
        # spoke. This is why it is a named source field and not a bare version string.
        if ev.get("hvs") == HV_FROM_CLIENT:
            hv = str(ev.get("hv") or "").strip().lower()
            # Normalise `HTTP/1.1` and `1.1` to the same thing; anything we do not recognise is left
            # alone rather than guessed at.
            hv = hv[5:] if hv.startswith("http/") else hv
            if hv in ("1.0", "1.1") and _at_least(version, H2_EXPECTED_SINCE.get(name, 10 ** 9)):
                reasons.append(REASON_HTTP11)

        return Verdict(reasons=reasons, determinable=True)
    except Exception:
        # FAIL OPEN. An error here is not evidence about the client; it is evidence about us.
        return Verdict()
