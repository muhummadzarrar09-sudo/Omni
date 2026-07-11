"""
OMNI Voice Orb - Winning Visual Core
=====================================
Floating, visual feedback element that represents OMNI's state.
Hackathon-grade: no heavy deps, 60fps, draggable, tooltip, context menu.

States:
  IDLE: Soft slow cyan pulse
  LISTENING: Bright fast green pulse
  THINKING: Purple glow with rotation
  SPEAKING: White/blue expansion
"""

from PyQt5.QtWidgets import QWidget, QMenu, QAction
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QPainter, QColor, QRadialGradient, QBrush, QFont
from loguru import logger
import math
import time

class VoiceOrb(QWidget):
    """OMNI Voice Orb - floating visual indicator (robust, no numpy)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self._state = "idle"
        self._pulse_val = 0.0
        self._pulse_dir = 1
        self._color = QColor(0, 255, 255, 150)
        self._drag_pos = None
        self._dragging = False
        self._start_time = time.time()
        
        self.setGeometry(100, 100, 140, 140)
        self.setFixedSize(140, 140)
        self.setToolTip("OMNI - Press V to toggle listening\nRight-click for menu | Drag to move")
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_animation)
        self.timer.start(16)  # ~60 FPS
        
        self.STATE_COLORS = {
            "idle": QColor(0, 200, 255, 100),
            "listening": QColor(50, 255, 100, 200),
            "thinking": QColor(180, 100, 255, 200),
            "speaking": QColor(255, 255, 255, 220),
            "recording": QColor(50, 255, 100, 200),
            "processing": QColor(180, 100, 255, 200),
            "error": QColor(255, 80, 80, 180),
        }

        self.STATE_LABELS = {
            "idle": "● Idle - Press V",
            "listening": "🎤 Listening...",
            "recording": "🎤 Listening...",
            "thinking": "🧠 Thinking...",
            "processing": "🧠 Thinking...",
            "speaking": "🔊 Speaking...",
            "error": "⚠ Error",
        }

        logger.info("VoiceOrb created - Visual Core active")

    def set_state(self, state: str) -> None:
        if state not in self.STATE_COLORS:
            # Map generic statuses
            mapping = {
                "recording": "listening",
                "processing": "thinking",
                "speaking": "speaking",
                "idle": "idle",
                "error": "idle"
            }
            state = mapping.get(state, "idle")
        
        if state in self.STATE_COLORS:
            self._state = state
            self._color = self.STATE_COLORS[state]
            tooltip = self.STATE_LABELS.get(state, state)
            self.setToolTip(f"OMNI - {tooltip}\nRight-click for menu | Drag to move")
            self.update()
            logger.debug(f"Orb state -> {state}")

    def _update_animation(self) -> None:
        speed = 0.02
        if self._state == "listening" or self._state == "recording":
            speed = 0.08
        elif self._state == "thinking" or self._state == "processing":
            speed = 0.05
        elif self._state == "speaking":
            speed = 0.1
        
        self._pulse_val += speed * self._pulse_dir
        if self._pulse_val >= 1.0 or self._pulse_val <= 0.0:
            self._pulse_dir *= -1
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        base_radius = 45
        # Use math.sin instead of numpy
        if self._state == "thinking" or self._state == "processing":
            pulse_offset = 5 * math.sin(self._pulse_val * 5 * math.pi)
        else:
            pulse_offset = 10 * self._pulse_val
        radius = base_radius + pulse_offset
        
        cx, cy = self.width() // 2, self.height() // 2
        
        gradient = QRadialGradient(cx, cy, radius)
        center_color = self._color
        outer_color = QColor(0, 0, 0, 0)
        
        gradient.setColorAt(0, center_color)
        gradient.setColorAt(0.6, center_color)
        gradient.setColorAt(1.0, outer_color)
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(int(cx - radius), int(cy - radius), int(radius * 2), int(radius * 2))
        
        # Aura for active states
        if self._state in ["listening", "recording", "thinking", "processing", "speaking"]:
            aura_radius = radius * 1.5
            aura_gradient = QRadialGradient(cx, cy, aura_radius)
            aura_gradient.setColorAt(0, QColor(self._color.red(), self._color.green(), self._color.blue(), 40))
            aura_gradient.setColorAt(1, QColor(0, 0, 0, 0))
            painter.setBrush(QBrush(aura_gradient))
            painter.drawEllipse(int(cx - aura_radius), int(cy - aura_radius), int(aura_radius * 2), int(aura_radius * 2))

        # Center letter O with state icon
        painter.setPen(QColor(255, 255, 255, 200))
        font = QFont("Segoe UI", 20, QFont.Bold)
        painter.setFont(font)
        # Show first letter of state or O
        text = "O"
        if self._state == "listening":
            text = "🎤"
        elif self._state in ["thinking", "processing"]:
            text = "🧠"
        elif self._state == "speaking":
            text = "🔊"
        # Use simple ASCII fallback if emoji not render
        if len(text) > 1:  # emoji might be 2 chars but ok
            # Draw smaller
            painter.setFont(QFont("Segoe UI", 16, QFont.Bold))
        painter.drawText(self.rect(), Qt.AlignCenter, "O" if self._state == "idle" else text[:1] if text == "O" else "●")

        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            self._dragging = True
        elif event.button() == Qt.RightButton:
            self._show_context_menu(event.globalPos())

    def mouseMoveEvent(self, event):
        if self._dragging and self._drag_pos is not None:
            self.move(event.globalPos() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._dragging = False

    def _show_context_menu(self, pos: QPoint):
        menu = QMenu(self)
        status_action = QAction(f"Status: {self._state.upper()}", menu)
        status_action.setEnabled(False)
        menu.addAction(status_action)
        menu.addSeparator()
        help_action = QAction("📋 Help", menu)
        help_action.triggered.connect(lambda: logger.info("Orb help clicked"))
        menu.addAction(help_action)
        exit_action = QAction("🚪 Exit OMNI", menu)
        exit_action.triggered.connect(self._exit_app)
        menu.addAction(exit_action)
        menu.exec_(pos)

    def _exit_app(self):
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            app.quit()

    def enterEvent(self, event):
        # Slight opacity increase on hover
        self.setWindowOpacity(1.0)

    def leaveEvent(self, event):
        self.setWindowOpacity(0.85)
