#!/usr/bin/env python3
"""Shared zero-trust auth for Colt bots.
Factor 1 (know): colt.net email (name.familyname@colt.net) + shared access password.
Factor 2 (possess): a 6-digit one-time code emailed to that Colt mailbox, entered via /verify.
Guessing the email + password is NOT enough — you must control the Colt inbox.
Codes: single-use, time-limited, attempt-limited. Lockout on repeated failures. Persisted store."""
import os, re, json, time, hmac, ssl, socket, smtplib, secrets, hashlib
from email.message import EmailMessage

COLT_PW     = os.environ.get("COLT_BOT_PASSWORD", "")
EMAIL_RE    = re.compile(r"^[a-z]+(?:-[a-z]+)*\.[a-z]+(?:-[a-z]+)*@colt\.net$", re.I)

# --- Partner / guest access -------------------------------------------------
# Colt AEs self-serve via EMAIL_RE (name.familyname@colt.net). Access outside colt.net is granted
# two ways. Email addresses/domains are NOT secrets, so the defaults are committed (auditable):
#   PARTNER_EMAILS  -> individual named people
#   PARTNER_DOMAINS -> a whole trusted domain (anyone@that-domain)
# Add more at runtime WITHOUT a code change:
#   EXTRA_ALLOWED_EMAILS="a@x.ch,b@y.com"     EXTRA_ALLOWED_DOMAINS="foo.io,bar.com"
PARTNER_EMAILS  = {"ud@objectale.ch"}          # Objectale partner
PARTNER_DOMAINS = {"s4biz.io"}                 # S4BIZ — whole domain trusted

_GENERIC_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")

EXTRA_ALLOWED_EMAILS  = {e.strip().lower() for e in
                         os.environ.get("EXTRA_ALLOWED_EMAILS", "").split(",") if e.strip()}
EXTRA_ALLOWED_DOMAINS = {d.strip().lower().lstrip("@") for d in
                         os.environ.get("EXTRA_ALLOWED_DOMAINS", "").split(",") if d.strip()}
ALLOWED_EMAILS  = PARTNER_EMAILS  | EXTRA_ALLOWED_EMAILS
ALLOWED_DOMAINS = PARTNER_DOMAINS | EXTRA_ALLOWED_DOMAINS

def email_allowed(email: str) -> bool:
    """True if the address may authenticate:
         * a Colt AE            -> name.familyname@colt.net   (EMAIL_RE)
         * a named partner      -> ALLOWED_EMAILS
         * a trusted domain     -> anyone@ALLOWED_DOMAINS
    Used by BOTH the Telegram bots and the web app so they can never disagree.
    NOTE: this only decides WHO may start auth — the shared password + a 6-digit OTP
    delivered to that mailbox are still required."""
    e = (email or "").strip().lower()
    if not _GENERIC_EMAIL_RE.match(e):
        return False
    if EMAIL_RE.match(e) or e in ALLOWED_EMAILS:
        return True
    return e.split("@", 1)[1] in ALLOWED_DOMAINS
MAX_FAILS   = int(os.environ.get("AUTH_MAX_FAILS", "5"))
LOCK_SECS   = int(os.environ.get("AUTH_LOCK_SECS", "900"))
OTP_TTL     = int(os.environ.get("OTP_TTL_SECS", "600"))      # 10 minutes
OTP_MAX     = int(os.environ.get("OTP_MAX_TRIES", "5"))
REQUIRE_2FA = os.environ.get("REQUIRE_2FA", "1").lower() in ("1", "true", "yes")

SMTP_HOST     = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT     = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER     = os.environ.get("SMTP_USER", "")
SMTP_PASS     = os.environ.get("SMTP_PASS", "")
SMTP_FROM     = os.environ.get("SMTP_FROM", SMTP_USER)
SMTP_STARTTLS = os.environ.get("SMTP_STARTTLS", "1").lower() in ("1", "true", "yes")

# Gmail API (HTTPS/443) — used when the SMTP ports are blocked (e.g. on cloud droplets).
# Service account with domain-wide delegation (scope gmail.send), impersonating GMAIL_SENDER.
# The SA JSON key is passed base64-encoded in the env (no secret file to mount).
GMAIL_SENDER  = os.environ.get("GMAIL_SENDER", "")
GMAIL_SA_B64  = os.environ.get("GMAIL_SA_B64", "")

def _now(): return time.time()

class Auth:
    def __init__(self, bot_name, store_path, log=None):
        self.bot = bot_name; self.path = store_path
        self.log = log or (lambda **k: None)
        self.authed = self._load()   # {uid: {email, ts}}
        self.pending = {}            # {uid: {email, code_hash, exp, tries}}
        self.fails = {}              # {uid: [n, t0]}

    def _load(self):
        try: return json.load(open(self.path))
        except Exception: return {}
    def _save(self):
        try:
            d = os.path.dirname(self.path)
            if d: os.makedirs(d, exist_ok=True)
            json.dump(self.authed, open(self.path, "w"), indent=2)
        except Exception: pass

    def is_authed(self, uid, allowed=None):
        u = str(uid); ok = u in self.authed
        return ok and ((not allowed) or (u in allowed))

    def locked(self, uid):
        c = self.fails.get(str(uid))
        if not c: return 0
        n, t0 = c
        if n >= MAX_FAILS and (_now() - t0) < LOCK_SECS: return int(LOCK_SECS - (_now() - t0))
        if (_now() - t0) >= LOCK_SECS: self.fails.pop(str(uid), None)
        return 0
    def _fail(self, uid):
        c = self.fails.get(str(uid)) or [0, _now()]; c[0] += 1
        if c[0] == 1: c[1] = _now()
        self.fails[str(uid)] = c

    def _hash(self, code, uid): return hashlib.sha256((str(code).strip() + str(uid)).encode()).hexdigest()

    def begin(self, uid, email, pw):
        """Factor 1. Returns (state, message). state in locked|error|denied|authed|otp_sent."""
        u = str(uid)
        lk = self.locked(uid)
        if lk: return ("locked", "\U0001f6d1 Too many attempts. Try again in %ds." % lk)
        if not COLT_PW: return ("error", "Auth is not configured (COLT_BOT_PASSWORD).")
        email = (email or "").strip()
        if not (email_allowed(email) and hmac.compare_digest(pw or "", COLT_PW)):
            self._fail(uid)
            self.log(evt="auth", bot=self.bot, result="fail", email=email.lower()[:60], user=u, ts=int(_now()))
            return ("denied", "❌ Access denied. Requires a valid Colt email (name.familyname@colt.net) and the access password.")
        if not REQUIRE_2FA:
            self.authed[u] = {"email": email.lower(), "ts": int(_now())}; self._save()
            self.log(evt="auth", bot=self.bot, result="ok", email=email.lower(), user=u, ts=int(_now()))
            return ("authed", "✅ Authenticated as %s." % email.lower())
        code = "".join(secrets.choice("0123456789") for _ in range(6))
        self.pending[u] = {"email": email.lower(), "code": self._hash(code, u), "exp": _now() + OTP_TTL, "tries": 0}
        if not self._send_otp(email.lower(), code):
            self.log(evt="auth", bot=self.bot, result="otp_send_fail", email=email.lower(), user=u, ts=int(_now()))
            return ("error", "⚠ I couldn't send the verification email. Ask the admin to check SMTP settings.")
        self.log(evt="auth", bot=self.bot, result="otp_sent", email=email.lower(), user=u, ts=int(_now()))
        return ("otp_sent", "\U0001f4e7 I emailed a 6-digit code to %s.\nReply:  /verify <code>   (valid %d min)." % (email.lower(), OTP_TTL // 60))

    def verify(self, uid, code):
        """Factor 2. Returns (ok, message)."""
        u = str(uid); p = self.pending.get(u)
        if not p: return (False, "No pending verification. Start with /auth <email> <password>.")
        if _now() > p["exp"]: self.pending.pop(u, None); return (False, "⏱ Code expired. Run /auth again.")
        if p["tries"] >= OTP_MAX: self.pending.pop(u, None); self._fail(uid); return (False, "Too many wrong codes. Run /auth again.")
        p["tries"] += 1
        if hmac.compare_digest(self._hash(code, u), p["code"]):
            self.authed[u] = {"email": p["email"], "ts": int(_now())}; self._save()
            self.pending.pop(u, None); self.fails.pop(u, None)
            self.log(evt="auth", bot=self.bot, result="verified", email=p["email"], user=u, ts=int(_now()))
            return (True, "✅ Verified. You're in as %s." % p["email"])
        self.log(evt="auth", bot=self.bot, result="otp_bad", email=p["email"], user=u, ts=int(_now()))
        return (False, "❌ Wrong code. %d attempt(s) left." % max(0, OTP_MAX - p["tries"]))

    def _build_msg(self, email, code):
        msg = EmailMessage()
        msg["Subject"] = "Your Colt bot access code"
        msg["From"] = SMTP_FROM or GMAIL_SENDER; msg["To"] = email
        msg.set_content("Your one-time access code is: %s\n\nIt expires in %d minutes.\n"
                        "If you did not request this, ignore this email.\n\n- Colt pre-sales bot" % (code, OTP_TTL // 60))
        return msg

    def _send_otp(self, email, code):
        # Prefer the Gmail API (HTTPS/443) when configured — works where SMTP ports are blocked.
        if GMAIL_SENDER and GMAIL_SA_B64:
            return self._send_gmail_api(email, code)
        return self._send_smtp(email, code)

    def _send_gmail_api(self, email, code):
        try:
            import base64, json as _json, requests
            from google.oauth2 import service_account
            from google.auth.transport.requests import Request as GRequest
            info = _json.loads(base64.b64decode(GMAIL_SA_B64))
            creds = service_account.Credentials.from_service_account_info(
                info, scopes=["https://www.googleapis.com/auth/gmail.send"], subject=GMAIL_SENDER)
            creds.refresh(GRequest())
            raw = base64.urlsafe_b64encode(self._build_msg(email, code).as_bytes()).decode()
            r = requests.post(
                "https://gmail.googleapis.com/gmail/v1/users/%s/messages/send" % GMAIL_SENDER,
                headers={"Authorization": "Bearer " + creds.token, "Content-Type": "application/json"},
                json={"raw": raw}, timeout=20)
            if r.status_code in (200, 202): return True
            self.log(evt="gmail_api", bot=self.bot, result="error", status=r.status_code, err=r.text[:200], ts=int(_now()))
            return False
        except Exception as e:
            self.log(evt="gmail_api", bot=self.bot, result="error", err=repr(e)[:200], ts=int(_now()))
            return False

    def _send_smtp(self, email, code):
        if not (SMTP_HOST and SMTP_USER and SMTP_PASS and SMTP_FROM): return False
        msg = self._build_msg(email, code)
        _orig_gai = socket.getaddrinfo   # force IPv4 (avoid AAAA ENETUNREACH on no-IPv6 bridges)
        def _v4_only(host, port, family=0, type=0, proto=0, flags=0):
            return _orig_gai(host, port, socket.AF_INET, type, proto, flags)
        socket.getaddrinfo = _v4_only
        try:
            ctx = ssl.create_default_context()
            if SMTP_PORT == 465:
                with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=20, context=ctx) as s:
                    s.login(SMTP_USER, SMTP_PASS); s.send_message(msg)
            else:
                with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as s:
                    if SMTP_STARTTLS: s.starttls(context=ctx)
                    s.login(SMTP_USER, SMTP_PASS); s.send_message(msg)
            return True
        except Exception as e:
            self.log(evt="smtp", bot=self.bot, result="error", err=repr(e)[:140], ts=int(_now()))
            return False
        finally:
            socket.getaddrinfo = _orig_gai
