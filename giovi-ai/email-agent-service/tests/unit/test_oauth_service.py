from datetime import datetime, timedelta, timezone
from typing import Optional, Sequence

import pytest
from cryptography.fernet import Fernet
from google.auth.exceptions import GoogleAuthError

from email_agent_service.config.settings import get_settings
from email_agent_service.repositories.host_email_integrations import HostEmailIntegrationRecord
from email_agent_service.repositories.oauth_states import OAuthStateRecord
from email_agent_service.services.integrations.oauth_service import (
    GmailOAuthService,
    OAuthStateExpiredError,
    OAuthStateNotFoundError,
    OAuthTokenExchangeError,
)


@pytest.fixture(autouse=True)
def settings_env(monkeypatch):
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("GOOGLE_OAUTH_REDIRECT_URI", "https://example.com/callback")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class FakeOAuthStateRepository:
    def __init__(self):
        self.created_record: Optional[OAuthStateRecord] = None
        self.deleted_state: Optional[str] = None
        self._stored_records = {}

    def create_state(self, record: OAuthStateRecord) -> None:
        self.created_record = record
        self._stored_records[record.state] = record

    def get_state(self, state: str) -> Optional[OAuthStateRecord]:
        return self._stored_records.get(state)

    def delete_state(self, state: str) -> None:
        self.deleted_state = state
        self._stored_records.pop(state, None)


class FakeHostEmailIntegrationRepository:
    def __init__(self):
        self.records = []

    def upsert_integration(self, record: HostEmailIntegrationRecord) -> None:
        self.records.append(record)


class FakeCredentials:
    def __init__(self):
        self.token = "access-token"
        self.refresh_token = "refresh-token"
        self.expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        self.scopes = ["scope-1", "scope-2"]


class FakeFlow:
    def __init__(self, authorization_url: str = "https://accounts.google.com/o/oauth2/auth"):
        self.authorization_url_value = authorization_url
        self.redirect_uri = None
        self.credentials = FakeCredentials()
        self.fetch_token_called_with: Optional[str] = None

    def authorization_url(self, **kwargs):
        return self.authorization_url_value, "fake-state"

    def fetch_token(self, *, code: str):
        if code == "raise":
            raise GoogleAuthError("error")
        self.fetch_token_called_with = code
        return self.credentials


def build_service(
    state_repo: Optional[FakeOAuthStateRepository] = None,
    integration_repo: Optional[FakeHostEmailIntegrationRepository] = None,
    fake_flow: Optional[FakeFlow] = None,
) -> tuple[GmailOAuthService, FakeOAuthStateRepository, FakeHostEmailIntegrationRepository]:
    state_repo = state_repo or FakeOAuthStateRepository()
    integration_repo = integration_repo or FakeHostEmailIntegrationRepository()
    service = GmailOAuthService(state_repo, integration_repo)
    if fake_flow:
        # pylint: disable=protected-access
        service._build_flow = lambda redirect_uri: fake_flow  # type: ignore[assignment]
    return service, state_repo, integration_repo


def test_generate_authorization_url_creates_state(monkeypatch):
    fake_flow = FakeFlow()
    service, state_repo, _ = build_service(fake_flow=fake_flow)

    url, state, expires_at = service.generate_authorization_url(
        host_id="host-123",
        email="user@example.com",
        redirect_uri="https://example.com/callback",
    )

    assert url == fake_flow.authorization_url_value
    assert state == "fake-state"
    assert isinstance(expires_at, datetime)
    assert state_repo.created_record is not None
    assert state_repo.created_record.host_uid == "host-123"


def test_handle_callback_persists_integration(monkeypatch):
    state_repo = FakeOAuthStateRepository()
    integration_repo = FakeHostEmailIntegrationRepository()
    fake_flow = FakeFlow()

    now = datetime.now(timezone.utc)
    state_repo.create_state(OAuthStateRecord(state="state-123", host_uid="host-xyz", expires_at=now + timedelta(minutes=5)))

    service, _, _ = build_service(
        state_repo=state_repo, integration_repo=integration_repo, fake_flow=fake_flow
    )

    record = service.handle_callback(state="state-123", code="auth-code", email="user@example.com")

    assert fake_flow.fetch_token_called_with == "auth-code"
    assert integration_repo.records
    saved_record = integration_repo.records[0]
    assert saved_record.email == "user@example.com"
    assert saved_record.host_id == "host-xyz"
    assert saved_record.provider == "gmail"
    assert list(saved_record.scopes) == fake_flow.credentials.scopes
    assert state_repo.deleted_state == "state-123"
    assert record.email == saved_record.email
    assert record.encrypted_access_token == saved_record.encrypted_access_token


def test_handle_callback_raises_when_state_missing():
    service, _, _ = build_service(state_repo=FakeOAuthStateRepository(), fake_flow=FakeFlow())

    with pytest.raises(OAuthStateNotFoundError):
        service.handle_callback(state="missing", code="auth-code", email="user@example.com")


def test_handle_callback_raises_when_state_expired():
    state_repo = FakeOAuthStateRepository()
    state_repo.create_state(
        OAuthStateRecord(
            state="state-123",
            host_uid="host-xyz",
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )
    )
    service, _, _ = build_service(state_repo=state_repo, fake_flow=FakeFlow())

    with pytest.raises(OAuthStateExpiredError):
        service.handle_callback(state="state-123", code="auth-code", email="user@example.com")


def test_handle_callback_wraps_token_exchange_errors():
    state_repo = FakeOAuthStateRepository()
    state_repo.create_state(
        OAuthStateRecord(
            state="state-123",
            host_uid="host-xyz",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
    )
    fake_flow = FakeFlow()
    service, _, _ = build_service(state_repo=state_repo, fake_flow=fake_flow)

    with pytest.raises(OAuthTokenExchangeError):
        service.handle_callback(state="state-123", code="raise", email="user@example.com")

