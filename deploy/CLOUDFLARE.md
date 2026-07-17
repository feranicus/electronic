# Cloudflare in front of cybergod.ai — plan (KISS, secure-by-design)

## Why
The droplet takes constant WordPress/PHP/.env scanning (see the daily attacker digest). Cloudflare's
free tier drops that at the edge — before it ever reaches Caddy/colt-web — and absorbs DDoS. It is
the single highest-leverage, lowest-effort control here. CISA/BSI baseline both call for a WAF and
DDoS protection on internet-facing services; this satisfies both with one config, no new code.

## What it does NOT touch (important — shared host)
Cloudflare is an HTTP(S) reverse proxy for ports 80/443 ONLY.
- **Amnezia VPN (UDP 44610)** — bypasses Cloudflare entirely. Unaffected.
- **SSH (22)** — never proxied. Keep it on the droplet IP (or Tailscale). Unaffected.
- **VideoDead / jobhuntwow** — they share videodead-caddy on :443, so they ride behind Cloudflare
  too. That is fine (they get the same protection) but is a shared-blast-radius decision: a
  Cloudflare misconfig affects all sites on this host. Proceed knowingly.

## Architecture after
```
Internet ──► Cloudflare (WAF, bot-fight, rate-limit, DDoS, CF-IPCountry)
                   │  only clean HTTPS
                   ▼
        droplet 64.225.108.200 :443  ──► videodead-caddy ──► colt-web:8000
Amnezia VPN (UDP) and SSH go straight to the droplet IP, NOT through Cloudflare.
```

## Who does what
| Step | Who | Why |
|---|---|---|
| Create the Cloudflare account | **You** | it is your identity |
| Add the site `cybergod.ai` | **You** | 2 clicks |
| Move nameservers at GoDaddy | **You** | only the domain owner can — the one irreducible step |
| DNS records, TLS mode, WAF rule | **`python cloudflare_setup.py --apply`** | config as code, idempotent |
| App reads real client IP + country | **already done** | `CF-Connecting-IP` / `CF-IPCountry` in telemetry.py |

```
# after the account exists and the site is added:
$env:CF_API_TOKEN="<scoped token>"       # PowerShell
python cloudflare_setup.py --dry-run     # shows every change, touches nothing
python cloudflare_setup.py --apply
```
Scoped token (least privilege) — dash.cloudflare.com/profile/api-tokens -> Create Custom Token:
`Zone:DNS:Edit` + `Zone:Zone Settings:Edit` + `Zone:Zone WAF:Edit` + `Zone:Zone:Read`, scoped to the
single zone `cybergod.ai`. Store it like any secret: `python set_secret.py CF_API_TOKEN` (never git).

## One-time human steps (Cloudflare, free plan)
1. Add the site `cybergod.ai` to a Cloudflare account (dashboard → Add site).
2. Cloudflare shows two nameservers. At **GoDaddy** → cybergod.ai → Nameservers → **change to the
   Cloudflare pair**. (This is the one irreducible human step — only the domain owner can move NS.)
3. In Cloudflare DNS, set:
   - `A  @   64.225.108.200   Proxied (orange cloud)`
   - `A  www 64.225.108.200   Proxied`
   - `A  ssh 64.225.108.200   DNS only (grey cloud)`  ← so SSH bypasses CF, optional convenience
4. SSL/TLS mode → **Full (strict)** (Caddy already serves a valid Let's Encrypt cert).
5. Security → **WAF → Managed Rules ON**; **Bot Fight Mode ON**; a rate-limit rule:
   `(http.request.uri.path contains ".php" or contains "/wp-" or contains "/.env"
     or contains "/.git")  →  Block`.  That one rule kills today's entire digest.
6. Network → **True-Client-IP / restore original visitor IP** is automatic via `CF-Connecting-IP`,
   which `telemetry.client_ip()` now reads first. The `country` field auto-fills from `CF-IPCountry`.

## App side — already done in code (nothing to change on deploy)
- `telemetry.client_ip()` trusts `CF-Connecting-IP` when present, else the existing X-Forwarded-For.
- `country` uses `CF-IPCountry` first, DB-IP as fallback.

## Optional hardening (later, not required for KISS)
- Lock the droplet firewall so :80/:443 accept ONLY Cloudflare's published IP ranges (defeats
  attackers hitting the origin IP directly). NOTE: this is a firewall change — Amnezia VPN shares
  this host, so scope it to tcp/80,443 ONLY and never touch the VPN's UDP rule. Do it deliberately.

## Rollback
Point GoDaddy nameservers back, or flip the DNS records to "DNS only" (grey cloud). Instant.
