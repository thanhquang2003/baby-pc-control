# Remove the BabyControl Windows service. Run as Administrator (parent account).
#Requires -RunAsAdministrator
param([string]$ServiceName = "BabyControl")
$ErrorActionPreference = "Stop"
if (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue) {
    Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
    sc.exe delete $ServiceName | Out-Null
    Write-Host "Removed $ServiceName"
} else {
    Write-Host "$ServiceName not installed"
}
