// legal-locales/it.jsx — see ./index.js. Missing exports fall back to English, then German.
// German is the NORMATIVE text; this is a reading translation.
//
// TRANSLATED FROM THE ENGLISH VARIANT IN ../legal.jsx, CROSS-CHECKED AGAINST THE GERMAN.
// Nothing here is a new legal instrument: every retention period (30 / 90 days), every legal basis
// (Art. 6(1)(b) / 6(1)(f)), the single non-EU recipient (Google / Gmail API under the EU-US Data
// Privacy Framework), the FRA1 / Frankfurt hosting claim, the DB-IP credit and the German statutes
// (§ 5 DDG, § 7(1) DDG, § 18(2) MStV, § 25(2)(2) TDDDG) are carried over EXACTLY. DSGVO article
// numbers are written as GDPR (Regolamento UE 2016/679) per Italian usage; the German statutes are
// NOT localised, because they are the law that actually applies to this service. The competent
// supervisory authority stays the German (Hessian) one from OPERATOR — no Garante substitution.
// Register: formal "Lei".
//
// WHY `s6p` IS A GETTER AND NOT A PLAIN VALUE:
// legal.jsx imports ./legal-locales/index.js, which imports this file, which needs OPERATOR back
// from legal.jsx — a module cycle. This file's body runs BEFORE legal.jsx's body, so reading
// `OPERATOR.name` while building the JSX at module scope would hit the const's temporal dead zone
// and throw at import time (a white screen, not a build error). A getter defers the read to render,
// by which point legal.jsx has finished evaluating. The VALUE is still the same JSX element, so the
// shape matches `en` exactly. Do not "simplify" this back into a plain property, and do not copy the
// address in here — OPERATOR is the one place the legal identity lives.
import { OPERATOR } from "../legal.jsx";

// ---------------------------------------------------------------- the Art.13 notice (Assess screen)
export const NOTICE = {
  title: "🇪🇺 Trattamento dei dati",
  p1: (<>Cliccando su <strong>Assess</strong> viene avviata un'analisi su un server nel data center di{" "}
       <strong>Francoforte sul Meno (DE)</strong>. Trattiamo il Suo indirizzo e-mail, il Suo indirizzo
       IP, le marche temporali e l'azienda da Lei richiesta — per erogare il servizio e per rilevare
       attacchi (Art. 6(1)(b) e 6(1)(f) GDPR). I log di sicurezza vengono cancellati automaticamente
       dopo <strong>30 giorni</strong>.</>),
  p2: (<><strong>I Suoi dati restano nell'UE.</strong> Unica eccezione: il Suo indirizzo e-mail viene
       trasmesso all'API Gmail affinché possiamo inviarLe il codice monouso (Google, EU-US Data
       Privacy Framework). L'analisi in sé utilizza esclusivamente fonti pubbliche e non riceve{" "}
       <strong>alcun</strong> dato dell'utente — soltanto il nome dell'azienda oggetto di
       valutazione.</>),
  link: "Informativa sulla privacy", ok: "Ho capito — non mostrare più",
  mini: (<>🇪🇺 I Suoi dati restano nell'UE (Francoforte/FRA1) · e-mail, IP, marche temporali &amp;
         nome dell'azienda sono trattati per erogare il servizio e rilevare attacchi
         (Art. 6(1)(b)/(f) GDPR), log conservati 30 giorni. </>),
};

// ---------------------------------------------------------------- the /impressum page
export const IMPRESSUM = {
  h1: "Note legali (Impressum)", sub: "Informazioni ai sensi del § 5 DDG (legge tedesca sui servizi digitali)",
  s1: "Fornitore del servizio",
  s2: "Contatti",
  s3: "Responsabile dei contenuti ai sensi del § 18(2) MStV",
  s4: "Numero di identificazione IVA",
  s5: "Risoluzione delle controversie",
  s5p: (<>La Commissione europea mette a disposizione una piattaforma per la risoluzione delle
        controversie online (ODR):{" "}
        <a href="https://ec.europa.eu/consumers/odr/" target="_blank" rel="noreferrer">ec.europa.eu/consumers/odr</a>.
        Non siamo disposti né obbligati a partecipare a procedure di risoluzione delle controversie
        dinanzi a un organismo di conciliazione per i consumatori.</>),
  s6: "Responsabilità per i contenuti e i collegamenti",
  s6p: (<>In qualità di fornitore del servizio siamo responsabili dei contenuti propri di queste
        pagine ai sensi delle leggi generali (§ 7(1) DDG). Della responsabilità per i contenuti delle
        pagine esterne collegate risponde sempre il rispettivo fornitore; al momento
        dell'inserimento del collegamento non erano riconoscibili violazioni di legge. Non appena
        veniamo a conoscenza di violazioni, rimuoviamo immediatamente i collegamenti
        corrispondenti.</>),
  s7: "Diritto d'autore",
  s7p: (<>I contenuti e le opere creati dal gestore su queste pagine sono soggetti al diritto d'autore
        tedesco. I documenti di analisi prodotti da cybergod.ai sono materiale di vendita interno e
        non sono destinati alla diffusione pubblica.</>),
  note: "Nota: cybergod.ai è uno strumento interno ad accesso limitato per l'analisi cyber in fase di pre-vendita; non è aperto all'uso da parte del pubblico.",
  todo: "⚠ Queste note legali sono ancora incomplete. Prima della pubblicazione occorre inserire nome, indirizzo postale e numero di telefono in OPERATOR (src/legal.jsx) — in Germania un Impressum incompleto è perseguibile.",
};

// ---------------------------------------------------------------- the /contact page
export const CONTACT = {
  h1: "Contatti", sub: "Una linea diretta — nessun modulo, nessuna attesa",
  lead: "Domande sull'accesso, su un'analisi, sulla protezione dei dati o su una collaborazione? Ci scriva direttamente.",
  email: "E-mail", emailD: "Per l'accesso, le richieste in materia di protezione dei dati e qualsiasi questione commerciale. Di norma risposta nella stessa giornata lavorativa.",
  li: "LinkedIn", liD: "La via più rapida per una presentazione professionale.",
  wa: "WhatsApp", waD: "La via più rapida. Direttamente sul telefono, di norma risposta in pochi minuti.",
  tg: "Telegram", tgD: "Messaggio diretto — la stessa piattaforma su cui girano i bot di assessment.",
  gh: "GitHub", ghD: "Background tecnico e progetti.",
  access: "Richiedere l'accesso",
  accessD: "cybergod.ai è ad accesso limitato: è necessario un indirizzo e-mail partner autorizzato. Nel messaggio indichi la Sua azienda e l'indirizzo da abilitare.",
  legal: "Note legali: ", soon: "canale in arrivo",
};

// ---------------------------------------------------------------- the /privacy page
export const PRIVACY = {
  h1: "Privacy e trattamento dei dati", sub: "Datenschutz & Datenverarbeitung — cybergod.ai",
  lead: "La versione tedesca di questa informativa è il testo giuridicamente vincolante; la presente traduzione italiana è fornita unicamente per agevolarne la lettura. cybergod.ai è uno strumento interno per l'analisi cyber in fase di pre-vendita. Questa pagina descrive quali dati trattiamo, su quale base giuridica, dove sono conservati e per quanto tempo li conserviamo — ai sensi degli Art. 13/14 GDPR.",
  s1: "1. Dove si trovano i Suoi dati",
  s1p: (<><strong>I Suoi dati personali restano nell'UE.</strong> L'applicazione, il database, le
       sessioni, i documenti generati e i log di sicurezza girano tutti su un unico server nel{" "}
       <strong>data center di Francoforte sul Meno, Germania (DigitalOcean, regione FRA1)</strong>.
       Non esiste alcuna replica e alcun backup al di fuori dell'UE.</>),
  s1sub: "Responsabili del trattamento (Art. 28 GDPR):",
  s1list: [
    (<><strong>DigitalOcean</strong> — hosting del server, regione di Francoforte (FRA1), UE.</>),
    (<><strong>Google (API Gmail)</strong> — recapita il codice monouso (OTP) al Suo indirizzo e-mail
       e recapita al gestore le notifiche operative e di sicurezza. Tali notifiche possono contenere{" "}
       <strong>metadati tecnici relativi a un accesso (indirizzo IP, Paese, browser/dispositivo,
       pagina richiesta)</strong>, affinché il gestore possa verificare accessi ed eventi di
       sicurezza (Art. 6(1)(f) GDPR). Google è certificata secondo l'EU-US Data Privacy Framework
       (Art. 45 GDPR). Non viene trasmesso alcun contenuto delle analisi.</>),
    (<><strong>Telegram</strong> — solo se utilizza l'accesso opzionale via Telegram; in tal caso
       rileva il Suo ID utente Telegram.</>),
  ],
  s1note: (<>L'analisi in sé valuta esclusivamente <strong>dati di infrastruttura pubblicamente
           visibili dell'azienda oggetto di valutazione</strong> (Shodan, RIPE, CAIDA, PeeringDB,
           crt.sh) e redige i testi del report tramite un endpoint di IA. A tali servizi vengono
           trasmessi <strong>solo il nome dell'azienda oppure il dominio/ASN del bersaglio</strong>,
           ovvero il riscontro tecnico — <strong>nessun identificativo utente, nessun indirizzo
           e-mail, nessun indirizzo IP di un utente</strong>. Essi non sono pertanto destinatari dei
           Suoi dati personali.</>),
  s2: "2. Quali dati trattiamo",
  th: ["Dati", "Finalità", "Base giuridica", "Conservazione"],
  rows: [
    ["Indirizzo e-mail (accesso, OTP)", "Controllo degli accessi, autenticazione a due fattori",
     "Art. 6(1)(b) — contratto/utilizzo; Art. 6(1)(f) — sicurezza", "Per tutta la durata dell'accesso"],
    ["Indirizzo IP, marca temporale, user-agent, dispositivo/browser, Paese",
     "Rilevamento di attacchi (DDoS, brute force, scanner), prevenzione degli abusi, esercizio",
     "Art. 6(1)(f) — legittimo interesse alla sicurezza informatica (considerando 49)",
     "30 giorni (conservazione dei log), poi cancellazione automatica"],
    ["Aziende richieste, lingua, momento, documenti generati",
     "Erogazione dell'analisi, attribuzione dei costi, tracciabilità",
     "Art. 6(1)(b), Art. 6(1)(f)", "90 giorni, ovvero fino alla cancellazione da parte dell'utente"],
    ["Segnalazioni di sicurezza (regola, oggetto, dati forensi)", "Risposta agli incidenti", "Art. 6(1)(f)", "30 giorni"],
  ],
  s2note: (<><strong>Nessun</strong> cookie pubblicitario, <strong>nessun</strong> tracciamento tra
           siti diversi, <strong> nessuna</strong> profilazione, <strong>nessuna</strong> decisione
           automatizzata con effetti giuridici (Art. 22). L'unico cookie impostato è un cookie di
           sessione strettamente necessario (§ 25(2)(2) TDDDG — non soggetto a consenso).</>),
  s3: "3. Minimizzazione dei dati (Art. 5(1)(c))",
  s3list: [
    (<>Geolocalizzazione <strong>solo a livello di Paese</strong> — nessuna città, nessuna coordinata.
       Database locale offline, nessuna interrogazione presso terzi.</>),
    (<>I file statici (CSS/immagini) non vengono registrati nei log.</>),
    (<>Gli indirizzi IP possono essere conservati dal gestore in forma <strong>hash</strong>
       (<code>TELEMETRY_HASH_IPS=1</code>): la correlazione resta possibile, l'identificativo
       decade.</>),
    (<>I bersagli delle analisi sono <strong>aziende</strong>, non persone fisiche. Vengono valutati
       esclusivamente dati di infrastruttura pubblicamente visibili — <strong>non viene effettuata
       alcuna scansione attiva</strong>.</>),
  ],
  s4: "4. I Suoi diritti (Art. 15–21 GDPR)",
  s4p: (<>Accesso, rettifica, cancellazione, limitazione, portabilità e il{" "}
        <strong>diritto di opporsi al trattamento fondato sul legittimo interesse</strong>. Richieste
        a <a href="mailto:feranicus@s4biz.io">feranicus@s4biz.io</a> — risposta entro un mese
        (Art. 12(3)). Ha inoltre il diritto di proporre reclamo a un'autorità di controllo
        (Art. 77).</>),
  s5: "5. Sicurezza (Art. 32 GDPR)",
  s5list: [
    "Cifratura TLS per l'intero trasporto; rinnovo automatico dei certificati.",
    "Accesso zero trust: identità in allow-list + password condivisa + codice monouso via e-mail.",
    "I documenti sono vincolati al proprietario — può leggerli solo l'utente che li ha generati.",
    "Rilevamento continuo degli attacchi con allarmi (brute force, DDoS, scanner, esfiltrazione).",
    "Aggiornamenti di sicurezza del server regolari e automatizzati.",
  ],
  s6: "6. Titolare del trattamento",
  // getter — see the header comment (module cycle: OPERATOR is read at render, not at import).
  get s6p() {
    return (<>Titolare del trattamento ai sensi del GDPR è <strong>{OPERATOR.name}</strong>,{" "}
           {OPERATOR.street}, {OPERATOR.zipCity}, {OPERATOR.country} —{" "}
           <a href={"mailto:" + OPERATOR.email}>{OPERATOR.email}</a>. Indicazioni complete nelle{" "}
           <a href="/impressum">note legali</a>. Uso interno per il settore vendite; i documenti
           generati sono materiale di vendita interno. Ha il diritto di proporre reclamo a
           un'autorità di controllo per la protezione dei dati (Art. 77 GDPR); l'autorità competente
           è <strong>{OPERATOR.authority}</strong>.</>);
  },
  credit: "Corrispondenza IP-Paese: ", disclaimerT: "Nota: ",
  disclaimer: "Questo testo descrive l'effettivo trattamento tecnico. Non costituisce consulenza legale e dovrebbe essere esaminato da un responsabile della protezione dei dati prima di una pubblicazione esterna.",
};
