# 🤖 OMNI - Autonomous Personal Agent

> **Accessibility-first autonomous agent for everyone**
> Built for voice control, privacy-first, runs locally

**Hackathon**: Agentic AI Innovation Challenge 2026  
**Category**: Open Innovation  
**Platform**: Windows (GTX 1050 Ti compatible)

---

## 🎯 What is OMNI?

OMNI is a voice-controlled autonomous agent that enables hands-free computing. Built with accessibility in mind, it helps:

- 🦾 **People without hands** — Full computer control via voice
- 👨‍💻 **Developers** — Voice-navigate code, run terminal commands
- 📧 **Productivity users** — Voice email, browser automation
- ⚡ **Power users** — Custom shortcuts, workflow automation

### Key Features

| Feature | Description |
|---------|-------------|
| 🎤 **Push-to-Talk** | Press CapsLock to speak — privacy-safe, not always-listening |
| 🌐 **Browser Control** | Voice-navigate Chrome/Edge via CDP |
| 💻 **Windows Automation** | Control any Windows app via UIA |
| ⌨️ **VS Code Integration** | Voice code editing and terminal commands |
| 🔊 **Local TTS** | Kokoro TTS for instant audio feedback |
| 🔒 **Privacy-First** | All processing local — no data leaves your device |

---

## 🚀 Quick Start

### Prerequisites

- Windows 10/11
- Python 3.10+
- GTX 1050 Ti 4GB (or any GPU with 4GB+ VRAM)
- Microphone

### Installation

```powershell
# Clone this repository
git clone https://github.com/YOUR_USERNAME/omni.git
cd omni

# Create virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Launch Chrome with Accessibility

**Required** for browser control:

```powershell
# Run the launch script
.\scripts\launch-chrome.ps1
```

Or manually:
```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --force-renderer-accessibility --remote-debugging-port=9222
```

### Run OMNI

```powershell
python omni.py
```

---

## 🎤 Voice Commands

### Browser
```
"open github"          → Navigate to website
"go to google.com"     → Navigate to URL
"search for cats"      → Google search
"click login"          → Click element
```

### Windows
```
"open notepad"         → Launch application
"close window"         → Close active window
```

### System
```
"screenshot"           → Take screenshot
```

### OMNI
```
"help"                 → Show commands
"settings"             → Open settings
"status"               → Show status
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         OMNI                                │
├──────────────┬──────────────┬──────────────┬────────────────┤
│   UI Layer   │  Voice Layer │  Action Layer│   System Layer │
├──────────────┼──────────────┼──────────────┼────────────────┤
│ • System Tray│ • PTT Hotkey │ • Browser CDP│ • Global Keys  │
│ • Settings   │ • Whisper STT│ • Windows UIA│ • Clipboard    │
│ • Commands   │ • VAD        │ • VS Code    │ • Notifications│
└──────────────┴──────────────┴──────────────┴────────────────┘
```

### Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| App Shell | PyQt5 | UI, system tray, settings |
| STT | faster-whisper | Local speech-to-text |
| VAD | Silero VAD | Voice activity detection |
| TTS | Kokoro TTS | Text-to-speech feedback |
| Browser | CDP (python-cdp) | Chrome automation |
| Windows | Python-UIAutomation | GUI control |
| VS Code | WebSocket bridge | Code editor integration |

---

## 📁 Project Structure

```
omni/
├── omni/                     # Main package
│   ├── __init__.py           # Package exports
│   ├── app.py                # PyQt5 main app
│   ├── core/                 # Core systems
│   │   ├── event_bus.py      # Event communication
│   │   ├── config_manager.py # Settings persistence
│   │   ├── plugin_manager.py # Plugin registry
│   │   └── command_registry.py
│   ├── plugins/              # Command plugins
│   │   ├── browser_plugin.py
│   │   ├── windows_plugin.py
│   │   ├── system_plugin.py
│   │   └── omni_plugin.py
│   ├── voice/                # Voice pipeline
│   │   ├── ptt_manager.py
│   │   └── transcriber.py
│   ├── tts/                  # Text-to-speech
│   │   └── kokoro_tts.py
│   ├── ui/                   # User interface
│   │   ├── tray.py
│   │   └── settings.py
│   └── utils/                # Utilities
│       ├── logger.py
│       └── metrics.py
├── scripts/                  # Setup & launch scripts
│   ├── setup.ps1
│   ├── launch-omni.ps1
│   └── launch-chrome.ps1
├── docs/                     # Documentation
│   └── *.md
├── requirements.txt          # Python dependencies
├── omni.py                   # Entry point
├── README.md                 # This file
└── LICENSE                  # MIT License
```

---

## 🔧 Configuration

Settings are stored in `%USERPROFILE%\.omni\config.json`:

```json
{
    "ptt_key": "caps_lock",
    "whisper_model": "base.en",
    "whisper_device": "cuda",
    "tts_voice": "af_sarah",
    "tts_speed": 1.0,
    "tts_enabled": true,
    "browser_port": 9222,
    "debug_mode": false
}
```

### Changing Settings

1. Right-click OMNI tray icon
2. Select "Settings"
3. Modify and save

---

## 🛠️ Development

### Adding New Commands

1. Create a new plugin in `omni/plugins/`:

```python
from omni.core.plugin_manager import CommandPlugin, CommandMetadata, CommandResult

class MyPlugin(CommandPlugin):
    metadata = CommandMetadata(
        name="my_command",
        category="my_category",
        description="Does something cool",
        patterns=[r"do\s+(?P<thing>\w+)"],
        examples=["do something"]
    )
    
    async def execute(self, entities, context):
        return CommandResult.ok(f"Did: {entities.get('thing')}")
```

2. Register in `app.py`:

```python
from omni.plugins import MyPlugin
self.plugin_manager.register(MyPlugin())
```

3. Add patterns in `command_registry.py`:

```python
self.register_patterns("my_category", {
    "my_command": [(r"do\s+(?P<thing>\w+)", "thing")]
})
```

---

## 🏆 Hackathon Submission

### Required Deliverables
- [x] AI Agent explanation (this README)
- [ ] Demo Video (8 min max)
- [ ] Source Code (this repository)
- [ ] Screenshots/Presentation

---

## 📜 License

MIT License - See LICENSE file

---

## 🙏 Acknowledgments

- [whisper.cpp](https://github.com/ggerganov/whisper.cpp) — Fast Whisper inference
- [Silero VAD](https://github.com/snakers4/silero-vad) — Voice activity detection
- [Kokoro TTS](https://github.com/nazdridoy/kokoro-tts) — Local text-to-speech
- [Python-UIAutomation](https://github.com/yinkaisheng/Python-UIAutomation-for-Windows) — Windows automation

---

**Built with ❤️ for accessibility and universal computing**
