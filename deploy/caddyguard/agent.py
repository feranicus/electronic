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


def mount_source(c):
    """Where does THIS container's /etc/caddy/Caddyfile actually come from on the host?

    NEVER assume LIVE. The default (/opt/videodead/Caddyfile) is production's path; staging's
    proxy mounts a different file, so hashing LIVE there produced an empty hash and the check
    reported a stale mount on a healthy box. Docker knows the answer - ask it, and fall back to
    LIVE only when there is no such mount to inspect.
    """
    if not c:
        return ""
    out = sh(["docker", "inspect", c, "--format",
              '{{range .Mounts}}{{if eq .Destination "/etc/caddy/Caddyfile"}}{{.Source}}{{end}}{{end}}'
              ]).stdout.strip()
    return out or ""


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
    src = mount_source(c) or LIVE
    h, k = _sha_host(src), _sha_in_container(c)
    if not k:
        return True, "could not read the file inside the container - skipping"
    if not h:
        # A MISSING HOST FILE IS NOT STALENESS. It means this box does not mount a Caddyfile from
        # the path we looked at - there is nothing to compare, and the honest answer is SKIP.
        # Reading absence as failure is the mirror of "absence of evidence is never a finding".
        return True, "no host file at %s - single-file mount not in use here, nothing to compare" % src
    if h == k:
        return True, "container reads the current file (%s)" % h[:12]
    if not fix:
        return False, "STALE MOUNT: %s host=%s container=%s" % (src, h[:12], k[:12])
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
                   % (h[:12], k2[:12], src))


def site_blocks(text):
    """The site headers in a Caddyfile: every unindented line that opens a block.

    Text-level on purpose. This guards the write that happens BEFORE any container, admin API or
    `caddy adapt` is consulted, so it must work with none of them. The global options block is a
    bare `{` with no address in front of it, and is excluded.
    """
    out = []
    for ln in (text or "").splitlines():
        if not ln or ln[:1].isspace() or ln.lstrip().startswith("#"):
            continue
        t = ln.strip()
        if t.endswith("{") and t != "{":
            out.append(t[:-1].strip())
    return out


def apply(text, why=""):
    """Validate -> backup -> in-place write -> graceful reload. Rolls back on any failure."""
    c = container()
    ok, msg = acceptable(text, c)
    if not ok:
        return False, "REFUSED (%s): %s" % (why, msg)
    before = read(LIVE)

    # NEVER EMPTY A LIVE PROXY. 10 Aug 2026: a staging check called `assemble --apply` on a box
    # whose /opt/caddyguard/blocks/ was empty -- staging composes its Caddyfile directly and is not
    # fragment-managed -- so the assembly was EMPTY, this function wrote it, Caddy carried on
    # serving from memory, and the next reboot detonated it. That is the exact 2026-08-07 outage
    # mechanism, reproduced by the check written to detect it.
    # A config with no site blocks is never a legitimate deployment onto a proxy that is currently
    # serving sites. Same doctrine as the co-tenant guard and the FP auditor: an automatic process
    # may narrow the estate, it may not wipe it. CADDYGUARD_ALLOW_EMPTY is the deliberate escape.
    new_sites, old_sites = site_blocks(text), site_blocks(before)
    if old_sites and not new_sites and not os.environ.get("CADDYGUARD_ALLOW_EMPTY"):
        return False, ("REFUSED (%s): the new config serves NO sites while the live one serves %d "
                       "(%s). Refusing to empty a running proxy. Set CADDYGUARD_ALLOW_EMPTY=1 if "
                       "that is genuinely intended."
                       % (why, len(old_sites), ", ".join(old_sites[:4])))
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
            # PATH MATCHERS. kimi-k2.6 was right that hosts + terminal handlers alone is coarse:
            # a fragment rewritten so /api routes elsewhere keeps the same host set and the same
            # handler TYPES, and the old comparison saw nothing. A path matcher is stable under
            # re-serialisation, so it can be compared safely.
            p = o.get("path")
            if isinstance(p, list) and p:
                handlers.add("path:" + ",".join(sorted(str(x) for x in p)))
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk((cfg or {}).get("apps", {}))
    return hosts, handlers


# The domains this proxy is EXPECTED to serve. Committed, so a vhost silently disappearing is a
# failure rather than a quiet 404 nobody notices for twelve hours. Kimi flagged the gap on
# 2026-08-07: config_drift compares disk to running, so a deploy that rewrites the file AND reloads
# leaves both sides agreeing on an estate that is missing a customer's domain.
# Override per-host with CADDY_EXPECT="a.com,b.com"; empty disables the check rather than failing
# a box that legitimately serves something else (staging serves one vhost, production eleven).
EXPECT = [d for d in os.environ.get(
    "CADDY_EXPECT",
    "cybergod.ai,www.cybergod.ai,godeyes.ai,jobhuntwow.com,www.jobhuntwow.com,"
    "klimaanlage-preise.de,klimaanlage-montieren.de,www.klimaanlage-montieren.de,"
    "jev.best,www.jev.best"
).split(",") if d.strip()]


def cmd_admin():
    """Is Caddy's admin API reachable from anywhere but localhost?

    THE POINT kimi-k2.6 RAISED AND NOBODY HAD CHECKED (9 Aug 2026). Every drift and roster check in
    this file READS `http://127.0.0.1:2019/config/`, and the deploy WRITES through it
    (`POST /load`). That endpoint replaces the running configuration for EVERY domain on the box
    and has no authentication of its own: Caddy's only protection is that it binds to loopback by
    default. Nothing asserted that it still does. If a config ever set `admin { listen :2019 }`, or
    the port were published by Docker, anyone able to reach it would own the shared proxy, and
    every check in this file would keep reporting green while they did.

    Two independent questions, because either alone can be wrong:
      1. what the RUNNING config says the admin endpoint binds to;
      2. whether the port is actually published to a public interface by Docker.
    """
    c = container()
    if not c:
        print("SKIP no proxy container"); return 0

    bad = []
    raw = sh(["docker", "exec", c, "wget", "-qO-", "http://127.0.0.1:2019/config/"]).stdout
    listen = None
    if (raw or "").strip():
        try:
            listen = ((json.loads(raw).get("admin") or {}).get("listen"))
        except Exception:
            listen = None
    # Absent means Caddy's default, which IS localhost:2019. An explicit value must be loopback.
    if listen is not None:
        v = str(listen)
        if not (v.startswith("localhost") or v.startswith("127.0.0.1") or v.startswith("[::1]")):
            bad.append("the running config binds the admin API to %r, not loopback" % v)

    ports = sh(["docker", "port", c]).stdout or ""
    for line in ports.splitlines():
        if "2019" in line and ("0.0.0.0" in line or "[::]" in line):
            bad.append("docker publishes the admin port to the world: %s" % line.strip())

    # PROVE IT, DO NOT INFER IT. kimi-k2.6 argued (9 Aug 2026) that loopback plus not-published
    # does not establish isolation from co-tenant containers on the shared Docker bridge. Its
    # stated mechanism is wrong -- each container has its OWN network namespace, so `localhost`
    # inside videodead-caddy is not reachable from colt-web, and only `network_mode: container:`
    # or `service:` sharing would change that, which nothing here uses.
    #
    # But the CONSTRUCTIVE half of the objection stands and is the doctrine of this whole file: a
    # check that reasons about its subject is weaker than one that reproduces it. So actually TRY
    # to reach the admin API from a DIFFERENT container over the bridge address. If something ever
    # does share a namespace, or a future config binds 0.0.0.0, this measures it instead of
    # arguing about it.
    notes = []
    ip = (sh(["docker", "inspect", "-f",
              "{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}", c]).stdout or "").split()
    probe_from = None
    for cand in ("colt-web", "jhw-web", "polara-web"):
        if (sh(["docker", "inspect", "-f", "{{.State.Running}}", cand]).stdout or "").strip() == "true":
            probe_from = cand
            break
    if ip and probe_from:
        r = sh(["docker", "exec", probe_from, "sh", "-c",
                "wget -qO- --timeout=3 http://%s:2019/config/ 2>/dev/null | head -c 40" % ip[0]])
        if (r.stdout or "").strip():
            bad.append("the admin API ANSWERED a request from another container (%s -> %s:2019); "
                       "it is reachable across the shared bridge" % (probe_from, ip[0]))
        else:
            notes.append("probed from %s -> %s:2019: no answer (isolated, measured not assumed)"
                         % (probe_from, ip[0]))

    # THE VERDICT IS THE FIRST LINE. This check reported FAIL on a healthy box for one reason: it
    # printed a diagnostic line BEFORE its verdict, the caller matches `OK*` on the flattened
    # output, and so a correct result never matched and fell through to the wildcard -- which I
    # had (correctly) made a FAILURE the day before. A machine-readable verdict that is not in a
    # fixed position is not machine-readable. Notes come after, never before.
    if bad:
        print("EXPOSED " + " | ".join(bad))
        for n in notes:
            print("   " + n)
        return 1
    print("OK admin API is loopback-only (%s) and not published"
          % (listen or "Caddy default localhost:2019"))
    for n in notes:
        print("   " + n)
    return 0


def cmd_roster():
    """Is every domain we are supposed to serve actually in the RUNNING config?"""
    c = container()
    if not c or not EXPECT:
        print("SKIP no container or no expected roster configured"); return 0
    raw = sh(["docker", "exec", c, "wget", "-qO-", "http://127.0.0.1:2019/config/"]).stdout
    if not (raw or "").strip():
        print("SKIP admin API unreachable - cannot read the running roster"); return 0
    try:
        hosts, _ = _served(json.loads(raw))
    except Exception as e:
        print("SKIP could not parse the running config (%s)" % e); return 0
    missing = [d for d in EXPECT if d.strip() and d.strip() not in hosts]
    if missing:
        print("MISSING the running proxy does not serve: %s" % ", ".join(missing))
        print("   serving: %s" % ", ".join(sorted(hosts)))
        return 1

    # UNEXPECTED VHOSTS ARE ALSO A FINDING. kimi-k2.6 made the symmetry argument on 2026-08-09 and
    # it is correct: this check's whole premise is that "a vhost that silently disappears is a
    # failure", and on a SHARED reverse proxy a vhost that silently APPEARS is the same class of
    # event. An unexplained hostname in the running config means either a project wrote outside the
    # guard, or something is claiming traffic and certificates for a name nobody committed.
    #
    # It is a WARNING, not a failure, and deliberately so: legitimately adding a site is a normal
    # operation, and a gate that fails the deploy every time somebody launches a project would be
    # switched off within a week. It names them so the operator decides.
    known = {d.strip() for d in EXPECT if d.strip()}
    # Caddy's own internal names are not vhosts anyone committed and are not traffic-bearing.
    _INTERNAL = {"localhost", "127.0.0.1", "::1", ""}
    extra = sorted(h for h in hosts
                   if h not in known and h.lower() not in _INTERNAL
                   and not any(h == "www." + d or h.endswith("." + d) for d in known))
    print("OK all %d expected domain(s) are served (%d host(s) total)" % (len(EXPECT), len(hosts)))
    if extra:
        print("   [!] %d host(s) served that are NOT on the committed roster: %s"
              % (len(extra), ", ".join(extra[:8])))
        print("       On a shared proxy an unexpected vhost claims traffic and certificates for a "
              "name nobody committed. Add it to the roster, or find out who wrote it.")
    return 0


def cmd_drift():
    c = container()
    if not c:
        # SKIP, not a bare note: a caller matching on the verdict token cannot classify "[!] ..."
        # and would score this either as a pass it did not earn or as a failure it did not deserve.
        print("SKIP no caddy container - nothing to compare"); return 0
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
    # AN EMPTY RUNNING CONFIG IS DEGENERATE, NOT THE ABSENCE OF DRIFT. Raised by gemma-4-31B-it
    # and kimi-k2.6 on the same run and both were right: after the reboot this reported OK on
    # "0 host(s), 0 handler(s)" while the proxy served nothing and the roster check correctly
    # failed. Equal emptiness compares fine and means the box is down.
    if not d_hosts and not r_hosts:
        print("DRIFT the running config serves NO hosts at all - the proxy is up but serving "
              "nothing. That is a degenerate config, not the absence of drift.")
        return 1
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
    if cmd == "roster":
        return cmd_roster()
    if cmd == "admin":
        return cmd_admin()
    if cmd == "show":
        return cmd_show()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
