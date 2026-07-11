"""Tray V2"""
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QIcon, QPainter, QPixmap, QColor, QFont
from PyQt5.QtCore import Qt

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("TrayV2")

class TrayIcon(QSystemTrayIcon):
    def __init__(self, parent_app, event_bus):
        super().__init__(parent_app.app)
        self.parent_app = parent_app
        self.event_bus = event_bus
        self.set_icon("idle")
        self.create_menu()
        logger.info("TrayIcon V2")

    def create_menu(self):
        menu = QMenu()
        status = QAction("OMNI V2 Phase 1", menu)
        status.setEnabled(False)
        menu.addAction(status)
        menu.addSeparator()
        help_action = QAction("Help", menu)
        menu.addAction(help_action)
        exit_action = QAction("Exit", menu)
        exit_action.triggered.connect(self.exit_app)
        menu.addAction(exit_action)
        self.setContextMenu(menu)

    def set_icon(self, status: str):
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(0, 200, 255))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(8, 8, 48, 48)
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Arial", 24, QFont.Bold))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "O2")
        painter.end()
        self.setIcon(QIcon(pixmap))

    def update_status(self, status: str):
        self.set_icon(status)

    def exit_app(self):
        if self.parent_app:
            self.parent_app.app.quit()
