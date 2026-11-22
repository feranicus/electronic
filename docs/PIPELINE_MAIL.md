# Mail into the Pipeline — how it works, end to end

A short manual for the people who use it, not for the people who wrote it. Every number here is
read from the code, not remembered; the file that holds each one is named beside it so you can
check.

---

## The one-paragraph version

Every 15 minutes a timer on the droplet asks Gmail for the last two weeks of mail in the mailboxes
you switched on, scores each message against the open deals, and files the ones it is sure about on
the right card. It never guesses: a message it cannot place lands in an "unplaced" list you can
file by hand. It never moves a card. It only reads.

---

## Switching it on (two steps, once)

**1. Google, once — a domain admin.** admin.google.com → Security → Access and data control →
API controls → Domain-wide delegation → edit client `105211423907937536502` → add
`https://www.googleapis.com/auth/gmail.readonly`.

That is the same service account that already sends your sign-in codes. Nothing else in Google
needs touching: the Gmail API is already on in the `colt-bots` project, and colt-web already
receives the credential.

**2. cybergod.ai → Admin → Users.** Tick **Mailbox** beside each person whose mail should be read.

Three states, and they are different: *read into Pipeline*, *not read*, *not decided*. Untick it
and reading stops immediately — no deploy. A colt.net or other outside address shows
"another Workspace" instead of a switch, because our delegation reaches s4biz.io only and that
mailbox cannot be opened whoever ticks what.

Only the platform administrator can set this. Reading a colleague's mail is a decision about a
person, not user administration.

---

## The cycle, step by step

### 1. The timer fires — every 15 minutes

`mailsweep.service`, installed by `ship.py`. Also 5 minutes after a reboot, and it catches up a
missed window rather than skipping it. Hard ceiling of 300 seconds so a hung call to Google cannot
overlap the next run. *(mailsweep.py)*

You can also press **Read mail now** on the board. Same code, same result.

### 2. It reads each mailbox — the last 14 days, 60 messages at most

One token per mailbox, minted for that person only, read-only. If one mailbox is refused the
others still run and the board says which one failed and why.

What it does NOT look at: chats, drafts, anything you sent yourself, Promotions, Social.
*(gmail_read.py — `LOOKBACK_DAYS` 14, `MAX_MESSAGES` 60, `DEFAULT_QUERY`)*

A message already seen is skipped. The sweep is safe to run twice; nothing is filed twice.

### 3. It scores every message against every open deal

Arithmetic, not a model. Each signal is a fact about the message compared to a fact about the deal:

| Points | Signal |
|---|---|
| 4 | the sender's domain is the deal's own domain (`paratus.africa`) |
| 4 | the sender's domain carries the company name, when the deal has no domain recorded |
| 4 | the deal's named contact is on the message (From, To or Cc) |
| 3 | the company's name appears in the message |
| 2 | the deal reference appears anywhere in it |
| 2 | the subject carries three significant words of the deal title |
| 1 | it arrived after the deal was opened, within a year |

**A message needs 5 to be filed.** *(dealmatch.py — `MIN_SCORE` 5, `WINDOW_DAYS` 365)*

That floor is deliberately above "the company name appeared once": *Paratus* in an industry
newsletter is not a message from Paratus.

Three things it refuses outright:

- **Nothing clears 5** → unplaced, with "no deal matched strongly enough".
- **Two deals tie** → unplaced, naming both. Filing Paratus's pricing question under the wrong
  Paratus deal makes the board lie quietly, which is worse than leaving it in the queue.
- **The message predates the deal** → refused. It cannot be about a deal that had not been opened.

Closed deals (Lost) are not considered at all.

### 4. It files what it is sure about

The message appears under **Mail filed on this deal**, with a label (`nda`, `agreement`, `loi`,
`poc`, `signature`, `invoice`, `pricing`, `meeting`, or plain `mail`) and the **evidence** — the
actual reasons it was filed here. If you disagree with a link, the evidence tells you why it
happened.

**The label never moves a card.** The stages in the process map are signature events; an email that
says "NDA" is not an NDA that was signed. You move the card; this only helps you find it.

### 5. What it could not place waits for you

"Mail nobody could place", under the board, with the reason. Pick a deal from the dropdown and it
is filed. That queue is the point — "we saw it and could not place it" is work for a person, and
throwing it away would make the same message look like new activity on the next sweep.

---

## What it never does

- **It never writes to Gmail.** The scope is `gmail.readonly`. It cannot label, archive, reply or
  delete, and a test fails the build if a write scope ever appears in that module.
- **It never moves a card between stages.** Only a person does that.
- **It never reads a mailbox nobody switched on.** If the store cannot be read it reads nothing —
  on a question about someone's mail there is only one safe direction.
- **It never reads outside s4biz.io.** Delegation does not reach another company's Workspace.

---

## Making the matching work better

The matcher can only use what the deal card tells it. A deal with just a company name matches on
the name and the timing — enough to be useful, not enough to be certain. Fill in:

- **Domain** (`paratus.africa`) — the strongest single signal. One field, four points.
- **Contact** (`someone@paratus.africa`) — catches the case where they write from a personal
  address, and catches people you are copied with.
- **Title** — helps when one company has two deals running.

A company with two open deals and nothing to tell them apart will tie, and tie means unplaced. If
you see the same pair tying repeatedly, give them different titles or different contacts.

---

## When something looks wrong

**The board says "off".** It names the missing half, or halves — the credential, the kill switch,
or no mailbox switched on. Fix what it names.

**A mailbox is refused.** The note names the mailbox and what Google said. A 403 usually means the
`gmail.readonly` scope has not been added for that client id.

**Nothing is being filed.** Press **Read mail now** and read the counts: it reports how many it
read, how many it filed, how many it could not place, and how many it had already seen. A sweep
that reads 0 is a mailbox problem; a sweep that reads 40 and files 0 is a matching problem, and the
unplaced queue will say why for each one.

**Stop it immediately.** Untick the mailboxes on the Admin page. For everything at once,
`PIPELINE_MAIL_READ=0` on the droplet stops all reading without a deploy.

---

## Who can do what

| | view the board | move cards, notes | read mailboxes, re-file |
|---|---|---|---|
| Platform administrator | yes | yes | yes |
| S4biz power user | yes | yes | yes |
| Reseller administrator | yes | yes | — |
| Sales representative | yes | yes | — |
| Company administrator, Pre-sales, User | — | — | — |

*(roles.py — `pipeline.view`, `pipeline.edit`, `pipeline.admin`)*

Every one of these is checked on the server for every request. Hiding a menu item is presentation,
not a control.

---

## Where things live

| What | Where |
|---|---|
| Reading Gmail | `webapp/backend/app/gmail_read.py` |
| Scoring and labelling | `webapp/backend/app/dealmatch.py` |
| Deals, stages, filing, the sweep | `webapp/backend/app/pipeline.py` |
| The board | `webapp/frontend/src/pages/Pipeline.jsx` |
| The timer | `mailsweep.py`, installed by `ship.py` |
| Who may do what | `roles.py` |
| Why it is built this way | `docs/decisions/2026-11-pipeline.md` |

The stage columns come from `Herkos_Commercial_Process_Map_v0.1_DRAFT.docx` and are not edited in
the code by hand. `python -m app.pipeline` from `webapp/backend` prints all three tracks.
