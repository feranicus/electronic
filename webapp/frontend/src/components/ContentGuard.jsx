import { useEffect, useState, useRef } from "react";
import { useT } from "../i18n.jsx";

/**
 * ContentGuard — right-click and the source/save/devtools shortcuts are intercepted, and the
 * visitor is told why.
 *
 * WHAT THIS IS: a deterrent and a notice, which is what commercial sites use it for. It signals
 * that the methodology and copy are protected IP, and it stops the casual "right-click, save
 * image / view source" reflex. It is not a technical control and is not presented as one: the
 * browser already holds the bytes. That distinction lives in this comment, not in the UI.
 *
 * FOUR THINGS IT MUST NOT BREAK, each of which would be a real defect:
 *
 *   1. FORM FIELDS. The cabinet's whole job is typing a company name, and people paste it. A
 *      context menu blocked inside an input takes away paste, spellcheck and "undo" and would
 *      make the product actively worse. Inputs, textareas, selects and contenteditable are
 *      exempt, always.
 *   2. COPYING RESULTS. Nothing here blocks selection or Ctrl+C. A partner reading the 5,000-word
 *      /partners page, or an operator copying a job id out of the run log, is doing exactly what
 *      the product is for. Blocking copy is the most user-hostile version of this feature and
 *      buys nothing an attacker cannot trivially undo.
 *   3. ACCESSIBILITY. Only the specific shortcuts below are intercepted. Tab, arrows, Enter,
 *      Escape and every screen-reader key are untouched, and the notice is announced politely
 *      (role="status", aria-live) rather than trapping focus.
 *   4. THE LANGUAGE. This is a string that reaches a human, so it goes through the dictionary in
 *      all six locales. A hardcoded English notice on the German site would fail the i18n audit,
 *      and rightly.
 *
 * DevTools is deliberately NOT chased beyond the keyboard shortcuts. Menu -> More tools -> and
 * the panel is open anyway, so a detection loop would burn CPU on every visitor's machine to
 * inconvenience nobody. Doing the honest 90% cleanly beats a loop that lies about the last 10%.
 */
const BLOCKED_KEYS = [
  // [ctrl/meta, shift, key] — the shortcuts that mean "give me the source or a copy of the page"
  { ctrl: true, shift: false, key: "u" },   // view-source
  { ctrl: true, shift: false, key: "s" },   // save page
  { ctrl: true, shift: true, key: "i" },    // devtools
  { ctrl: true, shift: true, key: "j" },    // console
  { ctrl: true, shift: true, key: "c" },    // inspect element
  { ctrl: false, shift: false, key: "f12" },
];

function isEditable(el) {
  if (!el) return false;
  const tag = (el.tagName || "").toLowerCase();
  if (tag === "input" || tag === "textarea" || tag === "select") return true;
  if (el.isContentEditable) return true;
  return !!(el.closest && el.closest("input, textarea, select, [contenteditable='true']"));
}

export default function ContentGuard() {
  const [, , t] = useT();          // useT() returns [lang, setLang, t] - read it, do not assume
  const [shown, setShown] = useState(false);
  const timer = useRef(null);

  useEffect(() => {
    const announce = () => {
      setShown(true);
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(() => setShown(false), 4200);
    };

    const onContextMenu = (e) => {
      if (isEditable(e.target)) return;          // never take paste away from a form field
      e.preventDefault();
      announce();
    };

    const onKeyDown = (e) => {
      const k = (e.key || "").toLowerCase();
      const ctrl = e.ctrlKey || e.metaKey;
      const hit = BLOCKED_KEYS.some((b) => b.key === k && b.ctrl === ctrl && b.shift === e.shiftKey);
      if (!hit) return;
      if (isEditable(e.target) && k === "s") return;   // Ctrl+S in a field is not "save page"
      e.preventDefault();
      announce();
    };

    // Dragging an image out of the page is the other half of the right-click reflex.
    const onDragStart = (e) => {
      const tag = (e.target && e.target.tagName || "").toLowerCase();
      if (tag === "img" || tag === "svg") e.preventDefault();
    };

    document.addEventListener("contextmenu", onContextMenu);
    document.addEventListener("keydown", onKeyDown);
    document.addEventListener("dragstart", onDragStart);
    return () => {
      document.removeEventListener("contextmenu", onContextMenu);
      document.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("dragstart", onDragStart);
      if (timer.current) clearTimeout(timer.current);
    };
  }, []);

  return (
    <div
      className={"cg-guard" + (shown ? " on" : "")}
      role="status"
      aria-live="polite"
      aria-hidden={shown ? "false" : "true"}
    >
      <div className="cg-guard-i" aria-hidden="true">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="11" width="18" height="11" rx="2" />
          <path d="M7 11V7a5 5 0 0 1 10 0v4" />
        </svg>
      </div>
      <div className="cg-guard-t">
        <strong>{t("guard.title")}</strong>
        <span>{t("guard.body")}</span>
      </div>
    </div>
  );
}
