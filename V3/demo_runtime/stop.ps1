$ErrorActionPreference = 'Stop'
$V3StopPath = Join-Path $PSScriptRoot 'runtime\STOP'
New-Item -ItemType Directory -Path (Split-Path $V3StopPath) -Force | Out-Null
Set-Content -LiteralPath $V3StopPath -Value 'Stop entries and flatten owned strategy position gracefully.' -Encoding utf8
