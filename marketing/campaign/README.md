# cybergod.ai outreach campaign

## One command

    cd "C:\Python SW\Linkedin Scraper"
    python marketing/campaign/outreach.py

That is the whole thing. It builds the target list if it is missing or stale, then works the queue:
for each person it opens their LinkedIn profile in your browser, puts their message on your
clipboard, prints the two files to attach, and waits for you to press send.

Useful flags:

    --dry-run              show the queue, open nothing, log nothing
    --segment CHANNEL      one segment at a time (CHANNEL GSI CONSULTING VENDOR CARRIER HYPERSCALER)
    --role SALES           one role at a time (EXEC SALES PRESALES)
    --limit 10
    --report               who has been contacted, by segment and role

## What is in here

| file | what it is |
|---|---|
| `outreach.py` | the queue. The only command you run. |
| `build_targets.py` | turns your `Connections.csv` export into a prioritised list. Called automatically. |
| `messages.py` | the copy, keyed by segment and role, plus hand-written messages for named people. |
| `test_targets.py` | the gate. Run it after editing either of the above. |
| `targets.json` / `targets.csv` | generated. The list, ranked. |
| `sent.jsonl` | generated. Who was contacted, when, with which message. Never edited by hand. |

## The list

10,237 connections in, 1,147 targets out, which is 11%. Everything else is a customer, a
colleague, a recruiter or somebody who cannot resell an assessment.

| segment | count | why they are here |
|---|---|---|
| HYPERSCALER | 318 | partner ecosystems, lower priority, ranked last |
| VENDOR | 282 | security vendors whose channel needs demand created |
| CARRIER | 229 | telcos already selling managed security |
| CHANNEL | 160 | VARs, MSPs, MSSPs, distributors. The most direct resellers. |
| GSI | 113 | Cognizant, Accenture, Infosys, Capgemini, NTT Data |
| CONSULTING | 45 | Big 4 plus Mazars and the mid-tier |

Ranking is segment fit plus role fit plus a small bonus for a recent connection. That is all. A
score you cannot explain to the person you are about to message is a score you should not act on.

**Colt is excluded entirely.** 396 connections and the single biggest block in the file. They are
ex-colleagues, not a market.

**BDO, Baker Tilly and Grant Thornton have zero connections in the export.** Three of the firms on
the original brief are not reachable this way. That needs a different route, not a different filter.

## The argument

Everything in here is one idea, told to five audiences.

> You cannot sell security to a company that believes it is already secure.

Every cyber deal starts with the same ritual. Book the discovery call. Ask what keeps them up at
night, what the pain points are, what the security projects are this year. And get the answer
everyone gets: we are fine, vendor X looks after it, call us back in six months.

That is not an objection a better script defeats. The prospect believes it, because nobody has ever
shown them otherwise. Discovery asks a stranger to confess a weakness to a salesperson.

So the product does not sell an assessment. It sells the deletion of discovery. Type a company
name, and three minutes later you are not asking a question, you are stating a fact with a number
attached. That turns a call into a meeting, a meeting into a demo, and a demo into remediation and
everything sold after it.

The first version of this file listed features (four decks, three minutes, passive, white-label)
and was rejected, correctly. Features answer "what is it". A salesperson is asking "what does my
Tuesday look like if I have this".

## The messages

Six segments times four roles, plus a per-person override for anybody worth an hour of thought.

    python marketing/campaign/messages.py --key CHANNEL_SALES
    python marketing/campaign/messages.py            # all of them

Same five beats everywhere, so the pitch cannot drift:

1. **The ritual.** Their world and the answer they always get. They recognise themselves.
2. **The turn.** They are not lying, they cannot see it. Removes the blame, keeps the problem.
3. **The proof.** The actual opening line, with the number. This is the pen.
4. **The unlock.** What changes, in the currency of their role.
5. **The ask.** Name one prospect, report in 48 hours, free.

The lever changes by role, because the same pen is a different pen to each of them:

- **SALES** feels it on their own calls. The six-months answer, and what replaces it.
- **EXEC** is the economic buyer. The team's funnel, rep ramp, and a line they can sell.
- **PRESALES** owns the decision criteria and has to defend the finding in the room, so evidence
  quality is the entire pitch.

## The close

Three layers and a route, appended by `render()` to every message. It is **not** a placeholder a
template can forget, because an earlier version put the ask inside each body and the demo and
partner layers then quietly fell out of most of them. A reader got an offer with no way to act on
it and no idea a partner programme existed.

1. **Give.** Name one company you are chasing and their report lands in 48 hours, free.
2. **Show.** Twenty minutes with the architect, not a salesperson, and it ends in twenty minutes if
   it is not useful.
3. **Partner.** Introduce us, resell it, or put your own brand on all four decks. Partner pack on
   request. Segment-aware, because a distributor wants margin, a security vendor wants OEM and a
   hyperscaler partner wants to introduce and get out of the way.
4. **Route.** `feranicus@s4biz.io · cybergod.ai`, so a forwarded message can be acted on.

The wording of layers 2 and 3 is lifted from the partner deck's own "The next step" slide rather
than invented, so the message and the pack say the same thing.

Order matters. A cold message that opens with "become a partner" asks a stranger for commitment
before they have seen anything work.

`messages.py --check` enforces the style and, more usefully, the argument: every message must name
the ritual it replaces, say how fast it is, and carry **all three close layers plus a contact
address**, each asserted separately. Checking only that "a close is present" is exactly what let
two thirds of it disappear. Verified by removing each layer in turn and confirming the gate fails,
and against the rejected first draft, which it also fails.

No em dashes and no prices for cybergod, ever. The loss figure in beat 3 is the *prospect's* number
and is the whole point, so the check looks for pricing language rather than currency symbols.

## Attachments

Two, every time. The concept and one artifact that proves it.

- `Cybergod_OnePager_EN.pdf` (generated by `build_onepager.py`, built automatically if missing)
- `rosatom.ru_Shodan_Findings.pptx`

A PDF, not the pitch deck. Most of these are read on a phone inside LinkedIn, where a PDF opens
inline and a .pptx has to be downloaded and opened in another app. That extra step is where a cold
message dies. The deck is what you send after they reply, and the partner agreements, SLA and DPA
are what you send after they say yes.

To change the one-pager, edit `build_onepager.py` and run it with `--png` so you look at the result
rather than trusting the code. It sizes its own boxes from the measured text, so longer copy grows
the box instead of being clipped.

## Why it does not send the messages itself

LinkedIn's User Agreement section 8.2 prohibits automated access and automated messaging, and the
penalty is account termination. This campaign runs on a profile with ten thousand connections built
over a career. A tool that risks that to save four seconds of pasting is a bad trade.

The second reason is the better one. A message a human read before sending is a better message. The
queue removes the tedious part, which is deciding who is next and what to say to them. It leaves
the part that actually earns the reply.

`sent.jsonl` is what stops a second run contacting the same person, survives the terminal being
closed, and is the only honest answer to "what did we actually send". Nothing is ever removed
from it.

## Rate

`DAILY_CAP = 25`. LinkedIn does not publish a limit and it varies by account age and behaviour. A
campaign that gets the account restricted on day two reaches nobody.

## Editing the copy

Edit `messages.py`, then:

    python marketing/campaign/messages.py --check
    python marketing/campaign/test_targets.py

The second one also proves every bucket the target list can produce has copy behind it. A bucket
with no message means somebody in the queue gets nothing.

## Editing the classifier

The two rules that matter, both learned the hard way:

**A token must start a word.** The first version used bare substring matching, so `"it "` matched
inside "Clal**it** Health Services", which is a hospital, and `"tech"` matched inside "Bio**tech**".
Both cleared every other test and landed at the top of the queue.

**Tightening a rule until the false positives disappear also deletes the customers.** The fix for
the above lost Bechtle IT-Systemhaus, Orange Cyberdefense and Softcat, who are literally the
channel. `test_targets.py` holds both directions, with the real company names, so the next edit
cannot fix one and quietly break the other.
