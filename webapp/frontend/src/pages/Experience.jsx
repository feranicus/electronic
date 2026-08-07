// /experience — "Who we are": the group's four registrations, the principal's pedigree, and the
// engagements actually delivered. Linked from /contact and /impressum.
//
// WHY THIS PAGE EXISTS. The reseller's objection on the RBC call was blunt and correct: a buyer who
// cannot see who is behind the product looks up the vendor, finds a small OÜ, and stops the
// conversation. The answer is not to hide the structure — it is to publish it, with registration
// numbers a buyer can verify and a delivery record they can check.
//
// EVERY FACT HERE COMES FROM legal.jsx (GROUP, PRINCIPAL). Company names, client names, VAT numbers
// and technology names are proper nouns and are NOT translated; only the surrounding prose is.
import { GROUP, PRINCIPAL, OPERATOR, useLegalLang, LangToggle } from "../legal";
import { useT } from "../i18n.jsx";
import SiteHeader from "../components/SiteHeader.jsx";

export default function Experience() {
  const [lang, setLang] = useLegalLang();
  const [, , t] = useT();

  return (
    <div className="legal">
      <SiteHeader />
      <div className="legal-head">
        <div>
          <h1 className="page-h">{t("exp.h1")}</h1>
          <p className="page-sub">{t("exp.sub")}</p>
        </div>
        <LangToggle lang={lang} setLang={setLang} />
      </div>

      <p className="legal-lead" style={{ maxWidth: 780 }}>{t("exp.lead")}</p>

      {/* ---- the group ------------------------------------------------------------------ */}
      <h2 className="exp-h2">{t("grp.h")}</h2>
      <p className="exp-p">{t("grp.p")}</p>
      <div className="grp-grid">
        {GROUP.entities.map((e) => (
          <div className="grp-card" key={e.id}>
            <span className="grp-flag">{e.flag}</span>
            <span className="grp-name">{e.name}</span>
            <span className="grp-juris">{t(e.jurisdictionKey)} · {e.type}</span>
            <span className="grp-role">{t(e.roleKey)}</span>
            <span className="grp-reg">{e.reg}</span>
            <span className="grp-city">{[e.street, e.city].filter(Boolean).join(", ")}</span>
          </div>
        ))}
      </div>
      <p className="exp-note">{t("grp.note")}</p>

      {/* ---- the principal --------------------------------------------------------------- */}
      <h2 className="exp-h2">{t("exp.who")}</h2>
      <p className="exp-p">
        <strong>{PRINCIPAL.name}</strong> — {t("exp.role")}. {t("exp.whoP")}
      </p>
      <div className="tribe-grid">
        {PRINCIPAL.tribes.map((tr) => (
          <div className="tribe" key={tr.k}>
            <span className="tribe-h">{t(tr.k)}</span>
            <span className="tribe-n">{tr.names.join(" · ")}</span>
          </div>
        ))}
      </div>

      {/* ---- delivered ------------------------------------------------------------------- */}
      <h2 className="exp-h2">{t("exp.work")}</h2>
      <p className="exp-p">{t("exp.workP")}</p>
      <div className="work-grid">
        {PRINCIPAL.work.map((w) => (
          <div className="work" key={w.client}>
            <span className="work-c">{w.client}</span>
            <span className="work-s">{t(w.sector)}</span>
            <span className="work-w">{t(w.what)}</span>
          </div>
        ))}
      </div>
      <p className="exp-note">{t("exp.workNote")}</p>

      {/* ---- builds it too ---------------------------------------------------------------- */}
      <h2 className="exp-h2">{t("exp.build")}</h2>
      <p className="exp-p">{t("exp.buildP")}</p>
      <div className="chips">{PRINCIPAL.langs.map((l) => <span className="chip" key={l}>{l}</span>)}</div>
      <p className="exp-p" style={{ marginTop: 14 }}>
        {t("exp.oss")}{" "}
        {PRINCIPAL.oss.map((o, i) => (
          <span key={o.name}>
            {i > 0 ? " · " : ""}
            <a href={o.href} target="_blank" rel="noreferrer">{o.name}</a>
          </span>
        ))}
      </p>

      <div className="panel" style={{ marginTop: 22 }}>
        <h2 style={{ marginTop: 0, fontSize: 20 }}>{t("exp.talk")}</h2>
        <p style={{ color: "var(--mut)", margin: "0 0 12px", lineHeight: 1.6 }}>{t("exp.talkP")}</p>
        <a className="btn sm" href="/contact">{t("nav.contact")} &rarr;</a>{" "}
        <a className="btn sm ghost" href={"mailto:" + OPERATOR.email}>{OPERATOR.email}</a>
      </div>

      <p className="legal-foot" style={{ marginTop: 16 }}>
        <a href="/impressum">Impressum</a> &middot; <a href="/privacy">Datenschutz / Privacy</a> &middot;{" "}
        <a href="/contact">{t("nav.contact")}</a>
      </p>
    </div>
  );
}
