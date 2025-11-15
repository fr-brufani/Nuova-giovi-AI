from __future__ import annotations

import re
from datetime import datetime
from email.header import decode_header
from typing import Optional

from dateutil import parser as date_parser

from ..models import GuestMessageInfo, ParsedEmail, ParsedEmailMetadata
from .base import EmailContent, EmailParser, is_booking_sender


class BookingMessageParser(EmailParser):
    MESSAGE_ID_REGEX = re.compile(r"Numero di conferma\s*[:=]\s*(\d+)", re.IGNORECASE)

    def matches(self, content: EmailContent) -> bool:
        sender = content.message.get("From")
        subject_raw = content.message.get("Subject", "")
        # Decodifica subject se codificato in RFC 2047 (base64 o quoted-printable)
        subject = self._decode_header(subject_raw)
        return is_booking_sender(sender) and "messaggio" in subject.lower()

    def parse(self, content: EmailContent) -> ParsedEmail:
        subject_raw = content.message.get("Subject")
        subject = self._decode_header(subject_raw) if subject_raw else None
        sender = content.message.get("From")
        recipients = content.message.get_all("To")
        received = parse_date_header(content.message.get("Date"))

        text = normalize_text(content.text or content.html or "")
        reservation_id = self._extract_reservation_id(content, text)
        message = extract_message_body(text)
        reply_to = content.message.get("Reply-To") or sender

        guest_message = GuestMessageInfo(
            reservationId=reservation_id or "unknown",
            source="booking",
            message=message or text,
            replyTo=reply_to,
            threadId=extract_thread_id(sender),
        )

        return ParsedEmail(
            kind="booking_message",
            guestMessage=guest_message,
            metadata=ParsedEmailMetadata(
                subject=subject,
                sender=sender,
                recipients=recipients,
                receivedAt=received,
            ),
            rawText=content.text,
            rawHtml=content.html,
        )

    def _extract_reservation_id(self, content: EmailContent, text: str) -> Optional[str]:
        match = self.MESSAGE_ID_REGEX.search(text)
        if match:
            return match.group(1)
        sender = content.message.get("From") or ""
        match = re.search(r"(\d{6,})-", sender)
        if match:
            return match.group(1)
        subject_raw = content.message.get("Subject", "")
        subject = self._decode_header(subject_raw)
        match = re.search(r"(\d{6,})", subject)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def _decode_header(header_value: str) -> str:
        """Decodifica header email codificato in RFC 2047 (base64 o quoted-printable)."""
        if not header_value:
            return ""
        try:
            decoded_parts = decode_header(header_value)
            decoded_string = ""
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    decoded_string += part.decode(encoding or "utf-8", errors="replace")
                else:
                    decoded_string += part
            return decoded_string
        except Exception:
            # Se la decodifica fallisce, ritorna il valore originale
            return header_value


def normalize_text(text: str) -> str:
    text = text.replace("=09", " ").replace("=20", " ")
    text = text.replace("\r\n", "\n")
    return text


def extract_message_body(text: str) -> Optional[str]:
    match = re.search(r"#- .* -#\s*(.*)", text)
    if match:
        return match.group(1).strip()
    return text.strip()


def extract_thread_id(sender: Optional[str]) -> Optional[str]:
    if not sender:
        return None
    match = re.search(r"@([A-Z0-9]+\.[A-Z0-9]+)$", sender, re.IGNORECASE)
    if match:
        return match.group(1).lower()
    return None


def parse_date_header(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return date_parser.parse(value)
    except (ValueError, OverflowError):
        return None

