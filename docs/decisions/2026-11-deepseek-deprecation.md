# deepseek-3.2 deprecated — 22 November 2026

DigitalOcean is retiring `deepseek-3.2` and recommends **DeepSeek V4.1 Flash 1017**: 552B
parameters against 680B, a 1,048,576-token context window against 163,840, and cheaper on every
axis — $0.30/$1.20 per 1M in/out against $0.50/$1.60, cache reads $0.006 against $0.15.

## The id, and why I did not take it from the email

This repository has a scar for exactly this. `deepseek-v4-flash` was read off DigitalOcean's
**pricing page**, put at the head of the chain, and 404'd on every assessment for days while the
chain silently degraded to the next model. **A marketing name is not an API id**, and the only
authority on an API id is the API.

The chain head is now `deepseek-v4.1-flash`, and the evidence for that spelling is three
independent things rather than the email:

1. `model_watch.MODEL_PRICES` already carried `"deepseek-v4.1-flash": (0.30, 1.20)` with the
   comment "DO's recommended successor" — somebody had already read DO's own page.
2. Those prices are **exactly** the pair in the deprecation notice: $0.30 in, $1.20 out.
3. DigitalOcean serves dated snapshots while the callable id is undated — `deepseek-3.2-0813` is
   recorded in `test_jhw_llm_events.py` as the dated form of `deepseek-3.2`. "1017" is the
   snapshot, not the id.

That is a reasoned conclusion, not a verified one, and the difference matters. Which is why:

## The catalogue is now asked BEFORE the deploy

`ship.py` already asserted that every chain model exists in the live catalogue — in `do_verify()`,
**step 5**, after the image is built, scanned, pushed through the staging gate and running in
production. A wrong id is therefore discovered by production, and the repair is a second full
deploy.

`modelcheck.py` asks the same question before anything moves. It reads the chain from **this
checkout** (the container is still on the old image, so its chain is not the thing being verified),
asks the catalogue from inside colt-web where the key lives, and on a miss prints every id that
vendor actually serves. An UNKNOWN — no key, catalogue unreachable — is reported and does **not**
block: this check must not become a reason a release cannot ship when the gateway is what is down.

It does not pick a model. A resolver that chose the "closest" catalogue entry would be the
`deepseek-v4-flash` mistake with more machinery.

## The head had fifteen homes, not one

CLAUDE.md said `enrich._FALLBACKS` is the ONE HOME for the chain. True of the chain; false of its
**head**, which is separately hardcoded as a fallback default in eleven other files — the shield
panel, release notes, settings, the staging quorum, proteus, audit_fp, author_geopol,
cassandra-bot, patchwatch and its provisioner, and `defense.js` in the browser. They are separate
deployables and genuinely cannot import the one home.

I found them with a grep, which is the method class 35 says not to trust. So
`tests/test_model_chain.py` now derives the set: every model id written anywhere in the tree must
either track the chain head, or be listed with a reason (price tables that must still price retired
models, bake-off probes, the two runaway models from the 2026-09-01 incident). A twelfth file that
starts hardcoding the head fails the suite instead of being discovered during the next deprecation.

It also asserts the two price tables agree about the head, and that no two chain models share a
vendor — a chain of four from one vendor is one model wearing four hats.

## The key

A new DigitalOcean key is a credential, and `set_secret.py` is its path. But the engine reads the
inference key under **two** names, `OPENAI_API_KEY` and `DO_INFERENCE_KEY`, and `enrich.py` carries
the scar: setting one left the old key parked in the other, the file-order resolver picked the
stale one, and the bake-off's own fingerprint proved it (`3c6b3a6a832e` vs `5847c2bbe7cd`).

`set_secret.py` now writes **both** when either is named. Writing one and leaving the other is not
a half-done job; it is a credential that looks right and silently is not.

## It shipped, and it 403'd — the check was blind to the fault that happened

Release `good-20261122-200100` went out green. `modelcheck.py` passed, the staging gate passed,
and then the Verint run said:

    [warn] enrich: model 'deepseek-v4.1-flash' returned HTTP 403 (not entitled)
    [enrich-mr] shard 0: 0/3 ids in 261ms  ERROR: HTTP Error 403: Forbidden
    [enrich-mr] shard 4: 0/1 ids in 144ms  ERROR: HTTP Error 403: Forbidden

**The id is right.** 403 is not 404. The model is in the catalogue and the gateway knows it; the
KEY is not granted it. Three of the four chain models answered on the same key in the same run,
which rules out the two blanket causes DigitalOcean documents — a paused key and a VPC-scoped key
both refuse everything, not one model.

**And my check measured the wrong thing.** It asked `/models` — does DigitalOcean *list* this
model — and called the chain verified. CLAUDE.md has carried the rule the whole time:
*"Entitlement is not visibility: every `anthropic-*` and commercial `openai-gpt-*` returns 403 on
this account."* I built a guard against the previous incident (`deepseek-v4-flash`, a 404) and it
could not fail for the reason that actually occurred. Class 1 and class 3 in one check.

`modelcheck.py` now issues a REAL one-token call per chain model and gives the three outcomes three
different diagnoses, because they have three different repairs:

| | meaning | repair |
|---|---|---|
| 200 / 400 | usable (400 = the model wants its own payload; kimi does this) | none |
| **403** | the id is right, the KEY is not entitled | DigitalOcean console: grant the model to the key |
| **404** | the id is wrong | `enrich.py::_FALLBACKS` |

It also prints the key's sha256 fingerprint and length, because "did the new key actually land?"
is the first thing you need and a 403 cannot answer it. Never key material: this repo is public.

The HEAD is treated differently from the rest. The chain is built to degrade, so an unusable model
at position 2+ is a warning and does not block a release — making this check the reason a release
cannot ship would be its own defect. An unusable head costs every call a wasted round-trip first,
which is exactly what those 261ms and 144ms shards were.

Six mutations, six caught, including the decisive one: reverting to the catalogue-only logic fails
three tests, one of which replays the Verint 403 verbatim.

## And the 403 was not entitlement either — the credential had a home nobody wrote to

The new key was installed, `set_secret.py` reported `set, 71 chars`, and the bots kept 403'ing.
Measured on the checkout, which is where the answer had been the whole time:

    assess-bot/.env      OPENAI_API_KEY / DO_INFERENCE_KEY   sha256 b4bb02748df6   (new)
    cassandra-bot/.env   OPENAI_API_KEY                      sha256 9327f18662ac
    cassandra-bot/.env   last written 2026-07-08

`cassandra-bot` loads `env_file: cassandra-bot/.env` in all three compose files and reads the same
`OPENAI_API_KEY`. `set_secret.py` wrote one file. The operator's objection was reasonable — the key
*was* touched eleven days ago, when two chain models were swapped — but a key's model list changing
in the DigitalOcean console and a file on disk being written are different events, and the file's
mtime settles it: nothing created eleven days ago can be in a file last written in July.

`deploy.py::BOTS_SECRETS` packs **both** files, so every `--reuse` deploy re-shipped the stale half.

Two defects with two repairs:

1. **The files.** The write set is derived by reading them, and the file list comes from
   `deploy.BOTS_SECRETS` — one home for "what gets shipped". A file that does **not** hold the
   credential is NAMED, never silently written: an env file with no inference key points at a
   service nobody configured, which is a different fault.
2. **The containers.** A container's environment is baked at creation. `docker restart` re-executes
   the process with the OLD environment, so a merely-restarted consumer keeps the stale credential
   and then returns a perfectly accurate 403. Every consumer is recreated, derived from compose's
   own labels and filtered to project `colt-stack` so Amnezia VPN, VideoDead and joplin are
   untouched.

### The first run fixed the credential and broke the artifact

It worked — `colt-web`, `colt-assessbot` and `colt-cassandra` all came back `b4bb02748df6`, and a
fourth home nobody had listed turned up on the droplet (`jobhuntwow-app/.env`, written because it
already held the key). But the run also printed this:

    recreated from /opt/colt-stack/docker-compose.ghcr.yml
    recreated from /opt/colt-stack/docker-compose.reuse.yml
    recreated from /opt/colt-stack/docker-compose.web.yml

and the second pass, moments later, listed only two — `ghcr.yml` was no longer claimed by any
container. Several compose files define the **same** services: `ghcr.yml` pulls the image CI built
and scanned, `reuse.yml` builds it locally. Looping over files and running a bare `up -d` applied
each definition in turn, so the bots were created from `ghcr.yml` and then again from `reuse.yml`.
Last one wins, and "ONE ARTIFACT" — the rule that the only internet-facing image is the one CI saw
— was broken by the script meant to fix a credential.

A container's own labels carry the exact `-f` list it was created from, so the repair is to rebuild
*that* invocation and name only *that* service: `up -d --force-recreate <service>`. A compose file
no running container reports is never applied. And the verification now prints each container's
image ref beside its key fingerprint, because recreating a container is precisely when its image
can change and an unprinted change is one nobody can catch.

Four more mutations, four caught, including reverting to the per-file loop.

`set_secret.py --audit` answers "which value does each home hold" with sha256 prefixes, and
`ship.py` reports divergence without blocking (the `report_requirement_drift` precedent — these
files are gitignored, so CI has none of them and must not deliver a verdict about them).

Seven mutations, seven caught — after the first run **missed** one. The project-filter assertion
read the whole docker log, and the later verification pass lists containers with the same filter,
so its line kept the test green while the recreate set had gone host-wide. Anchored on the `ps -q`
selection call instead (class 4, again).

## It was never the credential, and my own check said it was

With all four homes agreeing on `b4bb02748df6` — the key the DigitalOcean console shows holding
five models including DeepSeek V4.1 Flash 1017 — the next ship said:

    KEY     fingerprint b4bb02748df6, 71 chars
    CATALOG 78 model(s) visible on https://inference.do-ai.run/v1
    FORBIDDEN deepseek-v4.1-flash  in the catalog but this KEY is not entitled to it.
    OK      openai-gpt-oss-120b    usable
    OK      mistral-3-14B          usable
    OK      kimi-k2.6              usable

Three models answer on that key, so it is not paused, not VPC-scoped and not stale. The credential
theory is dead, and the line that killed it was one I wrote.

**`visible` was computed and then ignored.** The function asks `m in ids` and never reads the
answer: every 403 printed "in the catalog but this KEY is not entitled to it" regardless. That is
class 7 — a detail that renders identically whether or not anything was measured — and it sent the
operator to the console to grant a model to a key that already had it. The evidence needed to
settle it was sitting in the same function, in a variable, unused.

DigitalOcean answers an **unserved** id with 403 as readily as an **ungranted** one, so the
catalogue is the only thing that separates them, and the repairs are opposite: the console, or
`enrich.py::_FALLBACKS`. The verdict now says which it measured, and the NEAR line prints every
deepseek id this key actually sees — on entitlement cases too, not only on a 404.

The docs do not settle the id either. The migration note says DeepSeek V4 Flash moves to
`deepseek-v4.1-flash-1017`; the supported-models table still lists `deepseek-4-flash` and does not
carry the V4.1 slugs at all; the pricing page names both "DeepSeek V4.1 Flash" and "DeepSeek V4.1
Flash 1017". Three DigitalOcean pages, three answers. **That is exactly why this check asks the
API** — a marketing name is not an API id, and guessing `deepseek-v4-flash` off a pricing page is
the scar that started all of this. The next run prints the served ids, and that is the authority.

`SHIP_ALLOW_BAD_HEAD=1` was added alongside it. CLAUDE.md says a guard an informed operator cannot
override is a bug, and this one had no escape hatch: the chain is built to degrade, so an unusable
head is a tax on every call, not an outage, and it must not be the reason a release cannot ship
once the operator has read the evidence.

## The answer: they are two different models

With the NEAR line finally printing, the gateway's deepseek offering is:

    deepseek-3.2, deepseek-v4-flash-0731, deepseek-v4-pro, deepseek-v4-pro-0813,
    deepseek-v4.1-flash, deepseek-v4.1-flash-1017

`deepseek-v4.1-flash` and `deepseek-v4.1-flash-1017` are **two separate models**, not an id and
its dated snapshot. The operator's key grants, by its console entry: Deepseek 3.2, **DeepSeek V4.1
Flash 1017**, Kimi K2.6, Ministral 3 14B, OpenAI GPT-oss-120b — which is exactly the three models
that answered plus the one that did not. The chain was calling `deepseek-v4.1-flash`. The key
grants `deepseek-v4.1-flash-1017`. The 403 was correct every single time.

**The reasoning that put the wrong one in was recorded in this very file**, under "The id, and why
I did not take it from the email": *"DigitalOcean serves dated snapshots while the callable id is
undated — `deepseek-3.2-0813` is the dated form of `deepseek-3.2`. '1017' is the snapshot, not the
id."* That generalised from one model to another and was wrong, and it was written down
confidently enough that three later diagnoses took it as settled and went looking at credentials
instead. A reasoned conclusion recorded beside measured facts gets read as a measured fact.

**Two separate checks could each have ended this on day one and neither did**, for the same
reason: both treated "the id is listed" as "the id is right".

  * `modelcheck` computed `visible` and never read it, then announced entitlement (class 7).
  * The NEAR line printed only on a 404, so the 403 path never showed the sibling ids at all.

The verdict now says only what /models can support — the gateway serves this id, therefore it is
not a typo, and that is *not* evidence about entitlement, because the catalogue returns 78 models
while this key grants 5. Then each sibling is **called**, and the ones that answer are named. It
still does not pick a model: `deepseek-v4-flash` got in because a name looked right, and a
resolver that quietly chose the closest entry would be that mistake with more machinery.

Four mutations, four caught, including reverting the verdict to the line that claimed entitlement.

## Mistakes made while doing this

**I rewrote history.** The bulk rename skipped lines starting with `#` and `//` but not
**docstrings**, so a line inside `_chain()`'s docstring describing an August incident became a
claim about a model that did not exist in August. Restored, and `test_model_chain._code_lines()`
strips docstrings for exactly this reason.

**An engine test had the fallback pair typed out by hand.** `audit_fp._pick_auditor` names a
last-resort pair twice in one function; I changed one copy, and `test_recall`'s "every model
authored → refuse" check stopped exhausting the list, so an auditor was found where the test
expected a refusal. The pair is now `audit_fp.LAST_RESORT`, one home, and the test reads it.

**A doctrine test pinned the head by name.** `check(_E._FALLBACKS[0] == "deepseek-3.2", "chain head
is the model MEASURED fastest")` — the head *was* chosen by measurement, and that principle stands,
but a vendor retiring a model is not a measurement. The pin meant the retirement broke the suite
instead of the chain reporting it. Rewritten to the property it stood for (the slowest measured
model is last, never the head), with the old line kept above it.

**My own guard had two false findings on its first run**, and both would have sent somebody to
"fix" correct code: `audit_fp`'s vendor-stem list `("deepseek", "llama", ...)` read as model ids,
and a German locale string "DeepSeek-Texte". A model id carries a version; a vendor does not.

Seven mutations on the derived guard, seven caught.
