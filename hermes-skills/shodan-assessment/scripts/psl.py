"""psl.py — the REGISTRABLE domain (eTLD+1), which is what "same owner" actually means.

THE budget.gov.ru INCIDENT (2026-08). `_apex()` was one line:

    def _apex(d):
        p = d.split('.'); return ".".join(p[-2:])

so `budget.gov.ru` resolved to **`gov.ru`** — and therefore so did `duma.gov.ru`, `nalog.gov.ru`,
`mchs.gov.ru`, `fssp.gov.ru` and every other Russian ministry. The ownership gate then agreed that
the whole federal government was one customer: 203 IPs, 12 findings, €11-28M of priced risk, for a
request about ONE budget-transparency site. The same line would turn `bbc.co.uk` into `co.uk` and
`example.com.au` into `com.au`.

`gov.ru`, `co.uk`, `com.au` are PUBLIC SUFFIXES: nobody owns them, anyone can register under them.
Two names sharing a public suffix share nothing at all. Getting this wrong does not merely widen
scope — it inverts the meaning of the ownership test that the whole zero-false-positive design
rests on.

TWO SOURCES, in order:
  1. `data/public_suffix_list.dat` — the OFFICIAL list, if it has been fetched. `python update_psl.py`
     downloads it from publicsuffix.org and commits it. Evidence beats memory, and this file is the
     evidence.
  2. A committed structural RULE, used when that file is absent. It does not enumerate zones (a
     hand-typed zone list is exactly the kind of remembered fact that goes stale and is wrong in
     ways nobody notices). It encodes the observation that makes the class recognisable: under a
     TWO-LETTER country code, a second label drawn from the small set of ADMINISTRATIVE labels
     (gov, co, com, ac, edu, mil, gouv, govt, ...) is a public suffix, not a registration.

Fail direction: when unsure we take MORE labels, i.e. a NARROWER estate. A narrow estate misses
some of the customer's own hosts; a wide one puts a stranger's infrastructure in their deck. The
first is a recall bug, the second is the incident this file exists to prevent.
"""
from __future__ import annotations

import os

HERE = os.path.dirname(os.path.abspath(__file__))
_PSL_FILE = os.path.join(HERE, "data", "public_suffix_list.dat")

# Administrative second-level labels. These are ROLES ("this is the government part of the country's
# namespace"), not registrations, which is why the set generalises across countries instead of
# needing one entry per zone.
_ADMIN_SLD = {
    # government / state
    "gov", "gob", "gouv", "govt", "go", "gv", "gc", "gub", "gok", "gon", "gop", "gos", "mil",
    "mod", "idf", "police", "parliament", "muni", "int",
    # commercial / general
    "co", "com", "net", "org", "or", "ne", "biz", "info", "name", "nom", "pro", "web", "firm",
    "gen", "ind", "ltd", "plc", "asn", "id", "per", "idv", "priv", "pvt", "fam", "tur", "coop",
    # education / research / health
    "ac", "edu", "ed", "sch", "school", "k12", "res", "re", "eun", "sci", "med", "sld", "health",
    "nhs", "hs", "ms", "es", "sc", "kg", "ad", "gr", "lg",
    # misc real second levels
    "art", "tv", "press", "pub", "red", "inf", "club", "game", "ebiz", "ngo", "mobi", "geek",
    "kiwi", "maori", "iwi", "desa", "my", "in", "pp", "test", "csiro", "me",
}


def _load_official():
    """Parse the committed PSL if present -> set of suffix rules. Cheap, done once."""
    rules = set()
    try:
        with open(_PSL_FILE, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("//"):
                    continue
                rules.add(line)
    except OSError:
        return None
    return rules or None


_RULES = None
_LOADED = False


def _rules():
    global _RULES, _LOADED
    if not _LOADED:
        _RULES = _load_official()
        _LOADED = True
    return _RULES


def public_suffix(host: str) -> str:
    """The public suffix of `host` — the part nobody can own."""
    labels = [x for x in (host or "").strip().strip(".").lower().split(".") if x]
    if len(labels) < 2:
        return ".".join(labels)
    rules = _rules()
    if rules:
        # Official algorithm, simplified to the parts that matter here: longest matching rule wins;
        # an exception rule (!) shortens it by one label; a wildcard (*) lengthens it by one.
        best = 1
        for i in range(len(labels)):
            cand = ".".join(labels[i:])
            if ("!" + cand) in rules:
                return ".".join(labels[i + 1:])
            if cand in rules:
                best = max(best, len(labels) - i)
            wild = ".".join(["*"] + labels[i + 1:])
            if wild in rules:
                best = max(best, len(labels) - i)
        return ".".join(labels[len(labels) - best:])
    # Structural fallback — see the module docstring. Note the `>= 2`, not `>= 3`: `gov.ru` given on
    # its own IS a public suffix, and saying so is what lets the caller REFUSE to assess a whole
    # country's namespace. Requiring three labels here made `is_public_suffix("gov.ru")` false and
    # left that door open.
    if len(labels) >= 2 and len(labels[-1]) == 2 and labels[-2] in _ADMIN_SLD:
        return ".".join(labels[-2:])
    return labels[-1]


def registrable(host: str) -> str:
    """eTLD+1 — the unit of OWNERSHIP. `budget.gov.ru` -> `budget.gov.ru`, `www.bbc.co.uk` -> `bbc.co.uk`."""
    h = (host or "").strip().strip(".").lower()
    labels = [x for x in h.split(".") if x]
    if len(labels) < 2:
        return h
    suf = public_suffix(h)
    sl = suf.split(".")
    if len(labels) <= len(sl):
        return h                      # the host IS a public suffix — nothing registrable below it
    return ".".join(labels[-(len(sl) + 1):])


def is_public_suffix(host: str) -> bool:
    """True when the NAME ITSELF is a public suffix (gov.ru, co.uk) — never a customer estate."""
    h = (host or "").strip().strip(".").lower()
    return bool(h) and h == public_suffix(h)


if __name__ == "__main__":
    for h in ("budget.gov.ru", "duma.gov.ru", "gov.ru", "www.bbc.co.uk", "bbc.co.uk",
              "example.com.au", "ecolines.lv", "skon.de", "gitlab.bibel.tv", "mail.ecolines.net",
              "rt-solar.ru", "a.b.c.example.co.jp"):
        print("%-24s suffix=%-10s registrable=%-22s is_suffix=%s"
              % (h, public_suffix(h), registrable(h), is_public_suffix(h)))
