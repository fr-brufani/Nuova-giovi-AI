"""Processor per convertire BookingMessage in ParsedEmail per pipeline esistente."""

from __future__ import annotations

import logging
from datetime import datetime

from ..models.booking_message import BookingMessage
from ..models.parsing import GuestMessageInfo, ParsedEmail, ParsedEmailMetadata

logger = logging.getLogger(__name__)


class BookingMessageProcessor:
    """
    Processor per convertire BookingMessage in ParsedEmail.
    
    Converti BookingMessage (da API Booking.com) in ParsedEmail per usare
    GuestMessagePipeline esistente senza modifiche.
    """

    @staticmethod
    def process_message(booking_message: BookingMessage) -> ParsedEmail:
        """
        Converte BookingMessage in ParsedEmail.
        
        Args:
            booking_message: Messaggio dalla Booking.com Messaging API
            
        Returns:
            ParsedEmail compatibile con GuestMessagePipeline
        """
        # Filtra solo messaggi guest (già fatto nel polling service, ma double-check)
        if booking_message.sender.participant_type != "GUEST":
            raise ValueError(
                f"Messaggio non-GUEST non può essere processato: "
                f"participant_type={booking_message.sender.participant_type}"
            )
        
        # Estrai reservation_id da conversation_reference
        reservation_id = booking_message.conversation.conversation_reference
        if not reservation_id:
            raise ValueError(
                f"Messaggio senza conversation_reference (reservation_id): "
                f"message_id={booking_message.message_id}"
            )
        
        # Crea GuestMessageInfo
        guest_message = GuestMessageInfo(
            reservationId=reservation_id,
            source="booking",
            message=booking_message.content,
            guestName=booking_message.sender.name,
            guestEmail=booking_message.sender.email_alias,
            replyTo=booking_message.reply_to or booking_message.sender.email_alias,
            threadId=None,  # Booking.com non usa thread_id come Airbnb
        )
        
        # Crea ParsedEmailMetadata
        # Per Booking.com API, non abbiamo subject/sender email come Gmail
        # Usiamo dati disponibili
        metadata = ParsedEmailMetadata(
            subject=None,  # Booking.com non ha subject
            sender=booking_message.sender.email_alias or booking_message.sender.name,
            recipients=None,
            receivedAt=booking_message.timestamp,
            gmailMessageId=None,  # Usa Booking.com message_id come riferimento
            snippet=booking_message.content[:200] if len(booking_message.content) > 200 else booking_message.content,
        )
        
        # Crea ParsedEmail
        parsed_email = ParsedEmail(
            kind="booking_message",
            reservation=None,  # Sarà recuperato da GuestMessagePipeline usando reservation_id
            guestMessage=guest_message,
            metadata=metadata,
            rawText=booking_message.content,
            rawHtml=None,  # Booking.com non fornisce HTML
        )
        
        logger.debug(
            f"[BookingMessageProcessor] ✅ Convertito BookingMessage → ParsedEmail: "
            f"message_id={booking_message.message_id}, reservation_id={reservation_id}"
        )
        
        return parsed_email
    
    @staticmethod
    def should_process_message(booking_message: BookingMessage) -> bool:
        """
        Verifica se un messaggio deve essere processato.
        
        Filtri:
        - Solo messaggi GUEST
        - Deve avere conversation_reference (reservation_id)
        - Opzionale: ignora automatically_sent_template (se configurato)
        
        Args:
            booking_message: Messaggio dalla Booking.com Messaging API
            
        Returns:
            True se deve essere processato, False altrimenti
        """
        # Solo messaggi guest
        if booking_message.sender.participant_type != "GUEST":
            logger.debug(
                f"[BookingMessageProcessor] Salto messaggio non-GUEST: "
                f"participant_type={booking_message.sender.participant_type}"
            )
            return False
        
        # Deve avere reservation_id (conversation_reference)
        if not booking_message.conversation.conversation_reference:
            logger.warning(
                f"[BookingMessageProcessor] Messaggio senza reservation_id: "
                f"message_id={booking_message.message_id}"
            )
            return False
        
        # Opzionale: ignora self-service events o template automatici
        # Per ora processiamo tutto, ma possiamo aggiungere filtri se necessario
        if booking_message.message_type == "self_service_event":
            logger.debug(
                f"[BookingMessageProcessor] Salto self-service event: message_id={booking_message.message_id}"
            )
            return False
        
        # Verifica se è template automatico (se disponibile in attributes)
        if booking_message.attributes and booking_message.attributes.template_id:
            logger.debug(
                f"[BookingMessageProcessor] Messaggio da template automatico: "
                f"message_id={booking_message.message_id}, template_id={booking_message.attributes.template_id}"
            )
            # Per ora processiamo anche template automatici (l'host può decidere di rispondere)
            # Se necessario, possiamo aggiungere un filtro qui
        
        return True

