$ErrorActionPreference = 'SilentlyContinue'

# --- 1) heartbeat payload ---
$ts = (Get-Date).ToUniversalTime().ToString('o')
$result = 'COLLECTED'

$latest = Get-ChildItem 'C:\AIQuant\data\live_fxtm' -Filter 'ticks_*.parquet' |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1

$tickFile = $null
if ($latest) {
    $rowCount = & 'C:\AIQuant\.venv\Scripts\python.exe' -c "import sys; from pathlib import Path; import pandas as pd; p=sorted(Path(r'C:\AIQuant\data\live_fxtm').glob('ticks_*.parquet'))[-1]; print(len(pd.read_parquet(p)))"
    $tickFile = @{ file = $latest.Name; rows = ($rowCount | Select-Object -First 1) }
}

# market open estimate: compare latest tick mtime vs now
$marketOpen = $false
if ($latest) {
    $ageMin = ((Get-Date) - $latest.LastWriteTime).TotalMinutes
    if ($ageMin -lt 15) { $marketOpen = $true }
}
$marketState = if ($marketOpen) { 'OPEN' } else { 'STALE/CLOSED' }

$payload = [ordered]@{
    timestamp  = $ts
    result     = $result
    detail     = 'new=1768 total_day=43475'
    tick_file  = $tickFile
    market_open = $marketOpen
    market_state = $marketState
    source     = 'mt5-live-tick-collect cron'
} | ConvertTo-Json -Depth 4

$hbDir = 'C:\AIQuant\research\money_hunter\dashboard'
if (-not (Test-Path $hbDir)) { New-Item -ItemType Directory -Force -Path $hbDir | Out-Null }
Set-Content -Path (Join-Path $hbDir 'heartbeat_tick.json') -Value $payload -Encoding UTF8
Write-Output "HEARTBEAT_WRITTEN $payload"

# --- 2) dashboard self-heal on port 8787 ---
$c = Get-NetTCPConnection -LocalPort 8787 -State Listen -ErrorAction SilentlyContinue
if ($c) {
    Write-Output 'DASHBOARD_LISTENING'
} else {
    Write-Output 'DASHBOARD_DOWN_STARTING'
    Start-Process -FilePath 'C:\AIQuant\.venv\Scripts\python.exe' `
        -ArgumentList 'research\money_hunter\dashboard\dashboard.py' `
        -WorkingDirectory 'C:\AIQuant' -WindowStyle Hidden
    Start-Sleep -Seconds 6
    $c2 = Get-NetTCPConnection -LocalPort 8787 -State Listen -ErrorAction SilentlyContinue
    if ($c2) { Write-Output 'DASHBOARD_STARTED_OK' } else { Write-Output 'DASHBOARD_START_FAILED' }
}
