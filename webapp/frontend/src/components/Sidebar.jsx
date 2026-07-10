import { NavLink } from "react-router-dom";
import { authLogout } from "../api.js";
import { useNavigate } from "react-router-dom";

const items = [
  ["/app", "New Assessment", true],
  ["/app/assistant", "Assistant"],
  ["/app/history", "History"],
];

export default function Sidebar({ email }) {
  const nav = useNavigate();
  async function logout() {
    try { await authLogout(); } catch { /* ignore */ }
    nav("/login");
  }
  return (
    <aside className="side">
      <div className="brand"><span className="chev">❯</span> colt</div>
      <nav className="nav">
        {items.map(([to, label, end]) => (
          <NavLink key={to} to={to} end={!!end}>{label}</NavLink>
        ))}
      </nav>
      <div className="who">
        signed in as
        <b>{email || "…"}</b>
        <button className="btn ghost sm logout" onClick={logout}>Log out</button>
      </div>
    </aside>
  );
}
