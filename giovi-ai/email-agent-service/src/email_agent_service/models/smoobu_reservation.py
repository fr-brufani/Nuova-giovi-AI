"""Modelli dati per Smoobu API."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class SmoobuApartment:
    """Informazioni apartment/property da Smoobu API."""
    
    id: int
    name: str
    location: Optional[Dict[str, Any]] = None
    rooms: Optional[Dict[str, Any]] = None
    currency: Optional[str] = None
    price: Optional[Dict[str, str]] = None
    type: Optional[Dict[str, Any]] = None
    time_zone: Optional[str] = None


@dataclass
class SmoobuReservation:
    """Rappresenta una prenotazione dalla Smoobu API."""
    
    id: int
    reference_id: Optional[str] = None  # reference-id
    type: str = "reservation"  # reservation, modification, cancellation
    arrival: datetime = None
    departure: datetime = None
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    apartment: Dict[str, Any] = field(default_factory=dict)  # {id, name}
    channel: Optional[Dict[str, Any]] = None  # {id, name}
    guest_name: str = ""
    email: str = ""
    phone: Optional[str] = None
    adults: int = 1
    children: int = 0
    check_in: Optional[str] = None  # HH:ii format
    check_out: Optional[str] = None  # HH:ii format
    notice: Optional[str] = None
    assistant_notice: Optional[str] = None
    price: Optional[float] = None
    price_paid: Optional[str] = None  # "Yes"/"No"
    prepayment: Optional[float] = None
    prepayment_paid: Optional[str] = None
    deposit: Optional[float] = None
    deposit_paid: Optional[str] = None
    language: Optional[str] = None
    guest_app_url: Optional[str] = None
    is_blocked_booking: bool = False
    guest_id: Optional[int] = None
    related: list = field(default_factory=list)  # Related apartments
    price_elements: list = field(default_factory=list)  # Price elements array
    
    @property
    def apartment_id(self) -> Optional[int]:
        """Restituisce l'ID dell'apartment."""
        return self.apartment.get("id") if isinstance(self.apartment, dict) else None
    
    @property
    def apartment_name(self) -> Optional[str]:
        """Restituisce il nome dell'apartment."""
        return self.apartment.get("name") if isinstance(self.apartment, dict) else None
    
    @property
    def reservation_id(self) -> str:
        """Restituisce l'ID prenotazione come stringa."""
        return str(self.id)
    
    def to_firestore_format(self, host_id: str, client_id: str, property_id: str) -> dict:
        """
        Converte SmoobuReservation in formato Firestore.
        
        Args:
            host_id: ID dell'host
            client_id: ID del cliente (già creato/trovato)
            property_id: ID della property interna
            
        Returns:
            dict con struttura reservation per Firestore
        """
        data = {
            "reservationId": self.reservation_id,
            "hostId": host_id,
            "propertyId": property_id,
            "propertyName": self.apartment_name or "",
            "clientId": client_id,
            "clientName": self.guest_name,
            "startDate": self.arrival,
            "endDate": self.departure,
            "status": "confirmed" if self.type == "reservation" else ("cancelled" if self.type == "cancellation" else "confirmed"),
            "totalPrice": self.price,
            "adults": self.adults,
            "children": self.children,
            "importedFrom": "smoobu_api",
            "lastUpdatedAt": self.modified_at or self.created_at,
        }
        
        # Aggiungi campi opzionali
        if self.reference_id:
            data["referenceId"] = self.reference_id
        if self.phone:
            data["guestPhone"] = self.phone
        if self.check_in:
            data["checkInTime"] = self.check_in
        if self.check_out:
            data["checkOutTime"] = self.check_out
        if self.notice:
            data["notice"] = self.notice
        if self.language:
            data["language"] = self.language
        if self.channel:
            data["sourceChannel"] = self.channel.get("name", "smoobu")
        
        # Aggiungi campo per identificare apartment Smoobu
        if self.apartment_id:
            data["smoobuApartmentId"] = self.apartment_id
        
        return data

