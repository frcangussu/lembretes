import threading
import tkinter as tk
from datetime import datetime
from tkinter import ttk, messagebox

from db import ReminderDb

try:
    from tkcalendar import DateEntry
except Exception:  # noqa: BLE001
    DateEntry = None  # type: ignore[assignment]


class UiController:
    def __init__(self, db: ReminderDb):
        self._db = db
        self._root: tk.Tk | None = None
        self._list_win: tk.Toplevel | None = None
        self._tree: ttk.Treeview | None = None

        self._ui_thread = threading.Thread(target=self._ui_main, name="TkUI", daemon=True)
        self._ready = threading.Event()
        self._ui_thread.start()
        self._ready.wait(10)

    def _ui_main(self) -> None:
        root = tk.Tk()
        root.withdraw()
        root.title("Lembretes")
        root.protocol("WM_DELETE_WINDOW", root.withdraw)
        self._root = root
        self._ready.set()
        root.mainloop()

    def _on_ui_thread(self, fn):
        if self._root is None:
            return
        self._root.after(0, fn)

    def _focus_window(self, win: tk.Toplevel) -> None:
        win.deiconify()
        win.lift()
        win.attributes("-topmost", True)
        win.attributes("-topmost", False)
        win.focus_force()

    def show_pending_list(self) -> None:
        def _show():
            if self._root is None:
                return

            if self._list_win is not None and self._list_win.winfo_exists():
                self._focus_window(self._list_win)
                self._refresh_tree()
                return

            win = tk.Toplevel(self._root)
            win.title("Lembretes pendentes")
            win.geometry("650x360")
            def _close_pending(_evt=None):
                if self._list_win is win:
                    self._list_win = None
                    self._tree = None
                win.destroy()

            win.protocol("WM_DELETE_WINDOW", _close_pending)
            win.bind("<Escape>", lambda _e: (_close_pending(), "break")[1])

            cols = ("done", "title", "due")
            tree = ttk.Treeview(win, columns=cols, show="headings", selectmode="browse")
            tree.heading("done", text="")
            tree.heading("title", text="Título")
            tree.heading("due", text="Horário")
            tree.column("done", width=40, anchor="center", stretch=False)
            tree.column("title", width=450)
            tree.column("due", width=160, anchor="center")

            tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            tree.bind("<ButtonRelease-1>", self._on_tree_click)

            win.bind("<Control-plus>", lambda _e: self._open_add_dialog())
            win.bind("<Control-equal>", lambda _e: self._open_add_dialog())
            win.bind("<Control-KP_Add>", lambda _e: self._open_add_dialog())

            btns = ttk.Frame(win)
            btns.pack(fill=tk.X, padx=10, pady=(0, 10))

            ttk.Button(btns, text="Adicionar", command=self._open_add_dialog).pack(side=tk.LEFT)
            ttk.Button(btns, text="Atualizar", command=self._refresh_tree).pack(side=tk.LEFT)

            self._list_win = win
            self._tree = tree
            self._refresh_tree()
            self._focus_window(win)

        self._on_ui_thread(_show)

    def _refresh_tree(self) -> None:
        if self._tree is None:
            return

        for item in self._tree.get_children():
            self._tree.delete(item)

        for r in self._db.get_pending():
            self._tree.insert(
                "",
                "end",
                iid=str(r.id),
                values=("✔", r.title, r.due_at.strftime("%Y-%m-%d %H:%M:%S")),
            )

    def _on_tree_click(self, event) -> None:
        if self._tree is None:
            return

        region = self._tree.identify("region", event.x, event.y)
        if region != "cell":
            return

        column = self._tree.identify_column(event.x)
        if column != "#1":
            return

        item_id = self._tree.identify_row(event.y)
        if not item_id:
            return

        reminder_id = int(item_id)
        self._db.mark_done(reminder_id)
        self._refresh_tree()

    def _open_add_dialog(self) -> None:
        if self._root is None:
            return

        win = tk.Toplevel(self._root)
        win.title("Adicionar lembrete")
        win.geometry("520x230")
        win.transient(self._list_win if self._list_win is not None else self._root)
        win.grab_set()
        win.bind("<Escape>", lambda _e: win.destroy())
        self._focus_window(win)

        frm = ttk.Frame(win)
        frm.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        ttk.Label(frm, text="Título:").grid(row=0, column=0, sticky="w")
        title_var = tk.StringVar()
        ttk.Entry(frm, textvariable=title_var, width=52).grid(row=0, column=1, sticky="ew")

        ttk.Label(frm, text="Data:").grid(row=1, column=0, sticky="w", pady=(10, 0))
        if DateEntry is not None:
            date_entry = DateEntry(frm, width=20, date_pattern="dd/mm/yyyy")
            date_entry.grid(row=1, column=1, sticky="w", pady=(10, 0))
            date_entry.set_date(datetime.now().date())
        else:
            date_var = tk.StringVar()
            date_var.set(datetime.now().strftime("%d/%m/%Y"))
            date_entry = ttk.Entry(frm, textvariable=date_var, width=22)
            date_entry.grid(row=1, column=1, sticky="w", pady=(10, 0))

            def _format_date(evt=None):
                if evt is not None and evt.keysym in {
                    "Left",
                    "Right",
                    "Up",
                    "Down",
                    "Home",
                    "End",
                    "Tab",
                    "Shift_L",
                    "Shift_R",
                    "Control_L",
                    "Control_R",
                    "Alt_L",
                    "Alt_R",
                }:
                    return
                raw = "".join(ch for ch in date_var.get() if ch.isdigit())
                raw = raw[:8]
                if len(raw) <= 2:
                    formatted = raw
                elif len(raw) <= 4:
                    formatted = raw[:2] + "/" + raw[2:]
                else:
                    formatted = raw[:2] + "/" + raw[2:4] + "/" + raw[4:]
                if formatted != date_var.get():
                    date_var.set(formatted)
                    date_entry.icursor(tk.END)

            date_entry.bind("<KeyRelease>", _format_date)

        ttk.Label(frm, text="Hora (HH:MM):").grid(row=2, column=0, sticky="w", pady=(10, 0))
        time_var = tk.StringVar()
        time_entry = ttk.Entry(frm, textvariable=time_var, width=10)
        time_entry.grid(row=2, column=1, sticky="w", pady=(10, 0))

        def _format_time(_evt=None):
            raw = "".join(ch for ch in time_var.get() if ch.isdigit())
            raw = raw[:4]
            if len(raw) <= 2:
                formatted = raw
            else:
                formatted = raw[:2] + ":" + raw[2:]
            if formatted != time_var.get():
                time_var.set(formatted)

        time_entry.bind("<KeyRelease>", _format_time)

        frm.columnconfigure(1, weight=1)

        def _add():
            title = title_var.get().strip()
            if not title:
                messagebox.showerror("Erro", "Informe um título.")
                return

            if DateEntry is not None:
                selected_date = date_entry.get_date()
                date_s = selected_date.strftime("%d/%m/%Y")
            else:
                date_s = str(getattr(date_entry, "get")()).strip()

            time_s = time_var.get().strip()

            if not date_s:
                messagebox.showerror("Erro", "Informe uma data.")
                return
            if len(date_s) != 10 or date_s[2] != "/" or date_s[5] != "/":
                messagebox.showerror("Erro", "Informe a data no formato DD/MM/AAAA")
                return
            if len(time_s) != 5 or time_s[2] != ":":
                messagebox.showerror("Erro", "Informe a hora no formato HH:MM")
                return

            try:
                dt = datetime.strptime(date_s, "%d/%m/%Y")
                t = datetime.strptime(time_s, "%H:%M").time()
                due_at = dt.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
            except ValueError:
                messagebox.showerror("Erro", "Data ou hora inválida.")
                return

            self._db.add_reminder(title=title, due_at=due_at)
            win.destroy()
            self._refresh_tree()

        btns = ttk.Frame(frm)
        btns.grid(row=3, column=0, columnspan=2, sticky="e", pady=(14, 0))
        ttk.Button(btns, text="Cancelar", command=win.destroy).pack(side=tk.RIGHT)
        ttk.Button(btns, text="Adicionar", command=_add).pack(side=tk.RIGHT, padx=(0, 8))

    def show_notification(self, title: str, message: str, on_click) -> None:
        def _show():
            if self._root is None:
                return

            win = tk.Toplevel(self._root)
            win.title(title)
            win.attributes("-topmost", True)
            win.resizable(False, False)

            sw = win.winfo_screenwidth()
            sh = win.winfo_screenheight()
            w, h = 360, 120
            x = sw - w - 20
            y = sh - h - 60
            win.geometry(f"{w}x{h}+{x}+{y}")

            frm = ttk.Frame(win, padding=10)
            frm.pack(fill=tk.BOTH, expand=True)

            ttk.Label(frm, text=message, wraplength=330).pack(anchor="w")

            def _clicked(_evt=None):
                win.destroy()
                on_click()

            frm.bind("<Button-1>", _clicked)
            for child in frm.winfo_children():
                child.bind("<Button-1>", _clicked)

            ttk.Button(frm, text="Ver pendentes", command=_clicked).pack(anchor="e", pady=(10, 0))

            win.after(15000, win.destroy)

        self._on_ui_thread(_show)
