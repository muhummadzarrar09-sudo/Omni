@echo off
REM ============================================================
REM  OMNI V3 - One-click launcher for Windows
REM  Double-click this file to start the AGI.
REM ============================================================

setlocal enabledelayedexpansion
chcp 65001 >nul

echo.
echo   =====================================================
echo    OMNI V3 - Starting the AGI...
echo   =====================================================
echo.

REM Check if venv exists
if not exist .venv\Scripts\activate.bat (
    echo   First run - installing OMNI...
    echo.
    call install.bat
    if errorlevel 1 (
        echo.
        echo   ERROR: Installation failed.
        echo   Try running install.bat manually.
        pause
        exit /b 1
    )
)

REM Activate venv
echo   Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo   ERROR: Could not activate venv
    pause
    exit /b 1
)

REM Check if model is downloaded
if not exist data\models\qwen2.5-1.5b-instruct-q4_k_m.gguf (
    echo.
    echo   Model not found - downloading Qwen2.5-1.5B (~1.1GB)...
    echo   This is a one-time download.
    echo.
    omni model download
    if errorlevel 1 (
        echo.
        echo   ERROR: Model download failed.
        echo   Check your internet connection and try again.
        pause
        exit /b 1
    )
)

REM Start the backend
echo.
echo   Starting OMNI backend on http://localhost:8765 ...
echo   Opening browser in 5 seconds...
echo.
echo   =====================================================
echo    OMNI V3 is running!
echo.
echo    Backend:  http://localhost:8765
echo    API Docs: http://localhost:8765/docs
echo    UI:       http://localhost:3000 (run omni dev for UI)
echo.
echo    Press Ctrl+C to stop.
echo   =====================================================
echo.

REM Open browser after 5 seconds
start /min cmd /c "timeout /t 5 /nobreak >nul && start http://localhost:8765/docs"

REM Start the backend in foreground
omni start

REM If we get here, backend was stopped
echo.
echo   OMNI V3 stopped.
pause
