"""Tiny SQLite store for assessment history, keyed by user email (KISS — mirrors jobhuntwow store.py).
Secrets never land here; only job metadata + deck filenames."""
import os, json, time, sqlite3, threading
from .settings import DATA_DIR

_LOCK = threading.Lock()
_PATH = os.path.join(str(DATA_DIR), "colt.sqlite")


def _conn():
    os.makedirs(str(DATA_DIR), exist_ok=True)
    c = sqlite3.connect(_PATH)
    c.row_factory = sqlite3.Row
    return c


def _init():
    with _LOCK, _conn() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS jobs (
                job_id   TEXT PRIMARY KEY,
                email    TEXT NOT NULL,
                company  TEXT NOT NULL,
                created  INTEGER NOT NULL,
                status   TEXT NOT NULL,
                decks    TEXT NOT NULL DEFAULT '[]',
                summary  TEXT NOT NULL DEFAULT '{}'
            )"""
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_jobs_email ON jobs(email)")


_init()


def create_job(job_id: str, email: str, company: str) -> dict:
    with _LOCK, _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO jobs(job_id,email,company,created,status,decks,summary) "
            "VALUES(?,?,?,?,?,?,?)",
            (job_id, email.lower(), company, int(time.time()), "running", "[]", "{}"),
        )
    return get_job(job_id)


def finish_job(job_id: str, decks: list, summary: dict, status: str = "done") -> dict:
    with _LOCK, _conn() as c:
        c.execute(
            "UPDATE jobs SET status=?, decks=?, summary=? WHERE job_id=?",
            (status, json.dumps(decks), json.dumps(summary), job_id),
        )
    return get_job(job_id)


def set_status(job_id: str, status: str) -> None:
    with _LOCK, _conn() as c:
        c.execute("UPDATE jobs SET status=? WHERE job_id=?", (status, job_id))


def get_job(job_id: str):
    with _conn() as c:
        row = c.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
    return _row_to_dict(row) if row else None


def history(email: str) -> list:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM jobs WHERE email=? ORDER BY created DESC", (email.lower(),)
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def _row_to_dict(r) -> dict:
    return {
        "job_id": r["job_id"],
        "email": r["email"],
        "company": r["company"],
        "created": r["created"],
        "status": r["status"],
        "decks": json.loads(r["decks"] or "[]"),
        "summary": json.loads(r["summary"] or "{}"),
    }
