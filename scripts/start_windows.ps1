# ============================================================
# start_windows.ps1  — Start the FinAlly container (Windows)
# Usage:
#   .\scripts\start_windows.ps1          # build only if image missing
#   .\scripts\start_windows.ps1 --build  # force a fresh image build
# ============================================================
param(
    [switch]$Build
)

$ErrorActionPreference = "Stop"

$ImageName     = "finally:latest"
$ContainerName = "finally-app"
$VolumeName    = "finally-data"
$HostPort      = 8000
$AppUrl        = "http://localhost:$HostPort"

# Project root is one level above the scripts/ directory
$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectRoot = Split-Path -Parent $ScriptDir

function Write-Info  { param($msg) Write-Host "[FinAlly] $msg" -ForegroundColor Green  }
function Write-Warn  { param($msg) Write-Host "[FinAlly] $msg" -ForegroundColor Yellow }
function Write-Err   { param($msg) Write-Host "[FinAlly] $msg" -ForegroundColor Red    }

# ── Preflight checks ─────────────────────────────────────────
try { docker version | Out-Null } catch {
    Write-Err "Docker not found. Install Docker Desktop: https://www.docker.com/products/docker-desktop"
    exit 1
}

$EnvFile = Join-Path $ProjectRoot ".env"
if (-not (Test-Path $EnvFile)) {
    Write-Warn ".env file not found. Copying from .env.example ..."
    Copy-Item (Join-Path $ProjectRoot ".env.example") $EnvFile
    Write-Warn "Please edit .env and set OPENROUTER_API_KEY before running the app."
}

# ── Determine whether to build ───────────────────────────────
$ShouldBuild = $Build
if (-not $ShouldBuild) {
    $imageExists = docker image inspect $ImageName 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Info "Image '$ImageName' not found — building now ..."
        $ShouldBuild = $true
    }
}

if ($ShouldBuild) {
    Write-Info "Building Docker image '$ImageName' ..."
    docker build -t $ImageName $ProjectRoot
    if ($LASTEXITCODE -ne 0) { Write-Err "Build failed."; exit 1 }
    Write-Info "Build complete."
}

# ── Stop any existing container (idempotent) ─────────────────
$running = docker ps -q --filter "name=^${ContainerName}$" 2>$null
if ($running) {
    Write-Warn "Stopping existing container '$ContainerName' ..."
    docker stop $ContainerName | Out-Null
    docker rm   $ContainerName | Out-Null
}
$exists = docker ps -aq --filter "name=^${ContainerName}$" 2>$null
if ($exists) {
    docker rm $ContainerName | Out-Null
}

# ── Ensure named volume exists ───────────────────────────────
docker volume create $VolumeName | Out-Null

# ── Start container ──────────────────────────────────────────
Write-Info "Starting FinAlly ..."
docker run `
    --detach `
    --name $ContainerName `
    --publish "${HostPort}:8000" `
    --volume "${VolumeName}:/app/db" `
    --env-file $EnvFile `
    --restart unless-stopped `
    $ImageName

if ($LASTEXITCODE -ne 0) { Write-Err "Failed to start container."; exit 1 }

Write-Info "Container started. Waiting for health check ..."

# Poll /api/health for up to 30 seconds
$ready = $false
for ($i = 0; $i -lt 15; $i++) {
    try {
        $resp = Invoke-WebRequest -Uri "$AppUrl/api/health" -UseBasicParsing -TimeoutSec 2
        if ($resp.StatusCode -eq 200) { $ready = $true; break }
    } catch {}
    Start-Sleep -Seconds 2
}

Write-Host ""
Write-Info "FinAlly is running at: $AppUrl"
Write-Host ""

# Open the browser
try { Start-Process $AppUrl } catch {}
