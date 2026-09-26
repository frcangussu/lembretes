import threading
import time
from datetime import datetime
from typing import Callable

from db import ReminderDb, Reminder


class ReminderScheduler:
    def __init__(
        self,
        db: ReminderDb,
        on_due: Callable[[list[Reminder]], None],
        poll_seconds: float = 20.0,
    ):
        self._db = db
        self._on_due = on_due
        self._poll_seconds = poll_seconds
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, name="ReminderScheduler", daemon=True)

    def start(self) -> None:
        if self._thread.is_alive():
            return
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def _run(self) -> None:
        while not self._stop_event.is_set():
            now = datetime.now()
            due = self._db.get_due_unnotified(now)
            if due:
                try:
                    self._on_due(due)
                finally:
                    self._db.mark_notified([r.id for r in due])

            self._stop_event.wait(self._poll_seconds)
