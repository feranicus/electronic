#!/usr/bin/env python3
"""
MEDDPICC STEP UP - sends individual emails to each AE via the Gmail API.
From feranicus@s4biz.io, Reply-To jevgenijs.vainsteins@colt.net, CC Stephan/Alex/Jev,
deck attached, beautiful HTML. Fully automatic (no drafts).

Usage:  python send.py [monday|friday|test]
Auth:   OAuth token at $TOKEN_FILE (default /secrets/token.json), scope gmail.send.
"""
import base64, json, mimetypes, os, sys, time, pathlib
from email.message import EmailMessage
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES      = ["https://www.googleapis.com/auth/gmail.send"]
TOKEN_FILE  = os.environ.get("TOKEN_FILE", "/secrets/token.json")
SENDER      = os.environ.get("SENDER", "feranicus@s4biz.io")
SENDER_NAME = os.environ.get("SENDER_NAME", "Jev Vainsteins (Colt)")
REPLY_TO    = os.environ.get("REPLY_TO", "jevgenijs.vainsteins@colt.net")
CC          = os.environ.get("CC", "Stephan.Wanke@colt.net,Alexander.Kress@colt.net,Jevgenijs.Vainsteins@colt.net")
ATTACHMENT  = os.environ.get("ATTACHMENT", "/data/Stephan_Security_Report_09Jul2026_v2.pptx")
RECIPIENTS_FILE = os.environ.get("RECIPIENTS_FILE", "/app/recipients.json")
GO_LIVE     = os.environ.get("GO_LIVE", "true").lower() == "true"
TEST_EMAIL  = os.environ.get("TEST_EMAIL", "evgeny@s4biz.io")


def service():
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds.valid and creds.refresh_token:
        creds.refresh(Request())
        pathlib.Path(TOKEN_FILE).write_text(creds.to_json())
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def reply_box():
    return (
    '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:8px 0 20px;"><tr>'
    '<td style="background:#e8f6f5;border-left:4px solid #00A9A5;border-radius:6px;padding:14px 18px;color:#0a4b49;font-size:15px;">'
    '<b>Just hit &ldquo;Reply&rdquo;</b> &mdash; your answer comes straight to me at '
    '<a href="mailto:jevgenijs.vainsteins@colt.net" style="color:#007A78;font-weight:bold;text-decoration:none;">jevgenijs.vainsteins@colt.net</a>.'
    '</td></tr></table>')


def html(first, mode):
    h = lambda t: f'<p style="margin:18px 0 6px;color:#007A78;font-size:13px;font-weight:bold;letter-spacing:1.5px;">{t}</p>'
    if mode == "friday":
        inner = (
            f'<p style="margin:0 0 16px;">Hi {first},</p>'
            '<p style="margin:0 0 16px;">Quick end-of-week check-in for <b>MEDDPICC STEP UP</b>.</p>'
            + reply_box() + h("PLEASE REPLY WITH") +
            '<table cellpadding="0" cellspacing="0" style="margin:0 0 16px;color:#222;font-size:15px;line-height:1.5;">'
            '<tr><td style="padding:3px 10px 3px 0;color:#00A9A5;font-weight:bold;">&bull;</td><td>What moved this week on your July/August security deals (DDoS &middot; SD-WAN &middot; SASE)?</td></tr>'
            '<tr><td style="padding:3px 10px 3px 0;color:#00A9A5;font-weight:bold;">&bull;</td><td>Any new blockers?</td></tr>'
            '<tr><td style="padding:3px 10px 3px 0;color:#00A9A5;font-weight:bold;">&bull;</td><td>Where do you need my help to close &mdash; assessment, C-BIQ, exec sponsor, pricing, Fortinet/partner motion?</td></tr></table>'
            '<p style="margin:0 0 4px;">Thanks, and have a good weekend.</p>')
    else:
        inner = (
            f'<p style="margin:0 0 16px;">Hi {first},</p>'
            '<p style="margin:0 0 16px;">I&rsquo;m kicking off a short program &mdash; <b>MEDDPICC STEP UP</b> &mdash; to help us win more of the DACH security pipeline as a team.</p>'
            + h("WHAT IT IS") +
            '<p style="margin:0 0 16px;">Twice a week &mdash; every <b>Monday &amp; Friday</b> &mdash; I&rsquo;ll ask you for a quick status on the opportunities you think can close in <b>July&ndash;August</b> with a security angle: <b>DDoS, SD-WAN, SASE</b>, or anything security-adjacent. I&rsquo;ll then help you sharpen the MEDDPICC qualification and position Colt to close.</p>'
            + h("WHY") +
            '<p style="margin:0 0 8px;">Security is where we&rsquo;re most differentiated right now. This isn&rsquo;t a reporting chore &mdash; it&rsquo;s hands-on help: security assessment, C-BIQ risk report, competitive angle, exec sponsor, pricing, and joint Fortinet/partner motions.</p>'
            + reply_box() + h("WHAT I NEED &mdash; PER OPPORTUNITY") +
            '<table cellpadding="0" cellspacing="0" style="margin:0 0 16px;color:#222;font-size:15px;line-height:1.5;">'
            '<tr><td style="padding:3px 10px 3px 0;color:#00A9A5;font-weight:bold;">1.</td><td>Account &amp; project, and lifecycle stage (Qualify &rarr; Proposal &rarr; Negotiation &rarr; Close)</td></tr>'
            '<tr><td style="padding:3px 10px 3px 0;color:#00A9A5;font-weight:bold;">2.</td><td>Expected close month and value</td></tr>'
            '<tr><td style="padding:3px 10px 3px 0;color:#00A9A5;font-weight:bold;">3.</td><td>The single biggest blocker</td></tr>'
            '<tr><td style="padding:3px 10px 3px 0;color:#00A9A5;font-weight:bold;">4.</td><td>How I can help you better position Colt in that account</td></tr></table>'
            + h("WHAT YOU&rsquo;LL GET BACK") +
            '<p style="margin:0 0 18px;">A per-project security view &mdash; <b>2 slides per project</b> (status, risks, MEDDPICC snapshot, next steps). An example is <b>attached</b>. Once you reply, we build the same for your projects, updated weekly.</p>'
            '<p style="margin:0 0 4px;">Let&rsquo;s step it up.</p>')
    return (
        '<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f6;margin:0;padding:24px 0;font-family:Arial,Helvetica,sans-serif;"><tr><td align="center">'
        '<table width="620" cellpadding="0" cellspacing="0" style="width:620px;max-width:92%;background:#fff;border-radius:10px;overflow:hidden;">'
        '<tr><td style="background:#007A78;padding:26px 34px;">'
        '<div style="color:#fff;font-size:13px;letter-spacing:3px;font-weight:bold;opacity:.85;">COLT &middot; DACH SECURITY</div>'
        '<div style="color:#fff;font-size:28px;font-weight:bold;margin-top:6px;">MEDDPICC STEP&nbsp;UP</div>'
        '<div style="color:#bdeceb;font-size:15px;margin-top:6px;">Winning your July&ndash;August security deals, together</div></td></tr>'
        f'<tr><td style="padding:28px 34px 6px 34px;color:#222;font-size:15px;line-height:1.6;">{inner}</td></tr>'
        '<tr><td style="padding:6px 34px 26px 34px;border-top:1px solid #eee;">'
        '<div style="font-size:15px;color:#222;margin-top:16px;"><b>Jev Vainsteins</b></div>'
        '<div style="font-size:13px;color:#555;">Client Partner (CP), DACH &mdash; Security</div>'
        '<div style="font-size:13px;color:#007A78;font-weight:bold;">Colt Technology Services</div>'
        '<div style="font-size:13px;"><a href="mailto:jevgenijs.vainsteins@colt.net" style="color:#007A78;text-decoration:none;">jevgenijs.vainsteins@colt.net</a></div>'
        '</td></tr></table></td></tr></table>')


def build_message(first, to, mode):
    subject = ("MEDDPICC STEP UP - end-of-week status (July/August security deals)"
               if mode == "friday" else
               "MEDDPICC STEP UP - your July/August security deals (DDoS / SD-WAN / SASE)")
    msg = EmailMessage()
    msg["From"] = f"{SENDER_NAME} <{SENDER}>"
    msg["To"] = to
    msg["Cc"] = CC
    msg["Reply-To"] = REPLY_TO
    msg["Subject"] = subject
    msg.set_content("Please view this email in an HTML-capable client.")
    msg.add_alternative(html(first, mode), subtype="html")
    if mode != "friday" and os.path.exists(ATTACHMENT):
        ctype, _ = mimetypes.guess_type(ATTACHMENT)
        maintype, subtype = (ctype or "application/octet-stream").split("/", 1)
        with open(ATTACHMENT, "rb") as f:
            msg.add_attachment(f.read(), maintype=maintype, subtype=subtype,
                               filename=os.path.basename(ATTACHMENT))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    return {"raw": raw}


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "test"
    svc = service()
    if mode == "test":
        svc.users().messages().send(userId="me", body=build_message("Evgeny", TEST_EMAIL, "monday")).execute()
        print(f"Test sent to {TEST_EMAIL}. Reply must show {REPLY_TO}.")
        return
    recips = json.loads(pathlib.Path(RECIPIENTS_FILE).read_text())
    if not GO_LIVE:
        recips = [{"first": "Evgeny", "email": TEST_EMAIL}]
    ok = 0
    for r in recips:
        try:
            svc.users().messages().send(userId="me", body=build_message(r["first"], r["email"], mode)).execute()
            print("sent ->", r["email"]); ok += 1
        except Exception as e:  # noqa: BLE001
            print("FAILED", r["email"], e)
        time.sleep(0.4)
    print(f"Done. Sent {ok}/{len(recips)} ({mode}).")


if __name__ == "__main__":
    main()
