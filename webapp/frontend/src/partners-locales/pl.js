// partners-locales/pl.js — the POLISH translation of the /partners content.
//
// en.js IS THE REFERENCE. It carries the full reasoning about why this page is data and not JSX,
// why it lives in its own locale folder, and which content rules apply. Read it first; this file
// only carries the Polish text.
//
// THE OBJECT SHAPE IS ASSERTED BY tools/partners_gate.mjs: the same three exports, the same
// section ids in the same order, the same number of columns per section and the same number of
// bullets per column. Adding, removing, merging or reordering anything here is a failed build.
// Only the TEXT differs from en.js.
//
// LOOKUP KEYS THAT ARE DELIBERATELY NOT TRANSLATED: every `id`, every `group`, every `accent`,
// every `k` inside `change.cells` ("new", "closed", "open"), and `arts[].n`. Translating a lookup
// key makes content silently vanish.
//
// LANGUAGE RULES: no long dashes, no HTML entities (React escapes them, so they would reach the
// screen verbatim), no prices, no percentages, no seat counts. Formal business register
// throughout ("Państwo"). "findings" is rendered consistently as "ustalenia".

export const meta = {
  docTitle: "Dla kogo to jest",
  kicker: "Jedna nazwa na wejściu. Cztery dokumenty gotowe dla zarządu na wyjściu. Jedenaście grup odbiorców.",
  h1a: "Wystarczy nazwa firmy.",
  h1b: "Otrzymują Państwo ",
  h1c: "pełny obraz ryzyka",
  h1d: " w kilka minut.",
  lede:
    "Do ocenianej firmy nie zostaje wysłany ani jeden pakiet. Wszystko powstaje ze źródeł, z " +
    "których każdy badacz może legalnie korzystać. Nie ma więc czego instalować, nie trzeba " +
    "nikogo prosić o zgodę ani czekać na wypełnioną ankietę. Za każdym razem wracają cztery dokumenty.",
  artsNote:
    "Jest jeszcze piąty dokument: jeden samodzielny raport internetowy, który łączy wszystkie " +
    "cztery i otwiera się w dowolnej przeglądarce. To ten dokument ludzie przesyłają dalej " +
    "wewnątrz firmy. Każdy dokument jest dostępny po angielsku, niemiecku lub rosyjsku.",
  railTitle: "Dla kogo to jest",
  groupPartners: "Partnerzy",
  groupBuyers: "Kupujący",
  groupEngage: "Formy współpracy",
  foot:
    "Treść pochodzi z materiałów informacyjnych dla partnerów i regulatorów oraz z podpisanego " +
    "pakietu prawnego. Ceny, rabaty, liczby stanowisk i zobowiązania celowo nigdzie się nie " +
    "pojawiają. Liczby spotkań partnerskich pochodzą ze zgłoszeń samych partnerów i zależą od " +
    "konkretnego handlowca. Wynik oceny nie stanowi porady prawnej. Wszystkie odniesienia do " +
    "zidentyfikowanych klientów zostały usunięte.",
};

export const arts = [
  { n: "1", name: "Ustalenia", body:
    "Każda ekspozycja widoczna od strony internetu, uszeregowana od krytycznej do niskiej. Każda " +
    "mówi, czym jest, dlaczego ma znaczenie, jak ją usunąć oraz na jakim dokładnie adresie i " +
    "porcie została zaobserwowana." },
  { n: "2", name: "Ryzyko w pieniądzu", body:
    "Te same ustalenia wyrażone w walucie, uznaną metodą Factor Analysis of Information Risk. " +
    "Koszt jednego incydentu, najgorszy przypadek w skali roku oraz krzywa, która opada wraz z " +
    "zamykaniem ustaleń. Napisane dla dyrektora finansowego." },
  { n: "3", name: "Sprawcy zagrożeń", body:
    "Którzy napastnicy są naprawdę istotni dla tej branży i tych krajów oraz jak działają. " +
    "Odpowiedź na pytanie zarządu, kto miałby po nas przyjść." },
  { n: "4", name: "Zgodność", body:
    "Ustalenia odwzorowane na przepisy prawa obowiązujące tam, gdzie firma prowadzi działalność, " +
    "wraz z rzeczywistymi terminami. Dziś Unia Europejska i Kanada." },
];

export const sections = [
  // ------------------------------------------------------------------ MANAGED SERVICE PROVIDERS
  {
    id: "msp", group: "partners", nav: "Dostawcy usług zarządzanych",
    eyebrow: "Partner", h2: "Dla dostawców usług zarządzanych",
    scr: {
      s: "Prowadzą Państwo bezpieczeństwo dla wielu klientów naraz, zespołem, który nie rośnie tak szybko jak lista klientów.",
      c: "Ręczny przegląd ekspozycji jednego klienta kosztuje około dnia pracy analityka. Przy skali to się po prostu nie dzieje, więc kwartalny przegląd biznesowy staje się aktualizacją statusu, pod którą nikt nie planuje budżetu.",
      a: "Każdy klient w portfelu oceniany w tym samym rytmie, przy koszcie, który nie rośnie wraz z liczbą klientów. Naprawę sprzedają Państwo potem w czterech osobnych punktach cenowych.",
    },
    cols: [
      { h: "1. Co Państwo sprzedają", li: [
        "Samą ocenę, wycenioną, pod własną marką.",
        "Miesięczne lub kwartalne powtórzenie z raportem o tym, co się zmieniło. Ten raport to właśnie usługa zarządzana.",
        "Licencje, sprzedawane w pakietach lub bez limitu, na których zarabiają Państwo osobno.",
      ] },
      { h: "2. Dlaczego koszt się zgadza", li: [
        "Jeden analityk obsługuje cały portfel zamiast jednego klienta.",
        "Uruchomienie klienta nie wymaga od niego niczego: żadnej instalacji, żadnych dostępów, żadnego formularza.",
        "Dokument zgodności odpowiada audytorowi w tym samym przebiegu, więc nie ma drugiego projektu do obsadzenia.",
      ] },
      { h: "3. Gdzie jest marża", li: [
        "Nie w raporcie. W czterech sposobach zamknięcia ustalenia, opisanych poniżej.",
        "Opiekunowie klienta zyskują powód, by dzwonić do każdego klienta co miesiąc z konkretną wiadomością.",
        "Zamknięte ustalenie dowodzi, że abonament działa, a to najtrudniejsza rzecz do wykazania w bezpieczeństwie.",
      ] },
    ],
    ladder: { h: "Cztery sposoby zamknięcia ustalenia, od najtańszego", items: [
      { b: "Doradztwo.", t: "Warsztat, który przechodzi przez każde ustalenie w zestawieniu z tym, co klient już posiada." },
      { b: "Bez nowych wydatków, na własnym sprzęcie klienta.", t: "Większość ustaleń zamyka się przez zmiany konfiguracji, umiejscowienia i procesu na produktach, za które klient już płaci. Dostarczają Państwo listę działań, każde przypisane do narzędzia, które je zamyka." },
      { b: "Open source.", t: "Tam, gdzie istniejący sprzęt luki nie zamknie, projekt oparty na open source zamiast zakupu. Nie ma licencji do kupienia. Koszt przenosi się na kompetencje i utrzymanie, które klient albo zatrudnia, albo kupuje od Państwa." },
      { b: "Produkt komercyjny.", t: "Tylko tam, gdzie żadne z powyższych nie zadziała. Wybór pozostaje w ramach zatwierdzonej listy dostawców klienta. Doradzają Państwo w zakresie dopasowania, kolejności i integracji." },
    ] },
    win: { h: "Teza, powiedziana wprost", p:
      "Pojedynczy raport to projekt. Comiesięczny raport o tym, co się zmieniło, to abonament. " +
      "Sprzedają Państwo ustalenie i drogę do jego usunięcia, w czterech punktach cenowych, " +
      "klientowi, który już Państwu ufa." },
    steps: [
      { k: "Tydzień 1", v: "Przebieg na dziesięciu największych klientach i lektura tego, co wraca." },
      { k: "Tydzień 2", v: "Wysyłka jednego ustalenia do każdego z nich. Metoda opisana poniżej." },
      { k: "Tydzień 3", v: "Własna marka na dokumencie i wycena w ramach pakietu zarządzanego." },
    ],
    cta: { btn: "Porozmawiajmy", txt: "Pakiety licencji, plany bez limitu, poziomy i warunki są kwestią handlową. Prosimy pytać." },
  },

  // ------------------------------------------------------------------------------- RESELLERS
  {
    id: "var", group: "partners", nav: "Resellerzy",
    eyebrow: "Partner", h2: "Dla resellerów",
    scr: {
      s: "Sprzedają Państwo technologię i wygrywają relacją, wyczuciem czasu oraz jakością rozmowy, którą potrafią zacząć.",
      c: "Pierwsze spotkanie techniczne jest najtrudniejsze do zdobycia. Zwykłym zamiennikiem jest rabat, który kosztuje marżę i uczy klienta, żeby czekał na następny.",
      a: "Wchodzą Państwo na spotkanie, wiedząc już, co jest odsłonięte na ich styku z internetem. Za ocenę biorą Państwo pełną cenę, a jej wartość zaliczają na poczet prac, które ona ujawni.",
    },
    cols: [
      { h: "1. Jak jest wyceniona", li: [
        "Ocena to płatne zlecenie o ustalonym zakresie. To nie jest prezent.",
        "Jej wartość zostaje następnie zaliczona na poczet doradztwa lub prac naprawczych, które po niej nastąpią.",
        "Klient nie ryzykuje więc niczego, a Państwo otrzymują zapłatę w każdym wariancie.",
      ] },
      { h: "2. Na czym jeszcze Państwo zarabiają", li: [
        "Licencje, w pakietach lub bez limitu, jako druga i powtarzalna linia przychodu.",
        "Wszystkie cztery sposoby zamknięcia ustalenia: doradztwo, własny sprzęt klienta, open source albo zatwierdzony produkt.",
        "Powtórne przebiegi, które pokazują, co się zmieniło, i wznawiają rozmowę w stałym rytmie.",
      ] },
      { h: "3. Co zyskuje zespół sprzedaży", li: [
        "Powód, by zadzwonić do kogokolwiek, z czymś konkretnym do powiedzenia.",
        "Nowe logo: nie trzeba zgody ani dostępu, więc pracę można wykonać, zanim przyjdzie zaproszenie.",
        "Obrona odnowienia: przebieg przed datą odnowienia u konkurenta i pokazanie, co się zmieniło.",
      ] },
    ],
    win: { h: "Teza, powiedziana wprost", p:
      "Rabat kupuje jedną transakcję. Wiedza o ich styku z internetem większa niż ich własna kupuje " +
      "relację, a tym razem otrzymują Państwo zapłatę za pracę, która otworzyła drzwi." },
    steps: [
      { k: "Dzień 1", v: "Wybór pięciu potencjalnych klientów, u których nie da się umówić spotkania." },
      { k: "Dzień 2", v: "Wysyłka jednego ustalenia do każdego. Nigdy całego raportu." },
      { k: "Dzień 5", v: "Spotkanie. Wycena oceny. Zaliczenie jej na poczet dalszych prac." },
    ],
    cta: { btn: "Porozmawiajmy", txt: "Istnieją ścieżki poleceń, odsprzedaży, licencji i White-Label. Warunki na życzenie." },
  },

  // ------------------------------------------------------------------------------ THE METHOD
  {
    id: "play", group: "partners", nav: "Metoda otwarcia", accent: "gold",
    eyebrow: "Korzysta z tego każdy partner", h2: "Wysyłają Państwo jedno ustalenie. Raport zostaje u Państwa.",
    scr: {
      s: "Ocena została wykonana i trzymają Państwo w ręku dokument, w którym jest wszystko.",
      c: "Potencjalny klient, który o raport nie prosił, czyta go jak materiał sprzedażowy i odkłada na bok. Pełny raport prosi też o termin spotkania, którego nikt w tym kwartale nie ma.",
      a: "Wysyłają Państwo dokładnie jedno ustalenie, z dowodem i sposobem naprawy. To pojedyncze ustalenie wygrywa spotkanie. Raport sprzedają Państwo dopiero na nim.",
    },
    quote: {
      q: "W ogóle nie widzę tego adresu w naszym systemie ewidencji zasobów.",
      by: "Inżynier bezpieczeństwa sieci w dużym przedsiębiorstwie regulowanym, obserwujący przebieg " +
          "na żywo. Platforma pokazała adres przypisany do jego własnej organizacji. Nie potrafił " +
          "go odnaleźć w wewnętrznej ewidencji zasobów. Firma, sektor i szczegóły nieujawnione.",
    },
    cols: [
      { h: "Jak to przeprowadzić", li: [
        "Wykonać ocenę, przeczytać ustalenia i wybrać dokładnie jedno.",
        "Wysłać to ustalenie wraz z dowodem i wskazówką, jak je naprawić.",
        "Nie załączać raportu. Przy kontakcie na zimno usunąć szczegóły identyfikujące.",
        "Poprosić o trzydzieści minut na omówienie reszty.",
      ] },
      { h: "Dlaczego jedno ustalenie bije raport", li: [
        "**Nieznany zasób to najsilniejszy rodzaj ustalenia.** Adres spoza ewidencji zasobów jest poza łataniem, skanowaniem i raportowaniem, a inwentaryzacja zasobów leży u podstaw każdego standardu bezpieczeństwa, z którego są audytowani.",
        "**Wytrzymuje sceptycyzm.** Na znane ustalenie pada odpowiedź \"tym zajmuje się inny zespół\". Adresu, którego nikt nie potrafi wyjaśnić, tak zbyć się nie da.",
        "**Pasuje do sali.** Trafia w zespół, z którym już Państwo rozmawiają, a nie w dział, którego nikt na spotkaniu nie kontroluje.",
        "**Sam się wycenia.** Jeden niezarządzany host wystawiony do internetu jest tani w dyskusji i drogi w zignorowaniu.",
      ] },
    ],
    win: { h: "Co raportują partnerzy", p:
      "Partnerzy w Niemczech i Szwajcarii stosujący tę metodę raportują od sześciu do dziesięciu " +
      "nowych pierwszych spotkań na handlowca tygodniowo. Zależy to oczywiście od umiejętności " +
      "konkretnego handlowca w zamianie faktu na rozmowę, dlatego wolimy, żeby usłyszeli to " +
      "Państwo od nich. Umówimy tę rozmowę." },
    cta: { btn: "Poproś o rozmowę referencyjną", ghost: true, txt: "Partnerzy referencyjni dostępni na rynku niemieckojęzycznym." },
  },

  // --------------------------------------------------------------------- SYSTEMS INTEGRATORS
  {
    id: "gsi", group: "partners", nav: "Integratorzy systemów",
    eyebrow: "Partner", h2: "Dla integratorów systemów",
    scr: {
      s: "Rozpoznanie jest pierwszą fazą każdego programu bezpieczeństwa i transformacji, który Państwo prowadzą.",
      c: "Jest rozliczane po stawkach konsultanckich, wykonywane ręcznie, inne na każdym projekcie, i to właśnie o tę fakturę klienci się spierają. A bez niego nic, co następuje później, nie ma podstaw.",
      a: "Rozpoznanie staje się stałym, szybkim i identycznym krokiem na każdym projekcie, a marża przenosi się na architekturę i naprawę, czyli tam, gdzie jej miejsce.",
    },
    cols: [
      { h: "1. Gdzie mieści się w metodyce", li: [
        "Rozpoznanie staje się wejściem do Państwa metodyki, a nie jej zamiennikiem.",
        "Punkt odniesienia na starcie programu, potem powtórzenie na każdej bramce etapowej.",
        "Postęp jest udokumentowany tym, co zostało zamknięte, zamiast deklarowany w raporcie statusu.",
      ] },
      { h: "2. Gdzie jeszcze się przydaje", li: [
        "Ocena dostawcy bez czekania, aż dostawca zechce współpracować.",
        "Określenie zakresu nowo przejętej spółki, zanim jej sieć zostanie połączona z siecią matki.",
        "Dowolny kraj lub spółka zależna, w których nie mają Państwo lokalnego zespołu.",
      ] },
      { h: "3. Co zmienia się handlowo", li: [
        "Przestają Państwo sprzedawać tygodnie zbierania faktów, a zaczynają sprzedawać rezultat, który one blokowały.",
        "Dokument pieniężny wycenia program językiem dyrektora finansowego już pierwszego dnia.",
        "Każde ustalenie niesie swój dowód, więc przechodzi przez przegląd techniczny po stronie klienta.",
      ] },
    ],
    win: { h: "Teza, powiedziana wprost", p:
      "Pierwsza faktura przestaje być tą, którą klient kwestionuje, ponieważ kupuje teraz " +
      "odpowiedź, a nie czynność." },
    steps: [
      { k: "Krok 1", v: "Przebieg na żywym projekcie i porównanie z tym, co zespół znalazł ręcznie." },
      { k: "Krok 2", v: "Włączenie do standardowego produktu fazy rozpoznania." },
      { k: "Krok 3", v: "Własna marka na dokumencie albo integracja. Dwa modele opisane na końcu." },
    ],
    cta: { btn: "Porozmawiajmy", txt: "Warunki wolumenowe, regionalne i integracyjne są kwestią handlową. Prosimy pytać." },
  },

  // ------------------------------------------------------------------------------- VENDORS
  {
    id: "vendors", group: "partners", nav: "Producenci cyberbezpieczeństwa",
    eyebrow: "Partner", h2: "Dla producentów cyberbezpieczeństwa",
    scr: {
      s: "Mają Państwo produkt, który rozwiązuje realny problem, i demonstrację, która pokazuje go w działaniu.",
      c: "Demonstracja dowodzi, że produkt działa w ogóle. Nie dowodzi, że ten klient ma ten problem dzisiaj, więc ewaluacja sprowadza się do porównania funkcji z konkurentem.",
      a: "Najpierw pokazują Państwo klientowi, co jest otwarte na jego własnym styku z internetem, a dopiero potem swój produkt. Po wdrożeniu powtarzają przebieg i pokazują w pieniądzu, co produkt zamknął.",
    },
    cols: [
      { h: "1. We własnym zespole sprzedaży", li: [
        "Każdy opiekun klienta nosi obraz ekspozycji konkretny dla tego klienta.",
        "Otwiera drzwi w firmach, które nigdy o Państwu nie słyszały, bez żadnych dostępów.",
        "Dokument pieniężny zamienia ekspozycję techniczną w pozycję budżetową.",
      ] },
      { h: "2. Wewnątrz produktu", li: [
        "Ekspozycja zewnętrzna staje się funkcją Państwa platformy, dostarczaną przez nasz interfejs programistyczny.",
        "Państwa interfejs, Państwa marka, żadnego drugiego produktu do oceny przez klienta.",
        "Dodaje spojrzenie z zewnątrz do produktu, który patrzy głównie do wewnątrz, a to realna luka w większości stosów bezpieczeństwa.",
      ] },
      { h: "3. Obok produktu", li: [
        "Przebieg przed wdrożeniem i po nim. Różnica to Państwa studium przypadku.",
        "Daje odnowieniom liczbę zamiast wrażenia.",
        "Mogą Państwo także odsprzedawać licencje obok własnych produktów.",
      ] },
    ],
    win: { h: "Teza, powiedziana wprost", p:
      "Nikt nie spiera się z własną powierzchnią ataku. To najkrótsza droga od demonstracji do budżetu." },
    steps: [
      { k: "Ocena", v: "Przebieg na trzech własnych otwartych szansach sprzedaży." },
      { k: "Decyzja", v: "Narzędzie sprzedażowe, linia odsprzedaży albo funkcja platformy." },
      { k: "Integracja", v: "Ustalenia trafiają do Państwa produktu przez interfejs programistyczny." },
    ],
    cta: { btn: "Porozmawiajmy", txt: "Warunki integracji i licencji zależą od wolumenu i głębokości integracji. Prosimy pytać." },
  },

  // ---------------------------------------------------------------------------- CONSULTING
  {
    id: "consulting", group: "partners", nav: "Firmy doradcze",
    eyebrow: "Partner", h2: "Dla firm doradczych",
    scr: {
      s: "Sprzedają Państwo osąd i niezależność. Klienci płacą za radę i za nazwisko na okładce.",
      c: "Zbieranie faktów pochłania większość projektu i jest tą częścią, za którą klienci najmniej chcą płacić. Rozliczają Państwo juniorów za zbieranie faktów, a partnerów za ich interpretację, a ceniona jest tylko ta druga praca.",
      a: "Zbieranie faktów skraca się z tygodni do dni, na wyniku staje Państwa marka, a sprzedają Państwo interpretację.",
    },
    cols: [
      { h: "1. Co można sprzedać", li: [
        "Płatny pierwszy projekt, dostarczony w kilka dni, który otwiera ten większy.",
        "Niezależną drugą opinię o programie bezpieczeństwa, który już trwa.",
        "Licencje, by klient korzystał dalej, na których Państwo zarabiają.",
      ] },
      { h: "2. Co zostaje po Państwu", li: [
        "Ustalenia dla dyrektora bezpieczeństwa.",
        "Ryzyko w pieniądzu dla dyrektora finansowego.",
        "Sprawcy zagrożeń dla zarządu, a zgodność dla komitetu audytu.",
      ] },
      { h: "3. Dlaczego można to bezpiecznie podpisać", li: [
        "Tam, gdzie źródło było nieosiągalne, ustalenia mówią \"nieznane\" zamiast wymyślać słabość.",
        "Każde ustalenie niesie dowód, na którym się opiera, oraz datę obserwacji.",
        "Jest powtarzalne, więc kolejny projekt ma zmierzony punkt startu.",
      ] },
    ],
    win: { h: "Teza, powiedziana wprost", p:
      "Na dokumencie staje Państwa nazwa. Właśnie dlatego metoda, która odmawia zgadywania, jest " +
      "dla Państwa warta więcej niż taka, która zawsze wyprodukuje liczbę." },
    steps: [
      { k: "Pilot", v: "Jeden klient, jeden przebieg, Państwa własna analiza na wierzchu." },
      { k: "Pakiet", v: "Nazwana oferta o stałym zakresie i stałej cenie." },
      { k: "Marka", v: "Państwa identyfikacja na platformie i na każdym dokumencie." },
    ],
    cta: { btn: "Porozmawiajmy", txt: "Warunki White-Label, licencyjne i wolumenowe na życzenie." },
  },

  // --------------------------------------------------------------------------------- TELCO
  {
    id: "telco", group: "partners", nav: "Operatorzy telekomunikacyjni",
    eyebrow: "Partner", h2: "Dla operatorów telekomunikacyjnych",
    scr: {
      s: "Sprzedają Państwo łączność tysiącom klientów biznesowych i chcą dołożyć bezpieczeństwo, zanim łączność stanie się czystym towarem.",
      c: "Praktyka zarządzanego bezpieczeństwa wymaga analityków, których nie da się zrekrutować, przy marży, której rynek nie zapłaci, dla bazy klientów o wiele za dużej, by obsługiwać ją pojedynczo.",
      a: "Sprzedają Państwo usługę bezpieczeństwa, której koszt nie rośnie wraz z liczbą klientów, dostarczaną przez opiekunów klienta, których już Państwo zatrudniają.",
    },
    cols: [
      { h: "1. Co Państwo sprzedają", li: [
        "Markową usługę oceny: Państwa portal, Państwa faktura, Państwa cena.",
        "Licencje jako przychód powtarzalny, w pakietach lub bez limitu.",
        "Cykliczny przegląd, który utrudnia zmianę umowy na łączność bardziej niż sama cena.",
      ] },
      { h: "2. Jak dociera do bazy", li: [
        "Doklejenie w punkcie sprzedaży, w chwili podpisywania zamówienia na łączność.",
        "Bez nowego procesu sprzedaży: kanałem są obecni opiekunowie klienta.",
        "Sięga długiego ogona małych klientów, których nigdy nie obsłużą Państwo ludźmi.",
      ] },
      { h: "3. Gdzie działa", li: [
        "W Państwa własnym środowisku albo w chmurze krajowej, jeśli wymaga tego regulacja.",
        "W kraju wskazanym przez Państwa regulatora, łącznie z serwerem licencji.",
        "W językach, które Państwa rynek naprawdę czyta.",
      ] },
    ],
    win: { h: "Teza, powiedziana wprost", p:
      "To rzadka oferta bezpieczeństwa, którą baza klientów tej wielkości jest w stanie faktycznie " +
      "skonsumować, bo nic w niej nie wymaga jednego analityka na klienta." },
    steps: [
      { k: "Dowód", v: "Przebieg na próbce własnej bazy." },
      { k: "Marka", v: "Ostylowanie platformy i każdego dokumentu na własną markę." },
      { k: "Doklejenie", v: "Umieszczenie na formularzu zamówienia łączności." },
    ],
    cta: { btn: "Porozmawiajmy", txt: "Warunki White-Label, integracji, licencji i wolumenu na życzenie." },
  },

  // ----------------------------------------------------------------------------------- SME
  {
    id: "sme", group: "buyers", nav: "Małe i średnie firmy",
    eyebrow: "Kupujący", h2: "Dla małych i średnich firm",
    note:
      "Mała lub średnia firma oznacza tutaj przedsiębiorstwo mniej więcej od dziesięciu do dwustu " +
      "pięćdziesięciu pracowników, w którym jedna osoba zajmuje się informatyką obok innych " +
      "obowiązków. Ta strona jest napisana dla takiej właśnie firmy: dla właściciela, dyrektora " +
      "zarządzającego albo dla tej jednej osoby.",
    scr: {
      s: "Słyszą Państwo, że firma musi poważnie potraktować cyberbezpieczeństwo, i zgadzają się z tym.",
      c: "Rada brzmi: kupić test penetracyjny, konsultanta i zestaw polityk. Wszystkie trzy kosztują więcej niż ryzyko, które ktokolwiek Państwu wyliczył, i żadna z nich nie odpowiada na jedyne pytanie, które Państwo naprawdę mają.",
      a: "Dowiedzą się Państwo jeszcze w tym tygodniu, co obcy widzi w Państwa firmie z zewnątrz, bez instalowania czegokolwiek i bez wpuszczania kogokolwiek do sieci.",
    },
    cols: [
      { h: "1. Co Państwo otrzymują", li: [
        "Wszystko, co Państwa i wystawione do internetu, łącznie z rzeczami, o których nikt nie pamiętał.",
        "Ile kosztowałoby Państwa, gdyby coś poszło źle, w pieniądzu, z pokazaną metodą.",
        "Które przepisy Państwa dotyczą i do kiedy, prostym językiem.",
      ] },
      { h: "2. Dlaczego pasuje do firmy tej wielkości", li: [
        "Nic do instalowania. Żadnego oprogramowania, żadnych dostępów, nikogo w Państwa biurze.",
        "Podają Państwo nazwę firmy. To całe wdrożenie.",
        "Powtórka za każdym razem, gdy coś się zmieni, zamiast raz w roku, kiedy Państwa na to stać.",
      ] },
      { h: "3. Co można z tym zrobić", li: [
        "Przesłać w niezmienionej postaci klientowi, który Państwa audytuje.",
        "Dać bankowi lub ubezpieczycielowi bez tłumaczenia.",
        "Wręczyć dostawcy informatyki jako listę prac.",
      ] },
    ],
    channel: {
      b: "Jak to kupić.",
      t: "Przez partnera, nie bezpośrednio od nas. Albo wybierają Państwo jednego z naszych " +
         "certyfikowanych partnerów w swoim regionie, albo przedstawiają nam firmę informatyczną, " +
         "której już Państwo ufają, a my ją wdrożymy. Zachowują Państwo relację, którą mają. Oni " +
         "zyskują kompetencję. Wybór należy do Państwa.",
    },
    win: { h: "Teza, powiedziana wprost", p:
      "Większość firm tej wielkości znajduje co najmniej jedną rzecz, o której nie wiedziała, że " +
      "jest widoczna z internetu. Znalezienie jej kosztuje popołudnie, a nie projekt." },
    steps: [
      { k: "Teraz", v: "Obejrzeć publiczną demonstrację. Prawdziwe dokumenty, wymyślona firma." },
      { k: "Potem", v: "Poprosić nas albo własnego dostawcę o przebieg na własnej nazwie." },
      { k: "Później", v: "Naprawić to, co istotne, i powtórzyć przebieg, by wykazać zamknięcie." },
    ],
    cta: { btn: "Znajdź partnera", txt: "Ceny i warunki pochodzą od Państwa partnera. Prosimy podać region, a przedstawimy partnera, albo przyprowadzić własnego." },
  },

  // ---------------------------------------------------------------------------- ENTERPRISE
  {
    id: "enterprise", group: "buyers", nav: "Duże przedsiębiorstwa",
    eyebrow: "Kupujący", h2: "Dla dużych przedsiębiorstw",
    scr: {
      s: "Mają Państwo zespoły bezpieczeństwa, dojrzałe narzędzia i realny budżet. Każdy z tych zespołów posiada część obrazu.",
      c: "Nikt nie potrafi powiedzieć, jak cała grupa wygląda z zewnątrz, i tego udowodnić. Spółki zależne i przejęcia zostawiają zasoby, do których nikt się nie przyznaje. Ryzyko dostawcy ocenia się formularzem, który dostawca wypełnia sam o sobie.",
      a: "Jedno spojrzenie z zewnątrz na całą grupę, wycenione w pieniądzu, powtarzane w stałym rytmie, z raportem dokładnie o tym, co zmieniło się od poprzedniego przebiegu.",
    },
    cols: [
      { h: "1. Pokrycie, którego nie mają Państwa narzędzia", li: [
        "Cała grupa, łącznie ze spółkami zależnymi i markami, które nie noszą nazwy matki.",
        "Dostawcy oceniani tą samą metodą, bez dostępów i bez ankiet.",
        "Nowo przejęte spółki, zanim ich sieć zostanie połączona z Państwa siecią.",
      ] },
      { h: "2. Wynik w kształcie Państwa organizacji", li: [
        "Ustalenia dla bezpieczeństwa sieci. Ryzyko w pieniądzu dla dyrektora finansowego i komitetu ryzyka.",
        "Sprawcy zagrożeń dla zarządu. Zgodność dla audytu wewnętrznego.",
        "Żaden zespół nie musi niczego uzgadniać z innym zespołem, żeby skorzystać z własnego dokumentu.",
      ] },
      { h: "3. Zbudowane, by wytrzymać kwestionowanie", li: [
        "Każde ustalenie niesie adres, port, dowód i datę.",
        "Zakres jest celowo ostrożny: serwer innej firmy na współdzielonej infrastrukturze nigdy nie jest raportowany jako Państwa.",
        "Tam, gdzie źródło było nieosiągalne, raportuje \"nieznane\", zamiast wnioskować o słabości.",
      ] },
    ],
    change: {
      h: "Raport zmian, czyli ta część, która ma znaczenie",
      lead:
        "Pojedyncza ocena mówi, gdzie Państwo stoją. Nie powie, czy cokolwiek się poprawia. Po " +
        "powtórzeniu platforma porównuje oba przebiegi i raportuje wyłącznie to, co się ruszyło.",
      cells: [
        { k: "new", t: "Nowe", b: "nie istniały poprzednio",
          before: "Ekspozycje, które ", after: ": usługa, którą ktoś opublikował, certyfikat, który wygasł, serwer, który przyszedł wraz z przejęciem." },
        { k: "closed", t: "Zamknięte", b: "zniknęły",
          before: "Ustalenia, które ", after: ". To dowód, że budżet naprawczy dał rezultat, a jest to najtrudniejsza rzecz do wykazania w bezpieczeństwie." },
        { k: "open", t: "Wciąż otwarte", b: "nie drgnęły",
          before: "Ustalenia zgłoszone wcześniej, które ", after: ", wraz z informacją, jak długo pozostają otwarte. To lista eskalacyjna, która pisze się sama." },
      ],
      tailBefore: "Państwa proces zgodności nie chce raportu. Chce datowanej, udowodnionej odpowiedzi na jedno pytanie: ",
      tailBold: "co się zmieniło i czy ktoś naprawił to, co zgłosiliśmy?",
      tailAfter: " To właśnie zamienia projekt w mechanizm kontrolny i dlatego warto uruchamiać ocenę cyklicznie, a nie jednorazowo.",
    },
    channel: {
      b: "Jak to kupić.",
      t: "Przez kanał partnerski. Albo wybierają Państwo jednego z naszych certyfikowanych " +
         "partnerów, albo wskazują integratora systemów, z którym już Państwo pracują, a my go " +
         "wdrożymy. Państwa proces zakupowy, Państwa umowy i istniejące relacje z dostawcami " +
         "pozostają bez zmian.",
    },
    win: { h: "Teza, powiedziana wprost", p:
      "Państwa zespoły zachowują wszystkie posiadane narzędzia. To odpowiada na jedno pytanie, na " +
      "które żadne z nich nie jest wycelowane: co świat zewnętrzny widzi we wszystkim, co Państwo " +
      "posiadają. A potem dowodzi, miesiąc po miesiącu, czy to się kurczy." },
    steps: [
      { k: "Dowód", v: "Jedna jednostka biznesowa. Porównanie z tym, co Państwo sądzili, że mają." },
      { k: "Rozszerzenie", v: "Dodanie spółek zależnych i najbardziej krytycznych dostawców." },
      { k: "Eksploatacja", v: "Stały harmonogram i zarządzanie raportem zmian." },
    ],
    cta: { btn: "Porozmawiajmy", txt: "Umowy korporacyjne, dostęp do interfejsu programistycznego i dokumentacja bezpieczeństwa przychodzą przez Państwa partnera albo naszego." },
  },

  // ----------------------------------------------------------------------------------- LAW
  {
    id: "law", group: "buyers", nav: "Kancelarie prawne",
    eyebrow: "Kupujący", h2: "Dla kancelarii prawnych",
    scr: {
      s: "Doradzają Państwo w zakresie ochrony danych, incydentów cybernetycznych, fuzji i przejęć oraz ekspozycji regulacyjnej.",
      c: "Rutynowo potrzebują Państwo faktów technicznych o firmie, której nie mają Państwo prawa dotknąć. Testowanie cudzych systemów bez upoważnienia tworzy dokładnie tę odpowiedzialność, której zapobieganiu Państwo służą.",
      a: "Dowody techniczne uzyskane bez zrobienia czegokolwiek komukolwiek, co właśnie czyni je użytecznymi w Państwa pracy.",
    },
    cols: [
      { h: "1. Gdzie ma zastosowanie", li: [
        "**Badanie due diligence w transakcji:** rzeczywisty majątek zewnętrzny celu i jego wycenione ryzyko, zanim umowa sprzedaży zostanie podpisana.",
        "**Po incydencie:** niezależny, datowany obraz tego, co było publicznie widoczne.",
        "**Spory:** dowód techniczny, który inny biegły może odtworzyć.",
      ] },
      { h: "2. Dlaczego wolno tego używać", li: [
        "Całkowicie pasywne. Do ocenianej firmy nie dociera ani jeden pakiet.",
        "Nic nie jest wykorzystywane i nigdzie nie następuje logowanie.",
        "Zbudowane wyłącznie ze źródeł, z których każdy badacz może legalnie korzystać, więc nie jest potrzebne niczyje upoważnienie.",
      ] },
      { h: "3. Co można położyć przed klientem", li: [
        "Każde ustalenie z dowodem i datą pozyskania.",
        "Które regulacje mają zastosowanie, z obowiązkami i terminami cytowanymi z tekstów źródłowych.",
        "Ekspozycję przeliczoną na kwotę, którą zarząd Państwa klienta rozumie.",
      ] },
    ],
    win: { h: "Teza, powiedziana wprost", p:
      "Produkuje fakty techniczne o jednej właściwości, której wymaga Państwa praca: zostały " +
      "uzyskane bez zrobienia czegokolwiek komukolwiek. To właśnie czyni je użytecznymi." },
    steps: [
      { k: "Ocena", v: "Przebieg w sprawie, którą już Państwo prowadzą." },
      { k: "Weryfikacja", v: "Sprawdzenie ścieżki dowodowej według własnego standardu." },
      { k: "Wdrożenie", v: "Uczynienie z tego standardowego kroku w due diligence transakcyjnym i w sprawach incydentów." },
    ],
    cta: { btn: "Porozmawiajmy", txt: "Warunki na sprawę albo dla całej kancelarii, przez kanał partnerski. Wynik nie stanowi porady prawnej i nie zastępuje pełnomocnika." },
  },

  // ----------------------------------------------------------------------------- INSURANCE
  {
    id: "insurance", group: "buyers", nav: "Ubezpieczyciele",
    eyebrow: "Kupujący", h2: "Dla ubezpieczycieli, agentów i brokerów",
    scr: {
      s: "Zawierają Państwo ubezpieczenia cybernetyczne i wyceniają je na podstawie tego, co ubiegający się mówi o sobie sam.",
      c: "Wniosek jest wypełniany samodzielnie, optymistycznie i dezaktualizuje się w dniu podpisania. Przy odnowieniu nie sposób stwierdzić, czy cokolwiek, co ubezpieczony obiecał naprawić, zostało naprawione. Po szkodzie nie sposób wykazać, co było widoczne.",
      a: "Ocena tego, co obserwowalne, zamiast tego, co zadeklarowane, na każdym ryzyku, przy koszcie, który nie rośnie wraz z liczbą ryzyk.",
    },
    cols: [
      { h: "1. Jaką składkę powinno nieść to ryzyko?", li: [
        "Strata oczekiwana i najgorszy przypadek w skali roku, wyliczone uznaną metodą Factor Analysis of Information Risk.",
        "Obliczenia są pokazane, więc jest to techniczne wejście do decyzji taryfowej, a nie ocena z czarnej skrzynki.",
        "Dostępne, zanim ubiegający się w ogóle Państwa wybierze, bo nie wymaga żadnej współpracy.",
      ] },
      { h: "2. Co naprawdę jest w ich majątku?", li: [
        "Każda ekspozycja wystawiona do internetu, uszeregowana, z adresem i portem.",
        "Niezależne od wniosku, więc oba można porównać.",
        "Dostarczone w kilka minut, więc mieści się w procesie ofertowania.",
      ] },
      { h: "3. Czy są zgodni z przepisami?", li: [
        "Ich stan wobec przepisów cyberbezpieczeństwa, które ich dotyczą, wraz z terminami.",
        "Brak zgodności jest zarazem czynnikiem szkodowym i kwestią zakresu ochrony.",
        "Reżimy Unii Europejskiej i Kanady działają już dziś.",
      ] },
    ],
    ladder: { h: "Przez cały cykl życia polisy", items: [
      { b: "Przy ofercie.", t: "Kilka minut, bez potrzeby jakiejkolwiek współpracy." },
      { b: "Przy odnowieniu.", t: "Raport zmian pokazuje naprawę albo jej brak. Różnicę można wycenić." },
      { b: "W skali portfela.", t: "Ponowny przebieg całego portfela, gdy pojawia się nowa, szeroko wykorzystywana podatność, i znajomość skumulowanej ekspozycji tego samego dnia." },
      { b: "Przy szkodzie.", t: "Datowany zapis tego, co było widoczne z zewnątrz." },
    ] },
    win: { h: "Teza, powiedziana wprost", p:
      "Przechodzą Państwo od oceny tego, co mówi ubiegający się, do oceny tego, co da się " +
      "zaobserwować, spójnie, na każdym ryzyku. To argument o wskaźniku szkodowości, a nie o technologii." },
    steps: [
      { k: "Kalibracja", v: "Przebieg na ryzykach już zawartych, w tym takich, które dały szkody." },
      { k: "Porównanie", v: "Zestawienie wyników z wnioskami i przyjrzenie się różnicom." },
      { k: "Integracja", v: "W procesie ofertowania albo w portalu brokerskim." },
    ],
    cta: { btn: "Porozmawiajmy", txt: "Warunki portfelowe, interfejsu programistycznego i integracji na życzenie." },
  },

  // ----------------------------------------------------------------------------- REGULATOR
  {
    id: "regulator", group: "buyers", nav: "Regulatorzy",
    eyebrow: "Kupujący", h2: "Dla regulatorów i organów nadzoru",
    scr: {
      s: "Nadzorują Państwo populację podmiotów w ramach mandatu dotyczącego cyberbezpieczeństwa lub odporności operacyjnej.",
      c: "Prawo jest napisane, a terminy są realne. Państwa zdolność techniczna nie jest. W praktyce kontrolują Państwo kilka podmiotów rocznie, wybranych bez podstawy technicznej. Nie sposób wiedzieć, czy te niekontrolowane nie są właśnie tymi istotnymi.",
      a: "Nadzór nad całą populacją na podstawie publicznych dowodów, bez odwiedzania kogokolwiek, z zamianą każdego naruszenia w przygotowaną teczkę sprawy, którą Państwa urzędnik przegląda i podpisuje.",
    },
    cols: [
      { h: "1. Pokrycie zamiast próbkowania", li: [
        "Każdy nadzorowany podmiot, oceniony tą samą metodą tego samego dnia.",
        "Wyniki są porównywalne w całym sektorze, bo nic nie jest mierzone inaczej.",
        "Powtarzalne cyklicznie, więc można mierzyć kierunek, w którym zmierza sektor.",
      ] },
      { h: "2. Dowody, które wytrzymują kwestionowanie", li: [
        "Na każdy podmiot: adres, port, dowód i data obserwacji.",
        "Odwzorowane na konkretny przepis, którego dotyczą.",
        "Tam, gdzie źródło jest nieosiągalne, raportuje \"nieznane\" i nie twierdzi, że doszło do naruszenia.",
      ] },
      { h: "3. Zgodne z prawem z założenia", li: [
        "Całkowicie pasywne. Żaden podmiot nie jest dotykany, więc nie powstaje obowiązek zawiadomienia ani upoważnienia.",
        "Odtwarzalne, więc wytrzymuje przegląd przez własnych ekspertów podmiotu.",
        "Możliwe do wdrożenia w Państwa własnym lub w krajowym środowisku, jeśli wymaga tego mandat.",
      ] },
    ],
    ladder: { h: "Ścieżka egzekwowania, prowadzona na całej populacji", items: [
      { b: "Wykrycie.", t: "Stan niezgodności u nadzorowanego podmiotu, z adresem, portem i datą obserwacji." },
      { b: "Przypisanie.", t: "Konkretny przepis, którego dotyczy, w prawie europejskim albo w Państwa własnym instrumencie krajowym." },
      { b: "Potwierdzenie.", t: "Cztery niezależne modele sztucznej inteligencji, od czterech różnych dostawców, przeglądają sprawę. Dwa ją budują, dwa próbują ją obalić. Decyzję podejmują sztywne reguły w kodzie, a nie modele, a sprawa, której żaden z nich nie potwierdzi, nigdy nie opuszcza kolejki." },
      { b: "Przygotowanie.", t: "Udokumentowana teczka sprawy i zawiadomienie o wszczęciu postępowania powstają automatycznie." },
      { b: "Rozstrzygnięcie.", t: "Państwa urzędnik przegląda i podpisuje. Maszyna buduje sprawę, a organ ją wydaje, co utrzymuje każde rozstrzygnięcie w zakresie kontroli i zaskarżenia." },
    ] },
    win: { h: "Teza, powiedziana wprost", p:
      "Przestają Państwo wybierać podmioty do kontroli po reputacji. Zaczynają Państwo nadzorować " +
      "cały sektor na podstawie dowodów, bez wysyłania inspektora do jednego budynku i bez jednego " +
      "pakietu docierającego do nadzorowanego podmiotu." },
    steps: [
      { k: "Pilot", v: "Jeden sektor, jedna grupa podmiotów. Uszeregowanie ich." },
      { k: "Porównanie", v: "Zestawienie rankingu z własną wiedzą nadzorczą." },
      { k: "Skala", v: "Pełna populacja, cyklicznie, z kolejką egzekwowania." },
    ],
    cta: { btn: "Porozmawiajmy", txt: "Zamówienia publiczne, lokalizacja hostingu i warunki na życzenie." },
  },

  // --------------------------------------------------------------------------- WHITE-LABEL
  {
    id: "whitelabel", group: "engage", nav: "White-Label", accent: "purple",
    eyebrow: "Forma współpracy, model 1 z 2", h2: "White-Label",
    scr: {
      s: "Chcą Państwo mieć usługę bezpieczeństwa do sprzedaży pod własną nazwą.",
      c: "Zbudowanie silnika zajmuje lata. Odsprzedaż cudzej marki oznacza, że relacja klienta jest z nimi, a nie z Państwem.",
      a: "Państwa marka na wierzchu, nasz silnik pod spodem. Państwa klient, Państwa umowa, Państwa cena, a nas klient nigdy nie widzi.",
    },
    cols: [
      { h: "Co staje się Państwa", li: [
        "Marka na każdym ekranie i na wszystkich czterech dokumentach.",
        "Relacja z klientem, umowa i faktura.",
        "Własny cennik, ustalany przez Państwa, dla Państwa rynku.",
        "Miejsce działania: Państwa chmura, Państwa region albo środowisko krajowe. Serwer licencji może stać w dowolnym kraju lub regionie, jakiego Państwo wymagają.",
      ] },
      { h: "Co Państwa nie staje się", li: [
        "Kod źródłowy i własność platformy. Otrzymują Państwo licencję na używanie i prezentowanie, a nie na posiadanie.",
        "Prawo do dalszego licencjonowania samego oprogramowania osobom trzecim.",
        "Rozwój silnika i gwarancje jego poprawności. Te pozostają u nas i to właśnie na nich Państwo polegają.",
      ] },
    ],
    win: { h: "Proszę wybrać ten model, jeśli", p:
      "Chcą Państwo mieć produkt do sprzedaży: coś, do czego klient loguje się z Państwa nazwą na " +
      "ekranie. To właściwy model dla dostawców usług zarządzanych, operatorów " +
      "telekomunikacyjnych, firm doradczych i resellerów budujących praktykę bezpieczeństwa." },
    steps: [
      { k: "Zakres", v: "Marka, region hostingu, języki, wybrane moduły." },
      { k: "Budowa", v: "Stylujemy i wdrażamy. Państwo odbierają wedle uzgodnionych kryteriów." },
      { k: "Sprzedaż", v: "Pod Państwa nazwą, w Państwa cenie." },
    ],
    cta: { btn: "Porozmawiajmy", txt: "Zobowiązania, zakres wdrożenia i cennik są kwestią handlową i poufną. Prosimy pytać." },
  },

  // ----------------------------------------------------------------------------------- OEM
  {
    id: "oem", group: "engage", nav: "Zintegrowany (OEM)", accent: "purple",
    eyebrow: "Forma współpracy, model 2 z 2", h2: "Zintegrowany, zwany także OEM",
    scr: {
      s: "Mają już Państwo produkt, do którego klienci logują się codziennie.",
      c: "Sprzedaż osobnego produktu obok tworzy tarcie: kolejne logowanie, kolejna umowa, kolejna rzecz do wyjaśnienia. Rozmywa też produkt, który budowali Państwo latami.",
      a: "Nasz silnik wewnątrz Państwa produktu, więc klient widzi nową funkcję, a nie nowy produkt do oceny.",
    },
    cols: [
      { h: "Jak to działa", li: [
        "Wywołują Państwo nasz interfejs programistyczny. Ustalenia, wycenione ryzyko, kontekst sprawców zagrożeń, oceny zgodności i gotowe dokumenty wracają jako dane.",
        "Wyświetlają je Państwo we własnym interfejsie, we własnej strukturze.",
        "Ustalenia krytyczne są wypychane do Państwa platformy lub systemu monitorowania bezpieczeństwa w chwili wystąpienia, więc nie ma czego odpytywać.",
        "Możliwe do wdrożenia w Państwa środowisku, w regionie, którego wymaga Państwa architektura lub regulator.",
      ] },
      { h: "Co to Państwu daje", li: [
        "Nową zdolność w istniejącym produkcie, bez nowej pozycji do zatwierdzenia przez klienta.",
        "Bez drugiego logowania, bez drugiej umowy, bez drugiej ścieżki wsparcia.",
        "Pełną kontrolę nad doświadczeniem, jego miejscem w mapie drogowej i sposobem wyceny.",
        "Nadal mogą Państwo odsprzedawać licencje jako osobną linię tam, gdzie klient tego oczekuje.",
      ] },
    ],
    vs: {
      a: { h: "White-Label to", bold: "produkt", before: "gotowy ", after: ", który wygląda jak Państwa własny. Klient loguje się do czegoś z Państwa marką. Najlepszy, gdy budują Państwo praktykę usługową i potrzebują czegoś do sprzedaży." },
      b: { h: "Zintegrowany to", bold: "zdolność", before: "nowa ", after: " wewnątrz Państwa produktu. Klient widzi nową funkcję, a nie nowy produkt. Najlepszy, gdy już posiadają Państwo ekran, na który klient patrzy, i nie chcą dokładać drugiego." },
    },
    win: { h: "Proszę wybrać ten model, jeśli", p:
      "Są Państwo producentem oprogramowania lub bezpieczeństwa, ubezpieczycielem z portalem albo " +
      "firmą platformową. Test jest prosty. Jeśli klient już loguje się do czegoś Państwa, proszę " +
      "wybrać model zintegrowany. Jeśli nie, proszę wybrać White-Label." },
    steps: [
      { k: "Projekt", v: "Które wywołania, które dane, w którym miejscu się pojawiają." },
      { k: "Integracja", v: "Klucze o ograniczonym zakresie, podpisane wywołania zwrotne, wersjonowana specyfikacja." },
      { k: "Wydanie", v: "Staje się funkcją Państwa platformy." },
    ],
    cta: { btn: "Porozmawiajmy", txt: "Głębokość integracji, wolumen i warunki są kwestią handlową. Prosimy pytać." },
  },

  // ------------------------------------------------------------------------------- CONTACT
  {
    id: "contact", group: "engage", nav: "Porozmawiajmy",
    eyebrow: "Następny krok", h2: "Porozmawiajmy",
    note:
      "Ceny, poziomy, modele licencyjne, zobowiązania i warunki umowne są kwestią handlową i " +
      "uzgadniamy je bezpośrednio. Celowo nie są tutaj publikowane.",
    cols: [
      { h: "Co możemy zrobić w tym tygodniu", li: [
        "Przebieg na żywo na nazwie firmy wybranej przez Państwa, żeby oceniali Państwo wynik, a nie prezentację.",
        "Rozmowę referencyjną z partnerem, który już to sprzedaje na rynku niemieckojęzycznym.",
        "Pakiet prawny: umowa partnerska, załącznik White-Label i integracyjny, umowa o zachowaniu poufności, umowa o poziomie usług, regulamin, umowa powierzenia przetwarzania danych oraz karta informacyjna hostingu.",
        "Dokumentację architektury bezpieczeństwa, o którą poprosi Państwa oficer bezpieczeństwa lub dział zakupów.",
      ] },
      { h: "O co zapytamy Państwa", li: [
        "Do której z powyższych grup Państwo należą. To istotnie zmienia odpowiedź.",
        "Czy chcą to Państwo odsprzedawać, opatrzyć własną marką, czy zintegrować z własnym produktem.",
        "Czy sprzedają Państwo licencje, usługi, czy jedno i drugie.",
        "Gdzie muszą znajdować się dane oraz serwer licencji.",
      ] },
    ],
    cta: { btn: "Napisz do nas", ghost2: "Najpierw obejrzyj publiczną demonstrację", txt: "Cybergod LLC, część S4Biz Group" },
  },
];
