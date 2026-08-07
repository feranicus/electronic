// MoreMenu — the "…" button beside Demo that opens Who we are / Contact / Impressum / Privacy.
//
// WHY IT EXISTS, two reasons that turned out to be the same problem:
//
// 1. DESKTOP ARITHMETIC. #hd .wrap is a fixed-height flex row. Adding "Who we are" to the nav
//    pushed the German row past the viewport: "Zur Anwendung" wrapped and landed on top of the
//    page heading. CLAUDE.md has recorded twice that a fixed-height horizontal bar is an
//    arithmetic problem — brand + every control + gaps, measured, before shipping. I added a
//    control and did not re-measure. German is systematically longer and overflows first.
// 2. MOBILE HAD NO ROUTE AT ALL. `#hd nav a:not(.btn){display:none}` hides every plain link on a
//    phone, and the bottom tab bar is full at six items. So on the installed PWA there was no way
//    to reach Contact, Impressum or Who we are from anywhere.
//
// One collapsed menu answers both: the row loses two links and gains one compact trigger, and the
// phone gets the only entry point it was missing.
//
// SSR-SAFE: the audit renders this on the server in 6 languages. No window/document access outside
// an effect, and the closed state renders the trigger only.
import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useT } from "../i18n.jsx";

export default function MoreMenu() {
  const [, , t] = useT();
  const [open, setOpen] = useState(false);
  const box = useRef(null);
  const { pathname } = useLocation();

  // Route change closes it. Without this the panel stays open over the new page after a tap.
  useEffect(() => { setOpen(false); }, [pathname]);

  const onDoc = useCallback((e) => {
    if (box.current && !box.current.contains(e.target)) setOpen(false);
  }, []);

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open, onDoc]);

  const items = [
    { to: "/experience", label: t("nav.about") },
    { to: "/contact", label: t("nav.contact") },
    { to: "/impressum", label: "Impressum" },
    { to: "/privacy", label: t("nav.privacy") },
  ];

  return (
    <div className="moremenu" ref={box}>
      <button
        type="button"
        className="btn sm ghost more-t"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={t("nav.more")}
        onClick={() => setOpen((v) => !v)}
      >
        {/* The word on a wide screen, the glyph on a phone — chosen in CSS so there is no resize
            listener and no second source of truth for the breakpoint. */}
        <span className="lg">{t("nav.more")}</span>
        <span className="sm" aria-hidden="true">&#8942;</span>
      </button>
      {open && (
        <div className="more-p" role="menu">
          {items.map((i) => (
            <Link key={i.to} role="menuitem" to={i.to} onClick={() => setOpen(false)}>{i.label}</Link>
          ))}
        </div>
      )}
    </div>
  );
}
