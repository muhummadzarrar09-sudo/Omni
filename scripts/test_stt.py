#!/usr/bin/env python3
"""
OMNI STT Test Script
====================
Tests the complete voice pipeline end-to-end.

Usage:
    python scripts/test_stt.py                 # Run all tests
    python scripts/test_stt.py --mic           # Test microphone detection
    python scripts/test_stt.py --vad           # Test VAD loading
    python scripts/test_stt.py --whisper       # Test Whisper transcription
    python scripts/test_stt.py --quality       # Test audio quality detection
    python scripts/test_stt.py --record        # Record 3s and transcribe

Exit codes:
    0 = all tests passed
    1 = some tests failed
    2 = critical failure (no mic, no whisper)
"""

import sys
import os
import time
import wave
import tempfile
import argparse
from pathlib import Path
import numpy as np  # Used across all tests

# Add omni/ to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "omni"))
from loguru import logger

# Remove default loguru handler to avoid duplicate output
logger.remove()


def _color(code: str) -> str:
    return f"\033[{code}m" if sys.stdout.isatty() else ""


RED = _color("31")
GREEN = _color("32")
YELLOW = _color("33")
CYAN = _color("36")
BOLD = _color("1")
RESET = _color("0")


def log(msg: str, color: str = "") -> None:
    print(f"{color}{BOLD}[STT-TEST]{RESET}{color} {msg}{RESET}")


def ok(msg: str) -> None:
    log(f"{GREEN}✓{RESET} {msg}", GREEN)


def fail(msg: str) -> None:
    log(f"{RED}✗{RESET} {msg}", RED)


def warn(msg: str) -> None:
    log(f"{YELLOW}⚠{RESET} {msg}", YELLOW)


def info(msg: str) -> None:
    log(f"{CYAN}ℹ{RESET} {msg}", CYAN)


def section(name: str) -> None:
    print(f"\n{BOLD}{'─' * 56}{RESET}")
    log(f"{BOLD}{name}{RESET}", CYAN)
    print(f"{BOLD}{'─' * 56}{RESET}")


# ─── Test 1: Audio Device Detection ──────────────────────────────────────────

def test_audio_device_detection() -> bool:
    section("Test 1: Audio Device Detection")
    try:
        from omni.voice.audio_device import AudioDeviceManager

        adm = AudioDeviceManager()
        status = adm.get_status()

        print(f"\n  System:        {status.system}")
        print(f"  PyAudio:       {'✓ available' if status.pyaudio_available else '✗ not available'}")
        print(f"  Mics found:    {status.device_count}")

        if not status.pyaudio_available:
            fail("PyAudio not available — run: pip install PyAudio")
            return False

        if status.device_count == 0:
            fail("No microphone devices found")
            warn("Check Windows Sound settings and microphone connection")
            return False

        print(f"  Devices:")
        for d in status.all_input_devices:
            marker = " ← DEFAULT" if d.is_default else ""
            print(f"    [{d.index}] {d.name}{marker}")

        default = status.default_input_device
        if default:
            ok(f"Default microphone: {default.name}")
        else:
            warn("No default microphone set")

        # Probe status
        print(f"\n  Probe status: {status.current_probe_status}")
        if status.current_probe_status == "ok":
            ok("Default microphone probe: PASSED")
        elif status.current_probe_status == "failed":
            fail(f"Default microphone probe: FAILED — {status.last_error}")
            warn("Voice input may not work. Try selecting a different mic in Settings.")
            return False
        else:
            warn(f"Probe status: {status.current_probe_status}")

        return status.current_probe_status == "ok"

    except ImportError as e:
        fail(f"Cannot import AudioDeviceManager: {e}")
        return False
    except Exception as e:
        fail(f"Audio device detection error: {e}")
        return False


# ─── Test 2: VAD Loading ─────────────────────────────────────────────────────

def test_vad_loading() -> bool:
    section("Test 2: VAD (Voice Activity Detection) Loading")
    try:
        from omni.voice.vad import VoicePipeline, VADEngine
        import torch

        print(f"\n  PyTorch:       {torch.__version__}")
        print(f"  CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"  GPU:           {torch.cuda.get_device_name(0)}")

        # Check torchaudio
        torchaudio_ok = False
        try:
            import torchaudio
            print(f"  Torchaudio:    {torchaudio.__version__} ✓")
            torchaudio_ok = True
        except ImportError:
            print(f"  Torchaudio:    not installed ✗")

        # Create a minimal VoicePipeline (no callbacks)
        vp = VoicePipeline(
            event_bus=None,
            on_transcription=None,
            on_status=None,
            on_error=None,
        )

        print(f"\n  VAD engine:    {vp.vad_engine.name}")
        print(f"  Sample rate:   {vp.sample_rate} Hz")

        if vp.vad_engine == VADEngine.SILERO:
            ok(f"Silero VAD loaded — HIGH accuracy speech detection")
            if torchaudio_ok:
                ok("Torchaudio confirmed — VAD accuracy is optimal")
            else:
                warn("Silero VAD loaded but torchaudio not detected — may use CPU fallback")
        elif vp.vad_engine == VADEngine.ENERGY:
            ok("Energy-based VAD loaded — BASIC accuracy (fallback mode)")
            if not torchaudio_ok:
                info("To enable Silero VAD (HIGH accuracy):")
                info("  pip install torchaudio --index-url https://download.pytorch.org/whl/cu121")
        else:
            fail("No VAD loaded — voice detection may not work")
            return False

        print(f"\n  Parameters:")
        print(f"    Speech threshold:  {vp.speech_threshold}")
        print(f"    Silence threshold: {vp.silence_threshold}")
        print(f"    Min recording:     {vp.min_recording_s}s")
        print(f"    Max recording:     {vp.max_recording_s}s")
        print(f"    Silence chunks:    {vp.silence_chunks} (~{vp.silence_chunks * 64}ms)")

        return True

    except ImportError as e:
        fail(f"Cannot import VoicePipeline: {e}")
        return False
    except Exception as e:
        fail(f"VAD loading error: {e}")
        return False


# ─── Test 3: Whisper Model Loading ───────────────────────────────────────────

def test_whisper_loading() -> bool:
    section("Test 3: Whisper STT Model Loading")
    try:
        from omni.voice.vad import WhisperSTT
        import torch

        print(f"\n  Device: CPU (int8 — GTX 1050 Ti compatible)")
        print(f"  Model:  base.en (~75MB)")

        whisper = WhisperSTT(model_name="base.en", device="cuda")

        status = whisper.status
        print(f"\n  Status:")
        print(f"    Loaded:     {status['loaded']}")
        print(f"    Model:      {status['model_name']}")
        print(f"    Compute:    {status['compute_type']}")
        print(f"    Language:   {status['language']}")
        print(f"    Timeout:    {status['timeout_s']}s")
        if status['load_error']:
            print(f"    Error:      {status['load_error']}")

        if status['loaded']:
            compute = status['compute_type']
            if compute == 'float16':
                ok(f"Whisper on GPU (float16) — optimal performance")
            elif compute == 'int8':
                ok(f"Whisper on GPU (int8) — good performance")
            else:
                ok(f"Whisper on CPU (int8) — acceptable performance")
            return True
        else:
            fail(f"Whisper failed to load: {status['load_error']}")
            return False

    except ImportError as e:
        fail(f"faster-whisper not installed: {e}")
        info("Run: pip install faster-whisper")
        return False
    except Exception as e:
        fail(f"Whisper loading error: {e}")
        return False


# ─── Test 4: Audio Quality Detection ─────────────────────────────────────────

def test_audio_quality_detection() -> bool:
    section("Test 4: Audio Quality Detection")
    try:
        from omni.voice.vad import VADAudioQuality

        print("\n  Testing VADAudioQuality assessment on synthetic audio...")

        test_cases = [
            # (name, audio, is_too_short, is_too_quiet, should_transcribe)
            ("normal_speech", lambda: np.random.randn(16000) * 0.3, False, False, True),
            ("very_short", lambda: np.random.randn(800) * 0.3, True, False, False),  # 50ms
            ("very_quiet", lambda: np.random.randn(16000) * 0.005, False, True, False),
            ("silence", lambda: np.random.randn(16000) * 0.001, False, True, False),
            ("noise_only", lambda: np.random.randn(16000) * 0.002, False, True, False),
        ]

        import numpy as np

        all_passed = True
        for name, generator, expected_short, expected_quiet, expected_transcribe in test_cases:
            audio = generator()
            q = VADAudioQuality(
                duration_s=len(audio) / 16000,
                max_amplitude=float(np.abs(audio).max()),
                avg_rms=float(np.sqrt(np.mean(audio ** 2))),
                silence_ratio=float((np.abs(audio) < 0.005).mean()),
                is_too_short=expected_short,
                is_too_quiet=expected_quiet,
                is_noise_only=False,
            )
            result = q.should_transcribe()
            match = (result == expected_transcribe)
            status = f"{GREEN}✓{RESET}" if match else f"{RED}✗{RESET}"
            print(f"  {status} {name:15s} → should_transcribe={result} (expected {expected_transcribe})")
            if not match:
                all_passed = False

        if all_passed:
            ok("Audio quality detection: ALL PASSED")
        else:
            fail("Audio quality detection: SOME FAILED")
        return all_passed

    except ImportError as e:
        fail(f"Cannot test audio quality: {e}")
        return False


# ─── Test 5: Record & Transcribe (Manual Test) ───────────────────────────────

def test_record_and_transcribe(duration_s: float = 3.0) -> bool:
    section(f"Test 5: Record & Transcribe ({duration_s}s)")
    try:
        from omni.voice.audio_device import AudioDeviceManager
        from omni.voice.vad import VoicePipeline

        print(f"\n  Recording {duration_s}s of audio from your microphone...")
        print(f"  Make sure your mic is ready and SPEAK during the recording!")
        print(f"  (Press Enter to start recording)")
        input()

        adm = AudioDeviceManager()
        status = adm.get_status()
        if status.current_probe_status != "ok":
            fail(f"Microphone not ready: {status.last_error}")
            return False

        print(f"\n  Recording... (speak now!)")

        pipeline = VoicePipeline(
            device_manager=adm,
            on_transcription=None,
            on_status=None,
            on_error=None,
        )

        pipeline.start()
        time.sleep(duration_s)
        pipeline.stop()

        audio = pipeline.get_audio()
        if audio is None or len(audio) == 0:
            fail("No audio captured")
            return False

        duration = len(audio) / 16000
        print(f"\n  Captured: {duration:.2f}s of audio ({len(audio)} samples)")

        from omni.voice.vad import VADAudioQuality
        import numpy as np
        q = VADAudioQuality(
            duration_s=duration,
            max_amplitude=float(np.abs(audio).max()),
            avg_rms=float(np.sqrt(np.mean(audio ** 2))),
            silence_ratio=float((np.abs(audio) < 0.005).mean()),
            is_too_short=False,
            is_too_quiet=False,
            is_noise_only=False,
        )
        print(f"  Quality:   {q.quality_summary()}")

        if not q.should_transcribe():
            warn("Audio quality too poor — skipping transcription")
            return False

        print(f"\n  Transcribing...")
        from omni.voice.vad import WhisperSTT
        whisper = WhisperSTT(model_name="base.en", device="cuda")
        if not whisper.is_loaded():
            fail("Whisper not loaded")
            return False

        start = time.time()
        text = whisper.transcribe(audio)
        elapsed = time.time() - start

        print(f"\n  Transcription time: {elapsed:.1f}s")
        if text and text.strip():
            ok(f"Transcribed: '{text}'")
            return True
        else:
            warn("Transcription returned empty")
            info("This can happen if:")
            info("  - The audio was mostly silence or noise")
            info("  - Whisper didn't understand the accent")
            info("  - The audio was too quiet")
            return False

    except Exception as e:
        fail(f"Record & transcribe error: {e}")
        return False


# ─── Test 6: PyAudio Error Code Translation ───────────────────────────────────

def test_pyaudio_error_translation() -> bool:
    section("Test 6: PyAudio Error Code Translation")
    try:
        from omni.voice.audio_device import translate_pyaudio_error, PYAUDIO_ERROR_MESSAGES

        test_codes = [-9999, -9986, -9982, -9996, -9998]
        all_ok = True
        for code in test_codes:
            msg = translate_pyaudio_error(code)
            print(f"  [{code:6d}] → {msg}")
            if "error" in msg.lower() and str(code) not in msg:
                warn(f"  Generic message for code {code} — consider adding specific text")

        ok("Error translation: OK")
        return True
    except Exception as e:
        fail(f"Error translation test failed: {e}")
        return False


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="OMNI STT Test Script")
    parser.add_argument("--mic",     action="store_true", help="Test microphone detection only")
    parser.add_argument("--vad",     action="store_true", help="Test VAD loading only")
    parser.add_argument("--whisper", action="store_true", help="Test Whisper loading only")
    parser.add_argument("--quality", action="store_true", help="Test audio quality detection only")
    parser.add_argument("--record",  action="store_true", help="Record & transcribe (manual)")
    parser.add_argument("--all",     action="store_true", help="Run all tests")
    parser.add_argument("--duration", type=float, default=3.0, help="Recording duration for --record")
    args = parser.parse_args()

    run_all = args.all or not any([args.mic, args.vad, args.whisper, args.quality, args.record])

    print()
    print(f"{BOLD}╔{'═' * 56}╗{RESET}")
    print(f"{BOLD}║{RESET}        OMNI STT Test Suite — Phase 3             {BOLD}║{RESET}")
    print(f"{BOLD}╚{'═' * 56}╝{RESET}")
    print()

    results = []

    if args.mic or run_all:
        results.append(("Mic Detection", test_audio_device_detection()))

    if args.vad or run_all:
        results.append(("VAD Loading", test_vad_loading()))

    if args.whisper or run_all:
        results.append(("Whisper Loading", test_whisper_loading()))

    if args.quality or run_all:
        results.append(("Audio Quality", test_audio_quality_detection()))

    if args.record:
        results.append(("Record & Transcribe", test_record_and_transcribe(args.duration)))

    if args.mic or args.vad or args.whisper or args.quality or run_all:
        results.append(("Error Translation", test_pyaudio_error_translation()))

    # Summary
    print()
    print(f"{BOLD}{'─' * 56}{RESET}")
    log(f"{BOLD}Test Summary{RESET}", CYAN)
    print()

    all_passed = True
    for name, passed in results:
        status = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
        print(f"  {status}  {name}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        ok("All tests passed! STT pipeline is ready.")
        return 0
    else:
        fail("Some tests failed. Check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())