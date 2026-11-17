"""Static checks for the Windows installer files.

PowerShell is not available in CI/dev on macOS, so these catch the mistakes
that are easy to make and expensive to find on the parent's PC.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
BATCH = ["CAI_DAT.bat", "GO_CAI_DAT.bat"]
POWERSHELL = ["scripts/setup.ps1", "scripts/remove.ps1",
              "scripts/install_service.ps1", "scripts/uninstall_service.ps1",
              "scripts/build.ps1"]


@pytest.mark.parametrize("name", BATCH)
def test_batch_files_are_crlf_and_ascii(name):
    data = (ROOT / name).read_bytes()
    assert b"\n" in data
    assert data.count(b"\n") == data.count(b"\r\n"), "every line must end in CRLF"
    data.decode("ascii")                   # cmd.exe code pages mangle other text
    assert not data.startswith(b"\xef\xbb\xbf"), "a BOM breaks the first line"


@pytest.mark.parametrize("name", ["scripts/setup.ps1", "scripts/remove.ps1"])
def test_user_facing_powershell_is_ascii(name):
    # no BOM is written, and Windows PowerShell 5.1 reads BOM-less files as ANSI
    (ROOT / name).read_bytes().decode("ascii")


@pytest.mark.parametrize("name", POWERSHELL)
def test_powershell_brackets_balanced(name):
    text = (ROOT / name).read_text(encoding="utf-8")
    text = re.sub(r"(?m)^\s*#.*$", "", text)          # drop comment lines
    for open_ch, close_ch in ("{}", "()", "[]"):
        assert text.count(open_ch) == text.count(close_ch), (name, open_ch)
    assert text.count('"') % 2 == 0, f"{name}: unbalanced double quotes"


def test_batch_files_point_to_existing_scripts():
    assert "scripts\\setup.ps1" in (ROOT / "CAI_DAT.bat").read_text()
    assert "scripts\\remove.ps1" in (ROOT / "GO_CAI_DAT.bat").read_text()
    for name in ("setup.ps1", "remove.ps1"):
        assert (ROOT / "scripts" / name).exists()


def test_setup_references_existing_files():
    text = (ROOT / "scripts/setup.ps1").read_text()
    for entry in re.findall(r'scripts\\(entry_\w+\.py)', text):
        assert (ROOT / "scripts" / entry).exists(), entry
    for script in ("install_service.ps1", "remove.ps1"):
        assert script in text and (ROOT / "scripts" / script).exists()
    for exe in ("babycontrol-service", "babycontrol-kiosk", "babycontrol-admin"):
        assert exe in text


def test_gitattributes_keeps_windows_files_untouched():
    attrs = (ROOT / ".gitattributes").read_text()
    assert "*.bat -text" in attrs and "*.ps1 -text" in attrs
