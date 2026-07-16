// /privacy — bilingual (DE reference text, EN translation). All copy lives in ../legal.jsx so the
// page and the Art.13 notice on the Assess screen can never drift apart.
import { PRIVACY, useLegalLang, LangToggle } from "../legal";

export default function Privacy() {
  const [lang, setLang] = useLegalLang();
  const t = PRIVACY[lang];

  return (
    <div className="legal">
      <div className="legal-head">
        <div>
          <h1 className="page-h">{t.h1}</h1>
          <p className="page-sub">{t.sub}</p>
        </div>
        <LangToggle lang={lang} setLang={setLang} />
      </div>

      <div className="panel legal-body">
        <p className="legal-lead">{t.lead}</p>

        <h2>{t.s1}</h2>
        <p>{t.s1p}</p>
        <p>{t.s1sub}</p>
        <ul>{t.s1list.map((x, i) => <li key={i}>{x}</li>)}</ul>
        <p className="legal-note">{t.s1note}</p>

        <h2>{t.s2}</h2>
        <table className="legal-table">
          <thead><tr>{t.th.map((h, i) => <th key={i}>{h}</th>)}</tr></thead>
          <tbody>
            {t.rows.map((r, i) => <tr key={i}>{r.map((c, j) => <td key={j}>{c}</td>)}</tr>)}
          </tbody>
        </table>
        <p>{t.s2note}</p>

        <h2>{t.s3}</h2>
        <ul>{t.s3list.map((x, i) => <li key={i}>{x}</li>)}</ul>

        <h2>{t.s4}</h2>
        <p>{t.s4p}</p>

        <h2>{t.s5}</h2>
        <ul>{t.s5list.map((x, i) => <li key={i}>{x}</li>)}</ul>

        <h2>{t.s6}</h2>
        <p>{t.s6p}</p>

        {/* DB-IP is CC-BY-4.0 — this credit is a licence condition, not decoration. Do not remove. */}
        <p className="legal-foot">
          {t.credit}
          <a href="https://db-ip.com" rel="noreferrer" target="_blank">IP Geolocation by DB-IP</a> (CC BY 4.0).
        </p>
        <p className="legal-foot"><strong>{t.disclaimerT}</strong>{t.disclaimer}</p>
      </div>
    </div>
  );
}
