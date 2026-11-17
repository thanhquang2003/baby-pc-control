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


def test_corrupt_config_lets_parent_start_over(admin, tmp_path):
    (tmp_path / "config.dat").write_bytes(b"junk")
    (tmp_path / "config.bak").write_bytes(b"junk")
    session = AdminSession(tmp_path)
    assert session.corrupt and not session.has_password
    session.set_initial_password("newpass")
    assert not AdminSession(tmp_path).corrupt
    assert AdminSession(tmp_path).login("newpass")


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
