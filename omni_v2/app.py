"""
OMNI V2 App - Phase 1 Complete
Clean, Multi-Agent, 100+ Tools, Chain Commands, Three.js Orb ready
"""

import sys
import os
import asyncio
from pathlib import Path

try:
    from PyQt5.QtWidgets import QApplication, QMessageBox
    from PyQt5.QtCore import QTimer
    from loguru import logger
    from omni_v2.core import EventBus, ConfigManager, PluginManager, CommandRegistry
    from omni_v2.core.event_bus import EventType
    from omni_v2.agents import PlannerAgent, ExecutorAgent, MonitorAgent, EvaluatorAgent, MemoryAgent
    from omni_v2.tools import get_all_tools
    PYQT_AVAILABLE = True
except ImportError as e:
    print(f"PyQt5 not available: {e} - using CLI only")
    PYQT_AVAILABLE = False
    logger = None

class OMNIAppV2:
    """OMNI V2 App - Phase 1"""

    def __init__(self):
        if PYQT_AVAILABLE:
            self.event_bus = EventBus()
            self.config = ConfigManager()
            self.config.load()
            from omni_v2.utils.logger import setup_logger
            setup_logger(debug=self.config.get("debug_mode", False))
            self.app = QApplication(sys.argv)
            self.app.setQuitOnLastWindowClosed(False)
            self.app.setApplicationName("OMNI V2")
            self.app.setApplicationVersion("2.0.0-phase1")
        else:
            self.event_bus = None
            self.config = None
            self.app = None

        self.registry = CommandRegistry()
        self.plugin_manager = PluginManager()
        for tool in get_all_tools():
            self.plugin_manager.register(tool)

        self.planner = PlannerAgent(self.registry)
        self.executor = ExecutorAgent(self.plugin_manager)
        self.monitor = MonitorAgent()
        self.evaluator = EvaluatorAgent()
        self.memory = MemoryAgent()

        if PYQT_AVAILABLE:
            try:
                from omni_v2.ui.tray import TrayIcon
                from omni_v2.ui.orb import VoiceOrb
                self.tray = TrayIcon(self, self.event_bus)
                self.tray.show()
                self.orb = VoiceOrb()
                self.orb.show()
                logger.info("OMNI V2 Phase 1: Orb + Tray ready")
            except Exception as e:
                logger.warning(f"UI failed (headless?): {e}")
                class Dummy:
                    def set_state(self, *a, **k): pass
                    def show(self): pass
                    def update_status(self, *a, **k): pass
                self.tray = Dummy()
                self.orb = Dummy()

        if PYQT_AVAILABLE:
            logger.info("="*60)
            logger.info("OMNI V2 Phase 1 Complete - JARVIS KILLER")
            logger.info(f"Tools: {len(self.plugin_manager.get_all_plugins())} | Multi-Agent: Planner→Executor→Monitor→Evaluator→Memory")
            logger.info("Features: 100+ tools routing, chain commands, 5-turn context, persistent memory")
            logger.info("Next: Phase 2 - LLM Router + Ollama + SQLite + ChromaDB + Vision")
            logger.info("="*60)

    async def process_chain(self, text: str):
        """Process chain commands via multi-agent"""
        if PYQT_AVAILABLE:
            logger.info(f"Processing chain: '{text}'")
            if hasattr(self, 'orb'):
                self.orb.set_state("thinking")

        steps = self.planner.plan(text)
        results = []
        for step in steps:
            if PYQT_AVAILABLE:
                self.event_bus.emit(EventType.CHAIN_STEP, step.description, "Planner")
            result = await self.executor.execute_step(step, {"original": text})
            is_ok = self.monitor.monitor(step, result)
            results.append(result)
            self.memory.remember(step.description, result.message)

        final = self.evaluator.evaluate(text, steps, results)

        if PYQT_AVAILABLE:
            if hasattr(self, 'orb'):
                self.orb.set_state("idle")
            self.event_bus.emit(EventType.CHAIN_COMPLETE, final.final_message, "Evaluator")
            logger.info(f"Chain result: {final.success} -> {final.final_message}")

        return final

    def run(self):
        if not PYQT_AVAILABLE:
            print("PyQt5 not available, cannot run GUI. Use --cli mode")
            return

        demo_cmd = os.environ.get("OMNI_DEMO_COMMAND", "")
        if demo_cmd:
            QTimer.singleShot(800, lambda: asyncio.run(self.process_chain(demo_cmd)))

        QTimer.singleShot(500, lambda: logger.info("OMNI V2 ready. Press V or say 'Hey OMNI'"))

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
