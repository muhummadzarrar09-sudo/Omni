@echo off
REM OMNI Windows 11 x64 managed launcher.
setlocal
chcp 65001 >nul
cd /d "%~dp0"

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start.ps1" %*
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" (
    echo Startup failed with exit code %RESULT%.
    echo Run: .venv\Scripts\python.exe -m omni_v2.core.runtime_cli preflight --primary --frontend
)
exit /b %RESULT%
