#!/usr/bin/env python3
"""
ship.py — ONE command to ship the assess bot end-to-end. No manual steps.

It:
  1. Repairs assess-bot/bot.py from the running container if the local copy is broken/short
     (guards against the editor-truncation bug), then applies the multi-word-seed fix (idempotent).
  2. Commits + pushes the repo (single source of truth).
  3. Rebuilds + redeploys the whole colt-stack on the droplet (deploy.py --reuse).
  4. Verifies the bot container is up and tails its log.

Usage:   python ship.py
Env (optional): DROPLET_HOST, DROPLET_USER, SSH_KEY, BOT_CONTAINER
"""
import os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HOST = os.environ.get("DROPLET_HOST", "64.225.108.200")
USER = os.environ.get("DROPLET_USER", "root")
KEY  = os.environ.get("SSH_KEY", os.path.expanduser("~/.ssh/id_ed25519"))
CONT = os.environ.get("BOT_CONTAINER", "colt-assessbot")
BOT  = os.path.join(HERE, "assess-bot", "bot.py")

SSH = ["ssh", "-o", "StrictHostKeyChecking=accept-new", "-o", "LogLevel=ERROR",
        "-o", "ConnectTimeout=10", "-o", "BatchMode=yes", "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=4"]
SCP = ["scp", "-o", "StrictHostKeyChecking=accept-new", "-o", "LogLevel=ERROR"]
if os.path.exists(KEY):
    SSH += ["-i", KEY]; SCP += ["-i", KEY]

def ssh(cmd, check=True):
    r = subprocess.run(SSH + [f"{USER}@{HOST}", cmd], text=True, capture_output=True)
    if r.stdout.strip(): print(r.stdout.rstrip())
    if check and r.returncode != 0: sys.exit(f"[X] remote failed: {cmd}\n{r.stderr[:400]}")
    return r.stdout

def local(args, check=True):
    print("  $ " + " ".join(args)); r = subprocess.run(args, cwd=HERE)
    if check and r.returncode != 0: sys.exit(f"[X] failed: {' '.join(args)}")
    return r.returncode

SEED_OLD = "    seed = ctx.args[0]; extra = ctx.args[1:]"
SEED_NEW = ("    _args = list(ctx.args)\n"
            "    _i = next((k for k, t in enumerate(_args) if t.startswith('--')), len(_args))\n"
            "    seed = ' '.join(_args[:_i]).strip(); extra = _args[_i:]   # multi-word company names -> one seed\n"
            "    if not seed:\n"
            "        await update.message.reply_text('Usage: /assess <company / domain / ASN>'); return")

def repair_bot():
    """If local bot.py looks truncated (no main()/handlers), pull the good copy from the container."""
    txt = open(BOT, encoding="utf-8").read() if os.path.exists(BOT) else ""
    ok = ("def main(" in txt or "run_polling" in txt or "add_handler" in txt) and len(txt.splitlines()) > 110
    if not ok:
        print("  bot.py looks truncated — recovering the good copy from the running container...")
        tmp = "/tmp/ship_bot.py"
        ssh(f"docker cp {CONT}:/opt/bot.py {tmp}")
        subprocess.run(SCP + [f"{USER}@{HOST}:{tmp}", BOT], check=True)
        txt = open(BOT, encoding="utf-8").read()
        print(f"  recovered bot.py ({len(txt.splitlines())} lines)")
    return txt

def patch_bot(txt):
    if SEED_NEW.splitlines()[0] in txt:
        print("  multi-word-seed fix already present.")
    elif SEED_OLD in txt:
        open(BOT, "w", encoding="utf-8").write(txt.replace(SEED_OLD, SEED_NEW, 1))
        print("  applied multi-word-seed fix.")
    else:
        print("  (seed-parse anchor not found — leaving bot.py as-is)")
    # syntax check
    if subprocess.run([sys.executable, "-m", "py_compile", BOT]).returncode != 0:
        sys.exit("[X] bot.py does not compile after patch")
    print("  bot.py compiles OK.")

def main():
    print(f"=== ship: {USER}@{HOST}  container={CONT} ===")
    print("--- 1) repair + patch bot.py ---")
    patch_bot(repair_bot())

    print("--- 2) commit + push (single source of truth) ---")
    local(["git", "add", "assess-bot/bot.py", "hermes-skills/shodan-assessment/scripts", "CLAUDE.md", "ship.py"], check=False)
    rc = subprocess.run(["git", "commit", "-m", "assess-bot: multi-word seed + name-only autodiscovery; recon/deck upgrades"], cwd=HERE).returncode
    if rc == 0: local(["git", "push", "origin", "main"], check=False)
    else: print("  (nothing to commit)")

    print("--- 3) rebuild + redeploy the whole stack from the repo ---")
    local([sys.executable, "deploy.py", "--reuse", "--yes"])

    print("--- 4) verify ---")
    ssh(f"docker ps --format '{{{{.Names}}}}  {{{{.Status}}}}' | grep -i {CONT} || echo 'NOT RUNNING'")
    print("  recent bot log:")
    ssh(f"docker logs --tail 15 {CONT} 2>&1 || true", check=False)
    print("\n" + "=" * 56)
    print("DONE. In Telegram:  /assess Volkswagen AG   (no flags — auto-resolves everything)")
    print("=" * 56)

if __name__ == "__main__":
    main()
