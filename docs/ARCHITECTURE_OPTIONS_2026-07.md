# cybergod.ai — Architecture Review & Options Paper
### Why five iterations produced no measurable gain, and the three options in each problem area

**Date:** 30 July 2026 · **Author:** engineering · **Status:** for decision
**Audience:** Evgeny (product owner) · **Decision needed on:** 3 architecture decisions (ADR-01..03)

---

## 0. The honest diagnosis first

You said: *"we make like 5+ iterations and standing on one spot all the time, full gas in neutral."*
That is accurate, and the cause is architectural, not effort.

**Every change so far was validated against my reasoning, not against a measured baseline.** I would
find a defect, fix it, run unit tests that exercised *helpers*, and declare success. The system had
no definition of "better", so it could not move toward it. Symptoms:

| Iteration | What I fixed | Why it did not move the needle |
|---|---|---|
| 1 | Ownership gate (`_org_is_the_target`) | Fixed precision; recall untouched — 1 of 8 domains found |
| 2 | Group-structure discovery | Gate learned the subsidiaries; **nothing searched them** |
| 3 | Fed subsidiaries into discovery | Worked — but chain still ran gemma; deck footer exploded |
| 4 | Chain in `_FALLBACKS` | Overridden by compose `environment:` |
| 5 | Deleted compose value | Overridden by *legacy* `.env ENRICH_MODEL` |

The pattern is identical each time: **one variable, several homes; one quality goal, no metric.**
`test_parity.py` (added in iteration 5) is the first real ground truth in this repo — it replays
your own manual Shodan harvest and fails the deploy on regression. Everything below builds on that
idea: *make quality measurable, then changes become provable rather than argued.*

---

## 1. Baseline architecture (TOGAF Phase B — "as-is")

**Business layer.** Colt pre-sales SE or partner enters one company name → receives 4 decks + an
animated HTML report, EN or DE, in ~2–4 minutes, at ~$0.005 AI cost.

**Application layer.**

```
seed (name|domain)
   └─> autodiscover()        identity resolution: ASN, CT logs, cert SAN/CN, DNS probe,
   │                          group-structure crawl, whois-org pivots
   └─> run()                 Shodan sweep → ownership gates → co-tenant guard → host set
   └─> classify()            per-host severity + finding kind (deterministic rules)
   └─> enrich.py             ONE LLM call, whole-estate prompt → JSON prose
   └─> 4× pptxgenjs builders + 1 HTML builder   (deterministic rendering)
   └─> audit_fp.py           second LLM, different vendor, advisory only
   └─> clarify.py            deterministic questions → refine loop
```

**Technology layer.** FastAPI + SSE on a DO droplet (FRA1), Docker Compose in project `colt-stack`,
DO serverless inference, Shodan Freelancer plan, Loki/Grafana observability.

### Measured defects in the current baseline (evidence, not opinion)

| # | Defect | Evidence |
|---|---|---|
| D1 | Enrichment coverage is **unenforced and unreported** | LLM may return prose for 1 of 6 findings; run still logs `status=ok`. Un-enriched findings silently render canned `TEMPLATES` text — visually identical in the deck. This is exactly your *"AI added something to the first critical and then bubkes"*. |
| D2 | One config value had **4 homes** | `_FALLBACKS`, compose `environment:`, `.env ENRICH_MODELS`, `.env ENRICH_MODEL`. Cost 3 deploys. Now mitigated by `engine_config.py` + `/api/diag`. |
| D3 | **Single-source recon** | Shodan only. Practitioner consensus is that no single scanner is sufficient. |
| D4 | Deck quality is **unmeasured** | No check that a finding has customer-specific prose vs template. |
| D5 | FP audit is **advisory only** | Last run: `flagged 6, dropped 0, refused 6` — the guardrail suppressed 100% of the auditor's signal. Correct (it prevents an empty deck) but it means the audit currently changes nothing. |

---

## 2. Problem area 1 — Fewer false positives

### Research findings (fact-checked)

Enterprise EASM vendors do **not** use binary in/out gates. They use **graded attribution
confidence**. Qualys CSAM publishes an explicit *Attribution Confidence Score*: when it is High the
asset belongs to the org; when Low, "it's not straightforward to infer if the asset belongs to your
organization", and the product **logs the rules and execution details** behind each score
([Qualys CSAM docs](https://docs.qualys.com/en/csam/latest/inventory/confidence_score.htm)).

The industry pattern is to **assign confidence by discovery source** — e.g. DNS + TLS + HTTP
fingerprint agreement = high confidence — explicitly to "reduce time wasted chasing false positives
or misattributed assets", and attribution draws on whois, certificates and DNS records together
([IONIX](https://www.ionix.io/guides/what-is-attack-surface-management/),
[DevSecOps School](https://devsecopsschool.com/blog/external-attack-surface-management/)).
Shared hosting and CDNs are named as the specific cause of obscured ownership — which is precisely
the jweiland.cloud / Colt-shared-/24 problem in your decks.

### Options

**Option 1A — Graded attribution confidence (RECOMMENDED)**
Replace the boolean `_owns_apex/_owns_host` with a score 0–100 built from independent signals:
seed apex (100) · published group structure (90) · cert CN/SAN naming the brand (85) · per-IP whois
org corroborates (80) · vendor-tenant label match (75) · brand token only (40) · shared-hoster IP
with no other signal (20). Two independent signals ≥ 40 promote to "confirmed". Findings below a
threshold ship in an **"Unconfirmed — please confirm"** appendix instead of the main deck, and every
host carries its score + the rules that produced it (Qualys' logged-rules pattern).
*Impact:* removes the binary cliff that has caused every FP incident. *Effort:* M (2–3 days).
*Risk:* low — strictly more information than today; the deck can start by using the same cut-off.

**Option 1B — Attribution as a separate reasoning step (LLM-assisted, evidence-bound)**
Give a strong model the *evidence bundle* per host (whois org, cert chain, rDNS, group structure,
DNS path) and ask for an ownership verdict + rationale, with the deterministic owned-set as a veto.
*Impact:* handles cases rules cannot (joint ventures, franchise brands like Oaklins).
*Effort:* M. *Risk:* medium — LLM ownership calls already failed once (the skon.de empty-deck
incident); must remain advisory with deterministic veto.

**Option 1C — Make the FP audit blocking, with per-finding confidence**
Today the auditor's output is discarded wholesale by the >40% guardrail. Instead, let it *lower
confidence* rather than delete, feeding Option 1A. *Impact:* recovers a signal you already pay for.
*Effort:* S. *Risk:* low.

---

## 3. Problem area 2 — More and better results (Shodan + beyond)

### Research findings (fact-checked)

- **Shodan freshness is a known weakness.** Its data "can be weeks to months old", which is the
  main driver behind users seeking alternatives
  ([scansearch](https://scansearch.net/en/articles/best-shodan-alternatives/)).
- **Censys claims the highest coverage** of active internet services, scanning all 65K ports with
  92% overall accuracy ([Censys](https://censys.com/blog/evaluating-censys-performance/)).
- **ZoomEye and FOFA "often find what Shodan missed"**, particularly in the Asian segment; **Netlas**
  positions specifically for EASM with uniform freshness across DNS, HTTP and certificates
  ([securityvision comparative review](https://www.securityvision.ru/en/blog/sravnitelnyy-obzor-shodan-zoomeye-netlas-censys-fofa-i-criminal-ip-chast-3/)).
- **Practitioner consensus: combine engines.** "Start with Shodan; for stronger certificate, host
  and service pivots, add Censys; for OSINT-heavy search add Netlas, FOFA or ZoomEye."
- **OWASP Amass** is the reference open-source pattern: DNS enumeration, brute force, reverse DNS,
  name alterations, zone transfers, scraping, certificate sources, **and APIs from Shodan /
  SecurityTrails / VirusTotal** — i.e. multi-source by design
  ([OWASP Amass](https://owasp-amass.github.io/docs/)).
- **Free Shodan capability we are not using:** `count()` **does not consume query credits**, and
  facets give value distributions cheaply. Critically, `search_cursor()` — which we use everywhere —
  **cannot use facets at all**
  ([shodan-python docs](https://shodan.readthedocs.io/en/latest/examples/query-summary.html),
  [Shodan help](https://help.shodan.io/command-line-interface/3-stats)).

### Options

**Option 2A — Facet-first reconnaissance (RECOMMENDED, do this first)**
Before any credit-consuming sweep, run free `count()` + facet queries (`org`, `asn`, `domain`,
`ssl.cert.subject.cn`, `port`) to *map* the estate and validate each candidate anchor. This tells us
how big a pivot is **before** we spend credits, kills scope blow-outs at source, and directly feeds
the confidence scoring in 1A. *Impact:* high, immediate. *Effort:* S–M. *Cost:* zero credits.

**Option 2B — Second engine behind an adapter interface (Censys or Netlas)**
Define `ScanSource` with one method (`search(query) -> [HostRecord]`) and implement Shodan + one
other. Censys for coverage/accuracy; Netlas for freshness and EASM-shaped data. Cross-source
agreement becomes another confidence signal for 1A. *Impact:* high — directly attacks "manual finds
things we don't". *Effort:* M. *Cost:* a second subscription. *Risk:* low, additive.

**Option 2C — Adopt Amass-style multi-source enumeration for names**
We already do CT + CertSpotter + a DNS wordlist. Amass adds reverse DNS sweeps, name alterations
(`netbid` → `netbid-finance`, which we *excluded* as lookalikes last run), and SecurityTrails/VT
passive DNS. *Impact:* medium-high on recall. *Effort:* M. *Risk:* medium — name alteration is a
known FP source, so it must be gated by 1A confidence rather than admitted outright.

---

## 4. Problem area 3 — Deck quality (and whether to parallelise the AI)

### Research findings (fact-checked — this one contradicts the intuition)

Multi-agent LLM results are **mixed and highly task-dependent**, not uniformly better:

- Positive: biomedical QA accuracy **+2.86% to +21.88%**; multi-agent frameworks improved clinical
  report quality over a strong single-agent baseline
  ([MDPI](https://www.mdpi.com/2079-9292/14/24/4883),
  [radiology multi-agent framework](https://arxiv.org/pdf/2505.09787)).
- Negative: one systematic evaluation found **all 28 multi-agent configurations degraded** relative
  to single-agent baselines, from **−4.4% to −35.3%**, with degradation concentrated in *sequential
  or tightly coupled* workflows due to communication overhead and coordination error
  ([Language Model Teams as Distributed Systems](https://arxiv.org/pdf/2603.12229)).
- Cost: multi-agent systems consume **4–220× more tokens** than single-agent equivalents.

**Interpretation for us.** Your instinct — *"one takes X findings, another takes X findings"* — is
the **map-reduce / embarrassingly-parallel** shape, which is the case where the literature is
*positive*. It is not the "agents debate each other" shape, which is where degradation is reported.
Findings are independent of one another, so there is no coordination cost. This is the right call.

**But parallelism is not the actual cause of the bad decks.** D1 is: nothing enforces or measures
that every finding gets customer-specific prose, so a model that rewrites one finding and stops is
recorded as a success, and the deck silently renders template text for the rest.

### Options

**Option 3A — Per-finding map-reduce enrichment with a coverage contract (RECOMMENDED)**
Shard findings into batches of 2–3, issue N concurrent calls (`asyncio` + the existing chain), then
reduce into one JSON. Enforce a hard contract: **every finding id must come back rewritten**, else
retry just the missing shard. Emit `enrich_coverage = rewritten/total` to Loki and **fail the deck
build below a threshold**. *Impact:* fixes the "only the first critical is real" defect AND cuts
wall-clock (parallel, not serial). *Effort:* M. *Risk:* low — batches are independent; per-shard
retry is cheaper than a whole-prompt retry.

**Option 3B — Specialist roles per deck**
Different models for different artefacts: an analytical model for C-BIQ (numbers, FAIR), a
narrative model for GEOPOL, a concise one for Findings. *Impact:* medium. *Effort:* M.
*Risk:* medium — four chains to keep measured; only worth doing after 3A proves the harness.

**Option 3C — Deck-quality gate in CI (cheap, do alongside 3A)**
Extend `ship.py` to render a deck from a fixture and assert: no finding renders template-only prose;
no text box overflows its shape; no string exceeds its box's character budget; every severity band
present. The 4,000-character footer that produced "letters on top of each other" would have been
caught mechanically. *Impact:* medium-high on trust. *Effort:* S. *Risk:* none.

---

## 5. Recommended target architecture (TOGAF Phase E — transition)

```
                 ┌──────────────────── ATTRIBUTION SERVICE ────────────────────┐
 seed ──────────>│ signals: group structure · cert CN/SAN · per-IP whois org   │
                 │          vendor tenant · sibling TLD · brand token          │
                 │ output : confidence 0-100 + rule log per asset              │──┐
                 └─────────────────────────────────────────────────────────────┘  │
                                                                                   v
      ┌──────── DISCOVERY (multi-source, adapter interface) ────────┐      ┌──────────────┐
      │ Shodan (facet-first, credit-free mapping)                   │      │ confidence   │
      │ Censys | Netlas   (2nd engine)                              │─────>│ >= threshold │
      │ CT · CertSpotter · DNS probe · Amass-style alterations      │      │ else appendix│
      └─────────────────────────────────────────────────────────────┘      └──────────────┘
                                          │
                                          v
      ┌──────── ENRICHMENT (map-reduce, N parallel shards) ─────────┐
      │ shard 1..N ─> chain ─> reduce ─> COVERAGE CONTRACT enforced │
      └─────────────────────────────────────────────────────────────┘
                                          │
                                          v
      ┌──────── RENDER (deterministic) + QUALITY GATE in CI ────────┐
      └─────────────────────────────────────────────────────────────┘
```

### Architecture decisions requested

| ADR | Decision | Recommendation |
|---|---|---|
| **ADR-01** | Attribution model | Adopt **1A graded confidence** + **1C** (audit lowers confidence, never deletes) |
| **ADR-02** | Discovery sources | Adopt **2A facet-first now** (zero cost); decide **2B second engine** (Censys *or* Netlas) as a budget item |
| **ADR-03** | Enrichment topology | Adopt **3A map-reduce + coverage contract** and **3C deck-quality CI gate**; defer 3B |

### Sequencing (each step independently shippable and measurable)

1. **3C deck-quality gate** — smallest, stops visual regressions immediately.
2. **3A map-reduce + coverage** — fixes the "bubkes after the first finding" defect; measurable as `enrich_coverage`.
3. **2A facet-first** — free, improves both recall and scope safety.
4. **1A + 1C confidence scoring** — the structural fix for false positives.
5. **2B second engine** — after 1A exists, so cross-source agreement has somewhere to go.

### How we will know it worked (the metric that has been missing)

Extend `test_parity.py` into a scored harness across **multiple** customers (angermann, skon,
rightmart, bibeltv — all of which we hold real exports for) and publish per-run:

- **Precision** = confirmed-owned hosts in deck ÷ hosts in deck
- **Recall** = hosts in deck ÷ hosts your manual Shodan work proves
- **Enrichment coverage** = findings with customer-specific prose ÷ total findings
- **Deck integrity** = overflow/overlap violations (target: 0)

Any change that does not move one of these is, by definition, full gas in neutral.

---

## 6. What is already fixed as of this commit

- `ship.py::ssh()` had **no timeout** — the cause of the hang you just hit (CLAUDE.md mandates
  timeouts on every ssh; this helper never received it). Now 180s hard timeout, fails legibly.
- `SyntaxWarning: invalid escape sequence '\?'` → `sed -E` with a proper character class.
- `engine_config.py` + `GET /api/diag` — resolved config with provenance, so config archaeology
  stops. It correctly identified `ENRICH_MODEL` (legacy) as the reason V4 Flash never ran.
- Deck footer no longer interpolates 144 domains into a 3.1-inch box.

**Not yet built:** the Demo / "Trojan Empire" section.

---

## Sources

- [Qualys CSAM — Attribution Confidence Score](https://docs.qualys.com/en/csam/latest/inventory/confidence_score.htm)
- [IONIX — Attack Surface Management 101](https://www.ionix.io/guides/what-is-attack-surface-management/)
- [DevSecOps School — What is EASM (2026)](https://devsecopsschool.com/blog/external-attack-surface-management/)
- [CyCognito — ASM tools 2026](https://www.cycognito.com/learn/attack-surface-management/attack-surface-management-tools/)
- [Censys — Evaluating Censys' Performance](https://censys.com/blog/evaluating-censys-performance/)
- [securityvision — Comparative review: Shodan, ZoomEye, Netlas, Censys, FOFA, Criminal IP](https://www.securityvision.ru/en/blog/sravnitelnyy-obzor-shodan-zoomeye-netlas-censys-fofa-i-criminal-ip-chast-3/)
- [scansearch — Best Shodan alternatives 2026](https://scansearch.net/en/articles/best-shodan-alternatives/)
- [DEV — Top 5 internet asset search engines](https://dev.to/blake_gerry_e54a96df65161/top-5-internet-asset-search-engines-shodan-zoomeye-censys-netlas-and-fofa-165f)
- [OWASP Amass documentation](https://owasp-amass.github.io/docs/)
- [shodan-python — query summary via facets](https://shodan.readthedocs.io/en/latest/examples/query-summary.html)
- [Shodan Help — generating statistics](https://help.shodan.io/command-line-interface/3-stats)
- [Language Model Teams as Distributed Systems (arXiv)](https://arxiv.org/pdf/2603.12229)
- [Multi-Agent Coordination vs RAG — comparative evaluation (MDPI)](https://www.mdpi.com/2079-9292/14/24/4883)
- [Multimodal Multi-Agent Framework for Radiology Report Generation (arXiv)](https://arxiv.org/pdf/2505.09787)
- [Multi-Agent LLM Orchestration for Incident Response (arXiv)](https://arxiv.org/pdf/2511.15755)
