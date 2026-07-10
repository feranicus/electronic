/*  MEDDPICC STEP UP — auto-send from your s4biz Google account
 *  Sends INDIVIDUAL emails to each AE, Reply-To = your Colt address, CC Stephan/Alex/Jev,
 *  with the example deck attached, automatically every Monday & Friday.
 *
 *  SETUP (once):
 *   1. script.google.com -> New project -> paste this file.
 *   2. Upload the deck to your Google Drive (any folder); keep the exact name in ATTACHMENT_NAME.
 *   3. Project Settings (gear) -> set Time zone to (GMT+01:00) Berlin.
 *   4. Run sendTest() once -> approve the permission prompt -> check evgeny@s4biz.io + the Reply button.
 *   5. Run setupTriggers() once -> it schedules Monday & Friday 09:00 automatically.
 *  That's it. To go live to the whole team, leave GO_LIVE = true.
 */

// ---------- CONFIG ----------
var REPLY_TO        = 'jevgenijs.vainsteins@colt.net';
var CC              = 'Stephan.Wanke@colt.net,Alexander.Kress@colt.net,Jevgenijs.Vainsteins@colt.net';
var SENDER_NAME     = 'Jev Vainsteins (Colt)';
var ATTACHMENT_NAME = 'Stephan_Security_Report_09Jul2026_v2.pptx';  // must exist in your Google Drive
var SEND_HOUR       = 9;      // 09:00 local (set project time zone to Berlin)
var GO_LIVE         = true;   // true = send to all AEs; false = send only to TEST_EMAIL
var TEST_EMAIL      = 'evgeny@s4biz.io';

// ---------- RECIPIENTS (37 AEs) ----------
var RECIPIENTS = [
  {first:'Andreas',     email:'Andreas.Raus@colt.net'},
  {first:'Florian',     email:'Florian.Stumpf@colt.net'},
  {first:'Erik',        email:'Erik.Bartha@colt.net'},
  {first:'Christoph',   email:'Christoph.Rossa@colt.net'},
  {first:'Kerstin',     email:'Kerstin.Mahr@colt.net'},
  {first:'Guenther',    email:'Guenther.Frank@colt.net'},
  {first:'Birgit',      email:'Birgit.Schmidt@colt.net'},
  {first:'Ulrich',      email:'Ulrich.Pawlick@colt.net'},
  {first:'Dagmar',      email:'Dagmar.Fergin-Cham@colt.net'},
  {first:'Yasemin',     email:'Yasemin.Degirmenci@colt.net'},
  {first:'Ingo',        email:'Ingo.Ronsdorf@colt.net'},
  {first:'Naim',        email:'Naim.Buelbuel@colt.net'},
  {first:'Joscha',      email:'Joscha.Brandt@colt.net'},
  {first:'Massimiliano',email:'massimiliano.meneguz@colt.net'},
  {first:'Thorsten',    email:'Thorsten.Jacobsen@colt.net'},
  {first:'Marion',      email:'Marion.Norde2@colt.net'},
  {first:'Sebastian',   email:'Sebastian.Doebus@colt.net'},
  {first:'Karin',       email:'Karin.Lenz@colt.net'},
  {first:'Andreas',     email:'Andreas.Wuthenow@colt.net'},
  {first:'Daniel',      email:'Daniel.Eberhardt@colt.net'},
  {first:'Bennet',      email:'bennet.lahde@colt.net'},
  {first:'Matthias',    email:'Matthias.Vogler@colt.net'},
  {first:'Adis',        email:'adis.kadiric@colt.net'},
  {first:'Marcos',      email:'Marcos.Moreno@colt.net'},
  {first:'Pierre',      email:'Pierre.Mattenberger@colt.net'},
  {first:'Beat',        email:'Beat.Suter@colt.net'},
  {first:'Carmelo',     email:'Carmelo.Scalone@colt.net'},
  {first:'Armin',       email:'armin.hall@colt.net'},
  {first:'Klaus-Peter', email:'Klaus-Peter.Liebig@colt.net'},
  {first:'Christopher', email:'Christopher.Rosengart@colt.net'},
  {first:'Ben',         email:'Ben.Krause@colt.net'},
  {first:'Niclas',      email:'Niclas.Prusko@colt.net'},
  {first:'Stefan',      email:'Stefan.Risch@colt.net'},
  {first:'Rames',       email:'Rames.Grosskopf@colt.net'},
  {first:'Abdussamed',  email:'Abdussamed.Kuru@colt.net'},
  {first:'Thy Mai',     email:'Thymai.Nguyen@colt.net'},
  {first:'Stefan',      email:'Stefan.Wuerfel@colt.net'}
];

// ---------- ENTRY POINTS ----------
function sendMonday(){ runBatch('monday'); }
function sendFriday(){ runBatch('friday'); }
function sendTest(){ sendOne({first:'Evgeny', email:TEST_EMAIL}, 'monday'); }

function runBatch(kind){
  var list = GO_LIVE ? RECIPIENTS : [{first:'Evgeny', email:TEST_EMAIL}];
  list.forEach(function(r){ sendOne(r, kind); Utilities.sleep(400); });
}

function sendOne(r, kind){
  var isFri  = (kind === 'friday');
  var subject = isFri
    ? 'MEDDPICC STEP UP — end-of-week status (July/August security deals)'
    : 'MEDDPICC STEP UP — your July/August security deals (DDoS · SD-WAN · SASE)';
  var opts = {
    htmlBody: isFri ? htmlFriday(r.first) : htmlMonday(r.first),
    replyTo:  REPLY_TO,
    cc:       CC,
    name:     SENDER_NAME,
    attachments: isFri ? [] : getAttachment()
  };
  GmailApp.sendEmail(r.email, subject, 'Please view this email in an HTML-capable client.', opts);
}

function getAttachment(){
  var it = DriveApp.getFilesByName(ATTACHMENT_NAME);
  return it.hasNext() ? [it.next().getBlob()] : [];  // silently skips if not found
}

// ---------- SCHEDULING ----------
function setupTriggers(){
  ScriptApp.getProjectTriggers().forEach(function(t){ ScriptApp.deleteTrigger(t); });
  ScriptApp.newTrigger('sendMonday').timeBased().onWeekDay(ScriptApp.WeekDay.MONDAY).atHour(SEND_HOUR).nearMinute(0).create();
  ScriptApp.newTrigger('sendFriday').timeBased().onWeekDay(ScriptApp.WeekDay.FRIDAY).atHour(SEND_HOUR).nearMinute(0).create();
  Logger.log('Triggers set: Monday & Friday at ' + SEND_HOUR + ':00 (project time zone).');
}

// ---------- EMAIL HTML ----------
function shell_(inner){
  return '' +
  '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f6;margin:0;padding:24px 0;font-family:Arial,Helvetica,sans-serif;"><tr><td align="center">' +
  '<table role="presentation" width="620" cellpadding="0" cellspacing="0" style="width:620px;max-width:92%;background:#ffffff;border-radius:10px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.08);">' +
  '<tr><td style="background:#007A78;padding:26px 34px;">' +
  '<div style="color:#fff;font-size:13px;letter-spacing:3px;font-weight:bold;opacity:.85;">COLT · DACH SECURITY</div>' +
  '<div style="color:#fff;font-size:28px;font-weight:bold;margin-top:6px;">MEDDPICC STEP&nbsp;UP</div>' +
  '<div style="color:#bdeceb;font-size:15px;margin-top:6px;">Winning your July–August security deals, together</div></td></tr>' +
  '<tr><td style="padding:28px 34px 6px 34px;color:#222;font-size:15px;line-height:1.6;">' + inner + '</td></tr>' +
  '<tr><td style="padding:6px 34px 26px 34px;border-top:1px solid #eee;">' +
  '<div style="font-size:15px;color:#222;margin-top:16px;"><b>Jev Vainsteins</b></div>' +
  '<div style="font-size:13px;color:#555;">Client Partner (CP), DACH — Security</div>' +
  '<div style="font-size:13px;color:#007A78;font-weight:bold;">Colt Technology Services</div>' +
  '<div style="font-size:13px;"><a href="mailto:jevgenijs.vainsteins@colt.net" style="color:#007A78;text-decoration:none;">jevgenijs.vainsteins@colt.net</a></div></td></tr>' +
  '</table></td></tr></table>';
}

function replyBox_(){
  return '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:8px 0 20px;"><tr>' +
  '<td style="background:#e8f6f5;border-left:4px solid #00A9A5;border-radius:6px;padding:14px 18px;color:#0a4b49;font-size:15px;">' +
  '<b>Just hit “Reply”</b> — your answer comes straight to me at ' +
  '<a href="mailto:jevgenijs.vainsteins@colt.net" style="color:#007A78;font-weight:bold;text-decoration:none;">jevgenijs.vainsteins@colt.net</a>.</td></tr></table>';
}
function h_(t){ return '<p style="margin:18px 0 6px;color:#007A78;font-size:13px;font-weight:bold;letter-spacing:1.5px;">' + t + '</p>'; }

function htmlMonday(first){
  var inner =
    '<p style="margin:0 0 16px;">Hi ' + first + ',</p>' +
    '<p style="margin:0 0 16px;">I’m kicking off a short program — <b>MEDDPICC STEP UP</b> — to help us win more of the DACH security pipeline as a team.</p>' +
    h_('WHAT IT IS') +
    '<p style="margin:0 0 16px;">Twice a week — every <b>Monday &amp; Friday</b> — I’ll ask you for a quick status on the opportunities you think can close in <b>July–August</b> with a security angle: <b>DDoS, SD-WAN, SASE</b>, or anything security-adjacent. Based on what you send, I’ll help you sharpen the MEDDPICC qualification and position Colt to close.</p>' +
    h_('WHY') +
    '<p style="margin:0 0 8px;">Security is where we’re most differentiated right now. This isn’t a reporting chore — it’s hands-on help: security assessment, C-BIQ risk report, competitive angle, exec sponsor, pricing, and joint Fortinet/partner motions.</p>' +
    replyBox_() +
    h_('WHAT I NEED — PER OPPORTUNITY') +
    '<table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 0 16px;color:#222;font-size:15px;line-height:1.5;">' +
    '<tr><td style="padding:3px 10px 3px 0;color:#00A9A5;font-weight:bold;">1.</td><td>Account &amp; project, and lifecycle stage (Qualify → Proposal → Negotiation → Close)</td></tr>' +
    '<tr><td style="padding:3px 10px 3px 0;color:#00A9A5;font-weight:bold;">2.</td><td>Expected close month and value</td></tr>' +
    '<tr><td style="padding:3px 10px 3px 0;color:#00A9A5;font-weight:bold;">3.</td><td>The single biggest blocker</td></tr>' +
    '<tr><td style="padding:3px 10px 3px 0;color:#00A9A5;font-weight:bold;">4.</td><td>How I can help you better position Colt in that account</td></tr></table>' +
    h_('WHAT YOU’LL GET BACK') +
    '<p style="margin:0 0 18px;">A per-project security view — <b>2 slides per project</b> (status, risks, MEDDPICC snapshot, next steps). An example is <b>attached</b>. Once you reply, we build the same for your projects and keep it updated weekly, with individual follow-up.</p>' +
    '<p style="margin:0 0 4px;">Let’s step it up.</p>';
  return shell_(inner);
}

function htmlFriday(first){
  var inner =
    '<p style="margin:0 0 16px;">Hi ' + first + ',</p>' +
    '<p style="margin:0 0 16px;">Quick end-of-week check-in for <b>MEDDPICC STEP UP</b>.</p>' +
    replyBox_() +
    h_('PLEASE REPLY WITH') +
    '<table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 0 16px;color:#222;font-size:15px;line-height:1.5;">' +
    '<tr><td style="padding:3px 10px 3px 0;color:#00A9A5;font-weight:bold;">•</td><td>What moved this week on your July/August security deals (DDoS · SD-WAN · SASE)?</td></tr>' +
    '<tr><td style="padding:3px 10px 3px 0;color:#00A9A5;font-weight:bold;">•</td><td>Any new blockers?</td></tr>' +
    '<tr><td style="padding:3px 10px 3px 0;color:#00A9A5;font-weight:bold;">•</td><td>Where do you need my help to push it to close — assessment, C-BIQ, exec sponsor, pricing, Fortinet/partner motion?</td></tr></table>' +
    '<p style="margin:0 0 4px;">Thanks, and have a good weekend.</p>';
  return shell_(inner);
}
