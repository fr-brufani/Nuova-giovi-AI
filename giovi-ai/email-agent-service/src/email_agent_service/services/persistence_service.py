from __future__ import annotations

import logging

from firebase_admin import firestore

from ..models import ParsedEmail
from ..models.booking_reservation import BookingReservation
from ..models.scidoo_reservation import ScidooReservation
from ..models.smoobu_reservation import SmoobuReservation
from ..repositories import (
    BookingPropertyMappingsRepository,
    ClientsRepository,
    PropertiesRepository,
    PropertyNameMappingsRepository,
    ReservationsRepository,
    ScidooPropertyMappingsRepository,
    SmoobuPropertyMappingsRepository,
)

logger = logging.getLogger(__name__)


class PersistenceService:
    """Service per salvare dati parsati in Firestore."""

    def __init__(self, firestore_client: firestore.Client):
        self._properties_repo = PropertiesRepository(firestore_client)
        self._clients_repo = ClientsRepository(firestore_client)
        self._reservations_repo = ReservationsRepository(firestore_client)
        self._property_mappings_repo = PropertyNameMappingsRepository(firestore_client)
        self._booking_property_mappings_repo = BookingPropertyMappingsRepository(firestore_client)
        self._scidoo_property_mappings_repo = ScidooPropertyMappingsRepository(firestore_client)
        self._smoobu_property_mappings_repo = SmoobuPropertyMappingsRepository(firestore_client)

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
            "property_mapping_id": None,
            "property_mapping_action": None,
            "client_id": None,
            "client_created": False,
            "reservation_saved": False,
        }

        try:
            logger.info(f"[PERSISTENCE] Reservation ID: {reservation.reservation_id}, Property: {reservation.property_name}, Guest: {reservation.guest_name}")
            
            # Determina imported_from in base al tipo di email
            imported_from = "airbnb_email" if parsed_email.kind == "airbnb_confirmation" else "scidoo_email"
            
            # 1. Determina property applicando eventuali mapping
            if not reservation.property_name:
                logger.warning("[PERSISTENCE] Property name mancante!")
                return {
                    **result,
                    "saved": False,
                    "reason": "no_property_name",
                }

            resolved_property_id = None
            resolved_property_name = reservation.property_name

            property_created = False

            mapping = self._property_mappings_repo.get_mapping_for_name(
                host_id=host_id,
                extracted_name=resolved_property_name,
            )

            if mapping:
                result["property_mapping_id"] = mapping.id
                result["property_mapping_action"] = mapping.action

                if mapping.action == "ignore":
                    logger.info(
                        "[PERSISTENCE] Property name %s ignorato per host %s (mapping %s)",
                        resolved_property_name,
                        host_id,
                        mapping.id,
                    )
                    return {
                        **result,
                        "saved": False,
                        "reason": "property_name_ignored",
                        "property_name": resolved_property_name,
                    }

                if mapping.action == "map" and mapping.target_property_id:
                    mapped_property = self._properties_repo.get_by_id(mapping.target_property_id)
                    if mapped_property:
                        resolved_property_id = mapping.target_property_id
                        resolved_property_name = mapped_property.get("name", resolved_property_name)
                        logger.info(
                            "[PERSISTENCE] Property name %s mappato su property %s (%s)",
                            reservation.property_name,
                            resolved_property_name,
                            resolved_property_id,
                        )
                    else:
                        logger.warning(
                            "[PERSISTENCE] Mapping %s punta a property %s inesistente, fallback a creazione",
                            mapping.id,
                            mapping.target_property_id,
                        )

            if not resolved_property_id:
                logger.info(f"[PERSISTENCE] Cerca/crea property: {resolved_property_name}")
                resolved_property_id, property_created = (
                    self._properties_repo.find_or_create_by_name(
                        host_id=host_id,
                        property_name=resolved_property_name,
                        imported_from=imported_from,
                    )
                )
                result["property_created"] = property_created
                logger.info(
                    "[PERSISTENCE] Property: id=%s, created=%s",
                    resolved_property_id,
                    property_created,
                )

            result["property_id"] = resolved_property_id

            # 2. Trova/crea cliente (prima di salvare la prenotazione, così abbiamo reservation_id)
            # Nota: per ora passiamo reservation_id dopo aver creato la reservation
            # Ma per semplicità, passiamo prima property_id e reservation_id sarà aggiornato dopo
            logger.info(f"[PERSISTENCE] Cerca/crea cliente: email={reservation.guest_email}, name={reservation.guest_name}")
            client_id, client_created = self._clients_repo.find_or_create_by_email(
                host_id=host_id,
                email=reservation.guest_email,
                name=reservation.guest_name,
                phone=reservation.guest_phone,
                property_id=resolved_property_id,
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
                property_id=resolved_property_id,
                property_name=resolved_property_name or "",
                client_id=client_id,
                client_name=reservation.guest_name,
                start_date=reservation.check_in,
                end_date=reservation.check_out,
                status="confirmed",  # Scidoo invia solo prenotazioni confermate
                total_price=reservation.total_amount,
                adults=reservation.adults,
                children=reservation.children if hasattr(reservation, 'children') else None,
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
    
    def save_booking_reservation(
        self, reservation: BookingReservation, host_id: str
    ) -> dict[str, str | bool]:
        """
        Salva una prenotazione Booking.com API in Firestore - MULTI-HOST.
        
        Il host_id è già stato determinato dal polling service usando mapping
        booking_property_id → host_id.
        
        Args:
            reservation: BookingReservation parsata da XML OTA
            host_id: ID host (già mappato correttamente dal polling service)
            
        Returns:
            dict con informazioni su cosa è stato salvato
        """
        logger.info(
            f"[PERSISTENCE] Salvataggio prenotazione Booking.com: "
            f"reservation_id={reservation.reservation_id}, "
            f"property_id={reservation.property_id}, "
            f"host_id={host_id}, "
            f"guest={reservation.guest_info.email}"
        )
        
        result = {
            "property_id": None,
            "property_created": False,
            "client_id": None,
            "client_created": False,
            "reservation_saved": False,
            "saved": False,
        }
        
        try:
            # 1. Trova/crea property usando booking_property_id
            # Prima verifica se c'è mapping a internal_property_id
            booking_mapping = self._booking_property_mappings_repo.get_by_booking_property_id(
                reservation.property_id
            )
            
            resolved_property_id = None
            property_name = None
            property_created = False
            
            if booking_mapping and booking_mapping.internal_property_id:
                # Usa internal_property_id se mappato
                existing_property = self._properties_repo.get_by_id(booking_mapping.internal_property_id)
                if existing_property:
                    resolved_property_id = booking_mapping.internal_property_id
                    property_name = existing_property.get("name") or booking_mapping.property_name
                    logger.info(
                        f"[PERSISTENCE] Property trovata tramite mapping: "
                        f"booking_property_id={reservation.property_id} → "
                        f"internal_property_id={resolved_property_id}"
                    )
            
            if not resolved_property_id:
                # Cerca property per booking_property_id (se già esiste)
                # Per ora creiamo nuova property con booking_property_id come nome base
                # L'host potrà poi mapparla a una property esistente
                property_name = booking_mapping.property_name if booking_mapping else None
                property_display_name = property_name or f"Booking.com Property {reservation.property_id}"
                
                # Cerca se esiste già una property con questo nome per questo host
                existing_properties = self._properties_repo.list_by_name(host_id, property_display_name)
                if existing_properties:
                    resolved_property_id = existing_properties[0]["id"]
                    property_created = False
                    logger.info(
                        f"[PERSISTENCE] Property esistente trovata per nome: {property_display_name}"
                    )
                else:
                    # Crea nuova property
                    resolved_property_id, property_created = self._properties_repo.find_or_create_by_name(
                        host_id=host_id,
                        property_name=property_display_name,
                        imported_from="booking_api",
                    )
                    logger.info(
                        f"[PERSISTENCE] Property: id={resolved_property_id}, created={property_created}, "
                        f"name={property_display_name}"
                    )
                    
                    # Aggiorna mapping con internal_property_id
                    if booking_mapping:
                        self._booking_property_mappings_repo.update_mapping(
                            booking_mapping.id,
                            internal_property_id=resolved_property_id,
                            property_name=property_display_name,
                        )
                        logger.info(
                            f"[PERSISTENCE] Mapping aggiornato con internal_property_id: {resolved_property_id}"
                        )
                    else:
                        # Crea nuovo mapping
                        self._booking_property_mappings_repo.create_mapping(
                            booking_property_id=reservation.property_id,
                            host_id=host_id,
                            internal_property_id=resolved_property_id,
                            property_name=property_display_name,
                        )
                        logger.info(
                            f"[PERSISTENCE] Nuovo mapping creato: "
                            f"booking_property_id={reservation.property_id} → "
                            f"internal_property_id={resolved_property_id}"
                        )
            
            result["property_id"] = resolved_property_id
            result["property_created"] = property_created
            
            # 2. Trova/crea cliente
            logger.info(
                f"[PERSISTENCE] Cerca/crea cliente: email={reservation.guest_info.email}, "
                f"name={reservation.guest_info.name}"
            )
            client_id, client_created = self._clients_repo.find_or_create_by_email(
                host_id=host_id,
                email=reservation.guest_info.email,
                name=reservation.guest_info.name,
                phone=reservation.guest_info.phone,
                property_id=resolved_property_id,
                reservation_id=reservation.reservation_id,
                imported_from="booking_api",
            )
            result["client_id"] = client_id
            result["client_created"] = client_created
            logger.info(f"[PERSISTENCE] Cliente: id={client_id}, created={client_created}")
            
            # 3. Salva prenotazione
            logger.info(
                f"[PERSISTENCE] Salva prenotazione Booking.com: reservation_id={reservation.reservation_id}"
            )
            self._reservations_repo.upsert_reservation(
                reservation_id=reservation.reservation_id,
                host_id=host_id,
                property_id=resolved_property_id,
                property_name=property_name or property_display_name,
                client_id=client_id,
                client_name=reservation.guest_info.name,
                start_date=reservation.check_in,
                end_date=reservation.check_out,
                status="confirmed",
                total_price=reservation.total_amount,
                adults=reservation.adults,
                children=reservation.children,
                voucher_id=None,  # Booking.com API non usa voucher_id come Scidoo
                source_channel="booking",  # Channel Booking.com
                thread_id=None,  # Booking.com non usa thread_id come Airbnb
                imported_from="booking_api",
            )
            result["reservation_saved"] = True
            result["saved"] = True
            logger.info(
                f"[PERSISTENCE] ✅ Prenotazione Booking.com salvata con successo! "
                f"reservation_id={reservation.reservation_id}, host_id={host_id}"
            )
            
        except Exception as e:
            result["saved"] = False
            result["error"] = str(e)
            logger.error(
                f"[PERSISTENCE] ❌ Errore durante salvataggio prenotazione Booking.com: {e}",
                exc_info=True,
            )
            return result
        
        return result
    
    def update_booking_reservation(
        self, reservation: BookingReservation, host_id: str
    ) -> dict[str, str | bool]:
        """
        Aggiorna una prenotazione Booking.com esistente in Firestore.
        
        Usato per modifiche a prenotazioni già esistenti.
        
        Args:
            reservation: BookingReservation parsata da XML OTA (modificata)
            host_id: ID host (già mappato correttamente dal polling service)
            
        Returns:
            dict con informazioni su cosa è stato aggiornato
        """
        logger.info(
            f"[PERSISTENCE] Aggiornamento prenotazione Booking.com: "
            f"reservation_id={reservation.reservation_id}, host_id={host_id}"
        )
        
        result = {
            "updated": False,
            "reservation_found": False,
            "error": None,
        }
        
        try:
            # Verifica che reservation esista
            reservations_ref = self._reservations_repo._client.collection("reservations")
            query = (
                reservations_ref
                .where("reservationId", "==", reservation.reservation_id)
                .where("hostId", "==", host_id)
                .limit(1)
            )
            docs = list(query.get())
            
            if not docs:
                logger.warning(
                    f"[PERSISTENCE] Prenotazione non trovata per aggiornamento: "
                    f"reservation_id={reservation.reservation_id}, host_id={host_id}"
                )
                result["error"] = "reservation_not_found"
                return result
            
            existing_doc = docs[0]
            existing_data = existing_doc.to_dict() or {}
            result["reservation_found"] = True
            
            # Aggiorna reservation con nuovi dati
            self._reservations_repo.upsert_reservation(
                reservation_id=reservation.reservation_id,
                host_id=host_id,
                property_id=existing_data.get("propertyId", ""),
                property_name=existing_data.get("propertyName", ""),
                client_id=existing_data.get("clientId"),
                client_name=reservation.guest_info.name,
                start_date=reservation.check_in,
                end_date=reservation.check_out,
                status=existing_data.get("status", "confirmed"),  # Mantieni status esistente (non sovrascrivere "cancelled")
                total_price=reservation.total_amount,
                adults=reservation.adults,
                children=reservation.children,
                voucher_id=None,
                source_channel="booking",
                thread_id=None,
                imported_from="booking_api",
            )
            
            result["updated"] = True
            logger.info(
                f"[PERSISTENCE] ✅ Prenotazione Booking.com aggiornata: "
                f"reservation_id={reservation.reservation_id}"
            )
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(
                f"[PERSISTENCE] ❌ Errore durante aggiornamento prenotazione Booking.com: {e}",
                exc_info=True,
            )
            return result
        
        return result
    
    def cancel_booking_reservation(
        self, reservation_id: str, host_id: str
    ) -> dict[str, str | bool]:
        """
        Cancella una prenotazione Booking.com in Firestore.
        
        Usato per cancellazioni ricevute via API.
        
        Args:
            reservation_id: Reservation ID Booking.com
            host_id: ID host
            
        Returns:
            dict con informazioni su cancellazione
        """
        logger.info(
            f"[PERSISTENCE] Cancellazione prenotazione Booking.com: "
            f"reservation_id={reservation_id}, host_id={host_id}"
        )
        
        cancelled = self._reservations_repo.cancel_reservation_by_reservation_id(
            reservation_id=reservation_id,
            host_id=host_id,
        )
        
        if cancelled:
            logger.info(
                f"[PERSISTENCE] ✅ Prenotazione Booking.com cancellata: reservation_id={reservation_id}"
            )
            return {"cancelled": True, "reservation_id": reservation_id}
        else:
            logger.warning(
                f"[PERSISTENCE] ⚠️ Prenotazione Booking.com non trovata per cancellazione: "
                f"reservation_id={reservation_id}, host_id={host_id}"
            )
            return {
                "cancelled": False,
                "reservation_id": reservation_id,
                "reason": "reservation_not_found",
            }
    
    def save_scidoo_reservation(
        self, reservation: ScidooReservation, host_id: str
    ) -> dict[str, str | bool]:
        """
        Salva una prenotazione Scidoo API in Firestore.
        
        Il sistema controlla sempre se quella prenotazione esiste già (per internal_id).
        Se esiste, NON la modifica. Se non esiste, aggiunge la nuova prenotazione e il nuovo cliente.
        
        Args:
            reservation: ScidooReservation parsata da API
            host_id: ID host
            
        Returns:
            dict con informazioni su cosa è stato salvato
        """
        logger.info(
            f"[PERSISTENCE] Salvataggio prenotazione Scidoo: "
            f"internal_id={reservation.internal_id}, "
            f"room_type_id={reservation.room_type_id}, "
            f"host_id={host_id}, "
            f"guest={reservation.customer.email}"
        )
        
        result = {
            "property_id": None,
            "property_created": False,
            "client_id": None,
            "client_created": False,
            "reservation_saved": False,
            "saved": False,
            "skipped": False,
        }
        
        try:
            # 1. Trova/crea property usando room_type_id → mapping
            mapping = self._scidoo_property_mappings_repo.get_by_room_type_id(
                reservation.room_type_id,
                host_id=host_id
            )
            
            resolved_property_id = None
            property_name = None
            property_created = False
            
            if mapping and mapping.internal_property_id:
                # Usa internal_property_id se mappato
                existing_property = self._properties_repo.get_by_id(mapping.internal_property_id)
                if existing_property:
                    resolved_property_id = mapping.internal_property_id
                    property_name = existing_property.get("name") or mapping.property_name
                    logger.info(
                        f"[PERSISTENCE] Property trovata tramite mapping: "
                        f"room_type_id={reservation.room_type_id} → "
                        f"internal_property_id={resolved_property_id}"
                    )
            
            if not resolved_property_id:
                # Cerca property per nome room type o crea nuova
                room_type_name = mapping.room_type_name if mapping else f"Scidoo Room Type {reservation.room_type_id}"
                property_display_name = mapping.property_name if mapping else room_type_name
                
                # Cerca se esiste già una property con questo nome per questo host
                existing_properties = self._properties_repo.list_by_name(host_id, property_display_name)
                if existing_properties:
                    resolved_property_id = existing_properties[0]["id"]
                    property_created = False
                    logger.info(
                        f"[PERSISTENCE] Property esistente trovata per nome: {property_display_name}"
                    )
                else:
                    # Crea nuova property
                    resolved_property_id, property_created = self._properties_repo.find_or_create_by_name(
                        host_id=host_id,
                        property_name=property_display_name,
                        imported_from="scidoo_api",
                    )
                    logger.info(
                        f"[PERSISTENCE] Property: id={resolved_property_id}, created={property_created}, "
                        f"name={property_display_name}"
                    )
                    
                    # Crea/aggiorna mapping con internal_property_id
                    if mapping:
                        self._scidoo_property_mappings_repo.update_mapping(
                            mapping.id,
                            internal_property_id=resolved_property_id,
                            property_name=property_display_name,
                        )
                        logger.info(
                            f"[PERSISTENCE] Mapping aggiornato con internal_property_id: {resolved_property_id}"
                        )
                    else:
                        # Crea nuovo mapping
                        self._scidoo_property_mappings_repo.create_mapping(
                            room_type_id=reservation.room_type_id,
                            host_id=host_id,
                            internal_property_id=resolved_property_id,
                            property_name=property_display_name,
                            room_type_name=room_type_name,
                        )
                        logger.info(
                            f"[PERSISTENCE] Nuovo mapping creato: "
                            f"room_type_id={reservation.room_type_id} → "
                            f"internal_property_id={resolved_property_id}"
                        )
            
            result["property_id"] = resolved_property_id
            result["property_created"] = property_created
            
            # 2. Trova/crea cliente
            logger.info(
                f"[PERSISTENCE] Cerca/crea cliente: email={reservation.customer.email}, "
                f"name={reservation.customer.name}"
            )
            client_id, client_created = self._clients_repo.find_or_create_by_email(
                host_id=host_id,
                email=reservation.customer.email,
                name=reservation.customer.name,
                phone=reservation.customer.phone,
                property_id=resolved_property_id,
                reservation_id=reservation.internal_id,
                imported_from="scidoo_api",
            )
            result["client_id"] = client_id
            result["client_created"] = client_created
            logger.info(f"[PERSISTENCE] Cliente: id={client_id}, created={client_created}")
            
            # 3. Controlla se prenotazione esiste già (deduplica)
            # Usa internal_id come reservationId per il controllo
            reservations_ref = self._reservations_repo._client.collection("reservations")
            query = (
                reservations_ref
                .where("reservationId", "==", reservation.internal_id)
                .where("hostId", "==", host_id)
                .limit(1)
            )
            docs = list(query.get())
            
            if docs:
                # Prenotazione esiste già - NON modificare
                logger.info(
                    f"[PERSISTENCE] ⚠️ Prenotazione già esistente (internal_id={reservation.internal_id}), "
                    f"skip salvataggio per evitare duplicati"
                )
                result["saved"] = False
                result["skipped"] = True
                result["reason"] = "already_exists"
                return result
            
            # 4. Salva prenotazione (non esiste, quindi crea nuova)
            logger.info(
                f"[PERSISTENCE] Salva nuova prenotazione Scidoo: internal_id={reservation.internal_id}"
            )
            
            # Mappa stato Scidoo → Firestore
            status = self._map_scidoo_status(reservation.status)
            
            self._reservations_repo.upsert_reservation(
                reservation_id=reservation.internal_id,  # Usa internal_id come reservationId
                host_id=host_id,
                property_id=resolved_property_id,
                property_name=property_name or property_display_name,
                client_id=client_id,
                client_name=reservation.customer.name,
                start_date=reservation.checkin_date,
                end_date=reservation.checkout_date,
                status=status,
                total_price=reservation.total_price,
                adults=reservation.adults,
                children=reservation.children if hasattr(reservation, 'children') else None,
                voucher_id=None,  # Scidoo API non usa voucher_id
                source_channel=None,  # Scidoo è il PMS, non un canale
                thread_id=None,
                imported_from="scidoo_api",
            )
            result["reservation_saved"] = True
            result["saved"] = True
            logger.info(
                f"[PERSISTENCE] ✅ Prenotazione Scidoo salvata con successo! "
                f"internal_id={reservation.internal_id}, host_id={host_id}"
            )
            
        except Exception as e:
            result["saved"] = False
            result["error"] = str(e)
            logger.error(
                f"[PERSISTENCE] ❌ Errore durante salvataggio prenotazione Scidoo: {e}",
                exc_info=True,
            )
            return result
        
        return result
    
    def _map_scidoo_status(self, scidoo_status: str) -> str:
        """
        Mappa stato prenotazione Scidoo → Firestore.
        
        Args:
            scidoo_status: Stato Scidoo (es: "confermata_manuale", "annullata")
            
        Returns:
            Stato Firestore (es: "confirmed", "cancelled")
        """
        status_mapping = {
            "confermata_manuale": "confirmed",
            "confermata_pagamento": "confirmed",
            "confermata_carta": "confirmed",
            "opzione": "pending",
            "attesa_pagamento": "pending",
            "check_in": "checked_in",
            "check_out": "checked_out",
            "annullata": "cancelled",
            "eliminata": "cancelled",
            "sospesa": "pending",
            "saldo": "confirmed",
        }
        return status_mapping.get(scidoo_status, "confirmed")  # Default: confirmed
    
    def save_smoobu_reservation(
        self, reservation: SmoobuReservation, host_id: str
    ) -> dict[str, str | bool]:
        """
        Salva una prenotazione Smoobu API in Firestore - MULTI-HOST.
        
        Il sistema controlla sempre se quella prenotazione esiste già (per reservationId).
        Se esiste, aggiorna con merge. Se non esiste, aggiunge la nuova prenotazione e il nuovo cliente.
        
        Args:
            reservation: SmoobuReservation parsata da API
            host_id: ID host (già mappato correttamente dal polling service)
            
        Returns:
            dict con informazioni su cosa è stato salvato
        """
        logger.info(
            f"[PERSISTENCE] Salvataggio prenotazione Smoobu: "
            f"reservation_id={reservation.reservation_id}, "
            f"apartment_id={reservation.apartment_id}, "
            f"host_id={host_id}, "
            f"guest={reservation.email}"
        )
        
        result = {
            "property_id": None,
            "property_created": False,
            "client_id": None,
            "client_created": False,
            "reservation_saved": False,
            "saved": False,
        }
        
        try:
            # 1. Trova/crea property usando smoobu_apartment_id
            # Prima verifica se c'è mapping a internal_property_id
            smoobu_mapping = self._smoobu_property_mappings_repo.get_by_smoobu_apartment_id(
                reservation.apartment_id
            ) if reservation.apartment_id else None
            
            resolved_property_id = None
            property_name = None
            property_created = False
            
            if smoobu_mapping and smoobu_mapping.internal_property_id:
                # Usa internal_property_id se mappato
                existing_property = self._properties_repo.get_by_id(smoobu_mapping.internal_property_id)
                if existing_property:
                    resolved_property_id = smoobu_mapping.internal_property_id
                    property_name = existing_property.get("name") or smoobu_mapping.property_name
                    logger.info(
                        f"[PERSISTENCE] Property trovata tramite mapping: "
                        f"smoobu_apartment_id={reservation.apartment_id} → "
                        f"internal_property_id={resolved_property_id}"
                    )
            
            if not resolved_property_id and reservation.apartment_id:
                # Cerca property per nome o crea nuova
                property_display_name = reservation.apartment_name or f"Smoobu Apartment {reservation.apartment_id}"
                
                # Cerca se esiste già una property con questo nome per questo host
                existing_properties = self._properties_repo.list_by_name(host_id, property_display_name)
                if existing_properties:
                    resolved_property_id = existing_properties[0]["id"]
                    property_created = False
                    property_name = property_display_name
                    logger.info(
                        f"[PERSISTENCE] Property esistente trovata per nome: {property_display_name}"
                    )
                else:
                    # Crea nuova property
                    resolved_property_id, property_created = self._properties_repo.find_or_create_by_name(
                        host_id=host_id,
                        property_name=property_display_name,
                        imported_from="smoobu_api",
                    )
                    property_name = property_display_name
                    logger.info(
                        f"[PERSISTENCE] Property: id={resolved_property_id}, created={property_created}, "
                        f"name={property_display_name}"
                    )
                    
                    # Aggiorna mapping con internal_property_id
                    if smoobu_mapping:
                        self._smoobu_property_mappings_repo.update_mapping(
                            smoobu_mapping.id,
                            internal_property_id=resolved_property_id,
                            property_name=property_display_name,
                        )
                        logger.info(
                            f"[PERSISTENCE] Mapping aggiornato con internal_property_id: {resolved_property_id}"
                        )
                    else:
                        # Crea nuovo mapping
                        self._smoobu_property_mappings_repo.create_mapping(
                            smoobu_apartment_id=reservation.apartment_id,
                            host_id=host_id,
                            internal_property_id=resolved_property_id,
                            property_name=property_display_name,
                        )
                        logger.info(
                            f"[PERSISTENCE] Nuovo mapping creato: "
                            f"smoobu_apartment_id={reservation.apartment_id} → "
                            f"internal_property_id={resolved_property_id}"
                        )
            
            if not resolved_property_id:
                logger.error(f"[PERSISTENCE] ⚠️ Impossibile determinare property per apartment_id={reservation.apartment_id}")
                result["error"] = "property_not_found"
                return result
            
            result["property_id"] = resolved_property_id
            result["property_created"] = property_created
            
            # 2. Trova/crea cliente
            logger.info(
                f"[PERSISTENCE] Cerca/crea cliente: email={reservation.email}, "
                f"name={reservation.guest_name}"
            )
            client_id, client_created = self._clients_repo.find_or_create_by_email(
                host_id=host_id,
                email=reservation.email,
                name=reservation.guest_name,
                phone=reservation.phone,
                property_id=resolved_property_id,
                reservation_id=reservation.reservation_id,
                imported_from="smoobu_api",
            )
            result["client_id"] = client_id
            result["client_created"] = client_created
            logger.info(f"[PERSISTENCE] Cliente: id={client_id}, created={client_created}")
            
            # 3. Salva prenotazione (upsert_reservation gestisce già il controllo esistenza)
            logger.info(
                f"[PERSISTENCE] Salva prenotazione Smoobu: reservation_id={reservation.reservation_id}"
            )
            
            # Determina status in base al type
            status = "confirmed"
            if reservation.type == "cancellation":
                status = "cancelled"
            elif reservation.type == "modification":
                status = "confirmed"  # Modifica mantiene confirmed
            
            self._reservations_repo.upsert_reservation(
                reservation_id=reservation.reservation_id,
                host_id=host_id,
                property_id=resolved_property_id,
                property_name=property_name or reservation.apartment_name or "",
                client_id=client_id,
                client_name=reservation.guest_name,
                start_date=reservation.arrival,
                end_date=reservation.departure,
                status=status,
                total_price=reservation.price,
                adults=reservation.adults,
                children=reservation.children,
                voucher_id=reservation.reference_id,  # Usa reference_id come voucher_id
                source_channel="smoobu",  # Channel Smoobu
                thread_id=None,  # Smoobu non usa thread_id
                imported_from="smoobu_api",
            )
            result["reservation_saved"] = True
            result["saved"] = True
            logger.info(
                f"[PERSISTENCE] ✅ Prenotazione Smoobu salvata con successo! "
                f"reservation_id={reservation.reservation_id}, host_id={host_id}"
            )
            
        except Exception as e:
            result["saved"] = False
            result["error"] = str(e)
            logger.error(
                f"[PERSISTENCE] ❌ Errore durante salvataggio prenotazione Smoobu: {e}",
                exc_info=True,
            )
            return result
        
        return result
    
    def update_smoobu_reservation(
        self, reservation: SmoobuReservation, host_id: str
    ) -> dict[str, str | bool]:
        """
        Aggiorna una prenotazione Smoobu esistente in Firestore.
        
        Usato per modifiche a prenotazioni già esistenti.
        
        Args:
            reservation: SmoobuReservation parsata da API (modificata)
            host_id: ID host (già mappato correttamente dal polling service)
            
        Returns:
            dict con informazioni su cosa è stato aggiornato
        """
        logger.info(
            f"[PERSISTENCE] Aggiornamento prenotazione Smoobu: "
            f"reservation_id={reservation.reservation_id}, host_id={host_id}"
        )
        
        result = {
            "updated": False,
            "reservation_found": False,
            "error": None,
        }
        
        try:
            # Verifica che reservation esista
            reservations_ref = self._reservations_repo._client.collection("reservations")
            query = (
                reservations_ref
                .where("reservationId", "==", reservation.reservation_id)
                .where("hostId", "==", host_id)
                .limit(1)
            )
            docs = list(query.get())
            
            if not docs:
                logger.warning(
                    f"[PERSISTENCE] Prenotazione non trovata per aggiornamento: "
                    f"reservation_id={reservation.reservation_id}, host_id={host_id}"
                )
                result["error"] = "reservation_not_found"
                return result
            
            existing_doc = docs[0]
            existing_data = existing_doc.to_dict() or {}
            result["reservation_found"] = True
            
            # Aggiorna reservation con nuovi dati (usa save_smoobu_reservation che fa upsert)
            save_result = self.save_smoobu_reservation(reservation, host_id)
            
            if save_result.get("saved"):
                result["updated"] = True
                logger.info(
                    f"[PERSISTENCE] ✅ Prenotazione Smoobu aggiornata: "
                    f"reservation_id={reservation.reservation_id}"
                )
            else:
                result["error"] = save_result.get("error", "unknown")
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(
                f"[PERSISTENCE] ❌ Errore durante aggiornamento prenotazione Smoobu: {e}",
                exc_info=True,
            )
            return result
        
        return result
    
    def cancel_smoobu_reservation(
        self, reservation_id: str, host_id: str
    ) -> dict[str, str | bool]:
        """
        Cancella una prenotazione Smoobu in Firestore.
        
        Usato per cancellazioni ricevute via API.
        
        Args:
            reservation_id: Reservation ID Smoobu
            host_id: ID host
            
        Returns:
            dict con informazioni su cancellazione
        """
        logger.info(
            f"[PERSISTENCE] Cancellazione prenotazione Smoobu: "
            f"reservation_id={reservation_id}, host_id={host_id}"
        )
        
        cancelled = self._reservations_repo.cancel_reservation_by_reservation_id(
            reservation_id=reservation_id,
            host_id=host_id,
        )
        
        if cancelled:
            logger.info(
                f"[PERSISTENCE] ✅ Prenotazione Smoobu cancellata: reservation_id={reservation_id}"
            )
            return {"cancelled": True, "reservation_id": reservation_id}
        else:
            logger.warning(
                f"[PERSISTENCE] ⚠️ Prenotazione Smoobu non trovata per cancellazione: "
                f"reservation_id={reservation_id}, host_id={host_id}"
            )
            return {
                "cancelled": False,
                "reservation_id": reservation_id,
                "reason": "reservation_not_found",
            }

