from email.message import EmailMessage

from email_agent_service.parsers.booking_confirm import BookingConfirmationParser
from email_agent_service.parsers.booking_message import BookingMessageParser
from email_agent_service.parsers.base import EmailContent

BOOKING_CONFIRM_TEXT = """
Subject: Confermata - Prenotazione ID 5958915259 - Booking
Nome Ospite: Brufani Francesco
Struttura Richiesta: Piazza Danti Perugia Centro
Data di Check-in: 15/01/2026
Data di Check-out: 18/01/2026
Ospiti: 2 Adulti
Totale Prenotazione: 349,55 €"""

BOOKING_MESSAGE_TEXT = """
Numero di conferma: 5958915259
Francesco Brufani ha scritto:
#- Scrivi la tua risposta sopra questa riga -#
Ciao, è possibile portare un cane?
"""


def build_message(subject: str, sender: str, text: str) -> EmailContent:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = "host@example.com"
    message["Date"] = "Thu, 23 Oct 2025 09:42:29 +0000"
    message.set_content(text)
    return EmailContent(message=message, text=text, html=None)


def test_booking_confirmation_parser():
    parser = BookingConfirmationParser()
    content = build_message(
        "Confermata - Prenotazione ID 5958915259 - Booking",
        "Scidoo Booking Manager <reservation@scidoo.com>",
        BOOKING_CONFIRM_TEXT,
    )

    assert parser.matches(content)
    parsed = parser.parse(content)

    assert parsed.kind == "booking_confirmation"
    assert parsed.reservation is not None
    assert parsed.reservation.reservation_id == "5958915259"
    assert parsed.reservation.property_name == "Piazza Danti Perugia Centro"
    assert parsed.reservation.guest_name == "Brufani Francesco"
    assert parsed.reservation.adults == 2
    assert parsed.reservation.total_amount == 349.55


def test_booking_message_parser():
    parser = BookingMessageParser()
    content = build_message(
        "Abbiamo ricevuto questo messaggio da Francesco Brufani",
        "5958915259-XYZ@mchat.booking.com",
        BOOKING_MESSAGE_TEXT,
    )

    assert parser.matches(content)
    parsed = parser.parse(content)

    assert parsed.kind == "booking_message"
    assert parsed.guest_message is not None
    assert parsed.guest_message.reservation_id == "5958915259"
    assert parsed.guest_message.message == "Ciao, è possibile portare un cane?"

