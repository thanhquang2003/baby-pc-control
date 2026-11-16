"""Configuration and storage (FEAT-001).

Config lives in a JSON file under a data directory that only the admin
account can write (ACL hardened on Windows). The child's account may read it.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, time
from pathlib import Path

DEFAULT_DAILY_LIMIT_MINUTES = 30
PBKDF2_ITERATIONS = 200_000


class ConfigError(ValueError):
    """Raised when configuration values are invalid."""


def data_dir() -> Path:
    """Directory holding config and usage state."""
    override = os.environ.get("BABYCONTROL_HOME")
    if override:
        return Path(override)
    if sys.platform == "win32":
        return Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "BabyControl"
    return Path.home() / ".babycontrol"


def parse_hhmm(value: str) -> time:
    try:
        hour, minute = value.split(":")
        return time(int(hour), int(minute))
    except (ValueError, AttributeError) as exc:
        raise ConfigError(f"Invalid time {value!r}, expected HH:MM") from exc


@dataclass
class StudyWindow:
    """A weekly open-access period. days: 0=Monday ... 6=Sunday."""

    days: list[int]
    start: str
    end: str

    def validate(self) -> None:
        if not self.days or any(d not in range(7) for d in self.days):
            raise ConfigError("days must be a non-empty list of 0..6")
        if parse_hhmm(self.start) >= parse_hhmm(self.end):
            raise ConfigError("start must be earlier than end")

    def contains(self, now: datetime) -> bool:
        if now.weekday() not in self.days:
            return False
        return parse_hhmm(self.start) <= now.time() < parse_hhmm(self.end)


@dataclass
class Config:
    daily_limit_minutes: int = DEFAULT_DAILY_LIMIT_MINUTES
    grade: int = 3
    required_correct: int = 5
    study_windows: list[StudyWindow] = field(default_factory=list)
    password_salt: str = ""
    password_hash: str = ""

    def validate(self) -> None:
        if not 1 <= self.daily_limit_minutes <= 24 * 60:
            raise ConfigError("daily_limit_minutes must be 1..1440")
        if not 1 <= self.grade <= 12:
            raise ConfigError("grade must be 1..12")
        if not 1 <= self.required_correct <= 50:
            raise ConfigError("required_correct must be 1..50")
        for window in self.study_windows:
            window.validate()

    def is_study_time(self, now: datetime) -> bool:
        return any(w.contains(now) for w in self.study_windows)

    # --- admin password -------------------------------------------------
    def set_password(self, password: str) -> None:
        if len(password) < 4:
            raise ConfigError("password must be at least 4 characters")
        salt = secrets.token_bytes(16)
        self.password_salt = salt.hex()
        self.password_hash = _hash_password(password, salt)

    def verify_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        digest = _hash_password(password, bytes.fromhex(self.password_salt))
        return hmac.compare_digest(digest, self.password_hash)


def _hash_password(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    ).hex()


def config_path(base: Path | None = None) -> Path:
    return (base or data_dir()) / "config.json"


def load_config(base: Path | None = None) -> Config:
    """Load config, returning defaults if missing."""
    path = config_path(base)
    if not path.exists():
        return Config()
    raw = json.loads(path.read_text(encoding="utf-8"))
    windows = [StudyWindow(**w) for w in raw.pop("study_windows", [])]
    config = Config(study_windows=windows, **raw)
    config.validate()
    return config


def save_config(config: Config, base: Path | None = None) -> Path:
    """Validate then atomically write config."""
    config.validate()
    path = config_path(base)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(asdict(config), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    os.replace(tmp, path)
    harden_acl(path.parent)
    return path


def harden_acl(directory: Path) -> None:
    """Windows: admins/SYSTEM full control, other users read-only. No-op elsewhere."""
    if sys.platform != "win32":
        return
    subprocess.run(
        [
            "icacls", str(directory), "/inheritance:r",
            "/grant:r", "*S-1-5-18:(OI)(CI)F",        # SYSTEM
            "/grant:r", "*S-1-5-32-544:(OI)(CI)F",    # Administrators
            "/grant:r", "*S-1-5-32-545:(OI)(CI)RX",   # Users: read/execute
        ],
        check=False,
        capture_output=True,
    )
