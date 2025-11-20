from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from firebase_admin import firestore


PropertyMappingAction = Literal["map", "ignore"]


@dataclass
class PropertyNameMapping:
    id: str
    host_id: str
    extracted_name: str
    action: PropertyMappingAction
    target_property_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[object] = None
    updated_at: Optional[object] = None


class PropertyNameMappingsRepository:
    """Repository per gestire i mapping tra property estratte e property reali."""

    COLLECTION = "propertyNameMappings"

    def __init__(self, client: firestore.Client):
        self._client = client

    def list_by_host(
        self,
        host_id: str,
        action: Optional[PropertyMappingAction] = None,
    ) -> list[PropertyNameMapping]:
        query = self._collection().where("hostId", "==", host_id)
        if action:
            query = query.where("action", "==", action)
        docs = query.stream()
        return [self._deserialize(doc) for doc in docs]

    def get_by_id(self, mapping_id: str) -> Optional[PropertyNameMapping]:
        doc = self._collection().document(mapping_id).get()
        if not doc.exists:
            return None
        return self._deserialize(doc)

    def get_mapping_for_name(
        self,
        host_id: str,
        extracted_name: Optional[str],
    ) -> Optional[PropertyNameMapping]:
        if not extracted_name:
            return None

        normalized = self._normalize_name(extracted_name)
        if not normalized:
            return None

        query = (
            self._collection()
            .where("hostId", "==", host_id)
            .where("extractedNameLower", "==", normalized)
            .limit(1)
        )
        docs = list(query.get())
        if not docs:
            return None
        return self._deserialize(docs[0])

    def create_mapping(
        self,
        *,
        host_id: str,
        extracted_name: str,
        action: PropertyMappingAction,
        target_property_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> str:
        normalized = self._normalize_name(extracted_name)
        if not normalized:
            raise ValueError("Il nome estratto non può essere vuoto")

        data = {
            "hostId": host_id,
            "extractedName": extracted_name.strip(),
            "extractedNameLower": normalized,
            "action": action,
            "targetPropertyId": target_property_id,
            "notes": notes,
            "createdAt": firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        }
        doc_ref = self._collection().document()
        doc_ref.set(data)
        return doc_ref.id

    def update_mapping(
        self,
        mapping_id: str,
        *,
        extracted_name: Optional[str] = None,
        action: Optional[PropertyMappingAction] = None,
        target_property_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> None:
        updates: dict[str, Optional[str]] = {"updatedAt": firestore.SERVER_TIMESTAMP}

        if extracted_name is not None:
            normalized = self._normalize_name(extracted_name)
            if not normalized:
                raise ValueError("Il nome estratto non può essere vuoto")
            updates["extractedName"] = extracted_name.strip()
            updates["extractedNameLower"] = normalized

        if action is not None:
            updates["action"] = action
        if target_property_id is not None or action == "ignore":
            updates["targetPropertyId"] = target_property_id
        if notes is not None:
            updates["notes"] = notes

        self._collection().document(mapping_id).set(updates, merge=True)

    def delete_mapping(self, mapping_id: str) -> None:
        self._collection().document(mapping_id).delete()

    def _collection(self):
        return self._client.collection(self.COLLECTION)

    @staticmethod
    def _normalize_name(name: str) -> str:
        return name.strip().lower()

    @staticmethod
    def _deserialize(doc) -> PropertyNameMapping:
        data = doc.to_dict() or {}
        return PropertyNameMapping(
            id=doc.id,
            host_id=data.get("hostId"),
            extracted_name=data.get("extractedName"),
            action=data.get("action", "map"),
            target_property_id=data.get("targetPropertyId"),
            notes=data.get("notes"),
            created_at=data.get("createdAt"),
            updated_at=data.get("updatedAt"),
        )


