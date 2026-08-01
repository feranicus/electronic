import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { authBegin, authVerify } from "../api.js";
import SiteHeader from "../components/SiteHeader.jsx";
import { useT } from "../i18n";

export default function Login() {
  const [, , t] = useT();
  const nav = useNavigate();
  const [stage, setStage] = useState("creds"); // creds | otp
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function submitCreds(e) {
    e.preventDefault();
    setErr(""); setMsg(""); setBusy(true);
    try {
      const { ok, status, data } = await authBegin(email.trim(), password);
      if (ok && data.state === "otp_sent") {
        setStage("otp");
        setMsg(data.message || "A 6-digit code was sent to your inbox.");
      } else if (status === 423 || data.state === "locked") {
        setErr(data.message || "Account locked — too many attempts. Try again later.");
      } else {
        setErr(data.message || "Access denied. Use an approved partner email and the shared access password.");
      }
    } catch {
      setErr("Could not reach the identity service. Try again.");
    } finally { setBusy(false); }
  }

  async function submitOtp(e) {
    e.preventDefault();
    setErr(""); setBusy(true);
    try {
      const { ok, data } = await authVerify(email.trim(), code.trim());
      if (ok && data.ok) nav("/app");
      else setErr(data.message || "Invalid or expired code.");
    } catch {
      setErr("Could not reach the identity service. Try again.");
    } finally { setBusy(false); }
  }

  return (
    <div className="iam-page">
      <SiteHeader />
      <div className="iam">
      {/* LEFT — brand / IAM panel */}
      <aside className="iam-brand">
        <div className="iam-brand-top">
          <div className="brand"><span className="chev">&#10095;</span> cybergod.ai</div>
          <span className="iam-tag">{t("login.iam")}</span>
        </div>
        <div className="iam-brand-mid">
          <h1>Cyber pre-sales,<br/>self-serve.</h1>
          <p>One name in, a full attack-surface assessment out. The same engine behind
             the Telegram bots — now on the web, for every seller.</p>
          <ul className="iam-steps">
            <li><span>1</span><div><b>{t("login.step1")}</b>{t("login.step1b")}</div></li>
            <li><span>2</span><div><b>{t("login.step2")}</b>{t("login.step2b")}</div></li>
            <li><span>3</span><div><b>{t("login.step3")}</b>{t("login.step3b")}</div></li>
          </ul>
        </div>
        <div className="iam-brand-foot">{t("login.foot")} · &#187; &#187; &#187;</div>
      </aside>

      {/* RIGHT — sign-in card */}
      <main className="iam-form">
        <div className="iam-card">
          <div className="iam-prog">
            <span className={stage==="creds"||stage==="otp"?"on":""}>Sign in</span>
            <i/>
            <span className={stage==="otp"?"on":""}>Verify</span>
          </div>

          {stage === "creds" ? (
            <form onSubmit={submitCreds}>
              <h2>{t("login.portal")}</h2>
              <p className="iam-sub">{t("login.zero")}</p>
              <div className="label">{t("login.email")}</div>
              <input className="input" type="email" autoComplete="username" placeholder="name.surname@yourcompany.com"
                value={email} onChange={(e)=>setEmail(e.target.value)} required autoFocus />
              <div className="label">{t("login.pw")}</div>
              <input className="input" type="password" autoComplete="current-password" placeholder={t("login.pwPh")}
                value={password} onChange={(e)=>setPassword(e.target.value)} required />
              <button className="btn" type="submit" disabled={busy}>
                {busy ? <span className="spinner"/> : t("login.continue")}
              </button>
            </form>
          ) : (
            <form onSubmit={submitOtp}>
              <h2>{t("login.codeH")}</h2>
              <p className="iam-sub">{t("login.codeSub")}<b>{email}</b>. It expires in 10 minutes.</p>
              <div className="label">6-digit code</div>
              <input className="input otp" inputMode="numeric" maxLength={6} placeholder="000000"
                value={code} onChange={(e)=>setCode(e.target.value.replace(/\D/g,""))} autoFocus required />
              <button className="btn" type="submit" disabled={busy}>
                {busy ? <span className="spinner"/> : "Verify & enter"}
              </button>
              <button type="button" className="iam-back" onClick={()=>{setStage("creds");setErr("");setMsg("");setCode("");}}>
                &#8592; Use a different account
              </button>
            </form>
          )}

          {msg && <div className="ok">{msg}</div>}
          {err && <div className="err">{err}</div>}
          <Link className="iam-back" to="/">{t("login.back")}</Link>
        </div>
        <div className="iam-legal">Cybergod LLC · S4Biz Group · authorised use only<br />
          <a href="/impressum">Impressum</a> · <a href="/privacy">Datenschutz / Privacy</a> · <a href="/contact">Kontakt</a></div>
      </main>
      </div>
    </div>
  );
}
