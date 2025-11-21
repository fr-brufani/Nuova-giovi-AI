"""Polling service per Smoobu API - MULTI-HOST."""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from firebase_admin import firestore

from ..config.settings import get_settings
from ..models.smoobu_reservation import SmoobuReservation
from ..repositories.smoobu_property_mappings import SmoobuPropertyMappingsRepository
from ..repositories.properties import PropertiesRepository
from ..services.persistence_service import PersistenceService
from ..services.integrations.smoobu_client import SmoobuClient

logger = logging.getLogger(__name__)


class SmoobuReservationPollingService:
    """
    Service per polling continuo delle prenotazioni Smoobu - MULTI-HOST.
    
    **IMPORTANTE: Questo servizio gestisce TUTTI gli host contemporaneamente.**
    
    - Ogni host ha la sua API key Smoobu
    - Recupera prenotazioni per TUTTE le properties dell'host
    - Mappa ogni prenotazione al corretto host_id usando smoobu_apartment_id
    - Polla ogni N secondi (default 60s) per recuperare nuove prenotazioni,
      le processa e salva in Firestore
    - Supporta import iniziale massivo
    """
    
    # Collection per salvare le API key degli host
    HOST_API_KEYS_COLLECTION = "smoobuHostApiKeys"

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
            firestore_client: Firestore client per mapping repository
            polling_interval: Intervallo polling in secondi (default da settings: 60s)
        """
        self._settings = get_settings()
        self._persistence_service = persistence_service
        self._firestore_client = firestore_client
        self._mappings_repo = SmoobuPropertyMappingsRepository(firestore_client)
        self._properties_repo = PropertiesRepository(firestore_client)
        self._polling_interval = polling_interval or self._settings.smoobu_polling_interval_reservations
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Mantiene timestamp ultima modifica processata per ogni host
        self._last_modified_timestamps: Dict[str, datetime] = {}
        
        logger.info(
            f"[SmoobuReservationPolling] ✅ Initialized MULTI-HOST with interval={self._polling_interval}s"
        )
    
    def start(self) -> None:
        """Avvia polling service MULTI-HOST in background thread."""
        if self._running:
            logger.warning("[SmoobuReservationPolling] Service già in esecuzione")
            return
        
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name="SmoobuReservationPolling")
        self._thread.start()
        logger.info(
            f"[SmoobuReservationPolling] ✅ MULTI-HOST Service avviato "
            f"(interval={self._polling_interval}s, gestisce TUTTI gli host)"
        )
    
    def stop(self) -> None:
        """Ferma polling service."""
        if not self._running:
            return
        
        logger.info("[SmoobuReservationPolling] Fermata service...")
        self._running = False
        self._stop_event.set()
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
            if self._thread.is_alive():
                logger.warning("[SmoobuReservationPolling] Thread non terminato entro timeout")
        
        logger.info("[SmoobuReservationPolling] ✅ Service fermato")
    
    def _poll_loop(self) -> None:
        """Loop principale di polling."""
        logger.info("[SmoobuReservationPolling] Polling loop avviato")
        
        while self._running and not self._stop_event.is_set():
            try:
                # Poll prenotazioni modificate per tutti gli host configurati
                self._poll_all_hosts_reservations()
                
            except Exception as e:
                logger.error(f"[SmoobuReservationPolling] Errore durante polling: {e}", exc_info=True)
                # Continua anche in caso di errore (non fermare il loop)
            
            # Attendi prima del prossimo polling
            self._stop_event.wait(timeout=self._polling_interval)
        
        logger.info("[SmoobuReservationPolling] Polling loop terminato")
    
    def _get_hosts_with_api_keys(self) -> List[Dict[str, Any]]:
        """
        Recupera tutti gli host con API key Smoobu configurata.
        
        Returns:
            Lista di dict con hostId e apiKey
        """
        try:
            docs = self._firestore_client.collection(self.HOST_API_KEYS_COLLECTION).get()
            hosts = []
            for doc in docs:
                data = doc.to_dict() or {}
                if data.get("apiKey") and data.get("hostId"):
                    hosts.append({
                        "hostId": data["hostId"],
                        "apiKey": data["apiKey"],
                        "enabled": data.get("enabled", True),
                    })
            return hosts
        except Exception as e:
            logger.error(f"[SmoobuReservationPolling] Errore recupero host con API key: {e}")
            return []
    
    def _poll_all_hosts_reservations(self) -> None:
        """
        Poll prenotazioni modificate per tutti gli host configurati.
        """
        hosts = self._get_hosts_with_api_keys()
        
        if not hosts:
            logger.debug("[SmoobuReservationPolling] Nessun host con API key Smoobu configurata")
            return
        
        logger.info(f"[SmoobuReservationPolling] Polling per {len(hosts)} host configurati")
        
        for host_config in hosts:
            if not host_config.get("enabled", True):
                continue
                
            host_id = host_config["hostId"]
            api_key = host_config["apiKey"]
            
            try:
                self._poll_host_reservations(host_id, api_key)
            except Exception as e:
                logger.error(
                    f"[SmoobuReservationPolling] Errore polling host {host_id}: {e}",
                    exc_info=True,
                )
                # Continua con gli altri host
    
    def _poll_host_reservations(self, host_id: str, api_key: str) -> None:
        """
        Poll prenotazioni modificate per un host specifico.
        
        Args:
            host_id: ID host
            api_key: API key Smoobu
        """
        try:
            client = SmoobuClient(api_key=api_key, mock_mode=False)
            
            # Usa modifiedFrom per ottenere solo prenotazioni modificate
            last_modified = self._last_modified_timestamps.get(host_id)
            if last_modified:
                modified_from = last_modified.strftime("%Y-%m-%d")
            else:
                # Prima volta: ultimi 7 giorni
                modified_from = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            
            modified_to = datetime.now().strftime("%Y-%m-%d")
            
            logger.info(
                f"[SmoobuReservationPolling] Polling prenotazioni modificate per host {host_id} "
                f"(from {modified_from} to {modified_to})"
            )
            
            # Recupera tutte le pagine
            page = 1
            total_processed = 0
            total_updated = 0
            total_cancelled = 0
            
            while True:
                response = client.get_reservations(
                    modified_from=modified_from,
                    modified_to=modified_to,
                    page=page,
                    page_size=100,
                    exclude_blocked=True,
                )
                
                bookings = response.get("bookings", [])
                if not bookings:
                    break
                
                logger.info(
                    f"[SmoobuReservationPolling] Trovate {len(bookings)} prenotazioni "
                    f"(page {page}/{response.get('page_count', 1)})"
                )
                
                for booking_data in bookings:
                    try:
                        reservation = client.parse_reservation(booking_data)
                        
                        # Trova host_id usando mapping
                        mapped_host_id = self._find_host_id_for_apartment(reservation.apartment_id, host_id)
                        
                        if not mapped_host_id:
                            logger.warning(
                                f"[SmoobuReservationPolling] ⚠️ Nessun mapping per apartment_id={reservation.apartment_id}, "
                                f"usa host_id originale={host_id}"
                            )
                            mapped_host_id = host_id
                        
                        # Processa in base al type
                        if reservation.type == "cancellation":
                            cancel_result = self._persistence_service.cancel_smoobu_reservation(
                                reservation_id=reservation.reservation_id,
                                host_id=mapped_host_id,
                            )
                            if cancel_result.get("cancelled"):
                                total_cancelled += 1
                        elif reservation.type == "modification":
                            update_result = self._persistence_service.update_smoobu_reservation(
                                reservation=reservation,
                                host_id=mapped_host_id,
                            )
                            if update_result.get("updated"):
                                total_updated += 1
                        else:  # reservation (nuova)
                            save_result = self._persistence_service.save_smoobu_reservation(
                                reservation=reservation,
                                host_id=mapped_host_id,
                            )
                            if save_result.get("saved"):
                                total_updated += 1
                        
                        total_processed += 1
                        
                        # Aggiorna timestamp ultima modifica
                        if reservation.modified_at:
                            current_timestamp = self._last_modified_timestamps.get(host_id)
                            if not current_timestamp or reservation.modified_at > current_timestamp:
                                self._last_modified_timestamps[host_id] = reservation.modified_at
                        
                    except Exception as e:
                        logger.error(
                            f"[SmoobuReservationPolling] Errore processando prenotazione: {e}",
                            exc_info=True,
                        )
                        continue
                
                # Controlla se ci sono altre pagine
                page_count = response.get("page_count", 1)
                if page >= page_count:
                    break
                page += 1
            
            if total_processed > 0:
                logger.info(
                    f"[SmoobuReservationPolling] ✅ Host {host_id}: "
                    f"{total_processed} prenotazioni processate "
                    f"({total_updated} aggiornate, {total_cancelled} cancellate)"
                )
            
        except Exception as e:
            logger.error(
                f"[SmoobuReservationPolling] Errore polling host {host_id}: {e}",
                exc_info=True,
            )
    
    def _find_host_id_for_apartment(self, apartment_id: Optional[int], fallback_host_id: str) -> Optional[str]:
        """
        Trova host_id per un apartment_id Smoobu.
        
        Args:
            apartment_id: Apartment ID Smoobu
            fallback_host_id: Host ID da usare se non trovato mapping
            
        Returns:
            host_id se trovato mapping, fallback_host_id altrimenti
        """
        if not apartment_id:
            return fallback_host_id
        
        mapping = self._mappings_repo.get_by_smoobu_apartment_id(apartment_id)
        if mapping:
            return mapping.host_id
        
        # Se non trovato mapping, usa fallback (l'host che ha fatto la richiesta)
        return fallback_host_id
    
    def import_all_reservations(
        self,
        host_id: str,
        api_key: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Import iniziale massivo di tutte le prenotazioni per un host.
        
        Args:
            host_id: ID host
            api_key: API key Smoobu
            from_date: Data inizio import (default: 6 mesi fa)
            to_date: Data fine import (default: oggi)
            
        Returns:
            dict con statistiche import
        """
        logger.info(
            f"[SmoobuReservationPolling] 🚀 Import massivo prenotazioni per host {host_id}"
        )
        
        if not from_date:
            from_date = datetime.now() - timedelta(days=180)  # 6 mesi
        if not to_date:
            to_date = datetime.now()
        
        stats = {
            "total_processed": 0,
            "total_saved": 0,
            "total_skipped": 0,
            "total_errors": 0,
            "properties_imported": 0,
            "clients_imported": 0,
            "apartments": [],
        }
        
        try:
            client = SmoobuClient(api_key=api_key, mock_mode=False)
            
            # 1. Recupera e salva tutte le properties
            logger.info(f"[SmoobuReservationPolling] Recupero apartments per host {host_id}")
            apartments = client.get_apartments()
            
            for apt_data in apartments:
                try:
                    apartment = client.parse_apartment(apt_data)
                    
                    # Crea mapping
                    mapping = self._mappings_repo.get_by_smoobu_apartment_id(apartment.id)
                    if not mapping:
                        # Crea property e mapping
                        property_id, property_created = self._properties_repo.find_or_create_by_name(
                            host_id=host_id,
                            property_name=apartment.name,
                            imported_from="smoobu_api",
                        )
                        
                        self._mappings_repo.create_mapping(
                            smoobu_apartment_id=apartment.id,
                            host_id=host_id,
                            internal_property_id=property_id,
                            property_name=apartment.name,
                        )
                        
                        if property_created:
                            stats["properties_imported"] += 1
                        
                        stats["apartments"].append({
                            "smoobu_id": apartment.id,
                            "name": apartment.name,
                            "property_id": property_id,
                        })
                    else:
                        stats["apartments"].append({
                            "smoobu_id": apartment.id,
                            "name": apartment.name,
                            "property_id": mapping.internal_property_id,
                        })
                except Exception as e:
                    logger.error(f"Errore import apartment {apt_data.get('id')}: {e}")
                    stats["total_errors"] += 1
            
            logger.info(f"[SmoobuReservationPolling] Importate {len(stats['apartments'])} apartments")
            
            # 2. Recupera tutte le prenotazioni nel range
            from_str = from_date.strftime("%Y-%m-%d")
            to_str = to_date.strftime("%Y-%m-%d")
            
            logger.info(
                f"[SmoobuReservationPolling] Recupero prenotazioni dal {from_str} al {to_str}"
            )
            
            page = 1
            while True:
                response = client.get_reservations(
                    from_date=from_str,
                    to_date=to_str,
                    page=page,
                    page_size=100,
                    exclude_blocked=True,
                )
                
                bookings = response.get("bookings", [])
                if not bookings:
                    break
                
                logger.info(
                    f"[SmoobuReservationPolling] Processando pagina {page}/{response.get('page_count', 1)} "
                    f"({len(bookings)} prenotazioni)"
                )
                
                for booking_data in bookings:
                    try:
                        reservation = client.parse_reservation(booking_data)
                        
                        # Salva prenotazione (upsert gestisce già deduplica)
                        save_result = self._persistence_service.save_smoobu_reservation(
                            reservation=reservation,
                            host_id=host_id,
                        )
                        
                        stats["total_processed"] += 1
                        
                        if save_result.get("saved"):
                            stats["total_saved"] += 1
                            if save_result.get("client_created"):
                                stats["clients_imported"] += 1
                        elif save_result.get("skipped"):
                            stats["total_skipped"] += 1
                        else:
                            stats["total_errors"] += 1
                            logger.warning(
                                f"Errore salvataggio prenotazione {reservation.reservation_id}: "
                                f"{save_result.get('error', 'unknown')}"
                            )
                        
                    except Exception as e:
                        logger.error(
                            f"Errore processando prenotazione: {e}",
                            exc_info=True,
                        )
                        stats["total_errors"] += 1
                
                # Controlla se ci sono altre pagine
                page_count = response.get("page_count", 1)
                if page >= page_count:
                    break
                page += 1
            
            # Aggiorna timestamp ultima modifica
            self._last_modified_timestamps[host_id] = datetime.now()
            
            logger.info(
                f"[SmoobuReservationPolling] ✅ Import massivo completato per host {host_id}: "
                f"{stats['total_processed']} processate, {stats['total_saved']} salvate, "
                f"{stats['total_skipped']} saltate, {stats['total_errors']} errori"
            )
            
        except Exception as e:
            logger.error(
                f"[SmoobuReservationPolling] ❌ Errore durante import massivo: {e}",
                exc_info=True,
            )
            stats["error"] = str(e)
        
        return stats
    
    def save_host_api_key(self, host_id: str, api_key: str, enabled: bool = True) -> None:
        """
        Salva API key Smoobu per un host.
        
        Args:
            host_id: ID host
            api_key: API key Smoobu
            enabled: Se True, abilita polling per questo host
        """
        doc_ref = self._firestore_client.collection(self.HOST_API_KEYS_COLLECTION).document(host_id)
        doc_ref.set({
            "hostId": host_id,
            "apiKey": api_key,
            "enabled": enabled,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        }, merge=True)
        logger.info(f"[SmoobuReservationPolling] API key salvata per host {host_id}")
    
    def remove_host_api_key(self, host_id: str) -> None:
        """
        Rimuove API key Smoobu per un host.
        
        Args:
            host_id: ID host
        """
        doc_ref = self._firestore_client.collection(self.HOST_API_KEYS_COLLECTION).document(host_id)
        doc_ref.delete()
        logger.info(f"[SmoobuReservationPolling] API key rimossa per host {host_id}")

