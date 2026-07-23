import { useEffect, useState } from "react";
import { Routes, Route, useNavigate } from "react-router-dom";
import Sidebar from "../components/Sidebar.jsx";
import NewAssessment from "./NewAssessment.jsx";
import Compliance from "./Compliance.jsx";
import Assistant from "./Assistant.jsx";
import History from "./History.jsx";
import { getMe } from "../api.js";

export default function Cabinet() {
  const nav = useNavigate();
  const [me, setMe] = useState(null);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    let live = true;
    getMe()
      .then((d) => { if (live) { setMe(d); setChecked(true); } })
      .catch((e) => { if (e.status === 401) nav("/login"); else nav("/login"); });
    return () => { live = false; };
  }, [nav]);

  if (!checked) {
    return (
      <div style={{ minHeight: "100vh", display: "grid", placeItems: "center" }}>
        <span className="spinner" style={{ width: 34, height: 34, borderWidth: 4 }} />
      </div>
    );
  }

  return (
    <div className="cab">
      <Sidebar email={me?.email} />
      <main className="main">
        <Routes>
          <Route path="/" element={<NewAssessment />} />
          <Route path="compliance" element={<Compliance />} />
          <Route path="assistant" element={<Assistant />} />
          <Route path="history" element={<History />} />
        </Routes>
      </main>
    </div>
  );
}
