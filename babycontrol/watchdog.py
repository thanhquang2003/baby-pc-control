"""Pure decision logic for the service watchdog (FEAT-005).

The service observes interactive sessions and asks the watchdog what to do.
Administrator sessions are never touched, so the parent can always get in.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

DEFAULT_GRACE_SECONDS = 30.0


class Action(Enum):
    LAUNCH = "launch"    # start the kiosk in that session
    LOGOFF = "logoff"    # kiosk could not be kept running: end the session


@dataclass(frozen=True)
class SessionInfo:
    session_id: int
    username: str
    is_admin: bool
    kiosk_running: bool


class Watchdog:
    def __init__(self, grace_seconds: float = DEFAULT_GRACE_SECONDS) -> None:
        self.grace_seconds = grace_seconds
        self._missing_since: dict[int, float] = {}

    def evaluate(self, sessions: list[SessionInfo], mono: float,
                 kiosk_available: bool = True) -> list[tuple[Action, int]]:
        """Return actions for this cycle.

        If the kiosk executable is missing nothing is done (fail open) so a
        broken install cannot log the child out in a loop.
        """
        actions: list[tuple[Action, int]] = []
        seen = set()
        for s in sessions:
            seen.add(s.session_id)
            if s.is_admin or not s.username or s.kiosk_running or not kiosk_available:
                self._missing_since.pop(s.session_id, None)
                continue
            first = self._missing_since.setdefault(s.session_id, mono)
            if mono - first >= self.grace_seconds:
                actions.append((Action.LOGOFF, s.session_id))
                self._missing_since.pop(s.session_id, None)
            else:
                actions.append((Action.LAUNCH, s.session_id))
        for gone in set(self._missing_since) - seen:
            del self._missing_since[gone]
        return actions
