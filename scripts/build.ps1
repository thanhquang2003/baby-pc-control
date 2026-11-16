# Build BabyControl executables with PyInstaller. Run on Windows from the repo root.
# Entry stubs in scripts\ import the babycontrol package (relative imports need it).
$ErrorActionPreference = "Stop"
python -m pip install -r requirements-dev.txt
$common = @("--noconfirm", "--onefile", "--paths", ".")
python -m PyInstaller @common --name babycontrol-service `
    --hidden-import win32timezone --hidden-import servicemanager scripts\entry_service.py
python -m PyInstaller @common --noconsole --name babycontrol-kiosk scripts\entry_kiosk.py
if (Test-Path scripts\entry_admin.py) {
    python -m PyInstaller @common --noconsole --name babycontrol-admin scripts\entry_admin.py
}
Write-Host "Built into dist\ (keep all .exe files in the same folder)"
