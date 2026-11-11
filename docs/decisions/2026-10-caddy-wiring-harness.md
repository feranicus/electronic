# A test that cannot run anywhere has no baseline (15 Oct 2026)

Moved out of CLAUDE.md on 11 Nov 2026 to stay inside the per-turn context budget. The RULE stays
there; this is the evidence for it.

## What happened

`tests/test_caddy_wiring.py` pins the 2026-08-14 "LIVE shared config is DAMAGED" incident. The
wiring it extracts and runs later grew the `docker ps` / `docker inspect` lines that ASK the
container where its Caddyfile is. The extracted segment therefore re-assigned `$CF` over the
fixture's temp file, and with no docker on the box it died `rc 127` under `set -e`.

Two tests were red. Nobody saw it, because the module skipped on Windows — the operator's machine —
and was never reached in CI. A test that runs nowhere has no baseline, so nothing can be compared
against it and no run ever goes from green to red.

## The repair, and the one that was tempting and wrong

The tempting fix was to TRIM the docker lines out of the extracted segment. That tests a shortened
copy of the wiring, not the wiring — class 20.

**Simulate docker instead.** A stub on PATH answers `ps` and `inspect` with the fixture's own path,
and the test asserts the stub WAS consulted, so a wiring that stopped asking the container would
fail rather than quietly pass.

The module gate is `shell_harness_allowed()` (ONE HOME), never `shutil.which("bash")`: on this
machine `bash` is WSL's `bash.exe`, and a stripped `env=` makes WSL fail in UTF-16.

## Mutations caught

- the bare-word range delete
- the assumed path
- `sed -i` restoring the inode swap (a single-file bind mount follows an inode — class 54)
