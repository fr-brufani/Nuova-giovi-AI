from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from firebase_admin import firestore


@dataclass
class OAuthStateRecord:
    state: str
    host_uid: str
    expires_at: datetime


class OAuthStateRepository:
    COLLECTION = "oauthStates"

    def __init__(self, client: firestore.Client):
        self._collection = client.collection(self.COLLECTION)

    def create_state(self, record: OAuthStateRecord) -> None:
        doc_ref = self._collection.document(record.state)
        doc_ref.set(
            {
                "hostUid": record.host_uid,
                "createdAt": firestore.SERVER_TIMESTAMP,
                "expiresAt": record.expires_at,
            }
        )

    def get_state(self, state: str) -> Optional[OAuthStateRecord]:
        doc = self._collection.document(state).get()
        if not doc.exists:
            return None
        data = doc.to_dict() or {}
        expires_at = data.get("expiresAt")
        if isinstance(expires_at, datetime):
            expires_at = expires_at.astimezone(timezone.utc)
        else:
            expires_at = datetime.now(timezone.utc)
        host_uid = data.get("hostUid")
        if not host_uid:
            return None
        return OAuthStateRecord(state=state, host_uid=host_uid, expires_at=expires_at)

    def delete_state(self, state: str) -> None:
        self._collection.document(state).delete()

    def delete_expired_states(self) -> int:
        """Elimina tutti gli state scaduti. Ritorna il numero di state eliminati."""
        now = datetime.now(timezone.utc)
        deleted_count = 0
        
        # Query per trovare tutti gli state scaduti
        expired_states = self._collection.where("expiresAt", "<", now).get()
        
        for state_doc in expired_states:
            state_doc.reference.delete()
            deleted_count += 1
        
        return deleted_count

