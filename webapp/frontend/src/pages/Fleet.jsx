import { useEffect, useState } from "react";
import { adminFleet } from "../api.js";
import { useT } from "../i18n";

// FLEET — is the security sidecar connected to every project, and is anything watching them?
//
// Built because the operator asked why he receives nothing on Telegram from jev.best, jobhuntwow or
// polara. The honest answer is on this page: perseus_client.py was copied into those projects and
// imported by nothing, and it is an enforcement client with no telemetry anyway, so no message
// could ever have reached him.
//
// THE THREE STATES ARE DELIBERATELY NOT COLLAPSED INTO "OK / NOT OK":
//   LIVE      logging, and the sidecar is beating          -> protected and observed
//   OBSERVED  logging, no sidecar heartbeat                -> visible, and UNGUARDED
//   SILENT    no log line at all                           -> WE ARE BLIND, not "it is quiet"
// A dashboard that shows "0 attacks" for a project shipping no logs is the same defect as a backup
// that reports success while copying nothing. SILENT is drawn as the loudest state on the page.

function ago(s) {
  if (s === null || s === undefined) return "—";
  if (s < 90) return `${Math.round(s)}s`;
  if (s < 5400) return `${Math.round(s / 60)}m`;
  return `${(s / 3600).toFixed(1)}h`;
}

function when(v) {
  if (!v) return "—";
  try { return new Date(v * 1000).toISOString().slice(0, 16).replace("T", " "); } catch { return "—"; }
}

const TONE = { live: "ok", observed: "warn", silent: "bad" };

// THE VIEW IS SEPARATE FROM THE FETCH so it can be proven. SSR does not run useEffect, so a test
// that renders the default export only ever sees the loading state -- it would pass while the table
// was broken. FleetView takes the data as a prop and is rendered with a real fixture by the gate.
export function FleetView({ d, t, onRefresh }) {
  const blind = d.projects.filter((p) => p.state === "silent");
  const unguarded = d.projects.filter((p) => p.state === "observed");
  return (
    <div className="fleet">
      <div className="admin-head">
        <h2>{t("fleet.h")}</h2>
        <button type="button" className="btn ghost sm" onClick={onRefresh}>{t("fleet.refresh")}</button>
      </div>
      <FleetBody d={d} t={t} blind={blind} unguarded={unguarded} />
    </div>
  );
}

export default function Fleet() {
  const [, , t] = useT();
  const [d, setD] = useState(null);
  const [err, setErr] = useState("");

  async function load() {
    setErr("");
    try {
      setD(await adminFleet());               // getJSON-backed: the parsed body, not { ok, data }
    } catch (e) {
      setErr(e && e.status === 403 ? t("admin.forbidden") : t("fleet.loadFail"));
    }
  }
  useEffect(() => {
    load();
    const h = setInterval(load, 30000);       // the heartbeat is 60s; polling faster tells nothing
    return () => clearInterval(h);
  }, []);                                     // eslint-disable-line react-hooks/exhaustive-deps

  if (err) return <div className="err">{err}</div>;
  if (!d) return <p className="hint">{t("fleet.loading")}</p>;
  return <FleetView d={d} t={t} onRefresh={load} />;
}

function FleetBody({ d, t, blind, unguarded }) {
  return (
    <>
      <div className="fleet-sum">
        <div className="fleet-stat">
          <b>{d.guarded}</b><span>{t("fleet.guarded")}</span>
        </div>
        <div className={"fleet-stat" + (blind.length ? " bad" : "")}>
          <b>{blind.length}</b><span>{t("fleet.blindN")}</span>
        </div>
        <div className={"fleet-stat" + (unguarded.length ? " warn" : "")}>
          <b>{unguarded.length}</b><span>{t("fleet.unguardedN")}</span>
        </div>
        <div className="fleet-stat">
          <b>{d.published.cycle ?? "—"}</b><span>{t("fleet.cycle")}</span>
        </div>
      </div>

      {blind.length ? (
        <div className="err">
          {t("fleet.blindWarn")} <b>{blind.map((p) => p.name).join(", ")}</b>
        </div>
      ) : null}

      <div className="tablewrap">
        <table className="admin-tbl">
          <thead>
            <tr>
              <th>{t("fleet.project")}</th>
              <th>{t("fleet.state")}</th>
              <th>{t("fleet.sidecar")}</th>
              <th>{t("fleet.req")}</th>
              <th>{t("fleet.att")}</th>
              <th>{t("fleet.vis")}</th>
              <th>{t("fleet.alerts")}</th>
              <th>{t("fleet.lastSeen")}</th>
            </tr>
          </thead>
          <tbody>
            {d.projects.map((p) => (
              <tr key={p.key}>
                <td>
                  <b>{p.name}</b>
                  <div className="fleet-why">{p.why}</div>
                </td>
                <td><span className={"pill " + (TONE[p.state] || "")}>{t("fleet.s." + p.state)}</span></td>
                <td>
                  <span className={"pill " + (p.sidecar === "active" ? "ok" : "warn")}>
                    {t("fleet.sc." + p.sidecar.replace(" ", "_"))}
                  </span>
                  {p.sidecar !== "not installed" ? (
                    <div className="fleet-why">{t("fleet.beat")} {ago(p.sidecar_age_s)}</div>
                  ) : null}
                </td>
                <td>{p.requests_24h}</td>
                <td className={p.attacks_24h ? "bad" : ""}>{p.attacks_24h}</td>
                <td>{p.visitors_24h}</td>
                <td>{p.alerts_24h}</td>
                <td>{when(p.last_seen)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* The limit belongs ON the page, not in a comment. A reader cannot tell from a number
          whether it came from a log nobody is writing. */}
      <p className="hint">{d.caveat}</p>
      {/* t() takes ONE argument -- it has no interpolation. Passing a second would silently print
          the raw template, so the number is composed here. */}
      <p className="hint">{t("fleet.window")} {d.window_h}h.</p>
    </>
  );
}
