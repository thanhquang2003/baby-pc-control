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
import shutil
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, time
from pathlib import Path

from .secure_store import SecureStore, StoreError

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


def usage_dir(base: Path | None = None) -> Path:
    """Sub-directory the child's kiosk may write (usage counters only)."""
    return (base or data_dir()) / "usage"


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
    math_questions: int = 3      # correct Math answers needed per unlock
    english_questions: int = 2   # correct English answers needed per unlock
    block_task_manager: bool = True   # disable Task Manager for supervised users
    study_windows: list[StudyWindow] = field(default_factory=list)
    password_salt: str = ""
    password_hash: str = ""

    def validate(self) -> None:
        if not 1 <= self.daily_limit_minutes <= 24 * 60:
            raise ConfigError("daily_limit_minutes must be 1..1440")
        if not 1 <= self.grade <= 12:
            raise ConfigError("grade must be 1..12")
        for name in ("math_questions", "english_questions"):
            if not 0 <= getattr(self, name) <= 50:
                raise ConfigError(f"{name} must be 0..50")
        if self.math_questions + self.english_questions < 1:
            raise ConfigError("at least one question per unlock is required")
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


class ConfigCorrupt(Exception):
    """Config exists (or must exist) but cannot be read. Callers must fail
    closed (lock the machine) instead of falling back to defaults."""


def config_path(base: Path | None = None) -> Path:
    return (base or data_dir()) / "config.dat"


def _backup_path(base: Path | None) -> Path:
    return (base or data_dir()) / "config.bak"


def _legacy_path(base: Path | None) -> Path:
    return (base or data_dir()) / "config.json"   # plain JSON written by v1


# --- "was configured" marker -------------------------------------------------
# Lets us tell "fresh install" from "config deleted by the child". On Windows it
# is a registry value; elsewhere (dev/tests) a file under the data directory.

_REG_KEY = r"SOFTWARE\BabyControl"


def is_configured(base: Path | None = None) -> bool:
    if sys.platform == "win32" and base is None:
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _REG_KEY, 0,
                                winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
                return bool(winreg.QueryValueEx(key, "Configured")[0])
        except OSError:
            return False
    return ((base or data_dir()) / ".configured").exists()


def mark_configured(base: Path | None = None) -> None:
    if sys.platform == "win32" and base is None:
        import winreg
        try:
            with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, _REG_KEY, 0,
                                    winreg.KEY_WRITE | winreg.KEY_WOW64_64KEY) as key:
                winreg.SetValueEx(key, "Configured", 0, winreg.REG_DWORD, 1)
        except OSError:
            pass
        return
    root = base or data_dir()
    root.mkdir(parents=True, exist_ok=True)
    (root / ".configured").write_text("1")


def _config_from_json(text: str) -> Config:
    raw = json.loads(text)
    windows = [StudyWindow(**w) for w in raw.pop("study_windows", [])]
    config = Config(study_windows=windows, **raw)
    config.validate()
    return config


def load_config(base: Path | None = None) -> Config:
    """Load config.

    Fresh install (nothing stored, never configured) returns defaults. If a
    config was stored but can't be read (deleted, corrupt, edited) the backup is
    tried, and if that fails ConfigCorrupt is raised.
    """
    root = base or data_dir()
    store = SecureStore(root)
    problems = []
    found_any = False
    for path in (config_path(base), _backup_path(base)):
        try:
            data = store.read(path)
        except StoreError as exc:
            found_any = True
            problems.append(str(exc))
            continue
        if data is None:
            continue
        found_any = True
        try:
            return _config_from_json(data.decode("utf-8"))
        except (ValueError, TypeError, ConfigError) as exc:
            problems.append(f"{path.name}: {exc}")
    legacy = _legacy_path(base)
    if legacy.exists():   # v1 plain config: usable, re-encrypted on next save
        try:
            return _config_from_json(legacy.read_text(encoding="utf-8"))
        except (ValueError, TypeError, ConfigError, OSError) as exc:
            raise ConfigCorrupt(f"legacy config unreadable: {exc}") from exc
    if found_any or is_configured(base):
        raise ConfigCorrupt("; ".join(problems) or "configuration is missing")
    return Config()


def save_config(config: Config, base: Path | None = None) -> Path:
    """Validate, then write config encrypted, keeping the previous as .bak."""
    config.validate()
    path = config_path(base)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        shutil.copy2(path, _backup_path(base))
    SecureStore(path.parent).write(
        path, json.dumps(asdict(config), ensure_ascii=False).encode("utf-8"))
    legacy = _legacy_path(base)
    if legacy.exists():
        legacy.unlink()
    mark_configured(base)
    harden_acl(path.parent)
    return path


def prepare_data_dir(base: Path | None = None) -> Path:
    """Create the data directory tree and lock it down. Run as admin/SYSTEM."""
    root = base or data_dir()
    usage_dir(root).mkdir(parents=True, exist_ok=True)
    harden_acl(root)
    return root


def harden_acl(directory: Path) -> None:
    """Windows: admins/SYSTEM full control, other users read-only, except the
    `usage` sub-directory which users may modify. No-op elsewhere."""
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
    usage = usage_dir(directory)
    if usage.exists():
        subprocess.run(
            ["icacls", str(usage), "/grant:r", "*S-1-5-32-545:(OI)(CI)M"],
            check=False,
            capture_output=True,
        )
