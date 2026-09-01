"""AI Serverless spend: detect a SPIKE, name a suspect, alert Telegram and email.

WHY THIS IS NOT THE DAILY CAP. `llm_meter.DAILY_USD` is a wall: it stops a runaway once the day has
already cost $3. It answers "make it stop". It does NOT answer "something changed", which is the
question the operator actually asked on 2026-09-01 -- the spend was still small in absolute terms
and had jumped hard against every previous day. A fixed threshold set high enough not to cry wolf is
set too high to notice a 20x change at the bottom of the range, and one set low enough to notice it
fires every busy Tuesday. So a spike is a DEVIATION FROM THIS ACCOUNT'S OWN BASELINE.

TWO SOURCES, AND THE SECOND ONE IS THE POINT.

  1. THE METER (llm_meter.sqlite) sees every call THIS CODEBASE makes, per caller and per model.
     It is precise and it is the only thing that can name a suspect.
  2. THE DO BALANCE sees the whole ACCOUNT.

Source 1 alone would have been blind to the incident that caused this file. The two runaway models,
`deepseek-v4-pro-0813` and `glm-5.3-flash`, appear in NO configuration in this repository or in
jobhuntwow, and >96% of the account's tokens were theirs. A watcher built only on our own meter
would have reported a completely normal fortnight while the invoice tripled -- the exact "a check
that cannot see its subject" defect this repository keeps paying for. The balance delta is coarse
(it cannot say WHO) but it is the only signal that covers callers we do not control, including a
DO GenAI agent created in the console, which runs on DigitalOcean's own infrastructure and appears
in no repository and on no droplet.

So: the meter says who, the balance says whether. Report both, and when they disagree say so --
"the account spent $4.10 and our meter accounts for $0.06" is the entire diagnosis of an outsider
on the key, and it is a sentence no single source can produce.

DESIGN DECISIONS THAT ARE NOT ARBITRARY:

  * MEDIAN baseline, never mean. The thing being detected is an outlier, and one prior spike inside
    the baseline window inflates a mean enough to hide the next one. The median of fourteen days is
    unmoved by two bad ones.
  * BOTH a ratio AND an absolute floor. $0.001 -> $0.02 is a twentyfold rise and is noise. Requiring
    only a ratio produces an alert on every quiet day that follows a quieter one, and an alert that
    is benign every time is how the one that matters gets read past -- already recorded in this
    repository for the roster `www` warning and the bot-gate 8/10 line.
  * A MINIMUM BASELINE. With two days of history a median means nothing. Report "insufficient
    baseline" rather than a confident verdict: absence of evidence is never a finding.
  * THE ALERT NAMES WHAT IS NEW. An alert that says "spend is up" costs the reader the same
    investigation from scratch. It carries the per-model and per-caller delta against the baseline,
    so a model that was not being called last week is named in the message itself.
  * A COOLDOWN. A spike lasts hours; the check runs hourly. Without one, the day it matters produces
    twenty identical messages and the operator mutes the channel.

It never raises and it never blocks anything. Enforcement is llm_meter.allow(); this is observation.
"""
import json
import os
import statistics
import sys
import time

# The engine tree is COPYed into every image at /opt/shodan-skill. Same resolution as brand.py.
_SKILL_CANDIDATES = (
    os.environ.get("SHODAN_SKILL", "/opt/shodan-skill"),
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))), "hermes-skills", "shodan-assessment"),
)
for _p in (os.path.join(c, "scripts") for c in _SKILL_CANDIDATES):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

# ------------------------------------------------------------------ tunables (all overridable)
BASELINE_DAYS = int(os.environ.get("SPEND_BASELINE_DAYS", "14"))
MIN_BASELINE_DAYS = int(os.environ.get("SPEND_MIN_BASELINE_DAYS", "4"))
SPIKE_RATIO = float(os.environ.get("SPEND_SPIKE_RATIO", "4.0"))
# The absolute floor. Below this a ratio is arithmetic on noise. One cent is roughly two of our
# largest legitimate calls, so anything under it cannot be a runaway worth waking someone for.
SPIKE_MIN_USD = float(os.environ.get("SPEND_SPIKE_MIN_USD", "0.10"))
# The whole-account balance drop that counts as a spike on its own, regardless of our meter. DO
# auto-recharges in $5 steps, so a day that eats a top-up is the shape being watched for.
ACCOUNT_SPIKE_USD = float(os.environ.get("SPEND_ACCOUNT_SPIKE_USD", "2.00"))
# How much of the account's AI spend our meter must account for before the gap is worth reporting.
UNATTRIBUTED_USD = float(os.environ.get("SPEND_UNATTRIBUTED_USD", "1.00"))
COOLDOWN_S = int(os.environ.get("SPEND_ALERT_COOLDOWN_S", str(6 * 3600)))
EVERY_S = int(os.environ.get("SPEND_WATCH_EVERY_S", "3600"))

# State lives beside the meter on the shared, persistent colt_events volume. A cooldown kept in a
# module global is reset by every deploy, and this container is force-recreated on every ship -- the
# identical defect that made the shield's fourteen-day slow window unreachable until it was moved to
# disk. A window measured in hours cannot live in state measured in minutes.
STATE = os.environ.get("SPEND_WATCH_STATE", "/var/log/colt/spend_watch.json")


def _now():
    return time.time()


def _load_state():
    try:
        with open(STATE, "r", encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _save_state(d):
    try:
        os.makedirs(os.path.dirname(STATE) or ".", exist_ok=True)
        tmp = STATE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(d, fh)
        os.replace(tmp, STATE)
        return True
    except Exception:
        return False


# ------------------------------------------------------------------ the measurement
def _meter():
    try:
        import llm_meter
        return llm_meter
    except Exception:
        return None


def baseline(per_day, today):
    """(median, n_days) over COMPLETED days only.

    Today is excluded deliberately: it is the thing being judged, and an hour into a spike it would
    otherwise be dragging its own baseline up and damping the very signal we want. Days with no
    calls at all are counted as zero rather than skipped -- a quiet week IS the baseline, and
    dropping the zeros would silently raise it and hide a return to spending.
    """
    days = {d.get("day"): float(d.get("usd") or 0.0) for d in (per_day or [])}
    days.pop(today, None)
    if not days:
        return None, 0
    # Fill the calendar so silent days count. Anchored on the newest day we hold, so a gap at the
    # start of the window does not invent history we never had.
    newest = max(days)
    t_end = time.mktime(time.strptime(newest, "%Y-%m-%d"))
    seq = []
    for i in range(BASELINE_DAYS):
        d = time.strftime("%Y-%m-%d", time.gmtime(t_end - i * 86400))
        seq.append(days.get(d, 0.0))
    seq = seq[:max(len(days), MIN_BASELINE_DAYS)]
    return statistics.median(seq), len(days)


def _delta_tables(rep, today):
    """What is NEW today, per model and per caller.

    This is the part that turns an alert into a diagnosis. `report()` gives totals over the window,
    which cannot distinguish "the usual work, more of it" from "something we have never called
    before". So the models and callers active today are compared against the window, and anything
    absent from the window is flagged NEW -- which is precisely the shape of the 2026-09-01
    incident, where two model ids nobody had ever configured appeared from nothing.
    """
    m = _meter()
    if m is None:
        return [], []
    try:
        with m._connect() as c:
            tm = [(r[0], int(r[1]), float(r[2] or 0.0)) for r in c.execute(
                "SELECT model, COUNT(*), SUM(usd) FROM calls WHERE day = ?"
                " GROUP BY model ORDER BY SUM(usd) DESC", (today,))]
            tc = [(r[0], int(r[1]), float(r[2] or 0.0)) for r in c.execute(
                "SELECT caller, COUNT(*), SUM(usd) FROM calls WHERE day = ?"
                " GROUP BY caller ORDER BY SUM(usd) DESC", (today,))]
    except Exception:
        return [], []
    # `rep["per_model"]` CANNOT answer this: its window INCLUDES today, so every model active now
    # appears in it and nothing would ever look new. "New" has to mean it appears on no day before
    # today, which is a different query.
    _ = rep
    prior_m, prior_c = _prior_sets(today)
    models = [{"model": k, "calls": n, "usd": round(u, 4), "new": k not in prior_m}
              for k, n, u in tm]
    callers = [{"caller": k, "calls": n, "usd": round(u, 4), "new": k not in prior_c}
               for k, n, u in tc]
    return models, callers


def _prior_sets(today):
    """Models and callers seen on any day BEFORE today. Empty on a fault, which makes nothing
    look new -- the safe direction: a false 'NEW' accusation in an alert is worse than a quiet one,
    because the operator acts on it."""
    m = _meter()
    if m is None:
        return set(), set()
    try:
        with m._connect() as c:
            pm = {r[0] for r in c.execute("SELECT DISTINCT model FROM calls WHERE day < ?", (today,))}
            pc = {r[0] for r in c.execute("SELECT DISTINCT caller FROM calls WHERE day < ?", (today,))}
        return pm, pc
    except Exception:
        return set(), set()


def account_spend():
    """Whole-account AI spend today, from DigitalOcean. (usd, detail) or (None, why).

    THE ONLY SOURCE THAT COVERS CALLERS WE DO NOT CONTROL. Needs DO_API_TOKEN; without it this
    half is unavailable and says so rather than reporting zero, because "I could not look" and
    "nothing was spent" must never render the same -- that conflation is what let logship report
    success for a week while shipping nothing.
    """
    tok = os.environ.get("DO_API_TOKEN", "").strip()
    if not tok:
        return None, "DO_API_TOKEN is not set in this container - account-wide spend cannot be read"
    import urllib.error
    import urllib.request
    req = urllib.request.Request("https://api.digitalocean.com/v2/customers/my/balance",
                                 headers={"Authorization": "Bearer " + tok})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        return None, "DO balance lookup failed: %s" % (repr(e)[:120],)
    try:
        mtd = float(d.get("month_to_date_usage") or 0.0)
    except Exception:
        return None, "DO balance returned an unexpected shape"
    st = _load_state()
    prev, prev_ts = st.get("mtd_usage"), st.get("mtd_ts")
    st["mtd_usage"], st["mtd_ts"] = mtd, _now()
    _save_state(st)
    if prev is None or prev_ts is None:
        return None, "first reading (month-to-date $%.2f) - a delta needs two" % mtd
    if mtd < float(prev):            # the invoice rolled over into a new month
        return None, "month-to-date reset (new billing month) - baseline restarted"
    hours = max(0.25, (_now() - float(prev_ts)) / 3600.0)
    return mtd - float(prev), "$%.2f in %.1fh (month-to-date $%.2f)" % (
        mtd - float(prev), hours, mtd)


def check():
    """The verdict. Never raises. Returns a dict; `spike` is True when something needs a human."""
    m = _meter()
    out = {"ts": _now(), "spike": False, "reasons": [], "notes": [],
           "today_usd": None, "baseline_usd": None, "baseline_days": 0,
           "models": [], "callers": [], "account_delta": None}
    if m is None:
        out["notes"].append("llm_meter is not importable in this container - our own spend is "
                            "unmeasurable here (this is a wiring fault, not a quiet day)")
    else:
        today = time.strftime("%Y-%m-%d", time.gmtime())
        try:
            rep = m.report(days=BASELINE_DAYS)
        except Exception as e:
            rep = {"error": repr(e)[:120]}
        if not isinstance(rep, dict) or rep.get("error"):
            out["notes"].append("the meter could not be read: %s"
                                % (rep.get("error") if isinstance(rep, dict) else "unknown"))
        else:
            if rep.get("healthy") is False:
                out["notes"].append("THE METER IS UNHEALTHY - our own calls are not being recorded, "
                                    "so a quiet reading here proves nothing")
            cur = rep.get("today_usd")
            base, n = baseline(rep.get("per_day"), today)
            out["today_usd"], out["baseline_usd"], out["baseline_days"] = cur, base, n
            out["models"], out["callers"] = _delta_tables(rep, today)
            if cur is None:
                out["notes"].append("today's total is unreadable")
            elif n < MIN_BASELINE_DAYS:
                out["notes"].append("only %d day(s) of history - too little for a baseline, so no "
                                    "spike verdict is offered yet" % n)
            elif cur >= SPIKE_MIN_USD and (base is None or base <= 0 or cur >= base * SPIKE_RATIO):
                out["spike"] = True
                out["reasons"].append(
                    "our metered spend today is $%.4f against a %d-day median of $%.4f (%s)"
                    % (cur, n, base or 0.0,
                       "no prior spend at all" if not base else "%.1fx" % (cur / base)))
            # A MODEL WE HAVE NEVER CALLED BEFORE IS ALWAYS WORTH ONE MESSAGE. This is the signal
            # that would have caught 2026-09-01 on its first hour rather than from an invoice.
            # Deliberately changing the chain trips it too -- once, then the cooldown holds it. That
            # is the right trade: a single expected message costs nothing, and suppressing it would
            # mean suppressing the unexpected one, which is the whole point.
            new_m = [x["model"] for x in out["models"] if x.get("new")]
            if new_m:
                out["spike"] = True
                out["reasons"].append("model(s) called today that were never called before: %s"
                                      % ", ".join(sorted(new_m)[:6]))

    delta, detail = account_spend()
    out["account_delta"], out["account_detail"] = delta, detail
    if delta is None:
        out["notes"].append(detail)
    elif delta >= ACCOUNT_SPIKE_USD:
        out["spike"] = True
        out["reasons"].append("the DigitalOcean ACCOUNT spent %s since the last check" % detail)

    # THE DISAGREEMENT IS THE DIAGNOSIS. This is the sentence that names an outsider on the key.
    mine = out.get("today_usd")
    if delta is not None and mine is not None and delta - mine >= UNATTRIBUTED_USD:
        out["spike"] = True
        out["reasons"].append(
            "UNATTRIBUTED: the account moved $%.2f while this codebase accounts for $%.4f. The "
            "difference is a caller we do not control - another project on the shared key, or a "
            "GenAI agent created in the DigitalOcean console (which runs on their infrastructure "
            "and appears in no repository and on no droplet)." % (delta, mine))
    return out


def render(v):
    """Plain text. Telegram gets no Markdown: a model id or a caller name can carry an underscore,
    Telegram then rejects the whole message as malformed entities, and the alert that matters most
    is the one that silently never arrives."""
    L = ["AI SPEND ALERT - cybergod.ai" if v.get("spike") else "AI spend - normal",
         time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(v.get("ts") or _now())), ""]
    for r in v.get("reasons") or []:
        L.append("! " + r)
    if v.get("reasons"):
        L.append("")
    t, b = v.get("today_usd"), v.get("baseline_usd")
    L.append("metered today : %s" % ("$%.4f" % t if t is not None else "unknown"))
    L.append("baseline      : %s over %d day(s)"
             % ("$%.4f" % b if b is not None else "n/a", v.get("baseline_days") or 0))
    if v.get("account_detail"):
        L.append("account       : %s" % v["account_detail"])
    mo = [x for x in (v.get("models") or [])][:6]
    if mo:
        L.append("")
        L.append("models today:")
        for x in mo:
            L.append("  %-28s %4d calls  $%.4f%s"
                     % (x["model"][:28], x["calls"], x["usd"], "   <-- NEW" if x.get("new") else ""))
    ca = [x for x in (v.get("callers") or [])][:6]
    if ca:
        L.append("")
        L.append("callers today:")
        for x in ca:
            L.append("  %-28s %4d calls  $%.4f%s"
                     % (x["caller"][:28], x["calls"], x["usd"], "   <-- NEW" if x.get("new") else ""))
    for n in v.get("notes") or []:
        L.append("")
        L.append("note: " + n)
    return "\n".join(L)


def run_once(force=False):
    """Check, and alert if a spike is due. Returns the verdict with `alerted` set."""
    v = check()
    v["alerted"] = False
    if not v.get("spike") and not force:
        return v
    st = _load_state()
    last = float(st.get("last_alert") or 0)
    if not force and _now() - last < COOLDOWN_S:
        v["notes"].append("in cooldown - alerted %.1fh ago, next after %.0fh"
                          % ((_now() - last) / 3600.0, COOLDOWN_S / 3600.0))
        return v
    body = render(v)
    try:
        from . import notify
    except Exception:
        try:
            import notify
        except Exception:
            notify = None

    # `alerted` MUST MEAN DELIVERED. The first version set it True whenever notify merely imported,
    # so a container with no Telegram token and no Gmail credentials reported that it had alerted
    # nobody about a spend spike -- reporting success for work it did not do, which is the exact
    # defect that let logship ship an empty archive for a week while exiting 0. notify.telegram()
    # and notify.email() both return truthy only on real delivery, so ask them.
    ok_tg = ok_mail = False
    if notify is not None:
        try:
            ok_tg = bool(notify.telegram(body))
        except Exception:
            ok_tg = False
        try:
            ok_mail = bool(notify.email("AI spend alert - cybergod.ai", body))
        except Exception:
            ok_mail = False
    v["alerted"] = ok_tg or ok_mail
    v["delivery"] = {"telegram": ok_tg, "email": ok_mail}
    if not v["alerted"]:
        # An alert nobody receives is not an alert. Say so on stdout, which promtail ships to Loki,
        # so a silently muted channel is at least queryable rather than invisible.
        print(json.dumps({"evt": "spend_alert", "result": "undelivered", "spike": v.get("spike"),
                          "reasons": (v.get("reasons") or [])[:3]}), flush=True)

    # The cooldown is stamped even on a failed delivery, deliberately. The alternative is retrying
    # every hour against a channel that is misconfigured, which turns one problem into a second one
    # the moment it starts working again and twenty queued messages arrive at once.
    st["last_alert"] = _now()
    _save_state(st)
    return v


async def scheduler():
    """Hourly. Started from main.py's startup hook beside the other background loops."""
    import asyncio
    while True:
        try:
            await asyncio.sleep(max(300, EVERY_S))
            await asyncio.get_event_loop().run_in_executor(None, run_once)
        except asyncio.CancelledError:
            raise
        except Exception:
            pass


if __name__ == "__main__":
    force = "--send" in sys.argv
    v = run_once(force=force) if force else check()
    print(render(v))
    if "--json" in sys.argv:
        print()
        print(json.dumps(v, indent=2, default=str))
