#!/usr/bin/env python3
"""
quorum.py — 2 soldiers + 2 auditors review a staging validation run and write the verdict digest.

RUNS INSIDE colt-web ON THE STAGING DROPLET. That is not incidental: OPENAI_API_KEY lives in the
droplet's env file, never on the operator's PC, so any script that needs inference has to execute
where the key already is. Same pattern as model_probe.py.

    docker exec -i colt-web python3 /opt/stagegate/quorum.py < evidence.json

CONTRACT
    stdin  : evidence JSON  {host, checks:[{name, ok, detail}], reboot:{...}, diff:[...], ...}
    stdout : verdict JSON   {gate, models:[{role,model,verdict,reasons,risks}], digest, ...}

WHO DECIDES WHAT — this is the load-bearing design decision
-----------------------------------------------------------
`gate` is computed from the DETERMINISTIC checks alone. The models never set it. They read the same
evidence and write the REASONING, the risk digest and any objection worth a human's attention.

That is operating principle 5 ("the LLM assists, it does not decide side effects"), and it is not
timidity — it is the only arrangement that fails safely in both directions:
  * a 429, an outage or a truncated answer cannot block a correct release;
  * a hallucinated objection cannot stall a good deploy;
  * and a model that is feeling agreeable cannot wave through a container that is not running.
A model's dissent is surfaced loudly (`concerns`) and travels in the email and the Telegram
message, so a human sees it — it just does not silently flip a bit.

WHY FOUR, IN TWO ROLES
  soldiers  — "did this deploy work?"  Operational reading of the checks.
  auditors  — "what did everyone miss?" Adversarial reading, explicitly asked to look for the
              failure mode nobody listed. Different prompt, different question.
Both roles are filled from DIFFERENT VENDORS, because a 429 or a blind spot is provider-wide —
the same reason audit_fp.py refuses to let a model audit itself.
"""
import json
import os
import sys

sys.path.insert(0, "/opt/shodan-skill/scripts")

try:
    import enrich as E
except Exception as _e:                                    # pragma: no cover
    E = None
    _IMPORT_ERR = str(_e)

# 2 soldiers + 2 auditors, one per vendor. Order mirrors enrich._FALLBACKS, which is chosen from
# MEASURED evidence (compare_models.py on the real prompt), not from taste.
SOLDIERS = ["deepseek-3.2", "llama-4-maverick"]
AUDITORS = ["gemma-4-31B-it", "kimi-k2.6"]

SOLDIER_PROMPT = """You are a release engineer reviewing a STAGING validation run before the change
is promoted to production. The production host serves several live customer domains from ONE shared
reverse proxy, so a bad promotion takes every site down at once.

Answer ONLY from the evidence below. Never invent a check, a container name, a version or a number
that is not present. If the evidence does not cover something, say so plainly.

Return STRICT JSON, no prose outside it:
{"verdict":"go"|"no-go"|"unsure",
 "reasons":["<= 3 short factual sentences, each citing a specific check by name>"],
 "risks":["<= 3 concrete risks this change carries into production, or [] if none are evidenced>"]}

EVIDENCE:
%s"""

AUDITOR_PROMPT = """You are an independent auditor. Two other reviewers have already said whether
this staging run looks healthy. Your job is the opposite one: find what the checks DO NOT cover.

Look for: a check that passed for the wrong reason; a service that is "running" but was never
exercised; something that only breaks after a reboot, under load, or on the next restart; config
that validated but was never actually re-read by the process; anything about the SHARED reverse
proxy, since a fault there takes every domain down together.

Answer ONLY from the evidence. Do not invent findings — "no gap evidenced" is a valid and useful
answer, and is much better than a plausible-sounding guess.

Return STRICT JSON, no prose outside it:
{"verdict":"go"|"no-go"|"unsure",
 "reasons":["<= 3 sentences on what the evidence does and does not prove>"],
 "risks":["<= 3 gaps in the CHECKS themselves, or [] if none"]}

EVIDENCE:
%s"""


def _ask(model, prompt):
    """One model, one answer. Never raises: a reviewer that cannot answer is recorded, not fatal."""
    if E is None:
        return {"model": model, "verdict": "unsure", "reasons": ["enrich unavailable: %s" % _IMPORT_ERR],
                "risks": [], "error": "import"}
    try:
        raw, usage = E._call(prompt, model=model, max_tokens=900, timeout=90)
        j = E._json(raw)
        if not isinstance(j, dict):
            raise ValueError("model returned %s, not an object" % type(j).__name__)
        v = str(j.get("verdict", "unsure")).lower().strip()
        if v not in ("go", "no-go", "unsure"):
            v = "unsure"
        clip = lambda xs: [str(x)[:400] for x in (xs if isinstance(xs, list) else [xs])][:3]  # noqa: E731
        return {"model": model, "verdict": v,
                "reasons": clip(j.get("reasons") or []),
                "risks": clip(j.get("risks") or []),
                "tokens_out": (usage or {}).get("completion_tokens", 0)}
    except Exception as e:
        # A reviewer that 429s or times out is DATA, not a failure of the release. Recorded so the
        # digest is honest about how many opinions it actually collected.
        return {"model": model, "verdict": "unsure", "reasons": ["did not answer: %s" % e],
                "risks": [], "error": type(e).__name__}


def main():
    ev = json.load(sys.stdin)
    checks = ev.get("checks") or []
    failed = [c for c in checks if not c.get("ok")]

    # THE GATE. Deterministic, computed here so the same rule is visible in the artifact the
    # operator receives, rather than living only in the caller.
    gate = "GO" if (checks and not failed) else "NO-GO"

    slim = json.dumps(ev, indent=1)[:9000]     # bound the prompt; latency scales with prompt size
    reviews = []
    for m in SOLDIERS:
        reviews.append(dict(role="soldier", **_ask(m, SOLDIER_PROMPT % slim)))
    for m in AUDITORS:
        reviews.append(dict(role="auditor", **_ask(m, AUDITOR_PROMPT % slim)))

    answered = [r for r in reviews if not r.get("error")]
    dissent = [r for r in answered if r["verdict"] == "no-go"]

    lines = ["STAGING VALIDATION — %s" % ev.get("host", "?"),
             "",
             "GATE: %s   (%d/%d deterministic checks passed)"
             % (gate, len(checks) - len(failed), len(checks))]
    if failed:
        lines += ["", "FAILED CHECKS:"] + ["  x %s — %s" % (c.get("name"), str(c.get("detail"))[:160])
                                           for c in failed]
    lines += ["", "REVIEW PANEL (%d of 4 answered):" % len(answered)]
    for r in reviews:
        lines.append("  [%s] %-18s %s" % (r["role"][:7], r["model"], r["verdict"].upper()))
        for x in r["reasons"]:
            lines.append("        . %s" % x)
        for x in r["risks"]:
            lines.append("        ! risk: %s" % x)
    if dissent:
        lines += ["", "NOTE: %d reviewer(s) said NO-GO. The gate is decided by the deterministic"
                      % len(dissent),
                  "checks above, so this did not block the promotion — but read it before you"
                  " promote again."]
    if len(answered) < 2:
        lines += ["", "NOTE: fewer than two reviewers answered (quota or outage). The digest is"
                      " thin; the gate is unaffected."]

    print(json.dumps({"gate": gate, "checks_total": len(checks), "checks_failed": len(failed),
                      "failed": failed, "models": reviews,
                      "answered": len(answered), "dissent": len(dissent),
                      "digest": "\n".join(lines)}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
