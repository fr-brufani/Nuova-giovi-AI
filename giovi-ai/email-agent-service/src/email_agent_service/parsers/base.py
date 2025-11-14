from __future__ import annotations

import re
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import parseaddr
from typing import Optional

from ..models import ParsedEmail


@dataclass
class EmailContent:
    message: EmailMessage
    text: Optional[str]
    html: Optional[str]


class EmailParser:
    def matches(self, content: EmailContent) -> bool:  # pragma: no cover - interface
        raise NotImplementedError

    def parse(self, content: EmailContent) -> ParsedEmail:  # pragma: no cover - interface
        raise NotImplementedError

    @staticmethod
    def _clean_text(text: Optional[str]) -> Optional[str]:
        if text is None:
            return None
        return re.sub(r"\s+", " ", text).strip()


def is_booking_sender(address: Optional[str]) -> bool:
    if not address:
        return False
    _, email_address = parseaddr(address)
    address = email_address or address
    return any(
        domain in address.lower()
        for domain in [
            "@mchat.booking.com",
            "@guest.booking.com",  # Nuovo formato email Booking
            "@reply.booking.com",
            "@scidoo.com",
        ]
    )


def is_airbnb_sender(address: Optional[str]) -> bool:
    if not address:
        return False
    _, email_address = parseaddr(address)
    address = email_address or address
    return any(
        address.lower().endswith(domain)
        for domain in [
            "@airbnb.com",
            "@reply.airbnb.com",
        ]
    )

