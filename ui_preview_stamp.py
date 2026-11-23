#!/usr/bin/env python3
"""ui_preview_stamp.py — "you must look at a UI change before you ship it", enforced.

STANDING RULE, from the operator, 9 Aug 2026:
    Before `python ship.py`, any frontend UI or UX change must be previewed locally with
    `python preview.py` and looked at. Every time.

WHY IT IS CODE AND NOT A LINE IN CLAUDE.md. This session alone shipped four colour defects that a
ten-second look would have caught and no automated check could: a dark bar framing a light page
(twice), white text on a white menu, and an unreadable badge. Every gate was green each time,
because a gate can measure contrast and structure but it cannot see. CLAUDE.md is also full of
rules that went stale precisely because they were only written down. So the rule is a gate.

HOW IT WORKS, and why the stamp is a HASH rather than a timestamp:
  · `preview.py` writes `.ui-preview-stamp` containing the sha256 of every UI file, at the moment
    the preview server starts.
  · `ship.py` recomputes that hash. If it matches, this exact frontend was previewed. If it does
    not, the UI changed since you last looked at it, and ship stops.
  · A timestamp would only prove that a preview happened at some point, which is the same defect
    as `config_write_ordering` proving startup ORDERING rather than content. A hash proves you previewed
    THIS version. Same doctrine as the engine-hash deploy verify.
  · After a successful ship, `ship.py` records the shipped hash. If nothing UI-related has changed
    since then, no preview is asked for. You are only ever stopped when there is something new to
    look at.

Both files are gitignored: they describe THIS machine's state, not the repo's.
"""
import hashlib
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FE = ROOT / "webapp" / "frontend"
STAMP = ROOT / ".ui-preview-stamp"      # written by preview.py
SHIPPED = ROOT / ".ui-shipped-hash"     # written by ship.py after a successful deploy

# What counts as a UI or UX change. Deliberately narrow: a backend or engine edit must not make
# the operator open a browser for nothing, or the gate becomes noise and gets switched off.
UI_DIRS = [
    (FE / "src", (".jsx", ".js", ".css")),
    (FE / "public", (".webmanifest", ".svg", ".png", ".xml", ".txt", ".html")),
]
UI_FILES = [FE / "index.html"]


def ui_files():
    """Every file whose change a person could SEE. Sorted, so the hash is stable."""
    out = []
    for d, exts in UI_DIRS:
        if not d.exists():
            continue
        for p in sorted(d.rglob("*")):
            if p.is_file() and p.suffix.lower() in exts:
                out.append(p)
    out += [p for p in UI_FILES if p.exists()]
    return sorted(out)


# Text extensions get their line endings normalised before hashing. Binaries never do: a PNG can
# legitimately contain the bytes 0d 0a and "normalising" it would corrupt the digest.
_TEXT_SUFFIXES = {".jsx", ".js", ".mjs", ".ts", ".tsx", ".css", ".html", ".json",
                  ".webmanifest", ".txt", ".xml", ".svg", ".md"}


def ui_hash():
    """One sha256 over the whole UI surface: names and contents.

    LINE ENDINGS ARE NORMALISED, and that is not cosmetic. The hash used to be over RAW BYTES, so
    a Windows checkout (CRLF in the working copy, because core.autocrlf rewrites on checkout) and a
    Linux checkout of the SAME COMMIT produced DIFFERENT digests. The stamp then meant "previewed
    on this operating system" rather than "previewed", which is not the claim it advertises: the
    gate could not be evaluated from anywhere except the machine that wrote it, and a check nobody
    else can evaluate is a check nobody else can trust.

    This is the third appearance of the same trap in this repo: `git archive` applying autocrlf
    made the deploy artefact platform-dependent, and before that the CRLF-over-ssh script failure.
    Content is content; the byte that ends a line is the platform's business, not ours.
    """
    h = hashlib.sha256()
    for p in ui_files():
        h.update(str(p.relative_to(ROOT)).replace("\\", "/").encode())
        h.update(b"\0")
        b = p.read_bytes()
        if p.suffix.lower() in _TEXT_SUFFIXES:
            b = b.replace(b"\r\n", b"\n")
        h.update(b)
        h.update(b"\0")
    return h.hexdigest()


def _read(p):
    try:
        return p.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def write_preview_stamp():
    """Called by preview.py when the server starts."""
    h = ui_hash()
    STAMP.write_text(h, encoding="utf-8")
    return h


def record_shipped():
    """Called by ship.py after a deploy that verified."""
    SHIPPED.write_text(ui_hash(), encoding="utf-8")


def full_stack_change(run=None):
    """Does this working tree change the BACKEND as well as the frontend?

    THE GATE CAN ONLY HELP WITH A FRONTEND-ONLY CHANGE, and pretending otherwise blocks ships it
    cannot improve. `preview.py` serves the built frontend and nothing else: no FastAPI, no sqlite,
    no model chain. A feature whose screen is a form posting to a new route, backed by a new table
    and a four-model panel, renders in the preview as a page that errors on load - so "look at it"
    produces no evidence about the thing that was built, and demanding it anyway trains the
    operator to reach for `--no-preview` on every ship, which is how the gate dies for the pure-UI
    tweak it IS good at.

    For a full-stack change the STAGING GATE is the preview: it builds the real image, runs the
    real backend against a real database on the twin, exercises the engine, reboots the box and
    re-checks. That is strictly more evidence than a person looking at a dev server, and it is
    already mandatory.

    Measured from git, never from a flag: a flag would be the operator asserting it, and this is a
    fact about the diff. Unknown (no git, not a repo) counts as NOT full-stack, so the gate keeps
    asking rather than quietly letting a UI change through on an unanswered question (class 1).
    """
    import subprocess
    runner = run or (lambda c: subprocess.run(c, cwd=str(ROOT), capture_output=True, text=True,
                                              timeout=30))
    try:
        r = runner(["git", "status", "--porcelain", "--untracked-files=all"])
        if r.returncode != 0:
            return False, []
        paths = [ln[3:].strip().strip('"') for ln in (r.stdout or "").splitlines() if ln[3:].strip()]
    except Exception:
        return False, []
    fe = "webapp/frontend/"
    back = [p for p in paths
            if not p.startswith(fe)
            and p.endswith((".py", ".sql", ".yml", ".yaml", ".toml", ".json"))
            and not p.startswith(("docs/", "tests/", "marketing/"))]
    return bool(back), back[:8]


def check():
    """(ok, message). ok=False means: the UI changed and has not been previewed."""
    now = ui_hash()
    if _read(STAMP) == now:
        return True, "previewed (%d UI files, %s)" % (len(ui_files()), now[:12])
    if _read(SHIPPED) == now:
        return True, "no UI change since the last deploy (%s)" % now[:12]
    full, why = full_stack_change()
    if full:
        return True, ("the UI changed, and so did the backend (%s) - `preview.py` serves the "
                      "frontend alone, so it cannot render this. The STAGING GATE is the preview "
                      "for a full-stack change: real image, real backend, real database, on the "
                      "twin, with a reboot." % ", ".join(why))
    if not _read(SHIPPED) and not _read(STAMP):
        # First run on this machine: nothing to compare against. Ask once rather than assert
        # something untrue about what has or has not been looked at.
        return False, ("no record of a preview on this machine yet (first run). Look at the site "
                       "once, then ship.")
    return False, ("the frontend has changed since it was last previewed. UI hash is %s; the "
                   "preview stamp is %s." % (now[:12], (_read(STAMP) or "absent")[:12]))


if __name__ == "__main__":
    ok, msg = check()
    print(("OK   " if ok else "STOP ") + msg)
    print("     %d UI files under webapp/frontend" % len(ui_files()))
    raise SystemExit(0 if ok else 1)
