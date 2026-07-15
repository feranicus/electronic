#!/usr/bin/env python3
"""jhw.py — the ONE ops entry point for JobHuntWOW (no shell blobs; see CLAUDE.md).

    python jhw.py run 4435446898        # A->Z: backend+sandbox+login+scrape+tailor+apply (ONE command)
    python jhw.py login                 # ensure LinkedIn login (auto, else one-time manual in noVNC)
    python jhw.py backend       # (re)start the backend + /v1 proxy (repo-root compose)
    python jhw.py up            # build + start the secure-browser sandbox (Chrome + noVNC)
    python jhw.py watch         # print the noVNC URL to watch/drive the browser
    python jhw.py scrape 4435446898     # read a LinkedIn job -> out/job.json
    python jhw.py tailor                # scraped JD + Profile.pdf -> tailored resume + cover letter
    python jhw.py apply  4435446898     # drive Apply -> ATS, fill through Review (human submits)
    python jhw.py status        # container + health + noVNC URL
    python jhw.py logs          # follow sandbox logs
    python jhw.py down          # stop the sandbox

Wraps Docker so operations are re-runnable and documented. The sandbox compose lives in agent/;
the backend compose lives in the repo root (agent/..). Run from anywhere.
"""
from __future__ import annotations
import argparse, os, shutil, subprocess, sys

try:
    _SELF = os.path.abspath(__file__)
except OSError:
    # WSL+Docker can replace the CWD inode, killing getcwd(); recover via $PWD (same path, new inode)
    os.chdir(os.environ.get("PWD", "/"))
    _SELF = os.path.abspath(__file__)
HERE = os.path.dirname(_SELF)                              # .../agent
ROOT = os.path.abspath(os.path.join(HERE, ".."))            # .../jobhuntwow-app (backend compose)
NOVNC = "http://localhost:9090/vnc.html"
COOKIES = os.path.join(HERE, "linkedin_cookies.json")
COOKIES_SRC = os.path.abspath(os.path.join(HERE, "..", "..", "linkedin_cookies.json"))


def sh(*args, cwd=HERE, check=True):
    print("···", " ".join(args), f"(in {os.path.basename(cwd)})")
    return subprocess.run(args, cwd=cwd, check=check)


def dc(*args, cwd=HERE, check=True):
    return sh("docker", "compose", *args, cwd=cwd, check=check)


def ensure_prereqs():
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    if not os.path.exists(COOKIES):
        if os.path.exists(COOKIES_SRC):
            shutil.copy(COOKIES_SRC, COOKIES); print(f"[OK] copied LinkedIn cookies from {COOKIES_SRC}")
        else:
            print(f"[WARN] {COOKIES} missing and none at {COOKIES_SRC}. Export your LinkedIn cookies (JSON) there.")
    if not os.path.exists(os.path.join(HERE, ".env")):
        print("[WARN] agent/.env missing — set JHW_PROXY_BASE + AGENT_PROXY_TOKEN (see .env.example).")


def cmd_backend(_):
    # repo-root compose holds the backend + /v1 proxy; --force-recreate reloads .env (model routing).
    dc("up", "-d", "--build", "--force-recreate", "backend", cwd=ROOT)
    print("[OK] backend restarted (reloaded model routing from repo-root .env).")


def cmd_up(_):
    ensure_prereqs(); dc("up", "-d", "--build")
    print(f"\n[OK] Sandbox starting. Watch the browser at: {NOVNC}\n     ~30s, then: python jhw.py status")


def cmd_down(_): dc("down")
def cmd_watch(_): print(f"Open the browser view here: {NOVNC}")
def cmd_status(_): dc("ps", check=False); print(f"\nnoVNC (watch/drive): {NOVNC}")
def cmd_logs(_): dc("logs", "-f", check=False)


def _exec_agent(goal, job, out=None):
    ensure_prereqs()
    args = ["exec", "-T", "jhw-agent", "python3", "/agent/agent.py", goal, job]
    if out: args += ["--out", out]
    print(f"[i] {goal} job {job} — watch live at {NOVNC}")
    dc(*args, check=False)


def cmd_scrape(a):
    _exec_agent("scrape", a.job, "/agent/out/job.json")
    print(f"[OK] result (if any) -> {os.path.join(HERE, 'out', 'job.json')}")


def cmd_apply(a):
    _ensure_stack()                       # ONE command: bring backend + sandbox up, wait healthy, then apply
    _exec_agent("apply", a.job)


def cmd_tailor(_):
    # reads out/job.json + Profile.pdf -> resume.pdf, cover_letter.pdf, fields.json (in out/)
    ensure_prereqs()
    print(f"[i] tailor: extract + content LLMs -> out/  (needs a prior `scrape`)")
    dc("exec", "-T", "jhw-agent", "python3", "/agent/tailor.py", check=False)
    print(f"[OK] resume/cover-letter (if any) -> {os.path.join(HERE, 'out')}")




def _envval(key):
    f = os.path.join(HERE, ".env")
    if not os.path.exists(f): return ""
    for line in open(f, encoding="utf-8"):
        if line.strip().startswith(key + "="):
            return line.split("=", 1)[1].strip()
    return ""


def cmd_telegram(_):
    """Discover your Telegram chat id (message the bot first), and send a test message."""
    import json as _j, urllib.request as _u
    tok = _envval("TELEGRAM_BOT_TOKEN")
    if not tok:
        print("Set TELEGRAM_BOT_TOKEN in agent/.env first.\n"
              "1) In Telegram, message @BotFather -> /newbot -> copy the token.\n"
              "2) Put it in agent/.env as TELEGRAM_BOT_TOKEN=...\n"
              "3) Send any message to your new bot, then run `python jhw.py telegram` again.")
        return
    base = f"https://api.telegram.org/bot{tok}"
    try:
        data = _j.loads(_u.urlopen(f"{base}/getUpdates", timeout=20).read())
    except Exception as e:
        print(f"[ERR] Telegram API: {e}"); return
    chats = {}
    for upd in data.get("result", []):
        m = upd.get("message", {}); ch = m.get("chat", {})
        if ch.get("id"): chats[ch["id"]] = ch.get("first_name") or ch.get("title") or ""
    if not chats:
        print("No messages yet. Send any message to your bot in Telegram, then re-run `python jhw.py telegram`.")
        return
    print("Found chats (put the id in agent/.env as TELEGRAM_CHAT_ID):")
    for cid, nm in chats.items(): print(f"  {cid}   {nm}")
    cur = _envval("TELEGRAM_CHAT_ID")
    if cur:
        try:
            _u.urlopen(f"{base}/sendMessage?chat_id={cur}&text=%E2%9C%85%20JobHuntWOW%20is%20connected.", timeout=20)
            print(f"[OK] sent a test message to chat {cur}")
        except Exception as e:
            print(f"[warn] test send failed: {e}")


def cmd_models(_):
    """List the model ids your DO key can actually use (via the backend). Run backend first."""
    import json as _j, urllib.request as _u
    try:
        data = _j.loads(_u.urlopen("http://localhost:8000/api/models", timeout=30).read())
    except Exception as e:
        print(f"[ERR] backend not reachable on :8000 ({e}). Run `python jhw.py backend` first."); return
    models = data.get("models") or []
    if not models:
        print("[WARN] backend returned no models:", data); return
    print(f"Models available to your DO key ({len(models)}):")
    for m in sorted(models): print("  ", m)
    print("\nTell Claude which to use for driver(vision)/content/extract, or paste this list.")



def _accounts_path():
    p = os.path.join(HERE, "out", "ats_accounts.json"); os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


def cmd_atspw(a):
    """Store STABLE ATS account credentials for a host. The login email can differ from the résumé
       contact email (e.g. a Workday account under your gmail):
         python jhw.py atspw redhat.wd5.myworkdayjobs.com 'cLR|6eKZ-9c\\E4yU,afX' feranicus@gmail.com"""
    import json as _j
    email = getattr(a, "email", "") or ""
    if not email:
        try:
            email = _j.load(open(os.path.join(HERE, "templates", "resume_data.json"), encoding="utf-8")).get("basics", {}).get("email", "")
        except Exception:
            pass
    path = _accounts_path()
    try:
        acc = _j.load(open(path, encoding="utf-8"))
    except Exception:
        acc = {}
    acc[a.host] = {"email": email, "password": a.password}
    _j.dump(acc, open(path, "w"), indent=2)
    print(f"[OK] stored ATS login for {a.host} (user={email}). `python jhw.py apply <job>` will sign in.")


def cmd_import_passwords(a):
    """Bulk-load ATS logins from a Chrome/Google Password Manager CSV export (chrome://password-manager
       -> Settings -> Export passwords). One export populates every company's login at once."""
    import csv, json as _j, re as _re
    path = _accounts_path()
    try:
        acc = _j.load(open(path, encoding="utf-8"))
    except Exception:
        acc = {}
    n = 0
    with open(a.csv, newline="", encoding="utf-8", errors="ignore") as f:
        for row in csv.DictReader(f):
            row = { (k or "").lower(): v for k, v in row.items() }
            url, user, pwd = row.get("url", ""), row.get("username", ""), row.get("password", "")
            if not url or not pwd:
                continue
            host = _re.sub(r"^https?://", "", url).split("/")[0].lower()
            acc[host] = {"email": user, "password": pwd}
            n += 1
    _j.dump(acc, open(path, "w"), indent=2)
    print(f"[OK] imported {n} logins into out/ats_accounts.json — apply will now sign in to any of them.")


def cmd_inspect(_):
    """Dump the REAL DOM (fields, buttons, data-automation-ids) of the ATS tab currently open in the
       sandbox — so selectors are written from ground truth, not guesses. Open the ATS page first."""
    _ensure_stack()
    print("[i] inspecting the front ATS tab in the sandbox (open the ATS page in noVNC first) …")
    dc("exec", "-T", "jhw-agent", "python3", "/agent/flows/probe.py", check=False)
    print(f"[OK] full dump -> {os.path.join(HERE, 'out', 'dom_dump.json')}")


def cmd_login(_):
    ensure_prereqs()
    print("[i] ensuring LinkedIn login (auto, else one-time manual in noVNC) …")
    dc("exec", "-T", "jhw-agent", "python3", "/agent/agent.py", "login", check=False)


def _healthy(t=2):
    import urllib.request as _u
    for url in ("http://127.0.0.1:9222/json/version", "http://127.0.0.1:8000/api/health"):
        try:
            _u.urlopen(url, timeout=t)
        except Exception:
            return False
    return True


def _ensure_stack(build=False):
    """One command: ensure backend + /v1 proxy + browser sandbox are up, then return. `up -d` already
       blocks until the containers are running, so no health poll (WSL can't reach the published ports)."""
    ensure_prereqs()
    flags = ["up", "-d"] + (["--build", "--force-recreate"] if build else [])
    dc(*(flags + ["backend"]), cwd=ROOT, check=False)   # backend holds the DO key + model routing
    dc(*flags, check=False)                              # secure-browser sandbox (Chrome + noVNC)


def _wait_health():
    import time as _t
    for i in range(20):                                 # ~40s cap, then continue anyway
        if _healthy():
            print("[OK] stack healthy."); return True
        print("[i] waiting for backend (:8000) + sandbox (:9222) …" if i == 0 else ".",
              end="", flush=True)
        _t.sleep(2)
    print("\n[warn] health wait timed out — continuing anyway.")
    return False


def cmd_run(a):
    """A->Z orchestrator: backend + sandbox + login + scrape + tailor + apply, one command."""
    ensure_prereqs()
    dc("up", "-d", "--build", "--force-recreate", "backend", cwd=ROOT)   # backend + model routing
    dc("up", "-d", "--build")                                            # secure-browser sandbox
    _wait_health()
    cmd_login(None)
    print(f"\n[i] === scrape {a.job} ==="); _exec_agent("scrape", a.job, "/agent/out/job.json")
    print("\n[i] === tailor ==="); dc("exec", "-T", "jhw-agent", "python3", "/agent/tailor.py", check=False)
    print(f"\n[i] === apply {a.job} ==="); _exec_agent("apply", a.job)
    print(f"\n[OK] pipeline done. Review in noVNC ({NOVNC}) and click Submit.")


def main():
    p = argparse.ArgumentParser(description="jhw-agent ops")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("backend").set_defaults(fn=cmd_backend)
    sub.add_parser("up").set_defaults(fn=cmd_up)
    sub.add_parser("down").set_defaults(fn=cmd_down)
    sub.add_parser("watch").set_defaults(fn=cmd_watch)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    sub.add_parser("logs").set_defaults(fn=cmd_logs)
    s = sub.add_parser("scrape"); s.add_argument("job"); s.set_defaults(fn=cmd_scrape)
    a = sub.add_parser("apply"); a.add_argument("job"); a.set_defaults(fn=cmd_apply)
    sub.add_parser("tailor").set_defaults(fn=cmd_tailor)
    sub.add_parser("telegram").set_defaults(fn=cmd_telegram)
    sub.add_parser("models").set_defaults(fn=cmd_models)
    sub.add_parser("login").set_defaults(fn=cmd_login)
    ap = sub.add_parser("atspw"); ap.add_argument("host"); ap.add_argument("password")
    ap.add_argument("email", nargs="?", default=""); ap.set_defaults(fn=cmd_atspw)
    ip = sub.add_parser("import-passwords"); ip.add_argument("csv"); ip.set_defaults(fn=cmd_import_passwords)
    sub.add_parser("inspect").set_defaults(fn=cmd_inspect)
    r = sub.add_parser("run"); r.add_argument("job"); r.set_defaults(fn=cmd_run)
    args = p.parse_args(); args.fn(args)


if __name__ == "__main__":
    main()
