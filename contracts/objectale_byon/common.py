# -*- coding: utf-8 -*-
"""Shared facts and the block vocabulary for the objectale -> byon contract pack.

WHY THE CONTENT IS DATA AND NOT MARKUP. Ten documents (five agreements x two languages) rendered
from one builder, with the German and the English drafted as parallel block lists. A translator, or
a later edit, can change WORDS; it cannot move a clause, drop a schedule or renumber a document,
because none of those things live in the text. That is the same doctrine as legal.jsx for the
privacy copy and partners-locales for the /partners page, and build_pack.py asserts the two
languages are structurally identical before it writes anything.

EVERY PARTY DETAIL HERE WAS READ FROM THE COMPANIES' OWN IMPRESSUM OR SITE, not remembered:
  objectale GmbH   https://objectale.ch/en/startpage/  (address, telephone, e-mail)
  byon gmbh        https://www.byon.de/de/impressum    (address, HRB, VAT ID, managing directors)
  360 ITC GmbH     https://www.360itc.de/              (group structure; byon is an operating company)
A party block with a wrong register number is a document that cannot be signed, so these are facts
and not placeholders. Anything genuinely open is a bracketed field, and build_pack.py counts them.

THE COMMERCIAL FIGURES are the cybergod.ai list prices and service levels taken from the head
documents supplied by the operator (Master Partner Agreement Schedule 2, SLA Appendix A). They are
quoted so the back-to-back terms cannot promise byon more than objectale itself receives.
"""

# --------------------------------------------------------------------------- parties
#
# THE CHAIN, and every document in this pack names all three of them:
#
#   Stars4business OÜ  (Estonia)      owns and operates cybergod.ai        VENDOR
#        |  distribution agreement, non-exclusive
#   objectale GmbH     (Switzerland)  buys, resells, invoices, supports    DISTRIBUTOR
#        |  reseller agreement
#   byon gmbh          (Germany)      resells to its own customers         RESELLER
#        |  byon's own customer contract, on the vendor's End-User Terms
#   End customer       (e.g. a large enterprise)                           CUSTOMER
#
# THE LICENCE DOES NOT TRAVEL DOWN THAT CHAIN. The Vendor grants the right of use DIRECTLY to the
# Reseller and to each End Customer; the Distributor sells, invoices and supports. A three-deep
# sub-licence is what a large customer's counsel objects to, and it is also what collapses when the
# middle tier leaves. Rights direct, trade through the tiers.
VENDOR = {
    "name": "Stars4business OÜ",
    "short": "Stars4business",
    "addr": "[street], [postcode] Tallinn, Estonia",
    "addr_de": "[Straße], [PLZ] Tallinn, Estland",
    "reg": "[Estonian Commercial Register, registry code __________]",
    "reg_de": "[Handelsregister der Republik Estland, Registercode __________]",
    "vat": "[EE__________]",
    "mail": "feranicus@s4biz.io",
    "web": "www.cybergod.ai",
}

OBJECTALE = {
    "name": "objectale GmbH",
    "short": "objectale",
    "addr": "Bodenmattli 9, CH-8846 Willerzell, Switzerland",
    "addr_de": "Bodenmattli 9, CH-8846 Willerzell, Schweiz",
    "reg": "[Handelsregister des Kantons Schwyz, UID CHE-___.___.___]",
    "tel": "+41 58 3200 960",
    "mail": "info@objectale.ch",
    "web": "www.objectale.ch",
}

BYON = {
    "name": "byon gmbh",
    "short": "byon",
    "addr": "Solmsstraße 71, 60486 Frankfurt am Main, Germany",
    "addr_de": "Solmsstraße 71, 60486 Frankfurt am Main, Deutschland",
    "reg": "Amtsgericht Frankfurt am Main, HRB 131855",
    "vat": "DE271625857",
    "mgmt": "Robert Babic, Markus Michael",
    "tel": "+49 69 710 486 400",
    "mail": "info@byon.de",
    "web": "www.byon.de",
    "group": "360 ITC GmbH, Robert-Bosch-Straße 32, 63303 Dreieich",
    "group_de": "360 ITC GmbH, Robert-Bosch-Straße 32, 63303 Dreieich",
}

PLATFORM = "cybergod.ai"
OPERATOR = VENDOR["name"]

VERSION = "2.0"
DATE_EN = "21 August 2026"
DATE_DE = "21. August 2026"

# ONE GOVERNING LAW FOR THE WHOLE CHAIN, and this is a judgement rather than a preference.
#
# The parties span Estonia, Switzerland and Germany. Each pair could plausibly choose its own law,
# and the result is a flow-down clause construed under one law feeding a contract construed under
# another. That is precisely where a distribution chain fails: the reseller agreement says byon
# passes on "material contractual obligations" and the upstream agreement, under a different law,
# means something else by it. So the whole pack uses German law with Frankfurt am Main as the
# forum, which is byon's own seat and the only forum all three would accept without argument.
#
# THE COST IS REAL AND WORTH STATING: German law brings Sections 305 to 310 BGB, so a pre-formulated
# limitation of liability is controlled far more strictly than under Estonian or Swiss law. Every
# liability clause in this pack is drafted to survive that control rather than to be as aggressive
# as possible. Estonian law would be more vendor-friendly for the top tier; the price would be two
# different constructions of the same flow-down.
#
# Change these two and rebuild if the vendor's counsel prefers otherwise. Nothing else moves.
LAW_EN = "the laws of the Federal Republic of Germany"
LAW_DE = "dem Recht der Bundesrepublik Deutschland"
FORUM = "Frankfurt am Main"

# --------------------------------------------------------------------------- house style
# Mirrors the head documents: A4, Arial 10 pt body on a dark ink, Arial Black headings.
# THE ACCENT IS DELIBERATELY NEUTRAL. objectale's own brand colour could not be read from their
# site (the logo SVG and the stylesheet are not retrievable), and putting a guessed colour on a
# partner's contract is the same false claim as reading a brand out of a stock Office palette.
# Change ACCENT to their hex once they supply it; nothing else has to change.
INK = "1F2533"
HEAD = "14161F"
ACCENT = "2E4B63"
MUTED = "5C6B85"
RULE = "D8DCE4"

FONT_BODY = "Arial"
FONT_HEAD = "Arial Black"

# --------------------------------------------------------------------------- head-document facts
# Quoted, not invented. Used to keep the back-to-back terms honest: objectale cannot grant byon a
# service level it does not itself hold, and a schedule that says otherwise is unenforceable
# upstream and a liability downstream.
LIST_PRICES = [
    # item, list price EUR ex VAT
    ("Single assessment run", "100"),
    ("Report subscription, per seat per month", "200"),
    ("Findings review, per hour", "200"),
    ("Workshop, per day (SME)", "2,500"),
    ("Workshop, large enterprise, 2 days", "5,000"),
]
LIST_PRICES_DE = [
    ("Einzelner Assessment-Lauf", "100"),
    ("Report-Abonnement, je Seat und Monat", "200"),
    ("Findings-Review, je Stunde", "200"),
    ("Workshop, je Tag (KMU)", "2.500"),
    ("Workshop, Großunternehmen, 2 Tage", "5.000"),
]

SEVERITIES = [
    ("S1 - Critical", "Service unavailable, or a confirmed security incident affecting the service",
     "1 hour", "4 hours"),
    ("S2 - Major", "A major function is unusable and there is no workaround",
     "4 business hours", "1 business day"),
    ("S3 - Minor", "A function is degraded or a workaround exists",
     "1 business day", "Next scheduled release"),
    ("S4 - Request", "Question, change request, new seat, allow-list change",
     "2 business days", "By agreement"),
]
SEVERITIES_DE = [
    ("S1 - Kritisch", "Dienst nicht verfügbar oder bestätigter Sicherheitsvorfall mit Auswirkung "
     "auf den Dienst", "1 Stunde", "4 Stunden"),
    ("S2 - Schwerwiegend", "Eine wesentliche Funktion ist unbrauchbar, es besteht kein Workaround",
     "4 Arbeitsstunden", "1 Arbeitstag"),
    ("S3 - Gering", "Eine Funktion ist eingeschränkt oder es besteht ein Workaround",
     "1 Arbeitstag", "Nächstes geplantes Release"),
    ("S4 - Anfrage", "Frage, Änderungswunsch, neuer Seat, Änderung der Freigabeliste",
     "2 Arbeitstage", "Nach Vereinbarung"),
]

CREDITS = [("< 99.5% and >= 99.0%", "5%"), ("< 99.0% and >= 98.0%", "10%"),
           ("< 98.0% and >= 95.0%", "20%"), ("< 95.0%", "30%")]
CREDITS_DE = [("< 99,5% und >= 99,0%", "5%"), ("< 99,0% und >= 98,0%", "10%"),
              ("< 98,0% und >= 95,0%", "20%"), ("< 95,0%", "30%")]

# Sub-processors, from the operator's own documented architecture. Named because Art. 28(2) and
# Art. 13(1)(e) GDPR require the chain to be disclosed, and because a customer's procurement will
# ask for exactly this list.
SUBPROCESSORS = [
    ("DigitalOcean, LLC", "United States / Germany",
     "Infrastructure provider for the server on which the platform runs, and for the inference "
     "endpoint that writes the narrative sections of a deliverable.",
     "Frankfurt am Main (FRA1)"),
    ("Google LLC", "United States",
     "Gmail API, used to send the one-time login code and the daily report to the address the user "
     "registered. Covered by the EU-US Data Privacy Framework.",
     "United States"),
]
SUBPROCESSORS_DE = [
    ("DigitalOcean, LLC", "USA / Deutschland",
     "Infrastrukturanbieter für den Server, auf dem die Plattform läuft, sowie für den "
     "Inferenz-Endpunkt, der die Textabschnitte der Ergebnisdokumente erzeugt.",
     "Frankfurt am Main (FRA1)"),
    ("Google LLC", "USA",
     "Gmail-API, verwendet für den Versand des Einmalcodes bei der Anmeldung und des Tagesberichts "
     "an die vom Nutzer registrierte Adresse. Gedeckt durch das EU-US Data Privacy Framework.",
     "USA"),
]

NOTE_EN = ("This is a commercial template prepared for negotiation between the named parties. It "
           "is not legal advice and it has not been reviewed by admitted counsel in Germany or "
           "Switzerland. Have it checked before signature.")
NOTE_DE = ("Dies ist ein kaufmännischer Vertragsentwurf zur Verhandlung zwischen den genannten "
           "Parteien. Er stellt keine Rechtsberatung dar und wurde nicht von einer in Deutschland "
           "oder in der Schweiz zugelassenen Rechtsanwältin oder einem zugelassenen Rechtsanwalt "
           "geprüft. Lassen Sie ihn vor Unterzeichnung prüfen.")
