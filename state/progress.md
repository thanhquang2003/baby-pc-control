# Progress

## Latest Session

**Date:** 2026-11-16
**Verify:** `bash init.sh --verify` — 84 tests passed (macOS; Windows code not executed)
**Detail:** TASK-001 and FEAT-001..006 implemented and merged to `main` locally (no git remote, so no PRs; squash-merged from worktrees).

### Handoff

All queues empty. Pending: manual test on Windows.
- Untested on Windows: `babycontrol/kiosk.py` (Tk UI), `babycontrol/service.py` (pywin32 service, CreateProcessAsUser, WTS APIs, DisableTaskMgr), `babycontrol/admin.py` `run_ui`, `scripts/*.ps1`, PyInstaller build.
- Known limitation: kiosk (child's account) writes `usage\usage.json`, so a technical child could edit it. Hardening idea: move counting into the service and talk to the kiosk over a local pipe.
- Vocabulary lists in `babycontrol/exercises.py` are small (~16-18 words per grade band).
- See README.md for Windows install steps.

---

## History

- 2026-11-16: project initialized with lean-ai-harness.
