from functools import lru_cache
from typing import List, Optional, Union

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    firebase_project_id: Optional[str] = Field(
        default=None,
        alias="AGENCY_FIREBASE_PROJECT_ID",
        description="Se non impostato usa lo stesso project del service account Google",
    )
    default_plan_version: str = Field("v0.1", alias="AGENCY_DEFAULT_PLAN_VERSION")
    allowed_origins: List[str] = Field(default_factory=list, alias="AGENCY_ALLOWED_ORIGINS")

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: Union[List[str], str]) -> List[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def _load_settings() -> Settings:
    return Settings()


settings = _load_settings()

