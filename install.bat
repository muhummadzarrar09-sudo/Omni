@echo off
REM ============================================================
REM  OMNI V3 - First-time installer for Windows
REM  Called by start.bat or run directly.
REM ============================================================

setlocal enabledelayedexpansion
chcp 65001 >nul

echo.
echo   =====================================================
echo    OMNI V3 - Installing...
echo   =====================================================
echo.

REM Find Python
set PY=python
%PY% --version >nul 2>&1
if errorlevel 1 (
    set PY=py
    %PY% --version >nul 2>&1
    if errorlevel 1 (
        echo   ERROR: Python 3 not found.
        echo   Install Python 3.10+ from https://python.org
        echo   Make sure to check "Add Python to PATH" during install.
        pause
        exit /b 1
    )
)

for /f "tokens=*" %%i in ('%PY% --version') do set PY_VERSION=%%i
echo   Python: %PY_VERSION%
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

echo   Upgrading pip...
%PY% -m pip install --upgrade pip wheel setuptools --quiet

echo   Installing llama-cpp-python (prebuilt wheel)...
%PY% -m pip install llama-cpp-python ^
    --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu ^
    --quiet

echo   Installing OMNI V3 + dependencies...
%PY% -m pip install -e .[all] --quiet

echo.
echo   =====================================================
echo    OMNI V3 installed!
echo   =====================================================
echo.
echo   Next: start.bat will download the model (~1.1GB) and start the server.
echo.

exit /b 0
