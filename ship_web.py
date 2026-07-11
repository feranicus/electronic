#!/usr/bin/env python3
"""
ship_web.py -- ONE command to ship cybergod.ai end-to-end through GitHub CI/CD.
Run on your machine:   python ship_web.py

It automates every step so there are no manual clicks:
  1) release the domain from GitHub Pages (remove CNAME + disable Pages)   [webapp/unpublish_pages.py + gh]
  2) commit + push this repo  -> triggers .github/workflows/web-deploy.yml
  3) trigger + watch the workflow (build image -> GHCR -> deploy to droplet -> wire Caddy)  [gh]
  4) verify https://cybergod.ai/api/me returns 401 (up + auth working)

Requirements (one-time): the GitHub CLI `gh` installed and logged in (`gh auth login`).
Everything else -- build, push, deploy, TLS, Caddy -- happens in GitHub Actions on push.
See README.md / webapp/DEPLOY.md for the full picture.
"""
import os, sys, time, shutil, subprocess, ssl, urllib.request

HERE   = os.path.dirname(os.path.abspath(__file__))
OWNER  = "feranicus"
PAGES  = "feranicus/feranicus"     # the GitHub Pages repo that used to claim cybergod.ai
WORKFLOW = "web-deploy.yml"
DOMAIN = "cybergod.ai"

def sh(a, cap=False, check=False):
    print("  $ " + " ".join(a))
    r = subprocess.run(a, cwd=HERE, text=True,
                       capture_output=cap)
    if check and r.returncode != 0:
        sys.exit("[X] command failed: " + " ".join(a))
    return r

def need(tool, howto):
    if not shutil.which(tool):
        sys.exit(f"[X] '{tool}' not found. {howto}")

def gh_authed():
    return subprocess.run(["gh", "auth", "status"], capture_output=True).returncode == 0

def http_status(url):
    ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent":"ship"}),
                                    timeout=12, context=ctx) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:
        return "ERR(%s)" % type(e).__name__

def main():
    need("git", "Install Git.")
    need("gh", "Install GitHub CLI: https://cli.github.com  then run: gh auth login")
    if not gh_authed():
        sys.exit("[X] GitHub CLI not logged in. Run:  gh auth login   then re-run this script.")

    print("=== 1/4  release cybergod.ai from GitHub Pages ===")
    sh([sys.executable, os.path.join(HERE, "webapp", "unpublish_pages.py")])
    # best-effort: disable Pages entirely so GitHub stops answering for the domain
    sh(["gh", "api", "--method", "DELETE", f"/repos/{PAGES}/pages"], cap=True)

    print("\n=== 2/4  commit + push (triggers the workflow) ===")
    sh(["git", "add", "-A"])
    # commit only if there is something to commit
    if subprocess.run(["git","diff","--cached","--quiet"], cwd=HERE).returncode != 0:
        sh(["git", "commit", "-m", "ship: cybergod.ai web deploy via CI"])
    else:
        print("  (nothing new to commit)")
    sh(["git", "push", "origin", "main"], check=True)

    print("\n=== 3/4  trigger + watch the deploy workflow ===")
    sh(["gh", "workflow", "run", WORKFLOW, "--ref", "main"], cap=True)
    time.sleep(6)
    # get the most recent run id for this workflow and stream it
    r = sh(["gh", "run", "list", "--workflow", WORKFLOW, "--limit", "1",
            "--json", "databaseId,status", "--jq", ".[0].databaseId"], cap=True)
    run_id = (r.stdout or "").strip()
    if run_id:
        sh(["gh", "run", "watch", run_id, "--exit-status"])
    else:
        print("  (could not find the run id; check: gh run list --workflow " + WORKFLOW + ")")

    print("\n=== 4/4  verify ===")
    for _ in range(6):
        code = http_status(f"https://{DOMAIN}/api/me")
        print(f"  https://{DOMAIN}/api/me -> {code}   (401 = live + auth working)")
        if code == 401:
            print("\nDONE. https://%s/login is live." % DOMAIN); return
        time.sleep(10)
    print("\nWorkflow finished but the domain check isn't 401 yet.")
    print("Usually DNS/TLS propagation (~2-10 min) or the GHCR package needs one more minute.")
    print("Re-run `python ship_web.py` (it's idempotent) or check the Actions tab logs.")

if __name__ == "__main__":
    main()
