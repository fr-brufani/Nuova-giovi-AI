from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from ..models import ParsedEmail, ParsedEmailMetadata, ReservationInfo, GuestMessageInfo
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

        text = normalize_airbnb_text(content.text or "")
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
        
        # Estrai anche messaggio del guest se presente
        guest_message = extract_guest_message_from_confirmation(text, soup, guest_name)

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
        
        # Crea GuestMessageInfo se c'è un messaggio
        guest_message_info = None
        if guest_message:
            reply_to = content.message.get("Reply-To") or sender
            guest_message_info = GuestMessageInfo(
                reservationId=reservation_id or "unknown",
                source="airbnb",
                message=guest_message,
                replyTo=reply_to,
                threadId=thread_id,
                guestName=guest_name,
            )

        return ParsedEmail(
            kind="airbnb_confirmation",
            reservation=reservation,
            guestMessage=guest_message_info,
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
    # Pattern per escludere frasi che contengono "arriverà", "confermata", "nuova prenotazione"
    exclude_patterns = [
        r"arriverà",
        r"confermata",
        r"nuova prenotazione",
        r"prenotazione confermata",
        r"ciao\s+\w+",  # Esclude messaggi che iniziano con "Ciao"
        r"tradotto automaticamente",  # Esclude sezioni di traduzione
        r"hallo\s+\w+",  # Esclude messaggi in tedesco
        r"^siamo\s+",  # Esclude messaggi che iniziano con "Siamo"
        r"^desideriamo\s+",  # Esclude messaggi che iniziano con "Desideriamo"
        r"^viaggiamo\s+",  # Esclude messaggi che iniziano con "Viaggiamo"
        r"^non\s+vediamo\s+l'ora",  # Esclude "Non vediamo l'ora"
        r"mi\s+sposo",  # Esclude messaggi tipo "Mi sposo la prossima settimana"
        r"viaggio\s+di\s+nozze",  # Esclude "viaggio di nozze"
        r"casa\s+è\s+bellissima",  # Esclude "casa è bellissima"
    ]
    
    def should_exclude(text_line: str) -> bool:
        """Verifica se una riga di testo dovrebbe essere esclusa."""
        text_lower = text_line.lower()
        # Escludi testi molto lunghi (>100 caratteri) che non contengono SUITE/CASA/APPARTAMENTO
        if len(text_line) > 100 and not re.search(r"(?:SUITE|CASA|APPARTAMENTO|ROOM)", text_line, re.IGNORECASE):
            return True
        # Escludi testi che contengono più di 3 parole e non contengono SUITE/CASA/APPARTAMENTO
        words = text_line.split()
        if len(words) > 3 and not re.search(r"(?:SUITE|CASA|APPARTAMENTO|ROOM)", text_line, re.IGNORECASE):
            return True
        return any(re.search(pattern, text_lower, re.IGNORECASE) for pattern in exclude_patterns)
    
    if soup:
        # Cerca header h1 o h2 (ma escludi quelli con "arriverà" o "confermata")
        header = soup.find("h1") or soup.find("h2")
        if header:
            header_text = header.text.strip()
            if header_text and not should_exclude(header_text):
                return header_text
        
        # Cerca strong tag (ma escludi quelli con "arriverà" o "confermata")
        strong = soup.find("strong")
        if strong:
            strong_text = strong.text.strip()
            if strong_text and not should_exclude(strong_text):
                return strong_text
        
        # Cerca pattern specifico: testo tutto maiuscolo con "SUITE/CASA/APPARTAMENTO" seguito da trattino
        # Pattern: "MAGGIORE SUITE - DUOMO DI PERUGIA" o "IMPERIAL SUITE - PALAZZO DELLA STAFFA"
        # IMPORTANTE: cerca DOPO eventuali messaggi del guest
        # OTTIMIZZAZIONE: limita il numero di tag da controllare per evitare timeout
        tags_to_check = soup.find_all(string=True)
        # Limita a max 100 tag per evitare timeout su email molto lunghe
        if len(tags_to_check) > 100:
            # Prendi solo gli ultimi 100 tag (dove probabilmente c'è il property name)
            tags_to_check = tags_to_check[-100:]
        
        for tag in tags_to_check:
            text_line = tag.strip()
            # Escludi righe troppo corte o che contengono parole da escludere
            if len(text_line) < 10 or should_exclude(text_line):
                continue
            # Cerca pattern: tutto maiuscolo, contiene SUITE/CASA/APPARTAMENTO, seguito da trattino
            if re.search(r"^[A-Z][A-Z\s\-]+(?:SUITE|CASA|APPARTAMENTO|ROOM)\s*-\s*[A-Z\s\-]+", text_line):
                return text_line
            # Pattern alternativo: contiene SUITE/CASA/APPARTAMENTO e non contiene "arriverà"
            if re.search(r"(?:SUITE|CASA|APPARTAMENTO|ROOM)", text_line, re.IGNORECASE):
                if not should_exclude(text_line):
                    return text_line
    
    # Fallback: cerca nel testo plain con pattern più specifico
    # IMPORTANTE: cerca DOPO eventuali messaggi del guest (dopo "Tradotto automaticamente" o prima di "Check-in")
    # Pattern 1: "MAGGIORE SUITE - DUOMO DI PERUGIA" (tutto maiuscolo con trattino)
    # Cerca dopo eventuali sezioni di messaggio
    text_after_message = text
    # Se c'è "Tradotto automaticamente", cerca dopo quella sezione
    if "Tradotto automaticamente" in text or "tradotto automaticamente" in text.lower():
        # Cerca il property name dopo "Tradotto automaticamente" e prima di "Check-in"
        match = re.search(r"Tradotto automaticamente.*?(https://www\.airbnb\.it/rooms/[^\s]+).*?([A-Z][A-Z\s\-]+(?:SUITE|CASA|APPARTAMENTO|ROOM)\s*-\s*[A-Z\s\-]+)", text, re.IGNORECASE | re.DOTALL)
        if match:
            result = match.group(2).strip()
            if not should_exclude(result):
                return result
    
    # IMPORTANTE: Cerca il property name DOPO eventuali messaggi del guest
    # I messaggi del guest di solito vengono prima del link alla room
    # Pattern: cerca dopo il link "https://www.airbnb.it/rooms/..." che viene DOPO il messaggio
    room_link_match = re.search(r"https://www\.airbnb\.it/rooms/[^\s]+", text, re.IGNORECASE)
    if room_link_match:
        # Cerca il property name dopo il link alla room
        text_after_room_link = text[room_link_match.end():]
        # Cerca pattern property name nelle prime 500 caratteri dopo il link
        search_text = text_after_room_link[:500]
        match = re.search(r"([A-Z][A-Z\s\-]+(?:SUITE|CASA|APPARTAMENTO|ROOM)\s*-\s*[A-Z\s\-]+)", search_text)
        if match:
            result = match.group(1).strip()
            if not should_exclude(result):
                return result
    
    # Pattern 1: "MAGGIORE SUITE - DUOMO DI PERUGIA" (tutto maiuscolo con trattino)
    match = re.search(r"([A-Z][A-Z\s\-]+(?:SUITE|CASA|APPARTAMENTO|ROOM)\s*-\s*[A-Z\s\-]+)", text)
    if match:
        result = match.group(1).strip()
        if not should_exclude(result):
            return result
    
    # Pattern 2: testo con SUITE/CASA/APPARTAMENTO ma senza "arriverà" o "confermata"
    # OTTIMIZZAZIONE: cerca solo dopo "Tradotto automaticamente" o prima di "Check-in" per evitare timeout
    # Limita la ricerca a una porzione del testo per migliorare le performance
    search_text = text
    if "Tradotto automaticamente" in text or "tradotto automaticamente" in text.lower():
        # Cerca dopo "Tradotto automaticamente" e prima di "Check-in"
        match_section = re.search(r"Tradotto automaticamente.*?(?=Check-in|$)", text, re.IGNORECASE | re.DOTALL)
        if match_section:
            search_text = match_section.group(0)
    elif "Check-in" in text:
        # Cerca prima di "Check-in"
        match_section = re.search(r"^(.*?)Check-in", text, re.IGNORECASE | re.DOTALL)
        if match_section:
            search_text = match_section.group(1)
    
    # Limita la lunghezza del testo da cercare (max 5000 caratteri) per evitare timeout
    if len(search_text) > 5000:
        # Prendi gli ultimi 5000 caratteri (dove probabilmente c'è il property name)
        search_text = search_text[-5000:]
    
    # Cerca solo l'ultimo match valido (più in basso nel testo, dopo eventuali messaggi)
    # NON creare una lista di tutti i match, cerca direttamente l'ultimo
    last_match = None
    for match in re.finditer(r"([A-Z][A-Za-z\s\-]+(?:SUITE|CASA|APPARTAMENTO|ROOM)[A-Za-z\s\-]*)", search_text):
        result = match.group(1).strip()
        if not should_exclude(result) and len(result) > 10 and len(result) < 100:
            last_match = result
    
    if last_match:
        return last_match
    
    return None


def extract_guest_name(text: str, soup: Optional[BeautifulSoup]) -> Optional[str]:
    """Estrae il nome dell'ospite dall'email Airbnb."""
    # Pattern 1: Cerca nel subject completo: "Prenotazione confermata - Marie-Thérèse Weber-Gobet arriverà il 12 ott"
    # Cattura tutto il nome fino a "arriverà", gestendo anche nomi con trattini e spazi
    match = re.search(r"confermata\s*-\s*([A-Z][A-Za-zÀ-ÿ\s\-]+?)\s+arriver", text, re.IGNORECASE)
    if match:
        name = match.group(1).strip()
        # Rimuovi eventuali prefissi come "NUOVA PRENOTAZIONE CONFERMATA!"
        name = re.sub(r"^.*?confermata\s*!?\s*", "", name, flags=re.IGNORECASE).strip()
        if name and len(name) > 2:
            return name
    
    # Pattern 2: Cerca "FRANCESCO" o "Francesco Brufani" prima di "arriverà" (pattern più generico)
    # Cattura nomi con spazi, trattini, apostrofi
    match = re.search(r"([A-Z][A-Za-zÀ-ÿ\s\-']+?)\s+arriverà", text, re.IGNORECASE)
    if match:
        name = match.group(1).strip()
        # Rimuovi prefissi
        name = re.sub(r"^.*?confermata\s*!?\s*", "", name, flags=re.IGNORECASE).strip()
        name = re.sub(r"^.*?-\s*", "", name, flags=re.IGNORECASE).strip()
        if name and len(name) > 2:
            return name
    
    # Pattern 3: Cerca "NUOVA PRENOTAZIONE CONFERMATA! MARIE-THÉRÈSE ARRIVERÀ"
    match = re.search(r"NUOVA PRENOTAZIONE CONFERMATA!\s*([A-Z][A-Z\s\-]+?)\s+ARRIVER", text, re.IGNORECASE)
    if match:
        name = match.group(1).strip()
        if name and len(name) > 2:
            # Converti tutto maiuscolo in formato title case se possibile
            return name
    
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
                name = re.sub(r"^.*?NUOVA PRENOTAZIONE CONFERMATA!\s*", "", name, flags=re.IGNORECASE).strip()
                if name and len(name) > 2:
                    return name
    
    return None


def extract_date(text: str, soup: Optional[BeautifulSoup], labels: list[str]) -> Optional[datetime]:
    """Estrae una data dall'email Airbnb (check-in o check-out)."""
    from datetime import datetime as dt
    
    # Pattern per "gio 3 set 2026" o "3 settembre 2026" o "dom 12 ott" (senza anno)
    for label in labels:
        # Pattern 1: "Check-in gio 3 set 2026" (stessa riga, CON anno)
        pattern1 = re.compile(rf"{label}.*?([a-z]{{2,3}}\s+\d{{1,2}}\s+[a-z]{{3}}\s+\d{{4}})", re.IGNORECASE | re.DOTALL)
        match = pattern1.search(text)
        if match:
            try:
                return date_parser.parse(match.group(1), dayfirst=True, fuzzy=True)
            except (ValueError, OverflowError):
                pass
        
        # Pattern 2: "Check-in 3 settembre 2026" (stessa riga, CON anno)
        pattern2 = re.compile(rf"{label}.*?(\d{{1,2}}\s+[a-z]+\s+\d{{4}})", re.IGNORECASE | re.DOTALL)
        match = pattern2.search(text)
        if match:
            try:
                return date_parser.parse(match.group(1), dayfirst=True, fuzzy=True)
            except (ValueError, OverflowError):
                pass
        
        # Pattern 3: "Check-in" su una riga, data sulla riga successiva (multiline, CON anno)
        pattern3 = re.compile(rf"{label}.*?\n.*?([a-z]{{2,3}}\s+\d{{1,2}}\s+[a-z]{{3}}\s+\d{{4}})", re.IGNORECASE | re.MULTILINE)
        match = pattern3.search(text)
        if match:
            try:
                return date_parser.parse(match.group(1), dayfirst=True, fuzzy=True)
            except (ValueError, OverflowError):
                pass
        
        # Pattern 4: Gestisce il caso "Check-in         Check-out\ngio 3 set 2026   sab 5 set 2026" (CON anno)
        # Cerca tutte le date dopo "Check-in" e "Check-out", poi prendi la prima per check-in, la seconda per check-out
        if label.lower() == "check-in":
            # Cerca "Check-in" seguito da "Check-out" e poi due date sulla stessa riga (CON anno)
            # Gestisce anche spazi multipli e caratteri speciali (quoted-printable)
            pattern4 = re.compile(r"Check-in\s+Check-out.*?\n\s*([a-z]{2,3}\s+\d{1,2}\s+[a-z]{3}\s+\d{4})\s+([a-z]{2,3}\s+\d{1,2}\s+[a-z]{3}\s+\d{4})", re.IGNORECASE | re.MULTILINE | re.DOTALL)
            match = pattern4.search(text)
            if match:
                try:
                    # Prendi la prima data (check-in)
                    return date_parser.parse(match.group(1), dayfirst=True, fuzzy=True)
                except (ValueError, OverflowError):
                    pass
            # Pattern alternativo: "Check-in" e "Check-out" su righe separate
            pattern4_alt = re.compile(r"Check-in.*?Check-out.*?\n.*?([a-z]{2,3}\s+\d{1,2}\s+[a-z]{3}\s+\d{4})\s+([a-z]{2,3}\s+\d{1,2}\s+[a-z]{3}\s+\d{4})", re.IGNORECASE | re.MULTILINE | re.DOTALL)
            match = pattern4_alt.search(text)
            if match:
                try:
                    return date_parser.parse(match.group(1), dayfirst=True, fuzzy=True)
                except (ValueError, OverflowError):
                    pass
            # Fallback: cerca "Check-in" e poi la prima data che segue (anche su righe diverse, CON anno)
            pattern4_fallback = re.compile(r"Check-in.*?([a-z]{2,3}\s+\d{1,2}\s+[a-z]{3}\s+\d{4})", re.IGNORECASE | re.DOTALL)
            match = pattern4_fallback.search(text)
            if match:
                try:
                    return date_parser.parse(match.group(1), dayfirst=True, fuzzy=True)
                except (ValueError, OverflowError):
                    pass
        elif label.lower() == "check-out":
            # Cerca "Check-in" seguito da "Check-out" e poi due date sulla stessa riga (CON anno)
            # Gestisce anche spazi multipli e caratteri speciali (quoted-printable)
            pattern4 = re.compile(r"Check-in\s+Check-out.*?\n\s*([a-z]{2,3}\s+\d{1,2}\s+[a-z]{3}\s+\d{4})\s+([a-z]{2,3}\s+\d{1,2}\s+[a-z]{3}\s+\d{4})", re.IGNORECASE | re.MULTILINE | re.DOTALL)
            match = pattern4.search(text)
            if match:
                try:
                    # Prendi la seconda data (check-out)
                    return date_parser.parse(match.group(2), dayfirst=True, fuzzy=True)
                except (ValueError, OverflowError):
                    pass
            # Pattern alternativo: "Check-in" e "Check-out" su righe separate
            pattern4_alt = re.compile(r"Check-in.*?Check-out.*?\n.*?([a-z]{2,3}\s+\d{1,2}\s+[a-z]{3}\s+\d{4})\s+([a-z]{2,3}\s+\d{1,2}\s+[a-z]{3}\s+\d{4})", re.IGNORECASE | re.MULTILINE | re.DOTALL)
            match = pattern4_alt.search(text)
            if match:
                try:
                    return date_parser.parse(match.group(2), dayfirst=True, fuzzy=True)
                except (ValueError, OverflowError):
                    pass
            # Fallback: cerca "Check-out" e poi la prima data che segue (anche su righe diverse, CON anno)
            pattern4_fallback = re.compile(r"Check-out.*?([a-z]{2,3}\s+\d{1,2}\s+[a-z]{3}\s+\d{4})", re.IGNORECASE | re.DOTALL)
            match = pattern4_fallback.search(text)
            if match:
                try:
                    return date_parser.parse(match.group(1), dayfirst=True, fuzzy=True)
                except (ValueError, OverflowError):
                    pass
        
        # Pattern 5: Gestisce date SENZA anno (es. "dom 12 ott")
        # Se la data è senza anno, assumiamo l'anno corrente o prossimo se la data è passata
        if label.lower() == "check-in":
            # Cerca "Check-in" seguito da "Check-out" e poi due date SENZA anno
            pattern5 = re.compile(r"Check-in.*?Check-out.*?\n.*?([a-z]{2,3}\s+\d{1,2}\s+[a-z]{3})\s+([a-z]{2,3}\s+\d{1,2}\s+[a-z]{3})", re.IGNORECASE | re.MULTILINE | re.DOTALL)
            match = pattern5.search(text)
            if match:
                try:
                    date_str = match.group(1)
                    # Aggiungi l'anno corrente o prossimo
                    current_year = dt.now().year
                    # Prova con anno corrente
                    try:
                        parsed = date_parser.parse(f"{date_str} {current_year}", dayfirst=True, fuzzy=True)
                        # Se la data è passata, usa l'anno prossimo
                        if parsed < dt.now():
                            parsed = date_parser.parse(f"{date_str} {current_year + 1}", dayfirst=True, fuzzy=True)
                        return parsed
                    except (ValueError, OverflowError):
                        pass
                except (ValueError, OverflowError):
                    pass
            # Fallback: cerca "Check-in" e poi la prima data SENZA anno
            pattern5_fallback = re.compile(r"Check-in.*?([a-z]{2,3}\s+\d{1,2}\s+[a-z]{3})(?:\s+\d{4})?", re.IGNORECASE | re.DOTALL)
            match = pattern5_fallback.search(text)
            if match:
                try:
                    date_str = match.group(1)
                    current_year = dt.now().year
                    try:
                        parsed = date_parser.parse(f"{date_str} {current_year}", dayfirst=True, fuzzy=True)
                        if parsed < dt.now():
                            parsed = date_parser.parse(f"{date_str} {current_year + 1}", dayfirst=True, fuzzy=True)
                        return parsed
                    except (ValueError, OverflowError):
                        pass
                except (ValueError, OverflowError):
                    pass
        elif label.lower() == "check-out":
            # Cerca "Check-in" seguito da "Check-out" e poi due date SENZA anno
            pattern5 = re.compile(r"Check-in.*?Check-out.*?\n.*?([a-z]{2,3}\s+\d{1,2}\s+[a-z]{3})\s+([a-z]{2,3}\s+\d{1,2}\s+[a-z]{3})", re.IGNORECASE | re.MULTILINE | re.DOTALL)
            match = pattern5.search(text)
            if match:
                try:
                    date_str = match.group(2)  # Seconda data per check-out
                    current_year = dt.now().year
                    try:
                        parsed = date_parser.parse(f"{date_str} {current_year}", dayfirst=True, fuzzy=True)
                        if parsed < dt.now():
                            parsed = date_parser.parse(f"{date_str} {current_year + 1}", dayfirst=True, fuzzy=True)
                        return parsed
                    except (ValueError, OverflowError):
                        pass
                except (ValueError, OverflowError):
                    pass
            # Fallback: cerca "Check-out" e poi la prima data SENZA anno
            pattern5_fallback = re.compile(r"Check-out.*?([a-z]{2,3}\s+\d{1,2}\s+[a-z]{3})(?:\s+\d{4})?", re.IGNORECASE | re.DOTALL)
            match = pattern5_fallback.search(text)
            if match:
                try:
                    date_str = match.group(1)
                    current_year = dt.now().year
                    try:
                        parsed = date_parser.parse(f"{date_str} {current_year}", dayfirst=True, fuzzy=True)
                        if parsed < dt.now():
                            parsed = date_parser.parse(f"{date_str} {current_year + 1}", dayfirst=True, fuzzy=True)
                        return parsed
                    except (ValueError, OverflowError):
                        pass
                except (ValueError, OverflowError):
                    pass
    
    if soup:
        # Cerca nelle celle della tabella o span
        for tag in soup.find_all(["td", "span", "div", "p"]):
            text_content = tag.get_text()
            if any(label.lower() in text_content.lower() for label in labels):
                # Cerca data nel testo
                match = re.search(r"([a-z]{{2,3}}\s+\d{{1,2}}\s+[a-z]{{3}}\s+\d{{4}}|\d{{1,2}}\s+[a-z]+\s+\d{{4}})", text_content, re.IGNORECASE)
                if match:
                    try:
                        return date_parser.parse(match.group(1), dayfirst=True, fuzzy=True)
                    except (ValueError, OverflowError):
                        continue
        
        # Cerca pattern "Check-in" e "Check-out" seguiti da date in elementi HTML separati
        # Esempio: <div>Check-in</div><div>gio 3 set 2026</div>
        check_in_elements = soup.find_all(string=re.compile(r"Check-in", re.IGNORECASE))
        check_out_elements = soup.find_all(string=re.compile(r"Check-out", re.IGNORECASE))
        
        for label, elements in [("Check-in", check_in_elements), ("Check-out", check_out_elements)]:
            if label.lower() not in [l.lower() for l in labels]:
                continue
            for elem in elements:
                # Cerca nel parent o nei sibling
                parent = elem.parent
                if parent:
                    # Cerca nel testo del parent
                    parent_text = parent.get_text()
                    match = re.search(r"([a-z]{{2,3}}\s+\d{{1,2}}\s+[a-z]{{3}}\s+\d{{4}}|\d{{1,2}}\s+[a-z]+\s+\d{{4}})", parent_text, re.IGNORECASE)
                    if match:
                        try:
                            return date_parser.parse(match.group(1), dayfirst=True, fuzzy=True)
                        except (ValueError, OverflowError):
                            continue
                    # Cerca nei sibling successivi
                    next_sibling = parent.find_next_sibling()
                    if next_sibling:
                        sibling_text = next_sibling.get_text()
                        match = re.search(r"([a-z]{{2,3}}\s+\d{{1,2}}\s+[a-z]{{3}}\s+\d{{4}}|\d{{1,2}}\s+[a-z]+\s+\d{{4}})", sibling_text, re.IGNORECASE)
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


def extract_guest_message_from_confirmation(text: str, soup: Optional[BeautifulSoup], guest_name: Optional[str]) -> Optional[str]:
    """Estrae il messaggio del guest da un'email di conferma Airbnb."""
    # Il messaggio del guest di solito viene PRIMA del link alla room
    # Pattern: cerca testo tra il nome guest e il link "https://www.airbnb.it/rooms/..."
    
    # Cerca il link alla room
    room_link_match = re.search(r"https://www\.airbnb\.it/rooms/[^\s]+", text, re.IGNORECASE)
    if not room_link_match:
        return None
    
    # Cerca il testo PRIMA del link alla room
    text_before_room_link = text[:room_link_match.start()]
    
    # Cerca pattern di messaggio del guest
    # Pattern 1: Messaggio che inizia con "Ciao" o simile
    message_patterns = [
        r"(Ciao\s+[^\n]+(?:\n[^\n]+)*?)(?=Tradotto automaticamente|Invia un Messaggio|https://|Check-in|$)",
        r"(Hallo\s+[^\n]+(?:\n[^\n]+)*?)(?=Tradotto automaticamente|Invia un Messaggio|https://|Check-in|$)",
        r"((?:Siamo|Desideriamo|Viaggiamo|Non vediamo l'ora)[^\n]+(?:\n[^\n]+)*?)(?=Tradotto automaticamente|Invia un Messaggio|https://|Check-in|$)",
    ]
    
    for pattern in message_patterns:
        match = re.search(pattern, text_before_room_link, re.IGNORECASE | re.DOTALL)
        if match:
            message = match.group(1).strip()
            # Pulisci il messaggio: rimuovi spazi multipli e caratteri speciali
            message = re.sub(r'\s+', ' ', message)
            # Rimuovi prefissi comuni
            message = re.sub(r'^(Ciao|Hallo)\s+', '', message, flags=re.IGNORECASE)
            # Rimuovi suffissi comuni
            message = re.sub(r'\s+(Non vediamo l\'ora|Vi salutiamo|Cordiali saluti).*$', '', message, flags=re.IGNORECASE)
            if len(message) > 20:  # Solo se il messaggio è abbastanza lungo
                return message
    
    # Pattern 2: Se c'è "Tradotto automaticamente", il messaggio è prima
    if "Tradotto automaticamente" in text_before_room_link:
        # Cerca il testo tra l'inizio e "Tradotto automaticamente"
        match = re.search(r"^(.+?)(?=Tradotto automaticamente)", text_before_room_link, re.IGNORECASE | re.DOTALL)
        if match:
            message = match.group(1).strip()
            # Rimuovi header comuni
            message = re.sub(r'^(NUOVA PRENOTAZIONE CONFERMATA!|Invia un messaggio).*?\n', '', message, flags=re.IGNORECASE)
            # Rimuovi link e URL
            message = re.sub(r'https?://[^\s]+', '', message)
            message = re.sub(r'\s+', ' ', message).strip()
            if len(message) > 20:
                return message
    
    return None


def normalize_airbnb_text(value: str) -> str:
    """Rimuove artefatti quoted-printable e normalizza spazi per i testi Airbnb."""
    if not value:
        return value
    # Rimuovi soft break di quoted-printable
    cleaned = value.replace("=\n", "")
    # Sostituisci caratteri speciali comuni (=20, =C2=A0) con spazi normali
    artifacts = ["=20", "=C2=A0", "=E2=80=AF"]
    for artifact in artifacts:
        cleaned = cleaned.replace(artifact, " ")
    # Normalizza sequenze multiple di spazi lasciando le newline intatte
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned


def parse_date_header(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return date_parser.parse(value)
    except (ValueError, OverflowError):
        return None

