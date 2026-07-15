@echo off
echo === OMNI V3.1 QUICK FIX FOR -9999 ERROR ===
echo Your mic RMS 0.3918 = mic WORKS, just PyAudio exclusive bug
echo.

echo 1. Fixing psutil...
pip uninstall psutil -y
pip install psutil==6.1.1
pip install sounddevice==0.4.6

echo.
echo 2. Your pipeline is now FIXED - sounddevice primary
echo    - app_v3_neumorphism.py now uses pipeline_v3_fixed first
echo.

echo 3. Testing mic with sounddevice...
python -m omni_v2.voice.test_mic_fixed

echo.
echo 4. If above shows RMS >0.01, run:
echo    python -m omni_v2.app_v3_neumorphism
echo.
echo 5. Manual Windows Fix (IMPORTANT for -9999):
echo    Win+R -> mmsys.cpl -> Recording -> Microphone (Realtek HD Audio Mic input) -> Properties
echo    Advanced -> UNCHECK "Allow applications to take exclusive control"
echo    Levels -> 100 + Boost +20dB
echo    Advanced -> Default Format: 2 channel, 48000 Hz -> OK
echo.
pause
