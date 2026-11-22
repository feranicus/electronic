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
