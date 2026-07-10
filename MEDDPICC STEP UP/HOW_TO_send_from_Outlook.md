# MEDDPICC STEP UP — send individual emails from your Colt address

Goal: each of the 37 AEs gets an **individual** email that is **From** and **Reply-To**
`jevgenijs.vainsteins@colt.net`, with **Stephan Wanke + Alex Kress (+ you) in CC**, and the
example report attached. Because it goes through your real Outlook mailbox, replies come
straight back to you and it won't be spam-flagged.

Files in this folder:
- `AE_recipients.csv` — the 37 AEs (FirstName / LastName / Email)
- `email_template_MONDAY.txt` — the kickoff/ask email (uses «FirstName»)
- `email_template_FRIDAY.txt` — the shorter end-of-week status email
- Attach: `..\Richard Account review\Stephan_Security_Report_09Jul2026_v2.pptx`

## Option A — Mail Merge Toolkit (does CC + attachments; recommended)

Native Word mail-merge can't CC or attach files, so install the free/*low-cost*
**Mail Merge Toolkit** add-in (MAPILab) once. Then:

1. **Word → Mailings → Start Mail Merge → E-Mail Messages.**
2. **Select Recipients → Use an Existing List →** pick `AE_recipients.csv`.
3. Paste the body from `email_template_MONDAY.txt`. Replace `«FirstName»` with
   **Insert Merge Field → FirstName** (the file already shows where it goes).
4. **Finish & Merge → Merge to E-Mail (Mail Merge Toolkit).** In its dialog:
   - **To:** Email field · **Subject:** the subject line · **Format:** HTML or Plain
   - **CC:** `Stephan.Wanke@colt.net; Alexander.Kress@colt.net; Jevgenijs.Vainsteins@colt.net`
   - **Attach:** `Stephan_Security_Report_09Jul2026_v2.pptx`
5. Send. Make sure Outlook is set to send **from** `jevgenijs.vainsteins@colt.net`
   (if you have multiple accounts, pick it as the sending account).

Repeat Fridays with `email_template_FRIDAY.txt` (no attachment needed).

## Option B — No add-in (individual, from you, but no per-mail CC/attachment)

If you don't want the add-in: do plain Word mail-merge to email (steps 1–3, then
**Finish & Merge → Send E-Mail Messages**). Each AE still gets an individual mail from
your Colt address and replies come to you — but you won't be able to CC Stephan/Alex or
attach the deck per message. Workaround: **Bcc yourself** isn't available either in native
merge, so instead send Stephan + Alex a single copy separately, and share the deck via a
OneDrive/SharePoint link in the body.

## Why not just automate it from Gmail?
Automation here sends from `feranicus@s4biz.io` (not Colt) and can't set Reply-To, so
replies wouldn't land in your Colt inbox on a plain "Reply." Outlook mail-merge is the only
route that is genuinely *from you at Colt*. Trade-off: you run it (2 min) each Mon & Fri.
