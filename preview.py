#!/usr/bin/env python3
"""preview.py — see the site on THIS machine, before anything is deployed.

    python preview.py                 the dev server, live reload, opens the browser
    python preview.py --build         build for production and serve exactly what would ship
    python preview.py --offline       no proxy at all: pure front end, no API
    python preview.py --port 5000     pick the port
    python preview.py --no-open       do not open a browser

WHY THIS SCRIPT EXISTS RATHER THAN "just run npm run dev":

1. node_modules IN THIS REPO IS PLATFORM-SPECIFIC AND THE FOLDER IS SHARED.
   npm ships per-platform binaries as optional dependencies, so a node_modules installed on Linux
   dies on Windows with `The package "@esbuild/win32-x64" could not be found`, and vice versa. That
   exact failure already cost three shipping attempts (recorded in CLAUDE.md). This script DETECTS
   the mismatch and reinstalls, instead of handing the operator a command that cannot work on the
   machine he is typing it into.

2. THE PREVIEW MUST NOT BE ABLE TO CHANGE PRODUCTION.
   The public pages need real API data (/api/demo, /api/langs, /api/jurisdictions), so by default
   the dev server proxies /api to the live site. That is convenient and it is also dangerous: the
   browser may hold a live session cookie, and one click on "Run assessment" would start a REAL
   job against real quota from what looks like a local preview. So the proxy is READ-ONLY. GET and
   HEAD pass; anything that writes is refused on this machine, before it leaves it, with a message
   saying so. `--offline` removes the proxy entirely.

3. THE POINT OF THE COLOUR CHANGE WAS PHONES IN DAYLIGHT.
   So the server also listens on the local network and prints the address to type into a phone.
   Looking at it on a monitor indoors tests the one condition the change was NOT made for.

Deploys are still `python ship.py`. This script never touches the droplet, never builds an image
and never pushes anything.
"""
import argparse
import os
import platform
import shutil
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FE = ROOT / "webapp" / "frontend"
LIVE = "https://cybergod.ai"


def say(msg=""):
    print(msg, flush=True)


def die(msg):
    say("\n[X] " + msg)
    sys.exit(1)


def which(name):
    """npm is npm.cmd on Windows; shutil.which handles PATHEXT, a bare name does not."""
    return shutil.which(name)


def run(cmd, **kw):
    return subprocess.run(cmd, cwd=str(FE), shell=(os.name == "nt"), **kw)


# ----------------------------------------------------------------------------- the toolchain
def toolchain_runs(node):
    """Can vite actually START on this machine, with this node_modules?

    TEST BY EXECUTION, NOT BY FILE LAYOUT. The first version of this looked for a directory named
    `@esbuild/<platform>` and reported "installed for a different platform" on a Linux box where
    esbuild demonstrably worked: after an install, `node_modules/@esbuild/` holds one temporary
    directory per platform with a random suffix, so the name I was looking for is not the name that
    is there. It would have wiped a perfectly good node_modules on every run.

    Loading vite's CLI exercises the whole native chain (esbuild and rollup both ship per-platform
    binaries). If that works, the toolchain is fine; if it does not, the message says why.
    """
    vite = FE / "node_modules" / "vite" / "bin" / "vite.js"
    if not vite.exists():
        return False, "vite is not installed"
    r = subprocess.run([node, str(vite), "--version"], cwd=str(FE),
                       capture_output=True, text=True, timeout=120)
    if r.returncode == 0:
        return True, r.stdout.strip()
    return False, (r.stderr or r.stdout).strip().splitlines()[0] if (r.stderr or r.stdout) else "unknown error"


def ensure_deps():
    node = which("node")
    if not node:
        die("Node.js is not on PATH. Install Node 18 or newer from https://nodejs.org and re-run:\n"
            "    python preview.py")
    if not which("npm"):
        die("npm is not on PATH, although node is. Reinstall Node.js and re-run: python preview.py")

    ver = subprocess.run([node, "-v"], capture_output=True, text=True).stdout.strip()
    say("  node %s on %s" % (ver, platform.system()))

    nm = FE / "node_modules"
    if nm.exists():
        ok, detail = toolchain_runs(node)
        if ok:
            say("  %s, dependencies already in place" % detail)
            return
        # The documented failure: node_modules lives in a folder shared with a Linux sandbox, so it
        # can hold linux-x64 binaries while this is a Windows box. npm ships per-platform binaries
        # as optional dependencies, so the fix is a reinstall on THIS machine.
        say("  vite will not start with the current node_modules:")
        say("    %s" % detail[:160])
        say("  reinstalling for %s. This is the shared-folder problem, not a broken repo." % platform.system())
        shutil.rmtree(nm, ignore_errors=True)
    else:
        say("  installing dependencies (first run, about a minute)...")

    if run(["npm", "install", "--no-audit", "--no-fund"]).returncode != 0:
        die("npm install failed. Delete webapp/frontend/node_modules by hand, then re-run:\n"
            "    python preview.py")
    ok, detail = toolchain_runs(node)
    if not ok:
        die("dependencies installed but vite still will not start: %s" % detail)
    say("  %s ready" % detail)


# ----------------------------------------------------------------------------- addresses
def lan_ip():
    """The address a phone on the same network can reach. Connecting a UDP socket does not send a
    packet; it just asks the routing table which interface would be used."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("192.0.2.1", 9))          # RFC 5737 documentation address, never routed
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None


def free_port(start):
    for p in range(start, start + 40):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
    return start


def wait_then_open(url, port, do_open):
    for _ in range(120):                      # up to ~30s; vite is usually ready in 1-2
        time.sleep(0.25)
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                break
    else:
        return
    ip = lan_ip()
    say("")
    say("  " + "=" * 66)
    say("  READY")
    say("    on this computer   %s" % url)
    if ip:
        say("    on your phone      http://%s:%d   (same wifi)" % (ip, port))
        say("                       Look at it OUTSIDE. Daylight is the condition the light theme")
        say("                       was chosen for, and the one a monitor cannot show you.")
    else:
        say("    on your phone      unavailable: could not read this machine's network address")
    say("")
    say("    pages to look at   /            the landing page")
    say("                       /partners    the long one, the reason for going light")
    say("                       /demo        the dark hero against the light page")
    say("                       /login       the S4biz gradient panel")
    say("    Ctrl+C here stops it.")
    say("  " + "=" * 66)
    say("")
    if do_open:
        try:
            webbrowser.open(url)
        except Exception:
            pass


def main():
    ap = argparse.ArgumentParser(description="Preview cybergod.ai on this machine.")
    ap.add_argument("--build", action="store_true",
                    help="build for production and serve the built files, exactly what would ship")
    ap.add_argument("--offline", action="store_true",
                    help="no API proxy at all; the front end only")
    ap.add_argument("--api", default=LIVE,
                    help="what /api points at (default: the live site, READ-ONLY)")
    ap.add_argument("--port", type=int, default=5173)
    ap.add_argument("--no-open", action="store_true", help="do not open a browser")
    a = ap.parse_args()

    say("")
    say("  cybergod.ai — local preview. Nothing is deployed by this script.")
    say("")
    ensure_deps()

    # STAMP THE FRONTEND. ship.py refuses to deploy a UI that has changed since it was last
    # previewed, and this is what proves you looked at THIS version. A hash rather than a
    # timestamp, for the same reason the deploy verifies the engine by hash: "a preview happened
    # at some point" is not the same claim as "this frontend was previewed".
    try:
        import ui_preview_stamp
        h = ui_preview_stamp.write_preview_stamp()
        say("  stamped      %d UI files (%s) — ship.py will now accept this frontend" %
            (len(ui_preview_stamp.ui_files()), h[:12]))
    except Exception as e:
        say("  [!] could not write the preview stamp (%s); ship.py will still ask for a preview"
            % type(e).__name__)

    env = dict(os.environ)
    port = free_port(a.port)
    if port != a.port:
        say("  port %d was busy, using %d" % (a.port, port))
    env["CG_PORT"] = str(port)

    if a.offline:
        env["CG_API_TARGET"] = "http://127.0.0.1:1"     # nothing listens there; calls fail fast
        env["CG_API_READONLY"] = "1"
        say("  /api        disabled (--offline). Pages that need data will look empty.")
    else:
        env["CG_API_TARGET"] = a.api
        env["CG_API_READONLY"] = "1"
        say("  /api        %s, READ-ONLY" % a.api)
        say("              GET passes so the public pages have real data. Anything that WRITES is")
        say("              refused on this machine, so a preview cannot start a real assessment.")

    # ------------------------------------------------------------------------------------------
    # CALL vite.js DIRECTLY, NEVER `npm run dev`.
    # `npm run` resolves the binary through node_modules/.bin/vite, which is a PLATFORM SHIM: a
    # symlink on Linux, a .cmd on Windows, and absent entirely if an install was interrupted. That
    # is exactly what happened here, `sh: 1: vite: not found` on a machine where vite itself loads
    # perfectly. CLAUDE.md already records the same trap for node_modules/.bin/esbuild. Invoking
    # the .js entry point with node has none of that: one path, identical on every platform.
    # ------------------------------------------------------------------------------------------
    node = which("node")
    vite = str(FE / "node_modules" / "vite" / "bin" / "vite.js")
    if a.build:
        say("  building the production bundle...")
        if run([node, vite, "build"], env=env).returncode != 0:
            die("the build failed; the output above says why")
        cmd = [node, vite, "preview", "--port", str(port), "--host"]
        say("  serving the BUILT files (no live reload), which is exactly what would ship")
    else:
        cmd = [node, vite, "--port", str(port), "--host"]
        say("  dev server with live reload: edit a file, the browser updates")

    url = "http://localhost:%d/" % port
    threading.Thread(target=wait_then_open, args=(url, port, not a.no_open), daemon=True).start()
    try:
        run(cmd, env=env)
    except KeyboardInterrupt:
        pass
    say("\n  preview stopped. Nothing was deployed.\n")


if __name__ == "__main__":
    main()
