#!/usr/bin/env python3
"""
caddyguard agent — runs ON THE DROPLET. Makes the shared Caddyfile un-breakable.

    caddyguard migrate            split the live monolith into per-project fragments
    caddyguard write NAME FILE    replace ONE project's fragment, validate, apply, rollback on fail
    caddyguard assemble --apply   rebuild the monolith from fragments, validate, apply
    caddyguard restore NAME       recover one project's fragment from the newest good backup
    caddyguard check [--heal]     validate the LIVE file; alert; optionally self-heal
    caddyguard show               what the guard currently knows

WHY (the 2026-08-07 outage)
---------------------------
Four projects (colt, polara/klima, jhw, jev) each append a MARKED block into ONE shared file,
/opt/videodead/Caddyfile. On 2026-08-06 16:15:56 UTC a deploy truncated jobhuntwow's block —
directives and closing brace gone. Nothing noticed, because **Caddy reads its config only at
start**: the running process served from memory for 12 hours. Patchwatch's kernel upgrade rebooted
the box at 04:22:42; Caddy re-read the file, rejected it, and every domain died together.

Three properties fix that class of failure, and this file implements all three:
  1. ISOLATION  — a project may only ever write its OWN fragment. The monolith is GENERATED.
                  One project can no longer delete another's bytes, because it never touches them.
  2. WRITE-TIME VALIDATION — nothing reaches the live file until `caddy validate` accepts it, using
                  the running container's OWN image AND environment (line 3 uses an env placeholder;
                  validating without the env produces a phantom error — that cost us a whole cycle).
  3. RUNTIME DETECTION — `check` runs on a timer against the LIVE file, so latent damage is found
                  in minutes instead of at the next reboot.

WHY NOT conf.d + import: the container bind-mounts a single FILE (/opt/videodead/Caddyfile ->
/etc/caddy/Caddyfile). An import directory would need a new mount, i.e. editing videodead's compose
and RECREATING the shared proxy — a deliberate outage of every site to fix an outage. The fragment
+ assembler design gives the same isolation guarantee with no mount change.

IN-PLACE WRITES ONLY. The mount is a single file, so the container is bound to its INODE. `mv` onto
the target swaps the inode and the container silently keeps reading the OLD file forever. Every
write here is truncate-and-write (`open(...,"w")`), which preserves the inode.
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request

LIVE = os.environ.get("CADDYFILE", "/opt/videodead/Caddyfile")
ROOT = "/opt/caddyguard"
FRAG = os.path.join(ROOT, "blocks")
BAKD = os.path.join(ROOT, "backups")
STATE = os.path.join(ROOT, "state.json")
ENVF = "/opt/colt-stack/assess-bot/.env"

BEGIN = re.compile(r"^#\s*([A-Za-z0-9_.:-]+)\s+BEGIN\b")
END = re.compile(r"^#\s*([A-Za-z0-9_.:-]+)\s+END\b")


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", **kw)


# ---------------------------------------------------------------- container facts
def container():
    r = sh(["docker", "ps", "-a", "--format", "{{.Names}}"])
    for n in (r.stdout or "").split():
        if "caddy" in n.lower():
            return n
    return ""


def image_and_env(c):
    img = sh(["docker", "inspect", "-f", "{{.Config.Image}}", c]).stdout.strip() or "caddy:2-alpine"
    env = sh(["docker", "inspect", "-f", "{{range .Config.Env}}{{println .}}{{end}}", c]).stdout
    args = []
    for e in env.splitlines():
        e = e.strip()
        if "=" in e and not e.startswith(("PATH=", "HOME=", "HOSTNAME=")):
            args += ["-e", e]
    return img, args


# ---------------------------------------------------------------- structural checks
def balance(text):
    code = "\n".join(l.split("#")[0] for l in text.split("\n"))
    return code.count("{"), code.count("}")


def markers(text):
    """{name: (begin_idx, end_idx)} plus a list of structural complaints."""
    lines, open_at, spans, bad = text.split("\n"), {}, {}, []
    for i, ln in enumerate(lines):
        mb, me = BEGIN.match(ln.strip()), END.match(ln.strip())
        if mb:
            if mb.group(1) in open_at:
                bad.append("duplicate BEGIN for %s at line %d" % (mb.group(1), i + 1))
            open_at[mb.group(1)] = i
        elif me:
            n = me.group(1)
            if n not in open_at:
                bad.append("END without BEGIN for %s at line %d" % (n, i + 1))
            else:
                spans[n] = (open_at.pop(n), i)
    for n, i in open_at.items():
        bad.append("BEGIN without END for %s at line %d" % (n, i + 1))
    return spans, bad


def structural(text):
    """Cheap, dependency-free checks. Catch the 2026-08-07 defect without starting a container."""
    problems = []
    o, c = balance(text)
    if o != c:
        problems.append("brace imbalance: open=%d close=%d" % (o, c))
    _, bad = markers(text)
    problems += bad
    return problems


def validate(text, c=None):
    """caddy validate, in the container's OWN image AND environment. (ok, message)"""
    c = c or container()
    if not c:
        return False, "no caddy container found"
    img, envargs = image_and_env(c)
    d = "/tmp/_cgval"
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "Caddyfile"), "w", encoding="utf-8") as fh:
        fh.write(text)
    r = sh(["docker", "run", "--rm", "-v", "%s:/etc/caddy:ro" % d] + envargs +
           [img, "caddy", "validate", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"])
    return r.returncode == 0, ((r.stdout or "") + (r.stderr or "")).strip()[-500:]


def acceptable(text, c=None):
    probs = structural(text)
    if probs:
        return False, "; ".join(probs)
    return validate(text, c)


# ---------------------------------------------------------------- fragments
def read(p):
    return open(p, encoding="utf-8", errors="replace").read() if os.path.exists(p) else ""


def write_inplace(p, text):
    # truncate-and-write: preserves the inode, which a single-file bind mount depends on.
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)


def split(text):
    """(base_text, {name: block_text}) — base is everything outside any marker pair."""
    lines = text.split("\n")
    spans, _ = markers(text)
    owned = set()
    frags = {}
    for n, (a, b) in spans.items():
        frags[n] = "\n".join(lines[a:b + 1])
        owned |= set(range(a, b + 1))
    base = "\n".join(l for i, l in enumerate(lines) if i not in owned)
    return base.rstrip() + "\n", frags


def assemble():
    base = read(os.path.join(FRAG, "_base.caddy"))
    out = [base.rstrip()]
    for n in sorted(os.listdir(FRAG)) if os.path.isdir(FRAG) else []:
        if n.startswith("_") or not n.endswith(".caddy"):
            continue
        out.append(read(os.path.join(FRAG, n)).rstrip())
    return "\n\n".join(x for x in out if x.strip()) + "\n"


def name_to_file(n):
    return os.path.join(FRAG, n.replace(":", "__") + ".caddy")


def file_to_name(f):
    return os.path.basename(f)[:-len(".caddy")].replace("__", ":")


# ---------------------------------------------------------------- apply
def backup(tag="auto"):
    os.makedirs(BAKD, exist_ok=True)
    p = os.path.join(BAKD, "Caddyfile.%s.%s" % (tag, time.strftime("%Y%m%d-%H%M%S")))
    write_inplace(p, read(LIVE))
    return p


def _sha_host(p):
    import hashlib
    return hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else ""


def _sha_in_container(c):
    o = sh(["docker", "exec", c, "sha256sum", "/etc/caddy/Caddyfile"]).stdout.strip()
    return o.split()[0] if o else ""


def mount_sync(c, fix=True):
    """Does the CONTAINER see the file we just wrote? (ok, message)

    THE HOP NOTHING WAS CHECKING. /etc/caddy/Caddyfile is a single-FILE bind mount, so the mount
    is pinned to an INODE. Anything that replaces the file rather than truncating it (`mv`,
    `sed -i`, a tmp-file-plus-rename, an editor writing a new file) leaves the container reading
    the OLD inode forever. `caddy reload` then succeeds and loads the STALE bytes, `caddy validate`
    passes because it validates a freshly-mounted temp copy, and the drift check passes because
    BOTH of its sides read from inside the container. Three green lights over a dead site.
    This is the only comparison that spans the mount, so it is the only one that can see it.
    """
    if not c:
        return True, "no container - nothing to compare"
    h, k = _sha_host(LIVE), _sha_in_container(c)
    if not k:
        return True, "could not read the file inside the container - skipping"
    if h == k:
        return True, "container reads the current file (%s)" % h[:12]
    if not fix:
        return False, "STALE MOUNT: host=%s container=%s" % (h[:12], k[:12])
    # A restart is the only way to re-resolve a single-file bind mount. It is a few seconds of
    # blip for EVERY vhost on this box, so it is done only when the hashes actually disagree.
    sh(["docker", "restart", c])
    for _ in range(20):
        time.sleep(1)
        if sh(["docker", "exec", c, "true"]).returncode == 0:
            break
    time.sleep(3)
    k2 = _sha_in_container(c)
    if k2 == h:
        return True, "stale mount repaired by restart (now %s)" % h[:12]
    return False, ("STILL STALE after restart: host=%s container=%s - the mount source is not %s"
                   % (h[:12], k2[:12], LIVE))


def apply(text, why=""):
    """Validate -> backup -> in-place write -> graceful reload. Rolls back on any failure."""
    c = container()
    ok, msg = acceptable(text, c)
    if not ok:
        return False, "REFUSED (%s): %s" % (why, msg)
    before = read(LIVE)
    b = backup("pre")
    write_inplace(LIVE, text)
    # BEFORE reloading: prove the container can even SEE what we just wrote. Reloading through a
    # stale mount re-applies the old config and reports success.
    msync, mmsg = mount_sync(c)
    print("   mount: %s" % mmsg)
    if not msync:
        write_inplace(LIVE, before)
        return False, "cannot reach the running proxy's config (%s) - NOT applied, %s" % (mmsg, b)
    r = sh(["docker", "exec", c, "caddy", "reload", "--config", "/etc/caddy/Caddyfile"])
    if r.returncode != 0:
        # exec fails while the container is restarting; a stop/start is the only path then.
        sh(["docker", "restart", c])
        for _ in range(18):
            time.sleep(5)
            if sh(["docker", "inspect", "-f", "{{.State.Status}}", c]).stdout.strip() == "running":
                break
    st = sh(["docker", "inspect", "-f", "{{.State.Status}}", c]).stdout.strip()
    if st != "running":
        write_inplace(LIVE, before)
        sh(["docker", "restart", c])
        return False, "proxy did not come up (%s) — ROLLED BACK, backup at %s" % (st, b)
    return True, "applied (%s), backup %s" % (why, b)


# ---------------------------------------------------------------- alerting
def notify(text):
    """Telegram. Never raises: an alerting failure must not become a second outage."""
    tok = chat = ""
    for ln in read(ENVF).splitlines():
        if ln.startswith("BOT_TOKEN="):
            tok = ln.split("=", 1)[1].strip().strip('"')
        elif ln.startswith("ALERT_TG_CHAT="):
            chat = ln.split("=", 1)[1].strip().strip('"').split(",")[0]
    tok = os.environ.get("BOT_TOKEN", tok)
    chat = os.environ.get("ALERT_TG_CHAT", chat)
    if not (tok and chat):
        print("[warn] no telegram credentials — alert not sent")
        return False
    try:
        data = urllib.parse.urlencode({"chat_id": chat, "text": text[:3900],
                                       "disable_web_page_preview": "true"}).encode()
        urllib.request.urlopen("https://api.telegram.org/bot%s/sendMessage" % tok, data, timeout=15)
        return True
    except Exception as e:
        print("[warn] telegram: %s" % e)
        return False


# ---------------------------------------------------------------- commands
def cmd_migrate():
    os.makedirs(FRAG, exist_ok=True)
    live = read(LIVE)
    base, frags = split(live)
    write_inplace(os.path.join(FRAG, "_base.caddy"), base)
    for n, t in frags.items():
        write_inplace(name_to_file(n), t.rstrip() + "\n")
    print("migrated: base + %d fragments -> %s" % (len(frags), FRAG))
    for n in sorted(frags):
        o, c = balance(frags[n])
        print("   %-22s %4d lines  braces %d/%d%s"
              % (n, frags[n].count("\n") + 1, o, c, "  <-- UNBALANCED" if o != c else ""))
    json.dump({"migrated": time.time(), "live": LIVE}, open(STATE, "w"))
    return 0


def cmd_restore(name, src=None, force=False):
    """Recover one project's fragment from the newest backup whose copy of it is BALANCED.

    IDEMPOTENT BY DEFAULT. This runs on every `python ship.py`, so it must be a no-op once the
    block is healthy — otherwise a routine deploy would silently overwrite a project's current
    config with whatever an old backup happened to contain. It only acts when the fragment is
    missing, empty (markers but no site block), or brace-unbalanced. `--force` overrides."""
    # "HEALTHY" MUST MEAN IT ROUTES SOMETHING.
    # The first version accepted any brace-balanced, non-empty block — so jobhuntwow's clobbered
    # block, which is comments plus a `log { }` and NO reverse_proxy, passed as healthy and the
    # restore skipped it for days. Caddy served it as 200-with-an-empty-body: the site "worked"
    # by every structural measure and showed a blank page to every visitor.
    # A site block with no routing directive is not a site. Check for one.
    ROUTES = ("reverse_proxy", "respond", "redir", "file_server", "php_fastcgi", "import")
    cur = read(name_to_file(name))
    if cur and not force:
        o, c = balance(cur)
        code = "\n".join(l.split("#")[0] for l in cur.split("\n"))
        routes = [d for d in ROUTES if d in code]
        if o == c and o > 0 and routes:
            print("%s already healthy (%d lines, braces %d/%d, routes via %s) — nothing to restore"
                  % (name, cur.count("\n") + 1, o, c, "/".join(routes)))
            return 0
        if o == c and o > 0 and not routes:
            print("%s parses but has NO routing directive (%s) — it would serve an empty 200. "
                  "Restoring." % (name, ", ".join(ROUTES[:3]) + ", ..."))
    def _ls(d, pref=""):
        # Never let an unreadable directory abort the search — a restore that dies on /root
        # permissions is a restore that does not happen.
        try:
            return sorted((os.path.join(d, f) for f in os.listdir(d) if f.startswith(pref)),
                          reverse=True)
        except Exception:
            return []

    if src:
        cands = [src]
    else:
        cands = (_ls(os.path.dirname(LIVE), "Caddyfile.")
                 + _ls(BAKD) + _ls("/root", "Caddyfile.bak"))
    for p in cands:
        if not os.path.isfile(p):
            continue
        _, frags = split(read(p))
        blk = frags.get(name)
        if not blk:
            continue
        o, c = balance(blk)
        if o != c or o == 0:
            print("   skip %s (block present but braces %d/%d)" % (p, o, c))
            continue
        # A candidate must ROUTE, not merely parse — otherwise we would "restore" the same empty
        # block that caused the blank page, from a backup taken after the damage.
        bcode = "\n".join(x.split("#")[0] for x in blk.split("\n"))
        if not any(d in bcode for d in ROUTES):
            print("   skip %s (block parses but routes nothing)" % p)
            continue
        write_inplace(name_to_file(name), blk.rstrip() + "\n")
        print("restored %s from %s (%d lines, braces %d/%d)"
              % (name, p, blk.count("\n") + 1, o, c))
        return 0
    print("no backup contained a balanced '%s' block" % name)
    return 1


def cmd_write(name, path):
    new = read(path)
    spans, bad = markers(new)
    if name not in spans:
        print("refused: %s does not contain '# %s BEGIN/END'" % (path, name))
        return 2
    if len(spans) != 1 or bad:
        print("refused: a fragment must contain exactly its own marker pair (%s)" % (bad or spans))
        return 2
    prev = read(name_to_file(name))
    write_inplace(name_to_file(name), new.rstrip() + "\n")
    ok, msg = apply(assemble(), "write %s" % name)
    print(msg)
    if not ok:
        if prev:
            write_inplace(name_to_file(name), prev)
        else:
            os.remove(name_to_file(name))
        return 1
    return 0


def cmd_assemble(do_apply):
    text = assemble()
    ok, msg = acceptable(text)
    print("assembled %d bytes — %s" % (len(text), "OK" if ok else "INVALID: " + msg))
    if not ok:
        return 1
    if do_apply:
        ok, msg = apply(text, "assemble")
        print(msg)
        return 0 if ok else 1
    return 0


def cmd_check(heal):
    """The watchdog. Runs on a timer. This is what turns a 12-hour latent bomb into a 10-min alert."""
    c = container()
    live = read(LIVE)
    probs = structural(live)
    vok, vmsg = (True, "") if probs else validate(live, c)
    st = sh(["docker", "inspect", "-f", "{{.State.Status}}", c]).stdout.strip() if c else "missing"
    # THE PORT IS CONFIGURABLE. Hardcoding :443 made this check FAIL on staging, where the twin's
    # caddy listens on :8080 — and the failure detail was truncated right before the line that
    # said so, producing "FAIL ... structural: ok validate: ok". An auditor model caught it:
    # "the ok field is false both times, indicating a parsing or reporting bug in the check itself".
    port = os.environ.get("CADDY_PORT", "443")
    bound = (":%s" % port) in sh(["bash", "-c", "ss -lnt 2>/dev/null || netstat -lnt"]).stdout

    # THE MOUNT IS PART OF HEALTH. `validate` checks the HOST file and `st` checks the container,
    # but if the single-file bind mount is pinned to a replaced inode the proxy is serving bytes
    # neither of those two ever looks at. --heal restarts to re-resolve it; a read-only run
    # reports it. Never silently: a proxy reading a file nobody can see is the latent bomb.
    msync, mmsg = mount_sync(c, fix=bool(heal)) if c else (True, "no container")

    healthy = (not probs) and vok and st == "running" and bound and msync
    if healthy:
        print("OK  live config valid · proxy running · :%s bound · %s" % (port, mmsg))
        return 0

    detail = ["CADDY GUARD — the shared proxy config is NOT healthy",
              "file:      %s" % LIVE,
              "container: %s (%s)" % (c or "none", st),
              ":%s bound: %s" % (port, "yes" if bound else "NO"),
              "structural: %s" % ("; ".join(probs) if probs else "ok"),
              "validate:   %s" % ("ok" if vok else vmsg),
              "mount:      %s" % mmsg]
    print("\n".join(detail))

    if heal and os.path.isdir(FRAG):
        # Fragments are the source of truth and each was validated when written, so rebuilding
        # from them is strictly safer than leaving a crash loop in place.
        text = assemble()
        ok, msg = acceptable(text)
        if ok:
            ok, msg = apply(text, "self-heal")
            detail.append("self-heal: %s" % msg)
            print("self-heal: %s" % msg)
            if ok:
                notify("\n".join(detail) + "\n\nSELF-HEALED from validated fragments.")
                return 0
        else:
            detail.append("self-heal REFUSED: %s" % msg)
    notify("\n".join(detail))
    return 1


def cmd_show():
    print("live:      %s" % LIVE)
    print("fragments: %s" % FRAG)
    if os.path.isdir(FRAG):
        for f in sorted(os.listdir(FRAG)):
            t = read(os.path.join(FRAG, f))
            o, c = balance(t)
            print("   %-26s %4d lines  braces %d/%d" % (f, t.count("\n") + 1, o, c))
    live = read(LIVE)
    o, c = balance(live)
    print("live braces %d/%d · structural: %s" % (o, c, structural(live) or "ok"))
    print("container: %s" % (container() or "none"))
    return 0


# ---------------------------------------------------------------------------------------------
# DRIFT — is the RUNNING process serving what the FILE says?
#
# This is the 2026-08-07 mechanism: Caddy reads its config ONLY at start, so a file edited after
# startup is silently unapplied and nothing notices until the next restart. With the admin API on,
# we can ask the running process directly.
#
# WHY NOT COMPARE HASHES. The first version md5'd `caddy adapt` against `GET /config/` and reported
# DRIFT on a perfectly healthy box — including immediately after a reboot, with the SAME two hashes
# before and after. That is the tell: a reboot makes Caddy re-read the file, so a genuinely stale
# process CANNOT survive one. Two hashes that stay different across a restart are not two configs,
# they are two SERIALISATIONS of one config. `adapt` emits the adapter's JSON; the admin API
# re-marshals from parsed Go structs, which reorders keys and fills in defaults. Byte equality was
# never achievable and the check could only ever fail.
#
# So compare the thing the question is actually about: WHAT IS SERVED. The set of matched hostnames
# and the set of terminal handlers (proxy upstreams, file roots, redirect/respond) is stable under
# re-serialisation and is exactly what changes when a block is truncated or replaced — which is the
# defect this check exists to catch.
def _served(cfg):
    hosts, handlers = set(), set()

    def walk(o):
        if isinstance(o, dict):
            h = o.get("host")
            if isinstance(h, list):
                hosts.update(str(x) for x in h)
            hd = o.get("handler")
            if hd == "reverse_proxy":
                for u in o.get("upstreams") or []:
                    if isinstance(u, dict) and u.get("dial"):
                        handlers.add("proxy:" + str(u["dial"]))
            elif hd == "file_server":
                handlers.add("file_server")
            elif hd == "static_response":
                handlers.add("respond:%s" % (o.get("status_code") or o.get("headers") or ""))
            elif hd == "vars" and o.get("root"):
                handlers.add("root:" + str(o["root"]))
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk((cfg or {}).get("apps", {}))
    return hosts, handlers


def cmd_drift():
    c = container()
    if not c:
        print("[!] no caddy container - cannot compare"); return 0
    # HOP 1 - HOST FILE  ->  CONTAINER FILE (across the bind mount).
    # The first version of this check compared only hops 2 and 3, BOTH of which read from inside
    # the container. A stale single-file mount makes both sides agree perfectly on the wrong
    # bytes, so the check reported OK over a dead site. Check the mount first, always.
    ok, msg = mount_sync(c, fix=False)
    print(("OK   mount: " if ok else "STALE MOUNT ") + msg)
    if not ok:
        print("   the container is reading a REPLACED INODE - `caddy reload` is loading old bytes")
        print("   fix: caddyguard check --heal (restarts the proxy so the mount re-resolves)")
        return 1
    disk_raw = sh(["docker", "exec", c, "caddy", "adapt", "--config", "/etc/caddy/Caddyfile"]).stdout
    run_raw = sh(["docker", "exec", c, "wget", "-qO-", "http://127.0.0.1:2019/config/"]).stdout
    if not (run_raw or "").strip():
        # NOT a failure. `admin off` is a legitimate configuration; a check that cannot see its
        # subject must say so, not invent a verdict. (The ruff gate and the esbuild probe taught
        # this the expensive way.)
        print("SKIP admin API unreachable (admin off?) - cannot read the running config"); return 0
    try:
        d_hosts, d_h = _served(json.loads(disk_raw))
        r_hosts, r_h = _served(json.loads(run_raw))
    except Exception as e:
        print("SKIP could not parse a config (%s)" % e); return 0
    if d_hosts == r_hosts and d_h == r_h:
        print("OK running config serves exactly what the file says "
              "(%d host(s), %d handler(s))" % (len(r_hosts), len(r_h)))
        return 0
    print("DRIFT the running process is NOT serving the file on disk")
    for label, dset, rset in (("hosts", d_hosts, r_hosts), ("handlers", d_h, r_h)):
        only_d, only_r = sorted(dset - rset), sorted(rset - dset)
        if only_d:
            print("   %s on DISK but NOT running : %s" % (label, ", ".join(only_d)))
        if only_r:
            print("   %s RUNNING but not on disk  : %s" % (label, ", ".join(only_r)))
    return 1


def main(argv):
    if not argv:
        return cmd_show()
    cmd, rest = argv[0], argv[1:]
    os.makedirs(ROOT, exist_ok=True)
    if cmd == "migrate":
        return cmd_migrate()
    if cmd == "restore":
        pos = [x for x in rest if not x.startswith("--")]
        return cmd_restore(pos[0], pos[1] if len(pos) > 1 else None, "--force" in rest)
    if cmd == "write":
        return cmd_write(rest[0], rest[1])
    if cmd == "assemble":
        return cmd_assemble("--apply" in rest)
    if cmd == "check":
        return cmd_check("--heal" in rest)
    if cmd == "drift":
        return cmd_drift()
    if cmd == "show":
        return cmd_show()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
