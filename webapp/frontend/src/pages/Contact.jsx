// /contact — a direct line. Channels come from OPERATOR in ../legal.jsx; a channel with no handle
// set is rendered as "coming soon" rather than a dead link.
import { CONTACT, OPERATOR, useLegalLang, LangToggle } from "../legal";

const ICONS = {
  email: (<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="2.5" y="4.5" width="19" height="15" rx="2.5" /><path d="M3 6l9 7 9-7" /></svg>),
  li: (<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="3" /><path d="M7.5 10.5V17M7.5 7.6v.1M11.5 17v-3.6a2.4 2.4 0 0 1 4.8 0V17" /></svg>),
  tg: (<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M21 4L3 11l5 2 2 6 3-4 5 4z" /><path d="M8 13l9-6" /></svg>),
  gh: (<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 19c-4 1.4-4-2.2-6-2.8m12 4.8v-3.4a3 3 0 0 0-.8-2.3c2.7-.3 5.5-1.3 5.5-6a4.7 4.7 0 0 0-1.3-3.2 4.3 4.3 0 0 0-.1-3.2s-1-.3-3.4 1.3a11.7 11.7 0 0 0-6 0C6.5 2.4 5.5 2.7 5.5 2.7a4.3 4.3 0 0 0-.1 3.2A4.7 4.7 0 0 0 4 9.2c0 4.6 2.8 5.6 5.5 6a3 3 0 0 0-.8 2.3V21" /></svg>),
};

export default function Contact() {
  const [lang, setLang] = useLegalLang();
  const t = CONTACT[lang];

  const cards = [
    { k: "email", ic: ICONS.email, title: t.email, desc: t.emailD, href: "mailto:" + OPERATOR.email, label: OPERATOR.email },
    { k: "li",    ic: ICONS.li,    title: t.li,    desc: t.liD,    href: OPERATOR.linkedin, label: "LinkedIn" },
    { k: "tg",    ic: ICONS.tg,    title: t.tg,    desc: t.tgD,    href: OPERATOR.telegram, label: "Telegram" },
    { k: "gh",    ic: ICONS.gh,    title: t.gh,    desc: t.ghD,    href: OPERATOR.github,   label: "GitHub" },
  ];

  return (
    <div className="legal">
      <div className="legal-head">
        <div>
          <h1 className="page-h">{t.h1}</h1>
          <p className="page-sub">{t.sub}</p>
        </div>
        <LangToggle lang={lang} setLang={setLang} />
      </div>

      <p className="legal-lead" style={{ maxWidth: 760 }}>{t.lead}</p>

      <div className="ccards">
        {cards.map((c) => (
          c.href
            ? (<a key={c.k} className="ccard" href={c.href} target={c.k === "email" ? undefined : "_blank"} rel="noreferrer">
                 <span className="cico">{c.ic}</span>
                 <span className="ctit">{c.title}</span>
                 <span className="cdesc">{c.desc}</span>
                 <span className="clink">{c.label} &rarr;</span>
               </a>)
            : (<div key={c.k} className="ccard off">
                 <span className="cico">{c.ic}</span>
                 <span className="ctit">{c.title}</span>
                 <span className="cdesc">{c.desc}</span>
                 <span className="clink">{t.soon}</span>
               </div>)
        ))}
      </div>

      <div className="panel" style={{ marginTop: 18 }}>
        <h2 style={{ marginTop: 0, fontSize: 20 }}>{t.access}</h2>
        <p style={{ color: "var(--mut)", margin: 0, lineHeight: 1.6 }}>{t.accessD}</p>
      </div>

      <p className="legal-foot" style={{ marginTop: 16 }}>
        {t.legal}<a href="/impressum">Impressum</a> &middot; <a href="/privacy">Datenschutz / Privacy</a>
      </p>
    </div>
  );
}
