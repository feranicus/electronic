# -*- coding: utf-8 -*-
"""06 - Tripartite flow-down and step-in deed. Vendor, Distributor and Reseller.

THIS IS THE DOCUMENT YOU HAND TO AN ENTERPRISE PROCUREMENT TEAM. Everything else in the pack is
bilateral and confidential; this one is short, signed by all three, and answers the three questions
a large customer's counsel actually asks:

  1. Who owns the thing, and did the person selling it to us have the right to?     (clause 2)
  2. What happens to us if the middle company disappears?                           (clause 5)
  3. Who can we hold to the acceptable-use and IP terms?                            (clause 3)

IT DELIBERATELY CONTAINS NO PRICES. The whole economics of two-tier distribution is that the
Distributor's buy price and the Reseller's buy price are invisible to each other. Put a number in
here and the structure collapses into a single negotiation.

THE STEP-IN IS THE PART WITH TEETH. Clause 5 obliges the Vendor to contract directly with the
Reseller if the distribution agreement ends, for as long as the Reseller's own customer commitments
run. Without it, a customer of byon loses its service because of a dispute two tiers up that it was
never party to and could not have foreseen.
"""
from common import BYON, DATE_DE, DATE_EN, FORUM, LAW_DE, LAW_EN, NOTE_DE, NOTE_EN, OBJECTALE, \
    PLATFORM, VENDOR, VERSION

EN = [
    ("h1", "FLOW-DOWN AND STEP-IN DEED"),
    ("meta", "%s · %s · %s  ·  Version %s  ·  %s  ·  German law, %s"
     % (VENDOR["name"], OBJECTALE["name"], BYON["name"], VERSION, DATE_EN, FORUM)),

    ("p", "This Deed takes effect on [effective date] between:"),
    ("p", "%s, %s, registered under %s (the \"Vendor\");"
     % (VENDOR["name"], VENDOR["addr"], VENDOR["reg"])),
    ("p", "%s, %s, registered under %s (the \"Distributor\"); and"
     % (OBJECTALE["name"], OBJECTALE["addr"], OBJECTALE["reg"])),
    ("p", "%s, %s, registered with the %s (the \"Reseller\")."
     % (BYON["name"], BYON["addr"], BYON["reg"])),
    ("p", "Each a \"party\" and together the \"parties\"."),
    ("note", NOTE_EN),

    ("h2", "Background"),
    ("p", "A. The Vendor owns and operates %s, an external cyber-risk and EU regulatory-compliance "
          "assessment platform (the \"Platform\")." % PLATFORM),
    ("p", "B. The Vendor and the Distributor have entered into a distribution agreement (the "
          "\"Distribution Agreement\") under which the Distributor may appoint resellers."),
    ("p", "C. The Distributor and the Reseller have entered into a reseller framework agreement "
          "(the \"Reseller Agreement\") under which the Reseller supplies the Platform to its own "
          "customers (each an \"End Customer\")."),
    ("p", "D. The parties wish to record the rights that pass directly from the Vendor to the "
          "Reseller and to each End Customer, what the Reseller must pass on, and what happens to "
          "the Reseller and its End Customers if the Distribution Agreement ends."),

    ("h2", "1. Structure and precedence"),
    ("num", "1.1", "The Distribution Agreement governs the commercial relationship between the "
                   "Vendor and the Distributor. The Reseller Agreement governs the commercial "
                   "relationship between the Distributor and the Reseller. Neither is varied by "
                   "this Deed except where this Deed says so expressly."),
    ("num", "1.2", "Commercial terms, including prices, discounts and volume commitments, are not "
                   "part of this Deed and are not disclosed by it. No party is entitled to see "
                   "another tier's commercial terms by reason of this Deed."),
    ("num", "1.3", "Where this Deed conflicts with the Distribution Agreement or the Reseller "
                   "Agreement on a matter this Deed addresses, this Deed prevails."),

    ("h2", "2. The chain of rights"),
    ("num", "2.1", "The Vendor confirms that it owns or is licensed to grant all rights in the "
                   "Platform necessary for the supply contemplated by the Distribution Agreement "
                   "and the Reseller Agreement."),
    ("num", "2.2", "The Vendor confirms that the Distribution Agreement is in force and authorises "
                   "the Distributor to appoint the Reseller on the terms of the Reseller "
                   "Agreement."),
    ("num", "2.3", "DIRECT GRANT. The Vendor grants the Reseller, for the term and in the "
                   "Territory, a non-exclusive right to access and use the Platform, to demonstrate "
                   "it, and to supply rights of use to End Customers. That grant is made by the "
                   "Vendor directly and does not depend on a sub-licence from the Distributor."),
    ("num", "2.4", "DIRECT GRANT TO THE END CUSTOMER. Each End Customer receives its right of use "
                   "directly from the Vendor on the End-User Terms in Schedule 1, which the "
                   "Reseller incorporates into its own contract with that End Customer. The "
                   "Reseller does not purport to sub-licence the Platform."),
    ("num", "2.5", "Nothing in clause 2.3 or 2.4 gives the Reseller or an End Customer a right to "
                   "receive the Platform without paying for it, or affects the Vendor's right to "
                   "suspend access under clause 4."),
    ("num", "2.6", "Trade follows the chain. The Reseller orders from the Distributor and pays the "
                   "Distributor; the Distributor orders from the Vendor and pays the Vendor. The "
                   "Vendor has no claim against the Reseller for fees, and the Reseller has no "
                   "claim against the Vendor for fees, save under clause 5."),

    ("h2", "3. What the Reseller must pass on"),
    ("num", "3.1", "The Reseller will incorporate the End-User Terms in Schedule 1 into every "
                   "contract under which it supplies the Platform, without material change."),
    ("num", "3.2", "The Reseller will not make any representation or warranty about the Platform "
                   "beyond the Vendor's current documentation, and will not commit the Vendor or "
                   "the Distributor to a service level, a functionality or a delivery date."),
    ("num", "3.3", "THE VENDOR MAY ENFORCE DIRECTLY. The Vendor may enforce clauses 3.1, 3.2 and "
                   "the acceptable-use provisions of the End-User Terms against the Reseller, and "
                   "against an End Customer to the extent the End-User Terms so provide, without "
                   "joining the Distributor."),
    ("num", "3.4", "The Reseller will notify the Vendor and the Distributor without undue delay of "
                   "any use of the Platform that it becomes aware of which breaches the "
                   "acceptable-use provisions."),
    ("num", "3.5", "Where an End Customer is a public body, an operator of critical infrastructure "
                   "or a regulated financial institution, the Reseller will tell the Distributor "
                   "before the order is placed, and the Distributor will tell the Vendor, so that "
                   "any additional regulatory requirement is addressed before commitments are "
                   "made."),

    ("h2", "4. Suspension"),
    ("num", "4.1", "The Vendor may suspend access to the Platform for a named user, for the "
                   "Reseller or for an End Customer where it reasonably believes that credentials "
                   "have been compromised, or that use materially threatens the security or "
                   "integrity of the Platform, or where suspension is required by law or by "
                   "sanctions."),
    ("num", "4.2", "The Vendor will notify the Distributor and the Reseller of the reason without "
                   "undue delay, will limit the suspension to what the risk requires, and will "
                   "restore access as soon as the cause is removed."),
    ("num", "4.3", "A suspension for non-payment is exercised only against the tier that has not "
                   "paid, and only after that tier has been given 15 business days' written notice "
                   "and has not cured. An End Customer is not suspended for a non-payment upstream "
                   "of the Reseller for as long as that End Customer is paying the Reseller."),

    ("h2", "5. Step-in"),
    ("p", "This is the clause an End Customer's counsel is looking for."),
    ("num", "5.1", "If the Distribution Agreement ends for any reason, the Vendor will, at the "
                   "Reseller's written request made within 30 days, enter into a direct agreement "
                   "with the Reseller on terms materially equivalent to the Reseller Agreement, "
                   "excluding any term that is personal to the Distributor."),
    ("num", "5.2", "That direct agreement runs for the longer of the unexpired term of the "
                   "Reseller Agreement and the unexpired term of the Reseller's contracts with End "
                   "Customers existing at the date the Distribution Agreement ended, capped at 24 "
                   "months."),
    ("num", "5.3", "The commercial terms of the direct agreement are the Reseller's then-current "
                   "prices under the Reseller Agreement, unless the Reseller Agreement ended "
                   "because of the Reseller's own material breach, in which case clause 5.5 "
                   "applies instead."),
    ("num", "5.4", "The Distributor consents in advance to clauses 5.1 to 5.3 and will not claim "
                   "that the arrangement circumvents it. The Distributor is entitled to be paid "
                   "everything accrued to it up to the date the Distribution Agreement ends."),
    ("num", "5.5", "Where the Reseller Agreement ends because of the Reseller's material breach, "
                   "or the Reseller is subject to sanctions or insolvency, no step-in arises. In "
                   "that case the Vendor and the Distributor will use reasonable efforts to offer "
                   "each affected End Customer continuity of service on the End-User Terms, "
                   "directly or through another reseller."),
    ("num", "5.6", "Each party will do what is reasonably necessary to give effect to this clause, "
                   "including transferring account configuration and giving the Reseller and its "
                   "End Customers a reasonable period to export their documents."),

    ("h2", "6. Data protection"),
    ("num", "6.1", "The Vendor operates the Platform and processes personal data. The Reseller is "
                   "the controller for its own users' account data. The parties enter into the "
                   "tripartite data processing agreement, which satisfies Article 28 GDPR."),
    ("num", "6.2", "The Distributor is a processor only in respect of the support and commercial "
                   "correspondence it handles. It has no access to the Platform's data stores "
                   "except as recorded in that agreement."),
    ("num", "6.3", "An End Customer's own contract with the Reseller governs the processing "
                   "between them. Neither the Vendor nor the Distributor is a party to it."),

    ("h2", "7. Liability between the tiers"),
    ("num", "7.1", "Each party's liability under the agreement to which it is a party is governed "
                   "by that agreement. This Deed creates no additional liability except as stated "
                   "in this clause."),
    ("num", "7.2", "AGGREGATE CAP ACROSS THE CHAIN. The Vendor's aggregate liability to the "
                   "Distributor and the Reseller combined, in respect of the same event or series "
                   "of connected events, does not exceed the cap in the Distribution Agreement. "
                   "The Vendor is not exposed twice for one failure because there are two tiers."),
    ("num", "7.3", "Nothing in this Deed limits liability for intent or gross negligence, for "
                   "injury to life, body or health, under the German Product Liability Act, or "
                   "under a guarantee expressly given."),
    ("num", "7.4", "No party is liable to another for the acts of an End Customer, save where that "
                   "party procured or knowingly permitted the act."),

    ("h2", "8. Confidentiality and announcements"),
    ("num", "8.1", "Each party will keep the others' confidential information secret on the terms "
                   "of the non-disclosure agreement between them, and in any event will not "
                   "disclose another tier's commercial terms."),
    ("num", "8.2", "A public announcement naming another party requires that party's prior written "
                   "approval, not to be unreasonably withheld."),
    ("num", "8.3", "The Reseller may show this Deed, in full, to an End Customer or a prospective "
                   "End Customer under a duty of confidence. That is what it is for."),

    ("h2", "9. Term"),
    ("num", "9.1", "This Deed takes effect on the effective date and continues while both the "
                   "Distribution Agreement and the Reseller Agreement are in force."),
    ("num", "9.2", "Clauses 5, 6, 7, 8 and 10 survive, and clause 5 survives for the period it "
                   "provides for."),

    ("h2", "10. General"),
    ("num", "10.1", "Variations require text form signed by all three parties."),
    ("num", "10.2", "No party may assign this Deed without the written consent of the others, "
                    "except to an affiliate or in connection with a transfer of the whole business, "
                    "which must be notified."),
    ("num", "10.3", "If a provision is invalid the remainder is unaffected and the parties will "
                    "replace it with a valid provision closest to its purpose."),
    ("num", "10.4", "This Deed is executed in German and in English. In the event of a discrepancy "
                    "the [German] version prevails."),
    ("num", "10.5", "The parties may sign in counterparts and by qualified or advanced electronic "
                    "signature."),

    ("h2", "11. Governing law and jurisdiction"),
    ("num", "11.1", "This Deed is governed by %s, excluding its conflict of laws rules and the "
                    "United Nations Convention on Contracts for the International Sale of Goods."
     % LAW_EN),
    ("num", "11.2", "The exclusive place of jurisdiction for all disputes arising out of or in "
                    "connection with this Deed is %s." % FORUM),

    ("pagebreak",),
    ("h2", "Schedule 1 - End-User Terms"),
    ("p", "The End-User Terms are the separate document of that name, in the version current at "
          "the date of the End Customer's order. The Vendor will give the Distributor and the "
          "Reseller 30 days' notice of a change, and a change does not apply to an End Customer "
          "contract already signed until its renewal."),
    ("table", ["Item", "Detail"], [
        ["Version of the End-User Terms in force at signature", "[version] dated [date]"],
        ["Territory", "[Germany, Austria and Switzerland]"],
        ["Vendor notice address", VENDOR["mail"]],
        ["Distributor notice address", OBJECTALE["mail"]],
        ["Reseller notice address", BYON["mail"]],
        ["Vendor escalation contact", "[name] · [e-mail] · [telephone]"],
    ]),

    ("pagebreak",),
    ("h2", "Signatures"),
    ("p", "Signed by the three parties on the dates shown."),
    ("sig", "For %s (Vendor)" % VENDOR["name"], "For %s (Distributor)" % OBJECTALE["name"],
     ["Name:", "Function:", "Place:", "Date:"]),
    ("sig", "For %s (Reseller)" % BYON["name"], "",
     ["Name:", "Function:", "Place:", "Date:"]),
]

DE = [
    ("h1", "DURCHGRIFFS- UND EINTRITTSVEREINBARUNG"),
    ("meta", "%s · %s · %s  ·  Version %s  ·  %s  ·  Deutsches Recht, %s"
     % (VENDOR["name"], OBJECTALE["name"], BYON["name"], VERSION, DATE_DE, FORUM)),

    ("p", "Diese Vereinbarung tritt am [Datum des Inkrafttretens] in Kraft zwischen:"),
    ("p", "%s, %s, eingetragen unter %s (der \"Hersteller\");"
     % (VENDOR["name"], VENDOR["addr_de"], VENDOR["reg_de"])),
    ("p", "%s, %s, eingetragen unter %s (der \"Distributor\"); und"
     % (OBJECTALE["name"], OBJECTALE["addr_de"], OBJECTALE["reg"])),
    ("p", "%s, %s, eingetragen beim %s (der \"Wiederverkäufer\")."
     % (BYON["name"], BYON["addr_de"], BYON["reg"])),
    ("p", "Jeweils eine \"Partei\" und gemeinsam die \"Parteien\"."),
    ("note", NOTE_DE),

    ("h2", "Präambel"),
    ("p", "A. Der Hersteller ist Inhaber und Hersteller von %s, einer Plattform zur Bewertung "
          "externer Cyber-Risiken und der EU-Regulierungs-Compliance (die \"Plattform\")."
     % PLATFORM),
    ("p", "B. Hersteller und Distributor haben einen Distributionsvertrag (der "
          "\"Distributionsvertrag\") geschlossen, der den Distributor berechtigt, Wiederverkäufer "
          "zu bestellen."),
    ("p", "C. Distributor und Wiederverkäufer haben einen Wiederverkäufer-Rahmenvertrag (der "
          "\"Wiederverkäufervertrag\") geschlossen, unter dem der Wiederverkäufer die Plattform an "
          "eigene Kunden (jeweils ein \"Endkunde\") liefert."),
    ("p", "D. Die Parteien wollen festhalten, welche Rechte unmittelbar vom Hersteller auf den "
          "Wiederverkäufer und auf jeden Endkunden übergehen, was der Wiederverkäufer weitergeben "
          "muss und was mit dem Wiederverkäufer und seinen Endkunden geschieht, wenn der "
          "Distributionsvertrag endet."),

    ("h2", "1. Struktur und Rangfolge"),
    ("num", "1.1", "Der Distributionsvertrag regelt die kommerzielle Beziehung zwischen Hersteller "
                   "und Distributor. Der Wiederverkäufervertrag regelt die kommerzielle Beziehung "
                   "zwischen Distributor und Wiederverkäufer. Keiner von beiden wird durch diese "
                   "Vereinbarung geändert, außer soweit hier ausdrücklich bestimmt."),
    ("num", "1.2", "Kommerzielle Bedingungen, einschließlich Preisen, Rabatten und Mengenzusagen, "
                   "sind nicht Gegenstand dieser Vereinbarung und werden durch sie nicht "
                   "offengelegt. Keine Partei ist aufgrund dieser Vereinbarung berechtigt, die "
                   "kommerziellen Bedingungen einer anderen Stufe einzusehen."),
    ("num", "1.3", "Widerspricht diese Vereinbarung dem Distributionsvertrag oder dem "
                   "Wiederverkäufervertrag in einer hier geregelten Frage, geht diese Vereinbarung "
                   "vor."),

    ("h2", "2. Die Rechtekette"),
    ("num", "2.1", "Der Hersteller bestätigt, dass er Inhaber sämtlicher für die im "
                   "Distributionsvertrag und im Wiederverkäufervertrag vorgesehene Lieferung "
                   "erforderlichen Rechte an der Plattform ist oder zu deren Einräumung berechtigt "
                   "ist."),
    ("num", "2.2", "Der Hersteller bestätigt, dass der Distributionsvertrag in Kraft ist und den "
                   "Distributor berechtigt, den Wiederverkäufer zu den Bedingungen des "
                   "Wiederverkäufervertrages zu bestellen."),
    ("num", "2.3", "UNMITTELBARE EINRÄUMUNG. Der Hersteller räumt dem Wiederverkäufer für die "
                   "Laufzeit und im Gebiet das nicht ausschließliche Recht ein, auf die Plattform "
                   "zuzugreifen, sie zu nutzen, sie vorzuführen und Nutzungsrechte an Endkunden zu "
                   "liefern. Diese Einräumung erfolgt unmittelbar durch den Hersteller und hängt "
                   "nicht von einer Unterlizenz des Distributors ab."),
    ("num", "2.4", "UNMITTELBARE EINRÄUMUNG AN DEN ENDKUNDEN. Jeder Endkunde erhält sein "
                   "Nutzungsrecht unmittelbar vom Hersteller auf Grundlage der Endkundenbedingungen "
                   "nach Anlage 1, die der Wiederverkäufer in seinen eigenen Vertrag mit diesem "
                   "Endkunden einbezieht. Der Wiederverkäufer erteilt keine Unterlizenz an der "
                   "Plattform."),
    ("num", "2.5", "Ziffern 2.3 und 2.4 begründen kein Recht des Wiederverkäufers oder eines "
                   "Endkunden, die Plattform ohne Entgelt zu erhalten, und berühren das "
                   "Sperrungsrecht des Herstellers nach Ziffer 4 nicht."),
    ("num", "2.6", "Der Handel folgt der Kette. Der Wiederverkäufer bestellt beim Distributor und "
                   "zahlt an den Distributor; der Distributor bestellt beim Hersteller und zahlt an "
                   "den Hersteller. Der Hersteller hat gegen den Wiederverkäufer keinen "
                   "Entgeltanspruch und der Wiederverkäufer gegen den Hersteller keinen, "
                   "vorbehaltlich Ziffer 5."),

    ("h2", "3. Weitergabepflichten des Wiederverkäufers"),
    ("num", "3.1", "Der Wiederverkäufer bezieht die Endkundenbedingungen nach Anlage 1 ohne "
                   "wesentliche Änderung in jeden Vertrag ein, unter dem er die Plattform liefert."),
    ("num", "3.2", "Der Wiederverkäufer gibt über die aktuelle Dokumentation des Herstellers hinaus "
                   "keine Zusicherungen oder Garantien zur Plattform ab und verpflichtet weder den "
                   "Hersteller noch den Distributor auf ein Service Level, eine Funktionalität oder "
                   "einen Liefertermin."),
    ("num", "3.3", "UNMITTELBARE DURCHSETZUNG DURCH DEN HERSTELLER. Der Hersteller kann die "
                   "Ziffern 3.1 und 3.2 sowie die Nutzungsbeschränkungen der Endkundenbedingungen "
                   "unmittelbar gegenüber dem Wiederverkäufer und, soweit die Endkundenbedingungen "
                   "dies vorsehen, gegenüber einem Endkunden durchsetzen, ohne den Distributor "
                   "beiladen zu müssen."),
    ("num", "3.4", "Der Wiederverkäufer informiert Hersteller und Distributor unverzüglich über "
                   "jede ihm bekannt werdende Nutzung der Plattform, die gegen die "
                   "Nutzungsbeschränkungen verstößt."),
    ("num", "3.5", "Ist ein Endkunde eine öffentliche Stelle, ein Hersteller kritischer "
                   "Infrastrukturen oder ein beaufsichtigtes Finanzinstitut, informiert der "
                   "Wiederverkäufer vor Erteilung der Bestellung den Distributor und dieser den "
                   "Hersteller, damit zusätzliche aufsichtsrechtliche Anforderungen vor der "
                   "Eingehung von Verpflichtungen berücksichtigt werden."),

    ("h2", "4. Sperrung"),
    ("num", "4.1", "Der Hersteller darf den Zugang zur Plattform für einen benannten Nutzer, für "
                   "den Wiederverkäufer oder für einen Endkunden sperren, wenn er berechtigterweise "
                   "von einer Kompromittierung der Zugangsdaten ausgeht, wenn die Nutzung die "
                   "Sicherheit oder Integrität der Plattform erheblich gefährdet oder wenn die "
                   "Sperrung gesetzlich oder aufgrund von Sanktionen geboten ist."),
    ("num", "4.2", "Der Hersteller teilt Distributor und Wiederverkäufer den Grund unverzüglich "
                   "mit, beschränkt die Sperrung auf das vom Risiko Gebotene und stellt den Zugang "
                   "wieder her, sobald die Ursache entfallen ist."),
    ("num", "4.3", "Eine Sperrung wegen Zahlungsverzugs erfolgt nur gegenüber der säumigen Stufe "
                   "und erst, nachdem dieser Stufe eine Frist von 15 Arbeitstagen schriftlich "
                   "gesetzt wurde und sie nicht erfüllt hat. Ein Endkunde wird wegen eines "
                   "Zahlungsverzugs oberhalb des Wiederverkäufers nicht gesperrt, solange dieser "
                   "Endkunde an den Wiederverkäufer zahlt."),

    ("h2", "5. Eintrittsrecht"),
    ("p", "Dies ist die Klausel, nach der die Rechtsabteilung eines Endkunden sucht."),
    ("num", "5.1", "Endet der Distributionsvertrag aus welchem Grund auch immer, schließt der "
                   "Hersteller auf schriftliches Verlangen des Wiederverkäufers, das binnen 30 "
                   "Tagen zu stellen ist, einen unmittelbaren Vertrag mit dem Wiederverkäufer zu "
                   "im Wesentlichen gleichwertigen Bedingungen wie der Wiederverkäufervertrag, "
                   "ausgenommen Regelungen, die dem Distributor persönlich zustehen."),
    ("num", "5.2", "Dieser unmittelbare Vertrag läuft für den längeren der beiden Zeiträume: die "
                   "Restlaufzeit des Wiederverkäufervertrages oder die Restlaufzeit der im "
                   "Zeitpunkt der Beendigung des Distributionsvertrages bestehenden Verträge des "
                   "Wiederverkäufers mit Endkunden, höchstens jedoch 24 Monate."),
    ("num", "5.3", "Kommerziell gelten die zu diesem Zeitpunkt aktuellen Preise des "
                   "Wiederverkäufers aus dem Wiederverkäufervertrag, es sei denn, der "
                   "Wiederverkäufervertrag endete wegen einer wesentlichen Pflichtverletzung des "
                   "Wiederverkäufers; dann gilt Ziffer 5.5."),
    ("num", "5.4", "Der Distributor stimmt den Ziffern 5.1 bis 5.3 im Voraus zu und wird nicht "
                   "einwenden, dass die Regelung ihn umgeht. Dem Distributor steht alles zu, was "
                   "ihm bis zur Beendigung des Distributionsvertrages angefallen ist."),
    ("num", "5.5", "Endet der Wiederverkäufervertrag wegen einer wesentlichen Pflichtverletzung des "
                   "Wiederverkäufers oder unterliegt dieser Sanktionen oder einem "
                   "Insolvenzverfahren, entsteht kein Eintrittsrecht. In diesem Fall werden "
                   "Hersteller und Distributor sich in zumutbarem Umfang bemühen, jedem betroffenen "
                   "Endkunden die Fortführung des Dienstes zu den Endkundenbedingungen anzubieten, "
                   "unmittelbar oder über einen anderen Wiederverkäufer."),
    ("num", "5.6", "Jede Partei unternimmt das zumutbar Erforderliche, um dieser Ziffer Wirkung zu "
                   "verschaffen, einschließlich der Übertragung der Kontokonfiguration und der "
                   "Einräumung einer angemessenen Frist für den Export der Dokumente durch den "
                   "Wiederverkäufer und seine Endkunden."),

    ("h2", "6. Datenschutz"),
    ("num", "6.1", "Der Hersteller betreibt die Plattform und verarbeitet personenbezogene Daten. "
                   "Der Wiederverkäufer ist Verantwortlicher für die Kontodaten der eigenen Nutzer. "
                   "Die Parteien schließen den dreiseitigen Auftragsverarbeitungsvertrag, der Art. "
                   "28 DSGVO genügt."),
    ("num", "6.2", "Der Distributor ist Auftragsverarbeiter ausschließlich hinsichtlich der von ihm "
                   "bearbeiteten Support- und Geschäftskorrespondenz. Er hat auf die Datenbestände "
                   "der Plattform keinen Zugriff, soweit dort nicht anders geregelt."),
    ("num", "6.3", "Für die Verarbeitung zwischen einem Endkunden und dem Wiederverkäufer gilt "
                   "deren eigener Vertrag. Weder Hersteller noch Distributor sind daran beteiligt."),

    ("h2", "7. Haftung zwischen den Stufen"),
    ("num", "7.1", "Die Haftung jeder Partei richtet sich nach dem Vertrag, dessen Partei sie ist. "
                   "Diese Vereinbarung begründet keine zusätzliche Haftung außer nach dieser "
                   "Ziffer."),
    ("num", "7.2", "GESAMTOBERGRENZE ÜBER DIE KETTE. Die Gesamthaftung des Herstellers gegenüber "
                   "Distributor und Wiederverkäufer zusammen für dasselbe Ereignis oder eine Reihe "
                   "zusammenhängender Ereignisse übersteigt die Haftungsobergrenze des "
                   "Distributionsvertrages nicht. Der Hersteller haftet für ein Versagen nicht "
                   "doppelt, nur weil es zwei Stufen gibt."),
    ("num", "7.3", "Diese Vereinbarung begrenzt nicht die Haftung für Vorsatz oder grobe "
                   "Fahrlässigkeit, für Schäden aus der Verletzung des Lebens, des Körpers oder der "
                   "Gesundheit, nach dem Produkthaftungsgesetz oder aus einer ausdrücklich "
                   "übernommenen Garantie."),
    ("num", "7.4", "Keine Partei haftet einer anderen für Handlungen eines Endkunden, es sei denn, "
                   "sie hat die Handlung veranlasst oder wissentlich zugelassen."),

    ("h2", "8. Vertraulichkeit und Bekanntmachungen"),
    ("num", "8.1", "Jede Partei hält die vertraulichen Informationen der anderen nach Maßgabe der "
                   "zwischen ihnen bestehenden Geheimhaltungsvereinbarung geheim und wird "
                   "jedenfalls die kommerziellen Bedingungen einer anderen Stufe nicht offenlegen."),
    ("num", "8.2", "Eine öffentliche Bekanntmachung, die eine andere Partei nennt, bedarf deren "
                   "vorheriger schriftlicher Zustimmung, die nicht unbillig verweigert werden darf."),
    ("num", "8.3", "Der Wiederverkäufer darf diese Vereinbarung einem Endkunden oder einem "
                   "potenziellen Endkunden unter Geheimhaltungspflicht vollständig vorlegen. Dafür "
                   "ist sie gedacht."),

    ("h2", "9. Laufzeit"),
    ("num", "9.1", "Diese Vereinbarung tritt am Datum des Inkrafttretens in Kraft und besteht, "
                   "solange sowohl der Distributionsvertrag als auch der Wiederverkäufervertrag in "
                   "Kraft sind."),
    ("num", "9.2", "Die Ziffern 5, 6, 7, 8 und 10 gelten fort; Ziffer 5 für den dort vorgesehenen "
                   "Zeitraum."),

    ("h2", "10. Allgemeines"),
    ("num", "10.1", "Änderungen bedürfen der Textform und der Unterzeichnung durch alle drei "
                    "Parteien."),
    ("num", "10.2", "Keine Partei darf diese Vereinbarung ohne schriftliche Zustimmung der anderen "
                    "abtreten, ausgenommen an ein verbundenes Unternehmen oder im Zusammenhang mit "
                    "einer Übertragung des gesamten Geschäftsbetriebs; dies ist anzuzeigen."),
    ("num", "10.3", "Ist eine Bestimmung unwirksam, bleibt der übrige Inhalt unberührt; die "
                    "Parteien ersetzen sie durch eine wirksame Bestimmung, die ihrem Zweck am "
                    "nächsten kommt."),
    ("num", "10.4", "Diese Vereinbarung wird in deutscher und in englischer Sprache ausgefertigt. "
                    "Bei Abweichungen ist die [deutsche] Fassung maßgeblich."),
    ("num", "10.5", "Die Parteien können in Ausfertigungen und mittels qualifizierter oder "
                    "fortgeschrittener elektronischer Signatur unterzeichnen."),

    ("h2", "11. Anwendbares Recht und Gerichtsstand"),
    ("num", "11.1", "Diese Vereinbarung unterliegt %s unter Ausschluss ihrer Kollisionsnormen und "
                    "des UN-Kaufrechts." % LAW_DE),
    ("num", "11.2", "Ausschließlicher Gerichtsstand für alle Streitigkeiten aus oder im "
                    "Zusammenhang mit dieser Vereinbarung ist %s." % FORUM),

    ("pagebreak",),
    ("h2", "Anlage 1 - Endkundenbedingungen"),
    ("p", "Die Endkundenbedingungen sind das gesonderte Dokument dieses Namens in der bei "
          "Bestellung des Endkunden aktuellen Fassung. Der Hersteller kündigt Distributor und "
          "Wiederverkäufer eine Änderung 30 Tage im Voraus an; eine Änderung gilt für einen bereits "
          "geschlossenen Endkundenvertrag erst ab dessen Verlängerung."),
    ("table", ["Angabe", "Detail"], [
        ["Bei Unterzeichnung geltende Fassung der Endkundenbedingungen", "[Version] vom [Datum]"],
        ["Gebiet", "[Deutschland, Österreich und die Schweiz]"],
        ["Zustelladresse Hersteller", VENDOR["mail"]],
        ["Zustelladresse Distributor", OBJECTALE["mail"]],
        ["Zustelladresse Wiederverkäufer", BYON["mail"]],
        ["Eskalationskontakt Hersteller", "[Name] · [E-Mail] · [Telefon]"],
    ]),

    ("pagebreak",),
    ("h2", "Unterschriften"),
    ("p", "Von den drei Parteien zu den angegebenen Daten unterzeichnet."),
    ("sig", "Für %s (Hersteller)" % VENDOR["name"], "Für %s (Distributor)" % OBJECTALE["name"],
     ["Name:", "Funktion:", "Ort:", "Datum:"]),
    ("sig", "Für %s (Wiederverkäufer)" % BYON["name"], "",
     ["Name:", "Funktion:", "Ort:", "Datum:"]),
]
