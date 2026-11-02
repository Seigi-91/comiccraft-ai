param([string]$InstallDirectory = (Join-Path $env:LOCALAPPDATA 'ComicCraft-AI\CodexCLI'))
$ErrorActionPreference = 'Stop'
$nodeCommand = Get-Command node -ErrorAction SilentlyContinue
$npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
if (-not $nodeCommand -or -not $npmCommand) { throw 'Install Node.js 20+ first, then rerun this connector installer.' }
$nodeVersion = & ($nodeCommand.Source) --version
if (([Version]$nodeVersion.Trim().TrimStart('v')).Major -lt 20) { throw 'Node.js 20+ is required.' }
$codexEntry = Join-Path $InstallDirectory 'node_modules\@openai\codex\bin\codex.js'
$needsInstall = -not (Test-Path -LiteralPath $codexEntry)
if (-not $needsInstall) {
    $installedVersion = & ($nodeCommand.Source) $codexEntry --version
    $needsInstall = $LASTEXITCODE -ne 0 -or $installedVersion -notmatch '\b0\.166\.0\b'
}
if ($needsInstall) {
    New-Item -ItemType Directory -Path $InstallDirectory -Force | Out-Null
    & ($npmCommand.Source) install --prefix $InstallDirectory '@openai/codex@0.166.0' --no-audit --no-fund
    if ($LASTEXITCODE -ne 0) { throw 'Official Codex CLI installation failed. Check network/proxy and retry.' }
}
& ($nodeCommand.Source) $codexEntry --version
function Test-ChatGPTLogin {
    # Windows PowerShell can wrap native stderr as ErrorRecords even for status.
    $ErrorActionPreference = 'Continue'
    $loginStatus = & ($nodeCommand.Source) $codexEntry login status 2>&1
    return ($LASTEXITCODE -eq 0 -and ($loginStatus -join ' ') -match 'ChatGPT')
}
if (Test-ChatGPTLogin) {
    Write-Host 'Existing ChatGPT login detected. Open the website connection wizard to verify and enable capabilities.'
    return
}
Write-Host 'Sign in with your own ChatGPT account in the official browser flow. No API key is required by this connector.'
& ($nodeCommand.Source) $codexEntry login
if ($LASTEXITCODE -ne 0) { throw 'Login did not complete. Existing project files were preserved.' }
if (-not (Test-ChatGPTLogin)) { throw 'Use Sign in with ChatGPT to enable this connector. API-key login is not used automatically.' }
Write-Host 'Return to ComicCraft settings and refresh connector status. Each capability still needs an explicit real test.'
