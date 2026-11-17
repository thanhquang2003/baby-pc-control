# Progress

## Latest Session

**Date:** 2026-11-17
**Verify:** `bash init.sh --verify` — 123 tests passed (macOS; Windows code not executed)
**Detail:** v1 tagged. v2 (0.2.0) delivered: FEAT-007 encrypted config/usage, FEAT-008 shared-account + parent mode, FEAT-009 one-click installer. PRs #1, #2, #3 squash-merged to `main`.

### Handoff

All queues empty. Tag `v1` = two-account version (commit 3c69a50). v2 is not tagged yet.
- Untested on Windows: everything touching win32 — `service.py`, `kiosk.py` / `admin.py` Tk UI, DPAPI in `secure_store.py`, registry marker in `config.py`, `scripts/*.ps1` (setup/remove/install/uninstall/build), `CAI_DAT.bat`, `GO_CAI_DAT.bat`, PyInstaller build. No PowerShell on the dev Mac, so the .ps1 files got static checks only (`tests/test_installer_files.py`).
- Installer messages are Vietnamese without diacritics on purpose (the .ps1 files are ASCII; Windows PowerShell 5.1 reads BOM-less files as ANSI). The GUIs use proper Vietnamese. Option: add a UTF-8 BOM and switch to diacritics.
- Known limits: encryption stops casual edits only; a determined admin can delete data+key (kiosk then locks, parent recovers via admin tool). Counting still happens in the kiosk, not the service.
- Idea: GitHub Actions on windows-latest to build a release zip with prebuilt exes, so parents skip the Python/PyInstaller step.
- Vocabulary lists in `babycontrol/exercises.py` are small (~16-18 words per grade band).

---

## History

- 2026-11-16: project initialized with lean-ai-harness; v1 built (TASK-001, FEAT-001..006).
- 2026-11-17: v1 tagged; v2 shipped (FEAT-007..009, PRs #1-#3).
