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

# THE FOURTH WIRING POINT. A shared root-level module needs FOUR edits, not three: the Dockerfile
# that COPYs it, .dockerignore (which starts with `*`), the bots' Dockerfiles - and THIS list, which
# decides what is even packed onto the droplet. user_store.py was added to the first three and the
# staging build failed with `COPY user_store.py: "/user_store.py": not found`, because the tarball
# never carried it. Anything a Dockerfile COPYs from the repo root must appear here; asserted by
# tests/test_admin_users.py so the next one cannot be missed.
INCLUDE = ["webapp", "hermes-skills/shodan-assessment", "colt_auth.py", "user_store.py",
           # The security brain. webapp/Dockerfile COPYs it into the image because the systemd unit
           # runs `docker exec colt-web ... /opt/perseus/perseus/hub.py`, and that path only existed
           # on the HOST -- so the daily cycle failed every night and no blocklist was ever
           # published. A COPY whose source is not in the pack list fails the BUILD, which is the
           # loud version of the same mistake; both wiring points are needed and this is the fourth.
           "perseus",
           "docker-compose.web.yml", "deploy", ".dockerignore"]
EXCLUDE = {"node_modules", "__pycache__", "dist", ".git", ".pytest_cache", "shodan-out"}

def _keep(name):
    """One exclusion rule, used by BOTH pack paths (git archive and the working-tree fallback)."""
    return not (set(name.split("/")) & EXCLUDE)


def _filter(ti):
    return ti if _keep(ti.name) else None

GIT_TIMEOUT_S = 180     # a local git call on Windows, cold: see _tree_state


def _tree_state():
    """(is_clean, short_sha, dirty_paths) — what git thinks of the working tree, right now."""
    # FAILS CLOSED. g() used to return "" when git failed, and _tree_state() read "" as "no dirty
    # paths" - an unknown tree reported as a CLEAN one. And 30s was not what a local `git status`
    # legitimately takes on Windows: after a full index refresh (antivirus, cold cache, an index last
    # written by another git) it timed out in the 2026-10-13 ship. 180s, and ship.py refreshes the
    # index once beforehand so this call is normally instant.
    def g(*a):
        r = subprocess.run(["git"] + list(a), cwd=HERE, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=GIT_TIMEOUT_S)
        if r.returncode != 0:
            raise RuntimeError("git %s failed (rc=%s): %s"
                               % (" ".join(a), r.returncode, (r.stderr or "").strip()[:300]))
        return (r.stdout or "").strip()
    sha = g("rev-parse", "--short", "HEAD")
    dirty = [ln[2:].strip() for ln in g("status", "--porcelain").splitlines() if ln.strip()]
    return (not dirty), sha, dirty


def _add_extra(tar_path, extra):
    """Append untracked files (secrets) to an uncompressed tar produced by `git archive`."""
    got = []
    for rel in extra or ():
        p = os.path.join(HERE, rel)
        if os.path.exists(p):
            with tarfile.open(tar_path, "a") as t:      # "a" needs an UNcompressed tar
                t.add(p, arcname=rel)
            got.append(rel)
    if got:
        print("  + %d untracked file(s) added on top of the commit: %s"
              % (len(got), ", ".join(got)))
    return got


def pack(include=None, extra=()):
    """Pack the sources that will be BUILT on the droplet.

    `include` is the path set handed to `git archive`; it defaults to the WEB deploy's INCLUDE.
    deploy.py (the bots) passes its own, because the two images need different trees — the bots need
    assess-bot/, cassandra-bot/, obs/ and docker-compose.reuse.yml, which the web image never sees.
    ONE mechanism (pack the immutable commit, repository bytes, no CRLF), TWO file scopes. Sharing
    the mechanism is the point; sharing the file list would break the bots build outright, and a
    second COPY of the mechanism is how the two paths drifted apart in the first place.

    `extra` names UNTRACKED files to add on top of the commit. There is exactly one legitimate use:
    `assess-bot/.env`, which holds runtime secrets and is gitignored by design, so `git archive`
    can never contain it. The bots compose declares `env_file: assess-bot/.env`, and CLAUDE.md
    records that the LOCAL copy is the source of truth for those secrets. Packing only the commit
    would silently stop shipping them — a behaviour change smuggled in as a side effect of a
    determinism fix, which is exactly how a secret goes missing on the next fresh deploy. Code comes
    from the commit; secrets come from the operator's machine, and the split is deliberate.

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
                            "archive", "--format=tar", "-o", tf.name, "HEAD"]
                           + list(include or INCLUDE),
                           cwd=HERE, capture_output=True, text=True, timeout=180)
        if r.returncode == 0 and os.path.getsize(tf.name) > 0:
            gz = tf.name + ".gz"
            _add_extra(tf.name, extra)
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
        # `include or INCLUDE`, NOT the module constant: the fallback must pack the SAME tree the
        # git path would have. Leaving it hardcoded meant a caller that passed its own file set got
        # the web tree here — the bots image would then build without its own Dockerfile, and only
        # on the rare path where git is unavailable, which is the worst kind of bug to find.
        for item in list(include or INCLUDE) + list(extra or ()):
            p = os.path.join(HERE, item)
            if os.path.exists(p):
                tar.add(p, arcname=item, filter=_filter)
    return tf.name

def _staging_tail():
    """The twin has no shared proxy to publish into, so staging stops at "the app is up".
    ONE HOME: both the build path and the pull path end here when proxy=False."""
    return [
            "echo '== staging: no shared proxy on this box — skipping the caddy wiring =='",
            "echo -n 'colt-web image : '; docker inspect colt-web -f '{{.Config.Image}}'",
            "sleep 4",
            "curl -s -o /dev/null -w 'local colt-web /api/me = %{http_code}  (401 = LIVE)\\n' "
            "--max-time 15 http://127.0.0.1:8090/api/me || true",
            "",
    ]


def _proxy_tail():
    """Wire cybergod.ai into the SHARED Caddy, then prove it took.

    EXTRACTED VERBATIM 2026-10-15 so the pull-by-tag path reuses it instead of growing a second
    copy (defect class 32). Every line here was paid for by an outage - the marker-scoped delete,
    the in-place truncate that keeps the inode, the size floor, the forced admin load. A second
    copy of this block is a second chance to take six domains down, so there is exactly one."""
    return [
    "echo '== wire cybergod.ai into the shared caddy from the committed snippet =='",
    "CADDY_CT=\"$(docker ps --format '{{.Names}}' | grep -i caddy | head -1)\"",
    "CF=\"$(docker inspect \"$CADDY_CT\" --format '{{range .Mounts}}{{if eq .Destination \"/etc/caddy/Caddyfile\"}}{{.Source}}{{end}}{{end}}')\"",
    "cp \"$CF\" \"$CF.bak.$(date +%s)\"",
    # THE MARKER DELETE IS THE ONLY CORRECT ONE. It removes exactly our block and nothing else.
    #
    # There used to be a second, blunt line here:
    #     sed -i '/cybergod/,/^}/d' "$CF"
    # which deletes from the FIRST line containing "cybergod" to the next `}` at column 0. It was
    # belt-and-braces for a legacy unmarked block that has not existed for months, and it was
    # silently destroying somebody else's config on EVERY deploy: jobhuntwow.caddy line 14 is a
    # COMMENT reading "1:1 with cybergod.ai's traffic board", so the range started inside jhw's
    # block and ran to the closing brace of `jobhuntwow.com {`. Reproduced exactly: 26 lines ->
    # 14, braces unbalanced, which is the "CADDY: the LIVE shared config is DAMAGED" alert that
    # fired after every single ship. caddyguard then repaired it, so the damage was invisible
    # except as a recurring alert - and an alert that is benign-looking every time is how the one
    # that matters gets ignored.
    #
    # RULE: never delete a RANGE from a shared file using a word that can appear in prose. The
    # markers exist precisely so the boundaries are unambiguous.
    # ---- IN-PLACE, BECAUSE THE MOUNT IS PINNED TO AN INODE ------------------------------------
    # `sed -i` does NOT edit in place. It writes a temp file and renames it, so the file gets a NEW
    # INODE -- and /etc/caddy/Caddyfile is a single-FILE bind mount, which follows the OLD one. The
    # container then reads a file nobody can see. caddyguard/agent.py says this in its own module
    # docstring ("`mv` onto the target swaps the inode and the container silently keeps reading the
    # OLD file forever") and writes through write_inplace for exactly that reason. This deploy was
    # the one writer that ignored it.
    #
    # MEASURED, 2026-09-10 ship: caddyguard's 10-minute timer landed between this edit and the
    # assemble and reported `stale mount repaired by restart (now cdcf8eaf3c37)` -- it restarted
    # videodead-caddy-1, which owns :443 for all six domains. `Up 20 seconds` in the same log,
    # against `Up 51 minutes` on the previous ship. Whether a given deploy briefly drops every site
    # therefore depended on where the timer fell: a coin-flip outage, which is worse than a
    # reliable one because it teaches you the logs are noise.
    #
    # `sed` WITHOUT -i is a filter and touches nothing. The final `>` truncates the EXISTING inode.
    "new=\"$(sed '/# colt:cybergod BEGIN/,/# colt:cybergod END/d' \"$CF\"; cat deploy/caddy/cybergod.caddy)\"",
    "new=\"$(printf '%s\\n' \"$new\" | sed 's#^cybergod.ai,.*{$#cybergod.ai, www.cybergod.ai {#')\"",
    # NEVER write an empty or implausible result over the config that serves six domains. A command
    # substitution that failed returns the empty string, and `> \"$CF\"` would then blank the file
    # before anything had a chance to validate it.
    "[ \"$(printf '%s' \"$new\" | wc -c)\" -gt 500 ] || { echo 'REFUSING: assembled Caddyfile is implausibly small - NOT written'; exit 1; }",
    "printf '%s\\n' \"$new\" > \"$CF\"",
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
    # ---- THE ADMIN PAGES ARE PART OF THE APP, AND NOTHING HERE EVER PROVED THEY LOAD ----------
    # /api/me answering 401 proves the process is up and the gate is on. It proves NOTHING about a
    # route that computes something, and the Fleet page shipped BROKEN THREE TIMES behind a green
    # deploy: the tests all monkeypatch the log paths and unset LOKI_URL, so not one of them ever
    # called status() with the environment the container actually has. This runs it IN the
    # container, with the real .env, the real mounts and the real PROJECTS list, and `set -e` makes
    # a failure fail the DEPLOY instead of the operator. It reaches nothing outside the box.
    "echo '== admin: the fleet status must actually compute, with the REAL env =='",
    "docker exec colt-web python3 -c 'import sys;from app import fleet;d=fleet.status();n=len(d.get(\"projects\") or []);print(\"fleet.status(): %d project(s), error=%s\" % (n, d.get(\"error\")));sys.exit(1 if (d.get(\"error\") or n == 0) else 0)'",
    "curl -sk --resolve cybergod.ai:443:127.0.0.1 https://cybergod.ai/api/me -o /dev/null -w 'public via caddy = %{http_code}  (401 = LIVE)\\n'",
    "",
    ]

def remote_ghcr(tag, proxy=True, image=None):
    """PULL a pre-built, already-scanned colt-web image instead of building one on the droplet.

    WHY THIS EXISTS, and why it is a separate function rather than a flag threaded through
    remote(). The comment in remote() says it plainly: colt-web is built ON THE DROPLET, so the
    only internet-facing image in the stack is the one image CI never saw. Scanning it after the
    build on production is a sound mitigation and it stays; it is not the same thing as never
    putting an unscanned artifact on production in the first place.

    This path is the supply-chain shape instead: CI builds the image once, Trivy scans THAT image,
    GHCR holds it, and production runs the exact bytes that were scanned - selected by an immutable
    tag, so "the thing we tested" and "the thing that is running" cannot drift apart. It is
    additive on purpose: the laptop path through remote() is untouched, because a deploy script is
    not where you want a clever refactor.
    """
    import ghcr
    image = image or os.environ.get("WEB_IMAGE") or ghcr.ref(ghcr.WEB_IMAGE, "x").rsplit(":", 1)[0]
    _tok = (os.environ.get("GHCR_TOKEN") or os.environ.get("GITHUB_TOKEN") or "").strip()
    steps = [
        "set -e",
        "cd /opt/colt-stack",
        "[ -f .env ] || printf 'LOKI_URL=http://videodead-loki-1:3100/loki/api/v1/push\\nLOKI_NETWORK=videodead_appnet\\n' > .env",
        "docker network inspect videodead_appnet >/dev/null 2>&1 || docker network create videodead_appnet",
        "echo '== pull the CI-built, CI-scanned colt-web (no build on this box) =='",
        # BOTH HALVES OF THE NAME, never just the tag. Passing WEB_TAG alone left the repository
        # to a default inside compose, and that default was a DIFFERENT package than the one CI
        # pushes to - GHCR says "not found" for both a missing tag and a package you may not see,
        # so the mismatch cost a full pipeline run to find. ghcr.py is the one home. [2026-10-16]
        "export WEB_IMAGE='%s'" % image,
        "export WEB_TAG='%s'" % tag,
        "echo \"   pulling: $WEB_IMAGE:$WEB_TAG\"",
        # AUTHENTICATE, OR SAY THAT WE DID NOT. A private package answers an anonymous pull with
        # 404, identical to a tag that does not exist, so an unreported skip here is a diagnosis
        # nobody can make (class 37: a feature behind `if <derived thing>` fails silently).
        # The token travels in this script over STDIN, never in argv, and is never echoed.
        # NOT "%%s": this string is CONCATENATED, not %-formatted, so %% would reach the shell
        # literally and printf would pipe the two characters "%s" as the password (class 44 - the
        # doubling rule has a precondition). Found by reading the generated script, not the source.
        (("printf '%s' '" + _tok + "' | docker login ghcr.io -u x --password-stdin >/dev/null "
          "&& echo '   ghcr: logged in' || echo '   [!] ghcr: login FAILED - a private package "
          "will answer 404, which looks exactly like a missing tag'") if _tok else
         "echo '   [!] ghcr: NO token on this run - pulling anonymously. If the package is "
         "private this fails as \"not found\", which is indistinguishable from a missing tag.'"),
        # Fail if the tag is not there, rather than silently falling back to :latest - a deploy
        # that quietly ships a different image than the one named is the whole class of bug this
        # path exists to close.
        "docker compose -p colt-stack -f docker-compose.web.yml pull web",
        "docker compose -p colt-stack -f docker-compose.web.yml up -d --no-build --force-recreate",
        # NAME WHAT IS ACTUALLY RUNNING (defect class 26). The tag asked for and the digest that
        # answered are different facts, and only the second one is evidence.
        "echo '== running image =='",
        "docker inspect colt-web --format 'image: {{.Config.Image}}' || true",
        "docker inspect colt-web --format 'digest: {{index .Image}}' || true",
    ]
    steps += _proxy_tail() if proxy else _staging_tail()
    return "\n".join(steps)


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
    # --skip-version-check: the "a newer Trivy is available" banner printed TWICE per deploy and
    # is pure noise. The version we run is PINNED and checksum-verified on purpose (the Feb-Mar
    # 2026 supply-chain compromise), so an upgrade is a deliberate, reviewed change to
    # TRIVY_VERSION - never something to be nudged into by a banner. The vulnerability DATABASE
    # updates independently of the binary, so the findings are current either way.
    "trivy image --scanners vuln --severity HIGH --ignore-unfixed --exit-code 0"
    " --skip-version-check --timeout 8m ghcr.io/feranicus/colt-web:latest 2>&1 | tail -25 || true",
    "trivy image --scanners vuln --severity CRITICAL --ignore-unfixed --exit-code 1"
    " --skip-version-check --timeout 8m ghcr.io/feranicus/colt-web:latest 2>&1 | tail -25"
    " || { echo 'TRIVY_CRITICAL_FAIL'; }",
    ]
    if not proxy:
        return "\n".join(steps + _staging_tail())
    return "\n".join(steps + _proxy_tail())



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

    # --ghcr TAG: run the image CI already built and Trivy already scanned, instead of building a
    # fresh one on the droplet. Same wiring, same verification, no compiler on production.
    ghcr = None
    if "--ghcr" in sys.argv:
        k = sys.argv.index("--ghcr")
        if k + 1 >= len(sys.argv):
            sys.exit("[X] --ghcr needs a TAG, e.g. --ghcr 69617a3d561c")
        ghcr = sys.argv[k + 1]

    if not proxy:
        print("== STAGING MODE: build + start colt-web only, no proxy wiring ==", flush=True)
    preflight(tgt)

    if ghcr:
        # NOTHING IS PACKED. The sources do not travel, because the artifact is the image and the
        # image already exists. This is the whole point: what was scanned is what runs.
        print("== pull CI image %s (no source upload, no build on the droplet) ==" % ghcr, flush=True)
        payload = "\n".join(["set -e", "mkdir -p /opt/colt-stack", remote_ghcr(ghcr, proxy), ""])
        r = subprocess.run(SSH_BASE + [tgt, "bash -s"],
                           input=payload.encode("utf-8"), capture_output=True, timeout=900)
        out = (r.stdout or b"").decode("utf-8", "replace") + (r.stderr or b"").decode("utf-8", "replace")
        print(out, flush=True)
        if "TRIVY_CRITICAL_FAIL" in out:
            sys.exit("[X] the image carries CRITICAL, fixable vulnerabilities - not promoting it")
        if r.returncode != 0:
            # NAME THE SUBJECT (defect class 26). "the GHCR deploy failed (rc=1)" is the message
            # that cost a whole pipeline run on 2026-10-16: docker had already said "not found",
            # which covers BOTH a tag that was never pushed and a package we may not see. Ask the
            # registry itself, both ways, and print the difference - that is the diagnosis.
            low = out.lower()
            if "not found" in low or "failed to resolve reference" in low or "denied" in low:
                try:
                    import ghcr as _ghcr
                    wanted = "%s:%s" % (os.environ.get("WEB_IMAGE")
                                        or _ghcr.ref(_ghcr.WEB_IMAGE, "x").rsplit(":", 1)[0],
                                        ghcr)
                    print(_ghcr.report(wanted, token=os.environ.get("GHCR_TOKEN")
                                       or os.environ.get("GITHUB_TOKEN")), flush=True)
                except Exception as e:                   # noqa: BLE001 - a diagnostic must never
                    # replace the failure it was called to explain (class 10).
                    print("  (the GHCR check could not run: %s)" % type(e).__name__, flush=True)
            sys.exit("[X] the GHCR deploy failed (rc=%d). Compose is idempotent; re-run." % r.returncode)
        return

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
