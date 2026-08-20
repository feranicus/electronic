import { useEffect, useState } from "react";
import { getBrand, setBrand, deleteBrand } from "../api.js";
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

function Sw({ hex, label, ink }) {
  if (!hex) return null;
  return (
    <div className="wl-sw">
      <div className="wl-chip" style={{ background: "#" + hex, color: "#" + (ink || "FFFFFF") }}>
        {ink ? "Aa" : ""}
      </div>
      <div className="wl-swl">{label}</div>
      <code>#{hex}</code>
    </div>
  );
}

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
  // Cache-busts the logo preview after an upload: the URL never changes, so without this the
  // browser shows the PREVIOUS partner's mark and everyone concludes the upload failed.
  const [v, setV] = useState(0);

  async function load() {
    setErr("");
    try {
      const body = await getBrand();          // getJSON-backed: the parsed body
      setData(body);
      if (body && body.brand && body.brand.name) setName(body.brand.name);
    } catch (e) {
      setErr(t("wl.loadFail"));
    }
  }
  useEffect(() => { load(); }, []);            // eslint-disable-line react-hooks/exhaustive-deps

  async function submit(ev) {
    ev.preventDefault();
    setBusy(true); setErr(""); setWarnings([]);
    const r = await setBrand({ template: tpl, logo, name: name.trim(), panel });
    setBusy(false);
    if (!r.ok) { setErr((r.data && r.data.detail) || t("wl.saveFail")); return; }
    setWarnings((r.data && r.data.warnings) || []);
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
            <Sw hex={pal.brandLight} label={t("wl.stopLight")} ink={pal.onBrandLight} />
            <Sw hex={pal.brandMid} label={t("wl.stopMid")} />
            <Sw hex={pal.brandDark} label={t("wl.stopDark")} ink={pal.onBrandDark} />
          </div>
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
          <p className="hint">
            {t("wl.fonts")}: {(b.fonts && b.fonts.heading) || "—"} / {(b.fonts && b.fonts.body) || "—"}
          </p>
        </>
      )}
    </div>
  );
}
