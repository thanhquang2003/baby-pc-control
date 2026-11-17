"""BabyControl Windows service (FEAT-005). Windows only; needs pywin32.

Runs as SYSTEM. A service lives in session 0 and cannot show UI, so it only
supervises: every few seconds it makes sure the kiosk runs in each interactive
session (restarting it if it is closed) and logs the session off if the kiosk
cannot be kept running. It also applies the "block Task Manager" setting.
Parent and child may share one account; the parent uses the password on the
lock screen (parent mode).

Install:  scripts\\install_service.ps1     Remove: scripts\\uninstall_service.ps1
"""
from __future__ import annotations

import csv
import io
import os
import subprocess
import sys
import time
from pathlib import Path

from datetime import datetime

from .blocklist import effective_blocklist, flush_dns, kill_blocked, sync_hosts
from .config import load_config, prepare_data_dir
from .timer import UsageTracker
from .watchdog import Action, SessionInfo, Watchdog

CYCLE_SECONDS = 3
KIOSK_EXE = "babycontrol-kiosk.exe"
CREATE_NO_WINDOW = 0x08000000

if sys.platform == "win32":
    import servicemanager
    import win32event
    import win32profile
    import win32process
    import win32security
    import win32service
    import win32serviceutil
    import win32ts
    import winreg
    import win32con


def kiosk_path() -> Path:
    """The kiosk exe next to this exe (frozen), or None-equivalent if absent."""
    base = Path(sys.executable).parent if getattr(sys, "frozen", False) \
        else Path(__file__).resolve().parent.parent / "dist"
    return base / KIOSK_EXE


def parse_tasklist_sessions(csv_text: str) -> set[int]:
    """Session numbers from `tasklist /FO CSV /NH` output."""
    sessions = set()
    for row in csv.reader(io.StringIO(csv_text)):
        if len(row) >= 4 and row[3].strip().isdigit():
            sessions.add(int(row[3]))
    return sessions


def kiosk_sessions() -> set[int]:
    out = subprocess.run(
        ["tasklist", "/FI", f"IMAGENAME eq {KIOSK_EXE}", "/FO", "CSV", "/NH"],
        capture_output=True, text=True, creationflags=CREATE_NO_WINDOW, timeout=20,
    ).stdout
    return parse_tasklist_sessions(out)


def _user_sid_string(session_id: int) -> str:
    token = win32ts.WTSQueryUserToken(session_id)
    user_sid = win32security.GetTokenInformation(token, win32security.TokenUser)[0]
    return win32security.ConvertSidToStringSid(user_sid)


def observe_sessions() -> tuple[list[SessionInfo], dict[int, str]]:
    running = kiosk_sessions()
    sessions, sids = [], {}
    for entry in win32ts.WTSEnumerateSessions(win32ts.WTS_CURRENT_SERVER_HANDLE, 1, 0):
        if entry["State"] != win32ts.WTSActive:
            continue
        sid = entry["SessionId"]
        username = win32ts.WTSQuerySessionInformation(
            win32ts.WTS_CURRENT_SERVER_HANDLE, sid, win32ts.WTSUserName)
        if not username:
            continue
        try:
            sids[sid] = _user_sid_string(sid)
        except Exception:
            continue
        sessions.append(SessionInfo(sid, username, sid in running))
    return sessions, sids


def launch_kiosk(session_id: int) -> None:
    exe = kiosk_path()
    token = win32ts.WTSQueryUserToken(session_id)
    primary = win32security.DuplicateTokenEx(
        token, win32security.SecurityImpersonation, win32con.MAXIMUM_ALLOWED,
        win32security.TokenPrimary)
    env = win32profile.CreateEnvironmentBlock(primary, False)
    startup = win32process.STARTUPINFO()
    startup.lpDesktop = "winsta0\\default"
    win32process.CreateProcessAsUser(
        primary, None, f'"{exe}"', None, None, False,
        win32con.CREATE_UNICODE_ENVIRONMENT | win32con.NORMAL_PRIORITY_CLASS,
        env, str(exe.parent), startup)


def set_task_manager_blocked(user_sid: str, blocked: bool) -> None:
    """Best effort: set or clear the per-user DisableTaskMgr policy."""
    try:
        with winreg.CreateKey(
                winreg.HKEY_USERS,
                rf"{user_sid}\Software\Microsoft\Windows\CurrentVersion\Policies\System") as key:
            if blocked:
                winreg.SetValueEx(key, "DisableTaskMgr", 0, winreg.REG_DWORD, 1)
            else:
                try:
                    winreg.DeleteValue(key, "DisableTaskMgr")
                except FileNotFoundError:
                    pass
    except OSError:
        pass


def task_manager_should_be_blocked() -> bool:
    """Config flag; if the config is unreadable, block (fail closed)."""
    try:
        return load_config().block_task_manager
    except Exception:
        return True


def log_error(message: str) -> None:
    try:
        servicemanager.LogErrorMsg(message)
    except Exception:
        pass


class BabyControlService(win32serviceutil.ServiceFramework if sys.platform == "win32"
                         else object):
    _svc_name_ = "BabyControl"
    _svc_display_name_ = "BabyControl"
    _svc_description_ = "Parental control: supervises the kiosk in child sessions."

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self._stop_event = win32event.CreateEvent(None, 0, 0, None)
        self._watchdog = Watchdog()
        self._tracker = UsageTracker()     # read-only use: is parent mode active?

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self._stop_event)

    def SvcDoRun(self):
        servicemanager.LogInfoMsg("BabyControl service started")
        try:
            prepare_data_dir()
        except Exception as exc:
            log_error(f"prepare_data_dir failed: {exc}")
        while win32event.WaitForSingleObject(self._stop_event, CYCLE_SECONDS * 1000) \
                != win32event.WAIT_OBJECT_0:
            try:
                self.cycle()
            except Exception as exc:   # never let the loop die
                log_error(f"watchdog cycle failed: {exc}")
            try:
                self.enforce_blocklist()
            except Exception as exc:
                log_error(f"blocklist enforcement failed: {exc}")
        servicemanager.LogInfoMsg("BabyControl service stopped")

    def enforce_blocklist(self) -> None:
        """Kill blocked apps and keep the hosts file in line with the blocked
        sites. If the config is unreadable nothing changes (last state stays)."""
        try:
            config = load_config()
        except Exception:
            return
        parent_mode = self._tracker.pause_remaining(datetime.now()) > 0
        apps, sites = effective_blocklist(config, parent_mode)
        kill_blocked(apps)
        sync_hosts(sites, flush=flush_dns)

    def cycle(self) -> None:
        sessions, sids = observe_sessions()
        blocked = task_manager_should_be_blocked()
        for session in sessions:
            set_task_manager_blocked(sids[session.session_id], blocked)
        actions = self._watchdog.evaluate(
            sessions, time.monotonic(), kiosk_available=kiosk_path().exists())
        for action, session_id in actions:
            if action is Action.LAUNCH:
                try:
                    launch_kiosk(session_id)
                except Exception as exc:
                    log_error(f"launch kiosk failed in session {session_id}: {exc}")
            else:
                log_error(f"kiosk not running in session {session_id}; logging off")
                win32ts.WTSLogoffSession(win32ts.WTS_CURRENT_SERVER_HANDLE, session_id, False)


def main() -> None:
    if sys.platform != "win32":
        sys.exit("The BabyControl service only runs on Windows.")
    if len(sys.argv) == 1:   # started by the Service Control Manager
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(BabyControlService)
        servicemanager.StartServiceCtrlDispatcher()
    else:                    # install / start / stop / remove from a console
        win32serviceutil.HandleCommandLine(BabyControlService)


if __name__ == "__main__":
    main()
