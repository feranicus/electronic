import { useCallback, useEffect, useState } from "react";
import { Routes, Route, useNavigate } from "react-router-dom";
import Sidebar from "../components/Sidebar.jsx";
import NewAssessment from "./NewAssessment.jsx";
import Compliance from "./Compliance.jsx";
import Assistant from "./Assistant.jsx";
import History from "./History.jsx";
import Admin from "./Admin.jsx";
import ChangePassword from "./ChangePassword.jsx";
import { getMe } from "../api.js";

export default function Cabinet() {
  const nav = useNavigate();
  const [me, setMe] = useState(null);
  const [checked, setChecked] = useState(false);

  // getMe is getJSON-backed: it returns the PARSED BODY { email, is_admin, must_change }, not
  // { ok, data }. Destructuring {ok, data} here would silently yield undefined for both and every
  // guard below would fail closed — the defect api_contract.mjs exists to catch.
  const refresh = useCallback(() => getMe()
    .then((d) => { setMe(d); setChecked(true); return d; })
    .catch(() => { nav("/login"); }), [nav]);

  useEffect(() => { refresh(); }, [refresh]);

  if (!checked) {
    return (
      <div style={{ minHeight: "100vh", display: "grid", placeItems: "center" }}>
        <span className="spinner" style={{ width: 34, height: 34, borderWidth: 4 }} />
      </div>
    );
  }

  // A password issued by an administrator is temporary. Until it is replaced the cabinet is not
  // rendered at all — but the real refusal is server-side (_require_ready returns 403
  // password_change_required), so a client that skipped this screen would still get nowhere.
  if (me && me.must_change) {
    return (
      <div className="cab">
        <Sidebar email={me.email} isAdmin={false} />
        <main className="main">
          <ChangePassword forced onDone={refresh} />
        </main>
      </div>
    );
  }

  return (
    <div className="cab">
      <Sidebar email={me?.email} isAdmin={!!(me && me.is_admin)} />
      <main className="main">
        <Routes>
          <Route path="/" element={<NewAssessment />} />
          <Route path="compliance" element={<Compliance />} />
          <Route path="assistant" element={<Assistant />} />
          <Route path="history" element={<History />} />
          <Route path="password" element={<ChangePassword onDone={refresh} />} />
          {/* Rendered only for an administrator. This is convenience, not security: /api/admin/*
              refuses anyone not on colt_auth.ADMIN_EMAILS regardless of what the SPA renders. */}
          {me && me.is_admin ? <Route path="admin" element={<Admin />} /> : null}
        </Routes>
      </main>
    </div>
  );
}
