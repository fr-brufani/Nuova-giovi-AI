import json
from functools import lru_cache
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet, InvalidToken

from ..config.settings import get_settings


@lru_cache
def _get_fernet() -> Fernet:
    key = get_settings().token_encryption_key
    return Fernet(key)


def encrypt_text(value: str) -> str:
    fernet = _get_fernet()
    return fernet.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_text(token: str) -> str:
    fernet = _get_fernet()
    try:
        return fernet.decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:  # pragma: no cover
        raise ValueError("Invalid encryption token provided") from exc


def encrypt_dict(value: Dict[str, Any]) -> str:
    return encrypt_text(json.dumps(value, separators=(",", ":")))


def decrypt_dict(token: str) -> Dict[str, Any]:
    return json.loads(decrypt_text(token))


def encrypt_optional_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    return encrypt_text(value)


def decrypt_optional_text(token: Optional[str]) -> Optional[str]:
    if token is None:
        return None
    return decrypt_text(token)

