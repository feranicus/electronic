// legal.jsx — ONE bilingual source for every privacy/GDPR text (page + Assess notice).
//
// Why one file: the /privacy page and the Art.13 notice must never drift apart. If a retention
// period or a processor changes, it changes in exactly one place, in both languages.
//
// Language: follows the browser (de* -> German), overridable by the reader, remembered per browser.
// German is the reference text (German customers, German regulator); English is the translation.
import { useEffect, useState } from "react";

const KEY = "cg_legal_lang";

export function useLegalLang() {
  const [lang, setLangState] = useState(() => {
    try {
      const saved = localStorage.getItem(KEY);
      if (saved === "de" || saved === "en") return saved;
      return (navigator.language || "en").toLowerCase().startsWith("de") ? "de" : "en";
    } catch {
      return "en";
    }
  });
  useEffect(() => { try { localStorage.setItem(KEY, lang); } catch { /* private mode */ } }, [lang]);
  return [lang, setLangState];
}

export function LangToggle({ lang, setLang }) {
  return (
    <div className="lang-toggle" role="group" aria-label="Language / Sprache">
      <button type="button" className={lang === "de" ? "on" : ""} onClick={() => setLang("de")}>Deutsch</button>
      <button type="button" className={lang === "en" ? "on" : ""} onClick={() => setLang("en")}>English</button>
    </div>
  );
}

// ---------------------------------------------------------------- the Art.13 notice (Assess screen)
export const NOTICE = {
  de: {
    title: "🇪🇺 Datenverarbeitung",
    p1: (<>Mit <strong>Assess</strong> starten Sie eine Analyse auf einem Server im Rechenzentrum{" "}
         <strong>Frankfurt am Main (DE)</strong>. Dabei verarbeiten wir Ihre E-Mail-Adresse, Ihre
         IP-Adresse, Zeitstempel und das angefragte Unternehmen — zur Bereitstellung des Dienstes und
         zur Angriffserkennung (Art. 6(1)(b) und 6(1)(f) DSGVO). Sicherheits­protokolle werden nach{" "}
         <strong>30 Tagen</strong> automatisch gelöscht.</>),
    p2: (<><strong>Ihre Daten bleiben in der EU.</strong> Einzige Ausnahme: Ihre E-Mail-Adresse geht an
         die Gmail-API, um Ihnen den Einmalcode zu senden (Google, EU-US Data Privacy Framework). Die
         Analyse selbst nutzt nur öffentliche Quellen und erhält <strong>keine</strong> Nutzerdaten —
         nur den Namen des zu bewertenden Unternehmens.</>),
    link: "Datenschutzhinweise", ok: "Verstanden — nicht mehr anzeigen",
    mini: (<>🇪🇺 Ihre Daten bleiben in der EU (Frankfurt/FRA1) · E-Mail, IP, Zeitstempel &amp;
           Firmenname werden zur Bereitstellung und Angriffserkennung verarbeitet
           (Art. 6(1)(b)/(f) DSGVO), Logs 30 Tage. </>),
  },
  en: {
    title: "🇪🇺 Data processing",
    p1: (<>Clicking <strong>Assess</strong> starts an analysis on a server in the{" "}
         <strong>Frankfurt am Main (DE)</strong> data centre. We process your email address, your IP
         address, timestamps and the company you requested — to deliver the service and to detect
         attacks (Art. 6(1)(b) and 6(1)(f) GDPR). Security logs are deleted automatically after{" "}
         <strong>30 days</strong>.</>),
    p2: (<><strong>Your data stays in the EU.</strong> The only exception: your email address goes to
         the Gmail API so we can send you the one-time code (Google, EU-US Data Privacy Framework).
         The analysis itself uses public sources only and receives <strong>no</strong> user data —
         just the name of the company being assessed.</>),
    link: "Privacy notice", ok: "Understood — don't show again",
    mini: (<>🇪🇺 Your data stays in the EU (Frankfurt/FRA1) · email, IP, timestamps &amp; company name
           are processed to deliver the service and detect attacks (Art. 6(1)(b)/(f) GDPR),
           logs kept 30 days. </>),
  },
};

// ======================================================================================
// OPERATOR — the ONE place the legal identity lives. Impressum, the Datenschutz controller
// section and the contact page all read from here, so they can never disagree.
//
// !! FILL THESE IN BEFORE GOING LIVE !!
// A German Impressum (§ 5 DDG, formerly § 5 TMG) legally REQUIRES a real name and a
// physical postal address you can receive mail at — a PO box is not sufficient, and an
// incomplete Impressum is the classic Abmahnung (cease-and-desist) risk.
// `ship.py` prints a loud warning while any value below still starts with "TODO".
// ======================================================================================
export const OPERATOR = {
  // Verified from your own jev.best source (src/data.jsx, index.html) — legal spelling as used on
  // your Colt address jevgenijs.vainsteins@colt.net and your Latvian passport.
  name:    "Jevgenijs Vainsteins",
  street:  "Herman J Bach Weg 16",
  zipCity: "61169 Friedberg",
  country: "Deutschland",
  email:   "feranicus@s4biz.io",
  phone:   "+49 157 8554 1545",
  vatId:   "",                       // USt-IdNr. — leave "" if you are not VAT-registered
  // 61169 Friedberg is in Hessen, so the Hessian authority is the competent one (Art. 77 DSGVO).
  authority: "Der Hessische Beauftragte für Datenschutz und Informationsfreiheit",
  // --- contact channels (verified from jev.best) ---
  linkedin: "https://www.linkedin.com/in/feranicus",
  telegram: "https://t.me/feranicus",
  github:   "https://github.com/feranicus",
};
export const operatorReady = () =>
  ![OPERATOR.name, OPERATOR.street, OPERATOR.zipCity, OPERATOR.phone]
    .some((v) => String(v).startsWith("TODO"));

// ---------------------------------------------------------------- the /impressum page
export const IMPRESSUM = {
  de: {
    h1: "Impressum", sub: "Angaben gemäß § 5 DDG",
    s1: "Diensteanbieter",
    s2: "Kontakt",
    s3: "Verantwortlich für den Inhalt nach § 18 Abs. 2 MStV",
    s4: "Umsatzsteuer-Identifikationsnummer",
    s5: "Streitbeilegung",
    s5p: (<>Die Europäische Kommission stellt eine Plattform zur Online-Streitbeilegung (OS) bereit:{" "}
          <a href="https://ec.europa.eu/consumers/odr/" target="_blank" rel="noreferrer">ec.europa.eu/consumers/odr</a>.
          Wir sind nicht bereit und nicht verpflichtet, an Streitbeilegungs­verfahren vor einer
          Verbraucher­schlichtungsstelle teilzunehmen.</>),
    s6: "Haftung für Inhalte und Links",
    s6p: (<>Als Diensteanbieter sind wir für eigene Inhalte auf diesen Seiten nach den allgemeinen
          Gesetzen verantwortlich (§ 7 Abs. 1 DDG). Für Inhalte verlinkter externer Seiten ist stets
          deren jeweiliger Anbieter verantwortlich; zum Zeitpunkt der Verlinkung waren keine
          Rechtsverstöße erkennbar. Bei Bekanntwerden von Rechtsverletzungen entfernen wir
          entsprechende Links umgehend.</>),
    s7: "Urheberrecht",
    s7p: (<>Die durch den Betreiber erstellten Inhalte und Werke auf diesen Seiten unterliegen dem
          deutschen Urheberrecht. Die durch cybergod.ai erzeugten Analyse­dokumente sind internes
          Vertriebs­material und nicht zur öffentlichen Verbreitung bestimmt.</>),
    note: "Hinweis: cybergod.ai ist ein zugangsbeschränktes internes Werkzeug für die Cyber-Pre-Sales-Analyse; es steht der Allgemeinheit nicht zur Nutzung offen.",
    todo: "⚠ Dieses Impressum ist noch unvollständig. Vor der Veröffentlichung müssen Name, Anschrift und Telefonnummer in OPERATOR (src/legal.jsx) eingetragen werden — ein unvollständiges Impressum ist abmahnfähig.",
  },
  en: {
    h1: "Legal notice (Impressum)", sub: "Information pursuant to § 5 DDG (German Digital Services Act)",
    s1: "Service provider",
    s2: "Contact",
    s3: "Responsible for content under § 18(2) MStV",
    s4: "VAT identification number",
    s5: "Dispute resolution",
    s5p: (<>The European Commission provides a platform for online dispute resolution (ODR):{" "}
          <a href="https://ec.europa.eu/consumers/odr/" target="_blank" rel="noreferrer">ec.europa.eu/consumers/odr</a>.
          We are neither willing nor obliged to participate in dispute-resolution proceedings before a
          consumer arbitration board.</>),
    s6: "Liability for content and links",
    s6p: (<>As a service provider we are responsible for our own content on these pages under general
          law (§ 7(1) DDG). The respective provider is always responsible for the content of linked
          external pages; no legal infringements were apparent at the time of linking. We remove such
          links immediately upon becoming aware of any infringement.</>),
    s7: "Copyright",
    s7p: (<>Content created by the operator on these pages is subject to German copyright law. The
          analysis documents produced by cybergod.ai are internal sales material and are not intended
          for public distribution.</>),
    note: "Note: cybergod.ai is an access-restricted internal tool for cyber pre-sales analysis; it is not open to the general public.",
    todo: "⚠ This legal notice is incomplete. Name, postal address and phone number must be filled into OPERATOR (src/legal.jsx) before publication — an incomplete Impressum is legally actionable in Germany.",
  },
};

// ---------------------------------------------------------------- the /contact page
export const CONTACT = {
  de: {
    h1: "Kontakt", sub: "Direkter Draht — kein Formular, keine Warteschleife",
    lead: "Fragen zum Zugang, zu einer Analyse, zum Datenschutz oder zur Partnerschaft? Schreiben Sie direkt.",
    email: "E-Mail", emailD: "Für Zugang, Datenschutz­anfragen und alles Geschäftliche. Antwort in der Regel am selben Arbeitstag.",
    li: "LinkedIn", liD: "Der schnellste Weg für eine berufliche Kontaktaufnahme.",
    tg: "Telegram", tgD: "Direktnachricht — dieselbe Plattform, auf der auch die Assessment-Bots laufen.",
    gh: "GitHub", ghD: "Technischer Hintergrund und Projekte.",
    access: "Zugang anfragen",
    accessD: "cybergod.ai ist zugangsbeschränkt: eine freigegebene Colt- oder Partner-E-Mail-Adresse ist erforderlich. Nennen Sie in Ihrer Nachricht Ihre Firma und die gewünschte Adresse.",
    legal: "Rechtliches: ", soon: "Kanal folgt",
  },
  en: {
    h1: "Contact", sub: "A direct line — no form, no queue",
    lead: "Questions about access, an assessment, data protection or partnering? Get in touch directly.",
    email: "Email", emailD: "For access, data-protection requests and anything commercial. Usually answered the same working day.",
    li: "LinkedIn", liD: "The fastest route for a professional introduction.",
    tg: "Telegram", tgD: "Direct message — the same platform the assessment bots run on.",
    gh: "GitHub", ghD: "Technical background and projects.",
    access: "Request access",
    accessD: "cybergod.ai is access-restricted: an approved Colt or partner email address is required. Include your company and the address you want enabled.",
    legal: "Legal: ", soon: "channel coming soon",
  },
};

// ---------------------------------------------------------------- the /privacy page
export const PRIVACY = {
  de: {
    h1: "Datenschutz & Datenverarbeitung", sub: "Privacy & data processing — cybergod.ai",
    lead: "cybergod.ai ist ein internes Werkzeug für die Cyber-Pre-Sales-Analyse. Diese Seite beschreibt, welche Daten wir verarbeiten, auf welcher Rechtsgrundlage, wo sie liegen und wie lange wir sie aufbewahren — gemäß DSGVO Art. 13/14.",
    s1: "1. Wo Ihre Daten liegen",
    s1p: (<><strong>Ihre personenbezogenen Daten bleiben in der EU.</strong> Anwendung, Datenbank,
         Sitzungen, erzeugte Dokumente und Sicherheits­protokolle laufen ausschließlich auf einem
         Server im <strong>Rechenzentrum Frankfurt am Main, Deutschland (DigitalOcean, Region
         FRA1)</strong>. Es gibt keine Replikation und kein Backup außerhalb der EU.</>),
    s1sub: "Auftragsverarbeiter (Art. 28 DSGVO):",
    s1list: [
      (<><strong>DigitalOcean</strong> — Hosting des Servers, Region Frankfurt (FRA1), EU.</>),
      (<><strong>Google (Gmail API)</strong> — Versand des Einmalcodes (OTP) an Ihre E-Mail-Adresse
         sowie Versand der Betriebs- und Sicherheits­benachrichtigungen an den Betreiber. Diese
         Benachrichtigungen können <strong>technische Metadaten eines Zugriffs enthalten (IP-Adresse,
         Land, Browser/Gerät, aufgerufene Seite)</strong>, damit der Betreiber Zugriffe und
         Sicherheits­vorfälle prüfen kann (Art. 6(1)(f) DSGVO). Google ist nach dem EU-US Data
         Privacy Framework zertifiziert (Art. 45 DSGVO). Es werden keine Inhalte der Analysen
         übermittelt.</>),
      (<><strong>Telegram</strong> — nur, wenn Sie den optionalen Telegram-Zugang nutzen; dann gilt
         Ihre Telegram-Nutzer-ID.</>),
    ],
    s1note: (<>Die Analyse selbst wertet ausschließlich <strong>öffentlich sichtbare
             Infrastruktur­daten des zu bewertenden Unternehmens</strong> aus (Shodan, RIPE, CAIDA,
             PeeringDB, crt.sh) und erzeugt die Berichtstexte über einen KI-Endpunkt. Diesen Diensten
             wird <strong>nur der Firmenname bzw. die Domain/ASN des Analyse-Ziels</strong> bzw. der
             technische Befund übergeben — <strong>keine Nutzer­kennung, keine E-Mail-Adresse, keine
             IP-Adresse eines Nutzers</strong>. Sie sind daher keine Empfänger Ihrer
             personenbezogenen Daten.</>),
    s2: "2. Welche Daten wir verarbeiten",
    th: ["Daten", "Zweck", "Rechtsgrundlage", "Aufbewahrung"],
    rows: [
      ["E-Mail-Adresse (Anmeldung, OTP)", "Zugangskontrolle, Zwei-Faktor-Authentifizierung",
       "Art. 6(1)(b) — Vertrag/Nutzung; Art. 6(1)(f) — Sicherheit", "Dauer des Zugangs"],
      ["IP-Adresse, Zeitstempel, User-Agent, Gerät/Browser, Land",
       "Angriffserkennung (DDoS, Brute-Force, Scanner), Missbrauchsabwehr, Betrieb",
       "Art. 6(1)(f) — berechtigtes Interesse an IT-Sicherheit (ErwG 49)",
       "30 Tage (Log-Retention), danach automatisch gelöscht"],
      ["Angefragte Unternehmen, Sprache, Zeitpunkt, erzeugte Dokumente",
       "Bereitstellung der Analyse, Kostenzuordnung, Nachvollziehbarkeit",
       "Art. 6(1)(b), Art. 6(1)(f)", "90 Tage bzw. bis zur Löschung durch den Nutzer"],
      ["Sicherheitsmeldungen (Regel, Betreff, Forensik)", "Incident Response", "Art. 6(1)(f)", "30 Tage"],
    ],
    s2note: (<><strong>Keine</strong> Werbe-Cookies, <strong>kein</strong> Tracking über Websites
             hinweg, <strong>kein</strong> Profiling, <strong>keine</strong> automatisierte
             Entscheidung mit Rechtswirkung (Art. 22). Gesetzt wird ausschließlich ein technisch
             notwendiges Session-Cookie (§ 25 Abs. 2 Nr. 2 TDDDG — einwilligungsfrei).</>),
    s3: "3. Datenminimierung (Art. 5(1)(c))",
    s3list: [
      (<>Geolokalisierung nur auf <strong>Länderebene</strong> — keine Stadt, keine Koordinaten.
         Lokale Offline-Datenbank, keine Abfrage bei Dritten.</>),
      (<>Statische Dateien (CSS/Bilder) werden nicht protokolliert.</>),
      (<>IP-Adressen können betreiberseitig <strong>gehasht</strong> gespeichert werden
         (<code>TELEMETRY_HASH_IPS=1</code>): Korrelation bleibt möglich, die Kennung entfällt.</>),
      (<>Analyse-Ziele sind <strong>Unternehmen</strong>, keine natürlichen Personen. Es werden
         ausschließlich öffentlich sichtbare Infrastruktur­daten ausgewertet — es findet
         <strong> kein aktives Scannen</strong> statt.</>),
    ],
    s4: "4. Ihre Rechte (Art. 15–21 DSGVO)",
    s4p: (<>Auskunft, Berichtigung, Löschung, Einschränkung, Datenübertragbarkeit sowie
          <strong> Widerspruch gegen die Verarbeitung auf Grundlage berechtigter Interessen</strong>.
          Anfragen an <a href="mailto:feranicus@s4biz.io">feranicus@s4biz.io</a> — Antwort innerhalb
          eines Monats (Art. 12(3)). Beschwerderecht bei einer Aufsichtsbehörde (Art. 77).</>),
    s5: "5. Sicherheit (Art. 32 DSGVO)",
    s5list: [
      "TLS-Verschlüsselung für den gesamten Transport; automatische Zertifikatserneuerung.",
      "Zero-Trust-Zugang: zugelassene Identität + gemeinsames Passwort + E-Mail-Einmalcode.",
      "Dokumente sind eigentümergebunden — Zugriff nur durch den erzeugenden Nutzer.",
      "Kontinuierliche Angriffserkennung mit Alarmierung (Brute-Force, DDoS, Scanner, Exfiltration).",
      "Regelmäßige, automatisierte Sicherheits-Updates des Servers.",
    ],
    s6: "6. Verantwortlicher",
    s6p: (<>Verantwortlicher im Sinne der DSGVO ist <strong>{OPERATOR.name}</strong>,{" "}
          {OPERATOR.street}, {OPERATOR.zipCity}, {OPERATOR.country} —{" "}
          <a href={"mailto:" + OPERATOR.email}>{OPERATOR.email}</a>. Vollständige Angaben im{" "}
          <a href="/impressum">Impressum</a>. Interne Nutzung für Colt-Pre-Sales; die erzeugten
          Dokumente sind internes Vertriebsmaterial. Sie haben das Recht, sich bei einer
          Datenschutz-Aufsichtsbehörde zu beschweren (Art. 77 DSGVO); zuständig ist{" "}
          <strong>{OPERATOR.authority}</strong>.</>),
    credit: "IP-zu-Land-Zuordnung: ", disclaimerT: "Hinweis: ",
    disclaimer: "Dieser Text beschreibt die tatsächliche technische Verarbeitung. Er ist keine Rechtsberatung und sollte vor externer Veröffentlichung von einer/einem Datenschutzbeauftragten geprüft werden.",
  },
  en: {
    h1: "Privacy & data processing", sub: "Datenschutz & Datenverarbeitung — cybergod.ai",
    lead: "cybergod.ai is an internal tool for cyber pre-sales analysis. This page explains what data we process, on what legal basis, where it is stored and how long we keep it — under GDPR Art. 13/14.",
    s1: "1. Where your data lives",
    s1p: (<><strong>Your personal data stays in the EU.</strong> The application, database, sessions,
         generated documents and security logs all run on a single server in the{" "}
         <strong>Frankfurt am Main data centre, Germany (DigitalOcean, region FRA1)</strong>. There is
         no replication and no backup outside the EU.</>),
    s1sub: "Processors (Art. 28 GDPR):",
    s1list: [
      (<><strong>DigitalOcean</strong> — hosting of the server, Frankfurt (FRA1) region, EU.</>),
      (<><strong>Google (Gmail API)</strong> — delivers the one-time code (OTP) to your email address,
         and delivers operational and security notifications to the operator. Those notifications may
         contain <strong>technical metadata about a visit (IP address, country, browser/device, page
         requested)</strong> so the operator can review access and security events (Art. 6(1)(f) GDPR).
         Google is certified under the EU-US Data Privacy Framework (Art. 45 GDPR). No assessment
         content is transmitted.</>),
      (<><strong>Telegram</strong> — only if you use the optional Telegram access; then your Telegram
         user ID applies.</>),
    ],
    s1note: (<>The analysis itself evaluates only <strong>publicly visible infrastructure data of the
             company being assessed</strong> (Shodan, RIPE, CAIDA, PeeringDB, crt.sh) and writes the
             report prose via an AI endpoint. Those services receive <strong>only the company name or
             the target's domain/ASN</strong>, or the technical finding — <strong>no user identifier,
             no email address, no user IP address</strong>. They are therefore not recipients of your
             personal data.</>),
    s2: "2. What we process",
    th: ["Data", "Purpose", "Legal basis", "Retention"],
    rows: [
      ["Email address (sign-in, OTP)", "Access control, two-factor authentication",
       "Art. 6(1)(b) — contract/use; Art. 6(1)(f) — security", "For as long as access exists"],
      ["IP address, timestamp, user-agent, device/browser, country",
       "Attack detection (DDoS, brute force, scanners), abuse prevention, operations",
       "Art. 6(1)(f) — legitimate interest in IT security (Recital 49)",
       "30 days (log retention), then deleted automatically"],
      ["Companies requested, language, time, generated documents",
       "Delivering the analysis, cost attribution, traceability",
       "Art. 6(1)(b), Art. 6(1)(f)", "90 days, or until deleted by the user"],
      ["Security alerts (rule, subject, forensics)", "Incident response", "Art. 6(1)(f)", "30 days"],
    ],
    s2note: (<><strong>No</strong> advertising cookies, <strong>no</strong> cross-site tracking,
             <strong> no</strong> profiling, <strong>no</strong> automated decision-making with legal
             effect (Art. 22). The only cookie set is a strictly necessary session cookie
             (§ 25(2)(2) TDDDG — no consent required).</>),
    s3: "3. Data minimisation (Art. 5(1)(c))",
    s3list: [
      (<>Geolocation at <strong>country level only</strong> — no city, no coordinates. Local offline
         database, no third-party lookup.</>),
      (<>Static files (CSS/images) are not logged.</>),
      (<>IP addresses can be stored <strong>hashed</strong> by the operator
         (<code>TELEMETRY_HASH_IPS=1</code>): correlation is preserved, the identifier is not.</>),
      (<>Assessment targets are <strong>companies</strong>, not natural persons. Only publicly visible
         infrastructure data is evaluated — <strong>no active scanning</strong> takes place.</>),
    ],
    s4: "4. Your rights (Art. 15–21 GDPR)",
    s4p: (<>Access, rectification, erasure, restriction, portability, and the{" "}
          <strong>right to object to processing based on legitimate interests</strong>. Requests to{" "}
          <a href="mailto:feranicus@s4biz.io">feranicus@s4biz.io</a> — answered within one month
          (Art. 12(3)). You may also lodge a complaint with a supervisory authority (Art. 77).</>),
    s5: "5. Security (Art. 32 GDPR)",
    s5list: [
      "TLS encryption for all transport; automatic certificate renewal.",
      "Zero-trust access: allow-listed identity + shared password + emailed one-time code.",
      "Documents are owner-scoped — only the user who generated them can read them.",
      "Continuous attack detection with alerting (brute force, DDoS, scanners, exfiltration).",
      "Regular, automated security patching of the server.",
    ],
    s6: "6. Controller",
    s6p: (<>The controller under the GDPR is <strong>{OPERATOR.name}</strong>, {OPERATOR.street},{" "}
          {OPERATOR.zipCity}, {OPERATOR.country} —{" "}
          <a href={"mailto:" + OPERATOR.email}>{OPERATOR.email}</a>. Full details in the{" "}
          <a href="/impressum">legal notice</a>. Internal use for Colt pre-sales; the generated
          documents are internal sales material. You have the right to lodge a complaint with a data
          protection supervisory authority (Art. 77 GDPR); the competent authority is{" "}
          <strong>{OPERATOR.authority}</strong>.</>),
    credit: "IP-to-country mapping: ", disclaimerT: "Note: ",
    disclaimer: "This text describes the actual technical processing. It is not legal advice and should be reviewed by a data protection officer before external publication.",
  },
};
