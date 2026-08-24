import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

DB_PATH = Path(__file__).parent / "planner.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS commitments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    start TEXT NOT NULL,
    end TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    duration_minutes REAL NOT NULL,
    energy_cost TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS energy_windows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start TEXT NOT NULL,
    end TEXT NOT NULL,
    level TEXT NOT NULL
);
"""


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    # called on every startup, CREATE IF NOT EXISTS makes that fine
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        conn.commit()


def commitments_overlap(start1, end1, start2, end2) -> bool:
    return start1 < end2 and start2 < end1


def save_commitment(name: str, start: str, end: str) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO commitments (name, start, end) VALUES (?, ?, ?)",
            (name, start, end),
        )
        conn.commit()
        return cur.lastrowid


def load_commitments() -> list[tuple]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, name, start, end FROM commitments ORDER BY start"
        ).fetchall()


def delete_commitment(commitment_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM commitments WHERE id = ?", (commitment_id,))
        conn.commit()


def save_task(name: str, duration_minutes: float, energy_cost: str) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO tasks (name, duration_minutes, energy_cost) VALUES (?, ?, ?)",
            (name, duration_minutes, energy_cost),
        )
        conn.commit()
        return cur.lastrowid


def load_tasks() -> list[tuple]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, name, duration_minutes, energy_cost FROM tasks"
        ).fetchall()


def delete_task(task_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()


def save_energy_window(start: str, end: str, level: str) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO energy_windows (start, end, level) VALUES (?, ?, ?)",
            (start, end, level),
        )
        conn.commit()
        return cur.lastrowid


def load_energy_windows() -> list[tuple]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, start, end, level FROM energy_windows ORDER BY start"
        ).fetchall()


def delete_energy_window(window_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM energy_windows WHERE id = ?", (window_id,))
        conn.commit()
