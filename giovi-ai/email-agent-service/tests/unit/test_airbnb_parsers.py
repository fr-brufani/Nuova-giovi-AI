from email.message import EmailMessage

from email_agent_service.parsers.airbnb_confirm import AirbnbConfirmationParser
from email_agent_service.parsers.airbnb_message import AirbnbMessageParser
from email_agent_service.parsers.base import EmailContent

AIRBNB_CONFIRM_TEXT = """
Subject: Prenotazione confermata - Edward Cadagin arriverà il 10 set
CODICE DI CONFERMA HMYQBXYTNP
Check-in mer 10 set
Check-out ven 10 ott
TOTALE (EUR) 5.816,00 €
IMPERIAL SUITE LUXURY PERUGIA PIENO CENTRO STORICO
"""

AIRBNB_CONFIRM_TEMPLATE_TEXT = """
Subject: Prenotazione confermata - Francesco arriverà il 3 set
CODICE DI CONFERMA HMM5AE9MXB
Check-in         Check-out
                =20
gio 3 set 2026   sab 5 set 2026
                =20
16:00            11:00
TOTALE (EUR) 318,00 €
MAGGIORE SUITE - DUOMO DI PERUGIA
"""

AIRBNB_MESSAGE_TEXT = """
Gentile Lorenzo, grazie mille per le informazioni. Abbiamo un'altra domanda.
Tradotto automaticamente. Segue il messaggio originale:
Dear Lorenzo, Thank you so much for the information.
Prenotazione per Imperial Suite Luxury Perugia pieno Centro Storico per 10 settembre 2025 - 10 ottobre 2025
"""


def build_message(subject: str, sender: str, text: str) -> EmailContent:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = "host@example.com"
    message["Date"] = "Fri, 07 Mar 2025 20:27:17 +0000"
    message.set_content(text)
    return EmailContent(message=message, text=text, html=None)


def test_airbnb_confirmation_parser():
    parser = AirbnbConfirmationParser()
    content = build_message(
        "Prenotazione confermata - Edward Cadagin arriverà il 10 set",
        "Airbnb <automated@airbnb.com>",
        AIRBNB_CONFIRM_TEXT,
    )

    assert parser.matches(content)
    parsed = parser.parse(content)

    assert parsed.kind == "airbnb_confirmation"
    assert parsed.reservation is not None
    assert parsed.reservation.reservation_id == "HMYQBXYTNP"
    assert parsed.reservation.total_amount == 5816.00
    assert parsed.reservation.currency == "EUR"


def test_airbnb_confirmation_parser_handles_template_spacing():
    parser = AirbnbConfirmationParser()
    content = build_message(
        "Prenotazione confermata - Francesco arriverà il 3 set",
        "Airbnb <automated@airbnb.com>",
        AIRBNB_CONFIRM_TEMPLATE_TEXT,
    )

    assert parser.matches(content)
    parsed = parser.parse(content)

    assert parsed.reservation is not None
    assert parsed.reservation.reservation_id == "HMM5AE9MXB"
    assert parsed.reservation.check_in is not None
    assert parsed.reservation.check_out is not None
    assert parsed.reservation.total_amount == 318.00

def test_airbnb_message_parser():
    parser = AirbnbMessageParser()
    content = build_message(
        "RE: Prenotazione per Imperial Suite Luxury Perugia pieno Centro Storico",
        "Airbnb <express@airbnb.com>",
        AIRBNB_MESSAGE_TEXT,
    )

    assert parser.matches(content)
    parsed = parser.parse(content)

    assert parsed.kind == "airbnb_message"
    assert parsed.guest_message is not None
    assert "Gentile Lorenzo" in parsed.guest_message.message

