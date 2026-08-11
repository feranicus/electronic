"""run_log.py — turn the raw engine log into a document the ASSESSED COMPANY may read.

The operator asked for the full run log to be delivered per company, downloadable from History
alongside the decks. That is a genuinely good idea: the log is a methodology receipt. It shows the
timestamps, what was discovered, what the guards REFUSED to conclude, which model wrote the prose
and which independent model audited it. A customer who wonders "how do you know this" gets the
answer without a meeting.

BUT THE RAW LOG CANNOT BE HANDED OVER, and this module exists because of what is in it:

  · the OPERATOR'S EMAIL on every single line (`"user": "feranicus@s4biz.io"`);
  · INTERNAL FILESYSTEM PATHS that name the operator and the job id
    (/data/jobs/feranicus_s4biz.io/ddc87bfa.../...);
  · THE COST LEDGER. The `cost_snapshot` event carries lifetime_usd, assessments_total and the
    average per run. On the sberautotech run that read 193 assessments, $0.95 lifetime, $0.0049
    average. Handing a customer the exact AI cost of the thing they are being invoiced for, plus
    the total size of the book, is commercially self-harming. It is not a privacy leak, it is worse
    than one: it is a negotiating position given away for free.
  · TOKEN COUNTS, which are the same number wearing a different hat.

WHAT IS DELIBERATELY KEPT, because it is the whole value of the artifact:
  · every phase, its timing and its outcome;
  · every REFUSAL: the ASN that was not adopted, the ownership gate, "absence of evidence is never
    a finding", "NO ATTRIBUTABLE ESTATE ... that is a finding, not a failure";
  · the model that wrote the prose and the DIFFERENT-VENDOR model that audited it, with the verdict;
  · the QA caveat about passive OSINT limits;
  · the findings tally and the deliverable list, by name only.

TWO LAYERS, AND THE FIRST ONE IS THE REAL PROTECTION. This module renders an ALLOW-LIST: only
recognised structured events and recognised line shapes are emitted, and only named keys within
them. The regex redaction of emails, paths and ids is a SECOND layer for anything that slips past.
Its own negative tests proved the split: deleting the email regex, or un-dropping cost_snapshot,
changes nothing, because neither ever reaches the renderer. Deleting the allow-list DOES leak
immediately. Worth knowing when changing this file: the line to protect is the final `continue`,
not the regexes.

FAILS SAFE. Anything the redactor does not recognise is DROPPED, not passed through. A log line
invented by a future version of the engine cannot leak by default; it can only go missing, which
is visible and fixable. The opposite choice would leak silently, once, and permanently.
"""
import json
import re
import time

# Events whose CONTENT is commercial rather than technical. Dropped whole.
_DROP_EVENTS = {"cost_snapshot", "qwen_attempt", "engine_config"}

# Keys never rendered, wherever they appear.
_DROP_KEYS = {"user", "cost_usd", "qwen_cost_usd", "tokens_in", "tokens_out", "lifetime_usd",
              "assessments_total", "avg_usd", "tokens_in_total", "tokens_out_total",
              "ledger", "first_ts", "last_ts", "service", "bot", "job", "jobdir", "path"}

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_JOBPATH = re.compile(r"/data/jobs/\S+")
_UUID = re.compile(r"\b[0-9a-f]{12,32}\b")

RU = {
    "title": "ЖУРНАЛ ОЦЕНКИ", "company": "Компания", "started": "Начало", "duration": "Длительность",
    "lang": "Язык документов", "phases": "ХОД РАБОТЫ", "guards": "ЧТО СИСТЕМА ОТКАЗАЛАСЬ УТВЕРЖДАТЬ",
    "audit": "НЕЗАВИСИМАЯ ПРОВЕРКА", "found": "ИТОГ", "files": "ВЫДАННЫЕ ДОКУМЕНТЫ",
    "note": "О ГРАНИЦАХ МЕТОДА", "sec": "с",
    "foot": ("Журнал сформирован автоматически. Оценка выполнена по публичным источникам: "
             "к системам компании не отправлено ни одного запроса."),
    "guard_intro": ("Ниже перечислено то, что система МОГЛА БЫ заявить, но не стала, потому что "
                    "данных было недостаточно. Это часть метода: отсутствие данных никогда не "
                    "превращается в вывод."),
}
EN = {
    "title": "ASSESSMENT RUN LOG", "company": "Company", "started": "Started", "duration": "Duration",
    "lang": "Document language", "phases": "WHAT WAS DONE", "guards": "WHAT THE SYSTEM REFUSED TO CLAIM",
    "audit": "INDEPENDENT REVIEW", "found": "RESULT", "files": "DELIVERABLES",
    "note": "LIMITS OF THE METHOD", "sec": "s",
    "foot": ("Generated automatically. The assessment used public sources only: not a single "
             "request was sent to the company's systems."),
    "guard_intro": ("Below is what the system COULD have asserted and did not, because the "
                    "evidence was insufficient. That is part of the method: absence of evidence "
                    "never becomes a conclusion."),
}


def _clean(text):
    """Strip anything that identifies the operator or our internals. Applied to every line."""
    t = _JOBPATH.sub("[файл]", str(text))
    t = _EMAIL.sub("[оператор]", t)
    t = _UUID.sub("[id]", t)
    return t.strip()


def _ts(v):
    try:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(float(v)))
    except Exception:
        return ""


# Lines worth showing to the customer, matched on what they MEAN rather than on where they sit.
_GUARD_MARKERS = (
    "does NOT corroborate", "не подтверждает", "NOT an ownership anchor", "fails closed",
    "absence of evidence", "NOT raised as a finding", "NOT 'none'", "NOT determined",
    "no structure discovery", "put to the operator as a question", "REFUSED", "rolled back",
    "NO ATTRIBUTABLE ESTATE", "scope falls back",
)
_PHASE_MARKERS = ("[auto]", "PROGRESS:", "FP-AUDIT:", "enrich:")


def build(raw, company, lang="ru"):
    """Raw engine output (str or list of lines) -> the customer-facing log. Never raises."""
    L = RU if str(lang).lower().startswith("ru") else EN
    lines = raw.splitlines() if isinstance(raw, str) else list(raw or [])

    started = ended = None
    phases, guards, files, audit, qa, tally = [], [], [], [], [], {}

    for ln in lines:
        # str() because the caller may hand us a list containing None. Its own test found this:
        # a broken log must never be able to fail a completed assessment.
        s = str(ln or "").strip()
        if not s:
            continue
        if s.startswith("{"):                                   # structured event
            try:
                j = json.loads(s)
            except Exception:
                continue
            evt = j.get("evt")
            if evt in _DROP_EVENTS:
                continue
            if evt == "assess_start":
                started = j.get("ts")
            elif evt == "assess_done":
                ended = j.get("ts")
                tally = {k: j.get(k) for k in ("crit", "high", "med", "low", "decks", "lang")
                         if j.get(k) is not None}
            elif evt == "fp_audit":
                audit.append({k: j.get(k) for k in ("author", "auditor", "verdict", "flagged",
                                                    "dropped", "refused") if j.get(k) is not None})
            elif evt == "phase":
                phases.append("  %-46s %s (%s %s)"
                              % (_clean(j.get("name", "")), _clean(j.get("status", "")),
                                 int(float(j.get("ms", 0)) / 1000), L["sec"]))
            continue

        if s.startswith("QA:"):
            qa.append(_clean(s[3:]))
            continue
        if s.startswith("OK ") and ("." in s):                  # a produced file
            files.append(_clean(s[3:].rsplit("/", 1)[-1]))
            continue
        if any(m in s for m in _GUARD_MARKERS):
            guards.append("  " + _clean(s))
            continue
        if any(s.startswith(m) or m in s[:12] for m in _PHASE_MARKERS):
            phases.append("  " + _clean(s))
            continue
        # ANYTHING UNRECOGNISED IS DROPPED. See the module docstring: a future log line must be
        # able to go missing, never to leak.

    out = ["=" * 78, "  %s" % L["title"], "=" * 78, ""]
    out.append("%-22s %s" % (L["company"] + ":", company))
    if started:
        out.append("%-22s %s UTC" % (L["started"] + ":", _ts(started)))
    if started and ended:
        out.append("%-22s %d %s" % (L["duration"] + ":", int(float(ended) - float(started)), L["sec"]))
    if tally.get("lang"):
        out.append("%-22s %s" % (L["lang"] + ":", str(tally["lang"]).upper()))

    def section(title, body, intro=None):
        if not body:
            return
        out.extend(["", "-" * 78, title, "-" * 78])
        if intro:
            out.extend([intro, ""])
        out.extend(body)

    section(L["phases"], phases[:400])
    section(L["guards"], guards[:120], L["guard_intro"])
    if audit:
        rows = ["  %s: %s / %s: %s / %s: %s"
                % ("автор" if L is RU else "author", a.get("author", "-"),
                   "проверил" if L is RU else "auditor", a.get("auditor", "-"),
                   "вывод" if L is RU else "verdict", a.get("verdict", "-")) for a in audit]
        section(L["audit"], rows)
    if tally:
        section(L["found"], ["  CRITICAL %s · HIGH %s · MEDIUM %s · LOW %s"
                             % (tally.get("crit", 0), tally.get("high", 0),
                                tally.get("med", 0), tally.get("low", 0))])
    section(L["files"], ["  " + f for f in dict.fromkeys(files)])
    section(L["note"], ["  " + q for q in dict.fromkeys(qa)])
    out.extend(["", "=" * 78, L["foot"], "=" * 78])
    return "\n".join(out) + "\n"


def write(raw, company, lang, jobdir, filename=None):
    """Write the customer log next to the decks. Returns the path, or '' on any failure."""
    import os
    try:
        name = filename or "%s_Run_Log_%s.txt" % (str(company).replace("/", "_"),
                                                  str(lang).upper()[:2])
        p = os.path.join(jobdir, name)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(build(raw, company, lang))
        return p
    except Exception:
        return ""
