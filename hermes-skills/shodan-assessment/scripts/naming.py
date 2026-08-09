"""naming.py — learn the target's own hostname grammar, then generate candidates from it.

THE INSIGHT, from the ns03.ru engagement: a blind subdomain dictionary is close to useless. `vpn`,
`portal`, `remote`, `lk`, `owa` all returned NXDOMAIN. But Certificate Transparency revealed the
customer's actual grammar:

    srv-kap-gt.ns03.ru      ->  srv-<site>-<role>.<domain>
    ventil.nzn.ns03.ru      ->  <service>.<site>.<domain>

Once the grammar is known, candidates come from the target's OWN vocabulary — a few hundred
high-probability names instead of a ten-thousand-word blind list. Recall goes up and query volume
goes down at the same time.

LANGUAGE FOLLOWS THE TARGET, NOT THE PRODUCT. `ventil` (вентиляция) and `kotel` (котельная) are
building-services hosts that appear in no English wordlist, and `lueftung` / `heizung` appear in no
Russian one. But querying all seven languages against every target is waste: as the operator put it,
if the company does not operate in a country that speaks the language, there is no reason to ask.
So the language set is DERIVED from the target's own evidence — ccTLDs, the countries its estate is
hosted in, and the jurisdiction the engine already resolved — and English is always included
because it is the lingua franca of infrastructure naming.

ZERO PACKETS TO THE TARGET. A candidate is tested by RESOLVING it, which asks a public DNS resolver.
Nothing is sent to the customer's infrastructure, so this stays in the default tier.
"""
import re

# Role suffixes and host prefixes. These are near-universal in enterprise naming and are not
# language-specific: they come from the vendor documentation everyone copies.
ROLES = ("gt", "gw", "fw", "dc", "sql", "db", "ts", "rds", "app", "web", "bck", "bak", "vpn",
         "px", "proxy", "lb", "dmz", "mail", "srv", "esx", "nas", "san", "adfs", "ca")
PREFIXES = ("srv", "vm", "host", "node", "sv", "s")

# Service vocabularies. Deliberately SHORT and high-signal: every entry costs one DNS query per
# apex per site code, so a bloated list is the blind dictionary this module exists to replace.
LANG_SERVICES = {
    "en": ("vpn", "mail", "portal", "remote", "gateway", "backup", "monitor", "camera", "cctv",
           "hvac", "bms", "print", "files", "cloud", "intranet", "erp", "crm", "wiki", "git",
           "jira", "vc", "access", "badge", "heating", "energy", "warehouse", "hr", "finance"),
    "de": ("wartung", "lueftung", "luftung", "heizung", "klima", "drucker", "kamera", "zutritt",
           "technik", "verwaltung", "lager", "personal", "buchhaltung", "energie", "leitstand",
           "gebaeude", "werk", "produktion", "vertrieb", "einkauf", "fernwartung", "zeiterfassung"),
    "ru": ("ventil", "ventilyaciya", "kotel", "kotelnaya", "skud", "energo", "teplo", "voda",
           "ohrana", "sklad", "buh", "kadry", "zavod", "proizvodstvo", "dispetcher", "kamera",
           "svyaz", "elektro", "nasos", "ing", "avtomatika", "uchet"),
    "fr": ("chauffage", "ventilation", "camera", "impression", "acces", "gestion", "entrepot",
           "comptabilite", "maintenance", "usine", "production", "energie", "climatisation"),
    "es": ("calefaccion", "ventilacion", "camara", "acceso", "gestion", "almacen", "contabilidad",
           "mantenimiento", "fabrica", "produccion", "energia", "climatizacion"),
    "it": ("riscaldamento", "ventilazione", "telecamera", "accesso", "gestione", "magazzino",
           "contabilita", "manutenzione", "fabbrica", "produzione", "energia", "climatizzazione"),
    "pl": ("ogrzewanie", "wentylacja", "kamera", "dostep", "magazyn", "ksiegowosc", "produkcja",
           "utrzymanie", "fabryka", "energia", "klimatyzacja", "serwerownia"),
}

# Which language a country's infrastructure is likely to be named in. Only entries we can defend;
# an unknown country contributes nothing rather than guessing.
COUNTRY_LANG = {
    "DE": "de", "AT": "de", "CH": "de", "LI": "de",
    "RU": "ru", "BY": "ru", "KZ": "ru", "KG": "ru",
    "FR": "fr", "BE": "fr", "LU": "fr", "MC": "fr",
    "ES": "es", "MX": "es", "AR": "es", "CL": "es", "CO": "es", "PE": "es",
    "IT": "it", "SM": "it",
    "PL": "pl",
}
# ccTLD -> country, for the TLDs whose language differs from the obvious reading.
TLD_COUNTRY = {"de": "DE", "at": "AT", "ch": "CH", "ru": "RU", "su": "RU", "by": "BY", "kz": "KZ",
               "fr": "FR", "be": "BE", "es": "ES", "mx": "MX", "it": "IT", "pl": "PL"}


def langs_for(domains=(), countries=(), country=None, max_langs=3):
    """Which service vocabularies to use for THIS target.

    English is always included: it is the lingua franca of infrastructure naming, and even a purely
    German or Russian estate uses `vpn` and `mail`. Everything else must be EARNED by evidence that
    the company operates there — its own ccTLDs, the countries its estate is hosted in, or the
    jurisdiction already resolved for the compliance regime set.

    Capped, because each language multiplies the query count and the point of this module is FEWER
    queries than a blind dictionary, not more.
    """
    langs, seen = ["en"], {"en"}
    votes = []
    for d in (domains or []):
        tld = str(d).rsplit(".", 1)[-1].lower()
        if tld in TLD_COUNTRY:
            votes.append(TLD_COUNTRY[tld])
    votes += [str(c).upper() for c in (countries or []) if c]
    if country:
        votes.append(str(country).upper())
    for cc in votes:
        lg = COUNTRY_LANG.get(cc)
        if lg and lg not in seen:
            seen.add(lg)
            langs.append(lg)
        if len(langs) >= max_langs:
            break
    return langs


def _labels(host, apex):
    """The labels of `host` below `apex`, e.g. ventil.nzn.ns03.ru under ns03.ru -> [ventil, nzn]."""
    h, a = str(host).lower().rstrip("."), str(apex).lower().rstrip(".")
    if not h.endswith("." + a):
        return []
    return h[: -(len(a) + 1)].split(".")


def learn(names, apexes):
    """Reconstruct the grammar from names the target itself published (CT, DNS, certificates).

    Returns site codes (a label that appears as a ZONE under the apex, i.e. something is named
    *under* it), role tokens seen after a `srv-`-style prefix, and the service words already in use.
    """
    sites, roles, services, prefixes = {}, {}, {}, set()
    for nm in names or []:
        for ap in apexes or []:
            labs = _labels(nm, ap)
            if not labs:
                continue
            # <service>.<site>.<apex>: the RIGHTMOST label is a site zone because something is
            # published beneath it. One label is just a service on the apex.
            # srv-<site>-<role> is a COMPOUND, and it must be decomposed BEFORE the service pass.
            # Treating "srv-kap-gt" as a service word generated "srv-kap-gt.nzn.ns03.ru", which is
            # not a name anybody would ever configure -- the grammar has to be parsed, not tokenised.
            m = re.match(r"^([a-z]{1,6})-([a-z0-9]{2,10})-([a-z0-9]{1,6})$", labs[0])
            if m:
                prefixes.add(m.group(1))
                sites[m.group(2)] = sites.get(m.group(2), 0) + 1
                roles[m.group(3)] = roles.get(m.group(3), 0) + 1
            else:
                services[labs[0]] = services.get(labs[0], 0) + 1
            if len(labs) >= 2:
                sites[labs[-1]] = sites.get(labs[-1], 0) + 1
            break
    # A trailing digit is a sequence, not a distinct service: ventil2 tells us ventil<N> exists.
    seq = {re.sub(r"\d+$", "", s) for s in services if re.search(r"\d$", s)}
    return {"sites": sorted(sites, key=lambda k: -sites[k]),
            "roles": sorted(roles, key=lambda k: -roles[k]),
            "services": sorted(services, key=lambda k: -services[k]),
            "prefixes": sorted(prefixes),
            "sequenced": sorted(seq)}


def candidates(grammar, apexes, langs=("en",), cap=400, known=()):
    """High-probability hostnames, built from the target's grammar and its own languages.

    The cap is the whole point. An uncapped cross-product of services x sites x apexes is the blind
    dictionary again, one level up.
    """
    out = []
    # A name we already hold is not a candidate -- resolving it again spends a query to learn
    # something we knew before we started.
    seen = {str(k).lower().strip(".") for k in (known or [])}

    def add(name):
        n = name.lower().strip(".")
        if n and n not in seen and len(out) < cap:
            seen.add(n)
            out.append(n)

    vocab = []
    for lg in langs:
        vocab.extend(LANG_SERVICES.get(lg, ()))
    # The target's OWN service words rank first: they are evidence, not vocabulary.
    vocab = list(dict.fromkeys(list(grammar.get("services") or []) + vocab))
    sites = list(grammar.get("sites") or [])
    prefixes = list(grammar.get("prefixes") or []) or ["srv"]

    for ap in apexes or []:
        # <service>.<site>.<apex> -- only for site codes the target actually uses.
        for site in sites[:4]:
            for svc in vocab[:60]:
                add("%s.%s.%s" % (svc, site, ap))
        # <prefix>-<site>-<role>.<apex>
        for pre in prefixes[:2]:
            for site in sites[:4]:
                for role in (list(grammar.get("roles") or []) + list(ROLES))[:18]:
                    add("%s-%s-%s.%s" % (pre, site, role, ap))
        # A sequence seen once usually has siblings: ventil, ventil2 -> ventil3.
        for base in (grammar.get("sequenced") or []):
            for n in (2, 3, 4):
                for site in sites[:3]:
                    add("%s%d.%s.%s" % (base, n, site, ap))
                add("%s%d.%s" % (base, n, ap))
    return out
