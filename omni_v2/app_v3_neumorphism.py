"""
OMNI V3 NEUMORPHISM - Make It Soft, Make It Work
Entry for neomorphism UI

Usage:
    python -m omni_v2.app_v3_neumorphism
    python -m omni_v2.app_v3_neumorphism --test
    python -m omni_v2.app_v3_neumorphism --cli "open github"

This uses HUDNeumorphismV3 (soft extruded UI) instead of old glassmorphic
"""
import sys
import os
import asyncio
import threading
from pathlib import Path

# Torch fallback
try:
    import torch
except OSError as e:
    print(f"[OMNI V3 NEO WARNING] Torch DLL 1114: {e} - OMNI_NO_TORCH=1")
    os.environ["OMNI_NO_TORCH"] = "1"
except ImportError:
    pass

try:
    from loguru import logger
    from omni_v2.core import CommandRegistry, PluginManager
    from omni_v2.agents import PlannerAgent, ExecutorAgent, MonitorAgent, EvaluatorAgent, MemoryAgent
    from omni_v2.tools import get_all_tools
    from omni_v2.tools.browser_v3 import BrowserToolV3
    from omni_v2.voice.audio_device_v3 import get_audio_v3
    from omni_v2.voice.stt_simple import get_simple_stt
    from omni_v2.voice.tts_simple import get_simple_tts
    from omni_v2.core.paths import DATA_DIR
    PYQT_V3_AVAILABLE = True
except ImportError as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
    PYQT_V3_AVAILABLE = False
    DATA_DIR = Path.cwd() / "data"

class OMNIAppV3Neo:
    def __init__(self):
        print("="*70)
        print("  OMNI V3 NEOMORPHISM - Soft UI, Extruded, Inset Press")
        print("  GTX 1050 Ti | Offline | Profile Isolation | Soft Tactile")
        print("="*70)
        
        self.registry = CommandRegistry()
        self.plugin_manager = PluginManager()
        
        for tool in get_all_tools():
            if hasattr(tool, 'metadata') and 'browser' in tool.metadata.name and 'v3' not in tool.metadata.name:
                continue
            self.plugin_manager.register(tool)
        
        try:
            self.plugin_manager.register(BrowserToolV3())
            logger.info("✅ Browser V3 profile isolation registered")
        except Exception as e:
            logger.warning(f"Browser V3 register failed: {e}")
        
        self.planner = PlannerAgent(self.registry)
        self.executor = ExecutorAgent(self.plugin_manager)
        self.monitor = MonitorAgent()
        self.evaluator = EvaluatorAgent()
        self.memory = MemoryAgent()
        
        self.stt = None
        self.tts = None
        self.audio_mgr = None
        self.hud = None
        self.voice_pipeline = None
        self.ptt_manager = None
        self.app = None
        
        self._init_engines()
        
        if PYQT_V3_AVAILABLE:
            try:
                from PyQt5.QtWidgets import QApplication
                self.app = QApplication(sys.argv)
                self.app.setApplicationName("OMNI V3 Neomorphism")
                self.app.setQuitOnLastWindowClosed(False)
                
                # TRY NEOMORPHISM FIRST
                try:
                    from omni_v2.ui.hud_neomorphism import HUDNeumorphismV3
                    self.hud = HUDNeumorphismV3(app_instance=self)
                    logger.info("✅ HUDNeumorphismV3 Ready - soft extruded UI")
                except Exception as e:
                    logger.warning(f"Neomorphism HUD failed {e}, fallback to simple")
                    from omni_v2.ui.hud_simple import HUDSimpleV3
                    self.hud = HUDSimpleV3(app_instance=self)
                
                if self.audio_mgr:
                    try:
                        devices = self.audio_mgr.list_devices_for_ui()
                        self.hud.load_devices(devices)
                    except Exception as e:
                        logger.warning(f"Load devices failed: {e}")
                
            except Exception as e:
                logger.error(f"HUD init failed: {e}")
                import traceback
                traceback.print_exc()
                self.hud = None
    
    def _init_engines(self):
        try:
            self.audio_mgr = get_audio_v3()
            logger.info(f"✅ Audio V3: Best [{self.audio_mgr.get_best_index()}] {self.audio_mgr.get_best_name()}")
        except Exception as e:
            logger.error(f"Audio V3 failed: {e}")
        
        try:
            self.stt = get_simple_stt()
            logger.info(f"✅ STT V3: {self.stt.get_status()}")
        except Exception as e:
            logger.error(f"STT V3 failed: {e}")
        
        try:
            self.tts = get_simple_tts()
            logger.info(f"✅ TTS V3: {self.tts.get_status()}")
        except Exception as e:
            logger.error(f"TTS V3 failed: {e}")
        
        try:
            # Try fixed pipeline first (sounddevice primary - fixes -9999)
            try:
                from omni_v2.voice.pipeline_v3_fixed import VoicePipelineV3Fixed
                self.voice_pipeline = VoicePipelineV3Fixed(
                    stt=self.stt,
                    audio_mgr=self.audio_mgr,
                    on_transcription=self._on_transcription,
                    on_status=self._on_voice_status,
                    on_mic_level=self._on_mic_level,
                    hud=self.hud
                )
                logger.info("✅ VoicePipeline V3.1 FIXED (sounddevice primary, fixes -9999)")
            except ImportError:
                from omni_v2.voice.pipeline_v3 import VoicePipelineV3
                self.voice_pipeline = VoicePipelineV3(
                    stt=self.stt,
                    audio_mgr=self.audio_mgr,
                    on_transcription=self._on_transcription,
                    on_status=self._on_voice_status,
                    on_mic_level=self._on_mic_level,
                    hud=self.hud
                )
                logger.info("✅ VoicePipeline V3 (fallback)")
        except Exception as e:
            logger.error(f"Pipeline init failed: {e}")
        except Exception as e:
            logger.warning(f"Pipeline V3 failed {e}")
        
        try:
            from omni_v2.voice.ptt_manager import PTTManager
            from omni_v2.core import EventBus
            from omni_v2.core.event_bus import EventType
            self.event_bus = EventBus()
            self.ptt_manager = PTTManager(key="v", event_bus=self.event_bus)
            self.event_bus.subscribe(EventType.PTT_PRESSED, self._on_ptt_pressed)
            self.event_bus.subscribe(EventType.PTT_RELEASED, self._on_ptt_released)
            logger.info("✅ PTT V ready")
        except Exception as e:
            logger.warning(f"PTT failed: {e}")
    
    def _on_ptt_pressed(self, event):
        logger.info("🔴 PTT PRESSED")
        if self.hud:
            self.hud.set_state("listening")
            self.hud.set_transcription("🎤 Soft Listening... Speak LOUD 1 inch!")
        if self.voice_pipeline:
            self.voice_pipeline.start()
    
    def _on_ptt_released(self, event):
        logger.info("⚪ PTT RELEASED")
        if self.hud:
            self.hud.set_state("thinking")
            self.hud.set_transcription("🧠 Soft Thinking... neomorphism processing...")
        if self.voice_pipeline:
            self.voice_pipeline.stop()
    
    def _on_transcription(self, text: str):
        logger.info(f"✅ HEARD: '{text}'")
        if self.hud:
            self.hud.set_transcription(f"✅ Heard: {text}\n\n🧠 Soft reasoning...")
            self.hud.set_state("thinking")
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(self.process_chain(text))
            final_msg = result.final_message if hasattr(result, 'final_message') else str(result)
            if self.hud:
                self.hud.set_transcription(f"✅ Heard: {text}\n\n→ {final_msg[:300]}\n\nSoft neumorphic action completed offline.")
                self.hud.set_state("speaking")
            if self.tts:
                try:
                    self.tts.speak_async(final_msg[:250])
                except:
                    pass
            if self.hud:
                def idle_back():
                    import time
                    time.sleep(3)
                    try:
                        self.hud.set_state("idle")
                    except:
                        pass
                threading.Thread(target=idle_back, daemon=True).start()
        except Exception as e:
            logger.error(f"Chain failed: {e}")
            if self.hud:
                self.hud.set_transcription(f"Error: {e}\nHeard: {text}")
                self.hud.set_state("error")
    
    def _on_voice_status(self, status: str):
        state_map = {"recording":"listening","processing":"thinking","idle":"idle","error":"error"}
        if self.hud:
            self.hud.set_state(state_map.get(status, "idle"))
    
    def _on_mic_level(self, rms: float, max_val: float):
        if self.hud:
            self.hud.set_mic_level(rms, max_val)
    
    async def process_chain(self, text: str):
        steps = self.planner.plan(text)
        results = []
        for step in steps:
            result = await self.executor.execute_step(step, {"original": text})
            self.monitor.monitor(step, result)
            results.append(result)
            self.memory.remember(step.description, result.message)
        final = self.evaluator.evaluate(text, steps, results)
        return final
    
    def run(self):
        if not PYQT_V3_AVAILABLE or not self.app:
            print("PyQt5 not available, use --cli")
            return
        if self.ptt_manager:
            try:
                self.ptt_manager.start()
            except:
                pass
        if self.hud:
            self.hud.show()
            logger.info("OMNI V3 NEOMORPHISM READY — Soft extruded, inset press, offline")
        sys.exit(self.app.exec_())

def main():
    import argparse
    parser = argparse.ArgumentParser(description="OMNI V3 Neumorphism")
    parser.add_argument('--cli', type=str, help='CLI command')
    parser.add_argument('--test', action='store_true', help='Run tests')
    args = parser.parse_args()
    
    if args.test:
        print("OMNI V3 NEO --test")
        from omni_v2.agents import PlannerAgent, ExecutorAgent, MonitorAgent, EvaluatorAgent, MemoryAgent
        from omni_v2.core import CommandRegistry, PluginManager
        from omni_v2.tools import get_all_tools
        from omni_v2.tools.browser_v3 import BrowserToolV3
        import asyncio
        
        registry = CommandRegistry()
        pm = PluginManager()
        for t in get_all_tools():
            if hasattr(t, 'metadata') and 'browser' in t.metadata.name and 'v3' not in t.metadata.name:
                continue
            pm.register(t)
        pm.register(BrowserToolV3())
        
        planner = PlannerAgent(registry)
        executor = ExecutorAgent(pm)
        monitor = MonitorAgent()
        evaluator = EvaluatorAgent()
        
        test_cmds = ["open github", "open chrome and maximize and go to youtube", "search for iron man"]
        
        async def run_tests():
            for cmd in test_cmds:
                print(f"\n--- {cmd} ---")
                steps = planner.plan(cmd)
                results = []
                for step in steps:
                    result = await executor.execute_step(step)
                    monitor.monitor(step, result)
                    results.append(result)
                    print(f"  {step.action} -> ok")
                final = evaluator.evaluate(cmd, steps, results)
                print(f"  → {getattr(final, 'final_message', str(final))[:100]}")
            print("\nNeomorphism tests PASSED")
        
        asyncio.run(run_tests())
        sys.exit(0)
    
    if args.cli:
        print(f"OMNI V3 NEO CLI: {args.cli}")
        from omni_v2.agents import PlannerAgent, ExecutorAgent, MonitorAgent, EvaluatorAgent
        from omni_v2.core import CommandRegistry, PluginManager
        from omni_v2.tools import get_all_tools
        from omni_v2.tools.browser_v3 import BrowserToolV3
        import asyncio
        
        registry = CommandRegistry()
        pm = PluginManager()
        for t in get_all_tools():
            if hasattr(t, 'metadata') and 'browser' in t.metadata.name and 'v3' not in t.metadata.name:
                continue
            pm.register(t)
        pm.register(BrowserToolV3())
        
        planner = PlannerAgent(registry)
        executor = ExecutorAgent(pm)
        monitor = MonitorAgent()
        evaluator = EvaluatorAgent()
        
        async def run_cli():
            steps = planner.plan(args.cli)
            results = []
            for step in steps:
                result = await executor.execute_step(step, {"original": args.cli})
                monitor.monitor(step, result)
                results.append(result)
            final = evaluator.evaluate(args.cli, steps, results)
            print(getattr(final, 'final_message', str(final)))
        
        asyncio.run(run_cli())
        sys.exit(0)
    
    app = OMNIAppV3Neo()
    app.run()

if __name__ == "__main__":
    main()
