"""Services per integrazioni con piattaforme esterne."""

from .booking_messaging_client import (
    BookingAuthenticationError,
    BookingForbiddenError,
    BookingMessagingClient,
    BookingRateLimitError,
)
from .booking_reservation_client import BookingReservationClient
from .scidoo_reservation_client import (
    ScidooReservationClient,
    ScidooAPIError,
    ScidooAuthenticationError,
    ScidooRateLimitError,
)
from .oauth_service import GmailOAuthService

__all__ = [
    "GmailOAuthService",
    "BookingMessagingClient",
    "BookingReservationClient",
    "BookingAuthenticationError",
    "BookingForbiddenError",
    "BookingRateLimitError",
    "ScidooReservationClient",
    "ScidooAPIError",
    "ScidooAuthenticationError",
    "ScidooRateLimitError",
]

