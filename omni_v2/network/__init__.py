"""
OMNI V3 - Network Layer (Phase 5: Mobile-First)

The bridge between OMNI on the laptop and the mobile companion on your phone.

Two main pieces:
  1. mDNS service discovery (laptop auto-broadcasts, phone auto-discovers)
  2. Pairing protocol (one-time QR code, persistent device)

Privacy promise: zero cloud, zero accounts, local WiFi only.
"""
from omni_v2.network.mdns import OMNIMDNSBroadcaster, OMNIMDNSDiscovery
from omni_v2.network.discovery import (
    NetworkInfo,
    PairingCode,
    generate_pairing_code,
    parse_pairing_code,
)

__all__ = [
    "OMNIMDNSBroadcaster",
    "OMNIMDNSDiscovery",
    "NetworkInfo",
    "PairingCode",
    "generate_pairing_code",
    "parse_pairing_code",
]
