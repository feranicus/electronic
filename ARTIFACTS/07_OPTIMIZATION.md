# Optimizing the conversation / moving to a new project

## The one thing that matters

`CLAUDE.md` is **646 KB / 7,950 lines / 307 `##` sections**, and it is loaded into context on
**every turn**. Starting a new project does not help unless you also shrink this file, because a new
project that imports the same `CLAUDE.md` fills up at the same rate.

Everything below is ordered by impact.

## Step 1 — split CLAUDE.md into a lean core + a dated archive (biggest win)

`CLAUDE.md` today is two different things glued together:

1. **Standing rules** you always want in context — operating principles 1–7, the security/legal
   constraints (no scan-back, secrets never in git, SMTP blocked → Gmail API only, one-command
   rule, no em dashes in public copy, etc.), the "how things run" and "who can log in" facts.
2. **A defect diary** — ~290 dated post-mortems ("X broke, here is why, here is the fix, guarded by
   test Y"). Each is valuable as a record, but almost none of it needs to be in context on a normal
   turn. This is ~90% of the bytes.

**Proposed structure:**

```
CLAUDE.md                       # LEAN: operating principles + standing constraints + how-things-run
                                #       + a one-line pointer to the archive. Target < 40 KB.
docs/decisions/2026-07.md       # the dated post-mortems, by month
docs/decisions/2026-08.md
docs/decisions/2026-09.md
docs/decisions/INDEX.md         # one line per decision: date · title · files touched · guard test
```

The lean `CLAUDE.md` keeps a section like:

> ## Decision archive
> Full post-mortems live in `docs/decisions/`. Before changing a subsystem, grep that folder for it
> (e.g. `caddy`, `enrich`, `shield`, `scope`) — the history explains why the current shape exists.

This keeps every rule that changes behaviour in context, moves the history to where it is grep-able
on demand, and cuts the per-turn cost by roughly an order of magnitude. **Nothing is deleted.**

I can do this split for you mechanically (it is a scripted transform: keep the "principle/rule/
hard-rule" sections, move the dated-incident sections to monthly files, generate the index). Say the
word and it becomes one `python` run.

## Step 2 — start a fresh conversation, not necessarily a fresh project

Two separate things get conflated:

- **Conversation/session size** (what you are hitting): fixed by Step 1 + starting a new chat. A new
  chat with a lean `CLAUDE.md` starts nearly empty.
- **"Move to a new project"**: only worth it if you want a clean artifact gallery / separate
  workspace. The *code* does not need to move — it already lives on disk at
  `C:\Python SW\Linkedin Scraper` and in git. A new Cowork project pointed at the same folder sees
  the same files. So: **new conversation, same folder, slimmed CLAUDE.md** is the cheapest path and
  loses nothing.

## Step 3 — these ARTIFACTS/ docs are the handoff

When you open the new conversation, this folder is the orientation: `00_INDEX.md` says what exists,
the area docs say where each thing is and why. You do not need the old chat history at all — the
durable knowledge is (a) the code, (b) the lean CLAUDE.md rules, (c) `docs/decisions/` history, and
(d) these inventory docs.

## Step 4 — housekeeping that also trims context

- `incident-20260906-*.md` at the repo root are forensic dumps (IPs, emails) — already meant to be
  gitignored per CLAUDE.md. Move them out of the repo root.
- `linkedin_verifier_old{,2,3,4}.py` are superseded copies — archive or delete; they are dead weight
  in any "read the repo" pass.
- The many top-level `linkedin_*_post.md` marketing drafts can move under `marketing/`.

## What I recommend, in order

1. Let me **split `CLAUDE.md`** (Step 1) — the single highest-leverage change.
2. **Start a new conversation** on the same folder; hand it `ARTIFACTS/00_INDEX.md` as the opener.
3. Optionally tidy the root (Step 4) so future "read the project" passes are cheaper.

Say "split CLAUDE.md" and I will write the transform script and run it.
