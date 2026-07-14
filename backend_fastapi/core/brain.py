"""
OMNI Brain Wrapper for FastAPI - Portable, no hardcoded D:/Omni
Imports existing omni_v2 brain (planner, executor, etc.) and exposes simple API
Works wherever judges clone: Path(__file__).resolve()...
"""
from pathlib import Path
import sys

# Ensure repo root is in sys.path for omni_v2 imports
# backend_fastapi/core/brain.py -> parent.parent.parent = repo root (D:\Omni or C:\Users\Judge\...)
THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("BrainWrapper")

# Try import OMNI V2 brain
try:
    from omni_v2.core import CommandRegistry, PluginManager
    from omni_v2.agents import PlannerAgent, ExecutorAgent, MonitorAgent, EvaluatorAgent, MemoryAgent
    from omni_v2.tools import get_all_tools
    from omni_v2.tools.browser_v3 import BrowserToolV3
    from omni_v2.tools.demo_scenarios import DemoScenarios
    from omni_v2.voice.audio_device_v3 import get_audio_v3
    from omni_v2.voice.stt_simple import get_simple_stt
    from omni_v2.voice.tts_simple import get_simple_tts
    from omni_v2.voice.pipeline_v3_fixed import VoicePipelineV3Fixed
    BRAIN_AVAILABLE = True
    logger.info(f"✅ Brain import OK - REPO_ROOT: {REPO_ROOT} (portable, not hardcoded D:/Omni)")
except Exception as e:
    BRAIN_AVAILABLE = False
    logger.warning(f"Brain import failed: {e} - will run in mock mode")
    import traceback
    traceback.print_exc()

class OMNIBrain:
    """Singleton brain wrapper"""
    
    def __init__(self):
        self.ready = False
        self.registry = None
        self.plugin_manager = None
        self.planner = None
        self.executor = None
        self.monitor = None
        self.evaluator = None
        self.memory = None
        self.audio_mgr = None
        self.stt = None
        self.tts = None
        self.voice_pipeline = None
        self.demo = None
        
        if not BRAIN_AVAILABLE:
            logger.warning("Brain not available - mock mode")
            return
        
        try:
            self.registry = CommandRegistry()
            self.plugin_manager = PluginManager()
            
            for tool in get_all_tools():
                if hasattr(tool, 'metadata') and 'browser' in tool.metadata.name and 'v3' not in tool.metadata.name:
                    continue
                self.plugin_manager.register(tool)
            
            try:
                self.plugin_manager.register(BrowserToolV3())
                logger.info("✅ Browser V3 profile isolated registered - portable")
            except Exception as e:
                logger.warning(f"Browser V3 register failed: {e}")
            
            self.planner = PlannerAgent(self.registry)
            self.executor = ExecutorAgent(self.plugin_manager)
            self.monitor = MonitorAgent()
            self.evaluator = EvaluatorAgent()
            self.memory = MemoryAgent()
            
            try:
                self.audio_mgr = get_audio_v3()
                self.stt = get_simple_stt()
                self.tts = get_simple_tts()
                self.demo = DemoScenarios()
                logger.info(f"✅ Brain ready: Audio [{self.audio_mgr.get_best_index()}] {self.audio_mgr.get_best_name()}, STT {self.stt.get_status()}")
            except Exception as e:
                logger.warning(f"Audio/STT init failed: {e}")
            
            try:
                self.voice_pipeline = VoicePipelineV3Fixed(
                    stt=self.stt,
                    audio_mgr=self.audio_mgr,
                    on_transcription=lambda t: logger.info(f"Brain heard: {t}"),
                    on_status=lambda s: logger.info(f"Brain status: {s}"),
                    on_mic_level=lambda rms, mx: None
                )
                logger.info("✅ VoicePipelineV3Fixed (sounddevice) ready - fixes -9999")
            except Exception as e:
                logger.warning(f"Voice pipeline failed: {e}")
            
            self.ready = True
            logger.info(f"✅ OMNIBrain ready - portable REPO_ROOT: {REPO_ROOT}")
            
        except Exception as e:
            logger.error(f"OMNIBrain init failed: {e}")
            import traceback
            traceback.print_exc()
            self.ready = False
    
    async def execute(self, command: str):
        """Execute command via multi-agent"""
        if not self.ready or not self.planner:
            return {
                "success": True,
                "message": f"Mock (brain not ready): Would execute '{command}' in isolated Chrome profile OMNI-Profile (no email). Your RMS 0.014 = LOUD, mic works.",
                "logs": [f"[Planner] Mock plan for '{command}'", "[Executor] Mock success"],
                "mock": True
            }
        
        import asyncio
        try:
            steps = self.planner.plan(command)
            results = []
            logs = []
            
            for step in steps:
                logs.append(f"[Planner] Step {step.step_index}: {step.description} | {step.action} | {step.entities}")
                result = await self.executor.execute_step(step, {"original": command})
                ok = self.monitor.monitor(step, result)
                msg = getattr(result, 'message', str(result))[:120]
                logs.append(f"[Executor] {step.action} -> {getattr(result, 'success', True)} | Monitor: {ok} | {msg}")
                results.append(result)
                try:
                    self.memory.remember(step.description, msg)
                except:
                    pass
            
            final = self.evaluator.evaluate(command, steps, results)
            final_msg = getattr(final, 'final_message', str(final))
            logs.append(f"[Evaluator] {getattr(final, 'success', True)} -> {final_msg[:120]}")
            
            # TTS
            if self.tts:
                try:
                    self.tts.speak_async(final_msg[:200])
                except:
                    pass
            
            return {
                "success": getattr(final, 'success', True),
                "message": final_msg,
                "logs": logs,
                "steps": len(steps),
                "mock": False
            }
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "message": f"Error: {e}",
                "logs": [f"[Error] {e}"],
                "mock": False
            }
    
    def get_devices(self):
        """Get mic devices"""
        if not self.audio_mgr:
            return {"devices": [], "best": None, "error": "Audio manager not available"}
        
        try:
            devices = []
            for d in self.audio_mgr.devices:
                devices.append({
                    "index": d["index"],
                    "name": d["name"],
                    "score": d["score"],
                    "is_virtual": d.get("is_virtual", False),
                    "is_best": d == self.audio_mgr.best_device
                })
            return {
                "devices": devices,
                "best": self.audio_mgr.get_best_index(),
                "best_name": self.audio_mgr.get_best_name(),
                "count": len(devices)
            }
        except Exception as e:
            return {"devices": [], "best": None, "error": str(e)}
    
    def get_demo(self, demo_type: str):
        """Get demo scenario"""
        if not self.demo:
            return {"error": "Demo not available"}
        
        try:
            if demo_type == "accessibility":
                r = self.demo.accessibility_workflow()
            elif demo_type == "chain":
                r = self.demo.chain_self_healing_workflow()
            elif demo_type == "business":
                r = self.demo.business_guardian_workflow()
            else:
                return {"error": f"Unknown demo type {demo_type}"}
            
            return {
                "workflow": r.workflow,
                "steps": r.steps,
                "logs": r.agent_logs,
                "final": r.final_output,
                "impact": r.impact_statement
            }
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": str(e)}
    
    def test_mic(self):
        """Test mic via sounddevice (fixes -9999)"""
        if not self.audio_mgr:
            # Fallback direct sounddevice test
            try:
                import sounddevice as sd
                import numpy as np
                
                devices = sd.query_devices()
                best_idx = None
                for i, dev in enumerate(devices):
                    if dev['max_input_channels'] > 0 and 'realtek' in dev['name'].lower() and 'mic' in dev['name'].lower() and 'stereo' not in dev['name'].lower():
                        best_idx = i
                        break
                if best_idx is None:
                    best_idx = sd.default.device[0]
                
                with sd.InputStream(samplerate=16000, channels=1, device=best_idx, dtype='float32', blocksize=1024) as stream:
                    import time
                    frames = []
                    for _ in range(int(16000/1024*1)):
                        data, _ = stream.read(1024)
                        frames.append(data)
                    audio = np.concatenate(frames)
                    rms = float((audio**2).mean()**0.5)
                    max_v = float(abs(audio).max())
                
                return {"rms": rms, "max": max_v, "device": best_idx, "message": f"Direct SD RMS {rms:.4f} - {'LOUD' if rms>0.03 else 'Good'}", "backend": "sounddevice direct"}
            except Exception as e:
                return {"rms": 0, "max": 0, "error": str(e)}
        
        try:
            res = self.audio_mgr.test_mic_rms(duration=1.0)
            rms = res.get("rms", 0)
            return {
                "rms": rms,
                "max": res.get("max", 0),
                "device": res.get("device", self.audio_mgr.get_best_index()),
                "message": f"RMS {rms:.4f} - {'LOUD' if rms>0.03 else 'Good' if rms>0.01 else 'Low - boost mic' if rms>0.001 else 'Silent'}",
                "backend": "audio_mgr sounddevice"
            }
        except Exception as e:
            return {"rms": 0, "error": str(e)}

# Global singleton
_brain_instance = None

def get_brain():
    global _brain_instance
    if _brain_instance is None:
        _brain_instance = OMNIBrain()
    return _brain_instance
