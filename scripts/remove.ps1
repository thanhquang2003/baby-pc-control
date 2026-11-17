# BabyControl - go cai dat (chay qua GO_CAI_DAT.bat hoac Start > BabyControl).
# Can mat khau phu huynh de tranh viec tre tu go.
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$InstallDir = Join-Path $env:ProgramFiles "BabyControl"
$DataDir = Join-Path $env:ProgramData "BabyControl"
$ServiceName = "BabyControl"

function Say($Message, $Color = "White") { Write-Host $Message -ForegroundColor $Color }
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

if (-not (Test-Admin)) {
    Write-Host "Can quyen quan tri. Hay bam 'Yes' (Co) o hop thoai sap hien ra." -ForegroundColor Yellow
    try {
        Start-Process -FilePath "powershell.exe" -Verb RunAs -ArgumentList @(
            "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$PSCommandPath`"")
    } catch {
        Write-Host "Khong duoc cap quyen quan tri nen da huy." -ForegroundColor Red
        Read-Host "Nhan Enter de dong"
    }
    exit 0
}

try {
    Clear-Host
    Say "==============================================" "Yellow"
    Say "   GO CAI DAT BABYCONTROL" "Yellow"
    Say "==============================================" "Yellow"

    # 1. Xac nhan mat khau phu huynh (neu da dat)
    $adminExe = Join-Path $InstallDir "babycontrol-admin.exe"
    if (Test-Path $adminExe) {
        Say "Hay nhap MAT KHAU PHU HUYNH trong cua so vua hien ra."
        $check = Start-Process -FilePath $adminExe -ArgumentList "--confirm" -Wait -PassThru
        if ($check.ExitCode -ne 0) {
            Say "Chua xac nhan duoc mat khau. Da dung, khong go gi ca." "Red"
            Pause-Exit 1
        }
    }
    $answer = Read-Host "Go BabyControl khoi may nay? Go chu C roi Enter de dong y, phim khac de huy"
    if ($answer -notin @("C", "c")) {
        Say "Da huy. Khong co gi bi thay doi." "Green"
        Pause-Exit 0
    }

    # 2. Dung va xoa dich vu
    if (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue) {
        Say "Dang dung dich vu..."
        Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
        & sc.exe delete $ServiceName | Out-Null
    }
    for ($i = 0; $i -lt 5; $i++) {
        foreach ($process in @("babycontrol-kiosk", "babycontrol-admin")) {
            Get-Process -Name $process -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
        }
        Start-Sleep -Seconds 1
    }

    # 3. Bat lai Task Manager cho moi nguoi dung dang dang nhap
    Get-ChildItem Registry::HKEY_USERS -ErrorAction SilentlyContinue | ForEach-Object {
        $key = "Registry::{0}\Software\Microsoft\Windows\CurrentVersion\Policies\System" -f $_.Name
        if (Test-Path $key) {
            Remove-ItemProperty -Path $key -Name DisableTaskMgr -ErrorAction SilentlyContinue
        }
    }

    # 3b. Go khoi chan trang web trong file hosts (giu nguyen cac dong khac)
    $hostsPath = Join-Path $env:SystemRoot "System32\drivers\etc\hosts"
    if (Test-Path $hostsPath) {
        $kept = @()
        $skipping = $false
        foreach ($line in (Get-Content -Path $hostsPath)) {
            if ($line.StartsWith("# BEGIN BabyControl")) { $skipping = $true; continue }
            if ($skipping) {
                if ($line.StartsWith("# END BabyControl")) { $skipping = $false }
                continue
            }
            $kept += $line
        }
        $current = @(Get-Content -Path $hostsPath)
        if ($kept.Count -ne $current.Count) {
            [System.IO.File]::WriteAllLines($hostsPath, $kept, (New-Object System.Text.UTF8Encoding($false)))
            & ipconfig.exe /flushdns | Out-Null
            Say "Da go cac trang web bi chan." "Green"
        }
    }

    # 4. Xoa loi tat va chuong trinh
    $desktop = [Environment]::GetFolderPath("CommonDesktopDirectory")
    Remove-Item (Join-Path $desktop "BabyControl - Phu huynh.lnk") -Force -ErrorAction SilentlyContinue
    Remove-Item (Join-Path $env:ProgramData "Microsoft\Windows\Start Menu\Programs\BabyControl") `
        -Recurse -Force -ErrorAction SilentlyContinue
    Set-Location $env:SystemRoot
    try {
        Remove-Item $InstallDir -Recurse -Force
    } catch {
        Say "Khong xoa het duoc thu muc $InstallDir (co the xoa tay sau khi khoi dong lai)." "Yellow"
    }

    # 5. Du lieu (cai dat, nhat ky gio): hoi truoc khi xoa
    $wipe = Read-Host "Xoa luon cai dat va nhat ky gio dung may? Go chu C de xoa, phim khac de GIU lai (de cai lai sau nay)"
    if ($wipe -in @("C", "c")) {
        Remove-Item $DataDir -Recurse -Force -ErrorAction SilentlyContinue
        Remove-Item "HKLM:\SOFTWARE\BabyControl" -Recurse -Force -ErrorAction SilentlyContinue
        Say "Da xoa du lieu." "Green"
    } else {
        Say "Da giu lai du lieu o $DataDir" "Green"
    }

    Say ""
    Say "DA GO CAI DAT BABYCONTROL." "Green"
    Pause-Exit 0
} catch {
    Say ""
    Say "DA CO LOI: $($_.Exception.Message)" "Red"
    Pause-Exit 1
}
