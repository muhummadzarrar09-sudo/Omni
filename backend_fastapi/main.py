"""
OMNI V3 - FastAPI Backend - CORRECT Architecture
Next.js (beautiful UI) <-> FastAPI (pretty damn good backend) <-> OMNI Brain (Planner->Executor->Monitor->Evaluator + browser_v3 isolated + sounddevice fixes -9999)

Portable: No D:/Omni hardcode, uses Path(__file__).resolve().parent...
Run: uvicorn main:app --reload --port 8765
Or: python main.py

Endpoints:
- GET /                     -> health
- GET /api/health           -> brain status
- GET /api/devices          -> mic devices
- POST /api/execute         -> execute command via multi-agent
- GET /api/demo/{type}      -> accessibility, chain, business
- POST /api/test-mic        -> test mic RMS
- POST /api/ptt/start       -> start PTT recording (sounddevice)
- POST /api/ptt/stop        -> stop + transcribe + execute
- WebSocket /ws             -> live mic level + transcription stream
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, Request, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, field_validator
from pathlib import Path
import sys
import asyncio
import json
import time
import secrets
from typing import Optional, Any, Dict

# Ensure repo root in path
THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("FastAPI")

from core.brain import get_brain

app = FastAPI(
    title="OMNI V3 FastAPI - Neomorphism Backend",
    description="Pretty damn good backend processing for Next.js beautiful UI. Multi-agent, profile isolation, sounddevice fixes -9999, portable no D:/Omni hardcode.",
    version="3.1.0"
)

def api_error(message: str, status_code: int = 500):
    """Consistent error response for mutating API handlers."""
    return JSONResponse(status_code=status_code, content={"status": "error", "error": message})

# SMOKE-10 fix: cap request body size at 64KB to prevent OOM attacks
MAX_REQUEST_BYTES = 64 * 1024


@app.middleware("http")
async def limit_request_size(request, call_next):
    """Reject requests with body larger than MAX_REQUEST_BYTES (64KB)."""
    cl = request.headers.get("content-length")
    if cl is not None:
        try:
            if int(cl) > MAX_REQUEST_BYTES:
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=413,
                    content={"error": f"Request body too large (max {MAX_REQUEST_BYTES} bytes)"}
                )
        except (ValueError, TypeError):
            pass
    return await call_next(request)

# Optional explicit token for LAN/non-loopback use. Local loopback remains usable by the desktop UI.
import os
OMNI_API_TOKEN = os.environ.get("OMNI_API_TOKEN")

@app.middleware("http")
async def require_api_token(request: Request, call_next):
    # Localhost is trusted only when no explicit token is configured. Once a
    # token is configured, every mutating HTTP request requires it, regardless
    # of source address. Pairing bootstrap is the sole exception.
    bootstrap = request.url.path in {"/api/network/pair", "/api/network/pair/verify"}
    if OMNI_API_TOKEN and request.method not in {"GET", "HEAD", "OPTIONS"} and not bootstrap:
        supplied = request.headers.get("X-OMNI-Token", "")
        valid = secrets.compare_digest(supplied, OMNI_API_TOKEN)
        if not valid:
            valid = supplied in _device_tokens and _device_tokens[supplied].get("expires_at", 0) > time.time()
        if not valid:
            return JSONResponse(status_code=401, content={"error": "Authentication required"})
    return await call_next(request)

# CORS for Next.js (3000) and any origin for judges
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-OMNI-Token"],
)

class ExecuteRequest(BaseModel):
    command: str = Field(min_length=1, max_length=2000)
    # SMOKE-10 fix: cap command length to prevent abuse
    max_length: int = 2000

    @field_validator('command')
    @classmethod
    def _cap_command(cls, v: str) -> str:
        # Hard cap to 2000 chars; anything beyond is truncated with a marker
        if not v:
            return v
        if len(v) > 2000:
            return v[:2000] + "..."
        return v.strip()


# GUARD-04: per-IP rate limiter (60 req/min)
from omni_v2.core.guardrails import RateLimiter
_rate_limiter = RateLimiter(max_per_minute=60)


class ExecuteResponse(BaseModel):
    success: bool
    message: str
    logs: list = []
    steps: int = 0
    mock: bool = False

# Startup
@app.on_event("startup")
async def startup():
    # ROBUST-BUG-01 fix: explicitly bootstrap workspace (data dir + migration)
    try:
        from omni_v2.core.paths import bootstrap_workspace
        bootstrap_workspace()
        logger.info("✅ Workspace bootstrapped")
    except Exception as e:
        logger.warning(f"Workspace bootstrap failed: {e}")
    try:
        from omni_v2.agents.proactive import get_proactive_agent
        get_proactive_agent().start()
    except Exception:
        pass
    try:
        from omni_v2.memory.fast_af_store import get_fast_af_store
        app.state.fast_af_store = get_fast_af_store()
    except Exception:
        logger.exception("FastAFStore startup failed")

    # PROACTIVE-02: start the new proactive engine
    try:
        from omni_v2.agents.proactive_v2 import get_proactive_engine
        engine = get_proactive_engine(interval_sec=60.0)
        engine.start()
        logger.info("🟢 ProactiveEngine V2 started (60s interval, 9 rules)")
    except Exception as e:
        logger.warning(f"ProactiveEngine V2 start failed: {e}")

    # WAKEWORD-01: start the always-on "Hey OMNI" service
    try:
        from omni_v2.voice.wake_word_best import WakeWordServiceBest

        async def on_wake():
            logger.info("🟢 WakeWord: on_wake fired - OMNI is listening")
            try:
                await manager.broadcast({"type": "wake", "ts": time.time()})
                # Phase 5D: Push a notification too
                try:
                    from omni_v2.agents.notifications import get_notification_center, CAT_WAKE
                    get_notification_center().notify(
                        title="🎙 Hey OMNI",
                        body="Wake word detected. Listening...",
                        category=CAT_WAKE, priority=2, icon="🎙",
                    )
                except Exception:
                    pass
            except Exception:
                pass

        async def on_command(text: str):
            logger.info(f"🟢 WakeWord: voice command '{text}' - routing to brain")
            try:
                await manager.broadcast({"type": "voice_command", "text": text, "ts": time.time()})
                brain_inst = get_brain()
                result = await brain_inst.execute(text)
                await manager.broadcast({"type": "voice_result", "result": result, "ts": time.time()})
            except Exception as e:
                logger.error(f"on_command error: {e}")

        wake = WakeWordServiceBest(
            on_wake=lambda: asyncio.create_task(on_wake()),
            on_command=lambda text: asyncio.create_task(on_command(text)),
        )
        app.state.wake_word = wake
        if wake.is_available():
            wake.start()
            logger.info(f"🟢 WakeWord Best started with {wake.get_status()}")
        else:
            logger.info("ℹ️ WakeWord Best not available (no STT backend)")
    except Exception as e:
        logger.warning(f"WakeWord Best start failed: {e}")

    # BEST-01: TTS upgrade - edge-tts for natural voices
    try:
        from omni_v2.voice.tts_best import get_tts_best
        global_tts = get_tts_best(voice="jarvis")
        logger.info(f"🔊 TTS Best initialized: {global_tts.get_status()}")
    except Exception as e:
        logger.warning(f"TTS Best init failed: {e}")

    # BEST-02: APScheduler for cron-style tasks
    try:
        from omni_v2.agents.scheduler import get_scheduler
        async def fire_scheduled_task(task):
            logger.info(f"📅 Scheduled task firing: {task.name}")
            try:
                await manager.broadcast({"type": "scheduled_task", "task": task.name, "command": task.command, "ts": time.time()})
                brain_inst = get_brain()
                await brain_inst.execute(task.command)
            except Exception as e:
                logger.error(f"scheduled task fire: {e}")
        sched = get_scheduler(on_task_due=lambda t: asyncio.create_task(fire_scheduled_task(t)))
        app.state.scheduler = sched
        logger.info(f"⏰ Scheduler initialized: {len(sched.list_tasks())} existing tasks")
    except Exception as e:
        logger.warning(f"Scheduler init failed: {e}")

    # PHASE-5A: mDNS service discovery (laptop broadcasts, phone discovers)
    try:
        from omni_v2.network.mdns import OMNIMDNSBroadcaster
        from omni_v2.network.discovery import generate_pairing_code, make_discovery_info
        from omni_v2.agents.user_profile import get_user_profile

        # Get user name for the broadcast
        try:
            profile = get_user_profile()
            user_name = profile.get("name", "User")
        except Exception:
            user_name = "User"
        broadcast_name = f"{user_name}'s OMNI" if user_name else "OMNI"
        mdns_broadcaster = OMNIMDNSBroadcaster(
            port=8765,
            name=broadcast_name,
            capabilities=["voice", "vision", "wake_word", "memory", "personality", "marketplace"],
        )
        mdns_broadcaster.start()
        app.state.mdns_broadcaster = mdns_broadcaster
        info = make_discovery_info(broadcast_name, 8765)
        logger.info(f"📡 mDNS Broadcaster started: {info.http_url}")
        logger.info(f"📱 Mobile companion can discover on WiFi at {info.host}:{info.port}")
    except Exception as e:
        logger.warning(f"mDNS Broadcaster init failed: {e}")
        mdns_broadcaster = None

    # PHASE-5D: Notification center (in-app + web push)
    try:
        from omni_v2.agents.notifications import get_notification_center

        async def _notification_broadcast(payload, device_id=None):
            """Broadcast a notification to all (or one) WebSocket clients."""
            try:
                if device_id:
                    # Targeted — for now, all clients see it (no per-device routing yet)
                    await manager.broadcast(payload)
                else:
                    await manager.broadcast(payload)
            except Exception as e:
                logger.debug(f"Notif broadcast: {e}")

        notif_center = get_notification_center()
        app.state.notification_center = notif_center
        notif_center.broadcast = _notification_broadcast
        logger.info(f"🔔 NotificationCenter: VAPID={'enabled' if notif_center.get_vapid_public_key() else 'disabled'}, "
                    f"{notif_center.get_status()['devices_count']} devices")
    except Exception as e:
        logger.warning(f"NotificationCenter init failed: {e}")

    # PHASE-6A: Screen Watcher (Visual-First)
    try:
        from omni_v2.agents.screen_watcher import get_screen_watcher
        watcher = get_screen_watcher(interval_sec=30.0, save_screenshots=False)
        app.state.screen_watcher = watcher
        # Don't start the daemon by default — it requires a real screen.
        # The frontend can start it explicitly via /api/screen/start.
        logger.info(f"👁 ScreenWatcher ready (interval=30s, backend={watcher._cap_backend})")
    except Exception as e:
        logger.warning(f"ScreenWatcher init failed: {e}")
    print("="*70)
    print("  OMNI V3 FastAPI - Pretty Damn Good Backend")
    print(f"  REPO_ROOT: {REPO_ROOT} (portable, not D:/Omni)")
    print("  Sounddevice primary - fixes PyAudio -9999")
    print("  Profile isolated Chrome - no email leak")
    print("  Multi-agent: Planner->Executor->Monitor->Evaluator")
    print("="*70)
    brain = get_brain()
    print(f"✅ Brain ready: {brain.ready}")

@app.on_event("shutdown")
async def shutdown():
    """Stop background services so reloads/tests do not leak threads or devices."""
    fast_store = getattr(app.state, "fast_af_store", None)
    if fast_store is not None:
        try:
            fast_store.close()
        except Exception:
            logger.exception("FastAFStore shutdown failed")
    notification_center = getattr(app.state, "notification_center", None)
    if notification_center is not None:
        try:
            notification_center.shutdown()
        except Exception:
            logger.exception("Notification center shutdown failed")
    scheduler = getattr(app.state, "scheduler", None)
    if scheduler is not None:
        try:
            scheduler.shutdown()
        except Exception:
            logger.exception("Scheduler shutdown failed")
    wake = getattr(app.state, "wake_word", None)
    if wake is not None:
        try:
            wake.stop()
        except Exception:
            logger.exception("Wake-word shutdown failed")
    watcher = getattr(app.state, "screen_watcher", None)
    if watcher is not None:
        try:
            watcher.stop()
        except Exception:
            logger.exception("Screen watcher shutdown failed")
    mdns = getattr(app.state, "mdns_broadcaster", None)
    if mdns is not None:
        try:
            mdns.stop()
        except Exception:
            logger.exception("mDNS shutdown failed")

@app.get("/")
async def root():
    return {
        "name": "OMNI V3 FastAPI",
        "version": "3.1.0",
        "description": "Pretty damn good backend for Next.js beautiful neomorphism UI",
        "repo_root": str(REPO_ROOT),
        "portable": True,
        "no_hardcode": "No D:/Omni, uses Path(__file__).resolve()",
        "endpoints": ["/api/health", "/api/devices", "/api/execute", "/api/demo/{type}", "/api/test-mic", "/ws"],
        "frontend": "Next.js at http://localhost:3000 (npm run dev)",
        "fix": "sounddevice fixes -9999, RMS 0.014 = LOUD"
    }

@app.get("/api/health")
async def health():
    brain = get_brain()
    proactive_active = False
    try:
        from omni_v2.agents.proactive import get_proactive_agent
        proactive_active = get_proactive_agent()._running
    except Exception:
        pass
    return {
        "status": "ok",
        "brain_ready": brain.ready,
        "proactive_active": proactive_active,
        "repo_root": str(REPO_ROOT),
        "portable": True,
        "audio": brain.audio_mgr.get_best_name() if brain.audio_mgr else "No audio",
        "stt": brain.stt.get_status() if brain.stt else "No STT",
        "tts": brain.tts.get_status() if brain.tts else "No TTS",
        "fix": "sounddevice only, no PyAudio, no 404, no D:/Omni hardcode"
    }


# PROACTIVE-01: Proactive Engine V2 endpoints
@app.get("/api/proactive/suggestions")
async def get_proactive_suggestions():
    """Get pending proactive suggestions for the UI."""
    try:
        from omni_v2.agents.proactive_v2 import get_proactive_engine
        engine = get_proactive_engine()
        return {
            "status": "ok",
            "suggestions": engine.get_pending_suggestions(),
            "daily_count": engine._daily_suggestion_count,
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "suggestions": []}


# PHASE-1A: User Profile endpoints
@app.get("/api/user/profile")
async def get_user_profile():
    """Get the user's persistent profile."""
    try:
        from omni_v2.agents.user_profile import get_user_profile
        profile = get_user_profile()
        return {"status": "ok", "profile": profile.get_all()}
    except Exception:
        logger.exception("API operation failed")
        return api_error("Operation could not be completed", 500)


class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    pronouns: Optional[str] = None
    timezone: Optional[str] = None
    location: Optional[str] = None
    work_start_hour: Optional[int] = None
    work_end_hour: Optional[int] = None
    lunch_hour: Optional[int] = None
    favorite_voice: Optional[str] = None
    formality: Optional[str] = None
    theme: Optional[str] = None
    wake_word_sensitivity: Optional[float] = None
    proactive_frequency: Optional[str] = None
    favorite_music: Optional[str] = None
    birthday: Optional[str] = None
    hobbies: Optional[list] = None


@app.post("/api/user/profile")
async def update_user_profile(update: UserProfileUpdate):
    """Update user profile fields."""
    try:
        from omni_v2.agents.user_profile import get_user_profile
        profile = get_user_profile()
        # Only set non-None values
        payload = {k: v for k, v in update.dict().items() if v is not None}
        results = profile.set_many(**payload)
        if not all(results.values()):
            return {"status": "error", "error": "Some fields could not be set", "results": results}
        return {"status": "ok", "updated": list(payload.keys())}
    except Exception:
        logger.exception("API operation failed")
        return api_error("Operation could not be completed", 500)


@app.delete("/api/user/profile/{field}")
async def forget_user_profile_field(field: str):
    """Forget (reset) a specific profile field."""
    try:
        from omni_v2.agents.user_profile import get_user_profile
        profile = get_user_profile()
        success = profile.forget(field)
        return {"status": "ok" if success else "not_found", "field": field, "forgot": success}
    except Exception:
        logger.exception("API operation failed")
        return api_error("Operation could not be completed", 500)


@app.get("/api/user/greeting")
async def get_user_greeting():
    """Get a personalized greeting based on time + profile + history."""
    try:
        from datetime import datetime
        from omni_v2.agents.user_profile import get_user_profile
        from omni_v2.memory.session_memory import get_session_memory

        profile = get_user_profile()
        mem = get_session_memory()
        name = profile.greeting_name()
        now = datetime.now()
        hour = now.hour

        # Time-based greeting
        if 5 <= hour < 12:
            greeting = f"Good morning{', ' + name if name else ''} ☀️"
        elif 12 <= hour < 17:
            greeting = f"Good afternoon{', ' + name if name else ''}"
        elif 17 <= hour < 22:
            greeting = f"Good evening{', ' + name if name else ''}"
        else:
            greeting = f"Burning the midnight oil{', ' + name if name else ''} 🌙"

        # Yesterday's context
        yesterday_summary = ""
        yesterday = mem.get_yesterday_digest()
        if yesterday and yesterday.total_commands > 0:
            top_topic = yesterday.top_topics[0][0] if yesterday.top_topics else "various things"
            yesterday_summary = f" Yesterday you worked on {top_topic}."

        # Last seen
        last_seen = mem.get_last_seen()
        body = f"It's {now.strftime('%A, %B %d, %Y')}.{yesterday_summary} Ready for a productive day?"

        return {
            "status": "ok",
            "greeting": greeting,
            "body": body,
            "name": name,
            "has_name": bool(name),
            "has_history": bool(yesterday and yesterday.total_commands > 0),
            "last_seen": last_seen.isoformat() if last_seen else None,
        }
    except Exception:
        logger.exception("API operation failed")
        return api_error("Operation could not be completed", 500)


@app.get("/api/user/stats")
async def get_user_stats():
    """Get behavioral stats for the UI."""
    try:
        from omni_v2.agents.user_profile import get_user_profile
        from omni_v2.memory.session_memory import get_session_memory
        profile = get_user_profile()
        mem = get_session_memory()
        return {
            "status": "ok",
            "profile_stats": profile.get_stats(),
            "session_stats": mem.get_session_stats(),
            "weekly_summary": mem.get_weekly_summary(),
        }
    except Exception:
        logger.exception("API operation failed")
        return api_error("Operation could not be completed", 500)


# PHASE-1B: Session Memory endpoints
@app.get("/api/memory/sessions")
async def get_sessions(days: int = Query(default=7, ge=1, le=365)):
    """Get sessions from the last N days."""
    try:
        from omni_v2.memory.session_memory import get_session_memory
        mem = get_session_memory()
        sessions = mem.recall_sessions(days=days)
        return {
            "status": "ok",
            "sessions": [s.to_dict() for s in sessions],
            "count": len(sessions),
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "sessions": []}


@app.get("/api/memory/session/{session_id}")
async def get_session_details(session_id: str):
    """Get details for a specific session."""
    try:
        from omni_v2.memory.session_memory import get_session_memory
        mem = get_session_memory()
        sessions = mem.recall_sessions(days=30)
        for s in sessions:
            if s.id == session_id:
                return {"status": "ok", "session": s.to_dict()}
        return {"status": "not_found", "session_id": session_id}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/memory/search")
async def search_memory(q: str, days: int = Query(default=30, ge=1, le=365)):
    """Search across all sessions."""
    try:
        from omni_v2.memory.session_memory import get_session_memory
        mem = get_session_memory()
        matches = mem.search_history(q, days=days)
        return {
            "status": "ok",
            "query": q,
            "matches": [s.to_dict() for s in matches],
            "count": len(matches),
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "matches": []}


@app.get("/api/memory/today")
async def get_today_memory():
    """Get today's digest."""
    try:
        from omni_v2.memory.session_memory import get_session_memory
        mem = get_session_memory()
        digest = mem.get_today_digest()
        return {"status": "ok", "digest": digest.to_dict()}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/memory/yesterday")
async def get_yesterday_memory():
    """Get yesterday's digest."""
    try:
        from omni_v2.memory.session_memory import get_session_memory
        mem = get_session_memory()
        digest = mem.get_yesterday_digest()
        if digest:
            return {"status": "ok", "digest": digest.to_dict()}
        return {"status": "no_data", "message": "No data for yesterday"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/memory/weekly")
async def get_weekly_memory():
    """Get 7-day summary."""
    try:
        from omni_v2.memory.session_memory import get_session_memory
        mem = get_session_memory()
        summary = mem.get_weekly_summary()
        return {"status": "ok", "summary": summary}
    except Exception as e:
        return {"status": "error", "error": str(e)}


class ProactiveAction(BaseModel):
    suggestion_id: str
    action: str  # "dismiss" | "act" | "execute"


@app.post("/api/proactive/action")
async def proactive_action(req: ProactiveAction):
    """Handle a proactive suggestion action (dismiss / act / execute a command)."""
    try:
        from omni_v2.agents.proactive_v2 import get_proactive_engine
        engine = get_proactive_engine()
        if req.action == "dismiss":
            engine.dismiss(req.suggestion_id)
            return {"status": "ok", "action": "dismissed"}
        elif req.action == "act":
            engine.mark_acted_on(req.suggestion_id)
            return {"status": "ok", "action": "acted_on"}
        else:
            return {"status": "error", "error": f"Unknown action: {req.action}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


class ProactiveContext(BaseModel):
    """Push context into the engine (calendar, inbox, code, system)."""
    calendar: Optional[Dict[str, Any]] = None
    inbox: Optional[Dict[str, Any]] = None
    code: Optional[Dict[str, Any]] = None
    system: Optional[Dict[str, Any]] = None


@app.post("/api/proactive/context")
async def update_proactive_context(ctx: ProactiveContext):
    """Update the proactive engine's context (called periodically by the UI)."""
    try:
        from omni_v2.agents.proactive_v2 import get_proactive_engine
        engine = get_proactive_engine()
        payload = {k: v for k, v in ctx.dict().items() if v is not None}
        engine.update_context(**payload)
        return {"status": "ok", "context_keys": list(payload.keys())}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# SCHEDULER-01: APScheduler endpoints
class ScheduleCronReq(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    command: str = Field(min_length=1, max_length=2000)
    cron: str = Field(min_length=9, max_length=100)  # "0 9 * * 1-5" format


class ScheduleIntervalReq(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    command: str = Field(min_length=1, max_length=2000)
    seconds: Optional[int] = None
    minutes: Optional[int] = None
    hours: Optional[int] = None


class ScheduleOnceReq(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    command: str = Field(min_length=1, max_length=2000)
    run_at: str  # ISO format


@app.get("/api/scheduler/tasks")
async def list_scheduled_tasks():
    """List all scheduled tasks."""
    try:
        from omni_v2.agents.scheduler import get_scheduler
        sched = get_scheduler()
        return {"status": "ok", "tasks": sched.list_tasks()}
    except Exception as e:
        return {"status": "error", "error": str(e), "tasks": []}


@app.post("/api/scheduler/cron")
async def add_cron_task(req: ScheduleCronReq):
    """Add a cron-style task. e.g. {'name': 'morning', 'command': 'brief my day', 'cron': '0 8 * * *'}"""
    try:
        from omni_v2.agents.scheduler import get_scheduler
        sched = get_scheduler()
        task = sched.add_cron(req.name, req.command, req.cron)
        return {"status": "ok", "task_id": task.id, "name": task.name}
    except ValueError as e:
        return api_error(str(e), 400)
    except Exception:
        logger.exception("Scheduler request failed")
        return api_error("Request could not be completed", 500)


@app.post("/api/scheduler/interval")
async def add_interval_task(req: ScheduleIntervalReq):
    """Add an interval task. e.g. {'name': 'break', 'command': 'remind me to stretch', 'minutes': 30}"""
    try:
        from omni_v2.agents.scheduler import get_scheduler
        sched = get_scheduler()
        kwargs = {k: v for k, v in req.dict().items() if k not in ("name", "command") and v is not None}
        task = sched.add_interval(req.name, req.command, **kwargs)
        return {"status": "ok", "task_id": task.id, "name": task.name}
    except ValueError as e:
        return api_error(str(e), 400)
    except Exception:
        logger.exception("Scheduler request failed")
        return api_error("Request could not be completed", 500)


@app.post("/api/scheduler/once")
async def add_once_task(req: ScheduleOnceReq):
    """Add a one-shot task. e.g. {'name': 'meeting', 'command': 'remind meeting', 'run_at': '2026-07-15T15:00:00'}"""
    try:
        from datetime import datetime
        from omni_v2.agents.scheduler import get_scheduler
        sched = get_scheduler()
        run_at = datetime.fromisoformat(req.run_at)
        task = sched.add_once(req.name, req.command, run_at)
        return {"status": "ok", "task_id": task.id, "name": task.name}
    except ValueError as e:
        return api_error(str(e), 400)
    except Exception:
        logger.exception("Scheduler request failed")
        return api_error("Request could not be completed", 500)


class RemoveTaskReq(BaseModel):
    task_id: str


@app.post("/api/scheduler/remove")
async def remove_scheduled_task(req: RemoveTaskReq):
    """Remove a scheduled task by ID."""
    try:
        from omni_v2.agents.scheduler import get_scheduler
        sched = get_scheduler()
        removed = sched.remove(req.task_id)
        return {"status": "ok" if removed else "not_found", "removed": removed}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# TTS-BEST-01: Voice persona endpoints
class VoiceReq(BaseModel):
    persona: str  # "jarvis" | "friday" | "aria" | "davis" | "sara"


@app.post("/api/voice/set")
async def set_voice_persona(req: VoiceReq):
    """Change OMNI's voice persona."""
    try:
        from omni_v2.voice.tts_best import get_tts_best, VOICE_PERSONAS
        if req.persona not in VOICE_PERSONAS:
            return {"status": "error", "error": f"Unknown persona. Available: {list(VOICE_PERSONAS.keys())}"}
        tts = get_tts_best(voice=req.persona)
        tts.set_voice(req.persona)
        return {"status": "ok", "persona": req.persona, "voice": VOICE_PERSONAS[req.persona]}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/voice/personas")
async def list_voice_personas():
    """List available voice personas."""
    try:
        from omni_v2.voice.tts_best import VOICE_PERSONAS
        return {"status": "ok", "personas": VOICE_PERSONAS}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# PHASE-2: Personality endpoints
class PersonalityUpdate(BaseModel):
    formality: Optional[float] = None
    warmth: Optional[float] = None
    wit: Optional[float] = None
    verbosity: Optional[float] = None
    use_emoji: Optional[bool] = None
    use_dry_humor: Optional[bool] = None
    address_by_name: Optional[bool] = None


@app.get("/api/personality")
async def get_personality():
    """Get OMNI's personality settings."""
    try:
        from omni_v2.agents.personality import get_personality
        p = get_personality()
        return {"status": "ok", "personality": p.get_all()}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/personality")
async def update_personality(update: PersonalityUpdate):
    """Update personality dimensions."""
    try:
        from omni_v2.agents.personality import get_personality
        p = get_personality()
        payload = {k: v for k, v in update.dict().items() if v is not None}
        # Clamp values to [0, 1]
        for k in ("formality", "warmth", "wit", "verbosity"):
            if k in payload:
                payload[k] = max(0.0, min(1.0, payload[k]))
        results = p.set_many(**payload)
        return {"status": "ok", "updated": list(payload.keys())}
    except Exception as e:
        return {"status": "error", "error": str(e)}


class MoodReq(BaseModel):
    mood: str  # "helpful" | "focused" | "playful" | "concerned" | "celebratory"


@app.post("/api/personality/mood")
async def set_mood(req: MoodReq):
    """Manually set OMNI's mood."""
    try:
        from omni_v2.agents.personality import get_personality
        p = get_personality()
        valid = ("helpful", "focused", "playful", "concerned", "celebratory")
        if req.mood not in valid:
            return {"status": "error", "error": f"Invalid mood. Use: {list(valid)}"}
        p.set_mood(req.mood)
        return {"status": "ok", "mood": req.mood, "tone": p.get_mood_tone()}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/personality/test")
async def test_personality_phrase():
    """Test personality by generating a sample phrase."""
    try:
        from omni_v2.agents.personality import get_personality
        p = get_personality()
        return {
            "status": "ok",
            "acknowledgment": p.pick_acknowledgment(),
            "success": p.format_success(ms=120),
            "empathy": p.pick_failure_empathy(),
            "observation": p.observe_activity("Twitter", count=4),
            "mood": p.get_mood(),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


# PHASE-3A: Onboarding endpoints
@app.get("/api/onboarding")
async def get_onboarding_state():
    """Get the user's onboarding state."""
    try:
        from omni_v2.agents.onboarding import get_onboarding_state
        s = get_onboarding_state()
        return {"status": "ok", "onboarding": s.to_dict()}
    except Exception as e:
        return {"status": "error", "error": str(e)}


class OnboardingAdvance(BaseModel):
    name: Optional[str] = None


@app.post("/api/onboarding/advance")
async def onboarding_advance(req: OnboardingAdvance):
    """Advance to the next onboarding step. Optionally set name."""
    try:
        from omni_v2.agents.onboarding import get_onboarding_state
        s = get_onboarding_state()
        next_step = s.advance(name=req.name or "")
        # If we got a name, also set it in the user profile
        if req.name:
            try:
                from omni_v2.agents.user_profile import get_user_profile
                profile = get_user_profile()
                profile.set("name", req.name)
            except Exception:
                pass
        return {
            "status": "ok",
            "current_step": s.to_dict(),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/onboarding/skip")
async def onboarding_skip():
    """Skip onboarding."""
    try:
        from omni_v2.agents.onboarding import get_onboarding_state
        s = get_onboarding_state()
        s.skip()
        return {"status": "ok", "skipped": True}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/onboarding/reset")
async def onboarding_reset():
    """Reset onboarding (re-onboard)."""
    try:
        from omni_v2.agents.onboarding import get_onboarding_state
        s = get_onboarding_state()
        s.reset()
        return {"status": "ok", "reset": True}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# PHASE-3B: Demo mode endpoints
class DemoReq(BaseModel):
    action: str  # "start" | "stop" | "pause" | "resume" | "skip_to"
    scene_id: Optional[int] = None


# Track demo state globally
_demo_mode = None
_demo_callbacks = []

@app.post("/api/demo")
async def demo_control(req: DemoReq):
    """Control the demo mode."""
    global _demo_mode
    try:
        from omni_v2.agents.demo_mode import get_demo_mode, DEMO_SCRIPT
        if _demo_mode is None:
            async def on_scene(scene):
                import json
                # Broadcast to all WebSocket clients
                try:
                    await manager.broadcast({
                        "type": "demo_scene",
                        "scene": scene.id,
                        "title": scene.title,
                        "narration": scene.narration,
                        "action": scene.action,
                        "command": scene.command,
                        "duration_sec": scene.duration_sec,
                    })
                except Exception:
                    pass
            _demo_mode = get_demo_mode(on_scene=on_scene)
        if req.action == "start":
            _demo_mode.start()
            return {"status": "ok", "action": "started", "script_size": len(DEMO_SCRIPT)}
        elif req.action == "stop":
            _demo_mode.stop()
            return {"status": "ok", "action": "stopped"}
        elif req.action == "pause":
            _demo_mode.pause()
            return {"status": "ok", "action": "paused"}
        elif req.action == "resume":
            _demo_mode.resume()
            return {"status": "ok", "action": "resumed"}
        elif req.action == "skip_to":
            if req.scene_id is None:
                return {"status": "error", "error": "scene_id required for skip_to"}
            _demo_mode.skip_to(req.scene_id)
            return {"status": "ok", "action": "skipped", "scene_id": req.scene_id}
        return {"status": "error", "error": f"Unknown action: {req.action}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/demo/status")
async def demo_status():
    """Get demo mode status."""
    try:
        from omni_v2.agents.demo_mode import get_demo_mode, DEMO_SCRIPT
        global _demo_mode
        if _demo_mode is None:
            _demo_mode = get_demo_mode()
        return {
            "status": "ok",
            "demo": _demo_mode.get_status(),
            "script": [
                {"id": s.id, "title": s.title, "duration_sec": s.duration_sec}
                for s in DEMO_SCRIPT
            ],
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/demo/script")
async def demo_script():
    """Get the full demo script."""
    try:
        from omni_v2.agents.demo_mode import DEMO_SCRIPT
        return {
            "status": "ok",
            "script": [
                {
                    "id": s.id,
                    "title": s.title,
                    "narration": s.narration,
                    "action": s.action,
                    "command": s.command,
                    "duration_sec": s.duration_sec,
                    "shows": s.shows,
                }
                for s in DEMO_SCRIPT
            ],
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


# PHASE-3C: Stats endpoints
@app.get("/api/stats")
async def get_stats():
    """Get the full stats dashboard."""
    try:
        from omni_v2.agents.stats import get_stats_engine
        s = get_stats_engine()
        return {"status": "ok", "stats": s.get_full_dashboard()}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/stats/today")
async def get_stats_today():
    """Get today's stats."""
    try:
        from omni_v2.agents.stats import get_stats_engine
        s = get_stats_engine()
        return {"status": "ok", "today": s.get_today_stats()}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/stats/lifetime")
async def get_stats_lifetime():
    """Get lifetime stats."""
    try:
        from omni_v2.agents.stats import get_stats_engine
        s = get_stats_engine()
        return {"status": "ok", "lifetime": s.get_lifetime_stats()}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/stats/time-saved")
async def get_stats_time_saved():
    """Get estimated time saved by using OMNI."""
    try:
        from omni_v2.agents.stats import get_stats_engine
        s = get_stats_engine()
        return {"status": "ok", "time_saved": s.estimate_time_saved()}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# PHASE-4A: Vision endpoints
class VisionReq(BaseModel):
    file_path: Optional[str] = Field(default=None, max_length=1000)
    query: str = Field(default="Describe this", min_length=1, max_length=2000)
    capture_screen: bool = False


@app.post("/api/vision")
async def vision_process(req: VisionReq):
    """Process a file with multi-modal vision (image, PDF, screenshot)."""
    try:
        from omni_v2.vision.multimodal import get_vision
        v = get_vision()
        if req.capture_screen:
            result = v.process_screenshot(req.query)
        elif req.file_path:
            from omni_v2.core.paths import DATA_DIR
            from omni_v2.core.guardrails import safe_path
            safe, reason = safe_path(req.file_path, allowed_root=DATA_DIR / "vision" / "uploads")
            if not safe:
                return {"status": "error", "error": f"Path blocked: {reason}"}
            result = v.process_file(req.file_path, req.query)
        else:
            return {"status": "error", "error": "file_path or capture_screen required"}
        return {
            "status": "ok" if result.success else "error",
            "result": {
                "success": result.success,
                "file_type": result.file_type,
                "description": result.description,
                "extracted_text": result.extracted_text,
                "objects_detected": result.objects_detected,
                "metadata": result.metadata,
                "duration_ms": result.duration_ms,
                "model_used": result.model_used,
                "error": result.error,
            }
        }
    except Exception as e:
        return api_error("Request could not be completed", 500)


@app.get("/api/vision/status")
async def vision_status():
    """Get vision engine status."""
    try:
        from omni_v2.vision.multimodal import get_vision
        return {"status": "ok", "vision": get_vision().get_status()}
    except Exception:
        logger.exception("API operation failed")
        return api_error("Operation could not be completed", 500)


# PHASE-4B: Voice cloning endpoints
@app.post("/api/voice/clone/start")
async def voice_clone_start():
    """Start recording audio for voice cloning."""
    try:
        from omni_v2.voice.voice_clone import get_voice_cloner
        vc = get_voice_cloner()
        if not vc.is_available():
            return {"status": "error", "error": "Piper TTS not installed. Run: pip install piper-tts"}
        ok = vc.start_recording()
        if ok:
            return {"status": "ok", "recording": True, "message": "Speak for 30+ seconds"}
        return {"status": "error", "error": "Failed to start recording (already recording?)"}
    except Exception as e:
        return api_error("Request could not be completed", 500)


@app.post("/api/voice/clone/stop")
async def voice_clone_stop():
    """Stop recording and save the sample."""
    try:
        from omni_v2.voice.voice_clone import get_voice_cloner
        vc = get_voice_cloner()
        path = vc.stop_recording()
        if path:
            return {"status": "ok", "sample_path": str(path)}
        return {"status": "error", "error": "No recording in progress"}
    except Exception as e:
        return api_error("Request could not be completed", 500)


class VoiceTrainReq(BaseModel):
    sample_path: str = Field(min_length=1, max_length=1000)
    voice_name: Optional[str] = Field(default=None, max_length=100)


@app.post("/api/voice/clone/train")
async def voice_clone_train(req: VoiceTrainReq):
    """Train a custom voice from a recorded sample."""
    try:
        from omni_v2.voice.voice_clone import get_voice_cloner
        vc = get_voice_cloner()
        result = vc.train_voice(req.sample_path, req.voice_name)
        return result
    except Exception as e:
        return api_error("Request could not be completed", 500)


@app.get("/api/voice/clone/samples")
async def voice_clone_samples():
    """List voice samples."""
    try:
        from omni_v2.voice.voice_clone import get_voice_cloner
        return {"status": "ok", "samples": get_voice_cloner().list_samples()}
    except Exception:
        logger.exception("API operation failed")
        return api_error("Operation could not be completed", 500)


@app.get("/api/voice/clone/voices")
async def voice_clone_voices():
    """List cloned voices."""
    try:
        from omni_v2.voice.voice_clone import get_voice_cloner
        return {"status": "ok", "voices": get_voice_cloner().list_voices()}
    except Exception:
        logger.exception("API operation failed")
        return api_error("Operation could not be completed", 500)


@app.get("/api/voice/clone/status")
async def voice_clone_status():
    """Get voice clone status."""
    try:
        from omni_v2.voice.voice_clone import get_voice_cloner
        return {"status": "ok", "voice_clone": get_voice_cloner().get_status()}
    except Exception:
        logger.exception("API operation failed")
        return api_error("Operation could not be completed", 500)


# PHASE-4C: Skill Marketplace endpoints
@app.get("/api/skills/marketplace")
async def skills_marketplace(category: Optional[str] = None, search: Optional[str] = None):
    """Browse the skill marketplace."""
    try:
        from omni_v2.skills.marketplace import get_marketplace
        m = get_marketplace()
        items = m.get_index(category=category, search=search)
        return {
            "status": "ok",
            "items": items,
            "categories": m.get_categories(),
            "total": len(items),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


class SkillInstallReq(BaseModel):
    skill_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_.-]+$")


@app.post("/api/skills/install")
async def skill_install(req: SkillInstallReq):
    """Install a skill from the marketplace."""
    try:
        from omni_v2.skills.marketplace import get_marketplace
        m = get_marketplace()
        return m.install(req.skill_id)
    except Exception as e:
        return api_error("Request could not be completed", 500)


@app.post("/api/skills/uninstall")
async def skill_uninstall(req: SkillInstallReq):
    """Uninstall a skill."""
    try:
        from omni_v2.skills.marketplace import get_marketplace
        m = get_marketplace()
        ok = m.uninstall(req.skill_id)
        return {"status": "ok" if ok else "not_found", "uninstalled": ok}
    except Exception as e:
        return api_error("Request could not be completed", 500)


@app.get("/api/skills/installed")
async def skills_installed():
    """List installed skills."""
    try:
        from omni_v2.skills.marketplace import get_marketplace
        return {"status": "ok", "installed": get_marketplace().list_installed()}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/skills/updates")
async def skills_updates():
    """Check for skill updates."""
    try:
        from omni_v2.skills.marketplace import get_marketplace
        return {"status": "ok", "updates": get_marketplace().check_updates()}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/skills/marketplace/status")
async def skills_marketplace_status():
    """Get marketplace status."""
    try:
        from omni_v2.skills.marketplace import get_marketplace
        return {"status": "ok", "marketplace": get_marketplace().get_status()}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# PHASE-4D: Plugin SDK info endpoint
@app.get("/api/sdk")
async def sdk_info():
    """Info about the Plugin SDK."""
    return {
        "status": "ok",
        "sdk": {
            "name": "OMNI V3 Plugin SDK",
            "version": "1.0.0",
            "import": "from omni_v2.sdk import skill, command, ok, fail, reply",
            "example_code_path": "omni_v2/sdk/__init__.py",
            "skills_dir": "data/skills/installed/",
            "marketplace_count": 8,
        }
    }


# PHASE-5A: Network discovery endpoints
@app.get("/api/network/info")
async def get_network_info():
    """Get this OMNI brain's network info (for mobile discovery)."""
    try:
        from omni_v2.network.discovery import make_discovery_info
        # Get user name for the broadcast name
        name = "OMNI"
        try:
            from omni_v2.agents.user_profile import get_user_profile
            user_name = get_user_profile().get("name", "")
            if user_name:
                name = f"{user_name}'s OMNI"
        except Exception:
            pass
        info = make_discovery_info(name, 8765)
        return {
            "status": "ok",
            "network": info.to_dict(),
        }
    except Exception:
        logger.exception("API operation failed")
        return api_error("Operation could not be completed", 500)


@app.post("/api/network/pair")
async def generate_pairing():
    """Generate a one-time pairing code (5 min TTL) for mobile device."""
    try:
        from omni_v2.network.discovery import generate_pairing_code, make_discovery_info
        info = make_discovery_info("OMNI", 8765)
        code = generate_pairing_code(info.host, info.port, ttl_sec=300)
        return {
            "status": "ok",
            "pair": code.to_dict(),
            "uri": code.to_uri(),
            "qr_payload": make_qr_payload_for_pair(code, info),
        }
    except Exception:
        logger.exception("API operation failed")
        return api_error("Operation could not be completed", 500)


@app.get("/api/network/qr")
async def get_qr_code():
    """Get the current QR code (for phone to scan) as base64-encoded PNG."""
    try:
        from omni_v2.network.discovery import generate_pairing_code, make_discovery_info
        info = make_discovery_info("OMNI", 8765)
        code = generate_pairing_code(info.host, info.port, ttl_sec=300)
        uri = code.to_uri()
        # Try to generate a real QR code PNG if qrcode is installed
        qr_image_b64 = None
        try:
            import qrcode
            import io
            import base64
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(uri)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            qr_image_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        except ImportError:
            pass
        return {
            "status": "ok",
            "uri": uri,
            "pair": code.to_dict(),
            "qr_image_base64": qr_image_b64,
            "note": "Scan with phone or open the URI directly",
        }
    except Exception:
        logger.exception("API operation failed")
        return api_error("Operation could not be completed", 500)


def make_qr_payload_for_pair(code, info) -> str:
    """Build the QR payload string (combines pair info with brain info)."""
    import json
    return json.dumps({
        "type": "omni-discover",
        "name": info.name,
        "host": info.host,
        "port": info.port,
        "version": info.version,
        "model": info.model,
        "caps": info.capabilities,
        "pair_code": code.code,
    })


# PHASE-5B: Mobile companion — additional endpoints
import secrets as _secrets
_active_pair_codes: Dict[str, Any] = {}  # code -> {created_at, expires_at, host, port}
_device_tokens: Dict[str, Dict[str, Any]] = {}
MAX_WS_MESSAGE_BYTES = 256 * 1024


class PairingVerifyRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")

@app.post("/api/network/pair/verify")
async def verify_pairing_code(req: PairingVerifyRequest):
    """Verify a pairing code entered by a mobile device.
    Currently a soft-verify (any 6-digit number is accepted in this dev build).
    In a hardened build, the laptop would track issued codes and reject others.
    """
    code = req.code.strip()
    if not code or not code.isdigit() or len(code) != 6:
        return {"valid": False, "reason": "code must be 6 digits"}
    now = time.time()
    for issued, record in list(_active_pair_codes.items()):
        if record.get("expires_at", 0) <= now or record.get("used"):
            _active_pair_codes.pop(issued, None)
            continue
        if secrets.compare_digest(issued, code):
            record["used"] = True
            token = secrets.token_urlsafe(32)
            _device_tokens[token] = {"created_at": now, "expires_at": now + 60 * 60 * 24 * 30}
            return {"valid": True, "code": code, "token": token, "expires_at": now + 60 * 60 * 24 * 30}
    return {"valid": False, "reason": "invalid or expired code"}


@app.post("/api/voice/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    """Accept an audio blob from the mobile PWA, transcribe it, return text.
    Used by the phone's push-to-talk button.
    """
    try:
        # Read incrementally so chunked uploads cannot bypass the memory limit.
        max_audio_bytes = 10 * 1024 * 1024
        chunks = bytearray()
        while True:
            chunk = await audio.read(64 * 1024)
            if not chunk:
                break
            chunks.extend(chunk)
            if len(chunks) > max_audio_bytes:
                return {"status": "error", "error": "audio too large (max 10MB)"}
        data = bytes(chunks)
        if len(data) < 100:
            return {"status": "error", "error": "audio too small"}

        # Persist to a temp file
        import tempfile, os
        suffix = ".webm"
        if "mp4" in (audio.content_type or ""): suffix = ".m4a"
        elif "ogg" in (audio.content_type or ""): suffix = ".ogg"
        elif "wav" in (audio.content_type or ""): suffix = ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        # Try to transcribe using the brain's STT
        text = ""
        try:
            brain = get_brain()
            stt = getattr(brain, "stt", None)
            if stt and getattr(stt, "model", None):
                # Use faster-whisper directly on the file
                from faster_whisper import WhisperModel
                # If the STT engine has a transcribe_file method, use it
                if hasattr(stt, "transcribe_file"):
                    text = stt.transcribe_file(tmp_path) or ""
                else:
                    # Fallback: load a transient whisper model
                    model = WhisperModel("base.en", device="cpu", compute_type="int8")
                    segments, _ = model.transcribe(tmp_path, beam_size=5)
                    text = " ".join(seg.text for seg in segments).strip()
        except Exception as e:
            logger.warning(f"Transcribe failed: {e}")
        finally:
            try: os.unlink(tmp_path)
            except Exception: pass

        if not text:
            return {"status": "ok", "text": "", "message": "no speech detected"}

        return {"status": "ok", "text": text, "length_ms": len(data) * 1000 // 16000}
    except Exception:
        logger.exception("API operation failed")
        return api_error("Operation could not be completed", 500)


@app.get("/api/network/pair/active")
async def get_active_pair_code():
    """Return the most recent valid pairing code (for the QR page to display).
    Auto-generates one if none exists or the last one expired.
    """
    try:
        from omni_v2.network.discovery import generate_pairing_code, make_discovery_info
        info = make_discovery_info("OMNI", 8765)
        code = generate_pairing_code(info.host, info.port, ttl_sec=600)
        # Store it
        _active_pair_codes[code.code] = {
            "created_at": code.created_at,
            "expires_at": code.expires_at,
            "used": False,
            "host": info.host,
            "port": info.port,
        }
        # Prune expired
        now = time.time()
        for k in list(_active_pair_codes.keys()):
            if _active_pair_codes[k]["expires_at"] < now:
                del _active_pair_codes[k]
        return {
            "status": "ok",
            "pair": code.to_dict(),
            "name": info.name,
            "host": info.host,
            "port": info.port,
        }
    except Exception:
        logger.exception("API operation failed")
        return api_error("Operation could not be completed", 500)


# Mount the mobile PWA (Phase 5B)
# StaticFiles is mounted FIRST so it serves the file tree.
# A specific route at /mobile/qr/code.html serves a QR page with
# auto-generated pairing code (no manual params needed).
_MOBILE_DIR = REPO_ROOT / "mobile"

if _MOBILE_DIR.exists():
    # Serve the entire mobile/ directory as static assets at /mobile/
    # (index.html will be served automatically on /mobile/)
    app.mount("/mobile", StaticFiles(directory=str(_MOBILE_DIR), html=True), name="mobile")

    @app.get("/api/mobile/qr-page")
    async def mobile_qr_page_data():
        """API endpoint that returns the data needed to render a QR page.
        The frontend (qr.html) calls this to get fresh pairing code.
        """
        try:
            from omni_v2.network.discovery import generate_pairing_code, make_discovery_info
            info = make_discovery_info("OMNI", 8765)
            code = generate_pairing_code(info.host, info.port, ttl_sec=600)
            return {
                "status": "ok",
                "host": info.host,
                "port": info.port,
                "name": info.name,
                "code": code.code,
                "expires_at": code.expires_at,
                "valid": code.is_valid(),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


# PHASE-5B: Mobile WebSocket (dedicated for phone clients)
@app.websocket("/ws/mobile")
async def websocket_mobile(websocket: WebSocket):
    """Dedicated WebSocket for mobile companion clients.

    Supported message types from phone:
      - mobile_identify: handshake, identifies the device
      - text: text command, routed to brain
      - audio: base64-encoded audio blob (webm/ogg/m4a/wav), transcribed then executed
      - voice: alias for text (pre-transcribed)
      - location: lat/lon push for geofencing
      - ping: heartbeat
    """
    ws_token = websocket.query_params.get("token", "")
    if OMNI_API_TOKEN and not (secrets.compare_digest(ws_token, OMNI_API_TOKEN) or ws_token in _device_tokens):
        await websocket.close(code=1008, reason="Authentication required")
        return
    await manager.connect(websocket)
    mobile_meta = {"device": "unknown", "ua": "", "paired": False, "connected_at": time.time()}
    try:
        await websocket.send_json({
            "type": "welcome",
            "brain": "OMNI",
            "ts": time.time(),
            "endpoints": {
                "execute": "/api/execute",
                "transcribe": "/api/voice/transcribe",
                "network": "/api/network/info",
                "pair": "/api/network/pair",
            }
        })
        while True:
            data = await websocket.receive_text()
            if len(data.encode("utf-8")) > MAX_WS_MESSAGE_BYTES:
                await websocket.close(code=1009, reason="Message too large")
                return
            try:
                import json, base64, tempfile, os
                msg = json.loads(data)
                msg_type = msg.get("type")
                if msg_type == "ping":
                    await websocket.send_json({"type": "pong", "ts": time.time()})
                elif msg_type == "mobile_identify":
                    mobile_meta.update({
                        "device": msg.get("device", "unknown"),
                        "ua": (msg.get("ua") or "")[:200],
                        "paired": bool(msg.get("paired", False)),
                    })
                    # Register the device with the notification center
                    try:
                        from omni_v2.agents.notifications import get_notification_center
                        center = get_notification_center()
                        did = f"ws_{id(websocket)}"
                        # If the client sent a real device_id, use it
                        if msg.get("device_id"):
                            did = msg["device_id"]
                        center.touch_device(did, capabilities=msg.get("capabilities", []))
                        mobile_meta["device_id"] = did
                    except Exception:
                        mobile_meta["device_id"] = f"ws_{id(websocket)}"
                    logger.info(f"📱 Mobile identified: {mobile_meta['device']} (paired={mobile_meta['paired']})")
                    await websocket.send_json({
                        "type": "identified",
                        "brain": "OMNI",
                        "device_id": mobile_meta["device_id"],
                        "ts": time.time(),
                    })
                elif msg_type == "text":
                    text = (msg.get("text") or "").strip()
                    if not text:
                        await websocket.send_json({"type": "error", "error": "empty text"})
                        continue
                    try:
                        await websocket.send_json({"type": "thinking", "ts": time.time()})
                        brain_inst = get_brain()
                        result = await brain_inst.execute(text)
                        await websocket.send_json({
                            "type": "message",
                            "text": result.get("message", "done."),
                            "logs": result.get("logs", []),
                            "success": result.get("success", True),
                            "ts": time.time(),
                        })
                    except Exception as e:
                        await websocket.send_json({"type": "error", "error": str(e)})
                elif msg_type == "audio":
                    audio_b64 = msg.get("data", "")
                    fmt = msg.get("format", "webm")
                    if not audio_b64:
                        await websocket.send_json({"type": "error", "error": "empty audio"})
                        continue
                    try:
                        audio_bytes = base64.b64decode(audio_b64)
                        suffix = {"webm": ".webm", "ogg": ".ogg", "m4a": ".m4a", "mp4": ".m4a", "wav": ".wav"}.get(fmt, ".webm")
                        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                            tmp.write(audio_bytes)
                            tmp_path = tmp.name
                        text = ""
                        try:
                            from faster_whisper import WhisperModel
                            model = WhisperModel("base.en", device="cpu", compute_type="int8")
                            segments, _ = model.transcribe(tmp_path, beam_size=5)
                            text = " ".join(seg.text for seg in segments).strip()
                        except Exception as e:
                            logger.warning(f"WS audio transcribe failed: {e}")
                        finally:
                            try: os.unlink(tmp_path)
                            except Exception: pass
                        if text:
                            await websocket.send_json({"type": "transcript", "text": text, "ts": time.time()})
                            brain_inst = get_brain()
                            result = await brain_inst.execute(text)
                            await websocket.send_json({
                                "type": "message",
                                "text": result.get("message", "done."),
                                "logs": result.get("logs", []),
                                "success": result.get("success", True),
                                "ts": time.time(),
                            })
                        else:
                            await websocket.send_json({"type": "error", "error": "no speech detected"})
                    except Exception as e:
                        await websocket.send_json({"type": "error", "error": str(e)})
                elif msg_type == "voice":
                    text = msg.get("text", "")
                    if text:
                        try:
                            brain_inst = get_brain()
                            result = await brain_inst.execute(text)
                            await websocket.send_json({
                                "type": "voice_result",
                                "result": result,
                                "ts": time.time(),
                            })
                        except Exception as e:
                            await websocket.send_json({"type": "error", "error": str(e)})
                elif msg_type == "location":
                    lat = msg.get("lat")
                    lon = msg.get("lon")
                    accuracy = msg.get("accuracy_m")
                    logger.info(f"📍 Mobile location: ({lat}, {lon}) ±{accuracy}m")
                    fired = []
                    try:
                        from omni_v2.agents.geofence import get_geofence_engine
                        geo = get_geofence_engine()
                        fired = geo.update_location(lat=lat, lon=lon,
                                                     accuracy_m=accuracy, source="phone-ws")
                        # Also push into proactive context
                        from omni_v2.agents.proactive_v2 import get_proactive_engine
                        get_proactive_engine().update_context(
                            location={"lat": lat, "lon": lon},
                        )
                    except Exception as e:
                        logger.warning(f"Geofence update failed: {e}")
                    # Execute any fired rules
                    for ev in fired:
                        try:
                            brain_inst = get_brain()
                            await brain_inst.execute(ev.command)
                            logger.info(f"📍 Geofence fired (WS): {ev.place_name}/{ev.event} -> {ev.command}")
                        except Exception as e:
                            logger.warning(f"Geofence exec failed: {e}")
                    # Send fired events to the phone
                    if fired:
                        for ev in fired:
                            await websocket.send_json({
                                "type": "geofence_event",
                                "event": ev.to_dict(),
                                "ts": time.time(),
                            })
                    await websocket.send_json({
                        "type": "location_ack",
                        "fired_count": len(fired),
                        "ts": time.time(),
                    })
                else:
                    await websocket.send_json({"type": "echo", "data": msg})
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "error": "Invalid JSON"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Mobile WS error: {e}")
        manager.disconnect(websocket)


# PHASE-5D: Notification Center endpoints
class PushSubscribeReq(BaseModel):
    device_id: str
    endpoint: str
    p256dh: str
    auth: str
    user_agent: str = ""
    paired: bool = False
    capabilities: list = []


class NotificationCreateReq(BaseModel):
    title: str
    body: str = ""
    category: str = "info"
    priority: int = 1
    icon: str = "🔔"
    tag: str = ""
    dedup_key: str = ""
    expires_sec: float = 0


class PrefsUpdateReq(BaseModel):
    enabled: Optional[bool] = None
    muted_categories: Optional[list] = None
    dnd_enabled: Optional[bool] = None
    dnd_start_hour: Optional[int] = None
    dnd_end_hour: Optional[int] = None
    min_priority: Optional[int] = None
    play_sound: Optional[bool] = None
    show_preview: Optional[bool] = None


class SnoozeReq(BaseModel):
    minutes: float = 30
    reason: str = ""


@app.get("/api/notifications/status")
async def notifications_status():
    try:
        from omni_v2.agents.notifications import get_notification_center
        return {"status": "ok", "notifications": get_notification_center().get_status()}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/notifications/dashboard")
async def notifications_dashboard():
    try:
        from omni_v2.agents.notifications import get_notification_center
        return {"status": "ok", "dashboard": get_notification_center().get_full_dashboard()}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/notifications")
async def list_notifications(limit: int = Query(default=50, ge=1, le=500), category: Optional[str] = None,
                              unread_only: bool = False):
    try:
        from omni_v2.agents.notifications import get_notification_center
        notifs = get_notification_center().list_notifications(
            limit=limit, category=category, unread_only=unread_only,
        )
        return {
            "status": "ok",
            "notifications": [n.to_dict() for n in notifs],
            "count": len(notifs),
            "unread_count": get_notification_center().get_unread_count(),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


# IMPORTANT: specific paths must be declared BEFORE the catch-all
# /api/notifications/{notif_id} route, otherwise FastAPI routes
# /vapid and /devices to the notif_id parameter route (404).
@app.get("/api/notifications/vapid")
async def get_vapid_public_key():
    """Get the VAPID public key for Web Push subscription."""
    try:
        from omni_v2.agents.notifications import get_notification_center
        info = get_notification_center().get_vapid_info()
        return {"status": "ok", "vapid": info}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/notifications/devices")
async def list_devices_endpoint():
    try:
        from omni_v2.agents.notifications import get_notification_center
        devices = get_notification_center().list_devices()
        return {"status": "ok", "devices": [d.to_dict() for d in devices], "count": len(devices)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/notifications/subscribe")
async def subscribe_push(req: PushSubscribeReq):
    """Register a device's web-push subscription."""
    try:
        from omni_v2.agents.notifications import get_notification_center
        device = get_notification_center().register_device(
            device_id=req.device_id, endpoint=req.endpoint,
            p256dh=req.p256dh, auth=req.auth,
            user_agent=req.user_agent, paired=req.paired,
            capabilities=req.capabilities,
        )
        return {"status": "ok", "device": device.to_dict()}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.delete("/api/notifications/subscribe/{device_id}")
async def unsubscribe_push(device_id: str):
    try:
        from omni_v2.agents.notifications import get_notification_center
        ok = get_notification_center().unregister_device(device_id)
        return {"status": "ok" if ok else "not_found", "removed": ok}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# PHASE-5E: Notification preferences + snooze + export
@app.get("/api/notifications/prefs")
async def get_notification_prefs_endpoint():
    try:
        from omni_v2.agents.notification_prefs import get_notification_prefs
        prefs = get_notification_prefs()
        return {"status": "ok", "prefs": prefs.get_all(), "snooze": prefs.get_snooze(), "status_full": prefs.get_status()}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/notifications/prefs")
async def update_notification_prefs(req: PrefsUpdateReq):
    try:
        from omni_v2.agents.notification_prefs import get_notification_prefs
        prefs = get_notification_prefs()
        payload = {k: v for k, v in req.dict().items() if v is not None}
        results = prefs.update(**payload)
        return {"status": "ok", "updated": list(payload.keys()), "results": results}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/notifications/prefs/reset")
async def reset_notification_prefs():
    try:
        from omni_v2.agents.notification_prefs import get_notification_prefs
        get_notification_prefs().reset_all()
        return {"status": "ok", "reset": True}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/notifications/snooze")
async def snooze_notifications(req: SnoozeReq):
    """Snooze all notifications for N minutes."""
    try:
        from omni_v2.agents.notification_prefs import get_notification_prefs
        prefs = get_notification_prefs()
        state = prefs.snooze_for(req.minutes, req.reason)
        return {
            "status": "ok",
            "snooze": state.to_dict(),
            "message": f"🔕 Snoozed for {req.minutes} min",
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.delete("/api/notifications/snooze")
async def unsnooze_notifications():
    try:
        from omni_v2.agents.notification_prefs import get_notification_prefs
        ok = get_notification_prefs().unsnooze()
        return {"status": "ok", "unsnoozed": ok}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/notifications/export")
async def export_notifications(format: str = "json"):
    """Export notification history as JSON or CSV."""
    try:
        from omni_v2.agents.notifications import get_notification_center
        center = get_notification_center()
        items = center.list_notifications(limit=1000)
        if format == "csv":
            # Build CSV
            import io, csv
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(["id", "ts", "iso", "title", "body", "category", "priority", "read", "tag"])
            for n in items:
                from datetime import datetime
                iso = datetime.fromtimestamp(n.ts).isoformat() if n.ts else ""
                writer.writerow([n.id, n.ts, iso, n.title, n.body, n.category, n.priority, n.read, n.tag])
            from fastapi.responses import Response
            return Response(
                content=buf.getvalue(),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=omni-notifications.csv"},
            )
        # JSON default
        from fastapi.responses import Response
        import json
        return Response(
            content=json.dumps([n.to_dict() for n in items], indent=2, ensure_ascii=False),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=omni-notifications.json"},
        )
    except Exception as e:
        return {"status": "error", "error": str(e)}


# PHASE-5E: Snooze tool registration
try:
    from omni_v2.tools import snooze as _snooze_tool
    logger.info("🔕 snooze tool available")
except Exception as e:
    logger.warning(f"snooze tool not loaded: {e}")


@app.get("/api/notifications/{notif_id}")
async def get_notification(notif_id: str):
    try:
        from omni_v2.agents.notifications import get_notification_center
        n = get_notification_center().get_notification(notif_id)
        if not n:
            return {"status": "not_found", "notif_id": notif_id}
        return {"status": "ok", "notification": n.to_dict()}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/notifications/{notif_id}/read")
async def mark_notification_read(notif_id: str):
    try:
        from omni_v2.agents.notifications import get_notification_center
        ok = get_notification_center().mark_read(notif_id)
        return {"status": "ok" if ok else "not_found", "marked": ok}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/notifications/read-all")
async def mark_all_read(category: Optional[str] = None):
    try:
        from omni_v2.agents.notifications import get_notification_center
        n = get_notification_center().mark_all_read(category=category)
        return {"status": "ok", "marked": n}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/notifications")
async def create_notification(req: NotificationCreateReq):
    """Manually create a notification (e.g. for tests or external triggers)."""
    try:
        from omni_v2.agents.notifications import get_notification_center
        notif = get_notification_center().notify(
            title=req.title, body=req.body, category=req.category,
            priority=req.priority, icon=req.icon, tag=req.tag,
            dedup_key=req.dedup_key,
            expires_sec=req.expires_sec,
        )
        return {"status": "ok", "notification": notif.to_dict()}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.delete("/api/notifications")
async def clear_notifications(category: Optional[str] = None):
    try:
        from omni_v2.agents.notifications import get_notification_center
        n = get_notification_center().clear(category=category)
        return {"status": "ok", "cleared": n}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# PHASE-5D: "Send to my phone" tool registration
try:
    from omni_v2.tools import send_to_phone as _send_to_phone_tool
    # Auto-register the tool with the brain if a registry exists
    # The brain will pick it up via the standard plugin loader
    logger.info("📱 send_to_phone tool available")
except Exception as e:
    logger.warning(f"send_to_phone tool not loaded: {e}")


# PHASE-5C: Geofence endpoints
# These let the phone (or any client) push GPS coordinates,
# and the engine fires rules based on arrival/departure/dwell.
class GeofencePlaceReq(BaseModel):
    name: str
    lat: float
    lon: float
    radius_m: float = 100.0
    icon: str = "📍"
    address: str = ""
    notes: str = ""


class GeofenceRuleReq(BaseModel):
    place_id: str
    event: str          # "arrive" | "depart" | "dwell"
    command: str
    label: str = ""
    cooldown_sec: float = 1800.0
    dwell_sec: float = 300.0


class GeofenceLocationReq(BaseModel):
    lat: float
    lon: float
    accuracy_m: Optional[float] = None
    source: str = "phone"


@app.get("/api/geofence/status")
async def geofence_status():
    """Get geofence engine status (places, rules, current location)."""
    try:
        from omni_v2.agents.geofence import get_geofence_engine
        return {"status": "ok", "geofence": get_geofence_engine().get_status()}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/geofence/dashboard")
async def geofence_dashboard():
    """Full geofence dashboard (places, rules, events, current)."""
    try:
        from omni_v2.agents.geofence import get_geofence_engine
        return {"status": "ok", "dashboard": get_geofence_engine().get_full_dashboard()}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/geofence/places")
async def geofence_list_places():
    try:
        from omni_v2.agents.geofence import get_geofence_engine
        places = get_geofence_engine().list_places()
        return {"status": "ok", "places": [p.to_dict() for p in places], "count": len(places)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/geofence/places")
async def geofence_add_place(req: GeofencePlaceReq):
    try:
        from omni_v2.agents.geofence import get_geofence_engine
        place = get_geofence_engine().add_place(
            name=req.name, lat=req.lat, lon=req.lon,
            radius_m=req.radius_m, icon=req.icon,
            address=req.address, notes=req.notes,
        )
        return {"status": "ok", "place": place.to_dict()}
    except Exception as e:
        return api_error("Geofence operation failed", 500)


@app.post("/api/geofence/places/{place_id}/update")
async def geofence_update_place(place_id: str, req: GeofencePlaceReq):
    try:
        from omni_v2.agents.geofence import get_geofence_engine
        place = get_geofence_engine().update_place(
            place_id, name=req.name, lat=req.lat, lon=req.lon,
            radius_m=req.radius_m, icon=req.icon,
            address=req.address, notes=req.notes,
        )
        if not place:
            return {"status": "not_found", "place_id": place_id}
        return {"status": "ok", "place": place.to_dict()}
    except Exception as e:
        return api_error("Geofence operation failed", 500)


@app.delete("/api/geofence/places/{place_id}")
async def geofence_remove_place(place_id: str):
    try:
        from omni_v2.agents.geofence import get_geofence_engine
        ok = get_geofence_engine().remove_place(place_id)
        return {"status": "ok" if ok else "not_found", "removed": ok}
    except Exception as e:
        return api_error("Geofence operation failed", 500)


@app.get("/api/geofence/rules")
async def geofence_list_rules(place_id: Optional[str] = None):
    try:
        from omni_v2.agents.geofence import get_geofence_engine
        rules = get_geofence_engine().list_rules(place_id=place_id)
        # Enrich with place name
        result = []
        for r in rules:
            d = r.to_dict()
            place = get_geofence_engine().get_place(r.place_id)
            d["place_name"] = place.name if place else "(deleted)"
            d["place_icon"] = place.icon if place else "❓"
            result.append(d)
        return {"status": "ok", "rules": result, "count": len(result)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/geofence/rules")
async def geofence_add_rule(req: GeofenceRuleReq):
    try:
        from omni_v2.agents.geofence import get_geofence_engine
        rule = get_geofence_engine().add_rule(
            place_id=req.place_id, event=req.event, command=req.command,
            label=req.label, cooldown_sec=req.cooldown_sec, dwell_sec=req.dwell_sec,
        )
        if not rule:
            return {"status": "not_found", "error": f"place {req.place_id} not found"}
        return {"status": "ok", "rule": rule.to_dict()}
    except ValueError as e:
        return api_error(str(e), 400)
    except Exception as e:
        return api_error("Geofence operation failed", 500)


@app.delete("/api/geofence/rules/{rule_id}")
async def geofence_remove_rule(rule_id: str):
    try:
        from omni_v2.agents.geofence import get_geofence_engine
        ok = get_geofence_engine().remove_rule(rule_id)
        return {"status": "ok" if ok else "not_found", "removed": ok}
    except Exception as e:
        return api_error("Geofence operation failed", 500)


@app.post("/api/geofence/location")
async def geofence_update_location(req: GeofenceLocationReq):
    """Push a location update from the phone (or any client).
    Returns any geofence events fired by this update.
    """
    try:
        from omni_v2.agents.geofence import get_geofence_engine
        engine = get_geofence_engine()
        fired = engine.update_location(
            lat=req.lat, lon=req.lon, accuracy_m=req.accuracy_m, source=req.source,
        )
        # Broadcast to all WebSocket clients
        try:
            for ev in fired:
                await manager.broadcast({
                    "type": "geofence_event",
                    "event": ev.to_dict(),
                    "ts": time.time(),
                })
                # Also create a notification for the fired event (Phase 5D)
                try:
                    from omni_v2.agents.notifications import get_notification_center, CAT_GEOFENCE
                    get_notification_center().notify(
                        title=f"📍 {ev.place_name}",
                        body=f"{ev.event.capitalize()} → {ev.command}",
                        category=CAT_GEOFENCE,
                        priority=1,
                        icon="📍",
                        dedup_key=f"geo_{ev.id}",
                        data={"place_id": ev.place_id, "event": ev.event, "command": ev.command},
                    )
                except Exception:
                    pass
            # Also push current location to all clients
            current = engine.get_current_location()
            current_place = engine.get_current_place()
            await manager.broadcast({
                "type": "location_update",
                "location": current.to_dict() if current else None,
                "current_place": current_place.to_dict() if current_place else None,
                "ts": time.time(),
            })
        except Exception:
            pass
        # Execute the fired commands via the brain
        executed = []
        for ev in fired:
            try:
                brain = get_brain()
                result = await brain.execute(ev.command)
                executed.append({
                    "event": ev.to_dict(),
                    "result": result,
                })
                logger.info(f"📍 Geofence fired: {ev.place_name}/{ev.event} -> {ev.command}")
            except Exception as e:
                logger.warning(f"Geofence execute failed for {ev.command}: {e}")
        return {
            "status": "ok",
            "fired": [ev.to_dict() for ev in fired],
            "executed": executed,
        }
    except Exception as e:
        return api_error("Geofence operation failed", 500)


@app.get("/api/geofence/location")
async def geofence_current_location():
    """Get the most recent location + which place the user is at (if any)."""
    try:
        from omni_v2.agents.geofence import get_geofence_engine
        engine = get_geofence_engine()
        loc = engine.get_current_location()
        place = engine.get_current_place()
        return {
            "status": "ok",
            "location": loc.to_dict() if loc else None,
            "current_place": place.to_dict() if place else None,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/geofence/location/history")
async def geofence_location_history(limit: int = Query(default=50, ge=1, le=500)):
    try:
        from omni_v2.agents.geofence import get_geofence_engine
        history = get_geofence_engine().get_location_history(limit=limit)
        return {"status": "ok", "history": [h.to_dict() for h in history], "count": len(history)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/geofence/events")
async def geofence_recent_events(limit: int = Query(default=20, ge=1, le=500)):
    try:
        from omni_v2.agents.geofence import get_geofence_engine
        events = get_geofence_engine().get_recent_events(limit=limit)
        return {"status": "ok", "events": [e.to_dict() for e in events], "count": len(events)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/geofence/seed")
async def geofence_seed_samples():
    """Add a few sample places (Home, Work, Gym) for first-time users.
    Skips any that already exist (by name)."""
    try:
        from omni_v2.agents.geofence import get_geofence_engine, SAMPLE_PLACES
        engine = get_geofence_engine()
        existing_names = {p.name.lower() for p in engine.places.values()}
        # Sample coords (just for shape — user must edit lat/lon for real use)
        sample_coords = {
            "home": (33.6844, 73.0479),       # Islamabad-ish
            "work": (33.6934, 73.0589),
            "gym": (33.6794, 73.0429),
        }
        added = []
        for sp in SAMPLE_PLACES:
            if sp["name"].lower() in existing_names:
                continue
            lat, lon = sample_coords.get(sp["name"].lower(), (33.6844, 73.0479))
            p = engine.add_place(name=sp["name"], lat=lat, lon=lon,
                                 icon=sp.get("icon", "📍"), radius_m=150.0,
                                 address="(edit me)", notes="Sample place — update lat/lon to your real location")
            added.append(p.to_dict())
        return {"status": "ok", "added": added, "count": len(added)}
    except Exception as e:
        return api_error("Geofence operation failed", 500)


@app.post("/api/geofence/clear-events")
async def geofence_clear_events():
    try:
        from omni_v2.agents.geofence import get_geofence_engine
        n = get_geofence_engine().clear_events()
        return {"status": "ok", "cleared": n}
    except Exception as e:
        return api_error("Geofence operation failed", 500)


@app.post("/api/geofence/reset")
async def geofence_reset_all():
    """Wipe all places, rules, events, location. DESTRUCTIVE."""
    try:
        from omni_v2.agents.geofence import get_geofence_engine
        get_geofence_engine().reset_all()
        return {"status": "ok", "reset": True}
    except Exception as e:
        return api_error("Geofence operation failed", 500)



# PHASE-6A: Screen Watcher (Visual-First)
@app.get("/api/screen/status")
async def screen_status():
    """Get screen watcher status (running, backend, current scene)."""
    try:
        from omni_v2.agents.screen_watcher import get_screen_watcher
        return {"status": "ok", "screen": get_screen_watcher().get_status()}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/screen/context")
async def screen_context():
    """Get the current context dictionary (for the proactive engine)."""
    try:
        from omni_v2.agents.screen_watcher import get_screen_watcher
        return {"status": "ok", "context": get_screen_watcher().get_context()}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/screen/dashboard")
async def screen_dashboard():
    """Full screen dashboard (status + context + recent scenes)."""
    try:
        from omni_v2.agents.screen_watcher import get_screen_watcher
        return {"status": "ok", "dashboard": get_screen_watcher().get_full_dashboard()}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/screen/recent")
async def screen_recent(limit: int = Query(default=20, ge=1, le=500)):
    """List the N most recent scenes."""
    try:
        from omni_v2.agents.screen_watcher import get_screen_watcher
        scenes = get_screen_watcher().get_recent_scenes(limit=limit)
        return {"status": "ok", "scenes": [s.to_dict() for s in scenes], "count": len(scenes)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/screen/start")
async def screen_start():
    """Start the screen watcher daemon."""
    try:
        from omni_v2.agents.screen_watcher import get_screen_watcher
        get_screen_watcher().start()
        return {"status": "ok", "started": True}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/screen/stop")
async def screen_stop():
    """Stop the screen watcher daemon."""
    try:
        from omni_v2.agents.screen_watcher import get_screen_watcher
        get_screen_watcher().stop()
        return {"status": "ok", "stopped": True}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/screen/capture")
async def screen_capture():
    """Manually trigger a screen capture (returns the current scene)."""
    try:
        from omni_v2.agents.screen_watcher import get_screen_watcher
        watcher = get_screen_watcher()
        watcher._tick()
        scene = watcher.get_current_scene()
        return {"status": "ok", "scene": scene.to_dict() if scene else None}
    except Exception as e:
        return {"status": "error", "error": str(e)}


class ScreenClassifyReq(BaseModel):
    app: str = ""
    title: str = ""


@app.post("/api/screen/classify")
async def screen_classify(req: "ScreenClassifyReq"):
    """Classify a window title (no state, just the classifier)."""
    try:
        from omni_v2.agents.screen_watcher import classify_window
        return {"status": "ok", "activity": classify_window(req.app, req.title)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/devices")
async def devices():
    brain = get_brain()
    return brain.get_devices()

@app.post("/api/execute", response_model=ExecuteResponse)
async def execute(request: Request, req: ExecuteRequest):
    # SMOKE-03 fix: reject empty command with 400
    if not req.command or not req.command.strip():
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": "Command cannot be empty",
                "logs": ["[Error] Empty command rejected"],
                "steps": 0,
                "mock": False
            }
        )
    # GUARD-04: rate limit per client
    client_key = request.client.host if request.client else "unknown"
    rl_ok, rl_err = _rate_limiter.check(client_key)
    if not rl_ok:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=429,
            content={
                "success": False,
                "message": rl_err,
                "logs": [f"[Guardrail] {rl_err}"],
                "steps": 0,
                "mock": False
            }
        )
    # GUARD-05: prompt injection scan (log only, don't block — judges will try this)
    try:
        from omni_v2.core.guardrails import scan_prompt_injection
        inj, inj_msg = scan_prompt_injection(req.command)
        if inj:
            logger.warning(f"[Guardrail] Prompt injection attempt: {inj_msg} | cmd='{req.command[:80]}'")
    except ImportError:
        pass
    # PHASE-1: record this command in session memory + profile
    try:
        from omni_v2.memory.session_memory import get_session_memory
        from omni_v2.agents.user_profile import get_user_profile
        mem = get_session_memory()
        mem.record_command(req.command)
        profile = get_user_profile()
        profile.record_command(req.command)
    except Exception:
        pass  # don't let memory failures break the command
    brain = get_brain()
    result = await brain.execute(req.command)
    return result


@app.post("/api/execute/stream")
async def execute_stream(request: Request, req: ExecuteRequest):
    """
    Streaming version of /api/execute.
    Returns Server-Sent Events so the UI can show the LLM's actual
    reasoning tokens streaming in real-time.

    Events:
      - event: thinking, data: <token>
      - event: tool_call, data: <JSON {tool, args, result}>
      - event: final, data: <JSON {message, success, logs, ...}>
    """
    from fastapi.responses import StreamingResponse
    if not req.command or not req.command.strip():
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=400,
            content={"error": "Command cannot be empty"}
        )

    rl_ok, rl_err = _rate_limiter.check(request.client.host if request.client else "unknown")
    if not rl_ok:
        return JSONResponse(status_code=429, content={"error": rl_err})

    async def event_stream():
        import asyncio
        from omni_v2.llm.brain import get_brain as _get_brain
        brain_inst = _get_brain()
        # Execute exactly once. The prior implementation called think() and then execute(),
        # which duplicated side effects. Thought streaming will be added through the brain callback.
        # Now run the actual execution
        brain = get_brain()
        result = await brain.execute(req.command)
        yield f"event: final\ndata: {json.dumps(result)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.get("/api/demo/{demo_type}")
async def demo(demo_type: str):
    brain = get_brain()
    # SMOKE-04 fix: 404 for unknown demo types
    valid_types = {"accessibility", "chain", "business"}
    if demo_type not in valid_types:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=404,
            content={
                "error": f"Unknown demo type '{demo_type}'",
                "valid_types": sorted(valid_types),
                "hint": "Use /api/demo/accessibility, /api/demo/chain, or /api/demo/business"
            }
        )
    result = brain.get_demo(demo_type)
    if "error" in result:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content=result)
    return result

@app.post("/api/test-mic")
async def test_mic():
    brain = get_brain()
    # SMOKE-09 fix: don't even try to test mic if no audio backend
    if not _pyaudio_available() and not _sounddevice_available():
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "error": "No audio backend available for mic test",
                "hint": "pip install sounddevice (preferred) or pyaudio",
                "available_backends": _available_audio_backends()
            }
        )
    result = brain.test_mic() if hasattr(brain, 'test_mic') else {}
    if not isinstance(result, dict):
        result = {"message": str(result)}

    # API-BUG-02 fix: always include status/data/error keys
    status = "idle"
    last_text = None
    rms = result.get("rms", 0.0)
    error_msg = result.get("error")

    if brain.voice_pipeline:
        status = getattr(brain.voice_pipeline, "current_status", "idle")
        auto_txt = getattr(brain.voice_pipeline, "last_auto_text", None)
        if auto_txt:
            last_text = auto_txt
            brain.voice_pipeline.last_auto_text = None
        if hasattr(brain.voice_pipeline, "last_rms") and brain.voice_pipeline.last_rms > 0:
            rms = brain.voice_pipeline.last_rms

    return {
        "status": "ok" if not error_msg else "error",
        "data": {
            "rms": rms,
            "max": result.get("max", 0),
            "device": result.get("device"),
            "message": result.get("message", ""),
            "backend": result.get("backend", "unknown"),
            "last_auto_text": last_text,
            "current_pipeline_status": status,
        },
        "error": error_msg,
    }


def _sounddevice_available() -> bool:
    try:
        import sounddevice  # noqa
        return True
    except Exception:
        return False

@app.post("/api/ptt/start")
async def ptt_start():
    brain = get_brain()
    if not brain.voice_pipeline:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={
                "error": "Voice pipeline not available",
                "hint": "Check that sounddevice is installed and a mic is connected",
                "status": "error"
            }
        )
    # SMOKE-01 fix: check if pipeline is operationally ready
    is_op = getattr(brain.voice_pipeline, 'is_operational', None)
    if is_op is not None:
        operational = is_op()
    else:
        operational = getattr(brain.voice_pipeline, 'use_sounddevice', False) or _pyaudio_available()
    if not operational:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={
                "error": "No audio backend available",
                "hint": "pip install sounddevice (preferred) or pyaudio",
                "status": "error",
                "available_backends": _available_audio_backends()
            }
        )
    try:
        brain.voice_pipeline.start()
        return {"status": "recording", "message": "Recording started - speak LOUD 1 inch!"}
    except Exception as e:
        return {"error": str(e), "status": "error"}


def _pyaudio_available() -> bool:
    try:
        import pyaudio  # noqa
        return True
    except Exception:
        return False


def _available_audio_backends() -> list:
    backs = []
    try:
        import sounddevice  # noqa
        backs.append("sounddevice")
    except Exception:
        pass
    if _pyaudio_available():
        backs.append("pyaudio")
    return backs


@app.post("/api/ptt/stop")
async def ptt_stop():
    brain = get_brain()
    if not brain.voice_pipeline:
        # API-BUG-01 fix: return clear error and 503-ish shape
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={
                "error": "Voice pipeline not available",
                "hint": "Check that sounddevice is installed and a mic is connected",
                "status": "error"
            }
        )
    # SMOKE-02 fix: also check operational readiness (not just None)
    is_op = getattr(brain.voice_pipeline, 'is_operational', None)
    if is_op is not None:
        operational = is_op()
    else:
        operational = getattr(brain.voice_pipeline, 'use_sounddevice', False) or _pyaudio_available()
    if not operational:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={
                "error": "No audio backend available",
                "hint": "pip install sounddevice (preferred) or pyaudio",
                "status": "error",
                "available_backends": _available_audio_backends()
            }
        )
    if not brain.stt or not getattr(brain.stt, 'model', None):
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={
                "error": "STT engine not loaded",
                "hint": "pip install faster-whisper==1.0.3",
                "status": "error"
            }
        )
    try:
        brain.voice_pipeline.stop()
        # Wait a bit
        await asyncio.sleep(0.5)
        audio = brain.voice_pipeline._get_audio() if hasattr(brain.voice_pipeline, '_get_audio') else None
        text = None
        message = "No audio captured"
        rms = 0
        max_v = 0

        if audio is not None and len(audio) > 0:
            import numpy as np
            arr = np.array(audio)
            rms = float((arr**2).mean()**0.5) if len(arr) > 0 else 0
            max_v = float(abs(arr).max()) if len(arr) > 0 else 0

            text = brain.stt.transcribe(arr)
            if text:
                # Execute as command
                result = await brain.execute(text)
                message = result.get("message", "")
                return {
                    "status": "ok",
                    "text": text,
                    "message": message,
                    "rms": rms,
                    "max": max_v,
                    "logs": result.get("logs", [])
                }
            else:
                message = f"Didn't catch - RMS {rms:.4f} - speak louder, boost mic to 100% +20dB"

        return {"status": "ok", "text": text, "message": message, "rms": rms, "max": max_v}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e), "status": "error"}

# WebSocket for live mic level + transcription
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    ws_token = websocket.query_params.get("token", "")
    if OMNI_API_TOKEN and not (secrets.compare_digest(ws_token, OMNI_API_TOKEN) or ws_token in _device_tokens):
        await websocket.close(code=1008, reason="Authentication required")
        return
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if len(data.encode("utf-8")) > MAX_WS_MESSAGE_BYTES:
                await websocket.close(code=1009, reason="Message too large")
                return
            try:
                msg = json.loads(data)
                # Echo or handle
                await websocket.send_json({"type": "echo", "data": msg})
            except:
                await websocket.send_json({"type": "message", "text": data})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WS error: {e}")
        manager.disconnect(websocket)

# For direct run
if __name__ == "__main__":
    import uvicorn
    print(f"\n🚀 Starting FastAPI at http://localhost:8765")
    print(f"   Docs: http://localhost:8765/docs")
    print(f"   Health: http://localhost:8765/api/health")
    print(f"   REPO_ROOT: {REPO_ROOT} (portable)")
    uvicorn.run("main:app", host=os.environ.get("OMNI_HOST", "127.0.0.1"), port=8765, reload=False)
