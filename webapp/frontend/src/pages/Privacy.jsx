// Privacy / Datenschutz — reachable at /privacy and linked from the Assess notice.
// NOTE FOR WHOEVER MAINTAINS THIS: the residency claims below are deliberately SPECIFIC about what
// stays in Frankfurt and HONEST about what leaves the EU. Do not "simplify" it to "all data stays in
// the EU" — that would be false (Shodan, the LLM endpoint and Gmail are outside the droplet), and a
// false residency claim on a site that SELLS DSGVO assessments is the worst possible own goal.
export default function Privacy() {
  return (
    <div className="legal">
      <h1 className="page-h">Datenschutz &amp; Datenverarbeitung</h1>
      <p className="page-sub">Privacy &amp; data processing — cybergod.ai</p>

      <div className="panel legal-body">
        <p className="legal-lead">
          cybergod.ai ist ein internes Werkzeug für die Cyber-Pre-Sales-Analyse. Diese Seite
          beschreibt, welche Daten wir verarbeiten, auf welcher Rechtsgrundlage, wo sie liegen und
          wie lange wir sie aufbewahren — gemäß DSGVO/GDPR Art. 13/14.
        </p>

        <h2>1. Wo Ihre Daten liegen</h2>
        <p>
          <strong>Ihre personenbezogenen Daten bleiben in der EU.</strong> Anwendung, Datenbank,
          Sitzungen, erzeugte Dokumente und Sicherheits­protokolle laufen ausschließlich auf einem
          Server im <strong>Rechenzentrum Frankfurt am Main, Deutschland (DigitalOcean, Region
          FRA1)</strong>. Es gibt keine Replikation und kein Backup außerhalb der EU.
        </p>
        <p>
          <strong>Auftragsverarbeiter (Art. 28 DSGVO):</strong>
        </p>
        <ul>
          <li><strong>DigitalOcean</strong> — Hosting des Servers, Region Frankfurt (FRA1), EU.</li>
          <li><strong>Google (Gmail API)</strong> — <em>die einzige Stelle, an die eine
              Nutzer­kennung übermittelt wird</em>: Ihre E-Mail-Adresse, ausschließlich für den
              Versand des Einmalcodes (OTP) und der Betriebs­berichte an den Betreiber. Google ist
              nach dem EU-US Data Privacy Framework zertifiziert (Art. 45 DSGVO — Angemessenheits­beschluss).
              Übermittelt wird die Adresse und der Code — sonst nichts.</li>
          <li><strong>Telegram</strong> — nur, wenn Sie den optionalen Telegram-Zugang nutzen; dann
              gilt Ihre Telegram-Nutzer-ID.</li>
        </ul>
        <p className="legal-note">
          Die Analyse selbst wertet ausschließlich <strong>öffentlich sichtbare Infrastruktur­daten
          des zu bewertenden Unternehmens</strong> aus (Shodan, RIPE, CAIDA, PeeringDB, crt.sh) und
          erzeugt die Berichtstexte über einen KI-Endpunkt. Diesen Diensten wird <strong>nur der
          Firmenname bzw. die Domain/ASN des Analyse-Ziels</strong> bzw. der technische Befund
          übergeben — <strong>keine Nutzer­kennung, keine E-Mail-Adresse, keine IP-Adresse eines
          Nutzers</strong>. Sie sind daher keine Empfänger Ihrer personenbezogenen Daten.
        </p>

        <h2>2. Welche Daten wir verarbeiten</h2>
        <table className="legal-table">
          <thead><tr><th>Daten</th><th>Zweck</th><th>Rechtsgrundlage</th><th>Aufbewahrung</th></tr></thead>
          <tbody>
            <tr><td>E-Mail-Adresse (Anmeldung, OTP)</td><td>Zugangskontrolle, Zwei-Faktor-Authentifizierung</td>
                <td>Art. 6(1)(b) — Vertrag/Nutzung; Art. 6(1)(f) — Sicherheit</td><td>Dauer des Zugangs</td></tr>
            <tr><td><strong>IP-Adresse</strong>, Zeitstempel, User-Agent, Gerät/Browser, Land</td>
                <td>Angriffserkennung (DDoS, Brute-Force, Scanner), Missbrauchs­abwehr, Betrieb</td>
                <td><strong>Art. 6(1)(f)</strong> — berechtigtes Interesse an IT-Sicherheit (ErwG 49)</td>
                <td><strong>30 Tage</strong> (Log-Retention), danach automatisch gelöscht</td></tr>
            <tr><td>Angefragte Unternehmen, Sprache, Zeitpunkt, erzeugte Dokumente</td>
                <td>Bereitstellung der Analyse, Kostenzuordnung, Nachvollziehbarkeit</td>
                <td>Art. 6(1)(b), Art. 6(1)(f)</td><td>90 Tage bzw. bis zur Löschung durch den Nutzer</td></tr>
            <tr><td>Sicherheits­meldungen (Regel, Betreff, Forensik)</td><td>Incident Response</td>
                <td>Art. 6(1)(f)</td><td>30 Tage</td></tr>
          </tbody>
        </table>
        <p>
          <strong>Keine</strong> Werbe-Cookies, <strong>kein</strong> Tracking über Websites hinweg,
          <strong>kein</strong> Profiling, <strong>keine</strong> automatisierte Entscheidung mit
          Rechtswirkung (Art. 22). Gesetzt wird ausschließlich ein technisch notwendiges
          Session-Cookie (Art. 25(2) TTDSG § 25 Abs. 2 Nr. 2 — einwilligungsfrei).
        </p>

        <h2>3. Datenminimierung (Art. 5(1)(c))</h2>
        <ul>
          <li>Geolokalisierung nur auf <strong>Länderebene</strong> — keine Stadt, keine Koordinaten.
              Lokale Offline-Datenbank, keine Abfrage bei Dritten.</li>
          <li>Statische Dateien (CSS/Bilder) werden nicht protokolliert.</li>
          <li>IP-Adressen können betreiberseitig <strong>gehasht</strong> gespeichert werden
              (<code>TELEMETRY_HASH_IPS=1</code>): Korrelation bleibt möglich, die Kennung entfällt.</li>
          <li>Analyse-Ziele sind <strong>Unternehmen</strong>, keine natürlichen Personen. Es werden
              ausschließlich öffentlich sichtbare Infrastruktur­daten ausgewertet — es findet
              <strong>kein aktives Scannen</strong> statt.</li>
        </ul>

        <h2>4. Ihre Rechte (Art. 15–21 DSGVO)</h2>
        <p>
          Auskunft, Berichtigung, Löschung, Einschränkung, Datenübertragbarkeit sowie
          <strong> Widerspruch gegen die Verarbeitung auf Grundlage berechtigter Interessen</strong>.
          Anfragen an <a href="mailto:feranicus@s4biz.io">feranicus@s4biz.io</a> — Antwort innerhalb
          eines Monats (Art. 12(3)). Beschwerderecht bei einer Aufsichtsbehörde (Art. 77).
        </p>

        <h2>5. Sicherheit (Art. 32 DSGVO)</h2>
        <ul>
          <li>TLS-Verschlüsselung für den gesamten Transport; automatische Zertifikats­erneuerung.</li>
          <li>Zero-Trust-Zugang: zugelassene Identität + gemeinsames Passwort + E-Mail-Einmalcode.</li>
          <li>Dokumente sind eigentümer­gebunden — Zugriff nur durch den erzeugenden Nutzer.</li>
          <li>Kontinuierliche Angriffserkennung mit Alarmierung (Brute-Force, DDoS, Scanner, Exfiltration).</li>
          <li>Regelmäßige, automatisierte Sicherheits-Updates des Servers.</li>
        </ul>

        <h2>6. Verantwortlicher</h2>
        <p>
          Betreiber dieser Instanz: <a href="mailto:feranicus@s4biz.io">feranicus@s4biz.io</a> (S4BIZ).
          Interne Nutzung für Colt-Pre-Sales. Die erzeugten Dokumente sind internes Vertriebsmaterial.
        </p>

        <p className="legal-foot">
          IP-zu-Land-Zuordnung: <a href="https://db-ip.com" rel="noreferrer" target="_blank">IP Geolocation by DB-IP</a> (CC BY 4.0).
        </p>
        <p className="legal-foot">
          <strong>Hinweis:</strong> Dieser Text beschreibt die tatsächliche technische Verarbeitung.
          Er ist keine Rechtsberatung und sollte vor externer Veröffentlichung von einer/einem
          Datenschutzbeauftragten geprüft werden.
        </p>
      </div>
    </div>
  );
}
