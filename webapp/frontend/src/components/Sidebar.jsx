import { NavLink, useNavigate } from "react-router-dom";
import { authLogout } from "../api.js";
import { useT } from "../i18n";

// Desktop: a left sidebar. Phone: the SAME DOM becomes a compact top bar + a bottom tab bar —
// driven entirely by CSS (see .topbar / .side in styles.css). One component, one set of routes:
// a second "mobile version" would drift the moment anyone adds a page.
//
// The second element is an i18n KEY, not a label: this array is module-scope so it cannot call the
// hook. Resolved with t() at render time. These labels are LENGTH-CONSTRAINED — the same four sit
// in the narrow desktop rail and in the phone bottom bar; see the note on side.* in locales/en.js.
const items = [
  ["/app", "side.assess", true, (
    <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /></svg>
  )],
  ["/app/compliance", "side.compliance", false, (
    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3l7 3v5c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6z" /><path d="M9 12l2 2 4-4" /></svg>
  )],
  ["/app/assistant", "side.assistant", false, (
    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M21 12a8 8 0 1 1-3.2-6.4" /><path d="M12 8v4l3 2" /></svg>
  )],
  ["/app/history", "side.history", false, (
    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 12a9 9 0 1 0 3-6.7L3 8" /><path d="M3 4v4h4" /><path d="M12 8v4l3 2" /></svg>
  )],
];

export default function Sidebar({ email }) {
  const nav = useNavigate();
  const [, , t] = useT();
  async function logout() {
    try { await authLogout(); } catch { /* ignore */ }
    nav("/login");
  }
  return (
    <>
      {/* phone-only: brand + logout, so the bottom bar can be pure navigation */}
      <header className="topbar">
        <div className="brand"><span className="chev">❯</span> cybergod<span class="g">.ai</span></div>
        <button className="btn ghost sm" onClick={logout} aria-label={t("side.logout")}>{t("side.logout")}</button>
      </header>

      <aside className="side">
        <div className="brand"><span className="chev">❯</span> cybergod<span class="g">.ai</span></div>
        <nav className="nav">
          {items.map(([to, label, end, icon]) => (
            <NavLink key={to} to={to} end={!!end}>
              <span className="nav-ico">{icon}</span>
              <span className="nav-label">{t(label)}</span>
            </NavLink>
          ))}
        </nav>
        <div className="who">
          {t("side.signedIn")}
          <b>{email || "…"}</b>
          <button className="btn ghost sm logout" onClick={logout}>{t("side.logout")}</button>
          <div className="side-legal">
            <a href="/impressum">{t("side.impressum")}</a><span>&middot;</span>
            <a href="/privacy">{t("side.privacy")}</a><span>&middot;</span>
            <a href="/contact">{t("side.contact")}</a>
          </div>
        </div>
      </aside>
    </>
  );
}
