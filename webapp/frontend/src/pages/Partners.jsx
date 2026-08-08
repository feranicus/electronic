// /partners — "Who it is for": fourteen one-page arguments, one per audience.
//
// THIS FILE HOLDS NO COPY. Every string comes from partners-locales/<lang>.js, so the layout lives
// in exactly one place and a translation can only change words. That is the same guarantee the
// GEOPOL HTML builder gives: a fixed shell with text injected, so no language can move a box, drop
// a column or reorder the page. Guarded by tools/partners_gate.mjs, which asserts every locale has
// the identical section ids in the identical order with the same number of columns and bullets.
//
// STRUCTURE per section is the Minto pyramid as the strategy houses teach it: Situation, then
// Complication, then ONE governing-thought Answer, then three grouped supports, then evidence,
// then the next step. The .scr block is that spine and it is not optional: the test fails a
// section that has no Answer, because a page without a governing thought is a list of features.
import { useMemo } from "react";
import { Link } from "react-router-dom";
import SiteHeader from "../components/SiteHeader.jsx";
import WhatsAppFab from "../components/WhatsAppFab.jsx";
import { useLegalLang, OPERATOR } from "../legal";
import { useT } from "../i18n.jsx";
import { partnersFor } from "../partners-locales/index.js";

// Inline emphasis: **bold** inside a bullet. A deliberately tiny subset of Markdown.
//
// WHY NOT dangerouslySetInnerHTML: the copy is ours, but a translator working in a locale file is
// one stray "<" away from breaking the page, and an HTML entity written in a JS string reaches the
// screen verbatim because React escapes it (that defect shipped to the live site once already).
// Splitting on ** and emitting real elements makes both classes impossible.
function rich(s, keyBase) {
  if (typeof s !== "string" || s.indexOf("**") === -1) return s;
  return s.split("**").map((part, i) => (
    i % 2 ? <b key={keyBase + i}>{part}</b> : <span key={keyBase + i}>{part}</span>
  ));
}

function Scr({ scr, t }) {
  if (!scr) return null;
  return (
    <div className="pscr">
      <div className="r s"><div className="k">{t("prt.situation")}</div><div className="v">{scr.s}</div></div>
      <div className="r c"><div className="k">{t("prt.complication")}</div><div className="v">{scr.c}</div></div>
      <div className="r a"><div className="k">{t("prt.answer")}</div><div className="v">{scr.a}</div></div>
    </div>
  );
}

function Section({ s, t }) {
  const three = (s.cols || []).length === 3;
  return (
    <article className={"pop" + (s.accent ? " acc-" + s.accent : "")} id={s.id}>
      <div className="p-eyebrow">{s.eyebrow}</div>
      <h2>{s.h2}</h2>
      {s.note && <p className="p-note">{s.note}</p>}

      <Scr scr={s.scr} t={t} />

      {s.quote && (
        <blockquote className="p-quote">
          {"“" + s.quote.q + "”"}
          <span>{s.quote.by}</span>
        </blockquote>
      )}

      {!!(s.cols || []).length && (
        <div className={"p-cols" + (three ? " three" : "")}>
          {s.cols.map((c, ci) => (
            <div className="p-col" key={c.h}>
              <h3>{c.h}</h3>
              <ul>{c.li.map((x, li) => <li key={li}>{rich(x, `${s.id}-${ci}-${li}-`)}</li>)}</ul>
            </div>
          ))}
        </div>
      )}

      {s.ladder && (
        <div className="p-ladder">
          <div className="h">{s.ladder.h}</div>
          <ol>{s.ladder.items.map((i, n) => <li key={n}><b>{i.b}</b> {i.t}</li>)}</ol>
        </div>
      )}

      {s.change && (
        <div className="p-change">
          <div className="h">{s.change.h}</div>
          <p className="lead">{s.change.lead}</p>
          <div className="p-diff">
            {s.change.cells.map((c) => (
              <div className={"p-dcell " + c.k} key={c.k}>
                <div className="t">{c.t}</div>
                <p>{c.before}<b>{c.b}</b>{c.after}</p>
              </div>
            ))}
          </div>
          <p className="tail">{s.change.tailBefore}<b>{s.change.tailBold}</b>{s.change.tailAfter}</p>
        </div>
      )}

      {s.vs && (
        <div className="p-vs">
          <div><h4>{s.vs.a.h}</h4><p>{s.vs.a.before}<b>{s.vs.a.bold}</b>{s.vs.a.after}</p></div>
          <div><h4>{s.vs.b.h}</h4><p>{s.vs.b.before}<b>{s.vs.b.bold}</b>{s.vs.b.after}</p></div>
        </div>
      )}

      {s.channel && (
        <div className="p-chan"><b>{s.channel.b}</b> {s.channel.t}</div>
      )}

      {s.win && (
        <div className="p-win"><div className="h">{s.win.h}</div><p>{s.win.p}</p></div>
      )}

      {!!(s.steps || []).length && (
        <div className="p-steps">
          {s.steps.map((st) => (
            <div className="p-step" key={st.k}><b>{st.k}</b><span>{st.v}</span></div>
          ))}
        </div>
      )}

      {s.cta && (
        <div className="p-cta">
          {s.id === "contact"
            ? (<>
                <a className="btn" href={"mailto:" + OPERATOR.email}>{s.cta.btn}</a>
                <Link className="btn ghost" to="/demo">{s.cta.ghost2}</Link>
              </>)
            : (<a className={"btn" + (s.cta.ghost ? " ghost" : "")} href="#contact">{s.cta.btn}</a>)}
          <span className="txt">{s.cta.txt}</span>
        </div>
      )}
    </article>
  );
}

export default function Partners() {
  const [lang] = useLegalLang();
  const [, , t] = useT();
  const C = useMemo(() => partnersFor(lang), [lang]);
  const { meta, arts, sections } = C;

  const groups = [
    ["partners", meta.groupPartners],
    ["buyers", meta.groupBuyers],
    ["engage", meta.groupEngage],
  ];

  return (
    <div className="partners">
      <SiteHeader />

      <div className="p-shell">
        {/* Sticky on desktop, a wrapped row of chips on a phone. Same treatment as the deep-dive
            rail on the landing page, so there is no new interaction to learn. */}
        <aside className="p-rail">
          <p className="rt">{meta.railTitle}</p>
          {groups.map(([g, label]) => (
            <div key={g}>
              <span className="sep">{label}</span>
              {sections.filter((s) => s.group === g).map((s) => (
                <a key={s.id} href={"#" + s.id}>{s.nav}</a>
              ))}
            </div>
          ))}
        </aside>

        <main className="p-main">
          <section className="p-intro">
            <div className="kick">{meta.kicker}</div>
            <h1>{meta.h1a}<br />{meta.h1b}<span className="g">{meta.h1c}</span>{meta.h1d}</h1>
            <p className="p-lede">{meta.lede}</p>

            <div className="p-arts">
              {arts.map((a) => (
                <div className="p-art" key={a.n}>
                  <b>{a.n}. {a.name}</b>
                  <span>{a.body}</span>
                </div>
              ))}
            </div>
            <p className="p-artnote">{meta.artsNote}</p>
          </section>

          {sections.map((s) => <Section key={s.id} s={s} t={t} />)}

          <div className="p-foot">{meta.foot}</div>
        </main>
      </div>

      <WhatsAppFab />
    </div>
  );
}
