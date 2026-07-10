# 🤖 OMNI - Autonomous Personal Agent

> **The next generation of accessibility-first autonomous computing**
> Local. Private. Semantic. Autonomous.

**Hackathon**: Agentic AI Innovation Challenge 2026  
**Category**: Open Innovation  
**Platform**: Windows (Optimized for GTX 1050 Ti)

---

## 🎯 What is OMNI?

OMNI is not just a voice-control tool; it is an **autonomous agent** that bridges the gap between human intent and computer execution. By combining semantic understanding with a closed-loop reasoning system, OMNI can handle complex goals, recover from errors, and provide real-time visual feedback.

### 🚀 Superior Features (The "Winning" Edge)

| Feature | Technology | Why it's Superior |
|---------|-------------|-------------------|
| **Semantic Intent** | `Sentence-Transformers` | Understands *meaning*, not just keywords. "Get me to GitHub" works as well as "Open GitHub". |
| **Reasoning Loop** | `Plan → Act → Observe → Correct` | Doesn't just "fire and forget." It verifies if an action worked and retries with different strategies if it fails. |
| **Visual Core** | `PyQt5 Voice Orb` | A floating, reactive visual presence that communicates the agent's state (Listening, Thinking, Speaking). |
| **Local-First AI** | `Faster-Whisper` + `Kokoro` | Zero latency, zero API costs, and 100% privacy. All processing stays on your GPU. |
| **Hardware-Tuned** | `INT8 CUDA Optimization` | Specifically engineered for the GTX 1050 Ti to ensure zero crashes and maximum VRAM efficiency. |

---

## 🚀 Quick Start

### Prerequisites
- Windows 10/11
- Python 3.10+
- NVIDIA GPU (4GB+ VRAM recommended)
- Microphone

### Installation
```powershell
git clone https://github.com/muhummadzarrar09-sudo/Omni.git
cd Omni

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Launching
1. **Launch Chrome with Accessibility** (Required for browser control):
   ```powershell
   .\scripts\launch-chrome.ps1
   ```
2. **Run OMNI**:
   ```powershell
   python omni.py
   ```

---

## 🏗️ Architecture: The Autonomy Stack

OMNI operates on a four-layer stack designed for resilience and speed:

1.  **The Perception Layer (Voice)**: 
    - `Silero VAD` detects speech $\rightarrow$ `Faster-Whisper` transcribes it.
2.  **The Cognition Layer (The Brain)**: 
    - `IntentMapper` uses vector embeddings to map speech to a semantic goal.
    - `OmniReasoner` creates a plan and manages the execution loop.
3.  **The Action Layer (Plugins)**: 
    - Specialized plugins for Chrome (CDP), Windows (UIA), and VS Code.
    - Plugins provide `verify_action` hooks for the Reasoner to observe success.
4.  **The Feedback Layer (UI/TTS)**: 
    - `Voice Orb` provides instant visual state updates.
    - `Kokoro TTS` provides natural audio feedback.

---

## 📁 Project Structure
(Refer to `docs/` for detailed technical breakdowns)
- `omni/core/`: Intent mapping, Reasoning loop, and Event bus.
- `omni/voice/`: STT and VAD pipeline.
- `omni/tts/`: Local Kokoro-ONNX engine.
- `omni/plugins/`: The toolset OMNI uses to interact with the world.
- `omni/ui/`: The Voice Orb and System Tray.

---

## 📜 License
MIT License - See LICENSE file
