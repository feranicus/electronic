# -*- coding: utf-8 -*-
"""04 - Service level agreement, objectale -> byon, back-to-back with the head SLA.

THE ONE RULE THIS DOCUMENT IS BUILT AROUND: objectale does not operate the platform and cannot owe
byon a service level it does not itself hold. Every figure here is quoted from the head SLA rather
than chosen, and clause 2.3 says so in terms. A reseller SLA that promises more than the upstream
one is a liability the reseller funds out of its own margin, usually discovering this during the
first outage.
"""
from common import BYON, CREDITS, CREDITS_DE, DATE_DE, DATE_EN, NOTE_DE, NOTE_EN, OBJECTALE, \
    OPERATOR, SEVERITIES, SEVERITIES_DE, VERSION

EN = [
    ("h1", "SERVICE LEVEL AGREEMENT"),
    ("meta", "%s and %s  ·  Schedule to the Reseller Framework Agreement  ·  Version %s  ·  %s"
     % (OBJECTALE["name"], BYON["name"], VERSION, DATE_EN)),
    ("note", NOTE_EN),

    ("h2", "1. Purpose and scope"),
    ("num", "1.1", "This Service Level Agreement (the \"SLA\") is a schedule to the Reseller "
                   "Framework Agreement between %s (\"objectale\") and %s (\"byon\") and forms "
                   "part of it." % (OBJECTALE["name"], BYON["name"])),
    ("num", "1.2", "It covers the web cabinet, the Telegram bots, the assessment engine and the "
                   "delivery of the generated documents (together, the \"Platform\")."),
    ("num", "1.3", "It does not cover byon's own network or devices, byon's own services delivered "
                   "around the Platform, or a third-party public data source the Platform reads."),

    ("h2", "2. Who owes what"),
    ("num", "2.1", "The Platform is operated by %s (the \"Vendor\"). objectale is byon's "
                   "contractual counterparty and the single point of contact." % OPERATOR),
    ("num", "2.2", "objectale provides second-line support to byon and escalates to the Vendor. "
                   "byon provides first-line support to its own customers."),
    ("num", "2.3", "This SLA is back-to-back with the agreement between objectale and the "
                   "Vendor. The commitments below are the commitments objectale itself receives. "
                   "objectale does not owe byon more than that, and byon acknowledges it. Where "
                   "byon commits more to its own customers, byon carries the difference."),

    ("h2", "3. Availability"),
    ("num", "3.1", "Target availability of the cabinet is 99.5% per calendar month."),
    ("num", "3.2", "Availability is calculated as ((T - P - E - D) / (T - P - E)) x 100, where T is "
                   "the total minutes in the month, P is planned and emergency maintenance, E is "
                   "minutes attributable to an exclusion under clause 8, and D is downtime."),
    ("num", "3.3", "The Vendor's server-side monitoring is the reference measurement. byon may "
                   "raise a discrepancy in writing within 10 business days of the month end."),
    ("num", "3.4", "On request objectale will provide the monthly availability report it receives."),

    ("h2", "4. Maintenance"),
    ("num", "4.1", "Planned maintenance will not exceed 4 hours in aggregate per calendar month, "
                   "will be notified at least 48 hours in advance by e-mail to byon's nominated "
                   "contacts, and will be scheduled outside 08:00 to 18:00 CET on business days."),
    ("num", "4.2", "Emergency maintenance may be performed where the Vendor reasonably "
                   "determines it is necessary to preserve security or integrity. Notice is given "
                   "as soon as reasonably practicable and may be after the event."),
    ("num", "4.3", "Planned and emergency maintenance are excluded from downtime and from the "
                   "availability calculation."),

    ("h2", "5. Assessment performance"),
    ("num", "5.1", "An assessment run completes within 15 minutes of the engine accepting the "
                   "request, for 95% of runs in a calendar month."),
    ("num", "5.2", "A very large estate takes materially longer and is excluded from that "
                   "measurement. The threshold is recorded in Schedule A."),
    ("num", "5.3", "Runs excluded under clause 8, and runs cancelled by the user, are excluded."),

    ("h2", "6. Support and severities"),
    ("num", "6.1", "Standard support hours are 09:00 to 18:00 CET, Monday to Friday, excluding "
                   "public holidays at objectale's registered office."),
    ("num", "6.2", "Severity 1 is worked around the clock. All other severities are worked during "
                   "support hours."),
    ("num", "6.3", "byon proposes the severity when raising an incident. Where the parties do not "
                   "agree, objectale works the incident at the higher of the two proposed "
                   "severities until agreement is reached."),
    ("table", ["Severity", "Definition", "Response", "Restore or workaround"],
     [list(r) for r in SEVERITIES]),
    ("num", "6.4", "Response is the time to a substantive human reply, not an automated "
                   "acknowledgement. Restore includes a workaround that returns the affected "
                   "function to use."),

    ("h2", "7. Service credits"),
    ("num", "7.1", "Where availability in a month falls below the target, byon may claim a credit "
                   "against the fee for that month."),
    ("table", ["Monthly availability", "Credit, as a percentage of that month's fee"],
     [list(r) for r in CREDITS]),
    ("num", "7.2", "A credit must be claimed in writing within 30 days of the end of the month and "
                   "must identify the month, the availability byon calculates and the incidents "
                   "relied on."),
    ("num", "7.3", "Credits in any month are capped at 30% of the fee for that month, are applied "
                   "against future fees, are not payable in cash, and are byon's sole and "
                   "exclusive financial remedy for failure to meet the availability target."),
    ("num", "7.4", "objectale will pass on to byon any credit objectale itself receives from the "
                   "Vendor in respect of the same period, to the extent it exceeds the credit "
                   "calculated under this clause."),

    ("h2", "8. Exclusions"),
    ("bullet", "Planned and emergency maintenance notified under clause 4."),
    ("bullet", "byon's own network, environment, devices or internet access."),
    ("bullet", "Unavailability, rate limiting or change of a third-party public data source the "
               "Platform reads."),
    ("bullet", "Misuse, or use contrary to clause 7 of the Reseller Framework Agreement."),
    ("bullet", "Any suspension permitted under the Reseller Framework Agreement, including "
               "suspension for non-payment or for a suspected compromise."),
    ("bullet", "An event beyond the reasonable control of objectale or the Vendor."),
    ("bullet", "Use of a trial, pilot, sandbox, beta or preview feature."),

    ("h2", "9. Backup and recovery"),
    ("num", "9.1", "Backups are taken daily and retained for 7 days."),
    ("num", "9.2", "Recovery point objective: 24 hours. Recovery time objective: 8 hours, measured "
                   "from the point of invocation."),
    ("num", "9.3", "Documents generated but not downloaded before an event within the recovery "
                   "point objective may need to be regenerated. Regeneration of such a document is "
                   "not charged."),

    ("h2", "10. Security incident notification"),
    ("num", "10.1", "objectale will notify byon without undue delay, and in any event within 24 "
                    "hours of objectale becoming aware, of a security incident affecting byon's "
                    "data or byon's use of the Platform."),
    ("num", "10.2", "The notification will describe what is known, the affected scope and the "
                    "measures taken, and will be updated as the picture develops."),
    ("num", "10.3", "This clause does not replace the notification duties in the Data Processing "
                    "Agreement, which apply in addition."),

    ("h2", "11. Change and deprecation notice"),
    ("table", ["Type of change", "Notice"], [
        ["A change to the layout or navigation of the cabinet", "10 business days"],
        ["A change to the structure or the section order of a generated document", "20 business days"],
        ["Removal of a field or a section from a generated document", "30 business days"],
        ["A change to an interface or an integration contract", "30 business days"],
        ["A change to correct a defect or to close a security issue",
         "As soon as reasonably practicable"],
    ]),
    ("num", "11.1", "objectale will give byon at least 6 months' notice before a module is "
                    "withdrawn and at least 12 months' notice before the Platform is withdrawn, to "
                    "the extent objectale itself receives that notice."),

    ("h2", "12. Escalation"),
    ("table", ["Level", "Who", "Trigger"], [
        ["L1 - First line", "byon's own support desk", "On receipt from byon's customer."],
        ["L2 - Second line", "objectale's nominated contact",
         "S1 unresolved after 2 hours; S2 after 1 business day."],
        ["L3 - Management", "objectale's management and the Vendor",
         "S1 unresolved after 4 hours; S2 after 2 business days."],
    ]),

    ("h2", "13. Reporting and review"),
    ("num", "13.1", "objectale will provide a monthly report on request, covering availability, "
                    "maintenance performed and incidents raised by severity against the targets."),
    ("num", "13.2", "The parties will review this SLA annually and may vary it in text form."),

    ("h2", "14. Governing law"),
    ("num", "14.1", "Clause 24 of the Reseller Framework Agreement applies: German law and the "
                    "exclusive jurisdiction of the courts of Frankfurt am Main."),

    ("pagebreak",),
    ("h2", "Schedule A - Contacts and thresholds"),
    ("table", ["Item", "Detail"], [
        ["objectale support e-mail", "[support e-mail]"],
        ["objectale S1 escalation telephone", "[telephone]"],
        ["byon nominated contact 1", "[name] · [e-mail] · [telephone]"],
        ["byon nominated contact 2", "[name] · [e-mail] · [telephone]"],
        ["Large-estate threshold for clause 5.2", "[__ hosts]"],
        ["Monthly report required", "[yes / on request]"],
    ]),
    ("h2", "Summary of commitments"),
    ("table", ["#", "Commitment", "Value"], [
        ["1", "Cabinet availability per calendar month", "99.5%"],
        ["2", "Assessment run completes within", "15 minutes for 95% of runs"],
        ["3", "S1 response / restore", "1 hour / 4 hours"],
        ["4", "S2 response / restore", "4 business hours / 1 business day"],
        ["5", "Planned maintenance per month", "4 hours maximum, 48 hours' notice"],
        ["6", "Backup retention", "7 days"],
        ["7", "Recovery point / recovery time objective", "24 hours / 8 hours"],
        ["8", "Service credit cap per month", "30% of that month's fee"],
        ["9", "Security incident notification", "Within 24 hours of awareness"],
        ["10", "Platform withdrawal notice", "12 months"],
    ]),
    ("pagebreak",),
    ("h2", "Signatures"),
    ("sig", "For %s" % OBJECTALE["name"], "For %s" % BYON["name"],
     ["Name:", "Function:", "Place:", "Date:"]),
]

DE = [
    ("h1", "SERVICE LEVEL AGREEMENT"),
    ("meta", "%s und %s  ·  Anlage zum Wiederverkäufer-Rahmenvertrag  ·  Version %s  ·  %s"
     % (OBJECTALE["name"], BYON["name"], VERSION, DATE_DE)),
    ("note", NOTE_DE),

    ("h2", "1. Zweck und Anwendungsbereich"),
    ("num", "1.1", "Dieses Service Level Agreement (das \"SLA\") ist Anlage zum "
                   "Wiederverkäufer-Rahmenvertrag zwischen %s (\"objectale\") und %s (\"byon\") "
                   "und dessen Bestandteil." % (OBJECTALE["name"], BYON["name"])),
    ("num", "1.2", "Es erfasst das Web-Cabinet, die Telegram-Bots, die Assessment-Engine und die "
                   "Bereitstellung der erzeugten Dokumente (zusammen die \"Plattform\")."),
    ("num", "1.3", "Es erfasst nicht das Netz oder die Endgeräte von byon, die von byon rund um die "
                   "Plattform erbrachten eigenen Leistungen und keine öffentliche Drittdatenquelle, "
                   "die die Plattform auswertet."),

    ("h2", "2. Wer was schuldet"),
    ("num", "2.1", "Die Plattform wird von %s (der \"Hersteller\") betrieben. objectale ist "
                   "Vertragspartner von byon und einziger Ansprechpartner." % OPERATOR),
    ("num", "2.2", "objectale erbringt Second-Level-Support für byon und eskaliert an den "
                   "Hersteller. byon erbringt den First-Level-Support für die eigenen Kunden."),
    ("num", "2.3", "Dieses SLA gilt spiegelbildlich zur Vereinbarung zwischen objectale und dem "
                   "Hersteller. Die nachstehenden Zusagen sind diejenigen, die objectale selbst "
                   "erhält. objectale schuldet byon nicht mehr; byon nimmt dies zur Kenntnis. Sagt "
                   "byon eigenen Kunden mehr zu, trägt byon die Differenz."),

    ("h2", "3. Verfügbarkeit"),
    ("num", "3.1", "Die Zielverfügbarkeit des Cabinets beträgt 99,5% je Kalendermonat."),
    ("num", "3.2", "Die Verfügbarkeit berechnet sich als ((T - P - E - D) / (T - P - E)) x 100, "
                   "wobei T die Gesamtminuten des Monats, P geplante und Notfallwartung, E die "
                   "einer Ausnahme nach Ziffer 8 zurechenbaren Minuten und D die Ausfallzeit ist."),
    ("num", "3.3", "Maßgeblich ist die serverseitige Überwachung des Herstellers. byon kann eine "
                   "Abweichung binnen 10 Arbeitstagen nach Monatsende schriftlich rügen."),
    ("num", "3.4", "Auf Anforderung stellt objectale den erhaltenen monatlichen Verfügbarkeits"
                   "bericht zur Verfügung."),

    ("h2", "4. Wartung"),
    ("num", "4.1", "Geplante Wartung überschreitet insgesamt 4 Stunden je Kalendermonat nicht, wird "
                   "mindestens 48 Stunden vorher per E-Mail an die benannten Ansprechpartner von "
                   "byon angekündigt und außerhalb von 08:00 bis 18:00 Uhr MEZ an Arbeitstagen "
                   "durchgeführt."),
    ("num", "4.2", "Notfallwartung darf durchgeführt werden, wenn der Hersteller sie nach "
                   "billigem Ermessen zur Wahrung der Sicherheit oder Integrität für erforderlich "
                   "hält. Die Ankündigung erfolgt sobald zumutbar möglich, gegebenenfalls im "
                   "Nachhinein."),
    ("num", "4.3", "Geplante Wartung und Notfallwartung sind von der Ausfallzeit und von der "
                   "Verfügbarkeitsberechnung ausgenommen."),

    ("h2", "5. Assessment-Leistung"),
    ("num", "5.1", "Ein Assessment-Lauf wird innerhalb von 15 Minuten nach Annahme der Anforderung "
                   "durch die Engine abgeschlossen, und zwar bei 95% der Läufe je Kalendermonat."),
    ("num", "5.2", "Eine sehr große Umgebung benötigt wesentlich länger und ist von dieser Messung "
                   "ausgenommen. Der Schwellenwert ist in Anlage A festgehalten."),
    ("num", "5.3", "Nach Ziffer 8 ausgenommene sowie vom Nutzer abgebrochene Läufe bleiben "
                   "unberücksichtigt."),

    ("h2", "6. Support und Schweregrade"),
    ("num", "6.1", "Die regulären Supportzeiten sind 09:00 bis 18:00 Uhr MEZ, Montag bis Freitag, "
                   "ausgenommen gesetzliche Feiertage am Sitz von objectale."),
    ("num", "6.2", "Schweregrad 1 wird rund um die Uhr bearbeitet. Alle übrigen Schweregrade werden "
                   "innerhalb der Supportzeiten bearbeitet."),
    ("num", "6.3", "byon schlägt den Schweregrad bei der Meldung vor. Erzielen die Parteien keine "
                   "Einigung, bearbeitet objectale den Vorfall bis zur Einigung mit dem höheren der "
                   "beiden vorgeschlagenen Schweregrade."),
    ("table", ["Schweregrad", "Definition", "Reaktion", "Wiederherstellung oder Workaround"],
     [list(r) for r in SEVERITIES_DE]),
    ("num", "6.4", "Reaktion ist die Zeit bis zu einer inhaltlichen Rückmeldung durch einen "
                   "Menschen, nicht bis zu einer automatischen Empfangsbestätigung. Die "
                   "Wiederherstellung umfasst einen Workaround, der die betroffene Funktion wieder "
                   "nutzbar macht."),

    ("h2", "7. Service-Gutschriften"),
    ("num", "7.1", "Unterschreitet die Verfügbarkeit in einem Monat den Zielwert, kann byon eine "
                   "Gutschrift auf das Entgelt dieses Monats verlangen."),
    ("table", ["Monatsverfügbarkeit", "Gutschrift in Prozent des Monatsentgelts"],
     [list(r) for r in CREDITS_DE]),
    ("num", "7.2", "Eine Gutschrift ist binnen 30 Tagen nach Monatsende schriftlich geltend zu "
                   "machen und muss den Monat, die von byon errechnete Verfügbarkeit und die "
                   "herangezogenen Vorfälle benennen."),
    ("num", "7.3", "Gutschriften sind je Monat auf 30% des Monatsentgelts begrenzt, werden mit "
                   "künftigen Entgelten verrechnet, werden nicht ausgezahlt und sind der "
                   "ausschließliche finanzielle Ausgleich von byon für das Verfehlen der "
                   "Zielverfügbarkeit."),
    ("num", "7.4", "objectale gibt byon eine Gutschrift, die objectale selbst vom Hersteller für "
                   "denselben Zeitraum erhält, insoweit weiter, als sie die nach dieser Ziffer "
                   "berechnete Gutschrift übersteigt."),

    ("h2", "8. Ausnahmen"),
    ("bullet", "Nach Ziffer 4 angekündigte geplante Wartung und Notfallwartung."),
    ("bullet", "Netz, Umgebung, Endgeräte oder Internetzugang von byon."),
    ("bullet", "Nichtverfügbarkeit, Ratenbegrenzung oder Änderung einer öffentlichen "
               "Drittdatenquelle, die die Plattform auswertet."),
    ("bullet", "Missbräuchliche oder Ziffer 7 des Wiederverkäufer-Rahmenvertrages "
               "widersprechende Nutzung."),
    ("bullet", "Jede nach dem Wiederverkäufer-Rahmenvertrag zulässige Sperrung, einschließlich "
               "wegen Zahlungsverzugs oder vermuteter Kompromittierung."),
    ("bullet", "Ein Ereignis außerhalb des zumutbaren Einflussbereichs von objectale oder des "
               "Herstellers."),
    ("bullet", "Nutzung einer Test-, Pilot-, Sandbox-, Beta- oder Vorschaufunktion."),

    ("h2", "9. Sicherung und Wiederherstellung"),
    ("num", "9.1", "Sicherungen werden täglich erstellt und 7 Tage aufbewahrt."),
    ("num", "9.2", "Wiederherstellungspunkt: 24 Stunden. Wiederherstellungszeit: 8 Stunden, "
                   "gemessen ab dem Zeitpunkt der Auslösung."),
    ("num", "9.3", "Dokumente, die erzeugt, aber vor einem Ereignis innerhalb des "
                   "Wiederherstellungspunkts nicht heruntergeladen wurden, müssen gegebenenfalls "
                   "neu erzeugt werden. Die Neuerzeugung eines solchen Dokuments ist "
                   "unentgeltlich."),

    ("h2", "10. Meldung von Sicherheitsvorfällen"),
    ("num", "10.1", "objectale informiert byon unverzüglich, in jedem Fall binnen 24 Stunden ab "
                    "Kenntnis, über einen Sicherheitsvorfall, der Daten von byon oder die Nutzung "
                    "der Plattform durch byon betrifft."),
    ("num", "10.2", "Die Meldung beschreibt den bekannten Sachverhalt, den betroffenen Umfang und "
                    "die getroffenen Maßnahmen und wird mit fortschreitender Aufklärung "
                    "aktualisiert."),
    ("num", "10.3", "Diese Ziffer ersetzt nicht die Meldepflichten aus dem "
                    "Auftragsverarbeitungsvertrag; diese gelten zusätzlich."),

    ("h2", "11. Änderungs- und Abkündigungsfristen"),
    ("table", ["Art der Änderung", "Frist"], [
        ["Änderung von Layout oder Navigation des Cabinets", "10 Arbeitstage"],
        ["Änderung von Aufbau oder Abschnittsreihenfolge eines erzeugten Dokuments",
         "20 Arbeitstage"],
        ["Entfernen eines Feldes oder Abschnitts aus einem erzeugten Dokument", "30 Arbeitstage"],
        ["Änderung einer Schnittstelle oder eines Integrationsvertrages", "30 Arbeitstage"],
        ["Änderung zur Beseitigung eines Mangels oder zur Schließung einer Sicherheitslücke",
         "Sobald zumutbar möglich"],
    ]),
    ("num", "11.1", "objectale kündigt byon die Abkündigung eines Moduls mindestens 6 Monate und "
                    "die Abkündigung der Plattform mindestens 12 Monate im Voraus an, soweit "
                    "objectale diese Ankündigung selbst erhält."),

    ("h2", "12. Eskalation"),
    ("table", ["Stufe", "Wer", "Auslöser"], [
        ["L1 - First Level", "Eigener Support von byon", "Bei Eingang vom Kunden von byon."],
        ["L2 - Second Level", "Benannter Ansprechpartner von objectale",
         "S1 nach 2 Stunden ungelöst; S2 nach 1 Arbeitstag."],
        ["L3 - Management", "Geschäftsleitung von objectale und der Hersteller",
         "S1 nach 4 Stunden ungelöst; S2 nach 2 Arbeitstagen."],
    ]),

    ("h2", "13. Berichte und Überprüfung"),
    ("num", "13.1", "objectale stellt auf Anforderung einen Monatsbericht bereit, der "
                    "Verfügbarkeit, durchgeführte Wartung und gemeldete Vorfälle nach Schweregrad "
                    "im Vergleich zu den Zielwerten ausweist."),
    ("num", "13.2", "Die Parteien überprüfen dieses SLA jährlich und können es in Textform ändern."),

    ("h2", "14. Anwendbares Recht"),
    ("num", "14.1", "Es gilt Ziffer 24 des Wiederverkäufer-Rahmenvertrages: deutsches Recht und "
                    "ausschließlicher Gerichtsstand Frankfurt am Main."),

    ("pagebreak",),
    ("h2", "Anlage A - Ansprechpartner und Schwellenwerte"),
    ("table", ["Angabe", "Detail"], [
        ["Support-E-Mail objectale", "[E-Mail]"],
        ["S1-Eskalationstelefon objectale", "[Telefon]"],
        ["Benannter Ansprechpartner byon 1", "[Name] · [E-Mail] · [Telefon]"],
        ["Benannter Ansprechpartner byon 2", "[Name] · [E-Mail] · [Telefon]"],
        ["Schwellenwert große Umgebung nach Ziffer 5.2", "[__ Hosts]"],
        ["Monatsbericht erforderlich", "[ja / auf Anforderung]"],
    ]),
    ("h2", "Übersicht der Zusagen"),
    ("table", ["#", "Zusage", "Wert"], [
        ["1", "Verfügbarkeit des Cabinets je Kalendermonat", "99,5%"],
        ["2", "Assessment-Lauf abgeschlossen innerhalb von", "15 Minuten bei 95% der Läufe"],
        ["3", "S1 Reaktion / Wiederherstellung", "1 Stunde / 4 Stunden"],
        ["4", "S2 Reaktion / Wiederherstellung", "4 Arbeitsstunden / 1 Arbeitstag"],
        ["5", "Geplante Wartung je Monat", "höchstens 4 Stunden, 48 Stunden Vorlauf"],
        ["6", "Aufbewahrung der Sicherungen", "7 Tage"],
        ["7", "Wiederherstellungspunkt / Wiederherstellungszeit", "24 Stunden / 8 Stunden"],
        ["8", "Obergrenze der Gutschriften je Monat", "30% des Monatsentgelts"],
        ["9", "Meldung von Sicherheitsvorfällen", "binnen 24 Stunden ab Kenntnis"],
        ["10", "Abkündigungsfrist der Plattform", "12 Monate"],
    ]),
    ("pagebreak",),
    ("h2", "Unterschriften"),
    ("sig", "Für %s" % OBJECTALE["name"], "Für %s" % BYON["name"],
     ["Name:", "Funktion:", "Ort:", "Datum:"]),
]
