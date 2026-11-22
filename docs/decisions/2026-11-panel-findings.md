# The 22 November staging panel — what was right, what was wrong

Two soldiers said GO, two auditors said NO-GO. The deterministic checks decided the gate, as they
always do; the standing rule is that the panel's findings become a check or a fix in the same
change, never a note. Five claims. Two were right and are now built. Three were wrong and the
reasons are written down here, because a finding dismissed without a reason gets re-raised every
run and trains the operator to skim the panel.

---

## RIGHT — kimi-k2.6: a detail cited evidence that did not exist yet

> Post-reboot: `config_write_ordering` (21s) runs, but `mount_fresh` and `config_drift` run LATER
> in the sequence (checks 41 and 46 vs 38). The disclaimer "WHAT it read is proven by mount_fresh
> + config_drift" is false at the moment the check passes. … This is a check defect, not a system
> defect.

Exactly so, and the model was careful to say which half it was accusing. Checks run in source
order. Check 38 was citing checks 41 and 46 as proof of a question it had deliberately not
answered itself. The system was healthy — `mount_fresh` showed the same hash before and after, and
`config_drift` passed both times — and the detail was not.

This is defect class 8. An operator who reads "proven by X" stops looking; if X later fails, he has
already been told the question was settled. The detail now says what the check measured (ORDER),
names where the content question is answered, and says plainly that those checks run later in the
same gate and should be read on their own.

**The generalisation, which is the part worth keeping.** `tests/test_gate_claims.py` parses every
`chk <name> yes|no "<detail>"` in `stagegate.py`. If a detail uses claim vocabulary — proven,
proves, confirmed, verified, established, covered — about another check, that check must appear
EARLIER in the file. Pointing forward is fine; claiming proof from the future is not. The exact
wording that shipped is replayed through the matcher, so the guard cannot be quietly loosened, and
the repaired wording is asserted NOT to trip it, so the fix stays shippable.

---

## RIGHT — mistral-3-14B: the clause that mattered was never measured

> The check explicitly states it does NOT test bare file edits … yet this is the exact failure mode
> that caused the 2026-08-07 outage.

`guard_write_path_reloads` proves the happy path: a change written through `apply()` reaches the
running config. Its detail then asserted the other half in prose — "a bare file edit does NOT
propagate, because Caddy reads its config at start or on reload". That clause is the whole reason
the write path exists, and nothing measured it. A rule carried in a PASS string is a comment.

The reason it stayed unmeasured was sound: an earlier negative test wrote a broken fragment into
the live blocks directory and took staging down. Editing the live shared config to watch it fail is
an outage with a pass/fail label.

So the experiment moved to where it costs nothing. `agent.py staleproof` starts a **throwaway**
caddy on the proxy's own image, with its own config file, and runs the real sequence:

1. baseline — the throwaway serves `a.invalid` and not `b.invalid`
2. the 2026-08-07 action — the file is edited in place to add B, no reload
3. **the claim under test** — the running config still does not serve B
4. the repair — the config is loaded through the admin API, exactly as `apply()` does
5. the control — the running config now serves B

Steps 1 and 5 are what stop step 3 passing for the wrong reason: a container that came up dead, or
one that accepts no change at all, would score "B is not running" perfectly every time. Both are
asserted, and both are covered by their own tests. The live config's hash is compared before and
after and printed in the PASS detail. RFC 2606 `.invalid` names are used so a test vhost cannot
collide with or be routed to anything real, and `auto_https off` stops the throwaway trying to
obtain a certificate for them.

The gate runs it as `bare_edit_does_not_propagate`, and a SKIP is scored as a FAILURE — we are
already inside the branch that found a caddy container, so an experiment that could not run means
the gate learned nothing.

**Proved without docker.** Docker is not on every machine the suite runs on, and a `shutil.which`
skip hides a defect from the machine that needs it — `test_caddy_wiring.py` learned that when it
skipped on Windows, was never reached in CI, and left two red tests unseen for weeks. So docker is
SIMULATED (class 20): a fake `sh` models a caddy that serves what it was last told, a second models
the hypothetical one that hot-reloads on write, and the tests assert the stub was consulted.

---

## WRONG — mistral: "config_drift relies on cmd_drift, only valid if the config was reloaded; a stale mount would produce a false positive"

Config has three hops and each is measured separately: host file → container file (the MOUNT) →
running config (the RELOAD). `cmd_drift` checks the mount FIRST and returns before comparing
anything if it is stale. A stale mount is precisely what `mount_fresh` exists to catch, and it
cannot produce a false positive in `config_drift` because `config_drift` never gets that far.

That ordering is not incidental. The first version of the drift check compared only hops 2 and 3,
both read from inside the container, so a stale single-file mount made both sides agree perfectly
on the wrong bytes and the check reported OK over a dead site.

## WRONG — mistral: "mount_fresh only verifies the container sees the current inode, not that it was reloaded"

True, and by design — that is `config_drift`'s question. This names a division of labour as a gap.
A check that answered both would be the overclaiming check the finding above is about.

## WRONG, for the estate — kimi: "no check exercises TLS on :443; a certificate problem would not be caught"

Right about staging in isolation, wrong about the system. Staging has no public DNS and no real
certificate, so there is nothing there to exercise. Production is where it is measured: `caddyguard`
prints days-to-expiry for every domain on every ship (a lapsed certificate takes all of them down
together), and the OUTSIDE VIEW probes each site over HTTPS from off-box. Both ran on this release.

## PARTLY RIGHT, not acted on — kimi: "no check verifies the HOST file is the INTENDED file"

The authenticity comparison exists — `caddyguard` compares each fragment against its committed
block and reported `colt:cybergod matches the committed block (no host-side edit)` on this run —
but it runs in the production path, not in the staging gate. Consistency across the hops is not
authenticity, and the model is right that staging proves only consistency. Recorded rather than
built, because the committed-block comparison on staging needs the fragment roster that staging
deliberately does not carry; it is one vhost on :8080, not the estate.

---

## What was proved

Nine mutations, nine caught, both files restored byte-for-byte:

| mutation | caught by |
|---|---|
| the baseline assertion is dropped (passes on a dead container) | the serves-nothing test |
| the control is dropped (the bare-edit result proves nothing) | the ignores-loads test |
| the live-file hash comparison is dropped | the meddling test |
| the throwaway is never cleaned up | four tests |
| the in-place edit never happens | three tests |
| the gate scores a SKIP as a pass | the wiring test |
| the gate stops running the experiment | the invocation test |
| the overclaiming wording comes back | the claims test |
| the verb is no longer dispatched | the reachability test |

Two of my own checks were class-4 defects on the first attempt — one grepped for `docker run` when
the code builds a list, one searched for a sentence that the source wraps across two lines with
implicit concatenation. Both reported a missing feature about code that had it. And one of my
mutations was invalid: `if h0 != h1:` appears twice in `agent.py`, so it landed in `cmd_selftest`
and proved nothing. Every mutation is now asserted unique before it is applied.
