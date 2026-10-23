# Arranque local para testar loja + backoffice (API cloud por defeito).
# Uso: powershell -ExecutionPolicy Bypass -File deploy/dev.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host ""
Write-Host "=== Diomika dev local ===" -ForegroundColor Cyan
Write-Host "API producao: https://api.diomika.com"
Write-Host "Loja:         http://127.0.0.1:5173"
Write-Host "Backoffice:   http://127.0.0.1:5174"
Write-Host ""

# API local opcional (descomenta se quiseres testar backend local)
# python deploy/start_local_api.py

Start-Process powershell -ArgumentList @(
  "-NoExit", "-Command",
  "Set-Location '$Root\frontend-web'; npm run dev"
) -WindowStyle Normal

Start-Sleep -Seconds 2

Start-Process powershell -ArgumentList @(
  "-NoExit", "-Command",
  "Set-Location '$Root\backoffice-desktop'; npm run dev"
) -WindowStyle Normal

Write-Host "OK - duas janelas abertas (loja + backoffice)." -ForegroundColor Green
Write-Host "Para parar: fecha as janelas PowerShell."
Write-Host ""
