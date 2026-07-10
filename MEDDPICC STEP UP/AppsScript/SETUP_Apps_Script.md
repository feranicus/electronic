# MEDDPICC STEP UP — fully automatic send (Google Apps Script)

This is the real thing: runs in Google's cloud under your s4biz account, **sends
automatically** (no drafts), sets **Reply-To = jevgenijs.vainsteins@colt.net**, **attaches
the deck**, one **individual** email per AE, **CC** Stephan + Alex + you, every **Monday &
Friday**. Your machine doesn't need to be on.

## One-time setup (~5 minutes)

1. **Upload the deck to your Google Drive** (any folder). Keep the exact filename
   `Stephan_Security_Report_09Jul2026_v2.pptx` (or edit `ATTACHMENT_NAME` in the script).

2. Go to **https://script.google.com** → **New project**. Delete the sample code, then
   **paste the entire `Code.gs`** from this folder. Save (💾).

3. **Project Settings** (⚙ left sidebar) → set **Time zone** to *(GMT+01:00) Berlin* so
   9:00 means 9:00 your time.

4. **Test it.** In the editor, choose the function **`sendTest`** in the toolbar dropdown →
   **Run**. Google asks you to **authorize** (it's your own account — approve Gmail + Drive).
   It emails **evgeny@s4biz.io**. Open it and hit **Reply** → the To field must show
   `jevgenijs.vainsteins@colt.net`, and the deck should be attached. ✅

5. **Schedule it.** Choose **`setupTriggers`** → **Run**. Done — it now fires **Monday &
   Friday at 09:00** on its own.

## Going live
- The script has `GO_LIVE = true`, so the scheduled runs send to **all 37 AEs**.
- Want to keep testing to just yourself first? Set `GO_LIVE = false` (top of the script) —
  then the Monday/Friday runs go only to `TEST_EMAIL`. Flip it to `true` when you're happy.

## Change anything later
- **Recipients:** edit the `RECIPIENTS` array.
- **Wording / design:** edit `htmlMonday()` / `htmlFriday()`.
- **CC / Reply-To / send time:** the `CONFIG` block at the top.
- **Stop it:** in the editor → **Triggers** (⏰ left sidebar) → delete the two triggers.

## Notes
- Sending limits: Google Workspace ~1,500–2,000 recipients/day (consumer Gmail 500) — 37×2/wk
  is nothing.
- Reply-To is a real header set per email by `GmailApp.sendEmail(..., {replyTo: ...})`, so a
  plain **Reply** always lands on your Colt address, even though the From is your s4biz Gmail.
- This does **not** need Power Automate, Docker, Hermes, or any Colt-tenant permission — it
  lives entirely in your Google account.
