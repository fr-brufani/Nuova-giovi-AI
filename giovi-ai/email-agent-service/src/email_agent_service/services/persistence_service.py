from __future__ import annotations

import logging

from firebase_admin import firestore

from ..models import ParsedEmail
from ..repositories import ClientsRepository, PropertiesRepository, ReservationsRepository

logger = logging.getLogger(__name__)


class PersistenceService:
    """Service per salvare dati parsati in Firestore."""

    def __init__(self, firestore_client: firestore.Client):
        self._properties_repo = PropertiesRepository(firestore_client)
        self._clients_repo = ClientsRepository(firestore_client)
        self._reservations_repo = ReservationsRepository(firestore_client)

    def save_parsed_email(
        self, parsed_email: ParsedEmail, host_id: str
    ) -> dict[str, str | bool]:
        """
        Salva un'email parsata in Firestore.
        
        Per scidoo_confirmation:
        - Trova/crea property (da propertyName)
        - Trova/crea cliente (da guestEmail/guestName)
        - Crea/aggiorna prenotazione
        
        Per scidoo_cancellation:
        - Cerca prenotazione per voucherId
        - Aggiorna status a "cancelled"
        
        Returns:
            dict con informazioni su cosa è stato salvato
        """
        logger.info(f"[PERSISTENCE] Tentativo salvataggio email kind={parsed_email.kind}")
        
        # Gestione cancellazioni
        if parsed_email.kind == "scidoo_cancellation":
            if not parsed_email.reservation or not parsed_email.reservation.voucher_id:
                logger.warning(f"[PERSISTENCE] Email cancellazione senza voucherId")
                return {"saved": False, "reason": "no_voucher_id"}
            
            voucher_id = parsed_email.reservation.voucher_id
            logger.info(f"[PERSISTENCE] Cerca prenotazione da cancellare: voucher_id={voucher_id}")
            
            cancelled = self._reservations_repo.cancel_reservation_by_voucher_id(
                voucher_id=voucher_id,
                host_id=host_id,
            )
            
            if cancelled:
                logger.info(f"[PERSISTENCE] ✅ Prenotazione cancellata: voucher_id={voucher_id}")
                return {"saved": True, "cancelled": True, "voucher_id": voucher_id}
            else:
                logger.warning(f"[PERSISTENCE] ⚠️ Prenotazione non trovata per cancellazione: voucher_id={voucher_id}")
                return {"saved": False, "reason": "reservation_not_found", "voucher_id": voucher_id}
        
        if parsed_email.kind == "airbnb_cancellation":
            if not parsed_email.reservation:
                logger.warning(f"[PERSISTENCE] Email cancellazione Airbnb senza reservation data")
                return {"saved": False, "reason": "no_reservation_data"}
            
            reservation = parsed_email.reservation
            reservation_id = reservation.reservation_id
            thread_id = reservation.thread_id
            
            logger.info(f"[PERSISTENCE] Cerca prenotazione Airbnb da cancellare: reservationId={reservation_id}, threadId={thread_id}")
            
            # Cerca reservation per reservationId o threadId
            cancelled = False
            if reservation_id and reservation_id != "unknown":
                cancelled = self._reservations_repo.cancel_reservation_by_reservation_id(
                    reservation_id=reservation_id,
                    host_id=host_id,
                )
            elif thread_id:
                cancelled = self._reservations_repo.cancel_reservation_by_thread_id(
                    thread_id=thread_id,
                    host_id=host_id,
                )
            
            if cancelled:
                logger.info(f"[PERSISTENCE] ✅ Prenotazione Airbnb cancellata: reservationId={reservation_id}, threadId={thread_id}")
                return {"saved": True, "cancelled": True, "reservation_id": reservation_id, "thread_id": thread_id}
            else:
                logger.warning(f"[PERSISTENCE] ⚠️ Prenotazione Airbnb non trovata per cancellazione: reservationId={reservation_id}, threadId={thread_id}")
                return {"saved": False, "reason": "reservation_not_found", "reservation_id": reservation_id, "thread_id": thread_id}
        
        if parsed_email.kind not in ["scidoo_confirmation", "airbnb_confirmation"]:
            # Gestiamo scidoo_confirmation, airbnb_confirmation e scidoo_cancellation
            logger.warning(f"[PERSISTENCE] Kind non supportato: {parsed_email.kind}")
            return {"saved": False, "reason": "kind_not_supported"}

        if not parsed_email.reservation:
            logger.warning(f"[PERSISTENCE] Nessun dato reservation nell'email")
            return {"saved": False, "reason": "no_reservation_data"}

        reservation = parsed_email.reservation

        result = {
            "property_id": None,
            "property_created": False,
            "client_id": None,
            "client_created": False,
            "reservation_saved": False,
        }

        try:
            logger.info(f"[PERSISTENCE] Reservation ID: {reservation.reservation_id}, Property: {reservation.property_name}, Guest: {reservation.guest_name}")
            
            # Determina imported_from in base al tipo di email
            imported_from = "airbnb_email" if parsed_email.kind == "airbnb_confirmation" else "scidoo_email"
            
            # 1. Trova/crea property
            if reservation.property_name:
                logger.info(f"[PERSISTENCE] Cerca/crea property: {reservation.property_name}")
                property_id, property_created = (
                    self._properties_repo.find_or_create_by_name(
                        host_id=host_id,
                        property_name=reservation.property_name,
                        imported_from=imported_from,
                    )
                )
                result["property_id"] = property_id
                result["property_created"] = property_created
                logger.info(f"[PERSISTENCE] Property: id={property_id}, created={property_created}")
            else:
                logger.warning(f"[PERSISTENCE] Property name mancante!")
                return {
                    **result,
                    "saved": False,
                    "reason": "no_property_name",
                }

            # 2. Trova/crea cliente (prima di salvare la prenotazione, così abbiamo reservation_id)
            # Nota: per ora passiamo reservation_id dopo aver creato la reservation
            # Ma per semplicità, passiamo prima property_id e reservation_id sarà aggiornato dopo
            logger.info(f"[PERSISTENCE] Cerca/crea cliente: email={reservation.guest_email}, name={reservation.guest_name}")
            client_id, client_created = self._clients_repo.find_or_create_by_email(
                host_id=host_id,
                email=reservation.guest_email,
                name=reservation.guest_name,
                phone=reservation.guest_phone,
                property_id=property_id,
                reservation_id=reservation.reservation_id,
                imported_from=imported_from,
            )
            result["client_id"] = client_id
            result["client_created"] = client_created
            logger.info(f"[PERSISTENCE] Cliente: id={client_id}, created={client_created}")

            # 3. Salva prenotazione
            logger.info(f"[PERSISTENCE] Salva prenotazione: reservation_id={reservation.reservation_id}, voucher_id={reservation.voucher_id}, source_channel={reservation.source_channel}, thread_id={reservation.thread_id}")
            self._reservations_repo.upsert_reservation(
                reservation_id=reservation.reservation_id,
                host_id=host_id,
                property_id=property_id,
                property_name=reservation.property_name or "",
                client_id=client_id,
                client_name=reservation.guest_name,
                start_date=reservation.check_in,
                end_date=reservation.check_out,
                status="confirmed",  # Scidoo invia solo prenotazioni confermate
                total_price=reservation.total_amount,
                adults=reservation.adults,
                voucher_id=reservation.voucher_id,  # ID Voucher estratto dalla email
                source_channel=reservation.source_channel,  # "booking" o "airbnb" dal subject
                thread_id=reservation.thread_id,  # Thread ID per Airbnb (per matchare messaggi)
                imported_from=imported_from,
            )
            result["reservation_saved"] = True
            result["saved"] = True
            logger.info(f"[PERSISTENCE] ✅ Salvataggio completato con successo!")

        except Exception as e:
            result["saved"] = False
            result["error"] = str(e)
            logger.error(f"[PERSISTENCE] ❌ Errore durante salvataggio: {e}", exc_info=True)
            return result

        return result

