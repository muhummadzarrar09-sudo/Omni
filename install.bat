@echo off
REM ============================================================
REM  OMNI V3 - Windows source-checkout convenience installer
REM  Called by start.bat or run directly.
REM  This is NOT a B01-qualified install path. B01 dependency qualification is
REM  CPython 3.11 on Linux x86_64; see docs\TROUBLESHOOTING.md for exact scope.
REM ============================================================

setlocal enabledelayedexpansion
chcp 65001 >nul

echo.
echo   =====================================================
echo    OMNI V3 - Windows source install (UNQUALIFIED)
echo   =====================================================
echo   This convenience path resolves dependency ranges from package indexes.
echo   It is not B01 artifact or Windows qualification evidence.
echo   See docs\TROUBLESHOOTING.md for the supported and tested scope.
echo.

REM Find Python
set PY=python
%PY% --version >nul 2>&1
if errorlevel 1 (
    set PY=py
    %PY% --version >nul 2>&1
    if errorlevel 1 (
        echo   ERROR: CPython 3.11 not found.
        echo   Install CPython 3.11 from https://python.org
        echo   Make sure to check "Add Python to PATH" during install.
        pause
        exit /b 1
    )
)

for /f "tokens=*" %%i in ('%PY% --version') do set PY_VERSION=%%i
echo   Python: %PY_VERSION%
%PY% -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)"
if errorlevel 1 (
    echo   ERROR: OMNI requires CPython ^>=3.11,^<3.12; found %PY_VERSION%.
    echo   Do not bypass the package's Requires-Python contract.
    pause
    exit /b 1
)
echo.

REM Create venv
if not exist .venv (
    echo   Creating virtual environment...
    %PY% -m venv .venv
    if errorlevel 1 (
        echo   ERROR: Could not create venv
        pause
        exit /b 1
    )
)

REM Activate venv
call .venv\Scripts\activate.bat
set PY=python

echo   Installing OMNI from this checkout with the declared all profile...
%PY% -m pip install ".[all]" --quiet
if errorlevel 1 (
    echo   ERROR: Source installation failed.
    echo   Windows and native all-profile dependencies are not B01-qualified.
    echo   See docs\TROUBLESHOOTING.md for profile and platform limitations.
    pause
    exit /b 1
)

echo.
echo   =====================================================
echo    OMNI V3 installed!
echo   =====================================================
echo.
echo   Next: start.bat will download the model (~1.1GB) and start the server.
echo.

exit /b 0
