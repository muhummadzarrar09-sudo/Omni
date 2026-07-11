"""OMNI V2 Tools - 100+ Tools (Phase 1: Start with 12 core, expand to 100)"""

from .browser import BrowserTool
from .windows import WindowsTool
from .system import SystemTool
from .omni import OmniTool
from .vscode import VSCodeTool
from .media import MediaTool
from .files import FilesTool
from .ai import AITool
from .integrations import GmailTool, CalendarTool, SmartHomeTool, PerformanceTool
from .accessibility import AccessibilityTool

__all__ = [
    'BrowserTool', 'WindowsTool', 'SystemTool', 'OmniTool', 'VSCodeTool',
    'MediaTool', 'FilesTool', 'AITool',
    'GmailTool', 'CalendarTool', 'SmartHomeTool', 'PerformanceTool',
    'AccessibilityTool'
]

def get_all_tools():
    """Get all tools - Phase 1: 12 core, Phase 2: 100+"""
    return [
        BrowserTool(),
        WindowsTool(),
        SystemTool(),
        OmniTool(),
        VSCodeTool(),
        MediaTool(),
        FilesTool(),
        AITool(),
        AccessibilityTool(),
        PerformanceTool(),
        GmailTool(),
        CalendarTool(),
        SmartHomeTool(),
    ]
