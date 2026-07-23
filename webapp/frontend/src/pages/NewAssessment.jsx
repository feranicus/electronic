import { useEffect, useRef, useState } from "react";
import { startAssess, assessEventsUrl, ackPrivacy, assessStatus,
  assessClarify, assessRefine } from "../api.js";
import { NOTICE, useLegalLang, LangToggle } from "../legal";

function asText(v) {
  if (v == null) return "";
  if (typeof v === "string") return v;
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  if (typeof v === "object") {
    // pretty severity-style objects as "key: value" lines; else JSON
    try {
      const ents = Object.entries(v);
      if (ents.length && ents.every(([, x]) => typeof x !== "object"))
        return ents.map(([k, x]) => k + ": " + x).join("   ");
      return JSON.stringify(v, null, 2);
    } catch { return String(v); }
  }
  return String(v);
}

function fmtTime(sec) {
  const m = Math.floor(sec / 60), r = sec % 60;
  return m ? `${m}m ${String(r).padStart(2, "0")}s` : `${r}s`;
}

export default function NewAssessment() {
  const [company, setCompany] = useState("");
  const [lang, setLang] = useState("en");   // language of the 4 generated documents
  const [pct, setPct] = useState(0);        // last REAL milestone reported by the engine
  const [phase, setPhase] = useState("");   // human label for the current phase
  const [notice, setNotice] = useState(""); // e.g. "model X timed out — switching to Y"
  // GDPR Art. 13: tell the user what is collected BEFORE the processing starts, not afterwards.
  // Acknowledged once per browser; the acknowledgement itself is logged for accountability (Art. 5(2)).
  const [legalLang, setLegalLang] = useLegalLang();
  const [ackd, setAckd] = useState(() => {
    try { return localStorage.getItem("cg_privacy_ack") === "1"; } catch { return false; }
  });
  const [shown, setShown] = useState(0);    // eased value actually drawn (never goes backwards)
  const [elapsed, setElapsed] = useState(0);
  const startedRef = useRef(0);
  const [status, setStatus] = useState("idle"); // idle | running | done | error
  const [lines, setLines] = useState([]);
  const [decks, setDecks] = useState([]);
  const [summary, setSummary] = useState("");
  const [errMsg, setErrMsg] = useState("");
  // post-run clarification loop (jobhuntwow gap->answer model): after the decks are delivered we ask
  // what recon could not resolve; the operator answers / adds facts and we REFINE.
  const [jobId, setJobId] = useState(null);
  const [clarify, setClarify] = useState(null);   // {questions, summary, company} | null
  const [answers, setAnswers] = useState({});      // keyed by question.maps_to (what /refine expects)
  const [refining, setRefining] = useState(false);
  const esRef = useRef(null);
  const logRef = useRef(null);

  async function loadClarify(id) {
    try {
      const data = await assessClarify(id);   // getJSON returns the raw object (not {ok,data})
      if (data && (data.questions || []).length) { setClarify(data); setAnswers({}); }
      else setClarify(null);
    } catch { setClarify(null); }
  }
  const ansMulti = (key, opt) => setAnswers((a) => {
    const cur = new Set(a[key] || []);
    cur.has(opt) ? cur.delete(opt) : cur.add(opt);
    return { ...a, [key]: [...cur] };
  });
  const ansText = (key, val) => setAnswers((a) => ({ ...a, [key]: val }));
  const hasAnswers = Object.entries(answers).some(([, v]) =>
    Array.isArray(v) ? v.length : (typeof v === "boolean" ? v : String(v || "").trim()));

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [lines]);

  // The engine reports milestones (4 -> 8 -> 56 -> 62 -> 91 -> 99). Recon alone is ~70s, so a bar
  // pinned to milestones would freeze at 8% and look hung. Between milestones we ease toward the
  // NEXT one and never reach it, so it always creeps but never lies about being finished.
  const LADDER = [4, 8, 56, 62, 89, 91, 97, 99, 100];
  useEffect(() => {
    if (status !== "running") return;
    const id = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startedRef.current) / 1000));
      setShown((cur) => {
        const target = LADDER.find((x) => x > pct) ?? 100;
        const ceiling = target - 1;               // never pre-announce the next phase
        if (cur >= ceiling) return cur;
        return Math.min(ceiling, cur + (target - cur) * 0.015);
      });
    }, 400);
    return () => clearInterval(id);
  }, [status, pct]);

  useEffect(() => { setShown((c) => Math.max(c, pct)); }, [pct]);   // snap forward on a real milestone

  useEffect(() => () => { if (esRef.current) esRef.current.close(); }, []);

  // Phones evict background tabs. If we left a job running, pick it back up on return instead of
  // showing an empty form while the engine is still working.
  useEffect(() => {
    let stale = false;
    (async () => {
      let jid = null;
      try { jid = localStorage.getItem("cg_job"); } catch { /* ignore */ }
      if (!jid) return;
      const { ok, data } = await assessStatus(jid);
      if (!ok || stale) { try { localStorage.removeItem("cg_job"); } catch { /* ignore */ } return; }
      if (data.status === "running") {
        setCompany(data.company || "");
        // do NOT preload lines here: a fresh EventSource sends no Last-Event-ID, so the stream
        // replays the log from the start. Preloading would double every line.
        setLines([]);
        setStatus("running");
        startedRef.current = Date.now();
        setNotice("Reconnected to an assessment already running on the server.");
        attach(jid);
      } else if (data.status === "done" && (data.decks || []).length) {
        setCompany(data.company || "");
        setLines(data.lines || []); setDecks(data.decks || []);
        setSummary(data.summary || ""); setStatus("done"); setPct(100); setShown(100);
        setJobId(jid); loadClarify(jid);
        try { localStorage.removeItem("cg_job"); } catch { /* ignore */ }
      } else {
        try { localStorage.removeItem("cg_job"); } catch { /* ignore */ }
      }
    })();
    return () => { stale = true; };
  }, []);

  function acknowledge() {
    try { localStorage.setItem("cg_privacy_ack", "1"); } catch { /* private mode */ }
    setAckd(true);
    ackPrivacy();                                   // server-side record of the acknowledgement
  }

  // ONE place that wires the stream — used both by a fresh run and by resuming an in-flight job.
  function attach(jobId) {
    setJobId(jobId);
    if (esRef.current) esRef.current.close();
    const es = new EventSource(assessEventsUrl(jobId), { withCredentials: true });
    esRef.current = es;

    es.onmessage = (ev) => {
      let payload;
      try { payload = JSON.parse(ev.data); } catch { return; }
      if (payload.evt === "progress") {
        setLines((cur) => [...cur, payload.line]);
        // engine emits:  PROGRESS: [56%] BGP/ASN resilience ...
        const m = /^PROGRESS:\s*(?:\[(\d+)%\]\s*)?(.+)$/.exec(payload.line || "");
        if (m) {
          if (m[1]) setPct(Number(m[1]));
          setPhase(m[2].trim());
          // the engine announces model failover on a PROGRESS line — promote it to a banner so the
          // operator sees "the AI stalled, we switched" instead of silently getting a poorer deck
          if (/switching to|recovered on/i.test(m[2])) setNotice(m[2].trim());
        }
      } else if (payload.evt === "done") {
        try { localStorage.removeItem("cg_job"); } catch { /* ignore */ }
        setPct(100); setShown(100);
        setDecks(payload.decks || []);
        setSummary(payload.summary || "");
        setStatus("done");
        loadClarify(jobId);                          // surface the clarification questions
        es.close();
      } else if (payload.evt === "error") {
        try { localStorage.removeItem("cg_job"); } catch { /* ignore */ }
        setErrMsg(payload.message || "The assessment failed.");
        setStatus("error");
        es.close();
      }
    };
    es.onerror = () => {
      // DO NOT close. EventSource reconnects by itself and replays Last-Event-ID, so we resume
      // exactly where we left off. The run lives on the server now — a locked phone, a tunnel or a
      // flaky radio is a pause, not a cancellation.
      setStatus((cur) => {
        if (cur === "running") setNotice("Connection dropped — reconnecting… (the assessment keeps running on the server)");
        return cur;
      });
    };
    es.onopen = () => setNotice((n) => (n.startsWith("Connection dropped") ? "" : n));
  }

  async function run(e) {
    e.preventDefault();
    const name = company.trim();
    if (!name || status === "running") return;
    if (!ackd) { acknowledge(); }                   // first Assess click = notice was shown + accepted
    setStatus("running"); setLines([]); setDecks([]); setSummary(""); setErrMsg("");
    setClarify(null); setAnswers({});                // fresh run — drop the previous clarification
    setPct(0); setShown(0); setElapsed(0); setPhase("Starting the engine…"); setNotice("");
    startedRef.current = Date.now();

    const { ok, data } = await startAssess(name, lang);
    if (!ok || !data.job_id) {
      setStatus("error");
      setErrMsg(data.message || "Could not start the assessment.");
      return;
    }
    try { localStorage.setItem("cg_job", data.job_id); } catch { /* ignore */ }
    attach(data.job_id);
  }

  // Refine: send the clarification answers -> a NEW child run, re-scoped, streamed like the original.
  async function submitRefine() {
    if (!jobId || !hasAnswers || refining) return;
    setRefining(true);
    const { ok, data } = await assessRefine(jobId, answers, lang);
    setRefining(false);
    if (!ok || !data.job_id) {
      setErrMsg(data.message || "Could not refine the assessment.");
      return;
    }
    // reset the run view and stream the child exactly like a fresh assessment
    setStatus("running"); setLines([]); setDecks([]); setSummary(""); setErrMsg("");
    setClarify(null);
    setPct(0); setShown(0); setElapsed(0); setPhase("Re-scoping with your answers…"); setNotice("");
    startedRef.current = Date.now();
    try { localStorage.setItem("cg_job", data.job_id); } catch { /* ignore */ }
    attach(data.job_id);
  }

  return (
    <>
      <h1 className="page-h">New assessment</h1>
      <p className="page-sub">One input: a company name or domain. The engine resolves the entire footprint,
        sweeps Shodan, and writes the four boardroom decks — in English or Hoch-Deutsch. No IPs, ASNs or certs to type.</p>

      {!ackd && (
        <div className="panel gdpr-notice">
          <div className="gdpr-head">
            <div className="gdpr-title">{NOTICE[legalLang].title}</div>
            <LangToggle lang={legalLang} setLang={setLegalLang} />
          </div>
          <p>{NOTICE[legalLang].p1}</p>
          <p>{NOTICE[legalLang].p2}</p>
          <p><a href="/privacy" target="_blank" rel="noreferrer">{NOTICE[legalLang].link}</a></p>
          <button className="btn btn-sm" type="button" onClick={acknowledge}>
            {NOTICE[legalLang].ok}
          </button>
        </div>
      )}

      <div className="panel">
        <form className="assess-row" onSubmit={run}>
          <div className="fld">
            <div className="label">Company name</div>
            <input className="input" placeholder="e.g. Volkswagen AG"
              value={company} onChange={(e) => setCompany(e.target.value)}
              disabled={status === "running"} />
          </div>
          <div className="fld fld-lang">
            <div className="label">Document language</div>
            <select className="input" value={lang} onChange={(e) => setLang(e.target.value)}
              disabled={status === "running"}>
              <option value="en">English</option>
              <option value="de">Deutsch (Hochdeutsch)</option>
            </select>
          </div>
          <button className="btn" type="submit" disabled={status === "running" || !company.trim()}>
            {status === "running" ? <><span className="spinner" /> Assessing…</> : "Assess"}
          </button>
        </form>

        <div className="gdpr-mini">
          {NOTICE[legalLang].mini}
          <a href="/privacy" target="_blank" rel="noreferrer">{NOTICE[legalLang].link}</a>
        </div>

        {status === "running" && (
          <div className="prog">
            <div className="prog-top">
              <span className="prog-phase">{phase || "Working…"}</span>
              <span className="prog-meta">{Math.floor(shown)}% · {fmtTime(elapsed)}</span>
            </div>
            <div className="prog-track"><div className="prog-fill" style={{ width: Math.max(2, shown) + "%" }} /></div>
            {notice && <div className="prog-notice">⚠ {notice}</div>}
            <div className="prog-note">
              {elapsed > 300
                ? "Still working. Long runs usually mean Shodan recon found a large estate, or an AI model is slow and we are failing over to the next one — the log above says which."
                : "Typically 3–7 minutes: Shodan recon is the long part (~2–3 min), then the AI writes the prose (~1 min)."}
              {" "}Keep this tab open; refreshing cancels the run.
            </div>
          </div>
        )}

        {(status === "running" || lines.length > 0) && (
          <div className="loglist" ref={logRef}>
            {lines.length === 0 && status === "running"
              ? <div className="ln muted">Starting…</div>
              : lines.map((l, i) => <div key={i} className="ln">{l}</div>)}
          </div>
        )}

        {status === "running" && (
          <div className="status-row"><span className="spinner" /> Working — this usually takes about two minutes.</div>
        )}

        {status === "error" && <div className="err">{asText(errMsg)}</div>}

        {status === "done" && (
          <>
            <div className="ok">Done. Your four decks are ready.</div>
            <div className="decks">
              {decks.map((d) => (
                <a key={d.name} className="deck" href={d.url} download>
                  <div className="doc">PPTX</div>
                  <div><div className="fn">{d.name}</div><div className="muted" style={{ fontSize: 12 }}>Download</div></div>
                </a>
              ))}
            </div>
            {summary && <div className="summary">{asText(summary)}</div>}
          </>
        )}
      </div>

      {status === "done" && clarify && (clarify.questions || []).length > 0 && (
        <div className="panel clarify">
          <h2 className="page-h" style={{ fontSize: 20, marginTop: 0 }}>Refine this assessment</h2>
          <p className="page-sub" style={{ marginTop: 4 }}>
            The decks above are ready. To sharpen the scope, answer anything relevant below — confirm
            what is yours, add IP ranges / systems the auto-recon could not see, or flag anything that
            is not yours. I will re-scope and rebuild the four decks and the animated report.
          </p>

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
                        <input type="checkbox" checked={on} onChange={() => ansMulti(q.maps_to, opt)} />
                        {opt}
                      </label>
                    );
                  })}
                </div>
              )}

              {q.kind === "text" && (
                <input className="input" placeholder={q.placeholder || ""}
                  value={answers[q.maps_to] || ""}
                  onChange={(e) => ansText(q.maps_to, e.target.value)} />
              )}

              {q.kind === "yesno" && (
                <label className={"chip" + (answers[q.maps_to] ? " chip-on" : "")}>
                  <input type="checkbox" checked={!!answers[q.maps_to]}
                    onChange={(e) => ansText(q.maps_to, e.target.checked)} />
                  Yes
                </label>
              )}
            </div>
          ))}

          <button className="btn" type="button" onClick={submitRefine}
            disabled={!hasAnswers || refining}>
            {refining ? <><span className="spinner" /> Refining…</> : "Refine & rebuild"}
          </button>
          {!hasAnswers && <div className="gdpr-mini">Answer at least one question to refine.</div>}
        </div>
      )}
    </>
  );
}
