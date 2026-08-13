#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_byon_de_deck.py - cybergod.ai fuer die byon gmbh, auf Deutsch.

    python marketing/build_byon_de_deck.py

ADRESSAT: byon gmbh, Frankfurt am Main. Vorgetragen von Uwe Deiters (Objectale, ud@objectale.ch)
als unser Reseller. byon ist damit ein moeglicher PARTNER, nicht ein Endkunde, und das Deck ist
entsprechend eine Partner-Argumentation: Marge, Anlass, Upsell, Wiederholung.

WAS AUS DER QUELLE STAMMT, NICHT AUS DER PHANTASIE (byon.de, abgerufen 13.08.2026):
  · Frankfurt/Main, Solmsstrasse 71, gegruendet 2006, seit 2023 Teil der 360 ITC Gruppe
  · ueber 100 Mitarbeitende, darunter eine EIGENE (Software-)Entwicklung
  · Portfolio: Managed Firewall, SASE 2.0, SIEM, Zero Trust, KRITIS, Managed SBC und WLAN,
    SD-WAN, MPLS, Ethernet VPN, DIA, Dark Fibre, Microsoft 365, Intune, Purview,
    Cloud-Telefonie, ACD, Teams, SIP Trunks
  · GENANNTE REFERENZEN: Caritas, Der Paritaetische, maincubes, book-n-drive, Selecta
Die zehn Vertikalen in diesem Deck sind aus DIESEN Referenzen und diesem Portfolio abgeleitet,
nicht aus einer allgemeinen Branchenliste. Eine erfundene Zielgruppenliste faellt in der ersten
Rueckfrage auf.

DIE ZENTRALE THESE: cybergod.ai konkurriert nicht mit dem byon-Katalog, es ist der ANLASS dafuer.
Jeder Befund zeigt auf ein Produkt, das bei byon bereits im Regal steht.

BELEGE STATT BEHAUPTUNGEN:
  · "Wir sind ein Entwicklungshaus" wird mit dem echten Git-Log belegt: 112 Releases an 14 aktiven
    Tagen (30.07. bis 13.08.2026). Eine Zahl aus dem Repository, nachrechenbar.
  · Der Ernstfall vom 10.08. (Scanner, sechs Browser-Kennungen in zwei Sekunden) wurde am SELBEN
    TAG mit einem ausgelieferten Schild beantwortet. Datierbar im Log.
  · Kein Vergleich mit namentlich genannten Wettbewerbern ohne Beleg. Wo wir "3 bis 6 Monate"
    nennen, ist das der branchenuebliche Quartals-Releasezyklus als Kategorie, nicht eine
    Behauptung ueber ein bestimmtes Produkt.

STIL: keine langen Gedankenstriche (stehende Regel des Betreibers).
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_consensus_deck import (  # noqa: E402  - eine Template-Implementierung, wiederverwendet
    AMBER, BODY, CYAN, Deck, GREEN, INDIGO, MONO, MUTED, RED, VIOLET, WHITE,
    _rect, _tb, bullets, card, stat,
)
from build_consensus_business_deck import table  # noqa: E402

FOOT = ("S4BIZ GROUP · CYBERGOD LLC · FUER byon gmbh · AUGUST 2026 · "
        "VERTRAULICH, NUR FUER DEN INTERNEN GEBRAUCH BEI byon")
TITLE_MAX = 46


def _title(d, eyebrow, title, tail, sub, footer=FOOT):
    """Slide mit Breitenpruefung der Titelzeile VOR dem Rendern.

    Deutsch ist wie Russisch laenger als Englisch, und die Titelzeile hat eine feste Breite. Ein
    umbrechender Titel legt sich auf die Unterzeile, und das sieht man erst im Rendering.
    """
    n = len(title) + len(tail or "")
    if n > TITLE_MAX:
        raise SystemExit("[X] Titelzeile hat %d Zeichen und bricht um (max %d): %r"
                         % (n, TITLE_MAX, title + (tail or "")))
    return d.slide(eyebrow, title, tail, sub=sub, footer=footer)


def build(template, out):
    d = Deck(template)

    # ============================================================================ 01 Titel
    d.slide("fuer byon gmbh · august 2026",
            [("IHR KATALOG", WHITE), ("IST FERTIG.", WHITE),
             ("UNS FEHLT NUR", CYAN), ("DER ANLASS.", CYAN)],
            hero=True, footer=FOOT)

    # ================================================================= 02 Warum dieses Gespraech
    s = _title(d, "warum dieses gespraech", "byon hat alles im Regal. ", "Ausser dem Auslöser.",
               "Managed Firewall, SASE 2.0, SIEM, Zero Trust, KRITIS. Alles da. Der Anlass fehlt.")
    card(s, 0.62, 2.02, 3.9, 2.42, "DIE LAGE", MUTED, "Ein starker Katalog",
         "Ueber 30 Jahre ITK, eigene Cloud, eigene Entwicklung, 100+ Mitarbeitende. Netz, "
         "Microsoft, UC und IT-Security aus einer Hand.\n\nDas Angebot ist nicht das Problem.")
    card(s, 4.72, 2.02, 3.9, 2.42, "DAS PROBLEM", RED, "Der kalte Erstkontakt",
         "Ein Interessent, zu dem noch keine Beziehung besteht, hat keinen Grund, ueber SASE oder "
         "SIEM zu sprechen. Er hat kein Problem, das er sehen kann.\n\nDie Frage lautet nicht "
         "\"was koennen Sie\", sondern \"warum jetzt\".")
    card(s, 8.82, 2.02, 3.9, 2.42, "UNSER BEITRAG", CYAN, "Der sichtbare Anlass",
         "In 5 bis 7 Minuten, allein aus dem Firmennamen, vier praesentationsfertige Unterlagen "
         "darueber, was das Internet ueber dieses Unternehmen bereits weiss.\n\nOhne Zugang, ohne "
         "Auftrag, ohne ein einziges Paket an den Interessenten.")
    _tb(s, 0.62, 4.72, 12.1, 0.6,
        "cybergod.ai konkurriert nicht mit dem byon-Katalog. Es erzeugt die Nachfrage danach.",
        12.5, CYAN, MONO)

    # ==================================================================== 03 Was geliefert wird
    s = _title(d, "das ergebnis", "Was nach 5 bis 7 ", "Minuten vorliegt",
               "Eingabe ist ein Firmenname. Mehr braucht die Maschine nicht.")
    stat(s, 0.62, 2.06, 2.9, "5-7 Min", "VOM FIRMENNAMEN\nZUR FERTIGEN UNTERLAGE", CYAN)
    stat(s, 3.72, 2.06, 2.9, "0 Pakete", "AN DAS BEWERTETE\nUNTERNEHMEN GESENDET", GREEN)
    stat(s, 6.82, 2.06, 2.9, "4 + 1", "PRAESENTATIONEN PLUS\nANIMIERTER HTML-REPORT", VIOLET)
    stat(s, 9.92, 2.06, 2.9, "DE / EN / RU", "DOKUMENTSPRACHE\nJE KUNDE WAEHLBAR", AMBER)
    bullets(s, 0.62, 4.12, 12.1, [
        "Befunde: die von aussen sichtbare Angriffsflaeche, nach Schweregrad, mit Beweis je Fund.",
        "C-BIQ: die Risikobewertung in Euro, in der Sprache der Geschaeftsfuehrung, nicht in CVEs.",
        "Geopolitik: welche Akteure zu diesem Profil passen und was sie ueblicherweise tun.",
        "Massnahmen: eine Reihenfolge, die ein Vorstand beschliessen kann, herstellerneutral.",
        "Lauf-Protokoll: das vollstaendige Protokoll des Laufs, geschwaerzt, fuer den Endkunden.",
    ], size=11.5, gap=0.34)

    # ======================================================== 04 Null Pakete, kommerzieller Hebel
    s = _title(d, "der kommerzielle hebel", "Null Pakete heisst ", "null Genehmigung",
               "Das ist keine technische Feinheit. Das ist der Grund, warum es im Vertrieb funktioniert.")
    card(s, 0.62, 2.02, 5.95, 2.3, "AKTIVER SCAN", RED, "Braucht eine Unterschrift",
         "Ein Penetrationstest oder Schwachstellenscan sendet Pakete an fremde Systeme. Das "
         "erfordert eine schriftliche Beauftragung des Verfuegungsberechtigten, sonst ist es in "
         "Deutschland §202a und §303b StGB.\n\nAlso: erst Vertrag, dann Erkenntnis. Und der "
         "Vertrag setzt genau die Beziehung voraus, die noch nicht existiert.")
    card(s, 6.77, 2.02, 5.95, 2.3, "cybergod.ai", GREEN, "Braucht gar nichts",
         "Wir lesen ausschliesslich oeffentliche Quellen: Shodan, Certificate Transparency, "
         "oeffentliches DNS, RIPE, BGP.\n\nKein Paket an den Interessenten, kein Auftrag, kein "
         "NDA, kein Jurist. Die Unterlage liegt VOR dem ersten Termin auf dem Tisch, nicht danach.")
    _rect(s, 0.62, 4.58, 12.1, 1.22, fill=INDIGO)
    _tb(s, 0.86, 4.72, 11.6, 0.3, "WAS DAS FUER DEN TERMIN BEDEUTET", 12, WHITE, MONO, bold=True)
    _tb(s, 0.86, 5.04, 11.6, 0.64,
        "Der Vertriebsmitarbeiter kommt nicht mit einer Broschuere, sondern mit vier Seiten "
        "darueber, was am Perimeter dieses Unternehmens heute offen steht. Das Gespraech beginnt "
        "beim Befund, nicht bei der Vorstellungsrunde. Und der Befund gehoert byon.", 11.5, BODY)

    # ======================================================= 05 Entwicklungshaus, mit Beleg
    s = _title(d, "wer wir sind", "Wir sind ein ", "Entwicklungshaus",
               "Kein Vertriebsbuero vor einer fremden Plattform. Der Beweis ist datiert.")
    stat(s, 0.62, 2.06, 2.9, "112", "RELEASES IN 14 TAGEN\n30.07. BIS 13.08.2026", CYAN)
    stat(s, 3.72, 2.06, 2.9, "14 / 14", "TAGE MIT MINDESTENS\nEINEM RELEASE", GREEN)
    stat(s, 6.82, 2.06, 2.9, "2-3 Tage", "VON DER ANFORDERUNG\nZUM AUSGELIEFERTEN FEATURE", VIOLET)
    stat(s, 9.92, 2.06, 2.9, "1 Befehl", "TEST, FREIGABE, DEPLOY\nUND RUECKROLLPUNKT", AMBER)
    _rect(s, 0.62, 4.12, 12.1, 2.02, fill=INDIGO)
    _tb(s, 0.86, 4.26, 11.6, 0.3,
        "WARUM DAS FUER byon KOMMERZIELL RELEVANT IST", 12, WHITE, MONO, bold=True)
    bullets(s, 0.86, 4.60, 11.5, [
        "Ein Wunsch aus einem byon-Termin ist bei uns in Tagen im Produkt. Branchenueblich sind "
        "bei Enterprise-Software Quartalszyklen, also 3 bis 6 Monate.",
        "Das ist ein Vertriebsargument: byon kann im Termin zusagen, statt zu vertroesten. Eine "
        "Zusage, die in drei Tagen eingeloest wird, gewinnt Ausschreibungen.",
        "Neue Sprache, neue Rechtsordnung, neues Regelwerk: Konfiguration statt Neuentwicklung. "
        "Russisch und die kanadische Regulatorik entstanden so, in jeweils wenigen Tagen.",
    ], size=10.5, gap=0.46)

    # ================================================================ 06 Der Ernstfall als Beweis
    s = _title(d, "der beweis am ernstfall", "Angriff am 10.08. ", "Antwort am 10.08.",
               "Nicht im Labor. Am eigenen Server, mit Datum im Protokoll.")
    for i, (k, kc, h, b) in enumerate([
        ("19:05:55 UTC", RED, "Der Scanner",
         "Eine Adresse, zwei Sekunden, sechs verschiedene Browser-Kennungen. Gesucht wurden "
         "/DOCS.md und /IAM.md: interne Dokumentation und Rechtemodell."),
        ("NOCH AM 10.08.", AMBER, "Das Schild",
         "Deterministische Abwehr im Anfragepfad ausgeliefert. Erkennung in Mikrosekunden, "
         "danach Tarpit und befristete Sperre."),
        ("11.08.", GREEN, "Die Konsole",
         "Sechs Freigabeoptionen auf dem Telefon des Betreibers, Bestaetigung mit dem tatsaechlich "
         "gelesenen Zustand innerhalb von 20 Sekunden."),
        ("12.08.", VIOLET, "Die oeffentliche Seite",
         "Live-Ansicht der Angriffe, DSGVO-konform auf /24 gekuerzt. Vom Vorfall zur "
         "praesentierbaren Funktion in zwei Tagen."),
    ]):
        card(s, 0.62 + i * 3.08, 2.06, 2.88, 2.5, k, kc, h, b, bsize=9.2)
    _tb(s, 0.62, 4.78, 12.1, 0.86,
        "Das ist die Geschwindigkeit, die byon im Termin verkaufen kann. Ein Wettbewerber, der "
        "einen Vorfall im naechsten Quartals-Release adressiert, argumentiert gegen ein Datum im "
        "oeffentlichen Commit-Verlauf.", 11.5, BODY)

    # ================================================================= 07 Warum guenstiger
    s = _title(d, "warum wir guenstiger sind", "Der Preis folgt ", "der Architektur",
               "Nicht Dumping, sondern eine andere Kostenstruktur.")
    table(s, 0.62, 2.02, 12.1,
          ["KOSTENTREIBER", "KLASSISCHER ANBIETER", "cybergod.ai"],
          [["Erhebung", "eigene Sensorik, Agenten, Crawler", "oeffentliche Quellen, keine Sensorik"],
           ["Bereitstellung", "Installation beim Kunden", "keine, es wird nichts installiert"],
           ["Analyse", "Analystenstunden", "Maschine, danach vier Modelle zur Pruefung"],
           ["KI-Kosten je Lauf", "meist nicht ausgewiesen", "rund 0,005 USD, aus dem Kostenbuch"],
           ["Vertriebsmodell", "Jahresabonnement je Asset", "Preis je Lauf"],
           ["Erster Termin kostet", "einen Jahresbudgetposten", "einen Lauf"]],
          [0.28, 0.36, 0.36])
    _tb(s, 0.62, 5.28, 12.1, 0.62,
        "Ein Abonnement zwingt den Partner, das ganze Jahr zu verkaufen, bevor der erste Nutzen "
        "sichtbar ist. Ein Preis je Lauf laesst byon mit 100 Euro in ein Gespraech gehen, das "
        "sonst gar nicht stattgefunden haette.", 11.5, MUTED, MONO)

    # ==================================================================== 08 Spielfeld / Gameplay
    s = _title(d, "das spielfeld", "Der Vertriebszyklus ", "in sechs Zuegen",
               "So sieht der Ablauf beim Endkunden aus, vom kalten Namen bis zum Rahmenvertrag.")
    moves = [
        ("ZUG 1", "Zielauswahl", "byon waehlt 20 Namen aus einer Vertikale. Kein Kontakt noetig."),
        ("ZUG 2", "Lauf", "20 Assessments, ueber Nacht, im Namen und Logo von byon."),
        ("ZUG 3", "Aufhaenger", "Anschreiben mit EINEM konkreten Befund. Keine Broschuere."),
        ("ZUG 4", "Termin", "Die Unterlage liegt auf dem Tisch. Das Gespraech beginnt beim Befund."),
        ("ZUG 5", "Upsell", "Jeder Befund zeigt auf ein byon-Produkt. Siehe naechste Seite."),
        ("ZUG 6", "Takt", "Wiederholung nach Groesse: einmalig, quartalsweise oder woechentlich."),
    ]
    for i, (k, h, b) in enumerate(moves):
        col = 0.62 + (i % 3) * 4.1
        row = 2.06 + (i // 3) * 1.74
        card(s, col, row, 3.9, 1.6, k, CYAN if i < 3 else GREEN, h, b, bsize=9.5)
    _tb(s, 0.62, 5.5, 12.1, 0.4,
        "Der Engpass im Neugeschaeft ist nicht das Angebot, sondern der Grund fuer den ersten "
        "Termin. Genau diesen Engpass loest Zug 2.", 11.5, CYAN, MONO)

    # =========================================================== 09 Upsell-Matrix, der Kern
    s = _title(d, "der kern fuer byon", "Jeder Befund zeigt ", "auf ein byon-Produkt",
               "Das Assessment ist die Bedarfsanalyse, die byon sonst nicht bezahlt bekommt.")
    table(s, 0.5, 1.96, 12.35,
          ["TYPISCHER BEFUND AUS DEM ASSESSMENT", "BYON-PRODUKT, DAS DIREKT FOLGT", "ANLASS"],
          [["Firewall oder VPN-Portal offen im Internet", "Managed Firewall · SASE 2.0", "sofort"],
           ["Verwaltungszugaenge ohne Segmentierung erreichbar", "Zero Trust · ZTNA", "sofort"],
           ["Kein zentrales Ereignis-Monitoring erkennbar", "SIEM · Managed Detection", "Quartal"],
           ["SIP oder SBC von aussen ansprechbar", "Managed SBC · SIP Trunks", "sofort"],
           ["Standorte ohne redundante Anbindung", "SD-WAN · Ethernet VPN · DIA", "Projekt"],
           ["M365 ohne Härtung, Purview ungenutzt", "Modern Workplace · Intune · Purview", "Quartal"],
           ["OT oder Gebaeudetechnik im Netz sichtbar", "Segmentierung · KRITIS-Beratung", "sofort"],
           ["Kein DMARC, Domain fuer Spoofing offen", "E-Mail-Sicherheit · Consulting", "sofort"],
           ["NIS2-Betroffenheit erkennbar, nichts umgesetzt", "KRITIS-Paket · SIEM · Zero Trust", "Projekt"]],
          [0.44, 0.37, 0.19])

    # =========================================================== 10 Einsatzfrequenz
    s = _title(d, "wie oft wird gelaufen", "Einmalig, quartalsweise ", "oder woechentlich",
               "Der Takt richtet sich nach der Groesse der Organisation, nicht nach dem Preisplan.")
    card(s, 0.62, 2.02, 3.9, 2.36, "EINMALIG", MUTED, "Mittelstand bis 500 Mitarbeitende",
         "Ein Lauf als Tueroeffner, ein zweiter nach der Umsetzung als Nachweis.\n\nTypisch: 2 "
         "Laeufe je Kunde und Jahr. Der Wert fuer byon liegt im Folgegeschaeft, nicht im Lauf.")
    card(s, 4.72, 2.02, 3.9, 2.36, "QUARTALSWEISE", CYAN, "Gehobener Mittelstand, mehrere Standorte",
         "Der Perimeter aendert sich mit jedem Projekt, jeder Uebernahme, jedem neuen Standort."
         "\n\nTypisch: 4 Laeufe je Jahr, plus je ein Lauf nach groesseren Aenderungen.")
    card(s, 8.82, 2.02, 3.9, 2.36, "WOECHENTLICH", GREEN, "Konzern, KRITIS, Finanzsektor",
         "So haben wir es fuer eine grosse nordamerikanische Bank aufgesetzt: woechentlicher Lauf, "
         "Differenz zur Vorwoche, Eskalation nur bei Veraenderung.\n\nTypisch: 52 Laeufe je Jahr.")
    _tb(s, 0.62, 4.66, 12.1, 1.0,
        "WICHTIG FUER DIE MARGENRECHNUNG: der Preis je Lauf macht den woechentlichen Takt "
        "ueberhaupt erst bezahlbar. Bei einem Abonnementmodell zahlt der Kunde die Frequenz nicht "
        "nach Bedarf, sondern nach Vertrag. byon kann den Takt am Kunden ausrichten und die "
        "Differenz als eigene Leistung berechnen.", 11.5, BODY)

    # ============================================================ 11 Top 10 Vertikale
    s = _title(d, "zielgruppen", "Zehn Vertikale, aus ", "byons Referenzen",
               "Abgeleitet aus den auf byon.de genannten Referenzen und dem Portfolio.")
    table(s, 0.4, 1.94, 12.55,
          ["#", "VERTIKALE", "ANKER BEI byon", "WARUM DER PERIMETER DORT INTERESSANT IST"],
          [["1", "Sozialwirtschaft und Wohlfahrt", "Caritas, Der Paritaetische",
            "sehr viele Standorte, gewachsene IT, knappe Budgets"],
           ["2", "Gesundheit und Pflege", "Sozialwirtschaft angrenzend",
            "KRITIS, Medizintechnik im Netz, hohe Schadenshoehe"],
           ["3", "Rechenzentren und Colocation", "maincubes",
            "KRITIS, Kunden fragen nach Nachweisen, Reputationsrisiko"],
           ["4", "Energie und Wasser, Stadtwerke", "KRITIS-Portfolio",
            "KRITIS, Fernwirktechnik, gesetzliche Nachweispflicht"],
           ["5", "Mobilitaet und Verkehr", "book-n-drive",
            "viele Endpunkte im Feld, Buchungsplattform oeffentlich"],
           ["6", "Fertigung und Maschinenbau", "Mittelstandsfokus",
            "OT im Netz, Fernwartung, Lieferkettenanforderungen"],
           ["7", "Logistik und Transport", "SD-WAN, Standortanbindung",
            "viele Standorte, Partnerzugaenge, Betriebsunterbrechung teuer"],
           ["8", "Handel und Filialservices", "Selecta",
            "Filialnetz, Zahlungsverkehr, Automaten und IoT im Feld"],
           ["9", "Finanzdienstleister und Versicherer", "Zero Trust, SIEM",
            "DORA, Auslagerungsmanagement, Lieferantenpruefung"],
           ["10", "Oeffentliche Hand und kommunale IT", "KRITIS, M365",
            "NIS2-Umsetzung, Vergaberecht, hoher Nachweisdruck"]],
          [0.04, 0.24, 0.20, 0.52], size=9.4, rh=0.36)

    # ======================================================= 12 Playbook A
    s = _title(d, "playbook a", "Sozialwirtschaft, Pflege ", "und Rechenzentren",
               "Der Aufhaenger je Vertikale, in einem Satz, so wie er im Anschreiben steht.")
    for i, (k, kc, h, b) in enumerate([
        ("VERTIKALE 1 UND 2", CYAN, "Sozialwirtschaft, Wohlfahrt, Pflege",
         "AUFHAENGER: gewachsene Standortlandschaft. Typischer Erstbefund sind offene "
         "Verwaltungszugaenge einzelner Einrichtungen, die in der Zentrale niemand kennt.\n\n"
         "GESPRAECHSPARTNER: Geschaeftsfuehrung und IT-Leitung, oft in Personalunion.\n\n"
         "UPSELL: Segmentierung, Managed Firewall, danach M365-Haertung ueber alle Einrichtungen."),
        ("VERTIKALE 3", VIOLET, "Rechenzentren und Colocation",
         "AUFHAENGER: hier wird der Bericht selbst zum Produkt. Ein Betreiber, der seinen eigenen "
         "Perimeter belegen kann, gewinnt Ausschreibungen bei seinen Kunden.\n\n"
         "GESPRAECHSPARTNER: Geschaeftsfuehrung, Vertrieb und Compliance, nicht nur die Technik."
         "\n\nUPSELL: wiederkehrender Lauf als Nachweis, KRITIS-Beratung, SIEM."),
    ]):
        card(s, 0.62 + i * 6.15, 2.02, 5.95, 3.24, k, kc, h, b, bsize=10)
    _tb(s, 0.62, 5.44, 12.1, 0.44,
        "In beiden Faellen ist der erste Befund fast nie eine Schwachstelle im klassischen Sinn, "
        "sondern ein vergessener Standort. Das ist ein Gespraech ueber Ordnung, nicht ueber Angst.",
        11.5, MUTED, MONO)

    # ======================================================= 13 Playbook B
    s = _title(d, "playbook b", "Energie, Mobilität, ", "Fertigung, Logistik",
               "Vier Vertikale, in denen ein sichtbarer Befund sofort ein Projekt ausloest.")
    for i, (k, kc, h, b) in enumerate([
        ("VERTIKALE 4", RED, "Energie, Wasser, Stadtwerke",
         "Nachweispflicht nach BSIG. Ein Befund zu erreichbarer Fernwirk- oder Gebaeudetechnik ist "
         "unmittelbar ein Vorstandsthema.\n\nUPSELL: KRITIS-Paket, Segmentierung, SIEM."),
        ("VERTIKALE 5", AMBER, "Mobilitaet und Verkehr",
         "Buchungsplattform und Fahrzeugtelematik sind oeffentlich erreichbar, das Backend "
         "haeufig ueber Dienstleister.\n\nUPSELL: SASE 2.0, Zero Trust, Lieferantenpruefung."),
        ("VERTIKALE 6", CYAN, "Fertigung und Maschinenbau",
         "Fernwartungszugaenge von Maschinenlieferanten sind der klassische Erstbefund, und der "
         "Kunde kennt sie meist nicht.\n\nUPSELL: Segmentierung, Managed Firewall, ZTNA."),
        ("VERTIKALE 7", GREEN, "Logistik und Transport",
         "Viele Standorte, viele Partnerzugaenge. Eine Stunde Stillstand ist hier direkt in Euro "
         "berechenbar, was die C-BIQ-Unterlage stark macht.\n\nUPSELL: SD-WAN, DIA, Redundanz."),
    ]):
        col = 0.62 + (i % 2) * 6.15
        row = 2.02 + (i // 2) * 1.86
        card(s, col, row, 5.95, 1.74, k, kc, h, b, bsize=9.4)

    # ======================================================= 14 Playbook C
    s = _title(d, "playbook c", "Handel, Finanz ", "und oeffentliche Hand",
               "Drei Vertikale mit dem laengsten Zyklus und dem groessten Vertragswert.")
    for i, (k, kc, h, b) in enumerate([
        ("VERTIKALE 8", AMBER, "Handel und Filialservices",
         "Filialnetz, Zahlungsverkehr, Automaten und IoT im Feld. Der Erstbefund ist oft ein "
         "Geraet, das seit Jahren am Netz haengt und in keiner Inventarliste steht.\n\n"
         "UPSELL: Segmentierung, Managed WLAN, SD-WAN je Filiale."),
        ("VERTIKALE 9", VIOLET, "Finanzdienstleister und Versicherer",
         "DORA verlangt ein Auslagerungs- und Lieferantenmanagement mit Nachweis. Genau dafuer "
         "eignet sich ein wiederkehrender Lauf je Lieferant.\n\n"
         "UPSELL: Portfolio-Modus ueber viele Lieferanten, SIEM, Zero Trust."),
        ("VERTIKALE 10", CYAN, "Oeffentliche Hand und kommunale IT",
         "NIS2-Umsetzung mit hohem Nachweisdruck und knapper Personaldecke. Die Unterlage ist "
         "hier haeufig die Beschlussvorlage.\n\n"
         "UPSELL: KRITIS-Beratung, M365 mit Purview, Managed Services."),
    ]):
        card(s, 0.62 + i * 4.1, 2.02, 3.9, 3.2, k, kc, h, b, bsize=9.4)
    _tb(s, 0.62, 5.4, 12.1, 0.44,
        "Bei 9 und 10 ist nicht der Einzelkunde das Geschaeft, sondern dessen Lieferantenliste. "
        "Ein Kunde mit 200 Lieferanten sind 200 Laeufe, und byon steht auf jedem Deckblatt.",
        11.5, CYAN, MONO)

    # ================================================================ 15 NIS2 als zweiter Motor
    s = _title(d, "der zweite motor", "NIS2 und KRITIS ", "als eigener Anlass",
               "Ein zweites Modul mit demselben Ablauf: ein Firmenname, fertige Unterlagen.")
    card(s, 0.62, 2.02, 5.95, 2.4, "WAS ES TUT", CYAN, "Regulatorische Einstufung",
         "Bewertung gegen NIS2, Cyber Resilience Act und EU AI Act. Vier Praesentationen plus "
         "Fahrplan, in Deutsch.\n\nDie Annahmen zur Betroffenheit werden offen ausgewiesen und "
         "danach mit dem Kunden bestaetigt oder korrigiert, statt sie zu behaupten.")
    card(s, 6.77, 2.02, 5.95, 2.4, "WARUM DAS FUER byon PASST", GREEN, "byon verkauft KRITIS bereits",
         "byon fuehrt KRITIS als eigenes Beratungsthema. Das Compliance-Modul liefert dafuer den "
         "dokumentierten Einstieg, ohne dass ein Berater vorab Tage investiert.\n\n"
         "Aus der Einstufung folgen unmittelbar SIEM, Zero Trust und Segmentierung.")
    _tb(s, 0.62, 4.62, 12.1, 1.1,
        "EHRLICH GESAGT: das ist keine Rechtsberatung, und jede Unterlage sagt das auch. Fristen "
        "und Bussgeldrahmen sind aus den Primaertexten zitiert und mit Stand versehen, weil die "
        "nationale NIS2-Umsetzung sich noch bewegt. Ein Partner, der hier mehr verspricht als er "
        "belegen kann, verliert den Kunden beim ersten Nachfassen des Justiziars.", 11.5, BODY)

    # ================================================== 16 Unterscheidung: 4 Modelle + Live-Siege
    s = _title(d, "was uns unterscheidet", "Vier Modelle prüfen. ", "Der Code entscheidet.",
               "Und dieselbe Mechanik verteidigt unsere eigene Plattform, sichtbar in Echtzeit.")
    card(s, 0.62, 2.02, 3.9, 2.36, "DER KONSENSUS", VIOLET, "Vier Anbieter, nicht vier Rollen",
         "Zwei Modelle schreiben, zwei pruefen. Der Pruefer ist nie der Autor und nie vom selben "
         "Anbieter.\n\nEin Ausfall oder blinder Fleck eines Anbieters kommt nicht durch.")
    card(s, 4.72, 2.02, 3.9, 2.36, "DREI EINSATZORTE", CYAN, "Nicht nur im Bericht",
         "1. Aktive Abwehr der Plattform.\n2. Freigabe jedes Releases auf einer Kopie der "
         "Produktion, inklusive Neustart.\n3. Die Release-Notes selbst.\n\nJeden Tag im Betrieb, "
         "nicht als Demonstration.")
    card(s, 8.82, 2.02, 3.9, 2.36, "LIVE ZU ZEIGEN", GREEN, "cybergod.ai/defense.html",
         "Die Angriffe auf unsere eigene Plattform, animiert und in Echtzeit, DSGVO-konform auf "
         "/24 gekuerzt.\n\nIm Termin ist das der Moment, in dem das Thema fuer den Kunden konkret "
         "wird.")
    _tb(s, 0.62, 4.62, 12.1, 1.0,
        "Wir behaupten NICHT, dass unsere Modelle klueger sind als die anderer Anbieter. Das haben "
        "wir nicht gemessen, und eine solche Aussage ueber ein namentlich genanntes Produkt waere "
        "nach §6 UWG belegpflichtig. Die Aussage ist eine andere und sie ist pruefbar: vier "
        "unabhaengige Anbieter und die Entscheidung im Code ergeben Eigenschaften, die ein "
        "einzelnes Modell nicht haben kann.", 11.5, MUTED, MONO)

    # ============================================================ 17 Partnermodell, naechste Schritte
    s = _title(d, "partnermodell", "Was byon bekommt ", "und was jetzt folgt",
               "Drei konkrete Schritte, alle innerhalb der naechsten zwei Wochen machbar.")
    table(s, 0.62, 1.98, 12.1,
          ["BAUSTEIN", "INHALT"],
          [["White-Label", "byon-Logo auf Deckblatt und Bericht. Der Endkunde sieht byon, nicht uns."],
           ["Preis je Lauf", "Listenpreis 100 EUR, Partnerkondition ab 60 EUR je Lauf."],
           ["Abonnement", "200 EUR je Monat Liste, Partnerkondition ab 120 EUR, fuer Taktkunden."],
           ["Sprachen", "Deutsch, Englisch, Russisch als Dokumentsprache je Endkunde waehlbar."],
           ["Zugang", "Weboberflaeche und Telegram-Bot, beides mit Zwei-Faktor-Anmeldung."],
           ["Betrieb", "Frankfurt, EU. Keine Ausleitung der Kundendaten aus der EU."]],
          [0.22, 0.78])
    _rect(s, 0.62, 5.02, 12.1, 1.44, fill=INDIGO)
    _tb(s, 0.86, 5.14, 11.6, 0.3, "DIE NAECHSTEN DREI SCHRITTE", 12, WHITE, MONO, bold=True)
    bullets(s, 0.86, 5.46, 11.5, [
        "byon nennt drei Bestandskunden und drei Wunschkunden. Wir liefern sechs Assessments, "
        "kostenfrei, im byon-Layout. Aufwand fuer byon: die Namen.",
        "Gemeinsame Sichtung der sechs Unterlagen und Zuordnung der Befunde zum byon-Katalog.",
        "Pilot ueber eine Vertikale, mit 20 Laeufen und gemeinsamem Anschreiben.",
    ], size=10, gap=0.31)

    d.save(out)
    return out


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", default=os.path.join(
        here, "S4biz_Sovereign_Cyber_Cloud_Capability_Brief.pptx"))
    ap.add_argument("--out", default=os.path.join(here, "Cybergod_byon_Partnerpraesentation_DE.pptx"))
    a = ap.parse_args()
    p = build(a.template, a.out)
    print("fertig: %s (%.0f KB)" % (p, os.path.getsize(p) / 1024.0))


if __name__ == "__main__":
    main()
