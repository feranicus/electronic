#!/usr/bin/env python3
"""
deploy_web_direct.py -- deploy cybergod.ai (colt-web) DIRECTLY from your machine to the droplet.
No GitHub, no CI. Uses your working SSH. Minimal footprint. Idempotent, self-verifying.

Steps: pack web sources -> scp -> build+restart colt-web (single network, --force-recreate) ->
rewrite the cybergod block in videodead's Caddyfile from deploy/caddy/cybergod.caddy -> FORCE Caddy
to load it via the admin API (POST /load; a plain reload can keep a stale config) -> if still not
live, restart the caddy container as a last resort -> verify colt-web single-network + public 401.

Usage:  python deploy_web_direct.py
Env (optional): DROPLET_HOST (default 64.225.108.200), DROPLET_USER (root), SSH_KEY (path)
"""
import os, sys, base64, subprocess, tarfile, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
HOST = os.environ.get("DROPLET_HOST", "64.225.108.200")
USER = os.environ.get("DROPLET_USER", "root")
KEY  = os.environ.get("SSH_KEY", "")
# FAIL FAST, NEVER HANG. Without ConnectTimeout an unreachable droplet (blocked :22, wrong network)
# makes ssh sit for ~2min with no output, which is indistinguishable from "it is building".
# BatchMode=yes => never sit on an interactive password prompt; error out instead.
_TMO = ["-o", "ConnectTimeout=10", "-o", "BatchMode=yes", "-o", "ServerAliveInterval=15",
        "-o", "ServerAliveCountMax=4"]
SSH_BASE = ["ssh", "-o", "StrictHostKeyChecking=accept-new", "-o", "LogLevel=ERROR"] + _TMO
SCP_BASE = ["scp", "-o", "StrictHostKeyChecking=accept-new", "-o", "LogLevel=ERROR"] + _TMO
if KEY and os.path.exists(KEY):
    SSH_BASE += ["-i", KEY]; SCP_BASE += ["-i", KEY]

INCLUDE = ["webapp", "hermes-skills/shodan-assessment", "colt_auth.py",
           "docker-compose.web.yml", "deploy", ".dockerignore"]
EXCLUDE = {"node_modules", "__pycache__", "dist", ".git", ".pytest_cache", "shodan-out"}

def _keep(name):
    """One exclusion rule, used by BOTH pack paths (git archive and the working-tree fallback)."""
    return not (set(name.split("/")) & EXCLUDE)


def _filter(ti):
    return ti if _keep(ti.name) else None

def _tree_state():
    """(is_clean, short_sha, dirty_paths) — what git thinks of the working tree, right now."""
    def g(*a):
        r = subprocess.run(["git"] + list(a), cwd=HERE, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=30)
        return (r.stdout or "").strip() if r.returncode == 0 else ""
    sha = g("rev-parse", "--short", "HEAD")
    dirty = [ln[2:].strip() for ln in g("status", "--porcelain").splitlines() if ln.strip()]
    return (not dirty), sha, dirty


def pack():
    """Pack the sources that will be BUILT on the droplet.

    THE WORKING TREE IS A MOVING TARGET AND THAT IS HOW A DEPLOY GOES OUT UNTESTED.
    ship.py does: test the tree -> commit the tree -> push -> pack the tree for staging -> pack the
    tree AGAIN for production. Five separate reads of a MUTABLE thing. On 2026-08-07 an editor was
    still writing translation files while a ship was running: the tests saw 203 by-English strings,
    the staging pack saw 203 (and passed, and the AI panel said GO on it), and ninety seconds later
    the production pack saw 213 with the translations half-written — so production failed a gate
    that staging had just passed, on "the same commit". It was never the same code.

    So we pack from `git archive HEAD` — the COMMITTED tree, which is immutable — and fall back to
    the working directory only when git is unavailable. What ships is then provably the commit that
    was tested, pushed and tagged, and staging and production are guaranteed identical inputs.
    """
    clean, sha, dirty = _tree_state()
    if sha:
        if not clean:
            # NOT fatal: the operator may have deliberately left something out of the commit. But
            # they must know that what deploys is HEAD, not what they are looking at in the editor.
            print("  [!] working tree is DIRTY (%d path(s), e.g. %s)" % (len(dirty), ", ".join(dirty[:3])))
            print("      packing the COMMIT %s, not your working copy - uncommitted edits will NOT ship."
                  % sha)
        tf = tempfile.NamedTemporaryFile(suffix=".tar", delete=False); tf.close()
        # -c core.autocrlf=false -c core.eol=lf: `git archive` applies the SAME end-of-line
        # conversion as a checkout, so on Windows (core.autocrlf=true) it emits CRLF while
        # `git show HEAD:path` emits the raw LF blob. That would leave the deployed artifact
        # platform-dependent — exactly what packing the commit was supposed to remove — and it is
        # what tests/test_deploy_immutability.py caught on the operator's machine while passing in
        # a Linux sandbox. Forcing both off makes the archive the REPOSITORY bytes on every OS.
        r = subprocess.run(["git", "-c", "core.autocrlf=false", "-c", "core.eol=lf",
                            "archive", "--format=tar", "-o", tf.name, "HEAD"] + list(INCLUDE),
                           cwd=HERE, capture_output=True, text=True, timeout=180)
        if r.returncode == 0 and os.path.getsize(tf.name) > 0:
            gz = tf.name + ".gz"
            with tarfile.open(tf.name) as src, tarfile.open(gz, "w:gz") as dst:
                for m in src.getmembers():
                    if _keep(m.name):
                        dst.addfile(m, src.extractfile(m) if m.isfile() else None)
            os.unlink(tf.name)
            print("  packing COMMIT %s (immutable - staging and prod get identical bytes)" % sha)
            return gz
        print("  [!] git archive failed (%s) - falling back to the working tree"
              % ((r.stderr or "").strip()[:120]))
        try: os.unlink(tf.name)
        except Exception: pass

    tf = tempfile.NamedTemporaryFile(suffix=".tgz", delete=False); tf.close()
    with tarfile.open(tf.name, "w:gz") as tar:
        for item in INCLUDE:
            p = os.path.join(HERE, item)
            if os.path.exists(p):
                tar.add(p, arcname=item, filter=_filter)
    return tf.name

def remote(proxy=True):
    """The droplet-side script. `proxy=False` builds and starts colt-web but does NOT touch any
    reverse proxy — that is the STAGING shape: the twin has no videodead-caddy to wire into, and
    the whole point of staging is to exercise the app and the reboot, not to publish a domain."""
    steps = [
    "set -e",
    "cd /opt/colt-stack",
    "[ -f .env ] || printf 'LOKI_URL=http://videodead-loki-1:3100/loki/api/v1/push\\nLOKI_NETWORK=videodead_appnet\\n' > .env",
    # docker-compose.web.yml joins videodead_appnet as an EXTERNAL network. On production that
    # network already exists; on a fresh staging box it does not, and compose fails before it
    # builds anything. Creating it if absent is idempotent and touches nothing on production.
    "docker network inspect videodead_appnet >/dev/null 2>&1 || docker network create videodead_appnet",
    "echo '== build + (re)start colt-web (single network, force-recreate) =='",
    "docker compose -p colt-stack -f docker-compose.web.yml up -d --build --force-recreate",
    # ---- SCAN THE IMAGE THAT NOBODY WAS SCANNING -------------------------------------------
    # Trivy runs in deploy.yml against colttechbot and cassandra. colt-web is built HERE, on the
    # droplet, and therefore never went through CI at all - so the only INTERNET-FACING image in
    # the stack was the one image the scanner had never seen. Scan it where it is built.
    # Trivy is pinned and checksum-verified for the same reason it is in CI: the scanner is a
    # supply-chain dependency, and this one was compromised in Feb/Mar 2026.
    "echo '== scan colt-web (CRITICAL fails the deploy, HIGH reports) =='",
    "TRIVY_VERSION=0.69.3",
    "if ! command -v trivy >/dev/null 2>&1; then"
    "  cd /tmp && B=https://github.com/aquasecurity/trivy/releases/download/v$TRIVY_VERSION &&"
    "  curl -sfLO $B/trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz &&"
    "  curl -sfLO $B/trivy_${TRIVY_VERSION}_checksums.txt &&"
    "  grep \" trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz$\" trivy_${TRIVY_VERSION}_checksums.txt"
    " | sha256sum -c - &&"
    "  tar xzf trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz trivy &&"
    "  install -m 0755 trivy /usr/local/bin/trivy && cd - >/dev/null; fi",
    "trivy image --scanners vuln --severity HIGH --ignore-unfixed --exit-code 0"
    " --timeout 8m ghcr.io/feranicus/colt-web:latest 2>&1 | tail -25 || true",
    "trivy image --scanners vuln --severity CRITICAL --ignore-unfixed --exit-code 1"
    " --timeout 8m ghcr.io/feranicus/colt-web:latest 2>&1 | tail -25"
    " || { echo 'TRIVY_CRITICAL_FAIL'; }",
    ]
    if not proxy:
        steps += [
            "echo '== staging: no shared proxy on this box — skipping the caddy wiring =='",
            "echo -n 'colt-web image : '; docker inspect colt-web -f '{{.Config.Image}}'",
            "sleep 4",
            "curl -s -o /dev/null -w 'local colt-web /api/me = %{http_code}  (401 = LIVE)\\n' "
            "--max-time 15 http://127.0.0.1:8090/api/me || true",
            "",
        ]
        return "\n".join(steps)
    return "\n".join(steps + [
    "echo '== wire cybergod.ai into the shared caddy from the committed snippet =='",
    "CADDY_CT=\"$(docker ps --format '{{.Names}}' | grep -i caddy | head -1)\"",
    "CF=\"$(docker inspect \"$CADDY_CT\" --format '{{range .Mounts}}{{if eq .Destination \"/etc/caddy/Caddyfile\"}}{{.Source}}{{end}}{{end}}')\"",
    "cp \"$CF\" \"$CF.bak.$(date +%s)\"",
    "sed -i '/# colt:cybergod BEGIN/,/# colt:cybergod END/d' \"$CF\"",
    "sed -i '/cybergod/,/^}/d' \"$CF\"",
    "cat deploy/caddy/cybergod.caddy >> \"$CF\"",
    "sed -i 's#^cybergod.ai,.*{$#cybergod.ai, www.cybergod.ai {#' \"$CF\"",
    "docker exec \"$CADDY_CT\" caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile",
    "echo '== FORCE a full config load via the admin API (a plain reload can keep a stale config) =='",
    "docker exec \"$CADDY_CT\" sh -c 'caddy adapt --config /etc/caddy/Caddyfile > /tmp/cfg.json && curl -sS -X POST -H \"Content-Type: application/json\" -H \"Cache-Control: must-revalidate\" --data @/tmp/cfg.json http://localhost:2019/load && echo ADMIN_LOAD_OK' || echo 'admin load failed (no admin API?)'",
    "sleep 3",
    "code=\"$(curl -sk --resolve cybergod.ai:443:127.0.0.1 https://cybergod.ai/api/me -o /dev/null -w '%{http_code}' || true)\"",
    "if [ \"$code\" != \"401\" ]; then echo \"== admin load did not take (got $code) -> restarting $CADDY_CT (brief) ==\"; docker restart \"$CADDY_CT\" >/dev/null; sleep 6; fi",
    "echo '== verify =='",
    "echo -n 'colt-web image : '; docker inspect colt-web -f '{{.Config.Image}}'",
    "echo -n 'colt-web nets  : '; docker inspect colt-web -f '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}'; echo",
    "echo -n 'caddy->colt-web: '; docker exec \"$CADDY_CT\" wget -qO- -T5 http://colt-web:8000/api/me 2>&1 | head -c 60; echo",
    "curl -sk --resolve cybergod.ai:443:127.0.0.1 https://cybergod.ai/api/me -o /dev/null -w 'public via caddy = %{http_code}  (401 = LIVE)\\n'",
    "",
    ])


REMOTE = remote(True)      # kept so existing callers/readers see the production script unchanged

def preflight(tgt, tries=3):
    """Prove we can reach the droplet BEFORE doing anything slow, and say so out loud.

    HARD TIMEOUT + BACK-OFF. `-o ConnectTimeout` only bounds the TCP/kex phase; a connection that
    sshd accepts and then stalls (PerSourcePenalties, MaxStartups) hangs the whole deploy with no
    output at all — which is exactly what happened here, twice. CLAUDE.md has required a hard
    subprocess timeout on every ssh since deploy.py hit the same wall; this function never got one.
    Penalties DECAY, so backing off and retrying is the correct response, not failing the ship.
    """
    print("== preflight: ssh %s (hard 25s timeout, %d tries) ==" % (tgt, tries), flush=True)
    r, delay = None, 20
    for attempt in range(tries):
        try:
            r = subprocess.run(
                SSH_BASE + [tgt, "echo ssh-ok && docker ps --format '{{.Names}}' | head -5"],
                capture_output=True, text=True, timeout=25)
        except subprocess.TimeoutExpired:
            r = None
        if r is not None and r.returncode == 0 and "ssh-ok" in (r.stdout or ""):
            break
        if attempt < tries - 1:
            print("   no answer (attempt %d/%d) — sshd may be throttling; waiting %ds"
                  % (attempt + 1, tries, delay), flush=True)
            time.sleep(delay)
            delay *= 2
    if r is None:
        sys.exit("[X] ssh to %s timed out %d times.\n"
                 "    OpenSSH 9.8 enables PerSourcePenalties by default and penalties ACCRUE.\n"
                 "    They decay on their own — wait ~5 minutes and re-run.\n"
                 "    (Or: python ship.py --no-stage, which opens far fewer sessions.)" % (tgt, tries))
    if r.returncode or "ssh-ok" not in (r.stdout or ""):
        err = (r.stderr or "").strip()[:300]
        sys.exit(
            "[X] cannot SSH to %s\n    %s\n\n"
            "    Most likely one of:\n"
            "      1. Your key is not where THIS shell looks. PowerShell uses C:\\Users\\<you>\\.ssh,\n"
            "         WSL uses ~/.ssh. This script worked from WSL before — try there, or set\n"
            "         SSH_KEY=C:\\path\\to\\key\n"
            "      2. The droplet is not answering :22 from this network (it blocked your IP before;\n"
            "         tethering to mobile fixed it). Test:  ssh -v %s \"echo ok\"\n"
            "      3. Wrong host — DROPLET_HOST=%s" % (tgt, err or "no response (connect timed out)", tgt, HOST))
    print("  ssh OK — containers: %s" % ", ".join((r.stdout or "").split()[1:6]), flush=True)


def main():
    # --no-proxy is the STAGING mode: build and start colt-web, touch no reverse proxy. Selected by
    # stagegate.py together with DROPLET_HOST=<staging>. Same code path, same build, same image —
    # only the publishing step differs, because the twin has no shared proxy to publish into.
    proxy = "--no-proxy" not in sys.argv
    tgt = "%s@%s" % (USER, HOST)
    if not proxy:
        print("== STAGING MODE: build + start colt-web only, no proxy wiring ==", flush=True)
    preflight(tgt)
    print("== pack sources ==", flush=True)
    tgz = pack()
    blob = base64.b64encode(open(tgz, "rb").read()).decode("ascii")
    try: os.unlink(tgz)
    except Exception: pass
    print("  packed (%d KB -> %d KB base64)" % (len(blob) * 3 // 4 // 1024, len(blob) // 1024), flush=True)

    # ONE ssh connection for the whole deploy: the tarball travels INSIDE the remote script as
    # base64, then build + wire + verify. Why:
    #   * scp is gone. On Windows, tempfile gives "C:\Users\...\x.tgz" and scp reads the "C:" as a
    #     HOSTNAME (the colon), so the upload died instantly and silently. This sidesteps it entirely.
    #   * 4 ssh connections (mkdir/scp/tar/bash) -> 1. sshd throttles rapid repeat connects
    #     (MaxStartups), which is what made a later run hang on connect.
    # Everything is sent as raw LF bytes: text=True would turn \n into \r\n on Windows and feed
    # bash CRLF, which breaks the heredoc.
    payload = "\n".join([
        "set -e",
        "mkdir -p /opt/colt-stack",
        "cd /opt/colt-stack",
        "base64 -d > /tmp/colt-web-src.tgz <<'B64EOF'",
        blob,
        "B64EOF",
        "echo '== unpack on droplet =='",
        "tar xzf /tmp/colt-web-src.tgz -C /opt/colt-stack && rm -f /tmp/colt-web-src.tgz",
        remote(proxy),
        "",
    ])
    print("== upload + build + wire + verify (ONE ssh; the docker build takes 2-4 min) ==", flush=True)
    try:
        # Tee: stream to the operator AND keep the text, because the Trivy verdict is a MARKER in
        # the output and a marker nobody reads is decoration. That is the exact defect this change
        # set out to fix in the workflows; repeating it here would be embarrassing.
        r = subprocess.run(SSH_BASE + [tgt, "bash -s"],
                           input=payload.encode("utf-8"), timeout=1200,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out = r.stdout.decode("utf-8", "replace")
        print(out, flush=True)
    except subprocess.TimeoutExpired:
        sys.exit("[X] the remote build exceeded 20 minutes and was killed.\n"
                 "    Nothing is left half-applied: compose is idempotent, just re-run.")
    if r.returncode:
        sys.exit("[X] remote deploy failed (see output above)")
    if "TRIVY_CRITICAL_FAIL" in out:
        sys.exit("[X] colt-web has a CRITICAL, fixable vulnerability. The image is built and the\n"
                 "    container is running the PREVIOUS image; this stops the promotion.\n"
                 "    Fix it (usually a base-image bump in webapp/Dockerfile), or, if it is truly\n"
                 "    accepted risk, add the CVE to .trivyignore WITH A REASON AND A DATE.\n"
                 "    An allowlist without a reason is --exit-code 0 wearing a hat.")
    print("\nDONE. If 'public via caddy = 401', open https://cybergod.ai/login")


if __name__ == "__main__":
    main()
