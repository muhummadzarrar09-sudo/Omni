@echo off
REM OMNI safe uninstaller wrapper. User data is preserved unless -RemoveUserData is passed.
setlocal
chcp 65001 >nul
cd /d "%~dp0"

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\uninstall.ps1" %*
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" echo Uninstall failed or was cancelled with exit code %RESULT%.
exit /b %RESULT%
