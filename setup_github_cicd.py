#!/usr/bin/env python3
"""
setup_github_cicd.py — one-shot CI/CD wiring for the DigitalOcean deploy.

Does EVERYTHING:
  1) generates a passphrase-less deploy key (if missing),
  2) authorizes its public half on the droplet (~/.ssh/authorized_keys),
  3) sets GitHub Actions secrets DROPLET_SSH_KEY / DROPLET_HOST / DROPLET_USER (gh encrypts them),
  4) GUARDRAILS: branch protection on main (require the CI check) + a 'production' environment
     that requires YOU to approve each deploy.

Prereqs (one time):
  * GitHub CLI:  winget install GitHub.cli   (or https://cli.github.com)
  * gh auth login   (grant 'repo' scope; you must be admin of the repo)

Run:
  python setup_github_cicd.py
  python setup_github_cicd.py --repo feranicus/electronic --host 64.225.108.200 --user root
Flags: --no-droplet  --no-guardrails  --check quality-and-secrets
"""
import argparse, json, os, shutil, subprocess, sys

def run(cmd, check=True, capture=False, inp=None, quiet=False):
    if not quiet: print("  $ " + " ".join(cmd))
    r = subprocess.run(cmd, text=True, input=inp,
                       stdout=(subprocess.PIPE if capture else None),
                       stderr=(subprocess.STDOUT if capture else None))
    if check and r.returncode != 0:
        if capture and r.stdout: print(r.stdout)
        sys.exit("!! command failed: " + " ".join(cmd))
    return r

def gh_api(method, path, body=None):
    cmd = ["gh", "api", "--method", method, path, "-H", "Accept: application/vnd.github+json"]
    if body is not None:
        cmd += ["--input", "-"]
        r = subprocess.run(cmd, text=True, input=json.dumps(body), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    else:
        r = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return r.returncode, (r.stdout or "")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("REPO", "feranicus/electronic"))
    ap.add_argument("--host", default=os.environ.get("DROPLET_HOST", "64.225.108.200"))
    ap.add_argument("--user", default=os.environ.get("DROPLET_USER", "root"))
    ap.add_argument("--key",  default=os.path.join(os.path.expanduser("~"), ".ssh", "colt_deploy"))
    ap.add_argument("--check", default="quality-and-secrets", help="required CI job/check name")
    ap.add_argument("--no-droplet", action="store_true")
    ap.add_argument("--no-guardrails", action="store_true")
    a = ap.parse_args()

    if not shutil.which("gh"):
        sys.exit("!! GitHub CLI 'gh' not found.\n   Install:  winget install GitHub.cli\n   Then:     gh auth login")
    if run(["gh", "auth", "status"], check=False, capture=True, quiet=True).returncode != 0:
        sys.exit("!! Not authenticated. Run:  gh auth login   (grant repo scope)")

    # --- 1) deploy key ---
    priv, pub = a.key, a.key + ".pub"
    if not os.path.exists(priv):
        print("=== generating passphrase-less deploy key ==="); run(["ssh-keygen","-t","ed25519","-f",priv,"-N","","-C","gh-actions-deploy"])
    else:
        print("deploy key already exists:", priv)

    # --- 2) authorize on droplet ---
    if not a.no_droplet:
        print("=== authorizing the deploy key on the droplet (idempotent) ===")
        pk = open(pub, encoding="utf-8").read().strip()
        remote = ("mkdir -p ~/.ssh && chmod 700 ~/.ssh && touch ~/.ssh/authorized_keys && "
                  "grep -qxF '%s' ~/.ssh/authorized_keys || echo '%s' >> ~/.ssh/authorized_keys && echo AUTHORIZED" % (pk, pk))
        run(["ssh","-o","StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes", "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=4","%s@%s" % (a.user,a.host), remote])

    # --- 3) secrets ---
    print("=== setting GitHub Actions secrets on %s (encrypted by gh) ===" % a.repo)
    run(["gh","secret","set","DROPLET_SSH_KEY","--repo",a.repo], inp=open(priv,encoding="utf-8").read())
    run(["gh","secret","set","DROPLET_HOST","--repo",a.repo,"--body",a.host])
    run(["gh","secret","set","DROPLET_USER","--repo",a.repo,"--body",a.user])
    run(["gh","secret","list","--repo",a.repo], check=False)

    # --- 4) guardrails ---
    if not a.no_guardrails:
        print("\n=== guardrails: production environment (required reviewer) ===")
        who = subprocess.run(["gh","api","user","--jq",".id"], text=True, capture_output=True)
        out = (who.stdout or "").strip()
        uid = int(out) if out.isdigit() else None
        env_body = {"wait_timer":0,"prevent_self_review":False,
                    "reviewers":([{"type":"User","id":uid}] if uid else []),
                    "deployment_branch_policy":None}
        rc, o = gh_api("PUT","/repos/%s/environments/production" % a.repo, env_body)
        if rc==0: print("  ✓ 'production' environment set — deploys need one approval click.")
        else: print("  ! environment reviewers need a PUBLIC repo (or a paid plan for private). Response:\n   ", o[:300])

        print("\n=== guardrails: branch protection on main (require CI: %s) ===" % a.check)
        prot = {"required_status_checks":{"strict":True,"contexts":[a.check]},
                "enforce_admins":False,"required_pull_request_reviews":None,"restrictions":None}
        rc, o = gh_api("PUT","/repos/%s/branches/main/protection" % a.repo, prot)
        if rc==0: print("  ✓ main protected — the CI check must pass.")
        else: print("  ! branch protection needs a PUBLIC repo (or paid plan). Push once so the check exists, then re-run. Response:\n   ", o[:300])

    print("\nDONE. Push to main → CI runs → Deploy waits for your approval → ships to the droplet.")
    print("Manual deploy:  gh workflow run \"Deploy to DigitalOcean droplet\" --repo %s" % a.repo)

if __name__ == "__main__":
    main()
