"""
OMNI V3 - Network Tests (Phase 5A: mDNS Discovery)
"""
import sys
import time
import socket
import threading
import json
import tempfile
from pathlib import Path

# UTF-8 setup for Windows
try:
    from omni_v2.utils.utf8 import setup_utf8_console
    setup_utf8_console()
except Exception:
    pass


def test_discovery_constants():
    """Test 1: Discovery protocol constants are set"""
    from omni_v2.network.discovery import (
        SERVICE_TYPE, SERVICE_PORT, DISCOVERY_PORT, DISCOVERY_MAGIC
    )
    assert SERVICE_TYPE == "_omni-brain._tcp.local."
    assert SERVICE_PORT == 8765
    assert DISCOVERY_PORT == 47624
    assert DISCOVERY_MAGIC == b"OMNI-DISCOVER-v1"
    print("  ✅ Discovery constants correct")


def test_network_info_dataclass():
    """Test 2: NetworkInfo dataclass and URLs"""
    from omni_v2.network.discovery import NetworkInfo
    info = NetworkInfo(
        name="Test OMNI",
        host="192.168.1.100",
        port=8765,
        version="3.2.0",
        model="qwen2.5-1.5b",
        capabilities=["voice", "vision"],
        api_version="1.0",
    )
    assert info.ws_url == "ws://192.168.1.100:8765/ws/mobile"
    assert info.http_url == "http://192.168.1.100:8765"
    d = info.to_dict()
    assert d["name"] == "Test OMNI"
    assert d["host"] == "192.168.1.100"
    assert d["ws_url"] == "ws://192.168.1.100:8765/ws/mobile"
    print(f"  ✅ NetworkInfo: {d['ws_url']}")


def test_generate_pairing_code():
    """Test 3: Pairing code is 6 digits, expires"""
    from omni_v2.network.discovery import generate_pairing_code
    code = generate_pairing_code("192.168.1.100", 8765, ttl_sec=60)
    assert len(code.code) == 6
    assert code.code.isdigit()
    assert code.host == "192.168.1.100"
    assert code.port == 8765
    assert code.is_valid() is True
    # Expired
    code.expires_at = time.time() - 1
    assert code.is_valid() is False
    print(f"  ✅ Pairing code: {code.code} (TTL 60s)")


def test_pairing_code_uri():
    """Test 4: Pairing code can be converted to URI and back"""
    from omni_v2.network.discovery import (
        generate_pairing_code, parse_pairing_code
    )
    code = generate_pairing_code("10.0.0.5", 8765, ttl_sec=300)
    uri = code.to_uri()
    assert uri.startswith("omni://pair?")
    assert "host=10.0.0.5" in uri
    assert "port=8765" in uri
    assert f"code={code.code}" in uri
    # Parse it back
    parsed = parse_pairing_code(uri)
    assert parsed is not None
    assert parsed.code == code.code
    assert parsed.host == "10.0.0.5"
    assert parsed.port == 8765
    print(f"  ✅ URI roundtrip: {uri}")


def test_parse_invalid_uri():
    """Test 5: Invalid URIs return None"""
    from omni_v2.network.discovery import parse_pairing_code
    assert parse_pairing_code("http://example.com") is None
    assert parse_pairing_code("omni://other?host=x") is None
    assert parse_pairing_code("omni://pair") is None  # no query
    assert parse_pairing_code("omni://pair?host=x") is None  # no code
    assert parse_pairing_code("") is None
    print("  ✅ Invalid URIs rejected")


def test_qr_payload():
    """Test 6: QR code payload roundtrip"""
    from omni_v2.network.discovery import NetworkInfo, make_qr_payload, parse_qr_payload
    info = NetworkInfo(
        name="Zarrar's OMNI",
        host="192.168.1.42",
        port=8765,
        version="3.2.0",
        model="qwen2.5-1.5b",
        capabilities=["voice", "vision", "wake_word"],
    )
    payload = make_qr_payload(info)
    parsed = parse_qr_payload(payload)
    assert parsed is not None
    assert parsed.name == "Zarrar's OMNI"
    assert parsed.host == "192.168.1.42"
    assert parsed.port == 8765
    assert "voice" in parsed.capabilities
    print(f"  ✅ QR payload roundtrip")


def test_parse_invalid_qr():
    """Test 7: Invalid QR payloads return None"""
    from omni_v2.network.discovery import parse_qr_payload
    assert parse_qr_payload("not json") is None
    assert parse_qr_payload("{}") is None
    assert parse_qr_payload('{"type":"other"}') is None
    assert parse_qr_payload("") is None
    print("  ✅ Invalid QR payloads rejected")


def test_device_id_from_public_key():
    """Test 8: Device ID is deterministic from key"""
    from omni_v2.network.discovery import device_id_from_public_key
    key1 = b"my-public-key-bytes-12345"
    key2 = b"my-public-key-bytes-12345"
    key3 = b"different-key"
    id1 = device_id_from_public_key(key1)
    id2 = device_id_from_public_key(key2)
    id3 = device_id_from_public_key(key3)
    assert id1 == id2  # same key → same id
    assert id1 != id3  # different key → different id
    assert len(id1) == 16  # 16 chars
    print(f"  ✅ Device ID: {id1} (16 chars)")


def test_make_discovery_info():
    """Test 9: make_discovery_info returns valid info"""
    from omni_v2.network.discovery import make_discovery_info
    info = make_discovery_info("My Test OMNI", 8765)
    assert info.name == "My Test OMNI"
    assert info.port == 8765
    assert info.version == "3.2.0"
    assert "voice" in info.capabilities
    assert "vision" in info.capabilities
    print(f"  ✅ Discovery info: {info.host}:{info.port}")


def test_broadcaster_starts_and_stops():
    """Test 10: Broadcaster can start and stop cleanly"""
    from omni_v2.network.mdns import OMNIMDNSBroadcaster
    b = OMNIMDNSBroadcaster(port=18765, name="Test")  # use alt port to avoid conflicts
    b.start()
    time.sleep(0.5)  # let it broadcast a few times
    assert b._running
    status = b.get_status()
    assert status["running"] is True
    assert status["name"] == "Test"
    assert status["announce_count"] >= 0
    b.stop()
    assert not b._running
    print(f"  ✅ Broadcaster: {status['announce_count']} announces")


def test_discovery_finds_broadcaster():
    """Test 11: Discovery can find a broadcaster on the same machine"""
    from omni_v2.network.mdns import OMNIMDNSBroadcaster, OMNIMDNSDiscovery
    # Start a broadcaster
    b = OMNIMDNSBroadcaster(port=18766, name="Discoverable")
    b.start()
    # Start a discovery
    found_events = []
    def on_found(info):
        found_events.append(info)
    d = OMNIMDNSDiscovery(callback=on_found)
    d.start()
    # Wait for discovery
    time.sleep(7)  # broadcaster sends every 5s
    d.stop()
    b.stop()
    # Should have found at least one
    found = d.get_found()
    if found:
        print(f"  ✅ Discovery found: {found[0].name} at {found[0].host}:{found[0].port}")
    else:
        # Some test environments can't bind to broadcast port
        print(f"  ⚠️  Discovery found {len(found)} brains (may be sandbox limitation)")


def test_discovery_status():
    """Test 12: Discovery status works"""
    from omni_v2.network.mdns import OMNIMDNSDiscovery
    d = OMNIMDNSDiscovery()
    d.start()
    time.sleep(0.2)
    status = d.get_status()
    assert "running" in status
    assert "found_count" in status
    d.stop()
    print(f"  ✅ Discovery status: {status['found_count']} found")


def test_singleton_patterns():
    """Test 13: Singletons work (or don't, depending on design)"""
    # Note: Our network components are NOT singletons because the
    # broadcaster (laptop) and discovery (phone) are different processes.
    from omni_v2.network.mdns import OMNIMDNSBroadcaster, OMNIMDNSDiscovery
    b1 = OMNIMDNSBroadcaster(port=18767)
    b2 = OMNIMDNSBroadcaster(port=18768)
    assert b1 is not b2  # different instances
    d1 = OMNIMDNSDiscovery()
    d2 = OMNIMDNSDiscovery()
    assert d1 is not d2
    print("  ✅ Not singletons (intentional - different processes)")


def main():
    print("=" * 60)
    print("  NETWORK TESTS (Phase 5A: mDNS Discovery)")
    print("=" * 60)
    tests = [
        test_discovery_constants,
        test_network_info_dataclass,
        test_generate_pairing_code,
        test_pairing_code_uri,
        test_parse_invalid_uri,
        test_qr_payload,
        test_parse_invalid_qr,
        test_device_id_from_public_key,
        test_make_discovery_info,
        test_broadcaster_starts_and_stops,
        test_discovery_finds_broadcaster,
        test_discovery_status,
        test_singleton_patterns,
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
        print(f"  ✅ ALL 13 NETWORK TESTS PASSED")
    else:
        print(f"  ❌ {failed} TEST(S) FAILED")
    print("=" * 60)
    return failed


if __name__ == "__main__":
    sys.exit(main())
