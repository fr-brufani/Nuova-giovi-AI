from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from dateutil import parser as date_parser

from ..models import ParsedEmail, ParsedEmailMetadata, ReservationInfo
from .base import EmailContent, EmailParser, is_booking_sender

BOOKING_CONFIRM_SUBJECT_RE = re.compile(r"prenotazione id\s*(\d+)", re.IGNORECASE)
BOOKING_ID_BODY_RE = re.compile(r"(?:ID\s+Voucher|Numero di conferma)\s*[:=]\s*(\d+)", re.IGNORECASE)


class BookingConfirmationParser(EmailParser):
    def matches(self, content: EmailContent) -> bool:
        sender = content.message.get("From")
        subject = content.message.get("Subject", "")
        return is_booking_sender(sender) and bool(BOOKING_CONFIRM_SUBJECT_RE.search(subject))

    def parse(self, content: EmailContent) -> ParsedEmail:
        subject = content.message.get("Subject")
        sender = content.message.get("From")
        recipients = content.message.get_all("To")
        received = parse_date_header(content.message.get("Date"))

        text = normalize_text(content.text or content.html or "")
        reservation_id = extract_reservation_id(subject, text)
        property_name = extract_field(text, ["Struttura Richiesta", "Nome struttura"])
        guest_name = extract_field(text, ["Nome Ospite", "Ospite"])
        guest_email = extract_email(text)
        guest_phone = extract_phone(text)
        check_in = extract_date(text, ["Data di Check-in", "Check-in"])
        check_out = extract_date(text, ["Data di Check-out", "Check-out"])
        adults = extract_int(text, ["Ospiti", "Adulti"])
        total_amount, currency = extract_amount(text, ["Totale Prenotazione", "Totale (EUR)", "TU GUADAGNI"])

        reservation = ReservationInfo(
            reservationId=reservation_id or "unknown",
            source="booking",
            propertyName=property_name,
            guestName=guest_name,
            guestEmail=guest_email,
            guestPhone=guest_phone,
            checkIn=check_in,
            checkOut=check_out,
            adults=adults,
            totalAmount=total_amount,
            currency=currency,
        )

        return ParsedEmail(
            kind="booking_confirmation",
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


def normalize_text(text: str) -> str:
    text = text.replace("=09", " ").replace("=20", " ")
    text = text.replace("\r\n", "\n")
    return text


def extract_reservation_id(subject: Optional[str], text: str) -> Optional[str]:
    if subject:
        match = BOOKING_CONFIRM_SUBJECT_RE.search(subject)
        if match:
            return match.group(1)
    match = BOOKING_ID_BODY_RE.search(text)
    if match:
        return match.group(1)
    return None


def extract_field(text: str, labels: list[str]) -> Optional[str]:
    for label in labels:
        pattern = re.compile(rf"{re.escape(label)}\s*[:=]\s*([^\n\r]+)", re.IGNORECASE)
        match = pattern.search(text)
        if match:
            value = match.group(1).strip()
            if value:
                return value.split("\n")[0].strip()
    return None


def extract_email(text: str) -> Optional[str]:
    match = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, re.IGNORECASE)
    if match:
        return match.group(0).lower()
    return None


def extract_phone(text: str) -> Optional[str]:
    match = re.search(r"\+?\d[\d\s\-]{6,}", text)
    if match:
        return re.sub(r"[^\d+]", "", match.group(0))
    return None


def extract_date(text: str, labels: list[str]) -> Optional[datetime]:
    for label in labels:
        pattern = re.compile(rf"{re.escape(label)}\s*[:=]\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})", re.IGNORECASE)
        match = pattern.search(text)
        if match:
            try:
                return date_parser.parse(match.group(1), dayfirst=True)
            except (ValueError, OverflowError):
                continue
    return None


def extract_int(text: str, labels: list[str]) -> Optional[int]:
    for label in labels:
        pattern = re.compile(rf"{re.escape(label)}\s*[:=]\s*([0-9]+)", re.IGNORECASE)
        match = pattern.search(text)
        if match:
            try:
                return int(match.group(1))
            except ValueError:  # pragma: no cover - defensive
                continue
    return None


def extract_amount(text: str, labels: list[str]) -> tuple[Optional[float], Optional[str]]:
    for label in labels:
        pattern = re.compile(rf"{re.escape(label)}\s*[:=]\s*([0-9\.,]+)\s*([A-Z€]*)", re.IGNORECASE)
        match = pattern.search(text)
        if match:
            raw_amount = match.group(1).replace(".", "").replace(",", ".")
            currency = match.group(2) or "EUR"
            try:
                return float(raw_amount), currency.replace("€", "EUR")
            except ValueError:
                continue
    return None, None


def parse_date_header(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return date_parser.parse(value)
    except (ValueError, OverflowError):
        return None

