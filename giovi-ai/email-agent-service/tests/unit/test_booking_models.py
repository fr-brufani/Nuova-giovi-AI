"""Unit tests per modelli Booking.com."""

import pytest
from datetime import datetime

from email_agent_service.models.booking_message import (
    BookingConversation,
    BookingMessage,
    BookingMessageAttributes,
    BookingSender,
)
from email_agent_service.models.booking_reservation import (
    BookingGuestInfo,
    BookingPaymentInfo,
    BookingReservation,
)
from tests.fixtures.booking_api_responses import MOCK_MESSAGES_LATEST_RESPONSE


def test_booking_message_from_api_response():
    """Test creazione BookingMessage da response API."""
    message_data = MOCK_MESSAGES_LATEST_RESPONSE["data"]["messages"][0]
    
    booking_message = BookingMessage.from_api_response(message_data)
    
    assert booking_message.message_id == message_data["message_id"]
    assert booking_message.content == message_data["content"]
    assert booking_message.sender.participant_id == message_data["sender"]["participant_id"]
    assert booking_message.sender.participant_type == "GUEST"
    assert booking_message.sender.name == "Test Guest"
    assert booking_message.conversation.conversation_id == message_data["conversation"]["conversation_id"]
    assert booking_message.conversation.conversation_reference == "3812391309"
    assert isinstance(booking_message.timestamp, datetime)


def test_booking_message_to_internal_format():
    """Test conversione BookingMessage a formato interno."""
    message_data = MOCK_MESSAGES_LATEST_RESPONSE["data"]["messages"][0]
    booking_message = BookingMessage.from_api_response(message_data)
    
    internal = booking_message.to_internal_format()
    
    assert internal["kind"] == "booking_message"
    assert internal["source"] == "booking_api"
    assert internal["reservation_id"] == "3812391309"
    assert internal["message"] == message_data["content"]
    assert internal["guest_name"] == "Test Guest"
    assert internal["message_id"] == message_data["message_id"]
    assert "conversation_id" in internal


def test_booking_message_to_guest_message_info():
    """Test conversione BookingMessage a GuestMessageInfo format."""
    message_data = MOCK_MESSAGES_LATEST_RESPONSE["data"]["messages"][0]
    booking_message = BookingMessage.from_api_response(message_data)
    
    guest_info_format = booking_message.to_guest_message_info_format()
    
    assert guest_info_format["reservationId"] == "3812391309"
    assert guest_info_format["source"] == "booking"
    assert guest_info_format["message"] == message_data["content"]
    assert guest_info_format["guestName"] == "Test Guest"
    assert guest_info_format["threadId"] is None  # Booking non usa thread_id


def test_booking_reservation_to_firestore_format():
    """Test conversione BookingReservation a formato Firestore."""
    guest_info = BookingGuestInfo(
        name="Test Guest",
        email="test.guest@example.com",
        phone="+39 333 1234567",
    )
    
    reservation = BookingReservation(
        reservation_id="4705950059",
        property_id="8011855",
        check_in=datetime(2025, 3, 29),
        check_out=datetime(2025, 3, 31),
        guest_info=guest_info,
        adults=2,
        children=0,
        total_amount=500.0,
        currency="EUR",
        reservation_date=datetime(2025, 1, 15, 10, 0, 0),
    )
    
    firestore_format = reservation.to_firestore_format(host_id="host-123", client_id="client-456")
    
    assert firestore_format["reservationId"] == "4705950059"
    assert firestore_format["hostId"] == "host-123"
    assert firestore_format["propertyId"] == "8011855"
    assert firestore_format["clientId"] == "client-456"
    assert firestore_format["channel"] == "booking"
    assert firestore_format["status"] == "confirmed"
    assert firestore_format["stayPeriod"]["start"] == "2025-03-29T00:00:00"
    assert firestore_format["stayPeriod"]["end"] == "2025-03-31T00:00:00"
    assert firestore_format["totals"]["amount"] == 500.0
    assert firestore_format["totals"]["currency"] == "EUR"
    assert firestore_format["guests"]["adults"] == 2
    assert firestore_format["guests"]["children"] == 0
    assert firestore_format["source"]["provider"] == "booking-api"
    assert firestore_format["source"]["externalId"] == "4705950059"
    assert firestore_format["importedFrom"] == "booking_api"


def test_booking_reservation_to_internal_format():
    """Test conversione BookingReservation a formato interno ReservationInfo."""
    guest_info = BookingGuestInfo(
        name="Test Guest",
        email="test.guest@example.com",
        phone="+39 333 1234567",
    )
    
    reservation = BookingReservation(
        reservation_id="4705950059",
        property_id="8011855",
        check_in=datetime(2025, 3, 29),
        check_out=datetime(2025, 3, 31),
        guest_info=guest_info,
        adults=2,
        children=1,
        total_amount=500.0,
        currency="EUR",
    )
    
    internal = reservation.to_internal_format()
    
    assert internal["reservationId"] == "4705950059"
    assert internal["source"] == "booking"
    assert internal["propertyExternalId"] == "8011855"
    assert internal["checkIn"] == datetime(2025, 3, 29)
    assert internal["checkOut"] == datetime(2025, 3, 31)
    assert internal["guestName"] == "Test Guest"
    assert internal["guestEmail"] == "test.guest@example.com"
    assert internal["guestPhone"] == "+39 333 1234567"
    assert internal["adults"] == 2
    assert internal["children"] == 1
    assert internal["totalAmount"] == 500.0
    assert internal["currency"] == "EUR"


def test_booking_sender_dataclass():
    """Test creazione BookingSender."""
    sender = BookingSender(
        participant_id="guest-123",
        participant_type="GUEST",
        name="Test Guest",
        email_alias="guest@example.com",
    )
    
    assert sender.participant_id == "guest-123"
    assert sender.participant_type == "GUEST"
    assert sender.name == "Test Guest"
    assert sender.email_alias == "guest@example.com"


def test_booking_conversation_dataclass():
    """Test creazione BookingConversation."""
    conversation = BookingConversation(
        conversation_id="conv-123",
        conversation_type="reservation",
        conversation_reference="9876543210",
        property_id="8011855",
    )
    
    assert conversation.conversation_id == "conv-123"
    assert conversation.conversation_type == "reservation"
    assert conversation.conversation_reference == "9876543210"
    assert conversation.property_id == "8011855"


def test_booking_guest_info_dataclass():
    """Test creazione BookingGuestInfo."""
    guest = BookingGuestInfo(
        name="Test Guest",
        email="test@example.com",
        phone="+39 333 1234567",
        surname="Guest",
        given_name="Test",
    )
    
    assert guest.name == "Test Guest"
    assert guest.email == "test@example.com"
    assert guest.phone == "+39 333 1234567"
    assert guest.surname == "Guest"
    assert guest.given_name == "Test"


def test_booking_payment_info_dataclass():
    """Test creazione BookingPaymentInfo."""
    payment = BookingPaymentInfo(
        vcc_number="4111111111111111",
        vcc_cvc="123",
        vcc_expiry_date="12/25",
        vcc_effective_date=datetime(2025, 1, 15),
        vcc_current_balance=500.0,
        card_holder_name="Test Guest",
        is_payments_by_booking=True,
    )
    
    assert payment.vcc_number == "4111111111111111"
    assert payment.vcc_cvc == "123"
    assert payment.is_payments_by_booking is True
