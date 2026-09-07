"""Deterministic vetting: a model may PROPOSE a detection pattern, this file decides.

THE RULE THIS ENFORCES. Four reviewers agreeing is evidence, not authority. On 2026-08-07 all four
agreed a check was broken when the check was fine; on 2026-09-06 all four agreed on a bad answer
because I had shown them bad evidence. A pattern that can refuse a paying customer's request must
therefore clear tests that do not involve asking anyone's opinion.

FIVE BARRIERS, each independent, each failing CLOSED:

 1. It must COMPILE. A model that emits `(?P<` or an unbalanced group produces a rule that would
    raise inside the request path.
 2. It must not match ANYTHING WE SERVE. The known-good corpus is every real route of all six
    projects plus the paths real visitors actually request. This is the barrier that matters: on
    2026-08-10 a 404-count rule would have blocked two genuine visitors, one German and one
    Israeli, who had simply followed stale links.
 3. It must not be CATASTROPHICALLY BROAD. `.*`, `^/`, `/api` and friends match the whole estate.
    A rule that matches everything is not a detection, it is an outage with a regex in front.
 4. It must be ANCHORED or specific enough to mean something. A two-character fragment will match
    inside a thousand legitimate paths; this is the `struktur` inside `infrastruktur` lesson, which
    put an entire property group's estate into a telecoms company's report.
 5. It must be CHEAP. A pattern with nested quantifiers can be walked into catastrophic
    backtracking by a caller who controls the path, which turns our own defence into the denial of
    service. Measured against a hostile input, not reasoned about.

WHAT IS DELIBERATELY NOT HERE: any check that asks whether the pattern is a "good idea". That is
the reviewers' job, and their answer arrives as a vote count, never as a veto or a waiver.
"""
import re
import time

# Selectors that match so much of the estate that no evidence could justify them.
_TOO_BROAD = (".*", ".+", "^.*$", "^/", "/", "^/api", "/api", "^/api/", "/api/", "\\w+", "[a-z]+")

# A pattern must be at least this long once the regex punctuation is stripped, or it is a fragment
# that will collide with legitimate paths.
_MIN_LITERAL = 3

# Real traffic that must never match. Extended by the caller with each project's live route table.
KNOWN_GOOD = [
    "/", "/index.html", "/favicon.ico", "/robots.txt", "/sitemap.xml", "/manifest.webmanifest",
    "/sw.js", "/.well-known/security.txt", "/.well-known/acme-challenge/token",
    "/assets/index-abc123.js", "/assets/index-abc123.css", "/media/cassandra.mp4",
    "/api/health", "/api/me", "/api/demo", "/api/langs", "/api/jurisdictions", "/api/siege",
    "/api/auth/login", "/api/auth/signup", "/api/auth/verify", "/api/auth/logout",
    "/api/chat", "/api/models", "/api/contact", "/api/checkout", "/api/privacy/ack",
    "/api/assess", "/api/compliance", "/api/history", "/api/brand", "/api/admin/users",
    "/api/electronic/jobs", "/api/electronic/generate", "/v1/chat/completions", "/v1/models",
    "/app", "/login", "/partners", "/contact", "/impressum", "/privacy", "/demo", "/experience",
    "/shop", "/produkte", "/warenkorb", "/kasse", "/kontakt", "/datenschutz",
]

# NESTED QUANTIFIERS: the classic catastrophic-backtracking shapes, refused STATICALLY and never
# executed. The first version of this file measured the cost by RUNNING the pattern against a
# hostile string, and `/(a+)+!$` against 64 a's backtracks 2**64 times, so the vetter hung: I
# measured a denial of service by performing one. Detect the shape, then never run it.
_NESTED_QUANT = re.compile(r"\([^)]*[+*]\)[+*{]|\([^)]*\{\d+,\}\)[+*{]")

# A path a hostile caller could send. SHORT on purpose: anything that survives the static check
# above cannot blow up exponentially here, and a bounded probe cannot hang the daily cycle.
_EVIL = "/" + ("a" * 16) + "!" * 6


def _literal_len(pattern):
    """Roughly how much of the pattern is actual text rather than regex syntax."""
    return len(re.sub(r"[\\^$.|?*+()\[\]{}]", "", pattern))


def vet(pattern, known_good=None, budget_ms=25.0):
    """(ok, reason). Never raises: a malformed proposal is a refusal, not a crash."""
    p = (pattern or "").strip()
    if not p:
        return False, "empty pattern"
    if len(p) > 200:
        return False, "pattern is %d chars; a rule nobody can read is a rule nobody can review" % len(p)

    if p in _TOO_BROAD or p.replace("^", "").replace("$", "") in _TOO_BROAD:
        return False, "matches essentially the whole estate (%r)" % p

    try:
        rx = re.compile(p, re.I)
    except re.error as e:
        return False, "does not compile: %s" % e

    if _literal_len(p) < _MIN_LITERAL:
        return False, ("only %d literal character(s); a fragment that short collides with real "
                       "paths (the 'struktur' inside 'infrastruktur' failure)" % _literal_len(p))

    # BARRIER 2, and the one that protects customers.
    corpus = list(KNOWN_GOOD) + list(known_good or [])
    hits = [g for g in corpus if rx.search(g)]
    if hits:
        return False, "matches %d path(s) we actually serve, e.g. %s" % (len(hits), ", ".join(hits[:3]))

    # BARRIER 5a, STATIC and first: never execute a shape that is known to explode.
    if _NESTED_QUANT.search(p):
        return False, ("nested quantifier (the catastrophic-backtracking shape); refused without "
                       "running it, because running it is the denial of service")

    # BARRIER 5b. Measure what is left, on a bounded probe.
    t0 = time.perf_counter()
    try:
        rx.search(_EVIL)
        rx.search("/" + "ab" * 128)
    except Exception as e:
        return False, "raised while matching: %r" % e
    ms = (time.perf_counter() - t0) * 1000
    if ms > budget_ms:
        return False, ("took %.1fms on a hostile input (budget %.0fms); a pattern this expensive "
                       "turns our own defence into the denial of service" % (ms, budget_ms))

    return True, "compiles, matches nothing we serve, %d literal chars, %.2fms on a hostile input" \
                 % (_literal_len(p), ms)


def vet_batch(proposals, known_good=None):
    """[(pattern, why, evidence, reviewers)] -> (accepted, refused). Both are reported: a refusal
    is the most useful line in the daily delta, because it says what the loop wanted to do and was
    not allowed to."""
    accepted, refused = [], []
    for item in proposals or []:
        pattern = (item or {}).get("pattern")
        ok, reason = vet(pattern, known_good)
        rec = dict(item or {})
        rec["vet"] = reason
        (accepted if ok else refused).append(rec)
    return accepted, refused
