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
# A HONEYTOKEN IS THE ONLY ZERO-FALSE-POSITIVE SIGNAL WE HAVE. These paths are listed in robots.txt
# as Disallow and are linked from nowhere, so a request for one is either a deliberate scan or a
# robots-ignoring crawler. Either way it is not a visitor. (Thinkst canarytoken doctrine.)
HONEYTOKENS = ("/admin.php", "/wp-login.php", "/.env.bak", "/backup.zip", "/config.json.old")

_PROBE_RE = re.compile(
    # /.git /.env /.aws /.ssh — dot-directories.
    # THE NEGATIVE LOOKAHEAD IS LOAD-BEARING. `/.well-known/` is an IANA-registered namespace we
    # serve on purpose: ACME renewal and RFC 9116 security.txt live there. Without the exclusion
    # every Let's Encrypt validation and every security.txt fetch scored `probe_path` at weight 3.
    # It could not be BLOCKED (the prefix is exempt) but it was counted, so our own certificate
    # renewals were inflating the attack figures in the daily digest.
    # An impostor is still caught: `/.well-knownX/` fails the lookahead because it requires the
    # slash, and `/.well-known/x.php` or a traversal underneath it is caught by the rules below.
    r"(?:^|/)\.(?!well-known/)[^/]"
    r"|//"                                 # //slug — a doubled slash is a template artefact
    r"|/\["                                # /[workspace]/ — an UNRENDERED PLACEHOLDER. A human
                                           #   cannot type this; it is a scanner replaying docs.
    r"|\.(?:php|asp|aspx|jsp|cgi|sql|bak|old|db|sqlite|pem|key|log|ini|yml|yaml|env)(?:$|[?/])"
    r"|/(?:wp-|wordpress|phpmyadmin|xmlrpc|cgi-bin|adminer|actuator|struts|vendor/|solr|jenkins)"
    # THE NINETEEN CLASSES MEASURED AGAINST THE REAL MASS-SCANNING CORPUS (OWASP OAT-014, CISA
    # advisories, public honeypot feeds). Written from evidence of what scanners actually send,
    # not from imagination — `analyse_attacks.py` re-runs that comparison against OUR OWN log so
    # the next gap is found the same way.
    r"|/(?:admin|manager/html|cpanel|webadmin|adminpanel)(?:$|[/?])"      # admin consoles
    r"|/(?:swagger|api-docs|graphql|graphiql)|/v\d/api-docs"              # API introspection
    r"|/(?:boaform|goform|HNAP1|hudson|setup\.cgi|shell\?)"              # router / IoT / CI
    r"|/(?:web\.config|server-status|server-info|\.DS_Store|\.npmrc|\.dockercfg)"
    r"|XDEBUG_SESSION|/_ignition|/telescope/|/login\.action"             # debug + RCE chains
    r"|%2e%2e|\.\./|/%2e[a-z]"    # traversal, AND the single-encoded dot: 185.177.72.x
                                  # asked for /%2eenv five times each. One %2e IS ".", so that is
                                  # /.env wearing a costume, and the double-encoded rule missed it.
    r"|/autodiscover/autodiscover\.xml"                                  # Exchange probe (we run none)
    r"|(?:^|/)(?:id_rsa|credentials|dump|backup|shell|cmd|eval)(?:$|[./])"
    r"|(?:^|/)[A-Z_]{3,}\.md$"             # /DOCS.md /IAM.md /README.md at the root: repository
                                           #   documentation we do not serve, a leaked-docs scan.
    r"|/null$"

    # ------------------------------------------------------------------------------------------
    # THE NINE PATHS OUR OWN 14-DAY DIGEST WAS SEEING AND THIS REGEX COULD NOT SCORE (2026-08-22).
    # analyse_attacks.py named them in its "NEW OR UNRECOGNISED" section for days and nobody
    # joined the two up. Measured before the fix: 9 of 17 real attack paths from that digest were
    # invisible to the blocker, which is the whole reason `blocked` kept reading low. The corpus
    # knowing a class is worthless if probe_shape() cannot score it.
    #
    # EVERY PATTERN BELOW IS ANCHORED so it cannot reach a real route. The live route set is
    # main.py::_APP_ROUTES = {"", login, app, privacy, impressum, contact, demo, experience,
    # partners} plus /assets/** (StaticFiles) and /api/** (exempt anyway). test_shield.py asserts
    # all of them against this regex, because a shield that blocks a visitor is worse than none.

    # 1. PHP VERSION SUFFIXES. `.php$` missed /1.php7, /about.php525, /alfa-rex.php7, and the
    #    digest counted 24,069 php probes while these specific ones scored nothing.
    r"|\.php\d{1,4}(?:$|[?/])"

    # 2. VITE DEV-SERVER ARBITRARY FILE READ (CVE-2025-30208 family). /@fs/ is a Vite internal
    #    prefix; /@fs/etc/passwd and /@fs/proc/self/environ were the single most-repeated
    #    unrecognised probe in the digest, from three separate sources. We BUILD with Vite and
    #    serve static files in production, so this cannot succeed here, but a request for it is
    #    unambiguously a scanner: no browser and no human ever emits it.
    r"|(?:^|/)@(?:fs|vite|id)(?:$|/)"

    # 3. CLOUD AND SERVICE CREDENTIALS, by exact filename rather than by extension. Matching
    #    "*.json" would hit the SBOM and any future public document; matching these names cannot.
    r"|(?:^|/)(?:service[-_]?account(?:[-_]?key)?|serviceaccountkey|firebase[-_]?adminsdk"
    r"|firebase|credentials|secrets?|gcp[-_]?key|client[-_]secret"
    r"|application_default_credentials)\.json(?:$|[?/])"
    r"|\.(?:tfstate|tfvars|pfx|p12|jks|keystore|axd)(?:$|[?/])"
    # kubeconfig has NO extension, so it needs a filename rule and not an extension rule. The
    # committed test caught this: it was listed in the extension alternation, where it could never
    # match, which is a rule that looks present and does nothing.
    r"|(?:^|/)(?:kubeconfig|\.git-credentials|id_ed25519|authorized_keys)(?:$|[?/])"

    # 4. BUILD AND DEPLOY ARTEFACTS. Present in a repository, never on a web root.
    r"|(?:^|/)(?:Dockerfile|docker-compose|Procfile|Makefile|Jenkinsfile|Vagrantfile)(?:$|[.?/])"

    # 5. FRAMEWORK DEBUG CONSOLES. Information disclosure by design, which is why scanners want
    #    them. /telescope/ and /_ignition are already above; these are the rest of the family.
    r"|/(?:_?debugbar|_profiler|_debug|elmah\.axd|trace\.axd)(?:$|[/?])"

    # 7. FRAMEWORK AND CLOUD CONFIG FILES, from the 2026-08-26 digest. `/amplifyconfiguration.json`
    #    (AWS Amplify), `/application.properties` and `/appsettings.json` (Spring Boot and .NET)
    #    all carry credentials and none of them was scored. Named files, not an extension rule:
    #    the panel also proposed a bare `\.json$`, which would match `/.well-known/sbom.cdx.json`
    #    that we now serve deliberately. That proposal was REFUSED for exactly that reason.
    r"|(?:^|/)(?:amplifyconfiguration|awsconfiguration|appsettings(?:\.[a-z]+)?"
    r"|application|application-[a-z]+)\.(?:json|properties|ya?ml|config)(?:$|[?/])"

    # 8. WORDPRESS REST API ENUMERATION: /blog/wp/v2/users, /wp-json/wp/v2/users. The `/wp-` rule
    #    above misses the `/blog/wp/v2/` form, which is what the digest actually saw.
    r"|/wp/v2/(?:users|posts|media|categories|tags|pages)"
    r"|/wp-json(?:$|/)"

    # 6. ROOT-LEVEL HEX DIRECTORIES: /1b7e06/ /2ff83958/ /3fa375/. Cache and WAF probing.
    #    DELIBERATELY ROOT-ONLY. The obvious `(?:^|/)[0-9a-f]{5,12}/?$` would also match the LAST
    #    SEGMENT of a legitimate path, and job identifiers are hex, so /app/<jobid> would have
    #    been read as an attack on the operator's own cabinet. Anchor at ^ and the risk is gone.
    r"|^/[0-9a-f]{5,12}/?$"

    # ------------------------------------------------------------------------------------------
    # 9. THE EIGHT PATHS FROM THE 2026-08-29 DIGEST (added 2026-08-29).
    #
    # WHY THEY WERE MISSED IS MORE IMPORTANT THAN THE PATHS. Every rule above matches a dot, an
    # extension or a well-known product name. These eight carry NONE of those: `/env` is `.env`
    # with the dot removed, `/phpinfo` is the classic PHP disclosure page without its extension,
    # and `/Gaia/` and `/WebInterface/` are appliance consoles whose names look like ordinary
    # English words. A rule set built around punctuation cannot see a bare word.
    #
    # ALL EIGHT ARE ROOT-ANCHORED AND EXACT. That is the whole safety argument, and it matters
    # more here than anywhere else in this regex: `/info` and `/environment` ARE plausible routes
    # on somebody's site. They are not routes on OURS (main.py::_APP_ROUTES), and an anchored
    # exact match cannot reach `/api/info`, `/app/environment` or any asset path. Both directions
    # are asserted in test_shield.py against the real route list.
    #
    # `/crusader-404-probe` is DELIBERATELY LEFT OUT even though it appeared alongside these. It
    # arrived from three separate Google Cloud addresses, which is the shape of a commercial
    # scanning service rather than an attacker, and "we do not recognise it" is the honest state
    # until somebody establishes what it is. Absence of evidence is not a detection rule.
    # TWO RULES, NOT ONE, AND THE SPLIT IS THE POINT. `Gaia`, `WebInterface` and `geoserver` are
    # PRODUCT NAMES: unambiguous wherever they appear, so a subpath is allowed and must be, because
    # the real request in the digest was `/geoserver/web/` and an exact rule scored it False.
    # `env`, `environment`, `info`, `phpinfo` and `flight` are ORDINARY WORDS and stay exact at the
    # root: `^/info/?$` cannot reach `/api/info` or `/information`, and a prefix rule would.
    r"|^/(?:Gaia|WebInterface|geoserver)(?:$|[/?])"
    r"|^/(?:env|environment|phpinfo|info|flight)/?$"

    # 10. CLOUD INSTANCE METADATA, the SSRF payoff path. 169.254.169.254 is only reachable from
    #     inside the instance, so a request arriving over the internet for one of these is an
    #     attacker testing whether our front end will proxy it. We run no such proxy, which is
    #     exactly why a request for it is unambiguous: nothing legitimate ever asks.
    r"|(?:^|/)latest/(?:meta-data|user-data|dynamic)(?:$|/)"
    r"|(?:^|/)computeMetadata/(?:v\d|$)"
    r"|(?:^|/)metadata/(?:instance|identity|v1)(?:$|/)",
    re.I)


# ---------------------------------------------------------------------------------------------
# THE CLASS VOCABULARY. One table, used by three things: the public siege feed, analyse_attacks.py
# and the Grafana labels. It lived only in analyse_attacks.py, which is a repo-root ops script and
# is NOT copied into the colt-web image - so the feed could not have named a lane without a second
# copy, and a second copy is how ENRICH_MODELS ended up with four homes.
# NOTE this does NOT make the gap analysis circular: that compares this CORPUS against
# probe_shape(), which is a separate regex. The corpus is "what exists"; probe_shape is "what we
# detect". Sharing the vocabulary is what lets the two be compared at all.
CLASSES = [
    ("wordpress",   re.compile(r"(?i)/(wp-|wordpress|xmlrpc)")),
    ("php_probe",   re.compile(r"(?i)\.php(?:$|[?/])")),
    ("env_secrets", re.compile(r"(?i)(?:^|/)\.(env|git|aws|ssh|svn)")),
    ("admin_panel", re.compile(r"(?i)/(admin|manager|phpmyadmin|adminer|cpanel|webadmin)")),
    ("api_docs",    re.compile(r"(?i)/(swagger|openapi|graphql|actuator|\.well-known/openid)")),
    ("shell_rce",   re.compile(r"(?i)(cgi-bin|/shell|/cmd|eval\(|\bbash\b|\bwget\b|\bcurl\b)")),
    ("traversal",   re.compile(r"(\.\./|%2e%2e|\.\.%2f)")),
    ("sqli",        re.compile(r"(?i)(union\s+select|'\s+or\s+1=1|sleep\(|benchmark\()")),
    ("xss",         re.compile(r"(?i)(<script|javascript:|onerror=)")),
    ("backup_file", re.compile(r"(?i)\.(bak|old|sql|zip|tar|gz|db|sqlite|log|ini|ya?ml)(?:$|[?/])")),
    ("docs_leak",   re.compile(r"(?:^|/)[A-Z_]{3,}\.md$")),
    ("template",    re.compile(r"(//|/\[)")),
    ("iot_router",  re.compile(r"(?i)/(boaform|goform|HNAP1|setup\.cgi|hudson|jenkins|solr)")),
    # Added 2026-08-22 alongside the probe_shape patterns. THE TWO MUST MOVE TOGETHER: the corpus
    # is "what exists" and probe_shape is "what we detect", and the gap analysis is only
    # meaningful while both are current. A class here with no scoring rule there is a name for
    # something we still cannot block.
    ("dev_server",  re.compile(r"(?i)(?:^|/)@(fs|vite|id)(?:$|/)")),
    ("cloud_creds", re.compile(r"(?i)(?:^|/)(service[-_]?account|firebase|credentials|secrets?)"
                               r"\.json|\.(tfstate|tfvars|kubeconfig|pfx|p12|jks)(?:$|[?/])")),
    ("build_files", re.compile(r"(?i)(?:^|/)(Dockerfile|docker-compose|Procfile|Makefile"
                               r"|Jenkinsfile|Vagrantfile)(?:$|[.?/])")),
    ("debug_panel", re.compile(r"(?i)/(_?debugbar|_profiler|_debug|elmah\.axd|trace\.axd"
                               r"|_ignition|telescope)(?:$|[/?])")),
    ("hex_spray",   re.compile(r"(?i)^/[0-9a-f]{5,12}/?$")),
    # Added 2026-08-29 with section 9 and 10 of _PROBE_RE. THE TWO MUST MOVE TOGETHER, per the
    # note above: a class here with no scoring rule there is a name for something we still cannot
    # block, and a scoring rule with no class here is a block the digest cannot explain.
    # Root-anchored and exact, for the same reason the regex is: these are ordinary words.
    ("bare_secret", re.compile(r"(?i)^/(env|environment|phpinfo|info)/?$")),
    ("appliance_ui", re.compile(r"(?i)^/(Gaia|WebInterface|geoserver)(?:$|[/?])|^/flight/?$")),
    ("cloud_metadata", re.compile(r"(?i)(?:^|/)(latest/(meta-data|user-data|dynamic)"
                                  r"|computeMetadata/v\d|metadata/(instance|identity|v1))(?:$|/)")),
]


def classify(path):
    """Every class a path belongs to, most specific first. [] means it is not attack-shaped."""
    return [name for name, rx in CLASSES if rx.search(path or "")]


def lane_of(path):
    """The single lane the public feed should draw this in, or None."""
    hits = classify(path)
    return hits[0] if hits else None


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
# Static assets are matched by SHAPE, not by prefix: a real build asset is a filename with a known
# extension, so `/assets/index-a1b2c3.js` is ours and `/assets/.env` is not.
_ASSET_RE = re.compile(r"^/(?:assets|media|icons|static)/[\w][\w.\-]*"
                       r"\.(?:js|mjs|css|map|png|jpe?g|gif|webp|avif|svg|ico|woff2?|ttf|otf|eot"
                       r"|mp4|webm|json|txt)$", re.I)
OUR_EXACT = ("/robots.txt", "/sitemap.xml", "/favicon.ico", "/manifest.webmanifest", "/sw.js",
             "/defense.html", "/defense.js", "/healthz", "/health")


_ESCAPE_RE = re.compile(r"\.\.|%2e|%2f|%5c|\\", re.I)


def is_our_route(path):
    """True for a page or asset this application serves. Never scored, never blocked.

    A PREFIX EXEMPTION IS A HIDING PLACE UNLESS IT REFUSES TRAVERSAL. The first version returned
    True for anything under `/assets/`, so `/assets/../../.env` was waved through before the
    traversal rule could fire, and the negative test caught it immediately. That is the identical
    defect the `/api/` prefix already caused once, reintroduced by me in the fix for a different
    one. No legitimate route contains `..` or an encoded slash or dot, so refuse first and match
    afterwards.
    """
    raw = str(path or "/")
    if _ESCAPE_RE.search(raw):
        return False
    p = (raw.split("?")[0] or "/").rstrip("/") or "/"
    if p in OUR_EXACT or path in OUR_EXACT:
        return True
    if _ASSET_RE.match(p):                       # a real build asset, matched by SHAPE
        return True
    seg = [s for s in p.strip("/").split("/") if s]
    if not seg:
        return True                              # "/"
    if len(seg) == 1:
        return seg[0] in OUR_TOP
    # Exactly one level under /app/, and only a route the cabinet actually registers.
    return len(seg) == 2 and seg[0] == "app" and seg[1] in OUR_APP


def probe_shape(path):
    """Does the path LOOK like scanner behaviour? Pure pattern, NO exemptions.

    SEPARATED FROM is_probe_path BECAUSE THE EXEMPTION HAD BECOME A HIDING PLACE. /api/ is never
    blocked (every deploy verifier asserts 401 on /api/me), and the first version returned False
    for anything beneath it -- so /api/wp-login.php, /api/.env and /api/../../etc/passwd scored
    NOTHING AT ALL. An attacker who prefixed every probe with /api/ was invisible to the shield.
    Now the SHAPE is always scored; the EXEMPTION only decides whether we may ACT on that request.
    """
    raw = str(path or "/")
    if raw.lower() in EXTRA_PROBE_PATHS:
        return True
    # THE QUERY STRING IS ALWAYS SCANNED, EVEN ON OUR OWN PAGES.
    # `/?XDEBUG_SESSION_START=phpstorm` has `/` as its path. The first version of the route
    # exemption stripped the query, saw the homepage, and returned False, so a payload delivered
    # in the query on any legitimate URL became invisible. That is the `/api/` hiding place for
    # the THIRD time in one change: exemption from ACTION kept turning into exemption from
    # OBSERVATION. The path may be ours; the query never is.
    p, _sep, q = raw.partition("?")
    if q and _PROBE_RE.search(q):
        return True
    # OUR OWN ROUTES ARE NEVER AN ATTACK SHAPE, and this is checked FIRST.
    # `/app/admin` matched the `/(admin|manager|cpanel|...)` console rule and came back ACTIONABLE,
    # so the administrator moving around their own administration page accumulated probe_path at
    # weight 3 per request and could have tarpitted, then blocked, themselves out of the one page
    # only they can reach. The rule predates this change; the route was added later and nothing
    # compared the two. Same family as the 439-404 real visitor: a detector tuned on attacker
    # behaviour has to be checked against OUR behaviour before it can be trusted.
    if is_our_route(p):
        return False
    return bool(_PROBE_RE.search(raw))


def is_probe_path(path):
    """probe_shape minus the paths we will never act on. Used for blocking and alert suppression."""
    p = str(path or "/")
    if p.lower().startswith(NEVER_BLOCK_PREFIXES):
        return False
    return probe_shape(p)


def is_honeytoken(path):
    return str(path or "").split("?")[0].lower() in HONEYTOKENS


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


def is_blocked(ip):
    """Is this address currently held? Public because the siege feed must report what the shield
    ACTUALLY did, not infer it from a status code - the bot gate also answers 404, so `status==404`
    would have coloured ordinary crawler traffic as a block."""
    try:
        _prune()
        if str(ip) in ALLOW_IPS:
            return False
        if _blocked.get(str(ip), 0) > time.time():
            return True
        net = ".".join(str(ip).split(".")[:3])
        return BLOCK_NETS.get(net, 0) > time.time()
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
