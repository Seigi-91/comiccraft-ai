param([switch]$InstallPrerequisites, [string]$InstallDirectory = (Join-Path $env:LOCALAPPDATA 'ComicCraft-AI'), [switch]$NoStart)
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
function Refresh-TaskPath {
    $env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
}
function Ensure-Package([string]$Command, [string]$Package) {
    if ($Command -eq 'python' -and (Get-Command py -ErrorAction SilentlyContinue)) {
        & py -3 -c 'import sys; assert sys.version_info >= (3,11)'
        if ($LASTEXITCODE -eq 0) { return }
    }
    $installed = Get-Command $Command -ErrorAction SilentlyContinue
    if ($installed -and $installed.Source -notlike '*WindowsApps*') {
        if ($Command -eq 'node') {
            $versionText = & node --version
            if ($LASTEXITCODE -eq 0 -and ([Version]$versionText.Trim().TrimStart('v')).Major -ge 20) { return }
        } elseif ($Command -eq 'python') {
            & python -c 'import sys; assert sys.version_info >= (3,11)'
            if ($LASTEXITCODE -eq 0) { return }
        } else { return }
    }
    if (-not $InstallPrerequisites -or -not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "Missing $Command. Install $Package, reopen this installer, or use the documented manual setup."
    }
    & winget install --id $Package --exact --silent --accept-package-agreements --accept-source-agreements --disable-interactivity
    if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed: $Package" }
    Refresh-TaskPath
}
$sourceDirectory = Join-Path $InstallDirectory 'source'
if (-not (Test-Path -LiteralPath (Join-Path $sourceDirectory 'start.ps1'))) {
    New-Item -ItemType Directory -Path $InstallDirectory -Force | Out-Null
    $downloadDirectory = Join-Path $InstallDirectory ('download-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $downloadDirectory | Out-Null
    $archivePath = Join-Path $downloadDirectory 'source.zip'
    # A tagged source archive is reproducible and never includes the author's database or credentials.
    $sourceUrl = 'https://github.com/Seigi-91/comiccraft-ai/archive/refs/tags/v2.1.0.zip'
    Write-Host 'Downloading ComicCraft AI v2.1.0 from GitHub...'
    Invoke-WebRequest -UseBasicParsing -Uri $sourceUrl -OutFile $archivePath
    Expand-Archive -LiteralPath $archivePath -DestinationPath $downloadDirectory
    $extractedDirectory = Join-Path $downloadDirectory 'comiccraft-ai-2.1.0'
    if (-not (Test-Path -LiteralPath (Join-Path $extractedDirectory 'start.ps1'))) { throw 'Downloaded archive is incomplete.' }
    # Only copy a fresh installation. Never replace an existing .env, database or user work.
    if (Test-Path -LiteralPath $sourceDirectory) { throw 'An incomplete source directory already exists. Choose another InstallDirectory; existing files were preserved.' }
    Copy-Item -LiteralPath $extractedDirectory -Destination $sourceDirectory -Recurse
}
if ($NoStart) { Write-Host "Source installed at $sourceDirectory. Run start.ps1 there to install dependencies and launch."; exit 0 }
Ensure-Package 'python' 'Python.Python.3.12'
Ensure-Package 'node' 'OpenJS.NodeJS.LTS'
& (Join-Path $sourceDirectory 'start.ps1')
