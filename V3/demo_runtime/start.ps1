param([string]$Python = 'C:\AIQuant\.venv\Scripts\python.exe')
$ErrorActionPreference = 'Stop'
$V3DemoRoot = $PSScriptRoot
$V3StopPath = Join-Path $V3DemoRoot 'runtime\STOP'
if (Test-Path -LiteralPath $V3StopPath) { Remove-Item -LiteralPath $V3StopPath }
New-Item -ItemType Directory -Path (Join-Path $V3DemoRoot 'runtime') -Force | Out-Null
Set-Content -LiteralPath (Join-Path $V3DemoRoot 'runtime\START') -Value 'Explicit user start; valid bound authorization still required.' -Encoding utf8
$V3Arguments = @('-m', 'demo_engine.supervisor', '--root', ('"' + $V3DemoRoot + '"'))
Start-Process -FilePath $Python -ArgumentList $V3Arguments -WorkingDirectory $V3DemoRoot -WindowStyle Hidden
