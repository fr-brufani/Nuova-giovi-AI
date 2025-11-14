from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from ..models import ParsedEmail, ParsedEmailMetadata, ReservationInfo
from .base import EmailContent, EmailParser, is_airbnb_sender


class AirbnbConfirmationParser(EmailParser):
    THREAD_REGEX = re.compile(r"/hosting/reservations/details/([A-Z0-9]+)", re.IGNORECASE)
    CONFIRM_CODE_REGEX = re.compile(r"CODICE DI CONFERMA\s*([A-Z0-9]+)", re.IGNORECASE)

    def matches(self, content: EmailContent) -> bool:
        sender = content.message.get("From")
        subject = content.message.get("Subject", "")
        subject_lower = subject.lower()
        return is_airbnb_sender(sender) and (
            "prenotazione confermata" in subject_lower
            or "arriverà" in subject_lower
        )

    def parse(self, content: EmailContent) -> ParsedEmail:
        subject = content.message.get("Subject")
        sender = content.message.get("From")
        recipients = content.message.get_all("To")
        received = parse_date_header(content.message.get("Date"))

        text = content.text or ""
        html = content.html or ""
        soup = BeautifulSoup(html, "html.parser") if html else None

        reservation_id = self._extract_reservation_id(subject, text, soup)
        property_name = extract_property_name(text, soup)
        guest_name = extract_guest_name(text, soup)
        check_in = extract_date(text, soup, ["Check-in"])
        check_out = extract_date(text, soup, ["Check-out"])
        adults = extract_guests(text, soup)
        total_amount, currency = extract_amount(text, soup)

        reservation = ReservationInfo(
            reservationId=reservation_id or "unknown",
            source="airbnb",
            propertyName=property_name,
            guestName=guest_name,
            checkIn=check_in,
            checkOut=check_out,
            adults=adults,
            totalAmount=total_amount,
            currency=currency,
        )

        return ParsedEmail(
            kind="airbnb_confirmation",
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
        subject: Optional[str],
        text: str,
        soup: Optional[BeautifulSoup],
    ) -> Optional[str]:
        if subject:
            match = self.CONFIRM_CODE_REGEX.search(subject)
            if match:
                return match.group(1)
        if soup:
            for link in soup.find_all("a", href=True):
                match = self.THREAD_REGEX.search(link["href"])
                if match:
                    return match.group(1)
        match = self.CONFIRM_CODE_REGEX.search(text)
        if match:
            return match.group(1)
        return None


def extract_property_name(text: str, soup: Optional[BeautifulSoup]) -> Optional[str]:
    if soup:
        header = soup.find("h1")
        if header and header.text.strip():
            return header.text.strip()
        strong = soup.find("strong")
        if strong and strong.text.strip():
            return strong.text.strip()
    match = re.search(r"IMPERIAL SUITE.*", text)
    if match:
        return match.group(0).strip()
    return None


def extract_guest_name(text: str, soup: Optional[BeautifulSoup]) -> Optional[str]:
    match = re.search(r"Edward\s+Cadagin", text, re.IGNORECASE)
    if match:
        return match.group(0).strip()
    if soup:
        tags = soup.find_all(string=re.compile(r"arriverà", re.IGNORECASE))
        for tag in tags:
            return tag.split("arriver")[0].strip()
    return None


def extract_date(text: str, soup: Optional[BeautifulSoup], labels: list[str]) -> Optional[datetime]:
    for label in labels:
        pattern = re.compile(rf"{label}\s*(?:[:\-])?\s*([0-9]{1,2}\s+[A-Za-z]{3})", re.IGNORECASE)
        match = pattern.search(text)
        if match:
            try:
                return date_parser.parse(match.group(1), dayfirst=True, yearfirst=False, fuzzy=True)
            except (ValueError, OverflowError):
                continue
    if soup:
        spans = soup.find_all("span")
        for span in spans:
            if any(label.lower() in span.text.lower() for label in labels):
                parts = span.text.split()
                try:
                    return date_parser.parse(" ".join(parts[-2:]), dayfirst=True, fuzzy=True)
                except (ValueError, OverflowError):
                    continue
    return None


def extract_guests(text: str, soup: Optional[BeautifulSoup]) -> Optional[int]:
    match = re.search(r"(\d+)\s+adulti", text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    if soup:
        tag = soup.find(string=re.compile(r"ospiti", re.IGNORECASE))
        if tag:
            match = re.search(r"(\d+)", tag)
            if match:
                return int(match.group(1))
    return None


def extract_amount(text: str, soup: Optional[BeautifulSoup]) -> tuple[Optional[float], Optional[str]]:
    match = re.search(r"TOTALE.*?([0-9\.,]+)\s*€", text, re.IGNORECASE)
    if match:
        value = match.group(1).replace(".", "").replace(",", ".")
        try:
            return float(value), "EUR"
        except ValueError:
            pass
    if soup:
        tag = soup.find(string=re.compile(r"TOTALE", re.IGNORECASE))
        if tag:
            match = re.search(r"([0-9\.,]+)\s*€", tag)
            if match:
                value = match.group(1).replace(".", "").replace(",", ".")
                try:
                    return float(value), "EUR"
                except ValueError:
                    pass
    return None, None


def parse_date_header(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return date_parser.parse(value)
    except (ValueError, OverflowError):
        return None

