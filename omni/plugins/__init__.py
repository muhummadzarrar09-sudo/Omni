"""OMNI Plugins - All Command Implementations (Winning Edition)"""

# MVP Plugins (Core)
from .browser_plugin import BrowserPlugin
from .windows_plugin import WindowsPlugin
from .system_plugin import SystemPlugin
from .omni_plugin import OMNIPlugin

# VSCode Plugin (NEW - fixes missing vscode_* actions)
from .vscode_plugin import VSCodePlugin

# ALPHA Plugins (Accessibility Innovation)
from .alpha_plugin import (
    AlphaPlugin, 
    MacroManager, 
    ContextManager, 
    AdaptiveParser,
    ScreenDescriberPlugin,
    AccessibilityPlugin
)

# BETA Plugins (Integrations + Performance)
from .integrations_plugin import (
    GmailPlugin, 
    CalendarPlugin, 
    SmartHomePlugin, 
    PerformancePlugin
)

__all__ = [
    # MVP Core
    'BrowserPlugin',
    'WindowsPlugin',
    'SystemPlugin',
    'OMNIPlugin',
    'VSCodePlugin',
    # ALPHA
    'AlphaPlugin',
    'MacroManager',
    'ContextManager',
    'AdaptiveParser',
    'ScreenDescriberPlugin',
    'AccessibilityPlugin',
    # BETA
    'GmailPlugin',
    'CalendarPlugin',
    'SmartHomePlugin',
    'PerformancePlugin',
]


def get_all_plugins():
    """Get all available plugins for registration - ALL ACTIVE for hackathon dominance"""
    return [
        # MVP Core (Always Active)
        BrowserPlugin(),
        WindowsPlugin(),
        SystemPlugin(),
        OMNIPlugin(),
        VSCodePlugin(),
        
        # ALPHA (Accessibility Innovation)
        AlphaPlugin(),
        ScreenDescriberPlugin(),
        AccessibilityPlugin(),
        
        # BETA (Integrations - ALL active with demo mode fallbacks)
        PerformancePlugin(),
        GmailPlugin(),
        CalendarPlugin(),
        SmartHomePlugin(),
    ]
