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

// NEVER RENDER A NUMBER FOR SOMETHING THAT WAS NOT MEASURED.
//
// This is the single most important line on the page and it is three characters of logic. The
// backend sends null for every value it could not measure and an integer for every value it could,
// and the two must not look alike: a 0 in an enforcement column reads as "the defence is running
// and nothing got past it", which is the exact opposite of "we cannot see this project". String(0)
// is still "0", so a MEASURED zero survives intact -- that distinction is the whole point.
function n(v, t) {
  return v === null || v === undefined ? t("fleet.unknown") : String(v);
}

function agoOr(s, t) {
  return s === null || s === undefined ? t("fleet.unknown") : ago(s);
}

// `enforce` and `alerting` are ENUM KEYS from the backend and are never translated as keys -- the
// LABEL is chosen here, at render time. An unrecognised value falls through to the NEUTRAL tone and
// to t("fleet.e.<whatever>"), which prints a raw key that the SSR guard fails the build on. It must
// never fall through to "ok": a wildcard branch that scores an unknown answer as a pass is not a
// check. `empty` and `none` are drawn as BAD, because a sidecar that is beating happily while
// enforcing nothing is the state this panel exists to make impossible to misread as health.
const ETONE = { active: "ok", armed: "warn", empty: "bad", none: "bad", unknown: "" };
const ATONE = { self: "ok", covered: "ok", unknown: "", blind: "bad" };

// `elsewhere` is NEUTRAL, deliberately: the project keeps its own event volume and this container
// does not mount it. Colouring it like SILENT would repeat the exact error this page exists to
// prevent -- reporting where WE looked as a fact about THEM.
const TONE = { live: "ok", observed: "warn", silent: "bad", elsewhere: "" };

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
      {/* THE CAUSE, ON THE PAGE. When the backend cannot compute the status it now returns a
          rendered page with `error` set and NO projects, instead of a 500 with an empty body.
          Three deploy cycles were spent on "Could not read the fleet status." precisely because
          the page could not tell the operator what had actually gone wrong. Not translated:
          this is a raw exception for whoever is debugging, and translating it would hide it. */}
      {d.error ? (
        <div className="err">
          <b>{d.error}</b>
          {(d.error_where || []).map((l, i) => (
            <div key={i} style={{ fontFamily: "monospace", fontSize: "0.85em", opacity: 0.8 }}>{l}</div>
          ))}
        </div>
      ) : null}

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
          <b>{d.elsewhere ?? 0}</b><span>{t("fleet.elsewhereN")}</span>
        </div>
        <div className="fleet-stat">
          {/* `|| {}` because FleetView is rendered with hand-written fixtures by the gate, and a
              fixture that omits one key must fail an ASSERTION, not throw a TypeError that reads
              like a broken page. */}
          <b>{(d.published || {}).cycle ?? "—"}</b><span>{t("fleet.cycle")}</span>
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

      <SocPanel d={d} t={t} />

      {/* The limit belongs ON the page, not in a comment. A reader cannot tell from a number
          whether it came from a log nobody is writing. */}
      <p className="hint">{d.caveat}</p>
      {/* t() takes ONE argument -- it has no interpolation. Passing a second would silently print
          the raw template, so the number is composed here. */}
      <p className="hint">{t("fleet.window")} {d.window_h}h.</p>
    </>
  );
}

// SOC -- IS ANYTHING ACTUALLY BEING ENFORCED, OR ARE WE ONLY WATCHING?
//
// Everything above this point measures LIVENESS. The operator was told, correctly, that liveness is
// nearly all this page had: every row read `enforcing cycle 0`, which means perseus has never
// published a blocklist, which means the five sidecars have been iterating an EMPTY pattern list
// since the day they were installed. The page said `live` throughout and it was telling the truth
// about the wrong question.
//
// THIS PANEL IS DESIGNED FOR THE STATE IT IS IN TODAY: zero enforced, nothing published, several
// values genuinely unknown. It must not look like a healthy dashboard while it says that. So the
// numbers that are zero are drawn as FAULTS, the values nobody measured are drawn as WORDS, and the
// one thing that cannot be measured at all (tarpitting leaves no line in any log) is stated instead
// of being rendered as a confident nought.
function SocPanel({ d, t }) {
  const pub = d.published || {};
  const ev = d.publish_evt || {};
  // NOTHING IN THE BLOCKLIST IS TRUSTED WITHOUT `readable`.
  //
  // This is not belt and braces. The route's own ERROR path -- the one that runs when status()
  // throws -- hands back `{cycle: null, patterns: 0, age_s: null}` and no `readable` flag at all,
  // so a page that read `pub.patterns` directly would print "blocking rules: 0" underneath a banner
  // saying the blocklist could not be read. Two halves of one screen disagreeing, which is exactly
  // how a raw enum once reached a customer slide. An older backend that predates these fields lands
  // in the same place and gets the same honest answer.
  const readable = pub.readable === true;
  const pubCycle = readable ? pub.cycle : null;
  const pubPatterns = readable ? pub.patterns : null;
  const pubAge = readable ? pub.age_s : null;
  // "The blocklist says cycle 0" and "we could not read the blocklist" are different findings, and
  // only the first one is about perseus. Never claim the first without `readable`.
  const neverPublished = readable && !(Number(pub.cycle) > 0);

  return (
    <div className="soc">
      <h3>{t("fleet.socH")}</h3>
      <p className="hint">{t("fleet.socLede")}</p>

      <div className="fleet-sum">
        {/* RED ONLY FOR A MEASURED ZERO. `undefined` means the backend could not compute the fleet
            status at all, and colouring that as a fault would be this panel making a claim about
            perseus out of its own failure to measure -- one column over from the defect the whole
            module exists to prevent. */}
        <div className={"fleet-stat" + (d.enforcing === 0 ? " bad" : "")}>
          <b>{n(d.enforcing, t)}</b><span>{t("fleet.enforcingN")}</span>
        </div>
        <div className={"fleet-stat" + (d.alerting_blind ? " bad" : "")}>
          <b>{n(d.alerting_blind, t)}</b><span>{t("fleet.alertBlindN")}</span>
        </div>
      </div>

      {/* THE BLOCKLIST ITSELF. Three facts, in words, because two of them are routinely unknown and
          a 26px "0" in a stat card is a claim this page cannot support. */}
      <p className="hint">
        {t("fleet.blCycle")} <b>{n(pubCycle, t)}</b>
        {" · "}{t("fleet.blPatterns")} <b>{n(pubPatterns, t)}</b>
        {" · "}{t("fleet.blAge")} <b>{agoOr(pubAge, t)}</b>
      </p>

      {readable ? null : <div className="err">{t("fleet.blUnread")}</div>}
      {neverPublished ? <div className="err">{t("fleet.blNever")}</div> : null}

      {/* HAS THE BRAIN RUN? Four states, and three of them are "we do not know", which is why the
          backend sends an enum rather than a count. A count on its own cannot tell a reader whether
          `0` means the hub never published or that nobody asked Loki. */}
      {ev.lookup === "ok" ? (
        ev.runs ? (
          <p className="hint">
            <b>{n(ev.runs, t)}</b> {t("fleet.pubRuns")}
            {ev.failed ? <> {" · "}<b>{n(ev.failed, t)}</b> {t("fleet.pubFailed")}</> : null}
          </p>
        ) : (
          <div className="err">{t("fleet.pubNone")}</div>
        )
      ) : (
        <p className="hint">
          {ev.lookup === "off" ? t("fleet.pubOff")
            : ev.lookup === "no_answer" ? t("fleet.pubNoAnswer")
              : t("fleet.pubPending")}
        </p>
      )}

      <div className="tablewrap">
        <table className="admin-tbl">
          <thead>
            <tr>
              <th>{t("fleet.project")}</th>
              <th>{t("fleet.colEnforce")}</th>
              <th>{t("fleet.colRules")}</th>
              <th>{t("fleet.colAlerting")}</th>
              <th>{t("fleet.colRefused")}</th>
            </tr>
          </thead>
          <tbody>
            {(d.projects || []).map((p) => (
              <tr key={p.key}>
                <td><b>{p.name}</b></td>
                {/* `|| "unknown"` is not defensive padding: a payload from an older backend, or the
                    route's error path, carries no `enforce` at all, and `"fleet.e." + undefined`
                    prints the raw key on screen. Degrading to the value that MEANS "we do not know"
                    is the honest answer to a field that is not there. */}
                <td>
                  <span className={"pill " + (ETONE[p.enforce] || "")}>
                    {t("fleet.e." + (p.enforce || "unknown"))}
                  </span>
                  <div className="fleet-why">{t("fleet.blCycle")} {n(p.enforce_cycle, t)}</div>
                </td>
                <td>{n(p.enforce_patterns, t)}</td>
                <td>
                  <span className={"pill " + (ATONE[p.alerting] || "")}>
                    {t("fleet.a." + (p.alerting || "unknown"))}
                  </span>
                  <div className="fleet-why">{t("fleet.a." + (p.alerting || "unknown") + "Why")}</div>
                </td>
                <td>{n(p.refused_24h, t)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* NOT DETERMINABLE, SAID OUT LOUD. shield.decide() returns TARPIT and telemetry.py sleeps on
          it; neither writes an event, so no log this page can read holds a tarpit. The flag comes
          from the backend so that adding such an event removes this sentence in one edit. */}
      {d.tarpit_recorded === false ? <p className="hint">{t("fleet.tarpitNote")}</p> : null}
    </div>
  );
}
