"""Polling service per Booking.com Reservation API - MULTI-HOST."""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

from firebase_admin import firestore

from ..config.settings import get_settings
from ..models.booking_reservation import BookingReservation
from ..parsers.booking_reservation_parser import parse_ota_modify_xml, parse_ota_xml
from ..repositories.booking_property_mappings import BookingPropertyMappingsRepository
from ..services.persistence_service import PersistenceService
from ..services.integrations.booking_reservation_client import BookingReservationClient

logger = logging.getLogger(__name__)


class BookingReservationPollingService:
    """
    Service per polling continuo delle prenotazioni Booking.com - MULTI-HOST.
    
    **IMPORTANTE: Questo servizio gestisce TUTTI gli host contemporaneamente.**
    
    - Usa UN SOLO set di credenziali Booking.com (Machine Account condiviso)
    - Recupera prenotazioni per TUTTE le properties del provider
    - Mappa ogni prenotazione al corretto host_id usando booking_property_id
    - Polla ogni N secondi (default 20s) per recuperare nuove prenotazioni,
      le processa e salva in Firestore, poi invia acknowledgement.
    """

    def __init__(
        self,
        reservation_client: BookingReservationClient,
        persistence_service: PersistenceService,
        firestore_client: firestore.Client,
        polling_interval: Optional[int] = None,
    ) -> None:
        """
        Inizializza polling service MULTI-HOST.
        
        Args:
            reservation_client: Client Reservation API (condiviso per tutti gli host)
            persistence_service: Service per salvataggio in Firestore
            firestore_client: Firestore client per mapping repository
            polling_interval: Intervallo polling in secondi (default da settings: 20s)
        """
        self._settings = get_settings()
        self._client = reservation_client
        self._persistence_service = persistence_service
        self._firestore_client = firestore_client
        self._mappings_repo = BookingPropertyMappingsRepository(firestore_client)
        self._polling_interval = polling_interval or self._settings.booking_polling_interval_reservations
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        logger.info(
            f"[BookingReservationPolling] ✅ Initialized MULTI-HOST with interval={self._polling_interval}s, "
            f"mock_mode={reservation_client.mock_mode}"
        )
    
    def start(self) -> None:
        """Avvia polling service MULTI-HOST in background thread."""
        if self._running:
            logger.warning("[BookingReservationPolling] Service già in esecuzione")
            return
        
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name="BookingReservationPolling")
        self._thread.start()
        logger.info(
            f"[BookingReservationPolling] ✅ MULTI-HOST Service avviato "
            f"(interval={self._polling_interval}s, gestisce TUTTI gli host)"
        )
    
    def stop(self) -> None:
        """Ferma polling service."""
        if not self._running:
            return
        
        logger.info("[BookingReservationPolling] Fermata service...")
        self._running = False
        self._stop_event.set()
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
            if self._thread.is_alive():
                logger.warning("[BookingReservationPolling] Thread non terminato entro timeout")
        
        logger.info("[BookingReservationPolling] ✅ Service fermato")
    
    def _poll_loop(self) -> None:
        """Loop principale di polling."""
        logger.info("[BookingReservationPolling] Polling loop avviato")
        
        while self._running and not self._stop_event.is_set():
            try:
                # Poll nuove prenotazioni
                self._poll_new_reservations()
                
                # Poll prenotazioni modificate/cancellate
                self._poll_modified_reservations()
                
            except Exception as e:
                logger.error(f"[BookingReservationPolling] Errore durante polling: {e}", exc_info=True)
                # Continua anche in caso di errore (non fermare il loop)
            
            # Attendi prima del prossimo polling
            self._stop_event.wait(timeout=self._polling_interval)
        
        logger.info("[BookingReservationPolling] Polling loop terminato")
    
    def _find_host_id_for_property(self, booking_property_id: str) -> Optional[str]:
        """
        Trova host_id per un property_id Booking.com.
        
        Args:
            booking_property_id: Property ID Booking.com
            
        Returns:
            host_id se trovato mapping, None altrimenti
        """
        mapping = self._mappings_repo.get_by_booking_property_id(booking_property_id)
        if mapping:
            return mapping.host_id
        
        # Se non trovato mapping, log warning (la prenotazione verrà saltata)
        logger.warning(
            f"[BookingReservationPolling] ⚠️ Nessun mapping trovato per booking_property_id={booking_property_id}. "
            f"La prenotazione verrà saltata. Creare mapping in Firestore: "
            f"bookingPropertyMappings/{{id}} = {{bookingPropertyId: '{booking_property_id}', hostId: '...'}}"
        )
        return None
    
    def _poll_new_reservations(self) -> None:
        """
        Poll nuove prenotazioni e processa - MULTI-HOST.
        
        Per ogni prenotazione:
        1. Trova host_id usando mapping booking_property_id → host_id
        2. Salva in Firestore con il corretto host_id
        """
        try:
            # GET nuove prenotazioni (recupera TUTTE le prenotazioni del provider)
            xml_response = self._client.get_new_reservations()
            
            if not xml_response or not xml_response.strip():
                # Nessuna prenotazione nuova
                return
            
            # Parse XML
            reservations = parse_ota_xml(xml_response)
            
            if not reservations:
                logger.debug("[BookingReservationPolling] Nessuna prenotazione valida nell'XML")
                return
            
            logger.info(f"[BookingReservationPolling] Trovate {len(reservations)} nuove prenotazioni")
            
            # Processa ogni prenotazione (ogni prenotazione può appartenere a host diversi)
            reservation_ids_to_ack = []
            skipped_count = 0
            
            for reservation in reservations:
                try:
                    # Trova host_id usando mapping
                    host_id = self._find_host_id_for_property(reservation.property_id)
                    
                    if not host_id:
                        skipped_count += 1
                        logger.warning(
                            f"[BookingReservationPolling] ⚠️ Salto prenotazione {reservation.reservation_id}: "
                            f"nessun mapping per property_id={reservation.property_id}"
                        )
                        continue
                    
                    # Salva in Firestore con il corretto host_id
                    logger.info(
                        f"[BookingReservationPolling] Processando prenotazione: {reservation.reservation_id}, "
                        f"property={reservation.property_id}, host={host_id}, guest={reservation.guest_info.email}"
                    )
                    
                    # Salva prenotazione
                    save_result = self._persistence_service.save_booking_reservation(reservation, host_id)
                    
                    if save_result.get("saved"):
                        logger.info(
                            f"[BookingReservationPolling] ✅ Prenotazione salvata: "
                            f"reservation_id={reservation.reservation_id}, "
                            f"property_id={save_result.get('property_id')}, "
                            f"client_id={save_result.get('client_id')}"
                        )
                    else:
                        logger.error(
                            f"[BookingReservationPolling] ❌ Errore salvataggio prenotazione: "
                            f"{save_result.get('error', 'unknown error')}"
                        )
                        # Non facciamo acknowledgement se errore salvataggio
                        continue
                    
                    reservation_ids_to_ack.append(reservation.reservation_id)
                    
                except Exception as e:
                    logger.error(
                        f"[BookingReservationPolling] Errore processando prenotazione {reservation.reservation_id}: {e}",
                        exc_info=True,
                    )
                    # Continua con le altre prenotazioni
            
            if skipped_count > 0:
                logger.warning(
                    f"[BookingReservationPolling] ⚠️ {skipped_count} prenotazioni saltate per mancanza di mapping"
                )
            
            # Acknowledgement (se ci sono prenotazioni processate)
            if reservation_ids_to_ack:
                self._acknowledge_reservations(xml_response)
                logger.info(
                    f"[BookingReservationPolling] ✅ Acknowledgement inviato per {len(reservation_ids_to_ack)} prenotazioni "
                    f"({skipped_count} saltate)"
                )
            
        except Exception as e:
            logger.error(f"[BookingReservationPolling] Errore polling nuove prenotazioni: {e}", exc_info=True)
    
    def _poll_modified_reservations(self) -> None:
        """
        Poll prenotazioni modificate/cancellate e processa - MULTI-HOST.
        
        Per ogni prenotazione:
        1. Trova host_id usando mapping booking_property_id → host_id
        2. Verifica se reservation esiste già in Firestore
        3. Se esiste: aggiorna (è modifica)
        4. Se non esiste ma ha dati validi: crea nuova (modifica di prenotazione non ancora importata)
        5. Se non ha dati validi: considera cancellazione (salta se non esiste)
        """
        try:
            # GET prenotazioni modificate/cancellate
            xml_response = self._client.get_modified_reservations()
            
            if not xml_response or not xml_response.strip():
                # Nessuna modifica
                return
            
            # Parse XML (formato HotelResModifyNotif)
            reservations = parse_ota_modify_xml(xml_response)
            
            if not reservations:
                logger.debug("[BookingReservationPolling] Nessuna prenotazione modificata valida nell'XML")
                return
            
            logger.info(f"[BookingReservationPolling] Trovate {len(reservations)} prenotazioni modificate/cancellate")
            
            # Processa ogni prenotazione modificata
            reservation_ids_to_ack = []
            skipped_count = 0
            updated_count = 0
            cancelled_count = 0
            
            for reservation in reservations:
                try:
                    # Trova host_id usando mapping
                    host_id = self._find_host_id_for_property(reservation.property_id)
                    
                    if not host_id:
                        skipped_count += 1
                        logger.warning(
                            f"[BookingReservationPolling] ⚠️ Salto prenotazione modificata {reservation.reservation_id}: "
                            f"nessun mapping per property_id={reservation.property_id}"
                        )
                        continue
                    
                    # Verifica se reservation esiste già in Firestore
                    # Questo ci dice se è modifica (esiste) o cancellazione (non esiste o dati invalidi)
                    reservations_ref = self._firestore_client.collection("reservations")
                    query = (
                        reservations_ref
                        .where("reservationId", "==", reservation.reservation_id)
                        .where("hostId", "==", host_id)
                        .limit(1)
                    )
                    existing_docs = list(query.get())
                    existing_reservation = existing_docs[0] if existing_docs else None
                    
                    if existing_reservation:
                        existing_data = existing_reservation.to_dict() or {}
                        existing_status = existing_data.get("status", "confirmed")
                        
                        # Se già cancellata, salta
                        if existing_status == "cancelled":
                            logger.info(
                                f"[BookingReservationPolling] Prenotazione {reservation.reservation_id} "
                                f"già cancellata, salto"
                            )
                            reservation_ids_to_ack.append(reservation.reservation_id)
                            continue
                        
                        # Verifica se è cancellazione (controlla se XML ha dati validi)
                        # Se check_in/check_out sono None o dati invalidi, potrebbe essere cancellazione
                        is_cancellation = not reservation.check_in or not reservation.check_out
                        
                        if is_cancellation:
                            # Cancellazione
                            logger.info(
                                f"[BookingReservationPolling] Cancellazione prenotazione: "
                                f"reservation_id={reservation.reservation_id}, host={host_id}"
                            )
                            cancel_result = self._persistence_service.cancel_booking_reservation(
                                reservation_id=reservation.reservation_id,
                                host_id=host_id,
                            )
                            if cancel_result.get("cancelled"):
                                cancelled_count += 1
                                logger.info(
                                    f"[BookingReservationPolling] ✅ Prenotazione cancellata: "
                                    f"{reservation.reservation_id}"
                                )
                            else:
                                logger.warning(
                                    f"[BookingReservationPolling] ⚠️ Prenotazione non trovata per cancellazione: "
                                    f"{reservation.reservation_id}"
                                )
                        else:
                            # Modifica
                            logger.info(
                                f"[BookingReservationPolling] Modifica prenotazione: "
                                f"reservation_id={reservation.reservation_id}, host={host_id}"
                            )
                            update_result = self._persistence_service.update_booking_reservation(
                                reservation=reservation,
                                host_id=host_id,
                            )
                            if update_result.get("updated"):
                                updated_count += 1
                                logger.info(
                                    f"[BookingReservationPolling] ✅ Prenotazione aggiornata: "
                                    f"{reservation.reservation_id}"
                                )
                            else:
                                logger.warning(
                                    f"[BookingReservationPolling] ⚠️ Errore aggiornamento prenotazione: "
                                    f"{reservation.reservation_id}: {update_result.get('error', 'unknown')}"
                                )
                                # Non facciamo acknowledgement se errore
                                continue
                    else:
                        # Reservation non esiste in Firestore
                        # Potrebbe essere:
                        # 1. Modifica di prenotazione non ancora importata (crea nuova)
                        # 2. Cancellazione di prenotazione mai importata (salta)
                        
                        # Se ha dati validi, trattiamo come modifica (crea nuova)
                        if reservation.check_in and reservation.check_out:
                            logger.info(
                                f"[BookingReservationPolling] Modifica di prenotazione non ancora importata: "
                                f"creazione nuova reservation_id={reservation.reservation_id}, host={host_id}"
                            )
                            save_result = self._persistence_service.save_booking_reservation(reservation, host_id)
                            if save_result.get("saved"):
                                updated_count += 1
                                logger.info(
                                    f"[BookingReservationPolling] ✅ Nuova prenotazione creata da modifica: "
                                    f"{reservation.reservation_id}"
                                )
                            else:
                                logger.error(
                                    f"[BookingReservationPolling] ❌ Errore creazione prenotazione da modifica: "
                                    f"{reservation.reservation_id}: {save_result.get('error', 'unknown')}"
                                )
                                continue
                        else:
                            # Dati invalidi, probabilmente cancellazione di prenotazione mai importata
                            logger.info(
                                f"[BookingReservationPolling] Cancellazione di prenotazione non importata: "
                                f"reservation_id={reservation.reservation_id}, salto"
                            )
                            # Non facciamo nulla, ma facciamo acknowledgement
                    
                    reservation_ids_to_ack.append(reservation.reservation_id)
                    
                except Exception as e:
                    logger.error(
                        f"[BookingReservationPolling] Errore processando prenotazione modificata "
                        f"{reservation.reservation_id}: {e}",
                        exc_info=True,
                    )
                    # Continua con le altre prenotazioni
            
            if skipped_count > 0:
                logger.warning(
                    f"[BookingReservationPolling] ⚠️ {skipped_count} prenotazioni modificate saltate "
                    f"per mancanza di mapping"
                )
            
            # Acknowledgement (se ci sono prenotazioni processate)
            if reservation_ids_to_ack:
                self._acknowledge_modified_reservations(xml_response)
                logger.info(
                    f"[BookingReservationPolling] ✅ Acknowledgement modifiche inviato per "
                    f"{len(reservation_ids_to_ack)} prenotazioni "
                    f"({updated_count} aggiornate, {cancelled_count} cancellate, {skipped_count} saltate)"
                )
            
        except Exception as e:
            logger.error(
                f"[BookingReservationPolling] Errore polling prenotazioni modificate: {e}",
                exc_info=True,
            )
    
    def _acknowledge_reservations(self, reservations_xml: str) -> None:
        """Invia acknowledgement per nuove prenotazioni."""
        try:
            # Attesa 5 secondi come raccomandato Booking.com
            time.sleep(5)
            
            # POST acknowledgement
            response = self._client.acknowledge_new_reservations(reservations_xml)
            logger.debug(f"[BookingReservationPolling] Acknowledgement response: {response[:200]}")
            
        except Exception as e:
            logger.error(f"[BookingReservationPolling] Errore invio acknowledgement: {e}", exc_info=True)
    
    def _acknowledge_modified_reservations(self, reservations_xml: str) -> None:
        """Invia acknowledgement per prenotazioni modificate."""
        try:
            # Attesa 5 secondi come raccomandato Booking.com
            time.sleep(5)
            
            # POST acknowledgement
            response = self._client.acknowledge_modified_reservations(reservations_xml)
            logger.debug(f"[BookingReservationPolling] Acknowledgement modifiche response: {response[:200]}")
            
        except Exception as e:
            logger.error(f"[BookingReservationPolling] Errore invio acknowledgement modifiche: {e}", exc_info=True)

