import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional


@dataclass(frozen=True)
class Reminder:
    id: int
    title: str
    due_at: datetime
    created_at: datetime
    done_at: Optional[datetime]
    notified_at: Optional[datetime]


class ReminderDb:
    def __init__(self, db_path: str | Path):
        self._db_path = str(db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self._db_path, check_same_thread=False)
        con.row_factory = sqlite3.Row
        return con

    def _init_db(self) -> None:
        with self._connect() as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    due_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    done_at TEXT NULL,
                    notified_at TEXT NULL
                );
                """
            )
            con.execute(
                "CREATE INDEX IF NOT EXISTS idx_reminders_due_at ON reminders(due_at);"
            )

    @staticmethod
    def _dt_to_str(dt: datetime) -> str:
        return dt.isoformat(timespec="seconds")

    @staticmethod
    def _str_to_dt(s: Optional[str]) -> Optional[datetime]:
        if s is None:
            return None
        return datetime.fromisoformat(s)

    def add_reminder(self, title: str, due_at: datetime) -> int:
        now = datetime.now()
        with self._connect() as con:
            cur = con.execute(
                """
                INSERT INTO reminders (title, due_at, created_at, done_at, notified_at)
                VALUES (?, ?, ?, NULL, NULL)
                """,
                (title, self._dt_to_str(due_at), self._dt_to_str(now)),
            )
            return int(cur.lastrowid)

    def mark_done(self, reminder_id: int) -> None:
        now = datetime.now()
        with self._connect() as con:
            con.execute(
                "UPDATE reminders SET done_at = ? WHERE id = ? AND done_at IS NULL",
                (self._dt_to_str(now), reminder_id),
            )

    def get_pending(self) -> list[Reminder]:
        with self._connect() as con:
            rows = con.execute(
                """
                SELECT id, title, due_at, created_at, done_at, notified_at
                FROM reminders
                WHERE done_at IS NULL
                ORDER BY due_at ASC
                """
            ).fetchall()

        return [
            Reminder(
                id=int(r["id"]),
                title=str(r["title"]),
                due_at=datetime.fromisoformat(r["due_at"]),
                created_at=datetime.fromisoformat(r["created_at"]),
                done_at=self._str_to_dt(r["done_at"]),
                notified_at=self._str_to_dt(r["notified_at"]),
            )
            for r in rows
        ]

    def get_due_unnotified(self, now: datetime) -> list[Reminder]:
        with self._connect() as con:
            rows = con.execute(
                """
                SELECT id, title, due_at, created_at, done_at, notified_at
                FROM reminders
                WHERE done_at IS NULL
                  AND notified_at IS NULL
                  AND due_at <= ?
                ORDER BY due_at ASC
                """,
                (self._dt_to_str(now),),
            ).fetchall()

        return [
            Reminder(
                id=int(r["id"]),
                title=str(r["title"]),
                due_at=datetime.fromisoformat(r["due_at"]),
                created_at=datetime.fromisoformat(r["created_at"]),
                done_at=self._str_to_dt(r["done_at"]),
                notified_at=self._str_to_dt(r["notified_at"]),
            )
            for r in rows
        ]

    def mark_notified(self, reminder_ids: Iterable[int]) -> None:
        ids = [int(i) for i in reminder_ids]
        if not ids:
            return

        now = datetime.now()
        placeholders = ",".join(["?"] * len(ids))
        with self._connect() as con:
            con.execute(
                f"UPDATE reminders SET notified_at = ? WHERE id IN ({placeholders})",
                (self._dt_to_str(now), *ids),
            )
