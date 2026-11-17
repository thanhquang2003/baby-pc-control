"""Full-screen kiosk (FEAT-004, FEAT-008).

Runs in the user's desktop session (started by the service, see service.py).
Shows the exercise screen while locked, a small countdown while allowed, and a
"time is up" screen when the daily quota is used. Parent and child may share
the account: the parent enters the password on the lock screen to add time or
to switch to parent mode (free use for a while, nothing counted).
"""
from __future__ import annotations

import sys
from pathlib import Path

from .config import ConfigCorrupt, ConfigError, load_config
from .controller import (
    DEFAULT_OVERRIDE_MINUTES, DEFAULT_PARENT_MODE_MINUTES, KioskController, View,
)
from .timer import AccessState, UsageTracker

CONFIG_RELOAD_EVERY = 10   # ticks (seconds)
BG = "#1e2a3a"
FG = "#ffffff"


def format_mmss(seconds: float) -> str:
    seconds = max(0, int(seconds))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


class KioskApp:
    def __init__(self, base: Path | None = None) -> None:
        import tkinter as tk
        self.tk = tk
        self.base = base
        try:
            config = load_config(base)
        except ConfigCorrupt:
            config = None   # fail closed: stay locked until the config is fixed
        self.controller = KioskController(config, UsageTracker(base))
        self._ticks = 0
        self._shown_question = None
        self._feedback = ""

        self.root = tk.Tk()
        self.root.withdraw()
        self.overlay = self._build_overlay()
        self.hud = self._build_hud()

    # --- construction ---------------------------------------------------
    def _build_overlay(self):
        tk = self.tk
        win = tk.Toplevel(self.root, bg=BG)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.protocol("WM_DELETE_WINDOW", lambda: None)
        win.bind("<Alt-F4>", lambda e: "break")
        win.withdraw()
        self.body = tk.Frame(win, bg=BG)
        self.body.place(relx=0.5, rely=0.45, anchor="center")
        self.footer = tk.Frame(win, bg=BG)
        self.footer.place(relx=0.5, rely=0.95, anchor="s")
        tk.Label(self.footer, text="Phụ huynh:", bg=BG, fg="#9fb3c8").pack(side="left")
        self.pw_entry = tk.Entry(self.footer, show="*", width=14)
        self.pw_entry.pack(side="left", padx=6)
        tk.Button(self.footer, text=f"Thêm {DEFAULT_OVERRIDE_MINUTES} phút",
                  command=self._on_override).pack(side="left")
        tk.Button(self.footer,
                  text=f"Bố mẹ dùng máy {DEFAULT_PARENT_MODE_MINUTES // 60} giờ",
                  command=self._on_parent_mode).pack(side="left", padx=6)
        self.override_msg = tk.Label(self.footer, text="", bg=BG, fg="#ff8a80")
        self.override_msg.pack(side="left", padx=8)
        return win

    def _build_hud(self):
        tk = self.tk
        win = tk.Toplevel(self.root, bg="#000000")
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.withdraw()
        self.hud_label = tk.Label(win, text="", bg="#000000", fg="#7CFC00",
                                  font=("Segoe UI", 14, "bold"), padx=10, pady=4)
        self.hud_label.pack(side="left")
        self.hud_button = tk.Button(win, text="Kết thúc", command=self._on_end_parent)
        return win

    # --- rendering ------------------------------------------------------
    def _clear_body(self) -> None:
        for child in self.body.winfo_children():
            child.destroy()

    def _label(self, text, size=20, color=FG, **kw):
        lbl = self.tk.Label(self.body, text=text, bg=BG, fg=color,
                            font=("Segoe UI", size), wraplength=900, **kw)
        lbl.pack(pady=8)
        return lbl

    def _render_exercise(self, view: View) -> None:
        question = view.question
        if question is self._shown_question:
            return
        self._shown_question = question
        self._clear_body()
        tk = self.tk
        self._label("Làm bài để mở máy", 32, "#ffd54f")
        self._label(f"Đã đúng {view.correct}/{view.required}", 16, "#9fb3c8")
        self._label(question.prompt, 28)
        if question.choices:
            for choice in question.choices:
                tk.Button(self.body, text=choice, font=("Segoe UI", 18), width=28,
                          command=lambda c=choice: self._on_answer(c)).pack(pady=4)
        else:
            self.answer_entry = tk.Entry(self.body, font=("Segoe UI", 24), width=12,
                                         justify="center")
            self.answer_entry.pack(pady=8)
            self.answer_entry.bind(
                "<Return>", lambda e: self._on_answer(self.answer_entry.get()))
            tk.Button(self.body, text="Trả lời", font=("Segoe UI", 18),
                      command=lambda: self._on_answer(self.answer_entry.get())).pack()
            self.answer_entry.focus_set()
        self._label(self._feedback, 16, "#ff8a80")

    def _render_time_up(self) -> None:
        self._shown_question = None
        self._clear_body()
        self._label("Hết giờ dùng máy hôm nay", 36, "#ffd54f")
        self._label("Hẹn con ngày mai nhé!", 22)

    def _render_config_error(self) -> None:
        self._shown_question = None
        self._clear_body()
        self._label("Máy đang bị khoá", 36, "#ff8a80")
        self._label("Không đọc được cài đặt. Nhờ bố mẹ kiểm tra giúp con nhé.", 22)

    def _show_overlay(self) -> None:
        win = self.overlay
        win.geometry(f"{win.winfo_screenwidth()}x{win.winfo_screenheight()}+0+0")
        win.deiconify()
        win.lift()
        win.attributes("-topmost", True)
        win.focus_force()

    def _render(self, view: View) -> None:
        if view.state is AccessState.NEED_EXERCISE and view.question is not None:
            self._show_overlay()
            self._render_exercise(view)
            self.hud.withdraw()
        elif view.state is AccessState.NO_QUOTA:
            self._show_overlay()
            self._render_time_up()
            self.hud.withdraw()
        elif view.state is AccessState.CONFIG_ERROR:
            self._show_overlay()
            self._render_config_error()
            self.hud.withdraw()
        else:
            self.overlay.withdraw()
            self._shown_question = None
            self._feedback = ""
            self._show_hud(view)

    def _show_hud(self, view: View) -> None:
        if view.state is AccessState.STUDY_OPEN:
            self.hud.withdraw()
            return
        color = {"5min": "#ffd54f", "1min": "#ff5252"}.get(view.warning, "#7CFC00")
        if view.state is AccessState.PARENT_MODE:
            text = f"Chế độ bố mẹ: còn {format_mmss(view.remaining_seconds)}"
            self.hud_button.pack(side="left", padx=4)
        else:
            text = f"Còn {format_mmss(view.remaining_seconds)}"
            self.hud_button.pack_forget()
        self.hud_label.config(text=text, fg=color)
        self.hud.update_idletasks()
        width = self.hud.winfo_reqwidth()
        self.hud.geometry(f"+{self.hud.winfo_screenwidth() - width - 12}+8")
        self.hud.deiconify()
        self.hud.attributes("-topmost", True)
        self.hud.lift()

    # --- events ---------------------------------------------------------
    def _on_answer(self, response: str) -> None:
        ok = self.controller.submit(response)
        self._feedback = "" if ok or ok is None else "Chưa đúng, thử câu khác nhé!"
        self._shown_question = None   # force redraw (new question or unlocked)
        self._tick(reschedule=False)

    def _on_override(self) -> None:
        self._parent_action(self.controller.parent_override)

    def _on_parent_mode(self) -> None:
        self._parent_action(self.controller.parent_pause)

    def _on_end_parent(self) -> None:
        self.controller.end_parent_mode()
        self._tick(reschedule=False)

    def _parent_action(self, action) -> None:
        if action(self.pw_entry.get()):
            self.override_msg.config(text="")
        else:
            self.override_msg.config(text="Sai mật khẩu")
        self.pw_entry.delete(0, "end")
        self._tick(reschedule=False)

    def _tick(self, reschedule: bool = True) -> None:
        self._ticks += 1
        if self._ticks % CONFIG_RELOAD_EVERY == 0:
            try:
                self.controller.set_config(load_config(self.base))
            except ConfigCorrupt:
                self.controller.set_config(None)   # tampered/deleted: lock
            except (ConfigError, OSError, ValueError):
                pass   # transient read problem: keep the last good config
        self._render(self.controller.update())
        if reschedule:
            self.root.after(1000, self._tick)

    def run(self) -> None:
        self._tick()
        self.root.mainloop()


def main() -> int:
    KioskApp().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
