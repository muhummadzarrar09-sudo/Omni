"""OMNI Plugins - All Command Implementations"""

# MVP Plugins (Core)
from .browser_plugin import BrowserPlugin
from .windows_plugin import WindowsPlugin
from .system_plugin import SystemPlugin
from .omni_plugin import OMNIPlugin

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
    """Get all available plugins for registration"""
    return [
        # MVP Core (Always Active)
        BrowserPlugin(),
        WindowsPlugin(),
        SystemPlugin(),
        OMNIPlugin(),
        
        # ALPHA (Accessibility Innovation)
        AlphaPlugin(),
        ScreenDescriberPlugin(),
        AccessibilityPlugin(),
        
        # BETA (Integrations - Performance always active)
        PerformancePlugin(),
        
        # BETA Integrations (Commented out until configured)
        # GmailPlugin(),
        # CalendarPlugin(),
        # SmartHomePlugin(),
    ]
