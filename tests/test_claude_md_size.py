# -*- coding: utf-8 -*-
"""CLAUDE.md is re-injected into the model's context on EVERY turn.

It reached 646 KB / 307 sections, which is ~160,000 tokens spent before the operator types
anything, and that is what produced "This conversation is too long to continue". The narrative
history moved to docs/decisions/ on 2026-09-09.

Writing "keep it short" in the file itself is exactly the kind of rule this repository has watched
go stale over and over, so it is a build gate instead. The budget lives in ONE place
(docs_split.BUDGET) and is imported, never restated.
"""

import importlib.util
import os

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CLAUDE = os.path.join(ROOT, "CLAUDE.md")
DEC = os.path.join(ROOT, "docs", "decisions")
CORE = os.path.join(ROOT, "docs", "CLAUDE.core.md")


def _budget():
    """Load docs_split by PATH. Importing by name is how `import perseus` once silently picked up
    the package instead of the root script and measured the wrong module for a whole session."""
    p = os.path.join(ROOT, "docs_split.py")
    spec = importlib.util.spec_from_file_location("_docs_split_for_test", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.BUDGET


def test_claude_md_stays_inside_the_per_turn_context_budget():
    assert os.path.exists(CLAUDE), "CLAUDE.md is missing"
    size = os.path.getsize(CLAUDE)

    # A check that cannot fail is not a check: an empty or truncated CLAUDE.md must not pass a
    # size test by being small.
    assert size > 5_000, (
        "CLAUDE.md is only %d bytes - that is not a lean file, that is a truncated one. "
        "Restore it: git checkout HEAD -- CLAUDE.md" % size
    )

    budget = _budget()
    assert size <= budget, (
        "CLAUDE.md is %.1f KB, over the %.1f KB budget - about %d tokens of EVERY turn.\n"
        "Move the narrative into docs/decisions/<YYYY-MM>.md and leave the RULE here.\n"
        "If this is the first run after the history grew back:  python docs_split.py"
        % (size / 1024.0, budget / 1024.0, int(size / 4))
    )


def test_the_history_is_still_findable_from_claude_md():
    """A lean CLAUDE.md that does not say where the evidence went is worse than a long one: the
    rules lose their proof and the next person re-derives them from scratch."""
    text = open(CLAUDE, encoding="utf-8", errors="replace").read()
    assert "docs/decisions/" in text, (
        "CLAUDE.md must point at docs/decisions/ - the rules there are evidence-free without it"
    )

    if not os.path.isdir(DEC):
        pytest.skip("docs/decisions/ does not exist yet - run: python docs_split.py")
    files = [f for f in os.listdir(DEC) if f.endswith(".md")]
    assert files, "docs/decisions/ is empty - the history was not written"


def test_there_is_no_second_copy_of_the_doctrine():
    """docs_split.py MOVES docs/CLAUDE.core.md into place. If a copy is left behind, two files hold
    the same doctrine and the newer one always loses - the defect this repo records most often."""
    assert not os.path.exists(CORE), (
        "docs/CLAUDE.core.md still exists beside CLAUDE.md. It is a staging file that docs_split.py "
        "MOVES into place; two files holding the same doctrine will drift.\n"
        "If the split has not been run yet:  python docs_split.py"
    )
