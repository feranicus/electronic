# docs/ — the cybergod.ai user manual

`cybergod.ai_User_Manual.docx` is generated, not hand-edited. **Edit `build_manual.js`, never the
.docx** — a hand-edited Word file is overwritten by the next build and its changes are lost.

## Build

```
cd "C:\Python SW\Linkedin Scraper"
npm install docx          # once
node docs/build_manual.js
```

Output: `docs/cybergod.ai_User_Manual.docx` (18 pages, A4, Colt-branded).

## Verify before sharing

```
soffice --headless --convert-to pdf docs/cybergod.ai_User_Manual.docx
pdftoppm -jpeg -r 80 docs/cybergod.ai_User_Manual.pdf /tmp/pg/page
```
Then look at the images. A green build proves nothing about layout — orphaned lines and blank
pages only show up in the render.

## Rules that keep it correct

- **Every fact in the manual came from the code** (colt_auth.py, run_assessment.py,
  NewAssessment.jsx, Login.jsx, bot.py, legal.jsx). If you change the product, change
  `build_manual.js` in the SAME commit. A manual that has drifted is worse than no manual.
- **Headings use `pageBreakBefore`, never a trailing `PageBreak()` paragraph.** When a section
  happens to fill a page exactly, the break paragraph lands on the next page and leaves a totally
  blank sheet.
- **Every numbered list calls `steps()`**, which burns a fresh numbering `instance`. Sharing one
  reference makes docx continue a single list, so §3 opens at "5.".
- **No emoji.** They render as tofu boxes in Consolas/PDF. The Telegram language buttons are drawn
  as plain `[ English ] [ Deutsch ]`.
- `table()` always draws a header bar — use `plainTable()` for key/value blocks, or you get an empty
  dark stripe.

## Known product/doc inconsistencies (flagged, not silently papered over)

These were found while fact-checking the manual. The manual is written to be accurate; the PRODUCT
should be fixed:

1. `NewAssessment.jsx` says both "Typically 3–7 minutes" and "usually takes about two minutes".
   Pick one.
2. The Assess screen still warns "refreshing cancels the run". It no longer does — the job is
   server-side and the page re-attaches. The string is stale.
3. `legal.jsx` claims 30-day log retention; `obs/loki-config.yml` is set to 168h (7 days).
   The manual says "up to 30 days" so it is not wrong, but the two should agree.
4. `legal.jsx` claims assessment data is kept "90 days, or until deleted by the user". There is no
   purge job in `store.py` and no delete UI/endpoint. Either implement both, or reword the notice.
5. `shodan_recon._favicon_hash` makes one direct HTTPS GET to the target for `/favicon.ico`, so the
   absolute phrase "no active scanning" in `legal.jsx` is not literally true. The manual says
   "no port scanning, no vulnerability probing, no login attempts" instead.
