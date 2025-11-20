"""Unit tests per BookingReservationClient."""

import pytest
from tests.fixtures.booking_api_responses import MOCK_OTA_XML_RESPONSE


@pytest.fixture
def mock_reservation_client():
    """Fixture per client reservation in mock mode."""
    from email_agent_service.services.integrations.booking_reservation_client import (
        BookingReservationClient,
    )
    
    return BookingReservationClient(mock_mode=True)


@pytest.fixture(autouse=True)
def env_setup(monkeypatch):
    """Setup environment variables per test."""
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", "test-key-123456789012345678901234567890123456=")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("GOOGLE_OAUTH_REDIRECT_URI", "https://example.com/callback")


def test_client_initializes_in_mock_mode_without_credentials():
    """Test che il client reservation si inizializza in mock mode senza credenziali."""
    from email_agent_service.services.integrations.booking_reservation_client import (
        BookingReservationClient,
    )
    
    client = BookingReservationClient()
    assert client.mock_mode is True


def test_get_new_reservations_returns_xml(mock_reservation_client):
    """Test recupero nuove prenotazioni in mock mode."""
    xml_response = mock_reservation_client.get_new_reservations()
    
    assert isinstance(xml_response, str)
    assert "OTA_HotelResNotifRQ" in xml_response
    assert "HotelReservations" in xml_response
    assert "HotelReservationID" in xml_response


def test_get_new_reservations_with_filters(mock_reservation_client):
    """Test recupero prenotazioni con filtri."""
    xml_response = mock_reservation_client.get_new_reservations(
        hotel_ids="8011855", limit=10
    )
    
    assert isinstance(xml_response, str)
    assert "OTA_HotelResNotifRQ" in xml_response


def test_acknowledge_new_reservations(mock_reservation_client):
    """Test acknowledgement prenotazioni."""
    ack_response = mock_reservation_client.acknowledge_new_reservations(
        MOCK_OTA_XML_RESPONSE
    )
    
    assert isinstance(ack_response, str)
    assert "OTA_HotelResNotifRS" in ack_response or "Success" in ack_response


def test_get_modified_reservations(mock_reservation_client):
    """Test recupero prenotazioni modificate."""
    xml_response = mock_reservation_client.get_modified_reservations()
    
    assert isinstance(xml_response, str)
    assert "OTA_HotelResNotifRQ" in xml_response

