import { useEffect, useState } from "react";
import { adminUsers, adminSetUser, adminDisable, adminDeleteUser } from "../api.js";
import { useT } from "../i18n";

// ADMINISTRATION — create users, assign and reset passwords, see who can reach the platform.
//
// THE NAV ITEM AND THIS PAGE ARE PRESENTATION ONLY. Authorisation lives in the backend: every
// /api/admin/* route depends on _require_admin, which checks colt_auth.ADMIN_EMAILS. If this file
// were served to somebody who is not an administrator, every request it makes would return 403.
// Hiding a menu is not a control; anyone can issue the request the menu would have issued.
//
// THE PASSWORD IS SHOWN EXACTLY ONCE, here, right after it is set. It is never stored in plaintext,
// never emailed (that would put it in two mailboxes and a transit log, and the OTP already proves
// control of the mailbox, so mailing the password there collapses two factors into one channel),
// and it cannot be read back. Lost means reset, not recovered.

function ts(v) {
  if (!v) return "—";
  try { return new Date(v * 1000).toISOString().slice(0, 16).replace("T", " "); } catch { return "—"; }
}

export default function Admin() {
  const [, , t] = useT();
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [note, setNote] = useState("");
  const [issued, setIssued] = useState(null);   // { email, password } — shown once, then cleared
  const [q, setQ] = useState("");

  async function load() {
    setErr("");
    try {
      const body = await adminUsers();          // getJSON-backed: the parsed body
      setData(body);
    } catch (e) {
      setErr(e && e.status === 403 ? t("admin.forbidden") : t("admin.loadFail"));
    }
  }
  useEffect(() => { load(); }, []);             // eslint-disable-line react-hooks/exhaustive-deps

  async function submit(ev) {
    ev.preventDefault();
    setBusy(true); setErr(""); setIssued(null);
    const r = await adminSetUser(email.trim().toLowerCase(), pw.trim(), true, note.trim());
    setBusy(false);
    if (!r.ok) { setErr((r.data && r.data.detail) || t("admin.saveFail")); return; }
    setIssued({ email: r.data.user.email, password: r.data.password });
    setEmail(""); setPw(""); setNote("");
    load();
  }

  async function toggle(u) {
    setBusy(true);
    const r = await adminDisable(u.email, !u.disabled);
    setBusy(false);
    if (!r.ok) setErr((r.data && r.data.detail) || t("admin.saveFail"));
    load();
  }

  async function remove(u) {
    if (!window.confirm(t("admin.confirmRemove").replace("{email}", u.email))) return;
    setBusy(true);
    const r = await adminDeleteUser(u.email);
    setBusy(false);
    if (!r.ok) setErr((r.data && r.data.detail) || t("admin.saveFail"));
    load();
  }

  const users = ((data && data.users) || []).filter(
    (u) => !q.trim() || u.email.includes(q.trim().toLowerCase()));

  return (
    <div className="page">
      <h1>{t("admin.h1")}</h1>
      <p className="lede">{t("admin.lede")}</p>

      {err ? <div className="err">{err}</div> : null}

      {/* ---- issue or reset a password ---- */}
      <form className="card admin-new" onSubmit={submit}>
        <div className="assess-row">
          <div className="fld">
            <div className="label">{t("admin.email")}</div>
            <input className="input" value={email} onChange={(e) => setEmail(e.target.value)}
                   placeholder="name@company.com" autoComplete="off" required />
          </div>
          <div className="fld">
            <div className="label">{t("admin.password")}</div>
            <input className="input" value={pw} onChange={(e) => setPw(e.target.value)}
                   placeholder={t("admin.pwPlaceholder")} autoComplete="new-password" />
            <div className="hint">{t("admin.pwHint").replace(
              "{n}", String((data && data.min_password_len) || 12))}</div>
          </div>
          <div className="fld">
            <div className="label">{t("admin.note")}</div>
            <input className="input" value={note} onChange={(e) => setNote(e.target.value)}
                   placeholder={t("admin.notePlaceholder")} />
          </div>
          <button className="btn" disabled={busy || !email.trim()}>{t("admin.issue")}</button>
        </div>
      </form>

      {/* Shown once. There is no way to read it back afterwards, by design. */}
      {issued ? (
        <div className="card issued">
          <div className="issued-h">{t("admin.issuedH")}</div>
          <div className="issued-row">
            <span className="issued-email">{issued.email}</span>
            <code className="issued-pw">{issued.password}</code>
            <button type="button" className="btn ghost sm"
                    onClick={() => navigator.clipboard && navigator.clipboard.writeText(issued.password)}>
              {t("admin.copy")}
            </button>
            <button type="button" className="btn ghost sm" onClick={() => setIssued(null)}>
              {t("admin.dismiss")}
            </button>
          </div>
          <p className="issued-note">{t("admin.issuedNote")}</p>
        </div>
      ) : null}

      {/* ---- who can reach the platform ---- */}
      <div className="admin-head">
        <h2>{t("admin.usersH")}</h2>
        <input className="admin-q" value={q} onChange={(e) => setQ(e.target.value)}
               placeholder={t("admin.search")} aria-label={t("admin.search")} />
      </div>

      {data && !data.store_ok ? <div className="err">{t("admin.storeDown")}</div> : null}
      {data && data.shared_password_active ? (
        <p className="hint">{t("admin.sharedActive")}</p>
      ) : null}

      <div className="tablewrap">
        <table className="admin-tbl">
          <thead>
            <tr>
              <th>{t("admin.colEmail")}</th>
              <th>{t("admin.colAccess")}</th>
              <th>{t("admin.colState")}</th>
              <th>{t("admin.colLast")}</th>
              <th>{t("admin.colRuns")}</th>
              <th aria-label={t("admin.colActions")}></th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.email} className={u.disabled ? "row-off" : ""}>
                <td>
                  {u.email}
                  {u.is_admin ? <span className="tag admin">{t("admin.tagAdmin")}</span> : null}
                </td>
                <td>
                  {u.has_password
                    ? <span className="tag ok">{t("admin.tagAssigned")}</span>
                    : <span className="tag muted">{t("admin.tagShared")}</span>}
                  {!u.allowed ? <span className="tag warn">{t("admin.tagNotAllowed")}</span> : null}
                </td>
                <td>
                  {u.disabled ? <span className="tag off">{t("admin.tagDisabled")}</span> : null}
                  {u.must_change ? <span className="tag warn">{t("admin.tagMustChange")}</span> : null}
                  {!u.disabled && !u.must_change ? <span className="tag muted">{t("admin.tagActive")}</span> : null}
                </td>
                <td className="mono">{ts(u.last_login_ts)}</td>
                <td className="mono">
                  {u.assessments === null || u.assessments === undefined ? "—" : u.assessments}
                  {u.quota ? <span className="muted"> / {u.quota}</span> : null}
                </td>
                <td className="admin-actions">
                  {u.has_password && !u.is_admin ? (
                    <>
                      <button type="button" className="btn ghost sm" disabled={busy}
                              onClick={() => toggle(u)}>
                        {u.disabled ? t("admin.enable") : t("admin.disable")}
                      </button>
                      <button type="button" className="btn ghost sm danger" disabled={busy}
                              onClick={() => remove(u)}>
                        {t("admin.remove")}
                      </button>
                    </>
                  ) : null}
                </td>
              </tr>
            ))}
            {!users.length ? (
              <tr><td colSpan="6" className="muted">{data ? t("admin.none") : t("admin.loading")}</td></tr>
            ) : null}
          </tbody>
        </table>
      </div>
      <p className="hint">{t("admin.removeNote")}</p>
    </div>
  );
}
