"""Daily usage timer and access decision (FEAT-003).

Usage is counted only while the child's session is active and outside study
windows. State is persisted atomically so it survives reboots. Turning the
system clock back cannot reset the day: the latest date ever seen wins.
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime
from enum import Enum
from pathlib import Path

from .config import Config, usage_dir

# A gap longer than this between ticks (sleep, hibernate, service stop) is not
# counted as usage beyond this cap.
MAX_TICK_SECONDS = 120


class AccessState(Enum):
    STUDY_OPEN = "study_open"          # study window: free access, no quota used
    NEED_EXERCISE = "need_exercise"    # must pass exercises first
    ALLOWED = "allowed"                # exercises passed and quota remains
    NO_QUOTA = "no_quota"              # today's time is used up


class UsageTracker:
    def __init__(self, base: Path | None = None) -> None:
        self._path = (base or usage_dir()) / "usage.json"
        self._last_mono: float | None = None
        self._state = self._load()

    # --- persistence ----------------------------------------------------
    def _load(self) -> dict:
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            return {
                "date": raw["date"],
                "max_date_seen": raw.get("max_date_seen", raw["date"]),
                "used_seconds": float(raw.get("used_seconds", 0)),
                "bonus_seconds": float(raw.get("bonus_seconds", 0)),
            }
        except (OSError, ValueError, KeyError):
            return {"date": "", "max_date_seen": "", "used_seconds": 0.0,
                    "bonus_seconds": 0.0}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._state), encoding="utf-8")
        os.replace(tmp, self._path)

    # --- day rollover ---------------------------------------------------
    def _roll(self, now: datetime) -> None:
        today = now.date().isoformat()
        effective = max(today, self._state["max_date_seen"])
        self._state["max_date_seen"] = effective
        if self._state["date"] != effective:
            self._state.update(date=effective, used_seconds=0.0, bonus_seconds=0.0)

    # --- public API -----------------------------------------------------
    def used_seconds(self, now: datetime) -> float:
        self._roll(now)
        return self._state["used_seconds"]

    def remaining_seconds(self, config: Config, now: datetime) -> float:
        self._roll(now)
        total = config.daily_limit_minutes * 60 + self._state["bonus_seconds"]
        return max(0.0, total - self._state["used_seconds"])

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
    if config.is_study_time(now):
        return AccessState.STUDY_OPEN
    if tracker.remaining_seconds(config, now) <= 0:
        return AccessState.NO_QUOTA
    if not exercises_passed:
        return AccessState.NEED_EXERCISE
    return AccessState.ALLOWED
