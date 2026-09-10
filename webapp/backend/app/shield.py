"""shield.py — ACTIVE defence for cybergod.ai. Deterministic, inline, and safe on a shared host.

THE INCIDENT THAT PRODUCED IT (10 Aug 2026, 19:05:55-57 UTC). One IP, 195.178.110.199, produced
SIX "a person just opened cybergod.ai" alerts inside two seconds while announcing six different
browsers -- Safari/macOS, Chrome/Linux, Chrome/macOS, Edge/Windows, Firefox/Windows, Firefox/macOS
-- and asked for //slug, /[workspace]/, /DOCS.md and /IAM.md. No human has six browsers, and those
paths are template placeholders from a leaked-documentation scanner. The dirbruteforce rule fired
correctly, and then the platform did nothing about it and mailed the operator six times.

WHY THE MODELS ARE NOT IN THIS FILE, and this is a design decision, not an omission:
  · a model call is 300ms to 60s. Putting one in the request path IS a denial of service, and the
    panel's own failure modes (429, timeout) would become site outages;
  · operating principle 5 -- the LLM assists, it does not decide side effects -- is the product's
    own public claim. Code decides; the panel reviews out of band (shield_panel.py) and its
    proposals reach production the same way every other change does: through `python ship.py`.

WHY THIS IS SAFE ON THIS HOST, which is the whole reason it can exist at all:
  · Amnezia VPN (UDP), SSH (tcp/22) and the other sites' traffic NEVER pass through this process.
    Enforcement is HTTP-layer, inside colt-web only. There is no iptables, ufw or nft call in this
    file and a test asserts there never will be. The standing rule was "detection only, because we
    do not touch the firewall" -- the firewall was always the objection, not the blocking.
  · every decision is TIME-BOXED and expires by itself. Nothing here is permanent.
  · FAIL-OPEN: any exception anywhere in this module lets the request through. A security control
    that breaks the site is a worse outage than the scanning it prevents.
  · a GLOBAL BLAST CAP refuses to block when it would affect too much of the traffic -- the same
    doctrine as the co-tenant guard and the FP auditor: an automatic process may narrow, never wipe.

STANDARDS THIS IMPLEMENTS (named because a customer will ask):
  NIST SP 800-53r5 SI-4 (system monitoring), SI-10 (input validation), SC-5 (denial-of-service
  protection), AC-7 (unsuccessful logon attempts); NIST SP 800-63B 5.2.2 (throttling);
  OWASP ASVS v4 14.6 / OWASP Automated Threat Handbook OAT-011 (scraping), OAT-014 (vuln scanning);
  CISA "Bad Practices" -- default-deny on management surfaces. MITRE ATT&CK T1595.001/.003
  (active scanning, wordlist), T1110.001 (password guessing).
"""
import os
import re
import time

try:
    from . import notify
except Exception:                                        # pragma: no cover - import guard
    notify = None

# ------------------------------------------------------------------ THE SHARED DETECTION TABLE
# THE PROBE REGEX, THE CLASS VOCABULARY AND THE ROUTE/ASSET SHAPES USED TO LIVE IN THIS FILE.
# They moved to perseus/client.py on 2026-09-10, unchanged, and this file imports them.
#
# WHY: this file is not copied anywhere. perseus/client.py is copied into all five projects, so as
# long as the table lived here, jobhuntwow, jev.best, klimaanlage-preise.de and s4biz.io could not
# see a single one of these rules -- they ran a pattern-list lookup against a list the hub had
# never published, and blocked nothing for their entire lives. Moving the table to the file that
# IS copied is what makes one implementation reachable from five request paths. There is no second
# copy to drift, because there is no second SOURCE: whichever of the three locations below is
# resolved, its bytes came from perseus/client.py, and tests/test_perseus_shield.py asserts the
# pattern this module ended up with is the pattern that file defines -- comparing the compiled
# objects, not two comments claiming to agree.
#
# WHAT STAYED HERE is everything that is cybergod's alone and cannot be copied: OUR_TOP / OUR_APP /
# OUR_EXACT (this application's route list), EXTRA_PROBE_PATHS (its operator console), the
# disk-backed slow_store, the Telegram escalation, and the /24 rule that needs both.
#
# THE IMPORT ADDS NO NEW FAILURE DOMAIN: main.py already does `from . import perseus_client` to
# install the middleware, so colt-web has depended on that file being present since the sidecar was
# wired. And if every candidate below fails we run with detection OFF and SAY SO -- DETECTION,
# a printed line, and state()["detection"] -- rather than raise at import and take the site down.
# A control that is off must never look like a control that found nothing.
#
# THE TABLE IS RESOLVED, NOT ASSUMED, AND THE RESOLUTION NAMES ITSELF IN state()["detection"].
#
# There is ONE source file, perseus/client.py, and three places it can legitimately be found from
# here, because that one file is distributed to three of them:
#   1. `app/perseus_client.py`      - the copy `perseus.py --clients` writes into this package and
#                                     the Dockerfile ships as part of `COPY webapp/backend/app`.
#                                     This is what colt-web's own middleware imports, so it is the
#                                     copy that must win: shield and the sidecar then score with
#                                     the SAME object and cannot disagree.
#   2. `/opt/perseus/perseus/client.py` - the package the Dockerfile ships at line 60.
#   3. `<repo>/perseus/client.py`   - the source, for the test suite and for anyone running this
#                                     module out of a checkout before --clients has been run.
#
# A CANDIDATE THAT CANNOT ANSWER FOR THE WHOLE TABLE IS NOT A CANDIDATE. A copy predating the
# shared table is importable and incomplete, and `_pc.PROBE_RE` on it would raise AttributeError at
# import time and take the entire application module down. So each candidate is CHECKED against the
# full name list and skipped if it falls short -- which is also what makes a first run out of a
# fresh checkout work: candidate 1 is stale, candidate 3 is the source, and nothing crashes.
_NEEDED = ("PROBE_RE", "CLASSES", "classify", "lane_of", "ESCAPE_RE", "ASSET_RE", "HONEYTOKENS",
           "is_our_route", "probe_shape", "is_honeytoken")


def _resolve_table():
    """(module, where) for the shared detection table, or (None, "unavailable"). Never raises."""
    import importlib
    import importlib.util

    def complete(m):
        return m is not None and all(hasattr(m, n) for n in _NEEDED)

    for name, pkg in ((".perseus_client", __package__ or None), ("perseus_client", None)):
        try:
            m = importlib.import_module(name, pkg) if pkg else importlib.import_module(name)
            if complete(m):
                return m, "app.perseus_client"
        except Exception:
            pass
    here = os.path.dirname(os.path.abspath(__file__))
    for cand in ("/opt/perseus/perseus/client.py",
                 # app -> backend -> webapp -> repo root
                 os.path.join(here, "..", "..", "..", "perseus", "client.py")):
        try:
            p = os.path.abspath(cand)
            if not os.path.exists(p):
                continue
            # Loaded under its own name so it can never be mistaken for, or collide with, the
            # sidecar's module. It is the same FILE; a second module object of it holds separate
            # request state, which is why candidate 1 is preferred and this is the fallback.
            spec = importlib.util.spec_from_file_location("perseus_shared_table", p)
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            if complete(m):
                return m, p
        except Exception:
            pass
    return None, "unavailable"


_pc, DETECTION = _resolve_table()
if _pc is None:                                          # pragma: no cover - asserted by test
    try:
        print('{"evt":"shield_detection_unavailable","err":"the shared detection table could not'
              ' be resolved from any of the three known locations; probe detection is OFF on this'
              ' worker"}', flush=True)
    except Exception:
        pass


def _i(name, d):
    try:
        return int(os.environ.get(name, d))
    except Exception:
        return d


# ------------------------------------------------------------------ committed defaults + BOUNDS
# THE BOUNDS ARE THE CONTRACT WITH THE PANEL. shield_panel.py may tune the values inside these
# ranges; it can never reach the ranges themselves, because they live here in committed code and
# are enforced by clamp() on every read. A model cannot turn the shield off, and it cannot turn it
# into a self-inflicted outage.
BOUNDS = {
    "tarpit_after":  (3, 25),        # distinct suspicious hits before we start slowing them down
    "block_after":   (6, 60),        # ... before a timed block
    "window_s":      (60, 900),      # observation window
    "block_s":       (300, 86400),   # how long a block lasts (5 min .. 24 h)
    "tarpit_ms":     (250, 8000),    # per-request delay while tarpitting
    "ua_rotation_n": (3, 10),        # distinct client fingerprints from one IP = scanner
}
DEFAULTS = {"tarpit_after": 5, "block_after": 12, "window_s": 300, "block_s": 900,
            "tarpit_ms": 1500, "ua_rotation_n": 3}

ENABLED   = os.environ.get("SHIELD", "on").lower() not in ("0", "off", "false", "no")
ENFORCE   = os.environ.get("SHIELD_ENFORCE", "on").lower() not in ("0", "off", "false", "no")
BLAST_CAP = _i("SHIELD_BLAST_CAP_PCT", 20)   # never block more than this % of recent distinct IPs
MAX_TARPIT_CONCURRENT = _i("SHIELD_TARPIT_MAX", 24)
# Blocks always permitted regardless of the percentage. Deliberately small: enough to stop a
# handful of scanners on a quiet day, far too few to be an outage. NOT tunable by the panel.
MIN_ABS_BLOCKS = _i("SHIELD_MIN_ABS_BLOCKS", 5)
# Distinct 404 paths before a miss is evidence at all. Below this it is a stale bookmark.
NF_DISTINCT = _i("SHIELD_NF_DISTINCT", 6)

# ------------------------------------------------------------------ the SLOW window
# MEASURED ON THE 2026-08-26 DIGEST: 43,621 attack-shaped requests over fourteen days, coverage
# 100%, and ZERO blocked. The detector was not blind (that defect was fixed on 22 Aug); the
# EVIDENCE EXPIRED FASTER THAN THE SCANNER ACCUMULATED IT.
#
#   window 300s, block_after 12, probe_path weight 3  ->  4 probe requests inside ONE 5-minute
#   window to block. The three biggest sources in that digest ran at:
#       158.23.147.79    319 distinct paths / 2 days  =  0.55 per window
#       68.155.159.216   317 distinct paths / 2 days  =  0.55 per window
#       20.100.175.163   305 distinct paths / 2 days  =  0.53 per window
#   A source can therefore enumerate 319 DISTINCT paths and never once reach 4 in five minutes.
#   212.58.119.0/24 has been doing it for TWELVE DAYS.
#
# LOWERING THE THRESHOLD IS THE WRONG FIX and would undo a lesson already paid for: on 10 Aug two
# GENUINE visitors produced 439 and 362 404s each, entirely on our own stale routes, and a volume
# rule would have blocked both.
#
# So this is a second, much longer horizon keyed on the one thing a person does not produce:
# many DISTINCT PROBE-SHAPED paths. A visitor with four hundred 404s has ZERO, because our own
# routes are not probe shapes. That asymmetry is the whole safety argument, and test_shield.py
# asserts both directions.
SLOW_WINDOW_S = _i("SHIELD_SLOW_WINDOW_S", 86400)     # 24 hours
SLOW_DISTINCT = _i("SHIELD_SLOW_DISTINCT", 12)        # distinct probe paths before it is a scan
# Bounded, because the input is chosen by the attacker.
SLOW_MAX_IPS = _i("SHIELD_SLOW_MAX_IPS", 4000)
SLOW_MAX_PATHS = _i("SHIELD_SLOW_MAX_PATHS", 64)      # enough to prove a scan, far short of a log

# THE NETWORK HORIZON (added 2026-08-29 after fourteen days at zero blocks).
#
# The 24-hour rule above still could not see the actors we actually have. 212.58.119.0/24 had been
# probing for FIFTEEN DAYS at about 1.3 requests a day: it cannot reach twelve distinct paths in
# any twenty-four hours, no matter how long we watch. The daily digest folds returning actors to a
# /24 and could see the pattern plainly; the blocker could not, because it only ever looked at one
# address at a time.
#
# SCORING IS PER /24. BLOCKING STAYS PER ADDRESS, and a /24 hold remains an operator decision
# behind a Telegram button, because a /24 is up to 256 addresses and may be an office or a carrier.
#
# AND THE NETWORK EVIDENCE ALONE MAY NOT CONVICT. An address is blocked on it only once that
# address has ITSELF asked for SLOW_MIN_OWN probe paths. Otherwise one hostile host would put its
# 255 neighbours one request away from a block, which is the collateral this design exists to
# avoid. Corroboration before conviction, the same rule every ownership anchor in the engine obeys.
SLOW_NET_WINDOW_S = _i("SHIELD_SLOW_NET_WINDOW_S", 14 * 86400)
SLOW_NET_DISTINCT = _i("SHIELD_SLOW_NET_DISTINCT", 12)
SLOW_MIN_OWN = _i("SHIELD_SLOW_MIN_OWN", 2)

# Addresses that may NEVER be blocked. The operator's own IPs plus anything they add.
ALLOW_IPS = {x.strip() for x in os.environ.get("SHIELD_ALLOW_IPS", "").split(",") if x.strip()}

# Paths that must always work NO MATTER WHAT.
#   /.well-known/ — ACME/TLS renewal and RFC 9116. Blocking it turns a scanner into a CERTIFICATE
#                   outage for every visitor of every domain on the box.
#   /api/         — every deploy verifier in this repo asserts 401 on /api/me, and colt-web's own
#                   health depends on it. THIS OMISSION SHIPPED AND BROKE A DEPLOY: the bot-404
#                   gate sends twelve user agents from one address, the shield read that as UA
#                   rotation, blocked the operator's own IP, and /api/me answered 404 to everybody
#                   from it. visitors.py has exempted /api/ since the day it was written and I did
#                   not carry the exemption across. Authentication is what protects /api/, not the
#                   shield; a 401 is already a refusal.
NEVER_BLOCK_PREFIXES = ("/.well-known/", "/api/")

# ------------------------------------------------------------------ detection
# EVERY NAME IN THIS SECTION IS THE OBJECT perseus/client.py DEFINES -- not a copy of it. Read that
# file for the rules and the incident behind each one; see the note at the top of this file for why
# they live there. `re.compile(r"(?!)")` is a regex that can never match: if the shared table is
# unreachable this shield detects NOTHING, loudly (DETECTION above), rather than pretending to.
HONEYTOKENS = _pc.HONEYTOKENS if _pc is not None else ()
_PROBE_RE = _pc.PROBE_RE if _pc is not None else re.compile(r"(?!)")
CLASSES = _pc.CLASSES if _pc is not None else []
classify = _pc.classify if _pc is not None else (lambda path: [])
lane_of = _pc.lane_of if _pc is not None else (lambda path: None)
_ESCAPE_RE = _pc.ESCAPE_RE if _pc is not None else re.compile(r"\.\.|%2e|%2f|%5c|\\", re.I)
_ASSET_RE = _pc.ASSET_RE if _pc is not None else re.compile(r"(?!)")


# THE PAGES WE ACTUALLY SERVE. Kept here rather than imported from main.py because shield.py is
# on the request path and must not depend on the application module, but tests/test_shield.py
# asserts this set still covers main.py::_APP_ROUTES, so adding a page without adding it here
# fails the build instead of silently arming the shield against a real customer route.
OUR_TOP = ("", "login", "app", "privacy", "impressum", "contact", "demo", "experience",
           "partners")
# THE CABINET ROUTES, EXACTLY. `/app/` was a blanket PREFIX for four days and that made it a
# hiding place: `/app/wp-login.php`, `/app/.env` and `/assets/.env` all scored NOTHING, because
# the exemption I added to stop the shield blocking the administrator from `/app/admin` also
# exempted everything an attacker could append to it. Fifth instance of the same defect in this
# file, introduced by me while fixing a different one. An exemption must name what it exempts.
OUR_APP = ("admin", "assistant", "brand", "compliance", "history", "password")
OUR_EXACT = ("/robots.txt", "/sitemap.xml", "/favicon.ico", "/manifest.webmanifest", "/sw.js",
             "/defense.html", "/defense.js", "/healthz", "/health")


def is_our_route(path):
    """True for a page or asset this application serves. Never scored, never blocked.

    THE ROUTE LISTS ARE CYBERGOD'S AND STAY HERE; the matching (traversal refusal first, then the
    exact list, then the asset SHAPE, then one segment, then one level under the cabinet) is the
    shared implementation in perseus/client.py. A PREFIX EXEMPTION IS A HIDING PLACE UNLESS IT
    REFUSES TRAVERSAL: the first version returned True for anything under `/assets/`, so
    `/assets/../../.env` was waved through before the traversal rule could fire.
    """
    if _pc is None:                                      # pragma: no cover - asserted by test
        return False           # detection is off; claim nothing rather than exempt everything
    return _pc.is_our_route(path, top=OUR_TOP, app_routes=OUR_APP, exact=OUR_EXACT,
                            app_prefix="app")


def probe_shape(path):
    """Does the path LOOK like scanner behaviour? Pure pattern, NO exemptions.

    SEPARATED FROM is_probe_path BECAUSE THE EXEMPTION HAD BECOME A HIDING PLACE. /api/ is never
    blocked (every deploy verifier asserts 401 on /api/me), and the first version returned False
    for anything beneath it -- so /api/wp-login.php, /api/.env and /api/../../etc/passwd scored
    NOTHING AT ALL. An attacker who prefixed every probe with /api/ was invisible to the shield.
    Now the SHAPE is always scored; the EXEMPTION only decides whether we may ACT on that request.

    EXTRA_PROBE_PATHS is read at CALL time, not bound at definition time: shield_console mutates
    that set when the operator bans a path from Telegram, and a value captured at import would
    make the ban silently do nothing.
    """
    if _pc is None:                                      # pragma: no cover - asserted by test
        return False                                     # off, and DETECTION says so
    return _pc.probe_shape(path, is_ours=is_our_route, extra=EXTRA_PROBE_PATHS)


def is_probe_path(path):
    """probe_shape minus the paths we will never act on. Used for blocking and alert suppression."""
    p = str(path or "/")
    if p.lower().startswith(NEVER_BLOCK_PREFIXES):
        return False
    return probe_shape(p)


def is_honeytoken(path):
    if _pc is None:                                      # pragma: no cover - asserted by test
        return False
    return _pc.is_honeytoken(path)


# ------------------------------------------------------------------ state (in-memory, per worker)
_hits = {}          # ip -> [(ts, reason), ...]
_fps = {}           # ip -> {fingerprint: ts}
_blocked = {}       # ip -> expires_at
_seen_ips = {}      # ip -> last_seen  (denominator for the blast cap)
_tarpits = [0]      # concurrent tarpitted requests, list so it is mutable from a closure
_recent_paths = {}  # ip -> the last few paths, so an alert can show WHAT was asked for
_miss = {}          # ip -> {distinct 404 path: ts} — variety separates a scan from a typo
# key -> {distinct PROBE path: ts}. The key is an ADDRESS for the 24-hour rule and a /24 for the
# fourteen-day rule; both live in one dict because they are the same kind of evidence at two
# horizons, and one dict is one thing to bound, flush and prune.
#
# LOADED FROM DISK AT IMPORT. This used to be plain `{}` and was therefore reset by every deploy,
# which is why a window measured in days never once fired. slow_store fails open: if the database
# is unreadable this is `{}` and the shield behaves exactly as it did before, no worse.
_slow = {}
try:
    from . import slow_store as _ss
except Exception:                                        # pragma: no cover - direct execution
    try:
        import slow_store as _ss
    except Exception:
        _ss = None
if _ss is not None:
    try:
        _slow = _ss.load()
    except Exception:
        _slow = {}

# OPERATOR-AUTHORISED STATE. Written only by shield_console.apply_decisions() after a Telegram tap,
# never by a model and never by the inline path. Each entry is time-boxed like everything else.
BLOCK_NETS = {}          # "203.0.113" -> expires_at   (a /24, approved by hand)
STRICT_UNTIL = [0.0]     # strict mode expiry
EXTRA_PROBE_PATHS = set()   # paths the operator banned permanently


def _prune(now, window):
    for ip in list(_hits):
        _hits[ip] = [(t, r) for (t, r) in _hits[ip] if now - t < window]
        if not _hits[ip]:
            _hits.pop(ip, None)
    for ip in list(_miss):
        _miss[ip] = {k: t for k, t in _miss[ip].items() if now - t < window}
        if not _miss[ip]:
            _miss.pop(ip, None)
    for ip in list(_fps):
        _fps[ip] = {f: t for f, t in _fps[ip].items() if now - t < window}
        if not _fps[ip]:
            _fps.pop(ip, None)
    for ip, exp in list(_blocked.items()):
        if exp <= now:
            _blocked.pop(ip, None)
    for ip, t in list(_seen_ips.items()):
        if now - t > 3600:
            _seen_ips.pop(ip, None)


def cfg(key):
    """The effective value: committed default, panel tune, env override -- always CLAMPED.

    Clamping on READ rather than on write is deliberate. A tuning file that is edited by hand, or
    corrupted, or written by a future version with different ideas, still cannot push the shield
    outside the range this file commits to.
    """
    lo, hi = BOUNDS[key]
    v = DEFAULTS[key]
    try:
        from . import shield_tuning
        v = shield_tuning.get(key, v)
    except Exception:
        pass
    v = _i("SHIELD_" + key.upper(), v)
    return max(lo, min(hi, int(v)))


def fingerprint(cls):
    """A coarse client identity: browser + OS + device. Cheap, and rotating it is the tell."""
    return "%s|%s|%s" % (cls.get("browser") or "-", cls.get("os") or "-",
                         cls.get("device") or "-")


def observe(ip, path, status, cls, method="GET"):
    """Record one request and return the list of reasons it looked hostile. Never raises.

    UA ROTATION IS THE STRONGEST SIGNAL IN THIS FILE AND IT IS UNFAKEABLE-AWAY. An attacker
    rotating user agents to defeat per-client rate limiting produces the one thing a real visitor
    never produces: several distinct browser/OS fingerprints from a single address in seconds. The
    evasion IS the evidence. On the 10 Aug incident this alone identified the scanner from its
    second request, before any 404 threshold was reached.
    """
    reasons = []
    if not ENABLED or not ip or ip in ALLOW_IPS:
        return reasons
    try:
        now = time.time()
        win = cfg("window_s")
        _seen_ips[ip] = now

        # An exempt path contributes no STATUS signal: /api/me answers 401 to every anonymous
        # caller (the React app requests it on every logged-out page load), so counting that as an
        # authz probe scored ordinary visitors and blocked our own deploy verifier. The path SHAPE
        # is still scored below, or /api/ becomes a hiding place.
        _exempt = str(path or "").lower().startswith(NEVER_BLOCK_PREFIXES)
        if len(_seen_ips) % 64 == 0:
            _prune(now, win)

        if is_honeytoken(path):
            reasons.append("honeytoken")                 # zero false positives, by construction
        if probe_shape(path):
            reasons.append("probe_path")                 # shape is scored even on exempt paths
            # THE SLOW WINDOW. Remember the DISTINCT probe paths this address has asked for over
            # the last 24 hours, so a scanner pacing itself under the 5-minute rule still
            # accumulates. Only PROBE-SHAPED paths are recorded, which is what makes this safe:
            # a real visitor with hundreds of 404s on our own stale routes records nothing here.
            # RECORDED TWICE, UNDER THE ADDRESS AND UNDER THE /24. The address answers "is this
            # host scanning me today"; the network answers "has this neighbourhood been scanning
            # me for a fortnight", which is the question the fifteen-day actors made necessary.
            for _k in (ip, _ss.net_key(ip) if _ss else ""):
                if not _k:
                    continue
                if len(_slow) < SLOW_MAX_IPS or _k in _slow:
                    seen = _slow.setdefault(_k, {})
                    if len(seen) < SLOW_MAX_PATHS or path in seen:
                        seen[str(path)[:200]] = now
            # WRITE-BEHIND, off the hot path: a check against a timestamp on every probe, an
            # actual transaction once a minute. Wrapped, because losing the evidence store must
            # never cost us the request.
            if _ss is not None:
                try:
                    if _ss.due(now):
                        _slow.update(_ss.flush(_slow, now))
                except Exception:
                    pass
        # A 404 ON ONE OF OUR OWN ROUTES IS A STALE LINK, not evidence, however many of them there
        # are. The distinct-path floor alone was not enough: a visitor with eight old bookmarks
        # clears a floor of six and was blocked in testing. Our routes are not probe shapes, so
        # this costs nothing in detection and removes the whole class of false positive.
        if int(status or 0) == 404 and not _exempt and not is_our_route(path):
            # A 404 ALONE IS NOT EVIDENCE, and the real log proves it: two sources (Germany and
            # Israel) produced 439 and 362 404s while asking only for our own routes -- people,
            # not scanners. VARIETY is the discriminator: a person misses the same few stale paths;
            # a scanner misses hundreds of DIFFERENT ones. So a 404 scores only once this address
            # has missed on several DISTINCT paths inside the window.
            d404 = _miss.setdefault(ip, {})
            d404[str(path)[:120]] = now
            for _k, _t in list(d404.items()):
                if now - _t > win:
                    d404.pop(_k, None)
            if len(d404) >= NF_DISTINCT:
                reasons.append("not_found")
        if int(status or 0) in (401, 403) and not _exempt:
            reasons.append("authz_probe")
        if str(method).upper() in ("PUT", "DELETE", "PATCH", "TRACE", "CONNECT"):
            reasons.append("method_abuse")

        fp = fingerprint(cls or {})
        _fps.setdefault(ip, {})[fp] = now
        if len(_fps[ip]) >= cfg("ua_rotation_n"):
            reasons.append("ua_rotation")

        if reasons:
            _hits.setdefault(ip, []).append((now, reasons[0]))
            rp = _recent_paths.setdefault(ip, [])
            rp.append(str(path)[:120])
            del rp[:-10]                     # bounded: the alert shows five, keep a little slack
        return reasons
    except Exception:
        return []                                        # fail open, always


# A honeytoken is worth far more than one 404: a 404 can be a stale bookmark, a honeytoken cannot.
_WEIGHT = {"honeytoken": 6, "ua_rotation": 4, "probe_path": 3,
           "method_abuse": 2, "authz_probe": 1, "not_found": 1}


def _score(ip, now, win):
    """Weighted hostility for this address inside the window.

    UA ROTATION ONLY COUNTS WHEN SOMETHING ELSE IS ALSO WRONG, and that is a correction to the
    first version rather than a tuning change. Rotation is strong evidence of AUTOMATION; it is not
    by itself evidence of ATTACK. This repository's own deploy verifier sends twelve user agents
    from one address to prove the bot gate works, asks only for legitimate routes, and was duly
    blocked -- taking /api/me to 404 and failing the deploy. Monitoring, uptime checks and CI all
    look exactly like that.
    On the real 10 Aug incident the rotation arrived WITH four probe paths and a row of 404s, so
    requiring corroboration loses nothing there and removes a whole class of false positive here.
    Same doctrine as every ownership anchor in the engine: a strong signal still has to be
    corroborated before it is allowed to convict.
    """
    hits = [h for h in _hits.get(ip, ()) if now - h[0] < win]
    base = sum(_WEIGHT.get(r, 1) for (_t, r) in hits if r != "ua_rotation")
    if base <= 0:
        return 0, len(hits)                  # automation on legitimate paths is not an attack
    rot = sum(_WEIGHT["ua_rotation"] for (_t, r) in hits if r == "ua_rotation")
    return base + rot, len(hits)


def blast_ok():
    """Refuse to act when acting would affect too much of the traffic.

    An automatic control that can block everybody is worse than no control. Identical doctrine to
    the co-tenant guard's valve and the FP auditor's: narrow, never wipe.

    THE PERCENTAGE ALONE IS WRONG ON A QUIET SITE, and the shield's own regression test is what
    proved it: with one scanner and one honest visitor, blocking the scanner is 50% of the traffic,
    so a 20% cap made the shield structurally incapable of ever blocking anybody -- on exactly the
    traffic profile cybergod.ai actually has. A percentage of a handful is not a rate.
    So a small ABSOLUTE number of blocks is always permitted, and the percentage only governs once
    there are enough of them to be a pattern rather than an incident.
    """
    if len(_blocked) + 1 <= MIN_ABS_BLOCKS:
        return True
    return (len(_blocked) + 1) * 100.0 / max(1, len(_seen_ips)) <= BLAST_CAP


def _distinct(key, window, now):
    """Distinct probe paths recorded under `key` inside `window`. Prunes as it reads.

    Pruning on read is what keeps the state bounded without a sweeper: a key that stops scanning
    ages out of memory by itself, and slow_store applies the same cutoff on disk.
    """
    seen = _slow.get(key)
    if not seen:
        return 0
    cutoff = now - window
    for p in [p for p, ts in seen.items() if ts < cutoff]:
        seen.pop(p, None)
    if not seen:
        _slow.pop(key, None)
        return 0
    return len(seen)


def slow_scan(ip, now=None):
    """(own, net) distinct probe paths: this address over 24h, its /24 over fourteen days.

    Returns (0, 0) for anything not being tracked, which is every ordinary visitor, because only
    probe-shaped paths are ever recorded. A person with four hundred 404s on our own stale routes
    contributes nothing here, and that asymmetry is the entire safety argument for the rule.
    """
    try:
        now = now or time.time()
        own = _distinct(ip, SLOW_WINDOW_S, now)
        nk = _ss.net_key(ip) if _ss else ""
        net = _distinct(nk, SLOW_NET_WINDOW_S, now) if nk else 0
        return own, net
    except Exception:
        return 0, 0


def _decide_raw(ip, path):
    """ALLOW | TARPIT | BLOCK for this request. Pure function of recorded state. Never raises.

    THIS IS THE SCORING, NOT THE ENFORCEMENT. `decide()` wraps it and applies the two exemptions
    that keep a human from being locked out of the product. Kept separate on purpose: the evidence
    this function records must not change just because we declined to act on it.
    """
    try:
        if not ENABLED or not ip or ip in ALLOW_IPS:
            return "ALLOW", ""
        if str(path or "").lower().startswith(NEVER_BLOCK_PREFIXES):
            return "ALLOW", "never-block prefix (ACME / security.txt)"
        now = time.time()
        exp = _blocked.get(ip, 0)
        if exp > now:
            return "BLOCK", "already blocked for %ds more" % int(exp - now)
        # A /24 the operator approved by hand. Deliberately NOT something the shield can decide on
        # its own: a /24 is up to 256 addresses and may be a whole office or a mobile carrier.
        net = ".".join(str(ip).split(".")[:3])
        if BLOCK_NETS.get(net, 0) > now:
            return "BLOCK", "operator-approved /24 hold"
        if STRICT_UNTIL[0] > now:
            return "TARPIT", "strict mode (operator-approved)"
        # THE SLOW SCAN, checked BEFORE the fast score. Distinct probe paths over 24 hours, which
        # is the evidence a five-minute window throws away. Escalates on its own because a source
        # that has asked for a dozen different probe paths in a day has proved what it is,
        # regardless of how patiently it did so.
        slow_n, net_n = slow_scan(ip, now)
        # TWO HORIZONS. The address on its own over a day, or its /24 over a fortnight WITH this
        # address having contributed probe paths of its own. The second clause is what catches the
        # actors that had run for fifteen days untouched; SLOW_MIN_OWN is what stops one hostile
        # host putting its 255 neighbours one request away from a block.
        _rule = ("slow_scan" if slow_n >= SLOW_DISTINCT else
                 "slow_scan_net" if (net_n >= SLOW_NET_DISTINCT and slow_n >= SLOW_MIN_OWN)
                 else "")
        if _rule:
            _why = ("%d distinct probe paths in %dh - a low-and-slow scan"
                    % (slow_n, SLOW_WINDOW_S // 3600) if _rule == "slow_scan" else
                    "%d distinct probe paths from %s over %dd, %d from this address"
                    % (net_n, _ss.net_key(ip) if _ss else "?", SLOW_NET_WINDOW_S // 86400, slow_n))
            if not blast_ok():
                _ev("shield_refused", ip=ip, distinct=slow_n, net=net_n,
                    reason="blast cap on a slow scan")
                return "TARPIT", "blast cap reached - slowing instead of blocking"
            if ENFORCE:
                _blocked[ip] = now + cfg("block_s")
                _ev("shield_block", ip=ip, distinct=slow_n, net=net_n, seconds=cfg("block_s"),
                    rule=_rule, window_s=SLOW_WINDOW_S, net_window_s=SLOW_NET_WINDOW_S)
                _announce(ip, max(slow_n, net_n), slow_n, rule=_rule)
                return "BLOCK", _why
            _ev("shield_would_block", ip=ip, distinct=slow_n, net=net_n, rule=_rule)
            return "TARPIT", "enforcement off - would have blocked a slow scan"

        score, n = _score(ip, now, cfg("window_s"))
        if score >= cfg("block_after"):
            if not blast_ok():
                _ev("shield_refused", ip=ip, score=score,
                    reason="blast cap: %d blocked of %d seen IPs exceeds %d%%"
                           % (len(_blocked), len(_seen_ips), BLAST_CAP))
                return "TARPIT", "blast cap reached - slowing instead of blocking"
            if ENFORCE:
                _blocked[ip] = now + cfg("block_s")
                _ev("shield_block", ip=ip, score=score, hits=n, seconds=cfg("block_s"))
                _announce(ip, score, n)
                return "BLOCK", "score %d over %d" % (score, cfg("block_after"))
            _ev("shield_would_block", ip=ip, score=score, hits=n)
            return "TARPIT", "enforcement off - would have blocked"
        if score >= cfg("tarpit_after"):
            return "TARPIT", "score %d over %d" % (score, cfg("tarpit_after"))
        return "ALLOW", ""
    except Exception:
        return "ALLOW", ""


def tarpit_seconds():
    """How long to stall, or 0 when too many stalls are already in flight.

    A NAIVE TARPIT IS A SELF-INFLICTED DENIAL OF SERVICE: every stalled request holds a connection,
    so a scanner opening hundreds of them exhausts the server rather than itself. The concurrency
    cap is what makes this safe -- past the cap we simply answer 404 immediately.
    """
    if _tarpits[0] >= MAX_TARPIT_CONCURRENT:
        return 0.0
    return cfg("tarpit_ms") / 1000.0


def enter_tarpit():
    _tarpits[0] += 1


def leave_tarpit():
    _tarpits[0] = max(0, _tarpits[0] - 1)


# One note per address per hour. An exemption that pages on every request is a flood, and a flood
# is how the message that matters gets read past -- the roster warning and the 8/10 bot-gate line
# both had to be silenced for exactly that reason.
_EXEMPT_COOLDOWN_S = 3600
_exempt_told = {}


def decide(ip, path, authed=False):
    """ALLOW | TARPIT | BLOCK, with the two exemptions that stop us locking a human out.

    WHY THIS EXISTS (2026-09-07). The operator photographed cybergod.ai/app/admin returning our own
    branded 404 page while he was logged in as the administrator, and it worked again minutes later.
    Three measurements identified the source by elimination: `_is_probe('app/admin')` is False, the
    bot gate classifies his Chrome as `bot: False`, and the perseus sidecar answers 429 rather than
    404. The only remaining producer of a 404 on a valid page route is this module, and the block is
    time-boxed, which is exactly why it healed on its own. The shield had locked the operator out of
    his own admin console, silently, with a page that says the route does not exist.

    TWO EXEMPTIONS, BOTH NARROW, NEITHER WEAKENING ENUMERATION DEFENCE:

    1. AN AUTHENTICATED SESSION IS A KNOWN HUMAN. The cookie is signed, and only an address on the
       committed access list can obtain one at all -- it needs the shared password AND a one-time
       code delivered to a mailbox that person controls. That is far stronger corroboration than any
       timing heuristic here can produce. If a logged-in account really is scanning us, the right
       answer is a record naming WHO, which the exempt event below provides, not an anonymous 404.

    2. A ROUTE WE ACTUALLY SERVE IS NEVER BLOCKED, only slowed. `is_our_route`'s own docstring has
       said "Never scored, never blocked" since it was written, and `decide()` never consulted it --
       the code contradicted its documented contract. The shield exists to stop people asking for
       things we do not have; refusing a real page is what locks a person out of the product, and
       the tarpit already answers the throughput half of that concern.

    THE BLOCK IS STILL RECORDED EITHER WAY. `_decide_raw` sets `_blocked[ip]`, so the address stays
    blocked for the probe paths that convicted it and the evidence is unchanged. Only the response
    to a legitimate request is softened. An exemption that erased the finding would be a hiding
    place, which is the defect this codebase has already paid for four times.
    """
    try:
        verdict, why = _decide_raw(ip, path)
        if verdict != "BLOCK":
            return verdict, why

        if authed:
            _ev("shield_exempt", ip=ip, path=str(path or "")[:120],
                reason="authenticated session", would_have=why)
            # TELL THE OPERATOR. He was locked out with no message, and silence is what turned a
            # one-line fault into an hour of guessing. This is also a real signal in its own right:
            # either the detector is wrong about a real user, or an account is misbehaving.
            try:
                now = time.time()
                if now - _exempt_told.get(ip, 0) > _EXEMPT_COOLDOWN_S:
                    _exempt_told[ip] = now
                    if notify is not None:
                        notify.telegram(
                            "SHIELD would have blocked a LOGGED-IN user and did not.\n"
                            "address: %s\npath: %s\nevidence: %s\n"
                            "The address stays blocked for probe paths; the session is not."
                            % (ip, str(path or "")[:120], why))
            except Exception:
                pass                                   # an alert must never break the request
            return "ALLOW", "authenticated session - never blocked (%s)" % why

        if is_our_route(path):
            _ev("shield_exempt", ip=ip, path=str(path or "")[:120],
                reason="a route we serve", would_have=why)
            return "TARPIT", "our own route - slowed, not blocked (%s)" % why

        return verdict, why
    except Exception:
        return "ALLOW", ""                             # fail open, always


def is_blocked(ip):
    """Is this address currently held? Public because the siege feed must report what the shield
    ACTUALLY did, not infer it from a status code - the bot gate also answers 404, so `status==404`
    would have coloured ordinary crawler traffic as a block.

    IT ALWAYS RETURNED FALSE (found 2026-09-07 by a test written for something else). `_prune`
    takes (now, window) and was called with neither, so every call raised TypeError straight into
    the blanket `except` below and answered "not blocked" -- for every address, forever. The public
    defence feed is the consumer, so every genuine interception has been drawn as merely DETECTED.
    That is the mirror of the overclaim the feed was carefully built to avoid, and it was silent
    because the fallback is a plausible answer. Nth instance of a swallowed exception returning a
    default that looks like a measurement.
    """
    try:
        now = time.time()
        _prune(now, cfg("window_s"))
        if str(ip) in ALLOW_IPS:
            return False
        if _blocked.get(str(ip), 0) > now:
            return True
        net = ".".join(str(ip).split(".")[:3])
        return BLOCK_NETS.get(net, 0) > now
    except Exception:
        return False


def unblock(ip):
    """Manual release: lift the block AND forgive the history that caused it.

    Clearing the history is not tidiness, it is the whole point. The first version popped only the
    timer, so the very next request re-scored the same accumulated hits, sailed past the threshold
    again and re-blocked instantly -- a hand brake that did nothing. Its own regression test is
    what caught it. Releasing somebody means forgiving what they did, or it is not a release.
    """
    was = _blocked.pop(ip, None) is not None
    _hits.pop(ip, None)
    _fps.pop(ip, None)
    # THE SLOW WINDOW HAS TO BE FORGIVEN TOO, in memory AND on disk. It now survives restarts, so
    # leaving it would re-convict the address on its very next probe and reproduce the same
    # do-nothing hand brake through persistence. The /24's evidence is deliberately kept: forgiving
    # one host must not forgive 255 neighbours, and the network rule cannot fire on its own anyway
    # because it requires SLOW_MIN_OWN paths from the address itself, which this just cleared.
    _slow.pop(ip, None)
    if _ss is not None:
        try:
            _ss.forget(ip)
        except Exception:
            pass
    _ev("shield_unblock", ip=ip, was_blocked=was)
    return was


def state():
    """What the shield currently believes. Read by /api/diag and by the out-of-band panel."""
    now = time.time()
    return {
        "enabled": ENABLED, "enforcing": ENFORCE,
        # WHERE THE DETECTION TABLE CAME FROM. "unavailable" means the shared table could not be
        # imported and this shield is scoring NOTHING -- a state that must be readable, because a
        # control that is off and a control that found nothing look identical from the outside.
        "detection": DETECTION,
        "config": {k: cfg(k) for k in BOUNDS},
        "bounds": {k: list(v) for k, v in BOUNDS.items()},
        "blocked": {ip: int(exp - now) for ip, exp in _blocked.items() if exp > now},
        # THE EVIDENCE STORE IS REPORTED, because it fails open and a store that has quietly
        # stopped persisting looks exactly like a quiet fortnight. That confusion is what this
        # whole change set exists to end: a number that cannot fall tells you nothing.
        "slow_store": (_ss.stats() if _ss else {"healthy": False, "rows": 0, "keys": 0}),
        "watching": len(_hits), "seen_ips_1h": len(_seen_ips),
        "blast_cap_pct": BLAST_CAP, "tarpits_in_flight": _tarpits[0],
    }


def _announce(ip, score, n, rule=None):
    """Tell the operator, with the escalation menu. Best-effort and strictly non-blocking.

    The console is imported HERE rather than at module scope so that shield.py keeps no import of
    anything that talks to the network, and so a broken console can never take the request path
    down with it.

    THE PATHS SHOWN MUST BE THE EVIDENCE, NOT THE LAST FEW REQUESTS. `_recent_paths` is a short
    buffer, which is why an earlier alert read `Signals: probe_path, Paths: /` and told the
    operator nothing: "/" was simply the most recent thing that address asked for. For a SLOW SCAN
    the evidence is the set of distinct probe paths collected over 24 hours, so that is what the
    alert carries.
    """
    try:
        from . import shield_console
        hits = _hits.get(ip, ())
        if rule in ("slow_scan", "slow_scan_net"):
            # On the network rule the address's OWN paths are few by definition (SLOW_MIN_OWN is
            # 2), so an alert showing only those would understate the case that convicted it. Show
            # the neighbourhood's evidence, which is what the operator is being asked to judge.
            paths = sorted(_slow.get(ip, {}))
            if rule == "slow_scan_net" and _ss:
                paths = sorted(set(paths) | set(_slow.get(_ss.net_key(ip), {})))
            paths = paths[:8]
            reasons = [rule]
        else:
            paths = sorted({p for p in _recent_paths.get(ip, ())})[:5]
            reasons = sorted({r for (_t, r) in hits})
        shield_console.announce(ip, {
            "reasons": reasons,
            "hits": n, "score": score, "rule": rule or "fast",
            "paths": paths,
            "last_path": (_recent_paths.get(ip) or [""])[-1],
        })
    except Exception:
        pass


def _ev(evt, **k):
    if notify is None:
        return
    try:
        notify._log(evt=evt, **k)
    except Exception:
        pass
