# Active le venv TimaLove et se place dans le projet Django.
#
# IMPORTANT — lancer avec un point (dot-source) pour garder l'activation :
#   . .\activer-env.ps1
#
# Alternative CMD : double-clic ou "activer-env.bat"

$ErrorActionPreference = "Stop"
$Root = if ($PSScriptRoot) { $PSScriptRoot } else { Get-Location }
$VenvActivate = Join-Path $Root "venv\Scripts\Activate.ps1"
$AppDir = Join-Path $Root "timalove"

if (-not (Test-Path $VenvActivate)) {
    Write-Host "ERREUR : venv introuvable : $VenvActivate" -ForegroundColor Red
    Write-Host "Cree-le avec : python -m venv venv" -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path $AppDir)) {
    Write-Host "ERREUR : dossier app introuvable : $AppDir" -ForegroundColor Red
    exit 1
}

Set-Location $Root
& $VenvActivate
Set-Location $AppDir

Write-Host ""
Write-Host "Environnement TimaLove active." -ForegroundColor Green
Write-Host "Dossier : $AppDir" -ForegroundColor DarkGray
Write-Host "Python  : $(python --version 2>&1)" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Commandes utiles :" -ForegroundColor Cyan
Write-Host "  python manage.py runserver"
Write-Host "  python manage.py migrate"
Write-Host "  python manage.py createsuperuser"
Write-Host ""
