param([ValidateSet('preview','check','render')][string]$Action='preview')
$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
$localEncoder=Get-ChildItem -LiteralPath (Join-Path $PSScriptRoot 'tools') -Directory -ErrorAction SilentlyContinue | Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'bin\ffmpeg.exe') } | Select-Object -First 1
if($localEncoder){$env:Path=(Join-Path $localEncoder.FullName 'bin')+';'+$env:Path}
$env:HYPERFRAMES_SKIP_SKILLS='1'
if($Action -eq 'preview'){
    npx.cmd --yes hyperframes@0.8.221 preview --background --port 3017
}elseif($Action -eq 'render'){
    npx.cmd --yes hyperframes@0.8.221 render --quality delivery --output renders/ComicCraft-AI-demo.mp4
}else{
    npx.cmd --yes hyperframes@0.8.221 check
}
if($LASTEXITCODE -ne 0){throw 'HyperFrames command failed.'}
