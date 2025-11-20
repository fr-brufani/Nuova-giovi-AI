"""Unit tests per BookingMessagingClient."""

from datetime import datetime

import pytest

from email_agent_service.models.booking_message import BookingMessage
from email_agent_service.services.integrations.booking_messaging_client import (
    BookingAuthenticationError,
    BookingForbiddenError,
    BookingMessagingClient,
    BookingRateLimitError,
)
from tests.fixtures.booking_api_responses import (
    MOCK_CONVERSATION_BY_RESERVATION_RESPONSE,
    MOCK_MESSAGES_LATEST_RESPONSE,
)


@pytest.fixture
def mock_client():
    """Fixture per client in mock mode."""
    return BookingMessagingClient(mock_mode=True)


@pytest.fixture(autouse=True)
def env_setup(monkeypatch):
    """Setup environment variables per test."""
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", "test-key-123456789012345678901234567890123456=")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("GOOGLE_OAUTH_REDIRECT_URI", "https://example.com/callback")


def test_client_initializes_in_mock_mode_without_credentials():
    """Test che il client si inizializza in mock mode senza credenziali."""
    client = BookingMessagingClient()
    assert client.mock_mode is True


def test_client_initializes_in_production_mode_with_credentials():
    """Test che il client si inizializza in production mode con credenziali."""
    client = BookingMessagingClient(username="test", password="test", mock_mode=False)
    assert client.mock_mode is False


def test_get_latest_messages_returns_mock_data(mock_client):
    """Test recupero messaggi in mock mode."""
    response = mock_client.get_latest_messages()
    
    assert response["data"]["ok"] is True
    assert len(response["data"]["messages"]) > 0
    assert "message_id" in response["data"]["messages"][0]
    assert "conversation" in response["data"]["messages"][0]


def test_get_latest_messages_converts_to_booking_message(mock_client):
    """Test conversione response API a BookingMessage."""
    response = mock_client.get_latest_messages()
    message_data = response["data"]["messages"][0]
    
    booking_message = BookingMessage.from_api_response(message_data)
    
    assert booking_message.message_id == message_data["message_id"]
    assert booking_message.content == message_data["content"]
    assert booking_message.sender.participant_type == "GUEST"
    assert booking_message.conversation.conversation_reference == "3812391309"


def test_booking_message_to_internal_format():
    """Test conversione BookingMessage a formato interno."""
    message_data = MOCK_MESSAGES_LATEST_RESPONSE["data"]["messages"][0]
    booking_message = BookingMessage.from_api_response(message_data)
    
    internal = booking_message.to_internal_format()
    
    assert internal["kind"] == "booking_message"
    assert internal["source"] == "booking_api"
    assert internal["reservation_id"] == "3812391309"
    assert internal["message"] == message_data["content"]


def test_get_conversation_by_reservation(mock_client):
    """Test recupero conversazione per reservation_id."""
    response = mock_client.get_conversation_by_reservation(
        property_id="8011855", reservation_id="3812391309"
    )
    
    assert response["data"]["ok"] == "true"
    assert "conversation" in response["data"]
    assert response["data"]["conversation"]["conversation_type"] == "reservation"


def test_send_message_mock(mock_client):
    """Test invio messaggio in mock mode."""
    response = mock_client.send_message(
        property_id="8011855",
        conversation_id="f3a9c29d-480d-5f5b-a6c0-65451e335353",
        content="Test reply message",
    )
    
    # In mock mode, dovrebbe restituire response con ok
    assert "data" in response or response.get("ok") is not None


def test_confirm_messages(mock_client):
    """Test conferma messaggi."""
    response = mock_client.confirm_messages(number_of_messages=1)
    
    # In mock mode, dovrebbe restituire response con ok
    assert "data" in response or response.get("ok") is not None

