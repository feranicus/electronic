#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_targets.py — turn a LinkedIn Connections.csv export into a PRIORITISED target list.

    python marketing/campaign/build_targets.py --csv <path to Connections.csv>

WHY A SCRIPT AND NOT A ONE-OFF SORT: the export is refreshed every few weeks, and the segment and
role rules are the campaign's actual thesis. Both belong in a file that can be re-run and argued
with, not in a spreadsheet somebody hand-sorted once.

WHAT IT DECIDES, and it only ever decides these two things:
  SEGMENT — who they sell FOR   (channel partner, GSI, consultancy, security vendor, carrier)
  ROLE    — what they do        (sales / presales / exec / delivery / other)
The message is chosen by SEGMENT x ROLE, because "sell me the pen" to a Cognizant delivery partner
and to a Sophos founder are different pens.

SCORING IS DELIBERATELY BORING. Segment fit + role fit + a small recency bonus. No ML, no scraping
beyond the file the operator exported themselves. A score you cannot explain to the person you are
about to message is a score you should not act on.
"""
import argparse, csv, io, json, os, re, sys, collections
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------- segments
# Named companies first (exact-ish), then keyword fallbacks. Order matters: a security VENDOR that
# is also a reseller is a vendor, because the pitch differs.
GSI = ["cognizant", "accenture", "infosys", "wipro", "tata consultancy", "tcs", "capgemini",
       "atos", "ntt data", "dxc", "hcl", "tech mahindra", "unisys", "kyndryl", "sopra steria",
       "globant", "epam", "luxoft", "reply", "cgi", "fujitsu", "computacenter"]
BIG4 = ["deloitte", "pwc", "pricewaterhouse", "ernst & young", "ernst and young", " ey ", "kpmg"]
CONSULT = BIG4 + ["bdo", "mazars", "forvis", "baker tilly", "grant thornton", "rsm ", "crowe",
                  "moore global", "nexia", "pkf", "bearingpoint", "roland berger", "mckinsey",
                  "bain ", "boston consulting", "oliver wyman", "kearney", "alixpartners"]
VENDOR = ["sophos", "palo alto", "fortinet", "crowdstrike", "sentinelone", "trellix", "mcafee",
          "rapid7", "tenable", "qualys", "darktrace", "check point", "checkpoint", "trend micro",
          "watchguard", "barracuda", "arctic wolf", "proofpoint", "mimecast", "zscaler", "netskope",
          "cloudflare", "akamai", "f5 ", "imperva", "varonis", "cybereason", "kaspersky", "eset",
          "bitdefender", "sailpoint", "cyberark", "okta", "beyondtrust", "thales", "entrust",
          "digicert", "venafi", "recorded future", "mandiant", "secureworks", "bitsight",
          "securityscorecard", "upguard", "panorays", "riskrecon", "shodan", "censys", "cycognito",
          "randori", "intrigue", "bishop fox", "horizon3", "pentera", "picus", "safebreach",
          "attackiq", "cymulate", "xm cyber", "nozomi", "claroty", "dragos", "armis", "forescout",
          "cognyte", "verint", "nice actimize", "group-ib", "socradar", "intel471", "flashpoint"]
CARRIER = ["colt technology", "deutsche telekom", "t-systems", "orange busin", "bt group",
           "vodafone", "telefonica", "telefónica", "verizon", "at&t", "lumen", "ntt communications",
           "telia", "telenor", "kpn", "proximus", "swisscom", "a1 telekom", "cogent", "gtt",
           "zayo", "euNetworks", "eunetworks", "level 3", "singtel", "telstra"]
# A GENERIC WORD IS NOT A SEGMENT ANCHOR. The first cut used "consult", "distribution" and
# "integrator" as bare substrings and the top of the list came back as AlphaConsult-Gruppe (a
# staffing agency), BEC-Breddermann Executive (headhunters), Altium Biotech Consulting and ADNOC
# Distribution (an oil company). Exactly the failure the assessment engine already pays for with
# brand tokens: a common word matches half the market.
#
# So there are two tiers. SELF-EVIDENT terms name the business outright and stand alone. AMBIGUOUS
# terms only count when a technology signal CORROBORATES them, in the company name or the person's
# own title. "Consulting" plus "Cyber Security Director" is a target; "Consulting" plus "Recruitment
# Consultant" is not.
CHANNEL_STRONG = ["msp", "mssp", "managed service", "managed security", "value added reseller",
                  "value-added reseller", "systems integrator", "system integrator",
                  "solutions provider", "it services", "it service", "it-service", "systemhaus",
                  "security operations", "cyber defen", "cyberdefen", "cyber-defen",
                  "cybersecurity", "cyber security", "infosec", "penetration testing"]
# THE BIGGEST RESELLERS AND DISTRIBUTORS IN EUROPE HAVE NAMES THAT SAY NOTHING. Softcat, Bytes,
# Bechtle and Exclusive Networks are the literal channel and no keyword rule will ever find them,
# because their brand is a word. Precision without recall is just a different way of being wrong,
# so the ambiguity is resolved the only honest way available: by naming them.
CHANNEL_NAMED = ["softcat", "bytes technology", "bytes software", "computacenter", "insight direct",
                 "insight enterprises", "shi international", "cdw", "presidio", "trustmarque",
                 "phoenix software", "bechtle", "cancom", "datagroup", "axians", "nomios",
                 "telefonica tech", "telefónica tech", "orange cyberdefense", "ricoh", "konica",
                 "arrow electronics", "arrow ecs", "td synnex", "synnex", "ingram micro",
                 "exclusive networks", "westcon", "comstor", "nuvias", "infinigate", "also ",
                 "api technology", "climb global", "e92plus", "prianto", "wick hill",
                 "controlware", "sva ", "adesso", "msg systems", "materna", "bridgingit",
                 "netzlink", "consist", "allgeier", "q-perior", "arvato systems"]
CHANNEL_WEAK = ["consult", "distribution", "distributor", "integrator", "reseller", "partner",
                "solutions", "services"]
TECH_SIGNAL = ["it ", " it", "ict", "cyber", "security", "network", "cloud", "digital", "tech",
               "data", "soc", "infrastructure", "software", "systems", "telecom", "hosting",
               "datacent", "managed", "siem", "edr", "xdr", "zero trust", "compliance", "nis2",
               "risk", "audit", "penetration", "pentest", "grc"]

# Hyperscalers get their own bucket. They are not resellers of an assessment and they are not a
# security vendor; they are a partner ecosystem with a different motion, and 199 AWS contacts would
# otherwise dominate the top of the list purely by alphabet.
HYPER = ["amazon web services", "aws ", "microsoft", "google cloud", "google", "oracle cloud",
         "alibaba cloud", "ibm cloud"]

SEGMENTS = [("GSI", GSI), ("CONSULTING", CONSULT), ("VENDOR", VENDOR), ("HYPERSCALER", HYPER),
            ("CARRIER", CARRIER)]

# ---------------------------------------------------------------------------- roles
SALES = ["account executive", "account manager", "account director", "sales", "business development",
         "bdm", "bdr", "commercial", "revenue", "channel manager", "partner manager", "alliance",
         "client partner", "client director", "customer success", "key account"]
PRESALES = ["pre-sales", "presales", "pre sales", "solution architect", "solutions architect",
            "solution engineer", "sales engineer", "solution consultant", "technical account",
            "solutions consultant", "principal architect", "enterprise architect", "se manager",
            "technical sales", "bid manager", "proposal"]
# EXEC IS SPLIT IN TWO, AND THE ORDER IS THE WHOLE POINT. "Director" and "Head of" are generic:
# they appear in "Global Account Director DTAG" and "Head of Sales", who carry a number and whose
# pain is booking meetings, not opening a new revenue line. Measured on the real export, 43 of 374
# people labelled EXEC had an explicitly SALES title and would have received the wrong pitch.
# So C-level and ownership win outright, then an explicit sales title, then the generic words.
EXEC_HARD = ["chief", "ceo", "cto", "ciso", "cro", "coo", "cfo", "founder", "co-founder", "owner",
             "president", "managing director", "geschäftsführer", "geschaftsfuhrer",
             "vice president", "vp", "board member", "general manager", "country manager"]
SALES_TITLES = ["account director", "account manager", "account executive", "client director",
                "client partner", "channel director", "channel manager", "channel sales",
                "partner manager", "partner director", "partner sales", "sales director",
                "sales manager", "head of sales", "key account", "alliance manager",
                "alliance director", "business development manager",
                "business development director", "regional sales"]
EXEC = ["partner", "head of", "director", "board", "gm ", "regional director"]
DELIVERY = ["engineer", "consultant", "analyst", "architect", "specialist", "administrator",
            "developer", "researcher", "penetration", "pentest", "red team", "soc analyst"]


# A TOKEN MUST START A WORD. The first cut used bare `in`, so "it " matched inside "Clalit Health
# Services" (a hospital) and "tech" matched inside "Altium Biotech Consulting". Both cleared the
# corroboration test and landed at the top of the queue. This is the same defect the assessment
# engine has already paid for twice, with "abakus" inside "abakusconsulting" and "struktur" inside
# "infrastruktur": a short token used as a bare substring eventually matches somebody else's word.
#
# The lookbehind is the whole fix. Matching is still a PREFIX match at the front of a word, so
# "consult" keeps finding consulting and consultancy and "distribut" keeps finding distribution,
# which is what these lists are written to do.
_RX = {}


def _has(hay, needles):
    for n in needles:
        rx = _RX.get(n)
        if rx is None:
            # A trailing space in a token means "this word ends here". It must accept the separators
            # a company name really uses: "IT-Systemhaus", "IT&Services", "F5, Inc". Requiring a
            # literal space lost Bechtle IT-Systemhaus, which is Germany's largest IT reseller.
            rx = _RX[n] = re.compile(r"(?<![a-z0-9])" + re.escape(n.strip()) +
                                     (r"(?![a-z0-9])" if n.endswith(" ") else ""))
        if rx.search(hay):
            return True
    return False


# NEVER A TARGET, whatever else matches. Recruiters and staffing firms carry "Consulting",
# "Solutions" and "Partners" in their names and "IT"/"Cyber"/"Tech" in their titles, so they clear
# every keyword test and they cannot resell an assessment to anybody.
NEVER = ["recruit", "talent", "staffing", "personalberatung", "headhunt", "executive search",
         "personaldienst", "zeitarbeit", "hr consult", "human resources", "career", "job board"]


def segment_of(company, position):
    c = " %s " % (company or "").lower()
    p = " %s " % (position or "").lower()
    if _has(c, NEVER) or _has(p, NEVER):
        return "OTHER"
    for name, keys in SEGMENTS:
        if _has(c, keys):
            return name
    # ...ON THE COMPANY ONLY. Matching these against the TITLE made "Director of Cybersecurity
    # Audit, Barclays" a channel partner. He is a BUYER: the best kind of prospect, and the wrong
    # pitch entirely. What a person does is not what their employer sells.
    if _has(c, CHANNEL_STRONG) or _has(c, CHANNEL_NAMED):
        return "CHANNEL"
    # THE CORROBORATION MUST BE IN THE COMPANY, NOT THE TITLE. Allowing the title to corroborate
    # admitted "Head of IT, ADNOC Distribution" (an oil company) and "Altium Biotech Consulting":
    # their PEOPLE are technical, their BUSINESS is not reselling security. A job title tells you
    # what one person does; the segment is a property of the firm.
    if _has(c, CHANNEL_WEAK) and _has(c, TECH_SIGNAL):
        return "CHANNEL"                    # ambiguous word, corroborated by the company itself
    # A channel ROLE is about selling THROUGH partners, so the title alone can qualify — but only
    # when it is unambiguously a channel job, not merely a technical one.
    if _has(p, ["msp partner", "mssp", "channel manager", "channel director", "channel sales",
                "partner manager", "partner director", "alliance manager", "alliance director"]):
        return "CHANNEL"
    return "OTHER"


def role_of(position):
    p = " %s " % (position or "").lower()
    # PRESALES before SALES: "sales engineer" is presales, and it contains "sales".
    if _has(p, PRESALES):
        return "PRESALES"
    if _has(p, EXEC_HARD):          # a VP or a founder is the economic buyer, whatever else fits
        return "EXEC"
    if _has(p, SALES_TITLES):       # beats the generic "director" / "head of" below
        return "SALES"
    if _has(p, EXEC):
        return "EXEC"
    if _has(p, SALES):
        return "SALES"
    if _has(p, DELIVERY):
        return "DELIVERY"
    return "OTHER"


# Segment weight = how directly they can RESELL an assessment. Role weight = who signs or who
# feels the pain. Both are judgement calls and are stated here so they can be argued with.
SEG_W = {"CHANNEL": 40, "GSI": 36, "CONSULTING": 34, "VENDOR": 30, "CARRIER": 26,
         "HYPERSCALER": 14, "OTHER": 0}
ROLE_W = {"EXEC": 30, "SALES": 28, "PRESALES": 26, "DELIVERY": 8, "OTHER": 4}


def score(seg, role, connected_on):
    s = SEG_W.get(seg, 0) + ROLE_W.get(role, 0)
    # A recent connection remembers you. Small, capped, never the deciding factor.
    try:
        d = datetime.strptime((connected_on or "").strip(), "%d %b %Y")
        yrs = (datetime.now() - d).days / 365.0
        s += max(0, int(10 - yrs * 2))
    except Exception:
        pass
    return s


def load(path):
    raw = open(path, encoding="utf-8-sig").read().splitlines()
    i = next(n for n, l in enumerate(raw) if l.startswith("First Name,"))
    return list(csv.DictReader(io.StringIO("\n".join(raw[i:]))))


# OPERATOR DECISION (2026-08-22): Colt is out of the campaign entirely. 396 connections and the
# single biggest block in the file, but they are ex-colleagues, not a market: a partner pitch to
# people who worked with you reads wrong, and the relationship is worth more than the send. Other
# carriers (Deutsche Telekom, T-Systems, Vodafone, Cogent) stay - they are a real reseller channel.
EXCLUDE_COMPANIES = ["colt technology", "colt group", "colt data centre"]


def build(rows):
    out = []
    for r in rows:
        if any(x in (r.get("Company") or "").lower() for x in EXCLUDE_COMPANIES):
            continue
        url = (r.get("URL") or "").strip()
        if not url:
            continue                      # no profile = nothing to open; not a target
        comp, pos = (r.get("Company") or "").strip(), (r.get("Position") or "").strip()
        seg = segment_of(comp, pos)
        if seg == "OTHER":
            continue
        role = role_of(pos)
        out.append({
            "first": (r.get("First Name") or "").strip(),
            "last": (r.get("Last Name") or "").strip(),
            "company": comp, "position": pos, "url": url,
            "email": (r.get("Email Address") or "").strip(),
            "segment": seg, "role": role,
            "connected_on": (r.get("Connected On") or "").strip(),
            "score": score(seg, role, r.get("Connected On")),
            "message_key": "%s_%s" % (seg, role),
        })
    out.sort(key=lambda x: (-x["score"], x["company"].lower(), x["last"].lower()))
    for n, t in enumerate(out, 1):
        t["rank"] = n
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--out", default=HERE)
    ap.add_argument("--top", type=int, default=0, help="also write a top-N shortlist")
    a = ap.parse_args()

    rows = load(a.csv)
    tg = build(rows)
    os.makedirs(a.out, exist_ok=True)

    jp = os.path.join(a.out, "targets.json")
    json.dump(tg, open(jp, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    cp = os.path.join(a.out, "targets.csv")
    with open(cp, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(tg[0].keys()))
        w.writeheader(); w.writerows(tg)

    print("connections read : %d" % len(rows))
    print("in-scope targets : %d  (%.0f%%)" % (len(tg), 100.0 * len(tg) / max(1, len(rows))))
    print()
    seg = collections.Counter(t["segment"] for t in tg)
    role = collections.Counter(t["role"] for t in tg)
    print("by segment:"); [print("   %-11s %4d" % (k, v)) for k, v in seg.most_common()]
    print("by role   :"); [print("   %-11s %4d" % (k, v)) for k, v in role.most_common()]
    print()
    print("message buckets (segment x role), the ones that need their own copy:")
    for k, v in collections.Counter(t["message_key"] for t in tg).most_common(12):
        print("   %-20s %4d" % (k, v))
    print()
    print("wrote %s  and  %s" % (jp, cp))
    if a.top:
        sp = os.path.join(a.out, "shortlist_top%d.csv" % a.top)
        with open(sp, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(tg[0].keys()))
            w.writeheader(); w.writerows(tg[:a.top])
        print("wrote %s" % sp)


if __name__ == "__main__":
    main()
