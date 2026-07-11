#!/usr/bin/env python3
"""
unpublish_pages.py -- stop GitHub Pages from CLAIMING cybergod.ai.

Why: publish_landing.py had pushed a CNAME file (cybergod.ai) into the GitHub Pages repo.
That file makes GitHub Pages answer for cybergod.ai, so while DNS is cached some browsers hit
GitHub (404) instead of the droplet. cybergod.ai now lives 100% on the droplet, so GitHub must
let go of the name. This clones the Pages repo, deletes CNAME + the index/login/404 we added,
commits and pushes. Run ONCE. (You should also clear Settings -> Pages -> Custom domain, and/or
disable Pages for that repo, to be thorough.)

Usage:  python unpublish_pages.py
Env (optional): PAGES_REPO (default https://github.com/feranicus/feranicus.git), PAGES_BRANCH (main)
"""
import os, subprocess, tempfile, sys
REPO   = os.environ.get("PAGES_REPO", "https://github.com/feranicus/feranicus.git")
BRANCH = os.environ.get("PAGES_BRANCH", "main")

def run(a, **k): print("  $ " + " ".join(a)); return subprocess.run(a, **k)

def main():
    tmp = tempfile.mkdtemp(prefix="pages-unpub-")
    if run(["git","clone","--depth","1","-b",BRANCH,REPO,tmp]).returncode != 0:
        sys.exit("[X] clone failed -- check repo/branch or your git auth")
    removed = []
    for rel in ("CNAME", "login/index.html", "404.html"):
        p = os.path.join(tmp, rel)
        if os.path.exists(p):
            run(["git","-C",tmp,"rm","-q","-f",rel]); removed.append(rel)
    if not removed:
        print("  (nothing to remove -- CNAME already gone)"); return
    if run(["git","-C",tmp,"commit","-m","cybergod.ai: release GitHub Pages custom domain (served from droplet now)"]).returncode != 0:
        print("  (no change to commit)"); return
    if run(["git","-C",tmp,"push","origin",BRANCH]).returncode != 0:
        sys.exit("[X] push failed -- check git auth for " + REPO)
    print("\nDONE. Removed: %s" % ", ".join(removed))
    print("GitHub Pages no longer claims cybergod.ai. Also clear Settings -> Pages -> Custom domain to be safe.")

if __name__ == "__main__":
    main()
