"""
OMNI - Main Application (Scalable Architecture)
PyQt5-based autonomous personal agent with modular design.
"""

import sys
import asyncio
from pathlib import Path

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer
from loguru import logger

from omni.core import EventBus, ConfigManager, PluginManager, CommandRegistry
from omni.core.event_bus import EventType
from omni.plugins import BrowserPlugin, WindowsPlugin, SystemPlugin, OMNIPlugin
from omni.ui import TrayIcon
from omni.utils import setup_logger, MetricsCollector


class OMNIApp:
    """Main OMNI Application with scalable architecture."""
    
    def __init__(self):
        # Event bus first
        self.event_bus = EventBus()
        
        # Config
        self.config = ConfigManager()
        self.config.load()
        setup_logger(debug=self.config.get("debug_mode", False))
        
        # Metrics
        self.metrics = MetricsCollector()
        
        # PyQt5 app
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        
        # State
        self.is_listening = True
        self.is_speaking = False
        
        # Init components
        self._init_components()
        self._setup_ui()
        
        logger.info("OMNI initialized successfully")
    
    def _init_components(self) -> None:
        """Initialize all OMNI components"""
        logger.info("Initializing components...")
        
        # Command system
        self.command_registry = CommandRegistry()
        
        # Plugin manager
        self.plugin_manager = PluginManager()
        self._register_plugins()
        
        # TTS
        if self.config.get("tts_enabled", True):
            from omni.tts import KokoroTTS
            self.tts = KokoroTTS(
                voice=self.config.get("tts_voice", "af_sarah"),
                speed=self.config.get("tts_speed", 1.0)
            )
        else:
            self.tts = None
        
        logger.info("All components initialized")
    
    def _register_plugins(self) -> None:
        """Register all command plugins"""
        plugins = [
            BrowserPlugin(port=self.config.get("browser_port", 9222)),
            WindowsPlugin(),
            SystemPlugin(),
            OMNIPlugin(),
        ]
        
        for plugin in plugins:
            self.plugin_manager.register(plugin)
        
        logger.info(f"Registered {len(plugins)} plugins")
    
    def _setup_ui(self) -> None:
        """Setup system tray UI"""
        self.tray = TrayIcon(self, self.event_bus)
        self.tray.show()
        logger.info("System tray ready")
    
    def process_command(self, text: str) -> None:
        """Parse and execute voice command"""
        logger.info(f"Processing: '{text}'")
        
        parsed = self.command_registry.parse(text)
        
        if parsed.action == "unknown":
            self._speak(f"I don't understand: {text}")
            return
        
        # Execute async
        asyncio.create_task(self._execute_command(parsed))
    
    async def _execute_command(self, parsed) -> None:
        """Execute command via plugin system"""
        try:
            plugin = self.plugin_manager.get_plugin(parsed.action)
            
            if not plugin:
                self._speak(f"Command not available: {parsed.action}")
                return
            
            result = await plugin.execute(parsed.entities, {"original": parsed.original})
            
            if result.success:
                if result.message and not result.data:
                    self._speak(result.message)
                elif result.data and result.data.get("action") == "open_settings":
                    self.tray.open_settings()
            else:
                self._speak(result.message)
            
            self.event_bus.emit(EventType.STATUS_UPDATE, "idle", "OMNIApp")
            
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            self._speak("Command execution failed")
            self.event_bus.emit(EventType.STATUS_UPDATE, "error", "OMNIApp")
    
    def _speak(self, text: str) -> None:
        """Speak text via TTS"""
        if self.tts and not self.is_speaking:
            self.is_speaking = True
            self.event_bus.emit(EventType.STATUS_UPDATE, "speaking", "OMNIApp")
            
            def on_complete():
                self.is_speaking = False
                self.event_bus.emit(EventType.STATUS_UPDATE, "idle", "OMNIApp")
            
            self.tts.speak(text, callback=on_complete)
    
    def toggle_listening(self) -> None:
        """Toggle listening on/off"""
        self.is_listening = not self.is_listening
        
        if self.is_listening:
            self._speak("Listening on. Press CapsLock to speak.")
        else:
            self._speak("Listening off.")
        
        logger.info(f"Listening toggled: {self.is_listening}")
    
    def run(self) -> None:
        """Start the OMNI application"""
        logger.info("Starting OMNI...")
        
        # Start event bus
        asyncio.create_task(self.event_bus.start())
        
        # Initial greeting
        QTimer.singleShot(500, lambda: self._speak("OMNI ready. Press CapsLock to speak."))
        
        # Enter event loop
        sys.exit(self.app.exec_())


def main():
    """Entry point"""
    try:
        app = OMNIApp()
        app.run()
    except KeyboardInterrupt:
        logger.info("OMNI shutting down...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        QMessageBox.critical(None, "OMNI Error", f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
