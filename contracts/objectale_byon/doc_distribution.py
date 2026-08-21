# -*- coding: utf-8 -*-
"""00 - Distribution agreement, Stars4business OÜ (Vendor) -> objectale GmbH (Distributor).

THE MISSING HEAD AGREEMENT. Everything downstream referenced it as a bracket; a chain whose top
link is a placeholder is a chain a large customer's counsel will not accept.

TWO THINGS MAKE THIS A DISTRIBUTION AGREEMENT RATHER THAN A RESELLER AGREEMENT:

  * THE RIGHT TO APPOINT RESELLERS (clause 5). Without an express right, a reseller appointment is
    an unauthorised sub-licence and the Vendor can disown it. With it, the Vendor also gets to say
    what a reseller contract must contain, which is where the acceptable-use terms actually get
    their teeth two tiers down.

  * THE VENDOR GRANTS DIRECTLY, THE DISTRIBUTOR TRADES (clause 4). The Distributor buys and sells
    entitlements and carries the credit risk; it does not hold a licence it then sub-licences. That
    is what keeps the chain intact when this agreement ends, and it is the design the flow-down deed
    depends on.

THE LIABILITY CAP IS THE ONE COMMERCIAL FIGURE THAT MATTERS HERE, because the deed caps the
Vendor's exposure to both lower tiers combined at this number. Set it deliberately.
"""
from common import BYON, DATE_DE, DATE_EN, FORUM, LAW_DE, LAW_EN, LIST_PRICES, LIST_PRICES_DE, \
    NOTE_DE, NOTE_EN, OBJECTALE, PLATFORM, VENDOR, VERSION

EN = [
    ("h1", "DISTRIBUTION AGREEMENT"),
    ("meta", "%s and %s  ·  Version %s  ·  %s  ·  German law, %s"
     % (VENDOR["name"], OBJECTALE["name"], VERSION, DATE_EN, FORUM)),

    ("p", "This Distribution Agreement (the \"Agreement\") takes effect on [effective date] "
          "between:"),
    ("p", "%s, a private limited company incorporated in the Republic of Estonia, %s, registered "
          "under %s (the \"Vendor\"); and"
     % (VENDOR["name"], VENDOR["addr"], VENDOR["reg"])),
    ("p", "%s, a limited liability company incorporated in Switzerland, %s, registered under %s "
          "(the \"Distributor\")." % (OBJECTALE["name"], OBJECTALE["addr"], OBJECTALE["reg"])),
    ("note", NOTE_EN),

    ("h2", "Background"),
    ("p", "A. The Vendor owns and operates %s, an external cyber-risk and EU regulatory-compliance "
          "assessment platform (the \"Platform\"). The Platform reads public sources only. It is "
          "not a penetration test: it performs no port scanning, no vulnerability probing and no "
          "authentication attempt, and sends no packet to the organisation being assessed."
     % PLATFORM),
    ("p", "B. The Distributor is a boutique consultancy for telecommunications and IT "
          "infrastructure and wishes to distribute the Platform, including through resellers."),
    ("p", "C. The parties wish to record the terms of that distribution."),

    ("h2", "1. Interpretation"),
    ("num", "1.1", "\"Include\" and \"including\" are to be read without limitation."),
    ("num", "1.2", "A reference to writing includes e-mail to the addresses in Schedule 1. Where "
                   "this Agreement requires written form for a variation, that means text form "
                   "within the meaning of Section 126b BGB."),
    ("num", "1.3", "The Schedules form part of this Agreement."),

    ("h2", "2. Structure"),
    ("num", "2.1", "This Agreement is the framework. Individual transactions are agreed by order "
                   "in the form of Schedule 3."),
    ("num", "2.2", "The Service Level Agreement, the Data Processing Agreement, the End-User Terms "
                   "and the Flow-Down and Step-In Deed form part of the contractual arrangement "
                   "between the parties."),
    ("num", "2.3", "Order of precedence, highest first: the Flow-Down and Step-In Deed for the "
                   "matters it addresses; a signed order for the transaction it governs; the Data "
                   "Processing Agreement for data protection; the Service Level Agreement for "
                   "service levels; this Agreement; the Schedules."),
    ("num", "2.4", "The Distributor's general terms and conditions do not apply."),

    ("h2", "3. Appointment and territory"),
    ("num", "3.1", "The Vendor appoints the Distributor as a NON-EXCLUSIVE distributor of the "
                   "Platform in the Territory, and the Distributor accepts."),
    ("num", "3.2", "The Territory is [Germany, Austria and Switzerland] unless Schedule 1 states "
                   "otherwise."),
    ("num", "3.3", "The appointment is non-exclusive. The Vendor may appoint other distributors "
                   "and resellers and may sell directly, subject to clause 3.4."),
    ("num", "3.4", "Deal registration. Where the Distributor registers a named prospect in writing "
                   "and the Vendor confirms it, the Vendor will not solicit that prospect for the "
                   "Platform for six months and will refer inbound enquiries to the Distributor. "
                   "Confirmation is not to be unreasonably withheld. A registration lapses if no "
                   "order follows within six months."),
    ("num", "3.5", "The Distributor acts in its own name and for its own account. Nothing creates "
                   "an agency, a commercial agency relationship within the meaning of Sections 84 "
                   "ff. HGB, a partnership or a joint venture."),

    ("h2", "4. Rights granted"),
    ("num", "4.1", "The Vendor grants the Distributor a non-exclusive, non-transferable right, for "
                   "the term and in the Territory, to market and sell entitlements to the "
                   "Platform, to access and use it for demonstration, enablement and support, and "
                   "to appoint resellers under clause 5."),
    ("num", "4.2", "THE LICENCE IS NOT SUB-LICENSED THROUGH THE DISTRIBUTOR. The right of use is "
                   "granted by the Vendor directly to each reseller and to each end customer, on "
                   "the End-User Terms. The Distributor sells, invoices, carries the credit risk "
                   "and provides commercial and second-line support."),
    ("num", "4.3", "The Distributor receives no right in the source code, no right to host the "
                   "Platform on its own infrastructure and no right to modify the assessment "
                   "engine."),
    ("num", "4.4", "The Vendor retains all intellectual property in the Platform, its software, "
                   "its templates and its methodology."),

    ("h2", "5. Appointment of resellers"),
    ("num", "5.1", "The Distributor may appoint resellers in the Territory without the Vendor's "
                   "prior consent, provided each reseller contract complies with this clause."),
    ("num", "5.2", "Every reseller contract must, as a minimum, incorporate the End-User Terms for "
                   "onward flow-down, oblige the reseller not to make representations beyond the "
                   "Vendor's documentation, and preserve the Vendor's right to enforce the "
                   "acceptable-use provisions directly."),
    ("num", "5.3", "The Distributor will notify the Vendor of each reseller appointment within ten "
                   "business days and will name the reseller in Schedule 1."),
    ("num", "5.4", "The Distributor remains fully responsible to the Vendor for its resellers' "
                   "compliance as if it were the Distributor's own conduct."),
    ("num", "5.5", "Where a reseller is material to the Distributor's volume, the parties will "
                   "enter into the Flow-Down and Step-In Deed with that reseller. The Vendor will "
                   "not unreasonably refuse to do so."),
    ("num", "5.6", "The Vendor may require the Distributor to suspend a reseller that is in "
                   "material breach of the acceptable-use provisions, after telling the "
                   "Distributor the reason and giving it a reasonable opportunity to cure through "
                   "the reseller."),

    ("h2", "6. Distributor obligations"),
    ("num", "6.1", "The Distributor will market the Platform accurately, will use only marketing "
                   "material the Vendor supplies or approves, and will not describe the Platform "
                   "as a penetration test, a certification or an audit."),
    ("num", "6.2", "The Distributor will maintain at least two trained commercial contacts and two "
                   "trained technical contacts."),
    ("num", "6.3", "The Distributor will provide first commercial contact and second-line "
                   "technical support to its resellers, and will escalate to the Vendor only after "
                   "its own triage."),
    ("num", "6.4", "The Distributor will comply with applicable law, including export control and "
                   "sanctions law."),
    ("num", "6.5", "The Distributor will not use the Platform to assess an organisation it is not "
                   "entitled to assess, and will not benchmark it for publication, decompile it or "
                   "use it to build a competing service."),

    ("h2", "7. Vendor obligations"),
    ("num", "7.1", "The Vendor will operate the Platform in accordance with the Service Level "
                   "Agreement."),
    ("num", "7.2", "The Vendor will provide third-line support to the Distributor's nominated "
                   "contacts."),
    ("num", "7.3", "The Vendor will provide enablement, current documentation and sales material "
                   "at no charge."),
    ("num", "7.4", "The Vendor will give notice of changes and deprecations with the periods in "
                   "the Service Level Agreement."),
    ("num", "7.5", "The Vendor will tell the Distributor without undue delay of anything that "
                   "materially affects the Distributor's ability to supply, including a change of "
                   "a third-party data source entitlement."),

    ("h2", "8. Prices, ordering and payment"),
    ("num", "8.1", "The Vendor's list prices and the Distributor's discount are in Schedule 2. All "
                   "amounts are in euro and exclusive of value added tax."),
    ("num", "8.2", "The Distributor sets its own resale prices freely. The Vendor does not fix, "
                   "recommend as binding, or otherwise restrict the price at which the Distributor "
                   "or a reseller resells."),
    ("num", "8.3", "Payment is due within 30 days of the invoice date, without deduction."),
    ("num", "8.4", "On late payment the Vendor is entitled to default interest under Section 288(2) "
                   "BGB and to the lump sum under Section 288(5) BGB."),
    ("num", "8.5", "The Distributor may set off only against claims that are undisputed or finally "
                   "determined by a court."),
    ("num", "8.6", "The Vendor may adjust list prices once per contract year on three months' "
                   "notice. The Distributor's discount percentage is not reduced by an adjustment. "
                   "Where an adjustment exceeds five per cent the Distributor may terminate the "
                   "affected order with effect from the date it takes effect."),
    ("num", "8.7", "Non-payment by a reseller or an end customer does not relieve the Distributor "
                   "of its obligation to pay the Vendor."),

    ("h2", "9. Usage records and audit"),
    ("num", "9.1", "The Vendor records the number of assessment runs, the number of active seats "
                   "and the identity of the ordering user. Those records are the reference "
                   "measurement for invoicing."),
    ("num", "9.2", "The Distributor may raise a discrepancy in writing within 20 business days of "
                   "an invoice."),
    ("num", "9.3", "The Vendor may audit compliance once per contract year on 20 business days' "
                   "notice, at its own cost. Where the audit shows an underpayment above five per "
                   "cent, the Distributor bears the reasonable cost."),

    ("h2", "10. Trade marks and announcements"),
    ("num", "10.1", "Each party grants the other a non-exclusive, revocable, royalty-free licence "
                    "to use its name and logo for the term, solely to describe the partnership."),
    ("num", "10.2", "Neither party will register a mark or domain identical or confusingly similar "
                    "to the other's."),
    ("num", "10.3", "A press release or case study naming the other requires prior written "
                    "approval, not to be unreasonably withheld."),

    ("h2", "11. Data protection"),
    ("num", "11.1", "The parties, together with each reseller party to a Flow-Down and Step-In "
                    "Deed, enter into the Data Processing Agreement, which satisfies Article 28 "
                    "GDPR."),
    ("num", "11.2", "The Platform is hosted in Frankfurt am Main. Transfers of personal data from "
                    "the European Union to the Distributor in Switzerland rely on the adequacy "
                    "decision the European Commission adopted for Switzerland on 15 January 2024."),

    ("h2", "12. Confidentiality"),
    ("num", "12.1", "Each party will keep the other's confidential information secret and use it "
                    "only for this Agreement, applying reasonable steps to maintain secrecy within "
                    "the meaning of Section 2 no. 1(b) of the German Trade Secrets Act."),
    ("num", "12.2", "The duty survives termination for three years. Trade secrets remain protected "
                    "for as long as they qualify."),

    ("h2", "13. Quality, defects and warranties"),
    ("num", "13.1", "The Vendor provides the Platform as a service. The parties agree that German "
                    "lease law applies to its provision."),
    ("num", "13.2", "The strict liability for defects existing at the beginning of the contract "
                    "under Section 536a(1) first alternative BGB is excluded. The Vendor is liable "
                    "for such defects only where it is at fault."),
    ("num", "13.3", "The agreed quality is that described in the documentation current at the date "
                    "of the order and in the Service Level Agreement."),
    ("num", "13.4", "The Vendor warrants that the Platform performs materially in accordance with "
                    "the documentation. The Vendor does not warrant that an assessment identifies "
                    "every exposure, that a public source is complete or accurate, or that a "
                    "deliverable is free of a finding that later proves not to apply."),
    ("num", "13.5", "The Vendor warrants that it owns or is licensed to grant the rights it grants "
                    "under this Agreement."),

    ("h2", "14. Liability"),
    ("num", "14.1", "Each party is liable without limitation for intent and gross negligence, for "
                    "injury to life, body or health, under the German Product Liability Act, and "
                    "where it has given a guarantee or fraudulently concealed a defect."),
    ("num", "14.2", "For simple negligence, each party is liable only where it breaches a material "
                    "contractual obligation, meaning an obligation whose performance makes proper "
                    "performance of this Agreement possible in the first place and on whose "
                    "observance the other party regularly relies. Liability is then limited to the "
                    "foreseeable damage typical for this type of contract."),
    ("num", "14.3", "Subject to clauses 14.1 and 14.2, the Vendor's aggregate liability for simple "
                    "negligence in any contract year is limited to the fees paid by the "
                    "Distributor in the twelve months preceding the event, and to [EUR 500,000] in "
                    "total, whichever is lower. THIS FIGURE ALSO CAPS THE VENDOR'S COMBINED "
                    "EXPOSURE TO THE DISTRIBUTOR AND ANY RESELLER under the Flow-Down and Step-In "
                    "Deed."),
    ("num", "14.4", "Any further liability is excluded, in particular for loss of profit and "
                    "indirect damage, save where clause 14.1 applies."),
    ("num", "14.5", "The limitations apply equally to the personal liability of each party's "
                    "employees, representatives, bodies and vicarious agents."),
    ("num", "14.6", "The limitation period for claims for defects is one year from the statutory "
                    "commencement, save for claims under clause 14.1."),

    ("h2", "15. Indemnities"),
    ("num", "15.1", "The Vendor will indemnify the Distributor against third-party claims that use "
                    "of the Platform in accordance with this Agreement infringes an intellectual "
                    "property right, provided the Distributor notifies without undue delay, gives "
                    "the Vendor control of the defence and does not settle without consent."),
    ("num", "15.2", "The Vendor may at its option procure the right to continue use, modify the "
                    "Platform so that it no longer infringes, or terminate the affected order and "
                    "refund fees for the unexpired term."),
    ("num", "15.3", "The Distributor will indemnify the Vendor against third-party claims arising "
                    "from a representation the Distributor or its reseller makes beyond clause "
                    "6.1, or from an assessment run against an organisation it was not entitled to "
                    "assess."),

    ("h2", "16. Term and termination"),
    ("num", "16.1", "This Agreement runs for an initial term of 24 months and renews for "
                    "successive periods of 12 months unless either party gives three months' "
                    "notice before the end of the then-current term."),
    ("num", "16.2", "Either party may terminate for good cause within the meaning of Section 314 "
                    "BGB, in particular for an unremedied material breach after 30 days' written "
                    "demand, for insolvency, or for sanctions."),
    ("num", "16.3", "On termination the Distributor will cease to market the Platform. Accrued "
                    "fees remain payable."),
    ("num", "16.4", "TERMINATION DOES NOT STRAND A RESELLER OR AN END CUSTOMER. Where a Flow-Down "
                    "and Step-In Deed is in place, the step-in provisions of that Deed apply and "
                    "prevail over this clause."),
    ("num", "16.5", "Clauses 4.4, 10, 11, 12, 14, 15, 16 and 18 survive."),

    ("h2", "17. Escalation"),
    ("num", "17.1", "A dispute is escalated to the commercial owners, then within ten business "
                    "days to a member of each party's management, before proceedings are commenced, "
                    "except for interim relief, a claim for payment, or where a limitation period "
                    "would expire."),

    ("h2", "18. Final provisions and governing law"),
    ("num", "18.1", "Variations require text form. There are no oral side agreements."),
    ("num", "18.2", "Neither party may assign without the other's written consent, not to be "
                    "unreasonably withheld. Section 354a HGB is unaffected."),
    ("num", "18.3", "Neither party is liable for a failure caused by an event beyond its "
                    "reasonable control while that event continues, provided it notifies and "
                    "mitigates."),
    ("num", "18.4", "If a provision is invalid the remainder is unaffected."),
    ("num", "18.5", "This Agreement is executed in German and in English. In the event of a "
                    "discrepancy the [German] version prevails."),
    ("num", "18.6", "This Agreement is governed by %s, excluding its conflict of laws rules and "
                    "the United Nations Convention on Contracts for the International Sale of "
                    "Goods. The exclusive place of jurisdiction is %s." % (LAW_EN, FORUM)),

    ("pagebreak",),
    ("h2", "Schedule 1 - Party details, territory and appointed resellers"),
    ("table", ["Item", "Vendor", "Distributor"], [
        ["Legal entity", VENDOR["name"], OBJECTALE["name"]],
        ["Registered office", VENDOR["addr"], OBJECTALE["addr"]],
        ["Register", VENDOR["reg"], OBJECTALE["reg"]],
        ["VAT identification number", VENDOR["vat"], "[CHE-___.___.___ MWST]"],
        ["Represented by", "[name, function]", "[name, function]"],
        ["Commercial contact", "[name] · [e-mail]", "[name] · [e-mail]"],
        ["Technical contact", "[name] · [e-mail]", "[name] · [e-mail]"],
        ["Notices address", VENDOR["mail"], OBJECTALE["mail"]],
        ["Territory", "[Germany, Austria and Switzerland]", "-"],
    ]),
    ("h3", "Appointed resellers"),
    ("table", ["#", "Reseller", "Country", "Flow-Down Deed signed"], [
        ["1", BYON["name"], "Germany", "[yes / date]"],
        ["2", "[ ]", "[ ]", "[ ]"],
        ["3", "[ ]", "[ ]", "[ ]"],
    ]),

    ("pagebreak",),
    ("h2", "Schedule 2 - List prices and the Distributor's discount"),
    ("table", ["Item", "List price, EUR ex VAT"], [[a, b] for a, b in LIST_PRICES]),
    ("table", ["Item", "Detail"], [
        ["Distributor discount on list", "[__]% for the initial term"],
        ["Minimum commitment", "[none / __ seats / __ runs per quarter]"],
        ["Runs included per subscription seat per month", "[__]"],
        ["Price of a run beyond the included number", "[EUR __]"],
        ["Review of the discount", "Annually, on the anniversary of the Effective Date"],
    ]),
    ("note", "The Distributor's discount must leave room for a reseller discount below it and a "
             "margin for the reseller. Setting this number without deciding the reseller tier at "
             "the same time is what produces a channel nobody can make money in."),

    ("pagebreak",),
    ("h2", "Schedule 3 - Form of order"),
    ("table", ["Item", "Detail"], [
        ["Order number", "[ ]"],
        ["Effective date", "[ ]"],
        ["Reseller and end customer, where the order is for a named deal", "[ ]"],
        ["Term", "[ ]"],
        ["Discount applied", "[ ]"],
        ["Billing frequency", "[monthly in advance / on delivery]"],
    ]),
    ("table", ["Line", "Item", "Quantity", "Unit price, EUR ex VAT", "Total per period"], [
        ["1", "Report subscription seats", "[ ]", "[ ]", "[ ]"],
        ["2", "Assessment runs beyond the included number", "As consumed", "[ ]", "[ ]"],
        ["3", "Findings review hours", "[ ]", "[ ]", "[ ]"],
        ["4", "Workshops", "[ ]", "[ ]", "[ ]"],
        ["5", "Other", "[ ]", "[ ]", "[ ]"],
    ]),

    ("pagebreak",),
    ("h2", "Signatures"),
    ("sig", "For %s (Vendor)" % VENDOR["name"], "For %s (Distributor)" % OBJECTALE["name"],
     ["Name:", "Function:", "Place:", "Date:"]),
]

DE = [
    ("h1", "DISTRIBUTIONSVERTRAG"),
    ("meta", "%s und %s  ·  Version %s  ·  %s  ·  Deutsches Recht, %s"
     % (VENDOR["name"], OBJECTALE["name"], VERSION, DATE_DE, FORUM)),

    ("p", "Dieser Distributionsvertrag (der \"Vertrag\") tritt am [Datum des Inkrafttretens] in "
          "Kraft zwischen:"),
    ("p", "%s, einer Gesellschaft mit beschränkter Haftung estnischen Rechts, %s, eingetragen unter "
          "%s (der \"Hersteller\"); und"
     % (VENDOR["name"], VENDOR["addr_de"], VENDOR["reg_de"])),
    ("p", "%s, einer Gesellschaft mit beschränkter Haftung schweizerischen Rechts, %s, eingetragen "
          "unter %s (der \"Distributor\")."
     % (OBJECTALE["name"], OBJECTALE["addr_de"], OBJECTALE["reg"])),
    ("note", NOTE_DE),

    ("h2", "Präambel"),
    ("p", "A. Der Hersteller ist Inhaber und Hersteller von %s, einer Plattform zur Bewertung "
          "externer Cyber-Risiken und der EU-Regulierungs-Compliance (die \"Plattform\"). Die "
          "Plattform wertet ausschließlich öffentliche Quellen aus. Sie ist kein Penetrationstest: "
          "Sie führt keinen Portscan, keine Schwachstellenprüfung und keinen Anmeldeversuch durch "
          "und sendet an das bewertete Unternehmen kein Datenpaket." % PLATFORM),
    ("p", "B. Der Distributor ist eine Boutique-Beratung für Telekommunikation und IT-Infrastruktur "
          "und beabsichtigt, die Plattform zu vertreiben, auch über Wiederverkäufer."),
    ("p", "C. Die Parteien wollen die Bedingungen dieses Vertriebs festhalten."),

    ("h2", "1. Auslegung"),
    ("num", "1.1", "\"Einschließlich\" und \"insbesondere\" sind ohne Beschränkung zu verstehen."),
    ("num", "1.2", "Die Bezugnahme auf Schriftlichkeit umfasst E-Mail an die in Anlage 1 genannten "
                   "Adressen. Soweit dieser Vertrag für eine Änderung Schriftform verlangt, ist "
                   "Textform im Sinne des § 126b BGB gemeint."),
    ("num", "1.3", "Die Anlagen sind Bestandteil dieses Vertrages."),

    ("h2", "2. Struktur"),
    ("num", "2.1", "Dieser Vertrag ist der Rahmen. Einzelgeschäfte werden durch Bestellung nach dem "
                   "Muster der Anlage 3 vereinbart."),
    ("num", "2.2", "Das Service Level Agreement, der Auftragsverarbeitungsvertrag, die "
                   "Endkundenbedingungen und die Durchgriffs- und Eintrittsvereinbarung sind "
                   "Bestandteil der vertraglichen Beziehung der Parteien."),
    ("num", "2.3", "Rangfolge, beginnend mit dem höchsten Rang: die Durchgriffs- und "
                   "Eintrittsvereinbarung für die dort geregelten Fragen; eine unterzeichnete "
                   "Bestellung für das von ihr geregelte Geschäft; der "
                   "Auftragsverarbeitungsvertrag für den Datenschutz; das Service Level Agreement "
                   "für Service Levels; dieser Vertrag; die Anlagen."),
    ("num", "2.4", "Allgemeine Geschäftsbedingungen des Distributors finden keine Anwendung."),

    ("h2", "3. Bestellung und Gebiet"),
    ("num", "3.1", "Der Hersteller bestellt den Distributor zum NICHT AUSSCHLIESSLICHEN Distributor "
                   "der Plattform im Gebiet; der Distributor nimmt an."),
    ("num", "3.2", "Das Gebiet ist [Deutschland, Österreich und die Schweiz], sofern Anlage 1 nichts "
                   "anderes bestimmt."),
    ("num", "3.3", "Die Bestellung ist nicht ausschließlich. Der Hersteller darf weitere "
                   "Distributoren und Wiederverkäufer bestellen und unmittelbar verkaufen, "
                   "vorbehaltlich Ziffer 3.4."),
    ("num", "3.4", "Projektschutz. Meldet der Distributor einen namentlich benannten Interessenten "
                   "schriftlich an und bestätigt der Hersteller dies, wird der Hersteller diesen "
                   "Interessenten sechs Monate lang nicht für die Plattform ansprechen und "
                   "eingehende Anfragen an den Distributor verweisen. Die Bestätigung darf nicht "
                   "unbillig verweigert werden. Die Anmeldung erlischt, wenn binnen sechs Monaten "
                   "keine Bestellung folgt."),
    ("num", "3.5", "Der Distributor handelt im eigenen Namen und auf eigene Rechnung. Es entstehen "
                   "keine Stellvertretung, kein Handelsvertreterverhältnis im Sinne der §§ 84 ff. "
                   "HGB, keine Gesellschaft und kein Joint Venture."),

    ("h2", "4. Eingeräumte Rechte"),
    ("num", "4.1", "Der Hersteller räumt dem Distributor für die Laufzeit und im Gebiet das nicht "
                   "ausschließliche, nicht übertragbare Recht ein, Nutzungsberechtigungen an der "
                   "Plattform zu vermarkten und zu verkaufen, auf die Plattform zu Zwecken der "
                   "Vorführung, Befähigung und Unterstützung zuzugreifen und sie zu nutzen sowie "
                   "Wiederverkäufer nach Ziffer 5 zu bestellen."),
    ("num", "4.2", "DIE LIZENZ WIRD NICHT ÜBER DEN DISTRIBUTOR UNTERLIZENZIERT. Das Nutzungsrecht "
                   "wird vom Hersteller unmittelbar jedem Wiederverkäufer und jedem Endkunden auf "
                   "Grundlage der Endkundenbedingungen eingeräumt. Der Distributor verkauft, "
                   "rechnet ab, trägt das Kreditrisiko und leistet kaufmännische Betreuung sowie "
                   "Second-Level-Support."),
    ("num", "4.3", "Der Distributor erhält kein Recht am Quellcode, kein Recht zum Betrieb der "
                   "Plattform auf eigener Infrastruktur und kein Recht zur Änderung der "
                   "Assessment-Engine."),
    ("num", "4.4", "Der Hersteller behält sämtliche Schutzrechte an der Plattform, ihrer Software, "
                   "ihren Vorlagen und ihrer Methodik."),

    ("h2", "5. Bestellung von Wiederverkäufern"),
    ("num", "5.1", "Der Distributor darf im Gebiet ohne vorherige Zustimmung des Herstellers "
                   "Wiederverkäufer bestellen, sofern jeder Wiederverkäufervertrag dieser Ziffer "
                   "entspricht."),
    ("num", "5.2", "Jeder Wiederverkäufervertrag muss mindestens die Endkundenbedingungen zur "
                   "Weitergabe einbeziehen, den Wiederverkäufer verpflichten, keine über die "
                   "Dokumentation des Herstellers hinausgehenden Erklärungen abzugeben, und das "
                   "Recht des Herstellers zur unmittelbaren Durchsetzung der "
                   "Nutzungsbeschränkungen wahren."),
    ("num", "5.3", "Der Distributor zeigt jede Bestellung eines Wiederverkäufers binnen zehn "
                   "Arbeitstagen an und benennt ihn in Anlage 1."),
    ("num", "5.4", "Der Distributor bleibt dem Hersteller für die Einhaltung durch seine "
                   "Wiederverkäufer wie für eigenes Handeln verantwortlich."),
    ("num", "5.5", "Ist ein Wiederverkäufer für das Volumen des Distributors wesentlich, schließen "
                   "die Parteien mit diesem Wiederverkäufer die Durchgriffs- und "
                   "Eintrittsvereinbarung. Der Hersteller wird dies nicht unbillig verweigern."),
    ("num", "5.6", "Der Hersteller kann vom Distributor verlangen, einen Wiederverkäufer zu "
                   "sperren, der die Nutzungsbeschränkungen wesentlich verletzt, nachdem er dem "
                   "Distributor den Grund mitgeteilt und ihm angemessene Gelegenheit zur Abhilfe "
                   "über den Wiederverkäufer gegeben hat."),

    ("h2", "6. Pflichten des Distributors"),
    ("num", "6.1", "Der Distributor vermarktet die Plattform zutreffend, verwendet nur vom "
                   "Hersteller bereitgestelltes oder freigegebenes Material und stellt die "
                   "Plattform nicht als Penetrationstest, Zertifizierung oder Prüfung dar."),
    ("num", "6.2", "Der Distributor hält mindestens zwei geschulte kaufmännische und zwei geschulte "
                   "technische Ansprechpartner vor."),
    ("num", "6.3", "Der Distributor leistet die kaufmännische Erstbetreuung und den technischen "
                   "Second-Level-Support für seine Wiederverkäufer und eskaliert an den Hersteller "
                   "erst nach eigener Qualifizierung."),
    ("num", "6.4", "Der Distributor hält das anwendbare Recht einschließlich Exportkontroll- und "
                   "Sanktionsrecht ein."),
    ("num", "6.5", "Der Distributor wird die Plattform nicht für ein Unternehmen nutzen, zu dessen "
                   "Bewertung er nicht berechtigt ist, sie nicht zu Veröffentlichungszwecken mit "
                   "Wettbewerbsprodukten vergleichen, nicht dekompilieren und nicht zum Aufbau "
                   "eines Konkurrenzdienstes nutzen."),

    ("h2", "7. Pflichten des Herstellers"),
    ("num", "7.1", "Der Hersteller betreibt die Plattform nach Maßgabe des Service Level "
                   "Agreements."),
    ("num", "7.2", "Der Hersteller leistet Third-Level-Support für die benannten Ansprechpartner "
                   "des Distributors."),
    ("num", "7.3", "Der Hersteller stellt Befähigung, aktuelle Dokumentation und Vertriebsmaterial "
                   "unentgeltlich bereit."),
    ("num", "7.4", "Der Hersteller kündigt Änderungen und Abkündigungen mit den Fristen des Service "
                   "Level Agreements an."),
    ("num", "7.5", "Der Hersteller informiert den Distributor unverzüglich über alles, was dessen "
                   "Lieferfähigkeit wesentlich beeinträchtigt, einschließlich einer Änderung der "
                   "Berechtigung an einer Drittdatenquelle."),

    ("h2", "8. Preise, Bestellung und Zahlung"),
    ("num", "8.1", "Die Listenpreise des Herstellers und der Rabatt des Distributors ergeben sich "
                   "aus Anlage 2. Alle Beträge in Euro zuzüglich Umsatzsteuer."),
    ("num", "8.2", "Der Distributor bestimmt seine Wiederverkaufspreise frei. Der Hersteller setzt "
                   "die Preise, zu denen der Distributor oder ein Wiederverkäufer weiterverkauft, "
                   "nicht fest, empfiehlt sie nicht verbindlich und beschränkt sie nicht."),
    ("num", "8.3", "Die Zahlung ist innerhalb von 30 Tagen ab Rechnungsdatum ohne Abzug fällig."),
    ("num", "8.4", "Bei Zahlungsverzug stehen dem Hersteller Verzugszinsen nach § 288 Abs. 2 BGB "
                   "und die Pauschale nach § 288 Abs. 5 BGB zu."),
    ("num", "8.5", "Der Distributor kann nur mit unbestrittenen oder rechtskräftig festgestellten "
                   "Forderungen aufrechnen."),
    ("num", "8.6", "Der Hersteller darf die Listenpreise einmal je Vertragsjahr mit dreimonatiger "
                   "Frist anpassen. Der Rabattsatz des Distributors wird dadurch nicht verringert. "
                   "Übersteigt eine Anpassung fünf Prozent, kann der Distributor die betroffene "
                   "Bestellung zum Wirksamwerden kündigen."),
    ("num", "8.7", "Der Zahlungsausfall eines Wiederverkäufers oder Endkunden befreit den "
                   "Distributor nicht von seiner Zahlungspflicht gegenüber dem Hersteller."),

    ("h2", "9. Nutzungsnachweise und Prüfung"),
    ("num", "9.1", "Der Hersteller zeichnet die Anzahl der Assessment-Läufe, die Anzahl aktiver "
                   "Seats und die Identität des bestellenden Nutzers auf. Diese Aufzeichnungen sind "
                   "für die Rechnungsstellung maßgeblich."),
    ("num", "9.2", "Der Distributor kann eine Abweichung binnen 20 Arbeitstagen ab Rechnung "
                   "schriftlich rügen."),
    ("num", "9.3", "Der Hersteller darf die Einhaltung einmal je Vertragsjahr mit einer Frist von "
                   "20 Arbeitstagen auf eigene Kosten prüfen. Ergibt die Prüfung eine Unterzahlung "
                   "von mehr als fünf Prozent, trägt der Distributor die angemessenen Kosten."),

    ("h2", "10. Marken und Bekanntmachungen"),
    ("num", "10.1", "Jede Partei räumt der anderen ein nicht ausschließliches, widerrufliches und "
                    "unentgeltliches Recht ein, ihren Namen und ihr Logo für die Laufzeit "
                    "ausschließlich zur Beschreibung der Partnerschaft zu verwenden."),
    ("num", "10.2", "Keine Partei wird ein Zeichen oder eine Domain anmelden, das oder die mit der "
                    "Kennzeichnung der anderen identisch oder verwechslungsfähig ähnlich ist."),
    ("num", "10.3", "Eine Pressemitteilung oder Fallstudie, die die andere nennt, bedarf deren "
                    "vorheriger schriftlicher Zustimmung, die nicht unbillig verweigert werden "
                    "darf."),

    ("h2", "11. Datenschutz"),
    ("num", "11.1", "Die Parteien schließen gemeinsam mit jedem Wiederverkäufer, der Partei einer "
                    "Durchgriffs- und Eintrittsvereinbarung ist, den Auftragsverarbeitungsvertrag, "
                    "der Art. 28 DSGVO genügt."),
    ("num", "11.2", "Die Plattform wird in Frankfurt am Main gehostet. Übermittlungen "
                    "personenbezogener Daten aus der Europäischen Union an den Distributor in der "
                    "Schweiz stützen sich auf den Angemessenheitsbeschluss der Europäischen "
                    "Kommission vom 15. Januar 2024."),

    ("h2", "12. Vertraulichkeit"),
    ("num", "12.1", "Jede Partei hält die vertraulichen Informationen der anderen geheim und "
                    "verwendet sie nur für diesen Vertrag; sie trifft angemessene "
                    "Geheimhaltungsmaßnahmen im Sinne des § 2 Nr. 1 lit. b GeschGehG."),
    ("num", "12.2", "Die Pflicht besteht drei Jahre über das Vertragsende hinaus fort. "
                    "Geschäftsgeheimnisse bleiben geschützt, solange sie diese Eigenschaft "
                    "besitzen."),

    ("h2", "13. Beschaffenheit, Mängel und Zusicherungen"),
    ("num", "13.1", "Der Hersteller stellt die Plattform als Dienst bereit. Die Parteien sind sich "
                    "einig, dass auf die Überlassung Mietrecht Anwendung findet."),
    ("num", "13.2", "Die verschuldensunabhängige Haftung für anfängliche Mängel nach § 536a Abs. 1 "
                    "Alt. 1 BGB wird ausgeschlossen. Der Hersteller haftet für solche Mängel nur "
                    "bei Verschulden."),
    ("num", "13.3", "Die vereinbarte Beschaffenheit ergibt sich aus der bei Bestellung aktuellen "
                    "Dokumentation und aus dem Service Level Agreement."),
    ("num", "13.4", "Der Hersteller sichert zu, dass die Plattform im Wesentlichen der "
                    "Dokumentation entspricht. Er sichert nicht zu, dass ein Assessment jede "
                    "Exposition erkennt, dass eine öffentliche Quelle vollständig oder zutreffend "
                    "ist oder dass ein Ergebnisdokument frei von Feststellungen ist, die sich "
                    "später als nicht einschlägig erweisen."),
    ("num", "13.5", "Der Hersteller sichert zu, Inhaber der von ihm eingeräumten Rechte zu sein "
                    "oder zu deren Einräumung berechtigt zu sein."),

    ("h2", "14. Haftung"),
    ("num", "14.1", "Jede Partei haftet unbeschränkt für Vorsatz und grobe Fahrlässigkeit, für "
                    "Schäden aus der Verletzung des Lebens, des Körpers oder der Gesundheit, nach "
                    "dem Produkthaftungsgesetz sowie bei Übernahme einer Garantie oder arglistigem "
                    "Verschweigen eines Mangels."),
    ("num", "14.2", "Bei einfacher Fahrlässigkeit haftet jede Partei nur bei Verletzung einer "
                    "wesentlichen Vertragspflicht, also einer Pflicht, deren Erfüllung die "
                    "ordnungsgemäße Durchführung dieses Vertrages überhaupt erst ermöglicht und auf "
                    "deren Einhaltung die andere Partei regelmäßig vertraut. Die Haftung ist dann "
                    "auf den vertragstypischen, vorhersehbaren Schaden begrenzt."),
    ("num", "14.3", "Vorbehaltlich der Ziffern 14.1 und 14.2 ist die Gesamthaftung des Herstellers "
                    "für einfache Fahrlässigkeit je Vertragsjahr auf die vom Distributor in den "
                    "zwölf Monaten vor dem Ereignis gezahlten Entgelte, höchstens jedoch auf [EUR "
                    "500.000] begrenzt, je nachdem welcher Betrag niedriger ist. DIESER BETRAG "
                    "BEGRENZT ZUGLEICH DIE GESAMTHAFTUNG DES HERSTELLERS GEGENÜBER DISTRIBUTOR UND "
                    "WIEDERVERKÄUFER ZUSAMMEN nach der Durchgriffs- und Eintrittsvereinbarung."),
    ("num", "14.4", "Eine weitergehende Haftung ist ausgeschlossen, insbesondere für entgangenen "
                    "Gewinn und mittelbare Schäden, soweit nicht Ziffer 14.1 eingreift."),
    ("num", "14.5", "Die Beschränkungen gelten auch zugunsten der persönlichen Haftung der "
                    "Mitarbeiter, Vertreter, Organe und Erfüllungsgehilfen der Parteien."),
    ("num", "14.6", "Die Verjährungsfrist für Mängelansprüche beträgt ein Jahr ab dem gesetzlichen "
                    "Verjährungsbeginn, ausgenommen Ansprüche nach Ziffer 14.1."),

    ("h2", "15. Freistellungen"),
    ("num", "15.1", "Der Hersteller stellt den Distributor von Ansprüchen Dritter frei, die "
                    "geltend machen, die vertragsgemäße Nutzung der Plattform verletze ein "
                    "Schutzrecht, sofern der Distributor unverzüglich informiert, dem Hersteller "
                    "die Verteidigung überlässt und ohne Zustimmung keinen Vergleich schließt."),
    ("num", "15.2", "Der Hersteller kann nach eigener Wahl das Recht zur weiteren Nutzung "
                    "beschaffen, die Plattform ändern oder die betroffene Bestellung kündigen und "
                    "die für die ungenutzte Restlaufzeit gezahlten Entgelte erstatten."),
    ("num", "15.3", "Der Distributor stellt den Hersteller von Ansprüchen Dritter frei, die auf "
                    "einer über Ziffer 6.1 hinausgehenden Erklärung des Distributors oder seines "
                    "Wiederverkäufers oder auf einem Assessment gegen ein Unternehmen beruhen, zu "
                    "dessen Bewertung er nicht berechtigt war."),

    ("h2", "16. Laufzeit und Kündigung"),
    ("num", "16.1", "Dieser Vertrag läuft 24 Monate und verlängert sich um jeweils 12 Monate, "
                    "sofern nicht eine Partei mit einer Frist von drei Monaten zum Ende der "
                    "jeweiligen Laufzeit kündigt."),
    ("num", "16.2", "Jede Partei kann aus wichtigem Grund im Sinne des § 314 BGB kündigen, "
                    "insbesondere bei einer nach 30-tägiger schriftlicher Aufforderung nicht "
                    "behobenen wesentlichen Pflichtverletzung, bei Insolvenz oder bei Sanktionen."),
    ("num", "16.3", "Mit Beendigung stellt der Distributor die Vermarktung ein. Angefallene "
                    "Entgelte bleiben geschuldet."),
    ("num", "16.4", "DIE BEENDIGUNG LÄSST WEDER EINEN WIEDERVERKÄUFER NOCH EINEN ENDKUNDEN "
                    "ZURÜCK. Besteht eine Durchgriffs- und Eintrittsvereinbarung, gelten deren "
                    "Eintrittsregelungen und gehen dieser Ziffer vor."),
    ("num", "16.5", "Die Ziffern 4.4, 10, 11, 12, 14, 15, 16 und 18 gelten fort."),

    ("h2", "17. Eskalation"),
    ("num", "17.1", "Eine Streitigkeit wird an die kommerziell Verantwortlichen und sodann binnen "
                    "zehn Arbeitstagen an je ein Mitglied der Geschäftsleitung eskaliert, bevor ein "
                    "Verfahren eingeleitet wird; ausgenommen sind einstweiliger Rechtsschutz, "
                    "Zahlungsklagen und Fälle drohender Verjährung."),

    ("h2", "18. Schlussbestimmungen und anwendbares Recht"),
    ("num", "18.1", "Änderungen bedürfen der Textform. Mündliche Nebenabreden bestehen nicht."),
    ("num", "18.2", "Keine Partei darf ohne schriftliche Zustimmung der anderen abtreten; die "
                    "Zustimmung darf nicht unbillig verweigert werden. § 354a HGB bleibt "
                    "unberührt."),
    ("num", "18.3", "Keine Partei haftet für eine Leistungsstörung aufgrund eines Ereignisses "
                    "außerhalb ihres zumutbaren Einflussbereichs, solange dieses andauert und sie "
                    "informiert und mindert."),
    ("num", "18.4", "Ist eine Bestimmung unwirksam, bleibt der übrige Inhalt unberührt."),
    ("num", "18.5", "Dieser Vertrag wird in deutscher und in englischer Sprache ausgefertigt. Bei "
                    "Abweichungen ist die [deutsche] Fassung maßgeblich."),
    ("num", "18.6", "Dieser Vertrag unterliegt %s unter Ausschluss seiner Kollisionsnormen und des "
                    "UN-Kaufrechts. Ausschließlicher Gerichtsstand ist %s." % (LAW_DE, FORUM)),

    ("pagebreak",),
    ("h2", "Anlage 1 - Parteiangaben, Gebiet und bestellte Wiederverkäufer"),
    ("table", ["Angabe", "Hersteller", "Distributor"], [
        ["Rechtsträger", VENDOR["name"], OBJECTALE["name"]],
        ["Sitz", VENDOR["addr_de"], OBJECTALE["addr_de"]],
        ["Register", VENDOR["reg_de"], OBJECTALE["reg"]],
        ["USt-IdNr.", VENDOR["vat"], "[CHE-___.___.___ MWST]"],
        ["Vertreten durch", "[Name, Funktion]", "[Name, Funktion]"],
        ["Kaufmännischer Kontakt", "[Name] · [E-Mail]", "[Name] · [E-Mail]"],
        ["Technischer Kontakt", "[Name] · [E-Mail]", "[Name] · [E-Mail]"],
        ["Zustelladresse", VENDOR["mail"], OBJECTALE["mail"]],
        ["Gebiet", "[Deutschland, Österreich und die Schweiz]", "-"],
    ]),
    ("h3", "Bestellte Wiederverkäufer"),
    ("table", ["#", "Wiederverkäufer", "Land", "Durchgriffsvereinbarung unterzeichnet"], [
        ["1", BYON["name"], "Deutschland", "[ja / Datum]"],
        ["2", "[ ]", "[ ]", "[ ]"],
        ["3", "[ ]", "[ ]", "[ ]"],
    ]),

    ("pagebreak",),
    ("h2", "Anlage 2 - Listenpreise und Rabatt des Distributors"),
    ("table", ["Position", "Listenpreis, EUR zzgl. USt."], [[a, b] for a, b in LIST_PRICES_DE]),
    ("table", ["Angabe", "Detail"], [
        ["Rabatt des Distributors auf Liste", "[__]% für die Erstlaufzeit"],
        ["Mindestabnahme", "[keine / __ Seats / __ Läufe je Quartal]"],
        ["Enthaltene Läufe je Abonnement-Seat und Monat", "[__]"],
        ["Preis eines Laufs über die enthaltene Anzahl hinaus", "[EUR __]"],
        ["Überprüfung des Rabatts", "Jährlich zum Jahrestag des Inkrafttretens"],
    ]),
    ("note", "Der Rabatt des Distributors muss Raum für einen darunterliegenden Rabatt des "
             "Wiederverkäufers und für dessen Marge lassen. Diese Zahl festzulegen, ohne "
             "gleichzeitig die Wiederverkäuferstufe zu bestimmen, erzeugt einen Kanal, in dem "
             "niemand verdienen kann."),

    ("pagebreak",),
    ("h2", "Anlage 3 - Muster einer Bestellung"),
    ("table", ["Angabe", "Detail"], [
        ["Bestellnummer", "[ ]"],
        ["Datum des Inkrafttretens", "[ ]"],
        ["Wiederverkäufer und Endkunde, sofern die Bestellung ein benanntes Geschäft betrifft",
         "[ ]"],
        ["Laufzeit", "[ ]"],
        ["Angewandter Rabatt", "[ ]"],
        ["Abrechnungsintervall", "[monatlich im Voraus / bei Lieferung]"],
    ]),
    ("table", ["Pos.", "Position", "Menge", "Einzelpreis, EUR zzgl. USt.", "Summe je Periode"], [
        ["1", "Report-Abonnement-Seats", "[ ]", "[ ]", "[ ]"],
        ["2", "Assessment-Läufe über die enthaltene Anzahl hinaus", "Nach Verbrauch", "[ ]", "[ ]"],
        ["3", "Findings-Review-Stunden", "[ ]", "[ ]", "[ ]"],
        ["4", "Workshops", "[ ]", "[ ]", "[ ]"],
        ["5", "Sonstiges", "[ ]", "[ ]", "[ ]"],
    ]),

    ("pagebreak",),
    ("h2", "Unterschriften"),
    ("sig", "Für %s (Hersteller)" % VENDOR["name"],
     "Für %s (Distributor)" % OBJECTALE["name"],
     ["Name:", "Funktion:", "Ort:", "Datum:"]),
]
