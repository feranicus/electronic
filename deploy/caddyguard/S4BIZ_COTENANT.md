# s4biz.io — the sixth project on this droplet

Written from the s4biz.io repository so that anyone working in THIS repository knows what else is
on the box. It is not a duplicate of that project's own documentation; it is only the part that
touches shared infrastructure.

`s4biz.io` went live on 16 August 2026 and was, at that moment, **absent from every monitor here**.
The edits listed at the bottom fixed that. They live in this repository and take effect on the next
`python ship.py` **here**.

---

## What it is

The S4Biz corporate website. React and Vite single-page app, FastAPI serving it, one container. Two
endpoints: `POST /api/contact` and `GET /api/health`. No database, no login, no engine, no bots.

Its own repository holds `ship.py`, `deploy_direct.py`, `dnscut.py`, `import_secrets.py` and
`quorum.py`. Nothing in this repository deploys it.

## What it occupies

| | |
|---|---|
| Container | `s4biz-web`, plus `s4biz-promtail` |
| Compose project | `s4biz-stack`, at `/opt/s4biz-stack` |
| Upstream | `s4biz-web:8000` on `videodead_appnet` |
| Published host port | **none**, deliberately |
| Volumes | `s4biz-stack_s4biz_data`, `_s4biz_events`, `_s4biz_positions` |
| Caddy fragment | `/opt/caddyguard/blocks/s4biz__site.caddy`, markers `# s4biz:site BEGIN/END` |
| Domains | `s4biz.io`, `www.s4biz.io` |
| Secrets | `/opt/s4biz-stack/s4biz.env`, chmod 600 |

**It publishes no host port.** It originally took `127.0.0.1:8091` and the first deploy failed with
*port is already allocated*, because `polara-web` holds it. Needing no port makes that class of
collision impossible rather than unlikely. The proxy reaches it over the docker network and health
checks go through `docker exec`.

`s4biz-promtail` joins `videodead_appnet` **and** the Loki network. That is deliberate and safe:
the one-network rule exists because the shared proxy dials the *web* container by name and would
otherwise pick an address at random. Nothing dials the shipper.

## What it reuses from here

`import_secrets.py` in that repository reads `/opt/colt-stack/assess-bot/.env` **on the droplet**
and copies exactly four keys into its own env file:

```
GMAIL_SENDER   GMAIL_SA_B64   BOT_TOKEN   ALERT_TG_CHAT
```

Everything else is refused **by name**, including `SHODAN_API_KEY`, `OPENAI_API_KEY`,
`COLT_BOT_PASSWORD` and `ABUSEIPDB_KEY`. A marketing site holding an inference key is how the low
value system becomes the easiest route into the high value one. That allow-list is asserted by a
test in the other repository, not left to review.

**If you move or rename `assess-bot/.env`, that import stops working.** It fails safe: the site
serves normally and only enquiry *delivery* stops, because an enquiry is written to disk before any
delivery is attempted. Point it elsewhere with `SECRET_SOURCE=`.

Its release panel uses the same four models and the same `OPENAI_BASE_URL` from that env file, and
sends to the same Telegram chat.

## What changed in THIS repository

Five edits, all so that s4biz.io is visible to the monitoring that already exists here.

| File | Change |
|---|---|
| `deploy/caddyguard/agent.py` | `s4biz.io,www.s4biz.io` added to the `CADDY_EXPECT` default |
| `deploy/caddyguard/agent.py` | `s4biz-web` added to the admin-API probe candidates |
| `caddyguard.py` | `s4biz.io` added to the certificate-expiry loop |
| `caddyguard.py` | `https://s4biz.io/api/health` added to the local probe loop |
| `.github/workflows/uptime.yml` | three off-box targets, plus `s4biz.io` in the certificate loop |

**The roster edit is the one that matters.** An unexpected vhost only warns; a vhost that is not
*expected* can never be reported **missing**. While s4biz.io was off that list, its disappearance,
including from a truncated Caddyfile, would have been invisible.

`caddyguard restore` will now rebuild the s4biz block from
`/opt/caddyguard/blocks/s4biz__site.caddy` like any other, because the s4biz deploy writes that
fragment rather than only appending to the monolith.

## If you need to touch it

Do not deploy it from here, and do not hand-edit the droplet. From the s4biz repository:

```
python ship.py              full deploy and verify
python ship.py --rollback   back to the last known good state
```

Read-only diagnosis from here is fine:

```
docker exec s4biz-web curl -s localhost:8000/api/health
docker logs --tail 50 s4biz-web
```
