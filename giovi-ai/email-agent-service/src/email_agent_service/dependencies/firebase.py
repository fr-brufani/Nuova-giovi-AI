from __future__ import annotations

import json
from threading import Lock
from typing import Any, Dict, Optional, cast

import firebase_admin
from firebase_admin import credentials, firestore

from ..config.settings import FirebaseSettings, get_settings

_firebase_app: Optional[firebase_admin.App] = None
_firebase_lock = Lock()


def _load_credentials(settings: FirebaseSettings) -> credentials.Base:
    # Prefer file path se specificato (più affidabile)
    if settings.credentials_path:
        return credentials.Certificate(settings.credentials_path)

    if settings.credentials_json:
        # `credentials_json` is parsed by Pydantic as dict already, but can arrive as string during runtime.
        raw_value: Any = settings.credentials_json
        if isinstance(raw_value, str):
            raw_value = json.loads(raw_value)
        return credentials.Certificate(cast(Dict[str, Any], raw_value))

    # Fallback a Application Default Credentials se GOOGLE_APPLICATION_CREDENTIALS è settato
    return credentials.ApplicationDefault()


def _initialize_firebase_app(settings: FirebaseSettings) -> firebase_admin.App:
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    with _firebase_lock:
        if _firebase_app is not None:
            return _firebase_app

        credential = _load_credentials(settings)
        options: Dict[str, Any] = {}
        if settings.project_id:
            options["projectId"] = settings.project_id

        _firebase_app = firebase_admin.initialize_app(credential, options or None)
        return _firebase_app


def get_firestore_client() -> firestore.Client:
    settings = get_settings()
    app = _initialize_firebase_app(settings.firebase)
    return firestore.client(app)

