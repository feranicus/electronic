"""shield_console.py — "we are under attack", on Telegram, with buttons.

THE OPERATOR'S REQUIREMENT (10 Aug 2026): see clearly when an attack is happening, have the four
models report what they are doing, and be ASKED before anything stronger happens — with a menu of
escalations to approve.

THE THREE TIERS, and the split is deliberate:

  AUTO — happens immediately, no question asked, because it is reversible, time-boxed and cheap:
         tarpit, a 15-minute HTTP block, the alert itself. Waiting for a human to approve a
         15-minute 404 would mean the scan finishes before the phone unlocks.

  ASK  — everything with a longer reach or a cost: a 24-hour hold, widening to the /24, reporting
         the address to a third party, strict mode across the whole site, a permanent path rule.
         These are one tap on Telegram, and they EXPIRE unanswered (default 2h) rather than
         sitting as a live authorisation nobody remembers granting.

  NEVER — scanning the attacker back, connecting to their host, any form of "hack-back". It is a
         criminal offence in every jurisdiction this platform operates in (DE StGB s.202a/303b,
         EU Directive 2013/40, US CFAA s.1030, Canada Criminal Code s.342.1), the attacker's
         address is usually a compromised third party rather than the attacker, and one such
         packet would end the "not one packet is sent to the company being assessed" promise the
         whole product rests on. There is no button for it and there will not be.

HOW A BUTTON REACHES THE APP. colt-web writes the pending decision to the shared `colt_events`
volume and sends the keyboard; colt-assessbot already long-polls Telegram, so IT owns the callback
and writes the answer back to the same volume; colt-web applies it on its next pass. Two containers,
one volume they both already mount, no new port and no second Telegram consumer -- two processes
calling getUpdates would steal each other's messages.
"""
import json
import os
import time

STATE_DIR = os.environ.get("SHIELD_STATE_DIR", "/var/log/colt")
PENDING = os.path.join(STATE_DIR, "shield_pending.json")
DECISIONS = os.path.join(STATE_DIR, "shield_decisions.json")
ASK_TTL_S = int(os.environ.get("SHIELD_ASK_TTL_S", 7200))     # an unanswered ask expires
ANNOUNCE_COOLDOWN_S = int(os.environ.get("SHIELD_ANNOUNCE_COOLDOWN_S", 3600))

# THE MENU. `auto` is what already happened; everything else needs a tap. Keep the labels short --
# Telegram truncates inline buttons on a phone.
ACTIONS = {
    "hold24":  {"label": "Hold 24h",      "what": "extend the HTTP block on this address to 24 hours"},
    "net":     {"label": "Block /24 1h",  "what": "block the whole /24 for one hour (same evidence, wider net)"},
    "abuse":   {"label": "Report abuse",  "what": "submit the address to AbuseIPDB (community blocklist)"},
    "strict":  {"label": "Strict 1h",     "what": "tarpit every unauthenticated request off the known routes for one hour"},
    "deny":    {"label": "Ban this path", "what": "add the requested path to the permanent probe list"},
    "release": {"label": "False alarm",   "what": "release the address and allow it for 24 hours"},
}

_last_announced = {}


def _read(path, default):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default


def _write(path, obj):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, indent=2)
        os.replace(tmp, path)
        return True
    except Exception:
        return False


def _keyboard(incident_id):
    """Telegram inline keyboard, two per row. callback_data is capped at 64 bytes by the API."""
    row, rows = [], []
    for key, a in ACTIONS.items():
        row.append({"text": a["label"], "callback_data": "sh:%s:%s" % (incident_id, key)})
        if len(row) == 2:
            rows.append(row); row = []
    if row:
        rows.append(row)
    return {"inline_keyboard": rows}


def announce(ip, evidence, verdicts=None, already_done="tarpitted, then blocked for 15 minutes"):
    """Tell the operator, once per address per cooldown, and offer the ladder. Never raises."""
    try:
        now = time.time()
        if now - _last_announced.get(ip, 0) < ANNOUNCE_COOLDOWN_S:
            return None
        _last_announced[ip] = now

        incident_id = "%s-%d" % (str(ip).replace(":", "_").replace(".", "-"), int(now))
        pend = _read(PENDING, {})
        pend = {k: v for k, v in pend.items() if now - v.get("ts", 0) < ASK_TTL_S}   # expire old
        pend[incident_id] = {"ip": ip, "ts": now, "evidence": evidence,
                             "path": evidence.get("last_path", "")}
        _write(PENDING, pend)

        lines = ["\U0001f6e1 UNDER ATTACK — cybergod.ai",
                 "",
                 "IP      : %s%s" % (ip, " (%s)" % evidence.get("country") if evidence.get("country") else ""),
                 "Signals : %s" % ", ".join(evidence.get("reasons", []) or ["-"]),
                 "Requests: %s" % evidence.get("hits", "?"),
                 "Paths   : %s" % ", ".join((evidence.get("paths") or [])[:5]),
                 "",
                 "ALREADY DONE, automatically: %s." % already_done,
                 "Nothing below has happened. Tap to authorise; the ask expires in %dh."
                 % (ASK_TTL_S // 3600)]
        for r in (verdicts or []):
            if r.get("error"):
                lines.append("  [%s] no answer" % r["model"])
            else:
                lines.append("  [%s] %s" % (r["model"], (r.get("headline") or "")[:120]))
        lines += ["", "Counter-attack is not on this menu: it is a criminal offence in every "
                      "jurisdiction we operate in, and the address is usually a compromised third "
                      "party, not the attacker."]

        from . import notify
        notify.telegram("\n".join(lines), reply_markup=_keyboard(incident_id))
        notify._log(evt="shield_ask", ip=ip, incident=incident_id,
                    reasons=evidence.get("reasons", []))
        return incident_id
    except Exception:
        return None


def _hhmm(ts):
    """Absolute UTC clock time. A countdown ("expires in 23h 59m") is arithmetic the operator
    cannot check; a wall-clock time is something he can hold the system to tomorrow."""
    return time.strftime("%H:%M", time.gmtime(ts))


def apply_decisions(shield):
    """Read what the operator tapped and carry it out. Returns a list of applied descriptions.

    THE CONFIRMATION MUST PROVE THE CHANGE, NOT ANNOUNCE IT. The first version replied
    "Applied: holding 1.2.3.4 for 24h", which is the same sentence whether or not anything
    happened. Now each line is read back OUT OF THE SHIELD'S OWN STATE after the write: the actual
    expiry, the actual size of the block list, the actual strict-mode deadline. If the read-back
    disagrees with what was asked for, the operator is told that instead.

    A FAILED ACTION IS REPORTED, NEVER SWALLOWED. Silence after a tap is indistinguishable from
    success, and the whole point of this console is that the operator can trust what it says.
    """
    done, failed = [], []
    try:
        dec = _read(DECISIONS, {})
        if not dec:
            return done
        pend = _read(PENDING, {})
        now = time.time()
        for incident_id, choice in list(dec.items()):
            item = pend.get(incident_id)
            action = (choice or {}).get("action")
            who = (choice or {}).get("by", "?")
            if not item or action not in ACTIONS:
                dec.pop(incident_id, None)
                failed.append("%s: unknown action or the ask has expired" % (action or "?"))
                continue
            ip = item["ip"]
            try:
                if action == "release":
                    shield.unblock(ip)
                    shield.ALLOW_IPS.add(ip)
                    ok = ip in shield.ALLOW_IPS and not shield._blocked.get(ip)
                    done.append("%s released and allowed. Blocked now: %d address(es)"
                                % (ip, len(shield._blocked)) if ok else "")
                    if not ok:
                        failed.append("%s: release did not take" % ip)
                elif action == "hold24":
                    shield._blocked[ip] = now + 86400
                    exp = shield._blocked.get(ip, 0)
                    if exp - time.time() > 86000:
                        done.append("%s held 24h, until %s UTC (read back from shield state)"
                                    % (ip, _hhmm(exp)))
                    else:
                        failed.append("%s: hold not present in shield state after write" % ip)
                elif action == "net":
                    net = ".".join(str(ip).split(".")[:3])
                    if net.count(".") != 2:
                        failed.append("%s: not an IPv4 address, cannot widen to a /24" % ip)
                    else:
                        shield.BLOCK_NETS[net] = now + 3600
                        exp = shield.BLOCK_NETS.get(net, 0)
                        if exp - time.time() > 3500:
                            done.append("%s.0/24 blocked 1h, until %s UTC. Networks held: %d"
                                        % (net, _hhmm(exp), len(shield.BLOCK_NETS)))
                        else:
                            failed.append("%s.0/24: not present in shield state after write" % net)
                elif action == "strict":
                    shield.STRICT_UNTIL[0] = now + 3600
                    if shield.STRICT_UNTIL[0] - time.time() > 3500:
                        done.append("strict mode on 1h, until %s UTC. Every unauthenticated request "
                                    "off the known routes is now tarpitted"
                                    % _hhmm(shield.STRICT_UNTIL[0]))
                    else:
                        failed.append("strict mode: deadline not set")
                elif action == "deny":
                    pth = (item.get("path") or "").strip().lower()
                    if not pth:
                        failed.append("no path recorded on this incident, nothing to ban")
                    else:
                        shield.EXTRA_PROBE_PATHS.add(pth)
                        if shield.probe_shape(pth):
                            done.append("%s added to the probe list. Banned paths: %d"
                                        % (pth, len(shield.EXTRA_PROBE_PATHS)))
                        else:
                            failed.append("%s: added but the detector does not match it" % pth)
                elif action == "abuse":
                    from . import abuse_report
                    r = abuse_report.report(ip, categories="21,15",
                                            comment="Automated web scanning against cybergod.ai")
                    if r:
                        done.append("%s reported to AbuseIPDB" % ip)
                    else:
                        failed.append("%s: AbuseIPDB refused or ABUSEIPDB_KEY is not set" % ip)
            except Exception as e:
                failed.append("%s on %s: %s" % (action, ip, type(e).__name__))
            dec.pop(incident_id, None)
            pend.pop(incident_id, None)
            try:
                from . import notify as _n
                _n._log(evt="shield_action_applied", ip=ip, action=action, by=who,
                        ok=bool(done), detail=(done or failed or ["-"])[-1][:200])
            except Exception:
                pass

        done = [x for x in done if x]
        _write(DECISIONS, dec)
        _write(PENDING, pend)

        if done or failed:
            from . import notify
            L = []
            if done:
                L.append("\U00002705 ГОТОВО / APPLIED")
                L += ["   " + x for x in done]
            if failed:
                L.append("\U0000274C NOT APPLIED")
                L += ["   " + x for x in failed]
            L.append("")
            st = shield.state()
            L.append("Shield now: %d blocked · %d net(s) · %d watching · strict %s"
                     % (len(st.get("blocked") or {}), len(getattr(shield, "BLOCK_NETS", {})),
                        st.get("watching", 0),
                        "ON" if shield.STRICT_UNTIL[0] > time.time() else "off"))
            notify.telegram("\n".join(L))
    except Exception as e:
        try:
            from . import notify
            notify.telegram("\U0000274C Shield console error while applying: %s" % type(e).__name__)
            notify._log(evt="shield_apply_error", err=repr(e)[:200])
        except Exception:
            pass
    return done
