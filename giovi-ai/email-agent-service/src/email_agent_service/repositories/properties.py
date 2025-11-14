from __future__ import annotations

from typing import Optional

from firebase_admin import firestore


class PropertiesRepository:
    """Repository per gestire properties in Firestore.
    
    Le properties sono salvate in: properties/{propertyId}
    con campo hostId per filtrare per host.
    """

    def __init__(self, client: firestore.Client):
        self._client = client

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
        new_doc_ref.set(
            {
                "name": trimmed_name,
                "hostId": host_id,
                "createdAt": firestore.SERVER_TIMESTAMP,
                "lastUpdatedAt": firestore.SERVER_TIMESTAMP,
                "updatedAt": firestore.SERVER_TIMESTAMP,  # Campo aggiuntivo per compatibilità
                "importedFrom": imported_from,
            }
        )
        return new_doc_ref.id, True

