@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install_codex.ps1"
if errorlevel 1 echo Connector setup failed. Read the message above.
pause
