# Build BabyControl executables with PyInstaller. Run on Windows from the repo root.
# Entry stubs in scripts\ import the babycontrol package (relative imports need it).
$ErrorActionPreference = "Stop"
python -m pip install -r requirements-dev.txt
$common = @("--noconfirm", "--onefile", "--paths", ".")
python -m PyInstaller @common --name babycontrol-service `
    --hidden-import win32timezone --hidden-import servicemanager scripts\entry_service.py
python -m PyInstaller @common --noconsole --name babycontrol-kiosk scripts\entry_kiosk.py
# --uac-admin: the admin tool must be elevated to write the locked-down config
python -m PyInstaller @common --noconsole --uac-admin --name babycontrol-admin scripts\entry_admin.py
Write-Host "Built into dist\ (keep all .exe files in the same folder)"
