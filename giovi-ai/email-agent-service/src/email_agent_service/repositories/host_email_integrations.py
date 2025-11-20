from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Sequence

from firebase_admin import firestore


@dataclass
class HostEmailIntegrationRecord:
    email: str
    host_id: str
    provider: str
    encrypted_access_token: str
    encrypted_refresh_token: Optional[str]
    scopes: Sequence[str]
    token_expiry: Optional[datetime]
    status: str = "connected"
    last_history_id_processed: Optional[str] = None
    watch_subscription: Optional[dict] = None


class HostEmailIntegrationRepository:
    COLLECTION = "hostEmailIntegrations"

    def __init__(self, client: firestore.Client):
        self._collection = client.collection(self.COLLECTION)

    def upsert_integration(self, record: HostEmailIntegrationRecord) -> None:
        doc_ref = self._collection.document(record.email)
        doc_data = {
                "emailAddress": record.email,
                "hostId": record.host_id,
                "provider": record.provider,
                "encryptedAccessToken": record.encrypted_access_token,
                "encryptedRefreshToken": record.encrypted_refresh_token,
                "scopes": list(record.scopes),
                "status": record.status,
                "tokenExpiryDate": record.token_expiry,
                "updatedAt": firestore.SERVER_TIMESTAMP,
        }
        
        # Aggiungi campi watch se presenti
        if record.last_history_id_processed:
            doc_data["lastHistoryIdProcessed"] = record.last_history_id_processed
        if record.watch_subscription:
            # watch_subscription viene gestito da update_watch_subscription
            watch_sub = record.watch_subscription.copy()
            doc_data["watchSubscription"] = watch_sub
        
        doc_ref.set(doc_data, merge=True)

        doc_ref.set(
            {
                "createdAt": firestore.SERVER_TIMESTAMP,
            },
            merge=True,
        )
    
    def update_access_token(self, email: str, encrypted_token: str) -> None:
        """Aggiorna l'access token criptato in Firestore."""
        doc_ref = self._collection.document(email)
        doc_ref.update(
            {
                "encryptedAccessToken": encrypted_token,
                "updatedAt": firestore.SERVER_TIMESTAMP,
            }
        )

    def update_watch_subscription(
        self,
        email: str,
        history_id: str,
        expiration_ms: int,
    ) -> None:
        """Aggiorna watch subscription in Firestore."""
        doc_ref = self._collection.document(email)
        # Assicurati che expiration_ms sia int (può arrivare come stringa)
        if isinstance(expiration_ms, str):
            expiration_ms = int(expiration_ms)
        elif not isinstance(expiration_ms, (int, float)):
            expiration_ms = int(expiration_ms)
        
        # Converti millisecondi in datetime UTC (Firestore lo convertirà automaticamente in Timestamp)
        expiration_timestamp = datetime.fromtimestamp(float(expiration_ms) / 1000.0, tz=timezone.utc)
        doc_ref.update(
            {
                "watchSubscription": {
                    "historyId": history_id,
                    "expiration": expiration_timestamp,
                },
                "lastHistoryIdProcessed": history_id,
                "status": "active",
                "updatedAt": firestore.SERVER_TIMESTAMP,
            }
        )

    def get_by_email(self, email: str) -> Optional[HostEmailIntegrationRecord]:
        snapshot = self._collection.document(email).get()
        if not snapshot.exists:
            return None
        data = snapshot.to_dict() or {}
        
        # Converti token_expiry a datetime timezone-aware (UTC) se presente
        token_expiry = data.get("tokenExpiryDate")
        if token_expiry:
            if isinstance(token_expiry, datetime):
                # Se è già un datetime, assicurati che sia timezone-aware
                if token_expiry.tzinfo is None:
                    token_expiry = token_expiry.replace(tzinfo=timezone.utc)
                else:
                    token_expiry = token_expiry.astimezone(timezone.utc)
            elif hasattr(token_expiry, "toDate"):
                # Firestore Timestamp
                token_expiry = token_expiry.toDate()
                if token_expiry.tzinfo is None:
                    token_expiry = token_expiry.replace(tzinfo=timezone.utc)
                else:
                    token_expiry = token_expiry.astimezone(timezone.utc)
        
        # Converti watchSubscription expiration da Timestamp a datetime se necessario
        watch_subscription = data.get("watchSubscription")
        if watch_subscription and isinstance(watch_subscription, dict):
            expiration = watch_subscription.get("expiration")
            if expiration and hasattr(expiration, "toDate"):
                # Firestore Timestamp
                watch_subscription = watch_subscription.copy()
                watch_subscription["expiration"] = expiration.toDate()
        
        return HostEmailIntegrationRecord(
            email=data.get("emailAddress") or email,
            host_id=data.get("hostId"),
            provider=data.get("provider", "gmail"),
            encrypted_access_token=data.get("encryptedAccessToken", ""),
            encrypted_refresh_token=data.get("encryptedRefreshToken"),
            scopes=data.get("scopes") or [],
            token_expiry=token_expiry,
            status=data.get("status", "connected"),
            last_history_id_processed=data.get("lastHistoryIdProcessed"),
            watch_subscription=watch_subscription,
        )
    
    def delete_integration(self, email: str) -> None:
        """Elimina un'integrazione Gmail da Firestore."""
        doc_ref = self._collection.document(email)
        doc_ref.delete()

