@echo off
rem BabyControl - nhap dup file nay de cai dat. Khong can biet ve may tinh.
title Cai dat BabyControl
cd /d "%~dp0"
if not exist "scripts\setup.ps1" (
    echo.
    echo Khong tim thay thu muc "scripts".
    echo Hay GIAI NEN DAY DU file ZIP BabyControl ra mot thu muc,
    echo sau do mo thu muc do va nhap dup lai file CAI_DAT.bat.
    echo.
    pause
    exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup.ps1"
