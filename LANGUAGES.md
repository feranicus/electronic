# Languages — what we ship, why those four, and what the decks can actually produce

## What ships today

| Surface | Languages | Source of truth |
|---|---|---|
| Marketing site (`/`, `/demo`, `/contact`, `/privacy`, `/impressum`, `/login`) | EN · DE · IT · FR · ES · PL | `webapp/frontend/src/locales/*.js` |
| Cabinet (Assess, Compliance, Assistant, History, Sidebar) | EN · DE · IT · FR · ES · PL | same |
| Legal pages + the Art.13 notice | EN · DE · IT · FR · ES · PL | `webapp/frontend/src/legal.jsx` (DE/EN) + `src/legal-locales/*.jsx` |
| Telegram bots — interface | EN · DE · IT · FR · ES · PL | `assess-bot/bot.py::T`, `cassandra-bot::LANG_INSTRUCTION` |
| **Generated decks + the animated report** | **EN · DE · RU** | `hermes-skills/shodan-assessment/scripts/i18n/` |

**German is the NORMATIVE legal text.** The other five privacy translations are reading
translations and say so in their first sentence. That is standard practice and it is what makes
shipping a translated legal page safe.

## Why the deck languages are a SHORTER list than the interface languages

A deck language needs three things, and only two of them are a dictionary:

1. `scripts/i18n/<lang>.json` — the ~620 deck-chrome literals,
2. `scripts/i18n/i18n.py` — the engine-deterministic prose post-pass (finding titles, controls),
3. a `LANG_*` prompt block in `enrich.py` — the **per-company prose**, which no dictionary can ever
   cover because a model writes it fresh for every customer.

So "the site speaks Polish" does not imply "the decks speak Polish". Russian is the third deck language: it was added on request and exists end-to-end (chrome dictionary, engine post-pass, `LANG_RU` prompt block, compliance labels, animated HTML). `scripts/deck_langs.py` is the
single source of truth: it derives the list from the dictionaries actually present on disk, serves it
at `GET /api/langs`, and `supported()` coerces any other request down to English. The Assess screen
and the bot build their language choices from that list and say plainly, in the reader's own
language, when their interface language is not one the decks can be written in.

Before this, the Assess screen defaulted the document language from the SITE language. An Italian
reader would have sent `--lang it`, the engine would have fallen back to English, and nothing would
have said so. **Adding a locale is now: drop `it.json` in, add the enrich prompt block — the UI picks
it up on the next deploy with no frontend change.**

## Why Italian → French → Spanish → Polish

Chosen from a market study of where the buyer personas (MSP, VAR, GSI, cyber consultancy,
regulator) concentrate **and** where NIS2 is actually being enforced, at a €100–200/month
subscription with workshop and remediation upsell.

**The finding that reframed the question: English proficiency does not discriminate between the
serious candidates — the law does.** The Netherlands is #1 in the world on EF EPI 2025, Portugal #6,
Sweden #8, Poland #15. Italy (#59) and France (#38) are the only large Western European markets
where English is genuinely "Moderate". So the case is argued from regulatory urgency, channel size,
and where the deliverable legally has to go.

1. **Italian** — the only market with a *counted* register rather than an estimate: ACN puts the NIS
   list at **>20,000 organisations, >5,000 of them essential entities**. Italy met the 17 Oct 2024
   deadline and is not under infringement, and **from October 2026 ACN can begin audits**. ACN
   publishes a countable checklist to assess against (43 measures / 116 requirements). The channel is
   ~132,800 ICT firms; Italian MSPs already resell a quarterly vulnerability assessment at
   €1,500–8,000, so a €150 seat pays for itself on the first engagement of the year. And Italy has
   the weakest English of any large Western European market. *Weakness: no Italian-language mandate —
   the Consiglio di Stato has held an English-language bid annex cannot ground exclusion. Sell on the
   20,000 entities and the October 2026 audits, not on a language rule.*
2. **French** — the largest channel in Europe (€34.6bn ESN segment, ~670,000 employees, ~7,000 IT
   service providers of which 54% self-identify as MSP) and **65% of French SMEs outsource their
   cybersecurity — the highest adoption of twenty countries surveyed**. Uniquely, French-language
   documentation is a *litigated* legal exposure: Loi Toubon Art. 2 and Code du travail L.1321-6,
   applied to software twice in the appeal courts. France has not transposed NIS2 and is before the
   CJEU, but ANSSI's ReCyF gives a concrete framework to assess against today — you want to be
   localised *before* the law lands.
3. **Spanish** — 4th-largest cyber market in Europe (12% of continental revenue, €2.5bn → >€3bn at
   ~14% CAGR), EF 540, and the lowest incremental engineering cost of any remaining candidate as the
   third Romance locale. *Weakness, stated honestly: Spain has not transposed, is before the CJEU,
   and has no single NIS2 authority yet. Mitigation: ship ENS (Esquema Nacional de Seguridad) mapping
   alongside — Spanish buyers bundle ENS with NIS2 in the same sentence. Spain is also the most
   price-sensitive of the four; sell to the MSP as production capacity, never as an end-customer
   seat.*
4. **Polish** — the **largest in-scope population in the EU: ~38,000 entities, ~27,000 of them public
   bodies**, per the authoring ministry. The KSC amendment is in force since 3 April 2026 with the
   most sellable calendar of any market — registration 3 Oct 2026, obligations 3 Apr 2027, and **a
   mandatory audit from 3 Apr 2028 and every three years thereafter**, i.e. recurring revenue written
   into national law. The cyber market grew +25% y/y. *The language case is not about the buyer —
   Polish technical staff read English fine (EF 600, IT function 621). It is about where the artefact
   goes: Prawo zamówień publicznych Art. 20 ust. 2 requires procurement in Polish, and in practice a
   foreign-language document without a translation is treated as absent from the bid. That gates 71%
   of the population by count.*

### Runners-up and why they lost

- **Portuguese** — the best product-market-fit fact in the whole study (DL 125/2025 obliges every
  qualified entity to file an **inventory of internet-facing assets** with CNCS by 31 Jan 2027 — that
  is literally this engine's output, mandated), plus the hardest procurement language rule in the EU.
  Lost on wallet: total national cyber investment €371m, managed services €72.67m — a fifteenth of
  Spain. Portugal is also #6 in the world for English, and CNCS is shipping free open-source tooling
  that commoditises part of the product. Revisit if a Portuguese anchor partner appears; the
  translation is cheap once Spanish and French exist.
- **Japanese** — the best pure-language ROI on earth (EF #96, 90% of buyers prefer their own
  language, >72% of IT professionals sit inside SIers). Lost because **the differentiator is EU
  regulation and Japan's mainstream buyer does not care about NIS2** — only ~1,457 Japanese companies
  have an EU presence. Japan is a *product* decision, not a localisation one; if ever done, gate it on
  one SIer partner and lead with METI's ASM guidance + CRA export readiness.
- **Arabic** — Saudi is the bigger prize (SAR 15.2bn, +14%) but EU regulation has near-zero pull, Gulf
  IT works in English, and RTL is disproportionately expensive for this stack (pptxgenjs has an open
  defect on mixed RTL/LTR, and the decks are wall-to-wall bidirectional text: CVE IDs, IPs, ASNs,
  product names inside prose). The cheap correct move if the Gulf ever matters: keep the UI English
  and add `--lang ar` as a **deck output language only**, which satisfies Saudi GTPL Art. 55.

### Markets that do NOT justify localisation — the buyers work in English

Netherlands (EF #1; the national Cybersecurity Woordenboek keeps *attack surface*, *compliance*,
*red teaming* as English headwords — an over-translated Dutch build reads amateurish), the Nordics
(603–613), Czechia / Romania / Greece (582–605), UAE (IT function 493, Dubai 509), UK and Ireland.
Switzerland is already covered by German + French. **Brazil is the one market where proficiency
argues for localisation and the regulatory case collapses completely**: total ANPD fines across ~6
years of LGPD are R$14,400 (~€2,400), there is no Brazilian NIS2, a seat is ~9–10% of an analyst's
gross monthly salary, and there is a ~36% tax/FX gross-up. Set a trigger, not a date: revisit when a
Brazilian cyber act is sanctioned with a named authority holding sanctioning power.

## Rules that keep this from rotting

- **Never translate the instrument names**: NIS2, CRA / Cyber Resilience Act, DORA, EU AI Act, MITRE
  ATT&CK, FAIR, NIST. GDPR *is* translated (RGPD / RODO / DSGVO; Italian keeps GDPR). CERT Polska's
  own usage confirms the English name with a local gloss. **Over-translation is a bigger risk than
  under-translation in this domain** — which inverts the lesson from the German build.
- **Localise the legal citation, not just the prose.** An artefact citing Directive article numbers
  is not usable in a national submission. Italy must cite D.Lgs. 138/2024 and ACN's measures; France
  ReCyF; Spain ENS alongside NIS2; Poland the KSC amendment and *podmiot kluczowy/ważny*.
- **`tab.*` labels are a hard 8-character maximum** in every language — six share a 360px phone row.
  Asserted by `tools/i18n_audit.jsx`, per language, because German/French/Polish overflow first.
- **Polish past-tense verbs are gendered and a UI string cannot know the reader's gender.** Use the
  impersonal (`-no/-to`), the infinitive, or a noun phrase. Never `Pan/Pani` in an interface.
- **Register is encoded, not inferred**: Italian `Lei`, French `vous`, Spanish `usted` (es-ES —
  `vosotros`, never `ustedes`), Polish impersonal. For LLM-generated prose this belongs in the
  `LANG_*` prompt block, not the dictionary — a dictionary cannot reach text a model writes.

## The one command

Everything above is gated by `python ship.py`: the catalogue must be 100% in all six locales, and the
SSR audit renders 11 pages × 6 languages and fails on a raw key, a leaked `undefined`, an
over-length tab label, or English function-word residue above 6%.


## Adding a deck language — the whole checklist

`deck_langs.py` offers a language only when **both halves** exist, and fails closed otherwise:

1. `scripts/i18n/<code>.json` — the ~620 chrome strings, plus `locale`, `dateFormat` (`"dmy"` or ISO)
   and `units` (`bn`/`M`/`k` suffixes). The dictionary declares its own formatting rules; there is no
   `if (LANG === "xx")` anywhere in `deck_i18n.js` any more.
2. A `LANG_<CODE>` block registered in `enrich.py::LANG_BLOCKS` — the per-company PROSE. Without it a
   deck would render translated labels wrapped around English paragraphs, which is worse than an
   honest English deck, so `doc_langs()` refuses to list the language at all.

Optional but expected for parity: `compliance_enrich.py::LANG_BLOCKS`, the `ru:` column of
`build_compliance_deck.js::LABELS`, `geopol_html/i18n/<code>.json` for the animated report, and the
creed pair in `creed.js` (asserted byte-identical to the dictionary by `test_creed.js`).

`python ship.py` then renders every claimed language from the sample fixture with the dictionary
audit on and **fails if any string the German pack covers is still English** — German is the
reference locale, so "German translates it, this one does not" is the definition of a gap.
