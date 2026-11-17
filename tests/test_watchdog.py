from babycontrol.watchdog import Action, SessionInfo, Watchdog


def user(running, session_id=2, name="family"):
    return SessionInfo(session_id, name, running)


def test_running_kiosk_needs_no_action():
    assert Watchdog().evaluate([user(True)], 0) == []


def test_missing_kiosk_is_launched():
    assert Watchdog().evaluate([user(False)], 0) == [(Action.LAUNCH, 2)]


def test_logoff_after_grace_then_resets():
    wd = Watchdog(grace_seconds=30)
    assert wd.evaluate([user(False)], 0) == [(Action.LAUNCH, 2)]
    assert wd.evaluate([user(False)], 25) == [(Action.LAUNCH, 2)]
    assert wd.evaluate([user(False)], 30) == [(Action.LOGOFF, 2)]
    # after logoff the timer restarts
    assert wd.evaluate([user(False)], 35) == [(Action.LAUNCH, 2)]


def test_recovery_resets_timer():
    wd = Watchdog(grace_seconds=30)
    wd.evaluate([user(False)], 0)
    wd.evaluate([user(True)], 20)
    assert wd.evaluate([user(False)], 40) == [(Action.LAUNCH, 2)]


def test_every_user_is_supervised_including_administrators():
    wd = Watchdog(grace_seconds=30)
    sessions = [user(False, 1, "parent-admin"), user(False, 2, "child")]
    assert wd.evaluate(sessions, 0) == [(Action.LAUNCH, 1), (Action.LAUNCH, 2)]


def test_pre_login_sessions_untouched():
    wd = Watchdog(grace_seconds=0)
    login_screen = SessionInfo(3, "", False)
    for t in (0, 100):
        assert wd.evaluate([login_screen], t) == []


def test_missing_kiosk_exe_fails_open():
    wd = Watchdog(grace_seconds=0)
    assert wd.evaluate([user(False)], 100, kiosk_available=False) == []


def test_ended_sessions_are_forgotten():
    wd = Watchdog(grace_seconds=30)
    wd.evaluate([user(False)], 0)
    wd.evaluate([], 10)
    # same session id reused later starts a fresh grace period
    assert wd.evaluate([user(False)], 40) == [(Action.LAUNCH, 2)]
