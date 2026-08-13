from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import backend_fastapi.main as backend


@pytest.fixture()
def protected_client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(backend, "OMNI_API_TOKEN", "test-api-token")
    backend._active_pair_codes.clear()
    backend._device_tokens.clear()
    backend._websocket_tickets.clear()
    client = TestClient(backend.app)
    yield client
    backend._active_pair_codes.clear()
    backend._device_tokens.clear()
    backend._websocket_tickets.clear()


def test_every_pairing_code_issuer_requires_configured_api_token(protected_client: TestClient) -> None:
    requests = (
        ("post", "/api/network/pair"),
        ("get", "/api/network/qr"),
        ("get", "/api/network/pair/active"),
        ("get", "/api/mobile/qr-page"),
    )
    for method, path in requests:
        response = getattr(protected_client, method)(path)
        assert response.status_code == 401, path
        assert response.json() == {"error": "Authentication required"}

    # Possession of the short-lived code is intentionally the public bootstrap
    # credential; code creation and disclosure are never public.
    response = protected_client.post("/api/network/pair/verify", json={"code": "123456"})
    assert response.status_code == 200
    assert response.json()["valid"] is False


def test_pairing_code_is_issued_authenticated_and_consumed_once(protected_client: TestClient) -> None:
    issued = protected_client.get(
        "/api/network/pair/active",
        headers={"X-OMNI-Token": "test-api-token"},
    )
    assert issued.status_code == 200
    code = issued.json()["pair"]["code"]
    assert code in backend._active_pair_codes

    verified = protected_client.post("/api/network/pair/verify", json={"code": code})
    assert verified.status_code == 200
    payload = verified.json()
    assert payload["valid"] is True
    assert payload["token"] in backend._device_tokens
    assert code not in backend._active_pair_codes

    replay = protected_client.post("/api/network/pair/verify", json={"code": code})
    assert replay.status_code == 200
    assert replay.json()["valid"] is False


def test_low_entropy_pairing_code_has_a_global_attempt_bound(protected_client: TestClient) -> None:
    issued = protected_client.get(
        "/api/network/pair/active",
        headers={"X-OMNI-Token": "test-api-token"},
    )
    code = issued.json()["pair"]["code"]
    wrong_code = "000000" if code != "000000" else "999999"

    for _ in range(backend.MAX_PAIRING_ATTEMPTS):
        response = protected_client.post("/api/network/pair/verify", json={"code": wrong_code})
        assert response.status_code == 200
        assert response.json()["valid"] is False

    assert code not in backend._active_pair_codes
    response = protected_client.post("/api/network/pair/verify", json={"code": code})
    assert response.status_code == 200
    assert response.json()["valid"] is False


def test_websocket_ticket_endpoint_is_protected_and_ticket_is_one_use(
    protected_client: TestClient,
) -> None:
    denied = protected_client.post("/api/auth/websocket-ticket")
    assert denied.status_code == 401

    issued = protected_client.post(
        "/api/auth/websocket-ticket",
        headers={"X-OMNI-Token": "test-api-token"},
    )
    assert issued.status_code == 200
    ticket = issued.json()["ticket"]
    assert backend._websocket_token_is_valid(ticket) is True
    assert backend._websocket_token_is_valid(ticket) is False
