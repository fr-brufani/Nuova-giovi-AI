from __future__ import annotations

from typing import Optional

from firebase_admin import firestore


class ClientsRepository:
    """Repository per gestire clienti (guests) in Firestore.
    
    I clienti sono salvati in: clients/{clientId}
    con role="guest"
    """

    def __init__(self, client: firestore.Client):
        self._client = client

    def find_or_create_by_email(
        self,
        host_id: str,
        email: Optional[str],
        name: Optional[str],
        phone: Optional[str] = None,
        property_id: Optional[str] = None,
        reservation_id: Optional[str] = None,
        imported_from: str = "scidoo_email",
    ) -> tuple[Optional[str], bool]:
        """
        Trova o crea un cliente per email.
        
        Se email è None, cerca per nome (meno affidabile).
        
        Args:
            host_id: ID dell'host
            email: Email del cliente
            name: Nome del cliente
            phone: Telefono del cliente
            property_id: ID della property associata (opzionale)
            reservation_id: ID della prenotazione associata (opzionale)
            imported_from: Fonte dell'import
        
        Returns:
            tuple[client_id, was_created]: ID del cliente e se è stato creato
        """
        clients_ref = self._client.collection("clients")

        # Se abbiamo email, cerca per email
        if email:
            query = clients_ref.where("email", "==", email.lower()).limit(1)
            docs = query.get()

            # Controlla se ci sono risultati (QueryResultsList non ha .empty)
            docs_list = list(docs)
            if docs_list:
                doc = docs_list[0]
                # Aggiorna dati se necessario
                updates = {
                    "lastUpdatedAt": firestore.SERVER_TIMESTAMP,
                    "assignedHostId": host_id,
                }
                if name:
                    updates["name"] = name
                if phone:
                    updates["whatsappPhoneNumber"] = phone
                if property_id:
                    updates["assignedPropertyId"] = property_id
                if reservation_id:
                    updates["reservationId"] = reservation_id

                doc.reference.set(updates, merge=True)
                return doc.id, False

        # Se non trovato per email, cerca per nome (se disponibile)
        if name:
            query = (
                clients_ref.where("name", "==", name)
                .where("assignedHostId", "==", host_id)
                .limit(1)
            )
            docs = query.get()

            # Controlla se ci sono risultati (QueryResultsList non ha .empty)
            docs_list = list(docs)
            if docs_list:
                doc = docs_list[0]
                updates = {
                    "lastUpdatedAt": firestore.SERVER_TIMESTAMP,
                }
                if email:
                    updates["email"] = email.lower()
                if phone:
                    updates["whatsappPhoneNumber"] = phone
                if property_id:
                    updates["assignedPropertyId"] = property_id
                if reservation_id:
                    updates["reservationId"] = reservation_id

                doc.reference.set(updates, merge=True)
                return doc.id, False

        # Crea nuovo cliente
        new_doc_ref = clients_ref.document()
        client_data = {
            "role": "guest",
            "assignedHostId": host_id,
            "createdAt": firestore.SERVER_TIMESTAMP,
            "lastUpdatedAt": firestore.SERVER_TIMESTAMP,
            "importedFrom": imported_from,
            "autoReplyEnabled": False,  # Default: autoreply disabilitato per nuovi clienti
        }

        if name:
            client_data["name"] = name
        if email:
            client_data["email"] = email.lower()
        if phone:
            client_data["whatsappPhoneNumber"] = phone
        if property_id:
            client_data["assignedPropertyId"] = property_id
        if reservation_id:
            client_data["reservationId"] = reservation_id

        new_doc_ref.set(client_data)
        return new_doc_ref.id, True

    def reassign_property(
        self,
        host_id: str,
        from_property_id: str,
        to_property_id: str,
    ) -> int:
        """Aggiorna tutti i clienti assegnati alla property di origine."""
        clients_ref = self._client.collection("clients")
        query = (
            clients_ref.where("assignedHostId", "==", host_id)
            .where("assignedPropertyId", "==", from_property_id)
        )
        docs = list(query.get())
        updated = 0
        for doc in docs:
            doc.reference.set(
                {
                    "assignedPropertyId": to_property_id,
                    "lastUpdatedAt": firestore.SERVER_TIMESTAMP,
                },
                merge=True,
            )
            updated += 1
        return updated

    def unassign_property(
        self,
        host_id: str,
        property_id: str,
    ) -> int:
        """Rimuove l'associazione dei clienti a una property (imposta assignedPropertyId a null).
        
        Returns:
            Numero di clienti aggiornati.
        """
        clients_ref = self._client.collection("clients")
        query = (
            clients_ref.where("assignedHostId", "==", host_id)
            .where("assignedPropertyId", "==", property_id)
        )
        docs = list(query.get())
        updated = 0
        for doc in docs:
            doc.reference.set(
                {
                    "assignedPropertyId": firestore.DELETE_FIELD,
                    "lastUpdatedAt": firestore.SERVER_TIMESTAMP,
                },
                merge=True,
            )
            updated += 1
        return updated

    def delete_by_property(
        self,
        host_id: str,
        property_id: str,
    ) -> int:
        """Elimina tutti i clienti associati a una property.
        
        Returns:
            Numero di clienti eliminati.
        """
        clients_ref = self._client.collection("clients")
        query = (
            clients_ref.where("assignedHostId", "==", host_id)
            .where("assignedPropertyId", "==", property_id)
        )
        docs = list(query.get())
        deleted = 0
        for doc in docs:
            doc.reference.delete()
            deleted += 1
        return deleted

