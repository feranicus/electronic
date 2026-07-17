#!/usr/bin/env python3
"""
enable_gmail_api.py — switch OTP delivery to the Gmail API (HTTPS/443), redeploy, and verify.
The droplet blocks outbound SMTP ports; the Gmail API goes over 443 (allowed).

Prereq (one-time Google setup):
  * service account JSON key with the Gmail API enabled
  * Workspace Admin -> Domain-Wide Delegation: the SA's numeric client_id + scope
    https://www.googleapis.com/auth/gmail.send
  * GMAIL_SENDER in the .env files = the Workspace user to send as (e.g. feranicus@s4biz.io)

Run (from C:\\Python SW\\Linkedin Scraper):
    python enable_gmail_api.py gmail_sa.json                # full: set env -> deploy -> live test
    python enable_gmail_api.py gmail_sa.json --test-only    # just re-run the live send test
Env: DROPLET_HOST, DROPLET_USER, SSH_KEY.
"""
import base64, json, os, subprocess, sys, tempfile

LOCAL   = os.path.dirname(os.path.abspath(__file__))
HOST    = os.environ.get("DROPLET_HOST", "64.225.108.200")
USER    = os.environ.get("DROPLET_USER", "root")
SSH_KEY = os.environ.get("SSH_KEY", "")
SSH_OPTS = (["-i", SSH_KEY] if SSH_KEY else []) + ["-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes", "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=4", "-o", "LogLevel=ERROR"]
ENVS = [os.path.join(LOCAL, "assess-bot", ".env"), os.path.join(LOCAL, "cassandra-bot", ".env")]

def set_env(path, key, value):
    lines = open(path, encoding="utf-8").read().splitlines()
    out, found = [], False
    for ln in lines:
        if ln.startswith(key + "="): out.append("%s=%s" % (key, value)); found = True
        else: out.append(ln)
    if not found: out.append("%s=%s" % (key, value))
    open(path, "w", encoding="utf-8").write("\n".join(out) + "\n")

def ssh(cmd, check=True):
    r = subprocess.run(["ssh", *SSH_OPTS, "%s@%s" % (USER, HOST), cmd])
    if check and r.returncode != 0: sys.exit("!! failed (%d)" % r.returncode)
    return r
def scp(local, remote):
    if subprocess.run(["scp", *SSH_OPTS, local, "%s@%s:%s" % (USER, HOST, remote)]).returncode != 0:
        sys.exit("!! scp failed")

# NOTE: pure ASCII on purpose (Windows default encoding mangles non-ASCII bytes).
TEST = (
    "import os, base64, json, requests\n"
    "from google.oauth2 import service_account\n"
    "from google.auth.transport.requests import Request\n"
    "from email.message import EmailMessage\n"
    "info = json.loads(base64.b64decode(os.environ['GMAIL_SA_B64']))\n"
    "sender = os.environ['GMAIL_SENDER']\n"
    "creds = service_account.Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/gmail.send'], subject=sender)\n"
    "creds.refresh(Request())\n"
    "m = EmailMessage(); m['Subject'] = 'Colt bot - Gmail API test'; m['From'] = sender; m['To'] = sender\n"
    "m.set_content('If you received this, OTP email over the Gmail API (HTTPS) works from the droplet.')\n"
    "raw = base64.urlsafe_b64encode(m.as_bytes()).decode()\n"
    "r = requests.post('https://gmail.googleapis.com/gmail/v1/users/%s/messages/send' % sender, headers={'Authorization': 'Bearer ' + creds.token}, json={'raw': raw}, timeout=20)\n"
    "print('SEND status:', r.status_code)\n"
    "print(('OK - check the ' + sender + ' inbox.') if r.status_code == 200 else ('ERROR: ' + r.text[:500]))\n"
)

def run_test():
    tf = os.path.join(tempfile.gettempdir(), "colt_gmail_test.py")
    open(tf, "w", encoding="utf-8", newline="\n").write(TEST)
    scp(tf, "/tmp/colt_gmail_test.py")
    ssh("docker cp /tmp/colt_gmail_test.py colt-cassandra:/tmp/colt_gmail_test.py && "
        "docker exec colt-cassandra python3 /tmp/colt_gmail_test.py", check=False)

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    test_only = "--test-only" in sys.argv
    if not args: sys.exit("Usage: python enable_gmail_api.py <service-account.json> [--test-only]")
    sa = args[0]; info = json.load(open(sa, encoding="utf-8"))
    for k in ("client_email", "private_key", "token_uri", "client_id"):
        if k not in info: sys.exit("!! %s is not a valid service-account key (missing %s)" % (sa, k))
    print("Service account: %s  (client_id %s)" % (info["client_email"], info["client_id"]))

    if not test_only:
        b64 = base64.b64encode(open(sa, "rb").read()).decode()
        print("\n=== writing GMAIL_SA_B64 into both .env files ===")
        for e in ENVS: set_env(e, "GMAIL_SA_B64", b64); print("  updated", e)
        print("\n=== redeploying (deploy.py --reuse) ===")
        if subprocess.run([sys.executable, os.path.join(LOCAL, "deploy.py"), "--reuse", "--yes"]).returncode != 0:
            sys.exit("!! deploy failed")

    print("\n=== live test: sending via the Gmail API from inside colt-cassandra ===")
    run_test()
    print("\nIf you see 'SEND status: 200', the OTP path is live. Then on Telegram:")
    print("  /auth <your colt email> <password>  -> you'll receive the code.")
    print("If 403/401 'unauthorized_client': domain-wide delegation not propagated yet — wait a few min, re-run with --test-only.")

if __name__ == "__main__":
    main()
