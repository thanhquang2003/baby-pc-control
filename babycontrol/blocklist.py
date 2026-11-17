"""Blocking games/apps and websites chosen by the parent (FEAT-013).

Pure helpers plus two small enforcement functions that the service calls:
 - apps: processes whose image name is on the list are killed every few seconds
 - sites: a marked block in the Windows hosts file points the domains (and their
   www. form) at the local machine, which works in every browser.

Known limits (also in the README): an app can be renamed, a site reached through
a VPN/proxy or Firefox/Chrome "secure DNS" overrides, and hosts blocks whole
domains only (not a single page).
"""
from __future__ import annotations

import csv
import io
import os
import re
import stat
import subprocess
import sys
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit

MAX_ENTRIES = 200
HOSTS_BEGIN = "# BEGIN BabyControl (do not edit between these lines)"
HOSTS_END = "# END BabyControl"
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


class BlockEntryError(ValueError):
    """The text typed by the parent is not a usable app name or web address."""


# --- apps ----------------------------------------------------------------------

# Never blockable: blocking these could make Windows or BabyControl unusable.
PROTECTED_APPS = frozenset({
    "explorer.exe", "svchost.exe", "csrss.exe", "winlogon.exe", "wininit.exe",
    "services.exe", "lsass.exe", "smss.exe", "dwm.exe", "taskhostw.exe",
    "conhost.exe", "cmd.exe", "powershell.exe", "pwsh.exe", "sihost.exe",
    "fontdrvhost.exe", "ctfmon.exe", "runtimebroker.exe", "searchhost.exe",
    "startmenuexperiencehost.exe", "shellexperiencehost.exe", "msiexec.exe",
    "babycontrol-service.exe", "babycontrol-kiosk.exe", "babycontrol-admin.exe",
})

# A convenience starter list, not a guarantee: names vary by version and region.
GAME_PRESETS = (
    "steam.exe", "epicgameslauncher.exe", "robloxplayerbeta.exe",
    "robloxplayerlauncher.exe", "minecraftlauncher.exe", "minecraft.windows.exe",
    "leagueclient.exe", "league of legends.exe", "riotclientservices.exe",
    "valorant-win64-shipping.exe", "genshinimpact.exe", "fortniteclient-win64-shipping.exe",
    "battle.net.exe", "hd-player.exe", "dnplayer.exe",
)

_APP_RE = re.compile(r"^[a-z0-9][a-z0-9 ._()+\-]{0,100}\.exe$")


def normalize_app(text: str) -> str:
    """'C:\\Games\\Steam\\Steam.exe', 'steam' or 'STEAM.EXE' -> 'steam.exe'."""
    name = str(text).strip().strip('"').replace("/", "\\").split("\\")[-1].strip().lower()
    if not name:
        raise BlockEntryError("Chưa nhập tên ứng dụng")
    if not name.endswith(".exe"):
        name += ".exe"
    if not _APP_RE.match(name):
        raise BlockEntryError(f"Tên ứng dụng không hợp lệ: {text!r}")
    if name in PROTECTED_APPS:
        raise BlockEntryError(f"Không thể chặn {name}: đây là thành phần cần cho Windows/BabyControl")
    return name


# --- sites ---------------------------------------------------------------------

_DOMAIN_RE = re.compile(r"^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z][a-z0-9-]{1,62}$")


def normalize_site(text: str) -> str:
    """Link or address -> bare domain: 'https://www.Example.com/a/b?x=1' -> 'example.com'."""
    raw = str(text).strip().lower()
    if not raw:
        raise BlockEntryError("Chưa nhập địa chỉ trang web")
    if "://" not in raw and not raw.startswith("//"):
        raw = "//" + raw
    try:
        host = urlsplit(raw).hostname
    except ValueError as exc:
        raise BlockEntryError(f"Địa chỉ không hợp lệ: {text!r}") from exc
    if not host:
        raise BlockEntryError(f"Không tìm thấy tên trang web trong: {text!r}")
    host = host.rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    try:
        host = host.encode("idna").decode("ascii")      # unicode domain -> punycode
    except UnicodeError as exc:
        raise BlockEntryError(f"Tên miền không hợp lệ: {text!r}") from exc
    if not _DOMAIN_RE.match(host):
        raise BlockEntryError(f"Hãy nhập tên miền hoặc link trang web (ví dụ youtube.com), không phải: {text!r}")
    return host


def effective_blocklist(config, parent_mode: bool) -> tuple[list[str], list[str]]:
    """(apps, sites) to enforce right now.

    Nothing is blocked in parent mode (the parent is using the PC) or before a
    parent password exists (setup not finished)."""
    if parent_mode or not config.password_hash:
        return [], []
    return list(config.blocked_apps), list(config.blocked_sites)


# --- hosts file ----------------------------------------------------------------

def hosts_path() -> Path:
    return Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "drivers" / "etc" / "hosts"


def rewrite_hosts(original: str, domains: list[str]) -> str:
    """Return `original` with BabyControl's block replaced (or removed if no
    domains). Everything else is preserved, including the line-ending style."""
    newline = "\r\n" if "\r\n" in original else ("\n" if "\n" in original else "\r\n")
    kept, skipping = [], False
    for line in original.splitlines():
        if line.startswith("# BEGIN BabyControl"):
            skipping = True
            continue
        if skipping:
            if line.startswith("# END BabyControl"):
                skipping = False
            continue                    # unterminated block: drop to end of file
        kept.append(line)
    while kept and not kept[-1].strip():
        kept.pop()                      # no growing pile of blank lines
    if domains:
        kept.append("")
        kept.append(HOSTS_BEGIN)
        for domain in sorted(set(domains)):
            for name in (domain, "www." + domain):
                kept.append(f"127.0.0.1 {name}")
                kept.append(f"::1 {name}")
        kept.append(HOSTS_END)
    return newline.join(kept) + newline if kept else ""


def sync_hosts(domains: list[str], path: Path | None = None,
               flush: Callable[[], None] | None = None) -> bool:
    """Make the hosts file match `domains`. Returns True if it was changed.
    `flush` (e.g. ipconfig /flushdns) runs only after a change."""
    path = path or hosts_path()
    try:
        original = path.read_bytes().decode("utf-8", errors="surrogateescape")
    except FileNotFoundError:
        original = ""
    updated = rewrite_hosts(original, domains)
    if updated == original:
        return False
    try:
        os.chmod(path, stat.S_IREAD | stat.S_IWRITE)      # clear a read-only flag
    except OSError:
        pass
    path.write_bytes(updated.encode("utf-8", errors="surrogateescape"))
    if flush:
        flush()
    return True


def flush_dns() -> None:
    subprocess.run(["ipconfig", "/flushdns"], capture_output=True,
                   creationflags=CREATE_NO_WINDOW, timeout=20)


# --- processes -----------------------------------------------------------------

def running_blocked(tasklist_csv: str, blocked: list[str]) -> list[str]:
    """Image names from `tasklist /FO CSV /NH` output that are on the list."""
    wanted = {b.lower() for b in blocked}
    found = set()
    for row in csv.reader(io.StringIO(tasklist_csv)):
        if row and row[0].strip().lower() in wanted:
            found.add(row[0].strip().lower())
    return sorted(found)


def kill_blocked(blocked: list[str], run: Callable = subprocess.run) -> list[str]:
    """Kill every running process on the list. Returns the names killed."""
    if not blocked:
        return []
    out = run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True,
              errors="replace", creationflags=CREATE_NO_WINDOW, timeout=20).stdout
    killed = []
    for name in running_blocked(out or "", blocked):
        run(["taskkill", "/F", "/IM", name], capture_output=True,
            creationflags=CREATE_NO_WINDOW, timeout=20)
        killed.append(name)
    return killed
