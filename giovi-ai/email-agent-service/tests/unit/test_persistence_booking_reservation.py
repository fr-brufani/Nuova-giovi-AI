"""Unit tests per PersistenceService.save_booking_reservation."""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock

from email_agent_service.models.booking_reservation import BookingGuestInfo, BookingReservation
from email_agent_service.services.persistence_service import PersistenceService
from tests.fixtures.booking_api_responses import MOCK_OTA_XML_RESPONSE
from email_agent_service.parsers.booking_reservation_parser import parse_ota_xml


@pytest.fixture
def mock_firestore_client():
    """Mock Firestore client."""
    client = Mock()
    client.collection.return_value = Mock()
    return client


@pytest.fixture
def mock_repositories(mock_firestore_client):
    """Mock repositories."""
    from email_agent_service.repositories import (
        BookingPropertyMappingsRepository,
        ClientsRepository,
        PropertiesRepository,
        ReservationsRepository,
    )
    
    # Mock collections
    properties_collection = Mock()
    clients_collection = Mock()
    reservations_collection = Mock()
    mappings_collection = Mock()
    booking_mappings_collection = Mock()
    
    mock_firestore_client.collection.side_effect = lambda name: {
        "properties": properties_collection,
        "clients": clients_collection,
        "reservations": reservations_collection,
        "propertyNameMappings": mappings_collection,
        "bookingPropertyMappings": booking_mappings_collection,
    }[name]
    
    return {
        "properties": properties_collection,
        "clients": clients_collection,
        "reservations": reservations_collection,
        "mappings": mappings_collection,
        "booking_mappings": booking_mappings_collection,
    }


def test_save_booking_reservation_creates_mapping_if_not_exists(mock_firestore_client, mock_repositories):
    """Test che crea mapping se non esiste."""
    from email_agent_service.repositories.booking_property_mappings import BookingPropertyMappingsRepository
    
    # Mock booking property mapping (non esiste)
    booking_mappings_repo = BookingPropertyMappingsRepository(mock_firestore_client)
    booking_mappings_repo.get_by_booking_property_id = Mock(return_value=None)
    booking_mappings_repo.create_mapping = Mock(return_value="mapping-123")
    
    # Mock properties repo (crea nuova property)
    properties_repo = Mock()
    properties_repo.list_by_name = Mock(return_value=[])
    properties_repo.find_or_create_by_name = Mock(return_value=("property-123", True))
    
    # Mock clients repo
    clients_repo = Mock()
    clients_repo.find_or_create_by_email = Mock(return_value=("client-123", True))
    
    # Mock reservations repo
    reservations_repo = Mock()
    reservations_repo.upsert_reservation = Mock()
    
    # Parse reservation
    reservations = parse_ota_xml(MOCK_OTA_XML_RESPONSE)
    reservation = reservations[0]
    
    # Create persistence service with mocked repos
    service = PersistenceService(mock_firestore_client)
    service._booking_property_mappings_repo = booking_mappings_repo
    service._properties_repo = properties_repo
    service._clients_repo = clients_repo
    service._reservations_repo = reservations_repo
    
    # Save reservation
    result = service.save_booking_reservation(reservation, host_id="host-123")
    
    # Verifica
    assert result["saved"] is True
    assert result["property_id"] == "property-123"
    assert result["client_id"] == "client-123"
    assert result["property_created"] is True
    assert result["client_created"] is True
    
    # Verifica che mapping sia stato creato
    booking_mappings_repo.create_mapping.assert_called_once()
    call_args = booking_mappings_repo.create_mapping.call_args
    assert call_args.kwargs["booking_property_id"] == reservation.property_id
    assert call_args.kwargs["host_id"] == "host-123"
    assert call_args.kwargs["internal_property_id"] == "property-123"


def test_save_booking_reservation_uses_existing_mapping(mock_firestore_client, mock_repositories):
    """Test che usa mapping esistente."""
    from email_agent_service.repositories.booking_property_mappings import BookingPropertyMapping
    
    # Mock booking property mapping (esiste)
    booking_mapping = BookingPropertyMapping(
        id="mapping-123",
        booking_property_id="8011855",
        host_id="host-123",
        internal_property_id="property-456",
        property_name="Villa Bella Vista",
    )
    
    booking_mappings_repo = Mock()
    booking_mappings_repo.get_by_booking_property_id = Mock(return_value=booking_mapping)
    
    # Mock properties repo (property esiste)
    properties_repo = Mock()
    properties_repo.get_by_id = Mock(
        return_value={"id": "property-456", "name": "Villa Bella Vista"}
    )
    
    # Mock clients repo
    clients_repo = Mock()
    clients_repo.find_or_create_by_email = Mock(return_value=("client-123", False))
    
    # Mock reservations repo
    reservations_repo = Mock()
    reservations_repo.upsert_reservation = Mock()
    
    # Parse reservation
    reservations = parse_ota_xml(MOCK_OTA_XML_RESPONSE)
    reservation = reservations[0]
    
    # Create persistence service with mocked repos
    service = PersistenceService(mock_firestore_client)
    service._booking_property_mappings_repo = booking_mappings_repo
    service._properties_repo = properties_repo
    service._clients_repo = clients_repo
    service._reservations_repo = reservations_repo
    
    # Save reservation
    result = service.save_booking_reservation(reservation, host_id="host-123")
    
    # Verifica
    assert result["saved"] is True
    assert result["property_id"] == "property-456"  # Usa internal_property_id dal mapping
    assert result["property_created"] is False  # Property già esiste
    properties_repo.get_by_id.assert_called_once_with("property-456")


def test_save_booking_reservation_creates_client_if_not_exists(mock_firestore_client, mock_repositories):
    """Test che crea cliente se non esiste."""
    reservations = parse_ota_xml(MOCK_OTA_XML_RESPONSE)
    reservation = reservations[0]
    
    # Mock repositories
    booking_mappings_repo = Mock()
    booking_mappings_repo.get_by_booking_property_id = Mock(return_value=None)
    booking_mappings_repo.create_mapping = Mock(return_value="mapping-123")
    
    properties_repo = Mock()
    properties_repo.list_by_name = Mock(return_value=[])
    properties_repo.find_or_create_by_name = Mock(return_value=("property-123", True))
    
    clients_repo = Mock()
    clients_repo.find_or_create_by_email = Mock(return_value=("client-456", True))
    
    reservations_repo = Mock()
    reservations_repo.upsert_reservation = Mock()
    
    service = PersistenceService(mock_firestore_client)
    service._booking_property_mappings_repo = booking_mappings_repo
    service._properties_repo = properties_repo
    service._clients_repo = clients_repo
    service._reservations_repo = reservations_repo
    
    # Save reservation
    result = service.save_booking_reservation(reservation, host_id="host-123")
    
    # Verifica
    assert result["saved"] is True
    assert result["client_created"] is True
    
    # Verifica chiamata find_or_create_by_email
    clients_repo.find_or_create_by_email.assert_called_once()
    call_args = clients_repo.find_or_create_by_email.call_args
    assert call_args.kwargs["host_id"] == "host-123"
    assert call_args.kwargs["email"] == reservation.guest_info.email
    assert call_args.kwargs["name"] == reservation.guest_info.name
    assert call_args.kwargs["phone"] == reservation.guest_info.phone
    assert call_args.kwargs["reservation_id"] == reservation.reservation_id


def test_save_booking_reservation_saves_reservation(mock_firestore_client, mock_repositories):
    """Test che salva reservation correttamente."""
    reservations = parse_ota_xml(MOCK_OTA_XML_RESPONSE)
    reservation = reservations[0]
    
    # Mock repositories
    booking_mappings_repo = Mock()
    booking_mappings_repo.get_by_booking_property_id = Mock(return_value=None)
    booking_mappings_repo.create_mapping = Mock(return_value="mapping-123")
    
    properties_repo = Mock()
    properties_repo.list_by_name = Mock(return_value=[])
    properties_repo.find_or_create_by_name = Mock(return_value=("property-123", True))
    
    clients_repo = Mock()
    clients_repo.find_or_create_by_email = Mock(return_value=("client-123", True))
    
    reservations_repo = Mock()
    reservations_repo.upsert_reservation = Mock()
    
    service = PersistenceService(mock_firestore_client)
    service._booking_property_mappings_repo = booking_mappings_repo
    service._properties_repo = properties_repo
    service._clients_repo = clients_repo
    service._reservations_repo = reservations_repo
    
    # Save reservation
    result = service.save_booking_reservation(reservation, host_id="host-123")
    
    # Verifica
    assert result["saved"] is True
    assert result["reservation_saved"] is True
    
    # Verifica chiamata upsert_reservation
    reservations_repo.upsert_reservation.assert_called_once()
    call_args = reservations_repo.upsert_reservation.call_args
    assert call_args.kwargs["reservation_id"] == reservation.reservation_id
    assert call_args.kwargs["host_id"] == "host-123"
    assert call_args.kwargs["property_id"] == "property-123"
    assert call_args.kwargs["client_id"] == "client-123"
    assert call_args.kwargs["start_date"] == reservation.check_in
    assert call_args.kwargs["end_date"] == reservation.check_out
    assert call_args.kwargs["status"] == "confirmed"
    assert call_args.kwargs["total_price"] == reservation.total_amount
    assert call_args.kwargs["adults"] == reservation.adults
    assert call_args.kwargs["source_channel"] == "booking"
    assert call_args.kwargs["imported_from"] == "booking_api"

