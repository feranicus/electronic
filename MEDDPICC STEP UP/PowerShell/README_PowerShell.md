# MEDDPICC STEP UP — fully automatic, pure PowerShell (no man-in-the-middle)

Sends the emails itself via Gmail SMTP — no drafts, no Claude, no clicking. Sets
**Reply-To = jevgenijs.vainsteins@colt.net**, attaches the deck, CCs Stephan/Alex/you,
runs **Monday & Friday** via Windows Task Scheduler.

## The only two one-time things (unavoidable)
1. A Gmail **App Password** (Google requires it for SMTP — I can't create it for you).
2. Your **PC must be on** at Mon/Fri 09:00 (that's the one thing the cloud Apps Script avoids).

## Setup (5 minutes)

### 1. Get a Gmail App Password
- Your Google account needs **2-Step Verification ON** (myaccount.google.com/security).
- Go to **myaccount.google.com/apppasswords** → create one named "MEDDPICC" → copy the
  16-character password.
- If s4biz.io is Google **Workspace** and you don't see App Passwords, your admin has to
  allow them (Security → less secure / app passwords). If blocked, use the Apps Script
  version instead (no password needed).

### 2. Store it
- In this `PowerShell` folder, create a file **`app_password.txt`** and paste the 16-char
  password as the only line. Keep it private (don't share/commit it).

### 3. Put the deck where the script expects it
- The script attaches:
  `C:\Users\feran\Downloads\Richard Account review\Stephan_Security_Report_09Jul2026_v2.pptx`
- It's already there. (If you move/rename it, update `$Attachment` at the top of
  `Send-Meddpicc.ps1`.)

### 4. Test
```powershell
cd "C:\Users\feran\Downloads\MEDDPICC STEP UP\PowerShell"
powershell -ExecutionPolicy Bypass -File .\Send-Meddpicc.ps1 -Mode test
```
It emails **evgeny@s4biz.io**. Open it → **Reply** → the To field must show
`jevgenijs.vainsteins@colt.net`, deck attached, HTML looks right. ✅

### 5. Schedule it
```powershell
powershell -ExecutionPolicy Bypass -File .\Setup-Meddpicc.ps1
```
Registers Monday & Friday 09:00. That's it — it now sends on its own.

## Go live vs test
- `$GoLive = $true` (default) → scheduled runs send to all 37 AEs.
- Set `$GoLive = $false` in `Send-Meddpicc.ps1` to keep the scheduled runs going only to
  yourself until you're happy, then flip to `$true`.

## Edit anything
- **Recipients:** the `$Recipients` array. **Wording/design:** `Get-Html`.
  **CC / Reply-To / send time:** the CONFIG block / `Setup-Meddpicc.ps1`.
- **Remove the schedule:**
  `Unregister-ScheduledTask -TaskName 'MEDDPICC STEP UP - Monday','MEDDPICC STEP UP - Friday'`

## PowerShell vs Apps Script (both are in this folder)
| | PowerShell (this) | Apps Script |
|---|---|---|
| Sends automatically | ✅ | ✅ |
| Reply-To your Colt address | ✅ | ✅ |
| Deck attached | ✅ | ✅ |
| Needs your PC on | **Yes** | No (runs in Google cloud) |
| Credential | Gmail App Password | none (runs as you) |

Pick whichever fits. If your laptop isn't always on at 9:00, the Apps Script version is the
more reliable "set and forget."
