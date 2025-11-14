from datetime import datetime, timezone

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from email_agent_service.app import create_app
from email_agent_service.config.settings import get_settings
from email_agent_service.repositories.host_email_integrations import HostEmailIntegrationRecord
from email_agent_service.api.routes.integrations import get_oauth_service, get_backfill_service
from email_agent_service.services.integrations.oauth_service import (
    OAuthStateExpiredError,
    OAuthStateNotFoundError,
    OAuthTokenExchangeError,
)


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("GOOGLE_OAUTH_REDIRECT_URI", "https://example.com/callback")
    get_settings.cache_clear()
    monkeypatch.setattr("email_agent_service.app.get_firestore_client", lambda: None)

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client

    get_settings.cache_clear()


class FakeOAuthService:
    def __init__(self, *, raise_on_callback=None):
        self.raise_on_callback = raise_on_callback

    def generate_authorization_url(self, *, host_id, email, redirect_uri=None):
        return "https://accounts.google.com/auth", "state-123", datetime.now(timezone.utc)

    def handle_callback(self, *, state, code, email, redirect_uri=None):
        if self.raise_on_callback:
            raise self.raise_on_callback("error")

        return HostEmailIntegrationRecord(
            email=email,
            host_id="host-xyz",
            provider="gmail",
            encrypted_access_token="encrypted_access",
            encrypted_refresh_token="encrypted_refresh",
            scopes=["scope"],
            token_expiry=datetime.now(timezone.utc),
        )


class FakeBackfillService:
    def __init__(self):
        self.called_with = None

    def run_backfill(self, host_id: str, email: str):
        self.called_with = (host_id, email)
        return []


def test_start_gmail_integration_returns_authorization_url(client, monkeypatch):
    fake_service = FakeOAuthService()
    client.app.dependency_overrides[get_oauth_service] = lambda: fake_service

    response = client.post(
        "/integrations/gmail/start",
        json={"hostId": "host-xyz", "email": "user@example.com"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["authorizationUrl"] == "https://accounts.google.com/auth"
    assert payload["state"] == "state-123"

    client.app.dependency_overrides.clear()


def test_callback_returns_success(client):
    fake_service = FakeOAuthService()
    client.app.dependency_overrides[get_oauth_service] = lambda: fake_service

    response = client.post(
        "/integrations/gmail/callback",
        json={
            "state": "state-123",
            "code": "auth-code",
            "hostId": "host-xyz",
            "email": "user@example.com",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "connected"
    assert payload["hostId"] == "host-xyz"

    client.app.dependency_overrides.clear()


@pytest.mark.parametrize(
    "exception_cls,expected_status",
    [
        (OAuthStateNotFoundError, 400),
        (OAuthStateExpiredError, 400),
        (OAuthTokenExchangeError, 502),
    ],
)
def test_callback_returns_errors(client, exception_cls, expected_status):
    fake_service = FakeOAuthService(raise_on_callback=exception_cls)
    client.app.dependency_overrides[get_oauth_service] = lambda: fake_service

    response = client.post(
        "/integrations/gmail/callback",
        json={
            "state": "invalid",
            "code": "auth-code",
            "hostId": "host-xyz",
            "email": "user@example.com",
        },
    )

    assert response.status_code == expected_status

    client.app.dependency_overrides.clear()


def test_backfill_endpoint(client):
    fake_service = FakeBackfillService()
    client.app.dependency_overrides[get_backfill_service] = lambda: fake_service

    response = client.post(
        "/integrations/gmail/host@example.com/backfill",
        params={"host_id": "host-xyz"},
    )

    assert response.status_code == 200
    assert response.json() == {"processed": 0, "items": []}
    assert fake_service.called_with == ("host-xyz", "host@example.com")

    client.app.dependency_overrides.clear()

