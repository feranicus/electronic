# The deck author is a set, and the self-audit guard was comparing against None (11 Nov 2026)

No new rule. CLAUDE.md has said since the skon.de incident that **the FP auditor is never the
author and never the author's vendor**. This is the day we found it had stopped being enforced.

## What the verint run printed

    [enrich-mr] shard models: deepseek-3.2 x3, openai-gpt-oss-120b x3, mistral-3-14B x3
    ...
    FP-AUDIT: auditor=openai-gpt-oss-120b  vs  deck-author=?  ->  verdict=dirty  flagged=9

`openai-gpt-oss-120b` wrote three of the nine findings it then reviewed. The guard did not stop it
because the guard had nothing to compare against: `deck-author=?`.

## Why

`audit_fp` read the author from `target.qwen.model` — the model that WON the serial chain. That was
correct when enrichment was a serial chain with one winner. Two things have changed since:

1. most estates are now enriched by the **shards**, where three or four models each write a slice,
   so there is no single author; and
2. when the whole-estate call is skipped as infeasible — which is what happened here, 9 findings
   needing ~270s against a 175s slice — the serial chain never runs at all, so the field is
   **null**.

`_pick_auditor(None, chain)` then returns the first chain model whose vendor differs from
`_vendor(None)`, which is a comparison against nothing. **A guard that cannot fail is not a
guard** (class 3), and this one could not fail on any sharded run.

## The fix

- `enrich_parallel.run()` reports `authors`: every model whose shard actually **returned** ids. A
  shard that was planned for a model and then failed authored nothing, and naming it would deny
  the deck an auditor it is entitled to.
- `run_assessment` records that on `target.enrich_authors`.
- `audit_fp.authors_of()` is the ONE HOME for "who wrote this": the shard authors, unioned with the
  serial winner, falling back to the chain head only when nothing recorded an author — which is
  what the field meant before the shards existed.
- `_pick_auditor` takes the **list** and excludes every member, preferring a vendor that authored
  nothing. When every available model wrote part of the deck it returns `None` and the caller
  reports `unaudited`, because faking independence is worse than admitting there is none.
- The FP-AUDIT line names every author with its vendor (class 26). `deck-author=?` told the reader
  nothing, and the whole point of the line is to let a human confirm the auditor is not one of them.

Two incidental repairs on the way:

- A bare string passed as `authors` would iterate as characters, and `m not in "deepseek-3.2"` is
  true for every model id — the exact silent-success shape this function exists to prevent. It is
  coerced, and a check asserts it (class 36).
- `_call_shard`'s exception path omitted `model`, so the per-shard log printed `(?)` for precisely
  the shards worth investigating, and "which vendor is having a bad minute" — the question
  round-robin exists to answer — could not be read off a run at all.

## Proof

`test_recall.py` section 13, rewritten with the original single-author reasoning kept beside it
(class 17), plus section 20 for the wiring. Six mutations, six failures:

| mutation | caught by |
|---|---|
| `authors_of` ignores the shard record (the verint bug, restored) | section 13 |
| the string coercion is removed | section 13 |
| return a model instead of `None` when everyone authored | section 13 |
| authors taken from the PLAN rather than from what returned | section 20 |
| the engine never records `enrich_authors` | section 20 |
| the failure path forgets the model again | section 20 |

249 checks in recall, 1,252 in `tests/`.

## Open, not fixed here

The same run flagged the throughput table twice:

    measured mistral-3-14B:       58.9 tok/s  (table 15)  !! >2x off
    measured openai-gpt-oss-120b: 41.6 tok/s  (table 15)  !! >2x off
    measured deepseek-3.2:        37.3 tok/s  (table 20)

`enrich.MODEL_TOK_S` drives the feasibility arithmetic, so the stale table is why the whole-estate
call was skipped: at the measured 37.3 tok/s, 9 findings x 600 tokens is ~145s against a 175s
slice, and it would have fitted. One call per model is one sample, though, and a table tuned too
high produces shards that cannot finish — the failure mode the budget arithmetic was built to stop
after AS37468. Needs several runs, or a table derived from the cost ledger rather than written by
hand.
