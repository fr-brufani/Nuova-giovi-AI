from __future__ import annotations

import logging
import re
from typing import Optional

from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from ..models import ParsedEmail, ParsedEmailMetadata, ReservationInfo
from .base import EmailContent, EmailParser
from .scidoo_confirm import (
    extract_reservation_id,
    normalize_text,
    parse_date_header,
)

logger = logging.getLogger(__name__)


class ScidooCancellationParser(EmailParser):
    """Parser per email di cancellazione prenotazione Scidoo.
    
    Matcha email da reservation@scidoo.com con oggetto che inizia con "Cancellata - Prenotazione"
    """

    def matches(self, content: EmailContent) -> bool:
        sender = content.message.get("From", "")
        subject = content.message.get("Subject", "")
        matches_sender = "reservation@scidoo.com" in sender.lower()
        matches_subject = subject.startswith("Cancellata - Prenotazione")
        
        if matches_sender:
            logger.debug(f"[SCIDOO_CANCELLATION_PARSER] Email da reservation@scidoo.com: subject={subject[:50]}..., matches_subject={matches_subject}")
        
        return matches_sender and matches_subject

    def parse(self, content: EmailContent) -> ParsedEmail:
        subject = content.message.get("Subject")
        sender = content.message.get("From")
        recipients = content.message.get_all("To")
        received = parse_date_header(content.message.get("Date"))

        text = normalize_text(content.text or "")
        html = content.html or ""
        soup = BeautifulSoup(html, "html.parser") if html else None

        # Estrai ID Voucher dalla email (stesso metodo della conferma)
        reservation_id = extract_reservation_id(text, soup, subject=subject)
        voucher_id = reservation_id  # Per Scidoo, l'ID Voucher è lo stesso del reservation_id

        # Per le cancellazioni, creiamo un ReservationInfo minimale con solo voucherId
        reservation = ReservationInfo(
            reservationId=reservation_id or "unknown",
            voucherId=voucher_id,
            source="scidoo",
        )

        return ParsedEmail(
            kind="scidoo_cancellation",
            reservation=reservation,
            metadata=ParsedEmailMetadata(
                subject=subject,
                sender=sender,
                recipients=recipients,
                receivedAt=received,
            ),
            rawText=content.text,
            rawHtml=content.html,
        )

