/**
 * creed.js — the Cassandra line. ONE definition, used by every deck builder.
 *
 * "Cassandra foretold the fall of Troy — and no one believed her."
 * "We predict the critical cyber risks, stop them before they materialise,
 *  and keep every Trojan horse out of your IT landscape."
 *
 * WHY A SHARED MODULE: the same sentence hardcoded in five builders is five chances to drift.
 * Change it here and every deck follows. Same reasoning as legal.jsx for the privacy copy and
 * de.json for the deck chrome.
 *
 * WHY PLAIN addText CALLS (not a rich-text array): deck_i18n wraps addText and translates at that
 * boundary by looking the RENDERED STRING up in de.json. A plain string per line is the exact path
 * every other translated literal takes, so the German cover works with no special casing. The two
 * lines are therefore two separate keys in de.json — keep them in sync with the strings below.
 */
const LINE1 = "Cassandra foretold the fall of Troy — and no one believed her.";
const LINE2 = "We predict the critical cyber risks, stop them before they materialise, "
            + "and keep every Trojan horse out of your IT landscape.";

// German. The four security builders get DE for free via deck_i18n (these exact strings are keys in
// i18n/de.json). build_compliance_deck.js deliberately does NOT use deck_i18n — it carries its own
// label map — so it passes {lang:"de"} and we translate here. Both paths MUST produce identical
// German: scripts/test_creed.js asserts these constants equal the de.json values.
const LINE1_DE = "Kassandra sagte den Fall Trojas voraus \u2014 und niemand glaubte ihr.";
const LINE2_DE = "Wir sagen die kritischen Cyber-Risiken voraus, stoppen sie, bevor sie eintreten, "
               + "und halten jedes trojanische Pferd aus Ihrer IT-Landschaft fern.";

/**
 * draw(pres, slide, opts) — render the creed on a cover slide.
 * opts: { x, y, w, color, accent, fontFace, rule }
 * Defaults suit a 10 x 5.625in cover. Callers pass y to fit their own layout's free band.
 */
function draw(pres, s, o) {
  o = o || {};
  const x = o.x != null ? o.x : 0.5;
  const y = o.y != null ? o.y : 3.20;
  const w = o.w != null ? o.w : 7.7;
  const col = o.color || "121212";
  const acc = o.accent || "00B2A9";
  const FF = o.fontFace || "Segoe UI";
  // tunable: the compliance cover has a much shallower free band than the other four
  const s1 = o.size1 != null ? o.size1 : 9.5;
  const s2 = o.size2 != null ? o.size2 : 10.5;
  const h2 = o.h2 != null ? o.h2 : 0.40;
  const dy2 = o.dy2 != null ? o.dy2 : 0.34;
  // only non-i18n builders pass lang; the wrapped ones leave it unset and deck_i18n translates
  const de = String(o.lang || "en").toLowerCase().startsWith("de");
  const l1 = de ? LINE1_DE : LINE1, l2 = de ? LINE2_DE : LINE2;

  // hairline rule + gold tick: the same divider language the rest of the covers use
  if (o.rule !== false) {
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: 0.34, h: 0.025,
      fill: { color: acc }, line: { type: "none" } });
  }
  s.addText(l1, { x, y: y + 0.09, w, h: 0.20,
    fontSize: s1, fontFace: FF, color: col, italic: true, margin: 0 });
  s.addText(l2, { x, y: y + dy2, w, h: h2,
    fontSize: s2, fontFace: FF, color: col, bold: true, margin: 0 });
}

module.exports = { LINE1, LINE2, LINE1_DE, LINE2_DE, draw };
