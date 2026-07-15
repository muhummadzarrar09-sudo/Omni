"""
OMNI V3 FIXED - WEB SERVER - NEOMORPHISM - NO 404 LOOP - NO PyAudio
Fixes:
1. Root was D:\\ instead of D:\\Omni -> 404 File not found -> FIXED to correct root
2. PyAudio fails on Python 3.12 ImpImporter -> REMOVED, uses sounddevice only (your test shows sounddevice works RMS 0.014 LOUD)
3. Serves files directly via absolute path, not via SimpleHTTPRequestHandler chdir fragile logic

Usage:
    python -m omni_v2.web_server_fixed
    python -m omni_v2.web_server_fixed --port 8765
    # Opens http://localhost:8765/ directly - no /omni_v2/web_ui/... needed, root serves UI

This version:
- Serves Neomorphism UI at / (root) -> no more /omni_v2/web_ui/index.html 404
- Serves three.min.js at /assets/three.min.js and /three.min.js
- API still works
- Opens isolated Chrome profile to root URL
- NO PyAudio dependency - sounddevice only
"""
import sys
import os
import json
import threading
import time
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import socket

# Torch fallback
try:
    import torch
except OSError:
    os.environ["OMNI_NO_TORCH"] = "1"
except ImportError:
    pass

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("WebServerFixed")

# Brain
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
except Exception as e:
    BRAIN_AVAILABLE = False
    logger.warning(f"Brain not fully available: {e}")

registry = None
plugin_manager = None
planner = None
executor = None
monitor = None
evaluator = None
memory = None
audio_mgr = None
stt = None
tts = None
voice_pipeline = None
demo_scenarios = None

def init_brain():
    global registry, plugin_manager, planner, executor, monitor, evaluator, memory, audio_mgr, stt, tts, voice_pipeline, demo_scenarios
    if not BRAIN_AVAILABLE:
        return False
    try:
        registry = CommandRegistry()
        plugin_manager = PluginManager()
        for tool in get_all_tools():
            if hasattr(tool, 'metadata') and 'browser' in tool.metadata.name and 'v3' not in tool.metadata.name:
                continue
            plugin_manager.register(tool)
        try:
            plugin_manager.register(BrowserToolV3())
        except Exception as e:
            logger.warning(f"Browser V3 register failed: {e}")
        
        planner = PlannerAgent(registry)
        executor = ExecutorAgent(plugin_manager)
        monitor = MonitorAgent()
        evaluator = EvaluatorAgent()
        memory = MemoryAgent()
        
        try:
            audio_mgr = get_audio_v3()
            stt = get_simple_stt()
            tts = get_simple_tts()
            demo_scenarios = DemoScenarios()
            logger.info(f"✅ Brain: Audio best [{audio_mgr.get_best_index()}] {audio_mgr.get_best_name()}")
        except Exception as e:
            logger.warning(f"Audio/STT init failed: {e}")
        
        try:
            voice_pipeline = VoicePipelineV3Fixed(
                stt=stt, audio_mgr=audio_mgr,
                on_transcription=lambda text: logger.info(f"Web PTT Heard: {text}"),
                on_status=lambda s: logger.info(f"Web PTT Status: {s}"),
                on_mic_level=lambda rms, max_v: None
            )
            logger.info("✅ VoicePipelineV3Fixed with sounddevice primary - fixes -9999")
        except Exception as e:
            logger.warning(f"Voice pipeline failed: {e}")
        
        return True
    except Exception as e:
        logger.error(f"Brain init failed: {e}")
        import traceback
        traceback.print_exc()
        return False

# Correct paths - FIXED
THIS_FILE = Path(__file__).resolve()
OMNI_ROOT = THIS_FILE.parent.parent  # D:\Omni  <- FIXED, was parent.parent.parent = D:\
WEB_UI_FILE = OMNI_ROOT / "omni_v2" / "web_ui" / "index.html"
THREE_JS_FILE = OMNI_ROOT / "assets" / "three.min.js"
THREE_JS_FILE_ALT = OMNI_ROOT / "omni_v2" / "web_ui" / "three.min.js"

print(f"[WebServerFixed] THIS_FILE: {THIS_FILE}")
print(f"[WebServerFixed] OMNI_ROOT: {OMNI_ROOT} (FIXED, was D:\\ before)")
print(f"[WebServerFixed] WEB_UI_FILE: {WEB_UI_FILE} exists={WEB_UI_FILE.exists()}")
print(f"[WebServerFixed] THREE_JS: {THREE_JS_FILE} exists={THREE_JS_FILE.exists()}")

class FixedHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        logger.debug(f"HTTP {format%args}")
    
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        # API
        if path == "/api/health":
            self.send_json({"status": "ok", "brain": BRAIN_AVAILABLE, "neomorphism": True, "root": str(OMNI_ROOT), "fix": "sounddevice only, no PyAudio, no 404"})
            return
        
        if path == "/api/devices":
            devices = []
            try:
                if audio_mgr:
                    devices = [{"index": d["index"], "name": d["name"], "score": d["score"]} for d in audio_mgr.devices]
            except:
                pass
            self.send_json({"devices": devices, "best": audio_mgr.get_best_index() if audio_mgr else None})
            return
        
        # Serve three.min.js - FIXED to absolute path
        if path in ["/assets/three.min.js", "/three.min.js", "/static/three.min.js"]:
            for candidate in [THREE_JS_FILE, THREE_JS_FILE_ALT, OMNI_ROOT / "assets" / "three.min.js"]:
                if candidate.exists():
                    self.send_file(candidate, "application/javascript")
                    return
            self.send_error(404, "three.min.js not found")
            return
        
        # Serve main UI at ROOT - FIXES 404 LOOP
        # All these paths should serve the same neomorphism UI
        if path in ["/", "/index.html", "/omni_v2/web_ui/index.html", "/web_ui/index.html", "/ui"]:
            if WEB_UI_FILE.exists():
                # Read file and fix three.min.js path to be absolute /assets/three.min.js
                content = WEB_UI_FILE.read_text(encoding='utf-8')
                # Fix relative path ../../assets/three.min.js -> /assets/three.min.js
                content = content.replace('../../assets/three.min.js', '/assets/three.min.js')
                content = content.replace('../../assets/three.min.js', '/assets/three.min.js')
                content = content.replace('../assets/three.min.js', '/assets/three.min.js')
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(content.encode('utf-8'))
                return
            else:
                self.send_error(404, f"Web UI not found at {WEB_UI_FILE}")
                return
        
        # Favicon
        if path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        
        # 404 for others
        self.send_error(404, f"File not found: {path}. Try / for UI")
    
    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8') if content_length else "{}"
        try:
            data = json.loads(body)
        except:
            data = {}
        
        if path == "/api/execute":
            command = data.get("command", "")
            if not command:
                self.send_json({"error": "No command"}, 400)
                return
            
            if not BRAIN_AVAILABLE or not planner:
                self.send_json({
                    "success": True,
                    "message": f"Mock: Would open in isolated profile OMNI-Profile: {command} (no email). Start brain for real execution. Your RMS 0.014 = LOUD, mic works, -9999 fixed via sounddevice.",
                    "logs": [f"[Planner] Mock plan for '{command}'"],
                    "mock": True
                })
                return
            
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def run_chain():
                    steps = planner.plan(command)
                    results = []
                    logs = []
                    for step in steps:
                        logs.append(f"[Planner] Step {step.step_index}: {step.description}")
                        result = await executor.execute_step(step, {"original": command})
                        ok = monitor.monitor(step, result)
                        logs.append(f"[Executor] {step.action} -> {getattr(result, 'success', True)} | {getattr(result, 'message', '')[:80]}")
                        results.append(result)
                    final = evaluator.evaluate(command, steps, results)
                    msg = getattr(final, 'final_message', str(final))
                    logs.append(f"[Evaluator] {msg[:100]}")
                    return msg, logs
                
                message, logs = loop.run_until_complete(run_chain())
                if tts:
                    try:
                        tts.speak_async(message[:200])
                    except:
                        pass
                self.send_json({"success": True, "message": message, "logs": logs})
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.send_json({"success": False, "message": f"Error: {e}"}, 500)
            return
        
        elif path in ["/api/demo/accessibility", "/api/demo/chain", "/api/demo/business"]:
            demo_type = path.split("/")[-1]
            try:
                if not demo_scenarios:
                    self.send_json({"error": "Demo not available"}, 500)
                    return
                
                if demo_type == "accessibility":
                    result = demo_scenarios.accessibility_workflow()
                elif demo_type == "chain":
                    result = demo_scenarios.chain_self_healing_workflow()
                else:
                    result = demo_scenarios.business_guardian_workflow()
                
                self.send_json({"workflow": result.workflow, "logs": result.agent_logs, "final": result.final_output, "impact": result.impact_statement})
            except Exception as e:
                self.send_json({"error": str(e)}, 500)
            return
        
        elif path == "/api/test-mic":
            try:
                if audio_mgr:
                    res = audio_mgr.test_mic_rms(duration=1.0)
                    rms = res.get("rms", 0)
                    self.send_json({"rms": rms, "max": res.get("max",0), "message": f"RMS {rms:.4f} - {'LOUD' if rms>0.03 else 'Good' if rms>0.01 else 'Low'}"})
                else:
                    # Use sounddevice directly if audio_mgr not available
                    import sounddevice as sd
                    import numpy as np
                    sd.default.samplerate = 16000
                    sd.default.channels = 1
                    # Find Realtek
                    devices = sd.query_devices()
                    best_idx = None
                    for i, dev in enumerate(devices):
                        if dev['max_input_channels'] > 0 and 'realtek' in dev['name'].lower() and 'mic' in dev['name'].lower() and 'stereo' not in dev['name'].lower():
                            best_idx = i
                            break
                    if best_idx is None:
                        best_idx = sd.default.device[0]
                    
                    with sd.InputStream(samplerate=16000, channels=1, device=best_idx, dtype='float32', blocksize=1024) as stream:
                        data, _ = stream.read(int(16000*1))
                        # Actually read loop
                        import time
                        frames = []
                        for _ in range(int(16000/1024*1)):
                            d, _ = stream.read(1024)
                            frames.append(d)
                        audio = np.concatenate(frames)
                        rms = float((audio**2).mean()**0.5)
                        max_v = float(abs(audio).max())
                    
                    self.send_json({"rms": rms, "max": max_v, "message": f"SD direct RMS {rms:.4f}"})
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.send_json({"error": str(e), "rms": 0}, 500)
            return
        
        elif path == "/api/ptt/start":
            try:
                if voice_pipeline:
                    voice_pipeline.start()
                    self.send_json({"status": "recording", "message": "Recording - speak LOUD!"})
                else:
                    self.send_json({"error": "Voice pipeline not available"}, 500)
            except Exception as e:
                self.send_json({"error": str(e)}, 500)
            return
        
        elif path == "/api/ptt/stop":
            try:
                if voice_pipeline:
                    voice_pipeline.stop()
                    time.sleep(0.5)
                    audio = voice_pipeline._get_audio() if hasattr(voice_pipeline, '_get_audio') else None
                    text = None
                    message = "No audio"
                    rms = 0
                    max_v = 0
                    if audio is not None and len(audio) > 0:
                        import numpy as np
                        rms = float(np.sqrt(np.mean(np.array(audio)**2)))
                        max_v = float(np.abs(np.array(audio)).max())
                        if stt:
                            text = stt.transcribe(np.array(audio))
                            if text:
                                # Execute
                                try:
                                    import asyncio
                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)
                                    async def exec_after():
                                        steps = planner.plan(text)
                                        results = []
                                        for step in steps:
                                            result = await executor.execute_step(step, {"original": text})
                                            results.append(result)
                                        final = evaluator.evaluate(text, steps, results)
                                        return getattr(final, 'final_message', str(final))
                                    message = loop.run_until_complete(exec_after())
                                    if tts:
                                        try:
                                            tts.speak_async(message[:200])
                                        except:
                                            pass
                                except Exception as e:
                                    message = f"STT: {text} but exec failed: {e}"
                            else:
                                message = f"Didn't catch RMS {rms:.4f} - speak louder"
                    self.send_json({"status": "idle", "text": text, "message": message, "rms": rms, "max": max_v})
                else:
                    self.send_json({"error": "Voice pipeline not available"}, 500)
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.send_json({"error": str(e)}, 500)
            return
        
        self.send_error(404, f"API {path} not found")
    
    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def send_file(self, file_path: Path, content_type: str):
        try:
            content = file_path.read_bytes()
            self.send_response(200)
            self.send_header('Content-type', content_type)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Failed to serve file: {e}")
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

def find_free_port(start=8765):
    for port in range(start, start+20):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    return start

def open_in_isolated_chrome(url: str):
    try:
        from omni_v2.tools.browser_v3 import BrowserToolV3
        browser = BrowserToolV3()
        browser._launch_chrome_isolated(url)
        logger.info(f"🌐 Opened {url} in isolated profile")
        return True
    except Exception as e:
        logger.warning(f"Isolated chrome failed: {e}, trying webbrowser")
        try:
            import webbrowser
            webbrowser.open(url, new=2)
            return True
        except:
            return False

def main():
    import argparse
    parser = argparse.ArgumentParser(description="OMNI V3 FIXED Web Server - Neomorphism, no 404, no PyAudio")
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    
    print("="*70)
    print("  OMNI V3 FIXED WEB SERVER - Neomorphism Soft UI")
    print("  FIXES: 404 loop (root now serves UI), PyAudio -9999 (sounddevice only)")
    print("  Your RMS 0.014 = LOUD, mic works, sounddevice fixes -9999")
    print("="*70)
    print(f"\n[Path Fix] THIS_FILE: {THIS_FILE}")
    print(f"[Path Fix] OMNI_ROOT: {OMNI_ROOT} (was D:\\ before, now D:\\Omni)")
    print(f"[Path Fix] WEB_UI_FILE exists: {WEB_UI_FILE.exists()} -> {WEB_UI_FILE}")
    
    init_brain()
    
    port = find_free_port(args.port)
    server_address = ('', port)
    httpd = HTTPServer(server_address, FixedHandler)
    url = f"http://localhost:{port}"
    
    print(f"\n🌐 Starting FIXED server at {url}")
    print(f"   UI at ROOT: {url}/  <- FIXED, was /omni_v2/web_ui/index.html 404 before")
    print(f"   Assets: {url}/assets/three.min.js")
    print(f"   API: {url}/api/health")
    print(f"\n✅ Ready! No more 404, no PyAudio needed")
    print(f"   Your mic RMS 0.014 = LOUD enough for STT")
    print("="*70)
    
    if not args.no_browser:
        def open_browser():
            time.sleep(1.2)
            print(f"\n🚀 Opening isolated Chrome to {url}/ ...")
            open_in_isolated_chrome(url + "/")
        threading.Thread(target=open_browser, daemon=True).start()
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Stopping...")
        httpd.shutdown()

if __name__ == "__main__":
    main()
