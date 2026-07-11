#!/usr/bin/env python3
"""
publish_landing.py -- put the animated landing live on cybergod.ai RIGHT NOW.
No new API key, no DNS change, no droplet. cybergod.ai already serves GitHub Pages
(feranicus.github.io) -- this just replaces that stale page with the new one.

It also fixes the /login 404: because cybergod.ai is STATIC GitHub Pages, /login is
not a file and can't run the React app (that lives on the droplet). So when PORTAL_URL
is set (the droplet's public portal address, e.g. the Tailscale Funnel URL the deploy
prints, or https://app.cybergod.ai), this writes a tiny redirect at /login that bounces
the browser to the real portal. Then the landing's "Log in" buttons work.

Usage:  PORTAL_URL="https://<node>.ts.net" python publish_landing.py
Env (optional): PAGES_REPO (default https://github.com/feranicus/feranicus.git),
                PAGES_BRANCH (main), PORTAL_URL (droplet portal base URL)
"""
import os, subprocess, tempfile, shutil, sys
HERE   = os.path.dirname(os.path.abspath(__file__))
REPO   = os.environ.get("PAGES_REPO", "https://github.com/feranicus/feranicus.git")
BRANCH = os.environ.get("PAGES_BRANCH", "main")
SRC    = os.path.join(HERE, "colt_platform_architecture.html")
PORTAL = os.environ.get("PORTAL_URL", "").rstrip("/")

REDIRECT = (
    '<!doctype html><html><head><meta charset="utf-8">\n'
    '<title>Redirecting to the Colt portal...</title>\n'
    '<meta name="robots" content="noindex">\n'
    '<meta http-equiv="refresh" content="0;url=%(u)s/login">\n'
    '<link rel="canonical" href="%(u)s/login">\n'
    '<script>location.replace("%(u)s/login");</script>\n'
    '<style>body{font:16px/1.6 system-ui;background:#0a1526;color:#eaf1fb;'
    'display:grid;place-items:center;height:100vh;margin:0}a{color:#00B2A9}</style>\n'
    '</head><body><p>Taking you to the Colt portal... '
    '<a href="%(u)s/login">continue &#8594;</a></p></body></html>\n'
)

def run(a, **k):
    print("  $ " + " ".join(a)); return subprocess.run(a, **k)

def main():
    if not os.path.exists(SRC): sys.exit("[X] landing not found: " + SRC)
    tmp = tempfile.mkdtemp(prefix="pages-")
    if run(["git", "clone", "--depth", "1", "-b", BRANCH, REPO, tmp]).returncode != 0:
        sys.exit("[X] clone failed -- check the repo/branch or your git auth")

    shutil.copy(SRC, os.path.join(tmp, "index.html"))
    cn = os.path.join(tmp, "CNAME")
    if not os.path.exists(cn): open(cn, "w").write("cybergod.ai\n")
    add = ["index.html", "CNAME"]

    if PORTAL:
        os.makedirs(os.path.join(tmp, "login"), exist_ok=True)
        html = REDIRECT % {"u": PORTAL}
        open(os.path.join(tmp, "login", "index.html"), "w", encoding="utf-8").write(html)
        open(os.path.join(tmp, "404.html"), "w", encoding="utf-8").write(html)
        add += ["login/index.html", "404.html"]
        print("  [login] cybergod.ai/login -> %s/login" % PORTAL)
    else:
        print("  [login] PORTAL_URL not set -- /login will still 404 on Pages.")
        print("          Set PORTAL_URL to the droplet portal (the deploy prints it, e.g.")
        print("          https://<node>.ts.net) and re-run, and /login will redirect there.")

    run(["git", "-C", tmp, "add"] + add)
    if run(["git", "-C", tmp, "commit", "-m", "cybergod.ai: publish landing + /login redirect"]).returncode != 0:
        print("  (no change to publish)"); return
    if run(["git", "-C", tmp, "push", "origin", BRANCH]).returncode != 0:
        sys.exit("[X] push failed -- check git auth for " + REPO)
    print("\nDONE. cybergod.ai refreshes in ~1 min (GitHub Pages rebuild).")
    if PORTAL: print("      Login button now reaches the portal at %s/login" % PORTAL)

if __name__ == "__main__":
    main()
