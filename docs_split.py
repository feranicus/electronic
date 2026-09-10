#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
docs_split.py - move the CLAUDE.md narrative history out of the per-turn context.

WHY THIS EXISTS
---------------
CLAUDE.md is re-injected into the model's context on EVERY turn. It had grown to 646 KB /
7,950 lines / 307 sections, which is ~160,000 tokens spent before the operator types anything -
and that is what produces "This conversation is too long to continue. Start a new session, or
remove some tools to free up space."

NOTHING IS DELETED. This script:

  1. copies the CURRENT CLAUDE.md, byte for byte, into docs/decisions/HISTORY-<stamp>.md
     under a short header that says what it is and how to search it;
  2. VERIFIES the copy ends with the original bytes exactly, and refuses to touch anything
     if it does not;
  3. MOVES docs/CLAUDE.core.md into place as the new CLAUDE.md.

Step 3 is a MOVE, not a copy, deliberately: two files holding the same doctrine is the "one value,
several homes" defect this repository has paid for more than any other, and the newer home always
loses. After a successful run docs/CLAUDE.core.md does not exist.

THE ORIGINAL IS IN GIT. If anything here is wrong, `git checkout HEAD -- CLAUDE.md` restores it;
the script prints that line on every run.

Re-runnable and idempotent: if CLAUDE.md is already under budget and a history file already
exists, it reports that and changes nothing.

    python docs_split.py              apply
    python docs_split.py --dry-run    measure and print the plan, write nothing
"""

import argparse
import datetime
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "CLAUDE.md")
CORE = os.path.join(HERE, "docs", "CLAUDE.core.md")
DEC = os.path.join(HERE, "docs", "decisions")

# The budget the lean file must live inside. Chosen from measurement, not taste: at ~4 chars per
# token a 60 KB CLAUDE.md costs roughly 15k tokens per turn, which is a cost worth paying for
# doctrine that must hold on every turn. The 646 KB version cost ~160k, which is not.
BUDGET = 60_000

HEADER = """\
# CLAUDE.md - full narrative history, 2026-07-09 to 2026-09-09

This is the COMPLETE text of CLAUDE.md as it stood on 2026-09-09, moved here verbatim by
`python docs_split.py` so that it stops being re-injected into the model's context on every turn.

**It is evidence, not instructions.** The RULES it earned live in `CLAUDE.md`, which is short and
is loaded every turn. This file is read on demand.

**HOW TO USE IT.** Every rule in CLAUDE.md was earned by an incident recorded below. When a rule
matters and you need the story - what broke, what was measured, which fixture proved it - grep this
file for the distinctive phrase in the rule, or for the customer domain named in brackets
(bibeltv.de, skon.de, rightmart.de, angermann.de, lotto24.de, abakus-tk.de, adpolice.gov.ae,
aminagroup.com, budget.gov.ru, ns03.ru, jobhuntwow).

**DO NOT APPEND HERE.** A new incident goes in `docs/decisions/<YYYY-MM>.md`.

---

"""


def say(msg):
    print(msg)


def kb(n):
    return "%.1f KB" % (n / 1024.0)


def tokens(n):
    """A deliberately rough estimate: ~4 bytes per token for English prose."""
    return int(n / 4.0)


def atomic_write(path, data):
    """Temp file + os.replace, per the standing rule. os.replace can transiently fail on Windows
    while another process holds a handle, so it is retried a few times before giving up."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = os.path.join(os.path.dirname(path), ".part-%d-%s" % (os.getpid(), os.path.basename(path)))
    with open(tmp, "wb") as fh:
        fh.write(data)
    last = None
    for _ in range(20):
        try:
            os.replace(tmp, path)
            return
        except PermissionError as e:          # Windows: a reader holds the destination open
            last = e
            import time
            time.sleep(0.1)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
    try:
        os.unlink(tmp)
    except OSError:
        pass
    raise last


def tracked_in_git(path):
    """True when git has a committed copy, i.e. the original is recoverable."""
    try:
        r = subprocess.run(["git", "ls-files", "--error-unmatch", os.path.relpath(path, HERE)],
                           cwd=HERE, capture_output=True, encoding="utf-8",
                           errors="replace", timeout=30)
        return r.returncode == 0
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="measure and print the plan only")
    ap.add_argument("--force", action="store_true", help="overwrite an existing history file")
    a = ap.parse_args()

    if not os.path.exists(SRC):
        say("[X] no CLAUDE.md at %s" % SRC)
        return 1

    with open(SRC, "rb") as fh:
        original = fh.read()

    existing = sorted(f for f in os.listdir(DEC) if f.startswith("HISTORY-")) \
        if os.path.isdir(DEC) else []

    say("=" * 78)
    say("  CLAUDE.md context budget")
    say("=" * 78)
    say("  current CLAUDE.md : %9s   ~%s tokens PER TURN" % (kb(len(original)), f"{tokens(len(original)):,}"))
    say("  budget            : %9s" % kb(BUDGET))
    say("  history already   : %s" % (", ".join(existing) if existing else "none"))

    # Idempotent no-op: already split.
    if len(original) <= BUDGET and existing and not a.force:
        say("")
        say("  Already split. CLAUDE.md is inside the budget and the history is in docs/decisions/.")
        say("  Nothing to do.")
        return 0

    if not os.path.exists(CORE):
        say("")
        say("[X] docs/CLAUDE.core.md is missing - that file is the NEW lean CLAUDE.md and this")
        say("    script only moves it into place. It is written by hand (or by Claude), never")
        say("    generated here: deciding which doctrine must hold on every turn is a judgement,")
        say("    not a transform, and a script that guessed at it would quietly drop a rule.")
        return 1

    with open(CORE, "rb") as fh:
        core = fh.read()

    stamp = datetime.date.today().isoformat()
    hist = os.path.join(DEC, "HISTORY-2026-07-to-%s.md" % stamp)

    say("  new CLAUDE.md     : %9s   ~%s tokens PER TURN" % (kb(len(core)), f"{tokens(len(core)):,}"))
    say("  history target    : %s" % os.path.relpath(hist, HERE))
    saved = len(original) - len(core)
    say("  saved per turn    : %9s   ~%s tokens" % (kb(saved), f"{tokens(saved):,}"))

    if len(core) > BUDGET:
        say("")
        say("[X] the new CLAUDE.md is %s, over the %s budget. Move more of it into" % (kb(len(core)), kb(BUDGET)))
        say("    docs/decisions/ before shipping - the whole point is the per-turn cost.")
        return 1

    if os.path.exists(hist) and not a.force:
        say("")
        say("[X] %s already exists. Refusing to overwrite a history file." % os.path.relpath(hist, HERE))
        say("    Re-run with --force only if you are certain it is a duplicate.")
        return 1

    if a.dry_run:
        say("")
        say("  DRY RUN - nothing written.")
        return 0

    # --- 1. write the history, then PROVE the original survived it ---------------------------
    payload = HEADER.encode("utf-8") + original
    atomic_write(hist, payload)

    with open(hist, "rb") as fh:
        back = fh.read()
    if not back.endswith(original) or len(back) != len(payload):
        say("")
        say("[X] the history copy does not contain the original byte-for-byte. NOTHING ELSE WAS")
        say("    TOUCHED - CLAUDE.md is unchanged. Read %s and investigate." % os.path.relpath(hist, HERE))
        return 1
    say("")
    say("  [ok] history written and verified: %s bytes, ends with the original exactly" % f"{len(back):,}")

    # --- 2. only now replace CLAUDE.md, by MOVING the core (so no second home can exist) ------
    in_git = tracked_in_git(SRC)
    atomic_write(SRC, core)
    try:
        os.unlink(CORE)
    except OSError as e:
        say("  [!] could not remove %s (%s). Delete it by hand: two files holding the same" %
            (os.path.relpath(CORE, HERE), e))
        say("      doctrine is exactly the drift this repository keeps paying for.")

    with open(SRC, "rb") as fh:
        now = fh.read()
    if now != core:
        say("[X] CLAUDE.md does not match what was written. Restore with:")
        say("    git checkout HEAD -- CLAUDE.md")
        return 1

    say("  [ok] CLAUDE.md replaced: %s -> %s" % (kb(len(original)), kb(len(now))))
    say("")
    say("  The full history is committed at %s" % os.path.relpath(hist, HERE))
    say("  The original is%s in git. To undo everything:  git checkout HEAD -- CLAUDE.md" %
        ("" if in_git else " NOT (uncommitted!)"))
    say("")
    say("  New incidents go in docs/decisions/<YYYY-MM>.md, with at most ONE line in CLAUDE.md.")
    say("  tests/test_claude_md_size.py fails the build if CLAUDE.md passes %s again." % kb(BUDGET))
    return 0


if __name__ == "__main__":
    sys.exit(main())
