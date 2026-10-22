# Retiring jev.best from a proxy it shares with five other sites — 2026-10-22

## The request

Take jev.best down completely. It carries personal information that should not be reachable from
the open internet.

## What was in the way

`decommission.py` existed and was the right tool, with one gap and one hazard.

**The gap.** Its collateral check refuses to delete a Caddy fragment that also serves a domain
nobody asked to remove. That check is correct and it is the reason this script exists — removing a
site is the exact operation that caused the 2026-08-07 outage, when a truncated block in the
shared Caddyfile took cybergod.ai, godeyes.ai, jobhuntwow.com and klimaanlage-preise.de down
together for six hours after the next kernel reboot.

But on this droplet most vhosts live together in `_base.caddy` — measured on 2026-10-16: 2 of 5
fragments have a committed source and 138 lines of the proxy exist only on the droplet. So for a
site inside the shared base, "retire jev.best" could only ever answer *no*. The operation was not
unsafe, it was unsupported, and the refusal did not say which.

**The hazard.** `--sites` defaulted to `DEFAULT_SITES`, which named jev.best **and** both
klimaanlage domains. `python decommission.py --apply`, with no arguments, would have retired a
live project nobody had mentioned. Dry-run-by-default protected the action; nothing protected the
target.

## What changed

**A shared fragment is now edited, not deleted.** `split_fragment()` lifts the target site blocks
out by counting braces — never a line-based regex, because a nested `handle { }` is ordinary Caddy
and a line rule cuts the file in half, which is the 2026-08-07 shape. The rest of the file is kept
byte-for-byte. The ORIGINAL is archived under the decommission stamp, so `--undo` restores it
unchanged and needed no new code: it copies every archived `.caddy` back, which restores an edited
fragment exactly as it restores a removed one.

It still refuses, and says why, when:

- one header lists a target name together with one we are keeping (`jev.best, godeyes.ai {`) —
  that is a routing decision, not an edit;
- a block never closes, meaning our brace counting disagrees with Caddy's parser;
- the fragment's text could not be read, because a check that cannot see its subject must not
  answer (class 1).

The write is a temp file plus `mv` inside `blocks/`, refuses an empty replacement, and nothing
touches `/opt/videodead/Caddyfile` — that file is written only by `agent.py assemble --apply`,
which validates in the proxy's own image and environment before it reloads.

**No default target.** `--sites` is required and takes names or a group key (`jev`, `klima`).
`expand_sites()` completes every apex/www pair, which is the property the old default list was
really carrying: leaving `www.` served is not a smaller decommission, it is a half-finished one
that still answers.

**The containers to stop are read from the routing.** The old rule was
`any(k in name for k in ("polara", "klima", "jev"))` — three hardcoded homes that would stop a
container called `jev-archive` and miss one whose name says nothing about its domain. The site
block being removed already names its upstream; that is the authority. When nothing derives, the
plan falls back to a name match and says so on the same line, rather than presenting a guess as a
measurement (class 37).

**The survivors are derived.** `verify()` used to probe four hardcoded URLs. Editing the shared
base can break any vhost in it, so every name the proxy currently serves that is not being removed
is probed afterwards. The original four stay as a floor, because a check that can become empty is
a check that cannot fail, and because those are the sites the 2026-08-07 outage actually took down.

## Proof

Baseline first, then seven mutations, all caught:

| Mutation | Caught by |
|---|---|
| block removal ignores nesting (line-based) | the brace tests and the end-to-end write |
| a mixed header is silently split | the refusal test |
| the original is archived AFTER the write | the ordering tests |
| `--sites` gets a default again | the no-default test |
| containers matched by name substring again | the routing-derived test |
| survivors back to the hardcoded four | the derivation test |
| the empty-replacement guard removed | the write guard and the end-to-end run |

The end-to-end test is the one that matters: the write is base64 inside a shell string inside a
Python `%`-format, so it can pass every source assertion and still land the wrong bytes. It runs
the generated segment against a real file in a temp tree and compares the result to what the plan
computed, with the fixture proved first (class 12, class 48).

One defect of my own, caught by the existing guard rather than by me: I wrote the payload with
`printf %s`, and the suite scans every generated script for a bare `%s` because an unformatted
placeholder that never got substituted looks exactly like that. The payload is base64, so `echo`
carries it with nothing for the shell to interpret.

## What this does NOT do

Stated plainly, because the request was about personal information and three of these are outside
what any script here can reach:

- **Nothing is deleted.** Volumes, databases and images are kept, by design: `--undo` only means
  something while the data is still there. Public access is what ends. Deleting the data is a
  separate, irreversible decision.
- **DNS still points at the droplet.** With no site block matching that name, the TLS handshake
  fails outright — the same way jobhw.org failed for six days — so nothing is served. Moving or
  removing the records is a registrar job.
- **The hostname is permanently public.** Every certificate ever issued for jev.best is in the
  Certificate Transparency logs and cannot be withdrawn.
- **Copies elsewhere are not ours to remove.** Search engine caches and web archives hold whatever
  they fetched while the site was up.
- **`jev.py deploy` would put the vhost back.** That project writes its own fragment. Retiring it
  here and deploying it there again are not the same decision.

---

## The script had never once run — 2026-10-22, later the same day

The ship was green, the deploy verified, and then:

```
  DECOMMISSION — jev
  droplet: 64.225.108.200
  File "decommission.py", line 490, in main
    d = sections(ssh_script(plan_script(sites or ["__none__"]), timeout=240))
  File "recover.py", line 145, in sections
    for line in (out or "").splitlines():
AttributeError: 'tuple' object has no attribute 'splitlines'
```

`recover.ssh_script()` returns `(stdout, stderr, rc)`. All three call sites in decommission.py
passed the tuple straight into `sections()`, so the script could never have completed — the plan
is read-only, so nothing on the droplet was touched, but nothing was retired either.

Defect class 36 names this helper explicitly: *"Seventeen times in this workstream I have called a
helper that returns a different shape than I assumed (`run()` -> int, `ssh_script()` -> 3-tuple
…)"*. It is eighteen. The trap is real and worth recording: **ship.py defines its own
`ssh_script` that returns a string**, so the name alone does not tell you the shape — the module
does. Two helpers, one name, two contracts (class 32).

**The crash is the harmless half.** The return code was never read either. A refused ssh produces
empty output, `sections()` produces `{}`, and the plan would have announced *"none of the target
sites is served by a caddyguard fragment"* — a statement about the proxy, made by a probe that
never reached it. That is the `sshout()` failure of 2026-10-14 repeated verbatim, in a script
whose own docstring cites that incident.

**Why the suite was green.** Every test covered a piece — the generated scripts under `bash -n`,
the plan arithmetic, the splitter, the write — and not one executed `main()`. A script that cannot
run is not a script (class 2), and behaviour without wiring is not a control (class 9).

**The repair is the test, not the one-line unpack.** `run_remote()` is now the single place that
knows the shape, checks the return code, and refuses out loud; `main()` runs end to end in the
suite with the one boundary stubbed — ssh's actual 3-tuple — across the dry run, a refused ssh, an
empty read, a clean apply, a part-way apply, and a failed undo. Nine mutations, all caught; two
escaped on the first pass (apply and undo return codes) because the first version of the harness
answered every call with the same tuple, so the apply path was never exercised with a plan that
succeeded and a change that failed.

A part-way apply now says so and names the stamp: `set -e` stops the remote script at the first
failure, so a non-zero apply is a partial state, and letting `verify()` alone decide would pass
whenever the surviving sites happen to be up.

And the class is now guarded repo-wide, not just here: `tests/test_probe_fail_closed.py` derives
every module that imports `recover.ssh_script` and fails if any call site uses the result without
unpacking three values. Everything else in the repo already did.
