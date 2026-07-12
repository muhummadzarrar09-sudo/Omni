"""UI V2 - Phase 3 - Orb + HUD + Dashboard"""
try:
    from .orb import VoiceOrb
    from .tray import TrayIcon
    from .hud import ArcReactorHUD
    from .dashboard import SystemDashboard
    __all__ = ['VoiceOrb', 'TrayIcon', 'ArcReactorHUD', 'SystemDashboard']
except Exception as e:
    print(f"UI import failed: {e}")
    __all__ = []
