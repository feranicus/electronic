# Project conventions — feranicus/electronic (Cybergod LLC / S4Biz Group)

## READ THIS FIRST — where the rest of this file went (2026-09-09)

This file used to be **646 KB / 7,950 lines / 307 sections**. It is re-injected into the model's
context on EVERY turn, so it was spending ~160,000 tokens before the operator typed anything, and
that is what produced *"This conversation is too long to continue."*

Nothing was deleted. The full narrative history — every incident, every root cause, every measured
number, verbatim — is at:

    docs/decisions/HISTORY-2026-07-to-2026-09-10.md

**This file now carries only what must be true on EVERY turn**: the operating principles, the
settled facts, and the defect classes as one-line rules. The history is the EVIDENCE for those
rules and is read on demand, not on every turn.

**HOW TO USE THE HISTORY.** When a rule below matters and you need the story — what broke, what was
measured, which fixture proved it — `grep` the history file for the phrase in the rule. Every rule
here was earned by an incident recorded there; searching for the key words in the rule finds it.

**HOW TO ADD TO IT.** A new incident goes in `docs/decisions/<YYYY-MM>.md`, in the same voice and
detail as the history file. It gets **at most one line here**, and only if it is a rule that must
be obeyed on every turn. If a section here grows past a few lines, the story belongs in the month
file and the rule belongs here. `tests/test_claude_md_size.py` FAILS THE BUILD if this file passes
the size budget, because a rule that is only written down goes stale, and this one already did.

---

## Operating principles (standing instructions — always follow)

1. **Full automation, no manual steps.** Every operational task must be a script or a GitHub
   Actions workflow that runs end-to-end. Never leave the user hand-editing files on the droplet,
   clicking through consoles, or copy-pasting multi-step command sequences. If a task needs doing
   more than once, it gets a script.
2. **GitHub is the single source of truth.** All code, workflows, and infra definitions live in
   this repo. The droplet and cloud resources are provisioned *from* the repo (Actions → SSH /
   APIs), never configured out-of-band. To change how something runs, change it here and let CI
   apply it.
3. **Secrets never touch git.** Runtime secrets (API tokens, Spaces keys, bot tokens, the shared
   access password, service-account JSON) live ONLY as encrypted **GitHub Actions secrets** and/or
   in the droplet's own env files (`chmod 600`). `.gitignore` blocks `*.env`, `*_sa.json`, `data/`,
   `*.sqlite`, and `gitleaks` runs in CI. The only credential in GitHub-as-code is the deploy SSH
   key (a secret).
4. **Non-destructive on the droplet.** Never disturb Amnezia VPN / VideoDead / joplin. The
   colt-stack is an isolated compose project (`-p colt-stack`, `colt-*` names). No firewall
   changes. Patch automation only refreshes colt-stack images; other stacks get only shared
   OS/kernel patches.
5. **The LLM assists, it does not decide side effects.** The models write summaries, risk digests
   and prose. They never decide whether to run `apt`, push, deploy, reboot, block an address or
   promote a release — those are deterministic code paths.
6. **Deliver operations as scripts + document — NO command blobs.** Never hand the user long ad-hoc
   shell/heredoc command sequences to paste ("talmud commands"). Every operational step (build,
   run, deploy, diagnose, fix) must be a re-runnable **Python script** committed to the repo,
   invoked as `python <script> ...`, and any change (deps, Dockerfile, flags, config, architecture)
   must update the relevant **README.md** in the SAME change. KISS + full automation. (Applies to
   all projects.)
7. **ONE ORCHESTRATOR. ONE COMMAND. ALWAYS.** ← the rule I keep breaking; stop breaking it.
   The user must NEVER be told to run two scripts. Not "run the test then deploy", not "run X then
   Y to verify" — **one** command, every time, in every project. All other scripts are BUILDING
   BLOCKS that the orchestrator calls as subprocesses; they stay individually runnable only for
   debugging, and the user should never need to.
   - In this repo the orchestrator is **`python ship.py`** = test -> commit -> push -> staging gate
     -> deploy -> verify -> safe-point -> release notes. Flags narrow it (`--test`, `--web`,
     `--bots`, `--direct`, `--dry-run`, `--no-stage`, `--no-preview`, `--rollback`, `-m "msg"`),
     they never split it. `ship_web.py`, `deploy.py`, `deploy_web_direct.py`, `stagegate.py`,
     `caddyguard.py`, `dbbackup.py`, `perseus.py --install-only`, `secaudit.py`, `model_watch.py`,
     `release_notes.py` and `pytest` are all invoked BY ship.py.
   - New capability (a test, a check, a migration, a provisioning step)? **Wire it into ship.py in
     the same change.** A new script the user has to remember to run separately is a bug.
   - If a reply is about to end with two `python ...` lines, that is the signal: go back and fold
     them into the orchestrator, then give the single command.

## STANDING RULE — always end with the exact command to run — and it is ONE command

After finishing ANY piece of work the user must trigger, end the reply with the exact command,
copy-paste ready, with the right working directory:

    cd "C:\Python SW\Linkedin Scraper"
    python ship.py

**Exactly ONE `python ...` line.** If the work added a new step, WIRE IT INTO ship.py in the same
change instead of telling the user about it. If there is genuinely nothing to run, say
"Nothing to run." explicitly.

## STANDING RULES the operator has given directly (do not re-litigate)

- **"If I ask you something just do it, do not stop and wait for bullshit."** AskUserQuestion is
  for a genuine fork that cannot be resolved from the code or that reverses one of his own
  documented rules. It is NOT for "shall I continue" or "want me to build the next part". Finish
  the work, then report what was built and what it measured.
- **Look at a UI change before shipping it.** `python preview.py` and actually LOOK. Enforced by
  `ui_preview_stamp.py`: ship.py stops with exit 2 when the frontend hash changed since the last
  preview. `--no-preview` overrides deliberately.
- **Every release, the four models write the release notes and they are SENT** (Gmail API to
  feranicus@s4biz.io + Telegram). Same four as the staging panel; asserted identical by test.
- **The staging panel's findings get ACTED ON.** When the panel is right, it becomes a check or a
  fix in the SAME change — never a note. It is advisory and it is wrong often enough to matter, so
  say plainly which half is wrong and why; a model verdict never overrides a deterministic check,
  in either direction.
- **Public-facing copy must not read as AI-written.** BANNED: the em dash, "it's not X it's Y",
  rule-of-three everywhere, uniform sentence length, a neat aphorism as the closing line,
  systematic emoji placement, signposting ("here's the thing"), delve/leverage/robust/seamless/
  landscape/testament/underscore/pivotal, and bullets of identical length and grammar. Every number
  in a post is traced to the measurement that produced it before the post is written.
- **No unsubstantiated comparative claims.** We have never benchmarked the panel against Claude,
  ChatGPT or Gemini, so the site argues ARCHITECTURE, not superiority (UWG §6 / UCP Directive, and
  it would poison the engine's own evidence discipline).

## THE ONE IRREDUCIBLE HUMAN INPUT

Cloud credentials can only be minted by the account owner. Provide them **once** (GitHub secrets /
`golive.secrets.env` / the DO console); after that everything is automated and re-runnable.
Console-only jobs that no script can do: creating scoped per-project DO model access keys, moving
nameservers, and making a GHCR package public.

---

# SETTLED FACTS — do not re-derive, do not re-ask

## The estate

| Fact | Value |
|---|---|
| Production droplet | **64.225.108.200**, FRA1, **4 GB / 2 AMD vCPU / 80 GB** |
| Its name lies | `ubuntu-s-1vcpu-1gb-fra1-01` is the size it was CREATED at. Read the spec, never the name. |
| Staging twin | **165.245.244.174**, FRA1, same size/image/region deliberately |
| Public sites on the shared proxy | cybergod.ai · jobhuntwow.com · jev.best · klimaanlage-preise.de (+ montieren) · s4biz.io · godeyes.ai |
| Shared reverse proxy | `videodead-caddy-1` owns :443 for EVERY site. Its death is a total outage and never an application fault. |
| cybergod.ai DNS | **GoDaddy** (ns07/ns08.domaincontrol.com). `python golive.py` automates it with a GoDaddy API key in `golive.secrets.env`. Do NOT run publish_landing.py for cybergod. |
| Engine images | The engine lives in BOTH `webapp/Dockerfile` (colt-web) and `assess-bot/Dockerfile` (colt-assessbot). Two delivery paths; update both. |
| Event volumes | colt_events (cybergod, jobhuntwow, jev) · polara_events (klima) · s4biz_events (s4biz). Compose PREFIXES volume names with the project; ASK docker, never assume. |
| Loki | ONE instance, `videodead-loki-1`. Every promtail pushes to it. It is the shared substrate and the only thing that holds the PAST. |
| SMTP | **BLOCKED outbound.** Mail goes through the Gmail API in `notify.py`. Never "fix" this to smtplib. |

## The one command per project

    cybergod.ai          cd "C:\Python SW\Linkedin Scraper"        python ship.py
    jobhuntwow.com       cd jobhuntwow-app                          python ship.py
    jev.best             cd "C:\React SW\yantar\jev-best"          python jev.py deploy   (+ jev.py api)
    klimaanlage-preise   cd "C:\Python SW\Klima\klima-shop"        python ship.py
    s4biz.io             cd "...\S4biz new website"                python ship.py
    the whole fleet      cd "C:\Python SW\Linkedin Scraper"        python perseus.py --rollout

`jhw.py deploy` is NOT a subcommand and never was. jev's middleware lives in the **jev-api** image,
so `jev.py deploy` alone does not ship it.

## Diagnostic verbs (READ-ONLY, one ssh session each, from the operator's PC)

    python recover.py            outage triage: ports, crash loops, caddy validate, outside probes
    python fleet.py              per-project: code present? wired in? beating? traffic? attacks?
    python cost_report.py        AI spend; --trace (who can spend) · --whodunit (who did) · --correlate
    python agent_forensics.py    is an actor a human, a script, or an agent
    python authz_audit.py        every route answers 401 anonymously; --local runs it in-process
    python incident_report.py    forensics package for an exposure
    python secaudit.py           kernel/reboot/patch posture, and staging-vs-production twin drift
    python decommission.py       retire a vhost from the shared proxy (dry run by default)

## IAM, quotas, administration

`colt_auth.email_allowed()` is the ONE gate for the bots AND the web app. Four sources:
Colt AE `name.familyname@colt.net` · `PARTNER_EMAILS` (`ud@objectale.ch`) · `PARTNER_DOMAINS`
(`s4biz.io`) · **an ENABLED account in `user_store`** (an administrator creating a named account IS
an authorisation act; it fails CLOSED and can only ever ADD). Extend without code via
`EXTRA_ALLOWED_EMAILS` / `EXTRA_ALLOWED_DOMAINS` in the droplet `.env`.

- `ADMIN_EMAILS = {"feranicus@s4biz.io"}`, committed beside PARTNER_EMAILS and USER_QUOTAS, because
  "who may use this / how much / who decides" is one question and answering it in two files is how
  they drift. Addresses are not secrets; committing them makes them auditable.
- `USER_QUOTAS`: `mr.nvisinc@gmail.com` and `mordechai.rabinovich@rbc.com` capped at 5 each.
  **rbc.com is deliberately NOT in PARTNER_DOMAINS** (that would admit ~90,000 bank staff).
  Both front doors enforce; counting includes failed and running jobs; the lookup fails OPEN.
- Passwords: scrypt in `user_store` on the shared volume. An ASSIGNED password WINS; the shared
  `COLT_BOT_PASSWORD` is a fallback only for identities without one. A DISABLED account still
  counts as existing (or disabling would hand the person the shared password). A broken store
  REFUSES. The password is shown once and never emailed — the OTP already uses that mailbox.
- Authorisation is server-side: every `/api/admin/*` route depends on `_require_admin`, every
  functional route on `_require_ready`. Hiding a nav item is presentation, not a control.

## Secrets

`python set_secret.py NAME` — value on **stdin**, never argv. It upserts BOTH the local
`assess-bot/.env` (the source of truth: `deploy.py --reuse` packs it over the droplet's copy) and
the droplet's `/opt/colt-stack/assess-bot/.env`. `bash -s` reads its SCRIPT from stdin, so the
remote script travels in argv and the value on stdin — the two are mutually exclusive.

## The model chain and its budget

`enrich._FALLBACKS` = **deepseek-3.2 -> llama-4-maverick -> gemma-4-31B-it -> kimi-k2.6**, four
vendors so no shared failure domain. It is the ONE home: compose must not restate it (ship.py fails
the deploy if `- ENRICH_MODELS=` reappears) and ship.py deletes `ENRICH_MODEL`/`ENRICH_MODELS` from
the droplet .env. `GET /api/diag` + `engine_config.py` report the EFFECTIVE config with provenance.

- Entitlement is not visibility: every `anthropic-*` and commercial `openai-gpt-*` returns **403**
  on this account. `model_watch.entitled()` skips probing them and says why.
- Reasoning/thinking models break the strict-JSON contract. Instruct models only.
- Per-model required parameters live in `MODEL_PARAMS` (kimi: the temperature the server names,
  and `response_format` in `_drop`). A 4xx body is the server telling you what it wants — repair
  WHAT IT NAMED, never strip fields until something works.
- This gateway makes `max_tokens` and `response_format:json_object` MUTUALLY EXCLUSIVE. Keep the
  JSON contract, drop the ceiling; a truncated answer is a dirty failure, a timeout is a clean one.
- Budgets: `ENRICH_TIMEOUT=175`, `ENRICH_BUDGET_S=380`, head-weighted 55%, subprocess kill at 430s.
  Never issue a request whose completion time exceeds its own timeout.
- Cost: `llm_meter.py` at `enrich._call` — the ONE chokepoint, per-direction pricing, unknown model
  priced at the dearest rate we know, `allow()` checked BEFORE the request, fails OPEN on a storage
  fault and CLOSED on the budget. `spend_watch.py` compares a MEDIAN baseline against the DO
  balance delta hourly and names models that are NEW today.

## Shodan plan

`basic` (Freelancer): `vuln:` needs Small Business+, `tag:` needs Corporate. `shodan_plan()` calls
api-info once and SKIPS those queries rather than printing scary warnings.

---

# THE ENGINE'S NON-NEGOTIABLES (zero false positives)

The whole product rests on these. Each was paid for by a customer-facing incident; grep the history
for the domain named in brackets.

- **Absence of evidence is never a finding.** A FAILED lookup reports `UNKNOWN / data-unavailable`
  and claims no gap. [Cogent AS174 graded CRITICAL from a dead DNS resolver]
- **A pivot must PROVE ownership, not just match.** Never let a selector that can match the whole
  internet (a public CA, a shared hoster ASN, a generic favicon, a common word) become an ownership
  anchor. `api.count()` > 2000 = shared by definition. [bibeltv.de, 1003 false IPs]
- **A brand token is an anchor only if it is RARE.** Test rarity against the index, never against
  intuition — the engineer who picks the token speaks the language and cannot hear that it is a
  dictionary word. [abakus = abacus]
- **The HOSTER's identity is never the TARGET's.** whois-org, netblock holder, hoster cert-O and
  PTR domain are evidence about the PROVIDER. Same for the COUNTRY. [rightmart.de, aminagroup.com]
- **`_apex()` is the REGISTRABLE domain (eTLD+1), via `psl.registrable()`.** "The last two labels"
  turns budget.gov.ru into gov.ru and makes a government one customer. When unsure take MORE
  labels: a narrow estate is a recall bug, a wide one puts strangers in a customer's deck.
- **Pinning proves the ADDRESS, not the OBSERVATION.** On provider/multi-tenant infrastructure a
  record becomes a finding only if it names the customer. Fails OPEN only where that was EARNED —
  the customer owns address space AND no stranger's name is already on that address.
- **A discovered domain may ENLARGE the estate; it may never BE the estate.** Per-pivot
  (`PIVOT_MAX_ADD`) and per-domain (`DOMAIN_MAX_ADD`) budgets with whole-unit rollback. A guard
  whose baseline is computed AFTER the untrusted input is merged is not a guard.
- **An audit is a SIGNAL, not an authority.** The FP auditor may flag; deterministic ownership data
  decides. The auditor is never the author and never the author's vendor.
- **An EMPTY estate is an honest, saleable outcome.** "Nothing of yours is externally observable"
  is true and defensible for a shared-hosting customer; a deck full of other people's servers is
  not. Emptiness is not a refusal trigger.
- **A refusal is a FORK, not a failure.** `ScopeRefused` -> exit 4 -> an amber panel with the
  reason, the next step and an explicit operator override. A guard an informed operator cannot
  override is a bug, and one that presents its decision as a malfunction is a different bug.
- **No invented identifiers.** A CVE is cited only if it appears in the raw findings; `_audit_cves`
  strips the rest and emits `hallucination_guard`.
- **A prompt is a string that reaches a human, via the model.** The bible, the system prompts and
  every default are customer-facing surfaces. Guardrail 5 forbids inferring sector, country or
  regulator from infrastructure holder names.
- **Never translate ENUM/LOOKUP keys** (`sev`, `band`, tier, the `COLT` remediation tag). Rename
  the LABEL at render time; translating a key makes rows silently vanish.
- **Headline numbers are computed AFTER the last thing that can change them.** A count taken
  mid-pipeline describes a state the deck never had.
- **Not one packet is sent to the company being assessed.** It is on /partners, in the ToU, in the
  Art. 13 notice and in the signed partner pack, and it is why no customer authorisation is needed.
  `active_probe.enabled()` requires `ACTIVE_PROBE=1` **AND** `ACTIVE_PROBE_AUTH=<written
  authorisation reference>` — a flag says somebody wanted it, a reference says somebody is
  accountable.

---

# DEFENCE AND LAW

- **Detection and reporting scale; retaliation is illegal and pointless.** NEVER scan back, connect
  back, or build tooling for it: StGB §202a/§202b/§303a/§303b and **§202c (possession/creation)**,
  EU Directive 2013/40, US CFAA §1030, Canada CC s.342.1. The lawful path to a human is a complaint
  to the provider, drafted by us and FILED by a person.
- **The shield never touches iptables/nft/ufw.** Amnezia VPN shares the host; enforcement is
  HTTP-layer inside our own container. Asserted by test.
- **An authenticated session is never blocked or tarpitted**, and a route we SERVE is slowed, never
  blocked. Refusing a real page locks a real person out. The evidence is unchanged either way, and
  the exemption is ANNOUNCED.
- **A user agent is attacker-controlled; the PATH is the evidence.** So is the referrer, and so is
  the source: a visit from hosting/VPN infrastructure is not "a person".
- **VARIETY, NOT VOLUME.** A person misses the same few stale paths; a scanner misses hundreds of
  different ones. Two real visitors with 439 and 362 404s are the reason.
- **An exemption from ENFORCEMENT must never become an exemption from OBSERVATION.** `/api/` is
  never blocked (every deploy verifier asserts 401 on /api/me) and it became a hiding place.
- **Models propose, code decides.** `perseus/vet.py` (five fail-closed barriers) plus
  `ruleset.can_promote()` (24h in detection, 3-of-4 quorum across vendors, at least one hostile
  match, ZERO clean hits) and `thresholds()` clamped ON READ. `review()` auto-demotes a rule that
  refused legitimate-looking traffic: full autonomy without a way back is a one-way door.
- **A route that forwards a caller-chosen model id to a paid API is a payment endpoint.** It needs
  authentication AND an allowlist, and the list has ONE home.
- **Deny by default, and PROVE it.** In a framework where a route is public unless somebody
  remembers, an open endpoint is a matter of time. `authz_audit.py --local` is wired into ship.py.
- **Alerts must be received, and benign-every-time is the enemy.** An alert nobody gets is not an
  alert; a warning that fires on every run trains the operator to read past the one that matters.
  Edge-trigger state changes; never re-page a steady state.

---

# THE RECURRING DEFECT CLASSES — the checklist that actually prevents repeats

Every one of these has cost at least one deploy cycle, most of them several. Read this list before
writing a check, a fixture or a diagnostic.

## About checks

1. **A check that cannot see its subject is not a check.** It must not report its own blindness as
   a finding about the system. (logship shipped an empty archive for a week and exited 0; whodunit
   read a dead Loki query as innocence; the coverage metric graded its own homework.)
2. **A check that cannot RUN is not a check.** "skipping", "catalog unavailable", "not installed"
   printed on every run means it has never once executed.
3. **A check that cannot FAIL is not a check.** If the denominator is produced by the thing being
   measured, it is not a measurement. Prove a gate by breaking the thing it guards.
4. **Assert the PROPERTY, never a string the error text also contains, and never a position.**
   Anchor on the CALL SITE, resolve cross-module calls by AST, strip comments AND docstrings before
   grepping — a check has matched its own explanatory comment five separate times here.
5. **Print the comparison you made, never a raw dump plus a separately computed verdict.**
6. **A verdict is the FIRST line at column zero; notes are indented and come after.** A wildcard
   branch must FAIL, never score an unrecognised answer as a pass.
7. **A detail that renders identically whether or not anything was measured is templated output.**
   And a PASS detail must not carry failure vocabulary — another check parses it.
8. **A name is read far more often than a detail.** A check whose name overclaims teaches the
   outage (`config_reread` -> `config_write_ordering`; `config_change_propagates` ->
   `guard_write_path_reloads`).
9. **Behaviour AND wiring.** shield.py was fully tested while nothing asserted the middleware
   called it. A control that is correct and unreachable is not a control.
10. **A gate must render its own PASS on the operator's console** (cp1252) and must distinguish a
    CRASH from a FINDING.
11. **The last exit must follow the last check.** 73 checks once ran after the only `sys.exit(1)`.

## About tests and fixtures

12. **A fixture that does not reproduce the condition under test is a test of the fixture.** Prove
    the fixture first (assert the breaker actually broke).
13. **A negative test that passes because of ANOTHER guard measures that other guard.** Defeat
    every guard on the path. And a mutation that does not violate the property proves nothing.
14. **Run the BASELINE first.** A suite that is already red scores every mutation as "caught".
15. **A test that depends on a race, or on a four-digit needle in a haystack containing a clock, is
    a coin flip that teaches the operator to re-run rather than read.**
16. **A `finally` cannot survive SIGKILL, and `open(path,"w")` truncates before it validates its
    own arguments.** Any harness that edits real files writes to a temp file and `os.replace`s it,
    self-heals on import, and is followed by a scan for EVERY marker it could have left.
17. **A test that encodes a doctrine must be REWRITTEN when the doctrine is corrected**, with the
    old reasoning kept beside it — deleting it loses why.
18. **Tests must not reach the internet**, and the stub must be re-applied after every
    `importlib.reload`.

## About platform (eight wasted ships, one root cause)

19. **Ask "which machine, which interpreter, which toolchain?" before telling the operator to run
    anything.** Green in a Linux sandbox is not evidence about his Windows box. Prefer a gate
    inside the container/CI that installs its own dependencies.
20. **SIMULATE the platform, do not skip it.** `monkeypatch.setattr(os, "replace", windows_like)`
    proves Windows behaviour on Linux. A `sys.platform` skip hides the defect from the one machine
    that needs it.
21. **Line endings are the platform's business.** Any fixture that will be hashed, diffed or parsed
    is written in BINARY. `git archive` applies autocrlf unless you pass
    `-c core.autocrlf=false -c core.eol=lf`. Payloads to `bash` go over stdin as BYTES.
22. **POSIX-only APIs** (`os.uname`, `/proc`, `fcntl`, a Windows path passed to `bash -n`) fail on
    the machine that runs the tests. Guarded by an AST test.
23. **Console encoding**: ship.py sets `PYTHONIOENCODING`, reconfigures its own streams, and every
    `subprocess.run` passes `encoding="utf-8", errors="replace"`.
24. **A declared dependency the operator's Python lacks is an operator step.**
    `ensure_app_requirements()` installs MISSING packages only, never upgrades.

## About diagnosis

25. **A traceback's cause is its LAST line.** `tail -N` of a build log shows stack frames; grep for
    the error vocabulary FIRST, then show context.
26. **A diagnostic that does not NAME its subject sends the next investigation down the wrong
    road.** Print the path, the model, the address, the arithmetic.
27. **When a number surprises you, read the vendor's own breakdown before auditing your own code.**
28. **Source that NAMES a thing proves it COULD happen; it does not prove a process DID.** When
    half the evidence-gathering fails, say so instead of concluding from the half that worked.
29. **Before naming a cause, ask what would have to be TRUE for it to be the cause** — not what
    merely fits. Measure, then fix. I have twice started building on an unverified cause.
30. **A snapshot cannot answer a question about the past.** Loki holds the past; open sockets and
    container start times do not.
31. **Both terms of a ratio must be measured over the same period**, or the number describes when
    we started looking.

## About code and configuration

32. **ONE HOME.** A value with several homes drifts and the newer one always loses (ENRICH_MODELS
    had four; the document language had six; the shield's class table had two). If a value has a
    documented home in code, compose must not restate it, and prose must never restate what a
    selector already lists.
33. **A fix recorded in one project's CLAUDE.md is not applied to the sibling until somebody
    applies it.** For a platform- or estate-shaped defect, grep BOTH repos for the same shape.
34. **Follow the VALUE end-to-end — UI -> API -> persistence -> engine — and assert it at each
    hop.** A capability the engine has and the API discards is invisible to every engine test.
35. **When a change needs N edits, DERIVE N from something authoritative.** Counting by hand is how
    the fourth wiring point is missed (`_APP_ROUTES`, `.dockerignore`, `INCLUDE`, the sitemap).
36. **READ the signature.** Seventeen times in this workstream I have called a helper that returns
    a different shape than I assumed (`run()` -> int, `ssh_script()` -> 3-tuple, `getJSON` vs
    `postJSON`, `useT()` -> a 3-tuple, `classify()` -> a list). Writing a guard around a guess is
    worse than reading six lines, because it looks like care.
37. **A feature guarded by `if <derived thing>:` fails silently by construction.** Log the skip or
    assert the wiring.
38. **`except: pass` on an observability write is a self-inflicted blind spot.** Print once.
    A swallowed exception returning a plausible default is indistinguishable from a measurement.
39. **A silent write to the wrong place is worse than a permission error.** `os.makedirs` succeeds
    into a container's ephemeral overlay. ASK the container where its log/mount/volume actually is;
    never assume a path or a compose prefix.
40. **In-process locks do not serialise two processes.** Anything a `docker exec` can touch is
    written atomically (temp + `os.replace`, with the extension preserved — pptxgenjs, ffmpeg and
    pandoc rewrite a path whose extension they do not recognise).
41. **Never retry a non-idempotent remote command.** A timeout is an UNKNOWN outcome, not a
    failure. Reads and probes may retry; anything that creates, extracts, deletes or deploys
    reports the unknown state instead.
42. **Every remote call needs a HARD `timeout=`** sized to what that call legitimately takes, and
    **never judge success through a pipe** (`cmd > log 2>&1; rc=$?; tail log; exit $rc`).
43. **SSH SESSION COUNT is the only lever on Windows** (no ControlMaster; OpenSSH 9.8 enables
    PerSourcePenalties by default). Never add an `ssh()` to a step that already opens one — add a
    section to its batch. Payload in argv, data on stdin.
44. **A literal `%` must be `%%` — but only in a %-FORMATTED string.** The rule has a precondition.
45. **A layout row is ARITHMETIC.** Add up brand + every control + gaps in the LONGEST language
    before shipping; German and Polish overflow first. `tools/header_layout.mjs` measures it.
46. **In a grid or flex parent a new child is a LAYOUT PARTICIPANT, not an overlay**, and a
    `z-index` means nothing until you know which stacking context it is in. A popover inside a
    sticky ancestor must be portalled.
47. **A selector legitimately has SEVERAL rules.** The question is "does ANY rule set this
    property", never "does the first one".
48. **PARSE is not RUN.** An undefined identifier and an invalid colour are legal JavaScript until
    they execute. Render the page, execute the loop, read the artifact.
49. **READ THE DELIVERED ARTIFACT.** Rich finding text is not a good deck. Two slides of one deck
    disagreed; a raw enum reached a customer slide; 46 text boxes were truncated; a partner's deck
    kept our teal. Every one was invisible in the logs and obvious in the file.
50. **An OPTIONAL lookup may make a page more accurate, never less — and never slower than that
    page's own budget.** It parses inside its own `try`, it cannot raise past its caller, and it
    never runs on a request path: a background refresh fills a cache, the request reads it. A status
    page that hangs is its own outage, and a 500 from a nice-to-have is worse than the gap it filled.
51. **A route that COMPUTES is not verified by a route that answers 401.** Liveness is not the
    feature. If a deploy does not exercise the page, the page ships broken behind a green suite —
    and it did, three times. Run it where it runs, with the real env, and let `set -e` fail the ship.
52. **A handler must be able to describe its own failure.** A 500 with an empty body costs rounds
    of guessing: catch, print the traceback, and RENDER the cause with no invented rows.
53. **THE OBSERVER MUST BE OBSERVED, and a feature nobody has seen working is OFF.** The fleet page
    was the one request on the box with no telemetry of its own, so when it broke there was nothing
    to read and I guessed for three ships. Every call now emits `evt=fleet_status` through the same
    writer as access logging (and must not count its own lines as traffic), and the watch loop pages
    on the transition. A lookup that has never been observed succeeding defaults off, behind an env
    var, not behind a redeploy.
54. **One response is built from ONE snapshot.** Reading the same cache twice inside one handler
    lets a refresh land in between and the two halves then describe different moments — `live`
    beside zero traffic. Read once, pass it down.

---

# WHAT LIVES WHERE (the map, so nothing has to be rediscovered)

## cybergod.ai (this repo)

- `hermes-skills/shodan-assessment/scripts/` — the ENGINE. `run_assessment.py` (orchestrator),
  `shodan_recon.py` (discovery + ownership gates + `classify()`), `enrich.py` + `enrich_parallel.py`
  (LLM prose, the ONE chokepoint for spend), `audit_fp.py`, `clarify.py`, `psl.py`, `scope_deny.py`,
  `group_discovery.py`, `asn_sources.py`, `email_auth.py`, `cert_intel.py`, `naming.py`,
  `active_probe.py`, `compliance_*.py`, `build_*_deck.js`, `build_*_html.js`, `deck_i18n.js`,
  `i18n/`, `deck_langs.py`, `proteus.py` (White Label), `run_log.py`, `demo_build.py`,
  `cost_ledger.py`, `engine_config.py`, `model_probe.py`.
- `webapp/backend/app/` — FastAPI. `main.py`, `auth.py`, `store.py`, `telemetry.py`, `visitors.py`,
  `alerts.py`, `notify.py`, `shield.py` + `shield_panel.py` + `shield_console.py`, `slow_store.py`,
  `siege.py`, `fleet.py`, `brand.py`, `llm_meter.py`, `llm_events.py`, `spend_watch.py`,
  `attack_digest.py`, `threat_intel.py`, `abuse_report.py`, `ip_reputation.py`,
  `security_headers.py`, `daily_report.py`, `release_notes.py`, `geoip.py`, `perseus_client.py`.
- `webapp/frontend/src/` — React. `i18n.jsx` + `locales/` + `legal.jsx` + `legal-locales/` +
  `partners-locales/` (six UI languages, 100% enforced), `components/`, `pages/`, `styles.css`.
  Gates in `tools/`: i18n_catalogue, i18n_audit, header_layout, contrast_gate, canvas_smoke,
  api_contract, shipped_shell, partners_gate, render_gate.
- `perseus/` — the hub (`hub.py`, `ruleset.py`, `vet.py`, `abuse.py`, `client.py`).
- `deploy/` — `caddy/*.caddy` (committed blocks), `caddyguard/agent.py`, `dbbackup/agent.py`,
  `logship/agent.py`, `hostpath.py` (the ONE volume/mount resolver).
- Root verbs: `ship.py` (the orchestrator) and the diagnostics listed above.

## The proxy, and the outage that shaped everything

The shared Caddyfile is **GENERATED, not edited**: `/opt/caddyguard/blocks/<project>.caddy`
fragments, assembled, validated in the container's own image AND env, written IN PLACE (a
single-file bind mount pins the inode), reloaded through the admin API, then compared.

**CONFIG HAS THREE HOPS and a check must say which one it measured:** host file -> container file
(the MOUNT) -> running config (the RELOAD) -> what is SERVED. `caddy validate` proves none of them.
Consistency across the hops is not AUTHENTICITY — the fragment is also compared to the committed
block. Caddy reads its config only at start, so a file damaged at 16:15 can serve happily from
memory until a 04:22 kernel reboot takes six domains down together. That is why the watchdog runs
every 10 minutes, why patchwatch refuses to reboot into an invalid config, and why the uptime
workflow runs OFF-BOX.

---

# LANGUAGES

- **Interface: six** (en, de, it, fr, es, pl), 100% enforced by the catalogue + audit gates.
- **Documents: three** (en, de, ru). A document language needs `scripts/i18n/<code>.json` AND a
  `LANG_*` block in `enrich.py`; `deck_langs.doc_langs()` derives the list and fails closed —
  half a language is not a language. Served at `GET /api/langs`; `/api/jurisdictions` likewise.
- Interface language != document language. Prose must never restate what the selector lists.
- A COMPOSED string is not a dictionary key: translate the PARTS (the regex proposes, the
  dictionary decides) and let the pack declare its own plural grammar.

---

# COMPLIANCE

`compliance_enrich.JURISDICTIONS` is ONE registry (reference document, ordered regimes, which get
their own deck, prompt framing, eyebrow). `compliance.json` carries `order`/`decks`/`eyebrow`, so
**no deck builder holds a regime constant**. Fails CLOSED to the EU set. EU = NIS2 / CRA / EU AI
Act; CA = OSFI B-13 · E-21 · B-10 · Integrity & Security · Incident Reporting · PIPEDA · Law 25 ·
CCSPA. The reference's §6.4 "must never appear" list is a BUILD GATE. Not legal advice, and the
framework set on the findings deck is chosen from `d.target.country` — UNKNOWN is NOT the EU.

---

# HONEST LIMITS (state these, do not paper over them)

- Shodan cannot see a vhost behind an SNI-only front end. "Shared hosting, not externally
  observable" is the honest line.
- No public API is authoritative across all five RIRs; `clarify.py` always asks on a target with
  its own address space.
- DKIM is presence-only: a selector cannot be enumerated, so "not found" is NOT DETERMINABLE.
- view-source cannot be disabled by anyone. The boundary is the SERVER; what was worth fixing was
  source maps, secrets in the bundle and shipped HTML comments, and all three are now gated.
- The five projects share ONE DigitalOcean model access key, so DO's own per-key usage cannot
  attribute the invoice. Scoped, VPC-restricted per-project keys are a console job.
