@echo off
echo === OMNI V3 ULTIMATE FIX - No 404, No PyAudio, No psutil 6.0.0 ===
echo Your RMS 0.014 = LOUD, mic works, sounddevice fixes -9999, no need PyAudio
echo.

echo 1. Uninstall broken PyAudio attempt...
pip uninstall PyAudio -y
pip uninstall pyaudio -y

echo.
echo 2. Install FINAL requirements - NO PyAudio, sounddevice only...
pip install psutil sounddevice==0.4.6

echo.
echo 3. Test mic with sounddevice (should show RMS 0.014 LOUD, no -9999)...
python -m omni_v2.voice.test_mic_fixed

echo.
echo 4. Starting FIXED web server - ROOT serves UI, no more /omni_v2/web_ui/... 404...
echo    This version serves neomorphism UI at http://localhost:8765/ directly
echo    And opens isolated Chrome profile to root
python -m omni_v2.web_server_fixed

echo.
echo If browser shows 404 again, manually open http://localhost:8765/
pause
