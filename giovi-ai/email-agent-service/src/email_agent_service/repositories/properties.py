from __future__ import annotations

from typing import Any, List, Optional

from firebase_admin import firestore


class PropertiesRepository:
    """Repository per gestire properties in Firestore.
    
    Le properties sono salvate in: properties/{propertyId}
    con campo hostId per filtrare per host.
    """

    def __init__(self, client: firestore.Client):
        self._client = client

    def get_by_id(self, property_id: str) -> Optional[dict[str, Any]]:
        """
        Recupera una property per ID.
        """
        doc = self._client.collection("properties").document(property_id).get()
        if not doc.exists:
            return None
        data = doc.to_dict() or {}
        data["id"] = doc.id
        return data

    def find_or_create_by_name(
        self,
        host_id: str,
        property_name: str,
        imported_from: str = "scidoo_email",
    ) -> tuple[str, bool]:
        """
        Trova o crea una property per nome e hostId.
        
        Returns:
            tuple[property_id, was_created]: ID della property e se è stata creata
        """
        if not property_name or not property_name.strip():
            raise ValueError("Property name cannot be empty")

        trimmed_name = property_name.strip()
        properties_ref = self._client.collection("properties")

        # Cerca per nome E hostId (per evitare duplicati tra host diversi)
        query = (
            properties_ref
            .where("name", "==", trimmed_name)
            .where("hostId", "==", host_id)
            .limit(1)
        )
        docs = query.get()

        # Controlla se ci sono risultati (QueryResultsList non ha .empty)
        docs_list = list(docs)
        if docs_list:
            # Property esiste già
            doc = docs_list[0]
            # Aggiorna lastUpdatedAt
            doc.reference.set(
                {"lastUpdatedAt": firestore.SERVER_TIMESTAMP},
                merge=True,
            )
            return doc.id, False

        # Crea nuova property
        new_doc_ref = properties_ref.document()
        requires_review = imported_from == "airbnb_email"
        new_doc_ref.set(
            {
                "name": trimmed_name,
                "hostId": host_id,
                "createdAt": firestore.SERVER_TIMESTAMP,
                "lastUpdatedAt": firestore.SERVER_TIMESTAMP,
                "updatedAt": firestore.SERVER_TIMESTAMP,  # Campo aggiuntivo per compatibilità
                "importedFrom": imported_from,
                "requiresReview": requires_review,
            }
        )
        return new_doc_ref.id, True

    def list_by_name(self, host_id: str, property_name: str) -> List[dict[str, Any]]:
        query = (
            self._client.collection("properties")
            .where("hostId", "==", host_id)
            .where("name", "==", property_name.strip())
        )
        docs = list(query.get())
        results = []
        for doc in docs:
            data = doc.to_dict() or {}
            data["id"] = doc.id
            results.append(data)
        return results

    def list_imported_properties(
        self,
        host_id: str,
        *,
        imported_from: Optional[str] = None,
        requires_review: Optional[bool] = None,
    ) -> List[dict[str, Any]]:
        query = self._client.collection("properties").where("hostId", "==", host_id)
        if imported_from:
            query = query.where("importedFrom", "==", imported_from)
        if requires_review is not None:
            query = query.where("requiresReview", "==", requires_review)
        docs = list(query.get())
        results = []
        for doc in docs:
            data = doc.to_dict() or {}
            data["id"] = doc.id
            results.append(data)
        return results

    def delete_property(self, property_id: str) -> None:
        self._client.collection("properties").document(property_id).delete()

    def mark_reviewed(self, property_id: str) -> None:
        self._client.collection("properties").document(property_id).set(
            {
                "requiresReview": False,
                "lastUpdatedAt": firestore.SERVER_TIMESTAMP,
                "updatedAt": firestore.SERVER_TIMESTAMP,
            },
            merge=True,
        )

    def list_by_host(
        self,
        host_id: str,
        requires_review: Optional[bool] = None,
    ) -> List[dict[str, Any]]:
        query = self._client.collection("properties").where("hostId", "==", host_id)
        if requires_review is not None:
            query = query.where("requiresReview", "==", requires_review)
        docs = list(query.get())
        results: List[dict[str, Any]] = []
        for doc in docs:
            data = doc.to_dict() or {}
            data["id"] = doc.id
            results.append(data)
        return results

