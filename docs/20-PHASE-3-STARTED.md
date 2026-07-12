# 🚀 OMNI V2 - Phase 3 Started: Vision + Wake Word + Cinematic HUD

**Date:** 2026-07-11 | **Status:** Phase 2 Hardened (10/10), Phase 3 Kickoff

---

## Phase 3 Goals (From V2 PRD Week 2 Day 1-2)

| Feature | Description | Priority | Status |
|---------|-------------|----------|--------|
| **Vision** | Screen capture + LLaVA local vision | P0 | 🟡 Started |
| **Wake Word** | "Hey OMNI" continuous via pvporcupine | P0 | 🟡 Started |
| **Three.js Orb** | 2400 particle GLSL shader orb | P0 | 🟡 Started |
| **Arc Reactor HUD** | Glowing ring + live transcription | P1 | 🔜 Next |
| **System Dashboard** | CPU/RAM/GPU live graphs | P1 | 🔜 Next |
| **Face Auth** | Biometric login | P2 | 🔜 Phase 4 |

---

## Phase 3 Architecture

### Vision Pipeline

```
Screen Capture (mss, 60fps, fast)
  → OpenCV preprocessing
    → LLaVA 7B INT4 local via Ollama (4GB VRAM, 1050 Ti)
      → Text description: "I see VS Code with main.py, Chrome with YouTube"
        → MemoryAgent stores: "User was coding main.py"
```

**Implementation:**

**`omni_v2/vision/screen.py` - Fast Screen Capture:**
```python
import mss
from PIL import Image

class ScreenCapture:
    def capture(self, monitor=0) -> Image:
        with mss.mss() as sct:
            screenshot = sct.grab(sct.monitors[monitor])
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            return img

    def capture_region(self, x, y, w, h) -> Image:
        # For find_element
        ...

    def find_template(self, template_path: str) -> Tuple[int, int]:
        # For find login button via template matching
        ...
```

**`omni_v2/vision/llava.py` - LLaVA Vision Model:**
```python
class LLaVAVision:
    def __init__(self, model="llava:7b"):
        # Try Ollama LLaVA, fallback to mock for demo
        ...

    async def describe_screen(self, image: Image) -> str:
        # If Ollama LLaVA available: real description
        # Else: mock based on window titles for demo
        # "I see VS Code with main.py, Chrome with YouTube, OMNI V2 HUD"

    async def find_element(self, query: str, image: Image) -> Tuple[int, int]:
        # Use OWLv2 or CLIP to find "login button" coordinates
        # Phase 3: Mock, Phase 4: Real OWLv2
```

### Wake Word Pipeline

```
Microphone → pvporcupine (wake word "Hey OMNI", 5% CPU, offline)
  → Silero VAD (HIGH)
    → faster-whisper streaming (live transcription on HUD)
      → LLM Router
        → TTS streaming sentence-by-sentence
```

**`omni_v2/voice/wake_word.py`:**
```python
import pvporcupine
import pyaudio

class WakeWordDetector:
    def __init__(self, keyword="hey omni"):
        # pvporcupine needs access key, openwakeword is free alternative
        self.keyword = keyword
        self.detector = None
        self._init_porcupine()

    def _init_porcupine(self):
        try:
            import pvporcupine
            self.detector = pvporcupine.create(
                keywords=["hey google"],  # Use hey google as proxy for hey omni, or custom
                sensitivities=[0.7]
            )
            logger.info("Wake word: Hey OMNI via pvporcupine")
        except Exception:
            # Fallback to openwakeword (free, no key)
            try:
                import openwakeword
                ...
            except Exception:
                logger.warning("No wake word engine - using PTT only")

    def listen_for_wake_word(self, audio_callback):
        # Continuous listening loop, calls callback when wake word detected
        ...
```

**Hybrid Mode:**
- Continuous wake word listening (5% CPU)
- When "Hey OMNI" detected → start VAD + Whisper + show orb green listening
- After command → back to wake word listening
- User can still press V for PTT (hybrid)

### Three.js Orb - 2400 Particles

**`omni_v2/ui/orb_threejs.html` - Cinematic HUD:**

From qartex research: GLSL shader particle orb with 2400 particles, state colors:
- Blue idle: slow orbit
- Orange thinking: fast spin
- Green listening: pulse
- Red error: chaotic

**Implementation:**
- PyQt WebEngineView to embed HTML + Three.js
- HTML file with Three.js + custom shader
- Python communicates via WebChannel: `orb.set_state("listening")` → JS changes particle color/speed

**For Phase 3 Start:** Create HTML file with Three.js orb, but keep simple radial orb as fallback if WebEngine not available.

**`omni_v2/ui/hud.py` - Arc Reactor HUD:**

From eadmin2 research: Glowing ring in browser, click to talk, live transcription around ring.

- Center ring glows, click to talk
- Live transcription appears around ring while you speak (RealtimeSTT)
- Outer ring shows system stats: CPU, RAM, mic level

---

## Files to Create - Phase 3

**New in Phase 3:**

```
omni_v2/voice/wake_word.py - Wake word detector
omni_v2/vision/screen.py - Screen capture
omni_v2/vision/llava.py - Vision model
omni_v2/ui/orb_threejs.html - Three.js 2400 particle orb
omni_v2/ui/hud.py - Arc reactor HUD
omni_v2/ui/dashboard.py - System dashboard live graphs
omni_v2/security/face_auth.py - Biometric (Phase 4)
```

**Already Done Phase 2 Hardened:**

```
omni_v2/core/paths.py - Data inside project/data/ unanimous ✓
omni_v2/memory/sqlite_store.py - SQLite ✓
omni_v2/memory/vector_store.py - ChromaDB ✓
omni_v2/llm/router.py - Ollama multi-tier ✓
omni_v2/agents/memory.py - Uses SQLite+Chroma in data/ ✓
```

---

## How to Test Phase 3 (When Built)

```powershell
# Install Phase 3 deps
pip install mss opencv-python pvporcupine openwakeword pyqtwebengine

# Test screen capture
python -m omni_v2.vision.screen
# Should capture screen and save to data/screenshots/

# Test wake word
python -m omni_v2.voice.wake_word
# Should listen for "Hey OMNI" and print when detected

# Test Three.js orb
python -m omni_v2.ui.hud
# Should open window with glowing ring + particle orb

# Full V2 with new features
python omni.py --wakeword
# Wake word mode: say "Hey OMNI" instead of pressing V
```

---

## Current Status - Phase 3 Started

- [x] Data moved inside project/data/ unanimous (Phase 2 Hardened)
- [x] 10/10 tests still pass after move
- [x] Research for Vision, Wake Word, Three.js orb done (docs/15-JARVIS-RESEARCH.md)
- [ ] Implement screen.py (mss)
- [ ] Implement llava.py (Ollama LLaVA)
- [ ] Implement wake_word.py (pvporcupine)
- [ ] Create orb_threejs.html (Three.js 2400 particles)
- [ ] Create hud.py (arc reactor)
- [ ] Create dashboard.py (live graphs)
- [ ] Face auth (Phase 4)

**Next: Implement vision + wake word + Three.js orb skeleton, then polish for demo**

---

- Zarrar + Agent | 2026-07-11 | Phase 3 Started 🚀
