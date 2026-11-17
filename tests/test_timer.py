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


def test_pause_state(tmp_path):
    t = UsageTracker(tmp_path)
    assert t.pause_remaining(MON) == 0
    t.pause(30, MON)
    assert t.pause_remaining(MON) == 1800
    assert t.pause_remaining(MON + timedelta(minutes=10)) == 1200
    assert access_state(CONFIG, t, MON, False) is AccessState.PARENT_MODE
    # survives restart, wins over the study window, and expires
    t2 = UsageTracker(tmp_path)
    study = datetime(2026, 11, 16, 19, 30)
    t2.pause(60, study)
    assert access_state(CONFIG, t2, study, False) is AccessState.PARENT_MODE
    assert t2.pause_remaining(study + timedelta(minutes=61)) == 0
    t2.end_pause(study)
    assert access_state(CONFIG, t2, study, False) is AccessState.STUDY_OPEN


# --- two processes (kiosk + admin tool) share the file (BUG-003) ---------------

def pair(tmp_path):
    kiosk = UsageTracker(tmp_path, sync_interval=0)
    admin = UsageTracker(tmp_path, sync_interval=0)
    return kiosk, admin


def test_pause_set_by_admin_reaches_the_running_kiosk(tmp_path):
    kiosk, admin = pair(tmp_path)
    run(kiosk, MON, 60)
    admin.pause(30, MON)
    assert kiosk.pause_remaining(MON) == 1800
    assert access_state(CONFIG, kiosk, MON, False) is AccessState.PARENT_MODE


def test_bonus_from_admin_survives_kiosk_saving(tmp_path):
    kiosk, admin = pair(tmp_path)
    mono = run(kiosk, MON, 600)
    admin.add_bonus(900, MON)
    run(kiosk, MON, 120, start_mono=mono)       # kiosk keeps ticking and saving
    expected = 30 * 60 + 900 - 720
    assert kiosk.remaining_seconds(CONFIG, MON) == expected
    assert UsageTracker(tmp_path).remaining_seconds(CONFIG, MON) == expected


def test_stale_admin_never_lowers_kiosk_usage(tmp_path):
    kiosk, admin = pair(tmp_path)               # admin loaded when usage was 0
    run(kiosk, MON, 600)
    admin.add_bonus(60, MON)                    # admin saves after merging
    assert UsageTracker(tmp_path).used_seconds(MON) == 600


def test_extend_pause_only_while_paused(tmp_path):
    kiosk, admin = pair(tmp_path)
    admin.pause(3, MON)
    assert admin.extend_pause(3, MON + timedelta(seconds=30)) is True
    kiosk.end_pause(MON)                        # parent pressed "Kết thúc" on the HUD
    assert admin.extend_pause(3, MON) is False
    assert kiosk.pause_remaining(MON) == 0


def test_unreadable_file_mid_run_keeps_memory_and_heals(tmp_path):
    kiosk = UsageTracker(tmp_path, sync_interval=0)
    mono = run(kiosk, MON, 120)
    (tmp_path / "usage" / "usage.dat").write_bytes(b"edited by the child")
    assert kiosk.used_seconds(MON) == 120       # memory is the truth
    run(kiosk, MON, 60, start_mono=mono)        # next save rewrites a good file
    assert UsageTracker(tmp_path).used_seconds(MON) == 180


def test_day_rolled_by_other_process_is_adopted(tmp_path):
    kiosk, admin = pair(tmp_path)
    run(kiosk, MON, 300)
    tomorrow = MON + timedelta(days=1)
    admin.add_bonus(600, tomorrow)              # admin tool runs the next day
    assert kiosk.used_seconds(tomorrow) == 0
    assert kiosk.remaining_seconds(CONFIG, tomorrow) == 30 * 60 + 600


def test_sync_interval_limits_file_reads(tmp_path, monkeypatch):
    tracker = UsageTracker(tmp_path, sync_interval=60)
    reads = []
    original = tracker._store.read
    monkeypatch.setattr(tracker._store, "read", lambda p: reads.append(p) or original(p))
    for _ in range(20):
        tracker.used_seconds(MON)
    assert reads == []                          # inside the interval: no re-read


def test_pause_is_capped(tmp_path):
    t = UsageTracker(tmp_path)
    t.pause(100 * 60, MON)
    assert t.pause_remaining(MON) == 12 * 3600


def test_usage_is_encrypted_on_disk(tmp_path):
    run(UsageTracker(tmp_path), MON, 300)
    raw = (tmp_path / "usage" / "usage.dat").read_bytes()
    assert b"used_seconds" not in raw and b"paused_until" not in raw


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
