import json
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, Json, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class FirebaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    credentials_path: Optional[str] = Field(
        default=None,
        validation_alias="FIREBASE_CREDENTIALS_PATH",
        description="Absolute path to the Firebase service account json file.",
    )
    credentials_json: Optional[Json[dict]] = Field(
        default=None,
        validation_alias="FIREBASE_CREDENTIALS_JSON",
        description="Service account JSON payload encoded as string.",
    )
    project_id: Optional[str] = Field(
        default=None,
        validation_alias="FIREBASE_PROJECT_ID",
        description="Target Firebase/GCP project id.",
    )

class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = Field(default="local", validation_alias="APP_ENV")
    firebase: FirebaseSettings = Field(default_factory=FirebaseSettings)
    token_encryption_key: str = Field(..., validation_alias="TOKEN_ENCRYPTION_KEY")
    google_oauth_client_id: str = Field(..., validation_alias="GOOGLE_OAUTH_CLIENT_ID")
    google_oauth_client_secret: str = Field(..., validation_alias="GOOGLE_OAUTH_CLIENT_SECRET")
    google_oauth_redirect_uri: Optional[str] = Field(
        default=None, validation_alias="GOOGLE_OAUTH_REDIRECT_URI"
    )
    google_oauth_scopes: List[str] = Field(
        default_factory=lambda: [
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.readonly",
        ],
        validation_alias="GOOGLE_OAUTH_SCOPES",
    )
    gmail_pubsub_topic: Optional[str] = Field(
        default=None,
        validation_alias="GMAIL_PUBSUB_TOPIC",
        description="Nome completo del topic Pub/Sub per Gmail Watch (es: projects/PROJECT_ID/topics/TOPIC_NAME)",
    )

    @field_validator("google_oauth_scopes", mode="before")
    @classmethod
    def parse_scopes(cls, value: object) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            # accept comma separated values or JSON array
            value = value.strip()
            if not value:
                return []
            if value.startswith("["):
                parsed = json.loads(value)
                if not isinstance(parsed, list):
                    raise TypeError("GOOGLE_OAUTH_SCOPES JSON must be an array")
                return [str(item) for item in parsed]
            return [scope.strip() for scope in value.split(",") if scope.strip()]
        raise TypeError("Unsupported GOOGLE_OAUTH_SCOPES format")


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()

