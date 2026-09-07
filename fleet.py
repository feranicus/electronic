#!/usr/bin/env python3
"""fleet.py -- what is ACTUALLY happening on every project, right now, from this machine.

    python fleet.py                  # all projects, last 24h
    python fleet.py --hours 72
    python fleet.py --project jhw-web --ips --paths

WHY THIS EXISTS RATHER THAN THE WEB PAGE. The operator, correctly: "this is bull it will not show
anything because it needs to show this post IAM and IAM is on the server side". The Admin -> Fleet
screen is behind the session gate, so `preview.py` can never render it with real data, and sending
somebody to look at it locally is asking them to admire an empty box. This reads the droplet over
ssh and prints the truth -- the same pattern as recover.py, cost_report.py and agent_forensics.py,
which are the tools that have actually answered questions this month.

READ-ONLY, ONE SSH SESSION. It runs `docker inspect`, reads the shared event log and lists the
heartbeat directory. It changes nothing, and it never touches the projects being reported on.

IT ANSWERS THREE DIFFERENT QUESTIONS AND KEEPS THEM APART:
  1. IS THE CODE THERE?      perseus_client.py present in the running container
  2. IS IT WIRED IN?         the app module actually calls add_middleware -- a file that nothing
                             imports is not a control, which is the whole reason for this exercise
  3. IS IT RUNNING?          a heartbeat newer than 15 minutes
A project can pass 1 and fail 2, which is exactly the state jobhuntwow and jev.best were in for days
while the copy step printed "copied" and nobody was told anything.

AND IT DISTINGUISHES SILENT FROM QUIET. A project with no log lines is one we cannot see, never one
that is safe. That difference is the same one a backup tool must draw between "nothing to do" and
"I cannot find my subject", and getting it wrong is how a week of empty archives looked healthy.
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# service -> the name a human uses. Committed, so a project that stops reporting can be NOTICED;
# a list built from whatever appears in the log would simply stop mentioning it.
# The `service` value each project STAMPS on its own events -- not the container name. jev-api is
# the container; it stamps service=jev-web, and looking for "jev-api" is why this tool reported a
# project as unseeable while its lines sat in the log under another name.
PROJECTS = [("colt-web", "cybergod.ai"), ("jhw-web", "jobhuntwow.com"),
            ("polara-web", "klimaanlage-preise.de"), ("jev-web", "jev.best"),
            ("s4biz-web", "s4biz.io")]
STALE_BEAT_S = 15 * 60


def _script(hours):
    """One session. Everything read-only."""
    return "\n".join([
        "echo '#### CONTAINERS'",
        "docker ps --format '{{.Names}}\\t{{.Status}}' 2>/dev/null",
        "echo '#### WIRED'",
        # Question 2, asked of the RUNNING container rather than of a repo checkout: is the module
        # present, and does anything actually add the middleware?
        "for c in $(docker ps --format '{{.Names}}'); do",
        "  P=$(docker exec $c sh -c 'ls /app/perseus_client.py /opt/perseus_client.py "
        "/app/app/perseus_client.py 2>/dev/null | head -1' 2>/dev/null)",
        "  W=$(docker exec $c sh -c \"grep -rl 'perseus_client.Middleware' /app 2>/dev/null | head -1\" 2>/dev/null)",
        # printf, NOT echo. `echo "$c\\t..."` does not expand \\t under bash, so every row came
        # back as ONE field, the split produced fewer than 3 parts, and the whole table read
        # "none" -- which the CLI then rendered as "wired in: NO" while the web page, reading the
        # heartbeat, correctly showed the sidecar ACTIVE. Two implementations of one question
        # disagreed and the CLI was the one lying.
        "  printf '%s\\t%s\\t%s\\n' \"$c\" \"${P:-none}\" \"${W:-none}\"",
        "done",
        "echo '#### BEATS'",
        "ls -la /var/lib/docker/volumes/colt-stack_colt_events/_data/perseus_beats/ 2>/dev/null "
        "|| echo '(no heartbeat directory - no project is running the sidecar)'",
        "for f in /var/lib/docker/volumes/colt-stack_colt_events/_data/perseus_beats/*.json; do",
        "  [ -f \"$f\" ] && cat \"$f\" && echo",
        "done 2>/dev/null",
        "echo '#### EVENTS'",
        # EVERY PROJECT'S OWN LOG, NOT JUST THE SHARED ONE. klima writes to polara_events and
        # s4biz to s4biz_events -- their own volumes, each with its own promtail. Reading only
        # colt_events reported both as "we cannot see this project", which was true of the TOOL and
        # false about them: I was looking in the wrong place and calling it blindness.
        # ASK THE CONTAINER where its log is (EVENTS_LOG + the mount that contains it), the same
        # rule dbbackup already learned -- a volume name is a guess, docker inspect is an answer.
        "for c in $(docker ps --format '{{.Names}}'); do",
        "  E=$(docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' \"$c\" 2>/dev/null "
        "| sed -n 's/^EVENTS_LOG=//p' | head -1)",
        "  [ -z \"$E\" ] && continue",
        "  D=$(dirname \"$E\")",
        "  H=$(docker inspect -f '{{range .Mounts}}{{.Destination}}|{{.Source}}"
        "{{println}}{{end}}' \"$c\" 2>/dev/null | awk -F'|' -v d=\"$D\" '$1==d {print $2; exit}')",
        "  [ -z \"$H\" ] && continue",
        "  F=\"$H/$(basename \"$E\")\"",
        "  [ -f \"$F\" ] || continue",
        "  echo \"$F\"",
        "done | sort -u | { FOUND=0;",
        "  while read -r L; do FOUND=1; printf 'SIZE %s\\n' \"$(stat -c%s \"$L\")\"; "
        "tail -c 12000000 \"$L\"; done;",
        "  [ \"$FOUND\" = 0 ] && echo 'NOLOG'; }",
        "echo '#### END'",
    ]) + "\n"


def collect(hours, host=None):
    import recover as RC
    prev = RC.HOST
    if host:
        RC.HOST = host                    # override the ATTRIBUTE; RC reads the env at import
    try:
        out, err, rc = RC.ssh_script(_script(hours), timeout=300)
    finally:
        RC.HOST = prev
    if rc != 0 and not out:
        return None, "ssh failed (rc=%s): %s" % (rc, (err or "")[:200])
    return RC.sections(out or ""), ""


def analyse(sec, hours):
    cutoff = time.time() - hours * 3600
    running, wired, beats = {}, {}, {}

    for line in (sec.get("CONTAINERS") or "").splitlines():
        if "\t" in line:
            n, st = line.split("\t", 1)
            running[n.strip()] = st.strip()

    for line in (sec.get("WIRED") or "").splitlines():
        parts = line.split("\t")
        if len(parts) >= 3:
            wired[parts[0].strip()] = {"file": parts[1].strip(), "wired": parts[2].strip()}

    for line in (sec.get("BEATS") or "").splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                d = json.loads(line)
                if d.get("service"):
                    beats[d["service"]] = d
            except Exception:
                pass

    per, log_lines, size, nolog = {}, 0, None, False
    try:
        import shield as _sh          # noqa
    except Exception:
        _sh = None
    if _sh is None:
        sys.path.insert(0, os.path.join(HERE, "webapp", "backend", "app"))
        try:
            import shield as _sh
        except Exception:
            _sh = None

    for line in (sec.get("EVENTS") or "").splitlines():
        line = line.strip()
        if line.startswith("SIZE "):
            try:
                # One SIZE line per project log now, so ACCUMULATE. Keeping the last would report
                # the smallest estate as the whole fleet's volume.
                size = (size or 0) + int(line.split()[1])
            except (ValueError, IndexError):
                size = -1          # present but unreadable: NOT the same as absent
            continue
        if line == "NOLOG":
            nolog = True
            continue
        if not line.startswith("{"):
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        log_lines += 1
        if (d.get("ts") or 0) < cutoff:
            continue
        svc = d.get("service") or ""
        if not svc:
            continue
        p = per.setdefault(svc, {"n": 0, "http": 0, "ips": {}, "paths": {}, "attacks": 0,
                                 "attackers": {}, "last": 0})
        p["n"] += 1
        p["last"] = max(p["last"], d.get("ts") or 0)
        if d.get("evt") != "http":
            continue
        p["http"] += 1
        ip, path = d.get("ip") or "?", (d.get("path") or "?").split("?")[0]
        p["ips"][ip] = p["ips"].get(ip, 0) + 1
        p["paths"][path] = p["paths"].get(path, 0) + 1
        hostile = False
        try:
            hostile = bool(_sh and _sh.probe_shape(path))
        except Exception:
            hostile = False
        if hostile:
            p["attacks"] += 1
            p["attackers"].setdefault(ip, set()).add(path)

    return {"running": running, "wired": wired, "beats": beats, "per": per,
            "log_lines": log_lines, "log_size": size, "nolog": nolog, "hours": hours,
            "classifier": _sh is not None}


def render(a, want=None, show_ips=False, show_paths=False):
    now, L = time.time(), []
    L += ["", "=" * 78, "  FLEET  ·  last %dh  ·  read-only" % a["hours"], "=" * 78, ""]
    if not a["classifier"]:
        L.append("  [!] shield.probe_shape could not be imported here, so ATTACK counts are 0 by")
        L.append("      inability, not by measurement. Do not read them as 'no attacks'.")
        L.append("")
    if a.get("nolog") or (a["log_size"] is None and not a["log_lines"]):
        L.append("  [X] the shared event log was not found on the droplet. Every count below would")
        L.append("      be a statement about our blindness, so there is nothing to report.")
        return "\n".join(L)
    if a["log_size"] and a["log_size"] > 0:
        L.append("  shared event log: %.1f MB, %d line(s) parsed"
                 % (a["log_size"] / 1e6, a["log_lines"]))
    else:
        L.append("  shared event log: size unreadable, %d line(s) parsed (the lines are what "
                 "matters here)" % a["log_lines"])
    L.append("")

    for svc, name in PROJECTS:
        if want and svc != want:
            continue
        m = a["per"].get(svc)
        w = a["wired"].get(svc) or {}
        b = a["beats"].get(svc)
        up = a["running"].get(svc)
        beat_age = int(now - (b.get("ts") or 0)) if b else None

        L.append("-" * 78)
        L.append("  %-22s %s" % (name, "(%s)" % svc))
        L.append("    container   : %s" % (up or "NOT RUNNING"))
        # THE THREE QUESTIONS, KEPT APART. "the file is there" is not "it is wired in", and neither
        # is "it is running" -- conflating them is what made 'copied' look like 'installed'.
        L.append("    client file : %s" % (w.get("file") or "-"))
        L.append("    wired in    : %s" % (
            w.get("wired") if w.get("wired") and w["wired"] != "none"
            else "NO — nothing calls add_middleware(perseus_client.Middleware)"))
        L.append("    heartbeat   : %s" % (
            "active, %ds ago (cycle %s, %s checks)" % (beat_age, b.get("cycle"), b.get("checks"))
            if b and beat_age is not None and beat_age < STALE_BEAT_S
            else "STALE, %ds ago" % beat_age if b else "none — the sidecar has never run here"))

        if not m:
            L.append("    traffic     : NO LOG LINES AT ALL in this window.")
            L.append("                  That means we CANNOT SEE this project. It does not mean it")
            L.append("                  is quiet, and it does not mean it is safe.")
            L.append("")
            continue

        L.append("    traffic     : %d event(s), %d http, %d distinct address(es), last %s UTC"
                 % (m["n"], m["http"], len(m["ips"]),
                    time.strftime("%Y-%m-%d %H:%M", time.gmtime(m["last"]))))
        L.append("    attack-shaped: %d request(s)" % m["attacks"])
        for ip, paths in sorted(m["attackers"].items(), key=lambda kv: -len(kv[1]))[:5]:
            # VARIETY, NOT VOLUME: many DIFFERENT things it cannot have is a scan; the same stale
            # path a hundred times is a person following a dead link.
            L.append("      %-18s %d distinct probe path(s): %s"
                     % (ip, len(paths), ", ".join(sorted(paths)[:4])))
        if show_ips:
            L.append("    top addresses:")
            for ip, n in sorted(m["ips"].items(), key=lambda kv: -kv[1])[:10]:
                L.append("      %6d  %s" % (n, ip))
        if show_paths:
            L.append("    top paths:")
            for p, n in sorted(m["paths"].items(), key=lambda kv: -kv[1])[:10]:
                L.append("      %6d  %s" % (n, p[:64]))
        L.append("")

    L.append("-" * 78)
    unwired = [n for s, n in PROJECTS
               if a["running"].get(s) and (a["wired"].get(s, {}).get("wired", "none") == "none")]
    blind = [n for s, n in PROJECTS if not a["per"].get(s)]
    if unwired:
        L.append("  UNGUARDED (running, sidecar not wired): %s" % ", ".join(unwired))
        L.append("    -> `python ship.py` wires and redeploys cybergod; the others need their own")
        L.append("       deploy to pick up the middleware perseus.py inserted into their source.")
    if blind:
        L.append("  WE ARE BLIND TO: %s" % ", ".join(blind))
        L.append("    -> no log line at all. Nothing below this can be read as 'no attacks'.")
    if not unwired and not blind:
        L.append("  every project is wired, beating and reporting.")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=24)
    ap.add_argument("--project", default=None, help="one service id, e.g. jhw-web")
    ap.add_argument("--ips", action="store_true")
    ap.add_argument("--paths", action="store_true")
    ap.add_argument("--host", default=None)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    sec, err = collect(a.hours, a.host)
    if sec is None:
        print("[X] could not read the droplet: %s" % err)
        print("    Deciding nothing. BLIND is not the same as clean.")
        return 2
    res = analyse(sec, a.hours)
    if a.json:
        res["per"] = {k: {kk: (sorted(vv) if isinstance(vv, set) else vv)
                          for kk, vv in v.items() if kk != "attackers"}
                      for k, v in res["per"].items()}
        print(json.dumps(res, indent=1, default=str))
        return 0
    print(render(res, a.project, a.ips, a.paths))
    return 0


if __name__ == "__main__":
    sys.exit(main())
