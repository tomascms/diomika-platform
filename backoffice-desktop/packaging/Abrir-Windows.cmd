@echo off
setlocal
cd /d "%~dp0"
title Diomika Backoffice
echo.
echo  Diomika Backoffice — a preparar...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Abrir-Windows.ps1"
if errorlevel 1 (
  echo.
  echo Falhou. Leia LEIA-ME.txt (seccao Windows / antivirus).
  pause
)
endlocal
