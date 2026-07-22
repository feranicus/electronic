#!/usr/bin/env python3
"""
audit_fp.py — independent false-positive audit with a DIFFERENT vendor's model.

A second opinion on the findings, by a model from a different vendor than the one that authored the
decks (a 429/blind-spot is provider-wide, so the auditor must not share a failure domain with the
author). It reviews every finding + its evidence hosts against the target's identity and flags any
that look like they belong to a THIRD PARTY (client / hoster / CDN tenant) rather than the target —
the skon.de / bibeltv.de failure mode.

    python audit_fp.py findings.json            # prints a JSON verdict, exit 0
    python audit_fp.py findings.json --apply     # also REWRITE findings.json with flagged findings removed

Auto-fix (`--apply`): flagged findings are dropped and the summary counts recomputed, so the decks
rebuilt afterwards are clean. Conservative: only drops a finding the auditor marks false with a
reason AND that the deterministic owned-host check agrees is off-estate. Never raises.
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))

# vendor of a model id, so we can pick an auditor from a DIFFERENT vendor than the author.
def _vendor(m):
    m = (m or "").lower()
    for v in ("deepseek", "llama", "gemma", "google", "glm", "zhipu", "kimi", "moonshot",
              "qwen", "mistral", "minimax", "nvidia", "gpt-oss", "openai"):
        if v in m:
            return {"google": "google", "gemma": "google", "glm": "zhipu", "zhipu": "zhipu",
                    "kimi": "moonshot", "moonshot": "moonshot"}.get(v, v)
    return "other"


PROMPT = """You are an INDEPENDENT reviewer auditing a cyber attack-surface report for FALSE POSITIVES.
The report is about ONE target company. A false positive is any finding whose evidence host does NOT
belong to the target — e.g. a client's white-label site, a shared-hoster tenant, a CDN edge, or an
unrelated look-alike domain. Be strict: a host only belongs to the target if it is on the target's
own netblock/ASN, resolves from the target's own domain, or presents the target's certificate.

Return ONLY strict JSON:
{"verdict":"clean|dirty",
 "false_positives":[{"id":"<finding id>","reason":"<why this host is not the target's>"}],
 "notes":"<one line>"}

TARGET: %(company)s
KNOWN-OWNED identity: domains=%(domains)s · brand_tokens=%(tokens)s · owned_asns=%(asns)s · cert_org=%(certorg)s
RELATED-BUT-NOT-OWNED (client/third-party apexes already excluded upstream): %(unscoped)s

FINDINGS (id · sev · title · evidence hosts):
%(findings)s
"""


def _slim(fj):
    rows = []
    for f in (fj.get("findings") or []):
        ev = " ; ".join(map(str, (f.get("evidence") or [])[:4]))
        rows.append("%s · %s · %s · %s" % (f.get("id", ""), f.get("sev", ""), f.get("title", ""), ev))
    return "\n".join(rows)


def audit(fj):
    tgt = fj.get("target") or {}
    ident = tgt.get("ident") or {}
    company = tgt.get("company", "Target")
    prompt = PROMPT % {
        "company": company,
        "domains": ",".join(ident.get("domains", []) or tgt.get("domains", []))[:300],
        "tokens": ",".join(ident.get("brand_tokens", []))[:200],
        "asns": ",".join(map(str, ident.get("asns", [])))[:120],
        "certog": ident.get("cert_org_seen", ""),
        "certorg": ident.get("cert_org_seen", ""),
        "unscoped": ",".join(ident.get("related_unscoped", []))[:400],
        "findings": _slim(fj),
    }
    try:
        sys.path.insert(0, HERE)
        import enrich as E
        chain = E._chain() or ["gemma-4-31B-it"]
        author_vendor = _vendor(chain[0])
        # pick the first model from a DIFFERENT vendor
        auditor = os.environ.get("FP_AUDIT_MODEL")
        if not auditor:
            auditor = next((m for m in chain if _vendor(m) != author_vendor), None) or \
                      ("llama-4-maverick" if author_vendor != "llama" else "deepseek-3.2")
        txt, usage = E._call(prompt, model=auditor, timeout=int(os.environ.get("FP_AUDIT_TIMEOUT", "90")))
        j = E._json(txt) or {}
        fps = [x for x in (j.get("false_positives") or []) if isinstance(x, dict) and x.get("id")]
        print("[fp-audit] auditor=%s (author=%s) verdict=%s flagged=%d"
              % (auditor, chain[0], j.get("verdict", "?"), len(fps)), file=sys.stderr)
        return {"auditor": auditor, "verdict": j.get("verdict", "clean"),
                "false_positives": fps, "notes": j.get("notes", "")}
    except Exception as e:
        print("[fp-audit] failed (%s) — no findings dropped" % type(e).__name__, file=sys.stderr)
        return {"auditor": None, "verdict": "unaudited", "false_positives": [], "notes": str(e)[:120]}


import re as _re


def _host_is_off_estate(ev, owned):
    """True only if EVERY IP/host in this evidence is provably NOT the target's.

    The auditor (an LLM) over-rejects hosts on shared hosting (Google/M365) — it destroyed the
    skon.de deck by flagging every legit S-KON host. So a drop is only applied when the DETERMINISTIC
    owned-set agrees the host is off-estate: not a pinned IP, not under an owned domain, no brand
    token. Fail closed toward KEEPING the finding — a missing owned-set means we cannot corroborate,
    so we do not drop."""
    pins = set(owned.get("pinned") or [])
    doms = [str(d).lower().lstrip(".") for d in (owned.get("domains") or [])]
    toks = [t for t in (owned.get("brand_tokens") or []) if t]
    if not (pins or doms or toks):
        return False                       # no ownership data -> never corroborated -> keep
    blob = " ".join(str(e) for e in (ev or [])).lower()
    ips = _re.findall(r"\d{1,3}(?:\.\d{1,3}){3}", blob)
    for ip in ips:
        if ip in pins:
            return False                   # a pinned host is ours by definition
    if any(d and d in blob for d in doms):
        return False                       # references an owned domain
    if any(t in _re.sub(r"[^a-z0-9]", "", blob) for t in toks):
        return False                       # carries a brand token
    # nothing tied it to the target — but only call it off-estate if there was SOMETHING to check
    return bool(ips or "." in blob)


def apply_fixes(fj, fps):
    """Drop flagged findings — but only those the OWNED-SET corroborates as off-estate, and NEVER
    into an empty or decimated deck. Returns (new_fj, dropped_ids, refused_ids)."""
    owned = (fj.get("target") or {}).get("owned") or {}
    all_f = fj.get("findings") or []
    flagged = {x["id"] for x in fps}
    # corroborate each flag against the deterministic owned-set
    drop_ids, refused = [], []
    for f in all_f:
        if f.get("id") in flagged:
            (drop_ids if _host_is_off_estate(f.get("evidence"), owned) else refused).append(f.get("id"))
    # HARD GUARDRAILS: an audit must never empty or gut the deck. If it would drop everything, or
    # more than 40% of findings, refuse the whole auto-fix and keep them all (flag-only).
    if drop_ids and (len(drop_ids) >= len(all_f) or len(drop_ids) > max(1, int(0.4 * len(all_f)))):
        return fj, [], list(flagged)       # too aggressive -> keep everything, report as refused
    if not drop_ids:
        return fj, [], list(flagged)
    kept = [f for f in all_f if f.get("id") not in set(drop_ids)]
    fj["findings"] = kept
    sm = fj.setdefault("summary", {})
    for k in ("critical", "high", "medium", "low"):
        sm[k] = sum(1 for f in kept if str(f.get("sev", "")).lower() == k)
    sm["audited_false_positives"] = sm.get("audited_false_positives", 0) + len(drop_ids)
    return fj, drop_ids, refused


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("findings")
    ap.add_argument("--apply", action="store_true", help="rewrite findings.json with FPs removed")
    a = ap.parse_args()
    try:
        fj = json.load(open(a.findings, encoding="utf-8"))
    except Exception as e:
        print(json.dumps({"verdict": "error", "error": str(e)})); return
    res = audit(fj)
    res["dropped"] = []
    res["refused"] = []
    if a.apply and res["false_positives"]:
        fj, dropped, refused = apply_fixes(fj, res["false_positives"])
        if dropped:
            json.dump(fj, open(a.findings, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        res["dropped"] = dropped
        res["refused"] = refused
        if refused and not dropped:
            print("[fp-audit] REFUSED all %d flag(s): not corroborated by the owned-set, or would "
                  "gut the deck — findings kept unchanged." % len(refused), file=sys.stderr)
    print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()
