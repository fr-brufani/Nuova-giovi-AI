"""Client per Smoobu API."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from unittest.mock import Mock

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ...config.settings import get_settings
from ...models.smoobu_reservation import SmoobuReservation, SmoobuApartment

logger = logging.getLogger(__name__)


class SmoobuAPIError(Exception):
    """Errore generico API Smoobu."""
    pass


class SmoobuAuthenticationError(SmoobuAPIError):
    """Errore autenticazione API Smoobu (401)."""
    pass


class SmoobuForbiddenError(SmoobuAPIError):
    """Errore accesso negato API Smoobu (403)."""
    pass


class SmoobuRateLimitError(SmoobuAPIError):
    """Errore rate limit API Smoobu (429)."""
    pass


class SmoobuClient:
    """Client per Smoobu API con supporto mock mode."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        mock_mode: Optional[bool] = None,
    ) -> None:
        """
        Inizializza client Smoobu API.
        
        Args:
            api_key: API Key Smoobu (opzionale se mock_mode=True)
            base_url: Base URL API (default da settings)
            mock_mode: Se True, usa mock responses invece di chiamate reali
        """
        self._settings = get_settings()
        self.api_key = api_key or self._settings.smoobu_api_key
        self.base_url = base_url or self._settings.smoobu_api_base_url
        
        # Mock mode se non ci sono credenziali o esplicitamente richiesto
        self.mock_mode = (
            mock_mode if mock_mode is not None else not self.api_key
        )
        
        if self.mock_mode:
            logger.info("[SmoobuClient] Initialized in MOCK MODE - using mock JSON responses")
            self._init_mock_responses()
        else:
            logger.info(f"[SmoobuClient] Initialized in PRODUCTION MODE - API: {self.base_url}")
            self._init_session()
    
    def _init_session(self) -> None:
        """Inizializza session HTTP con retry logic."""
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
    
    def _init_mock_responses(self) -> None:
        """Inizializza mock JSON responses per sviluppo senza credenziali."""
        self._mock_user_response = {
            "id": 7,
            "firstName": "Test",
            "lastName": "User",
            "email": "test@smoobu.com"
        }
        
        self._mock_apartments_response = {
            "apartments": [
                {"id": 101, "name": "Test Apartment 1"},
                {"id": 102, "name": "Test Apartment 2"},
            ]
        }
        
        self._mock_reservations_response = {
            "page_count": 1,
            "page_size": 25,
            "total_items": 2,
            "page": 1,
            "bookings": [
                {
                    "id": 291,
                    "reference-id": None,
                    "type": "reservation",
                    "arrival": "2025-03-15",
                    "departure": "2025-03-18",
                    "created-at": "2025-01-15 13:51",
                    "modified-at": "2025-01-15 13:51",
                    "apartment": {"id": 101, "name": "Test Apartment 1"},
                    "channel": {"id": 70, "name": "Homepage"},
                    "guest-name": "Test Guest",
                    "email": "test.guest@example.com",
                    "phone": "+49123456789",
                    "adults": 2,
                    "children": 0,
                    "check-in": "16:00",
                    "check-out": "10:00",
                    "notice": "",
                    "price": 150,
                    "price-paid": "Yes",
                    "prepayment": 0,
                    "prepayment-paid": "No",
                    "deposit": 0,
                    "deposit-paid": "No",
                    "language": "en",
                    "guest-app-url": "https://guest.smoobu.com/?t=test&b=291",
                    "is-blocked-booking": False,
                    "guestId": 155,
                    "related": []
                }
            ]
        }
    
    def _request(
        self, method: str, endpoint: str, params: Optional[dict] = None, json_data: Optional[dict] = None
    ) -> requests.Response:
        """
        Esegue richiesta HTTP con gestione errori e retry.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: Endpoint path (es: "/api/reservations")
            params: Query parameters
            json_data: JSON body per POST/PUT
            
        Returns:
            Response object con JSON content
            
        Raises:
            SmoobuAuthenticationError: 401
            SmoobuForbiddenError: 403
            SmoobuRateLimitError: 429
            SmoobuAPIError: Altri errori
        """
        if self.mock_mode:
            # Ritorna mock JSON response
            mock_response = Mock(spec=requests.Response)
            mock_response.status_code = 200
            
            if endpoint == "/api/me":
                mock_response.json = lambda: self._mock_user_response
            elif endpoint == "/api/apartments":
                mock_response.json = lambda: self._mock_apartments_response
            elif endpoint.startswith("/api/reservations"):
                mock_response.json = lambda: self._mock_reservations_response
            else:
                mock_response.json = lambda: {}
            
            mock_response.text = str(mock_response.json())
            mock_response.raise_for_status = lambda: None
            logger.debug(f"[MOCK] {method} {endpoint} -> mock JSON response")
            return mock_response
        
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Api-Key": self.api_key,
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
        }
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data,
                timeout=30,
            )
            
            # Gestione errori HTTP
            if response.status_code == 401:
                raise SmoobuAuthenticationError(f"Authentication failed: {response.text}")
            elif response.status_code == 403:
                raise SmoobuForbiddenError(f"Access denied: {response.text}")
            elif response.status_code == 429:
                retry_after = int(response.headers.get("X-RateLimit-Retry-After", 60))
                logger.warning(f"Rate limit exceeded, waiting {retry_after}s")
                time.sleep(min(retry_after, 60))  # Max 60s wait
                raise SmoobuRateLimitError(f"Rate limit exceeded: {response.text}")
            elif response.status_code >= 500:
                logger.error(f"Server error {response.status_code}: {response.text}")
                response.raise_for_status()
            
            response.raise_for_status()
            return response
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise SmoobuAPIError(f"Request failed: {e}") from e
    
    def get_user(self) -> Dict[str, Any]:
        """
        Recupera informazioni utente corrente.
        
        Returns:
            dict con id, firstName, lastName, email
        """
        response = self._request("GET", "/api/me")
        return response.json()
    
    def get_apartments(self) -> List[Dict[str, Any]]:
        """
        Recupera lista di tutti gli apartments.
        
        Returns:
            Lista di dict con id e name
        """
        response = self._request("GET", "/api/apartments")
        data = response.json()
        return data.get("apartments", [])
    
    def get_apartment(self, apartment_id: int) -> Dict[str, Any]:
        """
        Recupera dettagli di un apartment specifico.
        
        Args:
            apartment_id: ID apartment Smoobu
            
        Returns:
            dict con dettagli apartment
        """
        response = self._request("GET", f"/api/apartments/{apartment_id}")
        return response.json()
    
    def get_reservations(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        created_from: Optional[str] = None,
        created_to: Optional[str] = None,
        modified_from: Optional[str] = None,
        modified_to: Optional[str] = None,
        arrival_from: Optional[str] = None,
        arrival_to: Optional[str] = None,
        departure_from: Optional[str] = None,
        departure_to: Optional[str] = None,
        apartment_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 100,
        show_cancellation: bool = False,
        exclude_blocked: bool = True,
        include_related: bool = False,
        include_price_elements: bool = False,
    ) -> Dict[str, Any]:
        """
        Recupera prenotazioni con filtri.
        
        Args:
            from_date: Data inizio range (yyyy-mm-dd)
            to_date: Data fine range (yyyy-mm-dd)
            created_from: Data creazione inizio (yyyy-mm-dd)
            created_to: Data creazione fine (yyyy-mm-dd)
            modified_from: Data modifica inizio (yyyy-mm-dd)
            modified_to: Data modifica fine (yyyy-mm-dd)
            arrival_from: Data arrivo inizio (yyyy-mm-dd)
            arrival_to: Data arrivo fine (yyyy-mm-dd)
            departure_from: Data partenza inizio (yyyy-mm-dd)
            departure_to: Data partenza fine (yyyy-mm-dd)
            apartment_id: Filtra per apartment specifico
            page: Numero pagina (default: 1)
            page_size: Dimensione pagina (max 100, default: 100)
            show_cancellation: Include prenotazioni cancellate
            exclude_blocked: Esclude blocked bookings
            include_related: Include related apartments
            include_price_elements: Include price elements
            
        Returns:
            dict con page_count, page_size, total_items, page, bookings
        """
        params = {
            "page": page,
            "pageSize": min(page_size, 100),  # Max 100
        }
        
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        if created_from:
            params["created_from"] = created_from
        if created_to:
            params["created_to"] = created_to
        if modified_from:
            params["modifiedFrom"] = modified_from
        if modified_to:
            params["modifiedTo"] = modified_to
        if arrival_from:
            params["arrivalFrom"] = arrival_from
        if arrival_to:
            params["arrivalTo"] = arrival_to
        if departure_from:
            params["departureFrom"] = departure_from
        if departure_to:
            params["departureTo"] = departure_to
        if apartment_id:
            params["apartmentId"] = apartment_id
        if show_cancellation:
            params["showCancellation"] = "true"
        if exclude_blocked:
            params["excludeBlocked"] = "true"
        if include_related:
            params["includeRelated"] = "true"
        if include_price_elements:
            params["includePriceElements"] = "true"
        
        response = self._request("GET", "/api/reservations", params=params)
        return response.json()
    
    def get_reservation(self, reservation_id: int) -> Dict[str, Any]:
        """
        Recupera dettagli di una prenotazione specifica.
        
        Args:
            reservation_id: ID prenotazione Smoobu
            
        Returns:
            dict con dettagli prenotazione
        """
        response = self._request("GET", f"/api/reservations/{reservation_id}")
        return response.json()
    
    def parse_reservation(self, booking_data: Dict[str, Any]) -> SmoobuReservation:
        """
        Parse JSON booking data in SmoobuReservation.
        
        Args:
            booking_data: dict da API response
            
        Returns:
            SmoobuReservation object
        """
        def parse_date(date_str: Optional[str]) -> Optional[datetime]:
            if not date_str:
                return None
            try:
                # Formato: "2025-03-15" o "2025-01-15 13:51"
                if " " in date_str:
                    return datetime.strptime(date_str, "%Y-%m-%d %H:%M")
                return datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                logger.warning(f"Failed to parse date: {date_str}")
                return None
        
        return SmoobuReservation(
            id=booking_data.get("id", 0),
            reference_id=booking_data.get("reference-id"),
            type=booking_data.get("type", "reservation"),
            arrival=parse_date(booking_data.get("arrival")),
            departure=parse_date(booking_data.get("departure")),
            created_at=parse_date(booking_data.get("created-at")),
            modified_at=parse_date(booking_data.get("modifiedAt") or booking_data.get("modified-at")),
            apartment=booking_data.get("apartment", {}),
            channel=booking_data.get("channel"),
            guest_name=booking_data.get("guest-name", ""),
            email=booking_data.get("email", ""),
            phone=booking_data.get("phone"),
            adults=booking_data.get("adults", 1),
            children=booking_data.get("children", 0),
            check_in=booking_data.get("check-in"),
            check_out=booking_data.get("check-out"),
            notice=booking_data.get("notice"),
            assistant_notice=booking_data.get("assistant-notice"),
            price=booking_data.get("price"),
            price_paid=booking_data.get("price-paid"),
            prepayment=booking_data.get("prepayment"),
            prepayment_paid=booking_data.get("prepayment-paid"),
            deposit=booking_data.get("deposit"),
            deposit_paid=booking_data.get("deposit-paid"),
            language=booking_data.get("language"),
            guest_app_url=booking_data.get("guest-app-url"),
            is_blocked_booking=booking_data.get("is-blocked-booking", False),
            guest_id=booking_data.get("guestId"),
            related=booking_data.get("related", []),
            price_elements=booking_data.get("priceElements", []),
        )
    
    def parse_apartment(self, apartment_data: Dict[str, Any]) -> SmoobuApartment:
        """
        Parse JSON apartment data in SmoobuApartment.
        
        Args:
            apartment_data: dict da API response
            
        Returns:
            SmoobuApartment object
        """
        return SmoobuApartment(
            id=apartment_data.get("id", 0),
            name=apartment_data.get("name", ""),
            location=apartment_data.get("location"),
            rooms=apartment_data.get("rooms"),
            currency=apartment_data.get("currency"),
            price=apartment_data.get("price"),
            type=apartment_data.get("type"),
            time_zone=apartment_data.get("timeZone"),
        )

