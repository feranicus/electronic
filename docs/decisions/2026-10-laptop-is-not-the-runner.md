# His green suite was testing a stack that does not ship (15 Oct 2026)

Moved out of CLAUDE.md on 11 Nov 2026 to stay inside the per-turn context budget. The four RULES
stay there in one line; this is the evidence for them, verbatim as it was written.

**HIS GREEN SUITE WAS TESTING A STACK THAT DOES NOT SHIP.** Four tests passed on his PC and failed
in CI, one root cause each, all the same shape — the laptop is not the runner.
**(a) A FLOOR IS NOT A PIN.** `starlette>=1.3.1` let image and laptop land on different releases;
which responses poll for a client disconnect changed between them, so the white-label harness —
which answered `http.request` FOREVER, wrong on every version — raised `Unexpected message
received` only in CI. ASGI says one body then `http.disconnect`; `_receive_for()` is the ONE HOME
and a contract test pins it, because a tolerant starlette passes the endpoint tests anyway. Pinned
`starlette==1.7.0`; a test forbids a floor on anything serving HTTP.
**(b) `ensure_app_requirements()` INSTALLS MISSING, NEVER UPGRADES** (still right), but its
docstring claimed drift "is answered by the image build" — it is not.
`report_requirement_drift()` is wired into ship.py, NAMES each mismatch, silent when they agree,
never blocks.
**(c) A TZ-MIXED DATE IS A PRODUCTION BUG.** `spend_watch.baseline()` parsed with local `mktime`
and formatted with UTC `gmtime`, dropping a real day east of Greenwich (MEASURED: UTC 0.20, Berlin
0.00). The droplet is UTC so the alert was never wrong there; his test asserted the buggy 0.00.
`calendar.timegm`, plus a four-timezone test.
**(d) `jobhuntwow-app/` IS GITIGNORED** — zero tracked files, so asserting its paths answered
"wiring is wrong" when the truth was "not in this checkout" (class 1). In-repo half always
asserted; sibling half skips with a reason. [2026-10-15]

