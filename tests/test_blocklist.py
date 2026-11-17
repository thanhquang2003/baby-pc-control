import subprocess
from types import SimpleNamespace

import pytest

from babycontrol import blocklist
from babycontrol.blocklist import (
    GAME_PRESETS, HOSTS_BEGIN, HOSTS_END, PROTECTED_APPS, BlockEntryError,
    effective_blocklist, kill_blocked, normalize_app, normalize_site,
    rewrite_hosts, running_blocked, sync_hosts,
)


# --- apps -----------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("steam", "steam.exe"),
    ("Steam.EXE", "steam.exe"),
    ("  steam.exe  ", "steam.exe"),
    (r"C:\Program Files (x86)\Steam\Steam.exe", "steam.exe"),
    ('"C:\\Games\\Roblox\\RobloxPlayerBeta.exe"', "robloxplayerbeta.exe"),
    ("C:/Games/Epic/EpicGamesLauncher.exe", "epicgameslauncher.exe"),
    ("League of Legends.exe", "league of legends.exe"),
])
def test_normalize_app(text, expected):
    assert normalize_app(text) == expected


@pytest.mark.parametrize("text", ["", "   ", ".exe", "bad|name", "a" * 150, "x<y"])
def test_normalize_app_rejects_garbage(text):
    with pytest.raises(BlockEntryError):
        normalize_app(text)


@pytest.mark.parametrize("name", sorted(PROTECTED_APPS))
def test_system_processes_cannot_be_blocked(name):
    with pytest.raises(BlockEntryError):
        normalize_app(name)
    with pytest.raises(BlockEntryError):
        normalize_app(name.upper())


def test_game_presets_are_valid_and_normalized():
    assert len(GAME_PRESETS) == len(set(GAME_PRESETS))
    for preset in GAME_PRESETS:
        assert normalize_app(preset) == preset


# --- sites ----------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("youtube.com", "youtube.com"),
    ("https://www.youtube.com/watch?v=abc&t=3", "youtube.com"),
    ("HTTP://WWW.YouTube.COM", "youtube.com"),
    ("www.facebook.com/groups/x", "facebook.com"),
    ("https://m.facebook.com", "m.facebook.com"),
    ("https://user:pw@games.example.org:8443/a/b#frag", "games.example.org"),
    ("example.co.uk.", "example.co.uk"),
    ("//tiktok.com/@someone", "tiktok.com"),
    ("https://bücher.de", "xn--bcher-kva.de"),
])
def test_normalize_site(text, expected):
    assert normalize_site(text) == expected


@pytest.mark.parametrize("text", [
    "", "   ", "localhost", "192.168.1.1", "http://127.0.0.1/x", "not a domain",
    "http://", "-bad-.com", "a..com", "https://exa mple.com", "ftp://", "x" * 300 + ".com",
])
def test_normalize_site_rejects_garbage(text):
    with pytest.raises(BlockEntryError):
        normalize_site(text)


# --- hosts file -----------------------------------------------------------------

ORIGINAL = "# Copyright (c) Microsoft\r\n127.0.0.1 localhost\r\n::1 localhost\r\n"


def test_rewrite_adds_block_with_www_and_ipv6_and_keeps_the_rest():
    result = rewrite_hosts(ORIGINAL, ["youtube.com"])
    assert result.startswith(ORIGINAL.rstrip("\r\n"))
    assert HOSTS_BEGIN in result and result.rstrip().endswith(HOSTS_END)
    for host in ("youtube.com", "www.youtube.com"):
        assert f"127.0.0.1 {host}\r\n" in result
        assert f"::1 {host}\r\n" in result
    assert "\n" not in result.replace("\r\n", "")      # consistent CRLF


def test_rewrite_is_idempotent():
    once = rewrite_hosts(ORIGINAL, ["b.com", "a.com"])
    assert rewrite_hosts(once, ["a.com", "b.com"]) == once       # order-insensitive
    assert once.count(HOSTS_BEGIN) == 1


def test_rewrite_updates_and_removes_the_block():
    once = rewrite_hosts(ORIGINAL, ["a.com"])
    changed = rewrite_hosts(once, ["b.com"])
    assert "a.com" not in changed and "b.com" in changed
    cleared = rewrite_hosts(changed, [])
    assert cleared == ORIGINAL                          # back to exactly the original
    assert HOSTS_BEGIN not in cleared


def test_rewrite_preserves_lf_files_and_odd_content():
    lf = "127.0.0.1 localhost\n# my note\n10.0.0.5 nas\n"
    result = rewrite_hosts(lf, ["a.com"])
    assert "\r" not in result and "10.0.0.5 nas" in result and "# my note" in result
    assert rewrite_hosts(result, []) == lf


def test_rewrite_drops_an_unterminated_block_and_empty_file_cases():
    broken = ORIGINAL + HOSTS_BEGIN + "\r\n127.0.0.1 old.com\r\n"
    assert rewrite_hosts(broken, []) == ORIGINAL
    assert rewrite_hosts("", []) == ""
    assert rewrite_hosts("", ["a.com"]).count("127.0.0.1 a.com") == 1


def test_sync_hosts_writes_only_on_change_and_flushes(tmp_path):
    hosts = tmp_path / "hosts"
    hosts.write_bytes(ORIGINAL.encode())
    flushed = []
    assert sync_hosts(["a.com"], hosts, flush=lambda: flushed.append(1)) is True
    assert sync_hosts(["a.com"], hosts, flush=lambda: flushed.append(1)) is False
    assert flushed == [1]                               # not flushed when unchanged
    assert b"127.0.0.1 www.a.com" in hosts.read_bytes()
    assert sync_hosts([], hosts, flush=lambda: flushed.append(1)) is True
    assert hosts.read_bytes() == ORIGINAL.encode()
    assert flushed == [1, 1]


def test_sync_hosts_creates_missing_file_and_keeps_foreign_bytes(tmp_path):
    hosts = tmp_path / "hosts"
    assert sync_hosts([], hosts) is False and not hosts.exists()
    hosts.write_bytes(b"127.0.0.1 caf\xe9.local\r\n")       # not valid UTF-8
    sync_hosts(["a.com"], hosts)
    sync_hosts([], hosts)
    assert hosts.read_bytes() == b"127.0.0.1 caf\xe9.local\r\n"


def test_sync_hosts_overwrites_a_read_only_file(tmp_path):
    import os
    import stat
    hosts = tmp_path / "hosts"
    hosts.write_bytes(ORIGINAL.encode())
    os.chmod(hosts, stat.S_IREAD)
    assert sync_hosts(["a.com"], hosts) is True
    assert b"a.com" in hosts.read_bytes()


# --- processes ------------------------------------------------------------------

TASKLIST = (
    '"System Idle Process","0","Services","0","8 K"\n'
    '"Steam.exe","4242","Console","1","200,000 K"\n'
    '"steam.exe","4300","Console","2","100,000 K"\n'
    '"chrome.exe","5000","Console","1","300,000 K"\n'
    '"League of Legends.exe","6000","Console","1","1,000,000 K"\n'
)


def test_running_blocked_matches_case_insensitively_once_per_name():
    assert running_blocked(TASKLIST, ["steam.exe", "league of legends.exe", "roblox.exe"]) == [
        "league of legends.exe", "steam.exe"]
    assert running_blocked(TASKLIST, []) == []
    assert running_blocked("", ["steam.exe"]) == []


def test_kill_blocked_kills_each_running_name_once():
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout=TASKLIST if cmd[0] == "tasklist" else "")

    killed = kill_blocked(["steam.exe", "minecraft.exe"], run=fake_run)
    assert killed == ["steam.exe"]
    assert ["taskkill", "/F", "/IM", "steam.exe"] in calls
    assert not any("minecraft.exe" in c for c in calls)


def test_kill_blocked_with_empty_list_runs_nothing():
    def boom(*a, **k):
        raise AssertionError("must not run any command")
    assert kill_blocked([], run=boom) == []


# --- what is enforced when -------------------------------------------------------

def test_effective_blocklist():
    config = SimpleNamespace(password_hash="x", blocked_apps=["steam.exe"],
                             blocked_sites=["youtube.com"])
    assert effective_blocklist(config, parent_mode=False) == (["steam.exe"], ["youtube.com"])
    assert effective_blocklist(config, parent_mode=True) == ([], [])      # parent is using the PC
    config.password_hash = ""
    assert effective_blocklist(config, parent_mode=False) == ([], [])     # setup not finished


def test_hosts_markers_match_the_uninstaller():
    from pathlib import Path
    remove = (Path(__file__).resolve().parent.parent / "scripts/remove.ps1").read_text()
    assert HOSTS_BEGIN.startswith("# BEGIN BabyControl") and HOSTS_END.startswith("# END BabyControl")
    assert '"# BEGIN BabyControl"' in remove and '"# END BabyControl"' in remove
    assert blocklist.hosts_path().name == "hosts"
