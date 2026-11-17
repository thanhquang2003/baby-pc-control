# BabyControl - trinh cai dat mot-chay (chay qua CAI_DAT.bat).
# Tu xin quyen quan tri, tu cai Python neu thieu, tao chuong trinh, cai dich vu,
# tao loi tat cho phu huynh. Moi buoc ghi vao install.log.
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch { }

$RepoRoot = Split-Path -Parent $PSScriptRoot
$LogFile = Join-Path $RepoRoot "install.log"
$InstallDir = Join-Path $env:ProgramFiles "BabyControl"
$BuildRoot = Join-Path $RepoRoot ".build"
$VenvDir = Join-Path $BuildRoot "venv"
$ServiceName = "BabyControl"
$PythonVersion = "3.12.8"
$PythonUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-amd64.exe"
$TotalSteps = 7
$ExeNames = @("babycontrol-service.exe", "babycontrol-kiosk.exe", "babycontrol-admin.exe")
# Ban tai tu trang Releases co san file .exe canh CAI_DAT.bat: khong can Python va khong can build.
$Prebuilt = $true
foreach ($exeName in $ExeNames) {
    if (-not (Test-Path (Join-Path $RepoRoot $exeName))) { $Prebuilt = $false }
}

function Write-Log($Message) {
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
}
function Say($Message, $Color = "White") {
    Write-Host $Message -ForegroundColor $Color
    Write-Log $Message
}
function Step($Number, $Title) {
    Say ""
    Say ("[{0}/{1}] {2}" -f $Number, $TotalSteps, $Title) "Cyan"
}
function Pause-Exit($Code) {
    Write-Host ""
    Read-Host "Nhan Enter de dong cua so nay"
    exit $Code
}
function Test-Admin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# --- 1. quyen quan tri: tu mo lai voi quyen cao --------------------------------
if (-not (Test-Admin)) {
    Write-Host "Can quyen quan tri de cai dat. Hay bam 'Yes' (Co) o hop thoai sap hien ra." -ForegroundColor Yellow
    try {
        Start-Process -FilePath "powershell.exe" -Verb RunAs -ArgumentList @(
            "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$PSCommandPath`"")
    } catch {
        Write-Host "Khong duoc cap quyen quan tri nen cai dat da bi huy." -ForegroundColor Red
        Read-Host "Nhan Enter de dong"
    }
    exit 0
}

# --- ham tro giup ---------------------------------------------------------------
function Run-Logged($File, $Arguments) {
    # Chay lenh ngoai, ghi ket qua vao log, bao loi neu ma thoat khac 0.
    Write-Log ("> {0} {1}" -f $File, ($Arguments -join " "))
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & $File @Arguments 2>&1
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previous
    }
    foreach ($line in $output) { Write-Log ([string]$line) }
    if ($code -ne 0) {
        throw ("Lenh that bai (ma {0}): {1}" -f $code, $File)
    }
}

function Refresh-Path {
    $machine = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $user = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machine;$user"
}

function Test-PythonOk($Exe) {
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $Exe -c "import sys, tkinter; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    } finally {
        $ErrorActionPreference = $previous
    }
}

function Find-Python {
    $candidates = @()
    if (Get-Command py -ErrorAction SilentlyContinue) {
        try {
            $found = & py -3 -c "import sys; print(sys.executable)" 2>$null
            if ($found) { $candidates += [string]$found }
        } catch { }
    }
    $command = Get-Command python -ErrorAction SilentlyContinue
    if ($command -and ($command.Source -notlike "*WindowsApps*")) { $candidates += $command.Source }
    foreach ($folder in @("Python313", "Python312", "Python311", "Python310")) {
        $candidates += (Join-Path $env:ProgramFiles "$folder\python.exe")
        $candidates += (Join-Path $env:LOCALAPPDATA "Programs\Python\$folder\python.exe")
    }
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate) -and (Test-PythonOk $candidate)) { return $candidate }
    }
    return $null
}

function Install-Python {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Say "Dang cai Python bang winget (co the mat vai phut)..."
        $previous = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        try {
            & winget install -e --id Python.Python.3.12 --scope machine --silent `
                --accept-package-agreements --accept-source-agreements 2>&1 |
                ForEach-Object { Write-Log ([string]$_) }
        } finally {
            $ErrorActionPreference = $previous
        }
        Refresh-Path
        $python = Find-Python
        if ($python) { return $python }
        Say "winget chua cai duoc, thu cach khac..." "Yellow"
    }
    Say "Dang tai Python tu python.org (khoang 25 MB)..."
    $installer = Join-Path $env:TEMP "python-$PythonVersion-amd64.exe"
    Invoke-WebRequest -Uri $PythonUrl -OutFile $installer -UseBasicParsing
    $signature = Get-AuthenticodeSignature $installer
    $signer = ""
    if ($signature.SignerCertificate) { $signer = $signature.SignerCertificate.Subject }
    if (($signature.Status -ne "Valid") -or ($signer -notlike "*Python Software Foundation*")) {
        Remove-Item $installer -Force -ErrorAction SilentlyContinue
        throw "File Python tai ve khong hop le (chu ky so sai). Da dung cai dat."
    }
    Say "Dang cai Python..."
    Start-Process -FilePath $installer -Wait -ArgumentList @(
        "/quiet", "InstallAllUsers=1", "PrependPath=1", "Include_tcltk=1", "Include_launcher=1")
    Refresh-Path
    $python = Find-Python
    if (-not $python) { throw "Da cai Python nhung khong tim thay. Hay khoi dong lai may roi chay lai CAI_DAT.bat." }
    return $python
}

function New-Shortcut($Path, $Target, $Arguments) {
    $folder = Split-Path -Parent $Path
    if (-not (Test-Path $folder)) { New-Item -ItemType Directory -Path $folder -Force | Out-Null }
    $shell = New-Object -ComObject WScript.Shell
    $link = $shell.CreateShortcut($Path)
    $link.TargetPath = $Target
    if ($Arguments) { $link.Arguments = $Arguments }
    $link.WorkingDirectory = Split-Path -Parent $Target
    $link.Save()
}

function Copy-WithRetry($Source, $Destination) {
    for ($attempt = 1; $attempt -le 6; $attempt++) {
        try {
            Copy-Item -Path $Source -Destination $Destination -Force
            return
        } catch {
            if ($attempt -eq 6) { throw }
            Start-Sleep -Seconds 2
        }
    }
}

# --- chinh ----------------------------------------------------------------------
try {
    Clear-Host
    Set-Content -Path $LogFile -Value "" -Encoding UTF8
    Say "==============================================" "Green"
    Say "   CAI DAT BABYCONTROL" "Green"
    Say "   Quan ly gio dung may cho tre" "Green"
    Say "==============================================" "Green"
    if (-not $Prebuilt) { Say "Viec nay mat khoang 5-10 phut, can ket noi Internet." }
    Say "Xin dung tat cua so nay cho den khi co thong bao HOAN TAT."
    if ($Prebuilt) { Say "Dung ban cai nhanh: khong can Internet, khong can Python." "Green" }

    Step 1 "Kiem tra may tinh"
    if ([Environment]::OSVersion.Version.Major -lt 10) { throw "Can Windows 10 hoac 11." }
    if (-not [Environment]::Is64BitOperatingSystem) { throw "Can Windows 64-bit." }
    $neededFiles = @("scripts\install_service.ps1", "scripts\remove.ps1")
    if (-not $Prebuilt) {
        $neededFiles += @("requirements-dev.txt", "scripts\entry_service.py", "babycontrol\kiosk.py")
    }
    foreach ($needed in $neededFiles) {
        if (-not (Test-Path (Join-Path $RepoRoot $needed))) {
            throw "Thieu file $needed. Hay giai nen DAY DU thu muc BabyControl roi chay lai."
        }
    }
    Say "May tinh phu hop." "Green"

    $dist = Join-Path $BuildRoot "dist"
    if ($Prebuilt) { $dist = $RepoRoot }

    Step 2 "Kiem tra / cai Python"
    if ($Prebuilt) {
        Say "Ban nay da co san chuong trinh, khong can Python." "Green"
    } else {
        $python = Find-Python
        if ($python) {
            Say "Da co Python: $python" "Green"
        } else {
            $python = Install-Python
            Say "Da cai xong Python." "Green"
        }
    }

    Step 3 "Chuan bi cong cu (tai thu vien, can Internet)"
    if ($Prebuilt) {
        Say "Bo qua (khong can)." "Green"
    } else {
        Set-Location $RepoRoot
        if (Test-Path $VenvDir) { Remove-Item $VenvDir -Recurse -Force }
        New-Item -ItemType Directory -Path $BuildRoot -Force | Out-Null
        Run-Logged $python @("-m", "venv", $VenvDir)
        $venvPython = Join-Path $VenvDir "Scripts\python.exe"
        Run-Logged $venvPython @("-m", "pip", "install", "--disable-pip-version-check", "-r", "requirements-dev.txt")
        Say "Xong." "Green"
    }

    Step 4 "Tao chuong trinh BabyControl (buoc lau nhat, vui long cho)"
    if ($Prebuilt) {
        Say "Dung chuong trinh da build san." "Green"
    } else {
        $work = Join-Path $BuildRoot "work"
        $common = @("-m", "PyInstaller", "--noconfirm", "--onefile", "--paths", ".",
                    "--distpath", $dist, "--workpath", $work, "--specpath", $BuildRoot)
        Say "  - dich vu nen..."
        Run-Logged $venvPython ($common + @("--name", "babycontrol-service",
            "--hidden-import", "win32timezone", "--hidden-import", "servicemanager",
            "scripts\entry_service.py"))
        Say "  - man hinh khoa..."
        Run-Logged $venvPython ($common + @("--noconsole", "--name", "babycontrol-kiosk",
            "scripts\entry_kiosk.py"))
        Say "  - cong cu danh cho phu huynh..."
        Run-Logged $venvPython ($common + @("--noconsole", "--uac-admin", "--name", "babycontrol-admin",
            "scripts\entry_admin.py"))
    }
    foreach ($exe in $ExeNames) {
        if (-not (Test-Path (Join-Path $dist $exe))) { throw "Khong tim thay $exe" }
    }
    Say "Xong." "Green"

    Step 5 "Chep chuong trinh vao $InstallDir"
    if (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue) {
        Say "Phat hien ban cu, dang dung de nang cap (cai dat va du lieu cu duoc giu nguyen)..."
        Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
    }
    foreach ($process in @("babycontrol-kiosk", "babycontrol-admin")) {
        Get-Process -Name $process -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    foreach ($exe in $ExeNames) {
        Copy-WithRetry (Join-Path $dist $exe) (Join-Path $InstallDir $exe)
        # File tai tu Internet bi danh dau "tu mang ve"; bo dau de Windows khong chan.
        Unblock-File -Path (Join-Path $InstallDir $exe) -ErrorAction SilentlyContinue
    }
    Copy-WithRetry (Join-Path $PSScriptRoot "remove.ps1") (Join-Path $InstallDir "remove.ps1")
    Say "Xong." "Green"

    Step 6 "Cai dich vu giam sat"
    & (Join-Path $PSScriptRoot "install_service.ps1") -ExePath (Join-Path $InstallDir "babycontrol-service.exe") |
        ForEach-Object { Write-Log ([string]$_) }
    Start-Sleep -Seconds 3
    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ((-not $service) -or ($service.Status -ne "Running")) {
        throw "Dich vu BabyControl khong chay duoc. Xem Event Viewer (nguon BabyControl) va file install.log."
    }
    Say "Dich vu dang chay." "Green"

    Step 7 "Tao loi tat va mo man hinh thiet lap"
    $adminExe = Join-Path $InstallDir "babycontrol-admin.exe"
    $desktop = [Environment]::GetFolderPath("CommonDesktopDirectory")
    New-Shortcut (Join-Path $desktop "BabyControl - Phu huynh.lnk") $adminExe $null
    $startMenu = Join-Path $env:ProgramData "Microsoft\Windows\Start Menu\Programs\BabyControl"
    New-Shortcut (Join-Path $startMenu "BabyControl - Phu huynh.lnk") $adminExe $null
    New-Shortcut (Join-Path $startMenu "Go cai dat BabyControl.lnk") "powershell.exe" `
        ("-NoProfile -ExecutionPolicy Bypass -File `"{0}`"" -f (Join-Path $InstallDir "remove.ps1"))
    Start-Process -FilePath $adminExe
    Say "Da tao loi tat 'BabyControl - Phu huynh' tren man hinh nen." "Green"

    Say ""
    Say "==============================================" "Green"
    Say "   HOAN TAT CAI DAT" "Green"
    Say "==============================================" "Green"
    Say "Viec can lam tiep (cua so BabyControl vua hien ra):"
    Say "  1. Tao MAT KHAU PHU HUYNH (nho ky, con khong duoc biet)."
    Say "  2. Chon so phut moi ngay, lop cua con, so cau hoi moi mon."
    Say "  3. Them cac khung gio hoc tu do neu muon (tab 'Gio hoc')."
    Say "Man hinh khoa se tu bat len khi may khong con duoc dung."
    Say "Muon go cai dat: Start > BabyControl > Go cai dat (can mat khau phu huynh)."
    Say "File nhat ky (neu can nho nguoi ho tro): $LogFile" "DarkGray"
    Pause-Exit 0
} catch {
    Say ""
    Say "DA CO LOI: $($_.Exception.Message)" "Red"
    Say "Chi tiet nam o file: $LogFile" "Yellow"
    Say "Neu can giup, hay gui file install.log cho nguoi ho tro." "Yellow"
    Pause-Exit 1
}
