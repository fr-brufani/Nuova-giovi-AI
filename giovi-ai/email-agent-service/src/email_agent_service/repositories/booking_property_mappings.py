"""Repository per mappare property_id Booking.com → host_id."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from firebase_admin import firestore


@dataclass
class BookingPropertyMapping:
    """Mapping tra property_id Booking.com e host_id + property_id interno."""
    
    id: str
    booking_property_id: str  # Property ID Booking.com (es: "8011855")
    host_id: str  # ID host proprietario
    internal_property_id: Optional[str] = None  # Property ID interno (se mappato)
    property_name: Optional[str] = None  # Nome property (per reference)
    created_at: Optional[object] = None
    updated_at: Optional[object] = None


class BookingPropertyMappingsRepository:
    """Repository per gestire mapping Booking.com property_id → host_id."""
    
    COLLECTION = "bookingPropertyMappings"
    
    def __init__(self, client: firestore.Client):
        self._client = client
    
    def get_by_booking_property_id(
        self, booking_property_id: str
    ) -> Optional[BookingPropertyMapping]:
        """
        Recupera mapping per property_id Booking.com.
        
        Args:
            booking_property_id: Property ID Booking.com (es: "8011855")
            
        Returns:
            Mapping se trovato, None altrimenti
        """
        query = (
            self._collection()
            .where("bookingPropertyId", "==", booking_property_id)
            .limit(1)
        )
        docs = list(query.get())
        if not docs:
            return None
        return self._deserialize(docs[0])
    
    def get_by_host(self, host_id: str) -> list[BookingPropertyMapping]:
        """
        Recupera tutti i mapping per un host.
        
        Args:
            host_id: ID host
            
        Returns:
            Lista di mapping
        """
        query = self._collection().where("hostId", "==", host_id)
        docs = list(query.get())
        return [self._deserialize(doc) for doc in docs]
    
    def create_mapping(
        self,
        booking_property_id: str,
        host_id: str,
        internal_property_id: Optional[str] = None,
        property_name: Optional[str] = None,
    ) -> str:
        """
        Crea un nuovo mapping.
        
        Args:
            booking_property_id: Property ID Booking.com
            host_id: ID host proprietario
            internal_property_id: Property ID interno (opzionale, può essere mappato dopo)
            property_name: Nome property (opzionale, per reference)
            
        Returns:
            ID del mapping creato
        """
        # Verifica se esiste già
        existing = self.get_by_booking_property_id(booking_property_id)
        if existing:
            # Aggiorna se host_id diverso o aggiunge internal_property_id
            if existing.host_id != host_id or internal_property_id:
                self.update_mapping(
                    existing.id,
                    host_id=host_id if existing.host_id != host_id else None,
                    internal_property_id=internal_property_id,
                    property_name=property_name,
                )
            return existing.id
        
        data = {
            "bookingPropertyId": booking_property_id,
            "hostId": host_id,
            "internalPropertyId": internal_property_id,
            "propertyName": property_name,
            "createdAt": firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        }
        doc_ref = self._collection().document()
        doc_ref.set(data)
        return doc_ref.id
    
    def update_mapping(
        self,
        mapping_id: str,
        host_id: Optional[str] = None,
        internal_property_id: Optional[str] = None,
        property_name: Optional[str] = None,
    ) -> None:
        """
        Aggiorna un mapping esistente.
        
        Args:
            mapping_id: ID del mapping
            host_id: Nuovo host_id (opzionale)
            internal_property_id: Nuovo internal_property_id (opzionale)
            property_name: Nuovo property_name (opzionale)
        """
        updates = {"updatedAt": firestore.SERVER_TIMESTAMP}
        
        if host_id is not None:
            updates["hostId"] = host_id
        if internal_property_id is not None:
            updates["internalPropertyId"] = internal_property_id
        if property_name is not None:
            updates["propertyName"] = property_name
        
        self._collection().document(mapping_id).set(updates, merge=True)
    
    def delete_mapping(self, mapping_id: str) -> None:
        """Elimina un mapping."""
        self._collection().document(mapping_id).delete()
    
    def _collection(self):
        return self._client.collection(self.COLLECTION)
    
    @staticmethod
    def _deserialize(doc) -> BookingPropertyMapping:
        data = doc.to_dict() or {}
        return BookingPropertyMapping(
            id=doc.id,
            booking_property_id=data.get("bookingPropertyId", ""),
            host_id=data.get("hostId", ""),
            internal_property_id=data.get("internalPropertyId"),
            property_name=data.get("propertyName"),
            created_at=data.get("createdAt"),
            updated_at=data.get("updatedAt"),
        )

