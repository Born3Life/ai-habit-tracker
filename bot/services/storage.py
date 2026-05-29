from __future__ import annotations

import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "data"
DB_PATH = DATA_DIR / "tracker.db"

TRIAL_DAYS = 7
PRICE = 590


def _init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                registered_at TEXT NOT NULL DEFAULT (datetime('now')),
                trial_end TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                is_paid INTEGER DEFAULT 0,
                last_summary_sent TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS checkins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                ai_response TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_checkins_user
            ON checkins(user_id, created_at)
        """)
        conn.commit()
    logger.info("db ready at %s", DB_PATH)


def _register_user(
    user_id: int,
    username: str | None,
    full_name: str,
) -> bool:
    with sqlite3.connect(str(DB_PATH)) as conn:
        existing = conn.execute(
            "SELECT user_id FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if existing:
            return False

        trial_end = (datetime.utcnow() + timedelta(days=TRIAL_DAYS)).isoformat()
        conn.execute(
            "INSERT INTO users (user_id, username, full_name, trial_end) "
            "VALUES (?, ?, ?, ?)",
            (user_id, username, full_name, trial_end),
        )
        conn.commit()
        return True


def _user_info(user_id: int) -> dict | None:
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    if row is None:
        return None
    return dict(row)


def _add_checkin(user_id: int, text: str, ai_response: str) -> None:
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute(
            "INSERT INTO checkins (user_id, text, ai_response) VALUES (?, ?, ?)",
            (user_id, text, ai_response),
        )
        conn.commit()


def _get_recent_checkins(user_id: int, limit: int = 30) -> list[dict]:
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT text, ai_response, created_at FROM checkins "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in reversed(rows)]


def _get_week_checkins(user_id: int) -> list[dict]:
    since = (datetime.utcnow() - timedelta(days=7)).isoformat()
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT text, ai_response, created_at FROM checkins "
            "WHERE user_id = ? AND created_at >= ? ORDER BY id",
            (user_id, since),
        ).fetchall()
    return [dict(r) for r in rows]


def _get_reminder_candidates() -> list[int]:
    """Users who haven't checked in today and are within trial/paid."""
    today = datetime.utcnow().date().isoformat()
    with sqlite3.connect(str(DB_PATH)) as conn:
        rows = conn.execute(
            """
            SELECT u.user_id FROM users u
            WHERE u.is_active = 1
              AND (u.is_paid = 1 OR u.trial_end > datetime('now'))
              AND u.user_id NOT IN (
                SELECT user_id FROM checkins
                WHERE created_at >= ?
              )
        """,
            (today,),
        ).fetchall()
    return [r[0] for r in rows]


async def init_db() -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _init_db)


async def register_user(
    user_id: int,
    username: str | None,
    full_name: str,
) -> bool:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        _register_user,
        user_id,
        username,
        full_name,
    )


async def user_info(user_id: int) -> dict | None:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _user_info, user_id)


async def add_checkin(user_id: int, text: str, ai_response: str) -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _add_checkin, user_id, text, ai_response)


async def get_recent_checkins(user_id: int, limit: int = 30) -> list[dict]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _get_recent_checkins, user_id, limit)


async def get_week_checkins(user_id: int) -> list[dict]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _get_week_checkins, user_id)


async def get_reminder_candidates() -> list[int]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _get_reminder_candidates)


def _mark_summary_sent(user_id: int) -> None:
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute(
            "UPDATE users SET last_summary_sent = datetime('now') WHERE user_id = ?",
            (user_id,),
        )
        conn.commit()


async def mark_summary_sent(user_id: int) -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _mark_summary_sent, user_id)
