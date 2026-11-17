import py_compile
from pathlib import Path

from babycontrol import config
from babycontrol.service import parse_tasklist_sessions

ROOT = Path(__file__).resolve().parent.parent


def test_parse_tasklist_sessions():
    out = ('"babycontrol-kiosk.exe","4242","Console","2","31,204 K"\n'
           '"babycontrol-kiosk.exe","5151","RDP-Tcp#0","3","30,000 K"\n')
    assert parse_tasklist_sessions(out) == {2, 3}


def test_parse_tasklist_no_match():
    info = 'INFO: No tasks are running which match the specified criteria.\n'
    assert parse_tasklist_sessions(info) == set()
    assert parse_tasklist_sessions("") == set()


def test_service_module_compiles():
    py_compile.compile(str(ROOT / "babycontrol" / "service.py"), doraise=True)


def test_prepare_data_dir_creates_usage_dir(tmp_path):
    root = config.prepare_data_dir(tmp_path / "bc")
    assert config.usage_dir(root).is_dir()


# --- FEAT-013: the service applies the parent's block lists ------------------------

def run_enforce(monkeypatch, cfg, pause_seconds):
    from types import SimpleNamespace

    from babycontrol import service
    calls = {}
    monkeypatch.setattr(service, "load_config", cfg if callable(cfg) else (lambda: cfg))
    monkeypatch.setattr(service, "kill_blocked", lambda apps: calls.__setitem__("apps", apps))
    monkeypatch.setattr(service, "sync_hosts",
                        lambda sites, flush=None: calls.__setitem__("sites", (sites, flush)))
    fake_self = SimpleNamespace(_tracker=SimpleNamespace(pause_remaining=lambda now: pause_seconds))
    service.BabyControlService.enforce_blocklist(fake_self)
    return calls


def test_service_enforces_configured_lists(monkeypatch):
    from types import SimpleNamespace

    from babycontrol import blocklist
    cfg = SimpleNamespace(password_hash="x", blocked_apps=["steam.exe"], blocked_sites=["a.com"])
    calls = run_enforce(monkeypatch, cfg, pause_seconds=0)
    assert calls["apps"] == ["steam.exe"]
    assert calls["sites"] == (["a.com"], blocklist.flush_dns)


def test_service_lifts_blocks_in_parent_mode(monkeypatch):
    from types import SimpleNamespace
    cfg = SimpleNamespace(password_hash="x", blocked_apps=["steam.exe"], blocked_sites=["a.com"])
    calls = run_enforce(monkeypatch, cfg, pause_seconds=900)
    assert calls["apps"] == [] and calls["sites"][0] == []     # hosts block removed too


def test_service_leaves_everything_alone_when_config_is_unreadable(monkeypatch):
    def unreadable():
        raise config.ConfigCorrupt("tampered")
    assert run_enforce(monkeypatch, unreadable, pause_seconds=0) == {}


def test_uninstaller_removes_the_hosts_block():
    text = (ROOT / "scripts" / "remove.ps1").read_text()
    assert "drivers\\etc\\hosts" in text and "flushdns" in text
