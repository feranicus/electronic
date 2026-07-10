# Project conventions — feranicus/electronic (Colt cyber pre-sales automation)

## Operating principles (standing instructions — always follow)

1. **Full automation, no manual steps.** Every operational task must be a script or a GitHub
   Actions workflow that runs end-to-end. Never leave the user hand-editing files on the droplet,
   clicking through consoles, or copy-pasting multi-step command sequences. If a task needs doing
   more than once, it gets a script.
2. **GitHub is the single source of truth.** All code, workflows, and infra definitions live in
   this repo. The droplet and cloud resources are provisioned *from* the repo (Actions → SSH /
   APIs), never configured out-of-band. To change how something runs, change it here and let CI
   apply it.
3. **Secrets never touch git.** Runtime secrets (API tokens, Spaces keys, bot tokens, the shared
   access password, service-account JSON) live ONLY as encrypted **GitHub Actions secrets** and/or
   in the droplet's own env files (`chmod 600`). `.gitignore` blocks `*.env`, `*_sa.json`, etc.,
   and `gitleaks` runs in CI. The only credential in GitHub-as-code is the deploy SSH key (a secret).
4. **Non-destructive on the droplet.** Never disturb Amnezia VPN / VideoDead(jobhuntwow) / joplin.
   The colt-stack is an isolated compose project (`-p colt-stack`, `colt-*` names). No firewall
   changes. Patch automation only refreshes colt-stack images; other stacks get only shared OS/kernel
   patches.
5. **The LLM assists, it does not decide side effects.** DeepSeek (DO serverless) writes summaries,
   risk digests, and prose. It never decides whether to run `apt`, push, deploy, or reboot — those
   are deterministic code paths.

## The one irreducible human input
Cloud credentials can only be minted by the account owner. Provide them **once** as GitHub secrets;
after that, everything is automated and re-runnable from the Actions tab.

## How things run (all from the repo)
- **Deploy the bots:** `.github/workflows/deploy.yml` — build → Trivy scan → GHCR → SSH deploy
  (deploy job waits for `production` environment approval). Manual: `python deploy.py --reuse --yes`.
- **CI / security:** `ci.yml` (gitleaks working-tree scan, ruff, pytest), `security.yml` +
  `codeql.yml` (Trivy CLI report-only, CodeQL SAST), `dependabot.yml`.
- **Auto-patcher:** `patchwatch/` — backup-first, LLM-assisted droplet updater on a 3-day systemd
  timer. Zero-touch setup via `patchwatch/provision_patchwatch.py` or the
  `provision-patchwatch.yml` workflow.

## GitHub secrets used (set once)
`DROPLET_SSH_KEY`, `DROPLET_HOST`, `DROPLET_USER`, `DO_API_TOKEN`, `SPACES_KEY`, `SPACES_SECRET`,
`PATCH_TG_CHAT` (optional; else auto-discovered). Repo *variables* (non-secret): `SPACES_REGION`,
`SPACES_BUCKET`. Set them with `gh secret set NAME` / `gh variable set NAME`.

## Assessment bot UX — KEEP IT SIMPLE (KISS, standing rule)
The user gives **one input: a company name or domain.** The engine resolves the *entire* recon
anchor block itself — ASNs + prefixes (bgpview.io + RIPEstat), brand domains & subdomains (crt.sh
CT logs), cert subject-O, favicon hash, and the internal-CA issuer pivot (auto-harvested live from
the Shodan sweep's cert issuers). NEVER require the operator to hand-feed `--asn/--net/--issuer/
--cert-org/--favicon` — those exist only as optional overrides. `run_assessment.py` calls
`shodan_recon.autodiscover()`, not bare `merge_variants()`. If a future change makes the operator
type infrastructure details, it's wrong — auto-resolve it.
