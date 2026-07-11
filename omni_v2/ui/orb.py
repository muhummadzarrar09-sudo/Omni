"""Voice Orb V2 - Phase 1: Simple radial, Phase 2: Three.js 2400 particles"""
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QColor, QRadialGradient, QBrush, QFont
import math, time

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("OrbV2")

class VoiceOrb(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._state = "idle"
        self._pulse_val = 0.0
        self._pulse_dir = 1
        self._color = QColor(0, 200, 255, 100)
        self.setGeometry(100, 100, 140, 140)
        self.setFixedSize(140, 140)
        self.setToolTip("OMNI V2 - Press V or say Hey OMNI\nPhase 1: Simple orb | Phase 2: Three.js 2400 particles")
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update)
        self.timer.start(16)
        self.colors = {
            "idle": QColor(0, 200, 255, 100),
            "listening": QColor(50, 255, 100, 200),
            "thinking": QColor(180, 100, 255, 200),
            "speaking": QColor(255, 255, 255, 220),
            "recording": QColor(50, 255, 100, 200),
            "processing": QColor(180, 100, 255, 200),
        }
        logger.info("VoiceOrb V2 Phase 1 (simple radial) - Phase 2 will be Three.js 2400 particles")

    def set_state(self, state: str):
        self._state = state if state in self.colors else "idle"
        self._color = self.colors.get(self._state, self.colors["idle"])
        self.update()

    def _update(self):
        speed = 0.08 if self._state in ["listening", "recording"] else 0.05 if self._state in ["thinking", "processing"] else 0.02
        self._pulse_val += speed * self._pulse_dir
        if self._pulse_val >= 1.0 or self._pulse_val <= 0.0:
            self._pulse_dir *= -1
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        base = 45
        pulse = 10 * self._pulse_val if self._state not in ["thinking", "processing"] else 5 * math.sin(self._pulse_val * 5 * 3.14)
        radius = base + pulse
        cx, cy = self.width()//2, self.height()//2
        grad = QRadialGradient(cx, cy, radius)
        grad.setColorAt(0, self._color)
        grad.setColorAt(0.6, self._color)
        grad.setColorAt(1, QColor(0,0,0,0))
        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(int(cx-radius), int(cy-radius), int(radius*2), int(radius*2))
        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            self._dragging = True

    def mouseMoveEvent(self, event):
        if hasattr(self, '_dragging') and self._dragging:
            self.move(event.globalPos() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._dragging = False
