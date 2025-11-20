"""Modelli dati per Booking.com Messaging API."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class BookingSender:
    """Informazioni sul mittente del messaggio."""
    
    participant_id: str
    participant_type: str  # "GUEST" o "property"
    name: Optional[str] = None
    email_alias: Optional[str] = None


@dataclass
class BookingConversation:
    """Informazioni sulla conversazione."""
    
    conversation_id: str
    conversation_type: str  # "reservation" o "request_to_book"
    conversation_reference: str  # reservation_id per conversazioni reservation
    property_id: Optional[str] = None


@dataclass
class BookingMessageAttributes:
    """Attributi aggiuntivi del messaggio (v1.2)."""
    
    self_service_topic: Optional[str] = None  # checkin, checkout, parking, etc.
    template_id: Optional[str] = None
    template_name: Optional[str] = None


@dataclass
class BookingMessage:
    """Rappresenta un messaggio dalla Booking.com Messaging API."""
    
    message_id: str
    content: str
    timestamp: datetime
    sender: BookingSender
    conversation: BookingConversation
    message_type: Optional[str] = None  # free_text, email, automatically_sent_template, self_service_event
    attachment_ids: List[str] = field(default_factory=list)
    attributes: Optional[BookingMessageAttributes] = None
    
    @classmethod
    def from_api_response(cls, data: dict) -> "BookingMessage":
        """Crea BookingMessage da response API Booking.com."""
        sender_data = data.get("sender", {})
        sender_metadata = sender_data.get("metadata", {})
        
        conversation_data = data.get("conversation", {})
        
        attributes_data = data.get("attributes")
        attributes = None
        if attributes_data:
            attributes = BookingMessageAttributes(
                self_service_topic=attributes_data.get("self_service_topic"),
                template_id=attributes_data.get("template_id"),
                template_name=attributes_data.get("template_name"),
            )
        
        return cls(
            message_id=data["message_id"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00")),
            sender=BookingSender(
                participant_id=sender_data["participant_id"],
                participant_type=sender_metadata.get("participant_type", ""),
                name=sender_metadata.get("name"),
                email_alias=sender_metadata.get("email_alias"),
            ),
            conversation=BookingConversation(
                conversation_id=conversation_data["conversation_id"],
                conversation_type=conversation_data["conversation_type"],
                conversation_reference=conversation_data.get("conversation_reference", ""),
                property_id=conversation_data.get("property_id"),
            ),
            message_type=data.get("message_type"),
            attachment_ids=data.get("attachment_ids", []),
            attributes=attributes,
        )
    
    def to_internal_format(self) -> dict:
        """
        Converte BookingMessage in formato interno compatibile con GuestMessageInfo.
        
        Returns:
            dict con struttura simile a ParsedEmail per integrazione con pipeline esistente
        """
        return {
            "kind": "booking_message",
            "source": "booking_api",
            "reservation_id": self.conversation.conversation_reference,
            "message": self.content,
            "guest_name": self.sender.name if self.sender.participant_type == "GUEST" else None,
            "guest_email": self.sender.email_alias if self.sender.participant_type == "GUEST" else None,
            "message_id": self.message_id,
            "conversation_id": self.conversation.conversation_id,
            "property_id": self.conversation.property_id,
            "timestamp": self.timestamp.isoformat(),
            "message_type": self.message_type,
        }
    
    def to_guest_message_info_format(self) -> dict:
        """
        Converte BookingMessage in formato GuestMessageInfo per compatibilità con pipeline esistente.
        
        Returns:
            dict con struttura GuestMessageInfo
        """
        from .parsing import GuestMessageInfo
        
        return GuestMessageInfo(
            reservationId=self.conversation.conversation_reference,
            source="booking",
            message=self.content,
            replyTo=self.sender.email_alias if self.sender.email_alias else None,
            threadId=None,  # Booking non usa thread_id come Airbnb
            guestName=self.sender.name if self.sender.participant_type == "GUEST" else None,
            guestEmail=self.sender.email_alias if self.sender.participant_type == "GUEST" else None,
        ).model_dump(by_alias=True)

