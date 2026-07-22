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


def _pick_auditor(author, chain):
    """Return a model GUARANTEED to differ from the deck author — different vendor if possible,
    but at minimum a different model id. An audit by the same model that wrote the decks is not an
    independent second opinion; it shares every blind spot and failure mode."""
    forced = os.environ.get("FP_AUDIT_MODEL")
    if forced and forced != author:
        return forced                                  # operator override (only if not the author)
    av = _vendor(author)
    # 1) prefer a chain model from a DIFFERENT vendor than the author
    for m in chain:
        if m != author and _vendor(m) != av:
            return m
    # 2) else any chain model that is at least a different id
    for m in chain:
        if m != author:
            return m
    # 3) last resort: a hard-coded alternative from another vendor
    for m in ("deepseek-3.2", "llama-4-maverick", "gemma-4-31B-it", "openai-gpt-oss-120b"):
        if m != author and _vendor(m) != av:
            return m
    return "deepseek-3.2" if author != "deepseek-3.2" else "llama-4-maverick"


def audit(fj):
    tgt = fj.get("target") or {}
    owned = tgt.get("owned") or {}                     # written by run_assessment (real ownership data)
    company = tgt.get("company", "Target")
    prompt = PROMPT % {
        "company": company,
        "domains": ",".join(owned.get("domains", []) or tgt.get("domains", []))[:300],
        "tokens": ",".join(owned.get("brand_tokens", []))[:200],
        "asns": ",".join(map(str, owned.get("asns", [])))[:120],
        "certorg": owned.get("cert_org", "") or "",
        "unscoped": ",".join(owned.get("related_unscoped", []))[:400],
        "findings": _slim(fj),
    }
    try:
        sys.path.insert(0, HERE)
        import enrich as E
        chain = E._chain() or ["gemma-4-31B-it"]
        # the ACTUAL deck author — the model that WON enrichment after any failover, not the chain
        # head. run_assessment records it as target.qwen.model.
        author = (tgt.get("qwen") or {}).get("model") or chain[0]
        auditor = _pick_auditor(author, chain)
        if auditor == author:                          # must never happen — refuse rather than fake independence
            print("[fp-audit] could not find a model different from the author %r — skipping audit"
                  % author, file=sys.stderr)
            return {"auditor": None, "author": author, "verdict": "unaudited",
                    "false_positives": [], "notes": "no distinct auditor available"}
        txt, usage = E._call(prompt, model=auditor, timeout=int(os.environ.get("FP_AUDIT_TIMEOUT", "90")))
        j = E._json(txt) or {}
        fps = [x for x in (j.get("false_positives") or []) if isinstance(x, dict) and x.get("id")]
        print("[fp-audit] auditor=%s (vendor=%s) vs deck author=%s (vendor=%s) verdict=%s flagged=%d"
              % (auditor, _vendor(auditor), author, _vendor(author), j.get("verdict", "?"), len(fps)),
              file=sys.stderr)
        return {"auditor": auditor, "author": author, "verdict": j.get("verdict", "clean"),
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
    # scanned_ips = every host recon's ownership gate already vetted and KEPT. Recon is the ownership
    # authority; the LLM auditor is a backstop. A host recon scanned is owned by definition, so the
    # auditor may NOT drop it (this is what wrongly deleted skon.de's real nginx-CVE critical).
    vetted = set(owned.get("scanned_ips") or [])
    pins = set(owned.get("pinned") or [])
    doms = [str(d).lower().lstrip(".") for d in (owned.get("domains") or [])]
    toks = [t for t in (owned.get("brand_tokens") or []) if t]
    if not (vetted or pins or doms or toks):
        return False                       # no ownership data -> never corroborated -> keep
    blob = " ".join(str(e) for e in (ev or [])).lower()
    ips = _re.findall(r"\d{1,3}(?:\.\d{1,3}){3}", blob)
    for ip in ips:
        if ip in vetted or ip in pins:
            return False                   # recon scanned/pinned this host -> ours by definition
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
