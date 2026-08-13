#!/usr/bin/env python3
"""B02 static/dynamic configuration ownership verification."""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from omni_v2.core.config import load_config, write_default_config
from omni_v2.core.config_manager import ConfigManager

FIXED_BACKEND = re.compile(r"https?://(?:localhost|127\.0\.0\.1):8765")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def verify_dynamic_contract() -> None:
    with tempfile.TemporaryDirectory(prefix="omni-config-contract-") as temporary:
        data_dir = Path(temporary)
        environment = {
            "OMNI_DATA_DIR": str(data_dir),
            "OMNI_BACKEND_PORT": "18765",
            "OMNI_FRONTEND_PORT": "13000",
            "OMNI_DISCOVERY_PORT": "17624",
            "OMNI_BROWSER_PROFILE_DIR": "contract-browser-profile",
            "OMNI_BROWSER_DEBUG_PORT": "19222",
            "OMNI_STT_MODEL": "contract-model",
            "OMNI_STT_DEVICE": "cpu",
            "OMNI_TTS_VOICE": "contract-voice",
            "OMNI_OFFLINE": "true",
            "OMNI_API_TOKEN": "must-not-appear-in-diagnostics",
        }
        config = load_config(environment=environment)
        public = json.dumps(config.public_dict())
        require(config.backend_url == "http://127.0.0.1:18765", "backend override failed")
        require(config.frontend_url == "http://127.0.0.1:13000", "frontend override failed")
        require(config.stt_model == "contract-model", "STT model override failed")
        require(config.stt_device == "cpu", "STT device override failed")
        require(config.tts_voice == "contract-voice", "TTS voice override failed")
        require(
            config.browser_profile_dir == (data_dir / "contract-browser-profile").resolve(),
            "browser profile override failed",
        )
        require(config.offline is True, "offline override failed")
        require("must-not-appear-in-diagnostics" not in public, "secret leaked to diagnostics")
        child = config.child_environment()
        require(child["OMNI_BACKEND_URL"] == config.backend_url, "child backend URL drifted")
        require(
            child["OMNI_API_TOKEN"] == environment["OMNI_API_TOKEN"],
            "child API secret drifted",
        )
        path, created = write_default_config(data_dir=data_dir)
        require(created and path.is_file(), "default configuration was not created")
        _, created_again = write_default_config(data_dir=data_dir)
        require(not created_again, "configuration initialization was not idempotent")

        previous = os.environ.copy()
        try:
            os.environ.update(environment)
            manager = ConfigManager()
            settings = manager.load()
            require(settings.whisper_model == "contract-model", "legacy STT projection drifted")
            require(settings.browser_port == 19222, "legacy browser-port projection drifted")
            require(manager.config_path.name == "settings.json", "legacy manager owns config.json")
        finally:
            os.environ.clear()
            os.environ.update(previous)


def verify_source_contract() -> None:
    routes = sorted((ROOT / "frontend_next" / "app" / "api").rglob("route.js"))
    require(bool(routes), "no frontend proxy routes found")
    for route in routes:
        source = route.read_text(encoding="utf-8")
        require(not FIXED_BACKEND.search(source), f"fixed backend URL remains in {route}")
        require(
            "backendProxy(" in source or "backendFetch(" in source,
            f"route bypasses canonical backend helper: {route}",
        )
        require("mock: true" not in source, f"route fabricates mock state: {route}")
        require("FastAPI not running" not in source, f"route hides backend unavailability: {route}")
        if re.search(r"export (?:async )?function (?:POST|PUT|PATCH|DELETE)\(", source):
            require(
                "sourceRequest: request" in source,
                f"mutation route omits browser origin context: {route}",
            )

    backend_helper = (ROOT / "frontend_next" / "backend.js").read_text(encoding="utf-8")
    require("import 'server-only'" in backend_helper, "backend helper can enter a browser bundle")
    require("process.env.OMNI_BACKEND_URL" in backend_helper, "backend helper bypasses managed URL")
    require("process.env.OMNI_API_TOKEN" in backend_helper, "backend helper bypasses managed API secret")
    require("X-OMNI-Token" in backend_helper, "backend helper does not authenticate mutations")
    require("enforceMutationOrigin" in backend_helper, "backend helper omits browser origin enforcement")
    require("status: response.status" in backend_helper, "backend response status is not preserved")
    require("status: 503" in backend_helper, "backend unavailability is not explicit")

    proxy_policy = (ROOT / "frontend_next" / "proxy-policy.mjs").read_text(encoding="utf-8")
    require("cross-site" in proxy_policy, "proxy policy ignores Fetch Metadata")
    require(
        "configuredBrowserOrigins().has(normalizedOrigin)" in proxy_policy,
        "proxy policy does not compare origins",
    )

    next_config = (ROOT / "frontend_next" / "next.config.js").read_text(encoding="utf-8")
    require("process.env.OMNI_BACKEND_URL" in next_config, "Next.js does not require managed URL")
    require("|| 'http://localhost" not in next_config, "Next.js silently defaults to localhost")
    require("source: '/api/python/:path*'" not in next_config, "browser API rewrite bypasses token injection")

    frontend_server = (ROOT / "frontend_next" / "server.js").read_text(encoding="utf-8")
    require("server.on('upgrade', relayWebSocket)" in frontend_server, "same-origin WebSocket relay is absent")
    require("process.env.OMNI_BACKEND_URL" in frontend_server, "WebSocket relay bypasses managed URL")

    browser_page = (ROOT / "frontend_next" / "app" / "page.js").read_text(encoding="utf-8")
    backend = (ROOT / "backend_fastapi" / "main.py").read_text(encoding="utf-8")
    require("/api/python/auth/websocket-ticket" in browser_page, "browser bypasses WebSocket ticket flow")
    require("/ws?token=" in browser_page, "browser WebSocket does not present its one-use ticket")
    require("/api/auth/websocket-ticket" in backend, "backend does not issue WebSocket tickets")
    require("_websocket_token_is_valid" in backend, "backend WebSocket bypasses canonical authentication")

    manager = (ROOT / "omni_v2" / "core" / "config_manager.py").read_text(encoding="utf-8")
    require('runtime.data_dir / "settings.json"' in manager, "legacy settings can overwrite config.json")
    require("_CANONICAL_FIELDS" in manager, "legacy settings lack canonical ownership boundary")

    runtime_consumers = {
        "omni_v2/voice/stt_manager.py": ("models_dir", "stt_model", "stt_device_attempts"),
        "omni_v2/voice/stt_simple.py": ("data_dir",),
        "omni_v2/voice/pipeline.py": ("data_dir", "stt_model", "stt_device_attempts"),
        "omni_v2/voice/loop.py": ("data_dir", "stt_model", "stt_device_attempts"),
        "omni_v2/voice/wake_word.py": ("models_dir", "picovoice_key"),
        "omni_v2/voice/wake_word_v3.py": ("stt_model", "stt_device_attempts"),
        "omni_v2/voice/wake_word_best.py": (
            "stt_model",
            "stt_device_attempts",
            "picovoice_key",
        ),
        "omni_v2/voice/tts_simple.py": ("models_dir", "tts_voice"),
        "omni_v2/voice/voice_clone.py": ("data_dir", "models_dir"),
        "omni_v2/ui/whisper_flow.py": ("stt_model", "stt_device_attempts"),
        "omni_v2/tools/browser_v3.py": (
            "browser_path",
            "browser_profile_dir",
            "browser_debug_port",
        ),
        "omni_v2/llm/hf_downloader.py": ("models_dir", "hf_token"),
        "omni_v2/llm/llama_cpp.py": ("models_dir", "fast_model_path", "deep_model_path"),
        "omni_v2/llm/brain.py": ("models_dir", "fast_model_path", "deep_model_path"),
        "omni_v2/vision/turbovlm.py": ("models_dir",),
    }
    for relative, required_attributes in runtime_consumers.items():
        source = (ROOT / relative).read_text(encoding="utf-8")
        require("load_config" in source, f"runtime consumer bypasses canonical config: {relative}")
        require(
            "from omni_v2.core.paths import DATA_DIR" not in source,
            f"runtime consumer retains import-time data ownership: {relative}",
        )
        for attribute in required_attributes:
            require(
                attribute in source,
                f"runtime consumer does not use canonical {attribute}: {relative}",
            )
        require(
            'WhisperModel("base.en"' not in source,
            f"runtime consumer fixes the command STT model: {relative}",
        )


if __name__ == "__main__":
    verify_dynamic_contract()
    verify_source_contract()
    print("B02 configuration contract: PASS")
