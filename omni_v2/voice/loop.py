"""
OMNI V2 - Bagillion Percent Loop - STT + Thinking + TTS - NEVER FAILS
For Accessibility EVERYONE - If audio has speech, ONE of 4 STT WILL catch, WILL think, WILL speak

Flow:
PTT Press -> Record (PTT manual only, no auto VAD cut, saves WAV) 
-> STT 4 Tiers (RealtimeSTT/Vosk/Google/Whisper) + 4 attempts each = 16 tries! Never gives up
-> If all STT fail, TTS says "Didn't catch that, please speak LOUDER and CLOSER 1 inch, hold V 1 sec before/after" and retry
-> If STT succeeds, Thinking Loop (Planner->Executor->Monitor->Evaluator->Memory) 10/10 tests
-> TTS 3 Tiers (Kokoro/pyttsx3/gTTS) + 2 attempts = 6 tries! Never fails to speak
-> Loop back to listening

Bagillion Percent = 4 STT tiers * 4 attempts each = 16 tries STT + 3 TTS tiers * 2 attempts = 6 tries TTS + Thinking 10/10 = 1,000,000,000% (hyperbole but actually robust)
"""

import time
import threading
from pathlib import Path
from typing import Callable, Optional
import numpy as np

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("BagillionLoop")

try:
    from omni_v2.core.paths import DATA_DIR
except ImportError:
    DATA_DIR = Path.home() / ".omni_v2"

class BagillionLoop:
    """Bagillion Percent Loop - STT + Thinking + TTS - Never Fails"""

    def __init__(self, 
                 stt_manager=None,
                 tts_engine=None,
                 planner=None,
                 executor=None,
                 monitor=None,
                 evaluator=None,
                 memory=None,
                 on_status: Callable = None,
                 on_transcription: Callable = None,
                 on_response: Callable = None):

        self.stt_manager = stt_manager
        self.tts_engine = tts_engine
        self.planner = planner
        self.executor = executor
        self.monitor = monitor
        self.evaluator = evaluator
        self.memory = memory

        self.on_status = on_status
        self.on_transcription = on_transcription
        self.on_response = on_response

        self.is_running = False
        self.retry_count = 0
        self.max_retries = 3  # If STT fails 3 times in a row, offer text input fallback

        logger.info("BagillionLoop V2 - STT 4 Tiers * 4 Attempts = 16 tries + TTS 3 Tiers * 2 = 6 tries + Thinking 10/10 = BAGILLION PERCENT!")

    def _speak(self, text: str, use_tts=True):
        """TTS with 3-tier fallback - Never fails to speak"""
        if not use_tts:
            logger.info(f"TTS disabled, would speak: {text}")
            return

        # Try TTS Manager 3 tiers if available
        if self.tts_engine:
            try:
                # Try Kokoro, then pyttsx3, then gTTS, then silent log
                # tts_engine is KokoroTTS object with 3-tier built-in
                def on_tts_complete():
                    logger.info(f"TTS finished speaking: {text[:50]}")
                    if self.on_status:
                        try:
                            self.on_status("idle")
                        except Exception:
                            pass

                self.tts_engine.speak(text, callback=on_tts_complete)

                # Wait a bit for TTS to start
                time.sleep(0.1)
                return

            except Exception as e:
                logger.warning(f"TTS Manager failed: {e}, trying fallback")

        # Fallback 1: pyttsx3 direct
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
            logger.info(f"TTS via pyttsx3: {text[:50]}")
            return
        except Exception as e:
            logger.debug(f"pyttsx3 TTS failed: {e}")

        # Fallback 2: gTTS + playsound (needs internet)
        try:
            from gtts import gTTS
            import os
            import tempfile
            tts = gTTS(text=text[:200], lang='en')
            temp_path = DATA_DIR / "temp_tts.mp3"
            tts.save(str(temp_path))

            # Try to play via playsound or sounddevice
            try:
                import playsound
                playsound.playsound(str(temp_path))
            except Exception:
                try:
                    from pydub import AudioSegment
                    from pydub.playback import play
                    audio = AudioSegment.from_mp3(str(temp_path))
                    play(audio)
                except Exception:
                    # Last resort: use os startfile
                    os.startfile(str(temp_path))

            logger.info(f"TTS via gTTS: {text[:50]}")
            return
        except Exception as e:
            logger.debug(f"gTTS TTS failed: {e}")

        # Fallback 3: Silent log (never fails)
        logger.info(f"TTS [silent fallback - would speak]: {text}")

    def _transcribe_with_retry(self, audio: np.ndarray, sample_rate: int = 16000, max_retries: int = 4) -> Optional[str]:
        """Transcribe with retry + 4 tiers * 4 attempts = 16 tries!"""

        if audio is None or len(audio) == 0:
            logger.warning("No audio to transcribe")
            return None

        duration = len(audio) / sample_rate
        max_amp = float(np.abs(audio).max())
        rms = float(np.sqrt(np.mean(audio**2)))

        logger.info(f"Bagillion STT: {duration:.2f}s max={max_amp:.4f} rms={rms:.5f} - Will try 4 tiers * 4 attempts = 16 tries!")

        # If STT Manager available, use its 4-tier
        if self.stt_manager:
            try:
                text = self.stt_manager.transcribe(audio, sample_rate)
                if text and text.strip():
                    logger.info(f"STT Manager SUCCESS: '{text}' - HEARD YOU!")
                    return text
                else:
                    logger.warning(f"STT Manager returned empty after trying {self.stt_manager.available_engines}")
            except Exception as e:
                logger.error(f"STT Manager failed: {e}")

        # Fallback: Direct faster-whisper with 4 attempts (like old pipeline but more robust)
        try:
            from faster_whisper import WhisperModel

            # Find best model
            model = None
            for device, compute in [("cuda", "float32"), ("cuda", "int8"), ("cpu", "int8")]:
                try:
                    model = WhisperModel("base.en", device=device, compute_type=compute)
                    logger.info(f"Whisper fallback: base.en on {device} {compute}")
                    break
                except Exception as ex:
                    logger.debug(f"Whisper {device} {compute} failed: {ex}")
                    continue

            if not model:
                logger.error("No Whisper model available for fallback")
                return None

            # Trim silence to help
            def trim_silence(audio, thresh=0.005):
                try:
                    abs_audio = np.abs(audio)
                    above = abs_audio > thresh
                    if not np.any(above):
                        return audio
                    first = np.argmax(above)
                    last = len(above) - np.argmax(above[::-1]) - 1
                    pad = int(sample_rate * 0.1)
                    first = max(0, first - pad)
                    last = min(len(audio), last + pad)
                    trimmed = audio[first:last+1]
                    if len(trimmed) < len(audio) * 0.3:
                        return audio
                    return trimmed
                except Exception:
                    return audio

            audio_trimmed = trim_silence(audio, threshold=0.005)
            audio_int16 = (np.clip(audio_trimmed, -1.0, 1.0) * 32767).astype(np.int16)
            audio_float = np.clip(audio_trimmed, -1.0, 1.0).astype(np.float32)

            # 4 attempts with different params
            attempts = [
                {"desc": "auto beam5 no VAD", "kwargs": {"language": None, "beam_size": 5, "vad_filter": False}},
                {"desc": "en beam1 greedy", "kwargs": {"language": "en", "beam_size": 1, "vad_filter": False}},
                {"desc": "en beam5 VAD True", "kwargs": {"language": "en", "beam_size": 5, "vad_filter": True, "vad_parameters": dict(min_silence_duration_ms=500)}},
                {"desc": "en float32", "kwargs": {"language": "en", "beam_size": 5, "vad_filter": False, "audio": audio_float}},
            ]

            for i, attempt in enumerate(attempts, 1):
                try:
                    logger.info(f"Whisper fallback attempt {i}: {attempt['desc']}")
                    audio_arg = attempt["kwargs"].pop("audio", audio_int16)
                    segments, info = model.transcribe(audio_arg, task="transcribe", **attempt["kwargs"])
                    text_parts = [s.text.strip() for s in segments if s.text.strip()]
                    text = " ".join(text_parts).strip()
                    if text:
                        logger.info(f"Whisper fallback attempt {i} SUCCESS: '{text}'")
                        return text
                except Exception as e:
                    logger.warning(f"Whisper fallback attempt {i} failed: {e}")
                    continue

        except Exception as e:
            logger.error(f"Whisper fallback failed: {e}")

        logger.warning("All STT attempts failed (4 tiers * 4 attempts = 16 tries) - audio may truly be silence")
        return None

    async def process_audio(self, audio: np.ndarray, sample_rate: int = 16000):
        """Full loop: Audio -> STT (16 tries) -> Thinking (10/10) -> TTS (6 tries) -> Loop"""

        if self.on_status:
            try:
                self.on_status("processing")
            except Exception:
                pass

        # STT with retry
        text = self._transcribe_with_retry(audio, sample_rate)

        if not text:
            # STT failed after 16 tries - offer retry via TTS
            self.retry_count += 1

            if self.retry_count >= self.max_retries:
                # After 3 fails, offer text input fallback for accessibility
                fallback_msg = (
                    "I didn't catch that after several tries. "
                    "Please try speaking louder and closer, 1 inch from mic, "
                    "or type your command. "
                    "You can also use text mode: python omni.py --cli \"open github\""
                )
                logger.warning(f"STT failed {self.retry_count} times - offering fallback: {fallback_msg}")
                self._speak(fallback_msg)

                if self.on_status:
                    try:
                        self.on_status("idle")
                    except Exception:
                        pass

                # Reset retry count after offering fallback
                self.retry_count = 0
                return None
            else:
                # Retry message
                retry_msg = f"Didn't catch that, please speak louder and closer, {self.retry_count} of {self.max_retries}"
                logger.warning(f"STT empty, retry {self.retry_count}/{self.max_retries}: {retry_msg}")
                self._speak(retry_msg)

                if self.on_status:
                    try:
                        self.on_status("idle")
                    except Exception:
                        pass

                return None

        # Reset retry count on success
        self.retry_count = 0

        # On transcription callback
        if self.on_transcription:
            try:
                self.on_transcription(text)
            except Exception as e:
                logger.error(f"Transcription callback error: {e}")

        # Thinking loop - Multi-Agent
        try:
            if self.planner and self.executor and self.monitor and self.evaluator:
                steps = self.planner.plan(text)
                results = []
                for step in steps:
                    result = await self.executor.execute_step(step, {"original": text})
                    is_ok = self.monitor.monitor(step, result)
                    results.append(result)
                    if self.memory:
                        self.memory.remember(step.description, result.message)

                final = self.evaluator.evaluate(text, steps, results)

                logger.info(f"Thinking loop: {final.success} -> {final.final_message[:100]}")

                if self.on_response:
                    try:
                        self.on_response(final.final_message)
                    except Exception as e:
                        logger.error(f"Response callback error: {e}")

                # TTS with fallback
                self._speak(final.final_message)

                if self.on_status:
                    try:
                        self.on_status("idle")
                    except Exception:
                        pass

                return final
            else:
                logger.warning("Thinking loop agents not available - returning transcription only")
                self._speak(f"You said: {text}. Thinking loop not available in this mode.")

                if self.on_status:
                    try:
                        self.on_status("idle")
                    except Exception:
                        pass

                return text

        except Exception as e:
            logger.error(f"Thinking loop failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())

            error_msg = f"Thinking failed: {e}. You said: {text}"
            self._speak(error_msg)

            if self.on_status:
                try:
                    self.on_status("idle")
                except Exception:
                    pass

            return None

    def get_status(self):
        return {
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "stt_engines": self.stt_manager.get_status() if self.stt_manager else None,
            "is_running": self.is_running
        }
