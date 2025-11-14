from __future__ import annotations

from datetime import datetime
from typing import Optional

from firebase_admin import firestore


class ReservationsRepository:
    """Repository per gestire prenotazioni in Firestore.
    
    Le prenotazioni sono salvate in: reservations/{randomId}
    Il document ID è generato automaticamente da Firestore.
    I campi reservationId e voucherId sono salvati dentro il documento.
    """

    def __init__(self, client: firestore.Client):
        self._client = client

    def upsert_reservation(
        self,
        reservation_id: str,
        host_id: str,
        property_id: str,
        property_name: str,
        client_id: Optional[str],
        client_name: Optional[str],
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        status: str = "confirmed",
        total_price: Optional[float] = None,
        adults: Optional[int] = None,
        voucher_id: Optional[str] = None,
        source_channel: Optional[str] = None,  # "booking" o "airbnb"
        imported_from: str = "scidoo_email",
    ) -> None:
        """
        Crea o aggiorna una prenotazione.
        
        Cerca prima se esiste già una reservation con lo stesso reservationId o voucherId.
        Se esiste, aggiorna il documento esistente.
        Se non esiste, crea un nuovo documento con ID generato automaticamente.
        """
        reservations_ref = self._client.collection("reservations")
        
        # Cerca se esiste già una reservation con lo stesso reservationId o voucherId
        existing_doc = None
        
        # Prima cerca per reservationId
        if reservation_id:
            query = (
                reservations_ref
                .where("reservationId", "==", reservation_id)
                .where("hostId", "==", host_id)
                .limit(1)
            )
            docs = list(query.get())
            if docs:
                existing_doc = docs[0]
        
        # Se non trovato e abbiamo voucherId, cerca per voucherId
        if not existing_doc and voucher_id:
            query = (
                reservations_ref
                .where("voucherId", "==", voucher_id)
                .where("hostId", "==", host_id)
                .limit(1)
            )
            docs = list(query.get())
            if docs:
                existing_doc = docs[0]

        reservation_data = {
            "reservationId": reservation_id,  # Campo dentro il documento
            "hostId": host_id,
            "propertyId": property_id,
            "propertyName": property_name,
            "startDate": start_date,
            "endDate": end_date,
            "status": status,
            "lastUpdatedAt": firestore.SERVER_TIMESTAMP,
            "importedFrom": imported_from,
        }

        if client_id:
            reservation_data["clientId"] = client_id
        if client_name:
            reservation_data["clientName"] = client_name
        if total_price is not None:
            reservation_data["totalPrice"] = total_price
        if adults is not None:
            reservation_data["adults"] = adults
        if voucher_id:
            reservation_data["voucherId"] = voucher_id  # ID Voucher da Booking/Scidoo
        if source_channel:
            reservation_data["sourceChannel"] = source_channel  # "booking" o "airbnb" (da subject email Scidoo)

        if existing_doc:
            # Aggiorna documento esistente
            existing_doc.reference.set(reservation_data, merge=True)
        else:
            # Crea nuovo documento con ID generato automaticamente
            new_doc_ref = reservations_ref.document()
            reservation_data["createdAt"] = firestore.SERVER_TIMESTAMP
            new_doc_ref.set(reservation_data)

    def cancel_reservation_by_voucher_id(
        self,
        voucher_id: str,
        host_id: str,
    ) -> bool:
        """
        Cancella una prenotazione cercandola per voucherId.
        
        Returns:
            True se la prenotazione è stata trovata e cancellata, False altrimenti
        """
        reservations_ref = self._client.collection("reservations")
        
        # Cerca prenotazione per voucherId e hostId
        query = (
            reservations_ref
            .where("voucherId", "==", voucher_id)
            .where("hostId", "==", host_id)
            .limit(1)
        )
        docs = list(query.get())
        
        if not docs:
            return False
        
        # Aggiorna lo status a "cancelled"
        doc = docs[0]
        doc.reference.set(
            {
                "status": "cancelled",
                "lastUpdatedAt": firestore.SERVER_TIMESTAMP,
                "cancellationDetails": f"Cancellata via email Scidoo {datetime.now().isoformat()}",
            },
            merge=True,
        )
        return True

