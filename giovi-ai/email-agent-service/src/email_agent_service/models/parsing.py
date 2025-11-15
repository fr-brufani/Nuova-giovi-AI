from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ReservationInfo(BaseModel):
    reservation_id: str = Field(..., alias="reservationId")
    source: Literal["booking", "airbnb", "scidoo"]
    voucher_id: Optional[str] = Field(default=None, alias="voucherId")  # ID Voucher da Booking/Scidoo
    source_channel: Optional[Literal["booking", "airbnb"]] = Field(default=None, alias="sourceChannel")  # Canale: Booking o Airbnb (da subject email Scidoo)
    thread_id: Optional[str] = Field(default=None, alias="threadId")  # Thread ID per Airbnb (per matchare messaggi)
    property_name: Optional[str] = Field(default=None, alias="propertyName")
    property_external_id: Optional[str] = Field(default=None, alias="propertyExternalId")
    check_in: Optional[datetime] = Field(default=None, alias="checkIn")
    check_out: Optional[datetime] = Field(default=None, alias="checkOut")
    guest_name: Optional[str] = Field(default=None, alias="guestName")
    guest_email: Optional[str] = Field(default=None, alias="guestEmail")
    guest_phone: Optional[str] = Field(default=None, alias="guestPhone")
    adults: Optional[int] = None
    children: Optional[int] = None
    total_amount: Optional[float] = Field(default=None, alias="totalAmount")
    currency: Optional[str] = None


class GuestMessageInfo(BaseModel):
    reservation_id: str = Field(..., alias="reservationId")
    source: Literal["booking", "airbnb"]
    message: str
    language: Optional[str] = None
    reply_to: Optional[str] = Field(default=None, alias="replyTo")
    thread_id: Optional[str] = Field(default=None, alias="threadId")
    guest_name: Optional[str] = Field(default=None, alias="guestName")
    guest_email: Optional[str] = Field(default=None, alias="guestEmail")


class ParsedEmailMetadata(BaseModel):
    subject: Optional[str] = None
    sender: Optional[str] = None
    recipients: Optional[list[str]] = None
    received_at: Optional[datetime] = Field(default=None, alias="receivedAt")
    gmail_message_id: Optional[str] = Field(default=None, alias="gmailMessageId")
    snippet: Optional[str] = None


class ParsedEmail(BaseModel):
    kind: Literal[
        "booking_confirmation",
        "booking_message",
        "airbnb_confirmation",
        "airbnb_cancellation",
        "airbnb_message",
        "scidoo_confirmation",
        "scidoo_cancellation",
        "unhandled",
    ]
    reservation: Optional[ReservationInfo] = None
    guest_message: Optional[GuestMessageInfo] = Field(default=None, alias="guestMessage")
    metadata: ParsedEmailMetadata
    raw_text: Optional[str] = Field(default=None, alias="rawText")
    raw_html: Optional[str] = Field(default=None, alias="rawHtml")


class GmailBackfillResponse(BaseModel):
    processed: int
    items: list[ParsedEmail]

