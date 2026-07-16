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

function fmtTime(sec) {
  const m = Math.floor(sec / 60), r = sec % 60;
  return m ? `${m}m ${String(r).padStart(2, "0")}s` : `${r}s`;
}

export default function NewAssessment() {
  const [company, setCompany] = useState("");
  const [lang, setLang] = useState("en");   // language of the 4 generated documents
  const [pct, setPct] = useState(0);        // last REAL milestone reported by the engine
  const [phase, setPhase] = useState("");   // human label for the current phase
  const [shown, setShown] = useState(0);    // eased value actually drawn (never goes backwards)
  const [elapsed, setElapsed] = useState(0);
  const startedRef = useRef(0);
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

  async function run(e) {
    e.preventDefault();
    const name = company.trim();
    if (!name || status === "running") return;
    setStatus("running"); setLines([]); setDecks([]); setSummary(""); setErrMsg("");
    setPct(0); setShown(0); setElapsed(0); setPhase("Starting the engine…");
    startedRef.current = Date.now();
    if (esRef.current) esRef.current.close();

    const { ok, data } = await startAssess(name, lang);
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
        // engine emits:  PROGRESS: [56%] BGP/ASN resilience ...
        const m = /^PROGRESS:\s*(?:\[(\d+)%\]\s*)?(.+)$/.exec(payload.line || "");
        if (m) {
          if (m[1]) setPct(Number(m[1]));
          setPhase(m[2].trim());
        }
      } else if (payload.evt === "done") {
        setPct(100); setShown(100);
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
        sweeps Shodan, and writes the four boardroom decks — in English or Hoch-Deutsch. No IPs, ASNs or certs to type.</p>

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

        {status === "running" && (
          <div className="prog">
            <div className="prog-top">
              <span className="prog-phase">{phase || "Working…"}</span>
              <span className="prog-meta">{Math.floor(shown)}% · {fmtTime(elapsed)}</span>
            </div>
            <div className="prog-track"><div className="prog-fill" style={{ width: Math.max(2, shown) + "%" }} /></div>
            <div className="prog-note">
              A full assessment takes about two minutes — Shodan recon is the long part, then the AI
              writes the prose. Keep this tab open; refreshing cancels the run.
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
    </>
  );
}
