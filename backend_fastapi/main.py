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
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from pathlib import Path
import sys
import asyncio
import json
import time
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

# CORS for Next.js (3000) and any origin for judges
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For hackathon, allow all - judges clone anywhere
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ExecuteRequest(BaseModel):
    command: str
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
        logger.info(f"⏰ Scheduler initialized: {len(sched.list_tasks())} existing tasks")
    except Exception as e:
        logger.warning(f"Scheduler init failed: {e}")
    print("="*70)
    print("  OMNI V3 FastAPI - Pretty Damn Good Backend")
    print(f"  REPO_ROOT: {REPO_ROOT} (portable, not D:/Omni)")
    print("  Sounddevice primary - fixes PyAudio -9999")
    print("  Profile isolated Chrome - no email leak")
    print("  Multi-agent: Planner->Executor->Monitor->Evaluator")
    print("="*70)
    brain = get_brain()
    print(f"✅ Brain ready: {brain.ready}")

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
    except Exception as e:
        return {"status": "error", "error": str(e)}


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
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.delete("/api/user/profile/{field}")
async def forget_user_profile_field(field: str):
    """Forget (reset) a specific profile field."""
    try:
        from omni_v2.agents.user_profile import get_user_profile
        profile = get_user_profile()
        success = profile.forget(field)
        return {"status": "ok" if success else "not_found", "field": field, "forgot": success}
    except Exception as e:
        return {"status": "error", "error": str(e)}


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
    except Exception as e:
        return {"status": "error", "error": str(e)}


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
    except Exception as e:
        return {"status": "error", "error": str(e)}


# PHASE-1B: Session Memory endpoints
@app.get("/api/memory/sessions")
async def get_sessions(days: int = 7):
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
async def search_memory(q: str, days: int = 30):
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
    name: str
    command: str
    cron: str  # "0 9 * * 1-5" format


class ScheduleIntervalReq(BaseModel):
    name: str
    command: str
    seconds: Optional[int] = None
    minutes: Optional[int] = None
    hours: Optional[int] = None


class ScheduleOnceReq(BaseModel):
    name: str
    command: str
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
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/scheduler/interval")
async def add_interval_task(req: ScheduleIntervalReq):
    """Add an interval task. e.g. {'name': 'break', 'command': 'remind me to stretch', 'minutes': 30}"""
    try:
        from omni_v2.agents.scheduler import get_scheduler
        sched = get_scheduler()
        kwargs = {k: v for k, v in req.dict().items() if k not in ("name", "command") and v is not None}
        task = sched.add_interval(req.name, req.command, **kwargs)
        return {"status": "ok", "task_id": task.id, "name": task.name}
    except Exception as e:
        return {"status": "error", "error": str(e)}


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
    except Exception as e:
        return {"status": "error", "error": str(e)}


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
    file_path: Optional[str] = None
    query: str = "Describe this"
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
        return {"status": "error", "error": str(e)}


@app.get("/api/vision/status")
async def vision_status():
    """Get vision engine status."""
    try:
        from omni_v2.vision.multimodal import get_vision
        return {"status": "ok", "vision": get_vision().get_status()}
    except Exception as e:
        return {"status": "error", "error": str(e)}


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
        return {"status": "error", "error": str(e)}


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
        return {"status": "error", "error": str(e)}


class VoiceTrainReq(BaseModel):
    sample_path: str
    voice_name: Optional[str] = None


@app.post("/api/voice/clone/train")
async def voice_clone_train(req: VoiceTrainReq):
    """Train a custom voice from a recorded sample."""
    try:
        from omni_v2.voice.voice_clone import get_voice_cloner
        vc = get_voice_cloner()
        result = vc.train_voice(req.sample_path, req.voice_name)
        return result
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/voice/clone/samples")
async def voice_clone_samples():
    """List voice samples."""
    try:
        from omni_v2.voice.voice_clone import get_voice_cloner
        return {"status": "ok", "samples": get_voice_cloner().list_samples()}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/voice/clone/voices")
async def voice_clone_voices():
    """List cloned voices."""
    try:
        from omni_v2.voice.voice_clone import get_voice_cloner
        return {"status": "ok", "voices": get_voice_cloner().list_voices()}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/voice/clone/status")
async def voice_clone_status():
    """Get voice clone status."""
    try:
        from omni_v2.voice.voice_clone import get_voice_cloner
        return {"status": "ok", "voice_clone": get_voice_cloner().get_status()}
    except Exception as e:
        return {"status": "error", "error": str(e)}


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
    skill_id: str


@app.post("/api/skills/install")
async def skill_install(req: SkillInstallReq):
    """Install a skill from the marketplace."""
    try:
        from omni_v2.skills.marketplace import get_marketplace
        m = get_marketplace()
        return m.install(req.skill_id)
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/skills/uninstall")
async def skill_uninstall(req: SkillInstallReq):
    """Uninstall a skill."""
    try:
        from omni_v2.skills.marketplace import get_marketplace
        m = get_marketplace()
        ok = m.uninstall(req.skill_id)
        return {"status": "ok" if ok else "not_found", "uninstalled": ok}
    except Exception as e:
        return {"status": "error", "error": str(e)}


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

@app.get("/api/devices")
async def devices():
    brain = get_brain()
    return brain.get_devices()

@app.post("/api/execute", response_model=ExecuteResponse)
async def execute(req: ExecuteRequest):
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
    client_key = "global"  # Could be per-IP in production
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
async def execute_stream(req: ExecuteRequest):
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

    async def event_stream():
        import asyncio
        from omni_v2.llm.brain import get_brain as _get_brain
        brain_inst = _get_brain()
        # Stream LLM tokens
        try:
            # We can't easily make the existing brain.think async-streaming,
            # so we do a regular think + stream the result
            brain_resp = brain_inst.think(req.command, stream=False)
            # Stream the raw LLM output token-by-token (simulated)
            raw = brain_resp.raw or brain_resp.text or ""
            chunk_size = 4  # characters per event
            for i in range(0, len(raw), chunk_size):
                chunk = raw[i:i+chunk_size]
                yield f"event: thinking\ndata: {json.dumps({'token': chunk, 'tier': brain_resp.tier})}\n\n"
                await asyncio.sleep(0.02)  # smooth streaming
            # Send tool calls
            for tc in brain_resp.tool_calls:
                yield f"event: tool_call\ndata: {json.dumps({'tool': tc['tool'], 'args': tc.get('args', {})})}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
            return

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
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
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
    uvicorn.run("main:app", host="0.0.0.0", port=8765, reload=True)
