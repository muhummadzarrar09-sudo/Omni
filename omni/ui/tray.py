"""System Tray Icon - OMNI status and menu"""
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QIcon, QPainter, QPixmap, QColor, QFont
from PyQt5.QtCore import Qt
from loguru import logger


class TrayIcon(QSystemTrayIcon):
    """System tray icon for OMNI."""

    STATUS_COLORS = {
        "idle": (50, 200, 50),
        "recording": (255, 200, 0),
        "processing": (0, 150, 255),
        "speaking": (0, 200, 150),
        "error": (255, 80, 80),
    }

    def __init__(self, parent_app, event_bus):
        # Pass QApplication as parent, not the plain Python OMNIApp class
        super().__init__(parent_app.app)
        self.parent_app = parent_app
        self.event_bus = event_bus
        self.set_icon("idle")
        self.create_menu()
        self.activated.connect(self.on_tray_activated)
        logger.info("TrayIcon created")

    def create_menu(self) -> None:
        menu = QMenu()
        status_action = QAction("🎤 OMNI Ready", menu)
        status_action.setEnabled(False)
        menu.addAction(status_action)
        menu.addSeparator()
        menu.addAction("🎤 Toggle Listening", menu, self.toggle_listening)
        menu.addSeparator()
        menu.addAction("📋 Help", menu, self.show_help)
        menu.addAction("⚙️ Settings", menu, self.open_settings)
        menu.addSeparator()
        menu.addAction("🚪 Exit", menu, self.exit_app)
        self.setContextMenu(menu)

    def set_icon(self, status: str) -> None:
        color = self.STATUS_COLORS.get(status, (100, 100, 100))
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(*color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(8, 8, 48, 48)
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Arial", 24, QFont.Bold))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "O")
        painter.end()
        self.setIcon(QIcon(pixmap))
        self.setToolTip(f"OMNI - {status.capitalize()}")

    def update_status(self, status: str) -> None:
        self.set_icon(status)

    def on_tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.Trigger:
            self.toggle_listening()
        elif reason == QSystemTrayIcon.DoubleClick:
            self.open_settings()

    def toggle_listening(self) -> None:
        if self.parent_app:
            self.parent_app.toggle_listening()

    def show_help(self) -> None:
        self.showMessage(
            "OMNI Help",
            "Press CapsLock to speak. Commands: open [site], screenshot, help, settings"
        )

    def open_settings(self) -> None:
        if self.parent_app:
            from omni.ui.settings import SettingsDialog
            dialog = SettingsDialog(self.parent_app.app)
            dialog.exec_()

    def exit_app(self) -> None:
        if self.parent_app:
            self.parent_app.app.quit()