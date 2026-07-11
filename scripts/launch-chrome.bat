@echo off
REM OMNI - Launch Chrome with CDP (Batch version - no ExecutionPolicy issue)
REM Use this if PowerShell script fails due to signing

echo Launching Chrome with accessibility flags...
echo CDP will be at http://localhost:9222

REM Try common Chrome paths
set CHROME_PATHS[0]=C:\Program Files\Google\Chrome\Application\chrome.exe
set CHROME_PATHS[1]=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe
set CHROME_PATHS[2]=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe

for %%i in (0 1 2) do (
    for /f "tokens=2 delims==" %%j in ('set CHROME_PATHS[%%i] 2^>nul') do (
        if exist "%%j" (
            echo Found Chrome at: %%j
            start "" "%%j" --remote-debugging-port=9222 --force-renderer-accessibility --enable-automation --disable-hang-monitor
            echo Chrome launched! CDP at http://localhost:9222
            goto :end
        )
    )
)

REM Fallback - try starting chrome via start command
echo Trying fallback launch...
start chrome --remote-debugging-port=9222 --force-renderer-accessibility

:end
pause
