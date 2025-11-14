import base64
from email.message import EmailMessage
from typing import Optional

import pytest
from cryptography.fernet import Fernet

from email_agent_service.config.settings import get_settings
from email_agent_service.models import ParsedEmail
from email_agent_service.parsers import (
    AirbnbConfirmationParser,
    AirbnbMessageParser,
    BookingConfirmationParser,
    BookingMessageParser,
    EmailParsingEngine,
)
from email_agent_service.repositories.host_email_integrations import HostEmailIntegrationRecord
from email_agent_service.services.backfill_service import GmailBackfillService


@pytest.fixture(autouse=True)
def env_setup(monkeypatch):
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("GOOGLE_OAUTH_REDIRECT_URI", "https://example.com/callback")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def build_email_bytes(subject: str, sender: str, to: str, body: str) -> bytes:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = to
    message.set_content(body)
    return message.as_bytes()


class FakeGmailService:
    def __init__(self, raw_bytes: bytes):
        self.raw_bytes = raw_bytes
        self.list_calls = 0
        self.get_calls = 0

    def list_messages(self, integration, query: str, page_token: Optional[str] = None, max_results: int = 100):
        self.list_calls += 1
        return {"messages": [{"id": "msg-1"}]}

    def get_message_raw(self, integration, message_id: str):
        self.get_calls += 1
        encoded = base64.urlsafe_b64encode(self.raw_bytes).decode("utf-8")
        return {"id": message_id, "raw": encoded, "snippet": "Snippet"}


class FakeIntegrationRepo:
    def __init__(self, record: HostEmailIntegrationRecord):
        self.record = record

    def get_by_email(self, email: str) -> Optional[HostEmailIntegrationRecord]:
        return self.record if self.record.email == email else None


class FakeProcessedRepo:
    def __init__(self):
        self.items = set()

    def was_processed(self, integration_email: str, message_id: str) -> bool:
        return (integration_email, message_id) in self.items

    def mark_processed(self, integration_email: str, message_id: str, history_id: Optional[str] = None):
        self.items.add((integration_email, message_id))


def test_backfill_service_parses_messages(monkeypatch):
    body = """
    Subject: Confermata - Prenotazione ID 5958915259 - Booking
    Nome Ospite=09Brufani Francesco
    Struttura Richiesta=09Piazza Danti Perugia Centro
    Data di Check-in=0915/01/2026
    Data di Check-out=0918/01/2026
    Ospiti=092 Adulti
    Totale Prenotazione: 349,55 €
    """
    email_bytes = build_email_bytes(
        "Confermata - Prenotazione ID 5958915259 - Booking",
        "reservation@scidoo.com",
        "host@example.com",
        body,
    )

    gmail_service = FakeGmailService(email_bytes)
    engine = EmailParsingEngine(
        [
            BookingConfirmationParser(),
            BookingMessageParser(),
            AirbnbConfirmationParser(),
            AirbnbMessageParser(),
        ]
    )
    record = HostEmailIntegrationRecord(
        email="host@example.com",
        host_id="host-123",
        provider="gmail",
        encrypted_access_token=Fernet(get_settings().token_encryption_key.encode()).encrypt(b"token").decode(),
        encrypted_refresh_token=None,
        scopes=[
            "https://www.googleapis.com/auth/gmail.readonly",
        ],
        token_expiry=None,
    )

    service = GmailBackfillService(
        gmail_service=gmail_service,
        integration_repository=FakeIntegrationRepo(record),
        processed_repository=FakeProcessedRepo(),
        parsing_engine=engine,
    )

    results = service.run_backfill(host_id="host-123", email="host@example.com")

    assert len(results) == 1
    first: ParsedEmail = results[0]
    assert first.kind == "booking_confirmation"
    assert first.reservation is not None
    assert first.reservation.reservation_id == "5958915259"

