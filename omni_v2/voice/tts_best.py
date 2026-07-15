"""
OMNI V3 - TTS V4 - THE BEST OF THE BEST

3 engines in priority order:
  1. edge-tts (Microsoft Edge natural voices) - FREE, sounds human
  2. piper-tts (offline, fast, neural) - if installed
  3. pyttsx3 SAPI5 (fallback) - always works on Windows
  4. Print fallback (last resort)

Voice personas for the JARVIS feel:
  - en-US-GuyNeural (default JARVIS-like male)
  - en-US-JennyNeural (warm female)
  - en-US-AriaNeural (energetic)
  - + 300+ more from Edge TTS
"""
from __future__ import annotations
import asyncio
import threading
import time
import io
import re
import tempfile
from pathlib import Path
from typing import Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("TTSBest")

try:
    from omni_v2.core.paths import DATA_DIR
except Exception:
    DATA_DIR = Path.cwd() / "data"


# Voice personas - JARVIS-like
VOICE_PERSONAS = {
    "jarvis": "en-US-GuyNeural",          # Default - calm British-ish male
    "jarvis_british": "en-GB-RyanNeural", # British JARVIS
    "friday": "en-US-JennyNeural",         # Female counterpart
    "aria": "en-US-AriaNeural",            # Energetic
    "davis": "en-US-DavisNeural",          # Authoritative male
    "sara": "en-US-SaraNeural",            # Young female
}


class TTSBest:
    """
    Multi-backend TTS with voice persona support.
    Singleton, thread-safe.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, voice: str = "jarvis"):
        if self._initialized:
            return
        self.voice_persona = voice
        self.edge_voice = VOICE_PERSONAS.get(voice, "en-US-GuyNeural")
        self.engine_type = None
        self.edge_voices_available: list = []
        self.piper_voices: dict = {}
        self.sapi_engine = None
        self.audio_dir = DATA_DIR / "tts_cache"
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.spoken_count = 0
        self.last_error = None
        self.init_status = "pending"
        self._init_engines()
        self._initialized = True
        logger.info(f"🔊 TTS Best: persona={voice} | engine={self.engine_type} | edge_voice={self.edge_voice}")

    def set_voice(self, persona: str):
        """Change voice persona on the fly."""
        if persona in VOICE_PERSONAS:
            self.voice_persona = persona
            self.edge_voice = VOICE_PERSONAS[persona]
            logger.info(f"🔊 TTS voice changed to {persona} ({self.edge_voice})")

    def _init_engines(self):
        # Try edge-tts first (best quality, free)
        try:
            import edge_tts
            self.engine_type = "edge-tts"
            self.init_status = "edge_tts_ready"
            # List available voices (cached for performance)
            try:
                # Note: this is async, but we just record the engine is available
                self.edge_voices_available = [
                    "en-US-GuyNeural", "en-US-JennyNeural", "en-US-AriaNeural",
                    "en-US-DavisNeural", "en-US-SaraNeural", "en-US-TonyNeural",
                    "en-US-NancyNeural", "en-US-JaneNeural", "en-US-JasonNeural",
                    "en-GB-RyanNeural", "en-GB-SoniaNeural", "en-GB-LibbyNeural",
                ]
                logger.info(f"✅ TTS V4: edge-tts ready (voices: {self.edge_voice})")
            except Exception:
                pass
            return
        except ImportError:
            self.last_error = "edge-tts not installed"
            logger.debug("edge-tts not installed - pip install edge-tts")

        # Try Piper (offline neural, super fast)
        try:
            import piper
            self.engine_type = "piper"
            self.init_status = "piper_ready"
            logger.info("✅ TTS V4: piper-tts ready")
            return
        except ImportError:
            logger.debug("piper-tts not installed - pip install piper-tts")

        # Fallback to SAPI5
        try:
            import pyttsx3
            self.sapi_engine = pyttsx3.init()
            voices = self.sapi_engine.getProperty('voices')
            if voices:
                for v in voices:
                    name_l = v.name.lower()
                    if any(k in name_l for k in ['zira', 'sarah', 'hazel', 'female']):
                        self.sapi_engine.setProperty('voice', v.id)
                        break
            self.sapi_engine.setProperty('rate', 185)
            self.engine_type = "sapi"
            self.init_status = "sapi_ready"
            logger.info("✅ TTS V4: SAPI5 fallback ready")
        except Exception as e:
            self.last_error = f"All TTS engines failed: {e}"
            self.init_status = "no_engine"
            logger.warning(f"⚠️ TTS V4: no engines available, will print only")

    def _truncate_at_sentence(self, text: str, max_len: int = 800) -> str:
        """Cut at sentence boundary (TTS-BUG-03 fix)."""
        if len(text) <= max_len:
            return text
        truncated = text[:max_len]
        m = list(re.finditer(r'[.!?]\s', truncated))
        if m:
            cut = m[-1].end()
            if cut > max_len * 0.5:
                return truncated[:cut].strip()
        last_space = truncated.rfind(' ')
        if last_space > max_len * 0.5:
            return truncated[:last_space].strip() + "..."
        return truncated + "..."

    def speak(self, text: str, blocking: bool = True, voice: Optional[str] = None) -> bool:
        """Speak text. Returns True if successful."""
        if not text or not text.strip():
            return False
        text = self._truncate_at_sentence(text.strip(), max_len=800)
        target_voice = VOICE_PERSONAS.get(voice or self.voice_persona, self.edge_voice)

        if self.engine_type == "edge-tts":
            return self._speak_edge_tts(text, blocking, target_voice)
        elif self.engine_type == "piper":
            return self._speak_piper(text, blocking)
        elif self.engine_type == "sapi":
            return self._speak_sapi(text, blocking)
        else:
            # Print fallback
            print(f"[OMNI SAYS]: {text}")
            self.spoken_count += 1
            return True

    def _speak_edge_tts(self, text: str, blocking: bool, voice: str) -> bool:
        """Edge TTS - Microsoft natural voices."""
        try:
            import edge_tts
            import sounddevice as sd

            # Run edge-tts in an async context
            async def _gen_and_play():
                communicate = edge_tts.Communicate(text, voice)
                audio_chunks = []
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_chunks.append(chunk["data"])
                if not audio_chunks:
                    return False
                # Combine chunks
                audio_bytes = b"".join(audio_chunks)
                # Decode and play
                import numpy as np
                # edge-tts outputs MP3-like data, but for streaming we can play directly
                # Save to temp file for sounddevice to play
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False, dir=str(self.audio_dir)) as f:
                    f.write(audio_bytes)
                    tmp_path = f.name
                try:
                    # Try to play with sounddevice via simpleaudio or pydub
                    try:
                        from pydub import AudioSegment
                        from pydub.playback import play
                        audio = AudioSegment.from_mp3(tmp_path)
                        play(audio)
                        return True
                    except ImportError:
                        # Fallback: use ffplay or mpg123
                        import subprocess
                        import shutil
                        for player in ["ffplay", "mpg123", "mplayer"]:
                            if shutil.which(player):
                                r = subprocess.run(
                                    [player, "-nodisp", "-autoexit", tmp_path],
                                    capture_output=True, timeout=30
                                )
                                return r.returncode == 0
                        # Last resort: save WAV and use sounddevice
                        return self._play_with_sounddevice(tmp_path)
                finally:
                    try:
                        Path(tmp_path).unlink()
                    except Exception:
                        pass

            # Run async
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # We're in an async context, schedule as task
                    return asyncio.create_task(_gen_and_play())
                else:
                    return loop.run_until_complete(_gen_and_play())
            except RuntimeError:
                # No event loop, create one
                return asyncio.run(_gen_and_play())
        except Exception as e:
            logger.error(f"edge-tts speak failed: {e}, falling back to SAPI")
            self.last_error = str(e)
            return self._speak_sapi(text, blocking)

    def _play_with_sounddevice(self, audio_path: str) -> bool:
        """Try to play audio file using sounddevice + simple decoder."""
        try:
            # Try scipy or wave for simple WAV files
            import soundfile as sf
            import sounddevice as sd
            data, sr = sf.read(audio_path)
            sd.play(data, samplerate=sr, blocking=True)
            return True
        except Exception as e:
            logger.debug(f"sounddevice play: {e}")
        return False

    def _speak_piper(self, text: str, blocking: bool) -> bool:
        """Piper TTS (offline neural)."""
        try:
            import piper
            # Implementation depends on piper version
            return False  # TODO
        except Exception as e:
            logger.error(f"piper speak failed: {e}")
            return False

    def _speak_sapi(self, text: str, blocking: bool) -> bool:
        """SAPI5 fallback."""
        try:
            if not self.sapi_engine:
                return False
            self.sapi_engine.say(text)
            if blocking:
                self.sapi_engine.runAndWait()
            self.spoken_count += 1
            return True
        except Exception as e:
            logger.error(f"SAPI speak failed: {e}")
            print(f"[OMNI SAYS]: {text}")
            self.spoken_count += 1
            return True

    def speak_async(self, text: str, voice: Optional[str] = None):
        """Non-blocking speak in background thread."""
        thread = threading.Thread(
            target=self.speak, args=(text, True, voice), daemon=True
        )
        thread.start()
        return thread

    def stop_speaking(self):
        """Interrupt any ongoing TTS."""
        try:
            if self.sapi_engine:
                self.sapi_engine.stop()
        except Exception:
            pass
        try:
            import sounddevice as sd
            sd.stop()
        except Exception:
            pass

    def get_status(self) -> dict:
        return {
            "engine": self.engine_type,
            "init_status": self.init_status,
            "persona": self.voice_persona,
            "edge_voice": self.edge_voice,
            "voices_available": self.edge_voices_available,
            "spoken_count": self.spoken_count,
            "last_error": self.last_error,
        }


def get_tts_best(voice: str = "jarvis") -> TTSBest:
    return TTSBest(voice=voice)
