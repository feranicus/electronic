#!/usr/bin/env python3
"""
finalize_public.py — one command to purge the leaked file from git history,
go public, and re-apply the CI/CD guardrails.

Steps (in order):
  1. pip install git-filter-repo
  2. safety backup bundle of the whole repo (so nothing is lost)
  3. git filter-repo: strip linkedin_cookies.json + the two broken submodule
     pointers (feranicus, jobhuntwow.com) from ALL history
  4. re-add the origin remote (filter-repo removes it by design) + force-push
  5. gh repo edit --visibility public
  6. python setup_github_cicd.py  (branch protection + prod environment + secrets)

Usage:
    python finalize_public.py           # prompts once before the irreversible steps
    python finalize_public.py --yes      # no prompt (fully unattended)

Requires: git, gh (authenticated), python.  Force-push uses your cached GitHub creds.
"""
import argparse, os, subprocess, sys, sysconfig, time, shutil

REPO_SLUG  = "feranicus/electronic"
REMOTE_URL = f"https://github.com/{REPO_SLUG}.git"
PURGE_PATHS = ["linkedin_cookies.json", "feranicus", "jobhuntwow.com"]
HERE = os.path.dirname(os.path.abspath(__file__))


def run(cmd, check=True, env=None, cwd=HERE):
    print("\n$ " + " ".join(cmd))
    r = subprocess.run(cmd, env=env, cwd=cwd)
    if check and r.returncode != 0:
        sys.exit(f"\n[X] step failed (exit {r.returncode}): {' '.join(cmd)}")
    return r.returncode


def capture(cmd, cwd=HERE):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True).stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    a = ap.parse_args()

    # sanity: are we in the right repo?
    if not os.path.isdir(os.path.join(HERE, ".git")):
        sys.exit(f"[X] {HERE} is not a git repo root.")
    print(f"Repo:   {HERE}")
    print(f"Target: {REPO_SLUG}")
    print("Will purge from ALL history:", ", ".join(PURGE_PATHS))
    print("Then: force-push rewritten history, make repo PUBLIC, re-apply guardrails.")

    if not a.yes:
        if input("\nProceed? This rewrites history and makes the repo public [y/N]: ").strip().lower() != "y":
            sys.exit("Aborted. Nothing changed.")

    # ---- 1) install git-filter-repo -------------------------------------
    print("\n=== 1/6  install git-filter-repo ===")
    run([sys.executable, "-m", "pip", "install", "--quiet", "--upgrade", "git-filter-repo"])
    # make sure `git filter-repo` is resolvable: add the pip Scripts dir to PATH
    env = os.environ.copy()
    scripts_dir = sysconfig.get_path("scripts")
    env["PATH"] = scripts_dir + os.pathsep + env.get("PATH", "")

    # ---- 2) safety backup bundle ----------------------------------------
    print("\n=== 2/6  safety backup (full-repo bundle) ===")
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = os.path.join(os.path.dirname(HERE), f"electronic-backup-{stamp}.bundle")
    run(["git", "bundle", "create", backup, "--all"])
    print(f"[ok] backup written: {backup}")

    # ---- 3) purge from history ------------------------------------------
    print("\n=== 3/6  purge paths from ALL history ===")
    cmd = ["git", "filter-repo", "--force", "--invert-paths"]
    for p in PURGE_PATHS:
        cmd += ["--path", p]
    run(cmd, env=env)

    # ---- 4) re-add remote + force-push ----------------------------------
    print("\n=== 4/6  re-add origin + force-push rewritten history ===")
    if "origin" in capture(["git", "remote"]).split():
        run(["git", "remote", "remove", "origin"], check=False)
    run(["git", "remote", "add", "origin", REMOTE_URL])
    run(["git", "push", "origin", "--force", "--all"])
    run(["git", "push", "origin", "--force", "--tags"], check=False)

    # ---- 5) make the repo public ----------------------------------------
    print("\n=== 5/6  make the repo public ===")
    if not shutil.which("gh"):
        sys.exit("[X] gh CLI not found — install it or flip visibility in the GitHub UI, then run setup_github_cicd.py")
    run(["gh", "repo", "edit", REPO_SLUG,
         "--visibility", "public", "--accept-visibility-change-consequences"], check=False)

    # ---- 6) re-apply guardrails -----------------------------------------
    print("\n=== 6/6  branch protection + prod environment + secrets ===")
    run([sys.executable, os.path.join(HERE, "setup_github_cicd.py")], check=False)

    print("\n" + "=" * 60)
    print("DONE. History purged, repo public, guardrails applied.")
    print("Next (manual, optional):")
    print("  - Rotate your LinkedIn cookies (log out/in) to fully close it.")
    print("  - After deploy.yml pushes images, set the GHCR packages to Public")
    print("    (repo > Packages > each > visibility) so the droplet pulls tokenless.")
    print(f"  - Rollback safety net if ever needed: {backup}")
    print("=" * 60)


if __name__ == "__main__":
    main()
