# The AI panel went "unavailable", and the governance step contradicted the gate — 22 Nov 2026

## It was not the key, and it was not the model

The operator's question was "why did a key change and one model change create multiple bugs". It
did not. The three ships before this one exited at `modelcheck` — the chain head was 403'ing, so
`ship.py` never reached step 3. Fixing the head is what let the pipeline run the staging gate and
its reboot test for the first time in days. Everything below was already broken; it had simply not
been reached.

That is worth saying plainly because the opposite conclusion — "the last change broke it" — is the
one that gets a correct fix reverted.

## What the gate reported

    post_reboot_api_auth     FAIL  GET /api/me -> 000 (want 401)
    post_reboot_app_served   FAIL  GET / -> 000
    post_reboot_bot_gate     FAIL  bot UA got 000 (want 404)
    post_reboot_engine_fresh FAIL  container=76c8ad95fea9 shipped=8154ea820d55
    post_reboot_proxy_routes OK    proxy -> colt-web -> 401 (the production path)
    post_reboot_concurrency  OK    40 parallel requests -> 40x401

    AI panel unavailable — gate decided by 44 deterministic checks (4 failed).
    STAGING GATE: NO-GO
    ...
    No failed checks. Nothing to remediate.

Three separate defects.

## 1. The panel cannot survive the reboot it is asked to judge

`run()` copies `quorum.py` into colt-web with `docker cp` — the container's **writable layer** —
and that copy happens before the reboot test. Anything that replaces the container in between
takes the reviewer with it. The panel then reports itself "unavailable", which is true of the
panel and useless as a diagnosis: the real fact is that its own code is no longer in there.

`post_reboot_engine_fresh` in the same run proves the container's bytes changed, which is that
replacement.

The copy is idempotent and costs nothing, so it is re-done in the session that asks the question,
and the container is **asked** whether the file is present (`PANEL_NO_REVIEWER`). A missing
reviewer, a dead gateway and a missing key were one sentence; now only the first is claimed, and
the other two stay honestly unexplained.

## 2. The fallback verdict dropped the failures

`govern.py` reads `verdict["failed"]`. The fallback dict never had that key, so a NO-GO carrying
four failures printed *"No failed checks. Nothing to remediate."* two lines under the gate's own
*"(4 failed)"*. Class 1 in its purest form: the step could not see its subject and reported its own
blindness as a finding about the system.

`fallback_verdict()` is now one home, it carries the failed checks, and `govern.run()` rendering
them is asserted separately — behaviour and wiring, because the first is invisible without the
second (class 9).

## 3. "the container is NOT running what we sent" names a symptom

A stale build and a replaced container produce that identical line and need opposite repairs.
`container_identity` prints id, image, start time and **published ports**, before and after the
reboot, because one identity line means nothing without the other to compare it against (class 26).

The ports matter for the other half of this run. `api_auth`, `app_served` and `bot_gate` curl
`127.0.0.1:8090`; `proxy_routes` goes over the docker network. An unpublished port makes the first
three read 000 — "the app is down" — at the same moment the proxy is getting 401s off that very
container, and 40 parallel requests are all answering. Four checks that cannot all be true, with
nothing on screen to separate them. The binding turns it into one readable fact.

## What is still unknown, and deliberately so

Why the staging container is replaced across a reboot, and whether 8090 is simply unbound
afterwards. Both are answerable only from the box, and the next gate run prints exactly the
evidence that decides them. Guessing a cause and building on it is the failure recorded twice in
CLAUDE.md's class 29; the repair here is to make the measurement, not to pick a story.

Five mutations, five caught, including reverting the reviewer copy to its pre-reboot-only position
and dropping `failed` from the fallback.
