/**
 * test_creed.js — the creed is translated by TWO independent paths:
 *   1. the four security builders -> deck_i18n looks the English string up in i18n/de.json
 *   2. build_compliance_deck.js   -> creed.js translates directly (it has no deck_i18n)
 * If those two ever disagree, one deck family silently ships different German. Pin them.
 */
const C = require("./creed.js"), de = require("./i18n/de.json").strings,
      ru = require("./i18n/ru.json").strings;
let bad = 0;
const check = (cond, label) => { console.log((cond ? "  ok   " : "  FAIL ") + label); if (!cond) bad++; };
check(!!de[C.LINE1], "de.json has a translation for creed line 1");
check(!!de[C.LINE2], "de.json has a translation for creed line 2");
check(de[C.LINE1] === C.LINE1_DE, "line 1 German matches between de.json and creed.js");
check(de[C.LINE2] === C.LINE2_DE, "line 2 German matches between de.json and creed.js");
check(!!ru[C.LINE1], "ru.json has a translation for creed line 1");
check(!!ru[C.LINE2], "ru.json has a translation for creed line 2");
check(ru[C.LINE1] === C.LINE1_RU, "line 1 Russian matches between ru.json and creed.js");
check(ru[C.LINE2] === C.LINE2_RU, "line 2 Russian matches between ru.json and creed.js");
check(/Troy/.test(C.LINE1) && /Trojas/.test(C.LINE1_DE) && /Трои/.test(C.LINE1_RU),
      "all three languages name Troy");
check(/Trojan horse/.test(C.LINE2) && /trojanische Pferd/.test(C.LINE2_DE), "both keep the Trojan-horse image");
console.log(bad ? "\ncreed: " + bad + " FAILURE(S)" : "\ncreed: all checks passed");
process.exit(bad ? 1 : 0);
