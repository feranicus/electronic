import { useEffect, useRef, useState } from "react";
import { startAssess, assessEventsUrl } from "../api.js";

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

export default function NewAssessment() {
  const [company, setCompany] = useState("");
  const [status, setStatus] = useState("idle"); // idle | running | done | error
  const [lines, setLines] = useState([]);
  const [decks, setDecks] = useState([]);
  const [summary, setSummary] = useState("");
  const [errMsg, setErrMsg] = useState("");
  const esRef = useRef(null);
  const logRef = useRef(null);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [lines]);

  useEffect(() => () => { if (esRef.current) esRef.current.close(); }, []);

  async function run(e) {
    e.preventDefault();
    const name = company.trim();
    if (!name || status === "running") return;
    setStatus("running"); setLines([]); setDecks([]); setSummary(""); setErrMsg("");
    if (esRef.current) esRef.current.close();

    const { ok, data } = await startAssess(name);
    if (!ok || !data.job_id) {
      setStatus("error");
      setErrMsg(data.message || "Could not start the assessment.");
      return;
    }
    const es = new EventSource(assessEventsUrl(data.job_id), { withCredentials: true });
    esRef.current = es;

    es.onmessage = (ev) => {
      let payload;
      try { payload = JSON.parse(ev.data); } catch { return; }
      if (payload.evt === "progress") {
        setLines((cur) => [...cur, payload.line]);
      } else if (payload.evt === "done") {
        setDecks(payload.decks || []);
        setSummary(payload.summary || "");
        setStatus("done");
        es.close();
      } else if (payload.evt === "error") {
        setErrMsg(payload.message || "The assessment failed.");
        setStatus("error");
        es.close();
      }
    };
    es.onerror = () => {
      // if we never finished, surface a connection error
      setStatus((s) => {
        if (s === "running") {
          setErrMsg("Lost connection to the assessment stream.");
          return "error";
        }
        return s;
      });
      es.close();
    };
  }

  return (
    <>
      <h1 className="page-h">New assessment</h1>
      <p className="page-sub">One input: a company name or domain. The engine resolves the entire footprint,
        sweeps Shodan, and writes the four boardroom decks. No IPs, ASNs or certs to type.</p>

      <div className="panel">
        <form className="assess-row" onSubmit={run}>
          <div className="fld">
            <div className="label">Company name</div>
            <input className="input" placeholder="e.g. Volkswagen AG"
              value={company} onChange={(e) => setCompany(e.target.value)}
              disabled={status === "running"} />
          </div>
          <button className="btn" type="submit" disabled={status === "running" || !company.trim()}>
            {status === "running" ? <><span className="spinner" /> Assessing…</> : "Assess"}
          </button>
        </form>

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
    </>
  );
}
