"""
OMNI - Complete Autonomous Personal Agent
MVP + ALPHA + BETA Integrated
Built for Accessibility | Voice-First | Privacy-Safe
"""

import sys
import os
import asyncio
from pathlib import Path

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer
from loguru import logger

# OMNI Core
from omni.core import EventBus, ConfigManager, PluginManager, CommandRegistry
from omni.core.event_bus import EventType
from omni.core.command_registry import ParsedCommand

# OMNI Voice Pipeline
from omni.voice import PTTManager, VoicePipeline, WhisperSTT

# OMNI TTS
from omni.tts import KokoroTTS

# OMNI Plugins
from omni.plugins import get_all_plugins

# OMNI UI
from omni.ui import TrayIcon
from omni.utils import setup_logger, MetricsCollector


class OMNIApp:
    """
    Complete OMNI Application
    Integrates MVP + ALPHA + BETA features
    """
    
    def __init__(self):
        # ===== CORE SYSTEMS =====
        self.event_bus = EventBus()
        self.config = ConfigManager()
        self.config.load()
        setup_logger(debug=self.config.get("debug_mode", False))
        self.metrics = MetricsCollector()
        
        # PyQt5 app
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.app.setApplicationName("OMNI")
        self.app.setApplicationVersion("1.0.0")
        
        # ===== STATE =====
        self.is_listening = True
        self.is_speaking = False
        self.is_recording_macro = False
        self._last_command = None
        
        # ===== INITIALIZE ALL COMPONENTS =====
        self._init_voice()
        self._init_command_system()
        self._init_tts()
        self._setup_ui()
        
        logger.info("=" * 50)
        logger.info("OMNI Initialized - ALL PHASES ACTIVE")
        logger.info("=" * 50)
    
    def _init_voice(self) -> None:
        """Initialize the complete voice pipeline"""
        logger.info("Initializing voice pipeline...")
        
        # PTT Manager (CapsLock detection)
        self.ptt = PTTManager(
            key=self.config.get("ptt_key", "caps_lock"),
            event_bus=self.event_bus
        )
        
        # Whisper STT
        self.whisper = WhisperSTT(
            model_name=self.config.get("whisper_model", "base.en"),
            device=self.config.get("whisper_device", "cuda")
        )
        
        # Voice Pipeline (VAD + capture)
        self.voice_pipeline = VoicePipeline(
            event_bus=self.event_bus,
            on_transcription=self._on_transcription,
            on_status=self._on_voice_status
        )
        
        # Connect PTT events
        self.event_bus.subscribe(EventType.PTT_PRESSED, self._on_ptt_pressed)
        self.event_bus.subscribe(EventType.PTT_RELEASED, self._on_ptt_released)
        
        # Connect status events
        self.event_bus.subscribe(EventType.STATUS_UPDATE, self._on_status_update)
        
        logger.info("Voice pipeline ready")
    
    def _init_command_system(self) -> None:
        """Initialize command system with all plugins"""
        logger.info("Initializing command system...")
        
        # Command registry (pattern → action mapping)
        self.command_registry = CommandRegistry()
        
        # Plugin manager
        self.plugin_manager = PluginManager()
        
        # Register all plugins
        plugins = get_all_plugins()
        for plugin in plugins:
            self.plugin_manager.register(plugin)
        
        logger.info(f"Registered {len(plugins)} plugins: {[p.metadata.name for p in plugins]}")
    
    def _init_tts(self) -> None:
        """Initialize TTS"""
        if self.config.get("tts_enabled", True):
            self.tts = KokoroTTS(
                voice=self.config.get("tts_voice", "af_sarah"),
                speed=self.config.get("tts_speed", 1.0)
            )
            logger.info("TTS ready")
        else:
            self.tts = None
            logger.info("TTS disabled")
    
    def _setup_ui(self) -> None:
        """Setup system tray"""
        self.tray = TrayIcon(self, self.event_bus)
        self.tray.show()
        logger.info("System tray ready")
    
    # ===== VOICE EVENT HANDLERS =====
    
    def _on_ptt_pressed(self, event) -> None:
        """Handle PTT key pressed - start recording"""
        logger.debug("PTT pressed")

        # Guard: don't re-trigger while processing a release
        if self.ptt._is_ptt_processing:
            return

        # Stop any current speech
        if self.is_speaking and self.tts:
            self.tts.stop()

        # Start voice capture
        self.voice_pipeline.start()
        self.event_bus.emit(EventType.STATUS_UPDATE, "recording", "OMNI")
    
    def _on_ptt_released(self, event) -> None:
        """Handle PTT key released - transcribe"""
        logger.debug("PTT released")

        # Mark as processing so press handler won't re-trigger
        self.ptt._is_ptt_processing = True

        try:
            # Stop capture and get audio
            self.voice_pipeline.stop()
            audio = self.voice_pipeline.get_audio()

            if audio is not None and len(audio) > 0:
                # Transcribe
                self.event_bus.emit(EventType.STATUS_UPDATE, "processing", "OMNI")
                self._on_transcription(audio)
            else:
                # No audio detected
                self._speak("No speech detected")
                self.event_bus.emit(EventType.STATUS_UPDATE, "idle", "OMNI")
        finally:
            self.ptt._is_ptt_processing = False
    
    def _on_transcription(self, audio) -> None:
        """Handle transcribed text"""
        text = self.whisper.transcribe(audio)

        if text and text.strip():
            logger.info(f"Transcribed: '{text}'")
            self.metrics.increment("transcriptions_total")
            self.event_bus.emit(EventType.TRANSCRIPTION_COMPLETE, {"text": text}, "OMNI")
            self._process_command(text)
        else:
            # Transcription failed or empty — non-fatal
            logger.warning(f"Transcription returned empty (audio may be too quiet or unclear)")
            self._speak("Didn't catch that, please try again")
            self.event_bus.emit(EventType.STATUS_UPDATE, "idle", "OMNI")
    
    def _on_voice_status(self, status: str) -> None:
        """Handle voice pipeline status updates"""
        self.event_bus.emit(EventType.STATUS_UPDATE, status, "VoicePipeline")
    
    def _on_status_update(self, event) -> None:
        """Handle status updates - sync to tray"""
        if hasattr(self, 'tray'):
            self.tray.update_status(event.data)
    
    # ===== COMMAND PROCESSING =====
    
    def _process_command(self, text: str) -> None:
        """Parse and execute voice command"""
        logger.info(f"Processing: '{text}'")
        self._last_command = text

        # Parse command
        parsed = self.command_registry.parse(text)

        if parsed.action == "unknown":
            self._speak(f"I don't understand: {text}")
            self.event_bus.emit(EventType.STATUS_UPDATE, "error", "OMNI")
            return

        # Build execution context
        context_dict = {
            "original": parsed.original,
            "plugin_count": len(self.plugin_manager.get_all_plugins()),
            "last_command": self._last_command,
        }

        # Execute — use run_until_complete when no loop is running (demo/sync path),
        # otherwise schedule via create_task (normal async path)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop — execute synchronously (demo mode, tests)
            loop = None

        if loop is None:
            try:
                event_loop = asyncio.get_event_loop()
            except RuntimeError:
                event_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(event_loop)
            event_loop.run_until_complete(self._execute_command(parsed, context_dict))
        else:
            asyncio.create_task(self._execute_command(parsed, context_dict))
    
    async def _execute_command(self, parsed: ParsedCommand, context_extra: dict = None) -> None:
        """Execute command via plugin system"""
        context_extra = context_extra or {}
        try:
            # Get plugin for action
            plugin = self.plugin_manager.get_plugin(parsed.action)

            if not plugin:
                self._speak(f"Command not available: {parsed.action}")
                self.event_bus.emit(EventType.STATUS_UPDATE, "error", "OMNI")
                return

            # Execute
            self.event_bus.emit(EventType.COMMAND_EXECUTING, parsed.action, "OMNI")

            plugin_context = {
                "original": parsed.original,
                "plugin_count": len(self.plugin_manager.get_all_plugins()),
                "last_command": context_extra.get("last_command"),
            }
            result = await plugin.execute(parsed.entities, plugin_context)
            
            # Handle result
            if result.success:
                self.event_bus.emit(EventType.COMMAND_COMPLETE, result.data, "OMNI")

                # Handle special result actions
                data = result.data or {}

                if data.get("action") == "open_settings":
                    self.tray.open_settings()
                elif data.get("action") == "repeat_last":
                    # Re-execute the last command directly (no re-parsing = no nested task)
                    last = data.get("command")
                    if last:
                        logger.info(f"Repeating last command: '{last}'")
                        self._speak(f"Repeating: '{last}'")
                        parsed = self.command_registry.parse(last)
                        if parsed.action != "unknown":
                            await self._execute_command(parsed, {"last_command": self._last_command})
                        return  # Don't emit idle status twice
                elif data.get("macro"):
                    # Handle macro execution
                    await self._execute_macro(data["macro"])
                elif result.message:
                    # Normal response — speak it
                    self._speak(result.message)
            else:
                self.event_bus.emit(EventType.COMMAND_FAILED, result.error, "OMNI")
                self._speak(result.message)
            
            self.event_bus.emit(EventType.STATUS_UPDATE, "idle", "OMNI")
            
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            self._speak("Command execution failed")
            self.event_bus.emit(EventType.COMMAND_FAILED, str(e), "OMNI")
            self.event_bus.emit(EventType.STATUS_UPDATE, "error", "OMNI")
    
    async def _execute_macro(self, macro_data: dict) -> None:
        """Execute a voice macro"""
        # TODO: Implement macro execution
        logger.info(f"Executing macro: {macro_data}")
    
    # ===== TTS =====
    
    def _speak(self, text: str) -> None:
        """Speak text via TTS — failures are non-fatal."""
        if not self.tts or not self.config.get("tts_enabled", True):
            logger.info(f"TTS (disabled): {text}")
            return
        
        try:
            if self.is_speaking and self.tts:
                self.tts.stop()
            
            self.is_speaking = True
            self.event_bus.emit(EventType.TTS_START, {"text": text[:50]}, "OMNI")
            
            def on_complete():
                self.is_speaking = False
                self.event_bus.emit(EventType.TTS_END, source="OMNI")
                self.event_bus.emit(EventType.STATUS_UPDATE, "idle", "OMNI")
            
            self.tts.speak(text, callback=on_complete)
        except Exception as e:
            # TTS failure is non-fatal — app keeps running
            logger.warning(f"TTS speak error: {e}")
            self.is_speaking = False
            self.event_bus.emit(EventType.STATUS_UPDATE, "idle", "OMNI")
    
    # ===== CONTROLS =====
    
    def toggle_listening(self) -> None:
        """Toggle listening on/off"""
        self.is_listening = not self.is_listening
        
        if self.is_listening:
            self._speak("Listening on. Press CapsLock to speak.")
        else:
            self._speak("Listening off.")
        
        logger.info(f"Listening: {self.is_listening}")
    
    def get_status(self) -> dict:
        """Get OMNI status"""
        return {
            "version": "1.0.0",
            "listening": self.is_listening,
            "speaking": self.is_speaking,
            "plugins": len(self.plugin_manager.get_all_plugins()),
            "whisper_loaded": self.whisper.is_loaded(),
            "tts_active": self.tts is not None,
        }
    
# ===== MAIN LOOP =====

    def run(self) -> None:
        """Start OMNI application"""
        logger.info("Starting OMNI...")

        # Check for demo mode
        demo_cmd = os.environ.get("OMNI_DEMO_COMMAND", "")

        # Start PTT monitoring — skip in demo mode
        if not demo_cmd:
            self.ptt.start()
        else:
            logger.info("DEMO MODE: PTT monitoring skipped")

        # Schedule demo command execution after event loop starts
        if demo_cmd:
            QTimer.singleShot(800, lambda: self._run_demo_command(demo_cmd))

        # Greeting
        QTimer.singleShot(500, lambda: self._speak(
            "OMNI demo ready." if demo_cmd else "OMNI ready. Press CapsLock to speak. Say 'help' for commands."
        ))

        # Enter Qt event loop
        sys.exit(self.app.exec_())

    def _run_demo_command(self, text: str) -> None:
        """Execute a demo command without microphone."""
        logger.info(f"Demo: executing '{text}'")
        self._process_command(text)


def main(debug: bool = False):
    """Entry point — supports normal and demo mode."""
    import argparse

    # Parse demo-mode argument
    demo_cmd = None
    if "--demo-mode" in sys.argv:
        idx = sys.argv.index("--demo-mode")
        if idx + 1 < len(sys.argv) and sys.argv[idx + 1]:
            demo_cmd = sys.argv[idx + 1]
        else:
            demo_cmd = "demo"  # flag only

    if demo_cmd is not None and demo_cmd != "demo":
        # Specific demo command passed
        logger.info(f"OMNI Demo Mode: '{demo_cmd}'")

    try:
        logger.info("Starting OMNI v1.0.0...")

        # In demo mode, skip PTT monitoring (no mic needed)
        if demo_cmd is not None:
            logger.info("DEMO MODE ACTIVE — PTT monitoring disabled")

        app = OMNIApp()

        app.run()
    except KeyboardInterrupt:
        logger.info("OMNI stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        try:
            QMessageBox.critical(None, "OMNI Error", f"Fatal error: {e}")
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()