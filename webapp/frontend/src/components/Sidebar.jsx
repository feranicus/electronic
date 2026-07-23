import { NavLink, useNavigate } from "react-router-dom";
import { authLogout } from "../api.js";

// Desktop: a left sidebar. Phone: the SAME DOM becomes a compact top bar + a bottom tab bar —
// driven entirely by CSS (see .topbar / .side in styles.css). One component, one set of routes:
// a second "mobile version" would drift the moment anyone adds a page.
const items = [
  ["/app", "Assess", true, (
    <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /></svg>
  )],
  ["/app/compliance", "Compliance", false, (
    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3l7 3v5c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6z" /><path d="M9 12l2 2 4-4" /></svg>
  )],
  ["/app/assistant", "Assistant", false, (
    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M21 12a8 8 0 1 1-3.2-6.4" /><path d="M12 8v4l3 2" /></svg>
  )],
  ["/app/history", "History", false, (
    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 12a9 9 0 1 0 3-6.7L3 8" /><path d="M3 4v4h4" /><path d="M12 8v4l3 2" /></svg>
  )],
];

export default function Sidebar({ email }) {
  const nav = useNavigate();
  async function logout() {
    try { await authLogout(); } catch { /* ignore */ }
    nav("/login");
  }
  return (
    <>
      {/* phone-only: brand + logout, so the bottom bar can be pure navigation */}
      <header className="topbar">
        <div className="brand"><span className="chev">❯</span> colt</div>
        <button className="btn ghost sm" onClick={logout} aria-label="Log out">Log out</button>
      </header>

      <aside className="side">
        <div className="brand"><span className="chev">❯</span> colt</div>
        <nav className="nav">
          {items.map(([to, label, end, icon]) => (
            <NavLink key={to} to={to} end={!!end}>
              <span className="nav-ico">{icon}</span>
              <span className="nav-label">{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="who">
          signed in as
          <b>{email || "…"}</b>
          <button className="btn ghost sm logout" onClick={logout}>Log out</button>
        </div>
      </aside>
    </>
  );
}
