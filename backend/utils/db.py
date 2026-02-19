"""
ProofPilot — SQLite job store

DATABASE_PATH env var: path to jobs.db (default: ./jobs.db relative to backend/)
Set to a Railway volume mount path (e.g. /app/data/jobs.db) for persistence.
"""

import os
import json
import sqlite3
from pathlib import Path
from datetime import datetime
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
    """Create jobs table if it doesn't exist. Safe to call on every startup."""
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
        conn.commit()


def save_job(job_id: str, data: dict) -> None:
    """Insert or replace a completed job. Called from asyncio.to_thread()."""
    with _connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO jobs
              (job_id, client_name, workflow_title, workflow_id,
               inputs, content, docx_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                data.get("client_name", ""),
                data.get("workflow_title", ""),
                data.get("workflow_id", ""),
                json.dumps(data.get("inputs", {})),
                data.get("content", ""),
                data.get("docx_path"),
                data.get("created_at", datetime.utcnow().isoformat()),
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
