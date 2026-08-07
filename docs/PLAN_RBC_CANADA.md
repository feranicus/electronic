# Plan — RBC follow-up, Canadian compliance, and the website "who we are"

**Source:** the 6 Aug 2026 demo call with Mordechai Rabinovich (Senior Network Security Engineer,
RBC) and Sam Rabin (reseller), 55 minutes, plus the two S4biz capability decks.
**Written:** 7 Aug 2026. **Owner:** Evgeny "Jev" Vainshtein.

Everything below is traceable to something that was actually said on the call or is in the decks.
Where a line is my inference rather than a request, it says so. Timestamps are from the transcript.

---

## 0. What the call actually established

Mordechai is **not** a buyer of the whole platform, and he said so plainly. He is a network
security engineer whose team owns **design** of the network, not operations, and RBC's security
organisation is ~2,000 people split across teams that each own one slice. His words (32:11 →
33:50), paraphrased: *"in a company like RBC I have no visibility into most of what you're
showing — another team entirely handles that. What could interest **me** is network exposure.
Translating it into financial exposure interests a different team. Compliance is a third."*

He then told us exactly how a tool gets in (35:25 → 36:03): a central group runs approved tooling
to produce a **recurring compliance report**; every other team must then report remediation against
it, and there is an audit. Compliance is mandatory, not voluntary.

And his closing ask (52:10 → 53:04): can their **Grafana / observability** reach the platform over
an **API**, and can we push critical findings back into their monitoring.

Sam's contribution is commercial and it is a hard constraint (49:49 → 50:26): whatever is shown
must be **fully white-label**. His reasoning is blunt and correct — a buyer who looks up a
four-person Estonian OÜ stops the conversation regardless of how good the product is.

**The single most repeated word in the meeting was "modules."** Both of them, independently, and I
committed to it at 51:58. That is the centre of this plan.

### The wedge

Sell **network exposure** to Mordechai's team first. It is the one thing he said he can own, act
on and take to his director (a Director of Network Engineering, described as experienced and open,
with an AI mandate). Once we are on-boarded through procurement, the other modules are an
expansion sale to teams next door — his words, 46:11.

---

## 1. Work items, in the order I propose

| # | Item | Why | Size |
|---|---|---|---|
| 1 | **Canadian compliance regimes** | Explicit RBC ask; I committed to weeks | L |
| 2 | **Contact + Impressum: who we are** | Directly asked; credibility gap Sam named | S |
| 3 | **Modularisation** (product + licensing) | Asked by both, repeatedly | L |
| 4 | **Multi-entity scoping** | "RBC is not one company" (32:11) | M |
| 5 | **Scheduled / recurring assessments + change diff** | Their actual compliance process (35:25) | M |
| 6 | **Public REST API + observability push** | Mordechai's closing ask (52:10) | M |
| 7 | **White-label mode** | Sam, emphatic (49:49) | M |
| 8 | **Credit packs alongside subscription** | Both models were discussed (20:52) | S |

Items 3–8 are independent of each other and can be reordered freely. Items 1 and 2 are the ones
with a named external audience waiting.

---

## 2. Canadian compliance — the detail

### What exists today
`compliance_enrich.py` grades a company against exactly three EU regimes
(`_ORDER = ["nis2", "cra", "aiact"]`) from one reference document,
`scripts/compliance/EU_COMPLIANCE_REFERENCE.md`. The findings deck already picks a **framework set
by jurisdiction** (`build_findings_deck.js`, `d.target.country` → UAE / GB / CH / EU / default), so
the country signal is already resolved by recon and plumbed through. Canada currently falls to the
generic ISO 27001 / NIST CSF default.

### What Canada needs
A federally regulated bank is the hardest case in the country, which is convenient — build for RBC
and everything smaller is a subset.

- **OSFI B-13** — Technology and Cyber Risk Management. The centre of gravity for an FRFI.
- **OSFI E-21** — Operational Risk and Resilience Management.
- **OSFI B-10** — Third-Party Risk Management.
- **OSFI Technology and Cyber Security Incident Reporting** advisory — the reporting clock.
- **PIPEDA** — federal privacy, plus mandatory breach-of-safeguards reporting to the OPC.
- **Bill C-26 / CCSPA** — critical cyber systems; **status must be verified before it ships.**
- **CCCS (Canadian Centre for Cyber Security)** — ITSG-33, Baseline Controls, Top 10 IT Security
  Actions. Not law, but it is the control language Canadian regulators and auditors speak.
- **Quebec Law 25** — provincial privacy, because RBC operates in Quebec.

### Hard rules this work inherits
These are already standing rules in this repo and they bind here:

1. **No invented identifiers.** Every article, deadline and penalty is quoted from the primary text
   with a retrieval date, exactly as `EU_COMPLIANCE_REFERENCE.md` does. Research happens **first**,
   from primary sources, before a line of code.
2. **Deterministic fallback holds the fixed facts.** Obligations, deadlines and penalty maxima are
   company-independent, so the decks stay correct with no model available; only applicability reads
   "requires confirmation".
3. **Never translate an enum.** Regime keys (`osfi_b13`, `pipeda`, …) are lookup keys.
4. **Jurisdiction drives the regime set.** `CA` must select the Canadian set the way `AE` selects
   the UAE set — one map, not a second code path.

### Files that change
`scripts/compliance/CA_COMPLIANCE_REFERENCE.md` (new) · `compliance_enrich.py` (regime registry
becomes jurisdiction-keyed instead of a flat `_ORDER`) · `build_compliance_deck.js` (labels) ·
`compliance_clarify.py` (province + FRFI status questions) · `build_findings_deck.js` (CA framework
set) · `ship.py` (gate).

### The honest caveat
It is **not legal advice**, every deck footer says so, and national/provincial rules move. The
reference document carries its compilation date and a re-check instruction, same as the EU one.

---

## 3. Contact and Impressum — who we are

Both pages are thin today. The decks contain the full, checkable answer, and Sam's objection is
precisely that a buyer cannot currently see it.

Four registrations, two continents, one principal:

| Entity | Where | Role | Official number |
|---|---|---|---|
| Stars4business OÜ | Estonia (Tallinn) | EU hub / consultancy | VAT EE102156878 |
| S4biz UG (haftungsbeschränkt) | Germany (Pinneberg) | Software development | USt-IdNr DE361822318 |
| S4BIZ Unipessoal Lda | Portugal (Lisboa) | Iberia operations | NIF 518007596 |
| CyberGod LLC | Delaware, USA (Lewes) | Cyber & cloud / US arm | EIN on file · HBS agent |

Plus: EU/EEA data residency by design, EUR/USD billing, and the principal-architect bio (Cognyte ·
Elbit/Cyberbit · Intellexa · AWS · Red Hat · Canonical · NetApp · Huawei · Colt · Cogent).

**One thing to fix while we are in there.** `/privacy` currently names a natural person in
Friedberg as the operator, while the contracts and these decks name Stars4business OÜ. Those two
cannot both be right, and a privacy notice naming the wrong controller is the one page a regulator
reads first. This needs a decision from you, not from me — see §9.

All copy goes through `legal.jsx` / `i18n.jsx` in **six languages**; nothing is hardcoded in a page.

---

## 4. Modularisation

Three sellable modules, matching the three teams Mordechai described:

| Module | Buyer at RBC | Contains |
|---|---|---|
| **EXPOSURE** | Network security engineering (Mordechai) | Recon, findings deck, evidence, animated report |
| **COMPLIANCE** | Compliance / audit | Regime grading, per-finding regime mapping, deadlines |
| **RISK** | Risk + CFO/CISO | C-BIQ quantification, GEOPOL |

Implementation is a per-account **entitlement set** checked in one place server-side, driving what
the cabinet shows and which artifacts the engine builds. It must not become an `if` scattered
through the UI — one gate, same doctrine as `colt_auth.email_allowed()`.

Deliberately **not** in scope here: BAS / digital twin (26:18). It is a real product in the S4biz
deck, it is the natural upsell after EXPOSURE lands, and it is far too large to bundle into this
plan. Say so honestly rather than half-building it.

---

## 5. Multi-entity scoping

"RBC is not one company" (32:11), and he flagged during the demo that several findings looked like
**RBC US / City National** rather than the Canadian bank (18:28) — one he thought belonged to a
tenant with its own IT. That is a scoping question with commercial consequences, and it is exactly
what the existing ownership gate and clarify loop are for.

Add: an **entity** under an account, each with its own seed, history and artifacts; a roll-up view;
and per-entity credit consumption.

---

## 6. Scheduled assessments + change diff

Their process needs a **weekly** run, not a one-off. Required:

- a schedule per entity (weekly / monthly);
- a **diff against the previous run** — new, resolved, unchanged findings. This is the actual
  compliance artifact: "what changed, and did anyone fix what we raised";
- remediation state per finding, carried across runs so a team can be shown to have closed it;
- email + Telegram on the delta, not on every run.

The diff is the highest-value item in this whole plan for a recurring-revenue argument, because a
one-off report is a project and a weekly delta is a subscription.

---

## 7. API + observability

- REST API mirroring the cabinet: start, status, artifacts, findings JSON. Scoped API keys per
  account/entity, never the session cookie.
- **Push** direction: webhook / JSON-lines for critical findings so their Grafana, Elastic, Splunk
  or Datadog can ingest without polling.
- Documented, versioned, rate-limited. This is the integration Mordechai said he could sell
  internally himself, because he already owns the observability relationship (53:04).

---

## 8. White-label

Per-partner branding: wordmark, colours, footer, deck cover and the animated report. Sam's point is
that this is a **deal-blocker**, not a nicety. The `COLT` → `MANAGED` tag-label precedent already
shows the pattern: rebrand at render time, never rename the enum.

---

## 9. Decisions I need from you

1. **Order.** Which of §1's eight items first, after Canada and the website pages?
2. **Privacy-page controller.** Which entity is the data controller for cybergod.ai —
   Stars4business OÜ, S4biz UG, or the natural person currently named? This changes /privacy,
   /impressum and the DPA, and I will not guess at it.
3. **RBC access.** `mordechai.rabinovich@rbc.com` is already whitelisted at 5 assessments. Raise it,
   or leave it as an evaluation cap?

---

## 10. What is already done

- RBC + NVIS evaluation accounts whitelisted, 5-assessment quota, enforced on both web and Telegram.
- Enterprise ASN discovery fixed — RBC announces ≥12 ASNs and the engine found 2 before the
  RIPEstat/`searchcomplete` change; it now finds 7 and asks the operator for the rest. That gap was
  found *because of* this account.
- Jurisdiction-driven framework selection on the findings deck (the mechanism Canada plugs into).
