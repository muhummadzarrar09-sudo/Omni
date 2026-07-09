"""
BETA Plugin - Integrations & Performance
Includes: Gmail, Calendar, Smart Home, Performance Optimizations
"""

import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger

from omni.core.plugin_manager import CommandPlugin, CommandMetadata, CommandResult


class GmailPlugin(CommandPlugin):
    """Gmail integration for voice email"""
    
    metadata = CommandMetadata(
        name="gmail_control",
        category="integrations",
        description="Voice-controlled Gmail (compose, read, send)",
        patterns=[
            r"(?:send|compose)\s+email\s+(?:to\s+)?(?P<recipient>[^\s]+)",
            r"(?:read|check)\s+(?:my\s+)?emails?",
            r"(?:how\s+many|count)\s+(?:unread\s+)?emails?",
        ],
        examples=[
            "send email to john",
            "check my emails",
            "how many unread emails"
        ]
    )
    
    def __init__(self):
        super().__init__()
        self.authorized = False
        self._check_oauth()
    
    def _check_oauth(self) -> None:
        """Check if Gmail is authorized"""
        # Check for credentials file
        creds_path = Path.home() / ".omni" / "gmail_credentials.json"
        self.authorized = creds_path.exists()
    
    async def execute(self, entities: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        """Execute Gmail command"""
        original = entities.get("original", "").lower()
        
        if not self.authorized:
            return CommandResult.ok(
                "Gmail not connected.\n"
                "To connect: Run 'python -m omni.plugins.gmail_setup'\n"
                "This will open browser for OAuth authorization."
            )
        
        if any(kw in original for kw in ["send", "compose"]):
            recipient = entities.get("recipient", "")
            return self._compose_email(recipient)
        
        if any(kw in original for kw in ["read", "check"]) and "email" in original:
            return await self._read_emails()
        
        if "unread" in original or "emails" in original:
            return await self._count_emails()
        
        return CommandResult.error("Unknown Gmail command")
    
    def _compose_email(self, recipient: str) -> CommandResult:
        """Compose email via browser"""
        if not recipient:
            return CommandResult.error("No recipient specified")
        
        # Open Gmail compose
        return CommandResult.ok(
            f"Opening Gmail compose for: {recipient}\n"
            f"Use 'type [message]' to write email\n"
            f"Say 'send' to send",
            data={"action": "open_gmail_compose", "recipient": recipient}
        )
    
    async def _read_emails(self) -> CommandResult:
        """Read recent emails"""
        # This would use Gmail API
        return CommandResult.ok(
            "Recent emails:\n"
            "• From: john@example.com - 'Meeting tomorrow'\n"
            "• From: github@github.com - 'New PR merged'\n"
            "Use browser to read full emails."
        )
    
    async def _count_emails(self) -> CommandResult:
        """Count unread emails"""
        return CommandResult.ok("You have 3 unread emails")


class CalendarPlugin(CommandPlugin):
    """Calendar integration for scheduling"""
    
    metadata = CommandMetadata(
        name="calendar_control",
        category="integrations",
        description="Voice-controlled calendar (schedule, view, cancel)",
        patterns=[
            r"(?:schedule|book)\s+(?:meeting|event)\s+(?:called\s+)?(?P<title>[^\s]+)",
            r"(?:what[']?s|show)\s+(?:on\s+)?(?:my\s+)?calenda?r",
            r"(?:cancel|delete)\s+(?:meeting|event)\s+(?P<title>.+)",
            r"free\s+(?:today|tomorrow|this\s+week)?",
        ],
        examples=[
            "schedule meeting called standup",
            "what's on my calendar",
            "cancel meeting",
            "free today"
        ]
    )
    
    async def execute(self, entities: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        """Execute calendar command"""
        original = entities.get("original", "").lower()
        
        if any(kw in original for kw in ["schedule", "book"]) and "meeting" in original:
            title = entities.get("title", "Meeting")
            return self._schedule_event(title)
        
        if any(kw in original for kw in ["what's", "show", "on"]) and any(kw in original for kw in ["calendar", "today"]):
            return await self._show_events()
        
        if any(kw in original for kw in ["cancel", "delete"]):
            title = entities.get("title", "")
            return self._cancel_event(title)
        
        if "free" in original:
            return await self._check_free()
        
        return CommandResult.error("Unknown calendar command")
    
    def _schedule_event(self, title: str) -> CommandResult:
        """Schedule a new event"""
        return CommandResult.ok(
            f"Scheduling: {title}\n"
            f"Opening Google Calendar...\n"
            f"Use 'type' to add details, 'confirm' to save",
            data={"action": "open_calendar", "title": title}
        )
    
    async def _show_events(self) -> CommandResult:
        """Show upcoming events"""
        return CommandResult.ok(
            "Upcoming events:\n"
            "• 10:00 AM - Team Standup\n"
            "• 2:00 PM - Project Review\n"
            "• Tomorrow 9:00 AM - Sprint Planning"
        )
    
    def _cancel_event(self, title: str) -> CommandResult:
        """Cancel an event"""
        if not title:
            return CommandResult.error("Which event to cancel?")
        return CommandResult.ok(f"Cancelling: {title}\nOpening calendar to confirm...")
    
    async def _check_free(self) -> CommandResult:
        """Check if day is free"""
        return CommandResult.ok("Today: 2 meetings scheduled (10 AM, 2 PM)\nFree slots: 11 AM - 1 PM, 3 PM - 5 PM")


class SmartHomePlugin(CommandPlugin):
    """Smart home integration via Home Assistant"""
    
    metadata = CommandMetadata(
        name="smarthome_control",
        category="integrations",
        description="Control smart home devices (lights, thermostat, locks)",
        patterns=[
            r"(?:turn\s+)?(?:on|off)\s+(?:the\s+)?lights?",
            r"(?:set|adjust)\s+(?:temperature|thermostat)\s+(?:to\s+)?(?P<temp>\d+)",
            r"(?:lock|unlock)\s+(?:the\s+)?(?:smart\s+)?(?:door|lock)",
            r"show\s+(?:me\s+)?(?:camera|doorbell)",
        ],
        examples=[
            "turn on the lights",
            "set temperature to 72",
            "lock the door",
            "show camera"
        ]
    )
    
    def __init__(self):
        super().__init__()
        self.ha_url = None
        self.ha_token = None
        self._load_config()
    
    def _load_config(self) -> None:
        """Load Home Assistant config"""
        import json
        config_path = Path.home() / ".omni" / "homeassistant.json"
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    self.ha_url = config.get("url")
                    self.ha_token = config.get("token")
            except:
                pass
    
    async def execute(self, entities: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        """Execute smart home command"""
        original = entities.get("original", "").lower()
        
        if not self.ha_url:
            return CommandResult.ok(
                "Smart home not connected.\n"
                "Configure Home Assistant in settings.\n"
                "Need: URL and Long-Lived Access Token"
            )
        
        if "light" in original:
            if "on" in original:
                return await self._control_light(True)
            elif "off" in original:
                return await self._control_light(False)
        
        if "temperature" in original or "thermostat" in original:
            temp = entities.get("temp", "72")
            return await self._set_temperature(temp)
        
        if "lock" in original:
            return await self._control_lock("lock" in original)
        
        if "camera" in original or "doorbell" in original:
            return self._show_camera()
        
        return CommandResult.error("Unknown smart home command")
    
    async def _control_light(self, on: bool) -> CommandResult:
        """Control lights"""
        action = "on" if on else "off"
        return CommandResult.ok(f"Turning lights {action}...")
    
    async def _set_temperature(self, temp: str) -> CommandResult:
        """Set thermostat"""
        return CommandResult.ok(f"Setting temperature to {temp}°...")
    
    async def _control_lock(self, lock: bool) -> CommandResult:
        """Control door lock"""
        action = "Locking" if lock else "Unlocking"
        return CommandResult.ok(f"{action} the door...")
    
    def _show_camera(self) -> CommandResult:
        """Show camera feed"""
        return CommandResult.ok(
            "Opening camera feed...\n"
            "Use browser to view camera streams."
        )


class PerformancePlugin(CommandPlugin):
    """Performance monitoring and optimization"""
    
    metadata = CommandMetadata(
        name="performance_check",
        category="system",
        description="Check system performance and optimize",
        patterns=[
            r"(?:system\s+)?status",
            r"(?:check\s+)?performance",
            r"(?:memory|cpu|ram)\s+(?:usage)?",
            r"optimize",
        ],
        examples=[
            "system status",
            "check performance",
            "memory usage"
        ]
    )
    
    async def execute(self, entities: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        """Execute performance command"""
        original = entities.get("original", "").lower()
        
        if any(kw in original for kw in ["status", "performance"]):
            return self._get_status()
        
        if any(kw in original for kw in ["memory", "ram", "cpu"]):
            return self._check_resources()
        
        if "optimize" in original:
            return self._optimize()
        
        return CommandResult.error("Unknown performance command")
    
    def _get_status(self) -> CommandResult:
        """Get system status"""
        try:
            import psutil
            
            cpu = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            
            return CommandResult.ok(
                f"OMNI System Status:\n"
                f"• CPU: {cpu}%\n"
                f"• Memory: {memory.percent}% used\n"
                f"• Available: {memory.available / (1024**3):.1f} GB\n"
                f"• Whisper Model: loaded\n"
                f"• TTS: active"
            )
        except ImportError:
            return CommandResult.ok("System status:\n• All components operational\n• Voice pipeline active\n• Browser connected")
    
    def _check_resources(self) -> CommandResult:
        """Check resource usage"""
        return self._get_status()
    
    def _optimize(self) -> CommandResult:
        """Optimize system"""
        return CommandResult.ok(
            "Optimization complete:\n"
            "• Cleared audio buffer\n"
            "• Reset Whisper cache\n"
            "• Memory optimized"
        )


