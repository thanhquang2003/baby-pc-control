# Install BabyControl as an auto-start Windows service. Run as Administrator (parent account).
#Requires -RunAsAdministrator
param(
    [string]$ExePath = "$PSScriptRoot\..\dist\babycontrol-service.exe",
    [string]$ServiceName = "BabyControl"
)
$ErrorActionPreference = "Stop"
$exe = (Resolve-Path $ExePath).Path
if (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue) {
    Write-Host "Service exists; reinstalling"
    & "$PSScriptRoot\uninstall_service.ps1" -ServiceName $ServiceName
    Start-Sleep -Seconds 3   # let Windows finish deleting the old service
}
New-Service -Name $ServiceName -BinaryPathName "`"$exe`"" `
    -DisplayName "BabyControl" -StartupType Automatic | Out-Null
# Restart automatically on failure so the child cannot kill it permanently
sc.exe failure $ServiceName reset= 0 actions= restart/1000/restart/1000/restart/1000 | Out-Null
Start-Service -Name $ServiceName
Write-Host "Installed and started $ServiceName"
