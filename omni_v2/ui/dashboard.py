"""Dashboard V2 - Phase 3 - Live CPU/RAM/GPU Graphs"""
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QFont
import collections

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("DashboardV2")

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class SystemDashboard(QWidget):
    """Live system monitor dashboard - CPU, RAM, GPU VRAM, mic level"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("OMNI V2 - System Dashboard")
        self.setGeometry(100, 100, 600, 400)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)

        self.cpu_history = collections.deque(maxlen=50)
        self.ram_history = collections.deque(maxlen=50)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_stats)
        self.timer.start(1000)  # Update every second

        self.cpu = 0
        self.ram = 0
        self.mic_level = 0

        logger.info("SystemDashboard V2 - Phase 3")

    def _update_stats(self):
        if PSUTIL_AVAILABLE:
            try:
                self.cpu = psutil.cpu_percent()
                self.ram = psutil.virtual_memory().percent
            except Exception:
                pass
        self.cpu_history.append(self.cpu)
        self.ram_history.append(self.ram)
        self.update()

    def set_mic_level(self, level: float):
        self.mic_level = level

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(20, 20, 30))

        # Title
        painter.setPen(QColor(0, 200, 255))
        painter.setFont(QFont("Arial", 16, QFont.Bold))
        painter.drawText(20, 30, "OMNI V2 - System Dashboard (Phase 3)")

        # Stats
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Consolas", 12))
        y = 60
        painter.drawText(20, y, f"CPU: {self.cpu:.1f}%")
        y += 25
        painter.drawText(20, y, f"RAM: {self.ram:.1f}%")
        y += 25
        painter.drawText(20, y, f"Mic Level: {self.mic_level:.4f}")
        y += 25

        # CPU graph
        painter.setPen(QPen(QColor(0, 200, 255), 2))
        graph_x, graph_y, graph_w, graph_h = 20, y + 20, 560, 100
        painter.drawRect(graph_x, graph_y, graph_w, graph_h)
        painter.setPen(QPen(QColor(0, 255, 100), 2))
        if len(self.cpu_history) > 1:
            for i in range(1, len(self.cpu_history)):
                x1 = graph_x + (i-1) * graph_w // 50
                y1 = graph_y + graph_h - int(self.cpu_history[i-1] * graph_h / 100)
                x2 = graph_x + i * graph_w // 50
                y2 = graph_y + graph_h - int(self.cpu_history[i] * graph_h / 100)
                painter.drawLine(x1, y1, x2, y2)

        # RAM graph
        y += 140
        painter.setPen(QPen(QColor(255, 100, 100), 2))
        painter.drawRect(graph_x, y, graph_w, graph_h)
        painter.setPen(QPen(QColor(255, 200, 0), 2))
        if len(self.ram_history) > 1:
            for i in range(1, len(self.ram_history)):
                x1 = graph_x + (i-1) * graph_w // 50
                y1 = y + graph_h - int(self.ram_history[i-1] * graph_h / 100)
                x2 = graph_x + i * graph_w // 50
                y2 = y + graph_h - int(self.ram_history[i] * graph_h / 100)
                painter.drawLine(x1, y1, x2, y2)

        # Labels
        painter.setPen(QColor(200, 200, 200))
        painter.setFont(QFont("Consolas", 10))
        painter.drawText(graph_x, graph_y - 5, "CPU History")
        painter.drawText(graph_x, y - 5, "RAM History")

        painter.end()
