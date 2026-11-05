/**
 * safe_text.js — the ONE implementation of "a control character must never reach a customer file".
 *
 * WHY THIS EXISTS (verint, Portuguese, 2026-11-03)
 *   The animated GEOPOL report shipped with "administra\x7f\x103o" where "administração" belonged,
 *   57 control characters across one page. It was NOT an encoding fault: the file was valid UTF-8,
 *   it carried <meta charset="utf-8">, "Múltiplas" in the same sentence was intact, and no
 *   encode/decode pair across the whole standard codec set reproduces the mapping. The model
 *   emitted corrupt bytes and every layer downstream passed them along, because escaping HTML and
 *   translating chrome are different questions from "is this text".
 *
 *   enrich._contract_ok() now REFUSES such an answer and fails over to the next model, which is the
 *   real fix. This module is the last line of defence, and it exists for the text that never went
 *   through the model at all: Shodan banners, PTR names, certificate subjects and HTTP titles are
 *   attacker-controlled and have no business carrying control bytes into a deck or a report.
 *
 * WHAT IT DOES NOT DO
 *   It does not repair. Corruption that ate a cedilla ate letters too, and "administrao" is still
 *   wrong — it is merely wrong without a control character in it. Silent repair would turn a loud
 *   defect into a quiet one, so the engine-side refusal stays the primary control and this is only
 *   the floor beneath it.
 */
"use strict";

// C0 controls except TAB, LF and CR, plus DEL. Nothing in natural-language prose is in this set.
const CTRL = /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/g;

/** Remove control characters from one value. Non-strings pass through untouched. */
function stripControls(s) {
  return typeof s === "string" ? s.replace(CTRL, "") : s;
}

/** How many control characters are in this value — for a gate that wants to report, not repair. */
function countControls(s) {
  if (typeof s !== "string") return 0;
  const m = s.match(CTRL);
  return m ? m.length : 0;
}

module.exports = { stripControls, countControls, CTRL };
