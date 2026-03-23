"""
db.py
=====
SQLite leaderboard persistence layer.

The database file is stored at DATA_DIR/leaderboard.db.
DATA_DIR defaults to the directory of this file but can be overridden
with the LEADERBOARD_DB_DIR environment variable — useful in Docker
when you want to mount a volume for persistence.
"""

import os
import sqlite3
from datetime import datetime
from typing import List, Dict

# ── Configuration ─────────────────────────────────────────────────────────────

_DEFAULT_DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.environ.get("LEADERBOARD_DB_DIR", _DEFAULT_DB_DIR)
DB_PATH = os.path.join(DB_DIR, "leaderboard.db")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row          # rows accessible as dicts
    conn.execute("PRAGMA journal_mode=WAL") # safer concurrent writes
    return conn


# ── Public API ────────────────────────────────────────────────────────────────

def init_db() -> None:
    """Create the scores table if it does not exist."""
    os.makedirs(DB_DIR, exist_ok=True)
    with _get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scores (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                player     TEXT    NOT NULL,
                score      INTEGER NOT NULL,
                created_at TEXT    NOT NULL
            )
        """)
        conn.commit()


def add_score(player: str, score: int) -> int:
    """
    Insert a new score row.

    Parameters
    ----------
    player : display name (already validated/sanitised by the route)
    score  : integer tile-merge score

    Returns
    -------
    The row-id of the inserted record.
    """
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    with _get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO scores (player, score, created_at) VALUES (?, ?, ?)",
            (player, score, now),
        )
        conn.commit()
        return cur.lastrowid


def get_top_scores(limit: int = 10) -> List[Dict]:
    """
    Return the top *limit* scores ordered by score descending.

    Each element is a dict with keys: rank, player, score, created_at.
    """
    with _get_connection() as conn:
        rows = conn.execute(
            """
            SELECT player, score, created_at
            FROM   scores
            ORDER  BY score DESC, created_at ASC
            LIMIT  ?
            """,
            (limit,),
        ).fetchall()

    return [
        {
            "rank":       idx + 1,
            "player":     row["player"],
            "score":      row["score"],
            "created_at": row["created_at"],
        }
        for idx, row in enumerate(rows)
    ]
