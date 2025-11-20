"""Unit tests per BookingMessageProcessor."""

import pytest
from datetime import datetime

from email_agent_service.models.booking_message import (
    BookingConversation,
    BookingMessage,
    BookingSender,
)
from email_agent_service.services.booking_message_processor import BookingMessageProcessor


@pytest.fixture
def sample_guest_message():
    """Messaggio guest di esempio."""
    return BookingMessage(
        message_id="msg-123",
        content="Ciao, vorrei informazioni sul check-in",
        timestamp=datetime(2025, 3, 20, 10, 0, 0),
        sender=BookingSender(
            participant_id="guest-123",
            participant_type="GUEST",
            name="Mario Rossi",
            email_alias="mario.rossi@example.com",
        ),
        conversation=BookingConversation(
            conversation_id="conv-456",
            conversation_type="reservation",
            conversation_reference="reservation-789",
            property_id=8011855,
        ),
    )


def test_process_message_converts_to_parsed_email(sample_guest_message):
    """Test che process_message converte correttamente BookingMessage → ParsedEmail."""
    parsed_email = BookingMessageProcessor.process_message(sample_guest_message)
    
    assert parsed_email.kind == "booking_message"
    assert parsed_email.guest_message is not None
    assert parsed_email.guest_message.reservation_id == "reservation-789"
    assert parsed_email.guest_message.source == "booking"
    assert parsed_email.guest_message.message == "Ciao, vorrei informazioni sul check-in"
    assert parsed_email.guest_message.guest_name == "Mario Rossi"
    assert parsed_email.guest_message.guest_email == "mario.rossi@example.com"
    assert parsed_email.raw_text == "Ciao, vorrei informazioni sul check-in"
    assert parsed_email.metadata.received_at == sample_guest_message.timestamp


def test_process_message_raises_for_non_guest():
    """Test che process_message solleva errore per messaggi non-GUEST."""
    property_message = BookingMessage(
        message_id="msg-123",
        content="Test",
        timestamp=datetime.now(),
        sender=BookingSender(
            participant_id="property-123",
            participant_type="property",
            name="Test Property",
        ),
        conversation=BookingConversation(
            conversation_id="conv-456",
            conversation_type="reservation",
            conversation_reference="reservation-789",
            property_id=8011855,
        ),
    )
    
    with pytest.raises(ValueError, match="non-GUEST"):
        BookingMessageProcessor.process_message(property_message)


def test_process_message_raises_for_missing_conversation_reference():
    """Test che process_message solleva errore se manca conversation_reference."""
    message_without_ref = BookingMessage(
        message_id="msg-123",
        content="Test",
        timestamp=datetime.now(),
        sender=BookingSender(
            participant_id="guest-123",
            participant_type="GUEST",
            name="Test Guest",
        ),
        conversation=BookingConversation(
            conversation_id="conv-456",
            conversation_type="reservation",
            conversation_reference="",  # Empty
            property_id=8011855,
        ),
    )
    
    with pytest.raises(ValueError, match="conversation_reference"):
        BookingMessageProcessor.process_message(message_without_ref)


def test_should_process_message_returns_true_for_guest():
    """Test che should_process_message ritorna True per messaggi guest."""
    guest_message = BookingMessage(
        message_id="msg-123",
        content="Test",
        timestamp=datetime.now(),
        sender=BookingSender(
            participant_id="guest-123",
            participant_type="GUEST",
            name="Test Guest",
        ),
        conversation=BookingConversation(
            conversation_id="conv-456",
            conversation_type="reservation",
            conversation_reference="reservation-789",
            property_id=8011855,
        ),
        message_type="free_text",
    )
    
    assert BookingMessageProcessor.should_process_message(guest_message) is True


def test_should_process_message_returns_false_for_non_guest():
    """Test che should_process_message ritorna False per messaggi non-GUEST."""
    property_message = BookingMessage(
        message_id="msg-123",
        content="Test",
        timestamp=datetime.now(),
        sender=BookingSender(
            participant_id="property-123",
            participant_type="property",
            name="Test Property",
        ),
        conversation=BookingConversation(
            conversation_id="conv-456",
            conversation_type="reservation",
            conversation_reference="reservation-789",
            property_id=8011855,
        ),
    )
    
    assert BookingMessageProcessor.should_process_message(property_message) is False


def test_should_process_message_returns_false_for_self_service_event():
    """Test che should_process_message ritorna False per self-service events."""
    self_service_message = BookingMessage(
        message_id="msg-123",
        content="Test",
        timestamp=datetime.now(),
        sender=BookingSender(
            participant_id="guest-123",
            participant_type="GUEST",
            name="Test Guest",
        ),
        conversation=BookingConversation(
            conversation_id="conv-456",
            conversation_type="reservation",
            conversation_reference="reservation-789",
            property_id=8011855,
        ),
        message_type="self_service_event",
    )
    
    assert BookingMessageProcessor.should_process_message(self_service_message) is False


def test_should_process_message_returns_false_for_missing_reference():
    """Test che should_process_message ritorna False se manca conversation_reference."""
    message_without_ref = BookingMessage(
        message_id="msg-123",
        content="Test",
        timestamp=datetime.now(),
        sender=BookingSender(
            participant_id="guest-123",
            participant_type="GUEST",
            name="Test Guest",
        ),
        conversation=BookingConversation(
            conversation_id="conv-456",
            conversation_type="reservation",
            conversation_reference="",  # Empty
            property_id=8011855,
        ),
    )
    
    assert BookingMessageProcessor.should_process_message(message_without_ref) is False

