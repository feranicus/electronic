// /impressum — legally required in Germany (§ 5 DDG). All identity data comes from OPERATOR in
// ../legal.jsx so the Impressum, the privacy controller section and the contact page cannot drift.
import { IMPRESSUM, OPERATOR, operatorReady, useLegalLang, LangToggle } from "../legal";
import SiteHeader from "../components/SiteHeader.jsx";

export default function Impressum() {
  const [lang, setLang] = useLegalLang();
  const t = IMPRESSUM[lang];
  const ready = operatorReady();

  return (
    <div className="legal">
      <SiteHeader />
      <div className="legal-head">
        <div>
          <h1 className="page-h">{t.h1}</h1>
          <p className="page-sub">{t.sub}</p>
        </div>
        <LangToggle lang={lang} setLang={setLang} />
      </div>

      <div className="panel legal-body">
        {!ready && <p className="legal-todo">{t.todo}</p>}

        <h2>{t.s1}</h2>
        <p className="imp-block">
          <strong>{OPERATOR.name}</strong><br />
          {OPERATOR.street}<br />
          {OPERATOR.zipCity}<br />
          {OPERATOR.country}
        </p>

        <h2>{t.s2}</h2>
        <p className="imp-block">
          E-Mail: <a href={"mailto:" + OPERATOR.email}>{OPERATOR.email}</a><br />
          Tel.: {OPERATOR.phone}
        </p>

        <h2>{t.s3}</h2>
        <p className="imp-block">
          <strong>{OPERATOR.name}</strong><br />
          {OPERATOR.street}, {OPERATOR.zipCity}, {OPERATOR.country}
        </p>

        {OPERATOR.vatId ? (<><h2>{t.s4}</h2><p className="imp-block">{OPERATOR.vatId}</p></>) : null}

        <h2>{t.s5}</h2>
        <p>{t.s5p}</p>

        <h2>{t.s6}</h2>
        <p>{t.s6p}</p>

        <h2>{t.s7}</h2>
        <p>{t.s7p}</p>

        <p className="legal-foot">{t.note}</p>
      </div>
    </div>
  );
}
