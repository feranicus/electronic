import { useEffect, useState } from "react";
import { adminUsers, adminSetUser, adminDisable, adminDeleteUser, adminSetRole } from "../api.js";
import { useT } from "../i18n";
import Fleet from "./Fleet.jsx";

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
  // A sub-menu, as asked for: Users | Fleet. The tab is PRESENTATION ONLY -- every
  // /api/admin/* route independently depends on _require_admin, so hiding a tab is not
  // a control and showing one grants nothing.
  const [adminTab, setAdminTab] = useState("users");
  // A ROLE CHANGE IS NOT SAVED UNTIL IT IS APPLIED. The first version wrote on every `change`
  // event, so a mis-click was a silent privilege change with nothing on screen to say so. The
  // picker now holds a PENDING value per address and the Apply button is the commit.
  const [pending, setPending] = useState({});      // email -> role chosen but not yet applied
  const [saved, setSaved] = useState("");          // the confirmation line, cleared on next action
  const [newRole, setNewRole] = useState("user");  // the role the create form will grant
  const [showPerms, setShowPerms] = useState(false);

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
    setBusy(true); setErr(""); setIssued(null); setSaved("");
    const r = await adminSetUser(email.trim().toLowerCase(), pw.trim(), true, note.trim(),
                                 newRole === "user" ? "" : newRole);
    setBusy(false);
    if (!r.ok) { setErr((r.data && r.data.detail) || t("admin.saveFail")); return; }
    setIssued({ email: r.data.user.email, password: r.data.password });
    // THE SERVER DECIDES WHETHER THE ROLE WAS APPLIED, and says so when it was not. The account
    // exists either way, so reporting "created" with no word about the role would be a lie by
    // omission the administrator only discovers when the person cannot do their job.
    if (r.data.role_error) setErr(r.data.role_error);
    else setSaved(t("admin.roleSaved").replace("{email}", r.data.user.email)
                   .replace("{role}", ROLE_LABEL[r.data.role] || r.data.role));
    setEmail(""); setPw(""); setNote(""); setNewRole("user");
    load();
  }

  async function toggle(u) {
    setBusy(true);
    const r = await adminDisable(u.email, !u.disabled);
    setBusy(false);
    if (!r.ok) setErr((r.data && r.data.detail) || t("admin.saveFail"));
    load();
  }

  // THE ROLE OF SOMEBODY WITH NO PASSWORD ROW IS SETTABLE, and that is the point of the feature:
  // every Colt address on this page signs in with the shared password and has no credential row at
  // all. Roles live in their own table for exactly that reason, so this works on every row here.
  async function applyRole(u) {
    const want = pending[u.email];
    if (!want || want === u.role) return;
    setBusy(true); setErr(""); setSaved("");
    const r = await adminSetRole(u.email, want === "user" ? "" : want);
    setBusy(false);
    if (!r.ok) { setErr((r.data && r.data.detail) || t("admin.saveFail")); return; }
    // SAY WHAT CHANGED, not "saved". A confirmation that does not name the address and the role
    // is indistinguishable from a confirmation of the previous click.
    setSaved(t("admin.roleSaved").replace("{email}", r.data.email)
              .replace("{role}", ROLE_LABEL[r.data.role] || r.data.role));
    setPending((p) => { const n = { ...p }; delete n[u.email]; return n; });
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

  // THE KEY IS NEVER TRANSLATED, ONLY THE LABEL. Renaming an enum key at render time is the rule
  // in CLAUDE.md and the reason for it is that a translated key stops matching and the row
  // silently disappears. `admin`, `sales_rep` and the rest are what travels on the wire in both
  // directions; this map only decides what the operator reads.
  // One literal t() call per role on purpose: tools/i18n_catalogue.mjs resolves call sites
  // statically, so a computed key would be invisible to the gate that proves every key exists.
  const ROLE_LABEL = {
    admin: t("admin.roleAdmin"),
    s4biz_power: t("admin.roleS4bizPower"),
    reseller_admin: t("admin.roleResellerAdmin"),
    company_admin: t("admin.roleCompanyAdmin"),
    presales: t("admin.rolePresales"),
    sales_rep: t("admin.roleSalesRep"),
    user: t("admin.roleUser"),
  };
  // DERIVED FROM THE SERVER, never from a list kept here. roles.py is the one home for the policy;
  // a second copy in the frontend drifts the first time a role is added and the drift shows up as
  // a 403 nobody can explain.
  const catalogue = (data && data.roles) || [];
  const grantable = new Set((data && data.grantable) || []);
  const myEmail = ((data && data.me && data.me.email) || "").toLowerCase();

  return (
    <div className="page">
      <h1>{t("admin.h1")}</h1>
      <p className="lede">{t("admin.lede")}</p>

      <div className="admin-tabs" role="tablist">
        <button type="button" role="tab" aria-selected={adminTab === "users"}
                className={"admin-tab" + (adminTab === "users" ? " on" : "")}
                onClick={() => setAdminTab("users")}>{t("admin.tabUsers")}</button>
        <button type="button" role="tab" aria-selected={adminTab === "fleet"}
                className={"admin-tab" + (adminTab === "fleet" ? " on" : "")}
                onClick={() => setAdminTab("fleet")}>{t("admin.tabFleet")}</button>
      </div>

      {adminTab === "fleet" ? <Fleet /> : (<>

      {err ? <div className="err">{err}</div> : null}
      {saved ? <div className="ok">{saved}</div> : null}

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
          <div className="fld fld-role">
            <div className="label">{t("admin.colRole")}</div>
            {/* The same catalogue and the same grantable set as the rows: one policy, one list.
                Before the page has loaded it is empty, so the control falls back to the default
                role rather than rendering an empty picker. */}
            <select className="input" value={newRole} disabled={busy}
                    aria-label={t("admin.colRole")}
                    onChange={(e) => setNewRole(e.target.value)}>
              {(catalogue.length ? catalogue : [{ key: "user" }]).map((r) => (
                <option key={r.key} value={r.key} disabled={!grantable.has(r.key)}>
                  {ROLE_LABEL[r.key] || r.key}
                </option>
              ))}
            </select>
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
              <th>{t("admin.colRole")}</th>
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
                  {/* An address on the committed ADMIN_EMAILS floor is admin whatever the table
                      says, so offering a picker for it would let the operator store a value the
                      server then ignores. It reads, it does not edit. */}
                  {u.role_fixed || u.email.toLowerCase() === myEmail ? (
                    <span className="tag muted">{ROLE_LABEL[u.role] || u.role}</span>
                  ) : (
                    <div className="admin-rolecell">
                      <select className="input admin-role" disabled={busy}
                              value={pending[u.email] || u.role}
                              aria-label={t("admin.colRole")}
                              onChange={(e) => setPending(
                                (p) => ({ ...p, [u.email]: e.target.value }))}>
                        {catalogue.map((r) => (
                          <option key={r.key} value={r.key}
                                  disabled={!grantable.has(r.key) && r.key !== u.role}>
                            {ROLE_LABEL[r.key] || r.key}
                          </option>
                        ))}
                      </select>
                      {/* Enabled only when there is something to commit, so the button's state is
                          itself the answer to "did my choice register?" */}
                      <button type="button" className="btn sm"
                              disabled={busy || !pending[u.email] || pending[u.email] === u.role}
                              onClick={() => applyRole(u)}>{t("admin.apply")}</button>
                    </div>
                  )}
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
              <tr><td colSpan="7" className="muted">{data ? t("admin.none") : t("admin.loading")}</td></tr>
            ) : null}
          </tbody>
        </table>
      </div>
      <p className="hint">{t("admin.removeNote")}</p>
      <p className="hint">{t("admin.roleNote")}</p>

      {/* WHAT A ROLE GRANTS, read from the policy the server enforces. The verbs and their
          descriptions come from roles.py over the API; writing them again here would give one
          fact two homes, and the copy in the frontend would be the one that goes stale. */}
      <button type="button" className="btn ghost sm" aria-expanded={showPerms}
              onClick={() => setShowPerms((v) => !v)}>
        {showPerms ? t("admin.rolesHide") : t("admin.rolesShow")}
      </button>
      {showPerms ? (
        <div className="tablewrap">
          <table className="admin-tbl admin-perms">
            <thead>
              <tr>
                <th>{t("admin.colRole")}</th>
                <th>{t("admin.colPerms")}</th>
              </tr>
            </thead>
            <tbody>
              {catalogue.map((r) => (
                <tr key={r.key}>
                  <td>
                    {ROLE_LABEL[r.key] || r.key}
                    <div className="hint">{r.about}</div>
                  </td>
                  <td>
                    <ul className="perm-list">
                      {(r.perms || []).map((v) => (
                        <li key={v}>
                          <code>{v}</code>
                          <span className="muted"> {(data && data.permissions
                                                     && data.permissions[v]) || ""}</span>
                        </li>
                      ))}
                    </ul>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      </>)}
    </div>
  );
}
