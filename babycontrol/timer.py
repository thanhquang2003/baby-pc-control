"""Daily usage timer and access decision (FEAT-003).

Usage is counted only while the child's session is active and outside study
windows. State is persisted atomically so it survives reboots. Turning the
system clock back cannot reset the day: the latest date ever seen wins.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

from .config import Config, data_dir, usage_dir
from .secure_store import SecureStore, StoreError

EXHAUSTED_SECONDS = 24 * 3600   # used when usage data was tampered with

# A gap longer than this between ticks (sleep, hibernate, service stop) is not
# counted as usage beyond this cap.
MAX_TICK_SECONDS = 120
HISTORY_DAYS = 60
MAX_PAUSE_SECONDS = 12 * 3600   # cap on parent mode, also limits clock-rollback abuse


class AccessState(Enum):
    STUDY_OPEN = "study_open"          # study window: free access, no quota used
    NEED_EXERCISE = "need_exercise"    # must pass exercises first
    ALLOWED = "allowed"                # exercises passed and quota remains
    NO_QUOTA = "no_quota"              # today's time is used up
    CONFIG_ERROR = "config_error"      # settings unreadable/tampered: stay locked
    PARENT_MODE = "parent_mode"        # parent unlocked the PC with the password
    NOT_SET_UP = "not_set_up"          # no parent password yet: do not lock anyone out


class UsageTracker:
    def __init__(self, root: Path | None = None) -> None:
        """`root` is the BabyControl data directory (holds the key); usage
        data is stored encrypted under `root/usage`."""
        root = root or data_dir()
        self._store = SecureStore(root)
        folder = usage_dir(root)
        self._path = folder / "usage.dat"
        self._bak = folder / "usage.bak"
        self._legacy = folder / "usage.json"      # plain file written by v1
        self._last_mono: float | None = None
        self._corrupt = False
        self._state = self._load()

    # --- persistence ----------------------------------------------------
    @staticmethod
    def _fresh() -> dict:
        return {"date": "", "max_date_seen": "", "used_seconds": 0.0,
                "bonus_seconds": 0.0, "history": {}, "paused_until": ""}

    @staticmethod
    def _parse(raw: dict) -> dict:
        return {
            "date": raw["date"],
            "max_date_seen": raw.get("max_date_seen", raw["date"]),
            "used_seconds": float(raw.get("used_seconds", 0)),
            "bonus_seconds": float(raw.get("bonus_seconds", 0)),
            "history": {str(k): float(v) for k, v in raw.get("history", {}).items()},
            "paused_until": str(raw.get("paused_until", "")),
        }

    def _load(self) -> dict:
        """Newest readable copy wins. If data exists but none is readable
        (deleted copy is covered by the backup; garbage/edited is not), fail
        closed: today's quota is treated as used up."""
        unreadable = False
        for path in (self._path, self._bak):
            try:
                data = self._store.read(path)
            except StoreError:
                unreadable = True
                continue
            if data is None:
                continue
            try:
                return self._parse(json.loads(data))
            except (ValueError, KeyError, AttributeError, TypeError):
                unreadable = True
        if self._legacy.exists():
            try:
                return self._parse(json.loads(self._legacy.read_text(encoding="utf-8")))
            except (OSError, ValueError, KeyError, AttributeError, TypeError):
                unreadable = True
        self._corrupt = unreadable
        return self._fresh()

    def _save(self) -> None:
        """Best effort: the counter keeps working in memory if the disk write
        fails (e.g. read-only directory)."""
        data = json.dumps(self._state).encode("utf-8")
        try:
            self._store.write(self._path, data)
            self._store.write(self._bak, data)
            if self._legacy.exists():
                self._legacy.unlink()
        except (OSError, StoreError):
            pass

    # --- day rollover ---------------------------------------------------
    def _roll(self, now: datetime) -> None:
        today = now.date().isoformat()
        effective = max(today, self._state["max_date_seen"])
        self._state["max_date_seen"] = effective
        if self._corrupt:
            self._corrupt = False
            self._state.update(date=effective, used_seconds=EXHAUSTED_SECONDS,
                               bonus_seconds=0.0)
            return
        if self._state["date"] != effective:
            previous = self._state["date"]
            if previous and self._state["used_seconds"] > 0:
                history = self._state["history"]
                history[previous] = round(self._state["used_seconds"])
                for old in sorted(history)[:-HISTORY_DAYS]:
                    del history[old]
            self._state.update(date=effective, used_seconds=0.0, bonus_seconds=0.0)

    # --- public API -----------------------------------------------------
    def used_seconds(self, now: datetime) -> float:
        self._roll(now)
        return self._state["used_seconds"]

    def remaining_seconds(self, config: Config, now: datetime) -> float:
        self._roll(now)
        total = config.daily_limit_minutes * 60 + self._state["bonus_seconds"]
        return max(0.0, total - self._state["used_seconds"])

    def pause(self, minutes: float, now: datetime) -> None:
        """Parent mode: no quota counted and no lock for `minutes` (capped)."""
        self._roll(now)
        seconds = min(max(0.0, minutes * 60), MAX_PAUSE_SECONDS)
        self._state["paused_until"] = (now + timedelta(seconds=seconds)).isoformat()
        self._save()

    def pause_remaining(self, now: datetime) -> float:
        self._roll(now)
        try:
            until = datetime.fromisoformat(self._state["paused_until"])
            return min(max(0.0, (until - now).total_seconds()), MAX_PAUSE_SECONDS)
        except (ValueError, TypeError):   # empty or unreadable value, or tz mismatch
            return 0.0

    def end_pause(self, now: datetime) -> None:
        self._roll(now)
        self._state["paused_until"] = ""
        self._save()

    def history(self, now: datetime) -> dict[str, float]:
        """Seconds used per day (finished days plus today), oldest first."""
        self._roll(now)
        result = dict(self._state["history"])
        if self._state["used_seconds"] > 0:
            result[self._state["date"]] = self._state["used_seconds"]
        return dict(sorted(result.items()))

    def add_bonus(self, seconds: float, now: datetime) -> None:
        """Parent grants extra time for today (negative values are ignored)."""
        self._roll(now)
        self._state["bonus_seconds"] += max(0.0, seconds)
        self._save()

    def tick(self, now: datetime, mono: float, active: bool, study_time: bool) -> float:
        """Record elapsed time since the previous tick. Returns seconds counted.

        `mono` is a monotonic clock reading (time.monotonic()). Time is counted
        only when the session is active and it is not a study window.
        """
        self._roll(now)
        counted = 0.0
        if self._last_mono is not None and active and not study_time:
            counted = min(max(0.0, mono - self._last_mono), MAX_TICK_SECONDS)
            self._state["used_seconds"] += counted
        self._last_mono = mono
        self._save()
        return counted


def access_state(config: Config, tracker: UsageTracker, now: datetime,
                 exercises_passed: bool) -> AccessState:
    """Decide what the child may do right now."""
    if tracker.pause_remaining(now) > 0:
        return AccessState.PARENT_MODE
    if config.is_study_time(now):
        return AccessState.STUDY_OPEN
    if tracker.remaining_seconds(config, now) <= 0:
        return AccessState.NO_QUOTA
    if not exercises_passed:
        return AccessState.NEED_EXERCISE
    return AccessState.ALLOWED
