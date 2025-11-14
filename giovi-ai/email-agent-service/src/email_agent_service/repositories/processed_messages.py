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

