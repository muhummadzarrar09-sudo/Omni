from __future__ import annotations

import ast
import builtins
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from omni_v2.core.config import load_config
from omni_v2.core.model_policy import (
    OfflineModeError,
    faster_whisper_kwargs,
    huggingface_download_kwargs,
    huggingface_pretrained_kwargs,
    require_cloud_tts,
    require_online,
)

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def offline_config(tmp_path: Path):
    return load_config(
        environment={
            "OMNI_DATA_DIR": str(tmp_path / "data"),
            "OMNI_OFFLINE": "1",
        }
    )


def test_canonical_model_policy_projects_local_only_and_cache_paths(offline_config) -> None:
    whisper = faster_whisper_kwargs(offline_config)
    transformers = huggingface_pretrained_kwargs(offline_config)
    hub = huggingface_download_kwargs(offline_config, offline_config.models_dir)

    assert whisper == {
        "download_root": str(offline_config.models_dir / "stt" / "faster-whisper"),
        "local_files_only": True,
    }
    assert transformers["cache_dir"] == str(offline_config.models_dir / "huggingface")
    assert transformers["local_files_only"] is True
    assert hub["local_files_only"] is True
    assert hub["local_dir"] == str(offline_config.models_dir)
    with pytest.raises(OfflineModeError, match="offline"):
        require_online(offline_config, "test download")
    with pytest.raises(OfflineModeError, match="offline"):
        require_cloud_tts(offline_config, "test synthesis")


def test_vosk_missing_model_never_reaches_http_in_offline_mode(
    monkeypatch: pytest.MonkeyPatch,
    offline_config,
) -> None:
    from omni_v2.voice.stt_manager import STTManager

    manager = STTManager.__new__(STTManager)
    manager.runtime_config = offline_config
    manager.stt_models_dir = offline_config.models_dir / "stt"
    manager.stt_models_dir.mkdir(parents=True)

    class Requests:
        @staticmethod
        def get(*args, **kwargs):
            raise AssertionError("offline Vosk attempted HTTP")

    monkeypatch.setitem(sys.modules, "vosk", SimpleNamespace())
    monkeypatch.setitem(sys.modules, "requests", Requests())
    result = manager._transcribe_vosk(np.zeros(16_000, dtype=np.float32), 16_000)
    assert result is None


def test_hugging_face_downloader_uses_library_local_only_switch(
    monkeypatch: pytest.MonkeyPatch,
    offline_config,
) -> None:
    import omni_v2.llm.hf_downloader as module

    captured: dict[str, object] = {}

    def fake_download(**kwargs):
        captured.update(kwargs)
        raise FileNotFoundError("not cached")

    monkeypatch.setattr(module, "load_config", lambda: offline_config)
    monkeypatch.setitem(
        sys.modules,
        "huggingface_hub",
        SimpleNamespace(hf_hub_download=fake_download),
    )
    downloader = module.HFDownloader()
    assert downloader.download("example/model", "model.gguf") is None
    assert captured["local_files_only"] is True
    assert captured["local_dir"] == str(offline_config.models_dir)


def test_transformers_loaders_receive_local_only_policy(
    monkeypatch: pytest.MonkeyPatch,
    offline_config,
) -> None:
    import omni_v2.vision.multimodal as module

    captured: list[dict[str, object]] = []

    class FakeModel:
        @classmethod
        def from_pretrained(cls, *args, **kwargs):
            captured.append(kwargs)
            return cls()

        def to(self, device):
            return self

        def encode_image(self, image):
            return image

        def answer_question(self, image, query, processor):
            return "local answer"

    class FakeProcessor:
        @classmethod
        def from_pretrained(cls, *args, **kwargs):
            captured.append(kwargs)
            return cls()

    monkeypatch.setattr(module, "load_config", lambda: offline_config)
    monkeypatch.setitem(
        sys.modules,
        "transformers",
        SimpleNamespace(AutoModelForCausalLM=FakeModel, AutoProcessor=FakeProcessor),
    )
    monkeypatch.setitem(sys.modules, "PIL", SimpleNamespace(Image=object))
    module.MultimodalVision._instance = None
    vision = module.MultimodalVision()
    assert vision._describe_with_moondream(object(), "describe") == "local answer"
    assert len(captured) == 2
    assert all(item["local_files_only"] is True for item in captured)
    assert all(item["cache_dir"] == str(offline_config.models_dir / "huggingface") for item in captured)
    module.MultimodalVision._instance = None


def test_cloud_tts_fallbacks_do_not_import_cloud_clients_offline(
    monkeypatch: pytest.MonkeyPatch,
    offline_config,
) -> None:
    import omni_v2.voice.loop as loop_module
    import omni_v2.voice.tts_best as tts_module
    import omni_v2.voice.voice_clone as clone_module

    attempted: list[str] = []
    real_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name in {"edge_tts", "gtts"}:
            attempted.append(name)
            raise AssertionError(f"offline runtime imported {name}")
        if name == "pyttsx3":
            raise ImportError("force local TTS fallback to remain unavailable")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    tts = tts_module.TTSBest.__new__(tts_module.TTSBest)
    tts.runtime_config = offline_config
    tts.sapi_engine = None
    tts.spoken_count = 0
    assert tts._speak_edge_tts("hello", True, "en-US-AriaNeural") is False

    cloner = clone_module.VoiceCloner.__new__(clone_module.VoiceCloner)
    cloner.runtime_config = offline_config
    cloner._active_voice_id = "male_deep"
    assert cloner.speak_in_my_voice("hello") is False

    loop = loop_module.BagillionLoop.__new__(loop_module.BagillionLoop)
    loop.runtime_config = offline_config
    loop.tts_engine = None
    loop._speak("hello")
    assert attempted == []


def test_every_faster_whisper_constructor_projects_canonical_policy() -> None:
    paths = [ROOT / "backend_fastapi" / "main.py", *sorted((ROOT / "omni_v2").rglob("*.py"))]
    constructors = 0
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            function = node.func
            if not isinstance(function, ast.Name) or function.id != "WhisperModel":
                continue
            constructors += 1
            assert any(
                keyword.arg is None
                and isinstance(keyword.value, ast.Call)
                and isinstance(keyword.value.func, ast.Name)
                and keyword.value.func.id == "faster_whisper_kwargs"
                for keyword in node.keywords
            ), f"{path}:{node.lineno} omits canonical Faster-Whisper policy"
    assert constructors == 11
