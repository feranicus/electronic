import { useEffect, useRef, useState } from "react";
import { startCompliance, complianceRefine, assessEventsUrl, assessStatus, assessClarify } from "../api.js";
import { useT } from "../i18n";
import { useDocLangs } from "../docLangs.js";

// Compliance module (NIS2 / CRA / EU AI Act). Same UX as Assess: one company-name input -> live
// stream -> decks -> post-run clarification/refine. Shares the assess streaming/status/clarify
// endpoints (engine-agnostic); starts + refines against the compliance engine.

function fmtTime(sec) {
  const m = Math.floor(sec / 60), r = sec % 60;
  return m ? `${m}m ${String(r).padStart(2, "0")}s` : `${r}s`;
}

export default function Compliance() {
  // `lang` here is the DOCUMENT language of the decks, not the interface language — the latter
  // comes from the shared site store, so only the translator is taken off useT().
  const [, , t] = useT();
  const [company, setCompany] = useState("");
  // Document language, offered from what the ENGINE can actually render — not from the six the
  // interface speaks. See docLangs.js.
  const { docs: docLangs, lang, setLang, unavailable: docLangUnavailable } = useDocLangs();
  const [pct, setPct] = useState(0);
  const [phase, setPhase] = useState("");
  const [notice, setNotice] = useState("");
  const [shown, setShown] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const startedRef = useRef(0);
  const [status, setStatus] = useState("idle");     // idle | running | done | error
  const [lines, setLines] = useState([]);
  const [decks, setDecks] = useState([]);
  const [errMsg, setErrMsg] = useState("");
  const [jobId, setJobId] = useState(null);
  const [clarify, setClarify] = useState(null);
  const [answers, setAnswers] = useState({});
  const [refining, setRefining] = useState(false);
  const esRef = useRef(null);
  const logRef = useRef(null);

  useEffect(() => { if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight; }, [lines]);

  const LADDER = [8, 56, 64, 72, 80, 88, 94, 100];
  useEffect(() => {
    if (status !== "running") return;
    const id = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startedRef.current) / 1000));
      setShown((cur) => {
        const target = LADDER.find((x) => x > pct) ?? 100;
        const ceiling = target - 1;
        if (cur >= ceiling) return cur;
        return Math.min(ceiling, cur + (target - cur) * 0.02);
      });
    }, 400);
    return () => clearInterval(id);
  }, [status, pct]);
  useEffect(() => { setShown((c) => Math.max(c, pct)); }, [pct]);
  useEffect(() => () => { if (esRef.current) esRef.current.close(); }, []);

  async function loadClarify(id) {
    try {
      const data = await assessClarify(id);
      if (data && (data.questions || []).length) { setClarify(data); setAnswers({}); }
      else setClarify(null);
    } catch { setClarify(null); }
  }
  const ansMulti = (key, opt) => setAnswers((a) => {
    const cur = new Set(a[key] || []); cur.has(opt) ? cur.delete(opt) : cur.add(opt);
    return { ...a, [key]: [...cur] };
  });
  const ansText = (key, val) => setAnswers((a) => ({ ...a, [key]: val }));
  const hasAnswers = Object.entries(answers).some(([, v]) =>
    Array.isArray(v) ? v.length : (typeof v === "boolean" ? v : String(v || "").trim()));

  function attach(id) {
    setJobId(id);
    if (esRef.current) esRef.current.close();
    const es = new EventSource(assessEventsUrl(id), { withCredentials: true });
    esRef.current = es;
    es.onmessage = (ev) => {
      let p; try { p = JSON.parse(ev.data); } catch { return; }
      if (p.evt === "progress") {
        setLines((cur) => [...cur, p.line]);
        const m = /^PROGRESS:\s*(?:\[(\d+)%\]\s*)?(.+)$/.exec(p.line || "");
        if (m) { if (m[1]) setPct(Number(m[1])); setPhase(m[2].trim());
          if (/switching to|recovered on/i.test(m[2])) setNotice(m[2].trim()); }
      } else if (p.evt === "done") {
        try { localStorage.removeItem("cg_cjob"); } catch { /* ignore */ }
        setPct(100); setShown(100); setDecks(p.decks || []); setStatus("done");
        loadClarify(id); es.close();
      } else if (p.evt === "error") {
        try { localStorage.removeItem("cg_cjob"); } catch { /* ignore */ }
        setErrMsg(p.message || t("comp.errFailed")); setStatus("error"); es.close();
      }
    };
    es.onerror = () => setStatus((cur) => {
      if (cur === "running") setNotice(t("comp.dropped"));
      return cur;
    });
    // Compare against the value we set, not an English prefix — same behaviour, in any language.
    es.onopen = () => setNotice((n) => (n === t("comp.dropped") ? "" : n));
  }

  // resume an in-flight compliance job on return
  useEffect(() => {
    let stale = false;
    (async () => {
      let jid = null; try { jid = localStorage.getItem("cg_cjob"); } catch { /* ignore */ }
      if (!jid) return;
      const data = await assessStatus(jid).catch(() => null);
      if (!data || stale) return;
      if (data.status === "running") {
        setCompany(data.company || ""); setLines([]); setStatus("running");
        startedRef.current = Date.now(); setNotice(t("comp.reconnected"));
        attach(jid);
      } else if (data.status === "done" && (data.decks || []).length) {
        setCompany(data.company || ""); setLines(data.lines || []); setDecks(data.decks || []);
        setStatus("done"); setPct(100); setShown(100); setJobId(jid); loadClarify(jid);
        try { localStorage.removeItem("cg_cjob"); } catch { /* ignore */ }
      } else { try { localStorage.removeItem("cg_cjob"); } catch { /* ignore */ } }
    })();
    return () => { stale = true; };
  }, []);

  async function run(e) {
    e.preventDefault();
    const name = company.trim();
    if (!name || status === "running") return;
    setStatus("running"); setLines([]); setDecks([]); setErrMsg(""); setClarify(null); setAnswers({});
    setPct(0); setShown(0); setElapsed(0); setPhase(t("comp.phaseStart")); setNotice("");
    startedRef.current = Date.now();
    const { ok, data } = await startCompliance(name, lang);
    if (!ok || !data.job_id) { setStatus("error"); setErrMsg(data.message || t("comp.errStart")); return; }
    try { localStorage.setItem("cg_cjob", data.job_id); } catch { /* ignore */ }
    attach(data.job_id);
  }

  async function submitRefine() {
    if (!jobId || !hasAnswers || refining) return;
    setRefining(true);
    const { ok, data } = await complianceRefine(jobId, answers, lang);
    setRefining(false);
    if (!ok || !data.job_id) { setErrMsg(data.message || t("comp.errRefine")); return; }
    setStatus("running"); setLines([]); setDecks([]); setErrMsg(""); setClarify(null);
    setPct(0); setShown(0); setElapsed(0); setPhase(t("comp.phaseRescope")); setNotice("");
    startedRef.current = Date.now();
    try { localStorage.setItem("cg_cjob", data.job_id); } catch { /* ignore */ }
    attach(data.job_id);
  }

  return (
    <>
      <h1 className="page-h">{t("comp.h1")}</h1>
      {/* Four connective fragments around three BOLD statutory names. The names are legal titles and
          are never translated (see rule in locales/en.js), so they cannot live inside a key. */}
      <p className="page-sub">{t("comp.sub.a")}<b>NIS2</b>{t("comp.sub.b")}
        <b>Cyber Resilience Act</b>{t("comp.sub.c")}<b>EU AI Act</b>{t("comp.sub.d")}</p>

      <div className="panel">
        <form className="assess-row" onSubmit={run}>
          <div className="fld">
            <div className="label">{t("comp.company")}</div>
            <input className="input" placeholder={t("comp.companyPh")}
              value={company} onChange={(e) => setCompany(e.target.value)}
              disabled={status === "running"} />
          </div>
          <div className="fld fld-lang">
            {/* The options come from /api/langs — the dictionaries the engine actually has. */}
            <div className="label">{t("comp.docLang")}</div>
            <select className="input" value={lang} onChange={(e) => setLang(e.target.value)}
              disabled={status === "running"}>
              {docLangs.map((d) => <option key={d.code} value={d.code}>{d.name}</option>)}
            </select>
            {docLangUnavailable && <div className="hint">{t("assess.docLangNote")}</div>}
          </div>
          <button className="btn" type="submit" disabled={status === "running" || !company.trim()}>
            {status === "running" ? <><span className="spinner" /> {t("comp.running")}</> : t("comp.go")}
          </button>
        </form>

        {status === "running" && (
          <div className="prog">
            <div className="prog-top">
              {/* `phase` is ENGINE output (server data) — never translated. */}
              <span className="prog-phase">{phase || t("comp.phaseIdle")}</span>
              <span className="prog-meta">{Math.floor(shown)}% · {fmtTime(elapsed)}</span>
            </div>
            <div className="prog-track"><div className="prog-fill" style={{ width: Math.max(2, shown) + "%" }} /></div>
            {notice && <div className="prog-notice">⚠ {notice}</div>}
            <div className="prog-note">{t("comp.note")}</div>
          </div>
        )}

        {(status === "running" || lines.length > 0) && (
          <div className="loglist" ref={logRef}>
            {lines.length === 0 && status === "running"
              ? <div className="ln muted">{t("comp.logStarting")}</div>
              : lines.map((l, i) => <div key={i} className="ln">{l}</div>)}
          </div>
        )}

        {status === "error" && <div className="err">{String(errMsg)}</div>}

        {status === "done" && (
          <>
            <div className="ok">{t("comp.done")}</div>
            <div className="decks">
              {decks.map((d) => {
                const html = /\.html$/i.test(d.name);
                return (
                  <a key={d.name} className="deck" href={d.url} target={html ? "_blank" : undefined}
                    rel={html ? "noreferrer" : undefined} download={html ? undefined : true}>
                    <div className="doc">{html ? "HTML" : "PPTX"}</div>
                    <div><div className="fn">{d.name}</div>
                      <div className="muted" style={{ fontSize: 12 }}>{html ? t("comp.openReport") : t("comp.download")}</div></div>
                  </a>
                );
              })}
            </div>
          </>
        )}
      </div>

      {status === "done" && clarify && (clarify.questions || []).length > 0 && (
        <div className="panel clarify">
          <h2 className="page-h" style={{ fontSize: 20, marginTop: 0 }}>{t("comp.confirmH")}</h2>
          <p className="page-sub" style={{ marginTop: 4 }}>{t("comp.confirmSub")}</p>

          {clarify.questions.map((q) => (
            <div key={q.id} className="clarify-q">
              <div className="clarify-title">{q.title}</div>
              {q.body && <div className="clarify-body">{q.body}</div>}

              {(q.kind === "domains_multi" || q.kind === "hosts_multi") && (
                <div className="clarify-opts">
                  {(q.options || []).map((opt) => {
                    const on = (answers[q.maps_to] || []).includes(opt);
                    return (
                      <label key={opt} className={"chip" + (on ? " chip-on" : "")}>
                        <input type="checkbox" checked={on} onChange={() => ansMulti(q.maps_to, opt)} />{opt}
                      </label>
                    );
                  })}
                </div>
              )}

              {q.kind === "choice" && (
                <div className="clarify-opts">
                  {(q.options || []).map((opt) => {
                    const on = answers[q.maps_to] === opt;
                    return (
                      <label key={opt} className={"chip" + (on ? " chip-on" : "")}>
                        <input type="radio" name={q.maps_to} checked={on}
                          onChange={() => ansText(q.maps_to, opt)} />{opt}
                      </label>
                    );
                  })}
                </div>
              )}

              {q.kind === "text" && (
                <input className="input" placeholder={q.placeholder || ""}
                  value={answers[q.maps_to] || ""} onChange={(e) => ansText(q.maps_to, e.target.value)} />
              )}

              {q.kind === "yesno" && (
                <label className={"chip" + (answers[q.maps_to] ? " chip-on" : "")}>
                  <input type="checkbox" checked={!!answers[q.maps_to]}
                    onChange={(e) => ansText(q.maps_to, e.target.checked)} />{t("comp.yes")}
                </label>
              )}
            </div>
          ))}

          <button className="btn" type="button" onClick={submitRefine} disabled={!hasAnswers || refining}>
            {refining ? <><span className="spinner" /> {t("comp.refineBusy")}</> : t("comp.refineGo")}
          </button>
          {!hasAnswers && <div className="gdpr-mini">{t("comp.refineHint")}</div>}
        </div>
      )}
    </>
  );
}
