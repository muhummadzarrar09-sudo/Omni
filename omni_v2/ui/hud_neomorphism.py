"""
OMNI V3 - NEOMORPHISM HUD - Soft UI, Extruded, Inset Press, Dark Mode
Replaces horse shit glassmorphic with soft neumorphic that actually looks premium.

Neomorphism Principles:
- Same background as parent: #232933 / #1E222D
- Two shadows: Dark (8,8) rgba(0,0,0,0.55) + Light (-8,-8) rgba(255,255,255,0.06)
- Extruded: shadows outside, main same color as bg
- Pressed/Inset: shadows inside, reversed
- All corners 20px, orb 100% circle
- No neon cyan borders - soft, not gamer

Designed for hackathon judges - looks expensive, feels tactile.
"""
import os
from pathlib import Path

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("HUDNeumorphismV3")

try:
    from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                                 QComboBox, QProgressBar, QFrame, QApplication, QGraphicsDropShadowEffect)
    from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QRectF, QPropertyAnimation, QEasingCurve, pyqtProperty
    from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QPainterPath, QLinearGradient, QRadialGradient, QFontDatabase
    try:
        from PyQt5.QtWebEngineWidgets import QWebEngineView
        WEBENGINE_AVAILABLE = True
    except ImportError:
        WEBENGINE_AVAILABLE = False
    PYQT_AVAILABLE = True
except ImportError as e:
    PYQT_AVAILABLE = False
    WEBENGINE_AVAILABLE = False

if PYQT_AVAILABLE:
    
    # === COLORS - Dark Neomorphism ===
    BG = QColor("#1E222D")        # main bg
    CARD_BG = QColor("#232933")   # card same as bg but slight
    CARD_BG_LIGHT = QColor("#2A313F")
    SHADOW_DARK = QColor(0, 0, 0, 110)      # dark shadow
    SHADOW_LIGHT = QColor(255, 255, 255, 14) # light shadow soft
    SHADOW_DARK_STRONG = QColor(0, 0, 0, 150)
    TEXT_PRIMARY = QColor("#E2E8F0")
    TEXT_SECONDARY = QColor("#A0AEC0")
    TEXT_ACCENT = QColor("#7DD3FC")
    ACCENT = QColor("#38BDF8")
    ACCENT_GREEN = QColor("#4ADE80")
    ACCENT_ORANGE = QColor("#FB923C")
    ACCENT_RED = QColor("#F87171")
    
    class NeumorphicCard(QFrame):
        """Basic neumorphic card - extruded soft, double shadow painted manual"""
        def __init__(self, parent=None, radius=22, padding=16, bg=CARD_BG, extruded=True):
            super().__init__(parent)
            self.radius = radius
            self.padding = padding
            self.bg = bg
            self.extruded = extruded
            self.setAttribute(Qt.WA_TranslucentBackground)
            # No stylesheet - custom paint
        
        def paintEvent(self, event):
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            
            # Full rect minus margin for shadows
            margin = 12
            rect = self.rect().adjusted(margin, margin, -margin, -margin)
            path = QPainterPath()
            path.addRoundedRect(QRectF(rect), self.radius, self.radius)
            
            if self.extruded:
                # Dark shadow bottom-right (offset 10,10)
                painter.setPen(Qt.NoPen)
                # Simulate blur by drawing 3 layers decreasing alpha
                for i, alpha in enumerate([20, 35, 50]):
                    offset = 10 - i*2
                    c = QColor(0,0,0, alpha)
                    painter.setBrush(c)
                    r = rect.adjusted(offset, offset, offset, offset)
                    p2 = QPainterPath()
                    p2.addRoundedRect(QRectF(r), self.radius, self.radius)
                    painter.drawPath(p2)
                
                # Light shadow top-left
                for i, alpha in enumerate([6, 10, 14]):
                    offset = -8 + i*1
                    c = QColor(255,255,255, alpha)
                    painter.setBrush(c)
                    r = rect.adjusted(offset, offset, offset, offset)
                    p2 = QPainterPath()
                    p2.addRoundedRect(QRectF(r), self.radius, self.radius)
                    painter.drawPath(p2)
            
            else:
                # Inset - inner shadows
                # Draw main first then inner shadows
                painter.setBrush(self.bg)
                painter.setPen(Qt.NoPen)
                painter.drawPath(path)
                
                # Inner dark top-left
                inner_dark = QColor(0,0,0, 70)
                painter.setBrush(inner_dark)
                inner_rect = rect.adjusted(3,3,-3,-3)
                # We fake inset by drawing smaller shadow inside
                pInner = QPainterPath()
                pInner.addRoundedRect(QRectF(inner_rect), self.radius-3, self.radius-3)
                # Subtract to keep border?
                painter.drawPath(pInner)
                
                # Don't draw main again for extruded path below handles
                return
            
            # Main card
            painter.setBrush(self.bg)
            painter.setPen(Qt.NoPen)
            painter.drawPath(path)
    
    class NeumorphicButton(QPushButton):
        """Neumorphic button - extruded, press = inset"""
        def __init__(self, text="", parent=None, accent=False):
            super().__init__(text, parent)
            self.accent = accent
            self.is_pressed = False
            self.radius = 14
            self.bg = CARD_BG
            self.setMinimumHeight(44)
            self.setCursor(Qt.PointingHandCursor)
            self.setAttribute(Qt.WA_TranslucentBackground)
            self.setStyleSheet("background: transparent; border: none;")
        
        def mousePressEvent(self, e):
            self.is_pressed = True
            self.update()
            super().mousePressEvent(e)
        
        def mouseReleaseEvent(self, e):
            self.is_pressed = False
            self.update()
            super().mouseReleaseEvent(e)
        
        def paintEvent(self, event):
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            rect = self.rect().adjusted(8, 6, -8, -6)
            path = QPainterPath()
            path.addRoundedRect(QRectF(rect), self.radius, self.radius)
            
            if not self.is_pressed:
                # Extruded shadows
                painter.setPen(Qt.NoPen)
                # Dark shadow
                for i, alpha in enumerate([30, 50, 75]):
                    offset = 6 - i
                    c = QColor(0,0,0, alpha)
                    painter.setBrush(c)
                    r = rect.adjusted(offset, offset, offset, offset)
                    p = QPainterPath()
                    p.addRoundedRect(QRectF(r), self.radius, self.radius)
                    painter.drawPath(p)
                # Light shadow
                for i, alpha in enumerate([8, 12, 16]):
                    offset = -5 + i
                    c = QColor(255,255,255, alpha)
                    painter.setBrush(c)
                    r = rect.adjusted(offset, offset, offset, offset)
                    p = QPainterPath()
                    p.addRoundedRect(QRectF(r), self.radius, self.radius)
                    painter.drawPath(p)
                # Main button bg
                bg = CARD_BG_LIGHT if not self.accent else QColor("#1E3A4E")
                if self.accent:
                    # Slight accent tint
                    bg = QColor("#234155")
                painter.setBrush(bg)
                painter.drawPath(path)
            else:
                # Pressed = inset
                bg = QColor("#1E242F") if not self.accent else QColor("#1A3445")
                painter.setBrush(bg)
                painter.setPen(Qt.NoPen)
                painter.drawPath(path)
                
                # Inner shadow
                painter.setBrush(QColor(0,0,0, 90))
                inner = rect.adjusted(2,2,-2,-2)
                pInner = QPainterPath()
                pInner.addRoundedRect(QRectF(inner), self.radius-2, self.radius-2)
                # Create inset effect with gradient border
                painter.drawPath(pInner)
                
                # Top light edge pressed
                painter.setPen(QPen(QColor(255,255,255, 8), 1))
                painter.drawPath(path)
            
            # Text
            painter.setPen(TEXT_PRIMARY if not self.accent else ACCENT)
            painter.setFont(QFont("Inter" if "Inter" in QFontDatabase().families() else "Segoe UI", 10, QFont.Medium))
            painter.drawText(rect, Qt.AlignCenter, self.text())
    
    class NeumorphicOrb(QWidget):
        """Neumorphic Orb - soft extruded circle with state colors"""
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setFixedSize(160, 160)
            self.state = "idle"
            self.glow = 0.0
            self.dir = 1
            self.pulse = 0.0
            self.timer = QTimer(self)
            self.timer.timeout.connect(self._anim)
            self.timer.start(25)
        
        def set_state(self, state: str):
            self.state = state
            self.update()
        
        def _anim(self):
            self.glow += 0.02 * self.dir
            if self.glow > 1.0 or self.glow < 0.0:
                self.dir *= -1
            self.pulse += 0.05
            self.update()
        
        def paintEvent(self, event):
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            cx, cy = self.width()//2, self.height()//2
            base_radius = 58
            
            # Background for shadows
            bg_rect = QRectF(cx-base_radius-14, cy-base_radius-14, base_radius*2+28, base_radius*2+28)
            
            # State colors neumorphic (soft not neon)
            state_colors = {
                "idle": (QColor("#3A4556"), QColor("#7DD3FC")),
                "listening": (QColor("#2D4A3E"), QColor("#4ADE80")),
                "thinking": (QColor("#4A3D2D"), QColor("#FB923C")),
                "speaking": (QColor("#3D3D4A"), QColor("#E9D5FF")),
                "error": (QColor("#4A2D2D"), QColor("#F87171")),
            }
            bg_col, accent_col = state_colors.get(self.state, state_colors["idle"])
            
            # ---- Neumorphic shadows for circle ----
            # Dark shadow bottom-right
            painter.setPen(Qt.NoPen)
            for i, alpha in enumerate([20, 40, 70]):
                offset = 12 - i*2
                c = QColor(0,0,0, alpha)
                painter.setBrush(c)
                r = QRectF(cx-base_radius-2+offset, cy-base_radius-2+offset, (base_radius+2)*2, (base_radius+2)*2)
                painter.drawEllipse(r)
            
            # Light shadow top-left
            for i, alpha in enumerate([8, 14, 20]):
                offset = -10 + i*2
                c = QColor(255,255,255, alpha)
                painter.setBrush(c)
                r = QRectF(cx-base_radius+offset, cy-base_radius+offset, base_radius*2, base_radius*2)
                painter.drawEllipse(r)
            
            # Main orb base - extruded soft
            # Gradient for soft depth
            grad = QRadialGradient(cx-15, cy-15, base_radius+20)
            grad.setColorAt(0, QColor("#2E3748"))
            grad.setColorAt(0.6, CARD_BG)
            grad.setColorAt(1, QColor("#1A202C"))
            painter.setBrush(grad)
            painter.drawEllipse(QRectF(cx-base_radius, cy-base_radius, base_radius*2, base_radius*2))
            
            # Inner orb accent depending on state - inner circle with soft glow
            inner_radius = 32 + self.glow*4
            if self.state == "listening":
                inner_radius = 36 + abs(self.glow)*8  # pulse when listening
            
            # Inner neumorphic inset
            painter.setBrush(QColor("#1E242F"))
            painter.drawEllipse(QRectF(cx-inner_radius-2, cy-inner_radius-2, (inner_radius+2)*2, (inner_radius+2)*2))
            
            # Inner glow accent
            inner_grad = QRadialGradient(cx, cy, inner_radius)
            inner_grad.setColorAt(0, QColor(accent_col.red(), accent_col.green(), accent_col.blue(), 200))
            inner_grad.setColorAt(0.5, QColor(accent_col.red(), accent_col.green(), accent_col.blue(), 90))
            inner_grad.setColorAt(1, QColor(accent_col.red(), accent_col.green(), accent_col.blue(), 10))
            painter.setBrush(inner_grad)
            painter.drawEllipse(QRectF(cx-inner_radius, cy-inner_radius, inner_radius*2, inner_radius*2))
            
            # Center dot
            painter.setBrush(QColor(255,255,255, 230))
            painter.drawEllipse(QRectF(cx-4, cy-4, 8, 8))
            
            # State text soft
            painter.setPen(QColor(255,255,255, 90))
            painter.setFont(QFont("Inter" if "Inter" in QFontDatabase().families() else "Segoe UI", 8, QFont.Bold))
            # Draw below orb
            painter.drawText(QRectF(cx-40, cy+base_radius+8, 80, 20), Qt.AlignCenter, self.state.upper())
    
    class HUDNeumorphismV3(QWidget):
        """MAIN NEUMORPHISM HUD V3"""
        
        transcription_signal = pyqtSignal(str)
        state_signal = pyqtSignal(str)
        mic_level_signal = pyqtSignal(float, float)
        
        def __init__(self, app_instance=None):
            super().__init__()
            self.app_instance = app_instance
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
            self.setAttribute(Qt.WA_TranslucentBackground)
            self.setGeometry(80, 80, 420, 780)
            self.setWindowTitle("OMNI V3 — Neomorphism")
            
            self._dragging = False
            self._drag_pos = None
            self._transcription = "Your Voice is Enough — Neomorphism Soft UI"
            self._mic_rms = 0.0
            self.waveform_data = [0]*24
            
            self._init_ui()
            self._connect_signals()
            
            self.wave_timer = QTimer(self)
            self.wave_timer.timeout.connect(self._update_wave)
            self.wave_timer.start(90)
            
            logger.info("HUDNeumorphismV3 - Soft UI, extruded, inset press")
        
        def _init_ui(self):
            # Main background with neomorphism bg color
            self.setStyleSheet(f"background: transparent;")
            
            root = QVBoxLayout(self)
            root.setContentsMargins(0, 0, 0, 0)
            
            # Outer card that holds everything - neumorphic extruded
            self.card = NeumorphicCard(self, radius=28, padding=0, bg=CARD_BG, extruded=True)
            self.card.setStyleSheet("background: transparent;")
            root.addWidget(self.card)
            
            card_layout = QVBoxLayout(self.card)
            card_layout.setContentsMargins(28, 28, 28, 28)
            card_layout.setSpacing(18)
            
            # Header
            header = QVBoxLayout()
            header.setSpacing(4)
            
            title = QLabel("OMNI V3")
            title.setStyleSheet(f"color: {TEXT_PRIMARY.name()}; font-family: 'Inter', 'Segoe UI'; font-size: 18px; font-weight: 800; background: transparent; letter-spacing: 2px;")
            title.setAlignment(Qt.AlignCenter)
            
            subtitle = QLabel("NEOMORPHISM • OFFLINE • PRIVATE")
            subtitle.setStyleSheet(f"color: {TEXT_SECONDARY.name()}; font-family: 'Inter', 'Segoe UI'; font-size: 9px; font-weight: 600; letter-spacing: 3px; background: transparent;")
            subtitle.setAlignment(Qt.AlignCenter)
            
            tiny = QLabel("GTX 1050 Ti • Privacy Profile • Soft UI")
            tiny.setStyleSheet(f"color: {QColor('#6B7280').name()}; font-family: 'Inter'; font-size: 8px; background: transparent; letter-spacing: 1px;")
            tiny.setAlignment(Qt.AlignCenter)
            
            header.addWidget(title)
            header.addWidget(subtitle)
            header.addWidget(tiny)
            card_layout.addLayout(header)
            
            # Orb area - neumorphic inset circle background
            self.orb_container = NeumorphicCard(self.card, radius=24, bg=QColor("#1E242F"), extruded=False)
            orb_layout = QVBoxLayout(self.orb_container)
            orb_layout.setContentsMargins(20, 20, 20, 12)
            orb_layout.setAlignment(Qt.AlignCenter)
            
            self.orb = NeumorphicOrb()
            orb_layout.addWidget(self.orb, alignment=Qt.AlignCenter)
            
            # Three.js attempt optional hidden (keep for wow)
            self.webview = None
            if WEBENGINE_AVAILABLE:
                try:
                    assets_path = Path(__file__).parent.parent.parent / "assets" / "three.min.js"
                    if not assets_path.exists():
                        assets_path = Path.cwd() / "assets" / "three.min.js"
                    if assets_path.exists():
                        self.webview = QWebEngineView()
                        self.webview.setFixedSize(0,0) # hidden, keep orb as main neumorphic visual
                        orb_layout.addWidget(self.webview)
                except Exception:
                    pass
            
            card_layout.addWidget(self.orb_container)
            
            # Mic device selector - neumorphic inset
            mic_card = NeumorphicCard(self.card, radius=16, bg=QColor("#1E242F"), extruded=False)
            mic_card_layout = QVBoxLayout(mic_card)
            mic_card_layout.setContentsMargins(16, 12, 16, 12)
            mic_card_layout.setSpacing(8)
            
            mic_header = QLabel("🎤 MICROPHONE — SOFT SELECT")
            mic_header.setStyleSheet(f"color: {TEXT_SECONDARY.name()}; font-family: 'Inter'; font-size: 8px; font-weight: 700; letter-spacing: 2px; background: transparent;")
            mic_card_layout.addWidget(mic_header)
            
            self.device_combo = QComboBox()
            self.device_combo.setMinimumHeight(38)
            self.device_combo.setStyleSheet(f"""
                QComboBox {{
                    background: #232933;
                    color: #E2E8F0;
                    border-radius: 12px;
                    padding: 8px 14px;
                    font-family: 'Inter', 'Segoe UI';
                    font-size: 10px;
                    border: none;
                }}
                QComboBox::drop-down {{ border: none; width: 30px; }}
                QComboBox QAbstractItemView {{
                    background: #1E242F;
                    color: #E2E8F0;
                    selection-background-color: #2A3441;
                    border-radius: 12px;
                    padding: 6px;
                }}
            """)
            # Add neumorphic shadow via graphics effect for combo parent?
            # We'll leave as is - card already inset
            mic_card_layout.addWidget(self.device_combo)
            
            # Mic bar - neumorphic track
            self.mic_bar = QProgressBar()
            self.mic_bar.setRange(0, 100)
            self.mic_bar.setValue(0)
            self.mic_bar.setTextVisible(True)
            self.mic_bar.setFormat("RMS 0% — Speak LOUD 1 inch")
            self.mic_bar.setFixedHeight(32)
            self.mic_bar.setStyleSheet(f"""
                QProgressBar {{
                    background: #1A202C;
                    border-radius: 16px;
                    text-align: center;
                    color: #A0AEC0;
                    font-family: 'Inter';
                    font-size: 9px;
                    font-weight: 600;
                    border: none;
                }}
                QProgressBar::chunk {{
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #4ADE80, stop:1 #38BDF8);
                    border-radius: 16px;
                    margin: 4px;
                }}
            """)
            mic_card_layout.addWidget(self.mic_bar)
            
            self.waveform_label = QLabel("· · · · · · · · · · · · · · · · · · · · · · · ·")
            self.waveform_label.setStyleSheet(f"color: #4ADE80; font-family: 'Consolas'; font-size: 12px; letter-spacing: 2px; background: transparent;")
            self.waveform_label.setAlignment(Qt.AlignCenter)
            mic_card_layout.addWidget(self.waveform_label)
            
            card_layout.addWidget(mic_card)
            
            # Transcription - inset neumorphic
            trans_card = NeumorphicCard(self.card, radius=16, bg=QColor("#1E242F"), extruded=False)
            trans_layout = QVBoxLayout(trans_card)
            trans_layout.setContentsMargins(16, 14, 16, 14)
            
            trans_header = QLabel("💬 TRANSCRIPTION — SOFT")
            trans_header.setStyleSheet(f"color: {TEXT_SECONDARY.name()}; font-family: 'Inter'; font-size: 8px; font-weight: 700; letter-spacing: 2px; background: transparent;")
            trans_layout.addWidget(trans_header)
            
            self.trans_label = QLabel(self._transcription)
            self.trans_label.setWordWrap(True)
            self.trans_label.setStyleSheet(f"color: {TEXT_PRIMARY.name()}; font-family: 'Inter', 'Segoe UI'; font-size: 11px; line-height: 1.4; background: transparent;")
            self.trans_label.setAlignment(Qt.AlignLeft)
            self.trans_label.setMinimumHeight(80)
            trans_layout.addWidget(self.trans_label)
            
            card_layout.addWidget(trans_card)
            
            # Demo buttons - neumorphic
            demo_header = QLabel("🎯 DEMO — INSET WHEN PRESSED")
            demo_header.setStyleSheet(f"color: {ACCENT_ORANGE.name()}; font-family: 'Inter'; font-size: 8px; font-weight: 800; letter-spacing: 2px; background: transparent;")
            card_layout.addWidget(demo_header)
            
            self.btn_access = NeumorphicButton("♿  Accessibility  —  Soft UI", accent=False)
            self.btn_chain = NeumorphicButton("🔗  Chain  +  Self-Heal  —  Soft", accent=True)
            self.btn_business = NeumorphicButton("🏪  Shop Guardian  —  Soft", accent=False)
            
            self.btn_access.clicked.connect(self._demo_accessibility)
            self.btn_chain.clicked.connect(self._demo_chain)
            self.btn_business.clicked.connect(self._demo_business)
            
            card_layout.addWidget(self.btn_access)
            card_layout.addWidget(self.btn_chain)
            card_layout.addWidget(self.btn_business)
            
            # Controls row
            ctrl_row = QHBoxLayout()
            ctrl_row.setSpacing(10)
            
            self.btn_test = NeumorphicButton("🧪 Test Mic")
            self.btn_test.clicked.connect(self._test_mic)
            self.btn_test.setMinimumHeight(40)
            
            self.btn_close = NeumorphicButton("✕ Close")
            self.btn_close.clicked.connect(self.close)
            self.btn_close.setMinimumHeight(40)
            
            ctrl_row.addWidget(self.btn_test)
            ctrl_row.addWidget(self.btn_close)
            card_layout.addLayout(ctrl_row)
            
            # Footer
            footer = QLabel("OMNI V3 Neomorphism • Your Voice is Enough • Offline on 1050 Ti")
            footer.setStyleSheet(f"color: #4A5568; font-family: 'Inter'; font-size: 7px; letter-spacing: 1px; background: transparent;")
            footer.setAlignment(Qt.AlignCenter)
            card_layout.addWidget(footer)
        
        def _connect_signals(self):
            self.transcription_signal.connect(self.set_transcription)
            self.state_signal.connect(self.set_state)
            self.mic_level_signal.connect(self.set_mic_level)
        
        def set_transcription(self, text: str):
            try:
                self._transcription = text
                # Format with soft line breaks
                self.trans_label.setText(text[:400])
                logger.info(f"HUD Neu transcription: {text[:100]}")
            except Exception as e:
                logger.warning(f"set_transcription neomorph failed: {e}")
        
        def set_state(self, state: str):
            try:
                if self.orb:
                    self.orb.set_state(state)
            except Exception as e:
                logger.warning(f"set_state neomorph failed: {e}")
        
        def set_mic_level(self, rms: float, max_val: float):
            try:
                self._mic_rms = rms
                pct = int(min(100, (rms / 0.05) * 100))
                self.mic_bar.setValue(pct)
                if rms < 0.001:
                    self.mic_bar.setFormat("🔇 Silent — Boost 100% +30dB")
                elif rms < 0.01:
                    self.mic_bar.setFormat(f"🔈 Low {rms:.4f} — LOUDER")
                elif rms < 0.03:
                    self.mic_bar.setFormat(f"🔉 Good {rms:.4f}")
                else:
                    self.mic_bar.setFormat(f"🔊 LOUD {rms:.4f} Excellent")
                self.waveform_data.append(rms)
                if len(self.waveform_data) > 24:
                    self.waveform_data.pop(0)
            except Exception as e:
                logger.warning(f"set_mic_level neomorph failed: {e}")
        
        def _update_wave(self):
            try:
                bars = ["·", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
                wave = ""
                for rms in self.waveform_data[-24:]:
                    idx = int(min(8, (rms / 0.04) * 8))
                    wave += bars[idx] + " "
                self.waveform_label.setText(wave)
            except Exception:
                pass
        
        # Demo handlers same as before
        def _demo_accessibility(self):
            try:
                from omni_v2.tools.demo_scenarios import DemoScenarios
                demo = DemoScenarios()
                result = demo.accessibility_workflow()
                text = f"♿ {result.workflow}\n\n" + "\n".join(result.agent_logs[:4]) + f"\n\n→ {result.final_output}\n\n{result.impact_statement}"
                self.set_transcription(text)
                self.set_state("speaking")
                QTimer.singleShot(3000, lambda: self.set_state("idle"))
                try:
                    from omni_v2.voice.tts_simple import get_simple_tts
                    get_simple_tts().speak_async(result.final_output[:180])
                except Exception:
                    pass
            except Exception as e:
                self.set_transcription(f"Demo failed: {e}")
        
        def _demo_chain(self):
            try:
                from omni_v2.tools.demo_scenarios import DemoScenarios
                demo = DemoScenarios()
                result = demo.chain_self_healing_workflow()
                text = f"🔗 {result.workflow}\n\n" + "\n".join(result.agent_logs[:6]) + f"\n\n→ {result.final_output}"
                self.set_transcription(text)
                self.set_state("thinking")
                QTimer.singleShot(1500, lambda: self.set_state("speaking"))
                QTimer.singleShot(3500, lambda: self.set_state("idle"))
            except Exception as e:
                self.set_transcription(f"Demo failed: {e}")
        
        def _demo_business(self):
            try:
                from omni_v2.tools.demo_scenarios import DemoScenarios
                demo = DemoScenarios()
                result = demo.business_guardian_workflow()
                text = f"🏪 {result.workflow}\n\n" + "\n".join(result.agent_logs[:5]) + f"\n\n→ {result.final_output}"
                self.set_transcription(text)
                self.set_state("speaking")
                QTimer.singleShot(3000, lambda: self.set_state("idle"))
            except Exception as e:
                self.set_transcription(f"Demo failed: {e}")
        
        def _test_mic(self):
            try:
                self.set_transcription("🧪 Testing mic 2s — Speak LOUD now! Soft UI listening...")
                self.set_state("listening")
                from omni_v2.voice.audio_device_v3 import get_audio_v3
                audio_mgr = get_audio_v3()
                combo_text = self.device_combo.currentText()
                idx = audio_mgr.get_index_from_combo_text(combo_text)
                import threading, time
                def test_thread():
                    for i in range(20):
                        res = audio_mgr.test_mic_rms(device_index=idx, duration=0.15)
                        rms = res.get('rms', 0)
                        max_v = res.get('max', 0)
                        self.mic_level_signal.emit(rms, max_v)
                        time.sleep(0.08)
                    self.state_signal.emit("idle")
                    self.transcription_signal.emit(f"Mic test done! Best RMS {self._mic_rms:.4f}. If <0.01 boost Windows Sound → Input 100% +30dB, 1 inch close!")
                threading.Thread(target=test_thread, daemon=True).start()
            except Exception as e:
                self.set_transcription(f"Mic test failed: {e}")
        
        def load_devices(self, devices: list):
            try:
                self.device_combo.clear()
                self.device_combo.addItems(devices)
            except Exception as e:
                logger.warning(f"load_devices neomorph failed: {e}")
        
        def mousePressEvent(self, event):
            if event.button() == Qt.LeftButton:
                self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
                self._dragging = True
        
        def mouseMoveEvent(self, event):
            if hasattr(self, '_dragging') and self._dragging:
                self.move(event.globalPos() - self._drag_pos)
        
        def mouseReleaseEvent(self, event):
            self._dragging = False
    
    # Alias for compatibility
    HUDSimpleV3 = HUDNeumorphismV3
    HUDNeomorphismV3_Modal = HUDNeumorphismV3

else:
    class HUDNeumorphismV3:
        def __init__(self, *a, **k):
            print("PyQt5 not available - HUDNeumorphismV3 dummy")
        def set_transcription(self, *a, **k): pass
        def set_state(self, *a, **k): pass
        def set_mic_level(self, *a, **k): pass
        def load_devices(self, *a, **k): pass
        def show(self): pass
