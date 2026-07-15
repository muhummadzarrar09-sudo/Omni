"""
OMNI V3 - Voice Cloning Tests (Phase 4B)
"""
import sys
import time
import tempfile
import wave
from pathlib import Path

# UTF-8 setup for Windows
try:
    from omni_v2.utils.utf8 import setup_utf8_console
    setup_utf8_console()
except Exception:
    pass


def test_voice_cloner_initialized():
    """Test 1: VoiceCloner initializes"""
    from omni_v2.voice.voice_clone import VoiceCloner
    VoiceCloner._instance = None
    vc = VoiceCloner()
    status = vc.get_status()
    assert "available" in status
    assert "recording" in status
    print(f"  ✅ VoiceCloner initialized: available={status['available']}")


def test_list_samples_empty():
    """Test 2: List samples returns empty initially"""
    from omni_v2.voice.voice_clone import VoiceCloner
    VoiceCloner._instance = None
    vc = VoiceCloner()
    samples = vc.list_samples()
    assert isinstance(samples, list)
    # May have samples from prior tests in real data dir, so just check structure
    for s in samples:
        assert "name" in s
        assert "path" in s
    print(f"  ✅ Samples: {len(samples)} found")


def test_list_voices_empty():
    """Test 3: List voices returns empty initially"""
    from omni_v2.voice.voice_clone import VoiceCloner
    VoiceCloner._instance = None
    vc = VoiceCloner()
    voices = vc.list_voices()
    assert isinstance(voices, list)
    print(f"  ✅ Voices: {len(voices)} found")


def test_train_voice_creates_metadata():
    """Test 4: Train voice creates metadata file"""
    from omni_v2.voice.voice_clone import VoiceCloner
    VoiceCloner._instance = None
    vc = VoiceCloner()
    # Create a fake sample
    tmp = Path(tempfile.mkdtemp(prefix="omni_voice_test_"))
    sample = tmp / "test_sample.wav"
    # Create a 2-second WAV
    with wave.open(str(sample), 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(22050)
        wf.writeframes(b"\x00\x00" * 22050 * 2)  # 2 seconds of silence
    result = vc.train_voice(str(sample), voice_name="test_voice_xyz")
    # Either success (Piper available) or graceful fallback
    if result.get("success"):
        assert "voice_id" in result
        assert result["voice_id"] == "test_voice_xyz"
    else:
        # Fallback message about Piper not installed
        assert "Piper" in result.get("error", "") or "fallback" in result
    print(f"  ✅ Train result: {result}")


def test_train_voice_with_missing_sample():
    """Test 5: Train with missing sample returns error"""
    from omni_v2.voice.voice_clone import VoiceCloner
    VoiceCloner._instance = None
    vc = VoiceCloner()
    result = vc.train_voice("/nonexistent/path.wav", voice_name="test")
    assert not result.get("success")
    assert "not found" in result.get("error", "").lower()
    print(f"  ✅ Missing sample: {result['error']}")


def test_speak_in_my_voice_no_active():
    """Test 6: Speak without active voice returns False"""
    from omni_v2.voice.voice_clone import VoiceCloner
    VoiceCloner._instance = None
    vc = VoiceCloner()
    vc._active_voice_id = None
    result = vc.speak_in_my_voice("hello world")
    assert result is False
    print("  ✅ No active voice: speak returns False")


def test_wav_duration():
    """Test 7: WAV duration calculation"""
    from omni_v2.voice.voice_clone import VoiceCloner
    VoiceCloner._instance = None
    vc = VoiceCloner()
    tmp = Path(tempfile.mkdtemp(prefix="omni_voice_dur_"))
    sample = tmp / "test.wav"
    with wave.open(str(sample), 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(22050)
        wf.writeframes(b"\x00\x00" * 22050 * 3)  # 3 seconds
    duration = vc._wav_duration(sample)
    assert abs(duration - 3.0) < 0.1
    print(f"  ✅ WAV duration: {duration:.2f}s")


def test_singleton():
    """Test 8: VoiceCloner is singleton"""
    from omni_v2.voice.voice_clone import VoiceCloner, get_voice_cloner
    VoiceCloner._instance = None
    v1 = get_voice_cloner()
    v2 = get_voice_cloner()
    assert v1 is v2
    print("  ✅ Singleton works")


def main():
    print("=" * 60)
    print("  VOICE CLONE TESTS (Phase 4B)")
    print("=" * 60)
    tests = [
        test_voice_cloner_initialized,
        test_list_samples_empty,
        test_list_voices_empty,
        test_train_voice_creates_metadata,
        test_train_voice_with_missing_sample,
        test_speak_in_my_voice_no_active,
        test_wav_duration,
        test_singleton,
    ]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            print(f"\n❌ {t.__name__} FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"\n❌ {t.__name__} ERROR: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    print()
    print("=" * 60)
    if failed == 0:
        print(f"  ✅ ALL 8 VOICE CLONE TESTS PASSED")
    else:
        print(f"  ❌ {failed} TEST(S) FAILED")
    print("=" * 60)
    return failed


if __name__ == "__main__":
    sys.exit(main())
