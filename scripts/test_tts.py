#!/usr/bin/env python3
"""
OMNI TTS Test Script
====================
Tests the TTS engine end-to-end — all three tiers.

Usage:
    python scripts/test_tts.py                    # Test all engines
    python scripts/test_tts.py --kokoro           # Test Kokoro only
    python scripts/test_tts.py --sapi             # Test SAPI only
    python scripts/test_tts.py --voices           # Preview all Kokoro voices
    python scripts/test_tts.py --text "Hello OMNI" # Speak custom text

Exit codes:
    0 = all tests passed
    1 = TTS completely unavailable (silent mode)
    2 = test error
"""

import sys
import os
import time
import argparse
from pathlib import Path

# Add omni/ to path for imports (after Path is defined)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "omni"))


def _color(code: str) -> str:
    return f"\033[{code}m" if sys.stdout.isatty() else ""


RED = _color("31")
GREEN = _color("32")
YELLOW = _color("33")
CYAN = _color("36")
BOLD = _color("1")
RESET = _color("0")


def log(msg: str, color: str = "") -> None:
    print(f"{color}{BOLD}[TTS-TEST]{RESET}{color} {msg}{RESET}")


def ok(msg: str) -> None:
    log(f"{GREEN}✓{RESET} {msg}", GREEN)


def fail(msg: str) -> None:
    log(f"{RED}✗{RESET} {msg}", RED)


def warn(msg: str) -> None:
    log(f"{YELLOW}⚠{RESET} {msg}", YELLOW)


def info(msg: str) -> None:
    log(f"{CYAN}ℹ{RESET} {msg}", CYAN)


def wait(prompt: str = "Press Enter to continue...") -> None:
    input(f"  {YELLOW}{prompt}{RESET}")


def test_kokoro_instantiation() -> bool:
    """Test that Kokoro-ONNX can be instantiated."""
    print()
    log(f"{BOLD}Test 1: Kokoro-ONNX Instantiation{RESET}", CYAN)
    print("-" * 40)

    try:
        from omni.tts.kokoro_tts import KokoroTTS, VOICE_CATALOG
        ok(f"kokoro_tts module imported OK")
        ok(f"Voice catalog: {len(VOICE_CATALOG)} voices defined")
    except ImportError as e:
        fail(f"Cannot import KokoroTTS: {e}")
        return False

    # Check model files
    tts = KokoroTTS()
    model_ok, voices_ok = tts.model_files_present

    if not model_ok:
        warn(f"kokoro-v1.0.onnx not found at {tts.model_dir}")
        warn("Run: python scripts/download_models.py --kokoro")
    else:
        ok(f"kokoro-v1.0.onnx present")

    if not voices_ok:
        warn(f"voices-v1.0.bin not found at {tts.model_dir}")
        warn("Run: python scripts/download_models.py --kokoro")
    else:
        ok(f"voices-v1.0.bin present")

    # Show engine status
    status = tts.get_status()
    print(f"\n  Engine type:    {status['engine_type']}")
    print(f"  Model dir:      {status['model_dir']}")
    print(f"  Voice:          {status['voice']}")
    print(f"  Speed:          {status['speed']}")
    print(f"  Speaking:       {status['is_speaking']}")

    if status['engine_type'] == 'kokoro-onnx':
        ok(f"TTS engine: Kokoro-ONNX active ✓")
    elif status['engine_type'] == 'pyttsx3':
        warn(f"TTS engine: Windows SAPI (Kokoro model files missing)")
        print(f"  {YELLOW}→ Download from: https://github.com/nazdridoy/kokoro-tts/releases/tag/v1.0.0{RESET}")
    else:
        fail(f"TTS engine: SILENT MODE (no engine available)")
        return False

    return True


def test_kokoro_speak(tts: "KokoroTTS", text: str = "Hello! OMNI text to speech is working. This is a test.") -> bool:
    """Test that Kokoro can generate and play audio."""
    print()
    log(f"{BOLD}Test 2: Kokoro Speech Generation{RESET}", CYAN)
    print("-" * 40)

    if tts.engine_type != 'kokoro-onnx':
        warn("Kokoro-ONNX not active, skipping generation test")
        return False

    print(f"  Speaking: \"{text[:60]}{'...' if len(text) > 60 else ''}\"")
    print(f"  Voice:    {tts.voice}")
    print(f"  Speed:    {tts.speed}x")
    print()

    completed = False

    def on_complete():
        nonlocal completed
        completed = True
        elapsed = time.time() - start_time
        ok(f"Speech completed in {elapsed:.1f}s")

    start_time = time.time()
    tts.speak(text, callback=on_complete)

    # Wait for completion (up to 30s)
    timeout = 30
    while not completed and (time.time() - start_time) < timeout:
        time.sleep(0.1)

    if not completed:
        fail(f"Speech did not complete within {timeout}s")
        tts.stop()
        return False

    return True


def test_sapi_speak() -> bool:
    """Test Windows SAPI as fallback."""
    print()
    log(f"{BOLD}Test 3: Windows SAPI Fallback{RESET}", CYAN)
    print("-" * 40)

    if sys.platform != 'win32':
        info("Not on Windows — SAPI test skipped")
        return True

    try:
        import pyttsx3
        ok("pyttsx3 installed")
    except ImportError:
        fail("pyttsx3 not installed (run: pip install pyttsx3)")
        return False

    try:
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        ok(f"SAPI engine started, {len(voices)} voices available")
        print(f"  First voice: {voices[0].name if voices else 'N/A'}")

        # Test speak
        print("  Speaking test sentence...")
        engine.say("Windows SAPI text to speech test. This is the fallback engine.")
        engine.runAndWait()
        ok("SAPI speech completed")
        return True

    except Exception as e:
        fail(f"SAPI test failed: {e}")
        return False


def test_voice_preview() -> bool:
    """Preview 4 recommended voices."""
    print()
    log(f"{BOLD}Test 4: Voice Preview (4 recommended voices){RESET}", CYAN)
    print("-" * 40)
    print(f"  Each voice will speak a test sentence.")
    print(f"  Press Enter to hear the next voice, or Q to skip.\n")

    from omni.tts.kokoro_tts import KokoroTTS, VOICE_CATALOG, VOICE_DEFAULTS

    tts = KokoroTTS()
    if tts.engine_type != 'kokoro-onnx':
        warn("Kokoro-ONNX not active, skipping voice preview")
        return False

    preview_voices = [
        ("af_sarah",    "Hello! I'm Sarah. This is OMNI's default voice — bright and warm."),
        ("am_michael",  "Hello! I'm Michael. A deep and steady voice for clear communication."),
        ("bf_gemma",    "Hello! I'm Gemma. A British female voice — elegant and refined."),
        ("am_patrick",  "Hello! I'm Patrick. A warm American male voice for friendly replies."),
    ]

    results = []
    for voice_id, test_text in preview_voices:
        cat = VOICE_CATALOG.get(voice_id, ("Unknown", ""))
        print(f"\n  [{voice_id}] {cat[0]} — {cat[1]}")
        choice = input(f"  Play (Enter) or Skip (S)? ").strip().lower()
        if choice == 's':
            print("  Skipped.")
            continue

        completed = [False]

        def on_done():
            completed[0] = True

        tts.preview_voice(voice_id, callback=on_done)
        timeout = 20
        start = time.time()
        while not completed[0] and (time.time() - start) < timeout:
            time.time()
        if completed[0]:
            ok(f"{voice_id} — completed")
            results.append((voice_id, True))
        else:
            fail(f"{voice_id} — timed out")
            tts.stop()
            results.append((voice_id, False))

    print()
    passed = sum(1 for _, ok_ in results if ok_)
    ok(f"Voice preview done: {passed}/{len(results)} successful")

    return True


def test_edge_cases() -> bool:
    """Test edge cases: empty text, very long text, concurrent calls."""
    print()
    log(f"{BOLD}Test 5: Edge Cases{RESET}", CYAN)
    print("-" * 40)

    from omni.tts.kokoro_tts import KokoroTTS

    tts = KokoroTTS()
    if tts.engine_type != 'kokoro-onnx':
        warn("Kokoro-ONNX not active, skipping edge case tests")
        return False

    # Edge case 1: Empty string
    print("  [1/3] Empty string...")
    tts.speak("")
    ok("Empty string handled (no crash)")

    # Edge case 2: Whitespace only
    print("  [2/3] Whitespace only...")
    tts.speak("   ")
    ok("Whitespace string handled (no crash)")

    # Edge case 3: Very long text (should be chunked)
    print("  [3/3] Very long text (800+ chars)...")
    long_text = "This is a test. " * 100  # ~1500 chars
    print(f"  Text length: {len(long_text)} chars")
    tts.stop()
    completed = [False]
    tts.speak(long_text, callback=lambda: completed.__setitem__(0, True))
    timeout = 30
    start = time.time()
    while not completed[0] and (time.time() - start) < timeout:
        time.sleep(0.1)
    if completed[0]:
        ok("Long text chunked and spoken without crash")
    else:
        fail("Long text caused timeout or hang")
        tts.stop()
        return False

    # Edge case 4: Stop mid-speech
    print("  [bonus] Stop mid-speech...")
    tts.speak("This sentence should be interrupted.", callback=lambda: None)
    time.sleep(0.5)
    tts.stop()
    ok("Stop mid-speech handled (no crash)")

    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="OMNI TTS Test Script")
    parser.add_argument("--kokoro",  action="store_true", help="Test Kokoro only")
    parser.add_argument("--sapi",    action="store_true", help="Test SAPI only")
    parser.add_argument("--voices",  action="store_true", help="Preview all voices")
    parser.add_argument("--text",    type=str, default="", help="Speak custom text")
    parser.add_argument("--all",     action="store_true", help="Run all tests")
    args = parser.parse_args()

    run_all = args.all or not any([args.kokoro, args.sapi, args.voices, args.text])

    print()
    print(f"{BOLD}╔{'═' * 56}╗{RESET}")
    print(f"{BOLD}║{RESET}           OMNI TTS Test Suite                {BOLD}║{RESET}")
    print(f"{BOLD}╚{'═' * 56}╝{RESET}")
    print()

    from omni.tts.kokoro_tts import KokoroTTS

    # Custom text mode
    if args.text:
        print(f"Speaking: \"{args.text}\"")
        tts = KokoroTTS()
        print(f"Engine: {tts.engine_type}")
        completed = [False]
        tts.speak(args.text, callback=lambda: completed.__setitem__(0, True))
        while not completed[0]:
            time.sleep(0.1)
        return 0

    # Voices preview mode
    if args.voices:
        test_kokoro_instantiation()
        test_voice_preview()
        return 0

    # SAPI only mode
    if args.sapi:
        return 0 if test_sapi_speak() else 1

    # Kokoro only mode
    if args.kokoro:
        ok_ = test_kokoro_instantiation()
        if ok_:
            from omni.tts.kokoro_tts import KokoroTTS as KT
            tts = KT()
            test_kokoro_speak(tts)
        return 0 if ok_ else 1

    # All tests
    results = []

    # Test 1: Instantiation & model files
    results.append(("Instantiation", test_kokoro_instantiation()))

    # If Kokoro is available, run more tests
    from omni.tts.kokoro_tts import KokoroTTS as KT
    tts = KT()

    if tts.engine_type == 'kokoro-onnx':
        results.append(("Speech Generation", test_kokoro_speak(tts)))
        results.append(("Edge Cases", test_edge_cases()))
        print()
        ans = input("Preview recommended voices? (Y/n): ").strip().lower()
        if ans != 'n':
            test_voice_preview()
    else:
        warn("Kokoro-ONNX not active — skipping generation tests")
        results.append(("Speech Generation", False))
        results.append(("Edge Cases", False))

    # Test SAPI fallback
    results.append(("SAPI Fallback", test_sapi_speak()))

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
        ok("All tests passed! OMNI TTS is ready.")
        return 0
    else:
        fail("Some tests failed. Check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())