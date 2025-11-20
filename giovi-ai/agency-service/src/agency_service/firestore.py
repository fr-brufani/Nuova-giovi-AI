from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional

from google.cloud import firestore
from google.cloud.firestore import Client

from .config import settings

_client: Optional[Client] = None


def get_client() -> Client:
    global _client
    if _client is None:
        if settings.firebase_project_id:
            _client = firestore.Client(project=settings.firebase_project_id)
        else:
            _client = firestore.Client()
    return _client


def serialize_document(doc: firestore.DocumentSnapshot) -> Dict[str, Any]:
    data = doc.to_dict() or {}
    data["id"] = doc.id
    return _convert_timestamps(data)


def _convert_timestamps(data: Dict[str, Any]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, datetime):
            result[key] = value.astimezone(timezone.utc).isoformat()
        elif isinstance(value, list):
            result[key] = [_convert_timestamps(v) if isinstance(v, dict) else v for v in value]
        elif isinstance(value, dict):
            result[key] = _convert_timestamps(value)
        else:
            result[key] = value
    return result


def add_timestamps(payload: Dict[str, Any], is_update: bool = False) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    payload = payload.copy()
    payload["updatedAt"] = now
    if not is_update:
        payload.setdefault("createdAt", now)
    return payload


def batch_fetch(collection: str, filters: Iterable[tuple[str, str, Any]]) -> list[Dict[str, Any]]:
    query = get_client().collection(collection)
    for field, op, value in filters:
        query = query.where(field, op, value)
    docs = query.stream()
    return [serialize_document(doc) for doc in docs]

