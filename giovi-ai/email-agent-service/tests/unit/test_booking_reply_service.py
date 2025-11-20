"""Unit tests per BookingReplyService."""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock

from email_agent_service.models.booking_message import (
    BookingConversation,
    BookingMessage,
    BookingSender,
)
from email_agent_service.services.booking_reply_service import BookingReplyService
from email_agent_service.services.guest_message_pipeline import GuestMessageContext


@pytest.fixture
def mock_messaging_client():
    """Mock BookingMessagingClient."""
    client = Mock()
    client.mock_mode = True
    return client


@pytest.fixture
def sample_booking_message():
    """Messaggio Booking.com di esempio."""
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


@pytest.fixture
def sample_context():
    """Contesto guest message di esempio."""
    return GuestMessageContext(
        host_id="host-123",
        client_id="client-456",
        property_id="property-789",
        reservation_id="reservation-789",
        property_name="Villa Bella Vista",
        client_name="Mario Rossi",
        client_email="mario.rossi@example.com",
    )


def test_send_reply_success(mock_messaging_client, sample_booking_message, sample_context):
    """Test invio risposta con successo."""
    # Setup mock
    mock_response = {
        "data": {
            "message_id": "sent-msg-456",
        },
        "errors": [],
    }
    mock_messaging_client.send_message.return_value = mock_response
    mock_messaging_client.mark_as_read.return_value = {"data": {"ok": True}}
    
    # Create service
    service = BookingReplyService(mock_messaging_client)
    
    # Send reply
    sent_message_id = service.send_reply(
        booking_message=sample_booking_message,
        reply_text="Ciao! Ti rispondo...",
        context=sample_context,
        mark_as_read=True,
    )
    
    # Verifica
    assert sent_message_id == "sent-msg-456"
    mock_messaging_client.send_message.assert_called_once_with(
        property_id=8011855,
        conversation_id="conv-456",
        content="Ciao! Ti rispondo...",
        attachment_ids=None,
    )
    mock_messaging_client.mark_as_read.assert_called_once()


def test_send_reply_without_mark_as_read(mock_messaging_client, sample_booking_message):
    """Test invio risposta senza marcare come letto."""
    mock_response = {
        "data": {
            "message_id": "sent-msg-456",
        },
    }
    mock_messaging_client.send_message.return_value = mock_response
    
    service = BookingReplyService(mock_messaging_client)
    
    sent_message_id = service.send_reply(
        booking_message=sample_booking_message,
        reply_text="Test reply",
        mark_as_read=False,
    )
    
    assert sent_message_id == "sent-msg-456"
    mock_messaging_client.send_message.assert_called_once()
    mock_messaging_client.mark_as_read.assert_not_called()


def test_send_reply_raises_for_missing_conversation_id(mock_messaging_client):
    """Test che send_reply solleva errore se manca conversation_id."""
    message_without_conv = BookingMessage(
        message_id="msg-123",
        content="Test",
        timestamp=datetime.now(),
        sender=BookingSender(
            participant_id="guest-123",
            participant_type="GUEST",
        ),
        conversation=BookingConversation(
            conversation_id="",  # Empty
            conversation_type="reservation",
            conversation_reference="reservation-789",
            property_id=8011855,
        ),
    )
    
    service = BookingReplyService(mock_messaging_client)
    
    with pytest.raises(ValueError, match="conversation_id"):
        service.send_reply(
            booking_message=message_without_conv,
            reply_text="Test",
        )


def test_send_reply_raises_for_missing_property_id(mock_messaging_client):
    """Test che send_reply solleva errore se manca property_id."""
    message_without_property = BookingMessage(
        message_id="msg-123",
        content="Test",
        timestamp=datetime.now(),
        sender=BookingSender(
            participant_id="guest-123",
            participant_type="GUEST",
        ),
        conversation=BookingConversation(
            conversation_id="conv-456",
            conversation_type="reservation",
            conversation_reference="reservation-789",
            property_id=None,  # None
        ),
    )
    
    service = BookingReplyService(mock_messaging_client)
    
    with pytest.raises(ValueError, match="property_id"):
        service.send_reply(
            booking_message=message_without_property,
            reply_text="Test",
        )


def test_send_reply_handles_mark_as_read_error(mock_messaging_client, sample_booking_message):
    """Test che send_reply continua anche se mark_as_read fallisce."""
    mock_response = {
        "data": {
            "message_id": "sent-msg-456",
        },
    }
    mock_messaging_client.send_message.return_value = mock_response
    mock_messaging_client.mark_as_read.side_effect = Exception("Mark as read failed")
    
    service = BookingReplyService(mock_messaging_client)
    
    # Non deve sollevare eccezione
    sent_message_id = service.send_reply(
        booking_message=sample_booking_message,
        reply_text="Test",
        mark_as_read=True,
    )
    
    assert sent_message_id == "sent-msg-456"


def test_send_reply_with_context(mock_messaging_client, sample_booking_message, sample_context):
    """Test send_reply_with_context wrapper."""
    mock_response = {
        "data": {
            "message_id": "sent-msg-456",
        },
    }
    mock_messaging_client.send_message.return_value = mock_response
    mock_messaging_client.mark_as_read.return_value = {"data": {"ok": True}}
    
    service = BookingReplyService(mock_messaging_client)
    
    sent_message_id = service.send_reply_with_context(
        booking_message=sample_booking_message,
        context=sample_context,
        reply_text="Test reply",
    )
    
    assert sent_message_id == "sent-msg-456"
    mock_messaging_client.send_message.assert_called_once()

