# The security, observability and alerting stack, end to end

> A deep dive for porting this into another project. Everything described here runs in production
> across five sites on one host: cybergod.ai, jobhuntwow.com, jev.best, klimaanlage-preise.de and
> s4biz.io.
>
> The companion document `VISITORS_BOTS_AND_TELEGRAM_ALERTS.md` covers layers 2 and 4 in code-level
> detail. This one is the whole picture and the reasoning.
>
> Version 1.0 · 21 September 2026

---

## 0. The five sentences that govern everything

1. **The header is attacker-controlled. The path is the evidence.**
2. **A claim is evidence only when contradicting it costs the attacker something.**
3. **Models propose, code decides.** No language model ever causes a side effect.
4. **Absence of evidence is never a finding.** A failed lookup reports "not determinable", never a gap.
5. **Fail open.** Every error in a detection path resolves to allow.

If you port nothing else, port those. Every design decision below is one of them applied.

---

## 1. The shape of it

Seven layers. Each is independently useful and none depends on the one below being perfect.

```
  7  PERIMETER        security headers, auth, authorisation audit, SPA probe guard
  6  OBSERVABILITY    structured events -> log shipper -> Loki -> Grafana + a fleet page
  5  AUTONOMY         three timed loops, a four-model panel, a promotion gate
  4  ALERTING         Telegram with cooldown, storm cap, action buttons
  3  ENFORCEMENT      tarpit, timed block, blast cap, kill switch, always reversible
  2  CLASSIFICATION   is this a browser or a script, in three buckets
  1  DETECTION        what did this client ask for, and how varied were the misses
  ---------------------------------------------------------------------------------
  0  THE EVENT RECORD one structured line per request. Everything above reads it
```

**Build them bottom-up and stop wherever the value runs out.** Layers 0 and 1 give you most of the
benefit for a day of work. Layer 5 is weeks and only pays off once you have traffic worth learning
from.

---

## 2. Layer 0: the event record

One JSON line per request, written to **stdout and to a shared file**. Everything else in the stack
is a consumer of this line, which is why it is layer zero rather than part of logging.

```json
{"evt":"http","ts":1758441600,"service":"jhw-web","ip":"203.0.113.77","method":"GET",
 "path":"/wp-login.php","status":404,"ms":3,"ua":"Mozilla/5.0 ...","bot":false,
 "sf":0,"hv":"1.1","hvs":"s","av":0,"ref":"","lang":"en","country":"DE","user":""}
```

Two rules that cost us real incidents:

**Write to the file explicitly, never rely on owning stdout.** The log shipper tails a file. If you
assume your process owns stdout you will discover otherwise the day something wraps it, and by then
the evidence is gone.

**Prove the write on deploy.** Our container runs as a non-root uid and every append silently failed
for a week. The deploy now writes a `deploy_probe` line and fails if it cannot. A log pipeline that
has never been observed working is off.

### Fields, and why each earns its place

| Field | Feeds | Note |
|---|---|---|
| `ip` | everything | From `CF-Connecting-IP`, then first `X-Forwarded-For`, then `X-Real-IP`, then the peer |
| `path` | layer 1 | Path only. Truncate it |
| `status` | layers 1, 4 | **The scanner rules are gated on 404. See section 11** |
| `ua` | layer 2 tier 0 | Labelling only, never judgement |
| `bot` | layer 2 | Derived from `ua` |
| `sf` | layer 2 tier 2 | Bitmask of which fetch-metadata headers were present. Presence, never values |
| `hv` / `hvs` | layer 2 tier 3 | Protocol version, and **whose** version it is |
| `av` | layer 2 tier 4 | Distinct assets this address fetched recently. One-way positive |
| `country` | reporting | Resolved offline from a local database. No geolocation service is called |
| `user` | layer 4 | Signed-in identity, for the session rules |

Use **milliseconds** for `ts`. One-second granularity destroys inter-arrival timing, which is the
strongest behavioural signal you will ever have, and you cannot get it back later.

---

## 3. Layer 1: detection

### Path shape

Every request is classified against a table of attack-shape regexes: WordPress, PHP probes, `.env`
and `.git`, admin panels, traversal, SQL injection, cross-site scripting, shell and remote code
execution, backup files, cloud credentials and metadata, build files, debug panels, appliance
interfaces. Twenty-two classes in our table.

**Classification is regex, not inference.** It runs on the request path, it is microseconds, and no
model call is ever in the request path. A model call is 300 ms to 60 s; in front of a request that is
itself a denial of service, that is the outage.

### Variety, not volume

This is the single most important rule in the detection layer.

A real visitor misses the same few stale paths over and over. A scanner misses hundreds of different
ones. So a source scores only after it has missed on **six or more distinct paths**, and a separate
slow rule needs **twelve distinct misses in twenty-four hours**.

Both numbers came from measurement, not taste:

- The two heaviest genuine visitors in one log had **439 and 362** 404s each, every one on real
  routes. Volume alone would have banned two real people.
- The three biggest hostile sources ran at about **0.55 probe requests per five-minute window**, slow
  enough to enumerate **319 distinct paths** without ever tripping a rate threshold.

One measurement sets the floor. The other sets the ceiling.

### Honeytokens

The only zero-false-positive signal available. List a handful of paths as `Disallow` in
`robots.txt`, link them from nowhere, and a request for one is either a deliberate scan or a crawler
ignoring robots. Either way it is not a customer.

---

## 4. Layer 2: classification

Full detail in the companion document. The summary:

Four tiers of evidence, ranked by what it costs an attacker to fake them. Three buckets, never two:
**visitor**, **client**, and **not determinable**. Precedence runs one way: an address seen once as
a bot or once contradicting itself is a client for the whole window, and nothing promotes it back.

The one design rule worth repeating here: **asset correlation only ever confirms.** Fetching the
page then the bundle and the fonts proves a browser engine rendered it. Fetching nothing proves
nothing, because a first visit, a cached repeat visit and an inline page all legitimately fetch
nothing. A signal that can only promote cannot produce a false accusation.

---

## 5. Layer 3: enforcement

Four properties, and they matter more than the blocking itself.

**Everything expires by itself.** Tarpit first, then a timed refusal. Nothing the shield does on its
own is permanent and nothing needs a human to undo it. Manual release forgives the history that
caused the block, not just the timer, because releasing somebody who is instantly re-blocked is not
a release.

**It cannot cause a mass outage.** A blast cap refuses to block more than a fixed share of recently
seen distinct visitors, above a small absolute floor. Over the cap the verdict degrades to a tarpit.
An automatic control that can cause an outage is worse than no control.

**Two prefixes are never blocked.** The ACME challenge path, because blocking it turns a scanner
into a certificate outage for every domain on the host. And the API prefix, because authentication
is already the control there and a 401 is already a refusal. **An exemption from enforcement is
never an exemption from observation**: a separate test asserts the API prefix cannot become a hiding
place.

**An authenticated session is never blocked and never tarpitted.** The evidence is still recorded.
Refusing a real page locks a real person out, and the evidence is unchanged either way.

Plus: it never touches a firewall. Enforcement is HTTP-layer, inside our own process. Refusal is
**429 with Retry-After**, never a 404, because a defence that lies about why it refused makes its own
logs useless.

### Two switches, and they are not the same switch

`ENFORCE=0` stops enforcement and keeps detection, telemetry and reporting. This is what a pilot runs
on. `ENABLED=0` stops the middleware entirely including the event write, so observation stops too.
Confusing them during an incident is expensive.

---

## 6. Layer 4: alerting

Telegram plus email, sent independently so one failing cannot silence the other.

Twelve rules, each with a threshold and a window, every threshold an environment variable:
distributed flood, single-address burst, path probing, directory brute force, authorisation probing,
download burst, session seen from several addresses, failed logins, password spray, one-time-code
brute force, new address for a known user, expensive-operation burst.

**Cooldown of 900 s keyed on (rule, subject), and a storm cap of 12 per hour across all rules.** Key
the cooldown on the pair, not the rule alone, or one noisy address silences the alert for a
different address that matters.

**Log every alert and every suppression.** When somebody asks why they did not get an alert, the
suppression line is the answer.

### Three tiers of action

| Tier | What | Why it sits there |
|---|---|---|
| AUTO | Tarpit, timed block, alert | Reversible, time-boxed, expires by itself. Waiting for a human means the scan finishes first |
| ASK | Hold 24 h, block a network, report abuse, ban a path, false alarm | Longer reach or a real cost. A /24 can be a whole office or a mobile carrier |
| NEVER | Scanning back, connecting to the attacker, any hack-back | Criminal. There is no button and there will not be |

ASK items reach a named human with the evidence attached and **expire unanswered after two hours**.
The confirmation is read back out of live state: after a tap, re-read the actual expiry and the
actual list size and report those. Silence after a tap is indistinguishable from success.

On the NEVER tier: German StGB §202a, §202b, §303a, §303b and §202c (which covers creating the
tooling), EU Directive 2013/40, US CFAA §1030, Canadian Criminal Code s.342.1. The attacking address
is usually a compromised third party, so the lawful answer and the effective answer are the same
answer: a complaint to the provider, drafted automatically and filed by a person.

---

## 7. Layer 5: autonomy

Three timers, three verbs. This is the layer you add last.

| Loop | When | What it may change |
|---|---|---|
| Per incident | every 10 min | Propose into **detection only**. No path to blocking exists |
| Daily | 04:40 UTC | Score yesterday, demote what misfired, mine candidates, promote what earned it, tune, publish |
| Weekly | Sunday 05:20 UTC | Re-vet every live rule against **this week's** routes, retire what a month never matched |

### The promotion gate

A rule moves from watching to blocking only when **all five** are true:

- at least **24 hours** in detection
- **three of four** reviewers agree, one model per vendor
- at least **one** confirmed hostile match in real traffic
- **exactly zero** matches against traffic actually served
- it passed five fail-closed barriers first

The fourth is absolute. **One legitimate hit kills a candidate permanently**, and the code carries
the comment that no number of good days earns it back.

A worked example from production: a candidate rule had 79 hostile hits behind it, which is tempting
evidence. It also had 134 hits from real visitors. Refused outright. Four models proposed it and
arithmetic killed it.

### Why the weekly loop exists

Attack patterns do not go stale. **Your application moves.** A rule matching `/@fs/` was a clean
attack signature in July; by September it matched 99 paths the build output serves. The weekly
re-vet caught it before a customer did. Five rules retired that week.

### Vetting a model's proposal as untrusted input

Five barriers, each fail-closed: it compiles; it matches nothing we serve; it is not catastrophically
broad; it has at least three characters of literal text after stripping regex punctuation; and it is
cheap, measured by running it against a deliberately hostile string with a 25 ms ceiling. A rule that
can be made to hang is a denial of service the customer installed on purpose.

### Four models, four vendors

Not four models. Four **vendors**. A rate limit is account-wide and provider-wide, so falling back to
the same vendor buys nothing, and a four-model panel on one vendor is four hats on one head.

The panel is advisory in **both** directions: it can neither block a good change nor wave through a
bad one. One week it answered zero times out of four because vendors were down. Nothing broke. **A
security control that stops working when a language model is unavailable is a single point of failure
with a friendly personality.**

Cost is capped before the request is issued, not after: three incidents per run, twelve per day, and
a hard daily spend ceiling. The meter fails **closed** here, deliberately opposite to everything
else: an unreadable meter means no spend, not unmetered spend.

---

## 8. Layer 6: observability

Structured events to stdout and a shared file, a log shipper tailing that file, Loki holding it,
Grafana on top, plus a fleet page that answers "is it actually working" for every project at once.

### Heartbeats

Each sidecar writes a heartbeat file every 60 seconds. That is how the fleet page distinguishes "no
attacks" from "not running", which are the same number and completely different facts.

### State words, and why they are words

| Field | Values |
|---|---|
| Sidecar | active · stale · not installed · unverifiable |
| Enforcement | unknown · none · armed · empty · active |
| Autonomy | active · partial · off · unknown |
| Alerting | active · off · unknown |

Every one of those enums has an **unknown**. A status page that cannot say "I do not know" will
invent an answer, and the invented answer is always the reassuring one.

`active` on the autonomy word requires all of: a published ruleset newer than 48 hours, a weekly
state file newer than 8 days, and a watch state file newer than an hour. Anything less is `partial`
and the page says which one is missing.

### Prove the brain, do not ask it

Our nightly loop ran from a path that existed on the host and not inside the container. It died on a
missing file every night for weeks while the installer printed "daily cycle armed", and five sidecars
enforced an empty list the whole time.

The installer now **asks the container, at the path the clients read**, for a published ruleset newer
than 48 hours, and exits non-zero if it cannot get one. A check that reports "armed" without asking
for the artifact is not a check.

---

## 9. Layer 7: the perimeter

### Security headers

Ten of them: content security policy, strict transport security, `nosniff`, frame options, referrer
policy, permissions policy, the two cross-origin isolation headers, cross-domain policy, and
`no-store` on responses carrying personal data.

**Do not copy another site's content security policy.** Read what your frontend actually loads. We
ported ours between two sites and it would have killed the landing page, which serves a large inline
script block. The fix was to scope the policy per path and pin the inline block by hash. Note that
under CSP level 3 a hash **disables** `unsafe-inline`, so you cannot list both as belt and braces.

### Authorisation is server-side on every route

Hiding a menu item is presentation, not a control. Anyone can issue the request the menu would have
issued. Every functional route carries a dependency that reads authorisation **from the store on
every request**, never from the cookie.

Then prove it: an audit script fetches every route anonymously and asserts each one refuses. Wire it
into the deploy. In a framework where a route is public unless somebody remembers, an open endpoint
is a matter of time.

### The probe guard, which is layer 7 feeding layer 1

If your application is a single-page app with a catch-all route, it answers **200** to
`/wp-login.php`. Section 11 explains why that quietly disables most of this stack. The fix is to
return 404 for probe-shaped paths, using the same path table layer 1 already owns rather than a
second one.

Be conservative: a false positive here is a real user getting a 404 on a real page. Keep a corpus of
your genuine client-side routes and assert in a test that **none** of them is ever refused.

---

## 10. Porting order

Ordered by value per hour of work.

1. **The event record.** One line per request, to a file, proven on deploy.
2. **Bot labelling.** The honest-client table. An afternoon.
3. **Security headers.** One file, ten headers, adjust the policy to your origins.
4. **Path-shape detection plus the variety rule.** Now you can see what is happening.
5. **Telegram alerting** with cooldown and storm cap. Send yourself one real alert and confirm it arrives.
6. **The probe 404 guard**, if you serve a single-page app.
7. **Client classification**, tiers 2 and 4. Fixes your visitor numbers.
8. **Enforcement**, detection-only first, for thirty days.
9. **The authorisation audit**, wired into the deploy.
10. **The autonomous loops.** Only once there is traffic worth learning from.

Stop whenever the value runs out. Most projects should stop at 6.

---

## 11. The failure modes we actually hit

This section is worth more than the rest of the document. Every one of these shipped, looked fine,
and was wrong.

### The status-code trap, and it is the subtle one

A site logged 4002 requests, 320 of them scanner-shaped, and raised **zero alerts** in 24 hours,
while a sister site raised 25 on a quarter of the traffic. Everything looked healthy: sidecar active,
autonomy active, alerting active.

The cause: the scanner rules are gated on `status in (404, 403)`, and the application is a
single-page app whose catch-all returns **200** for every unknown path. The detector was pointed at a
condition the application could not produce. The zero was arithmetically correct and diagnostically
worthless.

It cascaded further than the alerts. The local shield has a catch-all detector: after three
probe-shaped paths answered 2xx it concludes the app serves everything and disables enforcement
permanently, with an honest log line nobody was reading. **Three scanner requests after every
restart.** That shield had almost certainly never blocked anything.

**The lesson generalises:** when a counter reads zero, prove the detector can reach a non-zero
state before believing the zero.

### A check that cannot fail is not a check

We wrote an HTTP/2 contradiction check: a client claiming modern Chrome but speaking HTTP/1.1 is
lying. Sound idea. But the reverse proxy terminates TLS and opens a fresh upstream connection, and
the application server implements no HTTP/2 at all, so the version the app sees is **1.1 for
everybody**. The check would have fired on 100% of real browsers.

It now records **whose** version it is, and stays dormant until the proxy forwards the client's.

Related, and the reason we now mutation-test: a cosmetic pass in a deck builder looked for a
paragraph with exactly two runs, the framework produced three, it matched nothing, and the build
printed "built" and exited zero for weeks.

### The same bug fixed in one of its two homes

Telegram rejects an entire message with HTTP 400 if Markdown entities are malformed. Alert bodies
carry attacker-controlled paths, so one probe for `/wp-admin/_x` kills the alert. We found this,
fixed it in the notification module, and wrote it down.

The path actually wired to the HTTP alert rules was a **different file**, and it never got the fix.
It went unnoticed because that site had never produced a security alert, so it had never been
observed. It would have failed on the first one.

**Grep both repositories for the shape of a defect, not just the file you found it in.**

### Two writers, one counter

Two middlewares each emitted an `evt=http` line for every request with different field sets. Every
number on the status page for that project was roughly double. Nobody noticed because the numbers
were plausible.

### A string mismatch makes a control invisible

The shield in the main app emits `shield_block`. The sidecar copied into four other projects emits
`perseus_shield_block`. The fleet page counted only the first. A block on any of the four sibling
projects was invisible in the alert column, forever.

### The threshold guarding a route that does not exist

A download-burst rule keyed on a path prefix from a different product. It guarded nothing, while the
payload actually worth guarding was candidate CVs on a route the rule had never heard of.

### Counting addresses and calling them people

`len(set(ip))` over the log, labelled VISITORS on an admin page. One `curl` is one visitor. The
`bot` field was in the same record and was never read.

### A synthetic test that pages the operator

Our staging gate sends real probe paths at the staging container to prove the alert chain works. The
first version would have sent the operator a security alert **on every single release**, which is
exactly the benign-every-time failure that trains people to ignore alerts. It now suppresses the
delivery, keeps the detection, and leaves a line saying the delivery was suppressed, so an alert
nobody received never looks like one that was delivered.

---

## 12. What this stack does not do

State the boundary, or the buyer discovers it during an incident.

- It is HTTP layer only. It sees nothing on endpoints, in email, or in identity systems.
- It is not a web application firewall, not a volume scrubber, not an intrusion prevention system,
  not endpoint protection. It inspects nothing below HTTP.
- It never touches a firewall.
- It does not defeat automation that pays for a real browser engine. Asset correlation and fetch
  metadata both confirm a browser, and a Playwright-driven Chrome is a browser. What they defeat is
  the large, cheap population built on plain HTTP clients. Catching the rest needs behavioural
  analysis over time: inter-arrival regularity, coverage across a day, absence of idle periods.
- There is no tamper-evident logging. An attacker with host access can edit the audit trail.
- It cannot see a virtual host behind a shared front end that requires the client to name it.

---

## 13. A note on privacy, because it constrains the design

An IP address is personal data (GDPR; CJEU C-582/14 *Breyer*). Everything in this stack is derived
from what the client voluntarily sent, which is defensible under legitimate interest for security
with a notice and a retention period.

Techniques that unmask a user **behind a VPN** are a different category. WebRTC disclosure and
QUIC/UDP leak checks deliberately reveal an address the user chose to hide. We evaluated them and
declined: they need JavaScript so they never see scripted clients at all, they flag corporate
networks that block UDP along with Safari and every privacy extension, and they require running a
relay, which is new infrastructure and new attack surface. The header-based signals cost nothing and
unmask nobody.

If you want correlation without the identifier, store a salted hash of the address. Our sidecar
supports that with one environment variable, and the correlation survives while the identifier does
not.
