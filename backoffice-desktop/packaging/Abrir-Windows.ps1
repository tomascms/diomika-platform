#Requires -Version 5.1
<#
  Abre o Diomika Backoffice no Windows.
  1. Se já estiver instalado → abre a versão instalada (actualiza-se sozinha).
  2. Senão → corre o instalador Diomika-Backoffice-*-setup.exe desta pasta
     (instala só para este utilizador, sem pedir administrador, cria atalho
     no ambiente de trabalho e abre a aplicação).
  3. Sem instalador → extrai o .zip para .diomika e abre (modo de recurso,
     sem actualizações automáticas).
#>
$ErrorActionPreference = 'Continue'
$Root = $PSScriptRoot
Set-Location -LiteralPath $Root

function Write-Step([string]$msg) { Write-Host " - $msg" }

function Newest([string]$filter) {
  Get-ChildItem -LiteralPath $Root -Filter $filter -File -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
}

Write-Host ''
Write-Host ' Diomika Backoffice'
Write-Host ' -------------------'

$installed = @(
  (Join-Path $env:LOCALAPPDATA 'Programs\Diomika Backoffice\Diomika Backoffice.exe'),
  (Join-Path $env:LOCALAPPDATA 'Programs\backoffice-desktop\Diomika Backoffice.exe')
) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1

if ($installed) {
  Write-Step 'A abrir a versão instalada...'
  Start-Process -FilePath $installed
  exit 0
}

$setup = Newest 'Diomika-Backoffice-*-setup.exe'
if ($setup) {
  Write-Step "A instalar $($setup.Name) (só para este utilizador)..."
  try { Unblock-File -LiteralPath $setup.FullName -ErrorAction SilentlyContinue } catch {}
  Start-Process -FilePath $setup.FullName
  exit 0
}

$zip = Newest 'Diomika-Backoffice-*-windows.zip'
$appDir = Join-Path $Root '.diomika'
$appExe = Get-ChildItem -LiteralPath $appDir -Recurse -Filter 'Diomika Backoffice.exe' -File -ErrorAction SilentlyContinue |
  Select-Object -First 1 -ExpandProperty FullName

if (-not $appExe -and $zip) {
  Write-Step "A extrair $($zip.Name) (só na 1.ª vez)..."
  try { Unblock-File -LiteralPath $zip.FullName -ErrorAction SilentlyContinue } catch {}
  if (Test-Path -LiteralPath $appDir) { Remove-Item -LiteralPath $appDir -Recurse -Force -ErrorAction SilentlyContinue }
  Expand-Archive -LiteralPath $zip.FullName -DestinationPath $appDir -Force
  $appExe = Get-ChildItem -LiteralPath $appDir -Recurse -Filter 'Diomika Backoffice.exe' -File -ErrorAction SilentlyContinue |
    Select-Object -First 1 -ExpandProperty FullName
}

if (-not $appExe) {
  Write-Host ''
  Write-Host ' ERRO: não encontrei o instalador (Diomika-Backoffice-*-setup.exe) nesta pasta.'
  Write-Host ' Peça à Diomika o pacote mais recente.'
  Write-Host ''
  exit 1
}

Write-Step "A abrir: $appExe"
Start-Process -FilePath $appExe
exit 0
