"""release_notes.py — the four panel models write the release notes, and they are DELIVERED.

STANDING RULE (operator, 9 Aug 2026): every release, the SAME four models that review the staging
gate also write the release notes, and those notes are sent to feranicus@s4biz.io through the Gmail
API gateway AND to the operator's Telegram. A release nobody was told about is a release nobody can
review.

WHY IT RUNS INSIDE colt-web. Three things it needs live on the droplet and deliberately never on
the operator's PC or in git: OPENAI_API_KEY (the models), the Gmail API service-account credentials
(SMTP is BLOCKED outbound on this host — never "fix" this to SMTP), and BOT_TOKEN (Telegram). So
ship.py gathers the FACTS on the PC and pipes them in here:

    ssh <droplet> 'docker exec -i colt-web python3 -m app.release_notes' < facts.json

THE SAME FOUR MODELS as deploy/stagegate/quorum.py, and for the same reason: no shared failure
domain. Four vendors means a provider-wide 429 cannot silence the whole panel, and a model that is
wrong about the release is contradicted by three others rather than believed.

TWO RULES THIS FILE OBEYS:
  · THE DETERMINISTIC FACTS ARE THE NOTES. The commits, the files, the gate result and the engine
    hashes are computed by ship.py and reproduced verbatim. The models add readable prose and their
    own risk read ON TOP. If every model fails, the notes still go out and are still correct —
    exactly the doctrine that keeps the deck honest when enrichment fails.
  · IT CAN NEVER FAIL A DEPLOY. This runs AFTER the deploy has verified and the safe-point is
    tagged. Every exception is caught and reported; a mail server having a bad day must not turn a
    good release into a failed one.
"""
import datetime
import json
import os
import sys

sys.path.insert(0, "/opt/shodan-skill/scripts")

MODELS = ["deepseek-3.2", "llama-4-maverick", "gemma-4-31B-it", "kimi-k2.6"]

PROMPT = """You are writing the release notes for cybergod.ai, an external cyber-risk and
compliance assessment platform. You are one of four models writing them independently; your text
will be shown beside the others, so write YOUR view rather than a consensus.

The reader is the operator who runs the platform and sells it. He wants to know, in this order:
what changed, whether anything needs watching, and what he can now tell a customer that he could
not tell them yesterday.

RULES:
- British English. No long dashes. No marketing adjectives.
- Do not invent anything. Every claim must come from the facts below. If the facts do not say
  whether something works, say that it is untested rather than guessing.
- No version numbers, dates, CVE identifiers or figures unless they appear in the facts.
- Be specific: name the actual files and behaviours, not "various improvements".
- If "Deploy result" is FAIL, LEAD with that: say what failed and what the operator should check.
  A failed release is the one he most needs to understand, not the one to gloss over.

Return STRICT JSON, no prose outside it:
{"headline": "one sentence, under 120 characters, what this release is",
 "summary": ["2 to 4 sentences of plain English for the operator"],
 "customer_value": ["0 to 3 items: what a customer or partner gets that they did not have before"],
 "watch": ["0 to 3 items: what could go wrong, or what is unproven and should be checked"]}

FACTS ABOUT THIS RELEASE:
%s
"""


def _ask(model, facts_text):
    """One model, one set of notes. Never raises: a model that cannot answer is recorded."""
    try:
        import enrich as E
    except Exception as e:                                  # pragma: no cover - import guard
        return {"model": model, "error": "enrich unavailable: %s" % e}
    try:
        raw, usage = E._call(PROMPT % facts_text, model=model, max_tokens=900, timeout=90)
        j = E._json(raw)
        if not isinstance(j, dict):
            raise ValueError("model returned %s, not an object" % type(j).__name__)
        clip = lambda xs, n: [str(x)[:400] for x in (xs if isinstance(xs, list) else [xs])][:n]  # noqa: E731
        return {"model": model,
                "headline": str(j.get("headline") or "")[:200],
                "summary": clip(j.get("summary") or [], 4),
                "customer_value": clip(j.get("customer_value") or [], 3),
                "watch": clip(j.get("watch") or [], 3),
                "tokens_out": (usage or {}).get("completion_tokens", 0)}
    except Exception as e:
        # A model that 429s or times out is DATA. The notes still go out with the other three,
        # and the reader is told how many actually answered.
        return {"model": model, "error": "%s: %s" % (type(e).__name__, e)}


def _facts_text(f):
    """The deterministic half, formatted for the model AND reproduced verbatim in the notes."""
    out = []
    out.append("Deploy result: %s" % f.get("result", "GO"))
    for x in (f.get("failures") or []):
        out.append("  FAILED CHECK: %s" % x)
    out.append("Commit: %s" % f.get("commit", "?"))
    out.append("Safe-point tag: %s" % f.get("tag", "?"))
    out.append("Message: %s" % f.get("message", ""))
    if f.get("staging"):
        out.append("Staging gate: %s" % f["staging"])
    if f.get("tests"):
        out.append("Tests: %s" % f["tests"])
    if f.get("commits"):
        out.append("\nCommits in this release:")
        out += ["  - %s" % c for c in f["commits"][:20]]
    if f.get("files"):
        out.append("\nFiles changed (%d):" % f.get("files_total", len(f["files"])))
        out += ["  %s" % x for x in f["files"][:40]]
    return "\n".join(out)


def compose(facts, reviews):
    """The message body. Facts first, then each model, then who did not answer."""
    answered = [r for r in reviews if not r.get("error")]
    L = []
    _res = str(facts.get("result", "GO")).upper()
    L.append("%s  RELEASE  %s" % ("\U00002705" if _res == "GO" else "\U0001f6a8 FAILED —",
                                  facts.get("tag", "?")))
    L.append("commit   %s" % facts.get("commit", "?"))
    L.append("when     %s UTC" % datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M"))
    if facts.get("message"):
        L.append("message  %s" % facts["message"])
    L.append("")
    if facts.get("staging"):
        L.append("Staging gate : %s" % facts["staging"])
    if facts.get("tests"):
        L.append("Tests        : %s" % facts["tests"])
    L.append("Deploy       : %s" % _res)
    for x in (facts.get("failures") or []):
        L.append("   FAILED     : %s" % x)
    L.append("Notes written by %d of %d models" % (len(answered), len(reviews)))
    L.append("=" * 68)

    for r in reviews:
        L.append("")
        if r.get("error"):
            L.append("[%s] did not answer: %s" % (r["model"], r["error"]))
            continue
        L.append("[%s] %s" % (r["model"], r.get("headline") or ""))
        for s in r.get("summary") or []:
            L.append("   %s" % s)
        for s in r.get("customer_value") or []:
            L.append("   + %s" % s)
        for s in r.get("watch") or []:
            L.append("   ! watch: %s" % s)

    L.append("")
    L.append("=" * 68)
    L.append("WHAT ACTUALLY CHANGED (deterministic, not model output)")
    L.append(_facts_text(facts))
    return "\n".join(L)


def main():
    try:
        facts = json.load(sys.stdin)
    except Exception as e:
        print("release_notes: no usable facts on stdin (%s)" % e)
        return 1

    reviews = [_ask(m, _facts_text(facts)) for m in MODELS]
    body = compose(facts, reviews)
    subject = "Release %s — %s" % (facts.get("tag", "?"),
                                   (facts.get("message") or "cybergod.ai")[:80])

    if "--print" in sys.argv:
        print(body)
        return 0

    sent_mail = sent_tg = False
    try:
        from . import notify
        # Independent channels on purpose: the Gmail API being unavailable must not also silence
        # Telegram, and vice versa. notify.both() already enforces that separation.
        sent_tg = bool(notify.telegram("*%s*\n\n```\n%s\n```" % (subject, body[:3200])))
        sent_mail = bool(notify.email("[cybergod.ai] " + subject, body))
    except Exception as e:
        print("release_notes: delivery failed: %s: %s" % (type(e).__name__, e))

    answered = len([r for r in reviews if not r.get("error")])
    print("release_notes: %d/%d models answered | telegram=%s | email=%s"
          % (answered, len(MODELS), sent_tg, sent_mail))
    # Deliberately 0 even on a delivery failure. This runs after a VERIFIED deploy; a mail server
    # having a bad day must never turn a good release into a failed one. The line above is the
    # honest record of what happened.
    return 0


if __name__ == "__main__":
    sys.exit(main())
