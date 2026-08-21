# -*- coding: utf-8 -*-
"""07 - End-User Terms. The Vendor's terms, flowed down to the final customer.

WHO THIS IS FOR: the organisation at the bottom of the chain, which may be a twenty-person firm or
a global carrier. Its procurement team will not accept "our reseller's supplier has terms" as an
answer, and it will not accept a minimum-terms schedule inside somebody else's contract either. It
wants a document with the software owner's name on it that says what it may do, what the product
is, and what the product is not.

THREE THINGS THIS DOCUMENT EXISTS TO SAY PLAINLY, and each of them has been the subject of a real
argument in this product's history:

  * WHAT IT IS NOT. It is not a penetration test, not a certification, not an audit opinion and not
    legal advice. A deliverable that states a finding is stating what a public source showed at a
    point in time.
  * WHOSE INFRASTRUCTURE MAY BE ASSESSED. Only the Customer's own, or one it is authorised to
    assess. This is the clause that keeps everyone out of Section 202a StGB.
  * NO PACKET IS SENT. The platform reads public sources. That is a product promise, and it is what
    makes an assessment possible without the target's authorisation in the first place.

THE CUSTOMER CONTRACTS WITH THE RESELLER FOR COMMERCIALS. These terms govern the right of use and
nothing else: no price, no term, no service level. Those live in the Reseller's own contract, and
saying so here stops the two documents contradicting each other.
"""
from common import DATE_DE, DATE_EN, FORUM, LAW_DE, LAW_EN, NOTE_DE, NOTE_EN, PLATFORM, VENDOR, \
    VERSION

EN = [
    ("h1", "END-USER TERMS"),
    ("meta", "%s  ·  %s  ·  Version %s  ·  %s  ·  German law, %s"
     % (VENDOR["name"], PLATFORM, VERSION, DATE_EN, FORUM)),

    ("p", "These End-User Terms govern the right of the organisation named in the ordering "
          "document (the \"Customer\") to use the %s platform (the \"Platform\"), which is owned "
          "and operated by %s, %s (the \"Vendor\")."
     % (PLATFORM, VENDOR["name"], VENDOR["addr"])),
    ("p", "The Customer buys from an authorised reseller (the \"Reseller\"). Price, term, invoicing "
          "and service levels are agreed between the Customer and the Reseller. These terms govern "
          "the right of use and are incorporated into that contract."),
    ("note", NOTE_EN),

    ("h2", "1. What the Platform is"),
    ("num", "1.1", "The Platform assesses an organisation's exposure using PUBLIC SOURCES ONLY. It "
                   "reads internet scan data, certificate transparency logs, routing registries "
                   "and public DNS."),
    ("num", "1.2", "IT SENDS NO PACKET TO THE ORGANISATION BEING ASSESSED. It performs no port "
                   "scanning, no vulnerability probing and no authentication attempt against that "
                   "organisation."),
    ("num", "1.3", "It produces presentation decks, an animated report and a run log describing "
                   "what was done."),
    ("num", "1.4", "A deliverable is an assessment of what public information showed at a point in "
                   "time. IT IS NOT a penetration test, a security guarantee, a certification, an "
                   "audit opinion, an insurance assessment or legal advice, and the Customer will "
                   "not present it as any of those."),
    ("num", "1.5", "The Vendor does not warrant that an assessment identifies every exposure, that "
                   "a public source is complete or accurate, or that a deliverable is free of a "
                   "finding that later proves not to apply. The Vendor warrants that the Platform "
                   "performs materially in accordance with its documentation."),

    ("h2", "2. Right of use"),
    ("num", "2.1", "The Vendor grants the Customer a non-exclusive, non-transferable right, for "
                   "the term agreed with the Reseller, to access and use the Platform for the "
                   "Customer's own internal business purposes."),
    ("num", "2.2", "The right is granted by the Vendor DIRECTLY. It does not depend on a "
                   "sub-licence from the Reseller and it survives a change of Reseller."),
    ("num", "2.3", "Where the Customer is a service provider assessing its own clients, it may use "
                   "the Platform to do so provided clause 3 is satisfied for each client and the "
                   "Customer's contract with that client includes terms to the effect of clauses "
                   "1.4, 3 and 4."),
    ("num", "2.4", "Access is by named individual user. A named user is one natural person and "
                   "credentials may not be shared. A named user may be replaced when a person "
                   "leaves a role."),
    ("num", "2.5", "The Customer's group companies may use the Platform under the Customer's "
                   "entitlement, provided the Customer remains responsible for their compliance."),

    ("h2", "3. Whose infrastructure may be assessed"),
    ("p", "This is the clause that keeps everybody lawful. It is short on purpose."),
    ("num", "3.1", "The Customer may submit an organisation for assessment only where the Customer "
                   "owns or controls that organisation's infrastructure, or has that "
                   "organisation's authorisation, or is otherwise lawfully entitled to assess it."),
    ("num", "3.2", "The Customer confirms that entitlement on each submission. The Vendor does not "
                   "verify it and is not able to."),
    ("num", "3.3", "The Customer will not use the Platform as a pretext for competitive "
                   "intelligence, and will not publish an assessment of a third party without that "
                   "party's consent."),
    ("num", "3.4", "The Customer will not use the Platform in a manner or in a territory where "
                   "doing so would be unlawful, including under export control or sanctions law."),

    ("h2", "4. Restrictions"),
    ("num", "4.1", "The Customer will not decompile or disassemble the Platform or attempt to "
                   "derive its source code, except to the extent Section 69e of the German "
                   "Copyright Act permits and cannot be excluded."),
    ("num", "4.2", "The Customer will not benchmark the Platform against a competing product for "
                   "publication, and will not use it to build or train a competing service."),
    ("num", "4.3", "The Customer will not resell, sublicense or make the Platform available to a "
                   "third party, save as clause 2.3 permits."),
    ("num", "4.4", "The Customer will not circumvent a technical limit, a rate limit or an "
                   "entitlement check."),
    ("num", "4.5", "The Vendor may enforce this clause 4 and clause 3 against the Customer "
                   "directly, without joining the Reseller."),

    ("h2", "5. The deliverables"),
    ("num", "5.1", "The Customer may use the deliverables generated for it WITHOUT RESTRICTION for "
                   "its own purposes, including in its dealings with its auditors, its insurers, "
                   "its regulators and its own customers."),
    ("num", "5.2", "The Vendor claims no ownership of the Customer's own data or of the conclusions "
                   "the Customer draws."),
    ("num", "5.3", "Intellectual property in the Platform, its software, its templates and its "
                   "methodology remains with the Vendor. The Customer receives a right of use and "
                   "nothing more."),
    ("num", "5.4", "Where the Reseller supplies the Platform under its own brand, the deliverables "
                   "carry that brand. This does not change who owns the Platform or who these "
                   "terms bind."),

    ("h2", "6. Data protection"),
    ("num", "6.1", "The personal data the Platform processes is the Customer's own users' account "
                   "data: name, business e-mail address, the identity of the user who ordered an "
                   "assessment, request telemetry and support correspondence."),
    ("num", "6.2", "THE ANALYSIS PIPELINE RECEIVES NO USER IDENTITY. The public data sources "
                   "receive the name or domain of the organisation being assessed. The inference "
                   "endpoint that writes the narrative sections receives the technical findings. "
                   "Neither receives the identity of a person."),
    ("num", "6.3", "The Platform is hosted in Frankfurt am Main, Germany."),
    ("num", "6.4", "Where the Customer is a controller and the Reseller a processor, or the "
                   "reverse, the agreement between them governs. The Vendor makes its own "
                   "Article 28 terms available to the Customer on request."),
    ("num", "6.5", "The Customer will not submit special categories of personal data. The Platform "
                   "is not designed for them."),

    ("h2", "7. Security and suspension"),
    ("num", "7.1", "The Customer will keep credentials confidential and will notify the Reseller "
                   "without undue delay of a suspected compromise."),
    ("num", "7.2", "The Vendor may suspend access where it reasonably believes credentials have "
                   "been compromised, where use materially threatens the security or integrity of "
                   "the Platform, or where suspension is required by law or by sanctions."),
    ("num", "7.3", "The Vendor will give the reason without undue delay, will limit the suspension "
                   "to what the risk requires and will restore access as soon as the cause is "
                   "removed."),
    ("num", "7.4", "The Customer is not suspended for a non-payment upstream of the Reseller for "
                   "as long as the Customer is paying the Reseller."),

    ("h2", "8. Liability"),
    ("num", "8.1", "The Vendor is liable without limitation for intent and gross negligence, for "
                   "injury to life, body or health, under the German Product Liability Act, and "
                   "where it has given a guarantee or fraudulently concealed a defect."),
    ("num", "8.2", "For simple negligence the Vendor is liable only where it breaches a material "
                   "contractual obligation, meaning an obligation whose performance makes proper "
                   "performance possible in the first place and on whose observance the Customer "
                   "regularly relies, and then only for the foreseeable damage typical for this "
                   "type of contract."),
    ("num", "8.3", "Subject to clauses 8.1 and 8.2, the Vendor's aggregate liability to the "
                   "Customer is limited to the fees the Customer paid the Reseller for the "
                   "Platform in the twelve months preceding the event."),
    ("num", "8.4", "THE CUSTOMER'S COMMERCIAL REMEDIES ARE AGAINST THE RESELLER. Service levels, "
                   "credits, refunds and delivery obligations are agreed with the Reseller and are "
                   "claimed from the Reseller."),
    ("num", "8.5", "The Vendor is not liable for a security incident at an organisation that has "
                   "been assessed, whether or not the assessment identified the vector. The "
                   "Customer is responsible for the decisions it takes on the basis of a "
                   "deliverable."),

    ("h2", "9. Term and changes"),
    ("num", "9.1", "These terms apply for as long as the Customer has a right of use under its "
                   "contract with the Reseller."),
    ("num", "9.2", "The Vendor may change these terms. A change is notified through the Reseller "
                   "at least 30 days in advance and applies to the Customer only from the next "
                   "renewal of its contract with the Reseller."),
    ("num", "9.3", "Clauses 3, 4, 5.3, 6 and 8 survive the end of the right of use."),

    ("h2", "10. General"),
    ("num", "10.1", "These terms are governed by %s, excluding its conflict of laws rules and the "
                    "United Nations Convention on Contracts for the International Sale of Goods." %
     LAW_EN),
    ("num", "10.2", "The exclusive place of jurisdiction, where the Customer is a merchant, is %s. "
                    "Where the Customer is not a merchant, the statutory rules apply." % FORUM),
    ("num", "10.3", "If a provision is invalid the remainder is unaffected."),
    ("num", "10.4", "These terms exist in German and in English. In the event of a discrepancy the "
                    "[German] version prevails."),

    ("pagebreak",),
    ("h2", "Annex - What the Customer should tell its own stakeholders"),
    ("p", "Written for the Customer to reuse. Everything here is a statement the Vendor stands "
          "behind."),
    ("table", ["Question a stakeholder asks", "The answer"], [
        ["Does anything touch our systems?",
         "No. The platform reads public sources. No packet is sent to the assessed organisation."],
        ["Do we need to open a firewall or install an agent?", "No. Neither."],
        ["Where is our data?",
         "Frankfurt am Main, Germany. The account data stays in the European Union."],
        ["Does an AI see our identity?",
         "No. The inference endpoint receives the technical findings; it does not receive a user "
         "identity or the account."],
        ["Is this a penetration test?",
         "No, and it must not be described as one. It is an external assessment from public "
         "information."],
        ["Can we use the report with our auditor or insurer?",
         "Yes, without restriction, for the Customer's own purposes."],
        ["Who do we call when it breaks?",
         "The Reseller. Service levels and credits are agreed with the Reseller."],
        ["What if the Reseller goes away?",
         "The right of use comes from the Vendor directly and survives a change of Reseller."],
    ]),

    ("pagebreak",),
    ("h2", "Acknowledgement"),
    ("p", "Where the Customer's procurement requires a signed copy, it may be signed here. "
          "Signature is not otherwise required: these terms are incorporated by the Customer's "
          "contract with the Reseller."),
    ("sig", "For %s (Vendor)" % VENDOR["name"], "For the Customer",
     ["Name:", "Function:", "Place:", "Date:"]),
]

DE = [
    ("h1", "ENDKUNDENBEDINGUNGEN"),
    ("meta", "%s  ·  %s  ·  Version %s  ·  %s  ·  Deutsches Recht, %s"
     % (VENDOR["name"], PLATFORM, VERSION, DATE_DE, FORUM)),

    ("p", "Diese Endkundenbedingungen regeln das Recht des in der Bestellunterlage benannten "
          "Unternehmens (der \"Kunde\") zur Nutzung der Plattform %s (die \"Plattform\"), deren "
          "Inhaber und Hersteller %s, %s (der \"Hersteller\") ist."
     % (PLATFORM, VENDOR["name"], VENDOR["addr_de"])),
    ("p", "Der Kunde erwirbt von einem autorisierten Wiederverkäufer (der \"Wiederverkäufer\"). "
          "Preis, Laufzeit, Abrechnung und Service Levels werden zwischen Kunde und "
          "Wiederverkäufer vereinbart. Diese Bedingungen regeln das Nutzungsrecht und werden in "
          "jenen Vertrag einbezogen."),
    ("note", NOTE_DE),

    ("h2", "1. Was die Plattform ist"),
    ("num", "1.1", "Die Plattform bewertet die Exposition eines Unternehmens AUSSCHLIESSLICH AUS "
                   "ÖFFENTLICHEN QUELLEN. Sie wertet Internet-Scandaten, "
                   "Certificate-Transparency-Logs, Routing-Register und öffentliches DNS aus."),
    ("num", "1.2", "SIE SENDET AN DAS BEWERTETE UNTERNEHMEN KEIN DATENPAKET. Sie führt gegen dieses "
                   "Unternehmen keinen Portscan, keine Schwachstellenprüfung und keinen "
                   "Anmeldeversuch durch."),
    ("num", "1.3", "Sie erzeugt Präsentationen, einen animierten Bericht und ein Laufprotokoll, das "
                   "das Vorgehen beschreibt."),
    ("num", "1.4", "Ein Ergebnisdokument ist eine Bewertung dessen, was öffentliche Informationen "
                   "zu einem Zeitpunkt gezeigt haben. ES IST KEIN Penetrationstest, keine "
                   "Sicherheitsgarantie, keine Zertifizierung, kein Prüfungsurteil, keine "
                   "versicherungstechnische Bewertung und keine Rechtsberatung; der Kunde wird es "
                   "nicht als solches darstellen."),
    ("num", "1.5", "Der Hersteller sichert nicht zu, dass ein Assessment jede Exposition erkennt, "
                   "dass eine öffentliche Quelle vollständig oder zutreffend ist oder dass ein "
                   "Ergebnisdokument frei von Feststellungen ist, die sich später als nicht "
                   "einschlägig erweisen. Der Hersteller sichert zu, dass die Plattform im "
                   "Wesentlichen ihrer Dokumentation entspricht."),

    ("h2", "2. Nutzungsrecht"),
    ("num", "2.1", "Der Hersteller räumt dem Kunden für die mit dem Wiederverkäufer vereinbarte "
                   "Laufzeit das nicht ausschließliche, nicht übertragbare Recht ein, auf die "
                   "Plattform für eigene interne Geschäftszwecke zuzugreifen und sie zu nutzen."),
    ("num", "2.2", "Das Recht wird vom Hersteller UNMITTELBAR eingeräumt. Es hängt nicht von einer "
                   "Unterlizenz des Wiederverkäufers ab und besteht bei einem Wechsel des "
                   "Wiederverkäufers fort."),
    ("num", "2.3", "Ist der Kunde ein Dienstleister, der eigene Kunden bewertet, darf er die "
                   "Plattform hierfür nutzen, sofern Ziffer 3 für jeden dieser Kunden erfüllt ist "
                   "und der Vertrag des Kunden mit diesem Kunden Regelungen im Sinne der Ziffern "
                   "1.4, 3 und 4 enthält."),
    ("num", "2.4", "Der Zugang erfolgt über benannte Einzelnutzer. Ein benannter Nutzer ist eine "
                   "natürliche Person; Zugangsdaten dürfen nicht geteilt werden. Ein benannter "
                   "Nutzer darf bei einem Rollenwechsel ersetzt werden."),
    ("num", "2.5", "Konzerngesellschaften des Kunden dürfen die Plattform im Rahmen der "
                   "Berechtigung des Kunden nutzen, sofern der Kunde für deren Einhaltung "
                   "verantwortlich bleibt."),

    ("h2", "3. Wessen Infrastruktur bewertet werden darf"),
    ("p", "Dies ist die Klausel, die alle Beteiligten rechtmäßig handeln lässt. Sie ist bewusst "
          "kurz."),
    ("num", "3.1", "Der Kunde darf ein Unternehmen nur zur Bewertung einreichen, wenn er dessen "
                   "Infrastruktur besitzt oder kontrolliert, die Autorisierung dieses Unternehmens "
                   "hat oder sonst rechtmäßig zur Bewertung berechtigt ist."),
    ("num", "3.2", "Der Kunde bestätigt diese Berechtigung bei jeder Einreichung. Der Hersteller "
                   "prüft sie nicht und kann sie nicht prüfen."),
    ("num", "3.3", "Der Kunde wird die Plattform nicht zum Zwecke der Wettbewerbsbeobachtung "
                   "einsetzen und keine Bewertung eines Dritten ohne dessen Einwilligung "
                   "veröffentlichen."),
    ("num", "3.4", "Der Kunde wird die Plattform nicht in einer Weise oder in einem Gebiet nutzen, "
                   "in dem dies rechtswidrig wäre, einschließlich nach Exportkontroll- oder "
                   "Sanktionsrecht."),

    ("h2", "4. Beschränkungen"),
    ("num", "4.1", "Der Kunde wird die Plattform nicht dekompilieren oder disassemblieren und nicht "
                   "versuchen, ihren Quellcode abzuleiten, soweit § 69e UrhG dies nicht zwingend "
                   "gestattet."),
    ("num", "4.2", "Der Kunde wird die Plattform nicht zu Veröffentlichungszwecken mit "
                   "Wettbewerbsprodukten vergleichen und sie nicht zum Aufbau oder Training eines "
                   "Konkurrenzdienstes nutzen."),
    ("num", "4.3", "Der Kunde wird die Plattform nicht weiterverkaufen, unterlizenzieren oder "
                   "Dritten zugänglich machen, ausgenommen nach Ziffer 2.3."),
    ("num", "4.4", "Der Kunde wird technische Beschränkungen, Ratenbegrenzungen oder "
                   "Berechtigungsprüfungen nicht umgehen."),
    ("num", "4.5", "Der Hersteller kann diese Ziffer 4 und Ziffer 3 unmittelbar gegenüber dem "
                   "Kunden durchsetzen, ohne den Wiederverkäufer beiladen zu müssen."),

    ("h2", "5. Die Ergebnisdokumente"),
    ("num", "5.1", "Der Kunde darf die für ihn erzeugten Ergebnisdokumente für eigene Zwecke "
                   "UNEINGESCHRÄNKT nutzen, auch im Verkehr mit seinen Prüfern, Versicherern, "
                   "Aufsichtsbehörden und eigenen Kunden."),
    ("num", "5.2", "Der Hersteller beansprucht kein Eigentum an den Daten des Kunden oder an den "
                   "Schlussfolgerungen, die der Kunde zieht."),
    ("num", "5.3", "Die Schutzrechte an der Plattform, ihrer Software, ihren Vorlagen und ihrer "
                   "Methodik verbleiben beim Hersteller. Der Kunde erhält ein Nutzungsrecht und "
                   "nicht mehr."),
    ("num", "5.4", "Liefert der Wiederverkäufer die Plattform unter eigener Marke, tragen die "
                   "Ergebnisdokumente diese Marke. Daran, wem die Plattform gehört und wen diese "
                   "Bedingungen binden, ändert das nichts."),

    ("h2", "6. Datenschutz"),
    ("num", "6.1", "Die von der Plattform verarbeiteten personenbezogenen Daten sind die "
                   "Kontodaten der eigenen Nutzer des Kunden: Name, geschäftliche E-Mail-Adresse, "
                   "Identität des Nutzers, der ein Assessment beauftragt hat, Anfragetelemetrie "
                   "und Supportkorrespondenz."),
    ("num", "6.2", "DIE ANALYSEKETTE ERHÄLT KEINE NUTZERIDENTITÄT. Die öffentlichen Datenquellen "
                   "erhalten den Namen oder die Domain des bewerteten Unternehmens. Der "
                   "Inferenz-Endpunkt, der die Textabschnitte erzeugt, erhält die technischen "
                   "Feststellungen. Keiner von beiden erhält die Identität einer Person."),
    ("num", "6.3", "Die Plattform wird in Frankfurt am Main, Deutschland, gehostet."),
    ("num", "6.4", "Ist der Kunde Verantwortlicher und der Wiederverkäufer Auftragsverarbeiter oder "
                   "umgekehrt, gilt die Vereinbarung zwischen ihnen. Der Hersteller stellt dem "
                   "Kunden seine eigenen Bedingungen nach Art. 28 DSGVO auf Anforderung zur "
                   "Verfügung."),
    ("num", "6.5", "Der Kunde wird keine besonderen Kategorien personenbezogener Daten übermitteln. "
                   "Die Plattform ist dafür nicht ausgelegt."),

    ("h2", "7. Sicherheit und Sperrung"),
    ("num", "7.1", "Der Kunde hält Zugangsdaten vertraulich und informiert den Wiederverkäufer "
                   "unverzüglich über den Verdacht einer Kompromittierung."),
    ("num", "7.2", "Der Hersteller darf den Zugang sperren, wenn er berechtigterweise von einer "
                   "Kompromittierung der Zugangsdaten ausgeht, wenn die Nutzung die Sicherheit oder "
                   "Integrität der Plattform erheblich gefährdet oder wenn die Sperrung gesetzlich "
                   "oder aufgrund von Sanktionen geboten ist."),
    ("num", "7.3", "Der Hersteller teilt den Grund unverzüglich mit, beschränkt die Sperrung auf "
                   "das vom Risiko Gebotene und stellt den Zugang wieder her, sobald die Ursache "
                   "entfallen ist."),
    ("num", "7.4", "Der Kunde wird wegen eines Zahlungsverzugs oberhalb des Wiederverkäufers nicht "
                   "gesperrt, solange er an den Wiederverkäufer zahlt."),

    ("h2", "8. Haftung"),
    ("num", "8.1", "Der Hersteller haftet unbeschränkt für Vorsatz und grobe Fahrlässigkeit, für "
                   "Schäden aus der Verletzung des Lebens, des Körpers oder der Gesundheit, nach "
                   "dem Produkthaftungsgesetz sowie bei Übernahme einer Garantie oder arglistigem "
                   "Verschweigen eines Mangels."),
    ("num", "8.2", "Bei einfacher Fahrlässigkeit haftet der Hersteller nur bei Verletzung einer "
                   "wesentlichen Vertragspflicht, also einer Pflicht, deren Erfüllung die "
                   "ordnungsgemäße Durchführung überhaupt erst ermöglicht und auf deren Einhaltung "
                   "der Kunde regelmäßig vertraut, und dann nur für den vertragstypischen, "
                   "vorhersehbaren Schaden."),
    ("num", "8.3", "Vorbehaltlich der Ziffern 8.1 und 8.2 ist die Gesamthaftung des Herstellers "
                   "gegenüber dem Kunden auf die Entgelte begrenzt, die der Kunde dem "
                   "Wiederverkäufer für die Plattform in den zwölf Monaten vor dem Ereignis gezahlt "
                   "hat."),
    ("num", "8.4", "DIE KOMMERZIELLEN ANSPRÜCHE DES KUNDEN RICHTEN SICH GEGEN DEN WIEDERVERKÄUFER. "
                   "Service Levels, Gutschriften, Erstattungen und Lieferpflichten werden mit dem "
                   "Wiederverkäufer vereinbart und ihm gegenüber geltend gemacht."),
    ("num", "8.5", "Der Hersteller haftet nicht für einen Sicherheitsvorfall bei einem bewerteten "
                   "Unternehmen, unabhängig davon, ob das Assessment den Angriffsweg erkannt hat. "
                   "Der Kunde trägt die Verantwortung für die Entscheidungen, die er auf Grundlage "
                   "eines Ergebnisdokuments trifft."),

    ("h2", "9. Laufzeit und Änderungen"),
    ("num", "9.1", "Diese Bedingungen gelten, solange dem Kunden aus seinem Vertrag mit dem "
                   "Wiederverkäufer ein Nutzungsrecht zusteht."),
    ("num", "9.2", "Der Hersteller kann diese Bedingungen ändern. Eine Änderung wird über den "
                   "Wiederverkäufer mindestens 30 Tage im Voraus mitgeteilt und gilt für den Kunden "
                   "erst ab der nächsten Verlängerung seines Vertrages mit dem Wiederverkäufer."),
    ("num", "9.3", "Die Ziffern 3, 4, 5.3, 6 und 8 gelten über das Ende des Nutzungsrechts hinaus "
                   "fort."),

    ("h2", "10. Allgemeines"),
    ("num", "10.1", "Diese Bedingungen unterliegen %s unter Ausschluss ihrer Kollisionsnormen und "
                    "des UN-Kaufrechts." % LAW_DE),
    ("num", "10.2", "Ausschließlicher Gerichtsstand ist, sofern der Kunde Kaufmann ist, %s. Ist der "
                    "Kunde kein Kaufmann, gelten die gesetzlichen Regelungen." % FORUM),
    ("num", "10.3", "Ist eine Bestimmung unwirksam, bleibt der übrige Inhalt unberührt."),
    ("num", "10.4", "Diese Bedingungen bestehen in deutscher und in englischer Sprache. Bei "
                    "Abweichungen ist die [deutsche] Fassung maßgeblich."),

    ("pagebreak",),
    ("h2", "Anlage - Was der Kunde seinen eigenen Beteiligten sagen kann"),
    ("p", "Zur Weiterverwendung durch den Kunden verfasst. Für jede Aussage steht der Hersteller "
          "ein."),
    ("table", ["Frage eines Beteiligten", "Die Antwort"], [
        ["Wird irgendetwas an unseren Systemen angefasst?",
         "Nein. Die Plattform wertet öffentliche Quellen aus. An das bewertete Unternehmen wird "
         "kein Datenpaket gesendet."],
        ["Müssen wir eine Firewall öffnen oder einen Agenten installieren?", "Nein, beides nicht."],
        ["Wo liegen unsere Daten?",
         "Frankfurt am Main, Deutschland. Die Kontodaten verbleiben in der Europäischen Union."],
        ["Sieht eine KI unsere Identität?",
         "Nein. Der Inferenz-Endpunkt erhält die technischen Feststellungen; er erhält weder eine "
         "Nutzeridentität noch das Konto."],
        ["Ist das ein Penetrationstest?",
         "Nein, und es darf nicht als solcher bezeichnet werden. Es ist eine externe Bewertung aus "
         "öffentlichen Informationen."],
        ["Dürfen wir den Bericht bei Prüfer oder Versicherer verwenden?",
         "Ja, uneingeschränkt, für eigene Zwecke des Kunden."],
        ["Wen rufen wir an, wenn etwas nicht funktioniert?",
         "Den Wiederverkäufer. Service Levels und Gutschriften werden mit ihm vereinbart."],
        ["Was passiert, wenn der Wiederverkäufer wegfällt?",
         "Das Nutzungsrecht stammt unmittelbar vom Hersteller und besteht bei einem Wechsel des "
         "Wiederverkäufers fort."],
    ]),

    ("pagebreak",),
    ("h2", "Bestätigung"),
    ("p", "Verlangt der Einkauf des Kunden eine unterzeichnete Fassung, kann hier unterzeichnet "
          "werden. Im Übrigen ist eine Unterzeichnung nicht erforderlich: Diese Bedingungen werden "
          "durch den Vertrag des Kunden mit dem Wiederverkäufer einbezogen."),
    ("sig", "Für %s (Hersteller)" % VENDOR["name"], "Für den Kunden",
     ["Name:", "Funktion:", "Ort:", "Datum:"]),
]
