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


def ui_hash():
    """One sha256 over the whole UI surface: names and contents."""
    h = hashlib.sha256()
    for p in ui_files():
        h.update(str(p.relative_to(ROOT)).replace("\\", "/").encode())
        h.update(b"\0")
        h.update(p.read_bytes())
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


def check():
    """(ok, message). ok=False means: the UI changed and has not been previewed."""
    now = ui_hash()
    if _read(STAMP) == now:
        return True, "previewed (%d UI files, %s)" % (len(ui_files()), now[:12])
    if _read(SHIPPED) == now:
        return True, "no UI change since the last deploy (%s)" % now[:12]
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
