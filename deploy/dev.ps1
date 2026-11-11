# Arranque local para testar loja + backoffice. A loja fala com a API local (porta 8001); o backoffice, com a da cloud.
# Uso: powershell -ExecutionPolicy Bypass -File deploy/dev.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host ""
Write-Host "=== Diomika dev local ===" -ForegroundColor Cyan
Write-Host "API local:    http://127.0.0.1:8001 (a loja; arranca abaixo)"
Write-Host "API cloud:   https://api.diomika.com (so o backoffice)"
Write-Host "Loja:         http://127.0.0.1:5173"
Write-Host "Backoffice:   http://127.0.0.1:5174"
Write-Host ""

# A loja (npm run dev) encaminha /api para a API local por omissao (FE-20): arranca-a primeiro.
# Atencao: a API local usa o .env da raiz, que e o de producao. Para nao tocar na producao, define as variaveis
# da base de dados de teste no ambiente antes de correres este script.
python deploy/start_local_api.py

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
