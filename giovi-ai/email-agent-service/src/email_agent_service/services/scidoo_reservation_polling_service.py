"""Polling service per Scidoo API - MULTI-HOST."""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Optional

from firebase_admin import firestore

from ..config.settings import get_settings
from ..models.scidoo_reservation import ScidooReservation
from ..repositories import ScidooIntegrationsRepository, ScidooPropertyMappingsRepository
from ..services.integrations.scidoo_reservation_client import (
    ScidooReservationClient,
    ScidooAPIError,
)
from ..services.persistence_service import PersistenceService

logger = logging.getLogger(__name__)


class ScidooReservationPollingService:
    """
    Service per polling continuo delle prenotazioni Scidoo - MULTI-HOST.
    
    **IMPORTANTE: Questo servizio gestisce TUTTI gli host contemporaneamente.**
    
    - Recupera API key da hosts/{hostId}.scidooApiKey per ogni host
    - Per ogni host con API key valida, crea client separato
    - Polla ogni N secondi (default 30s) per recuperare nuove/modificate prenotazioni
    - Mappa ogni prenotazione al corretto host_id usando room_type_id
    - Il sistema controlla sempre se la prenotazione esiste già (deduplica)
    """
    
    def __init__(
        self,
        persistence_service: PersistenceService,
        firestore_client: firestore.Client,
        polling_interval: Optional[int] = None,
    ) -> None:
        """
        Inizializza polling service MULTI-HOST.
        
        Args:
            persistence_service: Service per salvataggio in Firestore
            firestore_client: Firestore client per repository
            polling_interval: Intervallo polling in secondi (default da settings: 30s)
        """
        self._settings = get_settings()
        self._persistence_service = persistence_service
        self._firestore_client = firestore_client
        self._integrations_repo = ScidooIntegrationsRepository(firestore_client)
        self._mappings_repo = ScidooPropertyMappingsRepository(firestore_client)
        self._polling_interval = polling_interval or self._settings.scidoo_polling_interval
        
        # Cache per client API per host (evita ricreare client ad ogni poll)
        self._client_cache: dict[str, ScidooReservationClient] = {}
        
        # Track last modified per ogni host
        self._last_modified_cache: dict[str, Optional[datetime]] = {}
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        logger.info(
            f"[ScidooReservationPolling] ✅ Initialized MULTI-HOST with interval={self._polling_interval}s"
        )
    
    def start(self) -> None:
        """Avvia polling service MULTI-HOST in background thread."""
        if self._running:
            logger.warning("[ScidooReservationPolling] Service già in esecuzione")
            return
        
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name="ScidooReservationPolling")
        self._thread.start()
        logger.info(
            f"[ScidooReservationPolling] ✅ MULTI-HOST Service avviato "
            f"(interval={self._polling_interval}s, gestisce TUTTI gli host)"
        )
    
    def stop(self) -> None:
        """Ferma polling service."""
        if not self._running:
            return
        
        logger.info("[ScidooReservationPolling] Fermata service...")
        self._running = False
        self._stop_event.set()
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
            if self._thread.is_alive():
                logger.warning("[ScidooReservationPolling] Thread non terminato entro timeout")
        
        logger.info("[ScidooReservationPolling] ✅ Service fermato")
    
    def _poll_loop(self) -> None:
        """Loop principale di polling."""
        logger.info("[ScidooReservationPolling] Polling loop avviato")
        
        while self._running and not self._stop_event.is_set():
            try:
                # Poll nuove/modificate prenotazioni per tutti gli host
                self._poll_all_hosts()
            except Exception as e:
                logger.error(f"[ScidooReservationPolling] Errore durante polling: {e}", exc_info=True)
                # Continua anche in caso di errore (non fermare il loop)
            
            # Attendi prima del prossimo polling
            self._stop_event.wait(timeout=self._polling_interval)
        
        logger.info("[ScidooReservationPolling] Polling loop terminato")
    
    def _poll_all_hosts(self) -> None:
        """
        Poll prenotazioni per tutti gli host con integrazione Scidoo.
        
        Per ogni host:
        1. Recupera API key
        2. Crea/riusa client API
        3. Chiama API con last_modified o modified_from
        4. Processa prenotazioni
        """
        # Recupera tutti gli host con integrazione Scidoo
        hosts_with_integration = self._integrations_repo.get_all_hosts_with_integration()
        
        if not hosts_with_integration:
            logger.debug("[ScidooReservationPolling] Nessun host con integrazione Scidoo configurata")
            return
        
        logger.info(f"[ScidooReservationPolling] Polling per {len(hosts_with_integration)} host")
        
        for host_id, api_key in hosts_with_integration:
            try:
                self._poll_host_reservations(host_id, api_key)
            except Exception as e:
                logger.error(
                    f"[ScidooReservationPolling] Errore polling host {host_id}: {e}",
                    exc_info=True,
                )
                # Continua con altri host anche in caso di errore
    
    def _poll_host_reservations(self, host_id: str, api_key: str) -> None:
        """
        Poll prenotazioni per un singolo host.
        
        Args:
            host_id: ID host
            api_key: API key Scidoo
        """
        # Crea o riusa client API
        client = self._get_or_create_client(host_id, api_key)
        
        # Determina parametri per polling
        last_modified_time = self._last_modified_cache.get(host_id)
        
        if last_modified_time:
            # Usa modified_from per ottenere solo modifiche dall'ultima poll
            modified_from = last_modified_time.strftime("%Y-%m-%d")
            logger.debug(f"[ScidooReservationPolling] Host {host_id}: polling modifiche da {modified_from}")
            reservations = client.get_reservations(modified_from=modified_from)
        else:
            # Prima poll o reset: usa last_modified per ottenere tutte le modifiche recenti
            logger.debug(f"[ScidooReservationPolling] Host {host_id}: prima poll, uso last_modified")
            reservations = client.get_reservations(last_modified=True)
        
        if not reservations:
            logger.debug(f"[ScidooReservationPolling] Host {host_id}: nessuna prenotazione nuova/modificata")
            return
        
        logger.info(
            f"[ScidooReservationPolling] Host {host_id}: trovate {len(reservations)} prenotazioni"
        )
        
        # Processa ogni prenotazione
        processed_count = 0
        skipped_count = 0
        error_count = 0
        
        for reservation in reservations:
            try:
                # Trova host_id usando mapping room_type_id
                mapped_host_id = self._find_host_id_for_room_type(reservation.room_type_id)
                
                if not mapped_host_id:
                    skipped_count += 1
                    logger.warning(
                        f"[ScidooReservationPolling] ⚠️ Salto prenotazione {reservation.internal_id}: "
                        f"nessun mapping per room_type_id={reservation.room_type_id}"
                    )
                    continue
                
                # Se mapped_host_id diverso da host_id corrente, significa che la prenotazione
                # appartiene a un altro host (multi-property account)
                if mapped_host_id != host_id:
                    logger.debug(
                        f"[ScidooReservationPolling] Prenotazione {reservation.internal_id} "
                        f"appartiene a host {mapped_host_id} (non {host_id})"
                    )
                    # Processa comunque con il mapped_host_id corretto
                    target_host_id = mapped_host_id
                else:
                    target_host_id = host_id
                
                # Salva prenotazione (il PersistenceService fa deduplica)
                logger.info(
                    f"[ScidooReservationPolling] Processando prenotazione: {reservation.internal_id}, "
                    f"room_type={reservation.room_type_id}, host={target_host_id}, "
                    f"guest={reservation.customer.email}"
                )
                
                save_result = self._persistence_service.save_scidoo_reservation(
                    reservation, target_host_id
                )
                
                if save_result.get("saved"):
                    processed_count += 1
                    logger.info(
                        f"[ScidooReservationPolling] ✅ Prenotazione salvata: "
                        f"internal_id={reservation.internal_id}, "
                        f"property_id={save_result.get('property_id')}, "
                        f"client_id={save_result.get('client_id')}"
                    )
                elif save_result.get("skipped"):
                    logger.info(
                        f"[ScidooReservationPolling] ⏭️ Prenotazione già esistente (skip): "
                        f"internal_id={reservation.internal_id}"
                    )
                    skipped_count += 1
                else:
                    error_count += 1
                    logger.error(
                        f"[ScidooReservationPolling] ❌ Errore salvataggio prenotazione: "
                        f"{save_result.get('error', 'unknown error')}"
                    )
                
            except Exception as e:
                error_count += 1
                logger.error(
                    f"[ScidooReservationPolling] Errore processando prenotazione {reservation.internal_id}: {e}",
                    exc_info=True,
                )
        
        # Aggiorna last_modified cache
        self._last_modified_cache[host_id] = datetime.now()
        
        logger.info(
            f"[ScidooReservationPolling] Host {host_id}: "
            f"{processed_count} processate, {skipped_count} saltate, {error_count} errori"
        )
    
    def _find_host_id_for_room_type(self, room_type_id: str) -> Optional[str]:
        """
        Trova host_id per un room_type_id Scidoo.
        
        Args:
            room_type_id: Room Type ID Scidoo
            
        Returns:
            host_id se trovato mapping, None altrimenti
        """
        mapping = self._mappings_repo.get_by_room_type_id(room_type_id)
        if mapping:
            return mapping.host_id
        
        # Se non trovato mapping, log warning
        logger.warning(
            f"[ScidooReservationPolling] ⚠️ Nessun mapping trovato per room_type_id={room_type_id}. "
            f"La prenotazione verrà saltata. Creare mapping in Firestore: "
            f"scidooPropertyMappings/{{id}} = {{scidooRoomTypeId: '{room_type_id}', hostId: '...'}}"
        )
        return None
    
    def _get_or_create_client(self, host_id: str, api_key: str) -> ScidooReservationClient:
        """
        Crea o riusa client API per un host.
        
        Args:
            host_id: ID host
            api_key: API key Scidoo
            
        Returns:
            ScidooReservationClient
        """
        if host_id in self._client_cache:
            # Riusa client esistente
            return self._client_cache[host_id]
        
        # Crea nuovo client
        client = ScidooReservationClient(api_key=api_key, mock_mode=False)
        self._client_cache[host_id] = client
        return client

