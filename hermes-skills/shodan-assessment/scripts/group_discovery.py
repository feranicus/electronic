#!/usr/bin/env python3
"""
group_discovery.py — find the customer's SUBSIDIARIES from first-party evidence.

WHY THIS EXISTS (the angermann.de forensics, 2026-07)
-----------------------------------------------------
angermann.de shipped a deck that found 1 of the customer's 8 domains and added 2 that belong to
a law firm. ONE mechanism caused both failures: the brand-token gate in shodan_recon.

  too LOOSE : anything containing "angermann" was admitted   -> ra-angermann.de (Rechtsanwalt),
              renner-angermann.de, angermann-webdesign.de, "Zahnarztpraxis Angermann" (a DENTIST)
  too TIGHT : anything NOT containing it was invisible       -> netbid.com, netbid.io,
              nordleasing.com, leaseback.de, buerosuche.de

The second half is the important one, and it is STRUCTURAL: no amount of certificate-transparency,
SAN harvesting or DNS probing can ever reach netbid.com from the seed angermann.de, because the two
strings share nothing. Those missed hosts held the best findings in the engagement (an expired
certificate on the netbid.io mail cluster across 7 ports; an expired cert on nordleasing).

A surname is a terrible ownership anchor. A company's own "our group" page is an excellent one:
it is FIRST-PARTY, published by the customer, and it names every subsidiary with a link. That is
evidence of ownership in the same sense a shared certificate is — better, in fact, because it is
an assertion by the owner rather than an inference by us.

THE RULE THIS MODULE ENFORCES (extends the standing one in CLAUDE.md)
--------------------------------------------------------------------
  "An identity anchor must CORROBORATE the seed brand."
Corroboration is not only string similarity. A domain the customer's own group-structure page
links to corroborates ownership even with a completely different name; a domain that merely shares
a surname does NOT corroborate anything. So:

  * a candidate found on a STRUCTURE page (struktur/gruppe/group/companies/beteiligungen/...)
    is tier "group_structure"  -> strong, eligible for scope
  * a candidate found anywhere else on the site is tier "site_link"
    -> weak (partners, clients, tooling, social) -> NEVER auto-scoped, offered via clarify.py
  * every strong candidate is ALSO put to the operator in the clarification questions, because
    a group page can list joint ventures and global network brands (Angermann's M&A arm trades as
    Oaklins Germany AG, but oaklins.com is a worldwide network's shared infrastructure and is
    emphatically NOT Angermann's attack surface).

Fails CLOSED throughout: any fetch error yields NO candidates rather than a guess. Absence of
evidence is never a finding (CLAUDE.md).

USAGE
    python group_discovery.py angermann.de              # prints the JSON block
    python group_discovery.py angermann.de --json

    from group_discovery import discover
    res = discover("angermann.de")
    res["strong"]  -> [{"domain":..., "why":..., "source":...}, ...]
    res["weak"]    -> [...]

The `fetch` argument is a seam so tests inject fixtures instead of hitting the network
(scripts/test_group_discovery.py).
"""
import argparse, html as _html, json, re, sys, urllib.parse, urllib.request

try:                                    # authoritative scope denylist (shared with shodan_recon)
    from scope_deny import is_denied as _denied, why_denied as _deny_why
except Exception:                       # never let a missing import kill discovery
    def _denied(a): return False
    def _deny_why(a): return ""

try:                                    # registrable domain via the Public Suffix List
    import psl as _PSL
except Exception:
    _PSL = None

UA = "Mozilla/5.0 (compatible; cybergod-recon/1.0; +https://cybergod.ai)"
TIMEOUT = 8
MAX_PAGES = 4           # structure pages to read (a company has ONE structure page)
MAX_CANDIDATES = 25     # hard cap: a group page cannot legitimately name 200 companies

# ONLY a genuinely structural page counts. The first cut of this used loose hints (gruppe|
# unternehmen|portfolio|about) and on the REAL angermann.de it matched EIGHT pages — newsroom,
# references, careers, history — and harvested spiegel.de (a press article), xing-share.com (a
# share widget) and bewatec.com / vesselbid.com / clarus-am.com / einkaufsfinanzierer.com
# (M&A TRANSACTION CLIENTS). Putting an M&A client's estate in the adviser's deck is the exact
# S-KON failure this engine exists to prevent, so the pattern is now narrow and anchored.
# THE ABAKUS-TK.DE INCIDENT (2026-08): `struktur` was matched as a BARE SUBSTRING, and
# `infrastruktur` contains `struktur`. So `/it-infrastruktur/` -- the single most likely page path
# on a TELECOMS or IT provider's website -- was read as a corporate group-structure page, every
# external link on it was harvested as a "subsidiary", and the site-wide WhatsApp footer button put
# `wa.me` into scope. 236 of the 348 hosts in the delivered deck were Meta's.
# The irony is in the targeting: this module was written for a PROPERTY group and broke on a
# telecoms company, because "Infrastruktur" is that company's product.
# The generic tokens are therefore anchored to a word boundary; the German compounds that are
# genuinely structural (konzern-/unternehmens-/firmen-struktur) stay listed explicitly, because a
# lookbehind cannot tell them apart from `infrastruktur` -- they all have a letter in front.
STRUCTURE_HINTS = re.compile(
    r"((?<![a-z])struktur(?![a-z])|(?<![a-z])structure(?![a-z])"
    r"|konzernstruktur|unternehmensstruktur|firmenstruktur|gesellschaftsstruktur"
    r"|auf-einen-blick|at-a-glance|our-companies|group-companies"
    r"|beteiligungen|tochtergesellschaft|subsidiar"
    r"|/gruppe/?$|/group/?$|/companies/?$|/divisions/?$)", re.I)

# Pages that LOOK corporate but publish OTHER companies' names: press releases quote media,
# reference/transaction pages name clients, property pages name assets, career pages name tools.
# Anything matching this is never read as a structure page, whatever else it matches.
#
# `infra` leads this list, and it is belt-and-braces for the anchoring above: ANTI_HINTS is
# evaluated FIRST and hard-excludes, so even if a future edit loosens STRUCTURE_HINTS again, an
# infrastructure page can no longer be read as a group-structure page. Two independent barriers,
# because the single barrier is what failed on abakus-tk.de.
ANTI_HINTS = re.compile(
    r"(infrastruktur|infrastructure|infra"
    r"|newsroom|presse|press|news|mitteilung|publikation|referenz|reference|transaktion"
    r"|transaction|deal|case-stud|projekt|project|objekt|immobilie|expose|karriere|career"
    r"|job|stellen|archiv|blog|historie|history|geschichte|team|kontakt|contact|impressum"
    r"|datenschutz|privacy|recht|agb|terms|cookie|sitemap|suche|search|login|umfrage)", re.I)

# Share/tracking widgets masquerading as links.
# NB: do NOT match utm_ here. A campaign parameter is normal on a legitimate internal link —
# angermann.de links its own subsidiary as buerosuche.de/?utm_source=anghh, and an earlier version
# of this filter silently deleted a real subsidiary because of it.
WIDGET_RE = re.compile(r"(\bshare\b|sharer|addthis|addtoany|/intent/|share\.com|/share/)", re.I)

# Never treat these as subsidiaries: social, tooling, CDNs, standards bodies, gov, common SaaS.
#
# THE ABAKUS-TK.DE LESSON (2026-08): this set used to be the ONLY suppression, and it named
# `whatsapp.com` and `t.me` but not `wa.me`. A denylist that lives in one module protects one code
# path -- and `wa.me` could equally have arrived from a certificate SAN, a CT record or a refine
# answer, with nothing downstream to object. The authoritative list now lives in scope_deny.py and
# is enforced BOTH here (at harvest) and in shodan_recon._owns_apex (at the ownership gate), ahead
# of the group-structure assertion itself. What remains below is a local supplement, kept so this
# module still degrades sensibly if scope_deny is ever unavailable.
NOISE_APEX = {
    "facebook.com", "twitter.com", "x.com", "linkedin.com", "instagram.com", "youtube.com",
    "xing.com", "google.com", "gstatic.com", "googleapis.com", "gmail.com", "apple.com",
    "microsoft.com", "office.com", "adobe.com", "cloudflare.com", "jquery.com", "w3.org",
    "schema.org", "wordpress.org", "typo3.org", "creativecommons.org", "europa.eu",
    "whatsapp.com", "t.me", "telegram.me", "vimeo.com", "tiktok.com", "github.com",
    "mozilla.org", "wikipedia.org", "openstreetmap.org", "bing.com", "yahoo.com",
    # MEDIA. A structure or holding page routinely links a press mention ("as reported in ...").
    # A newspaper is never a Mittelstand subsidiary, and scanning one would be both a false
    # positive and an embarrassment. spiegel.de reached the live angermann.de run this way.
    "spiegel.de", "handelsblatt.com", "faz.net", "welt.de", "zeit.de", "sueddeutsche.de",
    "manager-magazin.de", "wiwo.de", "immobilien-zeitung.de", "iz.de", "thomas-daily.de",
    "bloomberg.com", "reuters.com", "ft.com", "wsj.com", "forbes.com", "cnbc.com",
    "n-tv.de", "ard.de", "zdf.de", "dpa.com", "presseportal.de", "finanzen.net",
}

# Public suffixes that need two labels kept (tiny built-in list; the estate is DACH-centric).
_MULTI = {"co.uk", "org.uk", "ac.uk", "gov.uk", "co.at", "or.at", "ch.ch", "com.au",
          "co.nz", "com.br", "co.jp", "com.tr", "com.pl", "com.ro"}


def _apex(host):
    """Registrable domain (eTLD+1). Delegates to psl.py so this module and shodan_recon can never
    disagree about what a 'domain' is -- the budget.gov.ru incident (2026-08) was caused by exactly
    such a hand-rolled 'last two labels' rule, which turned every federal ministry into one
    organisation. The local _MULTI table below is only a fallback if psl.py is unavailable."""
    h = (host or "").strip().lower().rstrip(".")
    h = h.split("/")[0].split(":")[0]
    if _PSL is not None:
        try:
            return _PSL.registrable(h) or ""
        except Exception:
            pass
    parts = [p for p in h.split(".") if p]
    if len(parts) < 2:
        return ""
    last2 = ".".join(parts[-2:])
    if last2 in _MULTI and len(parts) >= 3:
        return ".".join(parts[-3:])
    return last2


def _http(url, fetch=None):
    """GET -> text, or '' on ANY failure. Never raises: discovery is best-effort by contract."""
    if fetch is not None:
        try:
            return fetch(url) or ""
        except Exception:
            return ""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                   "Accept": "text/html,application/xhtml+xml"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            if int(getattr(r, "status", 200)) >= 400:
                return ""
            raw = r.read(1_500_000)
        for enc in ("utf-8", "latin-1"):
            try:
                return raw.decode(enc)
            except Exception:
                continue
    except Exception:
        pass
    return ""


def _links(html, base):
    """[(absolute_url, anchor_text)] for every href on the page."""
    out = []
    for m in re.finditer(r'<a\b[^>]*?href=["\']([^"\'>]+)["\'][^>]*>(.*?)</a>', html or "",
                         re.I | re.S):
        href, text = m.group(1).strip(), re.sub(r"<[^>]+>", " ", m.group(2))
        if href.lower().startswith(("javascript:", "mailto:", "tel:", "#", "data:")):
            continue
        try:
            out.append((urllib.parse.urljoin(base, href),
                        re.sub(r"\s+", " ", _html.unescape(text)).strip()))
        except Exception:
            continue
    return out


def _brand_core(apex):
    """'angermann.de' -> 'angermann'. The label only; used for weak corroboration checks."""
    return (apex or "").split(".")[0].lower()


def discover(seed_apex, fetch=None, log=None, max_pages=MAX_PAGES):
    """
    Crawl the seed's own site for its corporate-structure pages and return the domains it links to.

    Returns {"seed":..., "strong":[{domain,why,source}], "weak":[...], "pages":[...], "org_names":[...]}
    STRONG  = linked from a page that describes the group structure -> eligible for scope
    WEAK    = linked from elsewhere on the site -> context only, offered to the operator
    """
    say = log or (lambda m: print(m, file=sys.stderr))
    seed_apex = _apex(seed_apex) or (seed_apex or "").lower()
    if not seed_apex:
        return {"seed": "", "strong": [], "weak": [], "pages": [], "org_names": []}

    roots = ["https://www.%s/" % seed_apex, "https://%s/" % seed_apex]
    home, home_url = "", ""
    for r in roots:
        home = _http(r, fetch)
        if home:
            home_url = r
            break
    if not home:
        say("[group] %s: homepage unreachable - no structure discovery (fails closed)" % seed_apex)
        return {"seed": seed_apex, "strong": [], "weak": [], "pages": [], "org_names": []}

    # 1) find candidate STRUCTURE pages: same-site links whose URL or anchor text looks like
    #    a corporate-structure page. The homepage itself always counts as a weak source.
    # Selection is deliberately STRICT and URL-anchored. Anchor TEXT is not enough: the string
    # "Gruppe" appears in the nav of every page on a German corporate site, which is how the first
    # version wandered into the newsroom. The URL PATH is what identifies a structure page.
    struct_urls, seen_u = [], set()
    for url, text in _links(home, home_url):
        pu = urllib.parse.urlparse(url)
        if _apex(pu.netloc) != seed_apex:
            continue
        path = pu.path or "/"
        if ANTI_HINTS.search(path):
            continue                        # press/references/careers publish OTHER companies
        if not STRUCTURE_HINTS.search(path):
            continue                        # must be structural in the PATH, not merely in the nav text
        if url in seen_u:
            continue
        seen_u.add(url)
        struct_urls.append(url)
    struct_urls = struct_urls[:max_pages]

    # 2) harvest EXTERNAL domains from those pages (strong) and from the homepage (weak)
    strong, weak, pages, org_names = {}, {}, [], []

    denied_seen = {}

    def _harvest(html, src_url, bucket, why):
        for url, text in _links(html, src_url):
            apex = _apex(urllib.parse.urlparse(url).netloc)
            if not apex or apex == seed_apex or apex in NOISE_APEX:
                continue
            # THE ABAKUS GATE. `wa.me` in a site footer is not a subsidiary; it is the WhatsApp
            # click-to-chat shortener, and admitting it put 236 Meta hosts into a 20-person
            # reseller's deck. Recorded rather than silently dropped, so the log explains itself.
            if _denied(apex):
                denied_seen[apex] = _deny_why(apex) or "denied"
                continue
            if WIDGET_RE.search(url) or WIDGET_RE.search(apex):
                continue                    # xing-share.com et al are widgets, not subsidiaries
            if apex in bucket:
                continue
            bucket[apex] = {"domain": apex, "why": why, "source": src_url,
                            "anchor": (text or "")[:80]}
            if text and len(text) > 3:
                org_names.append(text[:80])

    for u in struct_urls:
        html = _http(u, fetch)
        if not html:
            continue
        pages.append(u)
        _harvest(html, u, strong, "linked from the customer's own group-structure page")
    _harvest(home, home_url, weak, "linked from the customer's homepage (not a structure page)")

    # a domain promoted to strong must not also sit in weak
    for d in list(weak):
        if d in strong:
            weak.pop(d, None)

    s = sorted(strong.values(), key=lambda x: x["domain"])[:MAX_CANDIDATES]
    w = sorted(weak.values(), key=lambda x: x["domain"])[:MAX_CANDIDATES]
    say("[group] %s: %d structure page(s) -> %d group domain(s), %d other site link(s)"
        % (seed_apex, len(pages), len(s), len(w)))
    if s:
        say("[group] group domains: %s" % ", ".join(x["domain"] for x in s))
    if denied_seen:
        say("[group] DENIED %d shared-infrastructure apex(es) (never a subsidiary): %s"
            % (len(denied_seen),
               ", ".join("%s (%s)" % (k, v) for k, v in sorted(denied_seen.items())[:8])))
    return {"seed": seed_apex, "strong": s, "weak": w, "pages": pages,
            "denied": sorted(denied_seen), "org_names": sorted(set(org_names))[:40]}


def main():
    ap = argparse.ArgumentParser(description="Discover a company's subsidiary domains from its own "
                                             "group-structure pages (first-party evidence).")
    ap.add_argument("seed", help="seed apex, e.g. angermann.de")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    res = discover(a.seed)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print("\nGROUP DOMAINS (strong - first-party structure page):")
        for x in res["strong"]:
            print("  %-32s  %s" % (x["domain"], x["anchor"]))
        print("\nOTHER SITE LINKS (weak - context only, never auto-scoped):")
        for x in res["weak"]:
            print("  %-32s  %s" % (x["domain"], x["anchor"]))


if __name__ == "__main__":
    main()
