from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from ..models import ParsedEmail
from ..parsers import EmailParsingEngine
from ..parsers.engine import decode_gmail_raw
from ..repositories import HostEmailIntegrationRepository
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

    def run_backfill(self, host_id: str, email: str, force: bool = False) -> List[ParsedEmail]:
        integration = self._load_integration(host_id, email)
        query = self._build_query(integration.pms_provider)
        
        logger.info(f"[BACKFILL] Inizio backfill per host_id={host_id}, email={email}, pms_provider={integration.pms_provider}, force={force}")
        logger.info(f"[BACKFILL] Query Gmail: {query}")

        # FASE 1: Fetch e parse tutte le email (senza salvare)
        all_parsed: List[tuple[str, ParsedEmail, dict]] = []  # (message_id, parsed, payload)
        next_token: Optional[str] = None
        skipped_count = 0

        logger.info(f"[BACKFILL] FASE 1: Fetch e parsing di tutte le email...")
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
                    if skipped_count <= 5:  # Log solo le prime 5 per non intasare
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
                
                # Log tipo email parsata
                logger.info(f"[BACKFILL] Email {message_id} parsata come: kind={parsed.kind}, subject={parsed.metadata.subject}")
                
                all_parsed.append((message_id, parsed, payload))

            next_token = response.get("nextPageToken")
            if not next_token:
                break

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
            logger.info(f"[BACKFILL] Email Scidoo conferma trovata! Reservation ID: {parsed.reservation.reservation_id if parsed.reservation else 'N/A'}, Property: {parsed.reservation.property_name if parsed.reservation else 'N/A'}")
            try:
                save_result = self._persistence_service.save_parsed_email(
                    parsed_email=parsed, host_id=host_id
                )
                if save_result.get("saved"):
                    logger.info(f"[BACKFILL] ✅ Salvato: property_id={save_result.get('property_id')}, client_id={save_result.get('client_id')}, reservation_saved={save_result.get('reservation_saved')}")
                else:
                    logger.warning(f"[BACKFILL] ❌ Salvataggio fallito: {save_result.get('reason')}, error={save_result.get('error')}")
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

    def _build_query(self, pms_provider: Optional[str] = None) -> str:
        """
        Costruisce la query Gmail per il backfill.
        
        Per pms_provider="scidoo":
        - Booking: email da reservation@scidoo.com con subject che finisce con " - Booking"
        - Airbnb: email da automated@airbnb.com con subject "Prenotazione confermata" o "Cancellazione effettuata"
        """
        since = datetime.now(timezone.utc) - timedelta(days=self._lookback_days)
        date_string = since.strftime("%Y/%m/%d")
        
        if pms_provider == "scidoo":
            # Per Scidoo: cerca email Booking da reservation@scidoo.com
            # Subject Booking: "Confermata - Prenotazione ID 5150895143 - Booking"
            # Subject Cancellazione Booking: "Cancellata - Prenotazione ID ... - Booking"
            # Usa subject:"Booking" invece di subject:" - Booking" per essere più flessibile
            booking_query = f"from:reservation@scidoo.com AND (subject:\"Confermata - Prenotazione\" OR subject:\"Cancellata - Prenotazione\") AND subject:\"Booking\" AND after:{date_string}"
            
            # Per Airbnb: cerca email dirette da automated@airbnb.com
            # Subject conferma: "Prenotazione confermata - ..."
            # Subject cancellazione: "Cancellazione effettuata - ..." (nota: "Cancellazione" non "Cancellata")
            airbnb_query = f"from:automated@airbnb.com AND (subject:\"Prenotazione confermata\" OR subject:\"Cancellazione effettuata\") AND after:{date_string}"
            
            # Combina le due query con parentesi esplicite per evitare ambiguità
            return f"(({booking_query}) OR ({airbnb_query}))"
        elif pms_provider == "booking":
            # Per Booking: cerca messaggi da @guest.booking.com
            return f"from:@guest.booking.com AND after:{date_string}"
        elif pms_provider == "airbnb":
            # Per Airbnb: cerca conferme e messaggi
            return f"(from:automated@airbnb.com OR from:express@airbnb.com) AND after:{date_string}"
        else:
            # Fallback: query generica (per retrocompatibilità o "other")
            booking_query = "(from:@guest.booking.com OR from:reservation@scidoo.com)"
            airbnb_query = "(from:express@airbnb.com OR from:automated@airbnb.com)"
            return f"({booking_query} OR {airbnb_query}) AND after:{date_string}"

    def _load_integration(self, host_id: str, email: str) -> HostEmailIntegrationRecord:
        integration = self._integration_repository.get_by_email(email)
        if integration is None:
            raise ValueError(f"Nessuna integrazione Gmail trovata per {email}")
        if integration.host_id != host_id:
            raise ValueError("L'integrazione non appartiene all'host richiesto")
        return integration

