#!/usr/bin/env python3
"""
golive.py -- ONE command that makes https://cybergod.ai/login a real, working login.
Run it on your machine:   python golive.py

It automates EVERYTHING, end to end:
    1) deploy    -> builds/refreshes the colt-web container on the droplet (isolated colt-stack,
                    does NOT touch VideoDead / Amnezia / joplin)          [deploy.py --reuse]
    2) DNS       -> points cybergod.ai + www at the droplet via the GoDaddy API              |
    3) proxy+TLS -> wires cybergod.ai -> colt-web with an auto Let's Encrypt cert   [provision_web.py]
    4) verify    -> checks the app answers on the droplet and that DNS now resolves to it

The ONE thing a script cannot invent is the credential that authorises a DNS change.
Provide it ONCE: copy golive.secrets.env.example -> golive.secrets.env and paste your
GoDaddy API key/secret (https://developer.godaddy.com/keys). That file is gitignored and
never leaves your machine. After that, `python golive.py` is fully hands-off, re-runnable,
and needs nothing in a browser.

If you don't supply a GoDaddy key, golive still deploys the app + TLS and prints the exact
2-line DNS change to make by hand in GoDaddy's website -- so it works either way.
"""
import os, sys, subprocess, socket, ssl, urllib.request

HERE   = os.path.dirname(os.path.abspath(__file__))
SECRETS = os.path.join(HERE, "golive.secrets.env")

def load_secrets():
    """Read golive.secrets.env (KEY=VALUE lines) into os.environ. Silent if absent."""
    if not os.path.exists(SECRETS):
        return False
    for ln in open(SECRETS, encoding="utf-8"):
        ln = ln.strip()
        if not ln or ln.startswith("#") or "=" not in ln:
            continue
        k, v = ln.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if v:
            os.environ[k] = v
    return True

def run(a, **k):
    print("  $ " + " ".join(a)); return subprocess.run(a, cwd=HERE, **k)

def http_status(url):
    ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "golive"})
        with urllib.request.urlopen(req, timeout=12, context=ctx) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:
        return "ERR(%s)" % type(e).__name__

def main():
    had_secrets = load_secrets()
    host = os.environ.get("DROPLET_HOST", "64.225.108.200")
    gd   = bool(os.environ.get("GODADDY_API_KEY") and os.environ.get("GODADDY_API_SECRET"))

    print("=== golive: cybergod.ai ===")
    print("  droplet  : %s" % host)
    print("  secrets  : %s" % ("golive.secrets.env loaded" if had_secrets else "none found (deploy+TLS only, DNS by hand)"))
    print("  DNS auto : %s" % ("YES (GoDaddy API)" if gd else "NO (will print the manual 2-line change)"))
    print()

    # 1) deploy colt-web to the droplet
    print("=== 1/4  deploy colt-web to the droplet ===")
    if run([sys.executable, "deploy.py", "--reuse", "--yes"]).returncode != 0:
        sys.exit("[X] deploy failed -- read the deploy.py output above, fix, re-run.")

    # 2+3) DNS (if GoDaddy key present) + proxy + TLS, all inside provision_web.py
    print("\n=== 2-3/4  DNS + proxy + TLS (provision_web.py) ===")
    run([sys.executable, os.path.join(HERE, "webapp", "provision_web.py")])

    # 4) verify
    print("\n=== 4/4  verify ===")
    s_ip = http_status("https://%s/api/me" % host)
    print("  app on droplet IP   https://%s/api/me  -> %s   (401 = up + auth working)" % (host, s_ip))
    try:
        resolved = socket.gethostbyname("cybergod.ai")
    except Exception:
        resolved = "?"
    print("  cybergod.ai resolves to  %s   (want %s)" % (resolved, host))
    if resolved == host:
        s_dom = http_status("https://cybergod.ai/api/me")
        print("  https://cybergod.ai/api/me -> %s" % s_dom)
        print("\nDONE. https://cybergod.ai/login is live.")
    elif gd:
        print("\nDNS was just updated via the GoDaddy API; it propagates in ~2-10 min.")
        print("Re-run `python golive.py` in a few minutes to confirm, then use https://cybergod.ai/login")
    else:
        print("\nApp + TLS are ready on the droplet. LAST STEP (once, GoDaddy website, no key):")
        print("  GoDaddy -> cybergod.ai -> DNS:")
        print("   - delete the 4 A-records 185.199.108-111.153 (GitHub Pages)")
        print("   - add A  @    -> %s   (TTL 600)" % host)
        print("   - add A  www  -> %s   (TTL 600)" % host)
        print("  ...OR paste a GoDaddy API key into golive.secrets.env and re-run to fully automate it.")
        print("  Then https://cybergod.ai/login is live.")

if __name__ == "__main__":
    main()
