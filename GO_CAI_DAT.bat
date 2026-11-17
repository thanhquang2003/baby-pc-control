@echo off
rem BabyControl - nhap dup file nay de go cai dat (can mat khau phu huynh).
title Go cai dat BabyControl
cd /d "%~dp0"
if not exist "scripts\remove.ps1" (
    echo.
    echo Khong tim thay thu muc "scripts".
    echo Hay mo Start, tim muc BabyControl, chon "Go cai dat BabyControl".
    echo.
    pause
    exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\remove.ps1"
