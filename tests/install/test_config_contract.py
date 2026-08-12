from __future__ import annotations

import json
from pathlib import Path

import pytest

from omni_v2.core.config import (
    DEFAULT_BACKEND_PORT,
    DEFAULT_DISCOVERY_PORT,
    DEFAULT_FRONTEND_PORT,
    ConfigError,
    load_config,
    write_default_config,
)
from omni_v2.core.config_manager import ConfigManager


def test_safe_defaults_resolve_under_explicit_data_root(tmp_path: Path) -> None:
    config = load_config(environment={"OMNI_DATA_DIR": str(tmp_path)})

    assert config.data_dir == tmp_path.resolve()
    assert config.backend_port == DEFAULT_BACKEND_PORT
    assert config.frontend_port == DEFAULT_FRONTEND_PORT
    assert config.discovery_port == DEFAULT_DISCOVERY_PORT
    assert config.backend_url == "http://127.0.0.1:8765"
    assert config.frontend_url == "http://127.0.0.1:3000"
    assert config.fast_model_path.parent == (tmp_path / "models").resolve()
    assert config.stt_engine == "auto"
    assert config.stt_model == "base.en"
    assert config.stt_device == "auto"
    assert config.browser_profile_dir == (tmp_path / "browser" / "chrome_profile").resolve()
    assert config.offline is False
    assert config.tts_allow_cloud is False
    assert "backend_docs_url" not in config.public_dict()


def test_precedence_is_defaults_then_file_then_environment(tmp_path: Path) -> None:
    (tmp_path / "config.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "backend_port": 9100,
                "frontend_port": 3100,
                "discovery_port": 48000,
                "models_dir": "weights",
                "fast_model_path": "file-model.gguf",
                "offline": True,
            }
        ),
        encoding="utf-8",
    )

    from_file = load_config(environment={}, data_dir=tmp_path)
    overridden = load_config(
        environment={
            "OMNI_BACKEND_PORT": "9200",
            "OMNI_MODEL_PATH": "environment-model.gguf",
            "OMNI_BROWSER_PROFILE_DIR": "browser-test-profile",
            "OMNI_OFFLINE": "false",
        },
        data_dir=tmp_path,
    )

    assert from_file.backend_port == 9100
    assert from_file.frontend_port == 3100
    assert from_file.cors_origins == (
        "http://127.0.0.1:3100",
        "http://localhost:3100",
    )
    assert from_file.discovery_port == 48000
    assert from_file.fast_model_path == (tmp_path / "weights" / "file-model.gguf").resolve()
    assert from_file.offline is True
    assert overridden.backend_port == 9200
    assert overridden.frontend_port == 3100
    assert overridden.fast_model_path == (
        tmp_path / "weights" / "environment-model.gguf"
    ).resolve()
    assert overridden.browser_profile_dir == (tmp_path / "browser-test-profile").resolve()
    assert overridden.child_environment()["OMNI_BROWSER_PROFILE_DIR"] == str(
        overridden.browser_profile_dir
    )
    assert overridden.offline is False


def test_secrets_are_environment_only_and_diagnostics_are_redacted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret_values = {
        "OMNI_API_TOKEN": "api-secret-value",
        "HUGGINGFACE_TOKEN": "hf-secret-value",
        "PORCUPINE_KEY": "voice-secret-value",
    }
    config = load_config(environment=secret_values, data_dir=tmp_path)
    public = json.dumps(config.public_dict())
    monkeypatch.setenv("HF_TOKEN", "changed-after-load")
    monkeypatch.setenv("HUGGINGFACE_TOKEN", "stale-alias")
    monkeypatch.setenv("PICOVOICE_KEY", "stale-alias")
    monkeypatch.setenv("OMNI_MICROPHONE_DEVICE", "stale-device")
    monkeypatch.setenv("UNRELATED_PARENT_VALUE", "preserved")
    child = config.child_environment()

    assert config.secret_status() == {
        "api_token_configured": True,
        "hf_token_configured": True,
        "picovoice_key_configured": True,
    }
    assert all(value not in public for value in secret_values.values())
    assert child["OMNI_API_TOKEN"] == secret_values["OMNI_API_TOKEN"]
    assert child["HF_TOKEN"] == secret_values["HUGGINGFACE_TOKEN"]
    assert child["PICOVOICE_ACCESS_KEY"] == secret_values["PORCUPINE_KEY"]
    assert "HUGGINGFACE_TOKEN" not in child
    assert "PICOVOICE_KEY" not in child
    assert "OMNI_MICROPHONE_DEVICE" not in child
    assert child["UNRELATED_PARENT_VALUE"] == "preserved"

    (tmp_path / "config.json").write_text(
        json.dumps({"schema_version": 1, "api_token": "must-not-be-accepted"}),
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="unsupported key.*api_token"):
        load_config(environment={}, data_dir=tmp_path)


def test_default_config_creation_is_idempotent_and_non_overwriting(tmp_path: Path) -> None:
    path, created = write_default_config(data_dir=tmp_path)
    original = path.read_bytes()
    second_path, second_created = write_default_config(data_dir=tmp_path)

    assert created is True
    assert second_created is False
    assert second_path == path
    assert path.read_bytes() == original
    assert json.loads(original)["schema_version"] == 1

    document = json.loads(path.read_text(encoding="utf-8"))
    document["frontend_port"] = 4444
    path.write_text(json.dumps(document), encoding="utf-8")
    _, third_created = write_default_config(data_dir=tmp_path)
    assert third_created is False
    assert json.loads(path.read_text(encoding="utf-8"))["frontend_port"] == 4444
    assert load_config(environment={}, data_dir=tmp_path).cors_origins == (
        "http://127.0.0.1:4444",
        "http://localhost:4444",
    )


@pytest.mark.parametrize(
    ("environment", "message"),
    [
        ({"OMNI_BACKEND_PORT": "0"}, "backend_port"),
        ({"OMNI_FRONTEND_PORT": "70000"}, "frontend_port"),
        ({"OMNI_BACKEND_HOST": "http://localhost"}, "backend_host"),
        ({"OMNI_BACKEND_HOST": "localhost:9000"}, "backend_host"),
        ({"OMNI_OFFLINE": "sometimes"}, "offline"),
        ({"OMNI_CORS_ORIGINS": "*"}, "CORS origin"),
        ({"OMNI_CORS_ORIGINS": "http://localhost:not-a-port"}, "CORS origin"),
        ({"OMNI_CORS_ORIGINS": "http://::1:3000"}, "CORS origin"),
        ({"OMNI_CORS_ORIGINS": "http://bad host:3000"}, "CORS origin"),
        ({"OMNI_CORS_ORIGINS": "http://localhost:"}, "CORS origin"),
    ],
)
def test_invalid_environment_values_fail_closed(
    tmp_path: Path,
    environment: dict[str, str],
    message: str,
) -> None:
    with pytest.raises(ConfigError, match=message):
        load_config(environment=environment, data_dir=tmp_path)


def test_wildcard_bind_hosts_use_matching_loopback_urls(tmp_path: Path) -> None:
    ipv4 = load_config(
        environment={
            "OMNI_BACKEND_HOST": "0.0.0.0",
            "OMNI_FRONTEND_HOST": "0.0.0.0",
        },
        data_dir=tmp_path,
    )
    ipv6 = load_config(
        environment={
            "OMNI_BACKEND_HOST": "::",
            "OMNI_FRONTEND_HOST": "::",
        },
        data_dir=tmp_path,
    )

    assert ipv4.backend_url == "http://127.0.0.1:8765"
    assert ipv4.frontend_url == "http://127.0.0.1:3000"
    assert ipv6.backend_url == "http://[::1]:8765"
    assert ipv6.frontend_url == "http://[::1]:3000"


def test_raw_ipv6_hosts_produce_bracketed_urls(tmp_path: Path) -> None:
    config = load_config(
        environment={
            "OMNI_BACKEND_HOST": "::1",
            "OMNI_FRONTEND_HOST": "::1",
            "OMNI_CORS_ORIGINS": "http://[::1]:3000",
        },
        data_dir=tmp_path,
    )

    assert config.backend_url == "http://[::1]:8765"
    assert config.frontend_url == "http://[::1]:3000"
    assert config.cors_origins == ("http://[::1]:3000",)


def test_offline_mode_rejects_cloud_tts_opt_in(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="offline.*tts_allow_cloud"):
        load_config(
            environment={
                "OMNI_OFFLINE": "true",
                "OMNI_TTS_ALLOW_CLOUD": "true",
            },
            data_dir=tmp_path,
        )


def test_same_bind_endpoint_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="must differ"):
        load_config(
            environment={
                "OMNI_BACKEND_HOST": "127.0.0.1",
                "OMNI_FRONTEND_HOST": "127.0.0.1",
                "OMNI_BACKEND_PORT": "9999",
                "OMNI_FRONTEND_PORT": "9999",
            },
            data_dir=tmp_path,
        )


def test_legacy_manager_projects_but_does_not_persist_canonical_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OMNI_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("OMNI_STT_ENGINE", "faster_whisper")
    monkeypatch.setenv("OMNI_STT_MODEL", "configured-stt")
    monkeypatch.setenv("OMNI_STT_DEVICE", "cpu")
    monkeypatch.setenv("OMNI_BROWSER_DEBUG_PORT", "12345")
    manager = ConfigManager()
    settings = manager.load()

    assert manager.config_path == tmp_path / "settings.json"
    assert settings.stt_engine == "faster_whisper"
    assert settings.whisper_model == "configured-stt"
    assert settings.whisper_device == "cpu"
    assert settings.browser_port == 12345
    assert manager.save() is True
    persisted = json.loads(manager.config_path.read_text(encoding="utf-8"))
    assert not set(persisted).intersection(
        {"whisper_model", "whisper_device", "browser_port", "tts_allow_cloud"}
    )
    with pytest.raises(ValueError, match="canonical runtime configuration"):
        manager.set("browser_port", 9999)
