from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from ..models import ParsedEmail, ParsedEmailMetadata, ReservationInfo
from .base import EmailContent, EmailParser

logger = logging.getLogger(__name__)


class ScidooConfirmationParser(EmailParser):
    """Parser per email di conferma prenotazione Scidoo.
    
    Matcha email da reservation@scidoo.com con oggetto che inizia con "Confermata - Prenotazione"
    """

    def matches(self, content: EmailContent) -> bool:
        sender = content.message.get("From", "")
        subject = content.message.get("Subject", "")
        matches_sender = "reservation@scidoo.com" in sender.lower()
        matches_subject = subject.startswith("Confermata - Prenotazione")
        
        if matches_sender:
            logger.debug(f"[SCIDOO_PARSER] Email da reservation@scidoo.com: subject={subject[:50]}..., matches_subject={matches_subject}")
        
        return matches_sender and matches_subject

    def parse(self, content: EmailContent) -> ParsedEmail:
        subject = content.message.get("Subject")
        sender = content.message.get("From")
        recipients = content.message.get_all("To")
        received = parse_date_header(content.message.get("Date"))

        text = normalize_text(content.text or "")
        html = content.html or ""
        soup = BeautifulSoup(html, "html.parser") if html else None

        # Estrai dati dalla email
        reservation_id = extract_reservation_id(text, soup, subject=subject)
        voucher_id = reservation_id  # Per Scidoo, l'ID Voucher è lo stesso del reservation_id
        source_channel = extract_source_channel(subject)  # Estrai Booking o Airbnb dal subject
        property_name = extract_property_name(text, soup)
        guest_name = extract_guest_name(text, soup)
        guest_email = extract_guest_email(text, soup)
        guest_phone = extract_guest_phone(text, soup)
        check_in = extract_check_in_date(text, soup)
        check_out = extract_check_out_date(text, soup)
        adults = extract_adults(text, soup)
        total_amount, currency = extract_total_amount(text, soup)

        reservation = ReservationInfo(
            reservationId=reservation_id or "unknown",
            voucherId=voucher_id,  # ID Voucher estratto dalla email
            source="scidoo",
            sourceChannel=source_channel,  # "booking" o "airbnb" dal subject
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
            kind="scidoo_confirmation",
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
    """Normalizza il testo rimuovendo caratteri speciali quoted-printable."""
    text = text.replace("=09", " ").replace("=20", " ")
    text = text.replace("\r\n", "\n")
    text = text.replace("=E2=82=AC", "€")  # Euro symbol
    return text


def extract_reservation_id(text: str, soup: Optional[BeautifulSoup], subject: Optional[str] = None) -> Optional[str]:
    """Estrae ID Voucher / ID Prenotazione.
    
    Supporta sia ID numerici (Booking) che alfanumerici (Airbnb).
    Esempi:
    - Booking: "ID Voucher=095150895143" -> "5150895143"
    - Airbnb: "ID Voucher=09HMMFYTC5TJ" -> "HMMFYTC5TJ"
    """
    # Pattern: "ID Voucher=09..." seguito da alfanumerici (lettere e numeri)
    # Supporta sia numerici che alfanumerici (es: HMMFYTC5TJ, 5150895143)
    match = re.search(r"ID\s+Voucher\s*=\s*0*([A-Z0-9]+)", text, re.IGNORECASE)
    if match:
        return match.group(1)
    
    if soup:
        # Cerca nella tabella HTML
        for row in soup.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if th and td and "ID Voucher" in th.get_text():
                voucher_text = td.get_text().strip()
                # Supporta alfanumerici (lettere e numeri)
                match = re.search(r"([A-Z0-9]+)", voucher_text, re.IGNORECASE)
                if match:
                    return match.group(1)
    
    # Fallback: estrai dal subject se disponibile
    # Subject: "Confermata - Prenotazione ID HMMFYTC5TJ - Airbnb"
    if subject:
        match = re.search(r"Confermata\s+-\s+Prenotazione\s+ID\s+([A-Z0-9]+)", subject, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None


def extract_source_channel(subject: Optional[str]) -> Optional[str]:
    """Estrae il canale (Booking o Airbnb) dal subject.
    
    Subject Booking: "Confermata - Prenotazione ID 5150895143 - Booking"
    Subject Airbnb: "Confermata - Prenotazione ID HMMFYTC5TJ - Airbnb"
    
    Returns:
        "booking", "airbnb", o None se non trovato
    """
    if not subject:
        return None
    
    subject_lower = subject.lower()
    if " - booking" in subject_lower:
        return "booking"
    elif " - airbnb" in subject_lower:
        return "airbnb"
    
    return None


def extract_property_name(text: str, soup: Optional[BeautifulSoup]) -> Optional[str]:
    """Estrae 'Camera/Alloggio' (nome property).
    
    NOTA: Usa "Camera/Alloggio" come nome property, non "Struttura Richiesta".
    Esempio: "1 Suite Scacco" -> "1 Suite Scacco"
    """
    # Pattern: "Camera/Alloggio=091 Suite Scacco"
    match = re.search(r"Camera/Alloggio\s*=\s*0*([^\n\r]+)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    if soup:
        # Cerca nella tabella HTML per "Camera/Alloggio"
        for row in soup.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if th and td and "Camera/Alloggio" in th.get_text():
                return td.get_text().strip()
    
    return None


def extract_guest_name(text: str, soup: Optional[BeautifulSoup]) -> Optional[str]:
    """Estrae nome ospite."""
    match = re.search(r"Nome\s+Ospite\s*=\s*0*([^\n\r]+)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    if soup:
        for row in soup.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if th and td and "Nome Ospite" in th.get_text():
                return td.get_text().strip()
    
    return None


def extract_guest_email(text: str, soup: Optional[BeautifulSoup]) -> Optional[str]:
    """Estrae email ospite."""
    # Pattern: "Email:ttorte.471243@guest.booking.com"
    match = re.search(r"Email\s*:\s*([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})", text, re.IGNORECASE)
    if match:
        return match.group(1).lower()
    
    if soup:
        # Cerca "Dati Ospite" section
        for tag in soup.find_all(string=re.compile(r"Email:", re.IGNORECASE)):
            parent = tag.parent
            if parent:
                email_text = parent.get_text()
                match = re.search(r"Email\s*:\s*([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})", email_text, re.IGNORECASE)
                if match:
                    return match.group(1).lower()
    
    return None


def extract_guest_phone(text: str, soup: Optional[BeautifulSoup]) -> Optional[str]:
    """Estrae telefono/cellulare ospite."""
    # Pattern: "Cellulare:+393392452297"
    match = re.search(r"Cellulare\s*:\s*(\+?\d[\d\s\-]{6,})", text, re.IGNORECASE)
    if match:
        phone = match.group(1)
        return re.sub(r"[^\d+]", "", phone)
    
    # Fallback su "Telefono:"
    match = re.search(r"Telefono\s*:\s*(\+?\d[\d\s\-]{6,})", text, re.IGNORECASE)
    if match:
        phone = match.group(1)
        return re.sub(r"[^\d+]", "", phone)
    
    return None


def extract_check_in_date(text: str, soup: Optional[BeautifulSoup]) -> Optional[datetime]:
    """Estrae data check-in."""
    match = re.search(r"Data\s+di\s+Check-in\s*=\s*0*(\d{1,2}/\d{1,2}/\d{2,4})", text, re.IGNORECASE)
    if match:
        try:
            return date_parser.parse(match.group(1), dayfirst=True)
        except (ValueError, OverflowError):
            pass
    
    if soup:
        for row in soup.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if th and td and "Data di Check-in" in th.get_text():
                date_str = td.get_text().strip()
                try:
                    return date_parser.parse(date_str, dayfirst=True)
                except (ValueError, OverflowError):
                    pass
    
    return None


def extract_check_out_date(text: str, soup: Optional[BeautifulSoup]) -> Optional[datetime]:
    """Estrae data check-out."""
    match = re.search(r"Data\s+di\s+Check-out\s*=\s*0*(\d{1,2}/\d{1,2}/\d{2,4})", text, re.IGNORECASE)
    if match:
        try:
            return date_parser.parse(match.group(1), dayfirst=True)
        except (ValueError, OverflowError):
            pass
    
    if soup:
        for row in soup.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if th and td and "Data di Check-out" in th.get_text():
                date_str = td.get_text().strip()
                try:
                    return date_parser.parse(date_str, dayfirst=True)
                except (ValueError, OverflowError):
                    pass
    
    return None


def extract_adults(text: str, soup: Optional[BeautifulSoup]) -> Optional[int]:
    """Estrae numero adulti."""
    match = re.search(r"Ospiti\s*=\s*0*(\d+)\s+Adulti", text, re.IGNORECASE)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass
    
    if soup:
        for row in soup.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if th and td and "Ospiti" in th.get_text():
                guests_text = td.get_text()
                match = re.search(r"(\d+)\s+Adulti", guests_text, re.IGNORECASE)
                if match:
                    try:
                        return int(match.group(1))
                    except ValueError:
                        pass
    
    return None


def extract_total_amount(text: str, soup: Optional[BeautifulSoup]) -> tuple[Optional[float], Optional[str]]:
    """Estrae totale prenotazione e valuta."""
    # Pattern: "Totale Prenotazione: 979,76 €" o "Prezzo=09979,76"
    match = re.search(r"Totale\s+Prenotazione\s*:\s*([0-9\.,]+)\s*€?", text, re.IGNORECASE)
    if match:
        amount_str = match.group(1).replace(".", "").replace(",", ".")
        try:
            return float(amount_str), "EUR"
        except ValueError:
            pass
    
    # Fallback su "Prezzo="
    match = re.search(r"Prezzo\s*=\s*0*([0-9\.,]+)", text, re.IGNORECASE)
    if match:
        amount_str = match.group(1).replace(".", "").replace(",", ".")
        try:
            return float(amount_str), "EUR"
        except ValueError:
            pass
    
    if soup:
        # Cerca nella tabella o nel testo
        for tag in soup.find_all(string=re.compile(r"Totale Prenotazione", re.IGNORECASE)):
            parent = tag.parent
            if parent:
                total_text = parent.get_text()
                match = re.search(r"([0-9\.,]+)\s*€?", total_text)
                if match:
                    amount_str = match.group(1).replace(".", "").replace(",", ".")
                    try:
                        return float(amount_str), "EUR"
                    except ValueError:
                        pass
    
    return None, None


def parse_date_header(value: Optional[str]) -> Optional[datetime]:
    """Parsa header Date email."""
    if not value:
        return None
    try:
        return date_parser.parse(value)
    except (ValueError, OverflowError):
        return None

