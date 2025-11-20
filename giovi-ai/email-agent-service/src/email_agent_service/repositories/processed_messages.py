from __future__ import annotations

from typing import Optional

from firebase_admin import firestore


class ProcessedMessageRepository:
    SUBCOLLECTION = "processedMessageIds"

    def __init__(self, client: firestore.Client):
        self._client = client

    def _collection(self, integration_email: str):
        return (
            self._client.collection("hostEmailIntegrations")
            .document(integration_email)
            .collection(self.SUBCOLLECTION)
        )

    def was_processed(self, integration_email: str, message_id: str) -> bool:
        doc = self._collection(integration_email).document(message_id).get()
        return doc.exists

    def mark_processed(
        self,
        integration_email: str,
        message_id: str,
        *,
        history_id: Optional[str] = None,
    ) -> None:
        self._collection(integration_email).document(message_id).set(
            {
                "historyId": history_id,
                "processedAt": firestore.SERVER_TIMESTAMP,
            },
            merge=True,
        )
    
    def is_processed(
        self,
        message_id: str,
        host_id: str,
        source: str,
    ) -> bool:
        """
        Verifica se un messaggio è già stato processato (per Booking.com API).
        
        Args:
            message_id: Message ID (Booking.com message_id)
            host_id: Host ID
            source: Source identifier ("booking_api", "airbnb_api", etc.)
            
        Returns:
            True se già processato, False altrimenti
        """
        # Usa collection dedicata per messages processati via API
        collection_ref = (
            self._client
            .collection("processedBookingMessages")
            .document(host_id)
            .collection(source)
        )
        doc = collection_ref.document(message_id).get()
        return doc.exists
    
    def mark_processed_api(
        self,
        message_id: str,
        host_id: str,
        source: str,
    ) -> None:
        """
        Marca un messaggio come processato (per Booking.com API).
        
        Args:
            message_id: Message ID (Booking.com message_id)
            host_id: Host ID
            source: Source identifier ("booking_api", "airbnb_api", etc.)
        """
        collection_ref = (
            self._client
            .collection("processedBookingMessages")
            .document(host_id)
            .collection(source)
        )
        collection_ref.document(message_id).set(
            {
                "processedAt": firestore.SERVER_TIMESTAMP,
            },
            merge=True,
        )

