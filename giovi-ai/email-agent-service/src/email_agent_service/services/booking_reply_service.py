"""Service per inviare risposte via Booking.com Messaging API."""

from __future__ import annotations

import logging
from typing import Optional

from ..models.booking_message import BookingMessage
from ..services.guest_message_pipeline import GuestMessageContext
from ..services.integrations.booking_messaging_client import (
    BookingAPIError,
    BookingForbiddenError,
    BookingMessagingClient,
)

logger = logging.getLogger(__name__)


class BookingReplyService:
    """
    Service per inviare risposte ai guest via Booking.com Messaging API.
    
    Usa conversation_id e property_id dal BookingMessage per inviare messaggi.
    """

    def __init__(self, messaging_client: BookingMessagingClient) -> None:
        """
        Inizializza reply service.
        
        Args:
            messaging_client: Client Messaging API
        """
        self._client = messaging_client
        logger.info(
            f"[BookingReplyService] ✅ Initialized (mock_mode={messaging_client.mock_mode})"
        )
    
    def send_reply(
        self,
        booking_message: BookingMessage,
        reply_text: str,
        context: Optional[GuestMessageContext] = None,
        mark_as_read: bool = True,
    ) -> str:
        """
        Invia risposta al guest via Booking.com Messaging API.
        
        Args:
            booking_message: Messaggio originale dal guest
            reply_text: Testo della risposta generata da AI
            context: Contesto del messaggio (opzionale, per logging)
            mark_as_read: Se True, marca il messaggio originale come letto
            
        Returns:
            message_id del messaggio inviato
            
        Raises:
            BookingAPIError: Se invio fallisce
            BookingForbiddenError: Se accesso negato alla property
        """
        # Estrai conversation_id e property_id dal messaggio
        conversation_id = booking_message.conversation.conversation_id
        property_id = booking_message.conversation.property_id
        
        if not conversation_id:
            raise ValueError(
                f"Messaggio senza conversation_id: message_id={booking_message.message_id}"
            )
        
        if not property_id:
            raise ValueError(
                f"Messaggio senza property_id: message_id={booking_message.message_id}"
            )
        
        # Log info
        reservation_id = booking_message.conversation.conversation_reference
        logger.info(
            f"[BookingReplyService] Invio risposta: "
            f"property_id={property_id}, conversation_id={conversation_id}, "
            f"reservation_id={reservation_id}, guest={booking_message.sender.name}"
        )
        
        if context:
            logger.debug(
                f"[BookingReplyService] Contesto: host_id={context.host_id}, "
                f"client_id={context.client_id}, property_name={context.property_name}"
            )
        
        try:
            # Invia messaggio via API
            response = self._client.send_message(
                property_id=property_id,
                conversation_id=conversation_id,
                content=reply_text,
                attachment_ids=None,  # Per ora non supportiamo allegati
            )
            
            # Estrai message_id dalla response
            data = response.get("data", {})
            sent_message_id = data.get("message_id")
            
            if not sent_message_id:
                logger.warning(
                    f"[BookingReplyService] ⚠️ Risposta inviata ma message_id non trovato nella response: {response}"
                )
                # Usa un placeholder
                sent_message_id = f"sent_{booking_message.message_id}"
            
            logger.info(
                f"[BookingReplyService] ✅ Risposta inviata con successo: "
                f"sent_message_id={sent_message_id}, conversation_id={conversation_id}"
            )
            
            # Opzionalmente marca messaggio originale come letto
            if mark_as_read:
                try:
                    self._mark_message_as_read(
                        booking_message=booking_message,
                        property_id=property_id,
                        conversation_id=conversation_id,
                    )
                except Exception as e:
                    # Non bloccare se mark_as_read fallisce
                    logger.warning(
                        f"[BookingReplyService] ⚠️ Errore marcando messaggio come letto: {e}"
                    )
            
            return sent_message_id
            
        except BookingForbiddenError as e:
            logger.error(
                f"[BookingReplyService] ❌ Accesso negato alla property {property_id}: {e}"
            )
            raise
        
        except BookingAPIError as e:
            logger.error(
                f"[BookingReplyService] ❌ Errore invio risposta: {e}",
                exc_info=True,
            )
            raise
    
    def _mark_message_as_read(
        self,
        booking_message: BookingMessage,
        property_id: str,
        conversation_id: str,
    ) -> None:
        """
        Marca messaggio come letto.
        
        Args:
            booking_message: Messaggio originale
            property_id: ID della property
            conversation_id: ID della conversazione
            
        Note:
            Per Booking.com, participant_id è generalmente il property_id stesso
            o un ID associato alla property. Se necessario, possiamo recuperarlo
            dalla reservation o usare property_id come fallback.
        """
        # Booking.com usa participant_id della property
        # Possiamo usare property_id come participant_id (standard Booking.com)
        # Oppure recuperarlo dalla reservation se necessario
        participant_id = str(property_id)  # Fallback: usa property_id come participant_id
        
        # Se abbiamo property_id da conversation, usiamolo
        if booking_message.conversation.property_id:
            participant_id = str(booking_message.conversation.property_id)
        
        logger.debug(
            f"[BookingReplyService] Marca messaggio come letto: "
            f"message_id={booking_message.message_id}, participant_id={participant_id}"
        )
        
        response = self._client.mark_as_read(
            property_id=property_id,
            conversation_id=conversation_id,
            message_ids=[booking_message.message_id],
            participant_id=participant_id,
        )
        
        logger.debug(
            f"[BookingReplyService] ✅ Messaggio marcato come letto: {response}"
        )
    
    def send_reply_with_context(
        self,
        booking_message: BookingMessage,
        context: GuestMessageContext,
        reply_text: str,
        mark_as_read: bool = True,
    ) -> str:
        """
        Invia risposta usando GuestMessageContext (wrapper più conveniente).
        
        Args:
            booking_message: Messaggio originale
            context: Contesto del messaggio
            reply_text: Testo della risposta
            mark_as_read: Se True, marca come letto
            
        Returns:
            message_id del messaggio inviato
        """
        return self.send_reply(
            booking_message=booking_message,
            reply_text=reply_text,
            context=context,
            mark_as_read=mark_as_read,
        )

