"""Unit tests per BookingReservationParser."""

import pytest
from datetime import datetime

from email_agent_service.models.booking_reservation import BookingReservation
from email_agent_service.parsers.booking_reservation_parser import (
    BookingReservationParserError,
    parse_ota_xml,
)
from tests.fixtures.booking_api_responses import MOCK_OTA_XML_RESPONSE


def test_parse_ota_xml_basic():
    """Test parsing base XML OTA."""
    reservations = parse_ota_xml(MOCK_OTA_XML_RESPONSE)
    
    assert len(reservations) == 1
    reservation = reservations[0]
    
    assert reservation.reservation_id == "4705950059"
    assert reservation.property_id == "8011855"
    assert reservation.guest_info.email == "test.guest@example.com"
    assert reservation.guest_info.name == "Test Guest"
    assert reservation.total_amount == 500.0
    assert reservation.currency == "EUR"


def test_parse_ota_xml_extract_dates():
    """Test estrazione date check-in/check-out."""
    reservations = parse_ota_xml(MOCK_OTA_XML_RESPONSE)
    
    assert len(reservations) == 1
    reservation = reservations[0]
    
    assert reservation.check_in is not None
    assert reservation.check_out is not None
    assert isinstance(reservation.check_in, datetime)
    assert isinstance(reservation.check_out, datetime)
    assert reservation.check_out > reservation.check_in


def test_parse_ota_xml_extract_guest_info():
    """Test estrazione informazioni guest."""
    reservations = parse_ota_xml(MOCK_OTA_XML_RESPONSE)
    
    assert len(reservations) == 1
    reservation = reservations[0]
    
    assert reservation.guest_info.name == "Test Guest"
    assert reservation.guest_info.email == "test.guest@example.com"
    assert reservation.guest_info.phone == "+39 333 1234567"
    assert reservation.guest_info.given_name == "Test"
    assert reservation.guest_info.surname == "Guest"


def test_parse_ota_xml_extract_guest_counts():
    """Test estrazione numero guests."""
    reservations = parse_ota_xml(MOCK_OTA_XML_RESPONSE)
    
    assert len(reservations) == 1
    reservation = reservations[0]
    
    assert reservation.adults == 2
    assert reservation.children == 0


def test_parse_ota_xml_empty_xml():
    """Test parsing XML vuoto."""
    empty_xml = """<?xml version="1.0" encoding="UTF-8"?>
<OTA_HotelResNotifRQ xmlns="http://www.opentravel.org/OTA/2003/05">
    <HotelReservations/>
</OTA_HotelResNotifRQ>"""
    
    reservations = parse_ota_xml(empty_xml)
    assert len(reservations) == 0


def test_parse_ota_xml_invalid_xml():
    """Test parsing XML invalido."""
    invalid_xml = "<invalid>xml</invalid>"
    
    with pytest.raises(BookingReservationParserError):
        parse_ota_xml(invalid_xml)


def test_parse_ota_xml_missing_required_fields():
    """Test parsing XML con campi richiesti mancanti."""
    # XML senza HotelReservationIDs
    xml_missing_res_id = """<?xml version="1.0" encoding="UTF-8"?>
<OTA_HotelResNotifRQ xmlns="http://www.opentravel.org/OTA/2003/05">
    <HotelReservations>
        <HotelReservation>
            <ResGlobalInfo>
                <Profiles>
                    <ProfileInfo>
                        <Profile>
                            <Customer>
                                <Email>test@example.com</Email>
                            </Customer>
                        </Profile>
                    </ProfileInfo>
                </Profiles>
            </ResGlobalInfo>
        </HotelReservation>
    </HotelReservations>
</OTA_HotelResNotifRQ>"""
    
    with pytest.raises(BookingReservationParserError):
        parse_ota_xml(xml_missing_res_id)


def test_parse_ota_xml_reservation_to_firestore_format():
    """Test conversione reservation a formato Firestore."""
    reservations = parse_ota_xml(MOCK_OTA_XML_RESPONSE)
    
    assert len(reservations) == 1
    reservation = reservations[0]
    
    firestore_format = reservation.to_firestore_format(host_id="host-123", client_id="client-456")
    
    assert firestore_format["reservationId"] == "4705950059"
    assert firestore_format["propertyId"] == "8011855"
    assert firestore_format["channel"] == "booking"
    assert firestore_format["status"] == "confirmed"
    assert firestore_format["totals"]["amount"] == 500.0
    assert firestore_format["totals"]["currency"] == "EUR"
    assert firestore_format["guests"]["adults"] == 2
    assert firestore_format["source"]["provider"] == "booking-api"


def test_parse_ota_xml_reservation_date():
    """Test estrazione data creazione prenotazione."""
    reservations = parse_ota_xml(MOCK_OTA_XML_RESPONSE)
    
    assert len(reservations) == 1
    reservation = reservations[0]
    
    assert reservation.reservation_date is not None
    assert isinstance(reservation.reservation_date, datetime)
    assert reservation.reservation_date.year == 2025
    assert reservation.reservation_date.month == 1
    assert reservation.reservation_date.day == 15


def test_parse_ota_xml_commission():
    """Test estrazione commission amount."""
    reservations = parse_ota_xml(MOCK_OTA_XML_RESPONSE)
    
    assert len(reservations) == 1
    reservation = reservations[0]
    
    # Nel mock XML c'è commission Amount="50" = 50.00 EUR (Amount è valore finale)
    assert reservation.commission_amount == 50.0

