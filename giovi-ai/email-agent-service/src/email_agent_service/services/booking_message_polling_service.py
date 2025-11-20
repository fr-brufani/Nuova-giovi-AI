"""Polling service per Booking.com Messaging API - MULTI-HOST."""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

from firebase_admin import firestore

from ..config.settings import get_settings
from ..models.booking_message import BookingMessage
from ..repositories.booking_property_mappings import BookingPropertyMappingsRepository
from ..repositories.processed_messages import ProcessedMessageRepository
from ..services.guest_message_pipeline import GuestMessagePipelineService
from ..services.gemini_service import GeminiService
from ..services.booking_message_processor import BookingMessageProcessor
from ..services.booking_reply_service import BookingReplyService
from ..services.integrations.booking_messaging_client import BookingMessagingClient

logger = logging.getLogger(__name__)


class BookingMessagePollingService:
    """
    Service per polling continuo dei messaggi Booking.com - MULTI-HOST.
    
    **IMPORTANTE: Questo servizio gestisce TUTTI gli host contemporaneamente.**
    
    - Usa UN SOLO set di credenziali Booking.com (Machine Account condiviso)
    - Recupera messaggi per TUTTE le properties del provider
    - Mappa ogni messaggio al corretto host_id usando conversation_reference → reservation_id → property_id → mapping → host_id
    - Polla ogni N secondi (default 60s) per recuperare nuovi messaggi,
      li processa con AI e invia risposte, poi conferma recupero.
    """

    def __init__(
        self,
        messaging_client: BookingMessagingClient,
        persistence_service,  # PersistenceService - evito import circolare
        firestore_client: firestore.Client,
        gemini_service: Optional[GeminiService] = None,
        polling_interval: Optional[int] = None,
    ) -> None:
        """
        Inizializza polling service MULTI-HOST.
        
        Args:
            messaging_client: Client Messaging API (condiviso per tutti gli host)
            persistence_service: Service per accesso dati (per guest pipeline)
            firestore_client: Firestore client per repositories
            gemini_service: Service per generazione risposte AI (opzionale)
            polling_interval: Intervallo polling in secondi (default da settings: 60s)
        """
        self._settings = get_settings()
        self._client = messaging_client
        self._persistence_service = persistence_service
        self._firestore_client = firestore_client
        self._gemini_service = gemini_service
        self._mappings_repo = BookingPropertyMappingsRepository(firestore_client)
        self._processed_repo = ProcessedMessageRepository(firestore_client)
        self._pipeline_service = GuestMessagePipelineService(firestore_client)
        self._message_processor = BookingMessageProcessor()
        self._reply_service = BookingReplyService(messaging_client)
        self._polling_interval = polling_interval or self._settings.booking_polling_interval_messages
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        logger.info(
            f"[BookingMessagePolling] ✅ Initialized MULTI-HOST with interval={self._polling_interval}s, "
            f"mock_mode={messaging_client.mock_mode}"
        )
    
    def start(self) -> None:
        """Avvia polling service MULTI-HOST in background thread."""
        if self._running:
            logger.warning("[BookingMessagePolling] Service già in esecuzione")
            return
        
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name="BookingMessagePolling")
        self._thread.start()
        logger.info(
            f"[BookingMessagePolling] ✅ MULTI-HOST Service avviato "
            f"(interval={self._polling_interval}s, gestisce TUTTI gli host)"
        )
    
    def stop(self) -> None:
        """Ferma polling service."""
        if not self._running:
            return
        
        logger.info("[BookingMessagePolling] Fermata service...")
        self._running = False
        self._stop_event.set()
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
            if self._thread.is_alive():
                logger.warning("[BookingMessagePolling] Thread non terminato entro timeout")
        
        logger.info("[BookingMessagePolling] ✅ Service fermato")
    
    def _poll_loop(self) -> None:
        """Loop principale di polling."""
        logger.info("[BookingMessagePolling] Polling loop avviato")
        
        while self._running and not self._stop_event.is_set():
            try:
                # Poll nuovi messaggi
                self._poll_messages()
                
            except Exception as e:
                logger.error(f"[BookingMessagePolling] Errore durante polling: {e}", exc_info=True)
                # Continua anche in caso di errore (non fermare il loop)
            
            # Attendi prima del prossimo polling
            self._stop_event.wait(timeout=self._polling_interval)
        
        logger.info("[BookingMessagePolling] Polling loop terminato")
    
    def _find_host_id_for_reservation(self, reservation_id: str) -> Optional[str]:
        """
        Trova host_id per un reservation_id.
        
        Cerca reservation in Firestore e usa property_id per trovare mapping.
        
        Args:
            reservation_id: Reservation ID Booking.com
            
        Returns:
            host_id se trovato, None altrimenti
        """
        # Cerca reservation in Firestore
        reservations_ref = self._firestore_client.collection("reservations")
        query = (
            reservations_ref
            .where("reservationId", "==", reservation_id)
            .where("importedFrom", "==", "booking_api")
            .limit(1)
        )
        docs = list(query.get())
        
        if not docs:
            logger.debug(
                f"[BookingMessagePolling] Reservation {reservation_id} non trovata in Firestore"
            )
            return None
        
        reservation_data = docs[0].to_dict() or {}
        host_id = reservation_data.get("hostId")
        
        if not host_id:
            logger.warning(
                f"[BookingMessagePolling] Reservation {reservation_id} senza hostId"
            )
            return None
        
        return host_id
    
    def _find_host_id_for_property(self, booking_property_id: str) -> Optional[str]:
        """
        Trova host_id per un booking_property_id usando mapping.
        
        Args:
            booking_property_id: Property ID Booking.com
            
        Returns:
            host_id se trovato, None altrimenti
        """
        mapping = self._mappings_repo.get_by_booking_property_id(booking_property_id)
        if mapping:
            return mapping.host_id
        
        logger.warning(
            f"[BookingMessagePolling] ⚠️ Nessun mapping trovato per booking_property_id={booking_property_id}"
        )
        return None
    
    def _poll_messages(self) -> None:
        """
        Poll nuovi messaggi e processa - MULTI-HOST.
        
        Per ogni messaggio:
        1. Estrai reservation_id da conversation_reference
        2. Trova reservation in Firestore
        3. Estrai property_id dalla reservation
        4. Trova host_id usando mapping booking_property_id → host_id
        5. Processa messaggio con guest pipeline
        6. Genera risposta AI se necessario
        7. Invia risposta via API
        """
        try:
            # GET nuovi messaggi (recupera TUTTI i messaggi del provider)
            response = self._client.get_latest_messages()
            
            if not response or not response.get("data"):
                return
            
            data = response["data"]
            messages_data = data.get("messages", [])
            number_of_messages = data.get("number_of_messages", 0)
            
            if number_of_messages == 0 or not messages_data:
                # Nessun messaggio nuovo
                return
            
            logger.info(f"[BookingMessagePolling] Trovati {number_of_messages} nuovi messaggi")
            
            # Processa ogni messaggio (ogni messaggio può appartenere a host diversi)
            processed_count = 0
            skipped_count = 0
            replied_count = 0
            messages_to_confirm = []
            
            for message_data in messages_data:
                try:
                    # Parse BookingMessage
                    booking_message = BookingMessage.from_api_response(message_data)
                    
                    # Usa processor per filtrare e validare messaggio
                    if not self._message_processor.should_process_message(booking_message):
                        logger.debug(
                            f"[BookingMessagePolling] Messaggio filtrato dal processor: "
                            f"message_id={booking_message.message_id}"
                        )
                        messages_to_confirm.append(booking_message.message_id)
                        continue
                    
                    # Estrai reservation_id da conversation_reference
                    reservation_id = booking_message.conversation.conversation_reference
                    if not reservation_id:
                        logger.warning(
                            f"[BookingMessagePolling] Messaggio senza conversation_reference: "
                            f"message_id={booking_message.message_id}"
                        )
                        messages_to_confirm.append(booking_message.message_id)
                        skipped_count += 1
                        continue
                    
                    # Trova host_id usando reservation
                    host_id = self._find_host_id_for_reservation(reservation_id)
                    
                    if not host_id:
                        logger.warning(
                            f"[BookingMessagePolling] ⚠️ Salto messaggio {booking_message.message_id}: "
                            f"nessun host_id trovato per reservation_id={reservation_id}"
                        )
                        messages_to_confirm.append(booking_message.message_id)
                        skipped_count += 1
                        continue
                    
                    # Verifica deduplicazione (già processato?)
                    message_id = booking_message.message_id
                    if self._processed_repo.is_processed(
                        message_id=message_id,
                        host_id=host_id,
                        source="booking_api",
                    ):
                        logger.debug(
                            f"[BookingMessagePolling] Messaggio già processato: message_id={message_id}, host={host_id}"
                        )
                        messages_to_confirm.append(message_id)
                        continue
                    
                    logger.info(
                        f"[BookingMessagePolling] Processando messaggio: message_id={message_id}, "
                        f"reservation_id={reservation_id}, host={host_id}, "
                        f"guest={booking_message.sender.name}"
                    )
                    
                    # Converti BookingMessage → ParsedEmail
                    try:
                        parsed_email = self._message_processor.process_message(booking_message)
                    except Exception as e:
                        logger.error(
                            f"[BookingMessagePolling] Errore conversione BookingMessage → ParsedEmail: {e}",
                            exc_info=True,
                        )
                        # Salta questo messaggio ma confermalo
                        messages_to_confirm.append(message_id)
                        continue
                    
                    # Usa GuestMessagePipeline per verificare se processare
                    should_process, client_id = self._pipeline_service.should_process_message(
                        parsed_email=parsed_email,
                        host_id=host_id,
                        is_new_reservation=False,  # Messaggi da conversazioni esistenti
                    )
                    
                    if not should_process:
                        logger.info(
                            f"[BookingMessagePolling] Messaggio non deve essere processato "
                            f"(auto-reply disabilitato o altro filtro): message_id={message_id}"
                        )
                        # Marca come processato (anche se non abbiamo risposto)
                        self._processed_repo.mark_processed_api(
                            message_id=message_id,
                            host_id=host_id,
                            source="booking_api",
                        )
                        messages_to_confirm.append(message_id)
                        continue
                    
                    if not client_id:
                        logger.warning(
                            f"[BookingMessagePolling] Cliente non trovato per messaggio: "
                            f"message_id={message_id}, reservation_id={reservation_id}"
                        )
                        # Marca come processato (non possiamo processare senza cliente)
                        self._processed_repo.mark_processed_api(
                            message_id=message_id,
                            host_id=host_id,
                            source="booking_api",
                        )
                        messages_to_confirm.append(message_id)
                        continue
                    
                    # Estrai contesto per AI reply
                    try:
                        context = self._pipeline_service.extract_context(
                            parsed_email=parsed_email,
                            host_id=host_id,
                            client_id=client_id,
                        )
                    except Exception as e:
                        logger.error(
                            f"[BookingMessagePolling] Errore estrazione contesto: {e}",
                            exc_info=True,
                        )
                        # Salta questo messaggio
                        messages_to_confirm.append(message_id)
                        continue
                    
                    # Genera risposta AI e invia (se gemini_service disponibile)
                    if self._gemini_service:
                        try:
                            reply_text = self._gemini_service.generate_reply(context)
                            logger.info(
                                f"[BookingMessagePolling] ✅ Risposta AI generata per messaggio: message_id={message_id}"
                            )
                            
                            # Invia risposta via BookingReplyService
                            try:
                                sent_message_id = self._reply_service.send_reply_with_context(
                                    booking_message=booking_message,
                                    context=context,
                                    reply_text=reply_text,
                                    mark_as_read=True,
                                )
                                logger.info(
                                    f"[BookingMessagePolling] ✅ Risposta inviata con successo: "
                                    f"sent_message_id={sent_message_id}, message_id={message_id}"
                                )
                                replied_count += 1
                            except Exception as e:
                                logger.error(
                                    f"[BookingMessagePolling] ❌ Errore invio risposta: {e}",
                                    exc_info=True,
                                )
                                # Continua comunque (abbiamo generato risposta, ma invio fallito)
                                # Marca comunque come processato per evitare retry infiniti
                        except Exception as e:
                            logger.error(
                                f"[BookingMessagePolling] Errore generazione risposta AI: {e}",
                                exc_info=True,
                            )
                            # Continua comunque a marcare come processato (abbiamo tentato)
                    else:
                        logger.warning(
                            "[BookingMessagePolling] GeminiService non disponibile, "
                            "risposta AI non generata"
                        )
                    
                    # Marca come processato
                    self._processed_repo.mark_processed_api(
                        message_id=message_id,
                        host_id=host_id,
                        source="booking_api",
                    )
                    
                    messages_to_confirm.append(message_id)
                    processed_count += 1
                    
                except Exception as e:
                    logger.error(
                        f"[BookingMessagePolling] Errore processando messaggio: {e}",
                        exc_info=True,
                    )
                    # Continua con gli altri messaggi
            
            if skipped_count > 0:
                logger.warning(
                    f"[BookingMessagePolling] ⚠️ {skipped_count} messaggi saltati "
                    f"(nessun host_id o già processati)"
                )
            
            # Conferma recupero messaggi (se ci sono messaggi processati)
            if messages_to_confirm:
                self._confirm_messages(number_of_messages)
                logger.info(
                    f"[BookingMessagePolling] ✅ Conferma recupero inviata per {len(messages_to_confirm)} messaggi "
                    f"({processed_count} processati, {replied_count} risposte inviate, {skipped_count} saltati)"
                )
            
        except Exception as e:
            logger.error(f"[BookingMessagePolling] Errore polling messaggi: {e}", exc_info=True)
    
    def _confirm_messages(self, number_of_messages: int) -> None:
        """Conferma recupero messaggi dalla coda."""
        try:
            response = self._client.confirm_messages(number_of_messages=number_of_messages)
            logger.debug(f"[BookingMessagePolling] Conferma response: {response}")
        except Exception as e:
            logger.error(f"[BookingMessagePolling] Errore conferma messaggi: {e}", exc_info=True)

