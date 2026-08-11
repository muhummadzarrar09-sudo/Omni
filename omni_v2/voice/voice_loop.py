"""
OMNI VOICE LOOP (Phase 10) — the hands-free "Hey OMNI" conversation cycle.

The actual JARVIS moment: always-on wake word → hear you → brain thinks →
speak back → listen again. This module is a clean orchestrator on top of the
existing (already-offline) pieces:
  - wake word   -> openwakeword (offline, no key)
  - STT         -> faster-whisper (offline)
  - brain       -> Brain.think() (identity + tiering + memory already injected)
  - TTS         -> piper (offline) / TTSBest

Design:
  - Pluggable components with sane defaults, so it's fully unit-testable
    offline with fakes (no camera/mic/model needed).
  - A `respond` call does one full turn: STT text -> brain.think -> TTS speech.
  - The `VoiceLoop` background thread continuously runs: wake detect -> record
    -> transcribe -> respond -> loop.
  - Voice can also drive GOALS: "hey omni, research X and report back" routes
    through the brain; if a GoalStack is attached, long intents can become
    away-mode goals automatically.

Fully local. No cloud. Falls back gracefully when any component is missing.
"""
from __future__ import annotations
import threading
import time
from typing import Any, Callable, Dict, List, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("VoiceLoop")


class VoiceLoop:
    """Orchestrates wake -> listen -> think -> speak, one continuous loop."""

    def __init__(
        self,
        wake_detector=None,       # detect_wake() -> bool
        audio_capture=None,       # record_turn() -> audio (any) 
        stt=None,                 # transcribe(audio) -> str
        brain=None,               # think(text) -> BrainResponse
        tts=None,                 # speak(text) -> bool
        goals=None,               # optional GoalStack for voice-driven goals
        on_status=None,           # callback(status) for UI
        on_transcription=None,    # callback(text) when user speaks
        on_reply=None,            # callback(reply_text)
    ):
        self.wake_detector = wake_detector
        self.audio_capture = audio_capture
        self.stt = stt
        self.brain = brain
        self.tts = tts
        self.goals = goals
        self.on_status = on_status
        self.on_transcription = on_transcription
        self.on_reply = on_reply

        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.RLock()
        self._turns = 0
        self._last_error = ""

    # -- control -----------------------------------------------------------
    def start(self) -> bool:
        """Start the background always-on loop. Returns True if components are usable."""
        if self._running:
            return True
        if not self._usable():
            logger.warning("VoiceLoop: not all components available; not starting")
            return False
        self._stop.clear()
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="omni-voice")
        self._thread.start()
        self._set_status("listening")
        logger.info("VoiceLoop started (always-on 'Hey OMNI')")
        return True

    def stop(self) -> None:
        self._running = False
        self._stop.set()
        self._set_status("stopped")

    @property
    def running(self) -> bool:
        return self._running

    def _usable(self) -> bool:
        # wake + stt + brain + tts should exist for a real loop
        return all(c is not None for c in (self.stt, self.brain, self.tts))

    def _set_status(self, s: str) -> None:
        if self.on_status:
            try:
                self.on_status(s)
            except Exception:
                pass

    # -- one full turn (also callable directly / for tests) ----------------
    def respond(self, text: str) -> str:
        """
        One full spoken turn: run text through the brain and speak the reply.
        Returns the reply text. Optionally routes long intents into a goal.
        """
        text = (text or "").strip()
        if not text:
            return ""
        if self.on_transcription:
            try:
                self.on_transcription(text)
            except Exception:
                pass
        reply = "Sorry, I didn't catch that."
        # Route voice-driven goals: "research X and report back" -> goal
        if self.goals is not None and self._is_goal_intent(text):
            try:
                goal = self.goals.create_goal(text, title=text[:60])
                reply = f"On it. I've started a goal: {text}. I'll report back when it's done."
            except Exception as e:
                logger.warning(f"voice goal create failed: {e}")
                reply = "I couldn't start that goal."
            if self.tts:
                self.tts.speak(reply)
            if self.on_reply:
                self.on_reply(reply)
            return reply

        if self.brain is not None:
            try:
                resp = self.brain.think(text)
                reply = resp.text or "Done."
                # speak the reply
                if self.tts:
                    self.tts.speak(reply)
            except Exception as e:
                logger.warning(f"brain.think failed: {e}")
                reply = "Something went wrong while I was thinking."
        elif self.tts:
            # no brain: just acknowledge
            self.tts.speak("I heard you, but my brain isn't loaded.")
            reply = "I heard you, but my brain isn't loaded."

        if self.on_reply:
            try:
                self.on_reply(reply)
            except Exception:
                pass
        with self._lock:
            self._turns += 1
        return reply

    @staticmethod
    def _is_goal_intent(text: str) -> bool:
        t = text.lower()
        return any(ph in t for ph in [
            "research", "investigate", "find out about", "look into",
            "plan", "build me", "make a plan to", "set up a",
        ]) and any(ph in t for ph in [
            "and report", "report back", "and tell me", "while i'm away",
            "and send me", "when done",
        ])

    # -- background loop ----------------------------------------------------
    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._iteration()
            except Exception as e:
                self._last_error = str(e)
                logger.warning(f"VoiceLoop iteration error: {e}")
            self._stop.wait(0.2)

    def _iteration(self) -> None:
        # 1) wait for wake word
        self._set_status("listening")
        if self.wake_detector is not None:
            # non-blocking wake check; if not triggered, keep waiting
            try:
                if not self.wake_detector.detect_wake():
                    return
            except Exception:
                return
            # small debounce so the wake word itself isn't captured
            time.sleep(0.4)
        # 2) capture the turn
        self._set_status("hearing")
        audio = None
        if self.audio_capture is not None:
            try:
                audio = self.audio_capture.record_turn()
            except Exception as e:
                self._last_error = f"capture: {e}"
                logger.warning(f"audio capture failed: {e}")
                return
        # 3) transcribe
        text = ""
        if self.stt is not None and audio is not None:
            self._set_status("thinking")
            try:
                text = self.stt.transcribe(audio) or ""
            except Exception as e:
                self._last_error = f"stt: {e}"
                logger.warning(f"stt failed: {e}")
                return
        # 4) respond (think + speak)
        if text.strip():
            self.respond(text)
        self._set_status("listening")

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "running": self._running,
                "turns": self._turns,
                "last_error": self._last_error,
                "has_wake": self.wake_detector is not None,
                "has_stt": self.stt is not None,
                "has_brain": self.brain is not None,
                "has_tts": self.tts is not None,
            }


def get_voice_loop(**kwargs) -> VoiceLoop:
    return VoiceLoop(**kwargs)
