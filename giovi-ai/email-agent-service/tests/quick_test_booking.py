#!/usr/bin/env python3
"""
Script di test rapido per Booking.com integration (senza pytest).

Esegui senza pytest per test rapido: python3 tests/quick_test_booking.py

Questo script verifica che tutti i componenti base funzionino correttamente
con mock mode, senza bisogno di credenziali reali o dipendenze installate.
"""

import sys
from pathlib import Path

# Aggiungi src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from datetime import datetime


def test_models():
    """Test import e creazione modelli."""
    print("\n🧪 Test Modelli Dati...")
    
    try:
        from email_agent_service.models.booking_message import (
            BookingConversation,
            BookingMessage,
            BookingSender,
        )
        from email_agent_service.models.booking_reservation import (
            BookingGuestInfo,
            BookingReservation,
        )
        print("  ✅ Import modelli OK")
        
        # Test BookingMessage
        sender = BookingSender(
            participant_id="test-123",
            participant_type="GUEST",
            name="Test Guest",
        )
        conversation = BookingConversation(
            conversation_id="conv-123",
            conversation_type="reservation",
            conversation_reference="9876543210",
        )
        message = BookingMessage(
            message_id="msg-123",
            content="Test message",
            timestamp=datetime.now(),
            sender=sender,
            conversation=conversation,
        )
        print(f"  ✅ BookingMessage creato: {message.message_id}")
        
        # Test BookingReservation
        guest = BookingGuestInfo(name="Test", email="test@test.com")
        reservation = BookingReservation(
            reservation_id="res-123",
            property_id="8011855",
            check_in=datetime.now(),
            check_out=datetime.now(),
            guest_info=guest,
            adults=2,
            total_amount=100.0,
            currency="EUR",
        )
        print(f"  ✅ BookingReservation creato: {reservation.reservation_id}")
        
        return True
    except Exception as e:
        print(f"  ❌ Errore modelli: {e}")
        return False


def test_clients():
    """Test client API in mock mode."""
    print("\n🧪 Test Client API (Mock Mode)...")
    
    try:
        from email_agent_service.services.integrations.booking_messaging_client import (
            BookingMessagingClient,
        )
        from email_agent_service.services.integrations.booking_reservation_client import (
            BookingReservationClient,
        )
        print("  ✅ Import client OK")
        
        # Test Messaging Client
        messaging_client = BookingMessagingClient(mock_mode=True)
        assert messaging_client.mock_mode is True
        print("  ✅ BookingMessagingClient inizializzato (mock mode)")
        
        response = messaging_client.get_latest_messages()
        assert "data" in response
        assert response["data"]["ok"] is True
        print(f"  ✅ get_latest_messages() OK - {response['data']['number_of_messages']} messaggi")
        
        # Test Reservation Client
        reservation_client = BookingReservationClient(mock_mode=True)
        assert reservation_client.mock_mode is True
        print("  ✅ BookingReservationClient inizializzato (mock mode)")
        
        xml_response = reservation_client.get_new_reservations()
        assert "OTA_HotelResNotifRQ" in xml_response
        print("  ✅ get_new_reservations() OK - XML ricevuto")
        
        return True
    except Exception as e:
        print(f"  ❌ Errore client: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_message_conversion():
    """Test conversione messaggi."""
    print("\n🧪 Test Conversione Messaggi...")
    
    try:
        from email_agent_service.models.booking_message import BookingMessage
        from tests.fixtures.booking_api_responses import MOCK_MESSAGES_LATEST_RESPONSE
        
        message_data = MOCK_MESSAGES_LATEST_RESPONSE["data"]["messages"][0]
        booking_message = BookingMessage.from_api_response(message_data)
        
        # Test conversione formato interno
        internal = booking_message.to_internal_format()
        assert internal["kind"] == "booking_message"
        assert internal["source"] == "booking_api"
        assert internal["reservation_id"] == "3812391309"
        print("  ✅ Conversione formato interno OK")
        
        # Test conversione GuestMessageInfo
        guest_info = booking_message.to_guest_message_info_format()
        assert guest_info["reservationId"] == "3812391309"
        assert guest_info["source"] == "booking"
        print("  ✅ Conversione GuestMessageInfo OK")
        
        return True
    except Exception as e:
        print(f"  ❌ Errore conversione: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Esegui tutti i test rapidi."""
    print("=" * 60)
    print("🚀 Quick Test Booking.com Integration (Mock Mode)")
    print("=" * 60)
    
    results = []
    results.append(("Modelli Dati", test_models()))
    results.append(("Client API", test_clients()))
    results.append(("Conversione Messaggi", test_message_conversion()))
    
    print("\n" + "=" * 60)
    print("📊 Risultati Test:")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} - {name}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("✅ Tutti i test sono passati!")
        print("\n💡 Per test completi con pytest:")
        print("   pytest tests/unit/test_booking_*.py -v")
        return 0
    else:
        print("❌ Alcuni test sono falliti!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
