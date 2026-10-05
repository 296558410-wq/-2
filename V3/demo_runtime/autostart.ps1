$ErrorActionPreference='Stop'
$V3DemoRoot=$PSScriptRoot
if(Test-Path -LiteralPath (Join-Path $V3DemoRoot 'runtime\STOP')) { exit 0 }
$V3Python='C:\AIQuant\.venv\Scripts\python.exe'
$V3Arguments=@('-m','demo_engine.supervisor','--root',('"'+$V3DemoRoot+'"'))
Start-Process -FilePath $V3Python -ArgumentList $V3Arguments -WorkingDirectory $V3DemoRoot -WindowStyle Hidden
