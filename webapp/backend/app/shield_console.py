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

THE SECOND HALF (2026-09-17): THE SAME CONSOLE, FOR THE FOUR SIBLING PROJECTS.
The operator received two different messages about the same class of event. cybergod's came with a
menu; jobhuntwow's, jev's, klima's and s4biz's came as flat text -- "SCANNER on jobhuntwow.com" and
nothing he could press -- because colt-web has no code inside those projects' request paths and
therefore nothing to act WITH.

It now has something to act with: `perseus_holds.json`, on the shared volume, which their sidecars
already poll. So the sibling alert gets THE SAME console -- same pending file, same
`sh:<incident>:<action>` callback, same bot handler, same decisions file, same apply loop. There is
ONE console in this estate and this is it; a second one would be a second set of bounds to drift.

WHAT THE SIBLING MENU DELIBERATELY DOES NOT CARRY. Every button must map to something this design
can actually deliver for THAT project, or it must not be on the menu -- a button that does nothing
is worse than no button. `Strict 1h` and `Ban this path` are colt-web's own in-process shield
(`STRICT_UNTIL`, `EXTRA_PROBE_PATHS`); pressing them from a jobhuntwow alert would change
cybergod.ai's posture over evidence from another site. They are not offered. The holds file carries
address holds and nothing else, so the sibling menu carries address holds and nothing else.

AND COUNTER-ATTACK IS STILL NOT ON IT, on any project, ever. DE StGB s.202a/202b/202c (which
criminalises even PREPARING the tooling), EU Directive 2013/40, US CFAA s.1030, Canada CC s.342.1.
The lawful route to a human is a complaint to the provider, which is what `Report abuse` is.
"""
import hashlib
import ipaddress
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


def _keyboard(incident_id, actions=None):
    """Telegram inline keyboard, two per row. callback_data is capped at 64 bytes by the API.

    `actions` defaults to cybergod's own ladder. The sibling console passes FLEET_ACTIONS; the
    keyboard builder itself is shared so the two menus can never diverge in shape, only in content.
    """
    row, rows = [], []
    for key, a in (actions or ACTIONS).items():
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


# =============================================================================================
# THE SIBLING CONSOLE -- jobhuntwow.com, jev.best, klimaanlage-preise.de, s4biz.io
# =============================================================================================
#
# THE CONTRACT, and it is fixed. The sidecars read this file; this module is the only thing in
# cybergod that writes it.
#
#     /var/log/colt/perseus_holds.json
#     {"generated": <epoch>,
#      "holds": [{"cidr": "104.28.222.0/24", "service": "jhw-web",
#                 "until": <epoch>, "why": "operator: Block /24 1h", "by": "telegram"}]}
#
# `service` scopes a hold to ONE project (the `service` name fleet.PROJECTS stamps on its rows);
# "*" means every project, is never written from a per-project alert, and is never released by one.
#
# IT IS A SEPARATE FILE FROM perseus_blocklist.json ON PURPOSE. The nightly cycle REWRITES the
# blocklist from the vetted ruleset, so an operator action parked there would be erased by the next
# 04:40 publish -- silently, and only noticed when the address came back.
HOLDS = os.path.join(STATE_DIR, "perseus_holds.json")

# THE BOUNDS. Every one of them is a CEILING committed in code; the environment may lower a bound
# and can never raise one. A limit an env var can widen is not a limit, and the .env on that droplet
# is the least reviewed surface in the estate.
#
#   HOLD_CEILING_S = 86400 (24h)  matches the longest rung on cybergod's own ladder (`hold24`).
#       Nothing here creates a permanent hold and there is no code path that can: `until` is
#       mandatory, must be in the future, and must be within this ceiling -- checked in the WRITER,
#       not only in the callers, so a future caller inherits the bound instead of re-deriving it.
#   MAX_HOLDS = 64                each hold costs one deliberate operator tap, and a repeat alert
#       for an address already held is suppressed, so the realistic ceiling is taps-per-day, not
#       packets. 64 holds x ~130 bytes is ~8 KB, re-read by five sidecars -- free. At the cap a new
#       hold is REFUSED and the operator is told; nothing is silently evicted, because evicting a
#       hold he asked for is the same defect as never creating it.
#   The prefix is capped at /24 (IPv4) and /64 (IPv6). A /16 is 65,536 addresses of somebody else's
#       customers on the evidence of one scanner, so it is not offered and not writable.
HOLD_CEILING_S = 86400
HOLD_FLOOR_S = 60
HOLDS_CEILING = 64


def _bounded_env(name, default, lo, hi):
    """An env override that can only ever move a bound INWARDS. Never raises: a typo in a .env
    must not stop this module importing (fleet.py already paid for that one)."""
    try:
        v = int(os.environ.get(name) or default)
    except Exception:
        v = default
    return max(lo, min(hi, v))


MAX_HOLD_S = _bounded_env("FLEET_MAX_HOLD_S", HOLD_CEILING_S, HOLD_FLOOR_S, HOLD_CEILING_S)
MAX_HOLDS = _bounded_env("FLEET_MAX_HOLDS", HOLDS_CEILING, 1, HOLDS_CEILING)
# How long "False alarm" keeps this console quiet about that address on that project.
FLEET_MUTE_S = _bounded_env("FLEET_MUTE_S", 86400, 300, 86400)

# THE SIBLING MENU. Each entry says what it does and, in `hold`, how this design delivers it:
#   ("ip", n)   a /32 (or /128) hold on that one address, for n seconds, on that ONE project
#   ("net", n)  the /24 the address sits in, for n seconds, on that ONE project -- IPv4 only
#   ("abuse",)  a complaint to the address's provider through AbuseIPDB. Not a hold, not a packet
#               to the source, and the only lawful route to a human behind it.
#   ("release",) drop every hold THIS project has on that address and stop alerting about it
# Keys are deliberately distinct from ACTIONS: a fleet key can never be applied through cybergod's
# own branch, and cybergod's `strict`/`deny` can never be applied to a sibling.
FLEET_ACTIONS = {
    "fhold1":   {"label": "Hold 1h",      "hold": ("ip", 3600),
                 "what": "hold this address on this project for one hour"},
    "fhold24":  {"label": "Hold 24h",     "hold": ("ip", 86400),
                 "what": "hold this address on this project for 24 hours"},
    "fnet1":    {"label": "Block /24 1h", "hold": ("net", 3600),
                 "what": "hold the whole /24 on this project for one hour"},
    "fabuse":   {"label": "Report abuse", "hold": ("abuse",),
                 "what": "submit the address to AbuseIPDB (community blocklist)"},
    "frelease": {"label": "False alarm",  "hold": ("release",),
                 "what": "release this project's holds on the address and stop alerting about it"},
}

# (service, ip) -> epoch until which the operator has said this source is not worth telling him
# about. In memory, in colt-web, which is the SAME process that both announces and applies -- so it
# cannot drift from the thing it suppresses. It is lost on restart, and that is the safe direction:
# the worst case is one more alert about a source he already dismissed.
_fleet_muted = {}


# ------------------------------------------------------------------ authorisation
def operator_chats():
    """The chat id(s) ALERT_TG_CHAT names, read at CALL time so a test (or a set_secret) is seen
    without an import cycle. notify.py owns the same variable for DELIVERY; this reads it for
    AUTHORISATION, which is the same question -- who is the operator -- asked in the other
    direction."""
    return [c.strip() for c in (os.environ.get("ALERT_TG_CHAT", "") or "").split(",") if c.strip()]


def authorised(decision):
    """(ok, reason) -- may this decision write a hold? FAILS CLOSED, and NAMES why.

    THIS IS THE WHOLE RISK OF THE FEATURE. A callback that reaches this bot can stop traffic on
    five production sites. cybergod's own ladder has been gated in ONE place since August -- the
    bot's `AUTH.is_authed(uid, ALLOWED)` -- and `apply_decisions` below has never verified anything
    itself: it trusts `shield_decisions.json` completely. For cybergod's own in-process shield that
    is defensible (worst case is cybergod.ai blocking an address for a day, with a release button
    in the same message). For a hold that reaches four OTHER production sites it is not, so the
    acting process checks for itself rather than inheriting a check it cannot see.

    Two accepted proofs, in order of strength:
      * `chat` -- the originating Telegram chat, verified against ALERT_TG_CHAT. When it is present
        it is AUTHORITATIVE: a chat that is not the operator's is refused even if the identity
        beside it looks fine, because a mismatched origin is positive evidence, not a missing field.
      * `by` -- the authenticated identity the bot recorded, verified against colt_auth.ADMINS (the
        committed `ADMIN_EMAILS`, extensible by EXTRA_ADMIN_EMAILS). This is what the bot writes
        today. It is deliberately NARROWER than the bot's own gate: a Colt AE or a partner may be
        authorised to run an assessment and must not thereby be authorised to block addresses on
        somebody else's site.
    Neither present -> refused. An unset ALERT_TG_CHAT does not mean "any chat".
    """
    d = decision or {}
    chat = str(d.get("chat") or "").strip()
    by = str(d.get("by") or "").strip().lower()
    if chat:
        allowed = operator_chats()
        if not allowed:
            return False, ("ALERT_TG_CHAT is not configured, so the callback's chat id cannot be "
                           "checked against anything; refusing rather than trusting its own claim")
        if chat not in allowed:
            return False, ("the callback came from chat %s, which is not the operator chat "
                           "(ALERT_TG_CHAT)" % chat)
        return True, "chat %s is the configured operator chat" % chat
    if by:
        try:
            import colt_auth
            ok = bool(colt_auth.is_admin(by))
        except Exception as exc:
            # A gate that cannot read its own list refuses. "We could not check" is not "allowed".
            return False, ("the administrator list could not be read (%s), so authorisation cannot "
                           "be established" % type(exc).__name__)
        if ok:
            return True, "%s is an administrator (colt_auth.ADMIN_EMAILS)" % by
        return False, ("%s is authorised to use the bot but is not an administrator; a hold reaches "
                       "four other production sites and is admin-only" % by)
    return False, "the decision carries neither an originating chat id nor an authenticated identity"


# ------------------------------------------------------------------ the holds file
def _now(now=None):
    return float(now if now is not None else time.time())


def _hold_ok(h, now):
    """(ok, reason) for ONE record. THE LAST GATE BEFORE DISK, which is why it lives in the writer
    and not in the five callers: a bound that every caller has to remember is a bound that the sixth
    caller will not have."""
    if not isinstance(h, dict):
        return False, "not an object"
    cidr, svc = str(h.get("cidr") or ""), str(h.get("service") or "")
    if not cidr or not svc:
        return False, "a hold must name both a cidr and a service"
    try:
        net = ipaddress.ip_network(cidr, strict=False)
    except Exception as exc:
        return False, "%r is not a network (%s)" % (cidr[:40], type(exc).__name__)
    floor = 24 if net.version == 4 else 64
    if net.prefixlen < floor:
        return False, ("%s is wider than the /%d maximum: that is other people's customers on the "
                       "evidence of one scanner" % (cidr, floor))
    until = h.get("until")
    if isinstance(until, bool) or not isinstance(until, (int, float)):
        return False, "`until` is mandatory and must be an epoch number; there is no permanent hold"
    if until <= now:
        return False, "`until` (%d) is not in the future" % int(until)
    if until > now + MAX_HOLD_S:
        return False, ("`until` is %ds away, beyond the %ds maximum"
                       % (int(until - now), MAX_HOLD_S))
    return True, ""


def _write_holds(holds, now=None):
    """Validate, bound, and write ATOMICALLY. Returns (written, rejected_reasons).

    ATOMIC BECAUSE FIVE SIDECARS READ THIS WHILE WE WRITE IT. temp file in the SAME directory, then
    os.replace -- a rename inside one directory is atomic on POSIX and on Windows, so a reader sees
    either the whole previous file or the whole new one and never a half-written JSON document that
    would parse as "no holds at all" and quietly disarm every project.
    """
    now = _now(now)
    keep, rejected = [], []
    for h in holds or []:
        ok, why = _hold_ok(h, now)
        if not ok:
            rejected.append(why)
            continue
        if len(keep) >= MAX_HOLDS:
            rejected.append("the live-hold cap of %d is reached; %s was not added"
                            % (MAX_HOLDS, h.get("cidr")))
            continue
        keep.append({"cidr": str(h["cidr"]), "service": str(h["service"]),
                     "until": int(h["until"]), "why": str(h.get("why") or "")[:200],
                     "by": str(h.get("by") or "telegram")[:40]})
    doc = {"generated": int(now), "holds": keep}
    try:
        os.makedirs(os.path.dirname(HOLDS), exist_ok=True)
        tmp = HOLDS + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2)
        os.replace(tmp, HOLDS)
    except Exception as exc:
        rejected.append("the holds file could not be written: %s" % type(exc).__name__)
        return [], rejected
    return keep, rejected


def live_holds(now=None):
    """Every unexpired hold on disk. An unreadable or malformed file yields NO holds and claims
    nothing -- absence of evidence is not a finding, here it is just an empty console."""
    now = _now(now)
    doc = _read(HOLDS, {})
    out = []
    for h in (doc or {}).get("holds") or []:
        try:
            if isinstance(h, dict) and float(h.get("until") or 0) > now:
                out.append(h)
        except Exception:
            continue
    return out


def held(ip, service, now=None):
    """Is this address already held for this project? '*' covers every project."""
    try:
        addr = ipaddress.ip_address(str(ip))
    except Exception:
        return False
    for h in live_holds(now):
        if h.get("service") not in (service, "*"):
            continue
        try:
            if addr in ipaddress.ip_network(str(h.get("cidr")), strict=False):
                return True
        except Exception:
            continue
    return False


def add_hold(cidr, service, seconds, label, now=None):
    """Create one bounded hold and READ IT BACK OFF DISK. Returns (record_or_None, note, live_n).

    The record returned is the one the file actually contains, never the one we intended to write:
    the confirmation the operator reads is built from it, and a confirmation composed from the
    REQUEST is the same sentence whether or not anything happened.
    """
    now = _now(now)
    seconds = max(HOLD_FLOOR_S, min(int(seconds), MAX_HOLD_S))
    rec = {"cidr": cidr, "service": service, "until": int(now + seconds),
           "why": "operator: %s" % label, "by": "telegram"}
    current = [h for h in live_holds(now)
               if not (h.get("service") == service and str(h.get("cidr")) == str(cidr))]
    written, rejected = _write_holds(current + [rec], now)
    back = next((h for h in written
                 if h.get("service") == service and str(h.get("cidr")) == str(cidr)), None)
    if back is None:
        return None, (rejected[-1] if rejected else "the hold is not in the file after the write"), \
               len(written)
    return back, "", len(written)


def release_holds(ip, service, now=None):
    """Drop every hold THIS project has on that address. Returns (removed, remaining).

    A "*" hold is never touched from a per-project alert: it was created for the whole estate and
    releasing it from one project's message would silently unblock four others.
    """
    now = _now(now)
    try:
        addr = ipaddress.ip_address(str(ip))
    except Exception:
        return 0, len(live_holds(now))
    keep, removed = [], 0
    for h in live_holds(now):
        hit = False
        if h.get("service") == service:
            try:
                hit = addr in ipaddress.ip_network(str(h.get("cidr")), strict=False)
            except Exception:
                hit = False
        if hit:
            removed += 1
        else:
            keep.append(h)
    written, _rej = _write_holds(keep, now)
    return removed, len(written)


# ------------------------------------------------------------------ the sibling alert
def _accepts_markup(fn):
    """Does this transport carry an inline keyboard? READ THE SIGNATURE -- do not call it and catch
    TypeError, because a TypeError raised INSIDE a real send would then be misread as 'no buttons'
    and the operator would silently lose the menu."""
    try:
        import inspect
        return "reply_markup" in inspect.signature(fn).parameters
    except Exception:
        return False


def _open_ask(service, ip, now):
    """Is there already an UNANSWERED menu on the operator's phone for this source on this project?

    THIS IS THE EDGE. The old sibling alert re-sent itself every five minutes for as long as the
    scanner kept scanning, because `watch()` only suppressed lines it had already READ. Now the
    state that matters is whether the operator has something to press: while an ask is open, or
    while the address is held, a second identical message adds nothing and trains him to swipe the
    next one away.
    """
    for _id, v in (_read(PENDING, {}) or {}).items():
        if (v.get("kind") == "fleet" and v.get("service") == service and v.get("ip") == ip
                and now - (v.get("ts") or 0) < ASK_TTL_S):
            return True
    return False


def should_announce(service, ip, now=None):
    """(bool, reason). The reason is returned rather than logged here so the caller can print the
    COMPARISON it made; a suppression nobody can see is indistinguishable from a broken detector."""
    now = _now(now)
    if held(ip, service, now):
        return False, "already held on %s" % service
    if _fleet_muted.get((service, ip), 0) > now:
        return False, "the operator called this a false alarm; muted until %s UTC" % _hhmm(
            _fleet_muted[(service, ip)])
    if _open_ask(service, ip, now):
        return False, "an unanswered menu for this source is already on the operator's phone"
    return True, "no hold, no mute and no open ask for %s on %s" % (ip, service)


def fleet_text(name, ip, paths):
    """THE LEGACY LINE, unchanged. A transport that cannot carry buttons gets exactly what it got
    before this feature existed -- never a message that describes a menu it is not showing."""
    return ("SCANNER on %s\n%s asked for %d distinct probe paths\n  %s"
            % (name, ip, len(paths), "\n  ".join(list(paths)[:6])))


def announce_fleet(name, service, ip, paths, send=None, now=None):
    """The sibling alert, WITH the menu. Returns the incident id, or None if nothing was sent.

    `send` is the transport the caller already uses (fleet.watch is handed notify.telegram). When it
    cannot carry a keyboard this degrades to `fleet_text` and writes NO console state: a pending ask
    nobody can answer is an expiry waiting to happen and would suppress the next real alert.
    """
    try:
        now = _now(now)
        if send is None:
            from . import notify as _n
            send = _n.telegram
        paths = sorted(set(paths or []))
        if not _accepts_markup(send):
            send(fleet_text(name, ip, paths))
            return None

        ok, why = should_announce(service, ip, now)
        if not ok:
            _tg_log(evt="fleet_ask_suppressed", service=service, ip=ip, reason=why)
            return None

        # SHORT AND CONSTANT-LENGTH. callback_data is capped at 64 bytes by the Telegram API and an
        # IPv6 address written into the id blows straight past it -- the menu would then arrive with
        # some buttons silently missing. The id is a digest; the pending record carries the facts.
        incident_id = "fl" + hashlib.sha1(
            ("%s|%s|%d" % (service, ip, int(now))).encode("utf-8")).hexdigest()[:10]
        pend = _read(PENDING, {})
        pend = {k: v for k, v in pend.items() if now - (v.get("ts") or 0) < ASK_TTL_S}
        pend[incident_id] = {"kind": "fleet", "ip": ip, "service": service, "name": name,
                             "ts": now, "paths": paths[:8]}
        _write(PENDING, pend)

        lines = ["\U0001f6e1 SCANNER on %s" % name,
                 "",
                 "IP      : %s" % ip,
                 "Project : %s (%s)" % (name, service),
                 "Probes  : %d distinct paths" % len(paths)]
        lines += ["  %s" % p for p in paths[:6]]
        lines += ["",
                  "NOTHING has been done automatically. cybergod has no code in %s's request path; "
                  "it can only ask that project's own sidecar to hold an address." % name,
                  "Every option below is TIME-BOXED and expires by itself -- the longest is %dh, "
                  "and there is no permanent hold on this menu. The ask itself expires in %dh."
                  % (MAX_HOLD_S // 3600, ASK_TTL_S // 3600),
                  "",
                  "Counter-attack is not on this menu: it is a criminal offence in every "
                  "jurisdiction we operate in, and the address is usually a compromised third "
                  "party, not the attacker."]
        send("\n".join(lines), reply_markup=_keyboard(incident_id, FLEET_ACTIONS))
        _tg_log(evt="fleet_ask", service=service, ip=ip, incident=incident_id, paths=len(paths))
        return incident_id
    except Exception as exc:
        _tg_log(evt="fleet_ask_error", service=service, ip=ip, err=repr(exc)[:160])
        return None


def _tg_log(**k):
    """notify._log, but it may never take down the thing it is observing."""
    try:
        from . import notify as _n
        _n._log(**k)
    except Exception:
        try:
            print(json.dumps(dict(k, ts=time.time())), flush=True)
        except Exception:
            pass


def _dur(seconds):
    return "%dh" % (seconds // 3600) if seconds >= 3600 else "%dm" % (seconds // 60)


def _apply_fleet(item, action, choice, now):
    """One tapped sibling action. Returns (applied_line, refused_line); exactly one is non-empty.

    THE CONFIRMATION SAYS WHAT WAS DONE, TO WHAT, AND WHEN IT LAPSES -- read back off the file, in
    absolute UTC. A countdown is arithmetic the operator cannot check; a wall-clock time is
    something he can hold the system to.
    """
    svc = str(item.get("service") or "")
    name = str(item.get("name") or svc)
    ip = str(item.get("ip") or "")
    spec = FLEET_ACTIONS[action]
    label = spec["label"]

    ok, why = authorised(choice)
    if not ok:
        # LOGGED, ALWAYS. A refusal that leaves no trace is indistinguishable from a message that
        # never arrived, and this is the one refusal an investigation would need.
        _tg_log(evt="fleet_hold_refused", service=svc, ip=ip, action=action,
                by=(choice or {}).get("by"), chat=(choice or {}).get("chat"), reason=why)
        return "", "%s on %s REFUSED: %s. Nothing was changed." % (label, name, why)

    kind = spec["hold"][0]
    if kind == "release":
        removed, remaining = release_holds(ip, svc, now)
        # Prune first: this dict is only ever grown by an operator tap, but a process that lives for
        # months should not keep a key for every address he ever dismissed.
        for k in [k for k, v in _fleet_muted.items() if v <= now]:
            _fleet_muted.pop(k, None)
        _fleet_muted[(svc, ip)] = now + FLEET_MUTE_S
        _tg_log(evt="fleet_hold_released", service=svc, ip=ip, removed=removed, by=why)
        return ("%s released on %s: %d hold(s) dropped, %d still live estate-wide. No further "
                "alert about it on %s until %s UTC."
                % (ip, name, removed, remaining, name,
                   _hhmm(_fleet_muted[(svc, ip)]))), ""

    if kind == "abuse":
        try:
            from . import abuse_report
            r = abuse_report.report(ip, categories="21,15",
                                    comment="Automated web scanning against %s" % name)
        except Exception as exc:
            return "", "%s: AbuseIPDB call failed (%s)" % (ip, type(exc).__name__)
        if not r:
            return "", "%s: AbuseIPDB refused or ABUSEIPDB_KEY is not set. No hold was created." % ip
        _tg_log(evt="fleet_abuse_reported", service=svc, ip=ip, by=why)
        return ("%s reported to AbuseIPDB as a scanner of %s. This is a complaint to its provider, "
                "not a packet to the source, and it creates NO hold -- %s is still served to it."
                % (ip, name, name)), ""

    seconds = spec["hold"][1]
    if kind == "net":
        try:
            addr = ipaddress.ip_address(ip)
        except Exception:
            return "", "%s is not an address, so it cannot be widened to a /24" % ip
        if addr.version != 4:
            return "", ("%s is IPv6; this console only widens IPv4 to a /24. Use Hold 1h/24h for "
                        "the single address." % ip)
        cidr = str(ipaddress.ip_network("%s/24" % ip, strict=False))
    else:
        cidr = "%s/%d" % (ip, 32 if ":" not in ip else 128)
        try:
            cidr = str(ipaddress.ip_network(cidr, strict=False))
        except Exception:
            return "", "%s is not an address" % ip

    rec, note, live_n = add_hold(cidr, svc, seconds, label, now)
    if rec is None:
        _tg_log(evt="fleet_hold_failed", service=svc, ip=ip, action=action, reason=note)
        return "", "%s on %s NOT applied: %s" % (label, name, note)
    _tg_log(evt="fleet_hold_applied", service=svc, ip=ip, cidr=rec["cidr"],
            until=rec["until"], action=action, by=why)
    return ("%s held on %s until %s UTC (%s, expires by itself). Live holds: %d of %d. It takes "
            "effect when %s's sidecar next reads %s."
            % (rec["cidr"], name, _hhmm(rec["until"]), _dur(seconds), live_n, MAX_HOLDS,
               name, os.path.basename(HOLDS))), ""


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
            # WHICH MENU THIS INCIDENT CAME FROM, read off the PENDING RECORD, never guessed from
            # the shape of the id. The two action tables are disjoint, so cybergod's `strict` can
            # never be applied to a sibling and a sibling's `fhold24` can never reach this shield.
            kind = (item or {}).get("kind")
            valid = FLEET_ACTIONS if kind == "fleet" else ACTIONS
            if not item or action not in valid:
                dec.pop(incident_id, None)
                failed.append("%s: unknown action or the ask has expired" % (action or "?"))
                continue
            ip = item["ip"]
            try:
                if kind == "fleet":
                    good, bad = _apply_fleet(item, action, choice, now)
                    if good:
                        done.append(good)
                    if bad:
                        failed.append(bad)
                elif action == "release":
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
            # THE OTHER FOUR SITES, in the same trailer and from the same read-back discipline. The
            # soonest expiry is named so "time-boxed" is a number the operator can check, not a
            # claim -- and an empty list says so rather than printing a bare 0.
            lh = live_holds()
            L.append("Fleet holds: %d of %d live%s"
                     % (len(lh), MAX_HOLDS,
                        (", next lapses %s UTC" % _hhmm(min(h["until"] for h in lh))) if lh
                        else " (no sibling project is holding anything)"))
            notify.telegram("\n".join(L))
    except Exception as e:
        try:
            from . import notify
            notify.telegram("\U0000274C Shield console error while applying: %s" % type(e).__name__)
            notify._log(evt="shield_apply_error", err=repr(e)[:200])
        except Exception:
            pass
    return done
