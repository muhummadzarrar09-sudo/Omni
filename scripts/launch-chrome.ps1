# Launch Chrome with Accessibility Flags for OMNI

$chromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"

if (-not (Test-Path $chromePath)) {
    $chromePath = "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
}

if (-not (Test-Path $chromePath)) {
    Write-Host "Chrome not found. Please install Chrome." -ForegroundColor Red
    exit 1
}

Write-Host "Launching Chrome with accessibility flags..." -ForegroundColor Cyan

& $chromePath --force-renderer-accessibility --remote-debugging-port=9222 --no-first-run

Write-Host "Chrome launched. CDP available at http://localhost:9222" -ForegroundColor Green
