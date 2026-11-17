from datetime import datetime, timedelta

import pytest

from babycontrol.admin import AdminSession, AuthError, describe_window
from babycontrol.config import ConfigError, StudyWindow, load_config
from babycontrol.timer import UsageTracker

NOW = datetime(2026, 11, 16, 16, 0)


@pytest.fixture
def admin(tmp_path):
    session = AdminSession(tmp_path, now_fn=lambda: NOW)
    session.set_initial_password("parent")
    return session


def test_first_run_sets_password_and_logs_in(tmp_path):
    session = AdminSession(tmp_path)
    assert not session.has_password
    session.set_initial_password("parent")
    assert session.authenticated
    again = AdminSession(tmp_path)
    assert again.has_password and not again.authenticated
    assert again.login("parent") and not AdminSession(tmp_path).login("nope")


def kiosk_view(tmp_path):
    return UsageTracker(tmp_path, sync_interval=0)


def test_creating_the_password_does_not_lock_until_the_tool_closes(admin, tmp_path):
    kiosk = kiosk_view(tmp_path)
    assert kiosk.pause_remaining(NOW) == 180      # PARENT_SESSION_MINUTES
    admin.end_parent_session()                    # parent closes the tool
    assert kiosk.pause_remaining(NOW) == 0        # supervision applies from now on


def test_keep_alive_renews_the_parent_session(tmp_path):
    clock = [NOW]
    session = AdminSession(tmp_path, now_fn=lambda: clock[0])
    session.set_initial_password("parent")
    kiosk = kiosk_view(tmp_path)
    clock[0] = NOW + timedelta(seconds=150)       # almost expired...
    assert kiosk.pause_remaining(clock[0]) == 30
    session.keep_alive()
    assert kiosk.pause_remaining(clock[0]) == 180


def test_crashed_tool_leaves_supervision_off_only_briefly(admin, tmp_path):
    kiosk = kiosk_view(tmp_path)
    assert kiosk.pause_remaining(NOW + timedelta(minutes=4)) == 0   # no keep_alive


def test_closing_does_not_end_a_longer_parent_mode_chosen_on_the_lock_screen(tmp_path):
    kiosk = kiosk_view(tmp_path)
    kiosk.pause(60, NOW)                          # parent chose 60 min on the lock screen
    session = AdminSession(tmp_path, now_fn=lambda: NOW)
    session.set_initial_password("parent")
    assert kiosk.pause_remaining(NOW) == 3600     # not shortened to 3 minutes
    session.end_parent_session()
    assert kiosk.pause_remaining(NOW) == 3600     # and not ended


def test_logging_in_starts_a_parent_session_only_when_asked(admin, tmp_path):
    admin.end_parent_session()
    again = AdminSession(tmp_path, now_fn=lambda: NOW)
    assert again.login("parent")                  # e.g. the uninstall confirmation
    assert kiosk_view(tmp_path).pause_remaining(NOW) == 0
    again.begin_parent_session()
    assert kiosk_view(tmp_path).pause_remaining(NOW) == 180
    again.end_parent_session()
    assert kiosk_view(tmp_path).pause_remaining(NOW) == 0


def test_corrupt_config_lets_parent_start_over(admin, tmp_path):
    (tmp_path / "config.dat").write_bytes(b"junk")
    (tmp_path / "config.bak").write_bytes(b"junk")
    session = AdminSession(tmp_path)
    assert session.corrupt and not session.has_password
    session.set_initial_password("newpass")
    assert not AdminSession(tmp_path).corrupt
    assert AdminSession(tmp_path).login("newpass")


def feed(*answers):
    items = list(answers)
    return lambda: items.pop(0) if items else None


def test_confirm_password_flow(admin, tmp_path):
    from babycontrol.admin import confirm_password
    fresh = lambda: AdminSession(tmp_path)          # noqa: E731
    assert confirm_password(fresh(), feed("parent"))
    assert confirm_password(fresh(), feed("bad", "bad", "parent"))   # third try
    assert not confirm_password(fresh(), feed("bad", "bad", "bad", "parent"))
    assert not confirm_password(fresh(), feed(None))                 # cancelled


def test_confirm_allowed_when_nothing_to_protect(tmp_path):
    from babycontrol.admin import confirm_password
    assert confirm_password(AdminSession(tmp_path), feed())          # no password yet
    (tmp_path / "config.dat").write_bytes(b"junk")
    (tmp_path / "config.bak").write_bytes(b"junk")
    (tmp_path / ".configured").write_text("1")
    assert confirm_password(AdminSession(tmp_path), feed())          # unreadable config


def test_cannot_reset_existing_password(admin):
    with pytest.raises(AuthError):
        admin.set_initial_password("other")


def test_actions_require_login(tmp_path):
    session = AdminSession(tmp_path)
    session.set_initial_password("parent")
    fresh = AdminSession(tmp_path)
    for call in (lambda: fresh.update_settings(30, 3, 3, 2),
                 lambda: fresh.add_window([0], "19:00", "20:00"),
                 lambda: fresh.remove_window(0),
                 lambda: fresh.grant_bonus(10),
                 lambda: fresh.change_password("parent", "newpw")):
        with pytest.raises(AuthError):
            call()


def test_update_settings_persists(admin, tmp_path):
    admin.update_settings(45, 6, 4, 3)
    loaded = load_config(tmp_path)
    assert (loaded.daily_limit_minutes, loaded.grade) == (45, 6)
    assert (loaded.math_questions, loaded.english_questions) == (4, 3)
    assert loaded.verify_password("parent")


def test_task_manager_flag(admin, tmp_path):
    assert load_config(tmp_path).block_task_manager is True
    admin.update_settings(30, 3, 3, 2, block_task_manager=False)
    assert load_config(tmp_path).block_task_manager is False
    admin.update_settings(30, 3, 3, 2)          # unspecified keeps the value
    assert load_config(tmp_path).block_task_manager is False


def test_invalid_settings_rejected_and_not_saved(admin, tmp_path):
    with pytest.raises(ConfigError):
        admin.update_settings(0, 3, 3, 2)
    assert admin.config.daily_limit_minutes == 30
    assert load_config(tmp_path).daily_limit_minutes == 30


def test_add_and_remove_windows(admin, tmp_path):
    admin.add_window([2, 0], "19:00", "20:30")
    admin.add_window([5, 6], "09:00", "11:00")
    windows = load_config(tmp_path).study_windows
    assert windows[0].days == [0, 2]
    assert [describe_window(w) for w in windows] == [
        "T2, T4  19:00-20:30", "T7, CN  09:00-11:00"]
    admin.remove_window(0)
    assert len(load_config(tmp_path).study_windows) == 1


def test_invalid_window_rejected(admin):
    with pytest.raises(ConfigError):
        admin.add_window([], "19:00", "20:00")
    with pytest.raises(ConfigError):
        admin.add_window([0], "20:00", "19:00")
    assert admin.config.study_windows == []


def test_change_password(admin, tmp_path):
    with pytest.raises(AuthError):
        admin.change_password("wrong", "newpw")
    admin.change_password("parent", "newpw")
    assert load_config(tmp_path).verify_password("newpw")


def test_grant_bonus_and_summary(admin):
    admin.grant_bonus(15)
    used, left = admin.today_summary()
    assert (used, left) == (0, 45)
    with pytest.raises(ConfigError):
        admin.grant_bonus(0)


def test_usage_report_lists_finished_days_and_today(tmp_path):
    tracker = UsageTracker(tmp_path)
    yesterday = NOW - timedelta(days=1)
    tracker.tick(yesterday, 0.0, True, False)
    tracker.tick(yesterday, 60.0, True, False)
    tracker.tick(NOW, 120.0, True, False)
    tracker.tick(NOW, 180.0, True, False)
    session = AdminSession(tmp_path, now_fn=lambda: NOW)
    # today: the tick right after midnight rollover also counts the 60s gap
    assert session.usage_report() == [("2026-11-16", 2), ("2026-11-15", 1)]
