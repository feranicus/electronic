# The four-model consensus: A to Z

**What this is.** A complete, implementable description of the four-model consensus pattern as it
runs in production on cybergod.ai, in three different jobs: the **CI/CD staging gate**, the
**cyber-defence panel**, and the **release notes**. Written to be lifted into another codebase
(jobhuntwow.com is the immediate target), so every section separates *the principle* from *our
specific plumbing*.

**Written 16 Aug 2026** from the running code, not from memory. Every file, model id, constant and
threshold named here was read out of the repository.

---

## 0. The one-paragraph version

Four language models from **four different vendors** independently review the same deterministic
evidence and write their reading of it. **They never decide anything.** Code computes the verdict;
the models produce the reasoning, the risk list and any objection worth a human's attention. Where
they are allowed to change something at all, six integers in the defence system, a **quorum of
three must agree on the direction**, the applied value is the **median**, and every value is
**clamped to bounds committed in git**. This arrangement fails safely in both directions: a rate
limit cannot block a good release, and an agreeable model cannot wave through a broken one.

---

## 1. Why four, why different vendors, why two roles

### 1.1 Four vendors, not four prompts

The panel is `deepseek-3.2 · llama-4-maverick · gemma-4-31B-it · kimi-k2.6`. The reason they come
from four vendors is not diversity for its own sake:

- **A 429 is provider-wide.** Four models on one provider is one model wearing four hats. When the
  quota goes, the whole panel goes silent at once.
- **A blind spot is model-family-wide.** Models trained on similar data make similar mistakes. The
  point of a panel is that a wrong reading is *contradicted*, and a model cannot contradict its own
  reasoning wearing a different name.
- **Same doctrine as the false-positive auditor elsewhere in this system:** a model never audits its
  own output, and the auditor is always a different vendor from the author.

### 1.2 Two roles, two prompts, two questions

| Role | Count | The question it is asked |
|---|---|---|
| **soldier** | 2 | "Did this work?" Operational reading of the evidence. |
| **auditor** | 2 | "What does the evidence NOT cover?" Adversarial reading. |

The auditor prompt is explicitly told to look for *a check that passed for the wrong reason, a
service that is running but was never exercised, something that only breaks after a reboot or under
load*. That is a different job from grading the run, and asking one model to do both produces a
worse answer at both.

### 1.3 What this bought, measured

The panel is not decoration. From our own record:

- It identified a disabled admin API from the string `d41d8cd98f00` alone, by recognising it as the
  md5 of the empty string.
- It twice spotted that a check's DETAIL contradicted its own VERDICT, which is the tell for "the
  check is broken, not the system".
- It noticed that nothing verified the reverse proxy's admin API was still loopback-only, on an
  endpoint that can replace the running configuration for every domain on the host.
- On 16 Aug 2026 it noticed that **six checks were missing from the evidence** while the gate
  reported "35/35 passed" (the previous run had counted 41).

And it is wrong often enough that the governance matters. It has inverted a check's logic, invented
a Kubernetes manifest for a system that has none, and made the same wrong call about one check on
three consecutive runs. **That third case was our defect, not the model's**: the briefing explained
why an old method was wrong and never said what the check currently does, so a reviewer reasoning
from that map landed on the removed method every time.

> **Rule: feed the panel more evidence, never more authority. If a reviewer makes the same wrong
> call three times, fix the briefing.**

---

## 2. The governance model, who decides what

This is the load-bearing part. Get it wrong and you have either a rubber stamp or a system that
cannot ship.

```
                    DETERMINISTIC CHECKS                    MODELS
                    ────────────────────                    ──────
verdict (GO/NO-GO)        DECIDE                            never
reasoning / diagnosis     ──                                WRITE
risk list                 ──                                WRITE
threshold values          bounds + clamp                    PROPOSE (quorum + median)
blocking an address       DECIDE                            never
release halt              ──                                2+ dissent ⇒ ask a human
```

### 2.1 The four invariants

1. **Code decides side effects.** A model call is 300ms to 60s and can 429. Anything on a hot path
   or a release path must be arithmetic.
2. **A failing gate can never be rescued by a happy panel.** Asserted by test.
3. **A single model can never veto.** One rate-limited or wrong reviewer must not hold releases
   hostage. Asserted by test.
4. **Dissent must reach a human before the consequence, not after.** See below.

### 2.2 The dissent threshold, and why it moved

Originally only a **unanimous** NO-GO halted a green gate. That threshold was raised to **two or
more dissenters (with at least one hard NO-GO)** on 16 Aug 2026, after the panel was right twice
about a gate that was lying:

- **2026-08-07**, all four named the same check; the check was scoring a failure as a pass.
- **2026-08-16**, two dissented, one naming missing evidence. Six checks had silently failed to
  report and the gate printed 35/35. Two of four is not unanimous, so nothing fired and it promoted.

Current policy, exercised against real panel shapes:

| Panel | Outcome |
|---|---|
| go / go / unsure / no-go | **HALT** |
| no-go × 4 | **HALT** |
| go / go / go / no-go (one grumpy model) | GO |
| go / go / go / unsure (one 429) | GO |
| go / go / unsure / unsure (nobody objects) | GO |
| no reviews at all (panel down) | GO |
| **red gate** + four happy models | **NO-GO** |

Two UNSUREs with nobody actually objecting is hesitation, not a finding. Halting on that makes every
quiet run an interruption, and a gate that stops you for nothing is a gate you override by reflex.

The halt is escapable with an explicit `OVERRIDE_PANEL=1`. A guard that cannot be overridden by an
informed operator is a bug; a guard that presents its decision as a malfunction is a different bug.

---

## 3. Application one, the CI/CD staging gate

**Files:** `stagegate.py` (orchestration, 800+ lines), `deploy/stagegate/quorum.py` (the panel, 239
lines), `tests/test_gate_integrity.py` (45 tests that the gate cannot lie).

### 3.1 The shape

```
ship.py
  └─ stagegate.run()
       ├─ deploy to the STAGING TWIN using the SAME script production uses
       ├─ HEALTH: ~20 deterministic checks          → CHECK|name|yes/no|detail
       ├─ REBOOT THE TWIN                            ← the whole point
       ├─ HEALTH again                               → post_reboot_*
       ├─ completeness: every pre-reboot check must report again
       ├─ quorum.py: 2 soldiers + 2 auditors read the SAME evidence JSON
       └─ GO / NO-GO  → production deploy proceeds, or is refused
```

### 3.2 The evidence contract

One check, one line, machine-parseable, and the *same strings* become what the models read:

```bash
chk() { printf 'CHECK|%s|%s|%s\n' "$1" "$2" "$(printf '%s' "$3" | tr '\n|' '  ' | cut -c1-1000)"; }
```

`tr` is the protocol protection: a newline inside a detail would truncate the record. `cut` is only
a runaway guard for a crashing command dumping a traceback, and it must sit **far above any real
detail**. We had it at 200 and it silently amputated every long detail at source for weeks.

```python
{"gate": "GO"|"NO-GO",
 "checks_total": int, "checks_failed": int,
 "models": [{"role": "soldier"|"auditor", "model": str, "verdict": "go"|"no-go"|"unsure",
             "diagnosis": str, "proposed_fix": str, "reasons": [str], "risks": [str]}],
 "answered": int, "dissent": int,
 "digest": str}
```

### 3.3 The prompt asks for a ROOT CAUSE and a FILE

The highest-value thing in this prompt is not "is it healthy". It is this instruction:

> *For every failed check, say what you believe the ROOT CAUSE is and name the REPO FILE that
> should change. Distinguish clearly between "the system under test is broken" and "the CHECK
> ITSELF is broken", a check whose detail contradicts its own verdict is a defect in the check, and
> saying so is more valuable than restating the failure.*

That single paragraph is what turns the panel from a commentary track into something that saves a
diagnostic cycle. The digest puts all four diagnoses **together, first**, so agreement and
disagreement are visible at a glance.

### 3.4 Six deterministic properties the panel does not provide

These are checks about the *checks*. Every one exists because a green gate lied:

| Property | The incident |
|---|---|
| No wildcard branch may score an unknown answer as a PASS | `*) chk config_drift yes "unavailable: $D"` took a NO-GO to 33/33 green |
| A PASS whose detail contains failure language is **demoted automatically** | a check reported PASS while quoting "STALE MOUNT" in its own detail |
| Details are **wrapped, never truncated** | truncation destroyed the evidence the check exists to provide, and cost the panel three review slots |
| A health run must reach a **terminal sentinel** | partial ssh output was counted as a complete run |
| Post-reboot checks are compared **by name** to pre-reboot | six checks vanished and the gate called it 35/35 |
| The ssh return code is **never discarded** | a dropped connection returning partial output was invisible |

> **Rule: a gate must know what it EXPECTS, not count what it got.** A shrinking denominator is not
> a smaller pass; it is missing evidence.

### 3.5 Why a reboot

Config that is valid on disk but never reloaded is invisible until the next restart. Our worst
outage was exactly that: a shared proxy config truncated at 16:15, latent for twelve hours, detonated
by an unattended kernel reboot at 04:22, taking every domain on the host down together.

The twin is the same size, image and region as production, deliberately. A twin that differs in
those is not a twin. It runs on **synthetic data only**, so no production personal data crosses over.

**A test that can pass without the event happening is not a test.** The reboot check originally
waited for SSH to answer, but right after `systemctl reboot` the box is still up, so it reported
"back after 1s" and passed. It now compares `/proc/sys/kernel/random/boot_id`, which is regenerated
on every boot, and requires it to **change**.

---

## 4. Application two, cyber defence

**Files:** `webapp/backend/app/shield.py` (inline, deterministic, no model call), `shield_panel.py`
(the panel, out of band), `shield_tuning.py` (storage with a contract), `shield_console.py` (the
human authorisation tier), `tests/test_shield.py`.

### 4.1 The split, and why the models are nowhere near a request

```
REQUEST PATH                                    OUT OF BAND (every 6 hours)
────────────                                    ───────────────────────────
shield.observe()   score the request            shield_panel: 4 models read
shield.decide()    ALLOW | TARPIT | BLOCK         what the shield actually DID
                   pure arithmetic, μs           → narrative + proposed integers
                                                 → quorum + median + clamp
                                                 → Telegram + email
```

Stated in the module docstring and non-negotiable:

- a model call is 300ms to 60s. **Putting one in front of a request that IS the attack is a denial
  of service**, and the panel's own failure modes (429, timeout) become site outages;
- the product's public claim is that the LLM assists and does not decide side effects.

### 4.2 What the panel may touch: exactly six integers

```python
BOUNDS = {
    "tarpit_after":  (3, 25),      "block_after":   (6, 60),
    "window_s":      (60, 900),    "block_s":       (300, 86400),
    "tarpit_ms":     (250, 8000),  "ua_rotation_n": (3, 10),
}
```

Four properties make this safe:

1. **The bounds live in committed code** and are enforced by `cfg()` **on every READ**, not on
   write. A hand-edited, corrupt or hostile tuning file therefore still cannot push the system out
   of range, the worst it can do is pick a different point inside a range you already accepted.
2. **A quorum of 3 of 4 must agree on the DIRECTION** before a key moves at all. Three saying "raise"
   and one saying "lower" raises it; a two-two split changes nothing.
3. **The applied value is the MEDIAN**, never the mean and never the boldest. One model arguing for
   a drastic change is outvoted by three moderate ones.
4. **A change of more than 25% in one cycle is clamped.** Adaptation should be gradual; a model that
   has misread one incident must not be able to swing the whole policy in one step.

It **cannot** block or unblock an address, change the bounds, the blast cap, the allowlist or the
kill switch.

### 4.3 The consensus function, in full

```python
def consensus(reviews, current):
    agreed, notes = {}, []
    keys = {k for r in reviews for k in (r.get("propose") or {})}
    for k in sorted(keys):
        cur = current.get(k)
        if cur is None:
            notes.append("%s: not a tunable key" % k); continue
        up = [r["propose"][k] for r in reviews if (r.get("propose") or {}).get(k, cur) > cur]
        dn = [r["propose"][k] for r in reviews if (r.get("propose") or {}).get(k, cur) < cur]
        side = up if len(up) >= QUORUM else (dn if len(dn) >= QUORUM else [])
        if not side:
            notes.append("%s: only %d up / %d down - below the quorum of %d, unchanged"
                         % (k, len(up), len(dn), QUORUM))
            continue
        agreed[k] = sorted(side)[len(side) // 2]        # MEDIAN
    return agreed, notes
```

The refusal is **reported, not swallowed**. A real report reads:

```
refused: block_s: only 0 up / 1 down - below the quorum of 3, unchanged
Bounds are committed in shield.py and cannot be changed by any model
```

That transparency is the feature. The operator sees what was proposed, what was applied, and why
the rest was refused.

### 4.4 The prompt tells the model what it is trading against

> *A threshold that is too aggressive locks out real visitors. A threshold that is too slack lets a
> scanner enumerate the site. Say which risk you are trading against which.*
>
> *If the evidence does not support a change, propose NO changes. "Leave it alone" is a real answer
> and is often the right one.*

Without that second sentence a panel invents work. With it, the most common real output is
`proposes NO change`, which is correct on a quiet day.

### 4.5 The human tier: AUTO / ASK / NEVER

Split by **reach**, not by confidence.

| Tier | Actions | Rationale |
|---|---|---|
| **AUTO** | tarpit, 15-minute block, alert | Waiting for approval on a 15-minute block means the scan finishes before the phone is unlocked |
| **ASK** (one Telegram tap, expires in 2h) | 24h hold · block the /24 for 1h · strict mode · ban a path · file an abuse report · false alarm + release | A /24 is up to 256 addresses and may be an office or a mobile carrier. The system honours that state; it never decides it |
| **NEVER** | scanning back, connecting to their host, any hack-back | Criminal under StGB §202a/§202b/§303a/§303b (§202c covers even the tooling), EU Directive 2013/40, US CFAA §1030, Canada CC s.342.1. The address is usually a compromised third party. **A test fails the build if an offensive action is added** |

Two implementation details worth copying:

- **Separate the recorder from the enforcer.** The Telegram bot RECORDS the decision; the web app
  ENFORCES it, on a 20-second loop. A bug in one cannot block anybody. Applying a decision is a file
  read; deliberating with four models is expensive. They do not belong on one clock.
- **Read the confirmation back out of live state after the write.** The first version printed
  "Applied: holding 1.2.3.4 for 24h", which is the same sentence whether or not anything happened.
  Times are absolute UTC, never countdowns. A failed action says so.

### 4.6 The blind spot a review panel cannot fix

A panel that reviews *its own system's decisions* only ever sees traffic the classifier already
understands. A technique the corpus does not name scores nothing, is never blocked, never becomes
evidence, and is invisible **precisely because it is new**. That is a blind spot with a feedback
loop.

`attack_digest.unknowns()` looks at the other side of the line: sources that missed on many
**distinct** paths, minus everything the corpus already names. What survives is, by construction, a
technique the system cannot yet detect. The models propose detection rules for those; a
deterministic `vet()` refuses anything matching the app's own routes, anything that is not a valid
regex, and anything matching everything: **before** a human is asked. Survivors become
**detection**, never an automatic block.

---

## 5. Application three, release notes

**Files:** `release_notes.py` (PC side: facts), `webapp/backend/app/release_notes.py` (container
side: models + delivery), `tests/test_release_notes.py`.

### 5.1 The split

```
ship.py  ──(after deploy VERIFIED and safe-point tagged)──►  release_notes.gather()
                                                              │  git log, git diff,
                                                              │  gate result, test result
                                                              ▼
                                        ONE ssh session, facts JSON over stdin (BINARY)
                                                              ▼
                              docker exec colt-web python3 -m app.release_notes
                                    4 models write prose  →  Telegram + Gmail API
```

The facts are computed on the operator's machine because that is where git is. The models and the
delivery run in the container because that is where `OPENAI_API_KEY`, the Gmail credentials and the
bot token live, and where they will keep living: **secrets never enter git and never reach the
operator's PC**.

### 5.2 Two rules this obeys

1. **The deterministic facts ARE the notes.** Commits, files changed, gate result, test result and
   engine hashes are reproduced verbatim. The models add readable prose *on top*. With all four
   failing, the notes still go out and are still correct, and they say `written by 0 of 4 models`.
2. **It can never fail a deploy.** It runs after verification and after the safe-point tag. Every
   exception is caught. A mail server having a bad day must not turn a good release into a failed one.

### 5.3 The baseline is the last state that actually shipped

```python
prev = _git("rev-parse", "--short", "last-known-good^{commit}")
rng  = "%s..HEAD" % prev
```

"What changed" is measured from the last **safe-point tag**, not from the last commit somebody
happened to make. That is the honest baseline: the last state that reached production and verified.

### 5.4 Four independent write-ups, not a merged one

Release notes are the one application where the four answers are **not** reduced to a consensus.
Each model's headline, summary, customer-value list and watch-list is printed under its own name.
The reason: for prose, disagreement is information. When one model says "watch: the draft complaint
feature depends on ABUSEIPDB_KEY being set; its effectiveness without the key is untested", that is
worth more than an averaged sentence.

The delivery notes carry a `! watch:` line per model, and the message ends with a
**WHAT ACTUALLY CHANGED (deterministic, not model output)** block, so the reader can always tell
which half is measured and which half is written.

### 5.5 Delivery constraints worth knowing

- **SMTP is blocked outbound** on our host, so mail goes through the Gmail API. A test greps for
  `smtplib` and fails, because "fixing" this to SMTP has an obvious appeal and would silently stop
  every release note.
- **Telegram gets no Markdown when a keyboard is attached.** An attacker-controlled path can contain
  `_` or `*`, Telegram rejects the whole message as malformed entities, and the alert that matters
  most is the one that silently never arrives.

---

## 6. The shared engine underneath all three

All three call one function. That is deliberate: three copies of "call a model" is three places for
a per-model quirk to be rediscovered.

### 6.1 A chain, not a model

```python
_FALLBACKS = ["deepseek-3.2", "llama-4-maverick", "gemma-4-31B-it", "kimi-k2.6"]
```

- **Per model:** N attempts with exponential backoff honouring `Retry-After`, then failover.
- **The whole chain is bounded** by a wall-clock budget.
- **Head-weighted allocation**, not 1/N. The head gets ~55% of what remains, because it is the model
  we want to win. Equal slices once capped every model below the job's actual duration.
- **Never issue a request whose completion time exceeds its own timeout.** Size `max_tokens` to the
  slice it was given.

### 6.2 Per-model quirks are ENCODED, not rediscovered

```python
MODEL_PARAMS = { "kimi": {"temperature": 0.6, "_drop": ["response_format"], ...} }
```

Three lessons behind that one line:

- One model returns HTTP 400 with `"temperature must be 0.6 for this model"`. We sent 0.35. That was
  the entire bug, invisible for three rounds because **both the probe and the caller discarded the
  HTTPError body**, the one field containing the answer.
- **When an API rejects a request, repair WHAT IT NAMED.** A blanket "drop response_format" once
  also removed the flag suppressing chain-of-thought, producing 46,801 characters of thinking and a
  truncated non-answer. The generic remedy created a worse fault than the one it fixed.
- **Never discard an error body.** A 4xx is the server telling you what it wants.

### 6.3 Tolerate any SHAPE, never an EMPTY answer

`_json()` handles: a plain object, `[{object}]`, a bare array, trailing prose, and ```json fences.
Then `_contract_ok()` **rejects** anything that is not a dict, under ~50 completion tokens, or
missing every expected field.

A model once returned `{}` in 4 seconds with 3 completion tokens. It parsed fine, was recorded as
"ok", was charged for, and produced an empty artifact, a **silent quality failure**, strictly worse
than an honest fallback, because the log stops admitting anything is wrong.

### 6.4 Model ids must be probed, not assumed

A marketing name from a pricing page was put at the head of the chain and returned **404 on every
call for days**, silently degrading to the second model. `model_probe.py` runs **inside the
container** (where the key is) and fails the deploy if any id in the chain is absent from the live
catalogue, printing near-matches.

> A check that cannot see the thing it checks is not a check. The earlier version needed the API key,
> which lives on the droplet, so it printed "catalog unavailable, skipping" on **every** run.

### 6.5 A truncated answer is OUR ceiling, not the model's fault

`finish_reason == "length"` means `max_tokens` cut the JSON mid-string. The panel's own reviewer
was being cut off at 900 tokens while its contract permitted ~1,020 tokens of content, so a
reviewer answering *fully* was guaranteed to fail, and was then reported as "did not answer". It had
acquired a reputation for being erratic across two reviews. The error message now says whose fault
it is.

---

## 7. Porting it to jobhuntwow.com

jobhuntwow is a FastAPI app with SSE behind a shared reverse proxy, deployed by its own orchestrator
(`python jhw.py deploy`). Everything below assumes that shape.

### 7.1 What is generic and what is ours

| Component | Generic? | Notes for the port |
|---|---|---|
| `consensus()` quorum + median | **Yes, copy as is** | ~20 lines, no dependencies |
| Bounds + clamp-on-read | **Yes** | Change the key names; keep the *on read* part |
| `_decide_from_verdict()` | **Yes** | Pure function, fully testable, no I/O |
| Evidence contract `CHECK\|name\|ok\|detail` | **Yes** | Any shell or Python can emit it |
| Soldier / auditor prompts | **Mostly** | Replace the domain paragraph; keep the governance paragraph verbatim |
| `ARCH` briefing | **No, rewrite** | This is the map of *your* system. See §7.4 |
| The health checks themselves | **No, rewrite** | Yours are about SSE, job workers, the ATS integrations |
| Model chain + `MODEL_PARAMS` | **Yes** | Same vendors, same quirks |
| Delivery (Telegram + Gmail API) | **Yes** | Same constraint if SMTP is blocked |

### 7.2 Order of work

1. **Write the deterministic checks first.** A panel with nothing to read produces confident
   nonsense. Aim for 15-25 checks that each measure one property. Start with: container running,
   restart count, auth enforced, the app served with a *browser* user agent, a job actually
   completing end to end, the SSE stream delivering frames, DB reachable, disk, memory.
2. **Add the evidence contract and the sentinel.** One line per check, plus a terminal marker.
3. **Add the panel, advisory only.** Print the digest, decide nothing. Run it for a week and read
   what it says. This is the cheapest way to find out whether your evidence is rich enough.
4. **Add the governance rules** (`_decide_from_verdict`) once you trust the checks.
5. **Only then** consider letting it tune anything.

### 7.3 The checks that transfer directly to jobhuntwow

| Check | Why it matters there |
|---|---|
| `app_served` **with a browser UA** | If you have a bot gate, `curl` gets the 404 the gate exists to return, and the check records a broken app |
| `api_auth` returns 401 anonymous | Probing `/` alone goes green on a cached PWA shell |
| `job_completes` end to end | "The worker is running" is not "the worker works". Run a real short job and check the OUTPUT |
| `sse_delivers_frames` | Your product is a live stream; a stream that opens and never emits is the empty-200 of streaming |
| `engine_fresh` (sha256 in container vs repo) | **A liveness probe is not a deploy proof.** A three-day-old container answers 401 perfectly happily |
| `evidence_complete` post-reboot | See §3.4 |

### 7.4 The briefing is the highest-leverage thing you will write

`ARCH` in `quorum.py` is a factual map of the system, stating what each check **already measures**.
It exists because the panel repeatedly proposed fixes for checks that already worked that way. The
sections that earn their keep:

- **the physical facts** (how config reaches the process, what a bind mount pins, when a process
  re-reads its config);
- **what each check already measures**, per check, in one line;
- **what does NOT exist**, ours says plainly *there is no Kubernetes, no config-map, no hot-reload
  watcher; do not propose one, propose changes to files that exist.* Without that, a panel proposes
  plausible architecture it cannot see.

For jobhuntwow that means writing down: how a job is queued and who owns it, what the SSE stream is
and is not, which ATS integrations are live, what the deploy actually replaces, and what has no
equivalent in your stack.

### 7.5 Cost

Four reviewers × ~1,800 output tokens is a few tenths of a cent per run on open-weight models. Ours
is measured in a persistent SQLite ledger precisely so the figure is not a guess. At that price the
panel can run on every deploy and every 6 hours, which is what makes it useful.

### 7.6 The five mistakes to avoid, ranked

1. **Do not let the panel decide.** The moment a verdict depends on a model, an outage becomes a
   release blocker and a hallucination becomes an incident.
2. **Do not put a model in a request path.** Ever.
3. **Do not give the panel a briefing with a hole in it.** It will fill the hole confidently and you
   will spend a review slot per run on the same wrong call.
4. **Do not count what you received.** Know what you expect; missing evidence is a failure.
5. **Do not trust a check because it is green.** The single most valuable thing this panel has done
   is repeatedly identify that *the check was lying, not the system*.

---

## 8. The commercial argument

For a page or a deck, the defensible claims are architectural and checkable. Do not claim to beat a
named product without a published benchmark.

- **No shared failure domain.** Four vendors, not four hats on one.
- **The auditor is never the author, and never the same vendor.** Nothing marks its own work.
- **Code decides, models explain.** A 429 cannot block a release; an agreeable model cannot wave
  through a dead container. Both directions asserted by test.
- **Every proposed change is bounded, quorum-gated and takes the median**, so one confident model
  cannot drag the result.
- **Chain order is set by measurement on the real prompt.** Latency rankings *invert* between a toy
  prompt and a 13,000-character one; we measured a model at 3.3s on a synthetic probe and 44.6s on
  the real workload.
- **We run it on ourselves first**, and the panel's catch ledger, including the times it was wrong
 , is published rather than curated.

Honest limits to state alongside: this has not been benchmarked against any named product; the panel
is unreliable when extrapolating to architecture it cannot see; and the whole arrangement is only as
good as the deterministic evidence underneath it.

---

## 9. File map

| File | Lines | Role |
|---|---|---|
| `stagegate.py` | ~800 | CI/CD gate: deploy to twin, health, reboot, health, decide |
| `deploy/stagegate/quorum.py` | 239 | The CI/CD panel: 2 soldiers + 2 auditors |
| `webapp/backend/app/shield.py` | ~420 | Inline deterministic defence. **No model call** |
| `webapp/backend/app/shield_panel.py` | 214 | The defence panel: quorum + median |
| `webapp/backend/app/shield_tuning.py` | ~90 | Storage with a contract. Clamp on read |
| `webapp/backend/app/shield_console.py` | ~250 | AUTO / ASK / NEVER, Telegram authorisation |
| `webapp/backend/app/attack_digest.py` | ~200 | The blind-spot finder |
| `release_notes.py` | ~120 | Facts from git, on the operator's machine |
| `webapp/backend/app/release_notes.py` | ~190 | Four write-ups + delivery, in the container |
| `tests/test_gate_integrity.py` | 45 tests | The gate must not be able to lie |
| `tests/test_shield.py` |: | Behaviour **and** wiring |
| `tests/test_release_notes.py` |: | Same four models; no SMTP; cannot fail a deploy |

---

*Written 16 August 2026 from the running code. Every model id, constant, threshold and file path was
read out of the repository at that date. The incident dates and figures come from the run logs and
the engineering record in `CLAUDE.md`.*
