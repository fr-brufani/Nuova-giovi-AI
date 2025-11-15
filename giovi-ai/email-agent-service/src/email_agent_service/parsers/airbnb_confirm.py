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
    THREAD_ID_REGEX = re.compile(r"/hosting/thread/(\d+)", re.IGNORECASE)
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
        thread_id = self._extract_thread_id(text, soup)
        property_name = extract_property_name(text, soup)
        guest_name = extract_guest_name(text, soup)
        check_in = extract_date(text, soup, ["Check-in"])
        check_out = extract_date(text, soup, ["Check-out"])
        adults = extract_guests(text, soup)
        total_amount, currency = extract_amount(text, soup)

        reservation = ReservationInfo(
            reservationId=reservation_id or "unknown",
            source="airbnb",
            voucherId=reservation_id,  # Per Airbnb, voucherId = reservationId (codice di conferma)
            threadId=thread_id,
            propertyName=property_name,
            guestName=guest_name,
            checkIn=check_in,
            checkOut=check_out,
            adults=adults,
            totalAmount=total_amount,
            currency=currency,
            sourceChannel="airbnb",  # Sempre "airbnb" per email dirette da automated@airbnb.com
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


def extract_property_name(text: str, soup: Optional[BeautifulSoup]) -> Optional[str]:
    """Estrae il nome della property dall'email Airbnb."""
    if soup:
        # Cerca header h1 o h2
        header = soup.find("h1") or soup.find("h2")
        if header and header.text.strip():
            return header.text.strip()
        # Cerca strong tag
        strong = soup.find("strong")
        if strong and strong.text.strip():
            return strong.text.strip()
        # Cerca pattern "MAGGIORE SUITE - DUOMO DI PERUGIA" o simile
        for tag in soup.find_all(string=True):
            if "SUITE" in tag or "CASA" in tag or "APPARTAMENTO" in tag:
                # Prendi la riga completa se contiene il nome property
                text_line = tag.strip()
                if len(text_line) > 10:  # Evita snippet troppo corti
                    return text_line
    
    # Fallback: cerca nel testo plain
    match = re.search(r"([A-Z][A-Z\s\-]+(?:SUITE|CASA|APPARTAMENTO|ROOM)[A-Z\s\-]*)", text)
    if match:
        return match.group(1).strip()
    return None


def extract_guest_name(text: str, soup: Optional[BeautifulSoup]) -> Optional[str]:
    """Estrae il nome dell'ospite dall'email Airbnb."""
    # Cerca pattern "FRANCESCO" o "Francesco Brufani" prima di "arriverà"
    match = re.search(r"([A-Z][A-Za-z\s]+?)\s+arriverà", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # Cerca nel subject: "Prenotazione confermata - Francesco Brufani arriverà..."
    match = re.search(r"confermata\s*-\s*([A-Z][A-Za-z\s]+?)\s+arriver", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    if soup:
        # Cerca tag che contengono "arriverà"
        tags = soup.find_all(string=re.compile(r"arriverà", re.IGNORECASE))
        for tag in tags:
            # Estrai il nome prima di "arriverà"
            parts = tag.split("arriver")
            if parts and parts[0].strip():
                name = parts[0].strip()
                # Rimuovi "Prenotazione confermata - " se presente
                name = re.sub(r"^.*?confermata\s*-\s*", "", name, flags=re.IGNORECASE).strip()
                if name:
                    return name
    return None


def extract_date(text: str, soup: Optional[BeautifulSoup], labels: list[str]) -> Optional[datetime]:
    """Estrae una data dall'email Airbnb (check-in o check-out)."""
    # Pattern per "gio 3 set 2026" o "3 settembre 2026"
    for label in labels:
        # Pattern 1: "Check-in gio 3 set 2026"
        pattern1 = re.compile(rf"{label}.*?([a-z]{{2,3}}\s+\d{{1,2}}\s+[a-z]{{3}}\s+\d{{4}})", re.IGNORECASE)
        match = pattern1.search(text)
        if match:
            try:
                return date_parser.parse(match.group(1), dayfirst=True, fuzzy=True)
            except (ValueError, OverflowError):
                pass
        
        # Pattern 2: "Check-in 3 settembre 2026"
        pattern2 = re.compile(rf"{label}.*?(\d{{1,2}}\s+[a-z]+\s+\d{{4}})", re.IGNORECASE)
        match = pattern2.search(text)
        if match:
            try:
                return date_parser.parse(match.group(1), dayfirst=True, fuzzy=True)
            except (ValueError, OverflowError):
                pass
    
    if soup:
        # Cerca nelle celle della tabella o span
        for tag in soup.find_all(["td", "span", "div"]):
            text_content = tag.get_text()
            if any(label.lower() in text_content.lower() for label in labels):
                # Cerca data nel testo
                match = re.search(r"([a-z]{{2,3}}\s+\d{{1,2}}\s+[a-z]{{3}}\s+\d{{4}}|\d{{1,2}}\s+[a-z]+\s+\d{{4}})", text_content, re.IGNORECASE)
                if match:
                    try:
                        return date_parser.parse(match.group(1), dayfirst=True, fuzzy=True)
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
    """Estrae l'importo totale dall'email Airbnb."""
    # Pattern per "TOTALE (EUR) 318,00 €" o "TOTALE 318,00 €"
    match = re.search(r"TOTALE.*?\(?EUR\)?\s*([0-9\.,]+)\s*€", text, re.IGNORECASE)
    if match:
        value = match.group(1).replace(".", "").replace(",", ".")
        try:
            return float(value), "EUR"
        except ValueError:
            pass
    
    # Pattern alternativo senza EUR
    match = re.search(r"TOTALE.*?([0-9\.,]+)\s*€", text, re.IGNORECASE)
    if match:
        value = match.group(1).replace(".", "").replace(",", ".")
        try:
            return float(value), "EUR"
        except ValueError:
            pass
    
    if soup:
        # Cerca nel testo HTML
        tag = soup.find(string=re.compile(r"TOTALE", re.IGNORECASE))
        if tag:
            match = re.search(r"\(?EUR\)?\s*([0-9\.,]+)\s*€", tag, re.IGNORECASE)
            if not match:
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

