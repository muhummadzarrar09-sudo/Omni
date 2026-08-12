@echo off
REM OMNI Windows 11 x64 primary installer wrapper.
REM This is not B01 evidence; see docs\TROUBLESHOOTING.md for exact scope.
REM scripts\install.ps1 enforces native x64 CPython 3.11.
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
