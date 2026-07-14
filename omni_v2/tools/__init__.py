"""OMNI V3 - Tools - 15 Core Reliable + Profile Isolation Magic"""

from .browser import BrowserTool
from .browser_v3 import BrowserToolV3
from .windows import WindowsTool
from .system import SystemTool
from .omni import OmniTool
from .vscode import VSCodeTool
from .media import MediaTool
from .files import FilesTool
from .ai import AITool
from .integrations import GmailTool, CalendarTool, SmartHomeTool, PerformanceTool
from .accessibility import AccessibilityTool

try:
    from .demo_scenarios import DemoScenarios
except ImportError:
    DemoScenarios = None

__all__ = [
    'BrowserTool', 'BrowserToolV3', 'WindowsTool', 'SystemTool', 'OmniTool', 'VSCodeTool',
    'MediaTool', 'FilesTool', 'AITool',
    'GmailTool', 'CalendarTool', 'SmartHomeTool', 'PerformanceTool',
    'AccessibilityTool'
]

def get_all_tools_v3():
    """V3 - 15 core reliable + profile isolation - for hackathon win"""
    tools = [
        BrowserToolV3(),  # Isolated profile magic - replaces old browser
        WindowsTool(),
        SystemTool(),
        OmniTool(),
        VSCodeTool(),
        FilesTool(),
        AccessibilityTool(),
    ]
    # Optional but keep minimal
    try:
        tools.append(SystemTool())
    except:
        pass
    return tools

def get_all_tools():
    """Get all tools - V2 compatibility + V3 override"""
    # Try V3 first
    try:
        v3 = get_all_tools_v3()
        # Add other tools for compatibility
        v3.extend([
            MediaTool(),
            AITool(),
            PerformanceTool(),
            GmailTool(),
            CalendarTool(),
            SmartHomeTool(),
        ])
        return v3
    except Exception as e:
        # Fallback V2
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
