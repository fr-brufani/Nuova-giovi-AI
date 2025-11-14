from __future__ import annotations

import logging
import base64
from email import message_from_bytes
from email.message import EmailMessage
from typing import Iterable, List, Optional

from ..models import ParsedEmail, ParsedEmailMetadata
from .base import EmailContent, EmailParser

logger = logging.getLogger(__name__)


class EmailParsingEngine:
    def __init__(self, parsers: Iterable[EmailParser]):
        self._parsers: List[EmailParser] = list(parsers)

    def parse(
        self,
        *,
        message_id: str,
        raw_payload: bytes,
        snippet: Optional[str] = None,
    ) -> ParsedEmail:
        email_message = message_from_bytes(raw_payload)
        text = extract_part(email_message, preferred_type="text/plain")
        html = extract_part(email_message, preferred_type="text/html")

        content = EmailContent(message=email_message, text=text, html=html)
        
        subject = email_message.get("Subject", "")
        sender = email_message.get("From", "")
        logger.debug(f"[PARSER_ENGINE] Tentativo parsing email: sender={sender[:50]}, subject={subject[:50]}")

        for parser in self._parsers:
            if parser.matches(content):
                parser_name = parser.__class__.__name__
                logger.info(f"[PARSER_ENGINE] ✅ Parser matchato: {parser_name} per email subject={subject[:50]}")
                parsed = parser.parse(content)
                parsed.metadata.gmail_message_id = message_id
                if snippet:
                    parsed.metadata.snippet = snippet
                return parsed
        
        logger.warning(f"[PARSER_ENGINE] ⚠️ Nessun parser matchato per email: sender={sender[:50]}, subject={subject[:50]}")

        return ParsedEmail(
            kind="unhandled",
            metadata=ParsedEmailMetadata(
                subject=email_message.get("Subject"),
                sender=email_message.get("From"),
                recipients=email_message.get_all("To"),
                snippet=snippet,
                gmailMessageId=message_id,
            ),
            rawText=text,
            rawHtml=html,
        )


def extract_part(message: EmailMessage, preferred_type: str) -> Optional[str]:
    if message.get_content_maintype() == "multipart":
        for part in message.walk():
            if part.get_content_type() == preferred_type:
                payload = part.get_payload(decode=True)
                if isinstance(payload, bytes):
                    charset = part.get_content_charset() or "utf-8"
                    try:
                        return payload.decode(charset, errors="replace")
                    except LookupError:  # pragma: no cover - rare encoding
                        return payload.decode("utf-8", errors="replace")
    else:
        if message.get_content_type() == preferred_type:
            payload = message.get_payload(decode=True)
            if isinstance(payload, bytes):
                charset = message.get_content_charset() or "utf-8"
                try:
                    return payload.decode(charset, errors="replace")
                except LookupError:  # pragma: no cover
                    return payload.decode("utf-8", errors="replace")
    return None


def decode_gmail_raw(raw_string: str) -> bytes:
    return base64.urlsafe_b64decode(raw_string.encode("utf-8"))

