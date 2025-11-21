from .integrations import (
    GmailCallbackRequest,
    GmailCallbackResponse,
    GmailIntegrationStartRequest,
    GmailIntegrationStartResponse,
    GmailWatchRequest,
    GmailWatchResponse,
    GmailNotificationPayload,
    ScidooConfigureRequest,
    ScidooConfigureResponse,
    ScidooSyncRequest,
    ScidooSyncResponse,
    ScidooTestRequest,
    ScidooTestResponse,
    ScidooRoomType,
    ScidooRoomTypesResponse,
)
from .booking_message import (
    BookingConversation,
    BookingMessage,
    BookingMessageAttributes,
    BookingSender,
)
from .booking_reservation import (
    BookingGuestInfo,
    BookingPaymentInfo,
    BookingReservation,
)
from .smoobu_reservation import (
    SmoobuReservation,
    SmoobuApartment,
)
from .scidoo_reservation import (
    ScidooReservation,
    ScidooCustomer,
    ScidooGuest,
)
from .parsing import (
    GmailBackfillPreviewResponse,
    GmailBackfillResponse,
    GuestMessageInfo,
    ParsedEmail,
    ParsedEmailMetadata,
    PropertyPreview,
    ReservationInfo,
    ReservationPreview,
)

__all__ = [
    "GmailIntegrationStartRequest",
    "GmailIntegrationStartResponse",
    "GmailCallbackRequest",
    "GmailCallbackResponse",
    "GmailWatchRequest",
    "GmailWatchResponse",
    "GmailNotificationPayload",
    # Scidoo integration models
    "ScidooConfigureRequest",
    "ScidooConfigureResponse",
    "ScidooSyncRequest",
    "ScidooSyncResponse",
    "ScidooTestRequest",
    "ScidooTestResponse",
    "ScidooRoomType",
    "ScidooRoomTypesResponse",
    "ParsedEmail",
    "ParsedEmailMetadata",
    "ReservationInfo",
    "GuestMessageInfo",
    "GmailBackfillResponse",
    "GmailBackfillPreviewResponse",
    "PropertyPreview",
    "ReservationPreview",
    # Booking.com models
    "BookingMessage",
    "BookingSender",
    "BookingConversation",
    "BookingMessageAttributes",
    "BookingReservation",
    "BookingGuestInfo",
    "BookingPaymentInfo",
    # Smoobu models
    "SmoobuReservation",
    "SmoobuApartment",
    # Scidoo models
    "ScidooReservation",
    "ScidooCustomer",
    "ScidooGuest",
]

