import { useEffect, useState } from "react";
import { getHistory } from "../api.js";

export default function History() {
  const [rows, setRows] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    getHistory()
      .then((d) => setRows(Array.isArray(d) ? d : []))
      .catch(() => setErr("Could not load history."));
  }, []);

  return (
    <>
      <h1 className="page-h">History</h1>
      <p className="page-sub">Every assessment you've run, with the decks ready to re-download.</p>

      {err && <div className="err">{typeof err === "string" ? err : JSON.stringify(err)}</div>}
      {rows === null && !err && (
        <div className="status-row"><span className="spinner" /> Loading…</div>
      )}
      {rows !== null && rows.length === 0 && (
        <div className="panel muted">No assessments yet. Run one from “New Assessment”.</div>
      )}
      {rows && rows.map((r) => (
        <div className="hrow" key={r.job_id}>
          <div>
            <div className="co">{r.company}</div>
            <div className="dt">{r.date}</div>
          </div>
          <div className="dl">
            {(r.decks || []).map((d) => (
              <a key={d.name} className="tag" href={d.url} download>{d.name}</a>
            ))}
          </div>
        </div>
      ))}
    </>
  );
}
