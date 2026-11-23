import { useEffect, useState } from "react";
import { getJSON, postJSON } from "../api.js";
import { useT } from "../i18n";

/* DEAL REGISTRATION — the fourth board.
 *
 * It looks like the other three and it is not one. The process-map tracks follow a PARTNER
 * relationship through stages a human moves a card between. A registration follows ONE DEAL, its
 * state is a VERDICT we issue, and it has a clock on it. So there is no drag-and-drop here: a card
 * moves because somebody with `dealreg.decide` decided, and the move is refused by name when the
 * state machine forbids it.
 *
 * THE SENTENCE THAT MUST NEVER BE EDITED OUT OF THIS SCREEN is the one on a `duplicate` card: the
 * second partner keeps the right to quote, to be supplied and to be priced. It comes from the API
 * (`config().second_partner` and the card's own reason), never from a string typed here, because a
 * UI that paraphrases it can drop it — and a partner who reads "already registered" and concludes
 * they are barred is obeying a restriction we never imposed and may not impose.
 */
export default function DealReg() {
  const [, , t] = useT();
  const [board, setBoard] = useState(null);
  const [err, setErr] = useState("");
  const [saved, setSaved] = useState("");
  const [busy, setBusy] = useState("");
  const [open, setOpen] = useState(null);
  const [f, setF] = useState({ company: "", domain: "", country: "", product: "herkos",
                               description: "", value_eur: "", close_date: "", contact: "",
                               competitor: "" });

  async function load() {
    setErr("");
    try { setBoard(await getJSON("/api/dealreg/board")); }
    catch (e) { setErr(t("dr.loadFail")); }
  }
  useEffect(() => { load(); }, []);                      // eslint-disable-line

  async function submit(e) {
    e.preventDefault();
    setBusy("new"); setErr(""); setSaved("");
    try {
      const r = await postJSON("/api/dealreg", { ...f, value_eur: Number(f.value_eur || 0) });
      setSaved(t("dr.submitted").replace("{id}", r.id));
      setF({ ...f, company: "", domain: "", description: "", value_eur: "", close_date: "" });
      await load();
    } catch (e2) { setErr(String((e2 && e2.message) || t("dr.saveFail"))); }
    finally { setBusy(""); }
  }

  async function decide(id, state) {
    setBusy(id); setErr(""); setSaved("");
    try {
      await postJSON("/api/dealreg/" + encodeURIComponent(id) + "/decide", { state, reason: "" });
      await load();
    } catch (e) {
      /* The 409 body carries the state machine's own sentence ("X cannot go from a to b
         (allowed: ...)"). Showing it beats inventing a friendlier one that says less. */
      setErr(String((e && e.message) || t("dr.saveFail")));
    } finally { setBusy(""); }
  }

  const cfg = (board && board.config) || {};
  const cols = (board && board.columns) || {};
  const states = (board && board.states) || [];

  return (
    <div>
      {err ? <div className="err">{err}</div> : null}
      {saved ? <div className="ok">{saved}</div> : null}

      {/* THE PROGRAMME TERMS, READ FROM THE API. Never retyped into this file: the form, the
          partner pack and the deck all read config(), so a window that changes cannot be current
          in one place and stale in another. */}
      <div className="card pipe-mail">
        <b>{t("dr.termsH")}</b>{" "}
        <span className="tag ok">
          {t("dr.terms")
            .replace("{days}", String(cfg.protection_days || ""))
            .replace("{clock}", t("dr.clock." + (cfg.clock_starts || "approval")))
            .replace("{sla}", String(cfg.sla_days || ""))}
        </span>
        <p className="hint">{t("dr.scopeNote")}</p>
      </div>

      <form className="card admin-new" onSubmit={submit}>
        <div className="assess-row">
          <div className="fld">
            <div className="label">{t("dr.company")}</div>
            <input className="input" value={f.company} required
                   onChange={(e) => setF({ ...f, company: e.target.value })} />
          </div>
          <div className="fld">
            {/* THE MATCH KEY, and the form says so. A partner who knows the domain is what
                separates their deal from somebody else's types it carefully. */}
            <div className="label">{t("dr.domain")}</div>
            <input className="input" value={f.domain} required placeholder="kunde.de"
                   onChange={(e) => setF({ ...f, domain: e.target.value })} />
          </div>
          <div className="fld">
            <div className="label">{t("dr.country")}</div>
            <input className="input" value={f.country} maxLength={2} placeholder="DE"
                   onChange={(e) => setF({ ...f, country: e.target.value })} />
          </div>
          <div className="fld">
            <div className="label">{t("dr.product")}</div>
            <select className="input" value={f.product}
                    onChange={(e) => setF({ ...f, product: e.target.value })}>
              <option value="herkos">Herkos</option>
              <option value="perseus">Perseus</option>
              <option value="both">{t("dr.both")}</option>
            </select>
          </div>
        </div>
        <div className="assess-row">
          <div className="fld">
            <div className="label">{t("dr.value")}</div>
            <input className="input" type="number" min="0" value={f.value_eur}
                   onChange={(e) => setF({ ...f, value_eur: e.target.value })} />
          </div>
          <div className="fld">
            <div className="label">{t("dr.close")}</div>
            <input className="input" type="date" value={f.close_date}
                   onChange={(e) => setF({ ...f, close_date: e.target.value })} />
          </div>
          <div className="fld">
            <div className="label">{t("dr.competitor")}</div>
            <input className="input" value={f.competitor}
                   onChange={(e) => setF({ ...f, competitor: e.target.value })} />
          </div>
        </div>
        <div className="fld">
          {/* WHAT MAKES IT DISTINGUISHABLE. This is not decoration: a second registration at the
              same customer is RETURNED rather than refused when it is described well enough to
              tell the two projects apart, so the hint says what the description is for. */}
          <div className="label">{t("dr.description")}</div>
          <textarea className="input" rows={3} value={f.description}
                    placeholder={t("dr.descriptionPlaceholder")}
                    onChange={(e) => setF({ ...f, description: e.target.value })} />
        </div>
        <button className="btn" disabled={busy === "new" || !f.company.trim() || !f.domain.trim()}>
          {t("dr.submit")}
        </button>
      </form>

      <div className="pipe-board">
        {states.map((s) => (
          <div className="pipe-col" key={s.key}>
            <div className="pipe-colh">
              <b>{t("dr.state." + s.key)}</b>
              <span className="tag">{(cols[s.key] || []).length}</span>
            </div>
            {(cols[s.key] || []).map((r) => (
              <div className="pipe-card" key={r.id} onClick={() => setOpen(open === r.id ? null : r.id)}>
                <div className="pipe-cardh">
                  <span className="tag">{r.id}</span> <b>{r.company}</b>
                </div>
                <div className="hint">{r.domain} · {r.country} · {r.product}</div>
                {board.sees_all ? <div className="hint">{r.owner}</div> : null}
                {r.reason ? <p className="hint">{r.reason}</p> : null}
                {open === r.id && board.can_decide ? (
                  <div className="pipe-actions">
                    {["review", "approved", "returned", "rejected"].map((st) => (
                      <button type="button" className="btn ghost sm" key={st}
                              disabled={busy === r.id}
                              onClick={(ev) => { ev.stopPropagation(); decide(r.id, st); }}>
                        {t("dr.state." + st)}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
