# 🔧 OMNI V3 — Troubleshooting

> Common issues and how to fix them.

---

## Installation Issues

### `pip install -e .[all]` fails with "CMake Error: CMAKE_C_COMPILER not set"

**Problem:** `llama-cpp-python` is trying to build from source instead of using the prebuilt wheel.

**Fix:** Use the install script which uses the prebuilt wheel index:

```powershell
# Windows
.\install.ps1

# Linux / macOS
./install.sh
```

If that doesn't work, install the wheel manually:

```bash
pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
```

### `omni: command not found` after `pip install`

**Problem:** The `omni` command wasn't installed in your PATH.

**Fix:**

```bash
# Reinstall in editable mode
pip install -e .

# Or check if it's in a different location
python -m omni.cli --help
```

### UnicodeEncodeError: 'charmap' codec can't encode '✅'

**Problem:** Windows console is using cp1252 instead of UTF-8.

**Fix:** Set PowerShell to UTF-8 (run before starting OMNI):

```powershell
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null
$env:PYTHONIOENCODING = "utf-8"
```

This is already handled in `omni_v2/utils/utf8.py`, which is called at the
top of `omni.py` and `omni/cli.py`. If you still see this, set the env var
before running.

---

## Model Issues

### `Model not found: data/models/qwen2.5-1.5b-instruct-q4_k_m.gguf`

**Fix:**

```bash
omni model download
```

This fetches the 1.1GB Qwen2.5-1.5B model from HuggingFace.

### `Brain loaded but token generation is very slow`

**Problem:** Model is running on CPU, not GPU.

**Fix:** Ensure `n_gpu_layers=20` in `omni_v2/llm/brain.py`. Check GPU is detected:

```python
import torch
print(torch.cuda.is_available())  # Should be True on NVIDIA
print(torch.cuda.device_count())  # Should be >= 1
```

For NVIDIA GPUs, install llama-cpp-python with CUDA support:

```powershell
.\install.ps1 -Cuda cu121
```

### `Brain takes >10s to load`

**Problem:** Cold load is loading the model from disk. Once loaded, it stays in RAM.

**Fix:** First command will be slow. Subsequent commands are 1-2s.

To preload, send a dummy command after startup:

```bash
curl -X POST http://localhost:8765/api/execute -H "Content-Type: application/json" -d "{\"command\":\"hello\"}"
```

---

## Voice Issues

### Microphone not detected (no input devices)

**Problem:** PyAudio is not installed (we don't use it), or sounddevice can't find the mic.

**Fix:**

```bash
# List available devices
python -c "import sounddevice as sd; print(sd.query_devices())"
```

If empty list, check:
- Microphone is plugged in
- Microphone is not muted in OS settings
- Privacy settings allow microphone access (Windows 10+)

### STT returns empty text

**Problem:** Microphone level too low, or background noise.

**Fix:**

1. Check mic level: `POST /api/test-mic`
2. Speak louder, closer to the mic
3. Reduce background noise
4. Boost mic gain in OS settings (Windows: Settings → Sound → Input)

### TTS sounds robotic

**Problem:** SAPI5 fallback is being used instead of edge-tts.

**Fix:** Install edge-tts:

```bash
pip install edge-tts
```

Restart OMNI. Check status: `GET /api/health` → `tts.engine` should be `edge-tts`.

### Wake word not triggering

**Problem:** Wake word sensitivity is too low, or wrong keyword.

**Fix:**

```bash
# Check status
curl http://localhost:8765/api/health
```

Look for `wake_word` status. Should say `loaded` with a backend.

If not, install openwakeword:

```bash
pip install openwakeword
```

For "Hey OMNI" specifically, you can train a custom model (Phase 4).

---

## Backend Issues

### `Address already in use: 0.0.0.0:8765`

**Problem:** Another instance of OMNI is running on the same port.

**Fix:**

```bash
# Windows: Find and kill the process
Get-Process python | Where-Object {$_.MainWindowTitle -like "*uvicorn*"} | Stop-Process -Force

# Linux / macOS
lsof -i :8765  # find PID
kill -9 <PID>
```

### `omni start` doesn't open a browser

**Problem:** Browser launch failed (headless server, no display).

**Fix:** Use `--no-browser` flag and open manually:

```bash
omni start --no-browser
# Then open http://localhost:8765/docs manually
```

### Frontend shows "Failed to fetch" or CORS error

**Problem:** CORS is blocking the request.

**Fix:** CORS is configured to allow all origins by default. If you see this:

1. Check the backend is running: `curl http://localhost:8765/api/health`
2. Check the frontend is on port 3000: `curl http://localhost:3000`
3. Check the API URL in `frontend_next/app/page.js` is `http://localhost:8765`

### WebSocket disconnects immediately

**Problem:** WebSocket route is missing or proxy is blocking it.

**Fix:** Check that `WS /ws` is in the FastAPI routes. It's defined in `backend_fastapi/main.py` around line 480.

---

## Tool Issues

### `Open this_doesnt_exist.exe` fails

**Expected!** The system is designed to self-heal. Look for:
- Multiple tool calls in the response (chrome → msedge → fallback)
- "I tried X, then Y, then Z" type messages
- Graceful error message at the end

If you get a hard error instead, the tool's allowlist needs updating.

### `open github` opens but Chrome shows email

**Problem:** Browser profile isn't isolated.

**Fix:** Check `data/chrome_profile/OMNI-Profile/`. It should be a separate Chrome profile. If not, delete it and let OMNI recreate:

```bash
# Stop OMNI
rm -rf data/chrome_profile
omni start
# Try again
```

### Files write fails with "Path blocked by guardrail"

**Expected!** The guardrail blocks writes outside `data/output/`. This is by design.

**Fix:** Either:
- Save to `data/output/` (e.g. `data/output/myfile.txt`)
- Modify `omni_v2/core/guardrails.py` to allow other paths (not recommended)

---

## Memory Issues

### Session memory grows unbounded

**Fix:** Run cleanup:

```python
from omni_v2.memory.session_memory import get_session_memory
deleted = get_session_memory().cleanup_old_sessions(max_age_days=90)
print(f"Deleted {deleted} old sessions")
```

Or add a cron job:

```bash
curl -X POST http://localhost:8765/api/scheduler/cron \
  -H "Content-Type: application/json" \
  -d '{"name":"memory cleanup","command":"run cleanup","cron":"0 3 * * 0"}'
```

### Profile doesn't persist

**Problem:** `data/profiles/user.json` not being saved.

**Fix:** Check disk space. Check write permissions on the `data/` directory.

```bash
ls -la data/profiles/
```

If the file doesn't exist, set a value via API and check again:

```bash
curl -X POST http://localhost:8765/api/user/profile \
  -H "Content-Type: application/json" \
  -d '{"name":"Test"}'

ls -la data/profiles/
```

---

## UI Issues

### Cinematic UI shows "Can't reach backend"

**Fix:** Check that backend is running on port 8765:

```bash
curl http://localhost:8765/api/health
```

If yes, check CORS. The frontend should be on `http://localhost:3000` and backend on `http://localhost:8765`.

### UI shows but commands don't work

**Fix:** Open browser DevTools (F12) → Network tab. Look for failed requests to `/api/execute`. Check the response body for error messages.

### Proactive banner doesn't appear

**Fix:** Wait 60 seconds (proactive engine runs every 60s). Check it's enabled:

```bash
curl http://localhost:8765/api/health
# Look for: "proactive_active": true
```

If false, check the backend logs for errors related to proactive_v2.

---

## Test Issues

### `omni test` fails with "ModuleNotFoundError: No module named 'omni_v2'"

**Fix:**

```bash
# Make sure you installed in editable mode
pip install -e .

# Or run from the repo root
cd /path/to/Omni
python -m omni_v2.tests.test_security_guardrails
```

### Individual test passes but `omni test` fails

**Problem:** Singleton state pollution between tests.

**Fix:** This is expected in some cases. The tests are designed to be runnable individually. To run all:

```bash
for t in test_security_guardrails test_fast_af_db test_hermes_refinement test_skill_synthesis test_user_profile test_session_memory test_personality test_opinion test_onboarding test_demo_mode test_stats test_vision test_voice_clone test_marketplace; do
    python -m omni_v2.tests.$t 2>&1 | tail -1
done
```

If a specific test fails, run it individually to see the issue.

---

## Skill Marketplace Issues

### `omni skills install` fails with network error

**Problem:** Can't reach the GitHub marketplace URL.

**Fix:** The installer creates a stub skill offline. Check:

```bash
ls data/skills/installed/
```

If the file exists, the install "succeeded" (offline). To get the real skill, connect to the internet and reinstall.

### Custom skill doesn't load

**Problem:** Skill file syntax error or missing required structure.

**Fix:** Use the SDK template:

```python
from omni_v2.sdk import skill, command, reply

@skill(
    name="my_skill",
    category="custom",
    description="What my skill does",
)
class MySkill:
    async def execute(self, entities, context):
        return reply("hello!")
```

Save to `data/skills/installed/my_skill.py`. Restart OMNI.

---

## Performance Issues

### Brain is slow (>5s per turn)

**Possible causes:**

1. **CPU fallback:** GPU not detected. Check `n_gpu_layers=20` in `brain.py`.
2. **Large context:** History > 5 turns. Reduce `_max_history`.
3. **Other apps using GPU:** Close Chrome, games, etc.

### UI is laggy

**Fix:**

1. Reduce proactive polling: change `setInterval(pollProactive, 30000)` to 60000 in `page.js`
2. Disable live thought stream animation
3. Use SSE streaming instead of polling

### High memory usage (>4GB)

**Fix:**

1. Run cleanup: `session_memory.cleanup_old_sessions(max_age_days=30)`
2. Don't load Moondream2 unless using vision
3. Reduce Whisper model: use `tiny.en` instead of `base.en`

---

## Getting More Help

1. **Check the logs:** `backend_fastapi/main.py` uses `loguru` for structured logging
2. **Run with debug:** Set `LOGURU_LEVEL=DEBUG` env var
3. **Check the docs:**
   - [docs/ARCHITECTURE.md](ARCHITECTURE.md) — system architecture
   - [docs/API.md](API.md) — API reference
   - [docs/PERFORMANCE.md](PERFORMANCE.md) — benchmarks
4. **File an issue:** [GitHub Issues](https://github.com/muhummadzarrar09-sudo/Omni/issues)
5. **Read the source:** Everything is well-commented. Start with `omni_v2/llm/brain.py`.

---

## Diagnostic Commands

```bash
# Full health check
curl http://localhost:8765/api/health

# Brain status
curl http://localhost:8765/api/personality

# Recent sessions
curl "http://localhost:8765/api/memory/sessions?days=1"

# Today's digest
curl http://localhost:8765/api/memory/today

# User stats
curl http://localhost:8765/api/user/stats

# Vision status
curl http://localhost:8765/api/vision/status

# Voice clone status
curl http://localhost:8765/api/voice/clone/status

# Skill marketplace status
curl http://localhost:8765/api/skills/marketplace/status

# Run all tests
omni test
```

---

## See Also

- **[docs/ARCHITECTURE.md](ARCHITECTURE.md)** — System architecture
- **[docs/API.md](API.md)** — API reference
- **[docs/PERFORMANCE.md](PERFORMANCE.md)** — Benchmarks
- **[docs/CHANGELOG.md](CHANGELOG.md)** — Version history
- **[README.md](../README.md)** — Top-level docs
