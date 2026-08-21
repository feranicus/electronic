# -*- coding: utf-8 -*-
"""03 - Mutual non-disclosure agreement, German law.

Signable on its own and before anything else is agreed, which is the point of it.

THE GERMAN-SPECIFIC PART is clause 3.4. Since the Trade Secrets Act (GeschGehG) came into force in
2019, information is only a protected trade secret in Germany if its holder has taken "angemessene
Geheimhaltungsmassnahmen" - reasonable steps to keep it secret. An NDA that only forbids disclosure
does nothing to establish that; an NDA that obliges both sides to apply named measures is itself
part of the evidence. The English-only head document has no equivalent because it is not drafted
for German law.
"""
from common import BYON, DATE_DE, DATE_EN, NOTE_DE, NOTE_EN, OBJECTALE, PLATFORM, VERSION

EN = [
    ("h1", "MUTUAL NON-DISCLOSURE AGREEMENT"),
    ("meta", "%s and %s  ·  Version %s  ·  %s  ·  German law, Frankfurt am Main"
     % (OBJECTALE["name"], BYON["name"], VERSION, DATE_EN)),
    ("p", "This Mutual Non-Disclosure Agreement (this \"Agreement\") takes effect on [effective "
          "date] between %s, %s (\"objectale\"), and %s, %s, registered with the %s (\"byon\"). "
          "Each a \"Party\"." % (OBJECTALE["name"], OBJECTALE["addr"], BYON["name"], BYON["addr"],
                                 BYON["reg"])),
    ("note", NOTE_EN),

    ("h2", "1. Purpose"),
    ("num", "1.1", "The Parties wish to evaluate and, if agreed, implement a commercial "
                   "relationship under which objectale supplies, and byon resells to its own "
                   "customers, the %s assessment platform (the \"Purpose\")." % PLATFORM),
    ("num", "1.2", "For the Purpose each Party may disclose confidential information to the other. "
                   "Each Party may act as Disclosing Party and as Receiving Party."),

    ("h2", "2. Confidential Information"),
    ("num", "2.1", "\"Confidential Information\" means any information disclosed for the Purpose, "
                   "in any form, that is marked confidential or that a reasonable recipient would "
                   "understand to be confidential from its nature or the circumstances of "
                   "disclosure."),
    ("num", "2.2", "It includes commercial terms, price lists, discount structures, customer and "
                   "prospect names, technical architecture, assessment methodology, unpublished "
                   "product plans, security information and the existence and content of the "
                   "Parties' negotiations."),
    ("num", "2.3", "It includes information about a Party's own customers and, in particular, any "
                   "assessment output relating to an organisation, which is treated as the "
                   "Confidential Information of the Party that holds the customer relationship."),
    ("num", "2.4", "Information does not need to be marked to be protected, and marking does not "
                   "make protected information that falls within clause 3."),

    ("h2", "3. Exclusions"),
    ("num", "3.1", "The obligations do not apply to information that is or becomes public without "
                   "a breach of this Agreement."),
    ("num", "3.2", "They do not apply to information the Receiving Party already lawfully held "
                   "without a duty of confidence, as it can show from its records."),
    ("num", "3.3", "They do not apply to information lawfully received from a third party free to "
                   "disclose it, or independently developed without use of the Confidential "
                   "Information."),
    ("num", "3.4", "The Receiving Party bears the burden of showing that an exclusion applies."),

    ("h2", "4. Obligations"),
    ("num", "4.1", "The Receiving Party will keep Confidential Information secret, will use it "
                   "only for the Purpose, and will not disclose it to a third party without prior "
                   "written consent."),
    ("num", "4.2", "The Receiving Party may disclose to its employees, officers, professional "
                   "advisers and affiliates who need the information for the Purpose and who are "
                   "bound by duties at least as protective. The Receiving Party remains "
                   "responsible for their compliance."),
    ("num", "4.3", "The Receiving Party will protect Confidential Information with at least the "
                   "care it applies to its own confidential information of like importance, and in "
                   "no case with less than reasonable care."),
    ("num", "4.4", "Reasonable steps to maintain secrecy. Each Party will apply, as a minimum, "
                   "access control limited to those who need the information, storage on systems "
                   "under its control with authentication, marking or equivalent identification of "
                   "confidential material, contractual confidentiality obligations on personnel, "
                   "and secure deletion under clause 9. The Parties agree that these constitute "
                   "reasonable steps to maintain secrecy within the meaning of Section 2 no. 1(b) "
                   "of the German Trade Secrets Act."),

    ("h2", "5. Limited use, no reverse engineering"),
    ("num", "5.1", "The Receiving Party will not use Confidential Information to compete with the "
                   "Disclosing Party, to solicit its customers, or for any purpose other than the "
                   "Purpose."),
    ("num", "5.2", "The Receiving Party will not decompile, disassemble or otherwise attempt to "
                   "derive the source code, structure or underlying method of any software or "
                   "system made accessible for the Purpose, except to the extent Section 69e of "
                   "the German Copyright Act permits and cannot be excluded by contract."),
    ("num", "5.3", "The Receiving Party will not run an assessment, a scan or a test against the "
                   "other Party's infrastructure without prior written authorisation identifying "
                   "the systems and the period."),

    ("h2", "6. No licence, no obligation"),
    ("num", "6.1", "Confidential Information remains the property of the Disclosing Party. This "
                   "Agreement grants no licence in any intellectual property, whether express or "
                   "implied."),
    ("num", "6.2", "Neither Party is obliged to disclose anything, to proceed with the Purpose, or "
                   "to enter into any further agreement."),
    ("num", "6.3", "Nothing in this Agreement restricts either Party from doing business with any "
                   "third party, including a competitor of the other, provided it does not use the "
                   "other's Confidential Information to do so."),

    ("h2", "7. Disclosure required by law"),
    ("num", "7.1", "The Receiving Party may disclose Confidential Information where required by "
                   "law, by a court or by a competent authority."),
    ("num", "7.2", "Where lawful, it will notify the Disclosing Party in advance and in time for "
                   "the Disclosing Party to seek protection, will disclose only what is required, "
                   "and will ask for confidential treatment."),

    ("h2", "8. Term and survival"),
    ("num", "8.1", "This Agreement runs for two years from the effective date. Either Party may "
                   "terminate it on 30 days' written notice."),
    ("num", "8.2", "The obligations in respect of Confidential Information disclosed during the "
                   "term continue for five years from the date of disclosure."),
    ("num", "8.3", "Information that qualifies as a trade secret remains protected for as long as "
                   "it qualifies, without time limit."),
    ("num", "8.4", "Where the Parties later sign a reseller framework agreement, its "
                   "confidentiality clause supplements this Agreement and this Agreement continues "
                   "to apply to disclosures made before it."),

    ("h2", "9. Return and destruction"),
    ("num", "9.1", "On written request, and in any event on termination, the Receiving Party will "
                   "return or securely destroy Confidential Information and will confirm in "
                   "writing which it has done."),
    ("num", "9.2", "The Receiving Party may retain one copy where required by law or by its "
                   "professional obligations, and copies held in routine backup that are not "
                   "readily accessible, provided this Agreement continues to apply to them for as "
                   "long as they are retained."),

    ("h2", "10. Remedies"),
    ("num", "10.1", "The Parties agree that damages alone may not be an adequate remedy for a "
                    "breach and that the Disclosing Party is entitled to seek interim relief, "
                    "including an injunction, without having to show actual damage."),
    ("num", "10.2", "The rights and remedies under the German Trade Secrets Act are unaffected."),
    ("num", "10.3", "Each Party's liability under this Agreement is unlimited for intent and gross "
                    "negligence, for injury to life, body or health and under the Product "
                    "Liability Act. For simple negligence liability is limited to the breach of a "
                    "material contractual obligation and to the foreseeable damage typical for "
                    "this type of contract."),

    ("h2", "11. No warranty as to accuracy"),
    ("num", "11.1", "Confidential Information is provided as it stands. Neither Party warrants its "
                    "accuracy or completeness, save for any warranty expressly given in a later "
                    "signed agreement."),
    ("num", "11.2", "Any assessment output disclosed for the Purpose is based on public "
                    "information at a point in time. It is not a guarantee of security, not legal "
                    "advice and not an audit opinion."),

    ("h2", "12. General"),
    ("num", "12.1", "Variations require text form within the meaning of Section 126b BGB, "
                    "including a variation of this clause."),
    ("num", "12.2", "Neither Party may assign this Agreement without the other's prior written "
                    "consent, except to an affiliate or in connection with a transfer of the whole "
                    "business, which must be notified."),
    ("num", "12.3", "If a provision is invalid, the remainder is unaffected and the Parties will "
                    "replace it with a valid provision closest to its purpose."),
    ("num", "12.4", "This Agreement is executed in German and in English. In the event of a "
                    "discrepancy, the [German] version prevails."),
    ("num", "12.5", "The Parties may sign in counterparts and by electronic signature."),

    ("h2", "13. Governing law and jurisdiction"),
    ("num", "13.1", "This Agreement is governed by German law, excluding its conflict of laws "
                    "rules and the UN Convention on Contracts for the International Sale of "
                    "Goods."),
    ("num", "13.2", "The exclusive place of jurisdiction is Frankfurt am Main."),

    ("h2", "14. Signatures"),
    ("sig", "For %s" % OBJECTALE["name"], "For %s" % BYON["name"],
     ["Name:", "Function:", "Place:", "Date:"]),
]

DE = [
    ("h1", "GEGENSEITIGE GEHEIMHALTUNGSVEREINBARUNG"),
    ("meta", "%s und %s  ·  Version %s  ·  %s  ·  Deutsches Recht, Frankfurt am Main"
     % (OBJECTALE["name"], BYON["name"], VERSION, DATE_DE)),
    ("p", "Diese gegenseitige Geheimhaltungsvereinbarung (die \"Vereinbarung\") tritt am [Datum des "
          "Inkrafttretens] zwischen %s, %s (\"objectale\"), und %s, %s, eingetragen beim %s "
          "(\"byon\"), in Kraft. Jeweils eine \"Partei\"."
     % (OBJECTALE["name"], OBJECTALE["addr_de"], BYON["name"], BYON["addr_de"], BYON["reg"])),
    ("note", NOTE_DE),

    ("h2", "1. Zweck"),
    ("num", "1.1", "Die Parteien beabsichtigen, eine geschäftliche Zusammenarbeit zu prüfen und, "
                   "sofern vereinbart, umzusetzen, bei der objectale die Assessment-Plattform %s "
                   "liefert und byon sie an eigene Kunden weiterverkauft (der \"Zweck\")."
     % PLATFORM),
    ("num", "1.2", "Zu diesem Zweck kann jede Partei der anderen vertrauliche Informationen "
                   "offenlegen. Jede Partei kann offenlegende und empfangende Partei sein."),

    ("h2", "2. Vertrauliche Informationen"),
    ("num", "2.1", "\"Vertrauliche Informationen\" sind alle zum Zweck offengelegten Informationen "
                   "in jeder Form, die als vertraulich gekennzeichnet sind oder deren "
                   "Vertraulichkeit ein verständiger Empfänger aus ihrer Natur oder den Umständen "
                   "der Offenlegung erkennen musste."),
    ("num", "2.2", "Dazu gehören kommerzielle Konditionen, Preislisten, Rabattstrukturen, Kunden- "
                   "und Interessentennamen, technische Architektur, Assessment-Methodik, "
                   "unveröffentlichte Produktplanungen, Sicherheitsinformationen sowie Bestehen und "
                   "Inhalt der Verhandlungen der Parteien."),
    ("num", "2.3", "Dazu gehören Informationen über eigene Kunden einer Partei und insbesondere "
                   "jedes Assessment-Ergebnis zu einem Unternehmen, das als vertrauliche "
                   "Information derjenigen Partei gilt, die die Kundenbeziehung hält."),
    ("num", "2.4", "Eine Kennzeichnung ist für den Schutz nicht erforderlich; eine Kennzeichnung "
                   "macht Informationen, die unter Ziffer 3 fallen, nicht schutzfähig."),

    ("h2", "3. Ausnahmen"),
    ("num", "3.1", "Die Pflichten gelten nicht für Informationen, die ohne Verstoß gegen diese "
                   "Vereinbarung öffentlich sind oder werden."),
    ("num", "3.2", "Sie gelten nicht für Informationen, die die empfangende Partei bereits "
                   "rechtmäßig und ohne Geheimhaltungspflicht besaß, was sie durch ihre "
                   "Aufzeichnungen belegen kann."),
    ("num", "3.3", "Sie gelten nicht für Informationen, die rechtmäßig von einem zur Offenlegung "
                   "berechtigten Dritten erlangt oder unabhängig ohne Nutzung der vertraulichen "
                   "Informationen entwickelt wurden."),
    ("num", "3.4", "Die Darlegungs- und Beweislast für das Vorliegen einer Ausnahme trägt die "
                   "empfangende Partei."),

    ("h2", "4. Pflichten"),
    ("num", "4.1", "Die empfangende Partei wird vertrauliche Informationen geheim halten, sie nur "
                   "zum Zweck verwenden und sie ohne vorherige schriftliche Zustimmung nicht an "
                   "Dritte weitergeben."),
    ("num", "4.2", "Die empfangende Partei darf sie ihren Mitarbeitern, Organen, "
                   "Berufsgeheimnisträgern und verbundenen Unternehmen offenlegen, die sie zum "
                   "Zweck benötigen und die mindestens gleichwertigen Pflichten unterliegen. Die "
                   "empfangende Partei bleibt für deren Einhaltung verantwortlich."),
    ("num", "4.3", "Die empfangende Partei schützt vertrauliche Informationen mindestens mit der "
                   "Sorgfalt, die sie für eigene vertrauliche Informationen vergleichbarer Bedeutung "
                   "anwendet, in keinem Fall jedoch mit weniger als der verkehrsüblichen Sorgfalt."),
    ("num", "4.4", "Angemessene Geheimhaltungsmaßnahmen. Jede Partei ergreift mindestens folgende "
                   "Maßnahmen: Zugriffsbeschränkung auf Personen mit Kenntnisbedarf, Speicherung "
                   "auf durch Authentifizierung geschützten eigenen Systemen, Kennzeichnung oder "
                   "gleichwertige Identifizierung vertraulichen Materials, vertragliche "
                   "Verschwiegenheitspflichten der Beschäftigten sowie sichere Löschung nach Ziffer "
                   "9. Die Parteien sind sich einig, dass dies angemessene Geheimhaltungsmaßnahmen "
                   "im Sinne des § 2 Nr. 1 lit. b GeschGehG darstellt."),

    ("h2", "5. Zweckbindung, kein Reverse Engineering"),
    ("num", "5.1", "Die empfangende Partei wird vertrauliche Informationen nicht nutzen, um der "
                   "offenlegenden Partei Wettbewerb zu machen, deren Kunden abzuwerben oder zu "
                   "einem anderen Zweck als dem Zweck."),
    ("num", "5.2", "Die empfangende Partei wird Software oder Systeme, die zum Zweck zugänglich "
                   "gemacht werden, nicht dekompilieren, disassemblieren oder auf sonstige Weise "
                   "versuchen, deren Quellcode, Aufbau oder zugrunde liegende Methode abzuleiten, "
                   "soweit § 69e UrhG dies nicht zwingend gestattet."),
    ("num", "5.3", "Die empfangende Partei wird ohne vorherige schriftliche Autorisierung, die die "
                   "Systeme und den Zeitraum benennt, kein Assessment, keinen Scan und keinen Test "
                   "gegen die Infrastruktur der anderen Partei durchführen."),

    ("h2", "6. Keine Lizenz, keine Verpflichtung"),
    ("num", "6.1", "Vertrauliche Informationen bleiben Eigentum der offenlegenden Partei. Diese "
                   "Vereinbarung räumt weder ausdrücklich noch stillschweigend Rechte an "
                   "Schutzrechten ein."),
    ("num", "6.2", "Keine Partei ist verpflichtet, etwas offenzulegen, den Zweck weiterzuverfolgen "
                   "oder eine weitere Vereinbarung zu schließen."),
    ("num", "6.3", "Diese Vereinbarung hindert keine Partei daran, mit Dritten Geschäfte zu machen, "
                   "auch mit Wettbewerbern der anderen, sofern sie dabei die vertraulichen "
                   "Informationen der anderen nicht verwendet."),

    ("h2", "7. Gesetzlich vorgeschriebene Offenlegung"),
    ("num", "7.1", "Die empfangende Partei darf vertrauliche Informationen offenlegen, soweit sie "
                   "aufgrund Gesetzes, gerichtlicher oder behördlicher Anordnung dazu verpflichtet "
                   "ist."),
    ("num", "7.2", "Soweit zulässig, wird sie die offenlegende Partei vorab und so rechtzeitig "
                   "informieren, dass diese Rechtsschutz suchen kann, nur das Erforderliche "
                   "offenlegen und um vertrauliche Behandlung ersuchen."),

    ("h2", "8. Laufzeit und Fortgeltung"),
    ("num", "8.1", "Diese Vereinbarung läuft zwei Jahre ab dem Datum des Inkrafttretens. Jede "
                   "Partei kann sie mit einer Frist von 30 Tagen schriftlich kündigen."),
    ("num", "8.2", "Die Pflichten hinsichtlich während der Laufzeit offengelegter vertraulicher "
                   "Informationen bestehen fünf Jahre ab dem Zeitpunkt der jeweiligen Offenlegung "
                   "fort."),
    ("num", "8.3", "Informationen, die Geschäftsgeheimnisse sind, bleiben ohne zeitliche Begrenzung "
                   "geschützt, solange sie diese Eigenschaft besitzen."),
    ("num", "8.4", "Schließen die Parteien später einen Wiederverkäufer-Rahmenvertrag, ergänzt "
                   "dessen Vertraulichkeitsklausel diese Vereinbarung; diese Vereinbarung gilt für "
                   "zuvor erfolgte Offenlegungen fort."),

    ("h2", "9. Rückgabe und Löschung"),
    ("num", "9.1", "Auf schriftliche Aufforderung, in jedem Fall bei Beendigung, gibt die "
                   "empfangende Partei vertrauliche Informationen zurück oder löscht sie sicher und "
                   "bestätigt schriftlich, was sie getan hat."),
    ("num", "9.2", "Die empfangende Partei darf ein Exemplar aufbewahren, soweit gesetzliche oder "
                   "berufsrechtliche Pflichten dies verlangen, sowie Kopien in routinemäßigen "
                   "Sicherungen, die nicht ohne Weiteres zugänglich sind, sofern diese Vereinbarung "
                   "für die Dauer der Aufbewahrung darauf weiter Anwendung findet."),

    ("h2", "10. Rechtsbehelfe"),
    ("num", "10.1", "Die Parteien sind sich einig, dass Schadensersatz allein einen Verstoß "
                    "möglicherweise nicht angemessen ausgleicht und dass die offenlegende Partei "
                    "berechtigt ist, einstweiligen Rechtsschutz einschließlich einer Unterlassungs"
                    "verfügung zu beantragen, ohne einen konkreten Schaden darlegen zu müssen."),
    ("num", "10.2", "Ansprüche und Rechtsbehelfe nach dem GeschGehG bleiben unberührt."),
    ("num", "10.3", "Die Haftung jeder Partei aus dieser Vereinbarung ist unbeschränkt für Vorsatz "
                    "und grobe Fahrlässigkeit, für Schäden aus der Verletzung des Lebens, des "
                    "Körpers oder der Gesundheit sowie nach dem Produkthaftungsgesetz. Bei "
                    "einfacher Fahrlässigkeit ist die Haftung auf die Verletzung wesentlicher "
                    "Vertragspflichten und auf den vertragstypischen, vorhersehbaren Schaden "
                    "begrenzt."),

    ("h2", "11. Keine Gewähr für Richtigkeit"),
    ("num", "11.1", "Vertrauliche Informationen werden wie vorhanden zur Verfügung gestellt. Keine "
                    "Partei sichert deren Richtigkeit oder Vollständigkeit zu, soweit nicht in "
                    "einer später unterzeichneten Vereinbarung ausdrücklich zugesichert."),
    ("num", "11.2", "Ein zum Zweck offengelegtes Assessment-Ergebnis beruht auf öffentlichen "
                    "Informationen zu einem Zeitpunkt. Es ist keine Sicherheitsgarantie, keine "
                    "Rechtsberatung und kein Prüfungsurteil."),

    ("h2", "12. Allgemeines"),
    ("num", "12.1", "Änderungen bedürfen der Textform im Sinne des § 126b BGB, auch die Änderung "
                    "dieser Ziffer."),
    ("num", "12.2", "Keine Partei darf diese Vereinbarung ohne vorherige schriftliche Zustimmung "
                    "der anderen abtreten, ausgenommen an ein verbundenes Unternehmen oder im "
                    "Zusammenhang mit einer Übertragung des gesamten Geschäftsbetriebs; dies ist "
                    "anzuzeigen."),
    ("num", "12.3", "Ist eine Bestimmung unwirksam, bleibt der übrige Inhalt unberührt; die "
                    "Parteien ersetzen sie durch eine wirksame Bestimmung, die ihrem Zweck am "
                    "nächsten kommt."),
    ("num", "12.4", "Diese Vereinbarung wird in deutscher und in englischer Sprache ausgefertigt. "
                    "Bei Abweichungen ist die [deutsche] Fassung maßgeblich."),
    ("num", "12.5", "Die Parteien können in Ausfertigungen und elektronisch unterzeichnen."),

    ("h2", "13. Anwendbares Recht und Gerichtsstand"),
    ("num", "13.1", "Diese Vereinbarung unterliegt deutschem Recht unter Ausschluss seiner "
                    "Kollisionsnormen und des UN-Kaufrechts."),
    ("num", "13.2", "Ausschließlicher Gerichtsstand ist Frankfurt am Main."),

    ("h2", "14. Unterschriften"),
    ("sig", "Für %s" % OBJECTALE["name"], "Für %s" % BYON["name"],
     ["Name:", "Funktion:", "Ort:", "Datum:"]),
]
