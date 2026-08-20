#!/usr/bin/env python3
"""build_perseus_shield_deck.py — PERSEUS SHIELD, the active-defence product, as a deep dive.

    python marketing/build_perseus_shield_deck.py [--out PATH] [--template PATH]

Perseus is the figure who beat the Gorgon without ever looking at her directly: he watched the
REFLECTION in a polished shield. That is exactly what this product does. It never trusts what the
client claims about itself (the user agent is attacker-controlled); it judges the reflection - the
paths requested, the misses, the fingerprint spread - and acts on that.

It reuses build_consensus_deck.py's Deck/card/bullets/stat helpers, so the S4biz template exists in
exactly ONE implementation and the decks cannot drift apart. Same reason build_consensus_business_deck
does it.

FOUR RULES THIS DECK OBEYS
--------------------------
1. NO UNSUBSTANTIATED COMPARISON AGAINST A NAMED PRODUCT. We have never benchmarked Perseus against
   Cloudflare, Akamai, Imperva, F5 or anyone else. The comparison slide therefore compares
   CATEGORIES (WAF, DDoS scrubbing, bot management, EDR, SIEM/SOAR) on what each is architecturally
   FOR, which is checkable and cannot be refuted by a competitor's next release. An unsubstantiated
   superiority claim against a named product is comparative advertising under UWG s.6 and the UCP
   Directive. Same rule the consensus decks obey.

2. EVERY NUMBER IS OURS AND MEASURED. 13 classes, 5 honeytokens, 6 tunable bounds, 6 console
   actions, 41 tests, a 42-path corpus - all read out of the code. The 156,511 requests / 2,253
   sources / 604 scanners come from one real analyse_attacks.py run against the live event log, and
   the deck says DETECTED, never "stopped", because the shield shipped after that log was written.
   Overstating this on a security product is self-refuting.

3. WHAT IT DOES NOT DO IS ON A SLIDE. It is HTTP-layer only, it never touches a firewall, it is not
   a WAF and not a DDoS scrubber. A defence product that will not state its own boundary is asking
   the buyer to discover it during an incident.

4. NO EM DASHES ANYWHERE. Standing rule for customer-facing copy.
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_consensus_deck import (  # noqa: E402  - one template implementation, reused
    AMBER, BODY, CYAN, Deck, GREEN, INDIGO, INK, LINE, MONO, MUTED, PANEL, RED, TEXT,
    VIOLET, WHITE, _rect, _tb, bullets, card, stat,
)
from pptx.util import Inches, Pt  # noqa: E402

FOOT = "S4BIZ GROUP · CYBERGOD LLC · PERSEUS SHIELD · INTERNAL SALES + PARTNER MATERIAL"

# Measured, from the code and the live log. Changing a number here means re-reading the source.
N_CLASSES, N_HONEY, N_BOUNDS, N_ACTIONS = 13, 5, 6, 6
N_TESTS, N_CORPUS = 41, 42
LOG_REQ, LOG_SRC, LOG_SCAN = "156,511", "2,253", "604"

# MEASURED ON THIS DECK'S OWN RENDER, not inherited from the consensus deck's comment.
# I set this to 50 by copying that file's note ("49 fits, 53 wraps") and slide 11 shipped a
# 49-character title that wrapped onto the sub-heading anyway. Observed here: 40 fits on one line,
# 49 wraps. Character count is a rough proxy in the first place, because Arial Black glyph widths
# vary a lot (W and M against I and T), so the cap takes the low end of the measured band.
TITLE_MAX = 40


def _check_title(title, tail):
    """A fixed-height title row is arithmetic, not taste.

    The consensus deck shipped a 53-character title that wrapped onto a second line and landed on
    the sub-heading. The cap is set from the RENDER (49 fits, 53 wraps), taking the lower end.
    The HERO title is a list of (text, colour) runs on its own multi-line box, so it is exempt.
    """
    if not isinstance(title, str):
        return
    n = len(title) + len(tail or "")
    assert n <= TITLE_MAX, "title row is %d chars, cap is %d: %r" % (n, TITLE_MAX, title + (tail or ""))


def table(s, x, y, w, cols, rows, widths, head_col=CYAN, size=9.2, rh=0.44):
    """Plain table. Column widths are FRACTIONS of w and must sum to 1."""
    assert abs(sum(widths) - 1.0) < 0.01, "column widths must sum to 1"
    cx = x
    for c, fr in zip(cols, widths):
        _tb(s, cx, y, w * fr - 0.08, 0.28, c.upper(), 8.4, head_col, MONO, True)
        cx += w * fr
    _rect(s, x, y + 0.30, w, 0.012, fill=LINE, line=None)
    yy = y + 0.40
    for r in rows:
        cx = x
        for cell, fr in zip(r, widths):
            txt = cell[0] if isinstance(cell, tuple) else cell
            col = cell[1] if isinstance(cell, tuple) else BODY
            _tb(s, cx, yy, w * fr - 0.08, rh, txt, size, col, TEXT)
            cx += w * fr
        yy += rh
    return yy


# ---------------------------------------------------------------------------------------------
# HOCH-DEUTSCH. Keyed by the ENGLISH SOURCE STRING, so a missing entry degrades to readable English
# instead of printing a key. Harvested with PERSEUS_I18N_AUDIT=1, which prints every string that
# reached a shape without a translation, so "is it complete" is a number rather than an opinion.
#
# NOT TRANSLATED, deliberately: proper nouns and standards identifiers (NIST, OWASP, MITRE ATT&CK,
# CISA, ASVS, OAT-011, T1595.001, GDPR, CJEU, WAF, DDoS, EDR, SIEM, SOAR, ZTNA, Perseus Shield).
# Translating a lookup identifier is how findings silently vanish; translating a standard's name
# makes it unfindable for the auditor who has to look it up.
DE = {
    'PERSEUS SHIELD': 'PERSEUS SHIELD',
    'THE GAP': 'DIE LÜCKE',
    'MECHANISM': 'MECHANIK',
    'PRECISION': 'PRÄZISION',
    'GOVERNANCE': 'GOVERNANCE',
    'THE CONSOLE': 'DIE KONSOLE',
    'FIT': 'EINORDNUNG',
    'CATEGORIES': 'KATEGORIEN',
    'DEPLOYMENT': 'EINFÜHRUNG',
    'EVIDENCE': 'BELEGE',
    'ASSURANCE': 'NACHWEISBARKEIT',
    'NEXT': 'NÄCHSTE SCHRITTE',
    'ACTIVE DEFENCE,': 'AKTIVE VERTEIDIGUNG,',
    'ON YOUR SIDE': 'AUF IHRER SEITE',
    'OF THE WIRE.': 'DER LEITUNG.',
    'An AI-governed HTTP defence layer that watches the reflection, not the claim. It sits in front of what you already run and it never touches your firewall.':
        'Eine KI-gesteuerte Verteidigungsschicht auf HTTP-Ebene, die das Spiegelbild betrachtet und nicht die Behauptung. Sie steht vor dem, was Sie bereits betreiben, und rührt Ihre Firewall nie an.',
    'WHY PERSEUS': 'WARUM PERSEUS',
    'Perseus beat the Gorgon without ever looking at her directly. He watched the reflection in a polished shield. A user agent is attacker-controlled and lies; the paths a client asks for are the reflection, and they cannot be faked without stopping the attack.':
        'Perseus besiegte die Gorgone, ohne sie je direkt anzusehen. Er beobachtete das Spiegelbild in einem polierten Schild. Ein User-Agent wird vom Angreifer kontrolliert und lügt; die Pfade, die ein Client anfordert, sind das Spiegelbild, und sie lassen sich nicht fälschen, ohne den Angriff abzubrechen.',
    'attack classes\nrecognised': 'Angriffsklassen\nerkannt',
    'authorised actions\none tap each': 'autorisierte Aktionen\nje ein Tippen',
    'AI reviewers\nadvisory only': 'KI-Prüfer\nnur beratend',
    'firewall changes\never made': 'Firewall-Änderungen\njemals',
    'NOBODY IS WATCHING': 'NIEMAND BEOBACHTET',
    'THE CLIENT.': 'DEN CLIENT.',
    'Every layer below is real and necessary. None of them answers the question a scanner actually poses.':
        'Jede Schicht unten ist real und notwendig. Keine davon beantwortet die Frage, die ein Scanner tatsächlich stellt.',
    'Layer': 'Schicht',
    'What it judges': 'Worüber sie urteilt',
    'Why a scanner walks past it': 'Warum ein Scanner daran vorbeigeht',
    'Network firewall': 'Netzwerk-Firewall',
    'Ports and addresses': 'Ports und Adressen',
    'Cannot see a URL path. Port 443 is open by design.': 'Sieht keinen URL-Pfad. Port 443 ist bewusst offen.',
    'WAF / rule engine': 'WAF / Regel-Engine',
    'Known payload shapes': 'Bekannte Payload-Muster',
    'Matches signatures per request. Does not model a CLIENT over time.':
        'Prüft Signaturen pro Anfrage. Modelliert keinen CLIENT über die Zeit.',
    'DDoS scrubbing': 'DDoS-Scrubbing',
    'Volume': 'Volumen',
    'A 4-request reconnaissance scan is not volume. It passes cleanly.':
        'Ein Aufklärungsscan mit vier Anfragen ist kein Volumen. Er passiert ungehindert.',
    'EDR': 'EDR',
    'The host, after landing': 'Das System, nach der Landung',
    'Engages once something is already executing on the box.':
        'Greift erst, wenn bereits etwas auf dem System ausgeführt wird.',
    'SIEM / SOAR': 'SIEM / SOAR',
    'Everything, later': 'Alles, später',
    'Correlates after the fact. Median human response is measured in hours.':
        'Korreliert im Nachhinein. Die mittlere menschliche Reaktionszeit misst sich in Stunden.',
    'The gap is BEHAVIOUR OVER TIME from a single client. One request for /.env is noise. Four requests for four different secrets files, from one address, announcing six browsers, is an attack in progress. Nothing in the stack above is built to say that out loud.':
        'Die Lücke ist das VERHALTEN ÜBER DIE ZEIT eines einzelnen Clients. Eine Anfrage nach /.env ist Rauschen. Vier Anfragen nach vier verschiedenen Geheimnisdateien, von einer Adresse, die sechs Browser vorgibt, sind ein laufender Angriff. Nichts im Stack darüber ist dafür gebaut, das auszusprechen.',
    'CODE DECIDES.': 'CODE ENTSCHEIDET.',
    'MODELS ADVISE.': 'MODELLE BERATEN.',
    'The decision on the request path is pure arithmetic. No model call ever sits between a visitor and your site.':
        'Die Entscheidung im Anfragepfad ist reine Arithmetik. Kein Modellaufruf steht jemals zwischen einem Besucher und Ihrer Website.',
    'OBSERVE': 'BEOBACHTEN',
    'Every request is classified against 13 attack-shape patterns: WordPress, PHP probes, .env and .git, admin panels, traversal, SQLi, XSS, shell/RCE, backup files, IoT router paths and more. Classification is regex, not inference.':
        'Jede Anfrage wird gegen 13 Angriffsmuster klassifiziert: WordPress, PHP-Sondierungen, .env und .git, Admin-Oberflächen, Traversal, SQLi, XSS, Shell/RCE, Backup-Dateien, IoT-Router-Pfade und weitere. Die Klassifizierung erfolgt per Regex, nicht per Inferenz.',
    'CORROBORATE': 'ERHÄRTEN',
    'Signals must agree before they convict. Fingerprint rotation proves AUTOMATION, not attack, so it scores only when a second hostile signal is present. Your own uptime checks and CI look exactly like automation.':
        'Signale müssen übereinstimmen, bevor sie verurteilen. Rotierende Fingerabdrücke belegen AUTOMATISIERUNG, keinen Angriff, und zählen daher nur, wenn ein zweites feindliches Signal vorliegt. Ihre eigenen Verfügbarkeitsprüfungen und CI sehen genauso aus.',
    'ACT, TIME-BOXED': 'HANDELN, BEFRISTET',
    'Tarpit first, then a timed HTTP block. Every block expires by itself. Nothing the shield does on its own is permanent, and nothing needs a human to undo it.':
        'Zuerst Tarpit, dann eine befristete HTTP-Sperre. Jede Sperre läuft von selbst ab. Nichts, was der Schild eigenständig tut, ist dauerhaft, und nichts erfordert einen Menschen zum Rückgängigmachen.',
    'ASK, FOR ANYTHING BIGGER': 'RÜCKFRAGE BEI GRÖSSEREM',
    'A 24-hour hold, widening to a /24, an abuse report: those reach a human on Telegram with the evidence attached, and expire unanswered after two hours.':
        'Eine 24-Stunden-Sperre, die Ausweitung auf ein /24, eine Missbrauchsmeldung: Diese erreichen einen Menschen per Telegram samt Beweisen und verfallen unbeantwortet nach zwei Stunden.',
    'A model call is 300 ms to 60 s. In front of a request that IS a denial of service, that is the outage. Perseus reviews out of band, on a timer, and never in the request path.':
        'Ein Modellaufruf dauert 300 ms bis 60 s. Vor einer Anfrage, die selbst ein Denial of Service IST, ist genau das der Ausfall. Perseus prüft zeitgesteuert und außerhalb des Anfragepfads, niemals darin.',
    'THE RAILS ARE': 'DIE LEITPLANKEN',
    'THE PRODUCT.': 'SIND DAS PRODUKT.',
    'Anyone can block traffic. The engineering is in never blocking the wrong person.':
        'Datenverkehr sperren kann jeder. Die Ingenieursleistung besteht darin, nie die falsche Person zu sperren.',
    '5 HONEYTOKENS are the only zero-false-positive signal available. They are listed as Disallow in robots.txt and linked from nowhere, so a request for one is a deliberate scan or a robots-ignoring crawler. Either way it is not a customer.':
        '5 HONEYTOKENS sind das einzige Signal ohne Falschmeldungen. Sie stehen als Disallow in der robots.txt und sind nirgends verlinkt; eine Anfrage darauf ist also ein vorsätzlicher Scan oder ein Crawler, der robots.txt ignoriert. In beiden Fällen ist es kein Kunde.',
    'VARIETY, NOT VOLUME. A real visitor misses the same few stale paths. A scanner misses hundreds of different ones. Misses only score once an address has missed on six or more DISTINCT paths.':
        'VIELFALT, NICHT VOLUMEN. Ein echter Besucher läuft immer in dieselben wenigen veralteten Pfade. Ein Scanner in Hunderte verschiedene. Fehlschläge zählen erst, wenn eine Adresse auf sechs oder mehr UNTERSCHIEDLICHEN Pfaden gescheitert ist.',
    'TWO PATH PREFIXES CAN NEVER BE BLOCKED: /.well-known/ (blocking it turns a scanner into a certificate outage for every domain on the host) and /api/ (authentication is the control there; a 401 is already a refusal).':
        'ZWEI PFAD-PRÄFIXE DÜRFEN NIE GESPERRT WERDEN: /.well-known/ (eine Sperre macht aus einem Scanner einen Zertifikatsausfall für jede Domain auf dem Host) und /api/ (dort ist die Authentifizierung die Kontrolle; ein 401 ist bereits eine Ablehnung).',
    'A BLAST CAP refuses a mass block. Beyond a small absolute allowance, Perseus will not block more than a set share of recent distinct visitors. An automatic control that can cause an outage is worse than no control.':
        'EINE WIRKUNGSGRENZE verweigert Massensperren. Jenseits eines kleinen absoluten Kontingents sperrt Perseus nie mehr als einen festgelegten Anteil der zuletzt gesehenen Besucher. Eine automatische Kontrolle, die einen Ausfall auslösen kann, ist schlechter als keine.',
    'FAILS OPEN, BY DESIGN': 'SCHEITERT BEWUSST DURCHLÄSSIG',
    'Every internal error in the decision path resolves to ALLOW.\n\nA kill switch and an allow-list sit above everything, and neither is tunable by the AI panel.\n\nManual release forgives the history that caused the block, not just the timer. Releasing somebody who is instantly re-blocked is not a release.\n\n41 unit tests and a 42-path mass-scanning corpus run on every deploy. The corpus also asserts that none of our own real routes is ever treated as an attack.':
        'Jeder interne Fehler im Entscheidungspfad endet mit ERLAUBEN.\n\nEin Not-Aus und eine Freigabeliste stehen über allem; beide sind für das KI-Gremium nicht veränderbar.\n\nEine manuelle Freigabe verzeiht die Historie, die zur Sperre führte, nicht nur den Zeitgeber. Wer sofort wieder gesperrt wird, ist nicht freigegeben.\n\n41 Unit-Tests und ein Korpus aus 42 Scan-Pfaden laufen bei jedem Deployment. Der Korpus prüft außerdem, dass keine unserer echten Routen je als Angriff behandelt wird.',
    'FOUR MODELS TUNE IT.': 'VIER JUSTIEREN.',
    'NONE COMMANDS IT.': 'KEINES BEFIEHLT.',
    'The AI reviews what the shield DID and proposes numbers. It cannot block anyone, and it cannot widen its own authority.':
        'Die KI prüft, was der Schild GETAN hat, und schlägt Zahlen vor. Sie kann niemanden sperren und ihre eigenen Befugnisse nicht erweitern.',
    'MAY PROPOSE': 'DARF VORSCHLAGEN',
    'Values for 6 integers only: how many suspicious hits before slowing a client down, before a timed block, the observation window, block duration, delay per request, and the fingerprint-rotation threshold.':
        'Werte für ausschließlich 6 ganze Zahlen: wie viele verdächtige Treffer vor dem Ausbremsen, wie viele vor einer befristeten Sperre, das Beobachtungsfenster, die Sperrdauer, die Verzögerung je Anfrage und der Schwellwert für rotierende Fingerabdrücke.',
    'MUST AGREE': 'MUSS ÜBEREINSTIMMEN',
    'Three of four reviewers must push the same DIRECTION before any number moves, and the value applied is the MEDIAN. One bold model cannot drag the result. Steps over 25 percent are refused outright.':
        'Drei von vier Prüfern müssen dieselbe RICHTUNG vertreten, bevor sich eine Zahl bewegt, und angewendet wird der MEDIAN. Ein einzelnes forsches Modell kann das Ergebnis nicht verschieben. Schritte über 25 Prozent werden grundsätzlich abgelehnt.',
    'CANNOT TOUCH': 'DARF NICHT ANRÜHREN',
    'Blocking or unblocking an address, the bounds themselves, the blast cap, the allow-list, the kill switch, and the never-block path list. Every proposal is clamped to its committed range on READ, so even a corrupted tuning file stays in range.':
        'Adressen sperren oder entsperren, die Grenzwerte selbst, die Wirkungsgrenze, die Freigabeliste, den Not-Aus und die Liste nie zu sperrender Pfade. Jeder Vorschlag wird beim LESEN begrenzt, sodass selbst eine beschädigte Datei im Rahmen bleibt.',
    'FOUR VENDORS, NO SHARED FAILURE DOMAIN': 'VIER ANBIETER, KEINE GEMEINSAME FEHLERDOMÄNE',
    'The panel runs one model each from four independent providers. A rate limit or an outage at any one of them is provider-wide, so a single-vendor panel is four hats on one head. It also means a model that is simply wrong is contradicted by three others rather than believed. The panel is advisory in both directions: it can neither block a good change nor wave through a bad one.':
        'Das Gremium betreibt je ein Modell von vier unabhängigen Anbietern. Eine Drosselung oder ein Ausfall betrifft immer den gesamten Anbieter; ein Gremium aus einer Hand ist daher nur vier Hüte auf einem Kopf. Zudem wird ein schlicht falsches Modell von drei anderen widerlegt statt geglaubt. Das Gremium ist in beide Richtungen beratend: Es kann weder eine gute Änderung blockieren noch eine schlechte durchwinken.',
    'ONE TAP,': 'EIN TIPP,',
    'WITH THE EVIDENCE ATTACHED.': 'MIT DEN BEWEISEN.',
    'Three tiers, decided once. The operator is asked for anything with reach or cost, and never asked for something reversible and cheap.':
        'Drei Stufen, einmal festgelegt. Der Betreiber wird bei allem gefragt, was Reichweite oder Kosten hat, und nie bei etwas Umkehrbarem und Billigem.',
    'Tier': 'Stufe',
    'Actions': 'Aktionen',
    'Why it sits there': 'Warum sie dort steht',
    'AUTO': 'AUTOMATISCH',
    'Tarpit, then a timed HTTP block, then alert': 'Tarpit, dann befristete HTTP-Sperre, dann Alarm',
    'Reversible, time-boxed, expires by itself. Waiting for a human means the scan finishes first.':
        'Umkehrbar, befristet, läuft von selbst ab. Auf einen Menschen zu warten hieße, dass der Scan vorher fertig ist.',
    'ASK': 'RÜCKFRAGE',
    'Hold 24h · Block /24 1h · Report abuse · Strict 1h · Ban path · False alarm':
        '24 h halten · /24 1 h sperren · Missbrauch melden · Streng 1 h · Pfad sperren · Fehlalarm',
    'Longer reach or a real cost. A /24 can be a whole office or a mobile carrier, so the shield may honour that state but never writes it unasked.':
        'Größere Reichweite oder echte Kosten. Ein /24 kann ein ganzes Büro oder ein Mobilfunknetz sein; der Schild darf diesen Zustand befolgen, schreibt ihn aber nie ungefragt.',
    'NEVER': 'NIEMALS',
    'Scanning back, connecting to the host, any form of hack-back':
        'Zurückscannen, Verbindung zum Host, jede Form von Hack-Back',
    'Criminal under StGB 202a/202b/303a/303b and 202c, EU Directive 2013/40, US CFAA 1030, Canada CC 342.1. The address is usually a compromised third party.':
        'Strafbar nach StGB 202a/202b/303a/303b und 202c, EU-Richtlinie 2013/40, US CFAA 1030, Canada CC 342.1. Die Adresse gehört meist einem kompromittierten Dritten.',
    'THE CONFIRMATION IS READ BACK OUT OF LIVE STATE':
        'DIE BESTÄTIGUNG WIRD AUS DEM LIVE-ZUSTAND ZURÜCKGELESEN',
    'After a tap, Perseus re-reads the actual expiry, the actual block-list size and the actual deadline, and reports those. A failed action is reported as NOT APPLIED with the reason. Silence after a tap would be indistinguishable from success, and a console whose statements cannot be trusted is worth nothing during an incident.':
        'Nach einem Tippen liest Perseus den tatsächlichen Ablauf, die tatsächliche Größe der Sperrliste und die tatsächliche Frist erneut aus und meldet diese. Eine fehlgeschlagene Aktion wird als NICHT ANGEWENDET samt Grund gemeldet. Schweigen nach einem Tippen wäre von Erfolg nicht zu unterscheiden, und eine Konsole, deren Aussagen man nicht trauen kann, ist im Ernstfall wertlos.',
    'IT COMPLEMENTS.': 'ES ERGÄNZT.',
    'IT REPLACES NOTHING.': 'ES ERSETZT NICHTS.',
    'Perseus is HTTP-layer only and deliberately narrow. Here is exactly where it sits against what you already own.':
        'Perseus arbeitet ausschließlich auf HTTP-Ebene und ist bewusst eng gefasst. Hier steht genau, wie es sich zu dem verhält, was Sie bereits besitzen.',
    'Existing control': 'Vorhandene Kontrolle',
    'Verdict': 'Urteil',
    'How Perseus relates to it': 'Wie sich Perseus dazu verhält',
    'Network firewall / NGFW': 'Netzwerk-Firewall / NGFW',
    'Keep': 'Behalten',
    'Perseus never touches it. No iptables, no nftables, no ACL, no rule push. Asserted by test.':
        'Perseus rührt sie nie an. Kein iptables, kein nftables, keine ACL, keine Regelübertragung. Per Test abgesichert.',
    'WAF': 'WAF',
    'The WAF judges the PAYLOAD of one request. Perseus judges the CLIENT across many. Different question, both worth asking.':
        'Die WAF beurteilt die NUTZLAST einer Anfrage. Perseus beurteilt den CLIENT über viele hinweg. Zwei verschiedene Fragen, beide lohnen sich.',
    'CDN / DDoS scrubbing': 'CDN / DDoS-Scrubbing',
    'Volume is absorbed upstream. Perseus handles the low-and-slow reconnaissance that is too small to scrub.':
        'Volumen wird vorgelagert abgefangen. Perseus übernimmt die langsame, leise Aufklärung, die zum Scrubbing zu klein ist.',
    'Bot management': 'Bot-Management',
    'Overlaps': 'Überschneidet',
    'Closest neighbour. Perseus adds an authorisation console and an out-of-band AI review of its own decisions.':
        'Der nächste Nachbar. Perseus ergänzt eine Freigabekonsole und eine KI-Prüfung der eigenen Entscheidungen außerhalb des Anfragepfads.',
    'EDR / XDR': 'EDR / XDR',
    'Engages after something lands. Perseus works to stop the landing.':
        'Greift, nachdem etwas gelandet ist. Perseus arbeitet daran, die Landung zu verhindern.',
    'Keep, and feed it': 'Behalten und speisen',
    'Every decision is a structured event. Perseus is a high-quality source, not a competitor.':
        'Jede Entscheidung ist ein strukturiertes Ereignis. Perseus ist eine hochwertige Quelle, kein Konkurrent.',
    'WHAT PERSEUS IS NOT: it is not a WAF, not a DDoS scrubber, not an IPS, and it inspects nothing below HTTP. A defence product that will not state its own boundary is asking the buyer to discover it during an incident.':
        'WAS PERSEUS NICHT IST: keine WAF, kein DDoS-Scrubber, kein IPS, und es prüft nichts unterhalb von HTTP. Ein Verteidigungsprodukt, das seine eigene Grenze nicht nennt, verlangt vom Käufer, sie im Ernstfall selbst zu entdecken.',
    'COMPARED ON': 'VERGLICHEN NACH',
    'ARCHITECTURE, NOT ON CLAIMS.': 'ARCHITEKTUR.',
    'We have benchmarked Perseus against no named product, so this compares what each category is structurally FOR. That is checkable, and a competitor release cannot refute it.':
        'Wir haben Perseus gegen kein namentlich genanntes Produkt gemessen. Verglichen wird daher, wofür jede Kategorie strukturell GEDACHT ist. Das ist überprüfbar, und keine Produktversion eines Wettbewerbers kann es widerlegen.',
    'Dimension': 'Dimension',
    'Unit of judgement': 'Beurteilungseinheit',
    'One request': 'Eine Anfrage',
    'Traffic volume': 'Verkehrsvolumen',
    'A session': 'Eine Sitzung',
    'A CLIENT over time': 'Ein CLIENT über die Zeit',
    'Decision latency': 'Entscheidungslatenz',
    'Inline, ms': 'Inline, ms',
    'Inline, ms (arithmetic)': 'Inline, ms (Arithmetik)',
    'Where it runs': 'Wo es läuft',
    'Edge or host': 'Edge oder Host',
    'Provider edge': 'Anbieter-Edge',
    'Your app, your data': 'Ihre Anwendung, Ihre Daten',
    'Tuning': 'Justierung',
    'Rules, by hand': 'Regeln, von Hand',
    'Provider policy': 'Anbieter-Richtlinie',
    'Vendor model': 'Herstellermodell',
    '4-model quorum, bounded': 'Quorum aus 4 Modellen, begrenzt',
    'Escalation to a human': 'Eskalation an einen Menschen',
    'Ticket': 'Ticket',
    'Console': 'Konsole',
    'One tap, 2h expiry': 'Ein Tippen, 2 h Frist',
    'Data leaves your estate': 'Daten verlassen Ihre Umgebung',
    'Varies': 'Unterschiedlich',
    'Yes': 'Ja',
    'No': 'Nein',
    'THE HONEST READING: the first three columns are mature categories that do their job better than we do ours at volume. Perseus is not competing for that budget. It answers a question none of them is shaped to answer, on infrastructure you already control, and it hands the decision to a named human when the decision has consequences.':
        'DIE EHRLICHE LESART: Die ersten drei Spalten sind ausgereifte Kategorien, die ihre Aufgabe bei hohem Volumen besser erfüllen als wir unsere. Perseus konkurriert nicht um dieses Budget. Es beantwortet eine Frage, für die keine von ihnen gebaut ist, auf Infrastruktur, die Sie bereits kontrollieren, und übergibt die Entscheidung an einen benannten Menschen, sobald sie Folgen hat.',
    'IT GOES IN FRONT': 'ES STEHT VOR DEM,',
    'OF WHAT YOU RUN.': 'WAS SIE BETREIBEN.',
    'Four integration shapes. None of them requires a change to a firewall, a routing change, or a maintenance window on the protected system.':
        'Vier Integrationsformen. Keine davon erfordert eine Firewall-Änderung, eine Routing-Änderung oder ein Wartungsfenster auf dem geschützten System.',
    'REVERSE-PROXY MIDDLEWARE': 'REVERSE-PROXY-MIDDLEWARE',
    'Perseus runs as middleware inside the proxy that already fronts your sites. Real client IP is read from the forwarded header. This is how we run it ourselves, in front of several unrelated domains on one host.':
        'Perseus läuft als Middleware in dem Proxy, der Ihren Seiten bereits vorgelagert ist. Die echte Client-IP wird aus dem Forwarded-Header gelesen. Genau so betreiben wir es selbst, vor mehreren voneinander unabhängigen Domains auf einem Host.',
    'SIDECAR TO A LEGACY APP': 'SIDECAR VOR EINER ALTANWENDUNG',
    'For an application nobody wants to touch, Perseus terminates in front of it and passes traffic through. The legacy app is unmodified and unaware. Nothing is recompiled and no agent is installed on it.':
        'Bei einer Anwendung, die niemand anfassen will, terminiert Perseus davor und reicht den Verkehr durch. Die Altanwendung bleibt unverändert und ahnungslos. Nichts wird neu kompiliert, und es wird kein Agent installiert.',
    'DETECTION-ONLY, ALONGSIDE': 'NUR ERKENNUNG, PARALLEL',
    'Enforcement off, telemetry on. Perseus watches and reports without ever refusing a request. This is the honest way to start: prove the verdicts against your real traffic before anything is enforced.':
        'Durchsetzung aus, Telemetrie an. Perseus beobachtet und berichtet, ohne je eine Anfrage abzulehnen. Das ist der ehrliche Einstieg: die Urteile am echten Verkehr belegen, bevor irgendetwas durchgesetzt wird.',
    'FEED THE CONTROLS YOU HAVE': 'IHRE VORHANDENEN KONTROLLEN SPEISEN',
    'Every decision is a structured event. Export to your SIEM, and hand confirmed hostile addresses to a blocklist your existing edge already consumes. Perseus decides; your estate enforces where you want it to.':
        'Jede Entscheidung ist ein strukturiertes Ereignis. Exportieren Sie es in Ihr SIEM und übergeben Sie bestätigte feindliche Adressen an eine Sperrliste, die Ihre vorhandene Edge bereits nutzt. Perseus entscheidet; Ihre Umgebung setzt dort durch, wo Sie es wollen.',
    'START AT C. A defence you have not watched being wrong is a defence you cannot trust to be right, and detection-only costs nothing to reverse.':
        'BEGINNEN SIE BEI C. Einer Verteidigung, die man nie hat irren sehen, kann man nicht vertrauen, wenn sie recht hat; und der reine Erkennungsbetrieb kostet nichts, wenn man ihn zurücknimmt.',
    'MEASURED ON': 'GEMESSEN AN',
    'OUR OWN FRONT DOOR.': 'UNSERER EIGENEN HAUSTÜR.',
    'One analyse_attacks run against the live event log of cybergod.ai. These are our numbers, from our estate, and they are stated at what they actually prove.':
        'Ein analyse_attacks-Lauf gegen das Live-Ereignisprotokoll von cybergod.ai. Das sind unsere Zahlen, aus unserer Umgebung, und sie stehen genau für das, was sie belegen.',
    'requests\nanalysed': 'Anfragen\nausgewertet',
    'distinct\nsources': 'verschiedene\nQuellen',
    'behaved like\nscanners': 'verhielten sich\nwie Scanner',
    'path corpus\npinned in tests': 'Pfad-Korpus\nin Tests verankert',
    'CLASSES BY DISTINCT SOURCE': 'KLASSEN NACH VERSCHIEDENEN QUELLEN',
    'Class': 'Klasse',
    'Sources': 'Quellen',
    'SAID AT WHAT IT PROVES': 'GESAGT MIT DEM, WAS ES BELEGT',
    'Those 604 sources were DETECTED, not stopped. That log was written BEFORE the shield shipped, and saying otherwise would be an unsupported claim on a security product, which is self-refuting.\n\nThe same measurement found 19 scanning patterns the detector did not yet recognise. They were added, and the corpus is now pinned in the test suite so the gap cannot reopen. That loop, measure the log then close the gap, is the product.':
        'Diese 604 Quellen wurden ERKANNT, nicht gestoppt. Das Protokoll entstand VOR der Auslieferung des Schilds; etwas anderes zu behaupten wäre eine unbelegte Aussage über ein Sicherheitsprodukt und widerlegt sich selbst.\n\nDieselbe Messung fand 19 Scan-Muster, die der Detektor noch nicht kannte. Sie wurden ergänzt, und der Korpus ist nun in der Testsuite verankert, damit sich die Lücke nicht wieder öffnet. Diese Schleife, das Protokoll messen und dann die Lücke schließen, ist das Produkt.',
    'MAPPED TO CONTROLS': 'AUF CONTROLS,',
    'AUDITORS ASK FOR.': 'DIE AUDITOREN PRÜFEN.',
    'Perseus was built against published control language, not against a threat feed.':
        'Perseus wurde gegen veröffentlichte Kontrollsprache gebaut, nicht gegen einen Threat Feed.',
    'Framework': 'Rahmenwerk',
    'Controls Perseus implements or evidences': 'Controls, die Perseus umsetzt oder belegt',
    'NIST SP 800-53r5': 'NIST SP 800-53r5',
    'SI-4 system monitoring · SI-10 input validation · SC-5 denial-of-service protection · AC-7 unsuccessful logon attempts':
        'SI-4 Systemüberwachung · SI-10 Eingabevalidierung · SC-5 Denial-of-Service-Schutz · AC-7 fehlgeschlagene Anmeldeversuche',
    'NIST SP 800-63B': 'NIST SP 800-63B',
    '5.2.2 throttling of authentication attempts': '5.2.2 Drosselung von Authentifizierungsversuchen',
    'OWASP': 'OWASP',
    'ASVS v4 14.6 · Automated Threat Handbook OAT-011 scraping · OAT-014 vulnerability scanning':
        'ASVS v4 14.6 · Automated Threat Handbook OAT-011 Scraping · OAT-014 Schwachstellen-Scanning',
    'MITRE ATT&CK': 'MITRE ATT&CK',
    'T1595.001 scanning IP blocks · T1595.003 wordlist scanning · T1110.001 password guessing':
        'T1595.001 Scannen von IP-Blöcken · T1595.003 Wortlisten-Scanning · T1110.001 Passwortraten',
    'CISA': 'CISA',
    'Bad Practices: default-deny on management surfaces':
        'Bad Practices: Default-Deny auf Verwaltungsoberflächen',
    'AND THE PRIVACY POSITION, BECAUSE IT IS ASKED EVERY TIME':
        'UND DIE DATENSCHUTZPOSITION, WEIL SIE JEDES MAL GEFRAGT WIRD',
    'An IP address is personal data (GDPR; CJEU C-582/14 Breyer). Perseus can be run with source addresses truncated to a /24 or salted-hashed on the way IN, so correlation survives and the identifier does not. Nothing is sent to a third party by default, and the AI review sees aggregate behaviour rather than visitor identities.':
        'Eine IP-Adresse ist ein personenbezogenes Datum (DSGVO; EuGH C-582/14 Breyer). Perseus kann so betrieben werden, dass Quelladressen bereits BEIM EINGANG auf ein /24 gekürzt oder gesalzen gehasht werden; die Korrelation bleibt erhalten, das Identifikationsmerkmal nicht. Standardmäßig wird nichts an Dritte übermittelt, und die KI-Prüfung sieht aggregiertes Verhalten statt Besucheridentitäten.',
    'THIRTY DAYS,': 'DREISSIG TAGE,',
    'ENFORCEMENT OFF.': 'OHNE DURCHSETZUNG.',
    'The only honest way to sell a defence product is to let it be watched being wrong first.':
        'Der einzige ehrliche Weg, ein Verteidigungsprodukt zu verkaufen, ist, es zuerst beim Irren beobachten zu lassen.',
    'WEEK 1': 'WOCHE 1',
    'DEPLOY DETECTION-ONLY': 'NUR ERKENNUNG AUSROLLEN',
    'Middleware or sidecar, enforcement off. No routing change, no firewall change, no maintenance window on the protected system.':
        'Middleware oder Sidecar, Durchsetzung aus. Keine Routing-Änderung, keine Firewall-Änderung, kein Wartungsfenster auf dem geschützten System.',
    'WEEK 2-3': 'WOCHE 2-3',
    'WATCH IT BE WRONG': 'BEIM IRREN ZUSEHEN',
    'Every verdict against your real traffic, with the evidence. Your monitoring, your CI and your partners are exactly the traffic that exposes a bad rule.':
        'Jedes Urteil am echten Verkehr, samt Beweisen. Ihr Monitoring, Ihre CI und Ihre Partner sind genau der Verkehr, der eine schlechte Regel entlarvt.',
    'WEEK 4': 'WOCHE 4',
    'ENFORCE THE CLASSES YOU ACCEPT': 'DIE AKZEPTIERTEN KLASSEN DURCHSETZEN',
    'Turn on enforcement for the classes you agree with, at the thresholds you set. The console and the panel start from your numbers, inside your bounds.':
        'Schalten Sie die Durchsetzung für die Klassen ein, denen Sie zustimmen, mit den Schwellwerten, die Sie festlegen. Konsole und Gremium starten mit Ihren Zahlen, innerhalb Ihrer Grenzen.',
    'ONGOING': 'LAUFEND',
    'THE LOOP': 'DIE SCHLEIFE',
    'Daily digest of what happened, what was unrecognised, and what the panel proposes. Every accepted pattern becomes a test so the gap cannot reopen.':
        'Täglicher Bericht darüber, was geschehen ist, was unerkannt blieb und was das Gremium vorschlägt. Jedes angenommene Muster wird zu einem Test, damit sich die Lücke nicht wieder öffnet.',
    'PERSEUS SHIELD · S4Biz Group · Cybergod LLC · feranicus@s4biz.io · +351 939 994 642':
        'PERSEUS SHIELD · S4Biz Group · Cybergod LLC · feranicus@s4biz.io · +351 939 994 642',
    'wordpress': 'wordpress',
    'php_probe': 'php_probe',
    'admin_panel': 'admin_panel',
    'shell_rce': 'shell_rce',
    'template': 'template',
    'env_secrets': 'env_secrets',
    'backup_file': 'backup_file',
}

RU = {
    'PERSEUS SHIELD': 'PERSEUS SHIELD',
    'THE GAP': 'ПРОБЕЛ',
    'MECHANISM': 'МЕХАНИКА',
    'PRECISION': 'ТОЧНОСТЬ',
    'GOVERNANCE': 'УПРАВЛЕНИЕ',
    'THE CONSOLE': 'КОНСОЛЬ',
    'FIT': 'МЕСТО В СТЕКЕ',
    'CATEGORIES': 'КАТЕГОРИИ',
    'DEPLOYMENT': 'ВНЕДРЕНИЕ',
    'EVIDENCE': 'ДОКАЗАТЕЛЬСТВА',
    'ASSURANCE': 'ПОДТВЕРЖДАЕМОСТЬ',
    'NEXT': 'ДАЛЬШЕ',
    'ACTIVE DEFENCE,': 'АКТИВНАЯ ЗАЩИТА,',
    'ON YOUR SIDE': 'НА ВАШЕЙ СТОРОНЕ',
    'OF THE WIRE.': 'ПРОВОДА.',
    'An AI-governed HTTP defence layer that watches the reflection, not the claim. It sits in front of what you already run and it never touches your firewall.':
        'Слой защиты на уровне HTTP под управлением ИИ, который смотрит на отражение, а не на заявление. Он встаёт перед тем, что у вас уже работает, и никогда не трогает ваш межсетевой экран.',
    'WHY PERSEUS': 'ПОЧЕМУ ПЕРСЕЙ',
    'Perseus beat the Gorgon without ever looking at her directly. He watched the reflection in a polished shield. A user agent is attacker-controlled and lies; the paths a client asks for are the reflection, and they cannot be faked without stopping the attack.':
        'Персей победил горгону, ни разу не взглянув на неё прямо. Он смотрел на отражение в начищенном щите. User-Agent подконтролен атакующему и лжёт; пути, которые запрашивает клиент, и есть отражение, и подделать их нельзя, не прекратив саму атаку.',
    'attack classes\nrecognised': 'классов атак\nраспознаётся',
    'authorised actions\none tap each': 'санкционированных действий\nпо одному нажатию',
    'AI reviewers\nadvisory only': 'ИИ-рецензента\nтолько совещательно',
    'firewall changes\never made': 'изменений межсетевого экрана\nза всё время',
    'NOBODY IS WATCHING': 'НИКТО НЕ СМОТРИТ',
    'THE CLIENT.': 'НА КЛИЕНТА.',
    'Every layer below is real and necessary. None of them answers the question a scanner actually poses.':
        'Каждый слой ниже реален и необходим. Ни один из них не отвечает на вопрос, который на самом деле задаёт сканер.',
    'Layer': 'Слой',
    'What it judges': 'О чём судит',
    'Why a scanner walks past it': 'Почему сканер проходит мимо',
    'Network firewall': 'Сетевой межсетевой экран',
    'Ports and addresses': 'Порты и адреса',
    'Cannot see a URL path. Port 443 is open by design.': 'Не видит путь URL. Порт 443 открыт по замыслу.',
    'WAF / rule engine': 'WAF / движок правил',
    'Known payload shapes': 'Известныеформы полезной нагрузки',
    'Matches signatures per request. Does not model a CLIENT over time.':
        'Сверяет сигнатуры по каждому запросу. Не моделирует КЛИЕНТА во времени.',
    'DDoS scrubbing': 'Очистка от DDoS',
    'Volume': 'Объём',
    'A 4-request reconnaissance scan is not volume. It passes cleanly.':
        'Разведка из четырёх запросов — это не объём. Она проходит беспрепятственно.',
    'EDR': 'EDR',
    'The host, after landing': 'Узел, после высадки',
    'Engages once something is already executing on the box.':
        'Включается, когда что-то уже выполняется на машине.',
    'SIEM / SOAR': 'SIEM / SOAR',
    'Everything, later': 'Всё, но позже',
    'Correlates after the fact. Median human response is measured in hours.':
        'Коррелирует постфактум. Медианное время реакции человека измеряется часами.',
    'The gap is BEHAVIOUR OVER TIME from a single client. One request for /.env is noise. Four requests for four different secrets files, from one address, announcing six browsers, is an attack in progress. Nothing in the stack above is built to say that out loud.':
        'Пробел — это ПОВЕДЕНИЕ ВО ВРЕМЕНИ одного клиента. Один запрос к /.env — шум. Четыре запроса к четырём разным файлам с секретами, с одного адреса, объявляющего шесть браузеров, — это идущая атака. Ничто в стеке выше не создано, чтобы сказать это вслух.',
    'CODE DECIDES.': 'РЕШАЕТ КОД.',
    'MODELS ADVISE.': 'МОДЕЛИ СОВЕТУЮТ.',
    'The decision on the request path is pure arithmetic. No model call ever sits between a visitor and your site.':
        'Решение на пути запроса — чистая арифметика. Ни один вызов модели никогда не стоит между посетителем и вашим сайтом.',
    'OBSERVE': 'НАБЛЮДАТЬ',
    'Every request is classified against 13 attack-shape patterns: WordPress, PHP probes, .env and .git, admin panels, traversal, SQLi, XSS, shell/RCE, backup files, IoT router paths and more. Classification is regex, not inference.':
        'Каждый запрос классифицируется по 13 шаблонам атак: WordPress, PHP-зондирование, .env и .git, админ-панели, обход каталогов, SQLi, XSS, shell/RCE, файлы резервных копий, пути IoT-маршрутизаторов и другие. Классификация — регулярные выражения, не вывод модели.',
    'CORROBORATE': 'ПОДТВЕРЖДАТЬ',
    'Signals must agree before they convict. Fingerprint rotation proves AUTOMATION, not attack, so it scores only when a second hostile signal is present. Your own uptime checks and CI look exactly like automation.':
        'Сигналы должны совпасть, прежде чем выносить приговор. Смена отпечатков доказывает АВТОМАТИЗАЦИЮ, а не атаку, поэтому она засчитывается только при втором враждебном сигнале. Ваши собственные проверки доступности и CI выглядят точно так же.',
    'ACT, TIME-BOXED': 'ДЕЙСТВОВАТЬ, НА СРОК',
    'Tarpit first, then a timed HTTP block. Every block expires by itself. Nothing the shield does on its own is permanent, and nothing needs a human to undo it.':
        'Сначала замедление, затем временная блокировка на уровне HTTP. Любая блокировка истекает сама. Ничто из того, что щит делает самостоятельно, не является постоянным, и ничто не требует человека для отмены.',
    'ASK, FOR ANYTHING BIGGER': 'СПРОСИТЬ О БОЛЬШЕМ',
    'A 24-hour hold, widening to a /24, an abuse report: those reach a human on Telegram with the evidence attached, and expire unanswered after two hours.':
        'Удержание на 24 часа, расширение до /24, жалоба на злоупотребление: всё это уходит человеку в Telegram вместе с доказательствами и без ответа истекает через два часа.',
    'A model call is 300 ms to 60 s. In front of a request that IS a denial of service, that is the outage. Perseus reviews out of band, on a timer, and never in the request path.':
        'Вызов модели занимает от 300 мс до 60 с. Перед запросом, который САМ ЯВЛЯЕТСЯ отказом в обслуживании, это и есть простой. Персей проверяет вне основного потока, по таймеру, и никогда на пути запроса.',
    'THE RAILS ARE': 'ОГРАНИЧИТЕЛИ',
    'THE PRODUCT.': 'И ЕСТЬ ПРОДУКТ.',
    'Anyone can block traffic. The engineering is in never blocking the wrong person.':
        'Блокировать трафик умеет каждый. Инженерия — в том, чтобы никогда не заблокировать не того.',
    '5 HONEYTOKENS are the only zero-false-positive signal available. They are listed as Disallow in robots.txt and linked from nowhere, so a request for one is a deliberate scan or a robots-ignoring crawler. Either way it is not a customer.':
        '5 ПРИМАНОК — единственный сигнал без ложных срабатываний. Они указаны как Disallow в robots.txt и ниоткуда не связаны ссылками, поэтому запрос к ним — это либо намеренное сканирование, либо краулер, игнорирующий robots.txt. В обоих случаях это не клиент.',
    'VARIETY, NOT VOLUME. A real visitor misses the same few stale paths. A scanner misses hundreds of different ones. Misses only score once an address has missed on six or more DISTINCT paths.':
        'РАЗНООБРАЗИЕ, А НЕ ОБЪЁМ. Настоящий посетитель промахивается по одним и тем же устаревшим путям. Сканер — по сотням разных. Промахи засчитываются только после шести и более РАЗЛИЧНЫХ путей с одного адреса.',
    'TWO PATH PREFIXES CAN NEVER BE BLOCKED: /.well-known/ (blocking it turns a scanner into a certificate outage for every domain on the host) and /api/ (authentication is the control there; a 401 is already a refusal).':
        'ДВА ПРЕФИКСА ПУТИ НЕЛЬЗЯ БЛОКИРОВАТЬ НИКОГДА: /.well-known/ (блокировка превращает сканер в отказ сертификатов для каждого домена на узле) и /api/ (там контролем является аутентификация; ответ 401 — это уже отказ).',
    'A BLAST CAP refuses a mass block. Beyond a small absolute allowance, Perseus will not block more than a set share of recent distinct visitors. An automatic control that can cause an outage is worse than no control.':
        'ПРЕДЕЛ ПОРАЖЕНИЯ запрещает массовую блокировку. Сверх небольшого абсолютного лимита Персей не заблокирует больше заданной доли недавних уникальных посетителей. Автоматический контроль, способный вызвать простой, хуже его отсутствия.',
    'FAILS OPEN, BY DESIGN': 'ОТКАЗЫВАЕТ В СТОРОНУ РАЗРЕШЕНИЯ',
    'Every internal error in the decision path resolves to ALLOW.\n\nA kill switch and an allow-list sit above everything, and neither is tunable by the AI panel.\n\nManual release forgives the history that caused the block, not just the timer. Releasing somebody who is instantly re-blocked is not a release.\n\n41 unit tests and a 42-path mass-scanning corpus run on every deploy. The corpus also asserts that none of our own real routes is ever treated as an attack.':
        'Любая внутренняя ошибка на пути решения завершается РАЗРЕШИТЬ.\n\nАварийный выключатель и белый список стоят надо всем, и ни то ни другое не настраивается ИИ-коллегией.\n\nРучное снятие прощает историю, вызвавшую блокировку, а не только таймер. Снять того, кого тут же заблокируют снова, — это не снятие.\n\n41 модульный тест и корпус из 42 путей массового сканирования запускаются при каждом развёртывании. Корпус также проверяет, что ни один наш реальный маршрут никогда не считается атакой.',
    'FOUR MODELS TUNE IT.': 'ЧЕТВЕРО НАСТРАИВАЮТ.',
    'NONE COMMANDS IT.': 'НИКТО НЕ ВЕЛИТ.',
    'The AI reviews what the shield DID and proposes numbers. It cannot block anyone, and it cannot widen its own authority.':
        'ИИ разбирает то, что щит СДЕЛАЛ, и предлагает числа. Он не может никого заблокировать и не может расширить собственные полномочия.',
    'MAY PROPOSE': 'МОЖЕТ ПРЕДЛАГАТЬ',
    'Values for 6 integers only: how many suspicious hits before slowing a client down, before a timed block, the observation window, block duration, delay per request, and the fingerprint-rotation threshold.':
        'Значения только для 6 целых чисел: сколько подозрительных попаданий до замедления клиента, сколько до временной блокировки, окно наблюдения, длительность блокировки, задержка на запрос и порог смены отпечатков.',
    'MUST AGREE': 'ДОЛЖНЫ СОГЛАСИТЬСЯ',
    'Three of four reviewers must push the same DIRECTION before any number moves, and the value applied is the MEDIAN. One bold model cannot drag the result. Steps over 25 percent are refused outright.':
        'Трое из четырёх рецензентов должны предлагать одно и то же НАПРАВЛЕНИЕ, прежде чем число сдвинется, а применяется МЕДИАНА. Одна смелая модель не утянет результат. Шаги свыше 25 процентов отклоняются сразу.',
    'CANNOT TOUCH': 'НЕ МОЖЕТ ТРОГАТЬ',
    'Blocking or unblocking an address, the bounds themselves, the blast cap, the allow-list, the kill switch, and the never-block path list. Every proposal is clamped to its committed range on READ, so even a corrupted tuning file stays in range.':
        'Блокировку или разблокировку адреса, границы, предел поражения, белый список, аварийный выключатель и список неблокируемых путей. Каждое предложение ограничивается ПРИ ЧТЕНИИ, поэтому даже испорченный файл настроек остаётся в рамках.',
    'FOUR VENDORS, NO SHARED FAILURE DOMAIN': 'ЧЕТЫРЕ ПОСТАВЩИКА, НЕТ ОБЩЕЙ ЗОНЫ ОТКАЗА',
    'The panel runs one model each from four independent providers. A rate limit or an outage at any one of them is provider-wide, so a single-vendor panel is four hats on one head. It also means a model that is simply wrong is contradicted by three others rather than believed. The panel is advisory in both directions: it can neither block a good change nor wave through a bad one.':
        'Коллегия использует по одной модели от четырёх независимых поставщиков. Ограничение скорости или сбой у любого из них охватывает всего поставщика, поэтому коллегия от одного вендора — это четыре шляпы на одной голове. Кроме того, просто ошибающейся модели возражают три остальные, а не верят ей. Коллегия совещательна в обе стороны: она не может ни заблокировать хорошее изменение, ни пропустить плохое.',
    'ONE TAP,': 'ОДНО НАЖАТИЕ,',
    'WITH THE EVIDENCE ATTACHED.': 'С ДОКАЗАТЕЛЬСТВАМИ.',
    'Three tiers, decided once. The operator is asked for anything with reach or cost, and never asked for something reversible and cheap.':
        'Три уровня, определённые один раз. Оператора спрашивают обо всём, что имеет охват или цену, и никогда — об обратимом и дешёвом.',
    'Tier': 'Уровень',
    'Actions': 'Действия',
    'Why it sits there': 'Почему он здесь',
    'AUTO': 'АВТО',
    'Tarpit, then a timed HTTP block, then alert':
        'Замедление, затем временная HTTP-блокировка, затем оповещение',
    'Reversible, time-boxed, expires by itself. Waiting for a human means the scan finishes first.':
        'Обратимо, ограничено по времени, истекает само. Ждать человека — значит дать сканированию закончиться первым.',
    'ASK': 'СПРОСИТЬ',
    'Hold 24h · Block /24 1h · Report abuse · Strict 1h · Ban path · False alarm':
        'Удержать 24 ч · Блок /24 на 1 ч · Жалоба · Строгий режим 1 ч · Запрет пути · Ложная тревога',
    'Longer reach or a real cost. A /24 can be a whole office or a mobile carrier, so the shield may honour that state but never writes it unasked.':
        'Больший охват или реальная цена. /24 может быть целым офисом или мобильным оператором, поэтому щит вправе соблюдать это состояние, но никогда не записывает его без спроса.',
    'NEVER': 'НИКОГДА',
    'Scanning back, connecting to the host, any form of hack-back':
        'Ответное сканирование, подключение к узлу, любая форма обратного взлома',
    'Criminal under StGB 202a/202b/303a/303b and 202c, EU Directive 2013/40, US CFAA 1030, Canada CC 342.1. The address is usually a compromised third party.':
        'Уголовно наказуемо по StGB 202a/202b/303a/303b и 202c, Директиве ЕС 2013/40, US CFAA 1030, УК Канады 342.1. Адрес обычно принадлежит скомпрометированной третьей стороне.',
    'THE CONFIRMATION IS READ BACK OUT OF LIVE STATE': 'ПОДТВЕРЖДЕНИЕ СЧИТЫВАЕТСЯ ИЗ ЖИВОГО СОСТОЯНИЯ',
    'After a tap, Perseus re-reads the actual expiry, the actual block-list size and the actual deadline, and reports those. A failed action is reported as NOT APPLIED with the reason. Silence after a tap would be indistinguishable from success, and a console whose statements cannot be trusted is worth nothing during an incident.':
        'После нажатия Персей заново считывает фактический срок истечения, фактический размер списка блокировок и фактический дедлайн и сообщает именно их. Неудавшееся действие сообщается как НЕ ПРИМЕНЕНО с указанием причины. Молчание после нажатия было бы неотличимо от успеха, а консоль, утверждениям которой нельзя доверять, во время инцидента ничего не стоит.',
    'IT COMPLEMENTS.': 'ОНО ДОПОЛНЯЕТ.',
    'IT REPLACES NOTHING.': 'НИЧЕГО НЕ ЗАМЕНЯЕТ.',
    'Perseus is HTTP-layer only and deliberately narrow. Here is exactly where it sits against what you already own.':
        'Персей работает только на уровне HTTP и намеренно узок. Вот точно, как он соотносится с тем, что у вас уже есть.',
    'Existing control': 'Имеющийся контроль',
    'Verdict': 'Вердикт',
    'How Perseus relates to it': 'Как с ним соотносится Персей',
    'Network firewall / NGFW': 'Сетевой экран / NGFW',
    'Keep': 'Оставить',
    'Perseus never touches it. No iptables, no nftables, no ACL, no rule push. Asserted by test.':
        'Персей его не трогает. Ни iptables, ни nftables, ни ACL, ни выгрузки правил. Проверено тестом.',
    'WAF': 'WAF',
    'The WAF judges the PAYLOAD of one request. Perseus judges the CLIENT across many. Different question, both worth asking.':
        'WAF судит о ПОЛЕЗНОЙ НАГРУЗКЕ одного запроса. Персей судит о КЛИЕНТЕ по многим. Разные вопросы, оба стоит задавать.',
    'CDN / DDoS scrubbing': 'CDN / очистка от DDoS',
    'Volume is absorbed upstream. Perseus handles the low-and-slow reconnaissance that is too small to scrub.':
        'Объём поглощается выше по потоку. Персей берёт на себя медленную тихую разведку, слишком малую для очистки.',
    'Bot management': 'Управление ботами',
    'Overlaps': 'Пересекается',
    'Closest neighbour. Perseus adds an authorisation console and an out-of-band AI review of its own decisions.':
        'Ближайший сосед. Персей добавляет консоль санкционирования и ИИ-разбор собственных решений вне основного потока.',
    'EDR / XDR': 'EDR / XDR',
    'Engages after something lands. Perseus works to stop the landing.':
        'Включается после того, как что-то приземлилось. Персей работает над тем, чтобы посадки не произошло.',
    'Keep, and feed it': 'Оставить и питать',
    'Every decision is a structured event. Perseus is a high-quality source, not a competitor.':
        'Каждое решение — структурированное событие. Персей это качественный источник, а не конкурент.',
    'WHAT PERSEUS IS NOT: it is not a WAF, not a DDoS scrubber, not an IPS, and it inspects nothing below HTTP. A defence product that will not state its own boundary is asking the buyer to discover it during an incident.':
        'ЧЕМ ПЕРСЕЙ НЕ ЯВЛЯЕТСЯ: это не WAF, не средство очистки от DDoS, не IPS, и он не инспектирует ничего ниже HTTP. Защитный продукт, который не называет собственную границу, предлагает покупателю выяснить её во время инцидента.',
    'COMPARED ON': 'СРАВНЕНИЕ ПО',
    'ARCHITECTURE, NOT ON CLAIMS.': 'АРХИТЕКТУРЕ.',
    'We have benchmarked Perseus against no named product, so this compares what each category is structurally FOR. That is checkable, and a competitor release cannot refute it.':
        'Мы не сравнивали Персей ни с одним названным продуктом, поэтому здесь сопоставляется то, ДЛЯ ЧЕГО структурно предназначена каждая категория. Это проверяемо, и выпуск продукта конкурента не может это опровергнуть.',
    'Dimension': 'Измерение',
    'Unit of judgement': 'Единица суждения',
    'One request': 'Один запрос',
    'Traffic volume': 'Объём трафика',
    'A session': 'Сессия',
    'A CLIENT over time': 'КЛИЕНТ во времени',
    'Decision latency': 'Задержка решения',
    'Inline, ms': 'В потоке, мс',
    'Inline, ms (arithmetic)': 'В потоке, мс (арифметика)',
    'Where it runs': 'Где работает',
    'Edge or host': 'Периметр или узел',
    'Provider edge': 'Периметр провайдера',
    'Your app, your data': 'Ваше приложение, ваши данные',
    'Tuning': 'Настройка',
    'Rules, by hand': 'Правила, вручную',
    'Provider policy': 'Политика провайдера',
    'Vendor model': 'Модель вендора',
    '4-model quorum, bounded': 'Кворум из 4 моделей, в границах',
    'Escalation to a human': 'Эскалация человеку',
    'Ticket': 'Заявка',
    'Console': 'Консоль',
    'One tap, 2h expiry': 'Одно нажатие, срок 2 ч',
    'Data leaves your estate': 'Данные покидают ваш контур',
    'Varies': 'По-разному',
    'Yes': 'Да',
    'No': 'Нет',
    'THE HONEST READING: the first three columns are mature categories that do their job better than we do ours at volume. Perseus is not competing for that budget. It answers a question none of them is shaped to answer, on infrastructure you already control, and it hands the decision to a named human when the decision has consequences.':
        'ЧЕСТНОЕ ПРОЧТЕНИЕ: первые три столбца — зрелые категории, которые на больших объёмах делают свою работу лучше, чем мы свою. Персей не претендует на этот бюджет. Он отвечает на вопрос, для которого ни одна из них не создана, на инфраструктуре, которую вы уже контролируете, и передаёт решение поимённо названному человеку, когда у решения есть последствия.',
    'IT GOES IN FRONT': 'ОНО ВСТАЁТ ПЕРЕД ТЕМ,',
    'OF WHAT YOU RUN.': 'ЧТО У ВАС ЕСТЬ.',
    'Four integration shapes. None of them requires a change to a firewall, a routing change, or a maintenance window on the protected system.':
        'Четыре формы интеграции. Ни одна не требует изменения межсетевого экрана, изменения маршрутизации или окна обслуживания на защищаемой системе.',
    'REVERSE-PROXY MIDDLEWARE': 'СЛОЙ В ОБРАТНОМ ПРОКСИ',
    'Perseus runs as middleware inside the proxy that already fronts your sites. Real client IP is read from the forwarded header. This is how we run it ourselves, in front of several unrelated domains on one host.':
        'Персей работает как промежуточный слой внутри прокси, который уже стоит перед вашими сайтами. Реальный IP клиента читается из заголовка пересылки. Именно так мы запускаем его сами, перед несколькими не связанными доменами на одном узле.',
    'SIDECAR TO A LEGACY APP': 'SIDECAR ПЕРЕД LEGACY-ПРИЛОЖЕНИЕМ',
    'For an application nobody wants to touch, Perseus terminates in front of it and passes traffic through. The legacy app is unmodified and unaware. Nothing is recompiled and no agent is installed on it.':
        'Для приложения, которое никто не хочет трогать, Персей терминирует перед ним и пропускает трафик насквозь. Унаследованное приложение не изменяется и ничего не знает. Ничего не перекомпилируется, и агент на него не ставится.',
    'DETECTION-ONLY, ALONGSIDE': 'ТОЛЬКО ОБНАРУЖЕНИЕ, ПАРАЛЛЕЛЬНО',
    'Enforcement off, telemetry on. Perseus watches and reports without ever refusing a request. This is the honest way to start: prove the verdicts against your real traffic before anything is enforced.':
        'Блокировки выключены, телеметрия включена. Персей наблюдает и сообщает, ни разу не отклоняя запрос. Это честный способ начать: доказать вердикты на вашем реальном трафике прежде, чем что-либо начнёт применяться.',
    'FEED THE CONTROLS YOU HAVE': 'ПИТАТЬ ИМЕЮЩИЕСЯ СРЕДСТВА',
    'Every decision is a structured event. Export to your SIEM, and hand confirmed hostile addresses to a blocklist your existing edge already consumes. Perseus decides; your estate enforces where you want it to.':
        'Каждое решение — структурированное событие. Выгружайте его в свой SIEM и передавайте подтверждённые враждебные адреса в список блокировок, который уже использует ваш периметр. Персей решает; ваша инфраструктура применяет там, где вы захотите.',
    'START AT C. A defence you have not watched being wrong is a defence you cannot trust to be right, and detection-only costs nothing to reverse.':
        'НАЧНИТЕ С ВАРИАНТА C. Защите, которую вы не видели ошибающейся, нельзя доверять; откат режима обнаружения ничего не стоит.',
    'MEASURED ON': 'ИЗМЕРЕНО НА',
    'OUR OWN FRONT DOOR.': 'СОБСТВЕННОМ ПОРОГЕ.',
    'One analyse_attacks run against the live event log of cybergod.ai. These are our numbers, from our estate, and they are stated at what they actually prove.':
        'Один запуск analyse_attacks по живому журналу событий cybergod.ai. Это наши числа, из нашей инфраструктуры, и они заявлены ровно в том объёме, который доказывают.',
    'requests\nanalysed': 'запросов\nпроанализировано',
    'distinct\nsources': 'уникальных\nисточников',
    'behaved like\nscanners': 'вели себя\nкак сканеры',
    'path corpus\npinned in tests': 'корпус путей\nзакреплён в тестах',
    'CLASSES BY DISTINCT SOURCE': 'КЛАССЫ ПО УНИКАЛЬНЫМ ИСТОЧНИКАМ',
    'Class': 'Класс',
    'Sources': 'Источники',
    'SAID AT WHAT IT PROVES': 'СКАЗАНО РОВНО ТО, ЧТО ДОКАЗАНО',
    'Those 604 sources were DETECTED, not stopped. That log was written BEFORE the shield shipped, and saying otherwise would be an unsupported claim on a security product, which is self-refuting.\n\nThe same measurement found 19 scanning patterns the detector did not yet recognise. They were added, and the corpus is now pinned in the test suite so the gap cannot reopen. That loop, measure the log then close the gap, is the product.':
        'Эти 604 источника были ОБНАРУЖЕНЫ, а не остановлены. Журнал был записан ДО выпуска щита, и утверждать иное значило бы сделать неподкреплённое заявление о продукте безопасности, что опровергает само себя.\n\nТо же измерение выявило 19 шаблонов сканирования, которые детектор ещё не распознавал. Их добавили, и корпус теперь закреплён в наборе тестов, чтобы пробел не открылся снова. Этот цикл — измерить журнал, затем закрыть пробел — и есть продукт.',
    'MAPPED TO CONTROLS': 'КОНТРОЛИ,',
    'AUDITORS ASK FOR.': 'КОТОРЫЕ СПРОСИТ АУДИТОР.',
    'Perseus was built against published control language, not against a threat feed.':
        'Персей построен по опубликованному языку контролей, а не по ленте угроз.',
    'Framework': 'Стандарт',
    'Controls Perseus implements or evidences': 'Контроли, которые Персей реализует или подтверждает',
    'NIST SP 800-53r5': 'NIST SP 800-53r5',
    'SI-4 system monitoring · SI-10 input validation · SC-5 denial-of-service protection · AC-7 unsuccessful logon attempts':
        'SI-4 мониторинг системы · SI-10 проверка ввода · SC-5 защита от отказа в обслуживании · AC-7 неудачные попытки входа',
    'NIST SP 800-63B': 'NIST SP 800-63B',
    '5.2.2 throttling of authentication attempts': '5.2.2 ограничение попыток аутентификации',
    'OWASP': 'OWASP',
    'ASVS v4 14.6 · Automated Threat Handbook OAT-011 scraping · OAT-014 vulnerability scanning':
        'ASVS v4 14.6 · Automated Threat Handbook OAT-011 скрейпинг · OAT-014 сканирование уязвимостей',
    'MITRE ATT&CK': 'MITRE ATT&CK',
    'T1595.001 scanning IP blocks · T1595.003 wordlist scanning · T1110.001 password guessing':
        'T1595.001 сканирование IP-блоков · T1595.003 сканирование по словарю · T1110.001 подбор паролей',
    'CISA': 'CISA',
    'Bad Practices: default-deny on management surfaces':
        'Bad Practices: запрет по умолчанию на интерфейсах управления',
    'AND THE PRIVACY POSITION, BECAUSE IT IS ASKED EVERY TIME':
        'И ПОЗИЦИЯ ПО ПЕРСОНАЛЬНЫМ ДАННЫМ, ПОТОМУ ЧТО ОБ ЭТОМ СПРАШИВАЮТ ВСЕГДА',
    'An IP address is personal data (GDPR; CJEU C-582/14 Breyer). Perseus can be run with source addresses truncated to a /24 or salted-hashed on the way IN, so correlation survives and the identifier does not. Nothing is sent to a third party by default, and the AI review sees aggregate behaviour rather than visitor identities.':
        'IP-адрес является персональными данными (GDPR; Суд ЕС C-582/14 Breyer). Персей можно запускать так, что адреса источников усекаются до /24 или хешируются с солью УЖЕ НА ВХОДЕ: корреляция сохраняется, а идентификатор нет. По умолчанию ничего не передаётся третьим сторонам, и ИИ-разбор видит агрегированное поведение, а не личности посетителей.',
    'THIRTY DAYS,': 'ТРИДЦАТЬ ДНЕЙ',
    'ENFORCEMENT OFF.': 'БЕЗ БЛОКИРОВОК.',
    'The only honest way to sell a defence product is to let it be watched being wrong first.':
        'Единственный честный способ продать защитный продукт — сначала дать посмотреть, как он ошибается.',
    'WEEK 1': 'НЕДЕЛЯ 1',
    'DEPLOY DETECTION-ONLY': 'РАЗВЕРНУТЬ ТОЛЬКО ОБНАРУЖЕНИЕ',
    'Middleware or sidecar, enforcement off. No routing change, no firewall change, no maintenance window on the protected system.':
        'Промежуточный слой или sidecar, блокировки выключены. Без изменения маршрутизации, без изменения межсетевого экрана, без окна обслуживания на защищаемой системе.',
    'WEEK 2-3': 'НЕДЕЛИ 2-3',
    'WATCH IT BE WRONG': 'СМОТРЕТЬ, КАК ОН ОШИБАЕТСЯ',
    'Every verdict against your real traffic, with the evidence. Your monitoring, your CI and your partners are exactly the traffic that exposes a bad rule.':
        'Каждый вердикт на вашем реальном трафике, с доказательствами. Ваш мониторинг, ваш CI и ваши партнёры — это ровно тот трафик, который вскрывает плохое правило.',
    'WEEK 4': 'НЕДЕЛЯ 4',
    'ENFORCE THE CLASSES YOU ACCEPT': 'ВКЛЮЧИТЬ ПРИНЯТЫЕ КЛАССЫ',
    'Turn on enforcement for the classes you agree with, at the thresholds you set. The console and the panel start from your numbers, inside your bounds.':
        'Включите блокировки для тех классов, с которыми согласны, на порогах, которые задали вы. Консоль и коллегия стартуют с ваших чисел, внутри ваших границ.',
    'ONGOING': 'ПОСТОЯННО',
    'THE LOOP': 'ЦИКЛ',
    'Daily digest of what happened, what was unrecognised, and what the panel proposes. Every accepted pattern becomes a test so the gap cannot reopen.':
        'Ежедневная сводка о том, что произошло, что осталось нераспознанным и что предлагает коллегия. Каждый принятый шаблон становится тестом, чтобы пробел не открылся снова.',
    'PERSEUS SHIELD · S4Biz Group · Cybergod LLC · feranicus@s4biz.io · +351 939 994 642':
        'PERSEUS SHIELD · S4Biz Group · Cybergod LLC · feranicus@s4biz.io · +351 939 994 642',
    'wordpress': 'wordpress',
    'php_probe': 'php_probe',
    'admin_panel': 'admin_panel',
    'shell_rce': 'shell_rce',
    'template': 'template',
    'env_secrets': 'env_secrets',
    'backup_file': 'backup_file',
}

# One registry. Adding a language is a pack plus nothing else: the CLI, the audit and the
# output filename all derive from these keys, so half a language cannot be advertised.
PACKS = {"de": DE, "ru": RU}

# The wrappers inside build() rebind the local names `_tb`, `card`, ... to themselves, which makes
# those names LOCAL to build() for the whole function. A wrapper body written as `return _tb(...)`
# would therefore resolve to the wrapper and recurse forever. Capture the originals here, at module
# scope, so the wrappers call something that can never be rebound.
_TB, _CARD, _BULLETS, _STAT, _TABLE = _tb, card, bullets, stat, table


def build(template, out, lang="en"):
    # ---- i18n AT THE RENDER BOUNDARY, not by hoisting strings ---------------------------------
    # Same doctrine as scripts/i18n/deck_i18n.js: the layout code is written once in English and the
    # translation is applied where text enters a shape. A translator therefore cannot move a box,
    # drop a card or reorder a table, because none of those things are in the dictionary they edit.
    # Unknown strings FALL THROUGH to English rather than crashing or printing a key, so a partial
    # dictionary degrades to readable English (the i18n.jsx fallback rule).
    # PADDING: look the string up TRIMMED and re-attach the caller's own whitespace. A trailing
    # space in the source ("What you cannot see is ") once cost five missed translations on the
    # website because the dictionary key had been written trimmed.
    _missing = []

    def T(x):
        if lang == "en" or not isinstance(x, str) or not x.strip():
            return x
        # Pure numbers, single letters and card kickers ("01", "A", "483") carry no language, so
        # they are neither translated nor counted as a gap. Anything with two or more letters is
        # prose or a label and must be decided deliberately, even if the decision is "unchanged".
        if not re.search(r"[A-Za-z]{2}", x):
            return x
        head = x[:len(x) - len(x.lstrip())]
        tail = x[len(x.rstrip()):]
        key = x.strip()
        val = PACKS.get(lang, {}).get(key)
        if val is None:
            _missing.append(key)
            return x
        return head + val + tail

    def _tb_(s, x, y, w, h, text, *a, **k):
        return _TB(s, x, y, w, h, T(text), *a, **k)

    def card_(s, x, y, w, h, kicker, kcol, head, body, **k):
        return _CARD(s, x, y, w, h, T(kicker), kcol, T(head), T(body), **k)

    def bullets_(s, x, y, w, items, **k):
        return _BULLETS(s, x, y, w, [T(i) for i in items], **k)

    def stat_(s, x, y, w, value, label, *a, **k):
        return _STAT(s, x, y, w, value, T(label), *a, **k)

    def table_(s, x, y, w, cols, rows, widths, **k):
        rows = [tuple((T(c[0]), c[1]) if isinstance(c, tuple) else T(c) for c in r) for r in rows]
        return _TABLE(s, x, y, w, [T(c) for c in cols], rows, widths, **k)

    d = Deck(template)
    _orig = d.slide

    def slide(eyebrow, title, title_tail="", sub="", footer=FOOT, hero=False):
        eyebrow, sub = T(eyebrow), T(sub)
        title = [(T(t), c) for t, c in title] if not isinstance(title, str) else T(title)
        title_tail = T(title_tail)
        _check_title(title, title_tail)
        return _orig(eyebrow, title, title_tail, sub, footer, hero)
    d.slide = slide

    # Every call site below goes through the wrappers, so adding a slide cannot bypass translation.
    _tb, card, bullets, stat, table = _tb_, card_, bullets_, stat_, table_  # noqa: F811

    # ---------------------------------------------------------------- 1. cover
    s = d.slide("PERSEUS SHIELD",
                [("ACTIVE DEFENCE,", WHITE), ("ON YOUR SIDE", WHITE), ("OF THE WIRE.", VIOLET)],
                None,
                "An AI-governed HTTP defence layer that watches the reflection, not the claim. "
                "It sits in front of what you already run and it never touches your firewall.",
                FOOT, True)
    _tb(s, 0.85, 4.62, 11.6, 0.30, "WHY PERSEUS", 10.5, CYAN, MONO, True)
    _tb(s, 0.85, 4.92, 11.6, 0.72,
        "Perseus beat the Gorgon without ever looking at her directly. He watched the reflection in "
        "a polished shield. A user agent is attacker-controlled and lies; the paths a client asks "
        "for are the reflection, and they cannot be faked without stopping the attack.",
        11.5, BODY, TEXT)
    for i, (v, lab, col) in enumerate([(str(N_CLASSES), "attack classes\nrecognised", CYAN),
                                       (str(N_ACTIONS), "authorised actions\none tap each", VIOLET),
                                       ("4", "AI reviewers\nadvisory only", INDIGO),
                                       ("0", "firewall changes\never made", GREEN)]):
        stat(s, 0.85 + i * 2.95, 5.85, 2.7, v, lab, col)

    # ---------------------------------------------------------------- 2. the problem
    s = d.slide("THE GAP", "NOBODY IS WATCHING", " THE CLIENT.",
                "Every layer below is real and necessary. None of them answers the question a "
                "scanner actually poses.")
    rows = [("Network firewall", "Ports and addresses", "Cannot see a URL path. Port 443 is open by design."),
            ("WAF / rule engine", "Known payload shapes", "Matches signatures per request. Does not model a CLIENT over time."),
            ("DDoS scrubbing", "Volume", "A 4-request reconnaissance scan is not volume. It passes cleanly."),
            ("EDR", "The host, after landing", "Engages once something is already executing on the box."),
            ("SIEM / SOAR", "Everything, later", "Correlates after the fact. Median human response is measured in hours.")]
    y = table(s, 0.85, 2.30, 11.6, ["Layer", "What it judges", "Why a scanner walks past it"],
              rows, [0.20, 0.24, 0.56])
    _rect(s, 0.85, y + 0.28, 11.6, 0.90, fill=PANEL, line=LINE)
    _tb(s, 1.10, y + 0.42, 11.1, 0.62,
        "The gap is BEHAVIOUR OVER TIME from a single client. One request for /.env is noise. "
        "Four requests for four different secrets files, from one address, announcing six browsers, "
        "is an attack in progress. Nothing in the stack above is built to say that out loud.",
        11, WHITE, TEXT)

    # ---------------------------------------------------------------- 3. how it decides
    s = d.slide("MECHANISM", "CODE DECIDES.", " MODELS ADVISE.",
                "The decision on the request path is pure arithmetic. No model call ever sits "
                "between a visitor and your site.")
    for i, (k, kc, h, b) in enumerate([
            ("01", CYAN, "OBSERVE",
             "Every request is classified against %d attack-shape patterns: WordPress, PHP probes, "
             ".env and .git, admin panels, traversal, SQLi, XSS, shell/RCE, backup files, IoT "
             "router paths and more. Classification is regex, not inference." % N_CLASSES),
            ("02", VIOLET, "CORROBORATE",
             "Signals must agree before they convict. Fingerprint rotation proves AUTOMATION, not "
             "attack, so it scores only when a second hostile signal is present. Your own uptime "
             "checks and CI look exactly like automation."),
            ("03", INDIGO, "ACT, TIME-BOXED",
             "Tarpit first, then a timed HTTP block. Every block expires by itself. Nothing the "
             "shield does on its own is permanent, and nothing needs a human to undo it."),
            ("04", GREEN, "ASK, FOR ANYTHING BIGGER",
             "A 24-hour hold, widening to a /24, an abuse report: those reach a human on Telegram "
             "with the evidence attached, and expire unanswered after two hours.")]):
        card(s, 0.85 + (i % 2) * 5.95, 2.30 + (i // 2) * 2.10, 5.65, 1.90, k, kc, h, b)
    _tb(s, 0.85, 6.62, 11.6, 0.30,
        "A model call is 300 ms to 60 s. In front of a request that IS a denial of service, that is "
        "the outage. Perseus reviews out of band, on a timer, and never in the request path.",
        10.5, MUTED, TEXT)

    # ---------------------------------------------------------------- 4. honeytoken + rails
    s = d.slide("PRECISION", "THE RAILS ARE", " THE PRODUCT.",
                "Anyone can block traffic. The engineering is in never blocking the wrong person.")
    bullets(s, 0.85, 2.28, 6.05, [
        "%d HONEYTOKENS are the only zero-false-positive signal available. They are listed as "
        "Disallow in robots.txt and linked from nowhere, so a request for one is a deliberate scan "
        "or a robots-ignoring crawler. Either way it is not a customer." % N_HONEY,
        "VARIETY, NOT VOLUME. A real visitor misses the same few stale paths. A scanner misses "
        "hundreds of different ones. Misses only score once an address has missed on six or more "
        "DISTINCT paths.",
        "TWO PATH PREFIXES CAN NEVER BE BLOCKED: /.well-known/ (blocking it turns a scanner into a "
        "certificate outage for every domain on the host) and /api/ (authentication is the control "
        "there; a 401 is already a refusal).",
        "A BLAST CAP refuses a mass block. Beyond a small absolute allowance, Perseus will not "
        "block more than a set share of recent distinct visitors. An automatic control that can "
        "cause an outage is worse than no control.",
    ], gap=1.12, size=10.5)
    _rect(s, 7.30, 2.28, 5.15, 4.10, fill=PANEL, line=LINE)
    _tb(s, 7.55, 2.44, 4.65, 0.30, "FAILS OPEN, BY DESIGN", 10, CYAN, MONO, True)
    _tb(s, 7.55, 2.80, 4.65, 3.40,
        "Every internal error in the decision path resolves to ALLOW.\n\n"
        "A kill switch and an allow-list sit above everything, and neither is tunable by the AI "
        "panel.\n\n"
        "Manual release forgives the history that caused the block, not just the timer. Releasing "
        "somebody who is instantly re-blocked is not a release.\n\n"
        "%d unit tests and a %d-path mass-scanning corpus run on every deploy. The corpus also "
        "asserts that none of our own real routes is ever treated as an attack."
        % (N_TESTS, N_CORPUS), 10.5, BODY, TEXT)

    # ---------------------------------------------------------------- 5. governance
    s = d.slide("GOVERNANCE", "FOUR MODELS TUNE IT.", " NONE COMMANDS IT.",
                "The AI reviews what the shield DID and proposes numbers. It cannot block anyone, "
                "and it cannot widen its own authority.")
    for i, (h, b, c) in enumerate([
            ("MAY PROPOSE",
             "Values for %d integers only: how many suspicious hits before slowing a client down, "
             "before a timed block, the observation window, block duration, delay per request, and "
             "the fingerprint-rotation threshold." % N_BOUNDS, CYAN),
            ("MUST AGREE",
             "Three of four reviewers must push the same DIRECTION before any number moves, and "
             "the value applied is the MEDIAN. One bold model cannot drag the result. Steps over "
             "25 percent are refused outright.", VIOLET),
            ("CANNOT TOUCH",
             "Blocking or unblocking an address, the bounds themselves, the blast cap, the "
             "allow-list, the kill switch, and the never-block path list. Every proposal is clamped "
             "to its committed range on READ, so even a corrupted tuning file stays in range.", RED)]):
        card(s, 0.85 + i * 3.95, 2.30, 3.70, 2.30, "0%d" % (i + 1), c, h, b, bsize=9.6)
    _rect(s, 0.85, 4.95, 11.6, 1.55, fill=PANEL, line=LINE)
    _tb(s, 1.10, 5.10, 11.1, 0.30, "FOUR VENDORS, NO SHARED FAILURE DOMAIN", 10, CYAN, MONO, True)
    _tb(s, 1.10, 5.44, 11.1, 0.95,
        "The panel runs one model each from four independent providers. A rate limit or an outage "
        "at any one of them is provider-wide, so a single-vendor panel is four hats on one head. "
        "It also means a model that is simply wrong is contradicted by three others rather than "
        "believed. The panel is advisory in both directions: it can neither block a good change nor "
        "wave through a bad one.", 11, BODY, TEXT)

    # ---------------------------------------------------------------- 6. the console
    s = d.slide("THE CONSOLE", "ONE TAP,", " WITH THE EVIDENCE ATTACHED.",
                "Three tiers, decided once. The operator is asked for anything with reach or cost, "
                "and never asked for something reversible and cheap.")
    rows = [(("AUTO", GREEN), "Tarpit, then a timed HTTP block, then alert",
             "Reversible, time-boxed, expires by itself. Waiting for a human means the scan finishes first."),
            (("ASK", AMBER), "Hold 24h · Block /24 1h · Report abuse · Strict 1h · Ban path · False alarm",
             "Longer reach or a real cost. A /24 can be a whole office or a mobile carrier, so the shield may honour that state but never writes it unasked."),
            (("NEVER", RED), "Scanning back, connecting to the host, any form of hack-back",
             "Criminal under StGB 202a/202b/303a/303b and 202c, EU Directive 2013/40, US CFAA 1030, Canada CC 342.1. The address is usually a compromised third party.")]
    y = table(s, 0.85, 2.30, 11.6, ["Tier", "Actions", "Why it sits there"], rows,
              [0.09, 0.36, 0.55], rh=0.86)
    _rect(s, 0.85, y + 0.30, 11.6, 1.30, fill=PANEL, line=LINE)
    _tb(s, 1.10, y + 0.44, 11.1, 0.30, "THE CONFIRMATION IS READ BACK OUT OF LIVE STATE", 10, CYAN, MONO, True)
    _tb(s, 1.10, y + 0.78, 11.1, 0.72,
        "After a tap, Perseus re-reads the actual expiry, the actual block-list size and the actual "
        "deadline, and reports those. A failed action is reported as NOT APPLIED with the reason. "
        "Silence after a tap would be indistinguishable from success, and a console whose statements "
        "cannot be trusted is worth nothing during an incident.", 11, BODY, TEXT)

    # ---------------------------------------------------------------- 7. complement
    s = d.slide("FIT", "IT COMPLEMENTS.", " IT REPLACES NOTHING.",
                "Perseus is HTTP-layer only and deliberately narrow. Here is exactly where it sits "
                "against what you already own.")
    rows = [("Network firewall / NGFW", "Keep", "Perseus never touches it. No iptables, no nftables, no ACL, no rule push. Asserted by test."),
            ("WAF", "Keep", "The WAF judges the PAYLOAD of one request. Perseus judges the CLIENT across many. Different question, both worth asking."),
            ("CDN / DDoS scrubbing", "Keep", "Volume is absorbed upstream. Perseus handles the low-and-slow reconnaissance that is too small to scrub."),
            ("Bot management", "Overlaps", "Closest neighbour. Perseus adds an authorisation console and an out-of-band AI review of its own decisions."),
            ("EDR / XDR", "Keep", "Engages after something lands. Perseus works to stop the landing."),
            ("SIEM / SOAR", "Keep, and feed it", "Every decision is a structured event. Perseus is a high-quality source, not a competitor.")]
    table(s, 0.85, 2.30, 11.6, ["Existing control", "Verdict", "How Perseus relates to it"],
          rows, [0.22, 0.12, 0.66])
    _tb(s, 0.85, 6.30, 11.6, 0.60,
        "WHAT PERSEUS IS NOT: it is not a WAF, not a DDoS scrubber, not an IPS, and it inspects "
        "nothing below HTTP. A defence product that will not state its own boundary is asking the "
        "buyer to discover it during an incident.", 10.5, AMBER, TEXT, True)

    # ---------------------------------------------------------------- 8. category comparison
    s = d.slide("CATEGORIES", "COMPARED ON", " ARCHITECTURE, NOT ON CLAIMS.",
                "We have benchmarked Perseus against no named product, so this compares what each "
                "category is structurally FOR. That is checkable, and a competitor release cannot "
                "refute it.")
    rows = [("Unit of judgement", ("One request", MUTED), ("Traffic volume", MUTED), ("A session", MUTED), ("A CLIENT over time", CYAN)),
            ("Decision latency", ("Inline, ms", MUTED), ("Inline, ms", MUTED), ("Inline, ms", MUTED), ("Inline, ms (arithmetic)", CYAN)),
            ("Where it runs", ("Edge or host", MUTED), ("Provider edge", MUTED), ("Edge or host", MUTED), ("Your app, your data", CYAN)),
            ("Tuning", ("Rules, by hand", MUTED), ("Provider policy", MUTED), ("Vendor model", MUTED), ("4-model quorum, bounded", CYAN)),
            ("Escalation to a human", ("Ticket", MUTED), ("Ticket", MUTED), ("Console", MUTED), ("One tap, 2h expiry", CYAN)),
            ("Data leaves your estate", ("Varies", MUTED), ("Yes", MUTED), ("Varies", MUTED), ("No", GREEN))]
    table(s, 0.85, 2.42, 11.6, ["Dimension", "WAF", "DDoS scrubbing", "Bot management", "PERSEUS SHIELD"],
          rows, [0.22, 0.16, 0.19, 0.20, 0.23], rh=0.50)
    _tb(s, 0.85, 6.10, 11.6, 0.80,
        "THE HONEST READING: the first three columns are mature categories that do their job better "
        "than we do ours at volume. Perseus is not competing for that budget. It answers a question "
        "none of them is shaped to answer, on infrastructure you already control, and it hands the "
        "decision to a named human when the decision has consequences.", 10.5, BODY, TEXT)

    # ---------------------------------------------------------------- 9. legacy integration
    s = d.slide("DEPLOYMENT", "IT GOES IN FRONT", " OF WHAT YOU RUN.",
                "Four integration shapes. None of them requires a change to a firewall, a routing "
                "change, or a maintenance window on the protected system.")
    for i, (k, kc, h, b) in enumerate([
            ("A", CYAN, "REVERSE-PROXY MIDDLEWARE",
             "Perseus runs as middleware inside the proxy that already fronts your sites. Real client "
             "IP is read from the forwarded header. This is how we run it ourselves, in front of "
             "several unrelated domains on one host."),
            ("B", VIOLET, "SIDECAR TO A LEGACY APP",
             "For an application nobody wants to touch, Perseus terminates in front of it and passes "
             "traffic through. The legacy app is unmodified and unaware. Nothing is recompiled and "
             "no agent is installed on it."),
            ("C", INDIGO, "DETECTION-ONLY, ALONGSIDE",
             "Enforcement off, telemetry on. Perseus watches and reports without ever refusing a "
             "request. This is the honest way to start: prove the verdicts against your real traffic "
             "before anything is enforced."),
            ("D", GREEN, "FEED THE CONTROLS YOU HAVE",
             "Every decision is a structured event. Export to your SIEM, and hand confirmed hostile "
             "addresses to a blocklist your existing edge already consumes. Perseus decides; your "
             "estate enforces where you want it to.")]):
        card(s, 0.85 + (i % 2) * 5.95, 2.30 + (i // 2) * 2.06, 5.65, 1.86, k, kc, h, b, bsize=9.6)
    _tb(s, 0.85, 6.55, 11.6, 0.40,
        "START AT C. A defence you have not watched being wrong is a defence you cannot trust to be "
        "right, and detection-only costs nothing to reverse.", 10.5, AMBER, TEXT, True)

    # ---------------------------------------------------------------- 10. evidence
    s = d.slide("EVIDENCE", "MEASURED ON", " OUR OWN FRONT DOOR.",
                "One analyse_attacks run against the live event log of cybergod.ai. These are our "
                "numbers, from our estate, and they are stated at what they actually prove.")
    for i, (v, lab, col) in enumerate([(LOG_REQ, "requests\nanalysed", CYAN),
                                       (LOG_SRC, "distinct\nsources", INDIGO),
                                       (LOG_SCAN, "behaved like\nscanners", VIOLET),
                                       (str(N_CORPUS), "path corpus\npinned in tests", GREEN)]):
        stat(s, 0.85 + i * 2.95, 2.30, 2.7, v, lab, col)
    rows = [("wordpress", "483"), ("php_probe", "481"), ("admin_panel", "162"),
            ("shell_rce", "113"), ("template", "100"), ("env_secrets", "96"),
            ("backup_file", "45")]
    _tb(s, 0.85, 3.95, 5.65, 0.30, "CLASSES BY DISTINCT SOURCE", 10, CYAN, MONO, True)
    table(s, 0.85, 4.30, 5.65, ["Class", "Sources"], rows, [0.62, 0.38], rh=0.30, size=9.6)
    _rect(s, 7.05, 3.95, 5.40, 2.70, fill=PANEL, line=LINE)
    _tb(s, 7.30, 4.10, 4.90, 0.30, "SAID AT WHAT IT PROVES", 10, AMBER, MONO, True)
    _tb(s, 7.30, 4.44, 4.90, 2.05,
        "Those %s sources were DETECTED, not stopped. That log was written BEFORE the shield "
        "shipped, and saying otherwise would be an unsupported claim on a security product, which "
        "is self-refuting.\n\n"
        "The same measurement found 19 scanning patterns the detector did not yet recognise. They "
        "were added, and the corpus is now pinned in the test suite so the gap cannot reopen. That "
        "loop, measure the log then close the gap, is the product." % LOG_SCAN,
        10.5, BODY, TEXT)

    # ---------------------------------------------------------------- 11. standards
    s = d.slide("ASSURANCE", "MAPPED TO CONTROLS", " AUDITORS ASK FOR.",
                "Perseus was built against published control language, not against a threat feed.")
    rows = [("NIST SP 800-53r5", "SI-4 system monitoring · SI-10 input validation · SC-5 denial-of-service protection · AC-7 unsuccessful logon attempts"),
            ("NIST SP 800-63B", "5.2.2 throttling of authentication attempts"),
            ("OWASP", "ASVS v4 14.6 · Automated Threat Handbook OAT-011 scraping · OAT-014 vulnerability scanning"),
            ("MITRE ATT&CK", "T1595.001 scanning IP blocks · T1595.003 wordlist scanning · T1110.001 password guessing"),
            ("CISA", "Bad Practices: default-deny on management surfaces")]
    y = table(s, 0.85, 2.30, 11.6, ["Framework", "Controls Perseus implements or evidences"],
              rows, [0.22, 0.78], rh=0.48)
    _rect(s, 0.85, y + 0.24, 11.6, 1.22, fill=PANEL, line=LINE)
    _tb(s, 1.10, y + 0.36, 11.1, 0.30, "AND THE PRIVACY POSITION, BECAUSE IT IS ASKED EVERY TIME",
        10, CYAN, MONO, True)
    _tb(s, 1.10, y + 0.68, 11.1, 0.86,
        "An IP address is personal data (GDPR; CJEU C-582/14 Breyer). Perseus can be run with source "
        "addresses truncated to a /24 or salted-hashed on the way IN, so correlation survives and the "
        "identifier does not. Nothing is sent to a third party by default, and the AI review sees "
        "aggregate behaviour rather than visitor identities.", 11, BODY, TEXT)

    # ---------------------------------------------------------------- 12. close
    s = d.slide("NEXT", "THIRTY DAYS,", " ENFORCEMENT OFF.",
                "The only honest way to sell a defence product is to let it be watched being wrong "
                "first.")
    for i, (k, kc, h, b) in enumerate([
            ("WEEK 1", CYAN, "DEPLOY DETECTION-ONLY",
             "Middleware or sidecar, enforcement off. No routing change, no firewall change, no "
             "maintenance window on the protected system."),
            ("WEEK 2-3", VIOLET, "WATCH IT BE WRONG",
             "Every verdict against your real traffic, with the evidence. Your monitoring, your CI "
             "and your partners are exactly the traffic that exposes a bad rule."),
            ("WEEK 4", INDIGO, "ENFORCE THE CLASSES YOU ACCEPT",
             "Turn on enforcement for the classes you agree with, at the thresholds you set. The "
             "console and the panel start from your numbers, inside your bounds."),
            ("ONGOING", GREEN, "THE LOOP",
             "Daily digest of what happened, what was unrecognised, and what the panel proposes. "
             "Every accepted pattern becomes a test so the gap cannot reopen.")]):
        card(s, 0.85 + (i % 2) * 5.95, 2.30 + (i // 2) * 2.06, 5.65, 1.86, k, kc, h, b, bsize=9.6)
    # The footer sits at y=7.04. 6.50 + 0.62 = 7.12 put this panel on top of it.
    _rect(s, 0.85, 6.42, 11.6, 0.54, fill=PANEL, line=LINE)
    _tb(s, 1.10, 6.50, 11.1, 0.38,
        "PERSEUS SHIELD · S4Biz Group · Cybergod LLC · feranicus@s4biz.io · +351 939 994 642",
        11, WHITE, MONO, True)

    if lang != "en" and _missing:
        # A gate, not a note: "is the German complete" must be a number. Duplicates collapsed,
        # order preserved so the report reads in slide order.
        seen, uniq = set(), []
        for m in _missing:
            if m not in seen:
                seen.add(m); uniq.append(m)
        if os.environ.get("PERSEUS_I18N_AUDIT"):
            print("UNTRANSLATED (%d):" % len(uniq))
            for m in uniq:
                print("  %r," % m)
        else:
            print("[!] %d string(s) fell back to English. PERSEUS_I18N_AUDIT=1 lists them."
                  % len(uniq))
    return d.save(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument("--template", default=os.path.join(
        here, "S4biz_Sovereign_Cyber_Cloud_Capability_Brief.pptx"))
    ap.add_argument("--lang", default="en", choices=["en"] + sorted(PACKS))
    ap.add_argument("--out")
    a = ap.parse_args()
    out = a.out or os.path.join(here, "S4biz_Perseus_Shield_%s.pptx" % a.lang.upper())
    p = build(a.template, out, a.lang)
    print("built: %s (%.1f KB)" % (p, os.path.getsize(p) / 1024.0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
