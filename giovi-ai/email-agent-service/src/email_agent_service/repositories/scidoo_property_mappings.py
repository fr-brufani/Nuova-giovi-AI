"""Repository per mappare room_type_id Scidoo → host_id."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from firebase_admin import firestore


@dataclass
class ScidooPropertyMapping:
    """Mapping tra room_type_id Scidoo e host_id + property_id interno."""
    
    id: str
    scidoo_room_type_id: str  # Room Type ID Scidoo (es: "1")
    host_id: str  # ID host proprietario
    internal_property_id: Optional[str] = None  # Property ID interno (se mappato)
    property_name: Optional[str] = None  # Nome property (per reference)
    room_type_name: Optional[str] = None  # Nome room type Scidoo
    created_at: Optional[object] = None
    updated_at: Optional[object] = None


class ScidooPropertyMappingsRepository:
    """Repository per gestire mapping Scidoo room_type_id → host_id."""
    
    COLLECTION = "scidooPropertyMappings"
    
    def __init__(self, client: firestore.Client):
        self._client = client
    
    def get_by_room_type_id(
        self, 
        room_type_id: str,
        host_id: Optional[str] = None
    ) -> Optional[ScidooPropertyMapping]:
        """
        Recupera mapping per room_type_id Scidoo.
        
        Args:
            room_type_id: Room Type ID Scidoo (es: "1")
            host_id: Opzionale, filtra per host_id
        
        Returns:
            Mapping se trovato, None altrimenti
        """
        query = self._collection().where("scidooRoomTypeId", "==", str(room_type_id))
        
        if host_id:
            query = query.where("hostId", "==", host_id)
        
        query = query.limit(1)
        docs = list(query.get())
        if not docs:
            return None
        return self._deserialize(docs[0])
    
    def get_by_host(self, host_id: str) -> list[ScidooPropertyMapping]:
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
        room_type_id: str,
        host_id: str,
        internal_property_id: Optional[str] = None,
        property_name: Optional[str] = None,
        room_type_name: Optional[str] = None,
    ) -> str:
        """
        Crea un nuovo mapping.
        
        Args:
            room_type_id: Room Type ID Scidoo
            host_id: ID host proprietario
            internal_property_id: Property ID interno (opzionale)
            property_name: Nome property (opzionale)
            room_type_name: Nome room type Scidoo (opzionale)
            
        Returns:
            ID del mapping creato
        """
        # Verifica se esiste già
        existing = self.get_by_room_type_id(room_type_id, host_id)
        if existing:
            # Aggiorna se necessario
            if internal_property_id or property_name or room_type_name:
                self.update_mapping(
                    existing.id,
                    internal_property_id=internal_property_id,
                    property_name=property_name,
                    room_type_name=room_type_name,
                )
            return existing.id
        
        data = {
            "scidooRoomTypeId": str(room_type_id),
            "hostId": host_id,
            "internalPropertyId": internal_property_id,
            "propertyName": property_name,
            "roomTypeName": room_type_name,
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
        room_type_name: Optional[str] = None,
    ) -> None:
        """
        Aggiorna un mapping esistente.
        
        Args:
            mapping_id: ID del mapping
            host_id: Nuovo host_id (opzionale)
            internal_property_id: Nuovo internal_property_id (opzionale)
            property_name: Nuovo property_name (opzionale)
            room_type_name: Nuovo room_type_name (opzionale)
        """
        updates = {"updatedAt": firestore.SERVER_TIMESTAMP}
        
        if host_id is not None:
            updates["hostId"] = host_id
        if internal_property_id is not None:
            updates["internalPropertyId"] = internal_property_id
        if property_name is not None:
            updates["propertyName"] = property_name
        if room_type_name is not None:
            updates["roomTypeName"] = room_type_name
        
        self._collection().document(mapping_id).set(updates, merge=True)
    
    def delete_mapping(self, mapping_id: str) -> None:
        """Elimina un mapping."""
        self._collection().document(mapping_id).delete()
    
    def delete_by_host(self, host_id: str) -> int:
        """
        Elimina tutti i mapping per un host.
        
        Args:
            host_id: ID host
            
        Returns:
            Numero di mapping eliminati
        """
        query = self._collection().where("hostId", "==", host_id)
        docs = list(query.get())
        deleted = 0
        for doc in docs:
            doc.reference.delete()
            deleted += 1
        return deleted
    
    def _collection(self):
        return self._client.collection(self.COLLECTION)
    
    @staticmethod
    def _deserialize(doc) -> ScidooPropertyMapping:
        data = doc.to_dict() or {}
        return ScidooPropertyMapping(
            id=doc.id,
            scidoo_room_type_id=data.get("scidooRoomTypeId", ""),
            host_id=data.get("hostId", ""),
            internal_property_id=data.get("internalPropertyId"),
            property_name=data.get("propertyName"),
            room_type_name=data.get("roomTypeName"),
            created_at=data.get("createdAt"),
            updated_at=data.get("updatedAt"),
        )

