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
const BRAND = require("./brand.js");   // White Label: the attribution line below the creed

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

// Russian. Same contract as the German pair: these are COPIES of the i18n/ru.json values, and
// test_creed.js asserts they are byte-identical, so the wrapped builders (via deck_i18n) and the
// compliance builder (which carries its own labels) can never render two different creeds.
const LINE1_RU = "Кассандра предсказала падение Трои — и никто ей не поверил.";
const LINE2_RU = "Мы предсказываем критические киберриски, останавливаем их до реализации и не пускаем ни одного троянского коня в ваш IT-ландшафт.";

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
  const acc = o.accent || BRAND.recolor("00D7BD");   // was the RETIRED Colt teal 00B2A9
  const FF = o.fontFace || "Segoe UI";
  // tunable: the compliance cover has a much shallower free band than the other four
  const s1 = o.size1 != null ? o.size1 : 9.5;
  const s2 = o.size2 != null ? o.size2 : 10.5;
  const h2 = o.h2 != null ? o.h2 : 0.40;
  const dy2 = o.dy2 != null ? o.dy2 : 0.34;
  // Only non-i18n builders pass lang; the wrapped ones leave it unset and deck_i18n translates.
  // A TABLE, not a ternary: `de ? X : Y` had to be rewritten for the third language, and that is
  // exactly the kind of edit that gets made in one builder and forgotten in another.
  const code = String(o.lang || "en").toLowerCase().slice(0, 2);
  const BY_LANG = { de: [LINE1_DE, LINE2_DE], ru: [LINE1_RU, LINE2_RU] };
  const [l1, l2] = BY_LANG[code] || [LINE1, LINE2];

  // hairline rule + gold tick: the same divider language the rest of the covers use
  if (o.rule !== false) {
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: 0.34, h: 0.025,
      fill: { color: acc }, line: { type: "none" } });
  }
  s.addText(l1, { x, y: y + 0.09, w, h: 0.20,
    fontSize: s1, fontFace: FF, color: col, italic: true, margin: 0 });
  s.addText(l2, { x, y: y + dy2, w, h: h2,
    fontSize: s2, fontFace: FF, color: col, bold: true, margin: 0 });

  // WHITE LABEL ATTRIBUTION. Drawn HERE, inside the one cover element every builder already calls,
  // rather than added to each builder in turn — five copies of an attribution line is five chances
  // for one deck to ship without it, which is precisely the drift this module was created to stop.
  // Returns "" when no partner theme is active, so an unbranded deck is byte-identical to before.
  const by = BRAND.poweredBy();
  if (by) {
    s.addText(by, { x, y: y + dy2 + h2 + 0.04, w, h: 0.20,
      fontSize: 7.5, fontFace: FF, color: col, margin: 0, transparency: 35 });
  }
}

module.exports = { LINE1, LINE2, LINE1_DE, LINE2_DE, LINE1_RU, LINE2_RU, draw };
