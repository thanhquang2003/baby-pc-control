# Progress

## Latest Session

**Date:** 2026-11-17
**Verify:** `bash init.sh --verify` — 123 tests passed (macOS; Windows code not executed)
**Detail:** FEAT-013 (v0.3.0: parent-defined blocking of apps/games by .exe name and websites via hosts file; tab Chặn). FEAT-012 (GitHub Actions: Windows CI + release build of exes/ZIP; prebuilt-aware setup.ps1). BUG-003 (v0.2.4: tracker syncs across processes; no lock while the parent tool is open) and FEAT-011 (v0.2.5: parent picks minutes on the lock screen). FEAT-010 (v0.2.3: wrong answers made up with the same subject, per-subject progress). BUG-001 (v0.2.1, no lock before a parent password exists) and BUG-002 (v0.2.2, kiosk stole focus from the answer box) fixed. v1 tagged. v2 (0.2.0) delivered: FEAT-007 encrypted config/usage, FEAT-008 shared-account + parent mode, FEAT-009 one-click installer. PRs #1, #2, #3 squash-merged to `main`.

### Handoff

All queues empty. Tag `v1` = two-account version (commit 3c69a50). v2 tag = d7934a1 (has BUG-001); fixes and features since v2 are in main as 0.2.5, not tagged.
- Now covered on Windows by CI (windows-latest): the whole pytest suite incl. DPAPI, and the PyInstaller build of the 3 exes. Still never run by a human: the .ps1 installer's prebuilt path, the Tk screens beyond what the owner tried, and the tag-triggered release upload (tag e.g. v2.2.0 to exercise it).
- Untested on Windows (older note): everything touching win32 — `service.py`, `kiosk.py` / `admin.py` Tk UI, DPAPI in `secure_store.py`, registry marker in `config.py`, `scripts/*.ps1` (setup/remove/install/uninstall/build), `CAI_DAT.bat`, `GO_CAI_DAT.bat`, PyInstaller build. No PowerShell on the dev Mac, so the .ps1 files got static checks only (`tests/test_installer_files.py`).
- Installer messages are Vietnamese without diacritics on purpose (the .ps1 files are ASCII; Windows PowerShell 5.1 reads BOM-less files as ANSI). The GUIs use proper Vietnamese. Option: add a UTF-8 BOM and switch to diacritics.
- Known limits: encryption stops casual edits only; a determined admin can delete data+key (kiosk then locks, parent recovers via admin tool). Counting still happens in the kiosk, not the service. Kiosk and admin tool now share usage.dat safely (token + merge in UsageTracker).
- Idea: GitHub Actions on windows-latest to build a release zip with prebuilt exes, so parents skip the Python/PyInstaller step.
- Vocabulary lists in `babycontrol/exercises.py` are small (~16-18 words per grade band).

---

## History

- 2026-11-16: project initialized with lean-ai-harness; v1 built (TASK-001, FEAT-001..006).
- 2026-11-17: v1 tagged; v2 shipped (FEAT-007..009, PRs #1-#3).
