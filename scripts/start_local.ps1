$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $RepoRoot
try {
    if (-not (Test-Path "apps\web\.next\BUILD_ID")) {
        Write-Host "[lexaudit] Erstelle Next.js Production-Build..."
        pnpm.cmd --dir apps/web build
    }
    uv run python scripts/start_local.py @args
}
finally {
    Pop-Location
}
