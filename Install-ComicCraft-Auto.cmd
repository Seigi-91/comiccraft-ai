@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" -InstallPrerequisites -SetupCodex
if errorlevel 1 echo Automatic connector setup did not complete. Existing work was preserved.
pause
