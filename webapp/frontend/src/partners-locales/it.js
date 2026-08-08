// partners-locales/it.js: the ITALIAN translation of en.js.
//
// en.js IS THE REFERENCE. Every key, every array length, every section id and every column here
// mirrors it exactly; only the text differs. The object shape is asserted by
// tools/partners_gate.mjs, so adding, removing, merging or reordering anything is a failed build
// rather than a page that quietly loses a column.
//
// Structural values are NOT translated because they are lookup keys: section `id`, `group`,
// `accent`, the `k` inside change.cells, and arts[].n. Everything else is content.
//
// Register: formal business Italian ("Lei" / impersonal). No long dashes, no HTML entities, no
// prices. Terminology is fixed: "finding" is always "rilievo".

export const meta = {
  docTitle: "A chi si rivolge",
  kicker: "Un nome in ingresso. Quattro documenti pronti per il consiglio in uscita. Undici destinatari.",
  h1a: "Digiti il nome di un'azienda.",
  h1b: "Ottenga il ",
  h1c: "quadro completo del rischio",
  h1d: " in pochi minuti.",
  lede:
    "Non viene inviato un solo pacchetto all'azienda analizzata. Tutto è costruito a partire da " +
    "fonti che qualsiasi ricercatore può consultare legittimamente. Non c'è quindi nulla da " +
    "installare, nessuno a cui chiedere il permesso e nessun questionario da attendere. Ogni volta " +
    "tornano quattro documenti.",
  artsNote:
    "Esiste anche un quinto documento: un unico report web autonomo che riunisce tutti e quattro e " +
    "si apre in qualsiasi browser. È quello che le persone inoltrano internamente. Ogni documento è " +
    "disponibile in inglese, tedesco o russo.",
  railTitle: "A chi si rivolge",
  groupPartners: "Partner",
  groupBuyers: "Acquirenti",
  groupEngage: "Come collaborare",
  foot:
    "I contenuti provengono dal materiale informativo per partner e autorità e dal pacchetto legale " +
    "firmato. Per scelta, in nessun punto compaiono prezzi, sconti, numero di postazioni o impegni. " +
    "I volumi di incontri riportati per i partner sono quelli dichiarati dai partner stessi e " +
    "dipendono dal singolo venditore. L'esito dell'assessment non costituisce consulenza legale. " +
    "Ogni riferimento a clienti identificabili è rimosso.",
};

export const arts = [
  { n: "1", name: "Rilievi", body:
    "Ogni esposizione rivolta verso internet, ordinata da Critica a Bassa. Ciascuna indica di che " +
    "cosa si tratta, perché è importante, come rimediare e l'indirizzo e la porta esatti su cui è " +
    "stata osservata." },
  { n: "2", name: "Rischio in denaro", body:
    "Gli stessi rilievi espressi in valuta, con il riconosciuto metodo Factor Analysis of " +
    "Information Risk. Costo di un singolo incidente, caso peggiore annuo e una curva che scende " +
    "man mano che i rilievi vengono chiusi. Scritto per il direttore finanziario." },
  { n: "3", name: "Attori delle minacce", body:
    "Quali attaccanti sono davvero rilevanti per questo settore e questi Paesi, e come operano. La " +
    "risposta al consiglio che chiede chi verrebbe a colpirci." },
  { n: "4", name: "Conformità", body:
    "Rilievi mappati sugli articoli delle leggi applicabili nei Paesi in cui l'azienda opera, con " +
    "le scadenze reali. Oggi Unione Europea e Canada." },
];

export const sections = [
  // ------------------------------------------------------------------ MANAGED SERVICE PROVIDERS
  {
    id: "msp", group: "partners", nav: "Managed service provider",
    eyebrow: "Partner", h2: "Per i managed service provider",
    scr: {
      s: "Gestisce la sicurezza di molti clienti contemporaneamente, con un team che non può crescere alla velocità del suo portafoglio clienti.",
      c: "Esaminare a mano l'esposizione di un singolo cliente costa circa una giornata di analista. Su larga scala non accade, e la business review trimestrale diventa un aggiornamento di stato su cui nessuno stanzia un budget.",
      a: "Valuti ogni cliente del suo portafoglio con la stessa cadenza, a un costo che non cresce con il numero dei clienti. Poi venda la soluzione su quattro livelli di prezzo distinti.",
    },
    cols: [
      { h: "1. Che cosa vende", li: [
        "L'assessment stesso, a pagamento, con il suo marchio.",
        "Una ripetizione mensile o trimestrale con un report di ciò che è cambiato. Quel report è il servizio gestito.",
        "Le licenze, vendute a pacchetti o in formula illimitata, su cui guadagna in modo autonomo.",
      ] },
      { h: "2. Perché i conti tornano", li: [
        "Un solo analista copre l'intero portafoglio invece di un singolo cliente.",
        "Avviare un cliente non richiede nulla da parte sua: nessun software da installare, nessun accesso, nessun modulo.",
        "Il documento di conformità risponde al revisore nella stessa esecuzione, quindi non serve un secondo incarico da presidiare.",
      ] },
      { h: "3. Dove sta il margine", li: [
        "Non nel report. Nei quattro modi di chiudere un rilievo, descritti qui sotto.",
        "I suoi account manager ottengono un motivo per chiamare ogni cliente, ogni mese, con una novità.",
        "Un rilievo chiuso dimostra che il retainer funziona, ed è la cosa più difficile da dimostrare nella sicurezza.",
      ] },
    ],
    ladder: { h: "I quattro modi di chiudere un rilievo, dal più economico", items: [
      { b: "Consulenza.", t: "Un workshop che ripercorre ogni rilievo alla luce di ciò che il cliente già possiede." },
      { b: "Nessuna nuova spesa, usando gli apparati esistenti.", t: "La maggior parte dei rilievi si chiude con modifiche di configurazione, posizionamento e processo su prodotti che il cliente già paga. Lei consegna un elenco di azioni, ciascuna associata allo strumento che la risolve." },
      { b: "Open source.", t: "Dove gli apparati esistenti non bastano, un progetto costruito su open source invece di un acquisto. Non c'è alcuna licenza da comprare. Il costo si sposta su competenze ed esercizio, che il cliente assume oppure acquista da lei." },
      { b: "Un prodotto commerciale.", t: "Solo dove nessuna delle opzioni precedenti funziona. La scelta resta all'interno dell'albo fornitori approvato dal cliente. Lei consiglia su idoneità, sequenza e integrazione." },
    ] },
    win: { h: "La promessa, detta con chiarezza", p:
      "Un report singolo è un progetto. Un report mensile di ciò che è cambiato è un abbonamento. " +
      "Lei vende il rilievo e la strada per risolverlo, su quattro livelli di prezzo, a un cliente " +
      "che già si fida di lei." },
    steps: [
      { k: "Settimana 1", v: "Esegua i suoi dieci clienti principali e legga che cosa torna." },
      { k: "Settimana 2", v: "Invii un rilievo a ciascuno. Veda il metodo qui sotto." },
      { k: "Settimana 3", v: "Ci metta il suo marchio e lo inserisca a listino nel suo livello gestito." },
    ],
    cta: { btn: "Parliamone", txt: "Pacchetti di licenze, piani illimitati, livelli e condizioni sono materia commerciale. Ce lo chieda." },
  },

  // ------------------------------------------------------------------------------- RESELLERS
  {
    id: "var", group: "partners", nav: "Rivenditori",
    eyebrow: "Partner", h2: "Per i rivenditori",
    scr: {
      s: "Vende tecnologia e vince sulla relazione, sul tempismo e sulla qualità della conversazione che riesce ad aprire.",
      c: "Il primo incontro tecnico è la cosa più difficile da ottenere. Il sostituto abituale è uno sconto, che le costa margine e insegna al cliente ad aspettare il prossimo.",
      a: "Entri sapendo già che cosa è esposto sul loro perimetro. Faccia pagare l'assessment al giusto valore, poi lo porti in detrazione sul lavoro che fa emergere.",
    },
    cols: [
      { h: "1. Come viene prezzato", li: [
        "L'assessment è un incarico a pagamento, a perimetro fisso. Non è un omaggio.",
        "Il suo valore viene poi detratto dalla consulenza o dagli interventi di rimedio che seguono.",
        "Il cliente quindi non rischia nulla, e lei viene pagato in ogni caso.",
      ] },
      { h: "2. Su che cos'altro guadagna", li: [
        "Le licenze, a pacchetti o in formula illimitata, come seconda linea ricorrente.",
        "Tutti e quattro i modi di chiudere un rilievo: consulenza, apparati esistenti, open source o un prodotto approvato.",
        "Le esecuzioni ripetute, che mostrano che cosa è cambiato e riaprono la conversazione a cadenza fissa.",
      ] },
      { h: "3. Che cosa ci guadagna la sua forza vendita", li: [
        "Un motivo per chiamare chiunque, avendo qualcosa di preciso da dire.",
        "Nuovi clienti: non servono permessi né accessi, quindi può lavorare prima ancora di essere invitato.",
        "Difesa del rinnovo: lo esegua prima della scadenza contrattuale di un concorrente e mostri che cosa è cambiato.",
      ] },
    ],
    win: { h: "La promessa, detta con chiarezza", p:
      "Uno sconto compra una trattativa. Conoscere il loro perimetro meglio di loro compra la " +
      "relazione, e questa volta lei viene pagato per il lavoro che le ha aperto la porta." },
    steps: [
      { k: "Giorno 1", v: "Scelga cinque potenziali clienti con cui non riesce a fissare un incontro." },
      { k: "Giorno 2", v: "Invii un rilievo a ciascuno. Mai il report." },
      { k: "Giorno 5", v: "Vada all'incontro. Quoti l'assessment. Lo porti in detrazione." },
    ],
    cta: { btn: "Parliamone", txt: "Esistono percorsi di segnalazione, rivendita, licenza e White-Label. Condizioni su richiesta." },
  },

  // ------------------------------------------------------------------------------ THE METHOD
  {
    id: "play", group: "partners", nav: "Il metodo di apertura", accent: "gold",
    eyebrow: "Ogni partner usa questo metodo", h2: "Invii un rilievo. Trattenga il report.",
    scr: {
      s: "Ha eseguito l'assessment e ha in mano un documento che contiene tutto.",
      c: "Un potenziale cliente che non ha chiesto un report lo legge come un documento di vendita e lo mette da parte. Un report completo chiede inoltre uno spazio in agenda che in questo trimestre nessuno ha.",
      a: "Invii esattamente un rilievo, con le sue prove e le indicazioni per risolverlo. È il singolo rilievo a farle ottenere l'incontro. Il report è ciò che vende una volta dentro.",
    },
    quote: {
      q: "Questo indirizzo non compare affatto nel nostro sistema di inventario.",
      by: "Un ingegnere di sicurezza di rete presso una grande azienda regolamentata, durante " +
          "un'esecuzione dal vivo. La piattaforma aveva fatto emergere un indirizzo attribuito alla " +
          "sua stessa organizzazione. Non è riuscito a trovarlo nell'inventario interno degli asset. " +
          "Azienda, settore e dettagli omessi.",
    },
    cols: [
      { h: "Come si applica", li: [
        "Esegua l'assessment, legga i rilievi e ne scelga esattamente uno.",
        "Invii quel rilievo, con le prove e il consiglio su come risolverlo.",
        "Non alleghi il report. Rimuova i dettagli identificativi se il contatto è a freddo.",
        "Chieda trenta minuti per illustrare il resto.",
      ] },
      { h: "Perché un rilievo batte un report", li: [
        "**Un asset sconosciuto è il tipo di rilievo più forte.** Un indirizzo fuori dall'inventario è fuori dalle patch, dalle scansioni e dalla reportistica, e l'inventario degli asset sta alla base di ogni standard di sicurezza su cui vengono verificati.",
        "**Regge allo scetticismo.** A un rilievo noto si risponde \"se ne occupa un altro team\". A un indirizzo che nessuno sa spiegare non si può rispondere così.",
        "**È adatto alla stanza.** Arriva al team con cui sta già parlando, non a una funzione che nessuno dei presenti controlla.",
        "**Si giustifica da solo.** Un host non gestito esposto su internet costa poco da discutere e molto da ignorare.",
      ] },
    ],
    win: { h: "Che cosa riportano i partner", p:
      "I partner in Germania e Svizzera che usano questo metodo riportano da sei a dieci nuovi primi " +
      "incontri per venditore a settimana. Dipende chiaramente dalla capacità del singolo venditore " +
      "di trasformare un fatto in una conversazione, quindi preferiamo che lo senta da loro. " +
      "Organizziamo noi la chiamata." },
    cta: { btn: "Chieda una call di referenza", ghost: true, txt: "Partner di referenza disponibili nel mercato di lingua tedesca." },
  },

  // --------------------------------------------------------------------- SYSTEMS INTEGRATORS
  {
    id: "gsi", group: "partners", nav: "System integrator",
    eyebrow: "Partner", h2: "Per i system integrator",
    scr: {
      s: "La discovery è la prima fase di ogni programma di sicurezza e di trasformazione che realizza.",
      c: "Viene fatturata a tariffa di consulenza, svolta a mano, diversa in ogni incarico, ed è la fattura su cui i clienti discutono. Eppure niente di ciò che segue è valido senza di essa.",
      a: "Renda la discovery un passo fisso, rapido e identico in ogni incarico, così il suo margine si sposta su architettura e rimedio, dove deve stare.",
    },
    cols: [
      { h: "1. Dove si colloca nel metodo", li: [
        "La discovery diventa un input della sua metodologia, non un suo sostituto.",
        "Una baseline all'avvio del programma, poi una ripetizione a ogni punto di controllo.",
        "L'avanzamento è dimostrato da ciò che si è chiuso, non affermato in un report di stato.",
      ] },
      { h: "2. Dove si applica inoltre", li: [
        "Valutare un fornitore senza attendere che il fornitore collabori.",
        "Definire il perimetro di un'azienda appena acquisita prima di collegarne la rete alla capogruppo.",
        "Qualsiasi Paese o controllata in cui non ha un team locale.",
      ] },
      { h: "3. Che cosa cambia sul piano commerciale", li: [
        "Smette di vendere settimane di raccolta dei fatti e inizia a vendere il risultato che quella raccolta bloccava.",
        "Il documento sul rischio in denaro quota il programma nella lingua del direttore finanziario fin dal primo giorno.",
        "Ogni rilievo porta con sé le proprie prove, quindi regge alla revisione tecnica del cliente.",
      ] },
    ],
    win: { h: "La promessa, detta con chiarezza", p:
      "La prima fattura smette di essere quella che il suo cliente contesta, perché ora compra una " +
      "risposta invece di un'attività." },
    steps: [
      { k: "Passo 1", v: "Lo esegua su un incarico in corso e confronti con quanto il suo team ha trovato a mano." },
      { k: "Passo 2", v: "Lo integri nel suo deliverable standard di discovery." },
      { k: "Passo 3", v: "Ci metta il suo marchio, oppure lo integri nel prodotto. Veda i due modelli in fondo." },
    ],
    cta: { btn: "Parliamone", txt: "Le condizioni per volumi, aree geografiche e integrazione sono materia commerciale. Ce lo chieda." },
  },

  // ------------------------------------------------------------------------------- VENDORS
  {
    id: "vendors", group: "partners", nav: "Vendor di cybersecurity",
    eyebrow: "Partner", h2: "Per i vendor di cybersecurity",
    scr: {
      s: "Ha un prodotto che risolve un problema reale e una dimostrazione che lo mostra all'opera.",
      c: "La sua dimostrazione prova che il prodotto funziona in generale. Non prova che questo cliente abbia il problema oggi, così la valutazione si riduce a un confronto di funzionalità con un concorrente.",
      a: "Mostri al potenziale cliente che cosa è aperto sul suo perimetro prima di mostrargli il prodotto. Poi lo esegua di nuovo dopo l'installazione e mostri, in denaro, che cosa il suo prodotto ha chiuso.",
    },
    cols: [
      { h: "1. Nella sua forza vendita", li: [
        "Ogni account manager porta con sé un quadro di esposizione specifico per quel cliente.",
        "Apre le porte in aziende che non hanno mai sentito il suo nome, senza alcun accesso.",
        "Il documento sul rischio in denaro trasforma un'esposizione tecnica in una voce di budget.",
      ] },
      { h: "2. Dentro il suo prodotto", li: [
        "L'esposizione esterna diventa una funzionalità della sua piattaforma, erogata tramite la nostra interfaccia di programmazione.",
        "La sua interfaccia, il suo marchio, nessun secondo prodotto da far valutare al cliente.",
        "Aggiunge una vista dall'esterno a un prodotto che guarda soprattutto all'interno, e questa è una lacuna reale in quasi tutti gli stack di sicurezza.",
      ] },
      { h: "3. Accanto al suo prodotto", li: [
        "Lo esegua prima e dopo l'installazione. La differenza è il suo caso di studio.",
        "Dà ai rinnovi un numero invece di una sensazione.",
        "Può anche rivendere licenze accanto ai suoi prodotti.",
      ] },
    ],
    win: { h: "La promessa, detta con chiarezza", p:
      "Nessuno discute la propria superficie di attacco. È la strada più breve da una dimostrazione " +
      "a un budget." },
    steps: [
      { k: "Valutare", v: "Lo esegua su tre delle sue trattative già aperte." },
      { k: "Decidere", v: "Strumento di vendita, linea di rivendita o funzionalità della sua piattaforma." },
      { k: "Integrare", v: "I rilievi arrivano nel suo prodotto tramite l'interfaccia di programmazione." },
    ],
    cta: { btn: "Parliamone", txt: "Le condizioni di integrazione e di licenza dipendono dai volumi e dalla profondità dell'integrazione. Ce lo chieda." },
  },

  // ---------------------------------------------------------------------------- CONSULTING
  {
    id: "consulting", group: "partners", nav: "Società di consulenza",
    eyebrow: "Partner", h2: "Per le società di consulenza",
    scr: {
      s: "Vende giudizio e indipendenza. I clienti pagano per il parere e per il nome sulla copertina.",
      c: "La raccolta dei fatti assorbe gran parte dell'incarico ed è la parte che i clienti pagano più malvolentieri. Fattura i junior per raccogliere i fatti e i partner per interpretarli, e solo il secondo lavoro viene valorizzato.",
      a: "Comprima la raccolta dei fatti da settimane a giorni, metta il suo marchio sull'output e venda l'interpretazione.",
    },
    cols: [
      { h: "1. Che cosa può vendere", li: [
        "Un primo incarico a pagamento, consegnato in pochi giorni, che apre quello più grande.",
        "Una second opinion indipendente su un programma di sicurezza già avviato.",
        "Le licenze perché il cliente continui a usarlo, sulle quali lei guadagna.",
      ] },
      { h: "2. Che cosa lascia al cliente", li: [
        "I rilievi per il direttore della sicurezza.",
        "Il rischio in denaro per il direttore finanziario.",
        "Gli attori delle minacce per il consiglio, e la conformità per il comitato di audit.",
      ] },
      { h: "3. Perché è sicuro firmarlo", li: [
        "Dove una fonte non è raggiungibile, i rilievi dicono \"sconosciuto\" invece di inventare una debolezza.",
        "Ogni rilievo porta con sé le prove su cui si fonda e la data in cui è stato osservato.",
        "È ripetibile, quindi l'incarico successivo parte da un punto di partenza misurato.",
      ] },
    ],
    win: { h: "La promessa, detta con chiarezza", p:
      "Il suo nome finisce sul documento. È esattamente per questo che un metodo che si rifiuta di " +
      "tirare a indovinare vale per lei più di uno che produce sempre un numero." },
    steps: [
      { k: "Pilota", v: "Un cliente, un'esecuzione, la sua analisi al di sopra." },
      { k: "Pacchetto", v: "Un'offerta con un nome, un perimetro fisso e un prezzo fisso." },
      { k: "Marchio", v: "La sua identità sulla piattaforma e su ogni documento." },
    ],
    cta: { btn: "Parliamone", txt: "Condizioni White-Label, di licenza e di volume su richiesta." },
  },

  // --------------------------------------------------------------------------------- TELCO
  {
    id: "telco", group: "partners", nav: "Operatori di telecomunicazioni",
    eyebrow: "Partner", h2: "Per gli operatori di telecomunicazioni",
    scr: {
      s: "Vende connettività a migliaia di clienti business e vuole agganciare la sicurezza prima che la connettività diventi pura commodity.",
      c: "Una practice di sicurezza gestita richiede analisti che non riesce ad assumere, a un margine che il mercato non paga, per una base clienti troppo ampia per essere servita uno alla volta.",
      a: "Venda un servizio di sicurezza il cui costo non cresce con il numero dei clienti, erogato dagli account manager che già impiega.",
    },
    cols: [
      { h: "1. Che cosa vende", li: [
        "Un servizio di assessment a marchio: il suo portale, la sua fattura, il suo prezzo.",
        "Le licenze come linea ricorrente, a pacchetti o in formula illimitata.",
        "Una revisione ricorrente che rende il contratto di connettività più difficile da sostituire di quanto faccia il solo prezzo.",
      ] },
      { h: "2. Come raggiunge la base clienti", li: [
        "La agganci al momento della vendita, mentre si firma l'ordine di connettività.",
        "Nessun nuovo processo di vendita: i suoi account manager sono il canale.",
        "Raggiunge la coda lunga dei piccoli clienti che non potrà mai servire con le persone.",
      ] },
      { h: "3. Dove viene eseguito", li: [
        "Nel suo ambiente, oppure in un cloud nazionale dove la normativa lo richiede.",
        "Nel Paese indicato dalla sua autorità, server di licenza incluso.",
        "Nelle lingue che il suo mercato legge davvero.",
      ] },
    ],
    win: { h: "La promessa, detta con chiarezza", p:
      "È la rara offerta di sicurezza che una base clienti delle sue dimensioni può davvero " +
      "assorbire, perché nulla al suo interno richiede un analista per cliente." },
    steps: [
      { k: "Provare", v: "Lo esegua su un campione della sua base clienti." },
      { k: "Marchio", v: "Personalizzi la piattaforma e ogni documento come suoi." },
      { k: "Agganciare", v: "Lo inserisca nel modulo d'ordine della connettività." },
    ],
    cta: { btn: "Parliamone", txt: "Condizioni White-Label, di integrazione, di licenza e di volume su richiesta." },
  },

  // ----------------------------------------------------------------------------------- SME
  {
    id: "sme", group: "buyers", nav: "Piccole e medie imprese",
    eyebrow: "Acquirente", h2: "Per le piccole e medie imprese",
    note:
      "Per piccola o media impresa si intende qui un'azienda da circa dieci a duecentocinquanta " +
      "dipendenti, in cui una sola persona si occupa dell'informatica oltre a un altro lavoro. " +
      "Questa pagina è scritta per quell'azienda: il titolare, l'amministratore delegato o quella " +
      "singola persona.",
    scr: {
      s: "Le dicono che la sua azienda deve prendere sul serio la sicurezza informatica, e lei è d'accordo.",
      c: "Il consiglio è di comprare un penetration test, un consulente e una serie di policy. Tutti e tre costano più del rischio che qualcuno le abbia mai quantificato, e nessuno dei tre risponde all'unica domanda che ha davvero.",
      a: "Scopra che cosa un estraneo può vedere della sua azienda dall'esterno, questa settimana, senza installare nulla e senza far entrare nessuno nella sua rete.",
    },
    cols: [
      { h: "1. Che cosa riceve", li: [
        "Tutto ciò che le appartiene ed è rivolto verso internet, comprese le cose che nessuno ricordava.",
        "Quanto le costerebbe se andasse male, in denaro, con il metodo esposto.",
        "Quali leggi la riguardano ed entro quando, in parole semplici.",
      ] },
      { h: "2. Perché è adatto a un'azienda delle sue dimensioni", li: [
        "Niente da installare. Nessun software, nessun accesso, nessuno che venga in ufficio.",
        "Lei fornisce il nome di un'azienda. Questa è tutta la configurazione.",
        "Lo esegua di nuovo ogni volta che qualcosa cambia, invece che una volta l'anno quando se lo può permettere.",
      ] },
      { h: "3. Che cosa può farne", li: [
        "Lo inoltri così com'è a un cliente che la sta verificando.",
        "Lo dia alla sua banca o al suo assicuratore senza bisogno di traduzioni.",
        "Lo consegni al suo fornitore informatico come elenco di lavori.",
      ] },
    ],
    channel: {
      b: "Come si acquista.",
      t: "Tramite un partner, non direttamente da noi. Scelga uno dei nostri partner certificati " +
         "nella sua zona, oppure ci presenti l'azienda informatica di cui già si fida e la porteremo " +
         "a bordo. Lei mantiene la relazione che ha. Loro acquisiscono la capacità. La scelta è sua.",
    },
    win: { h: "La promessa, detta con chiarezza", p:
      "Quasi tutte le aziende delle sue dimensioni trovano almeno una cosa che non sapevano fosse " +
      "visibile da internet. Trovarla le costa un pomeriggio invece di un progetto." },
    steps: [
      { k: "Ora", v: "Guardi la dimostrazione pubblica. Documenti reali, azienda inventata." },
      { k: "Poi", v: "Chieda a noi, o al suo fornitore, un'esecuzione sul suo nome." },
      { k: "Dopo", v: "Risolva ciò che conta, poi lo esegua di nuovo per dimostrare che è chiuso." },
    ],
    cta: { btn: "Trovi un partner", txt: "Prezzi e condizioni arrivano dal suo partner. Ci dica la sua zona e glielo presenteremo, oppure porti il suo." },
  },

  // ---------------------------------------------------------------------------- ENTERPRISE
  {
    id: "enterprise", group: "buyers", nav: "Grandi imprese",
    eyebrow: "Acquirente", h2: "Per le grandi imprese",
    scr: {
      s: "Ha team di sicurezza, strumenti maturi e un budget reale. Ognuno di quei team possiede una parte del quadro.",
      c: "Nessuno sa dire come appare l'intero gruppo visto dall'esterno, e dimostrarlo. Controllate e acquisizioni lasciano asset che nessun team rivendica. Il rischio fornitori si valuta con un modulo che il fornitore compila su se stesso.",
      a: "Una sola vista esterna dell'intero gruppo, quantificata in denaro, ripetuta a cadenza fissa, con un report di che cosa è esattamente cambiato dall'ultima esecuzione.",
    },
    cols: [
      { h: "1. Copertura che i suoi strumenti non hanno", li: [
        "L'intero gruppo, comprese le controllate e i marchi che non portano il nome della capogruppo.",
        "I fornitori valutati allo stesso modo, senza accessi e senza questionari.",
        "Le aziende appena acquisite, prima che la loro rete venga collegata alla sua.",
      ] },
      { h: "2. Output modellato sulla sua organizzazione", li: [
        "I rilievi per la sicurezza di rete. Il rischio in denaro per il direttore finanziario e per il comitato rischi.",
        "Gli attori delle minacce per il consiglio. La conformità per l'audit interno.",
        "Nessun team deve mettersi d'accordo con un altro team per poter usare il proprio documento.",
      ] },
      { h: "3. Costruito per reggere le contestazioni", li: [
        "Ogni rilievo riporta l'indirizzo, la porta, le prove e la data.",
        "La definizione del perimetro è volutamente conservativa: il server di un'altra azienda su infrastruttura condivisa non viene mai riportato come suo.",
        "Dove una fonte non è raggiungibile riporta \"sconosciuto\" invece di dedurre una debolezza.",
      ] },
    ],
    change: {
      h: "Il report delle variazioni, che è la parte che conta",
      lead:
        "Un singolo assessment le dice a che punto è. Non può dirle se qualcosa stia migliorando. Lo " +
        "esegua di nuovo e la piattaforma confronta le due esecuzioni e riporta solo ciò che si è mosso.",
      cells: [
        { k: "new", t: "Nuovo", b: "non esistevano l'ultima volta",
          before: "Esposizioni che ", after: ": un servizio pubblicato da qualcuno, un certificato scaduto, un server arrivato con un'acquisizione." },
        { k: "closed", t: "Chiuso", b: "spariti",
          before: "Rilievi ormai ", after: ". Questa è la prova che un budget di rimedio ha prodotto un risultato, ed è la cosa più difficile da dimostrare nella sicurezza." },
        { k: "open", t: "Ancora aperto", b: "non si sono mossi",
          before: "Rilievi sollevati in precedenza che ", after: ", con l'indicazione di da quanto tempo sono aperti. Questa è la lista di escalation, e si scrive da sola." },
      ],
      tailBefore: "Il suo processo di conformità non vuole un report. Vuole una risposta datata e documentata a una sola domanda: ",
      tailBold: "che cosa è cambiato, e qualcuno ha risolto quello che avevamo segnalato?",
      tailAfter: " È questo che lo trasforma da progetto a controllo, ed è la ragione per eseguirlo a cadenza fissa invece che una sola volta.",
    },
    channel: {
      b: "Come si acquista.",
      t: "Attraverso il canale. Scelga uno dei nostri partner certificati, oppure indichi il system " +
         "integrator con cui già lavora e lo porteremo a bordo. Il suo processo di acquisto, i suoi " +
         "contratti e i suoi rapporti con i fornitori restano come sono.",
    },
    win: { h: "La promessa, detta con chiarezza", p:
      "I suoi team mantengono ogni strumento che hanno. Questo risponde all'unica domanda a cui " +
      "nessuno di quegli strumenti è puntato: che cosa il mondo esterno vede di tutto ciò che " +
      "possiede. Poi dimostra, mese dopo mese, se quella superficie si stia riducendo." },
    steps: [
      { k: "Provare", v: "Una sola divisione. La confronti con quello che credeva di avere." },
      { k: "Estendere", v: "Aggiunga le controllate e i fornitori più critici." },
      { k: "Operare", v: "Lo metta a calendario e gestisca il report delle variazioni." },
    ],
    cta: { btn: "Parliamone", txt: "Accordi enterprise, accesso all'interfaccia di programmazione e documentazione di sicurezza passano dal suo partner o dal nostro." },
  },

  // ----------------------------------------------------------------------------------- LAW
  {
    id: "law", group: "buyers", nav: "Studi legali",
    eyebrow: "Acquirente", h2: "Per gli studi legali",
    scr: {
      s: "Assiste su protezione dei dati, incidenti informatici, fusioni e acquisizioni ed esposizione regolamentare.",
      c: "Le servono abitualmente fatti tecnici su un'azienda che non ha alcun titolo per toccare. Testare i sistemi di un'altra parte senza autorizzazione crea esattamente la responsabilità che il suo lavoro serve a prevenire.",
      a: "Prove tecniche ottenute senza fare nulla a nessuno, ed è precisamente questo a renderle utilizzabili nel suo lavoro.",
    },
    cols: [
      { h: "1. Dove si applica", li: [
        "**Due diligence in un'operazione:** il reale patrimonio esterno del target e il suo rischio quantificato, prima della firma del contratto di acquisto.",
        "**Dopo un incidente:** un quadro indipendente e datato di ciò che era pubblicamente visibile.",
        "**Contenziosi:** un allegato tecnico che un altro perito può riprodurre.",
      ] },
      { h: "2. Perché è lecito usarlo", li: [
        "Interamente passivo. Non un solo pacchetto raggiunge l'azienda analizzata.",
        "Nulla viene sfruttato e in nulla si effettua un accesso.",
        "Costruito solo su fonti che qualsiasi ricercatore può consultare legittimamente, quindi non serve l'autorizzazione di nessuno.",
      ] },
      { h: "3. Che cosa può mettere davanti a un cliente", li: [
        "Ogni rilievo con le sue prove e la data in cui è stato acquisito.",
        "Quali normative si applicano, con obblighi e scadenze citati dai testi originali.",
        "L'esposizione convertita in un importo che il consiglio del suo cliente comprende.",
      ] },
    ],
    win: { h: "La promessa, detta con chiarezza", p:
      "Produce fatti tecnici con l'unica proprietà che il suo lavoro esige: sono stati ottenuti " +
      "senza fare nulla a nessuno. È questo a renderli utilizzabili." },
    steps: [
      { k: "Valutare", v: "Lo esegua su una pratica che già segue." },
      { k: "Verificare", v: "Metta alla prova la catena delle prove secondo il suo standard." },
      { k: "Adottare", v: "Lo renda un passo standard nella due diligence e nella gestione degli incidenti." },
    ],
    cta: { btn: "Parliamone", txt: "Condizioni per singola pratica o per l'intero studio, attraverso il canale. L'output non è consulenza legale e non sostituisce il parere di un avvocato." },
  },

  // ----------------------------------------------------------------------------- INSURANCE
  {
    id: "insurance", group: "buyers", nav: "Assicuratori",
    eyebrow: "Acquirente", h2: "Per assicuratori, agenti e broker",
    scr: {
      s: "Sottoscrive polizze cyber e le tariffa in base a ciò che il proponente dichiara di sé.",
      c: "Il questionario è autodichiarato, ottimista e superato il giorno stesso della firma. Al rinnovo non può sapere se ciò che l'assicurato aveva promesso di correggere sia stato corretto. Dopo un sinistro non può dimostrare che cosa era visibile.",
      a: "Assuma il rischio su ciò che è osservabile invece che su ciò che è dichiarato, su ogni rischio, a un costo che non cresce con il numero dei rischi.",
    },
    cols: [
      { h: "1. Quale premio deve avere questo rischio?", li: [
        "Una perdita attesa e un caso peggiore annuo, prodotti con il riconosciuto metodo Factor Analysis of Information Risk.",
        "I calcoli sono esposti, quindi si tratta di un input tecnico alla sua decisione tariffaria e non di un punteggio uscito da una scatola nera.",
        "Disponibile prima ancora che il proponente l'abbia scelta, perché non richiede alcuna collaborazione.",
      ] },
      { h: "2. Che cosa c'è davvero sul loro perimetro?", li: [
        "Ogni esposizione rivolta verso internet, ordinata, con l'indirizzo e la porta.",
        "Indipendente dal questionario, quindi i due si possono confrontare.",
        "Consegnato in pochi minuti, quindi sta dentro un processo di quotazione.",
      ] },
      { h: "3. Sono conformi?", li: [
        "La loro posizione rispetto alle leggi cyber che li riguardano, con le scadenze.",
        "La non conformità è insieme un fattore di perdita e una questione di copertura.",
        "I regimi dell'Unione Europea e del Canada sono già attivi oggi.",
      ] },
    ],
    ladder: { h: "Lungo tutta la vita della polizza", items: [
      { b: "Alla quotazione.", t: "Pochi minuti, nessuna collaborazione necessaria." },
      { b: "Al rinnovo.", t: "Il report delle variazioni mostra il rimedio, o la sua assenza. Tariffi la differenza." },
      { b: "Sull'intero portafoglio.", t: "Rilanci l'analisi su tutto il portafoglio quando compare una nuova vulnerabilità ampiamente sfruttata, e conosca la sua esposizione cumulata lo stesso giorno." },
      { b: "Al sinistro.", t: "Un registro datato di ciò che era visibile dall'esterno." },
    ] },
    win: { h: "La promessa, detta con chiarezza", p:
      "Passa dal sottoscrivere ciò che il proponente dichiara al sottoscrivere ciò che si può " +
      "osservare, in modo coerente, su ogni rischio. È un discorso sul loss ratio, non sulla tecnologia." },
    steps: [
      { k: "Calibrare", v: "Lo esegua su rischi già sottoscritti, compresi quelli che hanno prodotto perdite." },
      { k: "Confrontare", v: "Metta i risultati accanto ai questionari e osservi gli scostamenti." },
      { k: "Integrare", v: "Nel processo di quotazione, oppure nel suo portale broker." },
    ],
    cta: { btn: "Parliamone", txt: "Condizioni per portafoglio, interfaccia di programmazione e integrazione su richiesta." },
  },

  // ----------------------------------------------------------------------------- REGULATOR
  {
    id: "regulator", group: "buyers", nav: "Autorità di vigilanza",
    eyebrow: "Acquirente", h2: "Per autorità di regolamentazione e vigilanza",
    scr: {
      s: "Vigila su una popolazione di soggetti con un mandato di sicurezza informatica o di resilienza operativa.",
      c: "La legge è scritta e le scadenze sono reali. La sua capacità tecnica non lo è. In pratica ispeziona pochi soggetti l'anno, scelti senza una base tecnica. Non può sapere se quelli non ispezionati siano quelli che contano.",
      a: "Vigili sull'intera popolazione a partire da prove pubbliche, senza visitare nessuno, e trasformi ogni violazione in un fascicolo istruito che il suo funzionario esamina e firma.",
    },
    cols: [
      { h: "1. Copertura invece di campionamento", li: [
        "Ogni soggetto vigilato, valutato con lo stesso metodo nello stesso giorno.",
        "I risultati sono confrontabili nell'intero settore, perché nulla viene misurato in modo diverso.",
        "Ripetibile a cadenza fissa, così può misurare la direzione di marcia del settore.",
      ] },
      { h: "2. Prove che reggono le contestazioni", li: [
        "Per ogni soggetto: l'indirizzo, la porta, le prove e la data di osservazione.",
        "Mappate sull'articolo specifico che viene violato.",
        "Dove una fonte non è raggiungibile riporta \"sconosciuto\" e non afferma alcuna violazione.",
      ] },
      { h: "3. Lecito per costruzione", li: [
        "Interamente passivo. Nessun soggetto viene toccato, quindi non sorge alcun obbligo di notifica o autorizzazione.",
        "Riproducibile, quindi resiste alla revisione dei periti del soggetto stesso.",
        "Installabile nel suo ambiente o in un ambiente nazionale dove il mandato lo richieda.",
      ] },
    ],
    ladder: { h: "La catena sanzionatoria, applicata all'intera popolazione", items: [
      { b: "Rilevare.", t: "Una condizione di non conformità su un soggetto vigilato, con l'indirizzo, la porta e la data di osservazione." },
      { b: "Mappare.", t: "L'articolo specifico che viene violato, nel diritto europeo o nel suo strumento nazionale." },
      { b: "Riscontrare.", t: "Quattro modelli di intelligenza artificiale indipendenti, di quattro fornitori diversi, esaminano il caso. Due lo costruiscono e due cercano di smontarlo. La decisione la prendono regole fisse scritte nel codice, non i modelli, e un caso che nessuno di loro riesce a riscontrare non esce mai dalla coda." },
      { b: "Redigere.", t: "Il fascicolo probatorio e l'atto sanzionatorio vengono preparati automaticamente." },
      { b: "Decidere.", t: "Il suo funzionario esamina e firma. La macchina costruisce il caso e l'autorità lo emette, ed è questo a mantenere ogni atto sindacabile e impugnabile." },
    ] },
    win: { h: "La promessa, detta con chiarezza", p:
      "Smette di scegliere chi ispezionare in base alla reputazione. Inizia a vigilare sull'intero " +
      "settore in base alle prove, senza mandare un ispettore in un solo edificio e senza che un " +
      "solo pacchetto raggiunga un soggetto vigilato." },
    steps: [
      { k: "Pilota", v: "Un settore, un gruppo di soggetti. Li metta in ordine." },
      { k: "Confronto", v: "Metta la classifica a confronto con la sua conoscenza di vigilanza." },
      { k: "Scala", v: "L'intera popolazione, a cadenza fissa, con la coda sanzionatoria." },
    ],
    cta: { btn: "Parliamone", txt: "Acquisti della pubblica amministrazione, luogo di hosting e condizioni su richiesta." },
  },

  // --------------------------------------------------------------------------- WHITE-LABEL
  {
    id: "whitelabel", group: "engage", nav: "White-Label", accent: "purple",
    eyebrow: "Come collaborare, modello 1 di 2", h2: "White-Label",
    scr: {
      s: "Vuole un servizio di sicurezza da vendere con il suo nome.",
      c: "Costruire il motore richiede anni. Rivendere il marchio di qualcun altro significa che la relazione con il cliente è con loro e non con lei.",
      a: "Il suo marchio davanti, il nostro motore sotto. Il suo cliente, il suo contratto, il suo prezzo, e loro non ci vedono mai.",
    },
    cols: [
      { h: "Che cosa diventa suo", li: [
        "Il marchio su ogni schermata e su tutti e quattro i documenti.",
        "La relazione con il cliente, il contratto e la fattura.",
        "Il suo listino, stabilito da lei, per il suo mercato.",
        "Il luogo di esecuzione: il suo cloud, la sua regione o un ambiente nazionale. Il server di licenza può stare nel Paese o nella regione che lei richiede.",
      ] },
      { h: "Che cosa non diventa suo", li: [
        "Il codice sorgente e la proprietà della piattaforma. Riceve una licenza per usarla e presentarla, non per possederla.",
        "Il diritto di concedere in licenza il software stesso a terzi.",
        "Lo sviluppo del motore e le sue garanzie di correttezza. Restano a noi, e sono ciò su cui lei fa affidamento.",
      ] },
    ],
    win: { h: "Scelga questo modello se", p:
      "Vuole un prodotto da vendere: qualcosa a cui il suo cliente accede con il suo nome sopra. È " +
      "il modello giusto per managed service provider, operatori di telecomunicazioni, società di " +
      "consulenza e rivenditori che stanno costruendo una practice di sicurezza." },
    steps: [
      { k: "Perimetro", v: "Marchio, regione di hosting, lingue, quali moduli." },
      { k: "Realizzazione", v: "Lo personalizziamo e lo mettiamo in esercizio. Lei lo collauda secondo criteri concordati." },
      { k: "Vendita", v: "Con il suo nome, al suo prezzo." },
    ],
    cta: { btn: "Parliamone", txt: "Impegni, perimetro di attivazione e listino sono materia commerciale e riservata. Ce lo chieda." },
  },

  // ----------------------------------------------------------------------------------- OEM
  {
    id: "oem", group: "engage", nav: "Integrato (OEM)", accent: "purple",
    eyebrow: "Come collaborare, modello 2 di 2", h2: "Integrato, chiamato anche OEM",
    scr: {
      s: "Ha già un prodotto a cui i suoi clienti accedono ogni giorno.",
      c: "Vendere un prodotto separato accanto ad esso crea attrito: un altro accesso, un altro contratto, un'altra cosa da spiegare. Inoltre diluisce il prodotto che ha costruito in anni.",
      a: "Il nostro motore dentro il suo prodotto, così il suo cliente vede una nuova funzionalità invece di un nuovo prodotto da valutare.",
    },
    cols: [
      { h: "Come funziona", li: [
        "Lei chiama la nostra interfaccia di programmazione. Rilievi, rischio quantificato, contesto sugli attori delle minacce, valutazioni di conformità e documenti finiti tornano come dati.",
        "Li mostra nella sua interfaccia, nella sua struttura.",
        "I rilievi critici vengono inviati alla sua piattaforma o al suo sistema di monitoraggio della sicurezza nel momento in cui si verificano, quindi non c'è nulla da interrogare.",
        "Installabile nel suo ambiente, nella regione che la sua architettura o la sua autorità richiede.",
      ] },
      { h: "Che cosa le dà", li: [
        "Una nuova capacità in un prodotto esistente, senza una nuova voce da far approvare al cliente.",
        "Nessun secondo accesso, nessun secondo contratto, nessun secondo canale di assistenza.",
        "Pieno controllo dell'esperienza, della sua posizione nella roadmap e del modo in cui la prezza.",
        "Può comunque rivendere licenze come linea separata dove un cliente lo richieda.",
      ] },
    ],
    vs: {
      a: { h: "White-Label è", bold: "prodotto", before: "Un ", after: " che sembra suo. Il suo cliente accede a qualcosa che porta il suo marchio. Ideale quando sta costruendo una practice di servizi e le serve qualcosa da vendere." },
      b: { h: "Integrato è", bold: "capacità", before: "Una ", after: " dentro il suo prodotto. Il suo cliente vede una nuova funzionalità, non un nuovo prodotto. Ideale quando possiede già la schermata che il suo cliente guarda e non vuole aggiungerne una seconda." },
    },
    win: { h: "Scelga questo modello se", p:
      "È un vendor software o di sicurezza, un assicuratore con un portale o un'azienda piattaforma. " +
      "Il criterio è semplice. Se il suo cliente accede già a qualcosa di suo, scelga l'integrato. Se " +
      "non lo fa, scelga il White-Label." },
    steps: [
      { k: "Progettare", v: "Quali chiamate, quali dati, dove compaiono." },
      { k: "Integrare", v: "Chiavi con perimetro definito, callback firmati, una specifica versionata." },
      { k: "Rilasciare", v: "Diventa una funzionalità della sua piattaforma." },
    ],
    cta: { btn: "Parliamone", txt: "Profondità dell'integrazione, volumi e condizioni sono materia commerciale. Ce lo chieda." },
  },

  // ------------------------------------------------------------------------------- CONTACT
  {
    id: "contact", group: "engage", nav: "Parliamone",
    eyebrow: "Prossimo passo", h2: "Parliamone",
    note:
      "Prezzi, livelli, modelli di licenza, impegni e condizioni contrattuali sono materia " +
      "commerciale e si concordano direttamente. Per scelta non sono pubblicati qui.",
    cols: [
      { h: "Che cosa possiamo fare questa settimana", li: [
        "Un'esecuzione dal vivo su un nome di azienda scelto da lei, così giudica l'output e non la presentazione.",
        "Una call di referenza con un partner che già lo vende nel mercato di lingua tedesca.",
        "Il pacchetto legale: contratto di partnership, addendum White-Label e di integrazione, accordo di riservatezza, accordo sui livelli di servizio, condizioni d'uso, accordo sul trattamento dei dati e una scheda tecnica sull'hosting.",
        "La documentazione sull'architettura di sicurezza che il suo responsabile della sicurezza o l'ufficio acquisti chiederà.",
      ] },
      { h: "Che cosa le chiederemo", li: [
        "Quale dei destinatari qui sopra rappresenta. Cambia la risposta in modo sostanziale.",
        "Se vuole rivenderlo, marchiarlo oppure integrarlo nel suo prodotto.",
        "Se vende licenze, servizi o entrambi.",
        "Dove devono risiedere i dati e il server di licenza.",
      ] },
    ],
    cta: { btn: "Ci scriva", ghost2: "Guardi prima la dimostrazione pubblica", txt: "Cybergod LLC, parte del S4Biz Group" },
  },
];
