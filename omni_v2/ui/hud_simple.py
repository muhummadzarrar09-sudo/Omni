"""
OMNI V3 - HUD SIMPLE - ONE UI THAT WORKS, NO TAURI BS
Single PyQt5 window, orb fallback if Three.js fails, mic bar, device selector, 3 demo buttons
"""
import os
import sys
from pathlib import Path

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("HUDSimpleV3")

try:
    from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                                 QComboBox, QProgressBar, QTextEdit, QApplication, QFrame,
                                 QGraphicsDropShadowEffect)
    from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize, QUrl
    from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QLinearGradient, QRadialGradient
    try:
        from PyQt5.QtWebEngineWidgets import QWebEngineView
        WEBENGINE_AVAILABLE = True
    except ImportError:
        WEBENGINE_AVAILABLE = False
        logger.warning("QWebEngineView not available - using fallback orb")
    PYQT_AVAILABLE = True
except ImportError as e:
    PYQT_AVAILABLE = False
    logger.error(f"PyQt5 not available: {e}")
    WEBENGINE_AVAILABLE = False

if PYQT_AVAILABLE:
    class OrbFallback(QWidget):
        """Fallback orb if Three.js fails - simple pulsing radial gradient 120px"""
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setFixedSize(140, 140)
            self.state = "idle"  # idle, listening, thinking, speaking, error
            self.glow = 0.0
            self.dir = 1
            self.timer = QTimer(self)
            self.timer.timeout.connect(self._anim)
            self.timer.start(30)
        
        def set_state(self, state: str):
            self.state = state
            logger.info(f"Orb state: {state}")
            self.update()
        
        def _anim(self):
            self.glow += 0.03 * self.dir
            if self.glow > 1.0 or self.glow < 0.0:
                self.dir *= -1
            self.update()
        
        def paintEvent(self, event):
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            cx, cy = self.width()//2, self.height()//2
            
            colors = {
                "idle": (QColor(0, 200, 255), 0.001),
                "listening": (QColor(0, 255, 136), 0.01),
                "thinking": (QColor(255, 136, 0), 0.02),
                "speaking": (QColor(255, 255, 255), 0.005),
                "error": (QColor(255, 0, 68), 0.03)
            }
            col, speed = colors.get(self.state, colors["idle"])
            
            # Outer glow
            for i in range(10):
                alpha = int(80 * (1 - i/10) * (0.5 + self.glow*0.5))
                c = QColor(col)
                c.setAlpha(alpha)
                painter.setPen(QPen(c, 2))
                r = 50 + i*3 + self.glow*10
                painter.drawEllipse(int(cx-r), int(cy-r), int(r*2), int(r*2))
            
            # Core gradient
            grad = QRadialGradient(cx, cy, 40)
            grad.setColorAt(0, QColor(255, 255, 255, 200))
            grad.setColorAt(0.3, col)
            grad.setColorAt(1, QColor(col.red()//2, col.green()//2, col.blue()//2, 255))
            painter.setBrush(grad)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(int(cx-40), int(cy-40), 80, 80)
            
            # Text
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Consolas", 10, QFont.Bold))
            painter.drawText(self.rect(), Qt.AlignCenter, f"OMNI\n{self.state.upper()}")
    
    class HUDSimpleV3(QWidget):
        """Single HUD that works - mic selector, mic bar, 3 demo buttons, transcription"""
        
        # Signals for thread-safe updates
        transcription_signal = pyqtSignal(str)
        state_signal = pyqtSignal(str)
        mic_level_signal = pyqtSignal(float, float)  # rms, max
        
        def __init__(self, app_instance=None):
            super().__init__()
            self.app_instance = app_instance
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
            self.setAttribute(Qt.WA_TranslucentBackground)
            self.setGeometry(100, 100, 420, 680)
            self.setWindowTitle("OMNI V3 - Your Voice is Enough")
            
            self._dragging = False
            self._drag_pos = None
            self._transcription = "Say 'Hey OMNI' or Press V — Your Voice is Enough"
            self._mic_rms = 0.0
            self._mic_max = 0.0
            
            self._init_ui()
            self._connect_signals()
            
            # Mic level timer for waveform
            self.waveform_data = [0]*20
            self.mic_timer = QTimer(self)
            self.mic_timer.timeout.connect(self._update_waveform)
            self.mic_timer.start(100)
            
            logger.info("HUDSimpleV3 - Single UI, no Tauri, works")
        
        def _init_ui(self):
            layout = QVBoxLayout(self)
            layout.setContentsMargins(20, 20, 20, 20)
            layout.setSpacing(10)
            
            # Main card
            card = QFrame()
            card.setStyleSheet("""
                QFrame {
                    background: rgba(15, 25, 40, 240);
                    border-radius: 24px;
                    border: 1px solid rgba(0, 200, 255, 60);
                }
            """)
            # Shadow
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(30)
            shadow.setColor(QColor(0, 200, 255, 80))
            shadow.setOffset(0, 10)
            card.setGraphicsEffect(shadow)
            
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(20, 20, 20, 20)
            card_layout.setSpacing(12)
            
            # Title
            title = QLabel("OMNI V3 — Offline Agent")
            title.setStyleSheet("color: #00ccff; font-family: Consolas; font-size: 14px; font-weight: bold; background: transparent; border: none;")
            title.setAlignment(Qt.AlignCenter)
            card_layout.addWidget(title)
            
            subtitle = QLabel("GTX 1050 Ti Optimized | Privacy-First | Accessibility")
            subtitle.setStyleSheet("color: #88aabb; font-family: Consolas; font-size: 9px; background: transparent; border: none;")
            subtitle.setAlignment(Qt.AlignCenter)
            card_layout.addWidget(subtitle)
            
            # Orb area
            self.orb_area = QFrame()
            self.orb_area.setStyleSheet("background: transparent; border: none;")
            orb_layout = QVBoxLayout(self.orb_area)
            orb_layout.setAlignment(Qt.AlignCenter)
            
            # Try Three.js orb, fallback to simple
            self.orb = None
            self.webview = None
            if WEBENGINE_AVAILABLE:
                try:
                    # Fix absolute path for three.min.js
                    assets_path = Path(__file__).parent.parent.parent / "assets" / "three.min.js"
                    # Also try frontend path
                    if not assets_path.exists():
                        assets_path = Path.cwd() / "assets" / "three.min.js"
                    
                    if assets_path.exists():
                        self.webview = QWebEngineView()
                        self.webview.setFixedSize(200, 200)
                        self.webview.setStyleSheet("background: transparent; border: none;")
                        # Load orb html with absolute path fix
                        orb_html_path = Path(__file__).parent / "orb_threejs.html"
                        if orb_html_path.exists():
                            # Inject absolute path for three.js
                            html = orb_html_path.read_text()
                            # Replace relative with absolute file://
                            abs_three = assets_path.absolute().as_uri()
                            html = html.replace("../../assets/three.min.js", abs_three)
                            html = html.replace("../../assets/three.min.js", abs_three)
                            # Write temp fixed
                            temp_html = Path.cwd() / "data" / "orb_fixed.html"
                            temp_html.parent.mkdir(exist_ok=True)
                            temp_html.write_text(html)
                            self.webview.load(QUrl.fromLocalFile(str(temp_html.absolute())))
                            logger.info(f"Three.js orb loading with absolute path: {abs_three}")
                        else:
                            # Simple html with three.js
                            simple_html = f"""
                            <html><body style="margin:0;background:transparent;overflow:hidden;">
                            <script src="{assets_path.absolute().as_uri()}"></script>
                            <script>
                            let scene, camera, renderer, particles;
                            init();
                            function init() {{
                                scene = new THREE.Scene();
                                camera = new THREE.PerspectiveCamera(75, 300/300, 0.1, 1000);
                                camera.position.z = 5;
                                renderer = new THREE.WebGLRenderer({{alpha:true, antialias:true}});
                                renderer.setSize(200,200);
                                renderer.setClearColor(0x000000,0);
                                document.body.appendChild(renderer.domElement);
                                const g = new THREE.BufferGeometry();
                                const pos=[]; for(let i=0;i<800;i++){{const t=Math.random()*Math.PI*2; const p=Math.acos(2*Math.random()-1); const r=2+Math.random()*0.5; pos.push(r*Math.sin(p)*Math.cos(t), r*Math.sin(p)*Math.sin(t), r*Math.cos(p));}} g.setAttribute('position', new THREE.Float32BufferAttribute(pos,3)); const m=new THREE.PointsMaterial({{size:0.06, color:0x00ccff, transparent:true, opacity:0.8}}); particles=new THREE.Points(g,m); scene.add(particles); animate();
                            }}
                            function animate(){{requestAnimationFrame(animate); if(particles) particles.rotation.y+=0.005; renderer.render(scene,camera);}}
                            </script>
                            </body></html>
                            """
                            self.webview.setHtml(simple_html)
                        orb_layout.addWidget(self.webview)
                        self.orb = OrbFallback()  # Keep fallback for state
                        logger.info("WebEngine Three.js orb attempted")
                    else:
                        raise FileNotFoundError(f"three.min.js not found at {assets_path}")
                except Exception as e:
                    logger.warning(f"Three.js orb failed {e}, using fallback")
                    self.webview = None
            
            if self.webview is None:
                # Fallback orb
                self.orb = OrbFallback()
                orb_layout.addWidget(self.orb, alignment=Qt.AlignCenter)
                logger.info("Using fallback orb 120px pulsing")
            else:
                # If webview success, also keep fallback hidden for state logic
                if self.orb is None:
                    self.orb = OrbFallback()
                # Don't add fallback to layout if webview works, but keep for logic
            
            card_layout.addWidget(self.orb_area)
            
            # Mic level bar + device selector
            mic_row = QHBoxLayout()
            mic_label = QLabel("Mic:")
            mic_label.setStyleSheet("color: #aaccaa; font-family: Consolas; font-size: 10px; background: transparent; border: none;")
            mic_row.addWidget(mic_label)
            
            self.device_combo = QComboBox()
            self.device_combo.setStyleSheet("""
                QComboBox { background: rgba(0, 200, 255, 20); color: #ccffff; border: 1px solid rgba(0,200,255,40); border-radius: 8px; padding: 4px; font-family: Consolas; font-size: 9px; }
                QComboBox QAbstractItemView { background: #0f1928; color: #ccffff; selection-background-color: rgba(0,200,255,40); }
            """)
            self.device_combo.setMinimumWidth(180)
            mic_row.addWidget(self.device_combo)
            
            card_layout.addLayout(mic_row)
            
            # Mic level progress bar
            self.mic_bar = QProgressBar()
            self.mic_bar.setRange(0, 100)
            self.mic_bar.setValue(0)
            self.mic_bar.setTextVisible(True)
            self.mic_bar.setFormat("RMS: %v% — Speak LOUD 1 inch!")
            self.mic_bar.setStyleSheet("""
                QProgressBar { background: rgba(0,0,0,100); border: 1px solid rgba(0,200,255,30); border-radius: 8px; text-align: center; color: #88cc88; font-family: Consolas; font-size: 9px; }
                QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #00ff88, stop:1 #00ccff); border-radius: 8px; }
            """)
            card_layout.addWidget(self.mic_bar)
            
            # Waveform simple (20 bars)
            self.waveform_label = QLabel(" waveform will appear when speaking ")
            self.waveform_label.setStyleSheet("color: #00ff88; font-family: Consolas; font-size: 14px; background: transparent; border: none; letter-spacing: 2px;")
            self.waveform_label.setAlignment(Qt.AlignCenter)
            card_layout.addWidget(self.waveform_label)
            
            # Transcription
            self.trans_label = QLabel(self._transcription)
            self.trans_label.setWordWrap(True)
            self.trans_label.setStyleSheet("color: #ffffff; font-family: Consolas; font-size: 11px; background: rgba(0,0,0,80); border-radius: 12px; padding: 12px; border: none;")
            self.trans_label.setAlignment(Qt.AlignCenter)
            self.trans_label.setMinimumHeight(70)
            card_layout.addWidget(self.trans_label)
            
            # Demo buttons - 3 killer workflows (no STT needed for video)
            demo_label = QLabel("🎯 1-Click Demo (No Mic Needed) — For Video")
            demo_label.setStyleSheet("color: #ffaa00; font-family: Consolas; font-size: 9px; font-weight: bold; background: transparent; border: none;")
            card_layout.addWidget(demo_label)
            
            btn_style = """
                QPushButton { background: rgba(0,200,255,30); color: #ffffff; border: 1px solid rgba(0,200,255,80); border-radius: 10px; padding: 8px; font-family: Consolas; font-size: 10px; font-weight: bold; }
                QPushButton:hover { background: rgba(0,200,255,60); border: 1px solid #00ccff; }
                QPushButton:pressed { background: rgba(0,200,255,90); }
            """
            
            self.btn_access = QPushButton("♿ Accessibility Demo")
            self.btn_access.setStyleSheet(btn_style)
            self.btn_access.clicked.connect(self._demo_accessibility)
            
            self.btn_chain = QPushButton("🔗 Chain + Self-Heal Demo")
            self.btn_chain.setStyleSheet(btn_style)
            self.btn_chain.clicked.connect(self._demo_chain)
            
            self.btn_business = QPushButton("🏪 Shop Guardian Demo")
            self.btn_business.setStyleSheet(btn_style)
            self.btn_business.clicked.connect(self._demo_business)
            
            card_layout.addWidget(self.btn_access)
            card_layout.addWidget(self.btn_chain)
            card_layout.addWidget(self.btn_business)
            
            # Control buttons
            ctrl_row = QHBoxLayout()
            self.btn_close = QPushButton("✕ Close")
            self.btn_close.setStyleSheet("QPushButton { background: rgba(255,0,68,20); color: #ffaaaa; border: 1px solid rgba(255,0,68,40); border-radius: 8px; padding: 6px; font-family: Consolas; font-size: 9px; } QPushButton:hover { background: rgba(255,0,68,40); }")
            self.btn_close.clicked.connect(self.close)
            
            self.btn_test = QPushButton("🧪 Test Mic Level")
            self.btn_test.setStyleSheet("QPushButton { background: rgba(0,255,136,20); color: #aaffaa; border: 1px solid rgba(0,255,136,40); border-radius: 8px; padding: 6px; font-family: Consolas; font-size: 9px; } QPushButton:hover { background: rgba(0,255,136,40); }")
            self.btn_test.clicked.connect(self._test_mic)
            
            ctrl_row.addWidget(self.btn_test)
            ctrl_row.addWidget(self.btn_close)
            card_layout.addLayout(ctrl_row)
            
            # Status
            self.status_label = QLabel("V3 Ready | Press V to speak LOUD 1 inch")
            self.status_label.setStyleSheet("color: #6699aa; font-family: Consolas; font-size: 8px; background: transparent; border: none;")
            self.status_label.setAlignment(Qt.AlignCenter)
            card_layout.addWidget(self.status_label)
            
            layout.addWidget(card)
        
        def _connect_signals(self):
            self.transcription_signal.connect(self.set_transcription)
            self.state_signal.connect(self.set_state)
            self.mic_level_signal.connect(self.set_mic_level)
        
        def set_transcription(self, text: str):
            # Thread-safe via signal if needed
            if QTimer.singleShot:
                try:
                    self._transcription = text
                    self.trans_label.setText(text)
                    logger.info(f"HUD transcription: {text[:100]}")
                except Exception as e:
                    logger.warning(f"set_transcription failed: {e}")
        
        def set_state(self, state: str):
            try:
                if self.orb:
                    self.orb.set_state(state)
                # Update webview orb color via JS if available
                if self.webview:
                    color_map = {
                        "idle": "0x00ccff",
                        "listening": "0x00ff88",
                        "thinking": "0xff8800",
                        "speaking": "0xffffff",
                        "error": "0xff0044"
                    }
                    col = color_map.get(state, "0x00ccff")
                    try:
                        self.webview.page().runJavaScript(f"if(typeof particles!== 'undefined' && particles.material) particles.material.color.setHex({col});")
                    except Exception:
                        pass
            except Exception as e:
                logger.warning(f"set_state failed: {e}")
        
        def set_mic_level(self, rms: float, max_val: float):
            try:
                self._mic_rms = rms
                self._mic_max = max_val
                # 0 - 0.1 rms -> 0-100%
                pct = int(min(100, (rms / 0.05) * 100))
                self.mic_bar.setValue(pct)
                
                if rms < 0.001:
                    self.mic_bar.setFormat("🔇 Silent - Boost mic 100%+30dB")
                elif rms < 0.01:
                    self.mic_bar.setFormat(f"🔈 Low RMS {rms:.4f} — Speak LOUDER")
                elif rms < 0.03:
                    self.mic_bar.setFormat(f"🔉 Good RMS {rms:.4f} — Keep speaking")
                else:
                    self.mic_bar.setFormat(f"🔊 LOUD RMS {rms:.4f} — Excellent!")
                
                # Update waveform data
                self.waveform_data.append(rms)
                if len(self.waveform_data) > 20:
                    self.waveform_data.pop(0)
            except Exception as e:
                logger.warning(f"set_mic_level failed: {e}")
        
        def _update_waveform(self):
            try:
                # Simple waveform visualization with bars
                bars = [" ", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
                wave_str = ""
                for rms in self.waveform_data[-20:]:
                    idx = int(min(8, (rms / 0.04) * 8))
                    wave_str += bars[idx]
                self.waveform_label.setText(wave_str)
            except Exception:
                pass
        
        def _demo_accessibility(self):
            try:
                from omni_v2.tools.demo_scenarios import DemoScenarios
                demo = DemoScenarios()
                result = demo.accessibility_workflow()
                text = f"♿ {result.workflow}\n\n" + "\n".join(result.agent_logs[:5]) + f"\n\n→ {result.final_output}\n\n{result.impact_statement}"
                self.set_transcription(text)
                self.set_state("speaking")
                QTimer.singleShot(3000, lambda: self.set_state("idle"))
                # TTS
                try:
                    from omni_v2.voice.tts_simple import get_simple_tts
                    get_simple_tts().speak_async(result.final_output[:200])
                except Exception as e:
                    logger.warning(f"TTS demo failed: {e}")
            except Exception as e:
                self.set_transcription(f"Demo failed: {e}\nTry python omni.py --cli")
        
        def _demo_chain(self):
            try:
                from omni_v2.tools.demo_scenarios import DemoScenarios
                demo = DemoScenarios()
                result = demo.chain_self_healing_workflow()
                text = f"🔗 {result.workflow}\n\n" + "\n".join(result.agent_logs[:7]) + f"\n\n→ {result.final_output}"
                self.set_transcription(text)
                self.set_state("thinking")
                QTimer.singleShot(1500, lambda: self.set_state("speaking"))
                QTimer.singleShot(3500, lambda: self.set_state("idle"))
                try:
                    from omni_v2.voice.tts_simple import get_simple_tts
                    get_simple_tts().speak_async("Chain self-healing demo — Chrome not found, auto fallback to Edge — true agentic")
                except Exception:
                    pass
            except Exception as e:
                self.set_transcription(f"Demo failed: {e}")
        
        def _demo_business(self):
            try:
                from omni_v2.tools.demo_scenarios import DemoScenarios
                demo = DemoScenarios()
                result = demo.business_guardian_workflow()
                text = f"🏪 {result.workflow}\n\n" + "\n".join(result.agent_logs[:6]) + f"\n\n→ {result.final_output}\n\n{result.impact_statement}"
                self.set_transcription(text)
                self.set_state("speaking")
                QTimer.singleShot(3000, lambda: self.set_state("idle"))
            except Exception as e:
                self.set_transcription(f"Demo failed: {e}")
        
        def _test_mic(self):
            try:
                self.set_transcription("🧪 Testing mic RMS for 2 seconds — Speak LOUD now!")
                self.set_state("listening")
                from omni_v2.voice.audio_device_v3 import get_audio_v3
                audio_mgr = get_audio_v3()
                combo_text = self.device_combo.currentText()
                idx = audio_mgr.get_index_from_combo_text(combo_text)
                
                import threading
                def test_thread():
                    import time
                    for i in range(20):
                        res = audio_mgr.test_mic_rms(device_index=idx, duration=0.2)
                        rms = res.get('rms', 0)
                        max_v = res.get('max', 0)
                        self.mic_level_signal.emit(rms, max_v)
                        time.sleep(0.1)
                    self.state_signal.emit("idle")
                    self.transcription_signal.emit(f"Mic test done! Best RMS was {self._mic_rms:.4f}. If <0.01, boost Windows Sound Settings -> Input 100% + Boost +30dB, speak 1 inch close!")
                
                threading.Thread(target=test_thread, daemon=True).start()
                
            except Exception as e:
                self.set_transcription(f"Mic test failed: {e}")
        
        def load_devices(self, devices: list):
            try:
                self.device_combo.clear()
                self.device_combo.addItems(devices)
            except Exception as e:
                logger.warning(f"load_devices failed: {e}")
        
        def mousePressEvent(self, event):
            if event.button() == Qt.LeftButton:
                self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
                self._dragging = True
        
        def mouseMoveEvent(self, event):
            if hasattr(self, '_dragging') and self._dragging:
                self.move(event.globalPos() - self._drag_pos)
        
        def mouseReleaseEvent(self, event):
            self._dragging = False

else:
    class HUDSimpleV3:
        def __init__(self, *a, **k):
            print("PyQt5 not available - HUDSimpleV3 dummy")
        def set_transcription(self, *a, **k): pass
        def set_state(self, *a, **k): pass
        def set_mic_level(self, *a, **k): pass
        def load_devices(self, *a, **k): pass
        def show(self): pass
