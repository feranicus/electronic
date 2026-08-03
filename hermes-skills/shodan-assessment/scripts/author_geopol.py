#!/usr/bin/env python3
"""
author_geopol.py — write the per-company GEOPOL HTML content with a DO model, then render it.

Phase 2 of the pipeline (the decks are phase 1). Uses the SAME DigitalOcean inference the decks use
(enrich._call over OPENAI_BASE_URL + OPENAI_API_KEY from .env) — Gemma / Llama / DeepSeek — to author
Scene 01 (exposed estate) and Scene 02 (who is coming) from findings.json + geopol.json, then calls
build_geopol_html.js to drop them into the fixed animated shell (skeleton.html).

    python author_geopol.py findings.json geopol.json <Company>_Report.html [--company NAME]

Model: $GEOPOL_HTML_MODEL, else the first of enrich._chain() (Gemma head). The LLM only writes the
two bespoke scenes as small JSON; the exact CSS + canvas animations + defense scenes are fixed in
the shell, so a weak model can never break the layout. Deterministic fallback if the model fails, so
this NEVER blocks the run.

LANGUAGE ($DECK_LANG, set by run_assessment.py):
  · the AUTHORED scenes get enrich.lang_block(lang) appended to the prompt — the ONE registry, so a
    new language never means a new `if de/ru` here;
  · the DETERMINISTIC fallback reads its strings from geopol_html/i18n/<lang>.json, because a model
    outage must not silently ship English scenes into a Russian report — the safety net has to be
    correct in the same language as the thing it is standing in for;
  · the fixed shell is localised by build_geopol_html.js from the SAME dictionary file.
English keeps the literals inline, so an English run is byte-for-byte what it was.
"""
import argparse, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
LANG = (os.environ.get("DECK_LANG") or "en").strip().lower()[:2] or "en"


def _load(p):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return {}


def _pack(lang):
    """The skeleton dictionary for `lang` ({} for English or a language with no file)."""
    if not lang or lang == "en":
        return {}
    p = os.path.join(HERE, "geopol_html", "i18n", lang + ".json")
    if not os.path.exists(p):
        print("[geopol-html] no i18n/%s.json — falling back to English content" % lang, file=sys.stderr)
        return {}
    return _load(p)


_FALLBACK = (_pack(LANG).get("fallback") or {})


def _t(key, english):
    """Deterministic-fallback string. The ENGLISH text stays here as the default, so the English
    path never depends on a dictionary existing and cannot drift from what it rendered before."""
    v = _FALLBACK.get(key)
    return v if isinstance(v, str) and v else english


PROMPT = """You are a cyber pre-sales analyst writing the two opening scenes of an animated
GEOPOL threat report for %(company)s. Return ONLY strict JSON, no prose, no markdown.

Use the REAL data below. Never invent hosts, IPs, CVEs, ASNs or breaches that are not present.
Inline emphasis tokens allowed in h1/sub/caption: {hl}teal highlight{/hl}, {ink}bright bold{/ink},
{red}red bold{/red}, {amber}amber bold{/amber}. Keep each sub to 2-4 sentences, dense and specific
(name the exact exposed host/port and ASN).%(lang_note)s

Return this exact shape:
{
 "scene1": {
   "h1": "<one line, <=9 words, one {hl}..{/hl} span> e.g. A VPN edge on {hl}the carrier backbone{/hl}.",
   "sub": "<2-4 sentences on the verified estate: host count, the hosting ASNs, and the single most
           important exposed door — name it with {red}host:port{/red} and its ASN>",
   "stats": [ {"n":"<int>","l":"Verified exposed hosts"}, {"n":"<int>","l":"Hosting ASNs"},
              {"n":"<int>","l":"<the priority exposure>","bad":true},
              {"n":"0","l":"Behind managed edge","bad":true} ],
   "legend": [ {"c":"teal","t":"<owned backbone/ASN>"}, {"c":"amber","t":"<hosters>"},
               {"c":"red","t":"Priority finding"}, {"c":"faint","t":"Behind managed edge (0)"} ],
   "caption": "<one line listing the top 3-4 real findings as host:port — role — note>"
 },
 "scene2": {
   "h1": "<one line characterising the threat, one {hl}..{/hl}> e.g. Symbolic and {hl}opportunistic{/hl}, not espionage.",
   "sub": "<2-4 sentences: what kind of target this is and which real threat actors it draws, from the GEOPOL data>",
   "legend": [ {"c":"teal","t":"<actor 1 — vector>"}, {"c":"violet","t":"<actor 2>"},
               {"c":"orange","t":"<actor 3>"}, {"c":"red","t":"<the KEV/edge finding>"} ],
   "caption": "<one line: most likely path, most damaging path, cheapest break — grounded in the findings>"
 }
}

REAL DATA
company: %(company)s
scope: %(scope)s
findings (severity · id · title · evidence): %(findings)s
asset inventory: %(inv)s
geopol verdict: %(verdict)s
geopol actors: %(actors)s
geopol sector: %(sector)s
"""


def _slim_findings(fj):
    out = []
    for f in (fj.get("findings") or [])[:12]:
        ev = (f.get("evidence") or [])[:2]
        out.append("%s %s: %s | %s" % (f.get("sev", ""), f.get("id", ""), f.get("title", ""), " ; ".join(map(str, ev))))
    return "\n".join(out)


def _slim_actors(gj):
    out = []
    for a in (gj.get("actors") or [])[:6]:
        out.append("%s (%s) — %s" % (a.get("title") or a.get("sponsor") or "?", a.get("band") or a.get("tier") or "",
                                     (a.get("what") or "")[:120]))
    return "\n".join(out)


def deterministic(fj, gj, company):
    """Always-correct content straight from the data. The safety net when the model fails."""
    sm = fj.get("summary") or {}
    tgt = fj.get("target") or {}
    hosts = sm.get("hosts") or sm.get("unique_ips") or (tgt.get("inventory") or {}).get("hosts") or 0
    asns = sm.get("asns") or (tgt.get("inventory") or {}).get("asns") or 0
    fnd = fj.get("findings") or []
    top = fnd[0] if fnd else {}
    ev0 = (top.get("evidence") or [""])[0]
    crit_high = [f for f in fnd if str(f.get("sev", "")).upper() in ("CRITICAL", "HIGH")]
    cap1 = _t("scene1.caption.prefix", "Findings: ") + " · ".join(
        ("%s — %s" % ((f.get("evidence") or [""])[0], f.get("title", "")))[:70] for f in crit_high[:3]) if crit_high else \
        _t("scene1.caption.empty", "A small, contained internet-facing estate.")
    actors = gj.get("actors") or []
    leg2 = [{"c": c, "t": (a.get("title") or a.get("sponsor") or _t("Threat actor", "Threat actor"))}
            for c, a in zip(("teal", "violet", "orange"), actors[:3])]
    if crit_high:
        leg2.append({"c": "red", "t": (crit_high[0].get("title") or _t("Priority finding", "Priority finding"))[:44]})
    # scene-3 EXPOSURES come straight from the real findings (host:port — title), so the vectors map
    # shows the target's actual estate, never a template's. vectors/impacts are exposure-class generic.
    exposures = []
    for f in (crit_high + [x for x in fnd if x not in crit_high])[:6]:
        ev = (f.get("evidence") or [""])[0]
        host = str(ev).split()[0] if ev else ""
        exposures.append((host + " — " + (f.get("title") or "")).strip(" —")[:34] or (f.get("title") or "")[:34])
    actor_defs = []
    for c, a in zip(("violet", "amber", "teal", "red", "orange", "mint"), actors[:6]):
        actor_defs.append({"name": (a.get("title") or a.get("sponsor") or _t("Threat actor", "Threat actor"))[:22],
                           "c": c, "method": (a.get("eyebrow") or a.get("band") or "")[:26]})
    # The h1/sub are %-format TEMPLATES, not concatenations, so a language whose word order differs
    # (Russian puts the company after the noun) can restate the whole sentence in the dictionary.
    # Named placeholders, never positional: a translator must be free to reorder them.
    fmt = {"company": company, "n": len(crit_high), "hosts": hosts, "asns": asns, "ev": ev0}
    return {
        "company": company,
        "scene3": {
            "vectors": [{"t": _t("Volumetric DDoS", "Volumetric DDoS"), "c": "teal"},
                        {"t": _t("Remote-access exploit", "Remote-access exploit"), "c": "red"},
                        {"t": _t("Credential stuffing", "Credential stuffing"), "c": "amber"},
                        {"t": _t("Web-app exploit", "Web-app exploit"), "c": "orange"},
                        {"t": _t("Ransomware deploy", "Ransomware deploy"), "c": "violet"},
                        {"t": _t("Data exfiltration", "Data exfiltration"), "c": "mint"}],
            "exposures": exposures,
            "impacts": [_t("Customer / user PII", "Customer / user PII"),
                        _t("Core service delivery", "Core service delivery"),
                        _t("Operational continuity", "Operational continuity"),
                        _t("Credentials & secrets", "Credentials & secrets"),
                        _t("Brand & trust", "Brand & trust")],
        },
        "scene1": {
            "h1": (_t("scene1.h1.priority", "%(company)s's {hl}%(n)s priority{/hl} exposed estate.") if crit_high
                   else _t("scene1.h1.plain", "%(company)s's exposed estate.")) % fmt,
            "sub": (_t("scene1.sub.priority",
                       "%(company)s has {ink}%(hosts)s internet-facing host(s){/ink} across "
                       "{ink}%(asns)s hosting ASN(s){/ink}. The priority exposure is {red}%(ev)s{/red}.") if ev0
                    else _t("scene1.sub.plain",
                            "%(company)s presents {ink}%(hosts)s internet-facing host(s){/ink} across "
                            "{ink}%(asns)s ASN(s){/ink}.")) % fmt,
            "stats": [{"n": str(hosts), "l": _t("Verified exposed hosts", "Verified exposed hosts")},
                      {"n": str(asns), "l": _t("Hosting ASNs", "Hosting ASNs")},
                      {"n": str(len(crit_high)), "l": _t("Priority findings", "Priority findings"), "bad": True},
                      {"n": "0", "l": _t("Behind managed edge", "Behind managed edge"), "bad": True}],
            "legend": [{"c": "teal", "t": _t("Owned / backbone", "Owned / backbone")},
                       {"c": "amber", "t": _t("Shared hosting", "Shared hosting")},
                       {"c": "red", "t": _t("Priority finding", "Priority finding")},
                       {"c": "faint", "t": _t("Behind managed edge (0)", "Behind managed edge (0)")}],
            "caption": cap1,
        },
        "scene2": {
            "h1": (gj.get("verdict") or _t("scene2.h1.default", "The threat picture, {hl}named{/hl}."))[:70],
            "sub": (gj.get("sectorContext") or gj.get("verdict") or
                    _t("scene2.sub.default",
                       "%(company)s faces the threat set typical of its sector and exposure.") % fmt)[:420],
            "legend": leg2 or [{"c": "violet", "t": _t("Opportunistic ransomware", "Opportunistic ransomware")}],
            "actors": actor_defs,            # drives the c2 threat-actor animation (real GEOPOL actors)
            "caption": ((gj.get("cbiqBridge") or [{}])[0].get("note")
                        or _t("scene2.caption.default",
                              "Most likely: opportunistic intrusion via the exposed edge. "
                              "Break it cheapest with ZTNA.")),
        },
    }


def author(fj, gj, company):
    """Try the DO model; fall back to deterministic. Returns the content dict."""
    base = deterministic(fj, gj, company)
    try:
        sys.path.insert(0, HERE)
        import enrich as E
        # ONE language registry (enrich.LANG_BLOCKS), never a local `if de/ru`. English keeps the
        # historic "British English." note; any other language gets the same prompt block the decks
        # use, so the animated report and the four decks speak with one voice.
        block = E.lang_block(LANG)
        prompt = PROMPT % {
            "company": company,
            "scope": (fj.get("target") or {}).get("scope", ""),
            "findings": _slim_findings(fj),
            "inv": json.dumps((fj.get("target") or {}).get("inventory", {}))[:600],
            "verdict": gj.get("verdict", ""),
            "actors": _slim_actors(gj),
            "sector": gj.get("sectorContext", ""),
            "lang_note": "" if block else " British English.",
        }
        # appended AFTER the %-format so a future block containing a literal % can never blow up
        prompt = prompt + block
        model = os.environ.get("GEOPOL_HTML_MODEL") or (E._chain() or ["gemma-4-31B-it"])[0]
        txt, usage = E._call(prompt, model=model, timeout=int(os.environ.get("GEOPOL_HTML_TIMEOUT", "120")))
        j = E._json(txt)
        # merge model scenes over the deterministic base, but only if they carry real prose
        ok = 0
        for sc in ("scene1", "scene2"):
            m = (j or {}).get(sc)
            if isinstance(m, dict) and (m.get("sub") or "").strip():
                base[sc] = {**base[sc], **{k: v for k, v in m.items() if v}}
                ok += 1
        print("[geopol-html] authored %d/2 scenes via %s (%s tok)"
              % (ok, model, (usage or {}).get("completion_tokens", "?")), file=sys.stderr)
    except Exception as e:
        print("[geopol-html] model author failed (%s) — deterministic content used" % type(e).__name__, file=sys.stderr)
    return base


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("findings")
    ap.add_argument("geopol")
    ap.add_argument("out")
    ap.add_argument("--company", default=None)
    a = ap.parse_args()

    fj, gj = _load(a.findings), _load(a.geopol)
    company = a.company or (fj.get("target") or {}).get("company") or gj.get("customer") or "Target"
    content = author(fj, gj, company)

    cpath = os.path.join(os.path.dirname(os.path.abspath(a.out)) or ".", "_geopol_content.json")
    json.dump(content, open(cpath, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    r = subprocess.run(["node", os.path.join(HERE, "build_geopol_html.js"), cpath, a.out])
    sys.exit(r.returncode)


if __name__ == "__main__":
    main()
