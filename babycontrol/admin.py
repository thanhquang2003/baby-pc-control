"""Parent admin tool (FEAT-006): password-protected settings, study windows,
bonus time and usage history. Run from the parent's (administrator) account.
"""
from __future__ import annotations

import sys
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Callable

from .config import (
    Config, ConfigCorrupt, ConfigError, StudyWindow, load_config, prepare_data_dir,
    save_config,
)
from .timer import UsageTracker

DAY_NAMES = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]


class AuthError(PermissionError):
    """Raised when an action needs a login that has not happened."""


def describe_window(window: StudyWindow) -> str:
    days = ", ".join(DAY_NAMES[d] for d in sorted(window.days))
    return f"{days}  {window.start}-{window.end}"


class AdminSession:
    def __init__(self, base: Path | None = None,
                 now_fn: Callable[[], datetime] = datetime.now) -> None:
        self.base = base
        self._now = now_fn
        try:
            self.config = load_config(base)
            self.corrupt = False
        except ConfigCorrupt:
            # Settings were lost or tampered with. Start from defaults so the
            # parent can set a new password; the child stays locked until then.
            self.config = Config()
            self.corrupt = True
        self.tracker = UsageTracker(base)
        self.authenticated = False

    # --- auth -----------------------------------------------------------
    @property
    def has_password(self) -> bool:
        return bool(self.config.password_hash)

    def set_initial_password(self, password: str) -> None:
        if self.has_password:
            raise AuthError("password already set")
        self.config.set_password(password)
        self._save()
        self.authenticated = True

    def login(self, password: str) -> bool:
        self.authenticated = self.config.verify_password(password)
        return self.authenticated

    def change_password(self, old: str, new: str) -> None:
        self._require_auth()
        if not self.config.verify_password(old):
            raise AuthError("old password is wrong")
        self.config.set_password(new)
        self._save()

    def _require_auth(self) -> None:
        if not self.authenticated:
            raise AuthError("login required")

    def _save(self) -> None:
        prepare_data_dir(self.base)
        save_config(self.config, self.base)

    def _apply(self, new: Config) -> None:
        """Validate+save `new`; keep the old config if it is rejected."""
        old, self.config = self.config, new
        try:
            self._save()
        except ConfigError:
            self.config = old
            raise

    # --- settings -------------------------------------------------------
    def update_settings(self, daily_limit_minutes: int, grade: int,
                        math_questions: int, english_questions: int,
                        block_task_manager: bool | None = None) -> None:
        self._require_auth()
        block = self.config.block_task_manager if block_task_manager is None \
            else block_task_manager
        self._apply(replace(
            self.config, daily_limit_minutes=daily_limit_minutes, grade=grade,
            math_questions=math_questions, english_questions=english_questions,
            block_task_manager=block))

    def add_window(self, days: list[int], start: str, end: str) -> None:
        self._require_auth()
        windows = list(self.config.study_windows) + [StudyWindow(sorted(days), start, end)]
        self._apply(replace(self.config, study_windows=windows))

    def remove_window(self, index: int) -> None:
        self._require_auth()
        windows = list(self.config.study_windows)
        del windows[index]
        self._apply(replace(self.config, study_windows=windows))

    # --- time -----------------------------------------------------------
    def grant_bonus(self, minutes: int) -> None:
        self._require_auth()
        if minutes <= 0:
            raise ConfigError("minutes must be positive")
        self.tracker.add_bonus(minutes * 60, self._now())

    def today_summary(self) -> tuple[int, int]:
        """(used minutes, remaining minutes) for today."""
        now = self._now()
        return (int(self.tracker.used_seconds(now) // 60),
                int(self.tracker.remaining_seconds(self.config, now) // 60))

    def usage_report(self) -> list[tuple[str, int]]:
        """(date, minutes used), newest first."""
        history = self.tracker.history(self._now())
        return [(day, round(sec / 60)) for day, sec in reversed(list(history.items()))]


# --- Tkinter UI (Windows; not unit tested) -----------------------------------

def run_ui(base: Path | None = None) -> None:
    import tkinter as tk
    from tkinter import messagebox, ttk

    session = AdminSession(base)
    root = tk.Tk()
    root.title("BabyControl - Phụ huynh")
    root.geometry("520x460")

    def clear():
        for child in root.winfo_children():
            child.destroy()

    def show_login():
        clear()
        frame = ttk.Frame(root, padding=24)
        frame.pack(expand=True)
        creating = not session.has_password
        if session.corrupt:
            ttk.Label(frame, text="Cài đặt cũ bị hỏng hoặc bị xoá.\nHãy tạo mật khẩu mới "
                      "và đặt lại cài đặt.", foreground="#c62828").pack(pady=8)
        ttk.Label(frame, text="Tạo mật khẩu phụ huynh" if creating else "Nhập mật khẩu",
                  font=("Segoe UI", 14)).pack(pady=8)
        pw = ttk.Entry(frame, show="*", width=24)
        pw.pack(pady=4)
        pw.focus_set()

        def submit(_event=None):
            try:
                if creating:
                    session.set_initial_password(pw.get())
                elif not session.login(pw.get()):
                    messagebox.showerror("Lỗi", "Sai mật khẩu")
                    return
            except (ConfigError, AuthError, OSError) as exc:
                messagebox.showerror("Lỗi", str(exc))
                return
            show_main()

        pw.bind("<Return>", submit)
        ttk.Button(frame, text="Tiếp tục", command=submit).pack(pady=8)

    def guarded(action):
        try:
            action()
            return True
        except (ConfigError, AuthError, OSError, ValueError) as exc:
            messagebox.showerror("Lỗi", str(exc))
            return False

    def show_main():
        clear()
        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)
        cfg = session.config

        # Settings tab
        tab = ttk.Frame(notebook, padding=16)
        notebook.add(tab, text="Cài đặt")
        fields = {}
        for row, (label, key, value, lo, hi) in enumerate([
            ("Phút được dùng mỗi ngày", "limit", cfg.daily_limit_minutes, 1, 1440),
            ("Lớp (1-12)", "grade", cfg.grade, 1, 12),
            ("Số câu Toán mỗi lần", "math", cfg.math_questions, 0, 50),
            ("Số câu Tiếng Anh mỗi lần", "english", cfg.english_questions, 0, 50),
        ]):
            ttk.Label(tab, text=label).grid(row=row, column=0, sticky="w", pady=6)
            var = tk.StringVar(value=str(value))
            ttk.Spinbox(tab, from_=lo, to=hi, textvariable=var, width=8).grid(
                row=row, column=1, padx=12)
            fields[key] = var

        block_tm = tk.BooleanVar(value=cfg.block_task_manager)
        ttk.Checkbutton(tab, text="Chặn Task Manager (Ctrl+Shift+Esc)",
                        variable=block_tm).grid(row=4, column=0, columnspan=2,
                                                sticky="w", pady=6)

        def save_settings():
            def do():
                session.update_settings(
                    int(fields["limit"].get()), int(fields["grade"].get()),
                    int(fields["math"].get()), int(fields["english"].get()),
                    block_tm.get())
            if guarded(do):
                messagebox.showinfo("Đã lưu", "Đã lưu cài đặt")

        ttk.Button(tab, text="Lưu", command=save_settings).grid(row=5, column=0, pady=16)

        # Study windows tab
        tab = ttk.Frame(notebook, padding=16)
        notebook.add(tab, text="Giờ học")
        listbox = tk.Listbox(tab, height=8)
        listbox.pack(fill="x")

        def refresh_windows():
            listbox.delete(0, "end")
            for window in session.config.study_windows:
                listbox.insert("end", describe_window(window))

        def remove_selected():
            sel = listbox.curselection()
            if sel and guarded(lambda: session.remove_window(sel[0])):
                refresh_windows()

        ttk.Button(tab, text="Xoá mục chọn", command=remove_selected).pack(pady=4)
        day_vars = [tk.BooleanVar() for _ in DAY_NAMES]
        days_row = ttk.Frame(tab)
        days_row.pack(pady=4)
        for name, var in zip(DAY_NAMES, day_vars):
            ttk.Checkbutton(days_row, text=name, variable=var).pack(side="left")
        time_row = ttk.Frame(tab)
        time_row.pack(pady=4)
        start_var, end_var = tk.StringVar(value="19:00"), tk.StringVar(value="20:30")
        ttk.Entry(time_row, textvariable=start_var, width=7).pack(side="left")
        ttk.Label(time_row, text=" đến ").pack(side="left")
        ttk.Entry(time_row, textvariable=end_var, width=7).pack(side="left")

        def add_selected():
            days = [i for i, var in enumerate(day_vars) if var.get()]
            if guarded(lambda: session.add_window(days, start_var.get(), end_var.get())):
                refresh_windows()

        ttk.Button(tab, text="Thêm khung giờ học", command=add_selected).pack(pady=4)
        ttk.Label(tab, text="Trong khung giờ học: dùng máy tự do, không cần làm bài, "
                  "không trừ giờ.", wraplength=440).pack(pady=8)
        refresh_windows()

        # Time tab
        tab = ttk.Frame(notebook, padding=16)
        notebook.add(tab, text="Thời gian")
        summary = ttk.Label(tab, font=("Segoe UI", 12))
        summary.pack(anchor="w")
        report = tk.Listbox(tab, height=9)

        def refresh_time():
            used, left = session.today_summary()
            summary.config(text=f"Hôm nay: đã dùng {used} phút, còn {left} phút")
            report.delete(0, "end")
            for day, minutes in session.usage_report():
                report.insert("end", f"{day}: {minutes} phút")

        bonus_row = ttk.Frame(tab)
        bonus_row.pack(anchor="w", pady=8)
        bonus_var = tk.StringVar(value="15")
        ttk.Label(bonus_row, text="Cộng thêm (phút): ").pack(side="left")
        ttk.Spinbox(bonus_row, from_=1, to=240, textvariable=bonus_var, width=6).pack(side="left")

        def grant():
            if guarded(lambda: session.grant_bonus(int(bonus_var.get()))):
                refresh_time()

        ttk.Button(bonus_row, text="Cộng", command=grant).pack(side="left", padx=8)
        ttk.Label(tab, text="Nhật ký sử dụng:").pack(anchor="w")
        report.pack(fill="x")
        refresh_time()

        # Password tab
        tab = ttk.Frame(notebook, padding=16)
        notebook.add(tab, text="Mật khẩu")
        old_var, new_var = tk.StringVar(), tk.StringVar()
        ttk.Label(tab, text="Mật khẩu cũ").pack(anchor="w")
        ttk.Entry(tab, textvariable=old_var, show="*").pack(anchor="w")
        ttk.Label(tab, text="Mật khẩu mới").pack(anchor="w", pady=(8, 0))
        ttk.Entry(tab, textvariable=new_var, show="*").pack(anchor="w")

        def change():
            if guarded(lambda: session.change_password(old_var.get(), new_var.get())):
                messagebox.showinfo("Đã đổi", "Đã đổi mật khẩu")
                old_var.set("")
                new_var.set("")

        ttk.Button(tab, text="Đổi mật khẩu", command=change).pack(pady=12, anchor="w")

    show_login()
    root.mainloop()


def confirm_password(session: AdminSession, ask: Callable[[], str | None],
                     attempts: int = 3) -> bool:
    """Gate for sensitive actions such as uninstalling.

    `ask` returns the typed password, or None if the dialog was cancelled.
    With no password set or unreadable settings there is nothing to protect,
    so the action is allowed (otherwise the parent could never clean up).
    """
    if session.corrupt or not session.has_password:
        return True
    for _ in range(attempts):
        password = ask()
        if password is None:
            return False
        if session.login(password):
            return True
    return False


def run_confirm_ui(base: Path | None = None) -> int:
    """Ask for the parent password in a dialog. Exit code 0 = confirmed."""
    import tkinter as tk
    from tkinter import messagebox, simpledialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    session = AdminSession(base)

    def ask():
        return simpledialog.askstring(
            "BabyControl", "Nhập mật khẩu phụ huynh để tiếp tục:", show="*", parent=root)

    ok = confirm_password(session, ask)
    if not ok:
        messagebox.showerror("BabyControl", "Chưa xác nhận được mật khẩu. Không thực hiện.",
                             parent=root)
    root.destroy()
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--confirm" in argv:
        return run_confirm_ui()
    run_ui()
    return 0


if __name__ == "__main__":
    sys.exit(main())
