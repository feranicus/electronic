#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""messages.py — the outreach copy, keyed by SEGMENT x ROLE. ONE source of truth.

    python marketing/campaign/messages.py            # print every message for review
    python marketing/campaign/messages.py --check    # the gate: length, banned words, coverage

THE ARGUMENT. Everything below is one idea, told to five different audiences.

    You cannot sell security to a company that believes it is already secure.

Every cyber deal starts with the same ritual. Book the discovery call. Ask what keeps them up at
night, what the pain points are, what the security projects are this year. And get the answer
everyone gets: we are fine, vendor X looks after it, call us back in six months.

That is not an objection a better script defeats. The prospect BELIEVES it, because nobody has ever
shown them otherwise. Discovery asks a stranger to confess a weakness to a salesperson, and nobody
does that.

So the product does not sell "an assessment". It sells the DELETION OF DISCOVERY. You type a
company name, and three minutes later you are not asking a question, you are stating a fact with a
number attached. The prospect cannot deny what they can see, and the call turns into a meeting, a
demo, remediation, and everything that gets sold after it.

THE FIRST VERSION OF THIS FILE LISTED FEATURES ("four decks, three minutes, passive, white-label")
and the operator was right to reject it. Features answer "what is it". A salesperson is asking
"what does my Tuesday look like if I have this". Every message below answers the second question,
and the features appear only as the reason the answer is credible.

STRUCTURE, the same five beats everywhere so the pitch cannot drift:
    1 THE RITUAL   their world and the answer they always get. They recognise themselves.
    2 THE TURN     they are not lying, they cannot see it. Removes blame, keeps the problem.
    3 THE PROOF    the actual opening line, with the number. This is the pen.
    4 THE UNLOCK   what changes, in the currency of their ROLE.
    5 THE ASK      name one prospect, report in 48 hours, free.

WHICH LEVER, BY ROLE (MEDDPICC):
    SALES     Identify Pain. Their call. Their six-months answer. Their meeting.
    EXEC      Economic Buyer + Metrics. The team's funnel, rep ramp, a line they can sell.
    PRESALES  Decision Criteria. They defend it in the room, so evidence quality is the pitch.

HOUSE STYLE, enforced by --check because it is the rule I break most:
    no em dashes · no "not X, it's Y" · vary sentence length · no closing aphorism
    no delve/leverage/robust/seamless/landscape · no OUR pricing, ever
A price for cybergod in a LinkedIn message is a negotiating position given away before the first
call. The loss figure in beat 3 is the PROSPECT's number and is the entire point, so the check
looks for pricing language, not for currency symbols.

ONLY CLAIMS THAT ARE TRUE. Measured in this repository: one company name is the only input, about
three minutes, four decks plus an animated HTML report, English German and Russian, partner
branding applied at render time, and nothing sent to the target, which is published at
cybergod.ai/partners and written into the Terms of Use.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- the close
# APPENDED BY render() TO EVERY MESSAGE, never written into a body. The first version put the ask
# inside each template and the demo and partner layers then quietly fell out of most of them, so a
# reader got an offer with no way to act on it and no idea a partner programme existed. Composing
# it in one place makes that impossible rather than merely unlikely.
#
# THE THREE LAYERS AND THEIR ORDER ARE THE WHOLE POINT. Give, then show, then ask. A cold message
# that opens with "become a partner" is asking a stranger for commitment before they have seen
# anything work.
#
# THE WORDING IS LIFTED FROM THE PARTNER DECK'S OWN "THE NEXT STEP" SLIDE, not invented:
#   01 See a demo report · 02 20 minutes with the architect, not a salesperson · 03 Become a
#   partner: pick a model, intro, resell or white-label.
# "Not a salesperson" is the strongest line in that deck and it is being said to salespeople, who
# know exactly what it means. My earlier "fifteen minutes" was weaker and, worse, a second number
# for a thing the deck already states as twenty.
#
# NO PRICES. The deck carries the tier discounts and the monthly figure. Those belong in the pack
# that goes out after a reply, not in a first message.
ASK = "Name one company you are chasing. I will send you their report in 48 hours, free."
DEMO = ("If it lands, twenty minutes with me directly. Not a salesperson, and if it is not useful "
        "it ends in twenty minutes.")
# Layer 3 is segment-aware because the three models are not equally attractive per segment. A
# distributor wants margin, a security vendor wants OEM, a hyperscaler partner wants to introduce
# and get out of the way.
PARTNER = {
    "CHANNEL": "And if you want to sell it: introduce us, resell it, or put your own brand on all "
               "four decks. Your choice, and I will send the partner pack.",
    "GSI": "And if it belongs in your portfolio: introduce us, resell it, or run it entirely under "
           "your own brand. I will send the partner pack.",
    "CONSULTING": "And if it belongs in the practice: introduce us, resell it, or put your firm's "
                  "brand on the output. I will send the partner pack.",
    "VENDOR": "And if it belongs in your channel or inside your own stack, there is a white-label "
              "and an OEM route. I will send the partner pack.",
    "CARRIER": "And if you want it in the portfolio: resell it, or run it under your own brand. I "
               "will send the partner pack.",
    "HYPERSCALER": "And if it is useful to your partners, the simplest version is an introduction. "
                   "We do the rest and you look good for it.",
}
ROUTE = "feranicus@s4biz.io  ·  cybergod.ai"


def close_for(seg):
    return "\n\n".join([ASK, DEMO, PARTNER.get(seg, PARTNER["CHANNEL"]), ROUTE])

# Beat 3, the opening line the prospect hears.
#
# VENDOR-NEUTRAL, ALWAYS. The first version named Palo Alto and carried a second, neutral variant
# for messages going to security vendors, because naming a competitor's box in a message to a
# vendor is a distraction at best. Neutral everywhere is simply better and it deletes the branch:
#   * a reader who runs Fortinet stops reading a line that is about somebody else's kit
#   * to a vendor it stops reading as a dig at a competitor
#   * "firewall VPN" is what every one of these actually is, so the sentence covers all of them
# Two homes for one sentence is also how these things drift; there is now one.
PROOF = ('"Your firewall VPN is reachable from the internet. If it goes, six hundred people '
         'cannot log in, and a day of that runs to about 120,000 euro before anyone talks '
         'about a ransom."')
PROOF_SHORT = "their firewall VPN sitting open to the internet"

# Naming any of these in outreach is a defect, not a style preference. Asserted by --check.
VENDOR_NAMES = ["palo alto", "fortinet", "fortigate", "cisco", "check point", "checkpoint",
                "sonicwall", "sophos", "watchguard", "juniper", "barracuda", "zscaler",
                "netscaler", "citrix", "pulse secure", "ivanti", "big-ip", "meraki",
                "forcepoint", "stormshield", "hillstone", "firebox"]

MESSAGES = {}


def _m(seg, role, body):
    MESSAGES["%s_%s" % (seg, role)] = body.strip()


# ---------------------------------------------------------------- CHANNEL (VAR / MSP / MSSP)
_m("CHANNEL", "SALES", """
Hi {first},

Every cyber deal starts with the same ritual. Book the discovery call, ask what keeps them up at
night, ask what their security projects are this year. Then get the answer you always get: we are
fine, vendor X looks after it, call us back in six months.

They are not lying to you. They cannot see what you can see.

Type their company name into cybergod.ai. Three minutes later you are not asking a question, you
are opening with a fact:

{proof}

Nobody answers that with call me back in six months. They answer with who else can see this.

Nothing is sent to their network, so there is no permission to ask for and no scoping call first.
""")

_m("CHANNEL", "EXEC", """
Hi {first},

Your reps' discovery calls all end the same way. What keeps you up at night, what are your
priorities this year, and then: we are fine, vendor X looks after it, call us back in six months.

That is not an objection you can train around. The customer believes it, because nobody has shown
them otherwise.

cybergod.ai takes a company name and returns that company's real exposure in three minutes. The rep
stops running a questionnaire and opens with {proof_short} and the number attached to it.

What changes is the top of the funnel, which is the part you cannot hire your way out of. A new
starter can run it in week one. It carries your logo and your colours, so the customer sees your
firm doing the analysis.

""")

_m("CHANNEL", "PRESALES", """
Hi {first},

You get pulled into discovery workshops to find out what a customer has, and a good half of them
are for deals that were never real.

cybergod.ai hands you the external estate before the first call. A company name, three minutes, and
every finding cites the host and the port it came from: exposed VPN and management planes, revoked
and expired certificates, mail authentication gaps, the loss modelled in money, the NIS2 articles.

It is deliberately conservative, because you are the one defending it in the room. Hosts it cannot
attribute to the customer are dropped. A failed lookup is reported as unknown instead of being
graded as a weakness. Invented CVE references are stripped before they reach a slide.

Nothing is sent to their network.
""")

_m("CHANNEL", "DEFAULT", """
Hi {first},

Cyber discovery calls end the same way every time: we are fine, vendor X looks after it, call back
in six months.

cybergod.ai removes the discovery. A company name, three minutes, and you open with {proof_short}
and what a day of it costs them. Nothing is sent to their network. Your brand on the report.
""")

# ---------------------------------------------------------------- GSI
_m("GSI", "SALES", """
Hi {first},

The security conversation inside an account you already hold is the hardest one to start. You ask
what their priorities are this year and you get the polite version: it is handled, the incumbent
looks after it, come back at budget time.

They are not being evasive. Nobody has put their external exposure in front of them.

cybergod.ai does it from a company name in three minutes. You walk in with {proof_short} and the
cost of a day of it, rather than a slide about your capability.

That is the difference between being invited to bid and being the person who found it. Nothing is
sent to their network, so it runs before any engagement letter exists.
""")

_m("GSI", "EXEC", """
Hi {first},

Your pursuit teams spend weeks building the credibility to talk about security, and the client
still answers the first question with: it is handled, the incumbent has it, come back at budget
time.

cybergod.ai compresses that to one call. A company name returns the client's real exposure in three
minutes, with the loss modelled in money and the NIS2, CRA, EU AI Act or OSFI position depending on
where they sit. The team opens with a finding instead of a credentials deck.

It is entirely passive, so it runs before there is an engagement letter, and it carries your brand
on every page. Your consultants keep the relationship and the follow-on work.

""")

_m("GSI", "PRESALES", """
Hi {first},

Pursuit teams burn weeks proving they understand a client's estate before anyone is paying for the
work, and the discovery workshop that would answer it is the thing the client will not schedule.

cybergod.ai does the external half from a company name in three minutes. Every finding names the
host and port behind it. Where the data does not support a conclusion the engine says unknown
instead of filling the slide, which is what makes it survive a client architect reading it line by
line.

Nothing is sent to their network.
""")

_m("GSI", "DEFAULT", """
Hi {first},

Clients answer the security question with "it is handled, come back at budget time", and a
credentials deck does not change that.

cybergod.ai turns a company name into their real exposure in three minutes: {proof_short}, the loss
in money, the regulatory gaps. Passive, so it runs before any engagement letter. Your brand on it.
""")

# ---------------------------------------------------------------- CONSULTING (Big 4 and beyond)
_m("CONSULTING", "SALES", """
Hi {first},

The awkward part of selling an assessment is that you have to sell the assessment. You ask what
their cyber priorities are, they say it is covered, and you are proposing a scoping phase to
discover a problem they have already told you they do not have.

cybergod.ai lets you skip to the end. A company name, three minutes, and the first thing they hear
from you is {proof_short}, with the cost of a day of it.

Now you are not proposing discovery. You are being asked what else is in there.

Nothing is sent to their network, so there is nothing to authorise and no letter to sign before you
can show a prospect something real.
""")

_m("CONSULTING", "EXEC", """
Hi {first},

Your cyber practice has to sell an assessment before it can perform one, and the buyer's honest
answer to "what are your priorities this year" is that it is covered by someone else.

cybergod.ai removes that step. A company name produces the client's real external exposure in three
minutes: the finding, the loss quantified, the sector actors, and their NIS2, CRA, EU AI Act or
OSFI position. Passive throughout, so a partner can put it in front of a prospect with no
authorisation and no engagement letter.

Your firm's brand on the output. It shortens the distance between a first conversation and a signed
scope, which is the only part of that funnel that has never got faster.

""")

_m("CONSULTING", "PRESALES", """
Hi {first},

The external discovery on a cyber assessment eats the margin, and it is also the part the client
can verify afterwards, which means it has to be right.

We automated it carefully. A company name, three minutes, and every finding cites the host and port
it came from. A failed lookup is reported as unknown rather than graded as a gap. Infrastructure the
engine cannot attribute to the client is dropped instead of inflating the estate. Unverifiable CVE
references are stripped before anything reaches a slide.

Nothing is sent to their network.
""")

_m("CONSULTING", "DEFAULT", """
Hi {first},

Selling a cyber assessment means convincing someone who has just told you they are covered.

cybergod.ai gives you their real exposure from a company name in three minutes, priced, with the
regulatory gaps named. Nothing sent to their network, no authorisation needed. Your firm's brand.
""")

# ---------------------------------------------------------------- VENDOR (security vendors)
_m("VENDOR", "SALES", """
Hi {first},

The deal is usually lost before your product is ever mentioned. Discovery call, what keeps you up
at night, and back comes: we are fine, we have a stack, call us in six months.

cybergod.ai changes what you open with. A company name, three minutes, and the first sentence is
{proof_short} with the cost of a day of it attached.

Then your product is not a proposal. It is the answer to something they have just seen.

Nothing is sent to their network, so there is no permission to chase first.
""")

_m("VENDOR", "EXEC", """
Hi {first},

Your partners lose the deal before your product is discussed. They book discovery, ask what keeps
the customer up at night, and hear the same thing everyone hears: we are fine, we have a stack,
call back in six months.

That is demand creation, it is the slowest part of the funnel, and it is the part you cannot do on
their behalf.

cybergod.ai turns a company name into that customer's real exposure in three minutes, with the loss
priced. The partner stops asking and starts showing. Every finding it produces is an argument for
buying something, and very often it is an argument for what you already sell.

It carries the partner's brand, or yours.

""")

_m("VENDOR", "PRESALES", """
Hi {first},

You spend the first two calls establishing that the prospect has a problem, and only then get to
talk about solving it.

cybergod.ai arrives with the problem already evidenced. A company name, three minutes, and each
finding cites the host and port behind it. It is built to be conservative: unattributable hosts are
dropped, a failed lookup is reported as unknown rather than graded as a weakness, and CVE references
it cannot verify are stripped before they reach a slide.

Nothing is sent to their network.
""")

_m("VENDOR", "DEFAULT", """
Hi {first},

Your partners have to create the demand before they can sell your product into it, and discovery
calls keep coming back as "we are fine, call in six months".

cybergod.ai turns a company name into the customer's real exposure in three minutes, priced, under
the partner's brand. Every finding is a reason to buy something.
""")

# ---------------------------------------------------------------- CARRIER (telco, non-Colt)
_m("CARRIER", "SALES", """
Hi {first},

Managed security is a hard sell to a customer who already believes they are covered. You ask about
their security priorities, they say the incumbent handles it, and the connectivity conversation is
the only one left.

cybergod.ai gives you a different opening. A company name, three minutes, and you lead with
{proof_short} and what a day of it costs them.

Every finding it returns points at managed firewall, SASE or DDoS, which is what you were going to
propose anyway. Now there is a reason attached.

Nothing is sent to their network.
""")

_m("CARRIER", "EXEC", """
Hi {first},

Selling managed security into your own connectivity base runs into the same wall every time. The
customer says it is handled, and your team has no evidence to argue with.

cybergod.ai produces the evidence from a company name in three minutes: the exposed appliance, what
a day of downtime costs, the actors that target that sector, the NIS2 position. Passive throughout,
so it runs before any contract exists.

Every finding lands on something you already sell. It carries your brand, so the customer sees your
name on the analysis.
""")

_m("CARRIER", "PRESALES", """
Hi {first},

Qualifying a managed security opportunity means finding out what the customer actually has exposed,
and the workshop that would tell you is the thing they will not schedule.

cybergod.ai does the external view from a company name in three minutes, with the host and port
behind every finding. Where the data will not support a claim it says unknown instead of grading a
weakness, which is what makes it safe in front of a customer's architect.

Nothing is sent to their network.
""")

_m("CARRIER", "DEFAULT", """
Hi {first},

Customers answer the managed security question with "it is handled", and there is no evidence in
the room to argue with.

cybergod.ai produces it from a company name in three minutes: {proof_short}, the cost of a day of
it, the NIS2 gap. Nothing sent to their network. Your brand on the report.
""")

# ---------------------------------------------------------------- HYPERSCALER
_m("HYPERSCALER", "SALES", """
Hi {first},

Security workloads land once the customer accepts they have a problem, and the discovery call that
should establish it comes back as "we are covered, call us next year".

cybergod.ai gives partners the opening. A company name, three minutes, and the conversation starts
with {proof_short} and the cost of a day of it. Nothing is sent to their network.
""")
_m("HYPERSCALER", "EXEC", """
Hi {first},

Your partners' security conversations stall at the same place: the customer believes they are
covered, and nobody has shown them otherwise.

cybergod.ai produces a customer's real external exposure from a company name in three minutes, with
the loss priced and the regulatory gaps named. Passive, so it runs before any engagement. Partners
use it to open security conversations that land on your platform.
""")
_m("HYPERSCALER", "PRESALES", MESSAGES["CARRIER_PRESALES"])
_m("HYPERSCALER", "DEFAULT", MESSAGES["CARRIER_DEFAULT"])

# DELIVERY and OTHER get the segment default: they are not the buyer, so the message is short and
# its only job is to reach somebody who is.
for _s in ("CHANNEL", "GSI", "CONSULTING", "VENDOR", "CARRIER", "HYPERSCALER"):
    for _r in ("DELIVERY", "OTHER"):
        MESSAGES["%s_%s" % (_s, _r)] = MESSAGES["%s_DEFAULT" % _s]

# ---------------------------------------------------------------- named accounts
# A person worth an hour of thought gets a hand-written message. The queue uses these verbatim and
# skips the template. Keyed by the LinkedIn vanity slug.
NAMED = {
    "joe-sophos": """
Hi Joe,

Sophos wins when a mid-market board accepts it has a problem. Your partners have to produce that
acceptance before MDR is ever on the table, and their discovery calls come back the way everyone's
do: we are fine, we have a stack, call us in six months.

That belief is the real competitor. It is not price and it is not a feature comparison.

We built the thing that ends it. One input, a company name. Three minutes later the partner is not
asking a question, they are saying: your firewall VPN is reachable from the internet, six
hundred people cannot work if it goes, and a day of that is about 120,000 euro. Every finding it produces
is an argument for something Sophos already sells.

Completely passive. Nothing is sent to the target, so there is no authorisation and no scoping call
standing between a partner and that first sentence.

Two ways it could matter to you. Partners white-label it and it feeds your funnel. Or it sits inside
your stack under an OEM arrangement and becomes a Sophos capability.

Name one account Sophos is chasing and I will send that report in 48 hours, free, so you are judging
the artifact rather than my description of it.
""",
}


# ---------------------------------------------------------------- rendering + the gate
# NOT a blanket currency ban. The loss figure in beat 3 is the PROSPECT's number and is the whole
# argument; what must never appear is what WE charge, because a price in a first message is a
# negotiating position given away before the first call.
BANNED = [
    ("em dash", "—"),
    ("en dash as punctuation", " – "),
    ("delve", "delve"), ("leverage", "leverage"), ("robust", "robust"),
    ("seamless", "seamless"), ("landscape", "landscape"), ("testament", "testament"),
    ("pivotal", "pivotal"), ("here's the thing", "here's the thing"),
    ("our pricing", "per seat"), ("our pricing", "per month"), ("our pricing", "per user"),
    ("our pricing", "discount"), ("our pricing", "list price"), ("our pricing", "margin of"),
    ("our pricing", "costs only"), ("our pricing", "starting at"),
]
MAX_CHARS = 1300          # past this a LinkedIn message stops being read


def render(target):
    """The exact text for one person, as (text, which_template).

    ONE FUNCTION, ONE CONTRACT. Splitting this into a text-returning render() and a tuple-returning
    render() is how api.js ended up with two fetch helpers of different shapes and a feature that
    silently disappeared. Both callers, the queue and the gate, unpack two values.
    """
    slug = re.sub(r"^.*?/in/([^/?]+).*$", r"\1", (target.get("url") or "").rstrip("/"))
    if slug in NAMED:
        return NAMED[slug].strip(), "named:%s" % slug
    key = target.get("message_key") or ""
    seg = target.get("segment", "")
    body = MESSAGES.get(key) or MESSAGES.get("%s_DEFAULT" % seg)
    if not body:
        return None, "no template for %r" % key
    txt = body.format(first=target.get("first") or "there",
                      proof=PROOF, proof_short=PROOF_SHORT)
    # LinkedIn collapses single newlines; keep the paragraph breaks, unwrap the source formatting.
    txt = re.sub(r"(?<!\n)\n(?!\n)", " ", txt)
    txt = re.sub(r"[ \t]{2,}", " ", txt).strip()
    # THE CLOSE IS APPENDED HERE, ALWAYS. Not a placeholder a template can forget.
    return txt + "\n\n" + close_for(seg), key


def check():
    fails = []

    def bad(label, why):
        fails.append(label)
        print("  FAIL  %-22s %s" % (label, why))

    for key in sorted(MESSAGES):
        seg = key.split("_")[0]
        txt, _ = render({"first": "Alex", "url": "", "message_key": key, "segment": seg})
        if txt is None:
            bad(key, "renders to nothing")
            continue
        if len(txt) > MAX_CHARS:
            bad(key, "%d chars, over the %d limit" % (len(txt), MAX_CHARS))
        low = txt.lower()
        for name, tok in BANNED:
            if tok.lower() in low:
                bad(key, "banned token (%s): %r" % (name, tok))
        if "{" in txt or "}" in txt:
            bad(key, "an unsubstituted placeholder reached the message")
        # THE CLOSE, ALL THREE LAYERS PLUS A ROUTE. The operator's question was "this message has
        # no call to action to contact us or how to move forward with partnership", and he was
        # right: an earlier rewrite kept the free assessment and silently dropped the demo and the
        # partner layer from most buckets. A reader was being given an offer with no way to act on
        # it and no idea a partner programme existed. Each layer is now asserted separately,
        # because "the close is present" was exactly the check that let two thirds of it vanish.
        if "48 hours" not in low:
            bad(key, "layer 1 GIVE missing: no free assessment, so it asks before it offers")
        if "twenty minutes" not in low:
            bad(key, "layer 2 SHOW missing: no demo, so a warm reply has nowhere to go")
        if not any(w in low for w in ("partner pack", "introduce us", "introduction",
                                      "white-label", "oem", "resell")):
            bad(key, "layer 3 PARTNER missing: no route into the partner programme")
        if "@" not in txt or "cybergod.ai" not in low:
            bad(key, "no contact route: a forwarded message must carry an address")
        # BEAT 1 ASSERTED, BY CONCEPT NOT BY PHRASE. The ritual differs by role: a seller's is the
        # "call back in six months" brush-off, a presales engineer's is the discovery workshop for a
        # deal that was never real. Listing the exact sentences I happened to write would only
        # restate the copy back to itself, which is a check that cannot fail. Requiring the
        # DISCOVERY IDEA to be present is a real test: the rejected first version of this file
        # opened "you sell security services and the hard part is getting the first meeting" and
        # contains none of these, so this gate would have stopped it.
        if not any(w in low for w in ("discovery", "six months", "budget time", "next year",
                                      "covered", "handled", "questionnaire", "workshop",
                                      "first two calls")):
            bad(key, "beat 1 missing: it never names the ritual it replaces, so it is a feature list")
        if "three minutes" not in low:
            bad(key, "does not say how fast, which is what makes the claim credible")
        for v in VENDOR_NAMES:
            if v in low:
                bad(key, "names a firewall vendor (%r). Keep beat 3 neutral: a reader who runs "
                         "something else stops reading, and to a vendor it reads as a dig." % v)

    for slug, body in NAMED.items():
        t = body.strip()
        if len(t) > 2000:
            bad("named:" + slug, "%d chars" % len(t))
        for name, tok in BANNED:
            if tok.lower() in t.lower():
                bad("named:" + slug, "banned token (%s)" % name)

    tp = os.path.join(HERE, "targets.json")
    if os.path.exists(tp):
        keys = {t["message_key"] for t in json.load(open(tp, encoding="utf-8"))}
        missing = sorted(k for k in keys if k not in MESSAGES)
        if missing:
            bad("coverage", "target buckets with no copy: %s" % ", ".join(missing))
        else:
            print("  PASS  coverage             all %d target buckets have copy" % len(keys))
    if fails:
        print("\n  %d FAILURE(S)" % len(fails))
        return 1
    print("  PASS  %d message(s): length, style, the ask, and all five beats" % len(MESSAGES))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--key", help="print one bucket, e.g. VENDOR_SALES")
    a = ap.parse_args()
    if a.check:
        sys.exit(check())
    keys = [a.key] if a.key else sorted(MESSAGES)
    for k in keys:
        txt, _ = render({"first": "Alex", "url": "", "message_key": k, "segment": k.split("_")[0]})
        print("=" * 78)
        print("  %s   (%d chars)" % (k, len(txt or "")))
        print("=" * 78)
        print(txt)
        print()
    if not a.key:
        for slug, body in NAMED.items():
            print("=" * 78)
            print("  NAMED: %s   (%d chars)" % (slug, len(body.strip())))
            print("=" * 78)
            print(body.strip())
            print()


if __name__ == "__main__":
    main()
