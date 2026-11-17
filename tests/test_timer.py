from datetime import datetime, timedelta

from babycontrol.config import Config, StudyWindow
from babycontrol.timer import (
    MAX_TICK_SECONDS, AccessState, UsageTracker, access_state,
)

MON = datetime(2026, 11, 16, 16, 0)   # Monday afternoon, outside any window
CONFIG = Config(daily_limit_minutes=30,
                study_windows=[StudyWindow([0], "19:00", "20:30")])


def run(tracker, now, seconds, step=60, active=True, study=False, start_mono=0.0):
    mono = start_mono
    tracker.tick(now, mono, active, study)
    for _ in range(int(seconds // step)):
        mono += step
        tracker.tick(now, mono, active, study)
    return mono


def test_counts_active_time(tmp_path):
    t = UsageTracker(tmp_path)
    run(t, MON, 600)
    assert t.used_seconds(MON) == 600
    assert t.remaining_seconds(CONFIG, MON) == 30 * 60 - 600


def test_inactive_and_study_time_not_counted(tmp_path):
    t = UsageTracker(tmp_path)
    run(t, MON, 300, active=False)
    run(t, MON, 300, study=True)
    assert t.used_seconds(MON) == 0


def test_long_gap_is_capped(tmp_path):
    t = UsageTracker(tmp_path)
    t.tick(MON, 0.0, True, False)
    t.tick(MON, 10_000.0, True, False)  # machine slept
    assert t.used_seconds(MON) == MAX_TICK_SECONDS


def test_persists_across_restart(tmp_path):
    run(UsageTracker(tmp_path), MON, 300)
    assert UsageTracker(tmp_path).used_seconds(MON) == 300


def test_resets_next_day(tmp_path):
    t = UsageTracker(tmp_path)
    run(t, MON, 600)
    tomorrow = MON + timedelta(days=1)
    assert t.used_seconds(tomorrow) == 0
    assert t.remaining_seconds(CONFIG, tomorrow) == 30 * 60


def test_clock_rollback_does_not_reset(tmp_path):
    t = UsageTracker(tmp_path)
    tomorrow = MON + timedelta(days=1)
    run(t, tomorrow, 600)
    assert t.used_seconds(MON) == 600          # clock set back to yesterday
    assert UsageTracker(tmp_path).used_seconds(MON) == 600


def test_bonus_extends_quota_and_resets_daily(tmp_path):
    t = UsageTracker(tmp_path)
    run(t, MON, 30 * 60)
    assert t.remaining_seconds(CONFIG, MON) == 0
    t.add_bonus(600, MON)
    t.add_bonus(-500, MON)                      # negative ignored
    assert t.remaining_seconds(CONFIG, MON) == 600
    assert t.remaining_seconds(CONFIG, MON + timedelta(days=1)) == 30 * 60


def test_usage_is_encrypted_on_disk(tmp_path):
    run(UsageTracker(tmp_path), MON, 300)
    raw = (tmp_path / "usage" / "usage.dat").read_bytes()
    assert b"used_seconds" not in raw and b"300" not in raw


def test_fresh_install_starts_at_zero(tmp_path):
    assert UsageTracker(tmp_path).used_seconds(MON) == 0


def test_tampered_usage_fails_closed(tmp_path):
    run(UsageTracker(tmp_path), MON, 60)
    (tmp_path / "usage" / "usage.dat").write_bytes(b"edited")
    (tmp_path / "usage" / "usage.bak").write_bytes(b"edited")
    t = UsageTracker(tmp_path)
    assert t.remaining_seconds(CONFIG, MON) == 0
    # a new day starts clean again
    assert t.remaining_seconds(CONFIG, MON + timedelta(days=1)) == 30 * 60


def test_deleting_one_copy_keeps_usage(tmp_path):
    run(UsageTracker(tmp_path), MON, 300)
    (tmp_path / "usage" / "usage.dat").unlink()
    assert UsageTracker(tmp_path).used_seconds(MON) == 300


def test_legacy_plain_usage_is_read(tmp_path):
    (tmp_path / "usage").mkdir()
    (tmp_path / "usage" / "usage.json").write_text(
        '{"date": "2026-11-16", "used_seconds": 120}')
    assert UsageTracker(tmp_path).used_seconds(MON) == 120


def test_unwritable_storage_does_not_crash(tmp_path):
    t = UsageTracker(tmp_path / "missing" / "deeper")
    (tmp_path / "missing").write_text("a file blocks the directory")
    run(t, MON, 120)
    assert t.used_seconds(MON) == 120      # still counted in memory


def test_access_states(tmp_path):
    t = UsageTracker(tmp_path)
    assert access_state(CONFIG, t, MON, False) is AccessState.NEED_EXERCISE
    assert access_state(CONFIG, t, MON, True) is AccessState.ALLOWED
    study = datetime(2026, 11, 16, 19, 30)
    assert access_state(CONFIG, t, study, False) is AccessState.STUDY_OPEN
    run(t, MON, 30 * 60)
    assert access_state(CONFIG, t, MON, True) is AccessState.NO_QUOTA
    # study window stays open even with no quota left
    assert access_state(CONFIG, t, study, False) is AccessState.STUDY_OPEN
