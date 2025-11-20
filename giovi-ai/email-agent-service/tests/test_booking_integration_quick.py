#!/usr/bin/env python3
"""Quick test tecnico per integrazione Booking.com - senza pytest."""

import sys
import os
# Aggiungi src al path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, '..', 'src')
sys.path.insert(0, src_dir)

from datetime import datetime
from unittest.mock import Mock

# Test 1: BookingMessageProcessor
print("=" * 60)
print("TEST 1: BookingMessageProcessor")
print("=" * 60)

from email_agent_service.models.booking_message import (
    BookingConversation,
    BookingMessage,
    BookingSender,
)
from email_agent_service.services.booking_message_processor import BookingMessageProcessor

# Crea messaggio guest di esempio
guest_message = BookingMessage(
    message_id="msg-test-123",
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

# Test should_process_message
assert BookingMessageProcessor.should_process_message(guest_message) is True, "should_process_message deve ritornare True per messaggi GUEST"
print("✅ should_process_message: OK")

# Test process_message
parsed_email = BookingMessageProcessor.process_message(guest_message)
assert parsed_email.kind == "booking_message", "kind deve essere 'booking_message'"
assert parsed_email.guest_message.reservation_id == "reservation-789", "reservation_id deve corrispondere"
assert parsed_email.guest_message.source == "booking", "source deve essere 'booking'"
print("✅ process_message: OK")
print(f"   - reservation_id: {parsed_email.guest_message.reservation_id}")
print(f"   - guest_name: {parsed_email.guest_message.guest_name}")
print(f"   - message: {parsed_email.guest_message.message[:50]}...")

# Test filtro non-GUEST
property_message = BookingMessage(
    message_id="msg-property",
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
assert BookingMessageProcessor.should_process_message(property_message) is False, "should_process_message deve ritornare False per messaggi non-GUEST"
print("✅ Filtro non-GUEST: OK")

print("\n" + "=" * 60)
print("TEST 2: BookingReplyService (con mock)")
print("=" * 60)

from email_agent_service.services.booking_reply_service import BookingReplyService
from email_agent_service.services.guest_message_pipeline import GuestMessageContext

# Mock client
mock_client = Mock()
mock_client.mock_mode = True
mock_client.send_message.return_value = {
    "data": {
        "message_id": "sent-msg-456",
    },
    "errors": [],
}
mock_client.mark_as_read.return_value = {"data": {"ok": True}}

# Crea service
reply_service = BookingReplyService(mock_client)
print("✅ BookingReplyService inizializzato")

# Crea contesto
context = GuestMessageContext(
    host_id="host-123",
    client_id="client-456",
    property_id="property-789",
    reservation_id="reservation-789",
    property_name="Villa Bella Vista",
    property_data={},
    client_name="Mario Rossi",
    client_email="mario.rossi@example.com",
)

# Test send_reply
sent_message_id = reply_service.send_reply(
    booking_message=guest_message,
    reply_text="Ciao! Grazie per il messaggio. Ti rispondo...",
    context=context,
    mark_as_read=True,
)

assert sent_message_id == "sent-msg-456", "message_id deve corrispondere"
assert mock_client.send_message.called, "send_message deve essere chiamato"
assert mock_client.mark_as_read.called, "mark_as_read deve essere chiamato"
print("✅ send_reply: OK")
print(f"   - sent_message_id: {sent_message_id}")
print(f"   - property_id usato: {mock_client.send_message.call_args[0][0]}")
print(f"   - conversation_id usato: {mock_client.send_message.call_args[0][1]}")

print("\n" + "=" * 60)
print("TEST 3: Integrazione end-to-end (struttura)")
print("=" * 60)

# Verifica che tutti i componenti siano collegabili
from email_agent_service.services.booking_message_polling_service import BookingMessagePollingService
from email_agent_service.services.integrations.booking_messaging_client import BookingMessagingClient

# Crea client mock
mock_messaging_client = BookingMessagingClient(mock_mode=True)
mock_persistence = Mock()
mock_firestore = Mock()
mock_gemini = Mock()
mock_gemini.generate_reply.return_value = "Risposta AI generata"

# Crea polling service (non lo avviamo, solo verifichiamo struttura)
polling_service = BookingMessagePollingService(
    messaging_client=mock_messaging_client,
    persistence_service=mock_persistence,
    firestore_client=mock_firestore,
    gemini_service=mock_gemini,
    polling_interval=60,
)

assert hasattr(polling_service, '_message_processor'), "PollingService deve avere _message_processor"
assert hasattr(polling_service, '_reply_service'), "PollingService deve avere _reply_service"
assert hasattr(polling_service, '_pipeline_service'), "PollingService deve avere _pipeline_service"
print("✅ BookingMessagePollingService struttura OK")
print("   - _message_processor: presente")
print("   - _reply_service: presente")
print("   - _pipeline_service: presente")

print("\n" + "=" * 60)
print("✅ TUTTI I TEST TECNICI SUPERATI!")
print("=" * 60)
print("\nComponenti testati:")
print("  ✅ BookingMessageProcessor (conversione e filtri)")
print("  ✅ BookingReplyService (invio risposte)")
print("  ✅ Integrazione strutturale (tutti i componenti collegabili)")
print("\nIl sistema è pronto per test con credenziali reali!")

