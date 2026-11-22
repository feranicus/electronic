# The channel pipeline — 22 November 2026

## What was asked for, and what the transcript changed

> additional functionality called Pipeline that we had in our www.jobhuntwow.com project just for
> users that are part of S4biz and inside this pipeline there will be a Kanban board for Sales
> funnel like in Pipedrive but for Channel Sales (Introduction, Demo stage, NDA, Master Partner
> Agreement, POC/POV, etc...) this needs to be aligned in general with our Sales Life Cycle …
> also this pipeline functionality needs to have some sort of integration with Gmail

The 20 November call between Dima and Jev was uploaded with the kit, and it is what stopped me
inventing the columns. At 50:12 Dima says:

> That's the process map that Assad proposed. You still have that process map, right? I think we
> should organize it according to the stages.

That document exists: `Herkos_Commercial_Process_Map_v0.1_DRAFT.docx`, HRK-COM-PRC-001, 2 October
2026, author Assad Kondakji. Every stage name, gate and exit criterion in `pipeline.py` is verbatim
from it, and I read it myself rather than trusting the search that found it.

**The map has three tracks, not one funnel**, and that is the part a flat column list would have
destroyed. Herkos H0–H9 and Perseus P0–P10 are direct-customer processes; the partner track R1–R6
is the channel one the operator described, and his five named stages are its stages almost exactly.
R6 says a partner "runs H0–H9 / P0–P10 with its own customers at its own prices" — so these are
parallel processes that share a board, not steps of one. Collapsing them would have put "Pilot
readiness" beside "MPA + onboarding" as though a card could move between them.

The board therefore shows **one track at a time**, partner by default. `canon_stage()` is
track-aware: `mpa` is a stage of the partner track and nothing else, and accepting it on a Perseus
deal would file the card in a column that board never renders, where it would simply vanish.

## What was reused, and what deliberately was not

The jobhuntwow tracker is 1,235 lines and more than half is job-application domain —
`jd_fingerprint`, `ats_of`, `record_tailored`, resume files, employer derivation from a posting URL.
Copying it wholesale would have imported a domain model that does not fit and would rot in place,
which is how a "reused" module becomes two modules nobody dares touch.

What came across is the half that was hard and is domain-free:

| from jobhuntwow | how |
|---|---|
| `mailmatch.py` → `dealmatch.py` | the scoring engine, the tie refusal, the self-test discipline; nouns changed, ATS signals dropped, contact-address signal added |
| `gmail_read.py` | `_http`, `_header`, `_body_text`, `parse_message` **verbatim** (76 lines) — a payload can be an int, HTML-only senders must not be dropped |
| `Pipeline.jsx` | native HTML5 drag-and-drop, the optimistic move that reverts with a reason, no one-click terminal link |
| stage machinery | `canon_stage` with a legacy remap, because a renamed stage once made every card in the old column invisible |

## The matcher refuses to guess, and that is the feature

Every signal is a fact about the message compared to a fact about the deal — sender domain, named
contact, company name, deal reference, title words, time — each weighted by how hard it is to be
wrong about. The evidence comes back so the card can show **why** it was filed there.

No model is consulted. There are four in this estate and none of them is asked here: there is
nothing they can add that counting cannot do, and filing Paratus's pricing question under the wrong
Paratus deal makes the board lie quietly, in the one artefact two people use to agree what is
happening. A tie leaves the message **unfiled with its reason**, and the unfiled queue is kept
rather than dropped — "we saw it and could not place it" is work for a person, and dropping it
would make the same message look like new activity on the next sweep.

**A label never moves a card.** `classify()` tags a message `nda`, `agreement`, `loi`, `poc`. The
gates in the process map are signature events: an email saying "NDA" is not an NDA that was signed,
and a board that advanced itself on vocabulary would be fiction within a week. Asserted twice — in
the matcher's own source, and through a sweep that leaves the card where it was.

## Gmail, and the one human step

cybergod.ai already holds a Workspace service account with domain-wide delegation for
`gmail.send` — that is how the sign-in codes go out. Reading is the same mechanism with one more
scope, so there is no second auth system, no OAuth consent screen, no refresh token to rotate.

The irreducible step is a domain admin's, in the console:

> Security → Access and data control → API controls → Domain-wide delegation → the **existing**
> client id → add `https://www.googleapis.com/auth/gmail.readonly`

Until that is done the board says so, in words, with the setting names. `gmail.modify` was not
requested: it would let this code label, archive and delete mail in a real person's mailbox, and a
bug in a correlation engine must not be able to touch a message.

`PIPELINE_MAILBOXES` is a list because the point is that Dima's mail reaches the board as well as
the shared one. Each address is impersonated separately, so one mailbox being refused does not
silence the others, and the mailbox is recorded on the row.

The sweep is re-runnable by construction: it reads a **window**, not a cursor, and `msg_id` is the
primary key of `deal_mail`. A crash halfway costs nothing and a second run files nothing twice.

## "Just for users that are part of S4biz" is a permission

Not a domain check. `pipeline.view`, `pipeline.edit` and `pipeline.admin` already existed in
`roles.py`; the router takes them as injected dependencies, so the policy has one home and the
module can be tested without an auth stack. A plain `user` on s4biz.io is refused; a `sales_rep`
is not. Letting a partner's sales person in later is a role change, not a code change.

Sweeping a mailbox is `pipeline.admin`, deliberately: reading somebody's mail is a different act
from moving a card.

All nine routes refuse an anonymous caller — measured by `authz_audit.py --local`, not asserted.

## What was proved

Twelve mutations, twelve caught. One was MISSED first time and it is the instructive one: deleting
the matcher's tie-refusal branch left all 26 tests green, because the only thing asserting it was
`dealmatch`'s own self-test, which pytest never ran — a check that cannot run is not a check
(class 2/3). Fixed twice over: a request-path test with two deals for the same company at the same
domain, and both module self-tests wired into the suite.

| mutation | caught by |
|---|---|
| a stage from another track is accepted | the track-awareness test |
| the first stage is hardcoded instead of derived | two tests |
| changing track leaves the card in a column that does not exist | the re-home test |
| the sweep considers closed deals | the closed-deal test |
| a message that matched nothing is dropped | two tests |
| deleting a deal destroys its mail | the unfile test |
| the matcher stops refusing a tie | **missed, then the tie test** |
| a refused move loses its reason | two tests |
| the board is gated on a domain instead of the verb | the wiring test |
| the sweep route only needs `pipeline.edit` | the verb test |
| the mail status stops reaching the board | the "says when it is off" test |

`ship.py` now prints the stage count per track with the document id, so a change to the columns is
visible in the ship log rather than discovered on the board.

## What is not built

- **Deal documents.** Dima asked to "catch the balls that are falling, the NDAs … organize the
  documents, create link for Paratus". The map's §6 release matrix is the right model for it —
  per-document earliest release stage, five documents marked "Never" to a customer — and it is a
  feature in its own right, not a field on a card.
- **Vertical news on the card** (Jev at 54:00). Needs the threat-intel feed pointed at a customer
  vertical; it is a sensible second pass once the board has real deals on it.
- **Tier, territory and volumes** from R4/R5. Stored as notes today.
