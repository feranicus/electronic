import { useEffect, useRef, useState } from "react";
import { assist } from "../api.js";
import { useT } from "../i18n";

export default function Assistant() {
  const [, , t] = useT();
  // Lazy initialiser: the opening line is written ONCE, in the language the cabinet was opened in.
  // Re-translating it later would rewrite a message already sitting in the transcript.
  const [msgs, setMsgs] = useState(() => [
    { role: "bot", content: t("assist.greeting") },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const bodyRef = useRef(null);

  useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
  }, [msgs, busy]);

  async function send() {
    const text = input.trim();
    if (!text || busy) return;
    setMsgs((m) => [...m, { role: "me", content: text }]);
    setInput(""); setBusy(true);
    try {
      const { ok, data } = await assist(text);
      const reply = ok ? (data.reply || "…") : (data.message || t("assist.errServer"));
      setMsgs((m) => [...m, { role: "bot", content: reply }]);
    } catch {
      setMsgs((m) => [...m, { role: "bot", content: t("assist.errNet") }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <h1 className="page-h">{t("assist.h1")}</h1>
      <p className="page-sub">{t("assist.sub")}</p>
      <div className="chat">
        <div className="chat-body" ref={bodyRef}>
          {msgs.map((m, i) => (
            <div key={i} className={"cmsg " + (m.role === "me" ? "me" : "bot")}>{m.content}</div>
          ))}
          {busy && <div className="cmsg bot"><span className="spinner" /></div>}
        </div>
        <div className="chat-input">
          <input className="input" placeholder={t("assist.ph")} value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()} disabled={busy} />
          <button className="btn" onClick={send} disabled={busy || !input.trim()}>
            {busy ? <span className="spinner" /> : t("assist.send")}
          </button>
        </div>
      </div>
    </>
  );
}
