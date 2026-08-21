# -*- coding: utf-8 -*-
"""05 - Data processing agreement (Auftragsverarbeitungsvertrag), Article 28 GDPR.

WHAT IS ACTUALLY PROCESSED, and it is much less than a customer expects. The platform reads public
sources about a TARGET COMPANY. It sends the target company's name to the public data sources and
the technical findings to the inference endpoint; neither receives a user's identity. The personal
data in play is therefore the platform USER's: an e-mail address for login and for the one-time
code, request telemetry, and support correspondence. Annex 1 says exactly that, because a DPA that
describes a broader processing than actually happens invites questions nobody can answer, and one
that describes a narrower processing is simply wrong.

THE SWISS LEG NEEDS NO SCCs. The European Commission adopted a renewed adequacy decision for
Switzerland on 15 January 2024, so a transfer from byon in Germany to objectale in Switzerland is
not a transfer to a third country requiring additional safeguards. That is checked, not assumed.
The US leg (Google, for the one-time code) is covered by the EU-US Data Privacy Framework.
"""
from common import BYON, DATE_DE, DATE_EN, FORUM, NOTE_DE, NOTE_EN, OBJECTALE, OPERATOR, \
    SUBPROCESSORS, SUBPROCESSORS_DE, VENDOR, VERSION

EN = [
    ("h1", "DATA PROCESSING AGREEMENT"),
    ("meta", "%s · %s · %s  ·  Article 28 GDPR  ·  Version %s  ·  %s  ·  German law, %s"
     % (VENDOR["name"], OBJECTALE["name"], BYON["name"], VERSION, DATE_EN, FORUM)),
    ("p", "This Data Processing Agreement (this \"DPA\") is concluded between:"),
    ("p", "%s, %s, which operates the platform (the \"Platform Processor\");"
     % (VENDOR["name"], VENDOR["addr"])),
    ("p", "%s, %s, which provides commercial and second-line support (the \"Support Processor\"); "
          "and" % (OBJECTALE["name"], OBJECTALE["addr"])),
    ("p", "%s, %s (the \"Controller\")." % (BYON["name"], BYON["addr"])),
    ("p", "It forms part of the Distribution Agreement, the Reseller Framework Agreement and the "
          "Flow-Down and Step-In Deed."),
    ("note", NOTE_EN),

    ("h2", "1. Subject matter and roles"),
    ("num", "1.1", "The Controller instructs the Processor to process personal data on its behalf "
                   "in connection with the provision of the assessment platform."),
    ("num", "1.2", "In respect of the account and usage data of the Controller's own users, the "
                   "Controller is the controller and the Processor is a processor within the "
                   "meaning of Article 4(8) GDPR."),
    ("num", "1.3", "Where the Controller performs assessments for its own customers, the "
                   "Controller determines for each engagement whether it acts as controller or as "
                   "processor for that customer, and is responsible for the corresponding "
                   "agreement with that customer. The Processor is not a party to it."),
    ("num", "1.4", "The subject matter, duration, nature and purpose of the processing, the types "
                   "of personal data and the categories of data subject are set out in Annex 1."),
    ("num", "1.5", "TWO PROCESSORS, SEVERALLY. In this DPA \"Processor\" means each of the Platform "
                   "Processor and the Support Processor. Every obligation of the Processor applies "
                   "to each of them severally in respect of the processing it actually performs, "
                   "and neither is responsible for the other's processing. The Platform Processor "
                   "operates the platform and holds the data; the Support Processor handles "
                   "support and commercial correspondence and has no access to the platform's data "
                   "stores. Making them jointly liable for each other would be a fiction, and a "
                   "fiction is not an answer to a supervisory authority."),

    ("h2", "2. Instructions"),
    ("num", "2.1", "The Processor processes personal data only on the documented instructions of "
                   "the Controller, including in respect of transfers to a third country, unless "
                   "required to do otherwise by Union or Member State law, in which case it will "
                   "inform the Controller before processing unless that law prohibits it."),
    ("num", "2.2", "The Reseller Framework Agreement, this DPA and the use of the platform in "
                   "accordance with its documentation constitute the Controller's initial "
                   "instructions."),
    ("num", "2.3", "The Processor will inform the Controller without undue delay if, in its "
                   "opinion, an instruction infringes the GDPR or other data protection law. The "
                   "Processor may suspend the affected processing until the instruction is "
                   "confirmed or withdrawn."),

    ("h2", "3. Confidentiality"),
    ("num", "3.1", "The Processor ensures that persons authorised to process the personal data "
                   "have committed themselves to confidentiality or are under an appropriate "
                   "statutory obligation of confidentiality, and that the commitment survives the "
                   "end of their engagement."),
    ("num", "3.2", "Access is limited to those personnel who need it to perform the Processor's "
                   "obligations."),

    ("h2", "4. Security of processing"),
    ("num", "4.1", "The Processor implements the technical and organisational measures set out in "
                   "Annex 2, which are appropriate to the risk within the meaning of Article 32 "
                   "GDPR."),
    ("num", "4.2", "The Processor may change a measure provided the level of protection is not "
                   "reduced. Material changes are notified to the Controller."),
    ("num", "4.3", "The Controller has reviewed Annex 2 and considers the measures appropriate for "
                   "the processing described in Annex 1."),

    ("h2", "5. Sub-processors"),
    ("num", "5.1", "The Controller grants general written authorisation for the engagement of "
                   "sub-processors. The sub-processors engaged at the date of this DPA are listed "
                   "in Annex 3."),
    ("num", "5.2", "The Processor will inform the Controller of an intended addition or "
                   "replacement of a sub-processor at least 30 days in advance. The Controller may "
                   "object on reasonable data-protection grounds within 14 days of that notice."),
    ("num", "5.3", "Where the Controller objects and the parties cannot agree a solution within a "
                   "further 30 days, either party may terminate the affected services with effect "
                   "from the date the change takes effect, without liability other than repayment "
                   "of fees paid for the unexpired term."),
    ("num", "5.4", "The Processor imposes on each sub-processor obligations equivalent to those in "
                   "this DPA and remains fully liable to the Controller for the sub-processor's "
                   "performance."),

    ("h2", "6. Assistance to the Controller"),
    ("num", "6.1", "Taking into account the nature of the processing, the Processor assists the "
                   "Controller by appropriate technical and organisational measures in responding "
                   "to requests from data subjects under Chapter III GDPR."),
    ("num", "6.2", "Where a data subject contacts the Processor directly, the Processor will "
                   "forward the request to the Controller without undue delay and will not respond "
                   "on the merits."),
    ("num", "6.3", "The Processor assists the Controller in complying with Articles 32 to 36 GDPR, "
                   "taking into account the nature of the processing and the information available "
                   "to it."),
    ("num", "6.4", "Assistance that goes materially beyond routine effort may be charged at the "
                   "Processor's then-current rates, notified in advance."),

    ("h2", "7. Personal data breach"),
    ("num", "7.1", "The Processor notifies the Controller without undue delay, and in any event "
                   "within 24 hours, after becoming aware of a personal data breach affecting the "
                   "Controller's personal data."),
    ("num", "7.2", "The notification describes the nature of the breach, the categories and "
                   "approximate number of data subjects and records concerned, the likely "
                   "consequences and the measures taken or proposed, and names a contact point. "
                   "Where the information is not available at once it is provided in phases "
                   "without undue further delay."),
    ("num", "7.3", "The Processor does not notify a supervisory authority or a data subject on the "
                   "Controller's behalf unless instructed to do so in writing."),

    ("h2", "8. Deletion and return"),
    ("num", "8.1", "On termination of the services the Processor will, at the Controller's choice, "
                   "delete or return the personal data and delete existing copies, unless Union or "
                   "Member State law requires storage."),
    ("num", "8.2", "The Controller may export the generated documents for 60 days after "
                   "termination. After that period the Processor deletes them."),
    ("num", "8.3", "Backups are deleted in the ordinary backup cycle, which is 7 days. Personal "
                   "data in a backup remains subject to this DPA until deleted."),
    ("num", "8.4", "The Processor confirms deletion in writing on request."),

    ("h2", "9. Audits"),
    ("num", "9.1", "The Processor makes available to the Controller the information necessary to "
                   "demonstrate compliance with Article 28 GDPR."),
    ("num", "9.2", "The Controller may audit once per calendar year, on 30 days' written notice, "
                   "during business hours, in a way that does not disrupt operations, and subject "
                   "to confidentiality. An additional audit may be carried out after a personal "
                   "data breach affecting the Controller."),
    ("num", "9.3", "The Processor may satisfy an audit request by providing a current third-party "
                   "certification or audit report covering the relevant controls, where that "
                   "reasonably answers the Controller's question."),
    ("num", "9.4", "The Controller bears its own audit costs. The Processor may charge for "
                   "personnel time beyond one working day per audit."),

    ("h2", "10. International transfers"),
    ("num", "10.1", "The platform is hosted in Frankfurt am Main, Germany. Personal data is stored "
                    "in the European Union."),
    ("num", "10.2", "The Processor is established in Switzerland. Transfers from the European "
                    "Union to Switzerland rely on the adequacy decision adopted by the European "
                    "Commission on 15 January 2024, which confirms that Switzerland ensures an "
                    "adequate level of protection. No additional safeguard is required for that "
                    "transfer."),
    ("num", "10.3", "Where a sub-processor in Annex 3 is established outside the European Economic "
                    "Area and outside a country covered by an adequacy decision, the transfer is "
                    "made on the Standard Contractual Clauses adopted by Commission Implementing "
                    "Decision (EU) 2021/914, together with any supplementary measure the transfer "
                    "impact assessment identifies."),
    ("num", "10.4", "Google LLC receives the user's e-mail address in order to deliver the "
                    "one-time login code and the daily report. That transfer relies on the EU-US "
                    "Data Privacy Framework."),

    ("h2", "11. Liability and term"),
    ("num", "11.1", "Liability under this DPA follows clause 17 of the Reseller Framework "
                    "Agreement. Article 82 GDPR is unaffected."),
    ("num", "11.2", "This DPA takes effect with the Reseller Framework Agreement and ends when the "
                    "last processing under it ends. Clauses 3, 8 and 11 survive."),
    ("num", "11.3", "Where a provision of this DPA is invalid, the remainder is unaffected and the "
                    "parties will replace it with a valid provision that meets Article 28 GDPR."),
    ("num", "11.4", "This DPA is governed by German law. The exclusive place of jurisdiction is "
                    "Frankfurt am Main."),

    ("pagebreak",),
    ("h2", "Annex 1 - Details of the processing"),
    ("table", ["Item", "Detail"], [
        ["Subject matter",
         "Provision of the assessment platform and the related support."],
        ["Duration", "The term of the Reseller Framework Agreement, plus the deletion periods in "
                     "clause 8."],
        ["Nature and purpose",
         "Authenticating users, delivering the one-time login code, recording usage for billing "
         "and abuse prevention, generating and delivering assessment documents, and handling "
         "support requests."],
        ["Categories of data subject",
         "Employees and contractors of the Controller who are named users; the Controller's "
         "contacts for support and billing."],
        ["Types of personal data",
         "Name; business e-mail address; the identity of the user who ordered an assessment; "
         "request telemetry, being IP address, country, time, path, status and user agent; support "
         "correspondence."],
        ["Special categories", "None. The platform is not designed for special-category data and "
                               "the Controller will not submit any."],
        ["Data not processed",
         "The public data sources receive the name or domain of the organisation being assessed. "
         "The inference endpoint receives the technical findings. Neither receives the identity of "
         "a user."],
    ]),
    ("note", "The last row is the one procurement asks about. It is worth reading before the "
             "first customer meeting: the analysis pipeline never receives a user identity, so it "
             "is not a recipient of personal data and does not appear in Annex 3."),

    ("pagebreak",),
    ("h2", "Annex 2 - Technical and organisational measures"),
    ("h3", "Confidentiality"),
    ("bullet", "Access to the application requires a password and a one-time code sent to the "
               "registered e-mail address."),
    ("bullet", "Access is by named individual user; accounts are provisioned and revoked by a "
               "named administrator."),
    ("bullet", "Passwords are stored only as salted hashes using a memory-hard key derivation "
               "function; they are never stored or transmitted in clear."),
    ("bullet", "Authorisation is enforced on the server for every request. Generated documents are "
               "scoped to the account that produced them."),
    ("bullet", "Administrative interfaces are bound to the local host and are not reachable from "
               "the internet."),
    ("h3", "Integrity"),
    ("bullet", "All traffic is served over TLS with certificates renewed automatically."),
    ("bullet", "Security response headers are set on every response, including a content security "
               "policy that forbids inline script."),
    ("bullet", "Changes reach production only through a version-controlled pipeline with automated "
               "tests; the deployed artefact is verified against the committed source."),
    ("bullet", "Container images are scanned for known vulnerabilities and a critical finding "
               "fails the build."),
    ("h3", "Availability and resilience"),
    ("bullet", "Daily backups of the operational databases with verified restoration."),
    ("bullet", "Automated patching of the operating system on a fixed cycle, with a check that "
               "refuses to reboot into an invalid configuration."),
    ("bullet", "Off-host monitoring of availability and certificate expiry."),
    ("h3", "Detection"),
    ("bullet", "Structured event logging of authentication, assessment runs and administrative "
               "actions, retained for 30 days."),
    ("bullet", "Automated detection of credential attacks, path probing and automated scanning, "
               "with alerting to a named operator."),
    ("h3", "Data minimisation and separation"),
    ("bullet", "Geolocation of a request is recorded at country level only."),
    ("bullet", "Request telemetry can be configured to store salted hashes of IP addresses instead "
               "of the addresses themselves."),
    ("bullet", "Each account's documents are stored under a separate directory keyed to that "
               "account and are served only to it."),
    ("bullet", "An uploaded branding template is not retained after the palette, fonts and logo "
               "have been extracted from it."),

    ("pagebreak",),
    ("h2", "Annex 3 - Sub-processors"),
    ("table", ["Sub-processor", "Country", "Purpose", "Location of processing"],
     [list(r) for r in SUBPROCESSORS]),
    ("num", "A", "The Processor will maintain this list and notify changes in accordance with "
                 "clause 5.2."),
    ("num", "B", "%s is a PARTY to this DPA as the Platform Processor and is not a sub-processor. "
                 "The sub-processors above are engaged by it. The Support Processor engages no "
                 "sub-processor for the processing it performs." % OPERATOR),

    ("pagebreak",),
    ("h2", "Signatures"),
    ("sig", "For %s (Platform Processor)" % VENDOR["name"],
     "For %s (Support Processor)" % OBJECTALE["name"],
     ["Name:", "Function:", "Place:", "Date:"]),
    ("sig", "For %s (Controller)" % BYON["name"], "",
     ["Name:", "Function:", "Place:", "Date:"]),
]

DE = [
    ("h1", "AUFTRAGSVERARBEITUNGSVERTRAG"),
    ("meta", "%s · %s · %s  ·  Art. 28 DSGVO  ·  Version %s  ·  %s  ·  Deutsches Recht, %s"
     % (VENDOR["name"], OBJECTALE["name"], BYON["name"], VERSION, DATE_DE, FORUM)),
    ("p", "Dieser Auftragsverarbeitungsvertrag (der \"AVV\") wird geschlossen zwischen:"),
    ("p", "%s, %s, die die Plattform betreibt (die \"Plattform-Auftragsverarbeiterin\");"
     % (VENDOR["name"], VENDOR["addr_de"])),
    ("p", "%s, %s, die die kaufmännische Betreuung und den Second-Level-Support erbringt (die "
          "\"Support-Auftragsverarbeiterin\"); und"
     % (OBJECTALE["name"], OBJECTALE["addr_de"])),
    ("p", "%s, %s (der \"Verantwortliche\")." % (BYON["name"], BYON["addr_de"])),
    ("p", "Er ist Bestandteil des Distributionsvertrages, des Wiederverkäufer-Rahmenvertrages und "
          "der Durchgriffs- und Eintrittsvereinbarung."),
    ("note", NOTE_DE),

    ("h2", "1. Gegenstand und Rollen"),
    ("num", "1.1", "Der Verantwortliche beauftragt den Auftragsverarbeiter, personenbezogene Daten "
                   "in seinem Auftrag im Zusammenhang mit der Bereitstellung der "
                   "Assessment-Plattform zu verarbeiten."),
    ("num", "1.2", "Hinsichtlich der Konto- und Nutzungsdaten der eigenen Nutzer des "
                   "Verantwortlichen ist der Verantwortliche Verantwortlicher und der "
                   "Auftragsverarbeiter Auftragsverarbeiter im Sinne des Art. 4 Nr. 8 DSGVO."),
    ("num", "1.3", "Führt der Verantwortliche Assessments für eigene Kunden durch, bestimmt er für "
                   "jedes Mandat, ob er als Verantwortlicher oder als Auftragsverarbeiter dieses "
                   "Kunden handelt, und ist für die entsprechende Vereinbarung mit diesem Kunden "
                   "verantwortlich. Der Auftragsverarbeiter ist daran nicht beteiligt."),
    ("num", "1.4", "Gegenstand, Dauer, Art und Zweck der Verarbeitung, die Arten personenbezogener "
                   "Daten und die Kategorien betroffener Personen ergeben sich aus Anlage 1."),
    ("num", "1.5", "ZWEI AUFTRAGSVERARBEITER, JEWEILS EINZELN. In diesem AVV bezeichnet "
                   "\"Auftragsverarbeiter\" sowohl die Plattform-Auftragsverarbeiterin als auch die "
                   "Support-Auftragsverarbeiterin. Jede Pflicht des Auftragsverarbeiters trifft "
                   "jede von ihnen einzeln für die von ihr tatsächlich durchgeführte Verarbeitung; "
                   "keine haftet für die Verarbeitung der anderen. Die "
                   "Plattform-Auftragsverarbeiterin betreibt die Plattform und hält die Daten; die "
                   "Support-Auftragsverarbeiterin bearbeitet Support- und Geschäftskorrespondenz "
                   "und hat keinen Zugriff auf die Datenbestände der Plattform. Eine gesamtschuld"
                   "nerische Zurechnung wäre eine Fiktion, und eine Fiktion ist gegenüber einer "
                   "Aufsichtsbehörde keine Antwort."),

    ("h2", "2. Weisungen"),
    ("num", "2.1", "Der Auftragsverarbeiter verarbeitet personenbezogene Daten ausschließlich auf "
                   "dokumentierte Weisung des Verantwortlichen, auch in Bezug auf Übermittlungen "
                   "in ein Drittland, es sei denn, er ist nach dem Recht der Union oder eines "
                   "Mitgliedstaats zu einer anderen Verarbeitung verpflichtet; in diesem Fall "
                   "informiert er den Verantwortlichen vor der Verarbeitung, sofern dieses Recht "
                   "dies nicht verbietet."),
    ("num", "2.2", "Der Wiederverkäufer-Rahmenvertrag, dieser AVV und die dokumentationsgemäße "
                   "Nutzung der Plattform bilden die anfängliche Weisung des Verantwortlichen."),
    ("num", "2.3", "Der Auftragsverarbeiter informiert den Verantwortlichen unverzüglich, wenn eine "
                   "Weisung seiner Auffassung nach gegen die DSGVO oder anderes Datenschutzrecht "
                   "verstößt. Er darf die betroffene Verarbeitung aussetzen, bis die Weisung "
                   "bestätigt oder zurückgenommen wird."),

    ("h2", "3. Vertraulichkeit"),
    ("num", "3.1", "Der Auftragsverarbeiter stellt sicher, dass die zur Verarbeitung befugten "
                   "Personen zur Vertraulichkeit verpflichtet sind oder einer angemessenen "
                   "gesetzlichen Verschwiegenheitspflicht unterliegen und dass diese Verpflichtung "
                   "über das Ende ihrer Tätigkeit hinaus fortbesteht."),
    ("num", "3.2", "Der Zugriff ist auf diejenigen Beschäftigten beschränkt, die ihn zur Erfüllung "
                   "der Pflichten des Auftragsverarbeiters benötigen."),

    ("h2", "4. Sicherheit der Verarbeitung"),
    ("num", "4.1", "Der Auftragsverarbeiter setzt die in Anlage 2 beschriebenen technischen und "
                   "organisatorischen Maßnahmen um, die dem Risiko im Sinne des Art. 32 DSGVO "
                   "angemessen sind."),
    ("num", "4.2", "Der Auftragsverarbeiter darf eine Maßnahme ändern, sofern das Schutzniveau "
                   "nicht sinkt. Wesentliche Änderungen werden dem Verantwortlichen mitgeteilt."),
    ("num", "4.3", "Der Verantwortliche hat Anlage 2 geprüft und hält die Maßnahmen für die in "
                   "Anlage 1 beschriebene Verarbeitung für angemessen."),

    ("h2", "5. Unterauftragsverarbeiter"),
    ("num", "5.1", "Der Verantwortliche erteilt eine allgemeine schriftliche Genehmigung zur "
                   "Beauftragung von Unterauftragsverarbeitern. Die bei Abschluss dieses AVV "
                   "beauftragten Unterauftragsverarbeiter sind in Anlage 3 aufgeführt."),
    ("num", "5.2", "Der Auftragsverarbeiter informiert den Verantwortlichen mindestens 30 Tage "
                   "vorher über die beabsichtigte Hinzuziehung oder Ersetzung eines "
                   "Unterauftragsverarbeiters. Der Verantwortliche kann binnen 14 Tagen ab dieser "
                   "Mitteilung aus sachlichen datenschutzrechtlichen Gründen widersprechen."),
    ("num", "5.3", "Widerspricht der Verantwortliche und erzielen die Parteien binnen weiterer 30 "
                   "Tage keine Einigung, kann jede Partei die betroffenen Leistungen zum "
                   "Wirksamwerden der Änderung beenden, ohne weitere Haftung außer der Erstattung "
                   "für die ungenutzte Restlaufzeit gezahlter Entgelte."),
    ("num", "5.4", "Der Auftragsverarbeiter verpflichtet jeden Unterauftragsverarbeiter zu "
                   "Pflichten, die den Pflichten dieses AVV entsprechen, und haftet dem "
                   "Verantwortlichen für dessen Leistung uneingeschränkt."),

    ("h2", "6. Unterstützung des Verantwortlichen"),
    ("num", "6.1", "Der Auftragsverarbeiter unterstützt den Verantwortlichen unter Berücksichtigung "
                   "der Art der Verarbeitung mit geeigneten technischen und organisatorischen "
                   "Maßnahmen bei der Beantwortung von Anträgen betroffener Personen nach Kapitel "
                   "III DSGVO."),
    ("num", "6.2", "Wendet sich eine betroffene Person unmittelbar an den Auftragsverarbeiter, "
                   "leitet dieser den Antrag unverzüglich an den Verantwortlichen weiter und "
                   "antwortet nicht in der Sache."),
    ("num", "6.3", "Der Auftragsverarbeiter unterstützt den Verantwortlichen bei der Einhaltung der "
                   "Art. 32 bis 36 DSGVO unter Berücksichtigung der Art der Verarbeitung und der "
                   "ihm zur Verfügung stehenden Informationen."),
    ("num", "6.4", "Unterstützung, die den routinemäßigen Aufwand wesentlich übersteigt, kann zu "
                   "den jeweils geltenden Sätzen des Auftragsverarbeiters berechnet werden; diese "
                   "werden vorher mitgeteilt."),

    ("h2", "7. Verletzung des Schutzes personenbezogener Daten"),
    ("num", "7.1", "Der Auftragsverarbeiter informiert den Verantwortlichen unverzüglich, in jedem "
                   "Fall binnen 24 Stunden nach Bekanntwerden, über eine Verletzung des Schutzes "
                   "personenbezogener Daten, die Daten des Verantwortlichen betrifft."),
    ("num", "7.2", "Die Meldung beschreibt die Art der Verletzung, die Kategorien und die "
                   "ungefähre Zahl der betroffenen Personen und Datensätze, die wahrscheinlichen "
                   "Folgen und die ergriffenen oder vorgeschlagenen Maßnahmen und benennt eine "
                   "Anlaufstelle. Stehen die Angaben nicht sofort zur Verfügung, werden sie ohne "
                   "unangemessene weitere Verzögerung schrittweise bereitgestellt."),
    ("num", "7.3", "Der Auftragsverarbeiter meldet weder einer Aufsichtsbehörde noch einer "
                   "betroffenen Person im Namen des Verantwortlichen, sofern er nicht schriftlich "
                   "dazu angewiesen wird."),

    ("h2", "8. Löschung und Rückgabe"),
    ("num", "8.1", "Nach Beendigung der Leistungen löscht der Auftragsverarbeiter die "
                   "personenbezogenen Daten nach Wahl des Verantwortlichen oder gibt sie zurück und "
                   "löscht vorhandene Kopien, sofern nicht das Recht der Union oder eines "
                   "Mitgliedstaats eine Speicherung verlangt."),
    ("num", "8.2", "Der Verantwortliche kann die erzeugten Dokumente 60 Tage nach Beendigung "
                   "exportieren. Danach löscht der Auftragsverarbeiter sie."),
    ("num", "8.3", "Sicherungen werden im regulären Sicherungszyklus von 7 Tagen gelöscht. "
                   "Personenbezogene Daten in einer Sicherung unterliegen bis zur Löschung diesem "
                   "AVV."),
    ("num", "8.4", "Der Auftragsverarbeiter bestätigt die Löschung auf Anforderung schriftlich."),

    ("h2", "9. Kontrollen"),
    ("num", "9.1", "Der Auftragsverarbeiter stellt dem Verantwortlichen alle Informationen zur "
                   "Verfügung, die zum Nachweis der Einhaltung des Art. 28 DSGVO erforderlich "
                   "sind."),
    ("num", "9.2", "Der Verantwortliche kann einmal je Kalenderjahr mit einer Ankündigungsfrist von "
                   "30 Tagen während der Geschäftszeiten betriebsschonend und unter Wahrung der "
                   "Vertraulichkeit kontrollieren. Nach einer Verletzung des Schutzes "
                   "personenbezogener Daten, die den Verantwortlichen betrifft, kann eine "
                   "zusätzliche Kontrolle durchgeführt werden."),
    ("num", "9.3", "Der Auftragsverarbeiter kann einem Kontrollverlangen durch Vorlage einer "
                   "aktuellen Zertifizierung oder eines Prüfberichts eines Dritten nachkommen, der "
                   "die einschlägigen Kontrollen abdeckt, sofern dies die Frage des "
                   "Verantwortlichen angemessen beantwortet."),
    ("num", "9.4", "Der Verantwortliche trägt seine eigenen Kontrollkosten. Der "
                   "Auftragsverarbeiter kann Personalaufwand berechnen, der einen Arbeitstag je "
                   "Kontrolle übersteigt."),

    ("h2", "10. Internationale Übermittlungen"),
    ("num", "10.1", "Die Plattform wird in Frankfurt am Main, Deutschland, gehostet. "
                    "Personenbezogene Daten werden in der Europäischen Union gespeichert."),
    ("num", "10.2", "Der Auftragsverarbeiter ist in der Schweiz ansässig. Übermittlungen aus der "
                    "Europäischen Union in die Schweiz stützen sich auf den "
                    "Angemessenheitsbeschluss der Europäischen Kommission vom 15. Januar 2024, mit "
                    "dem bestätigt wird, dass die Schweiz ein angemessenes Schutzniveau "
                    "gewährleistet. Für diese Übermittlung ist keine zusätzliche Garantie "
                    "erforderlich."),
    ("num", "10.3", "Ist ein Unterauftragsverarbeiter nach Anlage 3 außerhalb des Europäischen "
                    "Wirtschaftsraums und außerhalb eines von einem Angemessenheitsbeschluss "
                    "erfassten Landes ansässig, erfolgt die Übermittlung auf Grundlage der "
                    "Standardvertragsklauseln nach dem Durchführungsbeschluss (EU) 2021/914 nebst "
                    "etwaigen ergänzenden Maßnahmen, die die Übermittlungsfolgenabschätzung "
                    "ergibt."),
    ("num", "10.4", "Google LLC erhält die E-Mail-Adresse des Nutzers, um den Einmalcode für die "
                    "Anmeldung und den Tagesbericht zuzustellen. Diese Übermittlung stützt sich auf "
                    "das EU-US Data Privacy Framework."),

    ("h2", "11. Haftung und Laufzeit"),
    ("num", "11.1", "Die Haftung aus diesem AVV richtet sich nach Ziffer 17 des "
                    "Wiederverkäufer-Rahmenvertrages. Art. 82 DSGVO bleibt unberührt."),
    ("num", "11.2", "Dieser AVV tritt mit dem Wiederverkäufer-Rahmenvertrag in Kraft und endet mit "
                    "der letzten darauf beruhenden Verarbeitung. Die Ziffern 3, 8 und 11 gelten "
                    "fort."),
    ("num", "11.3", "Ist eine Bestimmung dieses AVV unwirksam, bleibt der übrige Inhalt unberührt; "
                    "die Parteien ersetzen sie durch eine wirksame Bestimmung, die Art. 28 DSGVO "
                    "genügt."),
    ("num", "11.4", "Dieser AVV unterliegt deutschem Recht. Ausschließlicher Gerichtsstand ist "
                    "Frankfurt am Main."),

    ("pagebreak",),
    ("h2", "Anlage 1 - Einzelheiten der Verarbeitung"),
    ("table", ["Angabe", "Detail"], [
        ["Gegenstand", "Bereitstellung der Assessment-Plattform und des zugehörigen Supports."],
        ["Dauer", "Die Laufzeit des Wiederverkäufer-Rahmenvertrages zuzüglich der Löschfristen nach "
                  "Ziffer 8."],
        ["Art und Zweck",
         "Authentifizierung von Nutzern, Zustellung des Einmalcodes für die Anmeldung, Erfassung "
         "der Nutzung zu Abrechnungs- und Missbrauchsverhinderungszwecken, Erzeugung und "
         "Bereitstellung der Assessment-Dokumente sowie Bearbeitung von Supportanfragen."],
        ["Kategorien betroffener Personen",
         "Beschäftigte und Auftragnehmer des Verantwortlichen, die benannte Nutzer sind; "
         "Ansprechpartner des Verantwortlichen für Support und Abrechnung."],
        ["Arten personenbezogener Daten",
         "Name; geschäftliche E-Mail-Adresse; Identität des Nutzers, der ein Assessment beauftragt "
         "hat; Anfragetelemetrie, das heißt IP-Adresse, Land, Zeit, Pfad, Status und User Agent; "
         "Supportkorrespondenz."],
        ["Besondere Kategorien", "Keine. Die Plattform ist nicht für besondere Kategorien "
                                 "personenbezogener Daten ausgelegt; der Verantwortliche wird "
                                 "solche nicht übermitteln."],
        ["Nicht verarbeitete Daten",
         "Die öffentlichen Datenquellen erhalten den Namen oder die Domain des bewerteten "
         "Unternehmens. Der Inferenz-Endpunkt erhält die technischen Feststellungen. Keiner von "
         "beiden erhält die Identität eines Nutzers."],
    ]),
    ("note", "Die letzte Zeile ist diejenige, nach der der Einkauf fragt. Sie lohnt sich vor dem "
             "ersten Kundengespräch: Die Analysekette erhält niemals eine Nutzeridentität, ist "
             "daher kein Empfänger personenbezogener Daten und erscheint nicht in Anlage 3."),

    ("pagebreak",),
    ("h2", "Anlage 2 - Technische und organisatorische Maßnahmen"),
    ("h3", "Vertraulichkeit"),
    ("bullet", "Der Zugang zur Anwendung erfordert ein Passwort und einen Einmalcode an die "
               "registrierte E-Mail-Adresse."),
    ("bullet", "Der Zugang erfolgt über benannte Einzelnutzer; Konten werden von einem benannten "
               "Administrator eingerichtet und entzogen."),
    ("bullet", "Passwörter werden ausschließlich als gesalzene Hashes mit einem speicherharten "
               "Schlüsselableitungsverfahren gespeichert und niemals im Klartext gespeichert oder "
               "übertragen."),
    ("bullet", "Die Berechtigungsprüfung erfolgt serverseitig bei jeder Anfrage. Erzeugte Dokumente "
               "sind dem erzeugenden Konto zugeordnet."),
    ("bullet", "Administrative Schnittstellen sind an die lokale Schnittstelle gebunden und aus dem "
               "Internet nicht erreichbar."),
    ("h3", "Integrität"),
    ("bullet", "Der gesamte Verkehr wird über TLS mit automatisch erneuerten Zertifikaten "
               "ausgeliefert."),
    ("bullet", "Sicherheitsrelevante Antwortheader werden bei jeder Antwort gesetzt, einschließlich "
               "einer Content Security Policy, die Inline-Skripte untersagt."),
    ("bullet", "Änderungen erreichen die Produktion nur über eine versionierte Pipeline mit "
               "automatisierten Tests; das ausgelieferte Artefakt wird gegen den eingecheckten "
               "Quellcode geprüft."),
    ("bullet", "Container-Images werden auf bekannte Schwachstellen geprüft; ein kritischer Befund "
               "lässt den Build fehlschlagen."),
    ("h3", "Verfügbarkeit und Belastbarkeit"),
    ("bullet", "Tägliche Sicherungen der Betriebsdatenbanken mit verifizierter Wiederherstellung."),
    ("bullet", "Automatisierte Betriebssystem-Aktualisierung in festem Zyklus, mit einer Prüfung, "
               "die einen Neustart in eine ungültige Konfiguration verweigert."),
    ("bullet", "Überwachung von Verfügbarkeit und Zertifikatsablauf von außerhalb des Systems."),
    ("h3", "Erkennung"),
    ("bullet", "Strukturierte Ereignisprotokollierung von Anmeldungen, Assessment-Läufen und "
               "administrativen Handlungen, aufbewahrt für 30 Tage."),
    ("bullet", "Automatisierte Erkennung von Angriffen auf Zugangsdaten, Pfad-Sondierung und "
               "automatisiertem Scannen mit Alarmierung eines benannten Herstellers."),
    ("h3", "Datenminimierung und Trennung"),
    ("bullet", "Die Geolokalisierung einer Anfrage wird ausschließlich auf Länderebene erfasst."),
    ("bullet", "Die Anfragetelemetrie kann so konfiguriert werden, dass anstelle der IP-Adressen "
               "gesalzene Hashwerte gespeichert werden."),
    ("bullet", "Die Dokumente jedes Kontos werden in einem eigenen, dem Konto zugeordneten "
               "Verzeichnis gespeichert und nur an dieses ausgeliefert."),
    ("bullet", "Eine hochgeladene Markenvorlage wird nach Extraktion von Farbpalette, Schriften und "
               "Logo nicht aufbewahrt."),

    ("pagebreak",),
    ("h2", "Anlage 3 - Unterauftragsverarbeiter"),
    ("table", ["Unterauftragsverarbeiter", "Land", "Zweck", "Ort der Verarbeitung"],
     [list(r) for r in SUBPROCESSORS_DE]),
    ("num", "A", "Der Auftragsverarbeiter führt diese Liste und teilt Änderungen nach Ziffer 5.2 "
                 "mit."),
    ("num", "B", "%s ist als Plattform-Auftragsverarbeiterin PARTEI dieses AVV und nicht "
                 "Unterauftragsverarbeiterin. Die vorstehenden Unterauftragsverarbeiter werden von "
                 "ihr eingesetzt. Die Support-Auftragsverarbeiterin setzt für die von ihr "
                 "durchgeführte Verarbeitung keinen Unterauftragsverarbeiter ein." % OPERATOR),

    ("pagebreak",),
    ("h2", "Unterschriften"),
    ("sig", "Für %s (Plattform-Auftragsverarbeiterin)" % VENDOR["name"],
     "Für %s (Support-Auftragsverarbeiterin)" % OBJECTALE["name"],
     ["Name:", "Funktion:", "Ort:", "Datum:"]),
    ("sig", "Für %s (Verantwortlicher)" % BYON["name"], "",
     ["Name:", "Funktion:", "Ort:", "Datum:"]),
]
