# Deal registration — the design, and where every number came from

23 November 2026. Requested by the operator: a fourth board beside Partner / Herkos / Perseus where
a reseller registers a large deal, asks for discount approval and dedicated support, and where two
resellers cannot register the same deal — with the four models checking whether a second
registration really is a duplicate.

## First: nobody has written this down, and that is recorded rather than papered over

`pipeline.py` carries the three tracks **verbatim** from
`Herkos_Commercial_Process_Map_v0.1_DRAFT.docx`, because a process the business already wrote down
is not mine to invent (class 59). That document says nothing about deal registration. **Measured
23 Nov 2026: no file in this repository contains the phrase.**

So everything below is the **channel-sales market standard**, researched from vendors' own
programme guides, not S4biz policy. Every number in `dealreg.py` is a default with a source named
here. When Assad writes the real programme guide, `dealreg.py` is where his numbers land and these
defaults are replaced — not argued with.

The research sourcing is worth stating because it shapes confidence: deal-registration mechanics
are the most consistently *unpublished* artefact in enterprise channel programmes. The signed
partner agreement incorporates a "Program Guide" by reference and keeps it behind portal login,
which lets the vendor change discounts and windows unilaterally. CrowdStrike's public programme
agreement contains the string "deal registration" exactly once, as an exclusion. Only five vendors
publish a complete, implementable specification: **AWS, Microsoft, Veeam, Barracuda, Nutanix**. The
richest sources are vendor-authored guides rehosted by distributors (TD SYNNEX, Infinigate, ALSO,
Ingram, Exclusive Networks).

Three aggregator sites that look authoritative are not and were discarded: xamplify.com,
indyrct.com, vendorradar.app — they contradict vendors' own published data and carry no citations.

## The four rules that are NOT defaults

These are doctrine. Each is enforced by `tests/test_dealreg.py`, so changing one means arguing with
a test rather than editing a line.

### 1. A registration is an INCENTIVE, never a PROHIBITION

Losing a registration costs the partner the discount, the protection and the dedicated deal
support. It never costs them the right to quote that customer, to be supplied, or to be priced.
`refused_protection()` is the only thing the module can do to a second partner, and its message
says what they keep in the same breath as what they lost.

This is the market standard — Nutanix: the second partner "may still obtain a standard-price
quote"; Barracuda and Proofpoint operate the same way — **and it is the only defensible position
under EU competition law.**

A programme drafted *or operated* so that a non-registering reseller is refused supply, refused a
quote or refused any price for "their" account stops being a supplier's pricing decision and
becomes **customer allocation** (Art. 4(b)/(d) VBER). The sharp edge for a portal specifically: a
registered deal is almost by definition a situation where another reseller may receive an
**unsolicited** enquiry from that customer. Blocking them from answering restricts a **passive**
sale, which is hardcore even inside a properly constituted exclusive distribution system — and
hardcore removes the block exemption for the **whole agreement**, regardless of market share.

Legal-risk ranking from the research, lowest first: (1) incentive-only, non-exclusive,
opportunity-scoped — what is built here; (2) exclusive distribution properly constituted under
Art. 4(b), max five distributors, active sales only, both 30% thresholds; (3) account-scoped
blocking operated as a prohibition — the highest risk and the one to stay away from.

**Not legal advice, and flagged honestly:** no decision, Commission guidance passage or law-firm
commentary addressing deal registration *by name* under VBER was found. The above applies general
vertical-restraints doctrine to the mechanism. Counsel should confirm before this shapes contract
terms. Note also that Regulation (EU) 2022/720 is in force until **31 May 2034** — the safe harbour
being designed against has a known expiry.

### 2. Opportunity-scoped, never account-scoped

Protection attaches to one opportunity at one customer, not to the customer. Zscaler states it
hardest: "Deal Registration is granted by **opportunity, not by account**." Cisco, Barracuda, Veeam
and Fortinet all say the same; Veeam from the other direction: "Additional orders by the same
customer who is not known to be part of a registered deal will be regarded as a separate deal."

Account-scoped is the minority model (ZINFI's product, Lenovo ISG US). It manufactures a false
duplicate every time a customer runs two unrelated projects, and it is the shape that most
resembles allocation. For a vendor with two product lines and a renewal motion it is the wrong
default twice over.

### 3. Deterministic code decides; the models are a signal

`duplicate_of()` computes the verdict that costs a partner money, from the match key alone. No
model is consulted and none can be. `dealreg_panel.py` may do exactly two things: **raise a flag**
for a human on a near-miss the key cannot see, and **write the explanation** a partner reads.

The boundary erodes precisely because the model is right often enough that wiring it to the verdict
starts to feel like an improvement — and then a partner loses a deal to a sentence nobody can
audit. This is the third place in the estate that has needed the rule, after the engine's FP
auditor ("an audit is a SIGNAL, not an authority") and `perseus/vet.py` (models propose, code
decides). `apply()` writes **one column** that no decision path reads, asserted by test.

### 4. A duplicate is a FORK, not a failure

Nutanix publishes two distinct denial codes and the second is the one that matters: *"same end
user, **different deal**, but insufficient information to distinguish it."* That is a request to
the partner, not a refusal. It goes to `returned` — fixable — never to `rejected` — terminal.
Conflating the two inflates the rejection rate and reads as arbitrary. Microsoft ("Action
required"), AWS ("Action Required") and Oracle ("Returned") all keep the states separate.

## The match key

`registrable domain` + `country` + `product line`, inside an active protection window.

**Domain, not the typed name.** Every source that addresses it agrees. ZINFI: a partner submitting
at acme.com triggers a duplicate "regardless of how the company name was entered". xAmplify names
the failure mode: "Deduplicating on company name alone lets duplicates and conflicts slip through."
"Müller GmbH", "Mueller GmbH" and "MUELLER" are one customer and three strings.

`_apex()` is the engine's `psl.registrable()` — the same eTLD+1 home. "The last two labels" turns
`budget.gov.ru` into `gov.ru`, which here would let the first ministry to register hold protection
against the entire government. The engine already paid for that one.

An **unparseable domain never matches anything**: absence of evidence is never a finding, and
matching two blank keys would hand the first partner with a broken domain protection over every
other broken one.

**Not adopted, and worth revisiting:** no source recommends VAT-ID as the primary key, but for an
EU-facing vendor a VIES-validatable VAT-ID is a materially better anchor than a domain — it
resolves the subsidiary problem Veeam itself names ("the parent company may have subsidiaries under
different names"). That is the single best upgrade available to this design, and it is a design
choice of ours, not a market standard.

## The numbers, each with its source

| Term | Value | Source |
|---|---|---|
| Protection window | **90 days** | the modal window: Fortinet, Check Point, Sophos, Barracuda, SonicWall, Dell, Lenovo EMEA |
| Clock starts | **approval** | Check Point, Sophos, Veeam, Rapid7, Dell (current terms). Dell documents its own drift from submission → approval; Barracuda still runs from submission |
| Extension | **+90 days**, partner-initiated | Dell's model: in-tool |
| Total cap | **270 days** (90 + 2×90) | Dell |
| Reminders | **30 / 15 / 1 days** | Barracuda's published cadence |
| Decision target | **5 business days** | Sophos ("in der Regel", a target not an SLA) and Microsoft, the only vendor publishing a symmetric obligation on itself |
| Minimum deal size | **none** | the direction of travel, not a gap: Check Point abolished its $20K minimum, Sophos removed **all** minimums globally in Jan 2026, Veeam/Rapid7/Tenable publish none |

**The honest finding on SLAs:** nine of ten security vendors publish none anywhere. Every "typical
24–48 hours" figure traces to a PRM vendor's blog with no methodology. Five days is a target *we*
choose, not a market norm — which is why `config()` reports it with provenance rather than printing
it as fact.

**A trap that cost the research real time, recorded so nobody repeats it:** "X days" in channel
material is almost never the protection period. SentinelOne's two "90 days" are *submission*
windows; Proofpoint's "21 days" means two opposite things on two pages; Arctic Wolf's 30/60 are
contract auto-renewal notice periods; Cisco's "30 days" is *quote* validity; WatchGuard's "90 days"
is a tier status-match. Verify the noun before copying the number.

## Discounts: deliberately not implemented yet

The research found four incompatible architectures (extra points off list; a boolean gate on
separately governed incentives; two instruments over one registration; relative uplift). Published
grids range from Check Point's 12% basic + 22/18/20 specials, to Sophos's +6 points at every tier,
to Barracuda's 35–40% registered versus 10% standard.

Picking one is a commercial decision, not an engineering one, so `dealreg.py` records the
*protection* and leaves the number to the programme guide. One thing is encoded: **the benefit must
be a buy-side discount, never an approved end-customer price.** Art. 4(a) VBER makes a recommended
price into a fixed price when compliance is procured *by incentives* — conditioning approval or the
discount on the reseller quoting a particular price is RPM dressed as a registration rule, and it is
hardcore. Veeam's wording is the defensible structure: an additional percentage "off the current
SRP list price", with what the reseller then charges remaining the reseller's own decision.

## RBAC, which is what the operator asked for

Four verbs, because "register", "see your own", "see everyone's" and "decide" are four different
powers:

| Role | submit | view.own | view.all | decide |
|---|---|---|---|---|
| admin | ✓ | ✓ | ✓ | ✓ |
| s4biz_power | ✓ | ✓ | ✓ | ✓ |
| reseller_admin | ✓ | ✓ | — | — |
| company_admin | ✓ | ✓ | — | — |
| sales_rep | ✓ | ✓ | — | — |
| presales, user | — | — | — | — |

Every S4biz account sees every registration, as asked — you cannot adjudicate "who got here first"
from a partial view, and an S4biz seller must know an account is spoken for before promising it to
somebody else.

**`dealreg.view.all` is deliberately withheld from partners**, and not only on need-to-know. A
registration names an end customer, the expected value, the close date and the incumbent
competitor, submitted by a reseller who competes with the other resellers. Granting it to a partner
would make *us* the channel through which one reseller reads a rival's pipeline — which is the
dual-distribution information-exchange exposure (VBER Art. 2(5)) in its most literal form. The
single-registration route answers **404, not 403**, on someone else's id, because a 403 confirms
the id exists and an id is itself a fact about a rival's pipeline.

## Anti-abuse carried over from the research

Immutability of the match fields after submit (Nutanix, Microsoft CPOR, AWS). No deletion —
Microsoft: "Opportunities can't be deleted… to maintain data integrity"; rejected registrations stay
for audit. Expiry by timer, never by someone remembering. Extension capped. Protection only from an
**approved** registration, so the race is won by qualifying rather than by typing first.

Not yet built, and named so it is not mistaken for done: anti-splitting detection (AWS and Dell both
forbid splitting one engagement into several); the anti-backfill tripwire (Microsoft's 72-hour rule);
proof-of-engagement as a tie-breaker (Veeam awards a true conflict to whoever has "proof of active
selling", then to whoever books the PO first); and the duplicate-rate metric ZINFI targets at <5%,
"higher rates indicate territory or account definition problems" — the one genuinely useful
benchmark because the portal can compute it.

## What is built

`webapp/backend/app/dealreg.py` — store, states, match key, windows, RBAC scoping, router.
`webapp/backend/app/dealreg_panel.py` — the four-vendor second opinion, flag-and-explain only.
`roles.py` — the four permissions.
`tests/test_dealreg.py` — 28 tests. **Fourteen mutations, fourteen caught**, including reverting to
account-scoped matching, letting a submitted registration protect, turning the refusal into a
prohibition, letting one model raise a flag, and letting the panel mark a duplicate itself.

One mutation was **missed first time**: running the clock from submission instead of approval. The
test approved a registration created milliseconds earlier, so the two clocks were the same number
to within its tolerance — a fixture that does not reproduce the condition under test is a test of
the fixture (class 12). Fixed by ageing the submission thirty days, after which the two answers
differ by thirty days.

## Sources

Vendor programme guides and documentation consulted: Sophos (Partner-Programm-Guide, 16 Apr 2026;
Globale Deal-Registration-Richtlinien), Veeam (DR Program Guide AMER 2025), Barracuda (Partner
Success Program Guide, 1 Jun 2026), Check Point (Partner Program Guide 2024; Quick Reference 2025),
AWS (Partner Central API reference: `CreateOpportunity`, `LifeCycle`), Microsoft (Partner Center:
register deals; customer-association issues), Zscaler (Summit FY24 guide), Nutanix (partner FAQ),
Fortinet, Dell, Lenovo, Rapid7, Proofpoint, Trend Micro, Cisco, HPE. German statutory text (GWB,
UWG, BGB) retrieved verbatim from gesetze-im-internet.de; **EU-law content could not be retrieved**
(EUR-Lex returns ROBOTS_DISALLOWED), so article numbers and substance are stated from knowledge and
flagged as unverified quotations — verify against the Official Journal before publication.
