@echo off
REM Auto-generated: clean commit + push of the CI/CD work to feranicus/electronic.
REM All output is captured to push_log.txt so it can be reviewed afterwards.
cd /d "C:\Python SW\Linkedin Scraper"
set LOG=push_log.txt
echo ==== push_to_github started %DATE% %TIME% ==== > "%LOG%"

REM 1) Clear the stale git lock the sandbox could not remove
if exist ".git\index.lock" del /f /q ".git\index.lock" >> "%LOG%" 2>&1
del /f /q "_wtest.tmp" >> "%LOG%" 2>&1

REM 2) Stop tracking accidentally-committed secret + bloat (files stay on disk)
git rm -r --cached --quiet venv >> "%LOG%" 2>&1
git rm --cached --quiet linkedin_cookies.json >> "%LOG%" 2>&1
git rm --cached --quiet "debug_no_results_*.html" >> "%LOG%" 2>&1
git rm --cached --quiet "Colt cyber pre-sales automation _ single source of truth _ feranicus_electronic@0db6dfb.pdf" >> "%LOG%" 2>&1

REM 3) Stage everything intended, excluding the two nested git repos
git add -A -- . ":!feranicus" ":!jobhuntwow.com" >> "%LOG%" 2>&1

echo ---- staged files (non-venv) ---- >> "%LOG%"
git diff --cached --name-status | findstr /V "venv/" >> "%LOG%" 2>&1

REM 4) Commit
git commit -m "CI/CD: GHCR build-scan-push + CodeQL SAST; repo hygiene" -m "- deploy.yml: build images, Trivy-scan the actual image, push to GHCR (SHA+latest), one-command rollback via workflow_dispatch" -m "- codeql.yml: Python + JavaScript SAST on push/PR/weekly" -m "- security.yml, dependabot.yml, ci.yml: DevSecOps pipeline" -m "- docker-compose.ghcr.yml + deploy.py --ghcr: registry-based droplet deploy" -m "- OpenTofu IaC (tofu/), tests/, zero-trust colt_auth + Gmail API OTP" -m "- Untrack accidentally-committed venv/ and linkedin_cookies.json" >> "%LOG%" 2>&1

REM 5) Push (uses Windows cached GitHub credentials)
echo ---- pushing ---- >> "%LOG%"
git push origin main >> "%LOG%" 2>&1

echo ==== done rc=%ERRORLEVEL% %DATE% %TIME% ==== >> "%LOG%"
type "%LOG%"
