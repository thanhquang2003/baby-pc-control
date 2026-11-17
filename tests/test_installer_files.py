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


# --- FEAT-012: GitHub Actions + prebuilt package --------------------------------

def test_workflows_exist_and_run_on_windows():
    for name in ("ci.yml", "release.yml"):
        text = (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
        assert "windows-latest" in text, name
        assert "python -m pytest" in text, name
        assert "\t" not in text, "YAML must not contain tabs"
        for line in text.splitlines():
            if "uses:" in line:
                assert "@" in line and not line.strip().endswith(("@main", "@master")), line


def test_release_workflow_packages_files_that_exist():
    text = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    assert "tags:" in text and "workflow_dispatch" in text
    assert "pull_request:" in text                  # build is checked before merging
    assert "contents: write" in text                # needed to upload release assets
    assert "if: github.ref_type == 'tag'" in text   # manual runs never publish
    for exe in ("babycontrol-service", "babycontrol-kiosk", "babycontrol-admin"):
        assert f"dist\\{exe}.exe" in text
    for path in re.findall(r"(?:scripts|packaging)\\[\w.]+", text):
        assert (ROOT / path.replace("\\", "/")).exists(), path
    for name in ("CAI_DAT.bat", "GO_CAI_DAT.bat"):
        assert name in text and (ROOT / name).exists()


def test_build_script_checks_exit_codes_and_matches_installer_options():
    build = (ROOT / "scripts/build.ps1").read_text()
    setup = (ROOT / "scripts/setup.ps1").read_text()
    assert "$LASTEXITCODE" in build
    for flag in ("--uac-admin", "win32timezone", "servicemanager", "--noconsole"):
        assert flag in build and flag in setup, flag


def test_setup_detects_prebuilt_package_and_skips_python():
    setup = (ROOT / "scripts/setup.ps1").read_text()
    assert "$Prebuilt" in setup and "Unblock-File" in setup
    # the exe check must be against the folder that holds CAI_DAT.bat
    assert 'Join-Path $RepoRoot $exeName' in setup
    guide = (ROOT / "packaging/HUONG_DAN.txt").read_text(encoding="utf-8")
    assert "CAI_DAT.bat" in guide and "GO_CAI_DAT.bat" in guide
