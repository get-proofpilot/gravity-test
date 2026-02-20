"""
ProofPilot — SQLite job store

DATABASE_PATH env var: path to jobs.db (default: ./jobs.db relative to backend/)
Set to a Railway volume mount path (e.g. /app/data/jobs.db) for persistence.
"""

import os
import json
import sqlite3
import secrets
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

DB_PATH = os.environ.get(
    "DATABASE_PATH",
    str(Path(__file__).parent.parent / "jobs.db")
)


def _connect() -> sqlite3.Connection:
    # Ensure parent directory exists (required when using a Railway Volume path)
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables if they don't exist. Safe to call on every startup."""
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id        TEXT PRIMARY KEY,
                client_name   TEXT NOT NULL DEFAULT '',
                workflow_title TEXT NOT NULL DEFAULT '',
                workflow_id   TEXT NOT NULL DEFAULT '',
                inputs        TEXT NOT NULL DEFAULT '{}',
                content       TEXT NOT NULL DEFAULT '',
                docx_path     TEXT,
                created_at    TEXT NOT NULL
            )
        """)

        # ── Clients table ───────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                client_id        INTEGER PRIMARY KEY AUTOINCREMENT,
                name             TEXT NOT NULL,
                domain           TEXT NOT NULL DEFAULT '',
                service          TEXT NOT NULL DEFAULT '',
                location         TEXT NOT NULL DEFAULT '',
                plan             TEXT NOT NULL DEFAULT 'Starter',
                monthly_revenue  TEXT NOT NULL DEFAULT '',
                avg_job_value    TEXT NOT NULL DEFAULT '',
                status           TEXT NOT NULL DEFAULT 'active',
                color            TEXT NOT NULL DEFAULT '#0051FF',
                initials         TEXT NOT NULL DEFAULT '',
                notes            TEXT NOT NULL DEFAULT '',
                strategy_context TEXT NOT NULL DEFAULT '',
                created_at       TEXT NOT NULL,
                updated_at       TEXT NOT NULL
            )
        """)
        conn.commit()

        # ── Table migrations ───────────────────────────────────────
        for col_sql in [
            "ALTER TABLE jobs ADD COLUMN client_id INTEGER DEFAULT 0",
            "ALTER TABLE jobs ADD COLUMN approved INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE jobs ADD COLUMN approved_at TEXT",
            "ALTER TABLE clients ADD COLUMN portal_token TEXT",
        ]:
            try:
                conn.execute(col_sql)
                conn.commit()
            except Exception:
                pass  # Column already exists

        # ── Seed clients if table is empty ──────────────────────────
        count = conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
        if count == 0:
            now = datetime.now(timezone.utc).isoformat()
            seed_clients = [
                ("All Thingz Electric",          "allthingzelectric.com",         "Starter",    "active",   "#7C3AED", "AE"),
                ("Adam Levinstein Photography",  "adamlevinstein.com",            "Starter",    "active",   "#7C3AED", "AL"),
                ("Dolce Electric",               "dolceelectric.com",             "Starter",    "active",   "#7C3AED", "DE"),
                ("Integrative Sports and Spine", "integrativesportsandspine.com", "Agency",     "active",   "#0D9488", "IS"),
                ("Saiyan Electric",              "saiyanelectric.com",            "Starter",    "active",   "#7C3AED", "SE"),
                ("Cedar Gold Group",             "cedargoldgroup.com",            "Agency",     "active",   "#0D9488", "CG"),
                ("Pelican Coast Electric",       "pelicancoastelectric.com",      "Starter",    "active",   "#7C3AED", "PC"),
                ("ProofPilot",                   "proofpilot.com",                "Agency",     "active",   "#0051FF", "PP"),
                ("Xsite Belize",                 "xsitebelize.com",               "Starter",    "active",   "#7C3AED", "XB"),
                ("Power Route Electric",         "powerrouteelectric.com",        "Starter",    "active",   "#7C3AED", "PR"),
                ("Alpha Property Management",    "alphapropertymgmt.com",         "Agency",     "active",   "#7C3AED", "AP"),
                ("Trading Academy",              "tradingacademy.com",            "Enterprise", "active",   "#7C3AED", "TA"),
                ("Youth Link",                   "youthlink.org",                 "Starter",    "inactive", "#F59E3B", "YL"),
                ("LAF Counseling",               "lafcounseling.com",             "Starter",    "active",   "#EA580C", "LC"),
            ]
            conn.executemany(
                """INSERT INTO clients
                   (name, domain, plan, status, color, initials, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                [(name, domain, plan, status, color, initials, now, now)
                 for name, domain, plan, status, color, initials in seed_clients]
            )
            conn.commit()

        # ── Generate portal tokens for any clients missing them ───
        rows = conn.execute(
            "SELECT client_id FROM clients WHERE portal_token IS NULL"
        ).fetchall()
        for row in rows:
            token = secrets.token_urlsafe(16)
            conn.execute(
                "UPDATE clients SET portal_token = ? WHERE client_id = ?",
                (token, row["client_id"]),
            )
        if rows:
            conn.commit()


# ── Job functions ────────────────────────────────────────────────────────────

def save_job(job_id: str, data: dict) -> None:
    """Insert or replace a completed job. Called from asyncio.to_thread()."""
    with _connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO jobs
              (job_id, client_name, workflow_title, workflow_id,
               inputs, content, docx_path, created_at, client_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                data.get("client_name", ""),
                data.get("workflow_title", ""),
                data.get("workflow_id", ""),
                json.dumps(data.get("inputs", {})),
                data.get("content", ""),
                data.get("docx_path"),
                data.get("created_at", datetime.now(timezone.utc).isoformat()),
                data.get("client_id", 0),
            ),
        )
        conn.commit()


def update_docx_path(job_id: str, docx_path: str) -> None:
    """Set docx_path after the document is generated."""
    with _connect() as conn:
        conn.execute(
            "UPDATE jobs SET docx_path = ? WHERE job_id = ?",
            (docx_path, job_id),
        )
        conn.commit()


def get_job(job_id: str) -> Optional[dict]:
    """Return a single job dict or None if not found."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["inputs"] = json.loads(d["inputs"])
        return d


def get_all_jobs() -> list:
    """Return all jobs sorted newest-first."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC"
        ).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["inputs"] = json.loads(d["inputs"])
            result.append(d)
        return result


def approve_job(job_id: str) -> bool:
    """Set approved=1 and record approval time."""
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE jobs SET approved=1, approved_at=? WHERE job_id=?",
            (datetime.now(timezone.utc).isoformat(), job_id),
        )
        conn.commit()
        return cur.rowcount > 0


def unapprove_job(job_id: str) -> bool:
    """Set approved=0 and clear approval time."""
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE jobs SET approved=0, approved_at=NULL WHERE job_id=?",
            (job_id,),
        )
        conn.commit()
        return cur.rowcount > 0


# ── Client CRUD functions ────────────────────────────────────────────────────

def _auto_initials(name: str) -> str:
    words = [w for w in name.split() if w]
    return "".join(w[0] for w in words[:2]).upper()


def create_client(data: dict) -> dict:
    """INSERT a new client and return the full row."""
    now = datetime.now(timezone.utc).isoformat()
    name = data.get("name", "").strip()
    initials = data.get("initials", "").strip() or _auto_initials(name)
    color = data.get("color", "#0051FF")
    token = secrets.token_urlsafe(16)
    with _connect() as conn:
        cur = conn.execute(
            """INSERT INTO clients
               (name, domain, service, location, plan, monthly_revenue, avg_job_value,
                status, color, initials, notes, strategy_context, portal_token, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                name,
                data.get("domain", ""),
                data.get("service", ""),
                data.get("location", ""),
                data.get("plan", "Starter"),
                data.get("monthly_revenue", ""),
                data.get("avg_job_value", ""),
                data.get("status", "active"),
                color,
                initials,
                data.get("notes", ""),
                data.get("strategy_context", ""),
                token,
                now, now,
            ),
        )
        conn.commit()
        return get_client(cur.lastrowid)


def get_client(client_id: int) -> Optional[dict]:
    """Return a single client dict or None."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM clients WHERE client_id = ?", (client_id,)
        ).fetchone()
        return dict(row) if row else None


def get_all_clients() -> list:
    """Return all non-deleted clients sorted by name."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM clients WHERE status != 'deleted' ORDER BY name ASC"
        ).fetchall()
        return [dict(r) for r in rows]


def update_client(client_id: int, data: dict) -> Optional[dict]:
    """PATCH semantics — only update provided keys."""
    allowed = {
        "name", "domain", "service", "location", "plan",
        "monthly_revenue", "avg_job_value", "status",
        "color", "initials", "notes", "strategy_context",
    }
    updates = {k: v for k, v in data.items() if k in allowed and v is not None}
    if not updates:
        return get_client(client_id)

    now = datetime.now(timezone.utc).isoformat()
    updates["updated_at"] = now

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [client_id]
    with _connect() as conn:
        conn.execute(
            f"UPDATE clients SET {set_clause} WHERE client_id = ?", values
        )
        conn.commit()
    return get_client(client_id)


def delete_client(client_id: int) -> bool:
    """Soft-delete: set status='deleted'."""
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE clients SET status='deleted', updated_at=? WHERE client_id=?",
            (datetime.now(timezone.utc).isoformat(), client_id),
        )
        conn.commit()
        return cur.rowcount > 0


# ── Portal functions ─────────────────────────────────────────────────────────

def get_client_by_token(token: str) -> Optional[dict]:
    """Look up a client by their portal token."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM clients WHERE portal_token = ? AND status != 'deleted'",
            (token,),
        ).fetchone()
        return dict(row) if row else None


def get_jobs_by_client(client_id: int) -> list:
    """Return all jobs for a specific client, newest first."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM jobs WHERE client_id = ? ORDER BY created_at DESC",
            (client_id,),
        ).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["inputs"] = json.loads(d["inputs"])
            result.append(d)
        return result
