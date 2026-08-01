// legal-locales/pl.jsx — see ./index.js. Missing exports fall back to English, then German.
// German is the NORMATIVE text; this is a reading translation.
//
// SCOPE OF THIS FILE: a reading translation for Polish. It does not create, soften or strengthen a
// single obligation. Every retention period (30 days / 90 days), every legal basis, the single
// non-EU recipient (Google / Gmail API under the EU-US Data Privacy Framework), the FRA1 Frankfurt
// hosting claim and the DB-IP credit are carried across verbatim. DSGVO article numbers become RODO
// article numbers; § 5 DDG, § 7(1) DDG, § 18(2) MStV and § 25(2)(2) TDDDG are GERMAN statutes and
// keep their German citation — there is no Polish equivalent that applies here. The competent
// supervisory authority stays the Hessian one named in OPERATOR; it is NOT replaced by the UODO.
//
// REGISTER: formal and impersonal. Polish past-tense verbs are GENDERED and the page cannot know the
// reader's gender, so the reader is addressed with the gender-neutral formal `Państwa` (possessive)
// and with impersonal constructions (`-no/-to`, infinitives, `przysługuje …`). No past-tense verb
// anywhere agrees with the reader.
//
// The PRIVACY lead opens by saying the German version is authoritative — that sentence is what makes
// shipping a translated legal page safe.
import { OPERATOR } from "../legal.jsx";

// WHY A COMPONENT AND NOT A PLAIN FRAGMENT: legal.jsx imports ./legal-locales/index.js, which
// imports this file — a module cycle. Reading OPERATOR at MODULE-EVALUATION time (inside a bare
// `(<>...{OPERATOR.name}...</>)`) would hit the temporal dead zone, because this module's body runs
// before legal.jsx's does. Wrapping it in a component defers the read to RENDER time, by which
// point legal.jsx is fully initialised. The rendered output is identical to the `en` variant.
function Controller() {
  return (<>Administratorem danych w rozumieniu RODO jest <strong>{OPERATOR.name}</strong>,{" "}
          {OPERATOR.street}, {OPERATOR.zipCity}, {OPERATOR.country} —{" "}
          <a href={"mailto:" + OPERATOR.email}>{OPERATOR.email}</a>. Pełne dane w{" "}
          <a href="/impressum">nocie prawnej</a>. Wykorzystanie wewnętrzne na potrzeby
          przedsprzedaży; wygenerowane dokumenty stanowią wewnętrzny materiał sprzedażowy.
          Przysługuje Państwu prawo wniesienia skargi do organu nadzorczego ds. ochrony danych
          (art. 77 RODO); organem właściwym jest <strong>{OPERATOR.authority}</strong>.</>);
}

// ---------------------------------------------------------------- the Art.13 notice (Assess screen)
export const NOTICE = {
  title: "🇪🇺 Przetwarzanie danych",
  p1: (<>Kliknięcie przycisku <strong>Assess</strong> uruchamia analizę na serwerze w centrum danych
       we <strong>Frankfurcie nad Menem (DE)</strong>. Przetwarzamy Państwa adres e-mail, adres IP,
       znaczniki czasu oraz nazwę wskazanej firmy — w celu świadczenia usługi oraz wykrywania ataków
       (art. 6(1)(b) i 6(1)(f) RODO). Dzienniki bezpieczeństwa są automatycznie usuwane po{" "}
       <strong>30 dniach</strong>.</>),
  p2: (<><strong>Państwa dane pozostają w UE.</strong> Jedyny wyjątek: Państwa adres e-mail jest
       przekazywany do interfejsu API Gmail, aby możliwe było przesłanie jednorazowego kodu (Google,
       EU-US Data Privacy Framework). Sama analiza korzysta wyłącznie ze źródeł publicznych i nie
       otrzymuje <strong>żadnych</strong> danych użytkownika — jedynie nazwę ocenianej firmy.</>),
  link: "Informacja o ochronie danych", ok: "Rozumiem — nie pokazuj ponownie",
  mini: (<>🇪🇺 Państwa dane pozostają w UE (Frankfurt/FRA1) · adres e-mail, adres IP, znaczniki czasu
         i nazwa firmy są przetwarzane w celu świadczenia usługi i wykrywania ataków
         (art. 6(1)(b)/(f) RODO), dzienniki przechowywane 30 dni. </>),
};

// ---------------------------------------------------------------- the /impressum page
export const IMPRESSUM = {
  h1: "Nota prawna (Impressum)", sub: "Informacje zgodnie z § 5 DDG (niemiecka ustawa o usługach cyfrowych)",
  s1: "Usługodawca",
  s2: "Kontakt",
  s3: "Odpowiedzialny za treść zgodnie z § 18(2) MStV",
  s4: "Numer identyfikacyjny VAT",
  s5: "Rozstrzyganie sporów",
  s5p: (<>Komisja Europejska udostępnia platformę internetowego rozstrzygania sporów (ODR):{" "}
        <a href="https://ec.europa.eu/consumers/odr/" target="_blank" rel="noreferrer">ec.europa.eu/consumers/odr</a>.
        Nie jesteśmy gotowi ani zobowiązani do udziału w postępowaniach w sprawie rozstrzygania
        sporów przed konsumenckim organem arbitrażowym.</>),
  s6: "Odpowiedzialność za treści i odsyłacze",
  s6p: (<>Jako usługodawca odpowiadamy za treści własne na tych stronach na zasadach ogólnych
        (§ 7(1) DDG). Za treść zewnętrznych stron, do których prowadzą odsyłacze, odpowiada zawsze
        ich dostawca; w chwili umieszczenia odsyłacza nie stwierdzono naruszeń prawa. Po powzięciu
        wiadomości o naruszeniu niezwłocznie usuwamy takie odsyłacze.</>),
  s7: "Prawo autorskie",
  s7p: (<>Treści i utwory stworzone przez operatora na tych stronach podlegają niemieckiemu prawu
        autorskiemu. Dokumenty analityczne generowane przez cybergod.ai stanowią wewnętrzny materiał
        sprzedażowy i nie są przeznaczone do publicznego rozpowszechniania.</>),
  note: "Uwaga: cybergod.ai jest wewnętrznym narzędziem o ograniczonym dostępie, służącym do analiz cyberbezpieczeństwa na etapie przedsprzedaży; nie jest udostępniane ogółowi odbiorców.",
  todo: "⚠ Niniejsza nota prawna jest niekompletna. Przed publikacją należy uzupełnić imię i nazwisko, adres pocztowy oraz numer telefonu w OPERATOR (src/legal.jsx) — w Niemczech niekompletny Impressum może być podstawą wezwań do zaniechania naruszeń.",
};

// ---------------------------------------------------------------- the /contact page
export const CONTACT = {
  h1: "Kontakt", sub: "Bezpośrednia linia — bez formularzy, bez kolejek",
  lead: "Pytania o dostęp, o analizę, o ochronę danych lub o współpracę partnerską? Zapraszamy do bezpośredniego kontaktu.",
  email: "E-mail", emailD: "W sprawach dostępu, wniosków dotyczących ochrony danych i wszelkich kwestii biznesowych. Odpowiedź zwykle tego samego dnia roboczego.",
  li: "LinkedIn", liD: "Najszybsza droga do kontaktu zawodowego.",
  wa: "WhatsApp", waD: "Najszybsza droga. Bezpośrednio na telefon, odpowiedź zwykle w ciągu kilku minut.",
  tg: "Telegram", tgD: "Wiadomość bezpośrednia — ta sama platforma, na której działają boty analityczne.",
  gh: "GitHub", ghD: "Zaplecze techniczne i projekty.",
  access: "Wniosek o dostęp",
  accessD: "cybergod.ai ma ograniczony dostęp: wymagany jest zatwierdzony partnerski adres e-mail. Prosimy podać w wiadomości nazwę firmy oraz adres, który ma zostać aktywowany.",
  legal: "Informacje prawne: ", soon: "kanał wkrótce",
};

// ---------------------------------------------------------------- the /privacy page
export const PRIVACY = {
  h1: "Ochrona danych i ich przetwarzanie", sub: "Datenschutz & Datenverarbeitung — cybergod.ai",
  lead: "Wersja niemiecka niniejszego tekstu jest wersją autentyczną i rozstrzygającą; niniejsze tłumaczenie udostępniono wyłącznie dla ułatwienia lektury. cybergod.ai jest wewnętrznym narzędziem do analiz cyberbezpieczeństwa na etapie przedsprzedaży. Na tej stronie wyjaśniono, jakie dane przetwarzamy, na jakiej podstawie prawnej, gdzie są przechowywane i jak długo je zachowujemy — zgodnie z art. 13/14 RODO.",
  s1: "1. Gdzie przechowywane są Państwa dane",
  s1p: (<><strong>Państwa dane osobowe pozostają w UE.</strong> Aplikacja, baza danych, sesje,
       wygenerowane dokumenty oraz dzienniki bezpieczeństwa działają na jednym serwerze w{" "}
       <strong>centrum danych we Frankfurcie nad Menem w Niemczech (DigitalOcean, region
       FRA1)</strong>. Nie ma replikacji ani kopii zapasowych poza UE.</>),
  s1sub: "Podmioty przetwarzające (art. 28 RODO):",
  s1list: [
    (<><strong>DigitalOcean</strong> — hosting serwera, region Frankfurt (FRA1), UE.</>),
    (<><strong>Google (API Gmail)</strong> — dostarcza jednorazowy kod (OTP) na Państwa adres e-mail
       oraz przekazuje operatorowi powiadomienia eksploatacyjne i dotyczące bezpieczeństwa.
       Powiadomienia te mogą zawierać <strong>techniczne metadane wizyty (adres IP, kraj,
       przeglądarka/urządzenie, żądana strona)</strong>, aby operator mógł weryfikować dostępy i
       zdarzenia bezpieczeństwa (art. 6(1)(f) RODO). Google posiada certyfikat w ramach EU-US Data
       Privacy Framework (art. 45 RODO). Treść analiz nie jest przekazywana.</>),
    (<><strong>Telegram</strong> — wyłącznie w przypadku korzystania z opcjonalnego dostępu przez
       Telegram; wówczas zastosowanie ma Państwa identyfikator użytkownika Telegrama.</>),
  ],
  s1note: (<>Sama analiza ocenia wyłącznie <strong>publicznie widoczne dane o infrastrukturze
           ocenianej firmy</strong> (Shodan, RIPE, CAIDA, PeeringDB, crt.sh) i tworzy treść raportu
           za pośrednictwem usługi (endpointu) AI. Usługi te otrzymują <strong>wyłącznie nazwę firmy albo
           domenę/ASN celu analizy</strong> lub ustalenie techniczne — <strong>żadnego
           identyfikatora użytkownika, żadnego adresu e-mail, żadnego adresu IP
           użytkownika</strong>. Nie są zatem odbiorcami Państwa danych osobowych.</>),
  s2: "2. Jakie dane przetwarzamy",
  th: ["Dane", "Cel", "Podstawa prawna", "Okres przechowywania"],
  rows: [
    ["Adres e-mail (logowanie, OTP)", "Kontrola dostępu, uwierzytelnianie dwuskładnikowe",
     "Art. 6(1)(b) — umowa/korzystanie; art. 6(1)(f) — bezpieczeństwo", "Przez czas trwania dostępu"],
    ["Adres IP, znacznik czasu, user-agent, urządzenie/przeglądarka, kraj",
     "Wykrywanie ataków (DDoS, brute force, skanery), przeciwdziałanie nadużyciom, eksploatacja usługi",
     "Art. 6(1)(f) — prawnie uzasadniony interes w zakresie bezpieczeństwa IT (motyw 49)",
     "30 dni (przechowywanie dzienników), następnie automatyczne usunięcie"],
    ["Wskazane firmy, język, czas, wygenerowane dokumenty",
     "Realizacja analizy, przypisanie kosztów, możliwość prześledzenia",
     "Art. 6(1)(b), art. 6(1)(f)", "90 dni lub do usunięcia przez użytkownika"],
    ["Alerty bezpieczeństwa (reguła, temat, dane forensyczne)", "Reagowanie na incydenty", "Art. 6(1)(f)", "30 dni"],
  ],
  s2note: (<><strong>Brak</strong> reklamowych plików cookie, <strong>brak</strong> śledzenia między
           witrynami, <strong>brak</strong> profilowania, <strong>brak</strong> zautomatyzowanego
           podejmowania decyzji wywołującego skutki prawne (art. 22). Jedynym stosowanym plikiem
           cookie jest ściśle niezbędny plik cookie sesji (§ 25(2)(2) TDDDG — nie wymaga
           zgody).</>),
  s3: "3. Minimalizacja danych (art. 5(1)(c))",
  s3list: [
    (<>Geolokalizacja <strong>wyłącznie na poziomie kraju</strong> — bez miasta, bez współrzędnych.
       Lokalna baza danych offline, bez zapytań do podmiotów trzecich.</>),
    (<>Pliki statyczne (CSS/obrazy) nie są rejestrowane.</>),
    (<>Adresy IP mogą być przechowywane przez operatora w postaci <strong>skrótu (hash)</strong>{" "}
       (<code>TELEMETRY_HASH_IPS=1</code>): korelacja zostaje zachowana, identyfikator — nie.</>),
    (<>Przedmiotem analizy są <strong>firmy</strong>, a nie osoby fizyczne. Oceniane są wyłącznie
       publicznie widoczne dane o infrastrukturze — <strong>nie jest prowadzone aktywne
       skanowanie</strong>.</>),
  ],
  s4: "4. Państwa prawa (art. 15–21 RODO)",
  s4p: (<>Dostęp do danych, sprostowanie, usunięcie, ograniczenie przetwarzania, przenoszenie danych
        oraz <strong>prawo sprzeciwu wobec przetwarzania opartego na prawnie uzasadnionych
        interesach</strong>. Wnioski prosimy kierować na adres{" "}
        <a href="mailto:feranicus@s4biz.io">feranicus@s4biz.io</a> — odpowiedź w terminie jednego
        miesiąca (art. 12(3)). Przysługuje również prawo wniesienia skargi do organu nadzorczego
        (art. 77).</>),
  s5: "5. Bezpieczeństwo (art. 32 RODO)",
  s5list: [
    "Szyfrowanie TLS całej transmisji; automatyczne odnawianie certyfikatów.",
    "Dostęp w modelu zero trust: tożsamość z listy dozwolonych + wspólne hasło + jednorazowy kod przesyłany e-mailem.",
    "Dokumenty są przypisane do właściciela — może je odczytać wyłącznie użytkownik, który je wygenerował.",
    "Ciągłe wykrywanie ataków wraz z alertowaniem (brute force, DDoS, skanery, eksfiltracja danych).",
    "Regularne, zautomatyzowane aktualizacje bezpieczeństwa serwera.",
  ],
  s6: "6. Administrator danych",
  s6p: (<Controller />),
  credit: "Przypisanie adresu IP do kraju: ", disclaimerT: "Uwaga: ",
  disclaimer: "Niniejszy tekst opisuje faktyczne przetwarzanie techniczne. Nie stanowi porady prawnej i przed publikacją zewnętrzną powinien zostać zweryfikowany przez inspektora ochrony danych.",
};
