# Build BabyControl executables with PyInstaller. Run on Windows from the repo root.
$ErrorActionPreference = "Stop"
python -m pip install -r requirements-dev.txt
python -m PyInstaller --noconfirm --onefile --name babycontrol-service babycontrol\service.py
python -m PyInstaller --noconfirm --onefile --noconsole --name babycontrol-kiosk babycontrol\kiosk.py
python -m PyInstaller --noconfirm --onefile --noconsole --name babycontrol-admin babycontrol\admin.py
Write-Host "Built into dist\"
