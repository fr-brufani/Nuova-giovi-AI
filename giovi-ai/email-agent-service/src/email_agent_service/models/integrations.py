from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, HttpUrl


class GmailIntegrationStartRequest(BaseModel):
    host_id: str = Field(..., alias="hostId", min_length=1)
    email: EmailStr
    pms_provider: Optional[str] = Field(default=None, alias="pmsProvider")
    redirect_uri: Optional[HttpUrl] = Field(default=None, alias="redirectUri")


class GmailIntegrationStartResponse(BaseModel):
    authorization_url: HttpUrl = Field(..., alias="authorizationUrl")
    state: str
    expires_at: datetime = Field(..., alias="expiresAt")


class GmailCallbackRequest(BaseModel):
    state: str
    code: str
    host_id: str = Field(..., alias="hostId", min_length=1)
    email: EmailStr
    pms_provider: Optional[str] = Field(default=None, alias="pmsProvider")
    redirect_uri: Optional[HttpUrl] = Field(default=None, alias="redirectUri")


class GmailCallbackResponse(BaseModel):
    status: str
    host_id: str = Field(..., alias="hostId")
    email: EmailStr
    provider: str = "gmail"


class GmailWatchRequest(BaseModel):
    topic_name: Optional[str] = Field(default=None, alias="topicName")


class GmailWatchResponse(BaseModel):
    history_id: str = Field(..., alias="historyId")
    expiration: int  # Millisecondi da epoch
    status: str = "active"


class GmailNotificationPayload(BaseModel):
    """Payload della notifica Pub/Sub da Gmail."""
    email_address: str = Field(..., alias="emailAddress")
    history_id: str = Field(..., alias="historyId")

