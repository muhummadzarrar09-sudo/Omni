"""
OMNI V3 - Vision Tests (Phase 4A)
"""
import sys
import time
import tempfile
from pathlib import Path

# UTF-8 setup for Windows
try:
    from omni_v2.utils.utf8 import setup_utf8_console
    setup_utf8_console()
except Exception:
    pass


def test_vision_initialized():
    """Test 1: Vision engine initializes"""
    from omni_v2.vision.multimodal import MultimodalVision
    MultimodalVision._instance = None
    v = MultimodalVision()
    assert v is not None
    status = v.get_status()
    assert "uploads_dir" in status
    print(f"  ✅ Vision initialized: {status}")


def test_vision_status():
    """Test 2: Status endpoint works"""
    from omni_v2.vision.multimodal import MultimodalVision
    MultimodalVision._instance = None
    v = MultimodalVision()
    status = v.get_status()
    assert "moondream2" in status
    assert "tesseract" in status
    assert "pdfplumber" in status
    print(f"  ✅ Status: {status}")


def test_process_text_file():
    """Test 3: Text file processing works"""
    from omni_v2.vision.multimodal import MultimodalVision
    MultimodalVision._instance = None
    v = MultimodalVision()
    # Create a test text file
    tmp = Path(tempfile.mkdtemp(prefix="omni_vision_test_"))
    test_file = tmp / "test.txt"
    test_file.write_text("Hello world. This is a test file with some content to summarize.", encoding="utf-8")
    result = v.process_file(str(test_file), "What's this about?")
    assert result.success
    assert result.extracted_text
    assert "Hello world" in result.extracted_text
    assert result.file_type == "text"
    print(f"  ✅ Text file: {result.extracted_text[:60]}...")


def test_process_nonexistent_file():
    """Test 4: Non-existent file returns error gracefully"""
    from omni_v2.vision.multimodal import MultimodalVision
    MultimodalVision._instance = None
    v = MultimodalVision()
    result = v.process_file("/nonexistent/file.txt", "test")
    assert not result.success
    assert "not found" in result.error.lower()
    print(f"  ✅ Non-existent file: {result.error}")


def test_process_bytes():
    """Test 5: Processing from bytes works"""
    from omni_v2.vision.multimodal import MultimodalVision
    MultimodalVision._instance = None
    v = MultimodalVision()
    data = b"Hello from bytes test content"
    result = v.process_bytes(data, "test.txt", "what is this?")
    assert result.success
    assert "Hello from bytes" in result.extracted_text
    print(f"  ✅ Bytes: {result.extracted_text[:60]}...")


def test_unsupported_file_type():
    """Test 6: Unsupported file type returns error"""
    from omni_v2.vision.multimodal import MultimodalVision
    MultimodalVision._instance = None
    v = MultimodalVision()
    tmp = Path(tempfile.mkdtemp(prefix="omni_vision_unsup_"))
    bad = tmp / "test.xyz"
    bad.write_text("data", encoding="utf-8")
    result = v.process_file(str(bad), "what?")
    assert not result.success
    assert "Unsupported" in result.error
    print(f"  ✅ Unsupported: {result.error}")


def test_singleton():
    """Test 7: Vision is singleton"""
    from omni_v2.vision.multimodal import MultimodalVision, get_vision
    MultimodalVision._instance = None
    v1 = get_vision()
    v2 = get_vision()
    assert v1 is v2
    print("  ✅ Singleton works")


def test_vision_result_dataclass():
    """Test 8: VisionResult has all fields"""
    from omni_v2.vision.multimodal import VisionResult
    r = VisionResult(success=True, file_type="text", description="test")
    assert r.success
    assert r.file_type == "text"
    assert r.description == "test"
    assert r.objects_detected == []
    assert r.metadata == {}
    assert r.error == ""
    print("  ✅ VisionResult fields OK")


def main():
    print("=" * 60)
    print("  VISION TESTS (Phase 4A)")
    print("=" * 60)
    tests = [
        test_vision_initialized,
        test_vision_status,
        test_process_text_file,
        test_process_nonexistent_file,
        test_process_bytes,
        test_unsupported_file_type,
        test_singleton,
        test_vision_result_dataclass,
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
        print(f"  ✅ ALL 8 VISION TESTS PASSED")
    else:
        print(f"  ❌ {failed} TEST(S) FAILED")
    print("=" * 60)
    return failed


if __name__ == "__main__":
    sys.exit(main())
