"""HUD V2 - Phase 3 - Arc Reactor + Live Transcription - FIXED Float->Int for PyQt"""
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QGraphicsDropShadowEffect
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen, QFont
import math
import time

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("HUDV2")

class ArcReactorHUD(QWidget):
    """Arc Reactor HUD - Glowing ring + live transcription + system stats - FIXED"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setGeometry(200, 200, 400, 400)
        self.setWindowTitle("OMNI V2 HUD")

        self._glow_val = 0.0
        self._glow_dir = 1
        self._transcription = "Say 'Hey OMNI' or Press V"
        self._system_stats = {"cpu": 0, "ram": 0, "mic_level": 0}

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_anim)
        self.timer.start(50)

        logger.info("ArcReactorHUD V2 - Phase 3 - Fixed float->int for drawEllipse")

    def set_transcription(self, text: str):
        self._transcription = text
        self.update()

    def set_system_stats(self, cpu: float, ram: float, mic_level: float = 0):
        self._system_stats = {"cpu": cpu, "ram": ram, "mic_level": mic_level}
        self.update()

    def _update_anim(self):
        self._glow_val += 0.05 * self._glow_dir
        if self._glow_val > 1.0 or self._glow_val < 0.0:
            self._glow_dir *= -1
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        cx, cy = self.width()//2, self.height()//2
        radius = 150

        # Outer glow (arc reactor) - FIXED: cast to int for PyQt
        glow_radius = int(radius + 20 + 10 * self._glow_val)
        for i in range(20):
            alpha = int(100 * (1 - i/20) * self._glow_val)
            color = QColor(0, 200, 255, alpha)
            painter.setPen(QPen(color, 2))
            # FIXED: All args must be int for this overload
            x = int(cx - glow_radius + i)
            y = int(cy - glow_radius + i)
            w = int((glow_radius - i) * 2)
            h = int((glow_radius - i) * 2)
            painter.drawEllipse(x, y, w, h)

        # Main ring - FIXED int
        painter.setPen(QPen(QColor(0, 200, 255, 200), 4))
        painter.drawEllipse(int(cx-radius), int(cy-radius), int(radius*2), int(radius*2))

        # Inner ring - FIXED int
        painter.setPen(QPen(QColor(0, 200, 255, 100), 2))
        painter.drawEllipse(int(cx-radius//2), int(cy-radius//2), int(radius), int(radius))

        # Center - OMNI logo
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Arial", 24, QFont.Bold)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignCenter, "OMNI\nV2")

        # Transcription around ring (bottom) - these overloads accept int, ok
        painter.setPen(QColor(255, 255, 255, 200))
        font2 = QFont("Consolas", 10)
        painter.setFont(font2)
        painter.drawText(int(cx-180), int(cy+radius+30), 360, 40, Qt.AlignCenter | Qt.TextWordWrap, self._transcription)

        # System stats (top)
        stats_text = f"CPU: {self._system_stats['cpu']:.0f}% | RAM: {self._system_stats['ram']:.0f}% | Mic: {self._system_stats['mic_level']:.3f}"
        painter.drawText(int(cx-180), int(cy-radius-40), 360, 20, Qt.AlignCenter, stats_text)

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
