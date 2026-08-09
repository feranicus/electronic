// The phone's bottom tab bar: Why · Live · Machine · Deep · Secure · Open.
//
// ============================================================================================
// WHY IT IS NOW SELF-CONTAINED AND ON EVERY PUBLIC PAGE (operator report, 9 Aug 2026)
// ============================================================================================
// It used to live only on the landing page, with its tab list, active state and click handler all
// owned by Landing.jsx. So on the installed app, tapping anything in the More menu, or Demo, or
// even the bar's OWN "Open" tab, landed the user on a page with NO bottom navigation at all. The
// only way back was the Android back button, which a standalone PWA does not always show. That is
// the same defect the More menu was created to fix, one level up: a phone user reached a dead end.
//
// The tab targets are SECTIONS OF THE LANDING PAGE, so the behaviour has to differ by route:
//   · on "/"        scroll to the section in place, and let Landing's scroll-spy light the tab;
//   · anywhere else navigate to "/#<id>". An in-page jump to a section that does not exist on
//                   this page would silently do nothing, which is exactly the trap SiteHeader's
//                   nav anchors already document.
// The "Open" tab goes to /login and works identically everywhere.
//
// PROPS ARE OPTIONAL. Landing still passes `active` and `onGo` because it owns the scroll-spy and
// smooth scrolling; every other page renders a bare <TabBar /> and this component handles the
// navigation itself. One component, one tab list, so the bar cannot differ between pages.
//
// NOT IN THE CABINET (/app). That has its own bottom navigation (Assess · Compliance · Assistant ·
// History) and two docked bars would overlap. Guarded by tests/test_routes.py.
import { useNavigate, useLocation } from "react-router-dom";
import { useT } from "../i18n.jsx";

const ICONS = {
  edge:   (<><path d="M13 2L4.5 13H11l-1 9 8.5-11H12z" /></>),
  demo:   (<><rect x="3" y="4" width="18" height="14" rx="2.5" /><path d="M10.5 8.5l4.5 2.6-4.5 2.6z" /><path d="M8 21h8" /></>),
  map:    (<><circle cx="5.5" cy="6" r="2.2" /><circle cx="18.5" cy="6" r="2.2" /><circle cx="12" cy="18" r="2.2" /><path d="M7.4 7.3L10.9 16M16.6 7.3L13.1 16M7.7 6h8.6" /></>),
  deep:   (<><path d="M12 3l9 4.5-9 4.5-9-4.5z" /><path d="M3 12l9 4.5 9-4.5" /><path d="M3 16.5L12 21l9-4.5" /></>),
  secure: (<><path d="M12 3l8 3.5v5c0 5-3.5 8.5-8 9.5-4.5-1-8-4.5-8-9.5v-5z" /><path d="M9 12l2 2 4-4" /></>),
  app:    (<><path d="M14 3h5a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-5" /><path d="M10 17l5-5-5-5" /><path d="M15 12H3" /></>),
};

/** The one tab list. Landing imports this so the two can never drift apart. */
export function tabsFor(t) {
  return [
    { id: "edge", label: t("tab.why"), href: "#edge" },
    { id: "demo", label: t("tab.live"), href: "#demo" },
    { id: "map", label: t("tab.machine"), href: "#map" },
    { id: "deep", label: t("tab.deep"), href: "#deep" },
    { id: "secure", label: t("tab.secure"), href: "#secure" },
    { id: "app", label: t("tab.open"), to: "/login" },
  ];
}

export default function TabBar({ tabs, active, onGo }) {
  const [, , t] = useT();
  const nav = useNavigate();
  const { pathname } = useLocation();
  const list = tabs || tabsFor(t);

  // Off the landing page a section tab is a ROUTE change, not a scroll. Landing reads the hash on
  // mount and scrolls there, so the user lands on the section they asked for.
  const go = (tab) => {
    if (onGo) return onGo(tab);
    if (tab.to) return nav(tab.to);
    if (pathname === "/") {
      const el = document.querySelector(tab.href);
      if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }
    nav("/" + tab.href);
  };

  return (
    <nav className="tabbar" aria-label="Sections">
      {list.map((tab) => (
        <button key={tab.id} type="button"
          className={active === tab.id ? "tb on" : "tb"}
          aria-current={active === tab.id ? "true" : undefined}
          onClick={() => go(tab)}>
          <svg viewBox="0 0 24 24" aria-hidden="true">{ICONS[tab.id]}</svg>
          {tab.label}
        </button>
      ))}
    </nav>
  );
}
