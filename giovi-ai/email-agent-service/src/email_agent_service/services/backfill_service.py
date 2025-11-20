from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from ..models import (
    GmailBackfillPreviewResponse,
    ParsedEmail,
    PropertyPreview,
    ReservationPreview,
)
from ..parsers import EmailParsingEngine
from ..parsers.engine import decode_gmail_raw
from ..repositories import HostEmailIntegrationRepository, PropertiesRepository
from ..repositories.host_email_integrations import HostEmailIntegrationRecord
from ..repositories.processed_messages import ProcessedMessageRepository
from .gmail_service import GmailService
from .persistence_service import PersistenceService

logger = logging.getLogger(__name__)


class GmailBackfillService:
    def __init__(
        self,
        *,
        gmail_service: GmailService,
        integration_repository: HostEmailIntegrationRepository,
        processed_repository: ProcessedMessageRepository,
        parsing_engine: EmailParsingEngine,
        persistence_service: PersistenceService,
        lookback_days: int = 180,
    ) -> None:
        self._gmail_service = gmail_service
        self._integration_repository = integration_repository
        self._processed_repository = processed_repository
        self._engine = parsing_engine
        self._persistence_service = persistence_service
        self._lookback_days = lookback_days

    def run_backfill(self, host_id: str, email: str, force: bool = False, firestore_client=None) -> List[ParsedEmail]:
        all_parsed, skipped_count = self._fetch_parsed_items(
            host_id=host_id,
            email=email,
            force=force,
            firestore_client=firestore_client,
        )

        # Separare conferme e cancellazioni
        confirmations: List[tuple[str, ParsedEmail, dict]] = []
        cancellations: List[tuple[str, ParsedEmail, dict]] = []
        other: List[tuple[str, ParsedEmail, dict]] = []

        for message_id, parsed, payload in all_parsed:
            if parsed.kind in ["scidoo_confirmation", "airbnb_confirmation"]:
                confirmations.append((message_id, parsed, payload))
            elif parsed.kind in ["scidoo_cancellation", "airbnb_cancellation"]:
                cancellations.append((message_id, parsed, payload))
            else:
                other.append((message_id, parsed, payload))

        logger.info(f"[BACKFILL] Email separate: {len(confirmations)} conferme, {len(cancellations)} cancellazioni, {len(other)} altre")

        parsed_results: List[ParsedEmail] = []
        scidoo_count = 0
        unhandled_count = 0

        # FASE 2: Processa PRIMA tutte le conferme
        logger.info(f"[BACKFILL] FASE 2: Processamento {len(confirmations)} email di CONFERMA...")
        for message_id, parsed, payload in confirmations:
            scidoo_count += 1
            logger.info(f"[BACKFILL] Email conferma trovata! Reservation ID: {parsed.reservation.reservation_id if parsed.reservation else 'N/A'}, Property: {parsed.reservation.property_name if parsed.reservation else 'N/A'}")
            try:
                save_result = self._persistence_service.save_parsed_email(
                    parsed_email=parsed, host_id=host_id
                )
                if save_result.get("saved"):
                    logger.info(f"[BACKFILL] ✅ Salvato: property_id={save_result.get('property_id')}, client_id={save_result.get('client_id')}, reservation_saved={save_result.get('reservation_saved')}")
                else:
                    logger.warning(f"[BACKFILL] ❌ Salvataggio fallito: {save_result.get('reason')}, error={save_result.get('error')}")
                
                # Se la conferma contiene un messaggio del guest, processalo
                if parsed.guest_message:
                    logger.info(f"[BACKFILL] 📧 Conferma contiene messaggio guest, processamento...")
                    try:
                        from ..services.guest_message_pipeline import GuestMessagePipelineService
                        
                        # Usa il firestore_client passato come parametro
                        if firestore_client:
                            pipeline_service = GuestMessagePipelineService(firestore_client)
                        
                        # Verifica se deve essere processato (è un messaggio da nuova prenotazione)
                        should_process, client_id = pipeline_service.should_process_message(parsed, host_id, is_new_reservation=True)
                        if should_process and client_id:
                            # Estrai contesto
                            context = pipeline_service.extract_context(parsed, host_id, client_id)
                            if context:
                                # Salva messaggio in conversazione
                                pipeline_service.save_guest_message(context, parsed, message_id)
                                logger.info(f"[BACKFILL] ✅ Messaggio guest salvato in conversazione per client_id={client_id}")
                            else:
                                logger.warning(f"[BACKFILL] ⚠️ Contesto non trovato per messaggio guest")
                        else:
                            logger.info(f"[BACKFILL] ℹ️ Messaggio guest non processato (autoReplyEnabled={should_process}, client_id={client_id})")
                    except Exception as e:
                        logger.error(f"[BACKFILL] ❌ Errore processamento messaggio guest: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"[BACKFILL] ❌ Errore salvataggio email {message_id}: {e}", exc_info=True)
            
            parsed_results.append(parsed)
            self._processed_repository.mark_processed(
                email,
                message_id,
                history_id=payload.get("historyId"),
            )

        # FASE 3: Processa POI tutte le cancellazioni
        logger.info(f"[BACKFILL] FASE 3: Processamento {len(cancellations)} email di CANCELLAZIONE...")
        for message_id, parsed, payload in cancellations:
            scidoo_count += 1
            voucher_id = parsed.reservation.voucher_id if parsed.reservation else None
            logger.info(f"[BACKFILL] Email Scidoo cancellazione trovata! Voucher ID: {voucher_id}")
            try:
                save_result = self._persistence_service.save_parsed_email(
                    parsed_email=parsed, host_id=host_id
                )
                if save_result.get("saved") and save_result.get("cancelled"):
                    logger.info(f"[BACKFILL] ✅ Prenotazione cancellata: voucher_id={save_result.get('voucher_id')}")
                else:
                    logger.warning(f"[BACKFILL] ⚠️ Cancellazione fallita: {save_result.get('reason')}, voucher_id={save_result.get('voucher_id')}")
            except Exception as e:
                logger.error(f"[BACKFILL] ❌ Errore cancellazione email {message_id}: {e}", exc_info=True)
            
            parsed_results.append(parsed)
            self._processed_repository.mark_processed(
                email,
                message_id,
                history_id=payload.get("historyId"),
            )

        # FASE 4: Processa altre email (non Scidoo)
        logger.info(f"[BACKFILL] FASE 4: Processamento {len(other)} altre email...")
        for message_id, parsed, payload in other:
            if parsed.kind == "unhandled":
                unhandled_count += 1
                logger.debug(f"[BACKFILL] Email non gestita: {message_id}, sender={parsed.metadata.sender}, subject={parsed.metadata.subject}")
            
            parsed_results.append(parsed)
            self._processed_repository.mark_processed(
                email,
                message_id,
                history_id=payload.get("historyId"),
            )

        logger.info(f"[BACKFILL] ✅ Backfill completato: {len(parsed_results)} email processate, {len(confirmations)} conferme, {len(cancellations)} cancellazioni, {unhandled_count} unhandled, {skipped_count} già processate (skip)")
        return parsed_results

    def run_preview(
        self,
        host_id: str,
        email: str,
        force: bool = False,
        firestore_client=None,
    ) -> GmailBackfillPreviewResponse:
        all_parsed, _ = self._fetch_parsed_items(
            host_id=host_id,
            email=email,
            force=force,
            firestore_client=firestore_client,
        )

        properties_summary: dict[str, dict] = {}
        reservations_preview: list[ReservationPreview] = []

        for _, parsed, _ in all_parsed:
            reservation = parsed.reservation
            property_name = reservation.property_name if reservation else None
            reservation_id = reservation.reservation_id if reservation else None

            if property_name:
                entry = properties_summary.setdefault(
                    property_name,
                    {"count": 0, "reservation_ids": []},
                )
                entry["count"] += 1
                if reservation_id:
                    entry["reservation_ids"].append(reservation_id)

            reservations_preview.append(
                ReservationPreview(
                    reservationId=reservation_id,
                    propertyName=property_name,
                    guestName=reservation.guest_name if reservation else None,
                    checkIn=reservation.check_in if reservation else None,
                    checkOut=reservation.check_out if reservation else None,
                    kind=parsed.kind,
                )
            )

        matched_ids_map: dict[str, list[str]] = {}
        if firestore_client and properties_summary:
            properties_repo = PropertiesRepository(firestore_client)
            for name in properties_summary.keys():
                existing = properties_repo.list_by_name(host_id, name)
                matched_ids_map[name] = [item["id"] for item in existing]

        properties_preview = []
        for name, data in properties_summary.items():
            sample_ids = data["reservation_ids"][:5]
            properties_preview.append(
                PropertyPreview(
                    name=name,
                    occurrences=data["count"],
                    matchedPropertyIds=matched_ids_map.get(name, []),
                    sampleReservationIds=sample_ids,
                )
            )

        return GmailBackfillPreviewResponse(
            processed=len(all_parsed),
            properties=properties_preview,
            reservations=reservations_preview,
        )

    def _fetch_parsed_items(
        self,
        host_id: str,
        email: str,
        force: bool = False,
        firestore_client=None,
    ) -> tuple[List[tuple[str, ParsedEmail, dict]], int]:
        integration = self._load_integration(host_id, email)

        airbnb_only = False
        if firestore_client:
            try:
                host_doc = firestore_client.collection("hosts").document(host_id).get()
                if host_doc.exists:
                    data = host_doc.to_dict()
                    airbnb_only = data.get("airbnbOnly", False)
            except Exception as e:
                logger.warning(f"[BACKFILL] Errore recupero airbnbOnly per host {host_id}: {e}")

        query = self._build_query(airbnb_only)

        logger.info(f"[BACKFILL] Inizio parsing email: host_id={host_id}, email={email}, airbnbOnly={airbnb_only}, force={force}")
        logger.info(f"[BACKFILL] Query Gmail: {query}")

        all_parsed: List[tuple[str, ParsedEmail, dict]] = []
        next_token: Optional[str] = None
        skipped_count = 0

        while True:
            response = self._gmail_service.list_messages(
                integration,
                query=query,
                page_token=next_token,
            )
            messages = response.get("messages", [])
            logger.info(f"[BACKFILL] Trovate {len(messages)} email in questa pagina")

            for message in messages:
                message_id = message["id"]
                if not force and self._processed_repository.was_processed(email, message_id):
                    skipped_count += 1
                    if skipped_count <= 5:
                        logger.debug(f"[BACKFILL] Email {message_id} già processata, skip")
                    continue

                payload = self._gmail_service.get_message_raw(integration, message_id)
                raw_data = decode_gmail_raw(payload["raw"])
                snippet = payload.get("snippet")

                parsed = self._engine.parse(
                    message_id=message_id,
                    raw_payload=raw_data,
                    snippet=snippet,
                )

                logger.info(f"[BACKFILL] Email {message_id} parsata come: kind={parsed.kind}, subject={parsed.metadata.subject}")

                all_parsed.append((message_id, parsed, payload))

            next_token = response.get("nextPageToken")
            if not next_token:
                break

        return all_parsed, skipped_count

    def _build_query(self, airbnb_only: bool = False) -> str:
        """
        Costruisce la query Gmail per il backfill.
        
        Se airbnb_only=True: cerca solo email Airbnb (conferme, cancellazioni, messaggi)
        Se airbnb_only=False: cerca email Booking e Airbnb (comportamento normale)
        """
        since = datetime.now(timezone.utc) - timedelta(days=self._lookback_days)
        date_string = since.strftime("%Y/%m/%d")
        
        if airbnb_only:
            # Solo Airbnb: conferme, cancellazioni e messaggi
            return f"(from:automated@airbnb.com OR from:express@airbnb.com) AND after:{date_string}"
        else:
            # Comportamento normale: Booking e Airbnb
            # Booking: email da reservation@scidoo.com con subject "Booking"
            booking_query = f"from:reservation@scidoo.com AND (subject:\"Confermata - Prenotazione\" OR subject:\"Cancellata - Prenotazione\") AND subject:\"Booking\" AND after:{date_string}"
            
            # Airbnb: email dirette da automated@airbnb.com
            airbnb_query = f"from:automated@airbnb.com AND (subject:\"Prenotazione confermata\" OR subject:\"Cancellazione effettuata\") AND after:{date_string}"
            
            # Combina le due query
            return f"(({booking_query}) OR ({airbnb_query}))"

    def _load_integration(self, host_id: str, email: str) -> HostEmailIntegrationRecord:
        integration = self._integration_repository.get_by_email(email)
        if integration is None:
            raise ValueError(f"Nessuna integrazione Gmail trovata per {email}")
        if integration.host_id != host_id:
            raise ValueError("L'integrazione non appartiene all'host richiesto")
        return integration

