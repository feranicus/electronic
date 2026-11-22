# The AI panel went "unavailable", and the governance step contradicted the gate — 22 Nov 2026

## My first answer was wrong, and the operator was right to refuse it

I wrote that these were pre-existing failures the pipeline had simply never reached, because the
three previous ships exited at `modelcheck`. The operator pushed back: RBAC and Pipeline shipped
fine earlier the same day with the same four models.

He is right, and it is checkable — `good-20261122-200100` is a tag on this repository. A full ship
went green at 20:01, which means the staging gate, the reboot test and the AI panel all worked
today. "Never reached" was false, and it is the comfortable kind of false: it explains a failure
without implicating anything I changed.

The diff from that green commit to the failing one is one-line model-id renames, `modelcheck.py`,
`set_secret.py` and `ship.py`. Nothing in that set can make a staging container stop answering.

## It is a race, which is why it passed at 20:01 and failed at 21:15

`wait_for_reboot()` waits for a new boot_id **over ssh** — the box. sshd is serving within seconds;
colt-web is python, uvicorn and the engine coming up behind docker's restart policy, and it is not
ready for a while after that. The post-reboot health run started the moment ssh answered.

The evidence was in the same output all along:

    post_reboot_api_auth     FAIL  GET /api/me -> 000
    post_reboot_app_served   FAIL  GET / -> 000
    post_reboot_bot_gate     FAIL  bot UA got 000
    post_reboot_proxy_routes OK    proxy -> colt-web -> 401
    post_reboot_concurrency  OK    40 parallel requests -> 40x401

`concurrency` probes **the same `127.0.0.1:8090`** and got forty 401s a few checks later. The app
was not down. It was not up yet. `engine_fresh` has the same shape: a `docker exec` into a
container still unpacking reads fewer files, and `md5sum` over a shorter input is a different
12-char hash, which renders as "the container is NOT running what we sent".

Class 15 — a test that depends on a race teaches the operator to re-run rather than read — and
this one taught both of us to blame the last thing that changed.

The wait is bounded (180s), it reports the seconds either way, and exhausting it is a FAIL
carrying that number. A readiness wait that hides a genuinely dead app would be worse than the race
it closes. It is injected after `chk()` is defined rather than prepended, because `chk` is the
CHECK-line protocol and has one home; the anchor is asserted rather than assumed, since a silent
no-op injection would restore the race with nothing saying so (class 37).

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
