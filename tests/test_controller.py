import random
from datetime import datetime, timedelta

import pytest

from babycontrol.config import Config, StudyWindow
from babycontrol.controller import KioskController
from babycontrol.timer import AccessState, UsageTracker

START = datetime(2026, 11, 16, 16, 0)   # Monday 16:00, outside study windows


class Clock:
    def __init__(self, now=START):
        self.now = now
        self.mono = 1000.0

    def advance(self, seconds):
        self.now += timedelta(seconds=seconds)
        self.mono += seconds


@pytest.fixture
def setup(tmp_path):
    clock = Clock()
    config = Config(daily_limit_minutes=10, math_questions=1, english_questions=1,
                    study_windows=[StudyWindow([0], "19:00", "20:30")])
    config.set_password("parent")
    ctl = KioskController(config, UsageTracker(tmp_path), lambda: clock.now,
                          lambda: clock.mono, random.Random(1))
    return ctl, clock


def pass_exercises(ctl):
    view = ctl.update()
    while view.question is not None:
        ctl.submit(view.question.answer)
        view = ctl.update()
    return view


def test_starts_locked_with_exercise(setup):
    ctl, _ = setup
    view = ctl.update()
    assert view.state is AccessState.NEED_EXERCISE
    assert view.question is not None and view.required == 2


def test_no_time_counted_while_doing_exercises(setup):
    ctl, clock = setup
    ctl.update()
    for _ in range(5):
        clock.advance(60)
        ctl.update()
    assert ctl.tracker.used_seconds(clock.now) == 0


def test_wrong_answer_keeps_locked(setup):
    ctl, _ = setup
    ctl.update()
    assert ctl.submit("wrong ###") is False
    assert ctl.update().state is AccessState.NEED_EXERCISE


def test_passing_unlocks_and_counts_time(setup):
    ctl, clock = setup
    view = pass_exercises(ctl)
    assert view.state is AccessState.ALLOWED
    clock.advance(60)
    view = ctl.update()
    assert view.remaining_seconds == 540


def test_quota_exhaustion_relocks_and_resets_exercises(setup):
    ctl, clock = setup
    pass_exercises(ctl)
    for _ in range(10):
        clock.advance(60)
        view = ctl.update()
    assert view.state is AccessState.NO_QUOTA
    assert view.question is None
    assert ctl.exercises_passed is False


def test_warnings(setup):
    ctl, clock = setup
    pass_exercises(ctl)
    warnings = []
    for _ in range(9):                      # 10-minute quota, one minute per step
        clock.advance(60)
        warnings.append(ctl.update().warning)
    # minutes used 1..4 -> >5 min left; 5..8 -> 5min warning; 9 -> 1 min left
    assert warnings == [None] * 4 + ["5min"] * 4 + ["1min"]


def test_study_window_free_access_and_no_usage(setup):
    ctl, clock = setup
    clock.now = datetime(2026, 11, 16, 19, 30)
    view = ctl.update()
    assert view.state is AccessState.STUDY_OPEN
    clock.advance(60)
    ctl.update()
    assert ctl.tracker.used_seconds(clock.now) == 0


def test_parent_override(setup):
    ctl, clock = setup
    pass_exercises(ctl)
    for _ in range(10):
        clock.advance(60)
        ctl.update()
    assert ctl.update().state is AccessState.NO_QUOTA
    assert ctl.parent_override("wrong") is False
    assert ctl.update().state is AccessState.NO_QUOTA
    assert ctl.parent_override("parent", 15) is True
    view = ctl.update()
    assert view.state is AccessState.ALLOWED
    assert view.remaining_seconds == 15 * 60


def test_unreadable_config_locks_and_recovers(setup):
    ctl, clock = setup
    pass_exercises(ctl)
    ctl.set_config(None)
    view = ctl.update()
    assert view.state is AccessState.CONFIG_ERROR and view.question is None
    assert ctl.parent_override("parent") is False
    fixed = Config(daily_limit_minutes=10, math_questions=1, english_questions=1)
    ctl.set_config(fixed)
    assert ctl.update().state is AccessState.NEED_EXERCISE   # must redo exercises


def test_submit_without_session_returns_none(setup):
    ctl, _ = setup
    pass_exercises(ctl)
    assert ctl.submit("x") is None


def test_config_change_takes_effect(setup):
    ctl, clock = setup
    pass_exercises(ctl)
    clock.advance(60)
    ctl.update()
    new = Config(daily_limit_minutes=1, math_questions=1, english_questions=1)
    ctl.set_config(new)
    assert ctl.update().state is AccessState.NO_QUOTA
