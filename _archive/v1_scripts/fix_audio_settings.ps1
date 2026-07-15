# OMNI V3 - Fix Windows Audio Settings for -9999 Error
# Run as admin maybe
# Fixes exclusive mode that causes PyAudio -9999

Write-Host "=== OMNI V3 Audio Fix for Realtek -9999 Error ===" -ForegroundColor Cyan
Write-Host ""

Write-Host "Your mic test RMS 0.3918 = mic WORKS, but PyAudio fails with -9999" -ForegroundColor Green
Write-Host "Root cause: Windows exclusive mode + 48000Hz default vs 16000Hz request" -ForegroundColor Yellow
Write-Host ""

Write-Host "Manual fix (do this once):" -ForegroundColor Cyan
Write-Host "1. Press Win+R, type mmsys.cpl, press Enter"
Write-Host "2. Go to Recording tab"
Write-Host "3. Right-click Microphone (Realtek HD Audio Mic input) [13] -> Properties"
Write-Host "4. Advanced tab:"
Write-Host "   - Uncheck 'Allow applications to take exclusive control of this device'"
Write-Host "   - Set Default Format to 1 channel, 48000 Hz or 44100 Hz"
Write-Host "5. Levels tab: Set to 100, Boost +20dB or +30dB if available"
Write-Host "6. Enhancements tab: Uncheck all / Disable all enhancements"
Write-Host "7. Click OK, OK"
Write-Host ""

Write-Host "Alternatively, run this Powershell to auto-set (requires nircmd or registry):" -ForegroundColor Gray

# Try to disable exclusive mode via registry (may need reboot)
try {
    $micKey = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Capture"
    if (Test-Path $micKey) {
        Write-Host "Found audio capture keys, but exclusive mode is per-device - manual uncheck recommended" -ForegroundColor Yellow
    }
} catch {
    Write-Host "Registry access failed - do manual steps above" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== Testing FIXED pipeline (sounddevice primary) ===" -ForegroundColor Cyan
Write-Host "New pipeline uses sounddevice instead of PyAudio - handles resampling, fixes -9999"
Write-Host ""
Write-Host "Run:" -ForegroundColor Green
Write-Host "  python -m omni_v2.voice.test_mic_fixed"
Write-Host ""
Write-Host "Expected: RMS should be >0.01 when speaking" -ForegroundColor Green
