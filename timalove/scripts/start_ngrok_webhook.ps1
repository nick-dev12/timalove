# Demarre ngrok vers Django (port 8000) et met a jour .env pour NabooPay.
# Usage :
#   1. Compte ngrok : https://dashboard.ngrok.com/signup
#   2. ngrok config add-authtoken VOTRE_TOKEN
#   3. .\scripts\start_ngrok_webhook.ps1
# Prerequis : Django/Daphne sur le port 8000

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$EnvFile = Join-Path $Root ".env"
$Port = if ($env:DJANGO_PORT) { $env:DJANGO_PORT } else { "8000" }

$machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
$userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
$env:Path = "$machinePath;$userPath"

$ngrokCmd = Get-Command ngrok -ErrorAction SilentlyContinue
if (-not $ngrokCmd) {
    Write-Error "ngrok introuvable. Installez : winget install Ngrok.Ngrok"
}

if ($env:NGROK_AUTHTOKEN) {
    & $ngrokCmd.Source config add-authtoken $env:NGROK_AUTHTOKEN | Out-Null
}

$authCheck = & $ngrokCmd.Source config check 2>&1
if ($LASTEXITCODE -ne 0 -and "$authCheck" -match "authtoken|ERR_NGROK") {
    Write-Error @"
ngrok n'est pas authentifie.
1. Creez un compte : https://dashboard.ngrok.com/signup
2. Copiez votre token : https://dashboard.ngrok.com/get-started/your-authtoken
3. Executez : ngrok config add-authtoken VOTRE_TOKEN
   ou definissez NGROK_AUTHTOKEN dans .env puis relancez ce script.
"@
}

Get-Process -Name ngrok -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

Write-Host "Demarrage ngrok http $Port ..."
$ngrokProc = Start-Process -FilePath $ngrokCmd.Source -ArgumentList "http", $Port -PassThru -WindowStyle Hidden

$publicUrl = $null
$lastError = ""
for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Seconds 1
    try {
        $resp = Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels" -Method Get -ErrorAction Stop
        $tunnel = $resp.tunnels | Where-Object { $_.proto -eq "https" } | Select-Object -First 1
        if ($tunnel.public_url) {
            $publicUrl = $tunnel.public_url.TrimEnd("/")
            break
        }
    } catch {
        $lastError = $_.Exception.Message
    }
}

if (-not $publicUrl) {
    Stop-Process -Id $ngrokProc.Id -Force -ErrorAction SilentlyContinue
    Write-Error "Tunnel ngrok indisponible ($lastError). Verifiez l'authtoken et que le port $Port est libre."
}

Write-Host "Tunnel ngrok : $publicUrl"

if (-not (Test-Path $EnvFile)) {
    Write-Error "Fichier .env introuvable : $EnvFile"
}

$content = Get-Content $EnvFile -Raw -Encoding UTF8
$webhookPath = "/api/payments/naboo-webhook/"

function Set-EnvLine {
    param([string]$Name, [string]$Value)
    $script:content = $content -replace "(?m)^$Name=.*$", "$Name=$Value"
    if ($script:content -notmatch "(?m)^$Name=") {
        $script:content = $content.TrimEnd() + "`n$Name=$Value`n"
    }
}

Set-EnvLine -Name "NGROK_URL" -Value $publicUrl
Set-EnvLine -Name "NABOOPAY_PUBLIC_SITE_URL" -Value $publicUrl

$utf8 = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($EnvFile, $content, $utf8)

Write-Host ""
Write-Host "=== Configuration .env mise a jour ==="
Write-Host "NGROK_URL=$publicUrl"
Write-Host "NABOOPAY_PUBLIC_SITE_URL=$publicUrl"
Write-Host ""
Write-Host "Webhook a coller dans NabooPay (test local) :"
Write-Host "  ${publicUrl}${webhookPath}"
Write-Host ""
Write-Host "Relancez Daphne/Django pour prendre en compte le .env."
Write-Host "ngrok tourne en arriere-plan (PID $($ngrokProc.Id)). Arret : Stop-Process -Name ngrok"
Write-Host ""
Write-Host "URLs completes : python scripts/naboopay_webhook_setup.py"
