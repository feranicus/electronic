# Security posture — what is in place, what is not, and why

Audited 10 Aug 2026 against the operator's five questions. Every "yes" below is backed by a
committed test or a file you can open; every "no" is stated plainly rather than softened. The
scope limits are the important part — a control that protects one of five sites is not "protected".

## 1. Do the smoke tests cover the new attacks?

YES for everything measured, and the gate is BLOCKING (`python ship.py` refuses to deploy):

| Covered | Where |
|---|---|
| 42-path mass-scanning corpus (OWASP OAT-014, CISA, honeypot feeds) | `tests/test_shield.py` |
| The real 10 Aug UA-rotating scanner, replayed request by request | same |
| The real webshell campaign paths from our own log (`alfa.php`, `lock360.php`, …) | same |
| `/api/` hiding place · single-encoded dot · 404-only false positive | same |
| Five safety rails, each proven to FAIL when removed | same |
| The shield is actually WIRED into the middleware, and the panel is scheduled | same |
| Every shield event appears in Grafana | same |

NOT covered, honestly: the Next.js reconnaissance from the 185.177.72.x cluster (`/_next`,
`/__rsc`, `/__nextjs_action`) is deliberately NOT a detector. Those are 404s for a framework we do
not run; they are caught by 404-variety instead. Making them a signature would be fitting a rule to
one campaign.

## 2. Best-practice defences and open-source tooling

IN PLACE — verified by file:

| Control | Where |
|---|---|
| Behavioural scanner detection + tarpit + timed block | `webapp/backend/app/shield.py` |
| Bot gate (404 to crawlers, humans + search engines served) | `visitors.py` |
| Zero-trust auth: shared password + emailed OTP, per-user quota | `colt_auth.py` |
| Secret scanning in CI | gitleaks, `.github/workflows/ci.yml` |
| Container CVE scanning | Trivy, `security.yml` |
| Static analysis (SAST) | CodeQL, `codeql.yml` |
| Dependency updates | `dependabot.yml` |
| Off-box uptime + certificate expiry | `uptime.yml` (runs outside the failure domain) |
| Unattended patching with a reboot gate | `patchwatch/` |
| Shared-proxy integrity, self-heal, watchdog | `caddyguard.py`, `deploy/caddyguard/agent.py` |
| RFC 9116 security.txt | `public/.well-known/security.txt` |

NOT IN PLACE — measured, not assumed (`grep` returns nothing for all four):

| Missing | What it would buy | Cost |
|---|---|---|
| **OWASP Coraza + Core Rule Set** | SQLi/XSS/LFI/RCE detection for ALL five sites | rebuild the shared proxy |
| **CrowdSec + bouncer** | community IP reputation, ~millions of known-bad addresses | same |
| **Cloudflare** | volumetric DDoS absorbed off-box; WAF; real client country | one nameserver move |
| **fail2ban on SSH** | port 22 is open to the internet with only OpenSSH's own throttling | low risk, do it |
| **AbuseIPDB reporting** | outbound community contribution | just needs `ABUSEIPDB_KEY` |
| **Backups of the persistent volumes** | jobs DB, cost ledger, auth store have NO backup | low risk, do it |
| **SBOM + signed images** | supply-chain provenance | moderate |

## 3. Observability

Grafana rows: colt-web health · Visitors · Security · **Active defence** (added 10 Aug — before
that the shield was invisible: six event types, zero panels). Loki holds every `evt=` line;
promtail ships from the shared volume. Off-box uptime every 10 minutes.

GAP: nothing checks whether **videodead-caddy itself** is alive. `container_running` only watches
colt-web. Caddy dying takes all five domains down at once and would be noticed by the external
uptime check, but not by any local one. Raised twice by kimi-k2.6; still open.

GAP: four vhosts are served that are NOT on the committed roster — `jev.best`,
`klimaanlage-montieren.de` and their www forms. On a shared proxy an unexpected vhost claims
traffic and certificates for a name nobody committed. Add them to `CADDY_EXPECT` or find out who
wrote them.

## 4. Are detections connected to responses?

YES, for cybergod.ai: detect → tarpit → timed block → Telegram menu → operator tap → applied,
with every step time-boxed and reversible.

**NO, for the other four sites.** godeyes.ai, jobhuntwow.com, klimaanlage-preise.de and jev.best
share the proxy but have no shield — enforcement lives inside colt-web. That is the honest limit of
the tier-1 design, and it is exactly what Coraza/CrowdSec at the proxy would fix.

## 5. Is it all connected to the four models and Telegram?

| Path | Models | Telegram |
|---|---|---|
| Release notes, every deploy incl. failures | 4 | yes + email |
| Staging gate, every deploy | 4 | in the ship log |
| Attack console (immediate) | 4 headlines | yes, with buttons |
| Shield review (every 6h, bounded tuning) | 4 | yes + email |
| Assessment FP audit | 1 auditor, different vendor from the author | in the deck |

The models never decide a side effect anywhere in that table. Code decides; they explain, review
and — within `shield.BOUNDS` only — nudge six integers.
