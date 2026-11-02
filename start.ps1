param([ValidateRange(1024,65535)][int]$Port = 8000, [switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$OutputEncoding = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $OutputEncoding
$env:PYTHONIOENCODING = 'utf-8'
Set-Location -LiteralPath $PSScriptRoot
$pythonPath = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    $bundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    if (Test-Path -LiteralPath $bundledPython) {
        & $bundledPython -m venv .venv
    } elseif (Get-Command py -ErrorAction SilentlyContinue) {
        py -3 -m venv .venv
    } else {
        python -m venv .venv
    }
    if ($LASTEXITCODE -ne 0) { throw 'Please install Python 3.11 or newer.' }
}
if (-not (Test-Path -LiteralPath '.env')) { Copy-Item -LiteralPath '.env.example' -Destination '.env' }
& $pythonPath -c 'import sys; assert sys.version_info >= (3,11)'
if ($LASTEXITCODE -ne 0) { throw 'Python 3.11+ required.' }
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw 'Please install Node.js 20+.' }
$nodeVersionText = & node --version
if ($LASTEXITCODE -ne 0 -or ([Version]$nodeVersionText.Trim().TrimStart('v')).Major -lt 20) { throw 'Node.js 20+ required.' }
& $pythonPath -m pip install -e .
if ($LASTEXITCODE -ne 0) { throw 'Backend dependency installation failed.' }
Push-Location frontend
try {
    if (-not (Test-Path -LiteralPath 'node_modules')) {
        npm.cmd ci
        if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
    }
    npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
} finally { Pop-Location }
$available = $false
for ($candidate = $Port; $candidate -le [Math]::Min(65535, $Port + 20); $candidate++) {
    $listener = New-Object System.Net.Sockets.TcpListener ([System.Net.IPAddress]::Loopback, $candidate)
    try { $listener.Start(); $Port = $candidate; $available = $true; break }
    catch [System.Net.Sockets.SocketException] { }
    finally { $listener.Stop() }
}
if (-not $available) { throw 'No free local port found. Choose another -Port.' }
$env:APP_PORT = [string]$Port
& $pythonPath -m app.services.diagnostics
Write-Host "ComicCraft AI: http://127.0.0.1:$Port"
Write-Host 'Keep this window open. Ctrl+C stops the website.'
if (-not $NoBrowser) {
    $helper = Join-Path $PSScriptRoot 'scripts\open_browser.ps1'
    Start-Process -FilePath powershell.exe -WindowStyle Hidden -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"' + $helper + '"'), '-Port', [string]$Port)
}
& $pythonPath -m uvicorn app.main:app --host 127.0.0.1 --port $Port
