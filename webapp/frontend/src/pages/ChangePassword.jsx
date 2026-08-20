import { useState } from "react";
import { changePassword } from "../api.js";
import { useT } from "../i18n";

// Shown INSTEAD of the cabinet while the server says a password change is owed, and reachable
// voluntarily from the sidebar at any other time.
//
// The blocking is NOT done here. Every functional endpoint depends on _require_ready, which refuses
// with 403 password_change_required until the change is made. This screen exists so the user is
// told why, rather than meeting a wall of failed requests. A control that lives only in the router
// is a suggestion.
export default function ChangePassword({ forced = false, onDone }) {
  const [, , t] = useT();
  const [cur, setCur] = useState("");
  const [a, setA] = useState("");
  const [b, setB] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(ev) {
    ev.preventDefault();
    setErr("");
    if (a !== b) { setErr(t("pw.mismatch")); return; }
    setBusy(true);
    const r = await changePassword(cur, a);
    setBusy(false);
    if (!r.ok) { setErr((r.data && r.data.detail) || t("pw.fail")); return; }
    setCur(""); setA(""); setB("");
    if (onDone) onDone();
  }

  return (
    <div className="page pw-page">
      <h1>{forced ? t("pw.h1Forced") : t("pw.h1")}</h1>
      <p className="lede">{forced ? t("pw.ledeForced") : t("pw.lede")}</p>
      {err ? <div className="err">{err}</div> : null}
      <form className="card pw-form" onSubmit={submit}>
        {/* On a forced change the user proved the old password and the OTP minutes ago, so asking
            for it again adds a step and no assurance. Everywhere else it is required: a session
            cookie is a bearer token, and without this a borrowed laptop is a password change. */}
        {!forced ? (
          <div className="fld">
            <div className="label">{t("pw.current")}</div>
            <input className="input" type="password" value={cur} onChange={(e) => setCur(e.target.value)}
                   autoComplete="current-password" required />
          </div>
        ) : null}
        <div className="fld">
          <div className="label">{t("pw.new")}</div>
          <input className="input" type="password" value={a} onChange={(e) => setA(e.target.value)}
                 autoComplete="new-password" required minLength={12} />
        </div>
        <div className="fld">
          <div className="label">{t("pw.repeat")}</div>
          <input className="input" type="password" value={b} onChange={(e) => setB(e.target.value)}
                 autoComplete="new-password" required minLength={12} />
        </div>
        <button className="btn" disabled={busy || !a || !b}>{t("pw.save")}</button>
      </form>
      <p className="hint">{t("pw.hint")}</p>
    </div>
  );
}
