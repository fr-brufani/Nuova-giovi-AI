from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, HttpUrl


class GmailIntegrationStartRequest(BaseModel):
    host_id: str = Field(..., alias="hostId", min_length=1)
    email: EmailStr
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


# Scidoo API Integration Models
class ScidooConfigureRequest(BaseModel):
    """Request per configurare integrazione Scidoo."""
    api_key: str = Field(..., alias="apiKey", min_length=1)
    trigger_sync: bool = Field(default=True, alias="triggerSync")


class ScidooConfigureResponse(BaseModel):
    """Response configurazione Scidoo."""
    host_id: str = Field(..., alias="hostId")
    connected: bool
    account_name: Optional[str] = Field(None, alias="accountName")
    properties_count: int = Field(0, alias="propertiesCount")
    sync_triggered: bool = Field(False, alias="syncTriggered")


class ScidooSyncRequest(BaseModel):
    """Request per sync massivo Scidoo."""
    checkin_from: Optional[str] = Field(None, alias="checkinFrom", description="Data inizio YYYY-MM-DD")
    checkin_to: Optional[str] = Field(None, alias="checkinTo", description="Data fine YYYY-MM-DD")


class ScidooSyncResponse(BaseModel):
    """Response sync Scidoo."""
    processed: int
    skipped: int
    errors: int
    reservations: list[dict] = Field(default_factory=list)


class ScidooTestRequest(BaseModel):
    """Request per test connessione Scidoo."""
    api_key: Optional[str] = Field(None, alias="apiKey", description="API key opzionale per test senza salvataggio")


class ScidooTestResponse(BaseModel):
    """Response test connessione Scidoo."""
    connected: bool
    account_name: Optional[str] = Field(None, alias="accountName")
    properties_count: int = Field(0, alias="propertiesCount")
    error: Optional[str] = None


class ScidooRoomType(BaseModel):
    """Room type Scidoo."""
    id: int
    name: str
    description: Optional[str] = None
    size: Optional[int] = None
    capacity: Optional[int] = None
    additional_beds: Optional[int] = Field(None, alias="additionalBeds")
    images: list[str] = Field(default_factory=list)


class ScidooRoomTypesResponse(BaseModel):
    """Response lista room types Scidoo."""
    room_types: list[ScidooRoomType] = Field(..., alias="roomTypes")

