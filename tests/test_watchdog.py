from babycontrol.watchdog import Action, SessionInfo, Watchdog

CHILD = dict(session_id=2, username="bé")


def child(running):
    return SessionInfo(is_admin=False, kiosk_running=running, **CHILD)


def test_running_kiosk_needs_no_action():
    assert Watchdog().evaluate([child(True)], 0) == []


def test_missing_kiosk_is_launched():
    assert Watchdog().evaluate([child(False)], 0) == [(Action.LAUNCH, 2)]


def test_logoff_after_grace_then_resets():
    wd = Watchdog(grace_seconds=30)
    assert wd.evaluate([child(False)], 0) == [(Action.LAUNCH, 2)]
    assert wd.evaluate([child(False)], 25) == [(Action.LAUNCH, 2)]
    assert wd.evaluate([child(False)], 30) == [(Action.LOGOFF, 2)]
    # after logoff the timer restarts
    assert wd.evaluate([child(False)], 35) == [(Action.LAUNCH, 2)]


def test_recovery_resets_timer():
    wd = Watchdog(grace_seconds=30)
    wd.evaluate([child(False)], 0)
    wd.evaluate([child(True)], 20)
    assert wd.evaluate([child(False)], 40) == [(Action.LAUNCH, 2)]


def test_admin_and_pre_login_sessions_untouched():
    wd = Watchdog(grace_seconds=0)
    admin = SessionInfo(1, "parent", True, False)
    login_screen = SessionInfo(3, "", False, False)
    for t in (0, 100):
        assert wd.evaluate([admin, login_screen], t) == []


def test_missing_kiosk_exe_fails_open():
    wd = Watchdog(grace_seconds=0)
    assert wd.evaluate([child(False)], 100, kiosk_available=False) == []


def test_ended_sessions_are_forgotten():
    wd = Watchdog(grace_seconds=30)
    wd.evaluate([child(False)], 0)
    wd.evaluate([], 10)
    # same session id reused later starts a fresh grace period
    assert wd.evaluate([child(False)], 40) == [(Action.LAUNCH, 2)]
