# MEDDPICC STEP UP — automate it from your Colt address (Power Automate)

## Short answer
Yes. **Power Automate** (part of your Microsoft 365, same family as Copilot) can send
these emails automatically, **from `jevgenijs.vainsteins@colt.net`**, on a schedule,
**individually** to each AE, with **CC** and the **report attached** — and because it runs
through your real mailbox, replies come straight back to you and it won't be spam-flagged.

**Copilot vs Power Automate:** Microsoft 365 Copilot itself doesn't run scheduled sends.
The engine is **Power Automate**. The nice part: Power Automate has a built-in **Copilot
("Describe it to design it")** that builds the flow from a plain-English prompt — see below.

> Caveat: this only works if Colt has Power Automate + the "Office 365 Outlook" connector
> enabled for your account (usually on by default). If it's blocked, that's a Colt IT toggle.
> Go to https://make.powerautomate.com — if you can create a flow, you're good.

## Setup (one-time)
1. Put two files in your **OneDrive** (so the flow can read them):
   - `AE_recipients.xlsx` (in this folder) — it already has a formatted table called **Recipients**.
   - `Stephan_Security_Report_09Jul2026_v2.pptx` (from the `Richard account review` folder).

## Option 1 — Let Power Automate's Copilot build it
At https://make.powerautomate.com click **Create → Describe it to design it** (Copilot) and paste:

> Every Monday and Friday at 09:00 (W. Europe Standard Time), read the rows of the
> **Recipients** table in my OneDrive file **AE_recipients.xlsx**. For each row, send an email
> **from my mailbox** to the row's **Email**, with **CC**
> `Stephan.Wanke@colt.net; Alexander.Kress@colt.net; Jevgenijs.Vainsteins@colt.net`,
> subject **"MEDDPICC STEP UP — your July/August security deals (DDoS · SD-WAN · SASE)"**,
> body starting **"Hi [FirstName],"** followed by the text I provide, and **attach**
> `Stephan_Security_Report_09Jul2026_v2.pptx` from my OneDrive.

Then paste the body from `email_template_MONDAY.txt`. Review and Save.

## Option 2 — Build it manually (reliable, ~10 min)
1. **Create → Scheduled cloud flow.** Recurrence: **Week**, on **Monday, Friday**, time **09:00**,
   and **set Time zone = W. Europe Standard Time** (don't leave it blank).
2. Action **Excel Online (Business) → List rows present in a table** → your OneDrive
   `AE_recipients.xlsx`, table **Recipients**.
3. (Optional attachment) **OneDrive for Business → Get file content** → the .pptx.
4. Action **Office 365 Outlook → Send an email (V2)**. Power Automate wraps it in an
   **Apply to each** over the table rows automatically. Fill in:
   - **To:** `Email` (dynamic content from the table)
   - **Subject:** MEDDPICC STEP UP — your July/August security deals (DDoS · SD-WAN · SASE)
   - **Body:** paste `email_template_MONDAY.txt`, replacing `«FirstName»` with the `FirstName`
     dynamic field.
   - **Show advanced options → CC:** `Stephan.Wanke@colt.net; Alexander.Kress@colt.net; Jevgenijs.Vainsteins@colt.net`
   - **Attachments:** Name = the file name, Content = the "Get file content" output.
5. **Test** first: set recurrence to every 5 min and change the table to just your own email,
   confirm it sends from your Colt address and looks right, then switch to the Mon/Fri schedule.

## Friday variant
Duplicate the flow (or add a condition on the weekday) and use the shorter
`email_template_FRIDAY.txt` (no attachment needed) for the Friday end-of-week nudge.

## Why this beats the Gmail automation
The Claude/Gmail route sends from `feranicus@s4biz.io` and can't set Reply-To. Power Automate
sends from **your** Colt mailbox — From and Reply-To are natively `jevgenijs.vainsteins@colt.net`,
so a plain "Reply" lands in your inbox. This is the automated, from-you solution.
