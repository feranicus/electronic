import { useEffect, useRef, useState } from "react";
import { assist } from "../api.js";

export default function Assistant() {
  const [msgs, setMsgs] = useState([
    { role: "bot", content: "Hi, I'm Cassandra - your pre-sales sidekick. Ask me for company research, a MEDDPICC breakdown, or outreach copy." },
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
      const reply = ok ? (data.reply || "…") : (data.message || "Something went wrong. Try again.");
      setMsgs((m) => [...m, { role: "bot", content: reply }]);
    } catch {
      setMsgs((m) => [...m, { role: "bot", content: "Could not reach the server. Try again." }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <h1 className="page-h">Assistant</h1>
      <p className="page-sub">Cassandra - research, MEDDPICC qualification, and outreach drafting for your accounts.</p>
      <div className="chat">
        <div className="chat-body" ref={bodyRef}>
          {msgs.map((m, i) => (
            <div key={i} className={"cmsg " + (m.role === "me" ? "me" : "bot")}>{m.content}</div>
          ))}
          {busy && <div className="cmsg bot"><span className="spinner" /></div>}
        </div>
        <div className="chat-input">
          <input className="input" placeholder="Ask Cassandra…" value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()} disabled={busy} />
          <button className="btn" onClick={send} disabled={busy || !input.trim()}>
            {busy ? <span className="spinner" /> : "Send"}
          </button>
        </div>
      </div>
    </>
  );
}
