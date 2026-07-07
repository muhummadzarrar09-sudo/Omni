# OMNI Architecture

**Version**: 1.0  
**Target**: Hackathon Demo (8 days)

---

## System Overview

```
                    ┌─────────────────────────────────────────┐
                    │           User (Voice Intent)           │
                    └────────────────────┬────────────────────┘
                                         │
                    ┌────────────────────▼────────────────────┐
                    │        PTT Hotkey (CapsLock)           │
                    │   ┌─────────────────────────────┐      │
                    │   │  Voice Activity Detection   │      │
                    │   └────────────┬──────────────┘      │
                    │                │ Audio Buffer         │
                    │                ▼                      │
                    │   ┌─────────────────────────────┐      │
                    │   │  Speech-to-Text              │      │
                    │   │  (faster-whisper, base.en)   │      │
                    │   └────────────┬──────────────┘      │
                    │                │ Text                 │
                    │                ▼                      │
                    │   ┌─────────────────────────────┐      │
                    │   │  Command Parser              │      │
                    │   └────────────┬──────────────┘      │
                    └────────────────┼─────────────────────┘
                                         │
        ┌────────────────────────────────┼────────────────────────────────┐
        ▼                                ▼                                ▼
┌───────────────┐              ┌─────────────────┐              ┌─────────────────┐
│   Browser     │              │  Windows Apps   │              │   VS Code       │
│   (CDP)       │              │  (UIA)          │              │   (Cline)       │
└───────────────┘              └────────┬────────┘              └────────┬────────┘
                                        │                                │
                    ┌────────────────────▼────────────────────┐
                    │        Kokoro TTS (Audio Feedback)      │
                    └─────────────────────────────────────────┘
```

---

## State Machine

```
IDLE → PTT Pressed → RECORDING → PTT Released → TRANSCRIBING → EXECUTING → TTS Feedback → IDLE
```

---

## Error Handling

| Error | Recovery |
|-------|----------|
| Microphone access | Wait, retry, notify |
| Whisper load fail | Fallback to tiny model |
| Browser not connected | Launch Chrome, retry |
| Element not found | Describe screen, ask |
| Command unknown | TTS: "I don't understand" |
