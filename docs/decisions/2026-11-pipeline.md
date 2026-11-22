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

## Which Google integration, and why this one (asked 22 Nov)

Four options were on the table. The one that is built is **Google Cloud: a service account with
domain-wide delegation, calling the Gmail REST API**.

**It is already the mechanism this product uses.** `notify.email()` has been sending the one-time
sign-in codes through that service account since the login gate was written -
`colt-bots@colt-bots.iam.gserviceaccount.com`, project `colt-bots`, client id
`105211423907937536502`, impersonating `feranicus@s4biz.io` with scope `gmail.send`. Reading is the
same mechanism with one more scope. No second auth system, no consent screen, no refresh token to
store and rotate, no browser on a server that has none.

**Apps Script** was the obvious alternative and is the wrong shape here. It runs inside Workspace
as a user, so it would have to call OUT to cybergod.ai - which needs an API credential anyway, so
the auth problem does not go away, it moves. Worse, the script lives in Google's editor and not in
this repo, which breaks operating principle 2 (GitHub is the single source of truth) and principle
1 (no console-configured steps that a script could own). It is also per-user: Dima would install
his own copy, and it would break silently the day he changed something nobody else can see.

**A Chrome extension** does not read mail server-side at all, so it cannot keep the board right
while nobody is looking - which is the entire point. What it would buy, and nothing else does, is a
button *inside* Gmail reading "file this on a deal". That is a real capability and a later feature;
if it is wanted, a **Workspace add-on** (CardService) beats a Chrome extension, because it works in
Gmail on mobile as well as desktop and a domain admin installs it once for everybody instead of
each person installing it themselves.

### The trade-off, stated rather than buried

Domain-wide delegation means the service account can impersonate **any** mailbox in s4biz.io. Our
code limits it to `PIPELINE_MAILBOXES` and the scope is `gmail.readonly`, never `gmail.modify` - so
it can read, and it cannot label, archive or delete. But the limit on *whose* mail is in our code,
not in Google's grant: the control that actually matters is the service-account key, which lives in
the droplet's `chmod 600` env file and in GitHub Actions secrets, and nowhere else.

The alternative is per-user OAuth - each person clicks "connect Gmail" and we store a refresh token
per user. That narrows the blast radius to whoever consented, at the cost of tokens to store,
rotate and repair when they expire. Worth doing if the mailbox set ever grows beyond the two or
three people who run the channel; overkill for them.

### Where the consent lives — reversed TWICE in one day, and the second one is the right one

**Final answer: on the Administration page, as a per-person switch, stored beside the roles.**
The operator said it plainly — *"the approval of dima@s4biz.io or any other s4biz.io address needs
to be in the GUI of cybergod.ai as RBAC, not in any other way; all other backend issues need to be
working under the hood automatically"* — and he is right, for a reason worth keeping.

Consent to read a colleague's mailbox is an **administrative act**: a named administrator, a
recorded time, visible and reversible by somebody who is not holding a git client. Shipping a code
change to add a person is exactly the "edit code, commit, ship, come back" loop that
`colt_auth.email_allowed()` was already fixed to avoid, and the reasons are identical. A withdrawal
is a write (`enabled=0`) rather than a delete, because a row saying somebody turned it off is
evidence and a missing row is silence.

`user_store.user_mail` is its own table keyed by address — same shape and same reasoning as
`user_roles`, because the people this has to describe (Colt addresses, partners) have no credential
row at all. It fails closed: a store that cannot be read reads no mail.

**A control that cannot work is not offered.** Domain-wide delegation reaches our own Workspace
only, so `armin.hall@colt.net` can never be opened however many times a box is ticked. The page
shows "another Workspace" with the reason instead of a switch, and the route refuses a yes rather
than storing one — a green toggle beside a mailbox nothing will ever read is worse than no toggle.
Two different faults land in that refusal and they need opposite repairs, so it distinguishes them:
a mailbox in another company, versus a deployment with no `GMAIL_SENDER` that cannot tell which
domain is its own. Saying "outside this Workspace" for the second sends the operator to argue with
Google about an address that was fine.

**Only the platform administrator may set it.** Not `users.invite.org`, which a company
administrator holds: reading a colleague's mail is not user administration, it is a decision about
a person.

The same merge bug as the role case would have shipped with it and was caught by the same test
shape — somebody with a mailbox decision, no credential row and no live session vanished from the
only page that could switch it off again.

---

#### The first reversal, kept because deleting it loses why (superseded above)

`enabled()` used to require `PIPELINE_MAIL_READ=1` on the droplet, on the principle that a feature
which reads somebody's mailbox must not default to on. That principle is right and still holds.
What changed is WHERE the deliberate act lives.

`gmail_read.MAILBOXES` is now a committed list. Naming a person's address in the tree, reviewed in
a diff before it ships, is a stronger and far more auditable act of consent than an environment
variable typed into a droplet that nobody will ever look at again — it shows up in a PR, in
`git log`, and in a blame. It is the same reasoning that already puts `ADMIN_EMAILS`,
`PARTNER_EMAILS` and `USER_QUOTAS` in the tree rather than in an env file, and for mailbox reading
the argument is stronger, not weaker.

It also removes a manual step, which is operating principle 1: a value typed into a droplet by
hand gets forgotten, done differently on the twin, and lost on a rebuild.

`PIPELINE_MAIL_READ=0` stays as an immediate kill switch that needs no deploy, and an empty list
reads nothing whatever the flag says. The module's own self-test asserts all three, and the old
check is kept above the new one with its reasoning, because deleting it would lose why (class 17).

### The one human step

Only a domain admin can grant it, and it is one line in the console:

> admin.google.com → Security → Access and data control → API controls → Domain-wide delegation →
> edit client **105211423907937536502** → add `https://www.googleapis.com/auth/gmail.readonly`

That is the whole console job. Nothing else: the Gmail API is already enabled in the `colt-bots`
project (the send path proves it), colt-web already receives `GMAIL_SA_B64` and `GMAIL_SENDER`
through `env_file: assess-bot/.env`, and whose mail is read is committed. The next ship turns it on.

Until every half is in place the board names **all** the missing ones, not the first it finds —
reporting one cause of two sends the operator to fix it, redeploy, and come back to the same
screen.

## The sweep runs itself

A button is a feature somebody has to remember, and the point of filing partner mail against deals
is that the board is right when you open it. `mailsweep.py` installs a systemd timer - every 15
minutes, 5 after boot, persistent so an hour of downtime does not silently skip the mail that
arrived - and ship.py installs it as a building block, never as a second command.

The work happens inside colt-web by `docker exec`, because the credentials are in the container's
environment and nowhere on the host (class 55). The unit refuses to enable itself if colt-web is
not running: a timer that fails every fifteen minutes teaches the operator to ignore systemd.

Moving the sweep to a timer exposed a defect the board never would have: `pipeline.py`'s
`__main__` guard sat above `build_router()`, so `python -m app.pipeline` - exactly what the unit
runs - would have executed main() at a point where half the module did not exist (class 48). It is
the last statement in the file now, and a test asserts there is exactly one guard and it is last.
Asserting only that the *last* guard is last passed the mutation that added a second one higher up.

## What is not built

- **Deal documents.** Dima asked to "catch the balls that are falling, the NDAs … organize the
  documents, create link for Paratus". The map's §6 release matrix is the right model for it —
  per-document earliest release stage, five documents marked "Never" to a customer — and it is a
  feature in its own right, not a field on a card.
- **Vertical news on the card** (Jev at 54:00). Needs the threat-intel feed pointed at a customer
  vertical; it is a sensible second pass once the board has real deals on it.
- **Tier, territory and volumes** from R4/R5. Stored as notes today.
