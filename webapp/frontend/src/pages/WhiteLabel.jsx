import { useEffect, useState } from "react";
import { getBrand, setBrand, deleteBrand, brandJob } from "../api.js";
import { useT } from "../i18n";

// WHITE LABEL — a partner uploads their own PowerPoint and every artifact they generate afterwards
// carries their design.
//
// WHAT THIS PAGE DELIBERATELY SHOWS: not just the result, but HOW it was decided and what we could
// not tell. The colours are read out of the file (exact), and four models then judge which accent
// is the brand and which image is the logo. A partner who disagrees can see the reasoning and the
// per-model votes rather than being told "the computer picked red".
//
// The palette swatches are rendered from the RETURNED theme, not from anything typed here, so what
// is on screen is what the deck builders will use.

function Sw({ hex, label, ink, why }) {
  if (!hex) return null;
  return (
    <div className="wl-sw">
      <div className="wl-chip" style={{ background: "#" + hex, color: "#" + (ink || "FFFFFF") }}>
        {ink ? "Aa" : ""}
      </div>
      <div className="wl-swl">{label}</div>
      <code>#{hex}</code>
      {/* PROVENANCE, next to the swatch. "Colours read from your template" is a claim, and the
          partner can only check it if we say WHICH colour came from where — their deck, their own
          dark surface, derived, or typed by them. */}
      {why ? <div className="wl-why">{why}</div> : null}
    </div>
  );
}

const HEX = /^[0-9A-Fa-f]{6}$/;

export default function WhiteLabel() {
  const [, , t] = useT();
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [name, setName] = useState("");
  const [tpl, setTpl] = useState(null);
  const [logo, setLogo] = useState(null);
  const [panel, setPanel] = useState(true);
  const [warnings, setWarnings] = useState([]);
  const [log, setLog] = useState([]);
  const [pct, setPct] = useState(0);
  // Cache-busts the logo preview after an upload: the URL never changes, so without this the
  // browser shows the PREVIOUS partner's mark and everyone concludes the upload failed.
  const [v, setV] = useState(0);
  // The three stops as the partner may edit them, and a nonce that reloads the preview <img>.
  // Held separately from `data` so typing does not mutate the saved brand: nothing is committed
  // until Apply, which is the whole point of having a preview at all.
  const [edit, setEdit] = useState({ brandLight: "", brandMid: "", brandDark: "" });
  const [pv, setPv] = useState(0);

  async function load() {
    setErr("");
    try {
      const body = await getBrand();          // getJSON-backed: the parsed body
      setData(body);
      if (body && body.brand && body.brand.name) setName(body.brand.name);
      const p = (body && body.brand && body.brand.palette) || null;
      if (p) {
        setEdit({ brandLight: p.brandLight || "", brandMid: p.brandMid || "",
                  brandDark: p.brandDark || "" });
        setPv((n) => n + 1);
      }
    } catch (e) {
      setErr(t("wl.loadFail"));
    }
  }
  useEffect(() => { load(); }, []);            // eslint-disable-line react-hooks/exhaustive-deps

  // WHY THERE IS A LOG AND A BAR HERE AT ALL.
  // With the panel on, four models at a 45s timeout is up to a minute even in parallel, and a
  // spinner that says nothing for a minute is indistinguishable from a hang — which is exactly
  // what happened the first time this page was used. The upload now returns a JOB and this polls
  // it, so every phase is visible: which model answered, which one is still out, and what was
  // decided. The same reasoning as the assessment progress bar.
  // ONLY SEND WHAT THE PARTNER ACTUALLY CHANGED, and only if it is a colour.
  //
  // Sending the three stops unconditionally would pin them on every save, so uploading a NEW
  // template would silently keep the previous template's palette — the overrides would beat the
  // file they were meant to correct. A stop is therefore an override only when it differs from
  // what is on screen for the saved brand.
  function pinned() {
    const p = (data && data.brand && data.brand.palette) || {};
    const out = {};
    for (const k of ["brandLight", "brandMid", "brandDark"]) {
      const v = String(edit[k] || "").trim().replace(/^#/, "");
      if (HEX.test(v) && v.toUpperCase() !== String(p[k] || "").toUpperCase()) out[k] = v;
    }
    // A new template is a fresh reading and the old stops must not survive it.
    return tpl ? {} : out;
  }

  const previewUrl = (slide) => {
    const p = pinned();
    const q = Object.keys(p).map((k) =>
      k.replace(/([A-Z])/g, (m) => "_" + m.toLowerCase()) + "=" + encodeURIComponent(p[k]));
    q.push("slide=" + slide, "v=" + pv);
    return "/api/brand/preview?" + q.join("&");
  };

  async function submit(ev) {
    ev.preventDefault();
    setBusy(true); setErr(""); setWarnings([]); setLog([]); setPct(0);
    let r;
    try {
      r = await setBrand({ template: tpl, logo, name: name.trim(), panel, ...pinned() });
    } catch (e) {
      // A REJECTED FETCH IS THE CASE THAT USED TO HANG FOR EVER. Without this the button sat on
      // "Reading your template…" with no way to say that the request never left the machine.
      setBusy(false);
      setErr(t("wl.netFail") + " " + String((e && e.message) || e));
      return;
    }
    if (!r.ok || !r.data || !r.data.job) {
      setBusy(false);
      setErr((r.data && r.data.detail) || t("wl.saveFail"));
      return;
    }
    poll(r.data.job, 0);
  }

  async function poll(job, since) {
    let s;
    try {
      s = await brandJob(job, since);          // getJSON-backed: the parsed body
    } catch (e) {
      setBusy(false);
      setErr(t("wl.netFail") + " " + String((e && e.message) || e));
      return;
    }
    if (s.lines && s.lines.length) setLog((L) => L.concat(s.lines));
    setPct(s.pct || 0);
    if (!s.done) { setTimeout(() => poll(job, s.total || 0), 900); return; }
    setBusy(false);
    if (s.error) { setErr(s.error); return; }
    setWarnings(s.warnings || []);
    setTpl(null); setLogo(null);
    setV((n) => n + 1);
    load();
  }

  async function remove() {
    if (!window.confirm(t("wl.confirmRemove"))) return;
    setBusy(true);
    await deleteBrand();
    setBusy(false);
    setName(""); setWarnings([]);
    load();
  }

  const b = (data && data.brand) || null;
  const pal = (b && b.palette) || {};
  const why = (b && b.palette_why) || {};
  const maxKb = (data && data.max_logo_kb) || 150;

  return (
    <div className="page">
      <h1>{t("wl.h1")}</h1>
      <p className="lede">{t("wl.lede")}</p>

      {err ? <div className="err">{err}</div> : null}

      <form className="card wl-form" onSubmit={submit}>
        <div className="assess-row">
          <div className="fld">
            <div className="label">{t("wl.template")}</div>
            <input className="input" type="file" accept=".pptx,.potx"
                   onChange={(e) => setTpl(e.target.files[0] || null)} />
            <div className="hint">{t("wl.uploadHint")}</div>
          </div>
          <div className="fld">
            <div className="label">{t("wl.logo")}</div>
            <input className="input" type="file" accept="image/png,image/jpeg,image/gif,image/webp"
                   onChange={(e) => setLogo(e.target.files[0] || null)} />
            <div className="hint">{t("wl.logoHint").replace("{n}", String(maxKb))}</div>
          </div>
          <div className="fld">
            <div className="label">{t("wl.name")}</div>
            <input className="input" value={name} onChange={(e) => setName(e.target.value)}
                   placeholder={t("wl.namePlaceholder")} />
          </div>
          <button className="btn" disabled={busy || (!tpl && !b)}>
            {busy ? t("wl.saving") : t("wl.save")}
          </button>
        </div>
        <label className="wl-panel">
          <input type="checkbox" checked={!panel} onChange={(e) => setPanel(!e.target.checked)} />
          <span>{t("wl.panelOff")}</span>
        </label>
      </form>

      {(busy || log.length) ? (
        <div className="card wl-prog">
          <div className="wl-bar"><span style={{ width: pct + "%" }} /></div>
          <div className="wl-pct">{pct}%</div>
          {/* Newest LAST and the box scrolls: a log that reorders itself is harder to read than
              one that grows, and the line you are waiting for is the one at the bottom. */}
          <pre className="wl-log">
            {log.map((l, i) => (l.t.toFixed(1) + "s  " + l.msg)).join("\n") || t("wl.starting")}
          </pre>
        </div>
      ) : null}

      {warnings.length ? (
        <div className="card wl-warn">
          <div className="wl-h">{t("wl.warnings")}</div>
          <ul>{warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>
        </div>
      ) : null}

      {!b ? (
        <p className="hint">{t("wl.none")}</p>
      ) : (
        <>
          <div className="wl-live">
            <span className="tag ok">{t("wl.active")}</span>
            {b.has_logo ? (
              <img className="wl-logo" src={"/api/brand/logo?v=" + v} alt={b.name || ""} />
            ) : null}
            <strong>{b.name}</strong>
            <button type="button" className="btn ghost sm" onClick={remove} disabled={busy}>
              {t("wl.remove")}
            </button>
          </div>

          <h2>{t("wl.palette")}</h2>
          <div className="wl-swatches">
            <Sw hex={pal.brandLight} label={t("wl.stopLight")} ink={pal.onBrandLight}
                why={why.brandLight} />
            <Sw hex={pal.brandMid} label={t("wl.stopMid")} ink={pal.onBrandMid}
                why={why.brandMid} />
            <Sw hex={pal.brandDark} label={t("wl.stopDark")} ink={pal.onBrandDark}
                why={why.brandDark} />
          </div>

          <div className="card wl-tune">
            <div className="wl-h">{t("wl.tune")}</div>
            <div className="assess-row">
              {[["brandLight", t("wl.stopLight")], ["brandMid", t("wl.stopMid")],
                ["brandDark", t("wl.stopDark")]].map(([k, lbl]) => (
                <div className="fld" key={k}>
                  <div className="label">{lbl}</div>
                  <input className="input mono" value={edit[k]} maxLength={7}
                         onChange={(e) => setEdit({ ...edit, [k]: e.target.value })} />
                </div>
              ))}
              <button type="button" className="btn ghost" disabled={busy}
                      onClick={() => setPv((n) => n + 1)}>{t("wl.refresh")}</button>
            </div>
            <div className="hint">{t("wl.tuneHint")}</div>
          </div>

          <h2>{t("wl.previewH")}</h2>
          {/* AN <img> ON A GET, not a fetch into a blob. The endpoint is session-scoped and returns
              SVG, so the browser's own credentialed request is the simplest correct thing; `v`
              changes on every refresh because the URL is otherwise identical and the previous
              slide would be served from cache, which reads exactly like the button doing nothing. */}
          {/* THE COVER AND A CONTENT SLIDE. Measured on a real branded deck, the cover carries 5
              branded colour uses and slide 3 carries 21 — the large dark fill only exists on the
              content layouts, so showing the cover alone would be a mostly-white page that does not
              answer what a partner is actually asking. */}
          <img className="wl-preview" src={previewUrl(1)} alt={t("wl.previewH")} />
          <img className="wl-preview" src={previewUrl(3)} alt={t("wl.previewH")} />
          <p className="hint">{t("wl.previewHint")}</p>

          <p className="hint">{t("wl.severityNote")}</p>
          <p className="hint">{t("wl.poweredNote")}</p>

          <h2>{t("wl.decided")}</h2>
          <p>{b.decided_by}{b.why ? " " + b.why : ""}</p>
          {(b.votes || []).length ? (
            <div className="tablewrap">
              <table className="admin-tbl">
                <thead>
                  <tr>
                    <th>{t("wl.colModel")}</th>
                    <th>{t("wl.colVote")}</th>
                  </tr>
                </thead>
                <tbody>
                  {(b.votes || []).map((vo, i) => (
                    <tr key={i}>
                      <td className="mono">{vo.model}</td>
                      <td>{vo.ok ? <code>#{vo.brand}</code>
                        : <span className="tag muted">{vo.err || t("wl.voteNone")}</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
          {/* NULL MEANS "WE READ NOTHING", and it must not be printed as if it were a finding.
              This line used to render "Georgia / Calibri" under the heading "Colours read from your
              template" for a file whose fonts are simply Microsoft's defaults — a stock theme
              reported as the partner's typography. */}
          <p className="hint">
            {(b.fonts && (b.fonts.heading || b.fonts.body))
              ? t("wl.fonts") + ": " + [(b.fonts.heading), (b.fonts.body)].filter(Boolean).join(" / ")
              : t("wl.fontsKept")}
          </p>
        </>
      )}
    </div>
  );
}
