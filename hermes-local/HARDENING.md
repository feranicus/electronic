# Hermes hardening — secure by design, KISS

Single agent. Browser / web / Page-Agent / gateways stay **ON** (you need OSINT), but
they're boxed by three simple things: a **domain allowlist**, **content = data**, and
**no secrets out**. Everything below is either already wired or a one-line action.

## What's already wired (base `docker-compose.yml`)
- **Operating policy** `AGENTS.md` mounted read-only → the behavioural guardrails
  (instructions only from paired users; browse allowlist only, read-only; never expose
  secrets; shell only for the skill; don't self-modify from web; stay bounded).
- **Allowlist** `allowlist.txt` mounted → the only sources the bot should browse/hit.
- **Least privilege**: `no-new-privileges`, `cap_drop: ALL`, `pids_limit`, `mem_limit`.
- **Skill mounted read-only** (scripts can't be tampered with at runtime).
- Secrets only via `.env` → env; never baked into the image, never printed.

## One-time: pick the tools (run once, then `up -d` again)
    docker compose run --rm hermes hermes tools
- **Enable:** web search / fetch, browser + Page-Agent, `execute_code`, the gateways you
  use (Telegram + optionally Discord/Slack/Email).
- **Disable:** image generation, TTS/voice, and any gateway you don't use.
- Set a **user allowlist** on each gateway (only your AEs) — `hermes gateway setup`
  (DM pairing). This is the single most important access control.

## Optional: hard egress enforcement (recommended on the droplet)
Forces all traffic through a proxy that permits only `allowlist.txt` and blocks
cloud-metadata/internal SSRF:

    docker compose -f docker-compose.yml -f docker-compose.hardened.yml up -d --build

Add a source anytime = add one line to `allowlist.txt`, then `up -d` again.

## Droplet backstop (KISS network firewall)
On the DO droplet, in addition (defence in depth):
- Egress: allow only 443/53 out; **block 169.254.169.254** (cloud metadata) and
  RFC1918 from the container network.
- Ingress: 443 from Cloudflare ranges + 22 from your IP only.

## Framework map (why these)
| Control | Frameworks |
|---|---|
| Domain + egress allowlist, metadata/SSRF block | CISA (network segmentation), OWASP LLM01 |
| Content = data, not instructions | OWASP LLM01, CISA secure-by-design |
| Read-only browsing (no login/forms/pay) | OWASP LLM06 (excessive agency) |
| No secrets printed/sent | OWASP LLM02, BSI (secrets) |
| Command-scoped shell | OWASP LLM06 |
| Least privilege container | CISA "Deploying AI Securely", BSI IT-Grundschutz |
| No auto memory/skill writes from web | OWASP LLM04, CSA MAESTRO |
| Rate/step limits + audit | OWASP LLM10, CISA monitoring, BSI logging |
| User allowlist per gateway | CISA/CSA IAM |

## Not done for you (Hermes runtime settings — one-liners above)
Enabling/disabling specific tools and the per-gateway user allowlist are done through
`hermes tools` / `hermes gateway setup` because they live in Hermes' own config, not the
compose file. Everything else is in the files here.
