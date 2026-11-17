# Build BabyControl executables with PyInstaller. Run on Windows from the repo root.
# Entry stubs in scripts\ import the babycontrol package (relative imports need it).
# Used by GitHub Actions (.github/workflows/release.yml) and for manual builds.
$ErrorActionPreference = "Stop"

function Invoke-Build($Arguments) {
    python -m PyInstaller @Arguments
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed (exit code $LASTEXITCODE)" }
}

python -m pip install -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

$common = @("--noconfirm", "--onefile", "--paths", ".")
Invoke-Build ($common + @("--name", "babycontrol-service",
    "--hidden-import", "win32timezone", "--hidden-import", "servicemanager",
    "scripts\entry_service.py"))
Invoke-Build ($common + @("--noconsole", "--name", "babycontrol-kiosk", "scripts\entry_kiosk.py"))
# --uac-admin: the admin tool must be elevated to write the locked-down config
Invoke-Build ($common + @("--noconsole", "--uac-admin", "--name", "babycontrol-admin",
    "scripts\entry_admin.py"))

foreach ($exe in @("babycontrol-service", "babycontrol-kiosk", "babycontrol-admin")) {
    if (-not (Test-Path "dist\$exe.exe")) { throw "Missing dist\$exe.exe" }
}
Write-Host "Built into dist\ (keep all .exe files in the same folder)"
