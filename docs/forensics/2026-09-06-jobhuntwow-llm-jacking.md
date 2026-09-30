# Incident report: LLM-jacking of jobhuntwow.com

**Classification:** Internal. Contains addresses, account identifiers and a data-protection
determination.
**Incident date:** 2026-08-30 to 2026-09-06 · **Contained:** 2026-09-06 15:49 UTC
**Report date:** 2026-09-21 · **Status:** Contained, remediated, with named items still open
**Author:** Reconstructed from logs, git history and two measured incident runs. Every claim carries
its source. Where a fact could not be established it says so and says what would establish it.

---

## 1. Executive summary

An unauthenticated HTTP endpoint on jobhuntwow.com forwarded a **caller-chosen model identifier** to
DigitalOcean's serverless inference API using our own API key. A single automated client found it
and used it as free inference for approximately seven days.

- **1,539 requests** from one address, **1,521 of them successful**, all to one endpoint.
- The client named **two models that appear in none of our configuration files**, and at the peak
  those two accounted for **more than 96% of the account's input tokens**.
- DigitalOcean **auto-recharged the prepaid balance by 5 USD three times inside two days** while our
  own cost report said lifetime spend was under one dollar.
- **No user data was exposed through this endpoint.** Determined, not assumed. See section 2.
- Containment took **56 seconds** from the last successful abuse to the fix being committed. Finding
  the cause took **six days**, and every one of those days was spent on our own blindness rather
  than on the attacker's skill.

The endpoint had no authentication, no model allowlist, no rate limit, no quota and no meter. It was
not a control that failed. It was five controls that were never written.

> **The sentence this incident produced, now a standing rule:** a route that forwards a
> caller-chosen model identifier to a paid API is a **payment endpoint**. It needs authentication
> and an allowlist, and the allowlist has one home.

---

## 2. The data-protection determination, resolved

Putting this second because it is the question anybody reading a breach report needs answered first.

**Finding: no third party's personal data was served. This was not a personal data breach under
GDPR Article 4(12), and no Article 33 notification obligation arises from it.**

The concern was real and had to be tested. A second defect in the same application, `/api/electronic/*`,
took the owner's email address as a request parameter with no session required, so anybody could in
principle have listed another user's jobs and downloaded their tailored CV and cover letter. The logs
show **53 requests to that route tree with no session**. Fifty of them, from `212.58.119.138` between
2026-08-16 and 2026-08-18, returned HTTP 200 and included eight artifact downloads of generated
resumes and cover letters.

**The eight job identifiers resolve to self-access, provably.** A job identifier in this system
embeds its own creation timestamp in the form `YYYYMMDD-HHMMSS-job-<hash>`. For every one of the
eight, the same address issued `POST /api/electronic/jd` at **exactly the second named in the
identifier**, and downloaded the artifacts one to two minutes later:

| Job identifier | Creation second embedded in the id | `POST /jd` from the same address at that second |
|---|---|---|
| `20260816-124559-job-6a882e` | 2026-08-16 12:45:59 | yes |
| `20260816-134010-job-05e7be` | 2026-08-16 13:40:10 | yes |
| `20260816-141731-job-efe990` | 2026-08-16 14:17:31 | yes |
| `20260817-083445-job-8572f1` | 2026-08-17 08:34:45 | yes |
| `20260817-140059-job-face14` | 2026-08-17 14:00:59 | yes |
| `20260817-163950-job-4e2ac8` | 2026-08-17 16:39:50 | yes |
| `20260818-121818-job-30c01f` | 2026-08-18 12:18:18 | yes |
| `20260818-190918-job-e95c4c` | 2026-08-18 19:09:18 | yes |

Corroborating, from the same evidence file: that address completed a one-time-code login as
`feranicus@gmail.com` at 07:12:21 and 07:13:04 UTC on 2026-08-16, five hours before the first
`/api/electronic/` request, and its user agent on those calls is `python-httpx/0.28.1`, a developer's
client rather than a browser.

**Every artifact served to an unauthenticated caller was created by that same caller, seconds
earlier.** Nobody downloaded anybody else's document. The remaining three anonymous requests to that
route tree, from `46.116.187.7` on 2026-09-06 at 18:41, all returned **401**, because the fix was
already in place.

Four accounts existed on the platform at the time, which bounds the population at risk regardless.

**What this finding does not cover.** `POST /api/connections`, which writes a Telegram bot token, was
also publicly reachable. There is no evidence in the window that it was exercised, and absence of
evidence over a 30-day retention window is not proof it never was. That is recorded as an open item
rather than cleared.

---

## 3. Timeline

All times UTC. Events marked *inferred* are derived rather than recorded, and the derivation is given.

| When | Event | Source |
|---|---|---|
| 2026-07-20 | `/api/chat` and `/api/models` created with **no authentication dependency and no allowlist** | commit `c3675c5` |
| ~2026-08-07 | jobhuntwow.com reachable behind the shared proxy. *Inferred* from a topology document dated that day; the true first-deploy date is no longer recoverable | `CADDY_ARCHITECTURE.md` |
| **2026-08-30 22:40:56** | **First request from `24.199.91.170`** | incident run 2, §2 |
| 2026-08-31 | 397 requests, the actor's heaviest day | incident run 2, §2a |
| ~2026-09-01 | **DigitalOcean auto-recharges 5 USD, three times inside two days.** The operator notices a payment, not an alert | `cost_report.py` header; decision log |
| 2026-09-01 ~10:22 | Vendor console shows two unknown models at 318.1K and 518.2K input tokens against our four models at roughly 14K and 16K | decision log, operator screenshot |
| 2026-09-03 | Second plateau, roughly 1.1M input tokens on one unknown model | decision log |
| 2026-09-06 12:01:20 | The separate `/v1/` proxy gets an allowlist. The chat route still does not | commit `b76cf68` |
| 2026-09-06 12:07:00 | First **metered** model call in the surviving evidence | incident run 2, §3 |
| 2026-09-06 | Log search for the two model names returns exactly one source: `jhw-web`, caller `qwen.chat_stream` | decision log |
| 2026-09-06 15:48:13 | **Last successful metered call** | incident run 2, §3 |
| **2026-09-06 15:49:09** | **CONTAINMENT. Session required and allowlist enforced on `/api/chat` and `/api/models`** | commit `302ee38` |
| ~2026-09-06 15:50 to 16:00 | Refusals begin. *Inferred*, tightly: 18 × HTTP 401 recorded, and the actor's hourly request counts for hours 15 to 18 sum to exactly 18 if refusals start partway through hour 15 | incident run 2, §2b |
| 2026-09-06 18:24:50 | The `/api/electronic/*` tree locked. Container restarts 9 seconds later, which dates the deploy | commit `78896d7` |
| 2026-09-06 18:34:39 | **Last request from the actor** | incident run 2, §2 |
| 2026-09-06 19:00:14 | `/openapi.json`, `/docs` and `/redoc` disabled | commit `8ac52c3` |
| 2026-09-07 | Behavioural classifier returns **automated, agent-shaped** | decision log |

**Exposure window: 48 days from route creation to fix.** Internet-reachable for approximately 30 of
them, inferred. **Abuse window: 6 days 19 hours 53 minutes**, spanning 8 calendar dates.

> A note on a figure that circulated internally as "8 days": the elapsed time is **6 days 20
> hours**. It touches eight dates. Use the elapsed figure; the other overstates duration by about
> 17%.

---

## 4. The vulnerability

**Route:** `POST https://jobhuntwow.com/api/chat`
**Body:** `{"messages": [...], "model": "<any string>"}`

The vulnerable handler, in full, as it existed for 48 days:

```python
@app.post("/api/chat")
async def chat(req: ChatReq):
    msgs = [m.model_dump() for m in req.messages]
    async def gen():
        async for chunk in qwen.chat_stream(msgs, model=req.model):
            yield chunk
    return StreamingResponse(gen(), media_type="text/plain; charset=utf-8")
```

Three hops from the request body to our credit card, with no validation on any of them:

1. `req.model` goes straight into `qwen.chat_stream(msgs, model=req.model)`.
2. In `qwen.py`, `mdl = model or QWEN_MODEL or llm.model_for("chat")`. A non-empty caller string
   short-circuits every default.
3. `_headers()` returns `{"Authorization": f"Bearer {DO_KEY}"}` and posts to DigitalOcean.

And a companion route made it trivial:

```python
@app.get("/api/models")
async def models():
    return await qwen.list_models()
```

`GET /api/models` returned DigitalOcean's **entire catalogue, 75 identifiers**, to anybody. The
caller did not have to guess a model name. We handed them the list.

Both model identifiers the actor used carry catalogue snapshot suffixes. Those are the strings a
client receives from listing, not strings anyone invents.

### Controls present at the time

| Control | Present |
|---|---|
| Authentication | **No.** No dependency on the handler |
| Model allowlist | **No.** First appears 48 days later |
| Rate limit or throttle | **No.** Grep across the whole backend finds none |
| Per-user quota | **No** |
| Daily spend cap | **No** |
| Token metering | **No.** The vendor returned usage on every response and both call sites discarded it |

The metering gap is the one that made this expensive rather than merely embarrassing. There was no
number to alarm on, so no alarm could exist.

### The API schema was public, but it is not how they found us

`/openapi.json`, `/docs` and `/redoc` were all served anonymously, publishing the route list,
parameter names and schemas, including the `model` field of `/api/chat`.

**That said, the evidence argues against schema discovery for this particular actor.** The
behavioural tool measured a *negative* interval between first reading the schema and first calling
the endpoint: the endpoint was called before the schema was ever fetched. The tool now refuses to
score that signal and prints "this client did not learn the API here." How they found it is **not
established.**

---

## 5. The actor

**Address:** `24.199.91.170`. Registry lookup at the time returned holder `DIGITALOCEAN-24-199-64-0`,
DigitalOcean LLC, abuse contact `abuse@digitalocean.com`. **Hosting infrastructure, not residential**,
which follows from the allocation alone. Country is **not established** and a hosting allocation's
registration country would not tell us where the operator is anyway.

**User agent:** `python-requests/2.34.2`, exclusively.

| Measure | Value |
|---|---|
| Total requests | **1,539** |
| Status distribution | **1,521 × 200, 18 × 401** |
| Endpoints touched | `chat` 1,539. `models` 0, `electronic` 0, `proxy` 0, `auth` 0 |
| Per-day | 14, 397, 250, 233, 264, 136, 131, 114 (sums to 1,539) |
| Duration | 6 d 19 h 53 m |
| Metered model calls observed | **34** (32 + 2 across the two models) |

> Two snapshots taken 21 minutes apart read 1,538 and 1,539. Both numbers are correct; the later one
> is final. This is worth recording because the discrepancy looked like an error and was not.

### Human, script or agent

The classifier returned **"automated, and agent-shaped (inference, not proof)"**.

| Signal | Measured | Reading |
|---|---|---|
| Inter-arrival regularity | coefficient of variation **0.771**, median beat **6.2 minutes** | Variable but bounded. The shape of a loop waiting on a model |
| Coverage across the day | **24 of 24 hours**; longest silence in twelve days **17 minutes** | Automated. No sleep |
| Concurrency | **1**, strictly serial | One loop, or one person |
| Model switch after a failed call | **4 switches, every one immediately after an error** | A configured fallback chain. Framework behaviour |
| Think time | Suppressed. Its coefficient of variation is **0.771, identical to the inter-arrival figure** | The gap measures the schedule, not a reader |
| Token variance | **Not measured.** Metered lines carry no address, so they cannot be attributed per actor | |

**The model-switching is the strongest signal.** A naive script names one model and retries it. A
client that walks a ladder when one fails has a configured fallback chain, which is framework
behaviour rather than a hand-rolled loop.

**What cannot be established, and the tool refuses to claim:** identity, intent, or which framework.
An engineer can hand-write a dependent loop and no log separates that from an agent.

**What the inference was used for is not establishable.** Request bodies are deliberately not logged,
because they are third-party content and may carry other people's personal data. The only
content-adjacent datum is the metered window's **10,574 input tokens per call**, which is the shape
of a large fixed scaffold re-sent every turn rather than a conversation. That is suggestive of resale or an
automated pipeline and it is **not evidence of either**.

### Behaviour under containment

The actor **did not back off**. It absorbed 18 consecutive 401s without changing its rhythm and kept
beating for roughly two and a half hours after the door closed. That is consistent with an unattended
loop nobody was watching.

---

## 6. The money

| Figure | Value | Confidence |
|---|---|---|
| Directly metered and observed | **34 calls, 359,504 input tokens, 17,728 output, 0.1769 USD** | **Measured.** But covers only 3 h 41 m of a 7-day incident |
| Extrapolated across the 1,559 chat requests in the window, all sources | **~8.11 USD**, range **4.06 to 16.22** | Estimate, bounds stated |
| Vendor auto-recharges | **5 USD × 3 inside two days** | Recorded contemporaneously, twice. The invoice itself is not in our possession |
| Our own report at that moment | **under 1 USD lifetime** | Measured, and wrong |

### Why our accounting disagreed with the bank

Four independent defects:

1. **The cost ledger had exactly one caller.** Everything else that spent money, including four
   scheduled jobs, was invisible to it by construction.
2. **The arithmetic priced input and output the same**, at a flat rate, against models where output
   costs over three times input on an output-heavy workload.
3. **Nothing capped anything, at any layer.**
4. **jobhuntwow emitted no model event at all.** Even a perfect ledger in the other project was blind
   to this codebase. Different repository, different container, no shared meter.

### The honest total

**Approximately 8 USD, with a defensible range of 4 to 16**, and three reasons that is not the
invoice: everything before the meter existed is extrapolated from request counts rather than tokens;
an unknown model is priced at the dearest rate we know, so a genuinely dearer model pushes the real
figure *up*; and log retention means anything older than the window is simply invisible.

**Per-project attribution is impossible after the fact** and will stay impossible until the key is
split. One DigitalOcean model access key is shared by **seven containers across five projects**, so
the vendor sees one caller. The strongest available formulation is a bound by elimination: our own
legitimate usage runs at about half a US cent per assessment, so essentially the whole AI line in
that window is unauthorised traffic.

The direct loss is small. **The finding is not the amount, it is that an anonymous stranger could
spend from our account at a rate we neither measured nor bounded.** The same hole with a more
expensive model, or a busier attacker, is a different number entirely.

---

## 7. Detection, and why nothing caught it sooner

**No security control detected this. The billing system did, and then the vendor's own console.**

| From | To | Elapsed |
|---|---|---|
| First abusive request | Billing signal | **~1 day 12 h** |
| First abusive request | Root cause identified | **~6 days** |
| First abusive request | Containment | **6 days 17 h** |

The sequence: an auto-recharge was noticed, the vendor's per-model breakdown named two models in one
line after half a day had been wasted auditing our own callers, a log search for those two names
returned exactly one source, and a single anonymous `curl` confirmed the door was open.

### The controls that should have caught it

Unsparing, because the value of this report is in this list.

1. **No authentication on the route.** Not bypassed. Never written. In a framework where a route is
   public unless somebody remembers, this outcome is a matter of time rather than of care.
2. **No allowlist**, on an endpoint that forwards a caller-chosen identifier to a paid API.
3. **No rate limit and no quota**, so 1,539 requests from one address over a week triggered nothing.
4. **No meter in that project at all.** Usage was returned by the vendor on every response and
   discarded at both call sites.
5. **The cost ledger could not see the project** even in principle.
6. **No spend watcher existed.** A meter-only watcher would have reported a completely normal
   fortnight while the invoice tripled.
7. **The evidence was in the log pipeline the whole time and nobody asked.** It needed a query, not a
   deploy.
8. **And when we finally asked, we asked wrong.** A diagnostic reported "jobhuntwow: 0 log lines, not
   shipping" and a whole theory was built on it. The label it queried had never been deployed. **A
   failed query rendered as innocence, three runs in a row.**
9. **That project's writes to the shared log were failing silently** on a file-ownership bug,
   swallowed by a bare except, so the queries were *honestly* empty.
10. **The API schema published the map.**
11. **No authorisation audit existed.** Nothing ever asked whether every route refuses a stranger,
    until after the money was gone.
12. **The vendor-side guardrail was available and unused.** The key is legacy, unscoped and not
    network-restricted, so the model allowlist that would have refused the request outright at the
    vendor was never configured.

Twelve findings, one sentence: **every layer that could have caught this was either absent, or
present and blind, and the blindness reported as health.**

---

## 8. Containment and remediation

| Change | What it now does |
|---|---|
| **Session required on `/api/chat`** | Anonymous callers get 401 |
| **Session required on `/api/models`**, and the response filtered | Even an authenticated user is not handed 75 identifiers |
| **One allowlist, one home** | Defined once; both the chat route and the `/v1/` proxy delegate to it. The proxy's own separate list, added three hours earlier, was replaced by a delegation to the same function |
| **Refusals are evidence** | A refused model records caller, user and source address, pages Telegram, and returns 403 naming what was asked for and what is allowed |
| **Metered line carries the user** | Per-call attribution now exists |
| **Metering at a chokepoint** | Two call sites, one emitter. Per-direction pricing. An unknown model is priced at the dearest rate known, never an average, because the whole point is to notice a caller nobody configured |
| **Budget enforcement in the sibling project** | Checked *before* the request. Fails **open** on a storage fault and **closed** on the budget |
| **A spend watcher** | Compares two sources hourly: our meter, which says *who*, against the vendor balance delta, which says *whether*. Median baseline rather than mean, because one prior spike hides the next. Requires both a ratio and an absolute floor. **Names the models that are new today** |
| **Schema and docs disabled** | Unless an explicit environment variable is set |
| **The `/api/electronic/*` tree locked** | Router-level session dependency; every email parameter replaced by the session identity, so the caller can no longer name whose data to operate on |
| **Regression gate** | A test **walks the live route table** and asserts 401 for everything outside a pinned public set, so a new route without a session dependency fails the day it is added |
| **Authorisation audit** | Measures the **response**, never the source. An earlier syntax-scanning version reported every route in the sibling project as public because its guard is a statement rather than a signature. Exits with "blind, not clean" rather than passing on an unreachable probe |

**Verified after the fix**, anonymously from outside: `/api/models`, `/api/me`, `/api/connections`,
`/api/electronic/jobs`, `/api/electronic/jobs?email=victim@example.com` and `/v1/models` all return
401. And from the actor's own traffic: 18 × 401.

---

## 9. Still open

Ordered by risk.

1. **The DigitalOcean key is still shared, legacy, unscoped and not network-restricted.** Seven
   containers, five projects, one fingerprint. The vendor supports scoping a key to specific models
   and binding it to a private network; a legacy key grants every foundation model and its scope
   cannot be edited. Our allowlist closes one path. A scoped per-project key closes every path
   including ones we have not imagined, **and it is the only thing that would make the next invoice
   attributable.** Console work, no script can do it. No evidence it has been done.
2. **Key rotation was recommended twice and there is no evidence it happened.** Cheap to check:
   compare the current fingerprint against the one recorded in the incident.
3. **jobhuntwow still has no budget cap and no rate limit.** Authentication is now required, but
   self-signup is open. **The same spend is available to anyone willing to create an account, and
   nothing currently prevents it.** This is the most likely recurrence path.
4. **The route-table gate exists in two projects.** The other three have no equivalent. The defect
   class is opt-in authorisation, and it recurs the moment somebody adds a route to a project
   without that test.
5. **A sibling site still publishes its API schema.** Separate repository, one-line fix.
6. **Two properties have never been source-audited**, only probed from outside with safe methods.
   Nothing says they are safe.
7. **The vendor invoice has never been reconciled in writing** for the incident period.
8. **One unresolved factual tension.** The actor made 397 requests on 2026-08-31, yet a console
   screenshot that morning was recorded as showing normal volume on our own four models only. Vendor
   aggregation lag is the likely explanation. Not resolved.
9. **`POST /api/connections`, a credential write, was publicly reachable.** No evidence it was
   exercised, bounded by a 30-day window.

---

## 10. Indicators of compromise

For searching your own logs for the same pattern.

**Addresses**

| Address | Role | Registry holder |
|---|---|---|
| `24.199.91.170` | The LLM-jacker | DigitalOcean LLC |
| `111.202.70.100` and `156.229.164.222` | 32 × 401 each within 32 seconds of one another, bearer-token brute force against the proxy | |
| `195.178.110.108` | 56 auth-path hits, 404/405 only | |
| `212.58.119.138` | 50 anonymous artifact requests. **Determined to be self-access, see section 2** | Caucasus Online |

**User agents:** `python-requests/2.34.2`, `python-httpx/0.28.1`

**Paths**

```
POST /api/chat                 {"messages":[...], "model":"<slug>"}
GET  /api/models
GET  /api/electronic/jobs?email=<address>
GET  /api/electronic/artifacts/<job-id>/{resume,cover_letter}.{pdf,docx}
POST /api/connections
GET  /openapi.json  /docs  /redoc
POST /v1/chat/completions      GET /v1/models
```

**The sharpest single indicator: a model identifier in your billing that appears in none of your
configuration files.** Both identifiers used here carry catalogue snapshot suffixes, which is the
string a client receives from listing rather than one anybody guesses. Check your vendor's per-model
breakdown against your own configuration. That one comparison is what broke this case open, after
half a day had been wasted auditing our own code.

**Billing signature:** a prepaid balance auto-recharging in fixed steps, repeatedly, within days.

**Behavioural signature:** one address, one path, 5 to 7 requests an hour sustained; median gap 6.2
minutes; active in 24 of 24 hours with a longest silence of 17 minutes across twelve days;
concurrency 1; roughly 10,500 input tokens per call, flat; model switched immediately after each failed call;
no change in rhythm after refusals begin.

---

## 11. Evidence register

| Artifact | Location | Integrity |
|---|---|---|
| Incident run 1, 2026-09-06 18:29:58 UTC | `docs/forensics/evidence/incident-20260906-182958.md` | 565 lines, sha256 `7d746cfb…` |
| Incident run 2, 2026-09-06 18:51:13 UTC, supersedes run 1 | `docs/forensics/evidence/incident-20260906-185113.md` | 598 lines, sha256 `bb07224b…` |
| Narrative record | `docs/decisions/HISTORY-2026-07-to-2026-09-10.md` | In the repository |
| Commits | `c3675c5` (introduction), `b76cf68`, `302ee38` (containment), `78896d7`, `8ac52c3` | In the repository |

> **These two evidence files were gitignored and existed in exactly one working tree.** They were
> generated from a 30-day log window that has long since rolled off, so nothing can regenerate them.
> One `git clean` would have made this incident permanently unverifiable. They are now archived under
> `docs/forensics/evidence/` with an explicit exception in `.gitignore`. **Anyone writing an incident
> tool should make its output durable by default.**

**Not in our possession:** the DigitalOcean invoice and the console screenshots referenced in the
timeline. The invoice is the authoritative cost figure and every number in section 6 should be read
as subordinate to it.

---

## 12. What this incident taught, as rules

1. **A route that forwards a caller-chosen model identifier to a paid API is a payment endpoint.** It
   needs authentication and an allowlist, and the allowlist has one home.
2. **When a number surprises you, read the vendor's own breakdown before auditing your own code.**
   Half a day went into our callers before one screenshot named the two models in a single line.
3. **A failed query is not an answer.** A diagnostic reported zero log lines and we read it as
   innocence three times. A tool that cannot see its subject must say so, never report a clean
   result.
4. **Absence of evidence is never a finding**, and its corollary here: a silently swallowed write
   error makes an empty log look honest.
5. **Measure the response, not the source.** The first authorisation audit scanned function
   signatures and declared everything public, because the real guard is a statement inside the
   handler. Ask the running system.
6. **A meter with one caller is not a meter.** Put it at the single chokepoint every caller must
   pass, and price an unknown model at the dearest rate you know so a caller nobody configured can
   never look cheap.
7. **Watch two sources.** Your own meter says *who*. The vendor balance says *whether*. A meter-only
   watcher reports a normal fortnight while the invoice triples.
8. **Make the incident tool's output durable.** Ours was one command away from being lost.
