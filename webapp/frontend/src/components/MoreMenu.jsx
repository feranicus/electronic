// MoreMenu — the button beside Demo that opens Who we are / Contact / Impressum / Privacy.
//
// WHY IT EXISTS, two reasons that turned out to be the same problem:
//
// 1. DESKTOP ARITHMETIC. #hd .wrap is a fixed-height flex row. Adding "Who we are" to the nav
//    pushed the German row past the viewport: "Zur Anwendung" wrapped and landed on top of the
//    page heading. A fixed-height horizontal bar is an arithmetic problem — brand + every control
//    + gaps, measured (tools/header_layout.mjs) before shipping.
// 2. MOBILE HAD NO ROUTE AT ALL. `#hd nav a:not(.btn){display:none}` hides every plain link on a
//    phone, so on the installed PWA there was no way to reach Contact, Impressum or Who we are.
//
// ============================================================================================
// WHY THE PANEL IS A PORTAL — the bug the operator filmed (7 Aug 2026)
// ============================================================================================
// On Android the menu opened and NOTHING appeared. Eight taps, no panel. It worked perfectly on
// desktop, which is what made it look like a touch-event problem; it was not. Measured on the
// live page:
//
//     .more-p   z-index 60   trapped: true      <- sealed inside #hd
//     #hd       z-index 20   position: sticky   <- sticky + z-index = a STACKING CONTEXT
//     <video>   top: 123px                      <- exactly where the panel drops
//
// A z-index inside a stacking context is ordered only against its SIBLINGS. `.more-p` at 60 does
// not compete with the page at 60 — the whole header competes, at 20. And on Android a <video> is
// promoted to a hardware overlay layer, which paints above non-composited content irrespective of
// paint order. On /demo the video starts immediately below the header, so the entire panel was
// drawn underneath it. On desktop the video is `position:static` and loses to any positioned
// element, so the same code was visibly fine — the failure needed BOTH a stacking context and a
// composited overlay to show up.
//
// So the panel now renders through a PORTAL to <body>: outside #hd, outside every ancestor's
// stacking context and clip, on its own compositing layer. It is positioned `fixed` from the
// trigger's measured rect rather than `absolute` from an ancestor, which also means no ancestor
// overflow can ever clip it.
//
// The outside-click close is now a real BACKDROP element rather than a document mousedown
// listener. A listener attached in an effect races the very gesture that opened the menu and has
// to be reasoned about per platform; an element that covers the screen simply receives the tap.
//
// SSR-SAFE: the i18n audit renders this on the server in 6 languages. createPortal needs a real
// document, so the portal is gated on a mounted flag — the server renders the trigger only.
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Link, useLocation } from "react-router-dom";
import { useT } from "../i18n.jsx";

const PHONE = 720;

// useLayoutEffect warns on the server because its effect cannot be encoded into the SSR output.
// The audit FILTERS that warning, and a filter is how a real error learns to hide — so avoid
// emitting it instead: on the server there is no layout to measure, so useEffect is correct.
const useIsoLayout = typeof window === "undefined" ? useEffect : useLayoutEffect;

export default function MoreMenu() {
  const [, , t] = useT();
  const [open, setOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [pos, setPos] = useState(null);
  const btn = useRef(null);
  const { pathname } = useLocation();

  useEffect(() => { setMounted(true); }, []);
  // Route change closes it. Without this the panel stays open over the new page after a tap.
  useEffect(() => { setOpen(false); }, [pathname]);

  // Anchor the fixed panel under the trigger. useLayoutEffect so it is placed before the browser
  // paints — with useEffect the panel flashes at the top-left corner for one frame.
  const place = useCallback(() => {
    const b = btn.current;
    if (!b) return;
    const r = b.getBoundingClientRect();
    setPos({ top: Math.round(r.bottom + 8), right: Math.round(window.innerWidth - r.right) });
  }, []);

  useIsoLayout(() => { if (open) place(); }, [open, place]);

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => { if (e.key === "Escape") { setOpen(false); btn.current?.focus(); } };
    // The panel is anchored to a rect, so anything that moves the trigger must re-anchor it.
    // Closing on scroll is deliberate: a menu that drifts away from its button looks broken.
    const onScroll = () => setOpen(false);
    window.addEventListener("keydown", onKey);
    window.addEventListener("resize", place);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("resize", place);
      window.removeEventListener("scroll", onScroll);
    };
  }, [open, place]);

  const items = [
    { to: "/experience", label: t("nav.about") },
    { to: "/contact", label: t("nav.contact") },
    { to: "/impressum", label: "Impressum" },
    { to: "/privacy", label: t("nav.privacy") },
  ];

  const phone = mounted && typeof window !== "undefined" && window.innerWidth <= PHONE;

  return (
    <div className="moremenu">
      <button
        ref={btn}
        type="button"
        className="more-t"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        {/* NOT a .btn. `.btn.sm.ghost` gave it a 999px radius and a 34px min-height around a ~6px
            glyph — a hollow circle beside the language pill, which is what the operator kept
            calling broken. The LABEL is what stops it reading as a circle, so it is shown on a
            phone too; tools/header_layout.mjs measures that the row still fits at 360px. */}
        <svg className="more-i" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
          <path d="M3 6h14M3 10h14M3 14h9" />
        </svg>
        <span className="more-l">{t("nav.more")}</span>
      </button>

      {mounted && open && createPortal(
        <>
          {/* A real element, not a document listener: it cannot race the opening gesture. */}
          <div className="more-bd" onClick={() => setOpen(false)} />
          <div
            className={"more-p" + (phone ? " sheet" : "")}
            role="menu"
            style={phone ? undefined : { top: pos?.top ?? 0, right: pos?.right ?? 0 }}
          >
            {phone && <div className="more-grab" aria-hidden="true" />}
            {items.map((i) => (
              <Link key={i.to} role="menuitem" to={i.to} onClick={() => setOpen(false)}>
                {i.label}
              </Link>
            ))}
          </div>
        </>,
        document.body
      )}
    </div>
  );
}
