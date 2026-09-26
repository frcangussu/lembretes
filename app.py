import sys
import threading
from datetime import datetime
from pathlib import Path

try:
    import pystray
    from PIL import Image, ImageDraw
except Exception:  # noqa: BLE001
    pystray = None  # type: ignore[assignment]
    Image = None  # type: ignore[assignment]
    ImageDraw = None  # type: ignore[assignment]

from db import ReminderDb
from scheduler import ReminderScheduler
from ui import UiController


def _default_db_path() -> Path:
    base = Path(__file__).resolve().parent
    return base / "lembrete.db"


def _make_icon_image():
    if Image is None or ImageDraw is None:
        raise RuntimeError("Pillow não está disponível")
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((6, 6, size - 6, size - 6), fill=(34, 197, 94, 255))
    d.rectangle((18, 18, size - 18, size - 18), outline=(255, 255, 255, 255), width=4)
    d.line((32, 22, 32, 34), fill=(255, 255, 255, 255), width=4)
    d.line((32, 32, 42, 42), fill=(255, 255, 255, 255), width=4)
    return img


class App:
    def __init__(self) -> None:
        self._db = ReminderDb(_default_db_path())
        self._ui = UiController(self._db)

        self._scheduler = ReminderScheduler(self._db, on_due=self._on_due)
        self._scheduler.start()

        self._icon = None
        if pystray is not None:
            self._icon = pystray.Icon(
                "lembrete",
                _make_icon_image(),
                "Lembretes",
                menu=pystray.Menu(
                    pystray.MenuItem("Ver pendentes", self._open_pending),
                    pystray.MenuItem("Adicionar lembrete...", self._add_quick),
                    pystray.MenuItem("Sair", self._exit),
                ),
            )

        self._show_overdue_on_startup()

    def run(self) -> None:
        if self._icon is not None:
            self._icon.run()
            return

        self._ui.show_pending_list()
        stop_evt = threading.Event()
        try:
            stop_evt.wait()
        except KeyboardInterrupt:
            self._exit()

    def _show_overdue_on_startup(self) -> None:
        now = datetime.now()
        due = self._db.get_due_unnotified(now)
        if not due:
            return

        self._db.mark_notified([r.id for r in due])
        self._on_due(due)
        self._ui.show_pending_list()

    def _on_due(self, reminders) -> None:
        if not reminders:
            return

        if len(reminders) == 1:
            r = reminders[0]
            msg = f"{r.title}\n\nVencimento: {r.due_at.strftime('%Y-%m-%d %H:%M:%S')}"
        else:
            msg = f"Você tem {len(reminders)} lembretes vencidos agora."

        self._ui.show_notification(
            title="Lembrete",
            message=msg,
            on_click=self._ui.show_pending_list,
        )

    def _open_pending(self, _icon=None, _item=None) -> None:
        self._ui.show_pending_list()

    def _add_quick(self, _icon=None, _item=None) -> None:
        self._ui.show_pending_list()

    def _exit(self, _icon=None, _item=None) -> None:
        self._scheduler.stop()
        if self._icon is not None:
            self._icon.stop()


def main() -> int:
    app = App()
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
