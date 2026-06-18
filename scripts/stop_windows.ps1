# ============================================================
# stop_windows.ps1  - Stop the FinAlly container (Windows)
# The named volume (finally-data) is NOT removed - data persists.
# ============================================================

$ErrorActionPreference = "Stop"
$ContainerName = "finally-app"

function Write-Info { param($msg) Write-Host "[FinAlly] $msg" -ForegroundColor Green  }
function Write-Warn { param($msg) Write-Host "[FinAlly] $msg" -ForegroundColor Yellow }

$running = docker ps -q --filter "name=^${ContainerName}$" 2>$null
if ($running) {
    Write-Info "Stopping container '$ContainerName' ..."
    docker stop $ContainerName | Out-Null
    Write-Info "Container stopped."
} else {
    Write-Warn "Container '$ContainerName' is not running."
}

$exists = docker ps -aq --filter "name=^${ContainerName}$" 2>$null
if ($exists) {
    docker rm $ContainerName | Out-Null
    Write-Info "Container removed."
}

Write-Info "Done. Portfolio data is preserved in the 'finally-data' Docker volume."
