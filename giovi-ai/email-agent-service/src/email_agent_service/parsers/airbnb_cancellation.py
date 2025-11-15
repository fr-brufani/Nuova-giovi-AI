from __future__ import annotations

import re
from typing import Optional

from bs4 import BeautifulSoup

from ..models import ParsedEmail, ParsedEmailMetadata, ReservationInfo
from .base import EmailContent, EmailParser, is_airbnb_sender


class AirbnbCancellationParser(EmailParser):
    """Parser per email di cancellazione Airbnb dirette da automated@airbnb.com."""
    
    THREAD_ID_REGEX = re.compile(r"/hosting/thread/(\d+)", re.IGNORECASE)
    CONFIRM_CODE_REGEX = re.compile(r"CODICE DI CONFERMA\s*([A-Z0-9]+)", re.IGNORECASE)

    def matches(self, content: EmailContent) -> bool:
        sender = content.message.get("From")
        subject = content.message.get("Subject", "")
        subject_lower = subject.lower()
        return is_airbnb_sender(sender) and "cancellazione effettuata" in subject_lower

    def parse(self, content: EmailContent) -> ParsedEmail:
        subject = content.message.get("Subject")
        sender = content.message.get("From")
        recipients = content.message.get_all("To")
        received = parse_date_header(content.message.get("Date"))

        text = content.text or ""
        html = content.html or ""
        soup = BeautifulSoup(html, "html.parser") if html else None

        # Estrai reservation ID (codice di conferma) e thread ID
        reservation_id = self._extract_reservation_id(text, soup)
        thread_id = self._extract_thread_id(text, soup)

        reservation = ReservationInfo(
            reservationId=reservation_id or "unknown",
            source="airbnb",
            voucherId=reservation_id,  # Per Airbnb, voucherId = reservationId
            threadId=thread_id,
            sourceChannel="airbnb",
        )

        return ParsedEmail(
            kind="airbnb_cancellation",
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

    def _extract_reservation_id(
        self,
        text: str,
        soup: Optional[BeautifulSoup],
    ) -> Optional[str]:
        """Estrae il codice di conferma dall'email di cancellazione."""
        # Cerca "CODICE DI CONFERMA" nel testo
        match = self.CONFIRM_CODE_REGEX.search(text)
        if match:
            return match.group(1)
        
        # Cerca nell'HTML
        if soup:
            tag = soup.find(string=re.compile(r"CODICE DI CONFERMA", re.IGNORECASE))
            if tag:
                # Cerca pattern alfanumerico dopo "CODICE DI CONFERMA"
                match = re.search(r"([A-Z0-9]{5,})", tag)
                if match:
                    return match.group(1)
        
        return None

    def _extract_thread_id(
        self,
        text: str,
        soup: Optional[BeautifulSoup],
    ) -> Optional[str]:
        """Estrae il thread ID dal link /hosting/thread/..."""
        if soup:
            for link in soup.find_all("a", href=True):
                match = self.THREAD_ID_REGEX.search(link["href"])
                if match:
                    return match.group(1)
        # Fallback: cerca nel testo
        match = self.THREAD_ID_REGEX.search(text)
        if match:
            return match.group(1)
        return None


def parse_date_header(value: Optional[str]) -> Optional[datetime]:
    from datetime import datetime
    from dateutil import parser as date_parser
    
    if not value:
        return None
    try:
        return date_parser.parse(value)
    except (ValueError, OverflowError):
        return None

