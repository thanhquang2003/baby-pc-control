"""Kiosk controller: UI-independent logic driven once per second (FEAT-004)."""
from __future__ import annotations

import random
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from .config import Config
from .exercises import ExerciseSession, Question
from .timer import AccessState, UsageTracker, access_state

WARN_5_MIN = 300
WARN_1_MIN = 60
DEFAULT_OVERRIDE_MINUTES = 15


@dataclass
class View:
    state: AccessState
    remaining_seconds: float
    question: Question | None = None
    correct: int = 0
    required: int = 0
    warning: str | None = None   # "5min" | "1min" | None


class KioskController:
    def __init__(self, config: Config | None, tracker: UsageTracker,
                 now_fn: Callable[[], datetime] = datetime.now,
                 mono_fn: Callable[[], float] = time.monotonic,
                 rng: random.Random | None = None) -> None:
        self.config = config
        self.tracker = tracker
        self._now = now_fn
        self._mono = mono_fn
        self._rng = rng
        self.exercises_passed = False
        self.session: ExerciseSession | None = None

    def set_config(self, config: Config | None) -> None:
        """Apply a freshly loaded config (changes take effect immediately).
        None means the config is unreadable: the machine stays locked."""
        self.config = config
        if config is None:
            self.exercises_passed = False
            self.session = None

    def _state(self) -> AccessState:
        return access_state(self.config, self.tracker, self._now(),
                            self.exercises_passed)

    def update(self) -> View:
        """Advance the clock by one tick and return what the UI should show."""
        if self.config is None:
            return View(AccessState.CONFIG_ERROR, 0.0)
        now = self._now()
        state = self._state()
        self.tracker.tick(now, self._mono(),
                          active=state is AccessState.ALLOWED,
                          study_time=state is AccessState.STUDY_OPEN)
        state = self._state()          # quota may have run out during the tick
        if state is AccessState.NO_QUOTA:
            self.exercises_passed = False
            self.session = None
        elif state is AccessState.NEED_EXERCISE and self.session is None:
            self.session = ExerciseSession(
                self.config.grade, self.config.math_questions,
                self.config.english_questions, self._rng)
        remaining = self.tracker.remaining_seconds(self.config, now)
        warning = None
        if state is AccessState.ALLOWED:
            if remaining <= WARN_1_MIN:
                warning = "1min"
            elif remaining <= WARN_5_MIN:
                warning = "5min"
        session = self.session
        return View(
            state=state,
            remaining_seconds=remaining,
            question=session.current if session else None,
            correct=session.correct if session else 0,
            required=session.required_correct if session else 0,
            warning=warning,
        )

    def submit(self, response: str) -> bool | None:
        """Grade an answer. None if no exercise is active."""
        if self.session is None:
            return None
        ok = self.session.submit(response)
        if self.session.passed:
            self.exercises_passed = True
            self.session = None
        return ok

    def parent_override(self, password: str,
                        minutes: int = DEFAULT_OVERRIDE_MINUTES) -> bool:
        """Parent password grants extra minutes today and skips the exercises."""
        if self.config is None or not self.config.verify_password(password):
            return False
        self.tracker.add_bonus(minutes * 60, self._now())
        self.exercises_passed = True
        self.session = None
        return True
