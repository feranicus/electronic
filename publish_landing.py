#!/usr/bin/env python3
"""
publish_landing.py — put the animated landing live on cybergod.ai RIGHT NOW.
No new API key, no DNS change, no droplet. cybergod.ai already serves GitHub Pages
(feranicus.github.io) — this just replaces that stale page with the new one.

Usage:  python publish_landing.py
Env (optional): PAGES_REPO (default https://github.com/feranicus/feranicus.git), PAGES_BRANCH (main)
"""
import os, subprocess, tempfile, shutil, sys
HERE   = os.path.dirname(os.path.abspath(__file__))
REPO   = os.environ.get("PAGES_REPO", "https://github.com/feranicus/feranicus.git")
BRANCH = os.environ.get("PAGES_BRANCH", "main")
SRC    = os.path.join(HERE, "colt_platform_architecture.html")

def run(a, **k): print("  $ " + " ".join(a)); return subprocess.run(a, **k)

def main():
    if not os.path.exists(SRC): sys.exit("[X] landing not found: " + SRC)
    tmp = tempfile.mkdtemp(prefix="pages-")
    if run(["git", "clone", "--depth", "1", "-b", BRANCH, REPO, tmp]).returncode != 0:
        sys.exit("[X] clone failed — check the repo/branch or your git auth")
    shutil.copy(SRC, os.path.join(tmp, "index.html"))          # the page cybergod.ai serves
    cn = os.path.join(tmp, "CNAME")
    if not os.path.exists(cn): open(cn, "w").write("cybergod.ai\n")   # keep the custom domain bound
    run(["git", "-C", tmp, "add", "index.html", "CNAME"])
    if run(["git", "-C", tmp, "commit", "-m", "cybergod.ai: publish animated landing"]).returncode != 0:
        print("  (no change to publish)"); return
    if run(["git", "-C", tmp, "push", "origin", BRANCH]).returncode != 0:
        sys.exit("[X] push failed — check git auth for " + REPO)
    print("\nDONE. cybergod.ai will show the new landing in ~1 minute (GitHub Pages rebuild).")

if __name__ == "__main__":
    main()
