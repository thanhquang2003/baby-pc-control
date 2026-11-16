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
