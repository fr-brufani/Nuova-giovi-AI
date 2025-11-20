"""Modelli dati per Booking.com Reservation API (OTA XML)."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class BookingGuestInfo:
    """Informazioni guest/booker dalla prenotazione."""
    
    name: str
    email: str
    phone: Optional[str] = None
    surname: Optional[str] = None
    given_name: Optional[str] = None


@dataclass
class BookingPaymentInfo:
    """Informazioni pagamento e VCC."""
    
    vcc_number: Optional[str] = None
    vcc_cvc: Optional[str] = None
    vcc_expiry_date: Optional[str] = None
    vcc_effective_date: Optional[datetime] = None
    vcc_current_balance: Optional[float] = None
    card_holder_name: Optional[str] = None
    is_payments_by_booking: bool = False


@dataclass
class BookingReservation:
    """Rappresenta una prenotazione dalla Booking.com Reservation API (OTA XML)."""
    
    reservation_id: str
    property_id: str
    check_in: datetime
    check_out: datetime
    guest_info: BookingGuestInfo
    adults: int
    total_amount: float
    currency: str
    children: int = 0
    room_type_code: Optional[str] = None
    room_type_name: Optional[str] = None
    rate_plan_code: Optional[str] = None
    meal_plan: Optional[str] = None
    commission_amount: Optional[float] = None
    payment_info: Optional[BookingPaymentInfo] = None
    special_requests: List[str] = field(default_factory=list)
    comments: Optional[str] = None
    reservation_date: Optional[datetime] = None  # Data creazione prenotazione
    
    def to_firestore_format(self, host_id: str, client_id: str) -> dict:
        """
        Converte BookingReservation in formato Firestore.
        
        Args:
            host_id: ID dell'host
            client_id: ID del cliente (già creato/trovato)
            
        Returns:
            dict con struttura reservation per Firestore
        """
        return {
            "reservationId": self.reservation_id,
            "hostId": host_id,
            "propertyId": self.property_id,
            "clientId": client_id,
            "channel": "booking",
            "status": "confirmed",
            "stayPeriod": {
                "start": self.check_in.isoformat(),
                "end": self.check_out.isoformat(),
            },
            "totals": {
                "amount": self.total_amount,
                "currency": self.currency,
            },
            "guests": {
                "adults": self.adults,
                "children": self.children,
            },
            "source": {
                "provider": "booking-api",
                "externalId": self.reservation_id,
            },
            "importedFrom": "booking_api",
            "createdAt": self.reservation_date.isoformat() if self.reservation_date else None,
            "bookingMetadata": {
                "roomTypeCode": self.room_type_code,
                "roomTypeName": self.room_type_name,
                "ratePlanCode": self.rate_plan_code,
                "mealPlan": self.meal_plan,
                "commissionAmount": self.commission_amount,
                "specialRequests": self.special_requests,
                "comments": self.comments,
            },
        }
    
    def to_internal_format(self) -> dict:
        """
        Converte in formato interno compatibile con ReservationInfo.
        
        Returns:
            dict con struttura ReservationInfo
        """
        return {
            "reservationId": self.reservation_id,
            "source": "booking",
            "propertyName": None,  # Sarà popolato da property lookup
            "propertyExternalId": self.property_id,
            "checkIn": self.check_in,
            "checkOut": self.check_out,
            "guestName": self.guest_info.name,
            "guestEmail": self.guest_info.email,
            "guestPhone": self.guest_info.phone,
            "adults": self.adults,
            "children": self.children,
            "totalAmount": self.total_amount,
            "currency": self.currency,
        }

