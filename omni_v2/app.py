"""
OMNI V2 App - Phase 3 Fixed - Actually HEARS You! + Wake Word + HUD Fixed
Clean, Multi-Agent, 100+ Tools, Chain Commands, Vision, Wake Word, Three.js Orb
"""

import sys
import os
import asyncio
from pathlib import Path
import threading

try:
    from PyQt5.QtWidgets import QApplication, QMessageBox
    from PyQt5.QtCore import QTimer
    from loguru import logger
    from omni_v2.core import EventBus, ConfigManager, PluginManager, CommandRegistry
    from omni_v2.core.event_bus import EventType
    from omni_v2.agents import PlannerAgent, ExecutorAgent, MonitorAgent, EvaluatorAgent, MemoryAgent
    from omni_v2.tools import get_all_tools
    from omni_v2.core.paths import DATA_DIR
    PYQT_AVAILABLE = True
except ImportError as e:
    print(f"PyQt5 not available: {e} - using CLI only")
    PYQT_AVAILABLE = False
    logger = None

class OMNIAppV2:
    """OMNI V2 App - Phase 3 Fixed - Actually HEARS You!"""

    def __init__(self):
        if PYQT_AVAILABLE:
            self.event_bus = EventBus()
            self.config = ConfigManager()
            self.config.load()
            try:
                from omni_v2.utils.logger import setup_logger
                setup_logger(debug=self.config.get("debug_mode", False))
            except Exception:
                pass
            self.app = QApplication(sys.argv)
            self.app.setQuitOnLastWindowClosed(False)
            self.app.setApplicationName("OMNI V2")
            self.app.setApplicationVersion("2.0.0-phase3-fixed")
        else:
            self.event_bus = None
            self.config = None
            self.app = None

        # Core - Multi-Agent
        self.registry = CommandRegistry()
        self.plugin_manager = PluginManager()
        for tool in get_all_tools():
            self.plugin_manager.register(tool)

        self.planner = PlannerAgent(self.registry)
        self.executor = ExecutorAgent(self.plugin_manager)
        self.monitor = MonitorAgent()
        self.evaluator = EvaluatorAgent()
        self.memory = MemoryAgent()

        # Voice Pipeline V2 - Actually HEARS You! PTT manual only, no auto VAD cut
        self.voice_pipeline = None
        self.ptt_manager = None
        self._init_voice_pipeline()

        # Phase 3 - Vision, Wake Word, Face Auth, LLM Router
        self.vision_capture = None
        self.vision_llava = None
        self.wakeword_detector = None
        self.face_auth = None
        self.llm_router = None

        self._init_phase3_modules()

        # UI
        if PYQT_AVAILABLE:
            try:
                from omni_v2.ui.tray import TrayIcon
                from omni_v2.ui.orb import VoiceOrb
                from omni_v2.ui.hud import ArcReactorHUD
                from omni_v2.ui.dashboard import SystemDashboard

                self.tray = TrayIcon(self, self.event_bus)
                self.tray.show()

                self.orb = VoiceOrb()
                self.orb.show()

                try:
                    self.hud = ArcReactorHUD()
                    self.hud.show()
                    logger.info("ArcReactorHUD V2 - Fixed float->int, no crash")
                except Exception as e:
                    logger.warning(f"HUD failed: {e}")
                    self.hud = None

                try:
                    self.dashboard = SystemDashboard()
                    logger.info("SystemDashboard V2 - Ready")
                except Exception as e:
                    logger.warning(f"Dashboard failed: {e}")
                    self.dashboard = None

                logger.info("OMNI V2 Phase 3 Fixed UI: Orb + Tray + HUD + Dashboard ready")
            except Exception as e:
                if PYQT_AVAILABLE and logger:
                    logger.warning(f"UI failed (headless?): {e}")
                class Dummy:
                    def set_state(self, *a, **k): pass
                    def show(self): pass
                    def hide(self): pass
                    def update_status(self, *a, **k): pass
                    def set_transcription(self, *a, **k): pass
                    def set_system_stats(self, *a, **k): pass
                self.tray = Dummy()
                self.orb = Dummy()
                self.hud = Dummy()
                self.dashboard = Dummy()

        if PYQT_AVAILABLE and logger:
            logger.info("="*70)
            logger.info("OMNI V2 Phase 3 Fixed - Actually HEARS You! - JARVIS KILLER")
            logger.info(f"Tools: {len(self.plugin_manager.get_all_plugins())} | Multi-Agent: Planner→Executor→Monitor→Evaluator→Memory")
            logger.info(f"Data: {DATA_DIR} (unanimous)")
            logger.info(f"Voice: PTT V toggle (manual stop only, no auto VAD cut) + Whisper CUDA + Silero VAD")
            logger.info(f"WakeWord: {self.wakeword_detector.backend if self.wakeword_detector else 'None (PTT only)'}")
            logger.info(f"Vision: ScreenCapture + LLaVA | FaceAuth: {self.face_auth.face_recognition_available if self.face_auth else False}")
            logger.info(f"UI: Orb + HUD (fixed float->int) + Dashboard")
            logger.info("Features: 100+ tools, chain commands, context memory, SQLite+Chroma, LLM Router, Vision, Wake Word, Actually HEARS")
            logger.info("Fix: Voice pipeline now PTT manual only, no auto VAD silence cut, VERY permissive thresholds (rms 0.0005)")
            logger.info("="*70)

    def _init_voice_pipeline(self):
        """Init voice pipeline that ACTUALLY HEARS YOU - PTT manual only"""
        try:
            from omni_v2.voice.pipeline import VoicePipelineV2
            from omni_v2.voice.audio_device import AudioDeviceManager
            from omni_v2.core.config_manager import ConfigManager

            # Try to get device manager
            try:
                device_manager = AudioDeviceManager()
                # Prefer Realtek mic (fixed in audio_device.py)
                device_index = device_manager.get_input_device_index()
                logger.info(f"Voice: Using mic index {device_index}")
            except Exception as e:
                logger.warning(f"Device manager failed: {e}, using default mic")
                device_manager = None
                device_index = None

            self.voice_pipeline = VoicePipelineV2(
                device_manager=device_manager,
                device_index=device_index,
                on_transcription=self._on_transcription,
                on_status=self._on_voice_status
            )

            # PTT Manager - V toggle (manual ON/OFF, no auto cut)
            try:
                from omni_v2.voice.ptt_manager import PTTManager
                from omni_v2.core.event_bus import EventBus, EventType

                self.ptt_manager = PTTManager(
                    key=self.config.get("ptt_key", "v") if self.config else "v",
                    event_bus=self.event_bus
                )

                # Subscribe PTT events to voice pipeline
                if self.event_bus:
                    self.event_bus.subscribe(EventType.PTT_PRESSED, self._on_ptt_pressed)
                    self.event_bus.subscribe(EventType.PTT_RELEASED, self._on_ptt_released)

                logger.info("Voice Pipeline V2: PTT V toggle, manual stop only, no auto VAD cut - WILL HEAR YOU")

            except Exception as e:
                logger.warning(f"PTT Manager init failed: {e}, voice pipeline still works via direct calls")

        except Exception as e:
            logger.error(f"Voice pipeline init failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            self.voice_pipeline = None

    def _init_phase3_modules(self):
        """Init Phase 3 modules - Vision, Wake Word, Face Auth, LLM Router"""

        # Vision
        try:
            from omni_v2.vision.screen import ScreenCapture
            from omni_v2.vision.llava import LLaVAVision
            self.vision_capture = ScreenCapture()
            self.vision_llava = LLaVAVision()
            if PYQT_AVAILABLE and logger:
                logger.info("Vision V2: ScreenCapture + LLaVA ready")
        except Exception as e:
            if PYQT_AVAILABLE and logger:
                logger.warning(f"Vision init failed: {e}")

        # Wake Word - Fixed to actually work with openwakeword
        try:
            from omni_v2.voice.wake_word import WakeWordDetector
            self.wakeword_detector = WakeWordDetector(keyword="hey omni")
            if PYQT_AVAILABLE and logger:
                status = self.wakeword_detector.get_status()
                logger.info(f"WakeWord V2: {status}")
        except Exception as e:
            if PYQT_AVAILABLE and logger:
                logger.warning(f"WakeWord init failed: {e}")
            self.wakeword_detector = None

        # Face Auth
        try:
            from omni_v2.security.face_auth import FaceAuth
            self.face_auth = FaceAuth()
            if PYQT_AVAILABLE and logger:
                logger.info(f"FaceAuth V2: Available={self.face_auth.face_recognition_available}")
        except Exception as e:
            if PYQT_AVAILABLE and logger:
                logger.warning(f"FaceAuth init failed: {e}")

        # LLM Router
        try:
            from omni_v2.llm.router import LLMRouter
            self.llm_router = LLMRouter()
            if PYQT_AVAILABLE and logger:
                logger.info(f"LLM Router V2: Ollama={self.llm_router.ollama_available}")
        except Exception as e:
            if PYQT_AVAILABLE and logger:
                logger.warning(f"LLM Router init failed: {e}")

    # ===== VOICE EVENT HANDLERS - Actually HEARS You! =====

    def _on_ptt_pressed(self, event):
        """PTT pressed - start recording (manual, no auto VAD cut)"""
        logger.info("PTT pressed - start recording (speak now! LOUD and CLOSE 2 inches)")
        if hasattr(self, 'orb'):
            self.orb.set_state("listening")
        if hasattr(self, 'hud'):
            try:
                self.hud.set_transcription("Listening... Speak LOUD! (PTT manual, no auto cut)")
            except Exception:
                pass

        if self.voice_pipeline:
            self.voice_pipeline.start()
        else:
            logger.error("Voice pipeline not available!")

    def _on_ptt_released(self, event):
        """PTT released - stop and transcribe (manual stop)"""
        logger.info("PTT released - stop recording and transcribe")
        if hasattr(self, 'orb'):
            self.orb.set_state("thinking")

        if self.voice_pipeline:
            self.voice_pipeline.stop()
        else:
            logger.error("Voice pipeline not available!")

    def _on_transcription(self, text: str):
        """Handle transcribed text - from VoicePipelineV2"""
        logger.info(f"Transcribed (HEARD YOU!): '{text}'")

        if hasattr(self, 'hud'):
            try:
                self.hud.set_transcription(f"Heard: {text}")
            except Exception:
                pass

        # Process via multi-agent chain
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Run chain processing
        try:
            result = loop.run_until_complete(self.process_chain(text))
            logger.info(f"Chain result: {result.success} -> {result.final_message[:100]}")

            # TTS response (if available)
            # For Phase 3, just log, Phase 4 will do TTS
            if hasattr(self, 'orb'):
                self.orb.set_state("speaking")
                # Simulate speaking then idle
                import threading
                def back_to_idle():
                    import time
                    time.sleep(2)
                    try:
                        self.orb.set_state("idle")
                    except Exception:
                        pass
                threading.Thread(target=back_to_idle, daemon=True).start()

        except Exception as e:
            logger.error(f"Chain processing failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())

    def _on_voice_status(self, status: str):
        """Voice pipeline status"""
        logger.info(f"Voice status: {status}")
        if hasattr(self, 'orb'):
            state_map = {
                "recording": "listening",
                "processing": "thinking",
                "idle": "idle",
                "error": "idle"
            }
            self.orb.set_state(state_map.get(status, "idle"))

    async def process_chain(self, text: str):
        """Process chain via multi-agent + vision context"""
        if PYQT_AVAILABLE and logger:
            logger.info(f"Processing chain V2: '{text}'")
            if hasattr(self, 'orb'):
                self.orb.set_state("thinking")

        # Vision context if needed
        vision_context = ""
        if any(kw in text.lower() for kw in ["screen", "what's on", "see", "look"]):
            if self.vision_capture and self.vision_llava:
                try:
                    img = self.vision_capture.capture()
                    if img:
                        vision_desc = await self.vision_llava.describe_screen(img)
                        vision_context = f" Vision: {vision_desc}"
                        logger.info(f"Vision: {vision_desc[:100]}")
                except Exception as e:
                    logger.warning(f"Vision failed: {e}")

        steps = self.planner.plan(text)
        results = []
        for step in steps:
            if PYQT_AVAILABLE and self.event_bus:
                try:
                    self.event_bus.emit(EventType.CHAIN_STEP, step.description, "Planner")
                except Exception:
                    pass
            result = await self.executor.execute_step(step, {"original": text + vision_context})
            is_ok = self.monitor.monitor(step, result)
            results.append(result)
            self.memory.remember(step.description, result.message)

        final = self.evaluator.evaluate(text, steps, results)

        # LLM enhance for chat queries
        if self.llm_router and any(kw in text.lower() for kw in ["who", "what", "how", "why", "explain", "plan"]):
            try:
                llm_resp = await self.llm_router.generate(text, tier="brain")
                final.final_message += f"\n\n[LLM {llm_resp.tier}]: {llm_resp.text[:200]}"
            except Exception as e:
                logger.warning(f"LLM enhance failed: {e}")

        if PYQT_AVAILABLE and logger:
            if hasattr(self, 'orb'):
                self.orb.set_state("idle")
            if hasattr(self, 'hud'):
                try:
                    self.hud.set_transcription(final.final_message[:100])
                except Exception:
                    pass
            logger.info(f"Chain result V2: {final.success} -> {final.final_message[:100]}")

        return final

    def start_wakeword_listener(self):
        """Start wake word listener in background"""
        if not self.wakeword_detector or not self.wakeword_detector.is_available():
            if PYQT_AVAILABLE and logger:
                logger.info("Wake word not available, using PTT V toggle only (press V)")
            return

        def on_wake():
            if PYQT_AVAILABLE and logger:
                logger.info("Hey OMNI detected! Starting voice capture...")
                if hasattr(self, 'orb'):
                    self.orb.set_state("listening")
                if hasattr(self, 'hud'):
                    self.hud.set_transcription("Hey OMNI heard! Listening...")
            # Start recording as if PTT pressed
            if self.voice_pipeline:
                self.voice_pipeline.start()
                # Auto-stop after 5 sec for wake word mode
                import threading
                def auto_stop():
                    import time
                    time.sleep(5)
                    if self.voice_pipeline and self.voice_pipeline.is_recording:
                        logger.info("Wake word mode: auto-stop after 5 sec")
                        self.voice_pipeline.stop()
                threading.Thread(target=auto_stop, daemon=True).start()

        thread = threading.Thread(
            target=self.wakeword_detector.listen_for_wake_word,
            args=(on_wake,),
            daemon=True,
            name="WakeWordV2"
        )
        thread.start()
        if PYQT_AVAILABLE and logger:
            logger.info("Wake word listener started - say Hey Jarvis / Hey Omni / Alexa")

    def run(self):
        if not PYQT_AVAILABLE:
            print("PyQt5 not available, use --cli mode")
            return

        # Start PTT
        if hasattr(self, 'ptt_manager') and self.ptt_manager:
            try:
                self.ptt_manager.start()
                logger.info("PTT V toggle started - press V to speak LOUD and CLOSE")
            except Exception as e:
                logger.warning(f"PTT start failed: {e}")

        # Start wake word listener if available and enabled
        if self.config and self.config.get("wakeword_enabled", True):
            self.start_wakeword_listener()

        demo_cmd = os.environ.get("OMNI_DEMO_COMMAND", "")
        if demo_cmd:
            QTimer.singleShot(800, lambda: asyncio.run(self.process_chain(demo_cmd)))

        QTimer.singleShot(500, lambda: logger.info("OMNI V2 Phase 3 Fixed ready. Press V LOUD and CLOSE (2 inches), or say Hey Jarvis/Alexa"))

        sys.exit(self.app.exec_())

def main():
    try:
        app = OMNIAppV2()
        app.run()
    except KeyboardInterrupt:
        print("OMNI V2 stopped")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
