"""UI V2"""
try:
    from .tray import TrayIcon
    from .orb import VoiceOrb
    __all__ = ['TrayIcon', 'VoiceOrb']
except Exception:
    __all__ = []
