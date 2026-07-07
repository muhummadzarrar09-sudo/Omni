# OMNI Technical Stack

**Selected Framework**: PyQt5 (App Shell)  
**Rationale**: Maximum velocity for solo 8-day build

---

## 1. App Shell: PyQt5

| Criteria | PyQt5 | Tauri | Winner |
|----------|-------|-------|--------|
| AI/ML Integration | Native Python | Rust FFI | **PyQt5** |
| Development Speed | Fast | Slow | **PyQt5** |
| Time to Competency | 2-3 days | 5-7 days | **PyQt5** |

---

## 2. Voice STT: faster-whisper

- whisper.cpp bindings via faster-whisper
- GPU-accelerated (GTX 1050 Ti compatible)
- Model: base.en (140 MB, ~1GB VRAM)

---

## 3. Browser Control: CDP

- Chrome DevTools Protocol via python-cdp
- Requires `--force-renderer-accessibility` flag

---

## 4. Windows Control: Python-UIAutomation

- Apache 2.0 license, no third-party deps
- Native UIA API for modern Windows

---

## 5. TTS: Kokoro TTS

- Local, fast, multiple voices
- GPU-accelerated inference

---

## GPU Memory Budget (GTX 1050 Ti 4GB)

| Component | VRAM Usage |
|-----------|------------|
| Whisper (base.en, fp16) | ~1.2 GB |
| Kokoro TTS | ~500 MB |
| PyQt5 UI | ~200 MB |
| **Total** | ~2 GB |

**Headroom**: 2GB for browser + Windows
