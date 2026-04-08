# OmegaBot local startup script for Windows.
# Starts the API and web app directly from the current checkout.

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-FreePort {
    param(
        [Parameter(Mandatory = $true)]
        [int]$PreferredPort
    )

    $port = $PreferredPort
    while ($true) {
        $listener = $null
        try {
            $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $port)
            $listener.Start()
            $listener.Stop()
            return $port
        } catch {
            if ($listener) {
                $listener.Stop()
            }
            $port++
        }
    }
}

function Test-HttpReady {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,
        [int]$Attempts = 12,
        [int]$DelaySeconds = 2
    )

    for ($i = 0; $i -lt $Attempts; $i++) {
        try {
            Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 5 | Out-Null
            return $true
        } catch {
            Start-Sleep -Seconds $DelaySeconds
        }
    }

    return $false
}

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ApiDir = Join-Path $ProjectRoot "apps/api"
$WebDir = Join-Path $ProjectRoot "apps/web"
$LogDir = Join-Path $ProjectRoot ".codex-logs"
$ApiPython = Join-Path $ApiDir ".venv/Scripts/python.exe"
$NpmCmd = (Get-Command npm.cmd -ErrorAction SilentlyContinue).Source

if (-not (Test-Path $ApiPython)) {
    throw "Missing API virtualenv Python at $ApiPython"
}

if (-not $NpmCmd) {
    throw "npm.cmd was not found on PATH."
}

if (-not (Test-Path (Join-Path $WebDir "node_modules"))) {
    throw "Missing frontend dependencies. Run 'npm install' in $WebDir first."
}

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$ApiPort = Get-FreePort -PreferredPort 8000
$WebPort = Get-FreePort -PreferredPort 3000

Write-Host "------------------------------------" -ForegroundColor Cyan
Write-Host "   OmegaBot - Local Dev Startup     " -ForegroundColor Cyan
Write-Host "------------------------------------" -ForegroundColor Cyan
Write-Host "[1/2] Starting Backend (FastAPI)..." -ForegroundColor Yellow

$env:DEBUG = "false"
$env:PYTHONUNBUFFERED = "1"
$apiProcess = Start-Process `
    -FilePath $ApiPython `
    -WorkingDirectory $ApiDir `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$ApiPort" `
    -RedirectStandardOutput (Join-Path $LogDir "api.out.log") `
    -RedirectStandardError (Join-Path $LogDir "api.err.log") `
    -PassThru

$apiReady = Test-HttpReady -Url "http://127.0.0.1:$ApiPort/health"
if (-not $apiReady) {
    Write-Warning "API did not report ready in time. Check $LogDir\api.err.log"
} else {
    Write-Host "      API ready at: http://127.0.0.1:$ApiPort" -ForegroundColor Green
}

Write-Host "[2/2] Starting Frontend (Next.js)..." -ForegroundColor Yellow
$env:NEXT_PUBLIC_API_URL = "http://127.0.0.1:$ApiPort"
$env:NEXT_PUBLIC_WS_URL = "ws://127.0.0.1:$ApiPort"
$webProcess = Start-Process `
    -FilePath $NpmCmd `
    -WorkingDirectory $WebDir `
    -ArgumentList "run", "dev", "--", "--hostname", "127.0.0.1", "--port", "$WebPort" `
    -RedirectStandardOutput (Join-Path $LogDir "web.out.log") `
    -RedirectStandardError (Join-Path $LogDir "web.err.log") `
    -PassThru

Write-Host ""
Write-Host "OmegaBot is starting." -ForegroundColor Green
Write-Host "Dashboard : http://127.0.0.1:$WebPort" -ForegroundColor Cyan
Write-Host "API Docs  : http://127.0.0.1:$ApiPort/docs" -ForegroundColor Cyan
Write-Host "Logs      : $LogDir" -ForegroundColor Gray
Write-Host "API PID   : $($apiProcess.Id)" -ForegroundColor Gray
Write-Host "Web PID   : $($webProcess.Id)" -ForegroundColor Gray
Write-Host ""
Write-Host "The first frontend request can take a little while in dev mode." -ForegroundColor DarkGray
