# Stopping an assessment — and never showing a dead one as live (11 Nov 2026)

## What happened

The operator started an assessment of `verint` from cybergod.ai/app, then ran `python ship.py` for
an unrelated change. The deploy recreated `colt-web`. The page went on showing:

    AI enrichment: improving prose + auditing vs methodology        88% · 7m 07s
    ⚠ Reconnected to an assessment already running on the server.

for as long as he left it open. Refreshing re-attached. Logging out and back in re-attached. There
was no control anywhere in the product that ended a run, and no mechanism behind one.

## Two defects, not one

**1. There was no cancel.** Not for a stuck run, not for a run the operator simply changed his mind
about. A paid pipeline — Shodan queries, four model vendors — that a person starts and cannot stop
is not finished software. The absence had never been noticed because runs normally end on their
own in three to seven minutes.

**2. A run that was not running was indistinguishable from one that was.** `_RUNNING` in `main.py`
maps `job_id -> asyncio.Task`. It is **in-process state**. The DB row is **durable state**. When the
container was recreated the first vanished and the second did not, so `status='running'` outlived
every process that could have been doing the work. The browser's re-attach believed the row.

This is class 1 in its purest form: the page reported a state nobody had measured. The measurement
already existed — `/api/assess/{job}/status` has returned `"running": job_id in _RUNNING` since it
was written — and the frontend ignored it in favour of the label.

## What was built

**The reaper.** `_reap_orphans()` runs in an `@app.on_event("startup")` handler. At boot, every row
still marked `running` belongs to a process that no longer exists — not probably, not after some
grace period: **by construction**, because `_RUNNING` is empty and this function runs before this
process can start anything. Those rows become `interrupted`, and the reason is appended to each
job's own `run.log`, because the next thing a person does is open the log and ask what happened.
It is deliberately synchronous inside the hook rather than a background task: a reap that lands
after the process has begun accepting work could mark a live job as an orphan.

**The cancel endpoint.** `POST /api/assess/{job_id}/cancel`, owner-scoped, idempotent, and honest
about which of two cases it hit. If the job is in `_RUNNING` it cancels the task; the existing
`CancelledError` handler kills the engine subprocess and the row becomes `cancelled`. If the row
says running but this process does not own it, there is nothing to kill and the row is corrected to
`interrupted`. The response carries `stopped`, because *"we killed it"* and *"there was nothing to
kill"* are different facts and a button that reports the same thing either way teaches nobody
anything.

A cancel arrives as the same `CancelledError` as a server shutdown, so the endpoint records the
intent in `_CANCELLED` before cancelling. Without that, a deliberate stop and a dying container
would be written to the database identically.

**The wall.** `JOB_WALL_S` (default 2700). The engine bounds its own phases — `RECON_BUDGET_S`,
`ENRICH_WALL_S` — but nothing bounded the subprocess as a whole, so a hang anywhere outside those
two phases ran until somebody recreated the container. It is a watchdog task rather than a
`wait_for` around the read loop, because a timed-out run must keep every line it already produced
and `wait_for` would discard the partially consumed stream. The ending is `timeout`, not `error`:
the time limit is the one fact that explains it.

**Four endings, four sentences.** `cancelled`, `timeout`, `interrupted`, `error`. The SSE error
frame now carries `status`, and both pages render the matching sentence. "Assessment failed"
described all four, and three of them are not failures.

**`ENGINE_PYTHON`.** The engine command was a hardcoded `python3`. In the container that is right;
on the operator's Windows box `python3` is a Store alias that opens a shop, so the subprocess path
could not be exercised anywhere but production. A test that cannot run the real code is a test of a
copy of it (class 2), so the interpreter name has one home and an env override.

## How it is proved

`tests/test_job_cancel.py`. The lifecycle scenarios run in their own interpreter — `DATA_DIR` and
`JOBS_DIR` are read at import time and `app.main` is already imported by other test files in the
same session — and hand measurements back as JSON. That buys more than isolation: the real ASGI
app, a real asyncio task and a **real engine subprocess** are exercised, because "cancelled" has to
mean a pid is gone, not that a dictionary entry was removed. The fake engine writes its own pid
into its `--outdir`, so the test reads the number the process reported rather than guessing it.

Fixture proofs first (class 12): the orphan row is asserted `running` before the reaper touches it,
and the engine pid is asserted alive before the cancel.

Five mutations, five failures:

| mutation | caught by |
|---|---|
| remove the startup decorator from the reaper | `test_the_reaper_runs_on_startup_and_not_in_the_background` |
| cancel flips the row but does not `proc.kill()` | `test_cancel_kills_the_real_engine_process` |
| drop the ownership check in the endpoint | `test_a_stranger_cannot_stop_somebody_elses_assessment` |
| remove the watchdog | `test_a_run_past_its_limit_is_killed_and_labelled_timeout` |
| write `error` where a cancel writes `cancelled` | `test_cancel_kills_the_real_engine_process` |

## What this did not fix

The deploy that caused it is still the right thing to do mid-run — the stack has no drain. A ship
during an assessment still ends that assessment. What changed is that it now ends *visibly*, says
so in the job's own log, and leaves nothing for the page to misread.
