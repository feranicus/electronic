# cybergod.ai — Project Blueprint

**Purpose of this document.** A complete rebuild specification for the cybergod.ai platform:
what every part does, why it is shaped that way, and in what order to stand it up in a new
directory. Written 15 Aug 2026 from the repository itself, not from memory.

**Two rules this document obeys.**

- **No invented identifiers.** Every file, environment variable, endpoint and container named
  here was read out of the repository. Nothing is approximated.
- **The reasoning is part of the specification.** Most of the guards below exist because a
  specific defect shipped. A rebuild that copies the code and drops the reason will reintroduce
  the defect within weeks. The incident is stated with each rule.

**The one thing to understand before reading anything else.** This system makes claims about
other people's infrastructure and takes automated action against live traffic. Both are
unforgiving. Almost every design decision here is a constraint on what the software is allowed
to conclude or do, not a feature. Read the constraints as the product.

---

## 0. What the product is

A pre-sales and compliance platform for cyber resellers, MSPs and integrators. The operator
types **one input, a company name or domain**, and receives a set of finished customer-ready
deliverables. There are four front doors into the same engines.

| Front door | What it is | Auth |
|---|---|---|
| Web cabinet (`/app`) | React SPA: assessment, compliance, assistant, history | Session cookie |
| Telegram bots | `colt-assessbot` (assessments) and `colt-cassandra` (assistant) | Shared password + emailed OTP |
| Public demo (`/demo`) | Real deliverables built from fabricated data | None |
| Public landing + partners | Marketing, legal, contact | None |

**The product promise that constrains everything:** *not one packet is sent to the company being
assessed.* It is stated on `/partners`, in the Terms of Use, in the Article 13 privacy notice and
in the signed partner pack. Every recon technique must therefore be passive. An active tier exists
but is gated behind written authorisation and is off by default (§4.7).

---

## 1. Repository map

```
/                                   root: operator-facing scripts, ONE orchestrator (ship.py)
├── webapp/
│   ├── backend/app/                FastAPI application (23 modules)
│   ├── frontend/src/               React SPA (6 UI locales)
│   ├── frontend/tools/             build gates (10 scripts, run in CI and in the image)
│   └── Dockerfile                  multi-stage: frontend build + gates, then python
├── hermes-skills/shodan-assessment/
│   ├── scripts/                    THE ENGINE: recon, enrichment, deck builders, tests
│   ├── reference/                  LLM knowledge bases + methodology
│   └── scripts/compliance/         EU + Canada legal reference documents
├── tests/                          21 pytest files (application + governance)
├── deploy/
│   ├── caddy/                      committed reverse-proxy fragments per project
│   └── dbbackup/                   database backup agent (systemd timer)
├── patchwatch/                     unattended OS patching with a reboot gate
├── obs/grafana/dashboards/         committed dashboards, auto-imported
├── .github/workflows/              8 workflows
└── marketing/                      decks, LinkedIn copy, partner pack
```

**Engine location note that matters for the rebuild.** `hermes-skills/shodan-assessment/scripts`
is copied into **two** images (`webapp/Dockerfile` and `assess-bot/Dockerfile`), because both the
web app and the Telegram bot run the engine. An engine change that reaches one image and not the
other produces a system where Telegram has the fix and the website does not. This happened. The
deploy verifier now compares sha256 of the engine files inside **both** containers against the
local files (§7.2).

---

## 2. Runtime topology

One DigitalOcean droplet, FRA1, **4 GB RAM / 2 vCPU / 80 GB**, public IP `64.225.108.200`.
A second identical droplet is the staging twin (§7.3).

```
Internet
   │
   ▼
videodead-caddy  ── owns :80/:443 for EVERY site on the box, TLS via Let's Encrypt
   │                (shared with unrelated projects: VideoDead, jobhuntwow, klima, jev.best)
   ├─ cybergod.ai ──► colt-web:8000   (FastAPI + built React, network: videodead_appnet)
   └─ (other projects' own upstreams)

colt-stack (docker compose project)
   ├─ colt-web         the web app + the engine
   ├─ colt-assessbot   Telegram assessment bot + the engine
   ├─ colt-cassandra   Telegram assistant bot
   └─ colt-promtail    tails /var/log/colt/events.log ──► Loki ──► Grafana

Shared docker volumes (Compose-prefixed: colt-stack_*)
   ├─ colt_events   /var/log/colt/   events.log, cost_ledger.sqlite, reputation.json,
   │                                 shield_tuning.json, authorized.json
   └─ colt_webdata  /data/           colt.sqlite (jobs), demo artifacts, GeoIP db
```

**Three topology rules learned the hard way.**

1. **`colt-web` is on exactly ONE docker network** (`videodead_appnet`), defined in exactly one
   compose file. When it was on two, Docker DNS returned both IPs and the shared proxy randomly
   dialled the unreachable one, producing intermittent 502s.
2. **Never `--remove-orphans`** when deploying a single service into the shared `colt-stack`
   project. `docker-compose.web.yml` defines only `web`; adding that flag deletes promtail and
   both bots, which look like orphans to that file.
3. **Compose prefixes volume names.** The real volumes are `colt-stack_colt_events`, not
   `colt_events`. Resolve a volume's host path by asking the container (`docker inspect .Mounts`),
   never by assuming a name. A backup tool that assumed the unprefixed name found nothing and
   reported success.

---

## 3. Subsystem: the assessment engine

`hermes-skills/shodan-assessment/scripts/run_assessment.py` is the orchestrator. One input, five
deliverables.

### 3.1 Pipeline

```
company name or domain
   │
   ├─ 1. IDENTITY RESOLUTION   shodan_recon.autodiscover()
   │      psl.registrable()        registrable domain via Public Suffix List
   │      asn_sources.discover()   RIPEstat → RIPE DB → CAIDA → PeeringDB → bgpview
   │      _cert_info / _cert_sans  the seed's live TLS cert: subject-O and SAN list
   │      _certspotter_domains     CT logs (SSLMate), paginated
   │      crt.sh                   second CT source (single point of failure otherwise)
   │      group_discovery.crawl()  the customer's OWN group-structure pages
   │      _probe_subdomains()      ~60-name DNS wordlist on brand-carrying apexes only
   │      naming.mine()            learn the target's naming grammar, generate from it
   │
   ├─ 2. SWEEP                 Shodan queries built from the proven identity anchors
   │      + EVERY GUARD IN §3.2 runs here
   │
   ├─ 3. CLASSIFY              classify() → findings with severity + evidence
   │      passive checks: email_auth, cert_intel, CAA, EOL-from-banner
   │
   ├─ 4. ENRICH                enrich.py (serial chain) + enrich_parallel.py (shards)
   │      _audit_cves()         strips any CVE not present in the scan evidence
   │
   ├─ 5. DERIVE                derive_cbiq (FAIR loss model), derive_geopol (threat actors),
   │                           bgp_resilience
   │
   ├─ 6. RENDER                4 pptx decks (pptxgenjs) + 1 animated HTML report
   │
   └─ 7. POST-DELIVERY         audit_fp.py (independent FP auditor, different vendor)
                               clarify.py (deterministic questions → refine run)
                               run_log.py (redacted customer copy of the run log)
```

### 3.2 The ownership doctrine, and every guard that enforces it

**The governing rule: a discovered domain is a CANDIDATE, not proof of ownership.** Recall is
cheap; a stranger's infrastructure in a customer's deck is not. Every guard below exists because
a specific run shipped a specific false positive.

| Guard | What it enforces | The incident that produced it |
|---|---|---|
| `psl.registrable()` | eTLD+1 via the Public Suffix List, never "last two labels" | `budget.gov.ru` collapsed to `gov.ru`, making every Russian ministry one customer: 203 IPs, €11-28M priced |
| `_owns_apex()` | an apex enters scope only via seed apex, brand token, cert-O, or a published group roster | `bibeltv.de` shipped 1,003 IPs for a broadcaster with 5 hosts |
| `_private_ca_ok()` | an issuer signing > `PIVOT_MAX_HOSTS` (2000) globally is shared, not the customer's CA | Let's Encrypt issues under bare codes `R3`/`R10`, read as a private CA |
| `_selector_is_distinctive()` | a brand selector matching > `BRAND_MAX_HOSTS` (2000) is refused | "abakus" is the German word for abacus; `http.html:"abakus"` matched the internet |
| `_org_is_the_target()` | an org string must corroborate the seed brand | a hoster's whois-org became the customer's brand tokens: +582 hosts, all strangers |
| `_org_core()` | truncate at a MID-STRING legal form (position, not a place-name list) | `org:"Lotto24 AG Hamburg, Germany"` matched every Hamburg netblock: +381 |
| `_accept_pivot()` | roll back a whole pivot adding > `max(PIVOT_MAX_ADD=60, 3× identity hosts)` | the lotto24 blow-out again, this time caught structurally |
| per-domain budget | roll back a discovered domain contributing > `max(DOMAIN_MAX_ADD=40, 3× seed)` | one `wa.me` footer link put Meta's global edge in scope: 236 of 348 hosts |
| `scope_deny.py` | shortener / social / SaaS platform denylist, enforced at harvest AND at the gate | same incident; a denylist in one module protects one code path |
| co-tenant guard | a host's own whois-org must corroborate, or it carries the customer's name | a shared Colt /24 put a doctors' pension fund in a property group's deck |
| attribution gate | on provider infrastructure a record must NAME the customer to become a finding | the IONOS elastic-SSL VIP: every Shodan record on the customer's own pinned IP belonged to a co-tenant |
| `_names_the_target()` | pinning proves the ADDRESS is theirs, not every OBSERVATION on it | same |
| `scope_blowout` | abort rather than build decks from an unverified estate | the safety net beneath all of the above |

**Two meta-rules that outrank the individual guards.**

- **Absence of evidence is never a finding.** A failed lookup reports `UNKNOWN / data-unavailable`
  and claims no gap. `bgp_resilience.py` once graded Cogent (a tier-1 transit network) as CRITICAL
  with zero upstreams, purely because container DNS died and an empty list read as "no routing
  autonomy". Every module takes a `discovery_ok` flag for this reason.
- **An empty result is an honest outcome.** "Nothing of yours is externally observable" is a true,
  defensible and saleable result for a company whose whole presence is shared hosting and SaaS.
  The co-tenant guard's old "never empty a deck" valve guaranteed the *worst* deck on the most
  common target shape, and was deliberately inverted.

### 3.3 Fail direction

When a guard is unsure, it takes the **narrower** estate. A narrow estate misses some of the
customer's own hosts, which is a recall bug and recoverable through the clarify loop. A wide one
puts a stranger's infrastructure in the customer's deck, which is not recoverable.

### 3.4 The clarify and refine loop

Deliver first, then ask. `clarify.py` generates **deterministic** questions (never LLM, so they
are auditable and cannot hallucinate a domain), each carrying a machine-actionable `maps_to`.
The operator's answers become CLI overrides on a child run: `--exclude-domain`, `--pin`,
`--platform-operator`, `--notes`, `--asn`, `--net`, `--domain`.

This is the **only sanctioned way scope changes after the first run**. The human asserts the fact,
so the zero-false-positive gate stays intact and the assertion is recorded.

### 3.5 The LLM chain

`enrich.py` takes a **chain**, not a model: `ENRICH_MODELS`, default `deepseek-3.2 →
llama-4-maverick → gemma-4-31B-it`. Per model: `ENRICH_ATTEMPTS` with exponential backoff
honouring `Retry-After`, then failover. The whole chain is bounded by `ENRICH_BUDGET_S`.

Rules that took several outages to establish:

- **The backup must be a different VENDOR.** A 429 is provider-wide; deepseek → deepseek is not a
  backup.
- **Head-weighted budget**, not 1/N. The head gets ~55% of the remaining budget because it is the
  model we want to win. Equal slices capped every model below the job's actual duration and
  produced English decks on a German run.
- **Never issue a request whose completion time exceeds its own timeout.**
  `feasible_max_tokens(seconds)` sizes the request to the slice it was given.
- **Instruct models only.** Reasoning/thinking models break the strict-JSON contract: they emit
  thinking, then truncate.
- **Tolerate any SHAPE, never an EMPTY answer.** `_json()` handles object, `[{object}]`, bare
  array, fenced, trailing prose. `_contract_ok()` then rejects anything under 50 completion tokens
  or missing both `exec_summary` and `findings`. A model returning `{}` in 4 seconds parsed fine,
  was charged for, and shipped an empty deck.
- **A `finish_reason == "length"` is OUR ceiling truncating the JSON**, not a model fault.
- **Per-model required parameters are encoded, not rediscovered.** `MODEL_PARAMS` holds e.g. the
  temperature a model demands and fields it cannot accept. When an API rejects a request, repair
  **what it named**, never whichever field the first regex hits. A blanket "drop response_format"
  once disabled the flag that suppressed chain-of-thought, producing 46,801 characters of thinking
  and a truncated non-answer.
- **Model ids are exact and must be probed, not assumed.** `model_probe.py` runs INSIDE the
  container (where the API key lives) and fails the deploy if any id in the chain is absent from
  the live catalogue. A marketing name (`deepseek-v4-flash`) was put at the head of the chain and
  404'd on every call for days.

### 3.6 No invented identifiers in a customer deck

Two layers, because a prompt rule is a request and not a guarantee.

1. **Prompt guardrails** in `reference/LLM_DELTAS_BIBLE.md`: cite a CVE only if that exact ID is in
   the raw findings; name incident and year instead when unsure; never invent a company, date or
   figure.
2. **`_audit_cves()`**, a post-check that cross-references every CVE in the generated prose against
   the CVEs actually present in the scan evidence. Unverifiable ones are **stripped** (prose kept),
   a warning printed, and `evt=hallucination_guard` emitted. Never silently rewritten.

### 3.7 The independent false-positive auditor

`audit_fp.py` reviews every finding's evidence host using a model from a **different vendor than
the one that actually wrote the deck** (the model that won enrichment after any failover). It
prefers a different vendor, guarantees a different id, and **refuses to audit rather than
self-audit**.

Its authority is deliberately limited: it may FLAG, and a finding is dropped only where the
deterministic owned-set agrees it is off-estate. Hard guardrail: it may never empty a deck and
never drop more than 40% of findings. It once turned a correct run into an empty deck by making
ownership calls with no ownership data. **An audit is a signal, not an authority.**

### 3.8 Deliverables

Four `.pptx` decks (findings, C-BIQ business impact, geopolitical, deltas) plus a bespoke animated
`_GEOPOL_Animated.html` five-scene scrollytelling page, and a redacted run log.

The HTML is assembled from a **fixed shell** (`scripts/geopol_html/skeleton.html`, extracted
byte-for-byte from a hand-authored exemplar) with only text and numbers injected, so the layout
cannot drift. Same doctrine as the locale files in the frontend.

The **run log is a deliverable**: it is the methodology receipt, showing every point where the
engine refused to conclude something. `run_log.py` builds the customer copy through an
**allow-list** of event types and line shapes (a regex redaction is only the backstop), because
the raw log carries the operator's email, internal paths and the cumulative cost ledger.

### 3.9 Document languages

Interface language and **document** language are different capabilities and are deliberately
separated. A deck language needs three things: `scripts/i18n/<lang>.json` (deck chrome), a
`LANG_*` prose block in `enrich.py`, and the `i18n.py` post-pass. `deck_langs.doc_langs()` derives
the list from what exists on disk and **fails closed**: half a language is not a language. It is
served publicly at `GET /api/langs`.

Currently EN, DE, RU. Interface is EN, DE, IT, FR, ES, PL.

**The hard rule: never translate an ENUM.** Severity (`CRITICAL`), actor band, tier, status and
the `COLT` remediation tag are lookup keys matched by the builders. Translating them makes findings
silently vanish (a findings deck fell from 23 pages to 8). They are translated at RENDER time only,
via a label map.

---

## 4. Subsystem: the defence stack (the shield)

This is the part most transferable to another project. It defends the platform itself.

### 4.1 The design split, and why the models are not in the request path

`shield.py` is **deterministic, inline, and contains no model call**. `shield_panel.py` runs the
four models **out of band**. The reasons are stated in the module docstring and are not negotiable:

- a model call is 300ms to 60s. Putting one in front of a request that IS the attack is a denial
  of service, and the panel's own failure modes (429, timeout) become site outages;
- the product's public claim is that the LLM assists and does not decide side effects.

### 4.2 Detection: what the shield accepts as evidence

Weighted signals inside a rolling window (`window_s`, default 300s).

| Signal | Weight | Note |
|---|---|---|
| `honeytoken` | 6 | paths listed in robots.txt as Disallow and linked nowhere. Zero false positives by construction |
| `ua_rotation` | 4 | N distinct browser/OS fingerprints from one address. **Only scores when something else is also wrong** |
| `probe_path` | 3 | 19 pattern classes measured against a real mass-scanning corpus |
| `method_abuse` | 2 | PUT / DELETE / PATCH / TRACE / CONNECT |
| `authz_probe` | 1 | 401 / 403 storm, excluding exempt paths |
| `not_found` | 1 | **only after `NF_DISTINCT` (6) DISTINCT missed paths** |

Three corrections that each came from real traffic:

- **UA rotation proves AUTOMATION, not ATTACK.** This repository's own deploy verifier sends twelve
  user agents from one address to test the bot gate, and the first version blocked it, taking
  `/api/me` to 404 and failing the deploy. Monitoring, uptime checks and CI all look like that.
- **A 404 count alone would have blocked two real people.** Two visitors produced 439 and 362 404s
  while asking only for our own routes. **Variety** is the discriminator, not volume.
- **An exemption from ACTION must never become an exemption from OBSERVATION.** `probe_shape()`
  (pure pattern) is what scores; `is_probe_path()` (shape minus exemptions) is what decides whether
  we may act. When they were one function, `/api/wp-login.php` and `/api/../../etc/passwd` scored
  nothing and `/api/` was a hiding place.

### 4.3 The five safety rails

Each is negative-tested: removing it makes the suite fail.

1. **No firewall call, ever.** Enforcement is HTTP-layer inside one process. A VPN (UDP), SSH and
   four other sites share the host and never pass through it. A test greps the modules (comments
   stripped) and fails on any iptables/nft/ufw call.
2. **Fail open.** Any exception anywhere in the module lets the request through. A control that
   breaks the site is a worse outage than the scanning it prevents.
3. **Everything is time-boxed.** Blocks, holds and modes all expire by themselves. Nothing is
   permanent.
4. **Never-block prefixes:** `/.well-known/` (blocking it turns a scanner into a *certificate*
   outage for every domain on the box) and `/api/` (authentication is the control there; a 401 is
   already a refusal).
5. **Blast cap.** Never block more than `SHIELD_BLAST_CAP_PCT` (20%) of recently seen distinct IPs.
   **A percentage of a handful is not a rate**: with one scanner and one visitor, blocking the
   scanner is 50%, so the cap made the shield structurally incapable of ever blocking anybody on
   exactly this site's traffic profile. `MIN_ABS_BLOCKS` (5) is therefore always permitted.

Plus a sixth for the tarpit specifically: **a naive tarpit is a self-inflicted denial of service**,
because every stalled request holds a connection. `MAX_TARPIT_CONCURRENT` (24) caps it; past the
cap we answer immediately.

### 4.4 The four-model panel and what it may touch

`shield_panel.py`, `MODELS = ["deepseek-3.2", "llama-4-maverick", "gemma-4-31B-it", "kimi-k2.6"]`.
Four vendors deliberately, so no shared failure domain.

The panel may propose values for **six integers**, and only those:

```python
BOUNDS = {
    "tarpit_after":  (3, 25),      "block_after":   (6, 60),
    "window_s":      (60, 900),    "block_s":       (300, 86400),
    "tarpit_ms":     (250, 8000),  "ua_rotation_n": (3, 10),
}
```

- The ranges live in committed code and are enforced by `cfg()` **on every read**, not on write, so
  a hand-edited or corrupted tuning file still cannot escape them.
- A **quorum of 3 of 4** must agree on the direction; the applied value is the **median**, so one
  bold model cannot drag the result; steps over **25%** are refused.
- The panel cannot block or release an address, and cannot touch the blast cap, the allowlist, the
  kill switch or the bounds themselves.

### 4.5 The Telegram attack console: AUTO / ASK / NEVER

`shield_console.py`. The tiering is by **reach**, not by confidence.

- **AUTO** (no question): tarpit, a 15-minute block, an alert. Waiting for human approval on a
  15-minute block means the scan finishes before the phone is unlocked.
- **ASK** (one tap, expires after `SHIELD_ASK_TTL_S` = 2h): hold 24h · block the /24 for 1h ·
  report to AbuseIPDB · strict mode 1h · ban a path permanently · false alarm (release + allow).
  A /24 is up to 256 addresses and may be an office or a mobile carrier, so the shield **honours**
  that state and never **decides** it.
- **NEVER**: scanning back, connecting to their host, any hack-back. Criminal under StGB
  §202a/§202b/§303a/§303b (and §202c covers even the tooling), EU Directive 2013/40, US CFAA
  §1030, Canada CC s.342.1. The address is usually a compromised third party, and one such packet
  ends the "not one packet" promise. **A test fails the build if an offensive action is added.**

Two implementation rules:

- **Separation of processes.** `colt-assessbot` already long-polls Telegram, so it owns the
  callback and RECORDS the decision to the shared volume; `colt-web` ENFORCES it. A second
  getUpdates consumer would steal the bot's messages, and a bug in the bot cannot block anybody.
- **The confirmation is read back out of live shield state after the write.** The first version
  printed "Applied: holding 1.2.3.4 for 24h", which is the same sentence whether or not anything
  happened. Times are absolute UTC, not countdowns. A failed action is reported, never swallowed.
  Apply runs on a **20-second** loop, separate from the 6-hourly panel: applying a decision is a
  file read, deliberating with four models is expensive, and they do not belong on one clock.

### 4.6 Supporting defence modules

| Module | Role |
|---|---|
| `telemetry.py` | one `evt=http` per request: ip, country, method, path, status, ms, ua, browser, os, device, bot, ref, user. Client IP from `CF-Connecting-IP` then the first `X-Forwarded-For` |
| `visitors.py` | human-visit alerts and the bot 404 gate (`BOT_404`) |
| `alerts.py` | 11 sliding-window rules, 15-min cooldown per rule+subject, 12/hour global storm cap. **An alert flood is a second outage** |
| `ip_reputation.py` | offline `classify(ip)` on the request path, `enrich(ip)` via RIPEstat off it; repeat-offender memory keyed on the /24, counting DISTINCT DAYS not burst volume |
| `siege.py` | public live attack feed. Bounded ring buffer, IP truncated to /24 **on the way in**, paths echoed only when they match a strict shape with no query string |
| `attack_digest.py` | daily digest; `unknowns()` surfaces sources the classifier does NOT recognise, because a panel reviewing its own decisions is structurally blind to a new technique |
| `abuse_report.py` | AbuseIPDB submission (opt-in, needs `ABUSEIPDB_KEY`) and a 4-model complaint DRAFTER that reaches no network |
| `threat_intel.py` | deterministic MITRE ATT&CK mapping per alert type. A static table beats an LLM here: free, reliable, unambiguous |
| `security_headers.py` | HSTS, CSP (`script-src 'self'`, no unsafe-inline), X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy; `no-store` on `/api/` |

**Where security headers belong:** in the app, not the shared Caddyfile. One bad edit to that file
took every domain on the box down for six hours. A header belongs to the app that knows what it
serves, ships inside the image (so the engine-hash verify covers it) and is testable in a second.
Install it **last** so it is the outermost middleware and also decorates the 404s the bot gate and
shield return before the app runs.

**A user agent is attacker-controlled; the path they requested is the evidence.** A scanner
announcing itself as Safari/iOS passed the UA-based bot check and triggered "a person just opened
the site" on a path no human has ever typed. Suppression is now by PATH regardless of UA.

**And the mirror of that:** classifying VPN or cloud egress as "not a person" blinds you to your
own tests and to every privacy-conscious prospect. Only **bulletproof hosting and research
scanners** are `never_human`; VPN and cloud visits still alert, labelled "via VPN".

### 4.7 The active tier (built, and switched off)

`active_probe.py` requires `ACTIVE_PROBE=1` **and** `ACTIVE_PROBE_AUTH=<written authorisation
reference>`. Two variables deliberately, not one boolean: a flag says somebody wanted it, a
reference says somebody is accountable, and the reference is what a court, customer or insurer
asks for. It is recorded in the run and printed into the artifact.

Its passive half ships and is the highest-value part: `eol_from_banner()` derives end-of-support
from a banner a scan engine already stored, at zero cost and zero packets.

---

## 5. Subsystem: the web application

### 5.1 API surface (complete, from `main.py`)

```
POST /api/auth/begin              password → emailed OTP
POST /api/auth/verify             OTP → session cookie
POST /api/auth/logout
GET  /api/me                      401 when anonymous (the deploy verifier's canary)
POST /api/assess                  start; returns job id
GET  /api/assess/{job}/events     SSE viewer (tails run.log; does NOT own the run)
GET  /api/assess/{job}/status     polling fallback
GET  /api/assess/{job}/clarify    deterministic post-run questions
POST /api/assess/{job}/refine     answers → flags → child job
GET  /api/assess/{job}/deck/{name}  owner-scoped, traversal-guarded
POST /api/compliance              start (jurisdiction-keyed)
POST /api/compliance/{job}/refine
POST /api/assist                  Cassandra assistant
GET  /api/history
GET  /api/langs                   document-language capability list
GET  /api/jurisdictions           compliance regime capability list
GET  /api/diag                    effective engine config WITH PROVENANCE (authenticated)
GET  /api/demo, /api/demo/deck/{name}   public, engine-free, pre-baked
GET  /api/siege                   public live attack feed
POST /api/privacy/ack             Art. 5(2) accountability record
GET  /{full_path:path}            SPA + static
```

### 5.2 The job model, and why the SSE stream is only a viewer

`POST /api/assess` starts `asyncio.create_task(_run_job(...))`, which owns the run server-side,
writes every line to `<jobdir>/run.log` and finalises the DB row. The SSE endpoint only **tails**
that file.

Before this, the stream **spawned** the engine, so closing a tab, locking a phone or refreshing
killed a five-minute run. Frames carry `id:` (the line number) so the browser replays
`Last-Event-ID` and resumes without duplicates. `es.onerror` must **not** close the EventSource,
or you defeat the browser's own auto-reconnect.

### 5.3 Identity, access and quota

`colt_auth.email_allowed()` is the **single gate** used by both the web app and the bots, so they
can never disagree. Three ways in: a corporate email pattern, a named partner address, or a trusted
domain. Extendable without a code change via `EXTRA_ALLOWED_EMAILS` / `EXTRA_ALLOWED_DOMAINS`.
Domain matching is EXACT, so `x@trusted.io.evil.com` is rejected.

Auth is a shared password **plus** a 6-digit OTP emailed via the Gmail API. **SMTP is blocked
outbound on this droplet; never "fix" this to SMTP.**

`colt_auth.USER_QUOTAS` caps named evaluation accounts. It lives beside the allow-list because
"who may use this" and "how much" are the same question and answering them in two files is how they
drift. **Both front doors enforce it** or the other one is the way around it: the web counts DB
jobs, the bot counts the shared cost ledger. Counting includes failed and running jobs. Both
lookups **fail open**: a quota check must never take an assessment down.

### 5.4 Frontend

React SPA, Vite, no CSS framework. 14 pages, 6 locales, one stylesheet.

- **One language store.** `legal.jsx` owns `getLang`/`setLang`/`subscribe`, read through
  **`useSyncExternalStore`**. A plain `useState` inside a shared hook gives every caller a private
  copy: the toggle changed the header and nothing else until the user navigated. **A value more
  than one component renders is application state, not component state.**
- **Two key spaces, and every string must state which.** `EN`/`DE` keyed by dotted key via `t()`,
  and `DE_BY_EN` keyed by the English source string via `tx()`. Mixing them printed raw keys like
  `q3.h` on the live site in both languages. A gate now fails the build on any dotted key reaching
  the DOM.
- **Long-form content is DATA, not markup.** `partners-locales/*.js` and `legal-locales/*.jsx` hold
  the copy; the component holds zero. A translator cannot move a box because layout is not in the
  file they edit. Fallback is **whole-array**, never per-index, or one locale gaining a section
  silently pairs the wrong heading with the wrong body.
- **An HTML entity in a `t()`/`tx()` string reaches the screen verbatim.** JSX parses entities in
  literal text; a string arriving through a function is escaped. This shipped in five locale files
  at once.
- **A popover inside a sticky ancestor must be portalled.** `z-index` only orders against siblings
  inside a stacking context, and Android promotes `<video>` to a hardware overlay. The More menu
  opened underneath the hero video on one page, on one platform, with identical code.
- **A fixed-height header row is arithmetic.** Add brand + every control + gaps against 360px in
  the LONGEST language before shipping. German and Polish overflow first.

---

## 6. Subsystem: compliance

A second assessment type with the same one-input, deliver-then-refine shape. Grades a company
against a **jurisdiction-keyed** regime set and produces regime decks, a roadmap deck and an
animated HTML report.

`compliance_enrich.JURISDICTIONS` is **one registry**: reference document, ordered regime list, the
subset that gets its own deck, prompt framing, eyebrow. `compliance.json` carries its own
`order`/`decks`/`eyebrow`, so **the deck builders contain no regime constant at all**. Adding a
country is a registry entry plus a reference document. It **fails closed to the EU set**: an
unknown code must never yield an empty regime list, because a deck with no regimes looks finished.

Two jurisdictions today: EU (NIS2, CRA, AI Act) and Canada (OSFI B-13, E-21, B-10, PIPEDA, Quebec
Law 25, CCSPA).

**The reference document's "must never appear" list is a BUILD GATE.** Research produced a list of
claims that would be wrong (a fine attached to a supervisory tool, a penalty for a provision not in
force, an obligation with no live clock). A rule that lives only in a markdown file is a rule the
next edit breaks, so `test_compliance_ca.py` asserts each one against the rendered artifact.

The deterministic fallback holds the FIXED facts (obligations, deadlines, penalty maxima are
company-independent), so the decks are correct with no model at all; only applicability reads
"requires confirmation".

---

## 7. Subsystem: deploy and release governance

### 7.1 ONE ORCHESTRATOR, ONE COMMAND

```
python ship.py
```

Everything else is a building block that `ship.py` calls as a subprocess. They remain individually
runnable for debugging and the operator should never need to.

```
1/5  TESTS          ruff F821/F811/F822 · pytest · 11 engine regression suites ·
                    frontend gates · brand gate · demo-fixture RFC 5737 check
2/5  COMMIT + PUSH  ALWAYS pushes, even with nothing new to commit
3/5  DEPLOY WEB     deploy_web_direct.py (single SSH session, ~90s, self-verifying)
4/5  DEPLOY BOTS    deploy.py --reuse (skipped when the engine hash already matches)
5/5  VERIFY         engine sha256 in BOTH containers · public 401 · caddyguard ·
                    model_probe · secaudit · tag last-known-good · 4-model release notes
```

Flags narrow it (`--test`, `--web`, `--bots`, `--direct`, `--dry-run`, `-m`, `--rollback`,
`--no-stage`, `--no-preview`). **They never split it.** If a reply is about to end with two
`python ...` lines, that is the signal to fold them into the orchestrator.

Rollback: `python ship.py --rollback` resets to the `last-known-good` tag (parking local work in
`git stash`) and redeploys that exact state. The droplet has no independent history; it is always
rebuilt FROM the repo, so a good commit on GitHub is the whole backup.

### 7.2 Verify the DEPLOYED CODE, never just "the site answers"

A fix was committed, tested, pushed, and the re-run still produced the bug, because:
the workflow failed at a late step; `colt-web` stayed **Up 3 days**; the shipper ignored a non-zero
exit and printed DONE; and both verifiers only checked that `/api/me` returns 401, which a
three-day-old container answers perfectly happily.

**A liveness probe is not a deploy proof.** `engine_is_current()` compares sha256 of the engine
files **inside each container** against the local files, for `colt-web` **and** `colt-assessbot`.
On mismatch it self-heals, and if still stale it exits non-zero.

Corollary: **never let a script print DONE on a path where a sub-step returned non-zero.**

### 7.3 The staging twin, and why the reboot is the point

A second identical droplet (same size, image and region, deliberately: latency, host generation and
kernel line are exactly the variables that make "it worked in staging" untrue).

`stagegate.py` deploys to staging using **the same script production uses**, health-checks,
**reboots it**, health-checks again, runs the AI panel, and only then allows production.
`ship.py` exits 2 and touches nothing on NO-GO.

Staging builds its state from committed RFC 5737 fixtures. **No production personal data crosses
over**, so the EU-only hosting claim needs no second location disclosed.

Two defects the gate caught in its own first runs, both worth expecting in a rebuild:

- it never actually deployed to staging, and health-checked a container that had never been put
  there;
- the reboot test waited for SSH to answer, and right after `systemctl reboot` the box is still up,
  so it reported "back after 1s" and passed. It now compares `/proc/sys/kernel/random/boot_id`,
  which is regenerated on every boot. **A test that can pass without the event happening is not a
  test.**

### 7.4 The AI review panel (`quorum.py`)

Four reviewers, one per vendor: two "soldiers", two "auditors". They produce the reasoning and the
risk digest; **the GO/NO-GO comes from the deterministic checks.**

It fails safe in both directions: a 429 cannot block a good release, and an agreeable model cannot
wave through a dead container. One narrow exception, added after it twice meant a check was lying:
a **unanimous** NO-GO (≥3 reviewers, all NO-GO) against a green gate **halts** and requires
`OVERRIDE_PANEL=1`. A split panel does not block.

**Standing rule: what the panel gets right becomes a check in the same change.** Real catches:
identifying a disabled admin API from `d41d8cd98f00` being the md5 of the empty string; noticing
twice that a check's DETAIL contradicted its own VERDICT (the tell for "the check is broken, not
the system"); and the best structural catch, that nothing verified the Caddy **admin API** was
still loopback-only, when that endpoint can replace the running config for every domain on the box.

**And it is wrong often enough to matter.** It has inverted a check's logic, invented a Kubernetes
manifest for a system that has none, and made the same wrong call about one check on three
consecutive runs. That third one was **our** defect: the briefing explained why an old method was
wrong and never said what the check currently does, so a reviewer reasoning from that map landed on
the removed method every time. **Feed the panel more evidence, never more authority; and if a
reviewer makes the same wrong call three times, fix the briefing.**

### 7.5 Deploy immutability

`deploy_web_direct.pack()` packs `git archive HEAD`, the **commit**, not the working directory.

One `ship.py` run once produced three different catalogue counts from "the same" commit, because
the tree was read five times and an editor changed it mid-flight. Staging validated one artefact
and production received another, which makes a green staging run meaningless.

**And `git archive` applies `core.autocrlf`.** It must be invoked as
`git -c core.autocrlf=false -c core.eol=lf archive`, or a Windows packer and a Linux packer ship
different bytes from one commit. Measured, not assumed: `core.eol=lf` alone does nothing.

### 7.6 The shared reverse proxy, and `caddyguard.py`

Five unrelated projects append a managed block into one Caddyfile. That file is now **generated,
not edited**: fragments live in `/opt/caddyguard/blocks/<project>.caddy` and the monolith is
assembled. A project cannot delete another's bytes because it never touches them.

**Config has THREE hops, and a check must say which one it measured:**

```
host file  ──(the bind MOUNT)──►  container file  ──(the RELOAD)──►  running config  ──►  served
```

`caddy validate` validates a fresh temp copy, so it proves nothing about hops 1 and 2. `caddy adapt`
and the admin API both read from **inside** the container, so they agree perfectly on the wrong
config. A single-file bind mount pins the **inode**: once something replaces the file rather than
truncating it, the container reads the old inode forever. Four honest checks all reported success
over a dead site because every one of them measured a hop that was fine.

Therefore: `agent.py mount_sync()` compares host file to container file and refuses to reload into
a stale mount; `agent.py drift` compares the SETS of served hostnames, terminal handlers and path
matchers between disk and the running config (stable under re-serialisation, unlike a byte hash);
`agent.py roster` compares the running config against a **committed** list of expected vhosts;
`agent.py admin` proves the admin API is loopback-only by **probing it from another container**.

Five guardrails, installed by one command and re-run on every ship: fragment isolation ·
write-time validation · a 10-minute watchdog timer (with `OnBootSec`, because a reboot is when
latent damage detonates) · a **reboot gate** in `patchwatch.py` that refuses to reboot into an
invalid proxy config · and an **off-box** uptime workflow, because monitoring that lives behind
the proxy it monitors is mute exactly when it matters.

**In-place writes only** (`open(...,"w")`, never `mv`), or the inode changes and the container
keeps reading the old file.

**And the incident that produced all of it:** a deploy truncated another project's block at
16:15 UTC; Caddy kept serving from memory for 12 hours; unattended patching upgraded the kernel and
rebooted at 04:22; every domain on the box died together. **A latent config is a time bomb, and the
write and the outage are separated by a reboot.**

### 7.7 Backups

`deploy/dbbackup/agent.py`, daily systemd timer plus 5 minutes after boot, `Persistent=true`.

- SQLite's **online backup API**, never `cp` or `tar`. A live WAL-mode file copied with tar may be
  torn mid-transaction.
- **Verified:** `PRAGMA integrity_check` plus per-table row counts. A copy that fails is **deleted**
  and alerted, because a corrupt backup is worse than none: it buys false confidence.
- The row-count invariant is a **WINDOW** (at least what existed before the copy, at most what
  exists after), not equality. The source is live, so exact equality false-alarms on a busy night,
  deletes a good backup, and trains you to ignore the alarm.
- `verify-restore` performs a real restore into a temp directory on every run. **A backup nobody has
  restored is a folder.**
- Finding nothing while the app is running is a **failure**, not a skip. "Nothing to do" and "I
  cannot see my subject" must be distinguished by something external.

### 7.8 Supply chain

Trivy is **pinned** to a version confirmed clean after a real 2026 supply-chain compromise of that
scanner, its tarball sha256 **verified against the signed checksums file before execution**, and it
is **able to fail the build** (CRITICAL exits 1). It previously ran with `--exit-code 0` in all four
invocations while the step name said "flip this to gate".

The internet-facing image was the one image it had never scanned, because that image is built on the
droplet rather than in CI. **The scanner is a supply-chain dependency like any other**: pin it,
verify it, and make it able to fail. A scanner nobody gates on is a log file with a licence.

Also: CI installers must not be fetched from a moving branch. `curl .../main/install.sh | sh` in a
job holding a deploy SSH key is precisely how one open-source project was compromised through
another's poisoned release.

---

## 8. Observability

Every component writes structured JSON events to `/var/log/colt/events.log` on the shared volume.
`colt-promtail` tails it into Loki; Grafana dashboards are **committed** in `obs/grafana/dashboards/`
and auto-imported by a workflow and by `ship.py`.

**The rule that makes it work: never rely on who owns your stdout.** `_ev()` writes to stdout AND
`EVENTS_LOG`. When the engine moved from the bot (whose docker stdout is scraped) into the web app
(where stdout is a pipe read by the SSE viewer), every live assessment silently vanished from
Grafana. If an event must reach Grafana, write it to the log file.

**Failures must be observable.** An unhandled exception once killed the engine before `assess_done`
was emitted, so the dashboard showed "11 requested / 1 completed" with no explanation. `main()` is
wrapped and emits `evt=assess_error` (company, error type, message, source line) to both sinks, then
re-raises so the exit code and traceback are unchanged. **A crash has to be as visible as a success,
or the dashboard lies by omission.**

**Loki is not the books of record.** It ages out, so lifetime cost lives in a SQLite ledger
(`cost_ledger.py`) on the persistent volume, and a cumulative `cost_snapshot` event carries the
lifetime figure so a Grafana panel stays correct after retention drops the old lines.
`--backfill` is idempotent (dedupe on ts+company) so re-running never double-counts.

**Panel titles must state their window.** Mixing "last 24h" and "selected range" on one row is what
looked like a data discrepancy. Stats set `noValue="0"` so quiet is not "No data".

---

## 9. Data and persistence

| Store | Path (in container) | Volume | Holds |
|---|---|---|---|
| Jobs DB | `/data/colt.sqlite` | `colt_webdata` | who ran what, when, language, jurisdiction, status |
| Cost ledger | `/var/log/colt/cost_ledger.sqlite` | `colt_events` | true all-time AI cost per run and per user |
| Events | `/var/log/colt/events.log` | `colt_events` | every structured event |
| Reputation | `/var/log/colt/reputation.json` | `colt_events` | repeat-offender memory, keyed on /24 |
| Shield tuning | `/var/log/colt/shield_tuning.json` | `colt_events` | panel-proposed values, clamped on read |
| Auth store | `/var/log/colt/authorized.json`, `/data/web_authorized.json` | both | authenticated identities |
| Demo | `/data/demo` | `colt_webdata` | pre-baked demo artifacts |
| Job dirs | under `/data` | `colt_webdata` | `run.log`, decks, `clarify.json`, `enrich_last.json` |

Only two of these cannot be regenerated: the jobs DB and the cost ledger. Those are what
`dbbackup.py` protects.

---

## 10. Configuration and secrets

**Secrets never touch git.** They live only in the droplet's `assess-bot/.env` (chmod 600, loaded by
`env_file:`) and as GitHub Actions secrets. `.gitignore` blocks `*.env` and `*_sa.json`; gitleaks
runs in CI.

`python set_secret.py NAME` upserts one key idempotently, restarts `colt-web` and verifies it inside
the container. **The value goes over stdin, never argv** (argv is visible in `ps` and shell history).

Two traps in that script worth carrying over:

- **`bash -s` reads its SCRIPT from stdin**, so it cannot also be the channel for the value. The
  script must travel in argv (base64 into a temp file); stdin stays free for the value. Getting this
  wrong made the droplet execute an API key as a shell command.
- **`deploy.py --reuse` ships the LOCAL `.env` over the droplet's copy**, so a secret written only on
  the droplet is silently wiped by the next bot deploy. `set_secret.py` writes both, local first.

**A value with a documented home in code must not be restated in compose.** The enrichment chain
once had FOUR homes (`_FALLBACKS`, compose `environment:` which beats `env_file:`, `.env
ENRICH_MODELS`, and a legacy singular `ENRICH_MODEL` that silently became the chain head). The
committed default won none of them for weeks. `ship.py` now has a static guard that fails the deploy
if the value reappears in a compose file, and `GET /api/diag` reports the **effective** configuration
**with provenance** so nobody has to guess where a value came from again.

Principal variables: `SHODAN_API_KEY`, `OPENAI_API_KEY` + `OPENAI_BASE_URL`, `BOT_TOKEN`,
`COLT_BOT_PASSWORD`, `GMAIL_SENDER` + `GMAIL_SA_B64`, `ALERT_EMAIL`, `ALERT_TG_CHAT`,
`ABUSEIPDB_KEY`, `EXTRA_ALLOWED_EMAILS`, `EXTRA_ALLOWED_DOMAINS`, plus the `ENRICH_*`, `SHIELD_*`
and `ACTIVE_PROBE_*` families.

**A default IS configuration.** An alert-recipient default in code silently resumed mailing a former
employer's address whenever the environment variable was unset. Removing it from compose was not
enough.

---

## 11. The gate inventory

Everything below is BLOCKING in `ship.py` unless stated. Each was added after a real defect, and
each was proven by reintroducing that defect and watching the gate fail.

**Python / engine**

| Gate | Catches |
|---|---|
| `ruff --select F821,F811,F822` | undefined names. A `NameError` took production down while every unit test passed, because they exercised helpers and nothing executed `run()` |
| `pytest tests/` (21 files) | application, auth, quota, routes, shield, supply chain, governance |
| `test_run_path.py` | EXECUTES `run()` against a mocked Shodan. A stub providing only `.search()` silently yields zero hosts while the engine calls `search_cursor()` |
| `test_recall.py` | 25 sections of recon behaviour |
| `test_scope_abakus.py`, `test_ca_pivot.py`, `test_parity.py` | scope regressions, replayed against real captured exports |
| `test_deck_quality.py` | walks EVERY slide; asserts no body text crosses the footer line |
| `test_compliance_ca.py` | the "must never appear" legal claims list |
| `test_drift.py`, `test_gate_integrity.py` | the gates themselves |
| `test_doc_lang.py` | asserts the RULE (no hand-written language list anywhere on the request path), not one spelling |

**Frontend (also run inside `webapp/Dockerfile`, where the toolchain is correct by construction)**

| Gate | Catches |
|---|---|
| `i18n_catalogue.mjs --check` | 100% coverage in every locale; HTML entities; a string in two key spaces |
| `run_i18n_audit.mjs` | renders 11 pages × 6 languages: raw keys, leaked `undefined`, over-long tab labels, >6% English function-words |
| `api_contract.mjs` | destructuring `{ok, data}` from a getJSON-backed call. `api.js` has two return contracts and both were got wrong |
| `contrast_gate.mjs` | WCAG on the shipped stylesheet; reserved CTA colour; dark surfaces and light text left over from a theme change |
| `header_layout.mjs` | the header row width in all six languages at three breakpoints |
| `canvas_smoke.mjs` | EXECUTES a render loop for 900 frames. `node --check` only parses, and an invalid colour is legal JS until it runs |
| `shipped_shell.mjs` | no source maps, no secrets, no comments in `dist/` |
| `partners_gate.mjs` | prices, unexpanded abbreviations, sentence length, a locale copied from English |

---

## 12. Engineering doctrine

The transferable part. Each line cost at least one outage.

**On checks**

1. **A check that cannot see its subject is not a check.** Recurring in six forms: a gate that
   printed "skipped" on every run for weeks; a validator run against a temp copy instead of the
   mounted file; a validator on a different image version; a probe that could not reach the API key;
   a catalogue check that could not run on the operator's platform.
2. **A check aimed at the wrong element cannot fail.** Grepping the first `className` in a file, a
   regex window too short to reach the field, slicing to the first occurrence of a selector when a
   selector has several rules, asserting a string when the bug is in a condition.
3. **A check must not false-positive on its own comment.** Strip comments before grepping source.
   Learned four separate times.
4. **A gate that only ever goes green is unproven.** Reintroduce the defect, watch it fail, restore.
5. **A negative test that passes because of defence in depth measures the other guard.** Defeat every
   guard on the path before believing it.
6. **A test that depends on a race is not a test.** Force the window deterministically.
7. **Any harness that mutates real files must self-heal on import.** A `finally` cannot survive
   SIGKILL, and a killed run leaves a marker that fails the next run for an unrelated reason.
8. **A fallback that turns an unknown answer into a pass is worse than no check.** One `*) chk … yes`
   wildcard took a NO-GO to 33/33 green.
9. **A PASS whose detail contains failure language is self-contradictory** and is demoted
   automatically. A check reported FAIL while quoting its own pass, and vice versa.
10. **A check's NAME is read far more often than its detail.** A name that promises content while
    measuring ordering is a defect even when the detail is honest.

**On automated judgement**

11. **Code decides side effects; models advise.** Both directions asserted.
12. **The auditor is never the author and never the same vendor.** Refuse to audit rather than
    self-audit.
13. **An automatic process may narrow, never wipe.** Every filter has a blast cap.
14. **Bound the autonomy in committed code, clamp on read, require a quorum, take the median, cap the
    step.**
15. **"The model answered" is not "the model delivered."** Measure the artifact.
16. **When an API rejects a request, fix what it NAMED.** Stripping fields until something works
    disables safeguards you did not know you had. Never discard an error body.

**On evidence**

17. **Absence of evidence is never a finding.**
18. **A signal must be corroborated before it convicts**: brand tokens, UA rotation, org strings,
    certificates, 404s. All the same rule.
19. **Rarity is not ownership**, and a name arriving from infrastructure the customer merely rents is
    evidence about the provider.
20. **Build a detector from one incident, then measure it against the whole log before believing it.**
21. **A diagnostic that does not name its subject sends the next investigation down the wrong road.**

**On process**

22. **ONE orchestrator, ONE command.** A new capability is wired into it in the same change.
23. **A value with a documented home must not be restated elsewhere.**
24. **Follow the value end to end: UI → API → persistence → engine, asserting at each hop.** A
    capability the engine has and the API discards is invisible to every engine test. This happened
    twice, with a language and with a jurisdiction.
25. **Before telling the operator to run anything, ask which machine and which toolchain.** Five
    wasted ships. Prefer a gate inside the container that installs its own dependencies.
26. **Content is content; the byte that ends a line is the platform's business.** CRLF broke a bash
    payload, a deploy artefact, a preview stamp and a test fixture.
27. **Never put a payload in argv**, and when an error names a missing program, check whether the
    command line is what is wrong.
28. **Never delete a RANGE from a shared file using a word that can appear in prose.** A `sed` range
    keyed on "cybergod" started inside another project's comment and truncated their block on every
    deploy for weeks.
29. **The reported line is not the fault: count the delimiters first.**
30. **Read the helper before calling it.** Fifteen invented signatures in one workstream.
31. **Judge a visual by rendering it and looking.** Convert to PDF or PNG and read the image. And for
    UI colour work, look at it on a phone in daylight, since that is the condition it was chosen for.

---

## 13. Rebuild order

Standing this up in a new directory, in dependency order.

1. **Repository and CI first.** Git, `.gitignore` blocking `*.env`, gitleaks, ruff F-rules, pytest.
   Do this before writing code, or the secrets rule is retrofitted.
2. **The engine, offline.** `psl.py`, `scope_deny.py`, `shodan_recon.py` with every guard in §3.2,
   and `test_run_path.py` executing `run()` against a mocked scanner from day one.
3. **The deterministic fallbacks.** Every deck must build correctly with no model available. Write
   these before wiring an LLM, or the fallback path is the one nobody ever renders.
4. **The deck builders**, parameterised, with the i18n wrapper installed at the `addText` boundary
   rather than by hoisting strings.
5. **The LLM chain**, with the contract check, the shape-tolerant parser, the CVE audit and
   `model_probe.py` before anything goes to a customer.
6. **The web app**: auth gate shared with the bots, the job model where the stream is only a viewer,
   owner-scoped downloads.
7. **The frontend**, with the language store as an external store and the locale files as data.
8. **Observability**, writing to a log file rather than stdout, with the dashboards committed.
9. **The shield**, inline and deterministic, with all five rails and their negative tests before it
   is ever enforcing.
10. **The panel**, out of band, bounded, quorum-gated.
11. **Deploy**: single-session SSH, engine-hash verification, commit-based packing.
12. **The staging twin**, including the reboot test.
13. **Backups**, with a real restore verified on every run.

**What to build even though it feels like overhead:** the engine-hash deploy verify, the negative
tests, and `GET /api/diag`. Those three are what stop a rebuild rediscovering this document's
incident list from scratch.

---

## 14. Known gaps, stated plainly

- **Not benchmarked against any named competitor.** The architectural argument is checkable; a
  superiority claim is not made, and comparative advertising against a named product needs
  substantiation under UWG §6 and the UCP Directive.
- **ASN discovery is incomplete for large enterprises.** No public API is authoritative across all
  five RIRs. A real bank announced twelve ASNs and the chain found seven. `clarify.py` therefore
  always asks on a target with its own address space.
- **Vendor tenant space is not proactively enumerated.** A vendor-hosted tenant is found only when a
  certificate or CT record names it.
- **Application-layer checks are not implemented, deliberately.** Reading a customer's HTTP response
  is sending packets to their infrastructure. Adding it requires an explicit per-engagement opt-in
  and the Terms of Use changed in the same edit.
- **The panel quorum can disarm silently.** The unanimous-NO-GO rule needs ≥3 reviewers, and the
  panel has run with 3 of 4 twice. It now announces when it cannot fire.
- **Several P0 items in `docs/SECURITY_ARCHITECTURE.md` remain open**: SBOM and signing, real IAM,
  secrets management, tenant isolation for white-label, audit-log integrity.

---

## 15. Companion documents

| Document | What it holds |
|---|---|
| `CLAUDE.md` | the full incident-by-incident engineering record, ~216 sections. The primary source for everything above |
| `docs/SECURITY_ARCHITECTURE.md` | what we run, what we do not have, what to add (P0/P1/P2), framework crosswalk, 90-day plan |
| `SECURITY_POSTURE.md` | audit of the shield against five specific questions |
| `docs/ARCHITECTURE_OPTIONS_2026-07.md` | why five iterations produced no measurable gain, and the three architecture decisions taken |
| `webapp/DEPLOY.md` | the web deploy pipeline in detail |
| `LANGUAGES.md` | market rationale for the locale set |
| `hermes-skills/shodan-assessment/reference/` | LLM knowledge bases: deltas bible, severity framework, methodology |
| `hermes-skills/shodan-assessment/scripts/compliance/` | EU and Canada legal reference documents |

---

*Written 15 August 2026. Every file, variable, endpoint and container named in this document was
read out of the repository at that date. Figures attributed to incidents come from the run logs and
`CLAUDE.md` records of those incidents.*
