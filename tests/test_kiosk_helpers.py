from babycontrol import kiosk


def test_format_mmss():
    assert kiosk.format_mmss(0) == "00:00"
    assert kiosk.format_mmss(59.9) == "00:59"
    assert kiosk.format_mmss(1800) == "30:00"
    assert kiosk.format_mmss(-5) == "00:00"


def test_kiosk_no_longer_skips_administrators():
    # shared-account mode: the kiosk must run for every user
    assert not hasattr(kiosk, "is_admin")


# --- regression: BUG-002 (kiosk stole focus from the answer box every second) ---

from unittest.mock import MagicMock  # noqa: E402

from babycontrol.controller import View  # noqa: E402
from babycontrol.timer import AccessState  # noqa: E402


def make_app():
    app = object.__new__(kiosk.KioskApp)       # skip __init__: no real Tk window
    app.tk = MagicMock()
    app.overlay = MagicMock()
    app.overlay.winfo_screenwidth.return_value = 1920
    app.overlay.winfo_screenheight.return_value = 1080
    app.hud = MagicMock()
    app.hud.winfo_screenwidth.return_value = 1920
    app.hud.winfo_reqwidth.return_value = 200
    app.hud_label = MagicMock()
    app.hud_button = MagicMock()
    app.answer_entry = MagicMock()
    app._overlay_visible = False
    app._hud_visible = False
    app._hud_state = None
    app._shown_question = None
    app._feedback = ""
    return app


def test_overlay_grabs_focus_once_not_every_tick():
    app = make_app()
    app._show_overlay()
    app.overlay.focus_displayof.return_value = object()   # focus is inside the overlay
    for _ in range(30):
        app._show_overlay()
    assert app.overlay.focus_force.call_count == 1
    assert app.overlay.deiconify.call_count == 1
    assert app.overlay.geometry.call_count == 1
    app.answer_entry.focus_set.assert_not_called()


def test_overlay_regains_focus_if_another_window_took_it():
    app = make_app()
    app._show_overlay()
    app.overlay.focus_displayof.return_value = None
    app._show_overlay()
    assert app.overlay.focus_force.call_count == 2
    app.answer_entry.focus_set.assert_called_once()


def test_overlay_reshown_after_being_hidden():
    app = make_app()
    app._show_overlay()
    app._hide_overlay()
    app.overlay.withdraw.assert_called_once()
    app._show_overlay()
    assert app.overlay.deiconify.call_count == 2


def test_hud_only_repositioned_when_text_changes():
    app = make_app()
    view = View(AccessState.ALLOWED, 600)
    for _ in range(20):
        app._show_hud(view)
    assert app.hud.geometry.call_count == 1
    assert app.hud.deiconify.call_count == 1
    app._show_hud(View(AccessState.ALLOWED, 540))
    assert app.hud.geometry.call_count == 2
    assert app.hud.deiconify.call_count == 1


def test_progress_text_shows_each_subject():
    view = View(AccessState.NEED_EXERCISE, 0, progress={"math": (1, 3), "english": (0, 2)})
    assert kiosk.progress_text(view) == "Toán 1/3  ·  Tiếng Anh 0/2"


def test_progress_text_hides_disabled_subject_and_has_fallback():
    only_english = View(AccessState.NEED_EXERCISE, 0, progress={"math": (0, 0), "english": (1, 3)})
    assert kiosk.progress_text(only_english) == "Tiếng Anh 1/3"
    no_progress = View(AccessState.NEED_EXERCISE, 0, correct=1, required=4)
    assert kiosk.progress_text(no_progress) == "Đã đúng 1/4"
