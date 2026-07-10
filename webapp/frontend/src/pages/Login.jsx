import { useEffect, useRef, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { authBegin, authVerify } from "../api.js";

export default function Login() {
  const nav = useNavigate();
  const [stage, setStage] = useState("creds"); // creds | otp
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const dustRef = useRef(null);

  // hero dust behind the card
  useEffect(() => {
    const cv = dustRef.current;
    if (!cv) return;
    const ctx = cv.getContext("2d");
    let W, H, ps = [], alive = true, id;
    const sz = () => { W = cv.width = cv.offsetWidth; H = cv.height = cv.offsetHeight; };
    sz();
    window.addEventListener("resize", sz);
    const sp = () => ({ x: Math.random() * W, y: Math.random() * H, r: Math.random() * 2.2 + 0.4,
      vx: Math.random() * 0.3 - 0.15, vy: -Math.random() * 0.4 - 0.05, a: Math.random() * 0.5 + 0.1,
      c: Math.random() > 0.7 ? "247,200,68" : "0,178,169" });
    for (let i = 0; i < 70; i++) ps.push(sp());
    const dr = () => {
      if (!alive) return;
      ctx.clearRect(0, 0, W, H);
      ps.forEach((p) => {
        p.x += p.vx; p.y += p.vy; p.a -= 0.0014;
        if (p.a <= 0 || p.y < -10) { Object.assign(p, sp()); p.y = H + 5; }
        ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, 7);
        ctx.fillStyle = "rgba(" + p.c + "," + p.a + ")"; ctx.fill();
      });
      id = requestAnimationFrame(dr);
    };
    dr();
    return () => { alive = false; cancelAnimationFrame(id); window.removeEventListener("resize", sz); };
  }, []);

  async function submitCreds(e) {
    e.preventDefault();
    setErr(""); setMsg(""); setBusy(true);
    try {
      const { ok, status, data } = await authBegin(email.trim(), password);
      if (ok && data.state === "otp_sent") {
        setStage("otp");
        setMsg(data.message || "A 6-digit code was emailed to your inbox.");
      } else if (status === 423 || data.state === "locked") {
        setErr(data.message || "Account locked - too many attempts. Try again later.");
      } else {
        setErr(data.message || "Access denied. Check your colt.net email and password.");
      }
    } catch {
      setErr("Could not reach the server. Try again.");
    } finally {
      setBusy(false);
    }
  }

  async function submitOtp(e) {
    e.preventDefault();
    setErr(""); setBusy(true);
    try {
      const { ok, data } = await authVerify(email.trim(), code.trim());
      if (ok && data.ok) {
        nav("/app");
      } else {
        setErr(data.message || "Invalid or expired code.");
      }
    } catch {
      setErr("Could not reach the server. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-shell">
      <canvas id="dust" ref={dustRef}></canvas>
      <div className="auth-card">
        <div className="brand"><span className="chev">❯</span> colt</div>
        <div className="steps">
          <div className={"s " + (stage === "creds" || stage === "otp" ? "on" : "")}></div>
          <div className={"s " + (stage === "otp" ? "on" : "")}></div>
        </div>

        {stage === "creds" ? (
          <form onSubmit={submitCreds}>
            <h2>Sign in</h2>
            <p className="sub2">Zero-trust access - your @colt.net email, the shared password, then a one-time code.</p>
            <div className="label">Colt email</div>
            <input className="input" type="email" autoComplete="username" placeholder="name@colt.net"
              value={email} onChange={(e) => setEmail(e.target.value)} required />
            <div className="label">Password</div>
            <input className="input" type="password" autoComplete="current-password" placeholder="Shared access password"
              value={password} onChange={(e) => setPassword(e.target.value)} required />
            <button className="btn" type="submit" disabled={busy}>
              {busy ? <span className="spinner" /> : "Continue"}
            </button>
          </form>
        ) : (
          <form onSubmit={submitOtp}>
            <h2>Enter the code</h2>
            <p className="sub2">We emailed a 6-digit code to <b>{email}</b>. It expires in 10 minutes.</p>
            <div className="label">6-digit code</div>
            <input className="input" inputMode="numeric" maxLength={6} placeholder="123456"
              value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
              style={{ letterSpacing: "0.4em", fontSize: 20, textAlign: "center" }} autoFocus required />
            <button className="btn" type="submit" disabled={busy}>
              {busy ? <span className="spinner" /> : "Verify & enter"}
            </button>
            <button type="button" className="auth-back" style={{ background: "none", border: 0, cursor: "pointer" }}
              onClick={() => { setStage("creds"); setErr(""); setMsg(""); setCode(""); }}>
              ← Use a different account
            </button>
          </form>
        )}

        {msg && <div className="ok">{msg}</div>}
        {err && <div className="err">{err}</div>}
        <Link className="auth-back" to="/">← Back to the overview</Link>
      </div>
    </div>
  );
}
