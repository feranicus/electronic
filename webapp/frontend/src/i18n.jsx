// i18n.jsx — ONE dictionary for every UI string outside the legal pages.
//
// WHY IT SHARES legal.jsx's HOOK AND STORAGE KEY:
// `useLegalLang()` already exists, already defaults from the browser (de* -> German) and already
// remembers the reader's choice in localStorage under `cg_legal_lang`. Introducing a second
// language store would let the site and the privacy page disagree — one toggle showing German
// while the other shows English is exactly the drift that legal.jsx was created to prevent.
// So there is ONE hook, ONE key, ONE toggle, and it now governs the whole site.
//
// FALLBACK IS ENGLISH, NEVER A CRASH. `t()` returns the English string when a German key is
// missing, and the key itself if neither exists. Same doctrine as the deck i18n engine: an
// incomplete translation must degrade to readable English, never to a blank screen or an
// exception. That also means this file can be filled in incrementally and safely.
//
// German is Hochdeutsch and addresses the reader as "Sie" — these are business buyers.
import { useLegalLang } from "./legal";

export const useLang = useLegalLang;

const EN = {
  // ---- navigation ------------------------------------------------------------------------------
  "nav.why": "Why it matters",
  "nav.live": "See it live",
  "nav.machine": "The machine",
  "nav.deep": "Deep dive",
  "nav.secure": "Security",
  "nav.demo": "Demo",
  "nav.contact": "Contact",
  "nav.open": "Open the app",
  "nav.login": "Log in",
  "nav.home": "Home",
  "nav.back": "Back to the main page",

  // Bottom tab bar. SHORT by contract — six of these share a 360px row, so anything longer than
  // ~8 characters wraps and the bar doubles in height. Never reuse the nav labels here.
  "tab.why": "Why", "tab.live": "Live", "tab.machine": "Machine",
  "tab.deep": "Deep", "tab.secure": "Secure", "tab.open": "Open",

  // ---- landing hero ----------------------------------------------------------------------------
  "hero.kick": "Cybergod LLC / S4Biz Group - external cyber-risk and EU compliance assessment",
  "hero.h1a": "Type a company name.",
  "hero.h1b": "Four boardroom decks.",
  "hero.h1c": "Two minutes.",
  "hero.sub": "Every organisation has an internet-facing footprint it cannot fully see. From one company name, this maps yours using public sources alone, prices the risk in euros, names the groups most likely to target you, and shows which EU deadlines already apply - without touching a single one of your systems.",
  "hero.cta1": "Open the app / Log in",
  "hero.cta2": "See a full demo report",

  // ---- the creed -------------------------------------------------------------------------------
  "creed.kick": "The name is not an accident",
  "creed.l1": "Cassandra foretold the fall of Troy — and no one believed her.",
  "creed.l2a": "We predict the ", "creed.l2b": "critical cyber risks", "creed.l2c": ", stop them ",
  "creed.l2d": "before they materialise", "creed.l2e": ", and keep every ",
  "creed.l2f": "Trojan horse", "creed.l2g": " out of your IT landscape.",

  // ---- demo page -------------------------------------------------------------------------------
  "demo.warnH": "THIS IS A DEMONSTRATION — EVERY RESULT IS FABRICATED",
  "demo.warn1a": "Trojan Empire is a fictional company.",
  "demo.warn1b": " Every host, certificate, CVE, threat actor and euro figure below is ",
  "demo.warn1c": "invented",
  "demo.warn1d": " to show you the shape of the deliverable. Nothing was scanned. No real organisation is described. The IP addresses use IETF documentation ranges (192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24) that cannot route to a real machine.",
  "demo.warn2": "What is not fabricated is the machinery: these files come from the same engine and the same deck builders a paying engagement uses.",
  "demo.whatH": "What this actually does",
  "demo.s1h": "You type one company name",
  "demo.s1b": "That is the entire input. No IP ranges, no ASNs, no certificates to paste. The engine works out the rest — including the subsidiaries that trade under completely different names, which is where most of the real exposure hides.",
  "demo.s2h": "It finds what is already public",
  "demo.s2b": "Entirely passive. It reads what internet-wide scanners, certificate transparency logs and public DNS already publish about the estate. No packet is ever sent to the target, so nothing needs permission and nothing sets off an alarm.",
  "demo.s3h": "It proves what belongs to whom",
  "demo.s3b": "The hard part is not finding hosts — it is knowing which are theirs. Every asset is scored on independent evidence (published group structure, certificates, per-IP registry ownership) and the reasons are recorded, so a disputed host can be explained rather than argued about.",
  "demo.s4h": "It writes the boardroom papers",
  "demo.s4b": "Four decks and an animated report, in English or Hochdeutsch: what is exposed, what it would cost in euros, who would plausibly come for it, and which service closes each gap. Roughly three minutes, start to finish.",
  "demo.deckH": "The deliverables — download them",
  "demo.deckLead": "These are the real files, generated for the fictional Trojan Empire. Open them; this is exactly what lands in your inbox for a real target.",
  "demo.deckWait": "Preparing the demonstration artifacts…",
  "demo.deckErr": "The demo artifacts are being prepared. Please refresh in a moment.",
  "demo.d1": "Attack-surface findings",
  "demo.d2": "Business impact, priced in euros",
  "demo.d3": "Who would target you, and why",
  "demo.d4": "Animated threat report",
  "demo.techH": "How it works, technically",
  "demo.accessH": "Running this against your own estate",
  "demo.access1": "The demonstration above is open to everyone. Live assessments are available to approved partners only, because each one consumes licensed scanning capacity and produces material about a real organisation.",
  "demo.access2": "If you sell cyber security and would like access, get in touch:",
  "demo.access3": "Please include your company and your role so access can be confirmed.",
  "demo.haveAccess": "I already have access",

  // ---- landing: sections below the fold ---------------------------------------------------------
  "lede.edge": "Your internet-facing footprint grows every quarter - a forgotten host, a supplier portal, a VPN nobody decommissioned, a certificate that quietly names an internal system. An attacker enumerates all of it in minutes, from public sources, without ever touching you. Most organisations have never looked at themselves the same way.",
  "q3.h": "Three questions decide a security budget. You should be able to answer all three today.",
  "clocks.lede": "Three EU laws now reach most mid-size organisations: NIS2, the Cyber Resilience Act and the EU AI Act. These dates are written in law, not on a vendor\u2019s slide - and the penalties are set against global turnover.",
  "touch.body": "This is not a penetration test and it is not a scan of your systems. No ports are probed, no logins attempted, no agent installed, no credentials required. It reads only what is already public - the internet equivalent of noting which doors are visible from the street.",
  "touch.bold": "That is precisely why it can show you what an attacker already sees, with no change request, no maintenance window, and not one packet sent to your infrastructure.",
  "earn.01h": "Before the board", "earn.01b": "Walk in with the exposure and the euro number instead of adjectives.",
  "earn.02h": "Before an audit", "earn.02b": "NIS2, CRA and AI-Act applicability, duties and deadlines on a single page.",
  "earn.03h": "After an acquisition", "earn.03b": "See the estate you have just inherited, mapped from the outside in.",
  "earn.04h": "Third-party risk", "earn.04b": "Assess a supplier the same way - no access, no questionnaire, no waiting.",
  "earn.05h": "Quarter on quarter", "earn.05b": "Re-run it and see exactly what changed on your perimeter.",
  "earn.06h": "Your own first look", "earn.06b": "Most organisations find something public they did not know was there.",
  // ---- demo: the technical section ---------------------------------------------------------------
  "demo.t1h": "Attribution before analysis.",
  "demo.t1b": " Ownership is graded on a 0\u2013100 confidence score built from independent signals \u2014 the customer\u2019s own published group structure, certificate subject names, per-IP registry organisation, vendor-tenant labels, DNS the customer controls. Two weak signals that agree beat one strong signal that does not, and every score carries the rules that produced it.",
  "demo.t2h": "Co-tenant safety.",
  "demo.t2b": " A shared netblock is not a customer. Where several companies share a provider range, per-IP registry ownership decides, so a neighbour\u2019s exposed management interface never appears in your report.",
  "demo.t3h": "The AI writes prose, never facts.",
  "demo.t3b": " Severity, evidence and CVE identifiers come from the scan data only. The language model rewrites explanation and remediation, and a second model from a different vendor independently reviews the result. Any CVE the model cites that is not in the evidence is stripped before the deck is built.",
  "demo.t4h": "Deterministic rendering.",
  "demo.t4b": " The decks are generated by code, not by a model, so the same input always produces the same document \u2014 and layout is machine-checked for overflow before anything ships.",
  "demo.t5h": "EU-resident.",
  "demo.t5b": " Application, data and logs run in Frankfurt. Assessments are passive: no packet is sent to the target.",
  "faq.1q": "\u201cIs this legal?\u201d",
  "faq.1a": "Yes. It uses public sources any researcher could look up, and never interacts with your systems. Nothing is exploited, nothing is logged into.",
  "faq.2q": "\u201cHow accurate is it?\u201d",
  "faq.2a": "Every finding carries the evidence behind it. Where a source cannot be reached it says \u201cunknown\u201d rather than inventing a weakness - and it asks you to confirm anything it could not resolve.",
  "faq.3q": "\u201cWhat do we have to provide?\u201d",
  "faq.3a": "Your company name. No access, no questionnaire, no NDA to start, and nothing to install. The euro figures are modelled ranges with the assumptions shown.",
  // ---- login -----------------------------------------------------------------------------------
  "login.h": "Sign in",
  "login.zero": "Zero-trust access for cyber security sales teams.",
  "login.email": "Work email",
  "login.pw": "Access password",
  "login.send": "Send me a code",
  "login.code": "6-digit code",
  "login.verify": "Verify",
  "login.sent": "A 6-digit code was sent to your inbox.",
  "login.portal": "Sign in to the portal",
  "login.pwPh": "Shared access password",
  "login.continue": "Continue \u2192",
  "login.codeH": "Enter your code",
  "login.codeSub": "We emailed a 6-digit code to ",
  "login.back": "\u2190 Back to the overview",
  "login.iam": "Identity & Access",
  "login.step1": "Your identity", "login.step1b": "your approved email + the shared access password",
  "login.step2": "One-time code", "login.step2b": "A 6-digit code lands in your inbox",
  "login.step3": "You\u2019re in", "login.step3b": "Your personal cabinet: assessments, assistant, history",
  "login.foot": "Zero-trust \u00b7 approved partners only",
};

const DE = {
  "nav.why": "Warum es zählt",
  "nav.live": "Live ansehen",
  "nav.machine": "Die Maschine",
  "nav.deep": "Im Detail",
  "nav.secure": "Sicherheit",
  "nav.demo": "Demo",
  "nav.contact": "Kontakt",
  "nav.open": "Zur Anwendung",
  "nav.login": "Anmelden",
  "nav.home": "Startseite",
  "nav.back": "Zurück zur Startseite",

  "tab.why": "Warum", "tab.live": "Live", "tab.machine": "Technik",
  "tab.deep": "Detail", "tab.secure": "Sicher", "tab.open": "App",

  "hero.kick": "Cybergod LLC / S4Biz Group - externe Cyber-Risiko- und EU-Compliance-Bewertung",
  "hero.h1a": "Einen Firmennamen eingeben.",
  "hero.h1b": "Vier Vorstandspräsentationen.",
  "hero.h1c": "Zwei Minuten.",
  "hero.sub": "Jedes Unternehmen hat eine internetseitige Angriffsfläche, die es nicht vollständig überblickt. Aus einem einzigen Firmennamen kartiert die Plattform Ihre — ausschließlich aus öffentlichen Quellen —, bepreist das Risiko in Euro, benennt die Gruppen, die Sie am ehesten ins Visier nehmen, und zeigt, welche EU-Fristen bereits gelten. Ohne ein einziges Ihrer Systeme zu berühren.",
  "hero.cta1": "Zur Anwendung / Anmelden",
  "hero.cta2": "Vollständigen Demo-Bericht ansehen",

  "creed.kick": "Der Name ist kein Zufall",
  "creed.l1": "Kassandra sagte den Fall Trojas voraus — und niemand glaubte ihr.",
  "creed.l2a": "Wir sagen die ", "creed.l2b": "kritischen Cyber-Risiken", "creed.l2c": " voraus, stoppen sie, ",
  "creed.l2d": "bevor sie eintreten", "creed.l2e": ", und halten jedes ",
  "creed.l2f": "trojanische Pferd", "creed.l2g": " aus Ihrer IT-Landschaft fern.",

  "demo.warnH": "DIES IST EINE DEMONSTRATION — ALLE ERGEBNISSE SIND ERFUNDEN",
  "demo.warn1a": "Trojan Empire ist ein fiktives Unternehmen.",
  "demo.warn1b": " Jeder Host, jedes Zertifikat, jede CVE, jeder Bedrohungsakteur und jeder Euro-Betrag unten ist ",
  "demo.warn1c": "erfunden",
  "demo.warn1d": ", um Ihnen die Form des Ergebnisses zu zeigen. Es wurde nichts gescannt. Es wird keine reale Organisation beschrieben. Die IP-Adressen stammen aus IETF-Dokumentationsbereichen (192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24), die zu keiner realen Maschine führen können.",
  "demo.warn2": "Nicht erfunden ist die Maschinerie: Diese Dateien stammen aus derselben Engine und denselben Generatoren wie bei einem bezahlten Projekt.",
  "demo.whatH": "Was die Plattform tatsächlich tut",
  "demo.s1h": "Sie geben einen Firmennamen ein",
  "demo.s1b": "Das ist die gesamte Eingabe. Keine IP-Bereiche, keine ASNs, keine Zertifikate. Die Engine ermittelt den Rest — einschließlich der Tochtergesellschaften, die unter völlig anderen Namen firmieren. Genau dort verbirgt sich meist die eigentliche Exposition.",
  "demo.s2h": "Sie findet, was bereits öffentlich ist",
  "demo.s2b": "Vollständig passiv. Ausgewertet wird, was internetweite Scanner, Certificate-Transparency-Logs und öffentliches DNS ohnehin über die Infrastruktur veröffentlichen. Es wird kein einziges Paket an das Ziel gesendet: keine Genehmigung nötig, kein Alarm ausgelöst.",
  "demo.s3h": "Sie belegt, wem was gehört",
  "demo.s3b": "Das Schwierige ist nicht, Hosts zu finden — sondern zu wissen, welche wirklich dem Unternehmen gehören. Jedes Asset wird anhand unabhängiger Belege bewertet (veröffentlichte Konzernstruktur, Zertifikate, Registry-Eigentümer je IP), und die Gründe werden protokolliert. So lässt sich ein strittiger Host erklären statt bestreiten.",
  "demo.s4h": "Sie schreibt die Vorstandsunterlagen",
  "demo.s4b": "Vier Präsentationen und ein animierter Bericht, auf Englisch oder in Hochdeutsch: was exponiert ist, was es in Euro kosten würde, wer es plausibel angreifen würde und welcher Service die jeweilige Lücke schließt. Rund drei Minuten von Anfang bis Ende.",
  "demo.deckH": "Die Ergebnisse — zum Herunterladen",
  "demo.deckLead": "Dies sind die echten Dateien, erzeugt für das fiktive Trojan Empire. Öffnen Sie sie: Genau das landet bei einem echten Ziel in Ihrem Postfach.",
  "demo.deckWait": "Demonstrationsartefakte werden vorbereitet…",
  "demo.deckErr": "Die Demo-Artefakte werden gerade erzeugt. Bitte in einem Moment neu laden.",
  "demo.d1": "Befunde der Angriffsfläche",
  "demo.d2": "Geschäftsauswirkung, in Euro bepreist",
  "demo.d3": "Wer Sie angreifen würde — und warum",
  "demo.d4": "Animierter Bedrohungsbericht",
  "demo.techH": "Wie es technisch funktioniert",
  "demo.accessH": "Die Analyse für Ihre eigene Infrastruktur",
  "demo.access1": "Die Demonstration oben steht allen offen. Echte Analysen sind ausschließlich freigegebenen Partnern vorbehalten, da jede Analyse lizenzierte Scan-Kapazität verbraucht und Material über eine reale Organisation erzeugt.",
  "demo.access2": "Wenn Sie Cyber Security verkaufen und Zugang möchten, melden Sie sich:",
  "demo.access3": "Bitte nennen Sie Ihr Unternehmen und Ihre Rolle, damit der Zugang bestätigt werden kann.",
  "demo.haveAccess": "Ich habe bereits Zugang",

  "lede.edge": "Ihre internetseitige Angriffsfläche wächst jedes Quartal — ein vergessener Host, ein Lieferantenportal, ein VPN, das niemand abgeschaltet hat, ein Zertifikat, das still und leise ein internes System benennt. Ein Angreifer erfasst das alles in Minuten, aus öffentlichen Quellen, ohne Sie je zu berühren. Die meisten Unternehmen haben sich noch nie so betrachtet.",
  "q3.h": "Drei Fragen entscheiden über ein Sicherheitsbudget. Sie sollten alle drei heute beantworten können.",
  "clocks.lede": "Drei EU-Gesetze erfassen inzwischen die meisten mittelgroßen Unternehmen: NIS2, der Cyber Resilience Act und die EU-KI-Verordnung. Diese Termine stehen im Gesetz, nicht auf einer Anbieterfolie — und die Sanktionen bemessen sich am weltweiten Umsatz.",
  "touch.body": "Dies ist kein Penetrationstest und kein Scan Ihrer Systeme. Es werden keine Ports geprüft, keine Anmeldungen versucht, kein Agent installiert, keine Zugangsdaten benötigt. Gelesen wird ausschließlich, was bereits öffentlich ist — das Internet-Äquivalent dazu, zu notieren, welche Türen von der Straße aus sichtbar sind.",
  "touch.bold": "Genau deshalb kann es Ihnen zeigen, was ein Angreifer bereits sieht — ohne Change Request, ohne Wartungsfenster und ohne ein einziges Paket an Ihre Infrastruktur.",
  "earn.01h": "Vor dem Vorstand", "earn.01b": "Gehen Sie mit der Exposition und der Euro-Zahl hinein statt mit Adjektiven.",
  "earn.02h": "Vor einem Audit", "earn.02b": "NIS2-, CRA- und KI-Verordnungs-Anwendbarkeit, Pflichten und Fristen auf einer Seite.",
  "earn.03h": "Nach einer Übernahme", "earn.03b": "Sehen Sie die gerade übernommene Infrastruktur, von außen kartiert.",
  "earn.04h": "Lieferantenrisiko", "earn.04b": "Bewerten Sie einen Lieferanten genauso — ohne Zugang, ohne Fragebogen, ohne Wartezeit.",
  "earn.05h": "Quartal für Quartal", "earn.05b": "Erneut ausführen und genau sehen, was sich an Ihrem Perimeter geändert hat.",
  "earn.06h": "Ihr eigener erster Blick", "earn.06b": "Die meisten Unternehmen finden etwas Öffentliches, von dem sie nicht wussten, dass es existiert.",
  "demo.t1h": "Attribution vor Analyse.",
  "demo.t1b": " Eigentum wird auf einer Skala von 0 bis 100 bewertet, gestützt auf unabhängige Signale — die vom Unternehmen selbst veröffentlichte Konzernstruktur, Zertifikatsnamen, die Registry-Organisation je IP, Vendor-Tenant-Kennungen, vom Unternehmen kontrolliertes DNS. Zwei schwache Signale, die übereinstimmen, wiegen schwerer als ein starkes, das es nicht tut, und jede Bewertung führt die Regeln mit, die sie erzeugt haben.",
  "demo.t2h": "Schutz vor Mitmietern.",
  "demo.t2b": " Ein gemeinsam genutzter Netzblock ist kein Kunde. Teilen sich mehrere Unternehmen einen Providerbereich, entscheidet die Registry-Eigentümerschaft je IP — die exponierte Management-Oberfläche eines Nachbarn taucht so nie in Ihrem Bericht auf.",
  "demo.t3h": "Die KI schreibt Prosa, niemals Fakten.",
  "demo.t3b": " Schweregrad, Nachweise und CVE-Kennungen stammen ausschließlich aus den Scan-Daten. Das Sprachmodell formuliert Erläuterung und Behebung, und ein zweites Modell eines anderen Anbieters prüft das Ergebnis unabhängig. Jede vom Modell genannte CVE, die nicht in den Nachweisen steht, wird vor dem Erstellen der Unterlagen entfernt.",
  "demo.t4h": "Deterministische Erzeugung.",
  "demo.t4b": " Die Unterlagen werden von Code erzeugt, nicht von einem Modell: Dieselbe Eingabe ergibt immer dasselbe Dokument — und das Layout wird maschinell auf Überlauf geprüft, bevor irgendetwas ausgeliefert wird.",
  "demo.t5h": "In der EU betrieben.",
  "demo.t5b": " Anwendung, Daten und Protokolle laufen in Frankfurt. Analysen sind passiv: Es wird kein Paket an das Ziel gesendet.",
  "faq.1q": "\u201eIst das legal?\u201c",
  "faq.1a": "Ja. Es nutzt öffentliche Quellen, die jede Person nachschlagen könnte, und interagiert nie mit Ihren Systemen. Es wird nichts ausgenutzt und sich in nichts eingeloggt.",
  "faq.2q": "\u201eWie genau ist es?\u201c",
  "faq.2a": "Jeder Befund führt den zugehörigen Nachweis mit. Ist eine Quelle nicht erreichbar, steht dort \u201eunbekannt\u201c, statt eine Schwachstelle zu erfinden — und Sie werden gebeten, alles zu bestätigen, was nicht geklärt werden konnte.",
  "faq.3q": "\u201eWas müssen wir bereitstellen?\u201c",
  "faq.3a": "Ihren Firmennamen. Kein Zugang, kein Fragebogen, keine NDA zum Start und nichts zu installieren. Die Euro-Angaben sind modellierte Bandbreiten mit offengelegten Annahmen.",
  "login.h": "Anmelden",
  "login.zero": "Zero-Trust-Zugang für Cyber-Security-Vertriebsteams.",
  "login.email": "Geschäftliche E-Mail",
  "login.pw": "Zugangspasswort",
  "login.send": "Code anfordern",
  "login.code": "6-stelliger Code",
  "login.verify": "Bestätigen",
  "login.sent": "Ein 6-stelliger Code wurde an Ihr Postfach gesendet.",
  "login.portal": "Am Portal anmelden",
  "login.pwPh": "Gemeinsames Zugangspasswort",
  "login.continue": "Weiter \u2192",
  "login.codeH": "Code eingeben",
  "login.codeSub": "Wir haben einen 6-stelligen Code gesendet an ",
  "login.back": "\u2190 Zur\u00fcck zur \u00dcbersicht",
  "login.iam": "Identit\u00e4t & Zugang",
  "login.step1": "Ihre Identit\u00e4t", "login.step1b": "Ihre freigegebene E-Mail + das gemeinsame Zugangspasswort",
  "login.step2": "Einmalcode", "login.step2b": "Ein 6-stelliger Code kommt in Ihr Postfach",
  "login.step3": "Sie sind drin", "login.step3b": "Ihr pers\u00f6nliches Cockpit: Analysen, Assistent, Verlauf",
  "login.foot": "Zero-Trust \u00b7 nur freigegebene Partner",
};

// ---------------------------------------------------------------------------------------------
// LANDING-PAGE COPY, keyed by the ENGLISH SOURCE STRING (gettext style).
//
// WHY NOT INVENTED KEYS: this page holds ~120 strings, many of them long sentences embedded in JS
// data arrays that are rendered with innerHTML. Inventing "landing.deep.d7.body" for each would be
// 120 chances to mistype a key and silently ship a blank. The English text IS the key, so a missing
// translation degrades to the original sentence — never to an empty box.
// ---------------------------------------------------------------------------------------------
const DE_BY_EN = {
  // -- section chrome
  "For boards, CISOs and risk owners": "Für Vorstände, CISOs und Risikoverantwortliche",
  "What you cannot see is": "Was Sie nicht sehen, ist",
  "already public": "bereits öffentlich",
  "How it usually goes": "Wie es üblicherweise läuft",
  "What you get here": "Was Sie hier bekommen",
  "An annual test, scoped to what you remembered to list":
    "Ein jährlicher Test, begrenzt auf das, woran Sie sich erinnert haben",
  "A findings spreadsheet with no price attached to anything":
    "Eine Befundtabelle, in der nichts einen Preis hat",
  "Weeks between the question and the answer": "Wochen zwischen Frage und Antwort",
  "The board asks what it would actually cost. Nobody knows.":
    "Der Vorstand fragt, was es tatsächlich kosten würde. Niemand weiß es.",
  "Compliance deadlines live in somebody&rsquo;s inbox.":
    "Compliance-Fristen liegen in irgendeinem Postfach.",
  "Your whole internet-facing estate, discovered from public data":
    "Ihre gesamte internetseitige Infrastruktur, ermittelt aus öffentlichen Quellen",
  "Every exposure modelled in euros, with the method shown":
    "Jede Exposition in Euro modelliert, mit offengelegter Methode",
  "Minutes, not weeks - and repeatable whenever you want":
    "Minuten statt Wochen — und jederzeit wiederholbar",
  "A number the board can actually make a decision on":
    "Eine Zahl, auf deren Basis der Vorstand wirklich entscheiden kann",
  "The regulatory clock, on one slide.": "Die Regulierungsuhr, auf einer Folie.",
  "GEOPOL deck": "GEOPOL-Präsentation", "C-BIQ deck": "C-BIQ-Präsentation",
  "Compliance decks": "Compliance-Präsentationen",
  "The clocks are": "Die Uhren laufen", "already running": "bereits",
  "NIS2 &mdash; Germany": "NIS2 &mdash; Deutschland",
  "EU AI Act": "EU-KI-Verordnung", "Cyber Resilience Act": "Cyber Resilience Act",
  "Nothing of yours is touched": "Nichts von Ihnen wird berührt",
  "Where it earns its place": "Wo es sich bezahlt macht",
  "Fair questions": "Berechtigte Fragen",
  "It is whether you know what.": "Sondern ob Sie wissen, was.",
  "Request an assessment": "Analyse anfragen",
  "Open the app": "Zur Anwendung",
  "Guided tour": "Geführte Tour",
  "You and bots": "Sie und die Bots", "Outside services": "Externe Dienste",
  "Safety nets": "Schutzmechanismen", "Observability": "Observability",
  "Swipe the map sideways to explore &rarr;": "Karte seitlich wischen zum Erkunden &rarr;",
  "Under the hood - for the engineer": "Unter der Haube — für Technikerinnen und Techniker",
  "Secure-by-design, in plain terms.": "Secure by Design, verständlich erklärt.",
  "Nobody walks in": "Niemand kommt einfach herein",
  "Secrets never in git": "Geheimnisse niemals in Git",
  "Scanned before ship": "Geprüft vor dem Ausliefern",
  "Never breaks the neighbours": "Stört niemals die Nachbarsysteme",
  "Do this in the web app": "Im Web-Portal ausführen",
  "One input. Zero flags.": "Eine Eingabe. Keine Parameter.",
  "The chat loops - watch the four .pptx files land.":
    "Der Chat läuft in Schleife — sehen Sie zu, wie die vier .pptx-Dateien ankommen.",
  "This is the entire product - texting a bot. The chat below plays the real flow: log in, ask, get four decks.":
    "Das ist das gesamte Produkt — eine Nachricht an einen Bot. Der Chat unten zeigt den echten Ablauf: anmelden, fragen, vier Präsentationen erhalten.",
  "Hover a box to see its wires. Click it to jump to the details. Or hit play for a guided tour.":
    "Fahren Sie über ein Feld, um seine Verbindungen zu sehen. Klicken Sie es an für Details. Oder starten Sie die geführte Tour.",
  "Plain English for everyone; under the hood for the engineer. Click a box in the map above to jump here.":
    "Klartext für alle, Technik für Fachleute. Klicken Sie oben in der Karte auf ein Feld, um hierher zu springen.",
  "Trivy (deps+image), CodeQL SAST, ruff, pytest - every change checked before it reaches the server.":
    "Trivy (Abhängigkeiten + Image), CodeQL SAST, ruff, pytest — jede Änderung wird geprüft, bevor sie den Server erreicht.",
  "An isolated container stack; existing services and the firewall are untouched.":
    "Ein isolierter Container-Stack; bestehende Dienste und die Firewall bleiben unberührt.",
  "Keys live only on the server or as encrypted GitHub secrets;":
    "Schlüssel liegen ausschließlich auf dem Server oder als verschlüsselte GitHub-Secrets;",
  // -- the three questions
  "WHO": "WER", "HOW MUCH": "WIE VIEL", "WHEN": "WANN",
  "The threat groups realistically interested in your sector and geography - and the route they would most likely take into you.":
    "Die Angreifergruppen, die sich realistisch für Ihre Branche und Region interessieren — und der Weg, den sie am ehesten zu Ihnen nehmen würden.",
  "Your exposure modelled in euros - expected annual loss, worst realistic case, and the return on fixing it first.":
    "Ihre Exposition in Euro modelliert — erwarteter Jahresschaden, realistischer Worst Case und die Rendite einer vorgezogenen Behebung.",
  "The regulatory dates that already apply to you - and the maximum fine attached to each of them.":
    "Die Regulierungstermine, die bereits für Sie gelten — und das jeweils angedrohte Bußgeld.",
  // -- deep dive (rendered with innerHTML from the DD array)
  "Two front doors, one input": "Zwei Eingänge, eine Eingabe",
  "Zero-trust login (2FA)": "Zero-Trust-Anmeldung (2FA)",
  "The engine + auto-discovery": "Die Engine + automatische Erkennung",
  "Shodan - what's exposed": "Shodan — was exponiert ist",
  "The AI writes it - you get five artifacts": "Die KI schreibt es — Sie erhalten fünf Artefakte",
  "A second AI audits the first": "Eine zweite KI prüft die erste",
  "It asks you what it couldn't work out": "Sie fragt Sie, was sie nicht klären konnte",
  "Compliance: NIS2, CRA, EU AI Act": "Compliance: NIS2, CRA, EU-KI-Verordnung",
  "Always watching": "Durchgehende Überwachung",
  "It patches itself": "Sie patcht sich selbst",
  "Shipping is one command": "Ausliefern ist ein einziger Befehl",
  "Type a company name - in <b>Telegram</b>, or in the <b>cybergod.ai web app</b>. Same engine, same decks. Two bots live on the server: the <b>assessment bot</b> runs the scan, <b>cassandra</b> answers questions about the findings.":
    "Geben Sie einen Firmennamen ein — in <b>Telegram</b> oder im <b>cybergod.ai-Portal</b>. Gleiche Engine, gleiche Ergebnisse. Zwei Bots laufen auf dem Server: der <b>Analyse-Bot</b> führt die Untersuchung durch, <b>Cassandra</b> beantwortet Fragen zu den Befunden.",
  "You need an approved <b>company or partner email</b>, the shared password, <b>and</b> a one-time code emailed to that inbox. Knowing the password isn't enough - you must own the mailbox.":
    "Sie benötigen eine freigegebene <b>Firmen- oder Partner-E-Mail</b>, das gemeinsame Passwort <b>und</b> einen Einmalcode, der an dieses Postfach gesendet wird. Das Passwort allein genügt nicht — Sie müssen das Postfach besitzen.",
  "From just the name the engine finds the company's <b>networks, domains and certificates</b> - then hunts, scores and writes. You never hand it an IP.":
    "Allein aus dem Namen ermittelt die Engine <b>Netze, Domains und Zertifikate</b> des Unternehmens — dann sucht, bewertet und schreibt sie. Sie übergeben nie eine IP-Adresse.",
  "It queries Shodan for exposed remote-access, databases, VPNs, mail, industrial gear and known-vulnerable systems - plus the killer pivot: the company's own private CA and whois-org, which reveal the hidden estate.":
    "Sie durchsucht Shodan nach exponierten Fernzugängen, Datenbanken, VPNs, Mailservern, Industriesteuerungen und bekannt verwundbaren Systemen — und nutzt den entscheidenden Hebel: die eigene private CA und die Whois-Organisation, die den verborgenen Teil der Infrastruktur offenlegen.",
  "A chain of AI models writes the words; fixed templates guarantee the structure and the maths. You get <b>Findings / C-BIQ (EUR) / GEOPOL / DELTAS</b> plus a <b>live animated report</b> you present on screen - in English or Hochdeutsch.":
    "Eine Kette von KI-Modellen formuliert den Text; feste Vorlagen sichern Struktur und Berechnung. Sie erhalten <b>Befunde / C-BIQ (EUR) / GEOPOL / DELTAS</b> sowie einen <b>animierten Live-Bericht</b> für die Präsentation — auf Englisch oder in Hochdeutsch.",
  "Before you ever see the decks, a <b>different model from a different vendor</b> re-reads every finding and challenges anything that looks like it isn't really theirs. A model is never allowed to mark its own homework.":
    "Bevor Sie die Unterlagen überhaupt sehen, liest ein <b>anderes Modell eines anderen Anbieters</b> jeden Befund erneut und hinterfragt alles, was nicht wirklich zum Unternehmen gehört. Kein Modell darf seine eigene Arbeit benoten.",
  "The decks land <b>first</b>. Then the engine tells you what it could not resolve - which related domains are yours, your netblocks if you sit behind a CDN, anything in the report that isn't yours - you answer, and it re-scopes and rebuilds.":
    "Die Unterlagen kommen <b>zuerst</b>. Danach nennt Ihnen die Engine, was sie nicht klären konnte — welche verwandten Domains Ihnen gehören, Ihre Netzblöcke hinter einem CDN, alles im Bericht, was nicht Ihres ist. Sie antworten, und sie definiert den Umfang neu und erstellt alles neu.",
  "The same one input, pointed at regulation. It grades the company against the three horizontal EU digital laws and writes <b>three regime decks, a roadmap deck and an animated report</b> - applicability, duties, gaps, deadlines and the maximum fine.":
    "Dieselbe eine Eingabe, auf die Regulierung gerichtet. Sie bewertet das Unternehmen anhand der drei horizontalen EU-Digitalgesetze und erstellt <b>drei Regime-Präsentationen, eine Roadmap und einen animierten Bericht</b> — Anwendbarkeit, Pflichten, Lücken, Fristen und das jeweilige Höchstbußgeld.",
  "Every login, assessment, audit, cost and patch prints a structured line that flows into <b>your existing Grafana</b> - no second monitoring stack.":
    "Jede Anmeldung, Analyse, Prüfung, Kostenbuchung und jeder Patch schreibt eine strukturierte Zeile, die in <b>Ihr bestehendes Grafana</b> fließt — kein zweiter Monitoring-Stack.",
  "A server nobody patches gets hacked. Every 3 days it <b>backs itself up</b> to Spaces, upgrades the OS/Docker, and an AI writes a risk digest. Reboots happen at 4am.":
    "Ein Server, den niemand patcht, wird kompromittiert. Alle 3 Tage <b>sichert er sich selbst</b> nach Spaces, aktualisiert Betriebssystem und Docker, und eine KI schreibt eine Risikozusammenfassung. Neustarts erfolgen um 4 Uhr morgens.",
  "Change the code, run one thing, it's live - and it <b>proves</b> the running container actually holds the new code before it reports success.":
    "Code ändern, einen Befehl ausführen, fertig — und es wird <b>nachgewiesen</b>, dass der laufende Container den neuen Code wirklich enthält, bevor Erfolg gemeldet wird.",
  // -- "Nothing of yours is touched" + closing
  "The question is not whether something of yours is exposed.":
    "Die Frage ist nicht, ob etwas von Ihnen exponiert ist.",
  // -- variants that carry a trailing space (the text node ends before an inline <span>)
  "What you cannot see is ": "Was Sie nicht sehen, ist ",
  "The clocks are ": "Die Uhren laufen ",
  "See it ": "Sehen Sie es ",
  "The whole ": "Die gesamte ",
  "Locked ": "Abgesichert ",
  "Brains": "Intelligenz",
  "You never type an IP, a network or a certificate. The robot resolves the target's ":
    "Sie geben nie eine IP, ein Netz oder ein Zertifikat ein. Der Bot ermittelt selbst ",
  "Shodan (paid)": "Shodan (kostenpflichtig)",
  "DeepSeek prose": "DeepSeek-Texte",
  "Keys live only on the server or as encrypted GitHub secrets; ":
    "Schlüssel liegen ausschließlich auf dem Server oder als verschlüsselte GitHub-Secrets; ",
  "Cybergod LLC / S4Biz Group - external cyber-risk and EU compliance assessment / one company name in, four boardroom documents out.":
    "Cybergod LLC / S4Biz Group — externe Cyber-Risiko- und EU-Compliance-Bewertung / ein Firmenname hinein, vier Vorstandsdokumente heraus.",
  "Findings / C-BIQ (EUR) / GEOPOL / DELTAS": "Befunde / C-BIQ (EUR) / GEOPOL / DELTAS",
  "One input. Zero flags.": "Eine Eingabe. Keine Parameter.",
  // -- long body paragraphs (multi-line JSX text nodes) "earn.01b": "Gehen Sie mit der Exposition und der Euro-Zahl hinein statt mit Adjektiven.", "earn.02b": "NIS2-, CRA- und KI-Verordnungs-Anwendbarkeit, Pflichten und Fristen auf einer Seite.", "earn.03b": "Sehen Sie die gerade übernommene Infrastruktur, von außen kartiert.", "earn.04b": "Bewerten Sie einen Lieferanten genauso — ohne Zugang, ohne Fragebogen, ohne Wartezeit.", "earn.05b": "Erneut ausführen und genau sehen, was sich an Ihrem Perimeter geändert hat.", "earn.06b": "Die meisten Unternehmen finden etwas Öffentliches, von dem sie nicht wussten, dass es existiert.",
  // -- fair questions
  "“Is this legal?”": "„Ist das legal?“",
  "“How accurate is it?”": "„Wie genau ist es?“",
  "“What do we have to provide?”": "„Was müssen wir bereitstellen?“",
};

/** tx("English source") -> German when the site is German, otherwise the original sentence. */
export function useTx() {
  const [lang] = useLang();
  return (en) => (lang === "de" && DE_BY_EN[en]) || en;
}


const DICT = { en: EN, de: DE };

/** t("nav.demo") in the current language. Missing German falls back to English, then to the key. */
export function tr(lang, key) {
  const d = DICT[lang] || EN;
  return (d[key] !== undefined ? d[key] : (EN[key] !== undefined ? EN[key] : key));
}

/** Hook form: `const [lang, setLang, t] = useT();` */
export function useT() {
  const [lang, setLang] = useLang();
  return [lang, setLang, (k) => tr(lang, k)];
}

/** Coverage, used by the build gate — an untranslated key must be a visible number, not a surprise. */
export const I18N_STATS = () => ({
  keys: Object.keys(EN).length,
  de: Object.keys(EN).filter((k) => DE[k] !== undefined).length,
});
