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

  // ---- login -----------------------------------------------------------------------------------
  "login.h": "Sign in",
  "login.zero": "Zero-trust access for cyber security sales teams.",
  "login.email": "Work email",
  "login.pw": "Access password",
  "login.send": "Send me a code",
  "login.code": "6-digit code",
  "login.verify": "Verify",
  "login.sent": "A 6-digit code was sent to your inbox.",
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

  "login.h": "Anmelden",
  "login.zero": "Zero-Trust-Zugang für Cyber-Security-Vertriebsteams.",
  "login.email": "Geschäftliche E-Mail",
  "login.pw": "Zugangspasswort",
  "login.send": "Code anfordern",
  "login.code": "6-stelliger Code",
  "login.verify": "Bestätigen",
  "login.sent": "Ein 6-stelliger Code wurde an Ihr Postfach gesendet.",
};

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
