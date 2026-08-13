@echo off
REM OMNI native Windows 11 Arm64/x64 installer wrapper.
REM This is not B01 evidence; see docs\TROUBLESHOOTING.md for exact scope.
REM scripts\install.ps1 enforces architecture-matched 64-bit CPython 3.11.
setlocal
chcp 65001 >nul
cd /d "%~dp0"

where powershell.exe >nul 2>&1
if errorlevel 1 (
    echo ERROR: Windows PowerShell is required.
    exit /b 1
)

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install.ps1" %*
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" echo Installation failed with exit code %RESULT%.
exit /b %RESULT%
