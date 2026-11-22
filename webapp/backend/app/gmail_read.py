"""gmail_read.py — READING the Workspace mailboxes, through the door this app already opens.

    python -m app.gmail_read        the self-test, and `status()` in words

HOW, AND WHY THIS IS THE RIGHT MECHANISM HERE.
    `notify.email()` already talks to the Gmail API with a SERVICE ACCOUNT that has DOMAIN-WIDE
    DELEGATION, impersonating GMAIL_SENDER with scope `gmail.send` - that is how the one-time
    sign-in codes go out. Reading is the SAME mechanism with one more scope. So there is no second
    auth system, no OAuth consent screen, no refresh token to store and rotate, and no "sign in
    with Google" round trip for a server that has no browser.

    THE ONE IRREDUCIBLE HUMAN STEP is in the Workspace admin console, because only a domain admin
    can grant it:
        Security -> Access and data control -> API controls -> Domain-wide delegation
        -> the EXISTING client id -> add https://www.googleapis.com/auth/gmail.readonly
    Until that is done this module reports exactly that and reads nothing. It is the same shape as
    every other credential in this estate: minted once by the account owner, automated afterwards.

    READONLY, DELIBERATELY. `gmail.modify` would let this code label, archive and delete mail in a
    real person's mailbox. Nothing here needs that, and a bug in a correlation engine must not be
    able to touch a message. If labelling is ever wanted it is a separate decision with its own
    scope and its own argument.

WHOSE MAILBOX. `PIPELINE_MAILBOXES` is a comma-separated list, because the point of this feature is
    that Dima's mail reaches the board as well as the shared one - "for example Dima from his email
    to classify and add emails to specific deals". Each address is impersonated separately with its
    own token, so one mailbox being refused does not silence the others, and the mailbox a message
    came from is recorded on the row.

WHY POLLING AND NOT PUSH. Gmail's watch/Pub-Sub delivers in seconds and needs a public endpoint, a
    Pub/Sub topic, a subscription and a verified push URL - new infrastructure and new attack
    surface for a board where a few minutes costs nothing. `users.messages.list` with a query and a
    bounded window is one HTTPS call with no moving parts and nothing anyone can replay at us.

EVERY NETWORK CALL GOES THROUGH ONE INJECTED `fetch`, so the suite exercises the real parsing and
the real bounds with no token and no socket.

PORTED from jobhuntwow's module of the same name; `_http`, `_header`, `_body_text` and
`parse_message` are reused verbatim - that is the half that was hard to get right (a payload can be
an int, HTML-only senders must not be dropped) and it has nothing to do with either domain.
"""
import base64
import json
import os
import re
import time

SA_B64 = os.environ.get("GMAIL_SA_B64", "")
SENDER = os.environ.get("GMAIL_SENDER", "")
SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
API = "https://gmail.googleapis.com/gmail/v1/users/%s"
# Narrow on purpose. This reads a business mailbox looking for partner correspondence, not a life:
# chats, drafts, our own sent mail, promotions and social never enter the pipeline.
DEFAULT_QUERY = os.environ.get(
    "PIPELINE_MAIL_QUERY",
    "-in:chats -in:drafts -from:me -category:promotions -category:social")
MAX_MESSAGES = int(os.environ.get("PIPELINE_MAIL_MAX", "60"))
BODY_CHARS = int(os.environ.get("PIPELINE_MAIL_BODY_CHARS", "4000"))
LOOKBACK_DAYS = int(os.environ.get("PIPELINE_MAIL_LOOKBACK_DAYS", "14"))


def mailboxes():
    """Which addresses to read. Defaults to the sending identity alone, so switching the feature
    on without naming anybody reads only the mailbox this app already owns."""
    raw = os.environ.get("PIPELINE_MAILBOXES", "") or SENDER
    return [a.strip().lower() for a in str(raw).replace(";", ",").split(",") if a.strip()]


def enabled():
    return os.environ.get("PIPELINE_MAIL_READ", "").lower() in ("1", "true", "yes", "on")


def configured():
    """Reading is OPT-IN. A feature that reads somebody's mailbox does not default to on, and
    `if <derived thing>:` must never fail silently - status() says which half is missing."""
    return bool(SA_B64 and mailboxes() and enabled())


def status():
    """What an operator needs on the console: which half is missing, in words."""
    return {
        "enabled": enabled(),
        "mailboxes": mailboxes(),
        "credentials": bool(SA_B64),
        "scope": SCOPE,
        "query": DEFAULT_QUERY,
        "note": ("" if configured() else
                 "reading is off: set PIPELINE_MAIL_READ=1, name the mailboxes in "
                 "PIPELINE_MAILBOXES, and have a Workspace admin add gmail.readonly to the "
                 "existing service account's domain-wide delegation"),
    }


def _token(mailbox):
    """A bearer token for the READ scope, impersonating ONE mailbox. Same pattern as the send
    path, one scope different - so a token minted here can never send anything."""
    from google.auth.transport.requests import Request as GRequest
    from google.oauth2 import service_account
    info = json.loads(base64.b64decode(SA_B64))
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=[SCOPE], subject=mailbox)
    creds.refresh(GRequest())
    return creds.token


def _http(fetch=None):
    """The transport. Injected in tests; `requests` in production. One seam, so nothing else in
    this module knows whether a socket exists."""
    if fetch:
        return fetch

    def _real(url, headers=None, params=None, timeout=20):
        import requests
        r = requests.get(url, headers=headers or {}, params=params or {}, timeout=timeout)
        return r.status_code, (r.json() if r.content else {})
    return _real


def _header(payload, name) -> str:
    # A PAYLOAD IS WHATEVER THE API SENT, and a test just proved it can be an int. Shapes from
    # outside are not ours to assume (defect class 35) -- coerce, never trust.
    if not isinstance(payload, dict):
        return ""
    for h in (payload.get("headers") or []):
        if not isinstance(h, dict):
            continue
        if str(h.get("name", "")).lower() == name.lower():
            return str(h.get("value") or "")
    return ""


def _body_text(payload) -> str:
    """The plain text of a message, however the part tree is shaped. HTML is stripped rather than
    skipped: plenty of recruiters send HTML only, and dropping those would silently lose the half of
    the mailbox that matters most."""
    out, stack, seen = [], [payload if isinstance(payload, dict) else {}], 0
    while stack and seen < 40:
        p = stack.pop()
        seen += 1
        if not isinstance(p, dict):
            continue
        mime = str(p.get("mimeType") or "")
        data = ((p.get("body") or {}).get("data") or "")
        if data and mime.startswith("text/"):
            try:
                raw = base64.urlsafe_b64decode(data + "===").decode("utf-8", "replace")
            except Exception:
                raw = ""
            if mime == "text/html":
                raw = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
                raw = re.sub(r"(?s)<[^>]+>", " ", raw)
                raw = re.sub(r"&nbsp;?", " ", raw)
            out.append(raw)
        stack.extend(p.get("parts") or [])
    text = re.sub(r"[ \t ]+", " ", "\n".join(out))
    return re.sub(r"\n{3,}", "\n\n", text).strip()[:BODY_CHARS]


def parse_message(d: dict) -> dict:
    """One Gmail message resource -> the flat shape mailmatch and the UI use. Never raises."""
    d = d if isinstance(d, dict) else {}
    payload = d.get("payload")
    payload = payload if isinstance(payload, dict) else {}
    try:
        ts = int(d.get("internalDate") or 0) / 1000.0
    except Exception:
        ts = 0.0
    return {
        "id": str(d.get("id") or "")[:64],
        "thread_id": str(d.get("threadId") or "")[:64],
        "ts": ts,
        "from": _header(payload, "From")[:200],
        "to": _header(payload, "To")[:200],
        "reply_to": _header(payload, "Reply-To")[:200],
        "subject": _header(payload, "Subject")[:300],
        "snippet": str(d.get("snippet") or "")[:400],
        "body": _body_text(payload),
        "labels": [str(x)[:40] for x in (d.get("labelIds") or [])][:12],
    }


def fetch_mailbox(mailbox, days=None, query=None, limit=None, fetch=None, token=None):
    """(messages, note) for ONE mailbox. NEVER raises: a mail fault must not touch the board, and
    an empty list with a stated reason is an honest answer (absence of evidence is not a finding).
    """
    days = LOOKBACK_DAYS if days is None else int(days)
    limit = MAX_MESSAGES if limit is None else max(1, min(200, int(limit)))
    q = "%s newer_than:%dd" % (query or DEFAULT_QUERY, max(1, days))
    http = _http(fetch)
    try:
        tok = token or (_token(mailbox) if fetch is None else "test")
    except Exception as e:
        return [], "the mail credentials were refused for %s: %r" % (mailbox, e)
    hdr = {"Authorization": "Bearer %s" % tok}
    base = API % (mailbox or "me")
    try:
        code, data = http(base + "/messages", headers=hdr, params={"q": q, "maxResults": limit})
        if code != 200:
            return [], "Gmail list returned HTTP %s for %s" % (code, mailbox)
        ids = [m.get("id") for m in (data.get("messages") or []) if m.get("id")][:limit]
    except Exception as e:
        return [], "%s could not be listed: %r" % (mailbox, e)
    out = []
    for mid in ids:
        try:
            code, d = http("%s/messages/%s" % (base, mid), headers=hdr, params={"format": "full"})
            if code == 200:
                m = parse_message(d)
                m["mailbox"] = mailbox
                out.append(m)
        except Exception:
            continue              # one unreadable message must not lose the other fifty-nine
    return out, ("read %d of %d message(s) from %s" % (len(out), len(ids), mailbox)
                 if ids else "no new mail in %s" % mailbox)


def fetch_recent(days=None, query=None, limit=None, fetch=None):
    """(messages, notes[]) across EVERY configured mailbox. One mailbox being refused does not
    silence the others, and every note says which mailbox it is about (class 26)."""
    if not configured() and fetch is None:
        return [], [status()["note"] or "mail reading is not configured"]
    msgs, notes = [], []
    for mb in mailboxes():
        got, note = fetch_mailbox(mb, days=days, query=query, limit=limit, fetch=fetch)
        msgs.extend(got)
        notes.append(note)
    return msgs, notes


# --------------------------------------------------------------------------- self-test
def _selftest():
    fails = []

    def ck(name, cond, detail=""):
        print(("  ok   " if cond else "  FAIL ") + name + ((" - " + detail) if detail else ""))
        if not cond:
            fails.append(name)

    b64 = lambda s: base64.urlsafe_b64encode(s.encode()).decode()      # noqa: E731
    msg = {"id": "m1", "threadId": "t1", "internalDate": "1795000000000",
           "snippet": "hello", "labelIds": ["INBOX"],
           "payload": {"headers": [{"name": "From", "value": "Urs <ud@objectale.ch>"},
                                   {"name": "Subject", "value": "Re: MPA"},
                                   {"name": "To", "value": "jev@s4biz.io"}],
                       "mimeType": "multipart/alternative",
                       "parts": [{"mimeType": "text/html",
                                  "body": {"data": b64("<p>Signed &nbsp;<b>today</b></p>")}}]}}
    p = parse_message(msg)
    ck("headers are read", p["from"] == "Urs <ud@objectale.ch>" and p["subject"] == "Re: MPA")
    ck("an HTML-only body is stripped, not dropped", "Signed" in p["body"] and "<p>" not in p["body"],
       repr(p["body"]))
    ck("the timestamp is seconds, not milliseconds", 1.7e9 < p["ts"] < 1.9e9, str(p["ts"]))
    ck("a payload that is not a dict does not raise", parse_message({"payload": 7})["from"] == "")
    ck("a message that is not a dict does not raise", parse_message(None)["id"] == "")

    calls = []

    def fake(url, headers=None, params=None, timeout=20):
        calls.append((url, dict(params or {})))
        if url.endswith("/messages"):
            return 200, {"messages": [{"id": "m1"}, {"id": "m2"}]}
        if url.endswith("/m1"):
            return 200, msg
        return 500, {}

    got, note = fetch_mailbox("dima@s4biz.io", days=7, limit=5, fetch=fake)
    ck("one unreadable message does not lose the readable one", len(got) == 1, note)
    ck("the mailbox is recorded on the message", got[0].get("mailbox") == "dima@s4biz.io")
    ck("the window is bounded in the QUERY, not after the fact",
       "newer_than:7d" in calls[0][1].get("q", ""), str(calls[0][1]))
    ck("the mailbox is the one impersonated, not 'me'", "dima@s4biz.io" in calls[0][0], calls[0][0])
    ck("the note NAMES its subject", "dima@s4biz.io" in note, note)

    def refuse(url, headers=None, params=None, timeout=20):
        return 403, {}
    _g, n2 = fetch_mailbox("x@s4biz.io", fetch=refuse)
    ck("an HTTP refusal is reported, never raised", "403" in n2 and "x@s4biz.io" in n2, n2)

    def boom(url, headers=None, params=None, timeout=20):
        raise RuntimeError("socket")
    _g, n3 = fetch_mailbox("x@s4biz.io", fetch=boom)
    ck("a transport fault is reported, never raised", "could not be listed" in n3, n3)

    ck("reading is OFF unless switched on", not enabled() or configured())
    ck("the status note names the console step when it is off",
       bool(status()["note"]) is not configured())

    print("gmail_read selftest: %d check(s) failed" % len(fails))
    return 1 if fails else 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
