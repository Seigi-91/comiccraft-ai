@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" -InstallPrerequisites
if errorlevel 1 (
  echo Installation failed. Read the message above, then press any key.
  pause >nul
)
