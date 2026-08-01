import { useEffect, useState } from "react";
import { getHistory } from "../api.js";
import { useT } from "../i18n";

export default function History() {
  const [rows, setRows] = useState(null);
  const [err, setErr] = useState("");
  const [, , t] = useT();

  useEffect(() => {
    getHistory()
      .then((d) => setRows(Array.isArray(d) ? d : []))
      .catch(() => setErr(t("hist.err")));
    // deps stay EMPTY on purpose: adding `t` would re-fire the fetch on every language switch.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <>
      <h1 className="page-h">{t("hist.h1")}</h1>
      <p className="page-sub">{t("hist.sub")}</p>

      {err && <div className="err">{typeof err === "string" ? err : JSON.stringify(err)}</div>}
      {rows === null && !err && (
        <div className="status-row"><span className="spinner" /> {t("hist.loading")}</div>
      )}
      {rows !== null && rows.length === 0 && (
        <div className="panel muted">{t("hist.empty")}</div>
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
