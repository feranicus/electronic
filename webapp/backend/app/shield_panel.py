"""shield_panel.py — the SAME four models, now reviewing what the shield did. Out of band.

STANDING RULE, applied here for the third time (staging gate, release notes, now defence):
`deepseek-3.2 · llama-4-maverick · gemma-4-31B-it · kimi-k2.6` -- two soldiers, two auditors, four
vendors. Four vendors means a provider-wide 429 cannot silence the panel, and a model that has
misread an incident is contradicted by three others instead of believed.

WHAT IT DOES, in order:
  1. reads the deterministic evidence: the shield's own state plus the recent http/security events;
  2. asks each model, independently, for a root-cause narrative and (optionally) threshold changes;
  3. requires CONSENSUS -- at least 3 of 4 must propose the same direction for a key before it
     moves at all, and the value applied is the MEDIAN of what they proposed, never the boldest;
  4. clamps everything through shield_tuning.propose(), which enforces the committed bounds;
  5. sends one incident report to Telegram and email through the Gmail API gateway.

WHAT IT CANNOT DO. It is not in the request path, so it can never slow or break a request. It
cannot block or unblock an address -- that is deterministic and stays that way. It cannot change
the bounds, the blast cap, the allowlist or the kill switch. The only mutable surface is six
integers inside ranges the operator committed to.

RUN IT:  docker exec colt-web python3 -m app.shield_panel --print     (no delivery, no tuning)
         docker exec colt-web python3 -m app.shield_panel             (tune + deliver)
"""
import json
import os
import sys

sys.path.insert(0, "/opt/shodan-skill/scripts")

MODELS = ["deepseek-3.2", "llama-4-maverick", "gemma-4-31B-it", "kimi-k2.6"]
QUORUM = 3          # of 4 must agree on a direction before any threshold moves

PROMPT = """You are one of four independent models reviewing the ACTIVE DEFENCE of cybergod.ai,
a public web application. You will be shown deterministic evidence only. Three other models are
reviewing the same evidence separately; write YOUR reading, not a consensus.

The defence is deterministic code. You do NOT block anything and you cannot. Your job is:
(a) explain what happened, in plain British English, to an operator who will read it on a phone;
(b) say whether the current thresholds served him well;
(c) optionally propose new values for the tunable integers.

HARD RULES:
- Do not invent an IP, a path, a count or a time that is not in the evidence.
- If the evidence does not support a change, propose NO changes. "Leave it alone" is a real answer
  and is often the right one.
- A threshold that is too aggressive locks out real visitors. A threshold that is too slack lets a
  scanner enumerate the site. Say which risk you are trading against which.
- You may only propose these keys, and only inside the stated bounds: %s

Return STRICT JSON, nothing outside it:
{"headline": "one sentence under 120 characters",
 "assessment": ["2 to 4 sentences: what happened and whether the response was proportionate"],
 "attacker": ["0 to 3 items: what the actor appears to be doing, and the MITRE ATT&CK technique"],
 "propose": {"key": integer, ...},
 "why": "one sentence justifying the proposal, or why you propose nothing"}

EVIDENCE:
%s
"""


def _evidence():
    """Deterministic facts only. No interpretation, no model output."""
    from . import shield
    ev = {"shield": shield.state()}
    log = os.environ.get("EVENTS_LOG", "/var/log/colt/events.log")
    hostile, seen = [], 0
    try:
        with open(log, encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()[-4000:]
        for ln in lines:
            try:
                j = json.loads(ln)
            except Exception:
                continue
            e = j.get("evt")
            if e in ("shield_block", "shield_would_block", "shield_refused", "security_alert",
                     "shield_tuned"):
                hostile.append({k: j.get(k) for k in
                                ("evt", "ts", "ip", "score", "hits", "rule", "seconds", "reason")
                                if j.get(k) is not None})
            if e == "http":
                seen += 1
    except Exception as exc:
        ev["events_error"] = str(exc)
    ev["recent_defence_events"] = hostile[-40:]
    ev["http_events_scanned"] = seen
    return ev


def _ask(model, evidence_text, bounds_text):
    try:
        import enrich as E
    except Exception as e:                                    # pragma: no cover
        return {"model": model, "error": "enrich unavailable: %s" % e}
    try:
        raw, usage = E._call(PROMPT % (bounds_text, evidence_text), model=model,
                             max_tokens=900, timeout=90)
        j = E._json(raw)
        if not isinstance(j, dict):
            raise ValueError("model returned %s, not an object" % type(j).__name__)
        prop = j.get("propose") if isinstance(j.get("propose"), dict) else {}
        clean = {}
        for k, v in prop.items():
            try:
                clean[str(k)] = int(v)
            except Exception:
                continue
        clip = lambda xs, n: [str(x)[:300] for x in (xs if isinstance(xs, list) else [xs])][:n]  # noqa: E731
        return {"model": model, "headline": str(j.get("headline") or "")[:200],
                "assessment": clip(j.get("assessment") or [], 4),
                "attacker": clip(j.get("attacker") or [], 3),
                "propose": clean, "why": str(j.get("why") or "")[:300],
                "tokens_out": (usage or {}).get("completion_tokens", 0)}
    except Exception as e:
        return {"model": model, "error": "%s: %s" % (type(e).__name__, e)}


def consensus(reviews, current):
    """A key moves only if >=QUORUM models push it the SAME WAY. The applied value is the MEDIAN.

    Taking the median rather than the mean or the extreme is the point: one model arguing for a
    drastic change is outvoted by three moderate ones, and a single outlier cannot drag the result.
    Agreement on DIRECTION is required first, so three models saying "raise it" and one saying
    "lower it" still raises it, while a two-two split changes nothing at all.
    """
    agreed, notes = {}, []
    keys = {k for r in reviews for k in (r.get("propose") or {})}
    for k in sorted(keys):
        cur = current.get(k)
        if cur is None:
            notes.append("%s: not a tunable key" % k)
            continue
        up = [r["propose"][k] for r in reviews if (r.get("propose") or {}).get(k, cur) > cur]
        dn = [r["propose"][k] for r in reviews if (r.get("propose") or {}).get(k, cur) < cur]
        side = up if len(up) >= QUORUM else (dn if len(dn) >= QUORUM else [])
        if not side:
            notes.append("%s: only %d up / %d down - below the quorum of %d, unchanged"
                         % (k, len(up), len(dn), QUORUM))
            continue
        s = sorted(side)
        agreed[k] = s[len(s) // 2]
    return agreed, notes


def compose(ev, reviews, applied, rejected, notes):
    answered = [r for r in reviews if not r.get("error")]
    sh = ev.get("shield", {})
    L = ["SHIELD REVIEW — cybergod.ai",
         "blocked now : %d" % len(sh.get("blocked") or {}),
         "watching    : %d IP(s) | seen in the last hour: %d"
         % (sh.get("watching", 0), sh.get("seen_ips_1h", 0)),
         "enforcing   : %s" % sh.get("enforcing"),
         "thresholds  : %s" % json.dumps(sh.get("config") or {}),
         "reviewed by %d of %d models" % (len(answered), len(reviews)),
         "=" * 68]
    for r in reviews:
        L.append("")
        if r.get("error"):
            L.append("[%s] did not answer: %s" % (r["model"], r["error"]))
            continue
        L.append("[%s] %s" % (r["model"], r.get("headline") or ""))
        for s in r.get("assessment") or []:
            L.append("   %s" % s)
        for s in r.get("attacker") or []:
            L.append("   * %s" % s)
        if r.get("propose"):
            L.append("   proposes: %s — %s" % (json.dumps(r["propose"]), r.get("why") or ""))
        else:
            L.append("   proposes NO change — %s" % (r.get("why") or ""))
    L += ["", "=" * 68, "WHAT ACTUALLY CHANGED (deterministic, not model output)"]
    L.append("applied : %s" % (json.dumps(applied) if applied else "nothing"))
    for n in notes + rejected:
        L.append("   refused: %s" % n)
    L.append("")
    L.append("Bounds are committed in shield.py and cannot be changed by any model.")
    L.append("Blocking itself is deterministic; the panel never blocks or unblocks an address.")
    return "\n".join(L)


def main():
    from . import shield
    ev = _evidence()
    bounds = json.dumps({k: list(v) for k, v in shield.BOUNDS.items()})
    reviews = [_ask(m, json.dumps(ev, indent=2)[:12000], bounds) for m in MODELS]
    current = {k: shield.cfg(k) for k in shield.BOUNDS}
    agreed, notes = consensus(reviews, current)

    applied, rejected = {}, []
    if agreed and "--print" not in sys.argv:
        from . import shield_tuning
        applied, rejected = shield_tuning.propose(
            agreed, "shield panel consensus",
            [r["model"] for r in reviews if not r.get("error")])

    body = compose(ev, reviews, applied, rejected, notes)
    if "--print" in sys.argv:
        print(body)
        return 0
    sent_tg = sent_mail = False
    try:
        from . import notify
        sent_tg = bool(notify.telegram("*Shield review — cybergod.ai*\n\n```\n%s\n```" % body[:3200]))
        sent_mail = bool(notify.email("[cybergod.ai] shield review", body))
    except Exception as e:
        print("shield_panel: delivery failed: %s: %s" % (type(e).__name__, e))
    print("shield_panel: %d/%d answered | applied=%s | telegram=%s | email=%s"
          % (len([r for r in reviews if not r.get("error")]), len(MODELS),
             json.dumps(applied), sent_tg, sent_mail))
    return 0


if __name__ == "__main__":
    sys.exit(main())
