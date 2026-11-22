#!/usr/bin/env python3
"""user_store.py — per-user credentials for cybergod.ai, shared by colt-web AND the Telegram bots.

WHY THIS EXISTS
---------------
Until now there was ONE shared access password (`COLT_BOT_PASSWORD`) for everybody, plus an
allow-list deciding who may present it. That is a single secret with no revocation: you cannot take
access away from one person without changing it for all of them, and you cannot tell from a log who
actually knew it. This module gives each identity its own password, set and reset by an
administrator, while leaving the allow-list and the OTP second factor exactly as they were.

WHERE IT LIVES, AND WHY THERE
-----------------------------
`/var/log/colt/users.sqlite` on the PERSISTENT, SHARED `colt_events` volume. That volume is mounted
read-write by colt-web, colt-assessbot and colt-cassandra, so all three consult ONE credential
store and can never disagree about a password. It is the same volume, and the same reasoning, as
`cost_ledger.sqlite`: it survives redeploys and image rebuilds, which `colt_webdata` (colt-web only)
would not give the bots.

THE SECURITY DECISIONS, STATED
------------------------------
* PASSWORDS ARE NEVER STORED. Only scrypt(password, salt) is. scrypt is memory-hard, which is what
  makes a stolen database expensive to attack offline; a plain SHA-256 of a password is not a
  meaningfully harder problem than the password itself. Parameters n=2**14, r=8, p=1 cost roughly
  16 MB and ~100 ms per verification, which is negligible for one login and ruinous for a
  brute-force run.
* NO USER ENUMERATION BY TIMING. `check_password` on an unknown address performs the SAME scrypt
  work against a dummy salt before returning False. Without that, "no such user" answers in
  microseconds and "wrong password" in ~100 ms, and the difference tells an attacker which
  addresses are real.
* CONSTANT-TIME COMPARISON. `hmac.compare_digest`, never `==`.
* THE PLAINTEXT IS RETURNED EXACTLY ONCE, to the administrator who generated it, and is never
  written to the database, never logged, and never included in any listing. If it is lost it is
  reset, not recovered. `list_all()` cannot leak a hash because it does not select the columns.
* FAILS CLOSED ON A BROKEN STORE. If the database cannot be opened, `check_password` returns
  (False, False) rather than allowing the login. `has_account` returns False so the caller falls
  back to the shared password, which keeps existing users working; but a user who HAS an assigned
  password can never be admitted by a store that is unreadable.
"""
import hashlib
import hmac
import os
import secrets
import sqlite3
import string
import time

# Candidate locations, most-shared first. The env var wins so a test or a local run can point at a
# scratch file without touching the real store.
_CANDIDATES = ("/var/log/colt/users.sqlite",
               os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "users.sqlite"))


def db_path():
    p = os.environ.get("USER_DB")
    if p:
        return p
    for c in _CANDIDATES:
        d = os.path.dirname(c)
        if os.path.isdir(d):
            return c
    return _CANDIDATES[-1]


# scrypt work factors. Raising n later is safe: the parameters are stored with each row, so old
# hashes keep verifying and only new ones get the higher cost.
_N, _R, _P, _DKLEN = 2 ** 14, 8, 1, 32
_MAXMEM = 64 * 1024 * 1024          # 128*n*r = 16 MB; give OpenSSL room so it does not refuse
MIN_PASSWORD_LEN = int(os.environ.get("MIN_PASSWORD_LEN", "12"))

# A fixed salt used ONLY to burn the same CPU on a miss as on a hit. It protects nothing and is
# deliberately not secret.
_DUMMY_SALT = b"cybergod-timing-equaliser-0000000"


def _conn():
    p = db_path()
    d = os.path.dirname(p)
    if d:
        os.makedirs(d, exist_ok=True)
    c = sqlite3.connect(p, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("""CREATE TABLE IF NOT EXISTS users (
                     email       TEXT PRIMARY KEY,
                     pw_hash     BLOB NOT NULL,
                     pw_salt     BLOB NOT NULL,
                     n           INTEGER NOT NULL DEFAULT 16384,
                     r           INTEGER NOT NULL DEFAULT 8,
                     p           INTEGER NOT NULL DEFAULT 1,
                     must_change INTEGER NOT NULL DEFAULT 1,
                     disabled    INTEGER NOT NULL DEFAULT 0,
                     created_ts  REAL,
                     updated_ts  REAL,
                     created_by  TEXT,
                     note        TEXT
                 )""")
    # A ROLE IS NOT A CREDENTIAL, AND IT MUST NOT LIVE IN THE CREDENTIAL ROW.
    #
    # The first version of this put a `role` column on `users`. It cannot work, and the admin page
    # is where it fails: most of the people on it - every Colt address, every partner on a trusted
    # domain - have NO row here at all, because they sign in with the shared password. `users`
    # requires pw_hash NOT NULL, so giving one of them a role would have meant inventing a
    # credential row, and that row has two side effects nobody asked for: `has_account()` would
    # start returning True, which takes the shared password away from them (i.e. assigning a role
    # LOCKS THE PERSON OUT), and `_has_enabled_account()` in colt_auth would start treating it as
    # an authorisation source in its own right. Naming somebody a Sales Rep is not an act of
    # granting or revoking access and must not quietly be one.
    #
    # So roles get their own table, keyed by address, with no dependence on whether a password was
    # ever issued. Reading it answers "what may this person do"; `users` answers "how do they prove
    # who they are". The dead `role` column is still added below because the droplet already has
    # it (it shipped on 22 Nov) and a schema that differs between boxes is its own class of bug;
    # nothing reads it, and tests/test_roles.py fails the build if anything starts to.
    c.execute("""CREATE TABLE IF NOT EXISTS user_roles (
                     email      TEXT PRIMARY KEY,
                     role       TEXT NOT NULL,
                     updated_ts REAL,
                     set_by     TEXT
                 )""")
    _cols = {r[1] for r in c.execute("PRAGMA table_info(users)").fetchall()}
    if "role" not in _cols:
        c.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT ''")
    c.commit()
    return c


def available():
    """True if the store can be opened. Used to report an honest status, never to bypass a check."""
    try:
        _conn().close()
        return True
    except Exception:
        return False


def _norm(email):
    return (email or "").strip().lower()


def _derive(password, salt, n=_N, r=_R, p=_P):
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p,
                          dklen=_DKLEN, maxmem=_MAXMEM)


def generate_password(words=None, length=16):
    """A password the administrator can read aloud without ambiguity.

    Deliberately excludes the characters that get misread or mistyped when a password is relayed
    over a phone call or a chat message: 0/O, 1/l/I. A password that has to be re-sent because it
    was transcribed wrongly is a password that ends up in more places than it should.
    """
    alphabet = "".join(c for c in (string.ascii_letters + string.digits) if c not in "0O1lI")
    return "".join(secrets.choice(alphabet) for _ in range(max(MIN_PASSWORD_LEN, int(length))))


def set_password(email, password, must_change=True, by="", note=None):
    """Create the account or replace its password. Returns the stored record (never the password)."""
    e = _norm(email)
    if not e or "@" not in e:
        raise ValueError("a valid email address is required")
    if len(password or "") < MIN_PASSWORD_LEN:
        raise ValueError("password must be at least %d characters" % MIN_PASSWORD_LEN)
    salt = secrets.token_bytes(32)
    h = _derive(password, salt)
    now = time.time()
    c = _conn()
    try:
        cur = c.execute("SELECT created_ts, created_by, note FROM users WHERE email=?", (e,))
        row = cur.fetchone()
        created = (row["created_ts"] if row else now) or now
        creator = (row["created_by"] if row else by) or by
        keep_note = note if note is not None else (row["note"] if row else None)
        c.execute("""INSERT INTO users (email, pw_hash, pw_salt, n, r, p, must_change, disabled,
                                        created_ts, updated_ts, created_by, note)
                     VALUES (?,?,?,?,?,?,?,COALESCE((SELECT disabled FROM users WHERE email=?),0),
                             ?,?,?,?)
                     ON CONFLICT(email) DO UPDATE SET
                        pw_hash=excluded.pw_hash, pw_salt=excluded.pw_salt,
                        n=excluded.n, r=excluded.r, p=excluded.p,
                        must_change=excluded.must_change, updated_ts=excluded.updated_ts,
                        note=excluded.note""",
                  (e, h, salt, _N, _R, _P, 1 if must_change else 0, e,
                   created, now, creator, keep_note))
        c.commit()
    finally:
        c.close()
    return get(e)


def check_password(email, password):
    """(ok, must_change). ok is False for an unknown, disabled or wrong-password account.

    Runs the same scrypt cost on every path so a miss cannot be distinguished from a wrong
    password by how long the answer took.
    """
    e = _norm(email)
    row = None
    try:
        c = _conn()
        try:
            row = c.execute(
                "SELECT pw_hash, pw_salt, n, r, p, must_change, disabled FROM users WHERE email=?",
                (e,)).fetchone()
        finally:
            c.close()
    except Exception:
        # A store we cannot read must never admit anybody who is supposed to have an account.
        _derive(password or "", _DUMMY_SALT)
        return (False, False)
    if row is None or row["disabled"]:
        _derive(password or "", _DUMMY_SALT)      # equalise timing; decide nothing from it
        return (False, False)
    calc = _derive(password or "", row["pw_salt"], row["n"], row["r"], row["p"])
    if hmac.compare_digest(calc, bytes(row["pw_hash"])):
        return (True, bool(row["must_change"]))
    return (False, False)


def has_account(email):
    """True if this identity has an assigned password (enabled or not).

    Callers use this to decide whether the shared fallback password still applies. It deliberately
    counts a DISABLED account: a disabled user must not fall back to the shared password and get in
    anyway, which would make disabling meaningless.
    """
    try:
        c = _conn()
        try:
            return c.execute("SELECT 1 FROM users WHERE email=?", (_norm(email),)).fetchone() is not None
        finally:
            c.close()
    except Exception:
        return False


def clear_must_change(email):
    try:
        c = _conn()
        try:
            c.execute("UPDATE users SET must_change=0, updated_ts=? WHERE email=?",
                      (time.time(), _norm(email)))
            c.commit()
        finally:
            c.close()
        return True
    except Exception:
        return False


def set_role(email, role, by=""):
    """Record a role for ANY address, with or without a credential row.

    The CALLER decides whether the actor is allowed to: roles.may_grant() and roles.may_touch()
    answer that, and they live in roles.py so there is one home for the policy. This function only
    writes, and it refuses a role the policy does not define - a typo must not become a silent
    demotion to the default. The empty string CLEARS the row, which is how a person goes back to
    the default role; that is a deletion rather than a stored "user" so the table says only what
    somebody actually decided.
    """
    import roles as _roles
    e = _norm(email)
    if not e or "@" not in e:
        return False
    r = (role or "").strip().lower()
    if r and r not in _roles.ROLES:
        return False
    try:
        c = _conn()
        try:
            if not r:
                c.execute("DELETE FROM user_roles WHERE email=?", (e,))
            else:
                c.execute("INSERT INTO user_roles (email, role, updated_ts, set_by) VALUES (?,?,?,?) "
                          "ON CONFLICT(email) DO UPDATE SET role=excluded.role, "
                          "updated_ts=excluded.updated_ts, set_by=excluded.set_by",
                          (e, r, time.time(), by or ""))
            c.commit()
            return True
        finally:
            c.close()
    except Exception:
        return False


def get_role(email):
    """The stored role, or '' when nobody has decided one.

    Fails to '' rather than raising: roles.role_of() turns '' into the least-privileged role, so a
    store we cannot read removes privilege instead of inventing it.
    """
    try:
        c = _conn()
        try:
            row = c.execute("SELECT role FROM user_roles WHERE email=?", (_norm(email),)).fetchone()
            return (row["role"] if row else "") or ""
        finally:
            c.close()
    except Exception:
        return ""


def list_roles():
    """{address: role} for everyone who has one. ONE query, because the admin listing needs the
    role of every address on the page and N lookups over a shared sqlite file on a 4 GB droplet is
    how a list page becomes a timeout."""
    try:
        c = _conn()
        try:
            return {r["email"]: r["role"] for r in c.execute("SELECT email, role FROM user_roles")}
        finally:
            c.close()
    except Exception:
        return {}


def set_disabled(email, disabled=True):
    c = _conn()
    try:
        c.execute("UPDATE users SET disabled=?, updated_ts=? WHERE email=?",
                  (1 if disabled else 0, time.time(), _norm(email)))
        c.commit()
    finally:
        c.close()
    return get(email)


def delete(email):
    c = _conn()
    try:
        cur = c.execute("DELETE FROM users WHERE email=?", (_norm(email),))
        c.commit()
        return cur.rowcount > 0
    finally:
        c.close()


def _row(r):
    # ANY NEW COLUMN MUST BE ADDED HERE TOO. This dict is hardcoded, so a column that is selected
    # but not listed is silently dropped between the database and the caller - exactly how `lang`
    # was lost once already. The ROLE is deliberately absent: it is not a property of a credential
    # and most people who have one have no row here. get_role() is its one home.
    return {"email": r["email"], "must_change": bool(r["must_change"]),
            "disabled": bool(r["disabled"]), "created_ts": r["created_ts"],
            "updated_ts": r["updated_ts"], "created_by": r["created_by"], "note": r["note"]}


def get(email):
    try:
        c = _conn()
        try:
            r = c.execute("""SELECT email, must_change, disabled, created_ts, updated_ts,
                                    created_by, note FROM users WHERE email=?""",
                          (_norm(email),)).fetchone()
            return _row(r) if r else None
        finally:
            c.close()
    except Exception:
        return None


def list_all():
    """Every account with an assigned password. The hash columns are not selected, so no caller of
    this function can leak them even by accident."""
    try:
        c = _conn()
        try:
            rows = c.execute("""SELECT email, must_change, disabled, created_ts, updated_ts,
                                       created_by, note FROM users ORDER BY email""").fetchall()
            return [_row(r) for r in rows]
        finally:
            c.close()
    except Exception:
        return []
