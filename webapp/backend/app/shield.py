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
# A HONEYTOKEN IS THE ONLY ZERO-FALSE-POSITIVE SIGNAL WE HAVE. These paths are listed in robots.txt
# as Disallow and are linked from nowhere, so a request for one is either a deliberate scan or a
# robots-ignoring crawler. Either way it is not a visitor. (Thinkst canarytoken doctrine.)
HONEYTOKENS = ("/admin.php", "/wp-login.php", "/.env.bak", "/backup.zip", "/config.json.old")

_PROBE_RE = re.compile(
    r"(?:^|/)\.[^/]"                       # /.git /.env /.aws /.ssh — dot-directories
    r"|//"                                 # //slug — a doubled slash is a template artefact
    r"|/\["                                # /[workspace]/ — an UNRENDERED PLACEHOLDER. A human
                                           #   cannot type this; it is a scanner replaying docs.
    r"|\.(?:php|asp|aspx|jsp|cgi|sql|bak|old|db|sqlite|pem|key|log|ini|yml|yaml|env)(?:$|[?/])"
    r"|/(?:wp-|wordpress|phpmyadmin|xmlrpc|cgi-bin|adminer|actuator|struts|vendor/|solr|jenkins)"
    r"|(?:^|/)(?:id_rsa|credentials|dump|backup|shell|cmd|eval)(?:$|[./])"
    r"|(?:^|/)[A-Z_]{3,}\.md$"             # /DOCS.md /IAM.md /README.md at the root: repository
                                           #   documentation we do not serve, a leaked-docs scan.
    r"|/null$",
    re.I)


def is_probe_path(path):
    """True when the PATH ITSELF is scanner behaviour, whatever the user agent claims.

    A user agent is attacker-controlled. The path is the evidence.
    """
    p = str(path or "/")
    if p.lower().startswith(NEVER_BLOCK_PREFIXES):
        return False
    if p.lower() in EXTRA_PROBE_PATHS:
        return True
    return bool(_PROBE_RE.search(p))


def is_honeytoken(path):
    return str(path or "").split("?")[0].lower() in HONEYTOKENS


# ------------------------------------------------------------------ state (in-memory, per worker)
_hits = {}          # ip -> [(ts, reason), ...]
_fps = {}           # ip -> {fingerprint: ts}
_blocked = {}       # ip -> expires_at
_seen_ips = {}      # ip -> last_seen  (denominator for the blast cap)
_tarpits = [0]      # concurrent tarpitted requests, list so it is mutable from a closure
_recent_paths = {}  # ip -> the last few paths, so an alert can show WHAT was asked for

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

        # A PATH WE WILL NEVER BLOCK ON MUST NOT BE SCORED ON EITHER, or the score is fed by
        # traffic that can never be acted upon. /api/me answers 401 to every ANONYMOUS caller --
        # the React app itself requests it on every page load while logged out -- so counting that
        # as an "authz probe" scored ordinary visitors, and scored the deploy verifier hard enough
        # to block it. Authentication is the control on /api/; the shield is not.
        if str(path or "").lower().startswith(NEVER_BLOCK_PREFIXES):
            return reasons
        if len(_seen_ips) % 64 == 0:
            _prune(now, win)

        if is_honeytoken(path):
            reasons.append("honeytoken")                 # zero false positives, by construction
        if is_probe_path(path):
            reasons.append("probe_path")
        if int(status or 0) == 404:
            reasons.append("not_found")
        if int(status or 0) in (401, 403):
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


def decide(ip, path):
    """ALLOW | TARPIT | BLOCK for this request. Pure function of recorded state. Never raises."""
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
    _ev("shield_unblock", ip=ip, was_blocked=was)
    return was


def state():
    """What the shield currently believes. Read by /api/diag and by the out-of-band panel."""
    now = time.time()
    return {
        "enabled": ENABLED, "enforcing": ENFORCE,
        "config": {k: cfg(k) for k in BOUNDS},
        "bounds": {k: list(v) for k, v in BOUNDS.items()},
        "blocked": {ip: int(exp - now) for ip, exp in _blocked.items() if exp > now},
        "watching": len(_hits), "seen_ips_1h": len(_seen_ips),
        "blast_cap_pct": BLAST_CAP, "tarpits_in_flight": _tarpits[0],
    }


def _announce(ip, score, n):
    """Tell the operator, with the escalation menu. Best-effort and strictly non-blocking.

    The console is imported HERE rather than at module scope so that shield.py keeps no import of
    anything that talks to the network, and so a broken console can never take the request path
    down with it.
    """
    try:
        from . import shield_console
        hits = _hits.get(ip, ())
        shield_console.announce(ip, {
            "reasons": sorted({r for (_t, r) in hits}),
            "hits": n, "score": score,
            "paths": sorted({p for p in _recent_paths.get(ip, ())})[:5],
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
