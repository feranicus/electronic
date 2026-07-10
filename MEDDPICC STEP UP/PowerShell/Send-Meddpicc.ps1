<#
  MEDDPICC STEP UP - sends individual emails to each AE via Gmail SMTP.
  From feranicus@s4biz.io, Reply-To jevgenijs.vainsteins@colt.net, CC Stephan/Alex/Jev,
  deck attached, beautiful HTML. No drafts - it actually sends.

  Usage:
    powershell -ExecutionPolicy Bypass -File .\Send-Meddpicc.ps1 -Mode test
    powershell -ExecutionPolicy Bypass -File .\Send-Meddpicc.ps1 -Mode monday
    powershell -ExecutionPolicy Bypass -File .\Send-Meddpicc.ps1 -Mode friday
#>
param([ValidateSet('monday','friday','test')][string]$Mode = 'test')
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

# ---------------- CONFIG ----------------
$Sender     = 'feranicus@s4biz.io'
$ReplyTo    = 'jevgenijs.vainsteins@colt.net'
$SenderName = 'Jev Vainsteins (Colt)'
$CC         = @('Stephan.Wanke@colt.net','Alexander.Kress@colt.net','Jevgenijs.Vainsteins@colt.net')
$Attachment = 'C:\Users\feran\Downloads\Richard Account review\Stephan_Security_Report_09Jul2026_v2.pptx'
$TestEmail  = 'evgeny@s4biz.io'
$GoLive     = $true    # $false = Monday/Friday runs go only to $TestEmail

# Gmail App Password: put it (one line) in app_password.txt next to this script. Keep it private.
$pwPath = Join-Path $here 'app_password.txt'
if (-not (Test-Path $pwPath)) { throw "Missing app_password.txt - see README_PowerShell.md (Gmail App Password)." }
$AppPassword = (Get-Content $pwPath -Raw).Trim()

# ---------------- RECIPIENTS (37) ----------------
$Recipients = @(
 @{first='Andreas';     email='Andreas.Raus@colt.net'},
 @{first='Florian';     email='Florian.Stumpf@colt.net'},
 @{first='Erik';        email='Erik.Bartha@colt.net'},
 @{first='Christoph';   email='Christoph.Rossa@colt.net'},
 @{first='Kerstin';     email='Kerstin.Mahr@colt.net'},
 @{first='Guenther';    email='Guenther.Frank@colt.net'},
 @{first='Birgit';      email='Birgit.Schmidt@colt.net'},
 @{first='Ulrich';      email='Ulrich.Pawlick@colt.net'},
 @{first='Dagmar';      email='Dagmar.Fergin-Cham@colt.net'},
 @{first='Yasemin';     email='Yasemin.Degirmenci@colt.net'},
 @{first='Ingo';        email='Ingo.Ronsdorf@colt.net'},
 @{first='Naim';        email='Naim.Buelbuel@colt.net'},
 @{first='Joscha';      email='Joscha.Brandt@colt.net'},
 @{first='Massimiliano';email='massimiliano.meneguz@colt.net'},
 @{first='Thorsten';    email='Thorsten.Jacobsen@colt.net'},
 @{first='Marion';      email='Marion.Norde2@colt.net'},
 @{first='Sebastian';   email='Sebastian.Doebus@colt.net'},
 @{first='Karin';       email='Karin.Lenz@colt.net'},
 @{first='Andreas';     email='Andreas.Wuthenow@colt.net'},
 @{first='Daniel';      email='Daniel.Eberhardt@colt.net'},
 @{first='Bennet';      email='bennet.lahde@colt.net'},
 @{first='Matthias';    email='Matthias.Vogler@colt.net'},
 @{first='Adis';        email='adis.kadiric@colt.net'},
 @{first='Marcos';      email='Marcos.Moreno@colt.net'},
 @{first='Pierre';      email='Pierre.Mattenberger@colt.net'},
 @{first='Beat';        email='Beat.Suter@colt.net'},
 @{first='Carmelo';     email='Carmelo.Scalone@colt.net'},
 @{first='Armin';       email='armin.hall@colt.net'},
 @{first='Klaus-Peter'; email='Klaus-Peter.Liebig@colt.net'},
 @{first='Christopher'; email='Christopher.Rosengart@colt.net'},
 @{first='Ben';         email='Ben.Krause@colt.net'},
 @{first='Niclas';      email='Niclas.Prusko@colt.net'},
 @{first='Stefan';      email='Stefan.Risch@colt.net'},
 @{first='Rames';       email='Rames.Grosskopf@colt.net'},
 @{first='Abdussamed';  email='Abdussamed.Kuru@colt.net'},
 @{first='Thy Mai';     email='Thymai.Nguyen@colt.net'},
 @{first='Stefan';      email='Stefan.Wuerfel@colt.net'}
)

# ---------------- HTML ----------------
function Get-Html([string]$first, [string]$mode) {
  $replyBox = @"
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:8px 0 20px;"><tr>
<td style="background:#e8f6f5;border-left:4px solid #00A9A5;border-radius:6px;padding:14px 18px;color:#0a4b49;font-size:15px;">
<b>Just hit &ldquo;Reply&rdquo;</b> &mdash; your answer comes straight to me at
<a href="mailto:jevgenijs.vainsteins@colt.net" style="color:#007A78;font-weight:bold;text-decoration:none;">jevgenijs.vainsteins@colt.net</a>.
</td></tr></table>
"@
  if ($mode -eq 'friday') {
    $inner = @"
<p style="margin:0 0 16px;">Hi $first,</p>
<p style="margin:0 0 16px;">Quick end-of-week check-in for <b>MEDDPICC STEP UP</b>.</p>
$replyBox
<p style="margin:18px 0 6px;color:#007A78;font-size:13px;font-weight:bold;letter-spacing:1.5px;">PLEASE REPLY WITH</p>
<table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 0 16px;color:#222;font-size:15px;line-height:1.5;">
<tr><td style="padding:3px 10px 3px 0;color:#00A9A5;font-weight:bold;">&bull;</td><td>What moved this week on your July/August security deals (DDoS &middot; SD-WAN &middot; SASE)?</td></tr>
<tr><td style="padding:3px 10px 3px 0;color:#00A9A5;font-weight:bold;">&bull;</td><td>Any new blockers?</td></tr>
<tr><td style="padding:3px 10px 3px 0;color:#00A9A5;font-weight:bold;">&bull;</td><td>Where do you need my help to push it to close &mdash; assessment, C-BIQ, exec sponsor, pricing, Fortinet/partner motion?</td></tr></table>
<p style="margin:0 0 4px;">Thanks, and have a good weekend.</p>
"@
  } else {
    $inner = @"
<p style="margin:0 0 16px;">Hi $first,</p>
<p style="margin:0 0 16px;">I&rsquo;m kicking off a short program &mdash; <b>MEDDPICC STEP UP</b> &mdash; to help us win more of the DACH security pipeline as a team.</p>
<p style="margin:18px 0 6px;color:#007A78;font-size:13px;font-weight:bold;letter-spacing:1.5px;">WHAT IT IS</p>
<p style="margin:0 0 16px;">Twice a week &mdash; every <b>Monday &amp; Friday</b> &mdash; I&rsquo;ll ask you for a quick status on the opportunities you think can close in <b>July&ndash;August</b> with a security angle: <b>DDoS, SD-WAN, SASE</b>, or anything security-adjacent. I&rsquo;ll then help you sharpen the MEDDPICC qualification and position Colt to close.</p>
<p style="margin:18px 0 6px;color:#007A78;font-size:13px;font-weight:bold;letter-spacing:1.5px;">WHY</p>
<p style="margin:0 0 8px;">Security is where we&rsquo;re most differentiated right now. This isn&rsquo;t a reporting chore &mdash; it&rsquo;s hands-on help: security assessment, C-BIQ risk report, competitive angle, exec sponsor, pricing, and joint Fortinet/partner motions.</p>
$replyBox
<p style="margin:18px 0 6px;color:#007A78;font-size:13px;font-weight:bold;letter-spacing:1.5px;">WHAT I NEED &mdash; PER OPPORTUNITY</p>
<table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 0 16px;color:#222;font-size:15px;line-height:1.5;">
<tr><td style="padding:3px 10px 3px 0;color:#00A9A5;font-weight:bold;">1.</td><td>Account &amp; project, and lifecycle stage (Qualify &rarr; Proposal &rarr; Negotiation &rarr; Close)</td></tr>
<tr><td style="padding:3px 10px 3px 0;color:#00A9A5;font-weight:bold;">2.</td><td>Expected close month and value</td></tr>
<tr><td style="padding:3px 10px 3px 0;color:#00A9A5;font-weight:bold;">3.</td><td>The single biggest blocker</td></tr>
<tr><td style="padding:3px 10px 3px 0;color:#00A9A5;font-weight:bold;">4.</td><td>How I can help you better position Colt in that account</td></tr></table>
<p style="margin:18px 0 6px;color:#007A78;font-size:13px;font-weight:bold;letter-spacing:1.5px;">WHAT YOU&rsquo;LL GET BACK</p>
<p style="margin:0 0 18px;">A per-project security view &mdash; <b>2 slides per project</b> (status, risks, MEDDPICC snapshot, next steps). An example is <b>attached</b>. Once you reply, we build the same for your projects and keep it updated weekly.</p>
<p style="margin:0 0 4px;">Let&rsquo;s step it up.</p>
"@
  }
  return @"
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f6;margin:0;padding:24px 0;font-family:Arial,Helvetica,sans-serif;"><tr><td align="center">
<table role="presentation" width="620" cellpadding="0" cellspacing="0" style="width:620px;max-width:92%;background:#ffffff;border-radius:10px;overflow:hidden;">
<tr><td style="background:#007A78;padding:26px 34px;">
<div style="color:#fff;font-size:13px;letter-spacing:3px;font-weight:bold;opacity:.85;">COLT &middot; DACH SECURITY</div>
<div style="color:#fff;font-size:28px;font-weight:bold;margin-top:6px;">MEDDPICC STEP&nbsp;UP</div>
<div style="color:#bdeceb;font-size:15px;margin-top:6px;">Winning your July&ndash;August security deals, together</div></td></tr>
<tr><td style="padding:28px 34px 6px 34px;color:#222;font-size:15px;line-height:1.6;">$inner</td></tr>
<tr><td style="padding:6px 34px 26px 34px;border-top:1px solid #eee;">
<div style="font-size:15px;color:#222;margin-top:16px;"><b>Jev Vainsteins</b></div>
<div style="font-size:13px;color:#555;">Client Partner (CP), DACH &mdash; Security</div>
<div style="font-size:13px;color:#007A78;font-weight:bold;">Colt Technology Services</div>
<div style="font-size:13px;"><a href="mailto:jevgenijs.vainsteins@colt.net" style="color:#007A78;text-decoration:none;">jevgenijs.vainsteins@colt.net</a></div></td></tr>
</table></td></tr></table>
"@
}

# ---------------- SEND ----------------
function Send-One([string]$first, [string]$to, [string]$mode) {
  $subject = if ($mode -eq 'friday') { 'MEDDPICC STEP UP - end-of-week status (July/August security deals)' }
             else { 'MEDDPICC STEP UP - your July/August security deals (DDoS / SD-WAN / SASE)' }
  $mail = New-Object System.Net.Mail.MailMessage
  $mail.From = New-Object System.Net.Mail.MailAddress($Sender, $SenderName)
  $mail.To.Add($to)
  foreach ($c in $CC) { $mail.CC.Add($c) }
  $mail.ReplyToList.Add($ReplyTo)        # <-- Reply goes to your Colt address
  $mail.Subject    = $subject
  $mail.Body       = (Get-Html $first $mode)
  $mail.IsBodyHtml = $true
  if ($mode -ne 'friday' -and (Test-Path $Attachment)) {
    $mail.Attachments.Add((New-Object System.Net.Mail.Attachment($Attachment)))
  }
  $smtp = New-Object System.Net.Mail.SmtpClient('smtp.gmail.com', 587)
  $smtp.EnableSsl   = $true
  $smtp.Credentials = New-Object System.Net.NetworkCredential($Sender, $AppPassword)
  $smtp.Send($mail)
  $mail.Dispose()
  Write-Host "sent -> $to"
}

if ($Mode -eq 'test') {
  Send-One 'Evgeny' $TestEmail 'monday'
  Write-Host "Test sent to $TestEmail. Open it and hit Reply - it must show $ReplyTo."
  return
}
$list = if ($GoLive) { $Recipients } else { @(@{first='Evgeny'; email=$TestEmail}) }
$ok = 0
foreach ($r in $list) {
  try { Send-One $r.first $r.email $Mode; $ok++ } catch { Write-Warning "FAILED $($r.email): $_" }
  Start-Sleep -Milliseconds 400
}
Write-Host "Done. Sent $ok of $($list.Count) ($Mode)."
