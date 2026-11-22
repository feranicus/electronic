import { useEffect, useRef, useState } from "react";
import { delJSON, getJSON, patchJSON, postJSON } from "../api.js";
import { useT } from "../i18n";

/* Pipeline — the channel-sales board.

   PORTED FROM jobhuntwow's Pipeline.jsx, which has been moved by hand every day since September.
   The mechanics that came across unchanged are the ones that were paid for there:

   DRAG A CARD TO MOVE IT. Native HTML5 drag-and-drop, no library — nothing to keep up to date and
   nothing extra in the bundle. The `<select>` stays as the keyboard and touch path, because
   dragging is not reachable without a mouse.

   THE MOVE IS OPTIMISTIC AND REVERSIBLE. The card lands in the new column immediately (a board
   that waits for a round trip feels broken), the PATCH follows, and if the server refuses it goes
   BACK where it was with the reason printed. A UI showing a state the database does not hold is
   the same defect as a log claiming a send the site never confirmed.

   AND THERE IS NO ONE-CLICK "lost" LINK. In jobhuntwow it sat beside the stage links and one
   mis-click put a live application in Rejected. Dragging is deliberate; a link is not.

   WHAT IS NEW HERE IS THE TRACK. Assad's process map is three parallel processes, not one funnel
   — a partner at R6 runs its own customers through H0–H9. So the board shows ONE track at a time
   and the columns come from the server for that track; a stage list in this file would drift from
   the map the first time it changed.

   Every value is coerced to text before it renders: a backend shape change must never white-screen
   the cabinet. */
const txt = (v) => (v === null || v === undefined ? "" : typeof v === "string" ? v : String(v));
const day = (ts) => (ts ? new Date(Number(ts) * 1000).toLocaleDateString() : "");

export default function Pipeline() {
  const [, , t] = useT();
  const [board, setBoard] = useState(null);
  const [track, setTrack] = useState("");
  const [err, setErr] = useState("");
  const [saved, setSaved] = useState("");
  const [busy, setBusy] = useState("");
  const [over, setOver] = useState("");
  const [open, setOpen] = useState(null);       // the card detail, when one is open
  const [company, setCompany] = useState("");
  const dragged = useRef(null);
  const didDrag = useRef(false);

  async function load(nextTrack) {
    setErr("");
    try {
      const q = nextTrack || track;
      const b = await getJSON("/api/pipeline" + (q ? "?track=" + encodeURIComponent(q) : ""));
      setBoard(b);
      setTrack(txt(b.track));
    } catch (e) {
      setErr(e && e.status === 403 ? t("pipe.forbidden") : t("pipe.loadFail"));
    }
  }
  useEffect(() => { load(); }, []);             // eslint-disable-line react-hooks/exhaustive-deps

  const deals = (board && board.deals) || [];
  const stages = (board && board.stages) || [];
  const stageKeys = stages.map((s) => s.key);

  async function move(id, to, from) {
    if (!id || !to || to === from || !stageKeys.includes(to)) return;
    setErr(""); setSaved(""); setBusy(id);
    setBoard((b) => ({ ...b, deals: b.deals.map((d) => (txt(d.deal_id) === id
      ? { ...d, stage: to } : d)) }));
    const r = await patchJSON("/api/pipeline/" + encodeURIComponent(id), { stage: to });
    setBusy("");
    if (!r.ok || txt(r.data && r.data.stage) !== to) {
      // BACK WHERE IT WAS, AND SAY WHY. The server's detail is the reason — a card that jumps
      // back with no explanation teaches the operator the board is flaky.
      setBoard((b) => ({ ...b, deals: b.deals.map((d) => (txt(d.deal_id) === id
        ? { ...d, stage: from } : d)) }));
      setErr(t("pipe.moveFail").replace("{why}", txt((r.data && r.data.detail) || "")));
      return;
    }
    const lab = (stages.find((s) => s.key === to) || {}).label || to;
    setSaved(t("pipe.moved").replace("{deal}", id).replace("{stage}", lab));
    load();
  }

  function onDrop(ev, to) {
    ev.preventDefault();
    setOver("");
    const d = dragged.current || {};
    const id = d.deal_id || txt(ev.dataTransfer && ev.dataTransfer.getData("text/plain"));
    dragged.current = null;
    move(id, to, d.from);
  }

  async function addDeal(ev) {
    ev.preventDefault();
    const name = company.trim();
    if (!name) return;
    setBusy("new"); setErr(""); setSaved("");
    const r = await postJSON("/api/pipeline", { company: name, track });
    setBusy("");
    if (!r.ok) { setErr(txt((r.data && r.data.detail) || t("pipe.saveFail"))); return; }
    setCompany("");
    load();
  }

  async function openCard(id) {
    setErr("");
    try {
      setOpen(await getJSON("/api/pipeline/" + encodeURIComponent(id)));
    } catch (e) {
      setErr(t("pipe.loadFail"));
    }
  }

  async function addNote(id, body) {
    if (!body.trim()) return;
    const r = await postJSON("/api/pipeline/" + encodeURIComponent(id) + "/notes", { body });
    if (!r.ok) { setErr(txt((r.data && r.data.detail) || t("pipe.saveFail"))); return; }
    openCard(id); load();
  }

  async function dropNote(id, noteId) {
    await delJSON("/api/pipeline/" + encodeURIComponent(id) + "/notes/"
                  + encodeURIComponent(noteId));
    openCard(id);
  }

  // DELETE, NOT "LOST". Lost is a STAGE - a real outcome with a reason, and it stays on the
  // board because a partner who went quiet is the thing you most need to see. A test deal is not
  // an outcome; it is noise, and there has to be a way to remove it entirely. The mail filed
  // against it is UNFILED rather than destroyed (the message really was received), which the
  // server does and the confirmation says.
  async function removeDeal(d) {
    if (!window.confirm(t("pipe.confirmDelete").replace("{company}", txt(d.company)))) return;
    setBusy(d.deal_id); setErr(""); setSaved("");
    const r = await delJSON("/api/pipeline/" + encodeURIComponent(d.deal_id));
    setBusy("");
    if (!r.ok) { setErr(txt((r.data && r.data.detail) || t("pipe.saveFail"))); return; }
    setSaved(t("pipe.deleted").replace("{company}", txt(d.company)));
    setOpen(null);
    load();
  }

  async function sweep() {
    setBusy("sweep"); setErr(""); setSaved("");
    const r = await postJSON("/api/pipeline/sweep", {});
    setBusy("");
    if (!r.ok) { setErr(txt((r.data && r.data.detail) || t("pipe.saveFail"))); return; }
    const d = r.data || {};
    // REPORT WHAT IT DID, never "ok". A sync that cannot say how many it read and how many it
    // could not place is a sync nobody can debug.
    setSaved(t("pipe.swept").replace("{read}", txt(d.read)).replace("{filed}", txt(d.filed))
      .replace("{unfiled}", txt(d.unfiled)));
    load();
  }

  const mail = (board && board.mail) || {};

  return (
    <div className="page">
      <h1>{t("pipe.h1")}</h1>
      <p className="lede">{t("pipe.lede")}</p>

      {err ? <div className="err">{err}</div> : null}
      {saved ? <div className="ok">{saved}</div> : null}

      {/* THE TRACK SELECTOR. Three parallel processes from the process map; a card cannot move
          between them by dragging, which is why they are tabs and not more columns. */}
      <div className="admin-tabs" role="tablist">
        {((board && board.tracks) || []).map((tr) => (
          <button type="button" role="tab" key={tr.key} aria-selected={track === tr.key}
                  className={"admin-tab" + (track === tr.key ? " on" : "")}
                  title={tr.about}
                  onClick={() => { setOpen(null); load(tr.key); }}>{tr.label}</button>
        ))}
      </div>

      <form className="card admin-new" onSubmit={addDeal}>
        <div className="assess-row">
          <div className="fld">
            <div className="label">{t("pipe.company")}</div>
            <input className="input" value={company} onChange={(e) => setCompany(e.target.value)}
                   placeholder={t("pipe.companyPlaceholder")} />
          </div>
          <button className="btn" disabled={busy === "new" || !company.trim()}>
            {t("pipe.add")}
          </button>
        </div>
      </form>

      {/* THE READER'S STATE, ON THE SCREEN. A feature guarded by `if configured():` fails silently
          by construction, so when the mailbox side is off the board says so and says what is
          missing rather than looking like a board nobody writes to. */}
      <div className="card pipe-mail">
        <b>{t("pipe.mailH")}</b>{" "}
        {mail.enabled && mail.credentials
          ? <span className="tag ok">{(mail.mailboxes || []).join(", ")}</span>
          : <span className="tag warn">{t("pipe.mailOff")}</span>}
        {mail.note ? <p className="hint">{txt(mail.note)}</p> : null}
        <button type="button" className="btn ghost sm" disabled={busy === "sweep"}
                onClick={sweep}>{t("pipe.sweep")}</button>
      </div>

      <div className="kan">
        {stages.map((s) => {
          const cards = deals.filter((d) => txt(d.stage) === s.key);
          return (
            <div className={"kcol" + (over === s.key ? " kdrop" : "")} key={s.key}
                 onDragOver={(ev) => { ev.preventDefault(); if (over !== s.key) setOver(s.key); }}
                 onDragEnter={(ev) => ev.preventDefault()}
                 onDragLeave={() => setOver((o) => (o === s.key ? "" : o))}
                 onDrop={(ev) => onDrop(ev, s.key)}>
              {/* THE GATE AND THE EXIT ARE THE COLUMN'S DEFINITION, not decoration: a column whose
                  cards sit for a month is answered by "the exit criterion was never met". */}
              <h4 title={t("pipe.gate") + ": " + txt(s.gate) + "\n" + t("pipe.exit") + ": "
                         + txt(s.exit)}>
                <span className="kcode">{txt(s.code)}</span> {txt(s.label)}
                {cards.length ? " (" + cards.length + ")" : ""}
              </h4>
              <p className="kgate">{txt(s.exit)}</p>
              {cards.map((d) => {
                const id = txt(d.deal_id);
                return (
                  <div className={"kcard" + (busy === id ? " ksaving" : "")} key={id} draggable
                       title={t("pipe.dragMe")}
                       onClick={() => { if (!didDrag.current) openCard(id); }}
                       onDragStart={(ev) => {
                         didDrag.current = true;
                         dragged.current = { deal_id: id, from: s.key };
                         try {
                           ev.dataTransfer.setData("text/plain", id);
                           ev.dataTransfer.effectAllowed = "move";
                         } catch { /* older browsers: the ref above still carries it */ }
                       }}
                       onDragEnd={() => {
                         dragged.current = null; setOver("");
                         setTimeout(() => { didDrag.current = false; }, 0);
                       }}>
                    <b>{txt(d.company)}</b>
                    {d.title ? <small>{txt(d.title)}</small> : null}
                    <small className="muted">
                      {txt(d.country)}{d.country && d.updated_ts ? " · " : ""}{day(d.updated_ts)}
                    </small>
                    {/* The keyboard and touch path. Dragging is not reachable without a mouse. */}
                    <select className="input kmove" value={s.key} aria-label={t("pipe.moveTo")}
                            onClick={(e) => e.stopPropagation()}
                            onChange={(e) => move(id, e.target.value, s.key)}>
                      {stages.map((o) => (
                        <option key={o.key} value={o.key}>{txt(o.label)}</option>
                      ))}
                    </select>
                  </div>
                );
              })}
            </div>
          );
        })}
      </div>

      {open && open.deal ? (
        <div className="card pipe-detail">
          <div className="admin-head">
            <h2>{txt(open.deal.company)}</h2>
            <div className="admin-actions">
              <button type="button" className="btn ghost sm"
                      onClick={() => setOpen(null)}>{t("pipe.close")}</button>
              <button type="button" className="btn ghost sm danger"
                      disabled={busy === open.deal.deal_id}
                      onClick={() => removeDeal(open.deal)}>{t("pipe.delete")}</button>
            </div>
          </div>
          <p className="hint">
            {txt(open.deal.deal_id)} · {txt(open.deal.contact)} {txt(open.deal.domain)}
          </p>

          <h3>{t("pipe.notes")}</h3>
          <NoteBox onAdd={(b) => addNote(open.deal.deal_id, b)} t={t} />
          <ul className="pipe-notes">
            {(open.notes || []).map((n) => (
              <li key={n.note_id}>
                <span className={"tag " + (n.kind === "stage" ? "muted" : "ok")}>{txt(n.kind)}</span>
                {" "}{txt(n.body)}
                <small className="muted"> {day(n.ts)} {txt(n.author)}</small>
                <button type="button" className="btn ghost sm"
                        onClick={() => dropNote(open.deal.deal_id, n.note_id)}>
                  {t("pipe.remove")}
                </button>
              </li>
            ))}
          </ul>

          <h3>{t("pipe.mailOn")}</h3>
          <ul className="pipe-notes">
            {(open.mail || []).map((m) => (
              <li key={m.msg_id}>
                <span className="tag muted">{txt(m.kind)}</span> <b>{txt(m.subject)}</b>
                <small className="muted"> {txt(m.sender)} · {day(m.ts)}</small>
                {/* WHY IT WAS FILED HERE. The matcher is a signal, and a signal that cannot show
                    its evidence is indistinguishable from a guess. */}
                {(m.evidence || []).length
                  ? <div className="hint">{(m.evidence || []).join(" · ")}</div> : null}
              </li>
            ))}
            {!(open.mail || []).length ? <li className="muted">{t("pipe.noMail")}</li> : null}
          </ul>
        </div>
      ) : null}

      {(board && (board.unfiled || []).length) ? (
        <div className="card">
          <h3>{t("pipe.unfiledH")}</h3>
          <p className="hint">{t("pipe.unfiledNote")}</p>
          <ul className="pipe-notes">
            {board.unfiled.map((m) => (
              <li key={m.msg_id}>
                <b>{txt(m.subject)}</b>
                <small className="muted"> {txt(m.sender)} · {day(m.ts)}</small>
                <select className="input kmove" defaultValue=""
                        aria-label={t("pipe.fileOn")}
                        onChange={async (e) => {
                          const v = e.target.value;
                          if (!v) return;
                          const r = await postJSON(
                            "/api/pipeline/mail/" + encodeURIComponent(m.msg_id) + "/file",
                            { deal_id: v });
                          if (!r.ok) setErr(txt((r.data && r.data.detail) || t("pipe.saveFail")));
                          load();
                        }}>
                  <option value="">{t("pipe.fileOn")}</option>
                  {deals.map((d) => (
                    <option key={d.deal_id} value={d.deal_id}>{txt(d.company)}</option>
                  ))}
                </select>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

function NoteBox({ onAdd, t }) {
  const [v, setV] = useState("");
  return (
    <div className="assess-row">
      <div className="fld">
        <input className="input" value={v} onChange={(e) => setV(e.target.value)}
               placeholder={t("pipe.notePlaceholder")} />
      </div>
      <button type="button" className="btn sm" disabled={!v.trim()}
              onClick={() => { onAdd(v); setV(""); }}>{t("pipe.addNote")}</button>
    </div>
  );
}
