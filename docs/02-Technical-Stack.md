# OMNI Technical Stack

**Selected Framework**: PyQt5 (App Shell)  
**AI Paradigm**: Semantic Intent Mapping + Autonomous Reasoning Loop

---

## 1. Core AI Components

### Speech-to-Text (STT)
- **Engine**: `faster-whisper` (base.en)
- **Optimization**: Forced `int8` compute on CUDA for GTX 1050 Ti stability.
- **VRAM Usage**: $\approx 500\text{MB}$.

### Intent Understanding (The Brain)
- **Engine**: `Sentence-Transformers` (`all-MiniLM-L6-v2`)
- **Logic**: Cosine Similarity between user input vectors and command intent centroids.
- **VRAM Usage**: $\approx 100\text{MB}$.

### Text-to-Speech (TTS)
- **Engine**: `Kokoro-ONNX` (v1.0)
- **Quality**: High-fidelity, local neural TTS.
- **VRAM Usage**: $\approx 300\text{MB}$.

### Voice Activity Detection (VAD)
- **Engine**: `Silero VAD` via `torch.hub`.
- **Precision**: Neural-based speech detection to prevent false triggers.

---

## 2. Automation & Control

| Target | Technology | Method |
|---------|------------|-----------|
| **Browser** | Chrome CDP | Remote debugging port 9222 |
| **Windows** | UIAutomation | Native Windows Accessibility API |
| **VS Code** | WebSocket Bridge | Editor-level command execution |

---

## 3. GPU Memory Budget (GTX 1050 Ti 4GB)

To ensure zero crashes during high-load demos, OMNI uses a strict VRAM budget:

| Component | VRAM Usage | Status |
|-----------|------------|--------|
| Whisper (int8) | $\approx 500\text{MB}$ | Optimized ✓ |
| Intent Mapper | $\approx 100\text{MB}$ | Optimized ✓ |
| Kokoro TTS | $\approx 300\text{MB}$ | Optimized ✓ |
| PyQt5 + Orb | $\approx 200\text{MB}$ | Optimized ✓ |
| **Total Base** | **$\approx 1.1\text{GB}$** | **Stable ✓** |

**Remaining Headroom**: $\approx 2.9\text{GB}$ for Chrome, Windows, and OS overhead. This ensures OMNI never triggers a CUDA Out-of-Memory (OOM) error.
