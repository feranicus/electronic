// /impressum — legally required in Germany (§ 5 DDG). All identity data comes from OPERATOR in
// ../legal.jsx so the Impressum, the privacy controller section and the contact page cannot drift.
import { IMPRESSUM, OPERATOR, GROUP, controller, operatorReady, useLegalLang } from "../legal";
import { useT } from "../i18n.jsx";
import SiteHeader from "../components/SiteHeader.jsx";

export default function Impressum() {
  const [lang] = useLegalLang();
  const t = IMPRESSUM[lang];
  const [, , tk] = useT();
  const ready = operatorReady();
  const ctl = controller();

  return (
    <div className="legal">
      <SiteHeader />
      <div className="legal-head">
        <div>
          <h1 className="page-h">{t.h1}</h1>
          <p className="page-sub">{t.sub}</p>
        </div>
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

        {/* THE GROUP. The contracting and data-controller entity for cybergod.ai is
            Stars4business OÜ (GROUP.controllerId); the natural person above remains the German
            service provider under § 5 DDG and is responsible for content under § 18 (2) MStV.
            Both facts are true and a buyer needs to see both. */}
        <h2>{tk("grp.h")}</h2>
        <p className="imp-block" style={{ marginBottom: 10 }}>{tk("grp.p")}</p>
        <p className="imp-block">
          <strong>{tk("imp.ctl")}:</strong> {ctl.name}, {ctl.city}, {tk(ctl.jurisdictionKey)} &middot; {ctl.reg}
        </p>
        <div className="grp-grid" style={{ marginTop: 12 }}>
          {GROUP.entities.map((e) => (
            <div className="grp-card" key={e.id}>
              <span className="grp-flag">{e.flag}</span>
              <span className="grp-name">{e.name}</span>
              <span className="grp-juris">{tk(e.jurisdictionKey)} &middot; {e.type}</span>
              <span className="grp-role">{tk(e.roleKey)}</span>
              <span className="grp-reg">{e.reg}</span>
            </div>
          ))}
        </div>
        <p className="imp-block" style={{ marginTop: 12 }}>
          <a href="/experience">{tk("exp.h1")} &rarr;</a>
        </p>

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
