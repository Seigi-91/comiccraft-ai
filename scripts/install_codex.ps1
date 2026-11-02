param([string]$InstallDirectory = (Join-Path $env:LOCALAPPDATA 'ComicCraft-AI\CodexCLI'))
$ErrorActionPreference = 'Stop'
$nodeCommand = Get-Command node -ErrorAction SilentlyContinue
$npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
if (-not $nodeCommand -or -not $npmCommand) { throw 'Install Node.js 20+ first, then rerun this connector installer.' }
$nodeVersion = & ($nodeCommand.Source) --version
if (([Version]$nodeVersion.Trim().TrimStart('v')).Major -lt 20) { throw 'Node.js 20+ is required.' }
$codexEntry = Join-Path $InstallDirectory 'node_modules\@openai\codex\bin\codex.js'
if (-not (Test-Path -LiteralPath $codexEntry)) {
    New-Item -ItemType Directory -Path $InstallDirectory -Force | Out-Null
    & ($npmCommand.Source) install --prefix $InstallDirectory '@openai/codex@0.166.0' --no-audit --no-fund
    if ($LASTEXITCODE -ne 0) { throw 'Official Codex CLI installation failed. Check network/proxy and retry.' }
}
& ($nodeCommand.Source) $codexEntry --version
Write-Host 'Sign in with your own ChatGPT account in the official browser flow. No API key is required by this connector.'
& ($nodeCommand.Source) $codexEntry login
if ($LASTEXITCODE -ne 0) { throw 'Login did not complete. Existing project files were preserved.' }
Write-Host 'Return to ComicCraft settings and refresh connector status. Each capability still needs an explicit real test.'
