// partners-locales/de.js — die deutsche Übersetzung von en.js.
//
// en.js IST DIE REFERENZ. Diese Datei enthält ausschließlich übersetzten Text: dieselben Exporte
// (`meta`, `arts`, `sections`), dieselben Schlüssel, dieselbe Reihenfolge der Abschnitts-Ids,
// dieselbe Anzahl Spalten und dieselbe Anzahl Aufzählungspunkte. Die Objektform wird von
// `tools/partners_gate.mjs` geprüft, eine Abweichung ist ein fehlgeschlagener Build.
//
// NICHT ÜBERSETZT, weil es Nachschlageschlüssel sind: jedes `id`, jedes `group`, jedes `accent`,
// jedes `k` in `change.cells` und `arts[].n`. Einen Nachschlageschlüssel zu übersetzen lässt Inhalt
// stillschweigend verschwinden. Alles andere ist Inhalt und ist übersetzt.
//
// KEINE LANGEN GEDANKENSTRICHE, KEINE HTML-ENTITÄTEN, KEINE PREISE. Kaufmännische Konditionen
// werden direkt vereinbart und stehen bewusst auf keiner öffentlichen Seite.

export const meta = {
  docTitle: "Für wen es gedacht ist",
  kicker: "Ein Name hinein. Vier vorstandsreife Dokumente heraus. Elf Zielgruppen.",
  h1a: "Geben Sie einen Firmennamen ein.",
  h1b: "Sie erhalten das ",
  h1c: "vollständige Risikobild",
  h1d: " in wenigen Minuten.",
  lede:
    "An das untersuchte Unternehmen wird kein einziges Datenpaket gesendet. Alles entsteht aus " +
    "Quellen, die für jede Recherche rechtmäßig zugänglich sind. Es gibt also nichts zu " +
    "installieren, niemanden um Erlaubnis zu fragen und keinen Fragebogen abzuwarten. Vier " +
    "Dokumente kommen jedes Mal zurück.",
  artsNote:
    "Hinzu kommt ein fünftes Dokument: ein einzelner, in sich geschlossener Webbericht, der alle " +
    "vier vereint und sich in jedem Browser öffnet. Dieses Dokument wird intern am häufigsten " +
    "weitergeleitet. Jedes Dokument ist auf Englisch, Deutsch oder Russisch verfügbar.",
  railTitle: "Für wen es gedacht ist",
  groupPartners: "Partner",
  groupBuyers: "Kunden",
  groupEngage: "Formen der Zusammenarbeit",
  foot:
    "Die Inhalte stammen aus den Briefing-Unterlagen für Partner und Aufsichtsbehörden sowie aus " +
    "den unterzeichneten Vertragsunterlagen. Preise, Rabatte, Nutzerzahlen oder Zusagen erscheinen " +
    "bewusst an keiner Stelle. Die genannten Terminzahlen der Partner sind deren eigene Angaben " +
    "und hängen von der einzelnen Vertriebsperson ab. Die Ergebnisse der Analyse sind keine " +
    "Rechtsberatung. Alle Hinweise auf identifizierbare Kunden wurden entfernt.",
};

export const arts = [
  { n: "1", name: "Feststellungen", body:
    "Jeder aus dem Internet erreichbare Angriffspunkt, eingestuft von Kritisch bis Niedrig. Jede " +
    "Feststellung nennt, worum es geht, warum sie zählt, wie sie behoben wird, und die genaue " +
    "Adresse und den Port, auf dem sie gesehen wurde." },
  { n: "2", name: "Risiko in Geld", body:
    "Dieselben Feststellungen, ausgedrückt in Geld, nach der anerkannten Methode Factor Analysis " +
    "of Information Risk. Kosten eines einzelnen Vorfalls, schlimmster Fall pro Jahr und eine " +
    "Kurve, die fällt, sobald Feststellungen geschlossen werden. Geschrieben für den " +
    "Finanzvorstand." },
  { n: "3", name: "Bedrohungsakteure", body:
    "Welche Angreifer für diese Branche und diese Länder tatsächlich relevant sind und wie sie " +
    "vorgehen. Die Antwort auf die Frage des Vorstands, wer es auf uns abgesehen hätte." },
  { n: "4", name: "Compliance", body:
    "Feststellungen, zugeordnet zu den Klauseln der Gesetze, die am Sitz des Unternehmens gelten, " +
    "mit den echten Fristen. Heute Europäische Union und Kanada." },
];

export const sections = [
  // ------------------------------------------------------------------ MANAGED SERVICE PROVIDERS
  {
    id: "msp", group: "partners", nav: "Managed Service Provider",
    eyebrow: "Partner", h2: "Für Managed Service Provider",
    scr: {
      s: "Sie betreiben Sicherheit für viele Kunden gleichzeitig, mit einem Team, das nicht so schnell wachsen kann wie Ihre Kundenliste.",
      c: "Die Exposition eines einzelnen Kunden von Hand zu prüfen kostet etwa einen Analystentag. In der Breite geschieht das deshalb nicht, und das Quartalsgespräch wird zum Statusbericht, für den niemand ein Budget einplant.",
      a: "Bewerten Sie jeden Kunden in Ihrem Bestand nach demselben Rhythmus, zu Kosten, die nicht mit der Kundenzahl steigen. Verkaufen Sie die Behebung anschließend auf vier getrennten Preisstufen.",
    },
    cols: [
      { h: "1. Was Sie verkaufen", li: [
        "Die Analyse selbst, bepreist, unter Ihrem eigenen Namen.",
        "Eine monatliche oder quartalsweise Wiederholung mit einem Bericht über das, was sich verändert hat. Dieser Bericht ist der Managed Service.",
        "Lizenzen, verkauft in Paketen oder als unbegrenzte Nutzung, an denen Sie eigenständig verdienen.",
      ] },
      { h: "2. Warum die Kostenrechnung aufgeht", li: [
        "Eine einzige Fachkraft deckt Ihren gesamten Kundenbestand ab statt eines einzelnen Kunden.",
        "Der Start bei einem Kunden verlangt von diesem nichts: keine Software, keinen Zugang, kein Formular.",
        "Das Compliance-Dokument beantwortet den Prüfer im selben Durchlauf, ein zweites Projekt muss also nicht besetzt werden.",
      ] },
      { h: "3. Wo die Marge liegt", li: [
        "Nicht im Bericht. In den vier Wegen, eine Feststellung zu schließen, unten dargestellt.",
        "Ihre Account Manager gewinnen einen Anlass, jeden Kunden jeden Monat mit Neuigkeiten anzurufen.",
        "Eine geschlossene Feststellung belegt, dass der Retainer wirkt. Das ist der schwierigste Nachweis in der Sicherheit.",
      ] },
    ],
    ladder: { h: "Die vier Wege, eine Feststellung zu schließen, der günstigste zuerst", items: [
      { b: "Beratung.", t: "Ein Workshop, der jede Feststellung gegen das prüft, was der Kunde bereits besitzt." },
      { b: "Ohne neue Ausgaben, mit vorhandener Technik.", t: "Die meisten Feststellungen schließen sich über Konfiguration, Platzierung und geänderte Abläufe auf Produkten, für die der Kunde ohnehin zahlt. Sie liefern eine Liste von Maßnahmen, jede dem Werkzeug zugeordnet, das sie schließt." },
      { b: "Open Source.", t: "Wo vorhandene Technik die Lücke nicht schließen kann, ein Entwurf auf Open-Source-Basis statt eines Kaufs. Es gibt keine Lizenz zu erwerben. Der Aufwand verlagert sich auf Wissen und Betrieb, das der Kunde entweder einstellt oder bei Ihnen einkauft." },
      { b: "Ein kommerzielles Produkt.", t: "Nur dort, wo keiner der vorigen Wege trägt. Die Auswahl bleibt innerhalb der freigegebenen Lieferantenliste des Kunden. Sie beraten zu Passung, Reihenfolge und Integration." },
    ] },
    win: { h: "Die Aussage, klar benannt", p:
      "Ein einzelner Bericht ist ein Projekt. Ein monatlicher Bericht über das, was sich verändert " +
      "hat, ist ein Abonnement. Sie verkaufen die Feststellung und den Weg zu ihrer Behebung, auf " +
      "vier Preisstufen, an einen Kunden, der Ihnen bereits vertraut." },
    steps: [
      { k: "Woche 1", v: "Lassen Sie Ihre zehn größten Kunden laufen und lesen Sie, was zurückkommt." },
      { k: "Woche 2", v: "Schicken Sie jedem eine einzelne Feststellung. Die Methode finden Sie unten." },
      { k: "Woche 3", v: "Setzen Sie Ihre Marke darauf und preisen Sie es in Ihre Managed-Service-Stufe ein." },
    ],
    cta: { btn: "Sprechen Sie mit uns", txt: "Lizenzpakete, unbegrenzte Modelle, Stufen und Konditionen sind kaufmännische Themen. Fragen Sie uns." },
  },

  // ------------------------------------------------------------------------------- RESELLERS
  {
    id: "var", group: "partners", nav: "Reseller",
    eyebrow: "Partner", h2: "Für Reseller",
    scr: {
      s: "Sie verkaufen Technologie und gewinnen über Beziehung, Zeitpunkt und die Qualität des Gesprächs, das Sie eröffnen können.",
      c: "Der erste technische Termin ist am schwersten zu bekommen. Der übliche Ersatz ist ein Rabatt. Der kostet Sie Marge und erzieht den Kunden dazu, auf den nächsten zu warten.",
      a: "Gehen Sie in den Termin und wissen Sie bereits, was an ihrem Perimeter offen liegt. Berechnen Sie die Analyse angemessen und rechnen Sie ihren Wert dann auf die Arbeit an, die sie aufgedeckt hat.",
    },
    cols: [
      { h: "1. Wie es bepreist wird", li: [
        "Die Analyse ist ein bezahltes Projekt mit festem Umfang. Sie ist keine Zugabe.",
        "Ihr Wert wird anschließend auf die folgende Beratung oder Behebung angerechnet.",
        "Der Kunde riskiert damit nichts, und Sie werden in beiden Fällen bezahlt.",
      ] },
      { h: "2. Woran Sie außerdem verdienen", li: [
        "Lizenzen, in Paketen oder als unbegrenzte Nutzung, als zweite und wiederkehrende Position.",
        "Alle vier Wege, eine Feststellung zu schließen: Beratung, vorhandene Technik, Open Source oder ein freigegebenes Produkt.",
        "Wiederholungsläufe, die zeigen, was sich verändert hat, und das Gespräch nach Plan wieder eröffnen.",
      ] },
      { h: "3. Was Ihr Vertrieb gewinnt", li: [
        "Einen Anlass, jeden anzurufen, und etwas Konkretes zu sagen.",
        "Neue Kunden: Sie brauchen weder Erlaubnis noch Zugang und können die Arbeit tun, bevor Sie eingeladen werden.",
        "Bestandsschutz: Lassen Sie es vor dem Verlängerungstermin eines Wettbewerbers laufen und zeigen Sie, was sich verändert hat.",
      ] },
    ],
    win: { h: "Die Aussage, klar benannt", p:
      "Ein Rabatt kauft einen Abschluss. Mehr über den Perimeter zu wissen als der Kunde selbst " +
      "kauft die Beziehung, und diesmal werden Sie für die Arbeit bezahlt, die Sie hineingebracht hat." },
    steps: [
      { k: "Tag 1", v: "Wählen Sie fünf Interessenten, bei denen Sie keinen Termin bekommen." },
      { k: "Tag 2", v: "Schicken Sie jedem eine einzelne Feststellung. Niemals den Bericht." },
      { k: "Tag 5", v: "Nehmen Sie den Termin wahr. Bepreisen Sie die Analyse. Rechnen Sie sie an." },
    ],
    cta: { btn: "Sprechen Sie mit uns", txt: "Vermittlung, Wiederverkauf, Lizenzen und White-Label sind alle möglich. Konditionen auf Anfrage." },
  },

  // ------------------------------------------------------------------------------ THE METHOD
  {
    id: "play", group: "partners", nav: "Die Eröffnungsmethode", accent: "gold",
    eyebrow: "Das nutzt jeder Partner", h2: "Schicken Sie eine Feststellung. Halten Sie den Bericht zurück.",
    scr: {
      s: "Sie haben die Analyse laufen lassen und halten ein Dokument mit allem darin in der Hand.",
      c: "Ein Interessent, der keinen Bericht angefordert hat, liest ihn als Verkaufsunterlage und legt ihn zur Seite. Ein vollständiger Bericht verlangt außerdem einen Termin, den in diesem Quartal niemand frei hat.",
      a: "Schicken Sie genau eine Feststellung, mit ihrem Nachweis und dem Weg zur Behebung. Die einzelne Feststellung gewinnt Ihnen den Termin. Der Bericht ist das, was Sie darin verkaufen.",
    },
    quote: {
      q: "Diese Adresse sehe ich in unserem Bestandsverzeichnis überhaupt nicht.",
      by: "Ein Ingenieur für Netzwerksicherheit in einem großen regulierten Unternehmen, während " +
          "eines laufenden Durchlaufs. Die Plattform hatte eine Adresse zutage gefördert, die " +
          "seiner eigenen Organisation zugeordnet war. Im internen Bestandsverzeichnis konnte er " +
          "sie nicht finden. Unternehmen, Branche und Details zurückgehalten.",
    },
    cols: [
      { h: "So gehen Sie vor", li: [
        "Lassen Sie die Analyse laufen, lesen Sie die Feststellungen und wählen Sie genau eine aus.",
        "Schicken Sie diese Feststellung, mit dem Nachweis und dem Rat zur Behebung.",
        "Hängen Sie den Bericht nicht an. Entfernen Sie identifizierende Details, wenn die Ansprache kalt ist.",
        "Bitten Sie um dreißig Minuten, um den Rest gemeinsam durchzugehen.",
      ] },
      { h: "Warum eine Feststellung stärker wirkt als ein Bericht", li: [
        "**Ein unbekanntes System ist die stärkste Form der Feststellung.** Eine Adresse außerhalb des Bestandsverzeichnisses liegt außerhalb von Patch-Management, Scans und Berichtswesen, und die Bestandsführung steht am Anfang jedes Sicherheitsstandards, gegen den geprüft wird.",
        "**Sie hält Skepsis stand.** Auf eine bekannte Feststellung folgt \"dafür ist ein anderes Team zuständig\". Eine Adresse, die niemand erklären kann, lässt sich so nicht beantworten.",
        "**Sie passt in den Raum.** Sie landet bei dem Team, mit dem Sie ohnehin sprechen, nicht bei einer Abteilung, über die im Termin niemand verfügt.",
        "**Sie bepreist sich selbst.** Ein einzelner ungemanagter Host am Internet ist billig zu diskutieren und teuer zu ignorieren.",
      ] },
    ],
    win: { h: "Was Partner berichten", p:
      "Partner in Deutschland und der Schweiz, die diese Methode nutzen, berichten von sechs bis " +
      "zehn neuen Erstterminen pro Vertriebsmitarbeiter und Woche. Das hängt erkennbar davon ab, " +
      "wie gut die einzelne Person eine Tatsache in ein Gespräch verwandelt. Deshalb hören Sie es " +
      "besser von den Partnern selbst. Wir stellen den Kontakt her." },
    cta: { btn: "Referenzgespräch anfragen", ghost: true, txt: "Referenzpartner im deutschsprachigen Markt verfügbar." },
  },

  // --------------------------------------------------------------------- SYSTEMS INTEGRATORS
  {
    id: "gsi", group: "partners", nav: "Systemintegratoren",
    eyebrow: "Partner", h2: "Für Systemintegratoren",
    scr: {
      s: "Die Bestandsaufnahme ist die erste Phase jedes Sicherheits- und Transformationsprogramms, das Sie führen.",
      c: "Sie wird zu Beratersätzen abgerechnet, von Hand erledigt, ist in jedem Projekt anders und steht auf der Rechnung, über die Kunden streiten. Ohne sie ist jedoch nichts gültig, was danach kommt.",
      a: "Machen Sie die Bestandsaufnahme zu einem festen, schnellen und in jedem Projekt gleichen Schritt. So wandert Ihre Marge dorthin, wo sie hingehört: in Architektur und Behebung.",
    },
    cols: [
      { h: "1. Wo sie in der Methodik sitzt", li: [
        "Die Bestandsaufnahme wird zur Eingabe für Ihre Methodik, nicht zu deren Ersatz.",
        "Eine Ausgangsmessung zu Programmbeginn, dann eine Wiederholung an jedem Meilenstein.",
        "Fortschritt wird durch Geschlossenes belegt, statt im Statusbericht behauptet.",
      ] },
      { h: "2. Wo sie außerdem greift", li: [
        "Einen Lieferanten bewerten, ohne auf dessen Mitwirkung zu warten.",
        "Ein neu erworbenes Unternehmen erfassen, bevor sein Netz mit dem der Mutter verbunden wird.",
        "Jedes Land und jede Tochtergesellschaft ohne eigenes Team vor Ort.",
      ] },
      { h: "3. Was sich kaufmännisch ändert", li: [
        "Sie verkaufen nicht mehr Wochen der Faktensuche, sondern das Ergebnis, das sie blockiert hat.",
        "Das Dokument zum Risiko in Geld bepreist das Programm am ersten Tag in der Sprache des Finanzvorstands.",
        "Jede Feststellung trägt ihren Nachweis und hält damit der technischen Prüfung des Kunden stand.",
      ] },
    ],
    win: { h: "Die Aussage, klar benannt", p:
      "Die erste Rechnung ist nicht länger die, über die Ihr Kunde streitet, denn sie kauft jetzt " +
      "eine Antwort statt einer Tätigkeit." },
    steps: [
      { k: "Schritt 1", v: "Lassen Sie es in einem laufenden Projekt mitlaufen und vergleichen Sie mit dem, was Ihr Team von Hand gefunden hat." },
      { k: "Schritt 2", v: "Nehmen Sie es in Ihr Standardergebnis der Bestandsaufnahme auf." },
      { k: "Schritt 3", v: "Setzen Sie Ihre Marke darauf oder binden Sie es ein. Beide Modelle finden Sie am Ende." },
    ],
    cta: { btn: "Sprechen Sie mit uns", txt: "Mengen-, Regional- und Integrationskonditionen sind kaufmännische Themen. Fragen Sie uns." },
  },

  // ------------------------------------------------------------------------------- VENDORS
  {
    id: "vendors", group: "partners", nav: "Cybersicherheitsanbieter",
    eyebrow: "Partner", h2: "Für Cybersicherheitsanbieter",
    scr: {
      s: "Sie haben ein Produkt, das ein echtes Problem löst, und eine Vorführung, die es in Aktion zeigt.",
      c: "Ihre Vorführung belegt, dass das Produkt grundsätzlich funktioniert. Sie belegt nicht, dass dieser Kunde das Problem heute hat. Die Bewertung fällt deshalb in einen Funktionsvergleich mit einem Wettbewerber zurück.",
      a: "Zeigen Sie dem Interessenten, was an seinem eigenen Perimeter offen liegt, bevor Sie ihm Ihr Produkt zeigen. Lassen Sie es nach der Einführung erneut laufen und zeigen Sie in Geld, was Ihr Produkt geschlossen hat.",
    },
    cols: [
      { h: "1. In Ihrem eigenen Vertrieb", li: [
        "Jeder Account Manager trägt ein Expositionsbild, das genau zu diesem Kunden gehört.",
        "Es öffnet Türen bei Unternehmen, die noch nie von Ihnen gehört haben, ganz ohne Zugang.",
        "Das Dokument zum Risiko in Geld macht aus einer technischen Exposition eine Budgetposition.",
      ] },
      { h: "2. In Ihrem Produkt", li: [
        "Externe Exposition wird zu einer Funktion Ihrer Plattform, geliefert über unsere Programmierschnittstelle.",
        "Ihre Oberfläche, Ihre Marke, kein zweites Produkt, das der Kunde bewerten muss.",
        "Es ergänzt eine Außensicht in einem Produkt, das überwiegend nach innen schaut. Das ist eine echte Lücke in den meisten Sicherheitsarchitekturen.",
      ] },
      { h: "3. Neben Ihrem Produkt", li: [
        "Lassen Sie es vor und nach der Einführung laufen. Der Unterschied ist Ihre Referenzgeschichte.",
        "Es gibt Verlängerungen eine Zahl statt eines Gefühls.",
        "Sie können Lizenzen auch neben Ihren eigenen Produkten weiterverkaufen.",
      ] },
    ],
    win: { h: "Die Aussage, klar benannt", p:
      "Niemand streitet über die eigene Angriffsfläche. Sie ist der kürzeste Weg von einer " +
      "Vorführung zu einem Budget." },
    steps: [
      { k: "Prüfen", v: "Lassen Sie es gegen drei Ihrer eigenen offenen Chancen laufen." },
      { k: "Entscheiden", v: "Vertriebswerkzeug, Handelsposition oder Funktion Ihrer Plattform." },
      { k: "Integrieren", v: "Feststellungen erreichen Ihr Produkt über die Programmierschnittstelle." },
    ],
    cta: { btn: "Sprechen Sie mit uns", txt: "Integrations- und Lizenzkonditionen hängen von Menge und Integrationstiefe ab. Fragen Sie uns." },
  },

  // ---------------------------------------------------------------------------- CONSULTING
  {
    id: "consulting", group: "partners", nav: "Beratungshäuser",
    eyebrow: "Partner", h2: "Für Beratungshäuser",
    scr: {
      s: "Sie verkaufen Urteilskraft und Unabhängigkeit. Kunden zahlen für den Rat und für den Namen auf dem Deckblatt.",
      c: "Die Faktensuche verbraucht den größten Teil des Projekts und ist der Teil, den Kunden am wenigsten bezahlen wollen. Sie stellen Juniorkräfte für das Sammeln in Rechnung und Partner für das Deuten, und nur das Zweite wird geschätzt.",
      a: "Verkürzen Sie die Faktensuche von Wochen auf Tage, setzen Sie Ihre eigene Marke auf das Ergebnis und verkaufen Sie die Deutung.",
    },
    cols: [
      { h: "1. Was Sie verkaufen können", li: [
        "Ein bezahltes Erstprojekt, in Tagen geliefert, das die größere Beauftragung eröffnet.",
        "Eine unabhängige Zweitmeinung zu einem bereits laufenden Sicherheitsprogramm.",
        "Lizenzen, damit der Kunde es weiter nutzt, an denen Sie verdienen.",
      ] },
      { h: "2. Was Sie hinterlassen", li: [
        "Feststellungen für die Sicherheitsleitung.",
        "Risiko in Geld für den Finanzvorstand.",
        "Bedrohungsakteure für den Vorstand und Compliance für den Prüfungsausschuss.",
      ] },
      { h: "3. Warum die Unterschrift sicher ist", li: [
        "Wo eine Quelle nicht erreichbar war, sagen die Feststellungen \"unbekannt\", statt eine Schwäche zu erfinden.",
        "Jede Feststellung trägt den Nachweis, auf dem sie ruht, und das Datum der Beobachtung.",
        "Es ist wiederholbar, also hat die Folgebeauftragung einen gemessenen Ausgangspunkt.",
      ] },
    ],
    win: { h: "Die Aussage, klar benannt", p:
      "Ihr Name steht auf dem Dokument. Genau deshalb ist eine Methode, die sich weigert zu raten, " +
      "für Sie mehr wert als eine, die immer eine Zahl liefert." },
    steps: [
      { k: "Pilot", v: "Ein Kunde, ein Durchlauf, Ihre eigene Analyse obendrauf." },
      { k: "Paket", v: "Ein benanntes Angebot mit festem Umfang und festem Preis." },
      { k: "Marke", v: "Ihre Identität auf der Plattform und auf jedem Dokument." },
    ],
    cta: { btn: "Sprechen Sie mit uns", txt: "White-Label-, Lizenz- und Mengenkonditionen auf Anfrage." },
  },

  // --------------------------------------------------------------------------------- TELCO
  {
    id: "telco", group: "partners", nav: "Telekommunikationsanbieter",
    eyebrow: "Partner", h2: "Für Telekommunikationsanbieter",
    scr: {
      s: "Sie verkaufen Konnektivität an Tausende von Geschäftskunden und wollen Sicherheit anbinden, bevor Konnektivität zur reinen Massenware wird.",
      c: "Eine eigene Managed-Security-Praxis braucht Analysten, die Sie nicht einstellen können, zu einer Marge, die der Markt nicht zahlt, für einen Kundenstamm, der für Einzelbetreuung viel zu groß ist.",
      a: "Verkaufen Sie einen Sicherheitsdienst, dessen Kosten nicht mit der Kundenzahl steigen, erbracht von den Account Managern, die Sie ohnehin beschäftigen.",
    },
    cols: [
      { h: "1. Was Sie verkaufen", li: [
        "Einen Analysedienst unter Ihrer Marke: Ihr Portal, Ihre Rechnung, Ihr Preis.",
        "Lizenzen als wiederkehrende Position, in Paketen oder als unbegrenzte Nutzung.",
        "Eine wiederkehrende Überprüfung, die den Konnektivitätsvertrag schwerer wechselbar macht als der Preis allein.",
      ] },
      { h: "2. Wie es den Kundenstamm erreicht", li: [
        "Binden Sie es am Verkaufspunkt an, während der Konnektivitätsauftrag unterschrieben wird.",
        "Keine neue Vertriebsbewegung: Ihre vorhandenen Account Manager sind der Kanal.",
        "Es erreicht den langen Ausläufer kleiner Kunden, den Sie mit Menschen nie bedienen können.",
      ] },
      { h: "3. Wo es läuft", li: [
        "In Ihrer eigenen Umgebung oder in einer nationalen Cloud, wo die Regulierung es verlangt.",
        "In dem Land, das Ihre Aufsicht benennt, einschließlich des Lizenzservers.",
        "In den Sprachen, die Ihr Markt tatsächlich liest.",
      ] },
    ],
    win: { h: "Die Aussage, klar benannt", p:
      "Das ist das seltene Sicherheitsangebot, das ein Kundenstamm Ihrer Größe wirklich aufnehmen " +
      "kann, weil nichts daran eine eigene Fachkraft pro Kunde verlangt." },
    steps: [
      { k: "Belegen", v: "Lassen Sie es über eine Stichprobe Ihres eigenen Bestands laufen." },
      { k: "Marke", v: "Gestalten Sie Plattform und alle Dokumente als Ihre eigenen." },
      { k: "Anbinden", v: "Setzen Sie es auf das Auftragsformular für Konnektivität." },
    ],
    cta: { btn: "Sprechen Sie mit uns", txt: "White-Label-, Integrations-, Lizenz- und Mengenkonditionen auf Anfrage." },
  },

  // ----------------------------------------------------------------------------------- SME
  {
    id: "sme", group: "buyers", nav: "Kleine und mittlere Unternehmen",
    eyebrow: "Kunde", h2: "Für kleine und mittlere Unternehmen",
    note:
      "Ein kleines oder mittleres Unternehmen meint hier einen Betrieb von etwa zehn bis " +
      "zweihundertfünfzig Beschäftigten, in dem eine Person die Informationstechnik neben einer " +
      "anderen Aufgabe betreut. Diese Seite ist für dieses Unternehmen selbst geschrieben: für die " +
      "Inhaberin oder den Inhaber, für die Geschäftsführung oder eben für diese eine Person.",
    scr: {
      s: "Man sagt Ihnen, Ihr Unternehmen müsse Cybersicherheit ernst nehmen, und Sie stimmen zu.",
      c: "Der Rat lautet, einen Penetrationstest, eine Beratung und ein Regelwerk zu kaufen. Alle drei kosten mehr, als irgendjemand das Risiko für Sie beziffert hat, und keines beantwortet die einzige Frage, die Sie wirklich haben.",
      a: "Finden Sie diese Woche heraus, was ein Fremder von außen über Ihr Unternehmen sehen kann, ohne etwas zu installieren und ohne jemanden in Ihr Netz zu lassen.",
    },
    cols: [
      { h: "1. Was Sie erhalten", li: [
        "Alles von Ihnen, was zum Internet zeigt, auch das, woran sich niemand mehr erinnert hat.",
        "Was es Sie kosten würde, wenn es schiefgeht, in Geld, mit offengelegter Methode.",
        "Welche Gesetze für Sie gelten und bis wann, in klarer Sprache.",
      ] },
      { h: "2. Warum es zu einem Unternehmen Ihrer Größe passt", li: [
        "Nichts zu installieren. Keine Software, kein Zugang, niemand, der Ihr Büro besucht.",
        "Sie nennen einen Firmennamen. Das ist die gesamte Einrichtung.",
        "Lassen Sie es erneut laufen, sobald sich etwas ändert, statt einmal im Jahr, wenn das Budget es hergibt.",
      ] },
      { h: "3. Was Sie damit tun können", li: [
        "Leiten Sie es unverändert an einen Kunden weiter, der Sie prüft.",
        "Geben Sie es Ihrer Bank oder Ihrem Versicherer, ohne Übersetzung.",
        "Übergeben Sie es Ihrem Dienstleister für Informationstechnik als Arbeitsliste.",
      ] },
    ],
    channel: {
      b: "So kaufen Sie es.",
      t: "Über einen Partner, nicht direkt bei uns. Wählen Sie entweder einen unserer " +
         "zertifizierten Partner in Ihrer Region, oder stellen Sie uns dem " +
         "Informationstechnik-Unternehmen vor, dem Sie bereits vertrauen, und wir nehmen es auf. " +
         "Sie behalten die Beziehung, die Sie haben. Der Partner gewinnt die Fähigkeit hinzu. Die " +
         "Wahl liegt bei Ihnen.",
    },
    win: { h: "Die Aussage, klar benannt", p:
      "Die meisten Unternehmen Ihrer Größe finden mindestens eine Sache, von der sie nicht wussten, " +
      "dass sie aus dem Internet sichtbar ist. Das zu finden kostet Sie einen Nachmittag statt " +
      "eines Projekts." },
    steps: [
      { k: "Jetzt", v: "Sehen Sie sich die öffentliche Vorführung an. Echte Dokumente, erfundenes Unternehmen." },
      { k: "Dann", v: "Bitten Sie uns oder Ihren eigenen Dienstleister um einen Durchlauf auf Ihren eigenen Namen." },
      { k: "Danach", v: "Beheben Sie, was zählt, und lassen Sie es erneut laufen, um den Abschluss zu belegen." },
    ],
    cta: { btn: "Partner finden", txt: "Preise und Konditionen kommen von Ihrem Partner. Nennen Sie uns Ihre Region und wir stellen den Kontakt her, oder bringen Sie Ihren eigenen mit." },
  },

  // ---------------------------------------------------------------------------- ENTERPRISE
  {
    id: "enterprise", group: "buyers", nav: "Großunternehmen",
    eyebrow: "Kunde", h2: "Für Großunternehmen",
    scr: {
      s: "Sie haben Sicherheitsteams, ausgereifte Werkzeuge und ein echtes Budget. Jedes dieser Teams besitzt einen Teil des Bildes.",
      c: "Niemand kann sagen und belegen, wie die gesamte Gruppe von außen aussieht. Tochtergesellschaften und Zukäufe hinterlassen Systeme, zu denen sich kein Team bekennt. Lieferantenrisiko wird mit einem Formular bewertet, das der Lieferant über sich selbst ausfüllt.",
      a: "Eine externe Sicht auf die gesamte Gruppe, in Geld bewertet, nach Plan wiederholt, mit einem Bericht darüber, was sich seit dem letzten Durchlauf genau verändert hat.",
    },
    cols: [
      { h: "1. Abdeckung, die Ihre Werkzeuge nicht haben", li: [
        "Die gesamte Gruppe, einschließlich Tochtergesellschaften und Marken, die den Namen der Mutter nicht tragen.",
        "Lieferanten, nach derselben Methode bewertet, ohne Zugang und ohne Fragebogen.",
        "Neu erworbene Unternehmen, bevor ihr Netz mit Ihrem verbunden wird.",
      ] },
      { h: "2. Ergebnisse in der Form Ihrer Organisation", li: [
        "Feststellungen für die Netzwerksicherheit. Risiko in Geld für den Finanzvorstand und den Risikoausschuss.",
        "Bedrohungsakteure für den Vorstand. Compliance für die Interne Revision.",
        "Kein Team muss sich mit einem anderen einigen, bevor es sein eigenes Dokument nutzen kann.",
      ] },
      { h: "3. Gebaut, um Widerspruch standzuhalten", li: [
        "Jede Feststellung trägt die Adresse, den Port, den Nachweis und das Datum.",
        "Die Abgrenzung ist bewusst konservativ: der Server eines anderen Unternehmens auf geteilter Infrastruktur wird nie als Ihrer gemeldet.",
        "Wo eine Quelle nicht erreichbar war, meldet es \"unbekannt\", statt eine Schwäche abzuleiten.",
      ] },
    ],
    change: {
      h: "Der Veränderungsbericht, und das ist der Teil, auf den es ankommt",
      lead:
        "Eine einzelne Analyse sagt Ihnen, wo Sie stehen. Sie kann nicht sagen, ob etwas besser " +
        "wird. Lassen Sie sie erneut laufen, und die Plattform vergleicht beide Durchläufe und meldet nur das, was sich bewegt hat.",
      cells: [
        { k: "new", t: "Neu", b: "beim letzten Mal noch nicht existierten",
          before: "Expositionen, die ", after: ": ein Dienst, den jemand veröffentlicht hat, ein abgelaufenes Zertifikat, ein Server, den ein Zukauf mitgebracht hat." },
        { k: "closed", t: "Geschlossen", b: "verschwunden",
          before: "Feststellungen, die ", after: " sind. Das ist der Nachweis, dass ein Budget für Behebung ein Ergebnis gebracht hat, und das ist der schwierigste Nachweis in der Sicherheit." },
        { k: "open", t: "Weiterhin offen", b: "sich nicht bewegt haben",
          before: "Früher erhobene Feststellungen, die ", after: ", mit der Angabe, wie lange sie offen sind. Das ist die Eskalationsliste, und sie schreibt sich von selbst." },
      ],
      tailBefore: "Ihr Compliance-Prozess will keinen Bericht. Er will eine datierte, belegte Antwort auf eine einzige Frage: ",
      tailBold: "Was hat sich verändert, und hat jemand behoben, was wir angesprochen haben?",
      tailAfter: " Das macht daraus statt eines Projekts eine Kontrolle, und das ist der Grund, es nach Plan laufen zu lassen statt einmalig.",
    },
    channel: {
      b: "So kaufen Sie es.",
      t: "Über den Kanal. Wählen Sie entweder einen unserer zertifizierten Partner, oder benennen " +
         "Sie den Systemintegrator, mit dem Sie bereits arbeiten, und wir nehmen ihn auf. Ihr " +
         "Einkaufsprozess, Ihre Verträge und Ihre bestehenden Lieferantenbeziehungen bleiben, wie sie sind.",
    },
    win: { h: "Die Aussage, klar benannt", p:
      "Ihre Teams behalten jedes Werkzeug, das sie haben. Dies beantwortet die eine Frage, auf die " +
      "keines dieser Werkzeuge gerichtet ist: was die Außenwelt über alles sehen kann, was Ihnen " +
      "gehört. Und es belegt Monat für Monat, ob das weniger wird." },
    steps: [
      { k: "Belegen", v: "Eine Geschäftseinheit. Vergleichen Sie sie mit dem, was Sie zu haben glaubten." },
      { k: "Ausweiten", v: "Nehmen Sie Tochtergesellschaften und Ihre kritischsten Lieferanten hinzu." },
      { k: "Betreiben", v: "Setzen Sie es auf einen Plan und steuern Sie den Veränderungsbericht." },
    ],
    cta: { btn: "Sprechen Sie mit uns", txt: "Konzernverträge, Zugang zur Programmierschnittstelle und Sicherheitsdokumentation kommen über Ihren oder unseren Partner." },
  },

  // ----------------------------------------------------------------------------------- LAW
  {
    id: "law", group: "buyers", nav: "Kanzleien",
    eyebrow: "Kunde", h2: "Für Kanzleien",
    scr: {
      s: "Sie beraten zu Datenschutz, Cybervorfällen, Unternehmenskäufen und regulatorischer Exposition.",
      c: "Sie brauchen regelmäßig technische Fakten über ein Unternehmen, das Sie nicht berühren dürfen. Die Systeme einer anderen Partei ohne Befugnis zu testen erzeugt genau die Haftung, die zu verhindern Ihre Aufgabe ist.",
      a: "Technische Nachweise, gewonnen, ohne irgendjemandem irgendetwas anzutun. Genau das macht sie in Ihrer Arbeit verwendbar.",
    },
    cols: [
      { h: "1. Wo es greift", li: [
        "**Due Diligence in einer Transaktion:** der tatsächliche externe Bestand des Zielunternehmens und dessen bewertetes Risiko, bevor der Kaufvertrag unterzeichnet wird.",
        "**Nach einem Vorfall:** ein unabhängiges, datiertes Bild dessen, was öffentlich sichtbar war.",
        "**Streitigkeiten:** ein technisches Beweisstück, das ein anderer Sachverständiger nachvollziehen kann.",
      ] },
      { h: "2. Warum die Nutzung rechtmäßig ist", li: [
        "Vollständig passiv. Kein einziges Datenpaket erreicht das untersuchte Unternehmen.",
        "Nichts wird ausgenutzt und an keinem System wird sich angemeldet.",
        "Aufgebaut allein aus Quellen, die für jede Recherche rechtmäßig zugänglich sind. Eine Befugnis von irgendjemandem ist deshalb nicht erforderlich.",
      ] },
      { h: "3. Was Sie einem Mandanten vorlegen können", li: [
        "Jede Feststellung mit ihrem Nachweis und dem Datum des Abrufs.",
        "Welche Vorschriften gelten, mit Pflichten und Fristen, zitiert aus den Primärtexten.",
        "Die Exposition, umgerechnet in einen Betrag, den der Vorstand Ihres Mandanten versteht.",
      ] },
    ],
    win: { h: "Die Aussage, klar benannt", p:
      "Es erzeugt technische Fakten mit der einen Eigenschaft, die Ihre Arbeit verlangt: sie wurden " +
      "gewonnen, ohne irgendjemandem irgendetwas anzutun. Genau das macht sie verwendbar." },
    steps: [
      { k: "Analysieren", v: "Lassen Sie es zu einem Mandat laufen, das Sie bereits betreuen." },
      { k: "Prüfen", v: "Messen Sie die Nachweiskette an Ihrem eigenen Maßstab." },
      { k: "Übernehmen", v: "Machen Sie es zum Standardschritt in der Transaktionsprüfung und in der Vorfallarbeit." },
    ],
    cta: { btn: "Sprechen Sie mit uns", txt: "Konditionen je Mandat oder kanzleiweit, über den Kanal. Das Ergebnis ist keine Rechtsberatung und ersetzt keine anwaltliche Prüfung." },
  },

  // ----------------------------------------------------------------------------- INSURANCE
  {
    id: "insurance", group: "buyers", nav: "Versicherer",
    eyebrow: "Kunde", h2: "Für Versicherer, Agenturen und Makler",
    scr: {
      s: "Sie zeichnen Cyberversicherungen und bepreisen sie nach dem, was der Antragsteller über sich selbst angibt.",
      c: "Das Antragsformular beruht auf Selbstauskunft, ist optimistisch und am Tag der Unterschrift veraltet. Bei der Verlängerung können Sie nicht sagen, ob das Zugesagte behoben wurde. Nach einem Schaden können Sie nicht zeigen, was sichtbar war.",
      a: "Zeichnen Sie das Beobachtbare statt des Erklärten, bei jedem Risiko, zu Kosten, die nicht mit der Zahl der Risiken steigen.",
    },
    cols: [
      { h: "1. Welche Prämie trägt dieses Risiko?", li: [
        "Ein Erwartungsschaden und ein schlimmster Fall pro Jahr, erzeugt nach der anerkannten Methode Factor Analysis of Information Risk.",
        "Die Rechenwege werden gezeigt. Es ist damit eine technische Eingabe für Ihre Tarifierung und keine Punktzahl aus einer Blackbox.",
        "Verfügbar, bevor der Antragsteller Sie gewählt hat, denn es braucht keine Mitwirkung.",
      ] },
      { h: "2. Was liegt tatsächlich in ihrem Bestand?", li: [
        "Jeder aus dem Internet erreichbare Angriffspunkt, eingestuft, mit Adresse und Port.",
        "Unabhängig vom Antragsformular, sodass sich beide vergleichen lassen.",
        "In Minuten geliefert, es passt also in einen Angebotsprozess.",
      ] },
      { h: "3. Sind sie regelkonform?", li: [
        "Ihr Stand gegenüber den Cybergesetzen, die für sie gelten, mit Fristen.",
        "Ein Verstoß treibt den Schaden und ist zugleich eine Frage der Deckung.",
        "Die Regime der Europäischen Union und Kanadas sind heute aktiv.",
      ] },
    ],
    ladder: { h: "Über die Laufzeit der Police", items: [
      { b: "Bei der Angebotserstellung.", t: "In Minuten, ohne jede Mitwirkung." },
      { b: "Bei der Verlängerung.", t: "Der Veränderungsbericht zeigt die Behebung oder deren Ausbleiben. Bepreisen Sie den Unterschied." },
      { b: "Über das Portfolio.", t: "Lassen Sie den gesamten Bestand erneut laufen, sobald eine neue, breit ausgenutzte Schwachstelle auftaucht, und kennen Sie Ihre kumulierte Exposition noch am selben Tag." },
      { b: "Im Schadenfall.", t: "Ein datierter Nachweis dessen, was von außen sichtbar war." },
    ] },
    win: { h: "Die Aussage, klar benannt", p:
      "Sie gehen davon weg, das Gesagte zu zeichnen, und dahin, das Beobachtbare zu zeichnen, " +
      "einheitlich, bei jedem Risiko. Das ist ein Argument über die Schadenquote, nicht über Technik." },
    steps: [
      { k: "Kalibrieren", v: "Lassen Sie es gegen bereits gezeichnete Risiken laufen, auch gegen solche mit Schäden." },
      { k: "Vergleichen", v: "Stellen Sie die Ergebnisse neben die Antragsformulare und sehen Sie sich die Lücken an." },
      { k: "Einbetten", v: "In den Angebotsprozess oder in Ihr Maklerportal." },
    ],
    cta: { btn: "Sprechen Sie mit uns", txt: "Portfolio-, Programmierschnittstellen- und Integrationskonditionen auf Anfrage." },
  },

  // ----------------------------------------------------------------------------- REGULATOR
  {
    id: "regulator", group: "buyers", nav: "Aufsichtsbehörden",
    eyebrow: "Kunde", h2: "Für Regulierungs- und Aufsichtsbehörden",
    scr: {
      s: "Sie beaufsichtigen eine Population von Unternehmen mit einem Mandat für Cybersicherheit oder operative Widerstandsfähigkeit.",
      c: "Das Gesetz ist geschrieben und die Fristen sind real. Ihre technische Kapazität ist es nicht. In der Praxis prüfen Sie eine Handvoll Unternehmen im Jahr, ausgewählt ohne technische Grundlage. Sie können nicht wissen, ob gerade die ungeprüften die wichtigen sind.",
      a: "Beaufsichtigen Sie die gesamte Population aus öffentlichen Nachweisen, ohne jemanden zu besuchen, und machen Sie aus jedem Verstoß eine vorbereitete Fallakte, die Ihre zuständige Person prüft und zeichnet.",
    },
    cols: [
      { h: "1. Abdeckung statt Stichprobe", li: [
        "Jedes beaufsichtigte Unternehmen, nach derselben Methode am selben Tag bewertet.",
        "Die Ergebnisse sind über den Sektor hinweg vergleichbar, weil nichts unterschiedlich gemessen wird.",
        "Nach Plan wiederholbar, sodass Sie die Richtung des Sektors messen können.",
      ] },
      { h: "2. Nachweise, die Widerspruch standhalten", li: [
        "Je Unternehmen: die Adresse, der Port, der Nachweis und das Datum der Beobachtung.",
        "Zugeordnet zu der konkreten Klausel, die berührt wird.",
        "Wo eine Quelle nicht erreichbar ist, meldet es \"unbekannt\" und behauptet keinen Verstoß.",
      ] },
      { h: "3. Rechtmäßig durch Bauweise", li: [
        "Vollständig passiv. Kein Unternehmen wird berührt, es entsteht also weder Anzeige- noch Genehmigungsbedarf.",
        "Reproduzierbar, es hält damit der Prüfung durch die eigenen Sachverständigen des Unternehmens stand.",
        "In Ihrer eigenen oder einer nationalen Umgebung betreibbar, wo das Mandat es verlangt.",
      ] },
    ],
    ladder: { h: "Die Vollzugskette, über die gesamte Population betrieben", items: [
      { b: "Erkennen.", t: "Ein nicht regelkonformer Zustand bei einem beaufsichtigten Unternehmen, mit Adresse, Port und dem Datum der Beobachtung." },
      { b: "Zuordnen.", t: "Die konkrete Klausel, die berührt wird, sei es im europäischen Recht oder in Ihrem eigenen nationalen Rechtsakt." },
      { b: "Erhärten.", t: "Vier unabhängige Modelle künstlicher Intelligenz von vier verschiedenen Anbietern prüfen den Fall. Zwei bauen ihn auf, zwei versuchen ihn zu zerlegen. Feste Regeln im Code treffen die Entscheidung, nicht die Modelle, und ein Fall, den keines von ihnen erhärten kann, verlässt die Warteschlange nie." },
      { b: "Entwerfen.", t: "Die belegte Fallakte und der Bescheid werden automatisch vorbereitet." },
      { b: "Entscheiden.", t: "Ihre zuständige Person prüft und zeichnet. Die Maschine baut den Fall, die Behörde erlässt ihn. Genau das hält jeden Bescheid überprüfbar und anfechtbar." },
    ] },
    win: { h: "Die Aussage, klar benannt", p:
      "Sie wählen nicht länger nach Ruf aus, wen Sie prüfen. Sie beaufsichtigen den gesamten Sektor " +
      "nach Nachweisen, ohne einen Prüfer in ein einziges Gebäude zu schicken und ohne dass ein " +
      "einziges Datenpaket ein beaufsichtigtes Unternehmen erreicht." },
    steps: [
      { k: "Pilot", v: "Ein Sektor, eine Gruppe von Unternehmen. Bringen Sie sie in eine Rangfolge." },
      { k: "Vergleichen", v: "Stellen Sie die Rangfolge neben Ihr eigenes Aufsichtswissen." },
      { k: "Skalieren", v: "Die volle Population, nach Plan, mit der Vollzugswarteschlange." },
    ],
    cta: { btn: "Sprechen Sie mit uns", txt: "Vergabe im öffentlichen Sektor, Betriebsstandort und Konditionen auf Anfrage." },
  },

  // --------------------------------------------------------------------------- WHITE-LABEL
  {
    id: "whitelabel", group: "engage", nav: "White-Label", accent: "purple",
    eyebrow: "Formen der Zusammenarbeit, Modell 1 von 2", h2: "White-Label",
    scr: {
      s: "Sie wollen einen Sicherheitsdienst, den Sie unter Ihrem eigenen Namen verkaufen.",
      c: "Die Maschine selbst zu bauen dauert Jahre. Die Marke eines anderen weiterzuverkaufen bedeutet, dass die Beziehung des Kunden zu diesem besteht und nicht zu Ihnen.",
      a: "Ihre Marke vorne, unsere Maschine darunter. Ihr Kunde, Ihr Vertrag, Ihr Preis, und er sieht uns nie.",
    },
    cols: [
      { h: "Was Ihnen gehört", li: [
        "Die Marke auf jedem Bildschirm und auf allen vier Dokumenten.",
        "Die Kundenbeziehung, der Vertrag und die Rechnung.",
        "Ihre eigene Preisgestaltung, von Ihnen festgelegt, für Ihren Markt.",
        "Wo es läuft: Ihre Cloud, Ihre Region oder eine nationale Umgebung. Der Lizenzserver kann in dem Land oder der Region stehen, die Sie verlangen.",
      ] },
      { h: "Was Ihnen nicht gehört", li: [
        "Der Quellcode und das Eigentum an der Plattform. Sie erhalten eine Lizenz, sie zu nutzen und darzubieten, nicht sie zu besitzen.",
        "Das Recht, die Software selbst an Dritte weiterzulizenzieren.",
        "Die Entwicklung der Maschine und ihre Zusicherungen zur Richtigkeit. Beides bleibt bei uns, und genau darauf verlassen Sie sich.",
      ] },
    ],
    win: { h: "Wählen Sie dies, wenn", p:
      "Sie ein Produkt zum Verkaufen wollen: etwas, in das sich Ihr Kunde einloggt und das Ihren " +
      "Namen trägt. Es ist das richtige Modell für Managed Service Provider, " +
      "Telekommunikationsanbieter, Beratungshäuser und Reseller, die eine Sicherheitspraxis aufbauen." },
    steps: [
      { k: "Umfang", v: "Marke, Betriebsregion, Sprachen, welche Module." },
      { k: "Aufbau", v: "Wir gestalten und stellen bereit. Sie nehmen es gegen vereinbarte Kriterien ab." },
      { k: "Verkauf", v: "Unter Ihrem Namen, zu Ihrem Preis." },
    ],
    cta: { btn: "Sprechen Sie mit uns", txt: "Zusagen, Einrichtungsumfang und Preisgestaltung sind kaufmännisch und vertraulich. Fragen Sie uns." },
  },

  // ----------------------------------------------------------------------------------- OEM
  {
    id: "oem", group: "engage", nav: "Integriert (OEM)", accent: "purple",
    eyebrow: "Formen der Zusammenarbeit, Modell 2 von 2", h2: "Integriert, auch OEM genannt",
    scr: {
      s: "Sie haben bereits ein Produkt, in das sich Ihre Kunden täglich einloggen.",
      c: "Ein eigenständiges Produkt daneben zu verkaufen erzeugt Reibung: ein weiterer Login, ein weiterer Vertrag, eine weitere Sache zum Erklären. Es verwässert außerdem das Produkt, an dem Sie Jahre gebaut haben.",
      a: "Unsere Maschine in Ihrem Produkt, sodass Ihr Kunde eine neue Funktion sieht statt eines neuen Produkts, das er bewerten muss.",
    },
    cols: [
      { h: "So funktioniert es", li: [
        "Sie rufen unsere Programmierschnittstelle auf. Feststellungen, bewertetes Risiko, Kontext zu Bedrohungsakteuren, Compliance-Einstufungen und fertige Dokumente kommen als Daten zurück.",
        "Sie stellen sie in Ihrer eigenen Oberfläche dar, in Ihrer eigenen Struktur.",
        "Kritische Feststellungen werden Ihrer Plattform oder Ihrem Sicherheitsüberwachungssystem zugestellt, sobald sie auftreten. Es gibt also nichts abzufragen.",
        "Betreibbar in Ihrer Umgebung, in der Region, die Ihre Architektur oder Ihre Aufsicht verlangt.",
      ] },
      { h: "Was es Ihnen bringt", li: [
        "Eine neue Fähigkeit in einem bestehenden Produkt, ohne dass der Kunde etwas Neues freigeben muss.",
        "Kein zweiter Login, kein zweiter Vertrag, kein zweiter Supportweg.",
        "Volle Kontrolle über das Erlebnis, über seinen Platz auf Ihrer Roadmap und über Ihre Preisgestaltung.",
        "Sie können Lizenzen weiterhin als eigene Position weiterverkaufen, wo ein Kunde es verlangt.",
      ] },
    ],
    vs: {
      a: { h: "White-Label ist", bold: "Produkt", before: "Ein ", after: ", das wie Ihres aussieht. Ihr Kunde loggt sich in etwas ein, das Ihre Marke trägt. Am besten, wenn Sie eine Dienstleistungspraxis aufbauen und etwas zum Verkaufen brauchen." },
      b: { h: "Integriert ist", bold: "Fähigkeit", before: "Eine ", after: " in Ihrem Produkt. Ihr Kunde sieht eine neue Funktion, kein neues Produkt. Am besten, wenn Sie den Bildschirm, auf den Ihr Kunde schaut, bereits besitzen und keinen zweiten hinzufügen wollen." },
    },
    win: { h: "Wählen Sie dies, wenn", p:
      "Sie ein Software- oder Sicherheitsanbieter sind, ein Versicherer mit Portal oder ein " +
      "Plattformgeschäft. Der Test ist einfach. Loggt sich Ihr Kunde bereits in etwas von Ihnen ein, " +
      "wählen Sie Integriert. Tut er das nicht, wählen Sie White-Label." },
    steps: [
      { k: "Entwurf", v: "Welche Aufrufe, welche Daten, an welcher Stelle." },
      { k: "Integration", v: "Eng gefasste Schlüssel, signierte Rückrufe, eine versionierte Spezifikation." },
      { k: "Auslieferung", v: "Es wird zu einer Funktion Ihrer Plattform." },
    ],
    cta: { btn: "Sprechen Sie mit uns", txt: "Integrationstiefe, Menge und Konditionen sind kaufmännische Themen. Fragen Sie uns." },
  },

  // ------------------------------------------------------------------------------- CONTACT
  {
    id: "contact", group: "engage", nav: "Sprechen Sie mit uns",
    eyebrow: "Nächster Schritt", h2: "Sprechen Sie mit uns",
    note:
      "Preise, Stufen, Lizenzmodelle, Zusagen und Vertragsbedingungen sind kaufmännische Themen " +
      "und werden direkt vereinbart. Sie werden hier bewusst nicht veröffentlicht.",
    cols: [
      { h: "Was wir diese Woche tun können", li: [
        "Ein Durchlauf auf einen Firmennamen Ihrer Wahl, damit Sie das Ergebnis beurteilen und nicht die Präsentation.",
        "Ein Referenzgespräch mit einem Partner, der dies im deutschsprachigen Markt bereits verkauft.",
        "Die Vertragsunterlagen: Partnervertrag, White-Label- und Integrationszusatz, Geheimhaltungsvereinbarung, Service-Level-Vereinbarung, Nutzungsbedingungen, Auftragsverarbeitungsvertrag und ein Hosting-Datenblatt.",
        "Die Dokumentation der Sicherheitsarchitektur, nach der Ihre Sicherheitsbeauftragten oder Ihr Einkauf fragen werden.",
      ] },
      { h: "Was wir Sie fragen werden", li: [
        "Welche der oben genannten Zielgruppen Sie sind. Das ändert die Antwort erheblich.",
        "Ob Sie es weiterverkaufen, mit Ihrer Marke versehen oder in Ihr eigenes Produkt integrieren wollen.",
        "Ob Sie Lizenzen, Dienstleistungen oder beides verkaufen.",
        "Wo die Daten und der Lizenzserver stehen müssen.",
      ] },
    ],
    cta: { btn: "Schreiben Sie uns", ghost2: "Zuerst die öffentliche Vorführung ansehen", txt: "Cybergod LLC, Teil der S4Biz Group" },
  },
];
