"""
OMNI Voice Orb
===============

A floating, visual feedback element that represents OMNI's state.
It's a semi-transparent, pulsing orb that stays on top of all windows.

States:
  - IDLE: Soft, slow cyan pulse
  - LISTENING: Bright, fast green pulse
  - THINKING: Rotating/Shifting purple glow
  - SPEAKING: Pulsing white/blue expansion
"""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, pyqtProperty, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QRadialGradient, QBrush
import numpy as np

class VoiceOrb(QWidget):
    """
    The OMNI Voice Orb - a floating visual indicator of agent state.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Window settings: Frameless, Transparent, Always on Top
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Orb properties
        self._state = "idle"
        self._pulse_val = 0.0
        self._pulse_dir = 1
        self._color = QColor(0, 255, 255, 150) # Default Cyan
        
        # Position and Size
        self.setGeometry(100, 100, 120, 120)
        self.setFixedSize(120, 120)
        
        # Animation Timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_animation)
        self.timer.start(16) # ~60 FPS
        
        # State transition colors
        self.STATE_COLORS = {
            "idle": QColor(0, 200, 255, 100),      # Soft Cyan
            "listening": QColor(50, 255, 100, 200), # Bright Green
            "thinking": QColor(180, 100, 255, 200), # Purple
            "speaking": QColor(255, 255, 255, 220), # Bright White
        }

    def set_state(self, state: str) -> None:
        """Update the orb's visual state."""
        if state not in self.STATE_COLORS:
            state = "idle"
        
        self._state = state
        self._color = self.STATE_COLORS[state]
        self.update()

    def _update_animation(self) -> None:
        """Update the pulse value based on state."""
        # Different pulse speeds for different states
        speed = 0.02
        if self._state == "listening":
            speed = 0.08
        elif self._state == "thinking":
            speed = 0.05
        elif self._state == "speaking":
            speed = 0.1
        
        self._pulse_val += speed * self._pulse_dir
        if self._pulse_val >= 1.0 or self._pulse_val <= 0.0:
            self._pulse_dir *= -1
            
        self.update()

    def paintEvent(self, event):
        """Draw the glowing orb."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Calculate dynamic radius
        base_radius = 40
        pulse_offset = 10 * self._pulse_val if self._state != "thinking" else 5 * np.sin(self._pulse_val * 5)
        radius = base_radius + pulse_offset
        
        # Center of the widget
        cx, cy = self.width() // 2, self.height() // 2
        
        # Create radial gradient for the glow effect
        gradient = QRadialGradient(cx, cy, radius)
        
        # Color settings
        center_color = self._color
        outer_color = QColor(0, 0, 0, 0) # Transparent
        
        gradient.setColorAt(0, center_color)
        gradient.setColorAt(0.6, center_color)
        gradient.setColorAt(1.0, outer_color)
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        
        # Draw the orb
        painter.drawEllipse(cx - int(radius), cy - int(radius), int(radius * 2), int(radius * 2))
        
        # Add a secondary "aura" for thinking/listening states
        if self._state in ["listening", "thinking", "speaking"]:
            aura_radius = radius * 1.4
            aura_gradient = QRadialGradient(cx, cy, aura_radius)
            aura_gradient.setColorAt(0, QColor(self._color.red(), self._color.green(), self._color.blue(), 50))
            aura_gradient.setColorAt(1, QColor(0, 0, 0, 0))
            
            painter.setBrush(QBrush(aura_gradient))
            painter.drawEllipse(cx - int(aura_radius), cy - int(aura_radius), int(aura_radius * 2), int(aura_radius * 2))
            
        painter.end()

    def mousePressEvent(self, event):
        """Allow moving the orb by dragging."""
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            self._dragging = True

    def mouseMoveEvent(self, event):
        if hasattr(self, '_dragging') and self._dragging:
            self.move(event.globalPos() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._dragging = False
