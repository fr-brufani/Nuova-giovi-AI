from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from ..models import GuestMessageInfo, ParsedEmail, ParsedEmailMetadata
from .base import EmailContent, EmailParser, is_airbnb_sender


class AirbnbMessageParser(EmailParser):
    THREAD_REGEX = re.compile(r"/hosting/thread/(\d+)", re.IGNORECASE)

    def matches(self, content: EmailContent) -> bool:
        sender = content.message.get("From")
        subject = content.message.get("Subject", "")
        subject_lower = subject.lower()
        return is_airbnb_sender(sender) and (
            "messaggio" in subject_lower
            or "prenotazione per" in subject_lower
            or "re:" in subject_lower
        )

    def parse(self, content: EmailContent) -> ParsedEmail:
        subject = content.message.get("Subject")
        sender = content.message.get("From")
        recipients = content.message.get_all("To")
        received = parse_date_header(content.message.get("Date"))

        text = content.text or ""
        html = content.html or ""
        soup = BeautifulSoup(html, "html.parser") if html else None

        reservation_id = extract_reservation_id(text, soup)
        message = extract_message_body(text, soup)
        guest_name = extract_guest_name(text, soup)
        reply_to = content.message.get("Reply-To") or sender

        guest_message = GuestMessageInfo(
            reservationId=reservation_id or "unknown",
            source="airbnb",
            message=message or text.strip(),
            replyTo=reply_to,
            threadId=extract_thread_id(text, soup),
            guestName=guest_name,
        )

        return ParsedEmail(
            kind="airbnb_message",
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


def extract_reservation_id(text: str, soup: Optional[BeautifulSoup]) -> Optional[str]:
    match = re.search(r"Prenotazione.*?([A-Z0-9]{5,})", text)
    if match:
        return match.group(1)
    if soup:
        tag = soup.find(string=re.compile(r"Prenotazione", re.IGNORECASE))
        if tag:
            match = re.search(r"([A-Z0-9]{5,})", tag)
            if match:
                return match.group(1)
    return None


def extract_message_body(text: str, soup: Optional[BeautifulSoup]) -> Optional[str]:
    match = re.search(r"Gentile.+?Grazie\.", text, re.IGNORECASE)
    if match:
        return match.group(0).strip()
    if soup:
        paragraphs = soup.find_all("p")
        body = " ".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
        if body:
            return body
    return None


def extract_guest_name(text: str, soup: Optional[BeautifulSoup]) -> Optional[str]:
    match = re.search(r"Da:\s*([A-Za-z\s]+)", text)
    if match:
        return match.group(1).strip()
    if soup:
        tag = soup.find(string=re.compile(r"Gentile", re.IGNORECASE))
        if tag:
            return tag.split(",")[0].replace("Gentile", "").strip()
    return None


def extract_thread_id(text: str, soup: Optional[BeautifulSoup]) -> Optional[str]:
    if soup:
        for link in soup.find_all("a", href=True):
            match = AirbnbMessageParser.THREAD_REGEX.search(link["href"])
            if match:
                return match.group(1)
    return None


def parse_date_header(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return date_parser.parse(value)
    except (ValueError, OverflowError):
        return None

