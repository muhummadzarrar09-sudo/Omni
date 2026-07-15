@echo off
TITLE OMNI V3 - Cinematic AGI Hermes Launcher
COLOR 0B
echo ==============================================================================
echo   🤖 OMNI V3 - CINEMATIC HALF-DUPLEX AGI HERMES LAUNCHER
echo ==============================================================================
echo.

:: 1. Detect project root folder (D:\Omni or D:\Omni\Omni)
SET PROJECT_ROOT=%~dp0
cd /d "%PROJECT_ROOT%"

:: Check if we are in outer folder and inner Omni exists
if exist "Omni\omni.py" (
    echo [INFO] Detected inner folder structure. Entering Omni\...
    cd /d "%PROJECT_ROOT%Omni"
    SET PROJECT_ROOT=%~dp0Omni\
)

echo [INFO] Project Root: %CD%
echo.

:: 2. Check Virtual Environment
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment python.exe not found at %CD%\.venv\Scripts\python.exe
    echo Please run: python -m venv .venv ^&^& .venv\Scripts\activate ^&^& pip install -r backend_fastapi\requirements.txt
    pause
    exit /b 1
)

:: 3. Check node_modules in frontend_next
if not exist "frontend_next\node_modules\" (
    echo [INFO] Installing Next.js dependencies in frontend_next...
    cd /d "%CD%\frontend_next"
    call npm install
    cd /d "%~dp0"
    if exist "Omni\omni.py" cd /d "%~dp0Omni"
)

echo ==============================================================================
echo   🚀 LAUNCHING FASTAPI BACKEND (Port 8765) + NEXT.JS CINEMATIC UI (Port 3000)
echo ==============================================================================
echo.

:: 4. Launch FastAPI in a separate dedicated window using python -m uvicorn (fixes launcher WinError!)
echo [1/2] Starting FastAPI Backend on Port 8765...
start "OMNI V3 - FastAPI Brain Backend (Port 8765)" /min cmd /c "cd /d "%CD%\backend_fastapi" && ..\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8765 && pause"

:: Give backend 3 seconds to warm up
timeout /t 3 /nobreak >nul

:: 5. Open browser automatically to Next.js UI
echo [2/2] Launching Next.js Cinematic Stage on Port 3000...
start "" "http://localhost:3000"

:: 6. Launch Next.js in this terminal window
cd /d "%CD%\frontend_next"
call npm run dev

echo.
echo [INFO] Both servers shut down.
pause
