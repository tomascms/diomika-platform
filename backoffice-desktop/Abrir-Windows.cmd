@echo off
setlocal
cd /d "%~dp0"
title Diomika Backoffice
echo.
echo  Diomika Backoffice
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0packaging\Abrir-Windows.ps1"
if errorlevel 1 pause
endlocal
