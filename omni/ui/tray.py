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
        # QSystemTrayIcon parent must be QObject, not a plain Python class
        super().__init__(parent_app.app)
        self.parent_app = parent_app
        self.event_bus = event_bus
        self.set_icon("idle")
        self.create_menu()
        self.activated.connect(self.on_tray_activated)
        logger.info("TrayIcon created")

    def create_menu(self) -> None:
        """Build the tray context menu.
        
        Use separate QAction creation + signal connection instead of
        the compact addAction(text, parent, callback) form which has
        incompatible overloads in some PyQt5 versions.
        """
        menu = QMenu()
        
        # Status indicator (disabled)
        status_action = QAction("🎤 OMNI Ready", menu)
        status_action.setEnabled(False)
        menu.addAction(status_action)
        menu.addSeparator()
        
        # Toggle Listening
        toggle_action = QAction("🎤 Toggle Listening", menu)
        toggle_action.triggered.connect(self.toggle_listening)
        menu.addAction(toggle_action)
        menu.addSeparator()
        
        # Help
        help_action = QAction("📋 Help", menu)
        help_action.triggered.connect(self.show_help)
        menu.addAction(help_action)
        
        # Settings
        settings_action = QAction("⚙️ Settings", menu)
        settings_action.triggered.connect(self.open_settings)
        menu.addAction(settings_action)
        menu.addSeparator()
        
        # Exit
        exit_action = QAction("🚪 Exit", menu)
        exit_action.triggered.connect(self.exit_app)
        menu.addAction(exit_action)
        
        self.setContextMenu(menu)

    def set_icon(self, status: str) -> None:
        """Set tray icon color based on status."""
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
        """Update the tray icon based on current status."""
        self.set_icon(status)

    def on_tray_activated(self, reason) -> None:
        """Handle tray icon clicks."""
        if reason == QSystemTrayIcon.Trigger:
            self.toggle_listening()
        elif reason == QSystemTrayIcon.DoubleClick:
            self.open_settings()

    def toggle_listening(self) -> None:
        """Toggle voice listening on/off."""
        if self.parent_app:
            self.parent_app.toggle_listening()

    def show_help(self) -> None:
        """Show help message."""
        self.showMessage(
            "OMNI Help",
            "Press CapsLock to speak.\n\n"
            "Commands:\n"
            "  • 'open github' — Open website\n"
            "  • 'screenshot' — Capture screen\n"
            "  • 'help' — Show all commands\n"
            "  • 'settings' — Open settings"
        )

    def open_settings(self) -> None:
        """Open the OMNI settings dialog."""
        if self.parent_app:
            from omni.ui.settings import SettingsDialog
            dialog = SettingsDialog(self.parent_app.app)
            dialog.exec_()

    def exit_app(self) -> None:
        """Exit the application."""
        if self.parent_app:
            self.parent_app.app.quit()